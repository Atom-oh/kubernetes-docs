# Sidecar vs Ambient 모드 선택 가이드 (EKS 1.36 실험 보고)

> **보고된 실험 버전**: Istio 1.30.2 / EKS 1.36.2 / Fortio 1.69.4
> **원문 보고일**: 2026년 8월 21일 · **내용 검토일**: 2026년 9월 11일

이 문서는 보고된 mTLS, NetworkPolicy, 지연 시간, 롤아웃 측정값을 보존합니다. 전체 원시 결과와 정확한 실행 스크립트 아카이브는 첨부되지 않았으며, 이번 검토에서 AWS 클러스터를 재구성하지 않았습니다. 설정과 산술 검증은 측정 결과의 독립적인 재현이 아닙니다.

부록은 명확한 코드·설정 결함을 고친 **후속 실험 예시**입니다. 기존 수치를 생성한 정확한 절차로 설명하면 안 됩니다. 새 측정에는 실제 소프트웨어, 이미지 digest, 정책과 산출물을 보관하고, 기존 결과의 버전을 Istio 1.31 등으로 바꾸지 않습니다.

## 선택 요약

| 요구사항 | Sidecar | Ambient (L4, waypoint 미사용) | Ambient (L7, waypoint 사용) | Cilium |
|---|---|---|---|---|
| mTLS | 보고된 STRICT 검사 통과 | 보고된 STRICT 검사 통과 | 보고된 STRICT 검사 통과 | 미측정. identity 상호 인증과 별도 WireGuard/IPsec 암호화는 하나의 STRICT 동등 스위치가 아님 |
| NetworkPolicy | 검사한 애플리케이션 포트 규칙 작동 | 검사 경로에 TCP 15008도 필요 | 검사 경로에 TCP 15008도 필요 | 미측정. Cilium은 표준 Kubernetes NetworkPolicy와 CiliumNetworkPolicy/클러스터 범위 확장을 지원 |
| 보고된 기준선 대비 P50 | +1.29ms | +0.04ms | +1.86ms | 미측정 |
| 조정 전 롤아웃 | 60,000건 중 HTTP 503 324건 + 비HTTP 오류 2건 | 60,000건 중 HTTP 503 0건 + 비HTTP 오류 195건 | 59,913건 중 HTTP 503 1,528건 + 비HTTP 오류 84건 | 미측정 |
| 종료 조정 후 롤아웃 | 60,000건 중 관측 오류 0건 | 60,000건 중 관측 오류 0건 | 60,000건 중 HTTP 503 648건 | 미측정 |

이 보고에서 ambient L4의 P50 차이는 작았고, 조정 전 sidecar보다 비성공 응답이 적었습니다. 종료 조정 후 표본에서는 sidecar와 ambient L4 모두 오류가 없었습니다. HTTP 503이 0건이라는 것만으로 무중단을 뜻하지 않으며, waypoint의 관측 오류율이 제품 고유의 실패율이나 IP 재사용이라는 원인을 입증하지도 않습니다.

먼저 필요한 기능을 정한 다음 전체 오류, 지연, identity, 운영 조건을 워크로드 예산과 비교합니다. Cilium 열은 문서화된 기능만 설명하며, 이번 실험에서는 Cilium을 배포하지 않았습니다.

## 1. mTLS — 실험 결과 (EKS 1.36.2, Istio 1.30.2)

원문은 전용 `mesh-isolated-test` 클러스터와 VPC, Amazon Linux 2023 arm64 m7g.xlarge 노드, 세 메시 네임스페이스의 STRICT PeerAuthentication을 기술합니다. 컨트롤 플레인과 워커 Kubernetes 버전은 1.36.2로 보고되었습니다.

기록된 plaintext Pod IP 요청은 실패했습니다:

```text
plaintext-client -> sidecar echo pod:8080  => connection reset
plaintext-client -> ambient-L4 echo:8080  => EOF
plaintext-client -> ambient-L7 echo:8080  => EOF
```

메시 내부 Service 요청은 세 모드 모두 HTTP 200으로 기록되었습니다. Envoy 관련 응답 헤더가 달랐지만, 헤더의 유무는 암호화나 전체 프록시 경로를 증명하지 않습니다.

인증서 명령으로 확인한 것은 인증서를 보유·요청하는 프록시입니다. 프록시 자체가 발급자는 아닙니다:

| 워크로드 | 검사한 프록시 | SPIFFE ID | Root CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | 동일 |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | 동일 |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | 동일 |


표의 ID는 **네임스페이스/ServiceAccount identity**입니다. 같은 default ServiceAccount를 사용하는 echo와 client Pod는 identity를 공유하므로 Pod마다 고유한 SPIFFE ID가 아닙니다. Istiod 또는 구성한 CA가 워크로드 인증서를 제공합니다.

보고된 실패·성공 대조군은 검사한 경로의 STRICT 적용과 일치합니다. 모든 경로, 프로토콜, 출발지와 우회 가능성을 검증한 것은 아닙니다. Ambient는 Istio CNI의 네트워크 네임스페이스 트래픽 캡처와 TCP 15008 HBONE을 사용하고, sidecar 모드는 워크로드 프록시를 사용합니다. 적용 경계는 [mTLS 가이드](../security/01-mtls.md)를 참고하세요.

## 2. NetworkPolicy — 실험 결과

보고서는 VPC CNI NetworkPolicy 적용과 `v1.3.5-eksbuild.3` 에이전트를 기술합니다. 전체 애드온 설정·버전, policy endpoint와 노드 상태 근거는 보관되어 있지 않습니다. 과거 결과에 기록된 버전을 유지합니다.

**작성자가 정책 적용을 확인했다고 보고한 뒤 수행한 ingress 포트 실험:**

