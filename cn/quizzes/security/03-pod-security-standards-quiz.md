# Pod Security Standards 测验

> **最后更新**: September 13, 2026
> **相关文档**: [Pod Security Standards](../../security/03-pod-security-standards.md)

请针对普通 Linux Pod 作答；有关特定版本的 Windows 和 user namespace 例外情况，请参阅指南。

本测验将测试你对 Pod Security Standards (PSS)、Pod Security Admission (PSA) 和安全配置文件的理解。

## 测验题目

### 1. 以下哪项不是 Pod Security Standards (PSS) 中的三个安全级别之一？

- A) Privileged
- B) Baseline
- C) Hardened
- D) Restricted

<details>
<summary>显示答案</summary>

**答案: C) Hardened**

**说明:**
Pod Security Standards 定义了三个安全级别：
- **Privileged**：不受限制，允许最大权限
- **Baseline**：防止已知的权限提升，限制最少
- **Restricted**：强化安全性，应用 Pod 加固最佳实践

Hardened 不是官方的 PSS 安全级别。

</details>

### 2. 当发生策略违规时，哪种 Pod Security Admission (PSA) 模式会阻止创建 Pod？

- A) audit
- B) warn
- C) enforce
- D) deny

<details>
<summary>显示答案</summary>

**答案: C) enforce**

**说明:**
PSA 提供三种模式：
- **enforce**：策略违规时拒绝创建 Pod
- **audit**：在审计日志中记录违规，但允许请求
- **warn**：向用户显示警告消息，但允许请求

deny 不是有效的 PSA 模式。audit/warn 本身不会拒绝请求；enforce 或其他检查仍可拒绝同一请求。audit 保留需要适当的日志配置。

</details>

### 3. 使用哪种标签格式将 PSS 应用于 namespace？

- A) security.kubernetes.io/enforce: restricted
- B) pod-security.kubernetes.io/enforce: restricted
- C) pss.kubernetes.io/level: restricted
- D) admission.kubernetes.io/policy: restricted

<details>
<summary>显示答案</summary>

**答案: B) pod-security.kubernetes.io/enforce: restricted**

**说明:**
通过 namespace 标签配置 PSA：
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

### 4. 以下哪项在 Baseline 安全级别中不被允许？

- A) hostNetwork: true
- B) runAsNonRoot: false
- C) allowPrivilegeEscalation: true
- D) readOnlyRootFilesystem: false

<details>
<summary>显示答案</summary>

**答案: A) hostNetwork: true**

**说明:**
Baseline 级别可防止已知的权限提升。以下内容被禁止：
- hostNetwork、hostPID、hostIPC
- privileged container
- Baseline 允许列表之外的显式 capability 添加，包括 NET_RAW
- 所有 hostPath volume；内置 PSA 不提供路径允许列表

Baseline 不要求 runAsNonRoot 或 allowPrivilegeEscalation: false。对于假定的 Pod 类型，Restricted 增加了这些控制项。readOnlyRootFilesystem 是推荐的加固措施，而非任一配置文件的要求。capability 检查针对显式添加；它不会移除运行时默认集合。

</details>

### 5. 以下哪项不是 Restricted 安全级别的要求？

- A) runAsNonRoot: true
- B) allowPrivilegeEscalation: false
- C) readOnlyRootFilesystem: true
- D) capabilities.drop: ["ALL"]

<details>
<summary>显示答案</summary>

**答案: C) readOnlyRootFilesystem: true**

**说明:**
Restricted 级别要求：
- runAsNonRoot: true（必需）
- allowPrivilegeEscalation: false（必需）
- capabilities.drop: ["ALL"]（必需）
- seccompProfile.type: RuntimeDefault 或 Localhost（必需）

readOnlyRootFilesystem 是一项安全最佳实践，但不是 Restricted 级别的强制要求。

</details>

### 6. PodSecurityPolicy (PSP) 在哪个 Kubernetes 版本中被移除？

- A) 1.21
- B) 1.23
- C) 1.25
- D) 1.27

<details>
<summary>显示答案</summary>

**答案: C) 1.25**

**说明:**
PSP 时间线：
- Kubernetes 1.21：宣布弃用 PSP
- Kubernetes 1.22：引入 PSA alpha
- Kubernetes 1.23：PSA beta
- Kubernetes 1.25：完全移除 PSP，PSA GA

</details>

### 7. 哪个标签可在 PSA 中应用特定版本的 PSS？

