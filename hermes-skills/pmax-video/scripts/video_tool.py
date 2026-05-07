#!/usr/bin/env python3
"""video_tool.py — submit video-render briefs to task_server for pmax-tarek.

Backs onto the SAME task_server + image_worker pipeline that handles images.
The worker's MODEL_CATALOG dispatches video models to the right FAL endpoints
and saves .mp4 to ~/mem0-server/assets/videos/YYYY-MM/.

Subcommands:
  text-to-video   — generate from a prompt only
  from-image      — animate an existing image (image-to-video)
  status <id>     — get render state
  list            — list recent video tasks

Env:
  TASK_SERVER_URL   — e.g. http://127.0.0.1:7439 (required)
  TASK_TOKEN_FILE   — path to token (default: ~/.hermes/profiles/pmax-tarek/.task_token)

Models:
  text-to-video:
    kling-v3-pro     — Kling v3 Pro, strong motion quality (default)
    seedance-1-pro   — Seedance 1 Pro (ByteDance), cinematic
    veo-3            — Google Veo 3, highest fidelity, includes audio

  image-to-video:
    kling-v3-i2v     — Kling v3 Pro, image-to-video (default)
    luma-ray2-i2v    — Luma Ray 2, strong camera motion
    minimax-i2v      — MiniMax Video 01 Live, fast

Aspect ratios: 16:9 (default), 9:16, 1:1
Durations: 5s (default), 10s  (not every model supports 10)
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

DEFAULT_T2V_MODEL = "kling-v3-pro"
DEFAULT_I2V_MODEL = "kling-v3-i2v"
DEFAULT_ASPECT = "16:9"
DEFAULT_DURATION = "5s"
DEFAULT_WAIT_TIMEOUT_SEC = 300  # videos take longer than images
DEFAULT_POLL_INTERVAL_SEC = 4

VALID_T2V_MODELS = {"kling-v3-pro", "seedance-1-pro", "veo-3"}
VALID_I2V_MODELS = {"kling-v3-i2v", "luma-ray2-i2v", "minimax-i2v"}
VALID_ASPECTS = {"16:9", "9:16", "1:1"}
VALID_DURATIONS = {"5s", "10s", "5", "10"}


def _deliver_to_telegram(file_path: str, caption: str = "", kind: str = "video") -> dict | None:
    """Upload rendered file to Telegram as native video/photo.

    Reads TELEGRAM_BOT_TOKEN + TELEGRAM_HOME_CHANNEL from env. Skips if unset.
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
          timeout: float = 20.0) -> tuple[int, dict]:
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


def _submit_and_wait(
    client: str,
    prompt: str,
    title: str | None,
    model: str,
    aspect: str,
    duration: str,
    image_url: str | None,
    wait_timeout: int,
    poll_interval: int,
    no_wait: bool,
) -> int:
    # 1. create task
    title = title or (prompt[:60] if prompt else f"{model} video")
    create_body = {
        "kind": "video_brief",
        "client": client,
        "title": title,
        "input": prompt or "(image-to-video, no prompt)",
        "created_by": "pmax-tarek",
        "meta": {"source": "video_tool", "render_mode": "video"},
    }
    code, resp = _http("POST", "/tasks", create_body)
    if code != 201:
        print(f"create_task failed: {code} {resp}", file=sys.stderr)
        return 2
    task_id = resp["id"]
    print(f"task {task_id} created  client={client}  model={model}", file=sys.stderr)

    # 2. request render
    render_metadata = {
        "aspect_ratio": aspect,
        "duration": duration,
    }
    if image_url:
        render_metadata["image_url"] = image_url
    render_body = {
        "actor": "pmax-tarek",
        "render_prompt": prompt or "(image-driven)",
        "render_model": model,
        "render_metadata": render_metadata,
    }
    code, resp = _http("POST", f"/tasks/{task_id}/request-render", render_body)
    if code != 200:
        print(f"request-render failed: {code} {resp}", file=sys.stderr)
        return 3
    print(f"task {task_id} queued  aspect={aspect} duration={duration}", file=sys.stderr)

    if no_wait:
        print(json.dumps({"task_id": task_id, "render_state": resp.get("render_state")}))
        return 0

    # 3. poll
    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        time.sleep(poll_interval)
        code, task = _http("GET", f"/tasks/{task_id}")
        if code != 200:
            print(f"poll failed: {code} {task}", file=sys.stderr)
            continue
        state = task.get("render_state")
        if state == "completed":
            url = task.get("render_asset_url") or ""
            local = url[len("file://"):] if url.startswith("file://") else url
            # Auto-deliver to Telegram
            tg_status: dict = {"attempted": False}
            try:
                cap = (prompt[:120] if prompt else f"{model} video")
                dresp = _deliver_to_telegram(local, caption=cap, kind="video")
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
                "model": model,
                "kind": "video",
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

    print(f"timed out after {wait_timeout}s — task {task_id} still not completed",
          file=sys.stderr)
    return 5


