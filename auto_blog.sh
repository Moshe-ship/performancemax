#!/bin/bash
# Hardened PMax blog auto-publisher
# Usage: auto_blog.sh [--dry-run]
# Env: DEBUG=1 → bash -x trace to LOGFILE
#      LLM_TIMEOUT=<sec> → max time for LLM call (default 600s)

set -euo pipefail
# ERR-TRAP-v1
trap 'ec=$?; echo "[ERR] exit=$ec line=$LINENO cmd=${BASH_COMMAND}" >&2; exit $ec' ERR

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

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

# Step 0: sync working tree with origin so runs never diverge (root-cause fix 2026-07-05)
if [ "$DRY_RUN" != "--dry-run" ]; then
  echo "[step 0/8] Syncing with origin/main"
  git fetch origin main --quiet 2>/dev/null || true
  git reset --hard origin/main 2>/dev/null || true
fi

# Step 1: Check if already published today (FORCE=1 bypasses — for manual backfills)
echo "[step 1/8] Checking if already published today"
if [ "${FORCE:-0}" != "1" ] && git log --oneline --since="$DATE" 2>/dev/null | grep -q "blog:"; then
  echo "  SKIP: Already published today (set FORCE=1 to override)"
  exit 0
fi
echo "  OK: proceeding (force=${FORCE:-0})"

