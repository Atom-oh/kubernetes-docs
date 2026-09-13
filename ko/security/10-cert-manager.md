<span id="목차"></span>

# cert-manager를 활용한 인증서 관리

> **마지막 업데이트**: 2026년 9월 13일
> **검증 기준**: cert-manager 1.21.2, cmctl 2.5.0, trust-manager 0.25.0, istio-csr 0.17.0, aws-privateca-issuer 1.9.2, ACK ACM 1.8.1. cert-manager 1.21의 공식 Kubernetes 지원·시험 범위는 1.33–1.36입니다.

cert-manager는 인증서 발급·갱신을 Kubernetes 리소스로 관리합니다. **CA 신뢰 배포, 애플리케이션 reload, 인증서 폐기·CRL/OCSP 운영은 별도 책임**입니다. 아래 예제는 로컬 schema·설정·라이브러리 검증을 거쳤으며 실제 CA 발급이나 AWS/Kubernetes 배포 결과가 아닙니다.

<span id="인증서-자동화의-필요성"></span>
<span id="cert-manager의-주요-기능"></span>
<span id="cncf-graduated-프로젝트"></span>
<span id="개요-1"></span>

## 개요

cert-manager는 2020년 11월 10일 CNCF에 합류했고 2022년 9월 19일 Incubating, **2024년 9월 29일 Graduated**로 승격됐습니다. Graduation은 특정 배포의 보안·가용성을 보증하지 않습니다.

| 관리 대상 | 확인할 책임 |
|---|---|
| 발급 | Issuer 인증, 요청자 승인, SAN·용도·유효기간 정책 |
| 갱신 | 실제 발급 수명, ARI/renewBefore, 실패 재시도와 경보 |
| 키 교체 | Secret 접근, 소비자 reload, CA rollover 순서 |
| 신뢰 | 어떤 root/intermediate를 어떤 namespace·process가 신뢰하는가 |
| 폐기 | CA의 revoke 절차와 CRL/OCSP 배포·소비 |

1.16.2 설치 예제와 오래된 호환성 표를 현재 지원 기준으로 사용하지 않습니다. 1.16은 2025년 6월에 EOL에 도달했습니다. 업그레이드는 중간 버전 release note와 CRD 변경을 확인해 계획합니다.

<span id="구성요소"></span>
<span id="구성요소-상세"></span>

## 아키텍처

![cert-manager 구성요소와 Issuer·Secret 관계](../.gitbook/assets/ko-security-10-cert-manager-0.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-security-10-cert-manager-0.html)

Controller가 Certificate를 조정하고 CertificateRequest를 만들며 issuer controller가 발급을 처리합니다. Webhook은 커스텀 리소스를 검증·defaulting·변환하고 cainjector는 지원 API/webhook 구성의 CA bundle을 관리합니다. CA/SelfSigned issuer는 반드시 외부 서비스인 것은 아닙니다.

<span id="helm을-사용한-설치"></span>
<span id="프로덕션-환경-권장-설정"></span>
<span id="설치-확인"></span>
<span id="설치-1"></span>

## 설치

설치 전 Kubernetes 지원 범위, Helm·클러스터 권한, Gateway API CRD와 실제 Gateway controller, 선택한 Prometheus Operator CRD를 확인합니다. Gateway API CRD를 controller 시작 후 설치했다면 재시작 및 discovery 상태를 확인해야 합니다.

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update jetstack
helm upgrade --install cert-manager jetstack/cert-manager \
  --version v1.21.2 --namespace cert-manager --create-namespace \
  --values cert-manager-values.yaml
kubectl get pods -n cert-manager
cmctl check api
```

```yaml
crds:
  enabled: true
  keep: true
replicaCount: 2
podDisruptionBudget:
  enabled: true
  minAvailable: 1
config:
  apiVersion: controller.config.cert-manager.io/v1alpha1
  kind: ControllerConfiguration
  gatewayAPI:
    enabled: true