| 모드 | 결과 |
|---|---|
| sidecar | ✅ 200 OK — 영향 없음 |
| ambient-L4 | ❌ 차단 (`i/o timeout`) |
| ambient-L7 | ❌ 차단 (`i/o timeout`) |


**8080과 HBONE 15008을 허용한 뒤 보고된 결과:**

| 모드 | 결과 |
|---|---|
| ambient-L4 | ✅ 200 OK — 정상화 |
| ambient-L7 | ✅ 200 OK — 정상화 |


이는 검사한 경로에서 HBONE 포트가 중요함을 보여 줍니다. 모든 기존 규칙이 sidecar에서 그대로 작동하거나 15008 허용만으로 최소 권한 ambient 정책이 완성된다는 뜻은 아닙니다. 출발지 선택자, waypoint 경로, DNS/컨트롤 플레인 egress와 CNI 구현에 따라 달라집니다. 네트워크 정책에는 터널 포트가 보이므로 내부 트래픽의 identity·포트 정책도 설계해야 합니다.

원문은 정책 기능 활성화 후 Pod를 재생성하자 음성 대조군이 차단되었다고 기록합니다. 해당 구성의 관측이며, 모든 현재 에이전트가 CNI ADD 때만 정책을 붙이거나 기존 Pod에 정책을 소급 적용할 수 없다는 증거는 아닙니다. 측정 전 reconciliation과 실제 적용을 확인하세요. 현재 AWS 문서는 정책 구성 전 트래픽을 허용하는 standard 시작 모드와, 필요한 의존성 허용 규칙을 준비해야 하는 strict 시작 모드를 구분합니다.

현재 AWS 문서는 Deployment, StatefulSet, DaemonSet, Job 등 컨트롤러가 소유한 Pod를 지원하며, 독립 Pod에는 추가 제약이 있습니다. Cilium도 표준 NetworkPolicy와 자체 정책 CRD를 지원합니다. 다른 구현의 동작을 이 실험 결과만으로 추론하면 안 됩니다.

## 3. Latency — 실험 결과 (T5)

보고서는 같은 Graviton 클러스터에서 Fortio 요청 설정 200 QPS, 60초, 연결 16개로 정상 상태를 측정했고, 케이스마다 성공 요청 12,000건을 기록했다고 설명합니다:

| 케이스 | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh (기준선) | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4 (waypoint 미사용) | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7 (waypoint) | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |


기준선 대비 P50 차이 1.29ms, 0.04ms, 1.86ms의 뺄셈은 맞습니다. 작은 차이를 무시할 수 있다거나 거래/SLO 예산에 적합하다고 판단하려면 반복 실험 편차, 리소스·배치 조건과 실제 결과 JSON이 필요합니다.

부록의 Fortio 명령은 시간 기반입니다. 요청 QPS × 실행 시간은 명목 부하이며 정확한 호출 수를 보장하지 않습니다. 각 실행의 DurationHistogram.Count와 RetCodes를 사용하세요. 재실행과 증거 보관 없이 과거 버전 표시를 갱신하지 않습니다.


## 4. 무중단 롤아웃 — 503 실험 결과 (핵심 관측)

### 배경

Pod 종료, endpoint 전파, 애플리케이션·프록시 drain, 연결 풀과 timeout 모두 롤아웃 실패에 영향을 줄 수 있습니다. 원문의 목적지 IP 재사용 경쟁과 ztunnel 알림 누락 설명은 **가설**입니다. 표시된 집계만으로 원인이 확정되지 않습니다. 응답 플래그, 실제 upstream host, endpoint/Pod UID 시간선과 연결 근거를 확인해야 합니다.

보고서는 메시 네임스페이스마다 echo 6개 replica와 Fortio client를 두고, 요청 설정 100 QPS로 600초 동안 대상 Deployment를 반복 재시작했다고 설명합니다. 애플리케이션 매니페스트는 동일하게 의도했지만 주입·공유 프록시 리소스와 실제 롤아웃 노출은 모드마다 달랐습니다.

### 결과

| 모드 | rollout 횟수 | 요청 수 | 503 건수 | 503 비율 | 비HTTP 결과(-1) | Sockets used |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2건 (0.0%) | 350 |
| ambient-L4 (waypoint 없음) | 64 | 60,000 | **0** | **0%** | 195건 (0.3%) | 1,652 |
| ambient-L7 (waypoint) | 65 | 59,913 | 1,528 | **2.6%** | 84건 (0.1%) | 2,486 |


원문에는 전체 기계 판독 산출물이 아닌 다음 요약도 있었습니다:

<details>
<summary>기록된 호출 수 요약 (해석 주석 수정)</summary>

```text
[sidecar]      rollout 42회, Sockets used: 350 (설정한 client 동시성: 16)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   rollout 64회, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   ← HTTP 응답을 얻지 못한 결과, 503 아님

[ambient-L7]   rollout 65회, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (집계 59,913건; 명목 부하 60,000건; 평균 지연 50.4ms — 다른 두 모드는 약 2~3ms)

```

</details>

해석할 때 다음 한계를 적용합니다:

1. 집계된 호출 수 기준 HTTP 503 비율은 324/60,000 = 0.54%, 1,528/59,913 ≈ 2.55%이며 비율의 비는 약 4.72입니다. 원문의 반올림 0.5%/2.6%와 “약 5배”는 이 표본의 설명이며 제품 고유 배수가 아닙니다.
2. Ambient L4에는 비HTTP 오류 195건이 있어 HTTP 503 0건이 전체 실패 0건을 뜻하지 않습니다. Fortio -1의 구체적인 reset/EOF/timeout 원인은 실제 오류 기록이 필요합니다.
3. 명목 60,000건과의 차이 87건만으로 이미 시작한 요청 87개가 완료되지 않았다고 결론 내릴 수 없습니다. 시간 기반 실행은 집계 수가 적을 수 있습니다. 보고된 59,913건과 평균 50.4ms는 보존하되 누락 요청의 상태를 만들지 않습니다.
4. Fortio SocketCount는 클라이언트 소켓 수이며 waypoint upstream 연결 풀의 직접 측정값이 아닙니다. 소켓 16개는 연결 재사용 시 설정한 동시성과 일치할 수 있지만 모든 upstream 연결이 정상이라는 증거는 아닙니다.
5. baseline 완료 롤아웃은 42/64/65회로 ambient L7이 가장 많습니다. L4가 아닙니다. 서로 다른 롤아웃 노출과 리소스·시간선 증거 부족으로 인과 비교에는 제약이 있습니다.

