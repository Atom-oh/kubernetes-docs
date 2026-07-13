# ポリシークイズ

このクイズでは、ResourceQuota、LimitRange、PodSecurityPolicy、NetworkPolicy など、Kubernetes のポリシー概念についての理解を確認します。

## 選択問題

1. Kubernetes における ResourceQuota の主な目的は何ですか？
   - A) pod の CPU と memory 使用量を制限する
   - B) namespace 内での resource 作成を制限する
   - C) cluster 全体の resource 使用量を監視する
   - D) node の resource 割り当てを管理する
   
<details>
<summary>答えを表示</summary>

**答え: B) namespace 内での resource 作成を制限する**

**解説:**
ResourceQuota は、namespace 内で作成できる resource の総量を制限します。これには CPU や memory などの computing resource だけでなく、pod、service、configmap などの object 数も含まれます。ResourceQuota を使用すると、1 つの team が cluster resource をすべて独占することを防げます。
</details>

2. LimitRange の主な機能は何ですか？
   - A) namespace 全体の resource 使用量を制限する
   - B) 個々の container に対するデフォルトの resource request と limit を設定する
   - C) cluster node 間で resource を分配する
   - D) pod 間の network 通信を制限する
   
<details>
<summary>答えを表示</summary>

**答え: B) 個々の container に対するデフォルトの resource request と limit を設定する**

**解説:**
LimitRange は、namespace 内の pod または container に対する resource 制約を定義します。これにより、デフォルトの resource request と limit を設定したり、resource 使用量の最小値/最大値を強制したりできます。LimitRange は個々の resource に適用される一方、ResourceQuota は namespace 全体に適用されます。
</details>

3. Kubernetes v1.25 で PodSecurityPolicy (PSP) が削除された後、どの mechanism がそれを置き換えましたか？
   - A) PodSecurityStandards
   - B) PodSecurityContext
   - C) PodSecurityAdmission
   - D) SecurityContextConstraints
   
<details>
<summary>答えを表示</summary>

**答え: C) PodSecurityAdmission**

**解説:**
PodSecurityPolicy (PSP) は Kubernetes v1.25 で削除され、PodSecurityAdmission がそれを置き換えました。これは Pod Security Standards に基づく組み込みの admission controller で、Privileged、Baseline、Restricted の 3 つの policy level を提供します。PodSecurityContext は pod level で security 設定を構成するために使用され、SecurityContextConstraints は OpenShift で使用される類似の mechanism です。
</details>

4. NetworkPolicy を使用してできないことは何ですか？
   - A) 特定の namespace からの pod への traffic のみを制限する
   - B) 特定の IP CIDR range への traffic のみを制限する
   - C) 特定の port への traffic のみを制限する
   - D) 特定 protocol の payload content を検査する
   
<details>
<summary>答えを表示</summary>

**答え: D) 特定 protocol の payload content を検査する**

**解説:**
NetworkPolicy は、pod 間の通信を制御する L3/L4 level の firewall policy を提供します。これにより、特定の namespace、label、IP CIDR range、port などに基づいて traffic を制限できます。ただし、NetworkPolicy は L7 level の検査（例: HTTP header、payload content）を実行できません。そのような機能には、service mesh（例: Istio）または API gateway を使用する必要があります。
</details>

5. Kubernetes における RBAC (Role-Based Access Control) の主な目的は何ですか？
   - A) pod 間の network 通信を制御する
   - B) user と service account の permission を管理する
   - C) resource 使用量を制限する
   - D) pod scheduling policy を設定する
   
<details>
<summary>答えを表示</summary>

**答え: B) user と service account の permission を管理する**

**解説:**
RBAC (Role-Based Access Control) は、Kubernetes API への access を制御するための mechanism です。これにより、user、group、または service account が cluster 内で実行できる operation を定義できます。RBAC は Role、ClusterRole、RoleBinding、ClusterRoleBinding などの resource を使用して permission を管理します。
</details>

6. Pod Security Standards の 3 つの policy level のうち、最も制限が厳しいものはどれですか？
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>答えを表示</summary>

**答え: C) Restricted**

