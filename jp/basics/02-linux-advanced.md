# Linux 運用スキル

> **対応バージョン**: すべての主要な Linux ディストリビューション **最終更新**: February 11, 2026

このドキュメントでは、Kubernetes 環境で効果的に作業するために不可欠な Linux 運用スキルについて説明します。

***

## 目次

1. [環境変数と Shell 設定](02-linux-advanced.md#1-environment-variables-and-shell-configuration)
2. [Shell スクリプティングの基礎](02-linux-advanced.md#2-shell-scripting-basics)
3. [テキスト処理ツール](02-linux-advanced.md#3-text-processing-tools)
4. [SSH とリモートアクセス](02-linux-advanced.md#4-ssh-and-remote-access)
5. [パフォーマンス監視とトラブルシューティング](02-linux-advanced.md#5-performance-monitoring-and-troubleshooting)
6. [ストレージ管理の基礎](02-linux-advanced.md#6-storage-management-basics)
7. [curl と API 呼び出し](02-linux-advanced.md#7-curl-and-api-calls)
8. [実用的なワンライナー集](02-linux-advanced.md#8-practical-one-liners-collection)

***

## 1. 環境変数と Shell 設定

環境変数は、Linux と Kubernetes で設定を管理するための中核的な仕組みです。

### 1.1 環境変数の基礎

```bash
env
echo $HOME
echo $PATH
printenv HOME
```

### 1.2 export コマンド

```bash
export MY_VAR="hello"
export DATABASE_URL="postgresql://localhost:5432/mydb"
export KUBECONFIG="/home/user/.kube/config"
```

### 1.3 source コマンド

```bash
cat > ~/my-env.sh << 'SCRIPT'
export APP_ENV="production"
export APP_PORT="8080"
alias k='kubectl'
SCRIPT

source ~/my-env.sh
```

### 1.4 .bashrc と .bash\_profile

```bash
cat >> ~/.bashrc << 'SCRIPT'
export KUBECONFIG=~/.kube/config
source <(kubectl completion bash)
alias k='kubectl'
SCRIPT

source ~/.bashrc
```

### 1.5 Kubernetes ConfigMap 連携

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

## 2. Shell スクリプティングの基礎

### 2.1 変数

```bash
#!/bin/bash
NAME="kubernetes"
NAMESPACE=${1:-default}
: ${REQUIRED_VAR:?"REQUIRED_VAR must be set"}
```

### 2.2 条件分岐

```bash
if [ "$ENV" = "production" ]; then
    echo "Production mode"
fi

case "$1" in
    start) echo "Starting..." ;;
    stop) echo "Stopping..." ;;
esac
```

### 2.3 ループ

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

### 2.4 関数

```bash
check_pod_exists() {
    local pod_name=$1
    kubectl get pod "$pod_name" &>/dev/null
}
```

### 2.5 Init Container パターン

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

## 3. テキスト処理ツール

### 3.1 kubectl での grep

```bash
kubectl get pods | grep -v "Running"
kubectl logs nginx-pod | grep -i error
```

### 3.2 awk によるフィールド抽出

```bash
kubectl get pods | awk 'NR>1 {print $1}'
kubectl get pods | awk '$3 != "Running" {print $1, $3}'
```

### 3.3 sed 編集

```bash
sed -i 's/replicas: [0-9]*/replicas: 5/' deployment.yaml
```

### 3.4 jq による JSON 解析

```bash
kubectl get pod nginx -o json | jq '.metadata.name'
kubectl get pods -o json | jq -r '.items[].metadata.name'
```

### 3.5 yq による YAML 解析

```bash
yq '.metadata.name' deployment.yaml
yq -i '.spec.replicas = 5' deployment.yaml
```

***

## 4. SSH とリモートアクセス

### 4.1 SSH キー生成

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 4.2 SSH トンネリング

```bash
ssh -L 8080:localhost:80 user@server
ssh -L 6443:kubernetes-api:6443 user@bastion
```

### 4.3 Bastion Host の使用

```bash
ssh -J bastion user@internal-server
```

### 4.4 rsync

```bash
rsync -avzP ./local/ user@remote:/path/
```

***

## 5. パフォーマンス監視とトラブルシューティング

### 5.1 top と htop

```bash
top -b -n 1 | head -20
```

### 5.2 vmstat と iostat

```bash
vmstat 1 5
iostat -dx 1 5
```

### 5.3 free と df

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

## 6. ストレージ管理の基礎

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

## 7. curl と API 呼び出し

### 7.1 HTTP メソッド

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"John"}' https://api.example.com/users
```

### 7.2 Kubernetes API 呼び出し

```bash
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl -s --cacert $CACERT -H "Authorization: Bearer $TOKEN" \
  "https://kubernetes.default.svc/api/v1/namespaces/default/pods"
```

### 7.3 便利な curl オプション

```bash
curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health
```

***

## 8. 実用的なワンライナー集

### 8.1 Kubernetes 操作

```bash
kubectl get pods -A | awk '$4 != "Running" && NR>1 {print $1, $2, $4}'
kubectl get pods -A -o json | jq -r '.items[] | select(.status.containerStatuses[]?.restartCount > 5) | .metadata.name'
```

### 8.2 ログ分析

```bash
kubectl logs deploy/app --since=1h | grep -i error
```

### 8.3 ネットワークデバッグ

```bash
nslookup kubernetes.default.svc.cluster.local
nc -zv service-name 80
```

***

## まとめ

1. **環境変数**: K8s ConfigMap/Secret の基盤
2. **Shell スクリプティング**: init containers やヘルスチェックに不可欠
3. **テキスト処理**: kubectl 出力解析の中核
4. **SSH**: node デバッグに重要
5. **パフォーマンス監視**: トラブルシューティングの基盤

***

[前へ: Linux の基礎](01-linux-basics.md) | [次へ: Container の基礎](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/basics/03-container-basics.md)
