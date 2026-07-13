# Security Quiz

このクイズでは、認証、認可、NetworkPolicy、Security Context、Secret 管理など、Kubernetes security の概念に関する理解を確認します。

## Multiple Choice Questions

1. Kubernetes でユーザー認証にサポートされていない認証方式はどれですか？
   - A) X.509 certificates
   - B) Service account tokens
   - C) OAuth tokens
   - D) Built-in user database
   
<details>
<summary>回答を表示</summary>

**回答: D) Built-in user database**

**解説:**
Kubernetes は組み込みのユーザーデータベースを提供していません。代わりに、X.509 certificates、service account tokens、OAuth tokens、OpenID Connect tokens、webhook token authentication などの認証方式をサポートしています。ユーザー管理は通常、外部システム（例: LDAP、Active Directory）との統合を通じて行われます。
</details>

2. Kubernetes における RBAC (Role-Based Access Control) の主要コンポーネントではないものはどれですか？
   - A) Role
   - B) ClusterRole
   - C) RoleBinding
   - D) SecurityPolicy
   
<details>
<summary>回答を表示</summary>

**回答: D) SecurityPolicy**

**解説:**
Kubernetes RBAC の主要コンポーネントは Role、ClusterRole、RoleBinding、ClusterRoleBinding です。Role と ClusterRole は権限の集合を定義し、RoleBinding と ClusterRoleBinding はそれらの権限をユーザー、グループ、または service account に関連付けます。SecurityPolicy は RBAC コンポーネントではありません。類似のリソースとしては PodSecurityPolicy（現在は非推奨）や PodSecurityStandard があります。
</details>

3. Kubernetes の pod の Security Context で設定できないものはどれですか？
   - A) Container user ID (UID)
   - B) Container group ID (GID)
   - C) Container network policy
   - D) Container privilege escalation capability
   
<details>
<summary>回答を表示</summary>

**回答: C) Container network policy**

**解説:**
Security Context は、pod または container レベルでの権限とアクセス制御設定を定義します。これには user ID (runAsUser)、group ID (runAsGroup)、privilege escalation capability (allowPrivilegeEscalation)、privileged containers (privileged)、capabilities が含まれます。ただし、network policies は Security Context ではなく、別個の NetworkPolicy リソースで定義されます。
</details>

4. Kubernetes における ServiceAccount の主な目的は何ですか？
   - A) Authentication for users outside the cluster
   - B) Providing identity for pods to communicate with the API server
   - C) Encrypting communication between nodes
   - D) Granting cluster administrator privileges
   
<details>
<summary>回答を表示</summary>

**回答: B) Providing identity for pods to communicate with the API server**

**解説:**
Service accounts は、pod 内で実行されるプロセスが Kubernetes API server と通信するための identity を提供します。各 namespace には default service account があり、明示的に指定しない限り、pod はこの default service account を使用します。Service accounts は RBAC と組み合わせて使用することで、pod が実行できる操作を制限できます。
</details>

5. Kubernetes における NetworkPolicy の主な目的は何ですか？
   - A) Routing traffic from outside the cluster to inside
   - B) Controlling and restricting communication between pods
   - C) Encrypting communication between nodes
   - D) Providing service discovery
   
<details>
<summary>回答を表示</summary>

**回答: B) Controlling and restricting communication between pods**

**解説:**
NetworkPolicy は、pod のグループ間の通信を制御する方法を提供します。これにより、どの pod がどの他の pod と通信できるか、またどの ports と protocols を使用できるかを指定できます。Network policies は、service-to-service communication の細かな制御と、microservice architectures における security 強化に重要です。
</details>

6. Pod Security Standards における 3 つの policy levels のうち、最も制限が厳しいものはどれですか？
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>回答を表示</summary>

**回答: C) Restricted**

**解説:**
Pod Security Standards は 3 つの policy levels を定義しています:
  - Privileged: 制限なし、すべての権限を許可
  - Baseline: 既知の privilege escalation paths を防止
  - Restricted: security settings が強化された最も制限の厳しい policy

Restricted policy は最も制限が厳しく、least privilege の原則に従い、security best practices を適用します。この policy は privileged containers、host namespace sharing、host path mounts などを禁止します。
</details>

