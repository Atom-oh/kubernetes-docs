# Cilium L2-L7 ネットワーキングとロードバランシングクイズ

このクイズでは、Cilium の L2-L7 ネットワーキング機能、ロードバランシングアーキテクチャ、マスカレーディング、Service Mesh 統合などに関する理解度を確認します。

## 選択式問題

1. OSI モデルにおいて、HTTP、gRPC、DNS などのプロトコルはどの層で動作しますか？
   - A) L3（ネットワーク層）
   - B) L4（トランスポート層）
   - C) L5（セッション層）
   - D) L7（アプリケーション層）

<details>

<summary>回答を表示</summary>

**回答: D) L7（アプリケーション層）**

**解説:**
OSI モデルでは、L7（アプリケーション層）はユーザーに最も近い層であり、HTTP、HTTPS、gRPC、DNS、FTP、Kafka などのアプリケーションプロトコルが動作します。Cilium は L7 層で API 対応フィルタリングを提供し、HTTP メソッド/パス/ヘッダー、gRPC メソッド、Kafka トピックなどに基づくきめ細かなネットワークポリシーを可能にします。これは、マイクロサービスアーキテクチャにおけるサービス間通信を詳細に制御するために不可欠です。
</details>

2. Cilium の DSR（Direct Server Return）モードの主な利点は何ですか？
   - A) クライアント IP を隠せる
   - B) レスポンストラフィックがロードバランサーをバイパスし、パフォーマンスが向上する
   - C) すべてのトラフィックを暗号化する
   - D) L7 ポリシーを自動的に適用する

<details>

<summary>回答を表示</summary>

**回答: B) レスポンストラフィックがロードバランサーをバイパスし、パフォーマンスが向上する**

**解説:**
DSR（Direct Server Return）モードでは、クライアントリクエストのみがロードバランサーを通過し、サーバーレスポンスはロードバランサーをバイパスして直接クライアントに送信されます。これにより、ロードバランサーのボトルネックが解消され、ネットワーク帯域幅を節約し、レスポンスレイテンシーを削減します。特に大きなレスポンス（ファイルダウンロード、ストリーミングなど）を処理する場合に効果的です。DSR モードは、外部ロードバランサーの背後でもクライアント IP を保持します。
</details>

3. Cilium で L7 プロキシ機能を提供するコンポーネントはどれですか？
   - A) kube-proxy
   - B) Hubble
   - C) Envoy
   - D) CoreDNS

<details>

<summary>回答を表示</summary>

**回答: C) Envoy**

**解説:**
Cilium は L7 プロキシ機能のために Envoy プロキシを統合しています。CiliumNetworkPolicy で L7 ルール（HTTP、gRPC、Kafka、DNS など）を定義すると、Cilium はサイドカーを使用せずに Envoy プロキシを透過的に自動デプロイします。Envoy は HTTP/gRPC トラフィック処理、高度なロードバランシング、トラフィック分割、メトリクス収集を提供します。このアプローチでは、個別のサイドカープロキシをデプロイする必要がないため、リソースオーバーヘッドを削減できます。
</details>

4. 次のうち、Cilium がサポートしていないロードバランシングアルゴリズムはどれですか？
   - A) Round Robin
   - B) Maglev Consistent Hashing
   - C) Source IP Hash
   - D) Weighted Response Time

<details>

<summary>回答を表示</summary>

**回答: D) Weighted Response Time**

**解説:**
Cilium は、Round Robin、Least Connection、Source IP Hash、Random、Maglev Consistent Hashing などのロードバランシングアルゴリズムをサポートしています。Maglev は Google が開発した一貫性ハッシュアルゴリズムで、バックエンドサーバーが追加または削除されても接続の一貫性を維持します。Weighted Response Time は Cilium で直接サポートされているアルゴリズムではありません。ただし、より高度なロードバランシング戦略は Envoy プロキシを通じて実装できます。
</details>

5. Cilium のマスカレーディングにおける eBPF ベース実装の利点ではないものはどれですか？
   - A) iptables より高速な処理
   - B) 優れたスケーラビリティ
   - C) すべての Linux カーネルバージョンでサポートされる
   - D) カーネル空間で直接処理する

