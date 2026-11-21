#!/usr/bin/env bash
# Saves your email APP password (not your normal password) so the agent can read verification codes.
# Gmail: Google Account > Security > App passwords. Yahoo: Account security > Generate app password.
set -euo pipefail
cd "$(dirname "$0")"
read -r -s -p "Email app password (hidden): " v; echo
v="$(printf '%s' "$v" | tr -d '[:space:]')"
if [ -z "$v" ]; then echo "Nothing saved."; exit 1; fi
mkdir -p secrets; umask 077; printf '%s' "$v" > secrets/mail_app_password
set -a; . ./.env; set +a
.venv/bin/python -c "import mailcode; print('login OK, latest:', mailcode.latest_code(60*24))"
