## 简答题

1. 说明 Kubernetes 集群中 etcd 数据库的备份和恢复流程。

<details>
<summary>显示答案</summary>

**答案：**

**etcd 备份流程：**

1. **验证 etcdctl 工具安装：**
   ```bash
   etcdctl version
   ```

2. **执行备份命令：**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

3. **验证备份文件：**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot status snapshot.db --write-out=table
   ```

4. **将备份文件存储在安全位置：**
   - 集群外部的存储
   - 云存储（S3、GCS 等）
   - 不同的物理位置

**etcd 恢复流程：**

1. **停止所有 API server 以进行恢复：**
   ```bash
   sudo systemctl stop kube-apiserver
   ```

2. **停止 etcd 服务：**
   ```bash
   sudo systemctl stop etcd
   ```

3. **备份数据目录（可选）：**
   ```bash
   sudo mv /var/lib/etcd /var/lib/etcd.bak
   ```

4. **从 snapshot 创建新的数据目录：**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
     --data-dir=/var/lib/etcd-restore \
     --name=master \
     --initial-cluster=master=https://127.0.0.1:2380 \
     --initial-cluster-token=etcd-cluster-1 \
     --initial-advertise-peer-urls=https://127.0.0.1:2380
   ```

5. **配置 etcd 使用已恢复的数据目录：**
   ```bash
   sudo mv /var/lib/etcd-restore /var/lib/etcd
   sudo chown -R etcd:etcd /var/lib/etcd
   ```

6. **重启 etcd 服务：**
   ```bash
   sudo systemctl start etcd
   ```

7. **验证 etcd 状态：**
   ```bash
   ETCDCTL_API=3 etcdctl endpoint health \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

8. **重启 API server：**
   ```bash
   sudo systemctl start kube-apiserver
   ```

9. **验证集群状态：**
   ```bash
   kubectl get nodes
   kubectl get pods --all-namespaces
   ```

**最佳实践：**
- 设置定期备份计划（例如每天）
- 在备份前验证 etcd 集群状态
- 验证备份文件完整性
- 定期测试恢复流程
- 在备份文件名中包含时间戳
- 保留多个备份版本
- 记录备份和恢复流程
</details>

2. 说明 Kubernetes 集群中 Node 维护的流程，并描述 `cordon`、`drain` 和 `uncordon` 命令之间的区别。

<details>
<summary>显示答案</summary>

**答案：**

**Node 维护流程：**

1. **检查 Node 状态：**
   ```bash
   kubectl get nodes
   kubectl describe node <node_name>
   ```

2. **Cordon 该 Node：**
   ```bash
   kubectl cordon <node_name>
   ```

3. **Drain 该 Node：**
   ```bash
   kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
   ```

4. **执行维护任务：**
   - 软件更新
   - Kernel 升级
   - 硬件更换
   - 配置变更

5. **完成任务后 Uncordon 该 Node：**
   ```bash
   kubectl uncordon <node_name>
   ```

6. **验证 Node 状态：**
   ```bash
   kubectl get nodes
   ```

**命令区别：**

1. **`kubectl cordon <node_name>`：**
   - 将该 Node 标记为不可调度。
   - 新的 Pod 不会被调度到该 Node 上。
   - 已经运行的 Pod 会继续运行。
   - Node 状态中会出现 `SchedulingDisabled` 指示。

2. **`kubectl drain <node_name>`：**
   - 将该 Node 标记为不可调度（包含 cordon）。
   - 从该 Node 安全驱逐正在运行的 Pod。
   - Pod 会被重新调度到其他 Node 上。
   - 默认会忽略 DaemonSet Pod（需要 `--ignore-daemonsets` 标志）。
   - 使用 emptyDir 卷的 Pod 可能会丢失数据，需要特殊处理（`--delete-emptydir-data` 标志）。
   - 遵守 PodDisruptionBudget。

3. **`kubectl uncordon <node_name>`：**
   - 将该 Node 重新标记为可调度。
   - 新的 Pod 可以被调度到该 Node 上。
   - 之前被驱逐的 Pod 不会自动返回。

**维护注意事项：**
- 确保集群有足够的备用容量
- 为关键工作负载设置 PodDisruptionBudget
- 一次只维护一个 Node
- 在维护期间调整自动扩缩设置
- 在维护前后验证工作负载状态
- 使用 rolling update 策略
</details>

3. 说明如何在 Kubernetes 集群中监控和管理资源使用情况。列出应包含的工具和技术。

<details>
<summary>显示答案</summary>

**答案：**

**Kubernetes 资源监控和管理方法：**

**1. 基础监控工具：**

- **Metrics Server：**
  - 提供基础 CPU 和内存使用指标
  - 支持 `kubectl top` 命令
  - 安装方法：
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    ```
  - 使用示例：
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Kubernetes Dashboard：**
  - 以可视化方式呈现集群状态和资源使用情况
  - 为 Pod、Node、Namespace 等提供资源管理界面

**2. 高级监控栈：**

- **Prometheus + Grafana：**
  - Prometheus：指标收集和存储
  - Grafana：指标可视化和 dashboard
  - 可通过 kube-prometheus-stack 或 Prometheus Operator 安装
  - 支持自定义告警规则和 dashboard

- **ELK/EFK Stack：**
  - Elasticsearch：日志存储和搜索
  - Logstash/Fluentd：日志收集和处理
  - Kibana：日志可视化和分析

**3. 资源管理技术：**

- **设置资源 requests 和 limits：**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **Namespace 级别的资源配额（ResourceQuota）：**
  ```yaml
  apiVersion: v1
  kind: ResourceQuota
  metadata:
    name: compute-quota
    namespace: dev
  spec:
    hard:
      pods: "10"
      requests.cpu: "4"
      requests.memory: 8Gi
      limits.cpu: "8"
      limits.memory: 16Gi
  ```

- **默认资源限制（LimitRange）：**
  ```yaml
  apiVersion: v1
  kind: LimitRange
  metadata:
    name: default-limits
    namespace: dev
  spec:
    limits:
    - default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 200m
        memory: 256Mi
      type: Container
  ```

