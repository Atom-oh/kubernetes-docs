# 用語集クイズ

> **レビュー基準**: Cilium 1.20.3
> **最終確認日**: 2026年10月16日

このクイズでは、Cilium、eBPF、Kubernetes、ネットワーキングに関連する主要な用語と概念の理解を確認します。

## 選択式問題

1. eBPF の正式名称は何ですか？
   * A) Enhanced Berkeley Packet Filter
   * B) Extended Berkeley Packet Filter
   * C) Embedded BPF Filter
   * D) External Berkeley Protocol Filter

<details>

<summary>回答を表示</summary>

**回答: B) Extended Berkeley Packet Filter**

**解説:** eBPF は従来の BPF を拡張したもので、ネットワーキング、トレーシング、その他のカーネルフックに使われます。Verifier はプログラムの性質を検査しますが、カーネルや Verifier 自体の実装バグをなくすものではありません。

</details>

2. Cilium で network policy が適用される基本単位は何ですか？
   * A) Pod
   * B) Node
   * C) Endpoint
   * D) Service

<details>

<summary>回答を表示</summary>

**回答: C) Endpoint**

**解説:** Cilium Endpoint は通常、管理対象の Pod に対応します。Endpoint ID はそれを管理する Agent 内でのみ一意ですが、セキュリティ Identity は共有できます。対象ノードの Agent 内で `cilium-dbg endpoint list` を実行してください。

</details>

3. 対応ネットワークデバイスで native XDP が実行される場所はどこですか？
   * A) L7 protocol analysis
   * B) Packet processing at network driver level
   * C) TLS encryption
   * D) DNS resolution

<details>

<summary>回答を表示</summary>

**回答: B) Packet processing at network driver level**

**解説:** Native XDP は、対応ドライバーの受信経路で実行されます。PASS は通常のネットワークスタックへ処理を続け、DROP、TX、REDIRECT はそれぞれ別の動作をします。Generic モードや offload モードは動作が異なります。Cilium の Service 高速化は条件付きであり、一定のパケットレートや組み込みの DDoS 保護を保証するものではありません。

</details>

4. Cilium の network observability platform の名称は何ですか？
   * A) Prometheus
   * B) Grafana
   * C) Hubble
   * D) Jaeger

<details>

<summary>回答を表示</summary>

**回答: C) Hubble**

**解説:** Hubble は flow 記録、判定結果、対応するプロトコルのメトリクスを、CLI／UI や構成済みの連携先に公開します。Relay は永続ストレージではありません。外部アラートや保存期間には別途設定が必要で、イベントが失われる場合もあります。

</details>

5. VXLAN の正式名称と主な目的は何ですか？
   * A) Virtual Extended LAN - Virtual network creation
   * B) Virtual Extensible LAN - L2 overlay network
   * C) Very Extended LAN - Large-scale network expansion
   * D) Variable Extensible LAN - Dynamic network configuration

<details>

<summary>回答を表示</summary>

**回答: B) Virtual Extensible LAN - L2 overlay network**

**解説:** VXLAN は UDP を使って IP underlay 上に L2 overlay を運び、24-bit の VNI を使います。VNI には約1,600万の値がありますが、これは Cilium の容量保証ではありません。Cilium は overlay metadata に Identity 情報も載せます。

</details>

6. BPF Maps の主な役割は何ですか？
   * A) Network routing table management
   * B) Data sharing and storage between eBPF programs
   * C) DNS record caching
   * D) TLS certificate storage

<details>

<summary>回答を表示</summary>

**回答: B) Data sharing and storage between eBPF programs**

**解説:** BPF map はカーネル管理の状態やイベントを eBPF プログラムとユーザー空間で共有します。Hash map や Array map はキーを使いますが、Ring Buffer など一部の map 型は通常の lookup／update／delete 操作をサポートしません。

</details>

7. Cilium で Pod の security identity を表す数値識別子は何と呼ばれますか？
   * A) Pod ID
   * B) Security Context
   * C) Identity
   * D) Endpoint ID

<details>

<summary>回答を表示</summary>

**回答: C) Identity**

**解説:** セキュリティ上重要な label によって Identity が決まります。すべてのメタデータ label が Identity に使われるわけではありません。Identity は割り当て範囲内で複数 Endpoint に共有されます。数値の Endpoint ID は Agent 内でローカルに使われる別の識別子です。

