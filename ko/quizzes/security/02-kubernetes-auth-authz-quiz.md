# Kubernetes 인증 및 권한 부여 퀴즈

> **관련 문서**: [Kubernetes 인증 및 권한 부여 시스템](../../security/02-kubernetes-auth-authz.md)

> **마지막 업데이트**: 2026년 9월 13일

## 객관식 문제

### 1. Kubernetes에서 X.509 인증서를 사용한 인증 시, 사용자 이름은 어느 필드에서 추출됩니까?

- A) Subject Alternative Name (SAN)
- B) Common Name (CN)
- C) Organization Unit (OU)
- D) Issuer

<details>
<summary>정답 보기</summary>

**정답: B) Common Name (CN)**

**설명:**
X.509 인증서에서 Common Name(CN)은 사용자 이름으로, Organization(O)은 그룹으로 매핑됩니다.

</details>

### 2. RBAC에서 ClusterRole과 Role의 주요 차이점은 무엇입니까?

- A) ClusterRole은 읽기 전용, Role은 읽기/쓰기
- B) ClusterRole은 클러스터 범위 정의이며, Role은 한 네임스페이스의 정의
- C) ClusterRole은 관리자 전용, Role은 일반 사용자 전용
- D) ClusterRole은 노드에만 적용, Role은 파드에만 적용

<details>
<summary>정답 보기</summary>

**정답: B) ClusterRole은 클러스터 범위 정의이며, Role은 한 네임스페이스의 정의**

**설명:**
ClusterRole은 네임스페이스 리소스의 재사용 권한도 정의할 수 있습니다. RoleBinding에서 ClusterRole을 참조하면 바인딩 네임스페이스에만 적용됩니다. ClusterRoleBinding은 ClusterRole 권한을 클러스터 전체에 부여합니다. 역할 정의 자체는 권한을 부여하지 않습니다.

</details>

### 3. ServiceAccount 토큰이 파드에 자동으로 마운트되는 기본 경로는?

- A) /var/run/secrets/kubernetes.io/token
- B) /etc/kubernetes/serviceaccount
- C) /var/run/secrets/kubernetes.io/serviceaccount
- D) /opt/kubernetes/secrets

<details>
<summary>정답 보기</summary>

**정답: C) /var/run/secrets/kubernetes.io/serviceaccount**

**설명:**
자동 마운트가 활성화된 Linux Pod의 기본 디렉터리입니다. 실제 토큰 파일은 이 디렉터리의 `token`이며 `automountServiceAccountToken: false`인 Pod나 사용자 지정 projected volume에서는 경로·존재 여부가 다릅니다.

</details>

### 4. MutatingAdmissionWebhook과 ValidatingAdmissionWebhook의 실행 순서는?

- A) Validating이 먼저, Mutating이 나중에
- B) Mutating이 먼저, Validating이 나중에
- C) 동시에 병렬로 실행
- D) 순서 없이 무작위로 실행

<details>
<summary>정답 보기</summary>

**정답: B) Mutating이 먼저, Validating이 나중에**

**설명:**
어드미션 컨트롤러 실행 순서: 1) MutatingAdmissionWebhook(요청 수정), 2) ValidatingAdmissionWebhook(요청 검증).

</details>

<span id="_5-eks에서-iam-사용자-역할을-kubernetes-rbac에-매핑하는-configmap은"></span>

### 5. 레거시 EKS CONFIG_MAP 인증 모드에서 IAM 사용자/역할 매핑을 보관하는 ConfigMap은?

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>정답 보기</summary>

**정답: B) aws-auth**

**설명:**
`kube-system/aws-auth`는 레거시 IAM 매핑입니다. 현재는 EKS access entry를 사용하고 필요한 RBAC 또는 EKS access policy를 부여합니다. 전환 중 두 모드를 함께 사용할 때 동일 principal은 access entry가 우선합니다. 기존 ConfigMap 전체를 덮어쓰면 노드 매핑 등을 잃을 수 있습니다.

</details>

<span id="_6-프로덕션-kubernetes-클러스터에-권장되는-인증-방법은"></span>

### 6. 외부 IdP가 발급한 ID 토큰으로 사용자 로그인을 통합하는 방법은?

- A) 정적 토큰 파일
- B) 기본 인증
- C) OIDC (OpenID Connect)
- D) 익명 인증

<details>
<summary>정답 보기</summary>

**정답: C) OIDC (OpenID Connect)**

**설명:**
OIDC는 외부 IdP가 발급한 ID 토큰의 issuer·audience·서명·만료를 검증합니다. 로그인과 갱신은 IdP/클라이언트가 담당하고 API 서버가 refresh token을 발급하는 것은 아닙니다. EKS IAM 인증도 별도 선택지이며 IRSA/Pod Identity는 Pod의 AWS API 권한을 위한 다른 경로입니다.

