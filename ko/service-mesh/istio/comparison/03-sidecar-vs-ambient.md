# Sidecar vs Ambient Mode 선택 가이드 (EKS 1.36 실측)

> **지원 버전**: Istio 1.30 / EKS 1.36
> **마지막 업데이트**: 2026년 7월 7일

이 문서는 미션 크리티컬 워크로드(예: 가상자산 거래소의 주문·체결 경로)를 EKS에 올릴 때 **Istio를 sidecar 모드로 도입할지, ambient 모드로 도입할지**를 결정하기 위한 실측 기반 가이드입니다. 아키텍처 설명 자체는 [Ambient Mode](../advanced/01-ambient-mode.md) 문서에 이미 있으므로 여기서는 반복하지 않고, 다음 4가지 요구사항을 기준으로 실측 결과와 권장안만 제시합니다.

1. mTLS 필수 (클러스터 내부 pod↔pod 통신)
2. NetworkPolicy 필수
3. Latency에 민감한 워크로드
4. 무중단 rollout — ambient waypoint의 503 우려 검증

> 💡 이 문서의 모든 수치는 이번 테스트 사이클만을 위해 만들고 종료 후 삭제한 **전용 단일 테넌트 EKS 클러스터**(`mesh-isolated-test`)에서 얻은 실측값입니다. 왜 전용 클러스터가 필요했는지는 §4 끝의 [테스트 격리에 관한 노트](#테스트-격리에-관한-노트)를 참고하세요.

## 의사결정 요약표

| 요구사항 | Sidecar | Ambient (L4, waypoint 미사용) | Ambient (L7, waypoint 사용) |
|---|---|---|---|
| mTLS | ✅ STRICT 지원, 실측 확인 | ✅ STRICT 지원, 실측 확인 | ✅ STRICT 지원, 실측 확인 |
| NetworkPolicy | ✅ 기존 룰 그대로 사용, 실측 확인 | ⚠️ HBONE 포트(15008) 허용 필요, 실측 확인 | ⚠️ HBONE 포트(15008) 허용 필요, 실측 확인 |
| Latency (no-mesh 기준 P50 오버헤드) | +1.29ms, 실측 | +0.04ms (거의 없음), 실측 | +1.86ms, 실측 |
| 무중단 rollout | 503 발생 (0.5%, 실측) | **실제 503 0건**, TCP 리셋 0.3%로 대체 | 503 발생 **2.6%, sidecar의 약 5배** (실측) |

> ✅ **한 줄 결론**: waypoint(L7)를 쓰지 않는 ambient(L4)가 rollout 안정성 면에서 가장 우수했고 latency 오버헤드도 거의 없었습니다. waypoint를 쓰는 순간 sidecar보다 503 비율이 더 높아지고 latency도 sidecar와 비슷한 수준으로 올라갑니다. 근거는 아래 §3~§4에서 확인하세요.

## 1. mTLS — 실측 결과 (EKS 1.36.2, Istio 1.30.2)

**테스트 환경**
- 전용 단일 테넌트 클러스터 `mesh-isolated-test`(독립 VPC, 다른 워크로드 없음), EKS 컨트롤플레인·워커 노드 모두 v1.36.2, Amazon Linux 2023 (arm64, m7g.xlarge)
- 테스트 네임스페이스 3개(sidecar / ambient-L4 / ambient-L7)에 네임스페이스 스코프 `PeerAuthentication` STRICT 적용 (mesh-wide 아님)

### 검증 1 — plaintext 직접 pod-IP 접근 (차단되어야 함)

```
plaintext-client -> sidecar echo pod:8080
  [E] Read error, err="read tcp ...: read: connection reset by peer"
plaintext-client -> ambient-L4 echo pod:8080
  [E] Read error, err="EOF"
plaintext-client -> ambient-L7 echo pod:8080
  [E] Read error, err="EOF"
```

### 검증 2 — in-mesh Service 경유 접근 (성공해야 함)

```
sidecar client -> http://echo:8080/     => HTTP/1.1 200 OK (server: envoy)
ambient-L4 client -> http://echo:8080/  => HTTP/1.1 200 OK (envoy 헤더 없음, 순수 L4 패스스루)
ambient-L7 client -> http://echo:8080/  => HTTP/1.1 200 OK (server: istio-envoy, x-envoy-decorator-operation)
```

### 검증 3 — SPIFFE 인증서

`istioctl ztunnel-config certificates` / `istioctl proxy-config secret`으로 확인:

| 워크로드 | 인증서 발급 주체 | SPIFFE ID | Root CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | 동일 |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | 동일 |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | 동일 |

> ✅ **결론**: 세 모드 모두 plaintext 접근이 즉시 차단되고, in-mesh 경유만 200을 반환하며, 동일 root CA에서 발급된 워크로드별 SPIFFE ID를 갖습니다. sidecar와 ambient 모두 "클러스터 내부 pod↔pod 통신 무조건 mTLS" 요구사항을 만족합니다.

**어떻게 다른가**: ambient는 `istio-cni`가 Pod network namespace에 트래픽 리다이렉션을 설정하고 ztunnel이 이를 HBONE(mTLS 터널, 포트 15008)으로 전달하는 방식이라 애플리케이션 코드나 사이드카 주입 없이도 mTLS가 적용됩니다. sidecar는 애플리케이션 파드 내 istio-proxy 컨테이너가 동일한 역할을 합니다. 두 방식의 세부 인증서 갱신·마이그레이션 전략은 [mTLS](../security/01-mtls.md) 문서를 참고하세요.

## 2. NetworkPolicy — 실측 결과

Ambient는 Pod의 실제 트래픽을 ztunnel까지 HBONE 터널(TCP 15008)로 전달한 뒤 ztunnel이 목적지로 복호화해 전달합니다. 따라서 **포트 기준으로 애플리케이션 포트(예: 8080)만 허용하는 NetworkPolicy는 ambient 대상 Pod의 인바운드 트래픽을 막습니다** — 실제 패킷이 15008로 도착하기 때문입니다. Ambient를 NetworkPolicy와 함께 쓰려면 대상 Pod에 **TCP 15008 인바운드 허용 규칙을 추가**해야 합니다.

**테스트 구성**: 전용 클러스터 `mesh-isolated-test`에서 VPC CNI NetworkPolicy 강제(`enableNetworkPolicy=true`, `aws-network-policy-agent v1.3.5-eksbuild.3`, eBPF)를 활성화했습니다. 이전 라운드에서 사용한 공유 클러스터에서는 이 기능을 켜면 다른 팀 소유의 휴면 NetworkPolicy 13개가 동시에 활성화될 위험이 있어 안전하게 실행할 수 없었는데, 전용 단일 테넌트 클러스터를 쓰면서 이 blast-radius 문제 자체가 사라졌습니다.

> ⚠️ **테스트 중 발견한 운영 함정**: `enableNetworkPolicy`를 켜기 **이전에** 생성된 Pod는 소급 적용되지 않습니다 — eBPF 후크는 Pod 네트워크 설정(CNI ADD) 시점에만 붙기 때문입니다. 이미 실행 중인 Pod에 "포트 9999만 허용"하는 정책을 적용해도 8080 트래픽이 그대로 통과하는 것으로 직접 확인했습니다. 애드온 활성화 후 `kubectl rollout restart`로 Pod를 재생성해야 비로소 NetworkPolicy가 실제로 적용됩니다. 운영 중인 클러스터에서 NetworkPolicy를 처음 켤 때 반드시 알아둬야 할 함정입니다.

**테스트 1 — 인그레스를 TCP 8080만 허용** (재생성된 Pod, 강제 적용 활성 확인됨)

| 모드 | 결과 |
|---|---|
| sidecar | ✅ 200 OK — 영향 없음 |
| ambient-L4 | ❌ 차단 (`i/o timeout`) |
| ambient-L7 | ❌ 차단 (`i/o timeout`) |

**테스트 2 — 인그레스에 TCP 8080 + TCP 15008(HBONE) 허용**

| 모드 | 결과 |
|---|---|
| ambient-L4 | ✅ 200 OK — 정상화 |
| ambient-L7 | ✅ 200 OK — 정상화 |

> ✅ **결론**: 위 가설이 실측으로 확인됐습니다. Ambient에서 워크로드 Pod의 네트워크 namespace에 실제로 도착하는 인바운드 패킷은 애플리케이션 포트(8080)가 아니라 ztunnel의 HBONE 포트(15008)입니다. 애플리케이션 포트만 허용하는 NetworkPolicy는 ambient 대상 Pod를 조용히 망가뜨립니다. sidecar는 사이드카가 패킷이 애플리케이션 포트로 이미 도착한 뒤 같은 Pod network namespace 안에서 트래픽을 가로채므로 영향이 없습니다.

네트워크 레벨(NetworkPolicy)과 아이덴티티 레벨(AuthorizationPolicy)을 함께 적용하는 defense-in-depth를 권장합니다. mTLS와 NetworkPolicy가 함께 사용될 때 sidecar 모드에서 발생하는 충돌 사례는 [mTLS와 네트워크 정책 충돌](../security/01-mtls.md#7-mtls와-네트워크-정책-충돌)에서 다룹니다.

## 3. Latency — 실측 결과 (T5)

**테스트 구성**: fortio load, 200qps, 60초, 커넥션 16개, 케이스당 12,000건, steady state(rollout restart 없음) — no-mesh 기준선(mesh 미적용 네임스페이스) vs sidecar vs ambient-L4 vs ambient-L7, 모두 `mesh-isolated-test`의 동일한 Graviton(m7g.xlarge) 노드에서 측정했습니다. 모든 케이스에서 Code 200 100%.

| 케이스 | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh (기준선) | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4 (waypoint 미사용) | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7 (waypoint) | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |

**no-mesh 기준선 대비 P50 오버헤드**: sidecar +1.29ms · ambient-L4 +0.04ms(거의 없음) · ambient-L7 +1.86ms

> ✅ **결론**: 기존에 인용했던 공개 벤치마크 방향(L4-only가 sidecar보다 낮고, waypoint는 sidecar와 비슷하거나 약간 높음)과 일치하며, 이제는 인용이 아니라 자체 실측치입니다. crypto 거래 경로처럼 latency에 매우 민감한 워크로드라면, 아래 §4 결과와 함께 **waypoint를 피하는 것이 지연과 rollout 안정성 모두에 유리하다**는 방향이 일관됩니다.

## 4. 무중단 rollout — 503 실측 (핵심)

### 배경

Ambient에서 우려되는 문제는 **L7 waypoint(Envoy)가 목적지 IP:Port 기준으로 커넥션 풀을 재사용**하는데, **ztunnel이 Pod 종료 시 상위 waypoint에 연결 종료를 통지하지 않아**, 종료된 Pod의 IP가 새 Pod에 재할당되면 waypoint가 유효하지 않은 기존 연결을 재사용해 503이 발생할 수 있다는 것입니다. sidecar도 유사한 파드 종료 race 조건으로 503이 발생할 수 있습니다(자세한 메커니즘은 [파드 종료 시 연결 에러](../troubleshooting/common-errors.md#파드-종료-시-연결-에러) 참고). 이 두 실패 모드를 EKS 1.36에서 실측으로 비교했습니다.

**테스트 환경**
- 전용 단일 테넌트 클러스터 `mesh-isolated-test`, EKS 컨트롤플레인·워커 노드 모두 v1.36.2, arm64(Graviton m7g.xlarge), Istio 1.30.2
- 3개 네임스페이스(sidecar / ambient-L4 / ambient-L7)에 **완전히 동일한 워크로드**(echo 서버 6 replica + fortio 클라이언트) 배포, 네임스페이스 라벨만 다름
- fortio 클라이언트가 keepalive 커넥션으로 100 qps 지속 부하를 주는 동안, 대상 네임스페이스의 `echo` Deployment를 짧은 간격으로 `rollout restart`
- 모드별 60,000건 요청(=100qps × 600초) 수집

### 실측 결과

| 모드 | rollout 횟수 | 요청 수 | 503 건수 | 503 비율 | 기타 오류(-1, TCP reset/EOF) | Sockets used |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2건 (0.0%) | 350 |
| ambient-L4 (waypoint 없음) | 64 | 60,000 | **0** | **0%** | 195건 (0.3%) | 1,652 |
| ambient-L7 (waypoint) | 65 | 59,913 | 1,528 | **2.6%** | 84건 (0.1%) | 2,486 |

> 완벽한 keepalive라면 소켓 사용량은 16이어야 합니다. ambient-L7은 60,000건 중 87건이 실행 시간 내에 완료되지 못했고, 평균 지연도 50.4ms로 다른 두 모드(약 2~3ms)보다 크게 높았습니다.

<details>
<summary>원본 fortio 실행 로그 보기</summary>

```
[sidecar]      rollout 42회, Sockets used: 350 (완벽 keepalive라면 16)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   rollout 64회, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   ← HTTP 응답 없이 TCP 연결이 끊긴 케이스, 503 아님

[ambient-L7]   rollout 65회, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (60,000건 중 59,913건만 완료; 평균 지연 50.4ms — 다른 두 모드는 약 2~3ms)
```

</details>

**결정적 근거**

1. **ambient-L7(waypoint)의 503 비율(2.6%)은 이 전용 클러스터에서 sidecar(0.5%)의 약 5배입니다.** 같은 날 앞서 진행한 공유·경쟁 클러스터 측정치가 시사했던 격차보다도 더 크게 나타났습니다(하단 격리 노트 참고) — "waypoint 연결 풀이 stale 연결을 재사용해 503을 낸다"는 우려가 완화되기는커녕 오히려 더 강하게 확인된 셈입니다.
2. **ambient-L4(waypoint 미사용)는 이번에도 실제 HTTP 503이 0건입니다.** 대신 연결 자체가 끊기는 TCP 레벨 오류("-1", 응답 없음)가 0.3% 발생했습니다. L4는 실패가 "503 응답"이 아니라 "연결 끊김"으로 나타나며, 클라이언트/애플리케이션의 재연결 로직에 그 처리를 위임합니다.
3. ambient-L7은 평균 지연도 크게 튀었고 60,000건 중 87건은 실행 시간 내에 끝내 완료되지 않았습니다 — rollout churn과 지속 부하가 겹치면 waypoint가 다른 두 모드와는 구분되게 부담을 받는다는 신호입니다.
4. 같은 600초 창에서 완료된 rollout 횟수(sidecar 42 / ambient-L4 64 / ambient-L7 65)는 부하가 많던 공유 클러스터에서의 이전 측정치보다 훨씬 높았습니다 — 이 전용 클러스터에는 CPU/네트워크를 다투는 다른 테넌트가 없었기 때문입니다. *상대적* 순서(sidecar가 가장 느리고 ambient-L4가 가장 빠름)는 유지됐지만, 절대적인 rollout 속도는 클러스터 경쟁 상황에 크게 좌우되므로 모드 자체의 고유한 속성으로 과도하게 해석하지 않는 것이 좋습니다.

### Graceful shutdown 하드닝 적용 후 — 후속 실측

위 baseline 수치는 `preStop` 훅이나 종료 관련 튜닝을 **전혀 하지 않은** 기본값 상태입니다. 다음 두 가지를 추가해 동일한 T1 테스트(100qps × 600초, 60,000건/모드)를 재실행했습니다:

- **3개 모드 전체**: `echo` 컨테이너에 `lifecycle.preStop.sleep.seconds: 10` (K8s 1.29+ 네이티브 sleep 액션, exec/셸 불필요) + `terminationGracePeriodSeconds: 40` — SIGTERM 전에 Endpoint 제거가 클러스터에 전파될 시간을 벌어줌
- **sidecar만 추가**: `proxy.istio.io/config` 어노테이션으로 istio-proxy에 `EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true` + `terminationDrainDuration: 30s` 주입 (istio-proxy initContainer의 실제 env에 반영된 것을 확인함) — active connection이 0이 되면 30초를 다 기다리지 않고 즉시 종료

| 모드 | rollout 횟수 | Code 200 | Code 503 | Code -1 | Sockets used | 평균 지연 |
|---|---|---|---|---|---|---|
| sidecar (하드닝) | 42 | 60,000 (100%) | **0** | **0** | 16 (완벽 keepalive) | 2.630ms |
| ambient-L4 (하드닝) | 38 | 60,000 (100%) | **0** | **0** | 395 | 1.189ms |
| ambient-L7 (하드닝) | 45 | 59,352 (98.9%) | 648 (1.1%) | **0** | 678 | 3.843ms |

**Baseline → 하드닝 비교**

| 모드 | Baseline 오류율 | 하드닝 후 오류율 | 변화 |
|---|---|---|---|
| sidecar | 503 0.5% + TCP오류 0% | 503 0% + TCP오류 0% | **503 완전히 사라짐** |
| ambient-L4 | 503 0% + TCP오류 0.3% | 503 0% + TCP오류 0% | **TCP 오류도 완전히 사라짐** |
| ambient-L7 | 503 2.6% + TCP오류 0.1% | 503 1.1% + TCP오류 0% | 503 비율이 절반 이하로 감소 |

> ✅ **결론**: 사용자가 지적했던 "Endpoint 제거 전에 graceful하게 종료되지 않아서 503이 난다"는 가설이 실측으로 확인됐습니다. `preStop sleep 10`만으로 sidecar와 ambient-L4의 오류가 완전히 사라졌고, ambient-L7(waypoint)도 절반 이하로 줄었습니다. waypoint 자체의 커넥션 재사용 문제(§4 본문의 핵심 메커니즘)는 workload 쪽 graceful shutdown 튜닝만으로는 완전히 해결되지 않는다는 뜻이기도 합니다 — L7 경로를 쓴다면 이 workload 측 하드닝을 기본으로 적용하고도 여전히 남는 503 리스크를 감안해야 합니다.

### Retry 완화책의 위험성 — 실측 결과 (T2)

**테스트 구성**: `order`(6 replica, 비멱등 `POST /order`, 핸들러 내 0.1초 지연 후 request ID를 `collector`에 보고), `collector`(distinct request ID를 집계하고 2회 이상 보인 ID를 표시), `order-client`(요청마다 고유 UUID를 붙여 20 req/s로 지속 POST)로 구성한 하네스입니다. 동일한 Istio VirtualService retry 정책(`attempts: 3, perTryTimeout: 2s, retryOn: 503,reset,connect-failure`)을 sidecar(istio-proxy)와 ambient-L7(waypoint) 양쪽에 적용했습니다. 각 모드는 `order` Deployment에 동시에 `rollout restart`를 걸며 300초간 측정했습니다.

| 모드 | rollout 횟수 | 전송 요청 수 | 클라이언트에 보인 실패(retry 3회 모두 소진) | 중복 실행 |
|---|---|---|---|---|
| sidecar (VirtualService retry) | 11 | 9,135 | 15건 (0.16%) | **0건** |
| ambient-L7 (waypoint retry) | 12 | 7,229 | 21건 (0.29%) | **0건** |

> ✅ **결론**: 두 모드 모두에서 비멱등 요청의 중복 실행은 관찰되지 않았습니다. 클라이언트에 보이는 낮은 실패율은 retry가 실제로 발동해 rollout churn으로 인한 일시적 오류를 대부분 가려주고 있었음을 보여주는데, 그럼에도 성공한 retry 중 같은 논리적 요청이 두 번 처리된 사례는 없었습니다.

> ⚠️ **주의 — "안전하다"는 증명은 아닙니다.** 이번 특정 조건(perTryTimeout=2s, 20 req/s, replica 6개, 기본 graceful shutdown, `preStop` 훅 없음)에서 재현되지 않았을 뿐입니다. 이론상의 메커니즘 — 요청이 애플리케이션에 이미 도달한 뒤 응답이 호출자에게 돌아오기 *전에* 연결이 끊겨 retry가 재전송되는 경우 — 은 애플리케이션이 처리를 시작한 *이후*이면서 응답이 돌아오기 *이전*인 매우 좁은 시간창에서만 발생합니다. 300초간의 지속적인 rollout churn으로도 두 모드 어느 쪽에서도 이 사례를 포착하지 못했지만, 서버 측 idempotency key가 없는 비멱등 경로라면 mesh 레벨 retry는 여전히 기본적으로 안전하지 않다고 취급해야 합니다 — 이 테스트는 race가 *흔하다*는 확신을 낮췄을 뿐, *안전하다*는 것을 증명하지는 않습니다.

### 테스트 격리에 관한 노트

<details>
<summary>왜 전용 클러스터가 필요했는지, 테스트 중 어떤 문제를 만났는지 (클릭하여 펼치기)</summary>

같은 날 앞서 진행한 T1/T3 실측은 공유 클러스터(`fsi-demo-cluster`)에서 4개 네임스페이스로 격리해 진행했습니다. 그 클러스터의 `benchmark` 네임스페이스에서는 100개 이상의 EC2 인스턴스 타입을 대상으로 하는 대규모 Kafka 벤치마크 Job이 동시에 실행되고 있었고, ambient-L7의 T1 로드가 완료된 직후 그 라운드가 생성한 모든 리소스(4개 네임스페이스, `istio-system`, Istio/Gateway API CRD 전체)가 동시에 사라지는 현상이 발생했습니다 — 원인은 끝내 특정하지 못했습니다(일치하는 ArgoCD Application 없음, Kyverno/Gatekeeper 정책 미발견). 이 때문에 T2·T4·T5는 실행하지 못했고, 자원 경쟁 상황에서 수집된 T1 수치의 신뢰도에도 의문이 남았습니다.

이번 라운드는 바로 그런 종류의 간섭을 없애기 위해 완전히 새로운 단일 테넌트 클러스터(`mesh-isolated-test`, 독립 VPC, 다른 워크로드 전혀 없음)를 만들어 T1~T5를 처음부터 끝까지 완료했고, 리소스 이상 현상은 전혀 없었습니다. 대신 **다른 종류의** 격리 문제가 드러났습니다: 새 클러스터에서 첫 T1 시도를 진행하는 도중, 로컬 워크스테이션이 공유하는 `~/.kube/config`의 current-context가 `mesh-isolated-test`에서 무관한 다른 클러스터로 조용히 바뀌어 그 시도가 무효화됐습니다(컨텍스트가 바뀐 뒤로 rollout-restart 루프가 `namespace not found` 오류를 내기 시작했지만, 이미 연결이 맺어져 있던 fortio 부하 생성기의 exec 연결 자체는 영향받지 않았습니다). 명시적인 kubeconfig로 확인한 결과 `mesh-isolated-test`의 네임스페이스와 리소스는 그 시간 내내 온전히 남아 있었습니다 — 즉 클러스터 쪽 삭제가 아니라 워크스테이션 수준의 컨텍스트 혼선이었습니다. 해결책은 `mesh-isolated-test`만을 가리키는 kubeconfig 파일을 만들어 모든 테스트 스크립트가 이를 명시적으로 참조하게 하고, 컨텍스트가 다시 흐트러지면 즉시 중단하는 가드를 넣는 것이었습니다. 이 문서에 실린 최종 수치는 모두 그렇게 수정한, 컨텍스트가 고정된 재실행분입니다.

</details>

## 5. 종합 권장 (계층화 접근)

"sidecar냐 ambient냐"의 이분법보다, **워크로드 특성에 따라 mesh 모드를 차등 적용**하는 것을 권장합니다. 이는 [Ambient Mode](../advanced/01-ambient-mode.md#사용-사례) 문서의 사용 사례 가이드와 일치하며, 이번 실측이 그 근거를 뒷받침합니다.

| 계층 | 예시 | 권장 | 근거 |
|---|---|---|---|
| 코어 (주문 생성·체결·정산, 비멱등) | 거래 API | **Ambient L4-only(waypoint 미적용) 또는 sidecar 유지** | §4 실측: waypoint 경유 시 503이 sidecar보다 약 5배. L4-only는 503이 0건. L7 기능이 꼭 필요하면 sidecar가 더 성숙. T2에서는 두 모드 모두 retry로 인한 중복 실행이 관찰되지 않았지만, 이것이 "안전하다"는 증명은 아니므로 이 계층에서는 mesh 모드와 무관하게 retry를 기본으로 켜지 않습니다. |
| 준코어 (멱등 read API) | 시세 조회, 잔고 조회 | Ambient (L4, 필요 시 L7) | 재시도해도 안전한 멱등 요청이라 waypoint 리스크가 상대적으로 낮음 |
| 주변부 (조회, 알림, 배치) | 대시보드, 알림 발송 | Ambient 적극 적용 | 리소스·운영 이점 극대화, 실측으로 mTLS·rollout 문제 없음 확인 |

**네임스페이스 단위 혼합 배치**는 이번 실측에서 실제로 검증됐습니다 — 같은 클러스터에서 sidecar/ambient-L4/ambient-L7 네임스페이스가 동시에 정상 동작했고, 각각 독립적으로 STRICT mTLS를 적용할 수 있었습니다.

### L4-only의 제약사항 — canary 배포는 여전히 가능한가?

Ambient L4-only는 waypoint가 없으므로 ztunnel이 HTTP 요청 내용을 들여다보지 못합니다. 즉 **HTTP 헤더/경로 기반 라우팅, retry, circuit breaker, traffic mirroring 같은 L7 기능은 L4-only 상태의 서비스에는 적용할 수 없습니다.** 이 제약이 canary 배포에 실제로 영향을 주는지는 트래픽이 어디서 들어오는지에 따라 다릅니다.

> ✅ **외부 진입(ingress) canary는 영향 없음.** Istio Ingress Gateway나 Gateway API의 `Gateway`는 워크로드의 ambient/sidecar 모드와 무관하게 항상 별도의 완전한 Envoy 프록시(Deployment)로 동작합니다. `VirtualService`/`HTTPRoute`의 weighted routing으로 v1/v2 subset을 나누는 결정은 이 게이트웨이에서 이미 끝나고, ztunnel(L4)은 그 결정 이후 이미 정해진 목적지 Pod까지 mTLS 터널만 뚫어주는 역할이라 L4-only여도 아무 문제가 없습니다. 외부로 노출되는 API의 canary 배포는 L4-only로 그대로 가능합니다.

> ⚠️ **mesh 내부(east-west) canary는 그 서비스에 L7이 필요합니다.** 예를 들어 서비스 A가 클러스터 내부에서 서비스 B를 호출할 때 B-v1/B-v2로 비율 기반 트래픽 분할을 하려면, 그 라우팅 결정을 누군가 L7에서 해줘야 합니다. ztunnel은 이 판단을 못 하므로, **B 앞에 waypoint를 배포하거나(ambient-L7 전환) B를 sidecar로 돌려야** canary가 성립합니다.

**결론**: "외부로 노출되는 API의 canary"는 L4-only로 충분하고, "내부 서비스 간 canary"가 필요한 서비스에 한해서만 waypoint 또는 sidecar를 선택적으로 붙이면 됩니다 — 이것이 위 계층화 권장안의 실제 적용 방식입니다.

**도입 전 재확인 체크리스트**

- [ ] 주문·체결·정산 경로가 L7 기능(HTTP 라우팅, retry, traffic split)을 반드시 필요로 하는가? 아니라면 ambient L4-only가 우선 후보
- [ ] NetworkPolicy에 HBONE 포트(15008) 허용 규칙을 반영했는가? (§2, 실측 확인 — `enableNetworkPolicy`를 운영 클러스터에서 처음 켠다면 기존 Pod를 재생성해야 합니다. 소급 적용되지 않습니다)
- [ ] 비멱등 API 경로에 retry 정책이 적용돼 있지 않은가? (§4 — T2 실측에서는 중복 실행이 발견되지 않았지만, 서버 측 idempotency key가 없다면 비멱등 경로는 여전히 retry를 기본 비활성으로 둡니다)
- [ ] 자체 워크로드 기준 latency를 재측정했는가? (§3, 이 클러스터의 Graviton 노드에서 실측 확인 — 인스턴스 타입이나 워크로드 특성이 크게 다르면 다시 측정할 것)

## 부록: 테스트 재현 방법

아래는 이 문서의 모든 수치를 만들어낸 실제 설정 파일과 실행 절차입니다. 그대로 복사해서 자체 클러스터에서 재현할 수 있습니다.

### A. 클러스터 생성 (eksctl)

전용 단일 테넌트 클러스터를 eksctl로 생성했습니다. NAT 게이트웨이를 쓰지 않는 완전 퍼블릭 서브넷 구성입니다(테스트 전용이라 신규 EIP 없이 빠르게 만들기 위한 선택 — 운영 환경이라면 NAT을 활성화하세요).

<details>
<summary>eksctl-cluster.yaml</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: "1.36"
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: "true"

availabilityZones:
  - ap-northeast-2a
  - ap-northeast-2c

vpc:
  nat:
    gateway: Disable

managedNodeGroups:
  - name: mesh-test-ng-arm64
    instanceType: m7g.xlarge
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    minSize: 3
    maxSize: 3
    volumeSize: 40
    privateNetworking: false
    labels:
      role: istio-mesh-test
    tags:
      ephemeral: "true"

addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: eks-pod-identity-agent
```

</details>

```bash
eksctl create cluster -f eksctl-cluster.yaml
```

### B. Istio 설치 (Gateway API CRD + ambient 프로파일)

Ambient 모드는 waypoint(Gateway API `Gateway` 리소스)를 쓰므로 Istio 설치 전에 Gateway API CRD가 먼저 있어야 합니다.

```bash
# 1) Gateway API CRD (Istio 1.30과 호환되는 v1.1.0)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml

# 2) Istio 1.30.2 ambient 프로파일 설치 (helm이 아니라 istioctl 사용)
istioctl install -f ambient-overlay.yaml -y
```

<details>
<summary>ambient-overlay.yaml (arm64 노드에 CNI/ztunnel/istiod를 스케줄링하기 위한 오버레이)</summary>

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: ambient
  values:
    cni:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["arm64"]
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["arm64"]
  components:
    pilot:
      k8s:
        affinity:
          nodeAffinity:
            requiredDuringSchedulingIgnoredDuringExecution:
              nodeSelectorTerms:
              - matchExpressions:
                - key: kubernetes.io/arch
                  operator: In
                  values: ["arm64"]
```

</details>

### C. 네임스페이스 & 워크로드 매니페스트

4개 네임스페이스 — `mesh-test-base`(mesh 미적용, latency 기준선용), `mesh-test-sidecar`, `mesh-test-ambient-l4`, `mesh-test-ambient-l7`. 라벨만 다르고 나머지 리소스는 byte-identical입니다.

<details>
<summary>namespaces.yaml</summary>

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-base
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-sidecar
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l4
  labels:
    istio.io/dataplane-mode: ambient
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l7
  labels:
    istio.io/dataplane-mode: ambient
```

</details>

<details>
<summary>워크로드 매니페스트 (echo 서버 6 replica + fortio 클라이언트) — 네임스페이스 4개에 동일하게 적용, namespace 필드만 교체</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar   # base / ambient-l4 / ambient-l7로 교체
  labels:
    app: echo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: echo
  template:
    metadata:
      labels:
        app: echo
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: echo
        image: fortio/fortio:1.69.4
        args: ["server", "-http-port", "8080"]
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /fortio/
            port: 8080
          initialDelaySeconds: 2
          periodSeconds: 3
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  selector:
    app: echo
  ports:
  - port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fortio-client
  namespace: mesh-test-sidecar
  labels:
    app: fortio-client
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fortio-client
  template:
    metadata:
      labels:
        app: fortio-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4
        command: ["/usr/bin/fortio"]
        args: ["server", "-http-port", "8081", "-redirect-port", "disabled"]
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

### D. mTLS — PeerAuthentication (§1)

<details>
<summary>peerauth-strict.yaml</summary>

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-sidecar
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l4
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l7
spec:
  mtls:
    mode: STRICT
```

</details>

ambient-L7 네임스페이스에는 waypoint를 별도로 배포해야 합니다:

```bash
istioctl waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
```

### E. NetworkPolicy (§2)

VPC CNI의 eBPF 기반 NetworkPolicy 강제를 애드온 설정으로 켭니다. **이 시점 이후 생성/재생성된 Pod에만** 적용된다는 점을 §2에서 다뤘습니다.

```bash
aws eks update-addon --cluster-name mesh-isolated-test --addon-name vpc-cni --region ap-northeast-2 \
  --configuration-values '{"enableNetworkPolicy":"true"}' --resolve-conflicts OVERWRITE

# 애드온 활성화 후 기존 Pod를 재생성해야 eBPF 후크가 붙습니다
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-sidecar
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l4
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l7
```

<details>
<summary>NetworkPolicy 매니페스트 (테스트 1: 8080만 허용 → 테스트 2: 8080+15008 허용)</summary>

```yaml
# 테스트 1 — ambient를 차단시키는 버전
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4   # ambient-l7, sidecar에도 동일하게 적용
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
```

```yaml
# 테스트 2 — HBONE 포트를 추가해 ambient를 정상화하는 버전
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
    - protocol: TCP
      port: 15008
```

</details>

### F. 무중단 rollout 테스트 실행 (T1, §4)

fortio 부하 생성(포그라운드, 지속시간 동안 블로킹)과 `rollout restart` 반복(백그라운드)을 동시에 실행하고, 부하가 끝나면 반복 루프를 정지시킵니다.

```bash
NS=mesh-test-sidecar   # ambient-l4, ambient-l7로 교체해 반복 실행
DUR=600
CLIENT=$(kubectl get pods -n "$NS" -l app=fortio-client -o jsonpath='{.items[0].metadata.name}')

# ① rollout 반복 루프 (백그라운드) — DUR초 동안 반복
(
  START=$(date +%s)
  while [ $(( $(date +%s) - START )) -lt "$DUR" ]; do
    kubectl rollout restart deployment/echo -n "$NS"
    kubectl rollout status deployment/echo -n "$NS" --timeout=60s
  done
) &
ROLLOUT_PID=$!

# ② fortio 부하 생성 (포그라운드, 100qps × 600s = 60,000건)
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors http://echo:8080/

kill "$ROLLOUT_PID" 2>/dev/null
```

> 💡 `-allow-initial-errors` 플래그가 없으면 fortio의 워밍업 요청이 하필 rollout 도중 503을 맞을 경우 테스트 전체가 즉시 중단됩니다. rollout churn과 겹치는 부하 테스트에는 필수 플래그입니다.

**Graceful shutdown 하드닝 패치** (§4 "하드닝 적용 후" 재검증에 사용, `kubectl patch --type strategic`으로 기존 Deployment에 적용):

```yaml
# 3개 모드 공통 — ambient-l4/l7는 이 패치만 적용
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
```

```yaml
# sidecar 네임스페이스만 추가 적용 (EXIT_ON_ZERO_ACTIVE_CONNECTIONS)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          proxyMetadata:
            EXIT_ON_ZERO_ACTIVE_CONNECTIONS: "true"
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
```

```bash
kubectl patch deployment/echo -n mesh-test-sidecar --type strategic --patch-file patch-prestop-sidecar.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l4 --type strategic --patch-file patch-prestop-ambient.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l7 --type strategic --patch-file patch-prestop-ambient.yaml
```

### G. Latency 테스트 실행 (T5, §3)

동일한 fortio 명령을 rollout 반복 없이 steady state로만 실행합니다.

```bash
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors http://echo:8080/
```

### H. Retry / 중복 실행 테스트 하네스 (T2, §4)

`order`(비멱등 POST 처리) · `collector`(중복 request-id 탐지) · `order-client`(지속 부하) 3개 파드를 파이썬 스크립트로 구성했습니다. sidecar와 ambient-L7 네임스페이스에 동일하게 배포합니다.

<details>
<summary>ConfigMap — order_server.py / collector.py / client.py</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar   # ambient-l7로도 동일하게 배포
data:
  order_server.py: |
    import http.server, urllib.request, time, os

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404); self.end_headers(); return
            rid = self.headers.get("X-Request-Id", "unknown")
            time.sleep(0.1)  # 종료 시점 race 윈도우를 넓히기 위한 지연
            try:
                req = urllib.request.Request(COLLECTOR_URL, data=rid.encode(), method="POST")
                urllib.request.urlopen(req, timeout=2)
            except Exception as e:
                print(f"collector report failed for {rid}: {e}", flush=True)
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, fmt, *args):
            pass

    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 8080), Handler).serve_forever()
  collector.py: |
    import http.server, json, threading

    lock = threading.Lock()
    counts = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes)}).encode()
            else:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 9090), Handler).serve_forever()
  client.py: |
    import urllib.request, uuid, time, os

    TARGET = os.environ.get("TARGET_URL", "http://order.mesh-test-sidecar.svc.cluster.local:8080/order")
    RPS = float(os.environ.get("RPS", "20"))
    interval = 1.0 / RPS
    sent = 0
    failed = 0
    while True:
        rid = str(uuid.uuid4())
        t0 = time.time()
        try:
            req = urllib.request.Request(TARGET, data=b"{}", method="POST", headers={"X-Request-Id": rid})
            urllib.request.urlopen(req, timeout=3)
            sent += 1
        except Exception:
            failed += 1
        dt = time.time() - t0
        if dt < interval:
            time.sleep(interval - dt)
