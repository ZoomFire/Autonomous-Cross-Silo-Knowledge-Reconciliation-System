#!/usr/bin/env sh
cd "$(dirname "$0")/../backend" || exit 1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001