- **Horizontal Pod Autoscaler (HPA)：**
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: web-app
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: web-app
    minReplicas: 2
    maxReplicas: 10
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 80
  ```

- **Vertical Pod Autoscaler (VPA)：**
  - 自动调整 Pod 的 CPU 和内存 requests
  - 根据资源使用模式提供建议

- **Cluster Autoscaler：**
  - 根据工作负载需求自动调整集群 Node 数量
  - 资源不足时添加 Node，利用率较低时移除 Node

**4. 监控最佳实践：**

- 为所有 Pod 设置资源 requests 和 limits
- 为关键指标配置告警
- 基于历史使用情况分析进行资源规划
- 定期执行资源审计
- 分析资源使用趋势以优化成本
- 为开发、预发布和生产环境设置适当的资源配额
- 同时监控 Node 级别和 Pod 级别的指标
</details>

4. 说明 Kubernetes 集群升级期间可能发生的主要风险，以及缓解这些风险的策略。

<details>
<summary>显示答案</summary>

**答案：**

**Kubernetes 集群升级风险和缓解策略：**

**1. 主要风险：**

- **API 兼容性问题：**
  - API 可能在新版本中变更或被移除
  - 某些 Custom Resource Definitions (CRDs) 或 API 版本可能不再受支持

- **工作负载中断：**
  - control plane 组件重启导致 API server 临时不可用
  - Node 升级期间 Pod 重新调度导致 Service 中断

- **功能变更：**
  - 默认行为可能发生变化，影响现有工作负载
  - 安全策略变更导致权限问题

- **性能问题：**
  - 新版本中的资源需求可能增加
  - 初始稳定期间可能出现性能下降

- **回滚复杂性：**
  - 某些升级无法轻松回滚
  - 数据格式变更导致回滚受限

**2. 缓解策略：**

- **充分规划和准备：**
  - **查看 changelog：** 检查新版本中的变更、已移除功能和已知问题
  - **验证升级路径：** 确认支持从当前版本直接升级到目标版本
  - **查看资源需求：** 检查新版本的最低要求

- **先在测试环境中测试：**
  - 在类似生产环境的测试集群中执行升级
  - 测试所有关键工作负载和自定义资源
  - 运行自动化测试套件

- **验证 API 兼容性：**
  - 检查正在使用的 API 版本：
    ```bash
    kubectl api-resources -o wide
    ```
  - 检查是否使用已弃用的 API：
    ```bash
    kubectl get -A | grep "deprecated"
    ```
  - 根据需要更新 manifest

- **备份和恢复计划：**
  - 备份 etcd 数据库：
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db
    ```
  - 备份所有关键 manifest：
    ```bash
    kubectl get all --all-namespaces -o yaml > all-resources.yaml
    ```
  - 记录并测试恢复流程

- **渐进式升级方法：**
  - **先升级 control plane 组件：**
    - 在 HA 设置中，一次升级一个 control plane Node
  - **Worker Node rolling upgrade：**
    - 将 Node 组划分为小批次进行升级
    - 每批升级后验证稳定性

- **工作负载保护：**
  - **设置 PodDisruptionBudget：**
    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: app-pdb
    spec:
      minAvailable: 2  # or maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```
  - **Drain Node 时要小心：**
    ```bash
    kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
    ```

- **增强监控：**
  - 在升级前、升级期间和升级后监控集群状态
  - 关注关键指标和日志
  - 临时调整告警阈值

- **回滚计划：**
  - 定义回滚触发条件
  - 记录回滚流程
  - 保留回滚所需的所有组件和镜像

- **沟通计划：**
  - 通知所有利益相关者升级计划和预期影响
  - 在升级期间提供状态更新
  - 为问题定义升级处理路径

**3. 特定版本注意事项：**

- **Minor Version 升级（例如 1.24 → 1.25）：**
  - 特别注意被移除的 API 和功能变更
  - 一次只升级一个 minor version

- **Patch Version 升级（例如 1.24.0 → 1.24.1）：**
  - 通常更安全，但仍然需要测试
  - 对于安全补丁，可考虑更快部署
</details>

5. 说明 Kubernetes 集群中可能发生的常见网络问题，以及如何诊断和解决这些问题。

<details>
<summary>显示答案</summary>

**答案：**

**Kubernetes 网络问题诊断和解决：**

**1. Pod 到 Pod 通信问题：**

- **症状：**
  - Pod 无法与其他 Pod 通信
  - 无法通过 Service 名称连接
  - 网络超时错误

- **诊断方法：**
  - 检查 network policy：
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - 创建测试 Pod 进行连通性测试：
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    ping <target_pod_IP>
    wget -O- <service_name>:<port>
    ```
  - 检查 CNI plugin Pod 状态：
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **解决方法：**
  - 重新安装或更新 CNI plugin
  - 修改或移除 network policy
  - 检查 Node 网络接口
  - 检查 firewall 规则

**2. Service Discovery 和 DNS 问题：**

- **症状：**
  - 无法通过 Service 名称连接
  - DNS 查询失败
  - 间歇性连接问题

- **诊断方法：**
  - 检查 CoreDNS Pod 状态：
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - 测试 DNS 查询：
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    nslookup kubernetes.default.svc.cluster.local
    nslookup <service_name>.<namespace>.svc.cluster.local
    cat /etc/resolv.conf
    ```
  - 检查 Service endpoint：
    ```bash
    kubectl get endpoints <service_name>
    ```

- **解决方法：**
  - 重启 CoreDNS Pod：
    ```bash
    kubectl rollout restart deployment coredns -n kube-system
    ```
  - 检查并修改 DNS 配置：
    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
  - 检查 kubelet DNS 设置

**3. Service 和 Ingress 问题：**

- **症状：**
  - 无法从外部来源访问 Service
  - Ingress 规则不工作
  - Load balancer 未创建

