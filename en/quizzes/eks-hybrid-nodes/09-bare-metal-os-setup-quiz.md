# Bare Metal Server OS Installation and Migration Quiz

> **Last Updated**: September 13, 2026

> **Related Document**: [Guide](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## Multiple Choice Questions

<span id="_1-what-is-a-key-benefit-of-running-eks-hybrid-nodes-on-bare-metal-servers"></span>

### 1. What can be a reason to assess bare metal for Hybrid Nodes?

- A) Automatic conversion of every VM to a container
- B) Potential removal of the hypervisor layer, evaluated against total cost and workload requirements
- C) Operation with no AWS connectivity
- D) Automatic cancellation of all software licenses

<details>
<summary>Show Answer</summary>

**Answer: B) Potential removal of the hypervisor layer, evaluated against total cost and workload requirements**

**Explanation:**

Removing a hypervisor can change licensing and execution overhead, but does not guarantee lower total cost or better performance. Containerization, data migration, availability, support and contract obligations need separate work. Do not infer savings from the guide's preserved unverified historical price estimates.

</details>

<span id="_2-what-are-the-essential-components-required-for-pxe-boot-infrastructure"></span>

### 2. Which components commonly serve a legacy PXE boot design?

- A) DNS and NFS alone
- B) DHCP/ProxyDHCP boot information and a TFTP boot server
- C) FTP and SMTP
- D) LDAP and Kerberos alone

<details>
<summary>Show Answer</summary>

**Answer: B) DHCP/ProxyDHCP boot information and a TFTP boot server**

**Explanation:**

Legacy PXE commonly uses DHCP boot information and TFTP. HTTP can deliver installer content; UEFI HTTP/iPXE designs may use different paths. pxelinux.0 is not a universal UEFI bootloader. Verify the firmware/loader chain and isolate provisioning; private activation codes and keys must not be exposed on a shared unauthenticated server.

</details>

<span id="_3-which-correctly-pairs-ubuntu-s-automated-installation-method-with-rhel-s-automated-installation-method"></span>

### 3. Which pairing correctly describes automated OS installation?

- A) Ubuntu: Kickstart; RHEL: Autoinstall
- B) Ubuntu Server: Subiquity Autoinstall YAML; RHEL: Kickstart
- C) Ubuntu: govc; RHEL: TOML
- D) Both require an unverified latest nodeadm download inside the installer

<details>
<summary>Show Answer</summary>

**Answer: B) Ubuntu Server: Subiquity Autoinstall YAML; RHEL: Kickstart**

**Explanation:**

Cloud-init can deliver Ubuntu's Autoinstall configuration. RHEL uses Kickstart. Validate the selected installer version and host-specific storage/network settings. A YAML parser or ksvalidator does not prove that the intended disk is safe to erase or that the installed host can authenticate.

</details>

<span id="_4-according-to-the-os-infrastructure-support-matrix-what-is-bottlerocket-s-supported-environment"></span>

### 4. Which Bottlerocket deployment is supported for EKS Hybrid Nodes in the reviewed AWS guidance?

- A) Any bare-metal variant
- B) Every hypervisor and architecture
- C) Supported VMware variants >=1.37.0 on x86_64
- D) Only EC2

<details>
<summary>Show Answer</summary>

**Answer: C) Supported VMware variants >=1.37.0 on x86_64**

**Explanation:**

This is the EKS Hybrid support boundary, not a statement about every Bottlerocket product variant. For Hybrid bare metal assess supported Ubuntu/RHEL hosts. AL2023 is also an on-premises virtualized-guest option, not the supported generic bare-metal path. Check Kubernetes variant availability and current lifecycle requirements separately.

</details>

<span id="_5-what-configuration-tool-and-format-does-bottlerocket-use-differently-from-other-operating-systems"></span>

### 5. How should Bottlerocket settings and govc be distinguished?

- A) govc is the Bottlerocket TOML parser
- B) Bottlerocket uses the same nodeadm YAML as Ubuntu
- C) Bottlerocket uses settings/bootstrap inputs; govc manages VMware VM lifecycle and user-data delivery
- D) settings.hybrid.ssm is a standard supported settings namespace

<details>
<summary>Show Answer</summary>

**Answer: C) Bottlerocket uses settings/bootstrap inputs; govc manages VMware VM lifecycle and user-data delivery**

**Explanation:**

Use the versioned Bottlerocket settings/bootstrap process from the guide. The old settings.hybrid.* examples were invalid. govc can clone/configure/power VMs but is not the OS settings parser. Protect guestinfo and user-data; base64 encoding does not encrypt credentials.

</details>

<span id="_6-when-selecting-a-credential-provider-for-an-environment-without-pki-infrastructure-and-with-internet-connectivity-which-option-is-recommended"></span>

### 6. Which statement about Hybrid credential providers and connectivity is correct?

- A) IAM Roles Anywhere works indefinitely with no AWS connection
- B) Both providers need their required AWS APIs; private connectivity can avoid public internet access
- C) SSM always requires direct public internet
- D) A Kubernetes ServiceAccount replaces the host's Hybrid credential provider

<details>
<summary>Show Answer</summary>

**Answer: B) Both providers need their required AWS APIs; private connectivity can avoid public internet access**

**Explanation:**

