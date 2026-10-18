# GitBook translation progress

Checkpoint: 2026-10-18T07:47:17.247062+00:00

Local translation uses three managed Codex subagents running `openai.gpt-6-luna`. The former local API helpers and duplicate Translate Sync run were stopped. Existing validated translations are retained with their original provenance.

| Locale | English source pages | Present | Missing | Changed files in this checkpoint |
|---|---:|---:|---:|---:|
| cn | 693 | 557 | 136 | 235 |
| jp | 693 | 570 | 123 | 64 |
| es | 693 | 587 | 106 | 153 |

452 changed Markdown files pass exact fenced-code, link-target, heading/fence-count and size validation. 0 changed files were excluded from this checkpoint because validation was incomplete.

**Quality review: IN PROGRESS.** Structural validation does not certify source fidelity or wording. Native agents still need to review all retained translations, repair stale technical prose, and complete missing pages. This checkpoint is local and has not been deployed.

The unified Actions workflow scans all English pages for cn/jp/es together, preserves retry checkpoints, and accumulates one translation PR. The workflow changes passed all 161 repository tests.
