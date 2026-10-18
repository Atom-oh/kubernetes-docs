# GitBook translation progress

Checkpoint: 2026-10-18T09:18:17.768835+00:00

Local translation uses three managed Codex subagents running `openai.gpt-6-luna`. The former local API helpers and duplicate Translate Sync run were stopped. Existing validated translations are retained with their original provenance.

| Locale | English source pages | Present | Missing | Changed files in this checkpoint | Existing pages still failing structure checks |
|---|---:|---:|---:|---:|---:|---:|
| cn | 693 | 683 | 10 | 13 | 105 |
| jp | 693 | 686 | 7 | 12 | 320 |
| es | 693 | 693 | 0 | 6 | 258 |

31 additional changed Markdown files pass exact fenced-code, link-target, heading/fence-count and size validation. Six edited legacy Japanese pages were excluded because they still need complete source reconciliation; their in-progress edits remain local. The previous checkpoints retained 452, 132, 96, 53, 29 and 25 validated changes.

**Quality review: IN PROGRESS.** Structural validation does not certify source fidelity or wording. Native agents still need to review all retained translations, repair stale technical prose, and complete missing pages. This checkpoint has not been deployed.

Spanish now has all 693 English counterparts. Its agent is reconciling legacy EKS Hybrid Nodes pages first, including the firewall and networking guidance identified by the user. Offline review bundles contain complete English/translated prose and source/target hashes; they make no model calls and assign no quality scores. Final review aggregation and translation-state updates refuse incomplete or stale native review evidence.

An asset checkpoint copied 208 referenced locale images from the English source, with identical bytes and no Markdown edits. The asset-only scan found no unresolved image destinations in the pages present at that checkpoint. Missing-page translations may add further references.

The source-fragment inventory found zero unresolved English fragments. The canonical-anchor helper adds explicit IDs only where source links or explicit IDs require them, preserves authored code/link bytes, and rejects translations whose heading structure still differs from English. Locale agents apply it before recording final content-review hashes.

The unified Actions workflow scans all English pages for cn/jp/es together, preserves retry checkpoints, and accumulates one translation PR. Reviewed translations on main supersede obsolete draft retry queues during import and refresh. All 174 repository tests pass. This report records a snapshot, not live coverage.

A real VitePress renderer audit with default syntax highlighting compiled all pages present in its snapshot without Vue errors: en/ko 693 each, cn 640, jp 649, es 671. English, Korean and Spanish had zero literal bold-marker text regions; Chinese and Japanese rendering findings remain assigned to their native locale agents. This does not certify final coverage or prose quality.

Native GPT-6.1-Sol separately corrected and reviewed Spanish Flink operations, Spanish VPC Lattice comparison, and Japanese SUMMARY. Verified complete-page quality scores are 93, 95 and 96; source/target hashes, specific findings and corrections are retained in `Native-Sol-Wording-Review-20261018.json`. These three reviews do not substitute for the remaining full multilingual review.

The GitHub build at checkpoint `3cfe2820` failed because a newly translated page referenced an image not yet included in that checkpoint. The follow-up `6ac17068` included 33 additional referenced images; all five validation/build jobs and GitBook previews pass. The full five-locale build completed in 16:18.65 with a 4,480 MB site. Subsequent asset-only checkpoints copied six and seven more referenced images without changing Markdown and found zero unresolved image references in their snapshots. The missing Japanese SUMMARY entries were restored with native translated labels and reviewed by Sol.

The latest local Markdown link scan found broken destinations only for pages missing at scan time. No final link or coverage pass is claimed. English source drift is zero across the 693 frozen source blobs, and the bilingual news dashboard still verifies all 94 records.

Changes to the unified translation workflow now trigger the normal PR validation workflow even when no document or script changes accompany them. YAML syntax and the single translation-job/model/concurrency settings were checked locally.

The `f79992db` validation job exposed a test that assumed the Japanese kernel page was missing. That page is now translated. The Markdown fallback test now uses an isolated file inventory through the existing file-existence lookup; its five tests and the complete `docs:validate` command pass, including all 174 tests, 94 news records, source-language links/parity, and referenced PNG checks for all five locales. CI validation at `498c37f0` also passes; the full five-locale build is running at this checkpoint.

The latest asset-only checkpoint copied 13 further referenced images with identical English bytes, zero unresolved image destinations and no Markdown rewrites.

Two lines in the Spanish Cilium eBPF page have trailing spaces inside an ASCII code diagram. They are byte-identical to the English protected code and are retained intentionally. The whitespace findings include no changed prose.
