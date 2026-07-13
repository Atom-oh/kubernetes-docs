# Cluster Architecture Quiz

このクイズでは、Kubernetes cluster architecture、主要コンポーネント、通信経路、高可用性構成についての理解を確認します。

## Multiple Choice Questions

1. 次のうち、Kubernetes control plane のコアコンポーネントではないものはどれですか？
   - A) kube-apiserver
   - B) etcd
   - C) kube-proxy
   - D) kube-scheduler
   
<details>

<summary>答えを表示</summary>

**解答: C) kube-proxy**

**解説:**
kube-proxy は node component であり、control plane component ではありません。コアとなる control plane components は kube-apiserver、etcd、kube-scheduler、kube-controller-manager、cloud-controller-manager です。kube-proxy は各 node で実行され、network rules を維持し、connection forwarding を実行します。
</details>

2. Kubernetes で、すべての cluster data を保存する「source of truth」として機能するコンポーネントはどれですか？
   - A) kube-apiserver
   - B) etcd
   - C) kube-controller-manager
   - D) kubelet
   
<details>

<summary>答えを表示</summary>

**解答: B) etcd**

**解説:**
etcd は、すべての cluster data を保存し、Kubernetes の「source of truth」として機能する、一貫性があり高可用な key-value store です。すべての cluster state、configuration、metadata は etcd に保存され、他のすべての control plane components は kube-apiserver を通じて etcd から情報を読み書きします。
</details>

3. 次のうち、Kubernetes node component ではないものはどれですか？
   - A) kubelet
   - B) kube-proxy
   - C) Container runtime
   - D) kube-controller-manager
   
<details>

<summary>答えを表示</summary>

**解答: D) kube-controller-manager**

**解説:**
kube-controller-manager は control plane component であり、node component ではありません。Node components は kubelet、kube-proxy、container runtime（containerd、CRI-O など）です。kube-controller-manager は control plane 上で実行され、node controller や replication controller など、さまざまな controller processes を実行します。
</details>

4. Kubernetes のどの control plane component が、新しく作成された pods を実行する nodes を選択しますか？
   - A) kube-apiserver
   - B) kube-scheduler
   - C) kubelet
   - D) kube-controller-manager
   
<details>

<summary>答えを表示</summary>

**解答: B) kube-scheduler**

**解説:**
kube-scheduler は、新しく作成された pods を実行する nodes を選択する control plane component です。scheduling process は、filtering（pod を実行できる nodes の特定）と scoring（適切な nodes へのスコア付け）で構成され、最終的に pod を最適な node に割り当てます。kube-scheduler は resource requirements、hardware/software/policy constraints、affinity/anti-affinity specifications、data locality、workload interference を考慮します。
</details>

5. Cloud provider APIs と連携する control plane component はどれですか？
   - A) kube-apiserver
   - B) etcd
   - C) cloud-controller-manager
   - D) kubelet
   
<details>

<summary>答えを表示</summary>

**解答: C) cloud-controller-manager**

**解説:**
cloud-controller-manager は、cloud-specific control logic を含み、cloud provider APIs と連携する control plane component です。これにより、Kubernetes core と cloud provider APIs を分離できます。cloud-controller-manager は、node controller、route controller、service controller、volume controller などの cloud-specific controllers を実行します。
</details>

6. 各 node で実行され、pods 内の containers の実行を管理する agent は何ですか？
   - A) kube-proxy
   - B) kubelet
   - C) containerd
   - D) kube-scheduler
   
<details>

<summary>答えを表示</summary>

**解答: B) kubelet**

**解説:**
kubelet は、各 node で実行され、pods 内の containers の実行を管理する agent です。kubelet はさまざまな仕組みを通じて PodSpecs を受け取り、その仕様に従って containers が健全に実行されるようにします。主な機能には、PodSpecs に従った containers の実行、container status の監視と報告、container lifecycle の管理、volume mounts の管理、node status の報告、container health checks の実行が含まれます。
</details>

