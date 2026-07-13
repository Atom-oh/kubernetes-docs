# cert-manager Quiz

通过以下问题测试你对 cert-manager 和 Kubernetes 证书管理的理解。

---

## Questions

### 1. What is cert-manager's project status in the CNCF?

- A) Sandbox 项目
- B) Incubating 项目
- C) Graduated 项目
- D) Archived 项目

<details>
<summary>显示答案</summary>

**答案：C) Graduated 项目**

**解释：**
cert-manager 于 2022 年 11 月获得 CNCF Graduated 状态，使其成为 Kubernetes 最成熟且被广泛采用的证书管理解决方案之一。此状态表明该项目已满足治理、安全性和社区采用方面的严格要求。

</details>

---

### 2. Which component in cert-manager watches Certificate resources and triggers certificate issuance?

- A) cainjector
- B) webhook
- C) controller
- D) acmesolver

<details>
<summary>显示答案</summary>

**答案：C) controller**

**解释：**
cert-manager 由三个核心组件组成：
- **controller**：监视 Certificate resources，管理证书生命周期，并触发签发/续期
- **webhook**：通过 admission webhooks 验证并变更 cert-manager resources
- **cainjector**：将 CA bundles 注入 ValidatingWebhookConfiguration、MutatingWebhookConfiguration 和 CRD conversion webhooks

</details>

---

### 3. What is the key difference between Issuer and ClusterIssuer resources?

- A) Issuer 支持更多证书类型
- B) ClusterIssuer 是 namespace 作用域，而 Issuer 是 cluster 作用域
- C) Issuer 是 namespace 作用域，而 ClusterIssuer 是 cluster 作用域
- D) ClusterIssuer 仅适用于 ACME

<details>
<summary>显示答案</summary>

**答案：C) Issuer 是 namespace 作用域，而 ClusterIssuer 是 cluster 作用域**

**解释：**
```yaml
# Issuer - only issues certificates in its namespace
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: letsencrypt-prod
  namespace: my-app  # Only works in this namespace

# ClusterIssuer - issues certificates across all namespaces
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod  # No namespace - cluster-wide
```

对于组织范围的证书策略使用 ClusterIssuer；对于 namespace 特定配置使用 Issuer。

</details>

---

### 4. Which ACME challenge type supports wildcard certificate issuance?

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) HTTP-01 和 DNS-01 都支持

<details>
<summary>显示答案</summary>

**答案：B) DNS-01**

**解释：**
ACME challenge 类型及其能力：
- **HTTP-01**：通过 HTTP endpoint（端口 80）证明 domain control。不支持通配符。
- **DNS-01**：通过 DNS TXT records 证明 domain control。支持 wildcard certificates（*.example.com）。
- **TLS-ALPN-01**：通过 TLS（端口 443）证明 domain control。不支持通配符。

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
spec:
  acme:
    solvers:
    - dns01:
        route53:
          region: us-east-1
      selector:
        dnsNames:
        - "*.example.com"  # Wildcard requires DNS-01
```

</details>

---

### 5. In a Certificate resource, what does the secretName field specify?

- A) Issuer secret 的名称
- B) 已签发证书将存储到的 Kubernetes Secret
- C) CA certificate secret
- D) ACME account secret

<details>
<summary>显示答案</summary>

**答案：B) 已签发证书将存储到的 Kubernetes Secret**

**解释：**
secretName 字段指定 cert-manager 存储已签发证书的位置：

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: my-app-tls
  namespace: my-app
spec:
  secretName: my-app-tls-cert  # Certificate stored here
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - my-app.example.com
```

生成的 Secret 包含：
- `tls.crt`：证书链
- `tls.key`：私钥
- `ca.crt`：CA certificate（如果可用）

</details>

---

### 6. What is the primary use case for the AWS Private CA Issuer?

- A) 免费公共证书
- B) 用于私有/企业证书的内部 PKI
- C) DNS-01 challenge 自动化
- D) 证书吊销

<details>
<summary>显示答案</summary>

**答案：B) 用于私有/企业证书的内部 PKI**

**解释：**
AWS Private CA (PCA) Issuer 将 cert-manager 与 AWS Certificate Manager Private Certificate Authority 集成：

```yaml
apiVersion: awspca.cert-manager.io/v1beta1
kind: AWSPCAClusterIssuer
metadata:
  name: aws-pca-issuer
spec:
  arn: arn:aws:acm-pca:us-east-1:123456789:certificate-authority/abc-123
  region: us-east-1
```

