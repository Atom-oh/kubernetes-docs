# Session Affinity

Session Affinity (or Sticky Session) is a technique that routes requests from the same user to the same pod.

## Table of Contents

1. [Session Affinity Overview](#session-affinity-overview)
2. [Consistent Hash Based](#consistent-hash-based)
3. [Cookie Based](#cookie-based)
4. [Header Based](#header-based)
5. [Practical Examples](#practical-examples)

## Session Affinity Overview

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

## Consistent Hash Based

### HTTP Header Based

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

### Cookie Based

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

### Source IP Based

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

## References

- [Istio Session Affinity](https://istio.io/latest/docs/reference/config/networking/destination-rule/#LoadBalancerSettings-ConsistentHashLB)
