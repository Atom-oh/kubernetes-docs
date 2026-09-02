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

The Job exposes failure and terminates within the three-hour bound.
</details>

4. When must cleanup verification fail?
   - A) No resources remain
   - B) Any App, project, bucket, role, or cluster remains
   - C) Smoke succeeds
   - D) Dataset hashes match

<details>
<summary>Show Answer</summary>

**Answer: B**

The remaining resource count must be zero.
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

---

[Return to learning materials](../../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
