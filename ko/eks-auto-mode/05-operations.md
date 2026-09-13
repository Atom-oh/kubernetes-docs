# 운영 및 관리

> **지원 버전**: EKS Auto Mode GA; 예제 기준 EKS 1.36
> **마지막 업데이트**: 2026년 9월 12일

Day-2 운영에서는 원하는 용량, 노드 수명 주기, 애플리케이션 가용성과 실제 수집되는 신호를 구분해야 합니다. 아래는 통제된 실습 구성이지 검증된 프로덕션 runbook이 아닙니다. 이번 감사에서 클라우드 리소스 변경이나 실제 노드·Pod 실행은 하지 않았습니다.

NodePool은 릴리스된 Karpenter 1.14.1 구조 스키마로 확인했습니다. 워크로드는 Kubernetes 1.36.2 구조 및 Restricted Pod Security 정책 검사를 통과했고 nginx 이미지 tag/index digest와 문서화된 non-root 구성을 확인했습니다. 실제 이미지 pull, IAM, 네트워크와 애플리케이션 동작은 해당 환경에서 검증해야 합니다.

## 운영 컨텍스트 확인

임시 자격 증명과 대상 kubeconfig를 사용합니다. 아래 읽기 전용 검사는 계정과 직접 API 엔드포인트를 비교합니다. 의도적으로 proxy를 사용하는 kubeconfig는 불일치를 우회하지 말고 별도로 검토하세요.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${AWS_REGION:?Set the cluster region}"
: "${CLUSTER_NAME:?Set the intended cluster name}"
: "${KUBECONFIG:?Set the reviewed kubeconfig path}"
export KUBE_CONTEXT="${KUBE_CONTEXT:-$CLUSTER_NAME}"
check_account() {
  local account
  account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$account" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch; stop.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-ops.XXXXXXXX")
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,endpoint:endpoint}' --output json > "$WORK_DIR/cluster.json"
endpoint=$(kubectl --context "$KUBE_CONTEXT" config view --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$WORK_DIR/cluster.json" >/dev/null
printf 'Private diagnostic directory: %s\n' "$WORK_DIR"
```

Manifest는 검토된 `default` NodeClass를 가정합니다. 필요한 예제만 선택하고 리소스 이름·네트워크 ID와 용량·비용을 검토하세요. 실습 풀의 `ops-lab` taint와 워크로드의 toleration/pool selector는 배치 제어이며 테넌트 보안 경계가 아닙니다.

## Budget은 덮어쓰지 않고 함께 평가

적용되는 모든 NodePool budget 중 가장 작은 중단 허용량을 사용합니다. 항상 적용되는 `10%`가 있으면 예약된 `30%`를 더해도 더 많이 허용되지 않습니다. 백분율은 올림 계산하며 삭제 중·NotReady 노드가 남은 허용량을 줄입니다.

다음 달력은 30% 상한, 평일 10% 상한과 업무 시간 1개 상한을 명시합니다. Karpenter schedule은 UTC입니다.

| 항목 | UTC schedule | 의도한 구간 |
|------|--------------|-------------|
| 30% | 항상 | 바깥 상한 |
| 10% | 일–목 15:00, 24시간 | 서울 월–금 달력 날짜 |
| 1개 | 월–금 00:00, 9시간 | 서울 업무 시간 09:00–18:00 |
| 0개 | 매월 1일 00:00, 24시간 | 명시적인 **UTC** 월간 freeze |

그 외 모두 정상인 노드가 20개라면 새 자발적 중단을 주말에는 6개, 평일 업무 외 시간에는 2개, 업무 시간에는 1개, freeze에는 0개 허용합니다. 이는 예시 정책이며 보편적인 프로덕션 권장값이 아닙니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-calendar
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 30%
    - nodes: 10%
      schedule: 0 15 * * sun-thu
      duration: 24h
    - nodes: '1'
      schedule: 0 0 * * mon-fri
      duration: 9h
    - nodes: '0'
      schedule: 0 0 1 * *
      duration: 24h
  limits:
    cpu: '100'
    memory: 400Gi
```

이전의 매시간 `9-18`/`9-21` cron과 반복된 48시간 주말 창은 설명된 구간을 넘어 중첩됐습니다. Schedule은 창의 시작점을 지정하며 긴 창을 매시간 다시 시작하라는 뜻이 아닙니다.

## 교체와 애플리케이션 가용성

1개 노드 budget은 해당 graceful 작업의 속도를 제한합니다. Expiration, interruption과 repair도 순차적으로 진행된다는 보장은 아닙니다. `expireAfter`는 최소 uptime 약속이 아니며 바꿔도 기존 NodeClaim 값을 덮어쓰지 않습니다. Auto Mode의 기본 expiry/grace와 최대 수명도 적용됩니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-rolling
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
    - nodes: '1'
  limits:
    cpu: '100'
    memory: 400Gi
```

빈 노드 consolidation 정책이 drift나 expiry를 비활성화하지는 않습니다. `do-not-disrupt`도 무기한 보존 보장이 아닙니다. Node와 Pod 제어 범위가 다르고 명시적·기본 termination grace period는 blocking Pod가 drift와 최종 종료에 미치는 영향을 바꿉니다. 유지보수에 사용하기 전에 [disruption 설명](https://karpenter.sh/v1.14/concepts/disruption/)을 확인하세요.

### PDB 예제

다음 namespace는 검토한 Kubernetes 버전의 Restricted 정책을 고정합니다. 이미지는 UID/GID 101로 실행하고 8080을 수신하며 PID·임시 파일에 `/tmp`를 사용합니다. Root filesystem을 읽기 전용으로 설정해도 이 writable emptyDir가 필요합니다. 이미지의 종료 신호는 SIGQUIT이며, port 80의 root nginx 이미지와 설정을 그대로 바꿔 쓸 수는 없습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ops-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: ops-lab
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: ops-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.4@sha256:cb92301e719d6639028de775fe8b28e15f58343aca5e5372001311958aafb300
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: ops-calendar
      tolerations:
      - key: ops-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
```

정상 desired replica가 5개일 때 `minAvailable: 3`은 다른 제약이 없다면 자발적 Pod 축출을 최대 2개 허용합니다. `maxUnavailable: 1`은 더 엄격한 별도 선택이며 같은 의미의 대체 표기가 아닙니다.

PDB는 healthy/Ready Pod를 기준으로 Eviction API를 제한하며 복제본을 만들거나 모든 장애·직접 삭제를 막지는 않습니다. 백분율은 올림합니다. 복제본 6개의 `minAvailable: "80%"`는 정상 5개를 요구하지만, 단일 복제본의 `maxUnavailable: "30%"`는 그 1개 축출을 허용할 수 있습니다.

상태 저장 시스템에는 실제 quorum과 readiness 의미를 적용하세요. 다수결 3-voter에는 정상 2개가 맞을 수 있으나 5-voter에는 3개가 필요합니다. `minAvailable: 2` 하나로 모든 stateful 워크로드를 다룰 수 없습니다. Singleton PDB는 의도적으로 자발적 drain을 막을 수 있어도 고가용성을 만들지는 않습니다.

## AZ 배치는 최소 용량이나 Failover 보장이 아님

동적 풀의 `limits.cpu`는 합산 상한이며 AZ별 최소값이 아닙니다. 예제는 가능한 AZ를 나열하지만 실제 적합성은 NodeClass 서브넷, 용량과 배치 제약이 결정합니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-multi-az
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
        - ap-northeast-2b
        - ap-northeast-2c
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
  namespace: ops-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: ha-app
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: ha-app
      containers:
      - name: app
        image: nginxinc/nginx-unprivileged:1.30.4@sha256:cb92301e719d6639028de775fe8b28e15f58343aca5e5372001311958aafb300
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: ops-multi-az
      tolerations:
      - key: ops-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      terminationGracePeriodSeconds: 60
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
```

복제본 6개만으로 3 AZ × 2 배치가 입증되지 않습니다. 예제는 적합한 domain을 최소 2개 요구합니다. 실제 서브넷 범위와 장애 정책을 검토한 뒤 변경하세요. 엄격한 `DoNotSchedule`은 AZ 장애 중 Pod를 Pending에 남길 수 있습니다.

노드마다 복제본 하나를 요구한다면 검토한 Pod template에 다음 affinity 조각을 추가할 수 있습니다. 복제본 9개라면 적합한 노드가 최소 9개 필요합니다. 대응하는 topology와 용량 없이 3-AZ 가용성이 보장되는 것은 아닙니다.

```yaml
podAntiAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
  - labelSelector:
      matchLabels:
        app: ha-app
    topologyKey: kubernetes.io/hostname
```

Active-active/standby에는 애플리케이션 상태, health check와 트래픽·failover 제어도 필요합니다. Auto Mode는 ARC zonal shift로 장애 AZ의 신규 용량을 피할 수 있으며 autoshift는 별도 구성이 필요합니다. AZ에 묶인 볼륨이나 엄격한 배치 제약을 이동 가능한 상태로 바꿔주지는 않습니다.

### 기존 Capacity Reservation 사용

풀 이름을 `reserved-capacity`로 정하고 On-Demand와 CPU limit을 설정해도 예약이 생성되지는 않습니다. 승인된 기존 예약은 커스텀 NodeClass에서 선택하고 `reserved` 용량을 허용합니다. 예시 reservation ID를 바꾸고 계정, AZ, 유형, 상태, 권한과 남은 예약 용량을 확인하세요.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: reserved-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  capacityReservationSelectorTerms:
  - id: cr-0123456789abcdef0
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reserved-capacity
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - reserved
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: reserved-nodeclass
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
```

이 manifest는 EC2 예약이나 고정된 노드 수를 만들지 않습니다. 예약은 사용하지 않아도 비용이 발생할 수 있습니다. Pod 수요와 무관한 desired node count에는 Auto Mode의 `spec.replicas` 정적 풀이 있으며 limits·weight·consolidation·scale 의미가 다릅니다. 정적 용량 참조를 확인하세요. Desired count도 실제 프로비저닝과 정상 용량 확보가 필요합니다.

## 실제 Publisher에 맞춘 모니터링

EKS control-plane 메트릭, 구성한 Container Insights, 자체 Prometheus exporter와 Auto Mode 컴포넌트 로그는 서로 다른 인터페이스입니다. 이전 `karpenter_*` 이름이 들어 있는 `Karpenter` CloudWatch namespace가 자동 생성된다고 가정하지 마세요.

관리형 compute/storage/load-balancer/IPAM 로그는 별도의 Vended Logs delivery로 구성합니다. 기본 control-plane logging이 모든 관리형 컴포넌트 로그를 켜는 스위치는 아닙니다. 시간 범위를 제한하고 IAM, 전송 대상과 요금을 확인합니다.

### 실제 메트릭 Metadata로 Dashboard 만들기

`AWS/EKS` control-plane namespace에서 대상 클러스터에 실제로 반환되는 메트릭을 먼저 확인합니다.

```bash
check_account
aws cloudwatch list-metrics --region "$AWS_REGION" --namespace AWS/EKS \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" --output json \
  > "$WORK_DIR/metric-catalog.json"
jq '.Metrics | to_entries | map({index:.key,metric:.value})' "$WORK_DIR/metric-catalog.json"
```

정확한 catalog index와 해당 메트릭에 적합한 통계를 선택하세요. 아래 로컬 생성기는 실제 namespace·dimension을 보존하고 widget region을 포함합니다. 없는 메트릭이나 다른 클러스터 항목을 거부해 허구의 패널을 만들지 않습니다.

```bash
: "${METRIC_INDEX:?Choose an exact entry from the captured catalog}"
: "${METRIC_STAT:?Choose the documented statistic for that metric, such as Maximum}"
export METRIC_INDEX METRIC_STAT AWS_REGION CLUSTER_NAME
python3 - <<'PY'
import json, os, re
from pathlib import Path
folder = Path(os.environ["WORK_DIR"])
metrics = json.loads((folder / "metric-catalog.json").read_text())["Metrics"]
index = int(os.environ["METRIC_INDEX"])
if index < 0 or index >= len(metrics):
    raise SystemExit("Metric is absent; verify collection instead of creating an empty widget")
metric = metrics[index]
if metric["Namespace"] != "AWS/EKS" or not any(
    d["Name"] == "ClusterName" and d["Value"] == os.environ["CLUSTER_NAME"]
    for d in metric["Dimensions"]
):
    raise SystemExit("Metric catalog entry does not match the reviewed cluster")
stat = os.environ["METRIC_STAT"]
if stat not in {"Average", "Sum", "Minimum", "Maximum", "SampleCount"}:
    if not re.fullmatch(r"p[0-9]+(?:\.[0-9]+)?", stat) or not 0 <= float(stat[1:]) <= 100:
        raise SystemExit("Unsupported statistic for this template")
series = [metric["Namespace"], metric["MetricName"]]
for dim in sorted(metric["Dimensions"], key=lambda d: d["Name"]):
    series.extend([dim["Name"], dim["Value"]])
body = {"widgets": [{"type": "metric", "x": 0, "y": 0, "width": 12, "height": 6,
    "properties": {"title": metric["MetricName"], "region": os.environ["AWS_REGION"],
                   "view": "timeSeries", "metrics": [series], "stat": stat, "period": 60}}]}
(folder / "dashboard.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```

승인된 절차로 dashboard를 생성·갱신하기 전에 `dashboard.json`을 검토하세요. Catalog에 있다고 모든 시간 구간에 datapoint가 있다는 뜻은 아닙니다. NodePool 개수, 프로비저닝 지연과 애플리케이션 SLO에는 실제 publisher·계측이 필요하며 Container Insights 하나로 모든 신호를 얻는다고 가정해서는 안 됩니다.

## 구조화된 Kubernetes 진단

존재하지 않는 `.status.phase` 대신 NodeClaim condition을 사용합니다. 모든 Pending Pod를 노드 용량 요청으로 취급하지 마세요.

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodepools -o json |
  jq '[.items[] | {name:.metadata.name,limits:.spec.limits,resources:.status.resources,
      requirements:.spec.template.spec.requirements,disruption:.spec.disruption,
      conditions:[.status.conditions[]? | {type,status,reason,observedGeneration}]}]'
