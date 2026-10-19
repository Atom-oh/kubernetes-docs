# Kubernetes ポリシークイズ

このクイズでは、ResourceQuota、LimitRange、Pod Security、NetworkPolicy など、Kubernetes のポリシー概念への理解を確認します。

## 選択問題

1. Kubernetes の ResourceQuota の主な目的は何ですか。
   - A) Pod の CPU とメモリ使用量を制限する
   - B) namespace 内で作成できるリソースを制限する
   - C) クラスター全体のリソース使用量を監視する
   - D) ノードへのリソース割り当てを管理する
   
<details>
<summary>答えを表示</summary>

**答え: B) namespace 内で作成できるリソースを制限する**

**解説:**
ResourceQuota は namespace 内で作成できるリソースの総量を制限します。CPU やメモリなどの計算リソースに加え、Pod、Service、ConfigMap などのオブジェクト数も対象にできます。これにより、特定のチームがクラスターのリソースを独占するのを防ぎます。
</details>

2. LimitRange の主な機能は何ですか。
   - A) namespace 全体のリソース使用量を制限する
   - B) 個々のコンテナに既定の resource requests と limits を設定する
   - C) クラスターのノード間でリソースを分配する
   - D) Pod 間のネットワーク通信を制限する
   
<details>
<summary>答えを表示</summary>

**答え: B) 個々のコンテナに既定の resource requests と limits を設定する**

**解説:**
LimitRange は namespace 内の Pod やコンテナに対するリソース制約を定義します。既定の resource requests と limits を設定したり、リソース使用量の最小値や最大値を強制したりできます。LimitRange は個々のリソースに適用され、ResourceQuota は namespace 全体に適用されます。
</details>

3. Kubernetes v1.25 で PodSecurityPolicy (PSP) が削除された後、どの仕組みがその役割を引き継ぎましたか。
   - A) PodSecurityStandards
   - B) PodSecurityContext
   - C) PodSecurityAdmission
   - D) SecurityContextConstraints
   
<details>
<summary>答えを表示</summary>

**答え: C) PodSecurityAdmission**

**解説:**
PodSecurityPolicy (PSP) は Kubernetes v1.25 で削除され、Pod Security Standards に基づく組み込みの admission controller である Pod Security Admission が代替しました。Privileged、Baseline、Restricted の 3 つのポリシーレベルを提供します。PodSecurityContext は Pod 単位のセキュリティ設定に使われ、SecurityContextConstraints は OpenShift にある類似の仕組みです。
</details>

4. NetworkPolicy では実現できないことは何ですか。
   - A) 特定の namespace から Pod へのトラフィックだけを許可する
   - B) 特定の IP CIDR 範囲からのトラフィックだけを許可する
   - C) 特定のポートへのトラフィックだけを許可する
   - D) 特定のプロトコルのペイロードを検査する
   
<details>
<summary>答えを表示</summary>

**答え: D) 特定のプロトコルのペイロードを検査する**

**解説:**
NetworkPolicy は Pod 間の通信を制御する L3/L4 レベルのファイアウォールポリシーです。namespace、ラベル、IP CIDR 範囲、ポートなどに基づいてトラフィックを制限できます。一方、HTTP ヘッダーやペイロードなどの L7 レベルの検査はできません。その機能には Istio などのサービスメッシュや API ゲートウェイを使用します。
</details>

5. Kubernetes における RBAC (Role-Based Access Control) の主な目的は何ですか。
   - A) Pod 間のネットワーク通信を制御する
   - B) ユーザーと ServiceAccount の権限を管理する
   - C) リソース使用量を制限する
   - D) Pod のスケジューリングポリシーを設定する
   
<details>
<summary>答えを表示</summary>

**答え: B) ユーザーと ServiceAccount の権限を管理する**

**解説:**
RBAC は Kubernetes API へのアクセスを制御する仕組みです。ユーザー、グループ、ServiceAccount が実行できる操作を定義できます。Role、ClusterRole、RoleBinding、ClusterRoleBinding などのリソースを使って権限を管理します。
</details>

