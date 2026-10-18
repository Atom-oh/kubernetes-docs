# Linkerd アーキテクチャ

> **最終更新**: 2026年10月16日 · Linkerd edge-26.10.1 / proxy release/v2.370.0

この章では、現在のコンポーネントの役割、ID階層、トラフィックの捕捉と注入のライフサイクルを説明します。対応するリリースとクラスターの組み合わせ、および固定バージョンの成果物は[インストールガイド](01-installation.md)を参照してください。以下の例は設定を示すもので、この監査では実際のデプロイやCAローテーションを行っていません。

## 全体アーキテクチャ

![Linkerdの中核となる3つのDeploymentと、メッシュに参加する2つのピアを示す簡略図。policy controllerはDestinationとともに動作するため別個には描かず、一部の接続だけを示しています。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-0.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-0.html)

デフォルトのコントロールプレーン名前空間は `linkerd` です。固定したチャートに含まれる中核のDeploymentは、`linkerd-destination`、`linkerd-identity`、`linkerd-proxy-injector` の3つです。DestinationにはpolicyとServiceProfile-validatorの各コンテナも含まれます。論理上のcontrollerの役割と、独立したDeploymentは同じではありません。任意のVizおよびmulticlusterコンポーネントには、それぞれ独自のライフサイクルがあります。

データプレーンは、メッシュに参加したアプリケーションと並んで動作するRust製プロキシを使用します。このリリースではnative sidecarがデフォルトです。Identity Deploymentでは意図的に通常のproxyを使い、startup waitを無効にしています。そのため、状態を調べるときは `containers` と `initContainers` の両方を確認してください。

## コントロールプレーン

### Destination Controller

Destinationはサービス検出の状態を監視し、ストリーミングAPIを通じてエンドポイントアドレス、期待されるID、profile情報を提供します。現在のデフォルトではEndpointSliceを使います。ServiceProfileは従来の設定方法として残っています。Gateway APIのルーティングと認可にはpolicy controllerも関与します。現在のLinkerdルーティングをSMI TrafficSplitだけで説明したり、Destinationがその旧拡張リソースを直接監視すると想定したりしないでください。

| 責務 | 意味 |
|---|---|
| 検出 | 要求されたServiceのエンドポイント追加・削除とメタデータ |
| 期待されるID | 送信側proxyが選択したピアを認証するための情報 |
| Profile | メトリクス、再試行、タイムアウト用にサポートされるルート/profile設定 |
| 負荷分散の入力 | エンドポイントと設定された重み。実行時の遅延観測と要求・接続の選択はproxyが行う |

以下はGoソースではなく、**Protocol Buffersのサービス定義の抜粋**です。メッセージ定義とimportは、固定バージョンのproxy APIにあります。

```protobuf
// Excerpt: message definitions/imports are in the linked API source.
service Destination {
  rpc Get(GetDestination) returns (stream Update) {}
  rpc GetProfile(GetDestination) returns (stream DestinationProfile) {}
}
```

`Get` はDestinationの更新をストリーム配信し、`GetProfile` はprofileの更新をストリーム配信します。ストリームもローカルキャッシュも設定変更を即時反映させるものではなく、利用できないエンドポイントへの対処も不要にはなりません。

### Identity Controller

デフォルトのKubernetes IDフローは次のとおりです。

1. Proxyの起動時に、ローカルの秘密鍵とCSRの素材を用意します。
2. Identity clientがCSR、要求するID、ServiceAccount tokenを送信します。
3. IdentityがKubernetes TokenReviewでtokenを検証し、DNS形式のIDを導出します。
4. 設定された**issuer署名認証情報**（通常は中間issuer）がworkload証明書に署名します。
5. Clientが返された証明書とチェーンを読み込み、有効期限前に更新します。

Trust anchorは証明書チェーン検証の基盤です。その秘密鍵はLinkerdのIdentity controllerには必要ありません。root CAがすべてのworkload CSRにオンライン署名するわけではありません。

以下はインストールを管理する担当者向けの**Helm values設定断片**です。

```yaml
identity:
  issuer:
    issuanceLifetime: 24h0m0s
    clockSkewAllowance: 20s
    scheme: linkerd.io/tls
```

`linkerd.io/tls` がデフォルトのissuer schemeです。`kubernetes.io/tls` との統合では、外部管理するSecretに対応した形式を使います。認証情報の所有者と鍵を合わせずにschemeを変更しないでください。また、一部だけのidentity ConfigMapで `linkerd-config` のvalues全体を上書きしないでください。

