# SageMaker Qwen PII Guidebook and Archify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a polished five-part Korean/English SageMaker Qwen PII guidebook across AI/ML and Data, with two showcase Archify diagrams and factual validation results.

**Architecture:** Keep the existing experiment package and September 1 validation artifacts as the evidence layer. Add a cross-section guidebook whose Parts 1–3 and 5 live under AI/ML/SageMaker AI and whose Part 4 lives under Data/SageMaker Unified Studio; generate separate Korean and English Archify architecture/workflow specifications, interactive viewers, and static GitBook images.

**Tech Stack:** Markdown, JSON, Node.js content-contract tests, VitePress, GitBook, Archify 2.16, inline SVG/HTML, PNG visual-check captures.

**Spec:** `docs/superpowers/specs/2026-09-02-sagemaker-qwen-guidebook-design.md`

## Global Constraints

- Work only in `/home/atomoh/kubernetes-docs-sagemaker-qwen` on `feat/sagemaker-qwen-pii-finetuning`.
- Use September 2, 2026 for new guidebook “Last Updated” headers.
- Preserve the September 1, 2026 date on the original validation report.
- Author both `ko/` and `en/`; do not edit `cn/`, `jp/`, or `es/`.
- Keep exact product names, APIs, model IDs, commands, and repository paths in English.
- State that SageMaker and EKS GPU training were not executed.
- Do not publish fine-tuned F1, training duration, or GPU cost.
- Publish 2,200 records, 1,600/200/400 splits, 80/20 language ratio, 30 Python tests, Qwen model ID, MLflow App 3.10.1, and the three provisioning outcomes exactly as recorded.
- Recheck the current Unified Studio project state before writing Part 5 and before final handoff.
- Use the current SageMaker MLflow App APIs; do not recommend legacy Tracking Server creation.
- Use Archify `meta.quality_profile: "showcase"` and no animation.
- The target-architecture diagram must be labeled as target design, not execution evidence.
- The actual-validation workflow must terminate before GPU training.
- Korean Archify specs omit `meta.locale`; Korean pages disclose that fixed viewer controls use English.
- Add no account IDs, ARNs, access keys, project IDs, bucket names, presigned URLs, or model weights.

---

### Task 1: Add the bilingual guidebook content contract

**Files:**
- Create: `scripts/__tests__/sagemaker-qwen-guidebook.test.mjs`

**Interfaces:**
- Produces: a single Node contract used by all subsequent content and asset tasks.
- Consumes: guidebook Markdown, quizzes, navigation, Archify JSON/HTML/PNG, and the validation JSON.

- [ ] **Step 1: Write the failing guidebook contract**

```js
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const read = (relative) => readFileSync(path.join(root, relative), 'utf8')

const pagePaths = [
  'ai-ml/sagemaker-ai/README.md',
  'ai-ml/sagemaker-ai/01-platform-architecture.md',
  'ai-ml/sagemaker-ai/02-pii-data-tokenization.md',
  'ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md',
  'data-on-eks/sagemaker-unified-studio/README.md',
  'data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md',
  'ai-ml/sagemaker-ai/04-validation-results.md',
]

for (const locale of ['ko', 'en']) {
  test(`${locale}: five-part SageMaker Qwen guidebook is complete and truthful`, () => {
    const combined = pagePaths.map((page) => read(`${locale}/${page}`)).join('\n')
    assert.match(combined, /Qwen\/Qwen3-30B-A3B-Instruct-2507/)
    assert.match(combined, /TYPE<TAB>ORIGINAL/)
    assert.match(combined, /2,200/)
    assert.match(combined, /1,600.*200.*400/s)
    assert.match(combined, /80%.*20%/s)
    assert.match(combined, /3\.10\.1/)
    assert.match(combined, /(?:미실행|not executed)/i)
    assert.match(combined, /(?:membership|멤버십)/i)
    assert.doesNotMatch(combined, /fine-tuned micro-F1\s*[:=]\s*\d/i)
    assert.doesNotMatch(combined, /GPU cost\s*[:=]\s*\$?\d/i)
  })
}

test('Archify sources, viewers, and static images exist for both locales', () => {
  const bases = [
    'ko-ai-ml-sagemaker-ai-01-platform-architecture-0',
    'en-ai-ml-sagemaker-ai-01-platform-architecture-0',
    'ko-ai-ml-sagemaker-ai-04-validation-results-0',
    'en-ai-ml-sagemaker-ai-04-validation-results-0',
  ]
  for (const base of bases) {
    const type = base.includes('04-validation') ? 'workflow' : 'architecture'
    assert.ok(existsSync(path.join(root, `assets/diagrams/archify/${base}.${type}.json`)))
    assert.ok(existsSync(path.join(root, `public/archmaps/${base}.html`)))
    const locale = base.slice(0, 2)
    assert.ok(existsSync(path.join(root, `${locale}/.gitbook/assets/${base}.png`)))
  }
})
```

