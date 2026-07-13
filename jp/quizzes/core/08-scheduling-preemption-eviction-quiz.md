## Short Answer Questions

1. Kubernetes cluster における etcd database のバックアップと復元の手順を説明してください。

<details>
<summary>解答を表示</summary>

**解答:**

**etcd バックアップ手順:**

1. **etcdctl tool のインストールを確認する:**
   ```bash
   etcdctl version
   ```

2. **バックアップコマンドを実行する:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

3. **バックアップファイルを確認する:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot status snapshot.db --write-out=table
   ```

4. **バックアップファイルを安全な場所に保存する:**
   - 外部 cluster storage
   - Cloud storage (S3, GCS など)
   - 異なる物理的な場所

**etcd 復元手順:**

1. **復元のためにすべての API server を停止する:**
   ```bash
   sudo systemctl stop kube-apiserver
   ```

2. **etcd service を停止する:**
   ```bash
   sudo systemctl stop etcd
   ```

3. **data directory をバックアップする（任意）:**
   ```bash
   sudo mv /var/lib/etcd /var/lib/etcd.bak
   ```

4. **snapshot から新しい data directory を作成する:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
     --data-dir=/var/lib/etcd-restore \
     --name=master \
     --initial-cluster=master=https://127.0.0.1:2380 \
     --initial-cluster-token=etcd-cluster-1 \
     --initial-advertise-peer-urls=https://127.0.0.1:2380
   ```

5. **復元した data directory を使用するように etcd を設定する:**
   ```bash
   sudo mv /var/lib/etcd-restore /var/lib/etcd
   sudo chown -R etcd:etcd /var/lib/etcd
   ```

6. **etcd service を再起動する:**
   ```bash
   sudo systemctl start etcd
   ```

7. **etcd status を確認する:**
   ```bash
   ETCDCTL_API=3 etcdctl endpoint health \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

8. **API server を再起動する:**
   ```bash
   sudo systemctl start kube-apiserver
   ```

9. **cluster status を確認する:**
   ```bash
   kubectl get nodes
   kubectl get pods --all-namespaces
   ```

**ベストプラクティス:**
- 定期的なバックアップスケジュールを設定する（例: 毎日）
- バックアップ前に etcd cluster status を確認する
- バックアップファイルの整合性を確認する
- 復元手順を定期的にテストする
- バックアップファイルに timestamp を含める
- 複数のバックアップバージョンを保持する
- バックアップと復元の手順を文書化する
</details>

2. Kubernetes cluster における node メンテナンスの手順と、`cordon`、`drain`、`uncordon` コマンドの違いを説明してください。

<details>
<summary>解答を表示</summary>

**解答:**

**Node メンテナンス手順:**

1. **node status を確認する:**
   ```bash
   kubectl get nodes
   kubectl describe node <node_name>
   ```

2. **node を cordon する:**
   ```bash
   kubectl cordon <node_name>
   ```

3. **node を drain する:**
   ```bash
   kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
   ```

4. **メンテナンスを実施する:**
   - Software updates
   - Kernel upgrades
   - Hardware replacement
   - Configuration changes

5. **作業完了後に node を uncordon する:**
   ```bash
   kubectl uncordon <node_name>
   ```

6. **node status を確認する:**
   ```bash
   kubectl get nodes
   ```

**コマンドの違い:**

1. **`kubectl cordon <node_name>`:**
   - node をスケジュール不可としてマークします。
   - 新しい pods はその node にスケジュールされません。
   - すでに実行中の pods は実行を継続します。
   - node status に `SchedulingDisabled` インジケーターが表示されます。

2. **`kubectl drain <node_name>`:**
   - node をスケジュール不可としてマークします（cordon を含む）。
   - node 上で実行中の pods を安全に evict します。
   - Pods は他の nodes に再スケジュールされます。
   - DaemonSet pods はデフォルトで無視されます（`--ignore-daemonsets` flag が必要）。
   - emptyDir volumes を使用している pods はデータを失う可能性があり、特別な対応が必要です（`--delete-emptydir-data` flag）。
   - PodDisruptionBudgets を尊重します。

3. **`kubectl uncordon <node_name>`:**
   - node を再びスケジュール可能としてマークします。
   - 新しい pods をその node にスケジュールできます。
   - 以前 evict された pods は自動的には戻りません。

**メンテナンス時の考慮事項:**
- cluster に十分な容量があることを確認する
- 重要な workloads には PodDisruptionBudgets を設定する
- 一度にメンテナンスする node は 1 つだけにする
- メンテナンス期間中は autoscaling 設定を調整する
- メンテナンス前後に workload status を確認する
- rolling update strategy を使用する
</details>

3. Kubernetes cluster で resource usage を監視および管理する方法を説明してください。含めるべき tools と techniques を列挙してください。

<details>
<summary>解答を表示</summary>

**解答:**

**Kubernetes resource 監視および管理方法:**

**1. 基本的な監視 tools:**

- **Metrics Server:**
  - 基本的な CPU と memory usage metrics を提供します
  - `kubectl top` コマンドをサポートします
  - インストール:
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    ```
  - 使用方法:
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Kubernetes Dashboard:**
  - cluster status と resource usage の視覚的な表示
  - pods、nodes、namespaces などを管理するための interface を提供します