prometheus:
  enabled: true
  servicemonitor:
    enabled: true
webhook:
  replicaCount: 2
  timeoutSeconds: 10
  podDisruptionBudget:
    enabled: true
    minAvailable: 1
cainjector:
  replicaCount: 2
  podDisruptionBudget:
    enabled: true
    minAvailable: 1
```

이 profile은 ServiceMonitor와 Gateway API를 사용하므로 관련 CRD/controller가 먼저 있어야 합니다. 그 기능이 없는 클러스터는 해당 설정을 끄고 최소 설치부터 검증합니다. HA replica와 PDB는 노드·AZ 분산 및 API 연결의 대체물이 아닙니다. 현재 설정은 `config.gatewayAPI.enabled`이며 이전 `enableGatewayAPI`도 1.21.2 decoder에서 허용되지만 deprecated입니다.

CRD를 보존하는 설정과 uninstall의 실제 리소스 소유권을 확인하세요. CRD 삭제는 해당 커스텀 리소스들을 삭제할 수 있으므로 업그레이드 해결책으로 무작정 삭제하지 않습니다.

<span id="리소스-관계도"></span>
<span id="certificate"></span>
<span id="issuer-vs-clusterissuer"></span>
<span id="certificaterequest"></span>

## 핵심 개념

![Certificate 리소스와 컨트롤러가 생성하는 발급 요청](../.gitbook/assets/ko-security-10-cert-manager-1.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-security-10-cert-manager-1.html)

| 리소스 | 범위·역할 |
|---|---|
| Certificate | namespace 안의 원하는 인증서와 출력 Secret |
| Issuer | 같은 namespace에서 참조하는 발급 설정 |
| ClusterIssuer | 여러 namespace에서 참조하는 발급 설정 |
| CertificateRequest | CSR과 issuerRef·승인/거부 상태를 갖는 발급 요청 |
| Order / Challenge | ACME 경로에서 사용하는 주문·검증 리소스 |

ClusterIssuer가 참조하는 credential/CA Secret은 controller의 cluster-resource namespace에 있으며 기본값은 cert-manager입니다. Issuer의 Secret은 Issuer namespace에 있습니다. Certificate 생성 권한만으로 허용 SAN·issuerRef가 제한되는 것은 아닙니다.

### Certificate와 갱신

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: app-tls
  namespace: demo-app
spec:
  secretName: app-tls
  dnsNames: [app.example.com]
  duration: 2160h
  renewBeforePercentage: 33
  privateKey:
    algorithm: ECDSA
    size: 256
    encoding: PKCS8
    rotationPolicy: Always
  usages: [server auth]
  issuerRef:
    name: lab-ca
    kind: ClusterIssuer
    group: cert-manager.io
```

요청 duration과 CA가 실제 발급한 기간은 다를 수 있습니다. 기본 갱신은 **실제 X.509 수명의 2/3 지점**이며 고정 15일/30일 전이 아닙니다. renewBeforePercentage는 실제 수명으로 버퍼를 계산합니다. renewBefore와 percentage는 서로 배타적으로 선택하고, duration은 최소1시간·유효 renewBefore는 최소5분·duration보다 작아야 합니다.

1.21.2의 renewal policy/windows와 지원되는 ARI 경로는 시점에 영향을 줄 수 있습니다. `renewal.policy: Disabled`는 자동 갱신을 끕니다. 설정값만 보지 말고 status.renewalTime, 실제 notBefore/notAfter, 실패 경보를 확인합니다. v1.18부터 privateKey.rotationPolicy 기본값은 Always입니다. 갱신된 key/cert가 Secret에 들어가도 application이 자동으로 reload한다고 가정하지 않습니다.

### CertificateRequest와 개인키