</details>

### 7. Kubernetes에서 `system:masters` 그룹의 목적은?

- A) 마스터 노드 관리
- B) RBAC·웹훅 인가를 우회하는 무제한 API 권한 제공
- C) 마스터 노드에 파드 스케줄링
- D) 시스템 네임스페이스 관리

<details>
<summary>정답 보기</summary>

**정답: B) RBAC·웹훅 인가를 우회하는 무제한 API 권한 제공**

**설명:**
`system:masters`는 인가를 우회하는 특별 그룹입니다. 일반 RBAC 관리자 바인딩과 같지 않으며, ClusterRoleBinding 삭제만으로 접근을 회수할 수 없습니다. 일반 관리자에게 이 그룹을 배정하지 않습니다.

</details>

### 8. ServiceAccount가 특정 네임스페이스에서 파드만 읽을 수 있도록 제한하는 방법은?

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) Role만 생성
- D) Role + RoleBinding

<details>
<summary>정답 보기</summary>

**정답: D) Role + RoleBinding**

**설명:**
Pod get/list/watch만 정의한 Role과 해당 네임스페이스의 RoleBinding을 사용합니다. 다른 허용 바인딩이 없다는 조건입니다. **ClusterRole + RoleBinding도 가능**하므로 이를 오답 보기로 두면 복수 정답이 됩니다. 다른 네임스페이스의 ServiceAccount도 subjects.namespace로 명시할 수 있으며 권한 범위는 바인딩 네임스페이스입니다.

</details>

### 9. RBAC에서 `impersonate` 동사의 목적은?

- A) 가짜 리소스 생성
- B) 사용자가 다른 사용자나 그룹으로 행동할 수 있게 허용
- C) 리소스 복제
- D) 리소스 이름 마스킹

<details>
<summary>정답 보기</summary>

**정답: B) 사용자가 다른 사용자나 그룹으로 행동할 수 있게 허용**

**설명:**
`impersonate` 동사는 사용자가 다른 사용자, 그룹 또는 ServiceAccount인 것처럼 작업을 수행할 수 있게 합니다. 디버깅과 관리 목적에 유용합니다.

</details>

### 10. 마운트된 볼륨에서 ServiceAccount 토큰이 포함된 파일은?

- A) ca.crt
- B) namespace
- C) token
- D) serviceaccount.json

<details>
<summary>정답 보기</summary>

**정답: C) token**

**설명:**
기본 자동 마운트 ServiceAccount 볼륨에는 다음 파일이 있습니다(사용자 지정 projection은 다를 수 있음): `ca.crt`(CA 인증서), `namespace`(현재 네임스페이스), `token`(인증용 JWT 토큰).

</details>

## 단답형 문제

### 1. Kubernetes에서 사용자 계정과 서비스 계정의 주요 차이점은 무엇입니까?

<details>
<summary>정답 보기</summary>

**정답: 사용자 계정은 외부에서 관리되고 Kubernetes가 직접 관리하지 않으며, 서비스 계정은 Kubernetes API로 관리되는 네임스페이스 리소스입니다.**

</details>

### 2. 서비스 계정 토큰의 자동 마운트를 비활성화하는 방법은?

<details>
<summary>정답 보기</summary>

**정답: ServiceAccount의 최상위 또는 Pod의 spec에 `automountServiceAccountToken: false`를 설정합니다. 둘 다 있으면 Pod 설정이 우선하며 명시적 projected token volume은 별도로 동작합니다.**

</details>

### 3. ClusterRole에서 `rules`와 `aggregationRule`의 차이점은?

<details>
<summary>정답 보기</summary>

**정답: `rules`는 권한을 직접 정의하고, `aggregationRule`은 특정 레이블과 일치하는 다른 ClusterRole의 권한을 자동으로 결합합니다.**

**설명:**
집계 컨트롤러가 대상 ClusterRole의 `rules`를 관리하므로 직접 수정한 rules는 덮어써질 수 있습니다. 라벨로 선택되는 역할을 추가·수정하는 권한도 최종 접근 권한에 영향을 줍니다.

</details>

### 4. TokenRequest API란 무엇이며 정적 토큰보다 선호되는 이유는?

<details>
<summary>정답 보기</summary>

**정답: TokenRequest API는 장수명 정적 토큰보다 더 안전한 시간 제한, 대상 바인딩 토큰을 생성합니다.**

