# Service Mesh ソリューション比較

> **最終更新**: February 19, 2026 **比較対象**: Istio 1.24, Linkerd 2.15, Kong Mesh 2.8, Consul Connect 1.19

このドキュメントでは、Kubernetes 環境で利用可能な主要な Service Mesh ソリューションを包括的に比較します。

## 目次

1. [概要とアーキテクチャ](01-service-mesh-comparison.md#overview-and-architecture)
2. [パフォーマンス比較](01-service-mesh-comparison.md#performance-comparison)
3. [機能比較](01-service-mesh-comparison.md#feature-comparison)
4. [運用の複雑さ](01-service-mesh-comparison.md#operational-complexity)
5. [セキュリティ機能](01-service-mesh-comparison.md#security-features)
6. [可観測性機能](01-service-mesh-comparison.md#observability-features)
7. [マルチクラスターサポート](01-service-mesh-comparison.md#multi-cluster-support)
8. [コスト分析](01-service-mesh-comparison.md#cost-analysis)
9. [ユースケースの推奨事項](01-service-mesh-comparison.md#use-case-recommendations)

## 概要とアーキテクチャ

### Service Mesh とは？

Service Mesh は、マイクロサービス間の通信を管理するインフラストラクチャレイヤーです。アプリケーションコードを変更せずに、トラフィック管理、セキュリティ、可観測性の機能を提供します。

#### Service Mesh の基本概念

```mermaid
flowchart TB
    subgraph "Without Service Mesh"
        direction LR
        AppA1[Service A] -->|Direct Call| AppB1[Service B]
        AppB1 -->|Direct Call| AppC1[Service C]

        Note1[Problems:<br/>- Retry logic implemented in each service<br/>- Manual encryption setup between services<br/>- Inconsistent metrics collection<br/>- Difficult traffic control]
    end

    subgraph "With Service Mesh"
        direction LR
        subgraph PodA["Pod A"]
            AppA2[Service A]
            ProxyA[Sidecar<br/>Proxy]
        end
        subgraph PodB["Pod B"]
            AppB2[Service B]
            ProxyB[Sidecar<br/>Proxy]
        end
        subgraph PodC["Pod C"]
            AppC2[Service C]
            ProxyC[Sidecar<br/>Proxy]
        end

        ControlPlane[Control Plane<br/>Policy Management]

        AppA2 --> ProxyA
        ProxyA <-->|mTLS<br/>Auto Encryption| ProxyB
        AppB2 --> ProxyB
        ProxyB <-->|mTLS| ProxyC
        AppC2 --> ProxyC

        ControlPlane -.->|Config Distribution| ProxyA
        ControlPlane -.->|Config Distribution| ProxyB
        ControlPlane -.->|Config Distribution| ProxyC

        Note2[Benefits:<br/>- Automatic retry and timeout<br/>- Automatic mTLS encryption<br/>- Unified metrics and tracing<br/>- Fine-grained traffic control]
    end

    classDef problem fill:#FFB74D,stroke:#333,stroke-width:2px,color:black;
    classDef solution fill:#66BB6A,stroke:#333,stroke-width:2px,color:white;
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef control fill:#E6522C,stroke:#333,stroke-width:2px,color:white;

    class Note1 problem;
    class Note2 solution;
    class AppA1,AppB1,AppC1,AppA2,AppB2,AppC2 app;
    class ProxyA,ProxyB,ProxyC proxy;
    class ControlPlane control;
```

#### アーキテクチャパターンの比較

```mermaid
flowchart LR
    subgraph "Istio - Sidecar Pattern"
        direction TB
        I_CP[Istiod<br/>Unified Control Plane<br/>1 Process]

        subgraph I_Pod1["Pod"]
            I_App1[App]
            I_Envoy1[Envoy<br/>Sidecar]
        end

        I_CP -->|xDS API| I_Envoy1
        I_App1 -->|localhost| I_Envoy1

        I_Note[Features:<br/>- Most feature-rich<br/>- Fine-grained L7 control<br/>- High resource usage<br/>- Complex operations]
    end

    subgraph "Linkerd - Micro-proxy Pattern"
        direction TB
        L_CP1[Destination<br/>Service Discovery]
        L_CP2[Identity<br/>Certificate Management]
        L_CP3[Proxy Injector<br/>Injection Management]

        subgraph L_Pod1["Pod"]
            L_App1[App]
            L_Proxy1[Linkerd2<br/>Rust Proxy]
        end

        L_CP1 --> L_Proxy1
        L_CP2 --> L_Proxy1
        L_CP3 -.-> L_Proxy1
        L_App1 -->|localhost| L_Proxy1

        L_Note[Features:<br/>- Most lightweight<br/>- Easy operations<br/>- Limited features<br/>- No VM support]
    end

    subgraph "Consul - Universal Pattern"
        direction TB
        C_Server[Consul Servers<br/>Distributed Cluster<br/>Service Catalog]

        subgraph C_Pod1["Pod"]
            C_App1[App]
            C_Client1[Consul<br/>Client]
            C_Envoy1[Envoy<br/>Proxy]
        end

        subgraph C_VM["VM"]
            C_App2[Legacy<br/>App]
            C_Client2[Consul<br/>Client]
            C_Envoy2[Envoy<br/>Proxy]
        end

        C_Client1 --> C_Server
        C_Client2 --> C_Server
        C_Server -->|Service Discovery| C_Envoy1
        C_Server -->|Service Discovery| C_Envoy2
        C_App1 --> C_Envoy1
        C_App2 --> C_Envoy2

        C_Note[Features:<br/>- VM-first support<br/>- Strong Service Discovery<br/>- Requires Consul infrastructure<br/>- Learning curve]
    end

    subgraph "Kong Mesh - Multi-zone Pattern"
        direction TB
        K_Global[Global CP<br/>Policy Sync]
        K_Zone1[Zone CP 1<br/>Local Management]
        K_Zone2[Zone CP 2<br/>Local Management]

        subgraph K_Pod1["K8s Pod"]
            K_App1[App]
            K_DP1[Kuma DP<br/>Envoy]
        end

        subgraph K_VM["VM"]
            K_App2[App]
            K_DP2[Kuma DP<br/>Envoy]
        end

        K_Global --> K_Zone1
        K_Global --> K_Zone2
        K_Zone1 --> K_DP1
        K_Zone2 --> K_DP2
        K_App1 --> K_DP1
        K_App2 --> K_DP2

        K_Note[Features:<br/>- Multi-cloud<br/>- K8s + VM equal support<br/>- Enterprise is paid<br/>- Small community]
    end

    classDef istio fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef linkerd fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef consul fill:#E6522C,stroke:#333,stroke-width:2px,color:white;
    classDef kong fill:#FF9900,stroke:#333,stroke-width:2px,color:black;
    classDef note fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class I_CP,I_Envoy1 istio;
    class L_CP1,L_CP2,L_CP3,L_Proxy1 linkerd;
    class C_Server,C_Client1,C_Client2,C_Envoy1,C_Envoy2 consul;
    class K_Global,K_Zone1,K_Zone2,K_DP1,K_DP2 kong;
    class I_Note,L_Note,C_Note,K_Note note;
```

### 詳細アーキテクチャ

#### Istio

```mermaid
flowchart TB
    subgraph "Control Plane"
        Istiod[Istiod<br/>Unified Control Plane]
    end

    subgraph "Data Plane"
        subgraph "Pod 1"
            App1[Application]
            Envoy1[Envoy Proxy]
        end
        subgraph "Pod 2"
            App2[Application]
            Envoy2[Envoy Proxy]
        end
    end

    subgraph "Configuration"
        VS[VirtualService]
        DR[DestinationRule]
        GW[Gateway]
        PA[PeerAuthentication]
        AP[AuthorizationPolicy]
    end

    Configuration -.->|xDS API| Istiod
    Istiod -->|Configuration| Envoy1
    Istiod -->|Configuration| Envoy2
    Envoy1 <-->|mTLS| Envoy2

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef config fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Istiod k8sComponent;
    class App1,App2 userApp;
    class Envoy1,Envoy2 userApp;
    class VS,DR,GW,PA,AP config;
```

**機能**:

* **Proxy**: Envoy (C++)
* **アーキテクチャ**: 統合 Control Plane (Istiod)
* **設定**: Kubernetes CRD (VirtualService, DestinationRule など)
* **強み**: 最も豊富な機能、大規模エンタープライズのサポート
* **弱み**: 学習曲線が急、リソースオーバーヘッドが大きい

**主要コンポーネント**:

* **Istiod**: Pilot + Citadel + Galley の統合
* **Envoy Proxy**: Data Plane
* **Ingress/Egress Gateway**: クラスター境界のトラフィック制御

### Linkerd

```mermaid
flowchart TB
    subgraph "Control Plane"
        Destination[Destination<br/>Service Discovery]
        Identity[Identity<br/>Certificate Authority]
        ProxyInjector[Proxy Injector<br/>Webhook]
    end

    subgraph "Data Plane"
        subgraph "Pod 1"
            App1[Application]
            LP1[Linkerd2-proxy<br/>Rust]
        end
        subgraph "Pod 2"
            App2[Application]
            LP2[Linkerd2-proxy<br/>Rust]
        end
    end

    ProxyInjector -.->|Inject| LP1
    ProxyInjector -.->|Inject| LP2
    Identity -->|Certificates| LP1
    Identity -->|Certificates| LP2
    Destination -->|Endpoints| LP1
    Destination -->|Endpoints| LP2
    LP1 <-->|mTLS| LP2

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class Destination,Identity,ProxyInjector k8sComponent;
    class App1,App2,LP1,LP2 userApp;
```

**機能**:

* **Proxy**: Linkerd2-proxy (Rust、カスタムビルド)
* **アーキテクチャ**: マイクロサービス Control Plane
* **設定**: Kubernetes ネイティブリソース + シンプルな Annotation
* **強み**: 超軽量、インストールと運用が容易、高速なパフォーマンス
* **弱み**: 機能が限定的、VM サポートなし

**主要コンポーネント**:

* **Destination**: Service Discovery とルーティングポリシー
* **Identity**: mTLS 証明書の自動発行
* **Proxy Injector**: Sidecar の自動注入

### Kong Mesh

```mermaid
flowchart TB
    subgraph "Global Control Plane (Optional)"
        KongGlobal[Kong Mesh<br/>Global Control Plane]
    end

    subgraph "Zone Control Plane"
        KongZone[Kong Mesh<br/>Zone Control Plane]
    end

    subgraph "Data Plane"
        subgraph "Pod 1"
            App1[Application]
            Envoy1[Envoy/Kuma DP]
        end
        subgraph "Pod 2"
            App2[Application]
            Envoy2[Envoy/Kuma DP]
        end
        subgraph "VM"
            AppVM[Legacy App]
            EnvoyVM[Kuma DP]
        end
    end

    KongGlobal -->|Sync Policies| KongZone
    KongZone -->|Configuration| Envoy1
    KongZone -->|Configuration| Envoy2
    KongZone -->|Configuration| EnvoyVM
    Envoy1 <-->|mTLS| Envoy2
    Envoy1 <-->|mTLS| EnvoyVM

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef vm fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    class KongGlobal,KongZone k8sComponent;
    class App1,App2,Envoy1,Envoy2 userApp;
    class AppVM,EnvoyVM vm;
```

**機能**:

* **Proxy**: Envoy (Kuma Data Plane)
* **アーキテクチャ**: Universal Control Plane (K8s + VM)
* **設定**: Kuma CRD + Kong Mesh UI
* **強み**: 優れた VM サポート、マルチゾーン/マルチクラウド、エンタープライズ機能
* **弱み**: 商用機能は有料、コミュニティが比較的小さい

**主要コンポーネント**:

* **Global Control Plane**: マルチゾーンポリシーの同期
* **Zone Control Plane**: ローカル Data Plane の管理
* **Kuma DP**: Kubernetes と VM 向けの Data Plane

#### Kong Mesh の詳細アーキテクチャ

Kong Mesh は Kuma をベースとする Universal Service Mesh であり、マルチゾーンアーキテクチャにより複数のクラスターと環境を単一の Mesh に統合します。

**マルチゾーンデプロイメントアーキテクチャ**

```mermaid
flowchart TB
    subgraph Global["Global Control Plane (Central Management)"]
        direction TB
        GCP[Kong Mesh Global<br/>Policy Store]
        GDB[(PostgreSQL<br/>Global State)]
    end

    subgraph Zone1["Zone 1 - AWS EKS"]
        direction TB
        ZCP1[Zone Control Plane 1]
        ZDB1[(Local State)]

        subgraph K8s1["Kubernetes Workloads"]
            direction LR
            subgraph Pod1["Pod A"]
                App1[Frontend]
                DP1[Kuma DP<br/>Envoy]
            end
            subgraph Pod2["Pod B"]
                App2[Backend]
                DP2[Kuma DP<br/>Envoy]
            end
        end
    end

    subgraph Zone2["Zone 2 - GCP GKE"]
        direction TB
        ZCP2[Zone Control Plane 2]
        ZDB2[(Local State)]

        subgraph K8s2["Kubernetes Workloads"]
            direction LR
            subgraph Pod3["Pod C"]
                App3[API Service]
                DP3[Kuma DP<br/>Envoy]
            end
        end
    end

    subgraph Zone3["Zone 3 - On-Premises"]
        direction TB
        ZCP3[Zone Control Plane 3]
        ZDB3[(Local State)]

        subgraph VM["Virtual Machines"]
            direction LR
            VM1[Legacy App]
            DPV[Kuma DP<br/>Envoy]
        end
    end

    %% Global to Zone connections
    GCP <-->|Policy Sync<br/>HTTP/gRPC| ZCP1
    GCP <-->|Policy Sync<br/>HTTP/gRPC| ZCP2
    GCP <-->|Policy Sync<br/>HTTP/gRPC| ZCP3
    GCP --> GDB

    %% Zone internal connections
    ZCP1 --> ZDB1
    ZCP1 -->|xDS Config| DP1
    ZCP1 -->|xDS Config| DP2

    ZCP2 --> ZDB2
    ZCP2 -->|xDS Config| DP3

    ZCP3 --> ZDB3
    ZCP3 -->|xDS Config| DPV

    %% App connections
    App1 --> DP1
    App2 --> DP2
    App3 --> DP3
    VM1 --> DPV

    %% Cross-Zone traffic
    DP1 <-.->|Cross-Zone mTLS| DP3
    DP2 <-.->|Cross-Zone mTLS| DPV

    classDef global fill:#E6522C,stroke:#333,stroke-width:2px,color:white;
    classDef zone fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef dataplane fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef vm fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef db fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    class GCP global;
    class ZCP1,ZCP2,ZCP3 zone;
    class DP1,DP2,DP3,App1,App2,App3 dataplane;
    class DPV,VM1 vm;
    class GDB,ZDB1,ZDB2,ZDB3 db;
```

**主な機能**:

* **Global Control Plane**: すべてのゾーンのポリシーを一元管理
* **Zone Control Plane**: 各ゾーンの Data Plane を独立して管理
* **自動 Service Discovery**: ゾーン間での Service Discovery を自動化
* **統合 mTLS**: ゾーン間通信も自動的に暗号化

**サービス接続とトラフィックフロー**

```mermaid
sequenceDiagram
    autonumber
    participant App as Application<br/>(Zone 1)
    participant DP1 as Kuma DP 1<br/>(Zone 1)
    participant ZCP1 as Zone CP 1
    participant GCP as Global CP
    participant ZCP2 as Zone CP 2
    participant DP2 as Kuma DP 2<br/>(Zone 2)
    participant Target as Target Service<br/>(Zone 2)

    Note over App,Target: Initial Setup Phase

    GCP->>ZCP1: Policy Sync<br/>(TrafficRoute, mTLS)
    GCP->>ZCP2: Policy Sync<br/>(TrafficRoute, mTLS)

    ZCP1->>DP1: xDS Configuration<br/>(Service Endpoints, Policies)
    ZCP2->>DP2: xDS Configuration<br/>(Service Endpoints, Policies)

    Note over App,Target: Service-to-Service Communication

    App->>DP1: HTTP Request (localhost)
    DP1->>DP1: Service Discovery<br/>(Check Zone 2 Endpoints)
    DP1->>DP2: mTLS Encrypted Request<br/>(Cross-Zone)
    DP2->>Target: Plaintext Request (localhost)
    Target->>DP2: Response
    DP2->>DP1: mTLS Encrypted Response
    DP1->>App: Plaintext Response

    Note over App,Target: Metrics and Tracing

    DP1->>ZCP1: Send Metrics
    DP2->>ZCP2: Send Metrics
    ZCP1->>GCP: Global Metrics Aggregation
    ZCP2->>GCP: Global Metrics Aggregation
```

**ポリシー伝播のメカニズム**

```mermaid
flowchart TD
    Start[Policy Create/Modify]
    Start --> Apply[kubectl apply -f policy.yaml]

    Apply --> Global{Apply to Global CP?}

    Global -->|Yes| GlobalStore[Global Control Plane<br/>Store Policy]
    Global -->|No| ZoneStore[Zone Control Plane<br/>Store Local Policy]

    GlobalStore --> Sync[Policy Sync]
    Sync --> Zone1[Zone CP 1 Receive]
    Sync --> Zone2[Zone CP 2 Receive]
    Sync --> Zone3[Zone CP 3 Receive]

    ZoneStore --> Zone1Apply[Apply Policy to<br/>that Zone CP only]

    Zone1 --> DP1[Data Plane 1<br/>xDS Update]
    Zone2 --> DP2[Data Plane 2<br/>xDS Update]
    Zone3 --> DP3[Data Plane 3<br/>xDS Update]
    Zone1Apply --> DP1

    DP1 --> Enforce1[Apply Envoy Config<br/>Real-time Traffic Control]
    DP2 --> Enforce2[Apply Envoy Config<br/>Real-time Traffic Control]
    DP3 --> Enforce3[Apply Envoy Config<br/>Real-time Traffic Control]

    classDef input fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef global fill:#E6522C,stroke:#333,stroke-width:2px,color:white;
    classDef zone fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef dataplane fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;

    class Start,Apply input;
    class GlobalStore,Sync global;
    class Zone1,Zone2,Zone3,ZoneStore,Zone1Apply zone;
    class DP1,DP2,DP3,Enforce1,Enforce2,Enforce3 dataplane;
```

**タイプ別のポリシー伝播スコープ**:

| ポリシータイプ           | スコープ  | 伝播方法             | ユースケース                          |
| --------------------- | ------ | ------------------ | --------------------------------- |
| **Mesh**              | Global | すべてのゾーン          | グローバル mTLS 設定              |
| **TrafficRoute**      | Global | すべてのゾーン          | グローバルルーティングルール              |
| **TrafficPermission** | Global | すべてのゾーン          | サービス間アクセス制御 |
| **HealthCheck**       | Zone   | ローカルゾーンのみ    | ゾーン固有のヘルスチェック       |
| **ProxyTemplate**     | Zone   | ローカルゾーンのみ    | ゾーン固有の Envoy 設定        |

**Data Plane のライフサイクル**

```mermaid
flowchart TB
    subgraph Init["Initialization Phase"]
        direction TB
        Start[Kuma DP Start]
        Start --> Token[Acquire Data Plane Token]
        Token --> Register[Register with Zone CP]
    end

    subgraph Config["Configuration Reception"]
        direction TB
        Register --> Connect[Establish gRPC Stream<br/>with Zone CP]
        Connect --> Receive[Receive xDS Configuration:<br/>- Listeners<br/>- Routes<br/>- Clusters<br/>- Endpoints]
    end

    subgraph Runtime["Runtime Operation"]
        direction TB
        Receive --> Proxy[Configure Envoy Proxy]
        Proxy --> Traffic[Traffic Proxy<br/>- mTLS Encrypt/Decrypt<br/>- Load Balancing<br/>- Health Check]
        Traffic --> Metrics[Metrics Collection<br/>- Request Count<br/>- Latency<br/>- Error Rate]
    end

    subgraph Update["Dynamic Update"]
        direction TB
        Metrics --> Watch[Detect Zone CP Changes]
        Watch --> UpdateConfig[Receive Config Update]
        UpdateConfig --> HotReload[Hot Reload<br/>Zero-downtime Apply]
        HotReload --> Traffic
    end

    subgraph Shutdown["Shutdown Phase"]
        direction TB
        Signal[SIGTERM Received]
        Signal --> Drain[Connection Draining<br/>Process Existing Connections]
        Drain --> Deregister[Deregister from Zone CP]
        Deregister --> Stop[Process Exit]
    end

    Metrics -.-> Signal

    classDef init fill:#66BB6A,stroke:#333,stroke-width:2px,color:white;
    classDef config fill:#42A5F5,stroke:#333,stroke-width:2px,color:white;
    classDef runtime fill:#FFA726,stroke:#333,stroke-width:2px,color:white;
    classDef update fill:#AB47BC,stroke:#333,stroke-width:2px,color:white;
    classDef shutdown fill:#EF5350,stroke:#333,stroke-width:2px,color:white;

    class Start,Token,Register init;
    class Connect,Receive config;
    class Proxy,Traffic,Metrics runtime;
    class Watch,UpdateConfig,HotReload update;
    class Signal,Drain,Deregister,Stop shutdown;
```

**ゾーン間 Service Discovery**

```mermaid
flowchart LR
    subgraph Zone1["Zone 1 - AWS"]
        direction TB
        Service1[Service: api<br/>Tag: version=v1]
        ZCP1[Zone CP 1]
        Service1 -.->|Register| ZCP1
    end

    subgraph Zone2["Zone 2 - GCP"]
        direction TB
        Service2[Service: api<br/>Tag: version=v2]
        ZCP2[Zone CP 2]
        Service2 -.->|Register| ZCP2
    end

    subgraph Zone3["Zone 3 - On-Prem"]
        direction TB
        Service3[Service: database<br/>Tag: tier=primary]
        ZCP3[Zone CP 3]
        Service3 -.->|Register| ZCP3
    end

    subgraph Global["Global Control Plane"]
        direction TB
        ServiceRegistry[Unified Service Registry<br/>api: [Zone1, Zone2]<br/>database: [Zone3]]
    end

    ZCP1 -->|Send Service Info| ServiceRegistry
    ZCP2 -->|Send Service Info| ServiceRegistry
    ZCP3 -->|Send Service Info| ServiceRegistry

    ServiceRegistry -->|Distribute Unified Service Map| ZCP1
    ServiceRegistry -->|Distribute Unified Service Map| ZCP2
    ServiceRegistry -->|Distribute Unified Service Map| ZCP3

    subgraph Client["Client (Zone 1)"]
        direction TB
        App[Application]
        DP[Kuma DP]
        App --> DP
    end

    DP -.->|1. Request api service| ZCP1
    ZCP1 -.->|2. Return Endpoints<br/>Zone1: 10.0.1.10<br/>Zone2: 10.1.1.10| DP
    DP -.->|3. Local-first Routing<br/>Zone1: 80%<br/>Zone2: 20%| Service1
    DP -.->|4. Cross-Zone Routing| Service2

    classDef zone fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef service fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef global fill:#E6522C,stroke:#333,stroke-width:2px,color:white;
    classDef client fill:#FF9900,stroke:#333,stroke-width:2px,color:black;

    class ZCP1,ZCP2,ZCP3 zone;
    class Service1,Service2,Service3 service;
    class ServiceRegistry global;
    class App,DP client;
```

**Service Discovery の機能**:

* **自動登録**: 各ゾーンの Service は Zone CP に自動登録されます
* **グローバルビュー**: Global CP はすべてのゾーンの Service を統合します
* **ローカル優先**: 同一ゾーン内の Service を優先してルーティングします
* **自動フェイルオーバー**: ローカル Service が失敗すると別のゾーンへ自動的に切り替えます
* **タグベースルーティング**: Service タグを使用したきめ細かなルーティング制御

**Kong Mesh の設定例**

**Mesh リソース（グローバル mTLS 設定）**:

```yaml
apiVersion: kuma.io/v1alpha1
kind: Mesh
metadata:
  name: default
spec:
  # Enable global mTLS
  mtls:
    enabledBackend: ca-1
    backends:
    - name: ca-1
      type: builtin
      dpCert:
        rotation:
          expiration: 24h
      conf:
        caCert:
          RSAbits: 2048
          expiration: 10y
  # Global metrics collection
  metrics:
    enabledBackend: prometheus-1
    backends:
    - name: prometheus-1
      type: prometheus
      conf:
        port: 5670
        path: /metrics
```

**TrafficRoute（ゾーン間ルーティング）**:

```yaml
apiVersion: kuma.io/v1alpha1
kind: TrafficRoute
metadata:
  name: api-route
  namespace: kuma-system
spec:
  sources:
  - match:
      kuma.io/service: '*'
  destinations:
  - match:
      kuma.io/service: api
  conf:
    # Local zone priority (80%)
    loadBalancer:
      roundRobin: {}
    split:
    - weight: 80
      destination:
        kuma.io/service: api
        kuma.io/zone: zone-1
    - weight: 20
      destination:
        kuma.io/service: api
        kuma.io/zone: zone-2
```

**TrafficPermission（サービス間アクセス制御）**:

```yaml
apiVersion: kuma.io/v1alpha1
kind: TrafficPermission
metadata:
  name: api-to-database
  namespace: kuma-system
spec:
  sources:
  - match:
      kuma.io/service: api
      kuma.io/zone: '*'  # api service from all zones
  destinations:
  - match:
      kuma.io/service: database
      kuma.io/zone: zone-3  # database in Zone 3 only
```

**Kong Mesh アーキテクチャの利点**

**マルチゾーンアーキテクチャ**:

* **グローバル Service Mesh**: 複数のクラスターと環境を単一の Mesh に統合
* **独立したゾーン管理**: 各ゾーンは独立して動作し、Global CP が失敗してもローカルトラフィックは正常に機能します
* **自動フェイルオーバー**: ゾーン障害時に別のゾーンへ自動的に切り替えます
* **ポリシーの一貫性**: 同じポリシーがすべてのゾーンに自動適用されます

**ユニバーサルサポート**:

* **Kubernetes + VM**: K8s と VM を同等にサポート
* **マルチクラウド**: AWS、GCP、Azure、オンプレミスを統合
* **レガシー統合**: 既存の VM ワークロードを段階的に Mesh に追加

**運用の利便性**:

* **GUI 提供**: Kong Mesh GUI による視覚的な管理
* **ポリシーテンプレート**: 事前定義済みのポリシーテンプレートを提供
* **自動 Service Discovery**: 手動設定なしで Service を自動検出

**エンタープライズ機能**（有料）:

* **RBAC**: きめ細かなロールベースのアクセス制御
* **マルチテナンシー**: ゾーンレベルの分離と管理
* **24/7 サポート**: 本番環境向けのプロフェッショナルサポート
* **高度な可観測性**: 詳細なメトリクスとトレーシング

### Consul Connect

```mermaid
flowchart TB
    subgraph "Consul Servers"
        ConsulServer[Consul Server Cluster<br/>Service Catalog + KV Store]
    end

    subgraph "Kubernetes Cluster"
        subgraph "Pod 1"
            App1[Application]
            ConsulClient1[Consul Client]
            EnvoyProxy1[Envoy Sidecar]
        end
        subgraph "Pod 2"
            App2[Application]
            ConsulClient2[Consul Client]
            EnvoyProxy2[Envoy Sidecar]
        end
    end

    subgraph "VM Infrastructure"
        AppVM[Legacy Application]
        ConsulClientVM[Consul Client]
        EnvoyVM[Envoy Proxy]
    end

    ConsulClient1 -->|Service Registration| ConsulServer
    ConsulClient2 -->|Service Registration| ConsulServer
    ConsulClientVM -->|Service Registration| ConsulServer
    ConsulServer -->|Service Discovery| EnvoyProxy1
    ConsulServer -->|Service Discovery| EnvoyProxy2
    ConsulServer -->|Service Discovery| EnvoyVM
    EnvoyProxy1 <-->|mTLS| EnvoyProxy2
    EnvoyProxy1 <-->|mTLS| EnvoyVM

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef vm fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    class ConsulServer,ConsulClient1,ConsulClient2 k8sComponent;
    class App1,App2,EnvoyProxy1,EnvoyProxy2 userApp;
    class AppVM,ConsulClientVM,EnvoyVM vm;
```

**機能**:

* **Proxy**: Envoy または Built-in Proxy
* **アーキテクチャ**: Consul Server Cluster + Consul Client
* **設定**: HCL または Kubernetes CRD
* **強み**: 強力な Service Discovery、VM ファーストの設計、マルチデータセンター
* **弱み**: Consul インフラストラクチャの管理が必要、Kubernetes 統合は Istio より複雑

**主要コンポーネント**:

* **Consul Server**: Service Catalog、KV Store、証明書管理
* **Consul Client**: 各ノードで実行、Service 登録
* **Envoy Sidecar**: トラフィック Proxy

## パフォーマンス比較

### レイテンシーオーバーヘッド

```mermaid
flowchart LR
    subgraph "Baseline"
        B[Direct K8s Service<br/>0.1ms]
    end

    subgraph "Linkerd"
        L[Linkerd2-proxy<br/>+0.5-1ms]
    end

    subgraph "Istio"
        I[Envoy Proxy<br/>+1-3ms]
    end

    subgraph "Kong Mesh"
        K[Kuma DP<br/>+1-2.5ms]
    end

    subgraph "Consul"
        C[Envoy/Built-in<br/>+1-3ms]
    end

    B -.->|Lightweight Proxy| L
    B -.->|Feature-rich| I
    B -.->|Medium| K
    B -.->|Medium| C

    classDef baseline fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef fast fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef medium fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    class B baseline;
    class L fast;
    class I,K,C medium;
```

**ベンチマーク結果**（P99 レイテンシーの増加、1000 RPS）:

| Service Mesh       | P50    | P95    | P99    | CPU 使用率 | メモリ使用量 |
| ------------------ | ------ | ------ | ------ | --------- | ------------ |
| **Baseline**       | 0.1ms  | 0.2ms  | 0.3ms  | -         | -            |
| **Linkerd**        | +0.5ms | +0.8ms | +1.2ms | +3-8%     | +20-50MB     |
| **Istio**          | +1.0ms | +2.5ms | +3.5ms | +5-15%    | +50-150MB    |
| **Kong Mesh**      | +0.8ms | +2.0ms | +3.0ms | +5-12%    | +40-120MB    |
| **Consul Connect** | +1.0ms | +2.5ms | +3.5ms | +6-14%    | +50-140MB    |

**テスト環境**: 3 ノード EKS 1.28、m5.xlarge、100 Service、1000 RPS

### リソース使用量の比較

#### Control Plane リソース

| コンポーネント    | Istio      | Linkerd             | Kong Mesh     | Consul Connect       |
| ------------ | ---------- | ------------------- | ------------- | -------------------- |
| **CPU**      | 500m-1     | 100m-300m           | 200m-500m     | 500m-1               |
| **メモリ**   | 1-2GB      | 200-500MB           | 500MB-1GB     | 1-2GB                |
| **レプリカ数** | 1 (Istiod) | 3-5 (マイクロサービス) | 1-2 (Zone CP) | 3-5 (Consul Server) |

#### Data Plane リソース（Pod ごと）

| Proxy      | Istio Envoy | Linkerd2-proxy | Kuma DP  | Consul Envoy |
| ---------- | ----------- | -------------- | -------- | ------------ |
| **CPU**    | 100-500m    | 20-100m        | 100-400m | 100-500m     |
| **メモリ** | 50-150MB    | 20-50MB        | 40-120MB | 50-140MB     |

### スループットの比較

**最大 RPS（Requests Per Second）**:

```mermaid
flowchart LR
    subgraph Throughput[Throughput Comparison]
        direction TB
        L[Linkerd<br/>~95-98% of baseline]
        K[Kong Mesh<br/>~90-95% of baseline]
        I[Istio<br/>~85-92% of baseline]
        C[Consul<br/>~85-92% of baseline]
    end

    classDef high fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef medium fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    class L high;
    class I,K,C medium;
```

**結論**:

* **Linkerd**: 最小のオーバーヘッド、軽量な Proxy
* **Istio/Consul**: 機能が多いため、オーバーヘッドはやや大きい
* **Kong Mesh**: 中程度のパフォーマンスレベル

## 機能比較

### 総合機能比較表

| 機能領域               | Istio             | Linkerd   | Kong Mesh    | Consul Connect |
| -------------------------- | ----------------- | --------- | ------------ | -------------- |
| **トラフィック管理**     |                   |           |              |                |
| トラフィック分割（Canary） | きめ細かい      | 基本     | きめ細かい | 基本          |
| A/B テスト                | Header ベース      | 限定的   | Header ベース | 限定的        |
| Blue-Green                 | はい               | はい       | はい          | はい            |
| トラフィックミラーリング          | はい               | いいえ        | はい          | Enterprise     |
| Circuit Breaking           | はい               | 基本     | はい          | はい            |
| Retry                      | きめ細かい      | 基本     | きめ細かい | 基本          |
| Timeout                    | はい               | はい       | はい          | はい            |
| Fault Injection            | はい               | 限定的   | はい          | 限定的        |
| **セキュリティ**               |                   |           |              |                |
| mTLS 自動化            | はい               | はい       | はい          | はい            |
| Authorization Policy     | 非常にきめ細かい | 基本     | きめ細かい | Intentions     |
| 外部 CA 統合    | はい               | はい       | はい          | はい            |
| JWT 認証         | はい               | 限定的   | はい          | はい            |
| Rate Limiting              | EnvoyFilter       | いいえ        | はい          | Enterprise     |
| **可観測性**          |                   |           |              |                |
| メトリクス（Prometheus）       | 豊富              | 基本     | 豊富         | 基本          |
| 分散トレーシング        | すべてのバックエンド      | Jaeger    | すべてのバックエンド | Jaeger/Zipkin  |
| Access Log                | 非常に詳細     | 基本     | 詳細     | 基本          |
| トポロジーの可視化     | Kiali             | Dashboard | GUI          | UI             |
| OpenTelemetry              | はい               | はい       | はい          | はい            |
| **プラットフォームサポート**       |                   |           |              |                |
| Kubernetes                 | はい               | はい       | はい          | はい            |
| Virtual Machine           | 限定的           | いいえ        | 優れている    | 優れている      |
| マルチクラスター              | 優れている         | サポート対象 | 優れている    | 優れている      |
| Service Discovery          | はい               | はい       | はい          | 非常に強力    |
| **運用**             |                   |           |              |                |
| インストールの複雑さ    | 高い              | 低い       | 中程度       | 中程度         |
| アップグレード                    | 中程度            | 容易      | 中程度       | 中程度         |
| トラブルシューティング            | 困難         | 容易      | 中程度       | 中程度         |
| CLI ツール                   | istioctl          | linkerd   | kumactl      | consul         |

**凡例**:

* はい = 完全にサポート
* 限定的 = サポートが限定的、または Enterprise 機能
* いいえ = サポートされていない

### トラフィック管理の詳細比較

#### Canary Deployment の例

**Istio**:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: reviews
        subset: v2
      weight: 100
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
---
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

**Linkerd**:

```yaml
apiVersion: split.smi-spec.io/v1alpha2
kind: TrafficSplit
metadata:
  name: reviews-split
spec:
  service: reviews
  backends:
  - service: reviews-v1
    weight: 90
  - service: reviews-v2
    weight: 10
---
# Requires separate Service creation
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
spec:
  selector:
    app: reviews
    version: v1
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
spec:
  selector:
    app: reviews
    version: v2
```

**Kong Mesh**:

```yaml
apiVersion: kuma.io/v1alpha1
kind: TrafficRoute
metadata:
  name: reviews-route
spec:
  sources:
  - match:
      kuma.io/service: '*'
  destinations:
  - match:
      kuma.io/service: reviews
  conf:
    split:
    - weight: 90
      destination:
        kuma.io/service: reviews
        version: v1
    - weight: 10
      destination:
        kuma.io/service: reviews
        version: v2
```

**Consul Connect**:

```hcl
Kind = "service-splitter"
Name = "reviews"
Splits = [
  {
    Weight        = 90
    ServiceSubset = "v1"
  },
  {
    Weight        = 10
    ServiceSubset = "v2"
  },
]
```

**比較**:

* **Istio**: 最もきめ細かな制御（Header ベースのルーティング、さまざまなマッチ条件）
* **Linkerd**: シンプルですが、個別の Service 作成が必要
* **Kong Mesh**: Kuma CRD、直感的
* **Consul**: HCL 設定、Service Discovery と統合

## セキュリティ機能

### mTLS 設定の比較

**Istio**:

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: default
  namespace: istio-system
spec:
  host: "*.local"
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```

**Linkerd**:

```bash
# mTLS enabled automatically (no configuration needed)
linkerd install | kubectl apply -f -

# Add annotation to namespace
kubectl annotate namespace default linkerd.io/inject=enabled
```

**Kong Mesh**:

```yaml
apiVersion: kuma.io/v1alpha1
kind: Mesh
metadata:
  name: default
spec:
  mtls:
    enabledBackend: ca-1
    backends:
    - name: ca-1
      type: builtin
      dpCert:
        rotation:
          expiration: 24h
      conf:
        caCert:
          RSAbits: 2048
          expiration: 10y
```

**Consul Connect**:

```hcl
Kind = "mesh"
Meta = {
  "consul.hashicorp.com/gateway-kind" = "mesh-gateway"
}
TLS {
  Incoming {
    TLSMinVersion = "TLSv1_2"
  }
}
```

### Authorization Policy の比較

**Istio**（最もきめ細かい）:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: reviews-policy
spec:
  selector:
    matchLabels:
      app: reviews
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/productpage"]
    to:
    - operation:
        methods: ["GET"]
        paths: ["/reviews/*"]
    when:
    - key: request.headers[user-agent]
      values: ["*Mobile*"]
```

**Linkerd**:

```yaml
apiVersion: policy.linkerd.io/v1beta1
kind: Server
metadata:
  name: reviews-server
spec:
  podSelector:
    matchLabels:
      app: reviews
  port: 9080
  proxyProtocol: HTTP/1
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: reviews-policy
spec:
  targetRef:
    kind: Server
    name: reviews-server
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: productpage
```

**Kong Mesh**:

```yaml
apiVersion: kuma.io/v1alpha1
kind: TrafficPermission
metadata:
  name: reviews-permission
spec:
  sources:
  - match:
      kuma.io/service: productpage
  destinations:
  - match:
      kuma.io/service: reviews
```

**Consul Connect**（Intentions）:

```hcl
Kind = "service-intentions"
Name = "reviews"
Sources = [
  {
    Name   = "productpage"
    Action = "allow"
  }
]
```

**比較**:

* **Istio**: 非常にきめ細かな L7 制御（Method、Path、Header）
* **Linkerd**: Service Account ベース、シンプル
* **Kong Mesh**: Service レベルの権限
* **Consul**: Intentions ベース、直感的

## 可観測性機能

### メトリクス収集

**Istio**:

* **メトリクス数**: デフォルトで 50 以上のメトリクス
* **カスタマイズ**: EnvoyFilter による無制限の拡張
* **統合**: Prometheus、Grafana、Kiali

**Linkerd**:

* **メトリクス数**: デフォルトで 20 以上のメトリクス（ゴールデンシグナルに注力）
* **カスタマイズ**: 限定的
* **統合**: Prometheus、Grafana、Linkerd Dashboard

**Kong Mesh**:

* **メトリクス数**: デフォルトで 40 以上のメトリクス
* **カスタマイズ**: Datadog、Prometheus
* **統合**: Kong Mesh GUI、Grafana

**Consul Connect**:

* **メトリクス数**: デフォルトで 30 以上のメトリクス
* **カスタマイズ**: Telegraf 統合
* **統合**: Consul UI、Prometheus、Grafana

### 分散トレーシング

**サポートされるバックエンド**:

| Service Mesh  | Jaeger | Zipkin | Tempo   | Datadog | AWS X-Ray |
| ------------- | ------ | ------ | ------- | ------- | --------- |
| **Istio**     | はい    | はい    | はい    | はい    | はい       |
| **Linkerd**   | はい    | はい    | はい    | 限定的 | 限定的     |
| **Kong Mesh** | はい    | はい    | はい    | はい    | はい       |
| **Consul**    | はい    | はい    | 限定的 | 限定的 | 限定的     |

### 可視化ツール

**Istio + Kiali**:

```yaml
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata:
  name: kiali
spec:
  deployment:
    accessible_namespaces: ["**"]
  external_services:
    prometheus:
      url: http://prometheus:9090
    grafana:
      url: http://grafana:3000
    tracing:
      url: http://jaeger-query:16686
```

**Linkerd Dashboard**:

```bash
linkerd viz install | kubectl apply -f -
linkerd viz dashboard
```

**Kong Mesh GUI**:

```yaml
apiVersion: kuma.io/v1alpha1
kind: Mesh
metadata:
  name: default
spec:
  metrics:
    enabledBackend: prometheus-1
    backends:
    - name: prometheus-1
      type: prometheus
```

**Consul UI**:

```hcl
ui_config {
  enabled = true
  metrics_provider = "prometheus"
  metrics_proxy {
    base_url = "http://prometheus:9090"
  }
}
```

## マルチクラスターサポート

### アーキテクチャ比較

**Istio Multi-Primary**:

```mermaid
flowchart TB
    subgraph Cluster1["Cluster 1 (us-west)"]
        Istiod1[Istiod]
        App1[Service A v1]
        App2[Service B]
    end

    subgraph Cluster2["Cluster 2 (us-east)"]
        Istiod2[Istiod]
        App3[Service A v2]
        App4[Service C]
    end

    Istiod1 <-.->|Service Discovery| Istiod2
    App1 <-->|Cross-cluster mTLS| App3
    App2 <-->|Cross-cluster mTLS| App4

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class Istiod1,Istiod2 k8sComponent;
    class App1,App2,App3,App4 userApp;
```

**Linkerd Multi-cluster**:

```mermaid
flowchart TB
    subgraph Cluster1["Source Cluster"]
        LinkerdCtl1[Linkerd Control Plane]
        Gateway1[Gateway]
        App1[Service A]
    end

    subgraph Cluster2["Target Cluster"]
        LinkerdCtl2[Linkerd Control Plane]
        Gateway2[Gateway]
        App2[Service A Mirror]
    end

    App1 -->|Route through| Gateway1
    Gateway1 <-->|mTLS| Gateway2
    Gateway2 --> App2

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class LinkerdCtl1,LinkerdCtl2,Gateway1,Gateway2 k8sComponent;
    class App1,App2 userApp;
```

**Kong Mesh Multi-zone**:

```mermaid
flowchart TB
    subgraph Global["Global Control Plane"]
        KongGlobal[Kong Mesh Global]
    end

    subgraph Zone1["Zone 1 (AWS)"]
        KongZone1[Zone CP]
        App1[Services]
    end

    subgraph Zone2["Zone 2 (Azure)"]
        KongZone2[Zone CP]
        App2[Services]
    end

    subgraph Zone3["Zone 3 (On-prem)"]
        KongZone3[Zone CP]
        App3[Services]
    end

    KongGlobal -->|Sync Policies| KongZone1
    KongGlobal -->|Sync Policies| KongZone2
    KongGlobal -->|Sync Policies| KongZone3
    App1 <-->|Cross-zone| App2
    App1 <-->|Cross-zone| App3

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class KongGlobal,KongZone1,KongZone2,KongZone3 k8sComponent;
    class App1,App2,App3 userApp;
```

**Consul Multi-datacenter**:

```mermaid
flowchart TB
    subgraph DC1["Datacenter 1"]
        ConsulServer1[Consul Servers]
        Gateway1[Mesh Gateway]
        App1[Services]
    end

    subgraph DC2["Datacenter 2"]
        ConsulServer2[Consul Servers]
        Gateway2[Mesh Gateway]
        App2[Services]
    end

    ConsulServer1 <-.->|WAN Gossip| ConsulServer2
    Gateway1 <-->|Mesh Gateway| Gateway2
    App1 -.->|Service Discovery| ConsulServer1
    App2 -.->|Service Discovery| ConsulServer2

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class ConsulServer1,ConsulServer2,Gateway1,Gateway2 k8sComponent;
    class App1,App2 userApp;
```

### マルチクラスター機能の比較

| 機能                      | Istio           | Linkerd         | Kong Mesh       | Consul    |
| ---------------------------- | --------------- | --------------- | --------------- | --------- |
| **設定の複雑さ** | 中程度          | 低い             | 中程度          | 中程度    |
| **Service Discovery**        | 自動       | Mirror Service | 自動       | 強力    |
| **トラフィックフェイルオーバー**         | 自動       | 手動          | 自動       | 自動 |
| **mTLS**                     | 自動       | Gateway 経由 | 自動       | 自動 |
| **ネットワーク要件**     | Flat または Gateway | Gateway         | Flat または Gateway | Gateway   |
| **ポリシー同期**              | はい             | 限定的         | Global CP       | はい       |
| **最大クラスター数**        | 数十個          | \~10            | 数十個          | 数十個    |

## 運用の複雑さ

### インストールとアップグレード

**Istio**:

```bash
# Install
istioctl install --set profile=default

# Upgrade (Canary)
istioctl install --set profile=default --revision=1-24-0

# Sequential transition per namespace
kubectl label namespace default istio.io/rev=1-24-0 --overwrite
kubectl rollout restart deployment -n default
```

**Linkerd**:

```bash
# Install
linkerd install | kubectl apply -f -

# Upgrade (In-place)
linkerd upgrade | kubectl apply -f -

# Automatic rollout
```

**Kong Mesh**:

```bash
# Helm install
helm install kong-mesh kong-mesh/kong-mesh

# Upgrade
helm upgrade kong-mesh kong-mesh/kong-mesh
```

**Consul**:

```bash
# Helm install
helm install consul hashicorp/consul -f values.yaml

# Upgrade
helm upgrade consul hashicorp/consul -f values.yaml
```

**比較**:

* **Linkerd**: 最も簡単なインストールとアップグレード
* **Istio**: Canary アップグレードによりダウンタイムなしを実現できますが、複雑です
* **Kong/Consul**: Helm ベース、中程度の複雑さ

### トラブルシューティングツール

**Istio**:

```bash
# Check proxy status
istioctl proxy-status

# Validate configuration
istioctl analyze

# Check proxy configuration
istioctl proxy-config cluster <pod> -n <namespace>

# Change log level
istioctl proxy-config log <pod> --level debug
```

**Linkerd**:

```bash
# Check status
linkerd check

# Check statistics
linkerd stat deploy

# Tap (real-time traffic observation)
linkerd tap deploy/webapp

# Check profile
linkerd profile --template deploy/webapp
```

**Kong Mesh**:

```bash
# Check status
kumactl inspect dataplanes

# Check metrics
kumactl inspect meshes

# Check logs
kubectl logs -n kong-mesh-system deployment/kong-mesh-control-plane
```

**Consul**:

```bash
# Check status
consul members

# Check services
consul catalog services

# Check intentions
consul intention list

# Proxy logs
kubectl logs <pod> -c consul-connect-envoy-sidecar
```

### 学習曲線

```mermaid
flowchart LR
    subgraph "Learning Difficulty"
        direction TB
        Easy[Easy<br/>Linkerd]
        Medium[Medium<br/>Kong Mesh<br/>Consul]
        Hard[Difficult<br/>Istio]
    end

    Easy -->|Basic features only| Use1[Quick Start]
    Medium -->|Balanced features| Use2[Medium Scale]
    Hard -->|All features| Use3[Large Enterprise]

    classDef easy fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef medium fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef hard fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    class Easy easy;
    class Medium medium;
    class Hard hard;
```

## コスト分析

### インフラストラクチャコスト

**リソースベースのコスト計算**（100 Pod 環境、EKS m5.xlarge）:

| Service Mesh  | Control Plane CPU | Control Plane メモリ | Data Plane CPU（合計） | Data Plane メモリ（合計） | 月額コスト（概算） |
| ------------- | ----------------- | -------------------- | ---------------------- | ------------------------- | ------------------- |
| **Baseline**  | -                 | -                    | -                      | -                         | $300                |
| **Linkerd**   | 300m              | 500MB                | 2 vCPU                 | 5GB                       | +$50 (\~$350)       |
| **Istio**     | 1 vCPU            | 2GB                  | 10 vCPU                | 15GB                      | +$150 (\~$450)      |
| **Kong Mesh** | 500m              | 1GB                  | 8 vCPU                 | 12GB                      | +$120 (\~$420)      |
| **Consul**    | 1 vCPU            | 2GB                  | 10 vCPU                | 14GB                      | +$145 (\~$445)      |

**注記**: 実際のコストは、ワークロードパターン、トラフィック量、設定によって大きく異なる場合があります。

### 運用コスト

**エンジニアの工数（月次）**:

| タスク                 | Istio      | Linkerd    | Kong Mesh  | Consul     |
| -------------------- | ---------- | ---------- | ---------- | ---------- |
| **初期セットアップ**    | 40h        | 8h         | 20h        | 24h        |
| **日次運用** | 20h/month  | 5h/month   | 10h/month  | 12h/month  |
| **トラブルシューティング**  | 15h/month  | 3h/month   | 8h/month   | 10h/month  |
| **アップグレード**         | 8h/quarter | 2h/quarter | 4h/quarter | 5h/quarter |

### ライセンスコスト

| 製品       | オープンソース       | Enterprise                              |
| ------------- | ----------------- | --------------------------------------- |
| **Istio**     | 無料（Apache 2.0） | Google Cloud Service Mesh（使用量ベース） |
| **Linkerd**   | 無料（Apache 2.0） | Buoyant Enterprise (\$$$)               |
| **Kong Mesh** | Kuma Open Source  | Kong Mesh Enterprise（要問い合わせ） |
| **Consul**    | 無料（MPL 2.0）    | Consul Enterprise (\$$$)                |

**Enterprise 機能の例**:

* **Kong Mesh Enterprise**: マルチゾーン GUI、RBAC、24/7 サポート
* **Consul Enterprise**: 監査ログ、Namespace、冗長化ゾーン
* **Buoyant Enterprise**: HA Control Plane、24/7 サポート、SLA

## ユースケースの推奨事項

### 1. 大規模エンタープライズ（1000 以上の Service）

**推奨: Istio**

**理由**:

* 最も豊富な機能セット
* きめ細かなトラフィック制御（A/B テスト、Canary）
* 強力なセキュリティ（L7 Authorization）
* マルチクラスター連携
* 広範なコミュニティとツールエコシステム

**設定例**:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: production
  components:
    pilot:
      k8s:
        hpaSpec:
          minReplicas: 3
          maxReplicas: 10
        resources:
          requests:
            cpu: 2000m
            memory: 4Gi
```

### 2. 小規模から中規模のスタートアップ（10～100 Service）

**推奨: Linkerd**

**理由**:

* 短時間でのインストール（5 分未満）
* 低いリソースオーバーヘッド
* シンプルな運用
* 自動 mTLS とメトリクス

**設定例**:

```bash
linkerd install | kubectl apply -f -
linkerd viz install | kubectl apply -f -

# Enable per namespace
kubectl annotate namespace default linkerd.io/inject=enabled
```

### 3. ハイブリッドクラウド（K8s + VM）

**推奨: Consul Connect または Kong Mesh**

**理由**:

* VM ワークロードを優先するサポート
* 強力な Service Discovery
* マルチプラットフォームでの一貫性

**Consul の設定例**:

```hcl
# In Kubernetes
service {
  name = "web"
  port = 8080
  connect {
    sidecar_service {}
  }
}

# In VM
service {
  name = "database"
  port = 5432
  connect {
    sidecar_service {
      proxy {
        upstreams = [
          {
            destination_name = "web"
            local_bind_port  = 8080
          }
        ]
      }
    }
  }
}
```

### 4. マルチクラウド戦略

**推奨: Istio または Kong Mesh**

**理由**:

* クラウド中立
* 一貫したポリシーと可観測性
* マルチクラスター連携

**Istio マルチクラスター**:

```bash
# Cluster 1 (AWS)
istioctl install --set values.global.meshID=mesh1 \
  --set values.global.multiCluster.clusterName=aws-cluster \
  --set values.global.network=aws-network

# Cluster 2 (GCP)
istioctl install --set values.global.meshID=mesh1 \
  --set values.global.multiCluster.clusterName=gcp-cluster \
  --set values.global.network=gcp-network

# Share Service Discovery
istioctl create-remote-secret \
  --context=aws-cluster --name=aws-cluster | \
  kubectl apply -f - --context=gcp-cluster
```

### 5. レガシー移行

**推奨: Kong Mesh または Consul**

**理由**:

* VM とコンテナを同時にサポート
* 段階的な移行
* 既存の Service Discovery との統合

**Kong Mesh ハイブリッド**:

```yaml
# Kubernetes Service
apiVersion: v1
kind: Service
metadata:
  name: legacy-db
  annotations:
    kuma.io/mesh: default
spec:
  type: ExternalName
  externalName: legacy-db.vm.local
---
# Run Kuma DP on VM
kuma-dp run \
  --cp-address=https://kong-mesh-cp:5678 \
  --dataplane-token-file=/tmp/token \
  --dataplane-file=/etc/kuma/dataplane.yaml
```

### 6. 強力な可観測性要件

**推奨: Istio**

**理由**:

* デフォルトで 50 以上のメトリクス
* 詳細な Access Log
* すべてのトレーシングバックエンドをサポート
* Kiali 統合

**可観測性スタック**:

```yaml
# Prometheus + Grafana + Jaeger + Kiali
istioctl install --set profile=demo \
  --set values.prometheus.enabled=true \
  --set values.grafana.enabled=true \
  --set values.tracing.enabled=true \
  --set values.kiali.enabled=true
```

## 最終結論と推奨事項

### 決定木

```mermaid
flowchart TD
    Start[Service Mesh Selection]
    Start --> Q1{Team Experience?}

    Q1 -->|New to Service Mesh| Simple[Simple Solution]
    Q1 -->|Experienced| Advanced[Advanced Features]

    Simple --> Q2{Resource Constraints?}
    Q2 -->|Yes, Efficiency Important| Linkerd[Linkerd]
    Q2 -->|No, Features Needed| KongSimple[Kong Mesh<br/>or Consul]

    Advanced --> Q3{Platform?}
    Q3 -->|K8s Only| Q4{Feature Requirements?}
    Q3 -->|K8s + VM| Hybrid[Kong/Consul]

    Q4 -->|Maximum Features| Istio[Istio]
    Q4 -->|Balanced| KongAdv[Kong Mesh]

    Hybrid --> Q5{VM-centric?}
    Q5 -->|Yes| Consul[Consul]
    Q5 -->|No, K8s-centric| Kong[Kong Mesh]

    classDef recommended fill:#00C7B7,stroke:#333,stroke-width:3px,color:white;
    classDef decision fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Linkerd,Istio,Consul,Kong recommended;
    class Start,Q1,Q2,Q3,Q4,Q5 decision;
```

### クイック推奨ガイド

| 状況                | 第 1 選択 | 第 2 選択 | 避けるべき選択                      |
| ------------------------ | ---------- | ---------- | -------------------------- |
| **導入開始時**      | Linkerd    | Kong Mesh  | Istio（複雑）            |
| **大規模エンタープライズ**     | Istio      | Kong Mesh  | Linkerd（機能が限定的） |
| **リソース制約** | Linkerd    | -          | Istio（オーバーヘッド）           |
| **VM ワークロード**         | Consul     | Kong Mesh  | Linkerd（サポートなし）       |
| **マルチクラウド**          | Istio      | Consul     | 単一クラウドソリューション     |
| **迅速な ROI**            | Linkerd    | -          | Istio（学習曲線）     |
| **きめ細かな制御** | Istio      | Kong Mesh  | Linkerd（限定的）          |

### 最終推奨事項

**Istio**:

* **使用する場面**: 大規模エンタープライズ、豊富な機能が必要、チームに Service Mesh の経験がある場合
* **長所**: クラス最高の機能、強力なコミュニティ、将来志向
* **短所**: 学習曲線が急、リソース使用量が多い

**Linkerd**:

* **使用する場面**: シンプルさを最優先、小規模チーム、迅速な開始、リソース効率
* **長所**: インストール/運用がシンプル、低オーバーヘッド、自動 mTLS
* **短所**: 機能が限定的、VM サポートなし

**Kong Mesh / Consul Connect**:

* **使用する場面**: ハイブリッド環境（K8s + VM）、マルチプラットフォーム、レガシー統合
* **長所**: VM ファーストのサポート、柔軟なアーキテクチャ、強力な Service Discovery
* **短所**: 商用機能は有料、コミュニティ規模

***

**次のステップ**:

1. PoC 環境で 2～3 のソリューションをテストする
2. 実際のワークロードパターンでパフォーマンスベンチマークを実施する
3. チームのフィードバックを収集する
4. 本番ロールアウト計画を策定する

**関連ドキュメント**:

* [Istio と VPC Lattice の比較](02-istio-vs-lattice.md)
* [Istio アーキテクチャ](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/istio/architecture/README.md)
