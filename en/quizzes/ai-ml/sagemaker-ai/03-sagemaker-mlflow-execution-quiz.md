# SageMaker AI and MLflow Execution Quiz

## Multiple Choice Questions

1. Which resource is used for new managed MLflow deployments?
   - A) Only the legacy Tracking Server
   - B) SageMaker MLflow App
   - C) A public EKS LoadBalancer
   - D) Only a local SQLite file

<details>
<summary>Show Answer</summary>

**Answer: B**

The managed path uses the current SageMaker MLflow App API.
</details>

2. What is required before a full run?
   - A) A completed smoke run and raw-PII logging scan
   - B) Removal of project membership
   - C) Immediate maximum-step execution
   - D) Disabled teardown

<details>
<summary>Show Answer</summary>

**Answer: A**

Review smoke completion, logging safety, aggregate results, and adapter inventory first.
</details>

3. What is the EKS Job failure/deadline contract?
   - A) Unlimited retries and no deadline
   - B) `backoffLimit: 0` and `activeDeadlineSeconds: 10800`
   - C) Ten retries and one hour
   - D) A permanent Deployment

<details>
<summary>Show Answer</summary>

**Answer: B**

These are retry and Job deadline settings. Controller or node failures can delay reclamation; they do not guarantee all resources disappear within three hours or cap total cost.
</details>

4. When must cleanup verification fail?
   - A) No resources remain
   - B) Resources remain or errors prevent confirming their state
   - C) Smoke succeeds
   - D) Dataset hashes match

<details>
<summary>Show Answer</summary>

**Answer: B**

Zero remaining is insufficient when queries failed. Preserve unknown states and refuse name-only deletion from old inventories without ownership evidence.
</details>

5. What was actually exercised on September 1?
   - A) A full SageMaker Training Job
   - B) A full EKS GPU Job
   - C) Provisioning and cleanup paths
   - D) Tuned-model evaluation

<details>
<summary>Show Answer</summary>

**Answer: C**

Both GPU Jobs stopped before submission.
</details>

6. Why is GPU execution blocked as of September 12, 2026?
   - A) The pinned PyTorch 2.8 DLC reached end of patch on August 6
   - B) Source bundling is billable
   - C) Every MLflow App was deleted
   - D) Local unit tests require a GPU

<details>
<summary>Show Answer</summary>

**Answer: A**

Validate a supported DLC, torch, dependency cohort, and GPU smoke run. Removing the date check alone is not an upgrade.
</details>

7. What does the SageMaker launcher do without `--execute`?
   - A) Submit the full Job immediately
   - B) Write the request JSON only
   - C) Delete existing Jobs
   - D) Guarantee a cost estimate

<details>
<summary>Show Answer</summary>

**Answer: B**

Request preview is the default. Actual submission requires the runtime support check and separate review.
</details>

8. Is saving EKS MLflow metric/parameter JSON enough?
   - A) Yes, it automatically includes adapter weights
   - B) Download final adapters and aggregate artifacts, then verify hashes
   - C) `emptyDir` survives cluster deletion
   - D) A log tail can reconstruct the model

<details>
<summary>Show Answer</summary>

**Answer: B**

Metadata export is different from preserving files. A cluster retained after export failure also needs cost awareness and subsequent cleanup.
</details>

---

[Return to learning materials](../../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