**解説:**
Pod Security Standards は 3 つの policy level を定義しています:
- Privileged: 制限なし、すべての privilege が許可される
- Baseline: 既知の privilege escalation 経路を防止する
- Restricted: 強化された security 設定が適用される、最も制限の厳しい policy

Restricted policy は最も制限が厳しく、least privilege の原則に従い、security best practice を適用します。この policy は privileged container、host namespace sharing、host path mount などを禁止します。
</details>

7. Kubernetes における AdmissionController の役割は何ですか？
   - A) user authentication
   - B) resource 使用量の監視
   - C) API request の検証と変更
   - D) Pod scheduling
   
<details>
<summary>答えを表示</summary>

**答え: C) API request の検証と変更**

**解説:**
AdmissionController は、authentication と authorization を通過した後、object が persistent storage に保存される前に、Kubernetes API server への request を intercept して検証または変更する plugin です。これにより、cluster administrator は resource の作成や変更に関する policy を適用できます。たとえば、PodSecurityAdmission、ResourceQuota、LimitRanger は AdmissionController として実装されています。
</details>

8. Kubernetes における OPA (Open Policy Agent) Gatekeeper の主な機能は何ですか？
   - A) Cluster monitoring と logging
   - B) policy に基づく resource 管理と検証
   - C) Auto scaling
   - D) Service mesh management
   
<details>
<summary>答えを表示</summary>

**答え: B) policy に基づく resource 管理と検証**

**解説:**
OPA Gatekeeper は、Kubernetes cluster に policy を適用するための拡張可能な solution です。OPA (Open Policy Agent) に基づいており、CustomResourceDefinitions (CRDs) を使用して policy を定義・適用します。Gatekeeper は AdmissionWebhook として動作し、cluster 内で作成または変更される resource が定義済み policy に準拠していることを検証します。これにより、security policy、resource limit、naming convention など、さまざまな policy を適用できます。
</details>

9. ResourceQuota が適用された namespace で、resource request と limit を指定せずに pod を作成するとどうなりますか？
   - A) pod はデフォルトの resource request と limit で作成される
   - B) pod の作成が拒否される
   - C) pod は作成されるが schedule されない
   - D) pod は作成され、無制限の resource を使用できる
   
<details>
<summary>答えを表示</summary>

**答え: B) pod の作成が拒否される**

**解説:**
ResourceQuota が namespace に適用され、CPU や memory などの computing resource に quota が設定されている場合、その namespace 内のすべての container は resource request と limit を明示的に指定する必要があります。指定しない場合、API server は pod 作成 request を拒否します。これは、quota が適用された namespace で resource 使用量を正確に追跡し制限するためです。
</details>

10. Kubernetes における PriorityClass の主な目的は何ですか？
    - A) pod scheduling priority を定義する
    - B) namespace resource allocation priority を設定する
    - C) API request processing priority を決定する
    - D) node importance level を設定する
    
<details>
<summary>答えを表示</summary>

**答え: A) pod scheduling priority を定義する**

**解説:**
PriorityClass は pod の scheduling priority を定義します。resource が不足している場合、priority の高い pod は priority の低い pod より先に schedule され、必要に応じて priority の低い pod を preempt できます。
</details>

## 短答問題

1. ResourceQuota と LimitRange の主な違いを説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
ResourceQuota は namespace 全体の resource 使用量を制限する一方、LimitRange は namespace 内の個々の container または pod に対して resource 制約を設定します。

主な違い:
1. **Scope**: ResourceQuota は namespace 全体に適用され、LimitRange は個々の resource（pod、container など）に適用されます。
2. **Purpose**: ResourceQuota は namespace 全体の resource 使用量を制限する一方、LimitRange はデフォルト設定、最小/最大 limit などを通じて個々の resource 使用量を制御します。
3. **Enforcement**: ResourceQuota が設定されている場合、quota を超える resource 作成は拒否されます。LimitRange は resource 作成時にデフォルトを適用するか、limit を超える場合に拒否します。
4. **Resource types**: ResourceQuota は CPU や memory だけでなく、pod、service、PVC などの object 数も制限できます。LimitRange は主に CPU、memory、storage などの computing resource に焦点を当てます。
</details>

