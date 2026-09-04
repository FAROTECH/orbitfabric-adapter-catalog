from __future__ import annotations

import json
from pathlib import Path

from orbitfabric.adapter_manager import AdapterCatalog, select_exact_release
from orbitfabric.adapter_manager.models import AdapterSourceCoordinate

CATALOG_PATH = Path(__file__).parents[1] / "catalog.json"

EXPECTED_RELEASES = {
    ("github.com/FAROTECH", "orbitfabric", "openobsw-opensvf", "0.1.0"): (
        "ef1b568c06a1573b580bbb91308b1311b81ba65dca29331fcf1610fc7ee5c016"
    ),
    ("github.com/FAROTECH", "orbitfabric", "openc3-cosmos", "0.1.0"): (
        "2509a1c1c132f647abba0ebe02af49627ebbbed58d62555efd60d7cb30b48d4f"
    ),
    ("github.com/FAROTECH", "orbitfabric", "fprime", "0.1.1"): (
        "724eb67299150887167dfce8aa3ea117a163c79b6fcaff6ab105dfd35daf7464"
    ),
}


def load_catalog() -> AdapterCatalog:
    return AdapterCatalog.model_validate_json(CATALOG_PATH.read_text(encoding="utf-8"))


def test_catalog_parses_with_promoted_core_model() -> None:
    catalog = load_catalog()
    assert len(catalog.adapters) >= 3


def test_canonical_release_anchors_are_exact() -> None:
    catalog = load_catalog()
    for (authority, publisher, name, version), digest in EXPECTED_RELEASES.items():
        selected = select_exact_release(
            catalog,
            AdapterSourceCoordinate(
                authority=authority,
                publisher=publisher,
                name=name,
            ),
            version,
        )
        assert selected.release_descriptor_digest.algorithm == "sha256"
        assert selected.release_descriptor_digest.value == digest
        assert selected.sources


def test_catalog_does_not_duplicate_descriptor_owned_artifact_membership() -> None:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for adapter in payload["adapters"]:
        for release in adapter["releases"]:
            assert "artifacts" not in release
            assert "artifact" not in release


def test_every_declared_binding_is_referenced() -> None:
    catalog = load_catalog()
    referenced = {
        source.binding
        for adapter in catalog.adapters
        for release in adapter.releases
        for source in release.sources
    }
    declared = {binding.id for binding in catalog.source_bindings}
    assert declared == referenced


def test_initial_github_bindings_point_to_canonical_adapter_repositories() -> None:
    catalog = load_catalog()
    bindings = {binding.id: binding for binding in catalog.source_bindings}
    assert bindings["github-farotech-openobsw-opensvf"].config == {
        "repository": "FAROTECH/orbitfabric-openobsw-opensvf-adapter"
    }
    assert bindings["github-farotech-openc3-cosmos"].config == {
        "repository": "FAROTECH/orbitfabric-openc3-cosmos-adapter"
    }
    assert bindings["github-farotech-fprime"].config == {
        "repository": "FAROTECH/orbitfabric-fprime-adapter"
    }


def test_catalog_contains_no_trust_or_endorsement_classification_fields() -> None:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    forbidden = {"official", "trusted", "ranking", "endorsement"}

    def walk(value: object) -> None:
        if isinstance(value, dict):
            assert forbidden.isdisjoint(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