<details>

<summary>回答を表示</summary>

**回答: C) すべての Linux カーネルバージョンでサポートされる**

**解説:**
eBPF ベースのマスカレーディングは、カーネル空間で直接処理するため、iptables より高速で、スケーラビリティと効率性に優れています。ただし、eBPF ベースのマスカレーディングが完全にサポートされるのは、比較的新しい Linux カーネル（4.19 以降）のみです。古いカーネルでは、iptables ベースのマスカレーディングにフォールバックする必要があります。Cilium 設定の `enable-bpf-masquerade: true` オプションで eBPF ベースのマスカレーディングを有効にできます。
</details>

6. Kubernetes Service 用に kube-proxy を完全に置き換える Cilium のモードはどれですか？
   - A) kube-proxy-replacement: partial
   - B) kube-proxy-replacement: strict
   - C) kube-proxy-replacement: hybrid
   - D) kube-proxy-replacement: disabled

<details>

<summary>回答を表示</summary>

**回答: B) kube-proxy-replacement: strict**

**解説:**
`kube-proxy-replacement: strict` 設定により、Cilium はすべての kube-proxy 機能を完全に置き換えます。このモードでは、Cilium がすべての ClusterIP、NodePort、LoadBalancer、ExternalIP Service を処理します。strict モードでは、kube-proxy を削除または無効化する必要があります。`partial` モードは一部の機能のみを置き換え、`disabled` は kube-proxy 置換を無効にします。DSR、Maglev ハッシュ、ソケットレベルのロードバランシングなどの高度な機能を使用する場合は strict モードが必要です。
</details>

7. Cilium L7 ポリシーで HTTP リクエストをフィルタリングするために使用できない条件はどれですか？
   - A) HTTP メソッド（GET、POST など）
   - B) URL パス
   - C) HTTP ヘッダー
   - D) リクエスト本文

<details>

<summary>回答を表示</summary>

**回答: D) リクエスト本文**

**解説:**
Cilium L7 HTTP ポリシーは、HTTP メソッド（GET、POST、PUT、DELETE など）、URL パス（正規表現をサポート）、HTTP ヘッダー（正規表現をサポート）に基づいてフィルタリングできます。ただし、リクエスト本文の検査は、大きなパフォーマンスオーバーヘッドと複雑さのため、Cilium では直接サポートされていません。リクエスト本文の検査が必要な場合は、WAF（Web Application Firewall）または別のアプリケーション層セキュリティソリューションを使用する必要があります。
</details>

8. Cilium と Istio を統合する主な利点は何ですか？
   - A) すべての Istio 機能を完全に置き換える
   - B) eBPF ベースのデータプレーンによりサイドカーオーバーヘッドを削減する
   - C) mTLS を自動的に無効化する
   - D) Istio を使用せずに Service Mesh を実装する

<details>

<summary>回答を表示</summary>

**回答: B) eBPF ベースのデータプレーンによりサイドカーオーバーヘッドを削減する**

**解説:**
Cilium と Istio を統合すると、Envoy サイドカー機能の一部を eBPF ベースのデータプレーンに置き換えられるため、リソースオーバーヘッドを削減できます。Cilium は L3/L4 トラフィック処理とネットワークポリシーを eBPF で処理し、必要な L7 トラフィックのみを Envoy に転送します。これにより、パフォーマンスが向上し、レイテンシーが削減されます。ただし、Cilium はすべての Istio 機能を置き換えるわけではなく、mTLS などの高度な Istio 機能は引き続き Istio によって処理されます。
</details>

9. Cilium におけるソケットレベルのロードバランシングの利点は何ですか？
   - A) パケット処理前にカーネル内で Service IP をバックエンド IP に変換する
   - B) L7 ポリシーを自動的に適用する
   - C) 暗号化されたトラフィックのみを処理する
   - D) 外部ロードバランサーが必要である

<details>

<summary>回答を表示</summary>

**回答: A) パケット処理前にカーネル内で Service IP をバックエンド IP に変換する**