def cmd_t2v(args: argparse.Namespace) -> int:
    return _submit_and_wait(
        client=args.client,
        prompt=args.prompt,
        title=args.title,
        model=args.model,
        aspect=args.aspect,
        duration=args.duration,
        image_url=None,
        wait_timeout=args.wait_timeout,
        poll_interval=args.poll_interval,
        no_wait=args.no_wait,
    )


def cmd_i2v(args: argparse.Namespace) -> int:
    src = Path(args.image).expanduser().resolve()
    if not src.exists():
        print(f"image not found: {src}", file=sys.stderr)
        return 6
    image_url = f"file://{src}"

    return _submit_and_wait(
        client=args.client,
        prompt=args.prompt,  # optional guidance
        title=args.title,
        model=args.model,
        aspect=args.aspect,
        duration=args.duration,
        image_url=image_url,
        wait_timeout=args.wait_timeout,
        poll_interval=args.poll_interval,
        no_wait=args.no_wait,
    )


def cmd_status(args: argparse.Namespace) -> int:
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
        "file_path": url[len("file://"):] if url.startswith("file://") else url,
        "render_error": task.get("render_error"),
        "client": task.get("client"),
        "title": task.get("title"),
        "model": task.get("render_model"),
    }, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    q = f"?limit={args.limit}"
    if args.client:
        q += f"&client={args.client}"
    code, resp = _http("GET", f"/tasks{q}")
    if code != 200:
        print(f"list failed: {code} {resp}", file=sys.stderr)
        return 1
    rows = resp.get("tasks", resp if isinstance(resp, list) else [])
    for t in rows:
        kind = t.get("kind") or ""
        if "video" not in kind and not (t.get("render_model") or "").startswith(
            ("kling", "seedance", "veo", "luma", "minimax")
        ):
            continue
        print(f"#{t.get('id'):<5}  {t.get('render_state') or '-':<10}  "
              f"{t.get('render_model'):<20}  {(t.get('title') or '')[:60]}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Tarek video generator (FAL)")
    sub = p.add_subparsers(dest="cmd", required=True)

    t2v = sub.add_parser("text-to-video", aliases=["t2v"], help="text prompt → video")
    t2v.add_argument("--client", required=True)
    t2v.add_argument("--prompt", required=True)
    t2v.add_argument("--title", default=None)
    t2v.add_argument("--model", default=DEFAULT_T2V_MODEL, choices=sorted(VALID_T2V_MODELS))
    t2v.add_argument("--aspect", default=DEFAULT_ASPECT, choices=sorted(VALID_ASPECTS))
    t2v.add_argument("--duration", default=DEFAULT_DURATION, choices=sorted(VALID_DURATIONS))
    t2v.add_argument("--no-wait", action="store_true")
    t2v.add_argument("--wait-timeout", type=int, default=DEFAULT_WAIT_TIMEOUT_SEC)
    t2v.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL_SEC)

    i2v = sub.add_parser("from-image", aliases=["i2v"], help="existing image → video")
    i2v.add_argument("--client", required=True)
    i2v.add_argument("--image", required=True, help="local path to source image")
    i2v.add_argument("--prompt", default="", help="optional motion/style guidance")
    i2v.add_argument("--title", default=None)
    i2v.add_argument("--model", default=DEFAULT_I2V_MODEL, choices=sorted(VALID_I2V_MODELS))
    i2v.add_argument("--aspect", default=DEFAULT_ASPECT, choices=sorted(VALID_ASPECTS))
    i2v.add_argument("--duration", default=DEFAULT_DURATION, choices=sorted(VALID_DURATIONS))
    i2v.add_argument("--no-wait", action="store_true")
    i2v.add_argument("--wait-timeout", type=int, default=DEFAULT_WAIT_TIMEOUT_SEC)
    i2v.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL_SEC)

    s = sub.add_parser("status", help="check render state of a video task")
    s.add_argument("task_id", type=int)

    ls = sub.add_parser("list", help="list recent video tasks")
    ls.add_argument("--client", default=None)
    ls.add_argument("--limit", type=int, default=10)

    args = p.parse_args()
    if args.cmd in ("text-to-video", "t2v"):
        return cmd_t2v(args)
    if args.cmd in ("from-image", "i2v"):
        return cmd_i2v(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "list":
        return cmd_list(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
