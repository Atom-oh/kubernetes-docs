# 정책 퀴즈

이 퀴즈는 Kubernetes의 정책 관련 개념인 리소스 쿼터, 리밋 레인지, 포드 보안 정책, 네트워크 정책 등에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes에서 ResourceQuota의 주요 목적은 무엇인가요?
   - A) 포드의 CPU 및 메모리 사용량 제한
   - B) 네임스페이스 내 리소스 생성 제한
   - C) 클러스터 전체의 리소스 사용량 모니터링
   - D) 노드의 리소스 할당 관리
   
<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스 내 리소스 생성 제한**

**설명:**
ResourceQuota는 네임스페이스 내에서 생성할 수 있는 리소스의 총량을 제한합니다. 이는 CPU, 메모리와 같은 컴퓨팅 리소스뿐만 아니라 포드, 서비스, 컨피그맵 등의 오브젝트 수도 제한할 수 있습니다. ResourceQuota를 사용하면 한 팀이 클러스터의 모든 리소스를 독점하는 것을 방지할 수 있습니다.
</details>

2. LimitRange의 주요 기능은 무엇인가요?
   - A) 네임스페이스의 총 리소스 사용량 제한
   - B) 개별 컨테이너의 기본 리소스 요청 및 제한 설정
   - C) 클러스터 노드 간 리소스 분배
   - D) 포드 간 네트워크 통신 제한
   
<details>
<summary>정답 보기</summary>

**정답: B) 개별 컨테이너의 기본 리소스 요청 및 제한 설정**

**설명:**
LimitRange는 네임스페이스 내에서 포드나 컨테이너에 대한 리소스 제약 조건을 정의합니다. 이를 통해 기본 리소스 요청 및 제한을 설정하거나, 최소/최대 리소스 사용량을 강제할 수 있습니다. LimitRange는 개별 리소스에 적용되는 반면, ResourceQuota는 네임스페이스 전체에 적용됩니다.
</details>

3. PodSecurityPolicy(PSP)가 Kubernetes v1.25에서 제거된 후, 이를 대체하는 메커니즘은 무엇인가요?
   - A) PodSecurityStandards
   - B) PodSecurityContext
   - C) PodSecurityAdmission
   - D) SecurityContextConstraints
   
<details>
<summary>정답 보기</summary>

**정답: C) PodSecurityAdmission**

**설명:**
PodSecurityPolicy(PSP)는 Kubernetes v1.25에서 제거되었으며, 이를 대체하는 메커니즘은 PodSecurityAdmission입니다. 이는 Pod Security Standards를 기반으로 하는 내장 어드미션 컨트롤러로, Privileged, Baseline, Restricted의 세 가지 정책 수준을 제공합니다. PodSecurityContext는 포드 수준에서 보안 설정을 구성하는 데 사용되며, SecurityContextConstraints는 OpenShift에서 사용되는 유사한 메커니즘입니다.
</details>

4. NetworkPolicy를 사용하여 할 수 없는 것은 무엇인가요?
   - A) 특정 네임스페이스의 포드로만 트래픽 제한
   - B) 특정 IP CIDR 범위로만 트래픽 제한
   - C) 특정 포트로만 트래픽 제한
   - D) 특정 프로토콜의 페이로드 내용 검사
   
<details>
<summary>정답 보기</summary>

**정답: D) 특정 프로토콜의 페이로드 내용 검사**

**설명:**
NetworkPolicy는 포드 간 통신을 제어하는 L3/L4 수준의 방화벽 정책을 제공합니다. 이를 통해 특정 네임스페이스, 레이블, IP CIDR 범위, 포트 등을 기반으로 트래픽을 제한할 수 있습니다. 그러나 NetworkPolicy는 L7 수준의 검사(예: HTTP 헤더, 페이로드 내용 등)를 수행할 수 없습니다. 이러한 기능이 필요한 경우 서비스 메시(예: Istio)나 API 게이트웨이를 사용해야 합니다.
</details>

5. Kubernetes에서 RBAC(Role-Based Access Control)의 주요 목적은 무엇인가요?
   - A) 포드 간 네트워크 통신 제어
   - B) 사용자 및 서비스 계정의 권한 관리
   - C) 리소스 사용량 제한
   - D) 포드 스케줄링 정책 설정
   
<details>
<summary>정답 보기</summary>

**정답: B) 사용자 및 서비스 계정의 권한 관리**

**설명:**
RBAC(Role-Based Access Control)는 Kubernetes API에 대한 접근을 제어하는 메커니즘입니다. 이를 통해 사용자, 그룹 또는 서비스 계정이 클러스터 내에서 수행할 수 있는 작업을 정의할 수 있습니다. RBAC는 Role, ClusterRole, RoleBinding, ClusterRoleBinding 등의 리소스를 사용하여 권한을 관리합니다.
</details>

6. Kubernetes에서 Pod Security Standards의 세 가지 정책 수준 중 가장 제한적인 것은 무엇인가요?
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>정답 보기</summary>

**정답: C) Restricted**

**설명:**
Pod Security Standards는 세 가지 정책 수준을 정의합니다:
- Privileged: 제한 없음, 모든 권한 허용
- Baseline: 알려진 권한 상승 경로 방지
- Restricted: 가장 제한적인 정책으로, 강화된 보안 설정 적용