**解説:**
ソケットレベルのロードバランシングは、パケットが送信される前の connect() システムコールで、Service IP をバックエンド Pod IP に変換します。これは従来のパケットベース NAT（Network Address Translation）よりはるかに効率的です。利点には、conntrack（接続追跡）オーバーヘッドの削減、送信元 IP の保持、低レイテンシー、優れたスケーラビリティが含まれます。ソケットレベル LB はアプリケーションの観点から透過的に動作するため、アプリケーションはバックエンド Pod と直接通信しているように見えます。
</details>

10. Cilium における IPv4 フラグメント処理に関する推奨ベストプラクティスは何ですか？
    - A) 常にフラグメント追跡を無効にする
    - B) フラグメンテーションを防ぐために MTU を一貫して設定する
    - C) すべてのフラグメントをブロックする
    - D) フラグメントサイズを最大に設定する

<details>

<summary>回答を表示</summary>

**回答: B) フラグメンテーションを防ぐために MTU を一貫して設定する**

**解説:**
IPv4 フラグメンテーションはパフォーマンス低下やセキュリティ上の問題を引き起こす可能性があるため、可能な限り防止する必要があります。そのためには、ネットワーク全体で MTU（Maximum Transmission Unit）を一貫して設定し、オーバーレイネットワーク（VXLAN など）を使用する場合は、カプセル化オーバーヘッド（約 50 バイト）を考慮して MTU を調整します。Path MTU Discovery（PMTUD）を有効にすると、最適な MTU を自動検出できます。フラグメント追跡（`enable-ipv4-fragment-tracking`）を有効にすると、フラグメントベースの攻撃を防止できます。
</details>

## 短答式問題

11. Cilium が L7 ネットワークポリシーでサポートするプロトコルを 4 つ挙げてください。

<details>

<summary>回答を表示</summary>

**回答:** HTTP、gRPC、Kafka、DNS

**解説:**
Cilium L7 ポリシーでサポートされる主なプロトコルは次のとおりです。
- **HTTP/HTTPS**: REST API と Web トラフィック。メソッド/パス/ヘッダーベースのフィルタリングをサポート
- **gRPC**: マイクロサービス間の RPC 通信。Service/メソッドベースのフィルタリングをサポート
- **Kafka**: メッセージキュープロトコル。トピック/clientID/API キーベースのフィルタリングをサポート
- **DNS**: DNS クエリおよびレスポンスのフィルタリング。FQDN ベースのポリシーをサポート
さらに、カスタムプロトコルは Envoy フィルターを通じてサポートできます。
</details>

12. Cilium ロードバランサーにおいて、バックエンドサーバーのヘルスチェックを行うメカニズムの名前は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** Health Check

**解説:**
Cilium ロードバランサーは複数のヘルスチェックメカニズムをサポートしています。
- **TCP ヘルスチェック**: ポート接続性を検証
- **HTTP ヘルスチェック**: HTTP レスポンスコード（200 OK など）を検証
- **Kubernetes Readiness/Liveness Probe 統合**: Pod ステータス Probe の結果を使用
異常なバックエンドはロードバランシングプールから自動的に削除され、復旧時に再追加されます。これにより、Service の高可用性が確保されます。
</details>

13. Cilium で外部トラフィックの送信元 IP を内部 IP に変換する機能の名前は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** Masquerading または SNAT（Source NAT）

**解説:**
Masquerading は、クラスター内の Pod から送信されるアウトバウンドトラフィックの送信元 IP を Node の IP に変換する機能です。これは SNAT（Source Network Address Translation）の一種です。Masquerading の目的は、内部クラスター IP を外部ネットワークから隠し、クラスター外部の Service へのアクセスを可能にすることです。Cilium は iptables ベースと eBPF ベースの両方の Masquerading をサポートしており、eBPF ベースの方が高いパフォーマンスを提供します。
</details>

14. Cilium が kube-proxy を置き換える際にセッション永続性のために使用するハッシュアルゴリズムの名前は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** Maglev（Consistent Hashing）

**解説:**
Maglev は Google が開発した一貫性ハッシュアルゴリズムです。Cilium で Maglev を使用すると、バックエンドサーバーが追加または削除された場合でも、既存の接続の大部分は同じバックエンドに維持されます。これはセッションアフィニティを必要とするアプリケーションにとって重要です。Maglev は高い負荷分散均一性と低い接続再分散率を提供するため、大規模なロードバランシング環境で効果的です。
</details>

