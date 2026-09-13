# 제약사항과 의사결정 포인트 퀴즈

이 퀴즈는 Lattice 전환의 제약 6개와 의사결정 순서, 과금 구조에 대한 이해도를 테스트합니다.

## 객관식 문제

1. TLS 신원과 TCP 연결 모델을 올바르게 구분한 설명은 무엇입니까?
   - A) SigV4 서명의 애플리케이션 영향과 Envoy iptables 예외 설정
   - B) 인증된 HTTP 신원과 익명 TLS 정책, 서비스 listener와 TCP resource connectivity를 구분한다
   - C) Hop 단위 과금과 STS 의존성
   - D) Failure domain 집중과 quotas 제한

<details>

<summary>정답 보기</summary>

**정답: B) 인증된 HTTP 신원과 익명 TLS 정책, 서비스 listener와 TCP resource connectivity를 구분한다**

**설명:**
현재 API/신뢰 경계의 선택이지 모든 TLS auth policy가 불가능하거나 Lattice 전체가 TCP resource 접근을 지원하지 않는다는 증명이 아닙니다.
</details>

2. 전환 설계에서 가장 먼저 결정해야 하는 항목은?
   - A) SigV4 서명을 라이브러리로 할지 egress proxy로 할지
   - B) 규정이 종단간 암호화 또는 워크로드 간 상호 인증을 요구하는지 — 이에 따라 HTTPS listener + IAM Auth와 TLS Passthrough가 갈리고 이후 설계 대부분이 종속된다
   - C) Lattice 서비스 개수와 예상 비용
   - D) 노드 Security Group의 prefix list 설정

<details>

<summary>정답 보기</summary>

**정답: B) 규정이 종단간 암호화 또는 워크로드 간 상호 인증을 요구하는지 — 이에 따라 HTTPS listener + IAM Auth와 TLS Passthrough가 갈리고 이후 설계 대부분이 종속된다**

**설명:**
이 결정은 기술이 아니라 조직의 심의 기준에 달려 있습니다. TLS Passthrough를 택하면 IAM Auth 전체와 L7 라우팅을 포기하고 인가를 엔드포인트 mTLS나 애플리케이션에서 새로 설계해야 하며, SPIRE 존속 검토까지 따라옵니다. 반대로 HTTPS listener를 택하면 서명 방식 결정으로 이어집니다. 이것을 나중에 확인하면 앞선 모든 설계를 되돌려야 하므로, 보안 담당자와 먼저 합의해야 합니다.
</details>

3. Lattice 비용은 어떻게 추정해야 합니까?
   - A) 체인이 깊으면 서비스 프로비저닝 요금이 늘어난다
   - B) 체인 깊이·fan-out·retry를 포함한 실제 서비스 호출과 데이터량·provisioned 시간을 집계한다
   - C) 체인 depth가 Cross-AZ 요금을 결정한다
   - D) 체인이 깊으면 quotas에 먼저 도달한다

<details>

<summary>정답 보기</summary>

**정답: B) 체인 깊이·fan-out·retry를 포함한 실제 서비스 호출과 데이터량·provisioned 시간을 집계한다**

**설명:**
단순 4-call 체인은 그 가정에서만 요청 4개를 만듭니다. 시간 요금·전송 byte·retry·접근 모델도 비용에 영향을 주며 이 자료에는 절감 실측이 없습니다.
</details>

4. 호출 체인 증거는 어떻게 유지해야 합니까?
   - A) 전환 후에는 애플리케이션이 변경되어 체인이 달라지기 때문
   - B) 전환 중 앱 trace를 유지하고 Lattice log·request ID와 연결한다
   - C) CloudWatch가 체인 depth 메트릭을 제공하지 않기 때문
   - D) 전환 후에는 비용 추정이 불필요하기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 전환 중 앱 trace를 유지하고 Lattice log·request ID와 연결한다**

**설명:**
Lattice 네이티브 span 부재가 앱 span을 없애거나 전환 후 호출 체인 분석을 불가능하게 만들지는 않습니다.
</details>

5. 평문 TCP 통신이 있는 환경에 권장되는 구성은?
   - A) 모든 서비스에 TLS를 도입해 전량 Lattice로 옮긴다
   - B) 서비스 HTTP/TLS listener와 TCP resource connectivity·기존 사설 대안을 별도로 평가한다
   - C) 평문 TCP 서비스를 모두 제거한다
   - D) Lattice의 Raw TCP listener를 활성화한다

