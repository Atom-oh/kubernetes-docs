# EKS upgrade operations quiz

> **Related document**: [EKS upgrades](../../ops/11-upgrade-operations.md)

## 1. How many intermediate minor versions can an EKS control-plane upgrade skip?

- A) Zero: advance to the next minor each time
- B) One
- C) Two
- D) Unlimited

<details>
<summary>Show answer</summary>

**Answer: A**

For example, 1.34→1.36 must pass through 1.35. Kubelet skew allowances are distinct from control-plane upgrade steps.

</details>

## 2. How should an absent CoreDNS Deployment in pure Auto Mode be interpreted?

- A) It always means DNS is broken
- B) Check the node system-service DNS and actual behavior
- C) Always install a self-managed Karpenter
- D) Delete CoreDNS Deployments from every cluster

<details>
<summary>Show answer</summary>

**Answer: B**

Mixed clusters must retain DNS Deployments and add-ons required by non-Auto nodes.

</details>

## 3. Which statement about Velero 1.18.2 restore create -o json is correct?

- A) It completes an actual restore
- B) It is entirely offline
- C) It does not create the object but can perform discovery/Backup reads
- D) It is valid only together with --dry-run

<details>
<summary>Show answer</summary>

**Answer: C**

restore create has no such --dry-run flag. Output-only review and actual isolated restore testing are different.

</details>

## 4. What should a preflight tool do on an API error or wrong kubecontext?

- A) Treat empty results as healthy
- B) Fail as unknown/mismatched context and investigate
- C) Automatically switch context and upgrade
- D) Delete PDBs

<details>
<summary>Show answer</summary>

**Answer: B**

Running alone does not establish Pod readiness; Deployment generation and rollout status also matter.

</details>

## 5. What is a basic eligibility condition for EKS native rollback?

- A) Any cluster newly created at its current version
- B) Meet eligibility, including initiation within seven days of upgrade completion to the previous minor
- C) Any previous version at any time
- D) An etcd backup bypasses every restriction

<details>
<summary>Show answer</summary>

**Answer: B**

Also check target support, EXTENDED policy, ACTIVE status and incompatible EKS features.

</details>

## 6. If cluster status is ACTIVE during Auto Mode node rollback, what does it mean?

- A) Rollback is fully complete
- B) The CP may still serve the current version; inspect the update ID
- C) Node rollback is impossible
- D) Immediately delete the previous cluster

<details>
<summary>Show answer</summary>

**Answer: B**

Auto Mode adjusts nodes first. Node timeout defaults to 720 minutes; a client wait timeout does not cancel AWS.

</details>

## 7. What does rollback --force bypass?

- A) The seven-day window and all PDBs
- B) All disruption and data compatibility
- C) Insight checks, not eligibility or Auto Mode disruption controls
- D) etcd data preservation

<details>
<summary>Show answer</summary>

**Answer: C**

ERROR/UNKNOWN blocks rollback while WARNING is advisory. Force is not the baseline recovery path.

</details>

## 8. What is not automatically restored to historical state by native version rollback?

- A) API server minor version
- B) Auto Mode node version adjustment
- C) Add-ons, apps, etcd objects and PV data
- D) Control-plane component versions

<details>
<summary>Show answer</summary>

**Answer: C**

Ordinary managed node groups need separate UpdateNodegroupVersion handling. Version rollback differs from snapshot restoration.

</details>

## 9. Which statement about setting an NLB target-group weight to zero is correct?

- A) Existing connections are always preserved to completion
- B) Existing connections can close after a short period; test retry/session behavior
- C) Weights must sum to 100
- D) NLB does not support weighted TGs

<details>
<summary>Show answer</summary>

**Answer: B**

Weights are relative values from 0–999. Distinguish ordinary changes from zero-weight transition; TLS listeners do not support TG stickiness.

</details>

## 10. What should be verified before decommissioning Blue?

- A) Destroy immediately when weight is zero
- B) Review shared resources/TG references, data compatibility, recovery period and ownership
- C) One HTTP 200 proves all data consistency
- D) Shared EFS removes the need to review concurrent writers

<details>
<summary>Show answer</summary>

**Answer: B**

Account for TG lifecycle on Auto Mode TGB/cluster deletion and shared listeners. Namespace changes do not guarantee consumer/DB/DNS isolation.

</details>