- [ ] **Step 2: Run the contract and verify RED**

Run:

```bash
node --test scripts/__tests__/sagemaker-qwen-guidebook.test.mjs
```

Expected: FAIL because guidebook pages and diagram assets do not exist.

- [ ] **Step 3: Preserve the RED evidence without committing a broken branch**

Record the failing output in the implementation ledger. Leave the contract
uncommitted until Task 8 makes it GREEN.

---

### Task 2: Create the bilingual Archify target-architecture diagram

**Files:**
- Create: `assets/diagrams/archify/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.architecture.json`
- Create: `assets/diagrams/archify/en-ai-ml-sagemaker-ai-01-platform-architecture-0.architecture.json`
- Create: `public/archmaps/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.html`
- Create: `public/archmaps/en-ai-ml-sagemaker-ai-01-platform-architecture-0.html`
- Create: `ko/.gitbook/assets/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.png`
- Create: `en/.gitbook/assets/en-ai-ml-sagemaker-ai-01-platform-architecture-0.png`

**Interfaces:**
- Produces: Part 1 static and interactive architecture assets.
- Consumes: experiment config, SageMaker launcher, EKS manifest, provisioning scripts, and result JSON.

- [ ] **Step 1: Read the required Archify architecture references**

Read:

```text
/home/atomoh/.agents/skills/archify/schemas/common.schema.json
/home/atomoh/.agents/skills/archify/schemas/architecture.schema.json
/home/atomoh/.agents/skills/archify/examples/brand-aware-delivery.architecture.json
```

- [ ] **Step 2: Write the Korean candidate first**

Create an architecture candidate with these stable IDs:

```json
{
  "schema_version": 1,
  "diagram_type": "architecture",
  "meta": {
    "title": "SageMaker Qwen PII 파인튜닝 목표 아키텍처",
    "quality_profile": "showcase",
    "animation": "none",
    "viewBox": [1320, 760]
  }
}
```

Use exactly these components:

| ID | Type | Label |
|---|---|---|
| `generator` | backend | 합성 PII 데이터 생성기 |
| `s3` | database | Amazon S3 |
| `unified` | cloud | SageMaker Unified Studio |
| `training` | cloud | SageMaker AI Training Job |
| `qwen` | backend | Qwen3-30B-A3B + QLoRA |
| `evaluation` | backend | 집계 평가 |
| `managedMlflow` | cloud | SageMaker MLflow App |
| `eksJob` | backend | EKS GPU Job |
| `eksMlflow` | backend | MLflow on EKS |
| `inventory` | security | Resource Inventory & Teardown |

Use one main horizontal path:

```text
generator -> s3 -> training -> qwen -> evaluation -> managedMlflow
```

Use side connections:

```text
unified -> s3              "project/catalog governance"
s3 -> eksJob               "same source + dataset"
eksJob -> eksMlflow        "aggregate metrics"
inventory -> training      "create/delete"
inventory -> managedMlflow "create/delete"
inventory -> eksJob        "ephemeral cluster"
```

Add one `ap-northeast-2` region boundary around AWS components and cards titled
`검증된 범위` and `목표 설계`. The target-design card states that SageMaker and
EKS GPU runs were not executed.

Add repository `sources` to `generator`, `training`, `eksJob`, and `inventory`.

- [ ] **Step 3: Run the Archify update checker once**

Run:

```bash
node /home/atomoh/.agents/skills/archify/scripts/check-update.mjs
```

Follow the skill notice/ack contract only if an update is reported.

- [ ] **Step 4: Validate and repair the Korean candidate**

Run after every edit:

```bash
node /home/atomoh/.agents/skills/archify/bin/archify.mjs validate \
  architecture \
  assets/diagrams/archify/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.architecture.json \
  --quality showcase \
  --repo-root /home/atomoh/kubernetes-docs-sagemaker-qwen \
  --json
```