6. Pod Security Standards の 3 つのポリシーレベルのうち、最も制限が厳しいものはどれですか。
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>答えを表示</summary>

**答え: C) Restricted**

**解説:**
Pod Security Standards は次の 3 つのポリシーレベルを定義します。
- Privileged: 制限がなく、すべての特権操作を許可する
- Baseline: 既知の権限昇格経路を防ぐ
- Restricted: セキュリティ設定を強化した最も制限の厳しいレベル

Restricted は最小権限の原則に従い、特権コンテナ、host namespace の共有、hostPath volume などを禁止します。
</details>

7. Kubernetes の AdmissionController の役割は何ですか。
   - A) ユーザー認証
   - B) リソース使用量の監視
   - C) API リクエストの検証と変更
   - D) Pod のスケジューリング
   
<details>
<summary>答えを表示</summary>

**答え: C) API リクエストの検証と変更**

**解説:**
AdmissionController は、認証と認可を通過した後、オブジェクトが永続ストレージに保存される前に Kubernetes API サーバーへのリクエストを受け取り、検証または変更するプラグインです。これにより、管理者はリソースの作成や変更にポリシーを適用できます。PodSecurityAdmission、ResourceQuota、LimitRanger などが AdmissionController として実装されています。
</details>

8. Kubernetes における OPA (Open Policy Agent) Gatekeeper の主な機能は何ですか。
   - A) クラスターの監視とログ収集
   - B) ポリシーに基づくリソース管理と検証
   - C) オートスケーリング
   - D) サービスメッシュの管理
   
<details>
<summary>答えを表示</summary>

**答え: B) ポリシーに基づくリソース管理と検証**

**解説:**
OPA Gatekeeper は、Kubernetes クラスターにポリシーを適用する拡張可能な仕組みです。Open Policy Agent (OPA) を基盤とし、CustomResourceDefinition (CRD) でポリシーを定義して適用します。Admission webhook として動作し、作成または変更されるリソースが定義済みのポリシーに準拠しているかを検証します。セキュリティ、リソース制限、命名規則などのポリシーに使用できます。
</details>

9. namespace に CPU/メモリの requests と limits の quota が設定され、admission による既定値もない場合、コンテナにこれらのリソース値を指定していない Pod はどうなりますか。
   - A) 既定の resource requests と limits が設定されて作成される
   - B) Pod の作成が拒否される
   - C) Pod は作成されるがスケジュールされない
   - D) Pod は作成され、無制限にリソースを使用できる
   
<details>
<summary>答えを表示</summary>

**答え: B) Pod の作成が拒否される**

**解説:**
namespace に ResourceQuota があり、CPU やメモリなどの計算リソースに quota が設定されている場合、Pod には admission による既定値の適用後も quota の評価に必要なリソース値が必要です。必要な値が設定されないままなら、作成は拒否されます。LimitRange で既定値を補えますが、オブジェクト数だけを制限する quota では CPU/メモリの値は必須ではありません。これにより、quota の対象となる namespace のリソースを正確に追跡・制限できます。
</details>

10. Kubernetes における PriorityClass の主な目的は何ですか。
    - A) Pod のスケジューリング優先度を定義する
    - B) namespace のリソース割り当て優先度を設定する
    - C) API リクエストの処理優先度を決める
    - D) ノードの重要度を設定する
    
<details>
<summary>答えを表示</summary>

**答え: A) Pod のスケジューリング優先度を定義する**

**解説:**
PriorityClass は Pod のスケジューリング優先度を定義します。リソースが不足している場合、高優先度の Pod は低優先度の Pod より先にスケジュールされ、必要に応じて低優先度の Pod を退避させることがあります。
</details>

## 短答問題

