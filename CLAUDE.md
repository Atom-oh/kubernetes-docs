# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kubernetes and Amazon EKS training content hosted on GitBook/VitePress. Documentation-only project — no application code, no test/lint/CI pipelines beyond the automation described below. All content is Markdown.

**Korean (`ko/`) and English (`en/`) are the human-edited source languages.** `cn/`, `jp/`, and `es/` are machine-translated mirrors of `en/`, kept up to date by `.github/workflows/translate-backfill.yml` and `translate-sync.yml` (see "Automated Translation" below) — **never hand-edit files under `cn/`, `jp/`, or `es/`**; edit `en/` and let sync pick it up, or re-run the backfill workflow for that section.

**GitBook URL**: https://atomoh.gitbook.io/kubernetes-docs/

## Build Commands

```bash
# Build Istio presentation slides (requires marp-cli: npm install -g @marp-team/marp-cli)
cd slide && bash build-presentation.sh
```

## Repository Structure

The repo is organized as a mirrored tree per language: `ko/`, `en/`, `cn/`, `jp/`, `es/` have identical directory structures. The canonical source of navigation for each language is its `SUMMARY.md` — always consult these for the current content tree. `cn/`/`jp/`/`es/` fill in section-by-section as `translate-backfill.yml` runs, so their trees may currently be a subset of `en/`'s.

**Top-level layout:**

- `README.md` — Language selector (root)
- `assets/` — Shared images/diagrams (SVG, PNG, HTML, drawio) used by all languages
- `slide/` — Marp presentation sources and build script
- `scripts/` — `translate.sh` (kiro-cli-based single-file translation), `validate-translation.py` (structural sanity check), `sync-nav.py` (SUMMARY.md/README.md nav entry sync for translated sections)
- `ko/`, `en/`, `cn/`, `jp/`, `es/` — Mirrored content trees, each containing:
  - `SUMMARY.md` — GitBook navigation (canonical structure)
  - `README.md` — Table of contents with learning/quiz/lab link pairs
  - Content directories: `basics/`, `core/`, `eks/`, `eks-hybrid-nodes/`, `eks-auto-mode/`, `ai-ml/`, `networking/` (with `cilium/`, `calico/` subtrees), `service-mesh/` (with `istio/`, `linkerd/`, `cilium-service-mesh/` subtrees), `security/`, `gitops/` (with `argocd/` subtree), `autoscaling/`, `observability/` (with `metrics/`, `logging/`, `tracing/`, `alerting/`, `grafana/` subtrees), `scheduling/`, `platform-engineering/`, `ops/`
  - `quizzes/` — Mirrors content structure
  - `labs/` — Hands-on lab guides (basics, core, eks, observability)

**Asset path references** vary by nesting depth: `../../assets/` from `ko/basics/`, `../../../assets/` from `ko/service-mesh/istio/`, etc.

## Adding or Renaming Content — Files to Keep in Sync

When adding, removing, or renaming any content page, update **all of these in both languages**:

1. **`ko/SUMMARY.md`** and **`en/SUMMARY.md`** — GitBook navigation. Uses GitBook's indentation format: `*` for top-level, indented `*` for children. Multi-part topics use a parent entry linking to part 1, with indented child entries for each part.
2. **`ko/README.md`** and **`en/README.md`** — Table of contents. Each entry follows the pattern: `[Title](./path.md) | [퀴즈/Quiz](./quizzes/path-quiz.md)` and optionally `| [실습/Lab](./labs/path-lab.md)`.
3. **`ko/quizzes/`** and **`en/quizzes/`** — Every content file should have a corresponding quiz.
4. **Subdirectory README files** — Some content sections have their own `README.md` (e.g., `observability/README.md`, `networking/README.md`, `gitops/README.md`). Update if adding a new subsection.

## Content Conventions

### Document Header Format

Not all documents include "Supported Versions" — some only have "Last Updated". Use whichever fields are relevant.

Korean:
```markdown
# Document Title
> **지원 버전**: ...        <!-- optional, include if version-specific -->
> **마지막 업데이트**: 2025년 X월 X일
```

English:
```markdown
# Document Title
> **Supported Versions**: ...  <!-- optional, include if version-specific -->
> **Last Updated**: Month Day, 2025
```

