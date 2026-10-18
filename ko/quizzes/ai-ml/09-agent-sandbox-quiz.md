# EKS에서 Agent Sandbox 운영하기 퀴즈

Agent Sandbox v1.0.6 API(`v1beta1`)와, 그 기본값이 Amazon EKS에서 어떻게 동작하는지 확인하는 퀴즈입니다. 관련 문서: [EKS에서 Agent Sandbox 운영하기](../../ai-ml/09-agent-sandbox.md).

## 객관식 문제

### 1. 신뢰할 수 없는 코드를 격리하기 위해 Agent Sandbox 자체가 제공하는 것은 무엇인가요?

- A. Sandbox마다 내장 microVM 하이퍼바이저
- B. Pod 오케스트레이션. 격리는 Pod의 `RuntimeClass`(예: gVisor, Kata Containers)가 담당
- C. `runc`를 어떤 신뢰할 수 없는 코드에도 안전하게 만드는 seccomp 프로필
- D. 전용 EC2 인스턴스 자동 배치

<details>
<summary>정답 보기</summary>

**정답: B. Pod 오케스트레이션. 격리는 Pod의 `RuntimeClass`(예: gVisor, Kata Containers)가 담당**

**설명:**
프로젝트는 스스로를 샌드박스 오케스트레이터라고 설명합니다. 위협 모델은 컨테이너 탈출에 대비해 `runtimeClassName`으로 고른 보안 런타임을 권장하며, 사용자가 빼지 못하도록 `SandboxTemplate`에 설정하라고 합니다. 기본 `runc`에서는 샌드박스 코드가 노드 커널을 공유합니다.

</details>

### 2. 템플릿에 `networkPolicy`가 없고 `networkPolicyManagement: Managed`를 유지했습니다. 생성되는 정책에 대한 설명으로 옳은 것은?

- A. CoreDNS를 포함해 모든 egress를 허용한다
- B. ingress는 `agent-sandbox-system`의 `sandbox-router` Pod만, egress는 사설 대역이 아닌 IPv4·IPv6 대역만 허용한다. CoreDNS는 허용하지 않는다
- C. 같은 네임스페이스의 모든 Pod에서 오는 ingress를 허용한다
- D. VPC CIDR로 가는 egress만 허용한다

<details>
<summary>정답 보기</summary>

**정답: B. ingress는 `agent-sandbox-system`의 `sandbox-router` Pod만, egress는 사설 대역이 아닌 IPv4·IPv6 대역만 허용한다. CoreDNS는 허용하지 않는다**

**설명:**
기본 정책은 `0.0.0.0/0`에서 `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`을, `::/0`에서 `fc00::/7`, `fe80::/10`을 제외합니다. CoreDNS 차단은 내부 서비스 탐색을 막기 위한 의도적인 동작이므로, 정책이나 Pod 리졸버를 바꾸기 전까지 공용 호스트 이름이 해석되지 않습니다.

</details>

### 3. IPv4 EKS 클러스터에서 예외를 추가하지 않아도 기본 관리형 정책 아래의 샌드박스가 여전히 도달할 수 있는 주소는?

- A. `169.254.169.254`의 IMDS
- B. `169.254.170.23`의 EKS Pod Identity Agent
- C. VPC CNI 커스텀 네트워킹에 쓰는 `100.64.0.0/10` 보조 CIDR의 Pod
- D. `10.0.12.34`의 Pod

<details>
<summary>정답 보기</summary>

**정답: C. VPC CNI 커스텀 네트워킹에 쓰는 `100.64.0.0/10` 보조 CIDR의 Pod**

**설명:**
기본 예외 목록은 RFC1918과 링크 로컬 대역만 다룹니다. `100.64.0.0/10`은 RFC1918이 아니므로 이 내부 주소들은 허용된 `0.0.0.0/0` 규칙에 해당합니다. IMDS와 Pod Identity Agent는 `169.254.0.0/16`에, `10.0.12.34`는 `10.0.0.0/8`에 속하므로 세 곳 모두 차단됩니다. IPv6 클러스터는 다릅니다. IPv4 규칙이 무시되고, VPC 글로벌 유니캐스트 주소는 제외되지 않으며, `ENABLE_V4_EGRESS`를 통한 IPv4 egress는 필터링되지 않습니다.

</details>

