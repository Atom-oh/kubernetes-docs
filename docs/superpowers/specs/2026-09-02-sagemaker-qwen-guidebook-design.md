# SageMaker Qwen PII Guidebook and Archify Design

## Goal

Turn the September 1, 2026 SageMaker Qwen PII validation work into a polished
Korean and English guidebook that:

- adds Amazon SageMaker AI as a first-class AI/ML topic;
- adds Amazon SageMaker Unified Studio as a first-class Data topic;
- explains the reusable Qwen PII extraction and deterministic tokenization
  design;
- distinguishes target architecture, locally validated code, AWS provisioning
  evidence, unexecuted GPU training, and the remaining cleanup action;
- embeds polished Archify diagrams with static GitBook images and interactive
  VitePress viewers.

The guidebook is educational content, not a claim that fine-tuning completed.

## Source of Truth

Use the following repository evidence:

- `examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml`
- `examples/ai-ml/qwen-pii-finetuning/data/dataset-manifest.json`
- `examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py`
- `examples/ai-ml/qwen-pii-finetuning/src/metrics.py`
- `examples/ai-ml/qwen-pii-finetuning/src/train.py`
- `examples/ai-ml/qwen-pii-finetuning/launch/sagemaker_train.py`
- `examples/ai-ml/qwen-pii-finetuning/launch/aws/`
- `examples/ai-ml/qwen-pii-finetuning/launch/eks/`
- `examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json`
- `docs/superpowers/reports/2026-09-01-sagemaker-qwen-pii-validation.md`

Do not infer measured values that are absent from these files.

## Truth and Status Policy

Every operational statement belongs to one of these statuses:

| Status | Meaning | Allowed wording |
|---|---|---|
| **Validated locally** | Covered by committed tests or deterministic generation | “검증됨 / Validated” |
| **Validated in AWS** | Observed through actual AWS API calls | “AWS에서 확인 / Observed in AWS” |
| **Target design** | Implemented or documented but not executed as a GPU run | “목표 설계 / Target design” |
| **Not executed** | SageMaker Training Job or EKS GPU Job never started | “미실행 / Not executed” |
| **Blocked** | External authorization or cleanup action is still required | “차단됨 / Blocked” |

The guidebook must state:

- 2,200 synthetic records were generated;
- train/validation/test counts are 1,600/200/400;
- Korean/English ratio is 80/20;
- 30 Python tests passed in the recorded validation snapshot;
- SageMaker MLflow App version 3.10.1 was observed;
- no SageMaker Training Job or EKS GPU cluster was started;
- no fine-tuned F1, training duration, or GPU cost was measured;
- the September 1 snapshot recorded one remaining Unified Studio project;
- the September 2 recheck found that project still `ACTIVE` and found no
  remaining `qwen-pii-*` MLflow App;
- the cleanup state must be checked once more immediately before final handoff.

Never turn an expected metric, target, or configuration value into a measured
result.

## Guidebook Structure

The five-part reading path crosses the AI/ML and Data sections.

### Landing page

Create:

- `ko/ai-ml/sagemaker-ai/README.md`
- `en/ai-ml/sagemaker-ai/README.md`

The landing page provides:

- audience and prerequisites;
- a five-part reading map;
- a status summary;
- decision guidance: SageMaker AI versus EKS;
- direct links to the runnable example and factual validation report;
- a warning that Part 4 lives in the Data section because Unified Studio is
  the governed workspace rather than the training runtime.

### Part 1: Platform architecture

Create:

- `ko/ai-ml/sagemaker-ai/01-platform-architecture.md`
- `en/ai-ml/sagemaker-ai/01-platform-architecture.md`

Cover:

- SageMaker AI Training Jobs;
- SageMaker MLflow App;
- S3 dataset, source, artifacts, and output prefixes;
- the optional EKS execution path with in-cluster MLflow;
- Unified Studio project/catalog governance;
- responsibility comparison between managed and Kubernetes-operated paths;
- one Archify target-architecture diagram;
- explicit “target design, not fully executed” labeling.

### Part 2: Synthetic PII and deterministic tokenization

Create:

- `ko/ai-ml/sagemaker-ai/02-pii-data-tokenization.md`
- `en/ai-ml/sagemaker-ai/02-pii-data-tokenization.md`

Cover:

- why only synthetic PII is used;
- exact split counts and language ratio;
- entity types;
- `TYPE<TAB>ORIGINAL` output contract;
- why Qwen extracts entities rather than rewriting masked text;
- NFC normalization, source-order numbering, original-before-variant matching,
  one-pass replacement, digit boundaries, and reassembly;
