#!/bin/sh
# Start the app on http://localhost:8010 (Mac/Linux)
set -eu
cd "$(dirname "$0")/.."
KEY=$(grep '^SSH_KEY_FILE=' .env | cut -d= -f2- | sed "s#^~#$HOME#")
[ -f "$KEY" ] || { echo "SSH_KEY_FILE in .env is not a file: $KEY"; exit 1; }
docker build -t file-processing-check .
docker rm -f file-processing-check >/dev/null 2>&1 || true
docker run -d --restart unless-stopped --name file-processing-check -p 8010:8000 --env-file .env \
  -v "$KEY":/keys/id:ro file-processing-check
echo "Running at http://localhost:8010"
