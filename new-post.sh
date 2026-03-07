#!/bin/bash
# Usage: ./new-post.sh "My Post Title"
# Creates a new scroll post and opens it in $EDITOR (default: nano)

TITLE="${1:-New Post}"
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
FILE="_posts/${DATE}-${SLUG}.md"

if [ -f "$FILE" ]; then
  echo "File already exists: $FILE"
  echo "Opening for editing..."
  ${EDITOR:-nano} "$FILE"
  exit 0
fi

cat > "$FILE" <<EOF
---
layout: scroll-post
title: "$TITLE"
date: $DATE
categories: [scroll]
commentbox: true
---

Write your post here. LaTeX works inline \$like this\$ or display:

\$\$
E = mc^2
\$\$

EOF

echo "Created: $FILE"
${EDITOR:-nano} "$FILE"
