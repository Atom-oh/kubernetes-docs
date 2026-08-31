# Part 4: Katib — Hyperparameter Tuning and AutoML

> **Supported Versions**: Katib 0.19.0, Kubeflow Community Distribution 26.03
> **Last Updated**: August 19, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl v1.34 or later, pointed at a cluster with Kubeflow installed (see Part 1)
* Access to a user Profile (namespace) in the Kubeflow Central Dashboard, to submit Experiments
* A GPU-enabled `NodePool`/`EC2NodeClass` pair configured via [Karpenter](../../autoscaling/02-karpenter.md), if you plan to run GPU-backed Trials
* A working training job template to reference from `trialTemplate` (e.g. a `TrainJob`/`ClusterTrainingRuntime` pair from Part 5, or a plain Kubernetes `Job`)

## What Katib Is

Earlier parts of this series covered the Kubeflow notebook and pipeline layers. This document covers **Katib**, Kubeflow's Kubernetes-native hyperparameter tuning and AutoML component. Katib turns "which learning rate, batch size, and network depth should I use?" into a declarative, cluster-scheduled search rather than a manual loop of edit-run-inspect, and it does so by composing ordinary Kubernetes objects — Custom Resources, pods, and services — rather than a bespoke scheduler bolted onto the side of the cluster.

Katib automates hyperparameter optimization (HPO) and neural architecture search by running many training jobs in parallel, each with a different combination of hyperparameters, and using the results to decide which combinations to try next. It is built around three cooperating pieces:

* **Experiment** — a CRD describing one tuning run: the objective to optimize, the search space of hyperparameters, the search algorithm to use, and a template describing how to run one training job.
* **Trial** — a CRD, created by the Katib controller, representing a single training run with one specific hyperparameter combination. An Experiment with `maxTrialCount: 50` will, over its lifetime, spawn up to 50 Trials.
* **Suggestion** — a service (also backed by a CRD) that implements the search algorithm. It receives results from completed and in-progress Trials and proposes the next hyperparameter set(s) to try.

The relationship is hierarchical: one Experiment owns many Trials, and each Trial owns the actual training job (a Kubernetes `Job`, or a training-job resource such as a `TrainJob` when integrated with Kubeflow Trainer — see Part 5) that Kubernetes schedules and runs like any other workload. Because everything is a CRD, `kubectl get experiments`, `kubectl get trials`, and `kubectl describe` on any of them behave exactly as they would for a Deployment or Job — there is no separate CLI or UI required to inspect state, though the Katib UI (part of the Kubeflow Central Dashboard) gives a visual view of trial progress and metric curves.

## Search Algorithms

Katib ships with a pluggable set of search algorithms, exposed through the Suggestion service. Each algorithm answers the same question — "given results so far, what should the next Trial(s) try?" — with a different strategy and a different tradeoff between exploration cost and search efficiency.

| Algorithm | Good for | Conceptual behavior |
|---|---|---|
| **Random search** | A cheap baseline, or a very large/poorly understood search space | Samples hyperparameter combinations independently and uniformly at random from the defined space. No memory of past trials. |
| **Grid search** | Small, low-dimensional search spaces where exhaustive coverage is affordable | Enumerates every combination of the discrete values provided for each hyperparameter. Guarantees full coverage but scales combinatorially with the number of parameters. |
| **Bayesian optimization** | Expensive-to-train models where each Trial's cost matters and informed sampling pays off | Builds a probabilistic model of how hyperparameters map to the objective metric, and uses that model to pick the next point(s) most likely to improve on the best result seen so far. Converges in fewer trials than random search for many workloads, at the cost of some sequential dependency between suggestions. |
| **Hyperband** | Workloads where "does this look promising early?" is a cheap, informative signal (e.g., loss curves after a few epochs) | Runs many configurations with a small resource budget, aggressively discards the worst performers, and reallocates the freed budget to the survivors for longer runs. Trades exhaustive per-config information for early pruning. |
| **CMA-ES and other advanced strategies** | Continuous, higher-dimensional search spaces, or workloads that benefit from population-style search (e.g., population-based training) | Evolve a population or distribution of candidate configurations over successive generations, adapting the sampling distribution based on which candidates performed well. Conceptually closer to evolutionary/optimization algorithms than to simple sampling. |

Which algorithm to choose is a function of how expensive each Trial is and how much structure the search space has. Random search is a reasonable default to establish a baseline; Bayesian optimization and Hyperband are the more common choices once training a single Trial is costly enough that reducing the total number of Trials materially matters.

## Anatomy of an Experiment

An Experiment's spec has three parts that matter most for understanding how a tuning run behaves:

* **`objective`** — names the metric to optimize (e.g., `accuracy` or `loss`) and the goal (`maximize` or `minimize`), along with an optional target value that, if reached, can be used to stop the Experiment early as "good enough."
* **`parameters`** — the search space: one entry per hyperparameter, each with a name, a type, and either a continuous range (min/max, useful for something like a learning rate) or a discrete list of values (useful for something like an optimizer choice or a categorical architecture flag).
* **`trialTemplate`** — describes how each Trial's actual training job gets built: a template for the underlying job spec, with placeholders that get substituted with the specific hyperparameter values the Suggestion service proposed for that Trial. In current Kubeflow deployments this template commonly points at a training job resource managed by **Kubeflow Trainer** (covered in depth in Part 5) — Katib's job here is to decide *what values* to inject, not to re-implement how a distributed training job runs.

