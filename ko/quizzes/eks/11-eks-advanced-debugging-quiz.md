# Amazon EKS 고급 디버깅 퀴즈

> **마지막 업데이트**: 2026년 9월 12일

현재 API·범위·안전 전제는 [본문](../../eks/11-eks-advanced-debugging.md)에 따릅니다. 예시는 live cluster·benchmark 결과가 아니며 감사에서 cloud·cluster 작업을 실행하지 않았습니다.

이 퀴즈는 Amazon EKS의 고급 디버깅 기법, 인시던트 대응, 컨트롤 플레인 디버깅, 노드 문제 해결, kubectl debug, PromQL 쿼리, 관측성(Observability)에 대한 이해를 테스트합니다.

## 퀴즈 개요
- 인시던트 대응 프로세스
- EKS 컨트롤 플레인 디버깅
- 노드 및 kubelet 문제 해결
- kubectl debug 명령어 활용
- PromQL 쿼리 및 메트릭 분석
- 분산 추적 및 로그 분석

## 객관식 문제

### 1. 활성화된 EKS control-plane audit log는 보통 어디서 조회하나요?

A. 고객 관리 /var/log/kubernetes directory
B. Amazon CloudWatch Logs
C. Managed etcd 직접 접근
D. AWS control-plane Pod에 kubectl logs

<details>
<summary>정답 보기</summary>

**정답: B. Amazon CloudWatch Logs**

올바른 region·account의 `/aws/eks/<cluster-name>/cluster`를 사용합니다. Api·audit·authenticator·controllerManager·scheduler 다섯 유형은 opt-in이며 활성화가 과거 log를 복원하지 않습니다. 403은 인가 근거이지 IAM 인증 실패로 단정할 수 없습니다. 아래 query는 명시적 기간으로 Logs Insights QL에서 별도 실행합니다.

```bash
# Read-only: confirm logging is enabled before searching the owned group.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.logging
```
```text
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

</details>

### 2. kubectl debug에서 별도 Pod 복사본을 요청하는 flag는?

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>정답 보기</summary>

**정답: B. --copy-to**

이전 질문의 기존 Pod에 container 추가라는 표현은 잘못되었습니다. --copy-to는 다른 Pod를 만들고, 원래 Pod의 ephemeral container는 이 flag나 --ephemeral flag를 사용하지 않습니다. --target은 runtime이 지원할 때 process namespace를 요청합니다. 복사본은 ServiceAccount·env/Secret 참조·volume·다른 일반 container를 유지할 수 있어 init 제거·command 하나 변경만으로 격리된 data clone이 되지 않습니다.

```bash
# MUTATION: separate reviewed reproduction Pod, not an ephemeral container in the original.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${DEBUG_POD_NAME:?Choose a new owned name}"; : "${DEBUG_IMAGE:?Reviewed image providing sleep}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" \
  --copy-to="$DEBUG_POD_NAME" --container="$CONTAINER_NAME" --image="$DEBUG_IMAGE" \
  --keep-init-containers=false --share-processes=true --profile=general -- sleep 3600
