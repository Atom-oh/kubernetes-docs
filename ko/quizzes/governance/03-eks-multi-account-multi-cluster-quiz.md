# EKS 멀티 계정·멀티 클러스터 아키텍처 퀴즈

> 이 퀴즈는 [EKS 멀티 계정·멀티 클러스터 아키텍처](../../governance/03-eks-multi-account-multi-cluster.md) 문서의 학습 내용을 테스트합니다.

---

1. 두 EKS 클러스터를 사용하는 A/B 구성의 타당한 검증 목표는?
   - A) EKS control plane이 단일 AZ임을 해결
   - B) 업그레이드·add-on·webhook 오류가 한 클러스터에 격리되는지 시험
   - C) 모든 Region 장애를 자동 방어
   - D) 비용이 항상 감소함을 보장

<details>
<summary>정답 보기</summary>

**정답: B) 업그레이드·add-on·webhook 오류가 한 클러스터에 격리되는지 시험**

**설명:**
클러스터별 장애 격리가 목표가 될 수 있습니다. 공유 VPC·DNS·계정·데이터 계층의 공통 장애는 별도 검토해야 합니다.

</details>

---

2. ARC zonal shift의 fail-safe 동작에 대한 설명으로 옳은 것은?
   - A) 어떤 워크로드든 zonal shift가 발생하면 즉시 트래픽이 차단된다
   - B) 워크로드의 endpoint가 전부 장애 AZ에만 있으면, EKS는 그 AZ로 트래픽을 계속 보낸다
   - C) 모든 워크로드가 자동으로 다른 AZ로 재배치된다
   - D) EKS Fargate에서만 이 동작이 발생한다

<details>
<summary>정답 보기</summary>

**정답: B) 워크로드의 endpoint가 전부 장애 AZ에만 있으면, EKS는 그 AZ로 트래픽을 계속 보낸다**

**설명:**
이것이 fail-safe 동작입니다. 즉 1-AZ에만 배포된 워크로드는 zonal shift로 보호받지 못합니다. N-1 부하와 single-AZ 예외를 시험해야 하며 practice run이 이 워크로드를 항상 중단시킨다는 뜻은 아닙니다.

</details>

---

3. EC2의 link-local1,024packet/s 제한에 대한 설명은?
   - A) DNS·IMDS·NTP 등 합계이므로 실제 지표와 DNS 경로를 함께 점검
   - B) DNS만 독점하는 무제한 quota
   - C) AZ당100Gbps를 뜻함
   - D) CoreDNS가 가장 흔한 장애임을 증명함

<details>
<summary>정답 보기</summary>

**정답: A) DNS·IMDS·NTP 등 합계이므로 실제 지표와 DNS 경로를 함께 점검**

**설명:**
Link-local allowance와 VPC DNS ENI 제한을 확인합니다. 높은 Pod 밀도만으로 원인을 단정하지 말고 linklocal_allowance_exceeded·DNS 지연 등을 확인합니다.

</details>

---

4. ALB target group의 cross-zone을 끌 때 확인할 것은?
   - A) ALB cross-zone 전송 요금이 반드시 절감됨
   - B) AZ별 target capacity와 empty-AZ503, unhealthy-target failover를 구분
   - C) 클러스터가 자동 재시작됨
   - D) 모든 target이 항상 healthy로 바뀜

<details>
<summary>정답 보기</summary>

**정답: B) AZ별 target capacity와 empty-AZ503, unhealthy-target failover를 구분**

**설명:**
Target stickiness와 Lambda target에 제약이 있고 empty AZ와 unhealthy target은 다르게 동작합니다. ALB 자체의 cross-zone regional data transfer에는 추가 전송 요금이 없습니다.

</details>
