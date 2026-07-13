## Short Answer Questions

1. 说明在 Kubernetes 集群中备份和恢复 etcd 数据库的流程。

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
   - 外部集群存储
   - 云存储（S3、GCS 等）
   - 不同的物理位置

**etcd 恢复流程：**

1. **为恢复停止所有 API server：**
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

4. **从快照创建新的数据目录：**
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
- 备份前验证 etcd 集群状态
- 验证备份文件完整性
- 定期测试恢复流程
- 在备份文件中包含时间戳
- 保留多个备份版本
- 记录备份和恢复流程文档
</details>

2. 说明 Kubernetes 集群中节点维护的流程，以及 `cordon`、`drain` 和 `uncordon` 命令之间的区别。

<details>
<summary>显示答案</summary>

**答案：**

**节点维护流程：**

1. **检查节点状态：**
   ```bash
   kubectl get nodes
   kubectl describe node <node_name>
   ```

2. **Cordon 节点：**
   ```bash
   kubectl cordon <node_name>
   ```

3. **Drain 节点：**
   ```bash
   kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
   ```

4. **执行维护：**
   - 软件更新
   - Kernel 升级
   - 硬件更换
   - 配置变更

5. **工作完成后 uncordon 节点：**
   ```bash
   kubectl uncordon <node_name>
   ```

6. **验证节点状态：**
   ```bash
   kubectl get nodes
   ```

**命令区别：**

1. **`kubectl cordon <node_name>`：**
   - 将节点标记为不可调度。
   - 新的 Pod 不会被调度到该节点。
   - 已经运行的 Pod 会继续运行。
   - 节点状态中会出现 `SchedulingDisabled` 指示。

2. **`kubectl drain <node_name>`：**
   - 将节点标记为不可调度（包含 cordon）。
   - 安全地驱逐在该节点上运行的 Pod。
   - Pod 会被重新调度到其他节点。
   - DaemonSet Pod 默认会被忽略（需要 `--ignore-daemonsets` 标志）。
   - 使用 emptyDir 卷的 Pod 可能会丢失数据，需要特殊处理（`--delete-emptydir-data` 标志）。
   - 遵守 PodDisruptionBudget。

3. **`kubectl uncordon <node_name>`：**
   - 将节点重新标记为可调度。
   - 新的 Pod 可以被调度到该节点。
   - 之前被驱逐的 Pod 不会自动返回。

**维护注意事项：**
- 确保集群中有足够容量
- 为关键工作负载设置 PodDisruptionBudget
- 一次只维护一个节点
- 在维护期间调整自动扩缩设置
- 在维护前后验证工作负载状态
- 使用滚动更新策略
</details>

3. 说明如何在 Kubernetes 集群中监控和管理资源使用情况。列出应包含的工具和技术。

<details>
<summary>显示答案</summary>

**答案：**

**Kubernetes 资源监控和管理方法：**

**1. 基础监控工具：**

