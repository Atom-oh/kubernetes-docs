# Bare Metal Server OS Installation and Migration Quiz

> **Related Document**: [Bare Metal Server OS Installation and Migration Guide](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## Multiple Choice Questions

### 1. What is a key benefit of running EKS Hybrid Nodes on bare metal servers?

A. Faster network speeds than AWS EC2 instances
B. VMware license cost savings and elimination of hypervisor overhead
C. Ability to use Bottlerocket OS
D. AWS Support Plans coverage

<details>
<summary>Show Answer</summary>

**Answer: B) VMware license cost savings and elimination of hypervisor overhead**

**Explanation:**
Running EKS Hybrid Nodes on bare metal servers allows you to save on VMware licensing costs (which moved to a subscription model after the Broadcom acquisition) and OpenShift subscription fees. Additionally, eliminating the hypervisor layer optimizes performance.

</details>

### 2. What are the essential components required for PXE boot infrastructure?

A. DNS server and NFS server
B. DHCP server and TFTP server
C. FTP server and SMTP server
D. LDAP server and Kerberos server

<details>
<summary>Show Answer</summary>

**Answer: B) DHCP server and TFTP server**

**Explanation:**
The core components of PXE boot infrastructure are:
- DHCP Server: Provides IP address allocation and PXE boot information (next-server, filename)
- TFTP Server: Serves bootloader (pxelinux.0), kernel (vmlinuz), and initial RAM disk (initrd.img)
- HTTP Server (optional): Hosts OS installation images and configuration files

</details>

### 3. Which correctly pairs Ubuntu's automated installation method with RHEL's automated installation method?

A. Ubuntu: Kickstart, RHEL: Autoinstall
B. Ubuntu: Autoinstall (cloud-init), RHEL: Kickstart
C. Ubuntu: Preseed, RHEL: Anaconda
D. Ubuntu: YAML, RHEL: JSON

<details>
<summary>Show Answer</summary>

**Answer: B) Ubuntu: Autoinstall (cloud-init), RHEL: Kickstart**

**Explanation:**
- Ubuntu uses Autoinstall (cloud-init based) for PXE automated installation. It uses YAML format configuration files.
- RHEL uses Kickstart for PXE automated installation. Configuration is done via ks.cfg files.

</details>

### 4. According to the OS infrastructure support matrix, what is Bottlerocket's supported environment?

A. Both bare metal and VMware supported
B. Bare metal only
C. VMware only
D. AWS EC2 only

<details>
<summary>Show Answer</summary>

**Answer: C) VMware only**

**Explanation:**
Bottlerocket is only supported in VMware environments for EKS Hybrid Nodes (v1.37.0+, x86_64 only). For bare metal servers, you must use Ubuntu, RHEL, or Amazon Linux 2023. Bottlerocket does not use nodeadm; it uses settings.toml for configuration.

</details>

### 5. What configuration tool and format does Bottlerocket use differently from other operating systems?

A. nodeadm (YAML)
B. ansible (INI)
C. govc (TOML)
D. terraform (HCL)

<details>
<summary>Show Answer</summary>

**Answer: C) govc (TOML)**

**Explanation:**
Bottlerocket does not use nodeadm; instead, it uses settings.toml files for configuration. The govc deployment workflow is: clone template → inject user-data → power on. In contrast, Ubuntu, RHEL, and Amazon Linux 2023 use nodeadm (YAML).

</details>

### 6. When selecting a credential provider for an environment without PKI infrastructure and with internet connectivity, which option is recommended?

A. IAM Roles Anywhere
B. SSM Hybrid Activations
C. Kubernetes Service Account
D. OIDC Provider

<details>
<summary>Show Answer</summary>

**Answer: B) SSM Hybrid Activations**

**Explanation:**
Credential provider selection guide:
- No PKI infrastructure, internet available: SSM
- Existing PKI infrastructure: IAM Roles Anywhere
- Air-gapped environment: IAM Roles Anywhere
- Custom node names needed: IAM Roles Anywhere

SSM is recommended for most environments due to its simple setup and no certificate requirements.

</details>

### 7. What option must be used when installing containerd with nodeadm on RHEL?

A. `--containerd-source distro`
B. `--containerd-source docker`
C. `--containerd-source eks`
D. `--containerd-version latest`

<details>
<summary>Show Answer</summary>

**Answer: B) `--containerd-source docker`**

**Explanation:**
On RHEL, you must use the `--containerd-source docker` option. The distribution default source (distro) is not supported on RHEL:

```bash
# Correct installation method
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker
```

Installation will fail without this option.

</details>

### 8. What is the correct order of phases when migrating from VMware to bare metal + EKS Hybrid Nodes?

A. Decommission VMware → Containerize workloads → Network transition → Build parallel infrastructure
B. Containerize workloads → Build parallel infrastructure → Decommission VMware → Network transition
C. Build parallel infrastructure → Containerize workloads → Network transition → Decommission VMware
D. Network transition → Build parallel infrastructure → Containerize workloads → Decommission VMware

<details>
<summary>Show Answer</summary>

**Answer: C) Build parallel infrastructure → Containerize workloads → Network transition → Decommission VMware**

**Explanation:**
VMware → Bare Metal + EKS Hybrid Nodes migration phases:
1. Phase 1: Build Parallel Infrastructure (Deploy EKS cluster and hybrid node infrastructure alongside VMware)
2. Phase 2: Containerize Workloads (Migrate VM-based workloads to containers)
3. Phase 3: Network Transition (Transition from NSX-T to Cilium BGP)
4. Phase 4: Decommission VMware (After verifying all workloads have been migrated)

</details>

### 9. What does OpenShift's Route concept map to in EKS Hybrid Nodes?

A. Service
B. Ingress / Gateway API
C. NetworkPolicy
D. Endpoint

<details>
<summary>Show Answer</summary>

**Answer: B) Ingress / Gateway API**

**Explanation:**
Concept mapping when migrating from OpenShift to EKS Hybrid Nodes:

| OpenShift | EKS Hybrid Nodes |
|-----------|-----------------|
| Route | Ingress / Gateway API |
| SCC | PSS (Pod Security Standards) |
| OLM | Helm / EKS Add-ons |
| MachineSet | nodeadm + Ansible |
| ImageStream | ECR |
| BuildConfig | External CI/CD |
| DeploymentConfig | Deployment |

</details>

### 10. What is the solution when Pods won't terminate on Ubuntu 24.04 due to containerd issues?

A. Disable SELinux and reboot
B. Update containerd to v1.7.19+ or modify AppArmor profile and reboot
C. Switch container runtime to Docker
D. Downgrade to cgroup v1

<details>
<summary>Show Answer</summary>

**Answer: B) Update containerd to v1.7.19+ or modify AppArmor profile and reboot**

**Explanation:**
Ubuntu 24.04 requires containerd v1.7.19 or later, or AppArmor profile changes are needed (Ubuntu bug #2065423):

```bash
# Check containerd version
containerd --version

# If version is below 1.7.19, modify AppArmor profile
sudo aa-remove-unknown

# Reboot required to apply changes
sudo reboot
```

Without rebooting, Pods may not terminate properly.

</details>
