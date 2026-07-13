# Node 生命周期管理

< [上一页：工作负载放置策略](./06-workload-placement.md) | [目录](./README.md) | [下一页：运维](./08-operations.md) >

> **支持的版本**：EKS 1.31+、nodeadm 0.1+
> **最后更新**：February 22, 2026

本文档介绍 EKS Hybrid Nodes 的高级 nodeadm 配置、fleet 安装自动化、升级策略、凭证生命周期管理和健康监控。

## 1. 高级 NodeConfig

### kubelet 调优

在生产环境中，你需要精细调整 kubelet 资源预留、驱逐阈值、镜像垃圾回收以及关机行为。

#### 资源预留（system-reserved / kube-reserved）

为系统进程和 Kubernetes 组件预留资源，防止 Pods 消耗所有 Node 资源。

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

| 参数 | 描述 | 推荐值 |
|-----------|-------------|-------------------|
| `systemReserved.cpu` | OS 和系统守护进程的 CPU | 500m – 1000m |
| `systemReserved.memory` | OS 和系统守护进程的内存 | 1Gi – 2Gi |
| `kubeReserved.cpu` | kubelet 和 containerd 的 CPU | 500m – 1000m |
| `kubeReserved.memory` | kubelet 和 containerd 的内存 | 1Gi – 2Gi |

#### 驱逐阈值

当 Node 资源不足时自动驱逐 Pods，以维持 Node 稳定性。

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

> **注意**：`evictionHard` 会触发立即驱逐，而 `evictionSoft` 允许在驱逐前有一个宽限期。设置软阈值有助于防止 Pod 被突然终止。

#### maxPods 计算

根据 Node 资源设置合适的 `maxPods` 值。对于使用 Cilium IPAM 的 hybrid nodes，请考虑由 `clusterPoolIPv4MaskSize` 分配的 IP 数量。

```yaml
kubelet:
  config:
    maxPods: 110  # /25 mask = 128 IPs, usable for pods
```

| 掩码大小 | IP 数量 | 推荐的 maxPods |
|-----------|----------|-------------------|
| /25 | 128 | 110 |
| /24 | 256 | 240 |
| /26 | 64 | 50 |

#### 镜像垃圾回收

自动清理未使用的镜像以管理磁盘空间。

```yaml
kubelet:
  config:
    imageGCHighThresholdPercent: 85
    imageGCLowThresholdPercent: 80
    imageMinimumGCAge: "2m"
```

#### 关机宽限期

为 Node 关机期间 Pod 的优雅终止设置宽限期。

```yaml
kubelet:
  config:
    shutdownGracePeriod: 60s
    shutdownGracePeriodCriticalPods: 20s
```

> **注意**：`shutdownGracePeriodCriticalPods` 必须位于 `shutdownGracePeriod` 之内。普通 Pods 会获得 `60s - 20s = 40s` 用于优雅终止。

### 高级 containerd 配置

#### 私有 Registry 镜像设置

使用私有 registries 作为镜像源，以提高镜像拉取速度并减少对外部网络的依赖。

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = "/etc/containerd/certs.d"
```

使用 `hosts.toml` 文件为每个 registry 配置镜像源：

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

#### GPU Nodes 的 NVIDIA Runtime Class

将 NVIDIA Container Runtime 设置为 GPU 工作负载的默认 runtime。

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

### Label 和 Taint 策略

#### 自动 nodeadm Labels

nodeadm 在初始化 hybrid nodes 时会自动分配以下 label：

```
eks.amazonaws.com/compute-type=hybrid
```

无需将此 label 手动添加到 `--node-labels`。

#### 自定义 Label 策略

按用途或环境添加 labels，以实现细粒度的工作负载放置控制。

```yaml
kubelet:
  flags:
    # Purpose-based labels
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training

    # Environment-based labels (production)
    # - --node-labels=environment=production,tier=compute

    # Datacenter location labels
    # - --node-labels=datacenter=dc-seoul-01,rack=rack-a3