Expected final receipt: 9/9 checks, 0 composition errors, 0 warnings.

- [ ] **Step 5: Author and validate the English candidate**

Use the same IDs, topology, component types, sources, and geometry. Translate
authored labels and cards; set `meta.locale: "en"`.

Run the matching validation command and require the same showcase receipt.

- [ ] **Step 6: Deliver both trusted HTML artifacts**

```bash
node /home/atomoh/.agents/skills/archify/bin/archify.mjs deliver \
  architecture \
  assets/diagrams/archify/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.architecture.json \
  public/archmaps/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.html \
  --quality showcase \
  --repo-root /home/atomoh/kubernetes-docs-sagemaker-qwen \
  --json

node /home/atomoh/.agents/skills/archify/bin/archify.mjs deliver \
  architecture \
  assets/diagrams/archify/en-ai-ml-sagemaker-ai-01-platform-architecture-0.architecture.json \
  public/archmaps/en-ai-ml-sagemaker-ai-01-platform-architecture-0.html \
  --quality showcase \
  --repo-root /home/atomoh/kubernetes-docs-sagemaker-qwen \
  --json
```

- [ ] **Step 7: Run visual checks and create static PNGs**

Run `visual-check --json` for each delivered HTML. Read the generated
`*.visual-check.json`, select the screenshot entry with width `1440`, height
`900`, and theme `light`, resolve its path relative to the HTML, and copy it to
the static PNG path listed in this task's Files block.

- [ ] **Step 8: Inspect both contact sheets**

Use `view_image` on the Korean and English visual-check contact-sheet
screenshots or their light/dark 1440×900 and 2048×1320 captures. Check node
fit, route crossings, labels, cards, and both themes. Allow at most two
candidate correction rounds; each correction requires revalidation,
redelivery, and a new visual check.

- [ ] **Step 9: Commit**

```bash
git add \
  assets/diagrams/archify/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.architecture.json \
  assets/diagrams/archify/en-ai-ml-sagemaker-ai-01-platform-architecture-0.architecture.json \
  public/archmaps/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.html \
  public/archmaps/en-ai-ml-sagemaker-ai-01-platform-architecture-0.html \
  ko/.gitbook/assets/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.png \
  en/.gitbook/assets/en-ai-ml-sagemaker-ai-01-platform-architecture-0.png
git commit -m "docs: add SageMaker Qwen target architecture"
```

---

### Task 3: Create the bilingual Archify actual-validation workflow

**Files:**
- Create: `assets/diagrams/archify/ko-ai-ml-sagemaker-ai-04-validation-results-0.workflow.json`
- Create: `assets/diagrams/archify/en-ai-ml-sagemaker-ai-04-validation-results-0.workflow.json`
- Create: `public/archmaps/ko-ai-ml-sagemaker-ai-04-validation-results-0.html`
- Create: `public/archmaps/en-ai-ml-sagemaker-ai-04-validation-results-0.html`
- Create: `ko/.gitbook/assets/ko-ai-ml-sagemaker-ai-04-validation-results-0.png`
- Create: `en/.gitbook/assets/en-ai-ml-sagemaker-ai-04-validation-results-0.png`

**Interfaces:**
- Produces: Part 5 static and interactive actual-result assets.
- Consumes: `provisioning-validation.json` and the September 1 report.

- [ ] **Step 1: Read workflow schema and example**

Read:

```text
/home/atomoh/.agents/skills/archify/schemas/common.schema.json
/home/atomoh/.agents/skills/archify/schemas/workflow.schema.json
/home/atomoh/.agents/skills/archify/examples/incident-response.workflow.json
```

- [ ] **Step 2: Write the Korean workflow candidate**

Use `schema_version: 2`, `diagram_type: "workflow"`,
`meta.quality_profile: "showcase"`, and `animation: "none"`.

Use this main rail:

```text
localValidated -> preflight -> attempt1 -> cleanup1 -> attempt2 ->
cleanup2 -> attempt3 -> partialCleanup -> blocked
```

Use exact semantic labels:

