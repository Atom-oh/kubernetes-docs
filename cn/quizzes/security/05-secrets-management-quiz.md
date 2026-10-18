# Secrets 管理测验

> **最后更新**：2026 年 9 月 13 日

本测验检验你对 Kubernetes Secrets、AWS Secrets Manager、External Secrets Operator 和加密的理解。

## 测验题目

### 1. Kubernetes Secret 默认采用哪种编码方式？

- A. AES-256 加密
- B. Base64 编码
- C. SHA-256 哈希
- D. RSA 加密

<details>
<summary>显示答案</summary>

**答案：B. Base64 编码**

**解释：**
序列化 Secret 的 `data` 字段使用 Base64。编码不等于加密。请保护 API 授权、存储和使用 Secret 的应用；改用外部存储并不会免除这些要求。

</details>

### 2. EKS 使用哪项 AWS 服务加密 etcd 中的数据？

- A. AWS Secrets Manager
- B. AWS KMS（Key Management Service）
- C. AWS Certificate Manager
- D. AWS CloudHSM

<details>
<summary>显示答案</summary>

**答案：B. AWS KMS（Key Management Service）**

**解释：**
EKS 1.28 及更高版本默认使用 AWS 拥有的密钥，对所有 Kubernetes API 数据进行 KMS 信封加密。也可以选择客户管理的密钥。这与自行管理 API Server 的配置不同；不要假设 EKS 默认以明文存储，或总是必须使用客户管理的密钥。

</details>

### 3. 在 External Secrets Operator 中，哪些资源会引用 AWS Secrets Manager 中的 secret？

- A. SecretStore
- B. ExternalSecret
- C. ClusterSecretStore
- D. A 与 B，或 C 与 B

<details>
<summary>显示答案</summary>

**答案：D. A 与 B，或 C 与 B**

**解释：**
SecretStore/ClusterSecretStore 描述 provider 的访问方式和身份；ExternalSecret 选择外部值并定义目标 Secret。命名空间级的 store 引用其所在命名空间中的 ServiceAccount。ClusterSecretStore 需要明确指定引用所在的命名空间，并受使用限制约束。

</details>

### 4. 以下哪项不是在 Pod 中使用 Secret 的方式？

- A. 注入为环境变量
- B. 挂载为卷
- C. 镜像拉取凭证
- D. 转换为 ConfigMap

<details>
<summary>显示答案</summary>

**答案：D. 转换为 ConfigMap**

**解释：**
Pod 可以通过键引用、卷和 `imagePullSecrets` 使用 Secret。ConfigMap 是另一种对象，不是保护 Secret 的机制。运行中的容器不会因 Secret 更新而刷新环境变量；卷的刷新和应用重新加载则是另外的问题。

</details>

<span id="_5-which-aws-service-is-used-to-configure-automatic-rotation-in-aws-secrets-manager"></span>

### 5. AWS Secrets Manager 中，哪项 AWS 服务会执行基于自定义 Lambda 的轮换函数？

- A. AWS EventBridge
- B. AWS Lambda
- C. AWS Step Functions
- D. AWS SNS

<details>
<summary>显示答案</summary>

**答案：B. AWS Lambda**

**解释：**
自定义 Lambda 轮换流程使用 Lambda 函数执行目标更新逻辑，并配置所需权限和网络访问。Secrets Manager 也提供托管轮换集成；并非所有轮换都使用由用户管理的 Lambda。ESO 会同步值，但不会自行轮换数据库凭证。

</details>

### 6. Sealed Secrets 的主要特点是什么？

- A. 在 etcd 中加密
- B. 可安全地存储在 Git 中
- C. 仅适用于 AWS
- D. 自动轮换

<details>
<summary>显示答案</summary>

**答案：B. 可安全地存储在 Git 中**

**解释：**
Sealed Secrets 使用受信任的证书加密值，以便将其存储在 Git 中。持有适用私钥的任何人（包括获授权的恢复操作人员）都能解密。元数据仍然可见；更新密钥不会轮换应用凭证，也不会删除 Git 中已有的密文。

