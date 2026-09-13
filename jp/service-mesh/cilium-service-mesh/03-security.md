# Ciliumサービスメッシュのセキュリティ

> **最終更新**: September 11, 2026 · Cilium/chart 1.20.1 · 同梱SPIRE 1.15.2。テスト済みKubernetes/EKS版とプラットフォーム要件は[概要](./README.md)を参照してください。

## 概要

ワークロード認可、ピア認証、アプリデータ暗号化という3つの別制御を評価します。Ciliumの帯域外相互認証、WireGuard/IPsec転送暗号化、別のztunnel mTLSベータは要件と制限が異なります。

以下のポリシー例は通常のCiliumポリシー/帯域外認証経路です。**ztunnel暗号化を有効にしたときも同じL4適用が維持されると想定しないでください**。ベータの制限は後述します。

## セキュリティアーキテクチャ

![ID/ポリシー、帯域外認証、任意の暗号化選択肢の論理的分離。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-0.html)

ボックスは責務をまとめ、全組み合わせが全ポリシーを保持すると認定するものではありません。特にztunnelベータは別のID/データ経路を使い、デフォルトCAは帯域外認証で示すSPIRE統合を必要としません。

## 相互認証とデータ暗号化

### 従来のCilium相互認証

帯域外方式はCilium 1.20.1でも**ベータ/未完成**と文書化されています。CiliumエージェントはSPIRE提供SVIDでCiliumセキュリティIDを認証します。ネットワークポリシールールが認証を要求しても、アプリ接続自体がTLSになるわけではありません。

![ポリシーで保護された通信を進める前の、エージェント間帯域外認証交換の例。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-1.html)

認証記録はID関係についてキャッシュされます。図はHTTP要求ごと、あるいは必ずアプリ接続ごとに新証明書/ハンドシェイクを作る意味ではありません。認証要件に加え明示的な認可ルールも適用します。

### ztunnelによるネイティブmTLS（2026年更新）

Cilium 1.20.1には **Ztunnel Transparent Encryption（ベータ）** があります。必要なブートストラップ/CA素材を準備してから、次のモード断片で選択します。

```yaml
encryption:
  enabled: true
  type: ztunnel
  ztunnel:
    ca:
      type: internal
```

リリースのデフォルトはCilium内部CAオプションです。`cilium-ztunnel-secrets` Secretが`bootstrap-private.key`、`bootstrap-root.crt`、`ca-private.key`、`ca-root.crt`を提供します。公式生成スクリプトは例で、完全な本番PKI/ローテーション設計ではありません。チャートの`bootstrapRootCert`単体は公開証明書だけを提供し、内部CAに必要な秘密鍵は生成しません。

Ciliumエージェントは参加Podのネットワーク名前空間にiptablesリダイレクトを設定し、ノードのztunnelへワークロード状態を送り、制御/証明書インターフェースを提供します。チャートは`ztunnel-cilium` DaemonSetを作成します。名前空間参加には`io.cilium/mtls-enabled=true`を使い、モードをインストールするだけでは全名前空間は参加しません。

リリースガイドは次の境界を定めています。

- 送信元と宛先の両ワークロードが参加する必要があり、参加済みと未参加間の通信は非対応。
- 参加は名前空間単位で、Podごとの参加は非対応。ホストネットワークPodは参加不可。
- mTLSへリダイレクトするのはTCPだけで、UDPや他プロトコルはこの暗号化経路外。
- ClusterMeshは非対応で、カーネルは必要なiptables操作に対応している必要がある。
- 暗号化はパケットがPodを出る前に行われる。そのためHBONEポート15008を直接対象とする場合を除き、通常L4ポリシーはこの経路で動作しない。

この統合は名前空間/サービスアカウントのワークロードIDモデルを使います。帯域外認証の数値`/identity/<id>` SPIFFEパスとは異なります。

準備したテストインストールの読み取り専用確認例:

