# Odd Shift Duo

An original, rigged comedy duo built from the supplied photo reference. The models are stylized rather than biometric scans, but preserve the visible likeness anchors and wardrobe contrast.

## Deliverables

- `Odd-Shift-Duo.blend` — editable Blender source and showcase set.
- `Odd-Shift-Duo.glb` — game-ready combined duo with one shared armature and animation.
- `Odd-Shift-Duo-Preview.mp4` — animation preview.
- `Odd-Shift-Duo-Poster.png` — poster render.
- `animation_manifest.json` — clip ranges for engine-side splitting.
- `build_funny_duo.py` and `render_funny_duo.py` — reproducible source scripts.
- `verification_report.txt` — fresh asset checks.

## Animation timeline

The GLB carries a synchronized `OddShift_Duo_Demo` animation. Split it using the manifest:

| Clip | Frames | Intent |
|---|---:|---|
| Curious Idle | 1–32 | Contrasting breathing, head tilts, side-eye |
| Swagger Walk | 33–72 | In-place game walk with mismatched rhythm |
| High Five | 73–104 | Anticipation, contact, recoil |
| Victory | 105–144 | Chaos celebrates while Deadpan shrugs |

Playback is authored at 24 fps. All showcase scenery is excluded from the GLB.
