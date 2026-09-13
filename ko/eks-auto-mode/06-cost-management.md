# 비용 관리 및 최적화

> **지원 버전**: EKS Auto Mode GA; 예제 검토 기준 EKS 1.36
> **마지막 업데이트**: 2026년 9월 12일

비용 최적화에는 같은 유효 작업량을 비교하는 청구 증거가 필요합니다. 노드 개수 snapshot, 낮은 CPU 사용률이나 광고 할인율은 실측 절감액이 아닙니다. 아래 예제는 소스·스키마·CLI 계약을 로컬에서 확인했으며 구매, 클라우드 배포나 실제 청구 조회는 수행하지 않았습니다.

## 청구 구성 요소

EKS 클러스터 요금, EC2 사용량, **별도 Auto Mode 요금**, EBS, 로드 밸런서, NAT/데이터 전송, 관측 및 기타 워크로드 서비스를 포함합니다. Auto Mode compute 요금은 최소 1분·초 단위이며 EC2 구매 옵션과 독립적입니다. EC2 Savings Plans/RI 할인이 별도 Auto Mode 요금에 적용되는 것은 아닙니다.

### 2026년 7월 GPU 요금 인하

AWS 7월 발표에 따르면 7월 1일부터 G 시리즈의 **Auto Mode 관리 요금**은 35%, P 시리즈/Trainium은 60% 인하되어 지원 리전에 자동 적용됩니다. 해당 요금 구성 요소의 인하이며 전체 GPU 청구액에 같은 비율이 적용되지는 않습니다. 발표에는 local NVMe GPU 인스턴스의 병렬 이미지 pull/unpack과 가속기 인식 복구도 포함되지만 이 예제의 실측 시작·애플리케이션 복구 시간을 입증하지는 않습니다.

## 비용을 고려한 배치

먼저 [운영 및 관리](./05-operations.md)의 계정/API 엔드포인트 검사와 private `WORK_DIR`를 사용하세요. 예제는 검토된 `default` NodeClass와 호환 용량을 가정합니다. 배포 전 비용을 검토합니다.

다음 완전한 실습 워크로드는 이전 영어 예제의 누락된 selector/image를 보완합니다. 운영 장에서 확인한 non-root nginx 이미지, Restricted namespace와 pool selector/toleration을 사용합니다. Requests는 **실측값이 아닌 설명용 값**입니다. ARM을 허용하기 전에 다중 아키텍처 이미지·라이브러리·애플리케이션 동작을 확인하세요.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cost-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
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
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
  namespace: cost-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: cost-efficient
  template:
    metadata:
      labels:
        app: cost-efficient
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.4@sha256:cb92301e719d6639028de775fe8b28e15f58343aca5e5372001311958aafb300
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
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
        karpenter.sh/nodepool: cost-optimized
      tolerations:
      - key: cost-lab
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
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values:
                - spot
```

Spot과 On-Demand를 함께 허용하면 용량을 선택할 수 있지만 soft Pod preference가 비율이나 즉각적인 fallback을 보장하지는 않습니다. Category 다양성도 리전·NodeClass·워크로드·실제 재고가 허용해야 유효합니다. 별도 티어 풀은 interruption/GPU/아키텍처 제약을 표현할 수 있으나 불필요한 분할은 packing 효율을 낮출 수 있습니다.

`WhenEmptyOrUnderutilized`는 requests와 제약으로 Pod를 더 저렴하게 재배치할 수 있는지 판단하며 CPU 사용률 임계값이 아닙니다. `consolidateAfter`는 debounce이지 삭제 마감 시각이 아닙니다. PDB·affinity·budget이 consolidation을 막을 수 있습니다. Pool CPU/memory limits는 인프라 확장을 제한하지만 급격한 프로비저닝에서는 eventual consistency로 일시적으로 초과할 수 있습니다. 통화 예산이나 계정 전체의 강제 지출 상한은 아닙니다.

## 청구와 운영 메트릭 구분

현재 노드 gauge는 node-hours가 아니며, node-hours도 인스턴스·요율·시간 없이 달러가 되지 않습니다. Auto Mode가 이전 예제의 허구 `Karpenter` CloudWatch 비용 메트릭을 자동 발행하지는 않습니다. 금액에는 실제 청구 export/Cost Explorer를, 용량·성능에는 구성한 collector를 사용하세요.

### CloudWatch 청구 개요

Billing alerts/metrics를 활성화하면 전 세계 계정의 `AWS/Billing` 추정 요금이 **us-east-1**에 발행됩니다. 현재 월의 누적 추정 요금이며 일일 EC2 지출, 특정 EKS 클러스터 합계나 예측값이 아닙니다. Payer 계정의 linked-account 범위도 확인하세요. 다음 로컬 dashboard 정의에는 필요한 currency dimension과 region이 있습니다.

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "Account estimated charges, month to date (USD)",
        "region": "us-east-1",
        "view": "timeSeries",
        "metrics": [
          [
            "AWS/Billing",
            "EstimatedCharges",
            "Currency",
            "USD"
          ]
        ],
        "period": 21600,
        "stat": "Maximum"
      }
    }
  ]
}
```

