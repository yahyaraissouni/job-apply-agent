#!/usr/bin/env bash
# Night mode: leave the computer plugged in and on; it applies at full speed until morning, then stops.
# Usage: ./night.sh [hours, default 8] [workers, default 3]
# Keeps the computer awake only while it runs. The daily cap in searches.yaml still applies.
cd "$(dirname "$0")"
HOURS="${1:-8}"; WORKERS="${2:-3}"
END=$(( $(date +%s) + HOURS * 3600 ))
loop() {
  while [ "$(date +%s)" -lt "$END" ]; do
    JOBBOT_WORKERS="$WORKERS" ./run.sh
    [ -f data/.searches_reviewed ] && [ -x ./run-easy.sh ] && [ -f data/.linkedin_ok ] && ./run-easy.sh
    sleep 120
  done
  echo "$(date '+%F %T') night mode finished" >> data/bot.log
}
echo "Night mode: ${HOURS} h, ${WORKERS} workers. Keep the computer plugged in, lid open. Ctrl+C to stop."
export -f loop; export END WORKERS
if command -v caffeinate >/dev/null; then caffeinate -is bash -c loop        # macOS: no sleep while running
elif command -v systemd-inhibit >/dev/null; then systemd-inhibit --what=sleep:idle --why="job apply agent" bash -c loop
else loop; fi
