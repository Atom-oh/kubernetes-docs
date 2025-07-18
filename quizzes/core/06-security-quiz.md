# 보안 퀴즈

이 퀴즈는 Kubernetes의 보안 관련 개념인 인증, 인가, 네트워크 정책, 보안 컨텍스트, 시크릿 관리 등에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes에서 사용자 인증을 위해 지원하는 방식이 아닌 것은 무엇인가요?
   - A) X.509 인증서
   - B) 서비스 계정 토큰
   - C) OAuth 토큰
   - D) 내장 사용자 데이터베이스
   
<details>
<summary>정답 보기</summary>

**정답: D) 내장 사용자 데이터베이스**

**설명:**
Kubernetes는 내장 사용자 데이터베이스를 제공하지 않습니다. 대신 X.509 인증서, 서비스 계정 토큰, OAuth 토큰, OpenID Connect 토큰, 웹훅 토큰 인증 등의 인증 방식을 지원합니다. 사용자 관리는 일반적으로 외부 시스템(예: LDAP, Active Directory)과 통합하여 수행합니다.
</details>

2. Kubernetes에서 RBAC(Role-Based Access Control)의 주요 구성 요소가 아닌 것은 무엇인가요?
   - A) Role
   - B) ClusterRole
   - C) RoleBinding
   - D) SecurityPolicy
   
<details>
<summary>정답 보기</summary>

**정답: D) SecurityPolicy**

**설명:**
Kubernetes RBAC의 주요 구성 요소는 Role, ClusterRole, RoleBinding, ClusterRoleBinding입니다. Role과 ClusterRole은 권한 집합을 정의하고, RoleBinding과 ClusterRoleBinding은 이러한 권한을 사용자, 그룹 또는 서비스 계정에 연결합니다. SecurityPolicy는 RBAC의 구성 요소가 아니며, 이와 유사한 리소스로는 PodSecurityPolicy(현재 deprecated) 또는 PodSecurityStandard가 있습니다.
</details>

3. Kubernetes에서 포드의 보안 컨텍스트(Security Context)를 통해 설정할 수 없는 것은 무엇인가요?
   - A) 컨테이너의 사용자 ID(UID)
   - B) 컨테이너의 그룹 ID(GID)
   - C) 컨테이너의 네트워크 정책
   - D) 컨테이너의 권한 상승 가능 여부
   
<details>
<summary>정답 보기</summary>

**정답: C) 컨테이너의 네트워크 정책**

**설명:**
보안 컨텍스트는 포드 또는 컨테이너 수준에서 권한 및 액세스 제어 설정을 정의합니다. 여기에는 사용자 ID(runAsUser), 그룹 ID(runAsGroup), 권한 상승 가능 여부(allowPrivilegeEscalation), 권한 있는 컨테이너(privileged), 기능(capabilities) 등이 포함됩니다. 그러나 네트워크 정책은 보안 컨텍스트가 아닌 별도의 NetworkPolicy 리소스를 통해 정의됩니다.
</details>

4. Kubernetes에서 서비스 계정(ServiceAccount)의 주요 목적은 무엇인가요?
   - A) 클러스터 외부 사용자의 인증
   - B) 포드가 API 서버와 통신할 때 사용하는 ID 제공
   - C) 노드 간 통신 암호화
   - D) 클러스터 관리자 권한 부여
   
<details>
<summary>정답 보기</summary>

**정답: B) 포드가 API 서버와 통신할 때 사용하는 ID 제공**

**설명:**
서비스 계정은 포드 내에서 실행되는 프로세스가 Kubernetes API 서버와 통신할 때 사용하는 ID를 제공합니다. 각 네임스페이스에는 기본 서비스 계정이 있으며, 포드는 명시적으로 지정하지 않으면 이 기본 서비스 계정을 사용합니다. 서비스 계정은 RBAC와 함께 사용하여 포드가 수행할 수 있는 작업을 제한할 수 있습니다.
</details>

5. Kubernetes에서 네트워크 정책(NetworkPolicy)의 주요 목적은 무엇인가요?
   - A) 클러스터 외부에서 내부로의 트래픽 라우팅
   - B) 포드 간 통신 제어 및 제한
   - C) 노드 간 통신 암호화
   - D) 서비스 디스커버리 제공
   
<details>
<summary>정답 보기</summary>

**정답: B) 포드 간 통신 제어 및 제한**

**설명:**
네트워크 정책은 포드 그룹 간의 통신을 제어하는 방법을 제공합니다. 이를 통해 어떤 포드가 어떤 포드와 통신할 수 있는지, 어떤 포트와 프로토콜을 사용할 수 있는지 등을 지정할 수 있습니다. 네트워크 정책은 마이크로서비스 아키텍처에서 서비스 간 통신을 세밀하게 제어하고 보안을 강화하는 데 중요합니다.
</details>

