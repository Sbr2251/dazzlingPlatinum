# Everspring Sanctuary integration

The repository-local builder regenerates the two Route 218 land members from the approved behavior contract and model sources under `assets/`, while preserving each canonical member’s building section. Run `python3 tools/everspring/build_everspring_land_data.py`; output is written to `build/everspring_generated/`.

The strict inspector and bounded alignment verifier validate both NSBMDs, all 51 material records, model/material/linkage/SBC word alignment, and the approved Platinum material register values. The save synchronizer patches both valid save partitions, both persisted coordinate triplets, fx32 height, field state, facing, and CRCs; it fails on ambiguous player records or invalid input saves.
