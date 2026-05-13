#!/usr/bin/env bash
set -euo pipefail

BUCKET=$(terraform output -raw bucket_name)
DISTRIBUTION=$(terraform output -raw cloudfront_distribution_id)
SITE_ROOT="$(dirname "$0")/.."
PROFILE="${AWS_PROFILE:-$(terraform output -raw aws_profile 2>/dev/null || echo "default")}"

echo "Building site..."
python3 "$SITE_ROOT/build.py"

echo "Syncing to s3://$BUCKET ..."
aws s3 sync "$SITE_ROOT/site/" "s3://$BUCKET/" \
  --delete \
  --profile "$PROFILE"

echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION" \
  --paths "/*" \
  --profile "$PROFILE" \
  --query "Invalidation.Id" \
  --output text

echo "Done — $(terraform output -raw site_url)"
