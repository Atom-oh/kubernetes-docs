# Security Quiz

本测验测试你对 Kubernetes 安全概念的理解，包括 authentication、authorization、network policies、security contexts 和 secret management。

## Multiple Choice Questions

1. Kubernetes 不支持以下哪种用户 authentication 方法？
   - A) X.509 certificates
   - B) Service account tokens
   - C) OAuth tokens
   - D) 内置用户数据库
   
<details>
<summary>显示答案</summary>

**答案：D) 内置用户数据库**

**解释：**
Kubernetes 不提供内置用户数据库。相反，它支持 X.509 certificates、service account tokens、OAuth tokens、OpenID Connect tokens 和 webhook token authentication 等 authentication 方法。用户管理通常通过与外部系统（例如 LDAP、Active Directory）集成来完成。
</details>

2. 以下哪项不是 Kubernetes 中 RBAC (Role-Based Access Control) 的主要组件？
   - A) Role
   - B) ClusterRole
   - C) RoleBinding
   - D) SecurityPolicy
   
<details>
<summary>显示答案</summary>

**答案：D) SecurityPolicy**

**解释：**
Kubernetes RBAC 的主要组件是 Role、ClusterRole、RoleBinding 和 ClusterRoleBinding。Role 和 ClusterRole 定义权限集合，而 RoleBinding 和 ClusterRoleBinding 将这些权限与 users、groups 或 service accounts 关联。SecurityPolicy 不是 RBAC 组件；类似资源包括 PodSecurityPolicy（现已弃用）或 PodSecurityStandard。
</details>

3. 在 Kubernetes 中，以下哪项不能通过 Pod 的 Security Context 配置？
   - A) Container user ID (UID)
   - B) Container group ID (GID)
   - C) Container network policy
   - D) Container privilege escalation capability
   
<details>
<summary>显示答案</summary>

**答案：C) Container network policy**

**解释：**
Security Context 在 Pod 或 container 级别定义 privilege 和 access control 设置。这包括 user ID (runAsUser)、group ID (runAsGroup)、privilege escalation capability (allowPrivilegeEscalation)、privileged containers (privileged) 和 capabilities。但是，network policies 是通过单独的 NetworkPolicy 资源定义的，而不是通过 Security Context 定义。
</details>

4. Kubernetes 中 ServiceAccount 的主要用途是什么？
   - A) 为集群外部的用户提供 authentication
   - B) 为 pods 提供与 API server 通信的 identity
   - C) 加密 nodes 之间的通信
   - D) 授予 cluster administrator 权限
   
<details>
<summary>显示答案</summary>

**答案：B) 为 pods 提供与 API server 通信的 identity**

**解释：**
Service accounts 为运行在 pods 内的进程提供 identity，使其能够与 Kubernetes API server 通信。每个 namespace 都有一个默认 service account，除非明确另行指定，否则 pods 会使用该默认 service account。Service accounts 可以与 RBAC 结合使用，以限制 pods 可以执行的操作。
</details>

5. Kubernetes 中 NetworkPolicy 的主要用途是什么？
   - A) 将流量从集群外部路由到内部
   - B) 控制和限制 pods 之间的通信
   - C) 加密 nodes 之间的通信
   - D) 提供 service discovery
   
<details>
<summary>显示答案</summary>

**答案：B) 控制和限制 pods 之间的通信**

**解释：**
NetworkPolicy 提供了一种控制多组 pods 之间通信的方式。通过它，你可以指定哪些 pods 可以与哪些其他 pods 通信，以及可以使用哪些 ports 和 protocols。Network policies 对于精细控制 service-to-service 通信以及提升 microservice architectures 中的安全性非常重要。
</details>

6. 在 Pod Security Standards 的三个 policy levels 中，哪一个限制最严格？
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>显示答案</summary>

**答案：C) Restricted**

**解释：**
Pod Security Standards 定义了三个 policy levels：
  - Privileged：无限制，允许所有 privileges
  - Baseline：防止已知的 privilege escalation 路径
  - Restricted：应用增强安全设置的最严格 policy

Restricted policy 限制最严格，它遵循最小权限原则并应用安全最佳实践。此 policy 禁止 privileged containers、host namespace sharing、host path mounts 等。
</details>

7. 保护 Kubernetes 中 Secret 数据的最有效方法是什么？
   - A) Base64 encoding
   - B) etcd encryption configuration
   - C) Namespace isolation
   - D) 添加 labels
   
<details>
<summary>显示答案</summary>

**答案：B) etcd encryption configuration**

