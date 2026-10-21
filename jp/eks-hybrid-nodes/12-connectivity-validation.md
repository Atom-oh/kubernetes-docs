# SNATなしのPod接続とPrivateLinkの検証

> **サポート対象バージョン**: EKS 1.36、Cilium 1.18.13（AWSビルド）、CoreDNSアドオン v1.14.7-eksbuild.10、デフォルトのVPC CNI設定
> **最終更新日**: 2026年10月19日

一部のファイアウォールでは、オンプレミスのPodをノードIPではなく**Pod IP**で識別する必要があります。このページでは、その要件を検証したテストを記録しています。Ciliumをネイティブルーティングに切り替えてマスカレードを無効にし、クラスター内外で38件の接続確認を実施しました。また、オンプレミスのPodがインターネットを経由せずにAWS API（STS、S3）を呼び出せるPrivateLink経路と、リンクがダウンしたときのDNSの動作についても説明します。

テスト環境は**オンプレミスをシミュレート**しています。2つ目のVPCをTransit Gateway（TGW）経由で接続し、そのEC2インスタンスをハイブリッドノードとして登録しています。EC2上でハイブリッドノードを実行することはサポートされておらず、ハイブリッドノードの料金が適用されます。数値は2026年10月19日の1回の実行結果です。Direct ConnectまたはVPN経由の実際のオンプレミスネットワークで再検証してください。

## まずサポート範囲を確認する

[ハイブリッドノード用のCNI設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)の「サポートされる機能」表では、AWSがサポートするCiliumの**ネットワーキングモードは「VXLANカプセル化」のみ**です。同じページには、マスカレードを無効にできること、その場合はオンプレミスネットワーク上でPod CIDRをルーティング可能にする必要があることが説明されており、ルーティング可能にする方法としてCilium BGP Control Planeが推奨されています。

| 構成 | Pod IPが見える場所 | AWSのサポート | Hybrid Nodes Gateway |
|---|---|---|---|
| VXLAN + マスカレード（デフォルト） | クラスター外からはどこにも見えない。ノードIPが見える | サポート対象 | 使用可能 |
| VXLAN + マスカレード無効 + BGP | クラウドからオンプレミス、およびオンプレミスのサーバー | サポート対象 | 使用可能 |
| **ネイティブルーティング + マスカレード無効**（このページ） | 上記に加え、**ハイブリッドノード間のセグメント** | **サポート範囲外** | 使用不可（VTEP、つまりVXLANが必要） |

VXLANでは、ハイブリッドノード間のトラフィックの外側ヘッダーにノードIPが含まれるため、そのセグメント上のファイアウォールからPod IPは見えません。そのセグメントでもPod IPを必要とするかどうかで選択が変わります。サポート範囲内にとどまる2行目で、ほとんどのケースには十分です。AWSのサポートの代わりにCiliumの商用サポートまたは社内の専門知識を利用できる場合に限り、3行目を検討してください。

## 構成

### アドレス範囲

| 範囲 | 値 | 注記 |
|---|---|---|
| クラウドVPC | `10.0.0.0/16` | クラウドノードとPod（VPC CNI） |
| リモートノードネットワーク | `172.18.0.0/16` | シミュレートしたオンプレミスVPC（ハイブリッドノードのホスト） |
| リモートPodネットワーク | `172.17.0.0/16` | Cilium cluster-pool。ノードごとに`/25` |
| Service | `172.16.0.0/16` | |

### Ciliumの値（ベース値への上書き）

```yaml
routingMode: native
ipv4NativeRoutingCIDR: "172.17.0.0/16"   # remote pod network
autoDirectNodeRoutes: false              # hosts are in different subnets; the on-prem router forwards
enableIPv4Masquerade: false              # no SNAT
vtep:
  enabled: false                         # no gateway
```

Cilium ChartはConfigMapが変更されてもエージェントを再起動しません（`rollOutCiliumPods`のデフォルトは`false`です）。そのため、値を変更した後に`kubectl -n kube-system rollout restart ds/cilium`を実行してください。その後、`cilium-dbg status`に`Routing: Network: Native`と表示されることを確認します。ConfigMapには引き続き`tunnel-protocol: vxlan`が含まれていましたが、影響はありませんでした。ホストNICでパケットをキャプチャしたところ、VXLANパケット（UDP 8472および4789）は0件でした。

### ルーティングとSNATの例外