**설명:**
요청한 수명과 audience가 적용되며, 실제 만료 시각은 서버 응답으로 확인합니다. 서버가 요청 수명을 조정할 수 있습니다. Pod projected 토큰은 kubelet이 갱신하지만 애플리케이션이 파일을 다시 읽어야 합니다. 일반 TokenRequest 호출 자체가 자동 파일 갱신을 제공하는 것은 아니며, 토큰은 계속 비밀 bearer 자격 증명입니다.

</details>

### 5. 여러 인증 방법이 구성된 경우 Kubernetes가 어떤 방법을 사용할지 결정하는 방법은?

<details>
<summary>정답 보기</summary>

**정답: 첫 번째 성공한 인증 결과를 사용하지만 인증기 실행 순서는 보장되지 않습니다.**

**설명:**
고정된 X.509 → OIDC → 프록시 순서를 가정하지 않습니다. 잘못된 자격 증명은 401을 일으킬 수 있습니다. 자격 증명이 없는 요청의 익명 처리는 서버 설정에 따라 다르며, 익명으로 인증되어도 인가에서 거부될 수 있습니다.

</details>

## 실습 문제

### 1. 다음 요구사항을 충족하는 Role과 RoleBinding을 작성하세요.

- 네임스페이스: development
- 권한: Pod 읽기(get, list, watch), ConfigMap 개별 객체 읽기·생성·수정·삭제(일괄 삭제 제외)
- 사용자: developer@example.com

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: development
  name: developer-role
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: development
subjects:
- kind: User
  name: developer@example.com
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-role
  apiGroup: rbac.authorization.k8s.io
```

</details>

<span id="_2-커스텀-토큰-만료-시간이-있는-serviceaccount를-생성하세요"></span>

### 2. ServiceAccount와 지정한 토큰 수명을 요청하는 projected volume Pod를 작성하세요.

<details>
<summary>정답 보기</summary>

```yaml
# ServiceAccount 정의
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-sa
  namespace: default
automountServiceAccountToken: false
---
# 커스텀 만료가 있는 projected 토큰을 사용하는 Pod
apiVersion: v1
kind: Pod
metadata:
  name: app-with-custom-token
  namespace: default
spec:
  serviceAccountName: custom-sa
  automountServiceAccountToken: false
  containers:
  - name: app
    image: registry.k8s.io/pause:3.10
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
      readOnly: true
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600  # 요청 수명이며 실제 수명 보장은 아님
          audience: https://service.example.com
```

**설명:**
`expirationSeconds`의 최소 요청값은 600초이며 실제 만료는 서버가 결정합니다. 위 audience는 예제 수신 서비스가 검증하도록 설정할 값이고 Kubernetes API에 자동 허용되는 값이 아닙니다. API 호출용이면 해당 API 서버가 허용하는 audience를 확인해야 합니다. 자동 마운트는 끄고 명시적 토큰만 읽기 전용으로 마운트합니다. 이 pause Pod는 마운트 구조만 보여주며 토큰을 사용하거나 HTTP 요청을 보내지 않습니다. 실제 애플리케이션은 kubelet의 토큰 교체 후 파일을 다시 읽어야 합니다.

</details>

### 3. 특정 사용자의 권한을 확인하는 명령어를 작성하세요.

<details>
<summary>정답 보기</summary>

```bash
# 사용자가 특정 작업을 수행할 수 있는지 확인
kubectl auth can-i create deployments --as=developer@example.com -n development

# 네임스페이스의 규칙 목록 조회(인가기별 한계는 아래 설명)
kubectl auth can-i --list --as=developer@example.com -n development

# ServiceAccount의 권한 확인
kubectl auth can-i get pods -n development \
  --as=system:serviceaccount:default:my-sa \
  --as-group=system:serviceaccounts \
  --as-group=system:serviceaccounts:default \
  --as-group=system:authenticated

# 그룹 가장
kubectl auth can-i create pods --as=developer@example.com --as-group=developers -n development
```

**설명:**
가장하려는 사용자·ServiceAccount와 각 그룹에 대해 호출자의 `impersonate` 권한이 필요합니다. 그룹 멤버십이 자동 복원된다고 가정하지 않습니다. `--list`는 완전한 유효 권한 목록을 항상 제공하지 않으며 EKS access policy 권한은 표시하지 않습니다. EKS에서 가장하면 RBAC 평가를 강제하므로 실제 IAM 역할로 별도 확인해야 합니다. `can-i` 허용은 어드미션·네트워크 접근·쿼터 통과를 보장하지 않습니다.

</details>

## 심화 문제

### 1. 멀티 테넌트 Kubernetes 클러스터에서 테넌트 간 격리를 위한 보안 전략을 설계하세요.

<details>
<summary>정답 보기</summary>

**네임스페이스 및 RBAC 설계:**

- 테넌트별 네임스페이스 생성
- Pod Security Standards 적용
- NetworkPolicy로 네트워크 격리
- ResourceQuota로 리소스 제한

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-alpha
  labels:
    tenant: alpha
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: tenant-alpha
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-alpha
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workload-editor
  namespace: tenant-alpha
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies"]
  verbs: ["get", "list"]  # 네트워크 정책은 읽기 전용
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-workload-editors
  namespace: tenant-alpha
subjects:
- kind: Group
  name: tenant-alpha:developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workload-editor
  apiGroup: rbac.authorization.k8s.io
```

