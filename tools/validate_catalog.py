from __future__ import annotations

import argparse
from pathlib import Path

from orbitfabric.adapter_manager import AdapterCatalog, select_exact_release


def validate(path: Path) -> AdapterCatalog:
    catalog = AdapterCatalog.model_validate_json(path.read_text(encoding="utf-8"))

    referenced_bindings = {
        source.binding
        for adapter in catalog.adapters
        for release in adapter.releases
        for source in release.sources
    }
    declared_bindings = {binding.id for binding in catalog.source_bindings}
    unused_bindings = sorted(declared_bindings - referenced_bindings)
    if unused_bindings:
        raise ValueError(f"Catalog contains unused source bindings: {unused_bindings}")

    release_count = 0
    for adapter in catalog.adapters:
        for release in adapter.releases:
            selected = select_exact_release(
                catalog,
                adapter.source_coordinate,
                release.version,
            )
            if selected.release_descriptor_digest != release.release_descriptor_digest:
                raise AssertionError("Exact selection changed the release descriptor digest")
            release_count += 1

    print(
        f"Catalog valid: {len(catalog.adapters)} adapters, "
        f"{release_count} releases, {len(catalog.source_bindings)} source bindings"
    )
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path, nargs="?", default=Path("catalog.json"))
    args = parser.parse_args()
    validate(args.catalog)


if __name__ == "__main__":
    main()
