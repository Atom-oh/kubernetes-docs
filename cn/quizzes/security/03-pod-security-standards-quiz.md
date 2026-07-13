# Pod Security Standards 测验

本测验测试你对 Pod Security Standards (PSS)、Pod Security Admission (PSA) 和安全配置文件的理解。

## 测验问题

### 1. 以下哪一项不是 Pod Security Standards (PSS) 中的三个安全级别之一？

A. Privileged
B. Baseline
C. Hardened
D. Restricted

<details>
<summary>显示答案</summary>

**答案：C. Hardened**

**解释：**
Pod Security Standards 定义了三个安全级别：
- **Privileged**：不受限制，允许最高权限
- **Baseline**：防止已知的权限提升，限制最少
- **Restricted**：强化安全，应用 Pod 加固最佳实践

Hardened 不是官方的 PSS 安全级别。

</details>

### 2. 当发生策略违规时，哪种 Pod Security Admission (PSA) 模式会阻止创建 Pod？

A. audit
B. warn
C. enforce
D. deny

<details>
<summary>显示答案</summary>

**答案：C. enforce**

**解释：**
PSA 提供三种模式：
- **enforce**：在策略违规时拒绝创建 Pod
- **audit**：在审计日志中记录违规但允许通过
- **warn**：向用户显示警告消息但允许通过

deny 不是有效的 PSA 模式。

</details>

### 3. 用于将 PSS 应用于 namespace 的标签格式是什么？

A. security.kubernetes.io/enforce: restricted
B. pod-security.kubernetes.io/enforce: restricted
C. pss.kubernetes.io/level: restricted
D. admission.kubernetes.io/policy: restricted

<details>
<summary>显示答案</summary>

**答案：B. pod-security.kubernetes.io/enforce: restricted**

**解释：**
PSA 通过 namespace 标签进行配置：
```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

标签格式：`pod-security.kubernetes.io/<MODE>: <LEVEL>`

</details>

### 4. Baseline 安全级别中不允许以下哪一项？

A. hostNetwork: true
B. runAsNonRoot: false
C. allowPrivilegeEscalation: true
D. readOnlyRootFilesystem: false

<details>
<summary>显示答案</summary>

**答案：A. hostNetwork: true**

**解释：**
Baseline 级别会防止已知的权限提升。以下内容被禁止：
- hostNetwork、hostPID、hostIPC
- privileged containers
- 危险的 capabilities（除 NET_RAW 外不能添加）
- hostPath volumes（特定路径除外）

runAsNonRoot、allowPrivilegeEscalation 和 readOnlyRootFilesystem 在 Baseline 中不受限制；它们在 Restricted 级别中强制执行。

</details>

### 5. 以下哪一项不是 Restricted 安全级别的要求？

A. runAsNonRoot: true
B. allowPrivilegeEscalation: false
C. readOnlyRootFilesystem: true
D. capabilities.drop: ["ALL"]

<details>
<summary>显示答案</summary>

**答案：C. readOnlyRootFilesystem: true**

**解释：**
Restricted 级别要求：
- runAsNonRoot: true（必需）
- allowPrivilegeEscalation: false（必需）
- capabilities.drop: ["ALL"]（必需）
- seccompProfile.type: RuntimeDefault 或 Localhost（必需）

readOnlyRootFilesystem 是一项安全最佳实践，但不是 Restricted 级别的强制要求。

</details>

### 6. PodSecurityPolicy (PSP) 是在哪个 Kubernetes 版本中被移除的？

A. 1.21
B. 1.23
C. 1.25
D. 1.27

<details>
<summary>显示答案</summary>

**答案：C. 1.25**

**解释：**
PSP 时间线：
- Kubernetes 1.21：宣布弃用 PSP
- Kubernetes 1.22：引入 PSA alpha
- Kubernetes 1.23：PSA beta
- Kubernetes 1.25：PSP 完全移除，PSA GA

</details>

### 7. 在 PSA 中，哪个标签用于应用特定版本的 PSS？

A. pod-security.kubernetes.io/enforce-version: v1.28
B. pod-security.kubernetes.io/version: v1.28
C. pod-security.kubernetes.io/enforce-version: 1.28
D. pod-security.kubernetes.io/policy-version: 1.28

<details>
<summary>显示答案</summary>

**答案：A. pod-security.kubernetes.io/enforce-version: v1.28**

**解释：**
版本标签格式：
```yaml
pod-security.kubernetes.io/<MODE>-version: <VERSION>
```

版本值使用 `v1.XX` 格式或 `latest`。指定版本会使用该 Kubernetes 版本中的 PSS 定义。

</details>

### 8. 如何在 EKS 中启用 PSA？

A. 需要安装 EKS add-on
B. 默认启用
C. 使用 eksctl command 启用
D. 在 AWS console 中配置

<details>
<summary>显示答案</summary>

**答案：B. 默认启用**

**解释：**
Pod Security Admission 在 Kubernetes 1.25+ 中默认启用。在 EKS 1.25 及更高版本中，PSA 无需额外配置即可使用。你只需向 namespaces 添加适当的标签。

</details>

### 9. 以下哪一项不是配置 PSA 豁免的方法？

A. RuntimeClass exemption
B. User exemption
C. Namespace exemption
D. Pod label exemption

<details>
<summary>显示答案</summary>

**答案：D. Pod label exemption**

**解释：**
PSA 支持以下豁免类型：
- **usernames**：针对特定用户的豁免
- **runtimeClassNames**：针对特定 RuntimeClasses 的豁免
- **namespaces**：针对特定 namespaces 的豁免

PSA 不支持基于 Pod label 的豁免。豁免通过 AdmissionConfiguration 进行配置。

</details>

### 10. Restricted 级别中允许哪种 seccompProfile 类型？

A. Unconfined
B. RuntimeDefault
C. Custom
D. Disabled

<details>
<summary>显示答案</summary>

**答案：B. RuntimeDefault**

**解释：**
Restricted 级别中允许的 seccompProfile 类型：
- **RuntimeDefault**：Container runtime 的默认配置文件
- **Localhost**：在 node 上定义的自定义配置文件

Unconfined 在 Restricted 级别中不允许。它会禁用 seccomp 过滤，并带来安全风险。

</details>

### 11. 从 PSP 迁移到 PSA 时，推荐的第一步是什么？

A. 立即删除 PSP
B. 对所有 namespaces 应用 enforce mode
C. 从 audit/warn mode 开始，以识别违规
D. 创建新的 cluster

<details>
<summary>显示答案</summary>

**答案：C. 从 audit/warn mode 开始，以识别违规**

**解释：**
推荐的 PSA 迁移步骤：
1. **从 audit/warn mode 开始**：识别违规
2. **修复 workloads**：解决违规
3. **切换到 enforce mode**：逐步应用
4. **移除 PSP**：迁移完成后

立即应用 enforce mode 可能会中断现有 workloads。

</details>

### 12. 即使在 Privileged 级别中，什么仍然受到限制？

A. hostNetwork usage
B. privileged containers
C. Nothing (everything is allowed)
D. hostPath volumes

<details>
<summary>显示答案</summary>

**答案：C. Nothing (everything is allowed)**

**解释：**
Privileged 级别完全不受限制：
- 允许所有 security context 设置
- 允许 hostNetwork、hostPID、hostIPC
- 允许 privileged containers
- 允许所有 capabilities
- 允许所有 volume types

此级别用于系统和基础设施 workloads（例如 CNI、storage drivers）。

</details>
