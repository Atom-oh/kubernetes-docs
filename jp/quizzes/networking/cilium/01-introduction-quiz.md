# Cilium の概要と基本概念クイズ

> **基準バージョン**: Cilium 1.20.3 / CLI 0.20.1。**最終更新**: 2026年10月16日

## 選択問題

1. Cilium のプログラム可能なカーネルデータパスを実現する技術は何ですか？
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>
<summary>答えを表示</summary>

**答え: B) eBPF**

**解説:**
Cilium は、サポート対象のカーネルフックに検証済みの eBPF プログラムをロードします。これによりネットワーキングや可観測性の機能を実現できますが、あらゆる代替手段より必ず高性能になるとは限りません。選択したワークロードと設定で測定してください。

</details>

2. 必要な統合を行った場合、Cilium はどのレイヤーのポリシーをサポートできますか？
   - A) L3 のみ
   - B) L3～L4 のみ
   - C) L3／L4 と、サポート対象の L7 プロトコル
   - D) L2～L3 のみ

<details>
<summary>答えを表示</summary>

**答え: C) L3／L4 と、サポート対象の L7 プロトコル**

**解説:**
HTTP と DNS のポリシーはサポート対象のプロキシ経路を使います。暗号化された HTTP には適切な終端／統合が必要です。Kafka を認識する L7 ルールは 1.20 で削除されました。L4 ポリシーでは引き続き Kafka 接続を制御できます。

</details>

3. Cilium でネットワークフローを可視化するコンポーネントは何ですか？
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>
<summary>答えを表示</summary>

**答え: B) Hubble**

**解説:**
Hubble はネットワーク／プロキシのフローを観測し、サービス間の関係を表示できます。HTTP の可視性はプロキシ経路に依存します。完全なアプリケーショントレースが自動的に作られるわけではありません。Prometheus のメトリクスと分散トレーシングは、それぞれ異なる役割を持ちます。

</details>

4. サポート対象の構成で、Cilium が置き換えられる Kubernetes Service コンポーネントは何ですか？
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>
<summary>答えを表示</summary>

**答え: B) kube-proxy**

**解説:**
`kubeProxyReplacement` は、Cilium による Service 処理を要求します。API／ブートストラップへのアクセスや移行の前提条件も引き続き重要です。DSR、Maglev、XDP は個別に選択する設定であり、自動的な性能向上を保証するものではありません。

</details>

5. Cilium の透過的なネットワーク暗号化モードの組み合わせはどれですか？
   - A) IPsec と WireGuard
   - B) TLS と SSH
   - C) GRE と HTTP
   - D) DNS と VXLAN

<details>
<summary>答えを表示</summary>

**答え: A) IPsec と WireGuard**

**解説:**
この問題で問う既存の方式は IPsec と WireGuard です。同じ `encryption.type` キーでは、ベータ版の `ztunnel` も指定でき、独自の名前空間登録、CA／ブートストラップ、トラフィック、ポリシーの前提条件を持つワークロード mTLS を提供します。これらは同じキーで選ぶ別々のモードです。Cilium は TLS を一切使わない、とするのは誤りです。

</details>

6. Cilium のマルチクラスター接続機能は何と呼ばれますか？
   - A) Cluster Federation
   - B) ClusterMesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>
<summary>答えを表示</summary>

**答え: B) ClusterMesh**

**解説:**
ClusterMesh は、設定済みの ID、信頼関係、ネットワーク到達性を備えた互換クラスター同士を接続します。アンダーレイ全体を自動構築するわけでも、すべての Service を自動的にグローバル到達可能にするわけでもありません。

</details>

7. 任意でパケット／ロードバランシングを早期に高速処理するために、Cilium が利用できる技術は何ですか？
   - A) DPDK
   - B) XDP
   - C) RDMA
   - D) SR-IOV

<details>
<summary>答えを表示</summary>

**答え: B) XDP**

**解説:**
XDP は、サポート対象のフック／ドライバーで選択したトラフィックを早期に処理できます。すべての Cilium のパケット経路が XDP を使用するわけではありません。有効化しただけで、パケット毎秒の保証や完全な DDoS 防御が得られるわけでもありません。

</details>

8. 文書化されたベンダーのバックポート相当を除く場合、Cilium 1.20 の標準的な upstream Linux カーネル基準はどれですか？
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>
<summary>答えを表示</summary>

