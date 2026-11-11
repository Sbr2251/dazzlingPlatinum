#!/bin/sh
# Linux: same trick as tools/macos/trainer_ai_macho.sh, but wraps the script bytes in an ELF object.
# The trainer AI script is pure data with no relocations: assemble it as ELF with arm-none-eabi-as,
# take its .text bytes, and define gTrainerAITable at the same offset in a host object.
# usage: trainer_ai_elf.sh <script.ss> <out.o> <enumproc> <include dir>...
set -e
in=$1 out=$2 enumproc=$3; shift 3
incs=""; for d in "$@"; do incs="$incs -I $d"; done
tmp=$(mktemp -d "${TMPDIR:-/tmp}/trainer_ai.XXXXXX"); trap 'rm -rf "$tmp"' EXIT
"$enumproc" < "$in" | arm-none-eabi-gcc -x assembler-with-cpp $incs -c -o "$tmp/elf.o" -
if [ -n "$(arm-none-eabi-readelf -r "$tmp/elf.o" | grep -v 'no relocations')" ]; then echo "trainer_ai_elf.sh: the script has relocations; this conversion cannot keep them" >&2; exit 1; fi
off=$(arm-none-eabi-nm "$tmp/elf.o" | awk '$3 == "gTrainerAITable" { print $1 }')
[ -n "$off" ] || { echo "trainer_ai_elf.sh: no gTrainerAITable" >&2; exit 1; }
arm-none-eabi-objcopy -O binary -j .text "$tmp/elf.o" "$tmp/script.bin"
cat > "$tmp/wrap.s" <<WRAP
    .section .rodata
    .p2align 2
Ltrainer_ai_start:
    .incbin "$tmp/script.bin"
    .globl gTrainerAITable
    .set gTrainerAITable, Ltrainer_ai_start + 0x$off
WRAP
cc -c -o "$out" "$tmp/wrap.s"