| 場所 | 設定 | 理由 |
|---|---|---|
| オンプレミスルーター | 各ノードのPodブロック（`/25`）をそのノードに向ける | 本番環境ではCilium BGP Control Planeでアドバタイズします。テストではオンプレミスVPCのルートテーブルに静的ルートを設定しましたが、ノードが再参加して別のPodブロックを取得すると古くなります。 |
| クラウドルートテーブル、TGW | `172.17.0.0/16`をオンプレミスに向ける | 戻りトラフィックがPod IPに直接到達する |
| VPC CNI | `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS=172.17.0.0/16,172.18.0.0/16` | クラウドPodもオンプレミスに向けて自身のIPを維持する。**ノード範囲（172.18）を含めないと、オンプレミスのサーバーにはクラウドノードIPが見えます。** |
| クラスターセキュリティグループ | `172.17.0.0/16`全体、および`172.18.0.0/16`からのUDP/TCP 53 | Podトラフィック、およびhostNetwork PodからのDNS（ノードIPを使ってCoreDNSを呼び出す） |

## 接続マトリックスの結果

各確認では、HTTPレスポンスだけでなく、サーバーが記録した**送信元アドレス**も検証しました。具体的にはnginxのアクセスログ（`$remote_addr`）、またはKubernetesの外部にあるサーバーの場合は、ピアアドレスをエコーする`socat`リスナーを確認しました。結果は38件成功、0件失敗でした。

| セグメント | 確認数 | 確認内容 | 結果 |
|---|---|---|---|
| PodからPod、直接接続 | 7 | 同一ハイブリッドノード内、ハイブリッドノード間、ハイブリッドとクラウドの双方向、クラウド間 | サーバーから見える送信元 = クライアントPod IP |
| ClusterIP Service | 3 | ハイブリッドからハイブリッドのバックエンド、ハイブリッドからクラウドのバックエンド、クラウドからハイブリッドのバックエンド | kube-proxyが書き換えるのは宛先のみ。送信元Pod IPは維持される |
| DNS | 4 | 2つのハイブリッドPodとhostNetwork PodからのService名、およびパブリック名 | CoreDNS（クラウドノード）とVPCリゾルバー経由で名前解決 |
| Kubernetes API | 2 | `kubernetes.default.svc/livez`、ServiceAccountトークン | 200、および403（認証済み、RBACの許可なし） |
| コントロールプレーンからハイブリッド | 3 | APIサーバープロキシ（webhook経路）、`exec`と`logs`、metrics-server | プロキシリクエストはクラウドVPC内のEKS管理ENIから送信される |
| Kubernetes外のオンプレミスサーバー | 2 | ハイブリッドPodとクラウドPodからハイブリッドホスト上の`socat`へ接続 | サーバーに172.17.xと10.0.xのPod IPが届いた |
| インターネット | 3 | ハイブリッドPod 2つ、クラウドPod 1つ | すべて単一のクラウドNATゲートウェイ経由で送信。経路上のアドレス変換はこれだけ |
| Ciliumポリシー | 3 | ハイブリッドPod上の`fromCIDR: 10.0.0.0/16` | ハイブリッドPodはブロック、クラウドPodは許可。削除後に元に戻る |
| MTU、大容量転送 | 2 | 双方向に32 MiBを転送し、sha256を比較 | 一致。Pod MTUは9001、8500バイトパケットのDF pingは成功 |
| ALB IPターゲット | 1 | ハイブリッドPod 2つ | 正常 |
| PrivateLink | 8 | 以下を参照 | すべて成功 |

`fromCIDR`ポリシーが機能したことも、SNATがない証拠です。クラウドPodはVPC CNIを使用し、Cilium IDを持たないため、ポリシーではIP範囲でしか一致させられません。これはPod IPが変更されずに届く場合にのみ機能します。

Pod MTUは9001、TGWの上限は8500です。TCPはTGWがMSSを調整するため問題ありませんでした。UDPなど、MSS調整のないプロトコルや、DXまたはVPN経路については、経路MTUを別途確認してください。

### 初回実行時に発生した3つの失敗

| 症状 | 原因 | 対処 |
|---|---|---|
| hostNetwork PodがService名を名前解決できない | hostNetwork PodはノードIP（172.18.x）を使ってCoreDNSを呼び出すが、クラスターSGにその範囲からのポート53のルールがなかった | クラスターSGで`172.18.0.0/16`からのUDPおよびTCP 53を許可する |
| オンプレミスサーバーにクラウドPodのノードIPが見える | VPC CNIのSNAT除外リストにPod範囲は含まれていたが、オンプレミスのノード範囲は含まれていなかった | `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS`に`172.18.0.0/16`を追加する |
| 匿名の`GET /version`が401を返す | EKS 1.36では、匿名リクエストが許可されるのはヘルスエンドポイントのみ | 到達性の確認には`/livez`または`/readyz`を使う |

