# EKS Hybrid Nodes Gateway 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

1. EKS Hybrid Nodes Gateway가 해결하는 문제는?
   - A) VPN/Direct Connect를 대체하여 컨트롤 플레인 연결을 제공
   - B) VPC와 Hybrid node 사이의 Gateway 관리 Pod 라우트와 VXLAN forwarding을 자동화
   - C) 하이브리드 노드를 위한 관리형 NAT 게이트웨이 제공
   - D) 클라우드와 온프레미스 간 모든 트래픽을 암호화

<details>
<summary>정답 보기</summary>

**정답: B) VPC와 Hybrid node 사이의 Gateway 관리 Pod 라우트와 VXLAN forwarding을 자동화**

**설명:**
Gateway는 aggregate VPC Pod-CIDR 라우트와 로컬 VXLAN forwarding 상태를 관리합니다. 승인된 private 연결에서 Gateway와 Hybrid node IP 사이의 underlay 라우팅은 여전히 필요합니다. Route table 소유권·반환 경로·보안 규칙을 검토해야 하며 모든 수동 네트워크 작업이 없어지는 것은 아닙니다. 제거 시 AWS 라우트가 자동 삭제되지도 않습니다.

</details>

---

2. 게이트웨이의 고가용성은 어떻게 유지되는가?
   - A) 여러 게이트웨이 간 로드 밸런싱을 통한 Active-Active
   - B) Kubernetes Lease 기반 리더 선출을 사용하는 2개 Pod Deployment
   - C) 자동 페일오버를 제공하는 AWS 관리형 이중화
   - D) Route 53 헬스 체크를 사용한 Multi-AZ 배포

<details>
<summary>정답 보기</summary>

**정답: B) Kubernetes Lease 기반 리더 선출을 사용하는 2개 Pod Deployment**

**설명:**
Chart 기본값은 2 replicas이며 필수 host anti-affinity와 선호 AZ anti-affinity를 사용합니다. 두 replica 모두 로컬 터널 엔트리를 유지하고 리더만 VPC 라우트와 CiliumVTEPConfig를 변경합니다. Lease 만료·라우트 교체·Cilium 반영·앱 복구 중 트래픽 중단이 생길 수 있습니다. Standby 증설은 처리량을 분산하지 않으며 PDB가 리더 또는 standby 교체 순서를 보장하지 않습니다.

</details>

---

3. 게이트웨이 아키텍처에서 CiliumVTEPConfig의 역할은?
   - A) 하이브리드 노드의 Cilium 네트워크 정책을 설정
   - B) 게이트웨이 IP를 원격 VTEP로 등록하여 하이브리드 노드의 Cilium이 VPC 방향 트래픽을 게이트웨이의 VXLAN 터널로 전달
   - C) 클러스터 전체의 Cilium 버전 업그레이드를 관리
   - D) VXLAN 터널의 암호화 키를 제공

<details>
<summary>정답 보기</summary>

**정답: B) 게이트웨이 IP를 원격 VTEP로 등록하여 하이브리드 노드의 Cilium이 VPC 방향 트래픽을 게이트웨이의 VXLAN 터널로 전달**

**설명:**
Gateway 1.0.2는 cilium.io/v2의 hybrid-gateway 객체를 관리합니다. spec.endpoints entry에는 name·tunnelEndpoint·cidr·mac이 들어가며 현재 리더 node IP와 실제 VXLAN 인터페이스 MAC을 사용합니다. 암호화 key 리소스가 아니며 VNI도 해당 CRD 필드가 아닙니다.

</details>

---

4. Hybrid Nodes Gateway 사용을 위한 CNI 전제 조건은?
   - A) 클라우드와 하이브리드 노드 모두 아무 CNI 가능
   - B) 클라우드 노드에 Cilium, 하이브리드 노드에 VPC CNI
   - C) AWS 유지 관리 Cilium의 VTEP 활성화·L7 비활성화와 cloud node 유형에 맞는 네트워킹
   - D) 클라우드와 하이브리드 노드 모두 VPC CNI

<details>
<summary>정답 보기</summary>

**정답: C) AWS 유지 관리 Cilium의 VTEP 활성화·L7 비활성화와 cloud node 유형에 맞는 네트워킹**

**설명:**
Gateway VTEP 최소 버전을 충족하는 AWS 유지 관리 Cilium에서 vtep.enabled=true·l7Proxy=false를 사용합니다. Cilium Ingress/Gateway API L7 기능은 동일 구성에 함께 적용할 수 없습니다. aws-node를 사용하는 관리형/자체 관리 cloud node는 Hybrid endpoint로 향하는 ClusterIP 트래픽을 위해 Hybrid Pod CIDR을 SNAT에서 제외해야 합니다. Auto Mode는 내장 네트워킹을 제공하므로 해당 노드용 aws-node DaemonSet을 설치·설정하지 않습니다. 직접 Pod IP 테스트만으로 ClusterIP 동작을 검증할 수 없습니다.