1. ResourceQuota と LimitRange の主な違いを説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
ResourceQuota は namespace 全体のリソース使用量を制限し、LimitRange は namespace 内の個々のコンテナや Pod に制約を設定します。

主な違い:
1. **適用範囲**: ResourceQuota は namespace 全体に適用され、LimitRange は個々のリソース（Pod、コンテナなど）に適用されます。
2. **目的**: ResourceQuota は namespace 全体の使用量を制限し、LimitRange は既定値や最小値・最大値を通じて各リソースの使用量を制御します。
3. **強制方法**: ResourceQuota を超えるリソースの作成は拒否されます。LimitRange はリソース作成時に既定値を適用するか、制限を超えた作成を拒否します。
4. **リソースの種類**: ResourceQuota は CPU、メモリだけでなく、Pod、Service、PVC などのオブジェクト数も制限できます。LimitRange は主に CPU、メモリ、ストレージなどの計算リソースを対象とします。
</details>

2. Pod Security Standards の 3 つのポリシーレベル（Privileged、Baseline、Restricted）とその特徴を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
Pod Security Standards は Pod のセキュリティ設定に対して 3 つのポリシーレベルを定義します。

1. **Privileged**:
   - ほとんど制限のない、最も寛容なポリシーです。
   - すべての特権操作を許可します。
   - host namespace、host port、特権コンテナなどを使用できます。
   - 開発や管理作業には適していますが、本番環境では重大なセキュリティリスクになります。

2. **Baseline**:
   - 既知の権限昇格経路を防ぐ中程度のポリシーです。
   - 多くのワークロードに適した基本的なセキュリティを提供します。
   - 特権コンテナと host namespace の使用を制限します。
   - Baseline でも HostPath volumeは禁止されます。Restricted ではさらに、非 root 実行、seccomp、capability の制限などが求められます。

3. **Restricted**:
   - セキュリティ設定を強化した最も制限の厳しいポリシーです。
   - 最小権限の原則に従い、セキュリティのベストプラクティスを強制します。
   - 特権コンテナ、host namespace、hostPath mount、権限昇格を禁止します。
   - コンテナを非 root ユーザーとして実行することを要求します。
   - セキュリティが特に重要な本番ワークロードに適しています。
</details>

3. NetworkPolicy を使って、ある namespace の Pod が別の namespace にある特定の Pod とのみ通信できるようにする方法を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
NetworkPolicy を使って、ある namespace の Pod が別の namespace にある特定の Pod とのみ通信できるようにするには、次のようにします。

1. **送信元 namespace に NetworkPolicy を適用する**:
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

2. **宛先 namespace に NetworkPolicy を適用する**:
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

この方法を使うには、namespace に適切なラベルが必要です。
```bash
kubectl label namespace source-namespace name=source-namespace
kubectl label namespace destination-namespace name=destination-namespace
```

これらのポリシーが分離するのは、指定した方向の通信だけです。他の NetworkPolicy は許可する通信を追加するため、より広い許可ポリシーを狭めることはできません。名前解決に DNS を使う場合は DNS 向けの egress を別途許可し、送信元と宛先の両方のルールをテストしてください。
</details>

4. Kubernetes で OPA Gatekeeper を使って実装できるポリシーの例を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
OPA Gatekeeper では、次のようなポリシーを実装できます。

まず、公式 Gatekeeper ライブラリから該当する ConstraintTemplate をインストールしてください。ここで使う種類はテンプレートから生成されるもので、組み込み API ではありません。また、ライブラリの K8sRequiredLabels のスキーマは、この章で簡略化して紹介した K8sRequiredLabelKeys とは異なります。

1. **イメージレジストリの制限**:
   - 承認済みのレジストリからのみイメージを pull できるようにします。
   - 例: 社内レジストリ、または信頼できる特定の公開レジストリだけを許可します。
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

2. **resource requests と limits の必須化**:
   - すべてのコンテナに resource requests と limits の設定を要求します。
   - リソース枯渇を防ぎ、適切なリソース割り当てを確保します。
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

