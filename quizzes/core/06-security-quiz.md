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

## 주관식 문제

1. Kubernetes에서 RBAC의 'Role'과 'ClusterRole'의 주요 차이점은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:**
Role은 특정 네임스페이스 내에서만 권한을 정의하고 적용되는 반면, ClusterRole은 클러스터 전체에 적용되며 모든 네임스페이스에 걸쳐 권한을 정의합니다. ClusterRole은 네임스페이스가 없는 리소스(노드, PV 등)에 대한 권한을 정의할 때도 사용됩니다.
</details>

2. Kubernetes에서 '최소 권한 원칙'을 적용하기 위한 방법 세 가지를 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
1. RBAC를 사용하여 필요한 최소한의 권한만 부여하기
2. 포드 보안 컨텍스트에서 비루트 사용자로 컨테이너 실행하기
3. 네트워크 정책을 사용하여 필요한 통신만 허용하기
4. 권한 있는 컨테이너 사용 제한하기
5. 컨테이너 기능(capabilities) 제한하기
6. 포드 보안 표준의 Restricted 프로필 적용하기

(위 중 세 가지만 설명하면 됩니다)
</details>

3. Kubernetes에서 Secret과 ConfigMap의 보안 관점에서의 주요 차이점은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:**
Secret은 민감한 정보(비밀번호, 토큰, 키 등)를 저장하기 위한 것이고, ConfigMap은 일반 구성 데이터를 저장하기 위한 것입니다. Secret은 Base64로 인코딩되어 저장되며(기본적으로는 암호화되지 않음), 메모리에만 마운트되도록 설정할 수 있고, 포드 생성 시에만 참조됩니다. 그러나 추가 구성 없이는 둘 다 etcd에 평문으로 저장되므로, 완전한 보안을 위해서는 etcd 암호화 설정이 필요합니다.
</details>

4. Kubernetes에서 '서비스 계정 토큰 볼륨 프로젝션'의 목적과 이점은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:**
서비스 계정 토큰 볼륨 프로젝션은 포드에 마운트되는 서비스 계정 토큰에 대해 시간 제한, 대상 청중 제한 등의 추가 보안 기능을 제공합니다. 이를 통해 토큰의 수명을 제한하고, 특정 API 서버만 토큰을 수락하도록 할 수 있어 토큰 유출 시 위험을 줄일 수 있습니다. 또한 토큰이 자동으로 갱신되므로 장기 실행 애플리케이션의 인증 문제를 방지할 수 있습니다.
</details>

5. Kubernetes에서 '컨테이너 샌드박싱'이란 무엇이며, 어떤 기술이 이를 구현하는 데 사용될 수 있나요?

<details>
<summary>정답 보기</summary>

**정답:**
컨테이너 샌드박싱은 컨테이너를 호스트 시스템과 다른 컨테이너로부터 격리하여 보안을 강화하는 기술입니다. 이를 구현하는 기술로는:
1. 리눅스 네임스페이스와 cgroups: 기본적인 컨테이너 격리 제공
2. seccomp: 시스템 콜 제한
3. AppArmor/SELinux: 강제적 접근 제어
4. gVisor: 사용자 공간 커널 구현으로 추가 격리 제공
5. Kata Containers: 경량 VM을 사용한 하드웨어 수준 격리
6. Firecracker: 마이크로VM 기반 격리

이러한 기술들은 컨테이너가 호스트 시스템에 미치는 영향을 제한하고, 컨테이너 탈출 공격의 위험을 줄입니다.
</details>

## 실습 문제

1. 다음 요구 사항에 맞는 RBAC 리소스를 생성하세요:
   - 'monitoring' 네임스페이스의 포드를 읽을 수 있는 Role
   - 'monitoring-team' 서비스 계정에 이 Role을 바인딩하는 RoleBinding

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
# monitoring-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: monitoring
  name: pod-reader
rules:
  - apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
