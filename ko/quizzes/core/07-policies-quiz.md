# 정책 퀴즈

이 퀴즈는 Kubernetes의 정책 관련 개념인 리소스 쿼터, 리밋 레인지, 포드 보안 정책, 네트워크 정책 등에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes에서 ResourceQuota의 주요 목적은 무엇인가요?
   * A) 포드의 CPU 및 메모리 사용량 제한
   * B) 네임스페이스 내 리소스 생성 제한
   * C) 클러스터 전체의 리소스 사용량 모니터링
   * D) 노드의 리소스 할당 관리

<details>

<summary>정답 보기</summary>

**정답: B) 네임스페이스 내 리소스 생성 제한**

**설명:** ResourceQuota는 네임스페이스 내에서 생성할 수 있는 리소스의 총량을 제한합니다. 이는 CPU, 메모리와 같은 컴퓨팅 리소스뿐만 아니라 포드, 서비스, 컨피그맵 등의 오브젝트 수도 제한할 수 있습니다. ResourceQuota를 사용하면 한 팀이 클러스터의 모든 리소스를 독점하는 것을 방지할 수 있습니다.

</details>

2. LimitRange의 주요 기능은 무엇인가요?
   * A) 네임스페이스의 총 리소스 사용량 제한
   * B) 개별 컨테이너의 기본 리소스 요청 및 제한 설정
   * C) 클러스터 노드 간 리소스 분배
   * D) 포드 간 네트워크 통신 제한

<details>

<summary>정답 보기</summary>

**정답: B) 개별 컨테이너의 기본 리소스 요청 및 제한 설정**

**설명:** LimitRange는 네임스페이스 내에서 포드나 컨테이너에 대한 리소스 제약 조건을 정의합니다. 이를 통해 기본 리소스 요청 및 제한을 설정하거나, 최소/최대 리소스 사용량을 강제할 수 있습니다. LimitRange는 개별 리소스에 적용되는 반면, ResourceQuota는 네임스페이스 전체에 적용됩니다.

</details>

3. PodSecurityPolicy(PSP)가 Kubernetes v1.25에서 제거된 후, 이를 대체하는 메커니즘은 무엇인가요?
   * A) PodSecurityStandards
   * B) PodSecurityContext
   * C) PodSecurityAdmission
   * D) SecurityContextConstraints

<details>

<summary>정답 보기</summary>

**정답: C) PodSecurityAdmission**

**설명:** PodSecurityPolicy(PSP)는 Kubernetes v1.25에서 제거되었으며, 이를 대체하는 메커니즘은 PodSecurityAdmission입니다. 이는 Pod Security Standards를 기반으로 하는 내장 어드미션 컨트롤러로, Privileged, Baseline, Restricted의 세 가지 정책 수준을 제공합니다. PodSecurityContext는 포드 수준에서 보안 설정을 구성하는 데 사용되며, SecurityContextConstraints는 OpenShift에서 사용되는 유사한 메커니즘입니다.

</details>

4. NetworkPolicy를 사용하여 할 수 없는 것은 무엇인가요?
   * A) 특정 네임스페이스의 포드로만 트래픽 제한
   * B) 특정 IP CIDR 범위로만 트래픽 제한
   * C) 특정 포트로만 트래픽 제한
   * D) 특정 프로토콜의 페이로드 내용 검사

<details>

<summary>정답 보기</summary>

**정답: D) 특정 프로토콜의 페이로드 내용 검사**

**설명:** NetworkPolicy는 포드 간 통신을 제어하는 L3/L4 수준의 방화벽 정책을 제공합니다. 이를 통해 특정 네임스페이스, 레이블, IP CIDR 범위, 포트 등을 기반으로 트래픽을 제한할 수 있습니다. 그러나 NetworkPolicy는 L7 수준의 검사(예: HTTP 헤더, 페이로드 내용 등)를 수행할 수 없습니다. 이러한 기능이 필요한 경우 서비스 메시(예: Istio)나 API 게이트웨이를 사용해야 합니다.

</details>

5. Kubernetes에서 RBAC(Role-Based Access Control)의 주요 목적은 무엇인가요?
   * A) 포드 간 네트워크 통신 제어
   * B) 사용자 및 서비스 계정의 권한 관리
   * C) 리소스 사용량 제한
   * D) 포드 스케줄링 정책 설정

<details>

<summary>정답 보기</summary>

**정답: B) 사용자 및 서비스 계정의 권한 관리**

**설명:** RBAC(Role-Based Access Control)는 Kubernetes API에 대한 접근을 제어하는 메커니즘입니다. 이를 통해 사용자, 그룹 또는 서비스 계정이 클러스터 내에서 수행할 수 있는 작업을 정의할 수 있습니다. RBAC는 Role, ClusterRole, RoleBinding, ClusterRoleBinding 등의 리소스를 사용하여 권한을 관리합니다.

</details>

