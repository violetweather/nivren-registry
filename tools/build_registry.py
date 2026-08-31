"""Builds and signs the static Nivren registry tree.

Usage:
  python tools/build_registry.py --niv <niv.exe> --packages <nivren/packages> \
      --root-secret <root.secret> --publisher-secret <publisher.secret> \
      --publisher official --repository violetweather/nivren \
      --workflow .github/workflows/release.yml --commit <hex> \
      --generation <n> [--status-days 90] [--authorization-days 730]

Every artifact is written under v1/ next to this script's parent directory.
The secret keys never leave the machine; only signed JSON and the public
root key are written into the tree.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"command failed: {' '.join(map(str, command))}\n{result.stdout}{result.stderr}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--niv", required=True)
    parser.add_argument("--packages", required=True)
    parser.add_argument("--root-secret", required=True)
    parser.add_argument("--publisher-secret", required=True)
    parser.add_argument("--publisher", default="official")
    parser.add_argument("--repository", default="violetweather/nivren")
    parser.add_argument("--workflow", default=".github/workflows/release.yml")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--status-days", type=int, default=90)
    parser.add_argument("--authorization-days", type=int, default=730)
    arguments = parser.parse_args()

    registry = pathlib.Path(__file__).resolve().parent.parent
    niv = pathlib.Path(arguments.niv)
    packages = pathlib.Path(arguments.packages)
    now = int(time.time())

    (registry / "v1/trust").mkdir(parents=True, exist_ok=True)

    # The public root key: printed by keygen, derived here from re-signing a
    # zero-generation probe is unnecessary — trust keygen printed it; require
    # it to already exist or derive it via sign-status output? Simplest and
    # verifiable: the caller keeps root.pub in v1/trust/root.pub; this script
    # refuses to continue without it so the tree never ships an unpinned key.
    root_pub = registry / "v1/trust/root.pub"
    if not root_pub.exists():
        sys.exit("v1/trust/root.pub is missing; write the registry public key first")

    # Publisher authorization, root-signed.
    publisher_pub = registry / "tools" / "publisher.pub"
    if not publisher_pub.exists():
        sys.exit("tools/publisher.pub is missing; write the publisher public key first")
    authorizations = registry / "v1/authorizations"
    authorizations.mkdir(parents=True, exist_ok=True)
    run([
        niv, "trust", "authorize", arguments.publisher, publisher_pub,
        arguments.repository, arguments.workflow,
        str(now + arguments.authorization_days * 86400),
        arguments.root_secret, authorizations / f"{arguments.publisher}.json",
    ])

    # Build, place, and attest every official package.
    published = []
    for project in sorted(packages.iterdir()):
        if not (project / "niv.toml").is_file():
            continue
        manifest = (project / "niv.toml").read_text(encoding="utf-8")
        name = re.search(r'name = "([^"]+)"', manifest).group(1)
        version = re.search(r'version = "([^"]+)"', manifest).group(1)
        run([niv, "package", project])
        artifact = project / "target" / f"{name}-{version}.nivpkg"
        destination = registry / "v1/packages" / name
        destination.mkdir(parents=True, exist_ok=True)
        (destination / f"{version}.nivpkg").write_bytes(artifact.read_bytes())
        provenance = registry / "v1/provenance" / name
        provenance.mkdir(parents=True, exist_ok=True)
        run([
            niv, "trust", "attest", destination / f"{version}.nivpkg",
            arguments.publisher, arguments.repository, arguments.workflow,
            arguments.commit, arguments.publisher_secret,
            provenance / f"{version}.json",
        ])
        published.append(f"{name} {version}")

    # Advisories stay as they are if present; start empty otherwise.
    advisories = registry / "v1/trust/advisories.json"
    if not advisories.exists():
        advisories.write_text("[]\n", encoding="utf-8")

    # Signed status with the requested generation.
    unsigned = registry / "tools" / "status-unsigned.json"
    unsigned.write_text(json.dumps({
        "generation": arguments.generation,
        "issued_at": now,
        "expires_at": now + arguments.status_days * 86400,
        "revoked_keys": [],
        "frozen_packages": {},
        "signature": "",
    }, indent=2) + "\n", encoding="utf-8")
    run([
        niv, "trust", "sign-status", unsigned, arguments.root_secret,
        registry / "v1/trust/status.json",
    ])
    unsigned.unlink()

    print(f"published {len(published)} packages at generation {arguments.generation}")
    for line in published:
        print(f"  {line}")


if __name__ == "__main__":
    main()