**答え: D) 5.10**

**解説:**
現行の要件は Linux 5.10 以降です。RHEL 8.10 のバックポート済み 4.18 など、明示された同等バージョンは例外です。個別の機能でさらに新しいカーネルが必要な場合があります。ワークステーションの OS だけでなく、ノード／VM のカーネルを確認してください。

</details>

9. Cilium の eBPF データプレーンを必要とせず、VXLAN／host-gw 接続を提供する選択肢はどれですか？
   - A) Cilium native routing
   - B) Calico BPF mode
   - C) Flannel VXLAN／host-gw
   - D) Cilium netkit mode

<details>
<summary>答えを表示</summary>

**答え: C) Flannel VXLAN／host-gw**

**解説:**
Flannel の接続バックエンドは別の実装です。任意のポリシーコントローラーや他のポリシー統合については、別途評価してください。製品全般に通用するリソース／性能の順位付けは避けてください。

</details>

10. CiliumNetworkPolicy の API バージョンは何ですか？
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

<details>
<summary>答えを表示</summary>

**答え: C) cilium.io/v2**

**解説:**
CiliumNetworkPolicy は、標準 Kubernetes NetworkPolicy とは別の CRD／API です。利用可能な機能は、Cilium のバージョンとデータプレーン／プロキシ設定にも依存します。

</details>

## 短答問題

11. ノードごとに実行され、エンドポイントと eBPF ポリシーを設定するコンポーネントは何ですか？

<details>
<summary>答えを表示</summary>

**答え: Cilium Agent**

**解説:**
Agent はノードローカルの処理を担当します。コンテナランタイム／CNI プラグイン、Operator、プロキシ、ホスト OS には、それぞれ別の責務があります。Agent がネットワーキングに関するすべての作業を所有するわけではありません。

</details>

12. クラスター単位の割り当て／コントローラー処理を調整するコンポーネントは何ですか？

<details>
<summary>答えを表示</summary>

**答え: Cilium Operator**

**解説:**
Operator は複数のレプリカで実行できます。レビュー済みチャートのデフォルトは 2 レプリカで、該当する処理にはリーダー選出を使います。責務は IPAM／ID モードによって異なります。必ず単一インスタンスになるわけでも、すべての ClusterMesh 接続を単独で所有するわけでもありません。

</details>

13. Cilium の接続性テスト用ワークロードを実行する CLI コマンドは何ですか？

<details>
<summary>答えを表示</summary>

**答え: `cilium connectivity test`**

**解説:**
このコマンドはワークロード／ポリシーを作成するため、承認済みのテスト環境と権限が必要です。読み取り専用の調査には、まず `cilium status`、エンドポイント診断、Hubble を利用してください。管理コマンドの `cilium monitor` は、現在の Agent 診断インターフェイスではありません。

</details>

14. エンドポイントのセキュリティ上重要なラベルに関連付けられる数値 ID は何ですか？

<details>
<summary>答えを表示</summary>

**答え: Security identity（Cilium identity）**

**解説:**
ID は割り当てスコープ内で、対象として選択されたラベルセットだけに基づきます。名前空間由来のラベルは異なる場合があります。同じアプリラベルだけでは同じ ID だと判断できません。数値 ID は割り当てられるもので、永続的でグローバルに意味のあるハッシュではありません。

</details>

15. コンテナネットワークプラグインのインターフェイスを定義する仕様は何ですか？

<details>
<summary>答えを表示</summary>

**答え: CNI（Container Network Interface）**

**解説:**
kubelet は CRI を通じてランタイムと通信し、ランタイムが CNI を呼び出します。CNI はネットワーク設定／結果をやり取りし、セットアップ／削除を処理します。kubelet の旧 CNI 設定フラグは Kubernetes 1.24 で削除されました。

</details>

## ハンズオン問題

16. インストール済み CLI と準備済みのラボ値／明示的なコンテキストを使い、新規の Cilium 1.20.3 インストールを示してください。

<details>
<summary>答えを表示</summary>

**答え:**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium version --client
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.3 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

**解説:**
ガイドにある事前検証済み環境、CNI の所有権、CIDR、values の前提条件に従ってください。既存リリースにはインストールせず、所有者のアップグレード手順を使います。`status` は正／負のトラフィックテストの代わりにはなりません。

</details>

