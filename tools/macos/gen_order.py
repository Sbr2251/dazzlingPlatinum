#!/usr/bin/env python3
# macOS: the hardware register and memory variables of libntr's simulator (sim_vars.c) must be laid out in definition order, as GNU ld
# lays them out: the SDK writes some registers as one 32-bit store across two 16-bit ones (G2_SetBlendAlpha: BLDCNT + BLDALPHA), and some
# memory blocks are addressed as one range. Apple's ld sorts common symbols by name (BLDALPHA came before BLDCNT, so every alpha blend
# coefficient was lost and blended graphics drew black). This writes an ld order file listing them in definition order.
# usage: gen_order.py <sim_vars.c> <out.order>
import re, sys
names = []
for line in open(sys.argv[1]):
    m = re.match(r'\s*(?:REGType\w+|u8|u16|u32|u64|s8|s16|s32|s64|vu8|vu16|vu32|vu64|TPData|SIM_HWPlttBlock|BOOL|int)\s+(s_\w+)\s*(?:\[[^\]]*\])?\s*;', line)
    if m and m.group(1) not in names: names.append(m.group(1))
open(sys.argv[2], 'w').write(''.join('_' + n + '\n' for n in names))
print(f'gen_order.py: {len(names)} symbols')
