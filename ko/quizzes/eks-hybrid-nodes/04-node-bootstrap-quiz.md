# EKS Hybrid Nodes 노드 부트스트랩 퀴즈

> **관련 문서**: [Node Bootstrap](../../eks-hybrid-nodes/04-node-bootstrap.md)
> **마지막 업데이트**: 2026년 9월 12일

### 1. Hybrid nodeadm의 역할은?

A. EKS 컨트롤 플레인 생성

B. aws/eks-hybrid 구현으로 Hybrid 노드 구성 요소 설치·초기화

C. 애플리케이션 Pod 스케줄링

D. CNI 컨트롤러 대체

<details>
<summary>정답 보기</summary>

**정답: B. aws/eks-hybrid 구현으로 Hybrid 노드 구성 요소 설치·초기화**

**설명:** EC2용 amazon-eks-ami nodeadm이 아닌 Hybrid 설치 프로그램을 사용합니다. init 전에 의존성을 설치하고 OS·런타임 소스를 선택하며 승인 바이너리를 검증합니다. 현재 SSM 신규 설치·업그레이드는 nodeadm1.0.19 이상이 필요합니다.

</details>

### 2. 일반적인 Hybrid NodeConfig의 클러스터 입력은?

A. 클러스터 이름·리전과 지원 자격 증명 공급자

B. VPC ID와 subnet ID만

C. 항상 수동 작성해야 하는 이름·엔드포인트·CA 세 필드

D. IAM 사용자 액세스 키와 비밀번호

<details>
<summary>정답 보기</summary>

**정답: A. 클러스터 이름·리전과 지원 자격 증명 공급자**

**설명:** 문서화된 Hybrid 설정은 spec.cluster.name/region과 spec.hybrid.ssm 또는 spec.hybrid.iamRolesAnywhere를 사용합니다. 준비한 Hybrid 역할이 클러스터 조회 권한을 제공합니다. 모든 일반 초기화에 수동 복사한 원본 PEM CA가 필수라는 설명은 잘못입니다.

</details>

### 3. nodeadm이 지원하는 자격 증명 공급자 조합은?

A. IAM 사용자 키와 LDAP

B. 정적 Kubernetes 토큰과 로컬 비밀번호

C. SSM hybrid activation과 IAM Roles Anywhere

D. EC2 instance profile과 kubeconfig 비밀번호

<details>
<summary>정답 보기</summary>

**정답: C. SSM hybrid activation과 IAM Roles Anywhere**

**설명:** ssm 또는 iam-ra 중 하나를 선택합니다. SSM은 spec.hybrid.ssm 아래 activationCode·activationId, IAM Roles Anywhere는 spec.hybrid.iamRolesAnywhere를 사용합니다. 둘 다 준비한 Hybrid 역할과 클러스터 접근 권한이 필요합니다.

</details>

### 4. kubelet 설정 필드가 아닌 것은?

A. maxPods

B. clusterDNS

C. clusterDomain

D. podScheduler

<details>
<summary>정답 보기</summary>

**정답: D. podScheduler**

**설명:** podScheduler는 kubelet 설정 필드가 아니며 스케줄러는 컨트롤 플레인에서 실행됩니다. 이전 선택지 clusterCIDR도 kubelet 설정 필드가 아니어서 옛 문제는 정답이 모호했습니다. NodeConfig의 kubelet 설정은 CNI IPAM 계획을 대체하지 않습니다.

</details>

### 5. 자동화의 init-command-completed 기록이 증명하는 것은?

A. Node가 영구적으로 Ready임

B. 당시 init 명령과 로컬 검사가 완료되었으며 클러스터 readiness는 별도 확인 필요

C. 모든 이미지 풀과 자격 증명 갱신 시험 완료

D. 신원을 포함한 호스트 복제가 안전함

<details>
<summary>정답 보기</summary>

**정답: B. 당시 init 명령과 로컬 검사가 완료되었으며 클러스터 readiness는 별도 확인 필요**

**설명:** 기록을 호스트·설정·바이너리에 결합하고 중단 시 started 상태를 보존하며 알 수 없는 상태를 자동 재실행하지 않습니다. network-online.target과 RemainAfterExit는 AWS 접근이나 Node readiness 증거가 아닙니다.

</details>

### 6. Kubernetes API 서버 CA의 올바른 의미는?

A. 매 TLS handshake마다 kubelet 클라이언트 인증서를 자동 발급

B. 레지스트리 로그인 자격 증명