2. Pod Security Standards の 3 つの policy level（Privileged、Baseline、Restricted）とその特徴を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
Pod Security Standards は、pod security 設定のために 3 つの policy level を定義しています:

1. **Privileged**:
   - ほとんど制限のない、最も open な policy。
   - すべての privileged operation を許可します。
   - host namespace、host port、privileged container などを使用できます。
   - development や administrative work には適していますが、production では重大な security risk があります。

2. **Baseline**:
   - 既知の privilege escalation 経路を防止する中間 level の policy。
   - ほとんどの workload に適した baseline level の security を提供します。
   - privileged container と host namespace の使用を制限します。
   - ただし、一部の privileged operation（例: host path mount）はまだ許可されます。

3. **Restricted**:
   - 強化された security 設定を持つ、最も制限の厳しい policy。
   - least privilege の原則に従い、security best practice を強制します。
   - privileged container、host namespace、host path mount、privilege escalation を禁止します。
   - container を non-root user として実行することを強制します。
   - security-critical な production workload に適しています。
</details>

3. NetworkPolicy を使用して、特定の namespace 内の pod が別の namespace 内の特定の pod とだけ通信できるように制限する方法を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
NetworkPolicy を使用して、特定の namespace 内の pod が別の namespace 内の特定の pod とだけ通信できるように制限するには:

1. **source namespace に NetworkPolicy を適用する**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-specific-communication
  namespace: source-namespace  # Source namespace
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: destination-namespace  # Destination namespace label
      podSelector:
        matchLabels:
          app: specific-app  # Destination pod label
```

2. **destination namespace に NetworkPolicy を適用する**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-specific-namespace
  namespace: destination-namespace  # Destination namespace
spec:
  podSelector:
    matchLabels:
      app: specific-app  # Destination pod label
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: source-namespace  # Source namespace label
```

この方法が機能するには、namespace に適切な label が必要です:
```bash
kubectl label namespace source-namespace name=source-namespace
kubectl label namespace destination-namespace name=destination-namespace
```

NetworkPolicy はデフォルトで allow-list mode で動作するため、これらの policy が適用されると、明示的に許可された通信のみが可能になり、それ以外はすべてブロックされます。
</details>

4. Kubernetes で OPA Gatekeeper を使用して実装できる policy の例を 3 つ説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
OPA Gatekeeper を使用して実装できる policy の例:

1. **Image Registry Restriction**:
   - 承認済み registry からのみ image を pull することを強制する policy
   - 例: company internal registry または特定の trusted public registry のみを許可
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
         - "gcr.io/trusted-project/"
   ```

2. **Enforce Resource Requests and Limits**:
   - すべての container に resource request と limit の設定を強制する policy
   - resource exhaustion を防ぎ、適切な resource allocation を確保します
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits-and-requests
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
       requests:
         - cpu
         - memory
   ```

3. **Prevent Privileged Containers**:
   - privileged container の実行を禁止する policy
   - security risk を低減し、container isolation を確保します
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

（上記のうち 3 つだけを説明すればよい）
</details>

5. Kubernetes で PriorityClass を使用して重要な workload の可用性を確保する方法を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
PriorityClass を使用して重要な workload の可用性を確保する方法:

1. **PriorityClass を定義する**:
   - 重要度に基づいてさまざまな priority level の PriorityClass を作成します
   ```yaml
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000  # Higher value means higher priority
   globalDefault: false
   description: "This priority class should be used for critical production workloads."
   ```

2. **重要な workload に PriorityClass を割り当てる**:
   - 重要な pod に PriorityClass reference を追加します
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: critical-service
   spec:
     priorityClassName: high-priority
     containers:
     - name: app
       image: critical-service:latest
   ```

3. **Preemption を活用する**:
   - resource が不足している場合、priority の高い pod は priority の低い pod を preempt（evict）して schedule されることができます
   - これにより、重要な workload が常に実行できるようになります

4. **System Priority Classes を考慮する**:
   - Kubernetes は system-cluster-critical (2000000000) や system-node-critical (2000001000) などの system priority class を提供します
   - user-defined priority class は通常、これらより低い値を使用するべきです

5. **Priority Hierarchy を設計する**:
   - workload の重要度に基づいて複数の priority level を定義します
   - 例: Production services (900000)、Internal tools (500000)、Development/Test (100000)
</details>

## ハンズオン問題

1. 次の要件を満たす ResourceQuota を作成してください:
   - Namespace: team-a
   - 最大 10 pods
   - 最大 5 services
   - 合計 CPU requests: 4 cores
   - 合計 memory requests: 8Gi

<details>
<summary>答えを表示</summary>

**答え:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    pods: "10"
    services: "5"
    requests.cpu: "4"
    requests.memory: 8Gi
```

