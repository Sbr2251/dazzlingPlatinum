#!/bin/bash
# Package the (unsigned) device .app as an unsigned .ipa for Sideloadly:
# Payload/"Dazzling Platinum.app" zipped. Sideloadly re-signs it on install.
# usage: make_ipa.sh <build dir>
set -euo pipefail
BUILDDIR=$(cd "$1" && pwd)
APP="$BUILDDIR/Dazzling Platinum.app"
IPA="$BUILDDIR/DazzlingPlatinum.ipa"
[ -d "$APP" ] || { echo "no app at $APP (run make_app.sh first)" >&2; exit 1; }
rm -rf "$BUILDDIR/Payload" "$IPA"
mkdir -p "$BUILDDIR/Payload"
cp -R "$APP" "$BUILDDIR/Payload/"
(cd "$BUILDDIR" && zip -qr "$IPA" Payload)
rm -rf "$BUILDDIR/Payload"
echo "ipa: $IPA"
