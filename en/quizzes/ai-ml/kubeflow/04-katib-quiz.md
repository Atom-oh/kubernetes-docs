# Part 4: Katib — Hyperparameter Tuning and AutoML Quiz

This quiz tests your understanding of Katib's Experiment/Trial/Suggestion architecture, the search algorithms it supports, early stopping, metrics collection, and the resource-pressure considerations of running Katib on EKS.

## Multiple Choice Questions

1. In Katib's architecture, what is the relationship between an Experiment, a Trial, and a Suggestion?
   - A) They are three interchangeable names for the same CRD
   - B) A Suggestion owns many Experiments, each of which owns one Trial
   - C) An Experiment owns many Trials, each running a specific hyperparameter combination, while a Suggestion service proposes those combinations
   - D) A Trial owns many Experiments, coordinated by a single global Suggestion

<details>
<summary>Show Answer</summary>

**Answer: C) An Experiment owns many Trials, each running a specific hyperparameter combination, while a Suggestion service proposes those combinations**

**Explanation:**
An Experiment object describes tuning; maxTrialCount is a completion-count criterion, not a successful-training count or immutable spending cap. Each Trial is a single training run with one specific hyperparameter combination. The Suggestion service implements an algorithm; how it uses prior observations depends on that algorithm.
</details>

2. Which search algorithm builds a probabilistic model of how hyperparameters map to the objective metric, using that model to pick the next most promising point(s) to try?
   - A) Grid search
   - B) Random search
   - C) Bayesian optimization
   - D) Hyperband

<details>
<summary>Show Answer</summary>

**Answer: C) Bayesian optimization**

**Explanation:**
Bayesian optimization builds a probabilistic model relating hyperparameters to the objective and uses it to select the next candidate(s) most likely to improve on the best result seen so far. Random search samples independently with no memory of past trials; grid search exhaustively enumerates discrete combinations; Hyperband allocates a small budget broadly and reallocates it to early survivors.
</details>

3. What tradeoff does Hyperband make compared to giving every configuration a full, equal training budget?
   - A) It trains every configuration to full completion before comparing them
   - B) It gives many configurations a small budget, discards the worst performers early, and reallocates freed budget to the survivors
   - C) It only ever tries a single configuration at a time
   - D) It ignores intermediate performance entirely and picks configurations at random

<details>
<summary>Show Answer</summary>

**Answer: B) It gives many configurations a small budget, discards the worst performers early, and reallocates freed budget to the survivors**

**Explanation:**
Hyperband trades exhaustive per-configuration information for early pruning: it runs many configurations cheaply at first, aggressively discards the ones that look weakest, and gives the freed-up resource budget to the configurations that are still promising.
</details>

4. In an Experiment's spec, what does the `objective` field define?
   - A) The container image used to run each Trial
   - B) The metric to optimize and whether to maximize or minimize it
   - C) The number of Trials that can run in parallel
   - D) The search algorithm's internal hyperparameters

<details>
<summary>Show Answer</summary>

**Answer: B) The metric to optimize and whether to maximize or minimize it**

**Explanation:**
`objective` names the metric (e.g., accuracy or loss) and the goal (maximize or minimize), and can optionally include a target value that allows the Experiment to stop early once reached. The search space is defined separately, under `parameters`, and how each Trial's job is run is defined under `trialTemplate`.
</details>

5. What did this review verify about Katib 0.19.0 medianstop threshold calculation?
   - A) It stops the Experiment entirely once the median Trial finishes
   - B) It stores successful-Trial averages over the first start_step observations, then calculates their arithmetic mean
   - C) It only allows exactly half of all proposed Trials to run
   - D) It selects the median hyperparameter value as the final answer

<details>
<summary>Show Answer</summary>

**Answer: B) It stores successful-Trial averages over the first start_step observations, then calculates their arithmetic mean**

**Explanation:**
The official guide describes a median rule, but 0.19.0 calculates an arithmetic mean. Successful-Trial averages [1, 2, 100] yield about 34.333 in the unchanged function, not statistical median 2. Defaults are min_trials_required=3 and start_step=4; collector/timestamp requirements also apply.
</details>

6. How does Katib typically get the objective metric value out of a running Trial's training container?
   - A) The training container must call a Katib API directly from inside its code
   - B) Configured pull collectors gather metrics, or Push mode report_metrics() sends them to DB manager
   - C) Katib pauses the container and inspects its memory directly
   - D) The Kubernetes scheduler extracts the metric automatically from resource usage

<details>
<summary>Show Answer</summary>

**Answer: B) Configured pull collectors gather metrics, or Push mode report_metrics() sends them to DB manager**

