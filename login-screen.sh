#!/usr/bin/env bash
# Shows the server browser in a web page (noVNC) so you can log in to LinkedIn himself.
# On your computer: ssh -N -L 6080:127.0.0.1:6080 you@your-server  then open http://localhost:6080/vnc.html
cd "$(dirname "$0")"
pkill -f "Xvfb :99" ; pkill -f "x11vnc.*:99" ; pkill -f "websockify.*6080" ; pkill -f "python login_li" ; sleep 1
Xvfb :99 -screen 0 1280x860x24 >/dev/null 2>&1 &
sleep 1
x11vnc -display :99 -localhost -nopw -forever -shared -rfbport 5999 >/dev/null 2>&1 &
websockify --web /usr/share/novnc 127.0.0.1:6080 127.0.0.1:5999 >/dev/null 2>&1 &
DISPLAY=:99 HEADLESS=0 .venv/bin/python login_li.py
pkill -f "x11vnc.*:99" ; pkill -f "websockify.*6080" ; pkill -f "Xvfb :99"
