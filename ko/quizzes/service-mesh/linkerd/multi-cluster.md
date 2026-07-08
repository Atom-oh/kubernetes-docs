# Linkerd 다중 클러스터 퀴즈

이 퀴즈는 Linkerd 다중 클러스터 기능에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Linkerd 다중 클러스터 아키텍처의 핵심 개념은?

A. 메시 페더레이션
B. 서비스 미러링
C. 클러스터 병합
D. 글로벌 로드밸런서

<details>
<summary>정답 및 설명</summary>

**정답: B. 서비스 미러링**

**설명:**
Linkerd는 서비스 미러링 아키텍처를 사용합니다. 원격 클러스터의 내보낸 서비스가 로컬 클러스터에 미러 서비스로 나타나, 로컬 서비스처럼 접근할 수 있습니다.

</details>

### 2. 두 클러스터 간 mTLS 통신을 위해 공유해야 하는 것은?

A. Identity Issuer
B. Trust Anchor
C. 워크로드 인증서
D. Kubernetes Secret

<details>
<summary>정답 및 설명</summary>

**정답: B. Trust Anchor**

**설명:**
두 클러스터가 상호 신뢰하려면 동일한 Trust Anchor(Root CA)를 공유해야 합니다. 각 클러스터는 별도의 Identity Issuer를 가질 수 있지만, 같은 Trust Anchor에서 서명되어야 합니다.

</details>

### 3. 서비스를 다른 클러스터에 내보내기 위한 레이블은?

A. linkerd.io/exported: "true"
B. mirror.linkerd.io/exported: "true"
C. multicluster.linkerd.io/export: "enabled"
D. linkerd.io/multicluster: "export"

<details>
<summary>정답 및 설명</summary>

**정답: B. mirror.linkerd.io/exported: "true"**

**설명:**
서비스에 `mirror.linkerd.io/exported: "true"` 레이블을 추가하면 다른 연결된 클러스터에서 해당 서비스를 미러링합니다.

</details>

### 4. 미러 서비스의 이름 형식은?

A. `<service>.<cluster>`
B. `<service>-<cluster>`
C. `<cluster>-<service>`
D. `<service>@<cluster>`

<details>
<summary>정답 및 설명</summary>

**정답: B. `<service>-<cluster>`**

**설명:**
미러 서비스는 `<원본 서비스 이름>-<원본 클러스터 이름>` 형식으로 생성됩니다. 예: west 클러스터의 web 서비스는 east 클러스터에서 web-west로 미러됩니다.

</details>

### 5. `linkerd multicluster link` 명령어의 역할은?

A. 두 클러스터의 네트워크 연결
B. 원격 클러스터 자격 증명을 로컬에 등록
C. 서비스 간 트래픽 라우팅 설정
D. 인증서 교환

<details>
<summary>정답 및 설명</summary>

**정답: B. 원격 클러스터 자격 증명을 로컬에 등록**

**설명:**
`linkerd multicluster link --cluster-name <name>`은 현재 클러스터의 자격 증명(게이트웨이 주소, 서비스 계정 토큰 등)을 생성하여 다른 클러스터에 등록할 수 있게 합니다.

</details>

### 6. 다중 클러스터 게이트웨이의 상태를 확인하는 명령어는?

A. `linkerd multicluster status`
B. `linkerd multicluster gateways`
C. `linkerd multicluster check`
D. `kubectl get gateway`

<details>
<summary>정답 및 설명</summary>

**정답: B. `linkerd multicluster gateways`**

**설명:**
`linkerd multicluster gateways`는 연결된 클러스터의 게이트웨이 상태를 보여줍니다. ALIVE, NUM_SVC(미러 서비스 수), LATENCY를 확인할 수 있습니다.

</details>

### 7. EKS 다중 클러스터에서 게이트웨이에 권장되는 설정은?

A. ClusterIP 서비스
B. NodePort 서비스
C. NLB (Network Load Balancer)
D. ALB (Application Load Balancer)

<details>
<summary>정답 및 설명</summary>

**정답: C. NLB (Network Load Balancer)**

**설명:**
EKS에서 다중 클러스터 게이트웨이는 NLB를 권장합니다. TCP/TLS 트래픽에 최적화되어 있으며, `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` 어노테이션으로 설정합니다.

</details>

### 8. TrafficSplit으로 로컬과 원격 클러스터 간 트래픽 분할 시 백엔드 서비스는?

A. 로컬 서비스와 원격 게이트웨이
B. 로컬 서비스와 미러 서비스
C. 로컬 서비스만
D. 원격 서비스 직접 참조

<details>
<summary>정답 및 설명</summary>

**정답: B. 로컬 서비스와 미러 서비스**

**설명:**
TrafficSplit 백엔드에 로컬 서비스(예: web)와 미러 서비스(예: web-west)를 지정합니다. 미러 서비스로 가는 트래픽은 자동으로 원격 클러스터의 게이트웨이로 라우팅됩니다.

</details>

### 9. 다중 클러스터 환경에서 미러 컨트롤러의 역할이 아닌 것은?

A. 원격 서비스 감시
B. 미러 서비스 생성/업데이트
C. 인증서 발급
D. 엔드포인트 동기화

<details>
<summary>정답 및 설명</summary>

**정답: C. 인증서 발급**

**설명:**
서비스 미러 컨트롤러는 원격 클러스터의 내보낸 서비스를 감시하고, 로컬에 미러 서비스를 생성/업데이트하고, 엔드포인트를 동기화합니다. 인증서 발급은 Identity Controller의 역할입니다.

</details>

### 10. 두 EKS 클러스터 간 프라이빗 연결을 위한 AWS 서비스는?

A. Direct Connect만
B. VPC Peering 또는 Transit Gateway
C. Route 53만
D. CloudFront

<details>
<summary>정답 및 설명</summary>

**정답: B. VPC Peering 또는 Transit Gateway**

**설명:**
EKS 클러스터 간 프라이빗 연결을 위해 VPC Peering(두 VPC 직접 연결) 또는 Transit Gateway(허브 앤 스포크 모델)를 사용합니다. 게이트웨이는 internal NLB로 설정합니다.

</details>

### 11. 다중 클러스터 환경에서 특정 원격 서비스만 접근을 허용하는 방법은?

A. NetworkPolicy
B. ServerAuthorization with SPIFFE ID
C. AWS Security Group
D. Kubernetes RBAC

<details>
<summary>정답 및 설명</summary>

**정답: B. ServerAuthorization with SPIFFE ID**

**설명:**
ServerAuthorization의 meshTLS.identities에 원격 클러스터의 특정 SPIFFE ID를 지정하여 접근을 제어합니다. 예: `spiffe://root.linkerd.cluster.local/ns/production/sa/api-gateway`

</details>

### 12. `linkerd multicluster check` 명령어가 확인하지 않는 것은?

A. Link 리소스 상태
B. 게이트웨이 연결
C. 애플리케이션 비즈니스 로직
D. 서비스 미러 컨트롤러 상태

<details>
<summary>정답 및 설명</summary>

**정답: C. 애플리케이션 비즈니스 로직**

**설명:**
`linkerd multicluster check`는 Link 리소스, 게이트웨이, 서비스 미러 컨트롤러, 인증서 등 다중 클러스터 인프라 상태를 확인합니다. 애플리케이션 로직은 확인하지 않습니다.

</details>
