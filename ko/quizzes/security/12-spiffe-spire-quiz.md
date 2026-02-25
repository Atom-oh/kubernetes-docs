# SPIFFE/SPIRE 퀴즈

다음 질문들을 통해 SPIFFE/SPIRE 워크로드 아이덴티티에 대한 이해도를 점검해보세요.

---

## 문제

### 1. SPIFFE ID의 올바른 형식은?

- A) `urn:spiffe:trust-domain:path`
- B) `spiffe://trust-domain/path`
- C) `https://trust-domain.spiffe.io/path`
- D) `spiffe:trust-domain/path`

<details>
<summary>정답 보기</summary>

**정답: B) `spiffe://trust-domain/path`**

**설명:**
SPIFFE ID는 URI 형식의 워크로드 식별자입니다:

```
spiffe://trust-domain/path

예시:
spiffe://example.org/ns/production/sa/web-server
spiffe://cluster.local/k8s/ns/default/sa/frontend
```

구성요소:
- **스킴**: `spiffe://` (고정)
- **Trust Domain**: 조직/클러스터 식별 (예: `example.org`)
- **Path**: 워크로드 식별 경로 (예: `/ns/production/sa/web-server`)

SPIFFE ID는 X.509 인증서의 SAN(Subject Alternative Name) URI 필드에 포함됩니다.

</details>

---

### 2. X.509-SVID와 JWT-SVID의 주요 차이점은?

- A) X.509-SVID는 단기 토큰, JWT-SVID는 장기 인증서
- B) X.509-SVID는 mTLS용, JWT-SVID는 API 인증용
- C) JWT-SVID만 SPIFFE 표준
- D) 기능적 차이 없음

<details>
<summary>정답 보기</summary>

**정답: B) X.509-SVID는 mTLS용, JWT-SVID는 API 인증용**

**설명:**
SVID(SPIFFE Verifiable Identity Document) 유형별 특성:

| 특성 | X.509-SVID | JWT-SVID |
|------|------------|----------|
| 형식 | X.509 인증서 | JWT 토큰 |
| 주요 용도 | mTLS 연결 | API 인증, 프록시 통과 |
| 전달 방식 | TLS 핸드셰이크 | HTTP 헤더 |
| 유효 기간 | 보통 1시간 | 보통 5분 |
| 검증 방식 | 인증서 체인 | 서명 검증 |

```bash
# X.509-SVID 조회
/opt/spire/bin/spire-agent api fetch x509

# JWT-SVID 조회
/opt/spire/bin/spire-agent api fetch jwt -audience myservice
```

</details>

---

### 3. SPIRE Server의 주요 역할은?

- A) 워크로드에 직접 인증서 배포
- B) 등록 항목 관리 및 SVID 서명
- C) 네트워크 트래픽 암호화
- D) 서비스 디스커버리

<details>
<summary>정답 보기</summary>

**정답: B) 등록 항목 관리 및 SVID 서명**

**설명:**
SPIRE Server의 핵심 기능:

```
┌─────────────────────────────────────────┐
│             SPIRE Server                 │
├─────────────────────────────────────────┤
│ • Registration Entry 저장/관리           │
│ • 노드 어테스테이션 검증                  │
│ • SVID 서명 (CA 역할)                    │
│ • Trust Bundle 배포                      │
│ • Agent 인증 및 권한 부여                 │
└─────────────────────────────────────────┘
```

Registration Entry 예시:
```bash
# 워크로드 등록
spire-server entry create \
  -spiffeID spiffe://example.org/web-server \
  -parentID spiffe://example.org/host \
  -selector k8s:ns:production \
  -selector k8s:sa:web-server
```

Server는 중앙 집중식 ID 관리를 담당하며, 실제 워크로드와 직접 통신하지 않습니다.

</details>

---

### 4. SPIRE Agent의 주요 역할은?

- A) 클러스터 전체 정책 관리
- B) 노드에서 워크로드 어테스테이션 수행 및 SVID 전달
- C) 인증서 서명
- D) DNS 레코드 관리

<details>
<summary>정답 보기</summary>

**정답: B) 노드에서 워크로드 어테스테이션 수행 및 SVID 전달**

**설명:**
SPIRE Agent의 역할:

```
┌─────────────────────────────────────────┐
│              SPIRE Agent                 │
│           (각 노드에 배포)                │
├─────────────────────────────────────────┤
│ • 워크로드 어테스테이션 (프로세스 검증)    │
│ • Workload API 노출 (Unix Socket)        │
│ • SVID 캐싱 및 자동 갱신                  │
│ • Server와 통신하여 SVID 요청             │
└─────────────────────────────────────────┘
           │
           ▼
    /run/spire/agent.sock
           │
           ▼
┌─────────────────────────────────────────┐
│            워크로드 (Pod)                 │
│    SVID 요청 → Agent가 신원 확인 후 발급   │
└─────────────────────────────────────────┘
```

Agent는 각 노드에서 DaemonSet으로 실행되며, 워크로드의 신원을 로컬에서 검증합니다.

</details>

---

### 5. EKS 환경에서 SPIRE 노드 어테스테이션에 권장되는 방식은?

- A) k8s_sat (Service Account Token)
- B) k8s_psat (Projected Service Account Token)
- C) aws_iid (AWS Instance Identity Document)
- D) join_token

<details>
<summary>정답 보기</summary>

**정답: B) k8s_psat (Projected Service Account Token)**

**설명:**
EKS에서 k8s_psat 사용 이유:

```yaml
# SPIRE Agent DaemonSet 설정
spec:
  containers:
  - name: spire-agent
    volumeMounts:
    - name: spire-token
      mountPath: /var/run/secrets/tokens
  volumes:
  - name: spire-token
    projected:
      sources:
      - serviceAccountToken:
          path: spire-agent
          expirationSeconds: 600
          audience: spire-server
```

k8s_psat vs k8s_sat:

| 특성 | k8s_sat | k8s_psat |
|------|---------|----------|
| 토큰 만료 | 없음 | 있음 (설정 가능) |
| Audience | 없음 | 지정 가능 |
| 보안 수준 | 낮음 | 높음 |
| EKS 권장 | 아니오 | 예 |

PSAT은 바운드 서비스 계정 토큰으로, 만료 시간과 audience를 지정할 수 있어 더 안전합니다.

</details>

---

### 6. Kubernetes 워크로드 어테스테이션에서 사용되는 셀렉터 형식은?

- A) `pod:name:nginx`
- B) `k8s:ns:default`
- C) `kubernetes/namespace=default`
- D) `selector.k8s.io/ns:default`

<details>
<summary>정답 보기</summary>

**정답: B) `k8s:ns:default`**

**설명:**
Kubernetes 워크로드 어테스테이션 셀렉터:

```bash
# 워크로드 등록 예시
spire-server entry create \
  -spiffeID spiffe://example.org/frontend \
  -parentID spiffe://example.org/ns/spire/sa/spire-agent \
  -selector k8s:ns:production \           # 네임스페이스
  -selector k8s:sa:frontend \             # ServiceAccount
  -selector k8s:pod-label:app:frontend \  # Pod 레이블
  -selector k8s:container-name:app        # 컨테이너 이름
```

주요 셀렉터 유형:
- `k8s:ns:<namespace>`: 네임스페이스 매칭
- `k8s:sa:<service-account>`: ServiceAccount 매칭
- `k8s:pod-label:<key>:<value>`: Pod 레이블 매칭
- `k8s:container-name:<name>`: 컨테이너 이름 매칭
- `k8s:container-image:<image>`: 컨테이너 이미지 매칭

</details>

---

### 7. SPIFFE CSI Driver의 주요 목적은?

- A) 영구 볼륨 프로비저닝
- B) 워크로드에 SVID를 파일 시스템으로 마운트
- C) 네트워크 스토리지 연결
- D) 시크릿 암호화

<details>
<summary>정답 보기</summary>

**정답: B) 워크로드에 SVID를 파일 시스템으로 마운트**

**설명:**
SPIFFE CSI Driver는 Workload API 없이 SVID를 제공합니다:

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    volumeMounts:
    - name: spiffe
      mountPath: /run/spiffe
      readOnly: true
  volumes:
  - name: spiffe
    csi:
      driver: csi.spiffe.io
      readOnly: true