7. Kubernetes で Secret data を保護するために最も効果的な方法は何ですか？
   - A) Base64 encoding
   - B) etcd encryption configuration
   - C) Namespace isolation
   - D) Adding labels
   
<details>
<summary>回答を表示</summary>

**回答: B) etcd encryption configuration**

**解説:**
Kubernetes の Secret data はデフォルトで Base64 にエンコードされて保存されますが、これは暗号化ではなく単純なエンコードです。etcd encryption configuration を使用すると、Secret data は etcd に保存される前に暗号化され、etcd database への不正アクセスから機密情報を保護できます。Namespace isolation と labels はアクセス制御には役立ちますが、データ自体を保護するものではありません。
</details>

8. Kubernetes における container image security を強化する方法ではないものはどれですか？
   - A) Image vulnerability scanning
   - B) Using trusted registries
   - C) Image signing and verification
   - D) Granting root privileges to containers
   
<details>
<summary>回答を表示</summary>

**回答: D) Granting root privileges to containers**

**解説:**
containers に root privileges を付与すると security が弱まります。Container image security を強化する方法には、image vulnerability scanning、trusted registries の使用、image signing and verification、least privilege の原則の適用、不要な packages の削除、containers を non-root users として実行することが含まれます。
</details>

9. Kubernetes における Audit Logging の主な目的は何ですか？
   - A) Collecting pod logs
   - B) Recording API server requests
   - C) Monitoring node status
   - D) Analyzing network traffic
   
<details>
<summary>回答を表示</summary>

**回答: B) Recording API server requests**

**解説:**
Audit logging は、Kubernetes API server への requests を記録する仕組みです。これにより、cluster 内で誰が何をしたかを追跡でき、security incident investigation、compliance requirements、troubleshooting に役立ちます。Audit logs には、request time、user、request content、response などの情報を含めることができます。
</details>

10. Kubernetes における privileged containers の特徴ではないものはどれですか？
    - A) Access to all host devices
    - B) Use of host network stack
    - C) Ability to load host kernel modules
    - D) Automatic access to resources in other namespaces
    
<details>
<summary>回答を表示</summary>

**回答: D) Automatic access to resources in other namespaces**

**解説:**
Privileged containers はほぼすべての host capabilities にアクセスできますが、他の namespaces 内の Kubernetes resources に自動的にアクセスできるわけではありません。Cross-namespace access は RBAC permissions によって制御されます。Privileged containers は host devices、network stack、kernel modules などにアクセスでき、大きな security risks をもたらすため、本当に必要な場合にのみ使用するべきです。
</details>

## Short Answer Questions

1. Kubernetes RBAC における 'Role' と 'ClusterRole' の主な違いは何ですか？

<details>
<summary>回答を表示</summary>

**回答:**
Role は特定の namespace 内でのみ権限を定義して適用します。一方、ClusterRole は cluster-wide に適用され、すべての namespaces にわたる権限を定義します。ClusterRole は、non-namespaced resources（nodes、PVs など）に対する権限を定義するためにも使用されます。
</details>

2. Kubernetes で 'principle of least privilege' を適用する 3 つの方法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**
1. RBAC を使用して必要最小限の権限だけを付与する
2. pod security context で containers を non-root users として実行する
3. network policies を使用して必要な通信のみを許可する
4. privileged containers の使用を制限する
5. container capabilities を制限する
6. Pod Security Standards Restricted profile を適用する

（上記のうち 3 つだけ説明すればよい）
</details>

3. Kubernetes における security の観点から見た Secret と ConfigMap の主な違いは何ですか？

<details>
<summary>回答を表示</summary>

**回答:**
Secret は機密情報（passwords、tokens、keys など）を保存するためのもので、ConfigMap は一般的な設定データを保存するためのものです。Secrets は Base64 でエンコードされて保存され（デフォルトでは暗号化されません）、memory 内にのみ mount するよう設定でき、pod 作成時にのみ参照されます。ただし、追加設定がない場合、どちらも etcd に plaintext で保存されるため、完全な security には etcd encryption settings が必要です。
</details>