6. Kubernetes에서 포드 보안 표준(Pod Security Standards)의 세 가지 정책 수준 중 가장 제한적인 것은 무엇인가요?
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>정답 보기</summary>

**정답: C) Restricted**

**설명:**
포드 보안 표준은 세 가지 정책 수준을 정의합니다:
- Privileged: 제한 없음, 모든 권한 허용
- Baseline: 알려진 권한 상승 경로 방지
- Restricted: 가장 제한적인 정책으로, 강화된 보안 설정 적용

Restricted 정책은 가장 제한적이며, 최소 권한 원칙을 따르고 보안 모범 사례를 적용합니다. 이 정책은 권한 있는 컨테이너, 호스트 네임스페이스 공유, 호스트 경로 마운트 등을 금지합니다.
</details>

7. Kubernetes에서 Secret 데이터를 보호하기 위한 가장 효과적인 방법은 무엇인가요?
   - A) Base64로 인코딩
   - B) etcd 암호화 구성
   - C) 네임스페이스 분리
   - D) 레이블 추가
   
<details>
<summary>정답 보기</summary>

**정답: B) etcd 암호화 구성**

**설명:**
Kubernetes에서 Secret 데이터는 기본적으로 Base64로 인코딩되어 저장되지만, 이는 암호화가 아닌 단순한 인코딩입니다. etcd 암호화 구성을 사용하면 Secret 데이터가 etcd에 저장되기 전에 암호화되므로, etcd 데이터베이스에 대한 무단 접근으로부터 민감한 정보를 보호할 수 있습니다. 네임스페이스 분리와 레이블 추가는 접근 제어에 도움이 될 수 있지만, 데이터 자체를 보호하지는 않습니다.
</details>

8. Kubernetes에서 컨테이너 이미지 보안을 강화하기 위한 방법이 아닌 것은 무엇인가요?
   - A) 이미지 취약점 스캔
   - B) 신뢰할 수 있는 레지스트리 사용
   - C) 이미지 서명 및 검증
   - D) 컨테이너에 루트 권한 부여
   
<details>
<summary>정답 보기</summary>

**정답: D) 컨테이너에 루트 권한 부여**

**설명:**
컨테이너에 루트 권한을 부여하는 것은 보안을 약화시키는 방법입니다. 컨테이너 이미지 보안을 강화하기 위한 방법으로는 이미지 취약점 스캔, 신뢰할 수 있는 레지스트리 사용, 이미지 서명 및 검증, 최소 권한 원칙 적용, 불필요한 패키지 제거, 비루트 사용자로 컨테이너 실행 등이 있습니다.
</details>

9. Kubernetes에서 감사 로깅(Audit Logging)의 주요 목적은 무엇인가요?
   - A) 포드 로그 수집
   - B) API 서버 요청 기록
   - C) 노드 상태 모니터링
   - D) 네트워크 트래픽 분석
   
<details>
<summary>정답 보기</summary>

**정답: B) API 서버 요청 기록**

**설명:**
감사 로깅은 Kubernetes API 서버에 대한 요청을 기록하는 메커니즘입니다. 이를 통해 클러스터에서 누가 무엇을 했는지 추적할 수 있으며, 보안 사고 조사, 규정 준수 요구 사항 충족, 문제 해결 등에 유용합니다. 감사 로그는 요청의 시간, 사용자, 요청 내용, 응답 등의 정보를 포함할 수 있습니다.
</details>

10. Kubernetes에서 권한 있는(privileged) 컨테이너의 특징이 아닌 것은 무엇인가요?
    - A) 호스트의 모든 장치에 접근 가능
    - B) 호스트 네트워크 스택 사용 가능
    - C) 호스트 커널 모듈 로드 가능
    - D) 다른 네임스페이스의 리소스에 자동 접근 가능
    
<details>
<summary>정답 보기</summary>

**정답: D) 다른 네임스페이스의 리소스에 자동 접근 가능**

**설명:**
권한 있는 컨테이너는 호스트의 거의 모든 기능에 접근할 수 있지만, 다른 네임스페이스의 Kubernetes 리소스에 자동으로 접근할 수 있는 것은 아닙니다. 네임스페이스 간 접근은 RBAC 권한에 의해 제어됩니다. 권한 있는 컨테이너는 호스트의 장치, 네트워크 스택, 커널 모듈 등에 접근할 수 있어 보안 위험이 크므로, 꼭 필요한 경우에만 제한적으로 사용해야 합니다.
</details>
