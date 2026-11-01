# Build 3C — full service image: FastAPI + Arabic/English UI (http://localhost:8000)
FROM python:3.12-slim

# Stream Python output straight to `docker logs` instead of buffering it —
# without this the container looks silent while it is actually working.
ENV PYTHONUNBUFFERED=1

# xgboost wheels require the GNU OpenMP runtime, which slim images do not ship.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer-cached dependency install (pinned versions = reproducible experiments)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code + the read-only research dataset + the pre-built Arabic/English UI
COPY backend ./backend
COPY data/raw ./data/raw
COPY frontend/dist ./frontend/dist
COPY docs ./docs
COPY VERSION ./VERSION

# Serve the API (interactive docs at /docs). Outputs land under /app/data —
# mounted to the host by docker-compose. The CLI experiment remains available:
#   docker compose run --rm ml-core python -m backend.experiments.run_baseline
EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
