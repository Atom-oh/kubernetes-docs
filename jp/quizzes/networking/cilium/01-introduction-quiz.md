# Cilium の概要と基本概念クイズ

このクイズでは、Cilium の基本概念、eBPF テクノロジー、アーキテクチャ、主要コンポーネント、および CNI の比較についての理解を確認します。

## 選択問題

1. カーネル内でプログラム可能なデータパスを提供する Cilium の中核技術は何ですか？
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>

<summary>答えを表示</summary>

**答え: B) eBPF**

**解説:**
eBPF（extended Berkeley Packet Filter）は、Linux カーネル内でプログラムを安全に実行できる技術です。Cilium は eBPF を活用し、カーネルレベルでネットワーキング、セキュリティ、および可観測性の機能を実装します。これにより、iptables ベースのソリューションよりもはるかに高いパフォーマンスと柔軟性が得られ、カーネルを再コンパイルせずにネットワークポリシーを動的に適用できます。
</details>

2. Cilium のネットワークポリシーはどのレイヤーをサポートしますか？
   - A) L3（ネットワーク層）のみ
   - B) L3-L4（ネットワーク層およびトランスポート層）
   - C) L3-L7（ネットワーク層からアプリケーション層）
   - D) L2-L3（データリンク層およびネットワーク層）

<details>

<summary>答えを表示</summary>

**答え: C) L3-L7（ネットワーク層からアプリケーション層）**

**解説:**
Cilium は、L3（IP）、L4（TCP/UDP ポート）から L7（アプリケーション層）までのネットワークポリシーをサポートします。つまり、HTTP メソッド、パス、ヘッダー、gRPC メソッド、Kafka トピックなどのアプリケーションレベルのトラフィックをフィルタリングできます。この API を認識するネットワーキングは、マイクロサービスアーキテクチャで詳細なセキュリティポリシーを実装する際に非常に有用です。
</details>

3. Cilium でネットワークの可視化とモニタリングを提供するツールは何ですか？
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>

<summary>答えを表示</summary>

**答え: B) Hubble**

**解説:**
Hubble は、eBPF を使用してネットワークフローをリアルタイムで監視および分析する、Cilium のネットワーク可観測性レイヤーです。Hubble は、Service 依存関係マップの生成、ネットワークポリシー違反の検出、HTTP/gRPC/DNS リクエストのトレーシング、ネットワークレイテンシーの計測などの機能を提供します。Prometheus と Grafana はメトリクスの収集および可視化ツールであり、Jaeger は分散トレーシングツールです。
</details>

4. Cilium の分散ロードバランシング機能は、どの Kubernetes コンポーネントを置き換えられますか？
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>

<summary>答えを表示</summary>

**答え: B) kube-proxy**

**解説:**
Cilium は、kube-proxy を完全に置き換えられる eBPF ベースの Service ロードバランシングを提供します。kube-proxy は iptables または IPVS を使用して Service トラフィックをバックエンド Pod にルーティングしますが、Cilium は eBPF を使用して、より高いパフォーマンスとスケーラビリティを提供します。Cilium の kube-proxy 置換モードを有効にすると、DSR（Direct Server Return）、Maglev ハッシュ、ソケットレベルのロードバランシングなどの高度な機能も利用できます。
</details>

5. 次のうち、Cilium がサポートするノード間トラフィックの暗号化方式ではないものはどれですか？
   - A) IPsec
   - B) WireGuard
   - C) TLS
   - D) 両方ともサポートされている（A および B）

<details>

<summary>答えを表示</summary>

**答え: C) TLS**

**解説:**
Cilium は、ノード間トラフィックの暗号化に IPsec と WireGuard の 2 つの方式をサポートします。IPsec は広く使用されている従来の VPN プロトコルスイートであり、WireGuard はより新しく、シンプルで高速な VPN プロトコルです。TLS は、Cilium のネットワーク層暗号化とは異なる目的で使用されるアプリケーション層の暗号化プロトコルです。Cilium では、設定オプションを通じて IPsec または WireGuard のいずれかを選択し、透過的なネットワーク暗号化を実装できます。
</details>