Restricted 정책은 가장 제한적이며, 최소 권한 원칙을 따르고 보안 모범 사례를 적용합니다. 이 정책은 권한 있는 컨테이너, 호스트 네임스페이스 공유, 호스트 경로 마운트 등을 금지합니다.
</details>

7. Kubernetes에서 AdmissionController의 역할은 무엇인가요?
   - A) 사용자 인증
   - B) 리소스 사용량 모니터링
   - C) API 요청 검증 및 수정
   - D) 포드 스케줄링
   
<details>
<summary>정답 보기</summary>

**정답: C) API 요청 검증 및 수정**

**설명:**
AdmissionController는 Kubernetes API 서버에 대한 요청이 인증 및 권한 부여를 통과한 후, 오브젝트가 영구 저장소에 저장되기 전에 요청을 가로채고 검증하거나 수정하는 플러그인입니다. 이를 통해 클러스터 관리자는 리소스 생성 및 수정에 대한 정책을 적용할 수 있습니다. 예를 들어, PodSecurityAdmission, ResourceQuota, LimitRanger 등이 AdmissionController로 구현되어 있습니다.
</details>

8. Kubernetes에서 OPA(Open Policy Agent) Gatekeeper의 주요 기능은 무엇인가요?
   - A) 클러스터 모니터링 및 로깅
   - B) 정책 기반 리소스 관리 및 검증
   - C) 자동 스케일링
   - D) 서비스 메시 관리
   
<details>
<summary>정답 보기</summary>

**정답: B) 정책 기반 리소스 관리 및 검증**

**설명:**
OPA Gatekeeper는 Kubernetes 클러스터에 정책을 적용하기 위한 확장 가능한 솔루션입니다. 이는 OPA(Open Policy Agent)를 기반으로 하며, CustomResourceDefinition(CRD)을 사용하여 정책을 정의하고 적용합니다. Gatekeeper는 AdmissionWebhook으로 작동하여 클러스터에 생성되거나 수정되는 리소스가 정의된 정책을 준수하는지 확인합니다. 이를 통해 보안 정책, 리소스 제한, 네이밍 컨벤션 등 다양한 정책을 적용할 수 있습니다.
</details>

9. Kubernetes에서 ResourceQuota가 적용된 네임스페이스에서 리소스 요청(requests)과 제한(limits)을 지정하지 않은 포드를 생성하려고 할 때 어떤 일이 발생하나요?
   - A) 포드가 기본 리소스 요청과 제한으로 생성됨
   - B) 포드 생성이 거부됨
   - C) 포드가 생성되지만 스케줄링되지 않음
   - D) 포드가 생성되고 무제한 리소스를 사용할 수 있음
   
<details>
<summary>정답 보기</summary>

**정답: B) 포드 생성이 거부됨**

**설명:**
ResourceQuota가 네임스페이스에 적용되고 CPU 및 메모리와 같은 컴퓨팅 리소스에 대한 쿼터가 설정된 경우, 해당 네임스페이스의 모든 컨테이너는 리소스 요청(requests)과 제한(limits)을 명시적으로 지정해야 합니다. 그렇지 않으면 API 서버는 포드 생성 요청을 거부합니다. 이는 쿼터가 적용된 네임스페이스에서 리소스 사용량을 정확하게 추적하고 제한하기 위한 것입니다.
</details>

10. Kubernetes에서 PriorityClass의 주요 목적은 무엇인가요?
    - A) 포드의 스케줄링 우선순위 정의
    - B) 네임스페이스의 리소스 할당 우선순위 설정
    - C) API 요청의 처리 우선순위 결정
    - D) 노드의 중요도 레벨 설정
    
<details>
<summary>정답 보기</summary>

## 주관식 문제

1. ResourceQuota와 LimitRange의 주요 차이점을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
ResourceQuota는 네임스페이스 전체에 대한 리소스 사용량을 제한하는 반면, LimitRange는 네임스페이스 내의 개별 컨테이너나 포드에 대한 리소스 제약 조건을 설정합니다.

주요 차이점:
1. **적용 범위**: ResourceQuota는 네임스페이스 전체에 적용되고, LimitRange는 개별 리소스(포드, 컨테이너 등)에 적용됩니다.
2. **목적**: ResourceQuota는 네임스페이스의 총 리소스 사용량을 제한하는 반면, LimitRange는 기본값 설정, 최소/최대 제한 등을 통해 개별 리소스의 사용량을 제어합니다.
3. **강제성**: ResourceQuota가 설정된 경우 쿼터를 초과하는 리소스 생성이 거부되며, LimitRange는 리소스 생성 시 기본값을 적용하거나 제한을 초과하는 경우 거부합니다.
4. **리소스 종류**: ResourceQuota는 CPU, 메모리뿐만 아니라 포드, 서비스, PVC 등의 오브젝트 수도 제한할 수 있지만, LimitRange는 주로 CPU, 메모리, 스토리지와 같은 컴퓨팅 리소스에 초점을 맞춥니다.
</details>

2. Pod Security Standards의 세 가지 정책 수준(Privileged, Baseline, Restricted)과 각각의 특징을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
Pod Security Standards는 포드의 보안 설정에 대한 세 가지 정책 수준을 정의합니다:

