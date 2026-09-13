# 레이턴시 영향 분석 퀴즈

이 퀴즈는 Lattice 전환의 레이턴시 악화·개선 요인과 PoC 측정 설계에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Lattice 전환의 레이턴시 영향을 사전에 "몇 ms 늘어난다"로 단정할 수 없는 이유는?
   - A) AWS가 레이턴시 수치를 공개하지 않기 때문이다
   - B) Proxy 처리·네트워크·TLS 재사용·인증이 함께 바뀌므로 실제 workload를 측정한다
   - C) Lattice가 아직 GA가 아니기 때문이다
   - D) 레이턴시는 리전에 따라서만 결정되기 때문이다

<details>

<summary>정답 보기</summary>

**정답: B) Proxy 처리·네트워크·TLS 재사용·인증이 함께 바뀌므로 실제 workload를 측정한다**

**설명:**
이 자료에는 Lattice 지연 실측이 없습니다. 방향과 크기는 시험한 설정에 따라 다르므로 microsecond 추정이나 개선 보장을 관측 결과로 제시하지 않습니다.
</details>

2. p50과 p99의 요인 구성이 다르다는 것은 무엇을 의미하는가?
   - A) p99는 항상 p50보다 나쁘므로 p50만 보면 된다
   - B) 중앙값과 tail은 경합·cold start·routing에 다르게 반응할 수 있으므로 둘 다 측정한다
   - C) p50과 p99는 같은 요인의 영향을 받으므로 하나만 측정하면 된다
   - D) p99는 노이즈이므로 무시해야 한다

<details>

<summary>정답 보기</summary>

**정답: B) 중앙값과 tail은 경합·cold start·routing에 다르게 반응할 수 있으므로 둘 다 측정한다**

**설명:**
Percentile별 반응 차이는 조사할 가설이며 p50 악화·p99 개선의 보장이 아닙니다. 분포와 함께 오류·처리량·workload 조건을 기록합니다.
</details>

3. 레이턴시 관점에서 "프록시 홉 하나보다 큰 영향을 줄 수 있다"고 언급된 클라이언트 설정은?
   - A) DNS 캐시 TTL
   - B) keepalive와 connection pool 설정
   - C) 로그 레벨
   - D) 요청 타임아웃 값

<details>

<summary>정답 보기</summary>

**정답: B) keepalive와 connection pool 설정**

**설명:**
인용 benchmark에서는 해당 workload의 연결 재사용이 중요했습니다. 새 TCP 연결에는 setup이 추가되며 TLS handshake는 TLS를 사용할 때 적용됩니다. Lattice 지연 실측은 아닙니다.
</details>

4. PoC 측정 매트릭스에서 `IAM Auth on`과 `IAM Auth off`의 차이가 알려주는 것은?
   - A) Cross-AZ 경유 비용
   - B) 조건이 같을 때 서명·자격 증명 처리·활성 정책 평가가 합쳐진 효과
   - C) Envoy CPU 경합 해소 효과
   - D) 경로 변경의 순수 효과

<details>

<summary>정답 보기</summary>

**정답: B) 조건이 같을 때 서명·자격 증명 처리·활성 정책 평가가 합쳐진 효과**

**설명:**
Auth on/off는 HMAC만 분리하지 않습니다. 부하·연결 설정을 고정한 반복 실행에서 자격 증명 갱신·실패·처리량도 보고합니다.
</details>

5. Cross-AZ에 대한 설명으로 올바른 것은?
   - A) 레이턴시 악화 요인이면서 동시에 별도의 추가 과금 요인이다
   - B) 레이턴시 악화 요인이지만, Lattice 경유 트래픽에는 별도의 inter-AZ 요금이 없고 data processing 요금에 포함된다
   - C) 레이턴시와 과금 모두에 영향이 없다
   - D) Lattice는 항상 호출자와 같은 AZ의 Target을 선택하므로 고려할 필요가 없다

<details>

<summary>정답 보기</summary>

**정답: B) 레이턴시 악화 요인이지만, Lattice 경유 트래픽에는 별도의 inter-AZ 요금이 없고 data processing 요금에 포함된다**

**설명:**
Cross-AZ는 물리적 거리로 인해 레이턴시를 늘리지만(실측 기준선: 같은 AZ 0.339 ms vs 다른 AZ 0.544 ms), 과금 측면에서는 Lattice가 별도의 inter-AZ 요금을 청구하지 않고 data processing 요금에 포함시킵니다. D는 틀렸습니다 — Lattice의 Target 선택이 호출자 AZ를 고려하는지는 공식 문서로 확인되지 않았으므로 PoC에서 실측해야 하며, 그래서 측정 매트릭스에 AZ 축이 있습니다.
</details>

6. PoC 측정 설계에서 웜업이 필요한 이유와, 그럼에도 첫 요청 지연을 따로 기록해야 하는 이유는?
   - A) 웜업은 불필요하며 첫 요청만 측정하면 된다
   - B) Credential이나 connection pool이 cold이면 수립 작업이 추가될 수 있으므로 첫 요청·웜업 후 지연을 별도 기록하고 콜드 스타트가 잦으면 둘 다 평가하기 때문이다
   - C) 웜업은 p50만 개선하고 p99에는 영향이 없기 때문이다
   - D) 첫 요청은 항상 실패하기 때문이다

<details>

<summary>정답 보기</summary>

**정답: B) Credential이나 connection pool이 cold이면 수립 작업이 추가될 수 있으므로 첫 요청·웜업 후 지연을 별도 기록하고 콜드 스타트가 잦으면 둘 다 평가하기 때문이다**

**설명:**
Cache나 connection pool이 cold 상태이면 첫 요청에 credential 획득·연결 수립이 포함될 수 있습니다. 획득 경로는 provider에 따라 IRSA는 STS, EKS Pod Identity는 node agent와 EKS Auth를 사용합니다. TLS handshake 작업은 TLS 연결에만 적용됩니다. 첫 요청과 웜업 후 지연을 provider/cache/transport 상태와 함께 별도 기록하며, 모든 첫 요청이 직접 STS를 호출하거나 TLS를 수립한다고 가정하지 않습니다. 콜드 스타트가 잦으면 두 조건을 모두 평가합니다.
</details>
