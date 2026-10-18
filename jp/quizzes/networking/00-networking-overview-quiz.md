# Kubernetes ネットワーキング概要クイズ

2026 年 9 月 11 日確認。[ネットワーキング概要](../../networking/README.md) と公式リファレンスで、バージョンやプラットフォームごとの条件も確認してください。

## 問題

### 1. Kubernetes のネットワーキングモデルで保証されない説明はどれですか？

- A. 通常の Pod は、意図的な分離が適用される場合を除き、Pod ネットワーク上で直接通信できる
- B. ノード上のエージェントは、そのノード上の Pod に到達できる
- C. 通常の Pod 内のコンテナは、Pod のネットワーク namespace を共有する
- D. 再作成された Pod は、必ず同じ IP を維持する

<details>
<summary>解答を表示</summary>

**解答: D. 再作成された Pod は、必ず同じ IP を維持する**

置き換え後の Pod には別の IP が割り当てられることがあります。同じ Pod 内でコンテナを再起動しても、ネットワーク sandbox が必ず作り直されるわけではありません。Service は変化するエンドポイントに対して安定した名前解決を提供します。個々の接続が成功するかどうかは、NetworkPolicy やルーティングにも左右されます。

</details>

### 2. 現在の Kubernetes で CNI が主に担う役割は何ですか？

- A. API server 経由で Pod をスケジュールする
- B. コンテナネットワークとアドレスを構成するためのランタイムインターフェイスを提供する
- C. すべての Service 負荷分散実装を置き換える
- D. コンテナイメージをダウンロードする

<details>
<summary>解答を表示</summary>

**解答: B. コンテナネットワークとアドレスを構成するためのランタイムインターフェイスを提供する**

Kubelet は CRI 経由で sandbox 操作を要求し、コンテナランタイムが CNI プラグインを管理・呼び出します。プラグインがネットワーク操作を実装し、IPAM に委譲したり、プロバイダー固有のエージェントを使ったりする場合があります。veth ペアは一般的な実装ですが、すべての CNI に必須ではありません。

</details>

### 3. Overlay とネイティブルーティングの違いは何ですか？

- A. Overlay は常に高速である
- B. Overlay は別のネットワーク上でトラフィックをカプセル化し、ネイティブルーティングはその Overlay を使わず基盤の経路を使う
- C. ネイティブルーティングには必ず VXLAN が必要である
- D. AWS だけが Overlay を利用できる

<details>
<summary>解答を表示</summary>

**解答: B. Overlay は別のネットワーク上でトラフィックをカプセル化し、ネイティブルーティングはその Overlay を使わず基盤の経路を使う**

VXLAN／IPIP はカプセル化の例です。ネイティブルーティングには適切な経路設計が必要です。BGP を使うことはできますが、常に必要なわけではありません。性能を断定する前に、MTU、暗号化、ポリシー、トラフィック、ハードウェアを比較してください。

</details>

### 4. クラスター内部向けの仮想 IP を提供する既定の Service type はどれですか？

- A. NodePort
- B. LoadBalancer
- C. ClusterIP
- D. ExternalName

<details>
<summary>解答を表示</summary>

**解答: C. ClusterIP**

ClusterIP は既定値です。通常はクラスター内部に公開されますが、それ自体がセキュリティ境界になるわけでも、到達可能性を保証するわけでもありません。NodePort は構成されたノードアドレスとポートを使います。LoadBalancer は実装が必要で、内部向けにもできます。ExternalName は DNS エイリアスを提供します。Headless Service には仮想 IP がありません。

</details>

### 5. eBPF ベースのネットワークデータプレーンと Hubble を組み合わせて提供するプロジェクトはどれですか？

- A. Flannel
- B. 元の Weave Net プロジェクト
- C. Cilium
- D. AWS VPC CNI

<details>
<summary>解答を表示</summary>

**解答: C. Cilium**

Cilium は eBPF を使い、可観測性機能として Hubble を含みます。該当する L7 機能では Envoy を使います。Calico のデータプレーンの選択肢や AWS のポリシーエージェントなど、他のプロジェクトも eBPF を使います。技術名だけでは、一律の性能順位は判断できません。

</details>

