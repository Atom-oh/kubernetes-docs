# Calico EKS 통합 퀴즈

> **관련 문서**: [EKS Integration](../../../networking/calico/08-eks-integration.md)
> **마지막 업데이트**: 2026년 9월 12일

## 퀴즈

1. 이 문서의 일반 EC2 Linux VPC CNI + Calico 구성에서 올바른 역할 분리는?
   - A) VPC CNI는 정책, Calico는 VPC IP 할당 담당
   - B) VPC CNI는 Pod 네트워킹, Calico는 정책 적용 담당
   - C) 두 CNI가 각각 모든 Pod 인터페이스를 독립 설정
   - D) Calico가 AWS 관리 EKS 컨트롤 플레인을 교체

<details>
<summary>정답 보기</summary>

**정답: B) VPC CNI는 Pod 네트워킹, Calico는 정책 적용 담당**

**설명:**
VPC CNI가 ENI, Pod IP 할당, 연결을 관리하고 Calico가 정책 규칙을 설정합니다. 이 문서는 Iptables와 kube-proxy를 유지하며 다른 데이터플레인은 별도 계획이 필요합니다.

</details>

2. EKS에 Calico를 설치하는 방법에 대한 올바른 설명은?
   - A) VPC CNI 네트워크 정책을 켜면 Calico가 설치됨
   - B) 버전을 고정한 Tigera Operator를 매니페스트 또는 해당 Helm 차트로 설치
   - C) 모든 EKS 클러스터에 AWS 지원 calico 애드온이 존재
   - D) Helm rollback은 항상 Calico CRD와 데이터 마이그레이션을 복구

<details>
<summary>정답 보기</summary>

**정답: B) 버전을 고정한 Tigera Operator를 매니페스트 또는 해당 Helm 차트로 설치**

**설명:**
Helm 차트는 Tigera Operator를 설치합니다. AWS VPC CNI 정책은 별도 구현입니다. Marketplace/커뮤니티 제품은 실제 카탈로그와 지원 주체를 확인하고 하나의 설치 소유 경로를 사용해야 합니다.

</details>

3. 현재 AWS 네이티브 네트워크 정책 안내와 일치하는 설명은?
   - A) 모든 현재 정책 기능이 EKS 1.14에서 도입됨
   - B) VPC CNI 1.21 이상과 문서화된 플랫폼/커널 조건에서 표준·관리자 정책을 지원
   - C) 네이티브 정책은 영구적으로 네임스페이스 정책만 지원
   - D) 네이티브 정책과 Calico가 같은 엔드포인트에 항상 함께 적용되어야 함

<details>
<summary>정답 보기</summary>

**정답: B) VPC CNI 1.21 이상과 문서화된 플랫폼/커널 조건에서 표준·관리자 정책을 지원**

**설명:**
표준 지원의 시작은 EKS 1.14가 아닌 VPC CNI 1.14입니다. 현재 AWS는 VPC CNI 1.21 이상, 호환 EKS/platform, Linux 커널 5.10 이상을 조건으로 NetworkPolicy와 AWS ClusterNetworkPolicy를 설명합니다. Calico와는 다른 API입니다.

</details>

4. EKS Fargate의 네트워크 정책 제약으로 올바른 것은?
   - A) Fargate에는 네트워킹이 없음
   - B) Fargate Pod 내부에는 Calico 노드 에이전트 정책과 VPC CNI 네이티브 정책이 적용되지 않음
   - C) kubernetesProvider를 EKS로 설정하면 모든 Calico 기능 지원
   - D) Fargate는 IPv6만 지원

<details>
<summary>정답 보기</summary>

**정답: B) Fargate Pod 내부에는 Calico 노드 에이전트 정책과 VPC CNI 네이티브 정책이 적용되지 않음**

**설명:**
Fargate에서는 이 노드 에이전트를 실행할 수 없습니다. Security Groups for Pods는 별도 제어입니다. Fargate와 연결하는 EC2 엔드포인트에 Calico 정책을 적용할 수는 있지만 Fargate 내부 적용을 뜻하지는 않습니다.

</details>

5. 이 구성에서 AWS IAM 권한은 어떻게 부여해야 하는가?
   - A) 모든 calico-node에 광범위한 EC2 Describe와 CloudWatch 권한 부여
   - B) 실제로 AWS API를 호출하는 컴포넌트에 부여하며 기본 Calico 정책은 Kubernetes RBAC 사용
   - C) Installation의 nodeMetadata 필드가 IRSA 역할 생성
   - D) IAM 정책 생성만으로 모든 ServiceAccount에 자동 연결

