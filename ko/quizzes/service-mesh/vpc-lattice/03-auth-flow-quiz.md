# IAM 인증 절차 상세 퀴즈

이 퀴즈는 Lattice IAM Auth의 4단계 절차, SigV4 서명 함정, 403 진단에 대한 이해도를 테스트합니다.

## 객관식 문제

1. VPC Lattice 데이터 평면 요청을 SigV4로 서명할 때 사용하는 서비스명은?
   - A) `vpc-lattice`
   - B) `vpc-lattice-svcs`
   - C) `lattice`
   - D) `execute-api`

<details>

<summary>정답 보기</summary>

**정답: B) `vpc-lattice-svcs`**

**설명:**
`vpc-lattice-svcs`가 데이터 평면 요청의 서명 서비스명입니다. `vpc-lattice`는 Lattice 제어 평면 API(서비스·리스너 생성 등)의 서비스명이라 혼동하기 쉽습니다. 서비스명은 signing key 파생 과정(secret key → 날짜 → 리전 → 서비스명 → 종료 문자열의 HMAC-SHA256 4회 연쇄)의 입력값이므로 틀리면 서명이 검증되지 않습니다. 서비스 DNS 이름 자체가 `...vpc-lattice-svcs.<region>.on.aws` 형태인 것과 일관됩니다.
</details>

2. Lattice IAM Auth에서 403이 발생하는 가장 흔한 원인은?
   - A) Lattice 서비스의 auth policy에 principal이 누락된 경우
   - B) 호출자 IAM Role의 identity-based policy에 `vpc-lattice-svcs:Invoke` 권한이 없는 경우
   - C) 노드 Security Group이 Lattice prefix list를 허용하지 않은 경우
   - D) Target Group의 health check가 실패한 경우

<details>

<summary>정답 보기</summary>

**정답: B) 호출자 IAM Role의 identity-based policy에 `vpc-lattice-svcs:Invoke` 권한이 없는 경우**

**설명:**
"서비스 쪽 auth policy에서 이 Role을 허용했으니 됐다"고 생각하기 쉽지만, 호출자 Role 자신에게도 Invoke 권한이 필요합니다. 리소스 정책만으로는 통과하지 못합니다. 실제 에러 메시지의 마지막 절이 `because no identity-based policy allows the vpc-lattice-svcs:Invoke action`으로 원인을 알려주므로, 403을 만나면 이 문구를 먼저 확인해야 합니다. 참고로 C는 403이 아니라 연결 실패나 타임아웃으로 나타납니다.
</details>

3. custom domain을 도입한 직후 403이 발생하기 시작했다면 가장 먼저 확인할 것은?
   - A) Target Group의 프로토콜 설정
   - B) `Host` 헤더 — SigV4에서 Host는 항상 서명 대상이므로, 서명할 때 쓴 Host 값과 실제 요청의 Host 헤더가 일치해야 한다
   - C) Lattice의 quotas 초과 여부
   - D) VPC의 DNS 확인 설정

<details>

<summary>정답 보기</summary>

**정답: B) `Host` 헤더 — SigV4에서 Host는 항상 서명 대상이므로, 서명할 때 쓴 Host 값과 실제 요청의 Host 헤더가 일치해야 한다**

**설명:**
SigV4는 `Host` 헤더를 항상 서명 대상에 포함합니다. custom domain을 붙이면 클라이언트는 그 도메인으로 요청을 보내므로 그 값으로 서명해야 하는데, 서명 로직이 Lattice 생성 도메인을 쓰고 있으면 불일치가 발생합니다. 이 문제는 전환 초기가 아니라 custom domain을 붙이는 시점에 터지기 때문에 놓치기 쉽습니다. custom domain 도입은 SNI 통제, 서명 대상 Host, 인증서 관리를 함께 결정해야 하는 항목입니다.
</details>

4. "특정 노드에 있는 Pod만 간헐적으로 403이 발생한다"면 가장 유력한 원인은?
   - A) 그 노드의 Security Group 설정 오류
   - B) 그 노드의 시각 동기화 문제 — `x-amz-date`는 서명 대상이며 SigV4의 허용 오차는 약 5분이다
   - C) 그 노드에 Gateway API Controller가 없기 때문
   - D) 그 노드의 kubelet 버전이 낮기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 그 노드의 시각 동기화 문제 — `x-amz-date`는 서명 대상이며 SigV4의 허용 오차는 약 5분이다**

