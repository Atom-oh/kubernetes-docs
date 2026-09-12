# Part 4: Katib — Hyperparameter Tuning and AutoML

> **Supported Versions**: Katib 0.19.0, Kubeflow Community Distribution 26.03.1
> **Last Updated**: September 12, 2026

## Lab Environment Setup

Use Katib 0.19.0 controllers, DB manager/storage, required Suggestion images and namespace permissions to create Experiments. Distinguish full-platform Profile access from standalone installation. GPU capacity is optional; Karpenter is one provisioner.

## What Katib Is

Katib supports hyperparameter optimization (HPO) and neural architecture search (NAS). An `Experiment` defines objective/search space/algorithm/Trial template; `Suggestion` and its algorithm service propose candidates; a `Trial` manages one candidate execution. How previous results influence suggestions depends on the algorithm.

These are **custom resource objects** defined by CRDs, not new CRD definitions installed for every run. The Trial controller creates the configured job resource; that job's controller and Kubernetes handle Pod creation and node placement. The 0.19.0 default trialResources includes `TrainJob.v1alpha1.trainer.kubeflow.org`, Kubernetes Job and legacy training-job kinds. Match the actual Trainer API/runtime, permissions, success/failure conditions and collector target Pods/containers; compatibility is not automatic.

Inspect state with `kubectl get experiments.kubeflow.org` and `kubectl get trials.kubeflow.org`. These are distinct from KFP's similarly named Experiment API.

## Search Algorithms

Algorithm names must match installed KatibConfig entries and Suggestion images. The 0.19.0 default configuration includes:

| Name | Strategy and constraints |
| --- | --- |
| `random` | Sampling the configured space/distributions; not necessarily uniform for every parameter |
| `grid` | Finite combinations; goals, failures or Trial limits can prevent exhaustive execution |
| `bayesianoptimization`, `tpe`, `multivariate-tpe` | Different model-based candidate strategies; fewer Trials or an optimum is not guaranteed |
| `hyperband` | Resource budgets and successive halving; training code must honor the budget parameter |
| `cmaes`, `sobol` | Covariance-adaptation evolution and low-discrepancy sampling respectively, not the same algorithm |
| `pbt` | Population-based training with checkpoint-sharing requirements; distinct from CMA-ES |
| `enas`, `darts` | Architecture-search algorithms with their own templates/dependencies |

The PBT guide requires an RWX volume and `resumePolicy: FromVolume`. Changing an algorithm name does not make arbitrary training code compatible.

## Anatomy of an Experiment

| Field | Meaning |
| --- | --- |
| `objective` | Metric name, maximize/minimize and optional target |
| `parameters` | double/int/discrete/categorical spaces, ranges/lists/distributions |
| `algorithm` | Installed Suggestion algorithm and settings |
| `trialTemplate` | trialParameters substitution and job spec, primary container/Pod selection, success/failure conditions |
| `parallelTrialCount` | Concurrently processed Trials, not Pod/GPU/EC2 count |
| `maxTrialCount` | Completion-count stopping criterion, not successful-training count or immutable lifetime cost cap |
| `maxFailedTrialCount` | Failure threshold including failed and metrics-unavailable Trials |
| `metricsCollectorSpec` / `earlyStopping` | Metric reporting and separate early-stopping configuration |

Goal attainment, completed-count limit or exhausted suggestions can end successfully; failure thresholds or Suggestion errors can fail the Experiment. Completion status counts succeeded, failed, killed, early-stopped and metrics-unavailable Trials. Resume policy and spec changes also affect lifecycle, so do not treat maxTrialCount as an immutable lifetime creation or spending limit.

`Succeeded` is a control-loop outcome, not a model-quality certification. `status.currentOptimalTrial` describes the best collected observation; missing metrics can leave no usable best model.

## Early Stopping and the 0.19.0 medianstop Implementation

