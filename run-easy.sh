#!/usr/bin/env bash
# LinkedIn Easy Apply worker. If EASY_PROXY is set (e.g. a home tunnel, see README), skip the run when it is down.
cd "$(dirname "$0")"
set -a; . ./.env; set +a
export TECTONIC="${TECTONIC:-$(command -v tectonic || echo $HOME/bin/tectonic)}"
if [ -n "${EASY_PROXY:-}" ] && ! curl -s -m 10 -x "$EASY_PROXY" https://www.linkedin.com -o /dev/null; then
  mkdir -p data; echo "$(date '+%F %T') [easy] proxy $EASY_PROXY is down: skipping" >> data/bot.log; exit 0
fi
exec .venv/bin/python easy.py "$@"
