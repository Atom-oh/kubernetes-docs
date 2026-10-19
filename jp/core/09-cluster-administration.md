# Kubernetes クラスター管理

> **サポート対象バージョン**: Kubernetes 1.34–1.37 向けの EKS 標準サポート（2026 年 10 月 12 日確認）
> **最終更新**: 2026年10月16日

Kubernetes クラスター管理は、クラスターのセットアップ、保守、監視、トラブルシューティング、アップグレードを含む重要な作業です。この章では、Kubernetes クラスター管理のさまざまな側面と、Amazon EKS におけるクラスター管理のベストプラクティスを説明します。

セルフマネージドの kubeadm 操作と EKS サービス操作は別物です。EKS は control plane ホスト、static Pod manifest、または etcd への直接アクセスを公開しません。以下のブロックは順番に実行する 1 つのスクリプトではなく、別々の例として扱ってください。実際のクラスターのバージョンに対するアップストリームのサポートおよび add-on の互換性を確認してください。

## 基本概念

- **クラスターライフサイクル管理**: クラスター作成から廃止までのプロセス全体
- **Control Plane 管理**: API server、scheduler、controller manager などの中核コンポーネントの管理
- **Node 管理**: worker node の追加、削除、保守
- **リソース割り当て**: CPU、メモリ、ストレージなどのリソース割り当てと制限の設定
- **アップグレード戦略**: ダウンタイムを最小化するクラスターおよびアプリケーションのアップグレード戦略