```

```bash
: "${WORKLOAD_NAMESPACE:?Select the workload namespace}"
: "${POD_NAME:?Select the Pod}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pod "$POD_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,phase:.status.phase,
       nodeSelector:.spec.nodeSelector,affinity:.spec.affinity,tolerations:.spec.tolerations,
       conditions:[.status.conditions[]? | {type,status,reason,lastTransitionTime}],
       containers:[.status.containerStatuses[]? |
         {name,ready,restartCount,waitingReason:.state.waiting.reason}]}'
```

노드별 분포는 사람이 읽는 표의 열 번호 대신 구조화된 필드로 계산합니다. 아래는 배치됐지만 준비되지 않은 Pod를 포함한 active Pod 객체를 세고 미배치 객체를 구분합니다.

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
  jq '[.items[] | select(.status.phase != "Succeeded" and .status.phase != "Failed") |
       {node: (.spec.nodeName // "(unscheduled)"), namespace: .metadata.namespace, pod: .metadata.name}] |
      group_by(.node) | map({node: .[0].node, activePodObjects: length})'
```

`kubectl top`은 metrics API가 구성되고 정상일 때 사용합니다. 실패했다고 metrics-server가 없다고 단정하지 마세요. 실제 인스턴스 호환성, NodeClass readiness, IAM·네트워크 문제는 event reason과 관리형 compute 로그로 확인합니다. `consolidateAfter`를 줄여도 Spot interruption 복구가 빨라지는 것은 아닙니다.

