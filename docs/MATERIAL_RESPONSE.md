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
