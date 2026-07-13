## 短答問題

1. Kubernetes cluster における etcd database の backup と restore 手順を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**etcd Backup 手順:**

1. **etcdctl tool の install を確認する:**
   ```bash
   etcdctl version
   ```

2. **backup command を実行する:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

3. **backup file を検証する:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot status snapshot.db --write-out=table
   ```

4. **backup file を安全な場所に保管する:**
   - cluster 外の storage
   - Cloud storage (S3, GCS など)
   - 異なる物理的な場所

**etcd Restore 手順:**

1. **restore のためにすべての API server を停止する:**
   ```bash
   sudo systemctl stop kube-apiserver
   ```

2. **etcd service を停止する:**
   ```bash
   sudo systemctl stop etcd
   ```

3. **data directory を backup する（任意）:**
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

5. **restore した data directory を使用するように etcd を構成する:**
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

**Best Practice:**
- 定期的な backup schedule（例: 毎日）を設定する
- backup 前に etcd cluster status を確認する
- backup file の完全性を検証する
- restore 手順を定期的に test する
- backup filename に timestamp を含める
- 複数の backup version を保持する
- backup と restore 手順を document 化する
</details>

2. Kubernetes cluster における node maintenance の手順を説明し、`cordon`、`drain`、`uncordon` command の違いを説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**Node Maintenance 手順:**

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

4. **maintenance task を実行する:**
   - Software update
   - Kernel upgrade
   - Hardware replacement
   - Configuration change

5. **task 完了後に node を uncordon する:**
   ```bash
   kubectl uncordon <node_name>
   ```

6. **node status を確認する:**
   ```bash
   kubectl get nodes
   ```

**Command の違い:**

1. **`kubectl cordon <node_name>`:**
   - node を scheduling 不可として mark します。
   - 新しい Pod はその node に schedule されません。
   - 既に実行中の Pod は実行を継続します。
   - node status に `SchedulingDisabled` indicator が表示されます。

2. **`kubectl drain <node_name>`:**
   - node を scheduling 不可として mark します（cordon を含みます）。
   - 実行中の Pod を node から安全に evict します。
   - Pod は他の node に reschedule されます。
   - DaemonSet Pod は default で無視されます（`--ignore-daemonsets` flag が必要）。
   - emptyDir volume を使用する Pod は data を失う可能性があり、特別な handling が必要です（`--delete-emptydir-data` flag）。
   - PodDisruptionBudget を尊重します。

3. **`kubectl uncordon <node_name>`:**
   - node を再び scheduling 可能として mark します。
   - 新しい Pod を node に schedule できます。
   - 以前に evict された Pod は自動的には戻りません。

**Maintenance の考慮事項:**
- cluster に十分な spare capacity があることを確認する
- critical workload に PodDisruptionBudget を設定する
- maintenance は一度に 1 つの node で実行する
- maintenance 期間中は auto-scaling setting を調整する
- maintenance 前後で workload status を確認する
- rolling update strategy を使用する
</details>

3. Kubernetes cluster における resource usage を監視および管理する方法を説明してください。含めるべき tool と technique を列挙してください。

<details>
<summary>答えを表示</summary>

**答え:**

**Kubernetes Resource Monitoring と Management の方法:**

**1. 基本 Monitoring Tool:**

- **Metrics Server:**
  - 基本的な CPU と memory usage metrics を提供します
  - `kubectl top` command を support します
  - Installation method:
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    ```
  - Usage examples:
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Kubernetes Dashboard:**
  - cluster status と resource usage を visual に表示します
  - Pod、node、namespace などの resource management interface を提供します

**2. 高度な Monitoring Stack:**

- **Prometheus + Grafana:**
  - Prometheus: Metric の収集と保存
  - Grafana: Metric visualization と dashboard
  - kube-prometheus-stack または Prometheus Operator 経由で install できます
  - custom alerting rule と dashboard を support します

- **ELK/EFK Stack:**
  - Elasticsearch: Log の保存と search
  - Logstash/Fluentd: Log の収集と processing
  - Kibana: Log visualization と analysis

**3. Resource Management Technique:**

- **resource request と limit の設定:**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **Namespace-level resource quota (ResourceQuota):**
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