- **Metrics Server：**
  - 提供基本的 CPU 和内存使用指标
  - 支持 `kubectl top` 命令
  - 安装：
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    ```
  - 使用方法：
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Kubernetes Dashboard：**
  - 以可视化方式呈现集群状态和资源使用情况
  - 提供用于管理 Pod、节点、namespace 等的界面

**2. 高级监控栈：**

- **Prometheus + Grafana：**
  - Prometheus：指标收集和存储
  - Grafana：指标可视化和仪表板
  - 可通过 kube-prometheus-stack 或 Prometheus Operator 安装
  - 支持自定义告警规则和仪表板

- **ELK/EFK Stack：**
  - Elasticsearch：日志存储和搜索
  - Logstash/Fluentd：日志收集和处理
  - Kibana：日志可视化和分析

**3. 资源管理技术：**

- **设置资源请求和限制：**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **Namespace 级资源配额（ResourceQuota）：**
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
  - 自动调整 Pod CPU 和内存请求
  - 基于资源使用模式提供建议

- **Cluster Autoscaler：**
  - 根据工作负载需求自动调整集群节点数量
  - 在资源不足时添加节点，在利用率较低时移除节点

**4. 监控最佳实践：**

- 为所有 Pod 设置资源请求和限制
- 为重要指标配置告警
- 通过历史使用情况分析规划资源
- 定期执行资源审计
- 分析资源使用趋势以优化成本
- 为开发、预发布和生产环境设置适当的资源配额
- 同时监控节点级和 Pod 级指标
</details>

4. 说明 Kubernetes 集群升级期间可能出现的主要风险以及缓解策略。

<details>
<summary>显示答案</summary>

**答案：**

**Kubernetes 集群升级风险和缓解策略：**

**1. 主要风险：**

- **API 兼容性问题：**
  - API 可能在新版本中发生变化或被移除
  - 某些 Custom Resource Definitions (CRDs) 或 API 版本可能不再受支持

- **工作负载中断：**
  - 由于控制平面组件重启，API server 可能暂时不可用
  - 节点升级期间由于 Pod 重新调度导致 Service 中断

- **功能变更：**
  - 默认行为变化可能影响现有工作负载
  - 安全策略变化可能导致权限问题

- **性能问题：**
  - 新版本中的资源需求可能增加
  - 初始稳定期可能出现性能下降

- **回滚复杂性：**
  - 某些升级无法轻松回滚
  - 由于数据格式变化导致回滚受限

**2. 缓解策略：**

- **充分规划和准备：**
  - **查看 changelog：**检查新版本中的变更、弃用功能和已知问题
  - **验证升级路径：**确认支持从当前版本直接升级到目标版本
  - **审查资源需求：**检查新版本的最低要求

- **先在测试环境中测试：**
  - 在与生产环境类似的测试集群上执行升级
  - 测试所有关键工作负载和自定义资源
  - 运行自动化测试套件

- **验证 API 兼容性：**
  - 检查正在使用的 API 版本：
    ```bash
    kubectl api-resources -o wide
    ```
  - 检查弃用 API 的使用：
    ```bash
    kubectl get -A | grep "deprecated"
    ```
  - 按需更新 manifest

- **备份和恢复计划：**
  - 备份 etcd 数据库：
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db
    ```
  - 备份所有重要 manifest：
    ```bash
    kubectl get all --all-namespaces -o yaml > all-resources.yaml
    ```
  - 记录并测试恢复流程

- **渐进式升级方法：**
  - **先升级控制平面组件：**
    - 在高可用部署中，一次升级一个控制平面节点
  - **Worker 节点滚动升级：**
    - 将节点组划分为小批次进行升级
    - 每个批次后验证稳定性

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
  - **Drain 节点时要谨慎：**
    ```bash
    kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
    ```

- **增强监控：**
  - 在升级前、升级期间和升级后监控集群状态
  - 密切观察关键指标和日志
  - 临时调整告警阈值

- **回滚计划：**
  - 定义回滚触发条件
  - 记录回滚流程
  - 保留回滚所需的所有组件和镜像

- **沟通计划：**
  - 通知所有利益相关方升级计划和预期影响
  - 在升级期间提供状态更新
  - 定义出现问题时的升级处理路径

**3. 版本特定注意事项：**

- **次版本升级（例如 1.24 → 1.25）：**
  - 特别注意被移除的 API 和功能变更
  - 一次只升级一个次版本

- **补丁版本升级（例如 1.24.0 → 1.24.1）：**
  - 通常更安全，但仍然需要测试
  - 对安全补丁可考虑更快部署
</details>

5. 说明 Kubernetes 集群中可能出现的常见网络问题，以及如何诊断和解决这些问题。

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
  - 检查网络策略：
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - 创建测试 Pod 测试连接性：
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
  - 修改或移除网络策略
  - 检查节点网络接口
  - 检查防火墙规则

**2. Service 发现和 DNS 问题：**

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
  - 检查 Service endpoints：
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
  - 无法从外部访问 Service
  - Ingress 规则不起作用
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
  - 检查 endpoints：
    ```bash
    kubectl get endpoints <service_name>
    ```

- **解决方法：**
  - 验证 Service selector 与 Pod label 匹配
  - 重新安装或更新 ingress controller
  - 验证 Service type 和端口配置
  - 检查云提供商 Load Balancer 设置

**4. 节点网络问题：**