### 4. `agent-orchestrator` 네임스페이스의 에이전트 Pod가 SDK in-cluster 모드로, 관리형 정책 템플릿에서 만들어진 샌드박스 Pod에 직접 연결합니다. 어떻게 되나요?

- A. 클러스터 내부 트래픽은 필터링되지 않으므로 동작한다
- B. 템플릿 정책에 해당 네임스페이스용 ingress 규칙을 추가하기 전까지 차단된다(정책을 적용하는 CNI가 있을 때)
- C. IPv6에서만 동작한다
- D. SDK가 자동으로 공용 Gateway로 전환한다

<details>
<summary>정답 보기</summary>

**정답: B. 템플릿 정책에 해당 네임스페이스용 ingress 규칙을 추가하기 전까지 차단된다(정책을 적용하는 CNI가 있을 때)**

**설명:**
기본 ingress 규칙은 라우터만 허용합니다. Service DNS나 Pod IP로 직접 연결하면 라우터를 거치지 않으므로 명시적인 ingress 규칙이 필요합니다. EKS에서는 VPC CNI의 네트워크 정책 적용이 켜져 있다는 전제이며, 적용 엔진이 없으면 정책은 아무것도 막지 않습니다.

</details>

### 5. 웜 Sandbox를 입양하지 않고 콜드 스타트를 강제하는 `SandboxClaim` 필드는?

- A. `warmPoolRef`
- B. `lifecycle.shutdownTime`
- C. `env` 또는 `volumeClaimTemplates`
- D. `lifecycle.ttlSecondsAfterFinished`

<details>
<summary>정답 보기</summary>

**정답: C. `env` 또는 `volumeClaimTemplates`**

**설명:**
환경 변수와 볼륨은 Pod가 만들어지기 전에 정해져야 하는데, 웜 Pod는 이미 존재합니다. 둘 중 하나라도 설정한 Claim은 풀의 템플릿으로 콜드 생성됩니다. 템플릿도 이를 허용해야 하며, `envVarsInjectionPolicy`와 `volumeClaimTemplatesPolicy`는 모두 기본값이 `Disallowed`입니다.

</details>

### 6. 베어메탈 인스턴스 없이 EKS에서 Kata Containers를 쓰려고 합니다. 문서화된 기능에 맞는 방법은?

- A. EKS Auto Mode에 커스텀 containerd 런타임 추가
- B. Pod가 이미 VM에서 실행되고 관리형 NetworkPolicy도 적용되는 Fargate
- C. Karpenter v1.13.0 이상에서 M8i, C8i, R8i 같은 지원 패밀리에 `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled`를 설정하고, 그 노드에 묶인 RuntimeClass 사용
- D. 모든 Graviton 인스턴스는 중첩 가상화를 제공하므로 아무 Graviton 인스턴스나 사용

<details>
<summary>정답 보기</summary>

**정답: C. Karpenter v1.13.0 이상에서 M8i, C8i, R8i 같은 지원 패밀리에 `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled`를 설정하고, 그 노드에 묶인 RuntimeClass 사용**

**설명:**
EC2는 특정 Intel 패밀리(M7i/C7i/R7i, M8i/C8i/R8i 등)에서 중첩 가상화를 지원합니다. Karpenter는 `nested-virtualization`을 보고하는 인스턴스 유형만 고릅니다. Auto Mode는 AMI와 컨테이너 런타임을 AWS가 관리하므로 Kata를 추가할 수 없고, VPC CNI는 Fargate Pod에 네트워크 정책을 적용하지 못합니다. RuntimeClass에 `scheduling`을 두어 준비된 노드에만 배치되게 하세요.

</details>

### 7. `operatingMode`를 `Running`에서 `Suspended`로 바꾸면 Sandbox에 어떤 일이 일어나나요?

- A. Sandbox 객체, Pod, PVC가 모두 삭제된다
- B. Pod는 삭제되고 Sandbox 객체와 PVC는 남으며, `Suspended` 조건이 `PodTerminating`에서 `PodTerminated`로 바뀐다
- C. Pod가 같은 노드의 메모리에 동결된다
- D. 헤드리스 Service만 삭제된다

<details>
<summary>정답 보기</summary>

**정답: B. Pod는 삭제되고 Sandbox 객체와 PVC는 남으며, `Suspended` 조건이 `PodTerminating`에서 `PodTerminated`로 바뀐다**