### 후속 실험: graceful shutdown 조정 후

원문은 모든 모드에 preStop sleep 10초와 Pod 종료 유예 40초를 적용하고, sidecar에 EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true와 terminationDrainDuration 30s도 적용했다고 기록합니다:

| 모드 | rollout 횟수 | Code 200 | Code 503 | Code -1 | Sockets used | 평균 지연 |
|---|---|---|---|---|---|---|
| sidecar (하드닝) | 42 | 60,000 (100%) | **0** | **0** | 16 | 2.630ms |
| ambient-L4 (하드닝) | 38 | 60,000 (100%) | **0** | **0** | 395 | 1.189ms |
| ambient-L7 (하드닝) | 45 | 59,352 (98.9%) | 648 (1.1%) | **0** | 678 | 3.843ms |


| 모드 | Baseline 오류율 | 하드닝 후 오류율 | 변화 |
|---|---|---|---|
| sidecar | 503 0.5% + TCP오류 0% | 503 0% + TCP오류 0% | **이 표본에서 503 0건 관측** |
| ambient-L4 | 503 0% + TCP오류 0.3% | 503 0% + TCP오류 0% | **이 표본에서 비HTTP 오류 0건 관측** |
| ambient-L7 | 503 2.6% + TCP오류 0.1% | 503 1.1% + TCP오류 0% | 503 비율이 절반 이하로 감소 |


이는 해당 표본의 관측입니다. Sidecar는 **두 요인**이 바뀌었으므로 preStop 하나의 효과라고 할 수 없습니다. 조정 후 롤아웃 횟수 42/38/45도 다릅니다. 종료 조정 후 결과가 개선되었지만 남은 waypoint 오류가 같은 원인이라는 증거나 다른 모드는 언제나 오류가 없다는 보장은 아닙니다.

종료 유예에는 preStop과 컨테이너 종료 시간이 포함됩니다. 10초 sleep은 시간을 제공할 뿐 모든 endpoint 갱신의 완료를 확인하지 않습니다. 릴리스 1.30.2 코드에서 EXIT_ON_ZERO_ACTIVE_CONNECTIONS는 최소 drain 기간 이후 downstream listener 연결 통계를 1초마다 확인합니다. 이 분기는 일반 terminationDrainDuration 타이머를 사용하지 않습니다. Kubernetes 종료 제한과 관측 오류도 영향을 줍니다. 즉시 종료나 무조건 30초 이내 drain으로 설명하면 안 됩니다.

### retry 완화의 위험 — 실험 결과 (T2)

원문은 주문 서비스 replica 6개, collector, client, 20 requests/s 설정, 300초 실행, 3회 retry와 per-try timeout 2초의 VirtualService를 설명합니다. 다음 값은 **보고된 값이며 독립적으로 재현하지 않았습니다**:

| 모드 | rollout 횟수 | 전송 요청 수 | 보고된 클라이언트 실패 | 보고된 중복 기록 |
|---|---|---|---|---|
| sidecar (VirtualService retry) | 11 | 9,135 | 15건 (0.16%) | **0건** |
| ambient-L7 (waypoint retry) | 12 | 7,229 | 21건 (0.29%) | **0건** |


기존 부록으로는 다음 해석을 뒷받침할 수 없습니다:

- 단일 순차 client가 무한 실행하며 통계를 출력하지 않고 성공 때만 sent를 증가시켰습니다. 초당 최대 20회 반복이면 300초의 9,135건 또는 7,229건을 설명할 수 없고, 서버의 0.1초 지연이 실제 처리율을 더 제한합니다.
- client timeout 3초는 원본 요청과 3회 retry 각각의 2초 예산보다 먼저 만료될 수 있습니다. 최종 실패가 retry 전체 소진을 뜻하지 않습니다.
- collector 보고 오류를 숨기면서 주문 서버는 201을 반환했습니다. 실행 중인 client와 카운터 reset이 겹쳤고, 복사한 ambient 매니페스트가 sidecar 네임스페이스 Service를 가리켰습니다.
- X-Request-Id는 프록시·추적 식별자이며 불변 비즈니스 명령 ID와 같다고 볼 수 없습니다. 관측이 불완전한 상태의 중복 보고 0건은 실제 중복 실행 0건을 입증하지 않습니다.
- 낮은 최종 실패율만으로 retry 발생을 확인할 수 없습니다. 적용된 route, retry counter와 실제 전달 기록이 보고서에 포함되지 않았습니다.

수정 부록은 실행 시간을 제한하고 집계를 출력하며, 별도 비즈니스 ID와 관측 오류 처리를 사용합니다. 기존 수치의 출처 부족을 해결하는 것은 아닙니다. 메모리 collector는 영속 트랜잭션 원장이나 멱등성 구현이 아닙니다.

### 원시 실패와 retry가 숨긴 실패를 분리해서 측정