| ID | Label | Role |
|---|---|---|
| `localValidated` | 로컬 데이터·테스트 통과 | start |
| `preflight` | AWS preflight 통과 | process |
| `attempt1` | App 상태 계약 불일치 | failure |
| `cleanup1` | App·S3·IAM 회수 | process |
| `attempt2` | Project tag 정책 거부 | failure |
| `cleanup2` | App·S3·IAM 회수 | process |
| `attempt3` | Project membership 누락 | failure |
| `partialCleanup` | App·S3·IAM 회수 | process |
| `blocked` | Unified Studio 프로젝트 1개 ACTIVE | failure/terminal |
| `trainingNotRun` | GPU 학습 미실행 | terminal |

Connect `blocked -> trainingNotRun` with label `stop before spend`. Add cards for
`실제 관측` and `하지 않은 주장`; the latter says no F1, duration, or GPU cost.

- [ ] **Step 3: Validate, author English, and freeze both candidates**

Run after every Korean candidate edit:

```bash
node /home/atomoh/.agents/skills/archify/bin/archify.mjs validate \
  workflow \
  assets/diagrams/archify/ko-ai-ml-sagemaker-ai-04-validation-results-0.workflow.json \
  --quality showcase \
  --json
```

Run the same command for
`en-ai-ml-sagemaker-ai-04-validation-results-0.workflow.json`. The English
candidate uses the same IDs and topology with `meta.locale: "en"`.

- [ ] **Step 4: Deliver, visually check, and create static PNGs**

Use the same delivery, receipt-driven 1440×900 light screenshot copy, and
manual contact-sheet inspection procedure as Task 2.

- [ ] **Step 5: Commit**

```bash
git add \
  assets/diagrams/archify/ko-ai-ml-sagemaker-ai-04-validation-results-0.workflow.json \
  assets/diagrams/archify/en-ai-ml-sagemaker-ai-04-validation-results-0.workflow.json \
  public/archmaps/ko-ai-ml-sagemaker-ai-04-validation-results-0.html \
  public/archmaps/en-ai-ml-sagemaker-ai-04-validation-results-0.html \
  ko/.gitbook/assets/ko-ai-ml-sagemaker-ai-04-validation-results-0.png \
  en/.gitbook/assets/en-ai-ml-sagemaker-ai-04-validation-results-0.png
git commit -m "docs: add SageMaker validation workflow"
```

---

### Task 4: Write the landing page and Parts 1–2 in both locales

**Files:**
- Create: `ko/ai-ml/sagemaker-ai/README.md`
- Create: `en/ai-ml/sagemaker-ai/README.md`
- Create: `ko/ai-ml/sagemaker-ai/01-platform-architecture.md`
- Create: `en/ai-ml/sagemaker-ai/01-platform-architecture.md`
- Create: `ko/ai-ml/sagemaker-ai/02-pii-data-tokenization.md`
- Create: `en/ai-ml/sagemaker-ai/02-pii-data-tokenization.md`

**Interfaces:**
- Consumes: target architecture assets, config, dataset manifest, tokenization code.
- Produces: guidebook entry and foundational learning content.

- [ ] **Step 1: Write the bilingual landing pages**

Use `Last Updated: September 2, 2026` / `마지막 업데이트: 2026년 9월 2일`.
Include a five-part table with Part 4 linked across to
`../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md`.

Include status cards in prose:

```text
Validated locally: dataset, tokenizer, metrics, launch contracts
Observed in AWS: quotas, MLflow App, project creation failures
Not executed: SageMaker Training Job, EKS GPU Job
Blocked: one Unified Studio project cleanup
```

- [ ] **Step 2: Write Part 1**

Embed:

```markdown
![SageMaker AI 관리형 학습 경로와 동일 소스·데이터를 사용하는 EKS 대안 경로, Unified Studio 거버넌스, MLflow 추적, 자원 회수 계층을 함께 보여주는 목표 아키텍처.](../../.gitbook/assets/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.html)
```

Use the English equivalent in `en/`. Label the figure “Target design / 목표
설계.” Include responsibility and decision tables.

- [ ] **Step 3: Write Part 2**

Use exact counts and hashes from `dataset-manifest.json`. Explain the nine
entity types, the TSV contract, deterministic tokenization steps, and metric
definitions. Use only synthetic values from `review-sample.jsonl`.

- [ ] **Step 4: Run focused contract**

Run:

```bash
node --test scripts/__tests__/sagemaker-qwen-guidebook.test.mjs
```