1. **Privileged (권한 있음)**:
   - 가장 개방적인 정책으로, 제한이 거의 없습니다.
   - 모든 권한 있는 작업을 허용합니다.
   - 호스트 네임스페이스, 호스트 포트, 권한 있는 컨테이너 등을 사용할 수 있습니다.
   - 개발 및 관리 작업에 적합하지만, 프로덕션 환경에서는 보안 위험이 큽니다.

2. **Baseline (기준선)**:
   - 중간 수준의 정책으로, 알려진 권한 상승 경로를 방지합니다.
   - 대부분의 워크로드에 적합한 기본 수준의 보안을 제공합니다.
   - 권한 있는 컨테이너, 호스트 네임스페이스 사용을 제한합니다.
   - 그러나 일부 권한 있는 작업(예: 호스트 경로 마운트)은 여전히 허용됩니다.

3. **Restricted (제한됨)**:
   - 가장 제한적인 정책으로, 강화된 보안 설정을 적용합니다.
   - 최소 권한 원칙을 따르며, 보안 모범 사례를 강제합니다.
   - 권한 있는 컨테이너, 호스트 네임스페이스, 호스트 경로 마운트, 권한 상승 등을 모두 금지합니다.
   - 루트가 아닌 사용자로 컨테이너를 실행하도록 강제합니다.
   - 보안이 중요한 프로덕션 워크로드에 적합합니다.
</details>

3. NetworkPolicy를 사용하여 특정 네임스페이스의 포드들이 다른 네임스페이스의 특정 포드와만 통신할 수 있도록 제한하는 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
NetworkPolicy를 사용하여 특정 네임스페이스의 포드들이 다른 네임스페이스의 특정 포드와만 통신하도록 제한하려면 다음과 같은 방법을 사용할 수 있습니다:

1. **소스 네임스페이스에 NetworkPolicy 적용**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-specific-communication
  namespace: source-namespace  # 소스 네임스페이스
spec:
  podSelector: {}  # 모든 포드에 적용
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: destination-namespace  # 대상 네임스페이스의 레이블
      podSelector:
        matchLabels:
          app: specific-app  # 대상 포드의 레이블
```

2. **대상 네임스페이스에 NetworkPolicy 적용**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-specific-namespace
  namespace: destination-namespace  # 대상 네임스페이스
spec:
  podSelector:
    matchLabels:
      app: specific-app  # 대상 포드의 레이블
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: source-namespace  # 소스 네임스페이스의 레이블
```

이 방법을 사용하려면 네임스페이스에 적절한 레이블이 지정되어 있어야 합니다:
```bash
kubectl label namespace source-namespace name=source-namespace
kubectl label namespace destination-namespace name=destination-namespace
```

NetworkPolicy는 기본적으로 허용(allow-list) 방식으로 작동하므로, 위의 정책이 적용되면 명시적으로 허용된 통신만 가능하고 나머지는 모두 차단됩니다.
</details>

4. Kubernetes에서 OPA Gatekeeper를 사용하여 구현할 수 있는 세 가지 정책 예시를 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
OPA Gatekeeper를 사용하여 구현할 수 있는 정책 예시:

1. **이미지 레지스트리 제한**:
   - 승인된 레지스트리에서만 이미지를 가져오도록 강제하는 정책
   - 예: 회사 내부 레지스트리나 특정 신뢰할 수 있는 공개 레지스트리만 허용
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: allowed-repos
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/trusted-project/"
   ```

2. **리소스 요청 및 제한 강제**:
   - 모든 컨테이너에 리소스 요청과 제한이 설정되도록 강제하는 정책
   - 리소스 고갈 방지 및 적절한 리소스 할당 보장
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits-and-requests
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
       requests:
         - cpu
         - memory
   ```

3. **권한 있는 컨테이너 방지**:
   - 권한 있는 컨테이너 실행을 금지하는 정책
   - 보안 위험 감소 및 컨테이너 격리 보장
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: prevent-privileged-containers
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
   ```

4. **호스트 경로 마운트 제한**:
   - 호스트 파일 시스템 마운트를 제한하는 정책
   - 컨테이너 격리 보장 및 호스트 시스템 보호
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPHostFilesystem
   metadata:
     name: prevent-host-filesystem-mount
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       allowedHostPaths: []
   ```

5. **레이블 강제**:
   - 모든 리소스에 필수 레이블이 있도록 강제하는 정책
   - 리소스 관리 및 비용 할당 개선
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredLabels
   metadata:
     name: require-team-label
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod", "Service", "Deployment"]
     parameters:
       labels:
         - key: "team"
           allowedRegex: "^(frontend|backend|infra)$"
         - key: "environment"
           allowedRegex: "^(dev|staging|prod)$"
   ```

(위 중 세 가지만 설명하면 됩니다)
</details>

5. Kubernetes에서 PriorityClass를 사용하여 중요한 워크로드의 가용성을 보장하는 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
PriorityClass를 사용하여 중요한 워크로드의 가용성을 보장하는 방법:

1. **PriorityClass 정의**:
   - 중요도에 따라 다양한 우선순위 레벨의 PriorityClass 생성
   ```yaml
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000  # 높은 값일수록 높은 우선순위
   globalDefault: false
   description: "This priority class should be used for critical production workloads."
   ```

2. **중요한 워크로드에 PriorityClass 할당**:
   - 중요한 포드에 PriorityClass 참조 추가
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: critical-service
   spec:
     priorityClassName: high-priority
     containers:
     - name: app
       image: critical-service:latest
   ```

