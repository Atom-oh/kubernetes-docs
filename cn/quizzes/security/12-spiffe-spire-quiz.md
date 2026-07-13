# SPIFFE/SPIRE 测验

通过以下问题测试你对 SPIFFE/SPIRE workload identity（工作负载身份）的理解。

---

## 问题

### 1. SPIFFE ID 的正确格式是什么？

- A) spiffe://workload/trust-domain/path
- B) spiffe://trust-domain/path
- C) trust-domain://spiffe/path
- D) https://spiffe/trust-domain/path

<details>
<summary>显示答案</summary>

**答案：B) spiffe://trust-domain/path**

**解释：**
SPIFFE ID 格式是具有以下结构的 URI：

```
spiffe://trust-domain/path
```

示例：
```
spiffe://example.org/ns/production/sa/frontend
spiffe://cluster.local/k8s/ns/default/pod/nginx-abc123
spiffe://acme.com/region/us-east-1/service/payment
```

组成部分：
- **spiffe://**：必需的 scheme
- **trust-domain**：组织的 identity namespace（例如 example.org）
- **path**：workload 的分层标识符

</details>

---

### 2. X.509-SVID 和 JWT-SVID 的关键区别是什么？

- A) X.509-SVID 用于认证，JWT-SVID 用于授权
- B) X.509-SVID 用于 mTLS 连接，JWT-SVID 用于 API 认证
- C) 它们在功能上完全相同
- D) X.509-SVID 比 JWT-SVID 过期更快

<details>
<summary>显示答案</summary>

**答案：B) X.509-SVID 用于 mTLS 连接，JWT-SVID 用于 API 认证**

**解释：**
SPIFFE 支持两种 SVID（SPIFFE Verifiable Identity Document）类型：

**X.509-SVID：**
- 用于 mTLS（mutual TLS）连接
- 在 SAN（Subject Alternative Name）URI 中包含 SPIFFE ID
- 生命周期较长（数小时到数天）
- 最适合：Service-to-service mTLS

**JWT-SVID：**
- 用于 API 认证（HTTP headers）
- 在 `sub` claim 中包含 SPIFFE ID
- 生命周期较短（分钟级）
- 最适合：REST APIs、serverless、跨网络调用

```yaml
# X.509-SVID use case
service-a --mTLS--> service-b

# JWT-SVID use case
service-a --HTTP + JWT Bearer--> API Gateway
```

</details>

---

### 3. SPIRE Server 的主要角色是什么？

- A) 运行 workloads
- B) 签发 SVIDs 并管理 workload 注册
- C) 对流量进行负载均衡
- D) 存储应用程序 secrets

<details>
<summary>显示答案</summary>

**答案：B) 签发 SVIDs 并管理 workload 注册**

**解释：**
SPIRE Server 的职责：

```
┌─────────────────────────────────────────────┐
│              SPIRE Server                    │
├─────────────────────────────────────────────┤
│  - Manages trust domain CA                   │
│  - Issues X.509 and JWT SVIDs               │
│  - Stores workload registration entries     │
│  - Performs node attestation                │
│  - Maintains federation relationships       │
└─────────────────────────────────────────────┘
                    │
         ┌─────────┴─────────┐
         ▼                   ▼
   SPIRE Agent          SPIRE Agent
     (Node 1)             (Node 2)
```

关键功能：
- trust domain 的 Certificate Authority
- workload 条目的注册 API
- node 和 workload attestation 验证
- SVID 签名与轮换

</details>

---

### 4. SPIRE Agent 的主要角色是什么？

- A) 管理 cluster 网络
- B) 在 nodes 上运行，以 attestation workloads 并在本地交付 SVIDs
- C) 存储 cluster secrets
- D) 调度 pods

<details>
<summary>显示答案</summary>

**答案：B) 在 nodes 上运行，以 attestation workloads 并在本地交付 SVIDs**

**解释：**
SPIRE Agent 作为 DaemonSet 在每个 node 上运行：

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: spire-agent
  namespace: spire
spec:
  template:
    spec:
      containers:
      - name: spire-agent
        image: ghcr.io/spiffe/spire-agent:1.8
        volumeMounts:
        - name: spire-agent-socket
          mountPath: /run/spire/sockets
