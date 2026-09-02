# Pod 네트워크 실측 벤치마크 퀴즈

1. `ping -c 200 -i 0.05`로 측정한 Pod 간 RTT 평균은 같은 노드 → 같은 AZ의 다른 노드 → 다른 AZ 순서로 어떻게 나타났나요?
   - A) 0.040 ms → 0.544 ms → 0.339 ms — 다른 AZ가 같은 AZ보다 빨랐다
   - B) 세 경로 모두 0.3 ms 안팎으로 차이가 없었다
   - C) 0.040 ms → 0.339 ms → 0.544 ms — 노드를 벗어나면 +0.30 ms, AZ를 벗어나면 다시 +0.21 ms가 더해지는 계단
   - D) 0.040 ms → 0.339 ms → 5.4 ms — AZ 경계가 RTT를 밀리초 단위로 늘렸다
<details>
<summary>정답 보기</summary>

**정답: C) 0.040 ms → 0.339 ms → 0.544 ms — 노드를 벗어나면 +0.30 ms, AZ를 벗어나면 다시 +0.21 ms가 더해지는 계단**

**설명:**
ping 평균(200회, 50 ms 간격, 손실 0/200)은 같은 노드 0.040 ms, 같은 AZ 0.339 ms, 다른 AZ 0.544 ms였습니다. 같은 AZ − 같은 노드 = +0.30 ms, 다른 AZ − 같은 AZ = +0.21 ms, 다른 AZ − 같은 노드 = +0.50 ms입니다. fortio HTTP(100 qps, 커넥션 4개, keepalive) p50도 0.259 → 0.461 → 0.704 ms로 같은 계단을 그렸고(+0.20 / +0.24 ms), HTTP p50 − ping 평균은 경로별 약 0.22 / 0.12 / 0.16 ms로 클라이언트+서버 유저 공간 스택의 비용입니다. 5.4 ms는 단일 플로우를 상한까지 채운 iperf3 전송 중 송신자의 TCP RTT(셰이퍼 큐잉)이며, 유휴 상태의 AZ 간 RTT가 아닙니다(D 오답). 비교하면 이 저장소의 Istio 비교 문서에서 사이드카 한 홉은 p50 +1.29 ms — AZ 한 홉보다 메시 한 홉이 더 비쌉니다.

</details>

2. iperf3 단일 TCP 스트림(`-P 1`)은 같은 AZ와 다른 AZ 모두 4.96 Gbps에서 멈췄고, 8 스트림(`-P 8`)에서는 두 경로 모두 9.94 Gbps가 나왔습니다. 이 두 숫자를 가장 잘 설명하는 것은?
   - A) 4.96 Gbps는 클라이언트 CPU 한 코어의 포화 때문이고, 8 스트림은 코어를 더 쓰기 때문에 빨라졌다
   - B) 4.96 Gbps는 EC2가 문서화한 단일 플로우 5 Gbps 상한(클러스터 플레이스먼트 그룹 밖)이고, 9.94 Gbps는 m5.xlarge "Up to 10 Gigabit"의 인스턴스 피크 — 인스턴스 대역폭을 다 쓰려면 플로우를 병렬화해야 한다
   - C) 4.96 Gbps는 m5.xlarge의 베이스라인 대역폭이고, 8 스트림에서 버스트 크레딧을 써서 피크에 도달했다
   - D) MTU 9001 점보 프레임이 단일 스트림에서는 비활성이었기 때문이다
<details>
<summary>정답 보기</summary>

**정답: B) 4.96 Gbps는 EC2가 문서화한 단일 플로우 5 Gbps 상한(클러스터 플레이스먼트 그룹 밖)이고, 9.94 Gbps는 m5.xlarge "Up to 10 Gigabit"의 인스턴스 피크 — 인스턴스 대역폭을 다 쓰려면 플로우를 병렬화해야 한다**

