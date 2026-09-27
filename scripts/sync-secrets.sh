#!/usr/bin/env bash
# Push the keys from .env to the GitHub repo's Actions secrets (values are never printed).
set -euo pipefail
cd "$(dirname "$0")/.."
for name in ANTHROPIC_API_KEY GEMINI_API_KEY GMAIL_APP_PASSWORD; do
  value=$(grep -E "^${name}=" .env | cut -d= -f2- || true)
  if [[ -z "$value" ]]; then
    echo "skip  $name (empty in .env)"
  else
    printf '%s' "$value" | gh secret set "$name" --repo circlenostar23-cloud/netherlands-news
    echo "set   $name"
  fi
done
