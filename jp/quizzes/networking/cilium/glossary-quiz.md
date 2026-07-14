# 用語集クイズ

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

**解説:** eBPF は Extended Berkeley Packet Filter の略で、もともとネットワークパケットキャプチャ用に開発された BPF (Berkeley Packet Filter) の拡張版です。eBPF は、Linux kernel 内でプログラムを安全に実行できる技術であり、ネットワークパケット処理、system call トレーシング、パフォーマンス監視など、さまざまな用途に使用されます。Cilium は eBPF を中核技術として活用し、高性能なネットワーキング、セキュリティ、オブザーバビリティ機能を提供します。

</details>

2. Cilium で network policy が適用される基本単位は何ですか？
   * A) Pod
   * B) Node
   * C) Endpoint
   * D) Service

<details>

<summary>回答を表示</summary>

**回答: C) Endpoint**

**解説:** Cilium では、Endpoint は network policy が適用されるネットワークエンドポイントを指し、通常は Kubernetes Pod に対応します。各 Endpoint には一意の ID があり、Cilium はこれらの Endpoint に基づいて network policy を適用し、トラフィックを制御します。Endpoint は Cilium Agent によって管理され、Pod の作成時に自動的に作成されます。現在の Node 上のすべての Endpoint は、`cilium endpoint list` コマンドで確認できます。

</details>

3. XDP (eXpress Data Path) の主な特徴は何ですか？
   * A) L7 protocol analysis
   * B) Packet processing at network driver level
   * C) TLS encryption
   * D) DNS resolution

<details>

<summary>回答を表示</summary>

**回答: B) Packet processing at network driver level**

**解説:** XDP (eXpress Data Path) は、network driver レベル（interrupt context）でパケットを処理する eBPF ベースの技術です。これにより kernel network stack をバイパスし、非常に高性能なパケット処理（1 秒あたり数百万パケット）が可能になります。XDP では、DROP、PASS、TX (transmit)、REDIRECT などのアクションでパケットを処理できます。Cilium は XDP を使用して、DDoS protection、高性能な load balancing、packet filtering を実装します。

</details>

4. Cilium の network observability platform の名称は何ですか？
   * A) Prometheus
   * B) Grafana
   * C) Hubble
   * D) Jaeger

<details>

<summary>回答を表示</summary>

**回答: C) Hubble**

**解説:** Hubble は、eBPF を使用して network flow をリアルタイムに監視・分析する Cilium の network observability platform です。Hubble の主な機能には、network flow monitoring、service dependency map の生成、network policy 違反の検出、performance metrics の収集、security event の追跡があります。Hubble は CLI と web ベースの UI の両方を提供し、Prometheus や Grafana と統合して metrics を可視化できます。

</details>

5. VXLAN の正式名称と主な目的は何ですか？
   * A) Virtual Extended LAN - Virtual network creation
   * B) Virtual Extensible LAN - L2 overlay network
   * C) Very Extended LAN - Large-scale network expansion
   * D) Variable Extensible LAN - Dynamic network configuration

<details>

<summary>回答を表示</summary>

**回答: B) Virtual Extensible LAN - L2 overlay network**

**解説:** VXLAN (Virtual Extensible LAN) は、Layer 3 (L3) network 上に Layer 2 (L2) network をオーバーレイする network virtualization 技術です。VXLAN はトンネリングに UDP encapsulation を使用し、24-bit VNI (VXLAN Network Identifier) により約 1,600 万の network segment をサポートします。Cilium では、VXLAN は Node 間の Pod 通信のための overlay networking mode として使用されます。代替手段には GENEVE や native routing mode があります。

</details>

6. BPF Maps の主な役割は何ですか？
   * A) Network routing table management
   * B) Data sharing and storage between eBPF programs
   * C) DNS record caching
   * D) TLS certificate storage

<details>

<summary>回答を表示</summary>

**回答: B) Data sharing and storage between eBPF programs**