Two additional Experiment-level fields shape how the search is executed rather than what it searches:

* **`parallelTrialCount`** — how many Trials may run concurrently.
* **`maxTrialCount`** — the total number of Trials the Experiment will run across its lifetime before stopping (regardless of whether a target objective value was hit).

## Early Stopping

Not every Trial needs to run to completion to know it isn't going to win. Katib supports **early stopping**, where a Trial that is clearly underperforming partway through training is terminated before it consumes its full resource allocation. A commonly used approach is the **median-stopping rule**: at a given point in training, a Trial's intermediate objective value is compared against the median of other Trials' intermediate values at the same point; if it falls meaningfully short, the Trial is stopped rather than allowed to run to completion for a result that's already unlikely to be competitive.

Early stopping and algorithms like Hyperband solve a related problem — not wasting compute on training that isn't going anywhere — but they operate at different levels: Hyperband is a *search strategy* that decides how much budget to give each configuration up front, while early stopping is a *runtime check* applied to a Trial that's already in flight based on how it's progressing relative to its peers.

## How an Experiment Runs, End to End

![Flowchart of the Katib hyperparameter tuning loop: an Experiment CRD triggers the Katib controller to create a Suggestion service, which proposes hyperparameter sets for parallel Trial training jobs; a metrics-collector sidecar reports each Trial's objective metric back to the Suggestion service, which either proposes another round or, once maxTrialCount or the target objective is reached, marks the Experiment Succeeded and records the best Trial's hyperparameters on its status.](../../../assets/diagrams/rendered/en-ai-ml-kubeflow-04-katib-0.svg)

The loop works like this: the Katib controller reconciles the Experiment and starts a Suggestion service for the requested algorithm. The Suggestion service proposes one or more hyperparameter combinations, bounded by `parallelTrialCount`. The controller creates a Trial CRD, and its underlying training job, for each proposal. As Trials report results, those results feed back into the Suggestion service to inform the next round of proposals. The loop continues until `maxTrialCount` is reached or the objective's target value is satisfied. Throughout, the Experiment's status is continuously updated with the best-performing Trial observed so far. Once the Experiment completes, that best Trial's hyperparameters and metric value are what's recorded as the final result.

## Metrics Collection

A training job doesn't natively know it's part of a Katib Experiment, so Katib needs a way to pull the objective metric back out of each Trial's pod. This is done via a **metrics-collector sidecar** injected into the Trial pod alongside the training container. The sidecar's job is to observe the training container's output — typically by tailing stdout/log files for a recognizable metric pattern, or by scraping a metrics endpoint the training code exposes — and report the parsed objective metric value back to Katib's metrics store.

This sidecar pattern is what keeps the training code itself mostly Katib-agnostic: a training script that already prints its accuracy or loss per epoch in a parseable format doesn't need to be rewritten to integrate with Katib — the collector does the extraction. It also means the choice of collection strategy (log parsing vs. endpoint scraping) matters for how reliably and how frequently Katib can observe intermediate progress, which in turn affects how well early stopping and Hyperband-style algorithms can act on that progress.

## Running Katib Experiments on EKS: Resource Pressure

Katib's concurrency knobs interact directly with cluster capacity in ways that matter more on EKS than they might in a fixed, over-provisioned on-prem cluster:

* **`parallelTrialCount` multiplies resource demand.** Each concurrent Trial is a full training job — if individual Trials request GPUs, a `parallelTrialCount` of 8 means 8 concurrent GPU requests hitting the cluster at once, not 8 requests spread out over time. An Experiment that looks modest on paper (`maxTrialCount: 100`) can still produce a sharp, short-lived spike in demand if `parallelTrialCount` is set high.
* **Cluster autoscaling has to keep pace.** On EKS, this pressure is typically absorbed by [Karpenter](../../autoscaling/02-karpenter.md) provisioning new GPU-backed nodes in response to the burst of pending Trial pods. Because GPU instance types often have longer provisioning lead times than general-purpose instances, a high `parallelTrialCount` can leave early Trials waiting on nodes rather than actually training — worth watching for in Trial pod events before assuming the Suggestion algorithm itself is slow.
* **Tune `parallelTrialCount` and `maxTrialCount` together, not independently.** A lower `parallelTrialCount` with a longer-running Experiment is often gentler on shared cluster capacity than a high `parallelTrialCount` finishing the same total Trials faster — the right balance depends on whether the cluster is dedicated to the tuning run or shared with other workloads.
* **Early stopping directly reduces wasted spend.** Because each terminated-early Trial frees its GPU allocation sooner, the median-stopping rule (see "Early Stopping" above) isn't just a search-efficiency optimization — on EKS it's also a direct lever on how much GPU-hour cost a tuning run accumulates before converging on a good hyperparameter set.

## Next Steps

Katib turns hyperparameter search into a Kubernetes-native control loop: an Experiment describes the objective and search space, a Suggestion service proposes hyperparameter combinations using a pluggable search algorithm, Trials run those combinations as ordinary training jobs, and a metrics-collector sidecar reports results back so the search can converge on a best configuration. On EKS, the practical lever is coordinating `parallelTrialCount`/`maxTrialCount` with autoscaling capacity — particularly for GPU-backed Trials — so a tuning run's concurrency doesn't outrun how fast the cluster can actually provision nodes for it.

Part 5 covers **Kubeflow Trainer**, the component that Katib's `trialTemplate` typically delegates to for actually running each Trial's distributed training job.

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/kubeflow/04-katib-quiz.md).
