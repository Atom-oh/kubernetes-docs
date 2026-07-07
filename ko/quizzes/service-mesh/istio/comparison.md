# Istio Comparison 퀴즈

> **지원 버전**: Istio 1.30 / EKS 1.36
> **마지막 업데이트**: 2026년 7월 7일

이 퀴즈는 Sidecar Mode와 Ambient Mode 선택 기준, 특히 EKS 1.36 실측 결과에 대한 이해도를 테스트합니다.

## 객관식 문제 (1-4번)

### 문제 1: Ambient waypoint 503의 근본 원인

Ambient 모드에서 rollout 중 waypoint 경로로 간헐적 503이 발생하는 근본 원인으로 옳은 것은?

A. Pod가 재시작될 때 IP가 중복 할당되기 때문
B. waypoint가 목적지 IP:Port 기준 커넥션을 재사용하는데, ztunnel이 Pod 종료를 waypoint에 통지하지 않기 때문
C. NetworkPolicy가 waypoint 트래픽을 차단하기 때문
D. STRICT mTLS가 waypoint에서 지원되지 않기 때문

<details>
<summary>정답 및 해설</summary>

**정답: B**

**해설:**

waypoint(Envoy)는 목적지 IP:Port 기준으로 커넥션 풀을 관리하며 재사용한다. ztunnel은 대상 Pod가 종료돼도 이를 상위 waypoint에 명시적으로 통지하지 않는다. 종료된 Pod와 동일한 IP가 새 Pod에 재할당되면, waypoint가 유효하지 않은 기존 연결을 재사용해 503이 발생할 수 있다. 이것이 우려의 근거가 되는 메커니즘이며 — IP 중복 할당이 아니라 **연결 생명주기 관리**다 — §4의 실측 503 비율이 이와 일관된다.