**2. 高度な監視 stack:**

- **Prometheus + Grafana:**
  - Prometheus: Metric の収集と保存
  - Grafana: Metric の可視化と dashboards
  - kube-prometheus-stack または Prometheus Operator でインストールできます
  - custom alerting rules と dashboards をサポートします

- **ELK/EFK Stack:**
  - Elasticsearch: Log の保存と検索
  - Logstash/Fluentd: Log の収集と処理
  - Kibana: Log の可視化と分析

**3. Resource 管理 techniques:**

- **Resource Requests と Limits の設定:**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **Namespace レベルの Resource Quotas (ResourceQuota):**
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

- **Default Resource Limits (LimitRange):**
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

- **Horizontal Pod Autoscaler (HPA):**
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

- **Vertical Pod Autoscaler (VPA):**
  - pod の CPU と memory requests を自動的に調整します
  - resource usage patterns に基づいて推奨値を提供します

- **Cluster Autoscaler:**
  - workload requirements に基づいて cluster node 数を自動的に調整します
  - resource 不足時には nodes を追加し、利用率が低い時には nodes を削除します

**4. 監視のベストプラクティス:**

- すべての pods に resource requests と limits を設定する
- 重要な metrics に対して alerts を設定する
- 過去の usage analysis に基づいて resources を計画する
- 定期的な resource audits を実施する
- cost optimization のために resource usage trends を分析する
- development、staging、production 環境に適切な resource quotas を設定する
- node レベルと pod レベルの両方の metrics を監視する
</details>

4. Kubernetes cluster upgrades 中に発生し得る主なリスクと、それらを軽減する戦略を説明してください。

<details>
<summary>解答を表示</summary>

**解答:**

**Kubernetes Cluster Upgrade のリスクと軽減戦略:**

**1. 主なリスク:**

- **API 互換性の問題:**
  - 新しい version で APIs が変更または削除される可能性があります
  - 一部の Custom Resource Definitions (CRDs) や API versions がサポートされなくなる可能性があります

- **Workload 中断:**
  - control plane component の再起動により API server が一時的に利用できなくなる
  - node upgrades 中の pod 再スケジュールにより Service が中断する

- **Feature 変更:**
  - default behavior の変更が既存の workloads に影響する可能性があります
  - security policy の変更により permission issues が発生する可能性があります

- **Performance 問題:**
  - 新しい versions で resource requirements が増加する可能性があります
  - 初期安定化期間中に performance degradation が発生する可能性があります

- **Rollback の複雑さ:**
  - 一部の upgrades は簡単に rollback できません
  - data format 変更により rollback に制限が生じます

**2. 軽減戦略:**

