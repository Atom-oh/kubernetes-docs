# Kubernetes クラスター管理

> **サポート対象バージョン**: Kubernetes 1.34 (Released 2025-11-24)
> **最終更新**: February 23, 2026

Kubernetes クラスター管理は、クラスターのセットアップ、保守、監視、トラブルシューティング、アップグレードを含む重要な作業です。この章では、Kubernetes クラスター管理のさまざまな側面と、Amazon EKS でのクラスター管理のベストプラクティスを学びます。

## コアコンセプト

- **クラスターライフサイクル管理**: クラスター作成から廃止までの全プロセス
- **Control Plane 管理**: API server、scheduler、controller manager などのコアコンポーネントの管理
- **Node 管理**: worker node の追加、削除、保守
- **リソース割り当て**: CPU、メモリ、ストレージなどのリソース割り当てと制限の設定
- **アップグレード戦略**: ダウンタイムを最小化するためのクラスターおよびアプリケーションのアップグレード戦略

## 目次
1. [クラスター管理の概要](#cluster-administration-overview)
2. [クラスターコンポーネント管理](#cluster-component-management)
3. [リソース管理](#resource-management)
4. [クラスターNetworking](#cluster-networking)
5. [Authentication と Authorization 管理](#authentication-and-authorization-management)
6. [クラスターアップグレード](#cluster-upgrades)
7. [バックアップとリカバリ](#backup-and-recovery)
8. [監視とロギング](#monitoring-and-logging)
9. [トラブルシューティング](#troubleshooting)
10. [Amazon EKS クラスター管理](#amazon-eks-cluster-administration)
11. [クラスター管理のベストプラクティス](#cluster-administration-best-practices)
12. [まとめ](#conclusion)

## 環境セットアップ

クラスター管理には次のツールが必要です。

```bash
# Install kubectl (Linux)
curl -LO "https://dl.k8s.io/release/v1.33.3/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Install kubeadm (for cluster creation and management)
sudo apt-get update && sudo apt-get install -y kubeadm=1.33.3-00

# Install Helm (for package management)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install k9s (cluster management UI)
curl -sS https://webinstall.dev/k9s | bash
```

## クラスター管理の概要

Kubernetes クラスター管理とは、クラスターのライフサイクル全体を管理するプロセスです。主な領域は次のとおりです。

1. **クラスターのセットアップと設定**: クラスター作成、node の追加、networking のセットアップ、ストレージ設定など
2. **運用管理**: リソース監視、パフォーマンス最適化、キャパシティ計画、トラブルシューティング
3. **セキュリティ管理**: Authentication、Authorization、network policy、security context など
4. **アップグレードとパッチ**: クラスターバージョンのアップグレード、セキュリティパッチの適用
5. **バックアップとリカバリ**: クラスターデータのバックアップ、災害復旧計画

次の図は、Kubernetes クラスター管理の主な領域と関連ツールを示します。

## クラスターコンポーネント管理

Kubernetes クラスターは Control Plane コンポーネントと node コンポーネントで構成されます。各コンポーネントの管理は、クラスターの安定性とパフォーマンスにとって重要です。

### Control Plane コンポーネント管理

![Kubernetes Control Plane が 5 つのコンポーネント（API server、etcd、scheduler、controller manager、cloud controller manager）へ分岐し、それぞれが担当する運用上の関心事（Authentication と Authorization、データバックアップ、scheduling policy、controller state 監視、cloud resource 管理）と対応付けられているツリー図。](../.gitbook/assets/en-core-09-cluster-administration-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-0.html)

#### API Server 管理

API server は Kubernetes API を公開する Control Plane のコアコンポーネントです。

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/healthz'
```

#### etcd 管理

etcd は Kubernetes のすべてのクラスターデータを格納する分散 key-value store です。

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

Node はコンテナ化アプリケーションを実行する worker machine です。

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

### コンポーネントステータス監視

```bash
# Check control plane component status
kubectl get componentstatuses

# Check system pod status
kubectl get pods -n kube-system

# Check node resource usage
kubectl top nodes
```

![クラスター管理者の 5 つの責務領域と、それぞれを実施するためのツールを対応付けた図。](../.gitbook/assets/en-core-09-cluster-administration-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-1.html)

### クラスター管理ツール

Kubernetes クラスター管理にはさまざまなツールを利用できます。

1. **kubectl**: Kubernetes クラスターと対話する command-line tool
2. **kubeadm**: Kubernetes クラスターを作成および管理するツール
3. **kops**: Kubernetes クラスターを作成、アップグレード、管理するツール
4. **eksctl**: Amazon EKS クラスターを作成および管理するツール
5. **Helm**: Kubernetes application package manager
6. **Kubernetes Dashboard**: Web ベースの Kubernetes user interface
7. **Prometheus & Grafana**: 監視およびアラートツール
8. **Fluentd & Elasticsearch**: ロギングツール

## クラスターコンポーネント管理

Kubernetes クラスターは複数のコンポーネントで構成され、これらを効果的に管理することが重要です。

### Control Plane コンポーネント

Control Plane コンポーネントはクラスターの全体的な状態を管理します。

1. **kube-apiserver**: Kubernetes API を公開するコンポーネント
2. **etcd**: クラスターデータを格納する key-value store
3. **kube-scheduler**: Pod を node にスケジュールするコンポーネント
4. **kube-controller-manager**: controller を実行するコンポーネント
5. **cloud-controller-manager**: cloud provider と対話するコンポーネント

次の図は Kubernetes Control Plane コンポーネントとその相互作用を示します。

![etcd、kube-scheduler、kube-controller-manager、cloud-controller-manager が中央の kube-apiserver と双方向に通信し、worker node の kubelet も API server と双方向に通信しながら kube-proxy と container runtime を管理するアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-2.html)

#### Control Plane コンポーネント監視

Control Plane コンポーネントのステータスを監視することは重要です。

```bash
# Check control plane component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -it -n kube-system etcd-<node-name> -- etcdctl endpoint health
```

#### Control Plane コンポーネント設定

Control Plane コンポーネント設定の管理方法は次のとおりです。

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
    - --etcd-certfile=/etc/kubernetes/pki/etcd/server.crt
    - --etcd-keyfile=/etc/kubernetes/pki/etcd/server.key
    - --etcd-servers=https://127.0.0.1:2379
    - --kubelet-client-certificate=/etc/kubernetes/pki/apiserver-kubelet-client.crt
    - --kubelet-client-key=/etc/kubernetes/pki/apiserver-kubelet-client.key
    - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
    - --secure-port=6443
    - --service-account-key-file=/etc/kubernetes/pki/sa.pub
    - --service-cluster-ip-range=10.96.0.0/12
    - --tls-cert-file=/etc/kubernetes/pki/apiserver.crt
    - --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
    image: k8s.gcr.io/kube-apiserver:v1.21.0
    name: kube-apiserver
```

### Node コンポーネント

Node コンポーネントは各 node 上で実行され、Pod を管理します。

1. **kubelet**: 各 node で実行され、Pod とコンテナの実行を保証する agent
2. **kube-proxy**: network rule を維持し、接続転送を処理するコンポーネント
3. **Container Runtime**: コンテナを実行する software（Docker、containerd、CRI-O など）

#### Node 管理

Node 管理の主要コマンドは次のとおりです。

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
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

#### Node トラブルシューティング

Node のトラブルシューティング用コマンドです。

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

## リソース管理

Kubernetes クラスターでリソースを効果的に管理することは、クラスターの安定性とパフォーマンスの維持に重要です。

### Resource Quota

Resource quota は namespace ごとのリソース使用量を制限します。

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

上記の例では、`dev` namespace には最大 10 個の Pod、1 CPU と 1Gi メモリの request、2 CPU と 2Gi メモリの limit を設定できます。

### Limit Range

Limit range は namespace 内の個々のリソースに default 値と制限を設定します。

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

上記の例では、`dev` namespace 内のすべてのコンテナに、500m CPU と 512Mi メモリの default limit、200m CPU と 256Mi メモリの default request、1 CPU と 1Gi メモリの最大値、100m CPU と 128Mi メモリの最小値が適用されます。

### Horizontal Pod Autoscaler (HPA)

HPA は CPU 使用率または custom metric に基づいて Pod 数を自動調整します。

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

上記の例では、`frontend` Deployment は CPU 使用率が 80% を超えると自動的に scale out し、80% 未満になると scale in します。replica 数は最小 2、最大 10 に維持されます。

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
    updateMode: "Auto"
```

上記の例では、`frontend` Deployment の Pod は実際のリソース使用量に基づいて CPU とメモリの request が自動調整されます。
## クラスターNetworking

Kubernetes クラスターNetworking は Pod、Service、node 間の通信を管理します。

### クラスターネットワークモデル

Kubernetes network model の基本要件は次のとおりです。

1. すべての Pod が NAT なしで他のすべての Pod と通信できる
2. Node agent（kubelet）がその node 上のすべての Pod と通信できる
3. NAT mode で実行される Pod が外部と通信できる

次の図は Kubernetes networking コンポーネントと通信フローを示します。

![client traffic が Ingress を経由して Service に入り、Service が別々の node 上にある 2 つの Pod に load balance し、Pod 同士が通信して外部 service に到達するアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-3.html)

### CNI (Container Network Interface) Plugin

Kubernetes は CNI plugin を通じて networking を実装します。一般的な CNI plugin は次のとおりです。

1. **Calico**: network policy と security 機能を強化した CNI
2. **Flannel**: シンプルな overlay networking を提供
3. **Cilium**: eBPF ベースの networking および security solution
4. **AWS VPC CNI**: AWS VPC と統合された CNI
5. **Weave Net**: multi-host container networking solution

#### CNI Plugin のインストールと設定

CNI plugin のインストール例（Calico）:

```bash
# Install Calico
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Check Calico status
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Service Networking

Kubernetes Service は Pod set に安定した endpoint を提供します。

1. **ClusterIP**: クラスター内からのみアクセス可能な Service
2. **NodePort**: すべての node の特定 port を通じてアクセス可能な Service
3. **LoadBalancer**: 外部 load balancer を通じてアクセス可能な Service
4. **ExternalName**: 外部 Service の CNAME record を提供

#### Service CIDR 設定

Service CIDR は Service IP address range を定義します。

```bash
# Set service CIDR in kube-apiserver configuration
--service-cluster-ip-range=10.96.0.0/12
```

### CoreDNS 管理

CoreDNS は Kubernetes に DNS service を提供します。

```bash
# Check CoreDNS status
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS configuration
kubectl get configmap -n kube-system coredns -o yaml
```

CoreDNS の設定例:

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

### Network Policy

Network policy は Pod 間の通信を制御します。

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

上記の例では、`role=db` label を持つ Pod は、`role=frontend` label を持つ Pod からの TCP port 3306 の inbound traffic と、`role=monitoring` label を持つ Pod への TCP port 9090 の outbound traffic だけを許可します。

## Authentication と Authorization 管理

Kubernetes の Authentication と Authorization 管理は、クラスター security のコア要素です。

次の図は Kubernetes の Authentication と Authorization のフローを示します。

![request が Authentication、Authorization、admission control を経て API server に到達し、各段階でサポートされる具体的な Authentication method と Authorization mode を示すアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-4.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-4.html)

### Authentication

Kubernetes はさまざまな Authentication method をサポートします。

1. **X.509 Certificates**: client certificate を使用する Authentication
2. **Service Account Tokens**: service account に関連付けられた JWT token
3. **OpenID Connect (OIDC)**: 外部 identity provider を介した Authentication
4. **Webhook Token Authentication**: 外部 service を介した token 検証
5. **Authentication Proxy**: Authentication proxy を介した request 処理

#### X.509 Certificate 管理

X.509 certificate の作成と管理:

```bash
# Create Certificate Signing Request (CSR)
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

# Get certificate
kubectl get csr user-csr -o jsonpath='{.status.certificate}' | base64 --decode > user.crt
```

#### OIDC Authentication 設定

OIDC Authentication の設定例:

```bash
# Add OIDC flags to kube-apiserver configuration
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### Authorization

Kubernetes はさまざまな Authorization mode をサポートします。

1. **RBAC (Role-Based Access Control)**: role ベースの access control
2. **ABAC (Attribute-Based Access Control)**: attribute ベースの access control
3. **Node**: node Authorization
4. **Webhook**: 外部 service を介した Authorization

#### RBAC 設定

RBAC は最も一般的な Authorization mechanism です。

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

上記の例では、`user` には `default` namespace の Pod を表示する権限があります。

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

上記の例では、`user` にはクラスター内のすべての node を表示する権限があります。

### Service Account 管理

Service account は Pod が API server と通信するために使用します。

```yaml
# Create service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default

# Grant permissions to service account
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

Security context は Pod とコンテナの権限および access control を定義します。

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
  - name: security-context-container
    image: nginx
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

上記の例では、Pod は UID 1000 および GID 3000 で実行され、コンテナは特権昇格ができず、すべての Linux capability が削除され、root filesystem は read-only で mount されます。

## クラスターアップグレード

Kubernetes クラスターのアップグレードは、新機能、パフォーマンス改善、security patch を適用するために必要です。

次の図は Kubernetes クラスターアップグレードプロセスを示します。

![Kubernetes クラスターアップグレードの workflow 図。計画とバージョン互換性確認、etcd backup、最初の Control Plane node のアップグレードと機能テスト、残りの Control Plane と worker node のアップグレード、クラスター検証を経てアップグレード完了となり、検証で問題が見つかった場合は backup から復元する rollback path がある。](../.gitbook/assets/en-core-09-cluster-administration-5.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-5.html)

### アップグレード計画

クラスターアップグレードを計画する際の考慮事項:

1. **バージョン互換性**: Kubernetes version 間の互換性を確認する
2. **アップグレードパス**: サポートされているアップグレードパスを確認する
3. **ダウンタイム**: アップグレード中に予想されるダウンタイムを計画する
4. **Rollback Plan**: 問題発生時の rollback plan を策定する
5. **アプリケーションへの影響**: アップグレードがアプリケーションに与える影響を評価する

### Control Plane アップグレード

kubeadm を使用した Control Plane のアップグレード:

```bash
# Check upgrade plan
kubeadm upgrade plan

# Upgrade first control plane node
ssh control-plane-1
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade apply v1.22.0

# Upgrade additional control plane nodes
ssh control-plane-2
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade node

# Upgrade kubelet and kubectl
sudo apt-get install -y kubelet=1.22.0-00 kubectl=1.22.0-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

### Worker Node アップグレード

Worker node のアップグレードプロセス:

```bash
# Drain node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# SSH to node
ssh <node-name>

# Upgrade kubeadm
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade node

# Upgrade kubelet and kubectl
sudo apt-get install -y kubelet=1.22.0-00 kubectl=1.22.0-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Uncordon node
kubectl uncordon <node-name>
```

### アップグレード検証

アップグレード後にクラスターのステータスを検証します。

```bash
# Check node versions
kubectl get nodes

# Check component status
kubectl get componentstatuses

# Check pod status
kubectl get pods --all-namespaces

# Test cluster functionality
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80
kubectl get svc nginx
```
## バックアップとリカバリ

Kubernetes クラスターのバックアップとリカバリは、災害復旧計画の重要な一部です。

次の図は Kubernetes クラスターのバックアップおよびリカバリプロセスを示します。

![スケジュールされた etcd snapshot と resource-YAML backup の両方が backup storage に保存され、災害復旧時には etcd restore と resource restore に利用されるアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-6.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-6.html)

### etcd バックアップ

etcd は Kubernetes クラスターのすべての状態情報を格納するため、定期的なバックアップが重要です。

```bash
# Create etcd snapshot
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db

# Check snapshot status
ETCDCTL_API=3 etcdctl --write-out=table snapshot status /backup/etcd-snapshot-2023-01-01-12-00-00.db
```

### etcd リカバリ

etcd snapshot から復元します。

```bash
# Stop all Kubernetes services
sudo systemctl stop kubelet kube-apiserver kube-controller-manager kube-scheduler

# Backup etcd data directory
sudo mv /var/lib/etcd /var/lib/etcd.bak

# Restore from snapshot
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  --data-dir=/var/lib/etcd \
  --initial-cluster=master-1=https://192.168.1.10:2380 \
  --initial-cluster-token=etcd-cluster-1 \
  --initial-advertise-peer-urls=https://192.168.1.10:2380 \
  snapshot restore /backup/etcd-snapshot-2023-01-01-12-00-00.db

# Set permissions
sudo chown -R etcd:etcd /var/lib/etcd

# Restart Kubernetes services
sudo systemctl start etcd
sudo systemctl start kubelet kube-apiserver kube-controller-manager kube-scheduler
```

### Resource バックアップ

Kubernetes resource を YAML file としてバックアップします。

```bash
# Backup all resources in all namespaces
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  mkdir -p /backup/resources/$ns
  for resource in $(kubectl api-resources --namespaced=true -o name); do
    kubectl get -n $ns $resource -o yaml > /backup/resources/$ns/$resource.yaml
  done
done

# Backup cluster-scoped resources
mkdir -p /backup/resources/cluster-scoped
for resource in $(kubectl api-resources --namespaced=false -o name); do
  kubectl get $resource -o yaml > /backup/resources/cluster-scoped/$resource.yaml
done
```

### バックアップの自動化

CronJob を使用してバックアップタスクを自動化します。

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  schedule: "0 0 * * *"  # Run daily at midnight
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: etcd-backup
            image: bitnami/etcd:latest
            command:
            - /bin/sh
            - -c
            - |
              ETCDCTL_API=3 etcdctl --endpoints=https://etcd-client:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/server.crt \
                --key=/etc/kubernetes/pki/etcd/server.key \
                snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db
            volumeMounts:
            - name: etcd-certs
              mountPath: /etc/kubernetes/pki/etcd
              readOnly: true
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: etcd-certs
            hostPath:
              path: /etc/kubernetes/pki/etcd
              type: Directory
          - name: backup
            persistentVolumeClaim:
              claimName: etcd-backup-pvc
```

## 監視とロギング

効果的な監視とロギングはクラスター管理のコア要素です。

次の図は Kubernetes クラスターの監視およびロギングアーキテクチャを示します。

![API server と node metric が kube-state-metrics と Node Exporter を通じて Prometheus に流れ、さらに Alertmanager と Grafana に流れる一方で、Pod log が Fluentd/Fluent Bit を経由して Elasticsearch と Kibana、および Loki に流れ、Loki も Grafana に接続するアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-7.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-7.html)

### 監視ツール

Kubernetes クラスター監視用のツール:

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

監視する主要 metric:

1. **Node Metrics**: CPU、メモリ、disk、network 使用量
2. **Pod Metrics**: CPU、メモリ使用量、restart count
3. **Container Metrics**: CPU、メモリ使用量、filesystem 使用量
4. **API Server Metrics**: request latency、request count、error rate
5. **etcd Metrics**: disk I/O、leader change、commit latency

### ロギングツール

Kubernetes クラスターロギング用のツール:

1. **Elasticsearch**: log の保存と検索
2. **Fluentd/Fluent Bit**: log の収集と転送
3. **Kibana**: log の可視化
4. **Loki**: log aggregation system
5. **Grafana**: log の可視化

#### EFK (Elasticsearch、Fluentd、Kibana) Stack のインストール

Helm を使用して EFK stack をインストールします。

```bash
# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace

# Install Fluentd
helm install fluentd fluent/fluentd \
  --namespace logging

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=LoadBalancer
```

#### Log 収集設定

Fluentd の設定例:

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
        @type json
        time_format %Y-%m-%dT%H:%M:%S.%NZ
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

## トラブルシューティング

Kubernetes クラスターのトラブルシューティングは、クラスター管理の重要な一部です。

### Pod のトラブルシューティング

Pod のトラブルシューティング用コマンドです。

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

Node のトラブルシューティング用コマンドです。

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

### Networking のトラブルシューティング

Networking のトラブルシューティング用コマンドです。

```bash
# Check service status
kubectl get svc <service-name>

# Check service detailed information
kubectl describe svc <service-name>

# Check endpoints
kubectl get endpoints <service-name>

# Check DNS
kubectl run -it --rm --restart=Never busybox --image=busybox -- nslookup <service-name>

# Test network connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- <service-name>:<port>

# Check network policies
kubectl get networkpolicy
kubectl describe networkpolicy <policy-name>
```

### Control Plane のトラブルシューティング

Control Plane のトラブルシューティング用コマンドです。

```bash
# Check component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check controller manager logs
kubectl logs -n kube-system kube-controller-manager-<node-name>

# Check scheduler logs
kubectl logs -n kube-system kube-scheduler-<node-name>

# Check etcd logs
kubectl logs -n kube-system etcd-<node-name>
```

## Amazon EKS クラスター管理

Amazon EKS は、クラスター管理の多くの側面を自動化する managed Kubernetes service です。

次の図は Amazon EKS クラスターアーキテクチャと管理コンポーネントを示します。

![user が AWS console、CLI、または API を通じて Amazon EKS を管理し、EKS が Control Plane、managed node group、Fargate を実行し、Control Plane が AWS IAM、VPC、CloudWatch を使用し、VPC CNI、CoreDNS、kube-proxy add-on を利用するアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-8.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-8.html)

### EKS クラスター設定

EKS クラスター設定の管理:

```bash
# Check EKS cluster information
aws eks describe-cluster --name my-cluster

# Update EKS cluster
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true

# Update EKS cluster version
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.22
```

### EKS Node Group 管理

EKS node group の管理:

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

EKS add-on の管理:

```bash
# Check available add-ons
aws eks describe-addon-versions \
  --kubernetes-version 1.22

# Install add-on
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.10.1-eksbuild.1

# Update add-on
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.10.2-eksbuild.1

# Delete add-on
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni
```

### EKS クラスターアップグレード

EKS クラスターのアップグレードプロセス:

1. **Control Plane アップグレード**:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version 1.22
   ```

2. **Add-on アップグレード**:
   ```bash
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.10.2-eksbuild.1
   ```

3. **Node Group アップグレード**:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

### EKS クラスター監視

EKS クラスター監視ツール:

1. **Amazon CloudWatch**: metric、log、alert
2. **AWS CloudTrail**: API call logging
3. **Amazon Managed Grafana**: metric の可視化
4. **Amazon Managed Service for Prometheus**: metric の収集と保存

CloudWatch Container Insights を有効にします。

```bash
# Enable Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## クラスター管理のベストプラクティス

Kubernetes および EKS クラスター管理のベストプラクティス:

### クラスター設定のベストプラクティス

1. **Infrastructure as Code (IaC)**: Terraform、AWS CDK、eksctl などを使用してクラスター設定を管理する
2. **Version Control**: クラスター設定を version control system に保存する
3. **複数環境**: development、staging、production 環境を分離する
4. **ネットワーク分離**: 適切な network separation と security group を設定する
5. **最小権限の原則**: 必要最小限の権限だけを付与する

### 運用のベストプラクティス

1. **定期的なバックアップ**: etcd と重要な resource を定期的にバックアップする
2. **監視とアラート**: 包括的な監視および alert system を構築する
3. **集中ロギング**: log を集約して分析する
4. **自動化**: 繰り返し作業を自動化する
5. **災害復旧計画**: 明確な災害復旧計画を策定してテストする

### セキュリティのベストプラクティス

1. **定期的な更新**: クラスターと node を定期的に更新する
2. **Network Policy**: 適切な network policy を設定する
3. **暗号化**: 保存中および転送中のデータを暗号化する
4. **Security Context**: 適切な security context を設定する
5. **Image Scanning**: container image の脆弱性を scan する

### リソース管理のベストプラクティス

1. **Resource Request と Limit**: すべての Pod に適切な resource request と limit を設定する
2. **Namespace 分離**: workload を namespace ごとに分離する
3. **Resource Quota**: namespace ごとに resource quota を設定する
4. **HPA と VPA**: autoscaling を設定する
5. **Node Affinity と Taint**: workload 配置を最適化する

### EKS 固有のベストプラクティス

1. **Managed Node Group**: 可能な場合は managed node group を使用する
2. **Fargate**: serverless workload には Fargate を使用する
3. **EKS Add-on**: 公式 EKS add-on を使用する
4. **IAM Roles for Service Accounts (IRSA)**: Pod ごとに IAM 権限を管理する
5. **VPC CNI Customization**: networking 要件に応じて VPC CNI を設定する

## まとめ

Kubernetes クラスター管理は、クラスターの安定性、security、パフォーマンスの維持に重要な役割を果たします。この章では、クラスターコンポーネント管理、リソース管理、networking、Authentication と Authorization 管理、アップグレード、バックアップとリカバリ、監視とロギング、トラブルシューティングを含む、クラスター管理のさまざまな側面を扱いました。

Amazon EKS を使用すると Kubernetes Control Plane 管理の複雑さを軽減でき、AWS service との統合を通じてクラスター管理を簡素化できます。ただし、効果的なクラスター管理には、基本的な Kubernetes の概念とベストプラクティスを理解することが依然として重要です。

クラスター管理は、クラスター要件と workload の特性に応じて継続的に調整する必要がある継続的なプロセスです。監視ツールを使用してクラスター状態を追跡し、自動化で反復作業を最小化し、ベストプラクティスに従ってクラスターの安定性と security を維持することが重要です。

## クラスターNetworking

Kubernetes クラスターNetworking は、Pod 間通信、service discovery、外部アクセスを管理します。

### ネットワークアーキテクチャ

![クラスターNetworking を Pod network、Service network、Ingress、network policy に分け、それぞれを CNI plugin、Service type（ClusterIP、NodePort、LoadBalancer）、Ingress controller、network security で実現するアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-9.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-9.html)

### CNI Plugin 管理

CNI (Container Network Interface) plugin は Kubernetes クラスターの networking を処理します。

```bash
# Install Calico CNI
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Install Flannel CNI
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml

# Install Cilium CNI (using Helm)
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.14.0 --namespace kube-system
```

### CNI Plugin 比較

| CNI Plugin | ネットワークモデル | Network Policy のサポート | パフォーマンス | 機能 |
|-----------|---------------|----------------------|-------------|----------|
| **Calico** | BGP | はい | 高 | Network policy に強く、routing ベース |
| **Flannel** | VXLAN/host-gateway | いいえ | 中 | シンプルなセットアップ、機能は限定的 |
| **Cilium** | eBPF | はい | 非常に高 | L3-L7 policy、高パフォーマンス |
| **Weave Net** | VXLAN | はい | 中 | encryption サポート、multi-cluster |
| **AWS VPC CNI** | AWS VPC | いいえ | 高 | AWS EKS 用に最適化 |

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
kubectl get endpoints <service-name>

# Check network policies
kubectl describe networkpolicy -n <namespace>
```
## Authentication と Authorization 管理

Kubernetes の Authentication と Authorization 管理は、クラスター security のコア要素です。RBAC (Role-Based Access Control) は user と service account の権限管理に使用されます。

### Authentication method

Kubernetes はさまざまな Authentication method をサポートします。

1. **X.509 Certificates**: client certificate を使用する Authentication
2. **Service Account Tokens**: Pod 内から API server にアクセスするために使用
3. **OpenID Connect (OIDC)**: 外部 identity provider との統合
4. **Webhook Token Authentication**: 外部 Authentication service との統合
5. **Authentication Proxy**: proxy を介した Authentication

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
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "watch", "list"]
```

```yaml
# clusterrolebinding.yaml - binding cluster role to user
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
- kind: Group
  name: manager
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

### User Certificate の作成

```bash
# Generate private key
openssl genrsa -out jane.key 2048

# Create Certificate Signing Request (CSR)
openssl req -new -key jane.key -out jane.csr -subj "/CN=jane/O=dev"

# Sign certificate with Kubernetes CA
sudo openssl x509 -req -in jane.csr \
  -CA /etc/kubernetes/pki/ca.crt \
  -CAkey /etc/kubernetes/pki/ca.key \
  -CAcreateserial \
  -out jane.crt -days 365

# Add user to kubeconfig
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

# Check service account token
kubectl describe serviceaccount app-service-account
```

### 権限の検証

```bash
# Check user permissions
kubectl auth can-i get pods --as jane

# Check permissions in a specific namespace
kubectl auth can-i create deployments --as jane --namespace production
```
## クラスターアップグレード

Kubernetes クラスターのアップグレードは、新機能、security patch、bug fix を適用するために必要です。アップグレードは慎重に計画して実行する必要があります。

### アップグレード計画

![アップグレード計画を 4 つの作業（バージョン互換性の確認、backup の作成、アップグレード戦略の選択、ダウンタイムの計画）に分け、それぞれが API change の確認、etcd backup、in-place と blue/green の選択、user への連絡という具体的なアクションにつながるツリー図。](../.gitbook/assets/en-core-09-cluster-administration-10.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-10.html)

### アップグレード戦略の比較

| 戦略 | 説明 | 利点 | 欠点 | 適した環境 |
|----------|-------------|------------|---------------|---------------------|
| **In-place Upgrade** | 既存クラスターを直接アップグレード | リソース効率がよく、手順がシンプル | rollback が複雑、ダウンタイムの可能性 | development、test 環境 |
| **Blue/Green Deployment** | 新バージョンのクラスターを作成して切り替える | 安全な rollback、検証可能 | リソース重複、コスト増加 | production 環境 |
| **Canary Deployment** | 一部の workload のみを新クラスターへ移行 | 段階的な検証、リスク低減 | 管理が複雑、二重運用 | 重要な production 環境 |

### kubeadm を使用したアップグレード

```bash
# Check current version
kubeadm version

# Check upgrade plan
sudo kubeadm upgrade plan

# Control plane upgrade
sudo apt-get update
sudo apt-get install -y kubeadm=1.33.3-00
sudo kubeadm upgrade apply v1.33.3

# kubelet upgrade
sudo apt-get install -y kubelet=1.33.3-00 kubectl=1.33.3-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Worker node upgrade (on each node)
# 1. Drain node
kubectl drain <node-name> --ignore-daemonsets

# 2. kubeadm upgrade
sudo apt-get update
sudo apt-get install -y kubeadm=1.33.3-00
sudo kubeadm upgrade node

# 3. kubelet upgrade
sudo apt-get install -y kubelet=1.33.3-00 kubectl=1.33.3-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# 4. Uncordon node
kubectl uncordon <node-name>
```

### アップグレード後の検証

```bash
# Check cluster version
kubectl version

# Check node versions
kubectl get nodes

# Check component status
kubectl get componentstatuses

# Check workload status
kubectl get pods -A
```
## バックアップとリカバリ

Kubernetes クラスターのバックアップとリカバリは、災害復旧計画の重要な一部です。主なバックアップ対象は etcd database、persistent volume data、Kubernetes resource definition です。

### etcd のバックアップとリカバリ

etcd はクラスターのすべての状態情報を格納するコアコンポーネントです。

```bash
# etcd backup
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d).db

# etcd recovery
# 1. Stop cluster
sudo systemctl stop kubelet
sudo docker stop $(docker ps -q)

# 2. Restore etcd data
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  snapshot restore /backup/etcd-snapshot-2025-11-24.db \
  --data-dir=/var/lib/etcd-restore \
  --name=master \
  --initial-cluster=master=https://127.0.0.1:2380 \
  --initial-cluster-token=etcd-cluster-1 \
  --initial-advertise-peer-urls=https://127.0.0.1:2380

# 3. Configure to use restored data directory
sudo mv /var/lib/etcd /var/lib/etcd.bak
sudo mv /var/lib/etcd-restore /var/lib/etcd

# 4. Restart cluster
sudo systemctl start kubelet
```

### Kubernetes Resource バックアップ

```bash
# Backup all resources in all namespaces
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

Velero は Kubernetes クラスター resource と persistent volume をバックアップおよびリカバリするツールです。

```bash
# Install Velero (using AWS S3 backup storage)
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.7.0 \
  --bucket velero-backup \
  --backup-location-config region=us-west-2 \
  --snapshot-location-config region=us-west-2 \
  --secret-file ./credentials-velero

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
| **etcd Snapshot** | クラスター状態 | 組み込み機能、完全な状態の保持 | volume data は含まれない、手動プロセス | 中 |
| **Resource YAML Backup** | Kubernetes object | 実装が容易、選択的な復元 | volume data は含まれない、関係性が複雑 | 遅い |
| **Velero** | resource と volume | 自動化、スケジュール、volume snapshot | 追加ツールのインストールが必要 | 速い |
| **Cloud Provider Snapshots** | クラスター全体 | 完全なリカバリ、cloud 統合 | cloud 依存、コスト | 非常に速い |
## 監視とロギング

効果的なクラスター管理には包括的な監視およびロギング system が必要です。これにより問題を早期に検出して解決できます。

### 監視アーキテクチャ

![Kubernetes 監視を metric 収集、log 収集、alert、可視化に分け、それぞれを kube-state-metrics と node-exporter を使用する Prometheus、log を Elasticsearch と Kibana に送信する Fluentd/Fluent Bit、Alertmanager、Grafana が担うアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-11.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-11.html)

### Prometheus と Grafana のインストール

```bash
# Install Prometheus and Grafana using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.enabled=true \
  --set prometheus.service.type=NodePort

# Check services
kubectl get svc -n monitoring

# Access Grafana (using port forwarding)
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
# Default username: admin, default password: prom-operator
```

### EFK Stack のインストール (Elasticsearch、Fluentd、Kibana)

```bash
# Install Elasticsearch and Kibana
helm repo add elastic https://helm.elastic.co
helm repo update

helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace \
  --set replicas=1 \
  --set minimumMasterNodes=1

helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=NodePort

# Install Fluentd
kubectl apply -f https://raw.githubusercontent.com/fluent/fluentd-kubernetes-daemonset/master/fluentd-daemonset-elasticsearch.yaml
```

### 主要な監視 metric

| Metric Type | 説明 | 主要 metric | 監視ツール |
|-------------|-------------|-------------|-----------------|
| **Node Metrics** | Node レベルのリソース使用量 | CPU、メモリ、disk、network | node-exporter、Prometheus |
| **Pod Metrics** | Container リソース使用量 | CPU、メモリ使用量、limit | cAdvisor、Prometheus |
| **Cluster Metrics** | クラスター状態と resource | Pod 数、node ステータス、event | kube-state-metrics |
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

```yaml
# alertmanager-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'

    route:
      receiver: 'slack-notifications'
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      group_by: ['alertname', 'cluster', 'service']

    receivers:
    - name: 'slack-notifications'
      slack_configs:
      - channel: '#alerts'
        send_resolved: true
        title: "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}"
        text: "{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}"
```
## トラブルシューティング

Kubernetes クラスターのトラブルシューティングは system administrator と operator にとって重要なスキルです。効果的なトラブルシューティングには体系的なアプローチが必要です。

### トラブルシューティング方法論

![問題の特定から文書化までの 6 段階のトラブルシューティング手順を示し、情報収集段階が log、event、resource status の確認に分岐する workflow 図。](../.gitbook/assets/en-core-09-cluster-administration-12.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-12.html)

### 一般的な問題と解決策

| 問題の種類 | 症状 | 診断コマンド | 一般的な解決策 |
|-------------|----------|---------------------|-----------------|
| **Pod Not Starting** | Pod が Pending または ContainerCreating 状態 | `kubectl describe pod <pod-name>` | リソース制約、image の可用性、volume mount を確認 |
| **Service Connection Issues** | Service 経由で Pod にアクセスできない | `kubectl describe svc <service-name>`, `kubectl get endpoints <service-name>` | label selector、Pod status、network policy を確認 |
| **Node Issues** | Node が NotReady 状態 | `kubectl describe node <node-name>`, `kubectl get events` | kubelet status、system resource、network connectivity を確認 |
| **DNS Issues** | Service name で接続できない | `kubectl exec -it <pod-name> -- nslookup kubernetes.default` | CoreDNS Pod、kube-dns Service、network policy を確認 |
| **Authentication Issues** | API server access が拒否される | `kubectl auth can-i <verb> <resource>` | RBAC 設定、certificate の有効性、service account を確認 |

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

### Networking のトラブルシューティング

```bash
# Check service and endpoints
kubectl get svc <service-name>
kubectl get endpoints <service-name>

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

Amazon EKS (Elastic Kubernetes Service) は AWS 上の managed Kubernetes service であり、AWS が Control Plane を管理します。ただし、node、networking、security などの管理は user の責任です。

### EKS クラスターアーキテクチャ

![Amazon EKS クラスターを AWS 管理の Control Plane（API server、etcd、scheduler）と、data plane（EC2 Auto Scaling group を持つ managed node group、self-managed node、Fargate）、networking（VPC CNI と AWS VPC）、security（IAM role と policy による IAM Authentication）をカバーする customer responsibility 領域に分けたアーキテクチャ図。](../.gitbook/assets/en-core-09-cluster-administration-13.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-13.html)

### EKS クラスターの作成

```bash
# Create cluster using eksctl
eksctl create cluster \
  --name my-cluster \
  --version 1.33 \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed

# Create cluster using AWS CLI
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
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
eksctl update nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --region us-west-2 \
  --max-pods-per-node 110
```

### EKS クラスターアップグレード

```bash
# Check cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"

# Upgrade cluster control plane
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.33

# Upgrade managed node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### EKS クラスターの Authentication と Authorization

```bash
# Map IAM user/role to cluster RBAC
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:role/admin-role \
  --group system:masters \
  --username admin

# Check aws-auth ConfigMap
kubectl describe configmap aws-auth -n kube-system
```

### EKS クラスター監視

```bash
# Enable CloudWatch Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --region us-west-2

# Install Prometheus and Grafana (using Amazon EKS add-on)
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version v1.1.1-eksbuild.1
```
## クラスター管理のベストプラクティス

効果的な Kubernetes クラスター管理のベストプラクティスは、安定性、security、パフォーマンスの確保に重要です。

### クラスターセットアップのベストプラクティス

1. **Multi-Availability Zone Configuration**: 高可用性のために複数の availability zone に node を分散する
2. **適切なサイズ設定**: workload に適した node type と数を選択する
3. **Autoscaling 設定**: cluster autoscaler と horizontal pod autoscaler を有効化する
4. **Network Policy の適用**: default deny policy から始め、必要な通信だけを許可する
5. **Resource Quota の設定**: namespace ごとに resource limit を設定する

### 運用のベストプラクティス

1. **Declarative Configuration の使用**: すべての resource を YAML file として定義し、version control する
2. **GitOps の採用**: Git を single source of truth として使用し、自動 deployment pipeline を構築する
3. **定期的なバックアップ**: etcd data と persistent volume data を定期的にバックアップする
4. **監視とアラート**: 包括的な監視 system を構築し、主要 metric に alert を設定する
5. **集中ロギング**: すべての log を中央 logging system に収集して分析しやすくする

### セキュリティのベストプラクティス

1. **最小権限の原則**: RBAC を使用して必要最小限の権限だけを付与する
2. **ネットワークセグメンテーション**: network policy を使用して Pod 間通信を制限する
3. **Image Scanning**: 脆弱性検出のために container image scanning を実装する
4. **Secret 管理**: 外部 secret management tool（例: AWS Secrets Manager、HashiCorp Vault）を使用する
5. **定期的な Security Audit**: クラスター設定と権限を定期的に監査する

### アップグレードのベストプラクティス

1. **段階的なアップグレード**: 一度にすべてではなく段階的にアップグレードする
2. **Test Environment を優先**: production の前に test environment でアップグレードを検証する
3. **Backup の作成**: アップグレード前に完全なバックアップを実施する
4. **Rollback Plan**: 問題発生時に以前の version に rollback する計画を策定する
5. **アップグレード時間帯の設定**: 使用量が少ない時間帯にアップグレードを実施する

### コスト最適化のベストプラクティス

1. **適切な Node Size の選択**: workload に最適な node type を選択する
2. **Spot Instance の活用**: 非重要 workload には spot instance を使用する
3. **Autoscaling の設定**: 需要に応じた自動 scale up と scale down を設定する
4. **Resource Request と Limit の最適化**: 実際の使用量に基づいて resource request と limit を設定する
5. **Idle Resource の特定**: idle resource を定期的に特定して削除する

### ドキュメントのベストプラクティス

1. **Architecture の文書化**: クラスター architecture、networking、security 設定を文書化する
2. **運用手順の文書化**: 一般的な運用作業、トラブルシューティング手順、緊急対応計画を文書化する
3. **Change Management**: すべてのクラスター変更を記録して追跡する
4. **Runbook の作成**: 一般的な scenario 用の step-by-step guide を提供する
5. **Knowledge Sharing**: チーム内で定期的に knowledge sharing と training session を実施する
## まとめ

Kubernetes クラスター管理は、さまざまな側面を含む複雑な作業です。クラスターのセットアップから運用、監視、トラブルシューティング、アップグレードまで、体系的なアプローチが必要です。

効果的なクラスター管理では、次の主要領域に注力してください。

1. **クラスターコンポーネント管理**: Control Plane と node コンポーネントの安定運用
2. **リソース管理**: 効率的なリソース割り当てと使用
3. **Networking**: 安全で効率的なネットワーク設定
4. **セキュリティ**: 適切な Authentication と Authorization 管理
5. **バックアップとリカバリ**: データ損失の防止と災害復旧計画
6. **監視とロギング**: クラスター状態とパフォーマンスの監視
7. **トラブルシューティング**: 体系的なトラブルシューティングアプローチ

Amazon EKS のような managed Kubernetes service を使用する場合は、service provider と user の shared responsibility model を理解することが重要です。AWS は Control Plane を管理しますが、node、networking、security などの管理は引き続き user の責任です。

ベストプラクティスに従い、適切なツールを活用することで、安定的で安全かつ効率的な Kubernetes クラスターを運用できます。クラスター管理能力を高めるための継続的な学習と改善が重要です。

---

> **参考資料**:
> - [Kubernetes 公式ドキュメント: クラスター管理](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Kubernetes Best Practices: Cluster Administration](https://kubernetes.io/docs/setup/best-practices/)
> - [etcd Documentation: Backup and Recovery](https://etcd.io/docs/v3.5/op-guide/recovery/)
> - [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)

## クイズ

この章で学んだ内容を確認するには、[クラスター管理クイズ](../quizzes/core/09-cluster-administration-quiz.md)に挑戦してください。
