# 集群管理测验

本测验涵盖自管集群和 EKS 的运维、备份、维护、监控与恢复，并保留原有的 15 个练习。主机级 etcd 操作流程不适用于由服务管理的 EKS 控制平面。

## 简答题

1. 说明 Kubernetes 集群中 etcd 数据库的备份和恢复流程。

<details>
<summary>显示答案</summary>

**答案：**

**etcd 备份流程：**

1. **验证 etcdctl 工具已安装：**
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
   etcdutl snapshot status snapshot.db --write-out=table
   ```

4. **将备份文件存储在安全位置：**
   - 集群外部存储
   - 云存储（如 S3、GCS）
   - 其他物理位置

**etcd 恢复流程：**

1. 验证 snapshot，并保留原始数据、PKI 和 encryption-provider 密钥/配置。etcd snapshot 不包含 PV 文件或所有主机配置。
2. 按所用发行版的运行手册停止所有 API server 和受影响的 etcd 进程。kubeadm 通常通过 static Pod 运行这些组件，而不是独立的 systemd unit；仅停止 kubelet 并不会停止这些容器。
3. 使用兼容版本的 etcdutl 离线恢复到新目录。以下单成员示例不是 HA 恢复命令：

```bash
etcdutl snapshot restore snapshot.db \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

