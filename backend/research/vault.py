"""File vault (v19): local versioned storage for research documents.

Each document keeps ALL its uploaded versions with a timestamp and a
what-changed note (meta.json). This is a local history, not a cloud backup —
keep the project folder inside OneDrive/Drive for that.
"""
from __future__ import annotations
import json, datetime, re
from backend.core import config as C

BASE = C.ROOT / "data" / "vault"


def _safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() or "file"


def list_docs() -> list[dict]:
    if not BASE.exists():
        return []
    out = []
    for d in sorted(BASE.iterdir()):
        mp = d / "meta.json"
        if d.is_dir() and mp.exists():
            m = json.loads(mp.read_text())
            out.append({"name": m["name"], "latest": m["versions"][-1],
                        "versions": m["versions"][::-1]})
    return out


def save(name: str, data: bytes, note: str) -> dict:
    folder = BASE / _safe(name)
    folder.mkdir(parents=True, exist_ok=True)
    mp = folder / "meta.json"
    m = json.loads(mp.read_text()) if mp.exists() else {"name": name, "versions": []}
    n = len(m["versions"]) + 1
    fname = f"v{n:03d}__{_safe(name)}"
    (folder / fname).write_bytes(data)
    entry = {"n": n, "ts": datetime.datetime.now().isoformat(timespec="seconds"),
             "note": (note or "").strip(), "file": fname, "size": len(data)}
    m["versions"].append(entry)
    mp.write_text(json.dumps(m, ensure_ascii=False, indent=1))
    return entry


def filepath(name: str, version: int | None = None):
    folder = BASE / _safe(name)
    m = json.loads((folder / "meta.json").read_text())
    vs = m["versions"]
    e = vs[-1] if version is None else next(v for v in vs if v["n"] == int(version))
    return folder / e["file"], e