### Proxy Injector

![Linkerd CNIを使わない適格なPodに対するadmissionフローの概念図。API serverがinjectorによる変更を適用し、native proxyの配置と除外条件は本文で説明しています。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-3.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-3.html)

Injectorはmutating admission webhookです。その応答はAPI serverが適用する変更を記述します。この図は概念図であり、wire形式の例ではありません。実際のwebhookの選択、Podによる上書き、プラットフォームの適格性も引き続き影響します。

選択した名前空間を有効にします。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

Deploymentでは、上書き設定を**Pod template**に記述します。以下は既存のworkload定義の中に置く設定断片です。

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

`enabled|disabled` という値ではなく、`enabled` または `disabled` のどちらか1つをそのまま指定します。Annotationを追加しても既存Podは変更されません。導入済みwebhookは指定されたシステム名前空間を除外し、明示的なPod上書きによって、通常なら有効な注入を無効にすることもできます。

| 注入・設定される項目 | 役割 |
|---|---|
| linkerd-init | Linkerd CNIを使わない場合にPodネットワークを捕捉するための設定 |
| linkerd-proxy | データプレーンproxy。このリリースでは通常、再起動可能なinit containerとして動作 |
| 投影されたidentity tokenとローカルidentity保存領域 | Bootstrapとworkload証明書に使用。Proxyの鍵は共有workload Secretとして配布されない |
| 環境変数・probe・リソース | 注入で生成される、バージョン固有の実行時設定 |

### Policy Controller

Policyは受信トラフィックの認可と、サポート対象の送信・要求ルーティング動作を制御します。この例は `app:web` ラベルと `http` という名前付きportを宣言したPodを選択し、`my-app` 名前空間のメッシュに参加した `api-gateway` ServiceAccountを認可します。

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

Serverは既存のPodとportの組み合わせを選択します。アプリケーション、Service、listenerを作成するものではありません。指定する名前付きportは実在する必要があります。適用されるpolicyか、明示的に選択した別のアクセスpolicyで許可されない限り、選択されたトラフィックはデフォルトで拒否されます。強制適用する前に、policyの対象範囲を段階的に適用してテストしてください。

AuthorizationPolicyはServerまたはサポート対象のrouteを対象にできます。ServiceAccount参照は便利な認証要件です。MeshTLSAuthenticationとNetworkAuthenticationを使うと、追加のIDやネットワーク集合を表現できます。1つのpolicy内に指定した必須認証参照はすべて一致する必要があります。トラフィックを許可できる他のpolicyも確認してください。

既存のServerAuthorization手順を使う場合は、次の設定がサポートされた**代替手段**です。直前の認可設定と併せて追加する要件ではありません。

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

リリースに含まれるCRDが提供するServerAuthorizationのAPIは `v1beta1` であり、元の例にある `v1beta2` ではありません。Serverの `v1beta2` は引き続き提供され、この例では現在の保存バージョンである `v1beta3` を使います。より柔軟なAuthorizationPolicyが推奨インターフェイスです。異なるAPI groupにあるIstioの同名リソースと、これらのLinkerdリソースを混同しないでください。

## データプレーン

### Proxyの動作とプロトコルの範囲

`linkerd2-proxy` はRustで実装された、メッシュ専用のproxyです。HTTP/1.1、HTTP/2、gRPC、TCPをサポートします。HTTPレベルのルーティングとメトリクスには、内容を認識できるHTTP通信が必要です。アプリケーションが開始するTLS通信の内容はproxyから見えず、UDP/QUICや捕捉をskipした通信はTCP proxy経路の対象外です。

メッシュに参加した通信可能なTCPピア間では、Linkerdが転送層のmTLSを提供します。文書化されたメッシュ転送ではTLS 1.3を使います。アプリケーションが開始するTLSのパススルーは別の層です。メッシュに参加していないピアと、明示的に捕捉を迂回する通信は、別途考慮する必要があります。デフォルトの受信policyは、メッシュに参加していない相手からの平文通信を受け入れます。自動mTLSは、すべての送信元に対して認証を必須にすることと同じではありません。

ProxyはHTTP要求を遅延を考慮して負荷分散し、内容が見えないTCP通信は接続単位で負荷分散します。エンドポイントの重みやルーティング規則と、実行時に推定する遅延は別の情報です。EWMAを、すべての要求が決定論的に最速の単一エンドポイントへ送られる保証と解釈しないでください。

