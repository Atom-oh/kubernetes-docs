# Linux Operations Skills

> **Supported Versions**: Bash on maintained Linux distributions; commands assume the named tools are installed **Last Updated**: September 11, 2026

This document covers essential Linux operations skills for working effectively in Kubernetes environments.

***

## Table of Contents

1. [Environment Variables and Shell Configuration](02-linux-advanced.md#1-environment-variables-and-shell-configuration)
2. [Shell Scripting Basics](02-linux-advanced.md#2-shell-scripting-basics)
3. [Text Processing Tools](02-linux-advanced.md#3-text-processing-tools)
4. [SSH and Remote Access](02-linux-advanced.md#4-ssh-and-remote-access)
5. [Performance Monitoring and Troubleshooting](02-linux-advanced.md#5-performance-monitoring-and-troubleshooting)
6. [Storage Management Basics](02-linux-advanced.md#6-storage-management-basics)
7. [curl and API Calls](02-linux-advanced.md#7-curl-and-api-calls)
8. [Practical One-Liners Collection](02-linux-advanced.md#8-practical-one-liners-collection)

***

<span id="1-environment-variables-and-shell-configuration"></span>

## 1. Environment Variables and Shell Configuration

Environment variables are the core mechanism for managing configuration in Linux and Kubernetes.

### 1.1 Environment Variable Basics

```bash
env
echo "$HOME"
echo "$PATH"
printenv HOME
```

### 1.2 The export Command

```bash
export MY_VAR="hello"
export DATABASE_URL="postgresql://localhost:5432/mydb"
export KUBECONFIG="/home/user/.kube/config"
```

### 1.3 The source Command

```bash
cat > ~/my-env.sh << 'SCRIPT'
export APP_ENV="production"
export APP_PORT="8080"
alias k='kubectl'
SCRIPT

source ~/my-env.sh
```

### 1.4 .bashrc and .bash\_profile

Interactive non-login Bash reads .bashrc; login Bash reads the first available .bash_profile/.bash_login/.profile. A login profile may explicitly source .bashrc. Add the block below once.

```bash
cat >> ~/.bashrc << 'SCRIPT'
export KUBECONFIG=~/.kube/config
command -v kubectl >/dev/null && source <(kubectl completion bash)
alias k='kubectl'
SCRIPT

source ~/.bashrc
```

### 1.5 Kubernetes ConfigMap Connection

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

## 2. Shell Scripting Basics

### 2.1 Variables

```bash
#!/bin/bash
NAME="kubernetes"
NAMESPACE=${1:-default}
: "${REQUIRED_VAR:?REQUIRED_VAR must be set}"
```

### 2.2 Conditionals

```bash
if [ "$ENV" = "production" ]; then
    echo "Production mode"
fi

case "$1" in
    start) echo "Starting..." ;;
    stop) echo "Stopping..." ;;
esac
```

### 2.3 Loops

```bash
for ns in default kube-system monitoring; do
    kubectl get pods -n "$ns"
done

# Running phase does not imply readiness. A bounded wait propagates API errors/timeouts.
kubectl wait --for=condition=Ready pod/mypod --timeout=120s
```

### 2.4 Functions

```bash
check_pod_exists() {
    local pod_name=${1:?Pod name required}
    local namespace=${2:-default}
    # Nonzero also includes authorization/connection errors; inspect stderr.
    kubectl get pod "$pod_name" -n "$namespace" -o name >/dev/null
}
```

### 2.5 Init Container Patterns

This bounded-loop example waits for DNS discovery. DNS success does not imply database readiness; the application needs connection retries or a database-specific readiness check. Prepare the mysql Service and custom myapp image. Kubelet can restart a failed init container, so this is distinct from a total Pod startup deadline.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: wait-for-db-dns
    image: busybox:1.37.0
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

## 3. Text Processing Tools

### 3.1 grep with kubectl

```bash
kubectl get pods --field-selector=status.phase!=Running
kubectl logs nginx-pod | grep -i error
```

### 3.2 awk Field Extraction

```bash
kubectl get pods | awk 'NR>1 {print $1}'
kubectl get pods --no-headers | awk '$3 != "Running" {print $1, $3}'
```

### 3.3 sed Editing

```bash
# Text-only preview; this can match more than the intended YAML field.
sed 's/replicas: [0-9]*/replicas: 5/' deployment.yaml
# For a structured edit, use the yq example below.
```

### 3.4 JSON Parsing with jq

```bash
kubectl get pod nginx -o json | jq '.metadata.name'
kubectl get pods -o json | jq -r '.items[].metadata.name'
```

### 3.5 YAML Parsing with yq

These examples use Mike Farah yq v4; Python yq has different options.

```bash
yq '.metadata.name' deployment.yaml
yq -i '.spec.replicas = 5' deployment.yaml
```

***

<span id="4-ssh-and-remote-access"></span>

## 4. SSH and Remote Access

### 4.1 SSH Key Generation

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 4.2 SSH Tunneling

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8080:localhost:80 user@server
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:6443:kubernetes-api:6443 user@bastion
```

For API tunnels, retain the original CA and TLS server name in kubeconfig. When connecting to 127.0.0.1, set tls-server-name to the actual API certificate name; keep TLS verification enabled.

### 4.3 Bastion Host Usage

```bash
ssh -J bastion user@internal-server
```

### 4.4 rsync

```bash
rsync -avzP ./local/ user@remote:/path/
```

***

<span id="5-performance-monitoring-and-troubleshooting"></span>

## 5. Performance Monitoring and Troubleshooting

### 5.1 top and htop

```bash
top -b -n 1 | head -20
```

### 5.2 vmstat and iostat

```bash
vmstat 1 5
iostat -dx 1 5
```

### 5.3 free and df

```bash
free -h
df -h
```

### 5.4 kubectl top

Requires a metrics.k8s.io provider such as Metrics Server; kubectl top is not a historical monitoring store.

```bash
kubectl top nodes
kubectl top pods --sort-by=memory
```

***

<span id="6-storage-management-basics"></span>

## 6. Storage Management Basics

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

The path and hostname below must match the node where the existing filesystem is mounted.

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

Local storage cannot move to another node after a node failure. This StorageClass does not provision disks; the PVC may remain Pending until a consumer Pod is scheduled. Match PV capacity to the real filesystem: the advertised value is not a directory quota. Retain cleanup/reuse is a separate operator action.

<span id="7-curl-and-api-calls"></span>

## 7. curl and API Calls

### 7.1 HTTP Methods

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"John"}' https://api.example.com/users
```

### 7.2 Kubernetes API Calls

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

The ServiceAccount needs pods list RBAC permission in that namespace. These files may be absent with automountServiceAccountToken: false. Projected tokens rotate, so long-lived clients must reread the file; do not log tokens.

### 7.3 Useful curl Options

```bash
curl --silent --show-error -o /dev/null -w "%{http_code}\n" https://api.example.com/health
```

***

<span id="8-practical-one-liners-collection"></span>

## 8. Practical One-Liners Collection

### 8.1 Kubernetes Operations

```bash
kubectl get pods -A | awk '$4 != "Running" && NR>1 {print $1, $2, $4}'
kubectl get pods -A -o json | jq -r '.items[] | select(any((.status.containerStatuses // [])[]; .restartCount > 5)) | [.metadata.namespace, .metadata.name] | @tsv'
```

### 8.2 Log Analysis

```bash
kubectl logs deploy/app --since=1h | grep -i error
```

### 8.3 Network Debugging

```bash
nslookup kubernetes.default.svc.cluster.local
nc -zv service-name 80
```

***

## Conclusion

1. **Environment Variables**: Foundation for K8s ConfigMap/Secret
2. **Shell Scripting**: Essential for init containers, health checks
3. **Text Processing**: Core to kubectl output parsing
4. **SSH**: Important for node debugging
5. **Performance Monitoring**: Foundation of troubleshooting

***

[Previous: Linux Basics](01-linux-basics.md) | [Next: Container Basics](03-container-technology.md)

## Verification References

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