3. **선점(Preemption) 활용**:
   - 리소스가 부족할 때 우선순위가 높은 포드는 우선순위가 낮은 포드를 선점(제거)하고 스케줄링됨
   - 이를 통해 중요한 워크로드가 항상 실행될 수 있도록 보장

4. **시스템 우선순위 클래스 고려**:
   - Kubernetes는 system-cluster-critical(2000000000)과 system-node-critical(2000001000)과 같은 시스템 우선순위 클래스를 제공
   - 사용자 정의 우선순위 클래스는 일반적으로 이보다 낮은 값을 사용해야 함

5. **우선순위 계층 설계**:
   - 워크로드의 중요도에 따라 여러 우선순위 레벨 정의
   - 예: 프로덕션 서비스(900000), 내부 도구(500000), 개발/테스트(100000)

## 실습 문제

1. 다음 요구 사항에 맞는 ResourceQuota를 생성하세요:
   - 네임스페이스: team-a
   - 최대 10개의 포드
   - 최대 5개의 서비스
   - CPU 요청 총합: 4 코어
   - 메모리 요청 총합: 8Gi

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    pods: "10"
    services: "5"
    requests.cpu: "4"
    requests.memory: 8Gi
```

적용 방법:
```bash
# 네임스페이스 생성
kubectl create namespace team-a

# ResourceQuota 적용
kubectl apply -f team-a-quota.yaml
```

ResourceQuota 상태 확인:
```bash
kubectl describe resourcequota team-a-quota -n team-a
```
</details>

2. 다음 요구 사항에 맞는 LimitRange를 생성하세요:
   - 네임스페이스: team-b
   - 컨테이너 기본 요청: CPU 100m, 메모리 256Mi
   - 컨테이너 기본 제한: CPU 200m, 메모리 512Mi
   - 컨테이너 최대 제한: CPU 1 코어, 메모리 2Gi

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: team-b-limits
  namespace: team-b
spec:
  limits:
  - default:
      cpu: 200m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    max:
      cpu: "1"
      memory: 2Gi
    type: Container
```

적용 방법:
```bash
# 네임스페이스 생성
kubectl create namespace team-b

# LimitRange 적용
kubectl apply -f team-b-limits.yaml
```

LimitRange 상태 확인:
```bash
kubectl describe limitrange team-b-limits -n team-b
```
</details>

3. 다음 요구 사항에 맞는 NetworkPolicy를 생성하세요:
   - 네임스페이스: web
   - 앱 레이블이 'frontend'인 포드는 앱 레이블이 'backend'인 포드와만 통신 가능
   - 백엔드 포드는 포트 8080으로만 통신 허용

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-backend-only
  namespace: web
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend-only
  namespace: web
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

적용 방법:
```bash
# 네임스페이스 생성
kubectl create namespace web

# NetworkPolicy 적용
kubectl apply -f web-network-policies.yaml
```

NetworkPolicy 상태 확인:
```bash
kubectl describe networkpolicy -n web
```
</details>

4. 다음 요구 사항에 맞는 PriorityClass와 이를 사용하는 포드를 생성하세요:
   - PriorityClass 이름: high-priority
   - 우선순위 값: 100000
   - 설명: "중요한 프로덕션 워크로드용"
   - 포드 이름: critical-app
   - 이미지: nginx

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "중요한 프로덕션 워크로드용"
---
apiVersion: v1
kind: Pod
metadata:
  name: critical-app
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx
```

적용 방법:
```bash
kubectl apply -f high-priority-pod.yaml
```

PriorityClass 및 포드 상태 확인:
```bash
kubectl get priorityclass high-priority
kubectl get pod critical-app
```
</details>

5. 다음 요구 사항에 맞는 Pod Security 설정을 적용하세요:
   - 네임스페이스: restricted-ns
   - 모드: enforce
   - 레벨: restricted

<details>
<summary>정답 보기</summary>

**정답:**

Kubernetes 1.25 이상에서는 네임스페이스에 레이블을 추가하여 Pod Security Standards를 적용할 수 있습니다:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

적용 방법:
```bash
kubectl apply -f restricted-namespace.yaml
```

또는 기존 네임스페이스에 레이블 추가:
```bash
kubectl create namespace restricted-ns
kubectl label namespace restricted-ns \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

## 고급 주제

1. Kubernetes에서 OPA Gatekeeper와 Kyverno의 차이점과 각각의 장단점을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**OPA Gatekeeper와 Kyverno 비교:**

1. **아키텍처 및 접근 방식**:
   - **OPA Gatekeeper**: Open Policy Agent(OPA)를 기반으로 하며, Rego라는 정책 언어를 사용합니다. ConstraintTemplate과 Constraint라는 두 가지 CRD를 사용하여 정책을 정의합니다.
   - **Kyverno**: 자체 정책 엔진을 사용하며, YAML/JSON 기반의 정책 정의를 제공합니다. 단일 Policy CRD를 사용하여 정책을 정의합니다.

