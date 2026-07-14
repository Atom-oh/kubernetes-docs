# Afinidad de sesión

La afinidad de sesión (o Sticky Session) es una técnica que enruta las solicitudes del mismo usuario al mismo Pod.

## Tabla de contenidos

1. [Descripción general de la afinidad de sesión](#session-affinity-overview)
2. [Basado en hash consistente](#consistent-hash-based)
3. [Basado en cookies](#cookie-based)
4. [Basado en encabezados](#header-based)
5. [Ejemplos prácticos](#practical-examples)

## Descripción general de la afinidad de sesión

```mermaid
flowchart TB
    User[User A]

    subgraph LB["Load Balancer"]
        Hash[Consistent Hash<br/>Based on User ID]
    end

    subgraph Pods["Pods"]
        Pod1[Pod 1<br/>Session A]
        Pod2[Pod 2]
        Pod3[Pod 3]
    end

    User -->|user_id=123| Hash
    Hash -->|Always Same| Pod1

    %% Style definitions
    classDef user fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef lb fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class User user;
    class Hash lb;
    class Pod1,Pod2,Pod3 pod;
```

## Basado en hash consistente

### Basado en encabezado HTTP

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-session-affinity
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-user-id"
```

### Basado en cookies

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-cookie-affinity
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpCookie:
          name: "session-id"
          ttl: 0s  # Cookie expiration time (0s = session cookie)
```

### Basado en IP de origen

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-ip-affinity
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      consistentHash:
        useSourceIp: true
```

## Referencias

- [Afinidad de sesión de Istio](https://istio.io/latest/docs/reference/config/networking/destination-rule/#LoadBalancerSettings-ConsistentHashLB)