직접 요청할 때는 실제 PEM CSR이 필요합니다. 문서의 잘린 base64 문자열을 적용하지 않습니다. cmctl의 create certificaterequest는 **클러스터에 요청을 생성하는 명령**이며 오프라인 검증 명령이 아닙니다. cmctl approve/deny 권한도 별도로 제한합니다. 이 감사에서는 cert-manager PKI 라이브러리로 합성 key/CSR을 만들고 서명만 로컬 검증했습니다.

<span id="유형별-비교"></span>
<span id="selfsigned-issuer"></span>
<span id="ca-issuer"></span>
<span id="acme-issuer-let-s-encrypt"></span>
<span id="인증서-발급-흐름"></span>
<span id="http-01-솔버"></span>
<span id="dns-01-솔버-route53-irsa"></span>
<span id="와일드카드-인증서"></span>
<span id="aws-private-ca-issuer"></span>
<span id="vault-pki-issuer"></span>

## Issuer 유형

### SelfSigned와 CA bootstrap

[전체 bootstrap 예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/bootstrap.yaml)는 전용 lab root와 leaf를 만듭니다. root CA는 실습용이며 자동 renewal을 Disabled, root key rotation을 Never로 명시해 **계획 없는 trust-anchor 교체를 피합니다**. 운영 root 보관·오프라인 CA·분리된 intermediate·감사·폐기는 별도로 설계해야 합니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cert-manager
  labels:
    trust-bundle: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: demo-app
  labels:
    trust-bundle: enabled
    cert-manager-http01: enabled
---
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: bootstrap
  namespace: cert-manager
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: lab-root
  namespace: cert-manager
spec:
  secretName: lab-root
  isCA: true
  commonName: Documentation Lab Root
  subject:
    organizations: [Documentation Lab]
  duration: 8760h
  renewal:
    policy: Disabled
  privateKey:
    algorithm: ECDSA
    size: 256
    encoding: PKCS8
    rotationPolicy: Never
  usages: [cert sign, crl sign]
  issuerRef:
    name: bootstrap
    kind: Issuer
    group: cert-manager.io
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: lab-ca
spec:
  ca:
    secretName: lab-root
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: app-tls
  namespace: demo-app
spec:
  secretName: app-tls
  dnsNames: [app.example.com]
  duration: 2160h
  renewBeforePercentage: 33
  privateKey:
    algorithm: ECDSA
    size: 256
    encoding: PKCS8
    rotationPolicy: Always
  usages: [server auth]
  issuerRef:
    name: lab-ca
    kind: ClusterIssuer
    group: cert-manager.io
```

CA issuer는 CA 인증서/key가 담긴 Secret을 사용합니다. CA Secret을 바꾸는 것만으로 모든 leaf가 즉시 재발급되거나 모든 client trust가 갱신되지는 않습니다. CA issuer는 CRL/OCSP URL을 인증서에 넣을 수 있지만 CRL이나 OCSP 응답 자체를 생성·유지하지 않습니다. CA 수명보다 긴 leaf를 발급하지 않도록 별도 발급 정책도 필요합니다.

### ACME: HTTP-01과 DNS-01

![ACME HTTP·DNS 검증과 인증서 발급](../.gitbook/assets/ko-security-10-cert-manager-2.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-security-10-cert-manager-2.html)

HTTP-01은 해당 호스트의 port80 경로 접근이 필요하고 wildcard를 지원하지 않습니다. DNS-01은 DNS TXT 권한으로 wildcard를 검증합니다. 기존 authorization 재사용이나 ACM의 사전 검증 방식에서는 모든 요청마다 새 challenge가 생긴다고 가정하지 않습니다.

신규 설치에서 2026년 3월에 유지보수가 종료된 ingress-nginx를 기본값으로 안내하지 않습니다. [HTTP-01 Gateway 예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/public-staging.yaml)는 설치된 Envoy Gateway의 `envoy-gateway` GatewayClass를 전제로 합니다. 실제 이름을 확인하고, solver namespace의 `cert-manager-http01: enabled` label과 Gateway allowedRoutes를 맞춥니다. HTTPS용 Gateway shim은 Secret reference를 생성할 뿐 Gateway controller 설치나 TLS reload를 대신하지 않습니다.

[Route53 issuer](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/route53-issuer.yaml)와 [IAM 정책](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/route53-policy.json)은 hostedZoneID를 고정하고 TXT challenge 이름으로 변경 권한을 제한합니다. zone ID를 명시하면 ListHostedZonesByName 전체 조회 권한을 생략할 수 있습니다. IRSA 또는 지원되는 Pod Identity의 실제 controller 자격 증명과 교차 계정 role 경로를 확인합니다. Namespace selector나 dnsZones는 IAM 통제의 대체물이 아닙니다.

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: public-dns01
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: pki-admin@example.com
    privateKeySecretRef:
      name: public-dns01-account
    solvers:
      - selector:
          dnsZones: [example.com]
        dns01:
          route53:
            region: ap-northeast-2
            hostedZoneID: Z1234567890ABC
```