メモリ10MB未満、p99が1ms未満、またはバイナリサイズが一定であるという普遍的な保証はありません。測定値はバージョンとbuild、アーキテクチャ、接続数、policyと設定、workload、計測方法によって異なります。

### Proxyのトラフィックフロー

![新しいメッシュ接続上でのHTTP要求。送信側proxyが宛先を検出して選択し、両proxyがmTLSを確立した後、受信側policyを通過してアプリケーションに届きます。既存の接続を再利用する場合もあります。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-5.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-5.html)

送信側の検出、ルーティングと負荷分散、再試行、タイムアウトは、受信側の認可とは異なる処理です。新しい接続では宛先の検出とmTLSの確立が行われます。既存の接続とキャッシュ済み設定が再利用される場合もあります。安全に要求を再試行できるかはアプリケーションとプロトコルによって判断してください。特に書き込み要求では注意が必要です。

### トラフィックの捕捉: linkerd-initまたはCNI

生成されたproxy-initまたはLinkerd CNIの設定を使用してください。以下は概念上の順序であり、**ホスト上で実行するiptablesコマンドではありません**。

```text
Inside the Pod network namespace:
  outbound TCP -> evaluate proxy-UID and configured bypass rules first
               -> redirect intercepted traffic to the outbound proxy (default 4140)
  inbound TCP  -> evaluate configured bypass rules
               -> redirect intercepted traffic to the inbound proxy (default 4143)

Linkerd CNI: installs the Linkerd-specific capture setup through the CNI chain.
linkerd-init: performs the setup at Pod startup when Linkerd CNI is not used.
```

以前の例では、全TCP通信をREDIRECTするルールより後にproxy UIDの迂回ルールを追加していました。この順序ではproxy自身の送信トラフィックを保護できません。また、これらのルールをホスト名前空間に適用しても、Podごとに設定するLinkerdの手順にはなりません。実際の実装には追加の除外設定やchainがあり、設定されたiptablesモードにも対応します。

Opaque portはプロトコル検出をskipしますが、proxyによる転送処理は維持します。Skip portはproxyとメッシュ機能を迂回します。サーバーが先に送信を開始する通信では、正しいopaque/protocol設定の代わりにskipを使用しないでください。

### Proxyを手作業で組み立てず、生成されたPodを確認する

以前の手作業によるPod例は、identity/bootstrapの素材が不足しており、上流に存在しない `stable-2.16.0` イメージを前提としていました。選択したCLIと導入済みコントロールプレーンの設定で、構成を生成するか確認してください。

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

デフォルトのinject modeはAnnotationの変換です。edge-26.9.1では手動生成でも既存の入力設定Annotationを読み取ります。実際に観測されたケースでは、CPU request `700m` のAnnotationがCLI flagの `100m` より優先され、入力されたlog-level Annotationも適用されました。競合する入力を更新または削除し、生成結果のproxyフィールドを確認してください。手動で生成したproxyは、後からAnnotationを編集しても自動再生成されません。短縮したcontainer定義を完全なインストール設定としてコピーせず、所有するリソースを通して生成workloadを更新してください。

```bash
: "${APP_POD:?Set an application Pod name in my-app}"
kubectl -n my-app get pod "$APP_POD" -o json |
  jq '{pod: .metadata.name, proxies: ([.spec.containers[]?, .spec.initContainers[]?] | map(select(.name == "linkerd-proxy") | {image, restartPolicy, resources, startupProbe, readinessProbe, livenessProbe}))}'
```

Native sidecarは `restartPolicy: Always` を指定した `initContainers` に現れます。設定でCNIを使う経路を選ぶと `linkerd-init` は省略されます。Proxyのhealth endpointは、設定されたadmin port（デフォルト `4191`）の `/live` と `/ready` です。Native sidecarのstartup/readinessとアプリケーションのreadinessは別々に確認してください。

## 証明書の階層

| 素材 | デフォルトの役割・保存場所 |
|---|---|
| Trust anchor証明書・bundle | 公開された信頼の基点。`linkerd-identity-trust-roots` ConfigMapの `ca-bundle.crt` |
| Root CA秘密鍵 | PKI所有者が管理する素材。Linkerdの実行には不要 |
| Issuer証明書・秘密鍵 | `linkerd-identity-issuer` Secret。デフォルト形式では `crt.pem` と `key.pem` |
| Kubernetes TLS issuer統合 | `tls.crt` と `tls.key` およびそれらに合うschemeを使う、意図的に設定する代替方式 |
| Workloadの鍵・証明書 | Proxy内に保存される認証情報。有効期間は公称24時間で、自動更新される |

