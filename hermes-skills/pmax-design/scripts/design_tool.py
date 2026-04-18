#!/usr/bin/env python3
"""design_tool.py — submit template-compose briefs to task_server for pmax-tarek
and pmax-mousa. Mirrors image_tool.py but for the local Pillow compositor
(no FAL, no FAL_KEY, zero render cost).

Usage:
  design_tool.py generate --client <slug> --headline "<hed>" \
                          [--subtitle "<sub>"] [--template-id <id>] \
                          [--title "<task title>"] [--no-wait]
  design_tool.py status <task_id>
  design_tool.py list [--client <slug>] [--limit 10]
  design_tool.py list-templates

Backend flow (async, same lifecycle as image/video):
  1. POST /tasks                         (kind='social_post')
  2. POST /tasks/{id}/request-render     (render_mode='template_compose',
                                          render_model='template/v1')
  3. (default) poll every 2s until completed | failed

Env:
  TASK_SERVER_URL   — e.g. http://127.0.0.1:7439 (profile .env provides this)
  TASK_TOKEN_FILE   — path to bearer token (profile .env provides this)

Templates:
  Located at ~/Projects/design-agent/templates/<slug>.png (PNG, 1080x1080 recommended)
  Configs at ~/Projects/design-agent/configs/<slug>.yaml (text-box coords + fonts)
  Discovery: run `design_tool.py list-templates`.

Template selection:
  If --template-id is passed, the worker uses that.
  Otherwise the worker falls back to task.client as the template slug.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DESIGN_AGENT_CONFIGS = Path.home() / "Projects/design-agent/configs"
DEFAULT_SERVER = "http://127.0.0.1:7439"
TEMPLATE_MODEL = "template/v1"   # server-visible sentinel; actual compose is local Pillow


def _token() -> str:
    p = os.environ.get("TASK_TOKEN_FILE")
    if not p:
        sys.exit("TASK_TOKEN_FILE env var not set — source your profile .env first")
    t = Path(p).read_text().strip()
    if not t:
        sys.exit(f"TASK_TOKEN_FILE {p} is empty")
    return t


def _server() -> str:
    return os.environ.get("TASK_SERVER_URL", DEFAULT_SERVER).rstrip("/")


def _req(method: str, path: str, body: dict | None = None, timeout: int = 30) -> dict:
    url = f"{_server()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_token()}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} {e.reason}: {e.read().decode()[:400]}")
    except urllib.error.URLError as e:
        sys.exit(f"task_server unreachable at {url}: {e.reason}")


def _create_task(client: str, title: str, description: str, actor: str) -> int:
    out = _req("POST", "/tasks", {
        "kind": "social_post",
        "client": client,
        "title": title,
        "input": description,
        "created_by": actor,
    })
    tid = out.get("id")
    if not tid:
        sys.exit(f"task_server returned no id: {out}")
    return int(tid)


def _request_render(task_id: int, headline: str, subtitle: str | None,
                    template_id: str | None, actor: str) -> dict:
    md = {
        "render_mode": "template_compose",
        "template_id": template_id,
        "headline": headline,
        "subtitle": subtitle,
    }
    return _req("POST", f"/tasks/{task_id}/request-render", {
        "actor": actor,
        "render_prompt": f"(template_compose template_id={template_id or '<client>'})",
        "render_model": TEMPLATE_MODEL,
        "render_metadata": md,
    })


def _poll_until_terminal(task_id: int, timeout_sec: int = 60) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        row = _req("GET", f"/tasks/{task_id}")
        state = row.get("render_state")
        if state in ("completed", "failed", "cancelled"):
            return row
        time.sleep(2)
    sys.exit(f"render timed out after {timeout_sec}s (task {task_id})")


def _actor_from_profile() -> str:
    """Infer actor from profile path — tarek vs mousa. Default tarek."""
    token_path = os.environ.get("TASK_TOKEN_FILE", "")
    if "pmax-mousa" in token_path:
        return "mousa"
    if "pmax-tarek" in token_path:
        return "tarek"
    return "tarek"


def cmd_generate(args) -> int:
    actor = _actor_from_profile()
    title = args.title or f"{args.headline[:60]} — template"
    desc = args.subtitle or args.headline
    task_id = _create_task(args.client, title, desc, actor)
    print(f"  task #{task_id} created (kind=social_post, client={args.client})")

    resp = _request_render(task_id, args.headline, args.subtitle, args.template_id, actor)
    print(f"  render_state={resp.get('render_state')}  model={resp.get('render_model')}")

    if args.no_wait:
        print(f"  (not waiting — run `design_tool.py status {task_id}` to check)")
        return 0

    row = _poll_until_terminal(task_id)
    state = row.get("render_state")
    url = row.get("render_asset_url")
    if state == "completed" and url:
        print(f"  ✓ completed — {url}")
        return 0
    print(f"  ✗ {state} — {row.get('render_error') or '(no error field)'}")
    return 1


def cmd_status(args) -> int:
    row = _req("GET", f"/tasks/{args.task_id}")
    print(json.dumps(row, indent=2))
    return 0


def cmd_list(args) -> int:
    params = []
    if args.client:
        params.append(f"client={args.client}")
    params.append(f"limit={args.limit}")
    qs = "&".join(params)
    rows = _req("GET", f"/tasks?{qs}")
    if isinstance(rows, dict) and "tasks" in rows:
        rows = rows["tasks"]
    for r in rows if isinstance(rows, list) else []:
        print(f"  #{r.get('id'):>5} [{r.get('render_state') or '—':<10}] "
              f"client={r.get('client'):<20} {r.get('title')}")
    return 0


def cmd_list_templates(args) -> int:
    if not DESIGN_AGENT_CONFIGS.exists():
        print(f"  no template configs at {DESIGN_AGENT_CONFIGS}")
        return 1
    # Filter EXAMPLE.yaml out BEFORE counting — it's a schema reference, not a
    # real template. Keeping it in the count while skipping it in the loop made
    # the "honest inventory" print a number that didn't match the rows shown.
    configs = [
        c for c in sorted(DESIGN_AGENT_CONFIGS.glob("*.yaml"))
        if c.stem != "EXAMPLE"
    ]
    templates_dir = DESIGN_AGENT_CONFIGS.parent / "templates"
    print(f"  template configs ({len(configs)}):")
    for c in configs:
        slug = c.stem
        # Check if matching PNG exists
        import yaml
        try:
            cfg = yaml.safe_load(c.read_text()) or {}
            png_name = cfg.get("template_file", "")
            png_path = templates_dir / png_name if png_name else None
            has_png = png_path and png_path.exists() if png_path else False
            status = "✓" if has_png else "⚠ PNG missing"
            print(f"    {slug:<25} {status}  (file={png_name})")
        except Exception as e:
            print(f"    {slug:<25} config unreadable: {e}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Create + render a template-compose task")
    g.add_argument("--client", required=True, help="Client slug (defaults as template_id too)")
    g.add_argument("--headline", required=True, help="Headline text (required)")
    g.add_argument("--subtitle", help="Optional subtitle")
    g.add_argument("--template-id", help="Override template slug (default: use --client)")
    g.add_argument("--title", help="Task title (default derived from headline)")
    g.add_argument("--no-wait", action="store_true", help="Return immediately after queueing")
    g.set_defaults(func=cmd_generate)

    s = sub.add_parser("status", help="Fetch one task row")
    s.add_argument("task_id", type=int)
    s.set_defaults(func=cmd_status)

    l = sub.add_parser("list", help="List tasks")
    l.add_argument("--client", help="Filter by client slug")
    l.add_argument("--limit", type=int, default=10)
    l.set_defaults(func=cmd_list)

    lt = sub.add_parser("list-templates", help="List available template configs")
    lt.set_defaults(func=cmd_list_templates)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