서비스·클러스터 할당과 일별 변화에는 Cost Explorer/CUR 또는 Data Exports를 사용합니다. AWS Budgets/Cost Anomaly Detection은 검토한 금액 임계값을 알릴 수 있지만 강제 지출 상한은 아닙니다. 노드 개수 alarm은 별도 용량 제어이며 실제 publisher·dimension·알림 대상이 필요합니다. 이전 alarm은 허구의 메트릭과 정의되지 않은 SNS 리소스를 참조했습니다.

### Kubecost

검토한 stable chart/app은 **3.2.4**, chart 이름은 새 저장소의 `kubecost`입니다. 더 최신 release candidate를 무조건 업그레이드 대상으로 선택하지 않았습니다. 버전 3은 FinOps agent와 ClickHouse 기반 구조를 사용합니다. 이전 `cost-analyzer` 저장소, CLI의 `kubecostToken` 예제나 버전 2 Prometheus 배포 가정을 재사용하지 마세요.

버전에 맞춰 라이선스, cluster identity, 청구 연동, 범위가 제한된 워크로드 IAM, 인증, 보존과 스토리지 values를 준비합니다. Auto Mode EBS StorageClass는 `ebs.csi.eks.amazonaws.com`이며 필요한 곳에 명시적으로 선택하고 암호화를 검토하세요. Chart에는 영구 데이터 보존/keep annotation이 있으므로 uninstall만으로 모든 유료 스토리지 삭제가 입증되지 않습니다. 접근을 private으로 유지하고 collector/telemetry 동작을 검토합니다. 설치 전에 로컬로 렌더링하세요.

```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```

이 명령은 설치하지 않습니다. Pod/namespace/idle cost 할당에는 agent와 일치하는 데이터 소스가, 실제 청구 대조에는 AWS 연동이 필요합니다. Namespace label만으로 청구 데이터가 생성되지는 않습니다. 호환되지 않는 추정치를 더하지 말고 idle/shared cost·할인·미할당 비용을 조정하세요.

## Spot 절감 측정