- **徹底した計画と準備:**
  - **changelog の確認:** 新しい version の変更点、deprecated features、known issues を確認する
  - **upgrade path の確認:** 現在の version から target version への直接 upgrade がサポートされていることを確認する
  - **resource requirements の確認:** 新しい version の最小要件を確認する

- **まず Test Environment でテストする:**
  - production に似た test cluster で upgrade を実施する
  - すべての重要な workloads と custom resources をテストする
  - automated test suites を実行する

- **API 互換性の確認:**
  - 使用中の API versions を確認する:
    ```bash
    kubectl api-resources -o wide
    ```
  - deprecated API usage を確認する:
    ```bash
    kubectl get -A | grep "deprecated"
    ```
  - 必要に応じて manifests を更新する

- **バックアップとリカバリ計画:**
  - etcd database をバックアップする:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db
    ```
  - すべての重要な manifests をバックアップする:
    ```bash
    kubectl get all --all-namespaces -o yaml > all-resources.yaml
    ```
  - recovery procedures を文書化してテストする

- **段階的な Upgrade アプローチ:**
  - **control plane components を先に upgrade する:**
    - high availability 構成では、control plane node を一度に 1 つずつ upgrade する
  - **worker nodes の rolling upgrade:**
    - node groups を小さな batches に分けて upgrade する
    - 各 batch 後に安定性を確認する

- **Workload 保護:**
  - **PodDisruptionBudget を設定する:**
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
  - **nodes の drain 時には注意する:**
    ```bash
    kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
    ```

- **監視の強化:**
  - upgrade 前、実行中、後に cluster status を監視する
  - 重要な metrics と logs を綿密に観察する
  - alert thresholds を一時的に調整する

- **Rollback 計画:**
  - rollback trigger conditions を定義する
  - rollback procedures を文書化する
  - rollback に必要なすべての components と images を保持する

- **Communication 計画:**
  - すべての stakeholders に upgrade schedule と想定影響を通知する
  - upgrade 中に status updates を提供する
  - 問題発生時の escalation paths を定義する

**3. Version 固有の考慮事項:**

- **Minor version upgrades (例: 1.24 → 1.25):**
  - 削除された APIs と feature changes に特に注意する
  - 一度に 1 minor version ずつ upgrade する

- **Patch version upgrades (例: 1.24.0 → 1.24.1):**
  - 一般的にはより安全ですが、それでも testing が必要です
  - security patches についてはより迅速な deployment を検討する
</details>

5. Kubernetes cluster で発生し得る一般的な networking issues と、それらを診断・解決する方法を説明してください。

<details>
<summary>解答を表示</summary>

**解答:**

**Kubernetes Networking Issue の診断と解決:**

**1. Pod 間通信の問題:**

- **症状:**
  - Pods が他の pods と通信できない
  - service name で接続できない
  - Network timeout errors

- **診断方法:**
  - network policies を確認する:
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - connectivity をテストするために test pod を作成する:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    ping <target_pod_IP>
    wget -O- <service_name>:<port>
    ```
  - CNI plugin pod status を確認する:
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **解決方法:**
  - CNI plugin を再インストールまたは更新する
  - network policies を変更または削除する
  - node network interfaces を確認する
  - firewall rules を確認する

**2. Service Discovery と DNS の問題:**

- **症状:**
  - service name で接続できない
  - DNS lookup failures
  - 断続的な接続問題

