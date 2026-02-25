# cert-manager 퀴즈

다음 질문들을 통해 cert-manager와 Kubernetes 인증서 관리에 대한 이해도를 점검해보세요.

---

## 문제

### 1. cert-manager 프로젝트의 CNCF 상태는?

- A) Sandbox
- B) Incubating
- C) Graduated
- D) Archived

<details>
<summary>정답 보기</summary>

**정답: C) Graduated**

**설명:**
cert-manager는 2022년 10월 CNCF Graduated 프로젝트로 승격되었습니다. 이는 프로젝트의 성숙도, 보안성, 거버넌스가 프로덕션 환경에서 사용하기에 충분히 검증되었음을 의미합니다. Kubernetes, Prometheus, Envoy와 같은 수준의 성숙도를 인정받은 것입니다.

</details>

---

### 2. cert-manager의 핵심 구성요소가 아닌 것은?

- A) controller
- B) webhook
- C) cainjector
- D) scheduler

<details>
<summary>정답 보기</summary>

**정답: D) scheduler**

**설명:**
cert-manager의 핵심 구성요소는 다음과 같습니다:

- **controller**: Certificate 리소스를 감시하고 인증서 발급/갱신을 관리
- **webhook**: ValidatingWebhook과 MutatingWebhook으로 리소스 유효성 검증
- **cainjector**: CA 번들을 자동으로 Webhook 설정에 주입

scheduler는 cert-manager의 구성요소가 아닙니다.

</details>

---

### 3. Issuer와 ClusterIssuer의 주요 차이점은?

- A) 지원하는 인증서 종류
- B) 적용 범위(네임스페이스 vs 클러스터 전체)
- C) ACME 프로토콜 지원 여부
- D) 인증서 갱신 주기

<details>
<summary>정답 보기</summary>

**정답: B) 적용 범위(네임스페이스 vs 클러스터 전체)**

**설명:**
두 리소스의 차이는 적용 범위입니다:

```yaml
# Issuer: 특정 네임스페이스 내에서만 사용 가능
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: letsencrypt-staging
  namespace: my-namespace  # 이 네임스페이스에서만 참조 가능

---
# ClusterIssuer: 모든 네임스페이스에서 사용 가능
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod  # 클러스터 전역에서 참조 가능
```

멀티테넌트 환경에서는 Issuer로 네임스페이스별 격리를, 단일 팀 환경에서는 ClusterIssuer로 관리 편의성을 높일 수 있습니다.

</details>

---

### 4. ACME 챌린지 방식 중 와일드카드 인증서를 지원하는 것은?

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) 모든 방식이 지원

<details>
<summary>정답 보기</summary>

**정답: B) DNS-01**

**설명:**
ACME 챌린지 방식별 특징:

| 방식 | 와일드카드 지원 | 요구사항 |
|------|----------------|----------|
| HTTP-01 | X | 포트 80 접근 가능 |
| DNS-01 | O | DNS 레코드 수정 권한 |
| TLS-ALPN-01 | X | 포트 443 접근 가능 |

```yaml
# DNS-01 챌린지로 와일드카드 인증서 발급
apiVersion: cert-manager.io/v1
kind: Certificate
spec:
  dnsNames:
    - "*.example.com"  # 와일드카드
    - "example.com"
  issuerRef:
    name: letsencrypt-dns01
    kind: ClusterIssuer
```

DNS-01은 DNS TXT 레코드를 통해 도메인 소유권을 검증하므로 와일드카드 인증서 발급이 가능합니다.

</details>

---

### 5. Certificate 리소스의 secretName 필드의 역할은?

- A) Issuer의 인증 정보를 저장
- B) 발급된 인증서와 개인키를 저장할 Secret 이름 지정
- C) ACME 계정 키를 저장
- D) CA 번들을 저장

<details>
<summary>정답 보기</summary>

**정답: B) 발급된 인증서와 개인키를 저장할 Secret 이름 지정**

**설명:**
secretName은 cert-manager가 발급한 인증서를 저장할 Kubernetes Secret의 이름을 지정합니다:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: my-app-cert
  namespace: default
spec:
  secretName: my-app-tls  # 이 이름의 Secret이 생성됨
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - myapp.example.com
```

생성되는 Secret 구조:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-app-tls
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-certificate>
  tls.key: <base64-encoded-private-key>
  ca.crt: <base64-encoded-ca-certificate>  # 선택적
```

</details>

---

### 6. AWS Private CA(PCA)를 Kubernetes에서 사용하기 위한 cert-manager 확장은?

- A) aws-pca-controller
- B) aws-privateca-issuer
- C) pca-cert-manager
- D) aws-ca-plugin

<details>
<summary>정답 보기</summary>

**정답: B) aws-privateca-issuer**

**설명:**
aws-privateca-issuer는 AWS Private CA를 cert-manager의 외부 Issuer로 사용할 수 있게 해주는 공식 확장입니다:

```yaml
apiVersion: awspca.cert-manager.io/v1beta1
kind: AWSPCAIssuer
metadata:
  name: aws-pca-issuer
  namespace: default
spec:
  arn: arn:aws:acm-pca:us-east-1:123456789:certificate-authority/abc-123
  region: us-east-1
```

