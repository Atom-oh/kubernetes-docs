# EKS Hybrid Nodes Operations Quiz

> **Related Document**: [Operations](../../eks-hybrid-nodes/08-operations.md)

## Multiple Choice Questions

### 1. What is the recommended tool combination for node monitoring in Hybrid Nodes environments?

A. Notepad and manual recording
B. Prometheus + Grafana + Node Exporter
C. Email notifications only
D. Manual log file review

<details>
<summary>Show Answer</summary>

**Answer: B. Prometheus + Grafana + Node Exporter**

**Explanation:**
The standard monitoring stack in Kubernetes environments is the combination of Prometheus, Grafana, and Node Exporter.

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

**Monitoring Stack Components:**
- **Prometheus**: Metric collection and storage
- **Grafana**: Visualization dashboards
- **Node Exporter**: Node system metrics
- **DCGM Exporter**: GPU metrics (for GPU nodes)
- **Alertmanager**: Alert management

```bash
# Install Prometheus stack (Helm)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

</details>

### 2. How do you check when kubelet certificate renewal is needed?

A. Certificates are permanent, no check needed
B. Check certificate expiration date with openssl command
C. Wait until node becomes NotReady
D. Renew manually every day

<details>
<summary>Show Answer</summary>

**Answer: B. Check certificate expiration date with openssl command**

**Explanation:**
kubelet certificates expire after a certain period and must be periodically checked and renewed.

```bash
# Check kubelet certificate expiration
sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem \
  -text -noout | grep -A 2 "Validity"

# Or use kubeadm
kubeadm certs check-expiration

# Renew certificates (kubeadm cluster)
kubeadm certs renew all
```

**Auto-renewal configuration (EKS):**
```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      rotateCertificates: true  # Auto certificate renewal
      serverTLSBootstrap: true
```

**Monitoring alert:**
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

### 3. What is the first troubleshooting step when kubelet is not responding on a Hybrid Node?

A. Restart entire cluster
B. Check kubelet service status and logs
C. Create new node
D. Delete all Pods

<details>
<summary>Show Answer</summary>

**Answer: B. Check kubelet service status and logs**

**Explanation:**
Systematic troubleshooting procedure for kubelet issues:

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

**Common kubelet failure causes:**
- Out of memory (OOM)
- Insufficient disk space
- Certificate expiration
- Network disconnection
- containerd failure

</details>

### 4. What command is used to safely move workloads for node maintenance?

A. kubectl delete node
B. kubectl drain
C. kubectl cordon only
D. kubectl delete pods --all

<details>
<summary>Show Answer</summary>

**Answer: B. kubectl drain**

**Explanation:**
`kubectl drain` makes the node unschedulable and safely evicts existing Pods.

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

**drain vs cordon comparison:**

| Command | Action |
|---------|--------|
| `kubectl cordon` | Only prevent new Pod scheduling |
| `kubectl drain` | cordon + evict existing Pods |
| `kubectl uncordon` | Allow scheduling again |

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

### 5. What is the recommended solution for centralizing logs from Hybrid Nodes?

A. Manually copy log files from each node
B. Log collection and forwarding using Fluent Bit/Fluentd
C. No log collection
D. Console output only

<details>
<summary>Show Answer</summary>

**Answer: B. Log collection and forwarding using Fluent Bit/Fluentd**

**Explanation:**
Fluent Bit or Fluentd collects container logs and forwards them to central log storage.

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

### 6. What is the default wait time before automatically rescheduling Pods to other nodes when a node fails?

A. Immediately (0 seconds)
B. 30 seconds
C. 5 minutes (300 seconds)
D. 1 hour

<details>
<summary>Show Answer</summary>

**Answer: C. 5 minutes (300 seconds)**

**Explanation:**
The default `pod-eviction-timeout` in Kubernetes is 5 minutes. Pods are evicted 5 minutes after a node becomes NotReady.

```yaml
# Node Lifecycle Controller settings (kube-controller-manager)
# --pod-eviction-timeout=5m0s  (default)
# --node-monitor-grace-period=40s  (NotReady detection)
```

**Configuration for faster failover:**
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

### 7. What is the recommended strategy for EKS Hybrid Nodes upgrades?

A. Upgrade all nodes simultaneously
B. Rolling upgrade (one at a time)
C. Delete and recreate cluster
D. No upgrades

<details>
<summary>Show Answer</summary>

**Answer: B. Rolling upgrade (one at a time)**

**Explanation:**
Rolling upgrades sequentially upgrade nodes without service interruption.

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
- [ ] Verify PodDisruptionBudget settings
- [ ] Sequential node upgrades
- [ ] Verify status after each step
- [ ] Prepare rollback plan
- [ ] Perform backups

</details>