## PrivateLink経由でオンプレミスPodからAWS APIを呼び出す

オンプレミスPodがAWS APIを呼び出す際にインターネットを経由しないようにするには、クラウドVPCにインターフェイスエンドポイントを配置し、DXまたはVPN経由でアクセスします。

```
hybrid Pod (172.17.x)
  -> CoreDNS -> VPC resolver: sts.<region>.amazonaws.com and s3.<region>.amazonaws.com resolve to endpoint ENIs (10.0.x)
  -> TGW (DX/VPN in production), source Pod IP preserved
  -> STS and S3 interface endpoints (2 AZs, private DNS)
```

ハイブリッドPodはクラスターDNS（CoreDNS）を通じて名前を解決し、続いてVPCリゾルバーを使うため、エンドポイントのプライベートDNSがそのまま適用されます。Kubernetes外部のオンプレミスサーバーで同じ応答を得るには、[Route 53 Resolverインバウンドエンドポイント](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-inbound-queries.html)が必要です。

### コンポーネント

| コンポーネント | 設定 |
|---|---|
| STSインターフェイスエンドポイント | プライベートDNSを有効化 |
| S3インターフェイスエンドポイント | プライベートDNSを有効化。**S3ゲートウェイエンドポイントのないVPCでは、`DnsOptions.PrivateDnsOnlyForInboundResolverEndpoint: AllResolvers`を設定します。設定せずに行った最初の試行は**、「To set PrivateDnsOnlyForInboundResolverEndpoint to true, the VPC must have a Gateway endpoint」というエラーで失敗しました。 |
| エンドポイントセキュリティグループ | `10.0.0.0/16`（VPC）および`172.17.0.0/16`（ハイブリッドPod）からのTCP 443のみ。ノード範囲の`172.18.0.0/16`は意図的に含めない |
| IAM | クラスターOIDCプロバイダー、ServiceAccountにバインドされたロール（IRSA） |
| バケットポリシー | テストロールは、`aws:SourceVpce`がS3エンドポイントの場合にのみ許可 |

S3ゲートウェイエンドポイントは[オンプレミスから使用できません](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)。オンプレミスPodにはインターフェイスエンドポイントが必要です。

以下のバケットポリシーは、テストロールのみをエンドポイント外でブロックします。オペレーターなど、他のプリンシパルには影響しません。

```json
{
  "Sid": "TestRoleOnlyThroughEndpoint",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::<bucket>", "arn:aws:s3:::<bucket>/*"],
  "Condition": {
    "StringNotEquals": {"aws:SourceVpce": "<s3-endpoint-id>"},
    "ArnEquals": {"aws:PrincipalArn": "<test-role-arn>"}
  }
}
```

### IRSAとPod Identity

IRSAでは、Pod自身が投影トークンを使ってSTSの`AssumeRoleWithWebIdentity`を呼び出すため、トークン交換はすでにSTSエンドポイント経由で行われます。クラスターOIDCプロバイダーが存在しない場合は、先に作成してください。Podの`env`で`AWS_STS_REGIONAL_ENDPOINTS=regional`を設定すると、SDKがリージョナルSTS名を使用し、プライベートDNSで名前解決できます。

EKS Pod Identityをハイブリッドノードで使うには、[追加の設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)が必要です。nodeadm設定の`enableCredentialsFile`と、Pod Identity Agentアドオン設定の`{"daemonsets":{"hybrid":{"create":true}}}`を指定します。テストクラスターのデフォルトのAgent DaemonSetはハイブリッドノードを除外していたため、このテストではIRSAを使用しました。

### 結果（8件すべて成功）