- **诊断方法：**
  - 检查 Service 状态：
    ```bash
    kubectl describe service <service_name>
    ```
  - 检查 Ingress 状态：
    ```bash
    kubectl describe ingress <ingress_name>
    ```
  - 检查 ingress controller Pod 日志：
    ```bash
    kubectl logs -n <ingress_namespace> <ingress_controller_pod>
    ```
  - 检查 endpoint：
    ```bash
    kubectl get endpoints <service_name>
    ```

- **解决方法：**
  - 验证 Service selector 是否匹配 Pod label
  - 重新安装或更新 ingress controller
  - 检查 Service 类型和端口配置
  - 检查 cloud provider load balancer 设置

**4. Node 网络问题：**

- **症状：**
  - Node 与集群断开连接
  - Node 到 Node 通信失败
  - kubelet 连接错误

- **诊断方法：**
  - 检查 Node 状态：
    ```bash
    kubectl describe node <node_name>
    ```
  - 检查 Node 网络接口：
    ```bash
    # Directly on the node
    ip addr
    ip route
    ```
  - 检查 firewall 规则：
    ```bash
    # Directly on the node
    iptables -L
    ```
  - 检查 kubelet 日志：
    ```bash
    journalctl -u kubelet
    ```

- **解决方法：**
  - 重新配置 Node 网络接口
  - 修改 firewall 规则
  - 重启 kubelet
  - 必要时重启 Node

**5. Network Policy 问题：**

- **症状：**
  - 意外的连接阻塞
  - 无法在特定 Namespace 之间通信
  - 只有部分 Pod 可访问

- **诊断方法：**
  - 检查 network policy：
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - 检查 Pod label：
    ```bash
    kubectl get pods --show-labels
    ```
  - 验证 network plugin 是否支持 network policy

- **解决方法：**
  - 修改或删除 network policy
  - 修改 Pod label
  - 使用 network policy 调试工具

**6. 常用网络调试工具：**

- **网络调试 Pod：**
  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: network-debug
  spec:
    containers:
    - name: debug
      image: nicolaka/netshoot
      command: ["sleep", "3600"]
  ```

- **有用命令：**
  ```bash
  # Inside the pod
  ping <IP>
  traceroute <IP>
  dig <service_name>.<namespace>.svc.cluster.local
  curl -v <URL>
  tcpdump -i any
  netstat -tuln
  ```

- **CNI plugin 特定的调试工具：**
  - Calico: `calicoctl`
  - Cilium: `cilium`
  - Weave: `weave`

**7. 最佳实践：**

- 记录网络拓扑
- 定期执行连通性测试
- 在变更 network policy 前分析影响
- 规划集群网络 CIDR 范围
- 实施网络监控工具
</details>
## 实践题

1. 编写一个满足以下要求的 ResourceQuota manifest：
   - Namespace: development
   - Maximum pods: 20
   - Maximum CPU requests: 4 cores
   - Maximum memory requests: 8Gi
   - Maximum PVCs: 10
   - Maximum storage requests: 100Gi

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: development
spec:
  hard:
    pods: "20"
    requests.cpu: "4"
    requests.memory: 8Gi
    persistentvolumeclaims: "10"
    requests.storage: 100Gi
```

此 ResourceQuota 为 'development' Namespace 设置以下限制：
- 最多 20 个 Pod
- CPU requests 总量为 4 cores
- 内存 requests 总量为 8Gi
- 最多 10 个 PersistentVolumeClaims
- 存储 requests 总量为 100Gi

应用 ResourceQuota：
```bash
kubectl apply -f resource-quota.yaml
```

检查当前 quota 使用情况：
```bash
kubectl describe quota dev-quota -n development
```

注意：在应用 ResourceQuota 之前，Namespace 必须已经存在。如果 Namespace 不存在，请先创建：
```bash
kubectl create namespace development
```
</details>

2. 编写一个脚本，检查集群中所有 Node 上的 kubelet 服务状态，并在发现问题时解决问题。

<details>
<summary>显示答案</summary>

**答案：**

```bash
#!/bin/bash
# Filename: check_kubelet.sh
# Description: Check kubelet service status on all nodes and troubleshoot

# Get node list
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

# Iterate over each node
for NODE in $NODES; do
  echo "===== Checking node: $NODE ====="

  # Check node status
  NODE_STATUS=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
  echo "Node status: $NODE_STATUS"

  # Check kubelet status via SSH
  echo "Checking kubelet service status..."
  ssh $NODE "sudo systemctl status kubelet | grep Active"

  # Start kubelet if not running
  if ssh $NODE "sudo systemctl is-active kubelet" != "active"; then
    echo "kubelet is not running. Starting service..."
    ssh $NODE "sudo systemctl start kubelet"

    # Check status again after starting
    sleep 5
    if ssh $NODE "sudo systemctl is-active kubelet" == "active"; then
      echo "kubelet service started successfully."
    else
      echo "kubelet service failed to start. Checking logs..."
      ssh $NODE "sudo journalctl -u kubelet --no-pager -n 50"
    fi
  else
    echo "kubelet service is running normally."
  fi

  # Check kubelet configuration
  echo "Checking kubelet configuration..."
  ssh $NODE "sudo cat /var/lib/kubelet/config.yaml | grep -E 'address|authentication|authorization'"

  echo "===== $NODE check complete ====="
  echo ""
done
```

此脚本执行以下任务：
1. 使用 `kubectl get nodes` 获取集群中所有 Node 的列表。
2. 对每个 Node：
   - 检查该 Node 的 Ready 状态。
   - 通过 SSH 连接到该 Node 以检查 kubelet 服务状态。
   - 如果 kubelet 未运行，则启动该服务。
   - 启动服务后再次检查状态。
   - 如果启动失败，则检查日志。
   - 检查 kubelet 配置文件中的关键设置。

**用法：**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
```

**注意事项：**
- 运行此脚本需要对所有 Node 的 SSH 访问权限。
- 生产环境建议使用基于 SSH key 的身份验证。
- 在云环境中，直接 SSH 访问 Node 可能受限，因此可能需要使用 cloud provider 的 Node 管理工具。
</details>

3. 设置一个 cron job，备份集群的 etcd 数据库，并将备份文件存储在安全位置。

<details>
<summary>显示答案</summary>

**答案：**

**1. 创建备份脚本：**

```bash
#!/bin/bash
# Filename: backup_etcd.sh
# Description: etcd database backup and remote storage

