# BGP詳細クイズ

> **関連ドキュメント**: [BGP詳細](../../../networking/calico/04-bgp-deep-dive.md)
> **最終更新日**: 2026年9月12日

## クイズ

1. BGPは何の略ですか？
   - A) Basic Gateway Protocol
   - B) Border Gateway Protocol
   - C) Bridge Gateway Protocol
   - D) Bandwidth Gateway Protocol

<details>
<summary>解答を表示</summary>

**回答: B) Border Gateway Protocol**

**解説:**
BGPはBorder Gateway Protocolの略です。自律システム間で経路情報を交換する、インターネットを支えるルーティングプロトコルです。CalicoではBGPを使って、ノード間でPodネットワークの経路を配布し、必要に応じて外部ネットワークインフラストラクチャにも配布します。

</details>

2. iBGPとeBGPの違いは何ですか？
   - A) iBGPは高速で、eBGPはより安全である
   - B) iBGPは同じAS内、eBGPは異なるAS間で使用される
   - C) iBGPはTCPを使い、eBGPはUDPを使う
   - D) iBGPはIPv4用で、eBGPはIPv6用である

<details>
<summary>解答を表示</summary>

**回答: B) iBGPは同じAS内、eBGPは異なるAS間で使用される**

**解説:**
iBGP (Internal BGP) は同じ自律システム (AS) 内にあるルーター間のBGPセッションを指します。eBGP (External BGP) は異なる自律システムのルーター間のBGPセッションを指します。Calicoクラスターでは通常、クラスター内のノードは同じASでiBGPを使い、外部ネットワークインフラストラクチャとのピアリングには異なるASでeBGPを使う場合があります。

</details>

3. プライベート16ビットASN用に予約されている範囲はどれですか？
   - A) 1-64511
   - B) 64512-65534
   - C) 65535-65600
   - D) 100000-200000

<details>
<summary>解答を表示</summary>

**回答: B) 64512-65534**

**解説:**
プライベートASNの範囲は、16ビットでは64512–65534、32ビットでは4200000000–4294967294です。ASNは自律システムを識別するもので、プライベートASNは、それ自体がルーティング不能なIPアドレスという意味ではありません。経路をグローバルインターネットに広告する前に、ASパスからプライベートASNを取り除いてください。CalicoのデフォルトASNは64512です。

</details>

4. N個のノードがあるクラスターで、BGPフルメッシュトポロジーを構成した場合、BGPセッションはいくつ確立されますか？
   - A) Nセッション
   - B) N * 2セッション
   - C) N * (N-1) / 2セッション
   - D) N^2セッション

<details>
<summary>解答を表示</summary>

**回答: C) N * (N-1) / 2セッション**

**解説:**
BGPフルメッシュでは、すべてのノードがほかのすべてのノードとピアリングします。セッション数はN * (N-1) / 2で、Nはノード数です。たとえば、ノードが10台のクラスターでは、10 * 9 / 2 = 45のBGPセッションになります。このため、大規模なクラスターではRoute Reflectorが推奨されます。

</details>

5. BGP Route Reflectorの主な役割は何ですか？
   - A) BGPトラフィックを暗号化する
   - B) クライアントに経路を反映し、BGPセッション数を減らす
   - C) 悪意のある経路をフィルタリングする
   - D) iBGPをeBGPに変換する

<details>
<summary>解答を表示</summary>

**回答: B) クライアントに経路を反映し、BGPセッション数を減らす**

**解説:**
Route Reflectorはクライアントから経路を受け取り、ほかのクライアントに「反映」することで、クラスター内で必要なBGPセッション数を減らします。フルメッシュで必要なN * (N-1) / 2セッションの代わりに、クライアントはRoute Reflector（複数の場合もあります）とのみピアリングすればよくなります。これは大規模クラスターでBGPを拡張するうえで重要です。

</details>

6. Route Reflectorの設定におけるCluster IDの目的は何ですか？
   - A) Kubernetesクラスターを識別する
   - B) Route Reflector間のルーティングループを防ぐ
   - C) ノードにIPアドレスを割り当てる
   - D) BGPセッションを暗号化する

<details>
<summary>解答を表示</summary>

**回答: B) Route Reflector間のルーティングループを防ぐ**

**解説:**
Route Reflectorは、CLUSTER_LISTに自身のクラスターIDが含まれている反映経路を拒否します。同じクライアントを担当する冗長Route Reflectorでは同じIDを共有できますが、異なるRoute Reflectorグループや階層レベルには、意図的に別のIDを割り当てる必要があります。Kubernetesクラスターの識別子ではありません。

