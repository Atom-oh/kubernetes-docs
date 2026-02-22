# Calico EKS 통합 퀴즈

> **관련 문서**: [Calico EKS 통합](../../../networking/calico/08-eks-integration.md)
> **마지막 업데이트**: 2025년 2월 22일

## 퀴즈

1. EKS에서 VPC CNI + Calico 조합을 사용할 때 각 컴포넌트의 역할로 올바른 것은?
   - A) VPC CNI: Network Policy, Calico: Pod 네트워킹
   - B) VPC CNI: Pod 네트워킹, Calico: Network Policy
   - C) VPC CNI: BGP 라우팅, Calico: IP 할당
   - D) VPC CNI와 Calico 모두 동일한 역할 수행

<details>
<summary>정답 보기</summary>

**정답: B) VPC CNI: Pod 네트워킹, Calico: Network Policy**

**설명:**
EKS에서 VPC CNI + Calico 조합은 역할을 분리합니다. AWS VPC CNI는 Pod에 VPC 내 실제 IP를 할당하고 네트워킹을 담당하며, Calico는 Network Policy 적용을 담당합니다. 이 조합으로 AWS 네이티브 네트워킹의 장점과 Calico의 강력한 정책 기능을 함께 사용할 수 있습니다.

</details>

2. EKS에서 Calico를 설치하는 방법으로 지원되지 않는 것은?
   - A) EKS 애드온
   - B) Tigera Operator
   - C) Helm Chart
   - D) AWS CloudFormation 템플릿 (Calico 전용)

<details>
<summary>정답 보기</summary>

**정답: D) AWS CloudFormation 템플릿 (Calico 전용)**

**설명:**
Calico는 EKS 애드온, Tigera Operator, Helm Chart를 통해 설치할 수 있습니다. AWS CloudFormation에는 Calico 전용 템플릿이 없습니다. 권장되는 방법은 Tigera Operator를 사용한 설치이며, 이를 통해 Calico 컴포넌트의 라이프사이클을 자동으로 관리할 수 있습니다.

</details>

3. EKS v1.25+에서 도입된 네이티브 Network Policy 지원의 활성화 방법은?
   - A) Calico 설치
   - B) VPC CNI 애드온에서 enableNetworkPolicy 설정
   - C) kube-proxy 재시작
   - D) 별도 설정 없이 자동 활성화

<details>
<summary>정답 보기</summary>

**정답: B) VPC CNI 애드온에서 enableNetworkPolicy 설정**

**설명:**
EKS v1.25+에서는 VPC CNI 애드온 설정에서 `enableNetworkPolicy: "true"`를 지정하여 Kubernetes 표준 NetworkPolicy 지원을 활성화할 수 있습니다. 이 기능은 eBPF 기반으로 구현되어 있으며, 기본 NetworkPolicy만 필요한 경우 Calico 없이도 사용할 수 있습니다.

</details>

4. Fargate에서 Calico 사용 시 제한사항으로 올바른 것은?
   - A) 완전히 지원됨
   - B) Calico가 Fargate에서는 동작하지 않음 (Policy-only 모드 불가)
   - C) eBPF 모드만 지원
   - D) BGP만 지원

<details>
<summary>정답 보기</summary>

**정답: B) Calico가 Fargate에서는 동작하지 않음 (Policy-only 모드 불가)**

**설명:**
Fargate는 서버리스 컴퓨팅 환경으로, 호스트 노드에 직접 접근할 수 없습니다. Calico는 각 노드에 DaemonSet으로 배포되어 iptables/eBPF 규칙을 관리해야 하므로, Fargate Pod에는 Calico Network Policy를 적용할 수 없습니다. Fargate에서는 AWS Security Group을 사용해야 합니다.

</details>

5. EKS에서 Calico에 IRSA(IAM Roles for Service Accounts) 구성이 필요한 경우는?
   - A) 모든 경우에 필수
   - B) AWS API를 호출하는 Calico 기능 사용 시 (예: AWS 통합 기능)
   - C) Network Policy 사용 시
   - D) IRSA는 Calico와 관련 없음

<details>
<summary>정답 보기</summary>

