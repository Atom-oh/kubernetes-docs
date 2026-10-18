# Shared VPC と接続性

> **最終更新**: 2026年9月13日

## 1. Shared VPC の Owner／Participant 権限: よくある誤解

Shared VPC（AWS RAM による Account 間の subnet 共有）を導入するとき、最もよくある誤解は「共有すれば両側から同じように見える」というものです。実際には resource ごとに owner と participant の権限が大きく異なります。

| Resource | Participant の権限 | Owner の権限 |
|---|---|---|
| Subnet | Describe のみ | すべて |
| Route table | Describe のみ | すべて |
| NACL | Describe のみ（owner が作成したもの） | すべて |
| **NAT Gateway** | **Describe も不可** | すべて |
| Internet Gateway | Describe のみ（Egress-only IGW は Describe も不可） | すべて |
| TGW attachment | 作成不可 | Owner のみ |
| ENI | 自分のものはすべて | 他者のものは Describe のみ |
| Security Group | 自分のものはすべて。owner が共有した SG も利用可能 | 他者のものは Describe のみ |
| Flow Logs | 自分の ENI のみ | Subnet と全 ENI が対象になり得る（participant 作成の Flow Log は owner でも Describe／削除不可） |

この表から、実務上2つの点が分かります。

**Flow Log の所有権は対称ではありません。** Owner が管理する subnet／VPC の中央 log と、participant の ENI log は、それぞれの目的、保持、費用負担を明示すれば共存できます。AWS は、すべての participant log を SCP で禁止することを求めていません。Flow Logs は通信を観測しますが、遮断はしません。

**VPC／subnet の tag は participant と共有されません。** 実際に使う Load Balancer Controller の version、mode、IAM permission で discovery をテストしてください。Subnet ID annotation を明示する方法は予測しやすい選択肢です。すべての discovery mode／version が失敗するという意味ではありません。

Security Group がサポートするのは Allow rule だけで、複数 SG の rule は統合されます。1つの SG に広い Allow があれば、より制限的な中央 SG を追加しても打ち消せません。調整可能な既定上限は SG あたり60 rule（inbound／outbound × IPv4／IPv6 をそれぞれ計上）、ENI あたり5 SG です。また **「rule 数 × ENI あたりの SG 数 ≤ 1,000」** という制約があります。Firewall Manager の共通 SG policy も同じ予算を消費します。

Participant の ENI／SG quota は、その participant Account に計上されます。既定値は5,000 ENI／AZ と2,500 SG／Region で、Account ごとのボトルネックになる場合があります。これらは調整可能です。SG 認可とは別に capacity を評価してください。

<span id="_2-the-real-ceiling-on-shared-vpc-—-it-s-not-the-cidr"></span>

## 2. Shared VPC の quota を実際の適用範囲に沿って計算する

ボトルネックになる順序は workload によります。既定 quota と適用済み quota を分け、それぞれの範囲での増加を予測してください。

| 範囲 | 既定 quota | 意味 |
|---|---|---|
| VPC route table あたりの非伝播 route | IPv4／IPv6 それぞれ500。1,000まで調整可能 | TGW を宛先にする static route を含む |
| VPC route table あたりの伝播 route | 100。固定 | TGW table 全体の上限とは別の VGW propagation 上限 |
| TGW 全 route table の static + dynamic route 合計 | TGW あたり10,000 | 上限引き上げは SA／TAM に相談 |
| VPC あたりの participant Account | 100。調整可能 | 共有先の principal 数 |
| 受信 Account あたりの共有 subnet | 100。調整可能 | AZ／用途の組み合わせ |
| VPC あたり NAU | 64,000。256,000まで調整可能 | Pod IP、ENI、managed prefix-list entry を含む |
| VPC あたり subnet と route table | それぞれ200。調整可能 | 設定数 |
| VPC あたり IPv4 CIDR | 5。50まで調整可能 | Address の消費と断片化も評価する |

