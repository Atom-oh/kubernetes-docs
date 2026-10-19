# L2–L7 ネットワーキングとロードバランシング

> **レビュー基準**: Cilium 1.20.3、CLI 0.20.1。Istio の例では 1.31 API を使用します。
> **最終レビュー日**: 2026 年 10 月 16 日

## ラボ環境の準備

[インストール](README.md)および[ネットワーキング](03-networking.md)ガイドに従って準備した使い捨てクラスターを使用します。プラットフォームとカーネルの対応状況、および kubectl のバージョンスキューを確認してください。HTTP ラボにはスケジュール可能な Linux ノードが 2 台必要です。DSR/Maglev の実験には、kube-proxy を使用しないよう事前に準備したクラスター、実際に到達できる API サーバーのエンドポイント、およびサポートされるネットワーク経路も必要です。

実験に使うインストール値は最初に一式として選んでください。`cilium install --config ...` を繰り返しても稼働中の機能を移行する手順にはなりません。また、任意のインストール後に kube-proxy を削除する方法も安全な近道ではありません。

## OSI レイヤーを理解する

OSI は概念モデルであり、Cilium の 7 つのプロセスでも、ポリシーフックが固定順序で実行されることを示すものでもありません。

| レイヤー | 役割・例 | Cilium との関係 |
|---|---|---|
| L1 物理 | ビット、媒体、トランシーバー、中継器 | 基盤となるハードウェアとネットワーク要件 |
| L2 データリンク | Ethernet フレーム、MAC アドレス、ブリッジ／スイッチ | パケット処理と、明示的に構成した L2 Service アナウンス |
| L3 ネットワーク | IP パケット、ルーティング、ICMP | ルーティング、ID/CIDR ポリシー、サポート対象のフラグメント処理 |
| L4 トランスポート | TCP セグメントと信頼性のあるストリーム、配送・順序を保証しない UDP データグラム | ポート／プロトコルポリシー、接続状態、Service 変換 |
| L5 セッション | セッション／対話の管理 | 多くの場合、アプリケーションやプロトコル内部で実装される概念的な機能 |
| L6 プレゼンテーション | 表現、エンコーディング、暗号変換 | TLS を概念上ここに置く場合はありますが、Linux に独立した層が必ず存在するわけではありません |
| L7 アプリケーション | HTTP、DNS、gRPC などのアプリケーションプロトコル | 対応するプロキシポリシー。プロトコルが存在するからといって、Cilium にそのポリシーパーサーがあるとは限りません |

### レイヤーごとの実際の機能

- **L2:** L2 Announcements は、対象となる Service IP に対して ARP/NDP 応答を行うベータ機能です。kube-proxy 置き換えと、適切なデバイス／ローカルネットワークへの到達性が必要です。選出されたノードがその Service のトラフィックを受信します。任意の MAC/VLAN ACL、汎用 L2 ブリッジ、またはすべてのパケットを捕捉する機能ではありません。`externalTrafficPolicy: Local` との既知の非互換性があります。1.20.2 のリリースノートにはこの組み合わせでのトラフィック欠落に対する修正が含まれるため、使用するバージョンでの挙動を確認してください。
- **L3:** IP／ID ポリシーとルーティングの要件は動作モードによって異なります。マルチキャストは別途有効化する VXLAN 必須のベータ機能です。文書化されているカーネルの最低バージョンは AMD64 で 5.10、AArch64 で 6.0 です。どのルーティングモードでも使えると想定しないでください。
- **L4:** TCP/UDP ポートポリシー、接続追跡、ソケット／パケット単位の Service ロードバランシング、対応するアフィニティは、それぞれ異なるフックで機能します。パケットが作られる前にソケット単位で判断される場合もあります。
- **L7:** 現在組み込みでサポートされるポリシーグループは HTTP と DNS です。gRPC はサポート対象の HTTP/2 経路を使用します。Kafka の L7 ルールは削除されています。TLS/SNI 機能には文書化されたプロキシ構成が必要であり、暗号化されたアプリケーション内容を自動的に検査できるわけではありません。