```bash
kubectl -n kube-system get daemonset ztunnel-cilium
kubectl get namespaces -l io.cilium/mtls-enabled=true
kubectl -n kube-system get configmap cilium-config -o yaml
```

名前空間ラベル、正常プロキシ、15008上のパケットだけでは期待する全通信の暗号化/認可は証明されません。参加成功、選択経路の両端、証明書ID/信頼、非対応通信を確認します。

### mTLSにCiliumとIstioのどちらを選ぶか

必要なID、認可、通信範囲で選択します。既存CiliumではIDポリシーとWireGuard/IPsecを使うか、制限内で別のztunnelベータを評価できます。実際に有効にする追加プロキシ、CA、運用依存関係を考慮します。

Istioはサイドカー/ambientでワークロードプロキシmTLSを提供し、それぞれ機能/プラットフォーム境界があります。`PeerAuthentication`の`STRICT`は受信mTLS要件で、単体ではID発行、プロキシ導入、全呼び出し元認可をしません。比較を暗号化スイッチ1つに還元しないでください。[サイドカー/ambientの章](../istio/comparison/03-sidecar-vs-ambient.md)は実測版とシナリオを保持しています。

### SPIREベース相互認証の設定

**帯域外**認証には、レビュー済みインストールvaluesへこのオーバーレイをマージします。

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      trustDomain: spiffe.cilium
      agentSocketPath: /run/spire/sockets/agent/agent.sock
      install:
        enabled: true
        server:
          dataStorage:
            enabled: true
            size: 1Gi
```

SPIRE StatefulSetに適切なStorageClass/PVを準備します。`gp3`クラスが全EKSに自動存在するわけではありません。`authentication.enabled`は必須です。trust domainとagent socket設定は`install.server`や`install.agent`下でなく`authentication.mutual.spire`下です。同梱チャートは旧`server.replicas`、`server.nodeAttestor`、`agent.workloadAttestor`、`server.ca.ttl`例を実装しません。

SPIRE Serverはエージェントを検証しSVIDに署名します。エージェントはワークロードを検証します。Cilium統合はさらに取得を委任し、CiliumセキュリティIDのエントリを登録します。SPIREを有効にするだけでは全通信への認証適用もWireGuard/IPsec有効化もしません。

### 相互認証ポリシーの適用

`authentication`は**Ingress/Egress許可ルール内のオブジェクト**です。配列でも最上位`spec.authentication`スイッチでもありません。このクラスター範囲ポリシーは意図的に1アプリ/名前空間を選びます。

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: production-backend-auth
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

### 名前空間ごとの相互認証

この名前空間単位の例は`production`のワークロードを選び、その名前空間の認証済みピアをTCP 8080で許可します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: namespace-auth
  namespace: production
spec:
  endpointSelector: {}
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

同一名前空間許可の例で、全アプリの最小権限ではありません。他ポート、クライアント、プローブ、既存ポリシー許可は別評価です。Ingressに影響し、完全なEgress依存ポリシーを暗黙に設定しません。

### サービスごとの相互認証

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: service-auth
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

送信元/宛先ラベルはワークロードを記述し、エンドユーザーのログインではありません。ワークロード作成、ラベル変更、サービスアカウント使用を誰ができるか、Kubernetes権限で制御する必要があります。

## CiliumNetworkPolicyのL7ルール

### HTTP L7セキュリティポリシー

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-security-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:role: reader
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/.*$
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:role: admin
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^(GET|POST|PUT|PATCH|DELETE)$
          path: ^/api/.*$
          headers:
          - Authorization
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: monitoring
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/health$
        - method: ^GET$
          path: ^/metrics$
```

ルール内のHTTPルールは選択肢です。`headers: [Authorization]`は存在だけを要求し、bearer token、署名、期限、権限は検証しません。旧`Authorization: Bearer .*`文字列はJWT検証器でも汎用正規表現の値一致でもありません。アプリ認証/認可を独立して行います。

