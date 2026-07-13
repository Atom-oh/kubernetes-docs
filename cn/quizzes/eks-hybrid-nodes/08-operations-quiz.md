# EKS Hybrid Nodes 运维测验

> **相关文档**: [运维](../../eks-hybrid-nodes/08-operations.md)

## 选择题

### 1. 在 Hybrid Nodes 环境中，推荐用于 Node 监控的工具组合是什么？

A. 记事本和手动记录
B. Prometheus + Grafana + Node Exporter
C. 仅电子邮件通知
D. 手动审查日志文件

<details>
<summary>显示答案</summary>

**答案：B. Prometheus + Grafana + Node Exporter**

**解释：**
Kubernetes 环境中的标准监控栈是 Prometheus、Grafana 和 Node Exporter 的组合。

```yaml
# Node Exporter DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    spec:
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.6.1
        ports:
        - containerPort: 9100
```

**监控栈组件：**
- **Prometheus**: 指标收集与存储
- **Grafana**: 可视化仪表板
- **Node Exporter**: Node 系统指标
- **DCGM Exporter**: GPU 指标（用于 GPU Node）
- **Alertmanager**: 告警管理

```bash
# Install Prometheus stack (Helm)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

</details>

### 2. 如何检查何时需要续期 kubelet 证书？

A. 证书是永久的，不需要检查
B. 使用 openssl 命令检查证书到期日期
C. 等到 Node 变为 NotReady
D. 每天手动续期

<details>
<summary>显示答案</summary>

**答案：B. 使用 openssl 命令检查证书到期日期**

**解释：**
kubelet 证书会在一段时间后过期，必须定期检查并续期。

```bash
# Check kubelet certificate expiration
sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem \
  -text -noout | grep -A 2 "Validity"

# Or use kubeadm
kubeadm certs check-expiration

# Renew certificates (kubeadm cluster)
kubeadm certs renew all
```

**自动续期配置 (EKS)：**
```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      rotateCertificates: true  # Auto certificate renewal
      serverTLSBootstrap: true
```

**监控告警：**
```yaml
- alert: KubeletCertExpiringSoon
  expr: |
    kubelet_certificate_manager_client_expiration_seconds < 604800
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "kubelet certificate expiring within 7 days"
```

</details>

### 3. 当 kubelet 在 Hybrid Node 上无响应时，首个故障排查步骤是什么？

A. 重启整个 cluster
B. 检查 kubelet service 状态和日志
C. 创建新的 Node
D. 删除所有 Pod

<details>
<summary>显示答案</summary>

**答案：B. 检查 kubelet service 状态和日志**

**解释：**
针对 kubelet 问题的系统化故障排查流程：

```bash
# 1. Check kubelet service status
sudo systemctl status kubelet

# 2. Check kubelet logs
sudo journalctl -u kubelet -f --no-pager | tail -100

# 3. Check for common error patterns
sudo journalctl -u kubelet | grep -E "error|failed|unable"

# 4. Check resource status (memory, disk)
free -h
df -h

# 5. Test network connectivity
curl -vk https://<eks-api-endpoint>:443

# 6. Check containerd status
sudo systemctl status containerd

# 7. Restart kubelet (if needed)
sudo systemctl restart kubelet
```

**常见 kubelet 故障原因：**
- 内存不足 (OOM)
- 磁盘空间不足
- 证书过期
- 网络断开
- containerd 故障

</details>

### 4. 什么命令用于在 Node 维护期间安全迁移 workload（工作负载）？

A. kubectl delete node
B. kubectl drain
C. 仅 kubectl cordon
D. kubectl delete pods --all

<details>
<summary>显示答案</summary>

**答案：B. kubectl drain**

**解释：**
`kubectl drain` 会将 Node 标记为不可调度，并安全地驱逐现有 Pod。

```bash
# 1. Drain node (move workloads)
kubectl drain hybrid-node-1 \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --grace-period=300

