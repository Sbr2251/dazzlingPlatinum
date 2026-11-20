#!/bin/bash
# Install + launch the Simulator build on this lane's own simulator and screenshot it.
#   tools/ios/sim_run.sh [build dir] [screenshot.png]
# Creates the dz-ios-build device if needed; shut it down when idle yourself.
set -euo pipefail
BUILD=${1:-build_ios_sim}
SHOT=${2:-$BUILD/sim_title.png}
APP="$BUILD/Dazzling Platinum.app"
BUNDLE=local.dazzlingplatinum.ios
NAME=dz-ios-build

UDID=$(xcrun simctl list devices available -j | python3 -c "
import json,sys
for rt,devs in json.load(sys.stdin)['devices'].items():
    for d in devs:
        if d['name']=='$NAME': print(d['udid']); raise SystemExit
")
if [ -z "$UDID" ]; then
  TYPE=$(xcrun simctl list devicetypes -j | python3 -c "
import json,re,sys
ts=[t for t in json.load(sys.stdin)['devicetypes'] if re.match(r'iPhone \d', t['name'])]
ts.sort(key=lambda t: [int(n) for n in re.findall(r'\d+', t['name'])])
print(ts[-1]['identifier'])")
  RUNTIME=$(xcrun simctl list runtimes -j | python3 -c "
import json,sys
rs=[r for r in json.load(sys.stdin)['runtimes'] if r['name'].startswith('iOS') and r['isAvailable']]
print(rs[-1]['identifier'])")
  UDID=$(xcrun simctl create "$NAME" "$TYPE" "$RUNTIME")
  echo "created simulator $NAME ($UDID)"
fi
xcrun simctl boot "$UDID" 2>/dev/null || true
xcrun simctl bootstatus "$UDID" -b >/dev/null
xcrun simctl install "$UDID" "$APP"
xcrun simctl launch "$UDID" "$BUNDLE"
sleep 20
xcrun simctl io "$UDID" screenshot "$SHOT"
echo "screenshot: $SHOT (simulator $UDID left booted; 'xcrun simctl shutdown $UDID' when idle)"
