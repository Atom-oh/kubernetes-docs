# Linkerd 설치 퀴즈

이 퀴즈는 Linkerd 설치 및 설정에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Linkerd CLI를 설치하는 올바른 명령어는 무엇입니까?

A. `apt-get install linkerd`
B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`
C. `kubectl install linkerd`
D. `helm install linkerd`

<details>
<summary>정답 및 설명</summary>

**정답: B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`**

**설명:**
Linkerd CLI는 공식 설치 스크립트를 통해 설치됩니다. 이 스크립트는 운영 체제를 감지하고 적절한 바이너리를 다운로드합니다. Homebrew(`brew install linkerd`)나 Chocolatey(`choco install linkerd2`)도 사용할 수 있지만, 공식 스크립트가 가장 일반적인 방법입니다.

</details>

### 2. Linkerd 설치 전 클러스터 요구사항을 확인하는 명령어는?

A. `linkerd check`
B. `linkerd check --pre`
C. `linkerd verify`
D. `linkerd install --dry-run`

<details>
<summary>정답 및 설명</summary>

**정답: B. `linkerd check --pre`**

**설명:**
`linkerd check --pre` 명령어는 Linkerd 설치 전 클러스터가 요구사항을 충족하는지 확인합니다. Kubernetes API 접근성, 버전 호환성, 필요한 권한 등을 검증합니다. 설치 후에는 `linkerd check`로 전체 상태를 확인합니다.

</details>

### 3. Helm으로 Linkerd를 설치할 때 반드시 직접 제공해야 하는 것은?

A. Envoy 프록시 이미지
B. Trust Anchor와 Identity Issuer 인증서
C. Prometheus 설정 파일
D. Kubernetes 버전 정보

<details>
<summary>정답 및 설명</summary>

**정답: B. Trust Anchor와 Identity Issuer 인증서**

**설명:**
CLI 설치와 달리 Helm 설치는 인증서를 자동 생성하지 않습니다. 사용자가 Trust Anchor(Root CA)와 Identity Issuer(Intermediate CA) 인증서를 직접 생성하고 제공해야 합니다. 이는 프로덕션 환경에서 인증서 관리를 더 잘 제어할 수 있게 해줍니다.

</details>

### 4. Linkerd HA(고가용성) 설치를 위한 권장 컨트롤 플레인 복제본 수는?

A. 1개
B. 2개
C. 3개
D. 5개

<details>
<summary>정답 및 설명</summary>

**정답: C. 3개**

**설명:**
HA 구성에서는 Destination, Identity, Proxy Injector 각각 3개의 복제본을 권장합니다. 3개의 복제본은 1개가 실패해도 쿼럼을 유지할 수 있으며, 롤링 업데이트 시에도 가용성을 보장합니다.

</details>

### 5. Viz 확장의 주요 기능이 아닌 것은?

A. 웹 대시보드
B. Prometheus 메트릭 수집
C. 자동 카나리 배포
D. 실시간 트래픽 탭(Tap)

<details>
<summary>정답 및 설명</summary>

**정답: C. 자동 카나리 배포**

**설명:**
Viz 확장은 웹 대시보드, Prometheus 기반 메트릭 수집, Grafana 대시보드, 실시간 트래픽 탭 기능을 제공합니다. 자동 카나리 배포는 Flagger와 같은 별도 도구를 통해 구현됩니다.

</details>

### 6. EKS에서 Multicluster 게이트웨이에 권장되는 로드밸런서 유형은?

A. Classic Load Balancer
B. Application Load Balancer (ALB)
C. Network Load Balancer (NLB)
D. Internal Load Balancer

<details>
<summary>정답 및 설명</summary>

**정답: C. Network Load Balancer (NLB)**

**설명:**
NLB는 TCP/TLS 트래픽에 최적화되어 있어 Linkerd의 mTLS 게이트웨이 트래픽에 적합합니다. ALB는 HTTP/HTTPS에 최적화되어 있고, Linkerd 게이트웨이는 TCP 레벨에서 동작하므로 NLB가 권장됩니다.

</details>

