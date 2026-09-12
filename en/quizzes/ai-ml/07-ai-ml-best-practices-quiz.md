# AI/ML Best Practices Quiz

15 questions on measurement, recovery and current APIs.

## 1. What does TTFT measure, and when is it unavailable?

<details>
<summary>Answer and explanation</summary>

Time from request to first nonempty output. First HTTP frame and token may differ; a nonstreaming response cannot measure actual TTFT/ITL. Specify tokenizer, failures and warmup boundaries.
</details>

## 2. Does combining startup optimizations always improve by 80–95%?

<details>
<summary>Answer and explanation</summary>

No. Measure image fetch/unpack, model download/loading, readiness and node preparation separately. Evaluate prefetch/lazy-loading costs, caches and full-weight reads instead of fixed savings.
</details>

## 3. How should GPUs for large distributed training be selected?

<details>
<summary>Answer and explanation</summary>

Check exact instance-size devices/memory, CPU/RAM/network, model state/activations, communication, prices and quotas. A family name does not fix GPU counts or prove a universally best choice.
</details>

## 4. Are EFA and placement groups always required?

<details>
<summary>Answer and explanation</summary>

EFA is a high-performance path for suitable workloads, not every DDP prerequisite. EFA communication requires the same AZ; cluster placement groups are recommended for performance. Verify drivers/plugins/security groups/interfaces.
</details>

## 5. Does a dataset over10TB always require FSx?

<details>
<summary>Answer and explanation</summary>

No single size cutoff decides. Compare I/O, concurrency, metadata, latency, durability, mount semantics and cost. Distinguish EFS/FSx/S3/instance store and current gp3 limits.
</details>

## 6. Can temperature alone establish throttling or hardware failure?

<details>
<summary>Answer and explanation</summary>

No. Check device-specific limits, clocks, power, throttle reasons and workload. DCGMFB_USED is MiB and XID_ERRORS is a last-code gauge; not every XID means hardware failure.
</details>

## 7. Are 120 seconds grace and a/drain call sufficient for Spot inference?

<details>
<summary>Answer and explanation</summary>

EC2 does not always guarantee 120 seconds and an arbitrary vLLM/drain API cannot be assumed. Test gateway readiness, SIGTERM, streams, retries, duplicates and cache reloads.
</details>

## 8. How is mean ITL calculated?

<details>
<summary>Answer and explanation</summary>

With actual token timestamps and at least two tokens:(last-first)/(tokens-1). Account for multi-token chunks and empty/single-token outputs; distinguish the tool-specific TPOT definition.
</details>

## 9. What does a saturation test demonstrate?

<details>
<summary>Answer and explanation</summary>

How throughput, latency, errors and goodput change with load. It does not alone prove a CPU/GPU/memory bottleneck. Distinguish arrival rate from concurrency and inspect clients, profiling and queues.
</details>

## 10. What input does SOCI 0.15 standalone use?

<details>
<summary>Answer and explanation</summary>

A local OCI image-layout directory/archive, not a generic docker-save tar. convert --standalone needs no containerd; actual lazy-start benefits require runtime/registry/workload validation.
</details>

## 11. How is a 09–17 UTC business-hour budget configured?

<details>
<summary>Answer and explanation</summary>

Use 0 9 * * 1-5 with 8h duration.0 9-17 * * 1-5 starts hourly and extends through01:00nextday. Budgets limit voluntary disruption, not Spot reclamation, failures or forceful expiration.
</details>

## 12. Does ESO refresh automatically issue credentials, reload apps and audit every read?

<details>
<summary>Answer and explanation</summary>

No. Distinguish provider rotation, Secret synchronization and app rereads. subPath/env values do not automatically refresh; CloudTrail does not log every local read. ESO 2.10 serves v1, not v1beta1.
</details>

## 13. How should GPU memory for a 30B FP16 model be estimated?

<details>
<summary>Answer and explanation</summary>

Weights alone are about 60GB; add KV, activations, workspace and communication. Four 24GB GPUs total 96GB but require sharding/peak-memory/throughput checks.13B FP16 exceeds 24GB; 70B FP16 exceeds 96GB.
</details>

## 14. Does high current vLLM KV-cache occupancy always reject requests?

<details>
<summary>Answer and explanation</summary>

Use vllm:kv_cache_usage_perc. Interpret occupancy with queues, preemption and memory state; immediate rejection is not guaranteed. Avoid obsolete gpu_cache_usage_perc and unverified hit-rate names.
</details>

## 15. Is a Karpenter placement group configured through a tag?

<details>
<summary>Answer and explanation</summary>

Version 1.14.1 uses EC2NodeClass.spec.placementGroupSelector name/id. An aws:ec2:placement-group tag is not the placement API. Verify AZ, capacity and networking and assess single-AZ recovery risk.
</details>

[Return to guide](../../ai-ml/07-ai-ml-best-practices.md)