```

</details>

### 3. NotReady node의 condition·heartbeat 확인 후 유용한 근거는?

A. 무관한 앱 log만
B. 적용 가능한 kubelet/runtime 상태·log와 network/EC2 근거
C. AWS 관리 etcd 직접 조작
D. CoreDNS log만으로 확정

<details>
<summary>정답 보기</summary>

**정답: B. 적용 가능한 kubelet/runtime 상태·log와 network/EC2 근거**

기존 “가장 흔한 원인” 주장을 뒷받침하는 측정 근거는 없습니다. Ready=False·heartbeat 부재/Unknown·resource pressure·instance 장애를 구분합니다. 호환 node의 인가된 host 접근 또는 NodeDiagnostic·문서화된 Auto Mode debug를 사용하며 SSH/systemctl을 보편적으로 적용하지 않습니다. 별도 검토한 restart·replacement 전에 범위를 제한해 log를 수집합니다.

```bash
# Read-only Kubernetes evidence first; no automatic kubelet restart.
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,nodeInfo:.status.nodeInfo,conditions:.status.conditions
}'
```

</details>

### 4. 양수로 설정된 CPU limit 대비 container CPU 사용을 나타내는 계산은?

A. 가정한 cpu_usage metric >80
B. 분모 없는 CPU seconds/second >0.8
C. CPU 사용 core / 일치하는 양수 CPU limit core
D. 가정한 container_cpu_percent metric

<details>
<summary>정답 보기</summary>

**정답: C. CPU 사용 core / 일치하는 양수 CPU limit core**

Rate(cpu_usage_seconds_total) 자체는 백분율이 아닌 CPU core입니다. Cluster 범위·namespace·Pod·container를 맞추고 양수 limit를 사용합니다. Limit 없음·누락이 사용률 0%는 아닙니다. HPA utilization은 보통 request 대비이므로 다른 계산입니다. 아래는 본문의 단일 cluster·label·scrape 전제에서 0.8 초과 비율을 보여 줍니다.

```promql
(sum by (namespace,pod,container) (
  rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
)
/ on (namespace,pod,container)
max by (namespace,pod,container) (
  kube_pod_container_resource_limits{namespace="diagnostics-example",resource="cpu",unit="core"} > 0
)) > 0.8
```
```promql
(max by (namespace,pod,container) (container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"})
/ on (namespace,pod,container)
max by (namespace,pod,container) (kube_pod_container_resource_limits{namespace="diagnostics-example",resource="memory",unit="byte"} > 0)) > 0.8
```

</details>

### 5. Managed EKS에서 고객의 node 간 network 진단에 통상 사용하는 도구가 아닌 것은?

A. 인가된 tcpdump capture
B. 인가된 저장 capture용 Wireshark
C. Workload의 범위 지정 curl/DNS 검사
D. AWS managed etcd endpoint에 etcdctl

<details>
<summary>정답 보기</summary>

**정답: D. AWS managed etcd endpoint에 etcdctl**

고객에게 managed-etcd 직접 endpoint가 제공되지 않습니다. Self-managed etcd에서 etcdctl이 network 진단에 전혀 쓸모없다는 뜻은 아닙니다. Capture에는 권한·host 문맥·범위 제한·비공개 취급이 필요하며 새 debug Pod는 장애 workload와 policy/DNS 경로가 다를 수 있습니다. Throughput counter는 latency 측정이 아닙니다.

```bash
# Deliberate bounded request from an owned workload with curl installed.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${HEALTH_URL:?Set a reviewed safe health URL}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP status: %{http_code}\n' "$HEALTH_URL"
```

</details>

### 6. 모든 threshold를 낮추는 대신 감지 지연을 줄이는 접근은?

A. 수동 관찰만 증가
B. 모든 metric에 가능한 최저 threshold
C. 적절한 측정 기반 alert·수집 범위 확인·escalation
D. Retention 연장만

<details>
<summary>정답 보기</summary>

**정답: C. 적절한 측정 기반 alert·수집 범위 확인·escalation**

실제 SLO·장애 양상에 맞추며 낮은 threshold는 alert fatigue를 만들 수 있습니다. 아래 HTTP counter·status label은 앱 instrumentation이 필요하고 요청 분모 0·누락이 성공을 증명하지 않습니다. 모든 restart 대신 waiting reason으로 CrashLoopBackOff를 확인합니다. Prometheus가 rule·namespace를 선택해야 하며 알림 수신은 별도 확인입니다. 여기서 MTTD를 측정하지 않았습니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: reviewed-quiz-alerts
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: reviewed-quiz-alerts
    rules:
    - alert: HighErrorRate
      expr: "(\n  sum(rate(http_requests_total{namespace=\"diagnostics-example\",job=\"\
        owned-app\",status=~\"5..\"}[5m]))\n  / sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m]))\n) > 0.05\nand on() (sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m])) > 0)"
      for: 2m
      labels:
        severity: critical
    - alert: PodCrashLooping
      expr: max by (namespace,pod,container) (kube_pod_container_status_waiting_reason{namespace="diagnostics-example",reason="CrashLoopBackOff"}
        == 1)
      for: 5m
      labels:
        severity: warning
```

</details>

### 7. Node에 진단 Pod를 생성하는 명령 형식은?

A. `kubectl debug node/<node-name> --image=<reviewed-image>`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>정답 보기</summary>

**정답: A. `kubectl debug node/<node-name> --image=<reviewed-image>`**

검증한 general profile은 /host와 host namespace를 사용하지만 privileged는 false입니다. 명시적 sysadmin은 더 넓은 권한을 주며 chroot/nsenter/도구/SELinux 동작은 platform·권한에 따릅니다. Pod 생성은 변경 작업이고 kubelet/runtime 장애 시 시작되지 않을 수 있습니다. 생성한 name·UID를 기록하고 검토한 정리 절차를 사용합니다.

```bash
# MUTATION: creates a node diagnostic Pod; general is not automatically privileged.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${NODE_NAME:?}"; : "${NODE_DEBUG_IMAGE:?Reviewed image}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "node/$NODE_NAME" \
  --image="$NODE_DEBUG_IMAGE" --profile=general --attach=false -- true
```

</details>

### 8. 분산 추적에서 Span이 나타내는 것은?

A. 전체 요청 총 시간만
B. 시간·관련 metadata를 가진 작업 단위 하나
C. Network latency만
D. Log timestamp

<details>
<summary>정답 보기</summary>

**정답: B. 시간·관련 metadata를 가진 작업 단위 하나**

Span은 HTTP 호출·DB 작업 등의 단위를 표현합니다. Trace ID로 연결되고 parent/child·link로 관련 작업을 표현하며 실제 가시성은 propagation·sampling에 달려 있습니다. Baggage는 전달하는 context이며 자동 span attribute가 아니고 secret을 넣지 않습니다. 아래 JSON은 사람이 읽는 예시이며 OTLP wire payload·실측 요청이 아닙니다. Collector는 본문의 현재 v1beta1 object config·지원 backend/OTLP 경로를 사용하며 이전 jaeger exporter/14250 절차는 현재 안내가 아닙니다.

```json
{
  "exampleOnly": true,
  "trace_id": "0123456789abcdef0123456789abcdef",
  "span_id": "0123456789abcdef",
  "parent_span_id": "fedcba9876543210",
  "name": "GET /api/products",
  "kind": "SERVER",
  "duration_ms": 85
}
```

</details>

### 9. Deployment 기반 CoreDNS의 DNS 오류를 조사할 때 유용한 근거는?

A. 범위를 지정한 CoreDNS Pod log/status와 workload resolver 확인
B. Describe service kubernetes만
C. AWS cluster metadata만
D. 이전 Endpoints 목록만

<details>
<summary>정답 보기</summary>

**정답: A. 범위를 지정한 CoreDNS Pod log/status와 workload resolver 확인**

기본 설정이 모든 DNS query를 기록하지는 않습니다. Resolver 설정·Pod/Service health·upstream 오류를 대조합니다. 순수 Auto Mode는 node-system DNS이며 혼합 cluster는 non-Auto용 Deployment를 유지합니다. 오래된 image의 무관한 default-namespace Pod 대신 도구가 있는 관련 Pod/container에서 확인합니다. Nslookup debug flag는 구현마다 다릅니다.

```bash
# Deployment-based CoreDNS only; use the Auto Mode path when applicable.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns --since=15m --tail=100
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- nslookup kubernetes.default.svc.cluster.local.
```

</details>

### 10. Resource-metrics API의 최근 Pod resource sample을 표시하는 명령은?

A. kubectl describe pod
B. kubectl top pods
C. kubectl get pods -o wide
D. kubectl logs

<details>
<summary>정답 보기</summary>

**정답: B. kubectl top pods**

Kubectl top은 보통 Metrics Server 같은 정상 metrics.k8s.io provider가 필요합니다. 순간 측정·이력이 아닌 최근 수집 CPU/memory sample이며 metric 부재가 사용량 0은 아닙니다. Requests/limits는 별도로 비교하고 이력은 monitoring backend를 사용합니다.

```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --sort-by=memory
kubectl --context "$KUBE_CONTEXT" top nodes
```

</details>

## 단답형 문제

### 1. 활성화한 EKS 컨트롤 플레인 로그의 CloudWatch Logs 그룹 이름 패턴은?

<details>
<summary>정답 보기</summary>

**정답:** `/aws/eks/<cluster-name>/cluster`. 해당 클러스터에서 로그 종류를 활성화해야 하며 이전 이벤트가 소급 생성되지는 않습니다. 계정·Region·그룹·시간 범위를 확인하고 아래 Logs Insights QL을 각각 실행합니다. 감사 로그의 username은 기록된 주체로, IAM role의 짧은 이름과 같다고 가정하지 않습니다.

```sql
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @logStream not like /kube-apiserver-audit/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 50
```

```sql
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter user.username = "REPLACE_WITH_EXACT_AUDIT_USERNAME"
| sort @timestamp desc
| limit 100
```

</details>

### 2. 현재 Kubernetes에서 이전 EphemeralContainers feature gate를 설정해야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. `EphemeralContainers`는 이전 feature gate 이름이며 1.23에서 beta, 1.25에서 stable이 되었습니다. 현재 버전에서는 `pods/ephemeralcontainers` RBAC·admission policy·image 접근·runtime 지원을 확인합니다. 추가는 Pod 변경이며 추가한 항목은 이후 수정하거나 제거할 수 없습니다. `--target`의 프로세스 가시성은 runtime 지원에 달려 있습니다. 생성은 본문의 검토된 절차를 따르고 아래 명령은 metadata만 조회합니다.

```bash
# Read-only inventory; adding an ephemeral container is a separate mutation.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq '{
    uid:.metadata.uid,
    ephemeralContainers:[.spec.ephemeralContainers[]? | {name,image,targetContainerName}],
    ephemeralStatuses:.status.ephemeralContainerStatuses
  }'
```

</details>

### 3. PromQL의 rate()와 irate()는 어떻게 다른가요?

<details>
<summary>정답 보기</summary>

`rate()`는 선택 범위의 counter 증가를 초당 값으로 추정하고 reset을 보정하며 범위 경계까지 외삽합니다. `irate()`는 범위 안의 마지막 두 sample로 계산하고 reset을 보정합니다. 둘 다 충분한 sample이 필요하며 수집되지 않은 spike를 볼 수는 없습니다. Series별 reset을 식별하도록 집계 전에 함수를 적용합니다. 알림에는 보통 `rate()`를 쓰며 `irate()`는 변동이 큰 counter 관찰에 유용하지만 더 나은 장애 감지를 보장하지 않습니다. Gauge에 일반적으로 적용하는 미분 함수가 아닙니다. 앞의 두 예시는 앱 계측 counter이고 마지막 결과는 백분율이 아닌 CPU core입니다. 단일 클러스터와 본문의 label·scrape 전제를 따릅니다.

```promql
sum by (namespace,service) (
  rate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```

```promql
sum by (namespace,service) (
  irate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```

```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

</details>

### 4. kubectl debug node는 호스트 파일시스템을 어디에 마운트하며 어떤 권한을 주나요?

<details>
<summary>정답 보기</summary>

**정답:** `/host`. `general` profile은 자동으로 privileged가 되지 않습니다. Host mount만으로 `chroot`·`systemctl`·보호 파일 읽기가 보장되지는 않습니다. Image의 도구와 admission·capability·SELinux·OS·노드 상태를 확인해야 합니다. 명시적으로 privileged인 `sysadmin`은 별도로 인가된 진단 절차가 필요합니다. Auto Mode도 문서화된 node debug를 지원하지만 직접 SSH나 일반 host 경로를 보편적으로 가정하지 않습니다. 생성·정리는 객관식 7번과 본문을 따르며 kubeconfig·credential 파일을 출력하지 않습니다.


</details>

### 5. 복구 시간을 중복 계산하지 않고 어떻게 나눌 수 있나요?

<details>
<summary>정답 보기</summary>

먼저 “MTTR”의 정의를 정합니다. 조직에 따라 감지 시점 또는 영향 시작 시점부터 계산하며 resolve·repair·recover의 뜻도 다릅니다. 여기서는 `t0 = 서비스 영향 시작`, `t1 = 감지`, `t2 = 조치 가능한 진단`, `t3 = 서비스 복구`로 정의합니다. 겹치지 않는 구간은 감지 `t1−t0`, 조사 `t2−t1`, 복구 `t3−t2`이며 합은 `t3−t0`입니다. 같은 incident 집합에 같은 정의로 평균을 내면 합 관계가 유지됩니다. 45분짜리 사건 하나는 소요 시간이지 검증된 평균이 아닙니다. 최종 원인 규명과 후속 작업은 복구 뒤에 올 수도 있으므로 모든 사건에 이 순서를 강제하지 않습니다. 수집 범위·런북·검증된 복구 절차를 개선하고 실제 효과를 측정합니다.


</details>

## 실습 문제

### 1. Production 컨테이너 중 최근 5분간 추정 재시작 증가가 2 이상인 항목을 찾으세요.

<details>
<summary>정답 보기</summary>

단일 클러스터와 `namespace`·`pod`·`uid`·`container` label을 제공하는 kube-state-metrics를 전제로 합니다. `increase()`는 counter reset을 보정하고 외삽하므로 소수가 나올 수 있으며 완전한 이벤트 장부가 아닙니다. `max`는 같은 값을 노출하는 exporter replica의 단순 합산을 피하지만 범용 HA 중복 제거는 아니므로 scrape 상태와 backend deduplication을 확인합니다. Pod UID를 유지해 같은 이름의 교체 Pod를 구분합니다. 변형은 생애 누적 횟수 >5, 최근 1시간 컨테이너 증가를 합친 상위 **Pod** 10개, 그래프용 초당 재시작률입니다. Series 누락은 재시작 0회가 아닙니다.

```promql
max by (namespace,pod,uid,container) (
  increase(kube_pod_container_status_restarts_total{namespace="production"}[5m])
) >= 2
```

```promql
max by (namespace,pod,uid,container) (
  kube_pod_container_status_restarts_total{namespace="production"}
) > 5
```

```promql
topk(10,
  sum by (namespace,pod,uid) (
    max by (namespace,pod,uid,container) (
      increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
    )
  )
)
```

```promql
max by (namespace,pod,uid,container) (
  rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])
)
```

</details>

### 2. Workload를 변경하기 전에 CrashLoopBackOff 컨테이너의 근거를 범위를 지정해 수집하세요.

<details>
<summary>정답 보기</summary>

`CrashLoopBackOff`는 컨테이너 waiting reason이며 Pod phase는 `Running`일 수 있습니다. 실제 context·namespace·Pod·실패 컨테이너를 선택하고 로그 수집 전에 현재 UID를 확인합니다. 이름 기반 로그 조회와 UID 확인은 원자적이지 않습니다. 아래 제한된 조회부터 시작해 exit code/reason·앱 오류·설정 참조·노드 압박·의존성 실패를 조사합니다. Startup/liveness probe 실패는 재시작을 일으킬 수 있지만 readiness 실패만으로 재시작하지는 않습니다. Secret·설정 누락은 crash loop 대신 생성 실패를 만들 수도 있습니다. 전체 환경변수·Secret 값·설정 파일을 출력하지 않습니다.

```bash
# Read-only, bounded evidence for one owned Pod and container.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE")
pod_state=$("${k[@]}" get pod "$POD_NAME" -o json | jq '{
  uid:.metadata.uid, phase:.status.phase, conditions:.status.conditions,
  containers:[.status.containerStatuses[]? | {name,ready,restartCount,state,lastState}],
  initContainers:[.status.initContainerStatuses[]? | {name,ready,restartCount,state,lastState}]
}')
printf '%s\n' "$pod_state"
pod_uid=$(jq -er '.uid' <<<"$pod_state")
"${k[@]}" get events --field-selector "involvedObject.uid=$pod_uid" \
  --sort-by='.metadata.creationTimestamp'