4. 对于 HA，将同一 snapshot 恢复到每个成员，为每个成员指定其名称/peer URL，并使用完全一致的成员列表。revision bump 应足够高，超过 snapshot 之后发生的写入，并使 watch cache 失效。
5. 将 etcd manifest/service 指向恢复后的数据目录，确保 owner 和证书正确。重新启动 API server/controller 之前，先验证 etcd quorum/health；随后验证 node 和 workload。
6. 遵循[官方恢复流程](https://etcd.io/docs/v3.6/op-guide/recovery/)。EKS 用户应通过受支持的备份工具恢复应用程序资源/数据，而不是访问托管 etcd。

**最佳实践：**
- 制定定期备份计划（例如每日备份）
- 备份前检查 etcd 集群状态
- 验证备份文件完整性
- 定期测试恢复流程
- 在备份文件名中加入时间戳
- 保留多个版本的备份
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
   kubectl drain <node_name> --ignore-daemonsets
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
   - Workload controller 可能会创建替代 Pod；是否能调度取决于可用容量和约束条件。
   - 不提供 `--ignore-daemonsets` 时，drain 会拒绝处理 DaemonSet Pod；提供该标志会让它们继续运行。
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
  - Kubernetes 1.34+ 的安装示例（请先核对要求并检查是否已安装）：
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml
    ```
  - 使用示例：
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Headlamp（Kubernetes Dashboard 已归档）：**
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
  - 列出当前提供的 API 版本（这并不能盘点客户端实际使用情况）：
    ```bash
    kubectl api-resources -o wide
    ```
  - 在允许访问 `/metrics` 时检查已观测到的弃用 API 请求；同时审计 manifests 和请求日志：
    ```bash
    kubectl get --raw /metrics | grep '^apiserver_requested_deprecated_apis'
    ```
  - 根据需要更新 manifest

- **备份和恢复计划：**
  - 备份 etcd 数据库：
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
      --endpoints=https://127.0.0.1:2379 \
      --cacert=/etc/kubernetes/pki/etcd/ca.crt \
      --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
      --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
    ```
  - 导出部分 workload 对象（不是完整备份；应妥善保护导出内容）：
    ```bash
    umask 077
    kubectl get all --all-namespaces -o yaml > workload-subset.yaml
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
    kubectl drain <node_name> --ignore-daemonsets
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

**Kubernetes 网络问题诊断与排查：**

**1. Pod 间通信问题：**

- **症状：**
  - Pod 无法与其他 Pod 通信
  - 无法通过 Service 名称连接
  - 网络超时

- **诊断方法：**
  - 查看 NetworkPolicy：
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - 创建测试 Pod 检查连通性：
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    ping <target_pod_IP>
    wget -O- <service_name>:<port>
    ```
  - 检查 CNI 插件 Pod 状态：
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **解决方法：**
  - 重新安装或升级 CNI 插件
  - 调整或删除造成阻断的 NetworkPolicy
  - 检查节点网络接口
  - 检查防火墙规则

**2. Service 发现与 DNS 问题：**

- **症状：**
  - 无法通过 Service 名称连接
  - DNS 查询失败
  - 连接间歇性中断

- **诊断方法：**
  - 检查 CoreDNS Pod 状态和日志：
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - 测试 DNS 查询并查看 Pod 的 resolver 配置：
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
  - 检查 kubelet 的 DNS 设置

**3. Service 与 Ingress 问题：**

- **症状：**
  - 外部来源无法访问 Service
  - Ingress 规则未生效
  - 未能创建 LoadBalancer

- **诊断方法：**
  - 查看 Service 状态：
    ```bash
    kubectl describe service <service_name>
    ```
  - 查看 Ingress 状态：
    ```bash
    kubectl describe ingress <ingress_name>
    ```
  - 查看 ingress controller Pod 日志：
    ```bash
    kubectl logs -n <ingress_namespace> <ingress_controller_pod>
    ```
  - 检查 endpoints：
    ```bash
    kubectl get endpoints <service_name>
    ```

- **解决方法：**
  - 验证 Service selector 与 Pod labels 匹配
  - 重新安装或升级 ingress controller
  - 检查 Service 类型和端口配置
  - 检查 cloud provider 的 load balancer 设置

**4. 节点网络问题：**

- **症状：**
  - 节点与集群断开连接
  - 节点间通信失败
  - kubelet 连接错误

- **诊断方法：**
  - 查看节点状态：
    ```bash
    kubectl describe node <node_name>
    ```
  - 检查节点网络接口和路由：
    ```bash
    # Directly on the node
    ip addr
    ip route
    ```
  - 检查防火墙规则：
    ```bash
    # Directly on the node
    iptables -L
    ```
  - 查看 kubelet 日志：
    ```bash
    journalctl -u kubelet
    ```

- **解决方法：**
  - 重新配置节点网络接口
  - 调整防火墙规则
  - 重启 kubelet
  - 必要时重启节点

**5. NetworkPolicy 问题：**

- **症状：**
  - 意外的连接阻断
  - 特定 Namespace 之间无法通信
  - 只有部分 Pod 可以访问

- **诊断方法：**
  - 查看 NetworkPolicy：
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - 检查 Pod labels：
    ```bash
    kubectl get pods --show-labels
    ```
  - 确认网络插件支持 NetworkPolicy

- **解决方法：**
  - 调整或删除 NetworkPolicy
  - 修改 Pod labels
  - 使用 NetworkPolicy 调试工具

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

- **常用命令：**
  ```bash
  # Inside the pod
  ping <IP>
  traceroute <IP>
  dig <service_name>.<namespace>.svc.cluster.local
  curl -v <URL>
  tcpdump -i any
  netstat -tuln
  ```

- **CNI 插件专用调试工具：**
  - Calico：`calicoctl`
  - Cilium：`cilium`
  - Weave：`weave`

**7. 最佳实践：**

- 记录网络拓扑
- 定期执行连通性测试
- 修改 NetworkPolicy 前评估影响
- 规划集群网络 CIDR 范围
- 部署网络监控工具
</details>

## 实践题

1. 编写一个满足以下要求的 ResourceQuota manifest：
   - 命名空间：development
   - Pod 数量上限：20
   - CPU requests 总量上限：4 cores
   - 内存 requests 总量上限：8Gi
   - PVC 数量上限：10
   - 存储 requests 总量上限：100Gi

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

2. 请为自管 Linux 集群编写 kubelet 检查脚本。假设每个节点都配置了 SSH 别名，并提供一个需显式启用的修复模式。

<details>
<summary>显示答案</summary>

**答案：**

```bash
#!/usr/bin/env bash
# check_kubelet.sh: self-managed Linux nodes with configured SSH aliases only.
set -euo pipefail
repair=${REPAIR_KUBELET:-0}
status=0
nodes=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
for node in $nodes; do
  printf '%s: ' "$node"
  if state=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n systemctl is-active kubelet'); then
    printf 'kubelet %s\n' "$state"
    continue
  else
    rc=$?
  fi
  if [ "$rc" -ne 3 ]; then
    printf 'SSH/sudo/service query failed (exit %s); no repair attempted\n' "$rc" >&2
    status=1
    continue
  fi
  printf 'kubelet %s\n' "$state"
  if [ "$repair" != 1 ]; then
    printf 'Inspect logs and approve a repair before rerunning with REPAIR_KUBELET=1\n'
    status=1
    continue
  fi
  if ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n systemctl start kubelet && sudo -n systemctl is-active --quiet kubelet' \
      && kubectl wait --for=condition=Ready "node/$node" --timeout=120s; then
    printf '%s: kubelet active and node Ready\n' "$node"
  else
    status=1
    ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n journalctl -u kubelet --no-pager -n 50' || true
  fi
done
exit "$status"
```

此脚本使用 `kubectl get nodes` 获取节点列表，并逐一检查 kubelet。只有在显式设置 `REPAIR_KUBELET=1` 且服务查询成功确认 kubelet 未运行时，才会尝试启动；之后会重新检查服务并确认 Node 恢复 Ready。若启动失败则检查日志。SSH、sudo 或服务查询错误会与“服务未运行”区分处理，避免误触发修复。

**用法：**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
# After diagnosing the inactive service and approving repair:
REPAIR_KUBELET=1 ./check_kubelet.sh
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
#!/usr/bin/env bash
# backup_etcd.sh: self-managed etcd; external storage must already be mounted.
set -euo pipefail
umask 077
BACKUP_DIR=${BACKUP_DIR:-/opt/etcd-backup}
REMOTE_ROOT=${REMOTE_ROOT:-/mnt/remote-storage}
REMOTE_DIR="$REMOTE_ROOT/etcd-backups"
METRICS_DIR=${METRICS_DIR:-/var/lib/node_exporter/textfile_collector}
RETENTION_DAYS=${RETENTION_DAYS:-7}
ETCD_ENDPOINT=${ETCD_ENDPOINT:-https://127.0.0.1:2379}
ETCD_CACERT=${ETCD_CACERT:-/etc/kubernetes/pki/etcd/ca.crt}
ETCD_CERT=${ETCD_CERT:-/etc/kubernetes/pki/etcd/healthcheck-client.crt}
ETCD_KEY=${ETCD_KEY:-/etc/kubernetes/pki/etcd/healthcheck-client.key}

publish_status() {
  rc=$?
  trap - EXIT
  if [ -d "$METRICS_DIR" ]; then
    tmp=$(mktemp "$METRICS_DIR/.etcd-backup.XXXXXX")
    success=0
    [ "$rc" -eq 0 ] && success=1
    printf 'etcd_backup_success %s\netcd_backup_last_attempt_timestamp_seconds %s\n' \
      "$success" "$(date +%s)" > "$tmp"
    chmod 0644 "$tmp"
    mv "$tmp" "$METRICS_DIR/etcd_backup_status.prom"
  fi
  exit "$rc"
}
trap publish_status EXIT
case "$RETENTION_DAYS" in ''|*[!0-9]*) echo 'Invalid retention' >&2; exit 1;; esac
mountpoint -q "$REMOTE_ROOT" || { echo 'Remote storage is not mounted' >&2; exit 1; }
mkdir -p "$BACKUP_DIR" "$REMOTE_DIR"
exec 9>"$BACKUP_DIR/.backup.lock"
flock -n 9 || { echo 'Another backup is running' >&2; exit 1; }
name="etcd-snapshot-$(date -u +%Y%m%d-%H%M%S).db"
ETCDCTL_API=3 etcdctl snapshot save "$BACKUP_DIR/$name" \
  --endpoints="$ETCD_ENDPOINT" --cacert="$ETCD_CACERT" \
  --cert="$ETCD_CERT" --key="$ETCD_KEY"
etcdutl snapshot status "$BACKUP_DIR/$name" --write-out=table
gzip "$BACKUP_DIR/$name"
cp "$BACKUP_DIR/$name.gz" "$REMOTE_DIR/.$name.gz.partial"
cmp "$BACKUP_DIR/$name.gz" "$REMOTE_DIR/.$name.gz.partial"
mv "$REMOTE_DIR/.$name.gz.partial" "$REMOTE_DIR/$name.gz"
# Retention runs only after snapshot validation and verified external copy.
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'etcd-snapshot-*.db.gz' \
  -mtime "+$RETENTION_DAYS" -delete
find "$REMOTE_DIR" -maxdepth 1 -type f -name 'etcd-snapshot-*.db.gz' \
  -mtime "+$RETENTION_DAYS" -delete
printf 'Verified backup copied to %s\n' "$REMOTE_DIR/$name.gz"
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
    create 0600 root root
}
```

**5. 测试备份：**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. 设置备份监控（可选）：**

若 `METRICS_DIR` 存在，脚本的 EXIT trap 会发布数值型 `etcd_backup_success` 和 `etcd_backup_last_attempt_timestamp_seconds` 指标。配置 node-exporter 的 textfile collector 读取该目录，并授予写入者所需权限；针对失败或尝试时间过旧发出告警。不要在 echo/copy 命令之后再追加 `$?` 检查。外部挂载必须已存在；验证或复制失败会停止保留策略。

**注意事项：**
- 备份文件应存储在集群外部的安全位置。
- 在云环境中，建议使用 S3 或 GCS 等 object storage。
- 定期执行备份恢复测试，以验证备份有效性。
- 对于 HA etcd 集群，只需在一个 etcd 实例上执行备份。
</details>
4. 编写一个有边界的维护流程，仅针对明确选定的自管 Linux 工作节点，同时保留中断预算；若健康检查失败则停止。

<details>
<summary>显示答案</summary>

**答案：**

**Node Rolling Update 流程：**

```bash
#!/usr/bin/env bash
# node_rolling_update.sh: explicitly selected self-managed Linux workers only.
set -euo pipefail
: "${MAINTENANCE_COMMAND:?Set a reviewed node-maintenance command that does not reboot itself}"
: "${WORKLOAD_HEALTHCHECK:?Set a command that verifies critical workload health}"
[ "$#" -gt 0 ] || { echo 'Pass the worker node names as arguments' >&2; exit 1; }
trap 'echo "Stopped on error; inspect the node before manually uncordoning it" >&2' ERR
for node in "$@"; do
  kubectl get node "$node" -o json | jq -e '
    (.metadata.labels["kubernetes.io/os"] == "linux") and
    (.metadata.labels | has("node-role.kubernetes.io/control-plane") | not) and
    (.metadata.labels | has("node-role.kubernetes.io/master") | not)' >/dev/null
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" 'sudo -n true'
done
kubectl get poddisruptionbudgets -A
bash -c "$WORKLOAD_HEALTHCHECK"
for node in "$@"; do
  kubectl wait --for=condition=Ready "node/$node" --timeout=120s
  boot_before=$(kubectl get node "$node" -o jsonpath='{.status.nodeInfo.bootID}')
  kubectl cordon "$node"
  kubectl drain "$node" --ignore-daemonsets --timeout=10m
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" "$MAINTENANCE_COMMAND"
  reboot_required=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
    'if [ -f /var/run/reboot-required ]; then echo yes; else echo no; fi')
  if [ "$reboot_required" = yes ]; then
    ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" 'sudo -n reboot' || true
    deadline=$((SECONDS + 600))
    while :; do
      boot_after=$(kubectl get node "$node" -o jsonpath='{.status.nodeInfo.bootID}')
      [ -n "$boot_after" ] && [ "$boot_after" != "$boot_before" ] && break
      [ "$SECONDS" -lt "$deadline" ] || { echo 'New boot ID not reported' >&2; exit 1; }
      sleep 5
    done
  fi
  # Require a fresh kubelet lease renewal, not a stale pre-maintenance Ready flag.
  lease_before=$(kubectl -n kube-node-lease get lease "$node" -o jsonpath='{.spec.renewTime}')
  deadline=$((SECONDS + 120))
  while :; do
    lease_after=$(kubectl -n kube-node-lease get lease "$node" -o jsonpath='{.spec.renewTime}')
    [ -n "$lease_after" ] && [ "$lease_after" != "$lease_before" ] && break
    [ "$SECONDS" -lt "$deadline" ] || { echo 'No fresh kubelet lease' >&2; exit 1; }
    sleep 5
  done
  kubectl wait --for=condition=Ready "node/$node" --timeout=5m
  bash -c "$WORKLOAD_HEALTHCHECK"
  kubectl uncordon "$node"
  bash -c "$WORKLOAD_HEALTHCHECK"