Let's Encrypt staging도 rate limit이 있으며 production root로 신뢰되지 않습니다. ACME account는 환경별로 구분됩니다. 만료 알림 email은 2025년에 종료되었으므로 email 필드만으로 만료 감시를 대신하지 않습니다. 429 응답은 Retry-After와 해당 한도의 보충 주기를 따르며 무조건1시간 후 재시도로 일반화하지 않습니다. ARI renewal과 일반 신규 발급의 한도 적용도 다릅니다.

### AWS Private CA

외부 aws-privateca-issuer controller에 CA ARN별 발급·조회 권한과 EKS workload identity가 필요합니다. [예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/pca-issuer.yaml)는 실제 CA ARN으로 교체해야 하며 CA 모드·template·algorithm·용도·요청 수명을 검증합니다. short-lived CA의 한도와 비용도 별도로 확인하세요. 승인 검사를 끄는 disableApprovedCheck를 해결책으로 사용하지 않습니다.

```bash
helm repo add awspca https://cert-manager.github.io/aws-privateca-issuer
helm upgrade --install aws-pca-issuer awspca/aws-privateca-issuer \
  --version v1.9.2 --namespace cert-manager
```

PCA controller의 기본 IAM 작업은 acm-pca:DescribeCertificateAuthority, acm-pca:GetCertificate, acm-pca:IssueCertificate입니다. Resource를 사용할 CA ARN으로 제한합니다.

### Vault PKI

[Issuer와 token RBAC](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/vault-issuer.yaml)는 demo-app/vault-issuer ServiceAccount의 token만 요청하도록 제한합니다. Vault 서버 TLS CA Secret은 따로 제공해야 합니다. [PKI role/policy 설정](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/vault-setup.sh)은 기존 PKI·Kubernetes auth mount, 승인된 Vault identity와 TokenReview 권한을 전제로 합니다.

Vault role은 SAN 범위를 제한하고 audience를 `vault://demo-app/vault-pki`로 issuer에 맞춥니다. Vault가 어디서 실행되는지에 따라 reviewer JWT·Kubernetes API audience·OIDC 접근 방식이 달라집니다. `--tls-skip-verify`나 광범위한 default Vault policy로 연결 오류를 우회하지 않습니다.

<span id="acm-vs-cert-manager-비교"></span>
<span id="alb-ingress-acm"></span>
<span id="ingress-nginx-cert-manager"></span>
<span id="nlb-tls-종단"></span>
<span id="gateway-api-cert-manager"></span>

## EKS 통합 패턴

| 경로 | TLS 종료·키 위치 |
|---|---|
| ALB/NLB TLS listener + ACM | AWS load balancer가 ACM ARN 사용 |
| NLB TCP + Gateway/Pod | backend가 Kubernetes Secret의 key/cert로 TLS 종료 |
| Gateway HTTPS listener | Gateway controller가 같은 namespace의 TLS Secret 참조 |
| ACM exportable public certificate | 명시적으로 export한 key/cert를 자체 workload에서 사용 |

