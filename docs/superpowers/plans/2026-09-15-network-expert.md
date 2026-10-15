# Expert Networking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish a Korean/English expert networking path that joins authoritative curricula to practical evidence and recovery exercises.

**Architecture:** Six expert workbooks plus a course index and six quizzes per language extend the existing beginner and specialist guides. Separate lab environments have explicit readiness contracts.

**Tech Stack:** Markdown, GitBook/VitePress, existing Node validation, Python static/sample checks and browser QA.

**Spec:** `docs/superpowers/specs/2026-09-15-network-expert-design.md`

## Global Constraints

- Documentation-only repository changes; no authoring-agent network/cloud configuration, paid enrollment or infrastructure creation.
- Core host examples use disposable Ubuntu Server 24.04 LTS or Rocky Linux 9 VMs. Netlab/provider prerequisites are separately established and version-recorded.
- Every active exercise has scoped ownership, environment/tool prerequisites, expected and negative observations, bounded execution and restoration.
- Public primary sources ground the content; do not copy course solutions or promise unavailable public access.
- Korean/English parity and at least eight explained quiz questions per chapter are required; do not edit machine-translated mirrors.
- No new repository test code is needed. Use existing validation plus task-local static/sample/browser checks.
- Current-HEAD full content review coverage, no unresolved Critical/Major findings, content quality at least 85/100, required CI and exact HEAD/base checks precede merge/deployment.

## Task 1: Protocol and Linux workbooks

**Files:** Create paired `networking/expert/01-protocol-projects.md`, `04-linux-performance.md` and their four quiz files.

**Interfaces:** Consumes beginner readiness and existing protocol/kernel/diagnostics guides. Produces protocol and host evidence for the final capstone.

- [ ] Map primary course material to concrete reading and original project deliverables.
- [ ] Write bounded observation/measurement workbooks with prerequisites, failure cases and recovery.
- [ ] Add aligned quizzes and self-check source accuracy, commands and links.

## Task 2: Routing and fabric workbooks

**Files:** Create paired `02-routing-policy-convergence.md`, `03-datacenter-evpn.md` and their four quiz files.

**Interfaces:** Uses separately prepared, owned local routing/fabric labs; produces policy, convergence and isolation evidence for the capstone.

- [ ] Verify upstream BGP Labs/netlab/provider setup and use a declared compatible lab path.
- [ ] Explain control/data-plane reasoning and concrete positive/negative experiments.
- [ ] Specify rollback and measurement limits, add quizzes, and self-check both languages.

## Task 3: Cloud, automation and course integration

**Files:** Create paired expert README, `05-cloud-cni-design.md`, `06-automation-capstone.md` and four quizzes. Modify both locale README/SUMMARY files, networking README, beginner README and beginner capstone.

**Interfaces:** Consumes the evidence contracts from tasks 1–2, existing cloud/CNI guides and official AWS/Cisco study domains.

- [ ] Write course progression, prerequisite gates and track/resource mapping.
- [ ] Add scoped cloud inventory/design exercises and a normalized evidence/automation capstone.
- [ ] Register all lessons/quizzes and link entry/continuation points without renaming routes.
- [ ] Run `npm run docs:validate` and the existing Python network-example suite.

## Task 4: Review and publication

**Evidence:** Task-owned files outside committed source; PR records carry final review and validation results.

- [ ] Complete independent changed-file reviews, fix material findings and re-review the current HEAD.
- [ ] Check snippet syntax, example data contracts, quiz/command parity and link targets.
- [ ] Build both locales and inspect built desktop/mobile navigation, anchors and answer disclosures.
- [ ] Push a PR, report an attributed current-HEAD AI review, require all CI/protection conditions and merge.
- [ ] Confirm Pages deployment, live new pages, and a clean synchronized main checkout.
