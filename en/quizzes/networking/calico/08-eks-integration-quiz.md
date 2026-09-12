# EKS Integration Quiz

> **Related Document**: [EKS Integration](../../../networking/calico/08-eks-integration.md)
> **Last Updated**: September 12, 2026

## Quiz

1. What is the role separation in this guide’s ordinary EC2 Linux VPC CNI + Calico configuration?
   - A) VPC CNI handles policy and Calico allocates VPC IPs
   - B) VPC CNI handles Pod networking and Calico enforces policy
   - C) Both CNIs independently configure every Pod interface
   - D) Calico replaces the AWS-managed EKS control plane

<details>
<summary>Show Answer</summary>

**Answer: B) VPC CNI handles Pod networking and Calico enforces policy**

**Explanation:**
VPC CNI manages ENIs, Pod IP allocation and connectivity. Calico programs policy rules. This guide keeps Iptables and kube-proxy; selecting an alternate dataplane requires a separate plan.

</details>

2. Which statement correctly describes installing Calico on EKS?
   - A) Enabling VPC CNI network policy installs Calico
   - B) The pinned Tigera Operator can be installed by manifests or its Helm chart
   - C) Every EKS cluster has an AWS-supported add-on named calico
   - D) A Helm rollback always reverses Calico CRD and data migrations

<details>
<summary>Show Answer</summary>

**Answer: B) The pinned Tigera Operator can be installed by manifests or its Helm chart**

**Explanation:**
The Helm chart installs the Tigera Operator. AWS VPC CNI policy is a different implementation. Check the actual catalog and support owner for Marketplace/community products, and use one installation owner.

</details>

3. Which statement matches the current AWS native network policy guidance?
   - A) EKS 1.14 introduced every current policy feature
   - B) VPC CNI 1.21+ supports standard and admin policy with the documented platform/kernel prerequisites
   - C) Native policy supports only namespace-scoped policies forever
   - D) Native policy and Calico must both enforce the same endpoints

<details>
<summary>Show Answer</summary>

**Answer: B) VPC CNI 1.21+ supports standard and admin policy with the documented platform/kernel prerequisites**

**Explanation:**
Standard support began in VPC CNI 1.14, not EKS 1.14. Current AWS guidance covers NetworkPolicy and AWS ClusterNetworkPolicy with VPC CNI 1.21+, compatible EKS/platform versions and Linux kernel 5.10+. The APIs differ from Calico’s.

</details>

4. What is a limitation of network policy on EKS Fargate?
   - A) Fargate has no networking
   - B) Neither Calico node-agent policy nor VPC CNI native network policy is enforced inside Fargate Pods
   - C) All Calico features work if kubernetesProvider is EKS
   - D) Fargate supports only IPv6

<details>
<summary>Show Answer</summary>

**Answer: B) Neither Calico node-agent policy nor VPC CNI native network policy is enforced inside Fargate Pods**

**Explanation:**
Fargate does not run these node agents. Security groups for Pods are a separate control. Calico can still restrict the EC2 endpoint of a connection involving a Fargate peer; that is not enforcement inside Fargate.

</details>

5. When should AWS IAM permissions be assigned in this setup?
   - A) Every calico-node needs broad EC2 Describe and CloudWatch access
   - B) Assign permissions to the component that actually calls AWS APIs; basic Calico policy uses Kubernetes RBAC
   - C) The nodeMetadata Installation field creates an IRSA role
   - D) Creating an IAM policy automatically associates it with every ServiceAccount

<details>
<summary>Show Answer</summary>

**Answer: B) Assign permissions to the component that actually calls AWS APIs; basic Calico policy uses Kubernetes RBAC**

**Explanation:**
VPC CNI needs its own AWS permissions. An exporter or cloud integration may need a separate role. Use the owning component’s supported IRSA or Pod Identity configuration; basic policy-only Calico does not need a broad AWS role.

</details>

6. What does AWS require to combine security groups for Pods with Calico policy?
   - A) Only POD_SECURITY_GROUP_ENFORCING_MODE=strict
   - B) VPC CNI 1.11+ and POD_SECURITY_GROUP_ENFORCING_MODE=standard, plus the feature’s other prerequisites
   - C) A label on the EC2 instance is sufficient
   - D) Security groups for Pods also work on EKS Auto Mode

<details>
<summary>Show Answer</summary>

**Answer: B) VPC CNI 1.11+ and POD_SECURITY_GROUP_ENFORCING_MODE=standard, plus the feature’s other prerequisites**

**Explanation:**
In strict mode those Pods are not subject to Calico enforcement. Check supported instances/branch ENIs and replace affected Pods after a mode change. Standard mode with normal external SNAT uses node security groups for traffic leaving the VPC.

</details>

7. What is the correct approach to an EKS/Calico upgrade?
   - A) Always upgrade Calico after EKS, regardless of compatibility
   - B) Choose a transition-compatible Calico version and review EKS, node, add-on and CRD requirements
   - C) EKS automatically upgrades and rolls back every third-party component
   - D) Applying an older operator guarantees a safe downgrade

<details>
<summary>Show Answer</summary>

**Answer: B) Choose a transition-compatible Calico version and review EKS, node, add-on and CRD requirements**

**Explanation:**
Check compatibility on both sides of the transition. Current EKS has a conditional seven-day rollback window to the previous minor version, but Calico and EKS add-ons do not automatically roll back. Recovery still requires compatibility and readiness checks.

</details>

8. Which provider value is used in the reviewed Installation?
   - A) AWS
   - B) EKS
   - C) AmazonEKS
   - D) None

<details>
<summary>Show Answer</summary>

**Answer: B) EKS**

**Explanation:**
Use `spec.kubernetesProvider: EKS`, or `installation.kubernetesProvider: EKS` in Helm values. This selects provider configuration; it does not prove every node type, CNI, dataplane or version is supported.

</details>

9. Which CNI type delegates networking to Amazon VPC CNI?
   - A) Calico
   - B) AmazonVPC
   - C) AWSCNI
   - D) VPC

<details>
<summary>Show Answer</summary>

**Answer: B) AmazonVPC**

**Explanation:**
Set `spec.cni.type: AmazonVPC` in Installation. Calico policy-only behavior also needs the documented Pod IP annotation/RBAC and a single policy engine; `bgp: Disabled` alone does not select this CNI.

</details>

10. Why must the backend selector and TCP port remain in one destination mapping?
   - A) YAML requires every field to be repeated
   - B) A duplicate destination key can discard the selector and allow unintended endpoints
   - C) The port automatically implies the backend Pod label
   - D) Duplicate keys always produce a Kubernetes validation error

<details>
<summary>Show Answer</summary>

**Answer: B) A duplicate destination key can discard the selector and allow unintended endpoints**

**Explanation:**
Some YAML parsers retain only the last duplicate key. Keep selector and ports together, reject duplicate keys during validation, and test both allowed and denied traffic. A Ready node is not evidence of correct policy enforcement.

</details>