6. Cilium のマルチクラスター・ネットワーキング機能は何と呼ばれますか？
   - A) Cluster Federation
   - B) Cluster Mesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>

<summary>答えを表示</summary>

**答え: B) Cluster Mesh**

**解説:**
Cluster Mesh は、複数の Kubernetes クラスターを接続して単一のネットワークとして動作させる、Cilium のマルチクラスター・ネットワーキング機能です。Cluster Mesh により、クラスター間の Service ディスカバリー、ロードバランシング、およびネットワークポリシーの適用が可能になります。この機能はハイブリッドクラウド、マルチクラウド、ディザスタリカバリーのシナリオで有用であり、各クラスターの Pod が他のクラスターの Service に直接アクセスできます。
</details>

7. Cilium がパケット処理のパフォーマンスを最適化するために使用する技術は何ですか？
   - A) DPDK
   - B) XDP (eXpress Data Path)
   - C) RDMA
   - D) SR-IOV

<details>

<summary>答えを表示</summary>

**答え: B) XDP (eXpress Data Path)**

**解説:**
XDP（eXpress Data Path）は、ネットワークドライバーレベルでパケット処理を可能にする eBPF ベースの技術です。XDP はカーネルのネットワークスタックをバイパスし、非常に高性能なパケット処理（毎秒数百万パケット）を実現します。Cilium は XDP を使用して、DDoS 防御、高性能なロードバランシング、およびパケットフィルタリングを実装します。DPDK、RDMA、SR-IOV も高性能なネットワーキング技術ですが、Cilium の中核技術は eBPF/XDP です。
</details>

8. Cilium 1.18 がサポートする最小 Linux カーネルバージョンは何ですか？
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>

<summary>答えを表示</summary>

**答え: C) 4.19**

**解説:**
Cilium 1.18 には Linux カーネル 4.19 以降が必要です。これは、Cilium が使用する eBPF 機能がこのバージョン以降で完全にサポートされているためです。より新しいカーネルバージョン（5.x 以降）を使用すると、追加の eBPF 機能と優れたパフォーマンスが得られます。たとえば、XDP ネイティブモード、BPF-to-BPF 関数呼び出し、BTF（BPF Type Format）などの高度な機能は、新しいカーネルでより適切にサポートされます。
</details>

9. 次の CNI プラグインのうち、eBPF ベースではないものはどれですか？
   - A) Cilium
   - B) Calico（eBPF モード）
   - C) Flannel
   - D) 両方とも eBPF ベースではない（C のみ）

<details>

<summary>答えを表示</summary>

**答え: C) Flannel**

**解説:**
Flannel は、eBPF を使用しない VXLAN または host-gw を使用するシンプルなオーバーレイネットワークソリューションです。対照的に、Cilium は最初から eBPF ベースとして設計されており、Calico も最近のバージョンでは eBPF データプレーンモードをサポートしています。Flannel は設定がシンプルでリソース使用量も少ない一方、L7 ネットワークポリシーや高度な可観測性機能は提供しません。
</details>

10. Cilium Network Policy の API バージョンは何ですか？
    - A) networking.k8s.io/v1
    - B) cilium.io/v1
    - C) cilium.io/v2
    - D) policy.cilium.io/v1

<details>

<summary>答えを表示</summary>

**答え: C) cilium.io/v2**

**解説:**
CiliumNetworkPolicy は `cilium.io/v2` API バージョンを使用します。これは、Cilium の高度な機能（L7 ポリシー、DNS ベースのポリシー、エンドポイントセレクターなど）をサポートするために、標準の Kubernetes NetworkPolicy（`networking.k8s.io/v1`）とは別に定義された CRD（Custom Resource Definition）です。Cilium は標準の Kubernetes NetworkPolicy もサポートしますが、CiliumNetworkPolicy を使用すると、より詳細な制御が可能になります。
</details>

## 短答問題

11. Cilium で各ノード上で実行され、eBPF プログラムをロードしてネットワークポリシーを実装する中核コンポーネントの名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: Cilium Agent**