- **診断方法:**
  - CoreDNS pod status を確認する:
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - DNS lookup をテストする:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    nslookup kubernetes.default.svc.cluster.local
    nslookup <service_name>.<namespace>.svc.cluster.local
    cat /etc/resolv.conf
    ```
  - service endpoints を確認する:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **解決方法:**
  - CoreDNS pods を再起動する:
    ```bash
    kubectl rollout restart deployment coredns -n kube-system
    ```
  - DNS configuration を確認・変更する:
    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
  - kubelet DNS settings を確認する

**3. Service と Ingress の問題:**

- **症状:**
  - service に外部からアクセスできない
  - Ingress rules が機能しない
  - Load balancer が作成されない

- **診断方法:**
  - service status を確認する:
    ```bash
    kubectl describe service <service_name>
    ```
  - ingress status を確認する:
    ```bash
    kubectl describe ingress <ingress_name>
    ```
  - ingress controller pod logs を確認する:
    ```bash
    kubectl logs -n <ingress_namespace> <ingress_controller_pod>
    ```
  - endpoints を確認する:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **解決方法:**
  - service selector が pod labels と一致することを確認する
  - ingress controller を再インストールまたは更新する
  - service type と port configuration を確認する
  - cloud provider load balancer settings を確認する

**4. Node Networking の問題:**

- **症状:**
  - Node が cluster から切断されている
  - nodes 間の通信が失敗する
  - kubelet connection errors

- **診断方法:**
  - node status を確認する:
    ```bash
    kubectl describe node <node_name>
    ```
  - node network interfaces を確認する:
    ```bash
    # Run directly on node
    ip addr
    ip route
    ```
  - firewall rules を確認する:
    ```bash
    # Run directly on node
    iptables -L
    ```
  - kubelet logs を確認する:
    ```bash
    journalctl -u kubelet
    ```

- **解決方法:**
  - node network interfaces を再設定する
  - firewall rules を変更する
  - kubelet を再起動する
  - 必要に応じて node を再起動する

**5. Network Policy の問題:**

- **症状:**
  - 予期しない接続ブロック
  - 特定の namespaces 間で通信できない
  - 一部の pods のみアクセス可能

- **診断方法:**
  - network policies を確認する:
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - pod labels を確認する:
    ```bash
    kubectl get pods --show-labels
    ```
  - network plugin が network policies をサポートしていることを確認する

- **解決方法:**
  - network policies を変更または削除する
  - pod labels を変更する
  - network policy debugging tools を使用する

**6. 一般的な Networking Debugging Tools:**

- **Network debugging pod:**
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

- **便利なコマンド:**
  ```bash
  # Inside the pod
  ping <IP>
  traceroute <IP>
  dig <service_name>.<namespace>.svc.cluster.local
  curl -v <URL>
  tcpdump -i any
  netstat -tuln
  ```

- **CNI plugin 固有の debugging tools:**
  - Calico: `calicoctl`
  - Cilium: `cilium`
  - Weave: `weave`

**7. ベストプラクティス:**

- network topology を文書化する
- 定期的な connectivity tests を実施する
- network policy 変更前に影響を分析する
- cluster network CIDR ranges を計画する
- network monitoring tools を実装する
</details>
## Hands-on Questions

1. 次の要件を満たす ResourceQuota manifest を作成してください:
   - Namespace: development
   - Maximum pods: 20
   - Maximum CPU requests: 4 cores
   - Maximum memory requests: 8Gi
   - Maximum PVCs: 10
   - Maximum storage requests: 100Gi

<details>
<summary>解答を表示</summary>

**解答:**

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

この ResourceQuota は 'development' namespace に次の limits を設定します:
- 最大 20 pods
- 合計 CPU requests は 4 cores
- 合計 memory requests は 8Gi
- 最大 10 PersistentVolumeClaims
- 合計 storage requests は 100Gi

ResourceQuota を適用するには:
```bash
kubectl apply -f resource-quota.yaml
```

現在の quota usage を確認するには:
```bash
kubectl describe quota dev-quota -n development
```

注: ResourceQuota を適用する前に namespace が存在している必要があります。namespace が存在しない場合は、先に作成してください:
```bash
kubectl create namespace development
```
</details>

2. cluster 内のすべての nodes で kubelet service status を確認し、問題があれば解決する script を作成してください。

<details>
<summary>解答を表示</summary>

**解答:**

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

この script は次の tasks を実行します:
1. `kubectl get nodes` を使用して cluster 内のすべての nodes の list を取得します。
2. 各 node について:
   - node の Ready status を確認します。
   - SSH 経由で node に接続して kubelet service status を確認します。
   - kubelet が実行されていない場合は service を開始します。
   - service 開始後に status を再度確認します。
   - 開始に失敗した場合は logs を確認します。
   - kubelet configuration file の主要な settings を確認します。

**使用方法:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
```

