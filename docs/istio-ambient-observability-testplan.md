# Istio Ambient — 관측성/트러블슈팅 실측 테스트 플랜 (T6~T11)

> **상태**: 미실행 (플랜만 작성됨)
> **작성일**: 2026년 8월 20일 · **최종 갱신**: 2026년 9월 2일
> **위치**: `docs/` — `site-scope.mjs`가 `docs/**`를 발행에서 제외하므로 사이트에 노출되지 않는 내부 문서입니다. 게시용 결과는 아래 §"결과를 문서에 어떻게 반영하는가"의 대상 문서에 작성합니다.
> **선행 테스트**: T1~T5 (완료) — `ko/service-mesh/istio/comparison/03-sidecar-vs-ambient.md` (부록 A~H에 재현 절차 있음)

> ⚠️ **실행 환경은 AWS 자격증명이 살아 있는 로컬 워크스테이션(맥북)입니다.** Claude Code 웹/원격 세션에서는 실행할 수 없습니다 — 2026-09-02 확인 결과 원격 컨테이너의 AWS 자격증명은 STS `InvalidClientTokenId`로 무효하고, `eksctl`·`kubectl`·`istioctl`도 설치돼 있지 않습니다. 또한 원격 컨테이너는 유휴 시 회수되므로, 테스트 중 세션이 끊기면 노드그룹 4개짜리 클러스터가 그대로 과금됩니다. 클러스터 생성은 반드시 수명을 통제할 수 있는 환경에서 하세요.

## 왜 이 테스트가 필요한가

고객 질문(게임팀 경유):

> "Istio Ambient 모드에 mTLS tunnel을 적용했을 때 성능상의 issue나, traffic이 암호화되어 troubleshooting이 어려워지는 문제가 없는지"

**성능 부분은 이미 답이 있습니다.** T5(latency)·T1(rollout 503) 실측으로 `03-sidecar-vs-ambient.md` §3~§4에 정리돼 있습니다 — ambient-L4는 no-mesh 대비 P50 +0.04ms, rollout 중 503 0건.

**트러블슈팅 부분은 문서에 없습니다.** 그리고 이건 도구 목록을 나열해서 채울 갭이 아닙니다 — 아래 가설이 맞다면 기존 §3~§5 권장안(계층화 접근)에 직접 영향을 주는 trade-off가 하나 더 생깁니다.

## 핵심 가설

> **H1.** mTLS 암호화 자체는 트러블슈팅을 어렵게 만들지 않는다. 프록시(sidecar/ztunnel/waypoint)가 암호화 **이전/이후** 지점에서 로그·메트릭을 생성하기 때문에, wire가 암호문이어도 프록시 레벨 가시성은 그대로다. 이는 sidecar와 ambient 모두 동일하다.
>
> **H2.** 진짜 가시성 차이는 암호화가 아니라 **L4냐 L7이냐**에서 온다. ztunnel은 L4 프록시이므로 HTTP를 파싱하지 않고, 따라서 ambient-L4에서는 **응답 코드·경로·메서드·요청별 지연이 telemetry에 나오지 않을 것**이다 (`istio_tcp_*`만 있고 `istio_requests_total`은 없음).
>
> **H3.** 따라서 T3/T5(성능·안정성)에서 가장 우수했던 ambient-L4가 **관측성에서는 가장 열등**하다. 성능과 가시성이 같은 축에서 충돌하며, HTTP 레벨 진단이 필요하면 waypoint를 붙여야 하는데 그러면 §3(+1.86ms)·§4(503 2.6%)의 비용이 따라온다.
>
> **H4.** (보안 관련) ambient-L4 워크로드에 **L7 조건(경로 기반) AuthorizationPolicy를 적용하면 조용히 무시될 것**이다 — ztunnel이 경로를 볼 수 없으므로. 에러 없이 정책이 미적용되면 운영상 함정이 된다.

H2·H3가 확인되면 고객 답변은 이렇게 됩니다:

> "암호화 때문에 트러블슈팅이 어려워지는 건 아닙니다 — sidecar도 wire는 똑같이 암호문이고, 양쪽 다 프록시 로그에서 평문 관점을 봅니다. 다만 ambient **L4-only**를 쓰면 HTTP 레벨 telemetry가 없어서 '어느 요청이 500을 냈는지'를 mesh에서 알 수 없습니다. 그게 필요하면 waypoint가 필요하고, waypoint는 지연과 rollout 503 리스크를 다시 가져옵니다."

