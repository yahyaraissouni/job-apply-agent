#!/usr/bin/env bash
# Runs N workers in parallel (searches.yaml "workers"), each taking its share of the postings.
cd "$(dirname "$0")"
set -a; . ./.env; set +a
export TECTONIC="${TECTONIC:-$(command -v tectonic || echo $HOME/bin/tectonic)}"
N="${JOBBOT_WORKERS:-$(.venv/bin/python -c "import yaml;print(yaml.safe_load(open('searches.yaml')).get('workers',1))")}"
for i in $(seq 0 $((N-1))); do
  .venv/bin/python bot.py --shard "$i" --shards "$N" "$@" &
  sleep 20   # stagger the starts
done
wait