- **症状：**
  - 节点与集群断开连接
  - 节点之间通信失败
  - kubelet 连接错误

- **诊断方法：**
  - 检查节点状态：
    ```bash
    kubectl describe node <node_name>
    ```
  - 检查节点网络接口：
    ```bash
    # Run directly on node
    ip addr
    ip route
    ```
  - 检查防火墙规则：
    ```bash
    # Run directly on node
    iptables -L
    ```
  - 检查 kubelet 日志：
    ```bash
    journalctl -u kubelet
    ```

- **解决方法：**
  - 重新配置节点网络接口
  - 修改防火墙规则
  - 重启 kubelet
  - 如有必要，重启节点

**5. Network Policy 问题：**

- **症状：**
  - 意外的连接阻断
  - 特定 namespace 之间无法通信
  - 只有部分 Pod 可访问

- **诊断方法：**
  - 检查网络策略：
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - 检查 Pod label：
    ```bash
    kubectl get pods --show-labels
    ```
  - 验证网络 plugin 支持 network policy

- **解决方法：**
  - 修改或删除网络策略
  - 修改 Pod label
  - 使用 network policy 调试工具

**6. 通用网络调试工具：**

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

- **CNI plugin 特定调试工具：**
  - Calico：`calicoctl`
  - Cilium：`cilium`
  - Weave：`weave`

**7. 最佳实践：**

- 记录网络拓扑文档
- 定期执行连接性测试
- 在网络策略变更前分析影响
- 规划集群网络 CIDR 范围
- 实施网络监控工具
</details>
## Hands-on Questions

1. 编写一个满足以下要求的 ResourceQuota manifest：
   - Namespace：development
   - 最大 Pod 数：20
   - 最大 CPU requests：4 cores
   - 最大 memory requests：8Gi
   - 最大 PVC 数：10
   - 最大 storage requests：100Gi

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

此 ResourceQuota 为 'development' namespace 设置以下限制：
- 最多 20 个 Pod
- CPU requests 总计 4 cores
- memory requests 总计 8Gi
- 最多 10 个 PersistentVolumeClaims
- storage requests 总计 100Gi

应用 ResourceQuota：
```bash
kubectl apply -f resource-quota.yaml
```

检查当前配额使用情况：
```bash
kubectl describe quota dev-quota -n development
```

注意：应用 ResourceQuota 之前必须先存在该 namespace。如果 namespace 不存在，请先创建：
```bash
kubectl create namespace development
```
</details>

2. 编写一个脚本，检查集群中所有节点上的 kubelet 服务状态，并在存在问题时进行解决。

<details>
<summary>显示答案</summary>

**答案：**

```bash
#!/bin/bash
# Filename: check_kubelet.sh
# Description: Check kubelet service status on all nodes and troubleshoot

# Get node list
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

# Loop through each node
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
      echo "Failed to start kubelet service. Checking logs..."
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
1. 使用 `kubectl get nodes` 获取集群中所有节点列表。
2. 对每个节点：
   - 检查节点的 Ready 状态。
   - 通过 SSH 连接到节点以检查 kubelet 服务状态。
   - 如果 kubelet 未运行，则启动服务。
   - 启动服务后再次检查状态。
   - 如果启动失败，则检查日志。
   - 检查 kubelet 配置文件中的关键设置。

**用法：**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
```

**注意事项：**
- 运行此脚本需要对所有节点具有 SSH 访问权限。
- 建议在生产环境中使用基于 SSH key 的认证。
- 在云环境中，对节点的直接 SSH 访问可能受到限制，需要使用云提供商的节点管理工具。
</details>

3. 设置一个 cron job，用于备份集群的 etcd 数据库，并将备份文件存储在安全位置。

<details>
<summary>显示答案</summary>

**答案：**

**1. 创建备份脚本：**

```bash
#!/bin/bash
# Filename: backup_etcd.sh
# Description: Backup etcd database and store remotely

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

**3. 设置 Cron Job：**

```bash
# Edit root user's crontab
sudo crontab -e
```

添加以下内容：

```
# Run etcd backup at 2 AM daily
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

要在备份失败时接收告警，可以与监控工具（例如 Prometheus）集成。将以下代码添加到备份脚本中：