H4는 별도로 §2(NetworkPolicy 함정)와 같은 급의 운영 함정으로 다룰 가치가 있습니다.

## 고객 환경 (2026-08-20 확인)

문의 경로: 게임팀 → 고객이 Ambient 도입 검토 중

| 항목 | 답변 | 영향 |
|---|---|---|
| 트래픽 종류 | 게임 서버 아님, **게임 플랫폼 트래픽 (HTTPS)** | UDP 아님 → mesh 적용 대상 확정. 단 TLS 종료 지점 확인 필요 → **T11** |
| 인스턴스 | m5 / m5d / m5ad / m6i / m7i.xlarge 검토 중, Graviton 병행 추천 | x86 재측정 필요 → **T10** |
| HTTP telemetry | "아마도 mesh로부터 받아야 할 것", 별도 APM 유무 확인 중 | L7 telemetry 요구 → waypoint 필요 가능성 → T6 결과가 직접적 근거 |
| 추가 요청 | 테스트 환경 공유 / ztunnel 로그 활용 방안 안내 | 환경은 부록 A~D로 즉시 공유 가능. ztunnel 로그는 T6·T8이 그대로 답 |

> 📌 **미해결 갈림길**: HTTPS를 게이트웨이에서 종료하는지, 파드 간 통신도 앱이 HTTPS로 처리하는지 미확인. 후자면 waypoint를 붙여도 L7 telemetry를 받을 수 없어 고객의 4번 요구가 구성상 불가능합니다. T11 실행 여부와 최종 권고가 여기서 갈립니다.

## 사전 준비

### 클러스터

`03-sidecar-vs-ambient.md` **부록 A~D를 그대로 재사용**합니다. 새로 만들 것 없음:

- 부록 A — `eksctl-cluster.yaml` (`mesh-isolated-test`, m7g.xlarge × 3, ap-northeast-2)
- 부록 B — Gateway API CRD v1.1.0 + `istioctl install -f ambient-overlay.yaml`
- 부록 C — 4개 네임스페이스(`mesh-test-base` / `-sidecar` / `-ambient-l4` / `-ambient-l7`) + echo(6 replica)/fortio 워크로드
- 부록 D — `PeerAuthentication` STRICT × 3 + `istioctl waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait`

> ⚠️ **kubeconfig 격리** — T1~T5 때 워크스테이션의 `~/.kube/config` current-context가 조용히 바뀌어 측정 1회가 무효화된 이력이 있습니다(§4 격리 노트). 전용 kubeconfig를 만들고 모든 스크립트가 이를 명시 참조하게 하세요.
>
> ```bash
> export KUBECONFIG=$HOME/.kube/mesh-isolated-test.yaml
> aws eks update-kubeconfig --name mesh-isolated-test --region ap-northeast-2
> # 가드: 컨텍스트가 흐트러지면 즉시 중단
> kubectl config current-context | grep -q mesh-isolated-test || { echo "WRONG CONTEXT"; exit 1; }
> ```

### 추가 준비 — access log 활성화 (필수)

**T1~T5에는 없던 단계입니다.** access log를 켜지 않으면 sidecar/waypoint 로그가 비어 있어 T6이 전부 무의미해집니다.

```yaml
# telemetry-accesslog.yaml — 재설치 없이 Telemetry API로 활성화
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-access-log
  namespace: istio-system
spec:
  accessLogging:
  - providers:
    - name: envoy
```

```bash
kubectl apply -f telemetry-accesslog.yaml
```

> 📌 **확인 필요**: 이 Telemetry 리소스가 ztunnel에도 적용되는지. ztunnel은 access log를 항상 stdout으로 내보내며 Telemetry API 제어 대상이 아닐 가능성이 높습니다 — T6-a에서 실제 확인하고 결과에 기록하세요.

### 프록시별 메트릭/로그 엔드포인트

포트는 버전에 따라 다를 수 있으므로 **먼저 확인**합니다:

```bash
ZT=$(kubectl get pod -n istio-system -l app=ztunnel -o jsonpath='{.items[0].metadata.name}')
kubectl get pod -n istio-system "$ZT" -o jsonpath='{.spec.containers[*].ports[*]}' | jq .
istioctl ztunnel-config --help   # 서브커맨드 단/복수형 확인 (workload vs workloads 등)
```