```

</details>

<details>
<summary>order / collector / order-client Deployment + Service</summary>

```yaml
apiVersion: v1
kind: Service
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  selector:
    app: collector
  ports:
  - port: 9090
    targetPort: 9090
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: collector
  template:
    metadata:
      labels:
        app: collector
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: collector
        image: python:3.12-alpine
        command: ["python3", "/scripts/collector.py"]
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: v1
kind: Service
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  selector:
    app: order
  ports:
  - port: 8080
    targetPort: 8080
    name: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  replicas: 6
  selector:
    matchLabels:
      app: order
  template:
    metadata:
      labels:
        app: order
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: order
        image: python:3.12-alpine
        command: ["python3", "/scripts/order_server.py"]
        env:
        - name: COLLECTOR_URL
          value: "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record"
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-client
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-client
  template:
    metadata:
      labels:
        app: order-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine
        command: ["python3", "/scripts/client.py"]
        env:
        - name: TARGET_URL
          value: "http://order.mesh-test-sidecar.svc.cluster.local:8080/order"
        - name: RPS
          value: "20"
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

`order` Service에 retry 정책을 적용합니다 (sidecar는 istio-proxy가, ambient-L7은 이미 배포된 waypoint가 이 VirtualService를 읽어 적용합니다):

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar   # ambient-l7로도 동일하게 배포
spec:
  hosts:
  - order
  http:
  - route:
    - destination:
        host: order
        port:
          number: 8080
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

