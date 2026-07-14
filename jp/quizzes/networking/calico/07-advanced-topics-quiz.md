# 高度なトピック クイズ

> **関連ドキュメント**: [高度なトピック](../../../networking/calico/07-advanced-topics.md)
> **最終更新**: February 22, 2026

## クイズ

1. Calico のブロックベース IPAM では、/26 CIDR ブロックはいくつの IP アドレスを提供しますか？
   - A) 32 IP
   - B) 64 IP
   - C) 128 IP
   - D) 256 IP

<details>
<summary>回答を表示</summary>

**回答: B) 64 IP**

**解説:**
/26 CIDR ブロックは 64 個の IP アドレスを提供します (2^(32-26) = 2^6 = 64)。Calico は設定可能なサイズの IP ブロックを Node に割り当て、その後、これらのブロックから個別の IP を Pod に割り当てます。デフォルトのブロックサイズは /26 であり、効率と IP 使用率のバランスを取ります。

</details>

2. Calico の IPAM における IP ブロックアフィニティとは何ですか？
   - A) 同じラベルを持つ Pod は常に同じブロックから IP を取得する
   - B) Node が特定の IP ブロックを取得し、優先的に使用する
   - C) Service にはそのエンドポイントに近い IP が割り当てられる
   - D) IP アドレスがアベイラビリティーゾーン別にグループ化される

<details>
<summary>回答を表示</summary>

**回答: B) Node が特定の IP ブロックを取得し、優先的に使用する**

**解説:**
IP ブロックアフィニティとは、Node が Pod IP を割り当てる必要がある場合に、1 つ以上の IP ブロックを取得し、それらのブロックから優先的に割り当てることを意味します。Node 上のすべての Pod は通常同じ IP プレフィックスを共有するため、ルート集約が可能になり、ルーティング効率が向上します。

</details>

3. Calico で WireGuard 暗号化を有効にするにはどうしますか？
   - A) 別の WireGuard operator をインストールする
   - B) FelixConfiguration で wireguardEnabled: true を設定する
   - C) WireGuard NetworkPolicy を適用する
   - D) Kubernetes API server のフラグで有効化する

<details>
<summary>回答を表示</summary>

**回答: B) FelixConfiguration で wireguardEnabled: true を設定する**

**解説:**
WireGuard 暗号化は、FelixConfiguration リソースで `wireguardEnabled: true` を設定することで有効になります。Calico は Node 間の WireGuard キーの生成と配布を自動的に管理し、Node をまたぐ Pod 間トラフィック用の暗号化トンネルを作成します。

</details>

4. Pod トラフィックの暗号化において、IPsec と比較した WireGuard の主な利点は何ですか？
   - A) WireGuard はより多くの暗号化アルゴリズムをサポートする
   - B) WireGuard は設定がより簡単で、CPU オーバーヘッドが低い
   - C) WireGuard はカーネルサポートなしで動作する
   - D) WireGuard はより優れた圧縮を提供する

<details>
<summary>回答を表示</summary>

**回答: B) WireGuard は設定がより簡単で、CPU オーバーヘッドが低い**

**解説:**
WireGuard は選択肢が少ないため設定がより簡単で（設定ミスのリスクが低減されます）、通常は IPsec と比べて CPU オーバーヘッドも低くなります。最新の暗号プリミティブを使用し、コードベースも小さいため、監査と保守が容易です。

</details>

5. Calico の Egress Gateway 機能の主なユースケースは何ですか？
   - A) Service への ingress トラフィックをロードバランシングする
   - B) 外部 Service にアクセスする Pod に一貫した送信元 IP を提供する
   - C) より高速な名前解決のために DNS 応答をキャッシュする
   - D) 送信 API 呼び出しをレート制限する

<details>
<summary>回答を表示</summary>

**回答: B) 外部 Service にアクセスする Pod に一貫した送信元 IP を提供する**

**解説:**
Egress Gateway により、Pod は一貫性があり予測可能な送信元 IP アドレスを使用して外部 Service にアクセスできます。外部 Service が IP ベースの許可リストを使用する場合、特定の Pod からのトラフィックが常に既知の Gateway IP からのものとして見えるようになるため、これは不可欠です。

</details>

6. Calico のマルチクラスター federation はどのような機能を提供しますか？
   - A) クラスター間の自動フェイルオーバー
   - B) クラスター間での共有 NetworkPolicy と Service discovery
   - C) すべてのクラスターの一元化されたログ記録
   - D) クラスター間で統合された請求

<details>
<summary>回答を表示</summary>

**回答: B) クラスター間での共有 NetworkPolicy と Service discovery**

**解説:**
マルチクラスター federation により、Calico は NetworkPolicy を共有し、クラスター間の Service discovery を有効にし、複数の Kubernetes クラスターにわたって一貫したネットワーキングを提供できます。これにより、異なるクラスター内のワークロードは統一されたポリシーを使用して安全に通信できます。

</details>

