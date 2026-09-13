# Pod Security Standards Quiz

> **Last Updated**: September 13, 2026
> **Related Document**: [Pod Security Standards](../../security/03-pod-security-standards.md)

Answer for ordinary Linux Pods; see the guide for version-specific Windows and user-namespace exceptions.

This quiz tests your understanding of Pod Security Standards (PSS), Pod Security Admission (PSA), and security profiles.

## Quiz Questions

### 1. Which is NOT one of the three security levels in Pod Security Standards (PSS)?

- A) Privileged
- B) Baseline
- C) Hardened
- D) Restricted

<details>
<summary>Show Answer</summary>

**Answer: C) Hardened**

**Explanation:**
Pod Security Standards defines three security levels:
- **Privileged**: Unrestricted, allows maximum privileges
- **Baseline**: Prevents known privilege escalation, minimal restrictions
- **Restricted**: Hardened security, applies Pod hardening best practices

Hardened is not an official PSS security level.

</details>

### 2. Which Pod Security Admission (PSA) mode blocks Pod creation when policy violations occur?

- A) audit
- B) warn
- C) enforce
- D) deny

<details>
<summary>Show Answer</summary>

**Answer: C) enforce**

**Explanation:**
PSA provides three modes:
- **enforce**: Rejects Pod creation on policy violation
- **audit**: Records violations in audit logs but allows
- **warn**: Shows warning message to user but allows

deny is not a valid PSA mode. Audit/warn do not themselves reject; enforce or other checks can still reject the same request. Audit retention requires appropriate log configuration.

</details>

### 3. What label format is used to apply PSS to a namespace?

- A) security.kubernetes.io/enforce: restricted
- B) pod-security.kubernetes.io/enforce: restricted
- C) pss.kubernetes.io/level: restricted
- D) admission.kubernetes.io/policy: restricted

<details>
<summary>Show Answer</summary>

**Answer: B) pod-security.kubernetes.io/enforce: restricted**

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

- A) hostNetwork: true
- B) runAsNonRoot: false
- C) allowPrivilegeEscalation: true
- D) readOnlyRootFilesystem: false

<details>
<summary>Show Answer</summary>

**Answer: A) hostNetwork: true**

**Explanation:**
Baseline level prevents known privilege escalation. The following are prohibited:
- hostNetwork, hostPID, hostIPC
- privileged containers
- Explicit capability additions outside the Baseline allowlist, including NET_RAW
- All hostPath volumes; built-in PSA provides no path allowlist

Baseline does not require runAsNonRoot or allowPrivilegeEscalation: false. Restricted adds those controls for the assumed Pod type. readOnlyRootFilesystem is recommended hardening, not a requirement of either profile. The capability check concerns explicit additions; it does not drop the runtime default set.

</details>

### 5. Which is NOT a requirement of the Restricted security level?

- A) runAsNonRoot: true
- B) allowPrivilegeEscalation: false
- C) readOnlyRootFilesystem: true
- D) capabilities.drop: ["ALL"]

<details>
<summary>Show Answer</summary>

**Answer: C) readOnlyRootFilesystem: true**

**Explanation:**
Restricted level requires:
- runAsNonRoot: true (required)
- allowPrivilegeEscalation: false (required)
- capabilities.drop: ["ALL"] (required)
- seccompProfile.type: RuntimeDefault or Localhost (required)

readOnlyRootFilesystem is a security best practice but is not a mandatory requirement of the Restricted level.

</details>

### 6. In which Kubernetes version was PodSecurityPolicy (PSP) removed?

- A) 1.21
- B) 1.23
- C) 1.25
- D) 1.27

<details>
<summary>Show Answer</summary>

**Answer: C) 1.25**

**Explanation:**
PSP Timeline:
- Kubernetes 1.21: PSP deprecation announced
- Kubernetes 1.22: PSA alpha introduced
- Kubernetes 1.23: PSA beta
- Kubernetes 1.25: PSP completely removed, PSA GA

</details>

### 7. What label applies a specific version of PSS in PSA?

