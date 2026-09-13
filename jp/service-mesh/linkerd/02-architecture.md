# Linkerdアーキテクチャ

> **最終更新**: September 11, 2026 · Linkerd edge-26.9.1 / proxy release/v2.368.0

現コンポーネントの役割、ID階層、通信捕捉、注入ライフサイクルを説明します。対応release/cluster構成と固定成果物は[インストールガイド](01-installation.md)を使います。以下は設定例で、監査では実デプロイやCA rotationをしていません。

## 全体アーキテクチャ

![Linkerdの中核3 Deploymentとメッシュpeer 2つの簡略図。policy controllerはDestination内で別表示せず、接続の一部を示す。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-0.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-0.html)

デフォルトcontrol-plane名前空間はlinkerdです。固定チャートの中核はlinkerd-destination、linkerd-identity、linkerd-proxy-injectorの3 Deploymentです。DestinationにはpolicyとServiceProfile-validatorコンテナもあり、論理役割と独立Deploymentは同じではありません。任意Viz/multiclusterは独自ライフサイクルを持ちます。

データプレーンは参加アプリに併設するRustプロキシです。このreleaseはnative sidecarがデフォルトです。Identity Deploymentは意図的に通常proxyとstartup wait無効を使うため、containersとinitContainers両方を確認します。

## コントロールプレーン

### Destination Controller

Destinationは検出状態を監視し、streaming APIでendpoint、期待ID、profile情報を提供します。現デフォルトはEndpointSliceです。ServiceProfileは従来設定として残り、Gateway APIルーティング/認可にはpolicy controllerも関わります。現routingをSMI TrafficSplitだけと説明したり、Destinationが旧拡張リソースを直接監視すると想定したりしないでください。

| 責務 | 意味 |
|---|---|
| 検出 | 要求Serviceのendpoint追加/削除とメタデータ |
| 期待ID | 送信proxyが選択peerを認証するための情報 |
| Profile | メトリクス、再試行、timeout用の対応route/profile設定 |
| 負荷分散入力 | endpointと設定重み。実遅延観測と要求/接続選択はproxyが行う |

以下はGoでなく**Protocol Buffersサービス抜粋**です。message定義とimportは固定proxy APIにあります。

```protobuf
// Excerpt: message definitions/imports are in the linked API source.
service Destination {
  rpc Get(GetDestination) returns (stream Update) {}
  rpc GetProfile(GetDestination) returns (stream DestinationProfile) {}
}
```

Getはdestination更新、GetProfileはprofile更新をstreamします。streamやローカルcacheが設定を即時化したり、利用不能endpointへの対処を不要にしたりはしません。

### Identity Controller

デフォルトKubernetes IDフロー:

1. Proxy起動でローカル秘密鍵/CSR素材を確立。
2. Identity clientがCSR、要求ID、ServiceAccount tokenを送信。
3. IdentityがKubernetes TokenReviewでtokenを検証しDNS形式IDを導出。
4. 設定された**issuer署名認証情報**（通常中間issuer）がworkload証明書へ署名。
5. Clientが証明書/chainを読込み、期限前に更新。

trust anchorはchain検証の基盤です。その秘密鍵はIdentity controllerに不要で、rootが全workload CSRのonline署名者になるわけではありません。

以下は所有者用**Helm values断片**です。

```yaml
identity:
  issuer:
    issuanceLifetime: 24h0m0s
    clockSkewAllowance: 20s
    scheme: linkerd.io/tls
```

linkerd.io/tlsがデフォルトissuer schemeです。kubernetes.io/tls統合は対応する外部管理Secret形式を使います。所有者/キーを合わせずschemeを変えたり、部分identity ConfigMapでlinkerd-configのvalues全体を上書きしたりしないでください。

### Proxy Injector

![Linkerd CNIなしの適格Podの概念的admissionフロー。API serverがinjector変更を適用し、native proxy配置と除外は本文で説明する。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-3.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-3.html)