done
```

此示例需要 kubectl、jq、已为所选 Node 配置 SSH alias、无需密码且经过授权的 sudo，以及经过审核的维护命令。它会检查 Debian/Ubuntu 的“需要重启”标记；其他操作系统需据此调整。请将 WORKLOAD_HEALTHCHECK 设为实际验证关键应用的命令，并且只传入经过审核的 worker 列表。例如：

```bash
MAINTENANCE_COMMAND='sudo -n /usr/local/sbin/approved-node-maintenance' \
WORKLOAD_HEALTHCHECK='kubectl -n app rollout status deployment/frontend --timeout=5m' \
./node_rolling_update.sh worker-1 worker-2
```

命令/脚本和应用名称必须真实存在并符合维护计划。流程不会使用 force，也不会授权丢弃 emptyDir 数据。若 drain/维护失败，流程会停止；重启后它会等待 boot ID 变化和新的 kubelet lease，并让失败的 Node 保持 cordon。PDB 和这些检查可减少计划内中断，但无法保证避免无关故障导致的不可用。EKS managed/Auto Mode Node 应使用 provider-managed 更新；control-plane Node 则应遵循独立的 kubeadm 控制平面流程。

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

```python
#!/usr/bin/env python3
# resource_usage_report.py: read-only Kubernetes API/metrics reporting.
import datetime
from decimal import Decimal
import html
import json
import os
from pathlib import Path
import re
import subprocess