</details>

7. BGPPeerリソースのnodeSelectorフィールドは何を制御しますか？
   - A) BGPを利用できるPod
   - B) BGPピアリングを確立するノード
   - C) 広告される経路
   - D) ピアを利用できる名前空間

<details>
<summary>解答を表示</summary>

**回答: B) BGPピアリングを確立するノード**

**解説:**
BGPPeerリソースの`nodeSelector`フィールドは、定義されたピアとのBGPセッションを確立するノードを指定します。たとえば、ラックを意識したピアリングでは、クラスター内のすべてのノードではなく、特定のラックにあるノードだけをローカルのToR (Top of Rack) スイッチとピアリングさせる場合に使います。

</details>

8. 自動ノード間メッシュを無効にするBGPConfigurationの設定はどれですか？
   - A) meshEnabled: false
   - B) nodeToNodeMeshEnabled: false
   - C) disableMesh: true
   - D) bgpMesh: disabled

<details>
<summary>解答を表示</summary>

**回答: B) nodeToNodeMeshEnabled: false**

**解説:**
この設定は自動メッシュセッションを無効にします。置き換えとなるRoute Reflectorまたはファブリックのセッションを確立し、受信・広告経路、ネクストホップ、代表的なトラフィックを先に検証してください。ノードをRoute Reflectorに指定すると、そのノードは自動メッシュから直ちに外れるため、変換前に適切なノードを準備してください。

</details>

9. CalicoはBGP経由でどの種類のService IPを広告できますか？
   - A) ClusterIPのみ
   - B) LoadBalancer IPのみ
   - C) ClusterIP、ExternalIP、LoadBalancer IP
   - D) NodePort Serviceのみ

<details>
<summary>解答を表示</summary>

**回答: C) ClusterIP、ExternalIP、LoadBalancer IP**

**解説:**
該当するフィールドはserviceClusterIPs、serviceExternalIPs、serviceLoadBalancerIPsです。これらは既存のアドレスを広告するもので、アドレスの割り当て、エンドポイントの健全性、戻り経路は別途必要です。クラウドロードバランサーのホスト名はBGPプレフィックスではありません。Kubernetesのspec.externalIPsは1.36から非推奨になりましたが、削除されたわけではありません。

</details>

10. CalicoでBGPコミュニティを使う目的は何ですか？
    - A) アクセス制御用のユーザーグループを作成する
    - B) ポリシー判断に使うメタデータとして経路にタグを付ける
    - C) 特定の経路を暗号化する
    - D) ルーティングテーブルを圧縮する

<details>
<summary>解答を表示</summary>

**回答: B) ポリシー判断に使うメタデータとして経路にタグを付ける**

**解説:**
コミュニティはルーターのポリシーに使う経路タグです。標準コミュニティは16ビット値を2つ、大規模コミュニティは32ビット値を3つ持ちます。high-priorityやinternal-onlyのような名前を付けても、その意味が自動的に強制されるわけではありません。prefixAdvertisementsは一致する既存経路にタグを付けるもので、集約経路を生成する機能ではありません。

</details>

11. CalicoでBGPセッションを保護するために使える認証方式は何ですか？
    - A) TLS証明書
    - B) MD5認証
    - C) OAuthトークン
    - D) Kerberos

<details>
<summary>解答を表示</summary>

**回答: B) MD5認証**

**解説:**
TCP MD5署名オプションは、BGPPeerが参照する共有シークレットを使ってBGPトラフィックを認証します。トラフィックを暗号化する機能でも、認証済みピアからの経路が正当であることを証明する機能でもありません。認証情報の設定と経路フィルターは、それぞれ個別に構成してください。

</details>

12. BGPにおけるGraceful Restartとは何ですか？
    - A) 設定を失わずにBGPを再起動する方法
    - B) BGPデーモンの再起動中に転送状態を維持する仕組み
    - C) 新しいBGPピアを段階的に追加する方法
    - D) 経路の取り下げを遅らせる手法

<details>
<summary>解答を表示</summary>

**回答: B) BGPデーモンの再起動中に転送状態を維持する仕組み**

**解説:**
ピアはGraceful Restart機能をネゴシエートし、BGPデーモンの再起動中に一定時間、経路を保持する場合があります。転送経路が引き続き利用できる場合にのみ役立ちます。古い経路が保持されることで、トラフィックがブラックホール化する可能性もあります。更新が中断されないことを保証する機能ではありません。