ALB는 cert-manager의 Kubernetes Secret을 직접 읽어 listener 인증서로 사용하지 않습니다. import/export/ACM ARN 연결이 필요합니다. [ALB 예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/alb-acm-ingress.yaml)는 실제 ACM ARN과 backend Service를 요구합니다. [NLB TCP 예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/nlb-tcp-service.yaml)는 TLS를 backend8443으로 통과시키며 backend가 실제 TLS를 제공해야 합니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: app-gateway
  namespace: demo-app
  annotations:
    cert-manager.io/cluster-issuer: lab-ca
spec:
  gatewayClassName: envoy-gateway
  listeners:
    - name: https
      hostname: app.example.com
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - group: ""
            kind: Secret
            name: app-gateway-tls
      allowedRoutes:
        namespaces:
          from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app
  namespace: demo-app
spec:
  parentRefs:
    - name: app-gateway
  hostnames: [app.example.com]
  rules:
    - backendRefs:
        - name: app
          port: 8080
```

이 Gateway는 lab-ca 인증서를 사용하므로 일반 browser가 신뢰하지 않습니다. 실제 공개 발급자를 쓰려면 승인 정책·domain validation과 controller를 준비합니다. GatewayClass 이름과 certificateRefs의 namespace/종류를 확인하고, 두 controller가 같은 Secret을 동시에 관리하지 않게 합니다.

<span id="_2026년-7월-업데이트-acm의-acme-프로토콜-지원"></span>
<span id="지원-인증서-유형"></span>
<span id="적용-시나리오"></span>
<span id="예시-ack를-통한-certificate-리소스-정의"></span>
<span id="cert-manager와-비교"></span>

## AWS 네이티브 대안: ACM + ACK

### ACM RequestCertificate와 ACK export

ACK ACM도 설치·운영하는 오픈소스 controller입니다. 1.8.1의 [예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/ack-acm.yaml)는 `options.export: ENABLED`, `exportTo`와 실제 출력 Secret을 명시합니다. 발급 요청만 정의한다고 자동으로 TLS Secret이 만들어지는 것은 아닙니다. 현재 CRD에는 `validationMethod`가 없으므로 이전 예제의 필드를 그대로 복사하지 않습니다.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: exported-public-tls
  namespace: demo-app
type: kubernetes.io/tls
data:
  tls.crt: ""
  tls.key: ""
---
apiVersion: acm.services.k8s.aws/v1alpha1
kind: Certificate
metadata:
  name: exportable-public-tls
  namespace: demo-app
spec:
  domainName: app.example.com
  keyAlgorithm: RSA_2048
  options:
    export: ENABLED
  exportTo:
    namespace: demo-app
    name: exported-public-tls
    key: tls.crt
```

Domain validation은 별도입니다. ACM이 제공하는 CNAME을 Route53 ACK 등으로 관리할 수 있지만 ACM controller 설치만으로 모든 DNS provider의 소유권 검증이 완료되지는 않습니다. Exportable public certificate 비용, controller IAM/RBAC·namespace 경계, key가 담긴 Secret 접근을 검토합니다. mTLS의 private CA·SPIFFE identity는 별도 issuer와 trust 설계가 필요합니다.

### ACM ACME: EAB와 사전 도메인 검증

2026년 7월6일 발표된 ACM ACME는45일 public certificate를 발급합니다. PKI 관리자가 endpoint와 domain validation을 준비하고 IAM role에 연결된 EAB credential을 발급한 뒤 client를 등록합니다. **server 주소만 바꾸는 절차가 아닙니다.** HMAC key는 안전하게 저장하고 ClusterIssuer가 읽는 cert-manager namespace의 acm-eab Secret/hmac key를 제공하세요.

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: acm-acme
spec:
  acme:
    server: https://acm-acme-enroll.ap-northeast-2.api.aws/REPLACE_ENDPOINT_ID/directory
    email: pki-admin@example.com
    privateKeySecretRef:
      name: acm-acme-account
    externalAccountBinding:
      keyID: REPLACE_EAB_KEY_ID
      keySecretRef:
        name: acm-eab
        key: hmac