# Variable settings
BACKUP_DIR="/opt/etcd-backup"
REMOTE_BACKUP_DIR="/mnt/remote-storage/etcd-backups"
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="etcd-snapshot-$DATE.db"
ETCD_ENDPOINTS="https://127.0.0.1:2379"
ETCD_CACERT="/etc/kubernetes/pki/etcd/ca.crt"
ETCD_CERT="/etc/kubernetes/pki/etcd/server.crt"
ETCD_KEY="/etc/kubernetes/pki/etcd/server.key"
RETENTION_DAYS=7

# Create backup directory
mkdir -p $BACKUP_DIR

# Create etcd snapshot
ETCDCTL_API=3 etcdctl snapshot save $BACKUP_DIR/$BACKUP_FILE \
  --endpoints=$ETCD_ENDPOINTS \
  --cacert=$ETCD_CACERT \
  --cert=$ETCD_CERT \
  --key=$ETCD_KEY

# Verify backup success
if [ $? -eq 0 ]; then
  echo "etcd backup successful: $BACKUP_FILE"

  # Check backup file status
  ETCDCTL_API=3 etcdctl snapshot status $BACKUP_DIR/$BACKUP_FILE --write-out=table

  # Compress backup file
  gzip $BACKUP_DIR/$BACKUP_FILE

  # Copy to remote storage
  mkdir -p $REMOTE_BACKUP_DIR
  cp $BACKUP_DIR/$BACKUP_FILE.gz $REMOTE_BACKUP_DIR/

  # Clean up old backup files (local)
  find $BACKUP_DIR -name "etcd-snapshot-*.db.gz" -type f -mtime +$RETENTION_DAYS -delete

  # Clean up old backup files (remote)
  find $REMOTE_BACKUP_DIR -name "etcd-snapshot-*.db.gz" -type f -mtime +$RETENTION_DAYS -delete

  echo "Backup complete and copied to remote storage: $REMOTE_BACKUP_DIR/$BACKUP_FILE.gz"
else
  echo "etcd backup failed"
  exit 1
fi
```

**2. 授予脚本执行权限：**

```bash
chmod +x /opt/etcd-backup/backup_etcd.sh
```

**3. 设置 cron job：**

```bash
# Edit root user's crontab
sudo crontab -e
```

添加以下内容：

```
# Run etcd backup daily at 2 AM
0 2 * * * /opt/etcd-backup/backup_etcd.sh >> /var/log/etcd-backup.log 2>&1
```

**4. 设置备份日志轮转：**

创建 `/etc/logrotate.d/etcd-backup` 文件：

```
/var/log/etcd-backup.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
```

**5. 测试备份：**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. 设置备份监控（可选）：**

要在备份失败时接收告警，可以与 Prometheus 等监控工具集成。将以下代码添加到备份脚本中：

```bash
# Create file indicating backup success/failure
if [ $? -eq 0 ]; then
  echo "success" > /var/lib/node_exporter/etcd_backup_status.prom
else
  echo "failure" > /var/lib/node_exporter/etcd_backup_status.prom
fi
```

**注意事项：**
- 备份文件应存储在集群外部的安全位置。
- 在云环境中，建议使用 S3 或 GCS 等 object storage。
- 定期执行备份恢复测试，以验证备份有效性。
- 对于 HA etcd 集群，只需要在一个 etcd 实例上执行备份。
</details>
4. 编写一个流程，用于对集群中的所有 Node 执行 rolling update。更新期间必须保持工作负载可用性。

<details>
<summary>显示答案</summary>

**答案：**

**Node Rolling Update 流程：**

```bash
#!/bin/bash
# Filename: node_rolling_update.sh
# Description: Perform cluster node rolling update

# Variable settings
UPGRADE_COMMAND="sudo apt update && sudo apt upgrade -y"
REBOOT_REQUIRED_CHECK="[ -f /var/run/reboot-required ]"
MAX_UNAVAILABLE=1  # Number of nodes to update at once

# Check cluster status
echo "Checking cluster status..."
kubectl get nodes
kubectl get pods --all-namespaces -o wide

# Check PodDisruptionBudgets
echo "Checking PodDisruptionBudgets..."
kubectl get poddisruptionbudget --all-namespaces

# Get node list
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
NODE_COUNT=$(echo $NODES | wc -w)

echo "Updating $NODE_COUNT nodes total."
echo "Node list: $NODES"
echo "Maximum $MAX_UNAVAILABLE node(s) will be updated at once."
echo "Press Enter to continue. Press Ctrl+C to cancel."
read

# Iterate over each node
for NODE in $NODES; do
  echo "===== Updating node: $NODE ====="

  # Cordon node
  echo "Cordoning node..."
  kubectl cordon $NODE

  # Drain node
  echo "Draining node..."
  kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data --force

  # Update node
  echo "Updating node..."
  ssh $NODE "$UPGRADE_COMMAND"

  # Check if reboot is required
  REBOOT_REQUIRED=$(ssh $NODE "$REBOOT_REQUIRED_CHECK && echo 'true' || echo 'false'")

  if [ "$REBOOT_REQUIRED" == "true" ]; then
    echo "Reboot required. Rebooting..."
    ssh $NODE "sudo reboot"

    # Wait until node is Ready again
    echo "Node rebooting. Waiting until Ready..."
    while true; do
      STATUS=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
      if [ "$STATUS" == "True" ]; then
        echo "Node is now Ready."
        break
      fi
      echo "Node is not Ready yet. Checking again in 10 seconds."
      sleep 10
    done
  else
    echo "Node reboot not required."
  fi

  # Uncordon node
  echo "Uncordoning node..."
  kubectl uncordon $NODE

  # Check node status
  echo "Checking node status..."
  kubectl get node $NODE

  # Wait for pods to be rescheduled on the node
  echo "Waiting for pods to be rescheduled on the node..."
  sleep 30

  # Check cluster status
  echo "Checking cluster status..."
  kubectl get pods --all-namespaces -o wide | grep $NODE

  echo "===== $NODE update complete ====="
  echo ""

  # User confirmation before proceeding to next node (optional)
  echo "Press Enter to proceed to next node. Press Ctrl+C to cancel."
  read
