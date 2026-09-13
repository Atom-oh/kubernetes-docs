# Linkerd 설치 퀴즈

2026년 9월 11일 edge-26.9.1·chart 2026.9.1 기준으로 검토했습니다. 전체 전제와 검증 경계는 [설치 가이드](../../../service-mesh/linkerd/01-installation.md)를 확인하세요.

### 1. 이 가이드의 정확한 공개 CLI를 어떻게 확보하나요?

A. linkerd라는 package는 모두 같은 버전이라고 가정한다

B. OS/architecture에 맞는 공식 edge-26.9.1 asset을 선택하고 checksum·client version을 확인한다

C. kubectl install linkerd를 사용한다

D. 해석하지 않는 installer에 --version stable-2.16.0을 넘긴다

<details>
<summary>정답 및 설명</summary>

**정답: B**

공식 릴리스 asset을 고정합니다. Installer 대안은 LINKERD2_VERSION을 사용하며 기존 install script는 deprecated이고 현재 edge가 기본입니다. Stable 배포판은 vendor 안내를 따릅니다. Windows asset은 windows.exe이며 windows-amd64.exe라는 이름을 만들면 안 됩니다.

</details>

### 2. 신규 설치의 사전 검사는 어느 명령인가요?

A. linkerd check

B. linkerd check --pre

C. linkerd verify

D. linkerd install --dry-run

<details>
<summary>정답 및 설명</summary>

**정답: B**

check --pre는 API 접근, Kubernetes 최소 버전, Gateway API 전제와 설치 권한·설정을 확인합니다. 이후 모든 Kubernetes 호환성의 증거는 아닙니다. 정확한 matrix를 검토하고 CNI 설치 경로라면 해당 flag를 사용하세요.

</details>

### 3. 수동 Helm 경로에 필요한 identity 자료는?

A. Envoy image

B. 공개 trust anchor와 issuer 인증서·개인 키 또는 지원되는 issuer-secret 통합

C. 모든 proxy Pod 안의 root CA 개인 키

D. Prometheus 설정 파일

<details>
<summary>정답 및 설명</summary>

**정답: B**

이 경로에서 control-plane Helm chart는 workload identity CA 자료를 생성하지 않습니다. 공개 trust anchor와 issuer 서명 credential을 제공하고 root 개인 키는 Kubernetes 밖에 보관하세요. External issuer-secret 통합은 해당 scheme·소유 구성이 필요합니다.

</details>

### 4. 포함된 HA profile은 핵심 control-plane 구성 요소에 몇 개 replica를 선택하나요?

A. 1개

B. 2개

C. 3개

D. 5개

<details>
<summary>정답 및 설명</summary>

**정답: C**

HA profile은 핵심 replica 3개, node anti-affinity, PDB와 injection webhook Fail 정책을 설정합니다. 중복 serving instance이며 quorum 투표자가 아닙니다. 대상 node·resource와 유효한 credential·network가 필요하고 replica 수만으로 가용성이 보장되지 않습니다.

</details>

### 5. Viz의 주요 기능이 아닌 것은?

A. Web dashboard

B. Prometheus 기반 metric

C. 자동 canary 승격

D. HTTP traffic tap

<details>
<summary>정답 및 설명</summary>

**정답: C**

Viz는 metric/dashboard/tap을 제공합니다. Canary 진행에는 별도 배포 controller와 분석 정책이 필요합니다. 현재 chart는 외부 Grafana 링크를 제공하며 grafana.enabled로 내장 Grafana를 배포·비활성화하지 않습니다.

</details>

### 6. Linkerd mTLS를 종료하지 않고 gateway의 raw TCP를 유지할 수 있는 AWS load balancer는?

A. ALB HTTP listener

B. Dashboard Ingress resource

C. NLB TCP listener

D. Gateway Load Balancer GENEVE appliance 경로

<details>
<summary>정답 및 설명</summary>

**정답: C**

Linkerd gateway 전송에는 TCP passthrough를 사용합니다. NLB의 internal/internet-facing은 network 요구에 따른 scheme이며 별도의 load balancer 제품이 아닙니다. 가이드의 internal NLB 예시는 AWS Load Balancer Controller 소유와 원격 network·probe 연결을 전제합니다.

