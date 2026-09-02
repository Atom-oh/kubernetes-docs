# Cloud Guidebook v2 — Taxonomy Reorg, llms.txt, Measured Benchmarks

## Goal

Turn the repo from a Kubernetes/EKS-centric doc tree into a comprehensive
cloud guidebook whose navigation tells one story — Linux → Container →
Kubernetes → EKS → Networking → Service Mesh → Storage → Database → Data
Pipeline → AI/ML → Security → GitOps → Platform → Observability → Operations —
while (a) keeping every existing URL stable, (b) making the book consumable by
LLMs via the llms.txt convention, and (c) adding measured-on-real-AWS
benchmark content in the two domains that have none today (storage,
database). Istio mTLS latency is already measured and published in
`service-mesh/istio/comparison/03-sidecar-vs-ambient.md`; this cycle fixes the
one place that still shows illustrative numbers instead.

## Non-goals

- No file moves or renames of existing content (SEO/URL stability).
- No cn/jp/es edits (machine-translated mirrors; backfill picks new sections up).
- No changes to slide/, news automation behavior, or GitBook hosting.

## Design

### 1. Taxonomy reorg (ko/en SUMMARY.md + README.md)

Nav-level only. New `##` group order and renames:

1. 소개 / Introduction — adds new `roadmap.md` (guidebook map + 3 learning
   paths) and `llm-guide.md` (how to use llms.txt endpoints with AI tools)
2. 소식 / News
3. Linux & Container — basics/01,02,03,05 (renamed from "Basic")
4. Kubernetes 핵심 개념 / Kubernetes Core Concepts — core/* plus Scheduling
   and Autoscaling folded in as nested parent items (their `##` groups go away)
5. Amazon EKS — unchanged (eks, hybrid nodes, auto mode)
6. Networking — basics/06 network-fundamentals parts move into this group as
   the leading item, then existing networking/* (renamed from "Network
   Operations")
7. Service Mesh — unchanged
8. Storage — NEW: storage/README.md (domain map linking core/04-storage and
   eks/04-eks-storage) + storage/01-ebs-gp2-gp3-benchmark.md (fio, measured)
9. Database — NEW: database/README.md (databases-on-Kubernetes overview:
   StatefulSet vs operator landscape) + database/01-clickhouse-on-eks.md
   (deploy + measured benchmark)
10. Data Pipeline — data-on-eks/* (group renamed from "Data on EKS")
11. AI/ML — unchanged
12. Security & Policy, GitOps, Platform Engineering, Container Registry,
    Observability, Operations Guide — unchanged content, ordered as listed
13. Lab Guides, Quiz 모음 — quiz group gains Storage/Database subsections

`.vitepress/summary.ts` already parses this format (including non-link parent
items); no code change needed for nav.

### 2. llms.txt (the "llmwiki")

- `scripts/generate-llms-txt.mjs`: parses `<locale>/SUMMARY.md`, emits into
  `public/`:
  - `llms.txt` — llms.txt-spec index: site title, one-paragraph summary,
    per-section link lists to the published clean URLs, one `## Docs` block
    per locale (ko first — primary audience).
  - `llms-full-ko.txt`, `llms-full-en.txt` — full concatenated markdown of
    every content page in SUMMARY order, with source URL headers per page.
- Wired into `npm run docs:build` (before the VitePress locale builds) so the
  files ship with every deploy; also runnable standalone.
- Excludes quizzes from llms-full (answer keys pollute LLM context) but lists
  them in llms.txt.
- `roadmap.md`/`llm-guide.md` document the endpoints for readers.

### 3. Measured benchmarks (fsi-demo-cluster, ap-northeast-2)

Both run in dedicated namespaces (`bench-storage`, `bench-database`) on the
m8g.xlarge Graviton nodes, and are deleted (namespace + PVC, Delete reclaim)
after results are captured. Manifests + exact commands are reproduced in the
docs so readers can re-run them.

- **Storage**: fio 3.x, alpine-based pod, one 100Gi gp2 PVC vs one 100Gi gp3
  PVC (defaults: gp2 = 300 IOPS for 100Gi, gp3 = 3000 IOPS / 125 MiB/s
  baseline), same node. Jobs: 4k randread, 4k randwrite, 1M seqread, 1M
  seqwrite, each with IOPS/bandwidth/latency (avg, p99). Story: "same 100GiB,
  ~10x IOPS gap and what it costs".
- **Database**: single-node ClickHouse (official multi-arch image) with 100Gi
  gp3 PVC, 12Gi memory limit. Synthetic Kubernetes-pod-log table (~100M
  rows via INSERT…SELECT FROM generateRandom): measure ingest rows/s,
  on-disk compression ratio, and latency (cold/warm) for 5 log-analytics
  query shapes (point lookup by trace id, time-range filter, top-K group by,
  needle-in-haystack LIKE, full-scan aggregate). Ties into
  observability/logging/04-clickhouse.md (cross-linked).

### 4. Corrections and sync plumbing

- `service-mesh/istio/security/01-mtls.md` (ko/en): replace the illustrative
  "+20% latency" table with the measured EKS numbers, cross-linking
  comparison/03-sidecar-vs-ambient.md.
- `.github/workflows/translate-backfill.yml`: add `storage`, `database` to the
  section dropdown.
- `.github/news-topic-map.yml`: add storage/database topic entries.

### 5. Visualization

- archify diagrams (interactive HTML in public/archmaps + PNG in
  `<locale>/.gitbook/assets`, embedded with the existing PNG + "interactive
  diagram" link pair that VitePress swaps for an iframe):
  - guidebook roadmap map (roadmap.md)
  - EBS data path: pod → kubelet/CSI → EBS gp2/gp3 (storage benchmark doc)
  - ClickHouse ingest/query flow (database benchmark doc)
- Benchmark results additionally rendered as markdown tables (GitBook-safe).

## Error handling / risks

- Benchmarks run on a shared demo cluster: pin pods to the same node type,
  record instance type and limits in the doc, present numbers as "measured on
  this configuration", not absolutes.
- If a benchmark cannot complete (scheduling pressure, quota), the affected
  doc section ships with the harness + manifests and no fabricated numbers —
  measured data only.
- Build memory: validate with NODE_OPTIONS=--max-old-space-size=8192.

## Testing

- `npm run docs:validate` (link + asset validation + script tests; add a test
  for generate-llms-txt.mjs).
- Full local VitePress build of ko+en.
- content-review-agent quality gate ≥ 85 on new/changed pages before PR.