**注:**
- この script を実行するには、すべての nodes への SSH access が必要です。
- production environments では SSH key-based authentication の使用が推奨されます。
- cloud environments では、nodes への直接 SSH access が制限されている場合があり、cloud provider の node management tools を使用する必要があります。
</details>

3. cluster の etcd database をバックアップし、バックアップファイルを安全な場所に保存する cron job を設定してください。

<details>
<summary>解答を表示</summary>

**解答:**

**1. バックアップ Script を作成する:**

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

**2. Script に実行権限を付与する:**

```bash
chmod +x /opt/etcd-backup/backup_etcd.sh
```

**3. Cron Job を設定する:**

```bash
# Edit root user's crontab
sudo crontab -e
```

次の内容を追加します:

```
# Run etcd backup at 2 AM daily
0 2 * * * /opt/etcd-backup/backup_etcd.sh >> /var/log/etcd-backup.log 2>&1
```

**4. Backup Log Rotation を設定する:**

`/etc/logrotate.d/etcd-backup` file を作成します:

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

**5. バックアップをテストする:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. Backup Monitoring を設定する（任意）:**

バックアップ失敗時に alerts を受け取るには、monitoring tools（例: Prometheus）と統合できます。backup script に次の code を追加します:

```bash
# Create file indicating backup success
if [ $? -eq 0 ]; then
  echo "success" > /var/lib/node_exporter/etcd_backup_status.prom
else
  echo "failure" > /var/lib/node_exporter/etcd_backup_status.prom
fi
```

**注:**
- バックアップファイルは cluster 外の安全な場所に保存する必要があります。
- cloud environments では、S3、GCS のような object storage の使用が推奨されます。
- バックアップの有効性を確認するため、定期的に backup restoration をテストしてください。
- high-availability etcd clusters では、バックアップは 1 つの etcd instance のみで実行すれば十分です。
</details>
4. cluster 内のすべての nodes に対して rolling updates を実行する手順を作成してください。updates 中も workload availability を維持する必要があります。

<details>
<summary>解答を表示</summary>

**解答:**

**Node Rolling Update 手順:**

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

**Rolling Update 前の準備:**

1. **PodDisruptionBudget を設定する:**
   重要な workloads には可用性を確保するために PDBs を設定します。

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

2. **十分な Resources を確保する:**
   1 つの node が取り除かれたときに、残りの nodes がすべての workloads を処理できることを確認します。

3. **バックアップを実施する:**
   upgrade 前に etcd database backup を実施します。

**Rolling Update のベストプラクティス:**

1. **段階的なアプローチ:**
   - 一度に 1 つの node のみ更新する
   - 各 node update 後に cluster status を確認する

2. **Automation と Idempotency:**
   - scripts を使用して process を自動化する
   - failure 時に安全に retry できるよう設計する

3. **監視の強化:**
   - update 中に cluster metrics を監視する
   - application status と performance を監視する

4. **Rollback 計画:**
   - 問題発生時に備えて rollback procedure を準備する
   - previous state を復元する方法を確保する

5. **Communication:**
   - update schedule と想定影響を周知する
   - update progress を定期的に報告する

**注:**
- cloud environments では、managed Kubernetes services (EKS, GKE, AKS など) の node update features を利用できます。
- 複数の node groups がある場合は、group ごとに updates を実施します。
- 重要な system pods (CoreDNS, kube-proxy など) の status を特に監視してください。
</details>

5. cluster 内で resource usage の高い pods を特定し、その情報を含む report を生成する script を作成してください。

<details>
<summary>解答を表示</summary>

**解答:**

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

**Script の使用方法:**
```bash
chmod +x resource_usage_report.sh
./resource_usage_report.sh
```

