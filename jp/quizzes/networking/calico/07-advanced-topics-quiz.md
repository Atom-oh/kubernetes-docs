# Calico の高度なトピックに関するクイズ

> **関連ドキュメント**: [高度なトピック](../../../networking/calico/07-advanced-topics.md)
> **最終更新**: 2026年9月12日

## クイズ

1. Calico のブロックベース IPAM では、/26 CIDR ブロックにいくつの IP アドレスが含まれますか？
   - A) 32 個
   - B) 64 個
   - C) 128 個
   - D) 256 個

<details>
<summary>解答を表示</summary>

**解答: B) 64 個**

**解説:**
IPv4 の /26 には 64 個のアドレスが含まれます。ただし、必ずしも 64 個すべてを Pod に使用できるわけではありません。Calico for Windows は、自身が所有するブロックごとに 4 個を予約します。IPv6 の既定値である /122 も 64 個のアドレスを含みます。プールを作成するときに `blockSize` を設定してください。作成後にその値を変更して調整することはできません。

</details>

2. Calico IPAM の IP ブロックアフィニティとは何ですか？
   - A) 同じラベルを持つ Pod は必ず同じブロックから IP を取得する
   - B) ノードが特定の IP ブロックを確保し、優先的に使用する
   - C) Service にはエンドポイントに近い IP が割り当てられる
   - D) IP アドレスがアベイラビリティーゾーンごとにグループ化される

<details>
<summary>解答を表示</summary>

**解答: B) ノードが特定の IP ブロックを確保し、優先的に使用する**

**解説:**
ノードは、プールの選択条件と上限の範囲内で、自身にアフィニティがあるブロックから優先して割り当てます。1 つのノードが複数のブロックを持つこともあり、許可されたアドレスの借用によって、より具体的な経路が作られる場合があります。ブロックアフィニティは `Node.spec.podCIDR` と同じものではなく、ノード上のすべての Pod が同じプレフィックスを共有する保証でもありません。

</details>

3. Calico で WireGuard 暗号化を有効にするにはどうしますか？
   - A) 別の WireGuard Operator をインストールする
   - B) FelixConfiguration で `wireguardEnabled: true` を設定する
   - C) WireGuard NetworkPolicy を適用する
   - D) Kubernetes API server のフラグで有効にする

<details>
<summary>解答を表示</summary>

**解答: B) FelixConfiguration で `wireguardEnabled: true` を設定する**

**解説:**
`wireguardEnabled` は、サポート対象の IPv4 経路で WireGuard を有効にします。IPv6 用の `wireguardEnabledV6` は別の設定です。通信する両方のピアが、互換性のあるカーネルとネットワーク機能を備えている必要があります。Calico はノードの鍵を管理し、公開鍵を公開します。同一ノード内の通信や、サポート対象外のピアとの通信が、ノード間トンネルによって自動的に暗号化されるわけではありません。

</details>

4. 普遍的な性能結果を断定せずに、WireGuard の設計を説明しているのはどれですか？
   - A) WireGuard はより多くの暗号化アルゴリズムをサポートする
   - B) WireGuard は暗号方式と鍵設定を意図的に限定している
   - C) Calico WireGuard にはノードや実行環境の前提条件がない
   - D) WireGuard はより優れた圧縮を提供する

<details>
<summary>解答を表示</summary>

**解答: B) WireGuard は暗号方式と鍵設定を意図的に限定している**

**解説:**
WireGuard は暗号方式の選択肢を意図的に限定しています。CPU 負荷、スループット、ローミング、オフロードの比較結果は、実装とワークロードによって異なります。バージョンが特定されていないコード行数や、この章にある未検証の性能範囲を、普遍的なセキュリティまたは速度の順位として扱うことはできません。

</details>

5. ここで説明する Calico Enterprise Egress Gateway の主な用途は何ですか？
   - A) Service への ingress トラフィックをロードバランシングする
   - B) 外部 Service にアクセスする Pod に一貫した送信元 IP アドレスを提供する
   - C) DNS 応答をキャッシュして名前解決を高速化する
   - D) 外向き API 呼び出しをレート制限する

<details>
<summary>解答を表示</summary>

**解答: B) 外部 Service にアクセスする Pod に一貫した送信元 IP アドレスを提供する**

**解説:**
トランジットゲートウェイ Pod は、選択されたクライアントのトラフィックを SNAT し、制御された送信元アドレスの範囲を外部に示します。実際に相手側から観測されるアドレスは、IP プール、上流の NAT、可用性によって異なります。NetworkPolicy の Allow ルールや BGP の `serviceExternalIPs` だけでは、このルーティングや SNAT の動作は実現しません。送信元 IP の許可リストだけで、コンプライアンスやアプリケーション認可の要件をすべて満たすわけでもありません。

</details>

6. 現在の Calico Enterprise Federation 機能が提供するものは何ですか？
   - A) アプリケーションデータベースの自動レプリケーションとフェイルオーバー
   - B) リモートエンドポイントの ID と一部の Service ディスカバリー。ポリシーは各クラスター内で適用される
   - C) すべてのクラスターの一元化されたログ記録
   - D) クラスター間で統合された請求

<details>
<summary>解答を表示</summary>

**解答: B) リモートエンドポイントの ID と一部の Service ディスカバリー。ポリシーは各クラスター内で適用される**

**解説:**
Federated endpoint identity は、リモートエンドポイントの情報をローカルのポリシー計算に取り込みます。リモートポリシーをローカルエンドポイントにコピーする機能ではありません。別の Federated Services Controller が、リモート Kubernetes API を読み取ります。ルーティング可能で送信元 IP が保持される Pod 経路、および Controller の認証情報と設定が前提条件です。Typha は共用の Federation Controller ではありません。