SCALE = {"": Decimal(1), "n": Decimal("1e-9"), "u": Decimal("1e-6"),
         "m": Decimal("1e-3"), "k": Decimal(1000), "K": Decimal(1000)}
SCALE.update({s: Decimal(1000) ** n for n, s in enumerate("MGTPE", 2)})
SCALE.update({s + "i": Decimal(1024) ** n for n, s in enumerate("KMGTPE", 1)})

def quantity(value):
    text = str(value)
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)", text)
    if not match or match[2] not in SCALE:
        raise ValueError("Unsupported Kubernetes quantity: " + text)
    return Decimal(match[1]) * SCALE[match[2]]

def kubectl_json(*args):
    return json.loads(subprocess.check_output(["kubectl", *args], text=True))

def make_rows(pods, metrics):
    index = {(p["metadata"]["namespace"], p["metadata"]["name"]): p for p in pods}
    rows = []
    for metric in metrics:
        key = metric["metadata"]["namespace"], metric["metadata"]["name"]
        if key not in index:
            continue  # API snapshots are not atomic; the Pod may have disappeared.
        spec = index[key]["spec"]
        active = spec.get("containers", []) + [c for c in spec.get("initContainers", [])
                                               if c.get("restartPolicy") == "Always"]
        usage = {r: sum((quantity(c["usage"][r]) for c in metric["containers"]), Decimal(0))
                 for r in ("cpu", "memory")}
        requests = {}
        for resource in ("cpu", "memory"):
            pod_request = spec.get("resources", {}).get("requests", {}).get(resource)
            values = [c.get("resources", {}).get("requests", {}).get(resource) for c in active]
            requests[resource] = (quantity(pod_request) if pod_request is not None else
                                  sum((quantity(v) for v in values), Decimal(0))
                                  if all(v is not None for v in values) else None)
        rows.append((key, usage, requests))
    return rows