done

echo "All node updates complete!"
kubectl get nodes
```

**Rolling Update 前准备：**

1. **设置 PodDisruptionBudget：**
   为关键工作负载设置 PDB，以确保可用性。

   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: app-pdb
     namespace: default
   spec:
     minAvailable: 2  # or maxUnavailable: 1
     selector:
       matchLabels:
         app: my-app
   ```

2. **确保资源充足：**
   验证当一个 Node 被移除时，其余 Node 可以承载所有工作负载。

3. **执行备份：**
   在更新前执行 etcd 数据库备份。

**Rolling Update 最佳实践：**

1. **渐进式方法：**
   - 一次只更新一个 Node
   - 每次 Node 更新后验证集群状态

2. **自动化和幂等性：**
   - 使用脚本自动化该流程
   - 设计为失败时可安全重试

3. **增强监控：**
   - 在更新期间监控集群指标
   - 监控应用程序状态和性能

4. **回滚计划：**
   - 为问题准备回滚流程
   - 准备恢复到先前状态的方法

5. **沟通：**
   - 公告更新时间计划和预期影响
   - 定期报告更新进度

**注意事项：**
- 在云环境中，可以利用托管 Kubernetes 服务（EKS、GKE、AKS 等）的 Node 更新功能。
- 如果有多个 Node 组，请按组执行更新。
- 特别监控关键 system Pod（CoreDNS、kube-proxy 等）的状态。
</details>

5. 编写一个脚本，识别集群中资源使用率高的 Pod，并生成包含这些信息的报告。

<details>
<summary>显示答案</summary>

**答案：**

