# 비용 관리 및 최적화

> **지원 버전**: EKS 1.29+, EKS Auto Mode GA
> **마지막 업데이트**: 2026년 2월 19일

< [이전: 운영 및 관리](./05-operations.md) | [목차](./README.md) | [다음: 노드 생명주기](./07-node-lifecycle.md) >

---

이 문서에서는 EKS Auto Mode에서 비용을 효과적으로 관리하고 최적화하는 방법을 설명합니다.

## 비용 최적화 기본 원칙

```yaml
# cost-optimization-best-practices.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
        # 1. 다양한 인스턴스 패밀리 허용
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]

        # 2. Graviton (ARM) 인스턴스 포함 (20% 저렴)
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]

        # 3. Spot 인스턴스 우선
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  # 4. 적극적인 Consolidation
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# 비용 최적화를 위한 Pod 설정
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
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
      # Spot 선호
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]

      # 적절한 리소스 요청 (오버프로비저닝 방지)
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 250m      # 실제 사용량 기반
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

## 비용 분석 대시보드

### CloudWatch 기반 비용 대시보드

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "일별 EC2 비용 추세",
        "metrics": [
          ["AWS/Billing", "EstimatedCharges", "ServiceName", "Amazon Elastic Compute Cloud - Compute"]
        ],
        "period": 86400,
        "stat": "Maximum"
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "노드 수 vs 비용",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", { "label": "노드 수" }],
          ["AWS/Billing", "EstimatedCharges", "ServiceName", "Amazon Elastic Compute Cloud - Compute", { "yAxis": "right", "label": "EC2 비용" }]
        ],
        "period": 3600
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Spot vs On-Demand 비율",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "spot", { "label": "Spot" }],
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "on-demand", { "label": "On-Demand" }]
        ],
        "period": 300
      }
    }
  ]
}
```

### Kubecost 통합

```yaml
# kubecost-installation.yaml
# Helm을 통한 Kubecost 설치
# helm repo add kubecost https://kubecost.github.io/cost-analyzer/
# helm install kubecost kubecost/cost-analyzer \
#   --namespace kubecost \
#   --create-namespace \
#   --set kubecostToken="<token>"

# Kubecost 대시보드 접근
# kubectl port-forward -n kubecost deployment/kubecost-cost-analyzer 9090
```

### 비용 할당 태깅

```yaml
# 비용 추적을 위한 NodeClass 태깅
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
spec:
  amiFamily: AL2023
  tags:
    # AWS Cost Allocation Tags
    Environment: production
    Team: platform
    Project: web-services
    CostCenter: "CC-12345"
    Application: my-app
```

## Spot 인스턴스 절감 효과 측정

### Spot 절감률 계산

```bash
#!/bin/bash
# spot-savings-calculator.sh

# 현재 Spot 노드 정보 수집
echo "=== Spot 인스턴스 절감 분석 ==="

# Spot 노드 수
SPOT_COUNT=$(kubectl get nodes -l karpenter.sh/capacity-type=spot --no-headers | wc -l)
# On-Demand 노드 수
OD_COUNT=$(kubectl get nodes -l karpenter.sh/capacity-type=on-demand --no-headers | wc -l)

echo "Spot 노드: $SPOT_COUNT"
echo "On-Demand 노드: $OD_COUNT"
echo "Spot 비율: $(echo "scale=2; $SPOT_COUNT * 100 / ($SPOT_COUNT + $OD_COUNT)" | bc)%"

# 인스턴스 타입별 현재 Spot 가격 조회
echo ""
echo "=== 인스턴스 타입별 Spot 가격 ==="
for type in m6i.xlarge m6i.2xlarge c6i.xlarge c6i.2xlarge; do
  SPOT_PRICE=$(aws ec2 describe-spot-price-history \
    --instance-types $type \
    --product-description "Linux/UNIX" \
    --max-items 1 \
    --query 'SpotPriceHistory[0].SpotPrice' \
    --output text 2>/dev/null)

  OD_PRICE=$(aws pricing get-products \
    --service-code AmazonEC2 \
    --filters "Type=TERM_MATCH,Field=instanceType,Value=$type" \
    --query 'PriceList[0]' 2>/dev/null | jq -r '.terms.OnDemand | to_entries[0].value.priceDimensions | to_entries[0].value.pricePerUnit.USD' 2>/dev/null)

  if [ -n "$SPOT_PRICE" ] && [ -n "$OD_PRICE" ]; then
    SAVINGS=$(echo "scale=0; (1 - $SPOT_PRICE / $OD_PRICE) * 100" | bc)
    echo "$type: Spot \$$SPOT_PRICE vs On-Demand \$$OD_PRICE (절감: ${SAVINGS}%)"
  fi
done
```