HTTPパスポリシーには対応する検査可能L7経路が必要です。アプリTLS、プローブ、他依存通信には関連設定が必要で、ポート番号だけではTLSは有効になりません。

### Kafka L7セキュリティポリシー

旧`rules.kafka`オブジェクトはCilium 1.20.1 L7スキーマで拒否されます。以下の置換は**ネットワーク到達性だけ**を制限します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-network-boundary
  namespace: kafka
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: kafka
      k8s:app: kafka
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kafka
        k8s:role: producer
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kafka
        k8s:role: consumer
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

produce/fetch、トピック、コンシューマーグループ用に、実KafkaリスナーのTLS/SASLとブローカーACLを設定します。古いL7ルール削除後にはL4アクセスが残り、トピック単位認可は維持されません。

### DNS L7セキュリティポリシー

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-security
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: web-application
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*.*.svc.cluster.local'
        - matchName: api.stripe.com
        - matchName: sts.us-east-1.amazonaws.com
  - toFQDNs:
    - matchName: api.stripe.com
    - matchName: sts.us-east-1.amazonaws.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

例は`kube-system`の`k8s-app=kube-dns`ラベル付きCoreDNSと通常の`cluster.local` DNSサフィックスを前提とします。UDP/TCP両方のDNSを許可します。Service FQDNはserviceとnamespace両ラベルを含むため、`*.*.svc.cluster.local`は旧`*.svc.cluster.local`と異なります。

外部HTTPS許可はDNSクエリ許可と別です。`sts.us-east-1.amazonaws.com`は特定リージョンのAWSエンドポイントです。AWSは旧`api.aws.amazon.com`を汎用APIエンドポイントとして使いません。該当IPv6/デュアルスタック/プライベート版も含め、実SDKのリージョン/サービスエンドポイントを選びます。内部DNS応答は全内部Serviceへの接続を自動許可しません。

リゾルバー検索リストと、有効ならNodeLocal DNS動作を確認します。広いS3ワイルドカードは意図した1バケット以外も許し得ます。DNS/IPポリシーは許可先経由の持ち出し防止を保証しません。

## 相互認証

### 認証モード

| モード | 帯域外ポリシーAPIでの意味 |
|---|---|
| `required` | 一致する許可通信に認証成功を要求 |
| `disabled` | 一致ルールに対する明示的認証免除 |
| `test-always-fail` | 意図的に認証失敗させるテストモード |

リリーススキーマに`optional`はありません。他ルールが重なる場合、明示要件がないことと慎重に範囲を限定した免除は異なります。認証ルールが通常の独立Allowと同じと想定せず、結果ポリシーを確認します。

### 相互認証ポリシー例

免除は明示的かつ狭い範囲とし、理由を示すべきです。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: authentication-exception
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: secure-service
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: trusted-client
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
    authentication:
      mode: required
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        k8s:app: prometheus
    toPorts:
    - ports:
      - port: '9090'
        protocol: TCP
    authentication:
      mode: disabled
```

Prometheusルールは「可能なら認証」でなく**認証無効**です。指定監視ワークロードとポートだけを許可します。どちらかのアプリ待ち受けポートのTLSは別アプリ設定です。

### SPIFFE IDベースの認証

デフォルトの**帯域外**SPIRE trust domainでは、CiliumセキュリティIDは次の形式です。

```text
spiffe://spiffe.cilium/identity/<numeric-security-identity>
```

許可ピアはエンドポイント/IDポリシーで選択します。`authentication`に任意SPIFFE-ID許可リストフィールドはありません。コメントをIstio型`/ns/.../sa/...` URIに変えてもアクセスは制限されません。上述のztunnelベータは別のワークロードIDモデルです。

## 暗号化

### WireGuard透過暗号化

```yaml
encryption:
  enabled: true
  type: wireguard