```bash
#!/bin/bash
# Filename: resource_usage_report.sh
# Description: Identify pods with high resource usage in the cluster and generate report

# Variable settings
REPORT_DIR="/tmp/k8s-reports"
DATE=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="$REPORT_DIR/resource-usage-report-$DATE.txt"
TOP_N=10  # Show top N pods

# Create report directory
mkdir -p $REPORT_DIR

# Write report header
echo "===== Kubernetes Cluster Resource Usage Report =====" > $REPORT_FILE
echo "Generated: $(date)" >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Add cluster information
echo "===== Cluster Information =====" >> $REPORT_FILE
kubectl cluster-info >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

# Node resource usage
echo "===== Node Resource Usage =====" >> $REPORT_FILE
kubectl top nodes | sort -k 3 -hr >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Top pods by CPU usage
echo "===== Top $TOP_N Pods by CPU Usage =====" >> $REPORT_FILE
kubectl top pods --all-namespaces | sort -k 3 -hr | head -n $((TOP_N + 1)) >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Top pods by memory usage
echo "===== Top $TOP_N Pods by Memory Usage =====" >> $REPORT_FILE
kubectl top pods --all-namespaces | sort -k 4 -hr | head -n $((TOP_N + 1)) >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Resource usage by namespace
echo "===== Resource Usage by Namespace =====" >> $REPORT_FILE
echo "CPU Usage (cores):" >> $REPORT_FILE
kubectl top pods --all-namespaces | tail -n +2 | awk '{print $2, $3}' | sed 's/m//' | awk '{ns[$1] += $2} END {for (namespace in ns) print namespace, ns[namespace]/1000}' | sort -k 2 -hr >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "Memory Usage (GiB):" >> $REPORT_FILE
kubectl top pods --all-namespaces | tail -n +2 | awk '{print $2, $4}' | sed 's/Mi//' | awk '{ns[$1] += $2} END {for (namespace in ns) print namespace, ns[namespace]/1024}' | sort -k 2 -hr >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Identify pods with high usage relative to requests
echo "===== Pods with High Usage Relative to Requests =====" >> $REPORT_FILE
echo "Collecting pod information..." >> $REPORT_FILE

# Create temporary files
PODS_USAGE_FILE="$REPORT_DIR/pods-usage-$DATE.tmp"
PODS_REQUESTS_FILE="$REPORT_DIR/pods-requests-$DATE.tmp"

# Collect current usage
kubectl top pods --all-namespaces | tail -n +2 > $PODS_USAGE_FILE

# Collect resource requests for all pods in all namespaces
echo "Namespace,Pod,CPU Request(m),Memory Request(Mi)" > $PODS_REQUESTS_FILE
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get pods -n $ns -o jsonpath='{range .items[*]}{.metadata.namespace},{.metadata.name},{range .spec.containers[*]}{.resources.requests.cpu}{","}{.resources.requests.memory}{"\n"}{end}{end}' | sed 's/$/,/' | sed 's/,$//' >> $PODS_REQUESTS_FILE
done

# Calculate usage relative to requests and add to report
echo "Pods with high CPU usage (usage/request > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  cpu_usage=$(echo $line | awk '{print $3}' | sed 's/m//')

  # Find CPU request for the pod
  cpu_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $3}' | sed 's/[^0-9m.]//g' | sed 's/m//')

  # Show as "not set" if no CPU request
  if [ -z "$cpu_request" ] || [ "$cpu_request" == "" ]; then
    echo "$ns/$pod: CPU usage ${cpu_usage}m, request not set" >> $REPORT_FILE
  else
    # Calculate CPU usage percentage
    cpu_percentage=$(echo "scale=2; $cpu_usage / $cpu_request * 100" | bc)

    # Only show if usage is 80% or higher
    if (( $(echo "$cpu_percentage >= 80" | bc -l) )); then
      echo "$ns/$pod: CPU usage ${cpu_usage}m, request ${cpu_request}m, utilization ${cpu_percentage}%" >> $REPORT_FILE
    fi
  fi
done < $PODS_USAGE_FILE

echo "" >> $REPORT_FILE
echo "Pods with high memory usage (usage/request > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  mem_usage=$(echo $line | awk '{print $4}' | sed 's/Mi//')

  # Find memory request for the pod
  mem_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $4}' | sed 's/[^0-9Mi.]//g' | sed 's/Mi//')

  # Show as "not set" if no memory request
  if [ -z "$mem_request" ] || [ "$mem_request" == "" ]; then
    echo "$ns/$pod: Memory usage ${mem_usage}Mi, request not set" >> $REPORT_FILE
  else
    # Calculate memory usage percentage
    mem_percentage=$(echo "scale=2; $mem_usage / $mem_request * 100" | bc)

    # Only show if usage is 80% or higher
    if (( $(echo "$mem_percentage >= 80" | bc -l) )); then
      echo "$ns/$pod: Memory usage ${mem_usage}Mi, request ${mem_request}Mi, utilization ${mem_percentage}%" >> $REPORT_FILE
    fi
  fi
done < $PODS_USAGE_FILE

echo "" >> $REPORT_FILE

# Identify pods without resource requests
echo "===== Pods Without Resource Requests =====" >> $REPORT_FILE
kubectl get pods --all-namespaces -o json | jq -r '.items[] | select((.spec.containers[].resources.requests.cpu == null) or (.spec.containers[].resources.requests.memory == null)) | .metadata.namespace + "/" + .metadata.name' >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Clean up temporary files
rm -f $PODS_USAGE_FILE $PODS_REQUESTS_FILE

# Report summary
echo "===== Report Summary =====" >> $REPORT_FILE
echo "Total nodes: $(kubectl get nodes | tail -n +2 | wc -l)" >> $REPORT_FILE
echo "Total pods: $(kubectl get pods --all-namespaces | tail -n +2 | wc -l)" >> $REPORT_FILE
echo "Total namespaces: $(kubectl get ns | tail -n +2 | wc -l)" >> $REPORT_FILE
echo "Report generation complete: $REPORT_FILE" >> $REPORT_FILE

# Output report location
echo "Report generated: $REPORT_FILE"

# HTML report generation (optional)
HTML_REPORT="${REPORT_FILE%.txt}.html"
echo "<html><head><title>Kubernetes Resource Usage Report</title>" > $HTML_REPORT
echo "<style>body{font-family:Arial;margin:20px}h1{color:#326ce5}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px}th{background-color:#f2f2f2}</style>" >> $HTML_REPORT
echo "</head><body>" >> $HTML_REPORT
echo "<h1>Kubernetes Cluster Resource Usage Report</h1>" >> $HTML_REPORT
echo "<p>Generated: $(date)</p>" >> $HTML_REPORT

# Convert report content to HTML
awk '/===== Cluster Information =====/{flag=1;print "<h2>Cluster Information</h2><pre>"}/===== Node Resource Usage =====/{flag=0;print "</pre><h2>Node Resource Usage</h2><table><tr><th>Node</th><th>CPU(%)</th><th>Memory(%)</th></tr>"}/===== Top.*CPU Usage/{flag=0;print "</table><h2>Top Pods by CPU Usage</h2><table><tr><th>Namespace</th><th>Pod</th><th>CPU(m)</th><th>Memory(Mi)</th></tr>"}/===== Top.*Memory Usage/{flag=0;print "</table><h2>Top Pods by Memory Usage</h2><table><tr><th>Namespace</th><th>Pod</th><th>CPU(m)</th><th>Memory(Mi)</th></tr>"}/===== Resource Usage by Namespace =====/{flag=0;print "</table><h2>Resource Usage by Namespace</h2>"}/CPU Usage \(cores\):/{flag=0;print "<h3>CPU Usage (cores)</h3><table><tr><th>Namespace</th><th>CPU(cores)</th></tr>"}/Memory Usage \(GiB\):/{flag=0;print "</table><h3>Memory Usage (GiB)</h3><table><tr><th>Namespace</th><th>Memory(GiB)</th></tr>"}/===== Pods with High Usage Relative to Requests =====/{flag=0;print "</table><h2>Pods with High Usage Relative to Requests</h2>"}/Pods with high CPU usage/{flag=0;print "<h3>Pods with High CPU Usage (usage/request > 80%)</h3><ul>"}/Pods with high memory usage/{flag=0;print "</ul><h3>Pods with High Memory Usage (usage/request > 80%)</h3><ul>"}/===== Pods Without Resource Requests =====/{flag=0;print "</ul><h2>Pods Without Resource Requests</h2><ul>"}/===== Report Summary =====/{flag=0;print "</ul><h2>Report Summary</h2><ul>"}{if(flag==1)print;else if($0 ~ /^NAME/){print "<tr>";for(i=1;i<=NF;i++)print "<th>"$i"</th>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]%/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]m/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].* [0-9]/){print "<tr><td>"$1"</td><td>"$2"</td></tr>"}else if($0 ~ /^[a-z].*\//){print "<li>"$0"</li>"}else if($0 ~ /^Total/){print "<li>"$0"</li>"}}' $REPORT_FILE >> $HTML_REPORT

echo "</ul></body></html>" >> $HTML_REPORT
echo "HTML report generated: $HTML_REPORT"
```

**脚本用法：**
```bash
chmod +x resource_usage_report.sh
./resource_usage_report.sh
```

**脚本功能：**
1. 收集集群信息
2. 收集 Node 资源使用情况
3. 按 CPU 和内存使用情况识别排名靠前的 Pod
4. 按 Namespace 计算资源使用情况
5. 识别相对于 requests 使用率较高的 Pod
6. 识别未设置资源 requests 的 Pod
7. 生成文本和 HTML 格式的报告

**注意事项：**
- 此脚本需要 `kubectl`、`jq` 和 `bc` 工具。
- 集群中必须安装 Metrics Server。
- 在大型集群中，脚本执行时间可能较长。
- 可以设置为 cron job 以定期生成报告。
- 报告可以通过电子邮件发送，或与监控系统集成。
</details>
## 高级主题

