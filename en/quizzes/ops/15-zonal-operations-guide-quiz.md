# Zonal Cluster Operations Quiz

> **Related Document**: [Zonal Cluster Operations](../../ops/15-zonal-operations-guide.md)

## Multiple Choice Questions

### 1. What is the eligibility window for Amazon EKS's native Kubernetes version rollback (GA'd July 2026)?

- A) 24 hours
- B) 7 days
- C) 30 days
- D) Unlimited

<details>
<summary>Show Answer</summary>

**Answer: B) 7 days**

**Explanation:**
EKS native rollback can revert one minor version at a time, within 7 days of the upgrade. Clusters created at the target version, more than 7 days elapsed, or clusters already re-upgraded are not eligible.

</details>

### 2. What mechanism is used to drain traffic out of a zone during a Zonal In-Place upgrade?

- A) `kubectl drain`
- B) Adjusting Target Group weight
- C) Waiting for DNS TTL to expire
- D) Recreating the cluster

<details>
<summary>Show Answer</summary>

**Answer: B) Adjusting Target Group weight**

**Explanation:**
Instead of touching anything inside the cluster, you adjust the weight of the Target Group bound via TargetGroupBinding to reduce or stop traffic to a given zone. For unplanned situations like an AZ outage, ARC Zonal Shift performs this role automatically.

</details>

### 3. What must be set on Kafka brokers to enable KIP-392 (Follower Fetching)?

- A) `auto.leader.rebalance.enable=true`
- B) `replica.selector.class=RackAwareReplicaSelector`
- C) `unclean.leader.election.enable=true`
- D) `min.insync.replicas=2`

<details>
<summary>Show Answer</summary>

**Answer: B) `replica.selector.class=RackAwareReplicaSelector`**

**Explanation:**
Brokers need `replica.selector.class` set to `RackAwareReplicaSelector` and a `broker.rack` (AZ ID) assigned. On the consumer side, the `client.rack` property must be set to the consumer's own AZ ID so fetches get redirected to a same-rack follower.

</details>

### 4. Which Valkey GLIDE `ReadFrom` strategy is recommended for workloads that are over 99% reads?

- A) `PRIMARY`
- B) `PREFER_REPLICA`
- C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`
- D) Random distribution

<details>
<summary>Show Answer</summary>

**Answer: C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`**

**Explanation:**
It prefers a same-AZ replica first, falls back to the same-AZ primary, and only reaches into other AZs as a last resort. For read-dominant workloads this is the recommended balance of cost savings and availability — HotelTrader cut inter-AZ transfer costs by 95% after adopting it.

</details>

### 5. Which statement about Amazon Aurora's default reader endpoint is correct?

- A) It automatically prioritizes replicas in the same AZ
- B) It is round-robin DNS with no AZ awareness
- C) It always routes to the primary
- D) It cannot be used without the AWS Advanced JDBC Wrapper

<details>
<summary>Show Answer</summary>

**Answer: B) It is round-robin DNS with no AZ awareness**

**Explanation:**
Aurora's default reader endpoint has no AZ affinity. You can work around this with per-AZ custom endpoints or the AWS Advanced JDBC Wrapper's `fastestResponse` strategy, but true AZ affinity itself remains an open feature request in the `aws-advanced-jdbc-wrapper` repository.

</details>

### 6. Which statement about how a pod can determine its own AZ is INCORRECT?

- A) It can look this up directly via EC2 IMDS
- B) A Kyverno mutating policy can copy a node label onto a pod annotation
- C) The Kubernetes Downward API injects the node's zone label into the pod by default
- D) An operator like Strimzi can provide rack-awareness as a built-in feature

<details>
<summary>Show Answer</summary>

**Answer: C) The Kubernetes Downward API injects the node's zone label into the pod by default**

**Explanation:**
The Downward API does not automatically inject a node's `topology.kubernetes.io/zone` label into a pod. That's why one of the other approaches — direct IMDS lookup, Kyverno-based admission-time label copying, or an operator's built-in support like Strimzi's — is needed.

</details>
