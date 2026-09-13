# EKS Hybrid Nodes Prerequisites Quiz

> **Related Document**: [Prerequisites](../../eks-hybrid-nodes/01-prerequisites.md)
> **Last Updated**: September 12, 2026

## Multiple Choice Questions

### 1. Which scenario is not a supported reason to register machines as EKS Hybrid Nodes?

- A) Using compatible on-premises GPU servers
- B) Keeping application processing near local datasets
- C) Registering ordinary EC2/cloud machines as hybrid-node infrastructure
- D) Connected edge workloads with tested recovery

<details>
<summary>Show Answer</summary>

**Answer: C) Registering ordinary EC2/cloud machines as hybrid-node infrastructure**

**Explanation:**
AWS supports hybrid-node infrastructure on customer-operated on-premises/edge physical or virtual hosts, not cloud infrastructure. EC2 registration as a hybrid node still incurs hybrid fees. Use ordinary AWS compute types for cloud nodes. Hybrid Nodes needs reliable connectivity; a placement label alone does not prove regulatory compliance or offline operation.

</details>

### 2. Which OS statement matches the current AWS hybrid integration matrix?

- A) Windows Server is the only option
- B) Ubuntu 20.04/22.04/24.04, RHEL 8/9, virtualized AL2023 and supported Bottlerocket VMware variants
- C) Any macOS release
- D) Any Linux image automatically receives AWS OS support

<details>
<summary>Show Answer</summary>

**Answer: B) Ubuntu 20.04/22.04/24.04, RHEL 8/9, virtualized AL2023 and supported Bottlerocket VMware variants**

**Explanation:**
Review vendor security maintenance, architecture and the chosen CNI/kernel. Bottlerocket VMware v1.37.0+ is x86_64-only and uses its own bootstrap path. AL2023 is for on-premises virtualized environments and is not covered by AWS OS support outside EC2. ARM EKS kube-proxy 1.31+ requires ARMv8.2+crypto; a generic kernel 5.4 rule or CPU model name is not complete validation.

</details>

### 3. Which assertion is incorrect when evaluating GPU workload compatibility?

- A) Driver and CUDA/framework image compatibility matter
- B) Memory requirements depend on the workload
- C) Supported OS/kernel and container runtime matter
- D) CPU architecture can be ignored once a GPU is installed

<details>
<summary>Show Answer</summary>

**Answer: D) CPU architecture can be ignored once a GPU is installed**

**Explanation:**
CPU architecture, GPU variant, drivers, OS/kernel, container toolkit/runtime and the application image must all work together. There is no universal 4GB GPU minimum or fixed 525/550 driver requirement for Hybrid Nodes. A host nvcc compiler is not required merely to run a correctly packaged container; nvidia-smi and nvcc report different components.

</details>

### 4. How should the basic host resource guidance be interpreted?

- A) 1 core and 512MB is a guaranteed sufficient configuration
- B) AWS recommends at least 1 vCPU and 1 GiB RAM, without a strict universal minimum
- C) Every workload requires exactly 4 cores and 8GB
- D) A 50GB disk guarantees readiness

<details>
<summary>Show Answer</summary>

**Answer: B) AWS recommends at least 1 vCPU and 1 GiB RAM, without a strict universal minimum**

**Explanation:**
Size the OS, kubelet/runtime, CNI/agents, images/logs and actual workload separately. The previous two-core/two-GB answer and 20/50/100GB disk recommendations were inconsistent planning examples, not validated workload minima. Likewise, AWS's 100Mbps/200ms network guidance is general guidance, not a universal acceptance threshold.

</details>

### 5. Which component is not required just because a host becomes an EKS Hybrid Node?

- A) A compatible CRI runtime such as containerd
- B) The kubelet
- C) Docker Engine
- D) The chosen AWS credential/authentication helpers

<details>
<summary>Show Answer</summary>

**Answer: C) Docker Engine**

**Explanation:**
Docker's containerd package source is not a requirement to run Docker Engine. On non-Bottlerocket hosts, nodeadm install installs dependencies, config check validates inputs, and init configures/joins the node. SSM installation/upgrades require nodeadm 1.0.19+ after the signing-key change; the reviewed release is 1.0.20. RHEL uses docker or a preinstalled runtime with none, not distro.

</details>

### 6. What is the correct approach to an H100 Hybrid Nodes deployment?

- A) Install 450.x on every host
- B) Treat an old 525.x example as permanently sufficient
- C) Require exactly 535.x regardless of framework
- D) Select a supported GPU/OS/driver/CUDA/runtime cohort and validate the application

<details>
<summary>Show Answer</summary>

**Answer: D) Select a supported GPU/OS/driver/CUDA/runtime cohort and validate the application**

**Explanation:**
The old table mixed minimum and recommended driver versions and contradicted its own answer. The 450/525/535/545/550 values are not a current universal deployment contract. Verify the precise H100 variant, supported driver branch, framework image and feature requirements; stage changes on an evacuated test host. No GPU execution or model benchmark was performed in this audit.

</details>

## References

- [Hybrid prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-prereqs.html)
- [Hybrid OS compatibility](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [nodeadm reference](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
