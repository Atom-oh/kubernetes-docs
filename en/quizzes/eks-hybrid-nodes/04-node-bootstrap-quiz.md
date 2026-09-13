# EKS Hybrid Nodes Node Bootstrap Quiz

> **Related Document**: [Node Bootstrap](../../eks-hybrid-nodes/04-node-bootstrap.md)
> **Last Updated**: September 12, 2026

### 1. What is the role of Hybrid nodeadm?

A. Creating the EKS control plane

B. Installing and initializing Hybrid node components using the aws/eks-hybrid implementation

C. Scheduling application Pods

D. Replacing the CNI controller

<details>
<summary>Show Answer</summary>

**Answer: B. Installing and initializing Hybrid node components using the aws/eks-hybrid implementation**

**Explanation:** Use the Hybrid installer, not the EC2 amazon-eks-ami nodeadm. Install dependencies before init, select the correct OS/runtime source and verify the approved binary. Current SSM new installs/upgrades require nodeadm1.0.19 or later.

</details>

### 2. Which cluster inputs are used in the normal Hybrid NodeConfig?

A. Cluster name and Region, together with a supported credential provider

B. VPC ID and subnet ID only

C. Three mandatory hand-written fields: name, endpoint and CA

D. An IAM user access key and password

<details>
<summary>Show Answer</summary>

**Answer: A. Cluster name and Region, together with a supported credential provider**

**Explanation:** The documented Hybrid config uses spec.cluster.name/region plus spec.hybrid.ssm or spec.hybrid.iamRolesAnywhere. The prepared Hybrid role supplies cluster discovery permissions. It is incorrect to require a manually copied raw PEM CA for every normal Hybrid initialization.

</details>

### 3. Which nodeadm credential-provider pair is supported?

A. IAM user keys and LDAP

B. Static Kubernetes tokens and local passwords

C. SSM hybrid activations and IAM Roles Anywhere

D. EC2 instance profiles and kubeconfig passwords

<details>
<summary>Show Answer</summary>

**Answer: C. SSM hybrid activations and IAM Roles Anywhere**

**Explanation:** Choose exactly one of ssm or iam-ra. SSM configuration contains activationCode and activationId under spec.hybrid.ssm; IAM Roles Anywhere uses spec.hybrid.iamRolesAnywhere. Both need the prepared Hybrid role and cluster access.

</details>

### 4. Which option is NOT a kubelet configuration field?

A. maxPods

B. clusterDNS

C. clusterDomain

D. podScheduler

<details>
<summary>Show Answer</summary>

**Answer: D. podScheduler**

**Explanation:** podScheduler is not a kubelet configuration field; the scheduler runs in the control plane. The earlier choice clusterCIDR was also invalid as a kubelet config field, making the old question ambiguous. NodeConfig kubelet settings do not replace CNI IPAM planning.

</details>

### 5. What does an init-command-completed automation record establish?

A. The Node is permanently Ready

B. The init command completed and local checks passed at that time; cluster readiness still needs verification

C. All image pulls and credential renewals have been tested

D. The host can safely be cloned including its identity

<details>
<summary>Show Answer</summary>

**Answer: B. The init command completed and local checks passed at that time; cluster readiness still needs verification**

**Explanation:** Bind automation records to the host/config/binary, retain started state on interruption and refuse automatic replay of unknown state. network-online.target and RemainAfterExit are not proofs of AWS connectivity or Node readiness.

</details>

### 6. How should the Kubernetes API server CA be understood?

A. It automatically issues the kubelet client certificate during every TLS handshake

B. It is the registry login credential

C. It supports server-certificate trust validation; client-certificate approval/issuance is separate

D. It replaces the Hybrid IAM role

<details>
<summary>Show Answer</summary>

**Answer: C. It supports server-certificate trust validation; client-certificate approval/issuance is separate**

**Explanation:** Validate the server hostname and CA chain. Do not use curl -k as a trust test. Cluster CA, private-registry CA and IAM Roles Anywhere host identity are different trust uses.

</details>

### 7. What is an appropriate response to a failed join or partial initialization?

A. Run nodeadm status and then uninstall --force immediately

B. Inspect bounded private kubelet logs and nodeadm debug, verify identity/network, then reconcile the recorded state

C. Delete all Cilium CRDs in the shared cluster

D. Delete the Node object and assume SSM is deregistered

<details>
<summary>Show Answer</summary>

**Answer: B. Inspect bounded private kubelet logs and nodeadm debug, verify identity/network, then reconcile the recorded state**

**Explanation:** The inspected CLI has nodeadm debug, not nodeadm status. Debug contacts AWS/cluster services; keep output private. A Node object deletion neither stops kubelet nor deregisters SSM. Uninstall is a controlled removal operation, not a generic authentication fix.

</details>

### 8. Which Bottlerocket Pod Identity statement is correct?

A. It uses NodeConfig and nodeadm exactly like Ubuntu

B. settings.hybrid.ssm is the complete documented bootstrap contract

C. Bottlerocket1.39.0+ uses provider bootstrap credentials-file support and the hybrid-bottlerocket agent DaemonSet

D. Base64 user data encrypts the private key

<details>
<summary>Show Answer</summary>

**Answer: C. Bottlerocket1.39.0+ uses provider bootstrap credentials-file support and the hybrid-bottlerocket agent DaemonSet**

**Explanation:** Bottlerocket has separate settings/bootstrap-container inputs. The compatible agent floor is v1.3.7-eksbuild.2, and the temporary-credential path is /var/eks-hybrid/.aws/credentials. Select a current compatible add-on and protect user data; encoding is not encryption.

</details>

### 9. Which Cilium lifecycle action is correctly scoped?

A. Change an existing cluster-pool CIDR in place

B. Run a hybrid-scoped preflight and verify DaemonSet coverage plus validation Deployment readiness before upgrade

C. Always reuse all old Helm values without review

D. Uninstall every CRD containing cilium to fix one node

<details>
<summary>Show Answer</summary>

**Answer: B. Run a hybrid-scoped preflight and verify DaemonSet coverage plus validation Deployment readiness before upgrade**

**Explanation:** Preflight has a separate node selector. Existing pool elements and mask size must not change; expansion can add a reviewed new pool entry with corresponding EKS/routing changes. CNI/CRD removal is a disruptive owner-controlled task.

</details>

### 10. What does nodeadm uninstall --force mean in the inspected release?

A. It guarantees removal of every mounted path including /var/lib/kubelet

B. It is a generic confirmation bypass and a substitute for drain

C. It removes additional default paths, but the v1.0.9+ protected /var/lib/kubelet behavior remains

D. It automatically verifies a new replacement node

<details>
<summary>Show Answer</summary>

**Answer: C. It removes additional default paths, but the v1.0.9+ protected /var/lib/kubelet behavior remains**

**Explanation:** Do not delete mounted kubelet paths blindly. Evacuate workloads, review data and provider/CNI cleanup, and preserve recovery evidence. An approved reinstall needs install → config check → init, not init alone after uninstall.

</details>

