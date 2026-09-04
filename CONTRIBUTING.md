# Contributing to the OrbitFabric Adapter Catalog

The Catalog is maintained through reviewable pull requests.

## Adding a community adapter release

Before opening a Catalog PR, publish the adapter release in its source repository with:

```text
adapter-release.json
all descriptor-declared release artifacts
stable provider release reference
```

The Release Descriptor must already contain the exact OrbitFabric Source Coordinate and Release Version that the Catalog entry will reference.

Provider-reported release immutability may contribute trust evidence when available, but it is not a Catalog identity prerequisite. The Catalog remains fail-closed because the exact Release Descriptor SHA-256 is anchored here.

A Catalog PR then adds:

1. the exact `source_coordinate`, if the adapter is new;
2. the exact release version and expected Release Descriptor SHA-256;
3. one or more source references;
4. a source binding when the required binding does not already exist.

Do not copy artifact membership or artifact digests from the Release Descriptor into the Catalog.

## Exactness rules

Catalog release identity is exact:

```text
Source Coordinate + exact Release Version + Release Descriptor SHA-256
```

Version strings are not normalized. `0.1.0` and `v0.1.0` are different strings; provider-specific values such as GitHub tag `v0.1.0` belong in `release_ref`.

Existing historical release anchors should normally be append-only. Changing an existing release version, descriptor digest or Source Coordinate requires an explicit corrective rationale and evidence that the Catalog entry itself was wrong.

## Community ownership and trust

The Catalog accepts third-party/community adapter identities. Repository ownership, GitHub uploader identity and Catalog membership do not automatically establish OrbitFabric publisher authentication, endorsement or official status.

Do not add invented `official`, `trusted`, ranking or endorsement fields to `catalog.json`.

## Validation

Pull-request CI validates:

- the Catalog against the promoted OrbitFabric Core model;
- exact selection of every recorded release;
- initial canonical release anchors;
- source-binding referential hygiene;
- that Catalog records do not duplicate descriptor-owned artifact membership.

Provider/live acquisition is tested separately by the product integration lane. It must converge on the same exact Catalog identity without weakening fail-closed behavior.

## Private and uncatalogued adapters

Catalog inclusion is not required to use an OrbitFabric adapter. Explicit/manual acquisition remains supported for private, experimental and project-local releases.