2. **정책 언어**:
   - **OPA Gatekeeper**: Rego 언어를 사용하며, 강력하지만 학습 곡선이 가파릅니다.
   - **Kyverno**: Kubernetes 리소스와 유사한 YAML 구문을 사용하여 정책을 정의하므로 Kubernetes 사용자에게 더 친숙합니다.

3. **기능**:
   - **OPA Gatekeeper**: 
     - 강력한 정책 언어로 복잡한 정책 표현 가능
     - 데이터 소스를 통합하여 외부 데이터 기반 결정 가능
     - 정책 라이브러리 및 재사용 가능한 템플릿 지원
   - **Kyverno**: 
     - 리소스 생성, 변경, 검증 기능 내장
     - 이미지 확인 및 변경 기능
     - 리소스 생성 시 자동으로 다른 리소스 생성 가능
     - 정책 예외 처리 기능

4. **장점**:
   - **OPA Gatekeeper**:
     - 더 성숙하고 널리 채택됨
     - 복잡한 정책 표현에 더 적합
     - 다양한 사용 사례에 대한 광범위한 문서 및 예제
     - Kubernetes 외부에서도 사용 가능한 OPA 생태계
   - **Kyverno**:
     - 더 쉬운 학습 곡선과 친숙한 YAML 구문
     - 별도의 정책 언어 학습 불필요
     - 리소스 생성 및 변경 기능 내장
     - 더 간단한 설정 및 구성

5. **단점**:
   - **OPA Gatekeeper**:
     - Rego 언어 학습 필요
     - 복잡한 설정 및 구성
     - 리소스 변경을 위해 추가 구성 필요
   - **Kyverno**:
     - 상대적으로 덜 성숙함
     - 매우 복잡한 정책 표현에 제한이 있을 수 있음
     - OPA에 비해 성능이 떨어질 수 있음

6. **선택 기준**:
   - **OPA Gatekeeper 선택 시**:
     - 복잡한 정책 로직이 필요한 경우
     - 이미 OPA를 사용하고 있거나 Rego에 익숙한 경우
     - 다양한 시스템에 걸쳐 일관된 정책 적용이 필요한 경우
   - **Kyverno 선택 시**:
     - 빠른 시작과 쉬운 학습 곡선이 중요한 경우
     - Kubernetes 리소스 구문에 익숙한 팀
     - 리소스 생성 및 변경 기능이 필요한 경우
     - 간단한 정책만 필요한 경우
</details>

2. Kubernetes에서 Pod Security Admission과 이전의 PodSecurityPolicy(PSP)의 주요 차이점을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Pod Security Admission과 PodSecurityPolicy(PSP) 비교:**

1. **구현 방식**:
   - **PodSecurityPolicy**: API 리소스(CRD)로 구현되었으며, 어드미션 컨트롤러를 통해 적용됩니다.
   - **Pod Security Admission**: 내장 어드미션 컨트롤러로 구현되어 있으며, 네임스페이스 레이블을 통해 구성됩니다.

2. **구성 방법**:
   - **PodSecurityPolicy**: 클러스터 관리자가 PSP 리소스를 생성하고 RBAC를 통해 사용자/서비스 계정에 바인딩해야 합니다.
   - **Pod Security Admission**: 네임스페이스에 레이블을 추가하여 적용 수준(enforce, audit, warn)과 정책 수준(privileged, baseline, restricted)을 지정합니다.

3. **정책 세분화**:
   - **PodSecurityPolicy**: 매우 세밀한 제어가 가능하며, 다양한 보안 컨텍스트 설정을 개별적으로 구성할 수 있습니다.
   - **Pod Security Admission**: 미리 정의된 세 가지 정책 수준(privileged, baseline, restricted)만 제공하며, 세부 설정을 개별적으로 조정할 수 없습니다.

4. **사용 편의성**:
   - **PodSecurityPolicy**: 설정이 복잡하고 RBAC 바인딩이 필요하여 구성 오류가 발생하기 쉽습니다.
   - **Pod Security Admission**: 간단한 네임스페이스 레이블링만으로 적용되어 사용이 훨씬 간편합니다.

5. **적용 범위**:
   - **PodSecurityPolicy**: 클러스터 전체 또는 특정 사용자/서비스 계정에 적용됩니다.
   - **Pod Security Admission**: 네임스페이스 단위로 적용됩니다.

6. **모드**:
   - **PodSecurityPolicy**: 적용 또는 미적용의 이진법적 접근 방식입니다.
   - **Pod Security Admission**: 세 가지 모드(enforce, audit, warn)를 제공하여 점진적인 적용이 가능합니다.
     - enforce: 위반 시 포드 생성 거부
     - audit: 위반 시 감사 로그에 기록
     - warn: 위반 시 경고 메시지 표시

7. **마이그레이션 및 지원**:
   - **PodSecurityPolicy**: Kubernetes v1.25에서 제거되었습니다.
   - **Pod Security Admission**: Kubernetes v1.23부터 베타 기능으로 제공되었으며, v1.25부터 PSP를 완전히 대체합니다.