```

Ciliumはノード鍵ペアを作り、CiliumNode情報で公開鍵を配布します。**異なるノード**のCilium管理Pod間の対応通信は暗号化されますが、同一ノード通信はされません。カーネルのWireGuard対応が必要です。チャートに`encryption.wireguard.userspaceFallback`はありません。

必要なノード間UDP 51871経路を許可し、MTU/カプセル化を考慮します。AWS VPC CNIチェイニングには、文書化された`cni.enableRouteMTUForCNIChaining`を含む追加MTU要件があります。無条件に適用せず、選択インストールモードに従います。

#### WireGuardアーキテクチャ

![Ciliumエージェントがノード間WireGuardを論理的に管理し、カーネルのWireGuardインターフェースが暗号化する。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-2.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-2.html)

Agentボックスは管理/鍵配布を表し、各パケットのユーザー空間中継ホップではありません。WireGuardインターフェース上のキャプチャでは平文の内側パケットが見える場合があります。暗号化評価では正しい外側ネットワーク経路を確認します。

ノード間の対象拡張は別のベータオプションです。

```yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: true
```

鍵更新のブートストラップ失敗を避けるため、デフォルトではコントロールプレーンノードをノード暗号化から除外します。リリースの通信表はXDPアクセラレーション、非Geneve DSR、Egress Gateway応答の除外も示します。外部要求のクライアント→クラスター区間はノードWireGuardでは暗号化されません。

### IPsec暗号化

```yaml
encryption:
  enabled: true
  type: ipsec
  ipsec:
    secretName: cilium-ipsec-keys
    keyFile: keys
    keyWatcher: true
    keyRotationDuration: 5m
```

SecretはCiliumの名前空間に存在する必要があります。文書化されたAES-GCM例の`keys`エントリは次の形式です。

```text
3+ rfc4106(gcm(aes)) <fresh-20-byte-random-value-in-hex> 128
```

`+`はトンネルごとに導出した鍵を選びます。`+`なしの旧グローバル鍵形式はセキュリティ上の理由で非推奨です。現行ガイダンスとしてコピーしないでください。サンプル鍵を再利用せず、文書化されたCLI/Secret手順で新しい鍵素材を生成・保護します。

`keyRotationDuration: 5m`は鍵変更後の移行/旧鍵削除猶予で、**5分ごとに新鍵を生成するスケジューラーではありません**。対応ローテーション手順で鍵IDと素材を更新し、ClusterMesh使用時は全クラスターを調整します。更新中にノード版が混在している間はローテーションしないでください。

ESP/ファイアウォール対応、実暗号化インターフェース、ネイティブルーティングCIDRを確認します。現IPsecはL7で文書化された透過DNSプロキシ動作を要求し、CNIチェイニングとホストポリシーは非対応で、同一ノード通信は暗号化しません。

### 暗号化の比較

| 項目 | WireGuard | IPsec | ztunnelベータ |
|---|---|---|---|
| 鍵/ID | ノード生成の鍵ペア | トンネル別導出を使う配布鍵素材 | ワークロードmTLS証明書とブートストラップ/CA素材 |
| データ経路 | カーネルWireGuardインターフェース | カーネルIPsec/XFRM | ノードごとのTLSプロキシとPod名前空間リダイレクト |
| 同一ノード/範囲 | 同一ノード通信は非暗号化。リリース通信表を使用 | 同一ノード通信は非暗号化。モード制限あり | 両端参加、TCPのみ、ポリシー制限あり |
| 暗号設定 | WireGuardのChaCha20-Poly1305スイート | AES-GCMなどカーネル対応の設定アルゴリズム | 対応プロキシがネゴシエートするTLS |
| 性能 | 実CPU、MTU、通信構成を測定 | アルゴリズム/ハードウェア、トンネル、単一トンネル復号制約を測定 | プロキシ、TLS、ワークロード負荷を測定。以前の比較ベンチマーク対象外 |

透過暗号化にも、許可された未知宛先を外部として扱うエンドポイント検出の期間があり得ます。Ciliumは緩和策として制限Egressと暗号化strictモードを文書化しますが、制限があります。strict EgressはIPv4/CIDR依存、strict IngressはWireGuardと管理インターフェースが必要でCNIチェイニング非対応です。「暗号化有効」を全経路のfail-closed保護の証明と解釈しないでください。

## IDベースのセキュリティ

### Cilium ID

CiliumはIDに関係するラベル集合に数値IDを割り当て、複数Podが共有できます。ユーザー計算のハッシュでも永久Pod識別子でもありません。

### IDの構成要素

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
CILIUM_POD='<agent-on-the-workload-node>'
kubectl -n default get ciliumendpoints
kubectl get ciliumidentities
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg encrypt status
```