def render_report(rows):
    lines = ["Kubernetes resource usage report", "Generated: " + datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "Requests: active application/native-sidecar containers or Pod-level requests.",
             "This is not scheduler effective-request accounting for completed init stages/overhead."]
    totals = {}
    for key, usage, _ in rows:
        total = totals.setdefault(key[0], {"cpu": Decimal(0), "memory": Decimal(0)})
        for resource in total:
            total[resource] += usage[resource]
    for resource in ("cpu", "memory"):
        lines.append("\nTop 10 Pods by " + resource)
        for key, usage, requests in sorted(rows, key=lambda row: row[1][resource], reverse=True)[:10]:
            request = requests[resource]
            ratio = f"{usage[resource] / request * 100:.1f}%" if request else "request missing/zero"
            lines.append(f"{key[0]}/{key[1]}: usage={usage[resource]}, request={request}, ratio={ratio}")
    lines.append("\nNamespace totals (CPU cores, memory GiB)")
    for namespace, total in sorted(totals.items()):
        lines.append(f"{namespace}: {total['cpu']:.3f}, {total['memory'] / (1024 ** 3):.3f}")
    lines.append("\nPods above 80% of known requests or with missing requests")
    for key, usage, requests in rows:
        if any(not requests[r] or usage[r] / requests[r] >= Decimal('0.8') for r in requests):
            lines.append(f"{key[0]}/{key[1]}: usage={usage}; requests={requests}")
    return "\n".join(lines)

