"""Re-signs the registry's trust documents for the Nivren 1.0.1 format.

Usage:
  python tools/resign_trust.py --niv <niv> --root-secret <root.secret> \
      --generation <n> [--status-days 90]

What changes and why:
  * Publisher authorizations gain a `packages` list (which package names
    the key may release) and are signed under the v2 domain. The list comes
    from tools/publishers.json; a publisher not listed there is refused.
  * Every advisory is re-signed under the v2 domain, which length-prefixes
    the affected-version set instead of joining it with a separator byte.
  * The status carries `advisories_sha256`, the digest of the served
    advisory list, so a host cannot drop advisories while serving a valid
    status. It is signed at the requested (strictly higher) generation.

Package archives and their provenance are untouched: the provenance format
did not change, and artifacts are immutable.
"""

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import time


def run(command):
    result = subprocess.run([str(part) for part in command], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"command failed: {' '.join(map(str, command))}\n{result.stdout}{result.stderr}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--niv", required=True)
    parser.add_argument("--root-secret", required=True)
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--status-days", type=int, default=90)
    arguments = parser.parse_args()

    registry = pathlib.Path(__file__).resolve().parent.parent
    niv = pathlib.Path(arguments.niv)
    trust = registry / "v1/trust"
    now = int(time.time())

    current = json.loads((trust / "status.json").read_text(encoding="utf-8"))
    if arguments.generation <= current["generation"]:
        sys.exit(
            f"generation must exceed the published generation {current['generation']}"
        )

    publishers = json.loads((registry / "tools/publishers.json").read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as scratch:
        scratch = pathlib.Path(scratch)

        # Authorizations: same key, repository, workflow, and expiry as the
        # published document, now bound to an explicit package list.
        for path in sorted((registry / "v1/authorizations").glob("*.json")):
            authorization = json.loads(path.read_text(encoding="utf-8"))
            publisher = authorization["publisher"]
            if publisher not in publishers:
                sys.exit(f"tools/publishers.json does not list publisher {publisher!r}")
            key_file = scratch / f"{publisher}.pub"
            key_file.write_text(authorization["public_key"] + "\n", encoding="utf-8")
            run([
                niv, "trust", "authorize", publisher, key_file,
                authorization["repository"], authorization["workflow"],
                str(authorization["expires_at"]), arguments.root_secret, path,
                ",".join(publishers[publisher]),
            ])
            print(f"re-authorized {publisher} for {', '.join(publishers[publisher])}")

        # Advisories: re-sign each entry and reassemble the list in order.
        advisories_path = trust / "advisories.json"
        advisories = json.loads(advisories_path.read_text(encoding="utf-8"))
        resigned = []
        for index, advisory in enumerate(advisories):
            unsigned = scratch / f"advisory-{index}.json"
            signed = scratch / f"advisory-{index}.signed.json"
            advisory["signature"] = ""
            unsigned.write_text(json.dumps(advisory, indent=2) + "\n", encoding="utf-8")
            run([niv, "trust", "sign-advisory", unsigned, arguments.root_secret, signed])
            resigned.append(json.loads(signed.read_text(encoding="utf-8")))
            print(f"re-signed advisory {advisory['id']}")
        advisories_path.write_text(json.dumps(resigned, indent=2) + "\n", encoding="utf-8")

        # Status: strictly higher generation, digest of the served advisories.
        unsigned = scratch / "status-unsigned.json"
        unsigned.write_text(json.dumps({
            "generation": arguments.generation,
            "issued_at": now,
            "expires_at": now + arguments.status_days * 86400,
            "revoked_keys": current["revoked_keys"],
            "frozen_packages": current["frozen_packages"],
            "advisories_sha256": "",
            "signature": "",
        }, indent=2) + "\n", encoding="utf-8")
        run([
            niv, "trust", "sign-status", unsigned, arguments.root_secret,
            trust / "status.json", advisories_path,
        ])
        print(f"signed status generation {arguments.generation}")


if __name__ == "__main__":
    main()