</details>

13. BIRDデーモンでBGPプロトコルの状態を確認するコマンドはどれですか？
    - A) bird status
    - B) birdcl -s /var/run/calico/bird.ctl show protocols
    - C) bird show peers
    - D) birdctl status bgp

<details>
<summary>解答を表示</summary>

**回答: B) birdcl -s /var/run/calico/bird.ctl show protocols**

**解説:**
対象のcalico-nodeコンテナ内で、IPv4の制御ソケットを明示してこのコマンドを実行してください。BGP、kernel、deviceなどのプロトコルが一覧表示されます。詳細を確認するには、実際のプロトコル名を指定してshow protocols allを使います。IPv6ではbirdcl6と/var/run/calico/bird6.ctlを使います。BGPが無効なインストール環境にはBIRDデーモンが存在しない場合があります。

</details>

14. Spine-Leaf型データセンタートポロジーで、Calicoノードは通常どのようにピアリングしますか？
    - A) すべてのノードがすべてのSpineスイッチとピアリングする
    - B) ノードはローカルのToR (Leaf) スイッチとピアリングする
    - C) masterノードだけがネットワークインフラストラクチャとピアリングする
    - D) ノードがスイッチを介さず相互に直接ピアリングする

<details>
<summary>解答を表示</summary>

**回答: B) ノードはローカルのToR (Leaf) スイッチとピアリングする**

**解説:**
Spine-Leafトポロジーでは、Calicoノードは通常、ローカルのTop-of-Rack (ToR/Leaf) スイッチとピアリングします。LeafスイッチはSpineスイッチとピアリングします。これはデータセンターネットワークの階層設計に沿った構成です。BGPPeerリソースのnodeSelectorを使い、ノードが自身のラックのToRスイッチとのみピアリングするようにします。

</details>

15. nodeToNodeMeshEnabledがtrueのままRoute Reflectorのピアリングを導入すると、何が起こることがありますか？
    - A) Route Reflectorが優先され、メッシュが無効になる
    - B) 移行中に、Route Reflector以外のクライアント間メッシュセッションと明示的なRoute Reflectorセッションが共存する
    - C) 設定エラーになり、Calicoの起動に失敗する
    - D) Route Reflectorが無視される

<details>
<summary>解答を表示</summary>

**回答: B) 移行中に、Route Reflector以外のクライアント間メッシュセッションと明示的なRoute Reflectorセッションが共存する**

**解説:**
routeReflectorClusterIDを設定すると、Route Reflectorノードは自動メッシュから外れます。残りのRoute Reflector以外のクライアントは、明示的なRoute Reflectorセッションの準備とテストを進める間、メッシュを維持できます。置き換えセッション、経路、ネクストホップ、トラフィックを検証してからメッシュを削除してください。

</details>

16. IPv4のデフォルト経路だけに一致するインポートルールはどれですか？
    - A) Accept with In 0.0.0.0/0
    - B) Accept with Equal 0.0.0.0/0
    - C) Reject with NotIn 0.0.0.0/0
    - D) ルールのないフィルター

<details>
<summary>解答を表示</summary>

**回答: B) Accept with Equal 0.0.0.0/0**

**解説:**
Equalは/0プレフィックスに完全一致します。In /0はすべてのIPv4経路に一致し、NotIn /0はどの経路にも一致しません。BGPFilterでは、一致するルールがない経路はデフォルトでAcceptされるため、許可リストには最後に無条件のRejectも必要です。

</details>

17. 10.244.0.0/16に対するprefixAdvertisementsは何を行いますか？
    - A) 常に新しい/16経路を生成する
    - B) すべての/26経路を/16に置き換える
    - C) この範囲に一致する既存経路にコミュニティを追加する
    - D) Service IPを割り当てる

<details>
<summary>解答を表示</summary>

**回答: C) この範囲に一致する既存経路にコミュニティを追加する**

**解説:**
現在のCalicoレンダラーは、Pod経路を含む一致済みの既存経路にコミュニティを追加します。プレフィックスの生成、アドレスの割り当て、ブロックの集約は行いません。先に明示的なBGPFilterのexport Acceptを設定すると、この組み込みのタグ付けが迂回されることがあるため、accepted-route操作が必要になる場合があります。

</details>

---

[学習資料に戻る](../../../networking/calico/04-bgp-deep-dive.md) | [前のクイズ: Networking Modes](./03-networking-modes-quiz.md) | [次のクイズ: Network Policy](./05-network-policy-quiz.md)