아래 구조화된 snapshot은 노드 0개, 누락된 label과 혼합 인스턴스를 처리합니다. **Auto Mode Node 객체**를 세며 청구 시간이나 지출을 계산하지 않습니다.

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[] | {
  capacity: (.metadata.labels["karpenter.sh/capacity-type"] // "unknown"),
  instanceType: (.metadata.labels["node.kubernetes.io/instance-type"] // "unknown")
}] as $nodes |
{
  totalNodeObjects: ($nodes | length),
  byCapacityAndType: ($nodes | group_by([.capacity,.instanceType]) |
    map({capacity: .[0].capacity, instanceType: .[0].instanceType, count:length})),
  spotNodePercent: (if ($nodes|length) == 0 then null
    else 100 * ([$nodes[]|select(.capacity=="spot")]|length) / ($nodes|length) end)
}'
```

비용 비교에는 같은 기간, 리전/AZ, 인스턴스/OS/tenancy, 통화와 유효 작업량 조건을 사용합니다. 과거 Spot 요율은 AZ·시각별로 다릅니다. 인스턴스 유형만으로 선택한 Pricing API 결과는 리전/OS/tenancy/상품이 다를 수 있고 이전 스크립트는 API 오류도 숨겼습니다. 현재 가격 표본으로 지난달 실제 청구를 재구성할 수는 없습니다.

```text
reference_total = cost of the reviewed On-Demand counterfactual for the same useful work
actual_total = actual compute + Auto Mode fees + other allocated costs
               + recovery costs not already included in those billed components
savings_amount = reference_total - actual_total
savings_percent = 100 * savings_amount / reference_total  (reference_total > 0)
```

중단·재시도 작업과 idle/미사용 약정은 한 번씩 포함하고 복구 compute를 중복 계산하지 마세요. 기준 비용에도 대응하는 Auto Mode/기타 요금이 필요합니다. 가정한 70% Spot 할인이나 현재 Spot 노드 비율을 실제 월간 절감이라고 부를 수 없습니다. Interruption event의 증거도 따로 유지하세요. 추측한 termination counter reason이 모든 interruption을 측정하지는 않습니다.

### Cost Explorer 읽기 전용 조회

먼저 AWS 생성 태그 **`aws:eks:cluster-name`**을 활성화합니다. `eks:cluster-name`은 문서화된 청구 key가 아닙니다. 참여 EC2 인스턴스 비용을 할당하며 **control-plane 요금이나 모든 클러스터 관련 서비스를 포함하지는 않습니다**. 계정/payer 범위와 태그 coverage를 검토하세요. Cost Explorer API 조회 자체에도 요금이 발생할 수 있습니다.

시작 포함·종료 제외 기간을 명시합니다. 다음 요청은 금액인 `AmortizedCost`를 사용하며 다른 단위의 `UsageQuantity`를 더하거나 노드 비율을 달러로 바꾸지 않습니다.

```bash
: "${COST_START:?Set YYYY-MM-DD inclusive start}"
: "${COST_END:?Set YYYY-MM-DD exclusive end, no later than today UTC}"
export COST_START COST_END CLUSTER_NAME
python3 - <<'PY'
import json, os
from datetime import date, datetime, timezone
from pathlib import Path
start, end = (date.fromisoformat(os.environ[key]) for key in ("COST_START", "COST_END"))
if not start < end <= datetime.now(timezone.utc).date():
    raise SystemExit("Require start < end <= today UTC")
request = {
    "TimePeriod": {"Start": start.isoformat(), "End": end.isoformat()},
    "Granularity": "DAILY",
    "Metrics": ["AmortizedCost"],
    "Filter": {"Tags": {"Key": "aws:eks:cluster-name", "Values": [os.environ["CLUSTER_NAME"]]}},
    "GroupBy": [{"Type": "DIMENSION", "Key": "INSTANCE_TYPE"},
                {"Type": "DIMENSION", "Key": "PURCHASE_TYPE"}]
}
(Path(os.environ["WORK_DIR"]) / "ce-request.json").write_text(json.dumps(request, indent=2) + "\n")
PY
```

```bash
check_account
aws ce get-cost-and-usage --region us-east-1 \
  --cli-input-json "file://$WORK_DIR/ce-request.json" \
  --output json > "$WORK_DIR/ce-result.json"
jq '[.ResultsByTime[] | {period:.TimePeriod,estimated:.Estimated,groups:.Groups}]' \
  "$WORK_DIR/ce-result.json"
```

`Estimated` 표시를 보존하고 환불·credit·할인 할당·불완전한 데이터를 고려합니다. 태그 필터에는 미할당 요금이나 미사용 약정이 빠질 수 있으므로 합계·절감을 주장하기 전에 전체 청구 데이터와 대조하세요.

## 리소스 적정 크기

고정된 [VPA 1.7.1 설치 가이드](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/installation.md)를 사용합니다. 문서상 Kubernetes 1.28+를 지원하며 특정 in-place 기능은 더 높은 버전이 필요합니다. 이전 `releases/latest/download/...` URL은 유효한 VPA 설치 절차가 아니었습니다. 클러스터 범위 설치 스크립트 적용 전에 CRD·RBAC·metrics-server·컴포넌트/인증서 구성을 검토하세요. `Off`도 정상 recommender가 필요합니다.

아래 리소스는 같은 namespace의 실제 실습 Deployment를 대상으로 합니다.

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get vpa cost-app-vpa -o json |
  jq '{conditions:.status.conditions,recommendations:.status.recommendation.containerRecommendations}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get deployment cost-efficient-app -o json |
  jq '[.spec.template.spec.containers[] | {name,resources}]'
```

`Off`는 권장값만 만들고 적용하지 않습니다. 모든 컨테이너, recommendation condition/이력, 계절성, 시작 peak, latency, CPU throttling과 memory/OOM 동작을 확인하세요. `resourcePolicy` 범위가 권장값과 기존 limits의 호환성을 입증하지는 않습니다. VPA는 성능 보장이 아니며 검토한 버전에는 Pod-level resource stanza 관련 제한도 문서화돼 있습니다.

### Kubernetes quantity 단위 보존

CPU `1`은 1 core, `1m`은 1 millicore입니다. `1Gi`는 1024Mi이며 접미사를 지워서는 변환되지 않습니다. 이전 `sed`/`awk` 합계 대신 컨테이너별 원 requests/limits와 사용량을 보존하세요.

```bash
: "${WORKLOAD_NAMESPACE:?Select a namespace}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pods -o json |
  jq '[.items[] | {pod:.metadata.name,uid:.metadata.uid,
    podResources:.spec.resources,overhead:.spec.overhead,
    containers:[.spec.containers[]|{name,resources}],
    initContainers:[.spec.initContainers[]?|{name,restartPolicy,resources}]}]' \
  > "$WORK_DIR/pod-requests.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  top pods --containers > "$WORK_DIR/container-usage.txt"
```

Metrics 조회는 성공해야 하며 데이터 부재는 사용률 0이 아닙니다. 두 snapshot은 동시 관측도 아니고, 컨테이너 사용량이 scheduler의 전체 Pod request 계산도 아닙니다. Init/restartable-init 컨테이너, Pod-level resources와 overhead도 고려해야 합니다.

| 관측 | 검토할 조치 |
|------|-------------|
| Request가 대표 사용량의 2배 초과로 보임 | 축소 전 peak/SLO 여유 조사; 자동 20–50% 절감 아님 |
| Request가 사용량의 2배 이내 | 최적이라는 증거 아님 |
| 사용량이 request 초과 | 배치·여유 검토; OOM 제한에는 단순 request가 아닌 메모리 **limit**이 관련 |
| Limit이 request보다 매우 큼 | Burst/throttling/OOM 정책 검토; limit만 줄여도 일반적인 request 기반 packing이 좋아지지는 않음 |

### 선택적인 Prometheus 검토 후보

다음 info rule은 **단일 클러스터**, CPU core/memory byte로 정규화된 kube-state-metrics와 namespace/Pod/container label이 있는 컨테이너 수준 cAdvisor를 가정합니다. CPU query는 합계 `cpu="total"` series가 필요하므로 collector label을 확인하세요. Collector replica 중복·인프라 cgroup을 제외하고 양수 request 분모를 요구합니다. 여러 클러스터는 모든 group/join에 실제 cluster label을 포함하세요. Series 부재를 0으로 바꾸지 않습니다. 오래된 series·컨테이너 재생성 영향과 대표 이력도 검토합니다.

1시간 동안 30% 미만이라는 임계값은 검토 trigger 예시이며 자동 request 축소 권장이나 실측 절감이 아닙니다. Prometheus Operator 설치 후 namespace/rule selector를 맞춰 사용하세요.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cost-review-candidates
  namespace: monitoring
spec:
  groups:
  - name: cost-review-candidates
    rules:
    - alert: LowCpuRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])) and on (namespace,pod,container)\
        \ max by (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        cpu\",unit=\"core\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\n\
        ) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\
        \ > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}) unless\
        \ on (namespace,pod,container) max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m]))\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
    - alert: LowMemoryRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"}) and on (namespace,pod,container) max by\
        \ (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        memory\",unit=\"byte\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }))\n) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        })) > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }) unless on (namespace,pod,container) max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"})\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
