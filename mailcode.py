"""Read the latest verification code or link from the candidate's inbox (IMAP, app password)."""
from __future__ import annotations

import datetime as dt
import email
import imaplib
import os
import re
from email.header import decode_header
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = os.environ.get("MAIL_IMAP_HOST", "imap.gmail.com")
USER = os.environ.get("MAIL_USER", "")
PASSFILE = HERE / "secrets" / "mail_app_password"


def _text(msg) -> str:
    parts = []
    for part in msg.walk():
        if part.get_content_type() in ("text/plain", "text/html"):
            try:
                parts.append(part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "ignore"))
            except Exception:
                pass
    return "\n".join(parts)


def latest_code(since_minutes: int = 15) -> str | None:
    if not PASSFILE.exists():
        return None
    m = imaplib.IMAP4_SSL(HOST)
    m.login(USER, PASSFILE.read_text().strip())
    try:
        m.select("INBOX", readonly=True)
        since = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%d-%b-%Y")
        _, data = m.search(None, f'(SINCE "{since}")')
        ids = data[0].split()[-15:]
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=since_minutes)
        for i in reversed(ids):
            _, raw = m.fetch(i, "(RFC822)")
            msg = email.message_from_bytes(raw[0][1])
            when = email.utils.parsedate_to_datetime(msg.get("Date"))
            if when and when.astimezone(dt.timezone.utc) < cutoff:
                break
            subject = "".join(t.decode(c or "utf-8", "ignore") if isinstance(t, bytes) else t
                              for t, c in decode_header(msg.get("Subject", "")))
            body = re.sub(r"<[^>]+>", " ", _text(msg))
            if not re.search(r"verif|code|confirm|activate|one-time|OTP|sign in|security", subject + body[:600], re.I):
                continue
            code = None
            for hit in re.finditer(r"code", body, re.I):
                window = body[hit.end():hit.end() + 250]
                tok = re.search(r"\b((?=[A-Za-z0-9]*\d)[A-Za-z0-9]{6,8})\b", window)
                if tok:
                    code = tok
                    break
            code = code or re.search(r"(?<![\d#])(\d{4,8})(?!\d)", subject + " " + body)
            link = re.search(r"https?://[^\s\"'<>]+(verif|confirm|activate|validate|token)[^\s\"'<>]*", _text(msg), re.I)
            sender = msg.get("From", "")[:80]
            provider = HOST.split(".")[-2] if HOST.count(".") >= 1 else ""
            if provider and re.search(provider, sender, re.I):
                continue  # the mail provider's own security mails are never the code we want
            out = f"from {sender}, subject '{subject[:80]}'"
            if code:
                out += f", code {code.group(1)}"
            if link:
                out += f", link {link.group(0)[:400]}"
            return out
        return None
    finally:
        m.logout()