適用方法:
```bash
# Create namespace
kubectl create namespace team-a

# Apply ResourceQuota
kubectl apply -f team-a-quota.yaml
```

ResourceQuota status の確認:
```bash
kubectl describe resourcequota team-a-quota -n team-a
```
</details>

2. 次の要件を満たす LimitRange を作成してください:
   - Namespace: team-b
   - Container default request: CPU 100m, Memory 256Mi
   - Container default limit: CPU 200m, Memory 512Mi
   - Container maximum limit: CPU 1 core, Memory 2Gi

<details>
<summary>答えを表示</summary>

**答え:**

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: team-b-limits
  namespace: team-b
spec:
  limits:
  - default:
      cpu: 200m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    max:
      cpu: "1"
      memory: 2Gi
    type: Container
```

適用方法:
```bash
# Create namespace
kubectl create namespace team-b

# Apply LimitRange
kubectl apply -f team-b-limits.yaml
```

LimitRange status の確認:
```bash
kubectl describe limitrange team-b-limits -n team-b
```
</details>

3. 次の要件を満たす NetworkPolicy を作成してください:
   - Namespace: web
   - app label が 'frontend' の pods は app label が 'backend' の pods とのみ通信できる
   - Backend pods は port 8080 の通信のみを許可する

<details>
<summary>答えを表示</summary>

**答え:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-backend-only
  namespace: web
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend-only
  namespace: web
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

適用方法:
```bash
# Create namespace
kubectl create namespace web

# Apply NetworkPolicy
kubectl apply -f web-network-policies.yaml
```

NetworkPolicy status の確認:
```bash
kubectl describe networkpolicy -n web
```
</details>

4. 次の要件で PriorityClass とそれを使用する pod を作成してください:
   - PriorityClass name: high-priority
   - Priority value: 100000
   - Description: "For critical production workloads"
   - Pod name: critical-app
   - Image: nginx

<details>
<summary>答えを表示</summary>

**答え:**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "For critical production workloads"
---
apiVersion: v1
kind: Pod
metadata:
  name: critical-app
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx
```

適用方法:
```bash
kubectl apply -f high-priority-pod.yaml
```

PriorityClass と pod status の確認:
```bash
kubectl get priorityclass high-priority
kubectl get pod critical-app
```
</details>

5. 次の Pod Security 設定を適用してください:
   - Namespace: restricted-ns
   - Mode: enforce
   - Level: restricted

<details>
<summary>答えを表示</summary>

**答え:**

Kubernetes 1.25 以降では、namespace に label を追加することで Pod Security Standards を適用できます:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

適用方法:
```bash
kubectl apply -f restricted-namespace.yaml
```

または、既存の namespace に label を追加します:
```bash
kubectl create namespace restricted-ns
kubectl label namespace restricted-ns \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```
</details>

## 高度なトピック

1. Kubernetes における OPA Gatekeeper と Kyverno の違い、およびそれぞれの pros と cons を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**OPA Gatekeeper vs Kyverno 比較:**

1. **Architecture and Approach**:
   - **OPA Gatekeeper**: Open Policy Agent (OPA) に基づき、Rego policy language を使用します。ConstraintTemplate と Constraint という 2 つの CRD を使用して policy を定義します。
   - **Kyverno**: 独自の policy engine を使用し、YAML/JSON-based の policy definition を提供します。単一の Policy CRD を使用して policy を定義します。

2. **Policy Language**:
   - **OPA Gatekeeper**: Rego language を使用し、強力ですが learning curve が急です。
   - **Kyverno**: Kubernetes resource に似た YAML syntax を使用して policy を定義するため、Kubernetes user にとってより馴染みがあります。

