#!/usr/bin/env sh
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8001}"
echo "Checking $BACKEND_URL/health"
curl -f "$BACKEND_URL/health"
echo
echo "Checking $BACKEND_URL/system/ready"
curl -f "$BACKEND_URL/system/ready"
echo