# These logs can contain sensitive application data; keep the terminal/evidence private.
# A missing previous instance/log is an evidence gap, not an empty successful result.
if ! "${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" --previous \
  --tail=100 --limit-bytes=65536 --timestamps; then
  printf '%s\n' 'Previous container log unavailable; retain this limitation.' >&2
fi
"${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --since=15m --tail=100 --limit-bytes=65536 --timestamps
```

재현이 필요하면 복사본의 identity·Secret 참조·volume·다른 컨테이너·외부 부작용을 검토한 뒤 객관식 2번과 본문 절차를 사용합니다. Image/command 하나 교체와 init 비활성화만으로 자원이 격리되지 않습니다. 적절한 환경의 정제된 재현을 우선하고 새 name·UID를 기록해 정리를 별도 검토합니다. Sleep 중인 debug 컨테이너는 앱 복구의 증거가 아닙니다.

</details>

### 3. 최근 1시간 EKS 감사 로그의 403 이벤트를 조회하고 완료된 결과를 확인하세요.

<details>
<summary>정답 보기</summary>

감사 로그가 이미 활성화되어 있어야 합니다. 소유 계정·Region과 `/aws/eks/<cluster-name>/cluster`를 선택하고 콘솔에서는 최근 1시간 범위를 지정합니다. 각 블록은 별도 Logs Insights QL입니다. JSON key 순서를 가정해 parse하지 말고 추출된 필드를 사용합니다. 집계는 고유 요청이 아닌 감사 이벤트 수이며 여러 audit stage가 같은 audit ID를 기록할 수 있습니다. 403은 인가 거부이지만 어느 IAM/RBAC policy 때문인지 단독으로 증명하지는 않습니다. CLI 예시는 AWS CLI·Bash·jq·Python이 필요하고 최대 100개 결과를 비공개 저장합니다. 실행 중 결과가 있어도 `Complete`만 최종 결과입니다. Polling 종료가 서비스의 query를 취소하지는 않습니다.

```sql
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

