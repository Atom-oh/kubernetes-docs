# クラスターアーキテクチャ

> **対応バージョン**: Kubernetes 1.32, 1.33, 1.34
> **最終更新**: August 31, 2026

## ラボ環境のセットアップ

このドキュメントの概念を実践するには、次のツールと環境が必要です。

### 必要なツール
- kubectl v1.34 以降
- 稼働する Kubernetes クラスター（EKS、minikube、kind など）

### ローカル開発環境のセットアップ

```bash
# Install minikube (for local development)
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Start cluster
minikube start

# Check cluster status
kubectl cluster-info

# Check control plane components
kubectl get pods -n kube-system
```

## クラスターアーキテクチャの概要

> **中核となる概念**: Kubernetes クラスターは Control Plane と worker node で構成され、それぞれは特定の役割を果たす複数のコンポーネントから成ります。

Kubernetes クラスターは、コンテナ化されたアプリケーションを実行するためのノード（仮想マシンまたは物理マシン）の集合で構成されます。クラスターは大きく Control Plane と worker node に分けられます。

### クラスターアーキテクチャ図

![Control Plane の kube-apiserver が etcd、scheduler、controller manager を調整し、worker node の kubelet と kube-proxy に到達して、さらに container runtime と実行中の Pod を駆動する様子を示すアーキテクチャ図。](../.gitbook/assets/en-core-01-cluster-architecture-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-01-cluster-architecture-0.html)

**Control Plane コンポーネント**:
- **kube-apiserver**: Kubernetes API を公開するフロントエンド
- **etcd**: すべてのクラスター データを保存するキー値ストア
- **kube-scheduler**: 新たに作成された Pod を実行するノードを選択
- **kube-controller-manager**: クラスターの状態を管理する controller を実行
- **cloud-controller-manager**: クラウドプロバイダーの API と連携

**worker node コンポーネント**:
- **kubelet**: 各ノードで実行される agent。コンテナ実行を管理
- **kube-proxy**: ネットワークルールを維持し、接続転送を実行
- **Container Runtime**: コンテナを実行（containerd、CRI-O など）

## Control Plane コンポーネント

Control Plane は Kubernetes クラスターの「頭脳」として機能し、クラスター全体の状態を管理および制御します。Control Plane コンポーネントは通常、専用マシン上で実行され、高可用性のために複数のインスタンスへ複製できます。

### Control Plane コンポーネントの詳細

| コンポーネント | 主な機能 | 通信先 | 高可用性構成 |
|-----------|---------------|----------------------|--------------------------------|
| **kube-apiserver** | - Kubernetes API を提供<br>- 認証と認可<br>- API リクエスト処理 | - すべてのコンポーネント<br>- etcd | 複数インスタンスによる水平スケーリング |
| **etcd** | - クラスター データを保存<br>- 分散キー値ストア<br>- 一貫性を保証 | - kube-apiserver | 複数ノードのクラスター |
| **kube-scheduler** | - Pod 配置の決定<br>- ノードリソースの評価<br>- affinity/anti-affinity の適用 | - kube-apiserver | Active-standby 構成 |
| **kube-controller-manager** | - Node controller<br>- Replication controller<br>- Endpoint controller<br>- Service account controller | - kube-apiserver | Active-standby 構成 |
| **cloud-controller-manager** | - クラウドプロバイダー統合<br>- ノードのライフサイクル<br>- ルーティングと負荷分散 | - kube-apiserver<br>- Cloud API | Active-standby 構成 |

### Control Plane の通信フロー

1. ユーザーまたは controller が kube-apiserver にリクエストを送信します
2. kube-apiserver が認証、認可、admission を実行します
3. kube-apiserver が etcd からデータを読み取り、または etcd へ書き込みます
4. controller と scheduler が kube-apiserver を通じてクラスター状態を watch します
5. kubelet がノード状態を kube-apiserver に報告します

### kube-apiserver

kube-apiserver は Kubernetes API を公開する Control Plane のフロントエンドです。すべての内部および外部リクエストは、この API server を介して処理されます。

**主な機能**:
- REST API を提供
- 認証と認可
- リクエストの検証と処理
- etcd との通信
- 水平スケーリング可能（複数インスタンスへスケール可能）

**主なフラグと設定オプション**:
```bash
# Basic configuration example
kube-apiserver \
  --advertise-address=192.168.1.10 \
  --allow-privileged=true \
  --authorization-mode=Node,RBAC \
  --enable-admission-plugins=NodeRestriction \
  --enable-bootstrap-token-auth=true \
  --etcd-servers=https://127.0.0.1:2379 \
  --kubelet-client-certificate=/etc/kubernetes/pki/apiserver-kubelet-client.crt \
  --kubelet-client-key=/etc/kubernetes/pki/apiserver-kubelet-client.key \
  --service-account-key-file=/etc/kubernetes/pki/sa.pub \
  --service-cluster-ip-range=10.96.0.0/12 \
  --tls-cert-file=/etc/kubernetes/pki/apiserver.crt \
  --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
```

**API Server のセキュリティ**:
- TLS 証明書による安全な通信
- さまざまな認証方式をサポート（X.509 証明書、service account token、OIDC、webhook など）
- RBAC（Role-Based Access Control）による権限管理
- admission controller によるリクエストの検証と変更

### etcd

etcd はすべてのクラスター データを保存する、一貫性と高可用性を備えたキー値ストアです。Kubernetes の「信頼できる唯一の情報源」として機能します。

**主な特徴**:
- 分散システム
- 強整合性（Raft 合意形成アルゴリズムを使用）
- 高可用性（複数ノードで構成可能）
- 安全なデータストレージ
- 変更を監視する watch 機能

**etcd クラスター構成**:
```bash
# etcd cluster configuration example (3 nodes)
etcd \
  --name etcd-1 \
  --initial-advertise-peer-urls https://192.168.1.11:2380 \
  --listen-peer-urls https://192.168.1.11:2380 \
  --listen-client-urls https://192.168.1.11:2379,https://127.0.0.1:2379 \
  --advertise-client-urls https://192.168.1.11:2379 \
  --initial-cluster-token etcd-cluster \
  --initial-cluster etcd-1=https://192.168.1.11:2380,etcd-2=https://192.168.1.12:2380,etcd-3=https://192.168.1.13:2380 \
  --initial-cluster-state new \
  --data-dir=/var/lib/etcd
```

**etcd のバックアップと復旧**:
```bash
# etcd backup
ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# etcd recovery
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://192.168.1.11:2380 \
  --initial-cluster-token=etcd-cluster \
  --initial-advertise-peer-urls=https://192.168.1.11:2380
```

**etcd のパフォーマンス最適化**:
- ディスク I/O の最適化（SSD 推奨）
- 適切なメモリ割り当て
- 定期的な compaction と defragmentation
- クラスター規模に応じた適切な etcd ノード数（通常 3 または 5）

#### 2026年7月の更新: etcd v3.7.0 リリース

