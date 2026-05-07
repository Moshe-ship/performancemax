#!/usr/bin/env python3
"""image_tool.py — submit image-render briefs to task_server for pmax-tarek.

Usage:
  image_tool.py generate --client <slug> --prompt "<image prompt>" \
                         [--title "<title>"] [--headline "<hed>"] [--subtitle "<sub>"] \
                         [--model ideogram-3] [--aspect 1:1] [--style-tags tag1,tag2] \
                         [--no-wait]
  image_tool.py status <task_id>
  image_tool.py list [--client <slug>] [--limit 10]

Backend flow (async):
  1. POST /tasks            (creates draft task with kind='image_brief')
  2. POST /tasks/{id}/request-render  (kicks off image_worker render)
  3. (default) poll GET /tasks/{id} every 2s until completed or failed

Env:
  TASK_SERVER_URL   — e.g. http://192.168.40.3:7439 (required)
  TASK_TOKEN_FILE   — path to token (default: ~/.hermes/profiles/pmax-tarek/.task_token)
  HERMES_HOME       — if set, overrides profile path

Models:
  ideogram-3        — text-heavy social graphics (default for Tarek's workflow)
  flux-2-pro        — photorealistic hero shots
  nano-banana-pro   — text + photo hybrid
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "ideogram-3"
DEFAULT_ASPECT = "1:1"
DEFAULT_WAIT_TIMEOUT_SEC = 120
DEFAULT_POLL_INTERVAL_SEC = 2


def _load_token() -> str:
    path_env = os.environ.get("TASK_TOKEN_FILE")
    if path_env:
        p = Path(path_env)
    else:
        hermes_home = os.environ.get("HERMES_HOME")
        if hermes_home:
            p = Path(hermes_home) / ".task_token"
        else:
            p = Path.home() / ".hermes" / "profiles" / "pmax-tarek" / ".task_token"
    if not p.exists():
        raise SystemExit(f"task_token not found at {p}")
    return p.read_text().strip()


def _server_url() -> str:
    url = os.environ.get("TASK_SERVER_URL")
    if not url:
        raise SystemExit("TASK_SERVER_URL env var not set")
    return url.rstrip("/")


def _http(method: str, path: str, body: dict | None = None,
          timeout: float = 15.0) -> tuple[int, dict]:
    url = _server_url() + path
    headers = {
        "Authorization": f"Bearer {_load_token()}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {"error": "unparseable"}
    except Exception as e:
        return 0, {"error": f"network_error: {e}"}


def _deliver_to_telegram(file_path: str, caption: str = "", kind: str = "image") -> dict | None:
    """POST a rendered file directly to Telegram as a native image or video.

    Reads TELEGRAM_BOT_TOKEN and TELEGRAM_HOME_CHANNEL from env (set by the
    Hermes profile .env). Skips silently if either is missing, so this works
    fine from CLI too.

    Returns the Telegram API response dict on success, None if skipped, raises
    on hard failure (so the caller can surface the error).
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_HOME_CHANNEL") or os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return None
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"deliver: file missing: {file_path}")
    endpoint = "sendVideo" if kind == "video" else "sendPhoto"
    field = "video" if kind == "video" else "photo"
    url = f"https://api.telegram.org/bot{token}/{endpoint}"
    args = [
        "curl", "-sS", "--max-time", "180",
        "-F", f"chat_id={chat_id}",
        "-F", f"{field}=@{file_path}",
    ]
    if caption:
        args += ["-F", f"caption={caption[:1024]}"]
    args.append(url)
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl failed ({r.returncode}): {r.stderr[:400]}")
    try:
        resp = json.loads(r.stdout)
    except Exception as e:
        raise RuntimeError(f"telegram response parse failed: {e}  raw={r.stdout[:300]}")
    if not resp.get("ok"):
        raise RuntimeError(f"telegram error: {resp}")
    return resp


def _studio_path_from_file_url(file_url: str) -> str:
    """image_worker mirrors assets to Studio. The file:// URL comes back with
    the MacBook prefix; translate to Studio's /Users/majana-agent/ equivalent
    so Tarek (running on Studio) can read the file directly."""
    if not file_url.startswith("file://"):
        return file_url
    p = file_url[len("file://"):]
    return p.replace("/Users/mousaabumazin/", "/Users/majana-agent/", 1)