**解释：**
Kubernetes 中的 Secret 数据默认以 Base64 编码形式存储，但这只是简单编码，而不是加密。使用 etcd encryption configuration 会在 Secret 数据存储到 etcd 之前对其加密，从而保护敏感信息，避免未经授权访问 etcd 数据库。Namespace isolation 和 labels 可以帮助进行 access control，但不能保护数据本身。
</details>

8. 以下哪项不是增强 Kubernetes 中 container image 安全性的方法？
   - A) Image vulnerability scanning
   - B) 使用 trusted registries
   - C) Image signing and verification
   - D) 向 containers 授予 root privileges
   
<details>
<summary>显示答案</summary>

**答案：D) 向 containers 授予 root privileges**

**解释：**
向 containers 授予 root privileges 会削弱安全性。增强 container image 安全性的方法包括 image vulnerability scanning、使用 trusted registries、image signing and verification、应用最小权限原则、移除不必要的软件包，以及以 non-root users 身份运行 containers。
</details>

9. Kubernetes 中 Audit Logging 的主要用途是什么？
   - A) 收集 pod logs
   - B) 记录 API server requests
   - C) 监控 node status
   - D) 分析 network traffic
   
<details>
<summary>显示答案</summary>

**答案：B) 记录 API server requests**

**解释：**
Audit logging 是一种记录发送到 Kubernetes API server 的 requests 的机制。这可以追踪集群中谁做了什么，对于 security incident investigation、compliance requirements 和 troubleshooting 很有用。Audit logs 可以包含 request time、user、request content 和 response 等信息。
</details>

10. 以下哪项不是 Kubernetes 中 privileged containers 的特征？
    - A) 访问所有 host devices
    - B) 使用 host network stack
    - C) 能够加载 host kernel modules
    - D) 自动访问其他 namespaces 中的资源
    
<details>
<summary>显示答案</summary>

**答案：D) 自动访问其他 namespaces 中的资源**

**解释：**
Privileged containers 几乎可以访问所有 host capabilities，但它们不会自动拥有访问其他 Kubernetes namespaces 中资源的权限。跨 namespace 访问由 RBAC permissions 控制。Privileged containers 可以访问 host devices、network stack、kernel modules 等，因此会带来显著的安全风险，所以只应在绝对必要时使用。
</details>

## Short Answer Questions

1. Kubernetes RBAC 中 'Role' 和 'ClusterRole' 的主要区别是什么？

<details>
<summary>显示答案</summary>

**答案：**
Role 只在特定 namespace 内定义并应用权限，而 ClusterRole 在整个集群范围内应用，并定义跨所有 namespaces 的权限。ClusterRole 还用于定义非 namespace 级资源（nodes、PVs 等）的权限。
</details>

2. 解释在 Kubernetes 中应用“最小权限原则”的三种方法。

<details>
<summary>显示答案</summary>

**答案：**
1. 使用 RBAC 仅授予最低限度的必要权限
2. 在 Pod security context 中以 non-root users 运行 containers
3. 使用 network policies 仅允许必要通信
4. 限制使用 privileged containers
5. 限制 container capabilities
6. 应用 Pod Security Standards Restricted profile

（只需解释以上三项）
</details>

3. 从安全角度看，Kubernetes 中 Secret 和 ConfigMap 的主要区别是什么？

<details>
<summary>显示答案</summary>

**答案：**
Secret 用于存储敏感信息（passwords、tokens、keys 等），而 ConfigMap 用于存储通用配置数据。Secrets 以 Base64 编码形式存储（默认不加密），可以配置为仅挂载在内存中，并且只在 pods 创建时被引用。不过，如果没有额外配置，两者都会以 plaintext 形式存储在 etcd 中，因此需要 etcd encryption settings 才能实现完整安全性。
</details>

4. Kubernetes 中 'service account token volume projection' 的目的和好处是什么？

<details>
<summary>显示答案</summary>

**答案：**
Service account token volume projection 为挂载到 pods 的 service account tokens 提供额外的安全特性，例如时间限制和 audience restrictions。这可以限制 token lifetime，并确保只有特定 API servers 接受该 token，从而在 token 泄露时降低风险。此外，tokens 会自动续期，避免长期运行的 applications 出现 authentication 问题。
</details>

5. Kubernetes 中的 'container sandboxing' 是什么，可以使用哪些技术来实现？

<details>
<summary>显示答案</summary>

**答案：**
Container sandboxing 是一种通过将 containers 与 host system 以及其他 containers 隔离来增强安全性的技术。用于实现它的技术包括：
1. Linux namespaces and cgroups：提供基础 container isolation
2. seccomp：限制 system calls
3. AppArmor/SELinux：Mandatory access control
4. gVisor：通过 user-space kernel implementation 提供额外隔离
5. Kata Containers：使用 lightweight VMs 实现 hardware-level isolation
6. Firecracker：基于 MicroVM 的隔离