**참고 자료:**
- [Sidecar vs Ambient Mode 선택 가이드](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode: Waypoint Proxy](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### 문제 2: EKS 1.36 실측 결과 해석

전용 단일 테넌트 EKS 1.36 클러스터에서 100qps × 600초(60,000건) 부하로 rollout을 반복한 실측 결과, sidecar는 503 비율 0.5%, ambient-L4(waypoint 미사용)는 실제 503 0건(대신 TCP 오류 0.3%), ambient-L7(waypoint 사용)은 503 2.6%였다. 이 결과에 대한 올바른 해석은?

A. ambient는 항상 sidecar보다 안정적이다
B. waypoint를 경유하면 sidecar보다 503 비율이 높아지지만, waypoint 없이 L4만 쓰면 실제 503은 발생하지 않는다
C. ambient-L4의 TCP 오류(0.3%)는 waypoint의 503과 동일한 현상이다
D. 소켓 사용량이 가장 적은 모드가 가장 안정적이다

<details>
<summary>정답 및 해설</summary>

**정답: B**

**해설:**

실측 데이터는 "ambient가 무조건 좋다/나쁘다"가 아니라 **waypoint 경유 여부**가 핵심 변수임을 보여준다. waypoint(L7)를 쓰는 ambient-L7은 sidecar보다 503 비율이 약 5배 높았고(2.6% vs 0.5%), waypoint를 쓰지 않는 ambient-L4는 실제 503이 0건이었다. 다만 ambient-L4도 실패가 없는 것은 아니며, TCP 레벨 연결 끊김(0.3%)이라는 다른 형태로 나타난다 — 이는 waypoint의 "죽은 연결에 요청을 흘려보내는" 503과는 다른 실패 모드(C는 오답)다. 소켓 사용량은 안정성 지표가 아니라 커넥션 재생성 빈도를 보여주는 참고 수치다(D는 오답) — 실제로 ambient-L4는 소켓을 가장 많이 썼음에도 503이 0건이었다.

**참고 자료:**
- [Sidecar vs Ambient Mode 선택 가이드: 무중단 rollout 실측 결과](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 문제 3: NetworkPolicy와 ambient

포트 기반 NetworkPolicy를 사용하는 클러스터에서 ambient 모드 Pod에 트래픽이 도달하지 않는 문제가 발생했다. 애플리케이션은 8080 포트를 사용한다. 가장 가능성이 높은 원인과 해결책은?

A. ambient는 NetworkPolicy를 지원하지 않으므로 NetworkPolicy를 제거해야 한다
B. 실제 트래픽이 HBONE 터널(TCP 15008)로 도착하므로, NetworkPolicy에 15008 인바운드 허용 규칙을 추가해야 한다
C. PeerAuthentication을 PERMISSIVE로 변경해야 한다
D. istio-cni DaemonSet을 재시작해야 한다

<details>
<summary>정답 및 해설</summary>

**정답: B**

**해설:**

ambient는 ztunnel이 Pod 트래픽을 HBONE(mTLS 터널)으로 감싸 포트 15008로 전달한다. 애플리케이션 포트(8080)만 허용하는 NetworkPolicy는 실제로 도착하는 15008 트래픽을 차단한다. 해결책은 대상 Pod에 TCP 15008 인바운드를 허용하는 규칙을 추가하는 것이다. sidecar는 사이드카가 애플리케이션과 동일한 Pod network namespace를 쓰므로 이런 추가 규칙이 필요 없다.

**참고 자료:**
- [Sidecar vs Ambient Mode 선택 가이드: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 문제 4: 비멱등 API와 retry 정책

주문 생성처럼 비멱등(non-idempotent)한 API 경로에 mesh 레벨 retry(예: waypoint retry, VirtualService retries)를 기본으로 적용하지 않는 것이 권장되는 이유는?

A. retry는 CPU 오버헤드가 너무 크기 때문
B. waypoint가 죽은 연결에 요청을 흘려보내 503을 반환했을 때, retry가 이미 처리된 요청을 다시 실행시켜 중복 실행(예: 중복 주문)을 유발할 수 있기 때문
C. retry는 STRICT mTLS와 호환되지 않기 때문
D. retry는 ambient 모드에서 지원되지 않기 때문

<details>
<summary>정답 및 해설</summary>

**정답: B**

**해설:**

503 자체는 클라이언트에 보이는 실패이지만, 그 이면에는 "요청이 서버에 도달해 처리가 끝났는데 응답만 유실된" 경우가 섞여 있을 수 있다(연결이 끊기는 시점과 애플리케이션 처리 완료 시점의 race). 이 경우 mesh retry는 같은 논리적 요청을 다른 커넥션으로 재전송하며, 서버가 멱등성을 보장하지 않는다면 요청이 두 번 처리된다. 주문 생성처럼 되돌릴 수 없는 작업에는 이 리스크가 특히 크므로, retry를 기본 적용하지 않고 별도로 검증하는 것이 안전하다. 후속 실측(T2)에서는 sidecar와 ambient-L7 waypoint retry 양쪽에 300초간 지속적인 rollout churn을 걸어봤지만 중복 실행은 0건이었다 — 이는 이 race가 *흔하다*는 확신을 낮출 뿐, *안전하다*는 것을 증명하지는 않는다. 매우 좁은 타이밍 창에서만 발생하는 문제라 더 길거나 더 높은 처리량의 테스트에서는 여전히 나타날 수 있다.

**참고 자료:**
- [Sidecar vs Ambient Mode 선택 가이드: Retry 완화책의 위험성](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

## 점수 계산

- 4문제 중 맞은 개수를 확인하세요.
- 4/4: Sidecar vs Ambient 선택 기준을 실측 근거로 설명할 수 있는 수준입니다.
- 2-3/4: 핵심 개념은 이해했지만 NetworkPolicy·retry 리스크 부분을 다시 확인하세요.
- 0-1/4: [Sidecar vs Ambient Mode 선택 가이드](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)를 처음부터 다시 읽어보세요.

## 학습 자료

- [Sidecar vs Ambient Mode 선택 가이드](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [mTLS](../../../service-mesh/istio/security/01-mtls.md)
