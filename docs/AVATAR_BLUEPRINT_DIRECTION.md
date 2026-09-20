# Avatar Blueprint direction

The target is not `photo -> hidden model magic -> asset`. It is:

`reference or idea -> explicit Avatar Blueprint -> deterministic compiler -> verified outputs`

That direction now has a first executable bounded implementation:
`axm.avatar.blueprint/v1` for the `stylized-doll` family.

A person can author the blueprint with ordinary explicit controls for proportions,
palette, named face/hair/clothing choices, placement, rig preset and motion beats.
An optional AI may propose exactly the same fields. Neither gets private
construction capability.

The compiler turns those fields into `axm.avatar.scene-plan/v1`, separating
geometry, behavior and appearance signatures before Blender realizes the plan.
The new generic builder retains rigid bone parenting; it does not silently invent
smooth skin deformation.

The recovered Odd Shift Duo file at
`profiles/doll/odd-shift-duo/avatar-blueprint.json` remains historical/pre-authored
provenance and is **not rewritten** to masquerade as the new general compiler
input. Doll Profile v1 remains the regression baseline.

## Reference interpretation boundary

Reference-image handling is a separate optional layer. Avatar Machine can create a
portable hashed reference packet and validate a response from a human or an
explicitly configured replaceable interpreter adapter. Avatar Machine itself
still does not infer arbitrary likeness from pixels, so no-provider operation
remains an explicit hold.

See `docs/REFERENCE_INTERPRETATION_STAGE.md`.

## Growth memory

Every successful blueprint build retains the explicit blueprint, deterministic
scene plan, compiler source and Blender builder under `creator-parts/`. Realized
renders/GLBs remain secondary.

The compiler also follows the existing no-fake-growth rule:

- cosmetic color changes alter appearance, not geometry identity;
- real proportion/shape changes alter geometry identity;
- motion changes alter behavior identity;
- the complete plan still receives its own full digest.

This is the same useful pattern as reusable construction systems, without making
Avatar Machine depend on MorphTile, UC or any other runtime.
