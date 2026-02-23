# 노드 라이프사이클 관리

< [이전: 워크로드 배치 전략](./06-workload-placement.md) | [목차](./README.md) | [다음: 운영 및 유지보수](./08-operations.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+
> **마지막 업데이트**: 2026년 2월 22일

이 문서에서는 EKS Hybrid Nodes의 nodeadm 고급 설정, 대규모 노드 설치 자동화, 업그레이드 전략, 자격 증명 관리 및 헬스체크 자동화를 다룹니다.

## 1. nodeadm 고급 설정 (Advanced NodeConfig)

### kubelet 튜닝

프로덕션 환경에서는 kubelet의 리소스 예약, 축출 임계값, 이미지 가비지 컬렉션 등을 세밀하게 조정해야 합니다.

#### 리소스 예약 (system-reserved / kube-reserved)

시스템 프로세스와 Kubernetes 컴포넌트를 위한 리소스를 예약하여 파드가 노드 전체 리소스를 소모하지 않도록 합니다.

```yaml
kubelet:
  config:
    systemReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "10Gi"
    kubeReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "5Gi"
```

| 파라미터 | 설명 | 권장값 |
|----------|------|--------|
| `systemReserved.cpu` | OS 및 시스템 데몬용 CPU | 500m ~ 1000m |
| `systemReserved.memory` | OS 및 시스템 데몬용 메모리 | 1Gi ~ 2Gi |
| `kubeReserved.cpu` | kubelet, containerd용 CPU | 500m ~ 1000m |
| `kubeReserved.memory` | kubelet, containerd용 메모리 | 1Gi ~ 2Gi |

#### 축출 임계값 (Eviction Thresholds)

노드 리소스가 부족할 때 파드를 자동으로 축출하여 노드 안정성을 유지합니다.

```yaml
kubelet:
  config:
    evictionHard:
      memory.available: "200Mi"
      nodefs.available: "10%"
      imagefs.available: "15%"
      nodefs.inodesFree: "5%"
    evictionSoft:
      memory.available: "500Mi"
      nodefs.available: "15%"
    evictionSoftGracePeriod:
      memory.available: "1m30s"
      nodefs.available: "2m"
```

> **참고**: `evictionHard`는 즉시 축출, `evictionSoft`는 유예 기간 후 축출됩니다. Soft 임계값을 먼저 설정하면 갑작스러운 파드 종료를 방지할 수 있습니다.

#### maxPods 계산

노드 리소스 기반으로 적절한 `maxPods` 값을 설정합니다. Cilium IPAM을 사용하는 하이브리드 노드에서는 `clusterPoolIPv4MaskSize`로 할당되는 IP 수를 고려해야 합니다.

```yaml
kubelet:
  config:
    maxPods: 110  # /25 마스크 = 128 IP 중 사용 가능한 수
```

| 마스크 크기 | IP 수 | 권장 maxPods |
|-------------|-------|-------------|
| /25 | 128 | 110 |
| /24 | 256 | 240 |
| /26 | 64 | 50 |

#### 이미지 가비지 컬렉션

디스크 공간 관리를 위해 미사용 이미지를 자동으로 정리합니다.

```yaml
kubelet:
  config:
    imageGCHighThresholdPercent: 85
    imageGCLowThresholdPercent: 80
    imageMinimumGCAge: "2m"
```

#### 셧다운 그레이스 기간

노드 셧다운 시 파드를 정상적으로 종료하기 위한 유예 기간을 설정합니다.

```yaml
kubelet:
  config:
    shutdownGracePeriod: 60s
    shutdownGracePeriodCriticalPods: 20s
```

> **참고**: `shutdownGracePeriodCriticalPods`는 `shutdownGracePeriod` 내에 포함되어야 합니다. 일반 파드는 `60s - 20s = 40s` 동안 종료 유예를 받습니다.

### containerd 고급 설정

#### 프라이빗 레지스트리 미러 설정

프라이빗 레지스트리를 미러로 사용하여 이미지 풀 속도를 개선하고 외부 네트워크 의존성을 줄입니다.

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = "/etc/containerd/certs.d"
```

`hosts.toml` 파일을 통해 레지스트리별 미러를 구성합니다:

```bash
# /etc/containerd/certs.d/docker.io/hosts.toml
sudo mkdir -p /etc/containerd/certs.d/docker.io
cat <<EOF | sudo tee /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"

[host."https://harbor.internal.company.io/v2/dockerhub-proxy"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
  override_path = true
EOF
```

#### GPU 노드용 NVIDIA 런타임 클래스

GPU 워크로드를 위해 NVIDIA Container Runtime을 기본 런타임으로 설정합니다.

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".containerd]
      default_runtime_name = "nvidia"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
      privileged_without_host_devices = false
      runtime_engine = ""
      runtime_root = ""
      runtime_type = "io.containerd.runc.v2"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
      BinaryName = "/usr/bin/nvidia-container-runtime"
      SystemdCgroup = true
```

### 레이블 및 테인트 전략

#### nodeadm 자동 레이블

nodeadm은 하이브리드 노드를 초기화할 때 다음 레이블을 자동으로 부여합니다:

```
eks.amazonaws.com/compute-type=hybrid
```

이 레이블은 `--node-labels` 플래그에 수동으로 추가할 필요가 없습니다.

#### 추가 커스텀 레이블 전략

용도별, 환경별로 추가 레이블을 부여하여 워크로드 배치를 세밀하게 제어합니다.

```yaml
kubelet:
  flags:
    # 용도별 레이블
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training

    # 환경별 레이블 (프로덕션)
    # - --node-labels=environment=production,tier=compute

    # 데이터센터 위치별 레이블
    # - --node-labels=datacenter=dc-seoul-01,rack=rack-a3
```

#### 테인트 전략

| 전략 | 설명 | 사용 사례 |
|------|------|-----------|
| 자동 테인트 (NodeConfig) | nodeadm 초기화 시 적용 | 모든 하이브리드 노드에 공통 적용 |
| 수동 테인트 (kubectl) | 운영 중 동적으로 적용 | GPU 노드 격리, 유지보수 모드 |

```yaml
# NodeConfig에서 자동 테인트
kubelet:
  flags:
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
```

```bash
# 운영 중 수동 테인트 추가
kubectl taint nodes hybrid-gpu-001 gpu=true:NoSchedule
kubectl taint nodes hybrid-node-005 maintenance=true:NoExecute
```

### 전체 NodeConfig 예시 (프로덕션급)

kubelet, containerd, 레이블, 테인트를 모두 포함하는 프로덕션 환경용 설정입니다.

```yaml
# production-nodeconfig.yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: prod-hybrid-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://XXXXXXXXXXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com
    certificateAuthority: |
      -----BEGIN CERTIFICATE-----
      MIIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      -----END CERTIFICATE-----
    cidr: 10.100.0.0/16

  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>

  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 60s
      shutdownGracePeriodCriticalPods: 20s
      systemReserved:
        cpu: "500m"
        memory: "1Gi"
        ephemeral-storage: "10Gi"
      kubeReserved:
        cpu: "500m"
        memory: "1Gi"
        ephemeral-storage: "5Gi"
      evictionHard:
        memory.available: "200Mi"
        nodefs.available: "10%"
        imagefs.available: "15%"
      evictionSoft:
        memory.available: "500Mi"
        nodefs.available: "15%"
      evictionSoftGracePeriod:
        memory.available: "1m30s"
        nodefs.available: "2m"
      imageGCHighThresholdPercent: 85
      imageGCLowThresholdPercent: 80
    flags:
      - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training
      - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule

  containerd:
    config: |
      version = 2
      [plugins."io.containerd.grpc.v1.cri".registry]
        config_path = "/etc/containerd/certs.d"
```

---

## 2. 대규모 노드 설치 자동화 (Fleet Installation)

### Ansible Playbook

대규모 환경에서는 Ansible을 사용하여 다수의 노드를 일괄 설치합니다.

#### 인벤토리 구성

```ini
# inventory/hosts.ini
[hybrid_nodes:children]
gpu_nodes
cpu_nodes

[gpu_nodes]
hybrid-gpu-001 ansible_host=192.168.1.101
hybrid-gpu-002 ansible_host=192.168.1.102
hybrid-gpu-003 ansible_host=192.168.1.103

[cpu_nodes]
hybrid-cpu-001 ansible_host=192.168.1.201
hybrid-cpu-002 ansible_host=192.168.1.202

[hybrid_nodes:vars]
ansible_user=admin
ansible_become=yes
eks_version=1.31
cluster_name=prod-hybrid-cluster
region=ap-northeast-2
```

#### 자동화 플레이북

```yaml
# playbooks/install-hybrid-nodes.yaml
---
- name: Install EKS Hybrid Nodes
  hosts: hybrid_nodes
  become: yes
  vars:
    nodeadm_url_amd64: "https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm"
    nodeadm_url_arm64: "https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/arm64/nodeadm"
    credential_provider: "ssm"

  tasks:
    - name: Download nodeadm
      get_url:
        url: "{{ nodeadm_url_amd64 }}"
        dest: /usr/local/bin/nodeadm
        mode: '0755'

    - name: Install dependencies
      command: nodeadm install {{ eks_version }} --credential-provider {{ credential_provider }}
      args:
        creates: /usr/bin/kubelet

    - name: Copy NodeConfig
      template:
        src: "templates/nodeconfig-{{ group_names[0] }}.yaml.j2"
        dest: /etc/eks/nodeconfig.yaml
        mode: '0600'

    - name: Initialize node
      command: nodeadm init -c file:///etc/eks/nodeconfig.yaml
      register: init_result
      failed_when: init_result.rc != 0

    - name: Verify kubelet is running
      systemd:
        name: kubelet
        state: started
        enabled: yes
```

#### 롤별 변수 (GPU 노드 vs 일반 노드)

```yaml
# group_vars/gpu_nodes.yml
node_labels: "node.kubernetes.io/instance-type=on-prem-gpu,nvidia.com/gpu.present=true"
node_taints: "eks.amazonaws.com/compute-type=hybrid:NoSchedule,gpu=true:NoSchedule"
containerd_runtime: "nvidia"

# group_vars/cpu_nodes.yml
node_labels: "node.kubernetes.io/instance-type=on-prem-cpu"
node_taints: "eks.amazonaws.com/compute-type=hybrid:NoSchedule"
containerd_runtime: "runc"
```

### 설치 검증 스크립트

```bash
#!/bin/bash
# verify-fleet.sh - 전체 노드 설치 검증

echo "=== 플릿 설치 검증 ==="

# 1. 노드 Ready 상태 확인
echo ""
echo "1. 노드 상태 확인"
NOT_READY=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  --no-headers | grep -v "Ready" | wc -l)
TOTAL=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  --no-headers | wc -l)
echo "   전체: ${TOTAL}개, NotReady: ${NOT_READY}개"

if [ "$NOT_READY" -gt 0 ]; then
    echo "   [WARN] NotReady 노드 목록:"
    kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
      --no-headers | grep -v "Ready"
fi

# 2. CNI 연결 검증
echo ""
echo "2. Cilium 상태 확인"
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium \
  --no-headers | while read line; do
    STATUS=$(echo $line | awk '{print $3}')
    if [ "$STATUS" != "Running" ]; then
        echo "   [WARN] Cilium 파드 비정상: $line"
    fi
done
echo "   Cilium 파드 수: $(kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium --no-headers | wc -l)"

# 3. 레이블/테인트 일괄 확인
echo ""
echo "3. 레이블 확인"
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o custom-columns='NAME:.metadata.name,LABELS:.metadata.labels' --no-headers

echo ""
echo "4. 테인트 확인"
for NODE in $(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o jsonpath='{.items[*].metadata.name}'); do
    TAINTS=$(kubectl get node $NODE -o jsonpath='{.spec.taints[*].key}')
    echo "   $NODE: $TAINTS"
done

echo ""
echo "=== 검증 완료 ==="
```

---

## 3. 노드 업그레이드 전략 (Upgrade Strategies)

### 버전 스큐 정책

Kubernetes는 kubelet과 API 서버 간 엄격한 버전 호환성 정책을 유지합니다.

| kubelet 버전 | API 서버 버전 | 호환 여부 |
|-------------|-------------|----------|
| 1.31 | 1.31 | ✅ 동일 버전 |
| 1.30 | 1.31 | ✅ n-1 |
| 1.29 | 1.31 | ✅ n-2 |
| 1.28 | 1.31 | ✅ n-3 |
| 1.27 | 1.31 | ❌ n-4 (미지원) |
| 1.32 | 1.31 | ❌ kubelet > API 서버 (미지원) |

> **중요**: 업그레이드 순서는 반드시 **컨트롤 플레인(EKS) → 노드** 순입니다. 노드를 컨트롤 플레인보다 먼저 업그레이드하면 호환성 문제가 발생합니다.

### 업그레이드 사전 체크리스트

업그레이드 전 다음 항목을 확인하세요:

```bash
#!/bin/bash
# pre-upgrade-check.sh

echo "=== 업그레이드 사전 체크리스트 ==="

# 1. PDB 확인
echo "1. PodDisruptionBudget 확인"
kubectl get pdb --all-namespaces -o custom-columns=\
'NAMESPACE:.metadata.namespace,NAME:.metadata.name,MIN-AVAILABLE:.spec.minAvailable,MAX-UNAVAILABLE:.spec.maxUnavailable,ALLOWED-DISRUPTIONS:.status.disruptionsAllowed'

# 2. 노드 용량 확인
echo ""
echo "2. 노드별 리소스 사용량"
kubectl top nodes -l eks.amazonaws.com/compute-type=hybrid

# 3. 실행 중인 파드 확인
echo ""
echo "3. 하이브리드 노드별 파드 수"
for NODE in $(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o jsonpath='{.items[*].metadata.name}'); do
    POD_COUNT=$(kubectl get pods --all-namespaces --field-selector spec.nodeName=$NODE \
      --no-headers | wc -l)
    echo "   $NODE: ${POD_COUNT}개 파드"
done

# 4. 현재 버전 확인
echo ""
echo "4. 현재 노드 버전"
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o custom-columns='NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion'
```

### 롤링 업그레이드

N개 노드를 순차적으로 업그레이드하여 서비스 중단을 최소화합니다.

```bash
#!/bin/bash
# rolling-upgrade.sh - 롤링 업그레이드 스크립트
set -euo pipefail

TARGET_VERSION="${1:?Usage: $0 <target-version> [max-unavailable]}"
MAX_UNAVAILABLE="${2:-1}"
NODECONFIG="/etc/eks/nodeconfig.yaml"

NODES=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o jsonpath='{.items[*].metadata.name}')

TOTAL=$(echo $NODES | wc -w)
CURRENT=0

echo "=== 롤링 업그레이드 시작 ==="
echo "대상 버전: $TARGET_VERSION"
echo "전체 노드: $TOTAL"
echo "최대 동시 불가용: $MAX_UNAVAILABLE"

for NODE in $NODES; do
    CURRENT=$((CURRENT + 1))
    echo ""
    echo "[$CURRENT/$TOTAL] 노드 업그레이드: $NODE"

    # 1. Cordon
    echo "  → Cordon"
    kubectl cordon $NODE

    # 2. Drain
    echo "  → Drain"
    kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data \
      --grace-period=120 --timeout=300s

    # 3. 원격 업그레이드 실행 (SSH)
    echo "  → nodeadm upgrade 실행"
    ssh $NODE "sudo nodeadm upgrade $TARGET_VERSION -c file://$NODECONFIG"

    # 4. 노드 Ready 대기
    echo "  → Ready 상태 대기"
    kubectl wait --for=condition=Ready node/$NODE --timeout=300s

    # 5. Uncordon
    echo "  → Uncordon"
    kubectl uncordon $NODE

    echo "  ✓ $NODE 업그레이드 완료"
done

echo ""
echo "=== 롤링 업그레이드 완료 ==="
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o custom-columns='NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion,STATUS:.status.conditions[-1].type'
```

### 카나리 업그레이드

안전을 위해 1개 노드를 먼저 업그레이드하고 검증한 후 나머지를 진행합니다.

```bash
#!/bin/bash
# canary-upgrade.sh - 카나리 업그레이드 스크립트
set -euo pipefail

TARGET_VERSION="${1:?Usage: $0 <target-version>}"
NODECONFIG="/etc/eks/nodeconfig.yaml"

# 카나리 노드 선택 (첫 번째 하이브리드 노드)
CANARY_NODE=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o jsonpath='{.items[0].metadata.name}')

echo "=== 카나리 업그레이드 ==="
echo "카나리 노드: $CANARY_NODE"
echo "대상 버전: $TARGET_VERSION"

# 카나리 노드 업그레이드
kubectl cordon $CANARY_NODE
kubectl drain $CANARY_NODE --ignore-daemonsets --delete-emptydir-data \
  --grace-period=120 --timeout=300s
ssh $CANARY_NODE "sudo nodeadm upgrade $TARGET_VERSION -c file://$NODECONFIG"
kubectl wait --for=condition=Ready node/$CANARY_NODE --timeout=300s
kubectl uncordon $CANARY_NODE

echo ""
echo "카나리 노드 업그레이드 완료. 검증을 진행하세요."
echo "카나리 노드 상태:"
kubectl describe node $CANARY_NODE | head -20

echo ""
read -p "나머지 노드를 업그레이드하시겠습니까? (y/N): " CONFIRM
if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
    echo "나머지 노드 롤링 업그레이드를 시작합니다..."
    # 카나리 노드를 제외한 나머지 노드
    REMAINING_NODES=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
      -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | grep -v $CANARY_NODE)

    for NODE in $REMAINING_NODES; do
        echo "업그레이드: $NODE"
        kubectl cordon $NODE
        kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data \
          --grace-period=120 --timeout=300s
        ssh $NODE "sudo nodeadm upgrade $TARGET_VERSION -c file://$NODECONFIG"
        kubectl wait --for=condition=Ready node/$NODE --timeout=300s
        kubectl uncordon $NODE
        echo "  ✓ $NODE 완료"
    done
fi

echo "=== 업그레이드 완료 ==="
```

### 롤백 절차

업그레이드 실패 시 이전 버전으로 복원하는 절차입니다.

```bash
#!/bin/bash
# rollback-node.sh - 노드 롤백 스크립트

NODE="${1:?Usage: $0 <node-name> <previous-version>}"
PREV_VERSION="${2:?Usage: $0 <node-name> <previous-version>}"
CREDENTIAL_PROVIDER="${3:-ssm}"
NODECONFIG="/etc/eks/nodeconfig.yaml"

echo "=== 노드 롤백: $NODE → v$PREV_VERSION ==="

# 1. Cordon & Drain
kubectl cordon $NODE
kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data --timeout=300s

# 2. 노드에서 uninstall → install → init
ssh $NODE << REMOTE_SCRIPT
  sudo nodeadm uninstall
  sudo rm -rf /var/lib/kubelet /etc/kubernetes
  sudo nodeadm install $PREV_VERSION --credential-provider $CREDENTIAL_PROVIDER
  sudo nodeadm init -c file://$NODECONFIG
REMOTE_SCRIPT

# 3. Ready 상태 대기
kubectl wait --for=condition=Ready node/$NODE --timeout=300s

# 4. Uncordon
kubectl uncordon $NODE

echo "=== 롤백 완료 ==="
kubectl get node $NODE -o custom-columns='NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion'
```

---

## 4. 자격 증명 라이프사이클 (Credential Lifecycle)

### SSM Hybrid Activation 갱신

SSM Hybrid Activation은 생성 시 설정한 만료일이 있으며, 만료 전에 새로운 활성화를 생성해야 합니다.

```bash
#!/bin/bash
# renew-ssm-activation.sh

# 현재 SSM 관리형 인스턴스 확인
aws ssm describe-instance-information \
  --filters "Key=ResourceType,Values=ManagedInstance" \
  --query 'InstanceInformationList[*].[InstanceId,ComputerName,RegistrationDate]' \
  --output table

# 새 활성화 생성
NEW_ACTIVATION=$(aws ssm create-activation \
  --default-instance-name "eks-hybrid-node" \
  --iam-role "service-role/AmazonEC2RunCommandRoleForManagedInstances" \
  --registration-limit 100 \
  --expiration-date "$(date -d '+30 days' --iso-8601=seconds)" \
  --region ap-northeast-2 \
  --output json)

echo "새 활성화 코드: $(echo $NEW_ACTIVATION | jq -r '.ActivationCode')"
echo "새 활성화 ID: $(echo $NEW_ACTIVATION | jq -r '.ActivationId')"
echo ""
echo "nodeconfig.yaml의 activationCode/activationId를 업데이트하세요."
```

노드 재등록이 필요한 경우:

```bash
# 기존 노드에서 재등록
sudo nodeadm uninstall
# nodeconfig.yaml에 새 activationCode/activationId 적용 후
sudo nodeadm init -c file://nodeconfig.yaml
```

### IAM Roles Anywhere 인증서 갱신

IAM Roles Anywhere를 사용하는 경우, 노드 인증서 만료 전에 갱신해야 합니다.

#### 인증서 만료 모니터링

```bash
#!/bin/bash
# check-cert-expiry.sh - 노드 인증서 만료 확인

CERT_PATH="/etc/iam/pki/server.pem"
WARNING_DAYS=30

if [ -f "$CERT_PATH" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in $CERT_PATH | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    echo "인증서: $CERT_PATH"
    echo "만료일: $EXPIRY"
    echo "남은 일수: ${DAYS_LEFT}일"

    if [ $DAYS_LEFT -lt $WARNING_DAYS ]; then
        echo "[WARN] 인증서 갱신이 필요합니다!"
        exit 1
    fi
fi
```

#### 자동 갱신 스크립트

```bash
#!/bin/bash
# renew-node-cert.sh - 노드 인증서 자동 갱신

CA_SERVER="https://ca.internal.company.io"
NODE_NAME=$(hostname)
CERT_DIR="/etc/iam/pki"

# 새 CSR 생성
openssl req -new -key $CERT_DIR/server.key \
  -out $CERT_DIR/server.csr \
  -subj "/CN=$NODE_NAME"

# CA 서버에 CSR 제출하여 새 인증서 발급
curl -X POST "$CA_SERVER/api/v1/sign" \
  -F "csr=@$CERT_DIR/server.csr" \
  -o $CERT_DIR/server.pem

# 인증서 검증
openssl x509 -in $CERT_DIR/server.pem -noout -text | head -15

# kubelet 재시작으로 새 인증서 적용
sudo systemctl restart kubelet
echo "인증서 갱신 완료"
```

#### Trust Anchor 업데이트

CA 인증서가 변경된 경우 Trust Anchor를 업데이트합니다:

```bash
# 기존 Trust Anchor 업데이트
aws rolesanywhere update-trust-anchor \
  --trust-anchor-id <trust-anchor-id> \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$(cat new-ca.pem)}" \
  --region ap-northeast-2
```

---

## 5. 노드 헬스체크 자동화 (Health Monitoring)

### 자동화된 헬스체크 CronJob

`nodeadm debug`를 기반으로 주기적으로 노드 상태를 검증하고 이상 시 알림을 보냅니다.

```yaml
# node-healthcheck-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hybrid-node-healthcheck
  namespace: monitoring
spec:
  schedule: "*/30 * * * *"  # 30분마다 실행
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: node-healthcheck
          containers:
          - name: checker
            image: bitnami/kubectl:latest
            command:
            - /bin/bash
            - -c
            - |
              NODES=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
                -o jsonpath='{.items[*].metadata.name}')
              ISSUES=""

              for NODE in $NODES; do
                # 노드 상태 확인
                READY=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
                if [ "$READY" != "True" ]; then
                  ISSUES="${ISSUES}\n[CRITICAL] $NODE is NotReady"
                fi

                # 메모리 압박 확인
                MEM_PRESSURE=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="MemoryPressure")].status}')
                if [ "$MEM_PRESSURE" = "True" ]; then
                  ISSUES="${ISSUES}\n[WARN] $NODE has MemoryPressure"
                fi

                # 디스크 압박 확인
                DISK_PRESSURE=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="DiskPressure")].status}')
                if [ "$DISK_PRESSURE" = "True" ]; then
                  ISSUES="${ISSUES}\n[WARN] $NODE has DiskPressure"
                fi
              done

              if [ -n "$ISSUES" ]; then
                echo -e "하이브리드 노드 이상 감지:${ISSUES}"
                # Slack 알림 (웹훅 URL은 시크릿에서 로드)
                if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
                  curl -X POST $SLACK_WEBHOOK_URL \
                    -H 'Content-type: application/json' \
                    -d "{\"text\": \"🚨 EKS Hybrid Node Alert${ISSUES}\"}"
                fi
              else
                echo "모든 하이브리드 노드 정상"
              fi
            env:
            - name: SLACK_WEBHOOK_URL
              valueFrom:
                secretKeyRef:
                  name: slack-webhook
                  key: url
                  optional: true
          restartPolicy: OnFailure
```

### kubelet/containerd 상태 모니터링 (노드 레벨)

각 노드에서 systemd 타이머로 로컬 헬스체크를 실행합니다.

```bash
#!/bin/bash
# /usr/local/bin/node-health-check.sh
# systemd 타이머로 5분마다 실행

ALERT_FILE="/tmp/node-health-alert"

# kubelet 상태 확인
if ! systemctl is-active --quiet kubelet; then
    echo "$(date): kubelet is not running" >> $ALERT_FILE
    sudo systemctl restart kubelet
fi

# containerd 상태 확인
if ! systemctl is-active --quiet containerd; then
    echo "$(date): containerd is not running" >> $ALERT_FILE
    sudo systemctl restart containerd
fi

# 디스크 사용량 확인
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "$(date): Disk usage is ${DISK_USAGE}%" >> $ALERT_FILE
fi

# nodeadm debug 실행 (네트워크 및 자격 증명 검증)
if command -v nodeadm &> /dev/null && [ -f /etc/eks/nodeconfig.yaml ]; then
    if ! sudo nodeadm debug -c file:///etc/eks/nodeconfig.yaml > /dev/null 2>&1; then
        echo "$(date): nodeadm debug failed" >> $ALERT_FILE
    fi
fi
```

```ini
# /etc/systemd/system/node-health-check.timer
[Unit]
Description=Hybrid Node Health Check Timer

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/node-health-check.service
[Unit]
Description=Hybrid Node Health Check

[Service]
Type=oneshot
ExecStart=/usr/local/bin/node-health-check.sh
```

---

< [이전: 워크로드 배치 전략](./06-workload-placement.md) | [목차](./README.md) | [다음: 운영 및 유지보수](./08-operations.md) >