**설명:**
노드가 다른 두 Pod 사이의 단일 플로우는 같은 AZ(cli→srv-a) 4.96 Gbps, 다른 AZ(cli→srv-b) 4.96 Gbps로 완전히 같았고, 이는 AWS가 문서화한 단일 플로우 5 Gbps 한도입니다. 이때 iperf3가 보고한 클라이언트 CPU는 19.5 % / 20.0 %(한 코어 기준)에 그쳤으므로 CPU 병목이 아닙니다(A 오답) — CPU에 묶인 경우는 같은 노드 단일 스트림(29.97 Gbps, 클라이언트 99.8 %)입니다. m5.xlarge의 베이스라인은 1.25 Gbps, 피크는 10 Gbps이며(C 오답), 8 스트림의 9.94 Gbps가 바로 그 피크입니다. MSS 8949(MTU 9001)는 모든 실행에 동일하게 적용되었습니다(D 오답). 상한에 닿은 단일 플로우에서는 송신자 TCP RTT가 유휴 ping 0.34 ms(같은 AZ) / 0.54 ms(다른 AZ)에서 5.6 ms / 5.4 ms까지 커지고 cwnd는 약 4.3 MB에 이르렀으며, 재전송은 1 스트림에서 4 / 2회였다가 인스턴스 상한에 닿은 8 스트림에서 5,874 / 5,979회로 늘었습니다 — ENA allowance 셰이핑의 간접 신호입니다(카운터 자체는 수집하지 않음). 실무적으로 노드가 다른 두 Pod 사이의 gRPC 스트림 하나, Kafka 복제 fetch 하나는 약 5 Gbps를 넘을 수 없습니다.

</details>

3. 8 스트림 iperf3 대역폭은 같은 AZ와 다른 AZ가 똑같이 9.94 Gbps였는데, fortio 폐루프 최대 처리량(`-qps 0`, 커넥션 16개, 20초)은 같은 AZ 38,507 qps → 다른 AZ 25,602 qps로 떨어졌습니다. 왜일까요?
   - A) AZ 간 링크가 요청/응답 트래픽에는 대역폭을 절반으로 제한하기 때문에
   - B) 다른 AZ 경로에서 요청 오류가 늘어 재시도가 발생했기 때문에
   - C) srv-b가 있는 노드의 CPU가 srv-a 노드보다 느렸기 때문에
   - D) 리틀의 법칙(Little's law) — 커넥션 수가 16개로 고정되면 처리량 = 동시성 ÷ 지연이라 16 ÷ 0.000624 s ≈ 25,641 qps가 상한이고, AZ 홉이 더한 약 +0.2 ms의 지연이 처리량을 34 % 깎았다. 다른 AZ의 비용은 대역폭이 아니라 지연이다
<details>
<summary>정답 보기</summary>

**정답: D) 리틀의 법칙(Little's law) — 커넥션 수가 16개로 고정되면 처리량 = 동시성 ÷ 지연이라 16 ÷ 0.000624 s ≈ 25,641 qps가 상한이고, AZ 홉이 더한 약 +0.2 ms의 지연이 처리량을 34 % 깎았다. 다른 AZ의 비용은 대역폭이 아니라 지연이다**

**설명:**
폐루프 평균 지연은 같은 노드 0.355 ms, 같은 AZ 0.415 ms, 다른 AZ 0.624 ms였고, 16 ÷ 0.000355 = 45,070(실측 44,991), 16 ÷ 0.000415 = 38,554(실측 38,507), 16 ÷ 0.000624 = 25,641(실측 25,602)로 리틀의 법칙이 세 경로 모두에서 맞습니다. 모든 실행에서 오류는 0건이었고(B 오답) 응답 본문은 약 75바이트라 대역폭은 전혀 문제가 되지 않습니다(A 오답) — 같은 8 스트림 테스트가 두 경로에서 동일한 9.94 Gbps를 보였습니다. srv-a와 srv-b는 같은 m5.xlarge입니다(C 오답). 커넥션 풀이 고정된 요청/응답 서비스에서 AZ 홉이 가져가는 것은 처리량 34 %(38.5k → 25.6k qps)이며, 그 원인은 지연입니다. 참고로 같은 노드의 p99 1.695 ms·max 13.593 ms가 같은 AZ(0.728 / 4.502 ms)보다 나쁜 것은 클라이언트와 서버가 한 노드의 4 vCPU를 나눠 쓴 CPU 경합 때문이고 네트워크 때문이 아닙니다.

</details>

4. 같은 100 qps / 커넥션 4개 조건에서 `-keepalive=false`(요청마다 새 TCP 커넥션)로 바꾸자 다른 AZ 경로의 HTTP p50이 어떻게 변했나요?
   - A) 0.704 ms → 1.517 ms(+0.813 ms)로 두 배 이상 — 새 커넥션은 TCP 핸드셰이크 RTT 한 번에 소켓 생성/해제 약 0.3 ms가 더해진 비용이라, RTT가 긴 경로일수록 벌칙이 크다
   - B) 변화 없음 — 커널이 커넥션을 재사용하기 때문에
   - C) 0.704 ms → 0.813 ms로 소폭 증가
   - D) p50은 그대로였고 p99만 나빠졌다
