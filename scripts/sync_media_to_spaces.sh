#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

: "${DO_SPACES_BUCKET:?DO_SPACES_BUCKET is required}"
: "${DO_SPACES_REGION:?DO_SPACES_REGION is required (example: nyc3)}"
DO_SPACES_ENDPOINT="${DO_SPACES_ENDPOINT:-https://${DO_SPACES_REGION}.digitaloceanspaces.com}"

if ! command -v aws >/dev/null 2>&1; then
  echo "Error: aws CLI is required. Install it first." >&2
  exit 1
fi

echo "Syncing videos to s3://${DO_SPACES_BUCKET}/videos ..."
aws --endpoint-url "$DO_SPACES_ENDPOINT" s3 sync \
  "$FRONTEND_DIR/public/videos" \
  "s3://${DO_SPACES_BUCKET}/videos" \
  --acl public-read \
  --exclude ".gitkeep"

aws --endpoint-url "$DO_SPACES_ENDPOINT" s3 sync \
  "$FRONTEND_DIR/src/assets/videos" \
  "s3://${DO_SPACES_BUCKET}/videos" \
  --acl public-read \
  --exclude ".gitkeep"

echo "Syncing images to s3://${DO_SPACES_BUCKET}/images ..."
aws --endpoint-url "$DO_SPACES_ENDPOINT" s3 sync \
  "$FRONTEND_DIR/src/assets/images" \
  "s3://${DO_SPACES_BUCKET}/images" \
  --acl public-read \
  --exclude ".gitkeep"

aws --endpoint-url "$DO_SPACES_ENDPOINT" s3 sync \
  "$FRONTEND_DIR/src/assets/logos" \
  "s3://${DO_SPACES_BUCKET}/images" \
  --acl public-read \
  --exclude ".gitkeep"

echo "Done. Set NEXT_PUBLIC_MEDIA_BASE_URL to your Spaces/CDN origin, for example:"
echo "https://${DO_SPACES_BUCKET}.${DO_SPACES_REGION}.digitaloceanspaces.com"