### Quiz Format

Korean quizzes use `<details><summary>정답 보기</summary>`, English quizzes use `<details><summary>Show Answer</summary>`:

```markdown
1. Question text
   - A) Option A
   - B) Option B
<details>
<summary>정답 보기</summary>  <!-- or "Show Answer" in en/ -->

**정답: B) Option B**  <!-- or "Answer: B) Option B" in en/ -->

**설명:**  <!-- or "Explanation:" in en/ -->
Explanation text here.

</details>
```

### Naming Conventions

- Content files: `NN-topic-name.md` (e.g., `01-linux-basics.md`)
- Multi-part topics: `NN-topic-name-partN.md` (e.g., `02-eks-cluster-creation-part1.md`)
- Quiz files: mirror content path under `quizzes/` with `-quiz` suffix (e.g., `quizzes/basics/01-linux-basics-quiz.md`)
- Lab files: mirror content path under `labs/` with `-lab` suffix (e.g., `labs/basics/01-linux-basics-lab.md`)
- Subdirectory introductions: `README.md` within the subtree (e.g., `networking/cilium/README.md`)
- **Exception — Istio, Linkerd, and Cilium Service Mesh quizzes** use topic-based names without numbers: `quizzes/service-mesh/istio/traffic-management.md`, `quizzes/service-mesh/linkerd/architecture.md`, etc.

### Bilingual Content Parity (ko/en)

Korean and English documents cover identical topics but are **not literal translations**. They may use different formatting for the same concept (e.g., tables vs. ASCII diagrams). When editing, ensure both languages convey the same information, but don't force identical formatting. (This applies to `ko`/`en` only — `cn`/`jp`/`es` are literal machine translations of `en`, see below.)

### Automated Translation (cn/jp/es)

`en/` is the single source for `cn/`, `jp/`, and `es/` (not `ko/` — English is the more token-efficient source and already mirrors `ko/`'s coverage). Two workflows keep them in sync:

- **`translate-backfill.yml`** (`workflow_dispatch`, pick a `section`): translates every untranslated file under `en/<section>/` (+ its `quizzes/`/`labs/` counterparts) into the requested languages via `kiro-cli` (headless, `scripts/translate.sh`), appends that section's nav entries into `cn/jp/es`'s `SUMMARY.md`/`README.md` (`scripts/sync-nav.py`), and opens one PR per run after a Bedrock-based quality gate (same ≥85/100 pattern as the news digest). Re-running for a section already done is a no-op (per-file skip-if-exists).
- **`translate-sync.yml`** (triggered on `push` to `main` touching `en/**/*.md`): re-translates only the files whose `cn/jp/es` counterpart already exists, so it never gets ahead of the section-by-section backfill.

Both use `kiro-cli chat --model gpt-5.5 --no-interactive --trust-tools=fs_read,fs_write` on the `kubernetes-docs-claude-arm` runner (kiro-cli ignores stdin and has a 128KiB argv limit, so it reads/writes the doc files itself rather than having content piped in). `.github/i18n-heading-map.json` caches each `SUMMARY.md`/`README.md` heading's translation so re-running backfill for a later section doesn't retranslate (and drift) a heading created by an earlier one.

When adding a brand-new top-level content section, no extra config is needed here — `translate-backfill.yml`'s `section` dropdown just needs that directory name added as a choice, and the section's own README/SUMMARY entries follow the existing convention automatically.

### Automated News-Driven Updates

`.github/workflows/weekly-news-digest.yml` runs weekly, matches fresh Kubernetes/EKS/CNCF news against `.github/news-topic-map.yml`, and updates the matched doc(s) in place in both `ko/` and `en/` (bumping the header's "마지막 업데이트"/"Last Updated" date) rather than writing a separate news file. Unmatched news is recorded as a link-only line in `ko/news/README.md` / `en/news/README.md`'s "갱신 로그"/"Update Log" — those two files are the only ones under `news/`; no per-week files are created.

When adding a new top-level content section that should participate in this pipeline (i.e., news about it should get auto-applied rather than always falling through to link-only), add a matching entry to `.github/news-topic-map.yml`.
