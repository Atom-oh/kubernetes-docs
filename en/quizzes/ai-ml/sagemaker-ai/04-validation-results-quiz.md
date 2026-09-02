# SageMaker Qwen Factual Validation Results Quiz

## Multiple Choice Questions

1. What did the September 2 recheck find?
   - A) Zero remaining resources
   - B) One Unified Studio project still `ACTIVE`
   - C) One running EKS GPU cluster
   - D) A completed Training Job

<details>
<summary>Show Answer</summary>

**Answer: B**

The App, S3, and IAM resources were reclaimed, but one project remains.
</details>

2. What was the key failure in attempt 3?
   - A) A misspelled model ID
   - B) Missing project membership
   - C) A dataset hash mismatch
   - D) CUDA out of memory

<details>
<summary>Show Answer</summary>

**Answer: B**

The caller role group profile was not assigned as an owner/member.
</details>

3. Which results were not published?
   - A) Record count
   - B) MLflow App version
   - C) Fine-tuned F1 and GPU cost
   - D) Python test count

<details>
<summary>Show Answer</summary>

**Answer: C**

GPU training was not executed, so those values were not measured.
</details>

4. What is the first rerun gate?
   - A) Submit the full Job
   - B) Verify that no `qwen-pii-*` project remains
   - C) Create an EKS cluster
   - D) Publish tuned metrics

<details>
<summary>Show Answer</summary>

**Answer: B**

Preflight must block a new run while the project remains.
</details>

5. How do the target architecture and actual workflow differ?
   - A) Both prove completion
   - B) One is a rerun design; the other records the real stop point
   - C) Both are cost reports
   - D) The actual workflow shows completed GPU training

<details>
<summary>Show Answer</summary>

**Answer: B**

The actual workflow terminates at `stop before spend`.
</details>

---

[Return to learning materials](../../../ai-ml/sagemaker-ai/04-validation-results.md)