- **Default resource limit (LimitRange):**
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
  - Pod の CPU と memory request を自動的に調整します
  - resource usage pattern に基づく recommendation を提供します

- **Cluster Autoscaler:**
  - workload requirement に基づいて cluster node 数を自動的に調整します
  - resource が不足している場合は node を追加し、utilization が低い場合は node を削除します

**4. Monitoring Best Practice:**

- すべての Pod に resource request と limit を設定する
- critical metrics に対する alert を構成する
- historical usage analysis に基づいて resource を計画する
- 定期的な resource audit を実行する
- cost optimization のために resource usage trend を分析する
- development、staging、production environment に適切な resource quota を設定する
- node-level と pod-level の metrics の両方を監視する
</details>

4. Kubernetes cluster upgrade 中に発生しうる主な risk と、それらを軽減する strategy を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**Kubernetes Cluster Upgrade の Risk と Mitigation Strategy:**

**1. 主な Risk:**

- **API Compatibility Issue:**
  - 新しい version で API が変更または削除される場合があります
  - 一部の Custom Resource Definitions (CRDs) や API version が support されなくなる場合があります

- **Workload Disruption:**
  - control plane component の restart により、API server が一時的に利用できなくなる場合があります
  - node upgrade 中の Pod rescheduling により、Service disruption が発生する場合があります

- **Feature Change:**
  - default behavior が変更され、既存 workload に影響する場合があります
  - security policy change により permission issue が発生する場合があります

- **Performance Issue:**
  - 新しい version で resource requirement が増える場合があります
  - 初期 stabilization period 中に performance degradation が発生する可能性があります

- **Rollback Complexity:**
  - 一部の upgrade は簡単に rollback できません
  - data format change により rollback に制限が生じる場合があります

**2. Mitigation Strategy:**

- **十分な Planning と Preparation:**
  - **changelog を確認する:** 新しい version の変更点、削除された feature、known issue を確認する
  - **upgrade path を確認する:** current version から target version への direct upgrade が support されていることを確認する
  - **resource requirement を確認する:** 新しい version の minimum requirement を確認する

- **まず Test Environment で Test する:**
  - production に類似した test cluster で upgrade を実行する
  - すべての critical workload と custom resource を test する
  - automated test suite を実行する

- **API Compatibility を確認する:**
  - 使用中の API version を確認する:
    ```bash
    kubectl api-resources -o wide
    ```
  - deprecated API usage を確認する:
    ```bash
    kubectl get -A | grep "deprecated"
    ```
  - 必要に応じて manifest を更新する

- **Backup と Recovery Plan:**
  - etcd database を backup する:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db
    ```
  - すべての critical manifest を backup する:
    ```bash
    kubectl get all --all-namespaces -o yaml > all-resources.yaml
    ```
  - recovery procedure を document 化し test する

- **段階的な Upgrade Approach:**
  - **control plane component を先に upgrade する:**
    - HA setup では、control plane node を一度に 1 つずつ upgrade する
  - **worker node の rolling upgrade:**
    - node group を小さな batch に分けて upgrade する
    - 各 batch 後に stability を確認する

- **Workload Protection:**
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
  - **node を drain するときは注意する:**
    ```bash
    kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
    ```

- **Monitoring の強化:**
  - upgrade 前、upgrade 中、upgrade 後に cluster status を監視する
  - key metrics と log に注目する
  - alert threshold を一時的に調整する

- **Rollback Plan:**
  - rollback trigger condition を定義する
  - rollback procedure を document 化する
  - rollback に必要なすべての component と image を保持する

- **Communication Plan:**
  - upgrade schedule と expected impact をすべての stakeholder に通知する
  - upgrade 中に status update を提供する
  - issue の escalation path を定義する

**3. Version 固有の考慮事項:**

- **Minor Version Upgrade (例: 1.24 → 1.25):**
  - removed API と feature change に特に注意する
  - minor version は一度に 1 つずつ upgrade する

- **Patch Version Upgrade (例: 1.24.0 → 1.24.1):**
  - 一般的により安全ですが、test は依然として必要です
  - security patch ではより迅速な deployment を検討する
</details>

5. Kubernetes cluster で発生しうる一般的な networking issue と、それらを diagnose および resolve する方法を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**Kubernetes Networking Issue の Diagnosis と Resolution:**

**1. Pod-to-Pod Communication Issue:**

- **Symptoms:**
  - Pod が他の Pod と通信できない
  - service name で接続できない
  - Network timeout error

- **Diagnosis Method:**
  - network policy を確認する:
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - connectivity testing 用の test pod を作成する:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    ping <target_pod_IP>
    wget -O- <service_name>:<port>
    ```
  - CNI plugin Pod status を確認する:
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **Resolution Method:**
  - CNI plugin を reinstall または update する
  - network policy を変更または削除する
  - node network interface を確認する
  - firewall rule を確認する

