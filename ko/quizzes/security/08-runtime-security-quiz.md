# 런타임 보안 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

이 퀴즈는 Falco, Seccomp, AppArmor, eBPF 기반 보안, EKS 런타임 보안에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Falco가 런타임 위협을 탐지하는 데 사용하는 기술은?

- A. 네트워크 패킷 분석
- B. 시스템 호출(syscall) 모니터링
- C. 로그 분석
- D. 메모리 스캐닝

<details>
<summary>정답 보기</summary>

**정답: B. 시스템 호출(syscall) 모니터링**

**설명:**
Falco의 대표적인 Linux runtime 경로는 syscall 이벤트를 규칙으로 평가합니다. Plugin으로 다른 event source도 처리할 수 있습니다. 0.44.1의 container 필드는 container plugin이 제공하며, modern_ebpf driver의 커널·BTF 요구사항과 metadata 수집을 확인합니다.

</details>

### 2. Seccomp의 주요 기능은?

- A. 네트워크 트래픽 필터링
- B. 프로세스가 호출할 수 있는 시스템 호출 제한
- C. 파일 시스템 암호화
- D. 사용자 인증

<details>
<summary>정답 보기</summary>

**정답: B. 프로세스가 호출할 수 있는 시스템 호출 제한**

**설명:**
Seccomp는 syscall을 필터링합니다. 거부 action은 프로파일에 따라 ERRNO 반환·프로세스 종료·통지 등으로 달라지므로 항상 종료된다는 설명은 틀립니다.

</details>

### 3. Kubernetes 1.27+에서 기본 Seccomp 프로파일로 권장되는 것은?

- A. Unconfined
- B. RuntimeDefault
- C. Localhost
- D. Docker/default

<details>
<summary>정답 보기</summary>

**정답: B. RuntimeDefault**

**설명:**
RuntimeDefault는 container runtime이 제공하는 프로파일입니다. Pod/container의 seccompProfile에 명시하거나 kubelet seccompDefault 설정을 확인합니다. Kubernetes 1.27 이상이라는 사실만으로 모든 Pod에 자동 적용되지 않습니다.

</details>

### 4. Falco 규칙에서 priority 필드의 역할은?

- A. 규칙 실행 순서 결정
- B. 알림의 심각도 수준 지정
- C. 리소스 할당량 설정
- D. 로그 보존 기간 설정

<details>
<summary>정답 보기</summary>

**정답: B. 알림의 심각도 수준 지정**

**설명:**
priority는 이벤트 심각도이며 실행 순서가 아닙니다. Falco의 기본 체계는 EMERGENCY, ALERT, CRITICAL, ERROR, WARNING, NOTICE, INFORMATIONAL, DEBUG입니다. 규칙 전체에는 desc·condition·output 등도 필요합니다.

</details>

### 5. AppArmor의 complain 모드에서 어떤 일이 발생하나요?

- A. 모든 접근 차단
- B. 일반 위반은 기록하며, 명시적 deny는 차단 가능
- C. 프로파일 비활성화
- D. 알림만 전송

<details>
<summary>정답 보기</summary>

**정답: B. 일반 위반은 기록하며, 명시적 deny는 차단 가능**

**설명:**
complain 모드는 일반적인 정책 위반을 기록하면서 허용하지만 명시적 deny 규칙은 차단할 수 있습니다. 따라서 “모든 접근을 무조건 허용”하는 모드로 해석하지 않습니다. 지원 kernel과 실제 로드된 프로파일을 확인합니다.

</details>

### 6. Amazon GuardDuty EKS Runtime Monitoring이 탐지하는 위협이 아닌 것은?

- A. 암호화폐 채굴
- B. 권한 상승
- C. 코드 품질 문제
- D. 컨테이너 탈출 시도

<details>
<summary>정답 보기</summary>

**정답: C. 코드 품질 문제**

**설명:**
GuardDuty Runtime Monitoring은 보안 위협 탐지 기능이며 코드 품질 분석기가 아닙니다. 현재 EKS EC2·Auto Mode를 지원하지만 EKS Hybrid Nodes·EKS Fargate는 지원하지 않습니다. OS·kernel·agent·coverage health를 확인해야 합니다.