**解説:** BPF Maps は、eBPF programs がデータを保存・取得するために使用する key-value store です。BPF Maps は、kernel space と user space の間でのデータ共有にも使用されます。主な種類には、Hash Map (key-value store)、Array Map (index-based array)、LRU Map (least recently used cache)、Ring Buffer (circular buffer) があります。Cilium は BPF Maps を使用して、service maps、backend maps、connection tracking tables などを保存します。

</details>

7. Cilium で Pod の security identity を表す数値識別子は何と呼ばれますか？
   * A) Pod ID
   * B) Security Context
   * C) Identity
   * D) Endpoint ID

<details>

<summary>回答を表示</summary>

**回答: C) Identity**

**解説:** Cilium Identity は、Pod の label set に基づいて生成される数値識別子です。同じ labels を持つすべての Pod は同じ Identity を共有します。Identity-based policies は、IP addresses ではなく Identity を使用して network policy を適用するため、Pod IP が変更されても policy の一貫性が維持されます。このアプローチは高い拡張性を備え、大規模な cluster でも効率的に動作します。Endpoint ID は特定の Pod instance を識別するもので、Identity とは異なります。

</details>

8. IPAM の正式名称と Cilium における役割は何ですか？
   * A) IP Address Management - IP address allocation and management
   * B) Internet Protocol Access Manager - Internet access management
   * C) IP Assignment Module - IP assignment module
   * D) Internal Protocol Address Mapper - Internal protocol address mapping

<details>

<summary>回答を表示</summary>

**回答: A) IP Address Management - IP address allocation and management**

**解説:** IPAM (IP Address Management) は、IP addresses の計画、割り当て、追跡、管理を担うシステムです。Cilium は複数の IPAM modes をサポートしています。Cluster Pool (cluster 全体の IP pool 管理)、Kubernetes (Kubernetes node CIDR を使用)、AWS ENI (AWS Elastic Network Interface を使用)、Azure (Azure networking integration)、GKE (Google Kubernetes Engine integration) です。IPAM mode の選択は、cluster environment と networking requirements によって決まります。

</details>

9. WireGuard の主な特徴と Cilium での用途は何ですか？
   * A) Packet capture tool - Network analysis
   * B) Modern VPN protocol - Inter-node traffic encryption
   * C) Load balancing algorithm - Traffic distribution
   * D) DNS proxy - Name resolution

<details>

<summary>回答を表示</summary>

**回答: B) Modern VPN protocol - Inter-node traffic encryption**

**解説:** WireGuard は、modern、fast、secure な VPN (Virtual Private Network) tunnel protocol です。IPsec よりシンプルかつ高速で、codebase が小さいため security auditing が容易です。Cilium では、WireGuard は Node 間の traffic encryption に使用されます。WireGuard を有効にすると、cluster 内の Pod 間のすべての traffic が透過的に暗号化されます。Cilium は IPsec または WireGuard のいずれかを使用して encryption を実装できます。

</details>

10. CNI の正式名称と役割は何ですか？
    * A) Container Network Interface - Standard interface for container network plugins
    * B) Cloud Native Infrastructure - Cloud native infrastructure
    * C) Cluster Network Integration - Cluster network integration
    * D) Container Node Interconnect - Container node connection

<details>

<summary>回答を表示</summary>

**回答: A) Container Network Interface - Standard interface for container network plugins**

**解説:** CNI (Container Network Interface) は、container runtimes と network plugins の間の標準インターフェースを定義する CNCF project です。Kubernetes では、kubelet は CNI interface を通じて network plugins (Cilium、Calico、Flannel など) と通信します。CNI は、container の追加・削除時の network configuration 用の標準 API を定義し、plugin architecture を通じてさまざまな networking solutions の統合を可能にします。Cilium は CNI implementations の 1 つです。

</details>

## 短答式問題

11. Cilium で L7 proxy と service mesh 機能を提供する open-source component の名称は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** Envoy

**解説:** Envoy は、L7 proxy および communication bus として使用される open-source edge and service proxy です。Cilium は L7 network policy の実装に Envoy を統合しています。CiliumNetworkPolicy で L7 rules (HTTP、gRPC、Kafka、DNS など) を定義すると、Cilium は Envoy proxy を自動的かつ透過的にデプロイします。Envoy は、高度な load balancing、traffic splitting、metrics collection 機能も提供します。