mTLS 데이터 플레인 선택과 HTTP retry 정책은 별개입니다. Sidecar Envoy와 waypoint Envoy는 L7 HTTP retry를 수행할 수 있지만, ztunnel은 [L4 프록시](https://istio.io/latest/docs/ambient/architecture/data-plane/)라 HTTP 503을 해석하거나 HTTP 요청을 재생할 수 없습니다.

공정한 baseline에서는 POST/PUT/PATCH/DELETE 같은 쓰기 route에 attempts: 0을 명시하고 다음을 분리합니다:

- retry 전 HTTP 오류와 비HTTP 실패.
- 실제 해당 proxy/cluster의 Envoy upstream_rq_retry와 upstream_rq_retry_success.
- 원본 요청을 포함한 upstream 전달 수와 observer 기록 수.
- 최종 client 성공·실패와 전체 요청 집계.
- 안정적인 비즈니스 명령 ID의 반복, observer 오류와 재시작.

| 데이터 플레인 | mTLS/암호화 의미 | L7 retry 위치 | 권장 사용 |
|---|---|---|---|
| Istio sidecar | 워크로드별 SPIFFE 인증서 기반 mTLS | 각 Pod의 Envoy | 비멱등 핵심 경로의 보수적인 기준선 |
| Istio ambient L4 | ztunnel 간 HBONE 워크로드 mTLS | 없음 | Istio mTLS와 L4 정책만 필요할 때 첫 후보 |
| Istio ambient L7 | HBONE + waypoint Envoy | 공유 waypoint | HTTP 라우팅·L7 정책이 필요한 서비스에만 추가 |
| Cilium out-of-band + WireGuard/IPsec | identity 상호 인증과 WireGuard/IPsec 같은 전송 암호화를 별도 선택 | L3/L4 암호화 계층에는 없음 | 기존 Cilium 데이터 플레인에서 identity 정책과 네트워크 암호화가 목적일 때 |


Cilium 행은 L3/L4 인증·암호화 계층에 관한 설명이며 선택적인 L7 프록시 기능이 없다는 뜻은 아닙니다. 여기서는 Cilium의 성능과 롤아웃 동작을 측정하지 않았습니다.

Cilium 1.20.1에는 `encryption.type: ztunnel`로 선택하는 별도의 [ztunnel 투명 암호화 베타](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)도 있습니다. Namespace 등록으로 TCP 워크로드 mTLS를 제공하며 양쪽 엔드포인트가 모두 등록되어야 합니다. ClusterMesh와 hostNetwork Pod는 지원하지 않고, 릴리스 문서는 이 경로에서 HBONE 포트 15008을 대상으로 하는 경우 외에는 일반 L4 정책이 동작하지 않는다고 명시합니다. 별도의 CA·bootstrap 요건을 가진 배포 선택지입니다.

Ztunnel 베타는 이 장에 보고한 측정에 포함되지 않았습니다.

> **운영 원칙:** mTLS만 필요하면 ambient L4부터 검증하고, L7 정책이나 east-west HTTP 라우팅이 필요한 서비스에만 waypoint를 추가합니다. 쓰기 retry를 끈 상태의 ambient 전체 오류가 워크로드 오류 예산을 초과하면 핵심 비멱등 경로의 sidecar 기준선을 유지합니다. 애플리케이션 retry와 멱등성도 별도로 관리해야 합니다.

### 테스트 격리에 관한 주의

원문은 공유 클러스터에서 간섭·리소스 소실이 있었고, 전용 클러스터의 초기 시도에서는 작업 PC의 current-context가 바뀌었다고 보고합니다. 포렌식 아카이브가 없으므로 삭제 원인이나 Istio 결함으로 확정하지 않습니다.

유효한 요구사항은 통제된 테스트 클러스터, 전용 kubeconfig/context/server 확인, 전체 리소스 목록과 산출물 보관입니다. 이전 부록에는 본문에서 설명한 context 보호가 없었으므로 수정 절차에 추가했습니다. 네임스페이스 분리만으로 CPU·네트워크·컨트롤 플레인 조건이 독립적이지는 않습니다.

## 5. 권장: 요구사항에 따른 계층별 접근

워크로드 계층은 계획용 분류이며 안전 보장이 아닙니다:

| 워크로드 요구사항 | 후보 | 필요한 검증 |
|---|---|---|
| mTLS와 L4 정책만 필요 | Ambient L4 우선, 필요하면 검증된 sidecar 기준선 유지 | 실제 identity, NetworkPolicy/내부 포트 적용, 전체 실패와 지연 |
| HTTP 라우팅 또는 L7 인가 | 적절한 waypoint, 호출자 sidecar 또는 gateway | 정책 부착, 적용 설정과 워크로드 오류 예산 |
| 핵심 비멱등 명령 | 명시적 쓰기 retry 정책과 서버 정합성 제어를 갖춘 데이터 플레인 | 안정적인 비즈니스 ID, 영속 멱등성/트랜잭션, 응답 소실·복구 실험 |
| 조회 API, 알림, 배치 | 실제 의미와 필요한 기능에 따라 선택 | 알림·배치도 부작용이 있을 수 있고 안전한 조회 retry도 부하를 늘릴 수 있음 |

세 메시 네임스페이스의 공존 보고는 유용하지만 모든 혼합 배포, 워크로드와 정책 조합의 안전성을 입증하지 않습니다.

### L4-only의 한계 — canary 배포는 가능한가?

ztunnel은 HTTP 요청별 헤더·경로 라우팅, 미러링과 HTTP retry를 제공하지 않습니다. **Istio가 관리하는** ingress gateway는 ambient backend에 전달하기 전에 L7 결정을 할 수 있습니다. Gateway API는 API이며 반드시 Envoy Deployment를 뜻하지 않습니다. GatewayClass/controller 구현에 따라 달라집니다.

Istio VirtualService는 DestinationRule subset을 선택할 수 있지만, 표준 HTTPRoute backendRefs는 보통 Service를 선택합니다. 같은 subset API로 설명하면 안 됩니다.

East-west HTTP 요청 분기는 실제 호출자/gateway/waypoint 경로에서 수행되어야 합니다. 목적지 B에만 sidecar를 넣어도 ambient L4 호출자에게 B-v1/B-v2를 선택하는 outbound HTTP 정책이 생기지 않습니다. B의 waypoint, 적절한 호출자 프록시 또는 별도로 설계한 L7 경유 지점을 사용하세요. L4 연결 단위 분배와 replica 기반 롤아웃은 HTTP 요청별 가중치 분기와 다릅니다.

필요 기능, CNI·정책 동작, 쓰기 retry와 자체 측정을 검토하세요. 다음 예시는 새 근거를 수집하기 위한 것이며 과거 보고의 누락된 사실을 소급 입증하지 않습니다.


## 부록: 후속 실험 절차

통제된 후속 실험을 위한 수정 절차이며 기존 결과의 복사·붙여넣기 재현을 보장하지 않습니다. 로컬 검증 범위는 문법, 설정 생성, Python observer/client 동작입니다. 스케줄링, 메시 정책 부착, CNI 적용과 관측 완전성은 실제 실험에서 검증해야 합니다.

### A. 클러스터 프로비저닝 (eksctl)

다음은 원문의 **기록된 입력**입니다. 노드·네트워크 선택을 설명하기 위해 보존하며 이번 감사에서 실행하지 않았습니다:

<details>
<summary>기록된 eksctl-cluster.yaml</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: '1.36'
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: 'true'
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
    ephemeral: 'true'
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
- name: eks-pod-identity-agent
```

</details>

Kubernetes minor 버전, 고정하지 않은 애드온과 현재 AMI 선택으로 과거 컨트롤 플레인 patch, 노드 이미지, 에이전트 버전을 정확히 복원할 수 없습니다. public subnet/no-NAT 실험 구성을 운영 환경의 처방으로 사용하지 마세요. private endpoint, IPv6 또는 NAT egress는 실제 네트워크 요구에 따라 결정합니다.

새 실험은 승인된 전용 클러스터에서 수행하고 ARN/API endpoint, 노드·AMI·커널 버전, CNI·에이전트 설정과 리소스 목록을 기록합니다. 관계없는 클러스터에서 잠재된 정책을 활성화하거나 공유 CRD를 교체하지 않습니다.

### B. Istio 설치 (Gateway API CRD + ambient profile)

예정된 클러스터 기록으로 다음 입력을 설정합니다. helper는 kubeconfig/context를 명시하고 API server 매핑을 매번 검사합니다:

```bash
set -euo pipefail
: "${TEST_KUBECONFIG:?Set the dedicated kubeconfig file}"
: "${TEST_CONTEXT:?Set its explicit test context}"
: "${ISTIOCTL_BIN:?Set the path to the intended Istio 1.30.2 CLI}"
: "${EXPECTED_API_SERVER:?Set the approved API-server URL}"
: "${NS:?Select the test namespace}"
: "${RUN_DIR:?Set a new artifact directory for this run}"
case "$NS" in
  mesh-test-base|mesh-test-sidecar|mesh-test-ambient-l4|mesh-test-ambient-l7) ;;
  *) echo "Unexpected test namespace" >&2; exit 1 ;;
