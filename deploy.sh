#!/usr/bin/env bash
# Vercel's remote build machine OOMs on this app's three.js/drei bundle
# (see README), so ship by building locally -- where memory isn't a
# constraint -- and uploading the prebuilt output straight to production.
set -euo pipefail
cd "$(dirname "$0")"

rm -rf frontend/.next .vercel/output
npx --yes vercel@latest build --prod --yes
npx --yes vercel@latest deploy --prebuilt --prod --yes