HTTP/gRPC ポリシーは Envoy を使用し、DNS ポリシーは Cilium の DNS プロキシを使用します。Envoy はエージェント管理プロセスの場合と、専用の `cilium-envoy` DaemonSet の場合があり、値やアップグレード互換性によって異なります。L7 を有効にした新規 1.20 チャートでは DaemonSet が既定で優先され、このプロファイルでも明示しています。ポリシーを追加しても、インストール時のすべての設定が置き換わるわけではありません。

## HTTP ポリシーのラボ

新しい Namespace と、それに合致するワークロードを作成します。イメージ／ダイジェストと既知のサーバー Readiness パスは、公式 CLI テストのデプロイ定義に基づいています。

```bash
set -euo pipefail
kubectl create namespace cilium-l2l7-demo
kubectl label namespace cilium-l2l7-demo docs-audit-lab=cilium-l2l7-05
```

Namespace がすでに存在する場合は中止してください。別の実行で作成したリソースを再利用せず、一貫した新しい名前を選びます。

**`l7-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-l2l7-demo
  labels:
    app: client
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-l2l7-demo
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app1
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app1
  template:
    metadata:
      labels:
        app: app1
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: client
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: app1-service
  namespace: cilium-l2l7-demo
spec:
  selector:
    app: app1
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f l7-app.yaml
kubectl -n cilium-l2l7-demo wait --for=condition=Ready pod/client pod/outsider --timeout=120s
kubectl -n cilium-l2l7-demo rollout status deployment/app1 --timeout=120s
kubectl -n cilium-l2l7-demo get pods,services -o wide
kubectl -n cilium-l2l7-demo exec client -- \
  curl --fail --silent --show-error --max-time 5 http://app1-service/
```

許可対象外のクライアントからの初期接続性も確認してください。Service の公開ポートは 80 ですが、バックエンドが待ち受けるポートは **8080** です。Pod の Ingress ポリシーではバックエンドのポートを使います。ここでは、存在しない、または設定が一致しない古いアプリケーション構成と、ラベルや既定エントリポイントが例に合わないクライアント Pod を置き換えています。

**`app1-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: app1-http
  namespace: cilium-l2l7-demo
spec:
  endpointSelector:
    matchLabels:
      app: app1
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-l2l7-demo
        k8s:app: client
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/api/v1$
          headerMatches:
          - name: x-demo-tenant
            value: team-a
```


```bash
kubectl apply -f app1-http.yaml
kubectl -n cilium-l2l7-demo get cnp app1-http -o yaml
```

ポリシーが反映されたら、指定したクライアントから GET `/` を実行できます。このルールで POST `/api/v1` が許可されるのは、`x-demo-tenant: team-a` という値と完全一致するヘッダーがある場合だけです。バックエンドがその API 操作を実装している必要は別途あります。他に該当する許可ポリシーがない範囲でのみ、それ以外のメソッド、パス、接続元が拒否されます。アプリケーションの応答に加えて、反映されたポリシーとフローの証跡を確認してください。

このヘッダーは**デモ用のフィルターであり、認証ではありません**。以前の 32 文字の「トークン」条件は、ID、署名、発行者、有効期限、認可を検証していません。リリース版のトランスレーターでは、値を含む `headers` 文字列はその値とのリテラル一致です。`X-Auth-Token: ^[a-zA-Z0-9]{32}$` は正規表現によるトークン検証にはなりません。意図する完全一致または存在条件には明示的な `headerMatches` を使い、ユーザー認証はアプリケーションまたは適切な認証レイヤーで行ってください。

メソッドとパスは正規表現に対応しています。Cilium 組み込みの HTTP ポリシーには、任意のリクエスト本文を条件にする機能はありません。ヘッダーの存在確認、完全一致、URL フィルタリング、アプリケーション認可は、それぞれ別の制御です。

## Service Mesh との統合

Cilium はネットワーキングと対応するネットワークポリシーを提供し、Istio は構成済みのプロキシとメッシュの動作を管理します。統合したからといって、Istio サイドカーが自動的に迂回される、mTLS のオーバーヘッドがなくなる、すべてのトレースが統合される、またはリクエストが高速化するとは限りません。