**TGW route は VPC route table に自動で伝播しません。** VPC owner が TGW を宛先とする static route を追加します。Attachment の propagation は TGW route table で管理します。したがって「TGW prefix が100を超えると Shared VPC が停止する」という説明は正しくありません。既定 route が検査を維持するか迂回するかは、実際の route association と戻り経路によります。

### 最小 Shared VPC Pool と workload group ごとの Shared VPC

「すべての workload を1つの Shared VPC にまとめる最小構成」と「workload group ごとに専用 Shared VPC を用意する複数構成」を比べるとき、見落としやすい視点があります。

- 同じ TGW–VPC の組み合わせに対する VPC attachment は**1つだけ**です。VPC は最大5つの TGW に接続できます。既定の attachment capacity は各方向100 Gbps／AZ あたり7.5 MPPS です。追加 capacity は SA／TAM に相談してください。
- 最小構成では、すべての workload の on-prem／external traffic がこの単一 attachment に集まります。共有するのは障害範囲だけでなく、**帯域と PPS の上限**でもあります。
- workload group ごとの構成では、各 VPC に独自の attachment があり、throughput の上限を分割できます。**TGW throughput 上限を分割できることが「複数の専用 Shared VPC」を選ぶ実務上の本当の理由です。**

結局、最小構成と group ごとの構成の選択は、「コスト対隔離」ではなく、**「中央 network pipeline の変更リスク」と「VPC 単位で共有する障害リスク」のトレードオフ**として捉えるほうが適切です。どちらも中央 pipeline の品質に依存するため、実際の判断要素は、どちらの案でも「中央 route の誤変更をどれだけ早く検知して復旧できるか」を測定することです。一般 workload には最小構成を使い、on-prem／external 接続が多い workload には信頼ゾーンごとに専用構成を用意する hybrid も検討できます。

### Transit Gateway の主な quota

| Quota | 既定値 | 調整可能 |
|---|---:|---|
| Account あたり TGW | 5 | はい |
| TGW あたり attachment | 5,000 | はい |
| **VPC あたり TGW** | **5** | **いいえ** |
| TGW あたり route table | 20 | はい |
| TGW あたり route 合計 | 10,000 | SA／TAM に相談 |
| **同じ TGW–VPC の組み合わせに対する attachment** | **1** | **いいえ** |

**経路全体で MTU を確認してください。** TGW は VPC／DX／Connect／peering 経路で8,500 byte をサポートします。VPN には別の tunnel 上限があります。VPC peering から TGW に移行する場合は、両方の endpoint の jumbo-frame 設定と PMTUD をテストしてください。MSS clamping が関係するのは TCP であり、UDP などすべての packet protocol の MTU 問題を解決するわけではありません。

Peered NAU は、同一 Region 内で直接 peering する VPC と対象の VPC を数えます（既定128,000、最大512,000）。組織内のすべての VPC や、推移的な接続 graph を数えるわけではありません。

## 3. AZ ID と Shared VPC

`ap-northeast-2a` などの AZ 名は、Account 間で異なる物理 AZ に対応する場合があります。Account をまたぐ resource の配置には、AZ 名ではなく **AZ ID（`apne2-az*`）** を使ってください。

VPC CNI の custom networking では、AZ ID を使って owner subnet を participant node の物理 AZ に対応付けます。ENIConfig の名前は、選択した node annotation／label と一致させる必要があります。`ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone` を使う場合は node の AZ 名を使い、spec にはその AZ ID に対応する subnet ID を設定してください。AZ ID をそのまま ENIConfig 名にすると lookup が壊れる場合があります。Secondary CIDR だけでは security boundary になりません。

## 4. Regional NAT Gateway

| 項目 | 挙動 |
|---|---|
| Scaling | 単一 ID のまま自動で scale up／down。Public subnet は不要 |
| Private NAT | 非対応 |
| Scaling の遅延 | 最大60分（その間に AZ 間 traffic が発生する場合がある） |
| Zonal から Regional への移行 | Connection reset と IP 変更の可能性 |
| 制約のある AZ | **非対応**（事前確認が必要） |

