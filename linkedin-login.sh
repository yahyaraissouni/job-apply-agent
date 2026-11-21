#!/usr/bin/env bash
# Opens LinkedIn in the agent's own browser so YOU log in (never copy cookies like li_at: LinkedIn kills copied
# sessions and logs you out everywhere). The session is saved in data/browser for Easy Apply.
cd "$(dirname "$0")"
set -a; [ -f .env ] && . ./.env; set +a
if [ "$(uname)" = "Darwin" ] || [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
  HEADLESS=0 .venv/bin/python login_li.py          # a normal window opens on this computer
else
  ./login-screen.sh                                # server without a screen: web view through noVNC
fi