### 6. 文書化された EKS VPC-CNI／Auto Mode のポリシー機能について、正確でない説明はどれですか？

- A. VPC CNI は VPC アドレスと EC2 ENI／prefix を使う
- B. ノードあたりの Pod 容量は、インスタンスの上限、割り当てモード、kubelet の上限によって異なる
- C. 対応する EKS 環境では、標準と Admin のネットワークポリシー機能を利用できる
- D. DNS ベースの ApplicationNetworkPolicy が、現在の HTTP メソッドや本文の検査を意味する

<details>
<summary>解答を表示</summary>

**解答: D. DNS ベースの ApplicationNetworkPolicy が、現在の HTTP メソッドや本文の検査を意味する**

AWS は Auto Mode 向けに DNS／FQDN の ApplicationNetworkPolicy を、Auto Mode と対応する EC2／VPC-CNI 環境向けに Admin ClusterNetworkPolicy を文書化しています。DNS ベースのネットワーク層制御と HTTP 検査は別の機能です。Linux EC2、Windows、Fargate ではサポート条件が異なります。標準的な EC2 add-on は Auto Mode の実装ではありません。

</details>

### 7. BGP のコントロールプレーンを選択できる組み合わせはどれですか？

- A. Flannel と元の Weave Net
- B. Calico と Cilium
- C. AWS VPC CNI と Flannel
- D. 元の Weave Net と AWS VPC CNI

<details>
<summary>解答を表示</summary>

**解答: B. Calico と Cilium**

Calico と Cilium は、適切なピアに経路を広告できます。BGP ピアリングだけでは、アプリケーションの Service 検出、ワークロード認証、暗号化は提供されません。経路の所有者と、選択した CNI の現行 BGP API およびトポロジー要件を確認してください。

</details>

### 8. 通常の Pod 間 Kubernetes NetworkPolicy による分離の対象外となるトラフィックはどれですか？

- A. 別々の Pod 間のトラフィック
- B. Pod から外部エンドポイントへの egress
- C. 1 つの Pod のネットワーク namespace を共有するコンテナ間の localhost 通信
- D. 外部から Pod に入るトラフィック

<details>
<summary>解答を表示</summary>

**解答: C. 1 つの Pod のネットワーク namespace を共有するコンテナ間の localhost 通信**

Pod のネットワーク namespace を共有するコンテナは、localhost 経由で通信できます。NetworkPolicy を適用するには対応する実装が必要で、仕様上の例外や実装依存の詳細もあります。すべてのホスト経由、変換後、トンネル経由の通信が同じように制御されるとは限りません。

</details>

### 9. 大規模クラスターを評価する際に有用なスケーラビリティの基準はどれですか？

- A. ダッシュボードがあるかどうかだけ
- B. コントローラー／API の負荷、状態伝播、ノードあたりのリソース、現実的な変更頻度での動作
- C. ロゴの見た目
- D. リリース頻度だけ

<details>
<summary>解答を表示</summary>

**解答: B. コントローラー／API の負荷、状態伝播、ノードあたりのリソース、現実的な変更頻度での動作**

ポリシーやエンドポイントの数、更新伝播、接続の入れ替わり、障害復旧、実際のデータプレーン負荷を試験してください。ノード数のしきい値や eBPF というラベルだけでは適合性を証明できません。選択したインストールモードに、製品コンポーネントとスケーリング機構が合っている必要があります。

</details>

### 10. Ingress と Service の正しい関係はどれですか？

- A. Ingress は L4 専用 API で、Service は L7 専用である
- B. Ingress は HTTP／HTTPS のルーティングを記述し、Service はネットワークエンドポイントと検出を提供する
- C. Service は常に外部向けである
- D. Ingress は UDP 専用である

<details>
<summary>解答を表示</summary>

**解答: B. Ingress は HTTP／HTTPS のルーティングを記述し、Service はネットワークエンドポイントと検出を提供する**

Ingress にはコントローラー／データプレーンが必要で、通常は Service をバックエンドとして参照します。データプレーンはエンドポイント Pod IP または NodePort に接続できるため、Service の仮想 IP が必ず追加のパケットホップになるわけではありません。Service のプロトコルとロードバランサーのサポートは、実際の実装で確認してください。

</details>
