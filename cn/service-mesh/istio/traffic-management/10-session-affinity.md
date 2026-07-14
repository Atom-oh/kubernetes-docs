# 会话亲和性

会话亲和性（Session Affinity，也称为 Sticky Session）是一种将同一用户的请求路由到同一 Pod 的技术。

## 目录

1. [会话亲和性概述](#session-affinity-overview)
2. [基于一致性哈希](#consistent-hash-based)
3. [基于 Cookie](#cookie-based)
4. [基于 Header](#header-based)
5. [实践示例](#practical-examples)

## 会话亲和性概述

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

## 基于一致性哈希

### 基于 HTTP Header

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

### 基于 Cookie

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

### 基于源 IP

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

## 参考资料

- [Istio 会话亲和性](https://istio.io/latest/docs/reference/config/networking/destination-rule/#LoadBalancerSettings-ConsistentHashLB)
