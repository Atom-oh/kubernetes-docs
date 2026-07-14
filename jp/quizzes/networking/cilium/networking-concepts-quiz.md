# Cilium ネットワーキングの概念クイズ

> **サポート対象バージョン**: Cilium 1.17
> **最終更新**: February 22, 2026

## OSI モデルと基本概念

1. **Cilium が主に動作する OSI モデルのレイヤーはどれですか？**
   - A) L2（データリンク層）
   - B) L3/L4（ネットワーク層/トランスポート層）
   - C) L7（アプリケーション層）
   - D) L3 から L7 までのすべてのレイヤー

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: D) L3 から L7 までのすべてのレイヤー</p>
   <p><strong>解説</strong>: Cilium は、L3/L4（IP アドレス、ポート）だけでなく、L7（HTTP、gRPC、Kafka など）のレイヤーまでネットワーキングおよびセキュリティ機能を提供します。</p>
   </details>

2. **次のうち、L2（データリンク層）アドレスはどれですか？**
   - A) IP アドレス
   - B) MAC アドレス
   - C) ポート番号
   - D) URL

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) MAC アドレス</p>
   <p><strong>解説</strong>: MAC（Media Access Control）アドレスはネットワークインターフェイスカードの一意の識別子であり、L2 レイヤーで使用されます。</p>
   </details>

3. **次のうち、L3（ネットワーク層）プロトコルはどれですか？**
   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) IP</p>
   <p><strong>解説</strong>: IP（Internet Protocol）は、ネットワーク層（L3）におけるパケットルーティングを担うプロトコルです。</p>
   </details>

## コンテナネットワーキング

4. **Cilium のデフォルトネットワークモデルは何ですか？**
   - A) ブリッジモード
   - B) オーバーレイネットワーク
   - C) アンダーレイネットワーク
   - D) Host ネットワーク

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) オーバーレイネットワーク</p>
   <p><strong>解説</strong>: Cilium は、デフォルトで VXLAN または Geneve を使用するオーバーレイネットワークモデルを使用します。</p>
   </details>

5. **Cilium が使用するデフォルトのオーバーレイプロトコルは何ですか？**
   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) VXLAN</p>
   <p><strong>解説</strong>: Cilium は、オーバーレイネットワークを構成するために、デフォルトで VXLAN（Virtual Extensible LAN）プロトコルを使用します。</p>
   </details>

6. **Cilium の Direct Routing モードの主な利点は何ですか？**
   - A) より高いセキュリティ
   - B) より優れた互換性
   - C) より低いレイテンシーとより高いスループット
   - D) より簡単なセットアップ

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) より低いレイテンシーとより高いスループット</p>
   <p><strong>解説</strong>: Direct Routing モードはオーバーレイカプセル化を使用しないため、より低いレイテンシーとより高いスループットを提供します。</p>
   </details>

## IP アドレス管理（IPAM）

7. **Cilium のデフォルト IPAM モードは何ですか？**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) CRD ベース
   - D) AWS ENI

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) Cluster Scope</p>
   <p><strong>解説</strong>: Cilium のデフォルト IPAM モードは Cluster Scope であり、クラスター全体にわたって IP アドレスを一元的に割り当てます。</p>
   </details>

8. **AWS EKS で Cilium を使用する場合に推奨される IPAM モードは何ですか？**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) CRD ベース

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) AWS ENI</p>
   <p><strong>解説</strong>: AWS EKS では、VPC IP アドレスを Pod に直接割り当てるため、AWS ENI IPAM モードの使用が推奨されます。</p>
   </details>

9. **Cilium の IPAM「PodCIDR」モードは、どの Kubernetes 機能を利用しますか？**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>解説</strong>: Cilium の PodCIDR IPAM モードは、Kubernetes が各 Node に割り当てる NodeSpec.PodCIDR フィールドを利用します。</p>
   </details>

## Service とロードバランシング

10. **Cilium の kube-proxy 置換モードで提供されない機能はどれですか？**
    - A) ClusterIP Service のサポート
    - B) NodePort Service のサポート
    - C) LoadBalancer Service のサポート
    - D) Service mesh 機能

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) Service mesh 機能</p>
    <p><strong>解説</strong>: Cilium の kube-proxy 置換モードは基本的な Kubernetes Service タイプをサポートしますが、Service mesh 機能は別の Cilium Service Mesh 機能を通じて提供されます。</p>
    </details>