### Spot 인터럽트 비용 영향 분석

```yaml
# Prometheus 메트릭을 활용한 Spot 분석
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: spot-cost-analysis
spec:
  groups:
    - name: spot-savings
      rules:
        # Spot 노드 비율
        - record: karpenter:spot_ratio
          expr: |
            sum(karpenter_nodes_total{capacity_type="spot"}) /
            sum(karpenter_nodes_total) * 100

        # Spot 인터럽트 빈도 (시간당)
        - record: karpenter:spot_interrupts_per_hour
          expr: |
            increase(karpenter_nodeclaims_terminated{reason="SpotInterruption"}[1h])
```

## 리소스 적정 크기 분석

### VPA를 활용한 리소스 추천

```yaml
# VPA 설치 및 설정
# kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-v1-crd.yaml
# kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-v1-rbac.yaml

apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # 추천만 받고 자동 적용은 안함
  resourcePolicy:
    containerPolicies:
      - containerName: "*"
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 4
          memory: 8Gi
```

### 리소스 사용량 분석 스크립트

```bash
#!/bin/bash
# resource-analysis.sh

echo "=== 리소스 적정 크기 분석 ==="

# 네임스페이스별 리소스 요청 vs 실제 사용량
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  echo ""
  echo "--- Namespace: $ns ---"

  # 요청된 리소스
  REQUESTED_CPU=$(kubectl get pods -n $ns -o jsonpath='{.items[*].spec.containers[*].resources.requests.cpu}' | tr ' ' '\n' | grep -v '^$' | sed 's/m//' | awk '{sum+=$1} END {print sum}')
  REQUESTED_MEM=$(kubectl get pods -n $ns -o jsonpath='{.items[*].spec.containers[*].resources.requests.memory}' | tr ' ' '\n' | grep -v '^$' | sed 's/Mi//' | awk '{sum+=$1} END {print sum}')

  # 실제 사용량 (kubectl top 기반)
  ACTUAL=$(kubectl top pods -n $ns --no-headers 2>/dev/null)
  if [ -n "$ACTUAL" ]; then
    ACTUAL_CPU=$(echo "$ACTUAL" | awk '{print $2}' | sed 's/m//' | awk '{sum+=$1} END {print sum}')
    ACTUAL_MEM=$(echo "$ACTUAL" | awk '{print $3}' | sed 's/Mi//' | awk '{sum+=$1} END {print sum}')

    if [ -n "$REQUESTED_CPU" ] && [ "$REQUESTED_CPU" != "0" ]; then
      CPU_UTIL=$(echo "scale=0; $ACTUAL_CPU * 100 / $REQUESTED_CPU" | bc)
      echo "CPU: 요청 ${REQUESTED_CPU}m, 사용 ${ACTUAL_CPU}m (${CPU_UTIL}% 활용)"
    fi

    if [ -n "$REQUESTED_MEM" ] && [ "$REQUESTED_MEM" != "0" ]; then
      MEM_UTIL=$(echo "scale=0; $ACTUAL_MEM * 100 / $REQUESTED_MEM" | bc)
      echo "Memory: 요청 ${REQUESTED_MEM}Mi, 사용 ${ACTUAL_MEM}Mi (${MEM_UTIL}% 활용)"
    fi
  fi
done
```

### 오버프로비저닝 감지

