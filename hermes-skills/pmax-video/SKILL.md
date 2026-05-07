---
name: pmax-video
description: Generate short videos (ads, reels, product motion) via FAL.ai — routed through the shared task_server + image_worker pipeline. Handles text-to-video AND image-to-video (animate an existing image).
version: 1.0.0
author: Mousa Abu Mazin
license: MIT
platforms: [macos, linux]
prerequisites:
  env_vars: [TASK_SERVER_URL, TASK_TOKEN_FILE]
metadata:
  hermes:
    tags: [video, generation, fal, reel, social, animation, agency]
---

# Tarek Video Generator

**⚠️ STRICT PROTOCOL — READ BEFORE ANY TOOL CALL**

When the user asks for a video, a reel, an animation, a drift clip, a motion shot, a product demo video, or ANY AI-generated moving image:

1. **ONLY call one of the two shell commands below** (text-to-video OR from-image). Do not invent your own.
2. **NEVER `curl` a task_server endpoint yourself.** The script already does that correctly.
3. **NEVER call `delegate_task` for video generation.** There is NO other working video backend on this machine. Delegation will hallucinate success and no file will exist.
4. **NEVER use fal_client directly in Python.** Use this skill. It handles auth, caching, spend caps, DB logging.
5. **NEVER claim a video was generated** unless `video_tool.py` printed a JSON line containing `"render_state": "completed"` AND `"file_path": "/Users/majana-agent/..."` — then verify with `ls -la <file_path>` before telling the user it exists.
6. If the command fails (non-zero exit, timeout, error JSON), **tell the user the real error**. Do not fall back to another tool. Do not fabricate.

## When to use this skill

- "Make me a reel about X"
- "Turn this image into a video"
- "Generate a 5-second clip of Y"
- "Animate the car drifting"
- Anything involving motion, drift, camera movement, animation, reels, stories

## Backend

- **Server**: `$TASK_SERVER_URL` (set in pmax-tarek `.env`, points to Studio localhost task_server at `http://127.0.0.1:7439`)
- **Auth**: Bearer token from `$TASK_TOKEN_FILE` (set in `.env`)
- **Worker**: `~/mem0-server/image_worker.py` — same worker dispatches image + video based on model name
- **Output dir**: `/Users/majana-agent/mem0-server/assets/videos/YYYY-MM/task_N_<hash>.mp4`

## How to invoke

### 1) Text-to-video — generate from a prompt

```bash
python3 ~/Projects/performancemax/hermes-skills/pmax-video/scripts/video_tool.py text-to-video \
  --client "tint-near-me" \
  --prompt "A black Porsche 911 drifting in a neon-lit garage, smoke clouds rising, cinematic slow-mo" \
  --model kling-v3-pro \
  --aspect 16:9 \
  --duration 5s
```

### 2) Image-to-video — animate an existing image

```bash
python3 ~/Projects/performancemax/hermes-skills/pmax-video/scripts/video_tool.py from-image \
  --client "tint-near-me" \
  --image /Users/majana-agent/mem0-server/assets/images/2026-04/task_14_66ca091ceed789cb.jpg \
  --prompt "The car drifts, making donuts, fire bursting from the tires" \
  --model kling-v3-i2v \
  --aspect 16:9 \
  --duration 5s
```

**Use image-to-video whenever the user references a previously generated image.** Much more coherent than regenerating from scratch.

## Output shape

On success:
```json
{"task_id": 15, "render_state": "completed",
 "render_asset_url": "file:///Users/majana-agent/mem0-server/assets/videos/2026-04/task_15_<hash>.mp4",
 "file_path": "/Users/majana-agent/mem0-server/assets/videos/2026-04/task_15_<hash>.mp4",
 "model": "kling-v3-i2v", "kind": "video"}
```

**The script uploads the video to the user's Telegram automatically** when `TELEGRAM_BOT_TOKEN` + `TELEGRAM_HOME_CHANNEL` are set (they are). You do NOT add `MEDIA:` tags. You do NOT curl sendVideo. Check `telegram_delivery.ok` in the JSON — if `true`, just confirm briefly to the user ("Done — video sent"). If `false`, relay the real error.

## Models — when to pick which

### Text-to-video
| Model | Strength | Duration | Notes |
|---|---|---|---|
| `kling-v3-pro` (default) | Strong motion, reliable quality | 5s / 10s | Best all-rounder |
| `seedance-1-pro` | Cinematic camera moves | 5s / 10s | ByteDance, smooth |
| `veo-3` | Highest fidelity + native audio | 5s | Google DeepMind, premium |

### Image-to-video
| Model | Strength | Notes |
|---|---|---|
| `kling-v3-i2v` (default) | Faithful to source image, strong motion | Best default for animating renders |
| `luma-ray2-i2v` | Strong camera motion / parallax | Good for cinematic scene setting |
| `minimax-i2v` | Fast iteration | Cheaper, lower fidelity |

## Aspect ratios

| Ratio | Use |
|---|---|
| `16:9` (default) | YouTube, landscape, web ads |
| `9:16` | Instagram reels, TikTok, stories |
| `1:1` | Instagram feed, square ads |

## Durations

- `5s` (default, cheaper, faster) — works on all video models
- `10s` — supported by Kling + Seedance; **not supported** on Veo 3

## Failure modes

- **`SPEND_CAP_EXCEEDED`** — Tarek hit the daily budget. Report to user.
- **`render_error`** — model refused prompt (unsafe content), FAL outage, or image-to-video source unreachable. Retry with rephrased prompt or different model.
- **Timeout** (default 300s) — video jobs can be slow. Use `--no-wait` + `status <task_id>` if expecting slow renders.

## Related

- `pmax-image` — sibling skill for static images (use it first to generate a base image, then animate it here)
- `~/mem0-server/image_worker.py` — the shared render worker on Studio
- `~/mem0-server/task_server.py` — HTTP API, Studio port 7439
