# Cluster Administration Quiz

This quiz covers self-managed and EKS operations, backups, maintenance, monitoring, and recovery. The 15 original exercises are retained; host-level etcd procedures do not apply to the managed EKS control plane.

## Short Answer Questions

1. Explain the backup and restore procedures for the etcd database in a Kubernetes cluster.

<details>
<summary>Show Answer</summary>

**Answer:**

**etcd Backup Procedure:**

1. **Verify etcdctl tool installation:**
   ```bash
   etcdctl version
   ```

2. **Execute backup command:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

3. **Verify backup file:**
   ```bash
   etcdutl snapshot status snapshot.db --write-out=table
   ```

4. **Store backup file in a safe location:**
   - Storage outside the cluster
   - Cloud storage (S3, GCS, etc.)
   - Different physical location

**etcd Restore Procedure:**

1. Validate the snapshot and preserve original data, PKI, and encryption-provider keys/configuration. An etcd snapshot does not contain PV files or all host configuration.
2. Stop all API servers and affected etcd processes using the distribution's runbook. kubeadm commonly uses static Pods, not separate systemd units; stopping kubelet alone does not stop those containers.
3. Restore offline into a new directory using a compatible etcdutl. This single-member example is not an HA recovery command:

```bash
etcdutl snapshot restore snapshot.db \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

4. For HA, restore the same snapshot to every member with its own name/peer URL and an identical full membership list. Set the revision bump high enough to exceed writes since the snapshot and invalidate watch caches.
5. Point the etcd manifest/service at the restored data with correct ownership and certificates. Verify etcd quorum/health before restarting API servers/controllers, then verify nodes and workloads.
6. Follow the [official recovery procedure](https://etcd.io/docs/v3.6/op-guide/recovery/). EKS users restore application resources/data through supported backup tools rather than accessing managed etcd.

**Best Practices:**
- Set up regular backup schedules (e.g., daily)
- Verify etcd cluster status before backup
- Validate backup file integrity
- Regularly test restore procedures
- Include timestamps in backup filenames
- Maintain multiple backup versions
- Document backup and restore procedures
</details>

2. Explain the procedure for node maintenance in a Kubernetes cluster and describe the differences between the `cordon`, `drain`, and `uncordon` commands.

<details>
<summary>Show Answer</summary>

**Answer:**

**Node Maintenance Procedure:**

1. **Check node status:**
   ```bash
   kubectl get nodes
   kubectl describe node <node_name>
   ```

2. **Cordon the node:**
   ```bash
   kubectl cordon <node_name>
   ```

3. **Drain the node:**
   ```bash
   kubectl drain <node_name> --ignore-daemonsets
   ```

4. **Perform maintenance tasks:**
   - Software updates
   - Kernel upgrades
   - Hardware replacement
   - Configuration changes

5. **Uncordon the node after completing tasks:**
   ```bash
   kubectl uncordon <node_name>
   ```

6. **Verify node status:**
   ```bash
   kubectl get nodes
   ```

**Command Differences:**

1. **`kubectl cordon <node_name>`:**
   - Marks the node as unschedulable.
   - New pods will not be scheduled on the node.
   - Already running pods continue to run.
   - `SchedulingDisabled` indicator appears in node status.

2. **`kubectl drain <node_name>`:**
   - Marks the node as unschedulable (includes cordon).
   - Safely evicts running pods from the node.
   - Workload controllers may create replacement Pods; scheduling them depends on capacity and constraints.
   - Drain refuses DaemonSet Pods unless --ignore-daemonsets is supplied; that flag leaves them running.
   - Pods using emptyDir volumes may lose data, requiring special handling (`--delete-emptydir-data` flag).
   - Respects PodDisruptionBudgets.

3. **`kubectl uncordon <node_name>`:**
   - Marks the node as schedulable again.
   - New pods can be scheduled on the node.
   - Previously evicted pods do not automatically return.

**Maintenance Considerations:**
- Ensure the cluster has sufficient spare capacity
- Set up PodDisruptionBudgets for critical workloads
- Perform maintenance on one node at a time
- Adjust auto-scaling settings during maintenance periods
- Verify workload status before and after maintenance
- Use rolling update strategies
</details>

3. Explain how to monitor and manage resource usage in a Kubernetes cluster. List the tools and techniques that should be included.

<details>
<summary>Show Answer</summary>

**Answer:**

**Kubernetes Resource Monitoring and Management Methods:**

**1. Basic Monitoring Tools:**

- **Metrics Server:**
  - Provides basic CPU and memory usage metrics
  - Supports `kubectl top` commands
  - Installation example for Kubernetes 1.34+ (verify requirements and existing installation first):
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml
    ```
  - Usage examples:
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Headlamp (Kubernetes Dashboard is archived):**
  - Visual representation of cluster status and resource usage
  - Provides resource management interface for pods, nodes, namespaces, etc.