```sql
filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| stats count(*) as deniedEvents by user.username, verb, objectRef.resource
| sort deniedEvents desc
| limit 100
```

```bash
# Read-only query with possible CloudWatch scan charges; no log configuration changes.
set -euo pipefail
umask 077
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
evidence_dir=$(mktemp -d "$PWD/eks-audit403.XXXXXX")
printf 'Private evidence directory: %s\n' "$evidence_dir"
read -r start_epoch end_epoch < <(python3 - <<'PY'
import time
end = int(time.time())
print(end - 3600, end)
PY
)
query_string='fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100'
query_id=$(aws logs start-query --region "$AWS_REGION" --no-cli-pager \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$start_epoch" --end-time "$end_epoch" \
  --query-string "$query_string" --query queryId --output text)
if [[ ! "$query_id" =~ ^[0-9a-fA-F-]{36}$ ]]; then
  printf '%s\n' 'No valid query ID returned.' >&2
  exit 1
fi
printf '%s\n' "$query_id" > "$evidence_dir/query-id.txt"
for attempt in {1..15}; do
  aws logs get-query-results --region "$AWS_REGION" --no-cli-pager \
    --query-id "$query_id" --output json > "$evidence_dir/result.json"
  status=$(jq -er '.status' "$evidence_dir/result.json")
  case "$status" in
    Complete)
      printf 'Query complete; inspect private file %s/result.json\n' "$evidence_dir"
      exit 0
      ;;
    Scheduled|Running) sleep 2 ;;
    *)
      printf 'Query ended without complete results: %s\n' "$status" >&2
      exit 1
      ;;
  esac
done
printf 'Polling limit reached; query %s may still run. Partial results are not final.\n' "$query_id" >&2
exit 2
```