这些技术限制 containers 对 host system 可能产生的影响，并降低 container escape attacks 的风险。
</details>

## Hands-on Questions

1. 创建满足以下要求的 RBAC 资源：
   - 一个可以读取 'monitoring' namespace 中 pods 的 Role
   - 一个将此 Role 绑定到 'monitoring-team' service account 的 RoleBinding

<details>
<summary>显示答案</summary>

**答案：**

```yaml
# monitoring-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: monitoring
  name: pod-reader
rules:
  - apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
---
# monitoring-rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: monitoring
subjects:
- kind: ServiceAccount
  name: monitoring-team
  namespace: monitoring
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

应用方法：
```bash
kubectl apply -f monitoring-role.yaml
kubectl apply -f monitoring-rolebinding.yaml
```
</details>

2. 创建满足以下要求的 NetworkPolicy：
   - 应用于 'backend' namespace 中的所有 pods
   - 仅允许来自 'frontend' namespace 中 pods、端口 8080 上的 incoming traffic
   - 允许所有 outgoing traffic

<details>
<summary>显示答案</summary>

**答案：**

```yaml
# backend-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend
  namespace: backend
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - {}  # Allow all outgoing traffic
```

应用方法：
```bash
kubectl apply -f backend-network-policy.yaml
```

注意：要让此 NetworkPolicy 生效，'frontend' namespace 必须具有 'name: frontend' label。如果没有，请使用以下命令添加：
```bash
kubectl label namespace frontend name=frontend
```
</details>

3. 创建一个具有以下 security context 要求的 Pod：
   - Container 以 UID 1000 运行
   - 不允许 privilege escalation
   - Read-only root filesystem

<details>
<summary>显示答案</summary>

**答案：**

```yaml
# secure-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: secure-container
    image: nginx
    securityContext:
      runAsUser: 1000
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
```

应用方法：
```bash
kubectl apply -f secure-pod.yaml
```
</details>

4. 创建一个 Secret 并将其作为 volume 挂载到 Pod，要求如下：
   - Secret 名为 'db-credentials'
   - 包含 'username=admin' 和 'password=s3cr3t'
   - 挂载到 Pod 中的 '/etc/db-credentials' 路径

<details>
<summary>显示答案</summary>

**答案：**

创建 Secret：
```bash
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=s3cr3t
```

或以 YAML 形式：
```yaml
# db-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # base64 encoding of 'admin'
  password: czNjcjN0  # base64 encoding of 's3cr3t'
```

挂载到 Pod：
```yaml
# pod-with-secret.yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-secret
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: secret-volume
      mountPath: "/etc/db-credentials"
      readOnly: true
  volumes:
  - name: secret-volume
    secret:
      secretName: db-credentials
```

应用方法：
```bash
kubectl apply -f db-secret.yaml
kubectl apply -f pod-with-secret.yaml
```
</details>

## Advanced Topics

1. 提供三个可以使用 OPA (Open Policy Agent) Gatekeeper 在 Kubernetes 中实现的 policies 示例，并解释它们。

<details>
<summary>显示答案</summary>

**答案：**

OPA Gatekeeper 是一个用于向 Kubernetes clusters 应用 policies 的强大工具。以下是可应用 policies 的示例：

1. **Image Registry Restriction**：强制 images 只能从已批准的 registries 拉取，防止使用来自不受信任来源的 images。
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: allowed-repos
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/company/"
   ```

2. **Prevent Privileged Containers**：禁止使用 privileged containers 以降低安全风险。
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: prevent-privileged-containers
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
   ```

3. **Enforce Resource Limits**：强制所有 containers 设置 CPU 和 memory limits，以防止 resource exhaustion attacks。
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
   ```

OPA Gatekeeper 还可以应用其他各种 policies，例如要求 namespaces 上具有特定 labels、限制 ingress hostnames、限制 volume types，以及防止 host path mounts。
</details>

2. 解释如何在 Kubernetes 中实现 mTLS (mutual TLS) 及其好处。

<details>
<summary>显示答案</summary>

**答案：**

mTLS (mutual TLS) 是一种 client 和 server 都使用 certificates 相互进行 authentication 的方法。以下是在 Kubernetes 中实现 mTLS 的方式及其好处：

**实现方法：**

