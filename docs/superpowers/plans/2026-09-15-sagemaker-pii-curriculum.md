# SageMaker PII fine-tuning curriculum implementation plan

> **For agentic workers:** Apply `superpowers:subagent-driven-development` or `superpowers:executing-plans` to the scoped tasks below. Review each deliverable before integration.

**Goal:** Teach how to prepare and augment PII extraction data, reason about QLoRA training, and evaluate a redaction pipeline, with an executable CPU exercise and parallel Korean/English guides.

**Architecture:** Extend the existing SageMaker guidebook with three practical chapters. Add a separate deterministic augmentation lab that uses the existing record contract without changing the historical generator, its manifests, or the guarded GPU launchers.

**Tech stack:** Python 3.12, pytest, existing PII parsing/evaluation helpers, Markdown, GitBook SUMMARY navigation, VitePress.

**Spec:** The user's September 15 request identifies insufficient SageMaker fine-tuning, QLoRA, PII tuning, and data augmentation instruction. The bounded design is: a QLoRA walkthrough, a CPU augmentation exercise, and an evaluation/release chapter connected to the current guidebook.

## Global constraints

- Preserve generator 1.0.0 and its published 2,200-record hashes.
- Preserve the historical runtime support guard; do not describe GPU training as completed.
- Use synthetic examples only; do not download model weights, call AWS, or launch billable jobs for this documentation task.
- Match code explanations to the pinned PEFT 0.17.1, Transformers 4.57.6, and TRL 0.24.0 implementation; label differences from current upstream examples.
- Keep augmentation descendants with their source family and augment training data only.
- Describe family separation, exact-text separation, entity separation, and template separation as different guarantees.
- Record measured CPU results as CPU results; never label an oracle or fixture score as model quality.
- Add both Korean and English pages and navigation entries.
- Use task-specific EBS temporary directories; run full site builds in hosted CI.
- Require latest-HEAD independent review, content score at least 85, passing CI, and live deployment verification before completion.

## Task 1: Executable augmentation and data audit exercise

**Files**

- Create `examples/ai-ml/qwen-pii-finetuning/data/augmentation_lab.py`.
- Create `examples/ai-ml/qwen-pii-finetuning/tests/test_augmentation_lab.py`.

**Interface**

The executable module generates a separate lab directory containing split JSONL files and an aggregate manifest. Records retain `id`, `source_text`, `entities`, and `target_tsv`, and add explicit family/split/augmentation provenance. The historical generator and training launchers are not changed.

```bash
python -m data.augmentation_lab --output-dir "$LAB_OUTPUT" --seed 42
python -m data.augmentation_lab --audit-dir "$LAB_OUTPUT"
```

- [x] Write tests for deterministic generation, disjoint family assignment, train-only augmentation, valid source/label/TSV correspondence, negative preservation, Unicode handling, duplicate/family leakage rejection, tampered hashes, and refusal to overwrite existing output.
- [x] Run the tests before implementation and confirm the missing module fails.
- [x] Implement deterministic synthetic base families, bounded label-preserving transformations, and aggregate-only audit output.
- [x] Run the exercise twice in separate temporary directories and compare hashes.
- [x] Run the package's full CPU test suite and confirm historical generator hashes remain unchanged.

## Task 2: QLoRA and SageMaker training walkthrough

**Files**

- Create `ko/ai-ml/sagemaker-ai/05-qlora-finetuning-workshop.md`.
- Create `en/ai-ml/sagemaker-ai/05-qlora-finetuning-workshop.md`.

- [x] Explain extraction versus rewriting, LoRA matrix dimensions/scaling, frozen quantized base weights, NF4, double quantization, compute dtype, activations, checkpointing, and optimizer memory.
- [x] Walk through the existing trainer in execution order: prompt/completion, tokenization and loss mask, model loading, adapter targets, batching, validation, saving, and inference.
- [x] Explain the 30.5B-total/3.3B-active MoE memory distinction and why named target modules must be inspected.
- [x] Provide a controlled tuning matrix, effective-batch/step calculations, small-sample overfitting check, and symptom-to-action table.
- [x] Map local files, source bundle, S3 channel, `/opt/ml` paths, training state, MLflow metrics, and adapter artifacts.
- [x] Explain the current runtime migration prerequisite without presenting an untested replacement image as validated.
- [x] Reference primary papers, versioned Hugging Face documentation, and official SageMaker documentation.

## Task 3: Augmentation and PII evaluation chapters

**Files**

- Create Korean/English `06-data-augmentation-workshop.md`.
- Create Korean/English `07-pii-evaluation-release.md`.

- [x] Describe the annotation contract and distinguish synthesis from augmentation.
- [x] Cover entity substitution, formatting/OCR variants, contextual paraphrases, negative examples, rare types, long documents, and label validity.
- [x] Include the exact tested CPU commands, output schema, audit behavior, and expected aggregate results.
- [x] Explain split-before-augmentation and the additional held-out entity/template/domain tests needed for generalization.
- [x] Demonstrate baseline versus candidate evaluation with controlled synthetic predictions and the existing metric APIs.
- [x] Explain entity recall/F1, residual PII, over-redaction, malformed output, subgroup counts, locked test sets, abstention, monitoring, and rollback.
- [x] Separate irreversible removal from reversible token replacement; explain that mappings and trained adapters need appropriate handling.
- [x] Include exercises with checkable answers, not invented benchmark results.

## Task 4: Integration and publication

**Files**

- Update Korean/English guidebook `README.md`, `02-pii-data-tokenization.md`, and `03-sagemaker-mlflow-execution.md` with practical entry links.
- Update `ko/SUMMARY.md` and `en/SUMMARY.md`.
- Update the example package `README.md` with the CPU exercise and scope.
- Create the six matching Korean/English quiz files under
  `quizzes/ai-ml/sagemaker-ai/` with `<chapter>-quiz.md` names.

- [x] Add a practical learning route ahead of the historical implementation/validation route.
- [x] Check every new local reference and Korean/English counterpart.
- [x] Satisfy the existing per-chapter quiz rule with eight explained questions
  per quiz, forward/back links, and SUMMARY entries; do not modify the parity baseline.
- [x] Run the full package CPU suite and `npm run docs:validate`.
- [x] Compile/render representative new pages, inspect desktop/mobile layout, and verify the exercise commands and navigation.
- [ ] Obtain independent latest-HEAD code/content review; resolve Critical/Major findings.
- [ ] Push the reviewed branch, complete hosted PR checks, verify current HEAD/base/reviews, and merge under the user's standing authorization.
- [ ] Verify the Pages deployment, published chapter navigation, and AI-readable Markdown availability.
- [ ] Clean up only this task's worktree after verification.