```text
Configuration: istiod --> Istio Envoy proxies
Request: app --> source sidecar --> Cilium/network --> destination sidecar --> app
```

### Istio のトラフィック横取りを維持する

現在の Cilium 統合ガイドでは、kube-proxy との共存と、慎重な構成が必要な完全置き換えの選択肢が説明されています。共存させる場合の設定断片は次のとおりです。

**`istio-cilium-values.yaml`**

```yaml
kubeProxyReplacement: false
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```


完全置き換えを意図して準備した構成では、`kubeProxyReplacement: true` に加えて、到達可能な API エンドポイントと置き換えの前提条件が必要です。Pod のソケット変換が Istio のトラフィック横取りを迂回しないよう `socketLB.hostNamespaceOnly: true` を維持します。ノードの CNI 構成を共有する場合は `cni.exclusive: false` にします。

Istio のサイドカーリダイレクトには init コンテナまたは Istio CNI ノードエージェントを使えます。ambient モードでは対応するノード／CNI 経路を使います。[現行の Istio インストールガイド](../../service-mesh/istio/01-installation.md)に従い、いずれか一つのモードを選んでください。Kubernetes API サーバーから Istio の Admission Webhook に到達できる必要があります。マネージドコントロールプレーンやオーバーレイネットワークでは、文書化されたルーティングまたはホストネットワークの対処が必要な場合があります。すべてのオーバーレイクラスターに `istiod hostNetwork: true` を指定しないでください。

### mTLS を維持し、L7 の担当を分ける

Istio で暗号化されたワークロードのトラフィックに、平文を前提とする Cilium HTTP 検査を適用しないでください。この例では Istio の mTLS と L7 ルーティングを維持し、Cilium の**L3/L4 のみ**のポリシーを使います。古い L7 統合例を動かすためだけに mTLS を無効化すると、セキュリティ設計が変わってしまいます。

次の設定は、`productpage` と `reviews` ワークロード、ポート 9080 の reviews Service、`version: v1`／`v2` ラベルの reviews Pod がすでに存在する `istio-cilium-demo` Namespace 用の**サイドカーモード**設定です。Bookinfo 全体のデプロイ手順ではありません。

**`istio-reviews.yaml`**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: istio-cilium-demo
spec:
  hosts:
  - reviews.istio-cilium-demo.svc.cluster.local
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v2
        port:
          number: 9080
  - route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v1
        port:
          number: 9080
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: istio-cilium-demo
spec:
  host: reviews.istio-cilium-demo.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-cilium-demo