3. **特権コンテナの禁止**:
   - 特権コンテナの実行を禁止します。
   - セキュリティリスクを低減し、コンテナの分離を保ちます。
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

4. **ホストファイルシステムへのアクセス制限**（対応するライブラリテンプレートが必要）:
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPHostFilesystem
   metadata:
     name: prevent-host-filesystem-mount
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod"]
     parameters:
       allowedHostPaths: []
   ```

5. **値を制約したラベルの必須化**:
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredLabels
   metadata:
     name: require-team-label
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod", "Service"]
       - apiGroups: ["apps"]
         kinds: ["Deployment"]
     parameters:
       labels:
       - key: team
         allowedRegex: "^(frontend|backend|infra)$"
       - key: environment
         allowedRegex: "^(dev|staging|prod)$"
   ```

（上記から 3 つだけ説明すればかまいません。）
</details>

5. Kubernetes で PriorityClass を使って重要なワークロードの可用性を高める方法を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
PriorityClass を使って重要なワークロードの可用性を高めるには、次のようにします。

1. **PriorityClass を定義する**:
   - 重要度に応じて、異なる優先度の PriorityClass を作成します。
   ```yaml
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000  # Higher value means higher priority
   globalDefault: false
   description: "This priority class should be used for critical production workloads."
   ```

2. **重要なワークロードに PriorityClass を割り当てる**:
   - 重要な Pod に PriorityClass を指定します。
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
   - リソースが不足すると、高優先度の Pod が低優先度の Pod を退避させてスケジュールされることがあります。
   - これによりスケジューリング上の優先度は高まりますが、制約や容量不足が残る場合に配置を保証するものではありません。

4. **システム用 PriorityClass を考慮する**:
   - Kubernetes には system-cluster-critical (2000000000) や system-node-critical (2000001000) などのシステム用 PriorityClass があります。
   - ユーザー定義の PriorityClass の値は最大 1,000,000,000 です。それを超える値はシステム用に予約されています。

5. **優先度の階層を設計する**:
   - ワークロードの重要度に応じて複数の優先度を定義します。
   - 例: 本番サービス (900000)、社内ツール (500000)、開発/テスト (100000)。
</details>

## ハンズオン問題

1. 次の要件を満たす ResourceQuota を作成してください。
   - Namespace: team-a
   - Pod は最大 10 個
   - Service は最大 5 個
   - CPU requests の合計: 4 cores
   - memory requests の合計: 8Gi

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

ResourceQuota の状態を確認する:
```bash
kubectl describe resourcequota team-a-quota -n team-a
```
</details>

2. 次の要件を満たす LimitRange を作成してください。
   - Namespace: team-b
   - コンテナの既定 request: CPU 100m、Memory 256Mi
   - コンテナの既定 limit: CPU 200m、Memory 512Mi
   - コンテナの最大 limit: CPU 1 core、Memory 2Gi

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

LimitRange の状態を確認する:
```bash
kubectl describe limitrange team-b-limits -n team-b
```
</details>

3. 次の要件を満たす NetworkPolicy を作成してください。
   - Namespace: web
   - app ラベルが 'frontend' の Pod は、app ラベルが 'backend' の Pod とのみ通信できる
   - Backend Pod が許可する通信は port 8080 のみ

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

NetworkPolicy の状態を確認する:
```bash
kubectl describe networkpolicy -n web
```
</details>

4. 次の要件を満たす PriorityClass と、それを使う Pod を作成してください。
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

PriorityClass と Pod の状態を確認する:
```bash
kubectl get priorityclass high-priority
kubectl get pod critical-app
```
</details>

5. 次の Pod Security 設定を適用してください。
   - Namespace: restricted-ns
   - Mode: enforce
   - Level: restricted

<details>
<summary>答えを表示</summary>

**答え:**

Kubernetes 1.25 以降では、namespace にラベルを追加して Pod Security Standards を適用できます。

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

