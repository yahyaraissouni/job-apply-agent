#!/usr/bin/env bash
# Saves your Claude API key in .env (hidden prompt; never paste it in a chat) and checks it works.
# Get one at https://platform.claude.com/settings/keys  (set a monthly spend limit in Settings > Limits).
set -euo pipefail
cd "$(dirname "$0")"
read -r -s -p "Claude API key (hidden, starts with sk-ant-): " k; echo
k="$(printf '%s' "$k" | tr -d '[:space:]')"
case "$k" in sk-ant-*) ;; *) echo "That doesn't look like a Claude API key (sk-ant-...). Nothing saved."; exit 1;; esac
code=$(curl -s -o /dev/null -w '%{http_code}' https://api.anthropic.com/v1/models -H "x-api-key: $k" -H "anthropic-version: 2023-06-01")
if [ "$code" != "200" ]; then echo "The key was refused (HTTP $code). Nothing saved."; exit 1; fi
[ -f .env ] || cp .env.example .env
umask 077
grep -v '^ANTHROPIC_API_KEY=' .env > .env.tmp || true
printf 'ANTHROPIC_API_KEY=%s\n' "$k" | cat - .env.tmp > .env && rm -f .env.tmp
chmod 600 .env
echo "Key saved in .env and accepted by Claude."
