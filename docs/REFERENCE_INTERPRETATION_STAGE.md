# Replaceable Reference Interpretation Stage

Reference-image interpretation is now an explicit **optional boundary** rather
than hidden magic inside the deterministic Avatar Machine.

## What is implemented

Avatar Machine can now:

1. copy supplied reference-image bytes into a portable local packet;
2. hash every reference;
3. hand the packet to either a human-authored response or an explicitly configured
   external/local interpreter adapter;
4. validate that the response refers to the exact reference hashes;
5. validate the proposed Doll Blueprint v1 fields;
6. emit an interpretation receipt and the accepted blueprint;
7. send that blueprint through the same deterministic compiler as a human-authored one.

## What is not implemented

Avatar Machine itself still does **not** infer likeness or design semantics from
arbitrary image pixels.

Without a human response or configured adapter, the command stops with an
explicit hold. Therefore the repository still must not claim native automatic
photo-to-avatar conversion.

## Portable packet

```bash
axm-avatar reference-packet work/reference-packet person.jpg side-view.png
```

The new directory contains:

```text
work/reference-packet/
  reference-packet.json
  references/
    000-person.jpg
    001-side-view.png
```

The JSON records hashes and relative paths. It does not depend on hidden absolute
workstation paths.

## Human response

A response must use schema `axm.avatar.interpretation-response/v1` and name its
method/provider. `reference_sha256` must exactly match the packet ordering.

```json
{
  "schema": "axm.avatar.interpretation-response/v1",
  "method": "HUMAN_AUTHORED",
  "provider": "creator-name",
  "reference_sha256": ["<hash-from-packet>"],
  "blueprint": { "...": "valid axm.avatar.blueprint/v1" }
}
```

Then:

```bash
axm-avatar interpret-reference   work/reference-packet/reference-packet.json   work/accepted-interpretation   --response response.json
```

## Replaceable adapter protocol

An optional executable adapter is invoked without a shell:

```text
ADAPTER --packet /path/reference-packet.json --output /temporary/response.json
```

The adapter is responsible for reading the packet's relative reference paths and
writing the same interpretation-response schema. It can be a local vision model,
a platform model wrapper or another tool. Avatar Machine records the named
provider and validates the result, but does not treat that provider as permanent
or privileged.

This keeps AI optional: humans and AI author the same blueprint contract, while
geometry, materials, rigging, animation, export and structural verification stay
deterministic after the blueprint boundary.