既存の namespace にラベルを追加する方法もあります。
```bash
kubectl create namespace restricted-ns
kubectl label namespace restricted-ns \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```
</details>

## 発展トピック

1. Kubernetes における OPA Gatekeeper と Kyverno の違い、およびそれぞれの長所と短所を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**OPA Gatekeeper と Kyverno の比較:**

1. **アーキテクチャとアプローチ**:
   - **OPA Gatekeeper**: Open Policy Agent (OPA) を基盤とし、Rego ポリシー言語を使います。ConstraintTemplate と Constraint の 2 つの CRD でポリシーを定義します。
   - **Kyverno**: 独自のポリシーエンジンを使い、YAML/JSON ベースでポリシーを定義します。バージョンに応じて、Policy/ClusterPolicy に加え、専用の cleanup/CEL ポリシー API など複数のポリシー種別を提供します。

2. **ポリシー言語**:
   - **OPA Gatekeeper**: 表現力が高い一方、習得には時間がかかる Rego を使います。
   - **Kyverno**: Kubernetes リソースに似た YAML 構文でポリシーを定義するため、Kubernetes ユーザーにとって馴染みやすい方法です。

3. **機能**:
   - **OPA Gatekeeper**:
     - 複雑なポリシーを表現できる
     - 外部データに基づく判断のためのデータソースを統合できる
     - ポリシーライブラリと再利用可能なテンプレートをサポートする
   - **Kyverno**:
     - リソースの生成、変更、検証の機能を標準で備える
     - イメージの検証や変更に対応する
     - リソース作成時に別のリソースを自動生成できる
     - ポリシー例外を扱う機能を備える

4. **長所**:
   - **OPA Gatekeeper**:
     - 成熟した Rego のポリシーエコシステムと再利用可能なテンプレートがある
     - 複雑なポリシー表現に適している
     - さまざまな用途に関するドキュメントや例が豊富
     - OPA エコシステムを Kubernetes 以外でも利用できる
   - **Kyverno**:
     - 馴染みのある YAML 構文を使うため習得しやすい
     - 別のポリシー言語を学ぶ必要がない
     - リソース生成と変更の機能が組み込まれている
     - セットアップと構成が比較的簡単

5. **短所**:
   - **OPA Gatekeeper**:
     - Rego の習得が必要
     - セットアップと構成が複雑
     - リソースの変更には追加設定が必要
   - **Kyverno**:
     - バージョンごとに CRD と機能の互換性を確認する必要がある
     - 非常に複雑なポリシー表現には制約がある場合がある
     - 代表的なポリシーと admission 負荷を使ってベンチマークしてください。どちらのエンジンが常に高性能かを示す普遍的な順位はありません。

6. **選択基準**:
   - **OPA Gatekeeper を選ぶ場合**:
     - 複雑なポリシーロジックが必要
     - すでに OPA を使用している、または Rego に習熟している
     - 複数のシステムで一貫したポリシー適用が必要
   - **Kyverno を選ぶ場合**:
     - すぐに使い始められることと習得のしやすさを重視する
     - チームが Kubernetes リソースの構文に馴染んでいる
     - リソースの生成、変更、検証の機能が必要
     - Kubernetes に馴染みのある方法で、変更、生成、検証、イメージ検証を行う要件に合っている
</details>

2. Kubernetes における Pod Security Admission と従来の PodSecurityPolicy (PSP) の主な違いを説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**Pod Security Admission と PodSecurityPolicy (PSP) の比較:**

1. **実装**:
   - **PodSecurityPolicy**: 組み込みの API リソース（CRD ではありません）として実装され、admission controller を通じて適用されていました。
   - **Pod Security Admission**: 組み込みの admission controller として実装され、namespace のラベルで設定します。

2. **設定方法**:
   - **PodSecurityPolicy**: クラスター管理者が PSP リソースを作成し、RBAC を使ってユーザーや ServiceAccount にバインドする必要がありました。
   - **Pod Security Admission**: 適用モード（enforce、audit、warn）とポリシーレベル（privileged、baseline、restricted）を示すラベルを namespace に追加します。