</details>

### 7. 문서화된 업그레이드 순서는?

A. Data plane 후 control plane과 CRD

B. Target CLI, CRD, control plane, 설치한 확장, data plane

C. CRD, data plane, control plane

D. CA 삭제 후 전체 재설치

<details>
<summary>정답 및 설명</summary>

**정답: B**

Target 호환성·release note와 현재 상태를 먼저 확인합니다. Trust credential을 유지하고 각 소유 도구로 갱신한 다음 의도한 앱 Pod를 재생성해 새 proxy를 받습니다. CLI 확장 update는 install로 render하며 viz upgrade는 하위 명령이 아닙니다. 지원 skew와 prune 삭제 내용을 확인하세요.

</details>

### 8. linkerd install --crds 명령 자체는 무엇을 하나요?

A. CLI binary 설치

B. Linkerd CRD manifest 생성

C. 모든 cluster resource 즉시 적용

D. 기존 모든 앱 Pod에 proxy 주입

<details>
<summary>정답 및 설명</summary>

**정답: B**

명령은 manifest를 출력합니다. 실제 설치는 kubectl apply나 선택한 배포 소유 도구가 수행합니다. Gateway API는 기본 Linkerd CRD 출력과 별도 전제이며 control plane은 이후 설치합니다.

</details>

### 9. edge-26.9.1의 tracing에는 어떤 접근이 맞나요?

A. 모든 확장이 CLI에 있으므로 linkerd jaeger install 실행

B. 지원 collector/backend, proxy tracing과 앱 context 전파 구성

C. Viz 설치만으로 모든 trace 저장 가정

D. Proxy가 앱 span을 모두 복원하므로 trace header 무시

<details>
<summary>정답 및 설명</summary>

**정답: B**

이 CLI에는 jaeger 하위 명령이 없고 공개 linkerd-jaeger chart 이력은 선택한 릴리스보다 오래되었습니다. 현재 tracing 경로와 receiver/export 호환성을 확인하세요. Metric/topology graph는 수집한 distributed trace와 같지 않습니다.

</details>

### 10. 완전한 제거 계획에서 먼저 해야 할 일은?

A. 앱 주입 상태를 유지한 채 CRD 삭제

B. 앱 injection·수동 proxy를 제거하고 재생성 결과를 검증한 뒤 확장·control plane 제거

C. 모든 namespace 즉시 삭제

D. 남은 주입 workload를 무시하도록 force uninstall

<details>
<summary>정답 및 설명</summary>

**정답: B**

Workload 소유 도구로 모든 주입 원인을 제거하고 앱 Pod를 재생성·검증한 뒤 설치한 확장과 control plane/CRD를 각 소유 도구로 제거합니다. CRD 삭제는 해당 custom resource를 지웁니다. Mesh 보안·라우팅 상실, CNI cleanup과 namespace 소유권도 별도로 검토하세요.

</details>

### 11. linkerd check가 검증하지 않는 것은?

A. Kubernetes API 접근

B. Control-plane 인증서 유효성

C. 애플리케이션 업무 로직

D. Control-plane Pod 상태

<details>
<summary>정답 및 설명</summary>

**정답: C**

Core 검사는 업무 결과나 모든 트래픽·보안 경로를 검증하지 않습니다. check --proxy가 해당 data-plane 검사를 추가하며 설치한 확장에는 자체 검사가 있습니다. 앱 테스트와 실제 트래픽 검증이 필요합니다.

</details>

### 12. 자동 proxy 주입을 요청하는 namespace annotation은?

A. linkerd.io/inject: enabled

B. linkerd.io/proxy: true

C. sidecar.linkerd.io/inject: true

D. linkerd/auto-inject: yes

<details>
<summary>정답 및 설명</summary>

**정답: A**

해당 annotation은 대상인 새 Pod의 주입을 요청합니다. Pod override, webhook 제외와 플랫폼 조건에 따라 달라져 모든 새 Pod의 주입을 보장하지 않습니다. 기존 Pod는 재생성이 필요하며 native sidecar는 initContainers에 있을 수 있습니다.

</details>