### PDB 허용량은 준수 여부 판정이 아님

`disruptionsAllowed`가 0이어도 의도한 정상 상태일 수 있습니다. Generation과 현재·원하는 health를 먼저 확인하세요.

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[] | {
    namespace: .metadata.namespace, name: .metadata.name,
    currentHealthy: .status.currentHealthy, desiredHealthy: .status.desiredHealthy,
    disruptionsAllowed: .status.disruptionsAllowed,
    assessment: (if .status.observedGeneration != .metadata.generation
                    or .status.currentHealthy == null or .status.desiredHealthy == null
                    or .status.disruptionsAllowed == null
                  then "UnknownOrStale"
                  elif .status.currentHealthy < .status.desiredHealthy then "BelowDesiredHealthy"
                  elif .status.disruptionsAllowed == 0 then "HealthyNoVoluntaryEvictions"
                  else "EvictionsPermitted" end)
  }]'
```

워크로드 가용성 요구와 복구 계획을 이해하기 전에 blocking PDB를 삭제하거나 완화하지 마세요.

### Node 객체의 나이

Node 객체 생성 시각은 EC2 시작 시각이나 AMI patch age가 아닙니다. 정책에 맞는 진단 임계값을 선택하세요. 이전의 고정된 “7일 정수 초과” 스크립트는 시간을 버림 처리하고 부적절한 보편적 한도를 가정했습니다.

```bash
: "${MAX_NODE_OBJECT_AGE_HOURS:?Set a reviewed diagnostic threshold in hours}"
export MAX_NODE_OBJECT_AGE_HOURS
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
  jq '{items:[.items[] | {name:.metadata.name,createdAt:.metadata.creationTimestamp}]}' \
  > "$WORK_DIR/node-times.json"
