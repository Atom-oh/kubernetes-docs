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

- [ ] Write a scope check that loads the built output or source configuration
  and fails when `cn`, `jp`, or `es` are active VitePress locales.
- [ ] Add a VitePress-only root landing page for Korean and English.
- [ ] Exclude translated mirror directories and remove their locale rewrites.
- [ ] Run `node scripts/check-vitepress-scope.mjs`; expect exit code 0.

### Task 2: Enforce local-link correctness

**Files:**
- Create: `scripts/validate-local-links.mjs`
- Modify: `.vitepress/config.ts`
- Modify: `ko/service-mesh/02-istio.md`
- Modify: `en/service-mesh/02-istio.md`
- Modify: `en/eks/12-kubernetes-version-roadmap.md`

- [ ] Write the validator and confirm it reports the known stale Istio links.
- [ ] Replace stale link targets with files that exist in the current tree.
- [ ] Disable `ignoreDeadLinks`.
- [ ] Run the validator for `ko` and `en`; expect no missing local targets.

### Task 3: Repair diagram assets

**Files:**
- Create: `assets/diagrams/rendered/observability-overview.svg`
- Create: `assets/diagrams/rendered/msa-service-map.svg`
- Create: `assets/diagrams/rendered/aiops-architecture.svg`
- Create: `scripts/validate-image-assets.mjs`
- Modify: observability lab Markdown files in all languages
- Delete: unused 1x1 PNG files under `assets/generated-diagrams/`

- [ ] Write an image validator that rejects referenced PNG files with dimensions
  below 16x16.
- [ ] Confirm the validator fails on the existing observability placeholders.
- [ ] Add readable shared SVG replacements and update Markdown references.
- [ ] Delete unused generated 1x1 PNG exports while retaining Draw.io sources.
- [ ] Run the validator; expect exit code 0.

### Task 4: Remove fake quiz landing pages

**Files:**
- Modify: `ko/SUMMARY.md`
- Modify: `en/SUMMARY.md`
- Modify: `scripts/sync-nav.py`
- Delete: `ko/quiz/**/README.md`
- Delete: `en/quiz/**/README.md`
- Delete: `en/quiz/service-mesh/istio/comparison.md`

- [ ] Convert linked quiz category placeholders into label-only bullets.
- [ ] Update the navigation synchronization comment and behavior to preserve raw
  group labels without expecting a destination file.
- [ ] Remove placeholder and orphan files.
- [ ] Generate both sidebars and verify quiz children remain correctly nested.

### Task 5: Add client-only quiz review progress

**Files:**
- Create: `.vitepress/theme/quiz-progress.ts`
- Modify: `.vitepress/theme/index.ts`
- Modify: `.vitepress/theme/custom.css`

- [ ] Add DOM-level tests using deterministic HTML fixtures and Node assertions.
- [ ] Implement route-scoped progress persistence for quiz `<details>` elements.
- [ ] Render a compact reviewed-question counter on quiz pages.
- [ ] Reinitialize progress after VitePress route changes.
- [ ] Verify GitBook Markdown remains unchanged.

### Task 6: Verification

**Files:**
- Modify: `.github/workflows/deploy.yml`

- [ ] Run all Node validation scripts.
- [ ] Run `npm run docs:build` and record peak behavior.
- [ ] Inspect generated routes to confirm ko/en exist and cn/jp/es do not.
- [ ] Confirm no unexpected tracked files changed.
