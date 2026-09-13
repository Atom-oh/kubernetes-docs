# Runtime Security Quiz

> **Last Updated**: September 13, 2026

This quiz tests your understanding of Falco, Seccomp, AppArmor, eBPF-based security, and EKS runtime security.

## Quiz Questions

### 1. What technology does Falco use to detect runtime threats?

- A. Network packet analysis
- B. System call (syscall) monitoring
- C. Log analysis
- D. Memory scanning

<details>
<summary>Show Answer</summary>

**Answer: B. System call (syscall) monitoring**

**Explanation:**
Falco commonly evaluates Linux syscall events against rules; plugins can provide other event sources. In 0.44.1, container fields come from the container plugin. Verify modern_ebpf kernel/BTF requirements and metadata collection.

</details>

### 2. What is the main function of Seccomp?

- A. Network traffic filtering
- B. Restrict system calls a process can make
- C. File system encryption
- D. User authentication

<details>
<summary>Show Answer</summary>

**Answer: B. Restrict system calls a process can make**

**Explanation:**
Seccomp filters system calls. Rejection can return ERRNO, terminate, or notify depending on the profile action; it does not always kill the process.

</details>

### 3. What is the recommended default Seccomp profile in Kubernetes 1.27+?

- A. Unconfined
- B. RuntimeDefault
- C. Localhost
- D. Docker/default

<details>
<summary>Show Answer</summary>

**Answer: B. RuntimeDefault**

**Explanation:**
RuntimeDefault is the profile supplied by the container runtime. Set seccompProfile explicitly or verify kubelet seccompDefault. Kubernetes 1.27+ alone does not apply it automatically to every Pod.

</details>

### 4. What is the role of the priority field in Falco rules?

- A. Determine rule execution order
- B. Specify severity level of alerts
- C. Set resource quota
- D. Set log retention period

<details>
<summary>Show Answer</summary>

**Answer: B. Specify severity level of alerts**

**Explanation:**
priority is event severity, not evaluation order. The standard levels are EMERGENCY, ALERT, CRITICAL, ERROR, WARNING, NOTICE, INFORMATIONAL, and DEBUG. A complete rule also needs fields such as desc, condition, and output.

</details>

### 5. What happens in AppArmor's complain mode?

- A. Block all access
- B. Log ordinary violations; explicit deny can still block
- C. Disable profile
- D. Send alerts only

<details>
<summary>Show Answer</summary>

**Answer: B. Log ordinary violations; explicit deny can still block**

**Explanation:**
Complain mode normally logs policy violations while allowing them, but explicit deny rules can still block access. It is not unconditional permission for all access. Verify kernel support and the loaded profile.

</details>

### 6. What is NOT a threat detected by Amazon GuardDuty EKS Runtime Monitoring?

- A. Cryptocurrency mining
- B. Privilege escalation
- C. Code quality issues
- D. Container escape attempts

<details>
<summary>Show Answer</summary>

**Answer: C. Code quality issues**

**Explanation:**
GuardDuty Runtime Monitoring detects security threats, not code-quality defects. Current EKS support covers EC2 and Auto Mode, but excludes EKS Hybrid Nodes and EKS Fargate. Check OS/kernel/agent requirements and coverage health.

</details>

### 7. What is the main function of Cilium Tetragon?

- A. Container image scanning
- B. eBPF-based security observability
- C. Network policy management
- D. Secrets management

<details>
<summary>Show Answer</summary>

**Answer: B. eBPF-based security observability**

**Explanation:**
Tetragon provides process events, file/network hooks, and supported actions. It does not require Cilium CNI installation. Verify hook support, selector scope, and false positives; test Post/monitor behavior before enforcement.

</details>

### 8. What condition detects shell execution inside a container in Falco?

- A. container and shell_procs
- B. spawned_process and container and shell_procs
- C. exec and shell
- D. process.name = bash

<details>
<summary>Show Answer</summary>

**Answer: B. spawned_process and container and shell_procs**

**Explanation:**
This expression depends on loaded spawned_process, container, and shell_procs macros from the ruleset. A shell may be legitimate and does not prove compromise. The guide defines independent macros and unique rule names.

</details>

### 9. How do you set a read-only root filesystem for a Pod?

- A. readOnlyRootFilesystem: true
- B. rootfs: readonly
- C. filesystem.readonly: true
- D. immutableRoot: true

<details>
<summary>Show Answer</summary>

**Answer: A. readOnlyRootFilesystem: true**

**Explanation:**
readOnlyRootFilesystem belongs to the container securityContext. Writable volumes or /tmp can be supplied separately. It does not prevent malicious use of writable volumes, network access, or memory.

</details>

### 10. What does the "Defense in Depth" strategy mean in runtime security?

- A. Rely on a single security layer
- B. Apply multiple overlapping security layers
- C. Focus only on defense
- D. Protect only external boundaries

<details>
<summary>Show Answer</summary>

**Answer: B. Apply multiple overlapping security layers**

**Explanation:**
Combine controls while checking each layer’s scope and failure modes. Image/signature checks, admission/permissions, seccomp/AppArmor, runtime detection, networking, and recovery complement each other; installing more tools alone is not a guarantee.

</details>

<span id="_11-what-command-shows-traffic-blocked-by-policies-in-hubble"></span>

### 11. Which Hubble command filters dropped flows?

- A. hubble observe --blocked
- B. hubble observe --verdict DROPPED
- C. hubble observe --denied
- D. hubble observe --policy-violation

<details>
<summary>Show Answer</summary>

**Answer: B. hubble observe --verdict DROPPED**

**Explanation:**
--verdict DROPPED selects dropped flows. Not every drop is a NetworkPolicy denial; inspect drop reasons and policy verdicts. The option alone does not establish the policy-specific cause implied by the original question.

</details>

### 12. Which is NOT a runtime security best practice?

- A. Use RuntimeDefault after checking workload compatibility
- B. Verify Falco collection on supported nodes
- C. Run containers as root
- D. Use read-only root filesystem

<details>
<summary>Show Answer</summary>

**Answer: C. Run containers as root**

**Explanation:**
Reduce unnecessary root privileges. RuntimeDefault and readOnlyRootFilesystem still require workload/node compatibility. Falco DaemonSets cannot run on every node type such as Fargate. Feature enablement and healthy GuardDuty coverage are separate checks.

</details>
