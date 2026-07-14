# Kubernetes ネットワーキング概要クイズ

このクイズでは、Kubernetes ネットワーキングの基礎、CNI (Container Network Interface)、およびさまざまな CNI ソリューションに関する理解度を確認します。

## クイズの問題

### 1. Kubernetes ネットワーキングモデルのコア要件では**ない**ものはどれですか？

A. すべての Pod は NAT なしで他のすべての Pod と通信できる
B. すべての Node は NAT なしで各 Pod と通信できる
C. Pod が自身のものとして認識する IP は、他者から見える IP と同じである
D. すべての Pod は、再起動後も維持される静的 IP アドレスを持つ必要がある

<details>
<summary>回答を表示</summary>

**回答: D. すべての Pod は、再起動後も維持される静的 IP アドレスを持つ必要がある**

**解説:**
Kubernetes ネットワーキングモデルのコア要件は、次の 3 つです。
1. すべての Pod は NAT なしで他のすべての Pod と通信できる
2. すべての Node は NAT なしで各 Pod と通信できる
3. Pod が自身のものとして認識する IP は、他者から見える IP と同じである

Pod IP アドレスは一時的です。Pod が再起動すると、新しい IP が割り当てられます。これがまさに Service が必要な理由です。

</details>

### 2. CNI (Container Network Interface) の主な役割は何ですか？

A. Pod スケジューリングの決定を行うために Kubernetes API server と通信する
B. コンテナのネットワークインターフェースを作成し、IP アドレスを割り当てる
C. Kubernetes Service のロードバランシングを実装する
D. コンテナイメージをダウンロードしてキャッシュする

<details>
<summary>回答を表示</summary>

**回答: B. コンテナのネットワークインターフェースを作成し、IP アドレスを割り当てる**

**解説:**
CNI は、コンテナネットワーク接続のための標準インターフェースです。主な役割は次のとおりです。
- コンテナの作成時にネットワークインターフェースを作成する (veth pairs)
- IP アドレスを割り当てる (IPAM)
- ルーティングルールを設定する
- コンテナの削除時にネットワークリソースをクリーンアップする

Kubelet は CNI plugin を呼び出して Pod ネットワーキングを設定します。

</details>

### 3. Overlay と Underlay (Native Routing) ネットワークの正しい違いは何ですか？

A. Overlay はより高いパフォーマンスを提供し、Underlay はより多くのオーバーヘッドを伴う
B. Overlay は既存ネットワーク上に仮想ネットワークを構築し、Underlay は物理ネットワーク上で直接ルーティングする
C. Overlay は BGP を使用し、Underlay は VXLAN を使用する
D. Overlay は AWS でのみ利用でき、Underlay はオンプレミス専用である

<details>
<summary>回答を表示</summary>

**回答: B. Overlay は既存ネットワーク上に仮想ネットワークを構築し、Underlay は物理ネットワーク上で直接ルーティングする**

**解説:**
- **Overlay Network**: VXLAN、IPIP などのカプセル化を使用して、既存ネットワーク上に仮想ネットワークを構築します。設定は簡単ですが、カプセル化のオーバーヘッドがあります。
- **Underlay (Native Routing)**: より高いパフォーマンスのために物理ネットワーク上で直接ルーティングします。BGP などを使用し、ネットワークインフラストラクチャとの統合が必要です。

</details>

### 4. クラスター内からのみアクセス可能な Kubernetes Service type はどれですか？

A. NodePort
B. LoadBalancer
C. ClusterIP
D. ExternalName

<details>
<summary>回答を表示</summary>

**回答: C. ClusterIP**

**解説:**
Kubernetes Service type の特性:
- **ClusterIP**: クラスター内からのみアクセス可能な仮想 IP を割り当てる (デフォルト)
- **NodePort**: すべての Node の特定ポート (30000-32767) を介した外部アクセス
- **LoadBalancer**: 外部アクセスのためにクラウドロードバランサーをプロビジョニングする
- **ExternalName**: 外部 DNS 名に対する CNAME レコードを作成する

</details>

### 5. コアとして eBPF 技術を使用する CNI はどれですか？

A. Flannel
B. Weave Net
C. Cilium
D. AWS VPC CNI

<details>
<summary>回答を表示</summary>

**回答: C. Cilium**

**解説:**
Cilium は、eBPF (extended Berkeley Packet Filter) をコア技術として使用する CNI です。eBPF の利点:
- カーネルレベルのネットワーク処理による高パフォーマンス
- iptables と比較してより効率的なパケット処理
- L7 の可視性と Policy の適用
- kube-proxy を置き換え可能

Calico も eBPF mode をサポートしていますが、Cilium は最初から eBPF をコアとして設計されていました。

</details>

### 6. AWS VPC CNI の特性では**ない**ものはどれですか？