**설명:**
일시 중지는 PVC 기반입니다. 컴퓨팅은 멈추고 스토리지는 남습니다. `Ready`는 사유 `SandboxSuspended`와 함께 False가 됩니다. EKS에서 EBS 볼륨은 AZ에 묶여 있으므로 재개된 Pod는 볼륨이 있는 가용 영역에 배치되어야 합니다.

</details>

### 8. Agent Sandbox v0.4.x를 운영 중인 클러스터를 v1.0.6으로 올리기 전에 해야 할 일은?

- A. 없음. v1.0.6을 `kubectl apply`하면 객체가 자동 변환된다
- B. v0.5.2 이상으로 올리고, 저장된 객체를 `v1beta1`로 마이그레이션한 뒤, 모든 CRD의 `status.storedVersions`에 `v1beta1`만 있는지 확인한다
- C. 모든 CRD를 삭제하고 다시 만든다
- D. v1.0.6에서 변환 웹훅을 다시 켠다

<details>
<summary>정답 보기</summary>

**정답: B. v0.5.2 이상으로 올리고, 저장된 객체를 `v1beta1`로 마이그레이션한 뒤, 모든 CRD의 `status.storedVersions`에 `v1beta1`만 있는지 확인한다**

**설명:**
v1.0.0에서 `v1alpha1`과 변환 웹훅이 제거되었고, v0.5.0 미만에서 바로 올리는 것은 지원되지 않습니다. `storedVersions`에 `v1alpha1`이 남아 있으면 API 서버가 업그레이드를 거부합니다. CRD를 삭제하면 모든 Sandbox, Claim, 템플릿, 풀이 연쇄 삭제됩니다.

</details>

### 9. `sandbox-router`를 통해 브라우저에서 샌드박스에 접근해야 합니다. 이 문서의 EKS 지침에 맞는 설계는?

- A. 인터넷에 노출된 NLB를 쓰는 `LoadBalancer` 타입 Service와 라우터 기본 `AllowAll` 권한 부여기
- B. CloudFront → CloudFront VPC origin → internal ALB → `sandbox-router-svc`. scoped-token v2 권한 부여와 ALB 또는 Envoy 계층의 속도 제한 적용
- C. 샌드박스 Pod마다 공인 IP
- D. 운영 환경에서도 사용자 노트북마다 port-forward

<details>
<summary>정답 보기</summary>

**정답: B. CloudFront → CloudFront VPC origin → internal ALB → `sandbox-router-svc`. scoped-token v2 권한 부여와 ALB 또는 Envoy 계층의 속도 제한 적용**

**설명:**
공개되는 것은 CloudFront뿐이고, ALB는 internal이며 보안 그룹은 CloudFront VPC origin 보안 그룹이나 관리형 접두사 목록만 허용합니다. 라우터의 기본 권한 부여기는 `AllowAll`이고, WebSocket 같은 업그레이드된 연결에 연결 제한을 두지 않으므로 노출 전에 권한 부여와 제한을 설정해야 합니다.

</details>

### 10. 이름이 70자이고 `spec.service: true`인 Sandbox에 v1.0.6은 어떤 변화를 주나요?

- A. 변화 없음. 이전처럼 동작한다
- B. CEL 규칙이 승인 단계에서 거부하며, 기존 객체는 `spec.service`를 해제하거나 63자 이하 이름으로 다시 만들기 전까지 모든 업데이트가 실패한다
- C. 컨트롤러가 Service 이름을 자동으로 잘라 준다
- D. Sandbox가 `v1alpha1`로 변환된다

<details>
<summary>정답 보기</summary>

**정답: B. CEL 규칙이 승인 단계에서 거부하며, 기존 객체는 `spec.service`를 해제하거나 63자 이하 이름으로 다시 만들기 전까지 모든 업데이트가 실패한다**

**설명:**
헤드리스 Service는 Sandbox 이름을 그대로 쓰고, Service 이름은 최대 63자의 DNS-1035 레이블이므로 이런 Sandbox는 원래 Ready가 될 수 없었습니다. v1.0.6은 이 실패를 승인 단계에서 알려 줍니다. 규칙이 객체 전체에 적용되고 기존 객체도 예외가 아니므로 상태 업데이트도 실패합니다.

</details>
