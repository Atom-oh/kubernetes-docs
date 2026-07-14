# Linkerd Multi-cluster クイズ

このクイズでは、Linkerd multi-cluster の機能に関する理解度を確認します。

## クイズ問題

### 1. Linkerd multi-cluster アーキテクチャの中核となる概念は何ですか？

A. Mesh federation
B. Service mirroring
C. Cluster merging
D. Global load balancer

<details>
<summary>回答を表示</summary>

**回答: B. Service mirroring**

**解説:**
Linkerd は service mirroring アーキテクチャを使用します。リモート Cluster から export された Service は、ローカル Cluster 内で mirror Service として表示され、ローカル Service と同様にアクセスできます。

</details>

### 2. 2 つの Cluster 間の mTLS 通信で共有する必要があるものは何ですか？

A. Identity Issuer
B. Trust Anchor
C. Workload certificates
D. Kubernetes Secret

<details>
<summary>回答を表示</summary>

**回答: B. Trust Anchor**

**解説:**
2 つの Cluster が相互に信頼するには、同じ Trust Anchor (Root CA) を共有する必要があります。各 Cluster は個別の Identity Issuer を持つことができますが、同じ Trust Anchor によって署名されている必要があります。

</details>

### 3. Service を他の Cluster に export するために使用する label はどれですか？

A. linkerd.io/exported: "true"
B. mirror.linkerd.io/exported: "true"
C. multicluster.linkerd.io/export: "enabled"
D. linkerd.io/multicluster: "export"

<details>
<summary>回答を表示</summary>

**回答: B. mirror.linkerd.io/exported: "true"**

**解説:**
Service に `mirror.linkerd.io/exported: "true"` label を追加すると、他の link された Cluster によって mirror されます。

</details>

### 4. mirror Service の命名形式は何ですか？

A. `<service>.<cluster>`
B. `<service>-<cluster>`
C. `<cluster>-<service>`
D. `<service>@<cluster>`

<details>
<summary>回答を表示</summary>

**回答: B. `<service>-<cluster>`**

**解説:**
mirror Service は `<original-service-name>-<original-cluster-name>` 形式で作成されます。例: west Cluster の web Service は、east Cluster では web-west として mirror されます。

</details>

### 5. `linkerd multicluster link` command の目的は何ですか？

A. 2 つの Cluster 間のネットワーク接続
B. リモート Cluster の認証情報をローカルに登録する
C. Service 間トラフィックルーティングを設定する
D. 証明書の交換

<details>
<summary>回答を表示</summary>

**回答: B. リモート Cluster の認証情報をローカルに登録する**

**解説:**
`linkerd multicluster link --cluster-name <name>` は、別の Cluster に登録するための、現在の Cluster の認証情報（gateway address、Service account token など）を生成します。

</details>

### 6. multi-cluster Gateway の status を確認する command はどれですか？

A. `linkerd multicluster status`
B. `linkerd multicluster gateways`
C. `linkerd multicluster check`
D. `kubectl get gateway`

<details>
<summary>回答を表示</summary>

**回答: B. `linkerd multicluster gateways`**

**解説:**
`linkerd multicluster gateways` は、link された Cluster の Gateway status を表示します。ALIVE、NUM_SVC（mirror された Service の数）、LATENCY が表示されます。

</details>

### 7. EKS multi-cluster における Gateway の推奨設定は何ですか？

A. ClusterIP service
B. NodePort service
C. NLB (Network Load Balancer)
D. ALB (Application Load Balancer)

<details>
<summary>回答を表示</summary>

**回答: C. NLB (Network Load Balancer)**

**解説:**
EKS 上の multi-cluster Gateway には NLB が推奨されます。TCP/TLS トラフィック向けに最適化されており、`service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` annotation で設定します。

</details>

### 8. TrafficSplit を使用してローカル Cluster とリモート Cluster の間でトラフィックを分割する際に、使用される backend Service は何ですか？

A. ローカル Service とリモート Gateway
B. ローカル Service と mirror Service
C. ローカル Service のみ
D. リモート Service への直接参照

<details>
<summary>回答を表示</summary>

**回答: B. ローカル Service と mirror Service**

**解説:**
TrafficSplit backend には、ローカル Service（例: web）と mirror Service（例: web-west）を指定します。mirror Service へのトラフィックは、リモート Cluster の Gateway に自動的にルーティングされます。

</details>

### 9. multi-cluster 環境における mirror controller の役割ではないものは何ですか？

A. リモート Service を監視する
B. mirror Service を作成または更新する
C. 証明書を発行する
D. endpoint を同期する

<details>
<summary>回答を表示</summary>

**回答: C. 証明書を発行する**

**解説:**
service mirror controller はリモート Cluster 内の export された Service を監視し、ローカルで mirror Service を作成または更新して、endpoint を同期します。証明書の発行は Identity Controller の役割です。

</details>

### 10. 2 つの EKS Cluster 間のプライベート接続に使用する AWS Service は何ですか？

A. Direct Connect のみ
B. VPC Peering または Transit Gateway
C. Route 53 のみ
D. CloudFront

<details>
<summary>回答を表示</summary>

**回答: B. VPC Peering または Transit Gateway**

**解説:**
EKS Cluster 間のプライベート接続には、VPC Peering（2 つの VPC 間の直接接続）または Transit Gateway（hub-and-spoke モデル）を使用します。Gateway は internal NLB で設定します。

</details>

### 11. multi-cluster 環境で特定のリモート Service にのみアクセスを許可するにはどうすればよいですか？

A. NetworkPolicy
B. SPIFFE ID を使用した ServerAuthorization
C. AWS Security Group
D. Kubernetes RBAC

<details>
<summary>回答を表示</summary>

**回答: B. SPIFFE ID を使用した ServerAuthorization**

**解説:**
ServerAuthorization の meshTLS.identities でリモート Cluster の特定の SPIFFE ID を指定してアクセスを制御します。例: `spiffe://root.linkerd.cluster.local/ns/production/sa/api-gateway`

</details>

### 12. `linkerd multicluster check` command で検証されないものは何ですか？

A. Link resource status
B. Gateway connectivity
C. Application business logic
D. Service mirror controller status

<details>
<summary>回答を表示</summary>

**回答: C. Application business logic**

**解説:**
`linkerd multicluster check` は、Link resource、Gateway、service mirror controller、証明書を含む multi-cluster infrastructure の status を検証します。Application logic は検証しません。

</details>
