# EKS Integration Quiz

> **Related Document**: [EKS Integration](../../../networking/calico/08-eks-integration.md)
> **Last Updated**: February 22, 2025

## Quiz

1. What is the typical role separation when using VPC CNI with Calico on EKS?
   - A) VPC CNI handles policy, Calico handles networking
   - B) VPC CNI handles networking (IP allocation), Calico handles network policy
   - C) VPC CNI and Calico both handle networking redundantly
   - D) Calico completely replaces VPC CNI

<details>
<summary>Show Answer</summary>

**Answer: B) VPC CNI handles networking (IP allocation), Calico handles network policy**

**Explanation:**
In the most common EKS configuration, the AWS VPC CNI handles pod networking by allocating IPs from the VPC, while Calico is installed in "policy-only" mode to provide network policy enforcement. This combines native VPC integration with Calico's powerful policy capabilities.

</details>

2. What are the three main methods to install Calico on EKS?
   - A) kubectl apply, Docker, AWS CLI
   - B) EKS Add-on, Tigera Operator, Helm chart
   - C) CloudFormation, Terraform, Pulumi
   - D) eksctl, AWS Console, SDK

<details>
<summary>Show Answer</summary>

**Answer: B) EKS Add-on, Tigera Operator, Helm chart**

**Explanation:**
Calico can be installed on EKS using: 1) The EKS managed add-on (simplest for policy-only mode), 2) The Tigera Operator (recommended for full Calico features), or 3) Helm charts (flexible configuration). Each method has different trade-offs in terms of simplicity vs customization.

</details>

3. Starting from which EKS version is the native Network Policy Controller available?
   - A) EKS 1.12
   - B) EKS 1.14
   - C) EKS 1.18
   - D) EKS 1.24

<details>
<summary>Show Answer</summary>

**Answer: B) EKS 1.14**

**Explanation:**
EKS introduced its native Network Policy Controller starting with version 1.14. This controller provides basic Kubernetes NetworkPolicy support. However, Calico offers additional policy features like GlobalNetworkPolicy and policy tiers that go beyond the native controller's capabilities.

</details>

4. What is a key limitation of running Calico with EKS Fargate?
   - A) Fargate does not support any networking
   - B) Calico cannot enforce network policies on Fargate pods
   - C) Fargate only supports IPv6
   - D) Calico requires root access which Fargate provides

<details>
<summary>Show Answer</summary>

**Answer: B) Calico cannot enforce network policies on Fargate pods**

**Explanation:**
Fargate pods run in isolated microVMs managed by AWS, and users cannot install DaemonSets or modify the underlying host. Since Calico's Felix agent runs as a DaemonSet, it cannot be deployed to Fargate nodes, meaning network policy enforcement is not available for Fargate pods.

</details>

5. What is IRSA in the context of Calico on EKS?
   - A) Internal Route Service Allocation
   - B) IAM Roles for Service Accounts - allowing pods to assume AWS IAM roles
   - C) Ingress Resource Security Association
   - D) IP Range Subnet Assignment

<details>
<summary>Show Answer</summary>

**Answer: B) IAM Roles for Service Accounts - allowing pods to assume AWS IAM roles**

**Explanation:**
IRSA (IAM Roles for Service Accounts) allows Kubernetes service accounts to assume AWS IAM roles. When Calico components need to access AWS APIs (e.g., for cloud provider integration), IRSA provides secure, fine-grained access without embedding credentials in pods.

</details>

6. How do Security Groups and Calico network policies differ in scope?
   - A) They are functionally identical
   - B) Security Groups operate at VPC/ENI level, Calico policies at pod/container level
   - C) Security Groups are only for ingress, Calico only for egress
   - D) Security Groups are deprecated in favor of Calico

<details>
<summary>Show Answer</summary>

**Answer: B) Security Groups operate at VPC/ENI level, Calico policies at pod/container level**

**Explanation:**
AWS Security Groups operate at the VPC networking layer, controlling traffic to/from ENIs (Elastic Network Interfaces). Calico network policies operate at the Kubernetes pod level with label-based selectors. Both can be used together for defense-in-depth, with SGs providing VPC-level controls and Calico providing application-level policies.

</details>

7. What should be considered when upgrading EKS clusters running Calico?
   - A) Calico must be uninstalled before upgrading
   - B) Verify Calico version compatibility with the target EKS version
   - C) EKS upgrades automatically upgrade Calico
   - D) Calico only supports specific EKS versions ending in even numbers

<details>
<summary>Show Answer</summary>

**Answer: B) Verify Calico version compatibility with the target EKS version**

**Explanation:**
When upgrading EKS, you should verify that your Calico version is compatible with the target Kubernetes/EKS version. Review Calico's compatibility matrix and upgrade Calico if necessary before or after the EKS upgrade, following the documented upgrade procedures.

</details>

8. What should the kubernetesProvider setting be configured to for EKS installations?
   - A) kubernetesProvider: AWS
   - B) kubernetesProvider: EKS
   - C) kubernetesProvider: Amazon
   - D) kubernetesProvider: None (auto-detected)

<details>
<summary>Show Answer</summary>

**Answer: B) kubernetesProvider: EKS**

**Explanation:**
When installing Calico on EKS, the `kubernetesProvider` should be set to `EKS` in the Installation resource. This tells Calico to use EKS-specific configurations and optimizations, ensuring proper integration with the managed Kubernetes service.

</details>

9. What does the cni.type setting control in Calico's Installation resource for EKS?
   - A) The version of the CNI specification to use
   - B) Whether Calico manages CNI or defers to another CNI plugin
   - C) The type of network encryption
   - D) Container runtime integration mode

<details>
<summary>Show Answer</summary>

**Answer: B) Whether Calico manages CNI or defers to another CNI plugin**

**Explanation:**
The `cni.type` setting determines Calico's CNI behavior. Setting `cni.type: AmazonVPC` tells Calico to defer networking to the VPC CNI while Calico handles policy only. Setting `cni.type: Calico` makes Calico handle both networking and policy.

</details>

10. What is "policy-only mode" in Calico on EKS?
    - A) A mode where only GlobalNetworkPolicies are enforced
    - B) A mode where Calico handles network policy but not pod networking
    - C) A mode that disables all egress policies
    - D) A mode for audit-only policy evaluation

<details>
<summary>Show Answer</summary>

**Answer: B) A mode where Calico handles network policy but not pod networking**

**Explanation:**
Policy-only mode is a Calico deployment configuration where the VPC CNI continues to handle pod IP allocation and routing, while Calico is responsible only for network policy enforcement. This is the most common Calico deployment pattern on EKS as it preserves native VPC networking benefits.

</details>