3. **ポリシーの粒度**:
   - **PodSecurityPolicy**: さまざまな security context 設定を個別に構成できる、細かな制御が可能でした。
   - **Pod Security Admission**: 事前定義された 3 つのポリシーレベル（privileged、baseline、restricted）のみを提供し、個々の設定を調整することはできません。

4. **使いやすさ**:
   - **PodSecurityPolicy**: RBAC binding を必要とする複雑なセットアップで、設定ミスが起こりやすい仕組みでした。
   - **Pod Security Admission**: namespace にラベルを付けるだけで適用でき、より簡単です。

5. **適用範囲**:
   - **PodSecurityPolicy**: クラスター全体、または特定のユーザーや ServiceAccount に適用されていました。
   - **Pod Security Admission**: namespace ごとに適用します。

6. **モード**:
   - **PodSecurityPolicy**: 適用するか適用しないかの二択でした。
   - **Pod Security Admission**: 段階的な適用のために 3 つのモードを提供します。
     - enforce: 違反がある場合、Pod の作成を拒否する
     - audit: 違反を audit log に記録する
     - warn: 違反がある場合、警告メッセージを表示する

7. **移行とサポート**:
   - **PodSecurityPolicy**: Kubernetes v1.25 で削除されました。
   - **Pod Security Admission**: Kubernetes v1.23 から beta として利用可能で、v1.25 で PSP を完全に置き換えました。

8. **拡張性**:
   - **PodSecurityPolicy**: 個別設定による高い拡張性がありました。
   - **Pod Security Admission**: 拡張性は限定的です。より細かな制御には OPA Gatekeeper や Kyverno などの追加ツールが必要になる場合があります。
</details>

3. 外部認可 webhook が Kubernetes RBAC をどのように補完するか、また認可方式の順序が重要な理由を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

自己管理の API サーバーでは、endpoint、CA、クライアント証明書、秘密鍵を指定した kubeconfig を使い、TLS 認証する webhook を設定します。フラグを使う例は次のとおりです。

```text
--authorization-mode=Node,RBAC,Webhook
--authorization-webhook-config-file=/path/to/webhook-config.yaml
--authorization-webhook-version=v1
```

Webhook は、認証済みユーザー/グループとリクエスト属性を含む `authorization.k8s.io/v1` SubjectAccessReview を受け取り、`allowed: true` などを含む SubjectAccessReview status を返します。通信資格情報を検証し、エラーやタイムアウトを意図どおり処理し、bearer token や機密リクエストデータをログに記録しないようにしてください。

**認可チェーンは最初の allow または deny で停止します。** `Node,RBAC,Webhook` の順序では、RBAC が許可すると webhook は呼び出されません。後続の webhook でその許可を拒否することはできません。外部ポリシーによる拒否を必須にするには、適切な順序や失敗時ポリシーを設定するか、admission による強制を検討してください。構造化された AuthorizationConfiguration では追加の webhook 制御を設定できます。EKS では API サーバーの任意の認可フラグを指定できません。

OPA adapter は Rego で review を評価できます。次の OPA 1.x の例では、現在のルール構文を使います。

```rego
package kubernetes.authz

default allow := false

allow if {
    input.spec.resourceAttributes.namespace == "default"
    input.spec.resourceAttributes.resource == "deployments"
    input.spec.resourceAttributes.verb == "get"
    input.spec.user == "jane"
    "developers" in input.spec.groups
}
```

互換性のある OPA バージョンをデプロイし、ポリシーバンドルを読み込み、review を OPA input として送信して、その結果を SubjectAccessReview status に対応付ける adapter を実装してください。OPA を単独で Deployment しただけでは、認可 webhook として完成しません。ポリシーの一元管理、外部属性の利用、監査性が利点ですが、可用性、レイテンシー、キャッシュ TTL、拒否時の挙動をテストする必要があります。
</details>