**정답: B) AWS API를 호출하는 Calico 기능 사용 시 (예: AWS 통합 기능)**

**설명:**
기본 Network Policy 기능만 사용하는 경우 IRSA가 필요하지 않습니다. 그러나 Calico Enterprise의 AWS 통합 기능이나 CloudWatch 로그 전송 등 AWS API를 호출하는 기능을 사용할 때는 적절한 IAM 권한이 필요하며, IRSA를 통해 안전하게 권한을 부여할 수 있습니다.

</details>

6. AWS Security Group과 Calico Network Policy의 차이점으로 올바른 것은?
   - A) 둘 다 Pod 레벨에서 동작
   - B) Security Group은 ENI 레벨, Calico는 Pod 레벨에서 동작
   - C) Security Group이 더 세분화된 제어 제공
   - D) Calico가 AWS 리소스에 더 적합

<details>
<summary>정답 보기</summary>

**정답: B) Security Group은 ENI 레벨, Calico는 Pod 레벨에서 동작**

**설명:**
AWS Security Group은 ENI(Elastic Network Interface) 레벨에서 동작하여 노드나 Pod 그룹 단위로 트래픽을 제어합니다. Calico Network Policy는 개별 Pod 레벨에서 레이블 기반으로 세분화된 제어가 가능합니다. 두 가지를 조합하여 계층화된 보안을 구현하는 것이 권장됩니다.

</details>

7. EKS 클러스터 업그레이드 시 Calico 관련 고려사항이 아닌 것은?
   - A) Calico 버전 호환성 확인
   - B) Network Policy 백업
   - C) VPC CIDR 변경
   - D) 롤링 업데이트 중 정책 연속성 확인

<details>
<summary>정답 보기</summary>

**정답: C) VPC CIDR 변경**

**설명:**
EKS 업그레이드 시 VPC CIDR은 변경되지 않으며 Calico와 직접 관련이 없습니다. 업그레이드 전에는 Calico 버전이 새 EKS 버전과 호환되는지 확인하고, Network Policy를 백업하며, 롤링 업데이트 중 정책이 연속적으로 적용되는지 검증해야 합니다.

</details>

8. EKS용 Calico Helm 설치에서 installation.kubernetesProvider의 올바른 값은?
   - A) AWS
   - B) EKS
   - C) AmazonEKS
   - D) Kubernetes

<details>
<summary>정답 보기</summary>

**정답: B) EKS**

**설명:**
Helm values에서 `installation.kubernetesProvider: EKS`를 설정하면 Calico가 EKS 환경에 최적화된 설정으로 배포됩니다. 이 설정은 EKS 특화 기능 활성화와 VPC CNI와의 올바른 통합을 보장합니다.

</details>

9. EKS에서 VPC CNI와 함께 Calico를 사용할 때 installation.cni.type의 올바른 값은?
   - A) Calico
   - B) AmazonVPC
   - C) AWSCNI
   - D) VPC

<details>
<summary>정답 보기</summary>

**정답: B) AmazonVPC**

**설명:**
`installation.cni.type: AmazonVPC`를 설정하면 Calico가 자체 CNI 대신 AWS VPC CNI를 네트워킹에 사용하고, Network Policy 적용만 담당합니다. 이를 "Policy-only 모드"라고 하며, AWS 네이티브 네트워킹을 유지하면서 Calico의 정책 기능을 사용할 수 있습니다.

</details>

10. Policy-only 모드에서 Calico가 담당하지 않는 것은?
    - A) Network Policy 적용
    - B) Pod IP 주소 할당
    - C) GlobalNetworkPolicy 적용
    - D) iptables/eBPF 규칙 관리

<details>
<summary>정답 보기</summary>

**정답: B) Pod IP 주소 할당**

**설명:**
Policy-only 모드에서는 Pod IP 할당과 네트워킹을 AWS VPC CNI가 담당합니다. Calico는 Network Policy, GlobalNetworkPolicy 적용과 이를 위한 iptables/eBPF 규칙 관리만 수행합니다. BGP와 IPAM 기능은 비활성화됩니다.

</details>
