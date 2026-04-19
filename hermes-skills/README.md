# Performance MAX — Hermes Skills

Skills used by the Hermes profile fleet on Studio. **One shared media backend** (task_server + image_worker + FAL), many profile lanes into it — not a fleet of independent media agents.

## Profile → lane matrix

| Profile | Surface | Media scope | Toolsets (as of 2026-04-18) |
|---|---|---|---|
| **pmax-tarek** | Telegram + Email | Broad operator — full 4-piece media kit (`pmax-content`, `pmax-image`, `pmax-video`, `pmax-design`) via `image_tool.py`/`video_tool.py` wrappers. Has `baoyu-infographic` (21 layouts × 21 styles, FAL via nano-banana-pro). | `terminal, web` |
| **pmax-mousa** | WhatsApp + Email + Google Workspace | Broad operator — same kit as Tarek. Has `baoyu-infographic`. | `terminal, web` |
| **pmax-dareen** | WhatsApp (client-facing, LIVE) | Narrow frontend lane: drafts content + submits render jobs via `dareen_task_cli.py` wrapper. Render modes: `image` + `video`. No direct FAL credentials. | `terminal, web` |
| **pmax-content** (the profile) | Email only (inbound from n8n workflows) | **Review-only article agent.** Reads Google Doc links, produces structured reviews, writes to mem0 under `user_id=content-reviews`. Does NOT generate media. | `terminal, web` |
| **pmax-coder** | CLI only (via `coder` alias) | Development assistant, no media | (see profile config) |
| **pmax-ops-observer** | Cron-driven reports | Ops dashboards + health reports, no media | (see profile config) |

Note on names: the **profile** `pmax-content` (article reviewer) is not the same thing as the **skill** `pmax-content/` (copywriter, used by Tarek and Mousa). Same name, different roles. The profile handles n8n email → review. The skill writes captions/ads/emails when Tarek or Mousa asks for copy.

## Skill kit (four capabilities, shared across broad-operator profiles)

These skills are loaded by pmax-tarek and pmax-mousa. Dareen has a narrower lane into the same backend (see below).

| Skill | What it does | Backend |
|---|---|---|
| `pmax-content` | Writes captions, ads, emails, reel scripts, GMB posts (voice + format library) | LLM only — no backend |
| `pmax-image` | Generates AI images via FAL (Ideogram 3 / FLUX 2 Pro / Nano Banana Pro) | `image_tool.py` → task_server → image_worker → FAL |
| `pmax-video` | Generates video via FAL (Kling v3 Pro / Seedance 1 Pro / Veo 3 / Kling i2v) — text-to-video + image-to-video | `video_tool.py` → task_server → image_worker → FAL |
| `pmax-design` | Composites headline + subtitle on designer-made branded PNG templates | `~/Projects/design-agent/design_agent.py` (Pillow, no API) |

## Shared backend

All async render skills (image, video) go through the **same pipeline**:

```
Skill CLI (image_tool.py / video_tool.py / dareen_task_cli.py)
        │ POST /tasks (kind=image_brief | video_brief | social_post)
        │ POST /tasks/{id}/request-render
        ▼
task_server (Studio localhost:7439, launchd com.majana.task-server)
        │ enqueue in tasks.db
        ▼
image_worker (Studio, launchd com.majana.image-worker)
        │ polls every 5s, claims queued tasks
        │ dispatches on render_mode → FalRouterBackend | TemplateComposeBackend
        ▼
  ├─ image:            FAL image endpoint → .jpg/.png → assets/images/YYYY-MM/
  ├─ video:            FAL video endpoint → .mp4    → assets/videos/YYYY-MM/
  └─ template_compose: local Pillow compose (design_agent) → .png → assets/templates/YYYY-MM/
```

The worker's `MODEL_CATALOG` is the single source of truth for FAL short-name → endpoint + kind (image | video). Add new FAL models there, not in the skill CLIs. Template jobs use the sentinel `render_model = "template/v1"` and dispatch on `render_metadata.render_mode = "template_compose"` to the local backend (no FAL call).

## Canonical render modes (brief_schema.VALID_RENDER_MODES)

Enforced by `~/mem0-server/brief_schema.py` on every inbound brief.

| `render_mode` | Pipeline | Status |
|---|---|---|
| `image` | task_server → image_worker → FAL image model | ✅ live |
| `video` | task_server → image_worker → FAL video model | ✅ live |
| `template_compose` | pmax-design Pillow compositor via `TemplateComposeBackend` (source_mode=template) | ✅ plumbing live (2026-04-18) — mock template only, onboarding real client templates is next |
| `photo_compose` | Same backend, `source_mode=photo` — client photo + brand_kit overlays (contrast + logo + CTA) | ✅ live (2026-04-18) — Lux smoke passed end-to-end via Dareen wrapper AND `design_tool.py generate --image`. Local-path intake only in v1. |
| `none` | text-only post, no render step | ✅ live |