**Explanation:**
StdOut/File/TensorFlowEvent and Custom collectors coexist with Push mode. Arbitrary HTTP scraping is not a built-in default. Pull injection requires namespace labeling, webhook and target Pod/container configuration. Job success alone does not prove metric collection.
</details>

7. Why does a high `parallelTrialCount` create sharper resource pressure on an EKS cluster than the same `maxTrialCount` run at low concurrency?
   - A) `parallelTrialCount` has no effect on how many pods are created
   - B) High parallelism means many Trials (and their resource requests, e.g. GPUs) hit the cluster at the same time rather than spread out, producing a short, sharp demand spike
   - C) EKS caps `parallelTrialCount` at 1 by default
   - D) Parallel Trials always run on the same node, so there is no additional demand

<details>
<summary>Show Answer</summary>

**Answer: B) High parallelism means many Trials (and their resource requests, e.g. GPUs) hit the cluster at the same time rather than spread out, producing a short, sharp demand spike**

**Explanation:**
Each concurrent Trial is a full training job. Demand is concurrency × Pods per Trial × resources per Pod, plus collector and service overhead — which can spike demand sharply even for an Experiment whose total `maxTrialCount` looks modest.
</details>

8. On EKS, what is a likely explanation if newly created Trial pods sit pending for a while right after a high-`parallelTrialCount` Experiment starts?
   - A) The Suggestion service has crashed
   - B) It may be waiting for capacity; confirm through Pod events, NodePool conditions, quotas, EC2 capacity and bootstrap state
   - C) Katib always pauses new Trials for a fixed warm-up period
   - D) The metrics-collector sidecar is blocking pod startup

<details>
<summary>Show Answer</summary>

**Answer: B) It may be waiting for capacity; confirm through Pod events, NodePool conditions, quotas, EC2 capacity and bootstrap state**

**Explanation:**
Pending alone does not prove Karpenter is successfully provisioning. Affinity, taints, volumes, quotas, capacity limits and bootstrap failures can also explain it. Use observed events and controller state.
</details>

## Short Answer Questions

9. Name two of the search algorithms Katib supports and, in one sentence each, describe what problem each is best suited for.

<details>
<summary>Show Answer</summary>

**Answer:** Any two of: random search (cheap baseline for large/poorly understood search spaces), grid search (exhaustive coverage of small, low-dimensional discrete spaces), Bayesian optimization (reducing total Trials needed when each Trial is expensive, via a probabilistic model of the objective), Hyperband (pruning underperforming configurations early using a cheap, informative early signal), or CMA-ES (covariance-adaptation evolution), or PBT (a separate population-based training strategy requiring checkpoint sharing).

**Explanation:**
Each algorithm trades off exploration cost against search efficiency differently, and the right choice depends on how expensive a single Trial is and how much structure the search space has.
</details>

10. What is the difference between what Hyperband does and what early stopping (e.g., the median-stopping rule) does, given that both aim to avoid wasting compute?

<details>
<summary>Show Answer</summary>

**Answer:** Hyperband is a search strategy that decides up front how much resource budget to give each configuration; early stopping is a runtime check applied to a Trial already in progress, based on how it's performing relative to its peers at that point in training.

**Explanation:**
The two operate at different levels: Hyperband's pruning is part of the search algorithm's overall budget-allocation strategy, while early stopping is a per-Trial decision made while that Trial is running, subject to compatible collector/log configuration, not automatic support for every combination.
</details>

## Hands-on / Applied Question

11. You are configuring an Experiment where each Trial requests one GPU, and the cluster has a Karpenter NodePool for GPU instances that typically takes several minutes to provision new capacity. You set `maxTrialCount: 60` and are deciding on `parallelTrialCount`. Explain, in a few sentences, the tradeoff between setting it high (e.g., 20) versus low (e.g., 4) in this environment.

<details>
<summary>Show Answer</summary>

**Answer:** A high `parallelTrialCount` (e.g., 20) can process Trials in fewer rounds when capacity is available but produces a sharp burst of 20 simultaneous GPU requests, which can outrun how fast Karpenter can provision GPU nodes — leaving early Trials pending rather than training, and potentially spiking shared cluster capacity if other workloads are competing for the same GPU NodePool. A low `parallelTrialCount` (e.g., 4) spreads the same 60 Trials over more rounds, giving Karpenter time to provision incrementally and reducing the risk of a capacity spike, potentially increasing elapsed time. Actual time and cost depend on capacity, durations, failures, stopping and node reclamation.

**Explanation:**
`parallelTrialCount` and `maxTrialCount` need to be tuned together with cluster autoscaling behavior in mind, not treated as independent settings — especially when Trials request scarce or slow-to-provision resources like GPUs.
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/04-katib.md)
