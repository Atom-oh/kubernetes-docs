# WorkloadEntry

> **対応バージョン**: Istio 1.28+
> **最終更新**: February 19, 2026

WorkloadEntry は、Virtual Machine（VM）またはベアメタルサーバーを Istio service mesh に登録するためのリソースです。これにより、Kubernetes 外部のワークロードでも、mesh のトラフィック管理、セキュリティ、可観測性機能を利用できます。

## 目次

1. [概要](#overview)
2. [WorkloadEntry と Kubernetes Pod](#workloadentry-vs-kubernetes-pod)
3. [アーキテクチャ](#architecture)
4. [基本的な使用方法](#basic-usage)
5. [ServiceEntry との統合](#serviceentry-integration)
6. [VM 登録の実践ガイド](#vm-registration-practical-guide)
7. [セキュリティ設定（mTLS）](#security-settings-mtls)
8. [ヘルスチェックとモニタリング](#health-checks-and-monitoring)
9. [高度な設定](#advanced-configuration)
10. [トラブルシューティング](#troubleshooting)
11. [ベストプラクティス](#best-practices)

## 概要

### WorkloadEntry とは？

WorkloadEntry は、mesh 外部のワークロード（VM、ベアメタル）を Istio service mesh に登録する Istio Custom Resource Definition（CRD）です。

### ユースケース

```mermaid
flowchart TB
    subgraph Legacy[Legacy Environment]
        VM1[VM<br/>Legacy App]
        VM2[VM<br/>Database]
        BM[Bare Metal<br/>High-Performance Server]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod1[Pod]
            App1[New App]
            Envoy1[Envoy]
        end

        subgraph Pod2[Pod]
            App2[Microservice]
            Envoy2[Envoy]
        end
    end

    subgraph Istiod[Control Plane]
        CP[istiod]
    end

    VM1 -.->|Mesh Registration| CP
    VM2 -.->|Mesh Registration| CP
    BM -.->|Mesh Registration| CP

    CP -.->|Config Delivery| Envoy1
    CP -.->|Config Delivery| Envoy2

    App1 <-->|mTLS| VM1
    App2 <-->|mTLS| VM2

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,BM vm;
    class App1,App2 k8sApp;
    class Envoy1,Envoy2 proxy;
    class CP controlPlane;
```

**主なユースケース**:
1. **段階的な移行**: レガシーアプリケーションを Kubernetes に段階的に移行
2. **ハイブリッドアーキテクチャ**: VM とコンテナを同時に運用
3. **データベース統合**: 外部データベースを mesh に組み込む
4. **高性能ワークロード**: GPU サーバーなどの専用ハードウェアを活用

## WorkloadEntry と Kubernetes Pod

### 比較表

| 特性 | Kubernetes Pod | WorkloadEntry (VM) |
|----------------|---------------|-------------------|
| **デプロイ場所** | クラスタ内部 | クラスタ外部 |
| **Envoy 注入** | 自動（sidecar） | 手動インストール |
| **Service ディスカバリ** | 自動（Service） | 手動（WorkloadEntry） |
| **IP 管理** | Kubernetes CNI | 手動指定 |
| **mTLS** | 自動 | 自動（証明書のデプロイが必要） |
| **ヘルスチェック** | 自動（Liveness/Readiness） | 手動設定 |
| **スケーリング** | HPA | 手動 |
| **運用の複雑さ** | 低 | 高 |
| **ユースケース** | クラウドネイティブアプリ | レガシーアプリ、専用ハードウェア |

### トラフィックフローの比較

```mermaid
flowchart LR
    subgraph PodFlow[Kubernetes Pod Flow]
        Client1[Client]
        K8sService[Service<br/>Auto Discovery]
        K8sPod[Pod<br/>Auto Envoy Injection]

        Client1 -->|1\. Request| K8sService
        K8sService -->|2\. Routing| K8sPod
    end

    subgraph VMFlow[WorkloadEntry Flow]
        Client2[Client]
        ServiceEntry[ServiceEntry<br/>Manual Registration]
        WorkloadEntry[WorkloadEntry<br/>VM + Envoy]

        Client2 -->|1\. Request| ServiceEntry
        ServiceEntry -->|2\. Routing| WorkloadEntry
    end

    %% Style definitions
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef k8s fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Client1,Client2 client;
    class K8sService,K8sPod k8s;
    class ServiceEntry,WorkloadEntry vm;
```

## アーキテクチャ

### VM ワークロードのアーキテクチャ

```mermaid
flowchart TB
    subgraph VM[Virtual Machine]
        App[Legacy<br/>Application<br/>Port 8080]
        EnvoyVM[Envoy Sidecar<br/>Manual Install]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod[Pod]
            PodApp[Application]
            EnvoyPod[Envoy<br/>Auto Injection]
        end

        Istiod[istiod<br/>Control Plane]
    end

    App <-->|Local Communication| EnvoyVM
    PodApp <-->|Local Communication| EnvoyPod

    EnvoyVM <-->|mTLS Traffic| EnvoyPod

    Istiod -.->|xDS Config<br/>ServiceEntry<br/>DestinationRule| EnvoyVM
    Istiod -.->|xDS Config| EnvoyPod
    Istiod -.->|Certificate Issuance<br/>Service Account| EnvoyVM

    %% Style definitions
    classDef vmApp fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App vmApp;
    class PodApp k8sApp;
    class EnvoyVM,EnvoyPod proxy;
    class Istiod controlPlane;
```

### 主要コンポーネント

1. **WorkloadEntry**: VM 情報の登録（IP、ポート、ラベル）
2. **ServiceEntry**: Service 定義と WorkloadEntry の参照
3. **Envoy Proxy**: VM に手動でインストールする sidecar
4. **istiod**: 設定の配布と証明書管理
5. **Service Account**: VM のアイデンティティ認証

## 基本的な使用方法

### WorkloadEntry リソース定義

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-api-vm-1
  namespace: production
spec:
  # VM's IP address
  address: 192.168.1.100

  # Labels for service selection
  labels:
    app: legacy-api
    version: v1.0
    tier: backend

  # Service account for mTLS authentication
  serviceAccount: legacy-api-sa

  # Ports to expose
  ports:
    http: 8080
    https: 8443
    metrics: 9090

  # Locality information (optional)
  locality: us-west-2/us-west-2a

  # Weight (for load balancing, optional)
  weight: 100

  # Network (multi-network environment, optional)
  network: vm-network
```

### 必須フィールドの説明

| フィールド | 説明 | 例 |
|-------|-------------|---------|
| **address** | VM の IP アドレス（必須） | `192.168.1.100` |
| **labels** | ServiceEntry のマッチング用ラベル | `app: legacy-api` |
| **serviceAccount** | mTLS 認証用の SA | `legacy-api-sa` |
| **ports** | 公開するポートマップ | `http: 8080` |

### 複数 VM の登録

```yaml
# VM 1
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-1
  namespace: production
spec:
  address: 192.168.1.101
  labels:
    app: api-service
    version: v1
  serviceAccount: api-sa
  ports:
    http: 8080
---
# VM 2
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-2
  namespace: production
spec:
  address: 192.168.1.102
  labels:
    app: api-service
    version: v1
  serviceAccount: api-sa
  ports:
    http: 8080
---
# VM 3 (different version)
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-3
  namespace: production
spec:
  address: 192.168.1.103
  labels:
    app: api-service
    version: v2  # New version
  serviceAccount: api-sa
  ports:
    http: 8080
```

## ServiceEntry との統合

WorkloadEntry は常に ServiceEntry とともに使用します。

### 基本的な統合パターン

```yaml
# 1. Define service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-api
  namespace: production
spec:
  hosts:
  - api.legacy.internal
  addresses:
  - 240.240.1.1  # Virtual IP
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: legacy-api  # Match with WorkloadEntry labels
---
# 2. Register VM with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-api-vm-1
  namespace: production
spec:
  address: 192.168.1.100
  labels:
    app: legacy-api  # Match with ServiceEntry
    version: v1
  serviceAccount: legacy-api-sa
  ports:
    http: 8080
```

### 操作フロー

```mermaid
sequenceDiagram
    autonumber
    participant Client as Kubernetes<br/>Pod
    participant DNS as Istio DNS
    participant Envoy as Envoy Proxy
    participant VM as VM<br/>WorkloadEntry

    Client->>DNS: Lookup api.legacy.internal
    DNS->>Client: 240.240.1.1 (Virtual IP)

    Client->>Envoy: HTTP Request<br/>240.240.1.1:8080
    Envoy->>Envoy: Lookup ServiceEntry<br/>workloadSelector matching
    Envoy->>Envoy: Find WorkloadEntry<br/>192.168.1.100

    Envoy->>VM: mTLS Connection<br/>192.168.1.100:8080
    VM->>Envoy: Response
    Envoy->>Client: Response
```

### ロードバランシング

複数の WorkloadEntry が存在する場合は、自動的にロードバランシングされます。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: database-cluster
spec:
  hosts:
  - db.cluster.internal
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
      tier: database
---
# Primary DB
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-primary
spec:
  address: 10.0.1.100
  labels:
    app: postgres
    tier: database
    role: primary
  weight: 100  # Weight
---
# Replica DB 1
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-replica-1
spec:
  address: 10.0.1.101
  labels:
    app: postgres
    tier: database
    role: replica
  weight: 50
---
# Replica DB 2
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-replica-2
spec:
  address: 10.0.1.102
  labels:
    app: postgres
    tier: database
    role: replica
  weight: 50
```

## VM 登録の実践ガイド

### 前提条件

1. **VM の要件**:
   - ネットワーク: Kubernetes クラスタと通信できること
   - OS: Linux（Ubuntu 20.04+ を推奨）
   - ポート: Envoy ポートが開放されていること（15012、15017 など）

2. **Kubernetes の準備**:
   - Istio のインストールが完了していること
   - VM 用の namespace を作成すること
   - ServiceAccount を作成すること

### ステップ 1: ServiceAccount の作成

```bash
# Create namespace
kubectl create namespace vm-workloads

# Create ServiceAccount
kubectl create serviceaccount vm-postgres-sa -n vm-workloads

# (Optional) RBAC setup
kubectl create role vm-postgres-role \
  --verb=get,list,watch \
  --resource=configmaps,secrets \
  -n vm-workloads

kubectl create rolebinding vm-postgres-binding \
  --role=vm-postgres-role \
  --serviceaccount=vm-workloads:vm-postgres-sa \
  -n vm-workloads
```

### ステップ 2: WorkloadGroup の作成（任意）

WorkloadGroup は複数の WorkloadEntry のテンプレートとして機能します。

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadGroup
metadata:
  name: postgres-vms
  namespace: vm-workloads
spec:
  metadata:
    labels:
      app: postgres
      version: v14
  template:
    serviceAccount: vm-postgres-sa
    network: vm-network
    ports:
      postgresql: 5432
```

### ステップ 3: VM への Envoy のインストール

#### 自動インストールスクリプトの生成

```bash
# Generate VM registration files with istioctl
istioctl x workload entry configure \
  -f workloadgroup.yaml \
  -o vm-postgres-1 \
  --clusterID Kubernetes \
  --autoregister

# Generated files:
# - cluster.env: Cluster information
# - istio-token: Authentication token
# - mesh.yaml: Mesh configuration
# - root-cert.pem: Root certificate
# - hosts: /etc/hosts entries
```

#### VM でのインストールの実行

```bash
# Connect to VM
ssh user@192.168.1.100

# Copy files (using SCP)
scp -r vm-postgres-1/* user@192.168.1.100:/tmp/

# Install Envoy on VM
sudo apt-get update
sudo apt-get install -y curl

# Install Istio sidecar
curl -LO https://storage.googleapis.com/istio-release/releases/1.28.0/deb/istio-sidecar.deb
sudo dpkg -i istio-sidecar.deb

# Place configuration files
sudo mkdir -p /etc/certs
sudo cp /tmp/root-cert.pem /etc/certs/
sudo cp /tmp/istio-token /var/run/secrets/tokens/
sudo cp /tmp/cluster.env /var/lib/istio/envoy/
sudo cp /tmp/mesh.yaml /etc/istio/config/mesh

# Start Envoy
sudo systemctl start istio
sudo systemctl enable istio

# Check status
sudo systemctl status istio
```

### ステップ 4: WorkloadEntry の登録

自動登録が有効な場合、Envoy の起動時に自動で作成されます。手動登録する場合:

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
  namespace: vm-workloads
spec:
  address: 192.168.1.100
  labels:
    app: postgres
    version: v14
  serviceAccount: vm-postgres-sa
  ports:
    postgresql: 5432
```

```bash
kubectl apply -f workloadentry.yaml
```

### ステップ 5: ServiceEntry の作成

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: postgres-service
  namespace: vm-workloads
spec:
  hosts:
  - postgres.vm.internal
  addresses:
  - 240.240.2.1
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
```

```bash
kubectl apply -f serviceentry.yaml
```

### ステップ 6: 接続のテスト

```bash
# Create test pod
kubectl run -it --rm debug \
  --image=postgres:14 \
  --restart=Never \
  --namespace=vm-workloads \
  -- psql -h postgres.vm.internal -U dbuser -d mydb

# On successful connection:
# Password for user dbuser:
# psql (14.x)
# Type "help" for help.
# mydb=#
```

## セキュリティ設定（mTLS）

### mTLS の自動有効化

WorkloadEntry は mTLS を自動的にサポートします。

```yaml
# Force mTLS with PeerAuthentication
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: vm-workloads
spec:
  mtls:
    mode: STRICT  # mTLS required for both VM and pod
```

### VM アイデンティティの検証

```bash
# Check certificates on VM
sudo ls -la /etc/certs/
# cert-chain.pem: Certificate chain
# key.pem: Private key
# root-cert.pem: Root CA

# Check certificate contents
sudo openssl x509 -in /etc/certs/cert-chain.pem -text -noout

# Check Subject Alternative Name (SAN):
# spiffe://cluster.local/ns/vm-workloads/sa/vm-postgres-sa
```

### アクセス制御（AuthorizationPolicy）

```yaml
# PostgreSQL access control
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: postgres-access
  namespace: vm-workloads
spec:
  selector:
    matchLabels:
      app: postgres  # WorkloadEntry labels
  action: ALLOW
  rules:
  # Allow only API service access
  - from:
    - source:
        principals:
        - cluster.local/ns/production/sa/api-service-sa
    to:
    - operation:
        ports: ["5432"]
        methods: ["*"]

  # Allow monitoring service access
  - from:
    - source:
        principals:
        - cluster.local/ns/istio-system/sa/prometheus
    to:
    - operation:
        ports: ["9187"]  # postgres_exporter
```

### mTLS の検証

```bash
# Test connection from pod to VM
kubectl exec -it <pod-name> -n production -- \
  curl -v --cacert /etc/certs/root-cert.pem \
  --cert /etc/certs/cert-chain.pem \
  --key /etc/certs/key.pem \
  https://postgres.vm.internal:5432

# Verify mTLS with Envoy stats
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats | grep ssl

# Example output:
# listener.0.0.0.0_15006.ssl.connection_error: 0
# listener.0.0.0.0_15006.ssl.handshake: 1234
```

## ヘルスチェックとモニタリング

### ヘルスチェックの設定

WorkloadEntry は自動ヘルスチェックをサポートしていないため、手動設定が必要です。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: postgres-healthcheck
  namespace: vm-workloads
spec:
  host: postgres.vm.internal
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
    outlierDetection:
      consecutiveErrors: 5  # Exclude after 5 consecutive failures
      interval: 30s         # Check every 30 seconds
      baseEjectionTime: 30s # Exclude for 30 seconds
      maxEjectionPercent: 50 # Exclude up to 50%
      minHealthPercent: 50   # Maintain at least 50%
```

### VM ヘルスチェックエンドポイント

VM アプリケーションにヘルスチェックエンドポイントを追加します。

```python
# Python Flask example
from flask import Flask, jsonify
import psycopg2

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    try:
        # Verify database connection
        conn = psycopg2.connect("dbname=mydb user=dbuser")
        conn.close()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### Prometheus メトリクスの収集

```yaml
# Collect VM metrics with ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-vm-metrics
  namespace: vm-workloads
spec:
  selector:
    matchLabels:
      app: postgres
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

### Grafana ダッシュボードクエリ

```promql
# VM workload request count
sum(rate(istio_requests_total{destination_workload="postgres-vm-1"}[5m]))

# VM workload error rate
sum(rate(istio_requests_total{destination_workload="postgres-vm-1",response_code="500"}[5m]))
/
sum(rate(istio_requests_total{destination_workload="postgres-vm-1"}[5m]))
* 100

# VM workload latency (P99)
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket{destination_workload="postgres-vm-1"}[5m])) by (le)
)
```

## 高度な設定

### マルチネットワーク環境

異なるネットワークの VM を登録します。

```yaml
# VM in Network A
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-network-a
spec:
  address: 192.168.1.100
  labels:
    app: api-service
  serviceAccount: api-sa
  network: network-a
  ports:
    http: 8080
---
# VM in Network B
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-network-b
spec:
  address: 10.0.1.100
  labels:
    app: api-service
  serviceAccount: api-sa
  network: network-b
  ports:
    http: 8080
```

### ローカリティ対応ロードバランシング

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-us-west
spec:
  address: 192.168.1.100
  labels:
    app: api-service
  locality: us-west/us-west-2/us-west-2a
  weight: 100
---
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-us-east
spec:
  address: 10.0.1.100
  labels:
    app: api-service
  locality: us-east/us-east-1/us-east-1a
  weight: 100
---
# Locality-aware routing with DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-locality-lb
spec:
  host: api.service.internal
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-west/*
          to:
            "us-west/*": 80
            "us-east/*": 20
        - from: us-east/*
          to:
            "us-east/*": 80
            "us-west/*": 20
```

### Canary Deployment

Canary deployment は WorkloadEntry にも適用できます。

```yaml
# v1 version VM
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-v1
spec:
  address: 192.168.1.100
  labels:
    app: api-service
    version: v1
  serviceAccount: api-sa
---
# v2 version VM (Canary)
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-v2
spec:
  address: 192.168.1.101
  labels:
    app: api-service
    version: v2
  serviceAccount: api-sa
---
# Traffic splitting with VirtualService
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-canary
spec:
  hosts:
  - api.service.internal
  http:
  - route:
    - destination:
        host: api.service.internal
        subset: v1
      weight: 90
    - destination:
        host: api.service.internal
        subset: v2
      weight: 10
---
# Define subsets with DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-subsets
spec:
  host: api.service.internal
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## トラブルシューティング

### WorkloadEntry が登録されない

**症状**: `kubectl get workloadentry` でリソースは表示されるが、トラフィックがルーティングされない

**確認**:

```bash
# 1. Check WorkloadEntry status
kubectl get workloadentry -n vm-workloads -o yaml

# 2. Check ServiceEntry's workloadSelector
kubectl get serviceentry -n vm-workloads -o yaml | grep -A 5 workloadSelector

# 3. Verify label matching
# WorkloadEntry labels:
#   app: postgres
# ServiceEntry workloadSelector:
#   labels:
#     app: postgres  # Must match

# 4. Check Envoy configuration
istioctl proxy-config endpoints <pod-name> -n production

# Output should include WorkloadEntry's IP:
# ENDPOINT            STATUS      CLUSTER
# 192.168.1.100:5432  HEALTHY     outbound|5432||postgres.vm.internal
```

**解決策**:

```yaml
# Modify labels to match exactly
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
spec:
  labels:
    app: postgres  # Must be identical to ServiceEntry
    version: v14
```

### VM での mTLS 接続失敗

**症状**: `connection refused` または `TLS handshake failed`

**確認**:

```bash
# Check Envoy logs on VM
sudo journalctl -u istio -f | grep -i tls

# Check certificates
sudo ls -la /etc/certs/
sudo openssl x509 -in /etc/certs/cert-chain.pem -text -noout

# Check certificate expiration
sudo openssl x509 -in /etc/certs/cert-chain.pem -noout -dates

# Check ServiceAccount token
sudo ls -la /var/run/secrets/tokens/
sudo cat /var/run/secrets/tokens/istio-token
```

**解決策**:

```bash
# Reissue certificates
istioctl x workload entry configure \
  -f workloadgroup.yaml \
  -o vm-postgres-1 \
  --clusterID Kubernetes \
  --autoregister

# Copy to VM and restart Envoy
scp -r vm-postgres-1/* user@192.168.1.100:/tmp/
ssh user@192.168.1.100 "sudo cp /tmp/root-cert.pem /etc/certs/ && sudo systemctl restart istio"
```

### ヘルスチェック失敗によるトラフィック未到達

**症状**: Envoy が WorkloadEntry を `UNHEALTHY` としてマークする

**確認**:

```bash
# Check Envoy endpoint status
istioctl proxy-config endpoints <pod-name> -n production | grep postgres

# Output:
# 192.168.1.100:5432  UNHEALTHY  outbound|5432||postgres.vm.internal

# Check DestinationRule's outlierDetection
kubectl get destinationrule -n vm-workloads -o yaml
```

**解決策**:

```yaml
# Adjust OutlierDetection settings
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: postgres-healthcheck
spec:
  host: postgres.vm.internal
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 10     # More lenient
      interval: 60s             # Increase check interval
      baseEjectionTime: 60s
      maxEjectionPercent: 100   # Prevent all from being excluded
```

### DNS ルックアップ失敗

**症状**: Pod から `postgres.vm.internal` のルックアップに失敗する

**確認**:

```bash
# Check ServiceEntry
kubectl get serviceentry -n vm-workloads

# DNS lookup test
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup postgres.vm.internal

# Check Istio DNS Proxy enablement
kubectl get pod <pod-name> -o yaml | grep ISTIO_META_DNS_CAPTURE
```

**解決策**:

```yaml
# Add addresses to ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: postgres-service
spec:
  hosts:
  - postgres.vm.internal
  addresses:
  - 240.240.2.1  # Specify virtual IP
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
```

## ベストプラクティス

### 1. 命名規則

```yaml
# WorkloadEntry name: <app>-<role>-<id>
name: postgres-primary-1
name: postgres-replica-2
name: api-backend-vm-3

# ServiceEntry name: <app>-service
name: postgres-service
name: api-service

# ServiceAccount name: <app>-sa
name: postgres-sa
name: api-sa
```

### 2. ラベル戦略

```yaml
spec:
  labels:
    # Required labels
    app: postgres          # Application name
    version: v14           # Version

    # Optional labels
    tier: database         # Tier (frontend, backend, database)
    role: primary          # Role (primary, replica, canary)
    environment: production # Environment
    team: platform         # Team
```

### 3. ServiceAccount の管理

```bash
# Separate ServiceAccount by namespace
kubectl create sa db-sa -n databases
kubectl create sa api-sa -n applications
kubectl create sa cache-sa -n middleware

# Principle of least privilege
kubectl create role db-limited \
  --verb=get \
  --resource=configmaps \
  -n databases
```

### 4. モニタリングとアラート

```yaml
# Alert setup with PrometheusRule
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: workloadentry-alerts
spec:
  groups:
  - name: workloadentry
    rules:
    - alert: WorkloadEntryDown
      expr: up{job="workloadentry-postgres"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "WorkloadEntry {{ $labels.instance }} is down"

    - alert: WorkloadEntryHighErrorRate
      expr: |
        rate(istio_requests_total{
          destination_workload=~".*-vm-.*",
          response_code="500"
        }[5m]) > 0.05
      for: 10m
      labels:
        severity: warning
```

### 5. ドキュメント

各 WorkloadEntry のドキュメントを管理します。

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-primary-1
  annotations:
    description: "Primary PostgreSQL database for production"
    owner: "platform-team@example.com"
    provisioned-date: "2025-11-26"
    os: "Ubuntu 22.04 LTS"
    location: "us-west-2a"
    runbook: "https://wiki.example.com/postgres-vm-runbook"
spec:
  address: 192.168.1.100
  labels:
    app: postgres
    version: v14
```

### 6. バックアップと災害復旧

```bash
# Backup WorkloadEntry
kubectl get workloadentry -n vm-workloads -o yaml > workloadentries-backup.yaml

# Backup ServiceEntry
kubectl get serviceentry -n vm-workloads -o yaml > serviceentries-backup.yaml

# Restore
kubectl apply -f workloadentries-backup.yaml
kubectl apply -f serviceentries-backup.yaml
```

### 7. 段階的な移行戦略

```mermaid
flowchart TD
    Phase1[Phase 1:<br/>VM Mesh Registration] --> Phase2[Phase 2:<br/>Traffic Splitting]
    Phase2 --> Phase3[Phase 3:<br/>Kubernetes Deployment]
    Phase3 --> Phase4[Phase 4:<br/>Traffic Transition]
    Phase4 --> Phase5[Phase 5:<br/>VM Removal]

    %% Style definitions
    classDef phase fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Phase1,Phase2,Phase3,Phase4,Phase5 phase;
```

**フェーズ 1: VM の Mesh 登録**
```yaml
# Register WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-api-vm
spec:
  address: 192.168.1.100
  labels:
    app: api
    version: legacy
```

**フェーズ 2: トラフィック分割（VM 100%）**
```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-migration
spec:
  hosts:
  - api.internal
  http:
  - route:
    - destination:
        host: api.internal
        subset: legacy
      weight: 100
```

**フェーズ 3: Kubernetes Deployment**
```bash
kubectl apply -f kubernetes-deployment.yaml
```

**フェーズ 4: 段階的なトラフィック移行**
```yaml
# 10% Kubernetes
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-migration
spec:
  http:
  - route:
    - destination:
        subset: legacy  # VM
      weight: 90
    - destination:
        subset: k8s     # Kubernetes
      weight: 10
```

**フェーズ 5: VM の削除**
```bash
# After transitioning 100% traffic to Kubernetes
kubectl delete workloadentry legacy-api-vm -n vm-workloads
```

## 参考資料

### 公式ドキュメント
- [WorkloadEntry リファレンス](https://istio.io/latest/docs/reference/config/networking/workload-entry/)
- [WorkloadGroup リファレンス](https://istio.io/latest/docs/reference/config/networking/workload-group/)
- [Virtual Machine のインストール](https://istio.io/latest/docs/setup/install/virtual-machine/)

### 関連ドキュメント
- [基本概念 - VM ワークロードの登録](../02-basic-concepts.md#vm-workload-registration)
- [ServiceEntry](12-service-entry.md)
- [Egress Control](11-egress-control.md)
- [セキュリティ - mTLS](../security/01-mtls.md)

### 追加リソース
- [Istio VM 統合ガイド](https://istio.io/latest/blog/2020/workload-entry/)
- [Envoy Proxy ドキュメント](https://www.envoyproxy.io/docs/envoy/latest/)
