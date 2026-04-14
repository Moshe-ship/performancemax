#!/bin/bash
# Hardened PMax blog auto-publisher
# Usage: auto_blog.sh [--dry-run]
# Env: DEBUG=1 → bash -x trace to LOGFILE
#      LLM_TIMEOUT=<sec> → max time for LLM call (default 600s)

set -euo pipefail

cd "$(dirname "$0")"

DATE=$(date +%Y-%m-%d)
BLOG_DIR="src/content/blog"
SHARED="$HOME/Projects/shared"
DRY_RUN="${1:-}"
LOGFILE="auto_blog.log"
LLM_TIMEOUT="${LLM_TIMEOUT:-600}"

# Redirect all output to log AND stdout
exec > >(tee -a "$LOGFILE") 2>&1

echo "=========================================="
echo "[$DATE $(date +%H:%M:%S)] auto_blog.sh start"
echo "  dry_run=$DRY_RUN  llm_timeout=${LLM_TIMEOUT}s"
echo "=========================================="

# Optional bash tracing
if [[ "${DEBUG:-0}" == "1" ]]; then
  echo "[DEBUG mode: bash -x tracing]"
  set -x
fi

# Step 1: Check if already published today
echo "[step 1/8] Checking if already published today"
if git log --oneline --since="$DATE" 2>/dev/null | grep -q "blog:"; then
  echo "  SKIP: Already published today"
  exit 0
fi
echo "  OK: no blog commit today"

