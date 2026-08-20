# Ray Train and Ray Tune Quiz

This quiz tests your understanding of Ray Train (Trainer, ScalingConfig, checkpointing), Ray Tune, and how the two combine for distributed hyperparameter tuning.

## Multiple Choice Questions

1. What problem does Ray Train primarily solve for a distributed training script?
   - A) It replaces PyTorch and other training frameworks with a new training API
   - B) It handles the boilerplate of launching worker processes, setting up their communication group, and coordinating checkpoints
   - C) It automatically labels training data before a run starts
   - D) It removes the need for GPUs by running training entirely on CPU

<details>

<summary>Show Answer</summary>

**Answer: B) It handles the boilerplate of launching worker processes, setting up their communication group, and coordinating checkpoints**

**Explanation:**
Ray Train is built on Ray's task and actor primitives and takes over the distributed-training boilerplate — launching one worker per allocated resource, setting up the inter-worker communication group (for example, a PyTorch DDP process group), and coordinating checkpointing — so a training script written against a familiar framework API can scale without the author hand-rolling that coordination.
</details>

2. Which of the following best describes Ray Train V2?
   - A) A completely separate product unrelated to earlier Ray Train releases
   - B) A rewritten implementation behind the existing `ray.train.torch.TorchTrainer` import path, which consolidates and simplifies how an earlier generation of trainer classes worked internally
   - C) A version of Ray Train that only supports CPU-based training
   - D) A deprecated API that Ray no longer documents

<details>

<summary>Show Answer</summary>

**Answer: B) A rewritten implementation behind the existing `ray.train.torch.TorchTrainer` import path, which consolidates and simplifies how an earlier generation of trainer classes worked internally**

**Explanation:**
Ray Train's API surface has evolved over time, but the user-facing import path (`ray.train.torch.TorchTrainer` for PyTorch) hasn't changed — what changed is the implementation behind it. Exact version history for when this rewrite became the default is best checked against the current Ray documentation rather than assumed.
</details>

3. What is the role of a `ScalingConfig` in Ray Train?
   - A) It specifies how many workers to launch and what resources (such as GPUs) each one needs
   - B) It defines the neural network architecture used during training
   - C) It sets the learning rate schedule for the optimizer
   - D) It configures which cloud region the Ray cluster runs in

<details>

<summary>Show Answer</summary>

**Answer: A) It specifies how many workers to launch and what resources (such as GPUs) each one needs**

**Explanation:**
A `ScalingConfig` tells the Trainer how many workers to launch and whether each one requires a GPU. The Trainer uses this to request the corresponding resources from the underlying Ray cluster, the same way any other Ray task or actor would.
</details>

4. Besides enabling recovery after a worker failure, what other purpose does Ray Train checkpointing serve?
   - A) It compresses the training dataset to save storage
   - B) It hands off a trained model to a later step in the workflow, such as a hyperparameter-tuning decision or model registration
   - C) It automatically deploys the model to a production serving endpoint
   - D) It replaces the need for a ScalingConfig

<details>

<summary>Show Answer</summary>

**Answer: B) It hands off a trained model to a later step in the workflow, such as a hyperparameter-tuning decision or model registration**

**Explanation:**
A reported checkpoint captures enough state (typically model weights and optimizer state) to resume training, but it also serves as the handoff point to whatever comes next — for example, a tuning decision, or registering the result as a model version, conceptually similar to the model registry pattern covered elsewhere in this documentation site.
</details>

5. What does Ray Tune do?
   - A) It runs many training trials in parallel across the cluster and uses a pluggable search algorithm to decide which hyperparameter combinations to try next
   - B) It only tunes a single hyperparameter at a time, sequentially
   - C) It replaces Ray Train entirely for any distributed training workload
   - D) It is a Kubernetes CRD-based controller unrelated to Ray's core primitives

<details>

<summary>Show Answer</summary>

**Answer: A) It runs many training trials in parallel across the cluster and uses a pluggable search algorithm to decide which hyperparameter combinations to try next**

**Explanation:**
Ray Tune is a hyperparameter tuning library built on Ray. Each trial trains with one hyperparameter combination and reports a result back, which Tune's search algorithm uses to decide what to try next. This is conceptually parallel to what Katib provides in the Kubeflow ecosystem, but native to Ray rather than a separate Kubernetes CRD-based system.
</details>

6. How does Ray Tune commonly combine with Ray Train for a model that itself needs distributed training?
   - A) Tune and Train cannot be used together; a team must choose one or the other
   - B) Tune wraps a Ray Train `Trainer` as the trainable it searches over, so each trial becomes its own distributed Ray Train run
   - C) Ray Train runs first to completion, and only then does Ray Tune begin, on a separate cluster
   - D) Tune replaces the Trainer's ScalingConfig with its own resource model