</details>

### 7. ExternalSecret 的 `refreshInterval` 字段有什么作用？

- A. 设置 secret 的过期时间
- B. 设置与外部 secret 的同步间隔
- C. 设置缓存保留时间
- D. 设置重试间隔

<details>
<summary>显示答案</summary>

**答案：B. 设置与外部 secret 的同步间隔**

**解释：**
当 `refreshPolicy` 为 Periodic 且 `refreshInterval` 为正值时，ESO 会定期协调外部值。这不保证在某个期限内完成，也不同于 OnChange 或 CreatedOnce。还需要处理 provider 错误、退避重试和应用重新加载。

</details>

### 8. 将 Kubernetes Secret 的 `immutable` 字段设为 `true` 会怎样？

- A. Secret 不能删除
- B. Secret 数据不能修改
- C. Secret 不能读取
- D. Secret 不能复制

<details>
<summary>显示答案</summary>

**答案：B. Secret 数据不能修改**

**解释：**
`immutable` 会阻止修改 Secret 数据，且之后不能将它改回可变状态。元数据仍可修改，Secret 也仍可删除。替换正在使用的依赖项时，优先创建一个新名称的 Secret，并通过受控发布完成切换。

</details>

### 9. Secrets Store CSI Driver 的主要功能是什么？

- A. 加密 etcd 中的 secret
- B. 将外部 secret 挂载为卷
- C. 自动生成 secret
- D. 备份 secret

<details>
<summary>显示答案</summary>

**答案：B. 将外部 secret 挂载为卷**

**解释：**
Secrets Store CSI Driver 与受支持的 provider 会将外部值作为文件挂载。同步到 Kubernetes Secret 是可选功能，需要启用同步功能并有 Pod 挂载该卷。轮换、文件传播和应用重新加载各自仍需处理；平台支持情况也因环境而异。

</details>

### 10. 使用 IRSA（IAM Roles for Service Accounts）搭配 External Secrets 有什么优势？

- A. 更快地访问 secret
- B. 无需在 Pod 中硬编码 IAM 凭证
- C. 自动轮换 secret
- D. 免费使用

<details>
<summary>显示答案</summary>

**答案：B. 无需在 Pod 中硬编码 IAM 凭证**

**解释：**
IRSA 通过精确的角色信任绑定，将投射的身份令牌交换为临时 AWS 凭证。它避免硬编码长期访问密钥，但并非完全不使用凭证。ESO 的 Pod Identity 使用 controller 的身份，不能代替 `serviceAccountRef` 的身份模拟。

</details>

### 11. 使用 `stringData` 定义 Secret 数据有什么特点？

- A. 数据已加密
- B. 无需手动进行 Base64 编码
- C. 更安全
- D. 数据已压缩

<details>
<summary>显示答案</summary>

**答案：B. 无需手动进行 Base64 编码**

**解释：**
`stringData` 接收明文输入，无需手动进行 Base64 转换，之后会将值合并到 `data`。它既不提供加密，也不额外限制访问；获授权的读取者可以通过 API 读取数据表示。避免在纳入版本控制的 YAML 中写入真实值，并留意服务端应用（server-side apply）的限制。

</details>

### 12. 以下哪项不是 Secrets 管理的最佳实践？

- A. 启用 etcd 加密
- B. 使用 RBAC 限制 Secret 访问
- C. 将明文凭证提交到源代码
- D. 使用外部 Secrets 管理系统

<details>
<summary>显示答案</summary>

**答案：C. 将明文凭证提交到源代码**

**解释：**
切勿提交明文凭证或用于解密的私钥。经过加密的 SOPS/SealedSecret 文件，以及不含值的 ESO 引用，可以存储在 Git 中，但应审核接收方、保护密钥、测试恢复流程并实施访问控制。没有任何单一工具能保证安全或合规。

</details>

---

[Secrets 管理指南](../../security/05-secrets-management.md)
