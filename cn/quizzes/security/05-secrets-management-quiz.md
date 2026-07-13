# Secrets Management 测验

本测验测试你对 Kubernetes Secrets、AWS Secrets Manager、External Secrets Operator 和加密的理解。

## 测验问题

### 1. Kubernetes Secrets 的默认编码方式是什么？

A. AES-256 加密
B. Base64 编码
C. SHA-256 哈希
D. RSA 加密

<details>
<summary>显示答案</summary>

**答案：B. Base64 编码**

**解释：**
Kubernetes Secrets 默认使用 Base64 编码。Base64 是简单的编码，而不是加密，因此你应该启用 etcd 加密或使用外部 secrets 管理系统。

</details>

### 2. EKS 中用于 etcd 加密的 AWS 服务是哪一个？

A. AWS Secrets Manager
B. AWS KMS (Key Management Service)
C. AWS Certificate Manager
D. AWS CloudHSM

<details>
<summary>显示答案</summary>

**答案：B. AWS KMS (Key Management Service)**

**解释：**
EKS 使用 AWS KMS 来加密存储在 etcd 中的 Kubernetes Secrets。可以在创建集群期间或之后启用信封加密：
```bash
aws eks associate-encryption-config \
  --cluster-name my-cluster \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:..."}}]'
```

</details>

### 3. External Secrets Operator 中哪些资源会引用 AWS Secrets Manager secrets？

A. SecretStore
B. ExternalSecret
C. ClusterSecretStore
D. A 和 B 或 C 和 B

<details>
<summary>显示答案</summary>

**答案：D. A 和 B 或 C 和 B**

**解释：**
External Secrets Operator 组件：
- **SecretStore/ClusterSecretStore**：外部 secret store 连接设置
- **ExternalSecret**：实际的 secret 引用和 Kubernetes Secret 创建

SecretStore 是 namespace 作用域，ClusterSecretStore 是 cluster 作用域。

</details>

### 4. 以下哪一项不是在 Pod 中使用 Secrets 的方式？

A. 作为环境变量注入
B. 作为卷挂载
C. Image pull secrets
D. 转换为 ConfigMap

<details>
<summary>显示答案</summary>

**答案：D. 转换为 ConfigMap**

**解释：**
在 Pod 中使用 Secrets 的方式：
1. **环境变量**：`envFrom.secretRef` 或 `env.valueFrom.secretKeyRef`
2. **Volume mount**：作为文件挂载
3. **Image pull secrets**：`imagePullSecrets`

Secrets 不会自动转换为 ConfigMaps。它们是独立的资源。

</details>

### 5. AWS Secrets Manager 中用于配置自动轮换的 AWS 服务是哪一个？

A. AWS EventBridge
B. AWS Lambda
C. AWS Step Functions
D. AWS SNS

<details>
<summary>显示答案</summary>

**答案：B. AWS Lambda**

**解释：**
AWS Secrets Manager 自动轮换使用 Lambda 函数。AWS 为 RDS、Redshift 等提供预构建的轮换函数，也可以用 Lambda 实现自定义轮换。

</details>

### 6. Sealed Secrets 的主要特性是什么？

A. etcd 中的加密
B. 可以安全地存储在 Git 中
C. 仅限 AWS
D. 支持自动轮换

<details>
<summary>显示答案</summary>

**答案：B. 可以安全地存储在 Git 中**

**解释：**
Sealed Secrets 使用公钥加密 secrets，因此它们可以安全地存储在 Git 仓库中。只有集群中的 Sealed Secrets controller 才能使用私钥解密。它适用于 GitOps 工作流。

</details>

### 7. ExternalSecret 的 refreshInterval 字段有什么作用？

A. 设置 secret 过期时间
B. 设置与外部 secret 的同步间隔
C. 设置缓存保留时间
D. 设置重试间隔

<details>
<summary>显示答案</summary>

**答案：B. 设置与外部 secret 的同步间隔**

**解释：**
`refreshInterval` 定义 External Secrets Operator 与外部 secret store 同步的频率：
```yaml
spec:
  refreshInterval: 1h  # Sync every 1 hour
```

当 secrets 在外部发生变化时，Kubernetes Secret 会按照此间隔更新。

</details>

### 8. 当 Kubernetes Secret 的 immutable 字段设置为 true 时会发生什么？

A. Secret 无法被删除
B. Secret 无法被修改
C. Secret 无法被读取
D. Secret 无法被复制

<details>
<summary>显示答案</summary>

**答案：B. Secret 无法被修改**

**解释：**
`immutable: true` 设置会阻止 Secret 创建后的修改：
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
immutable: true
data:
  password: cGFzc3dvcmQ=
```

要更改它，你必须删除并重新创建 Secret。这可以防止意外更改并提升性能。

</details>

### 9. CSI Secrets Store Driver 的主要功能是什么？

A. 加密 etcd 中的 secrets
B. 将外部 secrets 作为卷挂载
C. 自动生成 secrets
D. 备份 secrets

<details>
<summary>显示答案</summary>

**答案：B. 将外部 secrets 作为卷挂载**

**解释：**
Secrets Store CSI Driver 会将来自 AWS Secrets Manager、Azure Key Vault 等的外部 secrets 直接作为 CSI volumes 挂载。Pods 可以在不创建 Kubernetes Secrets 的情况下使用 secrets。

</details>

### 10. 将 External Secrets 与 IRSA (IAM Roles for Service Accounts) 一起使用有什么优势？

A. 更快地访问 secret
B. 无需在 Pods 中硬编码 IAM 凭证
C. 自动 secret 轮换
D. 免费使用

<details>
<summary>显示答案</summary>

**答案：B. 无需在 Pods 中硬编码 IAM 凭证**

**解释：**
IRSA 允许将 IAM roles 附加到 Service Accounts。External Secrets Operator Pods 可以在没有 AWS 凭证的情况下安全访问 AWS Secrets Manager。这是一项安全最佳实践。

</details>

### 11. 使用 stringData 定义 Secret 数据的特征是什么？

A. 已加密
B. 不需要 Base64 编码
C. 更安全
D. 已压缩

<details>
<summary>显示答案</summary>

**答案：B. 不需要 Base64 编码**

**解释：**
`stringData` 字段允许用纯文本指定值：
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
stringData:
  password: mypassword  # Plain text, auto Base64 encoded
```

Kubernetes 会自动处理 Base64 编码。但是，查询时它会在 data 字段中显示为 Base64。

</details>

### 12. 以下哪一项不是 secrets 管理最佳实践？

A. 启用 etcd 加密
B. 使用 RBAC 限制 Secret 访问
C. 将 secrets 提交到源代码
D. 使用外部 secrets 管理系统

<details>
<summary>显示答案</summary>

**答案：C. 将 secrets 提交到源代码**

**解释：**
Secrets 管理最佳实践：
- 启用 etcd 加密
- 使用 RBAC 限制 Secret 访问
- 使用外部 secrets 管理系统（AWS Secrets Manager、HashiCorp Vault 等）
- 启用审计日志
- 定期轮换 secret

切勿将 secrets 提交到源代码。纯文本 secrets 会暴露在版本控制系统中。

</details>