8. **확장성**:
   - **PodSecurityPolicy**: 사용자 정의 설정을 통해 높은 확장성을 제공합니다.
   - **Pod Security Admission**: 제한된 확장성을 제공하며, 더 세밀한 제어가 필요한 경우 OPA Gatekeeper나 Kyverno와 같은 추가 도구가 필요할 수 있습니다.

3. Kubernetes에서 RBAC와 함께 External Authorization을 구현하는 방법과 그 이점을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Kubernetes에서 RBAC와 External Authorization 구현:**

1. **External Authorization 개요**:
   External Authorization은 Kubernetes의 내장 RBAC 시스템 외부에서 권한 부여 결정을 수행하는 방식입니다. 이를 통해 더 복잡한 권한 부여 로직, 외부 ID 시스템과의 통합, 그리고 중앙 집중식 정책 관리가 가능해집니다.

2. **구현 방법**:

   a. **Webhook 모드 사용**:
   ```yaml
   apiVersion: v1
   kind: Config
   preferences: {}
   clusters:
   - name: authz-service
     cluster:
       server: https://authz-service.example.com/authorize
       certificate-authority: /path/to/ca.crt
   users:
   - name: kube-apiserver
     user:
       client-certificate: /path/to/client.crt
       client-key: /path/to/client.key
   current-context: webhook
   contexts:
   - context:
       cluster: authz-service
       user: kube-apiserver
     name: webhook
   ```

   b. **API 서버 구성**:
   ```
   --authorization-mode=Node,RBAC,Webhook
   --authorization-webhook-config-file=/path/to/webhook-config.yaml
   ```

   c. **외부 권한 부여 서비스 구현**:
   외부 서비스는 다음 형식의 요청을 처리해야 합니다:
   ```json
   {
     "apiVersion": "authorization.k8s.io/v1beta1",
     "kind": "SubjectAccessReview",
     "spec": {
       "resourceAttributes": {
         "namespace": "default",
         "verb": "get",
         "group": "apps",
         "resource": "deployments"
       },
       "user": "jane",
       "groups": ["developers", "qa"]
     }
   }
   ```

   그리고 다음과 같은 응답을 반환해야 합니다:
   ```json
   {
     "apiVersion": "authorization.k8s.io/v1beta1",
     "kind": "SubjectAccessReview",
     "status": {
       "allowed": true,
       "reason": "User is authorized by external policy"
     }
   }
   ```

3. **RBAC와 External Authorization 통합**:
   - RBAC를 기본 권한 부여 메커니즘으로 사용
   - 복잡한 정책이나 외부 시스템과의 통합이 필요한 경우 External Authorization으로 위임
   - 권한 부여 모드 체인에서 RBAC를 먼저 평가하고, 그 다음 Webhook 모드 평가

4. **이점**:
   - **세밀한 접근 제어**: 사용자 속성, 리소스 상태, 시간 기반 조건 등 복잡한 조건에 기반한 권한 부여 가능
   - **중앙 집중식 정책 관리**: 조직의 모든 시스템에 걸쳐 일관된 정책 적용 가능
   - **외부 ID 시스템 통합**: Active Directory, LDAP, OIDC 제공자 등과 통합 가능
   - **동적 정책 업데이트**: API 서버를 재시작하지 않고도 정책 업데이트 가능
   - **감사 및 로깅 강화**: 중앙 집중식 로깅 및 감사 기능 제공
   - **기존 RBAC 보완**: 기본 RBAC 시스템의 한계를 극복하면서 기존 RBAC 구성 유지