- A) pod-security.kubernetes.io/enforce-version: v1.28
- B) pod-security.kubernetes.io/version: v1.28
- C) pod-security.kubernetes.io/enforce-version: 1.28
- D) pod-security.kubernetes.io/policy-version: 1.28

<details>
<summary>显示答案</summary>

**答案: A) pod-security.kubernetes.io/enforce-version: v1.28**

**说明:**
版本标签格式：
```yaml
pod-security.kubernetes.io/<MODE>-version: <VERSION>
```

值使用 `v1.XX` 或 `latest`。固定版本选择的是策略定义，而不是 Kubernetes 升级。v1.28 选项用于说明语法；它不包含后续引入的控制项。latest 会跟随 API server 版本，并可能在升级时发生变化。

</details>

### 8. 如何在 EKS 中启用 PSA？

- A) 需要安装 EKS add-on
- B) 默认启用
- C) 使用 eksctl 命令启用
- D) 在 AWS console 中配置

<details>
<summary>显示答案</summary>

**答案: B) 默认启用**

**说明:**
PSA 已达到 GA，并在上游 Kubernetes 1.25+ 中默认启用。AWS 记录了 EKS 从 1.23 起默认启用，并采用宽松的 privileged/latest 默认值且没有静态豁免。请检查实际的 namespace 标签；应添加适当的策略，而不要假设仅启用 PSA 就能提供 Baseline/Restricted 强制执行。

</details>

### 9. 以下哪项不是配置 PSA 豁免的方法？

- A) RuntimeClass 豁免
- B) 用户豁免
- C) Namespace 豁免
- D) Pod 标签豁免

<details>
<summary>显示答案</summary>

**答案: D) Pod 标签豁免**

**说明:**
PSA 支持以下豁免类型：
- **usernames**：针对特定用户的豁免
- **runtimeClasses**：针对特定 RuntimeClass 的豁免
- **namespaces**：针对特定 namespace 的豁免

Pod 标签不会创建豁免。静态豁免条目是精确名称，而不是通配符或 group selector。用户豁免匹配请求身份，而不是 spec.serviceAccountName。EKS 不支持编辑此 control-plane 配置；选择 privileged namespace 强制执行与静态豁免不同。

</details>

### 10. Restricted 级别中允许哪种 seccompProfile 类型？

- A) Unconfined
- B) RuntimeDefault
- C) Custom
- D) Disabled

<details>
<summary>显示答案</summary>

**答案: B) RuntimeDefault**

**说明:**
Restricted 级别中允许的 seccompProfile 类型：
- **RuntimeDefault**：container runtime 的默认配置文件
- **Localhost**：在 node 上定义的自定义配置文件

Restricted 级别不允许 Unconfined。它会禁用 seccomp 过滤并带来安全风险。

</details>

### 11. 从 PSP 迁移到 PSA 时，建议的第一步是什么？

- A) 立即删除 PSP
- B) 对所有 namespace 应用 enforce 模式
- C) 先使用 audit/warn 模式来识别违规
- D) 创建一个新的 cluster

<details>
<summary>显示答案</summary>

**答案: C) 先使用 audit/warn 模式来识别违规**

**说明:**
推荐的 PSA 迁移步骤：
1. **先使用 audit/warn 模式**：识别违规
2. **修复 workload**：解决违规问题
3. **切换到 enforce 模式**：逐步应用
4. **移除 PSP**：迁移完成后

仅重新标记不会驱逐现有正在运行的 Pod。它们的替代 Pod 或相关更新可能会被拒绝，因此后续 rollout 可能会停滞。对于在 v1.25 之前仍提供 PSP 的 cluster，此 PSP 移除顺序具有历史意义。

</details>

<span id="_12-what-is-restricted-even-in-the-privileged-level"></span>

### 12. PSS Privileged 配置文件本身禁止以下哪项？

- A) hostNetwork 使用
- B) privileged container
- C) PSS 本身不禁止以上任何一项
- D) hostPath volume

<details>
<summary>显示答案</summary>

**答案: C) PSS 本身不禁止以上任何一项**

**说明:**
Privileged 不会对这些有效的 Pod 字段添加 PSS 限制：
- 允许所有 security context 设置
- 允许 hostNetwork、hostPID、hostIPC
- 允许 privileged container
- 允许所有 capability
- 允许所有 volume 类型

这并不会授予 IAM/RBAC 权限、绕过 schema validation 或其他 admission policy，也不会强制 privileged: true。此类 namespace 应仅限于经过审查的 host access component。

</details>
