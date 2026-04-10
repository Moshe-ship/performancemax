#!/bin/bash
set -e
cd "$(dirname "$0")"
BLOG_DIR="src/content/blog"
DATE=$(date +%Y-%m-%d)
SHARED="$HOME/Projects/shared"
DRY_RUN="${1:-}"

git log --oneline --since="$DATE" | grep -q "blog:" && echo "Already published today." && exit 0

EXISTING=$(ls $BLOG_DIR/*.md 2>/dev/null | xargs grep "^title:" | sed 's/.*title: *"//;s/"$//' | tr '\n' ', ' | cut -c1-500)

echo "[$DATE] Generating PMax blog via local LLM..."
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

RESULT=$(python3 "$SHARED/generate_blog.py" "$PROMPT" 2>/dev/null)
[ -z "$RESULT" ] && echo "ERROR: Empty LLM response" && exit 1

# Extract image query
IMAGE_QUERY=$(echo "$RESULT" | grep "^IMAGE_QUERY:" | sed 's/IMAGE_QUERY: *//')
[ -z "$IMAGE_QUERY" ] && IMAGE_QUERY="local business digital marketing"
RESULT=$(echo "$RESULT" | grep -v "^IMAGE_QUERY:")

# Fetch image
IMAGE_PATH="/tmp/pmax_blog_$DATE.jpg"
python3 "$SHARED/fetch_image.py" "$IMAGE_QUERY" "$IMAGE_PATH" pmax 2>/dev/null
if [ -f "$IMAGE_PATH" ] && [ -s "$IMAGE_PATH" ]; then
  mkdir -p public/blog-images
  cp "$IMAGE_PATH" "public/blog-images/$DATE.jpg"
fi

SLUG=$(echo "$RESULT" | grep "^title:" | head -1 | sed 's/title: *"//;s/"$//' | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-' | cut -c1-60)
[ -z "$SLUG" ] && SLUG="blog-$DATE"

if [ "$DRY_RUN" = "--dry-run" ]; then
  WORDS=$(echo "$RESULT" | wc -w | tr -d ' ')
  echo "DRY RUN — Slug: $SLUG"
  echo "Words: ~$WORDS"
  echo "Image: $(ls -lh "$IMAGE_PATH" 2>/dev/null | awk '{print $5}')"
  echo "$RESULT" | head -5
  exit 0
fi

echo "$RESULT" > "$BLOG_DIR/$SLUG.md"
git add "$BLOG_DIR/$SLUG.md" public/blog-images/ 2>/dev/null || true
git commit -m "blog: $SLUG"
git push origin main
echo "PUBLISHED: $SLUG"