5. **구현 예시 - OPA 통합**:
   Open Policy Agent(OPA)를 사용한 External Authorization 구현:
   
   a. OPA 배포:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: opa
     namespace: opa
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: opa
     template:
       metadata:
         labels:
           app: opa
       spec:
         containers:
         - name: opa
           image: openpolicyagent/opa:latest
           args:
           - "run"
           - "--server"
           - "--addr=0.0.0.0:8181"
           - "--set=decision_logs.console=true"
           ports:
           - containerPort: 8181
   ```

   b. OPA 정책 정의:
   ```rego
   package kubernetes.authz

   default allow = false

   allow {
     input.spec.resourceAttributes.namespace == "default"
     input.spec.resourceAttributes.resource == "deployments"
     input.spec.resourceAttributes.verb == "get"
     input.spec.user == "jane"
     "developers" in input.spec.groups
   }
   ```

   c. Webhook 서비스 구현:
   ```go
   func handleAuthz(w http.ResponseWriter, r *http.Request) {
       var review authorizationv1.SubjectAccessReview
       if err := json.NewDecoder(r.Body).Decode(&review); err != nil {
           http.Error(w, err.Error(), http.StatusBadRequest)
           return
       }
       
       // OPA에 쿼리
       allowed, reason := queryOPA(review)
       
       review.Status = authorizationv1.SubjectAccessReviewStatus{
           Allowed: allowed,
           Reason:  reason,
       }
       
       w.Header().Set("Content-Type", "application/json")
       json.NewEncoder(w).Encode(review)
   }
   ```

External Authorization은 Kubernetes의 RBAC 시스템을 보완하여 더 강력하고 유연한 접근 제어를 제공합니다. 그러나 외부 서비스에 대한 의존성이 생기므로 가용성과 성능을 고려한 설계가 필요합니다.
</details>

4. Kubernetes에서 Network Policy를 사용한 멀티 테넌트 네트워크 격리 전략을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Kubernetes에서 Network Policy를 사용한 멀티 테넌트 네트워크 격리 전략:**

1. **멀티 테넌트 네트워크 격리의 필요성**:
   - 여러 팀이나 프로젝트가 동일한 클러스터를 공유할 때 네트워크 수준의 격리 필요
   - 테넌트 간 무단 통신 방지
   - 보안 경계 설정 및 규정 준수 요구 사항 충족
   - 악의적인 워크로드로부터 보호

2. **네임스페이스 기반 격리 전략**:

   a. **기본 거부 정책 설정**:
   각 테넌트 네임스페이스에 모든 인그레스 및 이그레스 트래픽을 차단하는 기본 정책 적용:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny-all
     namespace: tenant-a
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

   b. **테넌트 내부 통신 허용**:
   동일한 테넌트 내의 포드 간 통신 허용:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-same-namespace
     namespace: tenant-a
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: tenant-a
   ```

   c. **특정 서비스 노출**:
   다른 테넌트에게 특정 서비스만 노출:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-api-access
     namespace: tenant-a
   spec:
     podSelector:
       matchLabels:
         app: api
     policyTypes:
     - Ingress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: tenant-b
       ports:
       - protocol: TCP
         port: 8080
   ```

3. **레이블 기반 세분화 전략**:
   
   a. **역할 기반 접근 제어**:
   포드 레이블을 사용하여 더 세밀한 접근 제어 구현:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: db-access-policy
     namespace: tenant-a
   spec:
     podSelector:
       matchLabels:
         app: database
     policyTypes:
     - Ingress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             role: backend
   ```

   b. **계층화된 애플리케이션 격리**:
   웹-앱-DB와 같은 계층화된 애플리케이션 아키텍처에서 계층 간 통신만 허용:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: web-to-app-only
     namespace: tenant-a
   spec:
     podSelector:
       matchLabels:
         tier: app
     policyTypes:
     - Ingress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             tier: web
   ```

4. **공유 서비스 접근 전략**:
   
   a. **공유 서비스 네임스페이스 생성**:
   모든 테넌트가 접근해야 하는 공유 서비스(모니터링, 로깅 등)를 위한 별도의 네임스페이스 생성

   b. **선택적 접근 허용**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-monitoring
     namespace: monitoring
   spec:
     podSelector:
       matchLabels:
         app: prometheus
     policyTypes:
     - Ingress
     ingress:
     - from:
       - namespaceSelector:
           matchExpressions:
           - key: name
             operator: In
             values: ["tenant-a", "tenant-b", "tenant-c"]
       ports:
       - protocol: TCP
         port: 9090
   ```

5. **외부 통신 제어 전략**:
   
   a. **특정 외부 엔드포인트만 허용**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-specific-egress
     namespace: tenant-a
   spec:
     podSelector:
       matchLabels:
         app: frontend
     policyTypes:
     - Egress
     egress:
     - to:
       - ipBlock:
           cidr: 203.0.113.0/24
       ports:
       - protocol: TCP
         port: 443
   ```

   b. **DNS 접근 허용**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-dns
     namespace: tenant-a
   spec:
     podSelector: {}
     policyTypes:
     - Egress
     egress:
     - to:
       - namespaceSelector:
           matchLabels:
             name: kube-system
         podSelector:
           matchLabels:
             k8s-app: kube-dns
       ports:
       - protocol: UDP
         port: 53
       - protocol: TCP
         port: 53
   ```

6. **구현 모범 사례**:
   - 모든 테넌트 네임스페이스에 기본 거부 정책 적용
   - 필요한 통신만 명시적으로 허용
   - 네임스페이스에 일관된 레이블 지정 체계 사용
   - 정책을 점진적으로 적용하고 테스트
   - 네트워크 정책 시뮬레이터 도구 사용
   - 정책 변경 사항을 버전 제어 시스템에 저장
   - 네트워크 정책 감사 및 모니터링 구현

7. **제한 사항 및 고려 사항**:
   - CNI 플러그인이 NetworkPolicy를 지원해야 함(Calico, Cilium, Weave Net 등)
   - 복잡한 정책은 성능에 영향을 미칠 수 있음
   - 일부 특수한 통신 패턴은 표준 NetworkPolicy로 구현하기 어려울 수 있음
   - 정책이 많아지면 관리 복잡성이 증가함

멀티 테넌트 환경에서 NetworkPolicy를 효과적으로 사용하면 테넌트 간의 네트워크 격리를 강화하고 보안 위험을 줄일 수 있습니다. 그러나 정책 설계와 관리에 주의를 기울여야 하며, 필요에 따라 추가적인 보안 도구(서비스 메시, 웹 애플리케이션 방화벽 등)로 보완하는 것이 좋습니다.
</details>

5. Kubernetes에서 ResourceQuota와 LimitRange를 사용한 리소스 관리 전략을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Kubernetes에서 ResourceQuota와 LimitRange를 사용한 리소스 관리 전략:**