使用场景：
- 内部 microservice mTLS
- 企业 PKI 合规要求
- 不暴露到公共互联网的私有证书
- 与现有 AWS PCA infrastructure 集成

</details>

---

### 7. What does trust-manager do in the cert-manager ecosystem?

- A) 验证证书签名
- B) 将 CA bundles 作为 ConfigMaps 或 Secrets 分发到各 namespaces
- C) 管理 ACME account registration
- D) 处理证书吊销

<details>
<summary>显示答案</summary>

**答案：B) 将 CA bundles 作为 ConfigMaps 或 Secrets 分发到各 namespaces**

**解释：**
trust-manager 是一个 cert-manager 子项目，用于分发受信任的 CA certificates：

```yaml
apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: my-ca-bundle
spec:
  sources:
  - useDefaultCAs: true           # Include system CAs
  - secret:
      name: "internal-ca"
      key: "ca.crt"
  target:
    configMap:
      key: "ca-certificates.crt"
    namespaceSelector:
      matchLabels:
        trust-bundle: enabled     # Distribute to labeled namespaces
```

这确保所有 application namespaces 中的 CA trust 保持一致。

</details>

---

### 8. What does the renewBefore field control in a Certificate resource?

- A) 最短有效期
- B) 在过期前多久 cert-manager 开始续期
- C) 最大续期尝试次数
- D) 续期检查间隔

<details>
<summary>显示答案</summary>

**答案：B) 在过期前多久 cert-manager 开始续期**

**解释：**
renewBefore 字段指定 cert-manager 何时开始续期流程：

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
spec:
  secretName: my-cert
  duration: 2160h    # 90 days validity
  renewBefore: 360h  # Renew 15 days before expiry
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - example.com
```

使用这些设置：
- 证书有效期为 90 天
- 续期在第 75 天开始（90 - 15 = 75）
- 为续期失败提供缓冲

</details>

---

### 9. What is the role of istio-csr in cert-manager's Istio integration?

- A) 验证 Istio configurations
- B) 使用 cert-manager 为 Istio service mesh 签发 workload certificates
- C) 仅管理 Istio gateway certificates
- D) 在 clusters 之间同步证书

<details>
<summary>显示答案</summary>

**答案：B) 使用 cert-manager 为 Istio service mesh 签发 workload certificates**

**解释：**
istio-csr 使用 cert-manager 替换 Istio 内置 CA（istiod），用于 workload identity：

```yaml
# istio-csr issues certificates for:
# - Workload mTLS (pod-to-pod)
# - Service mesh identity (SPIFFE)

# Configuration example
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: istiod
  namespace: istio-system
spec:
  secretName: istiod-tls
  issuerRef:
    name: istio-ca
    kind: ClusterIssuer
  isCA: true
```

优势：
- 集中式 PKI 管理
- 在 mesh 和 ingress 中保持一致的证书策略
- 与外部 CAs（Vault、AWS PCA）集成

</details>

---

### 10. What is a key difference between cert-manager and AWS Certificate Manager (ACM)?

- A) ACM 支持更多 issuers
- B) cert-manager 只能在 EKS 上运行
- C) cert-manager 以 Kubernetes Secrets 形式提供证书，ACM 将它们存储在 AWS 中
- D) ACM 支持更多证书类型

<details>
<summary>显示答案</summary>

**答案：C) cert-manager 以 Kubernetes Secrets 形式提供证书，ACM 将它们存储在 AWS 中**

**解释：**
cert-manager 与 AWS ACM 对比：

| Feature | cert-manager | AWS ACM |
|---------|--------------|---------|
| Storage | Kubernetes Secrets | AWS-managed |
| Private Key Access | Yes (in Secret) | No (AWS-only) |
| Use with Pods | Direct mounting | Not possible |
| Ingress Integration | Any ingress controller | ALB/NLB only |
| Multi-cloud | Yes | AWS only |
| Issuers | ACME, Vault, PCA, self-signed | Amazon, PCA |

在以下情况使用 cert-manager：
- 需要在 pods 内使用证书
- 需要 multi-cloud 可移植性
- 需要自定义 issuers
- 需要对 private keys 进行细粒度控制

</details>

---

## Score Calculation

- **9-10 correct**：优秀 - 你对 cert-manager 有深入理解。
- **7-8 correct**：良好 - 你扎实掌握了关键概念。
- **5-6 correct**：一般 - 有些领域需要进一步学习。
- **4 or fewer**：请再次查看文档。

## Related Documentation

- [使用 cert-manager 进行证书管理](../../security/10-cert-manager.md)
