# Duplicación de tráfico

Traffic Mirroring (o Shadow Traffic) es una técnica que replica el tráfico de producción en tiempo real para probar nuevas versiones.

## Tabla de contenido

1. [Descripción general de Traffic Mirroring](#traffic-mirroring-overview)
2. [Configuración básica](#basic-configuration)
3. [Duplicación parcial](#partial-mirroring)
4. [Ejemplos prácticos](#practical-examples)
5. [Mejores prácticas](#best-practices)

## Descripción general de Traffic Mirroring

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

## Configuración básica

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

## Duplicación parcial

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

## Referencias

- [Traffic Mirroring de Istio](https://istio.io/latest/docs/tasks/traffic-management/mirroring/)