1. **리소스 관리의 필요성**:
   - 클러스터 리소스의 공정한 분배
   - 리소스 고갈 방지
   - 비용 제어 및 예측 가능성 향상
   - 워크로드 성능 보장
   - 테넌트 간 리소스 격리

2. **계층적 리소스 관리 접근 방식**:

   a. **클러스터 수준**:
   - 노드 풀 구성 및 크기 조정
   - 클러스터 오토스케일러 설정
   - 노드 테인트 및 톨러레이션을 통한 워크로드 분리

   b. **네임스페이스 수준**:
   - ResourceQuota를 사용하여 네임스페이스별 리소스 제한
   - 네임스페이스 우선순위 클래스 할당

   c. **워크로드 수준**:
   - LimitRange를 사용하여 개별 컨테이너 기본값 및 제한 설정
   - 포드 우선순위 및 선점 구성

3. **ResourceQuota 전략**:

   a. **컴퓨팅 리소스 쿼터**:
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: compute-resources
     namespace: team-a
   spec:
     hard:
       requests.cpu: "10"
       requests.memory: 20Gi
       limits.cpu: "20"
       limits.memory: 40Gi
   ```

   b. **스토리지 리소스 쿼터**:
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: storage-resources
     namespace: team-a
   spec:
     hard:
       requests.storage: 500Gi
       persistentvolumeclaims: "10"
       # 스토리지 클래스별 제한
       ssd.storageclass.storage.k8s.io/requests.storage: 200Gi
       standard.storageclass.storage.k8s.io/requests.storage: 300Gi
   ```

   c. **오브젝트 수 쿼터**:
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: object-counts
     namespace: team-a
   spec:
     hard:
       pods: "50"
       services: "10"
       services.loadbalancers: "2"
       services.nodeports: "5"
       secrets: "20"
       configmaps: "20"
       replicationcontrollers: "10"
       deployments.apps: "10"
       statefulsets.apps: "5"
   ```

   d. **우선순위 기반 쿼터**:
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: priority-quota
     namespace: team-a
   spec:
     hard:
       pods: "10"
     scopeSelector:
       matchExpressions:
       - operator: In
         scopeName: PriorityClass
         values: ["high"]
   ```

4. **LimitRange 전략**:

   a. **컨테이너 기본값 및 제한 설정**:
   ```yaml
   apiVersion: v1
   kind: LimitRange
   metadata:
     name: container-limits
     namespace: team-a
   spec:
     limits:
     - default:  # 기본 제한
         cpu: 500m
         memory: 512Mi
       defaultRequest:  # 기본 요청
         cpu: 100m
         memory: 256Mi
       max:  # 최대 제한
         cpu: "2"
         memory: 2Gi
       min:  # 최소 요청
         cpu: 50m
         memory: 128Mi
       type: Container
   ```

   b. **포드 전체 제한 설정**:
   ```yaml
   apiVersion: v1
   kind: LimitRange
   metadata:
     name: pod-limits
     namespace: team-a
   spec:
     limits:
     - max:
         cpu: "4"
         memory: 4Gi
       min:
         cpu: 100m
         memory: 256Mi
       type: Pod
   ```

   c. **PVC 크기 제한**:
   ```yaml
   apiVersion: v1
   kind: LimitRange
   metadata:
     name: storage-limits
     namespace: team-a
   spec:
     limits:
     - max:
         storage: 100Gi
       min:
         storage: 1Gi
       type: PersistentVolumeClaim
   ```

5. **리소스 관리 모범 사례**:

   a. **계층적 쿼터 설계**:
   - 팀/부서별 네임스페이스 그룹화
   - 환경별(개발, 스테이징, 프로덕션) 쿼터 차별화
   - 애플리케이션 중요도에 따른 쿼터 할당

   b. **리소스 요청 및 제한 설정**:
   - 모든 컨테이너에 리소스 요청 설정
   - 중요한 워크로드에 적절한 제한 설정
   - 실제 사용량 모니터링 및 요청 조정

   c. **점진적 적용**:
   - 초기에는 큰 쿼터로 시작하여 점진적으로 조정
   - 감사 모드로 시작하여 영향 평가
   - 사용자 교육 및 피드백 수집

   d. **모니터링 및 알림**:
   - 쿼터 사용량 모니터링
   - 쿼터 접근 시 알림 설정
   - 리소스 사용 패턴 분석 및 최적화

6. **고급 리소스 관리 기법**:

   a. **동적 쿼터 관리**:
   - 시간대별 또는 수요에 따른 쿼터 조정
   - 자동화된 쿼터 관리 시스템 구현

   b. **비용 할당 및 차지백**:
   - 네임스페이스별 리소스 사용량 추적
   - 팀/부서별 비용 할당
   - 사용량 기반 비용 보고

   c. **버스팅 및 초과 할당**:
   - 일시적인 쿼터 초과 허용 메커니즘
   - 사용되지 않는 쿼터의 공유 풀 구현

ResourceQuota와 LimitRange를 효과적으로 조합하여 사용하면 클러스터 리소스를 공정하게 분배하고, 리소스 고갈을 방지하며, 워크로드 성능을 보장할 수 있습니다. 이러한 전략은 특히 여러 팀이나 애플리케이션이 동일한 클러스터를 공유하는 멀티 테넌트 환경에서 중요합니다.
</details>
