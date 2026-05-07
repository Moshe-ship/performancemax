---
name: pmax-image
description: Generate branded images (social posts, ads, hero shots) via FAL.ai — routed through the shared task_server + image_worker pipeline. Use when Tarek asks for an image, poster, social-post graphic, or product shot.
version: 1.0.0
author: Mousa Abu Mazin
license: MIT
platforms: [macos, linux]
prerequisites:
  env_vars: [TASK_SERVER_URL, TASK_TOKEN_FILE]
metadata:
  hermes:
    tags: [image, generation, fal, social, design, agency]
---

# Tarek Image Generator

**⚠️ STRICT PROTOCOL — READ BEFORE ANY TOOL CALL**

When the user asks for an image, a poster, a social-post graphic, a hero shot, or ANY AI-generated picture:

1. **ONLY call this one shell command** (shown below under "How to invoke"). Do not invent your own.
2. **NEVER `curl` a task_server endpoint yourself.** The script already does that correctly.
3. **NEVER call `delegate_task` for image generation.** There is NO other working image backend on this machine. Delegation will hallucinate success and no file will exist.
4. **NEVER claim an image was generated** unless `image_tool.py generate` printed a JSON line containing `"render_state": "completed"` AND `"file_path": "/Users/majana-agent/..."` — then verify with `ls -la <file_path>` before telling the user it exists.
5. If the command fails (non-zero exit, timeout, error JSON), **tell the user the real error**. Do not fall back to another tool. Do not fabricate.

Submit structured image briefs to the shared render pipeline. Tarek's requests go through the SAME task_server + image_worker backend that Dareen uses — no duplicate infrastructure. Every render is cached by prompt hash, rate-limited by spend cap, and logged as a task row for replay.

## When to use this skill

Invoke when the user asks to:
- "Generate an image for <client> about <topic>"
- "Make me a social post graphic for <product>"
- "Create a hero shot of <subject>"
- "Render a 1:1 / 9:16 / 16:9 visual"
- Any request that needs an AI-generated image

## Backend