</details>

## 심화 문제

### 1. 간헐적인 API 지연을 조사하는 추적·메트릭·로그 전략을 수립하세요.

<details>
<summary>정답 보기</summary>

**1. 측정 전제를 정합니다.** 단일 클러스터의 `diagnostics-example` namespace에 계측한 `api-gateway`, 초 단위 classic histogram, 제한된 `endpoint` label과 `le="0.5"` bucket이 있다고 가정합니다. Bucket과 count의 series 범위가 같은지 확인합니다. Kubernetes가 앱 메트릭을 자동 제공하는 것은 아닙니다. 영향받는 route·요청량·시간 범위를 비교합니다. 아래는 p99, 히트맵용 누적 bucket rate, 0.5초 초과 비율입니다. Rate를 빼기만 하면 비율이 아닌 초당 요청 수이며 요청이 없을 때 비율은 정의되지 않습니다.

```promql
histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (
  rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[5m])
))
```

```promql
sum by (le,namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[1m]))
```

```promql
(
  (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) - sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway",le="0.5"}[5m])))
  / sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m]))
)
and on (namespace,service,endpoint) (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) > 0)
```

**2. Trace를 조사합니다.** Backend UI에서 `api-gateway`, 영향 시간, 2초 초과 duration, `GET /api/products` 같은 관련 operation을 선택합니다. 실제 backend attribute 이름으로 오류 span과 downstream 호출을 확인합니다. 이는 UI 검색 조건이지 Jaeger에 import할 YAML이 아닙니다. Propagation·sampling을 먼저 확인하며 span 부재가 호출 부재의 증거는 아닙니다. 병렬 span 시간을 단순 합산해 전체 요청 시간으로 보지 않습니다.