</details>

### 7. Cilium Tetragon의 주요 기능은?

- A. 컨테이너 이미지 스캐닝
- B. eBPF 기반 보안 관찰성
- C. 네트워크 정책 관리
- D. 시크릿 관리

<details>
<summary>정답 보기</summary>

**정답: B. eBPF 기반 보안 관찰성**

**설명:**
Tetragon은 process 실행, 파일·네트워크 hook 관찰과 지원되는 action을 제공합니다. Cilium CNI 설치가 필수라는 뜻은 아닙니다. 실제 hook 지원·selector 범위·오탐을 확인하고 Post/monitor 검증 뒤 강제를 검토합니다.

</details>

### 8. Falco에서 컨테이너 내 셸 실행을 탐지하는 조건은?

- A. container and shell_procs
- B. spawned_process and container and shell_procs
- C. exec and shell
- D. process.name = bash

<details>
<summary>정답 보기</summary>

**정답: B. spawned_process and container and shell_procs**

**설명:**
해당 식은 기본 ruleset의 spawned_process·container·shell_procs macro가 로드된 경우에 유효합니다. shell 실행 자체는 정상 작업일 수 있으며 침해를 확정하지 못합니다. 본문은 독립적으로 정의한 macro와 고유 규칙 이름을 사용합니다.

</details>

### 9. Pod의 읽기 전용 루트 파일시스템 설정 방법은?

- A. readOnlyRootFilesystem: true
- B. rootfs: readonly
- C. filesystem.readonly: true
- D. immutableRoot: true

<details>
<summary>정답 보기</summary>

**정답: A. readOnlyRootFilesystem: true**

**설명:**
readOnlyRootFilesystem은 container securityContext에 설정합니다. 쓰기가 필요한 볼륨·/tmp는 따로 제공할 수 있지만 writable volume·네트워크·메모리상의 악성 활동까지 방지하지 않습니다.

</details>

### 10. 런타임 보안에서 "Defense in Depth" 전략의 의미는?

- A. 단일 보안 계층에 의존
- B. 여러 보안 계층을 중첩하여 적용
- C. 방어만 집중
- D. 외부 경계만 보호

<details>
<summary>정답 보기</summary>

**정답: B. 여러 보안 계층을 중첩하여 적용**

**설명:**
여러 통제를 조합하되 각 계층의 범위와 실패를 검증합니다. 이미지/서명, admission·권한, seccomp/AppArmor, runtime 탐지, 네트워크와 복구 절차는 상호 보완적입니다. 도구를 늘리는 것만으로 보호가 보장되지 않습니다.

</details>

<span id="_11-hubble에서-정책에-의해-차단된-트래픽을-확인하는-명령은"></span>

### 11. Hubble에서 drop 이벤트를 필터링하는 명령은?

- A. hubble observe --blocked
- B. hubble observe --verdict DROPPED
- C. hubble observe --denied
- D. hubble observe --policy-violation

<details>
<summary>정답 보기</summary>

**정답: B. hubble observe --verdict DROPPED**

**설명:**
--verdict DROPPED는 drop 이벤트를 선택합니다. 모든 drop이 NetworkPolicy 거부는 아니므로 drop reason과 policy verdict를 함께 확인합니다. 원래 질문의 “정책에 의해 차단”이라는 범위는 이 옵션 하나로 확정하지 못합니다.

</details>

### 12. 런타임 보안 모범 사례가 아닌 것은?

- A. 호환성을 확인한 워크로드에 RuntimeDefault 적용
- B. 지원되는 노드에서 Falco 수집 상태 확인
- C. 컨테이너에 root로 실행
- D. 읽기 전용 루트 파일시스템 사용

<details>
<summary>정답 보기</summary>

**정답: C. 컨테이너에 root로 실행**

**설명:**
불필요한 root 권한은 줄입니다. RuntimeDefault·readOnlyRootFilesystem도 workload 요구와 node 지원을 확인해야 하며 Falco DaemonSet을 Fargate 등 모든 node 유형에 설치할 수 있는 것은 아닙니다. GuardDuty 활성화와 healthy coverage 역시 구분합니다.

</details>