</details>

8. IPAM の正式名称と Cilium における役割は何ですか？
   * A) IP Address Management - IP address allocation and management
   * B) Internet Protocol Access Manager - Internet access management
   * C) IP Assignment Module - IP assignment module
   * D) Internal Protocol Address Mapper - Internal protocol address mapping

<details>

<summary>回答を表示</summary>

**回答: A) IP Address Management - IP address allocation and management**

**解説:** IPAM は IP アドレスを割り当て、追跡します。Cilium は mode に応じて Cluster Pool、Multi-Pool、Kubernetes host-scope、ENI などの所有モデルをサポートします。GKE はプラットフォームであり、単独の `ipam.mode` 値を意味するものではありません。マネージドプラットフォームとの連携を確認してください。

</details>

9. WireGuard の主な特徴と Cilium での用途は何ですか？
   * A) Packet capture tool - Network analysis
   * B) Modern VPN protocol - Inter-node traffic encryption
   * C) Load balancing algorithm - Traffic distribution
   * D) DNS proxy - Name resolution

<details>

<summary>回答を表示</summary>

**回答: B) Modern VPN protocol - Inter-node traffic encryption**

**解説:** Cilium WireGuard は、対応するノード間トラフィックを保護します。同一ノード上の Pod 間通信はノードトンネルを通らず、外部／ノード向けトラフィックには別の条件があります。IPsec より常に高速とは限らないため、同等のワークロードと保護設定で比較してください。

</details>

10. CNI の正式名称と役割は何ですか？
    * A) Container Network Interface - Standard interface for container network plugins
    * B) Cloud Native Infrastructure - Cloud native infrastructure
    * C) Cluster Network Integration - Cluster network integration
    * D) Container Node Interconnect - Container node connection

<details>

<summary>回答を表示</summary>

**回答: A) Container Network Interface - Standard interface for container network plugins**

**解説:** CNI はコンテナランタイムとネットワークプラグインの間のインターフェースを定義します。現在の Kubernetes では kubelet は CRI を使い、コンテナランタイムが CNI 呼び出しを管理します。kubelet が直接 CNI を管理するフラグは Kubernetes 1.24 で削除されました。

</details>

## 短答式問題

11. Cilium で L7 proxy と service mesh 機能を提供する open-source component の名称は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** Envoy

**解説:** Envoy は構成された HTTP／gRPC proxy 機能を提供します。DNS policy は Cilium の DNS proxy を使い、Kafka L7 rule は削除されています。Proxy の配置やライフサイクルは設定に従い、任意の L7 rule ごとに自動で一つずつ Proxy が配置されるわけではありません。

</details>

12. 各 Node で実行され、eBPF program loading、network policy implementation、endpoint management を担う Cilium component の名称は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** Cilium Agent

**解説:** Agent は、Cilium が管理する対象ノード上の Endpoint、BPF プログラム、ポリシー／データパス状態を管理します。IPAM の責務は mode によって Agent、Operator、プラットフォームの間で分担されます。

</details>

13. IP addresses を使用した packet routing を担う OSI model layer の名称と番号は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** L3 (Network Layer)

**解説:** L3 (Network Layer) は OSI model の第 3 層で、IP addresses を使用した logical addressing と packet routing を担います。IP (Internet Protocol) と ICMP (Internet Control Message Protocol) はこの layer で動作します。Cilium L3 policies は、IP addresses と CIDR blocks に基づいて traffic をフィルタリングできます。L2 (Data Link Layer) は MAC addresses を使用し、L4 (Transport Layer) は port numbers を使用します。

</details>

14. Pod のセットに安定した network endpoints を提供する Kubernetes resource の名称は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** Service

**解説:** Service は論理的なバックエンドアクセスの抽象化を提供します。通常の ClusterIP Service には仮想 IP があり、headless Service にはありません。ExternalName は DNS alias を使います。selector のない Service は、手動管理または外部 Endpoint を表すことができます。

</details>

15. packet の source IP address を変更する NAT type の名称は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** SNAT (Source Network Address Translation)

**解説:** SNAT はパケットの送信元アドレスを変更します。Masquerading は送信経路／インターフェースに関連付けられたアドレスを選びます。除外設定と選択された gateway IP が影響します。すべての Pod の outbound パケットが必ず変換されるわけではありません。DNAT は宛先を変更します。