1. 在 Kubernetes 集群中优化 etcd 性能的关键配置参数和最佳实践是什么？
   - A) `--max-request-bytes`, `--quota-backend-bytes`, regular compaction
   - B) `--max-concurrent-requests`, `--max-connections`, disk RAID configuration
   - C) `--auto-compaction-retention`, `--snapshot-count`, SSD storage
   - D) `--max-txn-ops`, `--max-result-buffer`, memory expansion

<details>
<summary>显示答案</summary>

**答案：C) `--auto-compaction-retention`, `--snapshot-count`, SSD storage**

**解释：**
etcd 是 Kubernetes 集群的核心数据存储，其性能直接影响整体集群性能。优化 etcd 性能的关键配置参数和最佳实践如下：

1. **`--auto-compaction-retention`**：etcd 是一种 append-only 存储，会保留所有变更的历史记录。此参数设置自动压缩 key 先前版本的间隔。默认值为 0（禁用），但在生产环境中通常设置为 1 小时（1h）或 24 小时（24h）。这有助于节省磁盘空间并提升性能。

2. **`--snapshot-count`**：指定 etcd 创建 snapshot 前要提交的事务数量。默认值为 100,000，但在大型集群中可调整此值以优化 snapshot 创建频率。较小的值会更频繁地创建 snapshot，从而缩短恢复时间，但会增加磁盘 I/O。

3. **SSD storage**：etcd 对磁盘 I/O 很敏感，因此使用 SSD（Solid State Drives）可显著提升性能。在大型集群中，使用 SSD 是必要的。

其他重要优化设置和最佳实践：

- **使用专用磁盘**：为 etcd 数据使用专用磁盘，以防止与其他应用程序发生 I/O 争用。
- **适当的内存分配**：etcd 会在内存中缓存数据以提升性能，因此必须分配足够的内存。
- **优化集群规模**：通常 3-5 个 etcd member 可提供最佳性能和可用性。
- **最小化网络延迟**：将 etcd member 放置在同一数据中心或 availability zone 中，以最小化 member 之间的网络延迟。
- **定期备份和压缩**：执行定期备份和 compaction，以确保数据安全并高效使用磁盘空间。

`--max-request-bytes` 和 `--quota-backend-bytes` 是实际的 etcd 参数，但主要与资源限制相关，而不是性能。`--max-concurrent-requests`、`--max-connections`、`--max-txn-ops` 和 `--max-result-buffer` 要么不是实际的 etcd 参数，要么不是性能优化的主要因素。
</details>

2. 在 Kubernetes 集群中实现 control plane 高可用性（HA）的最有效方式是什么？
   - A) Running multiple API server instances on a single master node
   - B) Configuring an etcd cluster with multiple master nodes and a load balancer
   - C) Deploying the API server as a StatefulSet with PersistentVolume
   - D) Implementing a watchdog process with auto-recovery on the master node

<details>
<summary>显示答案</summary>

**答案：B) Configuring an etcd cluster with multiple master nodes and a load balancer**

**解释：**
实现 Kubernetes control plane 高可用性（HA）的最有效方式，是配置包含多个 master Node 的 etcd 集群和一个 load balancer。此方法由以下组件组成：

1. **多个 master Node**：通常在不同 availability zone 中部署 3 个或 5 个 master Node，以消除单点故障。每个 master Node 运行以下 control plane 组件：
   - kube-apiserver：处理 API 请求的 server
   - kube-controller-manager：运行 controller 进程
   - kube-scheduler：Pod 调度决策

2. **etcd 集群**：etcd 是一个分布式 key-value store，用于存储所有 Kubernetes 集群数据。为实现高可用性，通常运行 3 个或 5 个 etcd 实例。etcd 可以直接运行在 master Node 上，也可以运行在专用 Node 上。

3. **Load balancer**：需要 load balancer 将客户端请求分发到多个 kube-apiserver 实例。这通常使用 cloud provider 的 load balancer 服务或 HAProxy、Nginx 等软件 load balancer 实现。

此配置的主要优势：
- **容错性**：即使一个 master Node 发生故障，集群也会继续运行。
- **高可用性**：跨多个 availability zone 部署甚至可以应对数据中心级别的故障。
- **可扩展性**：API server 请求可以分发到多个实例并由其处理。
- **数据一致性**：etcd 的 Raft 共识算法确保数据一致性。

其他选项的问题：
- 在单个 master Node 上运行多个 API server 实例，会使该 Node 本身成为单点故障。
- 将 API server 部署为 StatefulSet 不是常见做法，control plane 组件通常在 Kubernetes 外部管理。
- watchdog 进程可能有帮助，但其本身并不是真正的高可用性解决方案。
</details>

3. 在 Kubernetes 集群中配置 audit logging 时最重要的考虑事项是什么？
   - A) Logging all API requests to ensure complete audit trail
   - B) Using audit policies to selectively log only important events
   - C) Real-time streaming of audit logs to an external SIEM system
   - D) Restricting access to audit logs to administrators only

<details>
<summary>显示答案</summary>

**答案：B) Using audit policies to selectively log only important events**

**解释：**
配置 Kubernetes audit logging 时最重要的考虑事项，是使用 audit policy 有选择地仅记录重要事件。原因如下：

1. **最小化性能影响**：记录所有 API 请求会给 API server 带来显著负载并降低性能。大型集群每秒可能有数千个 API 请求。

2. **存储效率**：记录所有事件会导致日志数据快速增长，增加存储成本，并使日志分析变得困难。

3. **关注相关信息**：通过仅记录重要事件，安全分析人员可以关注关键信息。

4. **合规性**：许多合规要求需要记录特定类型的事件，而不是所有事件。

Kubernetes audit policy 支持以下 audit level：

- **None**：不记录该事件。
- **Metadata**：仅记录请求元数据（用户、时间戳、资源、操作等），并排除请求/响应正文。
- **Request**：记录元数据和请求正文，但排除响应正文。
- **RequestResponse**：记录元数据、请求正文和响应正文。

有效 audit policy 示例：
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
# Set logging level for authentication and authorization requests
- level: Metadata
  users: ["system:anonymous"]
  verbs: ["get", "list", "watch"]

