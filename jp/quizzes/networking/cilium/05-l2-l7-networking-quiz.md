# Cilium L2–L7 ネットワークとロードバランシングのクイズ

> **Cilium 1.20.3 · CLI 0.20.1 · 2026-10-16**

## 選択式問題

1. **HTTP、DNS、gRPC などのアプリケーション動作が概念上属する OSI 層はどれですか？**
   - A) L1
   - B) L2
   - C) L3
   - D) L7

   <details>
   <summary>回答を表示</summary>

   **回答: D) L7**

   アプリケーションプロトコルは概念上 L7 に対応します。ただし、Cilium にすべてのアプリケーションプロトコルを扱うネイティブポリシーパーサーがあるという意味ではありません。Kafka の L7 ルールは削除されています。

   </details>

2. **DSR の direct-return 特性は何ですか？**
   - A) すべての応答を暗号化する
   - B) リモートのバックエンドが、受信側のロードバランサーノードを経由せずに応答できる
   - C) クライアント IP を認証する
   - D) 上流のプロキシによって書き換えられたクライアント IP を復元する

   <details>
   <summary>回答を表示</summary>

   **回答: B) リモートのバックエンドが、受信側のロードバランサーノードを経由せずに応答できる**

   ネットワークが非対称な戻り経路をサポートしている必要があります。DSR は応答経路のホップを減らせますが、性能とクライアント IP の保持は実際のトポロジーに依存します。

   </details>

3. **Cilium の HTTP/gRPC ポリシーのうち、サポートされるものを処理するコンポーネントはどれですか？**
   - A) kube-proxy
   - B) Hubble Relay
   - C) Envoy
   - D) CoreDNS

   <details>
   <summary>回答を表示</summary>

   **回答: C) Envoy**

   Envoy のデプロイ方法はインストール時の値に依存します。DNS ポリシーは Cilium の DNS プロキシを使います。サポートされない Kafka ルールを宣言しても、Kafka パーサーがインストールされるわけではありません。

   </details>

4. **Cilium の BPF Service がバックエンドを選ぶ、ドキュメント記載のアルゴリズムの組み合わせはどれですか？**
   - A) Round Robin と Least Connection
   - B) Random と Maglev
   - C) Source-IP Hash と Weighted Response Time
   - D) Envoy のすべてのアルゴリズム

   <details>
   <summary>回答を表示</summary>

   **回答: B) Random と Maglev**

   BPF による選択と Envoy の L7 ロードバランシングは別のコンポーネントです。Maglev は指定された外部経路でサポートされますが、通常の東西方向の socket-LB トラフィックには適用されません。

   </details>

5. **マスカレーディングの実装について正しい説明はどれですか？**
   - A) BPF はすべてのワークロードで常に高速である
   - B) 現行の Cilium はすべての Linux カーネルで動作する
   - C) どちらの実装もカーネル内で動作し、設定やプラットフォームの要件がある
   - D) BPF を選択すればルーティング要件がなくなる

   <details>
   <summary>回答を表示</summary>

   **回答: C) どちらの実装もカーネル内で動作し、設定やプラットフォームの要件がある**

   製品名やカーネル内での実行だけでは、性能結果は決まりません。このリリースの BPF マスカレーディングには機能やデバイスの依存条件があり、IPv6 サポートはベータです。

   </details>

6. **kube-proxy 置き換えを有効にする現行の値はどれですか？**
   - A) kubeProxyReplacement: partial
   - B) kubeProxyReplacement: true
   - C) kubeProxyReplacement: strict
   - D) kubeProxyReplacement: hybrid

   <details>
   <summary>回答を表示</summary>

   **回答: B) kubeProxyReplacement: true**

   boolean の現行値 `true` を使い、API サーバーへの到達性を含む完全置き換えの前提条件を満たしてください。以前の `strict`／`partial` という用語は現行の契約ではありません。

   </details>

7. **Cilium の組み込み HTTP ポリシー述語ではないものはどれですか？**
   - A) Method
   - B) Path
   - C) サポート対象のヘッダー条件
   - D) 任意のリクエスト本文の内容

   <details>
   <summary>回答を表示</summary>

   **回答: D) 任意のリクエスト本文の内容**

   Method／path の式とサポートされるヘッダー条件は、それぞれ扱いが異なります。値を指定した `headers` 文字列はリテラルであり、一般的なヘッダー値の正規表現ではありません。ペイロード検査には、別途アプリケーションまたはプロキシ機能を設計する必要があります。

   </details>