injectorはmutating admission webhookです。応答はAPI serverが適用する変更を記述し、図は概念でwire形式例ではありません。実Webhook選択、Pod上書き、platform適格性は引き続き適用されます。

選択名前空間を有効にします。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

Deploymentの上書きは**Podテンプレート**へ置きます。既存定義内の断片です。

```yaml
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: enabled
        config.linkerd.io/proxy-cpu-request: 100m
        config.linkerd.io/proxy-memory-request: 64Mi
        config.linkerd.io/proxy-cpu-limit: '1'
        config.linkerd.io/proxy-memory-limit: 250Mi
        config.linkerd.io/proxy-log-level: warn,linkerd=info
```

enabled|disabledではなくenabledかdisabledの1リテラル値を使います。アノテーション追加は既存Podを変更しません。Webhookは指定system名前空間を除外し、明示Pod上書きで有効な注入を無効にもできます。

| 注入/設定項目 | 役割 |
|---|---|
| linkerd-init | Linkerd CNIなしの場合のPodネットワーク捕捉設定 |
| linkerd-proxy | データプレーンproxy。このreleaseでは通常再起動可能initコンテナ |
| 投影ID tokenとローカルID保存 | Bootstrapとworkload証明書用。proxy鍵は共有workload Secretとして配布されない |
| 環境/プローブ/リソース | 注入で生成する版固有runtime設定 |

### Policy Controller

policyは受信認可と対応送信/要求ルーティングを制御します。例はapp:webラベルとhttpという宣言ポートのPodを選び、my-appのメッシュapi-gateway ServiceAccountを認可します。

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: web-http
  namespace: my-app
spec:
  podSelector:
    matchLabels:
      app: web
  port: http
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: web-api-gateway
  namespace: my-app
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: web-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: api-gateway
```

Serverは既存Pod/port対を選び、アプリ、Service、listenerを作りません。名前付きportは存在が必要です。該当ポリシーか明示代替アクセス方針で許可しなければ、選択通信はデフォルト拒否です。強制前に範囲を段階的にテストします。

AuthorizationPolicyはServerか対応routeを対象にできます。ServiceAccount参照は便利な認証要件で、MeshTLSAuthenticationとNetworkAuthenticationは追加ID/ネットワーク集合を表します。1 policy内の全required認証参照に一致が必要です。他の認可可能policyも確認します。

既存ServerAuthorization手順では以下は対応**代替**で、前の認可と一緒に適用する追加要件ではありません。

```yaml
apiVersion: policy.linkerd.io/v1beta1
kind: ServerAuthorization
metadata:
  name: web-authz-legacy
  namespace: my-app
spec:
  server:
    name: web-http
  client:
    meshTLS:
      serviceAccounts:
      - name: api-gateway
        namespace: my-app
