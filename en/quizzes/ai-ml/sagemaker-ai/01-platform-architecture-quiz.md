# SageMaker Qwen Platform Architecture Quiz

## Multiple Choice Questions

1. How do model output and Python processing relate in this design?

   - A) The model certainly removes all PII
   - B) The model emits candidate TSV and code validates/replaces it; missed detection is evaluated separately
   - C) A round trip proves anonymity
   - D) The model deletes projects

<details>
<summary>Show Answer</summary>

**Answer: B**

Deterministic replacement does not automatically recover entities the model missed.

</details>

2. How should the diagram and validation record be interpreted?

   - A) Both GPU paths were validated
   - B) It is a target design; distinguish local tests from historical AWS observations
   - C) It shows live residual-project counts
   - D) It reports trained F1 and costs

<details>
<summary>Show Answer</summary>

**Answer: B**

The 2026-09-01 record stopped before training. Current AWS state and GPU outcomes are not proven by local tests.

</details>

3. Do identical model IDs and seeds fully reproduce results across environments?

   - A) Always
   - B) No; also verify revisions, data hashes, images/dependencies, CUDA/hardware and execution conditions
   - C) Only EKS needs a seed
   - D) The tokenizer does not matter for QLoRA

<details>
<summary>Show Answer</summary>

**Answer: B**

Direct package pins are not a full transitive lock, and GPU determinism has additional requirements.

</details>

4. What should be excluded from ordinary MLflow logs/public reports?

   - A) Dataset hashes
   - B) Reviewed LoRA settings
   - C) Raw source/completions, token mappings and presigned URLs
   - D) Non-sensitive aggregates

<details>
<summary>Show Answer</summary>

**Answer: C**

Distinguish necessary private inventory IDs/ARNs from public disclosure, and verify autologging/tracing.

</details>

5. Which statement about governance and model size is correct?

   - A) QLoRA always requires a Unified Studio project
   - B) Governance is this experiment's chosen procedure; 3.3B active does not represent total model memory
   - C) Owner assignment atomically rolls back every partial failure
   - D) A three-hour job limit caps all experiment costs

<details>
<summary>Show Answer</summary>

**Answer: B**

The model card lists 30.5B total/3.3B active. Verify readiness/ownership and actual GPU memory/cost separately.

</details>

---

[Return to Learning Materials](../../../ai-ml/sagemaker-ai/01-platform-architecture.md)
