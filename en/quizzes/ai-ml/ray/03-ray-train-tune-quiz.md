# Ray Train / Tune Quiz

## Multiple Choice Questions

1. What does Ray Train not author automatically?
   - A) Underlying worker coordination
   - B) Framework process-group setup
   - C) All model/data-partition/state-save-and-restore logic
   - D) Ray resource requests

<details>
<summary>Show Answer</summary>

**Answer: C**

Prepare model/data-loader integration and the real model, optimizer, and checkpoint logic.
</details>

2. What is the reviewed Train V2 default in 2.58.0?
   - A) V2 when the environment variable is unset
   - B) Only V1 can run
   - C) The TorchTrainer import was removed
   - D) Ray extras automatically install PyTorch

<details>
<summary>Show Answer</summary>

**Answer: A**

Distinguish runs explicitly selecting the older implementation. Frameworks are separate dependencies.
</details>

3. What happens when legacy trainer_resources is set in V2?
   - A) It always reserves more controller CPU
   - B) A deprecation error is raised
   - C) GPU count increases
   - D) Tune trial count changes

<details>
<summary>Show Answer</summary>

**Answer: B**

Controller, training-worker, and Tune-driver resource scopes differ.
</details>

4. What does Checkpoint.from_directory do?
   - A) Automatically captures every model/optimizer/RNG state
   - B) References files in a user-prepared checkpoint directory
   - C) Deploys the model
   - D) Anonymizes the dataset

<details>
<summary>Show Answer</summary>

**Answer: B**

Author the recovery payload and load the checkpoint returned by get_checkpoint.
</details>

5. What is the 2.58.0 V2 report participation rule?
   - A) Only rank 0 calls it
   - B) Every worker reaches the barrier the same number of times
   - C) Every metric is automatically averaged
   - D) It cannot be called without a checkpoint

<details>
<summary>Show Answer</summary>

**Answer: B**

Other workers report checkpoint=None even when only rank 0 saves files.
</details>

6. Does max_failures=0 disable every retry?
   - A) Yes
   - B) No; controller and preemption retries have separate settings
   - C) It always means infinite retries
   - D) It only disables Karpenter retries

<details>
<summary>Show Answer</summary>

**Answer: B**

Reviewed defaults for controller_failure_limit and max_preemption_failures are both -1.
</details>

7. What is the current V2 Train/Tune integration pattern?
   - A) Pass the V2 Trainer instance directly to Tuner
   - B) Construct and fit a Trainer inside a function trainable; connect callbacks as needed
   - C) The libraries cannot be combined
   - D) A separate Kubernetes cluster is always needed

<details>
<summary>Show Answer</summary>

**Answer: B**

Direct V2 Trainer input raised TuneError in the native check. Integration needs wiring and resource planning.
</details>

8. What does TuneReportCallback forward?
   - A) An automatically averaged worker metric
   - B) A second checkpoint upload
   - C) The first worker metric dictionary and existing checkpoint path
   - D) It always works outside Tune sessions

<details>
<summary>Show Answer</summary>

**Answer: C**

Construct it in a Tune session. Perform metric aggregation separately.
</details>

## Short Answer Questions

9. Why budget trial drivers and Train workers together?

<details>
<summary>Show Answer</summary>

Drivers can occupy resources required by their nested workers or placement groups. Check concurrency, worker bundles, cluster bounds, and per-node feasibility together.
</details>

10. What does a successful scalar Tune example not establish?

<details>
<summary>Show Answer</summary>

It does not prove model accuracy, PyTorch/DDP or GPU performance, multi-node checkpoint recovery, or EKS autoscaling. It checks APIs and collection of two scalar-trial results.
</details>

---

[Return to Learning Materials](../../../ai-ml/ray/03-ray-train-tune.md)