| 確認項目 | 結果 |
|---|---|
| ハイブリッドPodから`sts`、`s3`、バケットのホスト名を名前解決 | すべてエンドポイントENIのアドレス（10.0.x）を返す |
| ハイブリッドPod：`sts get-caller-identity`（IRSA） | AssumeRole ARNが返り、トークン交換にはSTSエンドポイントが使用された |
| ハイブリッドPod：`PutObject` | 成功。バケットポリシーはこのロールをエンドポイント外でブロックするため、リクエストはエンドポイント経由で送信された |
| クラウドPod：同じオブジェクトの`GetObject` | 同じ内容 |
| 同じノード上のPodおよびhostNetwork PodからSTS ENI:443へ接続 | Pod（172.17.x）はHTTP 302を受信、hostNetwork（172.18.x）はタイムアウト |
| エンドポイント外（ワークステーション）から同じロールを使用 | `aws:SourceVpce`条件により拒否 |

同じノードから送信されたにもかかわらず、Podは成功し、hostNetwork Podはブロックされました。**AWS側のセキュリティグループでも、Pod範囲を使ってオンプレミスPodを識別できます**。これはSNATがないことを示す最も直接的な証拠です。

## リンクがダウンしたときのDNSの動作

TGWルートテーブルにブラックホールルート（オンプレミスのノード範囲とPod範囲に対する`/17`）を追加し、DXまたはVPNの障害を約95秒間再現しました。ルート変更が反映されるまで約17秒かかりました。各ハイブリッドノードでは、プローブPodがオンプレミスService名とクラウドService名を毎秒名前解決し、その後、オンプレミスServiceを名前とClusterIPの両方で呼び出しました。障害中、ハイブリッドノードは`NotReady`になりましたが、Podは実行を続けました（プローブログに途切れはありません）。初回実行では、リンク復旧から約23秒後に再び`Ready`になりました。

| 構成 | 障害中のハイブリッドPodでの名前解決 | オンプレミスServiceへの呼び出し | 注記 |
|---|---|---|---|
| デフォルト：CoreDNSレプリカ2つともクラウドノード上 | **すべての名前解決が失敗**（43～44件中26件が失敗） | ClusterIPでは200、名前では失敗 | オンプレミス内のトラフィックは引き続き動作するが、名前解決は動作しない |
| ゾーンラベル + レプリカ3つ + `PreferSameZone`（ドキュメントの例とは異なる） | 約半数が失敗（76～80件中38～44件） | 名前による呼び出しが断続的に失敗 | Ciliumはヒントを無視し、到達不能なクラウドCoreDNSにも引き続き負荷分散する |
| ゾーンラベル + レプリカ4つ + **`PreferClose`** + 強制ゾーン分散 + Cilium再起動 | **失敗0件**（96～97件すべて成功） | 名前とClusterIPのどちらでも200 | クラウドPodの名前解決は正常。想定どおり、オンプレミスへの呼び出しのみ失敗 |

各段階で判明した原因は次のとおりです。

1. **AWSのドキュメントに記載された値`PreferClose`を使用してください。Ciliumは`PreferSameZone`を適用しませんでした。AWSの例では**`trafficDistribution: PreferClose`を使用しています。Kubernetes 1.35で`PreferClose`が非推奨の別名になったため、テストでは新しい名称の`PreferSameZone`を使用しましたが、それが失敗率の半減につながりました。ハイブリッドノードでは、`kubeProxyReplacement: false`の場合でも、ClusterIPの負荷分散はkube-proxyではなくCilium BPFが行います。EndpointSliceにはゾーンヒントがありましたが、`cilium-dbg bpf lb list`には3つのCoreDNSバックエンドすべてが残っていました。`trafficDistribution: PreferClose`では、オンプレミスのバックエンド2つだけが残りました。EndpointSliceのヒントはどちらの値でも同じように見えるため、ハイブリッドノード上のCiliumでバックエンド一覧を確認してください。
2. **参加時にゾーンラベルを設定してください**。テストでは後からラベルを追加し、`kubectl -n kube-system rollout restart ds/cilium`でCiliumを再起動しました。再起動なしで反映されるかどうかは確認していません。nodeadm設定でkubeletの`--node-labels=topology.kubernetes.io/zone=<name>`を指定して参加させれば、この問題を避けられます。
3. **CoreDNSのないクラウドAZも問題になります**。ゾーン内にCoreDNSがないクラウドPodは、すべてのバックエンドに負荷分散されます。オンプレミスのCoreDNSに送られたクエリは、障害中に失敗します。クラウドAZごとに1つのレプリカを実行し、さらにオンプレミスにも少なくとも1つ配置してください。
4. **優先アンチアフィニティでは配置を保証できませんでした**。CoreDNSの再起動後、オンプレミスのレプリカが一度1つに減りました。`whenUnsatisfiable: DoNotSchedule`を指定した`topologySpreadConstraints`により、ゾーンごとに少なくとも1つのレプリカを配置できます。
5. **ハイブリッドノード上のCoreDNSはPrivateLinkを経由しません**。ノードのリゾルバー（オンプレミスDNS）に転送するため、`sts`と`s3`はパブリックアドレスに解決されました。NAT経由で呼び出し自体は成功し正常に見えますが、S3リクエストは`aws:SourceVpce`バケットポリシーによって拒否され、マトリックスの確認項目4件が失敗しました。対処として、クラウドVPCにRoute 53 Resolverインバウンドエンドポイントを作成し、CoreDNSに`amazonaws.com`ブロックを追加しました。実際のネットワークでは、オンプレミスDNSサーバー上の条件付きフォワーダーでも同じことができます。