---
# monitoring-rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: monitoring
subjects:
- kind: ServiceAccount
  name: monitoring-team
  namespace: monitoring
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

적용 방법:
```bash
kubectl apply -f monitoring-role.yaml
kubectl apply -f monitoring-rolebinding.yaml
```
</details>

2. 다음 요구 사항에 맞는 NetworkPolicy를 생성하세요:
   - 'backend' 네임스페이스의 모든 포드에 적용
   - 'frontend' 네임스페이스의 포드에서만 8080 포트로 들어오는 트래픽 허용
   - 모든 나가는 트래픽 허용

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
# backend-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend
  namespace: backend
spec:
  podSelector: {}  # 모든 포드에 적용
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - {}  # 모든 나가는 트래픽 허용
```

적용 방법:
```bash
kubectl apply -f backend-network-policy.yaml
```

참고: 이 NetworkPolicy가 작동하려면 'frontend' 네임스페이스에 'name: frontend' 레이블이 있어야 합니다. 없다면 다음 명령으로 추가할 수 있습니다:
```bash
kubectl label namespace frontend name=frontend
```
</details>

3. 다음 요구 사항에 맞는 보안 컨텍스트가 적용된 포드를 생성하세요:
   - 컨테이너는 UID 1000으로 실행
   - 권한 상승 불가능
   - 루트 파일시스템은 읽기 전용

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
# secure-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: secure-container
    image: nginx
    securityContext:
      runAsUser: 1000
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
```

적용 방법:
```bash
kubectl apply -f secure-pod.yaml
```
</details>

4. 다음 요구 사항에 맞는 Secret을 생성하고, 이를 포드에 볼륨으로 마운트하세요:
   - 'db-credentials'라는 이름의 Secret
   - 'username=admin'과 'password=s3cr3t' 포함
   - 포드의 '/etc/db-credentials' 경로에 마운트

<details>
<summary>정답 보기</summary>

**정답:**

Secret 생성:
```bash
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=s3cr3t
```

또는 YAML로:
```yaml
# db-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # 'admin'의 base64 인코딩
  password: czNjcjN0  # 's3cr3t'의 base64 인코딩
```

포드에 마운트:
```yaml
# pod-with-secret.yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-secret
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: secret-volume
      mountPath: "/etc/db-credentials"
      readOnly: true
  volumes:
  - name: secret-volume
    secret:
      secretName: db-credentials
```

적용 방법:
```bash
kubectl apply -f db-secret.yaml
kubectl apply -f pod-with-secret.yaml
```
</details>

## 고급 주제

1. Kubernetes에서 OPA(Open Policy Agent) Gatekeeper를 사용하여 어떤 종류의 정책을 적용할 수 있는지 세 가지 예를 들고 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

OPA Gatekeeper는 Kubernetes 클러스터에 정책을 적용하기 위한 강력한 도구입니다. 다음은 적용할 수 있는 정책의 예입니다:

1. **이미지 레지스트리 제한**: 승인된 레지스트리에서만 이미지를 가져오도록 강제하여 신뢰할 수 없는 소스의 이미지 사용을 방지합니다.
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
         - "gcr.io/company/"
   ```

2. **권한 있는 컨테이너 방지**: 권한 있는 컨테이너의 사용을 금지하여 보안 위험을 줄입니다.
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

3. **리소스 제한 강제**: 모든 컨테이너에 CPU 및 메모리 제한이 설정되도록 강제하여 리소스 고갈 공격을 방지합니다.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
   ```

OPA Gatekeeper는 이 외에도 네임스페이스에 특정 레이블 요구, 인그레스 호스트 이름 제한, 볼륨 타입 제한, 호스트 경로 마운트 방지 등 다양한 정책을 적용할 수 있습니다.
</details>

2. Kubernetes에서 mTLS(mutual TLS)를 구현하는 방법과 그 이점에 대해 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