# Log changes to sensitive resources like Secret, ConfigMap in detail
- level: Request
  resources:
  - group: ""
    resources: ["secrets", "configmaps"]
  verbs: ["create", "update", "patch", "delete"]

# Log important resource changes in detail
- level: RequestResponse
  resources:
  - group: ""
    resources: ["pods"]
  verbs: ["create", "update", "patch", "delete"]

# Log only metadata by default
- level: Metadata
```

其他选项的问题：
- 记录所有 API 请求可能导致性能和存储问题。
- 实时流式传输到外部 SIEM system 很重要，但优先级低于决定记录什么。
- 限制 audit log 访问权限很重要，但这是安全措施，而不是 logging policy 本身。
</details>

4. 在 Kubernetes 集群中实现 Node auto-repair 的最有效方式是什么？
   - A) Deploy a DaemonSet that monitors node status and automatically reboots problematic nodes
   - B) Utilize cloud provider's managed node groups and auto-repair features
   - C) Use Node Problem Detector and custom controllers for node status monitoring and recovery
   - D) Implement a cron job that periodically checks node status and recreates problematic nodes

<details>
<summary>显示答案</summary>

**答案：C) Use Node Problem Detector and custom controllers for node status monitoring and recovery**

**解释：**
在 Kubernetes 集群中实现 Node auto-repair 的最有效方式，是将 Node Problem Detector 与 custom controller 结合使用。此方法提供以下优势：

1. **准确的问题检测**：Node Problem Detector (NPD) 是专用工具，可检测多种 Node 问题，包括：
   - Kernel 错误和崩溃
   - 硬件问题
   - 文件系统问题
   - 网络问题
   - 资源短缺问题

2. **灵活响应**：Custom controller 允许针对检测到的问题实现多种恢复策略：
   - 轻微问题：Node 重启
   - 严重问题：Node 替换
   - 特定类型的问题：重启特定服务

3. **Kubernetes 原生集成**：NPD 将 Node 状态报告为 NodeConditions，与现有 Kubernetes 机制良好集成。

4. **与云无关**：此方法适用于所有环境（本地环境、各种 cloud provider）。

实施步骤：

1. **部署 Node Problem Detector**：
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **实现 custom controller**：
   - 监视 Kubernetes event 和 Node 状态变化
   - 实现响应特定 NodeConditions 的逻辑
   - 执行恢复操作（通过 SSH 执行命令、通过 cloud API 重新创建 Node 等）

3. **设置告警和日志记录**：
   - 为恢复操作配置告警
   - 记录问题和恢复操作

其他选项的问题：

- **DaemonSet 方法**：如果 Node 存在严重问题，DaemonSet 本身可能受到影响，并且很难检测所有类型的问题。

- **Cloud provider 的 managed node group**：绑定到特定 cloud provider，无法用于本地环境。可检测的问题类型也可能受限。

- **Cron job 方法**：响应时间慢，问题检测能力有限，并且必须在集群外部运行。

将 Node Problem Detector 与 custom controller 结合使用，可以实现适用于各种环境的强大且灵活的 Node auto-repair 解决方案。
</details>

5. 在 Kubernetes 集群中有效管理 RBAC（Role-Based Access Control）的最佳实践是什么？
   - A) Grant cluster-admin role to all users for ease of management
   - B) Define granular roles by namespace and apply the principle of least privilege
   - C) Consolidate all permissions into a single ClusterRole for consistency
   - D) Always use user certificates instead of service accounts for authentication

<details>
<summary>显示答案</summary>

**答案：B) Define granular roles by namespace and apply the principle of least privilege**

**解释：**
在 Kubernetes 集群中有效管理 RBAC（Role-Based Access Control）的最佳实践，是按 Namespace 定义细粒度 role，并应用最小权限原则。此方法提供以下优势：

1. **最小权限原则**：仅向用户和 service account 授予最低限度的必要权限，以最小化安全风险。这有助于保护集群免受意外变更或恶意操作影响。

2. **Namespace 隔离**：按 Namespace 定义 role 可加强团队或应用程序之间的逻辑隔离。这可以防止一个团队的错误影响另一个团队的资源。

3. **细粒度访问控制**：可以针对特定资源类型或操作精细控制权限。例如，可以授予开发人员管理 Pod 和 Service 的权限，同时限制修改 Secret 或 Namespace 本身的权限。

4. **便于审计**：使用细粒度 role 可以清晰记录谁可以执行哪些操作，使审计和合规更容易。

RBAC 最佳实践实施示例：

1. **按 Namespace 定义 role**：
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: developer
     namespace: development
   rules:
   - apiGroups: [""]
     resources: ["pods", "services", "configmaps"]
     verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
   - apiGroups: ["apps"]
     resources: ["deployments", "replicasets"]
     verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
   - apiGroups: [""]
     resources: ["secrets"]
     verbs: ["get", "list", "watch"]  # Only allow reading secrets
   ```

2. **创建 role binding**：
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: developer-binding
     namespace: development
   subjects:
   - kind: Group
     name: developers
     apiGroup: rbac.authorization.k8s.io
   roleRef:
     kind: Role
     name: developer
     apiGroup: rbac.authorization.k8s.io
   ```

3. **谨慎使用 cluster-level role**：
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRole
   metadata:
     name: pod-reader
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get", "list", "watch"]
   ```

4. **为 service account 设置细粒度权限**：
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: app-role
     namespace: production
   rules:
   - apiGroups: [""]
     resources: ["configmaps"]
     resourceNames: ["app-config"]  # Only access to specific ConfigMap
     verbs: ["get"]
   ```

其他选项的问题：

- **向所有用户授予 cluster-admin role**：这会带来严重安全风险。所有用户都将对集群中的所有资源拥有完全访问权限，使集群容易受到意外变更或恶意操作影响。

- **将所有权限合并到单个 ClusterRole 中**：这会使细粒度访问控制无法实现，并违反最小权限原则。

- **始终使用用户证书**：Service account 适合应用程序身份验证，而在所有情况下都使用用户证书会增加管理负担。根据具体情况选择适当的身份验证机制很重要。
</details>