<details>
<summary>정답 보기</summary>

**정답: A) 0.704 ms → 1.517 ms(+0.813 ms)로 두 배 이상 — 새 커넥션은 TCP 핸드셰이크 RTT 한 번에 소켓 생성/해제 약 0.3 ms가 더해진 비용이라, RTT가 긴 경로일수록 벌칙이 크다**

**설명:**
keepalive=false(30초, 3,000 요청) p50은 같은 노드 0.664 ms(+0.405), 같은 AZ 1.079 ms(+0.618), 다른 AZ 1.517 ms(+0.813)로, 경로의 RTT가 길수록 추가 비용이 커졌습니다 — 추가분은 대략 RTT 한 번(TCP 핸드셰이크)에 소켓 설정/해제 약 0.3 ms입니다. 다른 AZ의 ping 평균 RTT 0.544 ms에 약 0.3 ms를 더하면 실측 +0.813 ms와 대략 맞습니다. 0.813 ms는 새 p50 값이 아니라 증가폭입니다(C 오답). p50 자체가 두 배 이상 커졌으므로 D도 오답입니다. AZ를 넘는 서비스라면 커넥션 풀·keepalive를 유지하는 것이 AZ 홉 자체(+0.24 ms)보다 더 큰 지연을 아낍니다.

</details>

5. 180초 지속 테스트(4 스트림)에서 다른 AZ로 223.4 GB를 보냈습니다. 검증한 요금(`APN2-DataTransfer-Regional-Bytes`)으로 이 한 번의 실행 비용은 얼마였나요?
   - A) $0 — 같은 리전 안의 트래픽은 무료다
   - B) $2.23 — GB당 $0.01이 한 번 부과된다
   - C) 약 $4.47 — GB당 $0.01이 보내는 AZ의 "out"과 받는 AZ의 "in" 양쪽에 부과되어 방향당 $2.23, 합계 $4.47(실효 $0.02/GB)
   - D) 베이스라인 1.25 Gbps 이하 구간은 무료이고 버스트 구간만 과금된다
<details>
<summary>정답 보기</summary>

**정답: C) 약 $4.47 — GB당 $0.01이 보내는 AZ의 "out"과 받는 AZ의 "in" 양쪽에 부과되어 방향당 $2.23, 합계 $4.47(실효 $0.02/GB)**

**설명:**
`aws pricing get-products`로 확인한 usagetype `APN2-DataTransfer-Regional-Bytes`("Regional Data Transfer - in/out/between AZs …")는 GB당 $0.0100입니다. AZ 간 전송은 데이터가 각 AZ를 "나갈 때" 부과되므로 같은 계정 안의 일방향 벌크 전송이라도 보내는 AZ $0.01/GB "out" + 받는 AZ $0.01/GB "in" = 실효 $0.02/GB입니다. 180초 동안 223,376,179,200바이트(223.4 GB, 9.93 Gbps)를 보냈으므로 223.4 × $0.01 = 방향당 $2.23, 합계 $4.47입니다. T1 전체의 AZ 간 바이트는 12.41 + 24.85 + 223.38 = 260.6 GB로 약 $5.21입니다. 이 180초 동안 18개 구간이 9.92–9.94 Gbps로 평탄했고 1.25 Gbps 베이스라인으로의 하향은 관찰되지 않았지만, 요금은 대역폭 등급과 무관하게 바이트당 부과됩니다(D 오답).

</details>

6. 기본 `ndots:5` Pod(glibc 2.41)에서 `sts.ap-northeast-2.amazonaws.com`(점 3개)을 한 번 콜드 resolve할 때 tcpdump에 잡힌 DNS 쿼리 수와 NXDOMAIN 응답 수는?
   - A) 쿼리 2개, NXDOMAIN 0개 — 점이 3개라 바로 절대 이름으로 질의된다
   - B) 쿼리 10개, NXDOMAIN 8개 — search 목록의 후보 4개에 각각 A+AAAA를 보내 8번 NXDOMAIN을 받은 뒤 5번째 후보(절대 이름)에서 A 응답을 받는다
   - C) 쿼리 5개, NXDOMAIN 4개 — 후보마다 A 레코드 하나만 보낸다
   - D) 쿼리 4개, NXDOMAIN 2개
