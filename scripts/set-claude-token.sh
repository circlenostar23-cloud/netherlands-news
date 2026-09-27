#!/usr/bin/env bash
# Prompt for the `claude setup-token` token (input hidden), store it in .env, and push all keys to GitHub.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Paste your Claude token (from 'claude setup-token'), then press Enter on an empty line."
echo "(Input is hidden. Line breaks from terminal wrapping are fine.)"
token=""
while IFS= read -rs line; do
  [[ -z "$line" ]] && break
  token+="$line"
done
token=$(printf '%s' "$token" | tr -d '[:space:]')
[[ -n "$token" ]] || { echo "No token entered."; exit 1; }
tmp=$(mktemp)
grep -v '^CLAUDE_CODE_OAUTH_TOKEN=' .env > "$tmp" || true
printf 'CLAUDE_CODE_OAUTH_TOKEN=%s\n' "$token" >> "$tmp"
mv "$tmp" .env && chmod 600 .env
echo "Saved to .env (${#token} characters)."
if [[ "$token" != sk-ant-oat* || ${#token} -lt 90 ]]; then
  echo "Warning: this doesn't look like a complete token (expected ~100 chars starting with sk-ant-oat)."
fi
./scripts/sync-secrets.sh