**2. Advanced Monitoring Stack:**

- **Prometheus + Grafana:**
  - Prometheus: Metric collection and storage
  - Grafana: Metric visualization and dashboards
  - Can be installed via kube-prometheus-stack or Prometheus Operator
  - Supports custom alerting rules and dashboards

- **ELK/EFK Stack:**
  - Elasticsearch: Log storage and search
  - Logstash/Fluentd: Log collection and processing
  - Kibana: Log visualization and analysis

**3. Resource Management Techniques:**

- **Setting resource requests and limits:**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **Namespace-level resource quotas (ResourceQuota):**
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

- **Default resource limits (LimitRange):**
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
  - Automatically adjusts CPU and memory requests for pods
  - Provides recommendations based on resource usage patterns

- **Cluster Autoscaler:**
  - Automatically adjusts the number of cluster nodes based on workload requirements
  - Adds nodes when resources are insufficient, removes nodes when utilization is low

**4. Monitoring Best Practices:**

- Set resource requests and limits for all pods
- Configure alerts for critical metrics
- Plan resources based on historical usage analysis
- Perform regular resource audits
- Analyze resource usage trends for cost optimization
- Set appropriate resource quotas for development, staging, and production environments
- Monitor both node-level and pod-level metrics
</details>

4. Explain the major risks that can occur during a Kubernetes cluster upgrade and strategies to mitigate them.

<details>
<summary>Show Answer</summary>

**Answer:**

**Kubernetes Cluster Upgrade Risks and Mitigation Strategies:**

**1. Major Risks:**

- **API Compatibility Issues:**
  - APIs may change or be removed in new versions
  - Some Custom Resource Definitions (CRDs) or API versions may no longer be supported

- **Workload Disruption:**
  - Temporary API server unavailability due to control plane component restarts
  - Service disruption due to pod rescheduling during node upgrades

- **Feature Changes:**
  - Default behaviors may change, affecting existing workloads
  - Permission issues due to security policy changes

- **Performance Issues:**
  - Resource requirements may increase in new versions
  - Potential performance degradation during initial stabilization period

- **Rollback Complexity:**
  - Some upgrades cannot be easily rolled back
  - Rollback limitations due to data format changes

**2. Mitigation Strategies:**

- **Thorough Planning and Preparation:**
  - **Review changelog:** Check for changes, removed features, and known issues in the new version
  - **Verify upgrade path:** Confirm direct upgrade is supported from current to target version
  - **Review resource requirements:** Check minimum requirements for the new version

- **Test in Test Environment First:**
  - Perform upgrade in a test cluster similar to production
  - Test all critical workloads and custom resources
  - Run automated test suites

- **Verify API Compatibility:**
  - List API versions currently served (not an inventory of client usage):
    ```bash
    kubectl api-resources -o wide
    ```
  - Inspect observed deprecated API requests when /metrics access is permitted; also audit manifests and request logs:
    ```bash
    kubectl get --raw /metrics | grep '^apiserver_requested_deprecated_apis'
    ```
  - Update manifests as needed

