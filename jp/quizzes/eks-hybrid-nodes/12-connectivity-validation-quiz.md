# SNATなしのPod接続とPrivateLinkに関するクイズ

> **最終更新日**: 2026年10月19日

[学習ガイド: SNATなしのPod接続とPrivateLinkの検証](../../eks-hybrid-nodes/12-connectivity-validation.md)

1. AWSがEKS Hybrid NodesでサポートしているCiliumのネットワーキングモードはどれですか？
   - A) ネイティブルーティングのみ
   - B) VXLANカプセル化のみ
   - C) VXLANとネイティブルーティングの両方

<details>
<summary>回答を表示</summary>

**回答: B) VXLANカプセル化のみ**

**説明:**
Configure CNI for hybrid nodes のサポート対象機能の表では、ネットワーキングモードとしてVXLANカプセル化が挙げられています。ネイティブルーティングはサポート対象外であり、Hybrid Nodes GatewayにはVTEP（VXLAN）が必要なため、ネイティブルーティングでは使用できません。

</details>

2. VXLANを維持したままマスカレードを無効にし、Cilium BGPでPod CIDRをアドバタイズします。ファイアウォールがPod IPを確認できないのは、どの区間ですか？
   - A) クラウドのPodとオンプレミスのPodの間
   - B) Kubernetes外部のオンプレミスサーバーへの通信
   - C) ハイブリッドノード間

<details>
<summary>回答を表示</summary>

**回答: C) ハイブリッドノード間**

**説明:**
ハイブリッドノード間のトラフィックはVXLANでカプセル化され、外側のヘッダーにはノードIPが含まれます。マスカレードを無効にすると、クラスター外へ出るトラフィックにはPod IPが保持されます。

</details>

3. ネイティブルーティングに切り替えた後、クラウドのPodからオンプレミスサーバーに接続すると、オンプレミスサーバーにはクラウドノードのIPが見えます。まず何を確認しますか？
   - A) VPC CNIの`AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS`にオンプレミスのノード範囲が含まれているか
   - B) Ciliumの`enableIPv4Masquerade`の値
   - C) TGWルートテーブルのデフォルトルート

<details>
<summary>回答を表示</summary>

**回答: A) VPC CNIの`AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS`にオンプレミスのノード範囲が含まれているか**

**説明:**
クラウドのPodに対するSNATはCiliumではなくVPC CNIが行います。除外リストにPod範囲（172.17.0.0/16）だけが含まれ、オンプレミスのノード範囲（172.18.0.0/16）が含まれていない場合、オンプレミスサーバー宛てのトラフィックはノードIPに変換されます。

</details>

4. hostNetwork PodだけがクラスターのService名を解決できず、通常のハイブリッドPodは問題なく解決できます。最も可能性の高い原因は何ですか？
   - A) CoreDNSがハイブリッドノード上にない
   - B) hostNetwork PodはノードIPからCoreDNSを呼び出すが、クラスターSGでノード範囲からのポート53が許可されていない
   - C) hostNetwork PodはDNSを使用できない

<details>
<summary>回答を表示</summary>

**回答: B) hostNetwork PodはノードIPからCoreDNSを呼び出すが、クラスターSGでノード範囲からのポート53が許可されていない**

**説明:**
通常のPodはPod IP（172.17.x）で通信しますが、hostNetwork PodはノードIP（172.18.x）で通信します。クラスターSGで`172.18.0.0/16`からのUDPおよびTCPポート53を許可してください。`dnsPolicy: ClusterFirstWithHostNet`も必要です。

</details>

5. オンプレミスのPodからプライベート経路でS3にアクセスする必要があります。正しい説明はどれですか？
   - A) S3ゲートウェイエンドポイントはオンプレミスからも使える。
   - B) S3インターフェイスエンドポイントが必要であり、ゲートウェイエンドポイントがない状態では、テストで`DnsOptions`を`AllResolvers`に設定する必要があった。
   - C) S3はPrivateLinkをサポートしていない。

<details>
<summary>回答を表示</summary>

**回答: B) S3インターフェイスエンドポイントが必要であり、ゲートウェイエンドポイントがない状態では、テストで`DnsOptions`を`AllResolvers`に設定する必要があった。**

**説明:**
ゲートウェイエンドポイントはオンプレミスからは使用できません。テストでは、`PrivateDnsOnlyForInboundResolverEndpoint`を指定せずに最初の作成を試みると、VPCにゲートウェイエンドポイントが必要だというエラーが発生しました。

</details>

6. エンドポイントSGでは、`172.17.0.0/16`（Pod範囲）からのTCP 443のみが許可されています。同じハイブリッドノード上の通常のPodとhostNetwork PodがSTSエンドポイントを呼び出すと、どうなりますか？
   - A) 両方とも成功する。
   - B) 両方とも失敗する。
   - C) 通常のPodは成功し、hostNetwork Podはタイムアウトする。

<details>
<summary>回答を表示</summary>

**回答: C) 通常のPodは成功し、hostNetwork Podはタイムアウトする。**

**説明:**
SNATがない場合、通常のPodの送信元はPod IPで、hostNetwork Podの送信元はノードIP（172.18.x）です。そのため、AWS側のセキュリティグループでは、Pod範囲に基づいてオンプレミスのPodを識別できます。

</details>

7. Kubernetes 1.36、Cilium 1.18の混在モードクラスターでのテストでは、リンク障害中もハイブリッドPodがオンプレミスのCoreDNSを使い続けるために、kube-dns Serviceにどの設定を指定しましたか？
   - A) `trafficDistribution: PreferClose`
   - B) `externalTrafficPolicy: Local`
   - C) `sessionAffinity: ClientIP`

<details>
<summary>回答を表示</summary>

**回答: A) `trafficDistribution: PreferClose`**

**説明:**
ハイブリッドノード上のClusterIP負荷分散はCilium BPFによって行われ、テストで使用したCilium 1.18.13は`PreferSameZone`を無視しました。AWSドキュメントの例でも`PreferClose`が使われています。Kubernetes 1.35以降では非推奨の別名ですが、ここで機能した値はこれだけでした。参加時に設定するゾーンラベル、すべてのゾーンへのCoreDNSの配置、およびCiliumの`loadBalancer.serviceTopology: true`も必要です。

</details>