python3 - <<'PY'
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
limit = float(os.environ["MAX_NODE_OBJECT_AGE_HOURS"])
if not math.isfinite(limit) or limit <= 0:
    raise SystemExit("Set a finite positive threshold")
now = datetime.now(timezone.utc)
rows = []
for item in json.loads((Path(os.environ["WORK_DIR"]) / "node-times.json").read_text())["items"]:
    result = {"node": item["name"], "thresholdHours": limit}
    try:
        created = datetime.fromisoformat(item.get("createdAt").replace("Z", "+00:00"))
        if created.tzinfo is None or created > now:
            raise ValueError("timestamp is not usable")
        hours = (now - created).total_seconds() / 3600
        result.update(nodeObjectAgeHours=round(hours, 3), exceedsThreshold=hours > limit)
    except (ValueError, TypeError, AttributeError):
        result["assessment"] = "UnknownTimestamp"
    rows.append(result)
print(json.dumps(rows, indent=2))
PY
```

알 수 없거나 미래의 timestamp를 정상으로 보고하지 않습니다. 교체 지연을 판단하기 전에 관측된 NodeClaim 정책, 이미지 정보와 AWS 유지보수·보안 정보를 대조하세요. 이 로컬 보고서는 CloudWatch alarm을 생성하지 않습니다.

## 보안 구성

Auto Mode는 관리형 Bottlerocket 이미지와 고정된 IMDSv2/hop-limit 설정을 사용합니다. 이전 `amiFamily`, `metadataOptions`, `blockDeviceMappings`와 잘못된 KMS ARN은 유효한 Auto Mode NodeClass 구성이 아니었습니다.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ops-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
```