```

リリースCRDはServerAuthorization v1beta1を提供し、旧例のv1beta2ではありません。Server v1beta2は提供継続し、例は現storage v1beta3です。AuthorizationPolicyが柔軟な推奨インターフェースです。別API groupのIstio同名リソースと混同しないでください。

## データプレーン

### Proxy動作とプロトコル範囲

linkerd2-proxyはRust製のメッシュ専用proxyです。HTTP/1.1、HTTP/2、gRPC、TCP対応です。HTTPルーティング/メトリクスは見えるHTTPが必要で、アプリ開始TLSは不透明、UDP/QUICやskip通信はTCP proxy経路の対象外です。

適格なメッシュTCP peerには転送mTLSを提供します。文書化されたメッシュ転送はTLS 1.3で、アプリTLSパススルーは別層です。未参加peerや明示捕捉迂回は別検討です。デフォルト受信policyは未参加の平文も受け、自動mTLSは全sourceの認証必須と同義ではありません。

proxyはHTTP要求に遅延対応負荷分散、不透明TCPに接続単位分散を使います。endpoint重み/route規則とruntime遅延推定は別です。EWMAを全要求が決定的に最速の1先へ行く保証と解釈しないでください。

普遍的10MBメモリ、p99<1ms、固定binary size保証はありません。測定は版/build、architecture、接続数、policy/設定、workload、計装に依存します。

### Proxyトラフィックフロー

![新しいメッシュ接続のHTTP要求。送信proxyが宛先を検出/選択し、両proxyがmTLSを確立、受信policyを経てアプリへ届く。既存接続は再利用可能。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-5.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-5.html)

送信検出、routing/balancing、再試行、timeoutと受信認可は異なります。新接続は検出/mTLS設定を行い、既存接続やcache設定を再利用できます。安全な再試行は特に書込でアプリ/プロトコルの判断です。

### 通信捕捉: linkerd-initまたはCNI

生成proxy-initまたはLinkerd CNI設定を使います。次は概念順序で、**実行するhost iptablesコマンドではありません**。

```text
Inside the Pod network namespace:
  outbound TCP -> evaluate proxy-UID and configured bypass rules first
               -> redirect intercepted traffic to the outbound proxy (default 4140)
  inbound TCP  -> evaluate configured bypass rules
               -> redirect intercepted traffic to the inbound proxy (default 4143)

Linkerd CNI: installs the Linkerd-specific capture setup through the CNI chain.
linkerd-init: performs the setup at Pod startup when Linkerd CNI is not used.
```

旧例は全TCP REDIRECT後にproxy UID迂回を追加しており、proxy自身の送信を保護できませんでした。host名前空間への適用もPod固有Linkerd設定ではありません。実装は追加除外/chainを含み、設定iptablesモードをサポートします。

opaque portはプロトコル検出をskipしつつproxy転送を維持します。skip portはproxyとメッシュ機能を迂回します。server-firstでは適切なopaque/protocol設定の代わりにskipしないでください。

### Proxyを手組みせず生成Podを確認

旧手組みPodはidentity/bootstrap素材が欠け、利用できない上流stable-2.16.0イメージを前提としていました。選択CLIと導入済みcontrol-plane設定で生成/確認します。

```bash
# The input is a complete, reviewed application manifest.
# Default mode adds the injection annotation for server-side admission.
linkerd inject web.yaml > web-annotated.yaml

# Manual mode materializes the proxy spec using the selected cluster configuration.
# Review/remove conflicting input config annotations before selecting CLI flags.
linkerd inject --manual --native-sidecar \
  --proxy-cpu-request 100m --proxy-memory-request 64Mi \
  --proxy-cpu-limit 1 --proxy-memory-limit 250Mi \
  web.yaml > web-manually-injected.yaml
```

デフォルトinjectはアノテーション変換です。edge-26.9.1のmanual生成も入力設定アノテーションを消費し、観測CPU request 700m指定は100m CLIフラグより優先され、入力log-levelも適用されました。競合入力を更新/削除して実proxyフィールドを確認します。manual生成proxyは後のアノテーション編集で自動再生成されません。短縮containerを完全導入としてコピーせず、所有者経由で生成workloadを更新します。

```bash
: "${APP_POD:?Set an application Pod name in my-app}"
kubectl -n my-app get pod "$APP_POD" -o json |
  jq '{pod: .metadata.name, proxies: ([.spec.containers[]?, .spec.initContainers[]?] | map(select(.name == "linkerd-proxy") | {image, restartPolicy, resources, startupProbe, readinessProbe, livenessProbe}))}'
