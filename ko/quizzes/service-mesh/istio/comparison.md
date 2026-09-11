# Istio Comparison 퀴즈

> **과거 실험 보고**: Istio 1.30.2 / EKS 1.36.2. 현재 지원 매트릭스가 아닙니다
> **검토일**: 2026년 9월 11일

이 퀴즈는 Sidecar Mode와 Ambient Mode 선택 기준, 특히 보고된 EKS 측정의 한계에 대한 이해도를 테스트합니다. 이번 감사에서 해당 실험을 재현하지 않았습니다.

## 객관식 문제 (1-6번)

### 문제 1: Ambient waypoint 503의 원인 근거

보고된 롤아웃 집계만으로 waypoint 503의 원인에 대해 내릴 수 있는 결론은?

A. IP 중복 할당이 입증되었다

B. 연결 생명주기 경쟁은 가설이며 원인 확정에는 프록시 응답 플래그와 endpoint·연결 시간선이 필요하다

C. NetworkPolicy가 모든 실패의 원인임이 입증되었다

D. 집계는 STRICT mTLS 미지원을 입증한다

<details>
<summary>정답 및 해설</summary>

**정답: B**

**해설:**

HTTP 상태 집계만으로 근본 원인을 확정할 수 없습니다. Pod 종료, endpoint 전파, 애플리케이션·프록시 drain, timeout과 연결 풀이 모두 영향을 줄 수 있습니다. 원문의 IP 재사용·ztunnel 알림 설명에는 보관된 진단 시간선이 없었습니다. 가설을 확정된 원리로 가르치기보다 실제 upstream host, 응답 플래그, Pod UID와 연결 이벤트를 조사해야 합니다.

**참고 자료:**