4. NetworkPolicy を使ったマルチテナントのネットワーク分離を設計してください。

<details>
<summary>答えを表示</summary>

**答え:**

各テナントの namespace に ingress/egress の両方を拒否する default-deny policy を用意します。その後、テナント内の広い通信を許可するか、役割ごとの細かなルールを使うかを選びます。NetworkPolicy は許可を加算するため、同一 namespace 内を広く許可するポリシーと細かな制限を併用すると、広い許可が役割別の制限を無効にします。

テナント内の広い通信を許可する場合は、両方向を許可します。ingress だけを許可しても、default egress deny は解除されません。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
```

より細かな分離には、`role: backend` や `tier: web` などのラベルを選択します。別テナントに一部の API だけを公開する場合は、namespace selector と Pod selector を同じ peer に組み合わせ、宛先ポートを明示してください。組み込みの `kubernetes.io/metadata.name` namespace ラベルを使うか、保護されたテナントラベルの規約を運用します。

共有サービスへのアクセスには、送信元の egress と宛先の ingress の両方が必要です。テナントから Prometheus の port 9090 への接続を許可しても、Prometheus がテナントの Pod を scrape する許可にはなりません。scrape には逆方向の通信経路が必要です。外部 egress は適切な IP 範囲と TCP port で制限するか、IP 指定が適さない場合はドメインベースのポリシーに対応した実装を使います。

DNS egress には通常、次のルールが必要です（NodeLocal DNS や異なるラベルを使う場合は調整してください）。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

NetworkPolicy を強制する CNI を使い、RBAC と admission rule で namespace/Pod のラベル変更を保護し、ポリシーをバージョン管理してください。許可される通信と拒否される通信の両方をテストします。標準の NetworkPolicy は L7 認証を提供せず、ノードや hostNetwork に関する既知の制約があります。
</details>

5. ResourceQuota と LimitRange を組み合わせたリソース管理戦略を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

- クラスター単位ではノード容量、オートスケーリング、ワークロード分離を計画します。namespace 単位では要求/上限の計算リソース、ストレージ、オブジェクト数を制限します。ワークロード単位では計測に基づいて resource requests と Pod priority を設定します。
- PVC の割り当てには `requests.storage` と `<class>.storageclass.storage.k8s.io/requests.storage` を使います。任意のオブジェクト数には `count/deployments.apps` や `count/statefulsets.apps` などのキーを使います。`deployments.apps` だけではオブジェクト数の指定になりません。
- 各 PriorityClass に対し、`scopeSelector` と `hard.pods` を使った別々の quota を適用します。PriorityClass は Pod に属し、namespace に直接属するものではありません。
- Container 用の LimitRange entry で既定値と最小/最大値の検証を設定します。Pod 用 entry はリソースの合計を制約し、PVC 用 entry はストレージ要求を制約します。どちらも既定値は設定しません。

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: object-counts
  namespace: team-a
spec:
  hard:
    pods: "50"
    services: "10"
    services.loadbalancers: "2"
    services.nodeports: "5"
    secrets: "20"
    configmaps: "20"
    count/deployments.apps: "10"
    count/statefulsets.apps: "5"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: storage-limits
  namespace: team-a
spec:
  limits:
  - type: PersistentVolumeClaim
    min:
      storage: 1Gi
    max:
      storage: 100Gi
```

ResourceQuota と LimitRange に組み込みの audit-only mode はありません。テスト用 namespace や、適用可能な場合は dry-run で変更を評価してください。実使用量とは別に quota の割り当てを監視し、上限に達する前にアラートを出し、測定値に基づいて調整します。動的な quota 変更、借用、共有プール、chargeback には追加の controller や自動化が必要です。組み込みの hard quota では一時的な超過は許可されません。Quota は admission を制限するもので、ワークロードの性能を保証するものではありません。
</details>
