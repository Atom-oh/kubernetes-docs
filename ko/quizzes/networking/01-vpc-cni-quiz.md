# Amazon VPC CNI 퀴즈

다음 문제들은 Amazon VPC CNI에 대한 이해도를 테스트합니다.

---

1. VPC CNI에서 IPAMD(L-IPAM Daemon)의 주요 역할은 무엇인가요?
   - A) Pod의 DNS 설정을 관리
   - B) ENI와 IP 주소를 사전 할당하고 관리
   - C) Network Policy를 적용
   - D) 노드 간 트래픽을 암호화

<details>
<summary>정답 보기</summary>

**정답: B) ENI와 IP 주소를 사전 할당하고 관리**

**설명:**
IPAMD(L-IPAM Daemon)는 각 노드에서 실행되는 데몬으로, ENI(Elastic Network Interface)를 관리하고 IP 주소를 사전 할당하여 Pod가 생성될 때 빠르게 IP를 할당할 수 있도록 합니다. CNI Binary는 kubelet이 호출하며 IPAMD에서 IP를 받아 Pod 네트워크 네임스페이스를 설정합니다.

</details>

---

2. Secondary IP 모드와 Prefix Delegation 모드의 주요 차이점은 무엇인가요?
   - A) Secondary IP는 IPv6만, Prefix Delegation은 IPv4만 지원
   - B) Secondary IP는 개별 IP를 할당하고, Prefix Delegation은 /28 접두사(16 IPs)를 할당
   - C) Secondary IP는 EKS에서만, Prefix Delegation은 자체 관리 클러스터에서만 사용 가능
   - D) Secondary IP는 오버레이 네트워크를 사용하고, Prefix Delegation은 직접 라우팅을 사용

<details>
<summary>정답 보기</summary>

**정답: B) Secondary IP는 개별 IP를 할당하고, Prefix Delegation은 /28 접두사(16 IPs)를 할당**

**설명:**
Secondary IP 모드는 각 ENI에 개별 IP 주소를 하나씩 할당하는 반면, Prefix Delegation 모드는 /28 IPv4 접두사(16개 IP)를 한 번에 할당합니다. 이를 통해 노드당 더 많은 Pod를 실행할 수 있으며, IP 할당 속도도 향상됩니다.

</details>

---

3. m5.large 인스턴스에서 VPC CNI의 최대 Pod 수가 29개인 이유는 무엇인가요?
   - A) Kubernetes의 기본 제한이 29개이기 때문
   - B) 최대 3개 ENI × ENI당 10개 IP = 30에서 ENI 수(3)를 빼면 27이므로 (실제 공식 적용)
   - C) AWS의 소프트 리미트로 제한되기 때문
   - D) VPC 서브넷 크기에 의해 제한되기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 최대 3개 ENI × ENI당 10개 IP = 30에서 ENI 수(3)를 빼면 27이므로 (실제 공식 적용)**

**설명:**
VPC CNI에서 최대 Pod 수는 (ENI 수 × ENI당 IP 수) - ENI 수로 계산됩니다. m5.large는 최대 3개의 ENI를 지원하고 ENI당 10개의 IPv4 주소를 할당할 수 있습니다. 각 ENI의 Primary IP는 노드에 사용되므로 (3 × 10) - 3 = 27개입니다. 실제로는 호스트 네트워킹 Pod와 추가 요소로 인해 약간 다를 수 있습니다.

</details>

---

4. WARM_IP_TARGET 환경 변수의 목적은 무엇인가요?
   - A) Pod에 할당할 수 있는 최대 IP 수를 설정
   - B) 노드에서 사전 할당하여 대기시킬 여유 IP 수를 설정
   - C) 클러스터 전체의 총 IP 수를 제한
   - D) IP 주소의 TTL(Time To Live)을 설정

<details>
<summary>정답 보기</summary>

**정답: B) 노드에서 사전 할당하여 대기시킬 여유 IP 수를 설정**

**설명:**
WARM_IP_TARGET은 IPAMD가 각 노드에서 사전 할당하여 대기시킬 여유 IP 수를 제어합니다. 새로운 Pod가 생성될 때 즉시 IP를 할당할 수 있도록 미리 확보해 두는 것입니다. 값이 크면 Pod 시작이 빨라지지만 IP를 더 많이 사용하고, 값이 작으면 IP 효율성은 높아지지만 Pod 시작이 느려질 수 있습니다.