| 대상 | 메트릭 | Access log |
|---|---|---|
| ztunnel | `localhost:15020/metrics` (확인 필요) | `kubectl logs -n istio-system -l app=ztunnel` |
| sidecar | `localhost:15000/stats/prometheus` | `kubectl logs <pod> -c istio-proxy` |
| waypoint | `localhost:15020/stats/prometheus` (확인 필요) | `kubectl logs <waypoint-pod>` |

---

## T6 — 모드별 관측성 매트릭스 (핵심, H1·H2·H3 검증)

### 목적

같은 요청을 3개 모드에 흘렸을 때 **각 모드에서 무엇을 볼 수 있는가**를 필드 단위로 비교합니다. 이것이 이번 라운드의 본체입니다.

### 실행

**① 식별 가능한 트래픽 생성** — 경로와 응답 코드를 다르게 해서 로그에 무엇이 남는지 봅니다. fortio의 echo 핸들러는 `status`/`delay` 쿼리 파라미터를 지원합니다.

```bash
for NS in mesh-test-sidecar mesh-test-ambient-l4 mesh-test-ambient-l7; do
  CLIENT=$(kubectl get pod -n "$NS" -l app=fortio-client -o jsonpath='{.items[0].metadata.name}')
  # 200 / 500 / 404 를 서로 다른 경로로
  for CASE in "/api/orders?status=200" "/api/payment?status=500" "/api/missing?status=404" "/api/slow?status=200&delay=300ms"; do
    kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
      fortio load -qps 5 -t 10s -c 2 -allow-initial-errors "http://echo:8080${CASE}"
  done
done
```

**② 각 모드의 access log 수집**

```bash
# ztunnel (ambient 양쪽 모드 담당)
kubectl logs -n istio-system -l app=ztunnel --tail=200 > /tmp/log-ztunnel.txt

# sidecar
POD=$(kubectl get pod -n mesh-test-sidecar -l app=echo -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n mesh-test-sidecar "$POD" -c istio-proxy --tail=200 > /tmp/log-sidecar.txt

# waypoint
WP=$(kubectl get pod -n mesh-test-ambient-l7 -l gateway.networking.k8s.io/gateway-name -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n mesh-test-ambient-l7 "$WP" --tail=200 > /tmp/log-waypoint.txt
```

**③ 각 프록시의 메트릭 수집** — `istio_requests_total`(L7) 유무가 H2의 판정 기준입니다.

```bash
# ztunnel
kubectl exec -n istio-system "$ZT" -- curl -s localhost:15020/metrics \
  | grep -E '^istio_(requests|tcp)' | cut -d'{' -f1 | sort -u

# sidecar
kubectl exec -n mesh-test-sidecar "$POD" -c istio-proxy -- curl -s localhost:15000/stats/prometheus \
  | grep -E '^istio_(requests|tcp)' | cut -d'{' -f1 | sort -u

# waypoint
kubectl exec -n mesh-test-ambient-l7 "$WP" -- curl -s localhost:15020/stats/prometheus \
  | grep -E '^istio_(requests|tcp)' | cut -d'{' -f1 | sort -u
```

**④ (선택) Kiali 그래프** — L4-only 서비스가 그래프에서 어떻게 표현되는지. Prometheus/Kiali 애드온이 필요합니다.

```bash
kubectl apply -f samples/addons/prometheus.yaml -f samples/addons/kiali.yaml
istioctl dashboard kiali
# 3개 네임스페이스 그래프를 각각 캡처 — L4-only에 HTTP 엣지 라벨(rps, %2xx)이 붙는지 확인
```

### 결과 표 (채울 골격)

| 관측 항목 | sidecar | ambient-L4 | ambient-L7 (waypoint) |
|---|---|---|---|
| HTTP 응답 코드 (access log) | | | |
| 요청 경로 | | | |
| HTTP 메서드 | | | |
| 요청별 지연 | | | |
| `istio_requests_total` 메트릭 | | | |
| `istio_tcp_*` 메트릭 | | | |
| src/dst SPIFFE identity | | | |
| 전송 바이트 | | | |
| Kiali 그래프 HTTP 엣지 라벨 | | | |

원본 로그 한 줄씩 샘플로 첨부(모드별 1건) — 문서에서 `<details>` 블록으로 넣을 예정.

### 판정 기준