名前空間、サービスアカウント、選択ワークロードラベルが寄与し得ます。ID 1–6はhost、world、unmanaged、health、init、remote-nodeに対応し、割り当てワークロードIDはインストールに依存します。関連ノードのエージェントを調べ、コマンド失敗/状態を完全に保持します。

### IDベースのポリシー

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: identity-based-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: frontend
        k8s:environment: production
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        k8s:app: prometheus
    toPorts:
    - ports:
      - port: '9090'
        protocol: TCP
```

### IPとIDの比較

![IDセレクターでPod変更ごとのアドレス一覧手修正を避ける一方、CiliumはアドレスとIDの対応状態を維持する。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-4.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-4.html)

IP変更をまたいでポリシーセレクターは安定したままにできます。Ciliumはエンドポイント/IPキャッシュ状態を更新する必要があり、IDはGCで回収・再割り当てされ得ます。図は再起動ごとに数値IDが不変と約束しません。

## 外部PKI統合

### cert-manager統合

以下は上流CA Secret生成の例であり、**それだけでSecretをSPIREへ接続しません**。

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: cilium-ca-issuer
spec:
  ca:
    secretName: cilium-ca-secret
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: cilium-spire-ca
  namespace: cilium-spire
spec:
  secretName: spire-ca-secret
  duration: 8760h
  renewBefore: 720h
  isCA: true
  privateKey:
    algorithm: ECDSA
    size: 256
    rotationPolicy: Always
  usages:
  - cert sign
  - crl sign
  subject:
    organizations:
    - Cilium
  commonName: SPIRE upstream CA
  issuerRef:
    name: cilium-ca-issuer
    kind: ClusterIssuer
    group: cert-manager.io
```

cert-manager設定のクラスターリソース名前空間にある`cilium-ca-secret`へ、十分な残存有効期間を持つ有効署名CA/キーを準備します。CA制約、署名用途、信頼チェーンを検証します。1年は下位CA寿命の例で、普遍的推奨ではありません。

外部管理SPIREサーバーは対応UpstreamAuthorityを使い、必要マウント素材またはissuer APIへアクセスする必要があります。既存PKIへ参加するdisk authorityでは、SPIREは`cert_file_path`、`key_file_path`、信頼ルートの`bundle_file_path`を要求します。再読み込み/ローテーションと信頼の重複期間を計画します。Kubernetes Secret更新だけでは全利用者が新CAを採用した証明にはなりません。

同梱SPIRE ConfigMapを部分的な無関係ファイルで置き換えないでください。外部運用SPIREでは、Ciliumの外部サーバーアドレス、trust domain、委任ID登録、認証前提を別々に確認します。

### Vault統合

以下は独立設定したSPIRE 1.15.2サーバーの**プラグイン断片**のみで、完全なサーバー設定やKubernetes Deploymentではありません。

```hcl
plugins {
  UpstreamAuthority "vault" {
    plugin_data {
      vault_addr = "https://vault.vault.svc:8200"
      pki_mount_point = "pki"
      ca_cert_path = "/vault/ca/ca.crt"
      k8s_auth {
        k8s_auth_mount_point = "kubernetes"
        k8s_auth_role_name = "spire-upstream"
        token_path = "/var/run/secrets/vault/token"
      }
    }
  }
}
```