# Step 2: Collect existing titles (handle empty dir)
echo "[step 2/8] Collecting existing blog titles"
if compgen -G "$BLOG_DIR/*.md" > /dev/null; then
  EXISTING=$(grep -h "^title:" "$BLOG_DIR"/*.md 2>/dev/null \
    | sed 's/.*title: *"//;s/"$//' \
    | tr '\n' ', ' \
    | cut -c1-500)
  echo "  OK: found $(echo "$EXISTING" | tr ',' '\n' | wc -l | tr -d ' ') existing titles"
else
  EXISTING=""
  echo "  OK: blog dir empty or missing, starting fresh"
fi

# Step 3: Check local LLM endpoint
echo "[step 3/8] Checking local LLM endpoint"
if ! curl -sf --max-time 5 http://localhost:8000/v1/models > /dev/null; then
  echo "  FAIL: local LLM (oMLX) not responding on port 8000"
  exit 2
fi
echo "  OK: oMLX responding"

# Step 4: Build prompt
echo "[step 4/8] Building prompt"
PROMPT="Write a complete SEO blog post in markdown for performancemaxagency.com.

EXISTING TITLES (avoid duplicates): $EXISTING

Rules:
- Author: Musa the Carpenter — expert, accessible, direct, story-driven
- Target: local business owners (restaurants, plumbers, dentists, contractors)
- 1500-2000 words
- Real statistics and actionable advice
- End with CTA for Performance MAX Agency
- Start with frontmatter:
---
title: \"Your Title\"
description: \"120-160 char meta description\"
date: \"$DATE\"
author: \"Musa the Carpenter\"
image: \"/blog-images/$DATE.jpg\"
tags: [\"tag1\", \"tag2\"]
---

Also on the VERY LAST LINE output: IMAGE_QUERY: your english search terms for a stock photo

Write the complete post now."

# Step 5: Call LLM (capture stdout + stderr separately, simple synchronous call)
echo "[step 5/8] Calling local LLM (timeout: ${LLM_TIMEOUT}s)"
LLM_STDOUT=$(mktemp)
LLM_STDERR=$(mktemp)
set +e
PYTHONUNBUFFERED=1 python3 "$SHARED/generate_blog.py" "$PROMPT" > "$LLM_STDOUT" 2> "$LLM_STDERR" &
LLM_PID=$!
SECONDS_WAITED=0
while kill -0 "$LLM_PID" 2>/dev/null; do
  sleep 5
  SECONDS_WAITED=$((SECONDS_WAITED + 5))
  if [ "$SECONDS_WAITED" -ge "$LLM_TIMEOUT" ]; then
    kill -TERM "$LLM_PID" 2>/dev/null
    sleep 2
    kill -KILL "$LLM_PID" 2>/dev/null
    echo "  FAIL: LLM call timed out after ${LLM_TIMEOUT}s"
    rm -f "$LLM_STDOUT" "$LLM_STDERR"
    exit 8
  fi
done
wait "$LLM_PID"
LLM_EXIT=$?
RESULT=$(cat "$LLM_STDOUT")
set -e

if [ "$LLM_EXIT" -ne 0 ]; then
  echo "  FAIL: LLM call exited with code $LLM_EXIT"
  echo "  stderr:"
  sed 's/^/    /' "$LLM_STDERR" | head -30
  rm -f "$LLM_STDOUT" "$LLM_STDERR"
  exit 3
fi

if [ -z "$RESULT" ]; then
  echo "  FAIL: LLM returned empty string"
  echo "  stderr:"
  sed 's/^/    /' "$LLM_STDERR" | head -30
  rm -f "$LLM_STDOUT" "$LLM_STDERR"
  exit 4
fi

echo "  OK: LLM returned $(echo "$RESULT" | wc -w | tr -d ' ') words"
rm -f "$LLM_STDOUT" "$LLM_STDERR"

# === FRONTMATTER VALIDATION GUARD ===
# Hardening after blog-2026-04-12 incident (Gemma dumped 2122 lines of
# reasoning text, committed blind, blocked CI for 4 days). Strip reasoning
# blocks, trim to frontmatter fence, verify required keys. Die hard if not.
echo "[step 5b/8] Validating frontmatter"
RESULT=$(printf '%s' "$RESULT" | python3 "$SCRIPT_DIR/../shared/strip_reasoning.py" 2>/dev/null || printf '%s' "$RESULT")

MISSING=""
for key in title description date author; do
    if ! printf '%s' "$RESULT" | grep -qE "^${key}: "; then
        MISSING="$MISSING $key"
    fi
done

if [ -n "$MISSING" ]; then
    REJECT_DIR="$SCRIPT_DIR/rejected-blogs"
    mkdir -p "$REJECT_DIR"
    REJECT_FILE="$REJECT_DIR/reject-$DATE-$(date +%H%M%S).md"
    printf '%s' "$RESULT" > "$REJECT_FILE"
    echo "  FAIL: LLM output missing required frontmatter:$MISSING"
    echo "  raw output saved to $REJECT_FILE for forensics"
    echo "  NOT committing — the build would fail in CI anyway"
    exit 8
fi
echo "  OK: frontmatter validated (title, description, date, author all present)"
# === END FRONTMATTER VALIDATION GUARD ===

# Step 6: Extract image query and slug (all pipelines guarded)
echo "[step 6/8] Extracting image query and slug"
set +e
set +o pipefail

IMAGE_QUERY=$(echo "$RESULT" | grep "^IMAGE_QUERY:" | sed 's/IMAGE_QUERY: *//')
[ -z "$IMAGE_QUERY" ] && IMAGE_QUERY="local business digital marketing"
RESULT=$(echo "$RESULT" | grep -v "^IMAGE_QUERY:")

# Try multiple title extraction strategies
RAW_TITLE=$(echo "$RESULT" | grep -m1 -E '^title:' | sed 's/title: *//;s/^"//;s/"$//')
if [ -z "$RAW_TITLE" ]; then
  RAW_TITLE=$(echo "$RESULT" | grep -m1 -E '^# ' | sed 's/^# *//')
fi

if [ -n "$RAW_TITLE" ]; then
  SLUG=$(printf '%s' "$RAW_TITLE" \
    | tr '[:upper:]' '[:lower:]' \
    | tr ' ' '-' \
    | tr -cd 'a-z0-9-' \
    | cut -c1-60)
else
  SLUG=""
fi
[ -z "$SLUG" ] && SLUG="blog-$DATE"

set -e
set -o pipefail
echo "  OK: slug=$SLUG  title='$RAW_TITLE'  image_query='$IMAGE_QUERY'"

# Step 7: Fetch image (best-effort)
echo "[step 7/8] Fetching image"
IMAGE_PATH="/tmp/pmax_blog_$DATE.jpg"
IMG_STDERR=$(mktemp)
if python3 "$SHARED/fetch_image.py" "$IMAGE_QUERY" "$IMAGE_PATH" pmax 2> "$IMG_STDERR"; then
  if [ -f "$IMAGE_PATH" ] && [ -s "$IMAGE_PATH" ]; then
    mkdir -p public/blog-images
    cp "$IMAGE_PATH" "public/blog-images/$DATE.jpg"
    echo "  OK: image fetched $(ls -lh "$IMAGE_PATH" | awk '{print $5}')"
  else
    echo "  WARN: fetch script succeeded but no image file"
  fi
else
  echo "  WARN: image fetch failed (continuing):"
  sed 's/^/    /' "$IMG_STDERR" | head -5
fi
rm -f "$IMG_STDERR"

# Step 8: Dry run or publish
if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "[step 8/8] DRY RUN — not publishing"
  WORDS=$(echo "$RESULT" | wc -w | tr -d ' ')
  echo "  slug: $SLUG"
  echo "  words: ~$WORDS"
  echo "  preview:"
  echo "$RESULT" | head -8 | sed 's/^/    /'
  exit 0
fi

echo "[step 8/8] Publishing to git"
mkdir -p "$BLOG_DIR"
echo "$RESULT" > "$BLOG_DIR/$SLUG.md"
git add "$BLOG_DIR/$SLUG.md" public/blog-images/ 2>/dev/null || true

if git diff --cached --quiet; then
  echo "  FAIL: nothing to commit (slug=$SLUG may already exist)"
  exit 5
fi

if ! git commit -m "blog: $SLUG"; then
  echo "  FAIL: git commit failed"
  exit 6
fi

if ! git push origin main; then
  echo "  FAIL: git push failed"
  exit 7
fi

echo "  OK: PUBLISHED $SLUG"
echo "=========================================="
echo "[$(date +%H:%M:%S)] auto_blog.sh done"
echo "=========================================="

# ── Self-scoring (added by blog_selfscore_v1.sh) ───────────────────────────
# After successful publish, submit the blog body to the review webhook.
# The webhook stores the score in SQLite with source="<NAME>-selfscore".
selfscore_blog() {
  local source_name="$1"
  local slug="$2"
  local body_file="$3"
  local word_count="$4"

  if [ ! -f "$body_file" ]; then
    return 0
  fi
  if [ ! -f "$HOME/.webhook_token" ]; then
    return 0
  fi

  local token
  token=$(cat "$HOME/.webhook_token")
  local payload
  payload=$(python3 -c "
import json, sys
body = open(sys.argv[1]).read()
print(json.dumps({
    keyword: sys.argv[2],
    article: body,
    word_count: int(sys.argv[3]),
    seo_score: 0,
    title_tag: ,
    meta_description: ,
    source: sys.argv[4] + -selfscore,
}))
" "$body_file" "$slug" "$word_count" "$source_name")

  local rid="${source_name}-selfscore-$(date +%Y%m%d-%H%M%S)"
  local response
  response=$(curl -sf -X POST "http://100.118.222.70:7438/review" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -H "X-Request-ID: $rid" \
    -d "$payload" 2>/dev/null || echo "{}")

  local status
  status=$(echo "$response" | python3 -c "import sys,json;print(json.load(sys.stdin).get(\"status\",\"unknown\"))" 2>/dev/null || echo "error")
  echo "  selfscore: status=$status request_id=$rid"
}
# ─────────────────────────────────────────────────────────────────────────────

selfscore_blog "pmax" "$SLUG" "$BLOG_DIR/$SLUG.md" "$(wc -w < "$BLOG_DIR/$SLUG.md" | tr -d " ")"
