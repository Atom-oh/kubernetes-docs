# アーキテクチャ

> **対応バージョン**: Istio 1.28+ **API バージョン**: `networking.istio.io/v1`, `security.istio.io/v1` **最終更新**: February 19, 2026

このドキュメントでは、Istio の内部アーキテクチャとネットワーキングの仕組みを詳しく説明します。

**背景と歴史**については、[基本概念](02-basic-concepts.md#background-and-history)のドキュメントを参照してください。

**重要な変更点（Istio 1.5+）**:

* Pilot、Citadel、Galley は**もはや個別のコンポーネントではありません**
* これらは Istiod（`pilot-discovery`）という**単一バイナリ**に統合されました
* Pilot/Citadel/Galley という用語は、**機能を表す歴史的な名称**を指します

## 目次

1. [Istio アーキテクチャ概要](03-architecture.md#istio-architecture-overview)
2. [Control Plane: Istiod](03-architecture.md#control-plane-istiod)
3. [Data Plane: Envoy Proxy](03-architecture.md#data-plane-envoy-proxy)
4. [Sidecar インジェクションの仕組み](03-architecture.md#sidecar-injection-mechanism)
5. [iptables とトラフィックのインターセプト](03-architecture.md#iptables-and-traffic-interception)
6. [DNS 処理の仕組み](03-architecture.md#dns-processing-mechanism)
7. [xDS API 通信](03-architecture.md#xds-api-communication)
8. [Sidecar リソースによる最適化](03-architecture.md#optimization-with-sidecar-resource)

## Istio アーキテクチャ概要

### 全体構造

### Control Plane と Data Plane

| カテゴリ        | Control Plane (Istiod)                        | Data Plane (Envoy)        |
| --------------- | --------------------------------------------- | ------------------------- |
| **役割**        | ポリシー管理、設定配布                        | 実際のトラフィック処理    |
| **配置場所**    | 個別の Pod（通常 1～3 個）                    | すべてのアプリケーション Pod |
| **言語**        | Go                                            | C++                       |
| **負荷**        | 低                                            | 高（すべてのトラフィック）|
| **スケーラビリティ** | 水平スケーリング（HA）                    | 自動（Pod ごとに 1 個）   |

## Control Plane: Istiod

### Istiod の内部構造

**重要**: Istio 1.5 以降、Pilot、Citadel、Galley は**個別のコンポーネントではなく、Istiod の内部機能**です。

```mermaid
flowchart TB
    subgraph Istiod[Istiod Single Process]
        subgraph PilotFunc[Pilot Functionality]
            SD[Service Discovery<br/>Service Detection]
            TR[Traffic Management<br/>Traffic Rules]
            xDS[xDS Server<br/>Configuration Distribution]
        end

        subgraph CitadelFunc[Citadel Functionality]
            CA[Certificate Authority<br/>CA Management]
            ID[Identity Management<br/>SPIFFE ID]
        end

        subgraph GalleyFunc[Galley Functionality]
            Val[Configuration Validation<br/>Config Validation]
            Proc[Configuration Processing<br/>Config Processing]
        end
    end

    subgraph K8S[Kubernetes API]
        API[API Server]
        CRD[Istio CRDs<br/>VirtualService, DestinationRule, etc.]
    end

    subgraph Envoys[Envoy Proxies]
        E1[Envoy 1]
        E2[Envoy 2]
        E3[Envoy N]
    end

    API --> Val
    CRD --> Val
    Val --> SD
    Val --> CA

    SD --> xDS
    TR --> xDS
    CA --> xDS

    xDS -->|xDS API<br/>Config Push| E1
    xDS -->|xDS API<br/>Config Push| E2
    xDS -->|xDS API<br/>Config Push| E3

    CA -->|X.509 Certificates<br/>SDS API| E1
    CA -->|X.509 Certificates<br/>SDS API| E2
    CA -->|X.509 Certificates<br/>SDS API| E3

    %% Style definitions
    classDef istiod fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef k8s fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef envoy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class SD,TR,xDS,CA,ID,Val,Proc istiod;
    class API,CRD k8s;
    class E1,E2,E3 envoy;
```

### Istiod の主な機能

**注記**: 以下の機能は、Istio 1.28 では Istiod 内に統合されています。歴史的な名称（Pilot、Citadel、Galley）は機能を説明するために使用されています。

#### 1. Service Discovery（Pilot 機能）

```yaml
# Kubernetes Service detection
apiVersion: v1
kind: Service
metadata:
  name: reviews
spec:
  selector:
    app: reviews
  ports:
  - port: 9080
```

Istiod は以下を追跡します:

* Kubernetes Service
* Endpoint（Pod IP）
* Pod の状態変更
* 外部 Service（ServiceEntry）

#### 2. Traffic Management（Pilot 機能）

Istio CRD を Envoy 設定に変換します:

```yaml
# VirtualService (user-defined)
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
```

↓ Istiod が Envoy 設定に変換 ↓

```json
{
  "route_config": {
    "weighted_clusters": {
      "clusters": [
        {"name": "outbound|9080|v1|reviews", "weight": 90},
        {"name": "outbound|9080|v2|reviews", "weight": 10}
      ]
    }
  }
}
```

#### 3. 証明書管理（Citadel 機能）

```mermaid
sequenceDiagram
    autonumber
    participant Envoy
    participant Istiod
    participant SPIFFE

    Envoy->>Istiod: CSR Request<br/>(Certificate Signing Request)
    Istiod->>SPIFFE: Identity Verification<br/>(ServiceAccount)
    SPIFFE->>Istiod: Verification Complete
    Istiod->>Istiod: Sign Certificate
    Istiod->>Envoy: Issue X.509 Certificate<br/>(TTL: 24 hours)

    Note over Envoy: Use Certificate<br/>mTLS Communication

    Envoy->>Istiod: Certificate Renewal Request<br/>(Before Expiry)
    Istiod->>Envoy: Issue New Certificate
```

**SPIFFE ID 形式**:

```
spiffe://cluster.local/ns/default/sa/reviews
```

#### 4. 設定検証（Galley 機能）

```yaml
# Invalid configuration
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: invalid
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: non-existent-service  # ❌ Non-existent service
```

Istiod は適用前に検証します:

```bash
$ kubectl apply -f invalid-vs.yaml
Error from server: admission webhook "validation.istio.io" denied the request:
configuration is invalid: host "non-existent-service" not found
```

### Istiod のプロセス構造

**Istio 1.28 での実際の実装**:

```bash
# Processes inside Istiod pod
$ kubectl exec -n istio-system deploy/istiod -- ps aux
USER       PID  COMMAND
istio-p+     1  /usr/local/bin/pilot-discovery discovery

# Single binary 'pilot-discovery' performs all functions
```

**要点**:

* Istiod は `pilot-discovery` という**単一の Go バイナリ**として実行されます
* Pilot、Citadel、Galley は**コードレベルのパッケージ/モジュール**として存在しますが、個別のプロセスではありません
* すべての機能は、単一プロセス内で goroutine として実行されます

**Istiod が提供する主なポート**:

| ポート      | プロトコル | 用途                     | 機能                      |
| --------- | -------- | ------------------------ | ------------------------- |
| **15010** | gRPC     | xDS（レガシー）            | 後方互換性                |
| **15012** | gRPC     | TLS 経由の xDS           | 主な xDS API エンドポイント |
| **15014** | HTTP     | Control Plane のモニタリング | メトリクスとヘルスチェック |
| **15017** | HTTPS    | Webhook                  | Sidecar インジェクション  |
| **8080**  | HTTP     | デバッグ                  | デバッグインターフェイス  |

### Istiod の Deployment

**高可用性構成**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: istiod
  namespace: istio-system
spec:
  replicas: 3  # 3 replicas for HA
  selector:
    matchLabels:
      app: istiod
  template:
    metadata:
      labels:
        app: istiod
    spec:
      containers:
      - name: discovery
        image: istio/pilot:1.28.0
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
```

**一般的なリソース使用量**:

* CPU: 0.5～2 コア
* メモリ: 2～4 GB
* 数千の Service と Pod を処理可能

## Data Plane: Envoy Proxy

### Envoy アーキテクチャ

```mermaid
flowchart TB
    subgraph EnvoyProxy[Envoy Proxy]
        Listener[Listeners<br/>Port Reception]
        Filter[Filters<br/>Request Processing]
        Router[Routers<br/>Routing Decision]
        Cluster[Clusters<br/>Upstream Services]

        Listener --> Filter
        Filter --> Router
        Router --> Cluster
    end

    subgraph External[External]
        Incoming[Incoming Requests]
        Outgoing[Outgoing Requests]
    end

    Incoming -->|Inbound| Listener
    Cluster -->|Outbound| Outgoing

    %% Style definitions
    classDef envoy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef external fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Listener,Filter,Router,Cluster envoy;
    class Incoming,Outgoing external;
```

### Envoy の主なコンポーネント

#### 1. Listener

**ポートで接続を受信します**:

```json
{
  "name": "0.0.0.0_15001",
  "address": {
    "socket_address": {
      "address": "0.0.0.0",
      "port_value": 15001
    }
  },
  "filter_chains": [...]
}
```

**デフォルトの Istio Listener**:

* `0.0.0.0:15001`: すべての outbound TCP トラフィック
* `0.0.0.0:15006`: すべての inbound TCP トラフィック
* `0.0.0.0:15021`: ヘルスチェック
* `0.0.0.0:15090`: Prometheus メトリクス

#### 2. Filter

**リクエスト/レスポンスを処理するプラグイン**:

```mermaid
flowchart LR
    Request[HTTP Request]

    subgraph Filters[Filter Chain]
        F1[JWT Auth]
        F2[Rate Limiting]
        F3[RBAC Validation]
        F4[Stats Collection]
        F5[Router]
    end

    Response[HTTP Response]

    Request --> F1 --> F2 --> F3 --> F4 --> F5 --> Response

    %% Style definitions
    classDef req fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef filter fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Request,Response req;
    class F1,F2,F3,F4,F5 filter;
```

#### 3. Cluster

**upstream Service の論理グループ**:

```json
{
  "name": "outbound|9080|v1|reviews.default.svc.cluster.local",
  "type": "EDS",
  "eds_cluster_config": {
    "service_name": "outbound|9080|v1|reviews.default.svc.cluster.local"
  },
  "circuit_breakers": {...},
  "outlier_detection": {...}
}
```

#### 4. Endpoint

**実際の Pod IP リスト**:

```json
{
  "cluster_name": "outbound|9080|v1|reviews",
  "endpoints": [
    {
      "lb_endpoints": [
        {"endpoint": {"address": {"socket_address": {"address": "10.244.1.5", "port_value": 9080}}}},
        {"endpoint": {"address": {"socket_address": {"address": "10.244.2.8", "port_value": 9080}}}}
      ]
    }
  ]
}
```

### Envoy のパフォーマンス

**ベンチマーク**（一般的な環境）:

* スループット: コアあたり 10,000+ RPS
* 追加レイテンシ: < 1ms（P99）
* メモリ: 50～100 MB（デフォルト設定）
* CPU: 0.1～0.5 コア（一般的な負荷）

## Sidecar インジェクションの仕組み

### インジェクションのプロセス

```mermaid
flowchart TB
    subgraph User[User]
        Deploy[Create Deployment]
    end

    subgraph K8S[Kubernetes]
        API[API Server]
        Webhook[Mutating Webhook]
    end

    subgraph Istio[Istio]
        Injector[Sidecar Injector]
    end

    subgraph Pod[Created Pod]
        Init[istio-init<br/>init container]
        App[Application<br/>container]
        Proxy[istio-proxy<br/>sidecar container]
    end

    Deploy -->|1\. POST| API
    API -->|2\. Call Webhook| Webhook
    Webhook -->|3\. Injection Request| Injector
    Injector -->|4\. Modified Pod Spec| Webhook
    Webhook -->|5\. Return| API
    API -->|6\. Create Pod| Init
    Init -->|7\. Complete| App
    Init -->|7\. Complete| Proxy

    %% Style definitions
    classDef user fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef k8s fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef istio fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef container fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Deploy user;
    class API,Webhook k8s;
    class Injector istio;
    class Init,App,Proxy container;
```

### インジェクション前と後の比較

**元の Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reviews
spec:
  template:
    spec:
      containers:
      - name: reviews
        image: reviews:v1
        ports:
        - containerPort: 9080
```

**インジェクション後**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    sidecar.istio.io/status: '{"initContainers":["istio-init"],"containers":["istio-proxy"]}'
spec:
  initContainers:
  - name: istio-init
    image: istio/proxyv2:1.28.0
    command: ['istio-iptables', ...]
    securityContext:
      capabilities:
        add: [NET_ADMIN, NET_RAW]
  containers:
  - name: reviews
    image: reviews:v1
    ports:
    - containerPort: 9080
  - name: istio-proxy
    image: istio/proxyv2:1.28.0
    args: ['proxy', 'sidecar', ...]
```

### Sidecar インジェクションの有効化

#### 自動インジェクション（推奨）

**Namespace レベル**:

```bash
# Add label to namespace
kubectl label namespace default istio-injection=enabled

# All pods deployed to this namespace will automatically have sidecar injected
kubectl apply -f deployment.yaml
```

**Pod レベル**（Annotation）:

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    sidecar.istio.io/inject: "true"  # Enable injection per pod
spec:
  containers:
  - name: app
    image: myapp:v1
```

#### 手動インジェクション

`istioctl kube-inject` コマンドを使用して、YAML ファイルに直接 Sidecar をインジェクションします。

```bash
# Inject sidecar into YAML file and deploy
istioctl kube-inject -f deployment.yaml | kubectl apply -f -

# Or save to file
istioctl kube-inject -f deployment.yaml -o deployment-injected.yaml
kubectl apply -f deployment-injected.yaml
```

**手動インジェクションのシナリオ**:

* 自動インジェクションを使用できない環境
* CI/CD パイプラインで明示的な制御が必要な場合
* デバッグのためにインジェクション済み YAML を確認したい場合

## iptables とトラフィックのインターセプト

### istio-init Container

**役割**: Pod のネットワークトラフィックを Envoy Proxy にリダイレクトする iptables ルールを設定します

```mermaid
sequenceDiagram
    autonumber
    participant K8S as Kubernetes
    participant Init as istio-init
    participant IPTables as iptables
    participant App as Application
    participant Envoy as Envoy Proxy

    K8S->>Init: Start Init Container
    Init->>IPTables: Set iptables rules
    Note over IPTables: Redirect all traffic<br/>to Envoy

    Init->>K8S: Complete (Exit 0)
    K8S->>App: Start Application
    K8S->>Envoy: Start Envoy

    App->>IPTables: Outbound request<br/>(e.g., curl reviews:9080)
    IPTables->>Envoy: Redirect (15001)
    Envoy->>Envoy: Routing decision
    Envoy->>IPTables: Send actual request
    Note over IPTables: Envoy UID<br/>bypasses iptables
```

### iptables ルールの詳細

**istio-init によって実行されるコマンド**:

```bash
#!/bin/bash
# istio-iptables script (simplified)

# 1. OUTPUT chain: Application outbound traffic
iptables -t nat -A OUTPUT -p tcp \
  -m owner ! --uid-owner 1337 \  # Exclude Envoy UID
  -j REDIRECT --to-port 15001     # Envoy outbound port

# 2. PREROUTING chain: Inbound traffic to pod
iptables -t nat -A PREROUTING -p tcp \
  -j REDIRECT --to-port 15006     # Envoy inbound port

# 3. Exclusion rules
# - localhost traffic
iptables -t nat -I OUTPUT -d 127.0.0.1/32 -j RETURN

# - Istiod communication (15012)
iptables -t nat -I OUTPUT -p tcp --dport 15012 -j RETURN

# - DNS (53)
iptables -t nat -I OUTPUT -p udp --dport 53 -j RETURN
```

### トラフィックフロー（iptables 適用後）

```mermaid
flowchart TB
    subgraph Pod[Pod Network Namespace]
        App[Application<br/>localhost:8080]

        subgraph IPTables[iptables NAT]
            Output[OUTPUT Chain]
            PreRouting[PREROUTING Chain]
        end

        subgraph Envoy[Envoy Proxy<br/>UID: 1337]
            L15001[Listener<br/>15001<br/>Outbound]
            L15006[Listener<br/>15006<br/>Inbound]
        end
    end

    External[External Service<br/>reviews:9080]

    %% Outbound flow
    App -->|1\. curl reviews:9080| Output
    Output -->|2\. REDIRECT| L15001
    L15001 -->|3\. Routing| L15001
    L15001 -->|4\. UID 1337<br/>bypass iptables| External

    %% Inbound flow
    External -->|5\. Incoming request| PreRouting
    PreRouting -->|6\. REDIRECT| L15006
    L15006 -->|7\. mTLS verification| L15006
    L15006 -->|8\. localhost| App

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef iptables fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef envoy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef external fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Output,PreRouting iptables;
    class L15001,L15006 envoy;
    class External external;
```

### iptables ルールの確認

**Pod 内から確認**:

```bash
# Enter pod
kubectl exec -it <pod-name> -c istio-proxy -- /bin/bash

# Check iptables rules
iptables -t nat -L -n -v

# OUTPUT chain
Chain OUTPUT (policy ACCEPT)
target     prot opt source     destination
ISTIO_OUTPUT  tcp  --  0.0.0.0/0  0.0.0.0/0

# ISTIO_OUTPUT detail
Chain ISTIO_OUTPUT (1 references)
RETURN     all  --  0.0.0.0/0  127.0.0.1           # Exclude localhost
RETURN     all  --  0.0.0.0/0  0.0.0.0/0           owner UID match 1337  # Exclude Envoy
REDIRECT   tcp  --  0.0.0.0/0  0.0.0.0/0           redir ports 15001  # Redirect rest

# PREROUTING chain
Chain PREROUTING (policy ACCEPT)
ISTIO_INBOUND  tcp  --  0.0.0.0/0  0.0.0.0/0

# ISTIO_INBOUND detail
Chain ISTIO_INBOUND (1 references)
REDIRECT   tcp  --  0.0.0.0/0  0.0.0.0/0           redir ports 15006
```

### iptables と eBPF（CNI Plugin）

Istio は 2 つのトラフィックインターセプト方式をサポートしています:

| 方式         | 利点                 | 欠点                    | 使用シナリオ                   |
| -------------- | -------------------- | ----------------------- | ------------------------------ |
| **iptables**   | シンプル、汎用的     | Init Container が必要   | デフォルトセットアップ         |
| **eBPF (CNI)** | Init 不要、高速      | 最新のカーネルが必要    | 高パフォーマンス、Ambient Mode |

## DNS 処理の仕組み

### Kubernetes DNS の基本動作

```mermaid
flowchart LR
    App[Application]

    subgraph Pod[Pod Network]
        Resolve["/etc/resolv.conf<br/>nameserver 10.96.0.10"]
    end

    subgraph K8S[Kubernetes]
        CoreDNS["CoreDNS<br/>Service: kube-dns<br/>ClusterIP: 10.96.0.10"]
    end

    App -->|"1\. Name resolution request<br/>(reviews)"| Resolve
    Resolve -->|"2\. DNS query<br/>(UDP 53 → 10.96.0.10)"| CoreDNS
    CoreDNS -->|"3\. Return ClusterIP<br/>(reviews = 10.100.1.5)"| Resolve
    Resolve -->|"4\. Return IP<br/>(10.100.1.5)"| App

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dns fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class App app;
    class Resolve,CoreDNS dns;
```

**/etc/resolv.conf**（Pod 内）:

```bash
nameserver 10.96.0.10  # kube-dns ClusterIP
search default.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

### Envoy の DNS 処理

**Istio では、Envoy が DNS を処理します**:

```mermaid
flowchart TB
    App[Application<br/>curl reviews:9080]

    subgraph Envoy[Envoy Proxy]
        Listener[Listener<br/>15001]
        DNS[DNS Filter]
        Route[Route Match]
        Cluster["Cluster<br/>outbound:9080::reviews"]
        EDS[Endpoint Discovery]
    end

    subgraph Istiod[Istiod]
        XDS[xDS Server]
    end

    App -->|1\. TCP connection| Listener
    Listener -->|2\. Inspect Host header| DNS
    DNS -->|3\. Name resolution| Route
    Route -->|4\. Select Cluster| Cluster
    Cluster -->|5\. Query Endpoints| EDS
    EDS <-->|6\. EDS API| XDS

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef envoy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef istiod fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class App app;
    class Listener,DNS,Route,Cluster,EDS envoy;
    class XDS istiod;
```

**利点**:

* CoreDNS 呼び出しが不要（パフォーマンス向上）
* 動的な Endpoint 更新
* 高度なルーティング（バージョン、重み付けなど）

### DNS Proxy（任意）

**DNS Proxy 機能は Istio 1.8+ で追加されました**:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"  # Enable DNS Proxy
```

**動作**:

```mermaid
sequenceDiagram
    autonumber
    participant App as Application
    participant IPT as iptables
    participant Envoy as Envoy<br/>DNS Proxy
    participant CoreDNS as CoreDNS
    participant Istiod as Istiod

    App->>IPT: DNS query<br/>reviews (UDP 53)
    IPT->>Envoy: Redirect (15053)

    alt Istio Service
        Envoy->>Istiod: Query service info<br/>(xDS)
        Istiod->>Envoy: Return ClusterIP
        Envoy->>App: 10.96.0.10
    else External DNS
        Envoy->>CoreDNS: DNS query
        CoreDNS->>Envoy: Return IP
        Envoy->>App: Return IP
    end
```

**DNS Proxy の iptables ルール**:

```bash
# Redirect UDP port 53 to Envoy DNS Proxy
iptables -t nat -A OUTPUT -p udp --dport 53 \
  -m owner ! --uid-owner 1337 \
  -j REDIRECT --to-port 15053
```

## xDS API 通信

### xDS プロトコルの概要

**xDS**: Discovery Service の略であり、Envoy の動的設定プロトコルです。

```mermaid
flowchart LR
    subgraph Istiod[Istiod]
        Pilot[Pilot<br/>xDS Server]
    end

    subgraph Envoy[Envoy Proxy]
        LDS[Listener DS]
        RDS[Route DS]
        CDS[Cluster DS]
        EDS[Endpoint DS]
        SDS[Secret DS]
    end

    Pilot <-->|gRPC<br/>Stream| LDS
    Pilot <-->|gRPC<br/>Stream| RDS
    Pilot <-->|gRPC<br/>Stream| CDS
    Pilot <-->|gRPC<br/>Stream| EDS
    Pilot <-->|gRPC<br/>Stream| SDS

    %% Style definitions
    classDef istiod fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef xds fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Pilot istiod;
    class LDS,RDS,CDS,EDS,SDS xds;
```

### xDS API の種類

| API     | 名前               | 役割                       | 例                |
| ------- | ------------------ | -------------------------- | ----------------- |
| **LDS** | Listener Discovery | ポート設定を受信           | 15001, 15006      |
| **RDS** | Route Discovery    | HTTP ルーティングルール    | VirtualService    |
| **CDS** | Cluster Discovery  | upstream Service           | DestinationRule   |
| **EDS** | Endpoint Discovery | Pod IP リスト              | Service Endpoint  |
| **SDS** | Secret Discovery   | TLS 証明書                 | mTLS 証明書       |

### xDS 通信フロー

```mermaid
sequenceDiagram
    autonumber
    participant Envoy as Envoy Proxy
    participant Istiod as Istiod<br/>(xDS Server)
    participant K8S as Kubernetes API

    Note over Envoy: Pod starts

    Envoy->>Istiod: 1. Connect (gRPC :15012)
    Istiod->>Envoy: 2. mTLS authentication

    Envoy->>Istiod: 3. LDS request
    Istiod->>Envoy: 4. Return Listeners

    Envoy->>Istiod: 5. CDS request
    Istiod->>Envoy: 6. Return Clusters

    Envoy->>Istiod: 7. EDS request
    Istiod->>Envoy: 8. Return Endpoints

    Envoy->>Istiod: 9. RDS request
    Istiod->>Envoy: 10. Return Routes

    Envoy->>Istiod: 11. SDS request
    Istiod->>Envoy: 12. Return Certificates

    Note over Envoy: Configuration complete<br/>Ready to process traffic

    K8S->>Istiod: 13. Service change detected
    Istiod->>Envoy: 14. EDS push (new Endpoint)
```

### xDS 通信の検証

**Envoy Admin API で確認**:

```bash
# From inside pod
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/config_dump

# LDS (Listeners)
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/config_dump | jq '.configs[0].dynamic_listeners'

# CDS (Clusters)
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/config_dump | jq '.configs[1].dynamic_active_clusters'

# EDS (Endpoints)
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/clusters | grep -A 5 "reviews"

# RDS (Routes)
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/config_dump | jq '.configs[2].dynamic_route_configs'
```

**istioctl で確認**:

```bash
# Listener configuration
istioctl proxy-config listeners <pod-name> -n default

# Cluster configuration
istioctl proxy-config clusters <pod-name> -n default

# Endpoint configuration
istioctl proxy-config endpoints <pod-name> -n default

# Route configuration
istioctl proxy-config routes <pod-name> -n default
```

## Sidecar リソースによる最適化

### 問題: すべての Service 情報を受信する

デフォルトでは、各 Envoy は**メッシュ全体のすべての Service に関する情報**を受信します:

```mermaid
flowchart TB
    subgraph Mesh[Service Mesh - 1000 services]
        S1[Service 1]
        S2[Service 2]
        S3[Service 3]
        Sn[Service 1000]
    end

    subgraph Pod[Single Pod]
        App[Application<br/>Uses: Service 1, 2 only]
        Envoy[Envoy Proxy<br/>Receives: All 1000]
    end

    Mesh -.->|Push all info| Envoy

    %% Style definitions
    classDef service fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef envoy fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class S1,S2,S3,Sn service;
    class Envoy envoy;
```

**問題点**:

* メモリ使用量の増加
* CPU 使用量の増加（設定処理）
* ネットワーク帯域幅の浪費
* Istiod の負荷増加

### 解決策: Sidecar リソース

**Sidecar リソース**を使用して、必要な Service だけを受信するように制限します:

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "./*"  # All services in same namespace
    - "istio-system/*"  # All services in istio-system
    - "production/reviews"  # Only reviews in production namespace
```

### Sidecar リソースの例

#### 1. Namespace の分離

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: team-a
spec:
  egress:
  - hosts:
    - "team-a/*"  # Own namespace only
    - "istio-system/*"  # System services
    - "shared/*"  # Shared services
```

#### 2. 特定の Service のみにアクセス

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: frontend
  namespace: default
spec:
  workloadSelector:
    labels:
      app: frontend
  egress:
  - hosts:
    - "default/reviews"
    - "default/ratings"
    - "default/details"
  - port:
      number: 443
      protocol: HTTPS
    hosts:
    - "external/*"
```

#### 3. 外部 Service のみにアクセス

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: external-only
  namespace: default
spec:
  workloadSelector:
    labels:
      app: batch-job
  egress:
  - hosts:
    - "./*"  # Same namespace
  outboundTrafficPolicy:
    mode: REGISTRY_ONLY  # Only those registered in ServiceEntry
```

### Sidecar リソースの効果

**前（Sidecar なし）**:

* 1000 Service → 1000 Cluster 設定
* Envoy メモリ: \~500 MB
* 設定プッシュ時間: 5～10 秒

**後（Sidecar 適用後）**:

* 10 Service → 10 Cluster 設定
* Envoy メモリ: \~80 MB
* 設定プッシュ時間: < 1 秒

### DNS と Sidecar の統合

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: dns-optimized
  namespace: default
spec:
  egress:
  - hosts:
    - "default/reviews"
    - "default/ratings"
  # Envoy only handles DNS for reviews, ratings
  # Rest forwarded to CoreDNS
```

**結果**:

* Envoy は `reviews`、`ratings` のみを名前解決します
* `google.com` などの外部ドメインは CoreDNS に転送されます
* メモリと CPU を節約できます

## 参考資料

### 公式ドキュメント

* [Istio Architecture](https://istio.io/latest/docs/ops/deployment/architecture/)
* [Envoy Proxy](https://www.envoyproxy.io/docs/envoy/latest/intro/intro)
* [xDS Protocol](https://www.envoyproxy.io/docs/envoy/latest/api-docs/xds_protocol)
* [SPIFFE](https://spiffe.io/)

### 歴史と背景

* [Envoy Origin Story - Matt Klein](https://blog.envoyproxy.io/the-universal-data-plane-api-d15cec7a)
* [Istio Announcement - Google Cloud Blog](https://cloud.google.com/blog/products/gcp/istio-service-mesh-for-microservices)
* [Service Mesh History](https://www.nginx.com/blog/what-is-a-service-mesh/)

### 発展的な学習

* [Envoy Architecture Overview](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/arch_overview)
* [Istio Performance and Scalability](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
* [iptables Tutorial](https://www.frozentux.net/iptables-tutorial/iptables-tutorial.html)