mTLS(mutual TLS)는 클라이언트와 서버 모두 인증서를 사용하여 서로를 인증하는 방식입니다. Kubernetes에서 mTLS를 구현하는 방법과 이점은 다음과 같습니다:

**구현 방법:**

1. **서비스 메시 사용**: Istio, Linkerd와 같은 서비스 메시는 사이드카 프록시를 통해 mTLS를 자동으로 구현합니다.
   ```yaml
   # Istio 예시
   apiVersion: security.istio.io/v1beta1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

2. **네트워크 정책과 함께 사용**: mTLS와 네트워크 정책을 결합하여 인증된 트래픽만 허용합니다.

3. **인증서 관리**: cert-manager와 같은 도구를 사용하여 인증서 수명 주기를 관리합니다.
   ```yaml
   apiVersion: cert-manager.io/v1
   kind: Certificate
   metadata:
     name: service-cert
     namespace: default
   spec:
     secretName: service-tls
     issuerRef:
       name: ca-issuer
       kind: ClusterIssuer
     commonName: service.default.svc.cluster.local
     dnsNames:
     - service.default.svc.cluster.local
   ```

**이점:**

1. **상호 인증**: 클라이언트와 서버가 서로를 인증하여 중간자 공격 방지
2. **암호화된 통신**: 모든 서비스 간 트래픽이 암호화되어 도청 방지
3. **세분화된 접근 제어**: 인증서 기반 신원을 사용하여 세밀한 접근 제어 가능
4. **제로 트러스트 아키텍처**: 네트워크 위치에 관계없이 모든 통신에 인증 요구
5. **규정 준수**: PCI DSS, HIPAA 등의 규정 준수 요구 사항 충족 지원

mTLS는 마이크로서비스 아키텍처에서 서비스 간 통신의 보안을 강화하는 중요한 방법입니다.
</details>

3. Kubernetes에서 '공급망 보안'을 강화하기 위한 방법들을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

Kubernetes에서 공급망 보안을 강화하기 위한 방법은 다음과 같습니다:

1. **이미지 서명 및 검증**:
   - Cosign, Notary 등의 도구를 사용하여 컨테이너 이미지에 서명
   - 서명된 이미지만 배포되도록 정책 적용 (예: OPA Gatekeeper, Kyverno)
   ```bash
   cosign sign --key cosign.key docker.io/company/app:latest
   ```

2. **소프트웨어 자재 명세서(SBOM) 생성 및 검증**:
   - Syft, Anchore 등의 도구를 사용하여 SBOM 생성
   - 이미지에 포함된 모든 소프트웨어 구성 요소 추적
   ```bash
   syft docker.io/company/app:latest -o spdx-json > sbom.json
   ```

3. **취약점 스캐닝**:
   - Trivy, Clair 등의 도구를 사용하여 이미지 취약점 스캔
   - CI/CD 파이프라인에 스캐닝 통합
   ```bash
   trivy image docker.io/company/app:latest
   ```

4. **최소 기본 이미지 사용**:
   - 공격 표면을 줄이기 위해 distroless, scratch 등의 최소 이미지 사용
   ```dockerfile
   FROM gcr.io/distroless/java:11
   COPY --from=build /app/target/app.jar /app.jar
   CMD ["app.jar"]
   ```

5. **이미지 정책 적용**:
   - 이미지 연령, 취약점 심각도, 레지스트리 출처 등에 기반한 정책 적용
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sTrustedImages
   metadata:
     name: trusted-images
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       allowedRegistries:
         - "docker.io/company/"
         - "gcr.io/verified/"
   ```

6. **공급망 수준 방어(Supply Chain Levels for Software Artifacts, SLSA)**:
   - 빌드 출처 추적
   - 재현 가능한 빌드 보장
   - 빌드 무결성 검증

7. **지속적인 모니터링 및 감사**:
   - 런타임 보안 도구를 사용하여 이상 행동 감지
   - 정기적인 보안 감사 수행