Legacy vendor-specific names (`higgsfield_image`, `higgsfield_video`, `higgsfield-soul`, `soul`) were removed on 2026-04-18 when the agency moved fully to FAL. If an older client YAML still references them, re-run the migration note at the bottom.

## Env vars every media skill expects

Set in each profile's `.env` (`~/.hermes/profiles/<profile>/.env`):
- `TASK_SERVER_URL=http://127.0.0.1:7439`
- `TASK_TOKEN_FILE=/Users/majana-agent/.hermes/profiles/<profile>/.task_token`
- `FAL_KEY=…` (optional for direct fallback; the render worker reads its own `~/mem0-server/.env` FAL_KEY by default)

## Routing — when agent picks which skill

| User intent | Skill |
|---|---|
| "Write me a caption / ad / email / reel script" | `pmax-content` |
| "Generate / make / create an image" | `pmax-image` |
| "Make a post in our brand style" (template-based) | `pmax-design` |
| "Animate / make a reel / turn this into a video" | `pmax-video` |

Agent picks by matching intent. Content request ≠ image render. Design-compose ≠ FAL call. One SKILL.md per capability = clean routing, clear failure modes.

## Adding a client brand template (for pmax-design)

Currently only the `mock` profile is installed. To add a real client:
1. Drop the designer-made PNG at `~/Projects/design-agent/templates/<client-slug>.png` (1080×1080 recommended)
2. Copy `configs/EXAMPLE.yaml` → `configs/<client-slug>.yaml`, fill in text-box pixel coords
3. Test: `python3.11 ~/Projects/design-agent/design_agent.py <client-slug> "test headline"`

## Dareen's narrow lane

Dareen's surface is **WhatsApp, client-facing**. She uses the same backend (task_server + image_worker) but via a restricted wrapper (`~/.hermes/profiles/pmax-dareen/bin/dareen_task_cli.py`) that:

- Reads `$TASK_SERVER_URL` + `$TASK_TOKEN_FILE` from the Hermes profile env — never echoes the token
- Rejects stale vendor names (no `higgsfield_*`)
- Rejects model/mode mismatches (e.g. `video` + `ideogram-3`)
- Surfaces `render_mode=template_compose` as "not wired yet" rather than silently failing

Policy overlay lives at `~/.hermes/profiles/pmax-dareen/policy.yaml`:
- `daily_spend_cap_usd: 2.00`
- `allowed_clients: [pmax, woodpecker, speedyway, tint-near-me, nail-box, lux-barbershop, kiddos-urgent-care]`
- `tiers: [draft, review]` — no `publish` tier (that's Mousa's alone)
- `blocked_actions_override: [write_global_mem0, edit_other_profiles, read_credentials, launchctl, git_push]`

## Toolset hardening (2026-04-18)

All four content-lane profiles now use `[terminal, web]` only — `file` toolset removed. Wrappers (`image_tool.py`, `video_tool.py`, `dareen_task_cli.py`) handle env + auth internally, so no profile needs raw file-tool access. Each profile's `config.yaml` has a comment documenting the rationale.

## Architecture summary

- **All services live on Studio** — MacBook can be closed, agents keep working
- `com.majana.task-server` — HTTP queue + DB + auth (Studio localhost:7439)
- `com.majana.image-worker` — render dispatcher (Studio, polls every 5s). Two backends:
  - `FalRouterBackend` — FAL image + video (add new models in `MODEL_CATALOG`)
  - `TemplateComposeBackend` — local Pillow via `design_agent.compose_brief()`
- `TEMPLATE_COMPOSE_ENABLED = True` flag in `image_worker.py` — single-line rollback if needed
- Assets: `~/mem0-server/assets/{images,videos,templates}/YYYY-MM/`
- Cache: `~/mem0-server/cache/images/*.json` (prompt-hash dedup, 30-day TTL — FAL only; template_compose is uncached in v1)

**Migrations:**
- 2026-04-16 — task_server + image_worker moved MacBook → Studio. `mem0-server` (Qdrant memory) still on MacBook, graceful-fails if unreachable.
- 2026-04-18 — purged all Higgsfield / `soul` vendor aliases from live code; flattened client-card schema to neutral `preferred_image_model` / `preferred_video_model`; hardened toolsets; installed Dareen wrapper.
- 2026-04-18 — wired `template_compose` end-to-end: `TemplateComposeBackend` in worker, `spend_tracker` ledger entry (`template/v1: $0`), Dareen wrapper + new `pmax-design/scripts/design_tool.py` for Tarek/Mousa. Mock template verified end-to-end; real client templates pending designer delivery.
- 2026-04-18 — surgically installed Nous's `baoyu-infographic` skill (21 layouts × 21 styles; commit `65c0a30a` upstream; extracted via `git archive`, no HEAD mutation — the hermes-agent repo is 427 commits behind upstream with 7 locally-modified files including the mem0 HTTP shim, so a plain `git pull` was deliberately NOT done). Disabled on pmax-dareen/content/coder/ops-observer via `skills.disabled`; enabled on pmax-tarek/mousa.