spec:
  mtls:
    mode: STRICT
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: reviews-l4
  namespace: istio-cilium-demo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: istio-cilium-demo
        k8s:app: productpage
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
```


DestinationRule は VirtualService が参照する Subset を定義します。`end-user: jason` ヘッダーはデモルートを選択するためのもので、認証済み ID ではありません。サイドカーの Injection が成功していること、実際のエンドポイントラベル、Subset の Readiness、メッシュのテレメトリを確認してください。

ポート 9080 の Cilium ルールを ambient 用ポリシーの例として再利用しないでください。ambient の HBONE はポート 15008 で暗号化トンネルを使うため、可視トラフィックと ID の境界が異なります。そのトポロジーに適した Istio ポリシーと、プラットフォーム固有の Cilium ネットワークガードを適用してください。

## ロードバランシングのアーキテクチャ

Cilium の Service Map、Backend Map、Reverse NAT 状態、接続追跡は、異なる転送段階を支えます。L7 の Envoy ロードバランシングは別コンポーネントです。そのアルゴリズム一覧を BPF Service データパスのアルゴリズムと混同しないでください。

### BPF 転送モードとアルゴリズム

| 設定／方式 | 意味と制約 |
|---|---|
| `loadBalancer.mode: snat` | 既定の転送モードです。対象となる外部 Service 経路では、直接返信ではなく送信元変換と返信用状態を使用します。 |
| `dsr` | リモートバックエンドからの返信が、入口側のロードバランサーノードを経由せずに返る方式です。ネットワークでその返信経路が許可されている必要があります。上流プロキシですでに変換されたクライアント IP を復元することはできません。 |
| `hybrid` | TCP は DSR、UDP は SNAT を使います。これは有効なロードバランサー動作であり、無効なトンネル／自動ダイレクトルーティングの組み合わせとは別です。 |
| アノテーションによる転送 | Service ごとにオプトインする対応機能です。転送アノテーションは作成時に選ぶものであり、後から変更すると接続が壊れることがあります。 |
| `loadBalancer.algorithm: random` | BPF のバックエンド選択で使われる既定アルゴリズムです。 |
| `maglev` | 対応する外部 N–S 経路では、一貫性のあるバックエンド選択を行います。対応する XDP 高速化も含みます。通常のソケット LB による E–W 接続には Maglev は適用されません。 |
| `sessionAffinity: ClientIP` | Kubernetes Service の独立したアフィニティ機能です。キーは外部接続元 IP、または該当するクラスター内ソケット LB トラフィックの場合はクライアントのネットワーク名前空間 Cookie です。 |

Maglev を使っても、バックエンド削除後にセッションが存続する保証はありません。ノード間でバックエンド状態、テーブルサイズ、シードを一致させる必要があります。テーブルサイズの既定値は 16381 です。以下で使用する 65521 は許可される値ですが、すべての環境で推奨される値ではありません。大きなテーブルほどメモリを消費します。アフィニティの有効期限と接続状態はハッシュ処理とは別です。

DSR のディスパッチには、ネイティブルーティングでの IP オプション、文書化されたネイティブ／Geneve オーバーレイ構成での Geneve、またはネイティブルーティング専用の IPIP/IP6IP6 経路を使用できます。VXLAN オーバーレイは Geneve による DSR ディスパッチの代わりにはなりません。IPIP には独自のポート／変換制約があるため、選択前にリリースガイドを確認してください。

XDP 高速化には対応するデバイス／ドライバーが必要です。`native` は選択したデバイスが対応していることを前提とし、`best-effort` は対応している場所で有効にします。古い `enable-xdp-acceleration` キーを書くだけでは有効になりません。また、早期の XDP 転送は tcpdump が後段で取得する地点から見えない場合があります。

### Cilium と kube-proxy

| 項目 | 正確な比較 |
|---|---|
| Linux の Service 実装 | Cilium は BPF フック／マップを使います。kube-proxy には iptables と nftables の各モードがあり、IPVS は Kubernetes 1.35 で非推奨になりました。 |
| プラットフォーム | Cilium には明記された Linux／カーネル要件があります。Windows の kernelspace kube-proxy は別の実装です。 |
| 接続状態 | Cilium の BPF 接続／NAT 状態は Linux netfilter conntrack とは別です。「片方は任意、もう片方は常時有効」という比較は大まかすぎます。 |
| L7 | Cilium は対応プロキシと統合します。kube-proxy の Service 転送は HTTP ポリシーエンジンではありません。 |
| パフォーマンス | 同じワークロードと構成で測定してください。製品名だけから一律の優劣は決まりません。 |

Linux の IPVS サブシステムにダイレクトルーティング機能があるというだけで、kube-proxy の DSR 構成を推測しないでください。

## DSR/Maglev の事前準備済みラボ

このプロファイルは、kube-proxy を使用しないよう新規に準備した **IPv4 Geneve オーバーレイ**のテストクラスター用です。既存 CNI の移行、kube-proxy の削除、クラウド側の送信元偽装対策／ルーティング設定は行いません。Pod CIDR が競合しないようにし、外部への返信経路を検証してください。

**`lb-values.yaml`**

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


実際の API エンドポイントと、クラスター単位で永続化する Maglev シードを指定します。シードはランダムな 12 バイトを Base64 エンコードしたものです。一度だけ生成してクラスターの値とともに保存し、アップグレードごとに再生成せず再利用してください。

```bash
: "${API_SERVER_HOST:?Set the reachable real API server host, not its ClusterIP}"
: "${API_SERVER_PORT:?Set the actual API server port}"
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

