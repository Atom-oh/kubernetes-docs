# Calico アーキテクチャクイズ

> **関連ドキュメント**: [Calico アーキテクチャ](../../../networking/calico/02-architecture.md)
> **最終更新**: February 22, 2026

## クイズ

1. Calico のアーキテクチャにおける Felix の主な役割は何ですか？
   - A) BGP ルート配布
   - B) 各 node での Policy 適用とインターフェース管理
   - C) Datastore 接続の集約
   - D) 設定テンプレートの処理

<details>
<summary>回答を表示</summary>

**回答: B) 各 node での Policy 適用とインターフェース管理**

**解説:**
Felix は Calico cluster の各 node で実行されるコアエージェントです。主な責務には、インターフェース管理（Pod veth ペアの作成）、ルーティングテーブルのプログラミング、iptables/eBPF ルール管理、NetworkPolicy の適用が含まれます。Felix は、意図した NetworkPolicy を実装するために dataplane が正しく設定されるようにします。

</details>

2. BIRD は何の略で、Calico ではどのような役割を果たしますか？
   - A) Basic Internet Routing Daemon - DNS 解決を処理する
   - B) BIRD Internet Routing Daemon - BGP ルーティングを処理する
   - C) Binary Internet Relay Daemon - パケット転送を処理する
   - D) Bridge Internet Routing Device - VXLAN トンネリングを処理する

<details>
<summary>回答を表示</summary>

**回答: B) BIRD Internet Routing Daemon - BGP ルーティングを処理する**

**解説:**
BIRD（BIRD Internet Routing Daemon）は、BGP peer 接続の管理、node 間でのルートの交換と伝播、および任意で Route Reflector としての機能を担う、Calico の BGP エージェントです。BIRD により、Calico はカプセル化なしの直接ルーティングを実現するネイティブ BGP 機能を提供します。

</details>

3. Calico のアーキテクチャにおける confd の目的は何ですか？
   - A) container 設定の管理
   - B) BIRD 設定ファイルの動的な生成
   - C) NetworkPolicy の保存
   - D) トラフィックの Load Balancing

<details>
<summary>回答を表示</summary>

**回答: B) BIRD 設定ファイルの動的な生成**

**解説:**
confd は、テンプレートに基づいて BIRD 設定ファイルを動的に生成します。Calico datastore における BGP 設定、node 情報、peer 設定の変更を監視し、手動介入なしでこれらの変更を反映するよう BIRD の設定を自動的に更新します。

</details>

4. Calico cluster で Typha はいつ Deployment すべきですか？
   - A) cluster の規模にかかわらず常に
   - B) 50 を超える node を持つ cluster でのみ
   - C) eBPF mode を使用する場合のみ
   - D) multi-cluster Deployment の場合のみ

<details>
<summary>回答を表示</summary>

**回答: B) 50 を超える node を持つ cluster でのみ**

**解説:**
Typha は 50 以上の node を持つ cluster で推奨されます。Typha がない場合、各 Felix instance は datastore に直接接続するため、大規模 cluster では API server に過剰な負荷がかかる可能性があります。Typha は datastore 接続を集約し、Felix instance にキャッシュされたデータを提供することで、API server の負荷を大幅に削減します。

</details>

5. Calico はどのような datastore オプションをサポートしていますか？
   - A) MySQL と PostgreSQL
   - B) etcd と Kubernetes API
   - C) MongoDB と Redis
   - D) 専用 etcd のみ

<details>
<summary>回答を表示</summary>

**回答: B) etcd と Kubernetes API**

**解説:**
Calico は、専用 etcd cluster または Kubernetes API（CRD を使用）という 2 つの datastore オプションをサポートしています。Kubernetes API datastore は、既存の Kubernetes infrastructure を使用して運用を簡素化するため、ほとんどの Deployment で推奨されます。etcd datastore は、非 Kubernetes Deployment、または特定の etcd 機能が必要な場合に使用されます。

</details>

6. kube-controllers にはどの controllers が含まれていますか？
   - A) Policy Controller のみ
   - B) Policy、Namespace、ServiceAccount、WorkloadEndpoint、Node Controllers
   - C) Node と Policy Controllers のみ
   - D) WorkloadEndpoint Controller のみ

<details>
<summary>回答を表示</summary>

**回答: B) Policy、Namespace、ServiceAccount、WorkloadEndpoint、Node Controllers**