이러한 방법들을 조합하여 구현하면 소프트웨어 공급망 공격으로부터 Kubernetes 환경을 보호하는 데 도움이 됩니다.
</details>

4. Kubernetes에서 '제로 트러스트 보안 모델'을 구현하기 위한 접근 방식을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

제로 트러스트 보안 모델은 "네트워크 내부에 있다고 해서 신뢰하지 않는다"는 원칙에 기반합니다. Kubernetes에서 제로 트러스트를 구현하기 위한 접근 방식은 다음과 같습니다:

1. **세분화된 신원 및 접근 관리**:
   - 강력한 RBAC 정책 구현
   - 서비스 계정에 최소 권한 부여
   - 외부 ID 제공자(OIDC, LDAP 등)와 통합
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     namespace: default
     name: minimal-access
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get", "list"]
     resourceNames: ["app-pod"]
   ```

2. **네트워크 세분화**:
   - 기본적으로 모든 트래픽 거부
   - 명시적으로 필요한 통신만 허용하는 네트워크 정책 적용
   - 마이크로세그멘테이션 구현
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

3. **상호 TLS(mTLS) 적용**:
   - 서비스 메시(Istio, Linkerd 등)를 사용하여 모든 서비스 간 통신에 mTLS 적용
   - 인증서 기반 서비스 신원 확인
   ```yaml
   apiVersion: security.istio.io/v1beta1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

4. **지속적인 검증 및 인증**:
   - 모든 요청에 대한 지속적인 인증 및 권한 부여
   - 컨텍스트 기반 접근 제어(시간, 위치, 장치 상태 등)
   - OPA Gatekeeper 또는 Kyverno를 사용한 동적 정책 적용

5. **암호화**:
   - 저장 데이터 암호화(etcd 암호화, 암호화된 PV 등)
   - 전송 중 데이터 암호화(TLS, mTLS)
   - 비밀 관리 도구(Vault, Sealed Secrets 등) 통합

6. **위협 감지 및 대응**:
   - 런타임 보안 모니터링 도구 배포
   - 이상 행동 감지 및 경고
   - 자동화된 대응 메커니즘 구현

7. **최소 권한 워크로드 구성**:
   - 비루트 사용자로 컨테이너 실행
   - 읽기 전용 파일 시스템 사용
   - 보안 컨텍스트 제한 적용
   ```yaml
   securityContext:
     runAsUser: 1000
     runAsGroup: 3000
     fsGroup: 2000
     readOnlyRootFilesystem: true
     allowPrivilegeEscalation: false
   ```

8. **지속적인 보안 태세 평가**:
   - 정기적인 취약점 스캔
   - 침투 테스트 및 보안 감사
   - 규정 준수 모니터링

제로 트러스트 모델은 단일 솔루션이 아니라 여러 보안 계층을 조합한 접근 방식으로, 지속적인 검증과 최소 권한 원칙을 기반으로 합니다.
</details>

5. Kubernetes에서 '런타임 보안'을 위한 도구와 기술을 비교 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

Kubernetes에서 런타임 보안을 위한 주요 도구와 기술은 다음과 같습니다:

1. **Falco**:
   - **작동 방식**: 시스템 콜을 모니터링하여 이상 행동 감지
   - **특징**: 
     - 커널 수준에서 동작하여 컨테이너 내부 활동 모니터링
     - 사용자 정의 규칙으로 다양한 보안 위협 감지
     - 실시간 경고 및 대응 지원
   - **예시 규칙**:
     ```yaml
     - rule: Terminal shell in container
       desc: A shell was spawned by a container
       condition: container and proc.name = bash
       output: Shell opened in container (user=%user.name container=%container.name)
       priority: WARNING
     ```