```bash
# Create file indicating backup success
if [ $? -eq 0 ]; then
  echo "success" > /var/lib/node_exporter/etcd_backup_status.prom
else
  echo "failure" > /var/lib/node_exporter/etcd_backup_status.prom
fi
```

**注意事项：**
- 备份文件应存储在集群外部的安全位置。
- 在云环境中，建议使用 S3、GCS 等对象存储。
- 定期测试备份恢复以验证备份有效性。
- 对于高可用 etcd 集群，只需在一个 etcd 实例上执行备份。
</details>
4. 编写一个对集群中所有节点执行滚动更新的流程。更新期间必须保持工作负载可用性。

<details>
<summary>显示答案</summary>

**答案：**

**节点滚动更新流程：**

```bash
#!/bin/bash
# Filename: node_rolling_update.sh
# Description: Perform cluster node rolling update

# Variable settings
UPGRADE_COMMAND="sudo apt update && sudo apt upgrade -y"
REBOOT_REQUIRED_CHECK="[ -f /var/run/reboot-required ]"
MAX_UNAVAILABLE=1  # Number of nodes to update at a time

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

echo "Updating $NODE_COUNT nodes in total."
echo "Node list: $NODES"
echo "Maximum $MAX_UNAVAILABLE nodes will be updated at a time."
echo "Press Enter to continue. Press Ctrl+C to cancel."
read

# Loop through each node
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

  # Check if reboot required
  REBOOT_REQUIRED=$(ssh $NODE "$REBOOT_REQUIRED_CHECK && echo 'true' || echo 'false'")

  if [ "$REBOOT_REQUIRED" == "true" ]; then
    echo "Node reboot required. Rebooting..."
    ssh $NODE "sudo reboot"

    # Wait until node becomes Ready again
    echo "Node rebooting. Waiting until Ready..."
    while true; do
      STATUS=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
      if [ "$STATUS" == "True" ]; then
        echo "Node is Ready."
        break
      fi
      echo "Node not Ready yet. Checking again in 10 seconds."
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

  # Wait for pods to be rescheduled to node
  echo "Waiting for pods to be rescheduled to node..."
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

**滚动更新前准备：**

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
   验证当移除一个节点时，其余节点能够承载所有工作负载。

3. **执行备份：**
   升级前执行 etcd 数据库备份。

**滚动更新最佳实践：**

1. **渐进式方法：**
   - 一次只更新一个节点
   - 每次节点更新后验证集群状态

2. **自动化和幂等性：**
   - 使用脚本自动化流程
   - 设计为失败时可安全重试

3. **增强监控：**
   - 更新期间监控集群指标
   - 监控应用状态和性能

4. **回滚计划：**
   - 准备出现问题时的回滚流程
   - 确保有恢复到先前状态的方法

5. **沟通：**
   - 公告更新计划和预期影响
   - 定期报告更新进度

**注意事项：**
- 在云环境中，可以使用托管 Kubernetes 服务（EKS、GKE、AKS 等）的节点更新功能。
- 如果有多个节点组，请按组执行更新。
- 特别监控重要系统 Pod（CoreDNS、kube-proxy 等）的状态。
</details>

5. 编写一个脚本，用于识别集群中资源使用率较高的 Pod，并生成包含这些信息的报告。

<details>
<summary>显示答案</summary>

**答案：**

```bash
#!/bin/bash
# Filename: resource_usage_report.sh
# Description: Identify pods with high resource usage and generate report

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
echo "===== Pods with High Resource Usage Relative to Requests =====" >> $REPORT_FILE
echo "Collecting pod information..." >> $REPORT_FILE

# Create temporary files
PODS_USAGE_FILE="$REPORT_DIR/pods-usage-$DATE.tmp"
PODS_REQUESTS_FILE="$REPORT_DIR/pods-requests-$DATE.tmp"

# Collect current usage
kubectl top pods --all-namespaces | tail -n +2 > $PODS_USAGE_FILE