Regional NAT Gateway は Zonal より大きい IP／connection 上限を提供します。Regional は AZ あたり32 IP（Zonal は8）を使用でき、各 IP は同じ宛先（宛先 IP + port + protocol）に対し、同時 connection を追加で55,000確保します。Payment processor や配送連携のように、**少数の宛先に大量の connection が集中する**構成では、port 枯渇を防ぐ直接的な効果があります。

Automatic mode（AWS が IP／AZ scaling を管理し、推奨）か Manual mode（利用者が直接管理）を選べます。**外部 partner の allowlist に登録した固定 egress IP が必要なら、Manual mode または IPAM public IPv4 allocation policy との連携が必要です。** Regional NAT Gateway route table は TGW を有効な宛先としてサポートするため、中央 TGW 検査と Regional NAT を組み合わせられます。相互排他的ではありません。

## 5. TGW + Network Firewall（中央検査）

East-West traffic を中央で検査する方法は2つあります。

- **Inspection VPC 経由**: Appliance mode と双方向 route が必要。
- **TGW 接続の Network Firewall**: Appliance mode が常に適用される。

Network Firewall は**非対称 routing に対応しません。** TGW owner Account と firewall owner Account が異なる場合、削除権限と可視性に制約が生じます。

AWS の観点では、中央検査を必須にする条件はありません。通常、多くの環境では**信頼ゾーン内に分散制御を置き、信頼ゾーン間や規制対象の経路だけを中央で強制する hybrid**が妥当です。

## 6. AWS API と VPC Endpoint

Service、Region、feature ごとに endpoint と endpoint policy のサポート状況を確認してください。Full access の既定 endpoint policy を設定しても、新しい IAM permission は付与されません。`describe-vpc-endpoint-services` の一覧を、service ドキュメント、private DNS の確認、実際の allow／deny 検証と組み合わせます。

## 7. Route 53 Profile と Hybrid DNS

Route 53 Profile は Private Hosted Zone、Resolver rule（forwarding／system）、DNS Firewall rule group、**interface VPC endpoint**、VPC Resolver query logging config に関連付けられます。VPC に関連付けられる Profile は1つだけです。

**最も誤解されやすいのは優先順位の規則です。** 「常に local VPC が優先」ではなく、「**より具体的な名前が優先**」されます。

| DNS query | Profile rule | VPC の local rule | 適用される rule |
|---|---|---|---|
| `example.com` | `example.com` | `example.com` | Local VPC（同じ名前なら local が優先） |
| `test.example.com` | `test.example.com` | `example.com` | **Profile（より具体的な名前が優先）** |
| `marketing.example.com` | なし | `marketing.example.com` | Local VPC |

2行目にあるとおり、中央 Profile に登録した**より具体的な名前は workload の local rule より優先されます。** これを理解していないと、原因の分からない名前解決障害が起きる場合があります。**「中央 Profile は workload に委任した namespace より具体的な名前を所有しない」という規則を明文化することを推奨します。** 実務では、namespace の管理を中央に置き、その下の subdomain を workload team に委任する方法が有効です。Route 53 Profile は Seoul Region でサポートされています。

## 8. VPC 間の接続方法

これらは相互排他的ではありません。Traffic の要件に応じて、接続ごとに選ぶ pattern です。

| 選択肢 | 適する用途 | 制約 |
|---|---|---|
| VPC Peering | 少数 VPC 間の直接双方向接続 | Peered NAU 上限128,000（→512,000）、CIDR 重複不可、非推移的 |
| Transit Gateway | 多数の VPC、on-prem、中央検査 | TGW table 合計、VPC static route、pair ごとの attachment、throughput を個別に数える |
| PrivateLink | 特定 service を一方向に公開 | Endpoint 費用、provider／consumer の継続運用 |
| **VPC Lattice** | CIDR 重複の use case を含む application service／resource 接続 | PrivateLink／NAT などの代替と protocol、auth、cost を比較 |
| 同一 VPC の local routing | 同じ trust zone 内で、同じ VPC を共有できる resource | Route／DNS／IP の障害を共有 |

