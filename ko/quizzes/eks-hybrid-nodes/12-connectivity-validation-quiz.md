# SNAT 없는 Pod 연결과 PrivateLink 검증 퀴즈

> **마지막 업데이트**: 2026년 10월 19일

[학습 문서: SNAT 없는 Pod 연결과 PrivateLink 검증](../../eks-hybrid-nodes/12-connectivity-validation.md)

1. AWS가 EKS Hybrid Nodes용 Cilium에서 지원하는 Networking Mode는 무엇인가요?
   - A) native routing만 지원한다.
   - B) VXLAN encapsulation만 지원한다.
   - C) VXLAN과 native routing을 모두 지원한다.

<details>
<summary>정답 보기</summary>

**정답: B) VXLAN encapsulation만 지원한다.**

**설명:**
CNI 구성 문서의 Supported capabilities 표에서 Networking Mode는 VXLAN encapsulation입니다. native routing은 지원 범위 밖이며, Hybrid Nodes Gateway도 VTEP(VXLAN)가 필요해 native routing과 함께 쓸 수 없습니다.

</details>

2. VXLAN을 유지한 채 masquerade만 끄고 Cilium BGP로 Pod CIDR을 광고하면, 방화벽이 Pod IP를 보지 못하는 구간은 어디인가요?
   - A) 클라우드 Pod와 온프렘 Pod 사이
   - B) 쿠버네티스 밖 온프렘 서버로 가는 구간
   - C) hybrid 노드와 hybrid 노드 사이

<details>
<summary>정답 보기</summary>

**정답: C) hybrid 노드와 hybrid 노드 사이**

**설명:**
hybrid 노드 사이 트래픽은 VXLAN으로 캡슐화되어 바깥 헤더가 노드 IP입니다. 클러스터 밖으로 나가는 트래픽은 masquerade를 끄면 Pod IP를 유지합니다.

</details>

3. native routing으로 바꾼 뒤 클라우드 Pod가 온프렘 서버를 호출했더니 서버에 클라우드 노드 IP가 보였습니다. 가장 먼저 확인할 것은 무엇인가요?
   - A) VPC CNI의 `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS`에 온프렘 노드 대역이 있는지
   - B) Cilium의 `enableIPv4Masquerade` 값
   - C) TGW route table의 기본 경로

<details>
<summary>정답 보기</summary>

**정답: A) VPC CNI의 `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS`에 온프렘 노드 대역이 있는지**

**설명:**
클라우드 Pod의 SNAT은 Cilium이 아니라 VPC CNI가 합니다. 제외 목록에 Pod 대역(172.17.0.0/16)만 있고 온프렘 노드 대역(172.18.0.0/16)이 없으면, 온프렘 서버로 가는 트래픽은 노드 IP로 바뀝니다.

</details>

4. hostNetwork Pod만 클러스터 Service 이름을 풀지 못합니다. 일반 hybrid Pod는 정상입니다. 원인으로 가장 알맞은 것은 무엇인가요?
   - A) CoreDNS가 hybrid 노드에 없어서
   - B) hostNetwork Pod는 노드 IP로 CoreDNS를 부르는데, 클러스터 SG가 노드 대역의 53번을 허용하지 않아서
   - C) hostNetwork Pod는 DNS를 쓸 수 없어서

<details>
<summary>정답 보기</summary>

**정답: B) hostNetwork Pod는 노드 IP로 CoreDNS를 부르는데, 클러스터 SG가 노드 대역의 53번을 허용하지 않아서**

**설명:**
일반 Pod는 Pod IP(172.17.x)로, hostNetwork Pod는 노드 IP(172.18.x)로 나갑니다. 클러스터 SG에 `172.18.0.0/16`의 UDP, TCP 53을 허용해야 합니다. `dnsPolicy: ClusterFirstWithHostNet`도 필요합니다.

</details>

5. 온프렘 Pod가 S3를 사설 경로로 쓰려고 합니다. 맞는 설명은 무엇인가요?
   - A) S3 gateway endpoint를 만들면 온프렘에서도 쓸 수 있다.
   - B) S3 interface endpoint가 필요하고, gateway endpoint 없이 만들 때는 `DnsOptions`를 `AllResolvers`로 지정했다.
   - C) S3는 PrivateLink를 지원하지 않는다.

<details>
<summary>정답 보기</summary>

**정답: B) S3 interface endpoint가 필요하고, gateway endpoint 없이 만들 때는 `DnsOptions`를 `AllResolvers`로 지정했다.**

**설명:**
gateway endpoint는 온프렘에서 접근할 수 없습니다. 시험에서는 `PrivateDnsOnlyForInboundResolverEndpoint`를 지정하지 않은 첫 생성이 gateway endpoint가 없다는 오류로 실패했습니다.

</details>

6. endpoint SG가 TCP 443을 `172.17.0.0/16`(Pod 대역)에서만 허용할 때, 같은 hybrid 노드의 일반 Pod와 hostNetwork Pod가 STS endpoint를 부르면 어떻게 되나요?
   - A) 둘 다 성공한다.
   - B) 둘 다 실패한다.
   - C) 일반 Pod는 성공하고 hostNetwork Pod는 타임아웃된다.

<details>
<summary>정답 보기</summary>

**정답: C) 일반 Pod는 성공하고 hostNetwork Pod는 타임아웃된다.**

**설명:**
SNAT이 없으므로 일반 Pod의 출발지는 Pod IP이고, hostNetwork Pod의 출발지는 노드 IP(172.18.x)입니다. AWS 쪽 SG로도 온프렘 Pod를 Pod 대역으로 구분할 수 있다는 뜻입니다.

</details>

7. Kubernetes 1.36, Cilium 1.18 mixed mode 클러스터의 시험에서 hybrid Pod가 링크 단절 중에도 온프렘 CoreDNS만 쓰게 만든 kube-dns Service 값은 무엇인가요?
   - A) `trafficDistribution: PreferClose`
   - B) `externalTrafficPolicy: Local`
   - C) `sessionAffinity: ClientIP`

<details>
<summary>정답 보기</summary>

**정답: A) `trafficDistribution: PreferClose`**

**설명:**
hybrid 노드의 ClusterIP 부하 분산은 Cilium BPF가 맡는데, 시험한 Cilium 1.18.13은 `PreferSameZone`을 무시했습니다. AWS 문서 예시도 `PreferClose`입니다. Kubernetes 1.35부터 deprecated 별칭이지만 이 구성에서는 이것만 동작했습니다. 조인할 때 붙인 zone label, zone마다 CoreDNS, Cilium `loadBalancer.serviceTopology: true`도 필요합니다.

</details>
