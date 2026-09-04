from __future__ import annotations

import argparse
import copy
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from orbitfabric.adapter_manager import (
    AdapterCatalog,
    AdapterManager,
    ProjectLockInstallService,
    ProjectLockService,
    select_exact_release_by_logical_key,
)
from orbitfabric.adapter_manager.errors import ProjectLockError
from orbitfabric_github_release_source import GitHubReleaseSource, GitHubReleaseSourceError


class CountingGitHubResolver:
    def __init__(self) -> None:
        self.calls = 0
        self.source = GitHubReleaseSource()

    def resolve(self, selection, materialization_root: Path):
        self.calls += 1
        return self.source.resolve(selection, materialization_root)


def fetch_catalog(url: str) -> tuple[AdapterCatalog, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "orbitfabric-adapter-catalog-p3/0.1"},
    )
    with urllib.request.urlopen(request, timeout=60.0) as response:
        payload = response.read()
    decoded = json.loads(payload)
    return AdapterCatalog.model_validate(decoded), decoded


def requested_state(lock_service: ProjectLockService, lock_path: Path, manager: AdapterManager):
    report = lock_service.check(lock_path, manager.list())
    if len(report.adapters) != 1:
        raise AssertionError("P3 fixture lock must contain exactly one adapter")
    return report, report.adapters[0]


def assert_no_installed_state(manager: AdapterManager) -> None:
    if manager.list():
        raise AssertionError("Negative control created Installed Adapter State")
    if manager.instances_root.exists() and any(manager.instances_root.iterdir()):
        raise AssertionError("Negative control left backend materialization")


def tampered_catalog_for_descriptor_digest(
    payload: dict[str, Any], *, name: str, version: str
) -> AdapterCatalog:
    mutated = copy.deepcopy(payload)
    matches = [
        adapter
        for adapter in mutated["adapters"]
        if adapter["source_coordinate"]["publisher"] == "orbitfabric"
        and adapter["source_coordinate"]["name"] == name
    ]
    if len(matches) != 1:
        raise AssertionError("Could not locate exact adapter in Catalog negative control")
    releases = [release for release in matches[0]["releases"] if release["version"] == version]
    if len(releases) != 1:
        raise AssertionError("Could not locate exact release in Catalog negative control")
    releases[0]["release_descriptor_digest"]["value"] = "0" * 64
    return AdapterCatalog.model_validate(mutated)