C. 서버 인증서 신뢰 검증에 사용하며 클라이언트 인증서 승인·발급은 별도

D. Hybrid IAM 역할 대체

<details>
<summary>정답 보기</summary>

**정답: C. 서버 인증서 신뢰 검증에 사용하며 클라이언트 인증서 승인·발급은 별도**

**설명:** 서버 호스트명과 CA 체인을 검증하며 curl -k를 신뢰 검사로 사용하지 않습니다. 클러스터 CA, 프라이빗 레지스트리 CA와 IAM Roles Anywhere 호스트 신원은 서로 다른 신뢰 용도입니다.

</details>

### 7. 조인 실패나 부분 초기화에 대한 적절한 대응은?

A. nodeadm status 후 즉시 uninstall --force

B. 제한된 비공개 kubelet 로그·nodeadm debug와 신원·네트워크 확인 후 기록된 상태 정리

C. 공유 클러스터의 Cilium CRD 모두 삭제

D. Node 객체를 삭제하면 SSM 등록도 취소되었다고 가정

<details>
<summary>정답 보기</summary>

**정답: B. 제한된 비공개 kubelet 로그·nodeadm debug와 신원·네트워크 확인 후 기록된 상태 정리**

**설명:** 확인한 CLI에는 nodeadm status가 아닌 nodeadm debug가 있습니다. Debug는 AWS·클러스터 서비스에 접근하므로 출력을 비공개로 보관합니다. Node 삭제는 kubelet 중지나 SSM 등록 취소가 아닙니다. Uninstall은 통제된 제거 작업이며 일반 인증 오류 해결책이 아닙니다.

</details>

### 8. Bottlerocket Pod Identity 설명으로 올바른 것은?

A. Ubuntu와 동일한 NodeConfig·nodeadm 사용

B. settings.hybrid.ssm만으로 문서화된 전체 bootstrap 구성 완료

C. Bottlerocket1.39.0 이상에서 공급자 bootstrap credentials-file 지원과 hybrid-bottlerocket agent DaemonSet 사용

D. Base64 user data가 개인 키를 암호화

<details>
<summary>정답 보기</summary>

**정답: C. Bottlerocket1.39.0 이상에서 공급자 bootstrap credentials-file 지원과 hybrid-bottlerocket agent DaemonSet 사용**

**설명:** Bottlerocket은 별도 settings·bootstrap-container 입력을 사용합니다. 에이전트 호환성 최소값은 v1.3.7-eksbuild.2이며 임시 자격 증명 경로는 /var/eks-hybrid/.aws/credentials입니다. 현재 호환되는 애드온을 선택하고 user data를 보호합니다. 인코딩은 암호화가 아닙니다.

</details>

### 9. 범위를 올바르게 정한 Cilium 수명 주기 작업은?

A. 기존 cluster-pool CIDR을 제자리 변경

B. Hybrid 범위 preflight를 수행하고 DaemonSet 커버리지·검증 Deployment readiness 확인 후 업그레이드

C. 기존 Helm 값을 검토 없이 항상 재사용

D. 노드 하나를 고치려고 cilium이 포함된 모든 CRD 삭제

<details>
<summary>정답 보기</summary>

**정답: B. Hybrid 범위 preflight를 수행하고 DaemonSet 커버리지·검증 Deployment readiness 확인 후 업그레이드**

**설명:** Preflight는 별도 node selector를 사용합니다. 기존 pool 항목과 mask size는 변경하지 않으며, 확장은 EKS·라우팅 변경을 함께 검토한 새 pool 항목을 추가할 수 있습니다. CNI·CRD 제거는 소유자가 통제할 중단 작업입니다.

</details>

### 10. 확인한 릴리스에서 nodeadm uninstall --force의 의미는?

A. /var/lib/kubelet을 포함한 모든 mount 경로 제거 보장

B. 일반 확인 우회이며 drain 대체

C. 추가 기본 경로를 제거하지만 v1.0.9 이후 /var/lib/kubelet 보호 동작은 유지

D. 새 대체 노드 자동 검증

<details>
<summary>정답 보기</summary>

**정답: C. 추가 기본 경로를 제거하지만 v1.0.9 이후 /var/lib/kubelet 보호 동작은 유지**

**설명:** Mount된 kubelet 경로를 무조건 삭제하지 않습니다. 워크로드를 비우고 데이터·공급자·CNI 정리를 검토하며 복구 증거를 보존합니다. 승인한 재설치에는 제거 후 init만이 아닌 install → config check → init이 필요합니다.

</details>