Expected: still FAIL only for remaining pages, quizzes, navigation, and second
diagram; landing and Parts 1–2 assertions pass.

- [ ] **Step 5: Commit**

```bash
git add ko/ai-ml/sagemaker-ai en/ai-ml/sagemaker-ai
git commit -m "docs: add SageMaker guidebook foundations"
```

---

### Task 5: Write Part 3 — SageMaker AI and MLflow execution

**Files:**
- Create: `ko/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md`
- Create: `en/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md`

**Interfaces:**
- Consumes: preflight, provisioning, launcher, teardown, EKS manifests.
- Produces: executable managed/self-managed comparison without claiming execution.

- [ ] **Step 1: Write the managed execution walkthrough**

Cover, in order:

1. read-only preflight;
2. source bundle;
3. dataset upload;
4. MLflow App creation;
5. Training Job request;
6. smoke/full gate;
7. aggregate result export;
8. teardown and verification.

Every command block is sourced from committed scripts. Add a callout:
“The commands are runnable implementation, but the recorded September 1
validation stopped before Training Job submission.”

- [ ] **Step 2: Add the EKS comparison**

Explain the ephemeral EKS 1.36 cluster, g6e.4xlarge, NVIDIA plugin 0.20.0,
ClusterIP MLflow, presigned dataset URLs, `backoffLimit: 0`,
`activeDeadlineSeconds: 10800`, in-Pod export, and trap deletion.

- [ ] **Step 3: Add error and stop conditions**

Include the observed App status enum, tag policy, membership, throttling, and
cleanup findings. Do not expose resource IDs.

- [ ] **Step 4: Commit**

```bash
git add ko/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md \
  en/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md
git commit -m "docs: add SageMaker MLflow execution guide"
```

---

### Task 6: Write Part 4 — Unified Studio governance

**Files:**
- Create: `ko/data-on-eks/sagemaker-unified-studio/README.md`
- Create: `en/data-on-eks/sagemaker-unified-studio/README.md`
- Create: `ko/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md`
- Create: `en/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md`
- Modify: `ko/data-on-eks/README.md`
- Modify: `en/data-on-eks/README.md`

**Interfaces:**
- Consumes: current AWS project status and provisioning failure evidence.
- Produces: standalone Data topic and guidebook Part 4.

- [ ] **Step 1: Recheck current external state**

Run a read-only AWS query on September 2, 2026:

```bash
aws datazone list-projects \
  --region ap-northeast-2 \
  --domain-identifier dzd-d1k7g3a43jm57c
```

Record only the count and status in prose; never commit domain/project IDs.

- [ ] **Step 2: Write the Unified Studio landing page**

Explain why a managed data/AI workspace appears in Data on EKS and how it
complements Kafka, Spark, Airflow, and Flink.

- [ ] **Step 3: Write Part 4**

Explain domains, project profiles, projects, catalog assets, memberships, the
All capabilities profile, custom-tag policy, IAM versus DataZone authorization,
owner assignment, and deletion.

End with links to Part 3 and Part 5.

- [ ] **Step 4: Update Data overview**

Add a `Governed data and AI workspace` row to the category table and add
Unified Studio to “Currently Covered” and “Next Steps.”

- [ ] **Step 5: Commit**

```bash
git add ko/data-on-eks en/data-on-eks
git commit -m "docs: add SageMaker Unified Studio governance guide"
```

---

### Task 7: Write Part 5 — factual validation results

**Files:**
- Create: `ko/ai-ml/sagemaker-ai/04-validation-results.md`
- Create: `en/ai-ml/sagemaker-ai/04-validation-results.md`

**Interfaces:**
- Consumes: validation JSON/report, current project-state recheck, workflow assets.
- Produces: final guidebook chapter with no fabricated metrics.

- [ ] **Step 1: Write the bilingual factual result table**

Use:

```text
2,200 records
1,600 / 200 / 400
80% / 20%
30 Python tests
MLflow App 3.10.1
SageMaker training executed: false
EKS training executed: false
```

- [ ] **Step 2: Embed the actual-validation workflow**

Use the static PNG + interactive link pattern for each locale. Introduce it as
an actual execution trace, not the target architecture.

- [ ] **Step 3: Explain attempts and cleanup**

Document all three attempts, fixes, and current remaining-project state. Add a
“What is not measured” table for F1, duration, GPU memory, and cost.

