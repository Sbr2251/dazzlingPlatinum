#!/usr/bin/env python3
# Checks that every GoTo/Call(If...) and ApplyMovement/ApplyFreeCameraMovement in the field scripts names a label defined in
# the same file. A jump to a constant or into movement data assembles fine but runs garbage at that point in the game
# (on the Mac app it crashes; on the DS it misbehaves). usage: tools/dazzling/check_script_targets.py [repo root]
import re,glob,sys,os
os.chdir(sys.argv[1] if len(sys.argv)>1 else '.')
lab=re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*$')
bad=[]
for f in sorted(glob.glob('res/field/maps/*/scripts.s')+glob.glob('res/field/maps/*/init.s')+glob.glob('res/field/scripts/*.s')):
    L=open(f).read().splitlines()
    labels={lab.match(l).group(1) for l in L if lab.match(l)}
    for i,l in enumerate(L):
        s=l.split('//')[0].strip()
        if not s: continue
        op=s.split()[0]
        if re.match(r'^(GoTo|Call)(If\w*)?$',op) or op in ('ApplyMovement','ApplyFreeCameraMovement'):
            args=[a.strip() for a in s[len(op):].split(',')]
            t=args[-1]
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$',t) and t not in labels:
                bad.append(f'{f}:{i+1}: {s}')
print('\n'.join(bad)); print(len(bad),'unresolved targets')
sys.exit(1 if bad else 0)