# Collect resource requests for all namespaces
echo "Namespace,Pod,CPURequest(m),MemoryRequest(Mi)" > $PODS_REQUESTS_FILE
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get pods -n $ns -o jsonpath='{range .items[*]}{.metadata.namespace},{.metadata.name},{range .spec.containers[*]}{.resources.requests.cpu}{","}{.resources.requests.memory}{"\n"}{end}{end}' | sed 's/$/,/' | sed 's/,$//' >> $PODS_REQUESTS_FILE
done

# Calculate usage relative to requests and add to report
echo "Pods with high CPU utilization (usage/request > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  cpu_usage=$(echo $line | awk '{print $3}' | sed 's/m//')

  # Find CPU request for this pod
  cpu_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $3}' | sed 's/[^0-9m.]//g' | sed 's/m//')

  # Show "Not set" if no CPU request
  if [ -z "$cpu_request" ] || [ "$cpu_request" == "" ]; then
    echo "$ns/$pod: CPU usage ${cpu_usage}m, request not set" >> $REPORT_FILE
  else
    # Calculate CPU utilization
    cpu_percentage=$(echo "scale=2; $cpu_usage / $cpu_request * 100" | bc)

    # Show only if utilization is 80% or higher
    if (( $(echo "$cpu_percentage >= 80" | bc -l) )); then
      echo "$ns/$pod: CPU usage ${cpu_usage}m, request ${cpu_request}m, utilization ${cpu_percentage}%" >> $REPORT_FILE
    fi
  fi
done < $PODS_USAGE_FILE

echo "" >> $REPORT_FILE
echo "Pods with high memory utilization (usage/request > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  mem_usage=$(echo $line | awk '{print $4}' | sed 's/Mi//')

  # Find memory request for this pod
  mem_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $4}' | sed 's/[^0-9Mi.]//g' | sed 's/Mi//')

  # Show "Not set" if no memory request
  if [ -z "$mem_request" ] || [ "$mem_request" == "" ]; then
    echo "$ns/$pod: Memory usage ${mem_usage}Mi, request not set" >> $REPORT_FILE
  else
    # Calculate memory utilization
    mem_percentage=$(echo "scale=2; $mem_usage / $mem_request * 100" | bc)

    # Show only if utilization is 80% or higher
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

# Generate HTML report (optional)
HTML_REPORT="${REPORT_FILE%.txt}.html"
echo "<html><head><title>Kubernetes Resource Usage Report</title>" > $HTML_REPORT
echo "<style>body{font-family:Arial;margin:20px}h1{color:#326ce5}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px}th{background-color:#f2f2f2}</style>" >> $HTML_REPORT
echo "</head><body>" >> $HTML_REPORT
echo "<h1>Kubernetes Cluster Resource Usage Report</h1>" >> $HTML_REPORT
echo "<p>Generated: $(date)</p>" >> $HTML_REPORT

# Convert report content to HTML
awk '/===== Cluster Information =====/{flag=1;print "<h2>Cluster Information</h2><pre>"}/===== Node Resource Usage =====/{flag=0;print "</pre><h2>Node Resource Usage</h2><table><tr><th>Node</th><th>CPU(%)</th><th>Memory(%)</th></tr>"}/===== Top.*CPU Usage/{flag=0;print "</table><h2>Top Pods by CPU Usage</h2><table><tr><th>Namespace</th><th>Pod</th><th>CPU(m)</th><th>Memory(Mi)</th></tr>"}/===== Top.*Memory Usage/{flag=0;print "</table><h2>Top Pods by Memory Usage</h2><table><tr><th>Namespace</th><th>Pod</th><th>CPU(m)</th><th>Memory(Mi)</th></tr>"}/===== Resource Usage by Namespace =====/{flag=0;print "</table><h2>Resource Usage by Namespace</h2>"}/CPU Usage \(cores\):/{flag=0;print "<h3>CPU Usage (cores)</h3><table><tr><th>Namespace</th><th>CPU(cores)</th></tr>"}/Memory Usage \(GiB\):/{flag=0;print "</table><h3>Memory Usage (GiB)</h3><table><tr><th>Namespace</th><th>Memory(GiB)</th></tr>"}/===== Pods with High Resource Usage Relative to Requests =====/{flag=0;print "</table><h2>Pods with High Resource Usage Relative to Requests</h2>"}/Pods with high CPU utilization/{flag=0;print "<h3>Pods with High CPU Utilization (usage/request > 80%)</h3><ul>"}/Pods with high memory utilization/{flag=0;print "</ul><h3>Pods with High Memory Utilization (usage/request > 80%)</h3><ul>"}/===== Pods Without Resource Requests =====/{flag=0;print "</ul><h2>Pods Without Resource Requests</h2><ul>"}/===== Report Summary =====/{flag=0;print "</ul><h2>Report Summary</h2><ul>"}{if(flag==1)print;else if($0 ~ /^NAME/){print "<tr>";for(i=1;i<=NF;i++)print "<th>"$i"</th>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]%/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]m/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].* [0-9]/){print "<tr><td>"$1"</td><td>"$2"</td></tr>"}else if($0 ~ /^[a-z].*\//){print "<li>"$0"</li>"}else if($0 ~ /^Total/){print "<li>"$0"</li>"}}' $REPORT_FILE >> $HTML_REPORT

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
2. 收集节点资源使用情况
3. 识别按 CPU 和内存使用率排序的前几个 Pod
4. 按 namespace 计算资源使用情况
5. 识别相对于 requests 使用率较高的 Pod
6. 识别未设置资源 requests 的 Pod
7. 生成文本和 HTML 格式的报告