def generate(args: argparse.Namespace) -> int:
    # 1. Create draft task
    style_tags: list[str] = []
    if args.style_tags:
        style_tags = [t.strip() for t in args.style_tags.split(",") if t.strip()]

    title = args.title or (args.headline or args.prompt[:60])
    create_body = {
        "kind": "image_brief",
        "client": args.client,
        "title": title,
        "input": args.prompt,
        "created_by": "pmax-tarek",
        "headline": args.headline,
        "subtitle": args.subtitle,
        "meta": {
            "source": "image_tool",
            "render_mode": "image",
        },
    }
    code, resp = _http("POST", "/tasks", create_body)
    if code != 201:
        print(f"create_task failed: {code} {resp}", file=sys.stderr)
        return 2
    task_id = resp["id"]
    print(f"task {task_id} created  client={args.client}", file=sys.stderr)

    # 2. Request render — include image_url if a style reference was given.
    # The worker auto-routes any image_url to nano-banana-pro (i2i capable).
    render_metadata: dict = {
        "style_tags": style_tags,
        "aspect_ratio": args.aspect,
        "headline": args.headline,
        "subtitle": args.subtitle,
    }
    if getattr(args, "style_ref", None):
        ref = Path(args.style_ref).expanduser().resolve()
        if not ref.exists():
            print(f"style-ref not found: {ref}", file=sys.stderr)
            return 6
        render_metadata["image_url"] = f"file://{ref}"
    render_body = {
        "actor": "pmax-tarek",
        "render_prompt": args.prompt,
        "render_model": args.model,
        "render_metadata": render_metadata,
    }
    code, resp = _http("POST", f"/tasks/{task_id}/request-render", render_body)
    if code != 200:
        print(f"request-render failed: {code} {resp}", file=sys.stderr)
        return 3
    print(f"task {task_id} queued  model={args.model}  aspect={args.aspect}", file=sys.stderr)

    if args.no_wait:
        print(json.dumps({"task_id": task_id, "render_state": resp.get("render_state")}))
        return 0

    # 3. Poll until done
    deadline = time.time() + args.wait_timeout
    while time.time() < deadline:
        time.sleep(args.poll_interval)
        code, task = _http("GET", f"/tasks/{task_id}")
        if code != 200:
            print(f"poll failed: {code} {task}", file=sys.stderr)
            continue
        state = task.get("render_state")
        if state == "completed":
            url = task.get("render_asset_url") or ""
            local = _studio_path_from_file_url(url)
            # Auto-deliver to Telegram if env has bot token + chat
            tg_status: dict = {"attempted": False}
            try:
                caption = args.headline or (args.prompt[:120] if args.prompt else "")
                dresp = _deliver_to_telegram(local, caption=caption, kind="image")
                if dresp is None:
                    tg_status = {"attempted": False, "reason": "no TELEGRAM_BOT_TOKEN or TELEGRAM_HOME_CHANNEL"}
                else:
                    tg_status = {"attempted": True, "ok": True,
                                 "message_id": dresp["result"].get("message_id")}
            except Exception as e:
                tg_status = {"attempted": True, "ok": False, "error": str(e)}
            print(json.dumps({
                "task_id": task_id,
                "render_state": state,
                "render_asset_url": url,
                "file_path": local,
                "model": args.model,
                "telegram_delivery": tg_status,
            }))
            return 0
        if state == "failed":
            print(json.dumps({
                "task_id": task_id,
                "render_state": state,
                "render_error": task.get("render_error"),
            }))
            return 4

    print(f"timed out after {args.wait_timeout}s — task {task_id} still not completed",
          file=sys.stderr)
    return 5


def status(args: argparse.Namespace) -> int:
    code, task = _http("GET", f"/tasks/{args.task_id}")
    if code != 200:
        print(f"status failed: {code} {task}", file=sys.stderr)
        return 1
    url = task.get("render_asset_url") or ""
    print(json.dumps({
        "task_id": task["id"],
        "status": task.get("status"),
        "render_state": task.get("render_state"),
        "render_asset_url": url,
        "file_path": _studio_path_from_file_url(url) if url else None,
        "render_error": task.get("render_error"),
        "client": task.get("client"),
        "title": task.get("title"),
    }, indent=2))
    return 0


def list_tasks(args: argparse.Namespace) -> int:
    q = f"?limit={args.limit}"
    if args.client:
        q += f"&client={args.client}"
    code, resp = _http("GET", f"/tasks{q}")
    if code != 200:
        print(f"list failed: {code} {resp}", file=sys.stderr)
        return 1
    rows = resp.get("tasks", resp if isinstance(resp, list) else [])
    for t in rows:
        print(f"#{t.get('id'):<5}  {t.get('render_state') or '-':<10}  "
              f"{t.get('client'):<20}  {(t.get('title') or '')[:60]}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="create brief + render image")
    g.add_argument("--client", required=True)
    g.add_argument("--prompt", required=True, help="image generation prompt")
    g.add_argument("--title", default=None)
    g.add_argument("--headline", default=None)
    g.add_argument("--subtitle", default=None)
    g.add_argument("--model", default=DEFAULT_MODEL,
                   choices=["ideogram-3", "flux-2-pro", "nano-banana-pro"])
    g.add_argument("--aspect", default=DEFAULT_ASPECT,
                   choices=["1:1", "9:16", "16:9", "4:5", "4:3"])
    g.add_argument("--style-tags", default="")
    g.add_argument("--style-ref", default=None,
                   help="Local path to a reference image (auto-routes to nano-banana-pro i2i). "
                        "Use client refs under ~/Projects/performancemax/client-style-refs/<slug>/.")
    g.add_argument("--no-wait", action="store_true")
    g.add_argument("--wait-timeout", type=int, default=DEFAULT_WAIT_TIMEOUT_SEC)
    g.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL_SEC)

    s = sub.add_parser("status", help="get render state of a task")
    s.add_argument("task_id", type=int)

    ls = sub.add_parser("list", help="list recent tasks")
    ls.add_argument("--client", default=None)
    ls.add_argument("--limit", type=int, default=10)

    args = p.parse_args()
    if args.cmd == "generate":
        return generate(args)
    if args.cmd == "status":
        return status(args)
    if args.cmd == "list":
        return list_tasks(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