4. Kubernetes における 'service account token volume projection' の目的と利点は何ですか？

<details>
<summary>回答を表示</summary>

**回答:**
Service account token volume projection は、pod に mount される service account tokens に対して、時間制限や audience restrictions などの追加 security features を提供します。これにより、token lifetime を制限し、特定の API servers のみが token を受け入れるようにできるため、token leakage が発生した場合の risk を低減できます。さらに、tokens は自動的に更新されるため、長時間実行される applications の authentication issues を防止できます。
</details>

5. Kubernetes における 'container sandboxing' とは何ですか。また、それを実装するためにどのような technologies を使用できますか？

<details>
<summary>回答を表示</summary>

**回答:**
Container sandboxing は、containers を host system や他の containers から分離することで security を強化する技術です。これを実装するための technologies には次のものがあります:
1. Linux namespaces and cgroups: 基本的な container isolation を提供
2. seccomp: system calls を制限
3. AppArmor/SELinux: Mandatory access control
4. gVisor: user-space kernel implementation による追加 isolation
5. Kata Containers: lightweight VMs を使用した hardware-level isolation
6. Firecracker: MicroVM-based isolation

これらの technologies は、containers が host system に与えられる影響を制限し、container escape attacks の risk を低減します。
</details>

## Hands-on Questions

1. 次の要件を満たす RBAC resources を作成してください:
   - 'monitoring' namespace の pods を読み取れる Role
   - この Role を 'monitoring-team' service account に bind する RoleBinding

<details>
<summary>回答を表示</summary>

**回答:**

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

適用方法:
```bash
kubectl apply -f monitoring-role.yaml
kubectl apply -f monitoring-rolebinding.yaml
```
</details>

2. 次の要件を満たす NetworkPolicy を作成してください:
   - 'backend' namespace 内のすべての pods に適用する
   - port 8080 で 'frontend' namespace 内の pods からの incoming traffic のみを許可する
   - すべての outgoing traffic を許可する

<details>
<summary>回答を表示</summary>

**回答:**

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

適用方法:
```bash
kubectl apply -f backend-network-policy.yaml
```

注: この NetworkPolicy を機能させるには、'frontend' namespace に 'name: frontend' label が必要です。ない場合は、次のように追加します:
```bash
kubectl label namespace frontend name=frontend
```
</details>

3. 次の security context 要件を満たす pod を作成してください:
   - Container が UID 1000 として実行される
   - Privilege escalation を許可しない
   - Read-only root filesystem

<details>
<summary>回答を表示</summary>

**回答:**

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

適用方法:
```bash
kubectl apply -f secure-pod.yaml
```
</details>

4. 次の要件を満たす Secret を作成し、pod に volume として mount してください:
   - 'db-credentials' という名前の Secret
   - 'username=admin' と 'password=s3cr3t' を含む
   - pod 内の '/etc/db-credentials' path に mount する

<details>
<summary>回答を表示</summary>

**回答:**

Secret を作成:
```bash
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=s3cr3t
```

または YAML として:
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

pod に mount:
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

適用方法:
```bash
kubectl apply -f db-secret.yaml
kubectl apply -f pod-with-secret.yaml
```
</details>

## Advanced Topics

1. Kubernetes で OPA (Open Policy Agent) Gatekeeper を使用して実装できる policies の例を 3 つ挙げ、それらを説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

OPA Gatekeeper は Kubernetes clusters に policies を適用するための強力なツールです。適用できる policies の例は次のとおりです:

1. **Image Registry Restriction**: images が承認済み registries からのみ pull されるように強制し、信頼できない sources の images の使用を防ぎます。
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

2. **Prevent Privileged Containers**: security risks を低減するため、privileged containers の使用を禁止します。
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

3. **Enforce Resource Limits**: resource exhaustion attacks を防ぐため、すべての containers に CPU と memory limits の設定を強制します。
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

OPA Gatekeeper は、namespaces に特定の labels を要求する、ingress hostnames を制限する、volume types を制限する、host path mounts を防止するなど、他のさまざまな policies も適用できます。
</details>

2. Kubernetes で mTLS (mutual TLS) を実装する方法とその利点を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