```

## Savings Plans와 Reserved Instances

| 옵션 | 적격 사용량/범위 | 주요 제한 |
|------|------------------|-----------|
| Compute Savings Plans | 패밀리·크기·리전·OS·tenancy와 무관한 적격 EC2 사용량, Fargate/Lambda도 포함 | 최대 66%는 광고상 최대이며 예상 할인 아님 |
| EC2 Instance Savings Plans | 한 리전의 선택한 패밀리; 그 범위의 크기·OS·tenancy 유연성 | 최대 72%; 정확한 한 인스턴스 크기에 대한 약정 아님 |
| EC2 RI | 조건이 일치하는 사용량; offering별 regional size 유연성/교환 규칙 | 기존에 일치하는 약정도 Auto Mode에 유효할 수 있음 |
| Spot | 별도 Spot 가격 | Savings Plans 중복 할인 없음 |

적격 Graviton·GPU EC2 사용량에 별도 “ARM Savings Plan”이나 GPU 전체 제외 규칙이 필요한 것은 아닙니다. SageMaker AI Savings Plans는 SageMaker 사용량 대상이며 ML을 실행한다는 이유로 EC2 GPU 노드에 적용되지 않습니다. Savings Plans는 물리 용량을 예약하지 않으므로 capacity reservation은 별도로 검토하세요. 별도 Auto Mode 요금은 EC2 할인 범위 밖입니다.

지속되는 적격·미커버 시간별 사용량으로 **해당 Savings Plans 요율의 USD/hour** 약정을 계산합니다. Baseline에서 이미 Spot을 제외했다면 `(1 - Spot%)`를 다시 곱하지 마세요. 기존 RI/SP coverage, 향후 적정화·아키텍처 변경, 공유 설정, 계절성과 미사용 약정을 고려합니다. 낮은 EC2 요율이나 노드 수만으로 안전한 구매액이 결정되지는 않습니다.

```bash
check_account
aws ce get-savings-plans-purchase-recommendation --region us-east-1 \
  --savings-plans-type COMPUTE_SP --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT --lookback-period-in-days THIRTY_DAYS \
  --output json > "$WORK_DIR/savings-plan-recommendation.json"
