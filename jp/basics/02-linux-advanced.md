# Linux 運用スキル

> **対応バージョン**: 保守対象の Linux ディストリビューション上の Bash。各コマンドは、記載されたツールがインストール済みであることを前提とします。 **最終更新日**: 2026年10月16日

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

<span id="1-environment-variables-and-shell-configuration"></span>

## 1. 環境変数と Shell 設定

環境変数は、Linux と Kubernetes で設定を管理するための中核的な仕組みです。

### 1.1 環境変数の基礎

```bash
env
echo "$HOME"
echo "$PATH"
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

対話型の非ログイン Bash は `.bashrc` を読み込みます。ログイン Bash は `.bash_profile`、`.bash_login`、`.profile` のうち最初に見つかったファイルを読み込みます。ログインプロファイルから `.bashrc` を明示的に読み込むこともできます。以下のブロックは一度だけ追加してください。

```bash
cat >> ~/.bashrc << 'SCRIPT'
export KUBECONFIG=~/.kube/config
command -v kubectl >/dev/null && source <(kubectl completion bash)
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

<span id="2-shell-scripting-basics"></span>

## 2. Shell スクリプティングの基礎

### 2.1 変数

```bash
#!/bin/bash
NAME="kubernetes"
NAMESPACE=${1:-default}
: "${REQUIRED_VAR:?REQUIRED_VAR must be set}"
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

# Running phase does not imply readiness. A bounded wait propagates API errors/timeouts.
kubectl wait --for=condition=Ready pod/mypod --timeout=120s
```

### 2.4 関数

```bash
check_pod_exists() {
    local pod_name=${1:?Pod name required}
    local namespace=${2:-default}
    # Nonzero also includes authorization/connection errors; inspect stderr.
    kubectl get pod "$pod_name" -n "$namespace" -o name >/dev/null
}
```

### 2.5 Init Container パターン

この上限付きループの例は DNS の検出を待機します。DNS の成功はデータベースの準備完了を意味しないため、アプリケーション側に接続再試行またはデータベース固有の準備状態チェックが必要です。事前に `mysql` Service とカスタム `myapp` イメージを用意してください。失敗した init container は kubelet により再起動されるため、Pod 全体の起動期限とは異なります。

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

## 3. テキスト処理ツール

### 3.1 kubectl での grep

```bash
kubectl get pods --field-selector=status.phase!=Running
kubectl logs nginx-pod | grep -i error
```

### 3.2 awk によるフィールド抽出

```bash
kubectl get pods | awk 'NR>1 {print $1}'
kubectl get pods --no-headers | awk '$3 != "Running" {print $1, $3}'
```

### 3.3 sed 編集

```bash
# Text-only preview; this can match more than the intended YAML field.
sed 's/replicas: [0-9]*/replicas: 5/' deployment.yaml
# For a structured edit, use the yq example below.
```

### 3.4 jq による JSON 解析

```bash
kubectl get pod nginx -o json | jq '.metadata.name'
kubectl get pods -o json | jq -r '.items[].metadata.name'
```

### 3.5 yq による YAML 解析

以下の例は Mike Farah yq v4 を使用します。Python 版 yq ではオプションが異なります。

```bash
yq '.metadata.name' deployment.yaml
yq -i '.spec.replicas = 5' deployment.yaml
```

***

<span id="4-ssh-and-remote-access"></span>

## 4. SSH とリモートアクセス

### 4.1 SSH キー生成

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 4.2 SSH トンネリング

API トンネルでは、元の CA と TLS サーバー名を kubeconfig に保持してください。`127.0.0.1` に接続する場合は、`tls-server-name` に API 証明書の実際の名前を設定し、TLS 検証を有効なままにします。

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8080:localhost:80 user@server
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:6443:kubernetes-api:6443 user@bastion
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

<span id="5-performance-monitoring-and-troubleshooting"></span>

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

Metrics Server などの `metrics.k8s.io` プロバイダーが必要です。`kubectl top` は過去のデータを保存する監視ストアではありません。

```bash
kubectl top nodes
kubectl top pods --sort-by=memory
```

***

<span id="6-storage-management-basics"></span>

## 6. ストレージ管理の基礎

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

以下のパスとホスト名は、既存のファイルシステムがマウントされているノードに一致させる必要があります。

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

ノード障害後、ローカルストレージを別のノードへ移動することはできません。この StorageClass はディスクをプロビジョニングしないため、利用する Pod がスケジュールされるまで PVC が `Pending` のままになる場合があります。PV の容量は実際のファイルシステムに合わせてください。表示される容量はディレクトリのクォータではありません。`Retain` の後のクリーンアップや再利用は、別途オペレーターが行う作業です。

***

<span id="7-curl-and-api-calls"></span>

## 7. curl と API 呼び出し

### 7.1 HTTP メソッド

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"John"}' https://api.example.com/users
```

### 7.2 Kubernetes API 呼び出し

ServiceAccount には、その namespace 内の Pod を一覧表示する RBAC 権限が必要です。`automountServiceAccountToken: false` の場合、以下のファイルが存在しないことがあります。投影トークンはローテーションされるため、長時間稼働するクライアントはファイルを読み直してください。トークンをログに記録してはいけません。

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

### 7.3 便利な curl オプション

```bash
curl --silent --show-error -o /dev/null -w "%{http_code}\n" https://api.example.com/health
```

***

<span id="8-practical-one-liners-collection"></span>

## 8. 実用的なワンライナー集

### 8.1 Kubernetes 操作

```bash
kubectl get pods -A | awk '$4 != "Running" && NR>1 {print $1, $2, $4}'
kubectl get pods -A -o json | jq -r '.items[] | select(any((.status.containerStatuses // [])[]; .restartCount > 5)) | [.metadata.namespace, .metadata.name] | @tsv'
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

[前へ: Linux の基礎](01-linux-basics.md) | [次へ: コンテナの基礎](03-container-technology.md)

## 検証用リファレンス

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