mTLS (mutual TLS) は、client と server の両方が certificates を使用して相互に認証する方法です。Kubernetes で mTLS を実装する方法とその利点は次のとおりです:

**実装方法:**

1. **Using Service Mesh**: Istio や Linkerd のような service meshes は、sidecar proxies を通じて mTLS を自動的に実装します。
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

2. **Use with Network Policies**: mTLS と network policies を組み合わせて、認証済み traffic のみを許可します。

3. **Certificate Management**: cert-manager のような tools を使用して certificate lifecycle を管理します。
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

**利点:**

1. **Mutual Authentication**: Client と server が相互に認証し、man-in-the-middle attacks を防止します
2. **Encrypted Communication**: すべての service-to-service traffic が暗号化され、eavesdropping を防止します
3. **Fine-grained Access Control**: Certificate-based identity により fine-grained access control が可能になります
4. **Zero Trust Architecture**: network location に関係なく、すべての通信に authentication を要求します
5. **Compliance Support**: PCI DSS、HIPAA などの compliance requirements を満たすのに役立ちます

mTLS は、microservice architectures における service-to-service communication の security を強化する重要な方法です。
</details>

3. Kubernetes における 'supply chain security' を強化する方法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

Kubernetes における supply chain security を強化する方法には、次のものがあります:

1. **Image Signing and Verification**:
   - Cosign、Notary などの tools を使用して container images に署名する
   - 署名済み images のみが deployment されるように policies を適用する（例: OPA Gatekeeper、Kyverno）
   ```bash
   cosign sign --key cosign.key docker.io/company/app:latest
   ```

2. **Software Bill of Materials (SBOM) Generation and Verification**:
   - Syft、Anchore などの tools を使用して SBOM を生成する
   - images に含まれるすべての software components を追跡する
   ```bash
   syft docker.io/company/app:latest -o spdx-json > sbom.json
   ```

3. **Vulnerability Scanning**:
   - Trivy、Clair などの tools を使用して images の vulnerabilities を scan する
   - scanning を CI/CD pipelines に統合する
   ```bash
   trivy image docker.io/company/app:latest
   ```

4. **Use Minimal Base Images**:
   - attack surface を減らすため、distroless、scratch のような minimal images を使用する
   ```dockerfile
   FROM gcr.io/distroless/java:11
   COPY --from=build /app/target/app.jar /app.jar
   CMD ["app.jar"]
   ```

5. **Apply Image Policies**:
   - image age、vulnerability severity、registry source などに基づいて policies を適用する
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

6. **Supply Chain Levels for Software Artifacts (SLSA)**:
   - build provenance を追跡する
   - reproducible builds を確保する
   - build integrity を検証する

7. **Continuous Monitoring and Auditing**:
   - runtime security tools を使用して anomalous behavior を検出する
   - 定期的な security audits を実施する

これらの方法を組み合わせることで、Kubernetes environments を software supply chain attacks から保護できます。
</details>

4. Kubernetes で 'zero trust security model' を実装するためのアプローチを説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

Zero trust security model は、「never trust, always verify」という原則に基づいています。Kubernetes で zero trust を実装するためのアプローチは次のとおりです:

1. **Fine-grained Identity and Access Management**:
   - 強力な RBAC policies を実装する
   - service accounts に必要最小限の権限を付与する
   - external ID providers（OIDC、LDAP など）と統合する
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

2. **Network Segmentation**:
   - デフォルトですべての traffic を拒否する
   - 明示的に必要な通信のみを許可する network policies を適用する
   - microsegmentation を実装する
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

3. **Apply Mutual TLS (mTLS)**:
   - service mesh（Istio、Linkerd など）を使用して、すべての service-to-service communication に mTLS を適用する
   - Certificate-based service identity verification
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

4. **Continuous Verification and Authentication**:
   - すべての requests に対して継続的な authentication and authorization を行う
   - context-based access control（time、location、device state など）
   - OPA Gatekeeper または Kyverno を使用した dynamic policy application

5. **Encryption**:
   - Data at rest encryption（etcd encryption、encrypted PVs など）
   - Data in transit encryption（TLS、mTLS）
   - Secret management tool integration（Vault、Sealed Secrets など）

