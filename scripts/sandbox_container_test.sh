#!/usr/bin/env bash
# Pre-delivery in-container test (development sandbox only).
# The sandbox kills background processes between tool calls, so this script
# is fully self-contained: it starts dockerd, prepares the local base image
# if missing, builds the app image, runs the baseline inside a container,
# and asserts the expected results appear.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/5] starting dockerd (overlayfs, no bridge — sandbox-safe flags)"
dockerd --iptables=false --ip6tables=false --bridge=none \
        >/tmp/dockerd.log 2>&1 &
DOCKERD_PID=$!
trap 'kill $DOCKERD_PID 2>/dev/null || true' EXIT
for i in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
docker info >/dev/null 2>&1 || { echo "dockerd failed to start"; tail -5 /tmp/dockerd.log; exit 1; }

echo "[2/5] ensuring local base image (Docker Hub is blocked in the sandbox)"
if ! docker image inspect local/ubuntu-noble-py312 >/dev/null 2>&1; then
  if [ ! -f /tmp/rootfs/etc/os-release ]; then
    debootstrap --variant=minbase --components=main,universe \
      --include=python3,python3-pip,libgomp1,ca-certificates \
      noble /tmp/rootfs http://archive.ubuntu.com/ubuntu >/tmp/deb.log 2>&1
  fi
  tar -C /tmp/rootfs -c . | docker import - local/ubuntu-noble-py312 >/dev/null
fi
echo "      base image ready"

echo "[3/5] building app image (same assembly steps as the shipped Dockerfile)"
cp /etc/ssl/certs/ca-certificates.crt .sandbox-ca.crt          # trust the egress proxy inside the build
docker build --network=host -q -t migration-risk-app:sandboxtest \
       -f Dockerfile.sandbox . >/dev/null
rm -f .sandbox-ca.crt
echo "      build OK"

echo "[4/5] running the baseline experiment INSIDE the container"
OUT=$(docker run --rm migration-risk-app:sandboxtest 2>/dev/null)
echo "$OUT" | grep -E "^\[done\]" || true

echo "[5/5] asserting results"
N=$(echo "$OUT" | grep -c "^\[done\]")
[ "$N" -eq 12 ] || { echo "FAIL: expected 12 [done] lines, got $N"; exit 1; }
echo "$OUT" | grep -q "Saved:" || { echo "FAIL: results file not written"; exit 1; }
echo "PASS: 12/12 experiments completed inside the container."