```

마운트되는 파일:
```
/run/spiffe/
├── svid.pem          # X.509 인증서
├── svid.key          # 개인키
└── bundle.pem        # Trust Bundle (CA 인증서)
```

장점:
- Workload API 통합 불필요
- 기존 애플리케이션에 쉽게 적용
- 자동 갱신 (CSI Driver가 관리)

</details>

---

### 8. SPIFFE 페더레이션의 주요 기능은?

- A) 단일 클러스터 내 서비스 통신
- B) 서로 다른 Trust Domain 간 상호 신뢰 설정
- C) DNS 기반 서비스 디스커버리
- D) 로드 밸런싱

<details>
<summary>정답 보기</summary>

**정답: B) 서로 다른 Trust Domain 간 상호 신뢰 설정**

**설명:**
SPIFFE 페더레이션 아키텍처:

```
┌────────────────────┐        ┌────────────────────┐
│  Trust Domain A    │        │  Trust Domain B    │
│  (cluster-a.com)   │◄──────►│  (cluster-b.com)   │
│                    │ 페더레이션│                    │
│  ┌──────────────┐  │        │  ┌──────────────┐  │
│  │ SPIRE Server │  │        │  │ SPIRE Server │  │
│  └──────────────┘  │        │  └──────────────┘  │
│         │          │        │         │          │
│  ┌──────────────┐  │        │  ┌──────────────┐  │
│  │  Workload A  │──────────────│  Workload B  │  │
│  └──────────────┘  │  mTLS   │  └──────────────┘  │
└────────────────────┘        └────────────────────┘
```

페더레이션 설정:
```bash
# Trust Domain A에서 B의 번들 가져오기
spire-server bundle set \
  -id spiffe://cluster-b.com \
  -path /path/to/cluster-b-bundle.pem
```

사용 사례:
- 멀티클러스터 서비스 메시
- 하이브리드 클라우드 환경
- 조직 간 제로 트러스트 통신

</details>

---

### 9. SPIFFE/SPIRE와 AWS IRSA(IAM Roles for Service Accounts) 비교 시 SPIFFE의 장점은?

- A) AWS 네이티브 통합
- B) IAM 정책 기반 세분화된 권한
- C) 클라우드 중립적이며 워크로드 간 mTLS 지원
- D) 설정 간편함

<details>
<summary>정답 보기</summary>

**정답: C) 클라우드 중립적이며 워크로드 간 mTLS 지원**

**설명:**
SPIFFE/SPIRE vs IRSA 비교:

| 특성 | SPIFFE/SPIRE | IRSA |
|------|--------------|------|
| 클라우드 의존성 | 없음 | AWS 전용 |
| 워크로드 간 인증 | mTLS 지원 | 미지원 |
| AWS 서비스 접근 | 별도 설정 필요 | 네이티브 |
| 멀티클라우드 | 지원 | 불가 |
| 온프레미스 | 지원 | 불가 |
| 복잡도 | 높음 | 낮음 |

SPIFFE/SPIRE 선택 상황:
- 워크로드 간 mTLS가 필요한 경우
- 멀티클라우드/하이브리드 환경
- 클라우드 독립적인 아이덴티티 필요 시

IRSA 선택 상황:
- AWS 서비스 접근만 필요한 경우
- 단순한 설정 선호 시

</details>

---

### 10. SPIFFE Trust Domain 네이밍 모범 사례는?

- A) 임의의 문자열 사용
- B) IP 주소 기반
- C) 조직 도메인 또는 클러스터 식별자 사용
- D) 숫자로만 구성

<details>
<summary>정답 보기</summary>

**정답: C) 조직 도메인 또는 클러스터 식별자 사용**

**설명:**
Trust Domain 네이밍 권장사항:

```
좋은 예시:
✓ spiffe://example.org              # 조직 도메인
✓ spiffe://prod.example.org         # 환경별 구분
✓ spiffe://cluster-1.example.org    # 클러스터별 구분
✓ spiffe://us-east-1.aws.example.org # 리전별 구분

나쁜 예시:
✗ spiffe://my-cluster              # 조직 식별 불가
✗ spiffe://192.168.1.100           # IP 변경 시 문제
✗ spiffe://12345                   # 의미 없음
✗ spiffe://test                    # 모호함
```

네이밍 원칙:
- **고유성**: 전역적으로 유일해야 함
- **계층 구조**: 조직/환경/클러스터 반영
- **안정성**: 장기간 변경 없이 유지
- **의미 전달**: 도메인 목적을 명확히 표현
- **DNS 호환**: 페더레이션 시 DNS로 번들 조회 가능

</details>

---

## 점수 계산

- **9-10개 정답**: 우수 - 해당 주제를 깊이 이해하고 있습니다.
- **7-8개 정답**: 양호 - 핵심 개념을 잘 파악하고 있습니다.
- **5-6개 정답**: 보통 - 추가 학습이 필요한 부분이 있습니다.
- **4개 이하**: 문서를 다시 복습하시기 바랍니다.

## 관련 문서

- [SPIFFE/SPIRE를 활용한 워크로드 아이덴티티](../../security/12-spiffe-spire.md)