Profile의 node role/access entry, 실제 프라이빗 라우팅과 보안 그룹 규칙을 검토하세요. 태그만으로 네트워크 제한이 입증되지는 않습니다. 노드 루트·데이터 EBS 암호화가 애플리케이션 PVC 암호화를 뜻하지도 않습니다. 고객 관리 키나 CA bundle에는 [NodePool 구성](./02-nodepool-configuration.md)의 유효한 `ephemeralStorage.kmsKeyID`·인증서 절차와 검토한 IAM/key policy를 사용하세요.

Restricted namespace에는 호환되는 워크로드 security context가 필요합니다. Host 접근이 필요한 노드 모니터링 agent를 억지로 이 namespace에 넣거나 agent 실행을 위해 클러스터 전체 보안을 해제하지 마세요. Collector의 별도 권한·namespace 정책을 검토합니다.

## 선택적인 Prometheus Query와 Alert

아래는 **단일 클러스터**, 설치된 kube-state-metrics와 Linux node-exporter 메트릭을 가정합니다.

- kube-state-metrics에서 `karpenter.sh/nodepool`, `eks.amazonaws.com/compute-type` node label을 allowlist에 포함합니다.
- CPU series에 정확히 매핑된 `node` label이 필요합니다. 모든 node-exporter scrape 구성에 자동으로 붙는 label은 아닙니다.
- Join/count 전에 kube-state-metrics replica를 중복 제거합니다. 한 노드에는 하나의 현재 NodePool label이 있어야 합니다.
- 여러 클러스터라면 모든 소스에 실제 cluster label을 보존하고 모든 group/join에 포함합니다.