</details>

---

5. VPC CNI의 네이티브 Network Policy 지원에 대해 올바른 설명은?
   - A) Calico를 내부적으로 사용하여 Network Policy를 적용
   - B) v1.14부터 eBPF 기반의 네이티브 Network Policy를 지원
   - C) Network Policy는 EKS에서 지원되지 않음
   - D) iptables를 사용하여 Network Policy를 적용

<details>
<summary>정답 보기</summary>

**정답: B) v1.14부터 eBPF 기반의 네이티브 Network Policy를 지원**

**설명:**
VPC CNI v1.14부터 eBPF 기반의 네이티브 Kubernetes Network Policy를 지원합니다. 이전에는 Calico와 같은 별도의 Network Policy 엔진이 필요했지만, 이제 VPC CNI 자체에서 표준 Kubernetes NetworkPolicy 리소스를 처리할 수 있습니다.

</details>

---

6. Custom Networking(ENIConfig)을 사용하는 주요 목적은 무엇인가요?
   - A) Pod의 DNS 서버를 커스텀 설정
   - B) Pod에 노드와 다른 서브넷의 IP를 할당
   - C) 커스텀 CNI 플러그인을 설치
   - D) 노드의 네트워크 인터페이스 이름을 변경

<details>
<summary>정답 보기</summary>

**정답: B) Pod에 노드와 다른 서브넷의 IP를 할당**

**설명:**
Custom Networking을 사용하면 ENIConfig CRD를 통해 Pod에 노드와 다른 서브넷의 IP를 할당할 수 있습니다. 이는 노드 서브넷의 IP가 부족하거나, Pod에 다른 보안 그룹을 적용해야 하거나, 노드와 Pod의 네트워크를 분리해야 할 때 유용합니다. 일반적으로 Secondary CIDR(예: 100.64.0.0/16)과 함께 사용됩니다.

</details>

---

7. Pod별 Security Group 기능에서 사용되는 Trunk ENI와 Branch ENI의 역할은?
   - A) Trunk ENI는 외부 트래픽용, Branch ENI는 내부 트래픽용
   - B) Trunk ENI는 노드의 메인 ENI로 Branch ENI를 수용하고, Branch ENI는 각 Pod에 할당되는 가상 ENI
   - C) Trunk ENI는 IPv4용, Branch ENI는 IPv6용
   - D) Trunk ENI와 Branch ENI는 동일한 역할을 수행

<details>
<summary>정답 보기</summary>

**정답: B) Trunk ENI는 노드의 메인 ENI로 Branch ENI를 수용하고, Branch ENI는 각 Pod에 할당되는 가상 ENI**

**설명:**
Pod별 Security Group은 Trunk/Branch ENI 아키텍처를 사용합니다. Trunk ENI는 노드에 연결된 메인 ENI로 여러 Branch ENI를 수용합니다. Branch ENI는 각 Pod에 할당되는 가상 네트워크 인터페이스로, 독립적인 AWS Security Group을 적용할 수 있습니다. 이를 통해 Pod 수준에서 세밀한 네트워크 보안 제어가 가능합니다.

</details>

---

8. IP 고갈 문제가 발생했을 때 가장 효과적인 대응 방법으로 적절하지 않은 것은?
   - A) Prefix Delegation 활성화
   - B) Secondary CIDR 추가
   - C) 모든 Pod를 호스트 네트워크 모드로 전환
   - D) Custom Networking으로 전용 Pod 서브넷 사용

<details>
<summary>정답 보기</summary>

**정답: C) 모든 Pod를 호스트 네트워크 모드로 전환**

**설명:**
호스트 네트워크 모드(`hostNetwork: true`)로 모든 Pod를 실행하면 IP 할당 문제는 해결될 수 있지만, Pod 간 네트워크 격리가 사라지고 포트 충돌이 발생할 수 있어 실질적인 해결책이 아닙니다. IP 고갈 문제의 적절한 대응 방법은 Prefix Delegation 활성화, Secondary CIDR 추가, Custom Networking 사용, WARM_IP_TARGET 조정 등입니다.

</details>
