---
name: pmax-email
description: Check inbox, summarize emails, read specific messages, reply, and send new emails for Performance MAX Agency. Use this skill when the user asks about their email, inbox, or wants to send/reply to messages.
version: 1.0.0
author: Mousa Abu Mazin
license: MIT
platforms: [linux, macos]
prerequisites:
  env_vars: [EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_IMAP_HOST, EMAIL_SMTP_HOST]
metadata:
  hermes:
    tags: [email, inbox, imap, smtp, communication, agency]
---

# Performance MAX Email Manager

Manage the agency email inbox directly. Check for new messages, get summaries, read full emails, reply, and compose new ones.

## Available Commands

All commands use the `scripts/email_tool.py` script.

### Check Inbox (unread emails)
```bash
python3 scripts/email_tool.py inbox [--limit 20]
```
Returns a summary of unread emails: sender, subject, date, and first 200 chars of body.

### Read a Specific Email
```bash
python3 scripts/email_tool.py read <email_uid>
```
Returns the full email body, sender, subject, date, and any attachment names.

### Search Emails
```bash
python3 scripts/email_tool.py search "keyword" [--limit 10]
```
Searches subject and body for the keyword. Returns matching emails.

### Reply to an Email
```bash
python3 scripts/email_tool.py reply <email_uid> "Your reply message here"
```
Sends a reply maintaining the email thread (proper In-Reply-To headers).

### Send a New Email
```bash
python3 scripts/email_tool.py send "recipient@example.com" "Subject line" "Email body here"
```
Sends a new email from the agency account.

### Get Daily Summary
```bash
python3 scripts/email_tool.py summary [--hours 24]
```
Returns a categorized summary of emails from the last N hours:
- **Urgent**: client complaints, deadlines, payments
- **Action Required**: new leads, proposals, meeting requests
- **FYI**: newsletters, notifications, automated messages

## Usage Guidelines

- When the user says "check my email" → run `inbox`
- When the user says "what's new" → run `summary --hours 8`
- When the user wants details on a specific email → run `read <uid>`
- When the user says "reply to that" → run `reply <uid> "message"`
- When the user says "email John about X" → run `send`
- Always show the draft before sending a reply — ask for confirmation
- Categorize emails by urgency when presenting summaries
- Keep summaries concise — sender, subject, one-line preview