```

#### Taint 策略

| 策略 | 描述 | 使用场景 |
|----------|-------------|----------|
| 自动 taints（NodeConfig） | 在 nodeadm init 期间应用 | 所有 hybrid nodes 的通用 taints |
| 手动 taints（kubectl） | 在运维期间动态应用 | GPU node 隔离、维护模式 |

```yaml
# Automatic taints in NodeConfig
kubelet:
  flags:
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
```

```bash
# Manual taint addition during operations
kubectl taint nodes hybrid-gpu-001 gpu=true:NoSchedule
kubectl taint nodes hybrid-node-005 maintenance=true:NoExecute
```

### 完整生产 NodeConfig 示例

包含 kubelet、containerd、labels 和 taints 的生产就绪配置。

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

## 2. Fleet 安装自动化

### Ansible Playbook

对于大规模环境，使用 Ansible 批量安装多个 Nodes。

#### Inventory 配置

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

#### 自动化 Playbook

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

#### 基于角色的变量（GPU Nodes vs CPU Nodes）

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

### Fleet 验证脚本

```bash
#!/bin/bash
# verify-fleet.sh - Fleet installation verification

echo "=== Fleet Installation Verification ==="

# 1. Check node Ready status
echo ""
echo "1. Node Status Check"
NOT_READY=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  --no-headers | grep -v "Ready" | wc -l)
TOTAL=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  --no-headers | wc -l)
echo "   Total: ${TOTAL}, NotReady: ${NOT_READY}"

if [ "$NOT_READY" -gt 0 ]; then
    echo "   [WARN] NotReady nodes:"
    kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
      --no-headers | grep -v "Ready"
fi

# 2. Verify CNI connectivity
echo ""
echo "2. Cilium Status Check"
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium \
  --no-headers | while read line; do
    STATUS=$(echo $line | awk '{print $3}')
    if [ "$STATUS" != "Running" ]; then
        echo "   [WARN] Abnormal Cilium pod: $line"
    fi
done
echo "   Cilium pod count: $(kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium --no-headers | wc -l)"

# 3. Verify labels and taints
echo ""
echo "3. Label Verification"
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o custom-columns='NAME:.metadata.name,LABELS:.metadata.labels' --no-headers

echo ""
echo "4. Taint Verification"
for NODE in $(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o jsonpath='{.items[*].metadata.name}'); do
    TAINTS=$(kubectl get node $NODE -o jsonpath='{.spec.taints[*].key}')
    echo "   $NODE: $TAINTS"
done

echo ""
echo "=== Verification Complete ==="
```

---

## 3. Node 升级策略

### 版本偏差策略

Kubernetes 在 kubelet 和 API server 之间维护严格的版本兼容性策略。

| kubelet 版本 | API Server 版本 | 兼容 |
|----------------|-------------------|------------|
| 1.31 | 1.31 | 是（相同版本） |
| 1.30 | 1.31 | 是（n-1） |
| 1.29 | 1.31 | 是（n-2） |
| 1.28 | 1.31 | 是（n-3） |
| 1.27 | 1.31 | 否（n-4，不支持） |
| 1.32 | 1.31 | 否（kubelet > API server，不支持） |

> **重要**：升级顺序必须始终是 **先 Control plane（EKS），再 Nodes**。在 Control plane 之前升级 Nodes 会导致兼容性问题。

### 升级前检查清单

升级前验证以下内容：

```bash
#!/bin/bash
# pre-upgrade-check.sh

echo "=== Pre-Upgrade Checklist ==="

# 1. Check PDBs
echo "1. PodDisruptionBudget Check"
kubectl get pdb --all-namespaces -o custom-columns=\
'NAMESPACE:.metadata.namespace,NAME:.metadata.name,MIN-AVAILABLE:.spec.minAvailable,MAX-UNAVAILABLE:.spec.maxUnavailable,ALLOWED-DISRUPTIONS:.status.disruptionsAllowed'