8. **このガイドで想定する Cilium／Istio の統合モデルはどれですか？**
   - A) Istio のサイドカーを自動的に迂回する
   - B) Istio のインターセプトを維持し、Cilium のネットワーク制御と Istio の L7／mTLS の役割を組み合わせる
   - C) mTLS を自動的に無効化する
   - D) すべての Cilium HTTP ルールで暗号化された Istio トラフィックを検査する

   <details>
   <summary>回答を表示</summary>

   **回答: B) Istio のインターセプトを維持し、Cilium のネットワーク制御と Istio の L7／mTLS の役割を組み合わせる**

   CNI と socket-LB の相互運用性を設定し、トポロジーをテストしてください。例では Istio mTLS を維持し、暗号化トラフィックに平文 HTTP 検査を適用せず、Cilium の L3／L4 ポリシーを使います。

   </details>

9. **socket-level load balancing で可能なことは何ですか？**
   - A) サポートされる socket hook で、パケット生成前にバックエンドを選択する
   - B) HTTP ヘッダーを自動的に認証する
   - C) すべてのトラフィックを復号する
   - D) 外部ロードバランサーを作成する

   <details>
   <summary>回答を表示</summary>

   **回答: A) サポートされる socket hook で、パケット生成前にバックエンドを選択する**

   TCP connect とサポート対象の UDP socket 経路では、早い段階で Service をバックエンドに変換できます。これはあらゆる環境でのレイテンシー保証ではなく、サイドカーのインターセプトと併用する場合に特別な設定が必要なことがあります。

   </details>

10. **フラグメンテーションに関する適切な原則はどれですか？**
    - A) 追跡すれば、あらゆるフラグメント攻撃を防げる
    - B) 実効経路 MTU を計画し、必要なエラー通知を確認する
    - C) すべてのフラグメントを常に破棄する
    - D) Cilium の MTU は常に最終的な Pod ペイロードサイズを意味する

    <details>
    <summary>回答を表示</summary>

    **回答: B) 実効経路 MTU を計画し、必要なエラー通知を確認する**

    Cilium の MTU は基盤ネットワークの値を上書きします。フラグメント追跡が保持するのは L4 のコンテキストであり、ペイロードの再構成や攻撃防止の保証ではありません。必要な通知や経路の動作に問題があると、PMTUD が失敗する場合があります。

    </details>

## 短答式問題

11. **現行の組み込み L7 ポリシーグループを挙げ、gRPC がどのように扱われるか説明してください。**

<details>
<summary>回答を表示</summary>

HTTP と DNS です。サポートされる gRPC 条件は、Envoy を通じた HTTP/2 の path／header マッチングを使います。DNS には Cilium の DNS プロキシを使い、Kafka の L7 ルールは削除されています。TLS の可視性は、前提にせず設定する必要があります。

</details>

12. **Service バックエンドの readiness と、汎用的なアクティブヘルスチェック機能の違いを説明してください。**

<details>
<summary>回答を表示</summary>

Kubernetes の endpoint／readiness 状態は、Service と終了処理の意味、および状態伝播の遅延を踏まえて、バックエンドが選択可能かどうかに影響します。これは、すべての BPF Service が独立した TCP／HTTP ヘルスプローブを実行するという意味ではありません。Cilium の接続性ヘルスチェック、アプリケーションプローブ、プロキシのヘルスチェックは別々の仕組みです。

</details>

13. **外部経路に出る Pod の送信元アドレスを変換する操作は何ですか？**

<details>
<summary>回答を表示</summary>

Source NAT（送信元 NAT）／マスカレーディングです。これは Service バックエンドへの宛先変換とは別です。選択されたインターフェイス、除外 CIDR、ノードごとの例外、その後段のクラウド NAT によって、観測される送信元が変わる場合があります。外部 HTTP 通信が成功しただけでは、どの実装が使われたかは証明できません。

</details>

14. **Maglev と `sessionAffinity: ClientIP` が互換ではない理由を説明してください。**

<details>
<summary>回答を表示</summary>

Maglev は、対応する経路で互換性のあるテーブル、状態、seed を使い、一貫してバックエンドを選択します。ClientIP affinity はクライアントごとに別の Service アフィニティとタイムアウト動作を保持し、IP または該当する socket-LB の namespace cookie を使います。どちらも、失敗または削除されたバックエンドへのセッション維持を保証しません。

</details>

15. **L4 とは何ですか？TCP と UDP の信頼性に関する違いも説明してください。**

<details>
<summary>回答を表示</summary>

L4 はトランスポート層です。TCP は信頼性のある順序付きバイトストリームを提供します。UDP は配信や順序を保証しないデータグラムを提供します。UDP があらゆるアプリケーションで自動的に高速になるわけではなく、ポート／プロトコルのポリシーもアプリケーション認証を提供しません。

</details>

## ハンズオン問題