1. **使用 Service Mesh**：Istio 和 Linkerd 等 service meshes 通过 sidecar proxies 自动实现 mTLS。
   ```yaml
   # Istio example
   apiVersion: security.istio.io/v1beta1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

2. **与 Network Policies 结合使用**：将 mTLS 与 network policies 结合，仅允许经过 authentication 的 traffic。

3. **Certificate Management**：使用 cert-manager 等工具管理 certificate lifecycle。
   ```yaml
   apiVersion: cert-manager.io/v1
   kind: Certificate
   metadata:
     name: service-cert
     namespace: default
   spec:
     secretName: service-tls
     issuerRef:
       name: ca-issuer
       kind: ClusterIssuer
     commonName: service.default.svc.cluster.local
     dnsNames:
     - service.default.svc.cluster.local
   ```

**好处：**

1. **Mutual Authentication**：Client 和 server 相互进行 authentication，防止 man-in-the-middle attacks
2. **Encrypted Communication**：所有 service-to-service traffic 都被加密，防止 eavesdropping
3. **Fine-grained Access Control**：基于 certificate 的 identity 支持 fine-grained access control
4. **Zero Trust Architecture**：无论 network location 如何，所有通信都要求 authentication
5. **Compliance Support**：帮助满足 PCI DSS、HIPAA 等 compliance requirements

mTLS 是增强 microservice architectures 中 service-to-service 通信安全性的重要方法。
</details>

3. 解释在 Kubernetes 中增强 'supply chain security' 的方法。

<details>
<summary>显示答案</summary>

**答案：**

在 Kubernetes 中增强 supply chain security 的方法包括：

1. **Image Signing and Verification**：
   - 使用 Cosign、Notary 等工具对 container images 进行签名
   - 应用 policies，确保只部署已签名的 images（例如 OPA Gatekeeper、Kyverno）
   ```bash
   cosign sign --key cosign.key docker.io/company/app:latest
   ```

2. **Software Bill of Materials (SBOM) Generation and Verification**：
   - 使用 Syft、Anchore 等工具生成 SBOMs
   - 跟踪 images 中包含的所有 software components
   ```bash
   syft docker.io/company/app:latest -o spdx-json > sbom.json
   ```

3. **Vulnerability Scanning**：
   - 使用 Trivy、Clair 等工具扫描 images 中的 vulnerabilities
   - 将 scanning 集成到 CI/CD pipelines 中
   ```bash
   trivy image docker.io/company/app:latest
   ```

4. **Use Minimal Base Images**：
   - 使用 distroless、scratch 等 minimal images 来减少 attack surface
   ```dockerfile
   FROM gcr.io/distroless/java:11
   COPY --from=build /app/target/app.jar /app.jar
   CMD ["app.jar"]
   ```

5. **Apply Image Policies**：
   - 根据 image age、vulnerability severity、registry source 等应用 policies
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sTrustedImages
   metadata:
     name: trusted-images
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       allowedRegistries:
         - "docker.io/company/"
         - "gcr.io/verified/"
   ```

6. **Supply Chain Levels for Software Artifacts (SLSA)**：
   - 跟踪 build provenance
   - 确保 reproducible builds
   - 验证 build integrity

7. **Continuous Monitoring and Auditing**：
   - 使用 runtime security tools 检测 anomalous behavior
   - 执行定期 security audits

结合这些方法有助于保护 Kubernetes environments 免受 software supply chain attacks。
</details>

4. 解释在 Kubernetes 中实现 'zero trust security model' 的方法。

<details>
<summary>显示答案</summary>

**答案：**

Zero trust security model 基于“never trust, always verify”原则。以下是在 Kubernetes 中实现 zero trust 的方法：

1. **Fine-grained Identity and Access Management**：
   - 实施强 RBAC policies
   - 向 service accounts 授予最低限度的必要权限
   - 与外部 ID providers（OIDC、LDAP 等）集成
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     namespace: default
     name: minimal-access
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get", "list"]
     resourceNames: ["app-pod"]
   ```

2. **Network Segmentation**：
   - 默认拒绝所有 traffic
   - 应用仅允许明确所需通信的 network policies
   - 实施 microsegmentation
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

3. **Apply Mutual TLS (mTLS)**：
   - 使用 service mesh（Istio、Linkerd 等）将 mTLS 应用于所有 service-to-service 通信
   - 基于 certificate 的 service identity verification
   ```yaml
   apiVersion: security.istio.io/v1beta1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

4. **Continuous Verification and Authentication**：
   - 对所有 requests 进行 continuous authentication 和 authorization
   - 基于 context 的 access control（time、location、device state 等）
   - 使用 OPA Gatekeeper 或 Kyverno 进行 dynamic policy application

5. **Encryption**：
   - Data at rest encryption（etcd encryption、encrypted PVs 等）
   - Data in transit encryption（TLS、mTLS）
   - 集成 Secret management tools（Vault、Sealed Secrets 等）