# 2. Check node capacity
echo ""
echo "2. Node Resource Usage"
kubectl top nodes -l eks.amazonaws.com/compute-type=hybrid

# 3. Check running pods
echo ""
echo "3. Pod Count per Hybrid Node"
for NODE in $(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o jsonpath='{.items[*].metadata.name}'); do
    POD_COUNT=$(kubectl get pods --all-namespaces --field-selector spec.nodeName=$NODE \
      --no-headers | wc -l)
    echo "   $NODE: ${POD_COUNT} pods"
done

# 4. Check current versions
echo ""
echo "4. Current Node Versions"
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o custom-columns='NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion'
```

### Rolling Upgrade

按顺序升级 N 个 Nodes，以最大限度减少服务中断。

```bash
#!/bin/bash
# rolling-upgrade.sh - Rolling upgrade script
set -euo pipefail

TARGET_VERSION="${1:?Usage: $0 <target-version> [max-unavailable]}"
MAX_UNAVAILABLE="${2:-1}"
NODECONFIG="/etc/eks/nodeconfig.yaml"

NODES=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o jsonpath='{.items[*].metadata.name}')

TOTAL=$(echo $NODES | wc -w)
CURRENT=0

echo "=== Rolling Upgrade Started ==="
echo "Target version: $TARGET_VERSION"
echo "Total nodes: $TOTAL"
echo "Max unavailable: $MAX_UNAVAILABLE"

for NODE in $NODES; do
    CURRENT=$((CURRENT + 1))
    echo ""
    echo "[$CURRENT/$TOTAL] Upgrading node: $NODE"

    # 1. Cordon
    echo "  -> Cordon"
    kubectl cordon $NODE

    # 2. Drain
    echo "  -> Drain"
    kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data \
      --grace-period=120 --timeout=300s

    # 3. Execute remote upgrade (SSH)
    echo "  -> Running nodeadm upgrade"
    ssh $NODE "sudo nodeadm upgrade $TARGET_VERSION -c file://$NODECONFIG"

    # 4. Wait for node Ready
    echo "  -> Waiting for Ready status"
    kubectl wait --for=condition=Ready node/$NODE --timeout=300s

    # 5. Uncordon
    echo "  -> Uncordon"
    kubectl uncordon $NODE

    echo "  Done: $NODE upgrade complete"
done

echo ""
echo "=== Rolling Upgrade Complete ==="
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o custom-columns='NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion,STATUS:.status.conditions[-1].type'
```

### Canary Upgrade

为确保安全，先升级一个 Node，验证通过后再继续处理其余 Nodes。

```bash
#!/bin/bash
# canary-upgrade.sh - Canary upgrade script
set -euo pipefail

TARGET_VERSION="${1:?Usage: $0 <target-version>}"
NODECONFIG="/etc/eks/nodeconfig.yaml"

# Select canary node (first hybrid node)
CANARY_NODE=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o jsonpath='{.items[0].metadata.name}')

echo "=== Canary Upgrade ==="
echo "Canary node: $CANARY_NODE"
echo "Target version: $TARGET_VERSION"

# Upgrade canary node
kubectl cordon $CANARY_NODE
kubectl drain $CANARY_NODE --ignore-daemonsets --delete-emptydir-data \
  --grace-period=120 --timeout=300s
ssh $CANARY_NODE "sudo nodeadm upgrade $TARGET_VERSION -c file://$NODECONFIG"
kubectl wait --for=condition=Ready node/$CANARY_NODE --timeout=300s
kubectl uncordon $CANARY_NODE

echo ""
echo "Canary node upgrade complete. Please verify."
echo "Canary node status:"
kubectl describe node $CANARY_NODE | head -20

