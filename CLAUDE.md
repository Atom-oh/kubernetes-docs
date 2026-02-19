# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bilingual (Korean + English) Kubernetes and Amazon EKS training content hosted on GitBook. Documentation-only project — no application code, no test/lint/CI pipelines. All content is Markdown.

**GitBook URL**: https://atomoh.gitbook.io/kubernetes-docs/

## Build Commands

```bash
# Build Istio presentation slides (requires marp-cli: npm install -g @marp-team/marp-cli)
cd slide && bash build-presentation.sh
```

## Repository Structure

```
kubernetes-docs/
├── README.md              # Language selector (root)
├── CLAUDE.md
├── assets/                # Shared images/diagrams (SVG, PNG, drawio)
├── slide/                 # Marp presentation sources and build script
├── ko/                    # Korean content
│   ├── README.md          # Korean table of contents
│   ├── SUMMARY.md         # GitBook navigation (Korean)
│   ├── basics/            # Linux, containers, K8s intro (4 docs)
│   ├── core/              # K8s core concepts (11 docs)
│   ├── eks/               # Amazon EKS topics (multi-part, 22 docs)
│   ├── cilium/            # Cilium CNI deep dive (10 docs)
│   ├── ai-ml/             # AI/ML Workloads, vLLM, Agentic AI (3 docs)
│   ├── networking/        # Cilium tool, VPC Lattice (2 docs)
│   ├── service-mesh/      # Istio overview + istio/ subtree (49+ docs)
│   ├── security/          # Kyverno, Auth/AuthZ (2 docs)
│   ├── gitops/            # ArgoCD (1 doc)
│   ├── autoscaling/       # KEDA, Karpenter (2 docs)
│   ├── observability/     # Monitoring Stack, Logging Stack (2 docs)
│   ├── scheduling/        # Custom Scheduler parts 1-3 (3 docs)
│   ├── package-management/ # Helm, KRO (2 docs)
│   ├── platform/          # ACK, K8s Extensions (2 docs)
│   ├── quizzes/           # Mirrors content structure with -quiz suffix
│   └── labs/              # Hands-on lab guides with step-by-step exercises (basics, core, eks)
└── en/                    # English content (same structure as ko/)
    ├── README.md
    ├── SUMMARY.md
    └── ...
```

`assets/` is shared at root level. From `ko/` or `en/` files, asset references use `../../assets/` (or `../../../assets/` for deeper nesting like `service-mesh/istio/`).

## Adding or Renaming Content — Files to Keep in Sync

When adding, removing, or renaming any content page, update **all of these in both languages**:

1. **`ko/SUMMARY.md`** and **`en/SUMMARY.md`** — GitBook navigation
2. **`ko/README.md`** and **`en/README.md`** — Table of contents with learning/quiz link pairs
3. **`ko/quizzes/`** and **`en/quizzes/`** — Every content file should have a corresponding quiz

## Content Conventions

### Document Header Format

Korean:
```markdown
# Document Title
> **지원 버전**: ...
> **마지막 업데이트**: 2025년 X월 X일
```

English:
```markdown
# Document Title
> **Supported Versions**: ...
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
- **Exception — Istio quizzes** use topic-based names without numbers: `quizzes/service-mesh/istio/traffic-management.md`, `security.md`, etc.

## Known Gaps

None - all content files have corresponding quizzes.
