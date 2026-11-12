#!/bin/sh
# Run locally after gh auth login. Publishes this reviewed repository and enables Pages.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
python3 -m unittest discover -s tests -v
python3 evals.py validate
python3 scripts/build_site.py
if [ -n "$(git status --porcelain)" ]; then
  echo 'Commit or stash local changes before publishing.' >&2
  exit 1
fi
gh auth status
owner=${1:-$(gh api user --jq .login)}
repo="$owner/llm-evals"
if git remote get-url origin >/dev/null 2>&1; then
  actual=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
  if [ "$actual" != "$repo" ]; then
    echo 'Existing origin does not match requested repository; stopping.' >&2
    exit 1
  fi
  if [ "$(gh repo view --json isPrivate --jq .isPrivate)" != false ]; then
    echo 'Existing repository is private; stopping without changing its visibility.' >&2
    exit 1
  fi
else
  if gh repo view "$repo" >/dev/null 2>&1; then
    echo 'Repository name already exists; stopping without modifying it.' >&2
    exit 1
  fi
  gh repo create "$repo" --public --source . --remote origin --description 'Local LLM and quantization evaluations with attributed frontier-model comparisons'
fi
git push -u origin main
if gh api "repos/$repo/pages" >/dev/null 2>&1; then
  gh api --method PUT "repos/$repo/pages" -f build_type=workflow >/dev/null
else
  gh api --method POST "repos/$repo/pages" -f build_type=workflow >/dev/null
fi
# The first push may reach Actions before Pages is enabled. Dispatch an explicit build.
gh workflow run pages.yml --repo "$repo" --ref main -F sync=false
printf 'Repository: https://github.com/%s\n' "$repo"
printf 'Deployment status: https://github.com/%s/actions\n' "$repo"
gh api "repos/$repo/pages" --jq .html_url