**3. 로그를 대조합니다.** 구조화 로그에 `trace_id`가 있다면 실제 trace ID로 placeholder를 바꾸고 소유한 앱 로그 그룹·시간 범위에서 아래 Logs Insights QL을 따로 실행합니다. 앱 계측이 필요하며 token·request body·전달된 secret을 기록하지 않습니다. 상관관계는 가설을 좁힐 뿐 인과관계의 증명은 아닙니다.

```sql
fields @timestamp, @message
| filter trace_id = "REPLACE_WITH_ACTUAL_TRACE_ID"
| sort @timestamp asc
| limit 100
```

**4. 인프라 근거를 비교합니다.** 아래 결과는 순서대로 초당 CPU throttled seconds, 초당 수신 bytes, 초당 JVM GC pause seconds입니다. Network throughput은 **network latency가 아닙니다**. 지연은 범위를 맞춘 client/server span이나 인가된 제한적 RTT 검사로 확인합니다. GC pause rate도 개별 요청 지연은 아닙니다. Metric 이름·label은 exporter와 runtime에 따라 다르며 무관한 클러스터 합계 대신 실제 node·Pod·시간을 맞춥니다.

```promql
rate(container_cpu_cfs_throttled_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

```promql
rate(container_network_receive_bytes_total{namespace="diagnostics-example",pod!=""}[5m])
```

```promql
rate(jvm_gc_pause_seconds_sum{namespace="diagnostics-example",service="api-gateway"}[5m])
```

**5. 대시보드를 설계합니다.** 아래는 panel 설계이며 Grafana import 파일이 아닙니다. 설치 버전의 editor/export 형식과 실제 datasource UID를 사용합니다.

| Panel | 측정값 |
|---|---|
| p50/p95/p99 지연 | 0.50·0.95·0.99를 각각 사용하는 histogram-quantile query 3개 |
| 상태별 요청률 | 실제 status label로 묶은 앱 request counter의 rate |
| 히트맵 | `le`와 route 범위를 유지한 classic histogram bucket rate |
| Downstream 지연 | 해당 service의 histogram·label 전제 |
| Pod resource | CPU counter rate는 core, memory working-set gauge는 bytes |

```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

```promql
container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"}
```

**6. 비교 알림을 평가합니다.** Prometheus가 이 rule·namespace를 선택하도록 release label을 바꿉니다. 50% threshold와 5분 지속 조건은 요청량·SLO에 맞춰 검증할 예시입니다. 긴 범위의 p99는 **1시간 평균 latency가 아니며** 최근 5분도 포함합니다. 예측 모델이 아닌 비교 규칙입니다. 양수 기준값이 필요하고 데이터 누락·NaN은 정상의 증거가 아닙니다. 수집 상태·낮은 요청량·알림 전달을 별도로 확인합니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: latency-comparison-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: latency-comparison-example
    rules:
    - record: diagnostics:http_duration_seconds:p99_5m
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[5m])\n))"
    - record: diagnostics:http_duration_seconds:p99_1h
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[1h])\n))"
    - alert: LatencyComparedWithLongerWindow
      expr: "(\n  diagnostics:http_duration_seconds:p99_5m\n  / diagnostics:http_duration_seconds:p99_1h\
        \ > 1.5\n)\nand on (namespace,service,endpoint) (diagnostics:http_duration_seconds:p99_1h\
        \ > 0)"
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Five-minute p99 exceeds one-hour p99 by over 50%; investigate.
```

Endpoint 특성·downstream 호출·CPU throttling·GC·network 경로·요청량 변화는 각각 근거가 필요한 가설로 구분합니다. 여기서 지연 개선 효과나 benchmark를 측정하지 않았습니다.

</details>

### 2. 간헐적인 NotReady 노드에 대해 근거 기반 RCA 절차를 수립하세요.

<details>
<summary>정답 보기</summary>

**1. 대상과 시간을 확인합니다.** `Ready=False`와 heartbeat 부재/`Unknown`을 구분합니다. Node UID·provider ID·OS/runtime 버전·condition 전환 시각·lease 갱신을 기록합니다. Event 보존 기간은 제한되므로 빈 목록이 과거 장애 부재를 증명하지 않습니다. 멈춘 node에서는 node debug 자체가 시작되지 않을 수 있습니다.

```bash
# Read-only scoped node evidence; confirm account/cluster/Region first.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s)
node_state=$("${k[@]}" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,
  nodeInfo:.status.nodeInfo,conditions:.status.conditions
}')
printf '%s\n' "$node_state"
node_uid=$(jq -er '.uid' <<<"$node_state")
"${k[@]}" get events --all-namespaces \
  --field-selector "involvedObject.uid=$node_uid" --sort-by='.metadata.creationTimestamp'