6. **Threat Detection and Response**：
   - 部署 runtime security monitoring tools
   - 检测 anomalous behavior 并发出 alerts
   - 实施 automated response mechanisms

7. **Least Privilege Workload Configuration**：
   - 以 non-root users 运行 containers
   - 使用 read-only filesystems
   - 应用 security context restrictions
   ```yaml
   securityContext:
     runAsUser: 1000
     runAsGroup: 3000
     fsGroup: 2000
     readOnlyRootFilesystem: true
     allowPrivilegeEscalation: false
   ```

8. **Continuous Security Posture Assessment**：
   - 定期 vulnerability scanning
   - Penetration testing 和 security audits
   - Compliance monitoring

Zero trust model 不是单一解决方案，而是一种结合多层安全措施的方法，基于 continuous verification 和最小权限原则。
</details>

5. 比较并解释 Kubernetes 中用于 'runtime security' 的工具和技术。

<details>
<summary>显示答案</summary>

**答案：**

Kubernetes 中 runtime security 的主要工具和技术包括：

1. **Falco**：
   - **工作原理**：监控 system calls 以检测 anomalous behavior
   - **特性**： 
     - 在 kernel level 运行以监控 container 内部活动
     - 用于检测各种 security threats 的 custom rules
     - 支持 real-time alerting and response
   - **示例规则**：
     ```yaml
     - rule: Terminal shell in container
       desc: A shell was spawned by a container
       condition: container and proc.name = bash
       output: Shell opened in container (user=%user.name container=%container.name)
       priority: WARNING
     ```

2. **Seccomp (Secure Computing Mode)**：
   - **工作原理**：限制 containers 可以使用的 system calls
   - **特性**：
     - 使用内置 Linux kernel feature
     - 只有被允许的 system calls 可以执行
     - 减少 attack surface
   - **实现示例**：
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: seccomp-pod
     spec:
       securityContext:
         seccompProfile:
           type: Localhost
           localhostProfile: profiles/audit.json
     ```

3. **AppArmor**：
   - **工作原理**：应用 per-program access control profiles
   - **特性**：
     - 对 files、network、capabilities 等进行 fine-grained access control
     - 默认包含在 Linux distributions 中
     - 可以按 container 应用 profile
   - **实现示例**：
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: apparmor-pod
       annotations:
         container.apparmor.security.beta.kubernetes.io/container1: localhost/restricted
     ```

4. **SELinux**：
   - **工作原理**：应用 Mandatory Access Control (MAC) policies
   - **特性**：
     - 基于 labels 的 fine-grained security policies
     - 支持 military-grade security standard
     - 需要复杂配置
   - **实现示例**：
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: selinux-pod
     spec:
       securityContext:
         seLinuxOptions:
           level: "s0:c123,c456"
     ```

5. **OPA Gatekeeper**：
   - **工作原理**：基于 policy 的 runtime governance
   - **特性**：
     - 声明式 policy 定义
     - 广泛的 policy application scope
     - 支持 audit 和 enforcement mode

6. **Commercial Tools (Aqua, Sysdig, StackRox, etc.)**：
   - **工作原理**：提供全面的 container security platforms
   - **特性**：
     - 集成 vulnerability scanning、runtime protection、compliance monitoring
     - 基于 machine learning 的 anomaly detection
     - Dashboard 和 reporting features

7. **gVisor**：
   - **工作原理**：在 application 和 host kernel 之间提供 user-space kernel
   - **特性**：
     - 在 container 和 host 之间提供额外 isolation layer
     - System call interception and emulation
     - 存在 performance overhead
   - **实现示例**：
     ```yaml
     apiVersion: node.k8s.io/v1
     kind: RuntimeClass
     metadata:
       name: gvisor
     handler: runsc
     ```

8. **Kata Containers**：
   - **工作原理**：使用 lightweight VMs 运行 containers
   - **特性**：
     - Hardware-level isolation
     - 保持 OCI compatibility
     - 比常规 containers 有更高 overhead

**比较和选择标准**：
  - **Security level**：Kata Containers 和 gVisor 提供最强隔离
  - **Performance impact**：Seccomp overhead 最小，Kata Containers 最高
  - **Implementation complexity**：Seccomp 和 AppArmor 相对容易，SELinux 复杂
  - **Monitoring vs Prevention**：Falco 主要用于 monitoring，其他工具提供 preventive protection
  - **Integration ease**：OPA Gatekeeper 与 Kubernetes 紧密集成

请根据组织的 security requirements、performance goals 和对 operational complexity 的容忍度选择合适的工具组合。
</details>
