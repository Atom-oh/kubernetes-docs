# Cilium ネットワーク概念クイズ

> **レビュー基準**: Cilium 1.20.3。
> **最終レビュー日**: 2026 年 10 月 16 日。

[ガイドに戻る](../../../networking/cilium/networking-concepts.md)

## OSI と基本概念

1. **Cilium のポリシー機能について正しい説明はどれですか？**

   - A) 一般的な MAC アドレスファイアウォールのみ
   - B) プロキシ統合のない L3/L4 のみ
   - C) HTTP ポリシーのみ
   - D) L3/L4 制御と、構成されたサポート対象の L7 ルール

   <details>
   <summary>解答を表示</summary>

   **解答: D) L3/L4 制御と、構成されたサポート対象の L7 ルール**

   Cilium は L3/L4 の適用に加え、サポート対象の HTTP/gRPC および DNS プロキシ機能を組み合わせます。これは、OSI のすべてのレイヤーを実装するという意味でも、廃止された Kafka L7 API をサポートするという意味でもありません。

   </details>

2. **リンク層アドレスはどれですか？**

   - A) IP アドレス
   - B) MAC アドレス
   - C) ポート番号
   - D) URL

   <details>
   <summary>解答を表示</summary>

   **解答: B) MAC アドレス**

   MAC アドレスはリンク層のインターフェイスを識別します。ローカルに割り当てたり変更したりできるため、グローバルな一意性や真正性が保証されるわけではありません。

   </details>

3. **ネットワーク層で IP アドレスを提供するプロトコルはどれですか？**

   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP

   <details>
   <summary>解答を表示</summary>

   **解答: C) IP**

   IP は論理アドレスとネットワーク層でのパケット配送を提供します。TCP と UDP は異なるトランスポート層の通信特性を持ちます。

   </details>

## コンテナネットワーキング

4. **プラットフォーム固有の上書きがない場合、Cilium Helm の一般的なルーティング既定値はどれですか？**

   - A) Docker ブリッジ
   - B) トンネル／オーバーレイモード
   - C) 必須の BGP ネイティブモード
   - D) すべてのワークロードでホストネットワーキング

   <details>
   <summary>解答を表示</summary>

   **解答: B) トンネル／オーバーレイモード**

   一般的な既定値はトンネルモードです。プラットフォーム固有のインストールプロファイルで別のモードを選ぶこともできます。これは EKS やクラウド全体で不変の設定ではありません。

   </details>

5. **一般的な Cilium トンネルプロファイルで既定のプロトコルはどれですか？**

   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS

   <details>
   <summary>解答を表示</summary>

   **解答: A) VXLAN**

   既定のトンネルプロトコルは VXLAN で、Cilium の既定では UDP ポート 8472 を使います。標準 VXLAN に割り当てられた UDP ポートは 4789 です。

   </details>

6. **ネイティブルーティングの具体的な特性はどれですか？**

   - A) 自動暗号化
   - B) 戻り経路が不要
   - C) その経路ではオーバーレイのカプセル化がない
   - D) スループットが必ず向上する

   <details>
   <summary>解答を表示</summary>

   **解答: C) その経路ではオーバーレイのカプセル化がない**

   ネイティブルーティングはオーバーレイヘッダーを使いませんが、Pod への到達性と戻り経路が正しく設定されている必要があります。性能はワークロードと実装に依存します。

   </details>

## IPAM

7. **プラットフォーム固有の上書きがない場合、Helm の一般的な IPAM 既定値はどれですか？**

   - A) kubernetes
   - B) cluster-pool
   - C) PodCIDR という名前のモード
   - D) eni

   <details>
   <summary>解答を表示</summary>

   **解答: B) cluster-pool**

   cluster-pool モードでは、Operator がノード CIDR を割り当て、各 Agent がローカルで Pod IP を割り当てます。曖昧な「Cluster Scope」という表現ではなく、実際のモード名を使ってください。

   </details>

8. **EC2 ENI と VPC アドレスを使う Cilium IPAM モードはどれですか？**

   - A) Kubernetes host-scope
   - B) cluster-pool
   - C) ENI
   - D) 汎用 CRD ベース

   <details>
   <summary>解答を表示</summary>

   **解答: C) ENI**

   ENI モードには AWS 固有の前提条件があります。あらゆる EKS コンピューティングモードや CNI チェイニング構成に対する普遍的な推奨ではありません。

   </details>

9. **ipam.mode: kubernetes では、Node のどのフィールドを使いますか？**

   - A) spec.podCIDR / spec.podCIDRs
   - B) spec.CIDR
   - C) spec.Subnet
   - D) spec.IPRange

   <details>
   <summary>解答を表示</summary>

   **解答: A) spec.podCIDR / spec.podCIDRs**

   Kubernetes がノードの Pod CIDR を割り当てます。Cilium は Kubernetes host-scope IPAM でこれらを使います。PodCIDR は IPAM モードの正式な名前ではありません。

   </details>

## Service とロードバランシング

10. **kube-proxy の置き換えだけでは有効にならない機能はどれですか？**

   - A) ClusterIP の転送
   - B) NodePort の転送
   - C) サポート対象の LoadBalancer Service の転送
   - D) ワークロードの mTLS

   <details>
   <summary>解答を表示</summary>

   **解答: D) ワークロードの mTLS**

   Service の転送と、ワークロードの認証／暗号化は別の機能です。外部ロードバランサーのプロビジョニングにも、対応するコントローラーまたはプロバイダーが必要です。

   </details>