**2. Service Discovery と DNS Issue:**

- **Symptoms:**
  - service name で接続できない
  - DNS lookup failure
  - intermittent connection issue

- **Diagnosis Method:**
  - CoreDNS Pod status を確認する:
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - DNS lookup を test する:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    nslookup kubernetes.default.svc.cluster.local
    nslookup <service_name>.<namespace>.svc.cluster.local
    cat /etc/resolv.conf
    ```
  - service endpoint を確認する:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Resolution Method:**
  - CoreDNS Pod を restart する:
    ```bash
    kubectl rollout restart deployment coredns -n kube-system
    ```
  - DNS configuration を確認および変更する:
    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
  - kubelet DNS setting を確認する

**3. Service と Ingress Issue:**

- **Symptoms:**
  - external source から service に access できない
  - Ingress rule が動作しない
  - load balancer が作成されない

- **Diagnosis Method:**
  - service status を確認する:
    ```bash
    kubectl describe service <service_name>
    ```
  - ingress status を確認する:
    ```bash
    kubectl describe ingress <ingress_name>
    ```
  - ingress controller Pod log を確認する:
    ```bash
    kubectl logs -n <ingress_namespace> <ingress_controller_pod>
    ```
  - endpoint を確認する:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Resolution Method:**
  - service selector が Pod label と一致することを確認する
  - ingress controller を reinstall または update する
  - service type と port configuration を確認する
  - cloud provider load balancer setting を確認する

**4. Node Networking Issue:**

- **Symptoms:**
  - node が cluster から切断されている
  - node-to-node communication failure
  - kubelet connection error

- **Diagnosis Method:**
  - node status を確認する:
    ```bash
    kubectl describe node <node_name>
    ```
  - node network interface を確認する:
    ```bash
    # Directly on the node
    ip addr
    ip route
    ```
  - firewall rule を確認する:
    ```bash
    # Directly on the node
    iptables -L
    ```
  - kubelet log を確認する:
    ```bash
    journalctl -u kubelet
    ```

- **Resolution Method:**
  - node network interface を再構成する
  - firewall rule を変更する
  - kubelet を restart する
  - 必要に応じて node を reboot する

**5. Network Policy Issue:**

- **Symptoms:**
  - 予期しない connection blocking
  - 特定の namespace 間で通信できない
  - 一部の Pod のみ access 可能

- **Diagnosis Method:**
  - network policy を確認する:
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - Pod label を確認する:
    ```bash
    kubectl get pods --show-labels
    ```
  - network plugin が network policy を support していることを確認する

- **Resolution Method:**
  - network policy を変更または削除する
  - Pod label を変更する
  - network policy debugging tool を使用する

**6. 一般的な Networking Debugging Tool:**

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

- **Useful commands:**
  ```bash
  # Inside the pod
  ping <IP>
  traceroute <IP>
  dig <service_name>.<namespace>.svc.cluster.local
  curl -v <URL>
  tcpdump -i any
  netstat -tuln
  ```

- **CNI plugin-specific debugging tools:**
  - Calico: `calicoctl`
  - Cilium: `cilium`
  - Weave: `weave`

**7. Best Practice:**

- network topology を document 化する
- 定期的な connectivity test を実行する
- network policy change の前に impact を分析する
- cluster network CIDR range を計画する
- network monitoring tool を実装する
</details>
## ハンズオン問題

1. 次の要件を満たす ResourceQuota manifest を作成してください:
   - Namespace: development
   - Maximum pods: 20
   - Maximum CPU requests: 4 cores
   - Maximum memory requests: 8Gi
   - Maximum PVCs: 10
   - Maximum storage requests: 100Gi

<details>
<summary>答えを表示</summary>

**答え:**

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

この ResourceQuota は 'development' namespace に次の limit を設定します:
- 最大 20 Pod
- 合計 CPU request 4 cores
- 合計 memory request 8Gi
- 最大 10 PersistentVolumeClaims
- 合計 storage request 100Gi

ResourceQuota を適用するには:
```bash
kubectl apply -f resource-quota.yaml
```

current quota usage を確認するには:
```bash
kubectl describe quota dev-quota -n development
```

注: ResourceQuota を適用する前に namespace が既に存在している必要があります。namespace が存在しない場合は、先に作成してください:
```bash
kubectl create namespace development
```
</details>

2. cluster 内のすべての node で kubelet service status を確認し、issue が見つかった場合に解決する script を作成してください。

<details>
<summary>答えを表示</summary>

**答え:**

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

この script は次の task を実行します:
1. `kubectl get nodes` を使用して cluster 内のすべての node list を取得します。
2. 各 node について:
   - node の Ready status を確認します。
   - SSH 経由で node に接続し、kubelet service status を確認します。
   - kubelet が実行されていない場合は service を開始します。
   - service 開始後に status を再確認します。
   - startup が失敗した場合は log を確認します。
   - kubelet configuration file の key setting を確認します。

**Usage:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
```