7. Kubernetes のどの node component が service IPs の network rules を維持し、connection forwarding を実行しますか？
   - A) kubelet
   - B) kube-proxy
   - C) CNI plugin
   - D) containerd
   
<details>

<summary>答えを表示</summary>

**解答: B) kube-proxy**

**解説:**
kube-proxy は、各 node で実行される network proxy であり、Kubernetes service concept の実装を担当します。node 上の network rules を維持し、connection forwarding を実行します。主な機能には、service IPs と ports の network rules の維持、connection forwarding、load balancing の実装、service discovery のサポートが含まれます。kube-proxy は userspace mode、iptables mode、IPVS mode など、複数の operating modes をサポートします。
</details>

8. Kubernetes で containers を実行するための標準 interface は何ですか？
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) CPI (Container Platform Interface)
   
<details>

<summary>答えを表示</summary>

**解答: A) CRI (Container Runtime Interface)**

**解説:**
CRI (Container Runtime Interface) は、Kubernetes で containers を実行するための標準 interface です。CRI を通じて、Kubernetes は containerd や CRI-O など、さまざまな container runtimes をサポートできます。CRI は kubelet と container runtimes 間の通信のための APIs を定義し、containers の作成、開始、停止、削除などの operations を可能にします。CNI (Container Network Interface) は networking のための interface であり、CSI (Container Storage Interface) は storage のための interface です。
</details>

9. Kubernetes clusters で pod networking を実装するために使用される interface は何ですか？
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) API (Application Programming Interface)
   
<details>

<summary>答えを表示</summary>

**解答: B) CNI (Container Network Interface)**

**解説:**
CNI (Container Network Interface) は、Kubernetes で pod networking を実装するための標準 interface です。CNI plugins は network interfaces を pods に接続し、IP addresses を割り当てる役割を担います。Calico、Cilium、Flannel、Weave Net など、さまざまな CNI plugins が存在し、それぞれ異なる機能と performance characteristics を持ちます。CNI を通じて、Kubernetes はさまざまな networking solutions をサポートできます。
</details>

10. Kubernetes clusters で storage systems との標準 interface を提供するものは何ですか？
    - A) CRI (Container Runtime Interface)
    - B) CNI (Container Network Interface)
    - C) CSI (Container Storage Interface)
    - D) CPI (Cloud Provider Interface)
    
<details>

<summary>答えを表示</summary>

**解答: C) CSI (Container Storage Interface)**

**解説:**
CSI (Container Storage Interface) は、Kubernetes と storage systems の間に標準 interface を提供します。CSI を通じて、storage providers は Kubernetes code を変更することなく独自の storage drivers を開発できます。CSI は volume creation、deletion、mounting、unmounting などの operations のために標準化された APIs を定義します。AWS EBS CSI driver、Azure Disk CSI driver、GCP PD CSI driver など、さまざまな CSI drivers が存在します。
</details>

## Short Answer Questions

11. Kubernetes control plane で複数の controller processes を実行するコンポーネントの名前は何ですか？

<details>

<summary>答えを表示</summary>

**解答: kube-controller-manager**

**解説:**
kube-controller-manager は、複数の controller processes を実行する control plane component です。各 controller は cluster の特定の側面を管理します。主な controllers には、node controller、replication controller、endpoint controller、service account & token controller、job controller、cronjob controller、daemonset controller、statefulset controller、PV controller、namespace controller、garbage collector が含まれます。
</details>

12. Kubernetes は etcd data の一貫性を保証するためにどの consensus algorithm を使用しますか？

<details>

<summary>答えを表示</summary>

**解答: Raft**

**解説:**
etcd は、distributed systems における data の強い一貫性を保証するために Raft consensus algorithm を使用します。Raft は leader election、log replication、safety を通じて distributed systems で consensus を達成します。etcd clusters は通常 3 nodes または 5 nodes で構成され、nodes の過半数（quorum）が正常に機能している限り、cluster は動作を継続できます。
</details>

