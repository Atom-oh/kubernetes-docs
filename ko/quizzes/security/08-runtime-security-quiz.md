# 런타임 보안 퀴즈

이 퀴즈는 Falco, Seccomp, AppArmor, eBPF 기반 보안, EKS 런타임 보안에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Falco가 런타임 위협을 탐지하는 데 사용하는 기술은?

A. 네트워크 패킷 분석
B. 시스템 호출(syscall) 모니터링
C. 로그 분석
D. 메모리 스캐닝

<details>
<summary>정답 보기</summary>

**정답: B. 시스템 호출(syscall) 모니터링**

**설명:**
Falco는 eBPF 또는 커널 모듈을 사용하여 커널 레벨에서 시스템 호출을 모니터링합니다. 프로세스 실행, 파일 접근, 네트워크 연결 등의 활동을 실시간으로 탐지합니다.

</details>

### 2. Seccomp의 주요 기능은?

A. 네트워크 트래픽 필터링
B. 프로세스가 호출할 수 있는 시스템 호출 제한
C. 파일 시스템 암호화
D. 사용자 인증

<details>
<summary>정답 보기</summary>

**정답: B. 프로세스가 호출할 수 있는 시스템 호출 제한**

**설명:**
Seccomp(Secure Computing Mode)은 프로세스가 호출할 수 있는 시스템 호출을 화이트리스트 방식으로 제한합니다. 허용되지 않은 syscall 호출 시 프로세스가 종료됩니다.

</details>

### 3. Kubernetes 1.27+에서 기본 Seccomp 프로파일로 권장되는 것은?

A. Unconfined
B. RuntimeDefault
C. Localhost
D. Docker/default

<details>
<summary>정답 보기</summary>

**정답: B. RuntimeDefault**

**설명:**
RuntimeDefault는 컨테이너 런타임(containerd, CRI-O)이 제공하는 기본 Seccomp 프로파일입니다:
```yaml
securityContext:
  seccompProfile:
    type: RuntimeDefault
```

대부분의 워크로드에 적합한 보안 수준을 제공합니다.

</details>

### 4. Falco 규칙에서 priority 필드의 역할은?

A. 규칙 실행 순서 결정
B. 알림의 심각도 수준 지정
C. 리소스 할당량 설정
D. 로그 보존 기간 설정

<details>
<summary>정답 보기</summary>

**정답: B. 알림의 심각도 수준 지정**

**설명:**
Falco 규칙의 priority는 탐지된 이벤트의 심각도를 지정합니다:
- EMERGENCY, ALERT, CRITICAL, ERROR
- WARNING, NOTICE, INFORMATIONAL, DEBUG

```yaml
- rule: Shell in Container
  priority: WARNING
```

</details>

### 5. AppArmor의 complain 모드에서 어떤 일이 발생하나요?

A. 모든 접근 차단
B. 정책 위반 시 로깅만 수행
C. 프로파일 비활성화
D. 알림만 전송

<details>
<summary>정답 보기</summary>

**정답: B. 정책 위반 시 로깅만 수행**

**설명:**
AppArmor 모드:
- **enforce**: 정책 위반 시 차단 및 로깅
- **complain**: 정책 위반 시 로깅만 (디버깅용)
- **unconfined**: 프로파일 미적용

complain 모드는 새 프로파일 테스트 시 유용합니다.

</details>

### 6. Amazon GuardDuty EKS Runtime Monitoring이 탐지하는 위협이 아닌 것은?

A. 암호화폐 채굴
B. 권한 상승
C. 코드 품질 문제
D. 컨테이너 탈출 시도

<details>
<summary>정답 보기</summary>

**정답: C. 코드 품질 문제**

**설명:**
GuardDuty EKS Runtime Monitoring 탐지 유형:
- PrivilegeEscalation (권한 상승)
- Execution (악성 코드 실행)
- CryptoCurrency (암호화폐 채굴)
- CredentialAccess (자격 증명 접근)
- DefenseEvasion (보안 우회)

코드 품질은 보안 위협이 아니라 개발 품질 문제입니다.

</details>