- A) pod-security.kubernetes.io/enforce-version: v1.28
- B) pod-security.kubernetes.io/version: v1.28
- C) pod-security.kubernetes.io/enforce-version: 1.28
- D) pod-security.kubernetes.io/policy-version: 1.28

<details>
<summary>Show Answer</summary>

**Answer: A) pod-security.kubernetes.io/enforce-version: v1.28**

**Explanation:**
Version label format:
```yaml
pod-security.kubernetes.io/<MODE>-version: <VERSION>
```

Values use `v1.XX` or `latest`. Pinning selects the policy definition, not a Kubernetes upgrade. The v1.28 choice illustrates syntax; it omits controls introduced later. latest follows the API server version and can change on upgrade.

</details>

### 8. How do you enable PSA in EKS?

- A) Need to install EKS add-on
- B) Enabled by default
- C) Enable with eksctl command
- D) Configure in AWS console

<details>
<summary>Show Answer</summary>

**Answer: B) Enabled by default**

**Explanation:**
PSA reached GA and is enabled by default in upstream Kubernetes 1.25+. AWS documents EKS default enablement from 1.23, with permissive privileged/latest defaults and no static exemptions. Review actual namespace labels; add an appropriate policy rather than assuming enablement alone provides Baseline/Restricted enforcement.

</details>

### 9. Which is NOT a method to configure PSA exemptions?

- A) RuntimeClass exemption
- B) User exemption
- C) Namespace exemption
- D) Pod label exemption

<details>
<summary>Show Answer</summary>

**Answer: D) Pod label exemption**

**Explanation:**
PSA supports the following exemption types:
- **usernames**: Exemptions for specific users
- **runtimeClasses**: Exemptions for specific RuntimeClasses
- **namespaces**: Exemptions for specific namespaces

Pod labels do not create exemptions. Static exemption entries are exact names, not wildcard or group selectors. User exemptions match the request identity, not spec.serviceAccountName. EKS does not expose editing this control-plane configuration; choosing privileged namespace enforcement is different from a static exemption.

</details>

### 10. Which seccompProfile type is allowed in the Restricted level?

- A) Unconfined
- B) RuntimeDefault
- C) Custom
- D) Disabled

<details>
<summary>Show Answer</summary>

**Answer: B) RuntimeDefault**

**Explanation:**
seccompProfile types allowed in Restricted level:
- **RuntimeDefault**: Container runtime's default profile
- **Localhost**: Custom profile defined on the node

Unconfined is not allowed in the Restricted level. It disables seccomp filtering and poses security risks.

</details>

### 11. What is the recommended first step when migrating from PSP to PSA?

- A) Delete PSP immediately
- B) Apply enforce mode to all namespaces
- C) Start with audit/warn mode to identify violations
- D) Create a new cluster

<details>
<summary>Show Answer</summary>

**Answer: C) Start with audit/warn mode to identify violations**

**Explanation:**
Recommended PSA migration steps:
1. **Start with audit/warn mode**: Identify violations
2. **Fix workloads**: Resolve violations
3. **Switch to enforce mode**: Apply gradually
4. **Remove PSP**: After migration is complete

Existing running Pods are not evicted merely by relabeling. Their replacements or relevant updates can be denied, so a later rollout may stall. This PSP removal sequence is historical for clusters that still served PSP before v1.25.

</details>

<span id="_12-what-is-restricted-even-in-the-privileged-level"></span>

### 12. Which of these does the PSS Privileged profile itself prohibit?

- A) hostNetwork usage
- B) privileged containers
- C) None of these by PSS itself
- D) hostPath volumes

<details>
<summary>Show Answer</summary>

**Answer: C) None of these by PSS itself**

**Explanation:**
Privileged adds no PSS restrictions on these valid Pod fields:
- All security context settings allowed
- hostNetwork, hostPID, hostIPC allowed
- privileged containers allowed
- All capabilities allowed
- All volume types allowed

This does not grant IAM/RBAC permissions, bypass schema validation or other admission policies, or force privileged: true. Limit such namespaces to reviewed host-access components.

</details>
