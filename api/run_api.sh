#!/bin/bash
# Run the FastAPI server

cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

