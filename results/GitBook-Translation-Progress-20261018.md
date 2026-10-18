# GitBook translation progress

Checkpoint: 2026-10-18T12:14:08.403163+00:00

Chinese, Japanese and Spanish each contain all 693 English Markdown counterparts and all 690 required navigation references. Three managed native Codex subagents running `openai.gpt-6-luna` perform full-page source comparisons and repair retained translations. Local model API helpers remain stopped.

| Locale | English pages | Present | Missing | Validated Markdown changes in this checkpoint | Existing pages failing source structure checks | Genuine current complete reviews | Remaining reviews |
|---|---:|---:|---:|---:|---:|---:|---:|
| cn | 693 | 693 | 0 | 27 | 79 | 269 | 424 |
| jp | 693 | 693 | 0 | 12 | 290 | 192 | 501 |
| es | 693 | 693 | 0 | 26 | 198 | 217 | 476 |

**Quality review: IN PROGRESS.** The 678 current complete reviews include two saved-byte-proven canonical-ID-only derivations retaining their original genuine scores. The other 676 records match their reviewed target bytes directly. Historical repeated Japanese reviews are retained for provenance and counted once per page. File presence, unchanged bytes and structural checks never manufacture semantic reviews or quality grades. Every page requires a genuine whole-page comparison with current source/target hashes and an actual score of at least 85. The PR remains a draft without deployment.

This checkpoint stages 65 validated Markdown changes. Their complete fenced code, link destinations, heading/fence counts and language size thresholds match English. Forty-two edited legacy pages remain excluded while their agents repair source differences. The last explicit Japanese translation fallback, the Kafka benchmark guide, now has a complete native Japanese translation and source comparison. Its eight code blocks, benchmark caveats and source image links are preserved.

Native GPT-6.1-Sol completed 109 whole-page wording reviews: 106 Chinese pages, two Spanish pages and Japanese SUMMARY. Actual findings, resolutions, original scores, source/target hashes and saved reviewed bytes are retained in `Native-Sol-Wording-Review-20261018.json`. Thirty-nine additional Chinese whole-page comparisons retain the native host's honest reviewer identity. All imported records are checked against current bytes. Their genuine work contributes to the counts above and does not replace the remaining full-language reviews.

The unified Actions workflow scans cn/jp/es together, serializes batches, persists retry checkpoints and accumulates one translation branch and PR. Reviewed translations on main supersede obsolete draft outputs during import and refresh. Future Actions translation uses GPT-6-Luna; provider errors stop before queue mutation. Current manual completion uses native Codex subagents.

All five CI validation/build jobs at `3d20ed55` passed. The full five-locale build completed in 18:07.87 with a 4,635 MB site, 7,683 MB peak process RSS and 7,989 MB peak build disk usage. It generated all 235 README redirects without missing-page warnings. Validation passed all 176 repository tests, all 94 bilingual news records, Korean/English links and parity, and referenced PNG checks across all five locales. These results apply to that pushed snapshot; this checkpoint receives a new CI run. The three complete GitBook page/navigation inventories also pass.

The latest actual VitePress/Vue renderer audit examined all 3,465 pages and found zero Vue compilation failures and zero literal bold markers. Authored local fragment checks also found zero failures across all five locales. These are byte-specific diagnostic snapshots, not final multilingual acceptance: retained translations still have 53 Chinese, 166 Japanese and 98 Spanish heading hierarchy differences. Final acceptance requires complete current reviews and fresh renderer, hierarchy and fragment checks on every page.

Assets are copied from English with identical bytes and without Markdown rewrites during parallel editing. This checkpoint adds two byte-verified Japanese Kafka benchmark images. Its asset-only scan reports zero unresolved destinations. Earlier Chinese emphasis repairs fixed 894 malformed regions across 113 pages while preserving prose and exact fenced code; those repairs alone are not semantic reviews.

English drift remains zero across the 693 frozen source blobs, and the branch contains the latest fetched main commit. All 1,040 changed English/Korean documents preserve protected code, link destinations, heading/fence counts and explicit anchors. Review aggregation rejects stale source/target bytes, incomplete full-page evidence and unresolved findings. Translation state is finalized only after all 2,079 genuine current reviews and final global checks pass.

The earlier anchor CLI help incident remains documented in `Native-Anchor-Repair-Review-20261018.json`. Its 171 changes were exact deterministic canonical-ID transformations. Genuine prior scores are retained only where saved reviewed bytes prove that transformation. A Spanish wrong-checkout edit was backed up and restored at its single affected primary-checkout path; the authorized worktree correction and review were retained. Intentional source-identical Cilium ASCII padding remains protected code.
