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

The historical record reported reclaimed App, S3, and IAM resources with one project remaining. The September 12 documentation review did not re-query current AWS state.
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

GPU training was not executed, so those comparison values were not measured. This does not imply zero total cost for resources such as the MLflow App and S3.
</details>

4. What is the first rerun gate?
   - A) Submit the full Job
   - B) Reconcile inventory and resolve remaining or unknown experiment-owned resources
   - C) Create an EKS cluster
   - D) Publish tuned metrics

<details>
<summary>Show Answer</summary>

**Answer: B**

Permission errors or absence from a list do not prove deletion. A shared name prefix does not authorize deleting someone else's resources.
</details>

5. How do the target architecture and actual workflow differ?
   - A) Both prove completion
   - B) One is a rerun design; the other records the real stop point
   - C) Both are cost reports
   - D) The actual workflow shows completed GPU training

<details>
<summary>Show Answer</summary>

**Answer: B**

The historical workflow stops before GPU training. It does not prove the current account state or zero total experiment cost.
</details>

---

[Return to learning materials](../../../ai-ml/sagemaker-ai/04-validation-results.md)
