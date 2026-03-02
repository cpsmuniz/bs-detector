#!/bin/sh
set -e

# Always copy image fixtures into /app so container does not depend on host (volume mount overwrites /app)
mkdir -p /app/evals/fixtures
cp -r /evals-fixtures/. /app/evals/fixtures/

pip install --no-cache-dir -r requirements.txt

exec uvicorn main:app --host 0.0.0.0 --port 8002 --reload