**解説:**
kube-controllers には、Kubernetes と Calico datastore の間を同期する複数の controller が含まれています。Policy Controller（NetworkPolicy の同期）、Namespace Controller（namespace profile の管理）、ServiceAccount Controller（service account の同期）、WorkloadEndpoint Controller（endpoint のクリーンアップ）、Node Controller（node 情報の同期）です。

</details>

7. 大規模 cluster で Typha replicas を算出する推奨式は何ですか？
   - A) 50 node あたり 1 replica
   - B) node 数を 200 で割り、最小 3
   - C) 常に 5 replicas
   - D) 100 node あたり 1 replica、最小 1

<details>
<summary>回答を表示</summary>

**回答: B) node 数を 200 で割り、最小 3**

**解説:**
Typha replicas の推奨式は、node 数 / 200 であり、高可用性のため最小 3 replicas とします。たとえば、500-node cluster では少なくとも 3 replicas（500/200 = 2.5 で、最小値の 3 に切り上げ）が必要であり、1000-node cluster では 5 replicas が必要です。

</details>

8. Calico のパケットフローで、node 上のルーティングテーブルをプログラミングする役割を担う component はどれですか？
   - A) BIRD
   - B) confd
   - C) Felix
   - D) Typha

<details>
<summary>回答を表示</summary>

**回答: C) Felix**

**解説:**
Felix は各 node 上のルーティングテーブルをプログラミングします。BIRD が node 間の BGP ルート交換を処理する一方で、Felix はルート情報を取得し、Linux kernel のルーティングテーブルにプログラミングします。Felix は Policy 適用のために iptables/eBPF ルールも管理します。

</details>

9. Typha は Felix instance との通信にどの port を使用しますか？
   - A) 443
   - B) 5473
   - C) 8080
   - D) 9090

<details>
<summary>回答を表示</summary>

**回答: B) 5473**

**解説:**
Typha は Felix instance からの接続に対して port 5473（calico-typha）で listen します。これは、cluster 内の各 node で実行される calico-node pods からの接続を受け付けるために、Typha Deployment で設定されるデフォルト port です。

</details>

10. eBPF mode を有効にする FelixConfiguration 設定はどれですか？
    - A) ebpfEnabled: true
    - B) bpfEnabled: true
    - C) dataplaneMode: ebpf
    - D) useEbpf: true

<details>
<summary>回答を表示</summary>

**回答: B) bpfEnabled: true**

**解説:**
Calico で eBPF mode を有効にするには、FelixConfiguration resource で `bpfEnabled: true` を設定します。これにより dataplane が iptables から eBPF に切り替わり、パフォーマンスが向上するとともに、Direct Server Return（DSR）や kube-proxy replacement などの機能が有効になります。

</details>

11. 大規模 cluster で Typha が Deployment されていない場合、Felix instance はどうなりますか？
    - A) Felix instance は起動に失敗する
    - B) 各 Felix が datastore に直接接続し、API server に過剰な負荷がかかる可能性がある
    - C) NetworkPolicy が適用されない
    - D) BGP peering が失敗する

<details>
<summary>回答を表示</summary>

**回答: B) 各 Felix が datastore に直接接続し、API server に過剰な負荷がかかる可能性がある**

**解説:**
Typha がない場合、すべての node 上のすべての Felix instance は、それぞれ datastore（Kubernetes API server）への独自の接続を維持します。数百の node を持つ大規模 cluster では、watch 接続とデータ転送により API server に過剰な負荷がかかる可能性があります。Typha は接続を集約し、データをキャッシュすることでこれを解決します。

</details>

12. デフォルトで Felix の health check port はどれですか？
    - A) 8080
    - B) 9091
    - C) 9099
    - D) 10250

<details>
<summary>回答を表示</summary>

**回答: C) 9099**

**解説:**
デフォルトでは、FelixConfiguration で `healthEnabled: true` が設定されている場合、Felix の health check endpoint は port 9099 で listen します。この port は、Felix が各 node で正しく実行されていることを検証するために Kubernetes liveness probe と readiness probe によって使用されます。

</details>

---

[学習教材に戻る](../../../networking/calico/02-architecture.md) | [前のクイズ: はじめに](./01-introduction-quiz.md) | [次のクイズ: ネットワークモード](./03-networking-modes-quiz.md)