```

native sidecarはrestartPolicy: AlwaysのinitContainersです。CNI経路設定時はlinkerd-initが省略されます。proxy healthは設定admin port（既定4191）の/liveと/readyです。native startup/readinessとアプリreadinessは別です。

## 証明書階層

| 素材 | デフォルトの役割/保存 |
|---|---|
| Trust anchor証明書/bundle | 公開信頼基盤。linkerd-identity-trust-roots ConfigMapのca-bundle.crt |
| Root CA秘密鍵 | PKI所有者の素材。Linkerd実行に不要 |
| Issuer証明書/秘密鍵 | linkerd-identity-issuer Secret。既定crt.pem/key.pem |
| Kubernetes TLS issuer統合 | tls.crt/tls.keyと一致schemeを使う意図的代替 |
| Workload鍵/証明書 | Proxyローカル認証素材。公称24h、自動更新 |

issuer/trust anchorの期限はPKI設定によります。既定CLI生成root/issuerは1年で、カスタム10年例はデフォルトや普遍的推奨ではありません。固定例時刻をコピーせず実日付を確認します。

### KubernetesワークロードID

デフォルトKubernetes ID機構ではDNS形式です。

```text
<service-account>.<namespace>.serviceaccount.identity.<linkerd-namespace>.<identity-trust-domain>

web-service.my-app.serviceaccount.identity.linkerd.cluster.local
```

同じServiceAccountの複数PodはIDを共有し、ローカル認証情報は各自が持ちます。identity trust domainは設定可能な概念で、変更したKubernetes DNS suffixと必ずしも同じではありません。

元のspiffe://root.linkerd.cluster.local/ns/.../sa/...はデフォルト形式ではありません。SPIFFE/SPIRE IDは別の[外部ワークロード・メッシュ拡張経路](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/)で対応します。Kubernetes TokenReviewをそのID/bootstrapモデルに置換しないでください。

### 更新とローテーション

proxy release/v2.368.0のidentity clientは通常、設定最小/最大更新間隔で制限し、**残存**有効期間の70%時点に次の証明書試行を予定します。error/期限切れ経路は最小遅延を使う場合があります。全証明書の固定時刻保証ではありません。

clientは更新要求時に読込済み鍵/CSRを再利用します。証明書更新と秘密鍵、issuer、trust anchorのrotationは同じではありません。

```bash
set -euo pipefail
kubectl -n linkerd get configmap linkerd-identity-trust-roots \
  -o jsonpath='{.data.ca-bundle\.crt}' > trust-bundle.pem
openssl crl2pkcs7 -nocrl -certfile trust-bundle.pem |
  openssl pkcs7 -print_certs -text -noout
kubectl -n linkerd get secret linkerd-identity-issuer -o json |
  jq -er '.data["crt.pem"] // .data["tls.crt"]' |
  base64 -d | openssl x509 -noout -dates