16. **l7-exercise の TCP 8080 で待ち受ける API に対し、frontend からの GET /api/v1/users と POST /api/v1/data のみを許可し、POST では X-Auth-Token がある場合に限るポリシーを記述してください。**

<details>
<summary>回答を表示</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-http
  namespace: l7-exercise
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: l7-exercise
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/v1/users$
        - method: ^POST$
          path: ^/api/v1/data$
          headerMatches:
          - name: x-auth-token
```

ワークロードのラベルと namespace、および listener が前提条件です。名前だけを指定した `headerMatches` はヘッダーの存在を確認しますが、token の値は検証しません。以前の `X-Auth-Token: .*` という文字列は、任意の値に一致するのではなく、値を指定したリテラルマッチとして扱われます。他に適用されるポリシーと、実際に反映された proxy 状態も確認してください。

</details>

17. **新規に準備した kube-proxy なしの IPv4 テストクラスターへ、ドキュメント記載の DSR／Maglev プロファイルをインストールしてください。**

<details>
<summary>回答を表示</summary>

**lb-values.yaml**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```

```bash
: "${API_SERVER_HOST:?Set the real reachable API server host}"
: "${API_SERVER_PORT:?Set its actual port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.3 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

このプロファイルは Geneve オーバーレイと Geneve DSR dispatch を使います。API endpoint、ネットワークの戻り経路、共有して永続化した Maglev seed をあらかじめ準備してください。65521 は使用可能なテーブルサイズの一つであり、すべての環境に必要な値ではありません。任意のインストール後に kube-proxy を削除したり、稼働中クラスターの転送モードをテスト目的で切り替えたりしないでください。

</details>

18. **要件が order-service による orders の produce と、payment-processor による payments の consume である場合、現行の Cilium ポリシーで何を強制でき、broker 側では何を設定する必要がありますか？**

<details>
<summary>回答を表示</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: broker-connectivity
  namespace: messaging
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: order-service
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: payment-processor
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

これは 2 つの送信元ワークロードから、想定した TCP 9092 の broker listener への通信だけを許可します。実際の listener に合わせてポートを置き換えてください。topic 操作は強制しません。異なる broker principal を認証し、Kafka 側で必要な produce／consume と consumer-group の認可を設定してください。`rules.kafka` は削除されているため、古い YAML を完全な認可設定として提示するのは誤りです。

</details>

19. **実際にルーティングできる 10.0.0.0/8 宛てをマスカレーディング対象から除外し、BPF マスカレーディングを設定してください。**

<details>
<summary>回答を表示</summary>

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```

適切に準備した設定にこの内容を統合してください。BPF NodePort／デバイスの前提条件と戻り経路は引き続き必要です。`ipv4NativeRoutingCIDR` は該当するマスカレーディング除外を制御しますが、経路を作成したり `routingMode` を切り替えたりはしません。選択したノードで `cilium-dbg status --verbose` と `cilium-dbg bpf nat list` を確認し、制御された外部観測も行ってください。

</details>

20. **L7 ポリシーが想定どおり動かない場合に、影響の大きい操作を避けながら調査する手順を示してください。**

<details>
<summary>回答を表示</summary>

```bash
cilium status --verbose
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system get pods -l k8s-app=cilium-envoy -o wide
kubectl -n cilium-l2l7-demo get pods -o wide
export APP_POD=REPLACE-WITH-APP1-POD
export CILIUM_POD=REPLACE-WITH-AGENT-ON-APP-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "pod-name:cilium-l2l7-demo:$APP_POD"
kubectl -n cilium-l2l7-demo get cnp -o yaml
kubectl get ccnp -o yaml
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
```

Envoy DaemonSet を明示的に有効化した場合は、次を実行します。

```bash
export ENVOY_POD=REPLACE-WITH-ENVOY-POD-ON-APP-NODE
kubectl -n kube-system logs "$ENVOY_POD" --all-containers=true --tail=100
```

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

無作為な DaemonSet Pod ではなく、ワークロードが動作するノード上の agent／Envoy Pod を選んでください。Envoy DaemonSet を明示的に使う場合はその Pod の範囲を限定したログを確認し、Envoy が agent に組み込まれている場合は agent 側の設定済みログを確認します。Relay の port-forward は別のターミナルで維持してください。期待するルールと実際のルール、平文／TLS の可視性、アプリケーション応答、フローを比較します。HTTP 403 はパケットの drop と同じではなく、観測結果がない場合はフィルターや損失が原因のこともあります。最初の手順として、削除済みの policy trace や endpoint の強制再生成を行う必要はありません。

</details>

---

[学習教材に戻る](../../../networking/cilium/05-l2-l7-networking.md) | [次のクイズ: セキュリティと可視性](./06-security-visibility-quiz.md)
