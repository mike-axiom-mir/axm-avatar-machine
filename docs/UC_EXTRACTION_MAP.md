# Doll Profile v1 extraction map

Written before implementation changes. This map distinguishes the current UC
repository from the retained Odd Shift Duo delivery package that contains the
actual executable source.

## Evidence baseline

- UC repository: `mike-axiom-mir/axm-universal-creation`
- UC commit inspected: `9381bd850a32c9c76a9aff4a04d4687f5a87b1ae`
- UC refs/history inspected: all fetched remote refs and reachable commits
- Exact Odd Shift source present in UC: **no**
- Retained executable source: `Odd-Shift-Duo-Package.zip`
- Retained package SHA-256: `4099449a58d90b86132d5653d5079024d8b332aac45b5ebb295c89e6dcaeff2e`

The retained package is therefore the primary source for the proven Odd Shift
implementation. UC remains the historical machine context, but the extraction
must not falsely attribute package-only source to a UC commit.

## Extraction decisions

| Source file | Purpose | Required? | Decision | Dependencies |
| --- | --- | ---: | --- | --- |
| `Odd-Shift-Duo-Package.zip/build_funny_duo.py` | Actual Blender geometry, 28-material appearance, shared 34-joint rig, four animation beats, editable `.blend`, GLB export and poster render | Yes | COPY + ADAPT | Blender `bpy`, `mathutils`, Python stdlib |
| `Odd-Shift-Duo-Package.zip/render_funny_duo.py` | Render selected review frames or the animated H.264 preview from the built `.blend` | Yes | COPY + ADAPT | Blender `bpy`, Blender FFmpeg support |
| `Odd-Shift-Duo-Package.zip/verify_funny_duo.py` | Inspect Blender scene, GLB structure, hand contact, materials, clip markers and video metadata | Yes | COPY + ADAPT | Blender `bpy`, `ffprobe`, Python stdlib |
| `Odd-Shift-Duo-Package.zip/animation_manifest.json` | Four clip ranges and loop intent | Yes | COPY | None at runtime beyond JSON |
| `Odd-Shift-Duo-Package.zip/VISUAL_CONTRACT.md` | Historical identity, style, animation and delivery contract | Yes | COPY | None |
| `Odd-Shift-Duo-Package.zip/Odd-Shift-Duo.blend` | Historical editable source and regression benchmark | Yes | COPY as fixture | Blender for deep inspection |
| `Odd-Shift-Duo-Package.zip/Odd-Shift-Duo.glb` | Historical exported structural benchmark | Yes | COPY as fixture | Local GLB parser |
| `Odd-Shift-Duo-Package.zip/Odd-Shift-Duo-Poster.png` | Historical visible benchmark | Yes | COPY as fixture | Image viewer |
| `Odd-Shift-Duo-Package.zip/Odd-Shift-Duo-Preview.mp4` | Historical motion benchmark | Yes | COPY as fixture | Video player / `ffprobe` |
| `Odd-Shift-Duo-Package.zip/build_stats.json` | Historical build metrics | Yes | COPY as fixture | None |
| `Odd-Shift-Duo-Package.zip/verification.json` | Historical claimed checks and measurements | Yes, but not trusted alone | COPY as fixture | Fresh verification must supersede claims |
| UC `src/axm_uc/rigged_characters.py` | OOPS-specific UC orchestration and GLB inspection | No for Odd Shift | LEAVE in UC; reimplement only generic local inspection needed by Avatar Machine | UC atomic/visual-learning/visual-3d modules |
| UC `tools/blender/axm_oops_character.py` | Fixed OOPS character generator | No | LEAVE in UC | UC Blender forge helpers |
| UC `tools/blender/axm_chaos_hero.py` plus detail/surface/motion helpers | Separate fixed character interpretation based on an illustration | No | LEAVE in UC | Multiple UC Blender helpers |
| UC `tools/blender/verify_rigged_character.py` and `verify_chaos_hero.py` | Verification for other character families | No | LEAVE in UC | Their respective UC builders/contracts |
| UC `src/axm_uc/game_character_expression.py` | Static renderer-neutral expression/stance derivation; no skeleton or clips | No | LEAVE in UC | UC surface-3D stack |
| UC `src/axm_uc/game_animation_runtime.py` | Clip-clock/state runtime; does not load or deform GLB | No | LEAVE in UC | UC runtime contracts |

## Dependency boundary

Avatar Machine will retain Blender 4.x, Blender's bundled glTF exporter,
FFmpeg/ffprobe, and ordinary Python libraries where required. It will not import
UC, read UC paths, call UC as a service, or require chat history.

The absolute Codex/Python paths embedded in the historical builder are an
environment accident and will be removed. The local orchestration, inspection,
tests, profile configuration and packaging code will live in Avatar Machine.

## Truth hold discovered before extraction

The historical builder does **not** parse a photograph or infer a new person.
Its likeness decisions are hard-coded geometry, materials and proportions that
were authored with platform/model assistance from an unseen reference. The
extractable local capability is exact regeneration and adaptation of the proven
Odd Shift doll profile. Arbitrary `reference image -> new avatar` interpretation
remains `HOLD_PLATFORM_MODEL_ASSISTED` until a real local interpretation stage
is implemented and verified.