- **H2 확인**: ambient-L4에 `istio_requests_total` 부재 + access log에 응답 코드/경로 부재
- **H2 반증**: ambient-L4에도 HTTP 필드가 나옴 → 가설 폐기, 문서는 "가시성 차이 없음"으로 정리
- **H1 확인**: 세 모드 모두 프록시 로그에서 평문 관점이 보임 (암호화가 로그를 가리지 않음)

---

## T7 — wire-level 캡처 (H1 검증)

### 목적

"트래픽이 암호화돼서 못 본다"는 우려를 **직접 시연**하고, 동시에 그게 ambient 고유 문제가 아님(sidecar도 동일)을 보입니다. 그리고 **평문을 어디서 볼 수 있는지**를 확정합니다.

### 실행

**① 노드 간 캡처 — 암호문 확인.** 먼저 echo/client가 서로 다른 노드에 있는지 확인합니다.

```bash
kubectl get pod -n mesh-test-ambient-l4 -o wide   # client와 echo가 다른 노드여야 함
NODE=$(kubectl get pod -n mesh-test-ambient-l4 -l app=echo -o jsonpath='{.items[0].spec.nodeName}')

# ambient: HBONE (15008)
kubectl debug node/"$NODE" -it --image=nicolaka/netshoot -- \
  tcpdump -i any -n 'tcp port 15008' -A -c 40

# sidecar: inbound mTLS (15006)
NODE_SC=$(kubectl get pod -n mesh-test-sidecar -l app=echo -o jsonpath='{.items[0].spec.nodeName}')
kubectl debug node/"$NODE_SC" -it --image=nicolaka/netshoot -- \
  tcpdump -i any -n 'tcp port 15006' -A -c 40
```

부하를 동시에 흘려야 잡힙니다 — 별 터미널에서 T6-① 루프를 돌리세요.

**② 파드 netns 내부 캡처 — 평문이 보이는가.** ambient는 istio-cni가 파드 netns에서 트래픽을 리다이렉트하므로, 파드 내부에서는 리다이렉트 **이전** 평문이 보일 가능성이 있습니다. sidecar는 app↔proxy 루프백이 평문입니다.

```bash
# ambient 파드 (사이드카 없음) — ephemeral 컨테이너가 파드 netns 공유
kubectl debug -n mesh-test-ambient-l4 -it "$(kubectl get pod -n mesh-test-ambient-l4 -l app=echo -o jsonpath='{.items[0].metadata.name}')" \
  --image=nicolaka/netshoot --profile=netadmin -- tcpdump -i any -n 'tcp port 8080' -A -c 40
```

> ⚠️ tcpdump에는 `NET_RAW`/`NET_ADMIN`이 필요합니다. `--profile=netadmin`이 없으면 권한 오류가 납니다. 실패하면 `--profile=sysadmin`으로 재시도하고, 어느 프로파일이 필요했는지 기록하세요.

### 결과 표

| 캡처 지점 | sidecar | ambient-L4 | ambient-L7 |
|---|---|---|---|
| 노드 간 wire (15008 / 15006) | | | |
| 파드 netns 내부 (8080) | | | |
| 평문을 볼 수 있는 위치 | | | |

### 문서화 포인트

- 양쪽 모드 모두 wire는 암호문 → **암호화는 ambient 고유 문제가 아님**
- 평문 관점은 wire 캡처가 아니라 **프록시 access log / netns 내부 캡처**에서 얻는다
- 따라서 "tcpdump로 못 본다"는 트러블슈팅 방법론 변경 이슈이며, 가시성 상실이 아니다

---

## T8 — ztunnel/waypoint 진단 도구 실제 출력 (레퍼런스용)

### 목적

Ambient 전용 진단 명령의 **실제 출력**을 확보합니다. 문서에 붙일 레퍼런스이자, sidecar의 `istioctl proxy-config`에 대응하는 대조표를 만듭니다.

### 실행