</details>

12. 各 Node で実行され、eBPF program loading、network policy implementation、endpoint management を担う Cilium component の名称は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** Cilium Agent

**解説:** Cilium Agent は、各 Kubernetes Node で DaemonSet として実行される Cilium の中核 component です。Agent の主な責務には、kernel への eBPF programs の loading と管理、network policies の実装と適用、service load balancing、IP address management (IPAM)、network endpoint management、metrics と logs の収集、Kubernetes API server との通信があります。各 Node の local networking operations は、その Node の Cilium Agent が処理します。

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

**解説:** Kubernetes Service は、Pod のセットに安定した network endpoints (ClusterIP、DNS name) を提供する abstraction です。Pod は動的に作成・削除され、その IP は変更される場合がありますが、Service は固定 IP と DNS names を提供するため、client は一貫してアクセスできます。Cilium は eBPF を通じて service load balancing を実装し、kube-proxy を置き換えることができます。Service types には ClusterIP、NodePort、LoadBalancer、ExternalName があります。

</details>

15. packet の source IP address を変更する NAT type の名称は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** SNAT (Source NAT) または Masquerading

**解説:** SNAT (Source Network Address Translation) は、packet の source IP address を別の IP address に変換する NAT type です。Masquerading は SNAT の特殊な形式で、source IP を outbound interface の IP に自動変換します。Cilium では、masquerading は cluster 内の Pod からの outbound traffic の source IP を Node IP に変換するために使用されます。対照的に、DNAT (Destination NAT) は destination IP を変更します。

</details>

## ハンズオン問題

16. 次の Cilium 関連用語を、その定義と対応付けてください: Cluster Mesh、CRD、FQDN、mTLS

<details>

<summary>回答を表示</summary>

**回答:**

* **Cluster Mesh**: Cilium の multi-cluster networking feature です。複数の Kubernetes clusters を接続し、cross-cluster service discovery、load balancing、network policy enforcement を可能にします。
* **CRD (Custom Resource Definition)**: custom resources を定義して Kubernetes API を拡張する方法です。Cilium は CRDs を使用して、CiliumNetworkPolicy、CiliumEndpoint などを定義します。
* **FQDN (Fully Qualified Domain Name)**: host の完全な domain name です（例: www.example.com）。Cilium FQDN policies は、IP ではなく domain name に基づいて external services へのアクセスを制御します。
* **mTLS (mutual TLS)**: client と server の両方が certificate を使用して相互認証する TLS の拡張です。双方向認証により、より強固な security を提供します。

**解説:** これらの用語は Cilium と Kubernetes networking で頻繁に使用されます。Cluster Mesh は hybrid/multi-cloud environments で有用であり、CRDs は Kubernetes extensibility の鍵であり、FQDN policies は dynamic IPs を持つ external services への access control に不可欠であり、mTLS は安全な service-to-service communication に重要です。

</details>

17. Cilium CLI を使用して、current cluster 内のすべての Identities とそれらの labels を照会するコマンドを記述してください。

<details>

<summary>回答を表示</summary>

**回答:**

```bash
# Query all Identities
cilium identity list

# Or query CiliumIdentity CRD using kubectl
kubectl get ciliumidentity -A

# Query detailed information for a specific Identity
cilium identity get <identity_id>

# Query detailed information in JSON format
kubectl get ciliumidentity <identity_id> -o json

# Filter Identities with specific labels
kubectl get ciliumidentity -o json | jq '.items[] | select(.metadata.labels."k8s:app" == "frontend")'

# Check Identity from Endpoints
cilium endpoint list
kubectl exec -n kube-system ds/cilium -- cilium endpoint list
```

**解説:** Cilium Identity は、Pod の label set に基づいて生成される数値識別子です。`cilium identity list` コマンドは、current cluster 内のすべての Identities とそれらの labels を表示します。CiliumIdentity は CRD として保存されるため、kubectl でも照会できます。Identity は network policies の基盤であり、同じ labels を持つすべての Pod は同じ Identity を共有します。

</details>

