# Amazon VPC CNI 퀴즈

2026년 9월 11일 [VPC CNI 본문](../../networking/01-vpc-cni.md)과 공식 근거에 맞춰 검토했습니다.

## 1. 표준 EKS Linux EC2 노드에서 IPAMD의 역할은?

- A. 모든 Pod의 DNS 애플리케이션 설정 관리
- B. Pod 네트워킹용 일반 ENI/IP 할당 pool 유지
- C. 네트워크 정책 컨트롤러 대체
- D. 모든 노드 간 트래픽 암호화

<details>
<summary>정답 보기</summary>

**정답: B. Pod 네트워킹용 일반 ENI/IP 할당 pool 유지**

컨테이너 런타임이 CNI 바이너리를 호출하고 바이너리가 주소를 요청하여 Pod sandbox를 설정합니다. IPAMD는 관련 주소 pool을 유지합니다. Windows, Fargate, Auto Mode는 관리 경로가 다릅니다.

</details>

## 2. IPv4 secondary-IP와 prefix 모드의 할당 차이는?

- A. Secondary-IP만 IPv6 지원
- B. Secondary-IP는 개별 주소, IPv4 prefix는 주소 16개의 /28 블록 할당
- C. Prefix 모드는 kubelet Pod 상한 제거
- D. Prefix 모드는 고갈된 서브넷에 새 공간 생성

<details>
<summary>정답 보기</summary>

**정답: B. Secondary-IP는 개별 주소, IPv4 prefix는 주소 16개의 /28 블록 할당**

Prefix에는 지원 하드웨어와 연속 블록이 필요합니다. 서브넷 공간을 사용하고 warm target이 미사용 주소를 예약할 수 있습니다. IPv6는 /80을 사용하며 EKS는 dual-stack Pod·Service를 제공하지 않습니다.

</details>

## 3. 과거 m5.large secondary-IPv4 bootstrap 공식에서 29가 나오는 계산은?

- A. Kubernetes가 모든 노드를 항상 29개로 제한
- B. 3 × (10 − 1) + 2 = 29
- C. 3 × 10 − 3 = 29
- D. 모든 서브넷의 크기가 29

<details>
<summary>정답 보기</summary>

**정답: B. 3 × (10 − 1) + 2 = 29**

IPv4 슬롯 10개인 ENI가 3개이고 각각의 primary 슬롯을 제외하면 일반 보조 주소는 27개입니다. 과거 공식은 host-network 시스템 Pod 2개를 더합니다. Prefix, SGPP, kubelet 상한, 리소스에 따라 해석이 달라지므로 현재 모든 환경의 용량 한계는 아닙니다.

</details>

## 4. WARM_IP_TARGET이 지정하는 것은?

- A. Pod 수의 강제 최대값
- B. 일반 할당에 사용할 여유 주소 수의 목표
- C. 클러스터 전체 주소 quota
- D. 주소 TTL

<details>
<summary>정답 보기</summary>

**정답: B. 일반 할당에 사용할 여유 주소 수의 목표**

MINIMUM_IP_TARGET은 전체 할당 주소의 하한입니다. IP target은 warm ENI/prefix 전략보다 우선하고 prefix 단위 할당은 계속 적용됩니다. 측정한 수요·변경 빈도·주소 공간·API 동작으로 값을 정합니다.

</details>

## 5. EKS 네이티브 네트워크 정책의 올바른 설명은?

- A. VPC CNI가 내부적으로 Calico 실행
- B. 표준 eBPF 정책은 1.14에서 도입되었지만 현재 플랫폼·버전·활성화 조건도 필요
- C. Windows와 Fargate까지 자동으로 포함
- D. 켜기만 하면 모든 독립 Pod에 안정적으로 적용 보장

<details>
<summary>정답 보기</summary>

**정답: B. 표준 eBPF 정책은 1.14에서 도입되었지만 현재 플랫폼·버전·활성화 조건도 필요**

검토한 1.23 구성은 설정된 정책 컨트롤러와 aws-eks-nodeagent를 사용합니다. 현재 EKS 안내에는 EC2 Linux, 컨트롤러 관리 Pod, Service·컨테이너 포트 조건이 있습니다. Standard 시작 모드는 규칙 해석 동안 허용하며 strict 시작 동작은 별도로 선택합니다.

</details>

## 6. ENIConfig custom networking의 역할은?

- A. DNS 서버 대체
- B. 노드 기본 구성과 다른 선택 서브넷·보안 그룹에서 Pod 주소 할당
- C. CIDR 추가 후 기존 Pod 자동 이동
- D. 중복 경로 자동 제거

<details>
<summary>정답 보기</summary>

**정답: B. 노드 기본 구성과 다른 선택 서브넷·보안 그룹에서 Pod 주소 할당**

실제 같은 AZ의 리소스를 준비하고 custom networking을 켠 뒤 의도한 노드 레이블·어노테이션으로 ENIConfig를 선택합니다. 명시적 어노테이션이 레이블보다 우선합니다. CIDR·서브넷 생성만으로 기존 Pod 이동이나 모든 경로·권한이 준비되지는 않습니다.

</details>

## 7. 지원 EC2 노드의 SGPP에서 trunk·branch 인터페이스의 역할은?

- A. Trunk는 항상 primary eth0
- B. 컨트롤러가 추가 trunk ENI를 붙이고 선택 Pod의 branch 인터페이스를 연결
- C. 각각 IPv4와 IPv6를 의미
- D. Prefix delegation으로 branch Pod 상한이 16배 증가

<details>
<summary>정답 보기</summary>

**정답: B. 컨트롤러가 추가 trunk ENI를 붙이고 선택 Pod의 branch 인터페이스를 연결**

Trunk는 primary ENI가 아닌 추가 인터페이스입니다. 지원 인스턴스, 컨트롤러·IAM, 실제 SG 규칙이 필요합니다. Fargate는 별도 관리 경로를 따릅니다. Windows·Auto Mode SGPP는 미지원이고 EKS 문서는 조건에 따른 IPv6 지원을 명시합니다.

</details>

## 8. IP 고갈에 대한 기본 대응으로 부적절한 것은?

- A. Prefix delegation 검토 전에 연속 공간·하드웨어 확인
- B. 용량 부족 시 CIDR·서브넷 추가와 워크로드 전환 계획
- C. 일반 Pod 주소 할당을 피하려고 모든 워크로드를 hostNetwork로 전환
- D. Custom networking과 측정 기반 warm target 검토

<details>
<summary>정답 보기</summary>

**정답: C. 일반 Pod 주소 할당을 피하려고 모든 워크로드를 hostNetwork로 전환**

모든 워크로드를 hostNetwork로 바꾸면 격리·포트 동작이 달라져 범용 용량 해결책이 아닙니다. 주소 고갈, prefix 단편화, ENI 한계, kubelet 용량, API 오류를 구분합니다. Prefix delegation도 부족한 서브넷 주소를 새로 만들지는 못합니다.

</details>
