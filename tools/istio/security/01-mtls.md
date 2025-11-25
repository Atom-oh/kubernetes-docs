# mTLS

Mutual TLS (mTLS)는 Istio의 핵심 보안 기능으로, 서비스 간 통신을 자동으로 암호화하고 인증합니다.

## 목차

1. [mTLS 개요](#mtls-개요)
2. [mTLS 모드](#mtls-모드)
3. [PeerAuthentication 설정](#peerauthentication-설정)
4. [마이그레이션 전략](#마이그레이션-전략)
5. [문제 해결](#문제-해결)

## mTLS 개요

Istio는 서비스 간 통신에 자동으로 mTLS를 적용하여 Zero Trust 네트워크를 구현합니다.

```mermaid
flowchart LR
    subgraph Pod1["Pod A"]
        App1[애플리케이션]
        Envoy1[Envoy<br/>Proxy]
    end
    
    subgraph Pod2["Pod B"]
        Envoy2[Envoy<br/>Proxy]
        App2[애플리케이션]
    end
    
    Istiod[istiod<br/>인증서 발급]
    
    App1 -->|평문| Envoy1
    Envoy1 <-->|mTLS 암호화| Envoy2
    Envoy2 -->|평문| App2
    
    Istiod -.->|인증서| Envoy1
    Istiod -.->|인증서| Envoy2
    
    %% 스타일 정의
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef control fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class App1,App2 app;
    class Envoy1,Envoy2 proxy;
    class Istiod control;
```

## mTLS 모드

### STRICT 모드 (권장)

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # mTLS만 허용
```

### PERMISSIVE 모드 (마이그레이션용)

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: PERMISSIVE  # mTLS와 평문 모두 허용
```

### DISABLE 모드

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: disable-mtls
  namespace: default
spec:
  mtls:
    mode: DISABLE  # mTLS 비활성화
```

## PeerAuthentication 설정

### 전역 설정

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

### 네임스페이스별 설정

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: namespace-policy
  namespace: production
spec:
  mtls:
    mode: STRICT
```

### 워크로드별 설정

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: workload-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: reviews
      version: v1
  mtls:
    mode: STRICT
```

### 포트별 설정

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: port-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  mtls:
    mode: STRICT
  portLevelMtls:
    8080:
      mode: DISABLE  # 8080 포트는 mTLS 비활성화
```

## 마이그레이션 전략

### 1단계: 현재 상태 확인

```bash
# 현재 mTLS 설정 확인
kubectl get peerauthentication -A

# 서비스별 mTLS 상태 확인
istioctl authn tls-check <pod-name> -n <namespace>
```

### 2단계: PERMISSIVE 모드로 전환

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: PERMISSIVE  # mTLS와 평문 모두 허용
```

### 3단계: 모니터링

```bash
# mTLS 연결 확인
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep ssl

# 평문 연결 확인
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep plaintext
```

### 4단계: STRICT 모드로 전환

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # mTLS만 허용
```

## 문제 해결

### mTLS 연결 실패

```bash
# 1. PeerAuthentication 확인
kubectl get peerauthentication -A

# 2. 인증서 확인
istioctl proxy-config secret <pod-name> -n <namespace>

# 3. TLS 연결 확인
istioctl authn tls-check <source-pod> <dest-service> -n <namespace>

# 4. Envoy 로그 확인
kubectl logs <pod-name> -c istio-proxy -n <namespace> | grep TLS
```

### 인증서 만료

```bash
# 인증서 유효 기간 확인
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq '.dynamicActiveSecrets[0].secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -text -noout
```

## 참고 자료

- [Istio mTLS](https://istio.io/latest/docs/concepts/security/#mutual-tls-authentication)
- [PeerAuthentication Reference](https://istio.io/latest/docs/reference/config/security/peer_authentication/)