11. **Cilium の BPF Service ロードバランシングアルゴリズムはどれですか？**

   - A) Random と Maglev
   - B) Round robin のみ
   - C) 既定で Least connections
   - D) Maglev のタイムアウトを定期的にローテーション

   <details>
   <summary>解答を表示</summary>

   **解答: A) Random と Maglev**

   既定は Random で、サポート対象の経路では Maglev を選択肢として使えます。Envoy のアルゴリズム、ClientIP アフィニティ、アフィニティのタイムアウトは、それぞれ別の概念です。

   </details>

12. **構成済みの Global Service で可能になることは何ですか？**

   - A) 世界中で使えるパブリック IP アドレスの自動割り当て
   - B) 接続されたクラスター間での Service ロードバランシング
   - C) すべてのポリシーの自動レプリケーション
   - D) 共有永続ストレージ

   <details>
   <summary>解答を表示</summary>

   **解答: B) 接続されたクラスター間での Service ロードバランシング**

   ClusterMesh と、一致する Service 名および namespace が必要です。エンドポイントやキャッシュの動作、障害時の挙動も引き続き検証してください。

   </details>

## ネットワークポリシー

13. **toCIDR が選択するものは何ですか？**

   - A) 宛先アドレス範囲
   - B) 認証済み DNS ホスト名
   - C) 名前付き Service のみ
   - D) TCP ポートのみ

   <details>
   <summary>解答を表示</summary>

   **解答: A) 宛先アドレス範囲**

   CIDR セレクターにはエンドポイントの分類規則があります。このバージョンでは、管理対象のクラスター内 Pod／ノードは既定で除外され、明示的な Beta オプトインで対象にできます。これは認証の仕組みではありません。

   </details>

14. **world エンティティが表すものは何ですか？**

   - A) 既知のクラスター ID すべて
   - B) 既知のクラスター／ClusterMesh ID ではない外部エンドポイント
   - C) Kubernetes ノードすべて
   - D) namespace すべて

   <details>
   <summary>解答を表示</summary>

   **解答: B) 既知のクラスター／ClusterMesh ID ではない外部エンドポイント**

   world は、すべてのクラスターにあるすべてのエンドポイントの同義語ではありません。適切なエンティティ／ID の範囲と必要なポートを選んでください。

   </details>

15. **以前の Cilium L7 機能のうち、廃止されたものはどれですか？**

   - A) HTTP パス照合
   - B) DNS クエリルール
   - C) Kafka トピックルール
   - D) HTTP メソッド照合

   <details>
   <summary>解答を表示</summary>

   **解答: C) Kafka トピックルール**

   現行のポリシーは、HTTP/gRPC 関連のプロキシ機能と DNS ルールをサポートします。古い Kafka ポリシーの例を現行 API に流用しないでください。

   </details>

## 高度な概念

16. **Cilium のノード間トランスポート暗号化モードの組み合わせはどれですか？**

   - A) HTTP と DNS
   - B) TCP と UDP
   - C) IPsec と WireGuard
   - D) Relay と Prometheus

   <details>
   <summary>解答を表示</summary>

   **解答: C) IPsec と WireGuard**

   適切なノード暗号化モードを選び、対象範囲を検証してください。SPIRE の相互認証と Beta の ztunnel ワークロード mTLS は役割も前提条件も異なります。

   </details>

17. **Cilium のマルチクラスター用ネットワーキング機能の名称は何ですか？**

   - A) Cluster Federation
   - B) ClusterMesh
   - C) Global Cluster
   - D) NodePort Mesh

   <details>
   <summary>解答を表示</summary>

   **解答: B) ClusterMesh**

   ClusterMesh はネットワークメタデータを共有し、構成済みのクラスター間接続をサポートします。アドレス設定、信頼関係、アンダーレイの前提条件は別途満たす必要があります。

   </details>

18. **Cilium BGP Control Plane の役割は何ですか？**

   - A) 学習したすべての経路をローカルデータパスに設定する
   - B) 選択した Pod／Service のプレフィックスをピアにアドバタイズする
   - C) DNS レコードを自動作成する
   - D) すべてのクラスター間通信を保証する

   <details>
   <summary>解答を表示</summary>

   **解答: B) 選択した Pod／Service のプレフィックスをピアにアドバタイズする**

   経路のアドバタイズは、アドレスの割り当てや実際のパケット転送とは別です。ピア側の経路を調べ、両方向の通信をテストしてください。

   </details>

19. **Egress Gateway は、条件に一致する送信トラフィックに何を行いますか？**

   - A) 選択したゲートウェイ IP に SNAT する
   - B) すべての元の Pod 送信元 IP を保持する
   - C) 外部向けトラフィックを自動的に暗号化する
   - D) 前提条件なしでゲートウェイインターフェイスを作成する

   <details>
   <summary>解答を表示</summary>

   **解答: A) 選択したゲートウェイ IP に SNAT する**

   Egress Gateway はアドレス変換によって、構成した送信元アドレスを提供します。準備済みのインターフェイスと経路に加え、新しい Pod にポリシーが反映されるまでの収束も考慮する必要があります。

   </details>

20. **BPF host routing が最適化するものは何ですか？**

   - A) ネイティブ／オーバーレイ間の自動フォールバック
   - B) ホスト内部のパケット転送とホストスタックの利用
   - C) ホストファイアウォールの認可
   - D) ストレージ暗号化

   <details>
   <summary>解答を表示</summary>

   **解答: B) ホスト内部のパケット転送とホストスタックの利用**

   BPF host routing は、前提条件と統合上の制約に応じて、ホストスタック／netfilter の一部を迂回できます。ノード間でネイティブルーティングとトンネルルーティングのどちらを選ぶかとは別の機能です。

   </details>