주요 사용 사례:
- 엔터프라이즈 PKI 통합
- 규정 준수가 필요한 내부 서비스 인증서
- mTLS를 위한 클라이언트 인증서 발급
- 하이브리드 환경에서 일관된 CA 사용

</details>

---

### 7. trust-manager의 주요 기능은?

- A) 인증서 발급 자동화
- B) CA 번들을 ConfigMap/Secret으로 배포
- C) 인증서 만료 알림
- D) ACME 챌린지 자동화

<details>
<summary>정답 보기</summary>

**정답: B) CA 번들을 ConfigMap/Secret으로 배포**

**설명:**
trust-manager는 cert-manager 팀에서 개발한 CA 번들 배포 도구입니다:

```yaml
apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: my-ca-bundle
spec:
  sources:
    - useDefaultCAs: true  # 시스템 CA 포함
    - secret:
        name: my-internal-ca
        key: ca.crt
    - configMap:
        name: additional-ca
        key: ca-bundle.crt
  target:
    configMap:
      key: ca-bundle.crt
    namespaceSelector:
      matchLabels:
        inject-ca: "true"
```

이를 통해 모든 네임스페이스에 일관된 CA 번들을 자동 배포하고 동기화할 수 있습니다.

</details>

---

### 8. Certificate 리소스의 renewBefore 필드 설정 시 갱신 동작은?

- A) 만료일 이전 지정된 기간에 자동 갱신 시작
- B) 수동 갱신 요청 시점 지정
- C) 인증서 유효 기간 설정
- D) 갱신 실패 시 재시도 간격

<details>
<summary>정답 보기</summary>

**정답: A) 만료일 이전 지정된 기간에 자동 갱신 시작**

**설명:**
renewBefore는 인증서 만료 전 갱신을 시작할 시점을 지정합니다:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: my-cert
spec:
  secretName: my-cert-tls
  duration: 2160h     # 90일 유효
  renewBefore: 360h   # 만료 15일 전 갱신 시작
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - myapp.example.com
```

위 설정에서:
- 인증서 유효 기간: 90일
- 갱신 시작 시점: 만료 15일 전 (75일째)
- cert-manager가 자동으로 새 인증서를 발급하고 Secret을 업데이트

</details>

---

### 9. Istio 서비스 메시와 cert-manager를 연동하는 컴포넌트는?

- A) istio-gateway
- B) istio-csr
- C) istio-ca
- D) istio-cert

<details>
<summary>정답 보기</summary>

**정답: B) istio-csr**

**설명:**
istio-csr(Certificate Signing Request)은 Istio의 워크로드 인증서를 cert-manager를 통해 발급받도록 연동하는 컴포넌트입니다:

```yaml
# istio-csr 설치
helm install istio-csr jetstack/cert-manager-istio-csr \
  --namespace cert-manager \
  --set "app.tls.rootCAFile=/var/run/secrets/istio-csr/ca.pem" \
  --set "app.certmanager.issuer.name=istio-ca" \
  --set "app.certmanager.issuer.kind=ClusterIssuer"
```

주요 이점:
- Istio의 기본 CA(istiod) 대신 외부 CA 사용
- 중앙 집중식 인증서 관리
- 엔터프라이즈 PKI 통합
- 인증서 가시성 및 감사

</details>

---

### 10. cert-manager와 AWS ACM(Certificate Manager) 비교 시 cert-manager의 장점은?

- A) AWS 관리형 서비스로 운영 부담 없음
- B) ALB/NLB와 네이티브 통합
- C) 인프라 독립적으로 멀티클라우드/온프레미스에서 동일하게 사용
- D) 무료 인증서 자동 갱신

<details>
<summary>정답 보기</summary>

**정답: C) 인프라 독립적으로 멀티클라우드/온프레미스에서 동일하게 사용**

**설명:**
cert-manager vs AWS ACM 비교:

| 특성 | cert-manager | AWS ACM |
|------|--------------|---------|
| 인프라 의존성 | 없음 (K8s만 필요) | AWS 전용 |
| 멀티클라우드 | 지원 | 불가 |
| 온프레미스 | 지원 | 불가 |
| 운영 부담 | 직접 관리 필요 | AWS 관리형 |
| Ingress 통합 | 모든 Ingress Controller | ALB/NLB만 |
| 비용 | Let's Encrypt 무료 | 퍼블릭 무료, Private 유료 |

cert-manager는:
- EKS, GKE, AKS, 온프레미스 모두에서 동일하게 작동
- Kubernetes 네이티브 워크플로우
- GitOps와 자연스러운 통합
- 다양한 Issuer 지원 (Let's Encrypt, Vault, Venafi 등)

</details>

---

## 점수 계산

- **9-10개 정답**: 우수 - 해당 주제를 깊이 이해하고 있습니다.
- **7-8개 정답**: 양호 - 핵심 개념을 잘 파악하고 있습니다.
- **5-6개 정답**: 보통 - 추가 학습이 필요한 부분이 있습니다.
- **4개 이하**: 문서를 다시 복습하시기 바랍니다.

## 관련 문서

- [cert-manager를 활용한 인증서 관리](../../security/10-cert-manager.md)