```

完全なtrust anchor移行には複数段階があります。

1. 現有効root、issuer、全consumer、導入/PKI所有者を棚卸し。
2. 所有者設定で旧rootと並べ新rootを追加。対象proxy/control planeとmulticluster peerが重複bundleを実読込することを確認。
3. 新root署名のissuerへrotationし、identityが読込したことを確認。
4. 設定ソースに応じconsumerを更新/再作成し、実新認証情報と対象経路mTLSを確認。
5. 必要peerが旧rootに依存しなくなってから削除し、最終bundleを伝播・再検証。

旧ConfigMap更新と1名前空間再起動はissuer移行と旧root除去の前で終わり、完全rotationではありませんでした。Helm/cert-manager/trust-managerと競合する直接変更を避けます。期限切れrootには通常の有効root切り替えでなく復旧手順が必要です。

```bash
linkerd check
linkerd check --proxy
kubectl -n linkerd get events --field-selector reason=IssuerUpdated
# Inspect each affected namespace/workload and its actual proxy version/identity.
kubectl -n my-app get pods -o wide
```

IssuerUpdatedは1観測で、全proxy/remote cluster移行の証明ではありません。cert-managerはissuer更新、trust-managerはbundle配布を自動化できますが、root切り替えは協調検証が必要です。実PKI設計の[手動](https://linkerd.io/docs/tasks/manually-rotating-control-plane-tls-credentials/)または[管理された認証情報手順](https://linkerd.io/docs/tasks/automatically-rotating-control-plane-tls-credentials/)に従います。この章はrotationを実行していません。

## サイドカー注入の詳細

![Pod作成前にnamespace意図、Podテンプレート上書き、適格性を組み合わせて判断する。アノテーションは全Pod注入の保証ではない。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-8.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-8.html)

controller workloadではPodテンプレートアノテーションと結果Podを確認します。1 YAML map内のmetadata重複キーは上書き/競合するため、namespace/workload例は別リソース/断片として保持します。

先のresource/logアノテーションは意図するrequests/limitsとlog設定で、実消費測定ではありません。opaque-port上書きはDBポート2つを追加するだけでなくデフォルトリストを置換するため、必要port全部を保持します。skip-portは意図的にメッシュ処理から外します。

## コンポーネント間通信

![検出、ID検証、policy、admissionという一部制御通信の役割。現デフォルトはEndpointSliceとTokenReviewを使い、ポート表はopaque TCPも含む。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-9.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-9.html)

| コンポーネント/経路 | 既定ポート | プロトコル/目的 |
|---|---|---|
| Destination Service | 8086 | 検出/profileのstreaming gRPC |
| Identity Service | 8080 | 証明書API gRPC |
| Policy Service | 8090 | Policy gRPC |
| Proxy Injector | Service 443 → Pod 8443 | HTTPS admission webhook |
| Proxy inbound | 4143 | HTTP/gRPC/opaqueを含む捕捉TCP |
| Proxy outbound | 4140 | 捕捉送信TCP |
| Proxy admin | 4191 | HTTPメトリクスとhealth |

ポートは設定可能で、一律ネットワーク許可ではありません。adminはEnvoy型routing設定インターフェースではなく、policy/設定はcontrol-plane APIで届きます。

## Istioアーキテクチャとの比較

| 観点 | Linkerd | Istio |
|---|---|---|
| 制御の配置 | この版では中核3 Deployment内に複数論理controller | 主要制御は統一Istiod、加えてmode固有component |
| データプレーン | 専用Rust proxy | Envoy sidecarまたはambient ztunnelと選択waypoint |
| 設定 | Linkerd streaming gRPC APIと対応resource | Envoy xDSと対応Istio/Gateway API設定 |
| 拡張 | 対応Linkerd機能/API範囲を確認 | mode/版固有Envoy/Wasm/Luaと接続を確認 |
| リソース/性能比較 | 同等workloadと実設定で測定 | 同等workloadと実設定で測定 |

xDSも通常gRPCを使い、プロトコル名は本質的複雑さの順位ではありません。CRD数は版/拡張で変わり、runtime負荷を測りません。requests/limitsは設定予約/上限で、観測メモリ/遅延ではありません。同じworkload、通信、protocol、policy、障害予算を比較して選びます。[保守されている比較](../istio/comparison/README.md)を参照してください。

## 次のステップと出典

- [トラフィック管理](03-traffic-management.md)、[セキュリティ](04-security.md)、[可観測性](05-observability.md)
- [アーキテクチャクイズ](../../quizzes/service-mesh/linkerd/architecture.md)
- [公式アーキテクチャ](https://linkerd.io/docs/reference/architecture/)、[注入](https://linkerd.io/docs/features/proxy-injection/)、[policy参照](https://linkerd.io/docs/reference/authorization-policy/)
- [自動mTLS](https://linkerd.io/docs/features/automatic-mtls/)、[プロトコル処理](https://linkerd.io/docs/features/protocol-detection/)、[負荷分散](https://linkerd.io/docs/features/load-balancing/)
- [固定Destination API](https://github.com/linkerd/linkerd2-proxy-api/blob/v0.20.0/proto/destination.proto)
- [Kubernetes token検証](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/controller/identity/validator.go)と[ID形式](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/controller/identity/domain.go)
- [固定証明書更新実装](https://github.com/linkerd/linkerd2-proxy/blob/a66af8117769df060adda6233302a2d1c4142229/linkerd/proxy/identity-client/src/certify.rs)
