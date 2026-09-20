# AXM Avatar Machine — Working Chat Start

This is the practical entry point for a normal AI chat or working instance. Do not rebuild the extraction from zero.

## Read first

1. `README.md`
2. `docs/UC_EXTRACTION_PROVENANCE.md`
3. `docs/AVATAR_BLUEPRINT_DIRECTION.md`
4. `docs/BLUEPRINT_COMPILER_V1.md`
5. `docs/REFERENCE_INTERPRETATION_STAGE.md`
6. this file

Keep one branch / one PR lane per chat until that lane is merged or explicitly abandoned.

## Inspect before changing

```bash
python -m pip install -e .
axm-avatar profile
axm-avatar material-catalog
axm-avatar validate-blueprint examples/blueprint-doll-pair-v1.json
axm-avatar compile-blueprint examples/blueprint-doll-pair-v1.json /tmp/avatar-scene-plan.json
PYTHONPATH=src python -m unittest discover -s tests -v
```

The recovered Odd Shift Duo is the frozen regression baseline. Do not rewrite its builder, renderer, verifier, or recovered profile to make generic work easier.

## Current paths

- recovered profile -> Blender/GLB/poster/clip -> verification/regression -> creator-parts;
- explicit Doll Blueprint -> deterministic scene plan -> generic Blender realization -> structural receipt -> creator-parts;
- reference bytes -> portable hash packet -> explicit human/replaceable interpreter -> validated blueprint;
- optional material-response family -> deterministic scene-plan intent -> base scalar projection + visible HOLD for unbound response organs.

## Truth boundaries

- arbitrary photo pixels -> interpreted avatar is not native automatic capability;
- Doll Profile v1 motion is rigid bone parenting, not smooth skinning;
- generic realistic/cartoon/mascot profile families are not implemented;
- response-organ verification from the supplied reference host does not automatically transfer to Blender;
- a material-response HOLD is not a failed geometry build and is not a visual PASS;
- UC and MorphTile are neighbors/donors, not runtime dependencies.

Extend the smallest explicit boundary instead of rewriting the proven baseline.