- [Sidecar vs Ambient Mode 선택 가이드](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode: Waypoint Proxy](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### 문제 2: 보고된 EKS 결과 해석

조정 전 sidecar는 60,000건 중 HTTP 503 324건·비HTTP 오류 2건, ambient L4는 60,000건 중 0건·195건, ambient L7은 59,913건 중 1,528건·84건을 기록했습니다. 근거가 뒷받침하는 해석은?

A. Ambient가 언제나 더 안정적이다

B. 이 표본에서 L7의 HTTP 503 비율이 높았으며 L4의 HTTP 503 0건에도 비HTTP 실패 195건은 남아 있다

C. 모든 오류 범주의 동일한 근본 원인이 입증되었다

D. Fortio SocketCount가 waypoint upstream 풀을 직접 측정한다

<details>
<summary>정답 및 해설</summary>

**정답: B**

**해설:**

HTTP 503 비율은 sidecar 0.54%, L7 약 2.55%이며 표본의 비율 차이는 약 4.72배입니다. 제품 고유의 배수가 아닙니다. HTTP 503 0건은 전체 실패 0건이 아닙니다. Fortio 비HTTP 코드 -1만으로 구체적인 reset/EOF/timeout 원인을 알 수 없습니다. SocketCount는 client 소켓이며 가장 많았던 것은 L4(1,652)가 아닌 L7(2,486)입니다. 요청 QPS × 시간으로 정확한 완료 호출 수가 보장되지 않고, 다른 롤아웃 횟수도 인과 비교를 제한합니다.

**참고 자료:**

- [Sidecar vs Ambient Mode 선택 가이드: 무중단 rollout 실측 결과](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 문제 3: NetworkPolicy와 ambient

보고된 VPC CNI 실험에서 정책 적용을 확인했고, 8080만 허용한 ingress 규칙이 관측한 HBONE 경로를 차단했습니다. 다음 확인 사항은?

A. 모든 NetworkPolicy를 제거한다

B. 필요한 TCP 15008 터널 경로를 적절한 범위로 허용하고 출발지·identity·내부 포트 정책 경계를 검증한다

C. mTLS를 PERMISSIVE로 바꾼다

D. CNI를 재시작한 뒤 정책이 맞다고 가정한다

<details>
<summary>정답 및 해설</summary>

**정답: B**

**해설:**

보고된 경로는 TCP 15008 허용 뒤 복구되었습니다. 해당 경로의 근거이며 모든 CNI나 기존 정책이 동일하게 동작한다는 증거는 아닙니다. 외부 터널 허용만으로 내부 트래픽의 최소 권한 정책이 완성되지 않습니다. 출발지 선택자, waypoint 경유, DNS·컨트롤 플레인 의존성과 실제 적용을 확인하세요. Sidecar의 애플리케이션 포트 결과 역시 검사 범위 안의 관측입니다.

**참고 자료:**

- [Sidecar vs Ambient Mode 선택 가이드: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 문제 4: 비멱등 API와 retry

주문 생성 같은 비멱등 명령 경로에서 mesh retry를 기본적으로 명시해 끄는 이유는?

A. Retry가 언제나 애플리케이션보다 CPU를 많이 소비한다

B. 실패·소실된 응답만으로 서버 결과를 알 수 없어 재전송이 이미 commit한 명령을 반복할 수 있다

C. Retry는 STRICT mTLS와 호환되지 않는다

D. Ambient에는 L7 retry 기능이 없다

<details>
<summary>정답 및 해설</summary>

**정답: B**

**해설:**

Timeout, reset 또는 오류 응답이 항상 명령의 부작용이 없었음을 입증하지는 않습니다. 서버에 적절한 영속 멱등성·트랜잭션 처리가 없다면 미확정 쓰기의 재생이 작업을 중복시킬 수 있습니다. 특정 waypoint 경쟁 원인을 입증해야만 생기는 위험이 아닙니다. 과거 T2의 중복 0건으로 안전성이나 신뢰할 만한 빈도도 추정할 수 없습니다. Client가 무한 실행하고 요청 수가 명시한 시간·속도와 맞지 않으며 관측 오류를 숨길 수 있었기 때문입니다. 수정한 시간 제한 observer도 업무 트랜잭션 원장이 아닙니다. 완전한 관측으로 안정적인 명령 ID와 응답 소실 사례를 측정해야 합니다.

**참고 자료:**

- [Sidecar vs Ambient Mode 선택 가이드: Retry 완화책의 위험성](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 문제 5: 데이터 플레인 동작의 공정한 비교

원시 실패와 retry로 숨겨진 실패를 구분하기 위한 필수 출발점은?

A. 최종 GET 성공 수만 비교한다

B. Sidecar retry는 유지하고 ambient에서만 끈다

C. 양쪽 쓰기 route를 attempts: 0으로 맞추고 원시 HTTP·비HTTP 오류, retry counter, upstream 전달 수와 최종 결과를 수집한다

D. 평균 CPU가 가장 낮은 모드를 선택한다

<details>
<summary>정답 및 해설</summary>

**정답: C**

**해설:**

Sidecar와 waypoint Envoy는 L7 retry를 수행하지만 ztunnel은 HTTP 503을 해석하거나 HTTP 요청을 replay할 수 없습니다. 양쪽 쓰기 retry를 동일하게 끄고 upstream_rq_retry, 실제 전달 수, 안정적인 명령 ID와 client 집계를 기록하세요. 부하, 버전, 리소스와 롤아웃 노출도 통제하고 반복해야 합니다. 관측을 더 공정하게 분리하지만 한 번의 실행으로 제품 고유 안정성이 증명되지는 않습니다.

**참고 자료:**

- [Sidecar vs Ambient Mode 선택 가이드: 원시 실패 측정](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Retry 및 Timeout](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

---

### 문제 6: Cilium 인증과 암호화

문서화된 Cilium mutual authentication에서 authentication을 required로 설정하면 무엇을 의미하나요?

A. 모든 payload가 자동으로 workload TLS를 사용한다

B. 데이터 경로 밖의 peer identity handshake와 payload 암호화는 별개이며 암호화를 따로 설정·검증해야 한다

C. Istio PeerAuthentication STRICT와 구현·성숙도가 동일하다

D. 인가 정책이 더 이상 필요 없다

<details>
<summary>정답 및 해설</summary>

**정답: B**

**해설:**

릴리스 Cilium 1.20.1 문서는 이 방식을 Beta로 표시하고 애플리케이션 데이터 경로와 분리된 out-of-band handshake로 설명합니다. 인증 정책만으로 payload가 암호화되지는 않습니다. 지원되는 WireGuard/IPsec 암호화의 플랫폼·트래픽 범위 제한을 별도로 확인하세요. 다른 구현이나 preview mTLS는 자체 기능·플랫폼 근거가 필요하며 이 authentication 설정으로 자동 활성화되지 않습니다.

**참고 자료:**

- [Cilium Service Mesh 보안](../../../service-mesh/cilium-service-mesh/03-security.md)

</details>

---

## 점수 계산

- 6문제 중 맞은 개수를 확인하세요.
- 6/6: Sidecar, Ambient, Cilium 선택과 retry 리스크를 실측 근거로 설명할 수 있는 수준입니다.
- 4-5/6: 핵심 개념은 이해했지만 raw failure 측정 또는 인증·암호화 구분을 다시 확인하세요.
- 0-3/6: [Sidecar vs Ambient Mode 선택 가이드](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)를 처음부터 다시 읽어보세요.

## 학습 자료

- [Sidecar vs Ambient Mode 선택 가이드](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [mTLS](../../../service-mesh/istio/security/01-mtls.md)
- [Cilium Service Mesh 보안](../../../service-mesh/cilium-service-mesh/03-security.md)

## 공식 근거

- [Istio ambient L7 feature status](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md)
- [Cilium 1.20.1 mutual authentication](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