</details>

## ハンズオン問題

16. ClusterMesh、CRD、FQDN、mTLS をそれぞれの定義と対応付けてください。

<details>

<summary>回答を表示</summary>

**回答:**

- **ClusterMesh**: クラスター間のネットワークメタデータ／接続性。すべてのポリシーリソースを自動的に複製するものではありません。
- **CRD**: Kubernetes API にカスタムリソースの種類を追加する定義。
- **FQDN**: DNS ツリー上の絶対名。`toFQDNs` は学習した IP アドレスを許可します。
- **mTLS**: 相互ピア認証を伴う TLS。認証とアプリケーション認可は別です。

</details>

17. CRD で割り当てられた Identity を照会し、実際のセキュリティ label で絞り込んでください。Agent のローカルな表示範囲も区別してください。

<details>

<summary>回答を表示</summary>

**回答:**

```bash
set -euo pipefail
kubectl get ciliumidentities -o json > identities.json
jq '.items[]
| select(.["security-labels"]["k8s:app"] == "frontend")
| {id: .metadata.name, labels: .["security-labels"]}' identities.json
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
```

これは CRD allocation mode を前提とします。`CiliumIdentity` は cluster-scoped で、`security-labels` が正しい情報源です。これは `metadata.labels` とは異なります。予約済み／ノードローカルの Identity がすべて CRD に表現されるわけではありません。Agent の表示範囲も別です。対象ノードの Cilium Agent Pod は[ノード選択手順](../../../networking/cilium/07-advanced-topics.md)に従って指定してください。

</details>

18. 選択した Agent の Service、CT、NAT、Policy、Endpoint map を調べてください。

<details>

<summary>回答を表示</summary>

**回答:**

```bash
set -eu
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --backends
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf ct list global
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf policy get --all
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
```

最初に対象ノードを所有する Agent を選んでください。`--backends` と Policy map の `--all` は有効なフラグです。CT／Policy の全件出力は大きくなるため、影響を受けたノードで必要な場合に使います。`map list` が示すのは Agent が開いている map であり、カーネル上の map の完全な一覧でも、すべてのアプリケーション接続が有効である証拠でもありません。

</details>

19. DNS 通信も許可しながら、TCP 443 を `api.example.com` と一階層の `*.googleapis.com` で学習した IP に許可する Policy を記述し、制約を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: fqdn-egress-policy
  namespace: cilium-glossary-demo
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

これは Policy のみの演習です。namespace と label 付きクライアント、および実際の CoreDNS 経路は別途準備してください。DNS の UDP／TCP 通信と DNS proxy による観測を許可します。`*.googleapis.com` は一階層のサブドメインに一致し、apex や `a.b.googleapis.com` には一致しません。DNS の `*` はすべての問い合わせ名を許可します。`toFQDNs` は IP アドレスへの許可を作るもので、共有 IP 上の HTTPS Host 制約やリモートサーバー認証ではありません。重複する Allow Policy と TLS 検証も確認してください。

</details>

20. Operator と Agent の責務を比較し、Operator の状態を確認してください。

<details>

<summary>回答を表示</summary>

**回答:**

```bash
kubectl -n kube-system get deployment cilium-operator
kubectl -n kube-system get pods -l name=cilium-operator
kubectl -n kube-system logs -l name=cilium-operator -c cilium-operator --prefix --since=10m --tail=100
cilium status --verbose
kubectl get ciliumidentities
kubectl get ciliumendpoints --all-namespaces
```

| コンポーネント | 範囲と責務 |
| --- | --- |
| Agent | Cilium が管理するノードの Endpoint、BPF プログラム、Policy／データパス状態、mode に応じたローカル IPAM 作業。 |
| Operator | クラスター単位の CRD 登録、mode に応じた IPAM／LB IPAM、孤立リソース／Identity の収集、有効化された Ingress／Gateway の変換。 |

`name=cilium-operator` は現行 chart で有効です。`operator.replicas` は1または2以外にも設定できます。Agent はデフォルトで Identity を作成します。Operator による Identity 管理は別の Beta mode です。有効化した機能によっては ClusterMesh の EndpointSlice／MCS 同期も加わるため、責務を常に同じものとして扱わないでください。

</details>

***

[学習資料に戻る](../../../networking/cilium/glossary.md) | [Cilium クイズ一覧](../../README.md#cilium)