```

권장값 조회이며 구매 명령이 아닙니다. 30일 lookback은 API 선택지이므로 결정 전에 더 긴 대표 이력과 비교하세요.

이전 Compute coverage 60–70%/70%, EC2 Instance coverage 30–40%, On-Demand coverage 50%와 Spot 40–60% / covered 30–40% / uncovered 10–20% 그림은 **검증되지 않은 계획 예시**이며 서로 더하는 보편적 목표가 아닙니다. 워크로드는 Spot 또는 On-Demand 용량에서 실행되며 Savings Plans는 적격 사용량의 청구 coverage이지 세 번째 노드 유형이 아닙니다.

## 비용 귀속

유효한 NodeClass identity/network selector와 승인된 태깅 권한을 사용합니다. 커스텀 NodeClass에는 node-role access entry가 필요합니다. 태그는 리소스를 설명하며 네트워크 격리나 모든 종속 서비스 coverage를 자동 생성하지 않습니다.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
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
  tags:
    Environment: lab
    Team: platform
    Project: web-services
    CostCenter: CC-12345
    Application: cost-lab
    ManagedBy: eks-auto-mode
```

이 예제를 사용하려면 대상 pool에서 `tagged-nodeclass`를 의도적으로 참조하세요. `amiFamily: AL2023`은 Auto Mode NodeClass 필드가 아닙니다. 실제 리소스 태그를 확인하고 Billing에서 key를 활성화합니다. 사용자 정의 key는 활성화 목록에 보이는 데 최대 24시간, 그 후 활성화에도 최대 24시간이 걸릴 수 있으며 보고서 최신성은 별도입니다. 정확히 24시간 후 모든 데이터가 나온다고 보장하지 마세요.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    cost-center: team-a
    environment: production
```

Namespace label은 Kubernetes 비용 할당 도구에 사용할 수 있지만 AWS 비용 할당 태그로 자동 전파되지는 않습니다. EC2 태그 귀속도 shared/control-plane/storage/network 비용 배분을 대체하지 않습니다.

## 최적화 체크리스트와 이전 수치

호환 인스턴스 다양성, 워크로드에 맞는 Spot, 측정한 request 적정화, 가능한 consolidation, 청구 통합과 약정 검토를 별도 작업으로 관리합니다. 변경 전후 전체 유효 작업 비용과 가용성을 측정하세요.

아래 이전 추정치에는 확인된 benchmark/청구 출처가 없습니다. 맥락 보존용이며 보장값이 아니고, 더하거나 곱해서 전체 절감액이라고 주장해서는 안 됩니다.

| 이전 주제 | 원래 예시 범위 |
|-----------|----------------|
| Spot | 60–70%, 60–90%, 70–90% |
| ARM/Graviton | 20% |
| Request 적정화/VPA | 10–30%, 15–30%, 20–40%, 20–50% |
| Consolidation | 10–20%, 10–30% |
| Savings Plans | 20–30%, 20–40% |
| Multi-AZ/스케줄링 | 5–10% / 10–20% |

AZ 복원력 축소는 일반적인 비용 최적화가 아닙니다. 배치·스케줄링 실험에는 데이터 전송, 장애 복구, 스토리지 보존과 워크로드 목표를 함께 반영하세요.

## 참고 자료

- [EKS pricing and Auto Mode charges](https://aws.amazon.com/eks/pricing/)
- [July 2026 GPU management-fee reduction](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-auto-mode-gpu-price/)
- [Auto Mode cost controls](https://docs.aws.amazon.com/eks/latest/userguide/auto-cost-control.html)
- [NodePool resource limits and disruption](https://karpenter.sh/v1.14/concepts/nodepools/)
- [Savings Plans types](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [Savings Plans versus RIs](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-ris.html)
- [EKS billing tags](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
- [Activating cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)
- [CloudWatch estimated billing charges](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html)
- [Kubecost 3.2.4 chart](https://kubecost.github.io/kubecost/kubecost-3.2.4.tgz)
- [VPA 1.7.1 installation](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/installation.md)
- [VPA known limitations](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/known-limitations.md)
- [Kubernetes resource units and scheduling](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Auto Mode NodeClass and tags](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)

< [이전: 운영 및 관리](./05-operations.md) | [목차](./README.md) | [다음: 노드 생명주기](./07-node-lifecycle.md) >
