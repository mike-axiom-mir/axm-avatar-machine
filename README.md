# AXM Avatar Machine

Standalone extraction of the proven Odd Shift Duo doll/avatar generator. The
real Blender builder, renderer and verifier live here; this repository does not
import, clone, read or call Universal Creation.

## What Doll Profile v1 does now

One common pipeline regenerates the pre-authored Odd Shift Duo and can package:

1. `visual` — poster plus four representative proof frames.
2. `clip` — H.264 animated preview.
3. `3d` — editable Blender source plus GLB.
4. `animated-3d` — Blender source, shared joint hierarchy, rigid-part animation and GLB plus clip manifest.

The historical result is retained under `fixtures/odd-shift-duo/historical/`
and is decoded by tests rather than trusted from an old report.

Each new run also writes `creator-parts/`. That directory is the reusable source
memory: the exact request, blueprint, profile, visual contract, builder/renderer/
verifier source, semantic primitive/assembly catalog, material controls, named
part transforms, rig hierarchy and authored motion keyframes. The poster, movie
and GLB are secondary realizations; the retained construction causes are the
part that can grow through later human or AI-directed recombination.

The retained state also has a semantic atom index. Identical local geometry is
one atom even when it has another name, placement or color. Material node/
behavior structure defines a material-family atom; base and emission colors are
appearance overrides. Exact variants remain reproducible, but do not inflate the
machine's growth count.

## Truth boundary

The exact local generator is present and independently runnable. It authors the
geometry, materials, 34-joint shared rig, four animation beats, GLB, `.blend`,
poster and preview. The decoded historical and fresh GLBs both contain one skin
record but **zero mesh-to-skin bindings**: the proven motion model is rigid mesh
parts parented to joints, not smooth vertex-weight deformation.

The original photograph-to-character interpretation is **not** present as
executable code. It was model/platform assisted and its decisions are hard-coded
into this profile. Supplying an arbitrary new reference image therefore fails
with `HOLD_PLATFORM_MODEL_ASSISTED`; it is not silently ignored and is not
claimed as an automatic local capability.

The no-AI-friendly growth path is an explicit Avatar Blueprint that either a
person or an optional AI can author. The same deterministic builder then owns
geometry, materials, rigging, animation, export and verification. The first
candidate blueprint is visible in the doll profile; general blueprint compilation
is not yet claimed.

| Boundary | Status |
| --- | --- |
| Rebuild the proven Odd Shift doll profile | Implemented locally |
| Blender source, GLB, rig, animation, still and clip | Implemented locally with Blender |
| Structural GLB/media verification | Implemented locally; ffprobe is external |
| Rigid joint-parented GLB animation | Implemented locally and reproduced |
| Smooth skinned-mesh deformation | Not present in the historical asset; not claimed |
| New photo/reference to a newly interpreted avatar | HOLD — platform/model-assisted stage not recovered |
| UC runtime dependency | None |

## Requirements

- Python 3.11 or newer.
- Blender 4.x available as `blender`, `AXM_AVATAR_BLENDER`, or `--blender PATH`;
  alternatively Python 3.11 with `bpy==4.3.0`, selected using `--bpy-python PATH`.
- `ffprobe` for movie verification.
- Optional Pillow (`pip install -e '.[visual-regression]'`) for poster pixel-difference metrics.

## Run

```bash
python -m pip install -e .
axm-avatar profile
axm-avatar build examples/odd-shift-duo.json outputs/odd-shift-duo --blender /path/to/blender
# Or: axm-avatar build examples/odd-shift-duo.json outputs/odd-shift-duo --bpy-python /path/to/python
```

The output directory must not already exist. The run produces logs, hashes,
standalone structural inspection, Blender verification, historical regression
comparison, proof frames and `Avatar-Machine-Doll-v1.zip`.

Inspect a GLB without Blender:

```bash
axm-avatar inspect-glb fixtures/odd-shift-duo/historical/Odd-Shift-Duo.glb
```

Run repository tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

See `docs/UC_EXTRACTION_MAP.md` for the pre-change map,
`docs/UC_EXTRACTION_PROVENANCE.md` for exact origins and adaptations, and
`docs/AVATAR_BLUEPRINT_DIRECTION.md` for the shared human/AI intent layer.

## Licensing

The existing PolyForm Noncommercial license and Creator Output Permission are
preserved. The software and creator outputs intentionally have different
permission boundaries; see `LICENSE`, `CREATOR_OUTPUT_PERMISSION.md`, and
`docs/LICENSING.md`.
