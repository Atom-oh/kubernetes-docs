# Session Affinity

Session Affinity(또는 Sticky Session)는 같은 해시 키의 요청에 대해 느슨한 친화성을 제공하는 기법이며 영구적인 파드 고정을 보장하지 않습니다.

## 목차

1. [Session Affinity 개요](#session-affinity-개요)
2. [Consistent Hash 기반](#consistent-hash-기반)
3. [Cookie 기반](#cookie-기반)
4. [HTTP Header 기반](#http-header-기반)
5. [Source IP 기반](#source-ip-기반)
6. [운영 고려사항](#운영-고려사항)

## Session Affinity 개요

![사용자 A의 요청(user_id=123)이 Load Balancer의 Consistent Hash를 거쳐 항상 동일한 파드 1로 라우팅되고, 같은 파드 풀의 파드 2와 파드 3는 이 사용자의 요청을 받지 않는 Session Affinity 동작을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-10-session-affinity-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-10-session-affinity-0.html)

## Consistent Hash 기반

### HTTP Header 기반

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

### Cookie 기반

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
          ttl: 0s  # 쿠키 만료 시간 (0s = 세션 쿠키)
```

### Source IP 기반

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

## 운영 고려사항

그림은 엔드포인트 집합과 각 프록시의 엔드포인트 정보가 같고 변하지 않는 상황을 가정합니다. 파드 추가·삭제나 locality별 엔드포인트 차이로 요청 대상이 바뀔 수 있으므로 재매핑과 파드 장애에 견디도록 세션 상태를 저장하세요.

동일한 호스트에는 위 DestinationRule 중 하나를 선택합니다. HTTP 헤더/쿠키 해시는 HTTP 처리가 필요하며 헤더가 없으면 사용자를 식별할 수 없습니다. `ttl: 0s`는 쿠키가 없을 때 세션 쿠키를 만들지만 브라우저가 후속 요청에 다시 보내야 합니다. 쿠키 속성과 수명은 앱 요구에 맞게 정하세요.

Source IP 해시는 프록시에 보이는 출발 주소를 사용합니다. NAT와 중간 로드 밸런서로 여러 클라이언트가 같은 주소로 보일 수 있으므로 신뢰 프록시와 클라이언트 IP 처리를 확인하세요. 위는 Sidecar DestinationRule 예제이며 waypoint의 기능 지원은 별도 확인해야 합니다.

## 참고 자료

- [Istio Session Affinity](https://istio.io/latest/docs/reference/config/networking/destination-rule/#LoadBalancerSettings-ConsistentHashLB)
