# Event capacity planning quiz

> **Related document**: [Event capacity planning](../../ops/12-event-capacity-planning.md)

## 1. How are multiple KEDA metrics used to determine the target?

- A) Sum every value
- B) HPA combines per-metric recommendations through a maximum and applies behavior/min/max
- C) Cron guarantees Ready Pods
- D) Metrics always define the upper ceiling

<details>
<summary>Show answer</summary>

**Answer: B**

Cron supplies a scheduled demand floor; maxReplicaCount and other constraints bound it. Verify actual readiness separately.

</details>

## 2. What matters when using a five-field Cron for a dated event?

- A) The year is implicit
- B) It deletes itself after one run
- C) It can recur next year and needs timezone/DST checks
- D) It always uses UTC only

<details>
<summary>Show answer</summary>

**Answer: C**

The example tests annual recurrence and boundaries. Remove or update the event configuration afterward.

</details>

## 3. Which configuration describes a static Karpenter NodePool?

- A) Higher weight alone creates static capacity
- B) Use replicas without weight and constrain limits.nodes
- C) Remove replicas at any time to switch to dynamic
- D) Scale operations are always blocked by every NodePool budget

<details>
<summary>Show answer</summary>

**Answer: B**

Distinguish static/dynamic modes. Static scale bypasses NodePool disruption budgets but respects PDBs.

</details>

## 4. What can happen if placeholder Deployment desired count remains unchanged after handoff?

- A) It always remains free of additional cost
- B) Recreated placeholders can cause additional nodes to be provisioned
- C) Karpenter automatically sets desired to zero
- D) The real application is always immediately Ready

<details>
<summary>Show answer</summary>

**Answer: B**

Validate retention/expiry, removal of placeholder demand and actual application readiness together.

</details>

## 5. Does adding 30% capacity guarantee survival of one AZ loss?

- A) Always
- B) Yes for On-Demand
- C) No; calculate placement and surviving throughput
- D) Yes whenever a PDB exists

<details>
<summary>Show answer</summary>

**Answer: C**

The 15/11-node example fails baseline peak after losing the larger AZ. Validate the input assumptions with measurements too.

</details>

## 6. What does a targeted Capacity Reservation mean?

- A) A security ACL restricted to one NodePool
- B) Instances explicitly target it and must satisfy matching criteria
- C) It automatically applies to every existing instance
- D) An On-Demand discount product

<details>
<summary>Show answer</summary>

**Answer: B**

Check IAM/sharing, AZ, type, platform, tenancy and actual consumption. It is distinct from an RI.

</details>

## 7. What happens when an immediate reservation is created at D-30 with only a future end_date?

- A) It waits free until the event
- B) end_date specifies a future start
- C) Unused active capacity can incur charges
- D) Occupied capacity is always charged twice

<details>
<summary>Show answer</summary>

**Answer: C**

Include the active interval in the cost model and avoid double-counting instances occupying reservations.

</details>

## 8. Which statement about CloudWatch scaler metricStat and minMetricValue is correct?

- A) metricStatType is the correct field
- B) minMetricValue is always activation threshold
- C) metricStat selects the statistic; minMetricValue is NoData fallback, overridden by ignoreNullValues=false
- D) Sum fits every rate gauge

<details>
<summary>Show answer</summary>

**Answer: C**

Distinguish deltas/counts from rates/cumulative counters and verify period, collection window and publishing delay.

</details>

## 9. How should a KEDA-managed workload be handled when metrics lag?

- A) Direct Deployment scaling always persists
- B) The HPA always has the Deployment name
- C) Review the ScaledObject floor within approved bounds and GitOps ownership
- D) Create an unbounded NodePool

<details>
<summary>Show answer</summary>

**Answer: C**

Direct HPA/Deployment changes can be overwritten at reconciliation. Record and restore original settings.

</details>

## 10. Which statement about preparation and cleanup is correct?

- A) Every image supports sh/echo and keeps its cache forever
- B) Deleting a NodePool after thirty minutes is always safe
- C) Validate app/cache constraints, baseline triggers and actual node/reservation cleanup
- D) Deleting a ScaledObject always restores original replicas

<details>
<summary>Show answer</summary>

**Answer: C**

Startup, GC, architecture and permissions vary. Cleanup must account for owning controllers and deletion lifecycle.

</details>