```bash
# ztunnel 계열 (서브커맨드 단/복수형은 --help로 먼저 확인)
istioctl ztunnel-config workloads   > /tmp/zt-workloads.txt
istioctl ztunnel-config services    > /tmp/zt-services.txt
istioctl ztunnel-config certificates > /tmp/zt-certs.txt
istioctl ztunnel-config policies    > /tmp/zt-policies.txt
istioctl ztunnel-config all -o json > /tmp/zt-all.json

# ztunnel 동적 로그 레벨 — 올렸을 때 추가로 무엇이 보이는지
istioctl ztunnel-config log --level debug
kubectl logs -n istio-system -l app=ztunnel --tail=100 > /tmp/zt-debug.txt
istioctl ztunnel-config log --level info   # 원복

# waypoint는 Envoy이므로 기존 도구가 그대로 통함
istioctl proxy-config all "$WP" -n mesh-test-ambient-l7 > /tmp/wp-config.txt

# ambient 파드에 기존 도구가 통하는가?
istioctl x describe pod "$(kubectl get pod -n mesh-test-ambient-l4 -l app=echo -o jsonpath='{.items[0].metadata.name}')" -n mesh-test-ambient-l4
istioctl proxy-config all "$(kubectl get pod -n mesh-test-ambient-l4 -l app=echo -o jsonpath='{.items[0].metadata.name}')" -n mesh-test-ambient-l4  # 실패 예상 — 에러 메시지 기록
```

### 결과 표 — sidecar ↔ ambient 도구 대응

| 하고 싶은 것 | sidecar | ambient |
|---|---|---|
| 워크로드 목록/상태 | `istioctl proxy-status` | |
| 인증서 확인 | `istioctl proxy-config secret` | |
| 정책 적용 확인 | `istioctl proxy-config listener` | |
| 라우팅 확인 | `istioctl proxy-config route` | |
| 로그 레벨 변경 | `istioctl proxy-config log` | |
| 파드 요약 진단 | `istioctl x describe pod` | |

각 ambient 칸에 실제로 동작한 명령을 넣고, 통하지 않는 것은 에러 메시지를 그대로 기록.

---

## T9 — 실패 시나리오 진단 실습 (H4 포함)

### 목적

"트러블슈팅이 어려워지는가"에 대한 실질적 답. 각 모드에 **같은 장애를 주입**하고, 원인에 도달하기까지 어떤 도구가 필요했는지를 기록합니다.

### 시나리오

**S1 — L4 AuthorizationPolicy DENY (principal 기반)**

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-l4
  namespace: mesh-test-ambient-l4
spec:
  selector:
    matchLabels:
      app: echo
  action: DENY
  rules:
  - from:
    - source:
        notPrincipals: ["cluster.local/ns/mesh-test-ambient-l4/sa/nonexistent"]
```

기대: L4 조건이므로 ztunnel이 강제 가능. 클라이언트가 보는 에러와 ztunnel 로그 라인을 기록.

**S2 — L7 AuthorizationPolicy DENY (경로 기반) — H4 검증, 가장 중요**

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-l7-path
  namespace: mesh-test-ambient-l4   # waypoint 없는 네임스페이스에 의도적으로 적용
spec:
  selector:
    matchLabels:
      app: echo
  action: DENY
  rules:
  - to:
    - operation:
        paths: ["/api/payment"]
```

확인 사항:
- `/api/payment` 요청이 실제로 차단되는가, 아니면 **그냥 통과하는가**?
- `istioctl analyze -n mesh-test-ambient-l4`가 경고를 내는가?
- 정책 리소스의 `status`에 무언가 표시되는가?
- 같은 정책을 `mesh-test-ambient-l7`(waypoint 있음)에 적용하면 차단되는가?

> 통과 + 경고 없음이면 **§2의 NetworkPolicy 함정과 동급의 운영 함정**입니다. 문서에 경고 콜아웃으로 반드시 넣어야 합니다.

**S3 — 애플리케이션이 500을 반환**

```bash
# echo가 500을 내도록 요청
fortio load -qps 5 -t 20s "http://echo:8080/api/payment?status=500"
```

확인 사항: mesh telemetry만으로 "어느 파드가 500을 냈는지" 알 수 있는가? 모드별로 답이 다를 것(H2·H3의 실전 형태). 답을 얻는 데 필요한 최소 도구를 기록.

**S4 — NetworkPolicy가 15008을 차단 (§2 재현, 진단 경로에 집중)**

§2의 "8080만 허용" NetworkPolicy를 다시 적용하고, **증상만 보고 원인에 도달하는 경로**를 기록합니다. `i/o timeout`에서 "HBONE 포트가 막혔다"까지 어떤 도구가 답을 줬는가?

### 결과 표

| 시나리오 | 모드 | 클라이언트가 본 증상 | 원인을 알려준 도구 | 진단 난이도 |
|---|---|---|---|---|
| S1 L4 DENY | sidecar / L4 / L7 | | | |
| S2 L7 DENY (경로) | sidecar / L4 / L7 | | | |
| S3 앱 500 | sidecar / L4 / L7 | | | |
| S4 NetPol 15008 차단 | L4 / L7 | | | |

