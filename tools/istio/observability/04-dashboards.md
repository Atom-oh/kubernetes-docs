# 대시보드

Grafana와 Kiali를 통해 Istio 서비스 메시를 시각화하고 모니터링합니다.

## 목차

1. [대시보드 개요](#대시보드-개요)
2. [Kiali](#kiali)
3. [Grafana](#grafana)
4. [Prometheus](#prometheus)
5. [커스텀 대시보드](#커스텀-대시보드)

## 대시보드 개요

Istio는 Kiali, Grafana, Prometheus를 통해 종합적인 관찰성을 제공합니다.

## Kiali

### 설치

```bash
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.28/samples/addons/kiali.yaml
```

### 접속

```bash
istioctl dashboard kiali
```

### 주요 기능

- 서비스 토폴로지 시각화
- 트래픽 흐름 분석
- 구성 검증
- 분산 추적 통합

## Grafana

### 설치

```bash
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.28/samples/addons/grafana.yaml
```

### Istio 대시보드

- **Istio Mesh Dashboard**: 전체 메시 개요
- **Istio Service Dashboard**: 서비스별 메트릭
- **Istio Workload Dashboard**: 워크로드별 메트릭
- **Istio Performance Dashboard**: 성능 메트릭
- **Istio Control Plane Dashboard**: istiod 메트릭

## Prometheus

### 설치

```bash
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.28/samples/addons/prometheus.yaml
```

## 커스텀 대시보드

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "Custom Istio Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(istio_requests_total[5m])) by (destination_service)"
          }
        ]
      }
    ]
  }
}
```

## 참고 자료

- [Kiali](https://kiali.io/)
- [Istio Grafana](https://istio.io/latest/docs/ops/integrations/grafana/)