<details>
<summary>정답 보기</summary>

**정답: B) 쿼리 10개, NXDOMAIN 8개 — search 목록의 후보 4개에 각각 A+AAAA를 보내 8번 NXDOMAIN을 받은 뒤 5번째 후보(절대 이름)에서 A 응답을 받는다**

**설명:**
EKS Pod의 resolv.conf는 `search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal`과 `options ndots:5`입니다. 점이 5개 미만인 이름은 search 접미사 4개를 먼저 순서대로 시도하고, glibc는 후보마다 A와 AAAA를 병렬로 보냅니다(C 오답). 캡처된 순서는 `….bench-net.svc.cluster.local.` → `….svc.cluster.local.` → `….cluster.local.`(셋 다 CoreDNS kubernetes 플러그인의 권위 있는 NXDomain) → `….ap-northeast-2.compute.internal.`(VPC 리졸버로 포워딩, NXDomain) → 마지막으로 `sts.ap-northeast-2.amazonaws.com.`에서 A 10.0.3.84 / 10.0.2.129 응답 — 쿼리 10개, NXDOMAIN 8개, 순차 왕복 5번, 첫 패킷부터 4.37 ms이고 쓸모 있는 답은 마지막 0.38 ms에 도착했습니다. 워밍된 20회 반복의 중앙값도 3.78 ms인데, 끝에 점을 붙인 `sts.ap-northeast-2.amazonaws.com.`은 쿼리 2개·중앙값 0.80 ms입니다. CoreDNS의 `cache 30`이 NXDOMAIN도 캐시하므로 워밍 후의 비용은 업스트림 조회가 아니라 Pod↔CoreDNS 순차 왕복 5번 자체입니다. 파생 산술로, 요청마다 외부 이름 하나를 resolve하는 앱이 클러스터 전체 1,000회/s면 CoreDNS에 2,000이 아닌 10,000 쿼리/s가 들어오고 그중 8,000이 NXDOMAIN입니다. 쿼리 4개·NXDOMAIN 2개는 `kubernetes.default`(점 1개)의 결과입니다(D 오답).

</details>

7. 같은 `ndots:5` Pod에서 FQDN처럼 보이는 `kubernetes.default.svc.cluster.local`(끝에 점 없음)을 resolve하자 역시 쿼리 10개·NXDOMAIN 8개가 나왔습니다. 왜 search 목록을 다 돌았을까요?
   - A) CoreDNS의 `kubernetes` 플러그인은 `cluster.local` 존 밖의 이름만 즉시 응답하기 때문에
   - B) glibc가 `svc.cluster.local`로 끝나는 이름은 항상 Service 이름으로 간주하기 때문에
   - C) `.ap-northeast-2.compute.internal` 접미사가 search 목록 맨 앞에 있어서 먼저 시도되기 때문에
   - D) 이 이름의 점은 4개로 ndots 5보다 적기 때문에, glibc 입장에서는 "짧은 이름"이라 search 접미사 4개를 모두 붙여 본 뒤에야 원래 이름 그대로 질의한다 — 끝에 점을 붙이면 쿼리 2개로 끝난다
<details>
<summary>정답 보기</summary>

**정답: D) 이 이름의 점은 4개로 ndots 5보다 적기 때문에, glibc 입장에서는 "짧은 이름"이라 search 접미사 4개를 모두 붙여 본 뒤에야 원래 이름 그대로 질의한다 — 끝에 점을 붙이면 쿼리 2개로 끝난다**

**설명:**
`kubernetes.default.svc.cluster.local`의 점은 4개로 ndots 5에 미달합니다. 따라서 glibc는 `….bench-net.svc.cluster.local`, `….svc.cluster.local`, `….cluster.local`, `….ap-northeast-2.compute.internal`을 먼저 시도해 8번 NXDOMAIN을 받은 뒤(그중 compute.internal 후보는 CoreDNS가 업스트림으로 포워딩해 2.2 ms가 걸렸습니다) 다섯 번째에야 원래 이름으로 A 응답을 받습니다 — 콜드 walk 5.6 ms, 워밍 중앙값 3.63 ms. 같은 이름에 점 하나만 붙인 `kubernetes.default.svc.cluster.local.`은 쿼리 2개·NXDOMAIN 0개, 콜드 0.4–0.5 ms, 워밍 중앙값 0.46 ms입니다. `ndots:1` Pod에서는 점 없이도 쿼리 2개(중앙값 0.97 ms)였습니다. search 목록 순서는 네임스페이스 도메인 → `svc.cluster.local` → `cluster.local` → 노드 도메인이라 C는 오답이고, A·B는 glibc/CoreDNS의 실제 동작이 아닙니다. 설정 파일에 Service FQDN을 적을 때는 끝의 점까지 적는 것이 안전합니다.