15. TCP および UDP プロトコルが動作する OSI モデルの層の名前と番号は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** L4（トランスポート層）

**解説:**
L4（トランスポート層）は OSI モデルの第 4 層であり、エンドツーエンドの接続と信頼性を担います。TCP（Transmission Control Protocol）と UDP（User Datagram Protocol）はこの層で動作します。TCP はコネクション型で信頼性の高い通信を提供する一方、UDP はコネクションレスで高速ですが、信頼性を保証しません。Cilium L4 ポリシーはポート番号とプロトコル（TCP/UDP）に基づいてトラフィックをフィルタリングできます。
</details>

## ハンズオン問題

16. `/api/v1/users` パスへの HTTP GET リクエストのみを許可し、`X-Auth-Token` ヘッダーが存在する場合にのみ `/api/v1/data` パスへの POST リクエストを許可する CiliumNetworkPolicy を作成してください。

<details>

<summary>回答を表示</summary>

**回答:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l7-http-policy"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/users"
        - method: "POST"
          path: "/api/v1/data"
          headers:
          - "X-Auth-Token: .*"
```

**解説:**
この CiliumNetworkPolicy は、L7 HTTP ルールを使用してきめ細かなアクセス制御を実装します。`rules.http` セクションでは 2 つのルールを定義します。1 つ目は `/api/v1/users` パスへの GET メソッドを許可し、2 つ目は `X-Auth-Token` ヘッダーが存在する場合にのみ `/api/v1/data` パスへの POST メソッドを許可します。ヘッダー値は正規表現で指定できるため、`.*` は任意の値を許可します。このポリシーを適用すると、Cilium は L7 トラフィックを検査するために Envoy プロキシを透過的に自動デプロイします。
</details>

17. DSR モードおよび Maglev ハッシュを有効にした kube-proxy 置換モードで Cilium をインストールする Helm コマンドを作成してください。

<details>

<summary>回答を表示</summary>

**回答:**
```bash
# Add Helm repo
helm repo add cilium https://helm.cilium.io/
helm repo update

# Install Cilium with kube-proxy replacement + DSR + Maglev settings
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=<API_SERVER_IP> \
  --set k8sServicePort=6443 \
  --set loadBalancer.mode=dsr \
  --set loadBalancer.algorithm=maglev \
  --set maglev.tableSize=65521 \
  --set bpf.masquerade=true

# Disable existing kube-proxy (delete or scale down DaemonSet)
kubectl -n kube-system delete ds kube-proxy
# Or modify kube-proxy ConfigMap to disable

# Verify installation
cilium status --verbose
kubectl -n kube-system exec ds/cilium -- cilium status | grep KubeProxyReplacement
```

**解説:**
`kubeProxyReplacement=true` は、kube-proxy 機能を置き換えるよう Cilium を設定します。`k8sServiceHost` と `k8sServicePort` は API server のアドレスを指定します（kube-proxy なしで API server にアクセスするために必要です）。`loadBalancer.mode=dsr` は Direct Server Return モードを有効にし、`loadBalancer.algorithm=maglev` は Maglev 一貫性ハッシュを使用します。`maglev.tableSize` はハッシュテーブルのサイズを設定します（素数を推奨）。`bpf.masquerade=true` は eBPF ベースの Masquerading を有効にします。
</details>

18. Kafka トラフィックに L7 ポリシーを適用し、`orders` トピックへの produce 操作のみ、および `payments` トピックからの consume 操作のみを許可する CiliumNetworkPolicy を作成してください。

<details>

<summary>回答を表示</summary>

**回答:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "kafka-l7-policy"
  namespace: messaging
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: order-service
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: "produce"
          topic: "orders"
  - fromEndpoints:
    - matchLabels:
        app: payment-processor
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: "fetch"
          topic: "payments"
```