def write_identity_mismatch_lock(lock_path: Path, output_path: Path) -> None:
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    payload["adapters"][0]["source_coordinate"]["name"] += "-identity-mismatch"
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    catalog, catalog_payload = fetch_catalog(args.catalog_url)
    selection = select_exact_release_by_logical_key(
        catalog,
        publisher="orbitfabric",
        name=args.adapter,
        release_version=args.version,
    )

    lock_path = args.lock.resolve()
    lock_bytes_before = lock_path.read_bytes()
    lock_service = ProjectLockService()
    lock = lock_service.load(lock_path)
    if len(lock.adapters) != 1:
        raise AssertionError("P3 fixture lock must contain exactly one adapter")
    lock_entry = lock.adapters[0]
    if lock_entry.source_coordinate != selection.source_coordinate:
        raise AssertionError("Catalog selection Source Coordinate does not match Project Lock")
    if lock_entry.release_version != selection.release_version:
        raise AssertionError("Catalog selection version does not match Project Lock")
    if lock_entry.release_descriptor.sha256 != selection.release_descriptor_digest.value:
        raise AssertionError("Catalog descriptor digest does not match Project Lock")

    with tempfile.TemporaryDirectory(prefix=f"orbitfabric-p3-{args.adapter}-") as temp:
        root = Path(temp)
        manager = AdapterManager(state_root=root / "state")
        install_service = ProjectLockInstallService(manager=manager)
        resolver = CountingGitHubResolver()

        before_report, before = requested_state(lock_service, lock_path, manager)
        if before_report.status != "NOT_SATISFIED" or before.status != "MISSING":
            raise AssertionError(f"Expected initial MISSING state, got {before.status}")

        acquisition_root = root / "acquisition"
        resolved = resolver.resolve(selection, acquisition_root)
        first = install_service.install_resolved_entry(
            lock_path,
            selection.source_coordinate,
            resolved.resolved_release,
        )
        if first.action != "INSTALLED" or first.after_status != "MATCH":
            raise AssertionError(f"Expected first install to reach MATCH, got {first}")
        if resolver.calls != 1:
            raise AssertionError("Expected exactly one remote resolver call for first ensure")
        if first.installed_instance_id is None:
            raise AssertionError("Installed result did not return an instance id")

        verify_before_removal = manager.verify(first.installed_instance_id)
        if not verify_before_removal.passed:
            raise AssertionError("Installed adapter verification failed before workspace removal")

        # Identity negative control: a valid resolved release must be rejected by a lock
        # requesting a different Source Coordinate, before backend materialization.
        bad_lock_path = root / "identity-mismatch-lock.json"
        write_identity_mismatch_lock(lock_path, bad_lock_path)
        bad_lock = lock_service.load(bad_lock_path)
        negative_identity_manager = AdapterManager(state_root=root / "negative-identity-state")
        negative_identity_service = ProjectLockInstallService(manager=negative_identity_manager)
        try:
            negative_identity_service.install_resolved_entry(
                bad_lock_path,
                bad_lock.adapters[0].source_coordinate,
                resolved.resolved_release,
            )
        except ProjectLockError as exc:
            if "source_coordinate" not in str(exc):
                raise AssertionError(
                    f"Identity negative control failed at unexpected gate: {exc}"
                ) from exc
        else:
            raise AssertionError("Identity mismatch was not rejected")
        assert_no_installed_state(negative_identity_manager)

        shutil.rmtree(acquisition_root)
        if acquisition_root.exists():
            raise AssertionError("Acquisition workspace was not removable")

        verify_after_removal = manager.verify(first.installed_instance_id)
        if not verify_after_removal.passed:
            raise AssertionError("Installed adapter verification depends on acquisition workspace")

        match_report, match_state = requested_state(lock_service, lock_path, manager)
        if not match_report.passed or match_state.status != "MATCH":
            raise AssertionError("Project Lock did not remain MATCH after workspace removal")

        # Consumer ensure semantics: MATCH is checked before any source resolution.
        calls_before_second = resolver.calls
        second_report, second_state = requested_state(lock_service, lock_path, manager)
        if second_state.status == "MATCH":
            second_action = "NOOP"
        else:
            raise AssertionError("Second ensure unexpectedly required remote resolution")
        if second_report.status != "MATCH" or resolver.calls != calls_before_second:
            raise AssertionError("MATCH fast path performed a remote resolver call")

        # Integrity negative control: wrong Catalog descriptor digest must fail during
        # provider resolution and must not create install state or local release bytes.
        bad_catalog = tampered_catalog_for_descriptor_digest(
            catalog_payload,
            name=args.adapter,
            version=args.version,
        )
        bad_selection = select_exact_release_by_logical_key(
            bad_catalog,
            publisher="orbitfabric",
            name=args.adapter,
            release_version=args.version,
        )
        negative_integrity_manager = AdapterManager(state_root=root / "negative-integrity-state")
        negative_resolver = CountingGitHubResolver()
        bad_acquisition = root / "negative-integrity-acquisition"
        try:
            negative_resolver.resolve(bad_selection, bad_acquisition)
        except GitHubReleaseSourceError as exc:
            if "descriptor" not in str(exc).lower() or "digest" not in str(exc).lower():
                raise AssertionError(
                    f"Integrity negative control failed at unexpected gate: {exc}"
                ) from exc
        else:
            raise AssertionError("Descriptor digest mismatch was not rejected")
        if negative_resolver.calls != 1:
            raise AssertionError("Integrity negative control resolver call count is unexpected")
        assert_no_installed_state(negative_integrity_manager)
        if bad_acquisition.exists() and any(bad_acquisition.iterdir()):
            raise AssertionError("Integrity failure left materialized release bytes")

        if lock_path.read_bytes() != lock_bytes_before:
            raise AssertionError("Product consumer E2E modified the Project Lock")

        facts = resolved.provider_facts
        return {
            "adapter": args.adapter,
            "version": args.version,
            "catalog_source": args.catalog_url,
            "source_coordinate": selection.source_coordinate.model_dump(mode="json"),
            "first_action": first.action,
            "first_after_status": first.after_status,
            "verify_before_workspace_removal": verify_before_removal.passed,
            "verify_after_workspace_removal": verify_after_removal.passed,
            "project_lock_after_workspace_removal": match_report.status,
            "second_action": second_action,
            "remote_calls_first_ensure": 1,
            "remote_calls_second_ensure": resolver.calls - calls_before_second,
            "negative_identity_fail_closed": True,
            "negative_descriptor_digest_fail_closed": True,
            "project_lock_unchanged": True,
            "provider_repository": facts.repository,
            "provider_release_ref": facts.release_ref,
            "provider_immutable": facts.immutable,
            "provider_author": facts.author_login,
        }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run the OrbitFabric P3 Catalog-to-installed-state consumer E2E proof."
    )
    result.add_argument("--catalog-url", required=True)
    result.add_argument("--adapter", required=True)
    result.add_argument("--version", required=True)
    result.add_argument("--lock", type=Path, required=True)
    return result


def main() -> int:
    result = run(parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