</details>

7. Calico の Windows サポートについて正しい記述はどれですか？
   - A) Windows ノードには別の CNI プラグインが必要である
   - B) Calico は一部の機能に制限があるものの、Windows ノードをサポートする
   - C) Windows サポートは Calico Enterprise でのみ利用できる
   - D) Windows ノードは BGP ピアリングに参加できない

<details>
<summary>解答を表示</summary>

**解答: B) Calico は一部の機能に制限があるものの、Windows ノードをサポートする**

**解説:**
Calico for Windows は HNS と HostProcess を使用し、対応するプラットフォームとバージョンに制限があります。IPv4 VXLAN、またはサポート対象の非オーバーレイ BGP を利用できます。一方、レビュー対象の Windows ガイドでは、IPv6／デュアルスタック、eBPF、WireGuard、HostEndpoint ポリシー、Service 広告はサポート対象外です。OS とコンテナのビルド、および実際のプロバイダープロファイルを照合してください。

</details>

8. Calico Enterprise と Calico Open Source の主な違いは何ですか？
   - A) Enterprise は異なるデータプレーン技術を使用する
   - B) Enterprise には追加のセキュリティ、コンプライアンス、可観測性機能が含まれる
   - C) Enterprise は特定の Kubernetes ディストリビューションでのみ動作する
   - D) Enterprise は BGP をサポートしない

<details>
<summary>解答を表示</summary>

**解答: B) Enterprise には追加のセキュリティ、コンプライアンス、可観測性機能が含まれる**

**解説:**
Calico Open Source 3.32 には、すでにポリシー階層、Whisker によるフロー可視化、ステージングポリシー、Istio／Dikastes を介した HTTP ポリシーが含まれています。商用エディションでは、ドメインポリシー、Egress Gateway、リモート ID／Service、レポートなど、製品固有の機能が追加されます。機能とサポート条件は、選択する製品とバージョンによって異なります。

</details>

9. 1,000 ノードを数える場合、Tigera Operator 1.42.6 は Typha のレプリカ数をいくつに算出しますか？
   - A) 5 レプリカ
   - B) 3 レプリカ
   - C) 7 レプリカ
   - D) 10 レプリカ

<details>
<summary>解答を表示</summary>

**解答: C) 7 レプリカ**

**解説:**
レビュー対象の Operator は、N > 4 の場合に `max(3, floor(N/200)+2)` を使用するため、N が 1,000 なら 7 になります。N ≤ 2 では 1、N ≤ 4 では 2 です。これはノード数と配置条件に基づく実装上の目標値であり、「Typha 1 台あたり 200 ノード」という実測済みの容量保証ではありません。

</details>

10. Calico-IPAM のデュアルスタック構成では、どのプール設定が必要ですか？
    - A) IPv6 専用の別インストール
    - B) IPv4 と IPv6 の両方のアドレス範囲に対する IPPool の設定
    - C) eBPF データプレーンのみを使用する
    - D) ネットワークポリシーの適用を無効にする

<details>
<summary>解答を表示</summary>

**解答: B) IPv4 と IPv6 の両方のアドレス範囲に対する IPPool の設定**

**解説:**
Calico-IPAM のデュアルスタックでは、IPv4 と IPv6 の両方のプールを使用します。Kubernetes、CNI、ノードのアドレス設定、アンダーレイも両アドレスファミリーをサポートする必要があります。IPv6 のみを使用する場合、IPv4 プールは必要ありません。Felix の `ipv6Support` はブール値です。このフラグやプールを追加するだけでは、既存クラスターの IP ファミリー設定は切り替わりません。

</details>

11. Calico IPAM の IP アドレス枯渇をどのように検出できますか？
    - A) kube-apiserver のログを確認する
    - B) `calicoctl ipam show` で割り当て状況を確認する
    - C) ノードのメモリ使用量を監視する
    - D) Pod の再起動回数を確認する

<details>
<summary>解答を表示</summary>

**解答: B) `calicoctl ipam show` で割り当て状況を確認する**

**解説:**
`ipam show` は割り当て状況を表示し、`--show-blocks` を付けるとブロックの詳細も確認できます。ノードとの対応付けには BlockAffinity を確認し、利用可能なプール、予約、アフィニティやホストの上限も考慮してください。別の場所に空きアドレスがあっても、割り当てに使えるとは限りません。新しい復旧レポートで古い割り当てであることを確認してからクリーンアップし、例として掲載された IP アドレスをそのまま使わないでください。

</details>

12. Calico の datastore に直接 etcd を使うことを検討する理由は何ですか？
    - A) 100 ノード未満のクラスターである
    - B) マネージド Kubernetes サービス上で稼働している
    - C) etcd の運用と復旧計画を明示した、サポート対象の非 Kubernetes デプロイメントである
    - D) eBPF データプレーンを使用する

<details>
<summary>解答を表示</summary>

**解答: C) etcd の運用と復旧計画を明示した、サポート対象の非 Kubernetes デプロイメントである**

**解説:**
直接 etcd を使う構成は、サポート対象であり、別途設計されたデプロイメントに適する場合があります。多くの Kubernetes 環境では Kubernetes datastore の方が簡単で、現在の eBPF データプレーンでは Kubernetes datastore が必須です。選択の根拠となる固定の「5,000 ノード」しきい値や、すべての環境に当てはまる読み取り速度の比較はありません。

</details>
