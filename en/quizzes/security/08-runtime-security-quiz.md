# Runtime Security Quiz

This quiz tests your understanding of Falco, Seccomp, AppArmor, eBPF-based security, and EKS runtime security.

## Quiz Questions

### 1. What technology does Falco use to detect runtime threats?

A. Network packet analysis
B. System call (syscall) monitoring
C. Log analysis
D. Memory scanning

<details>
<summary>Show Answer</summary>

**Answer: B. System call (syscall) monitoring**

**Explanation:**
Falco uses eBPF or kernel modules to monitor system calls at the kernel level. It detects activities like process execution, file access, and network connections in real-time.

</details>

### 2. What is the main function of Seccomp?

A. Network traffic filtering
B. Restrict system calls a process can make
C. File system encryption
D. User authentication

<details>
<summary>Show Answer</summary>

**Answer: B. Restrict system calls a process can make**

**Explanation:**
Seccomp (Secure Computing Mode) restricts the system calls a process can make using a whitelist approach. The process terminates if it attempts an unauthorized syscall.

</details>

### 3. What is the recommended default Seccomp profile in Kubernetes 1.27+?

A. Unconfined
B. RuntimeDefault
C. Localhost
D. Docker/default

<details>
<summary>Show Answer</summary>

**Answer: B. RuntimeDefault**

**Explanation:**
RuntimeDefault is the default Seccomp profile provided by the container runtime (containerd, CRI-O):
```yaml
securityContext:
  seccompProfile:
    type: RuntimeDefault
```

It provides an appropriate security level for most workloads.

</details>

### 4. What is the role of the priority field in Falco rules?

A. Determine rule execution order
B. Specify severity level of alerts
C. Set resource quota
D. Set log retention period

<details>
<summary>Show Answer</summary>

**Answer: B. Specify severity level of alerts**

**Explanation:**
The priority in Falco rules specifies the severity of detected events:
- EMERGENCY, ALERT, CRITICAL, ERROR
- WARNING, NOTICE, INFORMATIONAL, DEBUG

```yaml
- rule: Shell in Container
  priority: WARNING
```

</details>

### 5. What happens in AppArmor's complain mode?

A. Block all access
B. Only log policy violations
C. Disable profile
D. Send alerts only

<details>
<summary>Show Answer</summary>

**Answer: B. Only log policy violations**

**Explanation:**
AppArmor modes:
- **enforce**: Block and log on policy violation
- **complain**: Only log on policy violation (for debugging)
- **unconfined**: No profile applied

Complain mode is useful for testing new profiles.

</details>

### 6. What is NOT a threat detected by Amazon GuardDuty EKS Runtime Monitoring?

A. Cryptocurrency mining
B. Privilege escalation
C. Code quality issues
D. Container escape attempts

<details>
<summary>Show Answer</summary>

**Answer: C. Code quality issues**

**Explanation:**
GuardDuty EKS Runtime Monitoring detection types:
- PrivilegeEscalation
- Execution (malicious code)
- CryptoCurrency (mining)
- CredentialAccess
- DefenseEvasion

Code quality is a development quality issue, not a security threat.

</details>

### 7. What is the main function of Cilium Tetragon?

A. Container image scanning
B. eBPF-based security observability
C. Network policy management
D. Secrets management

<details>
<summary>Show Answer</summary>

**Answer: B. eBPF-based security observability**

**Explanation:**
Tetragon is Cilium's eBPF-based security observability tool:
- Process execution monitoring
- Network activity tracking
- File access monitoring
- Policy-based real-time response (e.g., process termination)

</details>

### 8. What condition detects shell execution inside a container in Falco?

A. container and shell_procs
B. spawned_process and container and shell_procs
C. exec and shell
D. process.name = bash

<details>
<summary>Show Answer</summary>

**Answer: B. spawned_process and container and shell_procs**

**Explanation:**
Falco rule example:
```yaml
- rule: Shell in Container
  condition: >
    spawned_process and
    container and
    shell_procs
  output: "Shell spawned in container"
  priority: WARNING
```

`spawned_process` means new process creation, `container` means container environment, `shell_procs` means shell processes (bash, sh, etc.).

</details>

### 9. How do you set a read-only root filesystem for a Pod?

A. readOnlyRootFilesystem: true
B. rootfs: readonly
C. filesystem.readonly: true
D. immutableRoot: true

<details>
<summary>Show Answer</summary>

**Answer: A. readOnlyRootFilesystem: true**

**Explanation:**
```yaml
securityContext:
  readOnlyRootFilesystem: true
```

This setting makes the container's root filesystem read-only, preventing malicious code from modifying files. Mount emptyDir volumes for paths that need write access.

</details>

### 10. What does the "Defense in Depth" strategy mean in runtime security?

A. Rely on a single security layer
B. Apply multiple overlapping security layers
C. Focus only on defense
D. Protect only external boundaries

<details>
<summary>Show Answer</summary>

**Answer: B. Apply multiple overlapping security layers**

**Explanation:**
Defense in Depth uses multiple security layers:
1. Build time: Image scanning, vulnerability analysis
2. Deploy time: Admission Control, PSS/PSA
3. Runtime: Falco, Seccomp, AppArmor

If one layer is breached, other layers provide protection.

</details>

### 11. What command shows traffic blocked by policies in Hubble?

A. hubble observe --blocked
B. hubble observe --verdict DROPPED
C. hubble observe --denied
D. hubble observe --policy-violation

<details>
<summary>Show Answer</summary>

**Answer: B. hubble observe --verdict DROPPED**

**Explanation:**
```bash
hubble observe --verdict DROPPED
```

`--verdict DROPPED` filters traffic denied by network policies. You can monitor and analyze policy violations in real-time.

</details>

### 12. Which is NOT a runtime security best practice?

A. Apply RuntimeDefault Seccomp to all workloads
B. Deploy Falco as DaemonSet on all nodes
C. Run containers as root
D. Use read-only root filesystem

<details>
<summary>Show Answer</summary>

**Answer: C. Run containers as root**

**Explanation:**
Runtime security best practices:
- Apply RuntimeDefault Seccomp
- Deploy Falco
- Read-only root filesystem
- **Run as non-root user** (runAsNonRoot: true)
- Remove unnecessary capabilities
- Enable GuardDuty runtime monitoring

Running as root is dangerous because container escape gives elevated privileges on the host.

</details>
