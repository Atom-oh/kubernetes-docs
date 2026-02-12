# Traffic Mirroring

Traffic Mirroring (or Shadow Traffic) is a technique that replicates production traffic in real-time to test new versions.

## Table of Contents

1. [Traffic Mirroring Overview](#traffic-mirroring-overview)
2. [Basic Configuration](#basic-configuration)
3. [Partial Mirroring](#partial-mirroring)
4. [Practical Examples](#practical-examples)
5. [Best Practices](#best-practices)

## Traffic Mirroring Overview

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

## Basic Configuration

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

## Partial Mirroring

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

## References

- [Istio Traffic Mirroring](https://istio.io/latest/docs/tasks/traffic-management/mirroring/)