**Script の機能:**
1. cluster information を収集する
2. node resource usage を収集する
3. CPU と memory usage が上位の pods を特定する
4. namespace ごとの resource usage を計算する
5. requests に対して usage が高い pods を特定する
6. resource requests がない pods を特定する
7. text と HTML formats で reports を生成する

**注:**
- この script を実行するには `kubectl`、`jq`、`bc` tools が必要です。
- Metrics Server が cluster にインストールされている必要があります。
- 大規模 clusters では script execution time が長くなる場合があります。
- 定期的な report generation のために cron job として設定できます。
- reports は email で送信したり monitoring systems と統合したりできます。
</details>
## Advanced Topics

1. Kubernetes cluster で etcd performance を最適化するための主要な configuration parameters と best practices は何ですか？
   - A) `--max-request-bytes`, `--quota-backend-bytes`, regular compaction
   - B) `--max-concurrent-requests`, `--max-connections`, disk RAID configuration
   - C) `--auto-compaction-retention`, `--snapshot-count`, SSD storage usage
   - D) `--max-txn-ops`, `--max-result-buffer`, memory expansion

<details>
<summary>解答を表示</summary>

**解答: C) `--auto-compaction-retention`, `--snapshot-count`, SSD storage usage**

**解説:**
etcd は Kubernetes cluster の中核となる data store であり、その performance は cluster 全体の performance に直接影響します。etcd performance を最適化するための主要な configuration parameters と best practices は次のとおりです:

1. **`--auto-compaction-retention`**: etcd はすべての変更履歴を保持する append-only store です。この parameter は、key の過去 versions を自動的に compact する期間を設定します。default は 0（無効）ですが、production environments では通常 1 時間（1h）または 24 時間（24h）に設定されます。これにより disk space を節約し、performance が向上します。

2. **`--snapshot-count`**: etcd が snapshot を作成する前に commit する transactions の数を指定します。default は 100,000 ですが、大規模 clusters では snapshot creation frequency を最適化するためにこの値を調整できます。小さい値は snapshots がより頻繁になることを意味し、recovery time は短縮されますが disk I/O が増加します。

3. **SSD storage usage**: etcd は disk I/O に敏感なため、SSDs (Solid State Drives) を使用すると performance が大幅に向上します。特に大規模 clusters では SSD usage が不可欠です。

その他の重要な optimization settings と best practices:

- **専用 disk を使用する**: 他の applications との I/O contention を防ぐため、etcd data には専用 disk を使用します。
- **適切な memory allocation**: etcd は performance のために data を memory に cache するため、十分な memory を割り当てる必要があります。
- **Cluster size optimization**: 一般的に 3〜5 個の etcd members が最適な performance と availability を提供します。
- **network latency を最小化する**: members 間の network latency を最小化するため、etcd members を同じ data center または availability zone に配置します。
- **定期的な backup と compaction**: data safety と効率的な disk space usage を確保するため、定期的な backups と compaction を実施します。

`--max-request-bytes` と `--quota-backend-bytes` は実際の etcd parameters ですが、主に performance ではなく resource limits に関連しています。`--max-concurrent-requests`、`--max-connections`、`--max-txn-ops`、`--max-result-buffer` は実際の etcd parameters ではないか、performance optimization の主要因ではありません。
</details>

2. Kubernetes cluster で control plane high availability (HA) を実装する最も効果的な方法は何ですか？
   - A) Running multiple API server instances on a single master node
   - B) Configuring an etcd cluster with multiple master nodes and load balancer
   - C) Deploying API server as StatefulSet and using PersistentVolume
   - D) Implementing a watch process with automatic recovery on master node

<details>
<summary>解答を表示</summary>

**解答: B) Configuring an etcd cluster with multiple master nodes and load balancer**

**解説:**
Kubernetes control plane high availability (HA) を実装する最も効果的な方法は、複数の master nodes と load balancer を備えた etcd cluster を構成することです。このアプローチは次の components で構成されます:

1. **複数の master nodes**: single points of failure をなくすため、通常は 3 または 5 個の master nodes を異なる availability zones にまたがって deploy します。各 master node は次の control plane components を実行します:
   - kube-apiserver: API requests を処理する server
   - kube-controller-manager: controller processes を実行します
   - kube-scheduler: pod scheduling decisions を行います

2. **etcd cluster**: etcd はすべての cluster data を保存する distributed key-value store です。high availability のため、通常は 3 または 5 個の etcd instances を実行します。etcd は master nodes 上で直接実行することも、別の専用 nodes 上で実行することもできます。

3. **Load balancer**: client requests を複数の kube-apiserver instances に分散するために load balancer が必要です。これは通常、cloud provider load balancer services または HAProxy、Nginx などの software load balancers を使用して実装されます。

この構成の主な利点:
- **Fault tolerance**: 1 つの master node が失敗しても、cluster は稼働を継続します。
- **High availability**: 複数の availability zones にまたがって deploy することで、data center レベルの障害に対応できます。
- **Scalability**: API server requests を複数の instances に分散して処理できます。
- **Data consistency**: etcd の Raft consensus algorithm により data consistency が保証されます。

他の選択肢の問題点:
- single master node 上で複数の API server instances を実行すると、その node 自体が single point of failure になります。
- API server を StatefulSet として deploy するのは一般的なアプローチではありません。control plane components は通常 Kubernetes の外部で管理されます。
- watch process は役立つ場合がありますが、それ単体では真の high availability solution ではありません。
</details>

3. Kubernetes cluster で Audit Logging を設定する際に最も重要な考慮事項は何ですか？
   - A) Log all API requests for complete audit trail
   - B) Use audit policy to selectively log only important events
   - C) Send audit logs to external SIEM system in real-time
   - D) Restrict access to audit logs to administrators only

<details>
<summary>解答を表示</summary>

**解答: B) Use audit policy to selectively log only important events**

**解説:**
Kubernetes Audit Logging を設定する際に最も重要な考慮事項は、audit policies を使用して重要な events のみを選択的に log することです。これは次の理由で重要です:

1. **performance impact を最小化する**: すべての API requests を logging すると、API server に大きな load がかかり performance が低下する可能性があります。特に大規模 clusters では、毎秒数千の API requests が発生することがあります。

2. **Storage efficiency**: すべての events を logging すると log data volume が急速に増加し、storage costs が増え、log analysis が困難になります。

3. **関連情報に集中する**: 重要な events のみを logging することで、security analysts は critical information に集中できます。

4. **Compliance**: 多くの compliance requirements では、すべての events ではなく特定の types of events の logging が求められます。

Kubernetes audit policies は次の audit levels をサポートします:

- **None**: event を log しません。
- **Metadata**: request metadata（user、timestamp、resource、action など）のみを log し、request/response bodies は除外します。
- **Request**: metadata と request body を log しますが、response body は除外します。
- **RequestResponse**: metadata、request body、response body を log します。

効果的な audit policy の例:
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

他の選択肢の問題点:
- すべての API requests を logging すると、performance と storage の問題が発生する可能性があります。
- external SIEM systems への real-time transmission は重要ですが、何を log するかを決定することより優先度は低いです。
- audit logs への access を制限することは重要ですが、logging policy そのものではなく security measure です。
</details>

4. Kubernetes cluster で Node Auto-Repair を実装する最も効果的な方法は何ですか？
   - A) Deploy DaemonSet that monitors node status and automatically reboots problematic nodes
   - B) Utilize cloud provider's managed node groups and auto-repair features
   - C) Use Node Problem Detector and custom controller for node status monitoring and repair
   - D) Implement cron job that periodically checks node status and recreates problematic nodes

<details>
<summary>解答を表示</summary>

**解答: C) Use Node Problem Detector and custom controller for node status monitoring and repair**

**解説:**
Kubernetes cluster で Node Auto-Repair を実装する最も効果的な方法は、Node Problem Detector と custom controller を組み合わせて使用することです。このアプローチには次の利点があります:

1. **正確な問題検出**: Node Problem Detector (NPD) はさまざまな node problems を検出できる専用 tool です。次の issues を検出できます:
   - Kernel errors and crashes
   - Hardware problems
   - File system issues
   - Network problems
   - Resource shortage issues

2. **柔軟な対応**: custom controller を使用することで、検出された problems に対してさまざまな recovery strategies を実装できます:
   - 軽微な issues: Node reboot
   - 重大な issues: Node replacement
   - 特定 types の issues: 特定 service の restart

3. **Kubernetes native integration**: NPD は node status を NodeConditions として報告し、既存の Kubernetes mechanisms とよく統合されます。

4. **Cloud independent**: このアプローチはすべての environments（on-premises、各種 cloud providers）で機能します。

実装手順:

1. **Node Problem Detector を deploy する**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **custom controller を実装する**:
   - Kubernetes events と node status changes を watch する
   - 特定の NodeConditions に応答する logic を実装する
   - recovery operations（SSH 経由の command execution、cloud API 経由の node recreation など）を実行する

3. **alerts と logging を設定する**:
   - recovery operations の alerts を設定する
   - issues と recovery operations を log する

他の選択肢の問題点:

- **DaemonSet アプローチ**: node に重大な issues がある場合、DaemonSet 自体が影響を受ける可能性があり、すべての types of problems を検出することは困難です。

- **Cloud provider's managed node groups**: 特定の cloud providers に依存し、on-premises environments では使用できません。また、検出できる problems の types が限られる場合があります。

- **Cron job アプローチ**: 反応時間が遅く、problem detection capability が限られており、cluster 外で実行する必要があります。

Node Problem Detector と custom controller を組み合わせることで、さまざまな environments で機能する堅牢で柔軟な node auto-repair solution を実装できます。
</details>

5. Kubernetes cluster で RBAC (Role-Based Access Control) を効果的に管理するための best practice は何ですか？
   - A) Grant cluster-admin role to all users for easy management
   - B) Define fine-grained roles per namespace and apply principle of least privilege
   - C) Consolidate all permissions into a single ClusterRole for consistency
   - D) Always use user certificates instead of service accounts for authentication

<details>
<summary>解答を表示</summary>

**解答: B) Define fine-grained roles per namespace and apply principle of least privilege**

**解説:**
Kubernetes cluster で RBAC (Role-Based Access Control) を効果的に管理するための best practice は、namespace ごとに fine-grained roles を定義し、principle of least privilege を適用することです。このアプローチには次の利点があります:

1. **Principle of least privilege**: security risks を最小化するため、users と service accounts には必要最小限の permissions のみを付与します。これにより、意図しない変更や malicious behavior から cluster を保護できます。

2. **Namespace isolation**: namespace ごとに roles を定義することで、teams または applications 間の論理的な isolation が強化されます。これにより、ある team のミスが別の team の resources に影響することを防ぎます。

3. **Fine-grained access control**: 特定の resource types または operations に対して permissions を細かく制御できます。たとえば、developers には pods と services を管理する permissions を付与しつつ、secrets や namespace 自体を変更する permissions は制限できます。

4. **監査の容易さ**: fine-grained roles を使用すると、誰がどの operations を実行できるかが明確に文書化され、auditing と compliance が容易になります。

RBAC best practices の実装例:

1. **namespace ごとに roles を定義する**:
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

2. **role bindings を作成する**:
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

3. **cluster-level roles は控えめに使用する**:
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

4. **service accounts に fine-grained permissions を付与する**:
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

他の選択肢の問題点:

- **すべての users に cluster-admin role を付与する**: これは重大な security risks をもたらします。すべての users がすべての cluster resources に完全 access できる状態は、意図しない変更や malicious behavior に対して system を脆弱にします。

- **すべての permissions を単一の ClusterRole に統合する**: これにより fine-grained access control が不可能になり、principle of least privilege に違反します。

- **常に user certificates を使用する**: application authentication には service accounts が適切であり、すべての状況で user certificates を使用すると management burden が増加します。状況に応じて適切な authentication mechanism を選択することが重要です。
</details>
