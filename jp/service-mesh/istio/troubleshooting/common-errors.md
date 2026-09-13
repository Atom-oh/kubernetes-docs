# Istioでよくあるエラーと解決方法

> **最終更新**: September 11, 2026 · CLI/設定確認: Istio 1.31.0

観測した障害、実効設定、ワークロードモードから始めます。以下は診断例で、メッシュをリセットする指示ではありません。Kubernetes/EKS版の[インストール互換性ガイダンス](../01-installation.md)を確認してください。

例は既存app名前空間、8080のDeployment/Service myapp、istio-ingress名前空間、デフォルトcluster DNS suffixを使います。実リソース/ドメインへ置換します。Deployment YAMLは**既存Deployment向けstrategic-merge断片**で、完全な新アプリではありません。レビューでクラスターのデプロイや本番ワークロードテストはしていません。

```bash
NS=app
GW_NS=istio-ingress
ISTIO_NS=istio-system
: "${POD:?Set the exact application Pod name}"
kubectl config current-context
istioctl version
kubectl -n "$NS" get pod "$POD" -o wide
```

## 目次

1. [Pod終了中の接続エラー](#connection-errors-during-pod-termination)
2. [サイドカー注入の問題](#sidecar-injection-issues)
3. [mTLS接続失敗](#mtls-connection-failure)
4. [VirtualServiceルーティング失敗](#virtualservice-routing-failure)
5. [Gateway設定の問題](#gateway-configuration-issues)
6. [メモリと性能の問題](#memory-and-performance-issues)
7. [証明書期限切れ](#certificate-expiration)
8. [DNS解決失敗](#dns-resolution-failure)
9. [Envoy初期化タイムアウト](#envoy-initialization-timeout)
10. [デバッグツール](#debugging-tools)

## Pod終了中の接続エラー {#connection-errors-during-pod-termination}

### 問題の説明

終了時にconnection reset、broken pipe、EOF、HTTP 503が起こり得ます。それだけでEnvoyが先に終了したとは証明できません。アプリ/プロキシログ、応答フラグ、Pod削除時刻、EndpointSlice変更を関連付けます。

### 根本原因

従来のアプリコンテナとcontainers内サイドカーには終了順序保証がありません。アプリがまだ必要としている間にプロキシが終了する場合も、既存要求完了前にアプリが受付を止める場合もあります。KubernetesネイティブサイドカーはrestartPolicy:AlwaysのinitContainersを使い、主コンテナ後に終了します。

Pod猶予期間はpreStop実行を含みます。常に30秒ではなく、終了済みプロセスが後から再びkillされるわけでもありません。endpoint更新、LB伝播、長時間接続で追加の失敗期間が生じ得ます。

### 解決方法

#### 方法1: アプリとプロキシ終了時間を予算化

アノテーションはプロキシdrainを設定し、preStopフックの導入や全active要求の無条件待機は**しません**。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      terminationGracePeriodSeconds: 60
```

30/60秒は例で、普遍的最小値ではありません。アプリ終了、フック、プロキシdrainを合わせて予算化します。holdApplicationUntilProxyStartsは**起動**の設定で終了順序ではありません。ProxyConfig変更の反映には新Podが必要です。

1.31の通常terminationDrainDuration経路は時間ベースです。EXIT_ON_ZERO_ACTIVE_CONNECTIONS有効時は最小drain期間を待ち、下流リスナー接続数をポーリングします。その経路は通常drainタイマーを固定上限には使いません。Kubernetes猶予制限と欠損/エラー統計も適用されます。代表接続で選択動作を検証します。

#### 方法2: ネイティブサイドカーの順序を検討

対応Kubernetes/Istio構成で、新規かつ注入対象Podのネイティブ注入を選びます。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
      labels: {}
    spec: {}
```

Kubernetes機能は1.33から安定版ですが、IstioアノテーションはAlphaと文書化されています。実注入initContainersとアプリ終了を確認します。順序だけでは要求失敗ゼロやPod猶予を越える無期限待機を保証しません。Ambientにはこの方法で設定するPod別Envoyがありません。

sidecar.istio.io/terminationGracePeriodSecondsという文書化されたアノテーションはありません。実spec.terminationGracePeriodSecondsを設定します。

#### 方法3: インストール全体のデフォルト

以下は**istioctlインストール入力**で、削除されたクラスター内Istio Operatorが調整するリソースではありません。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      terminationDrainDuration: 30s
      holdApplicationUntilProxyStarts: true
```

所有者を通じてレンダリング変更をレビューし、対象ワークロードを意図的にロールアウトします。旧shell/netstat preStopループは無制限で、待受ソケットを数え、プロキシイメージ内ツールを前提としていました。アプリ処理完了を確実に待つものではありませんでした。

### 検証方法

```bash
kubectl -n "$NS" get pod "$POD" -o json
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
kubectl -n "$NS" get events --field-selector "involvedObject.name=$POD"
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Podが存在する間にログを取得します。--previousは同Podの前コンテナインスタンスで、「終了中の現在コンテナ」ではなく、任意の削除Podログを復旧もしません。

### ベストプラクティス

アプリのSIGTERM処理と実readiness契約を実装します。/tmp/not-ready作成はアプリ/プローブが読まなければ無効果です。制限付きpreStop遅延は伝播時間を確保し得ますが、endpoint収束の証明や安全なアプリ終了の代わりではありません。アプリsleepの普遍的禁止も60秒の普遍的最小値もありません。書込再試行を無効にし、生HTTP/非HTTP失敗を測定します。[ロールアウト比較](../comparison/03-sidecar-vs-ambient.md)を参照します。

## サイドカー注入の問題 {#sidecar-injection-issues}

### 問題1: サイドカーが注入されない

プロキシ不在と判断する前に通常/ネイティブ両配置を確認します。

```bash
kubectl -n "$NS" get pod "$POD" -o jsonpath='{.spec.containers[*].name}{"\n"}{.spec.initContainers[*].name}{"\n"}'
kubectl get namespace "$NS" --show-labels
kubectl -n "$NS" get deployment myapp -o yaml
istioctl x check-inject "$POD" -n "$NS"
kubectl get mutatingwebhookconfigurations
kubectl -n "$ISTIO_NS" get pods -l app=istiod --show-labels
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

Ambient参加では意図的にistio-proxyアプリサイドカーがありません。サイドカーモードはnamespace revision/tag、Podテンプレートラベル、hostNetwork、Webhookセレクター、admissionイベントを確認します。自動注入はhost-network Podと指定system名前空間を除外します。

[注入ガイド](../advanced/07-sidecar-injection.md)に従い、意図する導入revision/tagか従来ラベルを使います。競合するistio-injectionとistio.io/revを併用しないでください。ラベルは新Podに作用し既存Podを改変しません。影響確認後に所有者を通じて対象ワークロードだけを再作成します。

推奨Pod別上書きはテンプレート下の**ラベル**です。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations: {}
      labels:
        sidecar.istio.io/inject: 'true'
    spec: {}
```

対応アノテーションは非推奨です。falseラベルは意図的除外の場合があり、無条件上書きするエラーではありません。trueでも全Webhook選択/プラットフォーム制限を迂回しません。注入はIstiodが提供し、旧app=sidecar-injectorログセレクターは現統合injectorを識別しません。

### 問題2: サイドカーのリソース不足

終了理由、イベント、使用量、スロットリングを調べます。OOMKilledはメモリ上限問題を示し得ますが、CrashLoopBackOffは多様な原因による再起動/バックオフ状態です。runAsNonRoot/非数値ユーザー検証エラーはsecurity context/イメージ問題で、RAM増加では直りません。

測定で変更が妥当ならPodテンプレートでrequestsとlimitsを一緒に設定します。例の量はワークロード別サイジングが必要です。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/proxyCPU: 200m
        sidecar.istio.io/proxyCPULimit: 1000m
        sidecar.istio.io/proxyMemory: 256Mi
        sidecar.istio.io/proxyMemoryLimit: 512Mi
      labels: {}
    spec: {}
```

新注入リソースと名前空間LimitRange/ResourceQuotaを検証します。admission通過だけのためにイメージセキュリティ設定を上書きしないでください。

## mTLS接続失敗 {#mtls-connection-failure}

### 問題の説明

上流接続エラー、503、WRONG_VERSION_NUMBERはTLS、プロトコル、endpoint、ネットワークが原因の場合があります。PeerAuthenticationは**受け入れる受信mTLS**を制御し、DestinationRule TLSはclient Envoyの送信TLSを制御します。clientのPeerAuthenticationをSTRICTにしても、それだけでmTLS開始を強制しません。

### PeerAuthenticationとDestinationRule

auto mTLS有効で明示DestinationRule TLS上書きがなければ、既知メッシュendpointへworkload mTLSを選びます。明示DISABLEはSTRICT宛先と競合し得ます。意図しない上書きは所有者経由で削除するか、意図的Istio mTLS宛先にISTIO_MUTUALを使います。任意外部TLS/平文サービスへ強制しないでください。

呼び出し元がstrict対応後、以下のセレクターなしポリシーを**app名前空間**に適用します。

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
```

設定root名前空間（通常istio-system）のセレクターなしポリシーは、そこだけでなくメッシュ全体です。適用前に移行影響を確認します。AmbientはPeerAuthentication DISABLEで転送mTLSを無効にできません。認証とAuthorizationPolicyは別で、403が自動的にTLS失敗とは限りません。

### デバッグコマンド

```bash
istioctl x describe pod "$POD" -n "$NS"
kubectl get peerauthentication -A -o yaml
kubectl get destinationrule -A -o yaml
istioctl proxy-config clusters "$POD" -n "$NS" \
  --fqdn myapp.app.svc.cluster.local -o json
istioctl proxy-config secret "$POD" -n "$NS"
```

送信cluster設定は関連callerプロキシ、受信ポリシーはreceiverで確認します。experimental describeは補助で、全経路暗号化の証明ではありません。証明書期限、ID、trust domain、実transport socket、応答フラグを調べます。waypointとztunnelは診断が異なります。[mTLSガイド](../security/01-mtls.md)を参照します。

## VirtualServiceルーティング失敗 {#virtualservice-routing-failure}

### 問題1: 通信がルーティングされない

404はEnvoyかアプリ由来です。変更前に発生元と応答詳細を特定します。hosts:myapp.example.comから内部Service myappへ送るVirtualServiceは、適切なGatewayに接続しHost/authority一致なら**有効**です。入口hostとbackend名は同じでなくても構いません。

メッシュ通信は要求service host、IngressはGateway許可ドメインに一致させ、VirtualServiceをそのGatewayへ接続します。短い宛先名は設定リソースの名前空間基準なので、明示FQDNは名前空間間の曖昧さを減らします。

### 問題2: subsetがない/正常な上流がない

完全な組み合わせで名前付きsubsetへメッシュルーティングします。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: app
spec:
  host: myapp.app.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Serviceはversion:v 1ラベルの準備済みendpointを実際に選ぶ必要があります。subset名一致だけではPod作成、Serviceセレクター修正、健全化はしません。宛先ポート、プロトコル選択、可視範囲、競合ルートを確認します。上の例はデフォルトcluster.localを前提とします。

### デバッグ

```bash
istioctl analyze -n "$NS"
istioctl proxy-config routes "$POD" -n "$NS"
istioctl proxy-config endpoints "$POD" -n "$NS"
kubectl -n "$NS" get svc myapp -o yaml
kubectl -n "$NS" get pods -l app=myapp --show-labels
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

analyzeは静的設定支援です。実際に要求を運ぶプロキシのroute/cluster/endpointを確認します。設定伝播は即時ではありません。Serviceへ送られたIngress要求が、他のmesh-only VirtualServiceのsubset選択を自動継承するわけではありません。


## Gateway設定の問題 {#gateway-configuration-issues}

### 問題1: Gatewayに届かない

HTTP応答前の拒否/timeoutはDNS、listener/Serviceポート不一致、LBターゲット欠落、ネットワークフィルターを示し得ます。まず実Gateway Deployment/Serviceを探します。名前空間と名前は導入方法によります。

```bash
kubectl -n "$GW_NS" get svc,pods --show-labels
kubectl -n "$GW_NS" get gateways.networking.istio.io -o yaml
kubectl -n "$NS" get virtualservice -o yaml
# For installations using Kubernetes Gateway API instead:
kubectl get gatewayclasses.gateway.networking.k8s.io
kubectl -n "$GW_NS" get gateways.gateway.networking.k8s.io -o yaml
kubectl -n "$NS" get httproutes.gateway.networking.k8s.io -o yaml
```

ServiceのloadBalancer ingressを確認します。providerはIP、host名、両方を公開できます。EKSでは実controller設定でLBターゲットhealth、type、SG、経路も確認します。Istiod再起動では異常AWSターゲットは直りません。

Istio Gateway（networking.istio.io）とKubernetes Gateway API（gateway.networking.k 8s.io）は別です。Gateway APIはAccepted、Programmed、ResolvedRefsなどHTTPRoute parent条件とcontrollerイベントを調べます。名前の誤記、listener不一致、接続拒否は外部接続失敗と別修正が必要です。

### 問題2: HTTPSとルート接続

例は**Istio Gateway API**です。selectorを実Gateway Podラベルへ置換し、所有ドメインと有効証明書を使い、Serviceが443を公開することを確認します。前節と同じbackend subsetを使います。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: myapp-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls-secret
    hosts:
    - myapp.example.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp-ingress
  namespace: app
spec:
  hosts:
  - myapp.example.com
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
  gateways:
  - istio-ingress/myapp-gateway
```

SIMPLEが下流TLS終端するためrouteはhttpです。TLS PASSTHROUGHなら適切なTLS/SNIルートが必要です。終端listenerとtlsルートだけを混ぜたり、不透明パススルー内のHTTPパス一致を期待したりしないでください。

credentialNameはGateway workloadからアクセス可能な認証情報を参照します。例ではPodとTLS Secretはistio-ingressです。

```bash
kubectl -n "$GW_NS" create secret tls myapp-tls-secret   --cert=path/to/fullchain.pem   --key=path/to/key.pem
```

管理済みSecretなら既存所有者の更新処理を使います。コマンドは証明書取得も自己署名issuerの信頼確立もしません。domain/SAN、提供chain、期限、client信頼、Gateway SDSを確認します。別Gateway設定オブジェクトの名前空間は、workloadの認証情報名前空間の普遍的な代替ではありません。

## メモリと性能の問題 {#memory-and-performance-issues}

### 問題1: Envoyメモリ使用増加

実メモリ/CPU、limits、接続、routes/clusters/listeners、テレメトリーcardinalityを比較します。大きな無関係ConfigMap/Secretが全プロキシに自動読込されるわけではありません。消費する設定/データだけが占有量を説明できます。リークには版固有の証拠が必要です。

未使用設定が支配的なら、範囲限定Sidecarで選択**サイドカー**ワークロードが取り込む設定を制限できます。

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: myapp-scope
  namespace: app
spec:
  workloadSelector:
    labels:
      app: myapp
  egress:
  - hosts:
    - ./*
    - istio-system/*
```

例はappとistio-systemのサービスだけを含みます。範囲縮小前に実名前空間間/外部依存を把握し、Sidecar selector重複を避けます。設定範囲の限定で、Egress firewallやambient waypoint policyではありません。先のPodテンプレートアノテーションで実測からメモリrequests/limitsを決めます。

### 問題2: 高レイテンシー

P99が1秒超でも、定義したワークロード予算に対する症状です。timeout変更前にアプリ時間、上流遅延、飽和、CPUスロットリング、接続プール、ペイロード、再試行増幅を確認します。

以下は前のmyapp VirtualServiceの**代替**で、5秒のroute期限と明示再試行無効を加えます。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
    timeout: 5s
```

期限は待機を制限しbackendを速めません。盲目的再試行は過負荷と不明書込の重複を増幅し得ます。特定冪等操作で適切なら、全体期限に対して明示予算を設け実試行を測定します。[再試行とタイムアウト](../traffic-management/05-retry-timeout.md)を参照します。

## 証明書期限切れ {#certificate-expiration}

### 問題の説明

x 509期限切れやhandshake失敗はworkload leaf、署名中間/root、Ingress証明書、時刻ずれに関係し得ます。期限はCA/provider/設定に依存し、「10年」「24時間」は普遍的診断ではありません。

### 診断と復旧

実公開trust bundleと読込workload証明書を調べます。

```bash
# Public trust bundle, not a private CA key.
kubectl -n "$NS" get configmap istio-ca-root-cert \
  -o jsonpath='{.data.root-cert\.pem}' > root-cert.pem
openssl crl2pkcs7 -nocrl -certfile root-cert.pem |
  openssl pkcs7 -print_certs -text -noout
istioctl proxy-config secret "$POD" -n "$NS"
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

カスタム統合では標準trust ConfigMapが異なり得るためCA providerを確認します。PKCS7表示はPEM bundleの最初だけでなく全証明書です。現在UTC、CA/CSRエラー、IDトークン、Istiod/SDS到達性、更新処理と期限を関連付けます。

istioctl 1.31にx ca rootコマンドはありません。leaf期限切れだけでCA削除/再生成しないでください。計画外root置換は依存全ワークロードを壊し得ます。実更新/接続/provider問題を直し、必要な信頼重複を持つ対応CA rotation手順を使います。復旧に必要な場合だけ特定の影響ワークロードを再起動します。

## DNS解決失敗 {#dns-resolution-failure}

### 問題の説明

no-such-hostやlookup timeoutは、アプリDNS、CoreDNS/上流DNS、Service存在/search suffix、Istio DNS捕捉を区別します。

```bash
kubectl -n kube-system get svc kube-dns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=kube-dns
# Run from the affected app container only if it includes these tools.
kubectl -n "$NS" exec "$POD" -c myapp -- cat /etc/resolv.conf
kubectl -n "$NS" exec "$POD" -c myapp -- nslookup myapp.app.svc.cluster.local
```

最小アプリ/プロキシイメージに診断ツールがあると想定しないでください。必要なら承認済み診断コンテナを使います。UDP/TCP 53両方のNetworkPolicy、node/resolver到達性、対象PodのdnsPolicy/searchを確認します。

ServiceEntryはIstioに外部サービスを登録し、CoreDNS修復、公開DNS作成、未解決hostの解決可能化はしません。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: app
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

api.example.comを実hostへ置換します。DNS解決が上流endpointを決めます。mode/版/設定によりIstio DNS捕捉/IP割り当てが合成アドレスを返す場合がありますが、実上流の解決/到達性は証明しません。[DNS捕捉ガイド](../advanced/04-dns-cache.md)を確認します。すでにHTTPS送信するアプリで、ここにHTTPSを宣言しても第2のTLS開始層は不要です。

## Envoy初期化タイムアウト {#envoy-initialization-timeout}

### 問題の説明

「Waiting for Envoy proxy to be ready」はxDS/CA接続、設定拒否、リソース、証明書/トークン、bootstrapが原因となり得ます。プローブ遅延を増やす前にPod/init状態、proxy/Istiodログ、イベント、proxy-statusを確認します。

holdApplicationUntilProxyStartsはproxy readyまでアプリを遅らせますが、readyになれないEnvoyを直しません。initialDelaySecondsだけのreadinessProbeはactionがなく無効です。

アプリが8080に実際に/readyを実装するなら、この断片は具体的startup/readiness契約を提供します。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      containers:
      - name: myapp
        startupProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
          failureThreshold: 3
```

actionとしきい値をアプリに合わせます。StartupProbeは起動許容、readinessはendpoint選択資格を制御し、どちらもIstiod到達性は修復しません。アプリプローブ失敗をEnvoy初期化のせいにする前に注入rewriteと実効proxy準備設定を確認します。

## デバッグツール {#debugging-tools}

### istioctlコマンド

```bash
istioctl analyze -A
istioctl proxy-status
istioctl proxy-config all "$POD" -n "$NS"
istioctl proxy-config log "$POD" -n "$NS"
# Temporarily change levels only on the selected Envoy.
istioctl proxy-config log "$POD" -n "$NS" --level http:debug
# Restore the previously recorded levels afterwards; --reset restores defaults.
istioctl bug-report --include "$NS" --duration 10m

# Ambient has ztunnel diagnostics; Envoy commands apply to waypoints.
istioctl ztunnel-config workloads -n "$ISTIO_NS"
istioctl ztunnel-config certificates -n "$ISTIO_NS"
```

experimentalコマンドは変化し得て、通信検証の代わりではありません。一時デバッグ前にレベルを記録して戻します。resetはデフォルトなので元のカスタム設定とは異なる場合があります。期間を制限し、bug-report共有前に収集設定/ログを確認します。

### Envoy Admin API

ループバックにだけ転送します。

```bash
# Keep this command running; use a second terminal for the HTTP requests.
kubectl -n "$NS" port-forward --address 127.0.0.1 "$POD" 15000:15000

```

別ターミナルで:

```bash
curl --fail --silent --show-error http://127.0.0.1:15000/clusters
curl --fail --silent --show-error http://127.0.0.1:15000/stats/prometheus
curl --fail --silent --show-error http://127.0.0.1:15000/config_dump
```

サイドカー/waypointを含むEnvoy用で、ztunnelの別adminには適用しません。終了時にport-forwardを閉じます。ログ変更は上の選択proxy用istioctlを優先し、その後記録値に戻します。

### 一般的なログ確認

```bash
kubectl -n "$NS" logs "$POD" -c myapp
kubectl -n "$NS" logs "$POD" -c istio-proxy
# Only when that container has a prior instance in this same Pod:
kubectl -n "$NS" logs "$POD" -c istio-proxy --previous
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
```

稼働中/現Podからのログ収集は削除Podの保持ではありません。要求時刻、trace/request ID、応答フラグ、関連endpoint/設定変更を障害証拠とともに保持します。

## 参考資料

- [注入の問題解決](https://istio.io/latest/docs/ops/common-problems/injection/)と[注入設定](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [ネットワーク問題](https://istio.io/latest/docs/ops/common-problems/network-issues/)と[TLS方向/auto mTLS](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Istioアノテーション](https://istio.io/latest/docs/reference/config/annotations/)と[リリース1.31プロキシ終了コード](https://github.com/istio/istio/blob/1.31.0/pkg/envoy/agent.go)
- [Kubernetes Pod終了](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)と[ネイティブサイドカー](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [プロキシ診断](https://istio.io/latest/docs/ops/diagnostic-tools/proxy-cmd/)、[CA統合](https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/)、[セキュアIngress](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Kubernetes DNS診断](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/)と[Istio DNSプロキシ](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [可観測性](../observability/README.md)、[セキュリティ](../security/README.md)、[トラフィック管理](../traffic-management/README.md)
