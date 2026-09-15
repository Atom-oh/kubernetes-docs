# 클라우드·CNI 설계 퀴즈

[본문](../../../networking/expert/05-cloud-cni-design.md)

1. DNS 응답을 받았지만 TCP 연결이 실패했습니다. 올바른 다음 단계는?

   - A) DNS 성공만으로 backend 정상으로 판정한다
   - B) 실제 대상·포트·경로·접근 제어·리스너를 확인한다
   - C) 모든 보안 그룹을 개방한다
   - D) 리소스가 없다고 단정한다

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** DNS는 이름 조회의 증거입니다. TCP 연결과 HTTP 응답은 별도 경로·정책·애플리케이션 증거로 확인합니다.

</details>

2. AWS Load Balancer Controller의 역할은?

   - A) 모든 HTTP 요청이 통과하는 데이터 평면
   - B) 각 Pod의 기본 게이트웨이
   - C) AWS API를 이용해 로드밸런서 자원을 조정하는 제어 평면
   - D) DNS 캐시 자체

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** 요청은 로드밸런서와 실제 대상의 경로를 사용합니다. controller Pod 상태와 데이터 평면 통신은 구분해서 조사합니다.

</details>

3. EndpointSlice는 ready이지만 LB target은 unhealthy입니다. 어떻게 해석하나요?

   - A) 두 상태가 다를 수 있으므로 등록 주소·포트·health check와 경로를 대조한다
   - B) 같은 의미라서 관측이 불가능한 상태다
   - C) DNS TTL만 바꾸면 해결된다
   - D) EndpointSlice를 삭제한다

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** readiness와 LB health check는 관측 주체·조건이 다릅니다. 같은 endpoint 객체의 주소와 조건을 연결하고 실제 target을 확인해야 합니다.

</details>

4. NetworkPolicy 객체가 존재하면 무엇이 추가로 필요한가요?

   - A) 없다. 객체 존재가 강제를 증명한다
   - B) 모든 Pod를 hostNetwork로 바꾼다
   - C) 필수 AWS 계정 전체의 관리자 권한
   - D) 선택된 Pod·정책 방향·지원 API·엔진 활성화와 실제 흐름의 증거

<details>
<summary>정답 보기</summary>

**정답: D**

**설명:** 정책 객체 목록은 적용 대상이나 실제 강제 결과를 보장하지 않습니다. 다른 관리형 정책·CRD도 고려합니다.

</details>

5. TGW association과 propagation을 바르게 구분한 것은?

   - A) 둘 다 동일한 방화벽 규칙이다
   - B) association은 attachment의 조회 table, propagation은 경로를 배우는 table을 정한다
   - C) propagation하면 항상 그 table을 조회한다
   - D) 하나의 attachment는 모든 table에 associate된다

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** 하나의 attachment는 한 table에 associate하고 여러 table에 propagate할 수 있습니다. 양쪽 조회·반환 경로를 따로 확인합니다.

</details>

6. 조회가 AccessDenied이고 endpoint 목록도 확보하지 못했습니다. 결과는?

   - A) 트래픽 차단 검증 성공
   - B) 자동으로 관리자 정책을 연결해야 함
   - C) 해당 범위의 증거 미확보; 승인된 최소 조회 권한이나 제공 자료가 필요
   - D) backend가 존재하지 않음

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** 권한 부족과 자원·네트워크 상태는 다릅니다. unknown을 허용·차단·부재로 바꾸지 않습니다.

</details>

7. Service ClusterIP를 패킷 경로에 표시할 때 적절한 방식은?

   - A) 논리적인 선택 관계와 실제 proxy/target 경로를 구분한다
   - B) 항상 노드 뒤의 별도 물리 hop으로 그린다
   - C) 모든 IP target 요청이 반드시 통과한다고 쓴다
   - D) 반환 경로는 생략한다

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** 실제 전달은 target type, proxy 구현과 정책에 따라 달라집니다. 객체의 논리 관계를 필수 wire hop으로 바꾸면 진단을 왜곡합니다.

</details>

8. 계정 없이 하이브리드 라우팅 설계표만 검토했습니다. 완료 표시는?

   - A) 실환경 장애 전환 검증 완료
   - B) 성능 보장 완료
   - C) 모든 정책 강제 확인
   - D) 설계 검토 완료; 실환경 관측은 미확인

<details>
<summary>정답 보기</summary>

**정답: D**

**설명:** 설계, 제공 자료 분석과 실제 실험은 서로 다른 증거 수준입니다. 결론을 실제 수행한 범위로 제한합니다.

</details>