- [ ] **Step 4: Add rerun gate**

Require:

1. no `qwen-pii-*` project remains;
2. preflight passes;
3. owner membership is assigned at create time;
4. smoke run completes;
5. raw PII logging scan passes;
6. only then run the full job.

- [ ] **Step 5: Commit**

```bash
git add ko/ai-ml/sagemaker-ai/04-validation-results.md \
  en/ai-ml/sagemaker-ai/04-validation-results.md
git commit -m "docs: publish SageMaker Qwen validation results"
```

---

### Task 8: Add quizzes, navigation, and cross-links

**Files:**
- Create the ten quiz files from the spec.
- Modify: `ko/SUMMARY.md`
- Modify: `en/SUMMARY.md`
- Modify: `ko/README.md`
- Modify: `en/README.md`
- Modify: `ko/ai-ml/mlflow/README.md`
- Modify: `en/ai-ml/mlflow/README.md`
- Modify: `ko/ai-ml/05-model-training.md`
- Modify: `en/ai-ml/05-model-training.md`
- Modify selected ko/en Kubeflow comparison text.

**Interfaces:**
- Produces: discoverable five-part learning path and matching assessments.

- [ ] **Step 1: Add five questions per part and locale**

Follow repository quiz markup. Include questions on status truth, TSV
extraction, MLflow App, DataZone membership, and cleanup stop conditions.

- [ ] **Step 2: Update navigation**

Add SageMaker AI after MLflow in AI/ML and Unified Studio after the Data
overview/anatomy entries. Add quiz links to root README files.

- [ ] **Step 3: Add cross-links**

Link model training and MLflow to Parts 1–3, and existing Kubeflow managed
alternative text to the new SageMaker landing page.

- [ ] **Step 4: Run the focused contract**

```bash
node --test scripts/__tests__/sagemaker-qwen-guidebook.test.mjs
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ko en scripts/__tests__/sagemaker-qwen-guidebook.test.mjs
git commit -m "docs: integrate SageMaker Qwen guidebook navigation"
```

---

### Task 9: Run final Archify and documentation verification

**Files:**
- Verify all guidebook, quiz, diagram, result, spec, and plan files.

- [ ] **Step 1: Verify Archify receipts**

For each of four JSON/HTML pairs, rerun `validate --quality showcase --json`
and `archify check <html>`. Confirm 9/9 checks, 0 errors, and 0 warnings.

- [ ] **Step 2: Verify visual evidence**

Run `visual-check --json` for all four HTML artifacts and inspect the newest
contact sheets with `view_image`. Report `visual_review: passed` only after
inspection.

- [ ] **Step 3: Run content and experiment tests**

```bash
node --test scripts/__tests__/sagemaker-qwen-guidebook.test.mjs
npm run docs:test
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  /tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests -q
```

- [ ] **Step 4: Validate links and images**

```bash
node scripts/validate-local-links.mjs
node scripts/validate-image-assets.mjs
```

If the local-link validator reports only the known baseline cluster
architecture asset paths, verify this branch adds zero new failures and record
the baseline paths.

- [ ] **Step 5: Build both locales**

```bash
VITEPRESS_BUILD_LOCALE=ko NODE_OPTIONS=--max-old-space-size=8192 \
  node node_modules/vitepress/bin/vitepress.js build . \
  --outDir /tmp/vitepress-sagemaker-guidebook-ko
VITEPRESS_BUILD_LOCALE=en NODE_OPTIONS=--max-old-space-size=8192 \
  node node_modules/vitepress/bin/vitepress.js build . \
  --outDir /tmp/vitepress-sagemaker-guidebook-en
```

- [ ] **Step 6: Run final security and diff checks**

```bash
git diff --check origin/main...HEAD
rg -n -P 'AKIA[0-9A-Z]{16}|arn:aws:|(?<![0-9])[0-9]{12}(?![0-9])|X-Amz-Signature|dzd-[a-z0-9]+' \
  ko/ai-ml/sagemaker-ai en/ai-ml/sagemaker-ai \
  ko/data-on-eks/sagemaker-unified-studio \
  en/data-on-eks/sagemaker-unified-studio \
  assets/diagrams/archify
git status --short
```

Expected: no sensitive identifiers and a clean worktree.

- [ ] **Step 7: Commit verification corrections if required**

Use explicit approved paths; do not use `git add -A`.
