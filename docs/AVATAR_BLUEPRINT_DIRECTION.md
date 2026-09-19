# Avatar Blueprint direction

The non-AI-friendly target is not `photo -> hidden model magic -> asset`. It is:

`reference or idea -> explicit Avatar Blueprint -> deterministic compiler -> verified outputs`

A person must be able to author the blueprint with ordinary controls: landmark
placement, proportions, named face/hair/clothing choices, palette, material
character, rig selection and motion beats. An AI may propose or revise the same
fields, but receives no private construction capability and is never required
for rebuild, export or verification.

`profiles/doll/odd-shift-duo/avatar-blueprint.json` makes the first profile's
high-level decisions visible. The current builder does not yet compile arbitrary
blueprints; geometry values are still in the proven Python source. Moving those
values behind bounded blueprint fields is the next capability-growth step after
the exact profile has been reproduced. Until that happens, the candidate schema
is direction and inspectable provenance, not a claimed general generator.

## Growth memory

Every successful build retains `creator-parts/`, including the exact executable
source and a machine-readable snapshot of the named parts, material controls,
rig hierarchy and motion keyframes that produced the realizations. Free creation
can only grow safely by proposing variations over retained causes, testing them,
and accepting useful parts or recipes into a later library. A render or GLB by
itself is evidence/output, not the machine's learned construction vocabulary.

The snapshot groups identical local geometry as one canonical atom and records
placements/materials as instances. Material-family identity ignores base and
emission color while retaining node structure and non-color controls. Cosmetic
variants stay reproducible but do not pretend to be machine growth.
