# Observability Lab 01 퀴즈

<span id="observability-실습-part-1-인프라-구성-퀴즈"></span>

> **마지막 업데이트**: 2026년 9월 13일

1. 검토일의 EKS 버전 상태를 적용하는 방법은?
   - A) 1.31은 무조건 이미 종료됐다
   - B) 1.36 표준 지원을 기준으로 실행 시점의 리전/지원 상태를 다시 확인한다
   - C) 마이너 버전은 영원히 지원된다
   - D) kubectl 버전 차이는 무관하다

<details>
<summary>정답 보기</summary>

**정답: B) 1.36 표준 지원을 기준으로 실행 시점의 리전/지원 상태를 다시 확인한다**

1.31의 확장 지원과 지원 종료를 구분하며 API 서버와 client 호환성을 확인합니다.

</details>

---

2. 기존 VPC를 재사용할 때 필요한 검사는?
   - A) VPC ID 문자열만
   - B) subnet AZ·주소 여유·route·DNS·SG와 service CIDR 비중첩
   - C) 두 service CIDR을 같게 한다
   - D) NAT/endpoint는 필요 없다

<details>
<summary>정답 보기</summary>

**정답: B) subnet AZ·주소 여유·route·DNS·SG와 service CIDR 비중첩**

이 생성기는 네트워크 리소스를 만들지 않으므로 실제 연결 전제가 필요합니다.

</details>

---

3. public API client CIDR 설정은?
   - A) 항상0.0.0.0/0
   - B) 승인된 좁은 실제 출발지 범위
   - C) 임의 문서 예제IP를 운영에 사용
   - D) 인증 대신 CIDR만 있으면 된다

<details>
<summary>정답 보기</summary>

**정답: B) 승인된 좁은 실제 출발지 범위**

private/public endpoint, 출발지와 인증을 함께 검증합니다.

</details>

---

4. IRSA role trust의 핵심 제약은?
   - A) 모든 service account 허용
   - B) 올바른 OIDC provider와 aud/sub의 정확한 namespace·ServiceAccount
   - C) 노드 role에 모든 권한
   - D) secret access key를 Pod에 하드코딩

<details>
<summary>정답 보기</summary>

**정답: B) 올바른 OIDC provider와 aud/sub의 정확한 namespace·ServiceAccount**

provider ARN과 issuer host/path도 같은 provider를 가리켜야 합니다.

</details>

---

5. Aurora 접근 경계는?
   - A) public writer와전체인터넷
   - B) private subnet과 실제 서비스 client SG의5432접근
   - C) SG 이름이 비슷하면 된다
   - D) Multi-AZ writer가 자동으로 생긴다

<details>
<summary>정답 보기</summary>

**정답: B) private subnet과 실제 서비스 client SG의5432접근**

단일 writer는 실습 선택이며 HA 보장이 아닙니다.

</details>

---

6. 애플리케이션 DB 계정은?
   - A) master계정을모든Pod에
   - B) lab table DML만 가진 별도runtime계정
   - C) 비밀번호없이public연결
   - D) 매실행마다기존비밀번호덮기

<details>
<summary>정답 보기</summary>

**정답: B) lab table DML만 가진 별도runtime계정**

bootstrap은 기존 role을 덮지 않으며 실패 시 candidate 파일을 검증합니다.

</details>

---

7. 특수문자 비밀번호의 전달 방식은?
   - A) DSN문자열에그대로연결
   - B) JSON의 원본 값을 URL.create의 password인자로 전달
   - C) 여러번URLencode
   - D) 로그에출력해복사

<details>
<summary>정답 보기</summary>

**정답: B) JSON의 원본 값을 URL.create의 password인자로 전달**

TLS verify-full과 실제CA경로도 함께 확인합니다.

</details>

---

8. 클러스터 생성 중 실패하면?
   - A) 새이름으로계속생성
   - B) 같은 이름의 부분 생성 리소스·state·소유권을 확인
   - C) 실패면과금0이라고가정
   - D) 모든VPC삭제

<details>
<summary>정답 보기</summary>

**정답: B) 같은 이름의 부분 생성 리소스·state·소유권을 확인**

CLI 실패가 리소스 미생성을 뜻하지 않습니다.

</details>

---

9. gp3 StorageClass 확인의 의미는?
   - A) 이름만있으면항상동작
   - B) EBS CSI·권한·실제class설정·volume정리를 확인
   - C) 공유class를무조건덮기
   - D) PVC삭제와snapshot삭제는같다

<details>
<summary>정답 보기</summary>

**정답: B) EBS CSI·권한·실제class설정·volume정리를 확인**

공유 객체 변경과 리소스 삭제 책임을 구분합니다.

</details>

---

10. 실습 비용 산정은?
   - A) 항상시간당2.5달러
   - B) 실제 리전·사용량·보존·NAT/LB/storage/snapshot 등을 포함
   - C) AMG월사용자요금을workspace시간요금으로환산
   - D) NodePoollimit이절대예산이다

<details>
<summary>정답 보기</summary>

**정답: B) 실제 리전·사용량·보존·NAT/LB/storage/snapshot 등을 포함**

고정 총액·실측되지 않은 절감률을 주장하지 않습니다.

</details>

---

[본문으로 돌아가기](../../../labs/observability/01-infrastructure-setup-lab.md)
