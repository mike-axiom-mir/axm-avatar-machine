# UC extraction provenance

## Source truth

The current Universal Creation repository was inspected at commit
`9381bd850a32c9c76a9aff4a04d4687f5a87b1ae`, including all fetched refs and
reachable history. No Odd Shift Duo generator or named output artifact exists
there. UC contains other real character paths (OOPS and Chaos Hero), but their
geometry, rigs and contracts are different and were not substituted.

The exact executable source was recovered from the retained delivery
`Odd-Shift-Duo-Package.zip`, SHA-256
`4099449a58d90b86132d5653d5079024d8b332aac45b5ebb295c89e6dcaeff2e`.
That package contained the generator, renderer, verifier, editable Blender
source, GLB, poster, preview and receipts.

## File provenance

| Original package path | Avatar Machine path | Treatment |
| --- | --- | --- |
| `build_funny_duo.py` | `blender/build_doll_v1.py` | Copied, then removed two Codex-host absolute Python paths, accepted ordinary Python arguments, guarded removed Eevee properties, added Blender 4.x Eevee compatibility, and added a machine-readable snapshot of the actual named parts/materials/rig/keyframes. Geometry, materials, rig and animation authorship retained. |
| `render_funny_duo.py` | `blender/render_doll_v1.py` | Copied, then accepted ordinary Python arguments and an explicit `.blend` path, and added Blender 4.x Eevee compatibility. Rendering behavior retained. |
| `verify_funny_duo.py` | `blender/verify_doll_v1.py` | Copied, then accepted ordinary Python arguments and an explicit `.blend` path so the same checks run under either Blender CLI or the external `bpy` module. Verification criteria retained. |
| `animation_manifest.json` | `profiles/doll/odd-shift-duo/animation_manifest.json` | Copied unchanged. |
| `VISUAL_CONTRACT.md` | `profiles/doll/odd-shift-duo/VISUAL_CONTRACT.md` | Copied unchanged. |
| Historical `.blend`, `.glb`, `.png`, `.mp4`, metrics and reports | `fixtures/odd-shift-duo/historical/` | Copied unchanged as regression evidence. |

Locally authored extraction machinery lives in `src/axm_avatar_machine/`. It
resolves Blender, executes the copied scripts, decodes GLB structure, probes
media, compares the fresh result with the historical fixture, packages selected
output modes, preserves the executable construction source and part state under
`creator-parts/`, groups repeated geometry and color-only material variants into
semantic atoms, and records hashes and truth boundaries. It contains no UC import
or runtime path.

## Dependency reasons

- Blender 4.x: the proven implementation is Blender Python and uses `bpy`,
  `mathutils`, the glTF exporter, Eevee and Blender's FFmpeg integration.
- `ffprobe`: independently inspects the produced H.264 preview.
- Python 3.11+: local orchestration, JSON/GLB inspection, hashing and packaging.
- Pillow (optional): pixel-difference measurement only; it is not needed to
  build or structurally verify the asset.

## Capability origin classification

| Stage | Classification | Evidence |
| --- | --- | --- |
| Reference photo understanding and likeness decisions | PLATFORM/MODEL ASSISTED | No parser or vision model call exists in the retained source; decisions are hard-coded. |
| Doll geometry construction | IMPLEMENTED LOCALLY | `blender/build_doll_v1.py` authors named Blender geometry. |
| Materials/appearance | IMPLEMENTED LOCALLY | 28 authored Blender materials and named appearance parts. |
| Rig and rigid-part animation | IMPLEMENTED LOCALLY | One 34-joint shared armature with rigid bone parenting. |
| Smooth skin binding/deformation | NOT PRESENT IN PROVEN ASSET | Both retained and fresh GLBs contain one skin record but zero nodes that reference it. |
| Animation | IMPLEMENTED LOCALLY | One synchronized action with four marked beats. |
| Blender, glTF export and render engines | EXTERNAL TOOL | Blender 4.x. |
| GLB/media structural verification | IMPLEMENTED LOCALLY + EXTERNAL TOOL | Local decoder plus Blender/ffprobe checks. |
| Arbitrary new reference to new avatar | NOT REPRODUCED | Explicit HOLD until an executable local interpretation stage exists. |
| Original source photograph | UNKNOWN | Not present in the retained package and intentionally not embedded in the asset. |