---

## T10 — 인스턴스 타입별 latency 재측정 (고객 요청)

### 목적

기존 T5는 m7g.xlarge(Graviton3) 단일 조건입니다. 고객이 **m5 / m5d / m5ad / m6i / m7i.xlarge**를 검토 중이고 Graviton과의 비교를 원하므로, 같은 조건에서 CPU 세대별로 재측정합니다.

대상 인스턴스는 crypto 처리 특성이 실제로 다릅니다:

| 인스턴스 | CPU | 비고 |
|---|---|---|
| m5.xlarge | Intel Skylake / Cascade Lake | m5d는 로컬 NVMe만 차이 → CPU 동일, 생략 가능 |
| m5ad.xlarge | AMD EPYC 7000 series | 아키텍처가 달라 별도 측정 가치 있음 |
| m6i.xlarge | Intel Ice Lake | |
| m7i.xlarge | Intel Sapphire Rapids | |
| m7g.xlarge | AWS Graviton3 (ARMv8.2 crypto) | T5 기존 측정치, 기준선 |

### 설계 — 클러스터 하나에 멀티 노드그룹

인스턴스별로 클러스터를 새로 만들지 않고, **한 클러스터에 노드그룹을 병렬로 두고 workload를 nodeSelector로 이동**시키며 라운드를 반복합니다. 비용과 시간이 크게 줄고, 컨트롤플레인·Istio 버전이 고정되므로 비교 조건도 더 깨끗합니다.

```yaml
# 부록 A의 managedNodeGroups를 교체
managedNodeGroups:
  - name: ng-m5
    instanceType: m5.xlarge
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    labels: { mesh-test/cpu: m5 }
  - name: ng-m6i
    instanceType: m6i.xlarge
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    labels: { mesh-test/cpu: m6i }
  - name: ng-m7i
    instanceType: m7i.xlarge
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    labels: { mesh-test/cpu: m7i }
  - name: ng-m7g
    instanceType: m7g.xlarge
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    labels: { mesh-test/cpu: m7g }
```

> ⚠️ **부록 B의 `ambient-overlay.yaml`을 반드시 수정해야 합니다.** 기존 오버레이는 CNI·ztunnel·istiod를 `kubernetes.io/arch: arm64`로 **강제 고정**합니다. 혼합 아키텍처 클러스터에서 이대로 두면 x86 노드에 ztunnel DaemonSet이 배포되지 않아 해당 노드의 ambient 파드가 mesh에 들어오지 못합니다. **nodeAffinity 블록 전체를 제거**하세요 (Istio 이미지는 멀티아치입니다).

> ⚠️ **부록 C 워크로드의 `nodeSelector: kubernetes.io/arch: arm64`도 제거**하고, 대신 라운드마다 `mesh-test/cpu` 레이블로 패치합니다.

### 실행

```bash
for CPU in m5 m6i m7i m7g; do
  for NS in mesh-test-base mesh-test-sidecar mesh-test-ambient-l4 mesh-test-ambient-l7; do
    kubectl patch deploy/echo -n "$NS" -p \
      "{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"mesh-test/cpu\":\"$CPU\"}}}}}"
    kubectl patch deploy/fortio-client -n "$NS" -p \
      "{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"mesh-test/cpu\":\"$CPU\"}}}}}"
    kubectl rollout status deploy/echo deploy/fortio-client -n "$NS" --timeout=180s
  done

  # waypoint도 같은 노드그룹으로 이동해야 ambient-L7 측정이 유효
  kubectl patch deploy -n mesh-test-ambient-l7 -l gateway.networking.k8s.io/gateway-name -p \
    "{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"mesh-test/cpu\":\"$CPU\"}}}}}"

  # T5와 동일한 부하 (부록 G)
  for NS in mesh-test-base mesh-test-sidecar mesh-test-ambient-l4 mesh-test-ambient-l7; do
    CLIENT=$(kubectl get pod -n "$NS" -l app=fortio-client -o jsonpath='{.items[0].metadata.name}')
    echo "=== $CPU / $NS ==="
    kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
      fortio load -qps 200 -t 60s -c 16 -allow-initial-errors http://echo:8080/
  done
done
```