def main():
    os.umask(0o077)
    group = kubectl_json("get", "--raw", "/apis/metrics.k8s.io")
    version = group["preferredVersion"]["version"]
    pod_metrics = kubectl_json("get", "--raw", f"/apis/metrics.k8s.io/{version}/pods")["items"]
    pods = kubectl_json("get", "pods", "-A", "-o", "json")["items"]
    rows = make_rows(pods, pod_metrics)
    report = render_report(rows)
    nodes = subprocess.check_output(["kubectl", "top", "nodes"], text=True)
    report += "\n\nNode resource usage\n" + nodes
    node_count = len(kubectl_json("get", "nodes", "-o", "json")["items"])
    namespace_count = len(kubectl_json("get", "namespaces", "-o", "json")["items"])
    context = subprocess.check_output(["kubectl", "config", "current-context"], text=True).strip()
    report += f"\nContext: {context}; nodes: {node_count}; namespaces: {namespace_count}\n"
    report += f"Inventory Pods: {len(pods)}; Pods with matched metrics: {len(rows)}\n"
    directory = Path(os.environ.get("REPORT_DIR", "/tmp/k8s-reports"))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    stem = "resource-usage-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    text_path = directory / (stem + ".txt")
    text_path.write_text(report, encoding="utf-8")
    (directory / (stem + ".html")).write_text(
        '<!doctype html><meta charset="utf-8"><title>Kubernetes resource report</title><pre>'
        + html.escape(report) + '</pre>', encoding="utf-8")
    print(text_path)

if __name__ == "__main__":
    main()
```

**脚本用法：**
```bash
python3 resource_usage_report.py
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
- 此脚本需要 Python 3，以及对 Pods 和 metrics API 的只读 `kubectl` 访问。它会发现已提供的 metrics API 版本，按 Namespace 汇总多容器用量，处理资源单位并对 HTML 输出进行转义。
- 集群中必须安装 Metrics Server。
- 在大型集群中，脚本执行时间可能较长。
- 可以设置为 cron job 以定期生成报告。
- 报告可以通过电子邮件发送，或与监控系统集成。
</details>

