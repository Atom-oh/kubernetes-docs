# Infrastructure Setup Quiz

> **Related Document**: [Infrastructure Setup](../../ops/01-infrastructure-setup.md)

## Multiple Choice Questions

### 1. Which three operational layers does this guide use?

- A) Network → Cluster → Platform
- B) Foundation → Workload → Database
- C) VPC → Pod → Container
- D) Every resource in one state

<details>
<summary>Show Answer</summary>

**Answer: A) Network → Cluster → Platform**

00-shared is a separate bootstrap. Network owns the VPC, Cluster owns EKS, and Platform owns CoreDNS, Pod Identity, and team access. Separate state does not prevent VPC or DNS failures from affecting other layers.

</details>

### 2. Which setting enables native S3 backend locking in Terraform 1.10 or later?

- A) use_lockfile = true
- B) Always create a DynamoDB table
- C) Enable bucket versioning only
- D) Use the same key for every layer

<details>
<summary>Show Answer</summary>

**Answer: A) use_lockfile = true**

Native locking uses S3 conditional writes. DynamoDB locking is relevant to existing configurations and transitions, but is not required for native S3 locking. Changing the lock mechanism alone does not move the state storage location.

</details>

### 3. Which statement about terraform_remote_state security is correct?

- A) Readers can access only outputs
- B) Backend access can expose the entire state snapshot, so consider trust boundaries
- C) sensitive=true revokes IAM read access
- D) State never contains sensitive values

<details>
<summary>Show Answer</summary>

**Answer: B) Backend access can expose the entire state snapshot, so consider trust boundaries**

The expression exposes root outputs, but the underlying state contains more information. Consider separately publishing only required values across trust boundaries.

</details>

### 4. Which statement about a standard regional EKS cluster and built-in Auto Mode pools is correct?

- A) One control-plane subnet AZ is sufficient
- B) A blue name pins workers to AZ-a
- C) EKS subnets need at least two distinct AZs; worker placement constraints are separate
- D) A Cluster=blue subnet tag pins nodes

<details>
<summary>Show Answer</summary>

**Answer: C) EKS subnets need at least two distinct AZs; worker placement constraints are separate**

Built-in pools can use multiple configured AZs. Single-AZ worker cells require NodePool/NodeClass placement design and recovery capacity in other cells.

</details>

### 5. What happens if gpu is added as a built-in compute_config.node_pools name?

- A) It creates an official built-in GPU pool
- B) gpu is not a built-in pool name; configure a suitable custom NodePool
- C) Existing nodes immediately become GPUs
- D) All clusters become GPU-only

<details>
<summary>Show Answer</summary>

**Answer: B) gpu is not a built-in pool name; configure a suitable custom NodePool**

The built-in names are general-purpose and system. The input is a list of names, not an arbitrary map defining GPU pools. Custom NodePools belong to the GitOps side of this guide.

</details>

### 6. What is the correct purpose and requirement for EKS Pod Identity?

- A) It automatically fixes Pod image pulls from ECR
- B) It always requires an OIDC provider
- C) It provides role credentials for supported SDK calls, with association, trust, and node support
- D) The association installs the ServiceAccount and ESO

<details>
<summary>Show Answer</summary>

**Answer: C) It provides role credentials for supported SDK calls, with association, trust, and node support**

Auto Mode includes agent functionality; ordinary EKS nodes may need the separate agent. Configure the matching namespace/SA and distinguish kubelet image-pull permissions from application SDK permissions.

</details>

### 7. How should state be separated by environment and cluster color?

- A) TF_DATA_DIR alone splits a shared S3 key
- B) Select distinct backend bucket/key values and matching initialization directories
- C) Changing the environment variable moves prod state to dev
- D) Disable S3 versioning

<details>
<summary>Show Answer</summary>

**Answer: B) Select distinct backend bucket/key values and matching initialization directories**

Backend configuration determines the actual state location. TF_DATA_DIR separates initialization metadata, modules, and provider caches; it does not replace the state key. Separate bootstrap local state by account/environment too.

</details>

### 8. How does this Auto Mode example handle CoreDNS and StorageClasses?

- A) Both are always created without configuration
- B) Pure Auto Mode uses node-local DNS; mixed nodes need a CoreDNS Deployment; create StorageClasses separately
- C) Always install duplicate EBS CSI and Pod Identity agents
- D) Pin the CoreDNS version to the word latest

<details>
<summary>Show Answer</summary>

**Answer: B) Pure Auto Mode uses node-local DNS; mixed nodes need a CoreDNS Deployment; create StorageClasses separately**

Pure Auto Mode uses CoreDNS as a node system service. Mixed clusters retain the Deployment; query Kubernetes/Region compatibility and pin that add-on version. Auto Mode StorageClasses use ebs.csi.eks.amazonaws.com.

</details>

### 9. Does an administrator access entry complete kubectl access on its own?

- A) It also grants IAM DescribeCluster and network access
- B) No: authenticate as that principal and prepare IAM permissions and private API connectivity
- C) Terraform’s caller is always automatically an admin
- D) The same entry must be recreated in the Platform layer

<details>
<summary>Show Answer</summary>

**Answer: B) No: authenticate as that principal and prepare IAM permissions and private API connectivity**

This example disables automatic creator administration. EKS access policies govern Kubernetes permissions, separately from IAM. One layer should own each principal’s access entry.

</details>

### 10. Which smoke-test failure handling is correct?

- A) Hide Pod creation errors with || true
- B) Always delete a pre-existing smoke-test namespace
- C) Return nonzero on failure and clean up only the verified temporary namespace
- D) Treat every Running-phase Pod as healthy

<details>
<summary>Show Answer</summary>

**Answer: C) Return nonzero on failure and clean up only the verified temporary namespace**

The test covers workload scheduling and cluster DNS, not external LB traffic or every application dependency. Container READY counts and Pod Ready conditions are also distinct.

</details>