最終的なCoreDNSアドオン設定値（`aws eks update-addon --configuration-values`）：

```json
{
  "replicaCount": 4,
  "trafficDistribution": "PreferClose",
  "topologySpreadConstraints": [{
    "maxSkew": 1, "topologyKey": "topology.kubernetes.io/zone", "whenUnsatisfiable": "DoNotSchedule",
    "labelSelector": {"matchLabels": {"k8s-app": "kube-dns"}}
  }],
  "corefile": "...default .:53 block...\namazonaws.com:53 {\n    errors\n    cache 30\n    forward . <inbound endpoint IP 1> <inbound endpoint IP 2>\n}"
}
```

`corefile`の値はCorefile全体を置き換えるため、デフォルトの`.:53`ブロックを含める必要があります。Corefileを変更した後、ハイブリッドノード上のCoreDNSレプリカ1つがConfigMapの変更を反映するのに時間がかかり、しばらく古い設定で応答していました。`rollout restart deploy/coredns`で解決しました。インバウンドエンドポイントのSGでは、ポート53をVPC範囲とハイブリッドPod範囲からのみ許可します。障害中はインバウンドエンドポイントにも到達できないため、AWS APIの名前は解決されませんが、その時点ではエンドポイント自体にも到達できません。

## 運用時に注意すること

- **CoreDNSの配置**：AWSは、混在モードのクラスターではハイブリッドノード上とクラウドノード上に少なくとも1つずつCoreDNSレプリカを配置することを推奨しています（[CoreDNSレプリカの設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)）。上記の測定結果からわかるように、障害中に効果を得るには、ゾーンラベル、ゾーン分散、`trafficDistribution`、およびCiliumの`loadBalancer.serviceTopology: true`をすべて正しく設定する必要があります。変更後は実際にリンクを切断して確認してください。
- **Webhookとコントロールプレーンの経路**：APIサーバープロキシのリクエストは、クラウドVPC内のEKS管理ENIから送信されました。ハイブリッドノード上でWebhookを実行するには、Pod CIDRをルーティング可能にし、オンプレミスのファイアウォールでそれらのENIがあるVPC範囲を許可する必要があります。
- **静的ルートのずれ**：再参加したノードが別のPodブロックを取得することがあります。BGPを使わない場合は、参加のたびにルートを調整する手順が必要です。
- **インターネットへの送信**：この構成ではオンプレミスのデフォルトルートをクラウドに向けていたため、すべての通信が1つのNATゲートウェイ経由で送信されました。オンプレミスが独自のインターネット経路を使う場合、その経路のNATとファイアウォールポリシーでPod範囲を認識できる必要があります。
- **コスト**：インターフェイスエンドポイントはAZごとの時間単位、および処理GB単位で課金されます。

## クイズ

* [SNATなしのPod接続とPrivateLinkのクイズ](../quizzes/eks-hybrid-nodes/12-connectivity-validation-quiz.md)

## 参考資料

* [ハイブリッドノード用のCNI設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)：サポートされるネットワーキングモード、マスカレード、BGPの推奨事項
* [ハイブリッドノードのネットワーキングを準備する](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [ハイブリッドノード用のWebhookを設定する](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)：CoreDNSレプリカの配置
* [ハイブリッドノード用のアドオンを設定する](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)：Pod Identity Agent
* [ネットワーク切断時の安定性に関するベストプラクティス](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
* [Amazon S3向けAWS PrivateLink](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
* [AWS PrivateLink経由でAWSサービスにアクセスする](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-aws-services.html)
* [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md)、[ネットワーク構成](02-network-configuration.md)、[ネットワーク分離のセキュリティレビュー](11-network-separation-security.md)