```

endpoint ID·EAB keyID는 대체값입니다. 승인된 domain은 endpoint 수준에서 미리 검증되어야 합니다. ACM ACME는 client가 개인키를 생성·보유하고 client가 갱신합니다. ACM inventory에 ARN이 생겨도 이 인증서를 ALB/CloudFront/API Gateway의 관리형 통합에 바로 연결할 수는 없습니다. ExportCertificate/RenewCertificate/RevokeCertificate도 이 발급 경로에 적용되지 않으며 lifecycle은 ACME client가 담당합니다. AWS 통합 서비스용 certificate는 RequestCertificate 경로와 구분합니다.

<span id="istio-istio-csr"></span>
<span id="istio-csr-아키텍처"></span>
<span id="istio-csr-설치"></span>
<span id="istio-ca-issuer-설정"></span>
<span id="istio-설치-istio-csr-사용"></span>
<span id="linkerd-trust-manager"></span>

externalAccountBinding이 참조하는 Secret 값은 base64url 인코딩된 HMAC 키여야 합니다. Kubernetes Secret의 data 인코딩은 별도 계층입니다. 제공자가 이미 인코딩한 값을 이중 인코딩하지 않도록 [ACME EAB 설정](https://cert-manager.io/docs/configuration/acme/)을 확인합니다.

## 서비스 메시 통합

![istio-agent·istio-csr·SDS와 프록시 간 mTLS](../.gitbook/assets/ko-security-10-cert-manager-3.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-security-10-cert-manager-3.html)

### Istio와 istio-csr

Sidecar 흐름에서는 istio-agent가 CSR을 만들고 istio-csr가 CertificateRequest를 제출합니다. agent는 발급된 key/cert를 SDS로 Envoy에 전달하며 workload proxy 사이에 mTLS를 구성합니다. Envoy와 같은 Pod의 application 사이가 자동으로 mTLS가 되는 것은 아닙니다.

[istio-csr values](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/istio-csr-values.yaml)는 rootCAFile에 대응하는 ConfigMap volume/mount를 실제로 구성합니다. application-trust bundle이 cert-manager namespace에 생성되고 issuer가 Ready가 된 뒤 설치합니다. root 파일 경로만 지정하거나 빈 PEM을 meshConfig에 넣는 것으로 충분하지 않습니다. Istio의 현재 Helm/istioctl external-CA 설정을 사용하고, istio-csr 경로와 Kubernetes CSR RA 경로를 혼합하지 않습니다. Ambient 지원은 별도로 확인합니다.

```bash
helm upgrade --install cert-manager-istio-csr jetstack/cert-manager-istio-csr \
  --version v0.17.0 --namespace cert-manager --values istio-csr-values.yaml
```

### Linkerd와 trust-manager

[Linkerd identity 예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/linkerd-identity.yaml)는 발급용 Secret과 root bundle ConfigMap을 준비합니다. pinned control-plane chart2026.9.1은 linkerd-identity-issuer Secret과 linkerd-identity-trust-roots ConfigMap을 참조합니다.

```yaml
identity:
  externalCA: true
  issuer:
    scheme: kubernetes.io/tls
