# EKS Hybrid Nodes Restricted-internet Setup Quiz

> **Related Document**: [Restricted-internet Setup](../../eks-hybrid-nodes/03-airgap-setup.md)
> **Last Updated**: September 12, 2026

### 1. Which connectivity statement is correct for EKS Hybrid Nodes?

A. Physical image transfer removes the need for AWS connectivity

B. Nodes still need EKS control-plane and credential-service connectivity

C. A private S3 bucket hosts the EKS control plane

D. VPN connectivity is the same as physical isolation

<details>
<summary>Show Answer</summary>

**Answer: B. Nodes still need EKS control-plane and credential-service connectivity**

**Explanation:** Restricted public internet access can coexist with private AWS connectivity. A physically disconnected network cannot provide the live control-plane and credential-service paths Hybrid Nodes require.

</details>

### 2. Why is a PHZ alias from hybrid-assets.eks.amazonaws.com to S3 insufficient?

A. S3 never supports private DNS

B. ECR must be installed before DNS

C. DNS does not provide the original TLS hostname, object routing or authorization

D. All HTTPS requests automatically use an IAM role

<details>
<summary>Show Answer</summary>

**Answer: C. DNS does not provide the original TLS hostname, object routing or authorization**

**Explanation:** S3 interface endpoints do support private DNS. However, an alias does not rewrite TLS SNI, the HTTP Host header, object paths or authentication. Use approved image preparation or real custom-manifest URLs; do not disable certificate verification.

</details>

### 3. What does nodeadm v1.0.20 private installation mode do?

A. Installs every OS dependency from a local manifest

B. Skips OS package installation but still installs credential and EKS artifacts

C. Makes all AWS API calls optional

D. Automatically signs every S3 artifact download

<details>
<summary>Show Answer</summary>

**Answer: B. Skips OS package installation but still installs credential and EKS artifacts**

**Explanation:** The released source requires --manifest-override with --private-mode. Prepare the runtime and OS dependencies separately. SSM's installer/signature source is separately constructed, and a file:// manifest does not imply file:// artifact support.

</details>

### 4. What should an artifact preparation script do when a checksum is missing or mismatched?

A. Warn and publish the remaining files

B. Accept the run if at least one file passed

C. Generate a new expected checksum from the downloaded file

D. Stop and retain the failed candidate for investigation

<details>
<summary>Show Answer</summary>

**Answer: D. Stop and retain the failed candidate for investigation**

**Explanation:** Every required file must match a trusted, reviewed checksum record. Generating a replacement expected value defeats that check. Hash agreement alone is not independent publisher authentication.

</details>

### 5. Which is the correct scope of the IAM Roles Anywhere update service?

A. It exists in every installation, including SSM

B. It is used when enableCredentialsFile is enabled; ordinary credential-process use is a separate path

C. The service is fictional and should always be removed

D. It removes the need to renew certificates

<details>
<summary>Show Answer</summary>

**Answer: B. It is used when enableCredentialsFile is enabled; ordinary credential-process use is a separate path**

**Explanation:** aws_signing_helper_update.service is real in the credentials-file mode. Configure the appropriate service and invoking process environments, including nodeadm's proxy detection/--with-proxy behavior. Certificate lifecycle and AWS connectivity remain required.

</details>

### 6. Which images should be included in the Hybrid Nodes delivery inventory?

A. A fixed list of VPC CNI images for every node

B. Only kubelet, because it is the CNI image

C. The actual supported CNI, DNS, datapath, sandbox and workload images, including init containers and platforms

D. Any tag constructed by appending -eksbuild.1 to a Kubernetes patch

<details>
<summary>Show Answer</summary>

**Answer: C. The actual supported CNI, DNS, datapath, sandbox and workload images, including init containers and platforms**

**Explanation:** VPC CNI is not the Hybrid Nodes CNI. Use actual deployed manifests and approved digests. Private ECR pulls also need the S3 layer path and workload image-pull credentials; listing repositories is insufficient.

</details>

### 7. What is a valid pre-bootstrap nodeadm configuration check?

A. nodeadm init --dry-run

B. nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml

C. curl -k followed by reporting readiness

D. Skip a missing config file and return success

<details>
<summary>Show Answer</summary>

**Answer: B. nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml**

**Explanation:** Use a populated, protected configuration file. config check validates configuration; it does not prove private network operation or register the node. The inspected init command has no --dry-run flag.

</details>

### 8. Which proxy change best preserves an existing kube-proxy DaemonSet?

A. Replace /containers/0/env with a new JSON Patch array

B. Delete NODE_NAME because proxies do not need it

C. Use a reviewed strategic merge by container/env name and retain existing arguments and NODE_NAME

D. Always exclude .eks.amazonaws.com from the proxy

<details>
<summary>Show Answer</summary>

**Answer: C. Use a reviewed strategic merge by container/env name and retain existing arguments and NODE_NAME**

**Explanation:** A JSON Patch add targeting an existing env member can replace the entire array. Scope the patch to kube-proxy and preserve other values. The broad .eks.amazonaws.com bypass also matches the public hybrid-assets download host.

</details>

### 9. What is required before using a transferred OCI image archive?

A. Only a successful tar import

B. Verification of the approved hash, digest/platform content, destination references and eventual runtime pull behavior

C. Disabling source registry TLS to avoid certificate failures

D. Assuming the builder's architecture is the only one needed

<details>
<summary>Show Answer</summary>

**Answer: B. Verification of the approved hash, digest/platform content, destination references and eventual runtime pull behavior**

**Explanation:** Skopeo --all preserves the platform list and --preserve-digests fails if a digest cannot be retained. Import names, the containerd k8s.io namespace, imagePullPolicy and garbage collection still affect whether the real Pod can start.

</details>

### 10. Which update practice is appropriate for the private artifact repository?

A. Automatically overwrite production latest keys every week

B. Treat AccessDenied from head-object as a missing object

C. Approve a new immutable candidate after provenance, compatibility and representative-node validation

D. Promise 50–80% bandwidth savings for every environment

<details>
<summary>Show Answer</summary>

**Answer: C. Approve a new immutable candidate after provenance, compatibility and representative-node validation**

**Explanation:** Use an owned bucket, explicit expected owner, separate publisher/reader permissions and stop on unknown errors. Conditional object writes do not make a whole upload atomic. Earlier bandwidth percentages are unverified historical illustrations, not guaranteed measurements.

</details>

