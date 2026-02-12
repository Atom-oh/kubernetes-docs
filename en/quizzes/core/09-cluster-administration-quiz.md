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
   ETCDCTL_API=3 etcdctl snapshot status snapshot.db --write-out=table
   ```

4. **Store backup file in a safe location:**
   - Storage outside the cluster
   - Cloud storage (S3, GCS, etc.)
   - Different physical location

**etcd Restore Procedure:**

1. **Stop all API servers for restoration:**
   ```bash
   sudo systemctl stop kube-apiserver
   ```

2. **Stop etcd service:**
   ```bash
   sudo systemctl stop etcd
   ```

3. **Backup data directory (optional):**
   ```bash
   sudo mv /var/lib/etcd /var/lib/etcd.bak
   ```

4. **Create new data directory from snapshot:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
     --data-dir=/var/lib/etcd-restore \
     --name=master \
     --initial-cluster=master=https://127.0.0.1:2380 \
     --initial-cluster-token=etcd-cluster-1 \
     --initial-advertise-peer-urls=https://127.0.0.1:2380
   ```

5. **Configure etcd to use the restored data directory:**
   ```bash
   sudo mv /var/lib/etcd-restore /var/lib/etcd
   sudo chown -R etcd:etcd /var/lib/etcd
   ```

6. **Restart etcd service:**
   ```bash
   sudo systemctl start etcd
   ```

7. **Verify etcd status:**
   ```bash
   ETCDCTL_API=3 etcdctl endpoint health \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

8. **Restart API server:**
   ```bash
   sudo systemctl start kube-apiserver
   ```

9. **Verify cluster status:**
   ```bash
   kubectl get nodes
   kubectl get pods --all-namespaces
   ```

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
   kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
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
   - Pods are rescheduled on other nodes.
   - DaemonSet pods are ignored by default (`--ignore-daemonsets` flag required).
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
  - Check API versions in use:
    ```bash
    kubectl api-resources -o wide
    ```
  - Check for deprecated API usage:
    ```bash
    kubectl get -A | grep "deprecated"
    ```
  - Update manifests as needed

- **Backup and Recovery Plan:**
  - Backup etcd database:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db
    ```
  - Backup all critical manifests:
    ```bash
    kubectl get all --all-namespaces -o yaml > all-resources.yaml
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
    kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
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

2. Write a script that checks the kubelet service status on all nodes in the cluster and resolves issues if found.

<details>
<summary>Show Answer</summary>

**Answer:**

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

This script performs the following tasks:
1. Uses `kubectl get nodes` to get a list of all nodes in the cluster.
2. For each node:
   - Checks the node's Ready status.
   - Connects to the node via SSH to check kubelet service status.
   - Starts the service if kubelet is not running.
   - Checks the status again after starting the service.
   - Checks logs if startup fails.
   - Checks key settings in the kubelet configuration file.

**Usage:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
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
    create 0644 root root
}
```

**5. Test backup:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. Set up backup monitoring (optional):**

To receive alerts on backup failure, you can integrate with monitoring tools like Prometheus. Add the following code to the backup script:

```bash
# Create file indicating backup success/failure
if [ $? -eq 0 ]; then
  echo "success" > /var/lib/node_exporter/etcd_backup_status.prom
else
  echo "failure" > /var/lib/node_exporter/etcd_backup_status.prom
fi
```

**Notes:**
- Backup files should be stored in a safe location outside the cluster.
- In cloud environments, using object storage like S3 or GCS is recommended.
- Regularly perform backup restoration tests to verify backup validity.
- For HA etcd clusters, backup only needs to be performed on one etcd instance.
</details>
4. Write a procedure for performing rolling updates on all nodes in the cluster. Workload availability must be maintained during updates.

<details>
<summary>Show Answer</summary>

**Answer:**

**Node Rolling Update Procedure:**

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

**Script Features:**
1. Collect cluster information
2. Collect node resource usage
3. Identify top pods by CPU and memory usage
4. Calculate resource usage by namespace
5. Identify pods with high usage relative to requests
6. Identify pods without resource requests
7. Generate reports in text and HTML formats

**Notes:**
- This script requires `kubectl`, `jq`, and `bc` tools.
- Metrics Server must be installed in the cluster.
- Script execution time may be longer on large clusters.
- Can be set up as a cron job for regular report generation.
- Reports can be sent via email or integrated with monitoring systems.
</details>
## Advanced Topics

1. What are the key configuration parameters and best practices for optimizing etcd performance in a Kubernetes cluster?
   - A) `--max-request-bytes`, `--quota-backend-bytes`, regular compaction
   - B) `--max-concurrent-requests`, `--max-connections`, disk RAID configuration
   - C) `--auto-compaction-retention`, `--snapshot-count`, SSD storage
   - D) `--max-txn-ops`, `--max-result-buffer`, memory expansion