選択したクラスターで、このガイドが作成した Namespace を使用します。別の使い捨てクラスターを使う場合は、そこで Namespace の作成とラベル付けをやり直してください。HTTP ポリシー用アプリケーションと、この外部 LB のバックエンドでは異なるラベルを使うため、先に作成したクライアント専用 HTTP ルールがこの実験を誤って遮断することはありません。

**`lb-echo.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lb-echo
  template:
    metadata:
      labels:
        app: lb-echo
    spec:
      automountServiceAccountToken: false
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  type: NodePort
  selector:
    app: lb-echo
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f lb-echo.yaml
kubectl -n cilium-l2l7-demo rollout status deployment/lb-echo --timeout=120s
kubectl -n cilium-l2l7-demo get pods -l app=lb-echo -o wide
kubectl -n cilium-l2l7-demo get service lb-echo -o wide
NODEPORT=$(kubectl -n cilium-l2l7-demo get service lb-echo -o jsonpath='{.spec.ports[0].nodePort}')
```

到達可能な入口ノードのうち、バックエンドノード**とは別のノード**を選び、Cilium のクラスター内ソケット LB の影響を受けない外部クライアントを使います。そのクライアントから実際の値を使って `http://ENTRY_NODE_IP:NODEPORT/` にリクエストします。Pod から ClusterIP への curl が成功しても、外部 DSR や Maglev の動作は証明できません。リクエスト／返信経路とバックエンド／接続状態を検証し、HTTP 応答が成功しただけで動作を推測しないでください。

## マスカレード

Pod の外向きマスカレードは、構成した外部経路で必要な場合に送信元アドレスを変更します。暗号化でもファイアウォールでもなく、Service の DNAT や DSR 転送とも別の機能です。

次の設定断片は、ネットワークが Pod の送信元アドレスと返信経路を実際にサポートする場合に限り、例示の `10.0.0.0/8` 宛てトラフィックを送信元マスカレードの対象外にします。

**`masquerade-values.yaml`**

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```


`ipv4NativeRoutingCIDR` は、ルーティング可能と仮定する範囲と、それに対応したマスカレード除外を示します。ルートを設定したり、データパス全体をネイティブルーティングへ切り替えたりするものではありません。返信経路が機能しない状態で広い範囲を除外すると、接続が壊れる可能性があります。

- このリリースでの BPF マスカレードは BPF NodePort 機能に依存し、BPF プログラムをロードしたデバイスにのみ適用されます。対象デバイスを確認し、必要なら文書化された `devices` 設定を使ってください。
- iptables 実装では文書化された `egressMasqueradeInterfaces` の動作を使います。このフィールドや、削除済みの汎用 `masquerade-interfaces`／`masquerade-all` の例を、BPF にも共通する制御項目として扱わないでください。
- IPv6 の BPF マスカレードはベータ版と記載されています。どちらの実装でも Cilium のプラットフォーム／カーネル要件はなくならず、最終的にはカーネル内でトラフィックを処理します。
- ノードアドレスの例外、ip-masq-agent の除外、後段のクラウド／NAT ゲートウェイによって、観測される送信元は変わることがあります。管理された観測先とノード側の状態／キャプチャを使ってください。任意の公開サイトへ到達できても、特定の NAT 実装を使った証明にはなりません。

対象エージェント上で実行します。

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
```

## フラグメント処理と MTU

リリース版のフラグメントトラッカーは、データグラムの識別情報と L4 の送信元／宛先ポートを、容量制限のある LRU マップに保存します。L4 ヘッダーを持たない後続フラグメントについてポート情報を復元できますが、これは**BPF によるペイロード再構成エンジンではなく**、フラグメント攻撃を防ぐ保証でもありません。

文書化された機能は IPv4 と IPv6 のトラッキングを含み、対応するフラグによって既定で有効になっており、ベータ版です。有効な IPv4 フラグは引き続き `enable-ipv4-fragment-tracking` です。`bpf-fragments-map-max` は追跡対象データグラムマップの容量を制御します。古い `fragment-tracking-timeout` と `max-fragments-per-flow` は、リリース版で有効な設定項目ではありません。

