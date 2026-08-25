# VitePress Korean and English Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish only Korean and English through VitePress while preserving the five-language GitBook source and fixing publishing-quality regressions.

**Architecture:** The Markdown tree remains the shared content layer. VitePress excludes translated mirrors and adds client-only quiz progress, while standalone validation scripts protect links, asset dimensions, and build scope.

**Tech Stack:** VitePress 1.6, Vue 3, Node.js ESM, Markdown, SVG, GitHub Actions

---

### Task 1: Limit the VitePress source set

**Files:**
- Create: `index.md`
- Modify: `.vitepress/config.ts`
- Create: `scripts/check-vitepress-scope.mjs`
- Test: `scripts/check-vitepress-scope.mjs`

- [x] Write a scope check that loads the built output or source configuration
  and fails when `cn`, `jp`, or `es` are active VitePress locales.
  (Implemented as `.vitepress/site-scope.mjs` + `scripts/__tests__/vitepress-scope.test.mjs`,
  exercised by `npm run docs:test` rather than a standalone script.)
- [x] Add a VitePress-only root landing page for Korean and English.
- [x] Exclude translated mirror directories and remove their locale rewrites.
- [x] Run `npm run docs:test`; expect exit code 0.

### Task 2: Enforce local-link correctness

**Files:**
- Create: `scripts/validate-local-links.mjs`
- Modify: `.vitepress/config.ts`
- Modify: `ko/service-mesh/02-istio.md`
- Modify: `en/service-mesh/02-istio.md`
- Modify: `en/eks/12-kubernetes-version-roadmap.md`

- [x] Write the validator and confirm it reports the known stale Istio links.
- [x] Replace stale link targets with files that exist in the current tree.
- [x] Disable `ignoreDeadLinks`.
- [x] Run the validator for `ko` and `en`; expect no missing local targets.

### Task 3: Repair diagram assets

**Files:**
- Create: `assets/diagrams/rendered/observability-overview.svg`
- Create: `assets/diagrams/rendered/msa-service-map.svg`
- Create: `assets/diagrams/rendered/aiops-architecture.svg`
- Create: `scripts/validate-image-assets.mjs`
- Modify: observability lab Markdown files in all languages
- Delete: unused 1x1 PNG files under `assets/generated-diagrams/`

- [x] Write an image validator that rejects referenced PNG files with dimensions
  below 16x16.
- [x] Confirm the validator fails on the existing observability placeholders.
- [x] Add readable shared SVG replacements and update Markdown references.
- [x] Delete unused generated 1x1 PNG exports while retaining Draw.io sources.
- [x] Run the validator; expect exit code 0.

### Task 4: Remove fake quiz landing pages

**Files:**
- Modify: `ko/SUMMARY.md`
- Modify: `en/SUMMARY.md`
- Modify: `scripts/sync-nav.py`
- Delete: `ko/quiz/**/README.md`
- Delete: `en/quiz/**/README.md`
- Delete: `en/quiz/service-mesh/istio/comparison.md`

- [x] Convert linked quiz category placeholders into label-only bullets.
- [x] Update the navigation synchronization comment and behavior to preserve raw
  group labels without expecting a destination file.
- [x] Remove placeholder and orphan files.
- [x] Generate both sidebars and verify quiz children remain correctly nested.

### Task 5: Add client-only quiz review progress

**Files:**
- Create: `.vitepress/theme/quiz-progress.ts`
- Modify: `.vitepress/theme/index.ts`
- Modify: `.vitepress/theme/custom.css`

- [x] Add DOM-level tests using deterministic HTML fixtures and Node assertions.
  (`scripts/__tests__/quiz-progress.test.mjs`)
- [x] Implement route-scoped progress persistence for quiz `<details>` elements.
  (Implemented as `.vitepress/theme/quiz-progress.mjs`, not `.ts` — the theme
  entry imports plain ESM.)
- [x] Render a compact reviewed-question counter on quiz pages.
- [x] Reinitialize progress after VitePress route changes.
- [x] Verify GitBook Markdown remains unchanged. (Client-only theme code; no
  Markdown output changed.)

### Task 6: Verification

**Files:**
- Modify: `.github/workflows/deploy.yml`

- [x] Run all Node validation scripts. `npm run docs:validate` (test + local-link
  + image validators) passes.
- [x] Run `npm run docs:build` and record peak behavior. Sequential ko then en
  build (`NODE_OPTIONS=--max-old-space-size=8192`, matching CI), ~159s + ~143s,
  no OOM.
- [x] Inspect generated routes to confirm ko/en exist and cn/jp/es do not.
  `.vitepress/dist/{ko,en}` present; `ls .vitepress/dist | grep -E '^(cn|jp|es)$'`
  empty; merged `sitemap.xml` has zero `/cn/`, `/jp/`, `/es/` entries.
- [x] Confirm no unexpected tracked files changed. Verified via `git status`
  before/after build; commits split by task (build scope, diagrams, quiz nav,
  stale links, quiz progress) on `docs/vitepress-ko-en-publishing`.