</details>

8. `dnsConfig.options`로 `ndots:1`을 준 Pod에서는 외부 이름 쿼리가 10 → 2개로 줄었지만, 짧은 인클러스터 이름 `kubernetes.default`는 오히려 나빠졌습니다(쿼리 6개·NXDOMAIN 4개, 중앙값 2.04 ms vs ndots:5의 1.71 ms). 무슨 일이 있었나요?
   - A) 점 1개 ≥ ndots 1이므로 glibc가 `kubernetes.default.`를 먼저 절대 이름으로 질의했고, CoreDNS는 그 존이 없어 VPC 리졸버로 포워딩(NXDomain)한 뒤에야 search 목록을 걸어 `svc.cluster.local` 후보에서 답을 얻었다 — 클러스터 내부 이름이 업스트림 리졸버로 새어 나간다
   - B) ndots:1에서는 CoreDNS 캐시가 비활성화되기 때문에
   - C) `kubernetes.default`는 ndots:1에서는 전혀 resolve되지 않았다
   - D) glibc가 A와 AAAA를 순차적으로 보내기 때문에 두 배 느려졌다
<details>
<summary>정답 보기</summary>

**정답: A) 점 1개 ≥ ndots 1이므로 glibc가 `kubernetes.default.`를 먼저 절대 이름으로 질의했고, CoreDNS는 그 존이 없어 VPC 리졸버로 포워딩(NXDomain)한 뒤에야 search 목록을 걸어 `svc.cluster.local` 후보에서 답을 얻었다 — 클러스터 내부 이름이 업스트림 리졸버로 새어 나간다**

**설명:**
ndots:1 Pod에서 `kubernetes.default`(점 1개)는 먼저 절대 이름 `kubernetes.default.`로 나갔고, CoreDNS는 이 이름에 대한 존이 없어 VPC 리졸버로 포워딩해 1.6 ms 뒤 NXDomain을 돌려받았습니다. 그다음 `kubernetes.default.bench-net.svc.cluster.local`(NXDOMAIN), 마지막으로 `kubernetes.default.svc.cluster.local`에서 172.20.0.1 응답 — 쿼리 6개, NXDOMAIN 4개, 워밍 중앙값 2.04 ms로 ndots:5의 쿼리 4개·NXDOMAIN 2개·1.71 ms보다 나빴습니다(C 오답). 반대로 외부 이름은 큰 이득입니다: `sts.ap-northeast-2.amazonaws.com`과 `www.amazon.com`은 10 → 2 쿼리, 중앙값 3.5–3.8 → 0.5–0.9 ms(약 4–7배 빠르고 쿼리는 5배 감소). glibc는 기본적으로 A/AAAA를 병렬로 보내며(D 오답) CoreDNS 캐시와 Pod의 ndots는 무관합니다(B 오답). ndots:1을 쓰려면 인클러스터 Service는 `서비스.네임스페이스.svc.cluster.local` 형태의 FQDN으로 적어야 하고, 끝에 점을 붙이는 방식은 ndots 값과 무관하게 항상 쿼리 2개·약 0.4–0.8 ms로 동작합니다.

</details>

9. 이 문서의 fortio 레이턴시 표는 모두 `-r 0.00001`(10 µs 히스토그램 해상도)로 다시 측정한 것입니다. 첫 실행 결과를 버린 이유는?
   - A) 첫 실행에서 오류율이 높았기 때문에
   - B) fortio 기본 해상도 `-r 0.001`은 1 ms 버킷이라, 1 ms 미만 응답은 모두 한 버킷에 들어가 p50·p99 같은 분위수가 버킷 안 선형 보간값(예: 1 ms 미만이면 전부 p50 = 0.5 ms)으로 나왔기 때문 — 평균은 유효했지만 분위수는 의미가 없었다
   - C) 기본 해상도에서는 fortio가 p99.9를 계산하지 않기 때문에
   - D) 첫 실행이 실수로 keepalive 없이 돌았기 때문에
<details>
<summary>정답 보기</summary>

