# GitBook translation progress

Checkpoint: 2026-10-18T08:26:24.423072+00:00

Local translation uses three managed Codex subagents running `openai.gpt-6-luna`. The former local API helpers and duplicate Translate Sync run were stopped. Existing validated translations are retained with their original provenance.

| Locale | English source pages | Present | Missing | Changed files in this checkpoint | Existing pages still failing structure checks |
|---|---:|---:|---:|---:|---:|---:|
| cn | 693 | 631 | 62 | 30 | 105 |
| jp | 693 | 639 | 54 | 32 | 321 |
| es | 693 | 666 | 27 | 34 | 259 |

96 additional changed Markdown files pass exact fenced-code, link-target, heading/fence-count and size validation. Five edited legacy Japanese pages were excluded because they still need complete source reconciliation; their in-progress edits remain local. The previous checkpoints retained 452 and 132 validated changes.

**Quality review: IN PROGRESS.** Structural validation does not certify source fidelity or wording. Native agents still need to review all retained translations, repair stale technical prose, and complete missing pages. This checkpoint has not been deployed.

An asset checkpoint copied 208 referenced locale images from the English source, with identical bytes and no Markdown edits. The asset-only scan found no unresolved image destinations in the pages present at that checkpoint. Missing-page translations may add further references.

The source-fragment inventory found zero unresolved English fragments. The canonical-anchor helper adds explicit IDs only where source links or explicit IDs require them, preserves authored code/link bytes, and rejects translations whose heading structure still differs from English. Locale agents apply it before recording final content-review hashes.

The unified Actions workflow scans all English pages for cn/jp/es together, preserves retry checkpoints, and accumulates one translation PR. Reviewed translations on main supersede obsolete draft retry queues during import and refresh. All 174 repository tests pass. This report records a snapshot, not live coverage.
