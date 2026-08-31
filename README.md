# The Nivren package registry

This repository is the live Nivren package registry, served as static files
through GitHub Pages at:

```text
https://violetweather.github.io/nivren-registry
```

## How trust works

Nothing on this host is trusted. Every guarantee is verified on the
installing machine against one pinned Ed25519 root key:

```text
8c26f6f713c20f165ca76d6e42424ca1498a78277647674b35d8d33dfa93bec7
```

Install with:

```text
niv install --trusted https://violetweather.github.io/nivren-registry <root-key-file>
```

The client fetches `v1/trust/root.pub`, refuses it unless it matches the key
you pinned, then verifies the root-signed status document (with rollback
protection through strictly increasing generations), the root-signed
publisher authorization, the publisher-signed release provenance, the
package digest, and every advisory — all locally, before a single file is
installed. A tampered host, a replayed old status, a yanked release, or an
unauthorized publisher all fail closed.

## Layout

```text
v1/trust/root.pub                    the registry public key
v1/trust/status.json                 root-signed status and generation
v1/trust/advisories.json             root-signed advisories
v1/packages/<name>/<version>.nivpkg  immutable package artifacts
v1/provenance/<name>/<version>.json  publisher-signed release provenance
v1/authorizations/<publisher>.json   root-signed publisher authorizations
```

Published artifacts are immutable: a version is never replaced, only yanked
through a signed status or advisory update. The git history of this
repository is the public audit log.

## Operations

The signed status expires after 90 days, so installs stay fresh: the
registry owner re-signs and redeploys it with
`python tools/build_registry.py` (or `niv trust sign-status` alone) before
expiry. Yanks, key revocations, and advisories ship the same way — a signed
document update and a commit, never a deleted artifact.

Publishing is a pull request carrying the package artifact and its signed
provenance; it merges only when the signature chain verifies against an
authorized publisher key.