## 高级主题

1. 哪两组选项包含真实的 etcd 设置或运维实践？（选择两项。）
   - A) `--max-request-bytes`、`--quota-backend-bytes`，以及定期 compaction
   - B) `--max-concurrent-requests`、`--max-connections`，以及磁盘 RAID 配置
   - C) `--auto-compaction-retention`、`--snapshot-count`，以及 SSD 存储
   - D) `--max-txn-ops`、`--max-result-buffer`，以及扩展内存

<details>
<summary>显示答案</summary>

**答案：A 和 C**

**解释：**
etcd 的配置选项必须和运维实践一起评估。A 和 C 包含真实设置或有效做法；请在实际版本上核对参数默认值，并通过测量验证调整效果。

1. **`--auto-compaction-retention`**：etcd 是仅追加存储，会保留变更历史；此参数设置自动压缩旧 key 版本的保留期。默认值为 0（禁用），生产环境通常设为 1 小时（1h）或 24 小时（24h），以节省磁盘空间并改善性能。

2. **`--snapshot-count`**：指定 etcd 在创建内部 Raft snapshot 前提交的事务数；这不是可移植的备份 snapshot。默认值随版本变化（v3.6 参考文档列出 10,000），调优前应检查安装版本并测量影响。

3. **SSD 存储**：etcd 对磁盘 I/O 敏感，使用 SSD 通常可显著改善性能；大型集群应使用 SSD，并结合实际负载测量。

其他重要优化设置和最佳实践：

- **使用专用磁盘**：为 etcd 数据使用专用磁盘，以防止与其他应用程序发生 I/O 争用。
- **适当的内存分配**：etcd 会在内存中缓存数据以提升性能，因此必须分配足够的内存。
- **优化集群规模**：通常 3-5 个 etcd member 可提供最佳性能和可用性。
- **平衡网络延迟和故障隔离**：降低成员间延迟的同时，避免所有成员集中在同一故障域；若整个 AZ 故障，同区部署可能失去 quorum。
- **定期备份和压缩**：执行定期备份和 compaction，以确保数据安全并高效使用磁盘空间。

`--max-request-bytes`、`--quota-backend-bytes` 和 `--max-txn-ops` 都是真实设置。选项 D 中的 `--max-result-buffer` 不受支持；也不要把资源限制、保留期和内部 snapshot 当作备份策略。
</details>

2. 在 Kubernetes 集群中实现 control plane 高可用性（HA）的有效方式是什么？
   - A) 在单个 master Node 上运行多个 API server 实例
   - B) 配置包含多个 master Node 和负载均衡器的 etcd 集群
   - C) 将 API server 部署为带 PersistentVolume 的 StatefulSet
   - D) 在 master Node 上实现可自动恢复的 watchdog 进程

<details>
<summary>显示答案</summary>

**答案：B：配置包含多个 master Node 和负载均衡器的 etcd 集群**

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

3. 哪种机制决定 Kubernetes audit logging 要记录哪些事件及其详细级别？
   - A) 不加筛选地记录所有请求和响应正文
   - B) 使用 audit policy 选择要记录的事件和详细级别
   - C) 将 audit log 实时流式传输到外部 SIEM 系统
   - D) 仅允许管理员访问 audit log

<details>
<summary>显示答案</summary>

**答案：B：使用 audit policy 选择要记录的事件和详细级别**

**解释：**
Audit policy 用于选择事件和详细级别。可用 Metadata catch-all 保留较广泛的审计轨迹，同时排除敏感正文；保留期限、访问控制和日志传送也同样重要。

1. **降低性能影响**：按审计需求和实测开销选择记录级别；对所有请求记录 Metadata 是受支持的基线。

2. **存储效率**：记录所有事件会导致日志数据快速增长，增加存储成本，并使日志分析变得困难。