- **Backup and Recovery Plan:**
  - Backup etcd database:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
      --endpoints=https://127.0.0.1:2379 \
      --cacert=/etc/kubernetes/pki/etcd/ca.crt \
      --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
      --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
    ```
  - Export a subset of workload objects (not a complete backup; secure the output):
    ```bash
    umask 077
    kubectl get all --all-namespaces -o yaml > workload-subset.yaml
    ```
  - Document and test recovery procedures

- **Gradual Upgrade Approach:**
  - **Upgrade control plane components first:**
    - In HA setups, upgrade one control plane node at a time
  - **Rolling upgrade of worker nodes:**
    - Divide node groups into small batches for upgrade
    - Verify stability after each batch

- **Workload Protection:**
  - **Set up PodDisruptionBudget:**
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
  - **Be careful when draining nodes:**
    ```bash
    kubectl drain <node_name> --ignore-daemonsets
    ```

- **Enhanced Monitoring:**
  - Monitor cluster status before, during, and after upgrade
  - Focus on key metrics and logs
  - Temporarily adjust alert thresholds

- **Rollback Plan:**
  - Define rollback trigger conditions
  - Document rollback procedures
  - Preserve all components and images needed for rollback

- **Communication Plan:**
  - Notify all stakeholders of upgrade schedule and expected impact
  - Provide status updates during upgrade
  - Define escalation paths for issues

**3. Version-Specific Considerations:**

- **Minor Version Upgrades (e.g., 1.24 → 1.25):**
  - Pay special attention to removed APIs and feature changes
  - Upgrade one minor version at a time

- **Patch Version Upgrades (e.g., 1.24.0 → 1.24.1):**
  - Generally safer but still requires testing
  - Consider faster deployment for security patches
</details>

5. Explain common networking issues that can occur in a Kubernetes cluster and how to diagnose and resolve them.

<details>
<summary>Show Answer</summary>

**Answer:**

**Kubernetes Networking Issue Diagnosis and Resolution:**

**1. Pod-to-Pod Communication Issues:**

- **Symptoms:**
  - Pods cannot communicate with other pods
  - Cannot connect by service name
  - Network timeout errors

- **Diagnosis Methods:**
  - Check network policies:
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - Create test pod for connectivity testing:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    ping <target_pod_IP>
    wget -O- <service_name>:<port>
    ```
  - Check CNI plugin pod status:
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **Resolution Methods:**
  - Reinstall or update CNI plugin
  - Modify or remove network policies
  - Check node network interfaces
  - Check firewall rules

**2. Service Discovery and DNS Issues:**

- **Symptoms:**
  - Cannot connect by service name
  - DNS lookup failures
  - Intermittent connection issues

- **Diagnosis Methods:**
  - Check CoreDNS pod status:
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - Test DNS lookup:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    nslookup kubernetes.default.svc.cluster.local
    nslookup <service_name>.<namespace>.svc.cluster.local
    cat /etc/resolv.conf
    ```
  - Check service endpoints:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Resolution Methods:**
  - Restart CoreDNS pods:
    ```bash
    kubectl rollout restart deployment coredns -n kube-system
    ```
  - Check and modify DNS configuration:
    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
  - Check kubelet DNS settings

**3. Service and Ingress Issues:**

- **Symptoms:**
  - Cannot access service from external sources
  - Ingress rules not working
  - Load balancer not being created

- **Diagnosis Methods:**
  - Check service status:
    ```bash
    kubectl describe service <service_name>
    ```
  - Check ingress status:
    ```bash
    kubectl describe ingress <ingress_name>
    ```
  - Check ingress controller pod logs:
    ```bash
    kubectl logs -n <ingress_namespace> <ingress_controller_pod>
    ```
  - Check endpoints:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Resolution Methods:**
  - Verify service selector matches pod labels
  - Reinstall or update ingress controller
  - Check service type and port configuration
  - Check cloud provider load balancer settings

**4. Node Networking Issues:**

- **Symptoms:**
  - Node disconnected from cluster
  - Node-to-node communication failure
  - kubelet connection errors

- **Diagnosis Methods:**
  - Check node status:
    ```bash
    kubectl describe node <node_name>
    ```
  - Check node network interfaces:
    ```bash
    # Directly on the node
    ip addr
    ip route
    ```
  - Check firewall rules:
    ```bash
    # Directly on the node
    iptables -L
    ```
  - Check kubelet logs:
    ```bash
    journalctl -u kubelet
    ```

- **Resolution Methods:**
  - Reconfigure node network interfaces
  - Modify firewall rules
  - Restart kubelet
  - Reboot node if necessary

**5. Network Policy Issues:**

- **Symptoms:**
  - Unexpected connection blocking
  - Cannot communicate between specific namespaces
  - Only some pods are accessible

- **Diagnosis Methods:**
  - Check network policies:
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - Check pod labels:
    ```bash
    kubectl get pods --show-labels
    ```
  - Verify network plugin supports network policies

- **Resolution Methods:**
  - Modify or delete network policies
  - Modify pod labels
  - Use network policy debugging tools

**6. Common Networking Debugging Tools:**

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

**7. Best Practices:**

- Document network topology
- Perform regular connectivity tests
- Analyze impact before network policy changes
- Plan cluster network CIDR ranges
- Implement network monitoring tools
</details>
## Hands-on Questions

1. Write a ResourceQuota manifest that meets the following requirements:
   - Namespace: development
   - Maximum pods: 20
   - Maximum CPU requests: 4 cores
   - Maximum memory requests: 8Gi
   - Maximum PVCs: 10
   - Maximum storage requests: 100Gi

<details>
<summary>Show Answer</summary>

**Answer:**

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

This ResourceQuota sets the following limits on the 'development' namespace:
- Maximum 20 pods
- Total CPU requests of 4 cores
- Total memory requests of 8Gi
- Maximum 10 PersistentVolumeClaims
- Total storage requests of 100Gi

To apply the ResourceQuota:
```bash
kubectl apply -f resource-quota.yaml
```

To check current quota usage:
```bash
kubectl describe quota dev-quota -n development
```

Note: The namespace must already exist before applying the ResourceQuota. If the namespace doesn't exist, create it first:
```bash
kubectl create namespace development
```
</details>

2. Write a kubelet check for a self-managed Linux cluster with SSH aliases for each node, and support an explicit repair mode.

<details>
<summary>Show Answer</summary>

**Answer:**

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

This script performs the following tasks:
1. Uses `kubectl get nodes` to get a list of all nodes in the cluster.
2. For each node:
   - Checks service state and verifies Ready after a requested repair.
   - Connects to the node via SSH to check kubelet service status.
   - Reports inactive services; starts them only when REPAIR_KUBELET=1 and the service query succeeded.
   - Checks the status again after starting the service.
   - Checks logs if startup fails.
   - Separates SSH/sudo/query failures from an inactive service and checks node readiness after repair.

**Usage:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
# After diagnosing the inactive service and approving repair:
REPAIR_KUBELET=1 ./check_kubelet.sh
```