```

Agent 职责：
- 向 SPIRE Server 进行 attestation（node attestation）
- 验证本地 workload identity（workload attestation）
- 从 Server 获取并缓存 SVIDs
- 向本地 workloads 暴露 Workload API（Unix domain socket）
- 处理 SVID 轮换

</details>

---

### 5. Amazon EKS 推荐使用哪种 node attestation 方法？

- A) aws_iid
- B) k8s_sat
- C) k8s_psat
- D) join_token

<details>
<summary>显示答案</summary>

**答案：C) k8s_psat**

**解释：**
Kubernetes 的 node attestation 方法：

**k8s_psat (Projected Service Account Token)** - 推荐用于 EKS：
```yaml
# SPIRE Server configuration
nodeAttestor "k8s_psat" {
    plugin_data {
        clusters = {
            "eks-cluster" = {
                service_account_allow_list = ["spire:spire-agent"]
                kube_config_file = ""
                allowed_node_label_keys = ["topology.kubernetes.io/zone"]
            }
        }
    }
}
```

为什么在 EKS 中使用 k8s_psat：
- 使用 projected service account tokens（更安全）
- Tokens 绑定 audience 且有时间限制
- 可与 EKS OIDC provider 配合使用
- Agents 上不需要 cloud provider credentials

替代方案：
- **k8s_sat**：Legacy service account tokens（安全性较低）
- **aws_iid**：EC2 instance identity（用于非 EKS）

</details>

---

### 6. k8s workload attestation 支持哪些 selector 类型？

- A) 仅 Container image
- B) Namespace、service account、pod labels 和 container image
- C) 仅 IP address
- D) 仅 Node name

<details>
<summary>显示答案</summary>

**答案：B) Namespace、service account、pod labels 和 container image**

**解释：**
Kubernetes workload attestation selectors：

```bash
# Create registration entry with selectors
spire-server entry create \
    -spiffeID spiffe://example.org/ns/production/sa/frontend \
    -parentID spiffe://example.org/agent/node1 \
    -selector k8s:ns:production \
    -selector k8s:sa:frontend \
    -selector k8s:pod-label:app:frontend \
    -selector k8s:container-image:nginx:1.25
```

可用 selectors：
| Selector | Example | Description |
|----------|---------|-------------|
| k8s:ns | k8s:ns:production | Namespace |
| k8s:sa | k8s:sa:frontend | ServiceAccount |
| k8s:pod-label | k8s:pod-label:app:web | Pod labels |
| k8s:container-image | k8s:container-image:nginx | Container image |
| k8s:pod-name | k8s:pod-name:nginx-xyz | Specific pod |
| k8s:pod-uid | k8s:pod-uid:abc-123 | Pod UID |

</details>

---

### 7. SPIFFE CSI Driver 的用途是什么？

- A) 管理 persistent volumes
- B) 无需 sidecars，直接将 SVIDs 挂载到 pods 中
- C) 加密 node storage
- D) Network policy enforcement

<details>
<summary>显示答案</summary>

**答案：B) 无需 sidecars，直接将 SVIDs 挂载到 pods 中**

**解释：**
SPIFFE CSI Driver 提供了一种无需 sidecar 的 SVID 交付方式：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-workload
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: spiffe
      mountPath: /run/spiffe/certs
      readOnly: true
  volumes:
  - name: spiffe
    csi:
      driver: "csi.spiffe.io"
      readOnly: true
```

优势：
- 不需要 sidecar container
- SVIDs 会自动作为文件挂载
- 透明的 certificate rotation
- 降低 pod 复杂度
- 可与任何期望使用 file-based certificates 的应用程序配合使用

CSI driver 与 SPIRE Agent 通信，以获取并挂载 SVIDs。

</details>

---

### 8. SPIFFE Federation 支持什么？

- A) Database replication
- B) 独立 SPIFFE deployments 之间的跨 trust-domain 通信
- C) 跨 clusters 调度 Pod
- D) Secret synchronization

<details>
<summary>显示答案</summary>