esac
check_mesh_context() {
  local actual
  actual=$(kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
    config view --minify -o jsonpath='{.clusters[0].cluster.server}') || return 1
  if [ "$actual" != "$EXPECTED_API_SERVER" ]; then
    echo "API-server mismatch; stopping" >&2
    return 1
  fi
}
kmesh() {
  check_mesh_context &&
    kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
imesh() {
  check_mesh_context &&
    "$ISTIOCTL_BIN" --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
check_mesh_context
mkdir -p "$RUN_DIR"
```

공유 current-context에 의존하지 않도록 하지만 동시 클러스터·자격 증명 변경을 모두 방지하지는 못합니다. 전용 파일을 통제하고 확인한 클러스터 식별 정보를 보관하세요.

보고된 버전은 Istio 1.30.2입니다. 이전 부록의 Gateway API 1.1.0 호환 주장은 설치 번들 아카이브가 없었습니다. 릴리스 1.30.2의 의존성과 conformance는 1.5.1을 사용합니다. 수정 예시의 Gateway/HTTPRoute에는 다른 설치 controller와의 호환성을 확인한 뒤 해당 standard 번들을 사용하며, 최신 카탈로그 항목만으로 호환성을 판단하지 않습니다.

```bash
# Only for a new dedicated lab needing this compatible bundle.
kmesh apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
imesh manifest generate -f ambient-overlay.yaml > "$RUN_DIR/istio-rendered.yaml"
# Review the render, existing ownership and installed version before installation.
imesh install -f ambient-overlay.yaml
```

Ambient L4만 사용하면 waypoint 리소스가 필수는 아닙니다. 이 실험에는 L7 케이스가 있으므로 waypoint 생성 전에 호환 Gateway API 리소스가 필요합니다. 의도한 Istio CLI/버전과 지원되는 업그레이드 경로를 사용하고 과거 실험을 새 릴리스로 바꿔 표시하지 않습니다.

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
                values:
                - arm64
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values:
                - arm64
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
                  values:
                  - arm64
```

이 overlay의 CNI, ztunnel, Istiod arm64 affinity를 native 1.30.2 오프라인 render에서 확인했습니다. 설정 생성은 배포 검증이 아닙니다.

### C. 네임스페이스와 워크로드 매니페스트

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

다음 애플리케이션 템플릿은 한 케이스용입니다. 모든 metadata.namespace를 선택한 케이스에 맞추고 `-n "$NS"`를 명시해 불일치가 실패하도록 합니다. 애플리케이션 설정은 동등하게 유지하되 다른 주입·공유 프록시 설정도 기록하세요.

<details>
<summary>수정한 echo/Fortio 워크로드 템플릿</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
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
        kubernetes.io/os: linux
      containers:
      - name: echo
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        args:
        - server
        - -http-port
        - '8080'
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
    name: http
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        command:
        - /usr/bin/fortio
        args:
        - server
        - -http-port
        - '8081'
        - -redirect-port
        - disabled
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

새 예시는 보고된 Fortio 버전에 검토 중 확인한 registry digest를 고정하고 HTTP 포트를 명시합니다. 과거 보고서는 digest와 모든 프로토콜 설정을 보관하지 않았으므로 기존 실행도 같은 바이트였다는 증거는 아닙니다. Fortio 이미지는 scratch 기반입니다. 내부 sh/curl/cat을 가정하지 말고 Fortio binary를 사용하세요.

### D. mTLS — PeerAuthentication (§1)

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

L7 네임스페이스:

```bash
imesh waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
kmesh -n mesh-test-ambient-l7 get gateways.gateway.networking.k8s.io -o yaml
```

부하 전 실제 Pod 주입·enrollment, 인증서와 Service 트래픽 경로를 확인합니다. Pod IP 직접 plaintext 차단은 L4 적용 검사이며 모든 호출이 waypoint나 L7 정책을 거친다는 증거는 아닙니다.

### E. NetworkPolicy (§2)

애드온 소유 도구를 통해 **검토한 기존 설정**에 NetworkPolicy opt-in을 병합합니다:

```json
{"enableNetworkPolicy":"true"}
```

실제 CNI·에이전트 버전과 standard/strict 시작 모드를 기록하세요. 한 필드와 OVERWRITE로 다른 설정을 덮어쓰지 않습니다. reconciliation 후 생성된 policy endpoint와 음성 대조군을 확인하세요. 설치된 구성에 필요하면 대상 Pod를 재생성하되 과거 관측을 보편적 소급 적용 불가 규칙으로 설명하지 않습니다.

```bash
kmesh -n "$NS" get policyendpoints.networking.k8s.aws
```

Test1과 Test2는 같은 대상·정책 이름에 순서대로 적용하는 대안입니다:

```yaml
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
```

```yaml
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

선택한 케이스 네임스페이스에 각각 적용합니다. 출발지를 제한하지 않은 포트 규칙은 도달성 실험이며 완전한 테넌트 격리가 아닙니다. 다른 선택된 정책과 허용 범위가 합쳐집니다. 터널 포트 하나가 기존 정책 경계를 모두 보존한다고 가정하지 말고 실제 DNS, 컨트롤 플레인, 출발지와 내부 포트·identity 요구를 검사하세요.

### F. 롤아웃 + 503 실험 (T1, §4)

각 케이스에 ready 워크로드와 새 산출물 디렉터리를 준비합니다. 아래 제한된 루프는 롤아웃 구간과 Fortio 실제 결과를 기록합니다. 부하 시작과 원자적으로 동시에 시작하는 구조는 아니므로, 부하 종료 뒤 끝나는 롤아웃까지 포함해 시간선에서 실제 겹친 노출을 구분하세요.

```bash
# Run after loading the context helpers above. Requires GNU timeout.
DUR=600
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
kmesh -n "$NS" rollout status deployment/fortio-client --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
STOP_FILE="$RUN_DIR/stop-rollouts"
test ! -e "$STOP_FILE"
trap 'touch "$STOP_FILE"' EXIT INT TERM
(
  begin=$(date +%s)
  while [ $(( $(date +%s) - begin )) -lt "$DUR" ] && [ ! -e "$STOP_FILE" ]; do
    cycle_start=$(date +%s)
    kmesh --request-timeout=15s -n "$NS" rollout restart deployment/echo || exit 1
    kmesh --request-timeout=75s -n "$NS" rollout status deployment/echo \
      --timeout=60s || exit 1
    printf '%s,%s\n' "$cycle_start" "$(date +%s)" >> "$RUN_DIR/rollout-times.csv"
  done
) >"$RUN_DIR/rollouts.log" 2>&1 &
ROLLOUT_PID=$!

check_mesh_context
load_status=0
timeout --signal=TERM --kill-after=5s "$((DUR+30))s" \
  kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
  -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio.json" 2>"$RUN_DIR/load.log" || load_status=$?
touch "$STOP_FILE"
rollout_status=0
wait "$ROLLOUT_PID" || rollout_status=$?
trap - EXIT INT TERM
if [ "$load_status" -ne 0 ] || [ "$rollout_status" -ne 0 ]; then
  echo "Invalid run: inspect load/rollout logs" >&2
  exit 1
fi
jq -e '.DurationHistogram.Count > 0 and (.RetCodes | type == "object")' \
  "$RUN_DIR/fortio.json" >/dev/null
```

결과 JSON, 두 stderr 로그, 롤아웃 구간, Pod/endpoint 시간선과 프록시 설정을 보관합니다. Timeout이나 롤아웃 실패는 불완전한 실행이며 부분 출력을 정상 표본으로 취급하지 않습니다. SocketCount는 Fortio의 클라이언트 소켓을 측정합니다.

후속 실험은 아래에서 적절한 조각을 기존 echo Deployment에 병합합니다. 완전한 Deployment가 아닌 **strategic-merge 조각**입니다. 첫 번째는 공통 애플리케이션 변경이고 두 번째는 sidecar 종료 설정도 바꿉니다.

```yaml
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
---
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

새 실행 디렉터리에서 바뀐 요인을 표시하고 반복합니다. kubelet sleep lifecycle hook은 보고된 Kubernetes 버전에서 사용할 수 있으며 이전 버전의 기능 지원은 별도 확인해야 합니다. Pod 종료 유예에 preStop이 포함됩니다. Sleep은 endpoint 수렴 확인이 아니고 proxy exit-on-zero도 drain 30초 상한을 보장하지 않습니다.

### G. 지연 시간 실험 (T5, §3)

롤아웃 루프 없이 안정된 워크로드에서 실행합니다:

```bash
# No rollout loop for this steady-state case.
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
kmesh -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio-latency.json" 2>"$RUN_DIR/latency.log"
jq '{Version, RequestedQPS, ActualQPS, ActualDuration,
     count: .DurationHistogram.Count, RetCodes, SocketCount}' \
  "$RUN_DIR/fortio-latency.json"
```

실제 호출 수, 달성 QPS, 오류 코드, 필요한 모든 percentile과 반복 편차를 보고하세요. 요청 설정 200 QPS × 60초만으로 성공 요청이 정확히 12,000건이었다고 증명할 수 없습니다.


### H. 중복 실행 관측 (T2, §4)

다음 수정 예시는 무한 client와 관측 오류 은폐를 대체합니다. 논리적 명령마다 안정적인 Idempotency-Key를 기록하고 프록시 추적 헤더를 비즈니스 식별자로 사용하지 않습니다. 명령 **중복 제거와 영속 비즈니스 트랜잭션은 구현하지 않습니다**.

ConfigMap을 t2-configmap.yaml로 저장합니다:

<details>
<summary>시간 제한 client, 주문 서버와 메모리 observer</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar
data:
  order_server.py: |
    import http.server
    import os
    import time
    import urllib.error
    import urllib.request

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector:9090/record")


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            command_id = self.headers.get("Idempotency-Key", "").strip()
            if not command_id:
                self.send_response(400)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            time.sleep(0.1)  # Processing delay before the observer record, not a post-commit delay.
            try:
                request = urllib.request.Request(
                    COLLECTOR_URL, data=command_id.encode(), method="POST"
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if isinstance(error, urllib.error.HTTPError):
                    error.close()
                # The record may have committed before an ambiguous transport failure.
                print(f"observer outcome unknown for {command_id}: {error}", flush=True)
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
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
            if self.path != "/record":
                self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                deliveries = sum(counts.values())
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes)}).encode()
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
    import json
    import math
    import os
    import time
    import urllib.error
    import urllib.request
    import uuid


    def run():
        target = os.environ.get("TARGET_URL", "http://order:8080/order")
        rps = float(os.environ.get("RPS", "20"))
        duration = float(os.environ.get("DURATION_SECONDS", "300"))
        timeout = float(os.environ.get("TIMEOUT_SECONDS", "12"))
        if not all(math.isfinite(value) and value > 0 for value in (rps, duration, timeout)):
            raise ValueError("RPS, DURATION_SECONDS and TIMEOUT_SECONDS must be finite and positive")
        interval = 1.0 / rps
        attempted = succeeded = failed = 0
        start = time.monotonic()
        deadline = start + duration
        while time.monotonic() < deadline:
            tick = time.monotonic()
            command_id = str(uuid.uuid4())
            attempted += 1
            request = urllib.request.Request(
                target, data=b"{}", method="POST", headers={"Idempotency-Key": command_id}
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    response.read()
                    if 200 <= response.status < 300:
                        succeeded += 1
                    else:
                        failed += 1
            except urllib.error.HTTPError as error:
                error.close()
                failed += 1
            except (urllib.error.URLError, TimeoutError, OSError):
                failed += 1
            pause = min(interval - (time.monotonic() - tick), deadline - time.monotonic())
            if pause > 0:
                time.sleep(pause)
        elapsed = time.monotonic() - start
        return {
            "attempted": attempted,
            "succeeded": succeeded,
            "failed": failed,
            "requested_rps_cap": rps,
            "elapsed_seconds": elapsed,
            "achieved_rps": attempted / elapsed if elapsed else 0,
        }


    if __name__ == "__main__":
        print(json.dumps(run()), flush=True)
```

</details>

주문 서버의 0.1초 지연은 기록 **이전**에 있어 트랜잭션 commit 이후 응답 소실 실험이 아닙니다. Collector timeout·오류에는 503을 반환하고 결과는 미확정입니다. Observer가 기록한 뒤 응답만 잃었을 수도 있습니다. Client 성공은 이 예시의 observer 확인 응답이며 실제 업무의 exactly-once 실행 증명이 아닙니다.

처음 네 리소스를 t2-servers.yaml, 마지막 Job을 order-client-job.yaml로 저장합니다. 각 케이스는 이전 client가 없는 새 collector에서 시작하고 모든 metadata.namespace를 일관되게 변경하세요. 짧은 Service 이름은 선택한 네임스페이스 안에서 호출하도록 합니다.

<details>
<summary>Collector/order Deployment·Service와 제한된 client Job</summary>

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
    name: http
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: collector
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/collector.py
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 9090
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
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
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: order
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/order_server.py
        env:
        - name: COLLECTOR_URL
          value: http://collector:9090/record
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 8080
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: batch/v1
kind: Job
metadata:
  generateName: order-client-
  namespace: mesh-test-sidecar
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 360
  template:
    metadata:
      labels:
        app: order-client
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
    spec:
      restartPolicy: Never
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/client.py
        env:
        - name: TARGET_URL
          value: http://order:8080/order
        - name: RPS
          value: '20'
        - name: DURATION_SECONDS
          value: '300'
        - name: TIMEOUT_SECONDS
          value: '12'
        volumeMounts:
        - name: scripts
          mountPath: /scripts
          readOnly: true
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

Job은 자동 재시도하지 않으며 선택된 sidecar 주입이 Job 완료를 막지 않도록 native-sidecar annotation을 사용합니다. 이 annotation 자체가 ambient enrollment나 sidecar 주입을 활성화하지는 않습니다. 실제 Job Pod와 namespace enrollment를 확인하세요. 수정 템플릿은 TCP readiness 검사를 추가하고 검토 중 확인한 registry digest로 Python 이미지를 고정합니다. 과거 보고에는 해당 digest가 없습니다. 로컬 동작은 호스트 Python 3.9 표준 라이브러리로 검사했으며 Python 3.12 컨테이너 실행이나 리소스 배포는 하지 않았습니다.

Client는 **순차 실행**입니다. RPS 20은 새로운 시도 수의 상한이지 일정한 open-loop 20 QPS 보장이 아닙니다. 서버 지연 0.1초와 오류로 실제 처리율이 낮아집니다. DURATION_SECONDS는 새 요청 시작을 제한하며 마지막 요청은 timeout만큼 종료 시간을 늘릴 수 있습니다. 최종 JSON에는 attempted/succeeded/failed와 achieved_rps가 있고 attempted = succeeded + failed입니다.

주문 명령과 **observer 쓰기 모두** retry를 끈 route로 시작합니다. 두 리소스를 order-no-retry.yaml로 저장합니다:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: collector-observer-no-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - collector
  http:
  - name: observer-record
    match:
    - method:
        exact: POST
      uri:
        exact: /record
    route:
    - destination:
        host: collector
        port:
          number: 9090
    timeout: 10s
    retries:
      attempts: 0
```

의도적인 **격리된 위험 retry 실험에만** 주문 정책을 다음 order-retry-experiment.yaml로 바꾸고 collector no-retry 정책은 유지합니다. 중복 전달 가능성을 드러내려는 실험이며 운영 쓰기 retry 권장이 아닙니다.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

3회 retry는 최초 요청을 포함해 최대 4회 시도를 허용합니다. Per-try 2초와 route timeout 10초는 연결·설정 시간과 상호작용합니다. Client timeout 12초는 더 긴 관측 창을 주지만 모든 시도가 발생했음을 증명하지 않습니다. 실제 proxy 설정과 retry counter를 수집하세요.

보고된 Istio 1.30 계열에서 ambient VirtualService는 Alpha이며 Gateway API 트래픽 설정과 혼용은 지원하지 않습니다. 경쟁하는 HTTPRoute를 설치하지 마세요. 실제 client sidecar 또는 목적지 waypoint의 적용 route를 확인합니다. Ambient L4만으로 HTTP retry 정책을 적용할 수 없습니다.

```bash
# A fresh collector and no earlier client must be running for this case.
# Replace metadata.namespace in every input with NS; explicit -n catches mismatches.
kmesh -n "$NS" apply -f t2-configmap.yaml -f t2-servers.yaml -f order-no-retry.yaml
kmesh -n "$NS" rollout status deployment/collector --timeout=120s
kmesh -n "$NS" rollout status deployment/order --timeout=120s
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-before.json"

# For the deliberate retry experiment only, replace the no-retry policy with
# order-retry-experiment.yaml and verify the effective proxy configuration first.
JOB_RESOURCE=$(kmesh -n "$NS" create -f order-client-job.yaml -o name)
JOB_NAME=${JOB_RESOURCE#*/}
if ! kmesh -n "$NS" wait --for=condition=complete "$JOB_RESOURCE" --timeout=370s; then
  kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client-failed.log" || true
  echo "Invalid/incomplete client run" >&2
  exit 1
fi
kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client.json"
jq -e '.attempted > 0 and .attempted == (.succeeded + .failed)' \
  "$RUN_DIR/client.json" >/dev/null
kmesh -n "$NS" get pods -l "batch.kubernetes.io/job-name=$JOB_NAME" \
  -o json >"$RUN_DIR/client-pods.json"
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-after.json"
kmesh -n "$NS" logs -l app=order -c order --prefix --tail=-1 \
  --max-log-requests=10 >"$RUN_DIR/available-order.log"
kmesh -n "$NS" exec deployment/collector -c collector -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9090/dupes', timeout=5).read().decode())" \
  >"$RUN_DIR/observer.json"
```

이 driver는 설정과 집계를 담당하며 주문 롤아웃을 **시작하지 않습니다**. Churn 실험에는 §F의 제한된 루프를 deployment/order 대상으로 조정해 300초 client 구간과 맞추고 두 시간선을 보관해야 합니다. 그 조정이 없다면 출력은 정상 상태 observer 검사입니다.

Client 실행 중 observer를 reset하지 마세요. 전후 collector Pod UID와 restart count를 비교하고 모든 order·observer 오류를 보관하며 삭제된 Pod의 로그도 유지해야 합니다. 위 명령은 현재 Pod에 남은 로그만 가져옵니다. Observer 재시작, 로그 누락 또는 observer 오류가 있으면 완전한 중복 검출을 주장할 수 없습니다. 실제 트랜잭션 안전성 조사에는 명령별 영속 원장과 통제된 commit 이후 응답 소실 실험이 필요합니다.

## 참고 자료와 검증 경계

- [Istio 1.30.2 릴리스](https://github.com/istio/istio/releases/tag/1.30.2), [릴리스 의존성](https://github.com/istio/istio/blob/1.30.2/go.mod), [프록시 종료 구현](https://github.com/istio/istio/blob/1.30.2/pkg/envoy/agent.go)
- [Istio 1.30 ambient L7 기능 상태](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md)와 [트래픽 관리](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/traffic-distribution/index.md)
- [Kubernetes 컨테이너 lifecycle hook](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/)과 [native sidecar](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Amazon EKS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)와 [설정·시작 모드](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Cilium 정책 지원](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/index.rst)
- [Fortio 1.69.4 소스·사용법](https://github.com/fortio/fortio/tree/v1.69.4)과 [컨테이너 빌드](https://github.com/fortio/fortio/blob/v1.69.4/Dockerfile)

설정 생성, 스키마, 산술과 로컬 HTTP 검사는 위의 구체적인 수정을 뒷받침합니다. 과거 EKS 측정값, 운영 성능, 미검증 애드온 조합의 호환성 또는 업무의 exactly-once 실행을 재현·보장하지 않습니다.