**Notes:**
- この script を実行するには、すべての node への SSH access が必要です。
- production environment では SSH key-based authentication が推奨されます。
- cloud environment では node への direct SSH access が制限される場合があるため、cloud provider の node management tool を使用する必要がある場合があります。
</details>

3. cluster の etcd database を backup し、backup file を安全な場所に保存する cron job を設定してください。

<details>
<summary>答えを表示</summary>

**答え:**

**1. backup script を作成する:**

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

**2. script に execute permission を付与する:**

```bash
chmod +x /opt/etcd-backup/backup_etcd.sh
```

**3. cron job を設定する:**

```bash
# Edit root user's crontab
sudo crontab -e
```

次の content を追加します:

```
# Run etcd backup daily at 2 AM
0 2 * * * /opt/etcd-backup/backup_etcd.sh >> /var/log/etcd-backup.log 2>&1
```

**4. backup log rotation を設定する:**

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

**5. backup を test する:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. backup monitoring を設定する（任意）:**

backup failure の alert を受け取るには、Prometheus などの monitoring tool と統合できます。backup script に次の code を追加します:

```bash
# Create file indicating backup success/failure
if [ $? -eq 0 ]; then
  echo "success" > /var/lib/node_exporter/etcd_backup_status.prom
else
  echo "failure" > /var/lib/node_exporter/etcd_backup_status.prom
fi
```

**Notes:**
- backup file は cluster 外の安全な場所に保存する必要があります。
- cloud environment では S3 や GCS などの object storage の使用が推奨されます。
- backup validity を確認するため、定期的に backup restoration test を実行してください。
- HA etcd cluster では、backup は 1 つの etcd instance でのみ実行すれば十分です。
</details>
4. cluster 内のすべての node で rolling update を実行する手順を作成してください。update 中も workload availability を維持する必要があります。

<details>
<summary>答えを表示</summary>

**答え:**

**Node Rolling Update 手順:**

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

**Rolling Update 前の準備:**

1. **PodDisruptionBudget を設定する:**
   availability を確保するため、critical workload に PDB を設定します。

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

2. **十分な Resource を確保する:**
   1 つの node が除外されたときに、残りの node がすべての workload を処理できることを確認します。

3. **Backup を実行する:**
   update 前に etcd database backup を実行します。

**Rolling Update Best Practice:**

1. **段階的 Approach:**
   - 一度に 1 つの node のみ update する
   - 各 node update 後に cluster status を確認する

2. **Automation と Idempotency:**
   - script を使用して process を自動化する
   - failure 時に安全に retry できるように design する

3. **Monitoring の強化:**
   - update 中に cluster metrics を監視する
   - application status と performance を監視する

