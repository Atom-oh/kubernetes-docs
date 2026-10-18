# Linux 运维技能

> **支持的版本**：受维护的 Linux 发行版上的 Bash；命令假定已安装所列工具 **最后更新**：October 16, 2026

本文介绍在 Kubernetes 环境中高效工作所需的 Linux 核心运维技能。

***

## 目录

1. [环境变量和 Shell 配置](02-linux-advanced.md#1-environment-variables-and-shell-configuration)
2. [Shell 脚本基础](02-linux-advanced.md#2-shell-scripting-basics)
3. [文本处理工具](02-linux-advanced.md#3-text-processing-tools)
4. [SSH 和远程访问](02-linux-advanced.md#4-ssh-and-remote-access)
5. [性能监控和故障排查](02-linux-advanced.md#5-performance-monitoring-and-troubleshooting)
6. [存储管理基础](02-linux-advanced.md#6-storage-management-basics)
7. [curl 和 API 调用](02-linux-advanced.md#7-curl-and-api-calls)
8. [实用单行命令集](02-linux-advanced.md#8-practical-one-liners-collection)

***

<span id="1-environment-variables-and-shell-configuration"></span>

## 1. 环境变量和 Shell 配置

环境变量是 Linux 和 Kubernetes 中管理配置的核心机制。

### 1.1 环境变量基础

```bash
env
echo "$HOME"
echo "$PATH"
printenv HOME
```

### 1.2 export 命令

```bash
export MY_VAR="hello"
export DATABASE_URL="postgresql://localhost:5432/mydb"
export KUBECONFIG="/home/user/.kube/config"
```

### 1.3 source 命令

```bash
cat > ~/my-env.sh << 'SCRIPT'
export APP_ENV="production"
export APP_PORT="8080"
alias k='kubectl'
SCRIPT

source ~/my-env.sh
```

### 1.4 .bashrc 和 .bash\_profile

交互式非登录 Bash 会读取 .bashrc；登录 Bash 会读取第一个可用的 .bash_profile/.bash_login/.profile。登录配置文件可以显式加载 .bashrc。以下代码块只需添加一次。

```bash
cat >> ~/.bashrc << 'SCRIPT'
export KUBECONFIG=~/.kube/config
command -v kubectl >/dev/null && source <(kubectl completion bash)
alias k='kubectl'
SCRIPT

source ~/.bashrc
```

### 1.5 Kubernetes ConfigMap 关联

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DATABASE_HOST: "mysql.default.svc.cluster.local"
  DATABASE_PORT: "3306"
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    envFrom:
    - configMapRef:
        name: app-config
```

***

<span id="2-shell-scripting-basics"></span>

## 2. Shell 脚本基础

### 2.1 变量

```bash
#!/bin/bash
NAME="kubernetes"
NAMESPACE=${1:-default}
: "${REQUIRED_VAR:?REQUIRED_VAR must be set}"
```

### 2.2 条件语句

```bash
if [ "$ENV" = "production" ]; then
    echo "Production mode"
fi

case "$1" in
    start) echo "Starting..." ;;
    stop) echo "Stopping..." ;;
esac
```

### 2.3 循环

```bash
for ns in default kube-system monitoring; do
    kubectl get pods -n "$ns"
done

# Running phase does not imply readiness. A bounded wait propagates API errors/timeouts.
kubectl wait --for=condition=Ready pod/mypod --timeout=120s
```

### 2.4 函数

```bash
check_pod_exists() {
    local pod_name=${1:?Pod name required}
    local namespace=${2:-default}
    # Nonzero also includes authorization/connection errors; inspect stderr.
    kubectl get pod "$pod_name" -n "$namespace" -o name >/dev/null
}
```

### 2.5 Init Container 模式

此有界循环示例会等待 DNS 发现。DNS 查询成功并不代表数据库已就绪；应用需要实现连接重试，或执行特定于数据库的就绪检查。请准备 mysql Service 和自定义 myapp 镜像。Kubelet 可以重启失败的 init container，因此这与 Pod 启动的总时限不同。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: wait-for-db-dns
    image: busybox:1.38.0
    command:
    - sh
    - -c
    - |
      for attempt in $(seq 1 60); do
        nslookup mysql.default.svc.cluster.local >/dev/null 2>&1 && exit 0
        sleep 2
      done
      echo "Database Service DNS did not become available" >&2
      exit 1
  containers:
  - name: app
    image: myapp:1.0
```

***

<span id="3-text-processing-tools"></span>

## 3. 文本处理工具

### 3.1 与 kubectl 搭配使用 grep

```bash
kubectl get pods --field-selector=status.phase!=Running
kubectl logs nginx-pod | grep -i error
```

### 3.2 使用 awk 提取字段

```bash
kubectl get pods | awk 'NR>1 {print $1}'
kubectl get pods --no-headers | awk '$3 != "Running" {print $1, $3}'
```

### 3.3 使用 sed 编辑

```bash
# Text-only preview; this can match more than the intended YAML field.
sed 's/replicas: [0-9]*/replicas: 5/' deployment.yaml
# For a structured edit, use the yq example below.
```

### 3.4 使用 jq 解析 JSON

```bash
kubectl get pod nginx -o json | jq '.metadata.name'
kubectl get pods -o json | jq -r '.items[].metadata.name'
```

### 3.5 使用 yq 解析 YAML

以下示例使用 Mike Farah yq v4；Python yq 的选项有所不同。

```bash
yq '.metadata.name' deployment.yaml
yq -i '.spec.replicas = 5' deployment.yaml
```

***

<span id="4-ssh-and-remote-access"></span>

## 4. SSH 和远程访问

### 4.1 生成 SSH 密钥

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 4.2 SSH 隧道

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8080:localhost:80 user@server
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:6443:kubernetes-api:6443 user@bastion
```

对于 API 隧道，请在 kubeconfig 中保留原始 CA 和 TLS 服务器名称。连接到 127.0.0.1 时，请将 tls-server-name 设置为实际的 API 证书名称；保持启用 TLS 验证。

### 4.3 使用 Bastion 主机

```bash
ssh -J bastion user@internal-server
```

### 4.4 rsync

```bash
rsync -avzP ./local/ user@remote:/path/
```

***

<span id="5-performance-monitoring-and-troubleshooting"></span>

## 5. 性能监控和故障排查

### 5.1 top 和 htop

```bash
top -b -n 1 | head -20
```

### 5.2 vmstat 和 iostat

```bash
vmstat 1 5
iostat -dx 1 5
```

### 5.3 free 和 df

```bash
free -h
df -h
```

### 5.4 kubectl top

需要 Metrics Server 等 metrics.k8s.io 提供程序；kubectl top 不会存储历史监控数据。

```bash
kubectl top nodes
kubectl top pods --sort-by=memory
```

***

<span id="6-storage-management-basics"></span>

## 6. 存储管理基础

### 6.1 lsblk

```bash
lsblk -f
```

### 6.2 LVM

```bash
# Use only an explicitly selected empty training disk. These commands write storage metadata.
: "${LAB_DISK:?Set an unused lab block device after checking lsblk and backups}"
lsblk -f "$LAB_DISK"
sudo wipefs --no-act "$LAB_DISK"
# Stop if the disk contains data, mounted filesystems, or existing volume metadata.
sudo pvcreate "$LAB_DISK"
sudo vgcreate data_vg "$LAB_DISK"
sudo lvcreate -l 100%FREE -n data_lv data_vg
```

### 6.3 Kubernetes PV/PVC

以下路径和主机名必须与现有文件系统挂载所在的节点相匹配。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv
spec:
  capacity:
    storage: 100Gi
  accessModes: [ReadWriteOnce]
  storageClassName: local-storage
  persistentVolumeReclaimPolicy: Retain
  local:
    path: /mnt/disks/vol1
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values: [replace-with-actual-node-hostname]
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: local-pvc
spec:
  storageClassName: local-storage
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
```

***

节点发生故障后，本地存储无法迁移到其他节点。此 StorageClass 不会创建磁盘；在某个使用它的 Pod 被调度之前，PVC 可能一直处于 Pending 状态。PV 容量应与实际文件系统相符：声明的容量值并不代表目录配额。保留策略下的清理和复用需要由操作人员另行处理。

<span id="7-curl-and-api-calls"></span>

## 7. curl 和 API 调用

### 7.1 HTTP 方法

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"John"}' https://api.example.com/users
```

### 7.2 Kubernetes API 调用

```bash
# Run inside a Pod with projected ServiceAccount credentials and curl installed.
set -e
SERVICEACCOUNT=/var/run/secrets/kubernetes.io/serviceaccount
CACERT="$SERVICEACCOUNT/ca.crt"
NAMESPACE=$(cat "$SERVICEACCOUNT/namespace")
TOKEN=$(cat "$SERVICEACCOUNT/token")
curl --fail --silent --show-error --cacert "$CACERT" \
  -H "Authorization: Bearer $TOKEN" \
  "https://kubernetes.default.svc/api/v1/namespaces/$NAMESPACE/pods"
unset TOKEN
```

此 ServiceAccount 需要在该命名空间中拥有列出 pods 的 RBAC 权限。设置 automountServiceAccountToken: false 时，这些文件可能不存在。投射的令牌会轮换，因此长期运行的客户端必须重新读取文件；不要记录令牌。

### 7.3 实用 curl 选项

```bash
curl --silent --show-error -o /dev/null -w "%{http_code}\n" https://api.example.com/health
```

***

<span id="8-practical-one-liners-collection"></span>

## 8. 实用单行命令集

### 8.1 Kubernetes 运维

```bash
kubectl get pods -A | awk '$4 != "Running" && NR>1 {print $1, $2, $4}'
kubectl get pods -A -o json | jq -r '.items[] | select(any((.status.containerStatuses // [])[]; .restartCount > 5)) | [.metadata.namespace, .metadata.name] | @tsv'
```

### 8.2 日志分析

```bash
kubectl logs deploy/app --since=1h | grep -i error
```

### 8.3 网络调试

```bash
nslookup kubernetes.default.svc.cluster.local
nc -zv service-name 80
```

***

## 总结

1. **环境变量**：K8s ConfigMap/Secret 的基础
2. **Shell 脚本**：init container 和健康检查必不可少的工具
3. **文本处理**：解析 kubectl 输出的核心工具
4. **SSH**：节点调试的重要工具
5. **性能监控**：故障排查的基础

***

[上一页：Linux 基础](01-linux-basics.md) | [下一页：容器基础](03-container-technology.md)

## 验证参考资料

- https://kubernetes.io/docs/concepts/storage/volumes/#local
- https://kubernetes.io/docs/concepts/storage/storage-classes/#local
- https://kubernetes.io/docs/tasks/run-application/access-api-from-pod/
- https://kubernetes.io/docs/concepts/configuration/configmap/
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_wait/
- https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html
- https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html
- https://download.samba.org/pub/rsync/rsync.1
- https://github.com/mikefarah/yq
- https://busybox.net/downloads/BusyBox.html
- https://github.com/docker-library/official-images/blob/master/library/busybox