プラグインは`server`内でなく最上位`plugins`に置きます。フィールドは`pki_mount_point`、ここで`token_path`は`k8s_auth`内です。トークンは設定Vault認証ロール用の投影Kubernetesサービスアカウントトークンで、汎用Vaultトークンファイルではありません。

トークン投影/audienceとVault Kubernetes認証を準備し、ロールを対象SPIREワークロードに結び付け、Vault検証用TLS CAをマウントして、必要なPKI sign-intermediate操作を許可します。SPIREの`ca_ttl`、Vault PKI TTL、ワークロード信頼、ローテーションを調整します。このガイドは外部依存をデプロイ/テスト済みと主張しません。

## ゼロトラストネットワーキング

### デフォルト拒否ポリシー

このクラスター範囲リソースは、隔離した`policy-lab`名前空間を意図的に対象とします。

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: policy-lab-default-deny
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: policy-lab
  enableDefaultDeny:
    ingress: true
    egress: true
  ingress: []
  egress: []
```

`enableDefaultDeny`を明示します。空のCilium ingress/egress配列だけではデフォルト拒否を有効にするルールは提供されません。Kubernetes NetworkPolicy例からその前提を持ち込まないでください。

DNSなど具体的な依存先を別Allowルールとして追加します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: policy-lab-dns
  namespace: policy-lab
spec:
  endpointSelector: {}
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```

すべてのホストネットワーク通信を許す普遍的要件はありません。実kubelet/プローブ、リゾルバー、ホストポリシー動作を評価します。例はCiliumのホスト処理を変えず、侵害された特権ノードを防御しません。

### 最小権限アクセス

例は`edge`の`app=ingress-gateway`ラベル付きCilium管理ゲートウェイ、`production`のfrontend/database、動作するSPIRE統合を前提とします。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: production-security
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: edge
        k8s:app: ingress-gateway
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
```

選択Gateway実装で実際に観測したラベルとIDを使います。Cilium自身のノードEnvoy Ingress/Gateway経路や外部LBは異なるIDを示す場合があります。任意Podラベルは`reserved:ingress`や外部クライアントアドレスと交換可能ではありません。終了した旧ingress-nginx例は必須依存ではありません。

### マイクロセグメンテーション

このアプリ階層ポリシーは、Service検索を開始する階層に明示DNSアクセスを残します。同じGatewayモデルと指定待ち受けポートを前提とします。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: frontend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: edge
        k8s:app: ingress-gateway
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: backend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: database
  enableDefaultDeny:
    egress: true
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: backend
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
  egress: []
```

DBはEgress Allowなしで明示的にEgressデフォルト拒否を有効にします。許可接続へのステートフル応答は引き続き許可されます。実バックアップ、レプリケーション、認証などの依存を意図的に追加します。ネットワーク経路制限は、認可されたDB/アプリ要求を通じたデータ取得を完全防止しません。

## セキュリティ監査と監視

### ポリシー監査モード

`cilium.io/audit-mode: "true"`は対応するポリシーごとの監査スイッチではありません。その任意アノテーションを持つポリシーも通常どおり適用され得ます。

**隔離エンドポイントテスト**では、実際の変更可能オプションは`PolicyAuditMode`です。ローカルエンドポイントを確認し、一時有効化して管理された観察後に適用を戻します。

```bash
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
ENDPOINT_ID='<local-endpoint-id-in-the-isolated-test>'
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID" PolicyAuditMode=true
# Observe the controlled test, then restore enforcement.
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID" PolicyAuditMode=false
```

1ポリシーオブジェクトへ監査動作を付けるのでなく、そのエンドポイントの適用を変えます。全L7拒否や全セキュリティ失敗が許可監査イベントになると推測しないでください。具体的データパス/プロキシ動作を確認します。`enableDefaultDeny: false`も同等のL7監査モードではありません。

### ポリシー違反の監視

