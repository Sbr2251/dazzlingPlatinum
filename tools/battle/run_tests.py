#!/usr/bin/env python3
"""Run tools/battle/tests/*.json against a headless build. One command:
  python3 tools/battle/run_tests.py [--build-dir build_linux] [--filter substr] [--save ...]
Each test: {name, spec, expect}. Expect keys: winner, battle_ended,
damage_to_battler, active_species, party_species_after, max_turns.
Without engine-core events, mega/totem/crit are asserted at the state level
(battle completes, damage/faint/switch observed, Mega reverts after battle);
they gain event-level assertions when battle_events lands.
Exit 1 if any test fails."""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as simmod

def check(result, events, expect):
    errs=[]
    if expect.get("battle_ended", True) and not result: errs.append("no result")
    if "winner" in expect and result.get("winner")!=expect["winner"]: errs.append(f"winner {result.get('winner')} != {expect['winner']}")
    if "damage_to_battler" in expect and not any(e.get("type")=="damage" and e.get("battler")==expect["damage_to_battler"] for e in events): errs.append("no damage event to battler")
    if "active_species" in expect and not any(e.get("type") in ("switch","switch_in") and e.get("to")==expect["active_species"] for e in events) and (result.get("final_battle") or {}).get("battlers",[{}])[0].get("species")!=expect["active_species"]: errs.append("active species not observed")
    if "party_species_after" in expect:
        party=result.get("party_after") or []
        if not party or party[0].get("species")!=expect["party_species_after"]: errs.append("party species after battle mismatch (mega revert check)")
    if "max_turns" in expect and result.get("turns",999)>expect["max_turns"]: errs.append("too many turns")
    return errs

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--build-dir",default="build_linux"); ap.add_argument("--filter",default=""); ap.add_argument("--save"); ap.add_argument("--tests",default=os.path.join(os.path.dirname(os.path.abspath(__file__)),"tests"))
    a=ap.parse_args()
    save=a.save
    if not save:
        for c in simmod.DEFAULT_SAVES:
            if os.path.exists(c): save=c; break
    files=sorted(glob.glob(os.path.join(a.tests,"*.json"))); fails=0
    for path in files:
        t=json.load(open(path)); name=t.get("name",os.path.basename(path))
        if a.filter and a.filter not in name: continue
        runner=simmod.BattleRunner(a.build_dir, save, seed=int(t["spec"].get("seed",42)))
        try:
            result=runner.run_battle(t["spec"], policy=t.get("policy","first"))
            errs=check(result, runner.events, t.get("expect",{}))
        except Exception as e:
            errs=[str(e)]; result=None
        finally:
            runner.close()
        print(("FAIL " if errs else "PASS ")+name+(" "+("; ".join(errs)) if errs else f" winner={result.get('winner')} turns={result.get('turns')}"))
        fails+=bool(errs)
    return 1 if fails else 0
if __name__=="__main__": sys.exit(main())
