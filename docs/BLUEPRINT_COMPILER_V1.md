# Doll Blueprint Compiler v1

This is the first **general, bounded, deterministic** Avatar Machine authoring path.

It is deliberately narrower than “make any avatar”. The implemented family is
`stylized-doll`. A person or optional AI authors the same explicit JSON fields,
and the local compiler turns those fields into a deterministic scene plan.

## Pipeline

`human/AI explicit fields -> validated Doll Blueprint v1 -> deterministic scene plan -> Blender builder -> editable .blend + animated GLB + poster -> structural inspection`

No reference image, model service, UC checkout, MorphTile runtime, chat history or
hidden workstation path is required.

The recovered Odd Shift Duo builder remains untouched and is still the proven
regression baseline. The new blueprint builder lives beside it.

## Current controls

Each character exposes bounded controls for:

- proportions: height, head scale, torso width and limb length;
- palette: skin, primary, secondary, hair and shoes;
- face: hair, facial hair, eye and mouth choices;
- wardrobe: top, bottom and one accessory;
- scene placement;
- fixed-library animation beats: idle, walk, wave and celebrate.

Doll Blueprint v1 currently supports one shared armature with 17 rigidly-parented
bones per character. Two characters therefore produce 34 bones. This is **rigid
bone parenting**, not smooth vertex-weight skinning.

## Deterministic signatures

The compiler writes separate signatures for:

- `geometry_signature` — proportions, primitive geometry, placement and rig structure;
- `behavior_signature` — authored animation keys;
- `appearance_signature` — material definitions and assignments;
- `plan_sha256` — the complete scene plan.

Changing only a color does not change geometry identity. Changing a real
proportion does. Changing animation changes behavior without pretending geometry
changed.

## Commands

```bash
axm-avatar validate-blueprint examples/blueprint-doll-pair-v1.json
axm-avatar compile-blueprint examples/blueprint-doll-pair-v1.json /tmp/scene-plan.json
axm-avatar build-blueprint examples/blueprint-doll-pair-v1.json outputs/workbench-duo --blender /path/to/blender
```

A successful Blender run retains the input blueprint, deterministic scene plan,
compiler source and Blender builder under `creator-parts/`.

`PASS` on the run receipt means deterministic compilation and structural GLB
inspection succeeded. It is not automatic aesthetic approval or proof of likeness.
