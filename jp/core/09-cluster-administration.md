# Kubernetes Cluster Administration

> **Supported Versions**: Kubernetes 1.34 (Released 2025-11-24)
> **最終更新**: February 23, 2026

Kubernetes cluster administration は、cluster のセットアップ、保守、monitoring、troubleshooting、upgrade を含む重要な作業です。この章では、Kubernetes cluster administration のさまざまな側面と、Amazon EKS における cluster management の best practices について学びます。

## Core Concepts

- **Cluster Lifecycle Management**: cluster の作成から廃止までの全プロセス
- **Control Plane Management**: API server、scheduler、controller manager などの core components の管理
- **Node Management**: worker nodes の追加、削除、保守
- **Resource Allocation**: CPU、memory、storage などの resource allocation と limit の設定
- **Upgrade Strategy**: downtime を最小化するための cluster と application の upgrade strategy

## Table of Contents
1. [Cluster Administration Overview](#cluster-administration-overview)
2. [Cluster Component Management](#cluster-component-management)
3. [Resource Management](#resource-management)
4. [Cluster Networking](#cluster-networking)
5. [Authentication and Authorization Management](#authentication-and-authorization-management)
6. [Cluster Upgrades](#cluster-upgrades)
7. [Backup and Recovery](#backup-and-recovery)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Troubleshooting](#troubleshooting)
10. [Amazon EKS Cluster Administration](#amazon-eks-cluster-administration)
11. [Cluster Administration Best Practices](#cluster-administration-best-practices)
12. [Conclusion](#conclusion)

## Environment Setup

cluster administration には、次の tools が必要です。

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

## Cluster Administration Overview

Kubernetes cluster administration は、cluster の lifecycle 全体を管理するプロセスです。これには、次の主な領域が含まれます。

1. **Cluster Setup and Configuration**: cluster の作成、node の追加、networking の設定、storage の設定など
2. **Operations Management**: resource monitoring、performance optimization、capacity planning、troubleshooting
3. **Security Management**: authentication、authorization、network policies、security contexts など
4. **Upgrades and Patches**: cluster version upgrade、security patch の適用
5. **Backup and Recovery**: cluster data backup、disaster recovery planning

次の図は、Kubernetes cluster administration の主な領域と関連 tools を示しています。

## Cluster Component Management

Kubernetes cluster は control plane components と node components で構成されます。各 component の管理は、cluster の安定性と performance にとって重要です。

### Control Plane Component Management

```mermaid
graph TD
    A[Control Plane] --> B[API Server]
    A --> C[etcd]
    A --> D[Scheduler]
    A --> E[Controller Manager]
    A --> F[Cloud Controller Manager]

    B --> G[Authentication and Authorization]
    C --> H[Data Backup]
    D --> I[Scheduling Policies]
    E --> J[Controller State Monitoring]
    F --> K[Cloud Resource Management]

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef operation fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E,F k8sComponent;
    class G,H,I,J,K operation;
```

#### API Server Management

API server は、Kubernetes API を公開する control plane の core component です。

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/healthz'
```

#### etcd Management

etcd は、Kubernetes のすべての cluster data を保存する distributed key-value store です。

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

### Node Management

Nodes は containerized applications を実行する worker machines です。

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

### Component Status Monitoring

```bash
# Check control plane component status
kubectl get componentstatuses

# Check system pod status
kubectl get pods -n kube-system

# Check node resource usage
kubectl top nodes
```

```mermaid
flowchart TD
    Admin[Cluster Administrator] --> Setup[Cluster Setup and Configuration]
    Admin --> Operations[Operations Management]
    Admin --> Security[Security Management]
    Admin --> Upgrade[Upgrades and Patches]
    Admin --> Backup[Backup and Recovery]

    Setup --> |Tools| SetupTools[kubeadm, kops, eksctl]
    Operations --> |Tools| OpsTools[kubectl, Prometheus, Grafana]
    Security --> |Tools| SecTools[RBAC, NetworkPolicy, PodSecurityPolicy]
    Upgrade --> |Tools| UpgradeTools[kubeadm upgrade, EKS update]
    Backup --> |Tools| BackupTools[etcd snapshot, Velero]

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Admin userApp;
    class Setup,Operations,Security,Upgrade,Backup k8sComponent;
    class SetupTools,OpsTools,SecTools,UpgradeTools,BackupTools default;
```

### Cluster Administration Tools

Kubernetes cluster administration には、さまざまな tools を利用できます。

1. **kubectl**: Kubernetes clusters と対話するための command-line tool
2. **kubeadm**: Kubernetes clusters を作成および管理するための tool
3. **kops**: Kubernetes clusters を作成、upgrade、管理するための tool
4. **eksctl**: Amazon EKS clusters を作成および管理するための tool
5. **Helm**: Kubernetes application package manager
6. **Kubernetes Dashboard**: Web-based Kubernetes user interface
7. **Prometheus & Grafana**: monitoring と alerting の tools
8. **Fluentd & Elasticsearch**: logging tools

## Cluster Component Management

Kubernetes cluster は複数の components で構成されており、これらの components を効果的に管理することが重要です。

### Control Plane Components

Control plane components は cluster 全体の状態を管理します。

1. **kube-apiserver**: Kubernetes API を公開する component
2. **etcd**: cluster data を保存する key-value store
3. **kube-scheduler**: pods を nodes に schedule する component
4. **kube-controller-manager**: controllers を実行する component
5. **cloud-controller-manager**: cloud providers と連携する component

次の図は、Kubernetes control plane components とその相互作用を示しています。

```mermaid
flowchart TD
    API[kube-apiserver] <--> ETCD[(etcd)]
    API <--> SCH[kube-scheduler]
    API <--> CM[kube-controller-manager]
    API <--> CCM[cloud-controller-manager]
    API <--> Kubelet[kubelet]

    subgraph "Control Plane"
        API
        ETCD
        SCH
        CM
        CCM
    end

    subgraph "Worker Node"
        Kubelet
        Proxy[kube-proxy]
        CRI[Container Runtime]
    end

    Kubelet --> CRI
    Kubelet --> Proxy

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class API,SCH,CM,CCM,Kubelet,Proxy,CRI k8sComponent;
    class ETCD dataStore;
```

#### Control Plane Component Monitoring

Control plane components の状態を monitor することは重要です。

```bash
# Check control plane component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -it -n kube-system etcd-<node-name> -- etcdctl endpoint health
```

#### Control Plane Component Configuration

Control plane component configuration の管理方法です。

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
    - --service-cluster-ip-range=10.96.0.0/12
    - --tls-cert-file=/etc/kubernetes/pki/apiserver.crt
    - --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
    image: k8s.gcr.io/kube-apiserver:v1.21.0
    name: kube-apiserver
```

### Node Components

Node components は各 node 上で実行され、pods を管理します。

1. **kubelet**: 各 node で実行され、pods と containers が稼働していることを保証する agent
2. **kube-proxy**: network rules を維持し、connection forwarding を処理します
3. **Container Runtime**: containers を実行する software（Docker、containerd、CRI-O など）

#### Node Management

Node management の主要 commands です。

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

#### Node Troubleshooting

Node troubleshooting の commands です。

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

## Resource Management

Kubernetes cluster 内の resources を効果的に管理することは、cluster の安定性と performance を維持するために重要です。

### Resource Quotas

Resource quotas は namespace ごとの resource usage を制限します。

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

上記の例では、`dev` namespace は最大 10 pods、1 CPU と 1Gi memory の requests、2 CPU と 2Gi memory の limits を持つことができます。

### Limit Ranges

Limit ranges は namespace 内の個々の resources に対する defaults と limits を設定します。

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

上記の例では、`dev` namespace 内のすべての containers は、500m CPU と 512Mi memory の default limits、200m CPU と 256Mi memory の default requests、最大 1 CPU と 1Gi memory、最小 100m CPU と 128Mi memory を持ちます。

### Horizontal Pod Autoscaler (HPA)

HPA は CPU usage または custom metrics に基づいて pods 数を自動的に調整します。

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

上記の例では、`frontend` deployment は CPU utilization が 80% を超えると自動的に scale out し、80% を下回ると scale in します。最小 2、最大 10 replicas を維持します。

### Vertical Pod Autoscaler (VPA)

VPA は pod の CPU と memory requests を自動的に調整します。

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

上記の例では、`frontend` deployment 内の pods は、実際の resource usage に基づいて CPU と memory requests が自動的に調整されます。
## Cluster Networking

Kubernetes cluster networking は、pods、services、nodes 間の通信を管理します。

### Cluster Network Model

Kubernetes network model の基本要件です。

1. すべての pods は NAT なしですべての他の pods と通信できます
2. Node agents（kubelet）はその node 上のすべての pods と通信できます
3. NAT mode で実行されている pods は外部と通信できます

次の図は、Kubernetes networking components と communication flows を示しています。

```mermaid
flowchart LR
    Client[Client] --> Ingress[Ingress]
    Ingress --> SVC[Service]
    SVC --> Pod1[Pod 1]
    SVC --> Pod2[Pod 2]

    subgraph "Cluster Internal"
        Ingress
        SVC
        subgraph "Node 1"
            Pod1
        end
        subgraph "Node 2"
            Pod2
        end
    end

    Pod1 <--> Pod2
    Pod1 --> ExtSvc[External Service]
    Pod2 --> ExtSvc

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Ingress,SVC k8sComponent;
    class Pod1,Pod2 userApp;
    class Client,ExtSvc default;
```

### CNI (Container Network Interface) Plugins

Kubernetes は CNI plugins を通じて networking を実装します。一般的な CNI plugins は次のとおりです。

1. **Calico**: network policy と security features を強化した CNI
2. **Flannel**: simple overlay networking を提供
3. **Cilium**: eBPF-based networking and security solution
4. **AWS VPC CNI**: AWS VPC と統合された CNI
5. **Weave Net**: multi-host container networking solution

#### CNI Plugin Installation and Configuration

CNI plugin installation example（Calico）:

```bash
# Install Calico
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Check Calico status
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Service Networking

Kubernetes services は pod sets に安定した endpoints を提供します。

1. **ClusterIP**: cluster 内でのみアクセス可能な Service
2. **NodePort**: すべての nodes の特定 port を通じてアクセス可能な Service
3. **LoadBalancer**: external load balancer を通じてアクセス可能な Service
4. **ExternalName**: external services の CNAME record を提供

#### Service CIDR Configuration

Service CIDR は service IP address range を定義します。

```bash
# Set service CIDR in kube-apiserver configuration
--service-cluster-ip-range=10.96.0.0/12
```

### CoreDNS Management

CoreDNS は Kubernetes に DNS services を提供します。

```bash
# Check CoreDNS status
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS configuration
kubectl get configmap -n kube-system coredns -o yaml
```

CoreDNS configuration example:

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

### Network Policies

Network policies は pods 間の通信を制御します。

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

上記の例では、`role=db` label を持つ pods は、`role=frontend` label を持つ pods からの TCP port 3306 inbound traffic と、`role=monitoring` label を持つ pods への TCP port 9090 outbound traffic のみを許可します。

## Authentication and Authorization Management

Kubernetes authentication and authorization management は、cluster security の core elements です。

次の図は、Kubernetes authentication and authorization flow を示しています。

```mermaid
flowchart TD
    User[User/Service Account] --> Auth[Authentication]
    Auth --> Authz[Authorization]
    Authz --> Admit[Admission Control]
    Admit --> API[API Server]

    subgraph "Authentication Methods"
        Cert[X.509 Certificates]
        Token[Service Account Tokens]
        OIDC[OpenID Connect]
        Webhook[Webhook Token Auth]
    end

    subgraph "Authorization Modes"
        RBAC[RBAC]
        ABAC[ABAC]
        Node[Node]
        WebhookAuthz[Webhook]
    end

    Auth --> Cert
    Auth --> Token
    Auth --> OIDC
    Auth --> Webhook

    Authz --> RBAC
    Authz --> ABAC
    Authz --> Node
    Authz --> WebhookAuthz

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Auth,Authz,Admit,API k8sComponent;
    class User userApp;
    class Cert,Token,OIDC,Webhook,RBAC,ABAC,Node,WebhookAuthz default;
```

### Authentication

Kubernetes はさまざまな authentication methods をサポートしています。

1. **X.509 Certificates**: client certificates を使用した authentication
2. **Service Account Tokens**: service accounts に関連付けられた JWT tokens
3. **OpenID Connect (OIDC)**: external identity providers を通じた authentication
4. **Webhook Token Authentication**: external services を通じた token verification
5. **Authentication Proxy**: authentication proxy を通じた request processing

#### X.509 Certificate Management

X.509 certificate の作成と管理です。

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

#### OIDC Authentication Configuration

OIDC authentication configuration example:

```bash
# Add OIDC flags to kube-apiserver configuration
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### Authorization

Kubernetes はさまざまな authorization modes をサポートしています。

1. **RBAC (Role-Based Access Control)**: role-based access control
2. **ABAC (Attribute-Based Access Control)**: attribute-based access control
3. **Node**: node authorization
4. **Webhook**: external services を通じた authorization

#### RBAC Configuration

RBAC は最も一般的な authorization mechanism です。

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

上記の例では、`user` は `default` namespace 内の pods を表示する権限を持ちます。

#### ClusterRole and ClusterRoleBinding

cluster-wide resources の permissions を管理します。

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

上記の例では、`user` は cluster 内のすべての nodes を表示する権限を持ちます。

### Service Account Management

Service accounts は pods が API server と通信するために使用されます。

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

Security context は pods と containers の permissions と access control を定義します。

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

上記の例では、pod は UID 1000 と GID 3000 で実行され、container は privilege escalation ができず、すべての Linux capabilities が drop され、root filesystem は read-only として mount されます。

## Cluster Upgrades

Kubernetes cluster upgrades は、新機能、performance improvements、security patches を適用するために必要です。

次の図は、Kubernetes cluster upgrade process を示しています。

```mermaid
flowchart TD
    Start[Upgrade Planning] --> Plan[Check Version Compatibility]
    Plan --> Backup[etcd Backup]
    Backup --> CP1[Upgrade First Control Plane Node]
    CP1 --> CPTest[Test Control Plane Functions]
    CPTest --> CP2[Upgrade Additional Control Plane Nodes]
    CP2 --> Worker[Upgrade Worker Nodes]
    Worker --> Validate[Cluster Validation]
    Validate --> End[Upgrade Complete]

    Validate -- Problem Occurs --> Rollback[Rollback]
    Rollback --> RestoreBackup[Restore from Backup]

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef alerting fill:#EB6E85,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class CP1,CP2,Worker,Validate k8sComponent;
    class Backup,RestoreBackup dataStore;
    class Rollback alerting;
    class Start,Plan,CPTest,End default;
```

### Upgrade Planning

cluster upgrades を計画する際の考慮事項です。

1. **Version Compatibility**: Kubernetes versions 間の compatibility を確認
2. **Upgrade Path**: supported upgrade paths を確認
3. **Downtime**: upgrade 中に想定される downtime を計画
4. **Rollback Plan**: 問題発生時の rollback plan を策定
5. **Application Impact**: upgrades が applications に与える影響を評価

### Control Plane Upgrade

kubeadm を使用した control plane upgrade です。

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

### Worker Node Upgrade

Worker node upgrade process です。

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

### Upgrade Verification

upgrade 後に cluster status を verify します。

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
## Backup and Recovery

Kubernetes cluster backup and recovery は、disaster recovery planning の重要な部分です。

次の図は、Kubernetes cluster backup and recovery process を示しています。

```mermaid
flowchart TD
    subgraph "Backup Process"
        Schedule[Set Backup Schedule] --> ETCDBackup[Create etcd Snapshot]
        Schedule --> ResourceBackup[Backup Resource YAMLs]
        ETCDBackup --> Store[Backup Storage]
        ResourceBackup --> Store
    end

    subgraph "Recovery Process"
        Disaster[Disaster Occurs] --> RestoreETCD[Restore etcd]
        RestoreETCD --> RestartServices[Restart Kubernetes Services]
        RestartServices --> ValidateCluster[Validate Cluster]
        ValidateCluster --> RestoreResources[Restore Resources]
    end

    Store -.-> RestoreETCD
    Store -.-> RestoreResources

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef alerting fill:#EB6E85,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class ETCDBackup,ResourceBackup,RestoreETCD,RestartServices,ValidateCluster,RestoreResources k8sComponent;
    class Store dataStore;
    class Disaster alerting;
    class Schedule default;
```

### etcd Backup

etcd は Kubernetes cluster のすべての state information を保存するため、regular backups が重要です。

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

### etcd Recovery

etcd snapshot から restore します。

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

### Resource Backup

Kubernetes resources を YAML files として backup します。

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

### Backup Automation

CronJob で backup tasks を自動化します。

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

## Monitoring and Logging

効果的な monitoring and logging は cluster administration の core element です。

次の図は、Kubernetes cluster monitoring and logging architecture を示しています。

```mermaid
flowchart LR
    subgraph "Monitoring Stack"
        Prom[Prometheus] --> Alert[Alertmanager]
        Prom --> Grafana[Grafana]
        KSM[kube-state-metrics] --> Prom
        NE[Node Exporter] --> Prom
        Alert --> Notify[Notification Channels]
    end

    subgraph "Logging Stack"
        Fluentd[Fluentd/Fluent Bit] --> ES[(Elasticsearch)]
        ES --> Kibana[Kibana]
        Fluentd --> Loki[(Loki)]
        Loki --> Grafana
    end

    subgraph "Kubernetes Cluster"
        API[API Server] --> KSM
        Node[Node] --> NE
        Pod[Pod] --> Fluentd
    end

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef prometheusComponent fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef grafana fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class API,Node,Pod k8sComponent;
    class ES,Loki dataStore;
    class Prom,Alert,KSM,NE prometheusComponent;
    class Grafana,Kibana grafana;
    class Fluentd,Notify default;
```

### Monitoring Tools

Kubernetes cluster monitoring の tools です。

1. **Prometheus**: metric collection and storage
2. **Grafana**: metric visualization
3. **Alertmanager**: alert management
4. **kube-state-metrics**: Kubernetes object metrics の生成
5. **metrics-server**: resource usage metrics の提供

#### Prometheus and Grafana Installation

Helm を使用して Prometheus と Grafana を install します。

```bash
# Add Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

#### Key Monitoring Metrics

monitoring すべき key metrics です。

1. **Node Metrics**: CPU、memory、disk、network usage
2. **Pod Metrics**: CPU、memory usage、restart count
3. **Container Metrics**: CPU、memory usage、filesystem usage
4. **API Server Metrics**: request latency、request count、error rate
5. **etcd Metrics**: disk I/O、leader changes、commit latency

### Logging Tools

Kubernetes cluster logging の tools です。

1. **Elasticsearch**: log storage and search
2. **Fluentd/Fluent Bit**: log collection and forwarding
3. **Kibana**: log visualization
4. **Loki**: log aggregation system
5. **Grafana**: log visualization

#### EFK (Elasticsearch, Fluentd, Kibana) Stack Installation

Helm を使用して EFK stack を install します。

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

#### Log Collection Configuration

Fluentd configuration example:

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

## Troubleshooting

Kubernetes cluster troubleshooting は cluster administration の重要な部分です。

### Pod Troubleshooting

Pod troubleshooting の commands です。

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

### Node Troubleshooting

Node troubleshooting の commands です。

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

### Networking Troubleshooting

networking troubleshooting の commands です。

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

### Control Plane Troubleshooting

control plane troubleshooting の commands です。

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

## Amazon EKS Cluster Administration

Amazon EKS は managed Kubernetes service であり、cluster administration の多くの側面を自動化します。

次の図は、Amazon EKS cluster architecture と management components を示しています。

```mermaid
flowchart TD
    User[User] --> |Manage| AWS[AWS Management Console/CLI/API]
    AWS --> |Manage| EKS[Amazon EKS]

    subgraph "AWS Cloud"
        EKS --> CP[EKS Control Plane]
        EKS --> NG[EKS Node Groups]
        EKS --> Fargate[EKS Fargate]

        CP --> |Uses| AWSIAM[AWS IAM]
        CP --> |Uses| AWSVPC[AWS VPC]
        CP --> |Logging| CW[CloudWatch]

        NG --> |Uses| EC2[EC2 Instances]
        Fargate --> |Uses| FargateProfile[Fargate Profiles]
    end

    subgraph "Add-ons"
        EKS --> CNI[Amazon VPC CNI]
        EKS --> CoreDNS[CoreDNS]
        EKS --> KubeProxy[kube-proxy]
    end

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class CP,NG,Fargate,CNI,CoreDNS,KubeProxy k8sComponent;
    class AWS,EKS,AWSIAM,AWSVPC,CW,EC2,FargateProfile awsService;
    class User userApp;
```

### EKS Cluster Configuration

EKS cluster configuration management です。

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

### EKS Node Group Management

EKS node group management です。

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

### EKS Add-on Management

EKS add-on management です。

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

### EKS Cluster Upgrade

EKS cluster upgrade process です。

1. **Control Plane Upgrade**:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version 1.22
   ```

2. **Add-on Upgrade**:
   ```bash
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.10.2-eksbuild.1
   ```

3. **Node Group Upgrade**:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

### EKS Cluster Monitoring

EKS cluster monitoring tools です。

1. **Amazon CloudWatch**: metrics、logs、alerts
2. **AWS CloudTrail**: API call logging
3. **Amazon Managed Grafana**: metric visualization
4. **Amazon Managed Service for Prometheus**: metric collection and storage

CloudWatch Container Insights を enable にします。

```bash
# Enable Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## Cluster Administration Best Practices

Kubernetes と EKS cluster administration の best practices です。

### Cluster Configuration Best Practices

1. **Infrastructure as Code (IaC)**: Terraform、AWS CDK、eksctl などを使用して cluster configuration を管理
2. **Version Control**: cluster configuration を version control systems に保存
3. **Multiple Environments**: development、staging、production environments を分離
4. **Network Separation**: 適切な network separation と security groups を設定
5. **Least Privilege Principle**: 必要最小限の permissions のみを付与

### Operations Best Practices

1. **Regular Backups**: etcd と重要な resources の regular backup
2. **Monitoring and Alerting**: comprehensive monitoring and alerting systems を構築
3. **Centralized Logging**: logs を一元化して分析
4. **Automation**: repetitive tasks を自動化
5. **Disaster Recovery Planning**: 明確な disaster recovery plans を策定し、test する

### Security Best Practices

1. **Regular Updates**: cluster と nodes の regular updates
2. **Network Policies**: 適切な network policies を設定
3. **Encryption**: data at rest と data in transit を暗号化
4. **Security Context**: 適切な security contexts を設定
5. **Image Scanning**: container images の vulnerabilities を scan

### Resource Management Best Practices

1. **Resource Requests and Limits**: すべての pods に適切な resource requests と limits を設定
2. **Namespace Separation**: workloads を namespace ごとに分離
3. **Resource Quotas**: namespace ごとに resource quotas を設定
4. **HPA and VPA**: autoscaling を設定
5. **Node Affinity and Taints**: workload placement を最適化

### EKS-Specific Best Practices

1. **Managed Node Groups**: 可能な場合は managed node groups を使用
2. **Fargate**: serverless workloads には Fargate を使用
3. **EKS Add-ons**: official EKS add-ons を使用
4. **IAM Roles for Service Accounts (IRSA)**: pod ごとに IAM permissions を管理
5. **VPC CNI Customization**: networking requirements に応じて VPC CNI を設定

## Conclusion

Kubernetes cluster administration は、cluster の安定性、security、performance を維持するうえで重要な役割を果たします。この章では、cluster component management、resource management、networking、authentication and authorization management、upgrades、backup and recovery、monitoring and logging、troubleshooting など、cluster administration のさまざまな側面を扱いました。

Amazon EKS を使用すると、Kubernetes control plane management の複雑さが軽減され、AWS services との統合によって cluster administration が簡素化されます。ただし、効果的な cluster management のためには、基本的な Kubernetes concepts と best practices を理解することが依然として重要です。

Cluster administration は、cluster requirements と workload characteristics に応じて継続的に調整する必要がある ongoing process です。monitoring tools を使用して cluster status を追跡し、automation によって repetitive tasks を最小化し、best practices に従って cluster stability と security を維持することが重要です。

## Cluster Networking

Kubernetes cluster networking は、pod-to-pod communication、service discovery、external access を管理します。

### Network Architecture

```mermaid
graph TD
    A[Cluster Networking] --> B[Pod Network]
    A --> C[Service Network]
    A --> D[Ingress]
    A --> E[Network Policies]

    B --> F[CNI Plugin]
    C --> G[ClusterIP, NodePort, LoadBalancer]
    D --> H[Ingress Controller]
    E --> I[Network Security]

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef networkComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E k8sComponent;
    class F,G,H,I networkComponent;
```

### CNI Plugin Management

CNI (Container Network Interface) plugins は Kubernetes clusters の networking を処理します。

```bash
# Install Calico CNI
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Install Flannel CNI
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml

# Install Cilium CNI (using Helm)
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.14.0 --namespace kube-system
```

### CNI Plugin Comparison

| CNI Plugin | Network Model | Network Policy Support | Performance | Features |
|-----------|---------------|----------------------|-------------|----------|
| **Calico** | BGP | Yes | High | network policies と routing-based に強い |
| **Flannel** | VXLAN/host-gateway | No | Medium | simple setup、限定的な features |
| **Cilium** | eBPF | Yes | Very High | L3-L7 policies、高い performance |
| **Weave Net** | VXLAN | Yes | Medium | encryption support、multi-cluster |
| **AWS VPC CNI** | AWS VPC | No | High | AWS EKS 向けに最適化 |

### Network Troubleshooting

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
## Authentication and Authorization Management

Kubernetes authentication and authorization management は cluster security の core elements です。RBAC (Role-Based Access Control) は users と service accounts の permissions を管理するために使用されます。

### Authentication Methods

Kubernetes はさまざまな authentication methods をサポートしています。

1. **X.509 Certificates**: client certificates を使用した authentication
2. **Service Account Tokens**: pods 内から API server access に使用
3. **OpenID Connect (OIDC)**: external identity providers との integration
4. **Webhook Token Authentication**: external authentication services との integration
5. **Authentication Proxy**: proxy を通じた authentication

### RBAC Configuration

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

### User Certificate Creation

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

### Service Account Management

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

### Permission Verification

```bash
# Check user permissions
kubectl auth can-i get pods --as jane

# Check permissions in a specific namespace
kubectl auth can-i create deployments --as jane --namespace production
```
## Cluster Upgrades

Kubernetes cluster upgrades は、新機能、security patches、bug fixes を適用するために必要です。Upgrades は慎重に計画し、実行する必要があります。

### Upgrade Planning

```mermaid
graph TD
    A[Upgrade Planning] --> B[Check Version Compatibility]
    A --> C[Create Backup]
    A --> D[Choose Upgrade Strategy]
    A --> E[Plan Downtime]

    B --> F[Review API Changes]
    C --> G[etcd Backup]
    D --> H[In-place vs Blue/Green]
    E --> I[User Communication]

    classDef planning fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef action fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E planning;
    class F,G,H,I action;
```

### Upgrade Strategy Comparison

| Strategy | Description | Advantages | Disadvantages | Suitable Environment |
|----------|-------------|------------|---------------|---------------------|
| **In-place Upgrade** | existing cluster を直接 upgrade | resource efficient、手順が simple | rollback が複雑、downtime の可能性 | development、test environments |
| **Blue/Green Deployment** | 新しい version の cluster を作成して切り替え | safe rollback、検証可能 | resource duplication、cost 増加 | production environments |
| **Canary Deployment** | 一部の workloads のみを新 cluster に移動 | gradual verification、risk 低減 | management が複雑、dual operation | critical production environments |

### Upgrade Using kubeadm

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

### Post-Upgrade Verification

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
## Backup and Recovery

Kubernetes cluster backup and recovery は、disaster recovery planning の重要な部分です。主な backup targets は etcd database、persistent volume data、Kubernetes resource definitions です。

### etcd Backup and Recovery

etcd は cluster のすべての state information を保存する core component です。

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

### Kubernetes Resource Backup

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

### Backup and Recovery Using Velero

Velero は、Kubernetes cluster resources と persistent volumes を backup および recovery するための tool です。

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

### Backup Strategy Comparison

| Backup Method | Backup Target | Advantages | Disadvantages | Recovery Time |
|--------------|---------------|------------|---------------|---------------|
| **etcd Snapshot** | Cluster state | built-in feature、complete state preservation | volume data は含まれない、manual process | Medium |
| **Resource YAML Backup** | Kubernetes objects | simple implementation、selective restore | volume data は含まれない、relationship complexity | Slow |
| **Velero** | Resources and volumes | automation、scheduling、volume snapshots | additional tool installation が必要 | Fast |
| **Cloud Provider Snapshots** | Entire cluster | complete recovery、cloud integration | cloud dependency、cost | Very Fast |
## Monitoring and Logging

効果的な cluster management には、comprehensive monitoring and logging system が必要です。これにより、問題を早期に検出して解決できます。

### Monitoring Architecture

```mermaid
graph TD
    A[Kubernetes Monitoring] --> B[Metric Collection]
    A --> C[Log Collection]
    A --> D[Alerting]
    A --> E[Visualization]

    B --> F[Prometheus]
    C --> G[Fluentd/Fluent Bit]
    D --> H[Alertmanager]
    E --> I[Grafana]

    F --> J[kube-state-metrics]
    F --> K[node-exporter]
    G --> L[Elasticsearch]
    L --> M[Kibana]

    classDef monitoring fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef component fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E monitoring;
    class F,G,H,I,J,K,L,M component;
```

### Prometheus and Grafana Installation

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

### EFK Stack Installation (Elasticsearch, Fluentd, Kibana)

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

### Key Monitoring Metrics

| Metric Type | Description | Key Metrics | Monitoring Tools |
|-------------|-------------|-------------|-----------------|
| **Node Metrics** | Node-level resource usage | CPU、memory、disk、network | node-exporter、Prometheus |
| **Pod Metrics** | Container resource usage | CPU、memory usage、limits | cAdvisor、Prometheus |
| **Cluster Metrics** | Cluster state and resources | Pod count、node status、events | kube-state-metrics |
| **Application Metrics** | Custom application metrics | Request count、latency、error rate | Prometheus client libraries |

### Log Collection and Analysis

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

### Alert Configuration

Prometheus Alertmanager を使用して alerts を設定できます。

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
## Troubleshooting

Kubernetes cluster troubleshooting は、system administrators と operators にとって重要な skill です。効果的な troubleshooting には systematic approach が必要です。

### Troubleshooting Methodology

```mermaid
graph TD
    A[Problem Identification] --> B[Information Gathering]
    B --> C[Root Cause Analysis]
    C --> D[Apply Solution]
    D --> E[Verification]
    E --> F[Documentation]

    B --> G[Check Logs]
    B --> H[Check Events]
    B --> I[Check Resource Status]

    classDef process fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef action fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E,F process;
    class G,H,I action;
```

### Common Problems and Solutions

| Problem Type | Symptoms | Diagnostic Commands | Common Solutions |
|-------------|----------|---------------------|-----------------|
| **Pod Not Starting** | Pod が Pending または ContainerCreating state | `kubectl describe pod <pod-name>` | resource constraints、image availability、volume mounts を確認 |
| **Service Connection Issues** | service 経由で pods にアクセスできない | `kubectl describe svc <service-name>`、`kubectl get endpoints <service-name>` | label selectors、pod status、network policies を確認 |
| **Node Issues** | Node が NotReady state | `kubectl describe node <node-name>`、`kubectl get events` | kubelet status、system resources、network connectivity を確認 |
| **DNS Issues** | service name で接続できない | `kubectl exec -it <pod-name> -- nslookup kubernetes.default` | CoreDNS pods、kube-dns service、network policies を確認 |
| **Authentication Issues** | API server access denied | `kubectl auth can-i <verb> <resource>` | RBAC settings、certificate validity、service account を確認 |

### Pod Troubleshooting

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

### Node Troubleshooting

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

### Networking Troubleshooting

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
## Amazon EKS Cluster Administration

Amazon EKS (Elastic Kubernetes Service) は、AWS が control plane を管理する AWS 上の managed Kubernetes service です。ただし、nodes、networking、security などの管理は user の責任です。

### EKS Cluster Architecture

```mermaid
graph TD
    A[Amazon EKS Cluster] --> B[Control Plane]
    A --> C[Data Plane]
    A --> D[Networking]
    A --> E[Security]

    B --> F[AWS Managed Components]
    C --> G[Managed Node Groups]
    C --> H[Self-Managed Nodes]
    C --> I[Fargate]
    D --> J[VPC CNI]
    E --> K[IAM Authentication]

    F --> L[API Server, etcd, Scheduler]
    G --> M[EC2 Auto Scaling Groups]
    J --> N[AWS VPC]
    K --> O[IAM Roles and Policies]

    classDef awsManaged fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef userManaged fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef network fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,F,L awsManaged;
    class C,G,H,I,E,K,O userManaged;
    class D,J,N network;
```

### EKS Cluster Creation

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

### Node Group Management

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

### EKS Cluster Upgrade

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

### EKS Cluster Authentication and Authorization

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

### EKS Cluster Monitoring

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
## Cluster Administration Best Practices

効果的な Kubernetes cluster management の best practices は、stability、security、performance を確保するために重要です。

### Cluster Setup Best Practices

1. **Multi-Availability Zone Configuration**: high availability のために nodes を複数の availability zones に分散
2. **Appropriate Sizing**: workloads に適した node types と counts を選択
3. **Autoscaling Configuration**: cluster autoscaler と horizontal pod autoscaler を有効化
4. **Apply Network Policies**: default deny policy から開始し、必要な communication のみを許可
5. **Set Resource Quotas**: namespace ごとに resource limits を設定

### Operations Best Practices

1. **Use Declarative Configuration**: すべての resources を YAML files として定義し、version control する
2. **Adopt GitOps**: Git を single source of truth として使用し、automated deployment pipelines を構築
3. **Regular Backups**: etcd data と persistent volume data の regular backup
4. **Monitoring and Alerting**: comprehensive monitoring systems を構築し、key metrics に alerts を設定
5. **Centralized Logging**: 分析しやすいよう、すべての logs を central logging system に収集

### Security Best Practices

1. **Least Privilege Principle**: RBAC を使用して必要最小限の permissions のみを付与
2. **Network Segmentation**: network policies を使用して pod-to-pod communication を制限
3. **Image Scanning**: vulnerability detection のために container image scanning を実装
4. **Secret Management**: external secret management tools（例: AWS Secrets Manager、HashiCorp Vault）を使用
5. **Regular Security Audits**: cluster configuration と permissions の regular audits を実施

### Upgrade Best Practices

1. **Gradual Upgrades**: 一度にすべてではなく段階的に upgrade
2. **Test Environment First**: production の前に test environments で upgrades を検証
3. **Create Backups**: upgrades 前に full backups を実行
4. **Rollback Plan**: 問題発生時に previous versions へ rollback する計画を策定
5. **Set Upgrade Windows**: usage が少ない時間帯に upgrades を実施

### Cost Optimization Best Practices

1. **Select Appropriate Node Sizes**: workloads に最適な node types を選択
2. **Utilize Spot Instances**: non-critical workloads には spot instances を使用
3. **Configure Autoscaling**: demand に基づいて自動的な scale up/down を設定
4. **Optimize Resource Requests and Limits**: actual usage に基づいて resource requests と limits を設定
5. **Identify Idle Resources**: idle resources を定期的に特定し削除

### Documentation Best Practices

1. **Document Architecture**: cluster architecture、networking、security settings を document 化
2. **Document Operations Procedures**: common operations tasks、troubleshooting procedures、emergency response plans を document 化
3. **Change Management**: すべての cluster changes を記録し追跡
4. **Create Runbooks**: common scenarios 向けの step-by-step guides を提供
5. **Knowledge Sharing**: team 内で regular knowledge sharing と training sessions を実施
## Conclusion

Kubernetes cluster administration は、さまざまな側面を含む複雑な task です。cluster setup から operation、monitoring、troubleshooting、upgrades まで、systematic approach が必要です。

効果的な cluster administration のために、次の key areas に注力してください。

1. **Cluster Component Management**: control plane と node components の安定運用
2. **Resource Management**: 効率的な resource allocation と usage
3. **Networking**: secure で効率的な network configuration
4. **Security**: 適切な authentication and authorization management
5. **Backup and Recovery**: data loss prevention と disaster recovery planning
6. **Monitoring and Logging**: cluster status と performance monitoring
7. **Troubleshooting**: systematic troubleshooting approach

Amazon EKS のような managed Kubernetes services を使用する場合、service provider と user の shared responsibility model を理解することが重要です。AWS が control plane を管理する一方で、nodes、networking、security などの管理は引き続き user の責任です。

best practices に従い、適切な tools を活用することで、stable、secure、efficient な Kubernetes cluster を運用できます。cluster management capabilities を高めるための continuous learning and improvement が重要です。

---

> **References**:
> - [Kubernetes Official Documentation: Cluster Administration](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Kubernetes Best Practices: Cluster Administration](https://kubernetes.io/docs/setup/best-practices/)
> - [etcd Documentation: Backup and Recovery](https://etcd.io/docs/v3.5/op-guide/recovery/)
> - [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)

## Quiz

この章で学んだ内容を確認するため、[Cluster Administration Quiz](../quizzes/core/09-cluster-administration-quiz.md) に挑戦してみてください。
