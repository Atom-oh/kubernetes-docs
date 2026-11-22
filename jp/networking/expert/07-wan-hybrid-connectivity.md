# 07. WANおよびハイブリッド接続の設計

> **最終更新日**: 2026年11月19日
> **ラボの範囲**: 設計レビュー（机上確認）のみ。このワークブックでは、回線、VPN、Direct Connect接続、Transit Gatewayは作成しません。
> **検証状況**: AWS Direct Connect、Site-to-Site VPN、Transit Gatewayのユーザーガイド、および引用したRFCを確認しました。この章の執筆中に接続を**設定または測定することはありませんでした**。

このワークブックを終えると、オンプレミスのサイトとAWSリージョン間で**各方向の経路を予測**し、リンク障害時に次の経路を選ぶルール、その切り替えにかかる時間、そして縮小するもの（帯域幅、MTU）を根拠とともに説明できるようになります。

まず[Routing Policy and Measured Convergence](02-routing-policy-convergence.md)を完了してください。この章ではLOCAL_PREF、AS_PATH、MED、コミュニティの意味を扱います。この章で問うのは、AWSがそれらを**どこまで**尊重するかだけです。[Network Fundamentals Part 5: WAN Types](../../basics/06-network-fundamentals-part5.md#wan-types)で回線の種類を、[Part 5: NAT, PAT and CGNAT](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat)でNAT/CGNATを復習してください。

**準備状況:** アカウントも回線も必要ありません。すべての課題は、この章の表と公式ドキュメントに照らして評価します。同じ設計を実際に構築すると、Direct Connectポート、VPN接続、Transit Gatewayアタッチメント、データ転送の料金が発生します。**その費用とリソースのクリーンアップは、学習者自身の責任です**。既存の承認済みラボアカウント以外でリソースを作成しないでください。

## 1. 答えを探す問いを持って読む

試験範囲は、読むべき箇所を決めるためだけに使います。数値と動作は、最初の列に記載した公式ドキュメントに基づきます。

| 読む資料 | 対応する試験範囲 | 自分の言葉で答える問い |
|---|---|---|
| [MEF 70.2](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/)、[Cisco Catalyst SD-WAN High Availability guide](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html) | ENCOR 350-401 アーキテクチャ: SD-WANのコントロールプレーンとデータプレーンの要素 | オーバーレイのコントロールプレーンに到達できなくなると、データトンネルはどうなりますか？ |
| [Site-to-Site VPN tunnel options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html)、[routing options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html) | ANS-C01 ドメイン1 ネットワーク設計、ドメイン2 ネットワーク実装 | AWSは2つのトンネルのどちらを使い、何がその選択を変えますか？ |
| [Direct Connect routing policies and BGP communities](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html) | ANS-C01 ドメイン1および2 | 2つのVIFから同じプレフィックスが広告された場合、AWSはどの順序で比較しますか？ |
| [How Transit Gateway works](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html) | ANS-C01 ドメイン1および2 | 同じCIDRがDXとVPN経由で届いた場合、どちらが優先され、AS_PATHは関係しますか？ |
| [Direct Connect quotas](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html)、[VPN quotas](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html)、[TGW quotas](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html) | ANS-C01 ドメイン1 | 設計が最初に突き当たる制限はどれですか？帯域幅、経路数、MTUのどれですか？ |
| [RFC 5880 (BFD)](https://www.rfc-editor.org/rfc/rfc5880.html)、[RFC 7296 (IKEv2)](https://www.rfc-editor.org/rfc/rfc7296.html) | プロトコルの原則 | 障害検知時間を求める際に掛け合わせる2つの値は何ですか？ |

読み終えたら、サイト、回線、AWSコンポーネントを描き、**BGPセッション**と、パケットが実際に通過する**リンク**を異なる線種で示してください。[ワークブック02](02-routing-policy-convergence.md)で見たように、セッションがあるからといってデータがその経路を流れるとは限りません。以下のDirect Connect gatewayは、その典型例です。

## 2. アンダーレイとオーバーレイ

WAN設計を2つのレイヤーに分けて記録します。**アンダーレイ**はパケットを実際に運ぶ回線（MPLS、インターネットアクセス、Direct Connect）です。**オーバーレイ**はその上に構築するトンネルとポリシー（IPsec VPN、SD-WAN）です。オーバーレイでアンダーレイの遅延、損失、共有物理経路を変えることはできません。同じ管路内の2回線にトンネルを1つずつ設けても、障害点は1つのままです。

| モデル | コントロールプレーン（経路を決めるもの） | データプレーン（パケットが通るもの） | 設計で確認すること |
|---|---|---|---|
| MPLS L3VPN | プロバイダーのPEが顧客の経路をVRFに分離し、BGPで交換する。CE–PE間では静的ルート、OSPF、BGPなどを使用 | プロバイダーのMPLSネットワーク。顧客にラベルは見えない | CE–PE間のプロトコル、プロバイダーのSLA、他キャリアとの物理的な分離 |
| インターネット + IPsec | 両端のエンドポイントが、トンネル内の静的ルートまたはBGPを使って決定 | パブリックインターネット上のESP、ベストエフォート | トンネル数、NATトラバーサル、アルゴリズム依存のMTU |
| SD-WAN | 中央コントローラーがポリシーと経路を配布 | 複数のアンダーレイを同時に利用するWANエッジ間のIPsecトンネル | コントローラーに到達できない場合の動作、トンネルごとの経路測定、アプリケーションごとのポリシー |

**SD-WANをコントロールプレーンとデータプレーンの観点から読む:** MEF 70.2では、SD-WANサービスを、その下にあるアンダーレイ接続サービスとは分けて定義しています。また、サイト間トンネル（TVC）とアプリケーションフローごとのポリシーを、別々の属性として定義しています（用語は[Part 5](../../basics/06-network-fundamentals-part5.md#wan-types)を参照）。Cisco Catalyst SD-WANでは、SD-WAN Controllerがコントロールプレーンをオーケストレーションし、OMPピアリングセッションを介して制御情報を交換します。Validatorはデバイスを認証し、Controllerとルーター間の制御接続をオーケストレーションします。データはルーター間のIPsec接続を通り、BFDがそれらの接続上で自動的に実行されて障害を検出します。したがって、「SD-WANは障害をすばやく検出する」というのは、**データトンネル上のBFD**に関する説明です。コントローラーの冗長化は別の設計項目です。

AWSでは、VPC内のSD-WANアプライアンスが、Connectアタッチメント経由のBGPでTransit Gatewayとピアリングします。Connectピア1つ（GREトンネル）は最大5 Gbpsを運び、1つのアタッチメントには最大4つのピアを設定できます。この章の演習ではConnectを使いませんが、セクション8の帯域幅比較には含めます。

## 3. IPsec Site-to-Site VPN

**定義:** AWS Site-to-Site VPN接続には**2つのトンネル**があり、それぞれ固有のパブリックIPアドレスを持ち、異なるAvailability Zoneで終端します。冗長性のため両方を設定してください。1つのトンネルが利用できなくなると（メンテナンス中など）、その接続のもう一方のトンネルにトラフィックが自動的に切り替わります。

**動作:**

- **IKEバージョン:** トンネルではIKEv1とIKEv2を許可できます。AWSはIKEv2を強く推奨しており、デバイスがIKEv2に対応していない場合に限りIKEv1を使用します。
- **方向ごとのトンネル利用:** オンプレミスからAWSへのトラフィックは両方のトンネルを使用します。AWSからオンプレミスへのトラフィックは一方のトンネルを優先し、AWS側の障害時にもう一方へフェイルオーバーするため、カスタマーゲートウェイは**非対称ルーティングを許可する必要があります**。仮想プライベートゲートウェイ（VGW）では、ゲートウェイのすべてのVPN接続を通じて1つのトンネルが送信経路として選択され、ECMPはサポートされません。
- **静的ルーティングとBGP:** デバイスがBGPに対応している場合は、動的ルーティングを選択してください。BGPの活性確認が2つ目のトンネルへのフェイルオーバーに役立つため、AWSはBGP対応デバイスを推奨しています。BGPを選択した場合、静的ルートも指定することはできません。
- **ECMP:** Transit Gateway上のVPNは、**動的ルーティングの場合に限り**トンネルを集約してECMPを利用できます。静的ルーティングのVPNはECMPをサポートしません。
- **帯域幅:** 標準トンネルは最大1.25 Gbps（最大140,000 PPS）を運びます。Large Bandwidth Tunnelは最大5 Gbpsを運びますが、Transit GatewayまたはCloud WANにアタッチされたVPNでのみ利用でき、両方のトンネルで同じ帯域幅設定を使用する必要があり、Accelerated VPNとは併用できません。
- **活性確認:** Dead Peer Detectionのタイムアウトは30秒以上で、タイムアウト時のアクションは`Clear`（IKEセッションを終了し、トンネルを停止して経路をクリア）、`None`、または`Restart`です。AWS Knowledge Centerでは、VPNのBGPホールドタイムのデフォルト値として30秒が示されています。
- **NATの背後にあるカスタマーゲートウェイ:** NATの背後にあるゲートウェイではNATトラバーサル（NAT-T、RFC 3948）を使い、ESPをUDPでカプセル化します。セクション7のMTU表に示すとおり、同じアルゴリズムでもNAT-Tを有効にするとMTUが下がります。CGNATの背後にあるブランチは、まず着信セッションを受け付けることができません（[Part 5](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat)を参照）。そのため、そのブランチからトンネルを開始する設計にしてください。

**実環境での注意:** 「トンネルが2つあるので冗長化済み」と報告してはいけません。2つのトンネルで冗長化されるのはAWSエンドポイントです。同じカスタマーゲートウェイとインターネット回線を共有している場合、それら2つが単一障害点です。顧客側の冗長性を確保するには、2つ目のカスタマーゲートウェイと2つ目のVPN接続を追加してください。

## 4. Direct Connect

**定義:** Direct Connectは、標準的なイーサネット光ファイバーケーブルを使って、Direct ConnectロケーションにあるAWSルーターとネットワークを接続します。VPCやパブリックAWSサービスに到達するため、接続上に**仮想インターフェイス**（VIF）を作成します。経路上のインターネットサービスプロバイダーを経由しません。デバイスは802.1Q VLAN、BGP、BGP MD5認証をサポートしている必要があります。

**接続タイプ:**

| タイプ | 速度 | VIF | 備考 |
|---|---|---|---|
| Dedicated | 1、10、100、400 Gbps | パブリック/プライベートVIFを最大50個、さらにトランジットVIFを最大4個、合計51個（増加不可） | シングルモードファイバー。ポート速度ごとにトランシーバー規格が固定 |
| Hosted | パートナーがプロビジョニングする50 Mbps～25 Gbps | 1個（増加不可） | 1 Gbps以上を提供するのは条件を満たすパートナーのみ。25 Gbpsを利用できるのは100 Gbpsポートがある場合のみ。AWSがトラフィックを制限し、超過分をドロップ |

**VIFのタイプ:**

- **プライベートVIF:** プライベートIPを使ってVPCに接続します。VGWに直接アタッチすると、同じリージョン内の1つのVPCに接続できます。Direct Connect gatewayにアタッチすると、複数アカウント、複数リージョンにまたがるVGWに接続できます。
- **パブリックVIF:** パブリックIPを使ってパブリックAWSサービスに接続します。広告するパブリックプレフィックスは自分が所有するものでなければならず、AWSは着信トラフィックの送信元が広告済みプレフィックスのいずれかであることを確認するためにフィルタリングします。
- **トランジットVIF:** Direct Connect gatewayに関連付けられたTransit Gatewayに、速度を問わず、Dedicated接続またはHosted接続から接続します。

**Direct Connect gateway:** VGW、Transit Gateway、またはCloud WANコアネットワークに関連付けるグローバルリソースです。AWSはこれを、データトラフィック経路の外部で動作する**BGPルートリフレクターの分散セット**として説明しています。そのため、単一障害点にはなりません。ワークブック02のルートリフレクターと同様に、経路を反映するものであり、パケットを運ぶものではありません。1つのgatewayは、最大20個のVGW、6個のTransit Gateway、30個のプライベートまたはトランジットVIFをサポートします。

**経路制限:** これらの制限は直接サービス停止につながるため、設計表に記載してください。

- プライベートVIFまたはトランジットVIF経由でオンプレミスからAWSへ向かう場合、1つのBGPセッションで、デフォルトではIPv4とIPv6の経路をそれぞれ100件受け入れます。プレフィックス制御を使って、それぞれ1,000件まで引き上げられます。**割り当て数を超える経路を広告すると、BGPセッションはidleになり、DOWNとして報告されます。**
- パブリックVIFのBGPセッションは1,000件の経路を受け入れます。
- トランジットVIF経由でAWSからオンプレミスへ向かう場合、各Transit Gatewayが広告するプレフィックスは、IPv4とIPv6を合わせて最大200件です。

**許可プレフィックス:** Transit Gatewayとの関連付けでは、Direct Connect gatewayは入力した許可プレフィックスを**そのまま**広告します。VPC CIDRが`10.20.0.0/16`で許可プレフィックスが`10.0.0.0/8`の場合、オンプレミスが受け取るのは`10.0.0.0/8`だけです。一方、VGWとの関連付けでは、許可プレフィックスは同じか、より小さいCIDRを通過させるフィルターとして機能します。セクション6の落とし穴はここから始まります。

<a id="dx-lag"></a>

**LAG:** リンクアグリゲーショングループはLACPを使って、1つのDirect Connectエンドポイントにある複数の接続を、1つの論理接続に束ねます。ルールは次のとおりです。

- すべての接続がDedicatedで、同じ帯域幅でなければなりません。
- LAGには、100 Gbps未満の接続を最大4つ、または100 Gbpsもしくは400 Gbpsの接続を最大2つ収容できます。
- すべての接続が同じDirect Connectエンドポイントで終端しなければなりません。マルチシャーシLAG（MLAG）はサポートされません。
- すべての接続がアクティブ/アクティブで動作します。LAGにはminimum-links属性（デフォルトは0）があり、設定すると稼働中の接続数が指定数を下回った場合にLAG全体を停止します。これにより、残りの接続への過負荷を防げます。

LAGは**容量**を増やしますが、同じロケーションにある同じデバイスで終端するため、ロケーション障害には耐えられません。Part 5で触れたように、1つのフローが1つのメンバーリンクの帯域幅を超えることはできません。ロケーション冗長性はResiliency Toolkitのモデルを使って設計します。**Maximum resiliency**は99.99%のSLA、**High resiliency**は99.9%のSLAを目標とし、いずれもDirect Connect SLAの全要件を満たす場合に限ります。**Development and test**では、1つのロケーション内の別々のデバイスに接続を分散します。

**MACsec:** 選択されたロケーションの10、100、400 Gbpsの**Dedicated**接続でサポートされます。1 Gbps Dedicated接続とすべてのHosted接続ではサポートされません。これはホップごとのL2暗号化であるため、デバイスがAWSデバイスと直接L2隣接している必要があり、ラストマイル区間はL2に対して透過的でなければなりません。サポートされるのは256ビット鍵のみで、100/400 Gbpsの接続では拡張パケット番号（XPN）が必要です。LAGでは、常にすべてのリンクで単一のMACsec鍵が使われます。

## 5. Transit Gateway

**定義:** Transit Gatewayは、VPCとオンプレミスネットワーク間のトラフィックを扱うリージョナル仮想ルーターです。アタッチメントはパケットの送信元にも宛先にもなります。VPC、VPN接続、VPN Concentrator、Direct Connect gateway、Connectアタッチメント、ピアリング接続をアタッチできます。

**ルートテーブルのルール:**

- アタッチメントは**1つの**ルートテーブルに関連付けられ、**複数の**ルートテーブルに伝播できます。伝播された経路はフィルタリングできません。
- 動的ルーティングのVPNは、関連付けられたルートテーブルの経路をBGP経由でカスタマーゲートウェイに広告します。Direct Connect gatewayアタッチメントは許可プレフィックスを広告します。
- 同じ宛先の場合、静的ルートは伝播ルートより優先され、伝播ルートはテーブルに表示されません。
- Transit Gatewayに表示されるのは優先経路だけです。同じ経路がDXとVPN経由で届いた場合、テーブルにはDX経路が表示されます。VPN経路が表示されるのは、DX経路が広告されなくなった後だけです。
- ピアリングアタッチメントは静的ルートのみをサポートします。

**経路評価の順序:** まず最長一致の経路が優先されます。異なるアタッチメントタイプから同じCIDRが届いた場合の優先順位は次のとおりです。

1. 静的ルート（例: Site-to-Site VPNの静的ルート）
2. システムルート（1:1 NAT用）
3. プレフィックスリスト参照ルート
4. VPC伝播ルート
5. Direct Connect gateway伝播ルート
6. Transit Gateway Connect伝播ルート
7. プライベートDirect Connect経由のSite-to-Site VPN伝播ルート
8. Site-to-Site VPN伝播ルート
9. Site-to-Site VPN Concentrator伝播ルート
10. Client VPN伝播ルート
11. Transit Gatewayピアリング（Cloud WAN）伝播ルート

**同じアタッチメントタイプ**から同じCIDRが届いた場合に限り、BGP属性が比較されます。AS_PATHが短い経路、次にMEDが小さい経路、サポートされている場合はiBGPよりeBGPが優先されます。MEDを付けずに広告された経路には、Direct Connectアタッチメントではデフォルト値の0が、VPNおよびConnectアタッチメントではデフォルト値の100が設定されます。異なるアタッチメントタイプ（例: VPNとVPC）間ではECMPはサポートされません。代わりに、上記の評価順序で1つの経路が選ばれます。

**MTUと帯域幅:** VPC、Direct Connect、Connect、ピアリングアタッチメント間のトラフィックのMTUは8500バイト、VPN経由のトラフィックは1500バイトです。Transit GatewayはすべてのパケットにMSSクランプを適用します。Path MTU Discoveryは、VPCおよびConnectアタッチメントから入るトラフィックでのみサポートされ、VPN、Direct Connect、ピアリングアタッチメントではサポートされません。VPCアタッチメントとDirect Connect gatewayの帯域幅は、Availability Zoneごと、方向ごとに最大100 Gbpsです。

<a id="failover-design"></a>

## 6. フェイルオーバー設計: DXをプライマリ、VPNをバックアップにする

このセクションは**方向ごとに**読んでください。オンプレミスからAWSへの経路は**お客様のルーターのポリシー**が選択し、AWSからオンプレミスへの経路は**AWSの評価順序**が選択します。片方向だけを変更すると経路が非対称になり、ステートフルファイアウォールが応答パケットをドロップすることがあります。

![ハイブリッドフェイルオーバーのアニメーション。① オンプレミスのルーター（AS 65010、10.10.0.0/16）は、DX経由とVPN経由でVPC 10.20.0.0/16への2つのBGP経路を学習し、LOCAL_PREF 200のDX経路を選び、DX接続の802.1Q VLAN 101（トランジットVIF）経由で10.20.1.10宛てのパケットを送信します。② DXロケーションを越えたパケットは、宛先を変えずにTransit Gatewayに到達し、TGWルートテーブルによってVPCアタッチメントへ転送されます。DX gatewayはBGP経路を反映するだけで、データ経路にはありません。③ DXリンクが切断されます。300 ms間隔で3回応答がないことをBFDが検出すると、BGPセッションがダウンし、両側でDX経路が撤回され、オンプレミスの最適経路がLOCAL_PREF 100のVPNトンネルに切り替わります。④ 次のパケットはVPN経路を通ります。IPsecがESPと外側IPヘッダー（送信元203.0.113.10、宛先198.51.100.10）を追加し、パケットはインターネットを通過します。⑤ Transit GatewayのVPNアタッチメントでESPが取り除かれ、元の10.20.1.10宛てのパケットがVPCへ転送されます。DX経路がなくなっているため、戻りのトラフィックもVPN伝播ルートを使います。](../../.gitbook/assets/en-networking-expert-07-wan-hybrid-connectivity-anim-0.svg)

### AWSからオンプレミスへ: AWSが選ぶ経路

**Transit Gatewayでは**、セクション5の評価順序がそのまま適用されます。

1. **最長プレフィックスが最初に優先されます。** オンプレミスがVPN経由で`10.10.1.0/24`を、DX経由で`10.10.0.0/16`を広告した場合、`10.10.1.0/24`宛てのトラフィックはVPNを通ります。DXをプライマリにするには、両方の経路で**同一のプレフィックス**を広告してください。
2. **同じCIDRでは、アタッチメントタイプがAS_PATHより優先されます。** DX gateway伝播ルートは常にVPN伝播ルートより優先されるため、VPNの広告にAS_PATHを追加しても、DXとVPNの選択には影響しません。逆に、VPN上の**静的ルート**はDX伝播ルートより優先され、気付かないうちにVPNがプライマリになります。バックアップVPNはBGPを使って構築してください。
3. **BGP属性は、同じタイプ内でのみ比較されます。** たとえば、複数のDX VIF間、または複数のVPN接続間で比較されます。

**VGWでは**、優先順位が異なります。同じプレフィックスの場合、Direct ConnectのBGP経路がVPNの静的ルートより優先され、VPNの静的ルートはVPNのBGP経路より優先されます。VPNのBGP経路間では、AS_PATHが短いものが優先され、最初のASが一致する場合はMEDが小さいものが優先されます。この2つの優先順位を混同しないでください。

**複数のDX VIF間では**、AWSはプライベートVIFとトランジットVIFの経路を次の順序で比較します。

| 順序 | 基準 | 設計での使い方 |
|---|---|---|
| 1 | 最長プレフィックス | より具体的な経路でアクティブ/パッシブを表現する |
| 2 | ローカルプリファレンスコミュニティ | `7224:7300`（高）、`7224:7200`（中）、`7224:7100`（低）。標準コミュニティを使用し、AS_PATHより先に評価されます。ルートターゲットなどの拡張コミュニティは優先順位の評価対象ではなく、削除される場合があります |
| 3 | AS_PATH長 | プレフィックスとローカルプリファレンスが等しい場合に追加する |
| 4 | MED | 優先度は最低。AWSはこれに依存することを推奨していません |
| 同順位 | ECMP | AS_PATH長と属性が同じ場合、VIF間で負荷分散する |

コミュニティが指定されていない場合、AWSリージョンは**そのリージョンに関連付けられた**Direct Connectロケーションを優先します。アクティブ/アクティブにする場合は、すべてのVIFに同じコミュニティ（例: `7224:7200`）を設定します。アクティブ/パッシブにする場合は、プライマリVIFに`7224:7300`、バックアップに`7224:7100`を設定します。これらのコミュニティは、オンプレミスへ**戻る**トラフィックの優先順位を設定します。

**ループ防止:** AS_PATHにDirect Connect ASN `7224`が2回以上含まれる経路は、AWSによってループと見なされ、インストールされません。これは、一方のVIFからAWS経由で学習した経路を別のVIFから再広告したときに起こります。AWSから学習した経路は、AWSへの広告対象から除外してください。

### オンプレミスからAWSへ: ルーターが選ぶ経路

AWSは、同じVPC経路をDX経由（許可プレフィックス）とVPN経由（TGWルートテーブル内の経路）で広告します。お客様のルーターは、ワークブック02のBGP選択ルールを使ってこれらを比較します。DXから学習した経路に高いLOCAL_PREFを設定すると、DXがプライマリになります。アニメーションにあるLOCAL_PREF 200/100は、このポリシーを示しています。

**許可プレフィックスの落とし穴:** VPNがTGWルートテーブルから`10.20.0.0/16`を広告する一方、許可プレフィックスが`10.0.0.0/8`に集約されていると、ルーターは**より長いVPNプレフィックス**を選びます。LOCAL_PREFが比較されるのは同一プレフィックスの経路間だけであり、この問題を解決できません。許可プレフィックスの長さをVPN側に合わせるか、ルーター上でVPNから学習した経路も同じ方法で集約してください。

### 検知時間の予算

| メカニズム | 値 | 情報源の性質 |
|---|---|---|
| DX上のBFD | 非同期BFDはAWS側で自動的に有効になりますが、ルーターで設定した場合にのみ有効になります。最小間隔は300 ms、乗数は3 | Direct Connect FAQおよびユーザーガイド |
| BFDなしのDX BGP | キープアライブがない状態が90秒続くとセッションがダウンする | AWS Knowledge Center |
| VPN BGP | デフォルトのホールドタイムは30秒 | AWS Knowledge Center |
| VPN DPD | 30秒以上。タイムアウト時のアクションは`Clear`、`None`、または`Restart` | VPNユーザーガイド |

BFDが障害を検出すると、ホールドタイムの満了を待つのではなく、BGPネイバー関係がすばやく解除されます。RFC 5880によると、BFDの検知時間はリモート側の乗数とネゴシエートされた間隔の積です。したがって、300 ms × 3は約0.9秒です。しかし、**検知時間は復旧時間ではありません。** 復旧には経路の撤回と伝播、両ルーターでのFIB更新、逆方向の切り替えが加わりますが、AWSはそれらの固定値を公表していません。設計書では検知値を引用し、それ以外を**実測するまでは仮定**と明記してください。測定点にはワークブック02の項目（アクション時刻、最初の変化、FIBの変化、継続的な復旧）を使います。

## 7. トンネルを通るMTUとMSS

| セグメント | MTU | 備考 |
|---|---|---|
| Site-to-Site VPN | 最大1446バイト、MSS 1406 | ジャンボフレームとPath MTU Discoveryは利用不可。一部のアルゴリズムとNAT-Tではさらに小さくなる |
| プライベートVIF | 1500または9001 | リンクレイヤーフレームは1522または9023バイト |
| トランジットVIF | 1500または8500 | Transit Gateway上のジャンボフレームは8500のみをサポート |
| Transit Gateway | VPC、DX、Connect、ピアリング間は8500、VPN経由は1500 | すべてのパケットでMSSクランプを実施。PMTUDはVPCとConnectからの入力のみ |

AWSが推奨するVPNのMTU/MSS値の例（IPv4 MSS）:

| 暗号化 | 完全性 | NAT-T | MTU | MSS |
|---|---|---|---|---|
| AES-GCM-16 | 該当なし | 無効 | 1446 | 1406 |
| AES-GCM-16 | 該当なし | 有効 | 1438 | 1398 |
| AES-CBC | SHA1/SHA2-256 | 無効 | 1438 | 1398 |
| AES-CBC | SHA2-512 | 有効 | 1406 | 1366 |

**動作:**

- AWSは、カスタマーゲートウェイが**暗号化する前に**フラグメント化することを推奨しています。VPNは転送前にフラグメントを再構成するため、再構成後のパケットが次のセグメント（例: Direct Connect）に収まることも確認してください。
- VIFをジャンボMTUに変更すると、基盤となる接続が更新され、その接続上のすべてのVIFで最大30秒の通信中断が起きる場合があります。メンテナンス時間帯に変更してください。
- 2つのプライベートVIFが異なるMTUで同じ経路を広告する場合、またはSite-to-Site VPNが同じ経路を広告する場合、MTU 1500が使われます。

**設計上のポイント:** フェイルオーバー設計で重要なのは、**バックアップ経路のMTUです**。大きなMSSでDX経由に確立したTCP接続がVPNへ切り替わると、PMTUDをサポートしないセグメント上で、大きなDF設定済みパケットが通知なくドロップされることがあります。この演習では、2つの選択肢を比較してください。選択したアルゴリズムのVPN値に合わせて、ルーターでハイブリッドフローのMSSをクランプするか、VPNをバックアップにする間はVIFを1500に保ちます。

## 8. 帯域幅、遅延、コストのトレードオフ

| 接続 | 帯域幅（公式上限） | 遅延と品質 | 冗長化の単位 | コスト要素 |
|---|---|---|---|---|
| DX Dedicated | LAGで束ねて1/10/100/400 Gbps | インターネットサービスプロバイダーを経由しない専用経路 | 接続、デバイス、ロケーション（Resiliency Toolkitのモデル） | ポート時間、アウトバウンドデータ転送 |
| DX Hosted | 50 Mbps～25 Gbps | パートナーネットワークを経由。AWSが契約レートに制限 | Hosted接続ごと、パートナーネットワーク | 同じAWS料金要素にパートナー料金を加算 |
| VPN標準トンネル | 最大1.25 Gbps、トンネルごとに140,000 PPS | インターネット経路、ベストエフォート | 2つのトンネル（AWS側）。カスタマーゲートウェイと回線は別 | 接続時間、アウトバウンドデータ転送、トンネルごとのパブリックIPv4 |
| VPN Large Bandwidth Tunnel | トンネルごとに最大5 Gbps（TGWとCloud WANのみ） | 標準と同様。MTUの上限も同じ | 上記と同じ | 別料金の接続時間 |
| TGW上のVPN ECMP | 動的ルーティングの複数トンネルの合計 | フロー単位の分散。1つのフローは1つのトンネルが上限 | トンネルごと、接続ごと | VPN料金に加え、TGWアタッチメント時間と処理GB単位の料金 |
| Connect（SD-WAN） | ピアごとに5 Gbps、アタッチメントごとに4ピア | 基盤となるトランスポート（VPCまたはDX）に従う | ピアごと、アタッチメントごと | TGWアタッチメント時間に加え、トランスポートアタッチメントの処理料金 |

Transit Gatewayでは、アタッチメント時間と、VPC、Direct Connect、VPNアタッチメントから処理したデータのGB単位で料金が発生します。単価はリージョンや時期によって変わるため、設計では**コスト要素**だけを記録してください。金額は確認する当日に料金ページで算出します。

## 9. 設計演習: 2つのサイトと1つのリージョン

この演習はリソースを作成しない机上確認です。結果には**設計レビュー**と明記してください。

**入力:**

| ロケーション | アドレスとASN | 接続 |
|---|---|---|
| Site A（本社データセンター） | `10.10.0.0/16`、AS 65010 | 2つの異なるDXロケーション（DX-1、DX-2）にそれぞれ1つ、10 Gbps Dedicated接続を設置し、それぞれにトランジットVIFを1つ設定。インターネット回線は1つ、カスタマーゲートウェイは1つ |
| Site B（ブランチ） | `10.30.0.0/16`、AS 65030 | 異なるキャリアのインターネット回線を2つ設置し、回線ごとにカスタマーゲートウェイとVPN接続を1つずつ設定。DXなし |
| リージョン | VPC `10.20.0.0/16`、Transit Gateway（Amazon ASNの例: 64512）、Direct Connect gateway（ASNの例: 64513） | DX gatewayと3つのVPNを同じTGWにアタッチ |

Site AからSite Bへのトラフィックは既存のMPLSサービスを利用するため、対象外です。すべてのVPNでBGP、IKEv2、AES-GCMを使い、NAT-Tは無効と仮定します。

**サービスレベル目標:** これらは学習者の設計目標であり、AWS SLAではありません。

- Site A → VPC: いずれか1つのDX接続、デバイス、ロケーションの障害が起きても、少なくとも5 Gbpsを維持し、障害検知から5秒以内の双方向データ経路の復旧を目指します。両方のDX接続が失敗した場合は、VPN経由の縮退運用を許容します。
- Site B → VPC: 回線またはカスタマーゲートウェイのいずれか1つが障害になっても接続を維持します。BGPホールドタイム内の切り替えを許容します。

**課題:**

1. **広告テーブル:** 各経路について、誰がどのプレフィックスを広告するかを記録します。DX gatewayの許可プレフィックス、各VPNが受信するTGWルートテーブルの経路、Site AおよびSite BがAWSに広告する経路を記録してください。クォータ（DX BGPセッションあたりデフォルト100件、TGWあたり200件）と照合します。
2. **ポリシーテーブル:** Site AのLOCAL_PREF（DX-1、DX-2、VPN）、DX VIFのローカルプリファレンスコミュニティ、TGWルートテーブルの関連付けと伝播を設定します。5 Gbpsの目標に基づき、2つのDX接続をアクティブ/アクティブにするか、アクティブ/パッシブにするかを決めてください。
3. **経路予測:** 以下の各シナリオについて、Site A → VPC、VPC → Site A、Site B → VPC、VPC → Site Bの経路と、それぞれの経路を選ぶ**ルールの段階**（例: 「TGW評価順序のステップ5、DX gateway伝播」）を記録します。
4. **時間の予算:** 各シナリオについて、検知メカニズムとその値を記録し、実測するまでは仮定とする項目を列挙し、目標を達成したかどうかを判定します。
5. **MTUの判断:** トランジットVIFのMTUとSite AのMSSクランプ値を、理由とともに選んでください。

| シナリオ | Site A → VPC | VPC → Site A | 適用ルール | 検知 | 残存帯域幅 | 判定 |
|---|---|---|---|---|---|---|
| 通常時 | | | | | | |
| DX-1接続が失敗 | | | | | | |
| DXロケーション1全体が失敗 | | | | | | |
| DX-1とDX-2が両方失敗 | | | | | | |
| Site AのルーターでBFDが設定されていない状態でDX-1が失敗 | | | | | | |
| Site Bの回線が1つ失敗 | | | | | | |
| DX-1が復旧 | | | | | | |

**レビュー基準:** すべてのセルで、出典ドキュメントにあるルールを少なくとも1つ引用してください。次の点を確認してください。

- 通常時にVPC → Site AがDXを使う理由を、「DXのほうが速い」ではなくTGW評価順序を使って説明しましたか？
- VPNで静的ルートを避けましたか？静的ルートを使った場合、通常時でもVPNが優先されることを確認しましたか？
- 許可プレフィックスとVPNが広告するプレフィックスの長さは同じですか？異なる場合、どちらの方向のトラフィックがVPNに流れますか？
- BFDがないシナリオでは、5秒の目標を達成できない（BGPホールドタイムが90秒）ことを確認しましたか？
- 両方のDX接続がダウンした場合、帯域幅がVPNの上限（標準トンネルあたり1.25 Gbps、ECMP使用時はトンネルの合計）に下がり、1つのフローは1つのトンネルを超えられないと記録しましたか？
- MTUをバックアップ経路に基づいて決めましたか？

## 10. 障害と復旧の観察

実環境がない場合、このセクションでは各判定を確定するために**どの証拠が必要か**を考える練習をします。後日、既存の承認済み環境でシナリオを再現できた場合は、以下の証拠を収集してください。

| レイヤー | 確認するもの | その証拠だけでは確認できないこと |
|---|---|---|
| お客様のルーターのBGPテーブル | 2つの候補経路、LOCAL_PREF、最適経路のマーカー | AWS側の戻り経路 |
| お客様のルーターのFIBとパケットキャプチャ | 実際の送信インターフェイス、トンネルインターフェイス上のESP | すべてのアプリケーションフローが成功したかどうか |
| TGWルートテーブル | 単一の優先経路。バックアップVPN経路が表示されるのはDX経路の撤回後 | パケットが実際に通った経路 |
| CloudWatch | VPNの`TunnelState`、DX VIFの`VirtualInterfaceBgpStatus` | データプレーンの損失が始まった時刻と終わった時刻 |
| 送信元を指定したプローブ | 損失区間、継続的な復旧の開始 | 大きなパケットやすべてのポート |

**フェイルバックも障害です。** DXが復旧してBGPが再確立すると、TGWではDX gateway伝播ルートが再び優先され、お客様のルーターではLOCAL_PREFの高いDX経路が再び優先されます。そのため、トラフィックは**自動的に**戻り、再度経路とMTUが切り替わります。不安定なリンクでは経路が繰り返し切り替わることがあります。継続的な復旧の基準（例: 連続した応答と観測時間）を事前に定義してください。ワークブック02と同様に、損失を観測しなかったという結果が意味するのは、サンプリングの分解能では中断を捉えられなかったということだけです。

## 11. 成果物と完了基準

| 成果物 | 完了の基準 |
|---|---|
| トポロジ図 | セッションとデータリンクが区別され、DX gatewayがデータ経路の外に配置されている |
| 広告およびポリシーの表 | 許可プレフィックス、VPNの広告、LOCAL_PREF、コミュニティ、TGWの関連付け/伝播がすべて記録され、クォータと照合されている |
| シナリオ表 | 7つのシナリオすべてについて、双方向の経路、適用ルール、検知値、残存帯域幅、判定が記録されている |
| MTUの判断 | バックアップ経路に基づいて決めたMSS値と、その根拠となる出典表がある |
| 未確定事項の一覧 | 経路伝播やFIB更新時間など、公表された固定値がない項目が、実測するまでは仮定と明記されている |

各方向での経路選択ルール、アタッチメントタイプの優先順位とAS_PATHの関係、許可プレフィックスの落とし穴、検知時間と復旧時間の違い、バックアップ経路がMTUを決める理由を、出典を示して説明できれば完了です。結果の表を[自動化の総合演習](06-automation-capstone.md)の変更レビューに活用し、[Cloud and CNI Design](05-cloud-cni-design.md)でクラウド内の経路に進んでください。組織間のVPC接続オプションについては[Cross-Org VPC Connectivity](../05-cross-org-vpc-connectivity.md)、EKS Hybrid Nodesのネットワーク要件については[Hybrid Nodes Network Configuration](../../eks-hybrid-nodes/02-network-configuration.md)を参照してください。最後に、[クイズ](../../quizzes/networking/expert/07-wan-hybrid-connectivity-quiz.md)に挑戦してください。

## 参考資料

AWS Direct Connect

- [What is Direct Connect?](https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html)（VIFの種類、ネットワーク要件、BFD、料金要素）
- [Direct Connect quotas](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html)
- [Hosted connections](https://docs.aws.amazon.com/directconnect/latest/UserGuide/hosted_connection.html)
- [Virtual interfaces and MTU](https://docs.aws.amazon.com/directconnect/latest/UserGuide/WorkingWithVirtualInterfaces.html)
- [Routing policies and BGP communities](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html)
- [Direct Connect gateways](https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-gateways-intro.html)、[Allowed prefixes interactions](https://docs.aws.amazon.com/directconnect/latest/UserGuide/allowed-to-prefixes.html)
- [Link aggregation groups](https://docs.aws.amazon.com/directconnect/latest/UserGuide/lags.html)、[MAC Security](https://docs.aws.amazon.com/directconnect/latest/UserGuide/MACsec.html)、[Resiliency Toolkit](https://docs.aws.amazon.com/directconnect/latest/UserGuide/resiliency_toolkit.html)
- [Direct Connect FAQ](https://aws.amazon.com/directconnect/faqs/)（BFDのデフォルト、MACsec対応接続）
- [AWS Knowledge Center: Enable BFD for Direct Connect](https://repost.aws/knowledge-center/enable-bfd-direct-connect)（BFDがない場合のBGPホールドタイム90秒）
- [CloudWatch metrics for Direct Connect virtual interface BGP health](https://aws.amazon.com/blogs/networking-and-content-delivery/introducing-cloudwatch-metrics-for-aws-direct-connect-virtual-interface-bgp-health-and-prefix-count/)

AWS Site-to-Site VPN

- [Tunnel options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html)、[Configure tunnel options](https://docs.aws.amazon.com/vpn/latest/s2svpn/tunnel-configure.html)
- [Routing options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html)、[Static and dynamic routing](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-static-dynamic.html)、[Route tables and route priority](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-route-priority.html)
- [Site-to-Site VPN quotas](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html)（帯域幅、PPS、MTU、経路数）
- [Best practices for a customer gateway device](https://docs.aws.amazon.com/vpn/latest/s2svpn/cgw-best-practice.html)（IKEv2、暗号化前のフラグメント化、アルゴリズムごとのMTU/MSS）
- [Monitor VPN tunnels using CloudWatch](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)
- [AWS Knowledge Center: Troubleshoot a VPN tunnel with BGP logs](https://repost.aws/knowledge-center/vpn-bgp-logs-troubleshoot-tunnel)（デフォルトのホールドタイム30秒）
- [AWS VPN pricing](https://aws.amazon.com/vpn/pricing/)

AWS Transit Gateway

- [How AWS Transit Gateway works](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html)（アタッチメント、関連付けと伝播、経路評価順序、ECMP）
- [Transit Gateway quotas](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html)（帯域幅、MTU、MSSクランプ、PMTUD）
- [AWS Transit Gateway pricing](https://aws.amazon.com/transit-gateway/pricing/)

標準規格およびベンダーのドキュメント

- [RFC 5880: Bidirectional Forwarding Detection](https://www.rfc-editor.org/rfc/rfc5880.html)
- [RFC 7296: IKEv2](https://www.rfc-editor.org/rfc/rfc7296.html)、[RFC 4303: ESP](https://www.rfc-editor.org/rfc/rfc4303.html)、[RFC 3948: UDP Encapsulation of IPsec ESP Packets](https://www.rfc-editor.org/rfc/rfc3948.html)
- [RFC 4271: BGP-4](https://www.rfc-editor.org/rfc/rfc4271.html)、[RFC 1997: BGP Communities](https://www.rfc-editor.org/rfc/rfc1997.html)、[RFC 6996: Autonomous System Reservation for Private Use](https://www.rfc-editor.org/rfc/rfc6996.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html)、[RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html)（アドレスの例）
- [MEF 70.2: SD-WAN Service Attributes and Service Framework](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/)
- [Cisco Catalyst SD-WAN High Availability Configuration Guide](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html)

試験範囲（トピックの選択にのみ使用）

- [AWS Certified Advanced Networking - Specialty (ANS-C01) exam guide](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)
- [Cisco 350-401 ENCOR](https://www.cisco.com/site/us/en/learn/training-certifications/exams/encor.html)
