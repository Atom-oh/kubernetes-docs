# Pod Security Standards Quiz

This quiz tests your understanding of Pod Security Standards (PSS), Pod Security Admission (PSA), and security profiles.

## Quiz Questions

### 1. Which is NOT one of the three security levels in Pod Security Standards (PSS)?

A. Privileged
B. Baseline
C. Hardened
D. Restricted

<details>
<summary>Show Answer</summary>

**Answer: C. Hardened**

**Explanation:**
Pod Security Standards defines three security levels:
- **Privileged**: Unrestricted, allows maximum privileges
- **Baseline**: Prevents known privilege escalation, minimal restrictions
- **Restricted**: Hardened security, applies Pod hardening best practices

Hardened is not an official PSS security level.

</details>

### 2. Which Pod Security Admission (PSA) mode blocks Pod creation when policy violations occur?

A. audit
B. warn
C. enforce
D. deny

<details>
<summary>Show Answer</summary>

**Answer: C. enforce**

**Explanation:**
PSA provides three modes:
- **enforce**: Rejects Pod creation on policy violation
- **audit**: Records violations in audit logs but allows
- **warn**: Shows warning message to user but allows

deny is not a valid PSA mode.

</details>

### 3. What label format is used to apply PSS to a namespace?

A. security.kubernetes.io/enforce: restricted
B. pod-security.kubernetes.io/enforce: restricted
C. pss.kubernetes.io/level: restricted
D. admission.kubernetes.io/policy: restricted

<details>
<summary>Show Answer</summary>

**Answer: B. pod-security.kubernetes.io/enforce: restricted**

**Explanation:**
PSA is configured through namespace labels:
```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

Label format: `pod-security.kubernetes.io/<MODE>: <LEVEL>`

</details>

### 4. Which is NOT allowed in the Baseline security level?

A. hostNetwork: true
B. runAsNonRoot: false
C. allowPrivilegeEscalation: true
D. readOnlyRootFilesystem: false

<details>
<summary>Show Answer</summary>

**Answer: A. hostNetwork: true**

**Explanation:**
Baseline level prevents known privilege escalation. The following are prohibited:
- hostNetwork, hostPID, hostIPC
- privileged containers
- Dangerous capabilities (cannot add except NET_RAW)
- hostPath volumes (except certain paths)

runAsNonRoot, allowPrivilegeEscalation, and readOnlyRootFilesystem are not restricted in Baseline; they are enforced in the Restricted level.

</details>

### 5. Which is NOT a requirement of the Restricted security level?

A. runAsNonRoot: true
B. allowPrivilegeEscalation: false
C. readOnlyRootFilesystem: true
D. capabilities.drop: ["ALL"]

<details>
<summary>Show Answer</summary>

**Answer: C. readOnlyRootFilesystem: true**

**Explanation:**
Restricted level requires:
- runAsNonRoot: true (required)
- allowPrivilegeEscalation: false (required)
- capabilities.drop: ["ALL"] (required)
- seccompProfile.type: RuntimeDefault or Localhost (required)

readOnlyRootFilesystem is a security best practice but is not a mandatory requirement of the Restricted level.

</details>

### 6. In which Kubernetes version was PodSecurityPolicy (PSP) removed?

A. 1.21
B. 1.23
C. 1.25
D. 1.27

<details>
<summary>Show Answer</summary>

**Answer: C. 1.25**

**Explanation:**
PSP Timeline:
- Kubernetes 1.21: PSP deprecation announced
- Kubernetes 1.22: PSA alpha introduced
- Kubernetes 1.23: PSA beta
- Kubernetes 1.25: PSP completely removed, PSA GA

</details>

### 7. What label applies a specific version of PSS in PSA?

A. pod-security.kubernetes.io/enforce-version: v1.28
B. pod-security.kubernetes.io/version: v1.28
C. pod-security.kubernetes.io/enforce-version: 1.28
D. pod-security.kubernetes.io/policy-version: 1.28

<details>
<summary>Show Answer</summary>

**Answer: A. pod-security.kubernetes.io/enforce-version: v1.28**

**Explanation:**
Version label format:
```yaml
pod-security.kubernetes.io/<MODE>-version: <VERSION>
```

Version values use `v1.XX` format or `latest`. Specifying a version uses the PSS definition from that Kubernetes version.

</details>

### 8. How do you enable PSA in EKS?

A. Need to install EKS add-on
B. Enabled by default
C. Enable with eksctl command
D. Configure in AWS console

<details>
<summary>Show Answer</summary>

**Answer: B. Enabled by default**

**Explanation:**
Pod Security Admission is enabled by default in Kubernetes 1.25+. In EKS 1.25 and later versions, PSA can be used without additional configuration. You only need to add appropriate labels to namespaces.

</details>

### 9. Which is NOT a method to configure PSA exemptions?

A. RuntimeClass exemption
B. User exemption
C. Namespace exemption
D. Pod label exemption

<details>
<summary>Show Answer</summary>

**Answer: D. Pod label exemption**

**Explanation:**
PSA supports the following exemption types:
- **usernames**: Exemptions for specific users
- **runtimeClassNames**: Exemptions for specific RuntimeClasses
- **namespaces**: Exemptions for specific namespaces

Pod label-based exemptions are not supported in PSA. Exemptions are configured through AdmissionConfiguration.

</details>

### 10. Which seccompProfile type is allowed in the Restricted level?

A. Unconfined
B. RuntimeDefault
C. Custom
D. Disabled

<details>
<summary>Show Answer</summary>

**Answer: B. RuntimeDefault**

**Explanation:**
seccompProfile types allowed in Restricted level:
- **RuntimeDefault**: Container runtime's default profile
- **Localhost**: Custom profile defined on the node

Unconfined is not allowed in the Restricted level. It disables seccomp filtering and poses security risks.

</details>

### 11. What is the recommended first step when migrating from PSP to PSA?

A. Delete PSP immediately
B. Apply enforce mode to all namespaces
C. Start with audit/warn mode to identify violations
D. Create a new cluster

<details>
<summary>Show Answer</summary>

**Answer: C. Start with audit/warn mode to identify violations**

**Explanation:**
Recommended PSA migration steps:
1. **Start with audit/warn mode**: Identify violations
2. **Fix workloads**: Resolve violations
3. **Switch to enforce mode**: Apply gradually
4. **Remove PSP**: After migration is complete

Immediately applying enforce mode can disrupt existing workloads.

</details>

### 12. What is restricted even in the Privileged level?

A. hostNetwork usage
B. privileged containers
C. Nothing (everything is allowed)
D. hostPath volumes

<details>
<summary>Show Answer</summary>

**Answer: C. Nothing (everything is allowed)**

**Explanation:**
Privileged level is completely unrestricted:
- All security context settings allowed
- hostNetwork, hostPID, hostIPC allowed
- privileged containers allowed
- All capabilities allowed
- All volume types allowed

This level is used for system and infrastructure workloads (e.g., CNI, storage drivers).

</details>