> 📌 client와 echo가 **같은 인스턴스 타입 노드**에 있어야 측정이 유효합니다. 라운드마다 `kubectl get pod -o wide`로 확인하세요. 노드그룹별 desiredCapacity 3이면 같은 그룹 안에서 분산되므로 조건이 만족됩니다.

### 결과 표

| 인스턴스 | no-mesh P50 | ambient-L4 P50 | sidecar P50 | ambient-L7 P50 | L4 오버헤드 |
|---|---|---|---|---|---|
| m5.xlarge | | | | | |
| m5ad.xlarge (선택) | | | | | |
| m6i.xlarge | | | | | |
| m7i.xlarge | | | | | |
| m7g.xlarge | 0.82ms | 0.86ms | 2.11ms | 2.68ms | +0.04ms |

P99도 같은 형식으로 병기. m7g 행은 T5 기존 측정치이며, 혼합 클러스터에서 재측정해 재현되는지 교차 확인할 것.

### 가설

> **H5.** mesh 모드 간 **상대 순서**(ambient-L4 ≈ no-mesh < sidecar < ambient-L7)는 프록시 홉 수에서 오는 아키텍처적 특성이라 CPU와 무관하게 유지된다. 반면 **절대 오버헤드**는 crypto 처리량에 비례해 세대별로 달라진다.

H5가 확인되면 "인스턴스 타입은 절대 성능을 바꾸지만 mesh 모드 선택 기준은 바꾸지 않는다"가 결론이 되어 권장안이 인스턴스와 독립적으로 성립합니다.

---

## T11 — 애플리케이션 레벨 HTTPS (이중 암호화) 영향 — 조건부

> **실행 조건**: 고객의 파드 간 통신이 애플리케이션 HTTPS인 경우에만. 외부 진입 구간에서만 TLS를 종료하고 mesh 내부가 평문 HTTP라면 이 테스트는 불필요합니다.

### 배경

고객 트래픽이 HTTPS(게임 플랫폼)인데, **TLS 종료 지점**에 따라 결론이 완전히 달라집니다.

- **(a) 게이트웨이에서 종료, mesh 내부는 평문 HTTP** — 표준 패턴. mesh mTLS가 파드 간 암호화 담당. T5/T6/T10 측정치가 그대로 적용되고 waypoint로 L7 telemetry 확보 가능.
- **(b) 파드 간 통신도 앱이 HTTPS로 처리** — waypoint가 보는 것은 앱이 암호화한 TLS 바이트이므로 **HTTP 파싱 불가**. waypoint를 붙여도 L7 telemetry·라우팅·retry가 동작하지 않고, Istio는 해당 포트를 TCP로 취급. 게다가 앱 TLS + HBONE mTLS **이중 암호화**로 오버헤드가 실제 증가.

(b)라면 "mesh에서 HTTP telemetry를 받는다"는 요구가 **구성 자체로 불가능**하므로, 진단 전에 확인이 필요한 갈림길입니다.

### 검증

echo 워크로드를 TLS로 서빙하도록 바꾸고(fortio는 `-cert`/`-key`로 HTTPS 서버 가능), waypoint가 붙은 네임스페이스에서:

1. waypoint access log에 HTTP 필드가 남는가 → **안 남을 것으로 예상**
2. `istio_requests_total`이 증가하는가 → **증가하지 않을 것으로 예상**
3. VirtualService의 경로 기반 라우팅이 동작하는가 → **동작하지 않을 것으로 예상**
4. 평문 HTTP + mTLS 대비 latency 차이 (이중 암호화 비용)

### 결과 표

| 항목 | 평문 HTTP + mTLS | 앱 HTTPS + mTLS |
|---|---|---|
| waypoint access log HTTP 필드 | | |
| `istio_requests_total` | | |
| 경로 기반 라우팅 동작 | | |
| P50 / P99 | | |

이 결과는 고객에게 "(b) 구성이면 파드 간 TLS를 걷어내고 mesh mTLS에 위임하는 것이 정석"이라는 권고의 근거가 됩니다.

---

## 결과를 문서에 어떻게 반영하는가

### 1) `03-sidecar-vs-ambient.md` — 주 반영 대상

