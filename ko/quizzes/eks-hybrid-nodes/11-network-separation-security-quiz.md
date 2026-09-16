# Hybrid Nodes 망분리 보안 검토 퀴즈

> **마지막 업데이트**: 2026년 9월 16일

[학습 문서: 보안팀 관점의 Hybrid Nodes 망분리 검토](../../eks-hybrid-nodes/11-network-separation-security.md)

1. “DX와 private endpoint를 사용하므로 망분리를 준수한다”는 설명을 어떻게 보완해야 하나요?
   - A) DX 연결 ID만 첨부하면 충분하다.
   - B) 적용 정책, 허용 통신·권한·데이터 범위, 실제 통제 증거와 승인 조건을 함께 제시한다.
   - C) 인터넷을 사용하지 않으면 외부 관리 연결은 존재하지 않는다.

<details>
<summary>정답 보기</summary>

**정답: B**

사설 경로는 노출을 줄이는 통제 수단입니다. 고객의 망분리 정책과 관리 통신의 허용 여부를 대신 결정하지 않습니다.

</details>

2. `com.amazonaws.<region>.eks` interface endpoint의 역할은 무엇인가요?
   - A) Control plane의 모든 kubelet TCP 10250 연결을 중계한다.
   - B) Kubernetes API의 RBAC를 endpoint policy로 대체한다.
   - C) `DescribeCluster` 같은 AWS EKS 관리 API의 사설 접근을 제공한다.

<details>
<summary>정답 보기</summary>

**정답: C**

Kubernetes API private endpoint와 AWS EKS 관리 API용 PrivateLink endpoint는 서로 다릅니다.

</details>

3. Hybrid node가 시작한 TCP 443 세션의 응답만 방화벽에서 허용했습니다. 일반적인 routed 구성에서 `kubectl logs`의 kubelet 연결도 허용되나요?
   - A) 아니다. API server가 노드 TCP 10250으로 시작하는 별도 세션을 검토해야 한다.
   - B) 그렇다. 같은 클러스터의 모든 트래픽은 기존 세션의 응답이다.
   - C) 그렇다. DX는 방화벽 규칙을 자동으로 우회한다.

<details>
<summary>정답 보기</summary>

**정답: A**

Stateful return 허용은 다른 TCP 세션의 신규 inbound 허용과 다릅니다.

</details>

4. 이 글의 private-only 전제를 확인하는 올바른 조합은 무엇인가요?
   - A) `endpointPrivateAccess=true`만 확인한다.
   - B) Private access 활성화와 public access 비활성화를 확인하고 실제 DNS·route·flow를 검증한다.
   - C) `publicAccessCidrs`를 줄이면 private endpoint도 같은 범위로 제한된다.

<details>
<summary>정답 보기</summary>

**정답: B**

Public과 private이 모두 켜져 있으면 hybrid node가 public 주소를 사용할 수 있습니다. Public CIDR 설정은 private endpoint의 접근 통제가 아닙니다.

</details>

5. DX를 사용하는 환경의 암호화 설명으로 맞는 것은 무엇인가요?
   - A) 모든 Pod 트래픽이 DX에 의해 기본 암호화된다.
   - B) Private IP 주소면 TLS 인증서 검증을 생략할 수 있다.
   - C) TLS를 유지하고, 별도 회선 암호화 요구에는 IPsec/MACsec의 지원 여부와 보호 범위를 확인한다.

<details>
<summary>정답 보기</summary>

**정답: C**

DX는 기본 전송 암호화를 보장하지 않습니다. MACsec의 링크 보호와 애플리케이션 종단 간 TLS도 같은 범위가 아닙니다.

</details>

6. 업무 Pod가 온프레미스에서 실행됩니다. 데이터 경계에 대해 맞는 설명은 무엇인가요?
   - A) 모든 업무 데이터는 자동으로 AWS에 복제된다.
   - B) 모든 데이터가 반드시 온프레미스에만 남는다.
   - C) 업무 저장소와 별개로 API 객체·Secret·`logs`·관리 스트림·앱 egress의 데이터 이동을 확인한다.

<details>
<summary>정답 보기</summary>

**정답: C**

노드 위치는 모든 데이터의 저장·전송 위치를 결정하지 않습니다. Kubernetes 관리 기능도 민감 데이터를 다룰 수 있습니다.

</details>

7. EKS ENI IP를 방화벽 allowlist로 사용할 때 필요한 운영 절차는 무엇인가요?
   - A) 최초 수집한 `/32`를 영구 사용한다.
   - B) Cluster 소유권·주소 범위를 확인하고 ENI 변경 때 갱신·재검증하며 공유 subnet의 위험을 기록한다.
   - C) AWS 전체 주소 공간을 허용한다.

<details>
<summary>정답 보기</summary>

**정답: B**

ENI IP는 바뀔 수 있습니다. 넓은 공유 subnet을 허용하면 다른 자원도 출발지 범위에 포함될 수 있습니다.

</details>

8. “`exec` 권한을 제거했으므로 관리자를 통한 데이터 접근은 모두 차단했다”는 설명의 문제는 무엇인가요?
   - A) Workload 생성·변경, privileged/hostPath, 다른 subresource 및 host 관리 권한도 검토해야 한다.
   - B) Namespace가 다르면 cluster 관리자는 접근할 수 없다.
   - C) NetworkPolicy가 모든 관리자 권한을 무효화한다.

<details>
<summary>정답 보기</summary>

**정답: A**

한 가지 명령의 제한만으로 대체 데이터 접근 경로가 사라지지 않습니다. 관리 주체의 전체 권한과 admission·host 통제를 함께 봅니다.

</details>

9. 보안 심사 증거에 관한 올바른 설명은 무엇인가요?
   - A) VPC Flow Logs만으로 TLS payload와 `exec` 입출력을 모두 복원한다.
   - B) CloudTrail만 있으면 Kubernetes audit 로그는 필요 없다.
   - C) 네트워크 기록·Kubernetes audit·CloudTrail의 범위를 구분하고, 합성 데이터로 허용과 거부를 시험한다.

<details>
<summary>정답 보기</summary>

**정답: C**

각 기록의 범위가 다릅니다. Kubernetes audit도 모든 스트림 payload를 녹화하지 않으며 실제 거부 시험과 데이터 분류를 대체하지 않습니다.

</details>

10. 보안 정책이 클라우드발 신규 연결을 전면 금지합니다. Webhook을 cloud node로 옮기거나 Hybrid Nodes Gateway를 쓰면 자동 충족되나요?
    - A) 둘 중 하나만 적용하면 된다.
    - B) 아니다. Kubelet의 별도 연결과 gateway의 실제 양방향 경로를 포함해 설계를 다시 검토해야 한다.
    - C) PrivateLink라는 이름으로 설명하면 된다.

<details>
<summary>정답 보기</summary>

**정답: B**

Webhook 이동은 kubelet 요구를 제거하지 않습니다. Hybrid Nodes Gateway도 단방향 보안 게이트웨이가 아닙니다. 정책과 지원되는 연결 요구가 충돌하면 설계 또는 공식 승인 조건을 재검토합니다.

</details>