17. `cilium-intro-demo` 内で、frontend Pod から backend Pod の TCP 8080 への Ingress を許可するラボ用ポリシーを書いてください。

<details>
<summary>答えを表示</summary>

**答え:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-backend
  namespace: cilium-intro-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-intro-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

**解説:**
名前空間とワークロードは既に存在している必要があります。送信元ピアに名前空間を明示すると、同じラベルを持つ他の名前空間にアクセスを許可せずに済みます。他の許可／拒否ポリシーやホストトラフィックも結果に影響します。このルールは HTTP フィルタリングでも egress 制限でもありません。

</details>

18. kube-proxy replacement と、Geneve dispatch を使う native-routing DSR を要求する values の一部を示してください。ほかに何を準備する必要がありますか？

<details>
<summary>答えを表示</summary>

**答え:**

```yaml
kubeProxyReplacement: true
k8sServiceHost: api.lab.example.internal
k8sServicePort: 443
routingMode: native
tunnelProtocol: geneve
ipv4NativeRoutingCIDR: 10.244.0.0/16
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
```

**解説:**
これは個別の native プロファイルであり、VXLAN ラボで DSR を有効にする指示ではありません。API ホスト／ポートと native-routing CIDR を、準備済みの実値に置き換えてください。API／ブートストラップの DNS アクセス、アンダーレイの Pod ルート、Geneve／MTU、戻り／送信元アドレスの経路を確保し、サポート対象の kube-proxy 移行手順に従ってください。静的な値だけでは、クラウドロードバランサーとの互換性も、あらゆるボトルネックの解消も保証されません。

</details>

19. クラスター状態、選択したバックエンドエンドポイントのノードローカルな状態、必要なポリシーリソースを表示してください。

<details>
<summary>答えを表示</summary>

**答え:**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
CILIUM_LAB_NS=cilium-intro-demo
BACKEND_POD=replace-with-actual-backend-pod
cilium status --context "$CILIUM_LAB_CONTEXT" --verbose
kubectl --context "$CILIUM_LAB_CONTEXT" get pod "$BACKEND_POD" -n "$CILIUM_LAB_NS" -o wide
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n kube-system -l k8s-app=cilium -o wide

# Choose the agent on the backend Pod's node.
CILIUM_AGENT_POD=replace-with-agent-pod-on-that-node
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint list
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint get "pod-name:$CILIUM_LAB_NS:$BACKEND_POD"
kubectl --context "$CILIUM_LAB_CONTEXT" get networkpolicy -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get ccnp -o yaml
```

**解説:**
エンドポイント ID と実現済み状態は、選択した Agent／ノードに属します。`cilium-dbg` がサポートする Pod 識別子を使ってください。`kubectl` が読み取るのは希望するポリシーリソースであり、適用の証明ではありません。`cilium-dbg policy get` は非推奨です。また、管理 CLI の `cilium endpoint`／`policy`／`monitor` コマンドは同等の機能ではありません。

</details>

20. 既存のラボリリースで Hubble を有効にし、インストール済みのクライアントツールからフローを観測してください。

<details>
<summary>答えを表示</summary>

**答え:**

```bash
# Terminal 1; the lab Cilium release and client tools must already exist.
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium hubble enable --context "$CILIUM_LAB_CONTEXT" --ui
cilium hubble port-forward --context "$CILIUM_LAB_CONTEXT" --port-forward 4245
```

```bash
# Terminal 2, with the port-forward still running.
BACKEND_POD=replace-with-actual-backend-pod
hubble observe --server 127.0.0.1:4245 --namespace cilium-intro-demo
hubble observe --server 127.0.0.1:4245 --pod "cilium-intro-demo/$BACKEND_POD"
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
```

**解説:**
リリースが GitOps 管理されている場合は、命令的な CLI 更新をせず、所有者の Helm values を変更してください。既に有効なら enable 手順を省きます。フォアグラウンドの port-forward を実行したままにし、Relay が TLS を使う場合はクライアント TLS も設定してください。HTTP イベントにはサポート対象の L7 プロキシ経路が必要です。`DROPPED` はすべてのアプリケーション障害を表すものではありません。同じ明示的なコンテキストを使って別のターミナルで `cilium hubble ui` を実行すると、UI にアクセスできます。

</details>

[学習教材に戻る](../../../networking/cilium/01-introduction.md) | [次のクイズ: eBPF の基本](02-ebpf-quiz.md)