**정답: B) fortio 기본 해상도 `-r 0.001`은 1 ms 버킷이라, 1 ms 미만 응답은 모두 한 버킷에 들어가 p50·p99 같은 분위수가 버킷 안 선형 보간값(예: 1 ms 미만이면 전부 p50 = 0.5 ms)으로 나왔기 때문 — 평균은 유효했지만 분위수는 의미가 없었다**

**설명:**
이 벤치마크의 실제 p50은 0.259–0.704 ms(keepalive HTTP)처럼 전부 1 ms 미만입니다. fortio 기본 `-r 0.001`은 히스토그램 버킷이 1 ms라서 이런 값들은 모두 첫 버킷에 쌓이고, 분위수는 그 버킷 안에서 선형 보간되어 경로와 무관하게 p50 = 0.5 ms 같은 가짜 값이 나옵니다. 평균은 유효했지만 분위수는 폐기하고 `-r 0.00001`(10 µs 버킷)로 모든 fortio 실행을 다시 돌렸습니다. 모든 실행의 오류는 0건이었고(A 오답) 요청/응답 설정은 동일했습니다(D 오답). 서브밀리초 네트워크를 측정할 때는 도구의 히스토그램 해상도를 먼저 확인해야 한다는 교훈입니다.

</details>

10. 이 문서가 ClusterIP(kube-proxy iptables 홉)와 `trafficDistribution: PreferClose`를 측정하지 **않은** 이유로 옳은 것은?
   - A) fortio가 Service DNS 이름을 대상으로 지원하지 않기 때문에
   - B) kube-proxy가 IPVS 모드라 iptables 홉이 존재하지 않았기 때문에
   - C) 클러스터의 aws-load-balancer-controller 웹훅(`mservice.elbv2.k8s.aws`, `failurePolicy: Fail`)이 모든 Service CREATE를 가로채는데, 컨트롤러 Pod가 Gateway API `ListenerSet` CRD 부재로 48일간 CrashLoopBackOff 상태여서 웹훅 엔드포인트가 0개였고, 그 결과 클러스터 어디서도 Service를 만들 수 없었다 — 웹훅을 우회하지 않고 Pod IP만으로 측정했다
   - D) 측정했지만 Pod IP와 차이가 없어 표에서 생략했다
<details>
<summary>정답 보기</summary>

**정답: C) 클러스터의 aws-load-balancer-controller 웹훅(`mservice.elbv2.k8s.aws`, `failurePolicy: Fail`)이 모든 Service CREATE를 가로채는데, 컨트롤러 Pod가 Gateway API `ListenerSet` CRD 부재로 48일간 CrashLoopBackOff 상태여서 웹훅 엔드포인트가 0개였고, 그 결과 클러스터 어디서도 Service를 만들 수 없었다 — 웹훅을 우회하지 않고 Pod IP만으로 측정했다**

**설명:**
벤치마크 네임스페이스에 Service를 `kubectl apply`할 때마다 `Internal error occurred: failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"`로 거부됐습니다. 읽기 전용 진단 결과 kube-system의 aws-load-balancer-controller v3.2.1(레플리카 2)은 48일 동안 9,250번 재시작한 CrashLoopBackOff 상태였고, 컨테이너마다 `no matches for kind "ListenerSet" in version "gateway.networking.k8s.io/v1"`을 반복 기록한 뒤 약 2분 18초 만에 캐시 동기화 타임아웃으로 종료했습니다. 이 컨트롤러의 `MutatingWebhookConfiguration` `aws-load-balancer-webhook`은 `namespaceSelector: {}`로 클러스터 전체의 Service CREATE에 걸리고 `failurePolicy: Fail`이므로, 준비된 엔드포인트가 0개면 어느 네임스페이스에서도 Service 생성이 불가능합니다. 웹훅을 우회하거나 컨트롤러를 고치는 대신 fixture는 Pod IP만 사용했고, 따라서 ClusterIP 홉의 비용과 `PreferClose`(Kubernetes 1.31 베타, 1.33 GA)의 효과는 이 문서에 숫자가 없습니다(D 오답). kube-proxy는 `mode: "iptables"`였습니다(B 오답). 그 밖에 ENA allowance 카운터(`ethtool -S`, hostNetwork Pod 필요)도 수집하지 않았고, 모든 셀은 하루에 한 번 측정한 n = 1이라 SLA가 아닌 자릿수 기준점으로 읽어야 합니다.

</details>

---

[학습 자료로 돌아가기](../../networking/06-pod-network-benchmark.md) | [네트워킹 홈으로](../../networking/README.md)
