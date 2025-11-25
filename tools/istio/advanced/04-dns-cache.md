# DNS Caching

DNS Caching을 통해 외부 서비스 호출 시 DNS 조회 성능을 최적화합니다.

## 개요

DNS Caching의 이점:
- DNS 조회 지연시간 감소
- 외부 DNS 서버 부하 감소
- 일관된 DNS 응답

## 설정

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-dns-cache
spec:
  host: api.external.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 100
```

## Envoy DNS Cache 활성화

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: dns-cache
spec:
  configPatches:
  - applyTo: CLUSTER
    match:
      cluster:
        service: api.external.com
    patch:
      operation: MERGE
      value:
        dns_refresh_rate: 30s
        dns_lookup_family: V4_ONLY
```

## 모범 사례

1. **TTL 설정**: 적절한 TTL 값 설정
2. **외부 서비스만**: 외부 호출에만 적용
3. **모니터링**: DNS 캐시 히트율 확인

## 참고 자료

- [Envoy DNS Cache](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery#dns-cache)