```

이 설정은 외부 issuer Secret을 사용해 갱신을 소비하도록 연결합니다. 설치 때 key를 파일로 추출해 한 번 복사하는 것과 다릅니다. root rollover에는 이전·새 root의 overlap, workload 갱신 및 trust reload 계획이 필요합니다. 예제 lab root는 수동 관리이며 자동 갱신을 끈 상태입니다.

<span id="bundle-리소스"></span>
<span id="사용-예시"></span>

## trust-manager

trust-manager0.25.0 chart 기본 렌더링은 `trust.cert-manager.io/v1alpha1 Bundle`을 사용합니다. Repo에 추가 CRD가 있다는 이유만으로 기본 설치 API가 바뀌었다고 가정하지 않습니다. source Secret/ConfigMap은 설정된 trust namespace에서 읽습니다.

```yaml
apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: application-trust
spec:
  sources:
    - secret:
        name: lab-root
        key: tls.crt
  target:
    configMap:
      key: ca-bundle.pem
    namespaceSelector:
      matchLabels:
        trust-bundle: enabled
```

`inLine`이 실제 inline PEM 필드이며 `inlineString`은 아닙니다. 포함하는 public CA와 private root를 최소화하고 namespaceSelector로 배포 범위를 명시합니다. Secret target은 별도 활성화/RBAC가 필요하므로 기본 예제는 ConfigMap만 사용합니다. trust bundle은 trust anchor 자료이며 private key를 배포하지 않습니다.

[소비자 Deployment](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/trust-consumer.yaml)는 디렉터리 mount를 사용합니다. subPath로 파일을 mount하면 ConfigMap 변경이 그 mount에 자동 반영되지 않습니다. 디렉터리 mount도 프로세스의 TLS context reload를 보장하지 않으므로 애플리케이션이 SSL_CERT_FILE 또는 해당 trust store 설정을 실제로 사용하는지 시험합니다.

<span id="prometheus-메트릭"></span>
<span id="인증서-상태-확인"></span>
<span id="cmctl-cli"></span>
<span id="일반적인-문제-해결"></span>
<span id="dns-전파-지연-dns-01"></span>
<span id="let-s-encrypt-rate-limit"></span>
<span id="webhook-타임아웃"></span>

## 모니터링 및 트러블슈팅

설치한 chart가 생성하는 ServiceMonitor의 selector와 port/targetPort를 기준으로 확인합니다. 1.21.2 profile은 controller/cainjector/webhook의 http-metrics target port를 선택합니다. 존재하지 않는 tcp-prometheus-servicemonitor 이름을 직접 쓰지 않습니다.

```yaml
groups:
  - name: cert-manager
    rules:
      - alert: CertificateNotReady
        expr: certmanager_certificate_ready_status{condition="True"} == 0
        for: 10m
        labels:
          severity: critical
      - alert: CertificateExpiringSoon
        expr: (certmanager_certificate_expiration_timestamp_seconds - time() < 604800) and (certmanager_certificate_expiration_timestamp_seconds - time() > 86400)
        for: 30m
        labels:
          severity: warning
      - alert: CertificateExpiryCritical
        expr: (certmanager_certificate_expiration_timestamp_seconds - time() <= 86400) and (certmanager_certificate_expiration_timestamp_seconds - time() > 0)
        for: 10m
        labels:
          severity: critical
      - alert: CertificateExpired
        expr: (certmanager_certificate_expiration_timestamp_seconds > 0) and (certmanager_certificate_expiration_timestamp_seconds <= time())
        for: 5m
        labels:
          severity: critical