**설명:**
`x-amz-date`가 서명 대상이므로 검증 측은 이 시각이 현재 시각과 크게 다르면 요청을 거부합니다. 즉 노드의 시각 동기화가 인증의 전제 조건입니다. Amazon Time Sync Service를 쓰는 EC2/EKS 노드에서는 보통 문제되지 않지만, NTP가 제대로 설정되지 않은 온프레미스·하이브리드 노드나 장시간 suspend 후 재개된 노드에서 발생합니다. 실패가 간헐적이고 노드 단위라는 특징이 진단의 단서입니다. 참고로 5분은 SigV4 공통 동작이며 Lattice 전용 값이 아닙니다.
</details>

5. egress proxy 방식으로 SigV4 서명을 할 때 "서명은 최종 홉에서 해야 한다"는 원칙이 중요한 이유는?
   - A) 프록시가 여러 개면 레이턴시가 증가하기 때문
   - B) 서명은 요청 내용(경로, 쿼리, Host, payload hash 등)에 묶여 있어, 서명 이후에 그것을 건드리는 프록시가 있으면 검증이 깨지기 때문
   - C) 프록시는 credential을 캐시할 수 없기 때문
   - D) IAM Role은 하나의 프록시에만 연결할 수 있기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 서명은 요청 내용(경로, 쿼리, Host, payload hash 등)에 묶여 있어, 서명 이후에 그것을 건드리는 프록시가 있으면 검증이 깨지기 때문**

**설명:**
canonical request에는 메서드, 정규화된 경로, 정렬된 쿼리 문자열, 서명 대상 헤더, payload 해시가 들어갑니다. 경로를 rewrite하거나 Host를 바꾸거나 쿼리를 추가·정렬 변경하거나 payload를 압축·해제하는 프록시가 서명 뒤에 있으면 서명이 불일치합니다. aws-samples 레퍼런스 구현은 `sigv4proxy` 사이드카를 8080에서 띄우고 init container가 iptables로 `169.254.171.0/24` 향 트래픽만 리다이렉트해, 프록시가 서명한 뒤 곧바로 Lattice로 나가게 만듭니다.
</details>

6. auth policy를 설정했는데도 클러스터 내부에서 인가가 적용되지 않는 경우의 원인은?
   - A) auth policy가 IPv6 트래픽을 지원하지 않기 때문
   - B) 클라이언트가 Kubernetes Service DNS로 직접 호출하면 Lattice를 거치지 않으므로 auth policy가 평가되지 않기 때문
   - C) auth policy는 계정 간 호출에만 적용되기 때문
   - D) Gateway API Controller가 정책을 아직 반영하지 않았기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 클라이언트가 Kubernetes Service DNS로 직접 호출하면 Lattice를 거치지 않으므로 auth policy가 평가되지 않기 때문**

**설명:**
AWS Gateway API Controller 문서가 명시하는 제약입니다. `IAMAuthPolicy`는 Gateway, HTTPRoute, GRPCRoute를 통과하는 트래픽에 대해서만 인가를 수행하며, `http://svc.ns.svc.cluster.local`처럼 클러스터 내부 DNS로 직접 보내면 Lattice를 우회해 정책이 평가되지 않습니다. 전환 기간 중 두 경로가 공존하면 인가가 적용되는 경로와 안 되는 경로가 동시에 존재하므로, NetworkPolicy로 직접 호출을 차단하는 등의 보완이 필요합니다. 또 다른 흔한 원인은 authType이 `AWS_IAM`이 아니라 `NONE`인 경우입니다.
</details>

7. AS-IS(App Mesh + SPIRE mTLS) 대비 TO-BE(Lattice IAM Auth)에서 인증의 "단위"와 "방향성"은 어떻게 바뀌는가?
   - A) connection 단위 양방향 → 요청 단위 양방향
   - B) connection 단위 양방향 상호 인증 → 요청 단위 단방향(클라이언트 증명) + TLS 서버 인증서
   - C) 요청 단위 단방향 → connection 단위 양방향
   - D) 단위와 방향성 모두 변화가 없다

<details>

<summary>정답 보기</summary>

**정답: B) connection 단위 양방향 상호 인증 → 요청 단위 단방향(클라이언트 증명) + TLS 서버 인증서**

**설명:**
mTLS는 연결 수립 시 한 번 서로의 SVID를 검증하는 양방향 모델입니다. Lattice IAM Auth는 요청마다 클라이언트의 SigV4 서명을 검증하므로 클라이언트 증명은 오히려 더 세밀해집니다(연결 탈취 후 임의 요청 전송 시나리오 차단, 경로·메서드·헤더 조건 활용 가능). 그러나 서버 측 신원 증명은 TLS 서버 인증서 수준으로 내려가며, "이 서비스가 진짜 그 팀의 서비스인가"를 워크로드 신원 체계로 확인하는 단계가 없어집니다.
</details>
