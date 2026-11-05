#!/usr/bin/env bash
# deploy.sh — publish the D2R Bible live to Cloudflare Pages
# (project `d2r-bible` → bull-4-u.com). Ships bible.html as index.html plus the
# self-hosted item art (art/) and the AI-vision API (functions/api/intake.js).
#
# Run it by hand anytime:   bash deploy.sh
# It is ALSO invoked automatically by hooks/pre-push after the smoke gate passes
# on a push to main that touches bible.html / art / functions (see that hook).
#
# Auth: needs CLOUDFLARE_API_TOKEN in the env (set in ~/.zshenv, scope Pages:Edit).
# The non-interactive shell sources ~/.zshenv, so it's present on hook runs too.
# Exit codes: 0 = deployed, 2 = skipped (missing token/npx), 1 = deploy failed.
set -u

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "deploy: not in a git repo."; exit 1; }
cd "$REPO" || exit 1

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "deploy: CLOUDFLARE_API_TOKEN not set — skipping (set it in ~/.zshenv, scope Pages:Edit)."
  exit 2
fi
if ! command -v npx >/dev/null 2>&1; then
  echo "deploy: npx not found on PATH — cannot deploy."
  exit 2
fi
for d in bible.html art functions; do
  if [ ! -e "$d" ]; then echo "deploy: missing '$d' — aborting."; exit 1; fi
done

DIST="$(mktemp -d -t d2r_dist.XXXXXX)" || { echo "deploy: mktemp failed."; exit 1; }
trap 'rm -rf "$DIST"' EXIT
mkdir -p "$DIST/d2r"
cp bible.html "$DIST/d2r/index.html"   # served at /d2r/
cp -R art "$DIST/d2r/art"              # MUST include — self-hosted item art
cp -R functions "$DIST/functions"      # MUST include — api/intake.js (AI vision)
cp tv/install-tvd.ps1 "$DIST/d2r/install-tvd.ps1"   # 📺 Windows: irm …/d2r/install-tvd.ps1 | iex
cp tv/install-tvd.sh  "$DIST/d2r/install-tvd.sh"    # 📺 Mac:     curl -fsSL …/d2r/install-tvd.sh | bash
cp tv/tasks_board.html "$DIST/d2r/tasks.html"      # v3864 (card 57) - his task board online, behind the site password
# v687 — do NOT ship orphan /d2r/v44/* (Session Cockpit is native in bible.html; external
# v44 CSS/JS/SW were a dead layer and caused ghost/404 confusion). Dist is only index+art+functions.
# v696 — GHOST EXORCISM (live audit): the Phase-Z service worker + a 41KB v44 orphan were STILL
# serving 200 from the edge, and any browser that ever registered that SW keeps intercepting
# /d2r/ GETs. Ship TOMBSTONES at those exact paths: a self-unregistering sw.js (kills old client
# registrations + nukes its caches on their next update check) and an inert v44-upgrade.js —
# both under no-cache so the edge revalidates instead of resurrecting the cached originals.
cat > "$DIST/d2r/sw.js" <<'SWJS'
/* v696 tombstone — the Phase-Z worker is dead. This replaces it on every client's next
   update check: unregister, drop all caches, hand pages back to the network. */
self.addEventListener('install', function(){ self.skipWaiting(); });
self.addEventListener('activate', function(e){
  e.waitUntil((async function(){
    try { const ks = await caches.keys(); await Promise.all(ks.map(function(k){ return caches.delete(k); })); } catch(err){}
    try { await self.registration.unregister(); } catch(err){}
    try { const cs = await self.clients.matchAll({type:'window'}); cs.forEach(function(c){ c.navigate(c.url); }); } catch(err){}
  })());
});
SWJS
mkdir -p "$DIST/d2r/v44"
printf '/* v696 tombstone — the v44 layer is dead; Session Cockpit is native in bible.html */\n' > "$DIST/d2r/v44/v44-upgrade.js"
# v657 — CACHE LOCKDOWN: Konyo's tabs kept serving WEEKS-old HTML from browser cache for URLs
# with stale ?v=/?cb= params (the recurring 'this bug is still there' ghost — routines widget,
# tooltip fixes, all of it). The HTML must always revalidate; the art can cache forever.
cat > "$DIST/_headers" <<'HDRS'
/d2r/
  Cache-Control: no-cache, must-revalidate
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
/d2r/index.html
  Cache-Control: no-cache, must-revalidate
/d2r/sw.js
  Cache-Control: no-cache, must-revalidate
/d2r/tasks.html
  Cache-Control: no-cache, must-revalidate
/d2r/v44/*
  Cache-Control: no-cache, must-revalidate
/d2r/art/*
  Cache-Control: public, max-age=604800, immutable
# v755.1 / v756 — installers must be text/plain so irm|iex and curl|bash get strings
# (Pages defaults .ps1 → application/octet-stream on some boxes)
/d2r/install-tvd.ps1
  Content-Type: text/plain; charset=utf-8
  Cache-Control: no-cache, must-revalidate
  Access-Control-Allow-Origin: *
/d2r/install-tvd.sh
  Content-Type: text/plain; charset=utf-8
  Cache-Control: no-cache, must-revalidate
  Access-Control-Allow-Origin: *
HDRS

echo "deploy: publishing to Cloudflare Pages (d2r-bible → bull-4-u.com)…"
if npx wrangler pages deploy "$DIST" --project-name=d2r-bible --branch=main; then
  echo "deploy: ✨ live."
  exit 0
fi
echo "deploy: FAILED — site NOT updated. Re-run: bash deploy.sh"
exit 1
