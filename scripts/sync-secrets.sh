#!/usr/bin/env bash
# Push the keys from .env to the GitHub repo's Actions secrets (values are never printed).
# A key with no line in .env yet (e.g. one added since your .env was made) is asked for once
# and saved to .env; press Enter to leave it out. Empty keys are skipped, and their GitHub
# secrets are left as they are.
set -euo pipefail
cd "$(dirname "$0")/.."
for name in CLAUDE_CODE_OAUTH_TOKEN ANTHROPIC_API_KEY GEMINI_API_KEY GMAIL_APP_PASSWORD OPENROUTER_API_KEY; do
  if ! grep -qE "^${name}=" .env && [[ -t 0 ]]; then
    read -rsp "$name isn't in .env yet. Paste it (or press Enter to skip): " value; echo
    [[ -s .env && -n $(tail -c1 .env) ]] && echo >> .env  # don't glue it onto a last line with no newline
    printf '%s=%s\n' "$name" "$value" >> .env
  fi
  value=$(grep -E "^${name}=" .env | cut -d= -f2- || true)
  if [[ -z "$value" ]]; then
    echo "skip  $name (empty in .env; the GitHub secret, if any, is unchanged)"
  else
    printf '%s' "$value" | gh secret set "$name" --repo circlenostar23-cloud/netherlands-news
    echo "set   $name"
  fi
done
