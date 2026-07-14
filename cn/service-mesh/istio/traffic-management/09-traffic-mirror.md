# 流量镜像

流量镜像（Traffic Mirroring，也称为 Shadow Traffic）是一种将生产流量实时复制以测试新版本的技术。

## 目录

1. [流量镜像概览](#traffic-mirroring-overview)
2. [基本配置](#basic-configuration)
3. [部分镜像](#partial-mirroring)
4. [实践示例](#practical-examples)
5. [最佳实践](#best-practices)

## 流量镜像概览

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

## 基本配置

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

## 部分镜像

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
    mirror:
      host: reviews
      subset: v2
    mirrorPercentage:
      value: 10  # Mirror only 10%
```

## 参考资料

- [Istio 流量镜像](https://istio.io/latest/docs/tasks/traffic-management/mirroring/)