```

ready metric에는 True/False/Unknown condition series가 있으므로 조건 없이 `==0`을 쓰면 정상 인증서에서도 오탐할 수 있습니다. 위 rules는 정상·NotReady·만료 임박·24시간 이내·만료5case/20assertion을 promtool로 검증했습니다. 수집 자체가 멈춘 경우는 별도의 scrape/absence 경보가 필요합니다.

```bash
kubectl get certificates,certificaterequests -A
kubectl get orders,challenges -A
kubectl describe certificate app-tls -n demo-app
cmctl status certificate app-tls -n demo-app
# 아래는 실제 변경 명령이며 권한과 영향 확인 후 사용합니다.
cmctl renew app-tls -n demo-app
```

DNS resolver 선택은 propagation 대기 시간을 늘리는 옵션과 다릅니다. split-horizon DNS·CAA·TXT 권한·CNAME·HTTP path와 실제 Challenge reason을 확인합니다. Webhook timeout은 연결·인증·routing 문제를 조사한 뒤 chart의 timeoutSeconds(1–30초)로 조정하며, 존재하지 않는 `--webhook-timeout` 플래그를 사용하지 않습니다.

<span id="갱신-버퍼-설정"></span>
<span id="백업-ca-전략"></span>
<span id="멀티-테넌트-issuer-전략"></span>
<span id="개인키-관리"></span>
<span id="secret-템플릿"></span>

## 모범 사례

- [namespace 범위 Role](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/certificate-requester-rbac.yaml)은 Certificate만 관리하며 개발자에게 클러스터 전체 Secret 읽기를 부여하지 않습니다. SAN·issuerRef·secretName 통제에는 별도 admission/approval 정책이 필요합니다.
- CertificateRequest 승인과 CA credential 권한을 분리합니다. 승인 controller의 default 동작을 확인하고 approver-policy 등 필요한 발급 정책을 구성합니다.
- Root key backup은 암호화·접근 통제·복구 시험을 포함하며 평문 YAML로 일반 디렉터리에 덤프하지 않습니다. Kubernetes Secret의 base64는 암호화가 아닙니다.
- Private CA를 public CA의 자동 fallback으로 사용하지 않습니다. client trust·이름·용도·키 접근·복구 시간을 따로 검증합니다.
- secretTemplate의 annotation/label은 metadata이며 외부 시크릿 동기화 도구를 자동 활성화하지 않습니다.
- 자동 갱신·CA rollover·Secret 소비자 reload·폐기를 각각 시험합니다. API schema나 Helm render 성공은 실제 발급 성공을 의미하지 않습니다.

<span id="핵심-정리"></span>
<span id="issuer-선택-가이드"></span>
<span id="참고-자료"></span>

## 요약 및 참고 자료

로컬 검증은 pinned Helm/CRD, controller config decoder, renewal6case, 실제 CSR 생성·서명 확인, Prometheus5case/20assertion, 다이어그램24browsercase를 포함합니다. 실제 CA/ACME 발급, AWS 리소스 생성, Vault login, mesh 설치·mTLS runtime은 실행하지 않았습니다.

- [cert-manager releases](https://cert-manager.io/docs/releases/)
- [CNCF project history](https://www.cncf.io/projects/cert-manager/)
- [Certificate renewal and rotation](https://cert-manager.io/docs/usage/certificate/)
- [CA issuer limitations](https://cert-manager.io/docs/configuration/ca/)
- [Vault issuer](https://cert-manager.io/docs/configuration/vault/)
- [Gateway API issuer integration](https://cert-manager.io/docs/usage/gateway/)
- [trust-manager](https://cert-manager.io/docs/trust/trust-manager/)
- [istio-csr](https://cert-manager.io/docs/usage/istio-csr/)
- [Linkerd automatic certificate rotation](https://linkerd.io/2-edge/tasks/automatically-rotating-control-plane-tls-credentials/)
- [ACM Kubernetes export](https://docs.aws.amazon.com/acm/latest/userguide/exportable-certificates-kubernetes.html)
- [ACM ACME](https://docs.aws.amazon.com/acm/latest/userguide/acm-acme.html)
- [ACM ACME launch](https://aws.amazon.com/about-aws/whats-new/2026/07/aws-certificate-manager-acme/)
- [AWS Private CA issuer](https://github.com/cert-manager/aws-privateca-issuer/tree/v1.9.2)
- [Let’s Encrypt rate limits](https://letsencrypt.org/docs/rate-limits/)
- [Staging environment](https://letsencrypt.org/docs/staging-environment/)
- [Expiration emails retired](https://letsencrypt.org/2025/01/22/ending-expiration-emails/)
- [Ingress NGINX retirement](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