**解説:**
この CiliumNetworkPolicy は、Kafka L7 ルールを使用してきめ細かなアクセス制御を実装します。最初の ingress ルールは、`order-service` Pod が `orders` トピックに対して produce（`apiKey: produce`）操作のみを実行することを許可します。2 つ目のルールは、`payment-processor` Pod が `payments` トピックから consume（`apiKey: fetch`）操作のみを実行することを許可します。Kafka API キーには `produce`、`fetch`、`metadata`、`offsets` などがあり、`clientID` を追加して特定のクライアントのみを許可することもできます。
</details>

19. 特定の CIDR 範囲（10.0.0.0/8）に対するマスカレーディングを除外しながら、Cilium で eBPF ベースのマスカレーディングを有効にする設定を作成してください。

<details>

<summary>回答を表示</summary>

**回答:**
```yaml
# ConfigMap settings
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  enable-ipv4-masquerade: "true"
  enable-bpf-masquerade: "true"
  ipv4-native-routing-cidr: "10.0.0.0/8"
  enable-ipv6-masquerade: "false"
```

```bash
# Install/upgrade using Helm
helm upgrade cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set ipv4NativeRoutingCIDR=10.0.0.0/8 \
  --set bpf.masquerade=true \
  --set enableIPv4Masquerade=true

# Verify settings
kubectl -n kube-system exec ds/cilium -- cilium status --verbose | grep -i masquerade

# Check masquerading rules
kubectl -n kube-system exec ds/cilium -- cilium bpf nat list
```

**解説:**
`enable-bpf-masquerade: true` は eBPF ベースのマスカレーディングを有効にします。`ipv4-native-routing-cidr: 10.0.0.0/8` は、この CIDR 範囲へのトラフィックがマスカレーディングなしでネイティブルーティングを使用するよう設定します。これは、クラスター内通信または VPC 内通信で送信元 IP を保持する必要がある場合に役立ちます。クラスター Pod CIDR と Service CIDR がこの範囲に含まれる場合、内部トラフィックにはマスカレーディングが適用されません。
</details>

20. Cilium で L7 ポリシーが期待どおりに動作しない場合に問題を診断するコマンドを作成してください。Envoy プロキシのステータス、ポリシー適用ステータス、リアルタイムトラフィック監視を含めてください。

<details>

<summary>回答を表示</summary>

**回答:**
```bash
# 1. Check overall Cilium status
cilium status --verbose

# 2. Check Envoy proxy status
kubectl -n kube-system exec ds/cilium -- cilium status | grep -i proxy
kubectl -n kube-system exec ds/cilium -- cilium bpf proxy list

# 3. Check policy application status
cilium policy get
kubectl get cnp -A -o wide
kubectl get ccnp -A -o wide

# 4. Check policy status for a specific endpoint
cilium endpoint list
cilium endpoint get <endpoint_id> -o json | jq '.status.policy'

# 5. Real-time traffic monitoring (including L7)
cilium monitor --type l7
cilium monitor --type policy-verdict
cilium monitor --type drop

# 6. Observe L7 flows through Hubble
hubble observe --protocol http
hubble observe --verdict DROPPED
hubble observe --pod <namespace>/<pod-name>

# 7. Check Envoy logs
kubectl -n kube-system logs ds/cilium | grep -i envoy
kubectl -n kube-system logs ds/cilium | grep -i proxy

# 8. Regenerate endpoint (reapply policy)
kubectl -n kube-system exec ds/cilium -- cilium endpoint regenerate <endpoint_id>

# 9. Network policy troubleshooting
cilium policy trace --src-identity <src_id> --dst-identity <dst_id> --dport <port>
```

**解説:**
L7 ポリシーの問題をトラブルシューティングするには、体系的なアプローチが必要です。まず、`cilium status` でシステム全体のステータスを確認し、Envoy プロキシが正常に動作していることを検証します。`cilium policy get` で適用済みポリシーを確認し、`cilium endpoint get` で特定の Pod にポリシーが正しく適用されていることを検証します。`cilium monitor` と `hubble observe` でリアルタイムトラフィックおよびポリシー判定を監視します。`policy trace` コマンドは、特定のトラフィックフローに対するポリシー判定プロセスをシミュレートします。
</details>

---

[学習教材に戻る](../../../networking/cilium/05-l2-l7-networking.md) | [次のクイズ: セキュリティと可視性](./06-security-visibility-quiz.md)