SSM can reduce certificate-management work where no managed PKI exists. IAM Roles Anywhere uses X.509 identity but still calls AWS CreateSession for temporary credentials. Either design needs its supported API/private endpoint paths, identity lifecycle and EKS authorization. A completely disconnected/DDIL environment is not the supported EKS Hybrid operating model.

</details>

<span id="_7-what-option-must-be-used-when-installing-containerd-with-nodeadm-on-rhel"></span>

### 7. What are the documented nodeadm containerd-source options for RHEL?

- A) distro is the only supported option
- B) docker, or none when containerd is installed and maintained separately
- C) eks, regardless of the OS
- D) latest, with no compatibility check

<details>
<summary>Show Answer</summary>

**Answer: B) docker, or none when containerd is installed and maintained separately**

**Explanation:**

RHEL does not support nodeadm's distro source. docker selects the compatible Docker-distributed containerd package; none skips installation and requires a separately managed runtime before init. The statement that every RHEL installation must use docker omits this supported alternative. AL2023 has a different source constraint.

</details>

<span id="_8-what-is-the-correct-order-of-phases-when-migrating-from-vmware-to-bare-metal-eks-hybrid-nodes"></span>

### 8. Which migration sequence keeps a recovery path?

- A) Decommission the source first
- B) Cancel licenses before the pilot
- C) Prepare a parallel target, migrate/test workloads and networking, accept data/operations, then decommission after the rollback window
- D) Copy VM disks into containers and immediately wipe the source

<details>
<summary>Show Answer</summary>

**Answer: C) Prepare a parallel target, migrate/test workloads and networking, accept data/operations, then decommission after the rollback window**

**Explanation:**

Inventory dependencies, plan backups/restores and keep rollback capacity. Test data consistency, TLS/DNS, access policies and real workload behavior before switching traffic. Neither VM containerization nor a CSI driver installation alone migrates state. Decommissioning and license changes require the agreed acceptance/retention decisions.

</details>

<span id="_9-what-does-openshift-s-route-concept-map-to-in-eks-hybrid-nodes"></span>

### 9. How should an OpenShift Route be migrated?

- A) Rename it to Service with no other changes
- B) Design an Ingress/Gateway API mapping and verify the selected controller's TLS and routing behavior
- C) Replace every Route with NetworkPolicy
- D) Copy its fields unchanged into a Gateway

<details>
<summary>Show Answer</summary>

**Answer: B) Design an Ingress/Gateway API mapping and verify the selected controller's TLS and routing behavior**

**Explanation:**

Ingress/Gateway API are candidate routing interfaces, not automatic equivalents. Preserve termination/reencrypt/passthrough, weights and annotations as applicable. The same caution applies to SCC versus PSS/PSA, OLM delivery, ImageStream triggers and DeploymentConfig hooks: ECR/Helm/Deployment do not reproduce every OpenShift behavior automatically.

</details>

<span id="_10-what-is-the-solution-when-pods-won-t-terminate-on-ubuntu-24-04-due-to-containerd-issues"></span>

### 10. What is an appropriate response to the documented Ubuntu 24.04 AppArmor/container termination issue?

- A) Remove all unknown AppArmor profiles on every host
- B) Verify the actual package/profile problem, apply the supported fix, and perform a planned reboot when that transition requires it
- C) Disable every security mechanism
- D) Assume every stuck Pod is fixed by installing exactly containerd 1.7.19

<details>
<summary>Show Answer</summary>

**Answer: B) Verify the actual package/profile problem, apply the supported fix, and perform a planned reboot when that transition requires it**

**Explanation:**

Bug 2065423 has released fixes and describes a restart for the affected package/profile transition. Check vendor package/backport status and actual signal-denial logs. aa-remove-unknown removes loaded profiles absent from /etc/apparmor.d; it is not a targeted editor. Use controlled drain/reboot/workload checks and do not make every AppArmor change a universal reboot rule.

</details>

### 11. Which cost model matches the reviewed EKS Hybrid pricing?

- A) A universal flat $0.01/vCPU-hour including every service
- B) Monthly marginal tiers on reported vCPU-hours, plus separate cluster and other costs
- C) Only CPU requested by running Pods is billed
- D) No node charge while workloads are idle

<details>
<summary>Show Answer</summary>

**Answer: B) Monthly marginal tiers on reported vCPU-hours, plus separate cluster and other costs**

**Explanation:**

The first 576,000 monthly vCPU-hours use $0.020/vCPU-hour, followed by the published marginal tiers. Aggregation is Regional within an account or an Organizations consolidated-billing scope. Include reported vCPUs, month lengths, cluster support tier and other services. The old $2,803.20/node-year result is preserved as an obsolete unverified assumption, not current TCO.

</details>

### 12. What does choosing Cilium BGP imply when replacing NSX-T functions?

- A) Every NSX-T feature is automatically reproduced
- B) BGP provides route exchange; overlay, firewall, load balancing and policy requirements need separate mapping
- C) No return-path routing needs testing
- D) All existing sessions survive unchanged

<details>
<summary>Show Answer</summary>

**Answer: B) BGP provides route exchange; overlay, firewall, load balancing and policy requirements need separate mapping**

**Explanation:**

BGP advertisements do not supply the whole NSX platform. Inventory route, overlay, security and load-balancing behavior separately, then test target addressing, return paths, TLS/DNS and established/new connections. Select the supported mixed-CNI pattern and preserve rollback; no universal one-to-one replacement is claimed.

</details>