**答案：B) 独立 SPIFFE deployments 之间的跨 trust-domain 通信**

**解释：**
SPIFFE Federation 允许不同 trust domains 中的 workloads 相互认证：

```
┌─────────────────────┐      Federation      ┌─────────────────────┐
│  Trust Domain A     │◄──────────────────►│  Trust Domain B      │
│  example.org        │     Bundle Exchange │  partner.com         │
├─────────────────────┤                      ├─────────────────────┤
│  spiffe://example.  │                      │  spiffe://partner.   │
│  org/service/api    │   ─── mTLS ───►     │  com/service/db      │
└─────────────────────┘                      └─────────────────────┘
```

配置：
```yaml
# SPIRE Server federation config
federatesWith "partner.com" {
    bundleEndpointURL = "https://spire.partner.com:8443"
    bundleEndpointProfile "https_spiffe" {
        endpointSPIFFEID = "spiffe://partner.com/spire/server"
    }
}
```

使用场景：
- Multi-cloud deployments
- Partner integrations
- Mergers and acquisitions
- 跨组织的 zero-trust 通信

</details>

---

### 9. SPIFFE/SPIRE 与 IAM Roles for Service Accounts (IRSA) 相比如何？

- A) IRSA 是平台无关的，SPIFFE 仅适用于 AWS
- B) SPIFFE 提供平台无关的 identity，IRSA 是 AWS 特定的
- C) 它们是完全相同的技术
- D) SPIFFE 仅适用于 Azure

<details>
<summary>显示答案</summary>

**答案：B) SPIFFE 提供平台无关的 identity，IRSA 是 AWS 特定的**

**解释：**
SPIFFE/SPIRE 与 IRSA 对比：

| Feature | SPIFFE/SPIRE | IRSA |
|---------|--------------|------|
| Platform | Any (multi-cloud) | AWS only |
| Identity Format | SPIFFE ID (URI) | IAM Role ARN |
| Credential Type | X.509/JWT SVID | AWS STS token |
| Service-to-Service | Native mTLS | Not supported |
| AWS Service Access | Via JWT exchange | Direct |
| Setup Complexity | Higher | Lower (EKS native) |

何时使用：
- **IRSA**：访问 AWS services 的 AWS-native workloads
- **SPIFFE/SPIRE**：Multi-cloud、service mesh、mTLS 需求

你可以同时使用两者：
```
Pod --SPIFFE--> Service Mesh (mTLS)
Pod --IRSA--> AWS Services (S3, DynamoDB)
```

</details>

---

### 10. SPIFFE 中 trust domain 命名的最佳实践是什么？

- A) 使用随机字符串
- B) 使用 IP addresses
- C) 使用组织控制的 DNS-style names
- D) 使用连续数字

<details>
<summary>显示答案</summary>

**答案：C) 使用组织控制的 DNS-style names**

**解释：**
Trust domain 命名最佳实践：

**推荐模式：**
```
# Organization domain
spiffe://example.com/...

# Environment-specific
spiffe://prod.example.com/...
spiffe://staging.example.com/...

# Region-specific
spiffe://us-east.example.com/...
```

**最佳实践：**
1. 使用你拥有的 domains（防止冲突）
2. 保持 trust domains 稳定（更改会造成中断）
3. 考虑 environment separation
4. 从一开始就规划 federation

**应避免的反模式：**
```
# Bad: Generic names
spiffe://cluster/...
spiffe://kubernetes/...

# Bad: Temporary names
spiffe://test123/...

# Bad: IP addresses
spiffe://10.0.0.1/...
```

Trust domain names 会出现在所有 SVIDs 和日志中，因此请选择有意义且稳定的标识符。

</details>

---

## 分数计算

- **9-10 correct**：优秀 - 你对 SPIFFE/SPIRE 有深入理解。
- **7-8 correct**：良好 - 你扎实掌握了关键概念。
- **5-6 correct**：一般 - 还有一些领域需要进一步学习。
- **4 or fewer**：请再次查看文档。

## 相关文档

- [使用 SPIFFE/SPIRE 实现 Workload Identity](../../security/12-spiffe-spire.md)