11. **Cilium は Service のロードバランシングにどのアルゴリズムを使用しますか？**
    - A) ラウンドロビン
    - B) 最小接続数
    - C) IP ハッシュ
    - D) 上記すべて

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) 上記すべて</p>
    <p><strong>解説</strong>: Cilium は、ラウンドロビン、最小接続数、IP ハッシュを含むさまざまなロードバランシングアルゴリズムをサポートします。</p>
    </details>

12. **Cilium の Global Service 機能で可能になることは何ですか？**
    - A) グローバルに分散した Service へのアクセス
    - B) 複数のクラスター間での Service ロードバランシング
    - C) グローバル IP アドレスの割り当て
    - D) グローバルネットワークポリシーの適用

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) 複数のクラスター間での Service ロードバランシング</p>
    <p><strong>解説</strong>: Cilium の Global Service 機能は、Cluster Mesh を通じて複数のクラスターにまたがる同一 Service のロードバランシングを可能にします。</p>
    </details>

## ネットワークポリシー

13. **Cilium ネットワークポリシーの「toCIDR」ルールで許可されるのは何ですか？**
    - A) 特定の IP アドレス範囲へのトラフィック
    - B) 特定のドメイン名へのトラフィック
    - C) 特定の Service へのトラフィック
    - D) 特定のポートへのトラフィック

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) 特定の IP アドレス範囲へのトラフィック</p>
    <p><strong>解説</strong>: toCIDR ルールは、特定の IP アドレス範囲（CIDR 表記）へのトラフィックを許可するために使用されます。</p>
    </details>

14. **Cilium ネットワークポリシーの「toEntities」ルールにおける「world」エンティティは何を意味しますか？**
    - A) クラスター内部のすべてのエンドポイント
    - B) すべての外部ネットワーク
    - C) すべての Node
    - D) すべての namespace

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) すべての外部ネットワーク</p>
    <p><strong>解説</strong>: 「world」エンティティは、クラスターの外部にあるすべてのネットワークを意味します。</p>
    </details>

15. **Cilium の L7 ポリシーでサポートされていないプロトコルはどれですか？**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) SMTP</p>
    <p><strong>解説</strong>: Cilium は HTTP、gRPC、Kafka などの L7 プロトコルをサポートしますが、デフォルトでは SMTP をサポートしません。</p>
    </details>

## 高度なネットワーキングの概念

16. **Cilium の Transparent Encryption 機能では、どのプロトコルを使用できますか？**
    - A) IPsec
    - B) WireGuard
    - C) A と B の両方
    - D) TLS

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) A と B の両方</p>
    <p><strong>解説</strong>: Cilium は IPsec と WireGuard の両方を使用して、Node 間のトラフィックを暗号化できます。</p>
    </details>

17. **Cilium の Multi-cluster 機能はどの技術を使用しますか？**
    - A) Cluster Federation
    - B) Cluster Mesh
    - C) Multi-cluster Networking
    - D) Global Cluster

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) Cluster Mesh</p>
    <p><strong>解説</strong>: Cilium は Cluster Mesh 技術を使用して、複数の Kubernetes クラスター間の接続性を提供します。</p>
    </details>

18. **Cilium の BGP サポートによって可能になることは何ですか？**
    - A) 外部ルーターとのルート交換
    - B) LoadBalancer Service の外部 IP アドバタイズメント
    - C) クラスター間の直接ルーティング
    - D) 上記すべて

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) 上記すべて</p>
    <p><strong>解説</strong>: Cilium の BGP サポートにより、外部ルーターとのルート交換、LoadBalancer Service の外部 IP アドバタイズメント、およびクラスター間の直接ルーティングが可能になります。</p>
    </details>

19. **Cilium の Egress Gateway 機能の主な目的は何ですか？**
    - A) 外部トラフィックの送信元 IP アドレスを保持すること
    - B) 外部トラフィックの宛先 IP アドレスを変更すること
    - C) 外部トラフィックを暗号化すること
    - D) 外部トラフィックをブロックすること

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) 外部トラフィックの送信元 IP アドレスを保持すること</p>
    <p><strong>解説</strong>: Egress Gateway は、Pod からクラスター外部へ送信されるトラフィックを特定の IP に SNAT し、一貫した送信元 IP を提供します。</p>
    </details>

20. **Cilium の Host Routing 機能について正しい説明はどれですか？**
    - A) Host ネットワークと Pod ネットワーク間のルーティング
    - B) Host 間の直接ルーティング
    - C) Host ネットワークインターフェイスの保護
    - D) Host ベースのロードバランシング

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) Host 間の直接ルーティング</p>
    <p><strong>解説</strong>: Cilium の Host Routing は、オーバーレイネットワークを使用せずに Host 間の直接ルーティングを提供します。</p>
    </details>