**解説:**
Cilium Agent は、各 Kubernetes ノードで DaemonSet として実行される Cilium の中核コンポーネントです。Agent の主な責務には、カーネル内の eBPF プログラムのロードと管理、ネットワークポリシーの実装と適用、Service ロードバランシング、IP アドレス管理（IPAM）、ネットワークエンドポイント管理、メトリクスとログの収集、API サーバーとの通信が含まれます。Cilium Agent は、ローカルノード上のすべてのネットワーキング操作を処理します。
</details>

12. Cilium でクラスター全体で実行され、CRD の同期や IP 割り当ての調整などのタスクを実行するコンポーネントは何ですか？

<details>

<summary>答えを表示</summary>

**答え: Cilium Operator**

**解説:**
Cilium Operator は、クラスター全体で単一のインスタンスとして実行される Kubernetes Operator です。Agent が各ノード上のローカル操作を処理する一方、Operator はクラスター全体レベルの操作を処理します。主な機能には、CiliumIdentity および CiliumEndpoint CRD の管理、クラスター レベルの IPAM 管理、ノード間 CIDR 割り当ての調整、ガベージコレクション（未使用リソースのクリーンアップ）、および Cluster Mesh 接続管理が含まれます。
</details>

13. Cilium で接続性の問題を診断するために使用する CLI コマンドは何ですか？

<details>

<summary>答えを表示</summary>

**答え: cilium connectivity test**

**解説:**
`cilium connectivity test` コマンドは、Cilium クラスターのネットワーク接続性を包括的にテストします。このコマンドは、Pod 間通信、Service 接続性、外部接続性、ネットワークポリシーの適用など、さまざまなシナリオを自動的にテストします。テスト結果は成功または失敗として表示され、失敗したテストには詳細情報が提供されます。さらに、`cilium status` で Cilium のステータスを確認し、`cilium monitor` でリアルタイムトラフィックを監視できます。
</details>

14. Cilium において Pod のセキュリティアイデンティティを表す数値識別子は何ですか？

<details>

<summary>答えを表示</summary>

**答え: Identity（または Security Identity、Cilium Identity）**

**解説:**
Cilium Identity は、Pod のラベルセットに基づいて生成される数値識別子です。同じラベルを持つすべての Pod は同じ Identity を共有します。このアプローチでは IP アドレスの代わりに Identity を使用してネットワークポリシーを適用できるため、Pod の IP が変更されてもポリシーの一貫性が維持されます。Identity ベースのポリシーは高いスケーラビリティを備え、大規模なクラスターでも効率的に動作します。
</details>

15. コンテナランタイムとネットワークプラグインの間の標準インターフェイスを定義する CNCF プロジェクトの略称は何ですか？

<details>

<summary>答えを表示</summary>

**答え: CNI (Container Network Interface)**

**解説:**
CNI（Container Network Interface）は、コンテナランタイムとネットワークプラグインの間の標準インターフェイスを定義する CNCF プロジェクトです。Kubernetes では、kubelet が CNI インターフェイスを通じてネットワークプラグイン（Cilium、Calico、Flannel など）と通信します。CNI はコンテナの追加および削除時におけるネットワーク設定の標準 API を定義しており、さまざまなネットワーキングソリューションをプラグインアーキテクチャを通じて統合できます。
</details>

## ハンズオン問題

16. Cilium CLI を使用して、Kubernetes クラスターに Cilium 1.18.0 をインストールするコマンドを記述してください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install --version 1.18.0

# Check installation status
cilium status

# Connectivity test
cilium connectivity test
```

**解説:**
上記のコマンドは、まず Cilium CLI バイナリをダウンロードし、`/usr/local/bin` にインストールします。続いて、`cilium install` コマンドで指定したバージョンの Cilium を Kubernetes クラスターにインストールします。インストール後、`cilium status` を使用してすべてのコンポーネントが適切に実行されていることを確認し、`cilium connectivity test` でネットワーク接続性を検証します。Helm を使用したインストールも可能であり、より詳細な設定オプションを利用できます。
</details>

17. frontend Pod から backend Pod のポート 8080 への TCP トラフィックのみを許可する CiliumNetworkPolicy を記述してください。

<details>

<summary>答えを表示</summary>

**答え:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-backend"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

**解説:**
この CiliumNetworkPolicy は、`app: frontend` ラベルを持つ Pod から、`app: backend` ラベルを持つ Pod への TCP ポート 8080 の Ingress トラフィックのみを許可します。`endpointSelector` はポリシーが適用される対象 Pod を選択し、`ingress` セクションは許可する受信トラフィックを定義します。`fromEndpoints` は送信元 Pod を指定し、`toPorts` は許可するポートとプロトコルを指定します。このポリシーを適用すると、他の Pod から backend へのトラフィックはブロックされます。
</details>

18. kube-proxy 置換モードを有効にして Cilium をインストールするコマンドと、DSR（Direct Server Return）モードを有効にする設定を記述してください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
# Install Cilium with kube-proxy replacement and DSR mode
cilium install --version 1.18.0 \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr

# Or installation using Helm
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr \
  --set k8sServiceHost=<API_SERVER_IP> \
  --set k8sServicePort=<API_SERVER_PORT>

# Verify installation
cilium status --verbose
```