**Notes:**
- SSH access to all nodes is required to run this script.
- SSH key-based authentication is recommended for production environments.
- In cloud environments, direct SSH access to nodes may be restricted, so you may need to use the cloud provider's node management tools.
</details>

3. Set up a cron job that backs up the cluster's etcd database and stores the backup file in a safe location.

<details>
<summary>Show Answer</summary>

**Answer:**

**1. Create backup script:**

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

**2. Grant execute permission to the script:**

```bash
chmod +x /opt/etcd-backup/backup_etcd.sh
```

**3. Set up cron job:**

```bash
# Edit root user's crontab
sudo crontab -e
```

Add the following content:

```
# Run etcd backup daily at 2 AM
0 2 * * * /opt/etcd-backup/backup_etcd.sh >> /var/log/etcd-backup.log 2>&1
```

**4. Set up backup log rotation:**

Create `/etc/logrotate.d/etcd-backup` file:

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

**5. Test backup:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. Backup monitoring:**

The script's EXIT trap publishes numeric `etcd_backup_success` and `etcd_backup_last_attempt_timestamp_seconds` metrics if METRICS_DIR exists. Configure node-exporter's textfile collector to read that directory, grant the writer permissions, and alert on failure or stale attempts. Do not append a later `$?` check after echo/copy commands. The external mount must already exist; validation or copy failure stops retention.

**Notes:**
- Backup files should be stored in a safe location outside the cluster.
- In cloud environments, using object storage like S3 or GCS is recommended.
- Regularly perform backup restoration tests to verify backup validity.
- For HA etcd clusters, backup only needs to be performed on one etcd instance.
</details>
4. Write a bounded maintenance procedure for explicitly selected self-managed Linux worker nodes, preserving disruption budgets and stopping when health checks fail.

<details>
<summary>Show Answer</summary>

**Answer:**

**Node Rolling Update Procedure:**

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

This example requires kubectl, jq, SSH aliases for the selected nodes, passwordless authorized sudo, and a reviewed maintenance command. It checks the Debian/Ubuntu reboot-required marker; adapt this to the operating system. Set WORKLOAD_HEALTHCHECK to a command that actually verifies critical applications, and pass only the reviewed worker list. For example:

```bash
MAINTENANCE_COMMAND='sudo -n /usr/local/sbin/approved-node-maintenance' \
WORKLOAD_HEALTHCHECK='kubectl -n app rollout status deployment/frontend --timeout=5m' \
./node_rolling_update.sh worker-1 worker-2
```

The command/script and application names must exist and match your plan. It does not use force or authorize emptyDir loss. It halts on failed drain/maintenance, waits for a changed boot ID after reboot and a fresh kubelet lease, and leaves failed nodes cordoned. PDBs and these checks reduce planned disruption; they cannot guarantee availability during unrelated failures. Use provider-managed updates for EKS managed/Auto Mode nodes and the separate kubeadm control-plane procedure for control-plane nodes.

**Pre-Rolling Update Preparation:**

1. **Set up PodDisruptionBudget:**
   Set up PDBs for critical workloads to ensure availability.

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

2. **Ensure Sufficient Resources:**
   Verify that remaining nodes can handle all workloads when one node is removed.

3. **Perform Backup:**
   Perform etcd database backup before updates.

**Rolling Update Best Practices:**

1. **Gradual Approach:**
   - Update only one node at a time
   - Verify cluster status after each node update

2. **Automation and Idempotency:**
   - Automate the process using scripts
   - Design for safe retries on failure

3. **Enhanced Monitoring:**
   - Monitor cluster metrics during updates
   - Monitor application status and performance

4. **Rollback Plan:**
   - Prepare rollback procedures for issues
   - Have methods to restore to previous state

5. **Communication:**
   - Announce update schedule and expected impact
   - Report update progress regularly

**Notes:**
- In cloud environments, you can leverage managed Kubernetes services' (EKS, GKE, AKS, etc.) node update features.
- If there are multiple node groups, perform updates by group.
- Specially monitor the status of critical system pods (CoreDNS, kube-proxy, etc.).
</details>

5. Write a script that identifies pods with high resource usage in the cluster and generates a report with that information.

<details>
<summary>Show Answer</summary>

**Answer:**

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

**Script Usage:**
```bash
python3 resource_usage_report.py
```

**Script Features:**
1. Collect cluster information
2. Collect node resource usage
3. Identify top pods by CPU and memory usage
4. Calculate resource usage by namespace
5. Identify pods with high usage relative to requests
6. Identify pods without resource requests
7. Generate reports in text and HTML formats

**Notes:**
- This script requires Python 3 and kubectl with read access to the Pods and metrics APIs. It discovers the served metrics version, aggregates multi-container usage by namespace, handles quantity units, and HTML-escapes output.
- Metrics Server must be installed in the cluster.
- Script execution time may be longer on large clusters.
- Can be set up as a cron job for regular report generation.
- Reports can be sent via email or integrated with monitoring systems.
</details>
## Advanced Topics

1. Which two sets contain real etcd settings or operational practices? (Select two.)
   - A) `--max-request-bytes`, `--quota-backend-bytes`, regular compaction
   - B) `--max-concurrent-requests`, `--max-connections`, disk RAID configuration
   - C) `--auto-compaction-retention`, `--snapshot-count`, SSD storage
   - D) `--max-txn-ops`, `--max-result-buffer`, memory expansion

<details>
<summary>Show Answer</summary>

**Answer: A and C**

**Explanation:**
etcd is the core data store for Kubernetes clusters, and its performance directly impacts overall cluster performance. Key configuration parameters and best practices for optimizing etcd performance are as follows:

1. **`--auto-compaction-retention`**: etcd is an append-only store that keeps a history of all changes. This parameter sets the interval for automatically compacting previous versions of keys. The default is 0 (disabled), but in production environments it's typically set to 1 hour (1h) or 24 hours (24h). This helps save disk space and improve performance.

2. **`--snapshot-count`**: Specifies the number of transactions to commit before etcd creates a snapshot. This governs internal Raft snapshots, not portable backup snapshots. Defaults are version-specific (the v3.6 reference lists 10,000); check the installed version and measure before tuning.

3. **SSD storage**: etcd is sensitive to disk I/O, so using SSDs (Solid State Drives) significantly improves performance. SSD usage is essential in large clusters.

Other important optimization settings and best practices:

- **Use dedicated disks**: Use dedicated disks for etcd data to prevent I/O contention with other applications.
- **Proper memory allocation**: etcd caches data in memory for performance, so sufficient memory must be allocated.
- **Optimize cluster size**: Typically 3-5 etcd members provide optimal performance and availability.
- **Minimize network latency**: Balance inter-member latency with fault isolation; placing every member in one zone loses quorum under that zone failure.
- **Regular backup and compaction**: Perform regular backups and compaction to ensure data safety and efficient disk space usage.

