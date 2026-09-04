# クロス Organization VPC 接続性クイズ

このクイズでは、異なる AWS Organizations 間で VPC を接続するための 5 つの選択肢についての理解度を確認します。

## 選択式問題

1. 異なる Organization のアカウントと Transit Gateway を共有するには、何が必要ですか？
   - A) 2 つの Organizations を 1 つに統合する
   - B) `--allow-external-principals` オプションと、受信側での招待の承諾
   - C) 両 Organizations の管理アカウント間の VPN 接続
   - D) AWS Support チケットによる手動承認

<details>

<summary>回答を表示</summary>

**回答: B) `--allow-external-principals` オプションと、受信側での招待の承諾**

**解説:**
AWS RAM 経由で Organization 外部のアカウントとリソースを共有するには、リソース共有で `--allow-external-principals` が必要であり、受信アカウントが `accept-resource-share-invitation` を実行するまでリソースは表示されません。Organization 内での OU ベースの自動共有とは異なり、Organization 間の共有では明示的なアカウント ID 指定と明示的な承諾が必須です。
</details>

2. 別の Organization にあるアカウントが共有された TGW への VPC attachment を作成すると、どうなりますか？
   - A) 即座に利用可能になる
   - B) TGW を所有するアカウントが承諾するまで pendingAcceptance のままになる
   - C) リクエストは拒否され、attachment は作成できない
   - D) 24 時間後に自動的にアクティブ化される

<details>

<summary>回答を表示</summary>

**回答: B) TGW を所有するアカウントが承諾するまで pendingAcceptance のままになる**

**解説:**
auto-accept が無効（デフォルト）の場合、外部アカウントの attachment は TGW 所有者が `accept-transit-gateway-vpc-attachment` を実行するまで `pendingAcceptance` のままです。ここで、「TGW 所有者がネットワークを一元的に制御する」というモデルが API レベルで強制されます。共有を受信するアカウントは attachment を作成できるだけで、route table を変更することはできません。
</details>

3. 同一 AZ 内での実測に基づくと、Transit Gateway の hop ごとに追加されるレイテンシ（p50）はどの程度ですか？
   - A) 約 0.02 ms — 実質ゼロ
   - B) 約 0.4–0.6 ms — 1 ミリ秒未満
   - C) 約 3–5 ms
   - D) 10 ms 以上

<details>

<summary>回答を表示</summary>

**回答: B) 約 0.4–0.6 ms — 1 ミリ秒未満**

**解説:**
c7g.large、素の EC2 responder、持続的な TCP_RR（1 パスあたり 1,500 サンプル）で測定したところ、TGW の 1 hop のコストは +0.571 ms（TCP_RR）/ +0.410 ms（ICMP）でした。参考として、VPC Peering のコストは測定限界内ではゼロ（同一 VPC のベースラインと同等）であり、NLB の 1 hop（+0.79 ms）は実際には TGW の 1 hop よりコストが高くなります。burstable instance や多段 proxy chain を用いる測定では、このサブミリ秒のシグナルがノイズに埋もれるため、測定設計が重要です。
</details>

4. VPC Lattice の target instance における Security Group 設定で、よくある落とし穴は何ですか？
   - A) すべての outbound rule を開放する必要がある
   - B) Lattice data plane は link-local（169.254.171.0/24）から到達するため、managed prefix list を許可する必要がある
   - C) SG ではなく NACL を使用する必要がある
   - D) port 443 のみを許可する必要がある

<details>

<summary>回答を表示</summary>

**回答: B) Lattice data plane は link-local（169.254.171.0/24）から到達するため、managed prefix list を許可する必要がある**

**解説:**
VPC Lattice のトラフィック（health check を含む）は、VPC CIDR ではなく link-local range 169.254.171.0/24 から到達します。target SG が VPC CIDR のみを許可している場合、すべての health check が UNHEALTHY と報告されます。修正するには、managed prefix list `com.amazonaws.<region>.vpc-lattice` を SG の inbound rules に追加します。
</details>

5. IP CIDR が重複する 2 つの Organizations の VPC を接続できる選択肢はどれですか？
   - A) VPC Peering と TGW Peering
   - B) TGW RAM Sharing
   - C) PrivateLink と VPC Lattice
   - D) どの選択肢でも接続できない

<details>

<summary>回答を表示</summary>

**回答: C) PrivateLink と VPC Lattice**

**解説:**
VPC Peering、TGW RAM sharing、TGW Peering はすべて L3 routing ベースであるため、CIDR の重複があると利用できません。PrivateLink は consumer VPC 内の ENI を介して動作し、VPC Lattice は link-local addressing を使用するため、どちらも CIDR の重複にかかわらず動作します。M&A や MSP migration のように IP の再設計が不可能な状況では、この 2 つだけが選択肢です。
</details>

6. TGW Peering 構成における routing について、正しい記述はどれですか？
   - A) route は BGP 経由で自動的に propagate される
   - B) BGP はサポートされないため、両方の TGW route table に static route を手動で追加する必要がある
   - C) VPC route table のみを変更すればよい
   - D) routing 設定は一切不要である

<details>

<summary>回答を表示</summary>

**回答: B) BGP はサポートされないため、両方の TGW route table に static route を手動で追加する必要がある**

**解説:**
TGW peering attachment は BGP をサポートしないため、route の自動 propagation はありません。peer の CIDR に向かう static route を両方の TGW route table に追加する必要があります。実環境でのテストでは、static route を設定するまでトラフィックは流れませんでした。また、運用上の注意点として、static TGW route は propagated route より優先されること、peering attachment ID は requester 側と accepter 側で異なることにも注意してください。
</details>