**解説:**
`kubeProxyReplacement=true` オプションは、すべての kube-proxy 機能を Cilium に置き換えるよう設定します。このモードでは、既存の kube-proxy を削除または無効化する必要があります。`loadBalancer.mode=dsr` は Direct Server Return モードを有効にするため、レスポンストラフィックはロードバランサーを経由せずにクライアントへ直接送信されます。DSR モードはロードバランサーのボトルネックを排除し、帯域幅を節約するため、特に大きなレスポンスを処理する場合に効果的です。
</details>

19. Cilium のステータスを確認し、特定の Pod のエンドポイント情報を照会し、適用されているネットワークポリシーを表示するコマンドを記述してください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
# Check overall Cilium status
cilium status

# Check detailed status (all components)
cilium status --verbose

# List all endpoints
cilium endpoint list

# Get detailed information for a specific endpoint (using endpoint ID)
cilium endpoint get <endpoint_id>

# Query endpoint by pod name
kubectl exec -n kube-system <cilium-agent-pod> -- cilium endpoint list | grep <pod-name>

# Query applied network policies
cilium policy get

# Query policies applied to a specific endpoint
cilium endpoint get <endpoint_id> -o json | jq '.status.policy'

# Real-time traffic monitoring
cilium monitor
```

**解説:**
`cilium status` は、Cilium Agent、Operator、Hubble など、すべてのコンポーネントのステータスを表示します。`cilium endpoint list` は現在のノード上のすべてのエンドポイント（Pod）を一覧表示し、各エンドポイントの ID、ステータス、ラベル、Identity を確認できます。`cilium policy get` はクラスターに適用されているすべてのネットワークポリシーを照会します。`cilium monitor` はネットワークトラフィックをリアルタイムで監視し、パケットフロー、ポリシーの適用、ドロップされたパケットを確認します。
</details>

20. Hubble を有効にし、Hubble CLI を使用してネットワークフローを観察するコマンドを記述してください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
# Install Cilium with Hubble enabled
cilium install --version 1.18.0 \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true

# Enable Hubble on existing Cilium
cilium hubble enable

# Install Hubble CLI
export HUBBLE_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/hubble/master/stable.txt)
curl -L --remote-name-all https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Hubble port forwarding
cilium hubble port-forward &

# Observe network flows
hubble observe

# Observe flows in a specific namespace
hubble observe --namespace default

# Observe flows for a specific pod
hubble observe --pod default/frontend

# Filter HTTP traffic only
hubble observe --protocol http

# Observe only dropped packets
hubble observe --verdict DROPPED

# Access Hubble UI (separate terminal)
cilium hubble ui
```

**解説:**
Hubble は、eBPF を使用してネットワークフローをリアルタイムで監視する Cilium の可観測性レイヤーです。`hubble.enabled=true` は Hubble を有効にし、`hubble.relay.enabled=true` はクラスター全体からフローを収集する Hubble Relay を有効にします。`hubble.ui.enabled=true` は Web ベースの UI を有効にします。`hubble observe` コマンドは、特定の namespace、Pod、プロトコル、判定結果などでトラフィックをフィルタリングするためのさまざまなオプションを提供します。
</details>

---

[学習教材に戻る](../../../networking/cilium/01-introduction.md) | [次のクイズ: eBPF の基本](./02-ebpf-quiz.md)
