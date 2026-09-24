# OrbitFabric Adapter Catalog

Canonical, version-controlled index of OrbitFabric adapter releases and their acquisition source bindings.

The Catalog is a **data product**, not a registry service and not an adapter package repository. It records the minimum provider-neutral information required to select one exact adapter release:

```text
Adapter Source Coordinate
+ exact Release Version
+ expected Release Descriptor SHA-256
+ source binding reference(s)
```

Artifact membership remains owned by each adapter's `adapter-release.json` Release Descriptor and is intentionally not duplicated here.

## Indexed exact releases (including historical identity)

```text
OpenOBSW/OpenSVF   0.1.0
OpenC3 COSMOS      0.1.0, 0.2.0
F Prime            0.1.1, 0.1.2
EDS-cFS            0.1.0
```

OpenC3 COSMOS currently demonstrates Source Coordinate coexistence across the GitHub ownership migration. Historical `0.1.0` remains under `github.com/FAROTECH`; post-migration `0.2.0` uses `github.com/OrbitFabric`. Both resolve through the canonical physical Organization repository binding.

## What Catalog membership means

A Catalog entry means that an exact adapter release is indexed for deterministic acquisition. It does **not** by itself mean:

```text
OrbitFabric-maintained
trusted publisher
official adapter
endorsed downstream integration
authenticated publication
```

Trust and acceptance remain separate from Catalog identity.

## Community contributions

Community-maintained adapters are welcome to propose Catalog entries through pull requests. A contribution should publish an OrbitFabric-compatible Release Descriptor and stable release artifacts first, then add the exact release identity and source binding here.

The first Catalog lane is exact-release only. It does not provide `latest`, `stable`, version ranges or automatic upgrades.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Manual installation remains supported

The Catalog is an additive discovery/acquisition convenience. OrbitFabric's explicit/manual release path remains valid for private, experimental, project-local or uncatalogued adapters.

## Format ownership

The Catalog data model and exact-selection semantics are owned by OrbitFabric Core. This repository owns maintained Catalog **contents**, not a second schema definition.

`catalog_version` identifies the Catalog data format. It is not the revision number of this repository's contents. Content history is tracked through Git commits, pull requests and, when introduced, data-product tags.

## Post-migration authority and exact selection

Decision 004 makes `github.com/OrbitFabric` the only current authority for OrbitFabric-maintained releases. Historical FAROTECH coordinates and descriptor digests above remain immutable. Operational binding identifiers now use `github-orbitfabric-*`; physical repositories are unchanged.

Core selects logical key plus exact requested version across all records: one match succeeds, zero fails, multiple fail as ambiguous. Historical COSMOS 0.1.0 does not make Organization COSMOS 0.2.0 ambiguous. No authority preference or remapping applies.

Unpublished candidate versions must not enter `catalog.json`. After approved release publication, add each exact descriptor digest and canonical coordinate, retaining historical entries.
