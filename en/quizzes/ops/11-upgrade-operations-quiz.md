# Upgrade Operations Quiz

> **Related Document**: [Upgrade Operations](../../ops/11-upgrade-operations.md)

## Multiple Choice Questions

### 1. How long does AWS support each EKS Kubernetes version under standard support?

- A) 6 months
- B) 12 months
- C) 14 months
- D) 24 months

<details>
<summary>Show Answer</summary>

**Answer: C) 14 months**

**Explanation:**
AWS provides 14 months of standard support for each Kubernetes version on EKS. After that, clusters can be migrated to extended support (additional cost) or must be upgraded. Planning upgrades within the standard support window is recommended.

</details>

### 2. What tool detects deprecated Kubernetes APIs in your cluster?

- A) kubectl
- B) Pluto
- C) Helm
- D) Terraform

<details>
<summary>Show Answer</summary>

**Answer: B) Pluto**

**Explanation:**
Pluto scans Kubernetes manifests, Helm releases, and live clusters for deprecated or removed API versions. It helps identify resources that need updating before upgrading to a version where those APIs no longer exist.

</details>

### 3. What is the purpose of Velero in EKS upgrade operations?

- A) To upgrade the Kubernetes version
- B) To backup and restore cluster resources before upgrade
- C) To monitor cluster performance
- D) To manage node groups

<details>
<summary>Show Answer</summary>

**Answer: B) To backup and restore cluster resources before upgrade**

**Explanation:**
Velero provides backup and restore capabilities for Kubernetes resources and persistent volumes. Taking a Velero backup before upgrades enables recovery if the upgrade causes issues, providing a safety net for the operation.

</details>

### 4. In the Terraform 3-Layer architecture, what is the correct upgrade order?

- A) Workload -> Platform -> Foundation
- B) Platform -> Foundation -> Workload
- C) Foundation -> Platform -> Workload
- D) All layers simultaneously

<details>
<summary>Show Answer</summary>

**Answer: C) Foundation -> Platform -> Workload**

**Explanation:**
The upgrade order follows dependencies: Foundation (VPC, IAM) first since Platform depends on it, then Platform (EKS cluster) since Workload depends on it, finally Workload (applications). This ensures each layer's dependencies are already upgraded.

</details>

### 5. In EKS Auto Mode, what happens to nodes during a Kubernetes version upgrade?

- A) Nodes upgrade in-place without restart
- B) Nodes are automatically replaced with new version nodes
- C) Nodes must be manually deleted
- D) Nodes are not affected by version upgrades

<details>
<summary>Show Answer</summary>

**Answer: B) Nodes are automatically replaced with new version nodes**

**Explanation:**
After upgrading the EKS control plane, Auto Mode automatically rotates nodes to match the new version. This process cordons old nodes, drains workloads, and provisions new nodes with the updated kubelet version.

</details>

### 6. What should be verified with Pod Disruption Budgets (PDBs) before upgrade?

- A) That no PDBs exist
- B) That PDBs allow enough disruption for rolling node replacement
- C) That PDBs are set to zero
- D) That PDBs reference correct API versions

<details>
<summary>Show Answer</summary>

**Answer: B) That PDBs allow enough disruption for rolling node replacement**

**Explanation:**
PDBs that are too restrictive (e.g., maxUnavailable: 0 with minAvailable: 100%) can block node draining during upgrades. Before upgrading, ensure PDBs allow sufficient disruption for the rolling replacement process to proceed.

</details>

### 7. What is the blue/green upgrade strategy for EKS clusters?

- A) Upgrading both clusters simultaneously
- B) Creating a new cluster with the new version and gradually shifting traffic
- C) Upgrading in-place with rollback capability
- D) Running both versions on the same nodes

<details>
<summary>Show Answer</summary>

**Answer: B) Creating a new cluster with the new version and gradually shifting traffic**

**Explanation:**
Blue/green upgrade creates a new "green" cluster running the target Kubernetes version alongside the existing "blue" cluster. Traffic is gradually shifted using weighted routing, allowing easy rollback by shifting traffic back to blue if issues arise.

</details>

### 8. What post-upgrade validation should be performed?

- A) Only check if pods are running
- B) Verify node status, pod health, addon functionality, and application behavior
- C) No validation is needed
- D) Only run Pluto again

<details>
<summary>Show Answer</summary>

**Answer: B) Verify node status, pod health, addon functionality, and application behavior**

**Explanation:**
Post-upgrade validation should include: all nodes Ready, pods Running, cluster addons (CoreDNS, kube-proxy, CNI) functional, ingress/egress working, storage operations successful, and application-specific health checks passing.

</details>

### 9. How does EKS extended support differ from standard support?

- A) Extended support is free
- B) Extended support provides additional months beyond standard at additional cost
- C) Extended support only covers security patches
- D) Extended support is only for Fargate

<details>
<summary>Show Answer</summary>

**Answer: B) Extended support provides additional months beyond standard at additional cost**

**Explanation:**
EKS extended support allows clusters to run on older Kubernetes versions beyond the 14-month standard window, but at additional per-cluster-hour cost. This provides flexibility for organizations that need more time to upgrade.

</details>

### 10. When upgrading, why is it important to check addon compatibility?

- A) Addons are automatically upgraded
- B) Some addon versions are only compatible with specific Kubernetes versions
- C) Addons don't affect upgrades
- D) Addons must be removed before upgrade

<details>
<summary>Show Answer</summary>

**Answer: B) Some addon versions are only compatible with specific Kubernetes versions**

**Explanation:**
EKS managed addons (VPC CNI, CoreDNS, kube-proxy) and third-party addons have version compatibility matrices with Kubernetes versions. Upgrading to an incompatible addon version can break cluster functionality. Check and plan addon upgrades alongside the cluster upgrade.

</details>
