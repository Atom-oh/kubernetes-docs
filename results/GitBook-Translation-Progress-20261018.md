# GitBook translation progress

Checkpoint: 2026-10-18T11:09:31.112462+00:00

All three GitBook languages now contain counterparts for all 693 English Markdown pages. Three managed Codex subagents running `openai.gpt-6-luna` perform the local translation and full-page comparison. Local API helpers remain stopped; original provenance is retained for imported translations until their actual native review is complete.

| Locale | English source pages | Present | Missing | Validated changes in this checkpoint | Existing pages failing source structure checks | Current complete native review records |
|---|---:|---:|---:|---:|---:|---:|
| cn | 693 | 693 | 0 | 51 | 83 | 154 |
| jp | 693 | 693 | 0 | 10 | 306 | 158 |
| es | 693 | 693 | 0 | 43 | 209 | 164 |

**Quality review: IN PROGRESS.** File coverage and structural checks do not certify source fidelity or natural wording. All 693 pages per language, including retained translations, require genuine complete-page review with current source/target hashes and scores of at least 85. These counts are snapshots; the PR remains a draft and has not been deployed. Two earlier Chinese/Japanese reviews have saved-byte canonical-ID-only derivations awaiting producer reconciliation. They retain their real prior scores and are not counted as current unchanged-target reviews above.

This checkpoint stages 104 additional Markdown changes whose complete fenced code, link destinations, heading/fence counts and language size thresholds match English. 42 edited legacy pages remain excluded from the checkpoint while their agents repair them. All three navigation inventories contain the complete 690 required English references, with no missing, extra or broken entries at the coverage check.

The Spanish agent reviewed every EKS Hybrid Nodes page and rebuilt stale sections against current English. Networking guidance, bootstrap requirements, workload and GPU caveats now retain the source conditions. The newly completed Chinese Cilium chapters and Windows quiz likewise preserve current English code and version scope. Further legacy pages still need full semantic reconciliation.

The unified Actions workflow scans cn/jp/es together, serializes translation batches, persists retry checkpoints and accumulates one translation branch and PR. Reviewed translations on main supersede obsolete draft contents during import and refresh. Future Actions translation uses GPT-6-Luna; provider errors stop before queue mutation. Current manual completion uses native Codex subagents rather than those API helpers.

`npm run docs:validate` passes all 176 repository tests, all 94 bilingual news records, Korean/English links and language parity, and referenced PNG checks for all five locales. `npm run docs:gitbook:check` passes all three complete page/navigation inventories. The anchor helper now checks English heading hierarchy on every translated page, including unreferenced pages, and adds IDs only where authored source fragments or explicit IDs require them. Its five tests verify hierarchy, protected code, fragment behavior and side-effect-free help/invalid options.

All five CI validation/build jobs at `4a2ae7cc` pass. This complete five-locale build finished in 17:31.05, with a 4,633 MB site, 7,644 MB peak process RSS and 7,964 MB peak build disk usage. It generated all 235 README redirects without missing-page warnings. These results apply to that pushed snapshot; this checkpoint will receive a new CI run.

Native GPT-6.1-Sol separately completed 67 whole-page wording reviews, preserving source/target hashes, concrete findings and resolutions in `Native-Sol-Wording-Review-20261018.json`. They include the earlier Spanish Flink and VPC Lattice pages, Japanese SUMMARY, and sixty-four Chinese pages. Twenty-eight additional read-only Chinese comparisons by the native host retain their honest host reviewer identity and exact snapshots. Their records enter the producer ledger only after current-byte verification; neither set substitutes for the remaining full-language review.

Assets are copied from English with identical bytes and without Markdown rewrites during parallel editing. Asset-only scans report no unresolved image destinations in their snapshots; new repairs can introduce further references. The Cilium ASCII-diagram padding remains byte-identical to English protected code and is classified separately from prose whitespace.

Actual VitePress renderer and authored-fragment audits are retained as diagnostic snapshots. Final acceptance requires zero malformed bold text, Vue compilation failures, heading hierarchy differences or broken local fragments across every locale. The last complete actual VitePress/Vue renderer scan examined all 3,465 pages across English, Korean, Chinese, Japanese and Spanish and found zero Vue compilation failures or literal bold markers. Its byte snapshots precede ongoing native edits, so it is a diagnostic checkpoint rather than final acceptance. Chinese emphasis-only repairs fixed 894 malformed regions across 113 previously unreviewed pages; a subsequent actual VitePress parse of every affected page found zero remaining literal markers. The repair preserves prose after removal of emphasis delimiters and exact fenced code; it is not a semantic quality review. No final multilingual render/fragment pass is claimed yet.

English drift remains zero across the 693 frozen source blobs. All 1,040 changed English/Korean documents preserve protected code, link destinations, heading/fence counts and explicit anchors. Final review aggregation and translation-state updates reject incomplete or stale native evidence; source hashes are never marked current solely because a file exists.

The earlier anchor CLI help incident is documented in `Native-Anchor-Repair-Review-20261018.json`: 171 changes were exact deterministic canonical-ID-only transformations. Genuine prior review scores are retained only where saved reviewed bytes prove that exact transformation. A Spanish wrong-checkout edit was separately backed up and restored at its single affected root-checkout path; the authorized worktree correction and review were retained and verified against its own English source.
