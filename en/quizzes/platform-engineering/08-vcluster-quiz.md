# vCluster Quiz

[vCluster](../../platform-engineering/08-vcluster.md)

The original eight topics have been reviewed against vCluster 0.37.0.

## 1. What does Shared Nodes vCluster separate and share?

<details>
<summary>Show answer</summary>

It can separate virtual APIs, RBAC, controllers and stores while sharing workload nodes, kernels, CNI and CSI. It does not guarantee complete hardware, network or performance isolation.

</details>

## 2. What does the Syncer do?

<details>
<summary>Show answer</summary>

Translate configured virtual resources/references to host resources and propagate observed state back. Defaults and naming vary by mode/version; not every resource always synchronizes bidirectionally.

</details>

## 3. What is required for PR previews?

<details>
<summary>Show answer</summary>

A validated profile, host capacity, trusted CI identity/events, explicit namespace/context and cleanup. Sub-30-second creation or faster tests are not guaranteed; do not give host credentials to untrusted fork code.

</details>

## 4. How should pause and automatic sleep be understood?

<details>
<summary>Show answer</summary>

Current pause removes workloads and recreates them on resume, with separate PVC/Service retention. It is not memory-preserving suspend or backup. Validate automatic wake behavior, entitlements and actual savings separately.

</details>

## 5. How do StorageClasses and PVCs work with Shared Nodes?

<details>
<summary>Show answer</summary>

Use supported fromHost StorageClass configuration and host CSI, synchronizing PVCs to the host. Check binding mode, topology and reclaim/retention. Version 0.37 supports snapshot sync, distinct from removed deploy.volumeSnapshotController.

</details>

## 6. What connects Backstage and GitOps provisioning?

<details>
<summary>Show answer</summary>

Prepared actions/skeletons, reviewed PRs, real ArgoCD project/destination/repository permissions and a values source. debug:log does not approve or wait for deployment. Deliver kubeconfigs through approved credential channels.

</details>

## 7. Does adding NetworkPolicy block all host access?

<details>
<summary>Show answer</summary>

No. Allows are additive and cannot be reduced by another deny policy. The Syncer needs host API access. The profile disables workload public egress but retains control-plane port allowances, requiring actual CNI/path validation.

</details>

## 8. How should deployment modes be selected?

<details>
<summary>Show answer</summary>

Evaluate API autonomy, node/kernel/CNI/CSI, account/admin boundaries, performance and lifecycle needs. Compare Shared Nodes, Dedicated/Private Nodes, Standalone and separate clusters without promising unmeasured speed, cost or regulatory suitability.

</details>