Issuerとtrust anchorの有効期間は、設定されたPKIによって異なります。CLIで生成するデフォルトのrootとissuerの有効期間は1年です。独自に設定した10年の例は、デフォルトでも普遍的な推奨値でもありません。固定の例示日時をコピーせず、実際の証明書の日付を確認してください。

### Kubernetes workload identity

デフォルトのKubernetes ID機構では、IDはDNS形式です。

```text
<service-account>.<namespace>.serviceaccount.identity.<linkerd-namespace>.<identity-trust-domain>

web-service.my-app.serviceaccount.identity.linkerd.cluster.local
```

同じServiceAccountを使うPodはIDを共有しますが、それぞれが独自のローカル認証情報を持ちます。Identity trust domainは設定可能な概念であり、変更後のKubernetes DNS suffixと必ず同一とは限りません。

元の `spiffe://root.linkerd.cluster.local/ns/.../sa/...` という文字列は、デフォルトのKubernetes ID形式ではありません。SPIFFE/SPIRE形式のIDは、独立した[外部workloadをメッシュに追加する経路](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/)でサポートされます。Kubernetes TokenReviewの代わりに、そのID/bootstrap方式を使わないでください。

### 更新とローテーション

Proxy release/v2.370.0では、Identity clientは通常、設定された更新間隔の最小値と最大値に収まるよう調整したうえで、**残りの**有効期間の70%が経過した時点に次の証明書取得を試みるよう予定します。エラー時や期限切れの場合は最小遅延が使われることがあります。すべての証明書に対して固定された時刻を保証するものではありません。

このclientは証明書の更新を要求する際、読み込み済みの鍵とCSRのdocumentを再利用します。証明書の更新は、秘密鍵、issuer、trust anchorのローテーションとは異なります。

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

Trust anchorを完全に移行するには、複数の段階が必要です。

1. 現在有効なroot、issuer、すべての利用者、インストールおよびPKIの管理者を洗い出します。
2. 管理者の設定を通して、新しいrootを古いrootと併せて追加します。対象のproxyとコントロールプレーンコンポーネント、およびmulticluster peerが、両方を含むbundleを実際に読み込んだことを確認してください。
3. 新しいrootで署名された認証情報にissuerを切り替え、Identity serviceがそれを読み込んだことを確認します。
4. 設定の管理元に応じて利用者を更新または再作成し、新しい認証情報と対象経路上のmTLS通信を実際に確認します。
5. 必要なpeerが古いrootに依存しなくなってから古いrootを削除し、最終bundleを配布して再確認します。

以前のConfigMap更新と、1つの名前空間の再起動だけでは、issuerの切り替えと古いrootの削除まで行っておらず、完全なローテーション手順ではありません。Helm/cert-manager/trust-managerの管理と競合する直接変更は避けてください。すでに期限切れのrootには、有効なrootの通常の切り替えではなく、復旧手順が必要です。

```bash
linkerd check
linkerd check --proxy
kubectl -n linkerd get events --field-selector reason=IssuerUpdated
# Inspect each affected namespace/workload and its actual proxy version/identity.
kubectl -n my-app get pods -o wide
```