<details>
<summary>Show Answer</summary>

**Answer: C) `--auto-compaction-retention`, `--snapshot-count`, SSD storage**

**Explanation:**
etcd is the core data store for Kubernetes clusters, and its performance directly impacts overall cluster performance. Key configuration parameters and best practices for optimizing etcd performance are as follows:

1. **`--auto-compaction-retention`**: etcd is an append-only store that keeps a history of all changes. This parameter sets the interval for automatically compacting previous versions of keys. The default is 0 (disabled), but in production environments it's typically set to 1 hour (1h) or 24 hours (24h). This helps save disk space and improve performance.

2. **`--snapshot-count`**: Specifies the number of transactions to commit before etcd creates a snapshot. The default is 100,000, but in large clusters this value can be adjusted to optimize snapshot creation frequency. Smaller values create snapshots more frequently, reducing recovery time but increasing disk I/O.

3. **SSD storage**: etcd is sensitive to disk I/O, so using SSDs (Solid State Drives) significantly improves performance. SSD usage is essential in large clusters.

Other important optimization settings and best practices:

- **Use dedicated disks**: Use dedicated disks for etcd data to prevent I/O contention with other applications.
- **Proper memory allocation**: etcd caches data in memory for performance, so sufficient memory must be allocated.
- **Optimize cluster size**: Typically 3-5 etcd members provide optimal performance and availability.
- **Minimize network latency**: Place etcd members in the same data center or availability zone to minimize network latency between members.
- **Regular backup and compaction**: Perform regular backups and compaction to ensure data safety and efficient disk space usage.

`--max-request-bytes` and `--quota-backend-bytes` are actual etcd parameters but are mainly related to resource limits rather than performance. `--max-concurrent-requests`, `--max-connections`, `--max-txn-ops`, and `--max-result-buffer` are either not actual etcd parameters or not primary factors in performance optimization.
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

3. What is the most important consideration when configuring audit logging in a Kubernetes cluster?
   - A) Logging all API requests to ensure complete audit trail
   - B) Using audit policies to selectively log only important events
   - C) Real-time streaming of audit logs to an external SIEM system
   - D) Restricting access to audit logs to administrators only

<details>
<summary>Show Answer</summary>

**Answer: B) Using audit policies to selectively log only important events**

**Explanation:**
The most important consideration when configuring Kubernetes audit logging is using audit policies to selectively log only important events. This is important for the following reasons:

1. **Minimize performance impact**: Logging all API requests can place significant load on the API server and degrade performance. Large clusters can have thousands of API requests per second.

2. **Storage efficiency**: Logging all events causes log data to grow rapidly, increasing storage costs and making log analysis difficult.

3. **Focus on relevant information**: By logging only important events, security analysts can focus on critical information.

4. **Compliance**: Many compliance requirements require logging specific types of events, not all events.

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

Problems with other options:
- Logging all API requests can cause performance and storage issues.
- Real-time streaming to external SIEM systems is important but lower priority than deciding what to log.
- Restricting access to audit logs is important but is a security measure rather than the logging policy itself.
</details>

4. What is the most effective way to implement node auto-repair in a Kubernetes cluster?
   - A) Deploy a DaemonSet that monitors node status and automatically reboots problematic nodes
   - B) Utilize cloud provider's managed node groups and auto-repair features
   - C) Use Node Problem Detector and custom controllers for node status monitoring and recovery
   - D) Implement a cron job that periodically checks node status and recreates problematic nodes

<details>
<summary>Show Answer</summary>

**Answer: C) Use Node Problem Detector and custom controllers for node status monitoring and recovery**

**Explanation:**
The most effective way to implement node auto-repair in a Kubernetes cluster is to use Node Problem Detector together with custom controllers. This approach provides the following benefits:

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

4. **Cloud independent**: This approach works in all environments (on-premises, various cloud providers).

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

2. **Namespace isolation**: Defining roles by namespace strengthens logical isolation between teams or applications. This prevents mistakes by one team from affecting another team's resources.

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
   - apiGroups: [""]
     resources: ["secrets"]
     verbs: ["get", "list", "watch"]  # Only allow reading secrets
   ```

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

- **Consolidating all permissions into a single ClusterRole**: This makes granular access control impossible and violates the principle of least privilege.

- **Always using user certificates**: Service accounts are suitable for application authentication, and using user certificates in all situations increases management burden. It's important to choose the appropriate authentication mechanism based on the situation.
</details>