Node query는 Auto Mode 노드만 선택합니다. Pod pending/unschedulable 신호는 클러스터 전체 기준이므로 Auto Mode 문제로 분류하기 전에 진단해야 합니다. CPU 식은 **노드별 non-idle 시간**이며 request 비율이나 용량 가중 pool 평균이 아닙니다. Series 부재를 자동으로 사용량 0으로 해석하지 마세요.

```promql
# nodes_by_pool
count by (label_karpenter_sh_nodepool) (max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))

# cpu
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{mode="idle",node!=""}[5m])))
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# pending
sum(max by (namespace, pod, uid) (kube_pod_status_phase{phase="Pending"}))

# unschedulable
sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable))

# age
((time() - max by (node) (kube_node_created)) / 86400)
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# not_ready
max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})
```

Prometheus Operator가 설치돼 있다면 Prometheus가 선택하는 namespace와 `ruleSelector`에 맞춰 다음 rule을 배치합니다. 임계값·기간은 설명용이며 모든 프로비저닝 실패가 termination counter로 표현된다는 뜻이 아닙니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: auto-ops-example
  namespace: monitoring
spec:
  groups:
  - name: auto-ops-example
    rules:
    - alert: ReportedUnschedulablePods
      expr: sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable)) > 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Reported unschedulable Pods exceed the example threshold
    - alert: AutoNodeNotReady
      expr: '(max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})

        * on (node) group_left (label_karpenter_sh_nodepool)

        max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))
        == 1'
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A registered Auto Mode node is not Ready
```

## 점검 주기

| 주기 | 검토할 증거 |
|------|-------------|
| 일일 | 지속되는 scheduling/NodeClaim 오류, Node condition, 워크로드 health, 현재 PDB 허용량과 collector 최신성 |
| 주간 | Disruption/drift event, 실제 객체·노드 나이, 용량·Spot 분포, resource requests와 청구 추세 |
| 변경 전·월간 | IAM/네트워크/스토리지 정책, 호환 소프트웨어·이미지 갱신, 검증한 복구, 할당량과 향후 수요 |

이전의 “Pending 0–5”, “CPU/메모리 80% 미만”, “시작 90초 미만”, “가용성 99.9%”와 응답 시간 범위는 검증되지 않은 계획용 기준이며 Auto Mode 정상 범위나 기본 SLO가 아닙니다. 모든 전환 상태나 PDB 허용량 0을 위반으로 부르지 말고 애플리케이션 목표·실측 동작에 근거해 임계값을 정의하세요.

## 참고 자료

- [Auto Mode NodePool behavior](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Disruption budgets, drift and termination](https://karpenter.sh/v1.14/concepts/disruption/)
- [Configure a PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Topology spread constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Auto Mode static capacity](https://docs.aws.amazon.com/eks/latest/userguide/auto-static-capacity.html)
- [NodeClass and capacity reservation selectors](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [EKS ARC zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift-enable.html)
- [Managed component log delivery](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Control-plane metrics and CloudWatch](https://aws.amazon.com/blogs/containers/proactive-amazon-eks-monitoring-with-amazon-cloudwatch-operator-and-aws-control-plane-metrics/)
- [CloudWatch dashboard structure](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Dashboard-Body-Structure.html)
- [Kube-state-metrics node metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [Kube-state-metrics Pod metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [NGINX unprivileged image](https://github.com/nginx/docker-nginx-unprivileged)

< [이전: Spot 전략](./04-spot-strategies.md) | [목차](./README.md) | [다음: 비용 관리](./06-cost-management.md) >
