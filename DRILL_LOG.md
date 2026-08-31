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
