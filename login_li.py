"""Opens LinkedIn's login page in the server browser (same profile as the Easy Apply worker)
and exposes it on 127.0.0.1:9222 so you can log in yourself (chrome://inspect or login-screen.sh). Closes once logged in (or after 20 min)."""
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(HERE / "data" / "browser"), headless=os.environ.get("HEADLESS", "1") == "1", locale="en-US", timezone_id="America/Toronto",
        viewport={"width": 1280, "height": 860}, proxy={"server": os.environ["EASY_PROXY"]} if os.environ.get("EASY_PROXY") else None,
        args=["--remote-debugging-port=9222", "--remote-debugging-address=127.0.0.1"],
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    print("Log in to LinkedIn in the window that opened (or in the noVNC page on a server). It closes by itself once you are in.", flush=True)
    end = time.time() + 20 * 60
    while time.time() < end:
        time.sleep(3)
        if any("/feed" in pg.url for pg in ctx.pages):
            print("Logged in. Session saved in the bot's browser.", flush=True)
            (HERE / "data" / ".linkedin_ok").write_text("ok")
            time.sleep(5)
            break
    else:
        print("Timed out (20 min) without login.", flush=True)
    ctx.close()
