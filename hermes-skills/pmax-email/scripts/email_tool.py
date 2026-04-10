#!/usr/bin/env python3
"""Performance MAX Email Tool — IMAP/SMTP email management for Hermes."""

import argparse
import email as email_lib
import imaplib
import json
import os
import smtplib
import ssl
import sys
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def _load_env():
    """Load env vars from the active Hermes profile .env file."""
    hermes_home = os.environ.get("HERMES_HOME", "")
    env_path = Path(hermes_home) / ".env" if hermes_home else None

    if not env_path or not env_path.exists():
        # Fallback: scan all profile dirs for one that has EMAIL_ADDRESS set
        profiles_dir = Path.home() / ".hermes" / "profiles"
        for profile in sorted(profiles_dir.iterdir()) if profiles_dir.exists() else []:
            candidate = profile / ".env"
            if candidate.exists():
                env_path = candidate
                break

    if not env_path or not env_path.exists():
        env_path = Path.home() / ".hermes" / ".env"

    if env_path and env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_env()


def _get_config():
    return {
        "address": os.environ.get("EMAIL_ADDRESS", "Mousa@performancemaxagency.com"),
        "password": os.environ.get("EMAIL_PASSWORD", ""),
        "imap_host": os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com"),
        "imap_port": int(os.environ.get("EMAIL_IMAP_PORT", "993")),
        "smtp_host": os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.environ.get("EMAIL_SMTP_PORT", "587")),
    }


def _connect_imap(cfg):
    mail = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"])
    mail.login(cfg["address"], cfg["password"])
    return mail


def _decode_header_value(raw):
    if raw is None:
        return ""
    parts = decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
        if not body:
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
    return body.strip()


def _get_attachments(msg):
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                fname = part.get_filename()
                if fname:
                    attachments.append(_decode_header_value(fname))
    return attachments


def _parse_email(raw_data, uid):
    msg = email_lib.message_from_bytes(raw_data)
    sender = _decode_header_value(msg.get("From", ""))
    subject = _decode_header_value(msg.get("Subject", "(no subject)"))
    date = _decode_header_value(msg.get("Date", ""))
    message_id = msg.get("Message-ID", "")
    body = _extract_body(msg)
    attachments = _get_attachments(msg)
    return {
        "uid": uid,
        "from": sender,
        "subject": subject,
        "date": date,
        "message_id": message_id,
        "body": body,
        "attachments": attachments,
    }


def cmd_inbox(args):
    cfg = _get_config()
    mail = _connect_imap(cfg)
    mail.select("INBOX")
    _, data = mail.uid("search", None, "UNSEEN")
    uids = data[0].split() if data[0] else []
    if not uids:
        print("No unread emails.")
        mail.logout()
        return
    uids = uids[-(args.limit):]
    results = []
    for uid in uids:
        _, msg_data = mail.uid("fetch", uid, "(BODY.PEEK[])")
        if msg_data[0] is None:
            continue
        raw = msg_data[0][1]
        parsed = _parse_email(raw, uid.decode())
        preview = parsed["body"][:200].replace("\n", " ")
        results.append({
            "uid": parsed["uid"],
            "from": parsed["from"],
            "subject": parsed["subject"],
            "date": parsed["date"],
            "preview": preview,
            "attachments": parsed["attachments"],
        })
    mail.logout()
    print(f"📬 {len(results)} unread email(s):\n")
    for i, e in enumerate(results, 1):
        att = f" 📎 {', '.join(e['attachments'])}" if e["attachments"] else ""
        print(f"{i}. [UID {e['uid']}] {e['subject']}")
        print(f"   From: {e['from']}")
        print(f"   Date: {e['date']}")
        print(f"   Preview: {e['preview']}{att}")
        print()


def cmd_read(args):
    cfg = _get_config()
    mail = _connect_imap(cfg)
    mail.select("INBOX")
    _, msg_data = mail.uid("fetch", args.uid.encode(), "(BODY[])")
    if msg_data[0] is None:
        print(f"Email UID {args.uid} not found.")
        mail.logout()
        return
    raw = msg_data[0][1]
    parsed = _parse_email(raw, args.uid)
    mail.logout()
    print(f"From: {parsed['from']}")
    print(f"Subject: {parsed['subject']}")
    print(f"Date: {parsed['date']}")
    if parsed["attachments"]:
        print(f"Attachments: {', '.join(parsed['attachments'])}")
    print(f"\n{parsed['body']}")