チャートの追加設定マップを使う明示的な例を示します。

**`fragment-values.yaml`**

```yaml
extraConfig:
  enable-ipv4-fragment-tracking: 'true'
  bpf-fragments-map-max: '8192'
```


8192 は容量の例であり、フローあたりの最大フラグメント数ではありません。容量を調べるときは `cilium_ipv4_frag_datagrams`／`cilium_ipv6_frag_datagrams` とその逼迫状況を確認してください。逼迫の指標は再構成成功や攻撃防止を示すカウンターではありません。

適切なパケットサイズと、機能する Path MTU Discovery 経路を優先してください。PMTUD は関連するエラー通知とネットワークの動作に依存し、どの環境でも自動的に最適なサイズが得られるわけではありません。Cilium の `MTU` は**基盤ネットワークの上書き値**です。[ネットワーキングガイド](03-networking.md)で説明しているように、通常の VXLAN オーバーヘッドは IPv4 アンダーレイで 50 バイト、IPv6 で 70 バイトです。1500 バイトの経路に対して基準値を安易に 1450 にすると、オーバーヘッドを二重に差し引く場合があります。

## 可観測性とトラブルシューティング

適切なノード、実際の Envoy 配置モード、意図したポリシー、反映済みエンドポイント状態、新しいトラフィックを確認してください。エージェント内の操作には `cilium-dbg` を、クラスター操作にはスタンドアロン CLI を使います。削除済みの `policy trace` コマンドや、エンドポイントの強制再生成から診断を始めないでください。

別のターミナルで有効な Hubble Relay のポートフォワードを実行したまま、対象フローを観察します。

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

HTTP ポリシーによる拒否は、パケットの DROPPED 判定ではなく HTTP 403 として現れる場合があります。タイムアウトだけでは、Readiness、DNS、ルーティング、TLS、観測上の問題も考えられます。すべてのエラーをポリシー成功の証拠と見なさず、各レイヤーを突き合わせてください。

## 検証上の制約と参照先

これらはリリース時のソースとスキーマで確認した例であり、限定されたローカル用リソースを使っています。本番環境での試験や稼働クラスターでのベンチマーク結果ではありません。イメージの実行、Webhook への到達性、mTLS トラフィック、DSR の返信経路、NAT の動作、フラグメント処理は、準備した環境で引き続き検証が必要です。この実行で付けたラベルのアプリケーションリソースだけを削除し、ラボの後片付けとしてクラスター CNI を削除しないでください。

- [Cilium kube-proxy 置き換え／DSR／Maglev](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/kubeproxy-free.rst)、[マスカレード](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/masquerading.rst)、[フラグメント処理](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/fragmentation.rst)、[フラグメントマップ実装](https://github.com/cilium/cilium/blob/v1.20.3/pkg/maps/fragmap/fragmap.go)
- [L2 Announcements](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/l2-announcements.rst)、[マルチキャスト](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/multicast.rst)、[HTTP ルールトランスレーター](https://github.com/cilium/cilium/blob/v1.20.3/pkg/envoy/policy/envoy_l7_rules_translator.go)、[Envoy チャートの既定値](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/templates/_helpers.tpl)
- [Cilium／Istio 統合](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/istio.rst)、[Istio CNI／init コンテナの各モード](https://istio.io/latest/docs/setup/additional-setup/cni/)、[Webhook の要件](https://istio.io/latest/docs/ops/configuration/mesh/webhook/)、[Istio 1.31 スキーマ](https://github.com/istio/istio/blob/1.31.0/manifests/charts/base/files/crd-all.gen.yaml)
- [Kubernetes Service のプロキシモード／アフィニティ](https://kubernetes.io/docs/reference/networking/virtual-ips/)、[Cilium 1.20.3 の値](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)

[メインページに戻る](README.md)

## クイズ

[L2–L7 とロードバランシングに関する問題を確認する](../../quizzes/networking/cilium/05-l2-l7-networking-quiz.md)。