### 7. Linkerd 업그레이드 시 올바른 순서는?

A. 데이터 플레인 → CRD → 컨트롤 플레인
B. CRD → 컨트롤 플레인 → 데이터 플레인
C. 컨트롤 플레인 → CRD → 데이터 플레인
D. CRD → 데이터 플레인 → 컨트롤 플레인

<details>
<summary>정답 및 설명</summary>

**정답: B. CRD → 컨트롤 플레인 → 데이터 플레인**

**설명:**
올바른 업그레이드 순서는: 1) CLI 업그레이드, 2) CRD 업그레이드, 3) 컨트롤 플레인 업그레이드, 4) 데이터 플레인(프록시) 업그레이드입니다. CRD를 먼저 업그레이드해야 새 API 버전을 사용할 수 있습니다.

</details>

### 8. `linkerd install --crds` 명령어의 목적은?

A. Linkerd CLI 설치
B. Custom Resource Definitions 설치
C. 인증서 생성
D. 프록시 주입

<details>
<summary>정답 및 설명</summary>

**정답: B. Custom Resource Definitions 설치**

**설명:**
`linkerd install --crds`는 Linkerd가 사용하는 CRD(Custom Resource Definitions)만 설치합니다. ServiceProfile, Server, ServerAuthorization 등의 CRD가 포함됩니다. 컨트롤 플레인은 별도로 `linkerd install`로 설치합니다.

</details>

### 9. Jaeger 확장 설치 명령어는?

A. `linkerd install jaeger`
B. `linkerd jaeger install | kubectl apply -f -`
C. `kubectl apply -f jaeger.yaml`
D. `helm install jaeger linkerd/jaeger`

<details>
<summary>정답 및 설명</summary>

**정답: B. `linkerd jaeger install | kubectl apply -f -`**

**설명:**
Linkerd 확장은 `linkerd <extension> install` 형식으로 매니페스트를 생성하고 kubectl로 적용합니다. Jaeger 확장은 분산 추적 기능을 제공합니다.

</details>

### 10. Linkerd를 완전히 제거하기 위한 올바른 순서는?

A. 컨트롤 플레인 → 확장 → CRD
B. 확장 → 컨트롤 플레인 → CRD
C. CRD → 컨트롤 플레인 → 확장
D. 모두 동시에 제거 가능

<details>
<summary>정답 및 설명</summary>

**정답: B. 확장 → 컨트롤 플레인 → CRD**

**설명:**
제거 순서는 설치의 역순입니다: 1) Viz, Jaeger, Multicluster 등 확장 제거, 2) 컨트롤 플레인 제거, 3) CRD 제거. 확장이 컨트롤 플레인에 의존하고, 컨트롤 플레인이 CRD에 의존하기 때문입니다.

</details>

### 11. `linkerd check` 명령어가 확인하지 않는 것은?

A. Kubernetes API 연결
B. 인증서 유효성
C. 애플리케이션 비즈니스 로직
D. 컨트롤 플레인 Pod 상태

<details>
<summary>정답 및 설명</summary>

**정답: C. 애플리케이션 비즈니스 로직**

**설명:**
`linkerd check`는 Linkerd 인프라 상태만 확인합니다: Kubernetes API 연결, 인증서 유효성, 컨트롤 플레인 Pod 상태, 프록시 상태 등. 애플리케이션의 비즈니스 로직이나 기능은 확인하지 않습니다.

</details>

### 12. 프록시 자동 주입을 위해 네임스페이스에 추가해야 하는 어노테이션은?

A. `linkerd.io/inject: enabled`
B. `linkerd.io/proxy: true`
C. `sidecar.linkerd.io/inject: true`
D. `linkerd/auto-inject: yes`

<details>
<summary>정답 및 설명</summary>

**정답: A. `linkerd.io/inject: enabled`**

**설명:**
네임스페이스에 `linkerd.io/inject: enabled` 어노테이션을 추가하면 해당 네임스페이스의 모든 새 Pod에 자동으로 linkerd-proxy가 주입됩니다. 개별 Pod에도 같은 어노테이션을 사용할 수 있습니다.

</details>