Early stopping can terminate an in-progress Trial. The official guide requires `StdOut`/`File` collectors and timestamped logs. Do not assume equivalent support for every collector or arbitrary training loop. Defaults are `min_trials_required=3` and `start_step=4`.

**Distinguish the documented rule from this release's implementation.** The official guide describes a median of completed-Trial running averages. In v0.19.0, however, `get_median_value` stores each successful Trial's average over its first start_step observations and returns the **arithmetic mean** of those stored averages. Executing the unchanged function locally with `[1, 2, 100]` produced about 34.333, not the statistical median 2. The algorithm name does not guarantee a median calculation in this release.

Hyperband's budget allocation and the early-stopping service are separate configuration/execution paths. Validate the risk of discarding promising candidates and the effects of metric format, reporting frequency and budget parameters.

## How an Experiment Runs, End to End

![Experiment and Suggestion generate candidates; Trial jobs report metrics through DB manager. Goals, completion counts and failure conditions determine termination.](../../.gitbook/assets/en-ai-ml-kubeflow-04-katib-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-04-katib-0.html)

The Experiment controller requests candidates through Suggestion resources and creates Trial objects. Trial and training-job controllers drive execution, while metrics are reported through DB manager. Algorithms consume results according to their implementation. Inspect termination conditions and remaining child jobs; optimal hyperparameters are not themselves a deployable model artifact.

## Metrics Collection

| Mode | Configuration and constraints |
| --- | --- |
| `StdOut` | Default pull mode; extracts metrics from the primary container's log format |
| `File` | TEXT or line-delimited JSON; configure path and filters |
| `TensorFlowEvent` | Event-file directory, including compatible TensorBoard writers |
| `Custom` | User-supplied collector implementation; arbitrary HTTP scraping is not a built-in default |
| `Push` | Training code calls SDK `report_metrics()` to DB manager; a collector sidecar is not always required |

Pull injection needs namespace label `katib.kubeflow.org/metrics-collector-injection: enabled`, a working webhook and correct target Pod/container selection. Distributed training needs an explicit reporting-rank policy. Validate metric names, numeric format, timestamps, connectivity and policies. A successful training job does not guarantee metrics were collected.

## Capacity and Cost on EKS

Demand is roughly **concurrent Trials × Pods per Trial × resources per Pod**, plus collector/Suggestion/database overhead. If each Trial has two Pods requesting four GPUs each, parallelTrialCount 8 can request 64 GPUs, not eight.

For Pending Pods inspect events, scheduling constraints, quotas, NodePool/EC2 capacity, drivers and bootstrap state. Karpenter cannot always supply capacity, and higher concurrency does not guarantee shorter total runtime. Early stopping can release Pod resources while EC2 charges continue for retained nodes.

Configure total-Trial criteria, concurrency, job retries/distributed size, deadlines and data retention together. Verify metric collection and termination with a small CPU workload before increasing GPU scale.

## Validation and Sources

The v0.19.0 configuration, controller/API, collector paths and medianstop source were inspected. The unchanged medianstop function was executed locally with preloaded successful-Trial history and network calls blocked. No Experiment or GPU workload was run.

- [0.19.0 default KatibConfig](https://github.com/kubeflow/katib/blob/v0.19.0/manifests/v1beta1/installs/katib-standalone/katib-config.yaml)
- [Experiment status decisions](https://github.com/kubeflow/katib/blob/v0.19.0/pkg/controller.v1beta1/experiment/util/status_util.go)
- [medianstop implementation](https://github.com/kubeflow/katib/blob/v0.19.0/pkg/earlystopping/v1beta1/medianstop/service.py)
- [Metrics collector guide](https://www.kubeflow.org/docs/components/katib/user-guides/metrics-collector/)
- [Early stopping guide](https://www.kubeflow.org/docs/components/katib/user-guides/early-stopping/)

## Next Steps

Continue with distributed-training APIs and runtimes in [Part 5: Trainer](05-training-operator.md).

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/kubeflow/04-katib-quiz.md).
