# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Korean-language Kubernetes and Amazon EKS training content repository. It is a documentation-only project (no application code) hosted on GitBook. All content is written in Markdown.

**GitBook URL**: https://atomoh.gitbook.io/kubernetes-docs/

## Build Commands

### Presentations (Marp)

```bash
# Build Istio presentation slides (requires marp-cli)
cd slide && bash build-presentation.sh

# Install marp-cli if needed
npm install -g @marp-team/marp-cli
```

There are no test, lint, or CI/CD pipelines for this project.

## Repository Structure

- `SUMMARY.md` — GitBook table of contents (must be updated when adding/removing/renaming pages)
- `README.md` — Project introduction and learning guide
- `basics/` — Linux, containers, Kubernetes introduction (3 docs)
- `core/` — Kubernetes core concepts: architecture, pods, services, storage, security, scheduling, etc. (11 docs)
- `eks/` — Amazon EKS: cluster creation, networking, storage, security, monitoring, cost optimization, upgrades, troubleshooting (multi-part docs)
- `cilium/` — Cilium CNI deep dive: eBPF, networking, IPAM, security, L2-L7 (10 docs)
- `advanced/` — Kyverno, Custom Scheduler, AI/ML workloads, vLLM deployment
- `tools/` — ArgoCD, Istio (extensive sub-hierarchy), ACK, Cilium, KEDA, Karpenter, monitoring stack, logging stack, VPC Lattice
- `tools/istio/` — Deep Istio documentation with subdirectories: `traffic-management/`, `security/`, `observability/`, `resilience/`, `advanced/`, `comparison/`, `troubleshooting/`
- `quizzes/` — Quiz files mirroring the same structure as content directories (`quizzes/basics/`, `quizzes/core/`, `quizzes/eks/`, etc.)
- `assets/` — Images and diagrams (SVG, PNG, drawio)
- `slide/` — Marp presentation sources and build script

## Content Conventions

### Document Header Format

Each document starts with a title, version/compatibility info block, and last-update date:

```markdown
# Document Title

> **지원 버전**: ...
> **마지막 업데이트**: 2025년 X월 X일
```

### Quiz Format

Quizzes use HTML `<details><summary>` tags for collapsible answers:

```markdown
1. Question text
   - A) Option A
   - B) Option B
<details>
<summary>정답 보기</summary>

**정답: B) Option B**

**설명:**
Explanation text here.

</details>
```

### Naming Conventions

- Content files: `NN-topic-name.md` (e.g., `01-linux-basics.md`)
- Multi-part topics: `NN-topic-name-partN.md` (e.g., `02-eks-cluster-creation-part1.md`)
- Quiz files: mirror content path under `quizzes/` with `-quiz` suffix (e.g., `quizzes/basics/01-linux-basics-quiz.md`)

## Key Relationships

- **Every content file should have a corresponding quiz** in the `quizzes/` directory
- **SUMMARY.md must stay in sync** with actual files — GitBook uses it to generate navigation
- **README.md table of contents** should also be updated when adding new content sections