3. **Features**:
   - **OPA Gatekeeper**: 
     - complex policy を表現するための強力な policy language
     - external data に基づく decision のために data source を統合できる
     - policy library と reusable template をサポート
   - **Kyverno**: 
     - 組み込みの resource 作成、変更、検証機能
     - image verification と modification 機能
     - resource が作成されたときに他の resource を自動的に作成できる
     - policy exception handling 機能

4. **Pros**:
   - **OPA Gatekeeper**:
     - より成熟しており、広く採用されている
     - complex policy expression により適している
     - さまざまな use case に対する豊富な documentation と example
     - OPA ecosystem を Kubernetes 以外でも使用可能
   - **Kyverno**:
     - 馴染みのある YAML syntax により learning curve が緩やか
     - 別の policy language の学習が不要
     - 組み込みの resource 作成・変更機能
     - setup と configuration がより簡単

5. **Cons**:
   - **OPA Gatekeeper**:
     - Rego language の学習が必要
     - setup と configuration が複雑
     - resource modification には追加 configuration が必要
   - **Kyverno**:
     - 相対的に成熟度が低い
     - 非常に complex な policy expression には制限がある場合がある
     - OPA と比較して performance が低い場合がある

6. **Selection Criteria**:
   - **Choose OPA Gatekeeper when**:
     - complex policy logic が必要
     - すでに OPA を使用している、または Rego に慣れている
     - さまざまな system 全体で一貫した policy application が必要
   - **Choose Kyverno when**:
     - quick start と容易な learning curve が重要
     - team が Kubernetes resource syntax に慣れている
     - resource 作成・変更機能が必要
     - simple policy のみが必要
</details>

2. Kubernetes における Pod Security Admission と以前の PodSecurityPolicy (PSP) の主な違いを説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**Pod Security Admission vs PodSecurityPolicy (PSP) 比較:**

1. **Implementation**:
   - **PodSecurityPolicy**: API resource（CRD）として実装され、admission controller を通じて適用されます。
   - **Pod Security Admission**: 組み込みの admission controller として実装され、namespace label を通じて構成されます。

2. **Configuration Method**:
   - **PodSecurityPolicy**: Cluster admin は PSP resource を作成し、RBAC を通じて user/service account に bind する必要があります。
   - **Pod Security Admission**: enforcement level（enforce、audit、warn）と policy level（privileged、baseline、restricted）を指定する label を namespace に追加して適用します。

3. **Policy Granularity**:
   - **PodSecurityPolicy**: 非常に細かい制御が可能で、さまざまな security context 設定を個別に構成できます。
   - **Pod Security Admission**: 事前定義された 3 つの policy level（privileged、baseline、restricted）のみを提供し、詳細な設定を個別に調整することはできません。

4. **Ease of Use**:
   - **PodSecurityPolicy**: RBAC binding が必要な複雑な setup で、configuration error がよく発生します。
   - **Pod Security Admission**: simple な namespace labeling で適用でき、はるかに使いやすいです。

5. **Scope**:
   - **PodSecurityPolicy**: cluster 全体または特定の user/service account に適用されます。
   - **Pod Security Admission**: namespace ごとに適用されます。

6. **Modes**:
   - **PodSecurityPolicy**: 適用するかしないかの binary approach。
   - **Pod Security Admission**: 段階的な適用のために 3 つの mode（enforce、audit、warn）を提供します。
     - enforce: violation がある場合、pod 作成を拒否
     - audit: violation を audit log に記録
     - warn: violation がある場合、warning message を表示

7. **Migration and Support**:
   - **PodSecurityPolicy**: Kubernetes v1.25 で削除されました。
   - **Pod Security Admission**: Kubernetes v1.23 から beta として利用可能で、v1.25 で PSP を完全に置き換えました。

8. **Extensibility**:
   - **PodSecurityPolicy**: custom setting による高い extensibility。
   - **Pod Security Admission**: extensibility は限定的で、より細かい制御には OPA Gatekeeper や Kyverno などの追加 tool が必要になる場合があります。
</details>
