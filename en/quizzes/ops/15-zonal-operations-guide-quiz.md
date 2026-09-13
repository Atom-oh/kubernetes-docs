# Zonal Cluster Operations Quiz

> **Related Document**: [Zonal Cluster Operations](../../ops/15-zonal-operations-guide.md)

## Multiple Choice Questions

### 1. What does the seven-day EKS native rollback window mean?

- A) The time rollback must take
- B) Eligibility to initiate rollback after upgrade completion
- C) Maximum node lifetime
- D) The period for automatic add-on restoration

<details>
<summary>Show Answer</summary>

**Answer: B) Eligibility to initiate rollback after upgrade completion**

It is the window to initiate rollback to the immediately previous minor version. Creation version, support status, subsequent upgrades, and compatibility still matter. Auto Mode rolls back nodes first; add-ons, applications, and data changes are not automatically restored.

</details>

### 2. What must be checked after setting an NLB target-group weight to zero?

- A) All existing connections terminate immediately
- B) TargetGroupBinding moves to another cluster
- C) New-flow reduction and existing-flow draining separately
- D) ARC rewrites every other cluster’s weights automatically

<details>
<summary>Show Answer</summary>

**Answer: C) New-flow reduction and existing-flow draining separately**

Ordinary weight changes affect new flows, but the current NLB guide says weight zero also closes existing connections after a short period. Do not assume natural draining alone; test reconnection and retry behavior. Check NewFlowCount, ActiveFlowCount, and errors before changing nodes. TGB has no weight field, and EKS zonal shift does not automatically change weights across clusters.

</details>

### 3. Which combination configures Kafka KIP-392 correctly?

- A) broker.rack alone automatically configures all consumers
- B) RackAwareReplicaSelector, broker.rack, and matching consumer client.rack
- C) Only unclean.leader.election.enable=true
- D) Different AZ-name and AZ-ID strings are interchangeable

<details>
<summary>Show Answer</summary>

**Answer: B) RackAwareReplicaSelector, broker.rack, and matching consumer client.rack**

The complete replica.selector.class is org.apache.kafka.common.replica.RackAwareReplicaSelector. The Strimzi Kafka CR configures brokers; ordinary application consumers need separate configuration. Selection falls back to the leader when no suitable local replica exists.

</details>

### 4. What is the priority for GLIDE AZ_AFFINITY_REPLICAS_AND_PRIMARY?

- A) Primary only
- B) Local replicas → local primary → replicas or primary in other AZs
- C) Remote replicas only
- D) Always error when no local node exists

<details>
<summary>Show Answer</summary>

**Answer: B) Local replicas → local primary → replicas or primary in other AZs**

Server AZ metadata must match client_az. Evaluate tolerance for stale replica reads; read percentage alone is insufficient. HotelTrader’s reported improvements include request batching as well as AZ-aware routing.

</details>

### 5. Which statement about Aurora’s default reader endpoint is correct?

- A) It distributes each SQL query to a different replica
- B) It guarantees a reader in the same AZ
- C) It balances connections and can use the writer if no replicas exist
- D) It requires the JDBC Wrapper to connect

<details>
<summary>Show Answer</summary>

**Answer: C) It balances connections and can use the writer if no replicas exist**

It does not guarantee AZ preference. Per-AZ READER custom endpoints need membership and fallback management. JDBC fastestResponse uses response time, not a strict AZ constraint. Feature request #1139 was closed in 2025.

</details>

### 6. Which statement about discovering a pod’s AZ is incorrect?

- A) Ordinary Pod-create admission always knows the scheduler-selected node
- B) The AWS MSK Kyverno example handles Pod/binding requests
- C) spec.nodeName can be passed to an initialization component through the Downward API
- D) IMDS access depends on environment and security configuration

<details>
<summary>Show Answer</summary>

**Answer: A) Ordinary Pod-create admission always knows the scheduler-selected node**

A node normally has not been selected at Pod creation. Use binding-time injection or post-scheduling lookup. The Downward API does not directly query node labels, and Strimzi does not configure unrelated application consumers automatically.

</details>
