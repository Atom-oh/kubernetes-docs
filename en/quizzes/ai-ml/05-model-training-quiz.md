# Model Training on EKS Quiz

15questions on current APIs, launchers and recovery boundaries.

## 1. What does tensor parallelism partition?

<details>
<summary>Answer and explanation</summary>

Tensor operations and weights within layers. DP partitions data across replicas, PP partitions layer stages, and expert parallelism partitions experts/token dispatch; their communication differs.
</details>

## 2. How should a200B model and global batch be planned?

<details>
<summary>Answer and explanation</summary>

Do not mandate3D from size alone; account for training state, activations, communication and device mesh. TP8×PP4×DP2 is64ranks, but microbatch1×accumulation32×DP2 gives global batch64.
</details>

## 3. How do slurmctld and slurmdbd state responsibilities differ?

<details>
<summary>Answer and explanation</summary>

slurmctld manages running job/node/partition state, scheduling and StateSaveLocation. slurmdbd handles accounting database records and does not replace controller recovery state.
</details>

## 4. What is the Slinky1.2.2 compute-group API?

<details>
<summary>Answer and explanation</summary>

slinky.slurm.net/v1beta1 NodeSet, using a Controller reference/template. Default StatefulSet-style or optional DaemonSet-style scaling; replicas is ignored in DaemonSet mode. The kind is not SlurmNodeSet.
</details>

## 5. Does FI_PROVIDER=efa alone enable NCCL over EFA?

<details>
<summary>Answer and explanation</summary>

No. EFA interfaces, driver/libfabric/aws-ofi-nccl, device plugin/Pod allocation, security groups and same-AZ placement are needed. Verify actual transport with logs/collective tests;400Gbps is not universal.
</details>

## 6. What should be checked for BioNeMo3.0.0?

<details>
<summary>Answer and explanation</summary>

Model/TransformerEngine/training-recipe support in BioNeMo Recipes. Do not reuse the old1.5 MegaMolBART module unverified; validate image/data/model revisions, devices, convergence and biological evaluation.
</details>

## 7. Does Optimum Neuron Trainer guarantee training for every HF model?

<details>
<summary>Answer and explanation</summary>

No. Match versioned training-model implementations, configuration, SDK/PyTorch, hardware, data and collator. Inference support differs from training support; a pretrained model and undefined dataset do not implement TP training.
</details>

## 8. How should FSx and S3 integration be verified?

<details>
<summary>Answer and explanation</summary>

Distinguish static mounts from dynamic provisioning and verify DRA/import/export policies, completion and permissions. EFS PVC capacity is not a quota, and local storage alone does not establish S3 durability.
</details>

## 9. Does Volcano minAvailable:4 require four nodes?

<details>
<summary>Answer and explanation</summary>

No; it counts Pods/members. Three nodes may fit four Pods. Check minimum-member/resource conditions and the gang plugin; it does not guarantee simultaneous startup or training success.
</details>

## 10. How does BF16 differ from FP16?

<details>
<summary>Answer and explanation</summary>

It has8exponent/7mantissa bits. The exponent-bit count matches FP32, not its precision or exact maximum finite value. FP16-style loss scaling is commonly unnecessary, but validate hardware/operations/convergence; autocast does not cast all training state.
</details>

## 11. How do activation checkpoints differ from recovery checkpoints?

<details>
<summary>Answer and explanation</summary>

Activation checkpointing trades backward recomputation for memory; it differs from disk model/optimizer/RNG recovery state. Verify use_reentrant, RNG/state and gradients without assuming fixed3–4x savings.
</details>

## 12. Does ZeRO Stage3 automatically offload to CPU?

<details>
<summary>Answer and explanation</summary>

No. It partitions optimizer state, gradients and parameters; offload is configured separately. Memory reduction depends on DP size, state, buffers and activations, not unlimited scaling.
</details>

## 13. What does MPIJob slotsPerWorker establish?

<details>
<summary>Answer and explanation</summary>

Worker hostfile slots. Actual process count depends on mpirun -np/mapping and launcher setup; one-rank-per-GPU binding needs explicit configuration. Operator0.8.2 uses the v2beta1 API.
</details>

## 14. How should checkpoint frequency and recovery be verified?

<details>
<summary>Answer and explanation</summary>

Choose intervals from save latency, failure rate, acceptable lost work and retention cost. Verify complete state/manifests/checksums, remote completion and actual resume. The guide checks identical CPU results for four uninterrupted updates versus resuming after two.
</details>

## 15. What do same-AZ EFA placement and Karpenter disruption budgets mean?

<details>
<summary>Answer and explanation</summary>

Connect Pod/NodePool constraints so communicating workers actually share an AZ. Placement groups are recommended for performance. Budget0 limits voluntary disruption, not Spot reclamation, failures or forced termination.
</details>

[Return to guide](../../ai-ml/05-model-training.md)
