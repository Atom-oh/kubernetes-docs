# EKS Hybrid Nodes Gateway 퀴즈

1. EKS Hybrid Nodes Gateway가 해결하는 문제는?
   - A) VPN/Direct Connect를 대체하여 컨트롤 플레인 연결을 제공
   - B) VXLAN 터널을 사용하여 VPC와 하이브리드 노드 간 Pod 네트워킹을 자동화하여 수동 Pod 라우팅을 제거
   - C) 하이브리드 노드를 위한 관리형 NAT 게이트웨이 제공
   - D) 클라우드와 온프레미스 간 모든 트래픽을 암호화

<details>
<summary>정답 보기</summary>

**정답: B) VXLAN 터널을 사용하여 VPC와 하이브리드 노드 간 Pod 네트워킹을 자동화하여 수동 Pod 라우팅을 제거**

**설명:**
EKS Hybrid Nodes Gateway는 EC2 기반 게이트웨이 노드와 Cilium 기반 하이브리드 노드 간 VXLAN 터널을 생성하고, VPC 라우트 테이블 엔트리를 자동으로 관리합니다. 이를 통해 수동 BGP 설정, 정적 라우트 관리, 온프레미스 Pod 네트워크의 VPC 라우팅 설정이 불필요해집니다. 단, 기본 노드 연결을 위한 VPN/Direct Connect는 여전히 필요합니다.

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
게이트웨이는 레이블이 지정된 EC2 노드에서 2개 Pod Deployment로 실행됩니다. Kubernetes Lease 기반 리더 선출을 통해 활성 Pod를 결정하며, 리더만 VPC 라우트 테이블 엔트리와 CiliumVTEPConfig CRD를 관리합니다. 리더가 실패하면 대기 Pod로 리더십이 이전되고, VPC 라우트가 새 리더의 ENI를 가리키도록 업데이트됩니다.

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
게이트웨이 리더가 CiliumVTEPConfig 리소스를 생성하면, 각 온프레미스 하이브리드 노드의 Cilium 에이전트가 이를 읽어 게이트웨이 IP를 원격 VTEP(VXLAN Tunnel Endpoint)로 등록합니다. 이를 통해 Cilium은 VPC 방향 트래픽을 직접 라우팅하지 않고 게이트웨이의 VXLAN 터널을 통해 전송하도록 처리합니다.

</details>

---

4. Hybrid Nodes Gateway 사용을 위한 CNI 전제 조건은?
   - A) 클라우드와 하이브리드 노드 모두 아무 CNI 가능
   - B) 클라우드 노드에 Cilium, 하이브리드 노드에 VPC CNI
   - C) 하이브리드 노드에 Cilium(VTEP 활성화), 클라우드 노드에 VPC CNI
   - D) 클라우드와 하이브리드 노드 모두 VPC CNI

<details>
<summary>정답 보기</summary>

**정답: C) 하이브리드 노드에 Cilium(VTEP 활성화), 클라우드 노드에 VPC CNI**

**설명:**
게이트웨이는 (1) 하이브리드 노드에 VTEP 지원이 활성화된 EKS 버전 Cilium CNI가 필요합니다 (VXLAN 터널링 참여를 위해). (2) 클라우드 노드에는 AWS VPC CNI가 필요합니다 (게이트웨이가 VPC 네이티브 라우팅에 의존하여 VPC와 VXLAN 터널 간 트래픽을 전달하므로). 두 CNI가 게이트웨이를 통해 협력하여 원활한 Pod 간 통신을 가능하게 합니다.

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
게이트웨이는 `hybrid_vxlan0`이라는 VXLAN 인터페이스를 VNI(VXLAN Network Identifier) 2와 UDP 포트 8472(Cilium 기본 VXLAN 포트)로 생성합니다. 각 하이브리드 노드에 대해 FDB(Forwarding Database) 엔트리, ARP 엔트리, 라우트를 프로그래밍하여 터널을 설정합니다. 보안 그룹과 온프레미스 방화벽에서 UDP 8472 양방향 허용이 필요합니다.

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
게이트웨이의 노드 컨트롤러가 CiliumNode 객체를 감시하며, 하이브리드 노드가 클러스터에 참여하거나 떠날 때 VXLAN 터널을 자동으로 추가/제거합니다. 리더 Pod는 VPC 라우트 테이블 엔트리를 유지하여 각 하이브리드 Pod CIDR을 활성 게이트웨이 인스턴스의 기본 ENI로 라우팅합니다. 이를 위해 IAM 역할에 ec2:DescribeRouteTables, ec2:CreateRoute, ec2:ReplaceRoute 권한이 필요합니다.

</details>

---

7. EKS Hybrid Nodes Gateway의 요금 모델은?
   - A) 처리된 데이터 양 기반 시간당 요금
   - B) EKS Hybrid Nodes 요금에 포함 (하이브리드 노드당 $0.10/시간)
   - C) 게이트웨이 자체는 추가 요금 없음, 게이트웨이 노드용 EC2 인스턴스 비용 발생
   - D) 처음 3개월 무료, 이후 표준 AWS 네트워킹 요금

<details>
<summary>정답 보기</summary>

**정답: C) 게이트웨이 자체는 추가 요금 없음, 게이트웨이 노드용 EC2 인스턴스 비용 발생**

**설명:**
EKS Hybrid Nodes Gateway는 추가 요금 없이 제공되며 오픈소스(GitHub에서 사용 가능)입니다. 다만 게이트웨이가 VPC 내 EC2 인스턴스에서 실행되므로 게이트웨이 노드에 대한 표준 EC2 인스턴스 비용이 발생합니다. 복잡한 BGP나 정적 라우팅 인프라를 직접 관리하는 것에 비해 비용 효율적인 솔루션입니다.

</details>

---

8. 수동 Pod 라우팅(BGP/정적 라우트) 대신 게이트웨이 방식을 선택해야 하는 경우는?
   - A) 클라우드와 온프레미스 Pod 간 최저 레이턴시가 필요한 경우
   - B) 운영을 단순화하고 온프레미스 Pod 네트워크를 라우팅 가능하게 만들 필요 없이 Webhook 통신과 AWS 서비스 통합을 활성화하려는 경우
   - C) 1000개 이상의 하이브리드 노드를 보유한 경우
   - D) 하이브리드 노드에서 Cilium이 아닌 CNI를 사용하는 경우

<details>
<summary>정답 보기</summary>

**정답: B) 운영을 단순화하고 온프레미스 Pod 네트워크를 라우팅 가능하게 만들 필요 없이 Webhook 통신과 AWS 서비스 통합을 활성화하려는 경우**

**설명:**
게이트웨이는 복잡한 네트워크 인프라 변경(BGP 설정, 정적 라우트 관리)을 피하고자 할 때 이상적입니다. 자동으로 (1) 하이브리드 노드의 Webhook에 대한 컨트롤 플레인 통신, (2) 클라우드와 온프레미스 간 Pod-to-Pod 트래픽, (3) AWS 서비스(ALB, NLB, Prometheus)의 하이브리드 Pod 연결을 활성화합니다. 이미 BGP 인프라가 있거나 게이트웨이를 통한 추가 홉을 최소화해야 하는 경우에는 수동 BGP 방식이 더 적합할 수 있습니다.

</details>