- dataset hashes and reproducibility;
- representative safe examples derived from `review-sample.jsonl`;
- how leakage, over-redaction, hallucination, parse success, determinism, and
  round-trip metrics would be calculated.

### Part 3: SageMaker AI and managed MLflow execution

Create:

- `ko/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md`
- `en/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md`

Cover:

- preflight and quotas;
- source bundle and dataset upload;
- scoped IAM roles and S3;
- current MLflow App APIs rather than legacy Tracking Server APIs;
- Training Job request shape;
- smoke-before-full strategy;
- runtime limits, adaptive retries, and aggregate-only MLflow logging;
- teardown inventory;
- the equivalent EKS Job path and what the team operates itself;
- commands as runnable examples, clearly labeled as unexecuted in this
  validation snapshot.

### Part 4: Unified Studio governance

Create:

- `ko/data-on-eks/sagemaker-unified-studio/README.md`
- `en/data-on-eks/sagemaker-unified-studio/README.md`
- `ko/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md`
- `en/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md`

This page is Part 4 of the guidebook and a standalone Data topic.

Cover:

- V2 domains, project profiles, projects, catalog assets, and memberships;
- why the **All capabilities** profile was selected;
- how dataset and ML artifacts fit a governed project;
- the actual custom-tag rejection;
- the actual project-membership authorization failure;
- IAM authorization versus DataZone internal project authorization;
- owner membership at project creation;
- cleanup rules and the remaining owner action;
- managed workspace versus “Data on EKS” operational boundaries.

### Part 5: Validation results and lessons

Create:

- `ko/ai-ml/sagemaker-ai/04-validation-results.md`
- `en/ai-ml/sagemaker-ai/04-validation-results.md`

Cover:

- the factual result summary;
- the three provisioning attempts;
- what succeeded, what failed, and what was fixed;
- resource cleanup state;
- the absence of training metrics;
- the decision to stop before GPU spend;
- one Archify actual-validation workflow;
- a rerun checklist gated on Unified Studio project cleanup;
- links back to Parts 1–4.

## Quiz Structure

Create one quiz per part in both locales:

- `ko/quizzes/ai-ml/sagemaker-ai/01-platform-architecture-quiz.md`
- `ko/quizzes/ai-ml/sagemaker-ai/02-pii-data-tokenization-quiz.md`
- `ko/quizzes/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution-quiz.md`
- `ko/quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md`
- `ko/quizzes/ai-ml/sagemaker-ai/04-validation-results-quiz.md`
- matching English files.

Each quiz has five questions. Questions must test:

- target design versus measured result;
- MLflow App versus legacy Tracking Server;
- extraction versus direct redaction;
- IAM versus DataZone membership;
- cleanup and stop conditions.

## Archify Deliverables

Create four source specifications:

- `assets/diagrams/archify/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.architecture.json`
- `assets/diagrams/archify/en-ai-ml-sagemaker-ai-01-platform-architecture-0.architecture.json`
- `assets/diagrams/archify/ko-ai-ml-sagemaker-ai-04-validation-results-0.workflow.json`
- `assets/diagrams/archify/en-ai-ml-sagemaker-ai-04-validation-results-0.workflow.json`

Deliver four interactive artifacts:

- `public/archmaps/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.html`
- `public/archmaps/en-ai-ml-sagemaker-ai-01-platform-architecture-0.html`
- `public/archmaps/ko-ai-ml-sagemaker-ai-04-validation-results-0.html`
- `public/archmaps/en-ai-ml-sagemaker-ai-04-validation-results-0.html`

Provide four static images:

- `ko/.gitbook/assets/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.png`
- `en/.gitbook/assets/en-ai-ml-sagemaker-ai-01-platform-architecture-0.png`
- `ko/.gitbook/assets/ko-ai-ml-sagemaker-ai-04-validation-results-0.png`
- `en/.gitbook/assets/en-ai-ml-sagemaker-ai-04-validation-results-0.png`

### Diagram 1: Target architecture

Use Archify `architecture` with `meta.quality_profile: "showcase"` and no
animation.

The main path is:

1. synthetic dataset generator;
2. S3 dataset/source;
3. SageMaker AI Training Job;
4. Qwen QLoRA adapter;
5. aggregate evaluation;
6. SageMaker MLflow App.

Show side branches:

