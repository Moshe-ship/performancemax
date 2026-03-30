#!/bin/bash
# Create a new blog post for Performance MAX
# Usage: ./scripts/new-post.sh "Your Blog Post Title"

if [ -z "$1" ]; then
  echo "Usage: ./scripts/new-post.sh \"Your Blog Post Title\""
  exit 1
fi

TITLE="$1"
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')
DATE=$(date +%Y-%m-%d)
FILE="src/content/blog/${SLUG}.md"

if [ -f "$FILE" ]; then
  echo "Error: $FILE already exists"
  exit 1
fi

cat > "$FILE" << EOF
---
title: "${TITLE}"
description: "WRITE A 1-2 SENTENCE DESCRIPTION HERE"
date: "${DATE}"
author: "Musa the Carpenter"
---

Write your blog post content here using Markdown.

## First Section

Your content...

## Second Section

More content...

## What to do next

Call to action paragraph here.
EOF

echo "Created: $FILE"
echo ""
echo "Next steps:"
echo "  1. Edit the post: code $FILE"
echo "  2. Preview: npm run dev"
echo "  3. Publish: git add . && git commit -m 'New post: ${TITLE}' && git push"