`--max-request-bytes`, `--quota-backend-bytes`, and `--max-txn-ops` are real settings. Option D also contains the unsupported `--max-result-buffer`; configuration limits, retention and internal snapshots should not be mistaken for a backup strategy.
</details>

2. What is the most effective way to implement control plane high availability (HA) in a Kubernetes cluster?
   - A) Running multiple API server instances on a single master node
   - B) Configuring an etcd cluster with multiple master nodes and a load balancer
   - C) Deploying the API server as a StatefulSet with PersistentVolume
   - D) Implementing a watchdog process with auto-recovery on the master node

<details>
<summary>Show Answer</summary>

**Answer: B) Configuring an etcd cluster with multiple master nodes and a load balancer**

**Explanation:**
The most effective way to implement Kubernetes control plane high availability (HA) is to configure an etcd cluster with multiple master nodes and a load balancer. This approach consists of the following components:

1. **Multiple master nodes**: Typically deploy 3 or 5 master nodes across different availability zones to eliminate single points of failure. Each master node runs the following control plane components:
   - kube-apiserver: Server that handles API requests
   - kube-controller-manager: Runs controller processes
   - kube-scheduler: Pod scheduling decisions

2. **etcd cluster**: etcd is a distributed key-value store that stores all Kubernetes cluster data. For high availability, typically run 3 or 5 etcd instances. etcd can run directly on master nodes or on dedicated nodes.

3. **Load balancer**: A load balancer is needed to distribute client requests across multiple kube-apiserver instances. This is typically implemented using cloud provider load balancer services or software load balancers like HAProxy or Nginx.

Key benefits of this configuration:
- **Fault tolerance**: The cluster continues to operate even if one master node fails.
- **High availability**: Deploying across multiple availability zones can handle even data center-level failures.
- **Scalability**: API server requests can be distributed and processed across multiple instances.
- **Data consistency**: etcd's Raft consensus algorithm ensures data consistency.

Problems with other options:
- Running multiple API server instances on a single master node makes the node itself a single point of failure.
- Deploying the API server as a StatefulSet is not a common approach, and control plane components are typically managed outside of Kubernetes.
- A watchdog process can be helpful but is not a true high availability solution by itself.
</details>

3. Which mechanism selects the events and detail levels recorded by Kubernetes audit logging?
   - A) Recording all request and response bodies without filtering
   - B) Using an audit policy to select events and levels
   - C) Real-time streaming of audit logs to an external SIEM system
   - D) Restricting access to audit logs to administrators only

<details>
<summary>Show Answer</summary>

**Answer: B) Using an audit policy to select events and levels**

**Explanation:**
Audit policies select events and detail levels. A metadata catch-all can retain a broad audit trail while sensitive payloads remain excluded; retention, access control, and delivery are also important. This is important for the following reasons:

1. **Minimize performance impact**: Logging all API requests can place significant load on the API server and degrade performance. Choose levels according to the required audit trail and measured overhead; logging metadata for all requests is a supported baseline.

2. **Storage efficiency**: Logging all events causes log data to grow rapidly, increasing storage costs and making log analysis difficult.

3. **Focus on relevant information**: By logging only important events, security analysts can focus on critical information.

4. **Compliance**: Align event coverage, retention, and access controls with the requirements applicable to the system.

Kubernetes audit policies support the following audit levels:

- **None**: Does not log the event.
- **Metadata**: Logs only request metadata (user, timestamp, resource, action, etc.) and excludes request/response body.
- **Request**: Logs metadata and request body but excludes response body.
- **RequestResponse**: Logs metadata, request body, and response body.

Example of an effective audit policy:
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

Problems with other options:
- Logging all API requests can cause performance and storage issues.
- Real-time streaming to external SIEM systems is important but lower priority than deciding what to log.
- Restricting access to audit logs is important but is a security measure rather than the logging policy itself.
</details>

4. Which pattern combines a dedicated node-problem detector with custom remediation logic for a self-managed environment?
   - A) Deploy a DaemonSet that monitors node status and automatically reboots problematic nodes
   - B) Utilize cloud provider's managed node groups and auto-repair features
   - C) Use Node Problem Detector and custom controllers for node status monitoring and recovery
   - D) Implement a cron job that periodically checks node status and recreates problematic nodes

