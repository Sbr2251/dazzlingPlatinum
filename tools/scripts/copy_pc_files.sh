#!/bin/bash
# cp_u (copy only when newer) is GNU-only; macOS's cp has no -u
cp_u() { if [ ! -e "$2" ] || [ "$1" -nt "$2" ]; then cp "$1" "$2"; fi; }
BUILDDIR=$1
OUTPUTDIR=$BUILDDIR
mkdir -p $OUTPUTDIR

cat $2 | while read line; do
  if [[ "$line" != "Source File,Target File" ]] ;
    then
    SourceFile=$(echo $line | cut -d, -f1)
    DestFile=$(echo $line | cut -d, -f2)
    mkdir -p `dirname $OUTPUTDIR$DestFile`
    
    cp_u $BUILDDIR/$SourceFile $OUTPUTDIR$DestFile
  fi
done
cp_u $BUILDDIR/../res/pc_port/header.bin $OUTPUTDIR/header.bin
cp_u $BUILDDIR/../res/pc_port/dwc_nv.bin $OUTPUTDIR/firmware.bin
cp_u $BUILDDIR/../language.csv $OUTPUTDIR/language.csv

if [[ "$4" == "-nx" ]]; then
  /opt/devkitpro/tools/bin/elf2nro $OUTPUTDIR/main $OUTPUTDIR/pokeplatinum.nro
else
  if [[ "$(uname -s)" == "Darwin" ]]; then
    # macOS: the game runs from this folder (main next to its files); tools/macos/make_app.sh wraps it in a .app
    if [ -x "$BUILDDIR/../tools/macos/make_app.sh" ]; then "$BUILDDIR/../tools/macos/make_app.sh" "$OUTPUTDIR" "$2"; fi
  elif [[ "$(uname -s)" =~ ^MSYS_NT.* ]]; then
    cp_u /ucrt64/bin/SDL2.dll $OUTPUTDIR/SDL2.dll
    cp_u /ucrt64/bin/libwinpthread-1.dll $OUTPUTDIR/libwinpthread-1.dll
    cp_u /ucrt64/bin/libenet-7.dll $OUTPUTDIR/libenet-7.dll
    cp_u /ucrt64/bin/libgcc_s_seh-1.dll $OUTPUTDIR/libgcc_s_seh-1.dll
    cp_u /ucrt64/bin/libstdc++-6.dll $OUTPUTDIR/libstdc++-6.dll
  else
    mkdir -p $OUTPUTDIR/$3.AppDir
    mkdir -p $OUTPUTDIR/$3.AppDir/usr/bin
    mkdir -p $OUTPUTDIR/$3.AppDir/usr/lib
    cp $BUILDDIR/main $OUTPUTDIR/$3.AppDir/usr/bin/app
    if [ ! -f $BUILDDIR/../tools/linuxdeploy/linuxdeploy-x86_64.AppImage ]; then
      echo "Downloading linuxdeploy..."
      wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage -O $BUILDDIR/../tools/linuxdeploy/linuxdeploy-x86_64.AppImage
      chmod +x $BUILDDIR/../tools/linuxdeploy/linuxdeploy-x86_64.AppImage
    fi
    $BUILDDIR/../tools/linuxdeploy/linuxdeploy-x86_64.AppImage --appdir $OUTPUTDIR/$3.AppDir --executable=$OUTPUTDIR/main --desktop-file=$BUILDDIR/../tools/linuxdeploy/App.desktop --icon-file=$BUILDDIR/../tools/linuxdeploy/app.png --output appimage
    mv pokeplatinum-x86_64.AppImage $OUTPUTDIR/pokeplatinum.AppImage
  fi
fi