# 2. Perform maintenance
# (OS patches, driver updates, etc.)

# 3. Make node schedulable again
kubectl uncordon hybrid-node-1
```

**drain 与 cordon 对比：**

| Command | Action |
|---------|--------|
| `kubectl cordon` | Only prevent new Pod scheduling |
| `kubectl drain` | cordon + evict existing Pods |
| `kubectl uncordon` | Allow scheduling again |

```yaml
# PodDisruptionBudget for safe draining
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

</details>

### 5. Hybrid Nodes 的日志集中化推荐方案是什么？

A. 从每个 Node 手动复制日志文件
B. 使用 Fluent Bit/Fluentd 进行日志收集和转发
C. 不收集日志
D. 仅控制台输出

<details>
<summary>显示答案</summary>

**答案：B. 使用 Fluent Bit/Fluentd 进行日志收集和转发**

**解释：**
Fluent Bit 或 Fluentd 会收集 container 日志，并将其转发到集中式日志存储。

```yaml
# Fluent Bit DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
spec:
  template:
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:2.1
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

**日志架构：**
```
[Hybrid Nodes]          [Central Log System]
+-- Node 1              +------------------+
|   +-- Fluent Bit ---> | Elasticsearch    |
+-- Node 2              | or               |
|   +-- Fluent Bit ---> | CloudWatch Logs  |
+-- Node 3              | or               |
    +-- Fluent Bit ---> | Loki             |
                        +------------------+
```

</details>

### 6. 当 Node 发生故障时，在自动将 Pod 重新调度到其他 Node 之前的默认等待时间是多少？

A. 立即（0 秒）
B. 30 秒
C. 5 分钟（300 秒）
D. 1 小时

<details>
<summary>显示答案</summary>

**答案：C. 5 分钟（300 秒）**

**解释：**
Kubernetes 中默认的 `pod-eviction-timeout` 是 5 分钟。Node 变为 NotReady 5 分钟后，Pod 会被驱逐。

```yaml
# Node Lifecycle Controller settings (kube-controller-manager)
# --pod-eviction-timeout=5m0s  (default)
# --node-monitor-grace-period=40s  (NotReady detection)
```

**更快 failover（故障转移）的配置：**
```yaml
# Add tolerations to Pod
apiVersion: v1
kind: Pod
spec:
  tolerations:
  - key: "node.kubernetes.io/not-ready"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 60  # Evict after 60 seconds (default 300)
  - key: "node.kubernetes.io/unreachable"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 60
```

**Node 状态转换：**
```
Ready --(40s)--> NotReady --(5min)--> Pod Eviction
         |                    |
    node-monitor-        pod-eviction-
    grace-period         timeout
```

</details>

### 7. EKS Hybrid Nodes 升级的推荐策略是什么？

A. 同时升级所有 Node
B. Rolling upgrade（一次一个）
C. 删除并重新创建 cluster
D. 不升级

<details>
<summary>显示答案</summary>

**答案：B. Rolling upgrade（一次一个）**

**解释：**
Rolling upgrade 会按顺序升级 Node，避免服务中断。

```bash
# Rolling upgrade procedure

# 1. Drain first node
kubectl drain hybrid-node-1 --ignore-daemonsets --delete-emptydir-data

# 2. Upgrade nodeadm
sudo nodeadm upgrade --config-source file://nodeadm-config.yaml

# 3. Check node status
kubectl get node hybrid-node-1

# 4. Uncordon node
kubectl uncordon hybrid-node-1

# 5. Wait for workload stabilization
sleep 60

# 6. Repeat for next node
kubectl drain hybrid-node-2 ...
```

**升级检查清单：**
- [ ] 验证 PodDisruptionBudget 设置
- [ ] 按顺序升级 Node
- [ ] 每个步骤后验证状态
- [ ] 准备 rollback plan
- [ ] 执行备份

</details>
