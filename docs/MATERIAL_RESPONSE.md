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

## Blender cheap-four host verification

The cheap-four binder now has an independent EEVEE 4.3 pixel verifier. It creates isolated probe spheres through the same `make_material` path used by Blueprint builds and measures rendered A/B evidence:

- breakup: visible local detail relative to the same base material with the organ off, plus repeated-render determinism;
- sheen: increased grazing-angle rim/centre response;
- coat: a measurable increase in the high-end highlight response over the rough base;
- anisotropy: measurable difference from isotropic shading and measurable response to a quarter-turn of the authored anisotropy orientation.

The receipt is written to `material-response-proof/receipt.json` and its proof PNGs remain in that directory. `verified_render_receipt` is deliberately scoped to these Blender/EEVEE probe scenes. It does not claim physical accuracy, numerical equivalence with the donor reference host, aesthetic acceptance, or game-engine parity.

The Blueprint run still remains HOLD whenever requested organs such as subsurface or wear layering are not yet bound, even if all cheap-four probes pass.

## EEVEE anisotropy correction

The Blender 4.3 manual marks Principled anisotropy as Cycles-only and EEVEE anisotropy as unsupported. Avatar Machine therefore does **not** promote `surface.anisotropy` to bound in the EEVEE host.

For EEVEE, the requested anisotropy organ stays `HOLD_EEVEE_ANISOTROPY_UNSUPPORTED`. The builder may apply the Opus pack's declared fallback — directionally stretched roughness — as a separately named `directional_roughness` fallback. Pixel evidence for that fallback is stored separately from `render_verified_organs`.

The breakup probe also uses a resolvable authored 40 mm scale for the host capability test. This proves the breakup node path can produce deterministic visible roughness/color variation; it does not claim that pore-scale 1–3 mm breakup must be visibly resolved in a 96×96 or full-body render.

## EEVEE subsurface core

Avatar Machine now binds the EEVEE-supported core of `surface.subsurface`:

- `Subsurface Weight`;
- per-channel `Subsurface Radius`, normalized from the pack's RGB millimetre distances;
- `Subsurface Scale`, set from the largest requested radius in metres;
- Principled `BURLEY` / Christensen-Burley method.

Blender 4.3 documents Random Walk skin methods, subsurface IOR and subsurface anisotropy as Cycles-only. The pack's separate subsurface `tint` also has no separate Principled EEVEE socket while Avatar Machine keeps the Blueprint palette authoritative. Therefore skin-living remains partially held as `HOLD_SUBSURFACE_TINT_UNMAPPED_IN_PRINCIPLED_EEVEE`.

The Blender verifier measures the implemented SSS core under strong backlighting. A successful receipt proves visible Burley weight/radius/scale behavior in the named EEVEE probe only; it does not upgrade the unmapped tint field or claim Cycles Random Walk skin equivalence.

## Subsurface probe geometry correction

The first EEVEE subsurface probe used a metre-scale sphere against millimetre-scale scattering distances and correctly failed the visual threshold. That was a poor capability stimulus, not evidence that the socket binding itself was absent.

The verification scene now uses a thin backlit shell geometry and a deliberately larger RGB scattering radius only for the isolated host-capability probe. The actual `skin-living` family values remain unchanged. This keeps the test strict while making the physical effect resolvable: the probe asks whether EEVEE Burley SSS can visibly carry backlight through a thin flesh-like form, not whether a full-body metre-scale sphere glows.