3. **关注相关信息**：通过仅记录重要事件，安全分析人员可以关注关键信息。

4. **合规性**：根据适用要求确定事件覆盖范围、保留期限和访问控制。

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
- level: Metadata
  resources:
  - group: ""
    resources: ["secrets", "configmaps", "serviceaccounts/token"]
  - group: authentication.k8s.io
    resources: ["tokenreviews"]
- level: Metadata
```

其他选项的问题：
- 记录所有 API 请求可能导致性能和存储问题。
- 实时流式传输到外部 SIEM system 很重要，但优先级低于决定记录什么。
- 限制 audit log 访问权限很重要，但这是安全措施，而不是 logging policy 本身。
</details>

4. 在自管环境中，哪种模式将专用节点问题检测器与自定义修复逻辑结合起来？
   - A) 部署 DaemonSet 监控节点状态，并自动重启有问题的节点
   - B) 使用云提供商的托管节点组和自动修复功能
   - C) 使用 Node Problem Detector 和自定义 controller 监控节点状态并执行恢复
   - D) 使用 cron job 定期检查节点状态并重建有问题的节点

<details>
<summary>显示答案</summary>

**答案：C：使用 Node Problem Detector 和自定义 controller 监控节点状态并执行恢复**

**解释：**
Node Problem Detector 与 custom controller 是一种可扩展的设计，但并非在所有环境中都最优。受支持的 provider-managed 修复（包括 EKS node repair）也可能减少运维工作。该设计的组成部分如下：

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

4. **匹配环境**：检测和修复逻辑必须适配操作系统、运行时和 provider；如果节点上的 agent 无法上报节点丢失，还需要外部信号或 controller。

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


</details>

5. 在 Kubernetes 集群中有效管理 RBAC（Role-Based Access Control）的最佳实践是什么？
   - A) 为便于管理而向所有用户授予 cluster-admin role
   - B) 按 Namespace 定义细粒度 role 并遵循最小权限原则
   - C) 为保持一致而将所有权限合并到单个 ClusterRole
   - D) 始终使用用户证书而不是 service account 进行身份验证

<details>
<summary>显示答案</summary>

**答案：B：按 Namespace 定义细粒度 role 并遵循最小权限原则**

**解释：**
在 Kubernetes 集群中有效管理 RBAC（Role-Based Access Control）的最佳实践，是按 Namespace 定义细粒度 role，并应用最小权限原则。此方法提供以下优势：

1. **最小权限原则**：仅向用户和 service account 授予最低限度的必要权限，以最小化安全风险。这有助于保护集群免受意外变更或恶意操作影响。

2. **Namespace 隔离**：按 Namespace 定义 role 可加强团队或应用程序之间的逻辑隔离，但 Namespace 边界可以限制普通 API 操作；还需搭配 workload admission 和网络控制。

Pod/Deployment 创建操作可能会间接暴露该 Namespace 中的 Secret 和 ServiceAccount 权限。移除直接读取 Secret 的权限虽有帮助，但并不能单独限制工作负载可挂载哪些凭证；还应使用适当的 admission control。

3. **细粒度访问控制**：可以针对特定资源类型或操作精细控制权限。例如，可以授予开发人员管理 Pod 和 Service 的权限，同时限制修改 Secret 或 Namespace 本身的权限。

4. **便于审计**：使用细粒度 role 可以清晰记录谁可以执行哪些操作，使审计和合规更容易。

RBAC 最佳实践实施示例：
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
   ```

1. **按 Namespace 定义 role**：

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

- **将所有权限合并到单个 ClusterRole 中**：一个权限过宽的共享 role 有过度授权风险；不过，范围狭窄、可复用的 ClusterRole 配合 namespaced RoleBinding 也可以是合适做法。

- **始终使用用户证书**：Service account 适合应用程序身份验证，而在所有情况下都使用用户证书会增加管理负担。根据具体情况选择适当的身份验证机制很重要。
</details>
