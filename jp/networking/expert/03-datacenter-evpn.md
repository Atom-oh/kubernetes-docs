# 03. データセンターEVPN: 分離とデータプレーンの証拠

> **最終更新日**: 2026年9月15日
> **ラボの境界**: 別途準備し、所有者が管理する破棄可能なLinuxファブリックVM。実稼働ファブリックやクラウドリソースは使わない。
> **検証状況**: 公式ドキュメント、上流トポロジー、FRR CLI／テンプレートソースを確認済み。この執筆時にラボは**実行していない**。

EVPNのBGPセッションが確立していることは観察の出発点であり、ファブリックが正常に動作する証明ではありません。このワークブックでは、VLAN、VNI、VRF、アンダーレイを通るフレーム／パケットを追跡し、分離と復元を実証します。まず[初心者向け8レッスン](../beginner/README.md)と[ルーティングポリシー](02-routing-policy-convergence.md)を完了してください。ブリッジ、neighbor、カーネルルートの証拠を解釈するには、[Linuxネットワークスタックの基礎](../../kernel/02-network-stack.md)を使います。

## 1. アーキテクチャを層ごとに読む

| 主な資料 | ラボに触れる前に用意するもの |
|---|---|
| [netlab EVPNモジュール](https://netlab.tools/module/evpn/) | 選択したデバイスの機能／プロバイダー確認表 |
| [netlabのプラットフォーム対応](https://netlab.tools/platforms/)と[FRRの注意事項](https://netlab.tools/caveats/#frrouting) | コンテナ内のFRRがVMカーネルにも依存する理由の説明 |
| [FRR EVPN](https://docs.frrouting.org/en/latest/evpn.html) | Linux bridge、VXLAN interface、SVI、VRFをEVPNの概念に対応付けた説明 |
| [RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.html)、[RFC 7432](https://www.rfc-editor.org/rfc/rfc7432.html) | カプセル化を図示し、経路識別とインポートポリシーを区別する |
| [RFC 9135](https://www.rfc-editor.org/rfc/rfc9135.html)、[RFC 9136](https://www.rfc-editor.org/rfc/rfc9136.html) | IRBを説明し、プレフィックス広告とホスト広告の違いを説明する |

**VLAN**はローカルのレイヤー2メンバーシップを定義します。アクセスポートのVLANと許可するトランクVLANは同じ設定ではありません。**LACP**はリンクアグリゲーショングループをネゴシエートします。利用可能な帯域はメンバーの状態とハッシュ方法で決まり、1つのフローが全メンバーを使うとは限りません。**STP**はブリッジ構成のループを防ぎます。想定外のブロッキングポートがあれば、EVPN以前の段階で通信が欠ける原因になり得ます。この確認表と併せて[netlab VLAN](https://netlab.tools/module/vlan/)、[LAG](https://netlab.tools/module/lag/)、[STP](https://netlab.tools/module/stp/)も読んでください。選択した小規模ラボではLACPや冗長STPトポロジーを**構築しません**。「正常にテストした」ではなく「未構築」と記録してください。別のファブリックに演習を適用する前に、正しいアクセスポート／トランクメンバーシップ、意図したLAGメンバー、想定されるSTP転送トポロジーを確認してください。

**アンダーレイ**はVTEP間のIP到達性を提供します。テナントアドレスとは独立して、ルーティング、戻り経路、使用可能なMTUが機能する必要があります。**オーバーレイ**はVTEP間でテナントトラフィックを運びます。VXLANでは外側にEthernet／IP／UDP／VXLANヘッダーが追加されます。外側の宛先はリモートVTEPであり、テナントホストではありません。VNIはVXLANヘッダー内の仮想セグメントを示します。VLAN IDはローカルで意味を持ち、そのVNIへのマッピングを検証する必要があります。VLAN IDとVNIが数値的に同じだと決めつけないでください。

## 2. 識別子、経路、転送を区別する

| 概念 | 意味 | 確認する証拠 |
|---|---|---|
| VTEP | カプセル化／カプセル解除のエンドポイント | ローカルアドレス、リモート到達性、VXLAN interface |
| L2VNI／MAC-VRF | ブリッジされたテナントセグメント | VLAN／bridgeマッピング、学習済みリモートMACとVTEP |
| L3VNI／IP-VRF | ルーティングされたテナントコンテキスト | VRFテーブル、トランジットVNI、リモートプレフィックス |
| RD | 重複し得るVPN経路の識別情報を区別する | 経路の生成元にあるRD |
| RT | インポート／エクスポートポリシーに使う拡張コミュニティのメンバーシップ | 広告されたexport RTと、受信側で有効なimport RTの集合 |
| SVI／IRB | ブリッジドメイン境界でのルーティング | ゲートウェイアドレス／MAC、SVIとVRFの関連付け、ルーティングプローブ |

異なるRDでも同じVPNに属することがあります。RDが一致してもメンバーシップは付与されません。RTはパケットファイアウォールではありません。想定外の経路がインポートされれば到達性が生じる場合がありますが、経路が存在するだけでは転送できる証拠になりません。非対称IRBでは、入口側でルーティングし、リモート側が宛先セグメントへブリッジします。参加するゲートウェイには、該当する宛先L2状態が必要です。対称IRBでは、両端がL3VNIを使ってテナントルーティングを行います。BGPでEVPNアドレスファミリーが有効だからといって、対称IRBだと推測しないでください。

| EVPN経路 | このワークブックでの役割 | 経路があっても証明できないこと |
|---|---|---|
| Type 2: MAC／IP広告 | MACを広告し、任意で関連IPも通知する。リモートホスト情報に使う | 広告された全MACが正しいbridgeに登録されたこと |
| Type 3: IMET | ingress replicationなど、BUM配送構築に使う参加情報を通知する | ユニキャストホスト転送やテナントルーティングの成功 |
| Type 5: IPプレフィックス | 特定ホストのMAC広告とは独立してテナントIP到達性を伝える | 受信側がプレフィックスをインポートした、またはVTEPに到達できること |

BUMはbroadcast、unknown unicast、multicastを意味します。VTEPのレプリケーション状態はType 3経路と併せて確認します。グローバルEVPN経路、VNI／VRFごとにインポートされた状態、実際の転送証拠を分けて報告してください。

## 3. 再現可能な上流ラボを選ぶ

[netlabホームページ](https://netlab.tools/)**からリンクされているexamplesリポジトリのリビジョン`7c4fa0dac160d3cc2eac41e11f20b74d083bb896`を使います**。

| 段階 | 上流の正確なパス | 想定するベースライン |
|---|---|---|
| A: L2 | [EVPN/vxlan-bridging](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/vxlan-bridging) | red内のh1↔h2、blue内のh3↔h4。VLAN間ルーティングなし |
| B: L3 | [EVPN/l3vpn](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/l3vpn) | red VRF内でルーティングされるh1↔h2、blue VRF内でルーティングされるh3↔h4。VRF間インポートなし |

どちらも`clab`、2台のスイッチs1／s2、4台のLinuxホスト、AS65000 EVPNを使うOSPFアンダーレイです。Stage Aの上流設定ではEOSとCumulusを明示し、Stage Bの既定はEOSです。**ここで選択するのは、s1とs2をそれぞれ`frr`に上書きする構成**です。文書化された[`-s nodes.s1.device=frr -s nodes.s2.device=frr`起動オプション](https://netlab.tools/netlab/up/)を使います。[EVPN対応表](https://netlab.tools/module/evpn/#platform-support)にはVLAN型EVPN、対称IRB、iBGP／IGPのFRR対応が記載されています。この表は古いイメージやプロバイダーのあらゆる組み合わせで動くことを保証しません。

ステージごとに専用VMを1台用意するか、ステージ間で証拠をエクスポートした後、所有する空のVMチェックポイントに戻してください。ノード／ラボIDが衝突する同じ環境内で両方の複製を起動しないでください。Stage BにはルーティングされたホストリンクとトランジットVNIがあります。これはL3VPN演習であり、アクセスポートVLANのanycast gatewayやホストモビリティの演習**ではありません**。資料を使ってIRBの違いを学びます。選択したL3専用モデルで不要なType 2／3やanycastのテストを、成功として報告しないでください。

## 4. ラボ固有の前提条件と記録

- コンソールアクセスがある、所有するx86-64 Ubuntu 24.04 Linux VMを使います。実行中の6コンテナ構成1ステージあたり4 vCPU、8 GiB RAM、空きディスク20 GiBを計画上の目安にし、実使用量を測定してください。
- ワークブックの前に、[netlab Ubuntuセットアップ](https://netlab.tools/install/ubuntu/)と[containerlabプロバイダー設定](https://netlab.tools/labs/clab/)を完了します。Docker、Ansible依存関係、ノードイメージも用意してください。
- 選択したFRR EVPN／VXLAN／VRF機能をサポートすると明示されたnetlabリリースを使います。正確なリリース、サンプルのリビジョン、2台分のノード上書きを記録します。
- 確認したnetlabの[FRRデバイス定義](https://github.com/ipspace/netlab/blob/4d85d13365caf3962a72ba59ec57a2e4450f365f/netsim/devices/frr.yml)では`quay.io/frrouting/frr:10.6.1`を選択します。ここにあるCLI例はFRR 10.6.1で確認しています。実際にインストールしたリリースのイメージとdigestを記録し、一致すると決めつけないでください。
- FRR／clabには、ブリッジ、VXLAN、Stage BではVRFに対応するVMカーネル機能が必要です。上流手順では**この所有VM**にモジュールをロードする場合があります。必要なモジュールをロードできない制限付きCodespaceは代替になりません。
- VMにiproute2、iputils、tcpdump、GNU `timeout`を用意します。DF／サイズプローブには、記録したノード名前空間内でVMのiputilsを使います。AlpineホストイメージのBusyBox `ping`がこれらのオプションに対応するとは限りません。
- FRRと選択したLinuxホストイメージに、商用ルーターライセンスは不要です。EOS／Cumulusを使い続けるのは別のプラットフォーム選択であり、独自のイメージアクセス、ライセンス、CLI要件があります。
- VM所有者がDocker／プロバイダーの権限を用意します。`vtysh`とnamespace操作には適切なラボ権限が必要です。管理インターフェイス、ワークステーションの経路、クラウド設定を変更しないでください。

**Stage AのVMシェル**で、宛先ディレクトリが存在しないことを確認してから実行します。

```bash
test ! -e "$HOME/expert-fabric-examples"
git clone --no-checkout https://github.com/ipspace/netlab-examples.git "$HOME/expert-fabric-examples"
git -C "$HOME/expert-fabric-examples" checkout --detach 7c4fa0dac160d3cc2eac41e11f20b74d083bb896
cd "$HOME/expert-fabric-examples/EVPN/vxlan-bridging"
git rev-parse HEAD
git status --short
sha256sum topology.yml
python3 -c 'from importlib.metadata import version; print(version("networklab"))'
containerlab version
docker version
ansible --version
uname -r
```

存在しないことの確認に失敗したら停止します。複製は新たに作成する所有対象であり、このVMを破棄するまで証拠と共に保持します。Stage B専用VMでも同じ複製／リビジョン手順を繰り返し、作業ディレクトリには`EVPN/l3vpn`を使います。観察を始める前に、所有者は公式起動手順でプロバイダー`clab`と2台のFRRノード上書きを設定してください。空のVMチェックポイント、生成されたラボID、正確な起動オプション、実験前の正常チェックポイントを記録します。このセットアップがブリッジ／VTEP／VRFを作成します。[FRR自体はLinuxインターフェイスを作成しません](https://docs.frrouting.org/en/latest/evpn.html#the-linux-vxlan-dataplane)。空のコンテナにBGP設定だけを貼り付けて、動くオーバーレイだと扱わないでください。

## 5. アイデンティティとデータプレーンの準備を確認する

アクティブステージの**VMシェル**で実行します。

```bash
netlab status
netlab inspect nodes.s1.interfaces
netlab inspect nodes.s2.interfaces
netlab connect --dry-run s1
netlab connect s1 --show version
netlab connect s1 --show running-config
netlab connect s1 --show ip ospf neighbor
netlab connect s1 --show bgp l2vpn evpn summary
netlab connect s1 --show evpn vni
netlab connect s1 --show bgp l2vpn evpn vni
netlab connect s1 ip -d link show
netlab connect s1 bridge link show
netlab connect s1 bridge fdb show
netlab connect s1 ip route show
```

s2でも読み取り専用の状態確認を繰り返します。ノード／インターフェイスの対応を解釈するには、[inspect](https://netlab.tools/netlab/inspect/)と[connect](https://netlab.tools/netlab/connect/)の資料を参照してください。`netlab connect s1`では**FRRコンテナ内のLinuxシェル**に入ります。FRR CLIに入るには`vtysh`と入力します。`s1#`はFRRの運用モードです。`configure terminal`で設定モードに入り、`end`で抜けます。運用モードで`exit`するとLinuxに戻ります。Linuxでは`ip`／`bridge`、FRRでは`show`を使います。上記のVM側`--show` wrapperも使えます。

`docker inspect --format '{{.Config.Image}} {{.Image}}' CONTAINER`で各コンテナのイメージ名とIDを記録し、名前を指定してラボオブジェクトを個別に調べます。実際のVXLAN interface、ローカルVTEPアドレス、bridge所属、動作中のVNI、リモートVTEPへの到達性を確認してください。Stage Bでは`show vrf vni`、Linux VRFデバイス／テーブル、redまたはblue内のホストリンク所属も確認します。現在の[FRR注意事項](https://netlab.tools/caveats/#frrouting)には、VLAN／VRFの初期化が冪等ではないこと、設定収集にLinux interfaceの状態が含まれないことが記されています。初期条件の失敗を、初期化を繰り返して直そうとしないでください。失敗を保存し、所有するセットアップチェックポイントに戻します。

実際の出力から次の対応表を作ります。記憶を頼りに値を埋めないでください。

| ホスト | データIP／prefix | アクセスVLANまたはルーティングリンク | VRF | L2VNI／L3VNI | ローカル／リモートVTEP | キャプチャinterface |
|---|---|---|---|---|---|---|
| h1 | 記録 | Stage A red／Stage Bルーティング | 記録 | 記録または正当なN/A | 記録 | 記録 |
| h2 | 記録 | Stage A red／Stage Bルーティング | 記録 | 記録または正当なN/A | 記録 | 記録 |
| h3／h4 | 個別に記録 | blue | 記録 | 記録または正当なN/A | 記録 | 記録 |

## 6. Stage A: L2転送と分離を実証する

`netlab connect h1 ip address show`を使ってh1／h2／h3／h4のデータアドレスを読み取ります。毎回1台だけ、正確なホスト名を指定してください。このコマンドはホストコンテナ内で動くため、VMにiproute2をインストールしてもコンテナのBusyBoxは変わりません。管理アドレスや、管理ネットワークを選ぶ可能性のある未解決ホスト名ではなく、データアドレスを使います。VMシェルで対応表の値を使って次のプレースホルダーを置き換えてください。

```bash
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
fabric_h3='REPLACE_WITH_H3_DATA_IPV4'
fabric_h4='REPLACE_WITH_H4_DATA_IPV4'
netlab connect h1 ping -c 5 -W 1 "$fabric_h2"
netlab connect h3 ping -c 5 -W 1 "$fabric_h4"
netlab connect h1 ping -c 5 -W 1 "$fabric_h3"
netlab connect s1 --show bgp l2vpn evpn route type 2
netlab connect s1 --show bgp l2vpn evpn route type 3
netlab connect s1 bridge fdb show
```

リモートType 2／MAC学習を期待する前に、意図したホストトラフィックを生成してください。各リモートMACを正しいVNIとVTEPに対応付けます。Type 3／レプリケーション状態も対象セグメントと一致させます。最初の2つのプローブは成功し、VLANをまたぐプローブはルーティングのない設計で失敗するはずです。その失敗だけでは不十分です。2つの正常系、正しいホスト接続、意図しないルーティング経路がないことを確認してください。負のプローブがローカルの経路不足で失敗したか、データプレーン境界まで到達して失敗したかを記録します。両者は異なる観察結果です。

s1のスイッチ間interfaceはインベントリで確認してください。指定リビジョンのStage A FRRマッピングでは`eth3`です。別端末から許可されたプローブを繰り返しながら、その所有interfaceだけをキャプチャします。

```bash
timeout 20s netlab capture s1 eth3 -nn -e -vv -l -c 30 udp port 4789
```

外側のVTEPペア、VNI、内側のMAC／IPペアを保存します。出力がない、キャプチャエラーがある、または管理トラフィックだけが見える場合は証拠になりません。観察したカプセル化が経路とFDBの証拠にどう一致するか説明してください。ブリッジだけの演習で、チェック表を埋めるためにType 5のテナントプレフィックスを期待しないでください。

## 7. Stage B: ルーティングされたVRFサービスを実証する

別途準備したStage BのVMに移動し、アイデンティティ／アドレス対応表を作り直します。`fabric_h2`、`fabric_h3`、`fabric_h4`変数には**Stage B**のアドレスを割り当てます。Stage Aの値は再利用できる証拠ではありません。セクション6の3つのプローブを再実行します。red／blueのペアは通信でき、VRF間トラフィックは通信できないはずです。併せて次を確認します。

```bash
netlab connect s1 --show vrf vni
netlab connect s1 --show bgp l2vpn evpn route type 5
netlab connect s1 --show bgp vrf red ipv4 unicast
netlab connect s1 --show ip route vrf red
netlab connect s1 ip -d link show type vrf
netlab connect s1 ip route show vrf red
```

Type 5テーブルでh2の実際のリモートサブネット、RD／export RT、redへのインポート、対応するLinux経路を特定します。blueも個別に確認します。redがblueをインポートしていないことを確認し、s2の戻り経路も調べます。セクション6と同様に、**Stage Bで実際に使うinterface**を使ってアンダーレイをキャプチャします。`eth3`とは限りません。トランジットVNIとVRFの関連を確認してください。管理ネットワークへのping成功は、テナントのルーティングサービスの証拠ではありません。

## 8. Stage B: インポートメンバーシップを1つ削除して復元する

対象オブジェクトは**s1のred VRF EVPN import-RTリスト**です。実行中の正確な設定と、有効なRTリストを保存します。redの記録済み数値トランジットVNIを指定して`netlab connect s1 --show bgp l2vpn evpn vni RED_L3VNI`を使い、import／export RTの詳細を確認します。事前状態では、下記`RED_RT`と呼ぶ明示的なimport RTが1つあり、同じ経路を取り込むワイルドカードや追加の自動importがないことが必要です。`BAD_RT`は、どのラボ経路もエクスポートせず既存リストにも使われていないと確認してから`65000:424242`を選びます。事前状態が異なる場合、ほかの項目を即興で削除しないでください。s1の**FRR CLI**では、リテラルのプレースホルダーではなく実際の`RED_RT`を使います。

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import 65000:424242
  no route-target import RED_RT
 exit-address-family
end
```

未使用RTを先に追加してから元のRTを削除すれば、明示的なリストを維持できます。このガードを使わず唯一の手動RTを削除すると、自動RTが復元されて実験が無効になることがあります。FRRリリースごとに自動RT制御は異なります。[実行時の設定に合うRTドキュメント](https://docs.frrouting.org/en/latest/bgp.html)を参照し、VNIの詳細表示で**有効な**import集合を検証します。元のRTがまだ有効なら、注入は達成されていないと分類して復元します。分離をテストしたと主張しないでください。

グローバルType 5広告とBGPセッションは残る一方、h2のリモートプレフィックスがs1のred VRF／FIBから消え、redのプローブは失敗するはずです。blueのペアは引き続き動作し、h2がローカルredゲートウェイへ到達できることも必須です。ホスト停止やアンダーレイ障害では、RT分離を証明できません。グローバルテーブルとインポート済みテーブルにある正確なプレフィックスを確認し、負のプローブの終了コード／出力を保存します。元のメンバーシップを追加してから一時的な方を削除し、同じオブジェクトを復元します。

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import RED_RT
  no route-target import 65000:424242
 exit-address-family
end
```

元の有効RT集合、リモート経路、redのプローブ、blueの正常系が復旧したことを確認します。RD、neighbor、export RTは変更しないでください。

## 9. Stage B: アンダーレイMTUの挙動を測定する

対象オブジェクトは**s1のスイッチ間データinterfaceのMTU**です。上流Stage Bリンクは1600を要求します。続行前に、選択したinterfaceの実値が1600であることを確認してください。管理／アクセス／bridge／VXLAN interfaceではないことと、対向側がs2であることを記録します。復元用に2つ目のVM端末を開いておきます。このステージの対応表からinterface、h1 namespace、h2のデータアドレスを指定してください。

```bash
fabric_underlay='REPLACE_WITH_S1_TO_S2_INTERFACE'
fabric_h1_ns='REPLACE_WITH_THIS_LABS_H1_NAMESPACE'
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
netlab connect s1 ip -d link show dev "$fabric_underlay"
sudo ip netns exec "$fabric_h1_ns" ip -br address
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1200 -c 5 -W 1 "$fabric_h2"
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1400 -c 5 -W 1 "$fabric_h2"
```

ベースラインの両サイズのプローブが成功することを確認します。VMの[iputils ping](https://github.com/iputils/iputils/blob/master/doc/ping.xml)が`-M do`を提供します。ホストコンテナ内でパッケージをインストールできるとは仮定しません。タグなしEthernetで外側がIPv4の場合、ICMPペイロード1400バイトは内側IP 1428バイト、カプセル化後の外側IPはおよそ1478バイトになります。実際のタグ／ヘッダーを記録してください。IPv6転送や追加カプセル化があると予算は変わります。

記録したMTUだけを変更し、両方のプローブを再実行しながらアンダーレイをキャプチャします。

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1400
timeout 20s netlab capture s1 "$fabric_underlay" -nn -vv -l -c 30 'ip proto 17 or icmp'
```

小さいプローブは通る一方で、大きい方はドロップする、または外側パケットがフラグメント化する場合があります。内側のDFだけで外側もDFになるとは限りません。IPv4プロトコルフィルターは、ポートだけのフィルターでは取り逃す後続UDPフラグメントも含めます。記録したVTEPペアと先頭フラグメントでVXLANを識別してください。OSPFがMTU不一致に反応することもあります。BGPが必ず確立したままだと決めつけず、neighbor状態、エラー、フラグメント、ICMP応答を記録します。サイズ依存の影響が出なければ、その観察結果を報告し、カプセル化／フラグメント化／offloadを調べます。ブラックホールを捏造してはいけません。範囲を限定して収集したら、直ちに復元してください。

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1600
netlab connect s1 ip -d link show dev "$fabric_underlay"
```

OSPF／BGP、2つのプローブサイズ、両VRFの正常系、VRF間の負の確認を再テストしてください。きれいに見せる目的で、経路、neighborテーブル、全bridgeをflushしないでください。

## 10. 証拠と完了条件

| テスト | 正常系の確認 | 意図した負の証拠 | 復元の証明 |
|---|---|---|---|
| L2セグメンテーション | 同一VLANの両ペアが成功し、VXLAN／FDBが正しい | ルーティングサービスなしでVLAN間通信が遮断される | 元のマッピングとプローブ再実行 |
| L3 VPN | Type 5が正しいVRFにインポートされ、テナントプローブが成功 | 他VRFがimport／FIBになく、プローブが遮断される | 元の経路／プローブ一覧 |
| RT不一致 | blueが成功し、対象ホストとローカルゲートウェイが稼働 | グローバル経路はあるがredにimportされず、redプローブが失敗 | RTリスト、経路、redプローブが元に戻る |
| MTU低下 | ベースラインサイズと既知のアンダーレイ | 測定されたサイズ／フラグメント化／隣接関係への影響、または再現しなかったという明示的記録 | MTU 1600と全ベースラインを再確認 |

各行について、フェーズ、時刻、VM／ラボID、上流リビジョン、ツール／イメージのバージョン、ノード／interface、期待値、実際の出力、結論を保存します。**PASS**、**FAIL**、**BLOCKED**、または根拠付きの**N/A**で記録します。経路テーブルが空、プローブがない、キャプチャがない、という状態だけではPASSになりません。選択モデルで必要ない型／機能だけをN/Aとして記録します。必須テストの失敗を回避するためにN/Aを使わないでください。すべての変更を名前付きの対象オブジェクトで元に戻します。失敗した場合は証拠を保存し、記録した所有VMチェックポイントだけを復元します。実験変更は保存せず、冪等でない初期化の再実行や全ラボの一括teardown／全体pruneをしないでください。

L2とL3サービスを追跡し、RD／RTと経路タイプを説明し、正常系を維持したまま分離を示し、復元を実証できれば完了です。[Linuxパフォーマンス](04-linux-performance.md)、[クラウド／CNI設計](05-cloud-cni-design.md)、[自動化capstone](06-automation-capstone.md)、[クイズ](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md)に続きます。