- **§6 신규 추가**: "관측성과 트러블슈팅 (T6~T9 실측)" — §5(종합 권장) 앞에 삽입
- **의사결정 요약표에 행 추가**: `HTTP 레벨 관측성` 행 — 4번째 요구사항 축으로 승격
- **§5 계층화 권장 표 갱신**: 코어 계층 근거에 "L4-only는 HTTP 진단 불가" 반영. 지금은 성능·안정성만 근거인데, 관측성이 반대 방향으로 작용하므로 권장안의 뉘앙스가 바뀔 수 있음
- **도입 전 체크리스트에 항목 추가**: L7 AuthorizationPolicy를 waypoint 없는 네임스페이스에 걸어둔 게 없는지 (S2 결과에 따라)
- **부록에 T6~T9 재현 절차 추가**: 기존 부록 A~H 뒤에 I~L로

### 2) `advanced/01-ambient-mode.md`

§문제 해결 섹션이 현재 2개 항목(ztunnel 미작동 / waypoint 트래픽 미도달)뿐입니다. T8의 도구 대응표와 T6의 관측성 매트릭스를 요약해 보강.

### 3) `security/01-mtls.md`

"암호화된 트래픽의 트러블슈팅" 서브섹션 신규 — H1의 결론(프록시가 평문 관점을 제공하므로 암호화가 가시성을 해치지 않음)을 아키텍처 설명으로. **이 부분만은 실측 없이 선행 작성 가능**합니다.

### 4) 언어 동기화

- `ko/` + `en/` 양쪽 작성 (리터럴 번역 아님, 동일 정보 전달). 현재 사이트가 발행하는 로케일은 이 둘뿐입니다 (`site-scope.mjs`의 `supportedLocales`).
- `cn/`/`jp/`/`es/`는 **직접 수정 금지** — `translate-sync.yml`이 `en/` 변경을 자동 반영합니다. 리포에는 유지되지만 현재 발행 대상에서는 제외돼 있으므로, 이 작업에서 신경 쓸 것은 없습니다.
- 새 파일을 만들지 않고 기존 문서에 섹션만 추가하는 방향이므로 `SUMMARY.md`/`README.md` 갱신은 불필요
- `npm run docs:validate`로 링크·이미지·ko/en 패리티 검사를 통과시킬 것 (PR CI가 같은 명령을 돌립니다)

### 5) 헤더 갱신

`03-sidecar-vs-ambient.md`의 `> **마지막 업데이트**`를 실행일로, 지원 버전은 실제 테스트한 EKS/Istio 버전으로.

## 실행 체크리스트

- [ ] 전용 kubeconfig 생성 + 컨텍스트 가드 스크립트
- [ ] 부록 A~D로 클러스터/워크로드/mTLS/waypoint 복원
- [ ] **access log 활성화** (Telemetry API) — 빠뜨리면 T6 무효
- [ ] ztunnel 메트릭 포트 및 `ztunnel-config` 서브커맨드 실제 이름 확인
- [ ] echo/client가 서로 다른 노드에 배치됐는지 확인 (T7 전제)
- [ ] T6 실행 → 관측성 매트릭스 완성 (H1·H2·H3 판정)
- [ ] T7 실행 → wire 암호문 + 평문 위치 확정
- [ ] T8 실행 → 도구 대응표 완성
- [ ] T9 실행 → 4개 시나리오, 특히 **S2(H4)** 결과 확정
- [ ] **T10 실행** → 인스턴스 타입별 표 완성 (H5 판정). 사전에 `ambient-overlay.yaml`의 arm64 nodeAffinity 제거 + 워크로드 nodeSelector 교체 필수
- [ ] **T11** — 고객이 파드 간 앱 HTTPS라고 답한 경우에만 실행
- [ ] 클러스터 삭제 (`eksctl delete cluster -f eksctl-cluster.yaml`) — `ephemeral: "true"` 태그 확인. 노드그룹 4개이므로 삭제 누락 시 비용 영향이 기존보다 큼
- [ ] ko/en 문서 반영 + 헤더 날짜 갱신
- [ ] 이 플랜 파일 삭제 또는 상태를 "완료"로 갱신

## 가설이 틀렸을 경우

H2가 반증되면(ambient-L4에도 HTTP telemetry가 있으면) 이 라운드의 결론은 훨씬 단순해집니다 — "성능도 좋고 가시성도 동등하다". 그 경우에도 T7(암호화 시연)·T8(도구 대응표)·T9-S2(L7 정책 함정)는 독립적으로 문서 가치가 있으므로 축소하지 말고 완주하세요. **가설 폐기도 결과이며, 문서에는 반증된 사실을 그대로 기록합니다** — T1~T5가 그렇게 작성돼 있습니다.
