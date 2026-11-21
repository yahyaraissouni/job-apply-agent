#!/usr/bin/env bash
# Optional: run on your home computer so the server's LinkedIn traffic leaves from your home connection.
# Usage: SERVER=you@your-server KEY=~/.ssh/your_key ./tunnel.sh   then set EASY_PROXY=socks5://127.0.0.1:1080 on the server.
: "${SERVER:?set SERVER=user@host}"
while true; do
  ssh -N -R 127.0.0.1:1080 ${KEY:+-i "$KEY"} -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes "$SERVER"
  sleep 10
done