4. **Rollback Plan:**
   - issue に備えて rollback procedure を準備する
   - previous state に restore する方法を用意する

5. **Communication:**
   - update schedule と expected impact を announce する
   - update progress を定期的に report する

**Notes:**
- cloud environment では、managed Kubernetes services (EKS, GKE, AKS など) の node update feature を活用できます。
- 複数の node group がある場合は、group ごとに update を実行します。
- critical system Pod (CoreDNS、kube-proxy など) の status を特に監視します。
</details>

5. cluster 内で resource usage が高い Pod を特定し、その情報を含む report を生成する script を作成してください。

<details>
<summary>答えを表示</summary>

**答え:**

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

**Script Usage:**
```bash
chmod +x resource_usage_report.sh
./resource_usage_report.sh
```

**Script の Feature:**
1. cluster information を収集する
2. node resource usage を収集する
3. CPU と memory usage による top Pod を特定する
4. namespace ごとの resource usage を計算する
5. request に対して usage が高い Pod を特定する
6. resource request がない Pod を特定する
7. text format と HTML format の report を生成する

**Notes:**
- この script には `kubectl`、`jq`、`bc` tool が必要です。
- cluster に Metrics Server が install されている必要があります。
- 大規模 cluster では script execution time が長くなる場合があります。
- 定期的な report generation のために cron job として設定できます。
- report は email で送信したり monitoring system と統合したりできます。
</details>
## 高度なトピック

1. Kubernetes cluster における etcd performance を最適化するための key configuration parameter と best practice は何ですか？
   - A) `--max-request-bytes`, `--quota-backend-bytes`, regular compaction
   - B) `--max-concurrent-requests`, `--max-connections`, disk RAID configuration
   - C) `--auto-compaction-retention`, `--snapshot-count`, SSD storage
   - D) `--max-txn-ops`, `--max-result-buffer`, memory expansion

<details>
<summary>答えを表示</summary>

**答え: C) `--auto-compaction-retention`, `--snapshot-count`, SSD storage**

**解説:**
etcd は Kubernetes cluster の core data store であり、その performance は cluster 全体の performance に直接影響します。etcd performance を最適化するための key configuration parameter と best practice は次のとおりです:

1. **`--auto-compaction-retention`**: etcd はすべての変更履歴を保持する append-only store です。この parameter は key の以前の version を自動的に compact する interval を設定します。default は 0（disabled）ですが、production environment では通常 1 hour (1h) または 24 hours (24h) に設定されます。これにより、disk space を節約し、performance を向上できます。

2. **`--snapshot-count`**: etcd が snapshot を作成する前に commit する transaction 数を指定します。default は 100,000 ですが、大規模 cluster では snapshot creation frequency を最適化するためにこの value を調整できます。小さい value では snapshot がより頻繁に作成され、recovery time は短縮されますが disk I/O は増加します。

3. **SSD storage**: etcd は disk I/O に敏感なため、SSD (Solid State Drives) を使用すると performance が大幅に向上します。大規模 cluster では SSD 使用が不可欠です。

その他の重要な optimization setting と best practice:

- **dedicated disk を使用する**: 他の application との I/O contention を防ぐため、etcd data には dedicated disk を使用します。
- **適切な memory allocation**: etcd は performance のために data を memory に cache するため、十分な memory を割り当てる必要があります。
- **cluster size を最適化する**: 通常、3～5 個の etcd member が最適な performance と availability を提供します。
- **network latency を最小化する**: member 間の network latency を最小化するため、etcd member を同じ data center または availability zone に配置します。
- **定期的な backup と compaction**: data safety と効率的な disk space usage を確保するため、定期的な backup と compaction を実行します。

`--max-request-bytes` と `--quota-backend-bytes` は実際の etcd parameter ですが、主に performance ではなく resource limit に関連しています。`--max-concurrent-requests`、`--max-connections`、`--max-txn-ops`、`--max-result-buffer` は実際の etcd parameter ではないか、performance optimization の primary factor ではありません。
</details>

2. Kubernetes cluster で control plane high availability (HA) を実装する最も効果的な方法は何ですか？
   - A) Running multiple API server instances on a single master node
   - B) Configuring an etcd cluster with multiple master nodes and a load balancer
   - C) Deploying the API server as a StatefulSet with PersistentVolume
   - D) Implementing a watchdog process with auto-recovery on the master node