**注意事项：**
- 运行此脚本需要 `kubectl`、`jq`、`bc` 工具。
- 集群中必须安装 Metrics Server。
- 在大型集群中，脚本执行时间可能较长。
- 可以设置为 cron job 以定期生成报告。
- 报告可以通过电子邮件发送或与监控系统集成。
</details>
## Advanced Topics

1. 在 Kubernetes 集群中，优化 etcd 性能的关键配置参数和最佳实践是什么？
   - A) `--max-request-bytes`, `--quota-backend-bytes`, 定期压缩
   - B) `--max-concurrent-requests`, `--max-connections`, 磁盘 RAID 配置
   - C) `--auto-compaction-retention`, `--snapshot-count`, 使用 SSD 存储
   - D) `--max-txn-ops`, `--max-result-buffer`, 扩展内存

<details>
<summary>显示答案</summary>

**答案：C) `--auto-compaction-retention`, `--snapshot-count`, 使用 SSD 存储**

**解释：**
etcd 是 Kubernetes 集群的核心数据存储，其性能直接影响整体集群性能。优化 etcd 性能的关键配置参数和最佳实践如下：

1. **`--auto-compaction-retention`**：etcd 是一个 append-only 存储，会维护所有变更的历史记录。此参数设置自动压缩 key 先前版本的周期。默认值为 0（禁用），但在生产环境中通常设置为 1 小时（1h）或 24 小时（24h）。这可以节省磁盘空间并提升性能。

2. **`--snapshot-count`**：指定 etcd 创建快照前要提交的事务数量。默认值为 100,000，但对于大型集群，可以调整该值以优化快照创建频率。较小的值意味着更频繁的快照，可减少恢复时间，但会增加磁盘 I/O。

3. **SSD storage usage**：etcd 对磁盘 I/O 敏感，因此使用 SSD（Solid State Drives）可以显著提升性能。尤其对于大型集群，使用 SSD 是必要的。

其他重要的优化设置和最佳实践：

- **使用专用磁盘**：为 etcd 数据使用专用磁盘，防止与其他应用程序发生 I/O 争用。
- **适当的内存分配**：etcd 会在内存中缓存数据以提升性能，因此应分配足够的内存。
- **集群规模优化**：通常 3-5 个 etcd member 可提供最佳性能和可用性。
- **最小化网络延迟**：将 etcd member 放置在同一数据中心或可用区，以最大限度减少 member 之间的网络延迟。
- **定期备份和压缩**：定期执行备份和压缩，以确保数据安全并高效使用磁盘空间。

`--max-request-bytes` 和 `--quota-backend-bytes` 是实际的 etcd 参数，但它们主要与资源限制相关，而不是性能。`--max-concurrent-requests`、`--max-connections`、`--max-txn-ops`、`--max-result-buffer` 不是实际的 etcd 参数，或不是性能优化的关键因素。
</details>