A. 各 Pod に実際の VPC IP アドレスを割り当てる
B. EC2 instance ENI (Elastic Network Interface) を利用する
C. Pod ごとに割り当て可能な IP 数は instance type によって制限される
D. L7 Network Policy をネイティブでサポートする

<details>
<summary>回答を表示</summary>

**回答: D. L7 Network Policy をネイティブでサポートする**

**解説:**
AWS VPC CNI の特性:
- Pod に実際の VPC IP アドレスを割り当てる (VPC native)
- EC2 ENI の Secondary IP を使用する
- 最大 Pod 数は instance type によって制限される (ENI 数 × ENI あたりの IP 数)
- デフォルトでは L3-L4 Network Policy のみをサポートする (L7 には Calico または Cilium が必要)

L7 Network Policy には、Cilium のような追加ソリューションが必要です。

</details>

### 7. BGP (Border Gateway Protocol) をサポートする CNI の組み合わせはどれですか？

A. Flannel, Weave Net
B. Calico, Cilium
C. AWS VPC CNI, Flannel
D. Weave Net, AWS VPC CNI

<details>
<summary>回答を表示</summary>

**回答: B. Calico, Cilium**

**解説:**
BGP をサポートする CNI:
- **Calico**: BGP はコア機能であり、ToR switch peering、Route Reflector をサポートする
- **Cilium**: BGP をサポート (v1.10+) しており、multi-cluster 環境で有用

BGP をサポートしない CNI:
- **Flannel**: シンプルな overlay network で、BGP をサポートしない
- **Weave Net**: 独自のルーティングプロトコルを使用し、BGP をサポートしない
- **AWS VPC CNI**: VPC native routing を使用し、BGP をサポートしない

</details>

### 8. Kubernetes Network Policy の対象と**ならない**トラフィックはどれですか？

A. Pod から別の Pod へのトラフィック
B. Pod から外部インターネットへのトラフィック
C. 同じ Pod 内のコンテナ間における localhost トラフィック
D. 外部ソースから Pod に入るトラフィック

<details>
<summary>回答を表示</summary>

**回答: C. 同じ Pod 内のコンテナ間における localhost トラフィック**

**解説:**
Network Policy は Pod 間のトラフィックを制御します。同じ Pod 内のコンテナは次のとおりです。
- 同じ network namespace を共有する
- localhost (127.0.0.1) を介して通信する
- Network Policy の対象ではない

Network Policy の対象となるトラフィック:
- Pod 間の Ingress/Egress トラフィック
- Pod から外部への Egress トラフィック
- 外部から Pod への Ingress トラフィック

</details>

### 9. 大規模 Kubernetes クラスター (500+ Node) 向けに CNI を選択する際、最も重要な考慮事項は何ですか？

A. UI dashboard が提供されているかどうか
B. Control plane のスケーラビリティとデータ同期効率
C. ロゴデザインとドキュメントの品質
D. 新バージョンのリリース頻度

<details>
<summary>回答を表示</summary>

**回答: B. Control plane のスケーラビリティとデータ同期効率**

**解説:**
大規模クラスター向けに CNI を選択する際の考慮事項:

1. **Control Plane Scalability**:
   - Calico: Typha コンポーネントが API server の負荷を軽減する
   - Cilium: Operator mode による効率的な同期

2. **Data Synchronization**:
   - Node agent ごとのリソース使用量
   - Policy 更新の伝播時間

3. **Performance**:
   - eBPF ベースのソリューションは iptables ベースよりも優れたスケーラビリティを持つ
   - ルール数の増加に伴うパフォーマンス低下

</details>

### 10. Ingress と Service の正しい違いは何ですか？

A. Ingress は L4 で動作し、Service は L7 で動作する
B. Ingress は HTTP/HTTPS ルーティングルールを定義し、Service は Pod のセットにネットワークエンドポイントを提供する
C. Ingress はクラスター内部通信のみをサポートし、Service は外部通信のみをサポートする
D. Ingress は TCP のみをサポートし、Service は UDP のみをサポートする

<details>
<summary>回答を表示</summary>

**回答: B. Ingress は HTTP/HTTPS ルーティングルールを定義し、Service は Pod のセットにネットワークエンドポイントを提供する**

**解説:**
- **Service**: Pod のセットに安定したネットワークエンドポイントを提供する (L4)
  - ClusterIP、NodePort、LoadBalancer type
  - TCP/UDP プロトコルをサポートする

- **Ingress**: HTTP/HTTPS トラフィックのルーティングルールを定義する (L7)
  - Host-based routing
  - Path-based routing
  - TLS termination
  - Ingress Controller が実際の実装を提供する

Ingress は最終的にトラフィックをバックエンド Service に転送します。

</details>

---

## 追加学習リソース

- [Kubernetes Networking Model](https://kubernetes.io/docs/concepts/cluster-administration/networking/)
- [CNI Specification](https://github.com/containernetworking/cni/blob/master/SPEC.md)
- [Network Policy Guide](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
