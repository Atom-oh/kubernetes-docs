# Amazon VPC CNI Quiz

Reviewed September 11, 2026 against the [VPC CNI guide](../../networking/01-vpc-cni.md) and its primary references.

## 1. What does IPAMD do on standard EKS Linux EC2 nodes?

- A. Manage every Pod's DNS application settings
- B. Maintain ordinary ENI/IP allocation pools for Pod networking
- C. Replace the network policy controller
- D. Encrypt all inter-node traffic

<details>
<summary>Show Answer</summary>

**Answer: B. Maintain ordinary ENI/IP allocation pools for Pod networking**

The container runtime invokes the CNI binary, which requests addressing and configures the Pod sandbox. IPAMD maintains the relevant address pools. Windows, Fargate and Auto Mode management paths differ.

</details>

## 2. What is the IPv4 allocation difference between secondary-IP and prefix modes?

- A. Only secondary-IP mode supports IPv6
- B. Secondary-IP mode allocates individual addresses; IPv4 prefix mode allocates /28 blocks with 16 addresses
- C. Prefix mode removes kubelet Pod limits
- D. Prefix mode creates free space in an exhausted subnet

<details>
<summary>Show Answer</summary>

**Answer: B. Secondary-IP mode allocates individual addresses; IPv4 prefix mode allocates /28 blocks with 16 addresses**

Prefix mode needs supported hardware and contiguous blocks. Allocation still consumes subnet space, and warm targets can reserve unused addresses. IPv6 uses /80 prefixes; EKS does not provide dual-stack Pods/Services.

</details>

## 3. How does the legacy m5.large secondary-IPv4 bootstrap calculation produce 29?

- A. Kubernetes always limits all nodes to 29
- B. 3 × (10 − 1) + 2 = 29
- C. 3 × 10 − 3 = 29
- D. 29 is the size of every subnet

<details>
<summary>Show Answer</summary>

**Answer: B. 3 × (10 − 1) + 2 = 29**

There are three ENIs with ten IPv4 slots each. Removing each ENI's primary slot leaves 27 ordinary secondary addresses; the historical formula adds two host-network system Pods. It is not a universal current capacity limit—prefixes, SGPP, kubelet caps and resources change the interpretation.

</details>

## 4. What does WARM_IP_TARGET specify?

- A. The hard maximum Pod count
- B. A target number of free addresses available for ordinary assignments
- C. The cluster-wide address quota
- D. An address TTL

<details>
<summary>Show Answer</summary>

**Answer: B. A target number of free addresses available for ordinary assignments**

MINIMUM_IP_TARGET is the floor for total allocated addresses. These IP targets override the warm ENI/prefix strategy; prefix-sized allocation still applies. Choose values from measured demand, churn, address space and API behavior.

</details>

## 5. Which statement about native EKS network policy is correct?

- A. VPC CNI internally runs Calico
- B. Standard eBPF policy was introduced in 1.14, but current platform/version and opt-in conditions still apply
- C. It automatically covers Windows and Fargate
- D. Enabling it guarantees every standalone Pod is reliably enforced

<details>
<summary>Show Answer</summary>

**Answer: B. Standard eBPF policy was introduced in 1.14, but current platform/version and opt-in conditions still apply**

The reviewed 1.23 setup uses the configured policy controller and aws-eks-nodeagent. Current EKS guidance includes EC2 Linux, controller-managed Pods and Service/container-port conditions. Standard startup mode allows traffic while rules are resolved; strict startup behavior is a separate deliberate choice.

</details>

## 6. What does custom networking with ENIConfig provide?

- A. A replacement DNS server
- B. Pod address allocation from selected subnets/security groups distinct from the node's default configuration
- C. Automatic migration of existing Pods after adding a CIDR
- D. Automatic removal of overlapping routes

<details>
<summary>Show Answer</summary>

**Answer: B. Pod address allocation from selected subnets/security groups distinct from the node's default configuration**

Configure actual same-AZ resources, enable custom networking and select ENIConfig through the intended node label/annotation. An explicit annotation overrides the label. New CIDR/subnet creation alone does not move existing Pods or supply all routes and permissions.

</details>

## 7. How do trunk and branch interfaces work for SGPP on eligible EC2 nodes?

- A. The trunk is always the primary eth0 interface
- B. The controller attaches an additional trunk ENI and associates branch interfaces used by selected Pods
- C. The two names mean IPv4 and IPv6 respectively
- D. Prefix delegation multiplies the branch-Pod limit by 16

<details>
<summary>Show Answer</summary>

**Answer: B. The controller attaches an additional trunk ENI and associates branch interfaces used by selected Pods**

The trunk is an additional interface, not the primary ENI. Supported instance types, controller/IAM and real security-group rules are prerequisites. Fargate follows a separate managed path. SGPP is unsupported on Windows/Auto Mode, while the EKS service guide documents IPv6 support under its conditions.

</details>

## 8. Which is an inappropriate default response to IP exhaustion?

- A. Check contiguous prefix space and hardware before considering prefix delegation
- B. Plan additional CIDRs/subnets and workload adoption when capacity is insufficient
- C. Switch every workload to hostNetwork to bypass ordinary Pod addressing
- D. Consider custom networking and measured warm-target tuning

<details>
<summary>Show Answer</summary>

**Answer: C. Switch every workload to hostNetwork to bypass ordinary Pod addressing**

Changing all workloads to hostNetwork changes isolation and port behavior and is not a general capacity fix. Diagnose address exhaustion, prefix fragmentation, ENI limits, kubelet capacity and API errors separately. Prefix delegation cannot create missing subnet addresses.

</details>
