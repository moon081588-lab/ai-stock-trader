#!/usr/bin/env bash
# Creates the private GitHub repo and pushes this project.
# Run once, from the project root:  bash scripts/setup_github.sh
set -euo pipefail

REPO_NAME="${1:-ai-stock-trader}"

command -v gh >/dev/null || {
  echo "GitHub CLI not found. Install it first:  brew install gh"
  exit 1
}

gh auth status >/dev/null 2>&1 || gh auth login

gh repo create "$REPO_NAME" \
  --private \
  --source=. \
  --remote=origin \
  --description "AI-assisted equity research: projections, portfolio and dividend analytics, news signals, paper trading" \
  --push

echo
echo "Done. Repo: $(gh repo view --json url -q .url)"
