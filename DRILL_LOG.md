# Registry operations drill log

Every entry here was executed against the live registry with signatures
verified client-side on a pinned root key. The git history of this
repository is the corresponding audit trail.

## 2026-08-31 — outside publishing, yank, and unyank

- **Generation 1**: the 25 official packages published under the `official`
  publisher; a consumer project installed `nivren_stats 1.0.0` from the live
  Pages URL over HTTPS and executed it.
- **Generation 2**: a second, independent publisher key (`outsider`) was
  root-authorized and published `registry_drill 1.0.0` with its own signed
  provenance. A separate consumer project installed it from the live
  registry and executed it. This is the outside-publishing exercise: the
  publisher's key never touched the root key, and the artifact verified
  end to end.
- **Generation 3 (yank)**: root-signed advisory `NIVREN-DRILL-0001` marked
  `registry_drill 1.0.0` withdrawn. A fresh install of the same dependency
  from the live registry failed closed with the advisory identifier,
  severity, and summary in the error.
- **Generation 4 (unyank)**: the advisory was re-signed with
  `withdrawn: true`. The same install succeeded again and the program ran.
- Rollback protection held throughout: each consumer records the highest
  status generation it has seen and refuses older documents.

Limitation, stated plainly: the "outside publisher" was a second key
operated by the registry owner, because the project has no outside users
yet. The flow exercised is exactly the one a real stranger will use.

## 2026-09-01 — trust-document format v2 (Nivren 1.0.1)

- **Generation 5**: every trust document re-signed with the 1.0.1 CLI
  after the 1.0.0 security review (`tools/resign_trust.py`). The status
  now commits to the served advisory list (`advisories_sha256`);
  revocation sets and advisory version sets are length-prefixed so two
  different sets can no longer sign to identical bytes; publisher
  authorizations name the packages each key may release (`official` →
  `nivren_*`, `outsider` → `registry_drill`, recorded in
  `tools/publishers.json`).
- Package archives and their provenance are unchanged: artifacts are
  immutable and the provenance format did not move. All 26 releases
  verify against the generation-5 documents with the 1.0.1 CLI.
- Compatibility: clients older than 1.0.1 cannot read the generation-5
  documents, so this tree was published only after the 1.0.1 release
  was available.
- CI now pins the registry root key independently of the checkout and
  checks the CLI archive against the release checksum manifest.