2. 在 Kubernetes 集群中实现控制平面高可用性（HA）的最有效方式是什么？
   - A) 在单个 master node 上运行多个 API server 实例
   - B) 配置包含多个 master node 和 load balancer 的 etcd 集群
   - C) 将 API server 部署为 StatefulSet 并使用 PersistentVolume
   - D) 在 master node 上实现带自动恢复的 watch 进程

<details>
<summary>显示答案</summary>

**答案：B) 配置包含多个 master node 和 load balancer 的 etcd 集群**

**解释：**
实现 Kubernetes 控制平面高可用性（HA）的最有效方式，是配置包含多个 master 节点和 load balancer 的 etcd 集群。此方法由以下组件组成：

1. **多个 master 节点**：通常在不同可用区部署 3 个或 5 个 master 节点，以消除单点故障。每个 master 节点运行以下控制平面组件：
   - kube-apiserver：处理 API 请求的服务器
   - kube-controller-manager：运行 controller 进程
   - kube-scheduler：做出 Pod 调度决策

2. **etcd 集群**：etcd 是一个分布式 key-value 存储，用于存储所有集群数据。为了实现高可用性，通常运行 3 个或 5 个 etcd 实例。etcd 可以直接运行在 master 节点上，也可以运行在单独的专用节点上。

3. **Load balancer**：需要一个 load balancer 将客户端请求分发到多个 kube-apiserver 实例。这通常通过云提供商的 load balancer 服务，或 HAProxy、Nginx 等软件 load balancer 实现。

此配置的关键优势：
- **容错能力**：如果一个 master 节点故障，集群仍会继续运行。
- **高可用性**：跨多个可用区部署可以应对数据中心级别故障。
- **可扩展性**：API server 请求可以分发到多个实例并进行处理。
- **数据一致性**：通过 etcd 的 Raft 共识算法确保数据一致性。

其他选项的问题：
- 在单个 master 节点上运行多个 API server 实例会使该节点本身成为单点故障。
- 将 API server 部署为 StatefulSet 不是常见方法；控制平面组件通常在 Kubernetes 外部管理。
- watch 进程可以提供帮助，但其本身不是真正的高可用解决方案。
</details>

3. 配置 Kubernetes 集群中的 Audit Logging 时，最重要的考虑事项是什么？
   - A) 记录所有 API 请求以获得完整审计追踪
   - B) 使用 audit policy 仅选择性记录重要事件
   - C) 将 audit log 实时发送到外部 SIEM 系统
   - D) 仅允许管理员访问 audit log

<details>
<summary>显示答案</summary>

**答案：B) 使用 audit policy 仅选择性记录重要事件**

**解释：**
配置 Kubernetes Audit Logging 时，最重要的考虑事项是使用 audit policy 仅选择性记录重要事件。这很重要，原因如下：

1. **最小化性能影响**：记录所有 API 请求可能对 API server 造成显著负载并降低性能。尤其在大型集群中，每秒可能产生数千个 API 请求。

2. **存储效率**：记录所有事件会导致日志数据量快速增长，增加存储成本，并使日志分析变得困难。

3. **关注相关信息**：仅记录重要事件可以让安全分析人员专注于关键信息。

4. **合规性**：许多合规要求需要记录特定类型的事件，而不是所有事件。

Kubernetes audit policy 支持以下审计级别：

- **None**：不记录事件。
- **Metadata**：仅记录请求元数据（用户、时间戳、资源、操作等），不包含请求/响应正文。
- **Request**：记录元数据和请求正文，但不包含响应正文。
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

# Log changes to sensitive resources like Secrets, ConfigMaps in detail
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
- 将日志实时传输到外部 SIEM 系统很重要，但优先级低于决定记录什么。
- 限制 audit log 访问权限很重要，但它是安全措施，而不是日志策略本身。
</details>

4. 在 Kubernetes 集群中实现 Node Auto-Repair 的最有效方式是什么？
   - A) 部署 DaemonSet 监控节点状态并自动重启有问题的节点
   - B) 使用云提供商的托管节点组和 auto-repair 功能
   - C) 使用 Node Problem Detector 和自定义 controller 进行节点状态监控和修复
   - D) 实现 cron job 定期检查节点状态并重建有问题的节点