2026年7月8日、SIG etcd は etcd v3.7.0 をリリースしました。主な内容は次のとおりです。

- **RangeStream**: 応答全体をメモリにバッファリングするのではなく、大規模な range 結果をチャンク単位でストリーミングします（長く要望されていた機能）。
- **パフォーマンス改善**: keys-only range リクエストを最適化し、より高速で信頼性の高い lease を実現
- 旧式の v2store の最後の残存部分を削除し、大規模な protobuf の刷新を完了
- 更新されたコア依存関係 bbolt v1.5.0 および raft v3.7.0 を同梱

詳細は [公式発表](https://kubernetes.io/blog/2026/07/08/announcing-etcd-3.7/) と [etcd v3.7 の変更履歴](https://github.com/etcd-io/etcd/blob/main/CHANGELOG/CHANGELOG-3.7.md) を参照してください。

### kube-scheduler

kube-scheduler は、新たに作成された Pod を実行するノードを選択する Control Plane コンポーネントです。

**スケジューリングプロセス**:
1. **Filtering**: Pod を実行できるノードを特定
   - リソース要件（CPU、メモリ）
   - Node selector、node affinity
   - taint と toleration
   - Volume 制約

2. **Scoring**: 適切なノードにスコアを割り当て
   - リソース使用率
   - Pod inter-affinity/anti-affinity
   - データの局所性
   - ノード間の負荷分散

3. **Binding**: Pod を最適なノードに割り当て

**Scheduler 構成**:
```bash
# Basic configuration example
kube-scheduler \
  --kubeconfig=/etc/kubernetes/scheduler.conf \
  --leader-elect=true \
  --v=2
```

**Scheduler Profile と Plugin**:
- デフォルトの scheduler profile
- カスタム scheduler profile
- Scheduler 拡張ポイント（filter、score、bind など）
- 複数 scheduler のサポート

**スケジューリングポリシー**:
```yaml
# Scheduling policy example
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      disabled:
      - name: NodeResourcesLeastAllocated
      enabled:
      - name: NodeResourcesMostAllocated
        weight: 1
```

### kube-controller-manager

kube-controller-manager は複数の controller プロセスを実行する Control Plane コンポーネントです。各 controller はクラスターの特定の側面を管理します。

**主な Controller**:
- **Node Controller**: ノード状態を監視して対応
- **Replication Controller**: Pod のレプリカ数を維持
- **Endpoint Controller**: Service と Pod を接続
- **Service Account & Token Controller**: namespace のデフォルトアカウントと API token を作成
- **Job Controller**: 一回限りのタスクを管理
- **CronJob Controller**: スケジュールされたタスクを管理
- **DaemonSet Controller**: 特定の Pod がすべてのノードで実行されることを保証
- **StatefulSet Controller**: stateful application を管理
- **PV Controller**: Persistent Volume を管理
- **Namespace Controller**: namespace のライフサイクルを管理
- **Garbage Collector**: 孤立したオブジェクトをクリーンアップ

**Controller Manager 構成**:
```bash
# Basic configuration example
kube-controller-manager \
  --kubeconfig=/etc/kubernetes/controller-manager.conf \
  --leader-elect=true \
  --use-service-account-credentials=true \
  --root-ca-file=/etc/kubernetes/pki/ca.crt \
  --service-account-private-key-file=/etc/kubernetes/pki/sa.key \
  --cluster-signing-cert-file=/etc/kubernetes/pki/ca.crt \
  --cluster-signing-key-file=/etc/kubernetes/pki/ca.key \
  --controllers=*,bootstrapsigner,tokencleaner
```

**Controller の動作**:
1. Controller は API server を通じてクラスター状態を継続的に watch します
2. 現在の状態と望ましい状態の差異を検出します
3. 差異を調整するための操作を実行します
4. 状態の変更を API server に報告します

### cloud-controller-manager

cloud-controller-manager はクラウド固有の制御ロジックを含む Control Plane コンポーネントです。これにより Kubernetes core とクラウドプロバイダー API を分離できます。

**主な Controller**:
- **Node Controller**: クラウドプロバイダー API を通じてノード状態を確認
- **Route Controller**: クラウド環境で route を設定
- **Service Controller**: クラウド load balancer を作成、更新、削除
- **Volume Controller**: クラウドストレージ Volume を作成、アタッチ、マウント

**クラウドプロバイダーの実装**:
- AWS Cloud Controller Manager
- Azure Cloud Controller Manager
- GCP Cloud Controller Manager
- OpenStack Cloud Controller Manager
- vSphere Cloud Controller Manager

**Cloud Controller Manager 構成**:
```bash
# AWS Cloud Controller Manager example
cloud-controller-manager \
  --cloud-provider=aws \
  --cloud-config=/etc/kubernetes/cloud-config \
  --kubeconfig=/etc/kubernetes/cloud-controller-manager.conf \
  --leader-elect=true
```

**Cloud Controller Manager の利点**:
- クラウドプロバイダー固有コードを Kubernetes core から分離
- クラウドプロバイダーが独自機能を独立して開発可能
- Kubernetes core を変更せずにクラウド機能を追加

## ノードコンポーネント

ノードはコンテナ化されたアプリケーションを実行する Kubernetes クラスター内の worker machine です。各ノードは Control Plane によって管理され、複数のコンポーネントで構成されます。

### kubelet

kubelet は各ノードで実行され、Pod 内のコンテナを管理する agent です。kubelet はさまざまな仕組みで PodSpec を受け取り、その仕様に従ってコンテナが正常に実行されることを保証します。

**主な機能**:
- PodSpec に従ってコンテナを実行
- コンテナ状態を監視して報告
- コンテナのライフサイクルを管理
- Volume mount を管理
- ノード状態を報告
- コンテナのヘルスチェックを実行

**kubelet 構成**:
```bash
# Basic configuration example
kubelet \
  --kubeconfig=/etc/kubernetes/kubelet.conf \
  --config=/var/lib/kubelet/config.yaml \
  --container-runtime=remote \
  --container-runtime-endpoint=unix:///var/run/containerd/containerd.sock \
  --pod-infra-container-image=k8s.gcr.io/pause:3.6
```

**kubelet 設定ファイルの例**:
```yaml
# /var/lib/kubelet/config.yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
address: 0.0.0.0
authentication:
  anonymous:
    enabled: false
  webhook:
    cacheTTL: 2m0s
    enabled: true
  x509:
    clientCAFile: /etc/kubernetes/pki/ca.crt
authorization:
  mode: Webhook
  webhook:
    cacheAuthorizedTTL: 5m0s
    cacheUnauthorizedTTL: 30s
cgroupDriver: systemd
clusterDomain: cluster.local
cpuManagerPolicy: none
evictionHard:
  memory.available: 100Mi
  nodefs.available: 10%
  nodefs.inodesFree: 5%
failSwapOn: true
healthzBindAddress: 127.0.0.1
healthzPort: 10248
```

**Static Pod**:
kubelet は API server を経由せずに直接管理する static Pod を実行できます。これは主に Control Plane コンポーネントの実行に使用されます。

```yaml
# /etc/kubernetes/manifests/kube-apiserver.yaml
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - name: kube-apiserver
    image: k8s.gcr.io/kube-apiserver:v1.24.0
    command:
    - kube-apiserver
    - --advertise-address=192.168.1.10
    # ... additional flags
```

### kube-proxy

kube-proxy は Kubernetes の Service 概念を実装する、各ノードで実行される network proxy です。ノード上のネットワークルールを維持し、接続転送を実行します。

**主な機能**:
- Service IP と port のネットワークルールを維持
- 接続転送
- 負荷分散を実装
- Service discovery をサポート

**動作モード**:
1. **userspace mode**: user space で proxy を実行（レガシー）
2. **iptables mode**: Linux iptables を使用した NAT 実装（デフォルト）
3. **IPVS mode**: Linux kernel の IP Virtual Server を使用（高性能）

**kube-proxy 構成**:
```bash
# Basic configuration example
kube-proxy \
  --config=/var/lib/kube-proxy/config.conf \
  --hostname-override=node1
```

**kube-proxy 設定ファイルの例**:
```yaml
# /var/lib/kube-proxy/config.conf
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
bindAddress: 0.0.0.0
clientConnection:
  acceptContentTypes: ""
  burst: 10
  contentType: application/vnd.kubernetes.protobuf
  kubeconfig: /var/lib/kube-proxy/kubeconfig.conf
  qps: 5
clusterCIDR: 10.244.0.0/16
configSyncPeriod: 15m0s
conntrack:
  maxPerCore: 32768
  min: 131072
  tcpCloseWaitTimeout: 1h0m0s
  tcpEstablishedTimeout: 24h0m0s
enableProfiling: false
healthzBindAddress: 0.0.0.0:10256
hostnameOverride: node1
iptables:
  masqueradeAll: false
  masqueradeBit: 14
  minSyncPeriod: 0s
  syncPeriod: 30s
ipvs:
  excludeCIDRs: null
  minSyncPeriod: 0s
  scheduler: ""
  syncPeriod: 30s
mode: "iptables"
```

**IPVS と iptables mode の比較**:

| 特性 | iptables mode | IPVS mode |
|----------------|---------------|-----------|
| パフォーマンス | Service 数が多い場合にパフォーマンス低下 | 大規模クラスターで高パフォーマンス |
| 負荷分散アルゴリズム | round robin のみサポート | 各種アルゴリズムをサポート（rr、lc、dh、sh、sed、nq） |
| 実装 | ネットワークパケット filtering chain | hash table ベース |
| kernel 要件 | デフォルトの kernel module | IPVS kernel module が必要 |

### Container Runtime

Container runtime はコンテナを実行するソフトウェアです。Kubernetes は Container Runtime Interface（CRI）を通じてさまざまな Container runtime をサポートします。

**主な Container Runtime**:
1. **containerd**: 軽量な Container runtime（現在最も広く使用）
2. **CRI-O**: Kubernetes 向けに特化して設計された軽量 runtime
3. **Docker Engine**: Docker shim を通じてサポート（Kubernetes 1.24 から非推奨）

**Container Runtime のレイヤー構造**:

![Kubernetes が Container Runtime Interface を呼び出し、それが containerd または CRI-O に委任され、それぞれが低レベル runtime（runc または crun）によって支えられることを示すツリー図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-1.svg)

**containerd 構成例**:
```toml
# /etc/containerd/config.toml
version = 2

[plugins]
  [plugins."io.containerd.grpc.v1.cri"]
    sandbox_image = "k8s.gcr.io/pause:3.6"
    [plugins."io.containerd.grpc.v1.cri".containerd]
      default_runtime_name = "runc"
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
          runtime_type = "io.containerd.runc.v2"
          [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
            SystemdCgroup = true
```

**CRI-O 構成例**:
```toml
# /etc/crio/crio.conf
[crio]
root = "/var/lib/containers/storage"
runroot = "/var/run/containers/storage"
storage_driver = "overlay"
storage_option = ["overlay.mountopt=nodev"]

[crio.runtime]
default_runtime = "runc"
conmon = "/usr/bin/conmon"
conmon_cgroup = "pod"
cgroup_manager = "systemd"

[crio.image]
pause_image = "k8s.gcr.io/pause:3.6"
```

### Add-on コンポーネント

Add-on は Kubernetes クラスターの機能を拡張する追加コンポーネントです。重要な Add-on には次のものがあります。

1. **CNI Network Plugin**: Pod networking を実装
   - Calico、Cilium、Flannel、Weave Net など

2. **DNS**: クラスター内で DNS service を提供
   - CoreDNS（デフォルト）

3. **Dashboard**: web ベースの UI を提供
   - Kubernetes Dashboard

4. **Ingress Controller**: HTTP/HTTPS routing を管理
   - NGINX Ingress Controller、Traefik、HAProxy など

5. **Metrics Server**: リソース使用量 metrics を収集
   - Metrics Server

6. **Logging と Monitoring**: log collection と monitoring
   - Prometheus、Grafana、Elasticsearch、Fluentd、Kibana など

**CoreDNS 構成例**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf {
            max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
```

**Calico CNI 構成例**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: calico-config
  namespace: kube-system
data:
  calico_backend: "bird"
  cni_network_config: |-
    {
      "name": "k8s-pod-network",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "calico",
          "log_level": "info",
          "datastore_type": "kubernetes",
          "nodename": "__KUBERNETES_NODE_NAME__",
          "mtu": __CNI_MTU__,
          "ipam": {
            "type": "calico-ipam"
          },
          "policy": {
            "type": "k8s"
          },
          "kubernetes": {
            "kubeconfig": "__KUBECONFIG_FILEPATH__"
          }
        },
        {
          "type": "portmap",
          "snat": true,
          "capabilities": {"portMappings": true}
        }
      ]
    }
```

## クラスター通信経路

Kubernetes クラスター内では、さまざまなコンポーネント間で通信が発生します。これらの通信経路を理解することは、クラスター設計、セキュリティ、トラブルシューティングに重要です。

### Control Plane 内部通信

![scheduler、controller manager、cloud controller manager のすべてが kube-apiserver を呼び出し、kube-apiserver が gRPC を介して etcd のクラスター状態を読み書きすることを示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-2.svg)

Control Plane コンポーネント間の通信は次のとおりです。

1. **kube-apiserver と etcd**: kube-apiserver はクラスター状態を保存および取得するために etcd と通信します。
   - プロトコル: gRPC
   - ポート: 2379/TCP
   - セキュリティ: TLS 証明書ベースの認証

2. **kube-scheduler と kube-apiserver**: kube-scheduler は Pod scheduling のために kube-apiserver と通信します。
   - プロトコル: HTTPS
   - ポート: 6443/TCP（kube-apiserver）
   - セキュリティ: TLS 証明書ベースの認証

3. **kube-controller-manager と kube-apiserver**: Controller はクラスター状態を watch および変更するために kube-apiserver と通信します。
   - プロトコル: HTTPS
   - ポート: 6443/TCP（kube-apiserver）
   - セキュリティ: TLS 証明書ベースの認証

4. **cloud-controller-manager と kube-apiserver**: Cloud controller はクラスター状態を watch し、クラウドリソースを管理するために kube-apiserver と通信します。
   - プロトコル: HTTPS
   - ポート: 6443/TCP（kube-apiserver）
   - セキュリティ: TLS 証明書ベースの認証

### Control Plane とノードの通信

![kube-apiserver と各ノードの kubelet および kube-proxy 間の双方向 HTTPS 通信を示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-3.svg)

Control Plane とノード間の通信は次のとおりです。

1. **kube-apiserver と kubelet**: kube-apiserver は Pod spec を配信し、ノード状態を収集するために kubelet と通信します。
   - プロトコル: HTTPS
   - ポート: 10250/TCP（kubelet）
   - セキュリティ: TLS 証明書ベースの認証

2. **kubelet と kube-apiserver**: kubelet はノード登録、Pod 状態報告、event 送信のために kube-apiserver と通信します。
   - プロトコル: HTTPS
   - ポート: 6443/TCP（kube-apiserver）
   - セキュリティ: TLS 証明書ベースの認証

3. **kube-proxy と kube-apiserver**: kube-proxy は Service 情報を取得するために kube-apiserver と通信します。
   - プロトコル: HTTPS
   - ポート: 6443/TCP（kube-apiserver）
   - セキュリティ: TLS 証明書ベースの認証

### ノード間通信

![異なるノード上に存在する可能性がある 4 つの Pod が、共有 CNI network を通じてすべて相互に双方向通信することを示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-4.svg)

ノード間通信は次のとおりです。

1. **Pod 間通信**: Pod は CNI plugin が提供する network を通じて相互に通信します。
   - プロトコル: アプリケーションに依存（TCP、UDP など）
   - ポート: アプリケーションに依存
   - セキュリティ: network policy により制御可能

2. **ノードをまたぐ Pod 通信**: 異なるノード上の Pod 間通信は CNI plugin によって処理されます。
   - プロトコル: アプリケーションに依存（TCP、UDP など）
   - ポート: アプリケーションに依存
   - セキュリティ: network policy により制御可能

### 外部通信

![外部 client がクラスター管理のために kube-apiserver へ直接到達し、application traffic が Service または Ingress を介して Pod に到達することを示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-5.svg)

外部エンティティとの通信は次のとおりです。

1. **Client と kube-apiserver**: ユーザーおよび外部システムは kube-apiserver を通じてクラスターとやり取りします。
   - プロトコル: HTTPS
   - ポート: 6443/TCP（kube-apiserver）
   - セキュリティ: TLS 証明書、token、ユーザー認証など

2. **外部 traffic と Service**: 外部 traffic は NodePort、LoadBalancer Service、または Ingress を通じてクラスター内の application にアクセスします。
   - プロトコル: HTTP、HTTPS、TCP、UDP など
   - ポート: Service 構成に依存
   - セキュリティ: Ingress controller と Service 構成に依存

### 通信セキュリティ

Kubernetes クラスター内の通信セキュリティは、次の方法で実装されます。

1. **TLS 証明書**: Control Plane コンポーネント間のすべての通信は TLS 証明書で暗号化されます。
2. **認証と認可**: API server へのすべてのリクエストは認証および認可プロセスを通過します。
3. **Network Policy**: Pod 間通信は network policy を通じて制限できます。
4. **暗号化された Secret**: etcd に保存される Secret は暗号化できます。

**API Server 通信セキュリティ構成例**:
```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64-encoded-key>
    - identity: {}
```

### 高可用性クラスター構成

高可用性（HA）Kubernetes クラスターは、単一障害点を排除し、サービス中断なしに継続運用できるよう設計されています。

### Control Plane の高可用性

Control Plane の高可用性は、次の方法で実装されます。

1. **複数の Control Plane ノード**: 通常、冗長性のために 3 または 5 台の Control Plane ノードをデプロイ
2. **etcd クラスター**: 複数の etcd インスタンスで構成されるクラスターをデプロイ（通常 3 または 5）
3. **Load Balancer**: API server の前に load balancer を配置して traffic を分散

**高可用性 Control Plane アーキテクチャ**:

![load balancer が、各自の kube-apiserver、etcd、kube-scheduler、kube-controller-manager を実行する 3 つの複製された Control Plane ノードに traffic を分散することを示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-6.svg)

**etcd クラスター構成**:

![3 つの etcd ノードが ring を形成し、Raft 合意形成プロトコルを介して状態を複製するために各ペアが双方向接続されていることを示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-7.svg)

### worker node の高可用性

worker node の高可用性は、次の方法で実装されます。

1. **複数の worker node**: workload を複数の worker node に分散
2. **自動ノード復旧**: クラウドプロバイダーの自動復旧機能を活用
3. **Auto Scaling**: cluster autoscaler による自動ノードスケーリング
4. **複数の Availability Zone**: 複数の Availability Zone にノードをデプロイ

**worker node の分散デプロイ**:

![障害分離のため、3 つの Availability Zone に各 2 台ずつ worker node が分散していることを示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-8.svg)

### application の高可用性

application の高可用性は、次の方法で実装されます。

1. **ReplicaSet/Deployment**: 複数の Pod replica を実行
2. **Pod 分散ルール**: Pod anti-affinity により Pod を複数ノードへ分散
3. **PodDisruptionBudget**: 計画的な中断時の最小可用性を保証
4. **Service と負荷分散**: traffic を複数の Pod に分散

**Pod Anti-Affinity の例**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: web-server
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-server
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: web-server
        image: nginx:1.21
```

**PodDisruptionBudget の例**:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-server-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-server
```

### 災害復旧戦略

Kubernetes クラスターの災害復旧戦略は、次の方法で実装されます。

1. **etcd のバックアップと復旧**: 定期的な etcd データのバックアップおよび復旧手順を確立
2. **Multi-Region デプロイ**: 複数の Region にクラスターをデプロイ
3. **Cluster Federation**: 複数クラスターを federation で管理
4. **継続的バックアップ**: application data を継続的にバックアップ

**etcd バックアップスクリプトの例**:
```bash
#!/bin/bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d-%H%M%S).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

**etcd 復旧スクリプトの例**:
```bash
#!/bin/bash
# Stop cluster
systemctl stop kubelet
docker stop $(docker ps -q)

# Recover etcd data
ETCDCTL_API=3 etcdctl snapshot restore /backup/etcd-snapshot.db \
  --data-dir=/var/lib/etcd-restore \
  --name=master \
  --initial-cluster=master=https://127.0.0.1:2380 \
  --initial-cluster-token=etcd-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380

# Replace etcd directory with recovered data
mv /var/lib/etcd /var/lib/etcd.old
mv /var/lib/etcd-restore /var/lib/etcd

# Restart cluster
systemctl start kubelet
```

## クラスターネットワーキング

Kubernetes networking により、Pod、Service、外部との通信が可能になります。Kubernetes networking model は、すべての Pod が一意の IP address を持ち、NAT なしで相互に通信できることを前提としています。

### ネットワーキングモデル

Kubernetes networking model には、次の要件があります。

1. **Pod 間通信**: すべての Pod は NAT なしですべての他の Pod と通信できなければなりません
2. **ノードから Pod への通信**: ノードは NAT なしですべての Pod と通信できなければなりません
3. **Pod から外部への通信**: Pod は外部と通信できなければなりません（通常は NAT を使用）

### CNI (Container Network Interface)

CNI は Kubernetes で networking を実装するための標準 interface です。さまざまな CNI plugin があり、それぞれ異なる機能とパフォーマンス特性を備えています。

**主な CNI Plugin**:

1. **Calico**: BGP ベースの networking、network policy をサポート
   - 特徴: 高パフォーマンス、network policy、暗号化、eBPF サポート
   - ユースケース: 大規模クラスター、セキュリティ重視の環境

2. **Cilium**: eBPF ベースの networking とセキュリティ
   - 特徴: L3-L7 security policy、高パフォーマンス、observability
   - ユースケース: Microservices、セキュリティ重視の環境

3. **Flannel**: シンプルな overlay network
   - 特徴: セットアップが簡単、軽量
   - ユースケース: 小規模クラスター、開発環境

4. **Weave Net**: マルチホスト container networking
   - 特徴: 暗号化、network policy、multi-cloud
   - ユースケース: Hybrid cloud、multi-cloud

**CNI 構成例（Calico）**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: calico-config
  namespace: kube-system
data:
  calico_backend: "bird"
  cni_network_config: |-
    {
      "name": "k8s-pod-network",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "calico",
          "log_level": "info",
          "datastore_type": "kubernetes",
          "nodename": "__KUBERNETES_NODE_NAME__",
          "mtu": __CNI_MTU__,
          "ipam": {
            "type": "calico-ipam"
          },
          "policy": {
            "type": "k8s"
          },
          "kubernetes": {
            "kubeconfig": "__KUBECONFIG_FILEPATH__"
          }
        },
        {
          "type": "portmap",
          "snat": true,
          "capabilities": {"portMappings": true}
        }
      ]
    }
```

### Service Networking

Kubernetes Service は一連の Pod に安定した endpoint を提供します。Service には ClusterIP、NodePort、LoadBalancer、ExternalName など複数の type があります。

**Service Networking コンポーネント**:

1. **ClusterIP**: クラスター内からのみアクセス可能な virtual IP
2. **kube-proxy**: Service IP 宛ての traffic を Pod に routing
3. **CoreDNS**: Service discovery のための DNS service

**Service Networking フロー**:
```
Client -> Service (ClusterIP) -> kube-proxy -> Pod
```

**Service の例**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

### Ingress Networking

Ingress はクラスター外部からクラスター内部の Service への HTTP および HTTPS routing を管理します。Ingress controller が Ingress resource を実装します。

**主な Ingress Controller**:
1. **NGINX Ingress Controller**: NGINX ベースの Ingress controller
2. **AWS ALB Ingress Controller**: AWS Application Load Balancer をベース
3. **Traefik**: Cloud-native edge router
4. **HAProxy Ingress**: HAProxy ベースの Ingress controller

**Ingress Networking フロー**:
```
Client -> Ingress Controller -> Service -> Pod
```

**Ingress の例**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: example.com
    http:
      paths:
      - path: /app
        pathType: Prefix
        backend:
          service:
            name: my-service
            port:
              number: 80
```

### Network Policy

Network policy は Pod 間の通信を制御する方法を提供します。デフォルトではすべての Pod が相互に通信できますが、network policy によりこれを制限できます。

**Network Policy の例**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 3306
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

### ネットワークトラブルシューティング

Kubernetes networking の問題をトラブルシューティングするための一般的なツールとコマンド:

1. **ping、traceroute**: 基本的な network connectivity のテスト
2. **tcpdump**: ネットワークパケットのキャプチャと分析
3. **netstat、ss**: ネットワーク接続状態の確認
4. **nslookup、dig**: DNS lookup のテスト
5. **kubectl exec**: Pod 内で network command を実行

**ネットワークデバッグの例**:
```bash
# Test network connectivity within a pod
kubectl exec -it <pod-name> -- ping <target-ip>

# Test DNS lookup within a pod
kubectl exec -it <pod-name> -- nslookup <service-name>

# Capture network packets within a pod
kubectl exec -it <pod-name> -- tcpdump -i eth0 -n

# Check service endpoints
kubectl get endpoints <service-name>
```

## クラスターストレージ

Kubernetes storage はコンテナ化された application にデータ永続化を提供します。Kubernetes は、application が storage を効率的に使用できるよう、さまざまな storage option と abstraction を提供します。

### ストレージアーキテクチャ

Kubernetes storage architecture は、次のコンポーネントで構成されます。

1. **Volume**: Pod 内の container に mount できる directory
2. **Persistent Volume (PV)**: クラスター内の storage resource
3. **Persistent Volume Claim (PVC)**: ユーザーからの storage request
4. **Storage Class**: storage の「class」または type を定義
5. **CSI (Container Storage Interface)**: storage system との標準 interface

**ストレージアーキテクチャフロー**:

![Pod の volume mount が、PVC と PV を経て CSI driver により実際の storage backend に解決されることを示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-9.svg)

### Volume の種類

Kubernetes はさまざまな種類の Volume をサポートします。

1. **Ephemeral Volume**:
   - **emptyDir**: 空の directory として開始され、Pod の削除時に削除されます
   - **configMap**: ConfigMap を Volume として mount
   - **secret**: Secret を Volume として mount
   - **downwardAPI**: Pod と container の情報を file として公開

2. **Persistent Volume**:
   - **awsElasticBlockStore**: AWS EBS Volume
   - **azureDisk**: Azure Disk
   - **gcePersistentDisk**: GCE Persistent Disk
   - **nfs**: NFS Volume
   - **csi**: CSI driver を介した Volume

**Volume の例**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - name: test-container
    image: nginx
    volumeMounts:
    - mountPath: /test-pd
      name: test-volume
  volumes:
  - name: test-volume
    persistentVolumeClaim:
      claimName: test-pvc
```

### Persistent Volume と Claim

Persistent Volume（PV）は、管理者によってプロビジョニングされる、または Storage Class を通じて動的にプロビジョニングされるクラスター内の storage resource です。Persistent Volume Claim（PVC）はユーザーからの storage request です。

**Persistent Volume の例**:
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-example
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: standard
  awsElasticBlockStore:
    volumeID: vol-0123456789abcdef0
    fsType: ext4
```

**Persistent Volume Claim の例**:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-example
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: standard
```

### Storage Class

Storage Class は、管理者が提供する storage の「class」を説明します。Storage Class により、PVC が要求されたときに PV を動的にプロビジョニングできます。

**Storage Class の例**:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  fsType: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
```

### CSI (Container Storage Interface)

CSI は Kubernetes と storage system の間に標準 interface を提供します。CSI を通じて、storage provider は Kubernetes code を変更せずに独自の storage driver を開発できます。

**CSI アーキテクチャ**:

![Kubernetes が Container Storage Interface を呼び出し、それが vendor CSI driver に委任され、基盤となる storage system をプロビジョニングすることを示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-10.svg)

**CSI Driver デプロイ例**:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  fsType: ext4
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

### ストレージのベストプラクティス

Kubernetes storage を使用する際のベストプラクティス:

1. **適切な Storage Type の選択**: workload の特性に一致する storage type を選択
2. **動的プロビジョニングの使用**: Storage Class を通じた動的プロビジョニングを活用
3. **適切な Access Mode の選択**: workload 要件に一致する access mode を選択
4. **Resource Request と Limit の設定**: 適切な storage capacity を要求
5. **バックアップと復旧戦略の確立**: 重要データ向けのバックアップおよび復旧戦略を準備
6. **Storage の監視**: storage 使用量とパフォーマンスを監視

## クラスターのスケーラビリティ

Kubernetes クラスターのスケーラビリティは、増加する load と要件を処理するクラスターの能力を指します。スケーラビリティは、horizontal scaling（scale out）と vertical scaling（scale up）によって実装できます。

### クラスターのスケール上限

Kubernetes クラスターには、次のスケール上限があります。

1. **ノード数**: 最大 5,000 ノード
2. **Pod 数**: クラスターあたり最大 150,000 Pod
3. **ノードあたりの Pod 数**: ノードあたり最大 110 Pod（デフォルト）
4. **Service 数**: クラスターあたり最大 10,000 Service
5. **Pod あたりの container 数**: Pod あたり最大 20 container

これらの上限は Kubernetes version およびクラスター構成によって異なる場合があります。

### Horizontal Scaling

Horizontal scaling は、ノードを追加してクラスター capacity を増加させます。

**Node Auto Scaling**:
Kubernetes Cluster Autoscaler は、workload 要件に基づいてノード数を自動調整します。

```yaml
# AWS Auto Scaling Group tags example
tags:
  k8s.io/cluster-autoscaler/enabled: "true"
  k8s.io/cluster-autoscaler/my-cluster: "owned"
```

**Cluster Autoscaler デプロイ例**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      containers:
      - name: cluster-autoscaler
        image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.24.0
        command:
        - ./cluster-autoscaler
        - --cloud-provider=aws
        - --nodes=2:10:my-asg-group
        - --scale-down-unneeded-time=10m
```

**Karpenter**:
Karpenter は AWS が開発した新しい node auto-scaling tool であり、より高速かつ効率的な node provisioning を提供します。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  subnetSelector:
    karpenter.sh/discovery: my-cluster
  securityGroupSelector:
    karpenter.sh/discovery: my-cluster
```

### Vertical Scaling

Vertical scaling は、既存ノードの resource（CPU、メモリ）を増加させます。

**Vertical Pod Autoscaler (VPA)**:
VPA は Pod の CPU およびメモリ request を自動調整します。

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
```

### application のスケーリング

application レベルの scaling は、Pod replica 数を調整することで実装されます。

**Horizontal Pod Autoscaler (HPA)**:
HPA は CPU utilization または custom metric に基づいて Pod replica 数を自動調整します。

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

**KEDA (Kubernetes Event-driven Autoscaling)**:
KEDA は event-driven autoscaling を提供し、さまざまな event source に基づく scaling を可能にします。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-app-scaledobject
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka.svc:9092
      consumerGroup: my-group
      topic: my-topic
      lagThreshold: "10"
```

### スケーラビリティのベストプラクティス

Kubernetes クラスターのスケーラビリティに関するベストプラクティス:

1. **Resource Request と Limit の設定**: すべての Pod に適切な resource request と limit を設定
2. **Node Pool 戦略**: workload 特性ごとに複数の node pool を構成
3. **Auto Scaling の構成**: Cluster Autoscaler、HPA、VPA を適切に構成
4. **効率的な Pod 配置**: node affinity、Pod affinity/anti-affinity を活用
5. **クラスター監視**: resource 使用量とパフォーマンスを継続的に監視
6. **Load Testing**: scaling 戦略を検証するために定期的に load test を実施

## クラスターセキュリティ

Kubernetes クラスターのセキュリティは複数のレイヤーで実装する必要があります。これには認証、認可、network policy、Pod security などが含まれます。

### 認証

Kubernetes API server へのアクセスを認証する方法:

1. **X.509 証明書**: TLS client certificate を使用する認証
2. **Service Account Token**: Pod 内から API server にアクセスするための token
3. **OpenID Connect (OIDC)**: 外部 identity provider を通じた認証
4. **Webhook Token Authentication**: 外部認証 service を通じた認証
5. **Authentication Proxy**: authentication proxy を通じた認証

**kubeconfig の例**:
```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    certificate-authority-data: <CA-DATA>
    server: https://api.my-cluster.example.com
users:
- name: admin
  user:
    client-certificate-data: <CERT-DATA>
    client-key-data: <KEY-DATA>
contexts:
- name: my-context
  context:
    cluster: my-cluster
    user: admin
current-context: my-context
```

### 認可

認証済みユーザーの操作を制御する方法:

1. **RBAC (Role-Based Access Control)**: role-based access control
2. **ABAC (Attribute-Based Access Control)**: attribute-based access control
3. **Node Authorization**: ノード向けの特別な authorization
4. **Webhook Authorization**: 外部 service を通じた authorization

**RBAC の例**:
```yaml
# Role definition
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]

# Role binding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: jane
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

### ネットワークセキュリティ

クラスター内の network traffic を保護する方法:

1. **Network Policy**: Pod 間通信を制御
2. **暗号化された通信**: TLS による通信の暗号化
3. **Service Mesh**: Istio、Linkerd などによる高度な network security

**Network Policy の例**:
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

### Pod Security

Pod レベルでのセキュリティ実装:

1. **Pod Security Context**: Pod および container レベルの security setting
2. **Pod Security Standards**: Pod security 要件を定義
3. **seccomp Profile**: system call の制限
4. **AppArmor/SELinux**: mandatory access control

**Pod Security Context の例**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-context-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

### Secret Management

機密情報を安全に管理する方法:

1. **Kubernetes Secret**: 基本的な Secret resource を使用
2. **暗号化された etcd**: etcd に保存された Secret を暗号化
3. **外部 Secret Management**: HashiCorp Vault、AWS Secrets Manager などを活用

**暗号化された etcd 構成例**:
```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64-encoded-key>
    - identity: {}
```

### セキュリティのベストプラクティス

Kubernetes クラスターのセキュリティに関するベストプラクティス:

1. **最小権限の原則**: 必要最小限の権限のみを付与
2. **定期的な更新**: クラスターとコンポーネントを定期的に更新
3. **ネットワーク分離**: network policy を通じて Pod 間通信を制限
4. **Image Security**: 信頼できる image のみを使用し、脆弱性スキャンを実装
5. **Audit Logging**: クラスター活動の audit log を有効化
6. **Security Benchmark**: CIS benchmark などのセキュリティ標準に準拠

## クラスターアップグレード

Kubernetes クラスターのアップグレードは、新機能、security patch、bug fix を適用するために必要です。アップグレードは慎重に計画および実行する必要があります。

### 2026年7月の更新: Kubernetes v1.37 が Beta に

v1.37.0-beta.0 は 2026年7月20日に公開され、次の minor release である v1.37 は release cycle の後期段階に入りました。Code Freeze は予定どおり 2026年7月22～23日に発効し、最終的な v1.37.0 release は 2026年8月26日に予定されています。完全なスケジュールについては、[v1.37 release information](https://www.kubernetes.dev/resources/release/) を参照してください。

同じ週（2026年7月22～23日）に、サポート対象のすべての line 向けに patch release が公開されました: [v1.36.3](https://github.com/kubernetes/kubernetes/releases/tag/v1.36.3)、[v1.35.7](https://github.com/kubernetes/kubernetes/releases/tag/v1.35.7)、[v1.34.10](https://github.com/kubernetes/kubernetes/releases/tag/v1.34.10)。通常どおり、ご使用の minor version 向けの最新 patch を適用することを推奨します。

### 2026年8月の更新: v1.37 の先行情報

2026年7月31日、release team は [Kubernetes v1.37 の先行情報](https://kubernetes.io/blog/2026/07/31/kubernetes-v1-37-sneak-peek/)を公開し、2026年8月26日に予定されている最終 v1.37.0 release に先立って、予定されている非推奨化、削除、機能変更を説明しました。Docs Freeze は 2026年8月5～6日に発効しました。一方、次の cycle の最初の tag、v1.38.0-alpha.0 は 2026年8月6日に作成されました。

### 2026年8月の更新: Patch Release と v1.37.0-rc.1

2026年8月20日、サポート対象のすべての line 向けに patch release が公開されました: [v1.36.4](https://github.com/kubernetes/kubernetes/releases/tag/v1.36.4)、[v1.35.8](https://github.com/kubernetes/kubernetes/releases/tag/v1.35.8)、[v1.34.11](https://github.com/kubernetes/kubernetes/releases/tag/v1.34.11)。通常どおり、ご使用の minor version 向けの最新 patch を適用することを推奨します。

同日、v1.37 向けの 2 番目の release candidate である [v1.37.0-rc.1](https://github.com/kubernetes/kubernetes/releases/tag/v1.37.0-rc.1) も tag 付けされました（rc.0 は 8月6日に作成）。これにより、最終 v1.37.0 release は 2026年8月26日に予定どおり進んでいます。

### 2026年8月の更新: Kubernetes v1.37 "Garhwal" リリース

[Kubernetes v1.37 "Garhwal"](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/) は、2026年8月26日に予定どおりリリースされました。この release は 67 件の enhancement で構成されます。16 件が Stable に昇格し、23 件が Beta に昇格し、残りは Alpha として導入されました。主な内容は次のとおりです。

- **Pod certificate と ClusterTrustBundle が Stable に昇格**: Service account token の代替として workload 向けに X.509 certificate を自動発行・ローテーションする PodCertificate feature と、trust anchor を配布する ClusterTrustBundle resource が標準機能になりました（[詳細記事](https://kubernetes.io/blog/2026/08/28/kubernetes-v1-37-pod-certificates-and-cluster-trust-bundles/)）
- **Metrics API (metrics.k8s.io) が GA に**: `kubectl top` と HPA が使用する resource metrics API が stable に昇格しました（[詳細記事](https://kubernetes.io/blog/2026/08/27/kubernetes-v1-37-metrics-api-ga/)）
- その他の **Stable**: いくつかの DRA（Dynamic Resource Allocation）機能、耐障害性のある watchcache 初期化など / **Beta**: HPA scale-to-zero、manifest ベースの admission control 構成など / **Alpha**: Pod レベルの checkpoint と restore など
- **非推奨化**: kube-dns、kube-proxy の `ipvs` mode、`kubectl run --filename/-f` が非推奨となり、static Pod は Secret または ConfigMap を参照できなくなりました。cgroup v1 サポートの削除も引き続き進行中です。

アップグレード前に、[公式 release note](https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.37.md) の非推奨化および削除を必ず確認してください。

### アップグレード戦略

Kubernetes クラスターアップグレードの戦略:

1. **Blue/Green Upgrade**: 新しい version のクラスターを別途作成し、workload を移行
2. **In-Place Upgrade**: 既存クラスターを直接アップグレード
3. **Canary Upgrade**: 検証のため最初に一部のノードのみをアップグレード

### アップグレード順序

Kubernetes クラスターアップグレードの一般的な順序:

1. **Control Plane Upgrade**: kube-apiserver、kube-controller-manager、kube-scheduler、etcd
2. **DNS と CNI Upgrade**: CoreDNS、CNI plugin、その他の主要 Add-on
3. **worker node Upgrade**: worker node を順番にアップグレード

**kubeadm Upgrade の例**:
```bash
# Control plane upgrade
kubeadm upgrade plan
kubeadm upgrade apply v1.24.0

# Worker node upgrade
kubectl drain <node-name> --ignore-daemonsets
# Upgrade kubelet and kubeadm on the node
apt-get update && apt-get install -y kubelet=1.24.0-00 kubeadm=1.24.0-00
kubeadm upgrade node
systemctl restart kubelet
kubectl uncordon <node-name>
```

### アップグレード時の考慮事項

Kubernetes クラスターをアップグレードする際の考慮事項:

1. **API 変更**: 新しい version の API 変更を確認
2. **Feature Gate**: 新しい feature gate とデフォルト値の変更を確認
3. **依存関係**: CNI、CSI などの依存コンポーネントの互換性を確認
4. **Downtime**: アップグレード中に予想される downtime を計画
5. **Rollback Plan**: 問題発生時の rollback plan を確立

### アップグレードのベストプラクティス

Kubernetes クラスターアップグレードのベストプラクティス:

1. **最初にテスト環境でテスト**: 本番アップグレード前にテスト環境で検証
2. **段階的アップグレード**: 一度に 1 つの minor version をアップグレード
3. **バックアップ**: アップグレード前に etcd data をバックアップ
4. **ドキュメント化**: アップグレード手順と結果を文書化
5. **監視**: アップグレード中および後にクラスター状態を監視
6. **アップグレードウィンドウ**: traffic が少ない時間帯にアップグレードを実施

## Amazon EKS クラスターアーキテクチャ

Amazon EKS（Elastic Kubernetes Service）は AWS が提供する managed Kubernetes service です。EKS は基本的な Kubernetes 機能をすべて提供するとともに、AWS service との統合および管理の利便性を追加します。

### EKS アーキテクチャの概要

EKS クラスターは、次のコンポーネントで構成されます。

1. **EKS Control Plane**: AWS が管理する Kubernetes Control Plane
2. **EKS Node**: ユーザーが管理する worker node（EC2 instance）
3. **EKS Managed Node Group**: AWS が管理する node group
4. **EKS Fargate Profile**: serverless container 実行環境
5. **VPC と Subnet**: クラスターネットワーキング用の VPC と Subnet

**EKS アーキテクチャ図**:

![AWS Cloud が managed EKS Control Plane、顧客運用の worker node、そしてクラスターが依存する AWS service と VPC networking をホストすることを示すアーキテクチャ図。](../../assets/diagrams/rendered/en-core-01-cluster-architecture-11.svg)

### EKS Control Plane

EKS Control Plane は AWS によって管理され、複数の Availability Zone にわたる高可用性を提供します。

**主な特徴**:
1. **Managed Service**: AWS が Control Plane の保守およびアップグレードを管理
2. **高可用性**: 複数の Availability Zone にデプロイ
3. **Auto Scaling**: load に基づいて自動スケール
4. **セキュリティ**: AWS security service と統合

### EKS Node Type

EKS はさまざまな type の node をサポートします。

1. **Self-Managed Node**: ユーザーが EC2 instance を直接管理
2. **Managed Node Group**: AWS が node lifecycle を管理
3. **Fargate**: serverless container 実行環境
4. **Bottlerocket Node**: container workload 向けに最適化された OS

**Managed Node Group の例**:
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: ap-northeast-2
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    volumeSize: 80
    privateNetworking: true
    labels:
      role: worker
    tags:
      nodegroup-role: worker
    iam:
      withAddonPolicies:
        autoScaler: true
        albIngress: true
```

### EKS Networking

EKS networking は Amazon VPC をベースとし、次のコンポーネントを含みます。

1. **VPC CNI Plugin**: AWS VPC networking との統合
2. **Security Group**: node および Pod レベルの network security
3. **Load Balancer Integration**: ELB、ALB、NLB との統合
4. **VPC Endpoint**: AWS service との private communication

**VPC CNI 構成例**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-network-policy: "true"
  enable-pod-eni: "true"
  warm-ip-target: "5"
  minimum-ip-target: "10"
```

### EKS Storage

EKS はさまざまな AWS storage service と統合します。

1. **EBS CSI Driver**: Amazon EBS Volume 管理
2. **EFS CSI Driver**: Amazon EFS file system 管理
3. **FSx for Lustre CSI Driver**: FSx for Lustre file system 管理
4. **S3**: object storage

**EBS CSI Driver の例**:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

### EKS Security

EKS は AWS security service と統合し、強力なセキュリティを提供します。

1. **IAM Integration**: AWS IAM と Kubernetes RBAC の統合
2. **VPC Security**: VPC security group と network ACL
3. **AWS KMS**: Secret encryption 向けの KMS 統合
4. **AWS WAF**: web application firewall 統合
5. **AWS Shield**: DDoS 保護

**IAM Role Service Account の例**:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/s3-reader-role
```

### EKS Monitoring と Logging

EKS は AWS monitoring および logging service と統合します。

1. **CloudWatch Container Insights**: container monitoring
2. **CloudWatch Logs**: log collection と分析
3. **X-Ray**: distributed tracing
4. **Prometheus と Grafana**: open source monitoring tool の統合

**CloudWatch Container Insights の例**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: amazon-cloudwatch
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: cloudwatch-agent
  namespace: amazon-cloudwatch
spec:
  selector:
    matchLabels:
      name: cloudwatch-agent
  template:
    metadata:
      labels:
        name: cloudwatch-agent
    spec:
      containers:
      - name: cloudwatch-agent
        image: amazon/cloudwatch-agent:1.247347.6b250880
        # ... additional configuration
```

### EKS コスト最適化

EKS クラスターのコストを最適化する方法:

1. **Spot Instance**: コスト効率のよい Spot instance を活用
2. **Fargate**: serverless container 実行により idle resource のコストを削減
3. **Auto Scaling**: cluster autoscaler による resource 最適化
4. **Graviton Processor**: ARM ベースの Graviton instance を活用
5. **Resource Request の最適化**: 適切な resource request と limit を設定

**Spot Instance Node Group の例**:
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: ap-northeast-2
managedNodeGroups:
  - name: spot-ng
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    spot: true
    desiredCapacity: 3
    minSize: 2
    maxSize: 10
```

## さらに学ぶ

このドキュメントで扱ったクラスターアーキテクチャへの理解を深めるには、次のトピックを参照してください。

- [Kubernetes の紹介](../basics/04-kubernetes-introduction.md) - Kubernetes の基本概念と歴史
- [Pod と Workload](./02-pods-and-workloads.md) - クラスター内で実行される workload の管理
- [Service と Networking](./03-services-networking.md) - クラスター内の networking 構成
- [Scheduling、Preemption、Eviction](./08-scheduling-preemption-eviction.md) - Pod がノードへ配置される仕組み
- [クラスター管理](./09-cluster-administration.md) - クラスターの運用と管理
- [EKS の紹介](../eks/01-eks-introduction.md) - Amazon EKS service の概要
- [EKS クラスターの作成](../eks/02-eks-cluster-creation-part1.md) - EKS クラスターの作成方法

### ハンズオンと高度な学習

- [Kubernetes 公式チュートリアル](https://kubernetes.io/docs/tutorials/) - ハンズオンによる学習
- [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way) - Kubernetes クラスターを手動で構築
- [Cilium Networking](../networking/cilium/01-introduction.md) - 高度な networking および security 機能

## まとめ

このドキュメントでは、Kubernetes クラスターのアーキテクチャ、主要コンポーネント、およびそれらが連携する仕組みを確認しました。また、クラスター networking、storage、スケーラビリティ、セキュリティ、アップグレードなどの重要な側面に加え、Amazon EKS クラスターのアーキテクチャも扱いました。

Kubernetes クラスターアーキテクチャを理解することは、効果的なクラスター設計、デプロイ、運用の基盤です。この知識により、安定性、スケーラビリティ、セキュリティを強化した Kubernetes 環境を構築できます。

## クイズ

この章で学んだ内容をテストするには、[クラスターアーキテクチャ クイズ](../quizzes/core/01-cluster-architecture-quiz.md) に挑戦してください。

## 参考資料

- [Kubernetes 公式ドキュメント](https://kubernetes.io/docs/)
- [Amazon EKS ドキュメント](https://docs.aws.amazon.com/eks/)
- [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
- [Kubernetes Patterns](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)
- [Kubernetes Up & Running](https://www.oreilly.com/library/view/kubernetes-up-and/9781492046523/)
- [Kubernetes Best Practices](https://www.oreilly.com/library/view/kubernetes-best-practices/9781492056461/)