echo ""
read -p "Proceed with remaining nodes? (y/N): " CONFIRM
if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
    echo "Starting rolling upgrade for remaining nodes..."
    REMAINING_NODES=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
      -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | grep -v $CANARY_NODE)

    for NODE in $REMAINING_NODES; do
        echo "Upgrading: $NODE"
        kubectl cordon $NODE
        kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data \
          --grace-period=120 --timeout=300s
        ssh $NODE "sudo nodeadm upgrade $TARGET_VERSION -c file://$NODECONFIG"
        kubectl wait --for=condition=Ready node/$NODE --timeout=300s
        kubectl uncordon $NODE
        echo "  Done: $NODE"
    done
fi

echo "=== Upgrade Complete ==="
```

### 回滚流程

升级失败时将 Node 恢复到先前版本的流程。

```bash
#!/bin/bash
# rollback-node.sh - Node rollback script

NODE="${1:?Usage: $0 <node-name> <previous-version>}"
PREV_VERSION="${2:?Usage: $0 <node-name> <previous-version>}"
CREDENTIAL_PROVIDER="${3:-ssm}"
NODECONFIG="/etc/eks/nodeconfig.yaml"

echo "=== Node Rollback: $NODE -> v$PREV_VERSION ==="

# 1. Cordon & Drain
kubectl cordon $NODE
kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data --timeout=300s

# 2. Uninstall, reinstall previous version, re-init on the node
ssh $NODE << REMOTE_SCRIPT
  sudo nodeadm uninstall
  sudo rm -rf /var/lib/kubelet /etc/kubernetes
  sudo nodeadm install $PREV_VERSION --credential-provider $CREDENTIAL_PROVIDER
  sudo nodeadm init -c file://$NODECONFIG
REMOTE_SCRIPT

# 3. Wait for Ready
kubectl wait --for=condition=Ready node/$NODE --timeout=300s

# 4. Uncordon
kubectl uncordon $NODE

echo "=== Rollback Complete ==="
kubectl get node $NODE -o custom-columns='NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion'
```

---

## 4. 凭证生命周期

### SSM Hybrid Activation 续期

SSM Hybrid Activations 在创建时会设置过期日期。你必须在当前 activation 过期之前创建新的 activation。

```bash
#!/bin/bash
# renew-ssm-activation.sh

# Check current SSM managed instances
aws ssm describe-instance-information \
  --filters "Key=ResourceType,Values=ManagedInstance" \
  --query 'InstanceInformationList[*].[InstanceId,ComputerName,RegistrationDate]' \
  --output table

# Create new activation
NEW_ACTIVATION=$(aws ssm create-activation \
  --default-instance-name "eks-hybrid-node" \
  --iam-role "service-role/AmazonEC2RunCommandRoleForManagedInstances" \
  --registration-limit 100 \
  --expiration-date "$(date -d '+30 days' --iso-8601=seconds)" \
  --region ap-northeast-2 \
  --output json)

echo "New activation code: $(echo $NEW_ACTIVATION | jq -r '.ActivationCode')"
echo "New activation ID: $(echo $NEW_ACTIVATION | jq -r '.ActivationId')"
echo ""
echo "Update activationCode/activationId in your nodeconfig.yaml."
```

需要重新注册 Node 时：

```bash
# Re-register on existing node
sudo nodeadm uninstall
# Update nodeconfig.yaml with new activationCode/activationId
sudo nodeadm init -c file://nodeconfig.yaml
```

### IAM Roles Anywhere 证书续期

使用 IAM Roles Anywhere 时，必须在 Node 证书过期之前对其续期。

#### 证书过期监控

```bash
#!/bin/bash
# check-cert-expiry.sh - Check node certificate expiration

CERT_PATH="/etc/iam/pki/server.pem"
WARNING_DAYS=30

