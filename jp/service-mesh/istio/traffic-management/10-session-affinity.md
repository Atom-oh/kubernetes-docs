# Session Affinity

Session Affinity（または Sticky Session）は、同じユーザーからのリクエストを同じ Pod にルーティングする手法です。

## 目次

1. [Session Affinity の概要](#session-affinity-overview)
2. [Consistent Hash ベース](#consistent-hash-based)
3. [Cookie ベース](#cookie-based)
4. [Header ベース](#header-based)
5. [実践例](#practical-examples)

## Session Affinity の概要

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

## Consistent Hash ベース

### HTTP Header ベース

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

### Cookie ベース

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

### Source IP ベース

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

## 参考資料

- [Istio Session Affinity](https://istio.io/latest/docs/reference/config/networking/destination-rule/#LoadBalancerSettings-ConsistentHashLB)
