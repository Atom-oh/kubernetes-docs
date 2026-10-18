# セッションアフィニティ

Session Affinity（Sticky Session とも呼ばれます）は、同じ hash key を持つ request 間に緩やかな親和性を与える手法です。Pod の割り当てが恒久的に固定されることを保証するものではありません。

## 目次

1. [セッションアフィニティの概要](#session-affinity-overview)
2. [Consistent Hash ベース](#consistent-hash-based)
3. [Cookie ベース](#cookie-based)
4. [HTTP Header ベース](#http-header-based)
5. [Source IP ベース](#source-ip-based)
6. [運用上の考慮事項](#operational-considerations)

## セッションアフィニティの概要 {#session-affinity-overview}

![user ID を含む client request が load balancer によって hash 化され、常に同じ Pod に routing される consistent-hash session affinity の図。他の Pod replica はその session では使われません。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-10-session-affinity-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-10-session-affinity-0.html)

## Consistent Hash ベース {#consistent-hash-based}

### HTTP Header ベース {#http-header-based}

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

### Cookie ベース {#cookie-based}

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

### Source IP ベース {#source-ip-based}

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

## 運用上の考慮事項 {#operational-considerations}

この図は、endpoint の集合が変わらず、各 proxy から見た endpoint も同じであることを前提とします。Pod の追加／削除や locality による endpoint の違いによって、request の割り当て先が変わることがあります。割り当て変更や Pod 障害が起きても安全なように、session state を保存してください。

同じ host に対して、これらの DestinationRule のいずれか 1 つを選択してください。HTTP header／cookie の hash には HTTP 処理が必要です。header がない場合、user を特定できません。`ttl: 0s` は cookie がないときに session cookie を作成しますが、browser がその cookie を返す必要があります。cookie の attribute と有効期間は、アプリケーションの要件に合わせてください。

Source-IP hashing は proxy から見える source address を使います。NAT や途中の load balancer によって複数 client が 1 つの address に集約されることがあります。これに依存する前に、信頼する proxy と client IP の取り扱いを確認してください。これらの DestinationRule の例は sidecar の動作を示しています。waypoint の feature support は別途確認してください。

## 参考資料

- [Istio Session Affinity](https://istio.io/latest/docs/reference/config/networking/destination-rule/#LoadBalancerSettings-ConsistentHashLB)