def cmd_search(args):
    cfg = _get_config()
    mail = _connect_imap(cfg)
    mail.select("INBOX")
    _, data = mail.uid("search", None, f'(OR SUBJECT "{args.query}" BODY "{args.query}")')
    uids = data[0].split() if data[0] else []
    if not uids:
        print(f"No emails matching '{args.query}'.")
        mail.logout()
        return
    uids = uids[-(args.limit):]
    results = []
    for uid in uids:
        _, msg_data = mail.uid("fetch", uid, "(BODY.PEEK[])")
        if msg_data[0] is None:
            continue
        raw = msg_data[0][1]
        parsed = _parse_email(raw, uid.decode())
        preview = parsed["body"][:200].replace("\n", " ")
        results.append({
            "uid": parsed["uid"],
            "from": parsed["from"],
            "subject": parsed["subject"],
            "date": parsed["date"],
            "preview": preview,
        })
    mail.logout()
    print(f"🔍 {len(results)} email(s) matching '{args.query}':\n")
    for i, e in enumerate(results, 1):
        print(f"{i}. [UID {e['uid']}] {e['subject']}")
        print(f"   From: {e['from']}")
        print(f"   Date: {e['date']}")
        print(f"   Preview: {e['preview']}")
        print()


def cmd_reply(args):
    cfg = _get_config()
    mail = _connect_imap(cfg)
    mail.select("INBOX")
    _, msg_data = mail.uid("fetch", args.uid.encode(), "(BODY[])")
    if msg_data[0] is None:
        print(f"Email UID {args.uid} not found.")
        mail.logout()
        return
    raw = msg_data[0][1]
    original = _parse_email(raw, args.uid)
    mail.logout()

    reply_msg = MIMEMultipart()
    reply_msg["From"] = cfg["address"]
    reply_msg["To"] = original["from"]
    subject = original["subject"]
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    reply_msg["Subject"] = subject
    if original["message_id"]:
        reply_msg["In-Reply-To"] = original["message_id"]
        reply_msg["References"] = original["message_id"]
    reply_msg.attach(MIMEText(args.message, "plain", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
        server.starttls(context=context)
        server.login(cfg["address"], cfg["password"])
        server.send_message(reply_msg)

    print(f"Reply sent to {original['from']}")
    print(f"Subject: {subject}")


def cmd_send(args):
    cfg = _get_config()
    msg = MIMEMultipart()
    msg["From"] = cfg["address"]
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg.attach(MIMEText(args.body, "plain", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
        server.starttls(context=context)
        server.login(cfg["address"], cfg["password"])
        server.send_message(msg)

    print(f"Email sent to {args.to}")
    print(f"Subject: {args.subject}")


def cmd_summary(args):
    cfg = _get_config()
    mail = _connect_imap(cfg)
    mail.select("INBOX")
    since = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).strftime("%d-%b-%Y")
    _, data = mail.uid("search", None, f'(SINCE "{since}")')
    uids = data[0].split() if data[0] else []
    if not uids:
        print(f"No emails in the last {args.hours} hours.")
        mail.logout()
        return

    emails = []
    for uid in uids:
        _, msg_data = mail.uid("fetch", uid, "(BODY.PEEK[])")
        if msg_data[0] is None:
            continue
        raw = msg_data[0][1]
        parsed = _parse_email(raw, uid.decode())
        preview = parsed["body"][:300].replace("\n", " ")
        emails.append({
            "uid": parsed["uid"],
            "from": parsed["from"],
            "subject": parsed["subject"],
            "date": parsed["date"],
            "preview": preview,
            "attachments": parsed["attachments"],
        })

    mail.logout()
    print(f"📊 Email summary — last {args.hours} hours ({len(emails)} emails):\n")
    for i, e in enumerate(emails, 1):
        att = f" 📎 {', '.join(e['attachments'])}" if e["attachments"] else ""
        print(f"{i}. [UID {e['uid']}] {e['subject']}")
        print(f"   From: {e['from']}")
        print(f"   Date: {e['date']}")
        print(f"   Preview: {e['preview']}{att}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Performance MAX Email Tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inbox = sub.add_parser("inbox", help="Show unread emails")
    p_inbox.add_argument("--limit", type=int, default=20)
    p_inbox.set_defaults(func=cmd_inbox)

    p_read = sub.add_parser("read", help="Read a specific email")
    p_read.add_argument("uid", help="Email UID")
    p_read.set_defaults(func=cmd_read)

    p_search = sub.add_parser("search", help="Search emails")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.set_defaults(func=cmd_search)

    p_reply = sub.add_parser("reply", help="Reply to an email")
    p_reply.add_argument("uid", help="Email UID to reply to")
    p_reply.add_argument("message", help="Reply message")
    p_reply.set_defaults(func=cmd_reply)

    p_send = sub.add_parser("send", help="Send a new email")
    p_send.add_argument("to", help="Recipient address")
    p_send.add_argument("subject", help="Email subject")
    p_send.add_argument("body", help="Email body")
    p_send.set_defaults(func=cmd_send)

    p_summary = sub.add_parser("summary", help="Email summary for last N hours")
    p_summary.add_argument("--hours", type=int, default=24)
    p_summary.set_defaults(func=cmd_summary)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
