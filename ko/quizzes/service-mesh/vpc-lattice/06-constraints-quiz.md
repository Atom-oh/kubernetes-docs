# 제약사항과 의사결정 포인트 퀴즈

이 퀴즈는 Lattice 전환의 제약 6개와 의사결정 순서, 과금 구조에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 제약 6개 중 "AWS가 기능을 추가해도 해소되지 않는 원리적 제약"에 해당하는 것은?
   - A) SigV4 서명의 애플리케이션 영향과 Envoy iptables 예외 설정
   - B) TLS Passthrough와 IAM Auth Policy의 양립 불가, Raw TCP 미지원
   - C) Hop 단위 과금과 STS 의존성
   - D) Failure domain 집중과 quotas 제한

<details>

<summary>정답 보기</summary>

**정답: B) TLS Passthrough와 IAM Auth Policy의 양립 불가, Raw TCP 미지원**

**설명:**
이 두 제약은 "TLS를 종료해야 헤더를 볼 수 있고, TLS가 없으면 SNI도 없다"는 하나의 사실에서 나옵니다. SigV4 검증은 `Authorization` 헤더 파싱을 전제하므로 TLS를 종료하지 않으면 물리적으로 불가능하고, 평문 TCP에는 라우팅 근거(SNI)가 아예 없습니다. 나머지 제약들(서명 방식, iptables 예외, 과금, failure domain)은 설계와 운영으로 다룰 수 있는 항목입니다.
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

3. Lattice 과금에서 "호출 체인 depth가 비용을 지배한다"는 것의 의미는?
   - A) 체인이 깊으면 서비스 프로비저닝 요금이 늘어난다
   - B) 과금이 hop 단위이므로 4홉 체인에서는 사용자 요청 하나가 Lattice 요청 4건을 만들고, 비용은 사용자 요청 수 × 체인 depth에 비례한다
   - C) 체인 depth가 Cross-AZ 요금을 결정한다
   - D) 체인이 깊으면 quotas에 먼저 도달한다

<details>

<summary>정답 보기</summary>

**정답: B) 과금이 hop 단위이므로 4홉 체인에서는 사용자 요청 하나가 Lattice 요청 4건을 만들고, 비용은 사용자 요청 수 × 체인 depth에 비례한다**

**설명:**
과금 3축은 서비스 프로비저닝(시간당), 데이터 처리(GB당, inter-AZ 포함), 요청 수(HTTP/HTTPS) 또는 TCP 연결 수(TLS listener)입니다. 각 홉에서 요청 수와 데이터 처리 요금이 발생하므로 체인 depth가 비용 배수가 됩니다. AS-IS(App Mesh)에서는 요청당 요금이 없고 비용이 Envoy의 컴퓨팅 리소스로 나타났으므로, 이 전환은 비용 모델을 "컴퓨팅 리소스"에서 "요청 수"로 바꿉니다. 결과적으로 chatty한 통신과 깊은 체인이 비싸집니다.
</details>

4. "호출 체인 depth 데이터를 전환 전에 수집해야 한다"고 강조하는 이유는?
   - A) 전환 후에는 애플리케이션이 변경되어 체인이 달라지기 때문
   - B) 전환 후 Lattice는 trace span을 만들지 않으므로 이 데이터를 얻기 어려워지기 때문
   - C) CloudWatch가 체인 depth 메트릭을 제공하지 않기 때문
   - D) 전환 후에는 비용 추정이 불필요하기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 전환 후 Lattice는 trace span을 만들지 않으므로 이 데이터를 얻기 어려워지기 때문**

**설명:**
Lattice는 X-Ray segment/span을 생성하지 않고 trace ID도 주입하지 않습니다. 현재 AS-IS에서는 Envoy가 span을 만들어주므로 분산 추적 데이터로 체인 depth를 알 수 있지만, 전환 후에는 애플리케이션에 OpenTelemetry 계측을 넣지 않는 한 이 데이터가 없습니다. 체인 depth는 비용 추정의 핵심 입력값이므로 지금 수집해야 합니다. 같은 이유로 서비스 쌍별 RPS와 데이터 전송량도 Envoy 메트릭이 살아 있는 동안 수집해야 합니다.
</details>

5. 평문 TCP 통신이 있는 환경에 권장되는 구성은?
   - A) 모든 서비스에 TLS를 도입해 전량 Lattice로 옮긴다
   - B) Hybrid — HTTP/HTTPS/gRPC는 Lattice, TLS가 있는 TCP는 TLS Passthrough, 평문 TCP는 NLB나 기존 경로 유지
   - C) 평문 TCP 서비스를 모두 제거한다
   - D) Lattice의 Raw TCP listener를 활성화한다

<details>

<summary>정답 보기</summary>

**정답: B) Hybrid — HTTP/HTTPS/gRPC는 Lattice, TLS가 있는 TCP는 TLS Passthrough, 평문 TCP는 NLB나 기존 경로 유지**

**설명:**
모든 것을 Lattice로 옮기려는 시도가 전환을 지연시키는 가장 흔한 원인입니다. 평문 TCP 서비스를 위해 TLS를 도입하는 작업까지 범위에 넣으면 애플리케이션 변경이 필요하고 일정이 통제를 벗어납니다. App Mesh 지원 종료(2026년 9월 30일)라는 기한이 있으므로, 기한 내에 반드시 옮겨야 하는 것(App Mesh에 의존하는 HTTP 통신)과 옮기지 않아도 되는 것(원래 App Mesh를 안 쓰던 평문 TCP)을 분리하는 것이 실무적으로 중요합니다. D는 존재하지 않는 기능입니다.
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

7. Failure domain 관점에서 AS-IS(sidecar)와 TO-BE(Lattice)의 차이를 올바르게 서술한 것은?
   - A) Lattice는 관리형이므로 장애가 발생하지 않는다
   - B) sidecar는 장애가 국소적(Envoy 하나 = Pod 하나)이고 고객이 개입할 수 있으나, Lattice 장애는 East-West 전면에 영향을 주고 고객의 직접 개입 수단이 제한적이다
   - C) 두 모델의 장애 범위는 동일하다
   - D) sidecar 모델이 장애 범위가 더 넓다

<details>

<summary>정답 보기</summary>

**정답: B) sidecar는 장애가 국소적(Envoy 하나 = Pod 하나)이고 고객이 개입할 수 있으나, Lattice 장애는 East-West 전면에 영향을 주고 고객의 직접 개입 수단이 제한적이다**

**설명:**
관리형 서비스는 개별 장애 확률이 낮지만 장애 시 범위가 넓고 고객이 손댈 수단이 제한적입니다. sidecar 모델은 장애가 잦을 수 있지만 국소적이고 Pod 재시작·설정 롤백·sidecar 우회 같은 대응이 가능합니다. 여기에 IAM Auth를 쓰면 STS가 데이터 경로 의존성이 되어, credential 갱신 실패 시 서명이 불가능해지고 미서명 요청은 403이 됩니다. 완화 수단은 credential 캐시 수명 확인, 갱신 실패 거동 테스트, critical 경로 이중화, 점진적 전환과 롤백 경로 확보, RTO/RPO 재산정입니다.
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
