#!/bin/sh
# macOS: Apple's assembler cannot fold the trainer AI script's label differences divided by 4 (".long (X - FlagTable) / 4": "expected relocatable expression").
# The script is pure data with no relocations, so assemble it as ELF with arm-none-eabi-as (same little-endian 32-bit layout), take its .text bytes, and wrap them
# in a Mach-O object that defines _gTrainerAITable at the same offset.
# usage: trainer_ai_macho.sh <script.ss> <out.o> <include dir>...
set -e
in=$1 out=$2; shift 2
incs=""; for d in "$@"; do incs="$incs -I $d"; done
tmp=$(mktemp -d "${TMPDIR:-/tmp}/trainer_ai.XXXXXX"); trap 'rm -rf "$tmp"' EXIT
arm-none-eabi-as $incs -o "$tmp/elf.o" "$in"
if [ -n "$(arm-none-eabi-readelf -r "$tmp/elf.o" | grep -v 'no relocations')" ]; then echo "trainer_ai_macho.sh: the script has relocations; this conversion cannot keep them" >&2; exit 1; fi
off=$(arm-none-eabi-nm "$tmp/elf.o" | awk '$3 == "gTrainerAITable" { print $1 }')
[ -n "$off" ] || { echo "trainer_ai_macho.sh: no gTrainerAITable" >&2; exit 1; }
arm-none-eabi-objcopy -O binary -j .text "$tmp/elf.o" "$tmp/script.bin"
cat > "$tmp/wrap.s" <<WRAP
    .section __DATA,__const
    .p2align 2
Ltrainer_ai_start:
    .incbin "$tmp/script.bin"
    .globl _gTrainerAITable
    .set _gTrainerAITable, Ltrainer_ai_start + 0x$off
WRAP
as -o "$out" "$tmp/wrap.s"