### 7. Cilium Tetragon의 주요 기능은?

A. 컨테이너 이미지 스캐닝
B. eBPF 기반 보안 관찰성
C. 네트워크 정책 관리
D. 시크릿 관리

<details>
<summary>정답 보기</summary>

**정답: B. eBPF 기반 보안 관찰성**

**설명:**
Tetragon은 Cilium의 eBPF 기반 보안 관찰성 도구입니다:
- 프로세스 실행 모니터링
- 네트워크 활동 추적
- 파일 접근 감시
- 정책 기반 실시간 대응 (예: 프로세스 종료)

</details>

### 8. Falco에서 컨테이너 내 셸 실행을 탐지하는 조건은?

A. container and shell_procs
B. spawned_process and container and shell_procs
C. exec and shell
D. process.name = bash

<details>
<summary>정답 보기</summary>

**정답: B. spawned_process and container and shell_procs**

**설명:**
Falco 규칙 예시:
```yaml
- rule: Shell in Container
  condition: >
    spawned_process and
    container and
    shell_procs
  output: "Shell spawned in container"
  priority: WARNING
```

`spawned_process`는 새 프로세스 생성, `container`는 컨테이너 환경, `shell_procs`는 셸 프로세스(bash, sh 등)를 의미합니다.

</details>

### 9. Pod의 읽기 전용 루트 파일시스템 설정 방법은?

A. readOnlyRootFilesystem: true
B. rootfs: readonly
C. filesystem.readonly: true
D. immutableRoot: true

<details>
<summary>정답 보기</summary>

**정답: A. readOnlyRootFilesystem: true**

**설명:**
```yaml
securityContext:
  readOnlyRootFilesystem: true
```

이 설정은 컨테이너의 루트 파일시스템을 읽기 전용으로 만들어 악성 코드가 파일을 수정하는 것을 방지합니다. 쓰기가 필요한 경로는 emptyDir 볼륨을 마운트합니다.

</details>

### 10. 런타임 보안에서 "Defense in Depth" 전략의 의미는?

A. 단일 보안 계층에 의존
B. 여러 보안 계층을 중첩하여 적용
C. 방어만 집중
D. 외부 경계만 보호

<details>
<summary>정답 보기</summary>

**정답: B. 여러 보안 계층을 중첩하여 적용**

**설명:**
Defense in Depth는 여러 보안 계층을 사용합니다:
1. 빌드 타임: 이미지 스캐닝, 취약점 분석
2. 배포 타임: Admission Control, PSS/PSA
3. 런타임: Falco, Seccomp, AppArmor

한 계층이 뚫려도 다른 계층이 보호합니다.

</details>

### 11. Hubble에서 정책에 의해 차단된 트래픽을 확인하는 명령은?

A. hubble observe --blocked
B. hubble observe --verdict DROPPED
C. hubble observe --denied
D. hubble observe --policy-violation

<details>
<summary>정답 보기</summary>

**정답: B. hubble observe --verdict DROPPED**

**설명:**
```bash
hubble observe --verdict DROPPED
```

`--verdict DROPPED`는 네트워크 정책에 의해 거부된 트래픽을 필터링합니다. 정책 위반을 실시간으로 모니터링하고 분석할 수 있습니다.

</details>

### 12. 런타임 보안 모범 사례가 아닌 것은?

A. 모든 워크로드에 RuntimeDefault Seccomp 적용
B. Falco를 모든 노드에 DaemonSet으로 배포
C. 컨테이너에 root로 실행
D. 읽기 전용 루트 파일시스템 사용

<details>
<summary>정답 보기</summary>

**정답: C. 컨테이너에 root로 실행**

**설명:**
런타임 보안 모범 사례:
- RuntimeDefault Seccomp 적용
- Falco 배포
- 읽기 전용 루트 파일시스템
- **비root 사용자로 실행** (runAsNonRoot: true)
- 불필요한 capabilities 제거
- GuardDuty 런타임 모니터링 활성화

root로 실행하면 컨테이너 탈출 시 호스트에 대한 권한이 높아져 위험합니다.

</details>