<details>
<summary>答えを表示</summary>

**答え: B) Configuring an etcd cluster with multiple master nodes and a load balancer**

**解説:**
Kubernetes control plane high availability (HA) を実装する最も効果的な方法は、複数の master node と load balancer を備えた etcd cluster を構成することです。この approach は次の component で構成されます:

1. **複数の master node**: single point of failure を排除するため、通常は異なる availability zone に 3 または 5 個の master node を deploy します。各 master node は次の control plane component を実行します:
   - kube-apiserver: API request を処理する server
   - kube-controller-manager: controller process を実行します
   - kube-scheduler: Pod scheduling decision

2. **etcd cluster**: etcd はすべての Kubernetes cluster data を保存する distributed key-value store です。high availability のため、通常は 3 または 5 個の etcd instance を実行します。etcd は master node 上で直接実行することも、dedicated node 上で実行することもできます。

3. **Load balancer**: client request を複数の kube-apiserver instance に分散するために load balancer が必要です。これは通常、cloud provider load balancer service または HAProxy や Nginx などの software load balancer を使用して実装されます。

この configuration の主な benefit:
- **Fault tolerance**: 1 つの master node が failure しても cluster は operation を継続します。
- **High availability**: 複数の availability zone に deploy することで、data center level の failure にも対応できます。
- **Scalability**: API server request を複数 instance に分散して処理できます。
- **Data consistency**: etcd の Raft consensus algorithm により data consistency が保証されます。

他の option の問題点:
- 単一の master node 上で複数の API server instance を実行すると、その node 自体が single point of failure になります。
- API server を StatefulSet として deploy するのは一般的な approach ではなく、control plane component は通常 Kubernetes の外部で管理されます。
- watchdog process は役立つ場合がありますが、それ単体では真の high availability solution ではありません。
</details>

3. Kubernetes cluster で audit logging を構成する際の最も重要な consideration は何ですか？
   - A) Logging all API requests to ensure complete audit trail
   - B) Using audit policies to selectively log only important events
   - C) Real-time streaming of audit logs to an external SIEM system
   - D) Restricting access to audit logs to administrators only

<details>
<summary>答えを表示</summary>

**答え: B) Using audit policies to selectively log only important events**

**解説:**
Kubernetes audit logging を構成する際の最も重要な consideration は、audit policy を使用して重要な event のみを選択的に log に記録することです。これは次の理由で重要です:

1. **performance impact を最小化する**: すべての API request を log に記録すると、API server に大きな load がかかり、performance が低下する可能性があります。大規模 cluster では 1 秒あたり数千の API request が発生する場合があります。

2. **storage efficiency**: すべての event を log に記録すると log data が急速に増加し、storage cost が増加し、log analysis が困難になります。

3. **relevant information に focus する**: 重要な event のみを log に記録することで、security analyst は critical information に focus できます。

4. **Compliance**: 多くの compliance requirement は、すべての event ではなく特定 type の event の logging を要求します。

Kubernetes audit policy は次の audit level を support します:

- **None**: event を log に記録しません。
- **Metadata**: request metadata（user、timestamp、resource、action など）のみを log に記録し、request/response body は除外します。
- **Request**: metadata と request body を log に記録しますが、response body は除外します。
- **RequestResponse**: metadata、request body、response body を log に記録します。

効果的な audit policy の例:
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

他の option の問題点:
- すべての API request を log に記録すると performance と storage の issue が発生する可能性があります。
- external SIEM system への real-time streaming は重要ですが、何を log に記録するかを決定することより priority は低いです。
- audit log への access を制限することは重要ですが、logging policy 自体ではなく security measure です。
</details>

4. Kubernetes cluster で node auto-repair を実装する最も効果的な方法は何ですか？
   - A) Deploy a DaemonSet that monitors node status and automatically reboots problematic nodes
   - B) Utilize cloud provider's managed node groups and auto-repair features
   - C) Use Node Problem Detector and custom controllers for node status monitoring and recovery
   - D) Implement a cron job that periodically checks node status and recreates problematic nodes

