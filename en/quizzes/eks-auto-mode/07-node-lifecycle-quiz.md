# EKS Auto Mode Node Lifecycle Quiz

> **Related Document**: [Node Lifecycle](../../eks-auto-mode/07-node-lifecycle.md)
> **Last Updated**: September 12, 2026

## Multiple Choice Questions

### 1. Which NodePool field specifies age-based expiration for newly created NodeClaims?

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>Show Answer</summary>

**Answer: C) `expireAfter`**

**Explanation:**
The field is under `spec.template.spec`. Auto Mode documents a 336h default and applies a 24h NodeClaim termination grace when omitted on the pool. The maximum managed-instance lifetime is 21 days, not a minimum uptime guarantee. Updating the template does not overwrite existing claims. The former development 336h, staging 168h, production 72–168h and security 24–48h values are unverified policy examples, not required compliance intervals.
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 2. What is true when an Auto Mode NodeClaim expires?

- A) It always disappears instantaneously
- B) Termination/draining starts without a guaranteed pre-ready replacement
- C) Only a notification is sent
- D) The same instance is rebooted

<details>
<summary>Show Answer</summary>

**Answer: B) Termination/draining starts without a guaranteed pre-ready replacement**

**Explanation:**
Expiration is a forceful trigger and is not rate-limited by NodePool disruption budgets. The controller prevents ordinary new scheduling and attempts draining/cleanup. PDBs and Pod annotations can affect eviction, but termination grace and the AWS lifetime maximum bound protection. A `nodes: 10%` budget therefore does not make expirations a controlled 10% rolling update. Replacement capacity and application readiness require their own evidence.

</details>

### 3. Which OS selection statement is correct for EKS Auto Mode?

- A) Choose AL2023 with `amiFamily`
- B) AWS manages Bottlerocket variants; NodeClass is not an AMI-family selector
- C) Select a custom AMI with `amiSelectorTerms`
- D) GPU nodes must use customer-managed AL2023

<details>
<summary>Show Answer</summary>

**Answer: B) AWS manages Bottlerocket variants; NodeClass is not an AMI-family selector**

**Explanation:**
Auto Mode does not expose those custom-AMI interfaces or SSH/SSM access. Its managed images also support accelerated workloads. The earlier quiz's AL2023 20–40s versus Bottlerocket 15–25s, and source's 40–60s versus 20–30s/20–40s, have no verified measurement provenance; they do not establish a universal boot-speed ranking. General-purpose OS comparisons are separate from Auto Mode's managed interface.

</details>

### 4. What can happen when an Auto Mode managed-image update makes existing NodeClaims drifted?

- A) Every instance is patched in place immediately
- B) Eligible claims can be replaced under applicable graceful-disruption controls
- C) Nothing until an arbitrary Node tag changes
- D) All nodes must be deleted simultaneously

<details>
<summary>Show Answer</summary>

**Answer: B) Eligible claims can be replaced under applicable graceful-disruption controls**

**Explanation:**
Inspect `Drifted` conditions, reasons and current policy. A 10% budget rounds up and combines with other active limits; it does not mean one-at-a-time replacement. Scheduling/PDB constraints and grace semantics also matter. Not every NodePool change induces drift: compatible requirement widening or behavioral weight/limit/disruption changes are different from desired-state drift. `amiFamily` is not an Auto Mode field.

</details>

### 5. What trade-off can a shorter expiration policy introduce?

- A) Guaranteed cost reduction
- B) More rescheduling, warm-up/recovery work and possible availability impact
- C) A guarantee of more CVEs
- D) Guaranteed stability

<details>
<summary>Show Answer</summary>

**Answer: B) More rescheduling, warm-up/recovery work and possible availability impact**

**Explanation:**
Frequent replacement can make a managed-image rollout more frequent, but does not prove the required patch is available or fix every workload vulnerability. It can add capacity, image-pull, checkpoint and recovery costs. It does not itself increase an EC2 Spot instance's interruption probability. Assess application recovery and node grace separately; a NodePool budget cannot rate-limit expiration.
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 6. How should consolidation and expiration be understood when their conditions overlap?

- A) Consolidation always wins
- B) Expiration always waits for drift and then consolidation
- C) Graceful methods and forceful expiration have distinct control paths, without a universal total order
- D) An administrator must manually choose every action

<details>
<summary>Show Answer</summary>

**Answer: C) Graceful methods and forceful expiration have distinct control paths, without a universal total order**

**Explanation:**
The graceful controller evaluates drift before consolidation; expiration is a separate forceful path. There is no documented global `drift > expiration > consolidation` or first-condition-wins guarantee. A five-day-old node may consolidate before a seven-day expiry. An eight-day-old expired claim may start termination even if it is well utilized.

</details>

### 7. Which is the sound starting point for urgent node patch remediation?

- A) Set `expireAfter` to zero on every pool
- B) Invent a drift annotation
- C) Verify the managed fix, identify affected claims and use a health-checked single-resource procedure
- D) Bulk-delete a pool and call it sequential replacement

<details>
<summary>Show Answer</summary>

**Answer: C) Verify the managed fix, identify affected claims and use a health-checked single-resource procedure**

**Explanation:**
Confirm the managed image/fix is available, then inspect a single NodeClaim UID, node mapping, PDBs, durable state and spare/obtainable capacity in the reviewed context. Use managed drift if suitable; review manual replacement separately and recheck health/image evidence before the next node. A cosmetic `SecurityPatch` tag is not a guaranteed patch trigger, and deleting all labeled nodes is not a rolling update. `--delete-emptydir-data` can discard local data.

The related guide establishes `KUBE_CONTEXT`; the command below only gathers evidence.

```bash
: "${NODECLAIM_NAME:?Select one NodeClaim for review}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaim "$NODECLAIM_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
       pool:.metadata.labels["karpenter.sh/nodepool"],imageID:.status.imageID,
       expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
       conditions:[.status.conditions[]?|{type,status,reason}]}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[]|{namespace:.metadata.namespace,name:.metadata.name,
       observedGeneration:.status.observedGeneration,generation:.metadata.generation,
       currentHealthy:.status.currentHealthy,desiredHealthy:.status.desiredHealthy,
       disruptionsAllowed:.status.disruptionsAllowed}]'
```


</details>

### 8. Does upstream `expireAfter: Never` provide indefinite retention for an Auto Mode node?

- A) Yes, including all maintenance and interruption
- B) No; Auto Mode's 21-day managed-instance maximum still applies
- C) Yes, if the Pod has a PDB
- D) Yes, for every stateful workload

<details>
<summary>Show Answer</summary>

**Answer: B) No; Auto Mode's 21-day managed-instance maximum still applies**

**Explanation:**
Upstream syntax is not permission to override Auto Mode's service lifetime. Do not recommend `Never` as a way to run an Auto Mode database or long job on one instance forever, or guess that a particular admission response is guaranteed without testing it. Plan checkpointing, external durable storage and recovery. Drift, interruption and other lifecycle actions can happen earlier.

</details>

## References

- [Auto Mode NodePool defaults](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode maximum lifetime](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Disruption and drift](https://karpenter.sh/v1.14/concepts/disruption/)
