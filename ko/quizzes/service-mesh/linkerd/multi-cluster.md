# Linkerd 다중 클러스터 퀴즈

2026년 9월 11일 검토한 [다중 클러스터 가이드](../../../service-mesh/linkerd/06-multi-cluster.md)를 기준으로 합니다.

### 1. Linkerd multicluster의 핵심 메커니즘은?

- A. Kubernetes cluster 병합
- B. Service mirroring
- C. 모든 애플리케이션 쓰기 자동 복제
- D. 필수 global load balancer

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Source controller가 대상 Kubernetes API에서 선택한 서비스 정보를 감시하고 local discovery 리소스를 만듭니다. 요청 shadowing이나 데이터 복제가 아닙니다. Hierarchical/flat/federated 모드는 network 요구사항이 다릅니다.

</details>

### 2. Mesh mTLS를 위해 cluster가 신뢰해야 하는 것은?

- A. 동일한 issuer private key
- B. 관련 공개 trust-anchor bundle과 issuer chain
- C. 공유 workload private key 하나
- D. 모든 위치의 동일한 Kubernetes Secret 객체

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** 공통 root가 가장 단순하지만 적절한 공유 bundle에 여러 root가 있어도 됩니다. Cluster별 issuer key는 분리할 수 있습니다. 기존 proxy의 trust bundle 전환은 조정해야 하며 공개 root와 signing key를 구분합니다.

</details>

### 3. Hierarchical gateway 모드의 기본 export label은?

- A. linkerd.io/exported: "true"
- B. mirror.linkerd.io/exported: "true"
- C. multicluster.linkerd.io/export: "enabled"
- D. linkerd.io/multicluster: "export"

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** 기본 hierarchical selector는 mirror.linkerd.io/exported=true입니다. Flat은 remote-discovery, federated member는 mirror.linkerd.io/federated=member를 사용합니다. Label은 Link/RBAC에 맞는 discovery를 선택하며 접근 제어 경계가 아닙니다.

</details>

### 4. 일반적인 mirror Service 이름은?

- A. `<service>.<cluster>`
- B. `<service>-<Link cluster name>`
- C. `<cluster>-<service>`
- D. `<service>@<cluster>`

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** west라는 Link에서 import한 web Service는 대응하는 namespace에서 보통 web-west입니다. Link cluster name은 alias이며 실제 EKS cluster 이름과 같을 필요는 없습니다. Namespace 자동 생성은 기본 활성화가 아닙니다.

</details>

### 5. 현재 link-gen 명령이 생성하는 것은?

- A. VPC route와 gateway load balancer
- B. Source cluster에 적용할 Link와 credential Secret 두 개
- C. 복제된 애플리케이션 데이터베이스
- D. 모든 Pod의 새 workload 인증서

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Context west에서 생성하고 east에 적용하면 East가 West를 발견합니다. Source mirror controller는 chart의 controllers 목록으로 구성합니다. 이전 link는 deprecated입니다. 생성한 kubeconfig는 민감하며 접근 가능한 API endpoint와 사용 가능한 CA 데이터가 필요합니다.

</details>

### 6. 대상 gateway probe 통계를 표시하는 명령은?

- A. linkerd multicluster status
- B. linkerd multicluster gateways
- C. kubectl get gateway
- D. linkerd gateway inspect

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** gateways는 설정한 대상 gateway probe를 표시하며 모든 애플리케이션의 건강 상태는 아닙니다. Probe는 source mirror controller가 수행합니다. Flat-only Link에는 gateway가 필요하지 않으므로 Link/endpoint/Pod 연결을 진단합니다.

</details>

### 7. 가이드의 AWS Load Balancer Controller 예제에 사용하는 구성은?

- A. Mesh TLS를 종료하는 public ALB
- B. Region 간에 자동 접근되는 임의 ClusterIP
- C. service.k8s.aws/nlb로 선택한 internal TCP NLB
- D. 이전 nlb annotation만으로 IP target 소유권 보장

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** 해당 controller, 지원되는 annotation, 준비된 private 연결을 가정합니다. EKS Auto Mode는 class/소유자가 다릅니다. Gateway data, probe, 원격 Kubernetes API 경로를 각각 확인해야 합니다.

</details>

### 8. 현재 HTTPRoute 예제의 local/remote 분배 backend는?

- A. Local Service와 다른 API server의 임의 remote Pod IP
- B. Local backend Service와 local에 import한 mirror Service
- C. Local Service만
- D. 자동 database replica set

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Apex Service에서 web-local과 web-west를 사용합니다. 상대 가중치는 자동 standby 정책이 아니며 100/0만으로 실패 시 가중치 0인 backend로 전환되지 않습니다. SMI/Failover extension은 deprecated이며 flat federation에는 별도 요구사항과 동작이 있습니다.

</details>

### 9. Mirror controller의 역할이 아닌 것은?

- A. 선택한 remote Service 감시
- B. Local mirror 생성/갱신
- C. Workload 인증서 발급
- D. 모드에 맞는 discovery/endpoint 정보 관리

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** Workload 인증서는 Identity가 발급합니다. 선택한 mirror controller는 hierarchical 서비스의 이전 Endpoints를 유지합니다. Remote-discovery 모드는 의도적으로 local Endpoints를 제거하고 destination의 원격 조회를 사용할 수 있습니다.

</details>

### 10. 적절히 구성하면 VPC 간 routed private 연결을 제공하는 것은?

- A. Route53만
- B. VPC peering 또는 적합한 Transit Gateway routing
- C. CloudFront만
- D. EKS management interface endpoint가 자동으로 제공하는 flat Pod routing

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Route, 고유하고 접근 가능한 address, DNS, security 제어가 필요합니다. PrivateLink는 선택한 service/resource 접근을 제공하며 VPC peering과 다릅니다. EKS interface endpoint는 cluster Kubernetes API endpoint가 아닙니다.

</details>

### 11. 최종 server에서 보존된 remote workload identity를 인가하는 방법은?

- A. AWS account 이름을 암묵적인 mesh identity로 취급
- B. Flat/federated 모드의 실제 DNS 형식 identity로 Linkerd 인가 구성
- C. 어떤 gateway에서도 이전 SPIFFE URI 예제 사용
- D. Public export label이 caller를 인증한다고 가정

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Hierarchical gateway를 거치면 최종 server에서 원래 caller identity가 보존되지 않습니다. Flat/federated는 보존합니다. ServiceAccount/namespace/trust-domain 이름이 같으면 여러 cluster에서 같은 identity일 수 있으므로 정책이 자동으로 East-only 출처를 증명하지 않습니다.

</details>

### 12. Multicluster 인프라 검사로 입증되지 않는 것은?

- A. 검사로 발견 가능한 Link 설정 오류
- B. 설정된 remote 접근/probe의 검사 가능한 실패
- C. 애플리케이션 business 정확성과 보장된 Region 복구
- D. Mirror component의 검사 가능한 설정 문제

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** 검사는 설정, credential, 인프라 진단에 도움이 됩니다. Failover 뒤 데이터 일관성, 안전한 쓰기 재시도, 용량, business 동작을 입증하지는 않습니다. 실제 workload 결과를 별도로 검증합니다.

</details>