<details>
<summary>정답 보기</summary>

**정답: B) 실제로 AWS API를 호출하는 컴포넌트에 부여하며 기본 Calico 정책은 Kubernetes RBAC 사용**

**설명:**
VPC CNI에는 자체 AWS 권한이 필요합니다. Exporter나 클라우드 통합에는 별도 역할이 필요할 수 있습니다. 해당 컴포넌트가 지원하는 IRSA/Pod Identity 설정을 사용하며 기본 policy-only Calico에 광범위한 AWS 역할은 필요하지 않습니다.

</details>

6. Security Groups for Pods와 Calico 정책을 함께 적용할 때 AWS가 요구하는 것은?
   - A) POD_SECURITY_GROUP_ENFORCING_MODE=strict만 설정
   - B) VPC CNI 1.11 이상과 POD_SECURITY_GROUP_ENFORCING_MODE=standard 및 나머지 기능 전제
   - C) EC2 인스턴스 레이블만 추가
   - D) Security Groups for Pods를 EKS Auto Mode에서도 사용

<details>
<summary>정답 보기</summary>

**정답: B) VPC CNI 1.11 이상과 POD_SECURITY_GROUP_ENFORCING_MODE=standard 및 나머지 기능 전제**

**설명:**
strict 모드의 해당 Pod에는 Calico 정책이 적용되지 않습니다. 지원 인스턴스/branch ENI를 확인하고 모드 변경 후 해당 Pod를 재생성해야 합니다. 일반 외부 SNAT를 사용하는 standard 모드에서는 VPC 외부 트래픽에 노드 Security Group이 사용됩니다.

</details>

7. EKS/Calico 업그레이드의 올바른 접근은?
   - A) 호환성과 무관하게 항상 EKS 다음 Calico 업그레이드
   - B) 전환 전후 호환 Calico 버전을 선택하고 EKS·노드·애드온·CRD 요건 검토
   - C) EKS가 모든 타사 컴포넌트를 자동 업그레이드·롤백
   - D) 이전 operator 적용만으로 안전한 다운그레이드 보장

<details>
<summary>정답 보기</summary>

**정답: B) 전환 전후 호환 Calico 버전을 선택하고 EKS·노드·애드온·CRD 요건 검토**

**설명:**
전환 전후 양쪽 호환성을 확인해야 합니다. 현재 EKS에는 직전 마이너 버전으로의 조건부 7일 롤백 기간이 있지만 Calico와 EKS 애드온은 자동 복구되지 않습니다. 복구에도 호환성과 준비 상태 검사가 필요합니다.

</details>

8. 검토한 Installation에서 사용하는 provider 값은?
   - A) AWS
   - B) EKS
   - C) AmazonEKS
   - D) None

<details>
<summary>정답 보기</summary>

**정답: B) EKS**

**설명:**
Installation에서는 `spec.kubernetesProvider: EKS`, Helm values에서는 `installation.kubernetesProvider: EKS`를 사용합니다. Provider 설정 선택이며 모든 노드 유형, CNI, 데이터플레인, 버전의 지원을 보장하는 것은 아닙니다.

</details>

9. Amazon VPC CNI에 네트워킹을 위임하는 CNI type은?
   - A) Calico
   - B) AmazonVPC
   - C) AWSCNI
   - D) VPC

<details>
<summary>정답 보기</summary>

**정답: B) AmazonVPC**

**설명:**
Installation의 `spec.cni.type: AmazonVPC`를 사용합니다. Calico policy-only에는 문서화된 Pod IP annotation/RBAC와 단일 정책 엔진도 필요하며 `bgp: Disabled`만으로 CNI가 선택되지 않습니다.

</details>

10. backend selector와 TCP 포트를 하나의 destination 매핑에 두어야 하는 이유는?
   - A) YAML은 모든 필드를 반복해야 함
   - B) destination 키 중복으로 selector가 사라져 의도하지 않은 엔드포인트를 허용할 수 있음
   - C) 포트가 backend Pod 레이블을 자동 의미
   - D) 중복 키는 Kubernetes에서 항상 오류 처리됨

<details>
<summary>정답 보기</summary>

**정답: B) destination 키 중복으로 selector가 사라져 의도하지 않은 엔드포인트를 허용할 수 있음**

**설명:**
일부 YAML 파서는 중복 키의 마지막 값만 유지합니다. selector와 ports를 함께 두고 검증에서 중복 키를 거부하며 허용·거부 트래픽을 모두 테스트하세요. 노드 Ready는 올바른 정책 적용의 근거가 아닙니다.

</details>
