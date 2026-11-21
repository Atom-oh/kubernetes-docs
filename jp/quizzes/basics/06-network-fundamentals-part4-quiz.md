# ネットワーク基礎 第4部クイズ：リクエストの経路とクラウド

> **最終更新日**: 2026年9月11日

リクエストがたどる全経路と、クラウド／Kubernetes における対応関係の理解度を確認します。

## 選択問題

1. 新しい HTTPS 接続の場合、概念上の依存関係として正しい順序はどれですか（キャッシュと既存の接続は除外します）。
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) サーバーアドレスを解決する → リンク／IP 接続を利用する → TCP+TLS または QUIC のハンドシェイク → HTTP リクエスト
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) TCP 接続 → DNS ルックアップ → TLS → ルーティング → HTTP

<details>
<summary>回答を表示</summary>

**回答: B) サーバーアドレスを解決する → リンク／IP 接続を利用する → TCP+TLS または QUIC のハンドシェイク → HTTP リクエスト**

**解説:**
これは依存関係の概要であり、パケットのトレースではありません。DNS メッセージもすでにリンク／IP 接続を利用しており、DNS 通信中またはその後の通信で ARP や IPv6 Neighbor Discovery が発生する場合があります。NAT は任意であり、ルーティングは該当するすべてのパケットに適用されます。HTTP/3 は TLS 1.3 を統合した QUIC を使用します。HTTP/1.1 と HTTP/2 は、HTTPS では一般に、別個の TLS ハンドシェイクを伴う TCP を使用します。

</details>

2. kube-proxy を使用するクラスターで、通常の ClusterIP Service の転送を表す組み合わせはどれですか。
   - A) CoreDNS: DHCP
   - B) kube-proxy: NAT + L4 負荷分散
   - C) CNI プラグイン: TLS 終端
   - D) NetworkPolicy: BGP ルーティング

<details>
<summary>回答を表示</summary>

**回答: B) kube-proxy: NAT + L4 負荷分散**

**解説:**
Linux では、kube-proxy は iptables または nftables を設定します。IPVS モードは Kubernetes 1.35 以降、非推奨となっています。eBPF ベースの Service 実装で kube-proxy を置き換えることはできますが、これは kube-proxy の eBPF モードではありません。Service／EndpointSlice の状態によって、対象となるエンドポイントが提供されます。ヘッドレス Service は ClusterIP を使用せず、NetworkPolicy はそれをサポートする実装を必要とします。

</details>

3. エンドポイントの依存関係と総コストを確認したうえで、サポートされる AWS サービス通信に対する NAT Gateway の処理を軽減できる選択肢はどれですか。
   - A) リージョンごとに NAT Gateway を 1 つに集約する
   - B) 必要な DNS、ルート、アクセス ポリシーを設定したうえで、サポートされるサービス通信に適切な VPC エンドポイントを使用する
   - C) すべての Pod にパブリック IP を割り当てる
   - D) IPv6 を無効にする

<details>
<summary>回答を表示</summary>

**回答: B) 必要な DNS、ルート、アクセス ポリシーを設定したうえで、サポートされるサービス通信に適切な VPC エンドポイントを使用する**

**解説:**
エンドポイントを使うと、該当するサービス通信を NAT 経由の経路から外せます。ただし、インターフェイスエンドポイントには時間単位およびデータ転送の料金がかかり、ネットワーク構成も重要です。S3／DynamoDB のゲートウェイエンドポイントには追加料金がかかりません。プライベート ECR イメージのプルには、通常、ecr.api と ecr.dkr のインターフェイスエンドポイントに加えて、S3 への経路、プライベート DNS、適切なアクセス設定が必要です。pull-through cache からの初回プルや、外部の Windows レイヤーでは、インターネットアクセスが引き続き必要になる場合があります。総コストを計算し、必要な外向き通信を維持してください。コスト削減やポート枯渇の解消が常に保証されるわけではありません。

</details>

---

[学習教材に戻る](../../basics/06-network-fundamentals-part4.md) | [次のクイズ：第5部](./06-network-fundamentals-part5-quiz.md)
