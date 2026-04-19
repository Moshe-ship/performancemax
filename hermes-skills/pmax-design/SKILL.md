---
name: pmax-design
description: Composite headline + subtitle onto branded PNG templates OR directly onto client-supplied photos via the shared task_server pipeline. Local Pillow compositor — no FAL, zero render cost. Two modes (template_compose + photo_compose) behind one wrapper.
version: 3.0.0
author: Mousa Abu Mazin
license: MIT
platforms: [macos, linux]
prerequisites:
  env_vars: [TASK_SERVER_URL, TASK_TOKEN_FILE]
metadata:
  hermes:
    tags: [design, template, compose, branded, gmb, social, pillow, photo, client-photo]
---

# PMAX Design — branded composer (template + photo)

**STRICT PROTOCOL — READ BEFORE ANY TOOL CALL**

1. **ONLY call `scripts/design_tool.py`.** Do NOT invent curl commands; the script
   handles auth, the brief shape, and the task lifecycle correctly.
2. **NEVER `cat ~/.hermes/secrets/.task_token`** — the wrapper reads the token from
   `$TASK_TOKEN_FILE` without echoing it.
3. **NEVER claim a template was rendered** unless the wrapper printed
   `✓ completed — file://...`. Then verify with `ls -la <path>` before telling the
   user the file exists.
4. If the wrapper exits non-zero, **tell the user the real error.** Do not fall back
   to `pmax-image` — they are different skills with different voice+brand intent.

## When to use this skill

- Brand-template posts with a consistent visual identity (logo, colors, typography)
- GMB posts where the headline IS the post
- Announcements / promos where a designer-made PNG template already exists
- When you want deterministic output (same headline → same pixels)

## When NOT to use this skill

- Fresh AI-generated imagery → `pmax-image` (FAL)
- Video / reels → `pmax-video` (FAL)
- When no template PNG exists for the client → onboard one first, or use `pmax-image`

## Backend

- Same task_server + worker as `pmax-image` / `pmax-video`. One queue, one lifecycle.
- Render path: `render_mode="template_compose"` + `render_model="template/v1"` → the
  worker dispatches to `TemplateComposeBackend` (local Pillow) instead of FAL.
- Asset output: `~/mem0-server/assets/templates/YYYY-MM/task_<id>_<hash>.png`
- Cost: $0 per render (ledgered at 0.0 for volume tracking).

## How to invoke

### 1) Template compose (no --image) — headline on a fixed branded template

```bash
python3 ~/Projects/performancemax/hermes-skills/pmax-design/scripts/design_tool.py generate \
  --client "mock" \
  --headline "Spring special — 20% off" \
  --subtitle "Book before April 30"
```

Uses `~/Projects/design-agent/templates/<client>.png` as the background and draws text in the configured boxes. `render_mode=template_compose`.

### 2) Photo compose (`--image`) — headline + logo + CTA on top of a client photo

```bash
design_tool.py generate \
  --client lux-barbershop \
  --headline "Sharp cuts, honest prices" \
  --subtitle "Walk-ins welcome in Alpharetta" \
  --image /path/to/client/haircut.jpg
```

The moment `--image` is present, the wrapper flips to `render_mode=photo_compose`. The photo becomes the base layer, and the client-card `brand_kit` drives the overlay stack:

- Contrast overlay (darken text zone for legibility) — optional per brand_kit
- Logo (transparent PNG at configured corner) — optional per brand_kit
- CTA pill (text + color + position) — optional per brand_kit

Rules:
- **Local path only in v1.** URLs rejected.
- `--image` path is canonicalized via `~/mem0-server/asset_intake.py` to `~/mem0-server/assets/uploads/YYYY-MM/<client>/<hash>.<ext>` before submission — deterministic dedupe.
- Text-box coords scale from a 1080 reference canvas to the actual photo dimensions, so any aspect ratio works.

### 3) Override the template / template_id

```bash
design_tool.py generate --client mock --template-id lux-barbershop --headline "X"
```

Rare — prefer one template per client. Useful for A/B tests.

## brand_kit schema (client card)

Add to `~/.hermes/profiles/pmax-dareen/clients/<slug>.yaml` (or the equivalent
for Tarek / Mousa when they wire client-specific brand data):

```yaml
brand_kit:
  contrast_overlay:
    enabled: true
    zone: bottom         # top | bottom | left | right | full
    strength: 0.55       # 0.0-1.0 opacity of the dark rectangle
  logo:
    path: /Users/majana-agent/mem0-server/assets/logos/<client>.png
    position: top-right  # corners + top-center/bottom-center/center
    scale: 0.14          # fraction of canvas width
  cta:
    text: "Book Now"
    color: "#D4A85C"
    text_color: "#111111"
    position: bottom-right
    font_size: 28
```

All three sub-blocks are optional. Missing block → overlay skipped silently. Missing logo file → skipped. Invalid position → defaults to top-left.

### 3) Fire and return (don't block on render)

```bash
design_tool.py generate --client mock --headline "X" --no-wait
# returns immediately with task_id; poll with `status`
```

### 4) List templates (honest view of what's actually wired)

```bash
design_tool.py list-templates
```

Output shows `✓` for templates with real PNGs installed, `⚠ PNG missing` for
configs pointing at TODO placeholder names. **Do not try to render against a
`⚠` template — the worker will fail with FileNotFoundError.**

### 5) Status / list

```bash
design_tool.py status 42
design_tool.py list --client mock --limit 5
```

## Template onboarding (adding a new client)

1. Designer delivers `1080×1080` PNG (or any square; the compositor respects it).
2. Drop at `~/Projects/design-agent/templates/<client-slug>.png`.
3. Copy `~/Projects/design-agent/configs/EXAMPLE.yaml` → `configs/<client-slug>.yaml`.
4. Fill in text-box pixel coordinates (`x`, `y`, `width`, `height`, `font`,
   `font_size`, `color`, `align`, `rtl`).
5. Update `template_file:` in the yaml to point at the new PNG (drop the `TODO-` prefix).
6. Test: `design_tool.py generate --client <slug> --headline "test"`.
7. Verify with `design_tool.py list-templates` that the new client shows `✓`.

## Aspect ratio note

`--aspect` is NOT a template-compose option. Templates already have fixed
dimensions (the PNG defines them). Aspect-ratio routing is for FAL-based
image/video jobs. If you need a different aspect ratio, onboard a separate
template PNG at those dimensions.

## Under the hood

- `design_tool.py` is a thin wrapper — it calls task_server directly.
- `image_worker.py` has a `TemplateComposeBackend` class that dynamically loads
  `~/Projects/design-agent/design_agent.py::compose_brief()`.
- `compose_brief()` is a pure function: `(brief: dict, asset_path: Path) -> str`.
- RTL/Arabic is supported if `arabic_reshaper` + `python-bidi` are installed.
- `COMPOSITOR_VERSION` in `design_agent.py` bumps when text-rendering behavior changes.

## Current live-template inventory (2026-04-18)

**Only `mock` has a real PNG.** The other 3 configs (`kiddos-urgent-care`,
`lux-barbershop`, `nail-box`) have pending-designer placeholder paths.

Honest status: **template_compose plumbing is done; product-done is pending
real client templates being delivered by the designer.**