if [ -f "$CERT_PATH" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in $CERT_PATH | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    echo "Certificate: $CERT_PATH"
    echo "Expiry date: $EXPIRY"
    echo "Days remaining: $DAYS_LEFT"

    if [ $DAYS_LEFT -lt $WARNING_DAYS ]; then
        echo "[WARN] Certificate renewal required!"
        exit 1
    fi
fi
```

#### 自动续期脚本

```bash
#!/bin/bash
# renew-node-cert.sh - Automatic node certificate renewal

CA_SERVER="https://ca.internal.company.io"
NODE_NAME=$(hostname)
CERT_DIR="/etc/iam/pki"

# Generate new CSR
openssl req -new -key $CERT_DIR/server.key \
  -out $CERT_DIR/server.csr \
  -subj "/CN=$NODE_NAME"

# Submit CSR to CA server for new certificate
curl -X POST "$CA_SERVER/api/v1/sign" \
  -F "csr=@$CERT_DIR/server.csr" \
  -o $CERT_DIR/server.pem

# Verify certificate
openssl x509 -in $CERT_DIR/server.pem -noout -text | head -15

# Restart kubelet to apply new certificate
sudo systemctl restart kubelet
echo "Certificate renewal complete"
```

#### Trust Anchor 更新

当 CA 证书发生变化时，更新 Trust Anchor：

```bash
# Update existing Trust Anchor
aws rolesanywhere update-trust-anchor \
  --trust-anchor-id <trust-anchor-id> \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$(cat new-ca.pem)}" \
  --region ap-northeast-2
```

---

## 5. 健康监控自动化

### 自动化健康检查 CronJob

定期使用 `nodeadm debug` 验证 Node 状态，并在出现异常时发送告警。

```yaml
# node-healthcheck-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hybrid-node-healthcheck
  namespace: monitoring
spec:
  schedule: "*/30 * * * *"  # Every 30 minutes
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
                # Check node status
                READY=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
                if [ "$READY" != "True" ]; then
                  ISSUES="${ISSUES}\n[CRITICAL] $NODE is NotReady"
                fi

                # Check memory pressure
                MEM_PRESSURE=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="MemoryPressure")].status}')
                if [ "$MEM_PRESSURE" = "True" ]; then
                  ISSUES="${ISSUES}\n[WARN] $NODE has MemoryPressure"
                fi

                # Check disk pressure
                DISK_PRESSURE=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="DiskPressure")].status}')
                if [ "$DISK_PRESSURE" = "True" ]; then
                  ISSUES="${ISSUES}\n[WARN] $NODE has DiskPressure"
                fi
              done

              if [ -n "$ISSUES" ]; then
                echo -e "Hybrid node issues detected:${ISSUES}"
                # Slack notification (webhook URL loaded from secret)
                if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
                  curl -X POST $SLACK_WEBHOOK_URL \
                    -H 'Content-type: application/json' \
                    -d "{\"text\": \"EKS Hybrid Node Alert${ISSUES}\"}"
                fi
              else
                echo "All hybrid nodes healthy"
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

### kubelet/containerd 状态监控（Node 级别）

使用 systemd timer 在每个 Node 上运行本地健康检查。

```bash
#!/bin/bash
# /usr/local/bin/node-health-check.sh
# Run every 5 minutes via systemd timer

ALERT_FILE="/tmp/node-health-alert"

# Check kubelet status
if ! systemctl is-active --quiet kubelet; then
    echo "$(date): kubelet is not running" >> $ALERT_FILE
    sudo systemctl restart kubelet
fi

# Check containerd status
if ! systemctl is-active --quiet containerd; then
    echo "$(date): containerd is not running" >> $ALERT_FILE
    sudo systemctl restart containerd
fi

# Check disk usage
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "$(date): Disk usage is ${DISK_USAGE}%" >> $ALERT_FILE
fi

# Run nodeadm debug (network and credential verification)
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

< [上一页：工作负载放置策略](./06-workload-placement.md) | [目录](./README.md) | [下一页：运维](./08-operations.md) >