18. service load balancing maps と connection tracking tables を確認するために、BPF Map contents を照会するコマンドを記述してください。

<details>

<summary>回答を表示</summary>

**回答:**

```bash
# Query BPF maps from Cilium Agent pod

# Service map (Service -> Backend mapping)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list

# Backend map (backend pod information)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list --backends

# Connection Tracking table
kubectl exec -n kube-system ds/cilium -- cilium bpf ct list global

# NAT map (masquerading/SNAT information)
kubectl exec -n kube-system ds/cilium -- cilium bpf nat list

# Policy map (Identity-based policies)
kubectl exec -n kube-system ds/cilium -- cilium bpf policy get --all

# Endpoint map
kubectl exec -n kube-system ds/cilium -- cilium bpf endpoint list

# List all BPF maps
kubectl exec -n kube-system ds/cilium -- cilium bpf map list
```

**解説:** BPF Maps は Cilium の data plane で使用される中核 data structures です。`cilium bpf lb list` は service load balancing information を表示し、service IP/port と backend Pod IP/port の対応関係を確認できます。`cilium bpf ct list` は connection tracking table を表示し、現在 active な connection status を確認できます。これらのコマンドは network troubleshooting と performance analysis に役立ちます。

</details>

19. Pod が外部の `api.example.com` および `*.googleapis.com` domains とのみ通信できるようにする、FQDN-based network policy を使用した CiliumNetworkPolicy を記述してください。

<details>

<summary>回答を表示</summary>

**回答:**

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "fqdn-egress-policy"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  # Allow DNS queries (required for FQDN policy to work)
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
      rules:
        dns:
        - matchPattern: "*"
  # Allow HTTPS traffic to specific FQDNs
  - toFQDNs:
    - matchName: "api.example.com"
    - matchPattern: "*.googleapis.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

**解説:** FQDN (Fully Qualified Domain Name) based policies は、IP address ではなく domain name に基づいて external services へのアクセスを制御します。この policy を機能させるには、DNS queries を許可する必要があります（最初の egress rule）。`toFQDNs` では、`matchName` は完全一致の domain name を指定し、`matchPattern` は wildcards を使用した pattern matching を指定します。`*.googleapis.com` はすべての Google API subdomains を許可します。FQDN policies は、dynamic IPs を持つ external services への access control に特に有用です。

</details>

20. Cilium Operator の役割、Cilium Agent との違いを説明し、Operator の status を確認するコマンドを記述してください。

<details>

<summary>回答を表示</summary>

**回答:**

```bash
# Check Cilium Operator status
kubectl -n kube-system get deployment cilium-operator

# Check Operator pod status
kubectl -n kube-system get pods -l name=cilium-operator

# Check Operator logs
kubectl -n kube-system logs -l name=cilium-operator

# Check Operator in overall Cilium status
cilium status --verbose

# Check CiliumIdentity resources (managed by Operator)
kubectl get ciliumidentity -A

# Check CiliumEndpoint resources
kubectl get ciliumendpoint -A
```

**Cilium Operator と Cilium Agent の役割比較:**

| Component           | 実行場所                        | 主な責務                                                                                                                                              |
| ------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Cilium Agent**    | 各 Node (DaemonSet)               | <p>- eBPF program loading/management<br>- Network policy enforcement<br>- Local endpoint management<br>- Service load balancing<br>- Node-level IPAM</p>           |
| **Cilium Operator** | Cluster (Deployment、1～2 instances) | <p>- CiliumIdentity CRD management<br>- Cluster-level IPAM<br>- CiliumEndpoint synchronization<br>- Garbage collection<br>- Cluster Mesh connection management</p> |

**解説:** Cilium Agent は各 Node で実行され、その Node の networking operations を処理します。これに対し、Cilium Operator は cluster 全体で single instance（または HA 用に 2 つ）として実行され、cluster-level coordination tasks を処理します。Operator は cluster 全体で Identity の一貫性を維持し、未使用 resources をクリーンアップし、cluster-level IPAM を管理します。

</details>

***

[学習教材に戻る](../../../networking/cilium/glossary.md) | [Cilium クイズ一覧](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/networking/cilium/README.md)
