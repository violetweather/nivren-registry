"""Verifies every published release in the registry tree.

Usage: python tools/verify_registry.py --niv <niv-binary>

For every v1/packages/<name>/<version>.nivpkg, runs
`niv registry verify-release` against its provenance, the publisher's
authorization, the signed status, the advisories, and the pinned root key.
A release blocked by an active advisory counts as verified-yanked, not as a
failure — the block is the advisory doing its job.
"""

import argparse
import pathlib
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--niv", required=True)
    arguments = parser.parse_args()
    registry = pathlib.Path(__file__).resolve().parent.parent
    now = str(int(time.time()))
    verified = 0
    yanked = 0
    failures = []
    import json
    for artifact in sorted(registry.glob("v1/packages/*/*.nivpkg")):
        name = artifact.parent.name
        version = artifact.stem
        provenance_path = registry / "v1/provenance" / name / f"{version}.json"
        publisher = json.load(open(provenance_path))["publisher"]
        result = subprocess.run(
            [
                arguments.niv, "registry", "verify-release",
                artifact, provenance_path,
                registry / "v1/authorizations" / f"{publisher}.json",
                registry / "v1/trust/status.json",
                registry / "v1/trust/advisories.json",
                registry / "v1/trust/root.pub",
                now, "0",
            ],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            verified += 1
        elif "blocked by advisory" in result.stderr + result.stdout:
            yanked += 1
            print(f"yanked  {name} {version}")
        else:
            failures.append(f"{name} {version}: {result.stderr.strip()}")
    print(f"verified {verified} releases, {yanked} yanked by advisory")
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"  {failure}")
        sys.exit(1)


if __name__ == "__main__":
    main()