- **Server**: `$TASK_SERVER_URL` (already set in pmax-tarek profile `.env` — the agent's terminal inherits it). Do NOT hard-code an IP in commands; always reference the env var or leave the script to read it itself.
- **Auth**: Bearer token from `$TASK_TOKEN_FILE` (already set in `.env`).
- **Worker**: `~/mem0-server/image_worker.py` on Studio, launchd-managed (`com.majana.image-worker`)
- **Models** (via FalRouterBackend):
  - `ideogram-3` — text-safe default (social posts with headline text)
  - `flux-2-pro` — photorealistic hero / product shots
  - `nano-banana-pro` — text + photo hybrid

## How to invoke

**This is the ONLY command shape you may use for image generation.** Always invoke with the **absolute path** shown. The script reads `TASK_SERVER_URL` and `TASK_TOKEN_FILE` from the environment that Hermes has already loaded from `.env` — the env vars are ALREADY SET; do not export them yourself; do not hard-code any IP or fallback.

### Generate an image (default: wait for completion, return file path)

```bash
python3 ~/Projects/performancemax/hermes-skills/pmax-image/scripts/image_tool.py generate \
  --client "tint-near-me" \
  --prompt "professional product shot of PPF film being applied to a dark BMW hood, warm studio lighting, high detail" \
  --headline "Protect your paint from day one" \
  --model ideogram-3 \
  --aspect 1:1
```

Returns a JSON line on success:
```json
{"task_id": 42, "render_state": "completed", "render_asset_url": "file:///Users/mousaabumazin/mem0-server/assets/images/2026-04/task_42_abc123.png", "file_path": "/Users/majana-agent/mem0-server/assets/images/2026-04/task_42_abc123.png", "model": "ideogram-3"}
```

`file_path` is the Studio-local mirror, usable directly by the Telegram bridge.

### Async submit (return immediately, poll later)

```bash
python3 ~/Projects/performancemax/hermes-skills/pmax-image/scripts/image_tool.py generate --client X --prompt "..." --no-wait
# → {"task_id": 43, "render_state": "queued"}
python3 ~/Projects/performancemax/hermes-skills/pmax-image/scripts/image_tool.py status 43
```

### List recent renders

```bash
python3 ~/Projects/performancemax/hermes-skills/pmax-image/scripts/image_tool.py list --client tint-near-me --limit 5
```

## Style-reference (image-to-image) mode

When the user asks for "a new post in the same style as our previous one", "match the brand look", or "keep the layout but change the headline", use `--style-ref <path>` to remix an existing reference instead of generating from scratch. The worker auto-routes i2i briefs to `nano-banana-pro` regardless of the `--model` flag.

### Installed client style-reference folders (on Studio)

Each folder holds finished past posts that capture the client's brand look. Pick ONE that best matches the layout/style you want to echo, and pass its path:

| Client | Folder | Count |
|---|---|---|
| Nail Box | `/Users/majana-agent/Projects/performancemax/client-style-refs/nail-box/` | 9 |
| Lux Barbershop | `/Users/majana-agent/Projects/performancemax/client-style-refs/lux-barbershop/` | 8 |
| Speedway | `/Users/majana-agent/Projects/performancemax/client-style-refs/speedyway/` | 8 |
| Tint Near | `/Users/majana-agent/Projects/performancemax/client-style-refs/tint-near-me/` | 2 |
| Kiddos Urgent Care | `/Users/majana-agent/Projects/performancemax/client-style-refs/kiddos-urgent-care/` | 8 |

### Example (i2i for Nail Box)

```bash
REF=$(ls /Users/majana-agent/Projects/performancemax/client-style-refs/nail-box/ | head -1)
python3 ~/Projects/performancemax/hermes-skills/pmax-image/scripts/image_tool.py generate \
  --client nail-box \
  --prompt "Same brand style and layout. New headline: 'BOOK FOR APRIL'. Same palette, composition." \
  --headline "BOOK FOR APRIL" \
  --model nano-banana-pro \
  --aspect 1:1 \
  --style-ref "/Users/majana-agent/Projects/performancemax/client-style-refs/nail-box/$REF"
```

Picking guidance: `ls` the folder, pick a filename that matches intent. Rotate refs to keep variety, don't re-remix the same one every time.

⚠️  **TEMPORARY** until designer delivers blank brand template masters. Once they arrive, `pmax-design` is the primary path for branded posts; `pmax-image --style-ref` stays as fallback for off-template one-offs.

## Prompt writing guidance

The **prompt** is sent directly to FAL — it should describe the image, not the task. Good patterns:

- Lead with the subject: "A sleek black BMW ..."
- Include lighting/mood: "... warm golden-hour light, shallow depth of field"
- Mention composition: "... centered, 1:1 aspect ratio"
- For text-on-image (Ideogram-3 strength): put the exact text in quotes: `'Bold headline reading "Book Your Slot"'`

**Headline/subtitle** are separate — they go into render_metadata for downstream composition but are not baked into the image unless the prompt explicitly includes them.

## Models: when to pick which

| Model | Best for | Cost | Text rendering |
|---|---|---|---|
| `ideogram-3` | Social posts with headline text, announcements, quote cards | low | **excellent** |
| `flux-2-pro` | Hero shots, product photography, lifestyle imagery | medium | okay |
| `nano-banana-pro` | Mixed scenes needing both photorealism and readable text | medium | good |

Default to `ideogram-3` unless the user specifically asks for photorealism.

## Aspect ratios

| Ratio | Use |
|---|---|
| `1:1` | Instagram feed, Facebook, square ads |
| `9:16` | Instagram/TikTok reels, stories |
| `16:9` | YouTube thumbnails, landscape banners |
| `4:5` | Instagram portrait feed (most engagement) |

## What the user gets back

- JSON response from `generate` includes `file_path`, `render_asset_url`, and `telegram_delivery`.
- **The script uploads the image to the user's Telegram automatically** when `TELEGRAM_BOT_TOKEN` + `TELEGRAM_HOME_CHANNEL` are set (they are, in Tarek's .env). You do NOT need to add `MEDIA:` tags, do NOT curl sendPhoto yourself, do NOT paste the file path for the user. The image has already been delivered by the time you read the JSON.
- If `telegram_delivery.ok` is `true`, the image is in the user's Telegram. Just confirm success briefly ("Done — sent you the image").
- If `telegram_delivery.ok` is `false`, tell the user the real error — do not retry via other channels.
- The file also lives on disk at `file_path` for downstream use (e.g. feeding into `pmax-video --image <path>` for image-to-video).

## Failure modes

- **`SPEND_CAP_EXCEEDED`**: Tarek's daily budget hit. Policy override or wait for the daily reset.
- **`render_error`**: Model rejected the prompt (unsafe content) or fal.ai was down. Retry with a rephrased prompt.
- **Timeout**: Default 120s wait. Image worker is async — use `--no-wait` + poll if you expect slowness.

## Related

- `~/mem0-server/image_worker.py` — the render worker (launchd)
- `~/mem0-server/brief_schema.py` — canonical brief shape
- `~/mem0-server/task_server.py` — HTTP API, port 7439
- Dareen's skill pattern (for reference): same backend, different profile
