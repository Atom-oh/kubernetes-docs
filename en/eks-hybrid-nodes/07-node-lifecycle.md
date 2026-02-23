# Node Lifecycle Management

< [Previous: Workload Placement Strategies](./06-workload-placement.md) | [Table of Contents](./README.md) | [Next: Operations and Maintenance](./08-operations.md) >

> **Supported Versions**: EKS 1.31+, nodeadm 0.1+
> **Last Updated**: February 22, 2026

This document covers advanced nodeadm configuration, fleet installation automation, upgrade strategies, credential lifecycle management, and health monitoring for EKS Hybrid Nodes.

## 1. Advanced NodeConfig

### kubelet Tuning

In production environments, you need to fine-tune kubelet resource reservations, eviction thresholds, image garbage collection, and shutdown behavior.

#### Resource Reservation (system-reserved / kube-reserved)

Reserve resources for system processes and Kubernetes components to prevent pods from consuming all node resources.

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

| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| `systemReserved.cpu` | CPU for OS and system daemons | 500m – 1000m |
| `systemReserved.memory` | Memory for OS and system daemons | 1Gi – 2Gi |
| `kubeReserved.cpu` | CPU for kubelet and containerd | 500m – 1000m |
| `kubeReserved.memory` | Memory for kubelet and containerd | 1Gi – 2Gi |

#### Eviction Thresholds

Automatically evict pods when node resources run low to maintain node stability.

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

> **Note**: `evictionHard` triggers immediate eviction, while `evictionSoft` allows a grace period before evicting. Setting soft thresholds helps prevent abrupt pod terminations.

#### maxPods Calculation

Set an appropriate `maxPods` value based on node resources. For hybrid nodes using Cilium IPAM, consider the number of IPs allocated by `clusterPoolIPv4MaskSize`.

```yaml
kubelet:
  config:
    maxPods: 110  # /25 mask = 128 IPs, usable for pods
```

| Mask Size | IP Count | Recommended maxPods |
|-----------|----------|-------------------|
| /25 | 128 | 110 |
| /24 | 256 | 240 |
| /26 | 64 | 50 |

#### Image Garbage Collection

Automatically clean up unused images to manage disk space.

```yaml
kubelet:
  config:
    imageGCHighThresholdPercent: 85
    imageGCLowThresholdPercent: 80
    imageMinimumGCAge: "2m"
```

#### Shutdown Grace Period

Set grace periods for graceful pod termination during node shutdown.

```yaml
kubelet:
  config:
    shutdownGracePeriod: 60s
    shutdownGracePeriodCriticalPods: 20s
```

> **Note**: `shutdownGracePeriodCriticalPods` must be within `shutdownGracePeriod`. Regular pods get `60s - 20s = 40s` for graceful termination.

### Advanced containerd Configuration

#### Private Registry Mirror Setup

Use private registries as mirrors to improve image pull speed and reduce external network dependencies.

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = "/etc/containerd/certs.d"
```

Configure per-registry mirrors using `hosts.toml` files:

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

#### NVIDIA Runtime Class for GPU Nodes

Set NVIDIA Container Runtime as the default runtime for GPU workloads.

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

### Label and Taint Strategies

#### Automatic nodeadm Labels

nodeadm automatically assigns the following label when initializing hybrid nodes:

```
eks.amazonaws.com/compute-type=hybrid
```

This label does not need to be manually added to `--node-labels`.

#### Custom Label Strategies

Add labels by purpose or environment for fine-grained workload placement control.

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

#### Taint Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Automatic taints (NodeConfig) | Applied during nodeadm init | Common taints for all hybrid nodes |
| Manual taints (kubectl) | Applied dynamically during operations | GPU node isolation, maintenance mode |

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

### Full Production NodeConfig Example

A production-ready configuration including kubelet, containerd, labels, and taints.

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

## 2. Fleet Installation Automation

### Ansible Playbook

For large-scale environments, use Ansible to install multiple nodes in batch.

#### Inventory Configuration

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

#### Automation Playbook

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

#### Role-Based Variables (GPU Nodes vs CPU Nodes)

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

### Fleet Verification Script

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

## 3. Node Upgrade Strategies

### Version Skew Policy

Kubernetes maintains a strict version compatibility policy between kubelet and the API server.

| kubelet Version | API Server Version | Compatible |
|----------------|-------------------|------------|
| 1.31 | 1.31 | Yes (same version) |
| 1.30 | 1.31 | Yes (n-1) |
| 1.29 | 1.31 | Yes (n-2) |
| 1.28 | 1.31 | Yes (n-3) |
| 1.27 | 1.31 | No (n-4, unsupported) |
| 1.32 | 1.31 | No (kubelet > API server, unsupported) |

> **Important**: The upgrade order must always be **Control plane (EKS) first, then nodes**. Upgrading nodes before the control plane causes compatibility issues.

### Pre-Upgrade Checklist

Verify the following before upgrading:

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

Upgrade N nodes sequentially to minimize service disruption.

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

For safety, upgrade one node first, validate, then proceed with the rest.

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

### Rollback Procedure

Procedure to restore a node to the previous version when an upgrade fails.

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

## 4. Credential Lifecycle

### SSM Hybrid Activation Renewal

SSM Hybrid Activations have an expiration date set at creation time. You must create a new activation before the current one expires.

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

When node re-registration is required:

```bash
# Re-register on existing node
sudo nodeadm uninstall
# Update nodeconfig.yaml with new activationCode/activationId
sudo nodeadm init -c file://nodeconfig.yaml
```

### IAM Roles Anywhere Certificate Renewal

When using IAM Roles Anywhere, you must renew node certificates before they expire.

#### Certificate Expiration Monitoring

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

#### Automatic Renewal Script

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

#### Trust Anchor Update

When the CA certificate changes, update the Trust Anchor:

```bash
# Update existing Trust Anchor
aws rolesanywhere update-trust-anchor \
  --trust-anchor-id <trust-anchor-id> \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$(cat new-ca.pem)}" \
  --region ap-northeast-2
```

---

## 5. Health Monitoring Automation

### Automated Health Check CronJob

Periodically verify node status using `nodeadm debug` and send alerts on anomalies.

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

### kubelet/containerd Status Monitoring (Node Level)

Run local health checks on each node using a systemd timer.

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

< [Previous: Workload Placement Strategies](./06-workload-placement.md) | [Table of Contents](./README.md) | [Next: Operations and Maintenance](./08-operations.md) >
