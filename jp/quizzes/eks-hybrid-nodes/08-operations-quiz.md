# EKS Hybrid Nodes Operations クイズ

> **関連ドキュメント**: [Operations](../../eks-hybrid-nodes/08-operations.md)

## 選択式問題

### 1. Hybrid Nodes 環境で Node 監視に推奨されるツールの組み合わせは何ですか？

A. Notepad と手動記録
B. Prometheus + Grafana + Node Exporter
C. メール通知のみ
D. 手動でのログファイルレビュー

<details>
<summary>回答を表示</summary>

**回答: B. Prometheus + Grafana + Node Exporter**

**説明:**
Kubernetes 環境における標準的な monitoring stack は、Prometheus、Grafana、Node Exporter の組み合わせです。

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

**Monitoring Stack コンポーネント:**
- **Prometheus**: Metric の収集と保存
- **Grafana**: 可視化ダッシュボード
- **Node Exporter**: Node システムメトリクス
- **DCGM Exporter**: GPU メトリクス（GPU Node 用）
- **Alertmanager**: Alert 管理

```bash
# Install Prometheus stack (Helm)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

</details>

### 2. kubelet certificate の更新が必要な時期をどのように確認しますか？

A. certificate は永続的なので、確認は不要
B. openssl command で certificate の有効期限を確認する
C. Node が NotReady になるまで待つ
D. 毎日手動で更新する

<details>
<summary>回答を表示</summary>

**回答: B. openssl command で certificate の有効期限を確認する**

**説明:**
kubelet certificate は一定期間後に期限切れになるため、定期的に確認して更新する必要があります。

```bash
# Check kubelet certificate expiration
sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem \
  -text -noout | grep -A 2 "Validity"

# Or use kubeadm
kubeadm certs check-expiration

# Renew certificates (kubeadm cluster)
kubeadm certs renew all
```

**自動更新設定 (EKS):**
```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      rotateCertificates: true  # Auto certificate renewal
      serverTLSBootstrap: true
```

**監視アラート:**
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

### 3. Hybrid Node で kubelet が応答しない場合、最初に行う troubleshooting step は何ですか？

A. cluster 全体を再起動する
B. kubelet service のステータスとログを確認する
C. 新しい Node を作成する
D. すべての Pod を削除する

<details>
<summary>回答を表示</summary>

**回答: B. kubelet service のステータスとログを確認する**

**説明:**
kubelet 問題に対する体系的な troubleshooting 手順:

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

**一般的な kubelet failure の原因:**
- メモリ不足 (OOM)
- ディスク容量不足
- certificate の期限切れ
- ネットワーク切断
- containerd failure

</details>

### 4. Node メンテナンスのために workload を安全に移動するために使用する command はどれですか？

A. kubectl delete node
B. kubectl drain
C. kubectl cordon のみ
D. kubectl delete pods --all

<details>
<summary>回答を表示</summary>

**回答: B. kubectl drain**

**説明:**
`kubectl drain` は Node をスケジュール不可にし、既存の Pod を安全に退避します。

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

**drain と cordon の比較:**

| Command | Action |
|---------|--------|
| `kubectl cordon` | 新しい Pod scheduling のみを防止 |
| `kubectl drain` | cordon + 既存の Pod を退避 |
| `kubectl uncordon` | 再び scheduling を許可 |

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

### 5. Hybrid Nodes からのログを集中管理するための推奨ソリューションは何ですか？

A. 各 Node からログファイルを手動でコピーする
B. Fluent Bit/Fluentd を使用したログ収集と転送
C. ログ収集を行わない
D. Console 出力のみ

<details>
<summary>回答を表示</summary>

**回答: B. Fluent Bit/Fluentd を使用したログ収集と転送**

**説明:**
Fluent Bit または Fluentd は container log を収集し、中央 log storage に転送します。

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

**Logging Architecture:**
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

### 6. Node が failure したとき、Pod を他の Node に自動的に再スケジュールするまでのデフォルト待機時間はどれですか？

A. 即時（0 秒）
B. 30 秒
C. 5 分（300 秒）
D. 1 時間

<details>
<summary>回答を表示</summary>

**回答: C. 5 分（300 秒）**

**説明:**
Kubernetes のデフォルトの `pod-eviction-timeout` は 5 分です。Node が NotReady になってから 5 分後に Pod は退避されます。

```yaml
# Node Lifecycle Controller settings (kube-controller-manager)
# --pod-eviction-timeout=5m0s  (default)
# --node-monitor-grace-period=40s  (NotReady detection)
```

**より高速な failover のための設定:**
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

**Node State Transitions:**
```
Ready --(40s)--> NotReady --(5min)--> Pod Eviction
         |                    |
    node-monitor-        pod-eviction-
    grace-period         timeout
```

</details>

### 7. EKS Hybrid Nodes upgrade の推奨 strategy は何ですか？

A. すべての Node を同時に upgrade する
B. Rolling upgrade（1 台ずつ）
C. cluster を削除して再作成する
D. upgrade しない

<details>
<summary>回答を表示</summary>

**回答: B. Rolling upgrade（1 台ずつ）**

**説明:**
Rolling upgrade は、サービス中断なしで Node を順次 upgrade します。

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

**Upgrade Checklist:**
- [ ] PodDisruptionBudget 設定を確認する
- [ ] Node を順次 upgrade する
- [ ] 各 step 後にステータスを確認する
- [ ] rollback plan を準備する
- [ ] バックアップを実行する

</details>
