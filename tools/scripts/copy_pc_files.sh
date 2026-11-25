#!/bin/bash
# Lay out built game data files next to `main` (and wrap into Dazzling Platinum.app on macOS).
# cp_u (copy only when newer) is GNU-only; macOS's cp has no -u.
cp_u() { if [ ! -e "$2" ] || [ "$1" -nt "$2" ]; then cp "$1" "$2"; fi; }
BUILDDIR=$1
OUTPUTDIR=$BUILDDIR
mkdir -p "$OUTPUTDIR"

cat "$2" | while read -r line; do
  if [[ "$line" != "Source File,Target File" ]] && [[ -n "$line" ]]; then
    SourceFile=$(echo "$line" | cut -d, -f1)
    DestFile=$(echo "$line" | cut -d, -f2)
    mkdir -p "$(dirname "$OUTPUTDIR$DestFile")"
    cp_u "$BUILDDIR/$SourceFile" "$OUTPUTDIR$DestFile"
  fi
done
cp_u "$BUILDDIR/../res/pc_port/header.bin" "$OUTPUTDIR/header.bin"
cp_u "$BUILDDIR/../res/pc_port/dwc_nv.bin" "$OUTPUTDIR/firmware.bin"
cp_u "$BUILDDIR/../language.csv" "$OUTPUTDIR/language.csv"

if [[ "$4" == "-ios" ]]; then
  : # iOS: files sit next to main in the build dir; tools/ios/make_app.sh packages the .app
else
  # macOS: wrap main, SDL3, and game files in "Dazzling Platinum.app"
  if [ -x "$BUILDDIR/../tools/macos/make_app.sh" ]; then
    "$BUILDDIR/../tools/macos/make_app.sh" "$OUTPUTDIR" "$2"
  fi
fi
