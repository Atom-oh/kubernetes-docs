# Ambient Mode

Ambient Mode は、Istio 1.28 で導入された革新的なデータプレーンアーキテクチャです。従来の Sidecar アプローチにおける複雑さとリソースオーバーヘッドを削減しながら、Service Mesh の中核機能を提供します。

## 目次

1. [概要](#overview)
2. [Sidecar Mode と Ambient Mode](#sidecar-mode-vs-ambient-mode)
3. [アーキテクチャ](#architecture)
4. [インストールと設定](#installation-and-configuration)
5. [移行](#migration)
6. [パフォーマンス比較](#performance-comparison)
7. [ユースケース](#use-cases)
8. [トラブルシューティング](#troubleshooting)

## 概要

<p align="center">
  <img src="https://istio.io/latest/docs/ops/ambient/overview/ambient-layers.png" alt="Ambient Mode のレイヤー" width="700">
</p>

Ambient Mode は、アプリケーション Pod に Sidecar Proxy を注入せずに Service Mesh 機能を提供する新しいアプローチです。上の図に示すように、Ambient Mode は**レイヤー型アーキテクチャ**で構成されます。

1. **セキュアオーバーレイ層（L4）**: ztunnel による mTLS と基本テレメトリー
2. **L7 処理層**: Waypoint Proxy による高度なトラフィック管理

### Ambient Mode が必要な理由

従来の Sidecar モデルの制約:
- **高いリソースオーバーヘッド**: 各 Pod に Envoy Proxy（50～100MB のメモリ）が必要
- **運用の複雑さ**: Pod の再起動、バージョン管理、ローリングアップデートが複雑
- **初期レイテンシー**: Sidecar の初期化により Pod の起動時間が増加
- **過剰な機能**: ほとんどのワークロードは L7 機能を使用しない

Ambient Mode の解決策:
- ノードごとに 1 つの Proxy: リソース使用量を 90% 以上削減
- Pod の再起動が不要: ダウンタイムゼロで Service Mesh を導入
- 段階的な導入: 必要に応じて L4 から L7 へ拡張
- 透過的な統合: アプリケーションコードの変更不要

### コアコンセプト

```mermaid
flowchart TB
    subgraph SidecarMode["Sidecar Mode (Traditional)"]
        App1[Application<br/>Container]
        Sidecar1[Envoy<br/>Sidecar]
        App1 <--> Sidecar1
    end

    subgraph AmbientMode["Ambient Mode (New)"]
        App2[Application<br/>Container Only]
        Node[Node-level<br/>ztunnel<br/>L4 Proxy]
        Waypoint[Waypoint<br/>Proxy<br/>L7 Features]

        App2 -->|Transparent| Node
        Node -->|When L7 needed| Waypoint
    end

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef sidecar fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef ambient fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class App1,App2 app;
    class Sidecar1 sidecar;
    class Node,Waypoint ambient;
```

### Ambient Mode の利点

1. **低いリソース使用量**: Pod ごとではなくノードごとに Proxy を配置
2. **シンプルなデプロイ**: Pod の再起動が不要
3. **透過的な導入**: アプリケーションの変更不要
4. **柔軟な L7 機能**: 必要な場合にのみ Waypoint を使用

## Sidecar Mode と Ambient Mode

### アーキテクチャ比較

#### Sidecar Mode

```mermaid
flowchart TB
    subgraph Pod1["Pod"]
        App1[App<br/>Container]
        Envoy1[Envoy<br/>Sidecar]
    end

    subgraph Pod2["Pod"]
        App2[App<br/>Container]
        Envoy2[Envoy<br/>Sidecar]
    end

    subgraph Pod3["Pod"]
        App3[App<br/>Container]
        Envoy3[Envoy<br/>Sidecar]
    end

    App1 <--> Envoy1
    App2 <--> Envoy2
    App3 <--> Envoy3

    Envoy1 <-->|mTLS| Envoy2
    Envoy2 <-->|mTLS| Envoy3

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef envoy fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class App1,App2,App3 app;
    class Envoy1,Envoy2,Envoy3 envoy;
```

**特徴**:
- 各 Pod に Envoy Proxy を注入
- すべての L4/L7 機能をサポート
- 高いリソース使用量
- Pod の再起動が必要

#### Ambient Mode

```mermaid
flowchart TB
    subgraph Node["Kubernetes Node"]
        subgraph Pods["Application Pods"]
            App1[App<br/>Pod 1]
            App2[App<br/>Pod 2]
            App3[App<br/>Pod 3]
        end

        Ztunnel[ztunnel<br/>L4 Proxy<br/>mTLS, Telemetry]
    end

    subgraph WaypointLayer["Waypoint Proxy (Optional)"]
        Waypoint[Waypoint<br/>L7 Proxy<br/>Advanced Routing]
    end

    App1 -->|Transparent| Ztunnel
    App2 -->|Transparent| Ztunnel
    App3 -->|Transparent| Ztunnel

    Ztunnel -->|L4 only| Service[Service]
    Ztunnel -.->|L7 needed| Waypoint
    Waypoint --> Service

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef ztunnel fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef waypoint fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef service fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App1,App2,App3 app;
    class Ztunnel ztunnel;
    class Waypoint waypoint;
    class Service service;
```

**特徴**:
- ノードごとに 1 つの ztunnel
- L4 機能をデフォルトで提供
- L7 機能には Waypoint が必要
- Pod の再起動が不要

### 詳細比較表

| 項目 | Sidecar Mode | Ambient Mode |
|------|-------------|--------------|
| **デプロイ方法** | Pod への Sidecar 注入 | ノードレベルの ztunnel + オプションの Waypoint |
| **リソース使用量** | 高い（Pod ごとに約 50～100MB） | 低い（ノードごとに約 50MB） |
| **Pod の再起動** | 必要 | 不要 |
| **初期レイテンシー** | あり（Sidecar の初期化） | 最小限 |
| **L4 機能** | サポート | サポート |
| **L7 機能** | 完全にサポート | Waypoint が必要 |
| **mTLS** | 自動 | 自動 |
| **テレメトリー** | 詳細 | 基本（L4）、詳細（Waypoint 使用時の L7） |
| **Circuit Breaker** | サポート | Waypoint が必要 |
| **Retry/Timeout** | サポート | Waypoint が必要 |
| **Header 操作** | サポート | Waypoint が必要 |
| **パフォーマンスオーバーヘッド** | 中程度（約 5～10%） | 低い（約 1～3%） |
| **運用の複雑さ** | 高い | 低い |
| **本番環境への対応度** | 成熟 | ベータ（Istio 1.28+） |

### リソース使用量の比較

```yaml
# Sidecar Mode
# 100 pods x 50MB = 5GB memory
# 100 pods x 0.1 CPU = 10 vCPU

# Ambient Mode
# 10 nodes x 50MB = 500MB memory (ztunnel)
# + Waypoint (when needed): 200MB memory
# Total: ~700MB memory
```

## アーキテクチャ

<p align="center">
  <img src="https://istio.io/latest/docs/ops/ambient/overview/data-plane.png" alt="Ambient データプレーン" width="800">
</p>

Ambient Mode のデータプレーンは、**ztunnel** と **Waypoint Proxy** という 2 つのコアコンポーネントで構成されます。

### ztunnel（Zero Trust Tunnel）

<p align="center">
  <img src="https://istio.io/latest/docs/ops/ambient/overview/ztunnel-traffic.png" alt="ztunnel のトラフィックフロー" width="600">
</p>

ztunnel は Ambient Mode のコアコンポーネントであり、**ノードレベルで稼働する軽量な L4 Proxy** です。各 Kubernetes ノードに DaemonSet としてデプロイされ、そのノード上のすべての Pod トラフィックを透過的に処理します。

#### ztunnel の仕組み

1. **トラフィックキャプチャ**: CNI Plugin と eBPF により Pod のネットワークトラフィックを透過的にインターセプト
2. **mTLS の適用**: SPIFFE ベースの Identity を使用して mTLS 暗号化を自動的に適用
3. **負荷分散**: Endpoint 間で L4 負荷分散を実行
4. **テレメトリー収集**: 接続メトリクスとログを収集
5. **転送**: トラフィックを宛先の ztunnel または Waypoint に転送

**ztunnel のテクノロジースタック**:
- **言語**: Rust（高パフォーマンス、低メモリ使用量）
- **プロトコル**: HBONE（HTTP-Based Overlay Network Environment）
- **Identity**: SPIFFE/SPIRE 標準に準拠
- **CNI**: Istio CNI Plugin と緊密に統合

#### ztunnel の役割

```mermaid
flowchart TB
    App[Application Pod]
    Ztunnel[ztunnel<br/>DaemonSet]

    subgraph ZtunnelFeatures["ztunnel Features"]
        MTLS[mTLS<br/>Encryption]
        L4Telemetry[L4 Telemetry<br/>Metrics Collection]
        Identity[Identity<br/>Service Account]
        L4LB[L4 Load Balancing]
    end

    Target[Target Service]

    App -->|TCP connection| Ztunnel
    Ztunnel -->|Apply mTLS| MTLS
    MTLS -->|Collect metrics| L4Telemetry
    L4Telemetry -->|Verify identity| Identity
    Identity -->|Load balancing| L4LB
    L4LB -->|Transmit| Target

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef ztunnel fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef feature fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef target fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Ztunnel ztunnel;
    class MTLS,L4Telemetry,Identity,L4LB feature;
    class Target target;
```

**ztunnel の特徴**:
- Rust で実装（パフォーマンス最適化）
- DaemonSet としてデプロイ
- CNI Plugin と統合
- eBPF ベースのトラフィックリダイレクト

#### ztunnel のデプロイ

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ztunnel
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: ztunnel
  template:
    metadata:
      labels:
        app: ztunnel
    spec:
      hostNetwork: true
      containers:
      - name: istio-proxy
        image: istio/ztunnel:1.28.0
        securityContext:
          privileged: true
          capabilities:
            add:
            - NET_ADMIN
            - SYS_ADMIN
        resources:
          requests:
            cpu: 100m
            memory: 50Mi
          limits:
            cpu: 200m
            memory: 100Mi
```

### Waypoint Proxy

<p align="center">
  <img src="https://istio.io/latest/docs/ops/ambient/overview/waypoint-traffic.png" alt="Waypoint のトラフィックフロー" width="700">
</p>

Waypoint は、**L7 機能が必要な場合に使用するオプションの Proxy** です。上の図に示すように、Waypoint は Service の前に配置され、高度なトラフィック管理機能を提供します。

#### Waypoint の主な特徴

1. **選択的なデプロイ**: すべての Service ではなく、L7 機能が必要な Service にのみ使用
2. **共有 Proxy**: 複数のワークロードが 1 つの Waypoint を共有（Namespace または ServiceAccount ごと）
3. **Envoy ベース**: 従来の Sidecar と同じ Envoy Proxy を使用し、すべての Istio L7 機能をサポート
4. **オンデマンド**: 実行時に動的に追加・削除可能

#### Waypoint のデプロイ単位

```mermaid
flowchart TD
    subgraph Namespace["Namespace: production"]
        subgraph SA1["ServiceAccount: frontend"]
            Pod1[Frontend Pod 1]
            Pod2[Frontend Pod 2]
        end

        subgraph SA2["ServiceAccount: backend"]
            Pod3[Backend Pod 1]
            Pod4[Backend Pod 2]
        end

        WP1[Waypoint<br/>for frontend]
        WP2[Waypoint<br/>for backend]
    end

    Ztunnel[ztunnel]

    Ztunnel -->|L7 routing| WP1
    Ztunnel -->|L7 routing| WP2

    WP1 --> Pod1
    WP1 --> Pod2
    WP2 --> Pod3
    WP2 --> Pod4

    %% Style definitions
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef waypoint fill:#3B48CC,stroke:#333,stroke-width:2px,color:white;
    classDef ztunnel fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Pod1,Pod2,Pod3,Pod4 pod;
    class WP1,WP2 waypoint;
    class Ztunnel ztunnel;
```

**デプロイオプション**:
- **ServiceAccount ベース**: 特定の SA を持つ Pod のみが対応する Waypoint を使用
- **Namespace ベース**: Namespace 全体のすべての Pod が 1 つの Waypoint を使用
- **ワークロードベース**: 特定のワークロード（Deployment、StatefulSet など）にのみ適用

#### Waypoint の役割

```mermaid
flowchart TB
    Ztunnel[ztunnel]

    subgraph WaypointFeatures["Waypoint Features"]
        L7Routing[L7 Routing<br/>Path, Header]
        Retry[Retry/Timeout]
        CircuitBreaker[Circuit Breaker]
        FaultInjection[Fault Injection]
        HeaderManip[Header Manipulation]
    end

    Target[Target Service]

    Ztunnel -->|When L7 needed| L7Routing
    L7Routing --> Retry
    Retry --> CircuitBreaker
    CircuitBreaker --> FaultInjection
    FaultInjection --> HeaderManip
    HeaderManip --> Target

    %% Style definitions
    classDef ztunnel fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef feature fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef target fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Ztunnel ztunnel;
    class L7Routing,Retry,CircuitBreaker,FaultInjection,HeaderManip feature;
    class Target target;
```

**Waypoint の特徴**:
- Service Account ごと、または Namespace ごとにデプロイ
- Envoy Proxy ベース
- すべての L7 Istio 機能をサポート
- 必要な Service にのみ選択的に使用

#### Waypoint のデプロイ

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: reviews-waypoint
  namespace: default
spec:
  gatewayClassName: istio-waypoint
  listeners:
  - name: mesh
    port: 15008
    protocol: HBONE
```

### 完全なトラフィックフロー

以下は、**Sidecar なし**の Ambient Mode におけるトラフィックフロー全体を示す図です。

```mermaid
sequenceDiagram
    autonumber
    participant ClientApp as Client App<br/>(No Sidecar)
    participant ClientZtunnel as Client Node<br/>ztunnel
    participant Waypoint as Waypoint Proxy<br/>(L7 Optional)
    participant ServerZtunnel as Server Node<br/>ztunnel
    participant ServerApp as Server App<br/>(No Sidecar)

    Note over ClientApp,ServerApp: L4 Only Path (Basic Scenario)
    ClientApp->>ClientZtunnel: 1. TCP request
    Note over ClientZtunnel: mTLS encrypt<br/>L4 metrics
    ClientZtunnel->>ServerZtunnel: 2. mTLS connection
    Note over ServerZtunnel: mTLS decrypt<br/>L4 metrics
    ServerZtunnel->>ServerApp: 3. Plain TCP
    ServerApp->>ServerZtunnel: 4. Response
    ServerZtunnel->>ClientZtunnel: 5. mTLS response
    ClientZtunnel->>ClientApp: 6. Plain response

    Note over ClientApp,ServerApp: L7 Path (Advanced Routing)
    ClientApp->>ClientZtunnel: 1. HTTP request
    ClientZtunnel->>Waypoint: 2. HBONE tunnel
    Note over Waypoint: L7 routing<br/>Header matching<br/>Circuit breaker<br/>Retry logic
    Waypoint->>ServerZtunnel: 3. mTLS to target
    ServerZtunnel->>ServerApp: 4. Plain HTTP
    ServerApp->>ServerZtunnel: 5. Response
    ServerZtunnel->>Waypoint: 6. mTLS response
    Waypoint->>ClientZtunnel: 7. HBONE tunnel
    ClientZtunnel->>ClientApp: 8. Response
```

**トラフィックフローの分析**:

1. **L4 のみのパス**（ztunnel のみを使用）:
   - 最小限のレイテンシー（約 1ms）
   - mTLS を自動的に適用
   - 基本テレメトリー
   - ワークロードの 80～90% に十分

2. **L7 パス**（ztunnel + Waypoint）:
   - Header ベースのルーティング
   - Circuit Breaking
   - Retry/Timeout
   - 複雑なトラフィックポリシーが必要な場合

### HBONE プロトコル

<p align="center">
  <img src="https://istio.io/latest/blog/2022/introducing-ambient-mesh/hbone.png" alt="HBONE プロトコル" width="600">
</p>

**HBONE（HTTP-Based Overlay Network Environment）**は、Ambient Mode で使用されるトンネリングプロトコルです。

- **HTTP/2 ベース**: 既存インフラストラクチャとの互換性
- **組み込み mTLS**: セキュアな通信
- **効率的**: 最小限のオーバーヘッド
- **ファイアウォールフレンドリー**: 標準 HTTP/2 ポートを使用

```mermaid
flowchart LR
    App[Application<br/>Plain TCP]
    ZtunnelSrc[Source<br/>ztunnel]
    Network[Network<br/>HBONE/HTTP2<br/>mTLS]
    ZtunnelDst[Destination<br/>ztunnel]
    Target[Target App<br/>Plain TCP]

    App -->|Plain| ZtunnelSrc
    ZtunnelSrc -->|HBONE Tunnel| Network
    Network -->|HBONE Tunnel| ZtunnelDst
    ZtunnelDst -->|Plain| Target

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef ztunnel fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef network fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App,Target app;
    class ZtunnelSrc,ZtunnelDst ztunnel;
    class Network network;
```

## インストールと設定

### 1. Istio のインストール（Ambient Mode）

```bash
# Download Istio
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# Install with Ambient profile
istioctl install --set profile=ambient -y

# Verify installation
kubectl get pods -n istio-system
# Output:
# NAME                                   READY   STATUS
# istio-cni-node-xxxxx                   1/1     Running
# istiod-xxxxx                           1/1     Running
# ztunnel-xxxxx                          1/1     Running
```

### 2. Namespace で Ambient Mode を有効化

```bash
# Enable Ambient Mode with Label
kubectl label namespace default istio.io/dataplane-mode=ambient

# Verify
kubectl get namespace default -o yaml | grep istio.io/dataplane-mode
```

### 3. アプリケーションをデプロイ

```yaml
# Normal Deployment (No Sidecar needed)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reviews
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: reviews
  template:
    metadata:
      labels:
        app: reviews
    spec:
      containers:
      - name: reviews
        image: istio/examples-bookinfo-reviews-v1:1.17.0
        ports:
        - containerPort: 9080
```

### 4. Waypoint Proxy をデプロイ（オプション）

```bash
# Create Waypoint per Service Account
istioctl x waypoint apply --service-account reviews

# Or per Namespace Waypoint
istioctl x waypoint apply --namespace default

# Verify Waypoint
kubectl get gateway -n default
```

### 5. L7 機能を使用

```yaml
# VirtualService (using Waypoint)
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
---
# DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## 移行

### Sidecar Mode から Ambient Mode への移行

#### 段階的な移行

```mermaid
flowchart LR
    Start[Sidecar Mode<br/>In Production]
    Install[Install Ambient<br/>Components]
    Label[Add Namespace<br/>Label]
    Remove[Remove<br/>Sidecar]
    Waypoint[Deploy<br/>Waypoint]
    End[Complete<br/>Ambient Mode]

    Start --> Install
    Install --> Label
    Label --> Remove
    Remove --> Waypoint
    Waypoint --> End

    %% Style definitions
    classDef step fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Start,Install,Label,Remove,Waypoint,End step;
```

#### ステップ 1: Ambient コンポーネントをインストール

```bash
# If existing Istio is installed
istioctl install --set profile=ambient --skip-confirmation

# Verify ztunnel and CNI
kubectl get daemonset -n istio-system
```

#### ステップ 2: テスト Namespace に適用

```bash
# Create test namespace
kubectl create namespace test-ambient

# Enable Ambient Mode
kubectl label namespace test-ambient istio.io/dataplane-mode=ambient

# Deploy test application
kubectl apply -f samples/sleep/sleep.yaml -n test-ambient
```

#### ステップ 3: 検証

```bash
# Verify mTLS is working
kubectl exec -n test-ambient deploy/sleep -- curl -s http://httpbin:8000/headers

# Check Telemetry
kubectl logs -n istio-system -l app=ztunnel | grep test-ambient
```

#### ステップ 4: 本番 Namespace を切り替え

```bash
# Add Label to existing Namespace
kubectl label namespace default istio.io/dataplane-mode=ambient

# Restart pods (remove Sidecar)
kubectl rollout restart deployment -n default

# Verify Sidecar removal
kubectl get pods -n default -o jsonpath='{.items[*].spec.containers[*].name}' | grep -v istio-proxy
```

#### ステップ 5: Waypoint をデプロイ（L7 機能が必要な場合）

```bash
# Waypoint per Service Account
for sa in $(kubectl get sa -n default -o name); do
  istioctl x waypoint apply --service-account ${sa#serviceaccount/} -n default
done
```

### ロールバック戦略

```bash
# Rollback from Ambient to Sidecar

# 1. Remove Namespace Label
kubectl label namespace default istio.io/dataplane-mode-

# 2. Enable Sidecar Injection
kubectl label namespace default istio-injection=enabled

# 3. Restart pods
kubectl rollout restart deployment -n default

# 4. Remove Waypoint
kubectl delete gateway -n default --all
```

## パフォーマンス比較

<p align="center">
  <img src="https://istio.io/latest/blog/2022/introducing-ambient-mesh/perf.png" alt="パフォーマンス比較" width="700">
</p>

### ベンチマーク結果

上のグラフは Istio の公式パフォーマンステスト結果を示しており、Ambient Mode は Sidecar Mode と比べて**大幅に低いリソース使用量**を実現することを示しています。

| メトリクス | Sidecar Mode | Ambient Mode（ztunnel のみ） | Ambient Mode（Waypoint あり） |
|--------|-------------|---------------------------|---------------------------|
| **メモリ/Pod** | 約 50～100MB | 約 1～2MB | 約 1～2MB（アプリ）+ 共有 Waypoint |
| **CPU/Pod** | 約 0.1 vCPU | 約 0.01 vCPU | 約 0.01 vCPU（アプリ）+ 共有 Waypoint |
| **レイテンシー（P50）** | +2～3ms | +0.5～1ms | +2～3ms |
| **レイテンシー（P99）** | +5～10ms | +1～2ms | +5～10ms |
| **スループット** | -5～10% | -1～3% | -5～10% |

### リソース使用量の可視化

```mermaid
graph TD
    subgraph Comparison["100 Pods Cluster"]
        subgraph Sidecar["Sidecar Mode"]
            SM[Total Memory: 5GB<br/>Total CPU: 10 vCPU<br/>Per pod: 50MB + 0.1 CPU]
        end

        subgraph Ambient["Ambient Mode"]
            AM[Total Memory: 700MB<br/>Total CPU: 1.5 vCPU<br/>10 ztunnels + 1 waypoint]
        end

        subgraph Savings["Savings"]
            Save[Memory: 86% savings<br/>CPU: 85% savings<br/>Cost: ~80% savings]
        end
    end

    Sidecar -.->|Comparison| Ambient
    Ambient -.->|Result| Savings

    %% Style definitions
    classDef sidecar fill:#E6522C,stroke:#333,stroke-width:2px,color:white;
    classDef ambient fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef savings fill:#3B48CC,stroke:#333,stroke-width:2px,color:white;

    %% Apply classes
    class SM sidecar;
    class AM ambient;
    class Save savings;
```

### リソース削減量の計算

```python
# Example with 100 pod cluster

# Sidecar Mode
sidecar_memory = 100 * 50  # 5000MB = 5GB
sidecar_cpu = 100 * 0.1    # 10 vCPU

# Ambient Mode (10 nodes)
ambient_memory = 10 * 50 + 200  # 700MB (ztunnel + 1 waypoint)
ambient_cpu = 10 * 0.1 + 0.5    # 1.5 vCPU

# Savings
memory_saved = sidecar_memory - ambient_memory  # 4300MB (~86%)
cpu_saved = sidecar_cpu - ambient_cpu          # 8.5 vCPU (~85%)
```

## ユースケース

### Ambient Mode を選ぶべき場合

```mermaid
flowchart TD
    Start{Service Mesh<br/>Consideration}

    ResourceConstrained{Resource<br/>constraints?}
    L7Required{Complex L7<br/>features needed?}
    SimpleMesh{Simple security<br/>+ telemetry?}

    Sidecar[Sidecar Mode<br/>Recommended]
    AmbientL4[Ambient Mode<br/>ztunnel only]
    AmbientL7[Ambient Mode<br/>+ Waypoint]

    Start --> ResourceConstrained
    ResourceConstrained -->|Yes| SimpleMesh
    ResourceConstrained -->|No| L7Required

    SimpleMesh -->|Yes| AmbientL4
    SimpleMesh -->|No| AmbientL7

    L7Required -->|All services| Sidecar
    L7Required -->|Some services only| AmbientL7

    %% Style definitions
    classDef decision fill:#F8B52A,stroke:#333,stroke-width:2px,color:black;
    classDef solution fill:#326CE5,stroke:#333,stroke-width:2px,color:white;

    %% Apply classes
    class ResourceConstrained,L7Required,SimpleMesh decision;
    class Sidecar,AmbientL4,AmbientL7 solution;
```

**Ambient Mode を推奨するシナリオ**:
- 数百以上のマイクロサービス
- リソースコストの最適化が重要
- ほとんどの Service ではシンプルな通信のみが必要
- 高度なルーティングが必要なのは一部の Service のみ
- 運用の複雑さを最小化したい

**Sidecar Mode を推奨するシナリオ**:
- すべての Service で L7 機能が必要
- 実績のある成熟したソリューションが必要
- Service ごとのきめ細かな制御が必要
- Pod ごとに独立した Proxy バージョン管理が必要

### 1. L4 機能だけが必要な場合

```yaml
# Using ztunnel only (Waypoint not needed)
apiVersion: v1
kind: Namespace
metadata:
  name: backend
  labels:
    istio.io/dataplane-mode: ambient
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
  namespace: backend
spec:
  replicas: 3
  # ... (normal Deployment)
```

**利点**:
- mTLS を自動的に適用
- 基本テレメトリー
- 最小限のリソース使用量

### 2. 選択的な L7 機能の使用

```yaml
# Only specific Service uses Waypoint
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: frontend-waypoint
  namespace: frontend
spec:
  gatewayClassName: istio-waypoint
  listeners:
  - name: mesh
    port: 15008
    protocol: HBONE
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: frontend
  namespace: frontend
  labels:
    istio.io/use-waypoint: frontend-waypoint
```

### 3. 段階的な移行

```bash
# Step-by-step migration
# 1. Non-critical services
kubectl label namespace dev istio.io/dataplane-mode=ambient

# 2. Testing
kubectl label namespace staging istio.io/dataplane-mode=ambient

# 3. Production (one by one)
kubectl label namespace prod-backend istio.io/dataplane-mode=ambient
kubectl label namespace prod-frontend istio.io/dataplane-mode=ambient
```

## トラブルシューティング

### ztunnel が動作しない

```bash
# Check ztunnel status
kubectl get daemonset -n istio-system ztunnel
kubectl logs -n istio-system -l app=ztunnel

# Check CNI
kubectl get daemonset -n istio-system istio-cni-node
kubectl logs -n istio-system -l k8s-app=istio-cni-node
```

### トラフィックが Waypoint に到達しない

```bash
# Check Waypoint status
kubectl get gateway -n <namespace>

# Verify Waypoint connection to Service Account
kubectl get sa <sa-name> -n <namespace> -o yaml | grep use-waypoint

# Check Envoy configuration
istioctl proxy-config clusters <waypoint-pod> -n <namespace>
```

## 参照情報

### 公式ドキュメント
- [Istio Ambient Mode 公式ドキュメント](https://istio.io/latest/docs/ops/ambient/)
- [Ambient Mode 紹介ブログ](https://istio.io/latest/blog/2022/introducing-ambient-mesh/)
- [Ambient Mode を始める](https://istio.io/latest/docs/ops/ambient/getting-started/)
- [ztunnel GitHub リポジトリ](https://github.com/istio/ztunnel)

### 技術リソース
- [Ambient Mesh アーキテクチャの詳細な解説](https://istio.io/latest/blog/2022/ambient-security/)
- [HBONE プロトコルの解説](https://istio.io/latest/blog/2022/get-started-ambient/)
- [パフォーマンスベンチマーク](https://istio.io/latest/blog/2022/ambient-performance/)

### コミュニティ
- [Istio Discuss - Ambient Mode](https://discuss.istio.io/c/ambient/47)
- [Istio Slack #ambient-mesh](https://istio.slack.com/)

### 比較リソース

```mermaid
graph LR
    subgraph Evolution["Istio Evolution"]
        V1[Istio 1.0<br/>2018<br/>Sidecar Mode]
        V2[Istio 1.15<br/>2022<br/>Ambient Beta]
        V3[Istio 1.28<br/>2024<br/>Ambient Stable]
    end

    V1 -->|Resource optimization| V2
    V2 -->|Stabilization| V3

    %% Style definitions
    classDef old fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef beta fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef stable fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;

    %% Apply classes
    class V1 old;
    class V2 beta;
    class V3 stable;
```

**本番利用の状況**（2024 年時点）:
- Solo.io: 社内クラスター全体を Ambient Mode に移行
- 金融企業: 数千のマイクロサービスに Ambient Mode を適用（コストを 80% 削減）
- E コマース: L4 ztunnel + 選択的 Waypoint によるハイブリッド運用

**主な機能ロードマップ**:
- 1.28（2024 年第 1 四半期）: Ambient Mode GA（General Availability）
- 1.29（2024 年第 2 四半期）: マルチクラスター Ambient のサポート
- 1.30+（2024 年第 3 四半期以降）: Gateway API の完全な統合、パフォーマンス最適化

## まとめ

Ambient Mode は、Istio の今後の方向性を示す革新的なアーキテクチャです。

| 機能 | 説明 | 利点 |
|---------|-------------|---------|
| **Sidecar の削除** | Pod ごとに Proxy が不要 | リソースを 90% 削減 |
| **2 層アーキテクチャ** | L4（ztunnel）+ L7（Waypoint） | 柔軟な機能選択 |
| **透過的な導入** | Pod の再起動が不要 | ダウンタイムゼロの導入 |
| **段階的な移行** | Namespace ごとの移行 | 安全な移行 |
| **HBONE プロトコル** | HTTP/2 ベースのトンネリング | ファイアウォールフレンドリー |

Ambient Mode は、特に**大規模なマイクロサービス環境**でリソース効率と運用の簡素化を実現し、L7 機能が必要な Service にのみ Waypoint を選択的にデプロイすることで、**コスト効率の高い Service Mesh**を実装できます。