13. Kubernetes における kube-proxy のデフォルト operating mode は何ですか？

<details>

<summary>答えを表示</summary>

**解答: iptables**

**解説:**
kube-proxy のデフォルト operating mode は iptables mode です。この mode では、kube-proxy は Linux iptables を使用して NAT を実装し、service IPs への traffic を pods に route します。他の operating modes には userspace mode（legacy）と IPVS mode（high performance）があります。IPVS mode は大規模 clusters でより優れた performance を提供しますが、Linux kernel の IPVS module が必要です。
</details>

14. Kubernetes cluster で API server と通信するための configuration file の名前は何ですか？

<details>

<summary>答えを表示</summary>

**解答: kubeconfig**

**解説:**
kubeconfig は、Kubernetes API server と通信するための configuration file です。この file には cluster information、authentication information（certificates、tokens など）、contexts（clusters と users の組み合わせ）が含まれます。kubectl command はデフォルトで $HOME/.kube/config file を使用しますが、--kubeconfig flag または KUBECONFIG environment variable を通じて別の file を指定できます。
</details>

15. Kubernetes で high availability cluster を構成する場合、一般的に最小として推奨される control plane nodes の数はいくつですか？

<details>

<summary>答えを表示</summary>

**解答: 3**

**解説:**
Kubernetes の high availability cluster における control plane nodes の一般的な推奨最小数は 3 です。これは、etcd clusters が過半数（quorum）ベースで動作するためです。3 nodes では、1 node が失敗しても（2 が過半数）cluster は動作を継続できます。5 nodes では、2 nodes が失敗しても（3 が過半数）cluster は動作を継続できます。一般的には奇数個の nodes を使用することが推奨されます。
</details>

## Hands-on Questions

16. etcd database の backup を作成する command を書いてください。backup file は `/backup/etcd-snapshot-$(date +%Y%m%d).db` に保存し、etcd endpoint は `https://127.0.0.1:2379`、certificate files は `/etc/kubernetes/pki/etcd/` directory にあるものとします。

<details>

<summary>答えを表示</summary>

**解答:**
```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d).db \
--endpoints=https://127.0.0.1:2379 \
--cacert=/etc/kubernetes/pki/etcd/ca.crt \
--cert=/etc/kubernetes/pki/etcd/server.crt \
--key=/etc/kubernetes/pki/etcd/server.key
```

**解説:**
この command は ETCDCTL_API environment variable を 3 に設定して etcdctl v3 API を使用し、snapshot save command で etcd database の snapshot を作成します。--endpoints flag は etcd server endpoint を指定し、--cacert、--cert、--key flags は TLS authentication に必要な certificate files を指定します。backup file は現在の日付を含む名前で /backup directory に保存されます。
</details>

17. 次の requirements を満たす kube-scheduler configuration file（YAML）を書いてください:
    - Scheduler name: custom-scheduler
    - Leader election enabled
    - Scoring plugin: Set NodeResourcesBalancedAllocation weight to 2
    - Filtering plugin: Disable NodeUnschedulable

<details>

<summary>答えを表示</summary>

**解答:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true

profiles:
  - schedulerName: custom-scheduler
    plugins:
      score:
        enabled:
          - name: NodeResourcesBalancedAllocation
        disabled: []
      filter:
        disabled:
          - name: NodeUnschedulable