위 예제의 PSS 버전 `v1.35`는 고정된 학습 기준이며 대상 클러스터에서 지원하는 정책 버전을 선택·검증해야 합니다. 기본 거부는 DNS와 외부 의존성도 막으므로 필요한 허용 정책을 별도로 검토합니다. CNI가 실제로 정책을 적용해야 합니다. 테넌트는 namespace 레이블·NetworkPolicy·ResourceQuota·RBAC를 변경할 수 없어야 하며 기존 다른 바인딩도 검토합니다.

**Deployment 생성·수정은 해당 네임스페이스의 다른 ServiceAccount나 Secret을 사용하는 Pod를 만들 수 있는 권한으로 이어집니다.** Secret get을 빼는 것만으로 이 경로를 차단하지 못합니다. 신뢰 수준이 다른 ServiceAccount/비밀을 같은 네임스페이스에 두지 말고, 필요하면 admission으로 사용 가능한 신원을 제한하거나 별도 클러스터를 사용합니다. 이 예제는 강한 테넌트 격리의 실증이 아닙니다.

**추가 보안 조치:**

- 애플리케이션별 별도 ServiceAccount 사용
- 감사 로깅 구현
- 정책 적용을 위한 어드미션 웹훅 사용
- 하위 테넌트 소유권과 정책 전파를 명시적으로 설계; 일반 Kubernetes 네임스페이스는 평면 구조

</details>

### 2. kubectl 명령어 실행 시 완전한 인증 및 권한 부여 흐름을 설명하세요.

<details>
<summary>정답 보기</summary>

1. **클라이언트**: kubectl은 선택한 kubeconfig/context를 읽고 서버 TLS 인증서를 검증합니다. 기본 파일은 `~/.kube/config`지만 `--kubeconfig`와 `KUBECONFIG`로 달라질 수 있습니다. 인증서·토큰·exec 플러그인으로 자격 증명을 준비하며 EKS IAM 경로는 보통 `aws eks get-token`을 사용합니다.
2. **인증**: API 서버가 자격 증명을 검증하여 사용자·그룹을 결정합니다. 여러 인증기의 첫 성공 결과를 사용하되 고정 실행 순서는 보장되지 않습니다. OIDC, 프록시, 웹훅은 각기 다른 검증·신뢰 설정을 가집니다.
3. **인가**: 구성된 인가기를 순서대로 평가하여 첫 Allow 또는 Deny에서 끝납니다. NoOpinion은 다음으로 넘어가며 전부 NoOpinion이면 403으로 거부합니다. RBAC 허용은 관련 바인딩의 합집합이고 명시적 거부 규칙은 없습니다. `system:masters` 우회는 별도 위험입니다.
4. **처리 분기**: 일반 리소스 CREATE/UPDATE는 변경 어드미션 이후 검증 어드미션을 거치며 둘 다 거부할 수 있습니다. 객체 검증·충돌 등의 검사도 통과한 실제 변경은 저장됩니다. `get/list/watch`는 어드미션을 거치지 않으며 dry-run, DELETE, CONNECT, 집계 API 등은 동일한 etcd 저장 흐름으로 단순화할 수 없습니다.
5. **응답**: API 서버는 결과나 오류를 클라이언트에 반환합니다. API 요청 성공은 컨트롤러 처리나 애플리케이션 준비 완료를 뜻하지 않습니다.

| 요청 예시 | 인증·인가 후의 차이 |
|---|---|
| `kubectl get pods` | 읽기 결과 반환; 어드미션을 거치거나 새 Pod를 저장하지 않음 |
| Pod CREATE | 변경/검증 어드미션 및 객체 검사를 통과한 뒤 저장; 스케줄링은 이후 |
| 서버 dry-run CREATE | 어드미션 등 서버 검증을 수행하되 영속 저장하지 않음 |

인증은 신원, 인가는 API 작업 허용, 어드미션은 변경 요청에 대한 추가 정책을 담당합니다.

</details>

## 공식 참고 자료

- [Authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [Admission](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
