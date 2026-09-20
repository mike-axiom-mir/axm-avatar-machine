# AXM Avatar Machine

Standalone AXM doll/avatar creation pipeline.

The recovered Odd Shift Duo generator is preserved as **Doll Profile v1**, and a
new bounded human-first Doll Blueprint compiler now lives beside it. This
repository does not import, clone, read or call Universal Creation or MorphTile.

## Proven baseline: Doll Profile v1

One common recovered pipeline regenerates the pre-authored Odd Shift Duo and can package:

1. `visual` — poster plus four representative proof frames.
2. `clip` — H.264 animated preview.
3. `3d` — editable Blender source plus GLB.
4. `animated-3d` — Blender source, shared joint hierarchy, rigid-part animation and GLB plus clip manifest.

The historical result remains under `fixtures/odd-shift-duo/historical/` and is
decoded by tests rather than trusted from an old report.

The exact retained source truth remains unchanged: the original
photograph-to-character interpretation was model/platform assisted and was not
present in the recovered executable source. The historical and fresh GLBs use
rigid bone-parented pieces, not smooth vertex-weight deformation.

## New: Doll Blueprint compiler v1

A person or optional AI can now author `axm.avatar.blueprint/v1` for the bounded
`stylized-doll` family. The compiler produces a deterministic scene plan and a
new generic Blender builder realizes that plan into:

- editable `.blend`;
- animated GLB;
- poster;
- structural inspection;
- run receipt;
- retained `creator-parts/` with blueprint, scene plan and exact source.

The compiler separates geometry, behavior and appearance signatures. A color-only
change does not pretend to be geometry growth.

Example:

```bash
axm-avatar validate-blueprint examples/blueprint-doll-pair-v1.json
axm-avatar compile-blueprint examples/blueprint-doll-pair-v1.json /tmp/scene-plan.json
axm-avatar build-blueprint examples/blueprint-doll-pair-v1.json outputs/workbench-duo --blender /path/to/blender
```

The old Odd Shift builder is not rewritten by this compiler and remains the
regression oracle.

## New: optional reference interpretation boundary

Reference photos can be packaged into a portable hashed packet:

```bash
axm-avatar reference-packet work/reference-packet person.jpg side-view.png
```

A human can author the blueprint response, or an explicitly configured replaceable
adapter can propose it. Avatar Machine validates the exact reference hashes and
the blueprint before accepting it.

```bash
axm-avatar interpret-reference   work/reference-packet/reference-packet.json   work/accepted   --response response.json
```

Or with an explicit adapter:

```bash
axm-avatar interpret-reference   work/reference-packet/reference-packet.json   work/accepted   --adapter /path/to/interpreter-adapter
```

**Important:** Avatar Machine itself still does not infer arbitrary likeness from
image pixels. With no human response or configured adapter, interpretation remains
an explicit hold. This is not a native automatic photo-to-avatar claim.

## Creator-parts / growth truth

Generated images, videos and GLBs are secondary realizations. Successful runs
retain the causes used to build them. Repeated placement/name/color variants do
not automatically count as new construction atoms.

## Capability boundary

| Boundary | Status |
| --- | --- |
| Rebuild proven Odd Shift doll profile | Implemented locally |
| Odd Shift Blender source, GLB, rigid rig/animation, still and clip | Implemented locally with Blender |
| Human-authored bounded stylized-doll blueprint -> deterministic scene plan | Implemented locally |
| Doll Blueprint v1 scene plan -> editable Blender + animated GLB + poster | Implemented; requires Blender runtime |
| Structural GLB verification | Implemented locally |
| Reference packet + human/external interpretation response validation | Implemented locally |
| Native arbitrary photo pixels -> interpreted new avatar | **Not implemented**; requires an explicit human/provider |
| Smooth skinned-mesh deformation | Not implemented in Doll v1; not claimed |
| Realistic/cartoon/mascot general profile families | Not implemented yet |
| UC/MorphTile runtime dependency | None |

## Requirements

- Python 3.11 or newer.
- Blender 4.x available as `blender`, `AXM_AVATAR_BLENDER`, or `--blender PATH`;
  alternatively Python 3.11 with `bpy==4.3.0`, selected using `--bpy-python PATH`.
- `ffprobe` for recovered Odd Shift movie verification.
- Optional Pillow for historical poster regression metrics.

## Existing Doll Profile v1 run

```bash
python -m pip install -e .
axm-avatar profile
axm-avatar build examples/odd-shift-duo.json outputs/odd-shift-duo --blender /path/to/blender
```

Inspect any GLB without Blender:

```bash
axm-avatar inspect-glb path/to/file.glb
```

Run repository tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

See:

- `docs/UC_EXTRACTION_MAP.md`
- `docs/UC_EXTRACTION_PROVENANCE.md`
- `docs/AVATAR_BLUEPRINT_DIRECTION.md`
- `docs/BLUEPRINT_COMPILER_V1.md`
- `docs/REFERENCE_INTERPRETATION_STAGE.md`

## Licensing

The existing PolyForm Noncommercial license and Creator Output Permission remain
unchanged. See `LICENSE`, `CREATOR_OUTPUT_PERMISSION.md`, and `docs/LICENSING.md`.