</details>

---

5. 게이트웨이가 사용하는 VXLAN 구성은?
   - A) VNI 1, UDP 포트 4789 (표준 VXLAN)
   - B) VNI 2, UDP 포트 8472 (Cilium 기본값)
   - C) VNI 100, UDP 포트 6081 (Geneve)
   - D) VNI 0, UDP 포트 443 (HTTPS 캡슐화)

<details>
<summary>정답 보기</summary>

**정답: B) VNI 2, UDP 포트 8472 (Cilium 기본값)**

**설명:**
기본 인터페이스는 hybrid_vxlan0, VNI는 2, UDP 포트는 8472입니다. 1.0.2는 이 인터페이스에 IP를 할당하지 않습니다. Hybrid node internal IP와 Pod CIDR을 이용한 결정적 MAC·FDB·neighbor·onlink route를 설치합니다. 양방향 underlay UDP 경로를 허용해야 합니다. VXLAN 캡슐화는 트래픽 암호화를 제공하지 않습니다.

</details>

---

6. 게이트웨이의 VPC 라우팅 관리 방식은?
   - A) BGP를 사용하여 VPC 라우터에 Pod 라우트를 광고
   - B) 하이브리드 Pod CIDR을 활성 게이트웨이의 기본 ENI로 가리키는 VPC 라우트 테이블 엔트리를 자동 생성 및 관리
   - C) VPC 메인 라우트 테이블에 NAT 규칙을 추가
   - D) Transit Gateway 라우트 테이블을 구성

<details>
<summary>정답 보기</summary>

**정답: B) 하이브리드 Pod CIDR을 활성 게이트웨이의 기본 ENI로 가리키는 VPC 라우트 테이블 엔트리를 자동 생성 및 관리**

**설명:**
리더 setup은 설정한 aggregate podCIDRs 라우트를 생성/교체한 다음 CiliumVTEPConfig를 갱신합니다. 각 replica는 CiliumNode 이벤트를 별도로 처리하여 노드별 로컬 터널 엔트리를 갱신합니다. Runtime 권한은 DescribeRouteTables·DescribeInstances·CreateRoute·ReplaceRoute이며 DeleteRoute를 호출하지 않습니다. Gateway를 종료한 뒤 운영자가 소유한 라우트만 검토하여 삭제하거나 복구해야 합니다.

</details>

---

7. EKS Hybrid Nodes Gateway의 요금 모델은?
   - A) 처리된 데이터 양 기반 시간당 요금
   - B) EKS Hybrid Nodes 요금에 포함 (하이브리드 노드당 $0.10/시간)
   - C) Gateway 소프트웨어 추가 요금은 없지만 EC2 등 인프라·트래픽 비용은 별도
   - D) 처음 3개월 무료, 이후 표준 AWS 네트워킹 요금

<details>
<summary>정답 보기</summary>

**정답: C) Gateway 소프트웨어 추가 요금은 없지만 EC2 등 인프라·트래픽 비용은 별도**

**설명:**
Gateway 소프트웨어 자체에 추가 요금은 없습니다. EC2·해당하는 Auto Mode 관리 요금·스토리지·cross-AZ 데이터 전송·private 연결·관측성 비용과 클러스터/Hybrid Nodes 비용은 별도입니다. 전체 비용은 배치와 트래픽에 따라 달라지므로 보편적인 비용 절감 보장은 아닙니다.

</details>

---

8. 수동 Pod 라우팅(BGP/정적 라우트) 대신 게이트웨이 방식을 선택해야 하는 경우는?
   - A) 클라우드와 온프레미스 Pod 간 최저 레이턴시가 필요한 경우
   - B) AWS Cilium/VTEP 구성과 추가 Gateway hop이 설계에 맞으며 Pod 라우트 관리를 단순화하려는 경우
   - C) 1000개 이상의 하이브리드 노드를 보유한 경우
   - D) 하이브리드 노드에서 Cilium이 아닌 CNI를 사용하는 경우

<details>
<summary>정답 보기</summary>

**정답: B) AWS Cilium/VTEP 구성과 추가 Gateway hop이 설계에 맞으며 Pod 라우트 관리를 단순화하려는 경우**

**설명:**
필수 AWS Cilium/VTEP 구성과 active-standby 추가 hop이 설계에 맞을 때 Pod 라우트 관리를 단순화할 수 있습니다. Webhook·ALB/NLB target에는 별도 라우팅·반환 경로·remote Pod 설정·health check·보안 규칙이 필요합니다. 수동으로 라우팅 가능한 Pod network도 이 경로를 지원할 수 있습니다. 기존 BGP/static routing 또는 다른 CNI/L7 요구 사항에 따라 다른 방식이 적합할 수 있습니다.

</details>
