#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <backend-url> <frontend-url>" >&2
  exit 2
fi

backend_url=${1%/}
frontend_url=${2%/}

echo "Checking backend health..."
curl --fail --silent --show-error "$backend_url/health"
echo

echo "Checking backend readiness..."
curl --fail --silent --show-error "$backend_url/ready"
echo

echo "Checking AI status endpoint..."
curl --fail --silent --show-error "$backend_url/api/v1/ai/status"
echo

echo "Checking frontend and SPA route..."
curl --fail --silent --show-error "$frontend_url/" >/dev/null
curl --fail --silent --show-error "$frontend_url/review" >/dev/null
echo "Frontend root and /review returned successfully."

echo "Smoke checks passed."