<details>
<summary>显示答案</summary>

**答案：C) 使用 Node Problem Detector 和自定义 controller 进行节点状态监控和修复**

**解释：**
在 Kubernetes 集群中实现 Node Auto-Repair 的最有效方式，是将 Node Problem Detector 与自定义 controller 一起使用。此方法提供以下优势：

1. **准确的问题检测**：Node Problem Detector (NPD) 是一个专用工具，可检测各种节点问题。它可以检测以下问题：
   - Kernel 错误和崩溃
   - 硬件问题
   - 文件系统问题
   - 网络问题
   - 资源不足问题

2. **灵活响应**：使用自定义 controller 可以针对检测到的问题实现多种恢复策略：
   - 轻微问题：节点重启
   - 严重问题：节点替换
   - 特定类型问题：重启特定服务

3. **Kubernetes 原生集成**：NPD 将节点状态报告为 NodeConditions，可与现有 Kubernetes 机制良好集成。

4. **云无关**：此方法适用于所有环境（本地部署、各种云提供商）。

实现步骤：

1. **部署 Node Problem Detector**：
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **实现自定义 controller**：
   - Watch Kubernetes 事件和节点状态变化
   - 实现响应特定 NodeConditions 的逻辑
   - 执行恢复操作（通过 SSH 执行命令、通过云 API 重建节点等）

3. **设置告警和日志：**
   - 为恢复操作配置告警
   - 记录问题和恢复操作日志

其他选项的问题：

- **DaemonSet 方法**：如果节点存在严重问题，DaemonSet 本身可能受到影响，并且很难检测所有类型的问题。

- **云提供商的托管节点组**：依赖特定云提供商，无法在本地环境中使用。此外，可检测的问题类型可能有限。

- **Cron job 方法**：响应时间慢，问题检测能力有限，并且必须在集群外部运行。

将 Node Problem Detector 与自定义 controller 结合使用，可以实现一个适用于各种环境、健壮且灵活的节点自动修复解决方案。
</details>

5. 在 Kubernetes 集群中有效管理 RBAC (Role-Based Access Control) 的最佳实践是什么？
   - A) 为便于管理，向所有用户授予 cluster-admin role
   - B) 按 namespace 定义细粒度 role 并应用最小权限原则
   - C) 为保持一致性，将所有权限合并到单个 ClusterRole
   - D) 始终使用用户证书而不是 service account 进行认证

<details>
<summary>显示答案</summary>

**答案：B) 按 namespace 定义细粒度 role 并应用最小权限原则**

**解释：**
在 Kubernetes 集群中有效管理 RBAC (Role-Based Access Control) 的最佳实践，是按 namespace 定义细粒度 role 并应用最小权限原则。此方法提供以下优势：

1. **最小权限原则**：仅向用户和 service account 授予必要的最低权限，以最大限度降低安全风险。这有助于保护集群免受非预期变更或恶意行为影响。

2. **Namespace 隔离**：按 namespace 定义 role 可加强团队或应用之间的逻辑隔离。这可以防止一个团队的错误影响另一个团队的资源。

3. **细粒度访问控制**：可以针对特定资源类型或操作精细控制权限。例如，可以授予开发人员管理 Pod 和 Service 的权限，但限制其修改 Secret 或 namespace 本身的权限。

4. **便于审计**：使用细粒度 role 可以清楚记录谁能执行哪些操作，使审计和合规更加容易。

RBAC 最佳实践实现示例：

1. **按 namespace 定义 role**：
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
     verbs: ["get", "list", "watch"]  # Allow only reading secrets
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

3. **谨慎使用集群级 role**：
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

- **向所有用户授予 cluster-admin role**：这会造成严重安全风险。所有用户都拥有对所有集群资源的完全访问权限，会使系统容易受到非预期变更或恶意行为影响。

- **将所有权限合并到单个 ClusterRole**：这会导致无法进行细粒度访问控制，并违反最小权限原则。

- **始终使用用户证书**：service account 适用于应用认证，在所有场景中使用用户证书会增加管理负担。根据场景选择合适的认证机制很重要。
</details>