<details>
<summary>答えを表示</summary>

**答え: C) Use Node Problem Detector and custom controllers for node status monitoring and recovery**

**解説:**
Kubernetes cluster で node auto-repair を実装する最も効果的な方法は、Node Problem Detector と custom controller を併用することです。この approach には次の benefit があります:

1. **正確な problem detection**: Node Problem Detector (NPD) は、次を含むさまざまな node problem を detect できる special-purpose tool です:
   - Kernel error と crash
   - Hardware issue
   - File system issue
   - Network issue
   - Resource shortage issue

2. **柔軟な response**: Custom controller により、detect された problem に対してさまざまな recovery strategy を実装できます:
   - Minor problem: Node reboot
   - Serious problem: Node replacement
   - Specific type の problem: Specific service restart

3. **Kubernetes native integration**: NPD は node status を NodeConditions として report し、既存の Kubernetes mechanism とよく統合されます。

4. **Cloud independent**: この approach はすべての environment（on-premises、各種 cloud provider）で機能します。

実装手順:

1. **Node Problem Detector を deploy する**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **custom controller を実装する**:
   - Kubernetes event と node status change を watch する
   - 特定の NodeCondition に対応する logic を実装する
   - recovery action（SSH 経由の command execution、cloud API 経由の node recreation など）を実行する

3. **alert と logging を設定する**:
   - recovery action に対する alert を構成する
   - problem と recovery action を log に記録する

他の option の問題点:

- **DaemonSet approach**: node に深刻な problem がある場合、DaemonSet 自体が影響を受ける可能性があり、すべての type の problem を detect するのは困難です。

- **Cloud provider's managed node groups**: 特定の cloud provider に依存し、on-premises environment では使用できません。detect できる problem の type も限られる場合があります。

- **Cron job approach**: reaction time が遅く、problem detection capability が限られており、cluster 外で実行する必要があります。

Node Problem Detector と custom controller を組み合わせることで、さまざまな environment で機能する強力で柔軟な node auto-repair solution を実装できます。
</details>

5. Kubernetes cluster で RBAC (Role-Based Access Control) を効果的に管理するための best practice は何ですか？
   - A) Grant cluster-admin role to all users for ease of management
   - B) Define granular roles by namespace and apply the principle of least privilege
   - C) Consolidate all permissions into a single ClusterRole for consistency
   - D) Always use user certificates instead of service accounts for authentication

<details>
<summary>答えを表示</summary>

**答え: B) Define granular roles by namespace and apply the principle of least privilege**

**解説:**
Kubernetes cluster で RBAC (Role-Based Access Control) を効果的に管理するための best practice は、namespace ごとに granular role を定義し、least privilege の原則を適用することです。この approach には次の benefit があります:

1. **Principle of least privilege**: user と service account に必要最小限の permission のみを付与し、security risk を最小化します。これにより、意図しない change や malicious action から cluster を保護できます。

2. **Namespace isolation**: namespace ごとに role を定義することで、team や application 間の logical isolation が強化されます。これにより、ある team の mistake が別の team の resource に影響するのを防ぎます。

3. **Granular access control**: 特定の resource type や action に対して permission を細かく制御できます。たとえば、developer には Pod と Service を管理する permission を付与しつつ、Secret や namespace 自体を変更する permission を制限できます。

4. **Audit ease**: granular role を使用すると、誰がどの action を実行できるかが明確に document 化され、audit と compliance が容易になります。

RBAC best practice の実装例:

1. **namespace ごとに role を定義する**:
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

2. **role binding を作成する**:
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

3. **cluster-level role は控えめに使用する**:
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

4. **service account に granular permission を設定する**:
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

他の option の問題点:

- **すべての user に cluster-admin role を付与する**: これは重大な security risk をもたらします。すべての user が cluster 内のすべての resource に完全 access できるようになり、意図しない change や malicious action に脆弱になります。

- **すべての permission を単一の ClusterRole に統合する**: これにより granular access control が不可能になり、least privilege の原則に違反します。

- **常に user certificate を使用する**: service account は application authentication に適しており、すべての状況で user certificate を使用すると management burden が増加します。状況に基づいて適切な authentication mechanism を選択することが重要です。
</details>
