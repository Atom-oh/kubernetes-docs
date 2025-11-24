# 분산 추적

분산 추적은 마이크로서비스 간 요청 흐름을 추적하고 시각화합니다.

## 목차

1. [분산 추적 개요](#분산-추적-개요)
2. [Jaeger 통합](#jaeger-통합)
3. [Zipkin 통합](#zipkin-통합)
4. [샘플링 설정](#샘플링-설정)
5. [Trace 분석](#trace-분석)

## 분산 추적 개요

Istio는 Envoy를 통해 자동으로 trace context를 전파합니다.

## Jaeger 통합

### Jaeger 설치

```bash
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.28/samples/addons/jaeger.yaml
```

### Trace 구성

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    defaultConfig:
      tracing:
        sampling: 100.0
        zipkin:
          address: jaeger-collector.istio-system:9411
```

## 샘플링 설정

```yaml
# 10% 샘플링
spec:
  meshConfig:
    defaultConfig:
      tracing:
        sampling: 10.0
```

## 참고 자료

- [Istio Distributed Tracing](https://istio.io/latest/docs/tasks/observability/distributed-tracing/)
