# 로깅

Istio의 로깅 기능을 통해 서비스 메시의 모든 활동을 기록하고 분석할 수 있습니다.

## 목차

1. [로깅 개요](#로깅-개요)
2. [Access Log](#access-log)
3. [Envoy 로그](#envoy-로그)
4. [로그 레벨 조정](#로그-레벨-조정)
5. [로그 수집](#로그-수집)

## 로깅 개요

Istio는 Envoy를 통해 모든 요청에 대한 access log를 생성할 수 있습니다.

## Access Log

### 활성화

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    accessLogFile: /dev/stdout
    accessLogFormat: |
      [%START_TIME%] "%REQ(:METHOD)% %REQ(X-ENVOY-ORIGINAL-PATH?:PATH)% %PROTOCOL%"
      %RESPONSE_CODE% %RESPONSE_FLAGS% %BYTES_RECEIVED% %BYTES_SENT%
      %DURATION% "%REQ(X-FORWARDED-FOR)%" "%REQ(USER-AGENT)%"
```

### JSON 형식

```yaml
spec:
  meshConfig:
    accessLogFile: /dev/stdout
    accessLogEncoding: JSON
```

## Envoy 로그

### 로그 레벨 확인

```bash
istioctl proxy-config log <pod-name> -n <namespace>
```

### 로그 레벨 변경

```bash
# Debug 레벨로 변경
istioctl proxy-config log <pod-name> -n <namespace> --level debug

# 특정 컴포넌트만
istioctl proxy-config log <pod-name> -n <namespace> --level http:debug,router:info
```

## 로그 수집

### Fluentd 설정

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*istio-proxy*.log
      pos_file /var/log/istio-proxy.log.pos
      tag istio.*
      <parse>
        @type json
      </parse>
    </source>
```

## 참고 자료

- [Istio Logging](https://istio.io/latest/docs/tasks/observability/logs/)