```bash
# Terminal 1
cilium hubble port-forward --port-forward 4245
# Terminal 2
hubble observe --server localhost:4245 --namespace production --verdict DROPPED --last 100
hubble observe --server localhost:4245 --namespace production --verdict DROPPED --drop-reason-desc POLICY_DENIED --last 100
hubble observe --server localhost:4245 --namespace policy-lab --verdict AUDIT --last 100
```

`DROPPED`にはポリシー拒否以外の原因も含まれます。理由で絞ったクエリは報告されたpolicy-denied破棄に注目します。L7/アプリ認可失敗には独自観測が必要です。`AUDIT`は`DROPPED`と別です。`--last 100`は制限付き履歴で、Relayは接続Hubbleインスタンスごとにその数を返す場合があります。完全なクラスター通信カウンターではありません。ストリーミング観測が意図した場合だけ`--follow`を追加します。

### Prometheusメトリクス

```yaml
prometheus:
  enabled: true
hubble:
  enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - flow
    - httpV2
    - icmp
    - port-distribution
    - tcp
```

エージェントとHubbleエクスポーターには、有効化フラグに加えてPrometheus検出/スクレイプが必要です。`httpV2`は非推奨`http`を置き換えるため両方有効にしないでください。HTTPメトリクスには対応L7可視性が必要です。

- `cilium_drop_count_total`は理由/方向別の破棄パケットを数え、ポリシー違反だけではありません。
- `cilium_forward_count_total`は転送パケットを数え、成功アプリ要求ではありません。
- Hubbleの`drop`エクスポーターは`hubble_drop_total`でフロー破棄情報を公開し、エージェントのパケットカウンターとは計数単位が違います。
- 旧`cilium_policy_verdict`は文書化されたメトリクス名ではありません。実ポリシー判定イベントか選択エクスポーターが公開するメトリクスを使います。

## 次のステップ

- [可観測性](./04-observability.md)
- [IngressとGateway](./05-ingress-gateway.md)
- [ベストプラクティス](./06-best-practices.md)
- [セキュリティクイズ](../../quizzes/service-mesh/cilium-service-mesh/security.md)

## 参考資料

- [Cilium1.20.1相互認証](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [認証例/API構造](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication-example.rst)
- [Cilium1.20.1 CNPスキーマ](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)
- [Cilium1.20.1 ztunnelベータ](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)
- [Ztunnel CA実装](https://github.com/cilium/cilium/blob/v1.20.1/pkg/ztunnel/ca/ca_server.go)
- [Ztunnelブートストラップ例](https://github.com/cilium/cilium/blob/v1.20.1/examples/kubernetes-ztunnel/generate-secrets.sh)
- [暗号化範囲/strictモード](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption.rst)
- [WireGuard](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-wireguard.rst)
- [IPsecと鍵ローテーション](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ipsec.rst)
- [Helm values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)
- [HTTP/DNSポリシー](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst)
- [デフォルト拒否動作](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/intro.rst)
- [明示的デフォルト拒否API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/rule.go)
- [変更可能エンドポイント監査オプション](https://github.com/cilium/cilium/blob/v1.20.1/pkg/option/endpoint.go)
- [エンドポイント設定CLI](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/cmdref/cilium-dbg_endpoint_config.md)
- [メトリクス](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/observability/metrics.rst)
- [SPIRE1.15.2サーバー設定](https://github.com/spiffe/spire/blob/v1.15.2/doc/spire_server.md)
- [SPIRE Vault authority](https://github.com/spiffe/spire/blob/v1.15.2/doc/plugin_server_upstreamauthority_vault.md)
- [SPIRE disk authority](https://github.com/spiffe/spire/blob/v1.15.2/doc/plugin_server_upstreamauthority_disk.md)
- [Kafka ACL](https://kafka.apache.org/41/security/authorization-and-acls/)
- [AWS STSエンドポイント](https://docs.aws.amazon.com/general/latest/gr/sts.html)
- [WireGuardプロトコル](https://www.wireguard.com/protocol/)
- [NISTゼロトラストアーキテクチャ — 追加資料](https://www.nist.gov/publications/zero-trust-architecture)
