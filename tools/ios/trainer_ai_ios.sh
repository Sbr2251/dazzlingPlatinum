#!/bin/sh
# iOS variant of tools/macos/trainer_ai_macho.sh: same ELF->Mach-O wrap, but the
# wrapper object is assembled for the iOS target in $SIM_IOS_TARGET (set by
# tools/ios/build.sh), not for macOS.
# usage: trainer_ai_ios.sh <script.ss> <out.o> <enumproc> <include dir>...
set -e
in=$1 out=$2 enumproc=$3; shift 3
incs=""; for d in "$@"; do incs="$incs -I $d"; done
tmp=$(mktemp -d "${TMPDIR:-/tmp}/trainer_ai.XXXXXX"); trap 'rm -rf "$tmp"' EXIT
"$enumproc" < "$in" | arm-none-eabi-gcc -x assembler-with-cpp $incs -c -o "$tmp/elf.o" -
if [ -n "$(arm-none-eabi-readelf -r "$tmp/elf.o" | grep -v 'no relocations')" ]; then echo "trainer_ai_ios.sh: the script has relocations; this conversion cannot keep them" >&2; exit 1; fi
off=$(arm-none-eabi-nm "$tmp/elf.o" | awk '$3 == "gTrainerAITable" { print $1 }')
[ -n "$off" ] || { echo "trainer_ai_ios.sh: no gTrainerAITable" >&2; exit 1; }
arm-none-eabi-objcopy -O binary -j .text "$tmp/elf.o" "$tmp/script.bin"
cat > "$tmp/wrap.s" <<WRAP
    .section __DATA,__const
    .p2align 2
Ltrainer_ai_start:
    .incbin "$tmp/script.bin"
    .globl _gTrainerAITable
    .set _gTrainerAITable, Ltrainer_ai_start + 0x$off
WRAP
clang -target "${SIM_IOS_TARGET:?tools/ios/build.sh sets SIM_IOS_TARGET}" -c "$tmp/wrap.s" -o "$out"