2. **Seccomp (Secure Computing Mode)**:
   - **작동 방식**: 컨테이너가 사용할 수 있는 시스템 콜 제한
   - **특징**:
     - 기본 Linux 커널 기능 활용
     - 허용된 시스템 콜만 실행 가능
     - 공격 표면 감소
   - **구현 예**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: seccomp-pod
     spec:
       securityContext:
         seccompProfile:
           type: Localhost
           localhostProfile: profiles/audit.json
     ```

3. **AppArmor**:
   - **작동 방식**: 프로그램별 접근 제어 프로필 적용
   - **특징**:
     - 파일, 네트워크, 기능 등에 대한 세밀한 접근 제어
     - Linux 배포판에 기본 포함
     - 컨테이너별 프로필 적용 가능
   - **구현 예**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: apparmor-pod
       annotations:
         container.apparmor.security.beta.kubernetes.io/container1: localhost/restricted
     ```

4. **SELinux**:
   - **작동 방식**: 강제적 접근 제어(MAC) 정책 적용
   - **특징**:
     - 세밀한 레이블 기반 보안 정책
     - 군사급 보안 표준 지원
     - 복잡한 설정 필요
   - **구현 예**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: selinux-pod
     spec:
       securityContext:
         seLinuxOptions:
           level: "s0:c123,c456"
     ```

5. **OPA Gatekeeper**:
   - **작동 방식**: 정책 기반 제어를 통한 런타임 거버넌스
   - **특징**:
     - 선언적 정책 정의
     - 광범위한 정책 적용 범위
     - 감사 및 시행 모드 지원
   - **예시 정책**:
     ```yaml
     apiVersion: constraints.gatekeeper.sh/v1beta1
     kind: K8sPSPCapabilities
     metadata:
       name: restrict-capabilities
     spec:
       match:
         kinds:
           - apiGroups: [""]
             kinds: ["Pod"]
       parameters:
         requiredDropCapabilities: ["ALL"]
         allowedCapabilities: ["NET_BIND_SERVICE"]
     ```

6. **Aqua, Sysdig, StackRox 등 상용 도구**:
   - **작동 방식**: 종합적인 컨테이너 보안 플랫폼 제공
   - **특징**:
     - 취약점 스캐닝, 런타임 보호, 규정 준수 모니터링 통합
     - 머신러닝 기반 이상 탐지
     - 대시보드 및 보고서 기능

7. **gVisor**:
   - **작동 방식**: 애플리케이션과 호스트 커널 사이에 사용자 공간 커널 제공
   - **특징**:
     - 컨테이너와 호스트 간 추가 격리 계층
     - 시스템 콜 인터셉트 및 에뮬레이션
     - 성능 오버헤드 존재
   - **구현 예**:
     ```yaml
     apiVersion: node.k8s.io/v1
     kind: RuntimeClass
     metadata:
       name: gvisor
     handler: runsc
     ```

8. **Kata Containers**:
   - **작동 방식**: 경량 VM을 사용하여 컨테이너 실행
   - **특징**:
     - 하드웨어 수준 격리 제공
     - OCI 호환성 유지
     - 일반 컨테이너보다 높은 오버헤드
   - **구현 예**:
     ```yaml
     apiVersion: node.k8s.io/v1
     kind: RuntimeClass
     metadata:
       name: kata
     handler: kata
     ```

**비교 및 선택 기준**:
  - **보안 수준**: Kata Containers와 gVisor는 가장 강력한 격리 제공
  - **성능 영향**: Seccomp는 최소한의 오버헤드, Kata Containers는 가장 큰 오버헤드
  - **구현 복잡성**: Seccomp와 AppArmor는 비교적 쉬움, SELinux는 복잡함
  - **모니터링 vs 방지**: Falco는 주로 모니터링, 다른 도구들은 예방적 보호 제공
  - **통합 용이성**: OPA Gatekeeper는 Kubernetes와 긴밀하게 통합

조직의 보안 요구 사항, 성능 목표, 운영 복잡성 허용 수준에 따라 적절한 도구 조합을 선택해야 합니다.
</details>
