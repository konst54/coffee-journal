#!/bin/sh
# Builds the static site for GitHub Pages: only runtime files from web/ (no tests, no data).
# Usage: tools/build-pages.sh OUT_DIR
set -eu
out=${1:?output directory}
mkdir -p "$out"
for f in index.html style.css main.js app.js model.js demo.js auth.js authbar.js config.js; do
  cp "web/$f" "$out/$f"
done
touch "$out/.nojekyll"
# Refuse to publish anything that looks like a secret or private export.
if grep -RIlE 'sb_secret_|service_role|BEGIN [A-Z ]*PRIVATE KEY|source_text' "$out" | grep -v '^$'; then
  echo 'refusing to publish: suspicious content' >&2; exit 1
fi