<details>

<summary>Show Answer</summary>

**Answer: B) Tune wraps a Ray Train `Trainer` as the trainable it searches over, so each trial becomes its own distributed Ray Train run**

**Explanation:**
A common pattern gives Tune a Ray Train `Trainer` as the trainable. Each hyperparameter trial is then itself a distributed Ray Train run, potentially spanning multiple GPUs or nodes — useful when a single trial needs distributed training to finish in reasonable time.
</details>

7. Why does the KubeRay-managed autoscaler on EKS react to a Ray Train or Ray Tune job's actual resource demand?
   - A) Because Ray Train and Ray Tune request CPUs and GPUs through Ray's normal task/actor resource-request mechanism, the same as any other Ray workload
   - B) Because Ray Train and Ray Tune communicate directly with the Kubernetes API server, bypassing Ray's scheduler
   - C) Because the cluster must always be provisioned at a fixed size before any job runs
   - D) Because Karpenter monitors GPU utilization inside the training process itself

<details>

<summary>Show Answer</summary>

**Answer: A) Because Ray Train and Ray Tune request CPUs and GPUs through Ray's normal task/actor resource-request mechanism, the same as any other Ray workload**

**Explanation:**
Both libraries request resources through Ray's ordinary task/actor resource-request mechanism, with no separate path specific to training or tuning. This is what lets the autoscaler covered in Part 2 react to real demand — requesting more worker nodes as a Tune sweep launches more concurrent trials, and scaling back down once trials finish — instead of requiring a fixed-size cluster up front.
</details>

8. What practical issue can arise from the co-scheduling needs of a Ray Train run's distributed workers on EKS?
   - A) None — Ray Train workers never need to start at the same time
   - B) A training run can stall waiting for the last few GPU workers to come up if the autoscaler cannot provision all requested workers within a reasonable window
   - C) Co-scheduling only matters for Ray Tune, never for Ray Train
   - D) Checkpointing automatically resolves any co-scheduling delay

<details>

<summary>Show Answer</summary>

**Answer: B) A training run can stall waiting for the last few GPU workers to come up if the autoscaler cannot provision all requested workers within a reasonable window**

**Explanation:**
The workers in one Ray Train run typically need to be co-scheduled — all up and holding their allocated GPUs before their communication group can be established, similar to gang-scheduling needs discussed elsewhere in this documentation site. GPU node pool provisioning lead time is often longer and less predictable than for CPU nodes, so a training job's real start time depends on how quickly every requested worker can be co-scheduled.
</details>

## Short Answer Questions

9. Explain what a Ray Train `Trainer` and a `ScalingConfig` each do, and how they work together to run a distributed training job.

<details>

<summary>Show Answer</summary>

**Answer:**
A Trainer (such as `TorchTrainer`) wraps a user-supplied training function that contains ordinary model-training logic — building the model, iterating over batches, computing loss, and stepping the optimizer. The Trainer is responsible for launching that function once per worker, inside the distributed process group the underlying framework's data-parallel training expects (for example, a PyTorch DDP process group), so the training function itself does not need to set up that coordination by hand.

A `ScalingConfig` tells the Trainer how many workers to launch and what resources each one needs, such as whether a GPU is required. The Trainer uses the `ScalingConfig` to request the corresponding resources from the underlying Ray cluster through Ray's normal task/actor resource-request mechanism. Together, the Trainer supplies the training logic and coordination, and the `ScalingConfig` supplies the resource shape the Trainer scales that logic across.
</details>

10. Describe why combining Ray Tune with Ray Train is useful, and how resource requests from that combination interact with cluster autoscaling on EKS.

<details>

<summary>Show Answer</summary>

**Answer:**
Some models are expensive enough to train that a single hyperparameter trial itself needs distributed (multi-GPU or multi-node) training to finish in a reasonable amount of time. Without combining the two libraries, a team would either have to tune hyperparameters serially against a distributed training job, or give up distributed training during the search phase. Because Ray Tune can wrap a Ray Train `Trainer` as its trainable, each trial becomes its own distributed Ray Train run, and Tune can run several such runs concurrently while deciding which hyperparameter combinations to try next.

Because every worker in every trial still requests CPUs and GPUs through Ray's normal task/actor resource-request mechanism, the KubeRay-managed autoscaler on EKS sees the combined, real-time resource demand of all active trials rather than a single, pre-declared shape. It can provision more worker nodes as a Tune sweep launches more concurrent trials, and scale back down as trials finish, instead of requiring the cluster to be sized up front for the largest possible sweep.
</details>

---

[Return to Learning Materials](../../../ai-ml/ray/03-ray-train-tune.md) | [Next Quiz: Ray Serve](./04-ray-serve-quiz.md)