### VPC Lattice の制約

Lattice は、実際の制約の大きさよりも簡単なものとして説明されることがあります。

| 項目 | 値 | 影響 |
|---|---|---|
| VPC あたりの service network association | **1つのみ** | 複数 network には service-network-type VPC endpoint が必要 |
| **Lattice service の最大 connection lifetime** | **10分** | Reconnect／retry／idempotency をテストし、resource connection と区別する |
| Lattice service の idle timeout | 既定60秒（60～600秒） | |
| Lattice resource の idle timeout | 350秒。Connection lifetime の上限なし | TCP resource の制約は少ない |
| AZ あたり service ごとの bandwidth／RPS | 10 Gbps／10,000 RPS（増加可能） | |
| Service あたり listener／listener あたり rule | 2／10 | |
| Region あたり service network | 50 | |
| MTU | 8,500 byte | |

Service と resource では長時間接続の扱いが異なるため、別々に評価してください。Service の10分 lifetime と、resource の350秒 idle timeout は同じ制約ではありません。HTTP／HTTPS listener は WebSocket をネイティブにサポートしません。TLS listener または Lattice resource が代替経路になります。Protocol、再接続、SNI、認可、負荷を検証してから選択してください。

## 9. East-West 検査の選択肢

| 選択肢 | 設定 |
|---|---|
| 分散 policy 制御 | SG／NACL／route／NetworkPolicy + Flow Logs |
| VPC ごとの分散 firewall | 各 VPC に独立した firewall |
| 中央 TGW 検査 | Transit Gateway 経路上の traffic をまとめて検査 |
| **Hybrid** | Trust zone 内は分散、trust zone 間／規制経路は中央で検査 |

Shared VPC の log 所有者、access、retention、重複費用を文書化してください。Owner と participant の log を中央収集できます。Participant の log を禁止することは前提条件ではありません。

## 次へ

VPC の境界を定めた後に残るのは、その上に data と security の境界をどう設計するかです → [Data and Security Boundaries](./05-data-security-boundaries.md)

## 参考資料

- [VPC quota](https://docs.aws.amazon.com/vpc/latest/userguide/amazon-vpc-limits.html)
- [Shared VPC owner／participant の責任](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-share-limitations.html)
- [共有 subnet における対応 service](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
- [共有 subnet の AZ ID](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html)
- [Security Group の共有](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-sharing.html)
- [Security Group rule](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)
- [Firewall Manager の共通 SG policy](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-common.html)
- [Firewall Manager SG audit policy](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-audit.html)
- [Regional NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html)
- [TGW quota](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html)
- [Transit Gateway の概要](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-transit-gateways.html)
- [TGW 接続の Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tgw-firewall.html)
- [Network Firewall と非対称 routing](https://docs.aws.amazon.com/network-firewall/latest/developerguide/asymmetric-routing.html)
- [VPC Lattice quota](https://docs.aws.amazon.com/vpc-lattice/latest/ug/quotas.html)
- [VPC Lattice の概要](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [PrivateLink 対応 service](https://docs.aws.amazon.com/vpc/latest/privatelink/aws-services-privatelink-support.html)
- [VPC Peering](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html)
- [VPC 接続方法の whitepaper](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/amazon-vpc-to-amazon-vpc-connectivity-options.html)
- [中央 VPC 検査](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/centralized-network-security-for-vpc-to-vpc-and-on-premises-to-vpc-traffic.html)
- [Route 53 Profiles](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles.html)
- [Route 53 Resolver の hybrid DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [TGW route propagation FAQ](https://aws.amazon.com/transit-gateway/faqs/)
- [ENIConfig label の対応付け](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)
- [Lattice listener の protocol](https://docs.aws.amazon.com/vpc-lattice/latest/ug/listeners.html)
