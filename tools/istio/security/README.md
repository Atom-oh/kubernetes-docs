# Security

Istio는 서비스 메시 내에서 강력한 보안 기능을 제공합니다.

## 목차

1. [mTLS](01-mtls.md)
2. [인증](02-authentication.md)
3. [권한 부여](03-authorization.md)
4. [Network Policy](04-network-policy.md)

## 개요

Istio 보안은 다음 세 가지 핵심 영역을 다룹니다:

### 1. 통신 보안 (mTLS)

모든 서비스 간 통신을 자동으로 암호화합니다.

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

### 2. 인증 (Authentication)

- **Peer Authentication**: 서비스 간 인증 (mTLS)
- **Request Authentication**: 최종 사용자 인증 (JWT)

### 3. 권한 부여 (Authorization)

세밀한 접근 제어 정책을 적용합니다.

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-read
spec:
  action: ALLOW
  rules:
  - to:
    - operation:
        methods: ["GET"]
```

## 다음 단계

1. **[mTLS](01-mtls.md)**: 서비스 간 암호화
2. **[인증](02-authentication.md)**: JWT 및 사용자 인증
3. **[권한 부여](03-authorization.md)**: 접근 제어 정책

## 참고 자료

- [Istio Security](https://istio.io/latest/docs/concepts/security/)
- [mTLS Documentation](https://istio.io/latest/docs/concepts/security/#mutual-tls-authentication)