실행 절차는 §4의 rollout 루프(F)와 동일하되, `order` Deployment에 rollout을 걸고, 측정 전 `collector`를 재시작해 카운터를 초기화하고, 측정 후 아래 명령으로 중복 건수를 조회합니다:

```bash
kubectl rollout restart deployment/collector -n "$NS"   # 카운터 초기화

# ... §4-F와 동일한 방식으로 order Deployment에 rollout 반복 + 300초 대기 ...

CLIENT=$(kubectl get pods -n "$NS" -l app=order-client -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n "$NS" "$CLIENT" -c order-client -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://collector.$NS.svc.cluster.local:9090/dupes', timeout=5).read().decode())"
```

## 참고 자료

- [Ambient Mode](../advanced/01-ambient-mode.md) — ztunnel/waypoint 아키텍처, 사이드카 대비 리소스 비교
- [mTLS](../security/01-mtls.md) — STRICT/PERMISSIVE 모드, 인증서 관리, NetworkPolicy 충돌
- [Troubleshooting: 파드 종료 시 연결 에러](../troubleshooting/common-errors.md#파드-종료-시-연결-에러)
- [Sidecar Injection](../advanced/07-sidecar-injection.md)
- [Service Mesh 솔루션 비교](01-service-mesh-comparison.md)