6. **Threat Detection and Response**:
   - runtime security monitoring tools を deployment する
   - anomalous behavior を検出して alert する
   - automated response mechanisms を実装する

7. **Least Privilege Workload Configuration**:
   - containers を non-root users として実行する
   - read-only filesystems を使用する
   - security context restrictions を適用する
   ```yaml
   securityContext:
     runAsUser: 1000
     runAsGroup: 3000
     fsGroup: 2000
     readOnlyRootFilesystem: true
     allowPrivilegeEscalation: false
   ```

8. **Continuous Security Posture Assessment**:
   - 定期的な vulnerability scanning
   - penetration testing と security audits
   - compliance monitoring

Zero trust model は単一の solution ではなく、continuous verification と least privilege の原則に基づいて、複数の security layers を組み合わせるアプローチです。
</details>

5. Kubernetes における 'runtime security' のための tools と technologies を比較して説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

Kubernetes における runtime security の主要な tools と technologies には次のものがあります:

1. **Falco**:
   - **How it works**: system calls を監視して anomalous behavior を検出します
   - **Features**: 
     - kernel level で動作して container internal activity を監視します
     - さまざまな security threats を検出するための custom rules
     - real-time alerting and response support
   - **Example rule**:
     ```yaml
     - rule: Terminal shell in container
       desc: A shell was spawned by a container
       condition: container and proc.name = bash
       output: Shell opened in container (user=%user.name container=%container.name)
       priority: WARNING
     ```

2. **Seccomp (Secure Computing Mode)**:
   - **How it works**: containers が使用できる system calls を制限します
   - **Features**:
     - 組み込みの Linux kernel feature を使用します
     - 許可された system calls のみ実行できます
     - attack surface を削減します
   - **Implementation example**:
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

3. **AppArmor**:
   - **How it works**: program ごとの access control profiles を適用します
   - **Features**:
     - files、network、capabilities などに対する fine-grained access control
     - Linux distributions にデフォルトで含まれます
     - container ごとの profile application が可能です
   - **Implementation example**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: apparmor-pod
       annotations:
         container.apparmor.security.beta.kubernetes.io/container1: localhost/restricted
     ```

4. **SELinux**:
   - **How it works**: Mandatory Access Control (MAC) policies を適用します
   - **Features**:
     - label-based の fine-grained security policies
     - military-grade security standard support
     - 複雑な configuration が必要です
   - **Implementation example**:
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

5. **OPA Gatekeeper**:
   - **How it works**: policy-based runtime governance
   - **Features**:
     - Declarative policy definition
     - 広範な policy application scope
     - Audit and enforcement mode support

6. **Commercial Tools (Aqua, Sysdig, StackRox, etc.)**:
   - **How it works**: 包括的な container security platforms を提供します
   - **Features**:
     - vulnerability scanning、runtime protection、compliance monitoring の統合
     - machine learning-based anomaly detection
     - dashboard and reporting features

7. **gVisor**:
   - **How it works**: application と host kernel の間に user-space kernel を提供します
   - **Features**:
     - container と host の間に追加 isolation layer を提供します
     - System call interception and emulation
     - performance overhead があります
   - **Implementation example**:
     ```yaml
     apiVersion: node.k8s.io/v1
     kind: RuntimeClass
     metadata:
       name: gvisor
     handler: runsc
     ```

8. **Kata Containers**:
   - **How it works**: lightweight VMs を使用して containers を実行します
   - **Features**:
     - Hardware-level isolation
     - OCI compatibility maintained
     - 通常の containers より overhead が高いです

**Comparison and Selection Criteria**:
  - **Security level**: Kata Containers と gVisor は最も強力な isolation を提供します
  - **Performance impact**: Seccomp は overhead が最小で、Kata Containers は最大です
  - **Implementation complexity**: Seccomp と AppArmor は比較的簡単で、SELinux は複雑です
  - **Monitoring vs Prevention**: Falco は主に monitoring、その他は preventive protection を提供します
  - **Integration ease**: OPA Gatekeeper は Kubernetes と密接に統合されます

組織の security requirements、performance goals、operational complexity tolerance に基づいて、適切な tool combination を選択してください。
</details>