"${k[@]}" -n kube-node-lease get lease "$NODE_NAME" \
  -o jsonpath='{.spec.renewTime}{"\n"}'
```

해당 EC2 instance의 `Maximum=1`은 구간 안에 실패한 status-check sample이 있다는 뜻입니다. `Sum`은 장애 지속 시간이 아니고 datapoint 누락은 성공이 아닙니다. Fargate·Hybrid Nodes는 해당 인프라의 근거를 사용합니다.

```bash
# EC2-backed nodes only: resolve the actual instance from providerID, not a guessed name.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Verified EC2 instance ID}"
read -r start_time end_time < <(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
end = datetime.now(timezone.utc)
print((end-timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
      end.strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" --no-cli-pager \
  --namespace AWS/EC2 --metric-name StatusCheckFailed \
  --dimensions "Name=InstanceId,Value=$INSTANCE_ID" \
  --start-time "$start_time" --end-time "$end_time" --period 300 \
  --statistics Maximum --query 'sort_by(Datapoints,&Timestamp)'
```

**2. 적용 가능한 host 근거를 수집합니다.** 인가된 host 접근·NodeDiagnostic·본문의 문서화된 Auto Mode 진단 경로를 사용합니다. `general`을 privileged chroot 대용으로 가정하지 않습니다. 아래 조회는 호환되는 systemd Linux host용이며 모든 debug image나 Bottlerocket·Auto Mode 경로에 적용되지 않습니다. Log는 민감할 수 있으므로 별도 검토한 복구 전에 비공개 수집합니다.

```bash
# Only inside an already authorized, compatible systemd Linux host context.
# These are bounded reads, not instructions to restart or prune the node.
journalctl -u kubelet --since '24 hours ago' -n 200 --no-pager
journalctl -u containerd --since '24 hours ago' -n 200 --no-pager
dmesg | tail -n 100
free -h
vmstat 1 5
cat /proc/pressure/memory /proc/pressure/cpu
```

**3. 관련 network 경로를 확인합니다.** 아래 요청은 선택한 kubeconfig의 CA로 TLS를 검증하며 `/readyz` 인가가 필요합니다. 장애 node가 아닌 호출자의 경로를 검사합니다. 401/403은 HTTP 응답을 받았다는 뜻이지 readiness의 증거는 아닙니다. DNS·timeout·인증서 오류를 구분하고 `curl -k`로 신뢰 오류를 숨기지 않습니다.

```bash
# Uses the selected kubeconfig CA and authentication; do not disable TLS verification.
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=10s get --raw='/readyz'
```

표준 VPC CNI에서만 실제 aws-node Pod와 해당 instance의 ENI를 조회합니다. Auto Mode는 관리형 networking 경로를 사용하므로 DaemonSet 부재를 장애로 단정하지 않습니다.

```bash
# Standard VPC CNI on an EC2 node; choose the aws-node Pod on the affected node.
: "${KUBE_CONTEXT:?}"; : "${AWS_NODE_POD:?}"; : "${AWS_REGION:?}"; : "${INSTANCE_ID:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  logs "$AWS_NODE_POD" -c aws-node --since=15m --tail=100 --limit-bytes=65536
aws ec2 describe-network-interfaces --region "$AWS_REGION" --no-cli-pager \
  --filters "Name=attachment.instance-id,Values=$INSTANCE_ID" \
  --query 'NetworkInterfaces[].{ENI:NetworkInterfaceId,Subnet:SubnetId,Status:Status,IPv4Prefixes:Ipv4Prefixes,PrivateIPs:PrivateIpAddresses[].PrivateIpAddress}'
```

**4. Resource 신호를 해석합니다.** 아래 단일 클러스터 query는 memory 여유·root filesystem 용량·system thread limit 사용·실제 kubelet pressure condition을 보여 줍니다. Node Exporter·kube-state-metrics series와 올바른 host mount·label이 필요합니다. Node Exporter의 `processes` collector는 기본 비활성화이며 `node_processes_max_threads`는 Linux `threads-max`입니다. 이 비율은 kubelet의 PIDPressure 판단이나 컨테이너 `pids.max`가 아닙니다. Filesystem·inode·imagefs·cgroup 제한과 scrape 실패를 따로 확인합니다. 아래 threshold는 기본값이 아닌 예시입니다.

```promql
(1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0)) * 100 > 90
```

```promql
(1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0)) * 100 > 85
```

```promql
node_processes_threads / (node_processes_max_threads > 0) * 100 > 80
```

```promql
max by (node) (kube_node_status_condition{condition=~"MemoryPressure|DiskPressure|PIDPressure",status="true"}) == 1
```

**5. 가설을 검증합니다.** Kernel OOM 기록의 종료 프로세스와 workload memory·limit를 대조하고 disk·inode 고갈은 실제 filesystem과 연결합니다. Kubelet/runtime log·node에서 API까지의 연결·CNI/IP 근거·EC2 health를 같은 시간대로 비교합니다. 높은 memory 사용이나 probe 실패만으로 memory leak 또는 인프라 장애를 확정하지 않습니다.

**6. 실제 compute 유형에 맞게 재발을 방지합니다.** Auto Mode는 node monitoring·repair를 포함합니다. Managed node group은 repair 설정을 확인해야 합니다. 직접 운영하는 Karpenter의 repair는 호환 release·`NodeRepair=true`·해당 condition/repair policy가 필요하며 진단 agent가 추가 condition을 제공합니다. 현재 Karpenter 정책은 `Ready=False/Unknown`에 30분을 허용하고 NodePool의 20% 초과가 비정상이면 복구를 중단하며 일반적인 graceful drain 대신 강제 종료할 수 있습니다. 자발적 disruption budget·PDB가 모든 repair에 적용된다고 보장하지 않습니다. EKS repair는 기본적으로 `MemoryPressure`·`DiskPressure`·`PIDPressure`를 복구하지 않으므로 workload 압박을 해결합니다. 이 EKS monitoring·repair 기능은 Linux 전용이며 Fargate에는 monitoring agent를 설치하지 않습니다. 불완전한 privileged Node Problem Detector DaemonSet을 배포하거나 기존 agent를 중복 설치하지 말고 본문과 현재 provider 설정을 따릅니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-health-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: node-health-example
    rules:
    - alert: NodeHighMemoryUse
      expr: (1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0))
        * 100 > 90
      for: 5m
      labels:
        severity: warning
    - alert: NodeRootFilesystemLowSpace
      expr: (1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}
        / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0))
        * 100 > 85
      for: 5m
      labels:
        severity: warning
    - alert: NodeNotReady
      expr: max by (node) (kube_node_status_condition{condition="Ready",status="true"})
        == 0
      for: 2m
      labels:
        severity: critical
```

Prometheus가 이 rule을 선택해야 하며 condition/exporter series 누락에는 별도 수집·inventory 알림이 필요합니다. 용량 알림과 kubelet pressure condition은 측정 대상이 달라 이름도 구분했습니다.

설정을 소유한 Linux kubelet이라면 아래는 **기존 설정에 검토 후 병합하는 조각**입니다. 완전한 설정이나 EKS node 파일 덮어쓰기 명령이 아닙니다. OS·provisioner가 지원하는 bootstrap 경로를 사용합니다. `mergeDefaultEvictionSettings`는 생략된 hard default를 유지하며, 이를 사용하지 않은 일부 값 변경은 나머지 threshold를 0으로 만들 수 있습니다. Soft threshold에는 대응하는 grace period가 필요하고 `evictionMaxPodGracePeriod`는 종료 유예 시간을 제한합니다. 값은 workload·용량 검증이 필요한 예시이며 Auto Mode 설정 지시가 아닙니다.

```json
{
  "mergeDefaultEvictionSettings": true,
  "evictionHard": {
    "memory.available": "500Mi",
    "nodefs.available": "10%",
    "imagefs.available": "15%"
  },
  "evictionSoft": {
    "memory.available": "1Gi",
    "nodefs.available": "15%"
  },
  "evictionSoftGracePeriod": {
    "memory.available": "1m",
    "nodefs.available": "1m"
  },
  "evictionMaxPodGracePeriod": 60
}
```

**기존 RCA 템플릿 — 검증되지 않은 예시이며 실제 사고 보고서가 아닙니다.** 원래 날짜·수량과 언어별 timezone을 보존합니다. PST·KST 예시가 같은 순간을 뜻한다고 주장하지 않습니다. Memory leak·실제 조치·완료 상태를 입증할 원본 근거는 없습니다. 운영에 사용하기 전에 근거로 빈칸을 채워야 합니다.

```markdown
## 인시던트 요약 (예시)
- 시작: 2024-01-15 14:30 KST
- 영향 예시: 노드 3대, Pod 45개
- 복구 예시: 2024-01-15 15:15 KST (소요 45분이며 측정된 평균 아님)

## 예시 타임라인 — 각 항목에 근거 필요
- 14:30 — NodeNotReady 알림
- 14:35 — 조사 시작
- 14:50 — 가설: memory pressure가 kubelet 종료를 유발; kernel·process 근거로 확인
- 15:00 — drain/restart 제안; 실제 인가·영향·data 보호 확인을 기록
- 15:15 — 복구 시점 제안; workload·SLO 검증 근거 필요

## 원인 가설
Memory leak이 node memory 고갈을 일으킬 수 있으나 이 템플릿으로 입증되지 않음.

## 후속 제안 — 완료를 주장하지 않음
1. 앱 memory 동작과 적절한 requests/limits 검증.
2. 알림 threshold 90%→80% 변경의 noise·용량 영향 평가.
3. Node Problem Detector를 고려하기 전에 기존 node monitoring 확인.
```

</details>

**실습의 공식 참고 자료:**

- [Prometheus functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Karpenter disruption and node repair](https://karpenter.sh/docs/concepts/disruption/)
- [EKS node monitoring and repair](https://docs.aws.amazon.com/eks/latest/userguide/node-health.html)
- [Kubelet node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Node Exporter collectors](https://github.com/prometheus/node_exporter#disabled-by-default)
