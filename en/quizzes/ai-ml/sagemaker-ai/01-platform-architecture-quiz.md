# SageMaker Qwen Platform Architecture Quiz

This quiz checks the target architecture's responsibility boundaries and the SageMaker AI/EKS path split.

## Multiple Choice Questions

1. What does the Qwen model directly emit?
   - A) The final masked document
   - B) `TYPE<TAB>ORIGINAL` entity rows
   - C) A Unified Studio project
   - D) An S3 deletion report

<details>
<summary>Show Answer</summary>

**Answer: B**

The model extracts entities; deterministic Python code validates, orders, and replaces them.
</details>

2. How should the Part 1 diagram be interpreted?
   - A) Evidence that both GPU paths completed
   - B) A target design for a rerun
   - C) A measured GPU cost comparison
   - D) Production deployment approval

<details>
<summary>Show Answer</summary>

**Answer: B**

The diagram is a target design and neither GPU training path was executed.
</details>

3. What makes the two execution paths comparable?
   - A) Different dataset splits
   - B) Frozen model ID, seed, hashes, dependencies, and QLoRA settings
   - C) MLflow only on EKS
   - D) Starting with a full run

<details>
<summary>Show Answer</summary>

**Answer: B**

Only the environment should vary when comparing the paths.
</details>

4. Which value must not be logged to a SageMaker MLflow App?
   - A) Dataset SHA-256
   - B) LoRA rank
   - C) Raw source text and token mapping
   - D) Dependency version

<details>
<summary>Show Answer</summary>

**Answer: C**

MLflow receives aggregate and non-sensitive experiment information only.
</details>

5. Why is project governance checked before GPU training?
   - A) To accelerate model downloads
   - B) A project without membership can become inaccessible to automation
   - C) QLoRA requires a project profile
   - D) EKS only runs inside DataZone

<details>
<summary>Show Answer</summary>

**Answer: B**

Owner membership at creation prevents an inaccessible project after partial provisioning.
</details>

---

[Return to learning materials](../../../ai-ml/sagemaker-ai/01-platform-architecture.md)
