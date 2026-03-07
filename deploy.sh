#!/bin/bash
# Usage: ./deploy.sh ["Optional commit message"]
# Stages all new/modified files, commits, and pushes to GitHub.

MSG="${1:-update site}"

git add -A
git status --short

if git diff --cached --quiet; then
  echo "Nothing to commit. Working tree is clean."
  exit 0
fi

read -r -p "Commit and push with message \"$MSG\"? [y/N] " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
  git commit -m "$MSG"
  git push origin master
  echo "Done. GitHub Pages will rebuild in ~1 minute."
else
  echo "Aborted."
  git reset HEAD
fi