<details>
<summary>Show Answer</summary>

**Answer: C) Use Node Problem Detector and custom controllers for node status monitoring and recovery**

**Explanation:**
Node Problem Detector plus custom remediation is one extensible design. It is not universally best: supported provider-managed repair, including EKS node repair, can reduce operational work. This approach provides the following benefits:

1. **Accurate problem detection**: Node Problem Detector (NPD) is a special-purpose tool that can detect various node problems, including:
   - Kernel errors and crashes
   - Hardware issues
   - File system issues
   - Network issues
   - Resource shortage issues

2. **Flexible response**: Custom controllers allow implementing various recovery strategies for detected problems:
   - Minor problems: Node reboot
   - Serious problems: Node replacement
   - Specific types of problems: Specific service restart

3. **Kubernetes native integration**: NPD reports node status as NodeConditions, integrating well with existing Kubernetes mechanisms.

4. **Cloud independent**: Detection and repair must match the OS/runtime/provider; node loss also requires an external signal/controller when an on-node agent cannot report.

Implementation steps:

1. **Deploy Node Problem Detector**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **Implement custom controller**:
   - Watch Kubernetes events and node status changes
   - Implement logic to respond to specific NodeConditions
   - Perform recovery actions (command execution via SSH, node recreation via cloud API, etc.)

3. **Set up alerts and logging**:
   - Configure alerts for recovery actions
   - Log problems and recovery actions

Problems with other options:

- **DaemonSet approach**: If the node has serious problems, the DaemonSet itself can be affected, and it's difficult to detect all types of problems.

- **Cloud provider's managed node groups**: Tied to specific cloud providers and cannot be used in on-premises environments. The types of problems that can be detected may also be limited.

- **Cron job approach**: Slow reaction time, limited problem detection capability, and must run outside the cluster.

Combining Node Problem Detector with custom controllers allows implementing a powerful and flexible node auto-repair solution that works across various environments.
</details>

5. What are the best practices for effectively managing RBAC (Role-Based Access Control) in a Kubernetes cluster?
   - A) Grant cluster-admin role to all users for ease of management
   - B) Define granular roles by namespace and apply the principle of least privilege
   - C) Consolidate all permissions into a single ClusterRole for consistency
   - D) Always use user certificates instead of service accounts for authentication

<details>
<summary>Show Answer</summary>

**Answer: B) Define granular roles by namespace and apply the principle of least privilege**

**Explanation:**
The best practice for effectively managing RBAC (Role-Based Access Control) in a Kubernetes cluster is to define granular roles by namespace and apply the principle of least privilege. This approach provides the following benefits:

1. **Principle of least privilege**: Grant only the minimum necessary permissions to users and service accounts to minimize security risk. This helps protect the cluster from unintended changes or malicious actions.

2. **Namespace isolation**: Defining roles by namespace strengthens logical isolation between teams or applications. This limits ordinary API actions; namespace boundaries also need workload admission and network controls.

3. **Granular access control**: Permissions can be finely controlled for specific resource types or actions. For example, developers can be granted permission to manage pods and services while restricting permissions to modify secrets or the namespace itself.

4. **Audit ease**: Using granular roles clearly documents who can perform what actions, making audits and compliance easier.

RBAC best practice implementation examples:

1. **Define roles by namespace**:
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

Pod/Deployment creation can indirectly expose Secrets and ServiceAccount privileges in the namespace. Removing direct Secret reads is useful but does not alone restrict which credentials workloads may mount; use appropriate admission controls.

2. **Create role binding**:
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

3. **Use cluster-level roles sparingly**:
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

4. **Granular permissions for service accounts**:
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

Problems with other options:

- **Granting cluster-admin role to all users**: This poses serious security risks. All users would have complete access to all resources in the cluster, making it vulnerable to unintended changes or malicious actions.

- **Consolidating all permissions into a single ClusterRole**: An all-powerful shared role risks overgranting; a narrowly scoped reusable ClusterRole with namespaced RoleBindings can be appropriate.

- **Always using user certificates**: Service accounts are suitable for application authentication, and using user certificates in all situations increases management burden. It's important to choose the appropriate authentication mechanism based on the situation.
</details>
