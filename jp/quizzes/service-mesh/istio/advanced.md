# Istio 高度なトピックのクイズ

> **検証基準**: Istio 1.31.0、Kubernetes 1.32–1.37、Argo Rollouts 1.10.1
> **最終レビュー日**: 2026年10月16日

各設問では、設定、実行時の動作、検証根拠を区別します。例はそれぞれ独立しています。該当するトポロジーを選び、リンク先ガイドに記載された前提条件を満たしてください。以下の過去の計算用数値は、現在の料金や新たなベンチマーク結果を示すものではありません。

## 選択問題 (1–5)

### 問題 1: Ambient モードと Sidecar モード

Ambient モードでワークロードごとのプロキシ負荷を削減できるアーキテクチャ上の変更はどれですか？

- A. Ambient は常に Sidecar より多くの機能を提供する。
- B. ノードごとの ztunnel が L4 トラフィックを処理し、必要な L7 処理用の waypoint は別途デプロイする。
- C. インストールが必ず10倍速くなる。
- D. 設定を変えなくてもすべてのポリシーが強化される。

<details>
<summary>回答を表示</summary>

**正解: B**

Ambient では、参加する各ワークロード Pod に Sidecar プロキシを1つずつ配置する必要がありません。ztunnel が L4 のセキュアなオーバーレイを提供し、宛先 waypoint への参加設定とサポートされる L7 ポリシーによって追加の処理経路が決まります。waypoint は、どちらの ztunnel からでも任意に選べる万能の共有ホップではありません。

| 項目 | 適切な比較 |
|---|---|
| CPU/メモリ | 同等のトラフィック、ポリシー、テレメトリ、ノード数、waypoint レプリカ数で測定します。一律に98%削減できるわけではありません。 |
| 参加 | 既存の Sidecar 非導入 Pod はアプリケーションを再起動せず Ambient に参加させられます。既存 Sidecar の削除にはワークロードの置き換えが必要です。 |
| 機能 | サポート範囲は異なります。Waypoint の EnvoyFilter はサポートされず、Ambient マルチクラスターにも独自の Beta トポロジー制限があります。 |
| 成熟度 | Ambient の中核機能は Istio 1.24 で GA になりましたが、それ以降のすべての機能が GA という意味ではありません。 |
| セキュリティ | mTLS とポリシーの適用は実際のトラフィック経路とサポート対象のポリシー適用先に依存します。L7 適用が必須なら waypoint を通ることを確認してください。 |

たとえば、Sidecar 1,000個がそれぞれ50 MB/0.1 vCPUを使うと**仮定**すると、合計は50,000 MB/100 vCPUです。ztunnel 10個がそれぞれ50 MB/0.1 vCPU、waypoint 1個が200 MB/0.5 vCPUという仮定では、合計700 MB/1.5 vCPUになります。計算上の削減率は98.6%/98.5%ですが、これらは任意の仮定値であり、ベンチマークでも容量保証でもありません。

サポート対象の Ambient コンポーネントをインストールし、既存のリビジョンラベルやインジェクションラベルを確認してから参加させます。

```bash
kubectl label namespace ambient-demo istio.io/dataplane-mode=ambient --overwrite
kubectl get daemonset ztunnel -n istio-system
istioctl ztunnel-config workloads --workload-namespace ambient-demo
```

namespace がすでに存在し、Ambient 用として意図され、互換性のあるワークロードを含んでいる必要があります。これらのコマンドだけでは CNI/ztunnel のインストール、waypoint の設定、インジェクション済み Pod の安全な移行は行われません。