6. Kubernetes에서 Pod Security Standards의 세 가지 정책 수준 중 가장 제한적인 것은 무엇인가요?
   * A) Privileged
   * B) Baseline
   * C) Restricted
   * D) Enforced

<details>

<summary>정답 보기</summary>

**정답: C) Restricted**

**설명:** Pod Security Standards는 세 가지 정책 수준을 정의합니다:

* Privileged: 제한 없음, 모든 권한 허용
* Baseline: 알려진 권한 상승 경로 방지
* Restricted: 가장 제한적인 정책으로, 강화된 보안 설정 적용

Restricted 정책은 가장 제한적이며, 최소 권한 원칙을 따르고 보안 모범 사례를 적용합니다. 이 정책은 권한 있는 컨테이너, 호스트 네임스페이스 공유, 호스트 경로 마운트 등을 금지합니다.

</details>

7. Kubernetes에서 AdmissionController의 역할은 무엇인가요?
   * A) 사용자 인증
   * B) 리소스 사용량 모니터링
   * C) API 요청 검증 및 수정
   * D) 포드 스케줄링

<details>

<summary>정답 보기</summary>

**정답: C) API 요청 검증 및 수정**

**설명:** AdmissionController는 Kubernetes API 서버에 대한 요청이 인증 및 권한 부여를 통과한 후, 오브젝트가 영구 저장소에 저장되기 전에 요청을 가로채고 검증하거나 수정하는 플러그인입니다. 이를 통해 클러스터 관리자는 리소스 생성 및 수정에 대한 정책을 적용할 수 있습니다. 예를 들어, PodSecurityAdmission, ResourceQuota, LimitRanger 등이 AdmissionController로 구현되어 있습니다.

</details>

8. Kubernetes에서 OPA(Open Policy Agent) Gatekeeper의 주요 기능은 무엇인가요?
   * A) 클러스터 모니터링 및 로깅
   * B) 정책 기반 리소스 관리 및 검증
   * C) 자동 스케일링
   * D) 서비스 메시 관리

<details>

<summary>정답 보기</summary>

**정답: B) 정책 기반 리소스 관리 및 검증**

**설명:** OPA Gatekeeper는 Kubernetes 클러스터에 정책을 적용하기 위한 확장 가능한 솔루션입니다. 이는 OPA(Open Policy Agent)를 기반으로 하며, CustomResourceDefinition(CRD)을 사용하여 정책을 정의하고 적용합니다. Gatekeeper는 AdmissionWebhook으로 작동하여 클러스터에 생성되거나 수정되는 리소스가 정의된 정책을 준수하는지 확인합니다. 이를 통해 보안 정책, 리소스 제한, 네이밍 컨벤션 등 다양한 정책을 적용할 수 있습니다.

</details>

9. Kubernetes에서 ResourceQuota가 적용된 네임스페이스에서 리소스 요청(requests)과 제한(limits)을 지정하지 않은 포드를 생성하려고 할 때 어떤 일이 발생하나요?
   * A) 포드가 기본 리소스 요청과 제한으로 생성됨
   * B) 포드 생성이 거부됨
   * C) 포드가 생성되지만 스케줄링되지 않음
   * D) 포드가 생성되고 무제한 리소스를 사용할 수 있음

<details>

<summary>정답 보기</summary>

**정답: B) 포드 생성이 거부됨**

**설명:** ResourceQuota가 네임스페이스에 적용되고 CPU 및 메모리와 같은 컴퓨팅 리소스에 대한 쿼터가 설정된 경우, 해당 네임스페이스의 모든 컨테이너는 리소스 요청(requests)과 제한(limits)을 명시적으로 지정해야 합니다. 그렇지 않으면 API 서버는 포드 생성 요청을 거부합니다. 이는 쿼터가 적용된 네임스페이스에서 리소스 사용량을 정확하게 추적하고 제한하기 위한 것입니다.

</details>

10. Kubernetes에서 PriorityClass의 주요 목적은 무엇인가요?
    * A) 포드의 스케줄링 우선순위 정의
    * B) 네임스페이스의 리소스 할당 우선순위 설정
    * C) API 요청의 처리 우선순위 결정
    * D) 노드의 중요도 레벨 설정

<details>

<summary>정답 보기</summary>

### 주관식 문제

1. ResourceQuota와 LimitRange의 주요 차이점을 설명하세요.
2. Pod Security Standards의 세 가지 정책 수준(Privileged, Baseline, Restricted)과 각각의 특징을 설명하세요.
3. NetworkPolicy를 사용하여 특정 네임스페이스의 포드들이 다른 네임스페이스의 특정 포드와만 통신할 수 있도록 제한하는 방법을 설명하세요.
4. Kubernetes에서 OPA Gatekeeper를 사용하여 구현할 수 있는 세 가지 정책 예시를 설명하세요.
5. Kubernetes에서 PriorityClass를 사용하여 중요한 워크로드의 가용성을 보장하는 방법을 설명하세요.

</details>
