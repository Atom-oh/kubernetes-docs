# mTLS

Mutual TLS (mTLS)는 Istio의 핵심 보안 기능으로, 서비스 간 통신을 자동으로 암호화하고 인증합니다.

> 📎 TLS 핸드셰이크와 인증서 검증이 생소하다면 [네트워크 기초 Part 2](../../../basics/06-network-fundamentals-part2.md)의 TLS 절을 먼저 읽어보세요.

## 목차

1. [mTLS 개요](#mtls-개요)
2. [mTLS 모드](#mtls-모드)
3. [인증서 관리](#인증서-관리)
4. [PeerAuthentication 설정](#peerauthentication-설정)
5. [AWS 서비스와 mTLS 통합](#aws-서비스와-mtls-통합)
6. [외부 서비스와 mTLS](#외부-서비스와-mtls)
7. [마이그레이션 전략](#마이그레이션-전략)
8. [일반적인 문제와 해결](#일반적인-문제와-해결)
9. [성능 및 모니터링](#성능-및-모니터링)

## mTLS 개요

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/id-prov.svg" alt="Istio Identity Provisioning" width="700">
</p>

Auto mTLS는 메시 피어에 적합한 TLS를 선택합니다. 사이드카 모드에서는 수신 프록시의 `STRICT`로 평문을 거부하고 AuthorizationPolicy로 신원을 제한합니다. Auto mTLS만으로 완전한 제로 트러스트 정책이 되지는 않습니다. 아래 신원 발급 과정은 사이드카 기준이며 ambient는 ztunnel과 선택적 waypoint를 사용합니다.

### Identity 기반 보안

Istio는 **SPIFFE (Secure Production Identity Framework for Everyone)** 표준을 사용하여 각 워크로드에 강력한 신원을 부여합니다:

```
spiffe://cluster.local/ns/default/sa/productpage
  │         │           │     │      │    │
  │         │           │     │      │    └─ ServiceAccount 이름
  │         │           │     │      └────── "sa" (ServiceAccount)
  │         │           │     └───────────── Namespace 이름
  │         │           └─────────────────── "ns" (Namespace)
  │         └─────────────────────────────── Trust Domain
  └───────────────────────────────────────── 프로토콜
```

**Identity 프로비저닝 과정**:
1. Kubernetes가 파드를 생성하고 ServiceAccount를 할당
2. Istio Agent가 파드 내에서 시작
3. Agent가 Istiod에 CSR (Certificate Signing Request) 전송
4. Istiod가 SPIFFE ID 기반 X.509 인증서 발급
5. Agent가 Envoy에 인증서 전달 (SDS 프로토콜)
6. 인증서 자동 갱신 (기본 TTL: 24시간)

![istiod가 각 파드의 Envoy 사이드카에 X.509 인증서를 발급하고, 파드 내부 애플리케이션과 사이드카 사이는 평문으로, 파드 간 Envoy 사이드카 사이는 mTLS로 암호화해 통신하는 구조를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-security-01-mtls-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-security-01-mtls-0.html)

## mTLS 모드

아래 예제는 대안 관계입니다. 메시 루트 네임스페이스(기본 `istio-system`)의 selector 없는 정책은 메시 전체에 적용됩니다. Ambient는 캡처된 메시 트래픽을 HBONE으로 암호화하며 `DISABLE`은 지원하지 않습니다. `STRICT`는 우회 평문 트래픽을 거부합니다.

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

## 인증서 관리

### Istio 기본 CA 인증서

istiod는 기본적으로 자체 서명 루트 CA를 생성하고 이를 직접 사용하여 워크로드 인증서에 서명합니다. 오프라인 루트 CA와 별도 중간 서명 CA는 운영 환경에서 선택하는 구성으로, 기본 설치 시 자동 생성되는 계층이 아닙니다.

Agent는 기본적으로 **24시간** 유효한 워크로드 인증서를 요청하고 수명의 절반 부근에 jitter를 더해 갱신을 예약합니다. CA는 요청 수명을 제한할 수 있습니다. 루트·중간 CA의 수명은 별도로 관리하며 실제 알고리즘과 유효 기간은 발급된 인증서에서 확인합니다.

### 인증서 확인

```bash
# 1. CA 인증서 확인
kubectl get secret istio-ca-secret -n istio-system -o jsonpath='{.data.ca-cert\.pem}' | \
  base64 -d | openssl x509 -noout -issuer -subject -dates

# 2. 워크로드 인증서 확인
istioctl proxy-config secret <pod-name> -n <namespace>

# 3. 인증서 상세 정보
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -text -noout

# 4. 인증서 만료 날짜 확인
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -noout -dates
```

### 사용자 정의 CA 인증서 사용

SPIFFE URI SAN을 발급할 수 있는 사설 PKI를 사용합니다. 공인 ACME 인증서는 워크로드 신원에 적합하지 않습니다. 아래 OpenSSL 예제는 새 테스트 메시의 초기 구성용입니다. istiod 설치 전에 `istio-system`과 `cacerts`를 생성하고 운영 루트 키는 오프라인에서 보호합니다.

#### 1단계: CA 인증서 및 키 생성

```bash
# 1. Root CA 생성
umask 077
openssl genrsa -out root-key.pem 4096

openssl req -new -x509 -days 3650 -key root-key.pem \
  -out root-cert.pem -addext "basicConstraints=critical,CA:TRUE" \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=MyOrg/OU=IT/CN=Root CA"

# 2. Intermediate CA 생성
openssl genrsa -out ca-key.pem 4096

openssl req -new -key ca-key.pem -out ca-cert.csr \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=MyOrg/OU=IT/CN=Intermediate CA"

# 3. Intermediate CA를 Root CA로 서명
cat > ca-extensions.txt <<EOF
basicConstraints=critical,CA:TRUE,pathlen:0
keyUsage=critical,keyCertSign,cRLSign
EOF

openssl x509 -req -days 1825 -in ca-cert.csr \
  -CA root-cert.pem -CAkey root-key.pem -CAcreateserial \
  -out ca-cert.pem -extfile ca-extensions.txt

# 4. Certificate Chain 생성
cat ca-cert.pem root-cert.pem > cert-chain.pem
```

#### 2단계: Kubernetes Secret 생성

```bash
kubectl create secret generic cacerts -n istio-system \
  --from-file=ca-cert.pem=ca-cert.pem \
  --from-file=ca-key.pem=ca-key.pem \
  --from-file=root-cert.pem=root-cert.pem \
  --from-file=cert-chain.pem=cert-chain.pem
```

#### 3단계: 새 메시 설치

`cacerts` 생성 후 [설치 가이드](../01-installation.md)에 따라 호환되는 Istio 버전을 고정해 설치합니다. 실행 중인 메시의 루트 인증서를 이 초기 설치 절차로 교체하지 않습니다.

#### 4단계: 검증

```bash
# CA 인증서가 올바르게 로드되었는지 확인
kubectl logs -l app=istiod -n istio-system | grep "Use plugged-in cert"

# 워크로드 인증서가 새 CA로 발급되었는지 확인
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -noout -issuer
```

### AWS Private CA 통합

워크로드 서명에는 **cert-manager → AWS Private CA issuer → istio-csr** 구성을 사용합니다. Istio가 없는 새 클러스터, 활성 Private CA, 해당 CA로 제한한 issuer ServiceAccount IAM 권한(`DescribeCertificateAuthority`, `GetCertificate`, `IssueCertificate`)을 준비합니다. EKS Pod Identity 또는 IRSA를 사용하고 CA가 SPIFFE SAN과 요청 유효 기간을 허용하는지 확인합니다.

Kubernetes와 호환되는 cert-manager(1.21은 Kubernetes 1.33–1.36 지원), AWS Private CA issuer 순으로 설치합니다. 아래 ARN은 선택한 CA로 교체합니다. 일반 YAML에서는 셸 변수가 확장되지 않습니다.

```yaml
apiVersion: awspca.cert-manager.io/v1beta1
kind: AWSPCAClusterIssuer
metadata:
  name: istio-ca
spec:
  arn: arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/REPLACE_WITH_CA_ID
  region: us-west-2
```

검증된 공개 루트 번들(`ca.pem`)로 `cert-manager` 네임스페이스에 `istio-root-ca` Secret을 생성하고 다음 Helm 값으로 istio-csr을 구성합니다:

```yaml
# istio-csr Helm values fragment
app:
  certmanager:
    issuer:
      group: awspca.cert-manager.io
      kind: AWSPCAClusterIssuer
      name: istio-ca
  tls:
    rootCAFile: /var/run/secrets/istio-csr/ca.pem
volumeMounts:
- name: root-ca
  mountPath: /var/run/secrets/istio-csr
  readOnly: true
volumes:
- name: root-ca
  secret:
    secretName: istio-root-ca
```

완전한 차트·Istio 설치 매니페스트는 [현재 istio-csr 설치 가이드](https://cert-manager.io/docs/usage/istio-csr/installation/)에서 호환성을 확인합니다. Istio 매니페스트는 istiod CA를 끄고(`ENABLE_CA_SERVER=false`), CA 주소를 `cert-manager-istio-csr.cert-manager.svc:443`으로 지정하며 발급된 istiod 서버 인증서와 고정 루트를 마운트합니다. 이 입력에는 `istioctl install -f`를 사용합니다. Ambient는 istio-csr에 신뢰할 ztunnel ServiceAccount도 설정해야 합니다. 기존 Istio 설치 후 istio-csr을 추가하는 방식은 해당 가이드에서 지원하지 않습니다.

cert-manager `Certificate`는 일반적으로 `tls.crt`, `tls.key`, 선택적 `ca.crt`를 생성합니다. Secret 이름을 `cacerts`로 지정해도 Istio가 요구하는 `ca-cert.pem`, `ca-key.pem`, `root-cert.pem`, `cert-chain.pem`이 되지 않습니다. istio-csr 경로는 이 Secret 형식 불일치를 피합니다.

### 인증서 갱신 정책

사이드카 agent가 요청 수명과 갱신 시점을 제어합니다. 다음은 `istioctl` 입력이며 설치 워크플로로 적용합니다. 부트스트랩 설정 변경 시 대상 프록시를 순차적으로 교체합니다:

```yaml
# Input to istioctl install -f; not kubectl apply
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        SECRET_TTL: "24h"
        SECRET_GRACE_PERIOD_RATIO: "0.5"
```

`SECRET_TTL` 기본값은 24h, `SECRET_GRACE_PERIOD_RATIO`는 0.5이며 갱신에는 jitter도 적용됩니다. 이는 agent 설정이며 기존 예제의 `CITADEL_CERT_TTL`/`CITADEL_GRACE_PERIOD`가 아닙니다. 실제 발급자는 인증서 수명을 더 짧게 제한할 수 있습니다.

### 인증서 순환 (Rotation)

Leaf 갱신, 동일 루트 아래 중간 CA 갱신, 루트 교체는 서로 다른 작업입니다. 루트를 교체할 때는 다음 순서가 필요합니다:

1. **기존·신규 루트를 모두 포함한 번들**을 모든 대상 워크로드·게이트웨이·클러스터에 배포하고 실제 신뢰 상태를 확인합니다.
2. 두 루트를 신뢰하는 동안 새 서명자로 전환하고 새 leaf를 발급합니다.
3. SDS 상태, 인증서 체인, 클러스터 간 통신, 남아 있는 이전 leaf를 확인합니다. 연결이 끊긴 워크로드와 장시간 연결도 고려합니다.
4. 마이그레이션과 롤백 기간이 끝난 뒤에만 이전 루트를 제거합니다.

선택한 CA 제공자의 지원되는 순환 절차를 따릅니다. `cacerts`를 한 번에 덮어쓰고 재시작한다고 무중단이 보장되지 않으며 갱신을 강제하려고 모든 네임스페이스를 재시작하지 않습니다.

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

## AWS 서비스와 mTLS 통합

### AWS Application Load Balancer (ALB)와 mTLS

ALB는 클라이언트 인증서 기반 mTLS를 지원합니다.

![클라이언트 인증서 기반 mTLS를 ALB가 검증하고 종료한 뒤, ALB에서 Istio Gateway까지는 TLS로, Gateway에서 백엔드 서비스까지는 Envoy mTLS로 다시 암호화되는 구간별 보안 체인을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-security-01-mtls-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-security-01-mtls-2.html)

#### ALB 리스너와 게이트웨이 설정

클라이언트 CA 번들로 ALB trust store를 생성하고 아래 이름에 반영합니다. AWS Load Balancer Controller가 이 Ingress와 리스너 설정을 관리합니다. `istio: ingressgateway` 레이블의 게이트웨이 배포, `gateway-cert` TLS Secret, `istio-system/public-gateway`에 연결하여 `api.example.com`을 애플리케이션으로 라우팅하는 VirtualService가 먼저 필요합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-gateway
  namespace: istio-system
spec:
  type: ClusterIP
  selector:
    istio: ingressgateway
  ports:
  - name: https
    port: 443
    targetPort: 8443
  - name: status-port
    port: 15021
    targetPort: 15021
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: istio-edge
  namespace: istio-system
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:123456789012:certificate/REPLACE_WITH_CERT_ID
    alb.ingress.kubernetes.io/mutual-authentication: '[{"port":443,"mode":"verify","trustStore":"istio-client-trust-store","ignoreClientCertificateExpiry":false}]'
    alb.ingress.kubernetes.io/backend-protocol: HTTPS
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTP
    alb.ingress.kubernetes.io/healthcheck-port: '15021'
    alb.ingress.kubernetes.io/healthcheck-path: /healthz/ready
spec:
  ingressClassName: alb
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: istio-gateway
            port:
              number: 443
---
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: public-gateway
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
      credentialName: gateway-cert
    hosts:
    - api.example.com
```

ALB `verify` 모드는 핸드셰이크에서 클라이언트 인증서를 검증합니다. `passthrough` 모드는 애플리케이션 검증용 인증서 체인을 전달하지만 여전히 TLS를 종료합니다. HTTPS target group은 ALB–게이트웨이 구간을 암호화하지만 **ALB는 대상 인증서를 검증하지 않습니다**. 대상 트래픽을 ALB 보안 그룹과 필요한 상태 확인 포트로 제한합니다. ClusterIP Service만으로 다른 클러스터 파드의 접근이 차단되지는 않습니다.

ALB는 `X-Amzn-Mtls-Clientcert-Serial-Number`, `-Subject`, `-Issuer`, `-Validity`, `-Leaf` 헤더를 제공합니다. 이는 신뢰하는 엣지가 전달하는 HTTP 신원 정보이며 Envoy에서의 클라이언트 TLS 세션이 아닙니다. 원본 직접 접근을 차단하고 클라이언트가 넣은 경쟁 신원 헤더를 정리해야 합니다. 백엔드에서는 인증된 게이트웨이 메시 principal을 요구한 뒤 검증된 정보에 애플리케이션 인가를 적용합니다. 헤더 존재 여부나 Subject 문자열만으로는 충분하지 않습니다. 임의의 Envoy bootstrap YAML ConfigMap을 생성해도 게이트웨이에 적용되지 않습니다.

### Amazon CloudFront와 mTLS

CloudFront는 네이티브 viewer mTLS를 지원합니다. 허용된 클라이언트 CA 번들을 담은 CloudFront trust store와 `ViewerMtlsConfig.Mode=required`로 유효한 인증서를 요구합니다. Trust store는 생성·업데이트 때 S3 번들을 읽으므로 S3 객체만 바꿔서는 반영되지 않습니다. 현재 viewer mTLS는 HTTP/3 대신 HTTP/2가 필요하며 모든 캐시 동작에서 HTTP를 거부하거나 리디렉션해야 합니다.

#### 선택한 배포 업데이트

다음 예제는 기존 설정 전체를 유지하고 ETag를 사용합니다. 적용 전에 대상 배포, 원본 HTTPS 설정, 모든 캐시 동작, trust store를 검토합니다. Viewer mTLS API를 지원하는 현재 AWS CLI가 필요합니다.

```bash
# Existing distribution and trust store selected explicitly by the operator.
DIST_ID=REPLACE_WITH_DISTRIBUTION_ID
TRUST_STORE_ID=REPLACE_WITH_TRUST_STORE_ID
aws cloudfront get-distribution-config --id "$DIST_ID" --output json > dist-before.json
ETAG=$(jq -r '.ETag' dist-before.json)
jq --arg trust "$TRUST_STORE_ID" '
  .DistributionConfig
  | .HttpVersion = "http2"
  | .DefaultCacheBehavior.ViewerProtocolPolicy = "https-only"
  | (if .CacheBehaviors.Quantity > 0 then
       .CacheBehaviors.Items |= map(.ViewerProtocolPolicy = "https-only")
     else . end)
  | .ViewerMtlsConfig = {
      Mode: "required",
      TrustStoreConfig: {
        TrustStoreId: $trust,
        AdvertiseTrustStoreCaNames: true,
        IgnoreCertificateExpiry: false
      }
    }
' dist-before.json > dist-mtls.json
# Review the complete diff before applying to the selected distribution.
diff -u <(jq '.DistributionConfig' dist-before.json) dist-mtls.json || true
aws cloudfront update-distribution --id "$DIST_ID" --if-match "$ETAG" \
  --distribution-config file://dist-mtls.json
```

#### 인증서 신원 전달과 인가

Origin request policy로 필요한 `CloudFront-Viewer-Cert-*` 헤더만 전달합니다: `Present`, `Sha256`, `Serial-Number`, `Issuer`, `Subject`, 선택적 `Validity`/`Pem`. PEM 헤더는 원본에만 제공되며 엣지 함수에서는 사용할 수 없습니다. 사용자별 응답은 캐시를 끄거나 신원을 고려한 캐시 키를 사용합니다. Origin request policy는 캐시 키를 바꾸지 않습니다.

선택적으로 viewer-request CloudFront Function에서 **네이티브 mTLS 검증 후** 허용 목록을 적용할 수 있습니다. 지문은 인증서를 식별하지만 일련번호만으로는 발급자 범위 안에서만 고유합니다. 클라이언트 인증서 교체 시 허용 목록도 갱신합니다:

```javascript
// Additional authorization after native CloudFront viewer mTLS verification.
function handler(event) {
    var fingerprint = event.request.headers['cloudfront-viewer-cert-sha256'];
    var allowed = ['REPLACE_WITH_VERIFIED_CERT_SHA256'];
    if (!fingerprint || allowed.indexOf(fingerprint.value) === -1) {
        return {statusCode: 403, statusDescription: 'Forbidden'};
    }
    return event.request;
}
```

지원되는 원본 접근 제어·네트워크 설계와 원본 인증으로 지정한 배포에서 온 요청만 수락해야 합니다. 백엔드는 임의 호출자의 동일 헤더를 신뢰하면 안 됩니다. Viewer 인증서 검증은 CloudFront에서 끝나며 원본 HTTPS는 별도 TLS 세션입니다. [CloudFront mTLS 설정](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/enable-mtls-distributions.html)과 [인증서 헤더](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewer-mtls-headers.html)를 참고하세요.

### 여러 TLS 구간의 보안

아래 그림은 구간별로 별도 TLS 세션을 사용합니다. 기존 End-to-End mTLS 제목은 클라이언트 인증서가 메시 워크로드 신원이라는 뜻이 아닙니다. CloudFront와 ALB 뒤의 신원 헤더는 신뢰하는 프록시가 전달한 정보이며 원래 mTLS 세션이 아닙니다.

![클라이언트의 인증서를 CloudFront가 mTLS로 검증한 뒤 ALB와 Istio Gateway까지는 TLS 위에 인증서 정보 헤더로 전달하고, 메시 내부에서는 Envoy가 서비스 A·B·C 사이를 자동 mTLS로 다시 보호하는 6개 구간의 전체 경로를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-security-01-mtls-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-security-01-mtls-4.html)

**구간별 보안**:
1. **클라이언트 → CloudFront**: mTLS (클라이언트 인증서 검증)
2. **CloudFront → ALB**: TLS + 인증서 정보 헤더
3. **ALB → Istio Gateway**: TLS + 인증서 정보 헤더
4. **Istio Mesh 내부**: 자동 mTLS (Envoy-to-Envoy)

## 외부 서비스와 mTLS

### Legacy 시스템 통합

일반 HTTPS를 지원하는 레거시 서버에는 사이드카가 TLS를 시작할 수 있습니다. 애플리케이션은 `http://legacy.external.com:80`으로 요청하고 프록시는 443에 연결합니다. 애플리케이션이 이미 HTTPS를 사용한다면 암호화된 흐름을 유지하고 이 규칙으로 TLS를 중복 적용하지 않습니다. 사설 서버 CA에는 명시적인 신뢰 번들이 필요합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-system
  namespace: default
spec:
  hosts: [legacy.external.com]
  location: MESH_EXTERNAL
  resolution: DNS
  ports:
  - number: 80
    targetPort: 443
    name: http
    protocol: HTTP
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: legacy-system
  namespace: default
spec:
  host: legacy.external.com
  trafficPolicy:
    tls:
      mode: SIMPLE
      sni: legacy.external.com
      subjectAltNames: [legacy.external.com]
```

### 외부 API mTLS 클라이언트 인증

HTTP→mTLS origination에는 **클라이언트 프록시 네임스페이스**에 클라이언트 인증서 체인·키와 서버 신뢰 번들을 배치합니다. 사이드카의 `credentialName` 사용에는 아래 DestinationRule workload selector가 필요합니다. 서버 SAN은 `api.external.com`과 일치해야 합니다.

```bash
kubectl create secret generic client-mtls-credential -n default \
  --from-file=tls.crt=client-chain.pem \
  --from-file=tls.key=client-key.pem \
  --from-file=ca.crt=server-ca.pem
```

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts: [api.external.com]
  location: MESH_EXTERNAL
  resolution: DNS
  ports:
  - number: 80
    targetPort: 443
    name: http
    protocol: HTTP
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-mtls
  namespace: default
spec:
  host: api.external.com
  workloadSelector:
    matchLabels:
      app: external-api-client
  trafficPolicy:
    tls:
      mode: MUTUAL
      credentialName: client-mtls-credential
      sni: api.external.com
      subjectAltNames: [api.external.com]
```

대상 워크로드는 `http://api.external.com:80`을 호출하고 해당 프록시만 mTLS를 시작합니다. 이 방식과 아래 egress gateway 방식은 대안 관계입니다.

### Egress Gateway를 통한 외부 mTLS

[Egress 가이드](../traffic-management/11-egress-control.md)에 따라 게이트웨이를 설치합니다. 아래 예제는 `istio-egressgateway.istio-system.svc.cluster.local` Service의 443 포트와 `istio: egressgateway` 파드 레이블을 가정합니다. 앞의 ServiceEntry를 양쪽 네임스페이스에 공개하고 직접 호출용 DestinationRule은 적용하지 않습니다. 게이트웨이용 클라이언트 자격 증명 Secret은 `istio-system`에 생성합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: egress-gateway
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts: [api.external.com]
    tls:
      mode: ISTIO_MUTUAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: to-egress-gateway
  namespace: default
spec:
  host: istio-egressgateway.istio-system.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
      sni: api.external.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-through-egress
  namespace: default
spec:
  hosts: [api.external.com]
  gateways: [mesh, istio-system/egress-gateway]
  http:
  - match:
    - gateways: [mesh]
      port: 80
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways: [istio-system/egress-gateway]
      port: 443
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-from-egress
  namespace: istio-system
spec:
  host: api.external.com
  workloadSelector:
    matchLabels:
      istio: egressgateway
  trafficPolicy:
    tls:
      mode: MUTUAL
      credentialName: client-mtls-credential
      sni: api.external.com
      subjectAltNames: [api.external.com]
```

흐름은 애플리케이션 HTTP:80 → 게이트웨이 ISTIO_MUTUAL:443 → 외부 MUTUAL:443입니다(ServiceEntry의 80은 targetPort 443으로 연결). 게이트웨이 SDS Secret, 생성된 클러스터, 서버 SAN 검증과 실제 요청을 확인합니다. 게이트웨이 라우팅만으로 우회가 차단되지는 않으므로 별도 네트워크 제어로 egress를 제한합니다.

## 마이그레이션 전략

### 1단계: 현재 상태 확인

```bash
# 현재 mTLS 설정 확인
kubectl get peerauthentication -A

# 서비스별 mTLS 상태 확인
istioctl proxy-config clusters <pod-name> -n <namespace> -o json
```

이 순서는 계획된 마이그레이션용입니다. 평문 예외는 필요한 최소 네임스페이스·워크로드로 제한하며 오류 진단만을 위해 기존 STRICT 메시를 낮추지 않습니다.

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

수신 측의 `istio_requests_total`/`istio_tcp_connections_opened_total`을 `connection_security_policy`별로 조회해 관측된 평문 트래픽을 찾습니다. 대표 요청을 생성하고 실제 프록시 클러스터·인증서를 확인합니다. 메트릭이 없다고 평문 호출자가 없다는 뜻은 아닙니다.

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

## 일반적인 문제와 해결

### 1. mTLS 연결 실패

**증상**:
```
upstream connect error or disconnect/reset before headers. reset reason: connection failure
```

**원인 분석**:

```bash
# 1. PeerAuthentication 확인
kubectl get peerauthentication -A

# 2. DestinationRule mTLS 모드 확인
kubectl get destinationrule -A -o yaml | grep -A 5 "trafficPolicy"

# 3. 인증서 확인
istioctl proxy-config secret <pod-name> -n <namespace>

# 4. TLS 연결 확인
istioctl proxy-config clusters <source-pod> -n <namespace> --fqdn <dest-service> -o json

# 5. Envoy 로그 상세 확인
kubectl logs <pod-name> -c istio-proxy -n <namespace> | grep -E "(TLS|SSL|certificate)"
```

**해결 방법**:

1. **PeerAuthentication과 DestinationRule 불일치**:
```yaml
# 문제: PeerAuthentication은 STRICT, DestinationRule은 DISABLE
# 해결: DestinationRule을 ISTIO_MUTUAL로 변경
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: fix-mtls
spec:
  host: myservice.default.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL  # STRICT 모드와 일치
```

2. **사이드카가 주입되지 않은 파드**:
```bash
# 네임스페이스에 istio-injection 레이블 추가
kubectl label namespace default istio-injection=enabled

# 파드 재시작
kubectl rollout restart deployment/<deployment-name> -n default
```

### 2. 인증서 만료 문제

**증상**:
```
TLS error: Secret is not supplied by SDS
x509: certificate has expired
```

**인증서 만료 확인**:

```bash
# 워크로드 인증서 만료 날짜 확인
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -noout -dates

# CA 인증서 만료 확인
kubectl get secret istio-ca-secret -n istio-system -o json | \
  jq -r '.data."ca-cert.pem"' | base64 -d | openssl x509 -noout -dates

# 모든 워크로드의 인증서 만료 날짜 체크
for pod in $(kubectl get pods -n default -o jsonpath='{.items[*].metadata.name}'); do
  echo "Pod: $pod"
  istioctl proxy-config secret $pod -n default -o json 2>/dev/null | \
    jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
    base64 -d 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "No cert found"
done
```

**해결 방법**:

먼저 CA 연결, 유효한 신뢰 번들, 노드 시각을 복구하고 agent/istiod 로그에서 갱신 실패 원인을 확인합니다. istiod 재시작 자체는 만료된 CA를 복구하지 않습니다. 원인 해결 후에도 복구되지 않는 대상 워크로드만 중단 예산을 고려해 순차 교체합니다.

### 3. Clock Skew (시간 동기화 문제)

`certificate is not valid yet` 또는 만료 오류는 노드 시각 문제일 수 있습니다. UTC 시각과 인증서 `NotBefore`/`NotAfter`를 비교합니다. TLS에 보편적인 ±5분 허용 범위는 없습니다. EC2 노드에서 NTP 주소를 HTTP로 조회하는 대신 chrony 상태를 확인합니다:

```bash
date -u
chronyc tracking
chronyc sources -v
# Amazon Time Sync NTP: 169.254.169.123 (not an HTTP metadata URL)
```

노드 OS에 맞는 시간 동기화 서비스(`chronyd` 또는 `chrony`)를 복구합니다. 유효 기간 검증을 우회하려고 존재하지 않는 인증서 grace-period 환경 변수를 추가하지 않습니다.

### 4. 순환 참조 (Circular Dependency)

Service A → B → A 호출 순환 자체가 mTLS 오류를 만들지는 않습니다. 분산 트레이스, 애플리케이션 deadline·재시도, 연결 오류와 프록시 로그로 재귀 호출·자원 고갈을 TLS 협상 문제와 구분합니다. `istioctl analyze`는 설정을 검사할 뿐 실행 중 호출 그래프를 재구성하지 않습니다. TCP 연결 timeout 증가는 의존성 순환의 해결책이 아닙니다.

### 5. Mixed Protocol (mTLS + 평문)

`WRONG_VERSION_NUMBER`는 TLS/평문 포트 불일치의 단서입니다. Service 포트 프로토콜, 애플리케이션 URL scheme, PeerAuthentication, DestinationRule, 실제 프록시 클러스터를 확인합니다. 잘못된 명시적 TLS 설정을 제거하거나 대상 프로토콜을 수정하고 일반 메시 피어에는 auto mTLS를 사용합니다. 범위가 제한된 PERMISSIVE 예외는 의도적인 마이그레이션용이며 일반적인 오류 해결책이 아닙니다.

### 6. Headless Service mTLS

Headless Service도 auto mTLS를 지원합니다. 먼저 endpoint 검색과 Service 포트 이름을 확인합니다. 아래 명시적 규칙은 선택 사항이며 endpoint 메타데이터 누락이나 애플리케이션 프로토콜 불일치를 해결하지는 않습니다.

**증상**: Headless 서비스에서 mTLS 연결 실패

**해결 방법**:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: headless-service-mtls
spec:
  host: headless-service.default.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
    portLevelSettings:
    - port:
        number: 3306
      tls:
        mode: ISTIO_MUTUAL
```

### 7. mTLS와 네트워크 정책 충돌

사이드카 mTLS는 애플리케이션 대상 포트를 사용합니다. **15008은 ambient HBONE**이며 공통 사이드카 mTLS 포트가 아닙니다. 아래 사이드카 예제는 게이트웨이 → productpage:9080, productpage → reviews/details:9080, istiod:15012와 클러스터 DNS를 허용합니다. 적용 전에 레이블, 실제 의존성, 스크레이프·프로브, NodeLocal DNS를 맞춰야 합니다. Ambient는 해당 CNI와 NetworkPolicy 동작을 별도로 검토합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: productpage-sidecar
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: productpage
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: istio-system
      podSelector:
        matchLabels:
          istio: ingressgateway
    ports:
    - protocol: TCP
      port: 9080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: reviews
    - podSelector:
        matchLabels:
          app: details
    ports:
    - protocol: TCP
      port: 9080
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: istio-system
      podSelector:
        matchLabels:
          app: istiod
    ports:
    - protocol: TCP
      port: 15012
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

## 성능 및 모니터링

### mTLS 성능 영향 — EKS 실측 데이터

다음 과거 벤치마크는 암호화와 프록시 처리를 포함한 전체 데이터플레인 경로를 비교합니다. 아래는 이 가이드북이 EKS 전용 클러스터(Graviton m7g.xlarge, fortio 200qps·60초·커넥션 16개, 모든 케이스 Code 200 100%)에서 직접 측정한 값입니다:

| 케이스 (mTLS STRICT) | P50 | P90 | P99 | no-mesh 대비 P50 오버헤드 |
|----------------------|-----|-----|-----|--------------------------|
| no-mesh (평문 기준선) | 0.82ms | 1.73ms | 1.97ms | — |
| sidecar | 2.11ms | 2.89ms | 3.91ms | **+1.29ms** |
| ambient L4 (ztunnel만) | 0.86ms | 1.74ms | 1.98ms | **+0.04ms (거의 없음)** |
| ambient L7 (waypoint) | 2.68ms | 3.63ms | 3.98ms | **+1.86ms** |

핵심: "mTLS를 켜면 +20% 느려진다" 같은 단일 계수는 존재하지 않습니다. 이 실행에서 ambient L4의 P50 증가는 0.04ms였습니다. 비교 대상은 L7 처리와 프록시 경로도 다르므로 이 수치만으로 TLS 암호화 비용을 분리하거나 0이라고 증명할 수는 없습니다. 측정 방법·rollout 중 503 비율·재현 절차는 [Sidecar vs Ambient 실측 비교](../comparison/03-sidecar-vs-ambient.md)를 참고하세요. 워크로드가 다르면 반드시 자체 재측정이 필요합니다.

**최적화 방법**:

1. **아키텍처에 맞는 암호화 가속**: AES-NI는 x86 확장이고 Graviton은 Arm 암호화 확장을 사용합니다. CPU 기능을 확인하고 실제 암호군·워크로드로 측정합니다.
```bash
lscpu
rg -m 1 "^(flags|Features)" /proc/cpuinfo
```

2. **TLS 1.3 사용** (더 빠른 핸드셰이크):
```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    meshMTLS:
      minProtocolVersion: TLSV1_3
```

3. **Connection Pooling**:
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: connection-pool
spec:
  host: myservice.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 1s
      http:
        http1MaxPendingRequests: 1024
        http2MaxRequests: 1024
        maxRequestsPerConnection: 0  # No request-count cap; reuse connections
        idleTimeout: 900s
```

### Prometheus 메트릭

mTLS 적용 비율, 애플리케이션 오류, 인증서 갱신, TLS 핸드셰이크를 구분해서 측정합니다. 아래 HTTP 메트릭은 사이드카·waypoint의 L7 텔레메트리가 필요하며 ztunnel L4에서는 HTTP 상태를 보고하지 않습니다. Agent 인증서 메트릭은 일반적으로 15020 `/stats/prometheus`의 사이드카 agent를 스크레이프해야 하며 파일 기반 인증서나 다른 데이터플레인에서는 없을 수 있습니다. 실제 메트릭 이름과 레이블을 먼저 확인합니다.

```promql
# Observed HTTP request share protected by mTLS (destination reporter).
sum by (destination_service_name) (rate(istio_requests_total{reporter="destination",connection_security_policy="mutual_tls"}[5m]))
/
sum by (destination_service_name) (rate(istio_requests_total{reporter="destination"}[5m]))

# Remaining sidecar workload certificate lifetime in seconds.
istio_agent_cert_expiry_seconds{resource_name="default"}

# HTTP 5xx fraction on mTLS-protected requests; not TLS handshake failures.
sum by (destination_service_name) (rate(istio_requests_total{reporter="destination",response_code=~"5.*",connection_security_policy="mutual_tls"}[5m]))
/
sum by (destination_service_name) (rate(istio_requests_total{reporter="destination",connection_security_policy="mutual_tls"}[5m]))
```

암호화/전체 비율은 **관측된 트래픽의 적용 비율**이며 핸드셰이크 성공률이 아닙니다. HTTP 5xx는 정상 TLS 연결 위의 애플리케이션 오류일 수 있습니다. Envoy는 listener/cluster SSL 통계에 `handshake`, `connection_error`, `fail_verify_*` 카운터를 제공합니다. 기존 `ssl_connection_handshake_duration_bucket` 예제는 표준 Envoy 히스토그램이 아닙니다. 필요한 프록시 통계를 활성화하고 실제 노출 이름을 확인한 뒤 쿼리를 작성합니다.

### Grafana 대시보드

mTLS 적용 비율, 워크로드 인증서 잔여 시간(초), mTLS 위 HTTP 5xx, 실제 TLS 검증 카운터 패널을 구성합니다. 위 표현식을 설정된 Prometheus datasource에 연결합니다. 프로비저닝에는 Grafana dashboard provider로 JSON 파일을 마운트하거나 dashboard sidecar를 설정해야 하며 ConfigMap 생성만으로 로드되지 않습니다. 파일은 HTTP API의 `{ "dashboard": ... }` wrapper가 아닌 dashboard 객체 자체여야 합니다.

### 인증서 만료 알림

아래 예제는 자동 갱신되는 24시간 사이드카 leaf와 이 PrometheusRule을 선택하는 Prometheus Operator를 가정합니다. 실제 발급 TTL·갱신 일정에 맞게 임계치를 조정합니다. 스크레이프 실패·필수 시계열 누락도 별도로 알립니다. 인증서 메트릭이 없다고 정상은 아닙니다. Agent의 초 단위 gauge는 음수가 가능하지만 Envoy의 정수 일 단위 gauge는 24시간 leaf에 7일 경고를 적용하거나 음수로 만료를 판단하기에 부적합합니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-cert-expiration-alert
  namespace: istio-system
spec:
  groups:
  - name: istio-certificates
    rules:
    - alert: IstioWorkloadCertificateExpiringSoon
      expr: istio_agent_cert_expiry_seconds{resource_name="default"} < 3600
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Workload certificate has less than one hour remaining"
    - alert: IstioWorkloadCertificateExpired
      expr: istio_agent_cert_expiry_seconds{resource_name="default"} < 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Workload certificate has expired"
    - alert: IstioHTTP5xxOverMTLS
      expr: |
        sum by (destination_service_name) (rate(istio_requests_total{reporter="destination",response_code=~"5.*",connection_security_policy="mutual_tls"}[5m]))
        /
        sum by (destination_service_name) (rate(istio_requests_total{reporter="destination",connection_security_policy="mutual_tls"}[5m])) > 0.05
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "HTTP 5xx fraction exceeds 5% on mTLS traffic"
```

### 로깅 및 디버깅

```bash
# 1. Envoy 로그 레벨 변경 (동적)
istioctl proxy-config log <pod-name> -n <namespace> --level connection:debug

# 2. mTLS 관련 로그 필터링
kubectl logs <pod-name> -c istio-proxy -n <namespace> | grep -E "(TLS|SSL|certificate|handshake)"

# 3. Envoy Admin Interface에서 인증서 확인
kubectl exec -it <pod-name> -c istio-proxy -n <namespace> -- \
  curl -s localhost:15000/certs | jq '.'

# 4. TLS 연결 통계
kubectl exec -it <pod-name> -c istio-proxy -n <namespace> -- \
  curl -s localhost:15000/stats | grep ssl

# 5. 실시간 mTLS 트래픽 확인
istioctl dashboard envoy <pod-name>.<namespace>
# http://localhost:15000/stats/prometheus 에서 ssl 메트릭 확인
```

진단 후 기존 로그 레벨로 복구합니다. 최소 프록시 이미지에는 curl이 없을 수 있으므로 로컬 port-forward로 admin endpoint를 조회합니다.

### 베스트 프랙티스

1. **프로덕션 환경**:
   - STRICT 모드 사용
   - 사용자 정의 CA 인증서 사용
   - 인증서 자동 갱신 설정
   - 만료 알림 구성

2. **성능 최적화**:
   - TLS 1.3 사용
   - Connection pooling 활성화
   - CPU 아키텍처에 맞는 암호화 가속 사용

3. **모니터링**:
   - 인증서 만료 추적
   - mTLS 적용 비율과 TLS 검증 오류를 별도로 모니터링
   - 실제 핸드셰이크 카운터와 인증서 갱신 추적

4. **보안**:
   - 정기적인 CA 순환
   - 최소 권한 원칙
   - NetworkPolicy와 함께 사용

## 참고 자료

- [Istio mTLS](https://istio.io/latest/docs/concepts/security/#mutual-tls-authentication)
- [PeerAuthentication Reference](https://istio.io/latest/docs/reference/config/security/peer_authentication/)
- [DestinationRule TLS](https://istio.io/latest/docs/reference/config/networking/destination-rule/#ClientTLSSettings)
- [Cert-Manager](https://cert-manager.io/docs/)
- [AWS Certificate Manager](https://docs.aws.amazon.com/acm/)
- [AWS ALB mTLS](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/mutual-authentication.html)

- [사용자 CA 전제 조건](https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/)
- [Agent certificate settings](https://istio.io/latest/docs/reference/commands/pilot-agent/)
- [AWS Load Balancer Controller annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/)
- [Envoy TLS statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