# Step 2: Collect existing titles (handle empty dir)
echo "[step 2/8] Collecting existing blog titles"
if compgen -G "$BLOG_DIR/*.md" > /dev/null; then
  # Full list (NOT truncated) so the model can actually avoid every existing title.
  EXISTING=$(grep -h "^title:" "$BLOG_DIR"/*.md 2>/dev/null \
    | sed 's/.*title: *"//;s/"$//' \
    | tr '\n' '|')
  echo "  OK: found $(printf '%s' "$EXISTING" | tr '|' '\n' | grep -c . ) existing titles"
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

# Step 3.5: Pick a distinct topic NOT already covered.
# Each entry is "keyword::persona::topic". persona ∈ {beauty, trades, general}
# and drives the voice/vocabulary in the prompt (Step 4). We skip any topic
# whose keyword already appears in an existing title, so the blog stops
# churning the same themes. Topics + hooks are grounded in the 2026-07 owner
# research (empty-chair economics, the FTC HomeAdvisor lead scandal, the
# vanity-metrics-vs-revenue distrust, real budget benchmarks).
echo "[step 3.5] Selecting a distinct topic"
TOPICS=(
  # ─── BEAUTY: nail salon / beauty spa / med-spa / barbershop (Nailbox, Lux — Alpharetta/Roswell/Milton) ───
  "dead on tuesdays::beauty::Why your salon is dead on Tuesdays and the three offers that actually fill the chairs"
  "fully booked::beauty::How to stay fully booked without slashing your prices"
  "charge your worth::beauty::How to raise your prices without losing your regulars"
  "client magnet::beauty::Become a client magnet: how to attract the clients you actually want"
  "slow season::beauty::Beat the January and late-summer slump: a salon owner's slow-season playbook"
  "rebooking::beauty::The rebooking habit that turns one-time clients into weekly regulars"
  "no-shows::beauty::How to stop no-shows and last-minute cancellations from wrecking your week"
  "salon reviews::beauty::How to get more 5-star reviews for your salon without begging for them"
  "how clients find a salon::beauty::How new clients actually pick a salon in 2026, and how to be the one they choose"
  "instagram bookings::beauty::Your Instagram looks great but the chairs are empty: turning followers into bookings"
  # ─── TRADES: window tint/PPF, auto, auto transport, carpentry, plumbing, HVAC, contractor (Kingdom, Tint Near Me, Speedy Way — DFW / Cary) ───
  "homeadvisor::trades::The FTC fined HomeAdvisor \$7.2M for junk leads: what it means if you still buy leads"
  "stop buying leads::trades::Stop renting leads you don't own: how to build a pipeline that's actually yours"
  "traffic but no calls::trades::Traffic up, phone silent: how to tell if your marketing is actually working"
  "what to spend::trades::What should a local service business actually spend on marketing? Real 2026 numbers"
  "more service calls::trades::How to get more service calls from Google without paying for junk leads"
  "shared leads::trades::Why the lead you paid for went to four other shops, and how to get exclusive ones"
  "reviews book jobs::trades::How more Google reviews turn into more booked jobs for your shop"
  "slow season calls::trades::How to keep the calls coming when your slow season hits"
  "shop website no calls::trades::Why your shop's website gets visitors but no calls, and how to fix it"
  "tint shop::trades::How a local tint shop books more cars without discounting"
  "shop not on google::trades::Why your shop isn't showing up on Google, and how to fix it this week"
  "prove marketing works::trades::The bank-account test: how to tell if your marketing is actually making you money"
  "agency red flags::trades::Seven red flags your marketing agency is quietly wasting your money"
  "near me not closest::trades::How to win 'near me' searches when you're not the closest shop"
  # ─── MORE BEAUTY ───
  "gbp appointments::beauty::The Google Business Profile setup that actually books appointments for your salon"
  "diy or hire salon::beauty::Should you market your salon yourself or hire someone? An honest breakdown"
  "walk-ins to regulars::beauty::How to turn first-time walk-ins into regulars who book every month"
)
EXISTING_LC=$(printf '%s' "$EXISTING" | tr '[:upper:]' '[:lower:]')
TOPIC=""; TOPIC_PERSONA="general"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  key="${line%%::*}"; rest="${line#*::}"
  persona="${rest%%::*}"; desc="${rest##*::}"
  if ! printf '%s' "$EXISTING_LC" | grep -qiF "$key"; then
    TOPIC="$desc"; TOPIC_PERSONA="$persona"; break
  fi
done < <(printf '%s\n' "${TOPICS[@]}" | sort -R)
# Fallback: if every keyword is covered, take any shuffled topic (parse persona too).
if [ -z "$TOPIC" ]; then
  line=$(printf '%s\n' "${TOPICS[@]}" | sort -R | head -1)
  rest="${line#*::}"; TOPIC_PERSONA="${rest%%::*}"; TOPIC="${rest##*::}"
fi
echo "  OK: persona=$TOPIC_PERSONA  topic=$TOPIC"

# Step 4: Build prompt
echo "[step 4/8] Building prompt (persona=$TOPIC_PERSONA)"

# Persona voice guide — grounded in 2026-07 owner research. Drives WHO we're
# writing to and in WHAT vocabulary. Never generic "local business owner."
case "$TOPIC_PERSONA" in
  beauty)
    PERSONA_GUIDE="AUDIENCE: the owner of a local nail salon, beauty spa, med-spa, or barbershop (think Alpharetta, Roswell, Milton, Johns Creek GA). Write to her like a trusted peer who's sat in her chair, not like an agency.
VOICE & VOCABULARY: use HER words — 'fully booked', 'fill the chairs', 'client magnet', 'dream clients', 'charge your worth', 'bigger bank balance', 'rebooking', 'your regulars', 'walk-ins'. NEVER use jargon like SEO, funnel, CTR, impressions, algorithm, or omnichannel.
HER REAL PAIN: empty chairs on slow days (Tuesdays and Wednesdays; the late-January and late-summer slumps) while wages and rent run regardless of bookings — an empty slot costs her more than the missed sale. She also feels isolated, with no one she trusts to ask.
HARD RULES: NEVER imply her craft or her work is the problem — she is excellent at what she does; the real gap is that the right clients can't find her or don't rebook. Frame everything around bookings and money in her pocket, never rankings or traffic."
    ;;
  trades)
    PERSONA_GUIDE="AUDIENCE: the owner of a local blue-collar / home-service business — window tint & PPF shop, auto services, auto transport, carpentry, plumbing, HVAC, or contractor (think Dallas-Fort Worth, Arlington, Lewisville, Frisco; or Cary/Raleigh NC). Write to him like a straight-talking peer who respects the trade.
VOICE & VOCABULARY: plain and no-BS. Use 'booked jobs', 'the phone ringing', 'leads you actually own', 'more calls', 'jobs on the calendar', 'your crew'. NEVER hide behind jargon like impressions, CTR, or vague 'algorithm updates'.
HIS REAL PAIN & DISTRUST: he's been burned. The FTC fined HomeAdvisor/Angi up to \$7.2M for selling leads that didn't match the trade or geographic area he paid for and for overstating how often those leads turn into jobs — 110,372 refund checks went out to providers. He is sick of agencies showing him rising traffic charts while the phone stays silent.
HARD RULES: Tie every single claim to booked jobs and revenue, never to vanity metrics. Be specific and accountable. When budget comes up, use real benchmarks — a sub-\$1M shop typically spends 5-10% of revenue on marketing, a \$1M-\$3M business 8-12%."
    ;;
  *)
    PERSONA_GUIDE="AUDIENCE: a local business owner who wants more customers and is tired of marketing that doesn't pay off.
VOICE: direct, practical, honest — plain language, not agency jargon. Tie everything to real outcomes (calls, bookings, revenue), never rankings or impressions.
HARD RULES: no hype, no fear-mongering. Give genuinely useful, specific advice a busy owner can act on this week."
    ;;
esac

PROMPT="Write a complete, genuinely useful blog post in markdown for performancemaxagency.com, a local-business marketing agency.

REQUIRED TOPIC — write specifically about this, with a fresh, specific angle:
$TOPIC

$PERSONA_GUIDE

EXISTING TITLES (your title and angle MUST be clearly different from ALL of these — do not rephrase any of them): $EXISTING

RULES:
- Author voice: The Performance MAX Team — an experienced local-marketing operator. Direct, warm, story-driven. Open with a specific, real-feeling scene (a named owner in a named town with a concrete number), NOT a generic 'in today's digital world' intro.
- Speak the owner's own language exactly as described in the AUDIENCE section above. Write for THAT owner, not a generic one.
- STAY STRICTLY in the AUDIENCE's industry. Do NOT make the post about a different business type (e.g. never write about restaurants, dentists, or law firms if the AUDIENCE is a salon or a trades shop). Every example, story, and scene must be from the AUDIENCE's own world.
- 1200-1800 words. Concrete, actionable, honest, real numbers where you can. No fluff, no hype, no filler.
- Every recommendation must connect to a real business outcome (booked appointments, phone calls, jobs, revenue) — never to vanity metrics.
- End with a natural, helpful CTA to book a strategy call with Performance MAX Agency (not pushy).
- Start with frontmatter exactly:
---
title: \"Your Title\"
description: \"120-160 char meta description\"
date: \"$DATE\"
author: \"The Performance MAX Team\"
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

# Anchor the stock-photo search to the persona's real business so the picture
# matches the owner reading it (no more generic guy-at-a-laptop for a nail salon).
case "$TOPIC_PERSONA" in
  beauty) IMAGE_QUERY="modern nail salon and beauty spa interior, manicure, $IMAGE_QUERY" ;;
  trades) IMAGE_QUERY="auto window tint / car detailing shop and home-service tradesperson at work, $IMAGE_QUERY" ;;
esac

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

# CRITICAL: image is keyed by SLUG, not DATE. Per-date filenames made every
# post published on the same day (or overwritten across a batch) share ONE
# picture. Rewrite the LLM's frontmatter path to the per-slug file so each
# post carries its own unique image. (root-cause fix 2026-07-22)
RESULT=$(printf '%s' "$RESULT" | sed "s|/blog-images/${DATE}\.jpg|/blog-images/${SLUG}.jpg|g")

set -e
set -o pipefail
echo "  OK: slug=$SLUG  title='$RAW_TITLE'  image_query='$IMAGE_QUERY'"

# Step 7: Fetch image (best-effort) — saved per-slug so images never collide
echo "[step 7/8] Fetching image"
IMAGE_PATH="/tmp/pmax_blog_${SLUG}.jpg"
IMG_STDERR=$(mktemp)
if python3 "$SHARED/fetch_image.py" "$IMAGE_QUERY" "$IMAGE_PATH" pmax 2> "$IMG_STDERR"; then
  if [ -f "$IMAGE_PATH" ] && [ -s "$IMAGE_PATH" ]; then
    mkdir -p public/blog-images
    cp "$IMAGE_PATH" "public/blog-images/$SLUG.jpg"
    echo "  OK: image fetched $(ls -lh "$IMAGE_PATH" | awk '{print $5}') -> $SLUG.jpg"
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
python3 "$SCRIPT_DIR/internal_link.py" "$BLOG_DIR/$SLUG.md" 2>/dev/null || true
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
    'keyword': sys.argv[2],
    'article': body,
    'word_count': int(sys.argv[3]),
    'seo_score': 0,
    'title_tag': '',
    'meta_description': '',
    'source': sys.argv[4] + '-selfscore',
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