[Ambient ガイド](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

### 問題 2: マルチクラスターのサービス検出

Istio の Sidecar マルチクラスター・メッシュで、アクセスを許可された Kubernetes サービスレジストリを読み取り、プロキシのサービス検出設定を生成するコンポーネントはどれですか？

- A. Istiod
- B. CoreDNS のみ
- C. east-west gateway のみ
- D. ServiceEntry オブジェクトのみ

<details>
<summary>回答を表示</summary>

**正解: A**

各 primary の Istiod は、アクセスを許可された Kubernetes API を読み取ります。primary-remote では、remote 側のワークロードは primary のコントロールプレーンを使います。remote 側のインストールは、「super-primary」が管理する2つ目の完全な Istiod ではありません。multi-primary では各 primary が独自のコントロールプレーンを持ち、許可された remote の検出を行います。

Istiod はプロキシ設定を生成・配布しますが、VirtualService/DestinationRule の Kubernetes オブジェクトやアプリケーションデータをすべてのクラスターに複製するわけではありません。設定は別途配布してください。共有信頼は明示的に構成する必要があり、meshID の値が同じでも共通 CA は作成されません。

CoreDNS はフォワーディングなどを構成できますが、Istio のクラスター間レジストリではありません。Gateway はネットワーク間のトラフィックを運びます。ServiceEntry は外部サービスなど、明示的に登録するサービスをレジストリに追加します。

存在しない `data.kubeconfig` フィールドを作るのではなく、実際の remote secret を生成します。

```bash
# After the remote installation; contexts must identify the intended clusters.
istioctl create-remote-secret --context="$CTX_CLUSTER2" --name=cluster2   | kubectl --context="$CTX_CLUSTER1" apply -f -
```

この secret により primary は**remote API**へアクセスできます。認証情報を保護し、生成された RBAC を確認してください。ネットワークを接続したり、ポリシーオブジェクトを複製したりするものではありません。

[マルチクラスターガイド](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### 問題 3: EnvoyFilter の用途

EnvoyFilter の主な用途は何ですか？

- A. Kubernetes Service を作成する。
- B. すべての VirtualService を自動生成する。
- C. 生成済み Envoy プロキシ設定の一部をカスタマイズする。
- D. Istiod のインストール設定をすべて置き換える。

<details>
<summary>回答を表示</summary>

**正解: C**

目的に応じて、サポート対象のルーティング、テレメトリ、セキュリティ、拡張 API を優先してください。それらの API では必要な動作を実現できず、生成される設定を理解している場合に EnvoyFilter を使います。たとえば、以下の Sidecar 専用 Lua フィルターは、例示用の送信リクエストヘッダーを変更します。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: quiz-header
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(handle)
                handle:headers():replace("x-quiz-example", "yes")
              end
```

namespace と selector は対象プロキシに一致させます。selector を指定しない場合、通常はリソースと同じ namespace のプロキシが対象です。root namespace のリソースはメッシュ全体に適用できる場合があります。1つの YAML オブジェクトに `workloadSelector` キーを2つ書かないでください。Lua が追加したヘッダーは認証済みの ID ではありません。

他の用途には、必要な依存関係がすべて揃っていなければなりません。Wasm モジュールには検証済みアーティファクト/ランタイムとマウント、またはサポートされる WasmPlugin 配布経路が必要です。グローバルな Rate Limit には到達可能なサービス、一致する descriptor、障害時のポリシーが必要です。フィルター名を挿入するだけでは、これらのシステムは提供されません。Ambient の waypoint では EnvoyFilter はサポートされません。

アップグレード時には、正確な Istio/Envoy バージョン、有効な適用範囲、フィルター順序、型付きペイロード、生成されたプロキシ設定を検証してください。Istiod のインストール値は引き続き Helm/istioctl で構成します。インクラスター operator は削除されましたが、IstioOperator YAML は現在も istioctl の入力です。

[EnvoyFilter ガイド](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>

### 問題 4: Sidecar インジェクション

新しく作成する Pod の自動 Sidecar インジェクションを無効にできる設定はどれですか？

- A. namespace に `istio-injection=disabled` ラベルを明示的に設定する。
- B. ワークロードの Pod template に `sidecar.istio.io/inject: "false"` ラベルを設定する。
- C. 設定を変更せずに Istiod を再起動する。
- D. A と B の両方。

<details>
<summary>回答を表示</summary>

**正解: D**

```bash
kubectl label namespace example istio-injection=disabled --overwrite
kubectl get namespace example -L istio-injection,istio.io/rev
```

以下の断片は既存 Deployment の spec の下に置きます。既存の image、selector、その他のフィールドは保持してください。

```yaml
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: 'false'
```

namespace または Pod の無効化ラベルが優先されます。特に、Pod 側で有効化しても `istio-injection=disabled` を上書き**できません**。`istio-injection=enabled` だけを削除しても、すべての環境で無効になるとは限りません。リビジョンラベル、Pod 側の有効化、インジェクターの既定値も確認してください。従来の inject annotation は label に置き換えられ、非推奨です。旧設定と新設定を競合させないでください。

変更が影響するのは新しい Pod であり、すでに注入されたプロキシではありません。既存 Pod を変更する際は、確認済みのワークロード更新手順を使ってください。namespace 全体でインジェクションを有効にしつつ、選択したワークロードの template では無効にできますが、その無効化によってワークロードのメッシュ/セキュリティへの参加も変わります。

```bash
kubectl get pod "$POD" -n "$NAMESPACE" -o json   | jq '{containers: [.spec.containers[].name],
         initContainers: [.spec.initContainers[]? | {name, restartPolicy}]}'
```

native sidecar は `restartPolicy: Always` を持つ initContainers に現れることがあります。通常の containers だけを調べたり、Ready が必ず `2/2` になると考えたりするのは不十分です。Ambient への参加は別の仕組みです。

[インジェクションガイド](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

### 問題 5: Argo Rollouts によるトラフィック分割

Argo Rollouts が更新する HTTP ルートの重みを保持する Istio の**宣言的リソース**はどれですか？

- A. Rollouts コントローラープロセス
- B. VirtualService
- C. Kubernetes Service のみ
- D. Gateway のみ

<details>
<summary>回答を表示</summary>

**正解: B**

Rollouts が名前付きルートの重みを更新し、Istiod が設定を変換し、ルーティングを**実行するのは Envoy** です。VirtualService はパケットを処理するプロセスではありません。10% は確率的なルーティング重みであり、100リクエストのうち正確に10件が canary に到達する保証ではありません。リトライや長時間接続は観測結果に影響します。

subset を使う別方式では、アプリケーションを選択する1つの Service、両方の subset、そしてリビジョンラベルを Rollouts が管理する設定が必要です。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  host: test
  subsets:
  - name: stable
    labels:
      app: test
  - name: canary
    labels:
      app: test
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  hosts:
  - test
  - test.rollouts-demo.svc.cluster.local
  http:
  - name: primary
    route:
    - destination:
        host: test
        port:
          number: 8080
        subset: stable
      weight: 100
    - destination:
        host: test
        port:
          number: 8080
        subset: canary
      weight: 0
    retries:
      attempts: 0
```

この strategy 断片は、ガイドにある対応する完全な Rollout に統合してください。不完全なリソースとして適用したり、別の host 単位分割方式と組み合わせたりしないでください。

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: test-subsets
            routes:
            - primary
          destinationRule:
            name: test-subsets
            canarySubsetName: canary
            stableSubsetName: stable
      steps:
      - setWeight: 10
      - pause: {}
```

名前が `test` の Service、完全な Rollout の selector/template、`rollouts-demo` namespace が存在する必要があります。Rollouts が subset のリビジョンラベルを更新します。`retries.attempts: 0` はこのルートでのメッシュリトライを無効にします。アプリケーション側のリトライは別です。

トラフィック分析は構成した場合にだけ実行されます。自動分析に失敗すると rollout を中断できますが、アプリケーションやデータベースへの副作用を元に戻すわけではありません。ガイドにある host 単位または subset 単位の完全な例を、一度に1つの方式で使ってください。

[Argo Rollouts ガイド](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

## 記述問題 (6–10)

### 問題 6: Ambient のリソースとコスト分析

元の仮定値（Pod 500個、r5.xlarge ノード5台、月730時間、1ノード時間あたり$0.252）を使い、プロキシリソースを計算して請求額の削減につながるか説明してください。Sidecar 1つあたり50 MB/0.1 vCPU、ztunnel 1つあたり50 MB/0.1 vCPU、waypoint は200 MB/0.5 vCPUとします。

<details>
<summary>解答例</summary>

料金とリソースの数値は**演習用の入力値**であり、現在の AWS 見積もりでも Istio の実測値でもありません。以下の MB/GB の計算は10進法です。

| リソース | Sidecar | 仮定した5ノードでの Ambient | 計算上の削減 |
|---|---|---|---|
| メモリ | 500 × 50 = 25,000 MB | 5 × 50 + 200 = 450 MB | 24,550 MB、98.2% |
| CPU | 500 × 0.1 = 50 vCPU | 5 × 0.1 + 0.5 = 1 vCPU | 49 vCPU、98% |

r5.xlarge は4 vCPU、32 GiB メモリです。5台ではシステムやアプリケーションの必要分を差し引く前でも20 vCPUしかありません。したがって、Sidecar が50 vCPUを使うという仮定は、この固定5ノードのシナリオではすでに成立しません。プロキシだけに必要な CPU の下限は ceil(50/4) = 13ノードです。これはアプリケーション CPU、システム予約、メモリ、IP上限、配置、可用性要件を含みません。

ztunnel のリソースを5ノード分で計上したまま、「13ノードという下限」と「Ambient は1ノード」とを比較しないでください。**実際に維持するノード数**を使って ztunnel の必要リソースを再計算し、waypoint の HA/トラフィック容量と他のすべてのワークロードも含めてください。

仮定した料金では、次のとおりです。

- 1ノード・月の料金は `0.252 × 730 = $183.96`。
- 変更しない5ノードの料金はどちらのモードでも `$919.80/月` です。プロキシ用の余力が測定できても、それだけで請求額は減りません。
- 13ノード・月なら `$2,391.48` です。これは以前の計算を修正した値であり、本番に必要な台数が証明されたという意味ではありません。
- 検証済みの fleet が Sidecar で Nₛ 台、Ambient で Nₐ 台なら、他の費用や契約を含める前のコンピューティング費用差は `(Nₛ − Nₐ) × $183.96/月` です。

全体を比較する際は、EKS/コントロールプレーン料金、ロードバランサー、AZ/リージョン間転送、ストレージ、テレメトリ、実際の購入契約を含めてください。Sidecar ではローカル通信も発生します。Ambient にすればネットワーク料金や OOM が自動的になくなるわけではありません。

演習で仮定する移行費用$6,000を回収する月数は、測定した月間純削減額 S が正の場合に限り `6000 / S` です。請求対象の容量が変わらなければ S はゼロの可能性があり、その場合、この計算で有限の回収期間は得られません。プロキシの計算だけから、以前の92%の請求削減や2.7か月の ROI を主張しないでください。

[Ambient ガイド](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

### 問題 7: EKS の Primary-Remote メッシュ

us-east-1 と us-west-2 にすでに存在する2つの EKS クラスター向けに、サービス検出、信頼、ネットワークの前提条件、クラスター間の検証例を含めて primary-remote 構成を説明してください。

<details>
<summary>解答例</summary>

これは**Sidecar**構成です。現在の Ambient マルチクラスター Beta がサポートするのは multi-primary/multi-network であり、この primary-remote モデルではありません。primary の Istiod が remote のプロキシを提供します。上位 primary から設定を受け取る完全な remote Istiod はありません。

インストール前に、確認済みの共通信頼、API アクセス、DNS、セキュリティグループ/ファイアウォール、必要な L4 コントロールプレーン/データプレーン経路を整えます。ネットワーク ID が別々であることは、接続性を作るものではありません。複数ネットワークでは、到達可能な remote endpoint を使うために両側に適切な east-west gateway が必要です。リージョン間のネットワーク費用と障害復旧は別途対応してください。

primary の基本設定は istioctl の入力です。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      externalIstiod: true
      multiCluster:
        clusterName: cluster1
      network: network1
```

remote 側では、**198.51.100.10 はドキュメント用のプレースホルダー**であり、EKS endpoint ではありません。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: remote
  values:
    istiodRemote:
      injectionPath: /inject/cluster/cluster2/net/network2
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network2
      remotePilotAddress: 198.51.100.10
```

remote namespace では、管理する primary も指定します。

```bash
kubectl --context="$CTX_CLUSTER2" annotate namespace istio-system   topology.istio.io/controlPlaneClusters=cluster1 --overwrite
```

保守されているガイドに従い、信頼の準備、同じ Istio リリースからの gateway 生成、primary のサービス検出/インジェクション公開、remote profile のインストールを行ってから、問題2で示した remote-access secret を作成してください。この2ネットワークの例では、remote のインジェクション経路は `net/network2` です。

EKS の NLB が提供するのは通常 DNS 名です。リリースによっては remotePilotAddress に DNS を指定できますが、chart の render だけではサービス検出/インジェクションの接続性や証明書名は証明されません。公式の外部コントロールプレーン向け DNS/証明書/インジェクション URL 設計を完成させてください。ロードバランサーの IP がないからといって、任意のアドレスで置き換えないでください。

検証には、同じ Istio 配布物のリリース版 `helloworld` と `curl` サンプルを使います。ドキュメントに従って、両クラスターに同じ namespace/Service identity とバージョン付きワークロードを作成します。ローカル endpoint がない Service でも、Istio が remote endpoint を検出している間、ローカル Kubernetes DNS の情報を提供できます。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: helloworld
  namespace: sample
spec:
  selector:
    app: helloworld
  ports:
  - name: http
    port: 5000
    targetPort: 5000
```

この Service だけではアプリケーションはデプロイされません。サンプルの実際の backend はポート5000で listen します。`containerPort 8080` を宣言しただけでは、標準の nginx プロセスがそのポートで listen するようにはなりません。サンプル全体をデプロイした後、既知の curl Pod/container を選び、データプレーン設定と応答を確認します。

```bash
kubectl --context="$CTX_CLUSTER1" get service,endpointslice -n sample
kubectl --context="$CTX_CLUSTER2" get service,endpointslice -n sample
istioctl --context="$CTX_CLUSTER1" proxy-status
istioctl --context="$CTX_CLUSTER1" proxy-config endpoints "$CURL_POD" -n sample   --cluster 'outbound|5000||helloworld.sample.svc.cluster.local'
kubectl --context="$CTX_CLUSTER1" exec -n sample "$CURL_POD" -c curl --   curl --fail --max-time 5 http://helloworld.sample.svc.cluster.local:5000/hello
```

複数ネットワークでは、クライアントに直接到達可能な remote Pod IP ではなく、east-west gateway の endpoint が見えることがあります。応答1件で証明できるのはその呼び出しだけです。両方向、endpoint のバージョン、信頼、ポリシー、障害シナリオを試してください。

**同じ host/subset/port**を持つ2つの重み付き宛先は、ローカル80%/remote20%を意味しません。対象 endpoint が存在する、サポートされた locality または明示的な宛先モデルを用意してください。クラスター間トラフィックを観測するときは、テレメトリ reporter を1つ選び、実際の source_cluster/destination_cluster ラベルを使用します。

[マルチクラスターガイド](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### 問題 8: ユーザー単位の共有 Rate Limit

`/api/premium/*` に対する共有の毎分100リクエスト制限を実装してください。identity、descriptor、障害時の契約を説明してください。

<details>
<summary>解答例</summary>

リクエスト経路は、**認証済みの入口 → 専用 Envoy gateway → 共有 Rate Limit サービス/Redis による判定 → backend または拒否**です。ローカルプロキシのバケットは、複数の gateway replica で共有される quota ではありません。

以下の条件付き例では、次を前提とします。

- `istio-system` に、実際のラベルが `app: premium-gateway` である専用 gateway があり、TLS/ルート設定と既存 backend Service が一致している。
- 信頼された認証レイヤーが、呼び出し側から渡された `x-user-id` を削除し、空でない正規のユーザー identity を設定する。その認証経路からのみ gateway/backend に到達できる。呼び出し側が自由に指定できるヘッダーはユーザー identity ではありません。
- 以下に示す既存の分離されたラボ用 Redis endpoint に到達できる。本番の Redis 認証/TLS、永続性、HA、フェイルオーバー、適切な接続設定は別途設計が必要です。replica 数だけではそれらは実現しません。

一致する descriptor は**2要素のシーケンス**です: `(header_match=premium, user_id=<trusted user>)`。サーバー設定では動的な user エントリーを premium エントリーの下にネストする必要があります。トップレベルに user_id だけを置いた descriptor では一致しません。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: |
    domain: premium-ratelimit
    descriptors:
    - key: header_match
      value: premium
      descriptors:
      - key: user_id
        rate_limit:
          unit: minute
          requests_per_unit: 100
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ratelimit
  template:
    metadata:
      labels:
        app: ratelimit
        sidecar.istio.io/inject: 'true'
    spec:
      containers:
      - name: ratelimit
        image: docker.io/envoyproxy/ratelimit:8fe6ea42@sha256:a61547259607d40aff153050c2a87873ca1676d1d9f5f06937d412000dcc2df1
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8081
          name: grpc
        env:
        - name: LOG_LEVEL
          value: info
        - name: CONFIG_TYPE
          value: FILE
        - name: RUNTIME_ROOT
          value: /data
        - name: RUNTIME_SUBDIRECTORY
          value: ratelimit
        - name: RUNTIME_APPDIRECTORY
          value: config
        - name: RUNTIME_WATCH_ROOT
          value: 'false'
        - name: RUNTIME_IGNOREDOTFILES
          value: 'true'
        - name: USE_STATSD
          value: 'false'
        - name: REDIS_SOCKET_TYPE
          value: tcp
        - name: REDIS_URL
          value: redis-ratelimit.istio-system.svc.cluster.local:6379
        - name: HOST
          value: '::'
        - name: GRPC_HOST
          value: '::'
        - name: HEALTHY_WITH_AT_LEAST_ONE_CONFIG_LOADED
          value: 'true'
        volumeMounts:
        - name: config-volume
          mountPath: /data/ratelimit/config
          readOnly: true
        command:
        - /bin/ratelimit
        resources:
          requests:
            memory: 128Mi
            cpu: 100m
          limits:
            memory: 512Mi
            cpu: 500m
        readinessProbe:
          httpGet:
            path: /healthcheck
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config-volume
        configMap:
          name: ratelimit-config
---
apiVersion: v1
kind: Service
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  ports:
  - port: 8080
    name: http
    targetPort: 8080
  - port: 8081
    name: grpc
    targetPort: 8081
  selector:
    app: ratelimit
```

この image は digest 付きの検証済み upstream commit 8fe6ea42 であり、更新される master tag ではありません。gRPC ポートは **8081**、HTTP health ポートは **8080** です。この workload には一致する injector と実際のメッシュ/ネットワークアクセスが必要です。保護された Redis 認証情報は適切な Secret/mount の仕組みで設定してください。新しい設定が読み込まれたことを確認してください。ここに示すファイルモード設定だけではホットリロードされた証拠になりません。

生成済みの Istio gRPC cluster を使い、確立済みのサービス検出/TLS ポリシーを適用します。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: premium-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: premium-ratelimit
          failure_mode_deny: true
          timeout: 0.1s
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: outbound|8081||ratelimit.istio-system.svc.cluster.local
                authority: ratelimit.istio-system.svc.cluster.local
            transport_api_version: V3
---
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: premium-ratelimit-actions
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: VIRTUAL_HOST
    match:
      context: GATEWAY
    patch:
      operation: MERGE
      value:
        rate_limits:
        - actions:
          - header_value_match:
              descriptor_value: premium
              headers:
              - name: :path
                string_match:
                  prefix: /api/premium/
          - request_headers:
              header_name: x-user-id
              descriptor_key: user_id
              skip_if_absent: false
```

action set は専用 gateway に意図的に限定しています。共有 gateway では実際に生成された vhost をさらに絞ってください。prefix 外のリクエストでは premium descriptor は生成されません。エンコードされたパスや別経路での backend アクセスも含め、ルート/パス正規化と認証ポリシーを一貫させます。

descriptor の生成を回避されないよう、premium 経路で identity が欠落または空の場合は拒否します。

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: premium-requires-identity
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: premium-gateway
  action: DENY
  rules:
  - to:
    - operation:
        paths:
        - /api/premium/*
    when:
    - key: request.headers[x-user-id]
      notValues:
      - '*'
```

この DENY ポリシーは、ヘッダー欠落を防ぐだけです。指定された値を認証するものではなく、必須の信頼できる入口/迂回防止策、既存 ALLOW ポリシー、TLS、アプリケーション認可の代わりにもなりません。

`failure_mode_deny: true` の場合、Rate Limit サービスのエラーは通常 HTTP 500、上限超過の判定は429になります。RPC の100 ms timeout は例であり、Redis とネットワークの遅延を考慮してテストしてください。ヘッダーや統計カウンターだけでは quota の適用を証明できません。

| 検証ケース | テストする契約 |
|---|---|
| 2つの gateway replica をまたいだ同じ認証済み identity | 共有される1つの descriptor/window quota |
| 2つ目の identity | 別々の user descriptor |
| identity の欠落または偽装 | guard/認証境界で拒否し、quota を迂回できる状態にしない |
| premium prefix 外のパス | premium descriptor は生成しない。他のセキュリティ/Rate Limit ポリシーは引き続き適用 |
| Redis/RLS が利用不可 | fail-closed の動作と実際の status/latency を確認 |
| window 境界または Redis 再起動 | カウンター/window の動作を測定する。別々のテスト実行をまたいで、必ず101件目を拒否すると約束しない |

許可された読み取り専用 endpoint に対して上限のあるリクエストを送り、新しいテスト identity/window を使います。50件送った後にさらに150件送っても、独立したクリーンな quota が2つ始まるわけではありません。Rate Limit ヘッダーを返すには、サポートされるサービス応答とフィルター設定が必要です。remaining/reset 値を捏造しないでください。

RLS の health、読み込まれた設定、実際の Envoy 統計（HTTP stat prefix 配下の `ratelimit.ok`、`ratelimit.over_limit`、`ratelimit.error`）を確認します。`rejected_total` などを作り上げず、出力された Prometheus 名/ラベルを検証してください。大規模な本番 keyspace で Redis `KEYS *` を実行したり、実装固有のカウンターを残 quota と解釈したりしないでください。固定した distroless RLS image は redis-cli のシェルではありません。

[Rate Limit ガイド](../../../service-mesh/istio/resilience/02-rate-limiting.md) · [EnvoyFilter ガイド](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>

### 問題 9: 分析を使った Blue/Green

preview と promotion 後の分析を含む Blue/Green Rollout を構成してください。メトリクス欠落を成功と見なさずに、トラフィック切り替えと失敗時の動作を説明してください。

<details>
<summary>解答例</summary>

これは問題5の canary 方式に対する**別の方式**です。Argo Rollouts 1.10 の controller/CRD、Istio を注入したデモ workload と呼び出し元、対応する source-reporter メトリクスを収集する Prometheus、検証済みデモ image を動かす Linux amd64 容量を前提とします。本番環境で検証済みのデプロイではなく、ラボの例です。

既存の `rollouts-demo` namespace に Service と完全な Rollout を作成します。Service の revision-hash selector は Rollouts が管理します。GitOps でこれらの動的フィールドを上書きしないでください。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: test-active
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-preview
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test
  namespace: rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
  strategy:
    blueGreen:
      activeService: test-active
      previewService: test-preview
      autoPromotionEnabled: true
      prePromotionAnalysis:
        templates:
        - templateName: preview-analysis
        args:
        - name: service-name
          value: test-preview
        - name: namespace
          value: rollouts-demo
      postPromotionAnalysis:
        templates:
        - templateName: active-analysis
        args:
        - name: service-name
          value: test-active
        - name: namespace
          value: rollouts-demo
      scaleDownDelaySeconds: 600
```

初期 image は検証済みの blue デモ digest で、更新時に使う対応する green digest はガイドに記載されています。新しいリビジョンでは preview が候補を指します。pre-analysis に成功した後、`autoPromotionEnabled: true` なら自動 promotion が可能になります。手動での明示的な promotion が必要な場合は false にしてください。これは別のポリシー選択です。

ここでのトラフィックは、メッシュ内クライアントから内部 Service に送られます。本番の入口公開には、実際の Gateway、TLS、一致する host 設定、認可が必要です。2つ目の VirtualService hostname を作るだけでは Gateway に追加されず、preview へのアクセスも保護されません。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-bluegreen
  namespace: rollouts-demo
spec:
  hosts:
  - test-active
  - test-active.rollouts-demo.svc.cluster.local
  http:
  - name: active
    route:
    - destination:
        host: test-active
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-preview-route
  namespace: rollouts-demo
spec:
  hosts:
  - test-preview
  - test-preview.rollouts-demo.svc.cluster.local
  http:
  - name: preview
    route:
    - destination:
        host: test-preview
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
```

両方のルートでメッシュのリトライを明示的に無効にしています。promotion 時に preview Service が自動的に旧 stable version へ切り替わるわけではありません。active Service の selector は新しいリビジョンに変わり、旧 ReplicaSet は最終的に**スケールダウン**されますが、必ず削除されるとは限りません。既存接続やアプリケーション/データベースの副作用は selector の変更で元に戻りません。

preview の分析前/実行中に、preview Service 経由で代表的かつ認可済みのトラフィックを生成してください。Prometheus のクエリだけではトラフィックは生成されません。この例では、2分間の window あたり推定20リクエスト、2xx の成功率95%以上、p95 が0.5秒以下、5xx/zero-status エラーが1%以下である必要があります。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: preview-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: active-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
```

2つの template は、引数の Service 名を変えて、意図的に同じ gate 定義を使います。`initialDelay: 5m` により2分間の window が遷移期間を過ぎるまで待ちますが、データの新しさと実際のトラフィックを別途確認してください。旧 active version の古いサンプルを候補の根拠として読まないでください。

Prometheus は vector を返すため、条件では長さと有限値を確認してから `result[0]` を参照します。分子の `or vector(0)` は2xxがない/すべて5xxの場合と、5xxがない/正常な場合を扱います。分母とトラフィック量の確認により、テレメトリが欠落またはアイドルの状態で合格するのを防ぎます。成功メトリクスに含まれるのは2xxのみです。4xxは5xx/zero-status エラーの分子には入りませんが、成功率は下がります。

`failureLimit: 0` は最初に失敗した measurement で中断します。2にした場合、3回目の失敗で上限を超えます。失敗を許容する5 sample の場合、5回すべての成功が必要なわけではありません。30秒間隔の5 sample でも、初期 delay や provider error があるため、フェーズが正確に2.5分で終わる保証はありません。

promotion 前に失敗すると、旧 active target が維持されます。promotion 後に失敗すると、controller の規則に従い、旧 ReplicaSet が利用可能な場合は中断して active の選択を元に戻します。これは即時かつ常に保証される rollback ではありません。旧 version の容量を十分に保ち、伝播、session、接続 drain、データベース互換性を検証してください。

```bash
kubectl argo rollouts get rollout test -n rollouts-demo --watch
kubectl get analysisrun -n rollouts-demo
kubectl get service test-active test-preview -n rollouts-demo -o yaml
```

コピーした status 出力や存在しないメトリクス名に頼らず、実際の AnalysisRun condition と revision tree を調べてください。Rollout の scale-down、endpoint の伝播、アプリケーションの復旧を対象環境でテストする必要があります。

[Argo Rollouts ガイド](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

### 問題 10: DNS の動作と測定

Istio の DNS capture と Envoy の upstream DNS 解決の違いを説明し、有効な設定と再現可能な性能比較の方法を示してください。元の未検証ベンチマーク値も、新しい測定結果として示さずに評価してください。

<details>
<summary>解答例</summary>

アプリケーションの DNS、Istio の DNS capture、CoreDNS/cache の動作、Envoy の upstream 解決はそれぞれ別のものです。HTTP リクエストを新しく送っても、DNS クエリや接続が必ず新たに発生するわけではありません。DNS capture は、任意の upstream 応答に対する万能な cache ではありません。

Sidecar モードでは istio-agent が capture された DNS リクエストを処理します。Ambient は別途文書化された DNS 経路を使い、Istio 1.25 以降は既定で capture が有効です。既知のメッシュ名は name table から応答し、未知の名前は転送します。Envoy は DNS を使う upstream endpoint を独立して解決します。

アプリケーションから発生する HTTPS の外部サービスを、有効な ServiceEntry で登録します。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.github.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

これは2つ目の TLS 層を開始するものでも、egress firewall を作るものでも、暗号化された HTTP リクエストの path を Sidecar から見えるようにするものでもありません。適切なネットワークポリシーとアプリケーションの TLS 検証は引き続き必要です。

Sidecar capture では、この istioctl 入力を既存のインストール値に統合し、通常の変更手順に従って対象 workload を再起動します。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: 'true'
```

DestinationRule の `trafficPolicy.dnsRefreshRate` というフィールドは存在せず、`consecutiveErrors` も現在の outlier detection のフィールドではありません。Istio 1.31 の生成 DNS cluster は DNS TTL を尊重します。関連する fallback 動作に対する mesh の `dnsRefreshRate` の既定値は60秒です。5分に設定しても、正の TTL を上書きする一律の更新間隔にはなりません。

架空の `envoy.filters.network.dns_cache` filter/type を挿入しないでください。Dynamic Forward Proxy と現行の DYNAMIC_DNS ServiceEntry mode は、それぞれ独自の要件を持つ別のサポート対象設計であり、汎用 cache 切り替えではありません。必要なら、DNS ガイドに従い、適用範囲を限定してバージョン検証済みの cluster カスタマイズを行ってください。

範囲を限定したテストには、curl が含まれることを確認した caller container と、DNS/TTL を制御できる**所有または使用許可済み**の HTTPS テスト endpoint を使います。BENCH_URL を明示的に設定してください。これはプロセス単位の所要時間を測るもので、Envoy だけの DNS latency ではありません。

```bash
: "${BENCH_URL:?Set an authorized HTTPS benchmark endpoint}"
for i in $(seq 1 20); do
  curl --silent --show-error --fail --max-time 5 --output /dev/null     --write-out '%{http_code},%{time_namelookup},%{time_connect},%{time_appconnect},%{time_starttransfer},%{time_total}
'     "$BENCH_URL" || break
  sleep 0.2
done
```

クライアント/image、Istio/Kubernetes のバージョン、proxy mode、TTL/応答の変更、DNS 経路、接続再利用、並行数、payload、TLS、ウォーム/コールドの手順を記録してください。curl を起動するたびにプロセス内の状態はリセットされます。接続再利用は別に制御してください。公開 GitHub API に負荷をかけたり、curl の image に ApacheBench も含まれると想定したりしないでください。統計を計算する前に失敗した sample を明示的に処理します。

元の韓国語の文章には EKS 1.34、Istio 1.28.0、r5.xlarge/us-east-1、api.github.com が記載されていましたが、生データも再現可能な benchmark artifact もありません。この**過去の背景**はそのまま示し、Istio 1.31 の結果として付け替えないでください。

| 元の未検証値 | 前 | 後 | 算術上の差 |
|---|---:|---:|---:|
| 平均応答時間 |287 ms|152 ms|47.04%低下|
| p95 |350 ms|180 ms|48.57%低下|
| p99 |420 ms|210 ms|50%低下|
| Throughput |12.34 RPS|23.15 RPS|87.60%増加|
| 主張された cache hit 率 |0%|99%|有効な hit/miss の根拠なし|
| 主張された接続再利用率 |0%|95%|有効な再利用測定なし|

総応答時間の差をすべて DNS によるものとはみなせません。並行数10の場合、ApacheBench の request あたり平均時間はおよそ `1000 × 10 / RPS` ms、「全同時リクエストの平均」欄は `1000 / RPS` ms です。元のラベルは逆でした。この修正をしても benchmark の正しさが証明されるわけではありません。

capture の有用なメトリクスには、実際に export されている場合の `istio_agent_dns_requests_total`、`istio_agent_dns_upstream_requests_total`、`istio_agent_dns_upstream_failures_total`、upstream 所要時間の histogram があります。upstream の成功/(成功+失敗)はクエリの成功率であり、cache hit 率ではありません。`envoy_cluster_upstream_cx_active` は gauge です。これに rate() を適用しても接続再利用は測定できません。

生成された cluster の DNS 設定、export を確認した counter、実際の resolver/接続 trace を調べてください。平均 latency だけでなく DNS 変更と障害復旧もテストします。workload の根拠なしに5～15分の更新間隔や一定の性能向上を推奨しないでください。

[DNS ガイド](../../../service-mesh/istio/advanced/04-dns-cache.md)

</details>

## 採点

- 問題1～5: 各10点、合計50点。正解は **B、A、C、D、B**。
- 問題6～10: 各10点、合計50点。仕組み、前提条件、妥当な設定、有意義な検証、測定上の制約を正しく説明できた場合に評価します。
- 合計: 100点。クイズの点数は、ここで扱う設問への理解度を示すものであり、運用の専門性を認定するものではありません。

## 学習資料

- [Ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [マルチクラスター](../../../service-mesh/istio/advanced/02-multi-cluster.md)
- [EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)
- [DNS](../../../service-mesh/istio/advanced/04-dns-cache.md)
- [gRPC](../../../service-mesh/istio/advanced/05-grpc.md)
- [WebSocket](../../../service-mesh/istio/advanced/06-websocket.md)
- [インジェクション](../../../service-mesh/istio/advanced/07-sidecar-injection.md)
- [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)
- [KEDA](../../../service-mesh/istio/advanced/10-keda-autoscaling.md)