```

**解説:**
この YAML file は KubeSchedulerConfiguration object を定義します。leaderElection.leaderElect: true は leader election を有効化し、profiles section は custom-scheduler という名前の scheduler profile を定義します。plugins section では、score plugins で NodeResourcesBalancedAllocation の weight を 2 に設定し、filter plugins で NodeUnschedulable を無効化しています。
</details>

18. high availability etcd cluster を構成するための etcd startup command を、次の requirements を満たすように書いてください:
    - Node name: etcd-1
    - Cluster name: etcd-cluster
    - Client URL: https://192.168.1.10:2379
    - Peer URL: https://192.168.1.10:2380
    - Initial cluster: etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380
    - Data directory: /var/lib/etcd
    - Certificate files are in the /etc/kubernetes/pki/etcd/ directory

<details>

<summary>答えを表示</summary>

**解答:**
```bash
etcd \
--name=etcd-1 \
--initial-advertise-peer-urls=https://192.168.1.10:2380 \
--listen-peer-urls=https://192.168.1.10:2380 \
--listen-client-urls=https://192.168.1.10:2379,https://127.0.0.1:2379 \
--advertise-client-urls=https://192.168.1.10:2379 \
--initial-cluster-token=etcd-cluster \
--initial-cluster=etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380 \
--initial-cluster-state=new \
--data-dir=/var/lib/etcd \
--cert-file=/etc/kubernetes/pki/etcd/server.crt \
--key-file=/etc/kubernetes/pki/etcd/server.key \
--trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt \
--peer-cert-file=/etc/kubernetes/pki/etcd/peer.crt \
--peer-key-file=/etc/kubernetes/pki/etcd/peer.key \
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
```

**解説:**
この command は etcd-1 という名前の etcd node を起動します。--initial-advertise-peer-urls と --listen-peer-urls は peer communication 用の URLs を指定し、--listen-client-urls と --advertise-client-urls は client communication 用の URLs を指定します。--initial-cluster-token は cluster の一意の identifier を指定し、--initial-cluster は cluster 内のすべての nodes を列挙します。--initial-cluster-state=new は新しい cluster が作成されることを示します。--data-dir は etcd data が保存される directory を指定します。最後に、certificate-related flags は TLS communication のための certificate files を指定します。
</details>

## Advanced Questions

19. Kubernetes cluster の high availability architecture を設計し、control plane components と etcd の deployment methods、load balancer configuration、failure scenarios への response measures を説明してください。

<details>

<summary>答えを表示</summary>

**解答:**

**High Availability Kubernetes Cluster Architecture Design**

1. **Control Plane Component Deployment**:
  - 少なくとも 3 つの control plane nodes を複数の availability zones に分散する
  - 各 node に kube-apiserver、kube-scheduler、kube-controller-manager を deploy する
  - kube-scheduler と kube-controller-manager を leader election mode で実行する（一度に 1 つの instance のみ active）
  - kube-apiserver は horizontal scalable（すべての instances が同時に active）

2. **etcd Deployment Methods**:
  - Stacked topology: control plane nodes と一緒に etcd を deploy する
  - External topology: separate nodes に etcd を deploy する（より高い isolation と scalability）
  - 少なくとも 3 つの etcd nodes を複数の availability zones に分散する（5 つを推奨）
  - etcd cluster は data consistency を保証するために Raft consensus algorithm を使用する

3. **Load Balancer Configuration**:
  - kube-apiserver の前段に load balancer を配置する
  - load balancer は L4（TCP）または L7（HTTP/HTTPS）level で動作できる
  - health checks によって unhealthy な kube-apiserver instances を検出し、traffic から除外する
  - cloud environments では、cloud provider の managed load balancers（AWS ELB、GCP Cloud Load Balancer など）を使用する
  - on-premises environments では、HAProxy、NGINX、keepalived などを使用する

4. **Failure Scenarios and Response Measures**:
  - **Single control plane node failure**:
  - kube-apiserver: load balancer が traffic を healthy nodes に route する
  - kube-scheduler/kube-controller-manager: leader election によって別 node 上の instance が active になる
  - etcd: 過半数が healthy であれば（3 のうち 2、5 のうち 3）cluster は動作を継続する

  - **Availability zone failure**:
  - nodes を複数の availability zones に分散して、single zone failures に対応する
  - worker nodes も複数の availability zones に分散する

  - **Network partition**:
  - etcd は network partitions 時の「split brain」を防ぐため、過半数ベースで動作する
  - minority partition にある etcd nodes は read-only mode に切り替わる

  - **etcd data corruption/loss**:
  - 定期的に etcd backups を実行する
  - backups からの recovery procedures を文書化し、test する

5. **Additional Considerations**:
  - **Certificate management**: certificate expiration を監視し、自動 renewal を行う
  - **Audit logging**: 重要な operations の audit logs を有効化し、外部に保存する
  - **Monitoring and alerting**: control plane component status の monitoring and alerting を設定する
  - **Automated recovery**: automated recovery mechanisms（例: systemd service auto-restart）を実装する

この high availability architecture により、単一 node、単一 availability zone、または一部の components が失敗しても、Kubernetes cluster は動作を継続できます。
</details>

20. Kubernetes cluster の networking architecture を説明し、pod-to-pod communication、service networking、external communication がどのように機能するかを述べ、CNI plugins の役割を説明してください。また、network policies を使用して pod-to-pod communication を制限する方法も説明してください。

<details>

<summary>答えを表示</summary>

**解答:**

**Kubernetes Networking Architecture**

1. **Kubernetes Networking Model**:
  - すべての pods は一意の IP addresses を持つ
  - Pods は NAT なしで通信できる
  - Nodes と pods は NAT なしで通信できる
  - pod 内の containers は localhost を通じて通信する

2. **Pod-to-Pod Communication**:
  - **Between pods on the same node**: node の local bridge network を通じて通信する
  - **Between pods on different nodes**: overlay network または routing tables を通じて通信する
  - CNI plugins が pod IP address assignment と routing を処理する

3. **Service Networking**:
  - **ClusterIP**: cluster 内からのみ access 可能な virtual IP
  - **kube-proxy**: service IPs への traffic を pods に route する
  - iptables mode: Linux iptables rules を使用して NAT を実装する
  - IPVS mode: Linux kernel の IP Virtual Server を使用して high-performance load balancing を提供する
  - **CoreDNS**: service names を ClusterIPs に resolve する DNS service
  - **Service discovery**: environment variables または DNS を通じて services を discover する

4. **External Communication**:
  - **Ingress**: HTTP/HTTPS traffic を services に route する
  - **NodePort**: nodes 上の特定の ports を通じて services を公開する
  - **LoadBalancer**: cloud provider の load balancer を通じて services を公開する
  - **ExternalName**: external services の CNAME records を作成する

5. **Role of CNI (Container Network Interface) Plugins**:
  - network interfaces を pods に接続する
  - IP addresses を割り当て、管理する
  - routing tables を設定する
  - network policies を実装する
  - 主な CNI plugins:
  - **Calico**: BGP-based networking、network policy support、high performance
  - **Cilium**: eBPF-based networking and security、L3-L7 security policies、high performance
  - **Flannel**: simple overlay network、easy configuration
  - **Weave Net**: multi-host container networking、encryption support

6. **Restricting Pod-to-Pod Communication Using Network Policies**:
  - NetworkPolicy resources を使用して pod-to-pod communication を制御する
  - デフォルトでは、すべての pods は相互に通信できる（policies が存在しない場合）
  - Network policy components:
  - **podSelector**: policy が適用される pods を選択する
  - **policyTypes**: Ingress（incoming）、Egress（outgoing）、またはその両方
  - **ingress**: incoming traffic の rules
  - **egress**: outgoing traffic の rules

  - **Default deny policy example**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

  - **Policy example allowing communication only between specific pods**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

  - **Namespace-to-namespace communication control example**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            purpose: monitoring
      ports:
        - protocol: TCP
          port: 9090
```

7. **Network Policy Implementation Considerations**:
  - network policies は CNI plugins によって実装される
  - すべての CNI plugins が network policies をサポートしているわけではない
  - policies を適用する前に test environment で検証する
  - default deny policy から始め、必要な通信のみを許可することを推奨する

Kubernetes networking architecture は、containers 間の通信を柔軟かつ scalable に可能にし、network policies を通じて granular な security control を提供します。
</details>

---

[学習資料に戻る](../../core/01-cluster-architecture.md) | [次のクイズ: Pods and Workloads](../core/02-pods-and-workloads-quiz.md)
