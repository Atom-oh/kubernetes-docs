# トラフィックミラーリング

Traffic Mirroring（またはShadow Traffic）は、本番トラフィックをリアルタイムで複製して、新しいバージョンをテストする手法です。

## 目次

1. [トラフィックミラーリングの概要](#traffic-mirroring-overview)
2. [基本設定](#basic-configuration)
3. [部分ミラーリング](#partial-mirroring)
4. [実践例](#practical-examples)
5. [ベストプラクティス](#best-practices)

## トラフィックミラーリングの概要

```mermaid
flowchart LR
    Client[Client]

    subgraph Production["Production"]
        V1[Version 1<br/>Actual Response]
    end

    subgraph Shadow["Shadow (Mirror)"]
        V2[Version 2<br/>Response Ignored]
    end

    Client -->|Request| V1
    V1 -->|Response| Client
    Client -.->|Replicate| V2
    V2 -.->|Ignored| Client

    %% Style definitions
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef production fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef shadow fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Client client;
    class V1 production;
    class V2 shadow;
```

## 基本設定

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-mirror
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 100
    mirror:
      host: reviews
      subset: v2
    mirrorPercentage:
      value: 100  # 100% mirroring
```

## 部分ミラーリング

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-partial-mirror
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 100
    mirror:
      host: reviews
      subset: v2
    mirrorPercentage:
      value: 10  # Mirror only 10%
```

## 参考資料

- [Istio Traffic Mirroring](https://istio.io/latest/docs/tasks/traffic-management/mirroring/)