<details>

<summary>정답 보기</summary>

**정답: B) 서비스 HTTP/TLS listener와 TCP resource connectivity·기존 사설 대안을 별도로 평가한다**

**설명:**
Resource configuration은 서비스 L7 routing/authentication을 그대로 받지 않는 TCP 모델입니다. 프로토콜을 올바른 모델에 맞추고 controller/API 지원을 확인합니다.
</details>

6. "클러스터 내부 통신은 Lattice를 거치지 않게 유지"하는 선택의 트레이드오프는?
   - A) 트레이드오프 없이 항상 유리하다
   - B) 비용과 레이턴시에는 유리하지만, k8s Service DNS 직접 호출은 auth policy가 평가되지 않으므로 내부 통신의 인가를 NetworkPolicy나 애플리케이션 계층에서 별도로 설계해야 한다
   - C) 인가는 유지되지만 관측성을 잃는다
   - D) Gateway API Controller가 동작하지 않게 된다

<details>

<summary>정답 보기</summary>

**정답: B) 비용과 레이턴시에는 유리하지만, k8s Service DNS 직접 호출은 auth policy가 평가되지 않으므로 내부 통신의 인가를 NetworkPolicy나 애플리케이션 계층에서 별도로 설계해야 한다**

**설명:**
Lattice의 강점은 클러스터·VPC·계정 경계를 넘는 통신이고, 같은 클러스터 안의 통신에는 이점이 없으면서 비용과 레이턴시를 추가합니다. 그래서 경계를 넘는 통신만 Lattice로 두는 것이 합리적인 경우가 많습니다. 그러나 `IAMAuthPolicy`는 Gateway/HTTPRoute/GRPCRoute를 통과하는 트래픽만 인가하므로, 내부 통신을 Lattice에서 빼면 그 구간의 인가가 사라집니다. 비용 최적화와 인가 일관성이 상충하는 지점입니다.
</details>

7. 장애 범위는 어떻게 비교해야 합니까?
   - A) Lattice는 관리형이므로 장애가 발생하지 않는다
   - B) 양쪽 경로 모두 개별·공유 의존성이 있으므로 영향 서비스·AZ·정책·복구 제어를 평가한다
   - C) 두 모델의 장애 범위는 동일하다
   - D) sidecar 모델이 장애 범위가 더 넓다

<details>

<summary>정답 보기</summary>

**정답: B) 양쪽 경로 모두 개별·공유 의존성이 있으므로 영향 서비스·AZ·정책·복구 제어를 평가한다**

**설명:**
Proxy 실패는 개별일 수 있지만 공통 mesh 설정은 넓게 실패할 수 있습니다. Lattice 장애가 자동으로 전체 East-West 장애는 아니며 고객 정책·target·controller 복구도 존재합니다.
</details>

8. 다음 중 공식 문서로 확인되지 않아 `확인 필요`로 표시된 항목은?
   - A) SigV4 서비스명이 `vpc-lattice-svcs`라는 점
   - B) API Gateway가 Lattice 서비스 네트워크를 private integration 대상으로 네이티브 지원하는지 여부
   - C) App Mesh 지원 종료일이 2026년 9월 30일이라는 점
   - D) listener protocol이 HTTP/HTTPS/TLS_PASSTHROUGH 3종이라는 점

<details>

<summary>정답 보기</summary>

**정답: B) API Gateway가 Lattice 서비스 네트워크를 private integration 대상으로 네이티브 지원하는지 여부**

**설명:**
API Gateway가 Lattice 서비스 네트워크를 private integration 대상으로 네이티브 지원한다는 근거는 찾지 못했습니다. 확인된 패턴은 API Gateway → VPC Link → ALB/NLB → Lattice 또는 프록시·페더레이션 계층 경유입니다. 다른 `확인 필요` 항목은 quotas의 정확한 값, Lattice의 Target 선택이 호출자 AZ를 고려하는지, TLS_PASSTHROUGH listener에 auth policy 설정 시 API 거동, ECH 지원 여부입니다. A·C·D는 모두 1차 자료로 확인된 사실입니다.
</details>
