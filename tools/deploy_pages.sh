#!/bin/sh
# Publish _site/ to the gh-pages branch of origin. Run tools/build_site.py first.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
WT="$ROOT/.gh-pages-worktree"
cd "$ROOT"
test -f _site/index.html || { echo "run python3 tools/build_site.py first" >&2; exit 1; }
rm -rf "$WT"
git worktree prune
if git ls-remote --exit-code --heads origin gh-pages >/dev/null 2>&1; then
  git fetch -q origin gh-pages
  git worktree add -q -B gh-pages "$WT" origin/gh-pages
else
  git worktree add -q --detach "$WT"
  (cd "$WT" && git checkout -q --orphan gh-pages && git rm -rfq . >/dev/null 2>&1 || true)
fi
(cd "$WT" && find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} + && cp -R "$ROOT/_site/." . \
  && git add -A && { git diff --cached --quiet || git commit -q -m "site: $(cd "$ROOT" && git rev-parse --short HEAD)"; } \
  && git push -q origin gh-pages)
git worktree remove --force "$WT"
echo "published gh-pages from $(git rev-parse --short HEAD)"
