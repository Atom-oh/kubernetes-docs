# Full documentation review

**Request:** Review every document for factual errors, outdated guidance,
broken images and related defects, allowing the time needed for full coverage.

**Scope:** All tracked Markdown under `ko/`, `en/`, `cn/`, `jp/`, `es/`.
Korean and English are reviewed and maintained as sources. Translation
structure, links and assets are audited across all five languages; translated
content is repaired through the repository's translation workflow.

**Reference date:** 2026-09-11. Verify current product behavior against official
documentation. Historical experiments retain their actual tested versions and
measurements; current installation instructions must distinguish supported
versions from historical examples.

## Work

- [ ] Inventory every document and its navigation, counterpart, assets, links
  and review status under `docs/reviews/2026-09-11/`.
- [ ] Check every local image for existence and decoding/XML validity; check
  external image references and document links without equating access-denied
  responses with missing resources.
- [ ] Review every Korean/English content document, lab and quiz. Record one
  evidence row per fully read file; match corrections across languages and
  corresponding quiz answers.
- [ ] Verify versions, API fields, command ordering and installation/removal
  instructions using primary sources. Do not claim an AWS lab was executed
  when validation was static.
- [ ] Reconcile translation defects with the English source and the existing
  translation automation.
- [ ] Validate links, assets, parity, tests and both locale builds. Review
  changes before publishing and verify changed pages on the built site.
- [ ] Produce a complete per-document report with separate automated,
  semantic, corrected and unresolved statuses. Do not equate pattern scanning
  or a sampled review with a complete semantic review.

## Working rules

- Use disjoint domain batches for parallel reviews. Each worker writes
  `docs/reviews/2026-09-11/batches/<batch>.json` incrementally.
- Keep coverage truthful: `fullyRead` means the full source was read.
- Do not run infrastructure-changing example commands or invent benchmark
  outcomes.
- Preserve the two pre-existing untracked root documents.
- Keep the audit branch and report available across long-running sessions.