```yaml
# 리소스 오버프로비저닝 경고
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: resource-efficiency-alerts
spec:
  groups:
    - name: resource-efficiency
      rules:
        # CPU 오버프로비저닝 감지
        - alert: CPUOverProvisioned
          expr: |
            (
              sum by (namespace, pod) (
                kube_pod_container_resource_requests{resource="cpu"}
              ) -
              sum by (namespace, pod) (
                rate(container_cpu_usage_seconds_total[5m])
              )
            ) /
            sum by (namespace, pod) (
              kube_pod_container_resource_requests{resource="cpu"}
            ) > 0.7
          for: 1h
          labels:
            severity: info
          annotations:
            summary: "CPU 오버프로비저닝 감지"
            description: "{{ $labels.namespace }}/{{ $labels.pod }}가 요청 CPU의 30% 미만을 사용 중"

        # 메모리 오버프로비저닝 감지
        - alert: MemoryOverProvisioned
          expr: |
            (
              sum by (namespace, pod) (
                kube_pod_container_resource_requests{resource="memory"}
              ) -
              sum by (namespace, pod) (
                container_memory_working_set_bytes
              )
            ) /
            sum by (namespace, pod) (
              kube_pod_container_resource_requests{resource="memory"}
            ) > 0.7
          for: 1h
          labels:
            severity: info
          annotations:
            summary: "메모리 오버프로비저닝 감지"
```

## Savings Plans 및 Reserved Instances 전략

### Auto Mode와 Savings Plans 통합

EKS Auto Mode는 동적으로 인스턴스를 프로비저닝하므로, Savings Plans을 전략적으로 활용해야 합니다.

| 전략 | 설명 | 권장 비율 |
|------|------|----------|
| **Compute Savings Plans** | 인스턴스 패밀리/리전 유연성 | 기본 워크로드의 60-70% |
| **EC2 Instance Savings Plans** | 특정 인스턴스 패밀리 고정 | 안정적 워크로드의 30-40% |
| **Spot + Savings Plans 혼합** | Spot으로 커버 안 되는 부분 보완 | On-Demand의 50% |

### Savings Plans 적용 전략

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Auto Mode + Savings Plans 전략                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  총 컴퓨팅 용량                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │████████████████████████████████████████████████████████████████████│  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  │                         │                    │                      │  │
│  │    Spot (40-60%)        │  Savings Plans    │   On-Demand          │  │
│  │    최대 비용 절감        │  (30-40%)         │   (10-20%)           │  │
│  │                         │  안정적 할인       │   유연성 확보         │  │
│                                                                              │
│  권장 접근법:                                                                 │
│  1. 먼저 Spot 활용을 극대화 (인터럽트 허용 워크로드)                           │
│  2. 기준 부하(baseline)에 Compute Savings Plans 적용                        │
│  3. 나머지는 On-Demand로 유연성 확보                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Savings Plans 구매 가이드

```bash
# 현재 사용량 패턴 분석
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity DAILY \
  --metrics "UnblendedCost" "UsageQuantity" \
  --filter '{
    "Dimensions": {
      "Key": "SERVICE",
      "Values": ["Amazon Elastic Compute Cloud - Compute"]
    }
  }' \
  --group-by Type=DIMENSION,Key=INSTANCE_TYPE

# Savings Plans 추천 받기
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days THIRTY_DAYS
```

## 비용 최적화 권장 사항 요약

| 영역 | 권장 사항 | 예상 절감 |
|------|----------|----------|
| **인스턴스 다양화** | 다양한 인스턴스 패밀리 허용 | 가용성 향상 |
| **Graviton 활용** | ARM 인스턴스 포함 | 최대 20% |
| **Spot 활용** | 인터럽트 허용 워크로드에 Spot 사용 | 60-70% |
| **Consolidation** | WhenEmptyOrUnderutilized 설정 | 10-30% |
| **리소스 적정화** | VPA 기반 리소스 요청 조정 | 20-40% |
| **Savings Plans** | 기준 부하에 Compute SP 적용 | 20-30% |

---

< [이전: 운영 및 관리](./05-operations.md) | [목차](./README.md) | [다음: 노드 생명주기](./07-node-lifecycle.md) >
