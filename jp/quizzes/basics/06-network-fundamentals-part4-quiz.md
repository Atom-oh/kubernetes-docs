# ネットワーク基礎 第4部クイズ: リクエストの経路とクラウド

> **最終更新日**: 2026年9月11日

リクエストの全経路と、クラウド/Kubernetes の対応関係について理解度を確認します。

## 選択式問題

1. 新しい HTTPS 接続における概念上の依存順序として正しいのはどれですか？（cache と既存の接続は除く）
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) server address を解決する → link/IP 接続を確立する → TCP+TLS または QUIC handshake → HTTP request
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) TCP connection → DNS lookup → TLS → routing → HTTP

<details>
<summary>回答を表示</summary>

**回答: B) server address を解決する → link/IP 接続を確立する → TCP+TLS または QUIC handshake → HTTP request**

**解説:**
これは依存関係の概要であり、packet trace ではありません。DNS message も、すでに link/IP 接続を使用しています。ARP や IPv6 Neighbor Discovery は、DNS や後続の通信中に発生する場合があります。NAT は任意であり、routing は該当するすべての packet に適用されます。HTTP/3 は TLS1.3 を統合した QUIC を使います。HTTP/1.1 と HTTP/2 は、HTTPS では別の TLS handshake を伴う TCP を一般的に使います。

</details>

2. kube-proxy を使用する cluster で、通常の ClusterIP Service の転送を説明する組み合わせはどれですか？
   - A) CoreDNS: DHCP
   - B) kube-proxy: NAT + L4 load balancing
   - C) CNI plugin: TLS termination
   - D) NetworkPolicy: BGP routing

<details>
<summary>回答を表示</summary>

**回答: B) kube-proxy: NAT + L4 load balancing**

**解説:**
Linux では kube-proxy が iptables または nftables を設定します。IPVS mode は Kubernetes 1.35 以降 deprecated です。eBPF ベースの Service 実装は kube-proxy を置き換えられますが、kube-proxy の eBPF mode ではありません。Service/EndpointSlice の状態が対象 endpoint を提供します。Headless Service は ClusterIP を使用せず、NetworkPolicy には対応する実装が必要です。

</details>

3. endpoint の依存関係と総コストを確認した後、サポート対象の AWS service traffic に対する NAT Gateway の処理を減らせる方法はどれですか？
   - A) Region ごとに NAT Gateway を1つに集約する
   - B) DNS、route、access policy を適切に設定し、サポート対象の service traffic に適した VPC endpoint を使う
   - C) すべての Pod に public IP を付与する
   - D) IPv6 を無効にする

<details>
<summary>回答を表示</summary>

**回答: B) DNS、route、access policy を適切に設定し、サポート対象の service traffic に適した VPC endpoint を使う**

**解説:**
Endpoint によって対象 service の traffic を NAT 経路から外せますが、interface endpoint には時間単位/データ処理の料金があり、構成も影響します。S3/DynamoDB gateway endpoint には追加の endpoint 料金がありません。Private ECR image pull では通常、ecr.api と ecr.dkr の interface endpoint に加えて、S3 経路、private DNS、適切な access 設定が必要です。Pull-through cache の初回 pull や外部の Windows layer では、引き続きインターネットアクセスが必要になる場合があります。総コストを計算し、必要な egress を維持してください。節約や port exhaustion の解消が一律に保証されるわけではありません。

</details>

---

[学習資料に戻る](../../basics/06-network-fundamentals-part4.md) | [次のクイズ: Cluster Architecture](../core/01-cluster-architecture-quiz.md)
