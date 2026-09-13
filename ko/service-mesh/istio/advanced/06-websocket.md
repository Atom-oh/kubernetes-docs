# WebSocket 지원

> **검증 기준**: Istio 1.31.0, Kubernetes 1.32–1.36
> **마지막 검토**: 2026년 9월 11일

Istio는 생성한 HTTP connection manager에서 WebSocket upgrade를 활성화합니다. 이 예제는 ingress gateway에서 TLS를 종료하는 HTTP/1.1 Upgrade 경로입니다. HTTP/2 Extended CONNECT와 HTTP/3는 전체 경로의 지원·설정을 별도로 확인해야 합니다.

## 기본 설정

전제조건은 표시한 라벨과443번 포트를 제공하는 기존 ingress Gateway Deployment/Service, `ws.example.com` DNS, Gateway workload namespace의 `ws-tls` 인증서/키 Secret,8080번의 `/ws`를 제공하는 기존 `app: websocket-service` Pod입니다. 예시 domain은 인증서가 포함하는 실제 이름으로 바꾸세요. 다음 리소스는 앱 배포·로드 밸런서·인증서를 생성하지 않습니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: websocket-service
  namespace: default
spec:
  selector:
    app: websocket-service
  ports:
  - name: http
    port: 8080
    targetPort: 8080
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: websocket-service
  namespace: default
spec:
  hosts: ["ws.example.com"]
  gateways: ["istio-system/websocket-gateway"]
  http:
  - match:
    - uri:
        exact: /ws
    - uri:
        prefix: /ws/
    route:
    - destination:
        host: websocket-service.default.svc.cluster.local
        port:
          number: 8080
    retries:
      attempts: 0
```

Route를 아래 Gateway에 명시적으로 연결했습니다. 경로 매칭으로 불필요하게 대소문자를 구분하는 `Upgrade` 헤더 조건을 피하며, 실제 handshake는 애플리케이션이 검증합니다. Mesh 재시도는 끕니다. VirtualService request timeout을 생략하여 Istio의 기본 비활성 route timeout을 사용하지만 전체 경로의 모든 connection/stream timeout을 끄는 것은 아닙니다.

## Gateway 설정

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: websocket-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: ws-tls
    hosts: ["ws.example.com"]
```

Client는 `wss://ws.example.com/ws`를 사용합니다. Gateway가 viewer TLS를 종료한 뒤 설정한 mesh/backend 전송 경로를 사용합니다. 애플리케이션 인증·Origin 확인·인가는 별도로 필요합니다. 앞선 proxy/load balancer에서 TLS를 종료한다면 해당 경로의 protocol·인증서·헤더 신뢰도 따로 검토하세요.

## 연결과 Timeout 관리

선택적인 DestinationRule은 기존 예시 수치를 **부하 시험용 입력값**으로 유지합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: websocket-service
  namespace: default
spec:
  host: websocket-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http1MaxPendingRequests: 1000
        idleTimeout: 3600s
```

`maxConnections`와 pending request 제한은 프록시별 목적지 pool 설정이며 클러스터 전체 WebSocket 수용량 보장이 아닙니다. `connectionPool.http.idleTimeout`은 활성 request/stream이 없는 HTTP 연결의 idle을 뜻하며 활성 WebSocket의1시간 수명이나 메시지 idle 제한이 아닙니다.

생성된 HCM/route의 stream idle 설정, 최대 stream/connection 시간, 앱 heartbeat/close 정책, 모든 중간 장비의 idle timeout을 확인하세요. Istio HCM 생성 및 설치된 ConnectionSettings가 Envoy 기본값을 바꿀 수 있습니다. Body buffering/filter는 upgrade와 호환되지 않을 수 있습니다. 복제본이 확장되어도 기존 WebSocket은 이동하지 않으므로 drain과 앱 수준 재연결을 계획하고 쓰기를 무조건 재생하지 않아야 합니다.

## 검증

```bash
# Inspect the selected gateway and backend configuration.
istioctl proxy-config routes <gateway-pod> -n istio-system
istioctl proxy-config clusters <gateway-pod> -n istio-system --fqdn websocket-service.default.svc.cluster.local

# Bounded HTTP/1.1 handshake check; certificate validation remains enabled.
curl --http1.1 --include --max-time 5 https://ws.example.com/ws -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=='
```

이 HTTP/1.1 검사에서는 정상 서버가 일반적으로101과 올바른 `Sec-WebSocket-Accept`를 반환합니다. curl은 handshake만 검사하며5초 제한에 도달하면 열린 연결을 exit 28로 끝낼 수 있습니다. 실제 WebSocket client로 frame·ping/pong·앱 인증·장시간 idle·close code·롤아웃/재연결을 시험하세요. 문서 감사에서는 배포나 live session 시험을 수행하지 않았습니다.

## 참고 자료

- [Envoy HTTP upgrades](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/upgrades)
- [Envoy timeout types](https://www.envoyproxy.io/docs/envoy/latest/faq/configuration/timeouts)
- [Istio secure ingress](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Istio 1.31 HCM generation](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/listener_builder.go)
