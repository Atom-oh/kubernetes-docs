# EKS 업그레이드: Auto Mode 무중단 업그레이드

> **지원 버전**: EKS 1.29+, EKS Auto Mode GA
> **마지막 업데이트**: 2025년 6월

< [이전: 리소스 최적화](./10-resource-optimization.md) | [목차](./README.md) | [다음: 없음] >

---

이 문서에서는 EKS Auto Mode 환경에서 무중단 업그레이드를 수행하는 방법을 설명합니다. 업그레이드 계획부터 사전 체크리스트, Auto Mode 특화 업그레이드, 블루/그린 전략, 그리고 사후 검증까지 실전 운영에 필요한 모든 내용을 다룹니다.

## 목차

1. [업그레이드 계획](#1-업그레이드-계획)
2. [사전 체크리스트](#2-사전-체크리스트)
3. [Auto Mode 업그레이드](#3-auto-mode-업그레이드)
4. [블루/그린 업그레이드](#4-블루그린-업그레이드)
5. [사후 검증](#5-사후-검증)

---

## 1. 업그레이드 계획

### Kubernetes 버전 지원 정책 (N-3)

Kubernetes는 최근 3개의 마이너 버전(N, N-1, N-2)만 공식 지원합니다. EKS는 이보다 넓은 범위를 지원하지만, 보안 패치와 버그 수정은 주로 최신 버전에 집중됩니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes 버전 지원 범위                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1.27 ──── 1.28 ──── 1.29 ──── 1.30 ──── 1.31 ──── 1.32       │
│    │         │         │         │         │         │          │
│    ▼         ▼         ▼         ▼         ▼         ▼          │
│  지원종료   Extended   N-2       N-1        N      Preview       │
│             Support                      (최신)                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### EKS 버전 생명주기

EKS 버전은 두 가지 지원 단계를 거칩니다:

| 지원 단계 | 기간 | 특징 | 비용 |
|----------|------|------|------|
| **Standard Support** | 출시 후 ~14개월 | 모든 패치, 보안 업데이트 제공 | 기본 요금 |
| **Extended Support** | Standard 종료 후 ~12개월 | 중요 보안 패치만 제공 | 추가 비용 ($0.60/cluster/hour) |

```bash
# 현재 EKS 버전 지원 상태 확인
aws eks describe-addon-versions --kubernetes-version 1.30 \
  --query 'addons[0].addonVersions[0].compatibilities[0]'

# 클러스터 현재 버전 확인
aws eks describe-cluster --name my-cluster \
  --query 'cluster.version' --output text
```

### 버전 호환성 매트릭스

| EKS 버전 | K8s 버전 | 주요 기능 | CoreDNS | VPC CNI | kube-proxy | 지원 상태 |
|---------|---------|----------|---------|---------|------------|----------|
| 1.32 | 1.32.x | DRA GA, CEL Admission | v1.11.4 | v1.19.2 | v1.32.0 | Preview |
| 1.31 | 1.31.x | AppArmor GA, nftables | v1.11.3 | v1.19.0 | v1.31.3 | Standard |
| 1.30 | 1.30.x | Pod Scheduling Readiness | v1.11.1 | v1.18.5 | v1.30.6 | Standard |
| 1.29 | 1.29.x | ReadWriteOncePod GA | v1.11.1 | v1.18.2 | v1.29.10 | Standard |
| 1.28 | 1.28.x | Sidecar Containers | v1.10.1 | v1.16.4 | v1.28.13 | Extended |
| 1.27 | 1.27.x | In-place Pod Resize | v1.10.1 | v1.15.1 | v1.27.16 | Extended |

### Add-on 버전 요구사항

각 EKS 버전에 맞는 Add-on 버전을 사용해야 합니다:

```bash
# 특정 EKS 버전에서 지원되는 Add-on 버전 조회
aws eks describe-addon-versions \
  --kubernetes-version 1.30 \
  --addon-name vpc-cni \
  --query 'addons[0].addonVersions[*].addonVersion' \
  --output table

# 현재 클러스터의 Add-on 버전 확인
aws eks list-addons --cluster-name my-cluster --output table
aws eks describe-addon --cluster-name my-cluster --addon-name vpc-cni \
  --query 'addon.addonVersion'
```

### Kubernetes Deprecation 정책

Kubernetes API는 명확한 사용 중단(deprecation) 정책을 따릅니다:

| API 유형 | 사용 중단 후 제거까지 | 예시 |
|---------|---------------------|------|
| GA (v1) | 12개월 또는 3개 릴리스 | `policy/v1` PodDisruptionBudget |
| Beta (v1beta1) | 9개월 또는 3개 릴리스 | `networking.k8s.io/v1beta1` Ingress |
| Alpha (v1alpha1) | 다음 릴리스에서 변경 가능 | 실험적 기능 |

**주요 Deprecation 이력**:

```yaml
# 1.29에서 제거된 API
- flowcontrol.apiserver.k8s.io/v1beta2 → v1beta3
- autoscaling/v2beta1 HPA → autoscaling/v2

# 1.32에서 제거 예정
- flowcontrol.apiserver.k8s.io/v1beta3 → v1
```

### 업그레이드 타임라인 권장사항

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      업그레이드 타임라인 권장                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  새 버전 출시                                                            │
│      │                                                                  │
│      ├── +30일: Dev/Test 환경 업그레이드 및 테스트                        │
│      │                                                                  │
│      ├── +60일: Staging 환경 업그레이드                                  │
│      │                                                                  │
│      ├── +90일: Production 업그레이드 계획 확정                          │
│      │                                                                  │
│      └── +120일: Production 업그레이드 실행                              │
│                                                                         │
│  EOL 알림 (60일 전)                                                      │
│      │                                                                  │
│      └── Extended Support 시작 전 업그레이드 완료 권장                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 사전 체크리스트

### Deprecated API 탐지 (pluto)

`pluto`는 Kubernetes 매니페스트에서 사용 중단된 API를 탐지하는 도구입니다.

```bash
# pluto 설치
brew install FairwindsOps/tap/pluto
# 또는
curl -L -o pluto.tar.gz \
  https://github.com/FairwindsOps/pluto/releases/latest/download/pluto_linux_amd64.tar.gz
tar -xzf pluto.tar.gz && sudo mv pluto /usr/local/bin/

# 파일 기반 탐지
pluto detect-files -d manifests/
pluto detect-files -d helm-charts/ -o wide

# Helm 릴리스 탐지
pluto detect-helm -o wide
pluto detect-helm --target-versions k8s=v1.30.0

# 클러스터 내 리소스 탐지
pluto detect-api-resources -o wide
pluto detect-api-resources --target-versions k8s=v1.30.0
```

**pluto 출력 예시**:

```
NAME                           KIND                VERSION              REPLACEMENT                    REMOVED   DEPRECATED   REPL AVAIL
ingress-old                    Ingress             extensions/v1beta1   networking.k8s.io/v1           true      true         true
my-pdb                         PodDisruptionBudget policy/v1beta1       policy/v1                      true      true         true
horizontal-pod-autoscaler      HorizontalPodAuto.. autoscaling/v2beta1  autoscaling/v2                 true      true         true
```

### PodDisruptionBudget (PDB) 감사

업그레이드 중 노드 drain이 실패하지 않도록 PDB를 검증합니다.

```bash
# 모든 PDB 상태 확인
kubectl get pdb -A -o wide

# PDB가 disruption을 허용하는지 확인
kubectl get pdb -A -o custom-columns=\
'NAMESPACE:.metadata.namespace,NAME:.metadata.name,MIN-AVAILABLE:.spec.minAvailable,MAX-UNAVAILABLE:.spec.maxUnavailable,ALLOWED-DISRUPTIONS:.status.disruptionsAllowed,CURRENT:.status.currentHealthy,DESIRED:.status.desiredHealthy'
```

**문제가 되는 PDB 패턴**:

```yaml
# 문제: minAvailable이 replicas와 같음 (disruption 불가)
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: blocking-pdb
spec:
  minAvailable: 3  # Deployment replicas도 3이면 drain 불가
  selector:
    matchLabels:
      app: my-app
---
# 권장: maxUnavailable 사용
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: safe-pdb
spec:
  maxUnavailable: 1  # 최소 1개 Pod는 항상 disruption 허용
  selector:
    matchLabels:
      app: my-app
```

```bash
# 문제가 있는 PDB 탐지 스크립트
kubectl get pdb -A -o json | jq -r '
  .items[] |
  select(.status.disruptionsAllowed == 0) |
  "\(.metadata.namespace)/\(.metadata.name): BLOCKED - disruptionsAllowed=0"
'
```

### ETCD 및 애플리케이션 상태 백업

EKS는 컨트롤 플레인(etcd 포함)을 관리하므로 직접 백업은 불필요합니다. 그러나 애플리케이션 상태는 별도로 백업해야 합니다.

```bash
# Velero 설치 확인
velero version

# 백업 스케줄 생성
velero schedule create pre-upgrade-backup \
  --schedule="0 2 * * *" \
  --include-namespaces=default,production \
  --include-resources=deployments,services,configmaps,secrets,pvc

# 업그레이드 전 수동 백업
velero backup create upgrade-$(date +%Y%m%d-%H%M%S) \
  --include-namespaces=default,production \
  --wait

# 백업 상태 확인
velero backup describe upgrade-20250615-100000
velero backup logs upgrade-20250615-100000
```

**Velero 복원 테스트**:

```bash
# 복원 테스트 (dry-run)
velero restore create --from-backup upgrade-20250615-100000 \
  --namespace-mappings default:default-restore-test \
  --dry-run

# 실제 복원 (테스트 네임스페이스로)
velero restore create test-restore \
  --from-backup upgrade-20250615-100000 \
  --namespace-mappings production:production-restore-test

# 복원 결과 확인
velero restore describe test-restore
kubectl get all -n production-restore-test
```

### Add-on 호환성 확인 스크립트

```bash
#!/bin/bash
# addon-compatibility-check.sh

CLUSTER_NAME="${1:-my-cluster}"
TARGET_VERSION="${2:-1.30}"

echo "=== Add-on 호환성 확인: EKS $TARGET_VERSION ==="

# 현재 설치된 Add-on 목록
ADDONS=$(aws eks list-addons --cluster-name $CLUSTER_NAME --query 'addons[]' --output text)

for ADDON in $ADDONS; do
    echo ""
    echo "--- $ADDON ---"

    # 현재 버전
    CURRENT=$(aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name $ADDON \
        --query 'addon.addonVersion' --output text)
    echo "현재 버전: $CURRENT"

    # 대상 버전에서 지원하는 버전들
    echo "EKS $TARGET_VERSION 호환 버전:"
    aws eks describe-addon-versions \
        --kubernetes-version $TARGET_VERSION \
        --addon-name $ADDON \
        --query 'addons[0].addonVersions[*].addonVersion' \
        --output table

    # 호환성 확인
    COMPATIBLE=$(aws eks describe-addon-versions \
        --kubernetes-version $TARGET_VERSION \
        --addon-name $ADDON \
        --query "addons[0].addonVersions[?addonVersion=='$CURRENT'].compatibilities[0].clusterVersion" \
        --output text)

    if [ -z "$COMPATIBLE" ] || [ "$COMPATIBLE" == "None" ]; then
        echo "⚠️  경고: 현재 버전 $CURRENT은 EKS $TARGET_VERSION와 호환되지 않을 수 있습니다"
    else
        echo "✅ 호환됨"
    fi
done
```

### 노드 상태 검증

```bash
#!/bin/bash
# node-health-check.sh

echo "=== 노드 상태 확인 ==="

# 노드 상태 요약
echo ""
echo "--- 노드 상태 ---"
kubectl get nodes -o custom-columns=\
'NAME:.metadata.name,STATUS:.status.conditions[?(@.type=="Ready")].status,VERSION:.status.nodeInfo.kubeletVersion,AGE:.metadata.creationTimestamp'

# NotReady 노드 확인
NOT_READY=$(kubectl get nodes --field-selector status.phase!=Running -o name 2>/dev/null | wc -l)
if [ "$NOT_READY" -gt 0 ]; then
    echo ""
    echo "⚠️  NotReady 노드 발견:"
    kubectl get nodes --field-selector status.phase!=Running
fi

# 노드 조건 확인
echo ""
echo "--- 노드 조건 (문제 있는 항목) ---"
kubectl get nodes -o json | jq -r '
  .items[] |
  .metadata.name as $name |
  .status.conditions[] |
  select(.status == "True" and .type != "Ready") |
  "\($name): \(.type) = \(.status) - \(.message)"
'

# 노드 리소스 압박 확인
echo ""
echo "--- 리소스 압박 상태 ---"
kubectl describe nodes | grep -A5 "Conditions:" | grep -E "(MemoryPressure|DiskPressure|PIDPressure)"
```

### 애플리케이션 상태 검증

```bash
#!/bin/bash
# app-health-check.sh

echo "=== 애플리케이션 상태 확인 ==="

# Pod 상태 요약
echo ""
echo "--- Pod 상태 요약 ---"
kubectl get pods -A --field-selector status.phase!=Running,status.phase!=Succeeded \
  -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,STATUS:.status.phase,RESTARTS:.status.containerStatuses[0].restartCount'

# CrashLoopBackOff 상태 Pod 확인
echo ""
echo "--- CrashLoopBackOff Pod ---"
kubectl get pods -A -o json | jq -r '
  .items[] |
  select(.status.containerStatuses != null) |
  select(.status.containerStatuses[].state.waiting.reason == "CrashLoopBackOff") |
  "\(.metadata.namespace)/\(.metadata.name)"
'

# Deployment 상태
echo ""
echo "--- Deployment 상태 ---"
kubectl get deployments -A -o custom-columns=\
'NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.readyReplicas,DESIRED:.spec.replicas,AVAILABLE:.status.availableReplicas'

# 업그레이드 차단 가능성 있는 리소스
echo ""
echo "--- HPA 상태 ---"
kubectl get hpa -A
```

### 종합 사전 체크 스크립트

```bash
#!/bin/bash
# pre-upgrade-check.sh

set -e

CLUSTER_NAME="${1:-my-cluster}"
TARGET_VERSION="${2:-1.30}"
REPORT_FILE="pre-upgrade-report-$(date +%Y%m%d-%H%M%S).txt"

echo "=== EKS 업그레이드 사전 체크 ===" | tee $REPORT_FILE
echo "클러스터: $CLUSTER_NAME" | tee -a $REPORT_FILE
echo "대상 버전: $TARGET_VERSION" | tee -a $REPORT_FILE
echo "시간: $(date)" | tee -a $REPORT_FILE
echo "" | tee -a $REPORT_FILE

# 1. 현재 클러스터 정보
echo "### 1. 현재 클러스터 정보 ###" | tee -a $REPORT_FILE
CURRENT_VERSION=$(aws eks describe-cluster --name $CLUSTER_NAME \
  --query 'cluster.version' --output text)
echo "현재 버전: $CURRENT_VERSION" | tee -a $REPORT_FILE

# 2. Deprecated API 확인
echo "" | tee -a $REPORT_FILE
echo "### 2. Deprecated API 확인 ###" | tee -a $REPORT_FILE
if command -v pluto &> /dev/null; then
    pluto detect-api-resources --target-versions k8s=v$TARGET_VERSION.0 2>&1 | tee -a $REPORT_FILE
else
    echo "pluto가 설치되지 않음. 설치 후 재실행하세요." | tee -a $REPORT_FILE
fi

# 3. PDB 상태 확인
echo "" | tee -a $REPORT_FILE
echo "### 3. PDB 상태 확인 ###" | tee -a $REPORT_FILE
BLOCKED_PDB=$(kubectl get pdb -A -o json | jq -r '.items[] | select(.status.disruptionsAllowed == 0) | "\(.metadata.namespace)/\(.metadata.name)"')
if [ -n "$BLOCKED_PDB" ]; then
    echo "⚠️  경고: Disruption 불가 PDB 발견:" | tee -a $REPORT_FILE
    echo "$BLOCKED_PDB" | tee -a $REPORT_FILE
else
    echo "✅ 모든 PDB가 disruption 허용" | tee -a $REPORT_FILE
fi

# 4. 노드 상태 확인
echo "" | tee -a $REPORT_FILE
echo "### 4. 노드 상태 확인 ###" | tee -a $REPORT_FILE
NOT_READY_NODES=$(kubectl get nodes --no-headers | grep -v " Ready" | wc -l)
if [ "$NOT_READY_NODES" -gt 0 ]; then
    echo "⚠️  경고: NotReady 노드 $NOT_READY_NODES개 발견" | tee -a $REPORT_FILE
    kubectl get nodes --no-headers | grep -v " Ready" | tee -a $REPORT_FILE
else
    echo "✅ 모든 노드 Ready 상태" | tee -a $REPORT_FILE
fi

# 5. Pod 상태 확인
echo "" | tee -a $REPORT_FILE
echo "### 5. Pod 상태 확인 ###" | tee -a $REPORT_FILE
FAILED_PODS=$(kubectl get pods -A --field-selector status.phase=Failed --no-headers 2>/dev/null | wc -l)
PENDING_PODS=$(kubectl get pods -A --field-selector status.phase=Pending --no-headers 2>/dev/null | wc -l)
echo "Failed Pods: $FAILED_PODS" | tee -a $REPORT_FILE
echo "Pending Pods: $PENDING_PODS" | tee -a $REPORT_FILE

# 6. Add-on 호환성
echo "" | tee -a $REPORT_FILE
echo "### 6. Add-on 호환성 ###" | tee -a $REPORT_FILE
ADDONS=$(aws eks list-addons --cluster-name $CLUSTER_NAME --query 'addons[]' --output text)
for ADDON in $ADDONS; do
    CURRENT=$(aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name $ADDON \
        --query 'addon.addonVersion' --output text)
    echo "$ADDON: $CURRENT" | tee -a $REPORT_FILE
done

# 7. Velero 백업 확인
echo "" | tee -a $REPORT_FILE
echo "### 7. 최근 백업 상태 ###" | tee -a $REPORT_FILE
if command -v velero &> /dev/null; then
    velero backup get --selector '!velero.io/schedule-name' 2>&1 | head -10 | tee -a $REPORT_FILE
else
    echo "Velero가 설치되지 않음" | tee -a $REPORT_FILE
fi

# 최종 결과
echo "" | tee -a $REPORT_FILE
echo "### 최종 결과 ###" | tee -a $REPORT_FILE
if [ "$NOT_READY_NODES" -eq 0 ] && [ -z "$BLOCKED_PDB" ]; then
    echo "✅ 업그레이드 준비 완료" | tee -a $REPORT_FILE
else
    echo "⚠️  업그레이드 전 위 경고 사항 해결 필요" | tee -a $REPORT_FILE
fi

echo ""
echo "리포트 저장됨: $REPORT_FILE"
```

---

## 3. Auto Mode 업그레이드

### Terraform 3-Layer 업그레이드 순서

EKS Auto Mode에서는 Terraform의 3-Layer 구조를 순차적으로 업그레이드합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Auto Mode 업그레이드 순서                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: 02-cluster Layer                                               │
│  ├── cluster_version 변수 업데이트                                       │
│  └── terraform apply → 컨트롤 플레인 업그레이드                          │
│                    │                                                    │
│                    ▼                                                    │
│  Step 2: 대기                                                           │
│  └── 컨트롤 플레인 업그레이드 완료 대기 (~10-15분)                        │
│                    │                                                    │
│                    ▼                                                    │
│  Step 3: 03-platform Layer                                              │
│  ├── Add-on 버전 업데이트                                                │
│  └── terraform apply → Add-on 업그레이드                                │
│                    │                                                    │
│                    ▼                                                    │
│  Step 4: NodePool 자동 교체                                              │
│  └── Karpenter Drift Detection → 노드 자동 교체                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 1: 02-cluster Layer 업데이트

```hcl
# terraform/02-cluster/variables.tf
variable "cluster_version" {
  description = "EKS cluster version"
  type        = string
  default     = "1.30"  # 1.29 → 1.30으로 업데이트
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
}
```

```hcl
# terraform/02-cluster/main.tf
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version  # 변수로 관리

  # Auto Mode 활성화
  cluster_compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }

  vpc_id     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  # 클러스터 업그레이드 설정
  cluster_upgrade_policy = {
    support_type = "STANDARD"  # EXTENDED로 변경 시 추가 비용 발생
  }

  tags = local.common_tags
}
```

```bash
# 클러스터 업그레이드 실행
cd terraform/02-cluster

# Plan 확인
terraform plan -var="cluster_version=1.30"

# Apply 실행
terraform apply -var="cluster_version=1.30"
```

### Step 2: 컨트롤 플레인 업그레이드 대기

```bash
#!/bin/bash
# wait-for-control-plane.sh

CLUSTER_NAME="${1:-my-cluster}"
TARGET_VERSION="${2:-1.30}"

echo "컨트롤 플레인 업그레이드 대기 중..."

while true; do
    STATUS=$(aws eks describe-cluster --name $CLUSTER_NAME \
        --query 'cluster.status' --output text)
    VERSION=$(aws eks describe-cluster --name $CLUSTER_NAME \
        --query 'cluster.version' --output text)

    echo "상태: $STATUS, 버전: $VERSION"

    if [ "$STATUS" == "ACTIVE" ] && [ "$VERSION" == "$TARGET_VERSION" ]; then
        echo "✅ 컨트롤 플레인 업그레이드 완료!"
        break
    fi

    sleep 30
done
```

### Step 3: 03-platform Layer Add-on 업데이트

```hcl
# terraform/03-platform/variables.tf
variable "addon_versions" {
  description = "EKS Add-on versions"
  type = object({
    coredns            = string
    kube_proxy         = string
    vpc_cni            = string
    eks_pod_identity   = string
  })
  default = {
    coredns            = "v1.11.1-eksbuild.11"
    kube_proxy         = "v1.30.6-eksbuild.3"
    vpc_cni            = "v1.18.5-eksbuild.1"
    eks_pod_identity   = "v1.3.4-eksbuild.1"
  }
}
```

```hcl
# terraform/03-platform/addons.tf
resource "aws_eks_addon" "coredns" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  addon_name    = "coredns"
  addon_version = var.addon_versions.coredns

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  configuration_values = jsonencode({
    replicaCount = 2
    resources = {
      limits = {
        cpu    = "100m"
        memory = "150Mi"
      }
      requests = {
        cpu    = "100m"
        memory = "70Mi"
      }
    }
  })
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  addon_name    = "kube-proxy"
  addon_version = var.addon_versions.kube_proxy

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  addon_name    = "vpc-cni"
  addon_version = var.addon_versions.vpc_cni

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  configuration_values = jsonencode({
    enableNetworkPolicy = "true"
    env = {
      ENABLE_PREFIX_DELEGATION = "true"
      WARM_PREFIX_TARGET       = "1"
    }
  })
}

resource "aws_eks_addon" "eks_pod_identity" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  addon_name    = "eks-pod-identity-agent"
  addon_version = var.addon_versions.eks_pod_identity

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

```bash
# Add-on 업그레이드 실행
cd terraform/03-platform
terraform apply
```

### Step 4: NodePool 자동 교체 (Karpenter Drift Detection)

Auto Mode에서는 컨트롤 플레인 업그레이드 후 Karpenter가 자동으로 노드를 교체합니다.

**Drift Detection 동작 원리**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Karpenter Drift Detection                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. 컨트롤 플레인 업그레이드 (1.29 → 1.30)                               │
│                    │                                                    │
│                    ▼                                                    │
│  2. Karpenter가 노드 AMI 버전 확인                                       │
│     - 현재 노드: AMI 1.29                                               │
│     - 최신 AMI: 1.30                                                    │
│                    │                                                    │
│                    ▼                                                    │
│  3. Drift 감지 → 노드에 "Drifted" 상태 표시                              │
│                    │                                                    │
│                    ▼                                                    │
│  4. 새 노드 프로비저닝 (AMI 1.30)                                        │
│                    │                                                    │
│                    ▼                                                    │
│  5. 기존 노드 Cordon → Pod 퇴거 → 노드 종료                             │
│     (PDB 준수)                                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**노드 교체 모니터링**:

```bash
# Drift 상태 확인
kubectl get nodes -L karpenter.sh/nodepool,karpenter.sh/capacity-type

# NodeClaim 상태 확인
kubectl get nodeclaims -o wide

# Drifted 노드 확인
kubectl get nodeclaims -o json | jq -r '
  .items[] |
  select(.status.conditions[] | select(.type == "Drifted" and .status == "True")) |
  "\(.metadata.name): Drifted"
'

# 실시간 노드 교체 모니터링
watch -n 5 'kubectl get nodes -o wide && echo "" && kubectl get nodeclaims -o wide'
```

### Graceful 노드 드레인 프로세스

```yaml
# NodePool 설정에서 disruption 정책 확인
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
      - nodes: "10%"  # 동시에 교체되는 노드 비율 제한
```

```bash
# 노드 드레인 진행 상황 확인
kubectl get events --field-selector reason=DisruptingNode -w

# Pod 퇴거 상황 확인
kubectl get events --field-selector reason=Evicted -w

# 특정 노드의 Pod 확인
NODE_NAME="ip-10-0-1-123.ap-northeast-2.compute.internal"
kubectl get pods -A --field-selector spec.nodeName=$NODE_NAME
```

### 업그레이드 진행 모니터링

```bash
#!/bin/bash
# monitor-upgrade.sh

echo "=== 업그레이드 진행 모니터링 ==="

while true; do
    clear
    echo "시간: $(date)"
    echo ""

    echo "--- 노드 상태 ---"
    kubectl get nodes -o custom-columns=\
'NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion,STATUS:.status.conditions[?(@.type=="Ready")].status,AGE:.metadata.creationTimestamp' \
    | sort -k2

    echo ""
    echo "--- NodeClaim 상태 ---"
    kubectl get nodeclaims -o custom-columns=\
'NAME:.metadata.name,NODEPOOL:.metadata.labels.karpenter\.sh/nodepool,READY:.status.conditions[?(@.type=="Ready")].status,DRIFTED:.status.conditions[?(@.type=="Drifted")].status'

    echo ""
    echo "--- 버전별 노드 수 ---"
    kubectl get nodes -o json | jq -r '
      [.items[].status.nodeInfo.kubeletVersion] |
      group_by(.) |
      map({version: .[0], count: length}) |
      .[] |
      "\(.version): \(.count)개"
    '

    echo ""
    echo "--- 최근 이벤트 ---"
    kubectl get events -A --sort-by='.lastTimestamp' | grep -E "(Drifted|Evicted|DisruptingNode|ProvisionedNode)" | tail -5

    sleep 10
done
```

**Prometheus 쿼리로 업그레이드 상태 확인**:

```promql
# 버전별 노드 수
count by (kubelet_version) (kube_node_info)

# Ready 상태가 아닌 노드 수
count(kube_node_status_condition{condition="Ready", status="false"})

# 최근 생성된 노드 (1시간 이내)
count(time() - kube_node_created < 3600)

# Pending Pod 수
count(kube_pod_status_phase{phase="Pending"})
```

### 업그레이드 중단 처리

```bash
# NodePool disruption 일시 중지
kubectl annotate nodepool default karpenter.sh/do-not-disrupt="true"

# 재개
kubectl annotate nodepool default karpenter.sh/do-not-disrupt-

# 특정 노드 보호
kubectl annotate node ip-10-0-1-123.ap-northeast-2.compute.internal \
  karpenter.sh/do-not-disrupt="true"
```

### 롤백 고려사항

컨트롤 플레인은 롤백이 불가능합니다. 따라서:

1. **업그레이드 전**: 반드시 테스트 환경에서 검증
2. **문제 발생 시**: 블루/그린 전략으로 이전 버전 클러스터로 트래픽 전환
3. **Add-on 롤백**: 이전 버전으로 downgrade 가능

```bash
# Add-on 버전 downgrade (필요시)
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.18.2-eksbuild.1 \
  --resolve-conflicts OVERWRITE
```

---

## 4. 블루/그린 업그레이드

### 전략 개요

블루/그린 업그레이드는 새 버전 클러스터를 기존 클러스터와 병렬로 운영하며 점진적으로 트래픽을 전환하는 전략입니다.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        블루/그린 업그레이드 아키텍처                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                              Route 53                                       │
│                                 │                                           │
│                    ┌────────────┴────────────┐                              │
│                    ▼                         ▼                              │
│              NLB (Blue)                 NLB (Green)                         │
│              Weight: 0%                 Weight: 100%                        │
│                    │                         │                              │
│           ┌───────┴───────┐         ┌───────┴───────┐                      │
│           ▼               ▼         ▼               ▼                      │
│      ┌─────────┐    ┌─────────┐ ┌─────────┐   ┌─────────┐                  │
│      │ EKS 1.29│    │ Nodes   │ │ EKS 1.30│   │ Nodes   │                  │
│      │ (Blue)  │    │         │ │ (Green) │   │         │                  │
│      └─────────┘    └─────────┘ └─────────┘   └─────────┘                  │
│                                                                             │
│      ←── 이전 버전 (유지) ──→   ←── 새 버전 (활성) ──→                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 1: 새 버전 클러스터 생성

```hcl
# terraform/02-cluster-green/variables.tf
variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "my-cluster-green"
}

variable "cluster_version" {
  description = "EKS cluster version"
  type        = string
  default     = "1.30"
}

variable "cluster_color" {
  description = "Cluster color for blue/green deployment"
  type        = string
  default     = "green"
}
```

```hcl
# terraform/02-cluster-green/main.tf
module "eks_green" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  cluster_compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }

  # Blue 클러스터와 동일한 VPC 사용
  vpc_id     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  tags = merge(local.common_tags, {
    "cluster-color" = var.cluster_color
    "eks-version"   = var.cluster_version
  })
}

# ArgoCD 등록을 위한 출력
output "cluster_endpoint" {
  value = module.eks_green.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  value = module.eks_green.cluster_certificate_authority_data
}

output "cluster_name" {
  value = module.eks_green.cluster_name
}
```

```bash
# Green 클러스터 생성
cd terraform/02-cluster-green
terraform init
terraform apply
```

### Step 2: Platform Layer 배포

```bash
# Green 클러스터에 Platform 컴포넌트 배포
cd terraform/03-platform-green
terraform init
terraform apply

# kubeconfig 업데이트
aws eks update-kubeconfig --name my-cluster-green --alias green
```

### Step 3: ArgoCD Hub에 새 클러스터 등록

```bash
# ArgoCD CLI로 Green 클러스터 등록
argocd cluster add green \
  --name my-cluster-green \
  --label env=production \
  --label color=green \
  --label eks-version=1.30

# 또는 Secret으로 등록
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: my-cluster-green
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
    env: production
    color: green
    eks-version: "1.30"
stringData:
  name: my-cluster-green
  server: https://XXXXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com
  config: |
    {
      "execProviderConfig": {
        "command": "argocd-k8s-auth",
        "args": ["aws", "--cluster-name", "my-cluster-green"],
        "apiVersion": "client.authentication.k8s.io/v1beta1"
      },
      "tlsClientConfig": {
        "insecure": false,
        "caData": "LS0tLS1CRUdJTi..."
      }
    }
EOF
```

### Step 4: ArgoCD ApplicationSet 설정

```yaml
# argocd/applicationsets/apps.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: production-apps
  namespace: argocd
spec:
  generators:
    - matrix:
        generators:
          # 클러스터 선택 (label selector)
          - clusters:
              selector:
                matchLabels:
                  env: production
                  # color: green  # 특정 색상만 선택 시
          # 배포할 앱 목록
          - list:
              elements:
                - app: api-server
                  namespace: default
                - app: web-frontend
                  namespace: default
                - app: worker
                  namespace: default
  template:
    metadata:
      name: '{{.app}}-{{.name}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/k8s-manifests.git
        targetRevision: main
        path: 'apps/{{.app}}'
      destination:
        server: '{{.server}}'
        namespace: '{{.namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

```bash
# ApplicationSet 적용
kubectl apply -f argocd/applicationsets/apps.yaml

# 동기화 상태 확인
argocd app list --selector env=production
```

### Step 5: Smoke Test

```bash
#!/bin/bash
# smoke-test.sh

CLUSTER_NAME="${1:-my-cluster-green}"
NAMESPACE="${2:-default}"

echo "=== Smoke Test: $CLUSTER_NAME ==="

# kubeconfig 전환
aws eks update-kubeconfig --name $CLUSTER_NAME

# 1. 노드 상태 확인
echo ""
echo "--- 노드 상태 ---"
kubectl get nodes

# 2. 핵심 Pod 상태 확인
echo ""
echo "--- 핵심 Pod 상태 ---"
kubectl get pods -n kube-system
kubectl get pods -n $NAMESPACE

# 3. 서비스 엔드포인트 확인
echo ""
echo "--- 서비스 엔드포인트 ---"
kubectl get svc -n $NAMESPACE

# 4. HTTP 헬스체크
echo ""
echo "--- HTTP 헬스체크 ---"
API_ENDPOINT=$(kubectl get svc api-server -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
if [ -n "$API_ENDPOINT" ]; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$API_ENDPOINT/health)
    echo "API Server Health: $HTTP_STATUS"
    if [ "$HTTP_STATUS" == "200" ]; then
        echo "✅ API Server 정상"
    else
        echo "❌ API Server 비정상"
        exit 1
    fi
fi

# 5. 데이터베이스 연결 테스트
echo ""
echo "--- DB 연결 테스트 ---"
kubectl exec -n $NAMESPACE deploy/api-server -- \
  curl -s localhost:8080/health/db | jq .

# 6. 메시지 큐 연결 테스트
echo ""
echo "--- MQ 연결 테스트 ---"
kubectl exec -n $NAMESPACE deploy/worker -- \
  curl -s localhost:8080/health/mq | jq .

echo ""
echo "=== Smoke Test 완료 ==="
```

### Step 6: NLB 가중치 전환

```bash
#!/bin/bash
# nlb-weight-shift.sh

BLUE_TG_ARN="arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:targetgroup/blue-tg/xxxxx"
GREEN_TG_ARN="arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:targetgroup/green-tg/xxxxx"
LISTENER_ARN="arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:listener/net/my-nlb/xxxxx/xxxxx"

shift_weight() {
    local BLUE_WEIGHT=$1
    local GREEN_WEIGHT=$2

    echo "트래픽 전환: Blue=$BLUE_WEIGHT%, Green=$GREEN_WEIGHT%"

    aws elbv2 modify-listener \
        --listener-arn $LISTENER_ARN \
        --default-actions Type=forward,ForwardConfig="{
            TargetGroups=[
                {TargetGroupArn=$BLUE_TG_ARN,Weight=$BLUE_WEIGHT},
                {TargetGroupArn=$GREEN_TG_ARN,Weight=$GREEN_WEIGHT}
            ]
        }"
}

# 단계별 전환
echo "=== NLB 가중치 전환 시작 ==="

echo "Step 1: 10% 전환"
shift_weight 90 10
echo "5분 대기 후 메트릭 확인..."
sleep 300

echo "Step 2: 50% 전환"
shift_weight 50 50
echo "5분 대기 후 메트릭 확인..."
sleep 300

echo "Step 3: 90% 전환"
shift_weight 10 90
echo "5분 대기 후 메트릭 확인..."
sleep 300

echo "Step 4: 100% 전환"
shift_weight 0 100

echo "=== 전환 완료 ==="
```

**Terraform으로 NLB 가중치 관리**:

```hcl
# terraform/04-traffic/variables.tf
variable "blue_weight" {
  description = "Traffic weight for blue cluster"
  type        = number
  default     = 0
}

variable "green_weight" {
  description = "Traffic weight for green cluster"
  type        = number
  default     = 100
}
```

```hcl
# terraform/04-traffic/nlb.tf
resource "aws_lb_listener" "app" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "TLS"
  certificate_arn   = var.certificate_arn

  default_action {
    type = "forward"

    forward {
      target_group {
        arn    = aws_lb_target_group.blue.arn
        weight = var.blue_weight
      }

      target_group {
        arn    = aws_lb_target_group.green.arn
        weight = var.green_weight
      }
    }
  }
}
```

```bash
# 가중치 변경
terraform apply -var="blue_weight=50" -var="green_weight=50"
```

### Step 7: 이전 클러스터 제거

```bash
# Blue 클러스터 트래픽이 0%인지 확인
aws elbv2 describe-listeners --listener-arns $LISTENER_ARN \
  --query 'Listeners[0].DefaultActions[0].ForwardConfig.TargetGroups'

# ArgoCD에서 Blue 클러스터 제거
argocd cluster rm my-cluster-blue

# Terraform으로 Blue 클러스터 삭제
cd terraform/02-cluster-blue
terraform destroy

# 정리 완료 확인
aws eks list-clusters
```

### 롤백 절차

문제 발생 시 트래픽을 다시 Blue로 전환합니다.

```bash
#!/bin/bash
# rollback.sh

echo "=== 롤백 시작 ==="

# 즉시 Blue로 100% 전환
aws elbv2 modify-listener \
    --listener-arn $LISTENER_ARN \
    --default-actions Type=forward,ForwardConfig="{
        TargetGroups=[
            {TargetGroupArn=$BLUE_TG_ARN,Weight=100},
            {TargetGroupArn=$GREEN_TG_ARN,Weight=0}
        ]
    }"

echo "트래픽이 Blue 클러스터로 전환되었습니다."

# 롤백 원인 분석을 위한 로그 수집
kubectl --context=green logs -n kube-system -l app=coredns --tail=100 > rollback-coredns.log
kubectl --context=green get events -A --sort-by='.lastTimestamp' > rollback-events.log

echo "=== 롤백 완료 ==="
```

### Stateful 워크로드 마이그레이션

데이터베이스 등 상태가 있는 워크로드는 별도 마이그레이션이 필요합니다.

```bash
# PVC 데이터 마이그레이션 (Velero 사용)

# Blue 클러스터에서 백업
velero backup create stateful-migration \
  --include-namespaces=database \
  --include-resources=pvc,pv \
  --snapshot-volumes

# Green 클러스터에서 복원
velero restore create stateful-migration-restore \
  --from-backup stateful-migration \
  --include-namespaces=database

# 데이터 정합성 확인
kubectl --context=green exec -n database deploy/postgres -- \
  psql -U postgres -c "SELECT count(*) FROM important_table;"
```

---

## 5. 사후 검증

### 종합 헬스체크 스크립트

```bash
#!/bin/bash
# post-upgrade-check.sh

CLUSTER_NAME="${1:-my-cluster}"

echo "=== 업그레이드 사후 검증: $CLUSTER_NAME ==="
echo "시간: $(date)"
echo ""

# 1. 노드 상태 검증
echo "### 1. 노드 상태 ###"
echo ""

# 모든 노드 Ready 확인
NOT_READY=$(kubectl get nodes --no-headers | grep -v " Ready" | wc -l)
if [ "$NOT_READY" -gt 0 ]; then
    echo "❌ NotReady 노드 발견: $NOT_READY개"
    kubectl get nodes | grep -v " Ready"
else
    echo "✅ 모든 노드 Ready"
fi

# 노드 버전 일관성 확인
echo ""
echo "노드 버전 분포:"
kubectl get nodes -o json | jq -r '
  [.items[].status.nodeInfo.kubeletVersion] |
  group_by(.) |
  map({version: .[0], count: length}) |
  .[] |
  "  \(.version): \(.count)개"
'

# 2. Pod 상태 검증
echo ""
echo "### 2. Pod 상태 ###"
echo ""

# 전체 Pod 상태 요약
TOTAL_PODS=$(kubectl get pods -A --no-headers | wc -l)
RUNNING_PODS=$(kubectl get pods -A --no-headers | grep " Running" | wc -l)
COMPLETED_PODS=$(kubectl get pods -A --no-headers | grep " Completed\| Succeeded" | wc -l)
PENDING_PODS=$(kubectl get pods -A --field-selector status.phase=Pending --no-headers 2>/dev/null | wc -l)
FAILED_PODS=$(kubectl get pods -A --field-selector status.phase=Failed --no-headers 2>/dev/null | wc -l)

echo "  전체: $TOTAL_PODS"
echo "  Running: $RUNNING_PODS"
echo "  Completed/Succeeded: $COMPLETED_PODS"
echo "  Pending: $PENDING_PODS"
echo "  Failed: $FAILED_PODS"

if [ "$PENDING_PODS" -gt 0 ] || [ "$FAILED_PODS" -gt 0 ]; then
    echo ""
    echo "⚠️  문제 Pod 목록:"
    kubectl get pods -A --field-selector 'status.phase!=Running,status.phase!=Succeeded' \
      -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,STATUS:.status.phase'
fi

# 3. 서비스 엔드포인트 검증
echo ""
echo "### 3. 서비스 엔드포인트 ###"
echo ""

# 엔드포인트가 없는 서비스 확인
kubectl get endpoints -A -o json | jq -r '
  .items[] |
  select(.subsets == null or .subsets == []) |
  "\(.metadata.namespace)/\(.metadata.name): No endpoints"
' | while read line; do
    if [ -n "$line" ]; then
        echo "⚠️  $line"
    fi
done

# 4. Ingress/LoadBalancer 검증
echo ""
echo "### 4. Ingress/LoadBalancer ###"
echo ""

# LoadBalancer 타입 서비스 확인
kubectl get svc -A -o json | jq -r '
  .items[] |
  select(.spec.type == "LoadBalancer") |
  "\(.metadata.namespace)/\(.metadata.name): \(.status.loadBalancer.ingress[0].hostname // "Pending")"
'

# 5. 핵심 시스템 컴포넌트 확인
echo ""
echo "### 5. 시스템 컴포넌트 ###"
echo ""

COMPONENTS=("coredns" "kube-proxy" "vpc-cni" "eks-pod-identity-agent")
for COMP in "${COMPONENTS[@]}"; do
    STATUS=$(kubectl get pods -n kube-system -l "k8s-app=$COMP" -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    if [ "$STATUS" == "Running" ]; then
        echo "✅ $COMP: Running"
    else
        echo "❌ $COMP: $STATUS"
    fi
done

# 6. Add-on 버전 확인
echo ""
echo "### 6. Add-on 버전 ###"
echo ""

aws eks list-addons --cluster-name $CLUSTER_NAME --query 'addons[]' --output text | while read ADDON; do
    VERSION=$(aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name $ADDON \
        --query 'addon.addonVersion' --output text)
    STATUS=$(aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name $ADDON \
        --query 'addon.status' --output text)
    echo "  $ADDON: $VERSION ($STATUS)"
done

echo ""
echo "=== 검증 완료 ==="
```

### Smoke Test 예시

```bash
#!/bin/bash
# smoke-test-detailed.sh

NAMESPACE="${1:-default}"
BASE_URL="${2:-http://localhost:8080}"

echo "=== Smoke Test ==="

# HTTP 엔드포인트 체크
test_endpoint() {
    local NAME=$1
    local URL=$2
    local EXPECTED=$3

    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$URL" --max-time 10)
    if [ "$RESPONSE" == "$EXPECTED" ]; then
        echo "✅ $NAME: $RESPONSE"
        return 0
    else
        echo "❌ $NAME: Expected $EXPECTED, Got $RESPONSE"
        return 1
    fi
}

echo ""
echo "--- HTTP 엔드포인트 ---"
test_endpoint "Health" "$BASE_URL/health" "200"
test_endpoint "Ready" "$BASE_URL/ready" "200"
test_endpoint "API Root" "$BASE_URL/api/v1" "200"

# 데이터베이스 연결
echo ""
echo "--- 데이터베이스 연결 ---"
DB_CHECK=$(kubectl exec -n $NAMESPACE deploy/api-server -- \
  curl -s localhost:8080/health/db 2>/dev/null | jq -r '.status')
if [ "$DB_CHECK" == "healthy" ]; then
    echo "✅ Database: Connected"
else
    echo "❌ Database: $DB_CHECK"
fi

# Redis/Cache 연결
echo ""
echo "--- Cache 연결 ---"
CACHE_CHECK=$(kubectl exec -n $NAMESPACE deploy/api-server -- \
  curl -s localhost:8080/health/cache 2>/dev/null | jq -r '.status')
if [ "$CACHE_CHECK" == "healthy" ]; then
    echo "✅ Cache: Connected"
else
    echo "❌ Cache: $CACHE_CHECK"
fi

# 메시지 큐 연결
echo ""
echo "--- Message Queue ---"
MQ_CHECK=$(kubectl exec -n $NAMESPACE deploy/worker -- \
  curl -s localhost:8080/health/mq 2>/dev/null | jq -r '.status')
if [ "$MQ_CHECK" == "healthy" ]; then
    echo "✅ Message Queue: Connected"
else
    echo "❌ Message Queue: $MQ_CHECK"
fi

echo ""
echo "=== Smoke Test 완료 ==="
```

### 메트릭 비교 (Before/After)

```promql
# 에러율 비교 (Before: 1시간 전 ~ 30분 전, After: 최근 30분)

# Before 에러율
sum(rate(http_requests_total{status=~"5.."}[30m] offset 1h))
/
sum(rate(http_requests_total[30m] offset 1h))

# After 에러율
sum(rate(http_requests_total{status=~"5.."}[30m]))
/
sum(rate(http_requests_total[30m]))

# 레이턴시 비교 (P99)

# Before P99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[30m] offset 1h))

# After P99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[30m]))

# 리소스 사용률 비교

# Before CPU 사용률
avg(rate(container_cpu_usage_seconds_total{namespace="default"}[30m] offset 1h))

# After CPU 사용률
avg(rate(container_cpu_usage_seconds_total{namespace="default"}[30m]))

# Before Memory 사용률
avg(container_memory_working_set_bytes{namespace="default"} offset 1h)

# After Memory 사용률
avg(container_memory_working_set_bytes{namespace="default"})
```

**Grafana 대시보드 쿼리 예시**:

```yaml
# grafana-dashboard-upgrade-comparison.yaml
panels:
  - title: "Error Rate Comparison"
    type: timeseries
    targets:
      - expr: |
          sum(rate(http_requests_total{status=~"5.."}[$__rate_interval]))
          /
          sum(rate(http_requests_total[$__rate_interval]))
        legendFormat: "Current"
      - expr: |
          sum(rate(http_requests_total{status=~"5.."}[$__rate_interval] offset 2h))
          /
          sum(rate(http_requests_total[$__rate_interval] offset 2h))
        legendFormat: "Before Upgrade (2h ago)"

  - title: "P99 Latency Comparison"
    type: timeseries
    targets:
      - expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[$__rate_interval])) by (le)
          )
        legendFormat: "Current P99"
      - expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[$__rate_interval] offset 2h)) by (le)
          )
        legendFormat: "Before Upgrade P99"
```

### 사후 모니터링 기간

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        사후 모니터링 권장 기간                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  업그레이드 완료                                                          │
│        │                                                                │
│        ├── 0-1시간: 집중 모니터링                                        │
│        │   - 에러율, 레이턴시 급증 감시                                   │
│        │   - 핵심 서비스 헬스체크 연속 실행                               │
│        │                                                                │
│        ├── 1-4시간: 정상 모니터링                                        │
│        │   - 알림 임계값 민감도 상향 유지                                 │
│        │   - 주기적 메트릭 확인                                          │
│        │                                                                │
│        ├── 4-24시간: 표준 모니터링                                       │
│        │   - 일일 트래픽 패턴 완전 경과                                   │
│        │   - 배치 작업 정상 완료 확인                                     │
│        │                                                                │
│        └── 24-72시간: 안정화 확인                                        │
│            - 주간 패턴까지 모니터링 (주말 트래픽 포함)                     │
│            - 업그레이드 완료 선언                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 운영 문서 업데이트

업그레이드 완료 후 다음 문서를 업데이트합니다:

```markdown
# 클러스터 버전 이력

| 날짜 | 이전 버전 | 새 버전 | 담당자 | 비고 |
|------|----------|--------|--------|------|
| 2025-06-15 | 1.29 | 1.30 | DevOps팀 | Auto Mode 업그레이드, 무중단 완료 |
| 2025-03-10 | 1.28 | 1.29 | DevOps팀 | 블루/그린 전략 사용 |

# Add-on 버전 현황

| Add-on | 버전 | 최종 업데이트 |
|--------|------|--------------|
| CoreDNS | v1.11.1-eksbuild.11 | 2025-06-15 |
| kube-proxy | v1.30.6-eksbuild.3 | 2025-06-15 |
| VPC CNI | v1.18.5-eksbuild.1 | 2025-06-15 |
| EKS Pod Identity | v1.3.4-eksbuild.1 | 2025-06-15 |

# 알려진 이슈

- 없음

# 다음 업그레이드 예정

- 2025년 9월: EKS 1.31 업그레이드 예정
- 사전 체크 시작: 2025년 8월
```

---

## 참고 자료

- [EKS 업그레이드 개념](../eks/08-eks-upgrades.md)
- [노드 생명주기 관리](../eks-auto-mode/07-node-lifecycle.md)
- [AWS EKS 업그레이드 모범 사례](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Kubernetes 버전 스큐 정책](https://kubernetes.io/releases/version-skew-policy/)
- [pluto - Deprecated API 탐지 도구](https://github.com/FairwindsOps/pluto)
- [Velero - Kubernetes 백업/복원](https://velero.io/docs/)

---

< [이전: 리소스 최적화](./10-resource-optimization.md) | [목차](./README.md) | [다음: 없음] >