7. Calico の Windows サポートについて正しい記述はどれですか？
   - A) Windows Node には別の CNI plugin が必要である
   - B) Calico は一部の機能制限付きで Windows Node をサポートする
   - C) Windows サポートは Calico Enterprise でのみ利用できる
   - D) Windows Node は BGP peering に参加できない

<details>
<summary>回答を表示</summary>

**回答: B) Calico は一部の機能制限付きで Windows Node をサポートする**

**解説:**
Calico は Kubernetes クラスターで Windows Node をサポートし、Linux/Windows 混在環境を実現します。ただし、OS の違いにより、eBPF dataplane などの一部の機能は Windows では利用できません。Windows サポートは基本的なネットワーキングと NetworkPolicy の適用を対象としています。

</details>

8. Calico Enterprise と Calico Open Source の主な違いは何ですか？
   - A) Enterprise は異なる dataplane テクノロジーを使用する
   - B) Enterprise には追加のセキュリティ、コンプライアンス、observability 機能が含まれる
   - C) Enterprise は特定の Kubernetes ディストリビューションでのみ動作する
   - D) Enterprise は BGP をサポートしない

<details>
<summary>回答を表示</summary>

**回答: B) Enterprise には追加のセキュリティ、コンプライアンス、observability 機能が含まれる**

**解説:**
Calico Enterprise はオープンソースプロジェクトを基盤とし、階層型ポリシーティア、フローの可視化、コンプライアンスレポート、脅威防御、エンタープライズサポートなどの機能を追加します。コアのネットワーク dataplane は両バージョンで同じです。

</details>

9. 大規模な Calico デプロイメントにおける Typha のサイジング式は何ですか？
   - A) Node 100 台ごとに Typha 1 台
   - B) Node 500 台ごとに Typha 1 台、HA のため最低 3 台
   - C) Typha replicas = nodes / 200、Node 1000 台以上のクラスターに推奨
   - D) クラスターサイズに関係なく固定で 5 replicas

<details>
<summary>回答を表示</summary>

**回答: C) Typha replicas = nodes / 200、Node 1000 台以上のクラスターに推奨**

**解説:**
Node が 1000 台以上のクラスターでは、スケーラビリティのために Typha が不可欠になります。一般的なサイジング式は Node 200 台あたりおよそ Typha replica 1 台であり、高可用性のため最低 3 replicas が必要です。Typha は datastore の更新を Felix インスタンスにファンアウトし、API server の負荷を軽減します。

</details>

10. Calico で IPv6 およびデュアルスタックネットワーキングをサポートするために必要なことは何ですか？
    - A) IPv6 専用の別インストール
    - B) IPv4 と IPv6 の両方のアドレス範囲に対する IPPool の設定
    - C) eBPF dataplane のみを使用する
    - D) NetworkPolicy の適用を無効にする

<details>
<summary>回答を表示</summary>

**回答: B) IPv4 と IPv6 の両方のアドレス範囲に対する IPPool の設定**

**解説:**
Calico でのデュアルスタックサポートには、IPv4 と IPv6 の両方の CIDR 範囲に対する IPPool の設定が必要です。その後、Pod は両方のプールからアドレスを取得できます。クラスターでも Kubernetes レベルでデュアルスタックを有効にする必要があり、基盤インフラストラクチャも IPv6 をサポートしている必要があります。

</details>

11. Calico の IPAM で IP アドレス枯渇を検出するにはどうしますか？
    - A) kube-apiserver のログを確認する
    - B) calicoctl ipam show を使用して割り当て状況を確認する
    - C) Node のメモリ使用量を監視する
    - D) Pod の再起動回数を確認する

<details>
<summary>回答を表示</summary>

**回答: B) calicoctl ipam show を使用して割り当て状況を確認する**

**解説:**
`calicoctl ipam show` コマンドは、すべてのプールとブロックにわたる合計 IP 数、割り当て済み IP 数、利用可能な IP 数を含む IPAM の割り当て状況を表示します。`--show-blocks` フラグは Node ごとの詳細なブロック割り当て情報を提供し、枯渇の問題を特定するのに役立ちます。

</details>

12. Kubernetes API ではなく etcd を Calico の datastore として選択すべきなのはいつですか？
    - A) Node が 100 台未満のクラスターの場合
    - B) マネージド Kubernetes Service で実行している場合
    - C) 非常に大規模なクラスターまたは非 Kubernetes デプロイメントの場合
    - D) eBPF dataplane を使用する場合

<details>
<summary>回答を表示</summary>

**回答: C) 非常に大規模なクラスターまたは非 Kubernetes デプロイメントの場合**

**解説:**
etcd datastore は、Kubernetes API server の負荷が懸念される非常に大規模なクラスター、または非 Kubernetes デプロイメント（ベアメタル、VM）に推奨されます。ほとんどの Kubernetes デプロイメントでは、別個の etcd クラスターを管理する必要がないため、Kubernetes datastore の方が簡単です。

</details>
