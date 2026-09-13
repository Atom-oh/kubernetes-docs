# Part 5: Kubeflow Trainer and Distributed Training

> **Review baseline**: Trainer 2.2.0 / Community Distribution 26.03.1; separate 2.3.0 upgrade comparison
> **Last Updated**: September 12, 2026

## Lab Environment Setup

Use compatible Kubernetes, Trainer controller/CRDs, runtimes and their dependencies such as JobSet. GPUs are workload-dependent; CPU training is possible. GPU workloads additionally require drivers, device plugins, node capacity and networking. Validation here is Helm rendering and schema inspection, not training execution.

## From Framework-Specific Operators to a Unified API

Distributed training on Kubernetes has gone through a real architectural shift inside the Kubeflow project, and this is the most important thing to understand before touching any YAML.

### The original Training Operator (v1)

The Training Operator that Kubeflow consolidated in 2021 took a **framework-specific CRD** approach. Each supported ML framework got its own Custom Resource Definition, each with its own controller implementing that framework's particular distributed-training semantics:

* **`PyTorchJob`** — the controller understood PyTorch's distributed launch conventions, injecting environment variables like `MASTER_ADDR`, `RANK`, and `WORLD_SIZE` into each worker Pod so `torch.distributed` could form a process group.
* **`TFJob`** — the controller instead constructed a `TF_CONFIG` environment variable (a JSON blob describing the cluster's task roles — chief, worker, parameter server) that TensorFlow's distribution strategies expect.
* **`MPIJob`** — the controller handled launching an MPI job across Pods, coordinating an `mpirun`-style launcher against a set of worker Pods.

Beyond these three, the v1 Training Operator also shipped CRDs for a handful of other frameworks. Each CRD encoded a different framework's idea of "how workers find each other and agree on their roles" directly into a separate controller, so adding a framework required integration, while shared Job-controller plumbing could still be reused.

### The shift to Kubeflow Trainer v2

Kubeflow Trainer v2 replaces this with a single, unified API built around two concepts instead of one CRD per framework:

* **`TrainJob`** — describes *what* to run: the training script/entrypoint, arguments, resource counts (e.g., number of workers), and a reference to the runtime that should execute it. This is the object an ML practitioner creates for an individual training run.
* **`TrainingRuntime` / `ClusterTrainingRuntime`** — describes *how* to run it: a reusable, framework-specific execution template covering the container image, the distributed launch mechanics (how workers discover each other, what env vars or launcher process gets used), and default resource shape. A platform team defines a small set of these once — say, a PyTorch DDP runtime, an MPI runtime — and many different `TrainJob`s reference the same runtime across many training runs.

This mirrors a pattern seen elsewhere in Kubernetes: separating a reusable "template" resource from the "instance" that consumes it, similar in spirit to how a `StorageClass` is a reusable template that many `PersistentVolumeClaim`s reference. The practical benefit is that a platform team can own and version the tricky distributed-launch mechanics in one place (the runtime), while ML practitioners submitting jobs only need to supply their script and ask for a runtime by name — the runtime reduces repeated setup, while training code must still handle compatible distributed initialization, data sharding, checkpointing and recovery.

### Differences Between 2.2.0 and 2.3.0

[Trainer 2.2.0](https://github.com/kubeflow/trainer/releases/tag/v2.2.0) was released March 20, 2026 and is bundled in 26.03.1. It adds JAX/XGBoost runtimes and Flux policy/integration; feature inclusion does not prove compatibility with every image, network or accelerator configuration.

2.2.0 also replaces `PodTemplateOverrides` with `RuntimePatches` and removes `numProcPerNode` from the Torch policy and removes `ElasticPolicy`. Do not confuse a runtime Torch policy with per-run `trainer.numProcPerNode`. Earlier 2.x manifests can require migration too.

Runtime progress/metrics in `status.trainerStatus` require the **alpha TrainJobStatus feature gate, disabled by default**. Training code must report to the status server with working TLS/projected ServiceAccount-token access. Injected token/CA environment values are file paths, not secret contents. Printing logs alone does not automatically populate status metrics.

[2.3.0](https://github.com/kubeflow/trainer/releases/tag/v2.3.0), released August 7, 2026, changes runtime finalizers/snapshots and Helm CRD placement. Its release notes require 2.0/2.1/2.2 installations to pass through 2.3 before later versions. Review CRD Helm ownership and release-specific migration before upgrading; deleting existing CRDs is not a routine upgrade fix.

The published OCI charts also differ: 2.2 renders eight default runtimes directly, while 2.3 packages them in a runtimes.yaml ConfigMap applied by a post-install/post-upgrade installer Job. The 2.3 hook installs kubectl at runtime, force-applies resources server-side and prunes by its management label; a pre-delete hook also exists. Review GitOps hook handling, network access and runtime ownership. This review rendered the hooks without executing them.

### Migrating Legacy APIs

26.03.1 includes Trainer 2.2.0 and legacy Training Operator 1.9.2. Their coexistence does not reveal any team's migration progress. PyTorchJob/TFJob/MPIJob and TrainJob are different APIs and are not automatically converted.

The [pinned official migration document](https://github.com/kubeflow/trainer/blob/v2.3.0/docs/operator-guides/migration.md) provides a PyTorchJob-to-default-Torch-runtime example and SDK direction, not an exhaustive mapping for every framework/field. Compare replica roles, launch commands, environment, retries, storage, scheduling/networking and checkpoint recovery for each workload.

## TrainJob and Runtime Responsibilities

`TrainingRuntime` is namespaced; `ClusterTrainingRuntime` is cluster-scoped. Both contain execution templates and ML policies. `TrainJob.runtimeRef` selects kind/name, while trainer fields can configure command/arguments, training Pod count and resources per Pod. Permissions and allowed overrides need separate management.

The default `torch-distributed` runtime has `mlPolicy.numNodes: 1`, `torch: {}` and a JobSet template. In 2.2.0 it references `pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime`. Record image/runtime revisions and verify architecture, drivers and communication libraries; this review did not execute the image or train a model.

Here numNodes represents training Pod count, not a one-to-one EC2 instance count. Calculate processes, GPUs per Pod and placement of multiple Pods separately.

## Distributed Training Mechanics on Kubernetes

JobSet and runtimes compose Jobs/Pods and use Service/DNS plus rank/rendezvous configuration for process discovery. A headless Service alone does not preserve process state or IPs; stable Pod naming, hostname/subdomain and network conditions still matter.

**Installing Trainer does not automatically enable gang scheduling.** The 2.2.0 default Torch runtime has no podGroupPolicy. Coscheduling/Volcano policies, CRDs and scheduler integration must be installed/configured for those PodGroup paths. Kueue admission is also distinct from actual Pod scheduling.

Fixed-size synchronous training needs all required processes ready for communication, but nodes need not be created at the same instant. Sequential provisioning can succeed within rendezvous timeouts; supported elastic workloads have different rules. Gang admission reduces partial allocation but cannot solve every EC2 shortage or application deadlock. Coordinate [Karpenter](../../autoscaling/02-karpenter.md) capacity with JobSet, scheduler and framework timeouts/retries.

![Trainer composes TrainJob and runtime into JobSet, with optional PodGroup scheduling and opt-in runtime-status reporting shown separately.](../../.gitbook/assets/en-ai-ml-kubeflow-05-training-operator-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-05-training-operator-0.html)

## Cross-Reference: Katib and TrainJob

Katib 0.19.0 can use TrainJob in a configured Trial template. Match trialResources registration, runtime, success/failure conditions, primary Pods/containers and metric collection. Katib metrics reporting is separate from Trainer's opt-in status server. A successful TrainJob does not automatically deploy a model to KServe.

## Validation and Sources

Official OCI Trainer Helm charts 2.2.0 and 2.3.0 were pulled and rendered with default runtimes enabled; CRD/runtime schemas were inspected. API admission/CEL, actual upgrades, JobSet creation, distributed/GPU training and status-server reporting were not executed.

- [2.2.0 TrainJob API](https://github.com/kubeflow/trainer/blob/v2.2.0/pkg/apis/trainer/v1alpha1/trainjob_types.go)
- [TrainJobStatus default feature gate](https://github.com/kubeflow/trainer/blob/v2.2.0/pkg/features/features.go)
- [Conditional Coscheduling PodGroup creation](https://github.com/kubeflow/trainer/blob/v2.2.0/pkg/runtime/framework/plugins/coscheduling/coscheduling.go)
- [Default Torch runtime](https://github.com/kubeflow/trainer/blob/v2.2.0/manifests/base/runtimes/torch_distributed.yaml)

## Next Steps

With the shift from framework-specific CRDs to the unified `TrainJob`/runtime model in place, [Part 6: KServe — Model Serving on Kubernetes](./06-kserve.md) covers what happens to a model once training against a `TrainJob` completes: serving it for inference.

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/kubeflow/05-training-operator-quiz.md).