## 目次
1. [クラスター管理の概要](#cluster-administration-overview)
2. [クラスターコンポーネント管理](#cluster-component-management)
3. [リソース管理](#resource-management)
4. [クラスターのネットワーク](#cluster-networking)
5. [認証および認可管理](#authentication-and-authorization-management)
6. [クラスターのアップグレード](#cluster-upgrades)
7. [バックアップとリカバリ](#backup-and-recovery)
8. [監視とロギング](#monitoring-and-logging)
9. [トラブルシューティング](#troubleshooting)
10. [Amazon EKS クラスター管理](#amazon-eks-cluster-administration)
11. [クラスター管理のベストプラクティス](#cluster-administration-best-practices)
12. [まとめ](#conclusion)

## 環境セットアップ

クラスター管理には以下のツールが必要です。

[公式の kubectl インストールガイド](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)を使用し、kubectl を API server と 1 つのマイナーバージョン以内に保ってください。セルフマネージドクラスターでは、対象マイナーの `pkgs.k8s.io` リポジトリから kubeadm/kubelet をインストールします。古い `1.x.y-00` パッケージ例は廃止されています。インストール前に、設定済みリポジトリから正確なパッケージバージョンを選択してください。

[公式 Helm 手順](https://helm.sh/docs/intro/install/)および[k9s リリース](https://github.com/derailed/k9s/releases)から Helm と k9s をインストールし、プラットフォームアーキテクチャとチェックサムを確認してください。EKS 管理には、認証済み AWS CLI と互換性のある eksctl も必要です。

```bash
kubectl version --client
helm version
k9s version
# Self-managed nodes only, after configuring the target minor repository:
apt-cache madison kubeadm
```


## クラスター管理の概要 {#cluster-administration-overview}

Kubernetes クラスター管理とは、クラスターのライフサイクル全体を管理するプロセスです。これには以下の主要領域が含まれます。

1. **クラスターのセットアップと設定**: クラスター作成、node 追加、ネットワーク設定、ストレージ設定など
2. **運用管理**: リソース監視、パフォーマンス最適化、キャパシティプランニング、トラブルシューティング
3. **セキュリティ管理**: 認証、認可、network policy、security context など
4. **アップグレードとパッチ**: クラスターバージョンのアップグレード、セキュリティパッチの適用
5. **バックアップとリカバリ**: クラスターデータのバックアップ、災害復旧計画

次の図は、Kubernetes クラスター管理の主な領域と関連ツールを示しています。

## クラスターコンポーネント管理 {#cluster-component-management}

Kubernetes クラスターは control plane コンポーネントと node コンポーネントで構成されます。各コンポーネントの管理は、クラスターの安定性とパフォーマンスに不可欠です。

### Control Plane コンポーネント管理

![Kubernetes control plane から 5 つのコンポーネント（API server、etcd、scheduler、controller manager、cloud controller manager）へ分岐し、それぞれが認証と認可、データバックアップ、スケジューリングポリシー、controller 状態監視、クラウドリソース管理という担当運用課題と組み合わされているツリー図。](../.gitbook/assets/en-core-09-cluster-administration-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-0.html)

#### API Server 管理

API server は Kubernetes API を公開する control plane の中核コンポーネントです。

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/readyz?verbose'
```

#### etcd 管理

etcd は Kubernetes API の状態を保存する分散 key-value store です。

```bash
# etcd backup
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d).db

# Check etcd status
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health
```

### Node 管理

Node はコンテナ化されたアプリケーションを実行する worker machine です。

```bash
# List nodes
kubectl get nodes

# Check node detailed information
kubectl describe node <node-name>

# Add node label
kubectl label node <node-name> environment=production

# Set node to maintenance mode
kubectl drain <node-name> --ignore-daemonsets

# Return node after maintenance
kubectl uncordon <node-name>
```

### コンポーネント状態の監視

```bash
# Check control plane component status
kubectl get --raw='/readyz?verbose'

# Check system pod status
kubectl get pods -n kube-system

# Check node resource usage
kubectl top nodes
```

![クラスター管理者の 5 つの責任領域と、それぞれを遂行するためのツールの対応を示す図。](../.gitbook/assets/en-core-09-cluster-administration-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-1.html)

### クラスター管理ツール

Kubernetes クラスター管理にはさまざまなツールを使用できます。

1. **kubectl**: Kubernetes クラスターと対話するためのコマンドラインツール
2. **kubeadm**: Kubernetes クラスターを作成・管理するツール
3. **kops**: Kubernetes クラスターを作成、アップグレード、管理するツール
4. **eksctl**: Amazon EKS クラスターを作成・管理するツール
5. **Helm**: Kubernetes アプリケーションのパッケージマネージャー
6. **Headlamp**: Kubernetes web UI。旧 Kubernetes Dashboard プロジェクトはアーカイブ済みです
7. **Prometheus & Grafana**: 監視およびアラートツール
8. **Fluentd & Elasticsearch**: ロギングツール

## クラスターコンポーネント管理

Kubernetes クラスターは複数のコンポーネントで構成され、これらを効果的に管理することが重要です。

### Control Plane コンポーネント

Control plane コンポーネントはクラスター全体の状態を管理します。

1. **kube-apiserver**: Kubernetes API を公開するコンポーネント
2. **etcd**: クラスターデータを保存する key-value store
3. **kube-scheduler**: Pod を node にスケジュールするコンポーネント
4. **kube-controller-manager**: controller を実行するコンポーネント
5. **cloud-controller-manager**: クラウドプロバイダーと連携するコンポーネント

次の図は、Kubernetes control plane コンポーネントとその相互作用を示しています。

![etcd、kube-scheduler、kube-controller-manager、cloud-controller-manager が中央の kube-apiserver と双方向通信し、worker node の kubelet が container runtime を使用しながら API server と双方向通信する一方、kube-proxy は独立して Service/EndpointSlice の状態を監視するアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-2.html)

#### Control Plane コンポーネントの監視

Control plane コンポーネントの状態を監視することは重要です。

```bash
# Check control plane component status
kubectl get --raw='/readyz?verbose'

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -n kube-system etcd-<node-name> -- etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key endpoint health
```

#### Control Plane コンポーネントの設定

以下の manifest は flag/設定の断片にすぎません。host networking、certificate mount、その他の kubeadm 生成設定は省略されています。実行中の control plane manifest をこの断片で置き換えないでください。image はクラスターのアップグレード計画に合わせてください。

Control plane コンポーネント設定の管理方法:

```yaml
# kube-apiserver configuration example
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - command:
    - kube-apiserver
    - --advertise-address=192.168.1.10
    - --allow-privileged=true
    - --authorization-mode=Node,RBAC
    - --client-ca-file=/etc/kubernetes/pki/ca.crt
    - --enable-admission-plugins=NodeRestriction
    - --enable-bootstrap-token-auth=true
    - --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
    - --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt
    - --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key
    - --etcd-servers=https://127.0.0.1:2379
    - --kubelet-client-certificate=/etc/kubernetes/pki/apiserver-kubelet-client.crt
    - --kubelet-client-key=/etc/kubernetes/pki/apiserver-kubelet-client.key
    - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
    - --secure-port=6443
    - --service-account-key-file=/etc/kubernetes/pki/sa.pub
    - --service-account-signing-key-file=/etc/kubernetes/pki/sa.key
    - --service-account-issuer=https://kubernetes.default.svc.cluster.local
    - --service-cluster-ip-range=10.96.0.0/12
    - --tls-cert-file=/etc/kubernetes/pki/apiserver.crt
    - --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
    image: registry.k8s.io/kube-apiserver:v1.36.5
    name: kube-apiserver
```

### Node コンポーネント

Node コンポーネントは各 node で実行され、Pod を管理します。

1. **kubelet**: 各 node で実行され、Pod と container の稼働を確保する agent
2. **kube-proxy**: network rule を維持し、接続転送を処理します
3. **Container Runtime**: container を実行するソフトウェア（containerd、CRI-O、または外部 CRI adapter を使用する Docker Engine）

#### Node 管理

Node 管理の主要コマンド:

```bash
# List nodes
kubectl get nodes

# Check node detailed information
kubectl describe node <node-name>

# Add node label
kubectl label node <node-name> key=value

# Add node taint
kubectl taint node <node-name> key=value:NoSchedule

# Set node to maintenance mode
kubectl cordon <node-name>

# Drain node
kubectl drain <node-name> --ignore-daemonsets
```

Drain は standalone Pod、PDB、または local data により停止する場合があります。デフォルトで `--force` や `--delete-emptydir-data` を追加するのではなく調査してください。後者は emptyDir データの損失を明示的に許可します。保守前に drain と workload の健全性を待機してください。

#### Node のトラブルシューティング

Node のトラブルシューティング用コマンド:

```bash
# Check node status
kubectl describe node <node-name> | grep Conditions -A 10

# Check node resource usage
kubectl top node <node-name>

# Check kubelet logs
journalctl -u kubelet

# Check container runtime status
systemctl status docker  # When using Docker
systemctl status containerd  # When using containerd
```

## リソース管理 {#resource-management}

Kubernetes クラスターのリソースを効果的に管理することは、クラスターの安定性とパフォーマンスの維持に重要です。

### Namespace 管理

ライフサイクル操作の練習には使い捨ての namespace を使用してください。namespace を削除すると、その namespace 内のリソースが削除されます。必要なデータを先に確認してバックアップしてください。`get all` は workload のサブセットにすぎません。

```bash
kubectl create namespace admin-demo
kubectl get all -n admin-demo
# Cleanup only the disposable exercise namespace:
kubectl delete namespace admin-demo
```

### ResourceQuota

ResourceQuota は namespace ごとのリソース使用量を制限します。

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-resources
  namespace: dev
spec:
  hard:
    requests.cpu: "1"
    requests.memory: 1Gi
    limits.cpu: "2"
    limits.memory: 2Gi
    pods: "10"
```

上の例では、`dev` namespace は最大 10 個の Pod、1 CPU と 1Gi メモリの request、2 CPU と 2Gi メモリの limit を持つことができます。

### LimitRange

LimitRange は namespace 内の個々のリソースに対するデフォルト値と制限を設定します。

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: limit-range
  namespace: dev
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 200m
      memory: 256Mi
    max:
      cpu: 1
      memory: 1Gi
    min:
      cpu: 100m
      memory: 128Mi
    type: Container
```

上の例では、`dev` namespace のすべての container は、500m CPU と 512Mi メモリのデフォルト limit、200m CPU と 256Mi メモリのデフォルト request、1 CPU と 1Gi メモリの最大値、100m CPU と 128Mi メモリの最小値を持ちます。

### Horizontal Pod Autoscaler (HPA)

HPA は CPU 使用率または custom metric に基づいて Pod の数を自動調整します。

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
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

上の例では、`frontend` Deployment は request された CPU の平均 CPU 使用率 80% を目標とします。tolerance、欠損 metric、安定化 window、および scaling policy の影響を受けます。最小 2、最大 10 の replica を維持します。

### Vertical Pod Autoscaler (VPA)

VPA は Pod の CPU およびメモリ request を自動調整します。

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: frontend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  updatePolicy:
    updateMode: "Recreate"
```

上の例では、`frontend` Deployment の Pod は実際のリソース使用量に基づいて CPU とメモリの request が自動調整されます。
## クラスターのネットワーク {#cluster-networking}

Kubernetes クラスターのネットワークは、Pod、Service、Node 間の通信を管理します。

### クラスターネットワークモデル

Kubernetes ネットワークモデルの基本要件:

1. すべての Pod は NAT なしで他のすべての Pod と通信できる
2. Node agent（kubelet）はその node 上のすべての Pod と通信できる
3. 外部接続は routing と egress policy に依存し、普遍的な Pod NAT モード要件はない

次の図は、Kubernetes のネットワークコンポーネントと通信フローを示しています。

![client traffic が Ingress 経由で Service に入り、別々の node 上の 2 つの Pod に負荷分散され、それらが相互通信し外部 service に到達するアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-3.html)

### CNI (Container Network Interface) Plugin

Kubernetes は CNI plugin を通じてネットワークを実装します。一般的な CNI plugin:

1. **Calico**: 拡張された network policy およびセキュリティ機能を備えた CNI
2. **Flannel**: シンプルな overlay networking を提供
3. **Cilium**: eBPF ベースのネットワークおよびセキュリティソリューション
4. **AWS VPC CNI**: AWS VPC と統合された CNI
5. **Weave Net (historical)**: アーカイブ済み。新規インストールには保守されている代替手段を選択してください

#### CNI Plugin のインストールと設定

CNI plugin のインストール例（Calico）:

1 つの CNI または文書化された chaining/migration 構成を選択してください。Calico、Flannel、Cilium の代替手段を同じ稼働中のクラスターに順番にインストールしてはいけません。サポートされる固定バージョンのリリースとプロバイダー固有の手順を使用してください。EKS では[ネットワークの章](./03-services-networking.md)にある VPC CNI または計画された代替 CNI の手順に従ってください。

```bash
# Inspect the installed networking components before making changes
kubectl get daemonsets -A
kubectl get pods -A -l k8s-app=calico-node
```


### Service ネットワーク

Kubernetes Service は Pod セットに安定した endpoint を提供します。

1. **ClusterIP**: クラスター内からのみアクセスできる Service
2. **NodePort**: すべての node の特定 port 経由でアクセスできる Service
3. **LoadBalancer**: 外部 load balancer 経由でアクセスできる Service
4. **ExternalName**: 外部 service 用の CNAME record を提供

#### Service CIDR 設定

Service CIDR は Service IP address 範囲を定義します。

```bash
# Set service CIDR in kube-apiserver configuration
--service-cluster-ip-range=10.96.0.0/12
```

### CoreDNS 管理

CoreDNS は Kubernetes の DNS service を提供します。

```bash
# Check CoreDNS status
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS configuration
kubectl get configmap -n kube-system coredns -o yaml
```

CoreDNS 設定例:

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
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

### NetworkPolicy

NetworkPolicy は Pod 間の通信を制御します。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: default
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

上の例では、`role=db` label を持つ Pod は、`role=frontend` label を持つ Pod からの TCP port 3306 の受信トラフィック、および `role=monitoring` label を持つ Pod への TCP port 9090 の送信トラフィックのみを許可します。

## 認証および認可管理 {#authentication-and-authorization-management}

Kubernetes の認証および認可管理は、クラスターセキュリティの中核要素です。

次の図は、Kubernetes の認証および認可フローを示しています。

![request が API server 内の認証、認可、admission control を通過し、各段階でサポートされる具体的な認証方法と認可 mode を示すアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-4.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-4.html)

### 認証

Kubernetes はさまざまな認証方法をサポートします。

1. **X.509 Certificates**: client certificate を使用した認証
2. **Service Account Tokens**: service account に関連付けられた JWT token
3. **OpenID Connect (OIDC)**: 外部 identity provider 経由の認証
4. **Webhook Token Authentication**: 外部 service 経由の token 検証
5. **Authentication Proxy**: authentication proxy 経由の request 処理

#### X.509 Certificate 管理

X.509 certificate の作成と管理:

```bash
# Generate a protected private key and CSR
umask 077
openssl genrsa -out user.key 2048
openssl req -new -key user.key -out user.csr -subj "/CN=user/O=group"

# Submit CSR to Kubernetes
cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: user-csr
spec:
  request: $(cat user.csr | base64 | tr -d '\n')
  signerName: kubernetes.io/kube-apiserver-client
  usages:
  - client auth
EOF

# Approve CSR
kubectl certificate approve user-csr
kubectl wait --for=jsonpath='{.status.certificate}' csr/user-csr --timeout=60s

# Get certificate
kubectl get csr user-csr -o jsonpath='{.status.certificate}' | base64 --decode > user.crt
```

#### OIDC 認証設定

OIDC 認証設定例:

```bash
# Add OIDC flags to kube-apiserver configuration
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### 認可

Kubernetes はさまざまな認可 mode をサポートします。

1. **RBAC (Role-Based Access Control)**: role ベースの access control
2. **ABAC (Attribute-Based Access Control)**: attribute ベースの access control
3. **Node**: node 認可
4. **Webhook**: 外部 service 経由の認可

#### RBAC 設定

RBAC は最も一般的な認可メカニズムです。

```yaml
# Role example
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]

# RoleBinding example
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

上の例では、`user` は `default` namespace の Pod を閲覧する権限を持ちます。

#### ClusterRole と ClusterRoleBinding

クラスター全体のリソースに対する権限を管理します。

```yaml
# ClusterRole example
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-reader
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "watch", "list"]

# ClusterRoleBinding example
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-nodes
subjects:
- kind: User
  name: user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: node-reader
  apiGroup: rbac.authorization.k8s.io
```

上の例では、`user` はクラスター内のすべての node を閲覧する権限を持ちます。

### Service Account 管理

Service account は Pod が API server と通信するために使用されます。

```yaml
# Create service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default

# Grant permissions to service account
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: my-service-account-binding
  namespace: default
subjects:
- kind: ServiceAccount
  name: my-service-account
  namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io

# Use service account in pod
---
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: my-service-account
  containers:
  - name: my-container
    image: nginx
```

### Security Context

Security context は Pod と container の権限および access control を定義します。

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
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: security-context-container
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

上の例では、Pod は UID 1000 および GID 3000 で実行され、container は権限昇格できず、すべての Linux capability が削除され、root filesystem は読み取り専用で mount されます。

## クラスターのアップグレード {#cluster-upgrades}

Kubernetes クラスターのアップグレードは、新機能、パフォーマンス向上、セキュリティパッチを適用するために必要です。

次の図は、Kubernetes クラスターのアップグレードプロセスを示しています。

![Kubernetes クラスターアップグレードのワークフロー図。計画とバージョン互換性確認、etcd バックアップ、最初の control plane node のアップグレードと機能テスト、残りの control plane および worker node のアップグレード、クラスター検証を経てアップグレード完了に至り、検証で問題が見つかった場合はバックアップから復元するロールバック経路があります。](../.gitbook/assets/en-core-09-cluster-administration-5.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-5.html)

### アップグレード計画

クラスターアップグレードを計画する際の考慮事項:

1. **バージョン互換性**: Kubernetes バージョン間の互換性を確認
2. **アップグレードパス**: サポートされるアップグレードパスを確認
3. **ダウンタイム**: アップグレード中に予想されるダウンタイムを計画
4. **ロールバック計画**: 問題発生時に備えたロールバック計画を策定
5. **アプリケーションへの影響**: アプリケーションに対するアップグレードの影響を評価

### Control Plane のアップグレード

kubeadm を使用する control plane のアップグレード:

[バージョン固有の kubeadm アップグレード手順](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)を使用してください。対象マイナーの pkgs.k8s.io リポジトリを有効にして、公開済みの正確なパッケージバージョンを選択します。一度にアップグレードするのは 1 つのマイナーバージョンだけです。

1. etcd をバックアップし、workload/add-on の互換性を検証します。最初の control plane node で kubeadm をアップグレードし、`kubeadm upgrade plan` を実行してから `kubeadm upgrade apply <target-version>` を実行します。
2. 追加の control plane node では、kubeadm をアップグレードして `kubeadm upgrade node` を実行します。
3. kubelet をアップグレードする前に各 node を drain します。drain が失敗した場合は手順を停止し、原因を解決してください。kubelet/kubectl を互換バージョンにアップグレードし、systemd を reload、kubelet を再起動して Ready と workload を検証し、その後、管理 client から uncordon します。
4. 各 worker で kubeadm をアップグレードして `kubeadm upgrade node` を実行し、続いて drain/kubelet/検証/uncordon の順序を実行します。Kubernetes のバージョン固有手順の代わりに、汎用的なシステム全体のアップグレードを実行しないでください。

コマンドは明示的に特定した node または管理 client で実行してください。入れ子になった `ssh` session の連続はマルチ node 自動化スクリプトではありません。

### Worker Node のアップグレード

Worker node のアップグレードプロセス:

[バージョン固有の kubeadm アップグレード手順](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)を使用してください。対象マイナーの pkgs.k8s.io リポジトリを有効にして、公開済みの正確なパッケージバージョンを選択します。一度にアップグレードするのは 1 つのマイナーバージョンだけです。

1. etcd をバックアップし、workload/add-on の互換性を検証します。最初の control plane node で kubeadm をアップグレードし、`kubeadm upgrade plan` を実行してから `kubeadm upgrade apply <target-version>` を実行します。
2. 追加の control plane node では、kubeadm をアップグレードして `kubeadm upgrade node` を実行します。
3. kubelet をアップグレードする前に各 node を drain します。drain が失敗した場合は手順を停止し、原因を解決してください。kubelet/kubectl を互換バージョンにアップグレードし、systemd を reload、kubelet を再起動して Ready と workload を検証し、その後、管理 client から uncordon します。
4. 各 worker で kubeadm をアップグレードして `kubeadm upgrade node` を実行し、続いて drain/kubelet/検証/uncordon の順序を実行します。Kubernetes のバージョン固有手順の代わりに、汎用的なシステム全体のアップグレードを実行しないでください。

コマンドは明示的に特定した node または管理 client で実行してください。入れ子になった `ssh` session の連続はマルチ node 自動化スクリプトではありません。

### アップグレードの検証

アップグレード後にクラスター状態を検証します。

```bash
# Check node versions
kubectl get nodes

# Check component status
kubectl get --raw='/readyz?verbose'

# Check pod status
kubectl get pods --all-namespaces

# Test cluster functionality
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80
kubectl get svc nginx
```
## バックアップとリカバリ {#backup-and-recovery}

Kubernetes クラスターのバックアップとリカバリは、災害復旧計画の重要な一部です。

次の図は、Kubernetes クラスターのバックアップとリカバリのプロセスを示しています。

![スケジュールされた etcd snapshot と resource YAML backup の両方が backup storage に保存され、後に災害復旧時の etcd restore と resource restore に供給されることを示すアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-6.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-6.html)

### etcd バックアップ

etcd は Kubernetes クラスターのすべての状態情報を保存するため、定期的なバックアップが重要です。

```bash
# Create etcd snapshot
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db

# Check snapshot status
etcdutl snapshot status --write-out=table /backup/etcd-snapshot-2023-01-01-12-00-00.db
```

### etcd リカバリ

etcd snapshot から復元します。

セルフマネージドの災害復旧では、ディストリビューション固有の runbook を使用して、すべての API server と影響を受けた etcd process を停止してください。kubelet だけを停止しても、既存の static Pod container は稼働したままです。互換性のある etcdutl で新しい directory に復元し、リカバリが検証されるまで元データを保持してください。この single-member コマンドは、multi-member HA 復元ではなく説明用です。

```bash
etcdutl snapshot status "$SNAPSHOT_FILE" --write-out=table
etcdutl snapshot restore "$SNAPSHOT_FILE" \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

SNAPSHOT_FILE には検証済みの snapshot を設定してください。HA では、各 member の固有の name/peer URL と同じ完全な membership list を使用して、すべての member で同じ snapshot を復元します。snapshot 以降の変更を超える revision bump を選択してください。適切な所有権と certificate で復元先 path を指すように etcd manifest/service を更新し、quorum/health を検証してから API server/controller を再起動します。[公式リカバリガイド](https://etcd.io/docs/v3.6/op-guide/recovery/)を参照してください。EKS ユーザーは管理された control plane etcd を直接復元できません。

### リソースバックアップ

これらの export は保護対象の inventory であり、完全で移植可能な restore 計画ではありません。Secret を含むため、制限された権限と暗号化が必要です。また PV data は含まれません。`umask 077` を使用し、各コマンドの失敗を確認してください。CRD/dependency は順序どおりに復元し、必要に応じて server 所有の metadata を削除します。`kubectl get all` が返す resource kind はサブセットだけです。

Kubernetes resource を YAML file としてバックアップします。

```bash
# Export listable resources (includes sensitive Secrets)
set -eu
umask 077
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  mkdir -p /backup/resources/$ns
  for resource in $(kubectl api-resources --verbs=list --namespaced=true -o name); do
    kubectl get -n "$ns" "$resource" -o yaml > "/backup/resources/$ns/$resource.yaml"
  done
done

# Backup cluster-scoped resources
mkdir -p /backup/resources/cluster-scoped
for resource in $(kubectl api-resources --verbs=list --namespaced=false -o name); do
  kubectl get "$resource" -o yaml > "/backup/resources/cluster-scoped/$resource.yaml"
done
```

### バックアップの自動化

セルフマネージド kubeadm の例のみ: ツール image は互換性のある etcdctl を含む検証済み image に置き換え、control plane の label/taint と certificate path を一致させ、backup PVC を作成してください。選択した host は、表示された loopback address で etcd を公開し、PVC mount を許可する必要があります。これは管理された EKS control plane では実行されません。snapshot を検証して保護された外部 storage にコピーしてください。クラスター内 PVC だけでは災害復旧になりません。

CronJob でバックアップタスクを自動化します。

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  concurrencyPolicy: Forbid
  schedule: "0 0 * * *"  # Run daily at midnight
  jobTemplate:
    spec:
      template:
        spec:
          hostNetwork: true
          automountServiceAccountToken: false
          nodeSelector:
            node-role.kubernetes.io/control-plane: ""
          tolerations:
          - key: node-role.kubernetes.io/control-plane
            operator: Exists
            effect: NoSchedule
          containers:
          - name: etcd-backup
            image: example.invalid/etcd-backup-tools:replace-me
            command:
            - /bin/sh
            - -c
            - |
              set -eu
              umask 077
              ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
                --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
                snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db
            volumeMounts:
            - name: etcd-ca
              mountPath: /etc/kubernetes/pki/etcd/ca.crt
              readOnly: true
            - name: etcd-client-cert
              mountPath: /etc/kubernetes/pki/etcd/healthcheck-client.crt
              readOnly: true
            - name: etcd-client-key
              mountPath: /etc/kubernetes/pki/etcd/healthcheck-client.key
              readOnly: true
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: etcd-ca
            hostPath:
              path: /etc/kubernetes/pki/etcd/ca.crt
              type: File
          - name: etcd-client-cert
            hostPath:
              path: /etc/kubernetes/pki/etcd/healthcheck-client.crt
              type: File
          - name: etcd-client-key
            hostPath:
              path: /etc/kubernetes/pki/etcd/healthcheck-client.key
              type: File
          - name: backup
            persistentVolumeClaim:
              claimName: etcd-backup-pvc
```

## 監視とロギング {#monitoring-and-logging}

効果的な監視とロギングはクラスター管理の中核要素です。

次の図は、Kubernetes クラスターの監視およびロギングアーキテクチャを示しています。

![API server と node metric が kube-state-metrics および Node Exporter を経由して Prometheus に流れ、その後 Alertmanager と Grafana に流れる一方、Pod log が Fluentd/Fluent Bit を経由して Elasticsearch（Kibana を伴う）と Loki に流れ、Loki も Grafana に供給するアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-7.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-7.html)

### 監視ツール

Kubernetes クラスター監視用ツール:

1. **Prometheus**: metric の収集と保存
2. **Grafana**: metric の可視化
3. **Alertmanager**: alert 管理
4. **kube-state-metrics**: Kubernetes object metric の生成
5. **metrics-server**: リソース使用量 metric の提供

#### Prometheus と Grafana のインストール

Helm を使用して Prometheus と Grafana をインストールします。

```bash
# Add Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

#### 主要な監視 metric

監視すべき主要 metric:

1. **Node Metrics**: CPU、メモリ、disk、network 使用量
2. **Pod Metrics**: CPU、メモリ使用量、restart 回数
3. **Container Metrics**: CPU、メモリ使用量、filesystem 使用量
4. **API Server Metrics**: request latency、request count、error rate
5. **etcd Metrics**: disk I/O、leader 変更、commit latency

### ロギングツール

Kubernetes クラスターのロギング用ツール:

1. **Elasticsearch**: log の保存と検索
2. **Fluentd/Fluent Bit**: log の収集と転送
3. **Kibana**: log の可視化
4. **Loki**: log aggregation system
5. **Grafana**: log の可視化

#### EFK（Elasticsearch、Fluentd、Kibana）Stack のインストール

スタンドアロンの Elastic Stack Helm-chart リポジトリはアーカイブ済みです。保守対象の deployment には Elastic Cloud on Kubernetes（ECK）を使用し、Elasticsearch/Kibana resource と互換性のある log collector を定義してください。operator のインストールだけでは EFK stack は作成されません。

```bash
helm repo add elastic https://helm.elastic.co
helm upgrade --install elastic-operator elastic/eck-operator \
  --namespace elastic-system --create-namespace \
  --version "${ECK_CHART_VERSION:?Select a supported ECK chart version}"
```

Dashboard は ClusterIP/認証済みアクセスの背後に置き、[ECK guide](https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s/install-using-helm-chart)に従って storage、TLS、credential、collector parsing、RBAC を設定してください。

#### Log 収集の設定

この例は Docker JSON を前提にせず、CRI log envelope を parse します。collector image には metadata/output plugin が含まれている必要があり、node log と書き込み可能な position-file storage を mount し、スコープを限定した metadata RBAC を受け取る必要があります。実際の Elasticsearch service に対して TLS/認証を設定してください。placeholder host だけでは完全な ECK 統合にはなりません。選択した collector に従って partial/multiline record を処理してください。

Fluentd 設定例:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: logging
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      read_from_head true
      <parse>
        @type regexp
        expression /^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<log>.*)$/
        time_type string
        time_format %Y-%m-%dT%H:%M:%S.%N%:z
      </parse>
    </source>

    <filter kubernetes.**>
      @type kubernetes_metadata
      kubernetes_url https://kubernetes.default.svc
      bearer_token_file /var/run/secrets/kubernetes.io/serviceaccount/token
      ca_file /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    </filter>

    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch-master
      port 9200
      logstash_format true
      logstash_prefix k8s
    </match>
```

## トラブルシューティング {#troubleshooting}

Kubernetes クラスターのトラブルシューティングは、クラスター管理の重要な一部です。

### Pod のトラブルシューティング

Pod のトラブルシューティング用コマンド:

```bash
# Check pod status
kubectl get pod <pod-name> -o wide

# Check pod detailed information
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs <pod-name>
kubectl logs <pod-name> -c <container-name>  # For multi-container pods
kubectl logs <pod-name> --previous  # Logs from previous container

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/sh
```

### Node のトラブルシューティング

Node のトラブルシューティング用コマンド:

```bash
# Check node status
kubectl get node <node-name> -o wide

# Check node detailed information
kubectl describe node <node-name>

# Check node resource usage
kubectl top node <node-name>

# SSH to node
ssh <node-name>

# Check node system logs
journalctl -u kubelet

# Check node resource usage
top
df -h
free -m
```

### ネットワークのトラブルシューティング

ネットワークのトラブルシューティング用コマンド:

```bash
# Check service status
kubectl get svc <service-name>

# Check service detailed information
kubectl describe svc <service-name>

# Check endpoints
kubectl get endpointslices -l kubernetes.io/service-name=<service-name>

# Check DNS
kubectl run -it --rm --restart=Never busybox --image=busybox -- nslookup <service-name>

# Test network connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- <service-name>:<port>

# Check network policies
kubectl get networkpolicy
kubectl describe networkpolicy <policy-name>
```

### Control Plane のトラブルシューティング

Control plane のトラブルシューティング用コマンド:

```bash
# Check component status
kubectl get --raw='/readyz?verbose'

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check controller manager logs
kubectl logs -n kube-system kube-controller-manager-<node-name>

# Check scheduler logs
kubectl logs -n kube-system kube-scheduler-<node-name>

# Check etcd logs
kubectl logs -n kube-system etcd-<node-name>
```

## Amazon EKS クラスター管理 {#amazon-eks-cluster-administration}

Amazon EKS は、クラスター管理の多くの側面を自動化するマネージド Kubernetes service です。

次の図は、Amazon EKS クラスターアーキテクチャと管理コンポーネントを示しています。

![ユーザーが AWS console、CLI、または API を通じて Amazon EKS を管理し、EKS が control plane、managed node group、Fargate を実行し、control plane が AWS IAM、VPC、CloudWatch を使用し、VPC CNI、CoreDNS、kube-proxy add-on を含むことを示すアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-8.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-8.html)

### EKS クラスター設定

endpoint access を変更する前に実際の管理者 CIDR を設定し、private access が到達可能なままであることを検証してください。バージョンアップグレードは、互換性のある add-on/node を備えた次にサポートされるマイナーバージョンでなければなりません。例を downgrade やマイナー version のスキップに使用しないでください。返された update ID を poll し、失敗した場合は依存する変更を停止してください。

EKS クラスター設定の管理:

```bash
# Check EKS cluster information
aws eks describe-cluster --name my-cluster

# Update EKS cluster
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${ADMIN_CIDR:?Set an approved administrator public CIDR}"

# Update EKS cluster version
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version "${TARGET_VERSION:?Select the next EKS-supported minor version}"
```

### EKS Node Group 管理

EKS node group 管理:

```bash
# Check node group information
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup

# Scale node group
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --scaling-config minSize=2,maxSize=10,desiredSize=5

# Update node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### EKS Add-on 管理

現在のバージョンを `aws eks describe-cluster --name my-cluster --query cluster.version --output text` で読み取り、add-on の検出に使用して互換性のある固定バージョンを選択してください。create/update の前に既存の設定/IAM を確認し、すでに管理されている add-on を再度 create しないでください。削除例では `--preserve` を使用して、EKS 管理を削除しても CNI が実行され続けるようにしています。稼働中のネットワークを uninstall することは別の、影響の大きい操作です。

EKS add-on 管理:

```bash
# Check available add-ons
aws eks describe-addon-versions --addon-name vpc-cni \
  --kubernetes-version "${CLUSTER_VERSION:?Set the actual cluster version}"

# Install add-on
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version "${CNI_ADDON_VERSION:?Select a compatible pinned VPC CNI add-on version}"

# Update add-on
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version "${CNI_ADDON_VERSION:?Select a compatible pinned VPC CNI add-on version}"

# Delete add-on
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni --preserve
```

### EKS クラスターのアップグレード

EKS クラスターのアップグレードプロセス:

1. **Control Plane のアップグレード**:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version "${TARGET_VERSION:?Select the next EKS-supported minor version}"
   ```

2. **Add-on のアップグレード**:
   ```bash
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version "${CNI_ADDON_VERSION:?Select a compatible pinned VPC CNI add-on version}"
   ```

3. **Node Group のアップグレード**:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

### EKS クラスターの監視

Control plane logging は api/audit/authenticator/controllerManager/scheduler log を export します。Container Insights には CloudWatch agent/add-on とスコープを限定した telemetry IAM 権限が必要です。update-cluster-logging では有効になりません。CloudWatch observability add-on は CloudWatch/Fluent Bit コンポーネントをインストールし、Prometheus/Grafana はインストールしません。[公式 add-on セットアップ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)を参照してください。

EKS クラスター監視ツール:

1. **Amazon CloudWatch**: metric、log、alert
2. **AWS CloudTrail**: API call logging
3. **Amazon Managed Grafana**: metric の可視化
4. **Amazon Managed Service for Prometheus**: metric の収集と保存

EKS control plane logging を有効化します。

```bash
# Enable EKS control-plane logs
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## クラスター管理のベストプラクティス {#cluster-administration-best-practices}

Kubernetes と EKS クラスター管理のベストプラクティス:

### クラスター設定のベストプラクティス

1. **Infrastructure as Code (IaC)**: Terraform、AWS CDK、eksctl などを使用してクラスター設定を管理
2. **Version Control**: クラスター設定を version control system に保存
3. **複数環境**: 開発、staging、本番環境を分離
4. **ネットワーク分離**: 適切なネットワーク分離と security group を設定
5. **最小権限の原則**: 必要最小限の権限のみを付与

### 運用のベストプラクティス

1. **定期的なバックアップ**: etcd と重要な resource を定期的にバックアップ
2. **監視とアラート**: 包括的な監視およびアラート system を構築
3. **集中ロギング**: log を集約して分析
4. **自動化**: 反復作業を自動化
5. **災害復旧計画**: 明確な災害復旧計画を策定・テスト

### セキュリティのベストプラクティス

1. **定期的な更新**: クラスターと node を定期的に更新
2. **NetworkPolicy**: 適切な network policy を設定
3. **暗号化**: 保存中および転送中のデータを暗号化
4. **Security Context**: 適切な security context を設定
5. **Image Scanning**: container image の脆弱性を scan

### リソース管理のベストプラクティス

1. **Resource Request と Limit**: すべての Pod に適切な resource request と limit を設定
2. **Namespace 分離**: workload を namespace ごとに分離
3. **ResourceQuota**: namespace ごとに resource quota を設定
4. **HPA と VPA**: autoscaling を設定
5. **Node Affinity と Taint**: workload の配置を最適化

### EKS 固有のベストプラクティス

1. **Managed Node Group**: 可能な場合は managed node group を使用
2. **Fargate**: serverless workload に Fargate を使用
3. **EKS Add-on**: 公式 EKS add-on を使用
4. **IAM Roles for Service Accounts (IRSA)**: Pod ごとに IAM 権限を管理
5. **VPC CNI Customization**: ネットワーク要件に応じて VPC CNI を設定

## まとめ {#conclusion}

Kubernetes クラスター管理は、クラスターの安定性、セキュリティ、パフォーマンスを維持する上で重要な役割を担います。この章では、クラスターコンポーネント管理、リソース管理、ネットワーク、認証および認可管理、アップグレード、バックアップとリカバリ、監視とロギング、トラブルシューティングを含む、クラスター管理のさまざまな側面を取り上げました。

Amazon EKS を使用すると、Kubernetes control plane 管理の複雑さが軽減され、AWS service との統合によりクラスター管理が簡素化されます。ただし、効果的なクラスター管理には、Kubernetes の基本概念とベストプラクティスを理解することが引き続き重要です。

クラスター管理は、クラスター要件と workload 特性に応じて継続的に調整すべき進行中のプロセスです。監視ツールを使用してクラスター状態を追跡し、自動化によって反復作業を最小化し、ベストプラクティスに従ってクラスターの安定性とセキュリティを維持することが重要です。

## クラスターのネットワーク

Kubernetes クラスターのネットワークは、Pod 間通信、service discovery、外部アクセスを管理します。

### ネットワークアーキテクチャ

![クラスターのネットワークが Pod network、Service network、Ingress、network policy に分割され、それぞれ CNI plugin、Service type（ClusterIP、NodePort、LoadBalancer）、ingress controller、network security によって実装されることを示すアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-9.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-9.html)

### CNI Plugin 管理

CNI（Container Network Interface）plugin は Kubernetes クラスターのネットワークを処理します。

1 つの CNI または文書化された chaining/migration 構成を選択してください。Calico、Flannel、Cilium の代替手段を同じ稼働中のクラスターに順番にインストールしてはいけません。サポートされる固定バージョンのリリースとプロバイダー固有の手順を使用してください。EKS では[ネットワークの章](./03-services-networking.md)にある VPC CNI または計画された代替 CNI の手順に従ってください。

```bash
# Inspect the installed networking components before making changes
kubectl get daemonsets -A
kubectl get pods -A -l k8s-app=calico-node
```


### CNI Plugin の比較

| CNI Plugin | ネットワークモデル | NetworkPolicy サポート | パフォーマンス | 機能 |
|-----------|---------------|----------------------|-------------|----------|
| **Calico** | BGP | はい | 高 | network policy に強い、routing ベース |
| **Flannel** | VXLAN/host-gateway | いいえ | 中 | セットアップが簡単、機能は限定的 |
| **Cilium** | eBPF | はい | 非常に高 | L3-L7 policy、高パフォーマンス |
| **Weave Net** | VXLAN | はい | 中 | 暗号化サポート、マルチクラスター |
| **AWS VPC CNI** | AWS VPC | サポートされるバージョン/設定でははい | workload に依存 | ネイティブ EKS 統合 |

### ネットワークのトラブルシューティング

```bash
# Test pod network connectivity
kubectl run -it --rm network-test --image=busybox -- sh
# Inside the container
ping <target-ip>
traceroute <target-ip>
wget -O- <service-name>

# DNS troubleshooting
kubectl run -it --rm dns-test --image=busybox -- sh
# Inside the container
nslookup kubernetes.default.svc.cluster.local
cat /etc/resolv.conf

# Check service endpoints
kubectl get endpointslices -l kubernetes.io/service-name=<service-name>

# Check network policies
kubectl describe networkpolicy -n <namespace>
```
## 認証および認可管理

Kubernetes の認証および認可管理は、クラスターセキュリティの中核要素です。RBAC（Role-Based Access Control）は user と service account の権限管理に使用されます。

### 認証方法

Kubernetes はさまざまな認証方法をサポートします。

1. **X.509 Certificates**: client certificate を使用した認証
2. **Service Account Tokens**: Pod 内からの API server access に使用
3. **OpenID Connect (OIDC)**: 外部 identity provider との統合
4. **Webhook Token Authentication**: 外部 authentication service との統合
5. **Authentication Proxy**: proxy 経由の認証

### RBAC 設定

```yaml
# role.yaml - namespace-scoped role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

```yaml
# rolebinding.yaml - binding role to user
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

```yaml
# clusterrole.yaml - cluster-scoped role
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: namespace-reader
rules:
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "watch", "list"]
```

```yaml
# clusterrolebinding.yaml - binding cluster role to user
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-namespaces-global
subjects:
- kind: Group
  name: namespace-viewers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: namespace-reader
  apiGroup: rbac.authorization.k8s.io
```

### User Certificate の作成

セルフマネージドの client-certificate 認証では、CSR を送信し、権限のある approver が要求された identity/group を検証する必要があります。クラスター CA private key を配布しないでください。EKS の user access には IAM/access entry を使用してください。

```bash
umask 077
openssl genrsa -out jane.key 2048
openssl req -new -key jane.key -out jane.csr -subj "/CN=jane/O=dev"
cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: jane-csr
spec:
  request: $(base64 < jane.csr | tr -d '\n')
  signerName: kubernetes.io/kube-apiserver-client
  expirationSeconds: 86400
  usages:
  - client auth
EOF
# Authorized approver only, after reviewing the CSR identity:
kubectl certificate approve jane-csr
kubectl wait --for=jsonpath='{.status.certificate}' csr/jane-csr --timeout=60s
kubectl get csr jane-csr -o jsonpath='{.status.certificate}' | base64 --decode > jane.crt
kubectl config set-credentials jane --client-certificate=jane.crt --client-key=jane.key
kubectl config set-context jane-context --cluster=kubernetes --user=jane
```

### Service Account 管理

```bash
# Create service account
kubectl create serviceaccount app-service-account

# Bind role to service account
kubectl create rolebinding app-service-account-binding \
  --role=pod-reader \
  --serviceaccount=default:app-service-account

# Inspect ServiceAccount metadata (projected tokens are not listed here)
kubectl describe serviceaccount app-service-account
```

### 権限の検証

```bash
# Check user permissions
kubectl auth can-i get pods --as jane

# Check permissions in a specific namespace
kubectl auth can-i create deployments --as jane --namespace production
```
## クラスターのアップグレード

Kubernetes クラスターのアップグレードは、新機能、セキュリティパッチ、bug fix を適用するために必要です。アップグレードは慎重に計画・実行する必要があります。

### アップグレード計画

![アップグレード計画を、バージョン互換性確認、バックアップ作成、アップグレード戦略の選択、ダウンタイムの計画という 4 つの作業に分け、それぞれ API 変更の確認、etcd バックアップ、in-place と blue/green の比較、ユーザーとのコミュニケーションという具体的なアクションにつながることを示すツリー図。](../.gitbook/assets/en-core-09-cluster-administration-10.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-10.html)

### アップグレード戦略の比較

| 戦略 | 説明 | 利点 | 欠点 | 適した環境 |
|----------|-------------|------------|---------------|---------------------|
| **In-place Upgrade** | 既存クラスターを直接アップグレード | リソース効率が高い、手順が簡単 | ロールバックが複雑、ダウンタイムの可能性 | 開発、テスト環境 |
| **Blue/Green Deployment** | 新バージョンクラスターを作成して切り替え | 安全なロールバック、検証可能 | リソース重複、コスト増加 | 本番環境 |
| **Canary Deployment** | 一部の workload のみ新クラスターに移動 | 段階的な検証、リスク軽減 | 管理が複雑、二重運用 | 重要な本番環境 |

### kubeadm を使用したアップグレード

[バージョン固有の kubeadm アップグレード手順](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)を使用してください。対象マイナーの pkgs.k8s.io リポジトリを有効にして、公開済みの正確なパッケージバージョンを選択します。一度にアップグレードするのは 1 つのマイナーバージョンだけです。

1. etcd をバックアップし、workload/add-on の互換性を検証します。最初の control-plane node で kubeadm をアップグレードし、`kubeadm upgrade plan` を実行してから `kubeadm upgrade apply <target-version>` を実行します。
2. 追加の control-plane node では、kubeadm をアップグレードして `kubeadm upgrade node` を実行します。
3. kubelet をアップグレードする前に各 node を drain します。drain が失敗した場合は手順を停止し、原因を解決してください。kubelet/kubectl を互換バージョンにアップグレードし、systemd を reload、kubelet を再起動して Ready と workload を検証し、その後、管理 client から uncordon します。
4. 各 worker で kubeadm をアップグレードして `kubeadm upgrade node` を実行し、続いて drain/kubelet/検証/uncordon の順序を実行します。Kubernetes のバージョン固有手順の代わりに、汎用的なシステム全体のアップグレードを実行しないでください。

コマンドは明示的に特定した node または管理 client で実行してください。入れ子になった `ssh` session の連続はマルチ node 自動化スクリプトではありません。

### アップグレード後の検証

```bash
# Check cluster version
kubectl version

# Check node versions
kubectl get nodes

# Check component status
kubectl get --raw='/readyz?verbose'

# Check workload status
kubectl get pods -A
```
## バックアップとリカバリ

Kubernetes クラスターのバックアップとリカバリは、災害復旧計画の重要な一部です。主なバックアップ対象は etcd database、persistent volume data、Kubernetes resource 定義です。

### etcd のバックアップとリカバリ

etcd はクラスターのすべての状態情報を保存する中核コンポーネントです。

セルフマネージドの災害復旧では、ディストリビューション固有の runbook を使用して、すべての API server と影響を受けた etcd process を停止してください。kubelet だけを停止しても、既存の static Pod container は稼働したままです。互換性のある etcdutl で新しい directory に復元し、リカバリが検証されるまで元データを保持してください。この single-member コマンドは、multi-member HA 復元ではなく説明用です。

```bash
etcdutl snapshot status "$SNAPSHOT_FILE" --write-out=table
etcdutl snapshot restore "$SNAPSHOT_FILE" \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

SNAPSHOT_FILE には検証済みの snapshot を設定してください。HA では、各 member の固有の name/peer URL と同じ完全な membership list を使用して、すべての member で同じ snapshot を復元します。snapshot 以降の変更を超える revision bump を選択してください。適切な所有権と certificate で復元先 path を指すように etcd manifest/service を更新し、quorum/health を検証してから API server/controller を再起動します。[公式リカバリガイド](https://etcd.io/docs/v3.6/op-guide/recovery/)を参照してください。EKS ユーザーは管理された control plane etcd を直接復元できません。

### Kubernetes リソースバックアップ

```bash
# Export selected resources, not a full cluster backup
set -eu
umask 077
mkdir -p /backup/resources/$(date +%Y-%m-%d)
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl -n $ns get all -o yaml > /backup/resources/$(date +%Y-%m-%d)/$ns-all.yaml
done

# Backup specific resource types
for resource in deployments services configmaps secrets; do
  kubectl get $resource -A -o yaml > /backup/resources/$(date +%Y-%m-%d)/$resource.yaml
done
```

### Velero を使用したバックアップとリカバリ

公式 matrix を使用して、互換性のある Velero/AWS plugin バージョンを選択してください。IRSA の例では、設定済みのクラスター OIDC provider と、velero ServiceAccount を信頼するスコープを限定した role を前提としています。インストール前に backup bucket、volume snapshot/file-backup サポート、暗号化、restore 権限を設定してください。すべての PVC が自動的に保護されるわけではありません。

Velero は Kubernetes クラスター resource と persistent volume をバックアップおよびリカバリするためのツールです。

```bash
# Install Velero (using AWS S3 backup storage)
velero install \
  --provider aws \
  --plugins "${VELERO_AWS_PLUGIN_IMAGE:?Select a plugin compatible with your Velero release}" \
  --bucket velero-backup \
  --backup-location-config region=us-west-2 \
  --snapshot-location-config region=us-west-2 \
  --no-secret \
  --sa-annotations "eks.amazonaws.com/role-arn=${VELERO_ROLE_ARN:?Set the preconfigured IRSA role ARN}"

# Full cluster backup
velero backup create full-cluster-backup --include-namespaces '*'

# Backup specific namespace
velero backup create production-backup --include-namespaces production

# Check backup status
velero backup describe full-cluster-backup

# Restore from backup
velero restore create --from-backup full-cluster-backup
```

### バックアップ戦略の比較

| バックアップ方法 | バックアップ対象 | 利点 | 欠点 | リカバリ時間 |
|--------------|---------------|------------|---------------|---------------|
| **etcd Snapshot** | クラスター状態 | 組み込み機能、完全な状態保持 | volume data は含まれない、手動プロセス | 中 |
| **Resource YAML Backup** | Kubernetes object | 実装が簡単、選択的 restore | volume data は含まれない、関係性が複雑 | 遅い |
| **Velero** | resource と volume | 自動化、スケジューリング、volume snapshot | 追加ツールのインストールが必要 | 速い |
| **Cloud Provider Snapshots** | サポートされる disk/filesystem | backend ネイティブのリカバリポイント | Kubernetes/EKS クラスター全体は取得しない | data/backend に依存 |
## 監視とロギング

効果的なクラスター管理には、包括的な監視およびロギング system が必要です。これにより問題を早期に検出・解決できます。

### 監視アーキテクチャ

![Kubernetes 監視が metric 収集、log 収集、alert、可視化に分割され、それぞれ Prometheus（kube-state-metrics と node-exporter を伴う）、Elasticsearch と Kibana に log を送る Fluentd/Fluent Bit、Alertmanager、Grafana によって処理されることを示すアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-11.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-11.html)

### Prometheus と Grafana のインストール

```bash
# Install Prometheus and Grafana using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.enabled=true \
  --set prometheus.service.type=ClusterIP

# Check services
kubectl get svc -n monitoring

# Access Grafana (using port forwarding)
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
# Obtain credentials from the configured Grafana Secret; do not assume a published default password
```

### EFK Stack のインストール（Elasticsearch、Fluentd、Kibana）

スタンドアロンの Elastic Stack Helm-chart リポジトリはアーカイブ済みです。保守対象の deployment には Elastic Cloud on Kubernetes（ECK）を使用し、Elasticsearch/Kibana resource と互換性のある log collector を定義してください。operator のインストールだけでは EFK stack は作成されません。

```bash
helm repo add elastic https://helm.elastic.co
helm upgrade --install elastic-operator elastic/eck-operator \
  --namespace elastic-system --create-namespace \
  --version "${ECK_CHART_VERSION:?Select a supported ECK chart version}"
```

Dashboard は ClusterIP/認証済みアクセスの背後に置き、[ECK guide](https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s/install-using-helm-chart)に従って storage、TLS、credential、collector parsing、RBAC を設定してください。

### 主要な監視 metric

| metric type | 説明 | 主要 metric | 監視ツール |
|-------------|-------------|-------------|-----------------|
| **Node Metrics** | node レベルのリソース使用量 | CPU、メモリ、disk、network | node-exporter、Prometheus |
| **Pod Metrics** | container のリソース使用量 | CPU、メモリ使用量、limit | cAdvisor、Prometheus |
| **Cluster Metrics** | クラスター状態と resource | Pod 数、node/object 状態、desired/current replica | kube-state-metrics |
| **Application Metrics** | custom application metric | request count、latency、error rate | Prometheus client library |

### Log の収集と分析

```bash
# Check logs for a specific pod
kubectl logs <pod-name> -n <namespace>

# Check logs from previous instance
kubectl logs <pod-name> -n <namespace> --previous

# Check logs for a specific container (multi-container pod)
kubectl logs <pod-name> -c <container-name> -n <namespace>

# Stream logs
kubectl logs -f <pod-name> -n <namespace>

# Check logs for all pods (using label selector)
kubectl logs -l app=nginx -n <namespace>
```

### Alert 設定

Prometheus Alertmanager を使用して alert を設定できます。

key `url` を持つ保護された `slack-webhook` Secret を monitoring に作成してから、これらの Helm value を既存の kube-prometheus-stack release にマージしてください。webhook URL を commit しないでください。スタンドアロンの ConfigMap は operator により自動的には使用されません。

```yaml
# alertmanager-values.yaml
alertmanager:
  alertmanagerSpec:
    secrets:
    - slack-webhook
  config:
    global:
      resolve_timeout: 5m
      slack_api_url_file: /etc/alertmanager/secrets/slack-webhook/url
    route:
      receiver: slack-notifications
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      group_by: [alertname, cluster, service]
    receivers:
    - name: slack-notifications
      slack_configs:
      - channel: '#alerts'
        send_resolved: true
        title: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

アップグレード時は現在の chart version と他の value を維持してください。通知に依存する前に Alertmanager の reload/status を検証します。
## トラブルシューティング

Kubernetes クラスターのトラブルシューティングは system administrator と operator にとって重要なスキルです。効果的なトラブルシューティングには体系的なアプローチが必要です。

### トラブルシューティングの方法論

![問題の特定から文書化までの 6 段階のトラブルシューティング手順を示し、情報収集段階が log、event、resource status の確認に分岐するワークフロー図。](../.gitbook/assets/en-core-09-cluster-administration-12.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-12.html)

### よくある問題と解決策

| 問題の種類 | 症状 | 診断コマンド | 一般的な解決策 |
|-------------|----------|---------------------|-----------------|
| **Pod が起動しない** | Pod が Pending または ContainerCreating 状態 | `kubectl describe pod <pod-name>` | リソース制約、image の可用性、volume mount を確認 |
| **Service 接続の問題** | service 経由で Pod にアクセスできない | `kubectl describe svc <service-name>`, `kubectl get endpointslices -l kubernetes.io/service-name=<service-name>` | label selector、Pod 状態、network policy を確認 |
| **Node の問題** | Node が NotReady 状態 | `kubectl describe node <node-name>`, `kubectl get events` | kubelet 状態、system resource、network 接続を確認 |
| **DNS の問題** | service name で接続できない | `kubectl exec -it <pod-name> -- nslookup kubernetes.default` | CoreDNS Pod、kube-dns service、network policy を確認 |
| **認証/認可の問題** | API server access が拒否される | `kubectl auth can-i <verb> <resource>` | RBAC 設定、certificate 有効性、service account を確認 |

### Pod のトラブルシューティング

```bash
# Check pod status
kubectl get pod <pod-name> -o wide

# Check pod details
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # Logs from previous container

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/sh

# Check pod events
kubectl get events --field-selector involvedObject.name=<pod-name>
```

### Node のトラブルシューティング

```bash
# Check node status
kubectl get nodes
kubectl describe node <node-name>

# Check node resource usage
kubectl top node <node-name>

# Check node system logs (SSH required)
ssh <node-ip> 'sudo journalctl -u kubelet'

# Check kubelet status (SSH required)
ssh <node-ip> 'sudo systemctl status kubelet'
```

### ネットワークのトラブルシューティング

```bash
# Check service and endpoints
kubectl get svc <service-name>
kubectl get endpointslices -l kubernetes.io/service-name=<service-name>

# DNS troubleshooting
kubectl run -it --rm dns-test --image=busybox -- sh
# Inside the container
nslookup kubernetes.default.svc.cluster.local
cat /etc/resolv.conf

# Network connectivity test
kubectl run -it --rm network-test --image=nicolaka/netshoot -- sh
# Inside the container
ping <target-ip>
traceroute <target-ip>
curl <service-name>:<port>
```
## Amazon EKS クラスター管理

Amazon EKS（Elastic Kubernetes Service）は、AWS が control plane を管理する AWS 上のマネージド Kubernetes service です。node に関する顧客の責任は、managed node group、Auto Mode、Fargate、またはセルフマネージド compute によって異なります。workload のセキュリティと設定は引き続き顧客の責任です。

### EKS クラスターアーキテクチャ

![Amazon EKS クラスターが、AWS 管理の control plane（API server、etcd、scheduler）と、data plane（EC2 Auto Scaling group を持つ managed node group、セルフマネージド node、Fargate）、networking（VPC CNI と AWS VPC）、security（IAM role と policy による IAM 認証）を含む顧客責任領域に分割されることを示すアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-13.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-13.html)

### EKS クラスターの作成

```bash
# Create cluster using eksctl
eksctl create cluster \
  --name my-cluster \
  --version 1.36 \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed

# Alternative: create control plane using AWS CLI (not after the eksctl example)
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
  --kubernetes-version 1.36 \
  --resources-vpc-config "subnetIds=${EKS_SUBNET_IDS:?Set two or more appropriate subnets},securityGroupIds=${EKS_SECURITY_GROUP_ID:?Set the intended security group},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${ADMIN_CIDR:?Set an approved administrator public CIDR}"
```

### Node Group 管理

```bash
# Create managed node group
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5

# Scale node group
eksctl scale nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --nodes 5 \
  --region us-west-2

# Update node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --region us-west-2
```

### EKS クラスターのアップグレード

```bash
# Check cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"

# Upgrade cluster control plane
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version "${TARGET_VERSION:?Select the next EKS-supported minor version}"

# Upgrade managed node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### EKS クラスターの認証および認可

クラスターは `API` または `API_AND_CONFIG_MAP` 認証 mode を使用する必要があります。既存の administrator/node access を維持しながら、legacy aws-auth mapping からの移行を計画してください。この例では、viewer role に default namespace のみへの access を付与します。

```bash
aws eks describe-cluster --name my-cluster --query cluster.accessConfig.authenticationMode
aws eks create-access-entry --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/cluster-viewer --type STANDARD
aws eks associate-access-policy --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/cluster-viewer \
  --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy \
  --access-scope type=namespace,namespaces=default
```

[EKS access-entry guide](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)を参照してください。EKS access entry を管理する権限と Kubernetes workload の権限は別個です。

### EKS クラスターの監視

Control plane logging は api/audit/authenticator/controllerManager/scheduler log を export します。Container Insights には CloudWatch agent/add-on とスコープを限定した telemetry IAM 権限が必要です。update-cluster-logging では有効になりません。CloudWatch observability add-on は CloudWatch/Fluent Bit コンポーネントをインストールし、Prometheus/Grafana はインストールしません。[公式 add-on セットアップ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)を参照してください。

```bash
# Enable EKS control-plane logs
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --region us-west-2

# Install CloudWatch observability (not Prometheus/Grafana)
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version "${CLOUDWATCH_ADDON_VERSION:?Select a compatible add-on version}"
```
## クラスター管理のベストプラクティス

効果的な Kubernetes クラスター管理のベストプラクティスは、安定性、セキュリティ、パフォーマンスを確保する上で重要です。

### クラスターセットアップのベストプラクティス

1. **Multi-Availability Zone Configuration**: 高可用性のため、複数の availability zone に node を分散
2. **適切なサイジング**: workload に適した node type と数を選択
3. **Autoscaling 設定**: cluster autoscaler と horizontal pod autoscaler を有効化
4. **NetworkPolicy の適用**: default deny policy から開始し、必要な通信のみ許可
5. **ResourceQuota の設定**: namespace ごとに resource limit を設定

### 運用のベストプラクティス

1. **宣言的設定の使用**: すべての resource を YAML file として定義し、version control する
2. **GitOps の採用**: Git を single source of truth として使用し、自動 deployment pipeline を構築
3. **定期的なバックアップ**: etcd data と persistent volume data を定期的にバックアップ
4. **監視とアラート**: 包括的な監視 system を構築し、主要 metric の alert を設定
5. **集中ロギング**: 分析しやすいようにすべての log を中央 logging system に収集

### セキュリティのベストプラクティス

1. **最小権限の原則**: RBAC を使用して必要最小限の権限のみを付与
2. **ネットワークセグメンテーション**: network policy を使用して Pod 間通信を制限
3. **Image Scanning**: 脆弱性検出のための container image scanning を実装
4. **Secret 管理**: 外部 secret 管理ツール（例: AWS Secrets Manager、HashiCorp Vault）を使用
5. **定期的なセキュリティ監査**: クラスター設定と権限を定期的に監査

### アップグレードのベストプラクティス

1. **段階的アップグレード**: 一度にすべてではなく段階的にアップグレード
2. **テスト環境を先に**: 本番前にテスト環境でアップグレードを検証
3. **バックアップの作成**: アップグレード前に完全なバックアップを実行
4. **ロールバック計画**: 問題発生時に以前の version にロールバックする計画を策定
5. **アップグレード window の設定**: 使用量が少ない時間帯にアップグレードを実行

### コスト最適化のベストプラクティス

1. **適切な Node Size の選択**: workload に最適な node type を選択
2. **Spot Instance の活用**: 重要でない workload に spot instance を使用
3. **Autoscaling の設定**: 需要に基づく自動 scale up/down を設定
4. **Resource Request と Limit の最適化**: 実際の使用量に基づいて resource request と limit を設定
5. **Idle Resource の特定**: idle resource を定期的に特定して削除

### ドキュメントのベストプラクティス

1. **アーキテクチャの文書化**: クラスターアーキテクチャ、networking、security 設定を文書化
2. **運用手順の文書化**: 一般的な運用作業、トラブルシューティング手順、緊急対応計画を文書化
3. **変更管理**: すべてのクラスター変更を記録・追跡
4. **Runbook の作成**: 一般的なシナリオ向けの段階的な guide を提供
5. **知識共有**: チーム内で定期的な知識共有とトレーニング session を実施
## まとめ

Kubernetes クラスター管理は、さまざまな側面を含む複雑な作業です。クラスターのセットアップから運用、監視、トラブルシューティング、アップグレードまで、体系的なアプローチが必要です。

効果的なクラスター管理のため、次の主要領域に注力してください。

1. **クラスターコンポーネント管理**: control plane および node コンポーネントの安定した運用
2. **リソース管理**: 効率的なリソース割り当てと使用
3. **ネットワーク**: 安全で効率的なネットワーク設定
4. **セキュリティ**: 適切な認証および認可管理
5. **バックアップとリカバリ**: データ損失の防止と災害復旧計画
6. **監視とロギング**: クラスター状態とパフォーマンスの監視
7. **トラブルシューティング**: 体系的なトラブルシューティングアプローチ

Amazon EKS のようなマネージド Kubernetes service を使用する場合、service provider と user 間の責任共有モデルを理解することが重要です。AWS が control plane を管理し、compute の責任は mode によって異なります。顧客は引き続きアプリケーション設定とセキュリティを管理します。

ベストプラクティスに従い、適切なツールを活用することで、安定し、安全で、効率的な Kubernetes クラスターを運用できます。クラスター管理能力を高めるための継続的な学習と改善が重要です。

---

> **参考資料**:
> - [Kubernetes 公式ドキュメント: クラスター管理](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Amazon EKS ユーザーガイド](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Kubernetes ベストプラクティス: クラスター管理](https://kubernetes.io/docs/setup/best-practices/)
> - [etcd ドキュメント: バックアップとリカバリ](https://etcd.io/docs/v3.6/op-guide/recovery/)
> - [Prometheus ドキュメント](https://prometheus.io/docs/introduction/overview/)

## クイズ

この章で学んだ内容を確認するには、[クラスター管理クイズ](../quizzes/core/09-cluster-administration-quiz.md)に挑戦してください。