`IssuerUpdated` eventは観測情報の1つであり、すべてのproxyやリモートクラスターで移行が完了した証明ではありません。cert-managerはissuerの更新を自動化でき、trust-managerはbundleを配布できますが、rootの切り替えには関係する対象を調整した検証が必要です。実際のPKI設計に応じて、[手動の手順](https://linkerd.io/docs/tasks/manually-rotating-control-plane-tls-credentials/)または[認証情報を管理する手順](https://linkerd.io/docs/tasks/automatically-rotating-control-plane-tls-credentials/)に従ってください。この章ではローテーションを実施していません。

## Sidecar注入の詳細

![Namespaceの意図、Pod templateの上書き、適格性に基づきPod作成前に注入を判断します。Annotationを設定しても、すべてのPodへの注入が保証されるわけではありません。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-8.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-8.html)

Controllerが管理するworkloadでは、Pod templateのAnnotationを使用し、作成されたPodを確認してください。1つのYAML mappingで同じmetadata keyを重複させると、片方が上書きされるか競合します。Namespaceとworkloadの例は、別々のリソースまたは設定断片として記述してください。

前述のresource/log Annotationが指定するのは、意図するproxyのrequest/limitとlog設定であり、実際の消費量の測定値ではありません。Opaque portの上書きは、database portを2つ追加するだけではなく、デフォルトのport一覧を置き換えます。必要なportをすべて残してください。Skip portの上書きは、対象トラフィックを意図的にメッシュ処理から除外します。

## コンポーネント間の通信

![検出、Identity検証、policy、admissionに関する、一部のコントロールプレーン通信を示します。現在のデフォルトではEndpointSliceとTokenReviewを使い、port表はopaque TCPも扱います。](../../.gitbook/assets/en-service-mesh-linkerd-02-architecture-9.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-02-architecture-9.html)

| コンポーネント・経路 | デフォルトport | プロトコル・用途 |
|---|---|---|
| Destination Service | 8086 | 検出/profile情報を配信するstreaming gRPC |
| Identity Service | 8080 | 証明書APIのgRPC |
| Policy Service | 8090 | Policy用gRPC |
| Proxy Injector | Service 443 → Pod 8443 | HTTPS admission webhook |
| Proxy inbound | 4143 | HTTP/gRPCまたはopaque通信を含む、捕捉されたTCP |
| Proxy outbound | 4140 | 捕捉された送信TCP |
| Proxy admin | 4191 | HTTPメトリクスとhealth endpoint |

これらのportは変更でき、一律にネットワークアクセスを許可するための規則ではありません。Admin endpointはEnvoyのようなルーティング設定インターフェイスではありません。Policyと設定はコントロールプレーンAPIを通じて配信されます。

## Istioアーキテクチャとの比較

| 観点 | Linkerd | Istio |
|---|---|---|
| コントロールプレーンの構成 | このリリースでは中核となる3つのDeploymentに複数の論理controllerを配置 | 主要な制御機能を統合したIstiodと、モード別のコンポーネント |
| データプレーン | メッシュ専用のRust proxy | Envoy sidecar、または選択したwaypointとambient ztunnel |
| 設定 | LinkerdのストリーミングgRPC APIとサポート対象resource | Envoy用xDS、およびサポート対象のIstio/Gateway API設定 |
| 拡張 | サポート対象のLinkerd機能/APIの範囲を確認 | モードとバージョンごとのEnvoy/Wasm/Lua対応、および接続方法を確認 |
| リソース・性能の比較 | 条件を揃えたworkloadと実設定を測定 | 条件を揃えたworkloadと実設定を測定 |

xDSも一般にgRPCを使います。プロトコル名だけで本質的な複雑さの優劣は決まりません。CRDの数はバージョンや拡張によって変わり、実行時のオーバーヘッドを示す指標ではありません。Requests/limitsは設定された予約値や上限であり、観測されたメモリ使用量や遅延ではありません。製品を選ぶ前に、同じworkload、トラフィック、プロトコル、policy、障害時の許容条件を比較してください。[保守されている比較資料](../istio/comparison/README.md)も参照してください。

## 次のステップと出典

- [トラフィック管理](03-traffic-management.md)、[セキュリティ](04-security.md)、[可観測性](05-observability.md)
- [アーキテクチャクイズ](../../quizzes/service-mesh/linkerd/architecture.md)
- [公式アーキテクチャ](https://linkerd.io/docs/reference/architecture/)、[proxy注入](https://linkerd.io/docs/features/proxy-injection/)、[policyリファレンス](https://linkerd.io/docs/reference/authorization-policy/)
- [自動mTLS](https://linkerd.io/docs/features/automatic-mtls/)、[プロトコル処理](https://linkerd.io/docs/features/protocol-detection/)、[負荷分散](https://linkerd.io/docs/features/load-balancing/)
- [固定バージョンのDestination API](https://github.com/linkerd/linkerd2-proxy-api/blob/v0.20.0/proto/destination.proto)
- [Kubernetes token検証](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/controller/identity/validator.go)と[ID形式](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/controller/identity/domain.go)
- [固定バージョンの証明書更新実装](https://github.com/linkerd/linkerd2-proxy/blob/0cdcc078e66eb27c79b9dfc030fc660042716d31/linkerd/proxy/identity-client/src/certify.rs)
