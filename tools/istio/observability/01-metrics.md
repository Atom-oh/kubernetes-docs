# 메트릭

Istio는 서비스 메시의 모든 트래픽에 대한 메트릭을 자동으로 생성합니다.

## 목차

1. [메트릭 개요](#메트릭-개요)
2. [Istio 표준 메트릭](#istio-표준-메트릭)
3. [Prometheus 통합](#prometheus-통합)
4. [커스텀 메트릭](#커스텀-메트릭)
5. [메트릭 쿼리](#메트릭-쿼리)

## 메트릭 개요

Istio는 Golden Signals (Latency, Traffic, Errors, Saturation)를 자동으로 수집합니다.

## Istio 표준 메트릭

### Request 메트릭

```promql
# 총 요청 수
istio_requests_total

# 요청 지연시간
istio_request_duration_milliseconds

# 요청 크기
istio_request_bytes

# 응답 크기
istio_response_bytes
```

### TCP 메트릭

```promql
# TCP 연결 수
istio_tcp_connections_opened_total
istio_tcp_connections_closed_total

# TCP 전송 바이트
istio_tcp_sent_bytes_total
istio_tcp_received_bytes_total
```

## Prometheus 통합

### ServiceMonitor 설정

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: istio-component-monitor
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: pilot
  endpoints:
  - port: http-monitoring
    interval: 15s
```

## 메트릭 쿼리

### 에러율

```promql
sum(rate(istio_requests_total{response_code=~"5.*"}[5m])) 
/ 
sum(rate(istio_requests_total[5m]))
```

### P95 지연시간

```promql
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)
```

## 참고 자료

- [Istio Metrics](https://istio.io/latest/docs/reference/config/metrics/)
