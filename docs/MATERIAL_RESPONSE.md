# Avatar material response intake

The user-supplied Opus material-response pack adds 13 named surface families composed from eight behaviors: subsurface, sheen, anisotropy, coat, breakup, transmission, iridescence and wear layering.

Avatar Machine preserves those families as optional Blueprint material intent.

Current truth:
- Blueprint selection/validation: implemented.
- Deterministic scene-plan retention: implemented.
- Avatar palette/base-color authority: preserved.
- Base roughness/metallic/specular projection into the generic Blender material: implemented.
- Organ-specific Blender behavior: **not yet bound/verified**.
- Supplied reference host: 8/8 checks pass, but those receipts are host-specific.
- Recovered Odd Shift profile: unchanged.

A Blueprint that selects active response organs may still produce structural Blender/GLB output, but its run receipt must remain HOLD until the Blender host earns its own organ receipts. Zero-weight response controls remain a true no-op.

## Blender cheap-four binding pass

The next integration step follows the supplied Opus package route rather than inventing a second material model.

The generic Blender 4.x host now constructs bindings for:

- `surface.breakup` — deterministic 4D Noise Texture driven from object coordinates; roughness and base-color modulation remain separate;
- `surface.sheen` — Principled `Sheen Weight`, `Sheen Roughness`, and optional tint;
- `surface.coat` — Principled `Coat Weight`, `Coat Roughness`, `Coat IOR`, and optional tint;
- `surface.anisotropy` — Principled anisotropy plus an explicit radial-Z object tangent for `tangent_u/tangent_v` requests.

Grain/custom-vector anisotropy remains HOLD until a mesh-owned direction field exists. Subsurface, transmission, iridescence and wear layering remain HOLD in this pass.

**Binding is not verification.** These organs remain `declared_contract_match_not_tested` for Blender until their donor verify measurements are ported and pass against Blender renders.

The CI now also runs a real Python 3.11 + `bpy==4.3.0` generic Blueprint build, checks the 900×900 poster, editable blend, GLB, structural inspection and host binding receipts, and uploads the proof pack as a workflow artifact. This raises the generic path above syntax-only evidence without pretending the visual organ tests have passed.

Zero-weight organ controls compile to an empty binding plan: no response sockets or response nodes are introduced by the organ binder.
