# Linux 操作技能

> **支持的版本**：所有主流 Linux 发行版 **最后更新**：February 11, 2026

本文档涵盖在 Kubernetes 环境中高效工作所需的基本 Linux 操作技能。

***

## 目录

1. [环境变量与 Shell 配置](02-linux-advanced.md#1-environment-variables-and-shell-configuration)
2. [Shell 脚本基础](02-linux-advanced.md#2-shell-scripting-basics)
3. [文本处理工具](02-linux-advanced.md#3-text-processing-tools)
4. [SSH 和远程访问](02-linux-advanced.md#4-ssh-and-remote-access)
5. [性能监控和故障排查](02-linux-advanced.md#5-performance-monitoring-and-troubleshooting)
6. [存储管理基础](02-linux-advanced.md#6-storage-management-basics)
7. [curl 和 API 调用](02-linux-advanced.md#7-curl-and-api-calls)
8. [实用单行命令集合](02-linux-advanced.md#8-practical-one-liners-collection)

***

## 1. 环境变量与 Shell 配置

环境变量是在 Linux 和 Kubernetes 中管理配置的核心机制。

### 1.1 环境变量基础

```bash
env
echo $HOME
echo $PATH
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

```bash
cat >> ~/.bashrc << 'SCRIPT'
export KUBECONFIG=~/.kube/config
source <(kubectl completion bash)
alias k='kubectl'
SCRIPT

source ~/.bashrc
```

### 1.5 Kubernetes ConfigMap 连接

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

## 2. Shell 脚本基础

### 2.1 变量

```bash
#!/bin/bash
NAME="kubernetes"
NAMESPACE=${1:-default}
: ${REQUIRED_VAR:?"REQUIRED_VAR must be set"}
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

while true; do
    STATUS=$(kubectl get pod mypod -o jsonpath='{.status.phase}')
    [ "$STATUS" = "Running" ] && break
    sleep 5
done
```

### 2.4 函数

```bash
check_pod_exists() {
    local pod_name=$1
    kubectl get pod "$pod_name" &>/dev/null
}
```

### 2.5 Init Container 模式

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: wait-for-db
    image: busybox:1.35
    command: ['sh', '-c', 'until nc -z mysql 3306; do sleep 2; done']
  containers:
  - name: app
    image: myapp:1.0
```

***

## 3. 文本处理工具

### 3.1 grep 与 kubectl

```bash
kubectl get pods | grep -v "Running"
kubectl logs nginx-pod | grep -i error
```

### 3.2 awk 字段提取

```bash
kubectl get pods | awk 'NR>1 {print $1}'
kubectl get pods | awk '$3 != "Running" {print $1, $3}'
```

### 3.3 sed 编辑

```bash
sed -i 's/replicas: [0-9]*/replicas: 5/' deployment.yaml
```

### 3.4 使用 jq 解析 JSON

```bash
kubectl get pod nginx -o json | jq '.metadata.name'
kubectl get pods -o json | jq -r '.items[].metadata.name'
```

### 3.5 使用 yq 解析 YAML

```bash
yq '.metadata.name' deployment.yaml
yq -i '.spec.replicas = 5' deployment.yaml
```

***

## 4. SSH 和远程访问

### 4.1 SSH 密钥生成

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 4.2 SSH 隧道

```bash
ssh -L 8080:localhost:80 user@server
ssh -L 6443:kubernetes-api:6443 user@bastion
```

### 4.3 Bastion Host 使用

```bash
ssh -J bastion user@internal-server
```

### 4.4 rsync

```bash
rsync -avzP ./local/ user@remote:/path/
```

***

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

```bash
kubectl top nodes
kubectl top pods --sort-by=memory
```

***

## 6. 存储管理基础

### 6.1 lsblk

```bash
lsblk -f
```

### 6.2 LVM

```bash
sudo pvcreate /dev/nvme1n1
sudo vgcreate data_vg /dev/nvme1n1
sudo lvcreate -l 100%FREE -n data_lv data_vg
```

### 6.3 Kubernetes PV/PVC

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv
spec:
  capacity:
    storage: 100Gi
  accessModes: [ReadWriteOnce]
  storageClassName: local-storage
  local:
    path: /mnt/disks/vol1
```

***

## 7. curl 和 API 调用

### 7.1 HTTP 方法

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"John"}' https://api.example.com/users
```

### 7.2 Kubernetes API 调用

```bash
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl -s --cacert $CACERT -H "Authorization: Bearer $TOKEN" \
  "https://kubernetes.default.svc/api/v1/namespaces/default/pods"
```

### 7.3 实用 curl 选项

```bash
curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health
```

***

## 8. 实用单行命令集合

### 8.1 Kubernetes 操作

```bash
kubectl get pods -A | awk '$4 != "Running" && NR>1 {print $1, $2, $4}'
kubectl get pods -A -o json | jq -r '.items[] | select(.status.containerStatuses[]?.restartCount > 5) | .metadata.name'
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

## 结论

1. **环境变量**：K8s ConfigMap/Secret 的基础
2. **Shell 脚本**：对 init containers、健康检查至关重要
3. **文本处理**：kubectl 输出解析的核心
4. **SSH**：对节点调试很重要
5. **性能监控**：故障排查的基础

***

[上一页：Linux 基础](01-linux-basics.md) | [下一页：Container 基础](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/basics/03-container-basics.md)