- Unified Studio project/catalog governs the dataset and artifacts;
- an EKS GPU Job consumes the same source and dataset;
- in-cluster MLflow tracks the EKS run;
- teardown inventory controls ephemeral resources.

Use no more than 11 primary nodes. Add a visible card stating that the GPU
training branches are target design and were not executed in the recorded
validation.

Use source evidence on relevant components from the config, launchers, and
result JSON.

### Diagram 2: Actual validation workflow

Use Archify `workflow` schema version 2, showcase quality, and no animation.

The main rail is:

1. local dataset/tests passed;
2. AWS preflight passed;
3. attempt 1: App status contract mismatch;
4. teardown succeeded;
5. attempt 2: project tag policy rejection;
6. teardown succeeded;
7. attempt 3: project membership failure;
8. App/S3/IAM cleanup;
9. blocked on one Unified Studio project;
10. GPU training not started.

The workflow must make cleanup branches and the final blocked state obvious.
It must not visually imply that SageMaker or EKS training completed.

### Archify quality contract

- Use the installed Archify skill only.
- Read the architecture schema/example for Diagram 1 and the workflow
  schema/example for Diagram 2.
- Set `meta.quality_profile` to `showcase`.
- Use automatic routes first.
- Run `scripts/check-update.mjs` once after the first candidate exists.
- Validate after every candidate change.
- Final validation must report all nine showcase checks with zero composition
  errors and zero warnings.
- Use `deliver` once per final artifact.
- Run `visual-check` after delivery at all required desktop sizes.
- Inspect the generated contact sheets with `view_image`.
- Do not modify delivered HTML after acceptance.
- Korean authored diagrams omit `meta.locale`; the Korean guide must disclose
  that fixed viewer controls fall back to English.

## Embedding Contract

Each diagram location uses:

1. a static PNG with descriptive alt text;
2. a blank line;
3. an interactive Archify link using the existing public URL convention.

The VitePress Markdown rule replaces this pair with an iframe. GitBook keeps the
static image and link.

## Navigation and Cross-links

Update both locales:

- `ko/SUMMARY.md`, `en/SUMMARY.md`
- `ko/README.md`, `en/README.md`
- `ko/data-on-eks/README.md`, `en/data-on-eks/README.md`
- `ko/ai-ml/mlflow/README.md`, `en/ai-ml/mlflow/README.md`
- `ko/ai-ml/05-model-training.md`, `en/ai-ml/05-model-training.md`
- selected Kubeflow comparison text where SageMaker is already mentioned.

The AI/ML navigation lists the SageMaker AI landing page and Parts 1, 2, 3,
and 5. The Data navigation lists Unified Studio as Part 4 and as a standalone
managed workspace guide.

Do not edit `cn/`, `jp/`, or `es/`.

## Content Style

- Primary authored languages are Korean and English.
- Keep exact AWS product names, APIs, model IDs, code identifiers, paths, and
  commands in English.
- Lead each part with a short “what you will learn” block.
- Prefer concise tables, callouts, and decision summaries over long prose.
- Use consistent status callouts:
  - ✅ validated;
  - 🧭 target design;
  - ⛔ not executed or blocked.
- Do not use status icons as the only carrier of meaning.
- Link primary AWS, Qwen, MLflow, and EKS documentation for current external
  facts.

## Validation

Add a Node content contract that verifies both locales contain:

- all five guidebook parts;
- matching quiz links;
- exact model ID;
- exact dataset counts;
- the phrase `TYPE<TAB>ORIGINAL`;
- explicit “training not executed” wording;
- no measured fine-tuning F1 or GPU cost;
- the Unified Studio membership distinction;
- both Archify static and interactive assets.

Run:

1. Archify showcase validation and delivery receipts;
2. Archify visual checks and manual contact-sheet inspection;
3. the focused guidebook content contract;
4. all Python experiment tests;
5. `npm run docs:test`;
6. local link and image validation;
7. Korean and English VitePress builds;
8. `git diff --check`;
9. sensitive-data scan for account IDs, ARNs, access keys, resource IDs, and
   presigned URLs.

If full link validation still fails only on known unrelated baseline files,
record those exact paths and verify this change introduces no new broken links.

## Non-goals

- claiming SageMaker or EKS fine-tuning completed;
- inventing fine-tuned accuracy, duration, or cost;
- running another GPU experiment;
- changing the Qwen training package beyond documentation-driven corrections;
- deleting the remaining Unified Studio project without domain-owner
  authorization;
- editing translated mirror locales;
- adding motion or presentation features to Archify artifacts.
