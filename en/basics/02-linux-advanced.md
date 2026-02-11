# Linux Operations Skills (For Kubernetes Practitioners)

> **Supported Versions**: All major Linux distributions
> **Last Updated**: February 2025

This document covers essential Linux operations skills for working effectively in Kubernetes environments.

---

## Table of Contents

1. [Environment Variables and Shell Configuration](#1-environment-variables-and-shell-configuration)
2. [Shell Scripting Basics](#2-shell-scripting-basics)
3. [Text Processing Tools](#3-text-processing-tools)
4. [SSH and Remote Access](#4-ssh-and-remote-access)
5. [Performance Monitoring and Troubleshooting](#5-performance-monitoring-and-troubleshooting)
6. [Storage Management Basics](#6-storage-management-basics)
7. [curl and API Calls](#7-curl-and-api-calls)
8. [Practical One-Liners Collection](#8-practical-one-liners-collection)

---

## 1. Environment Variables and Shell Configuration

Environment variables are the core mechanism for managing configuration in Linux and Kubernetes.

### 1.1 Environment Variable Basics

```bash
env
echo $HOME
echo $PATH
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

### 1.4 .bashrc and .bash_profile

```bash
cat >> ~/.bashrc << 'SCRIPT'
export KUBECONFIG=~/.kube/config
source <(kubectl completion bash)
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

---

## 2. Shell Scripting Basics

### 2.1 Variables

```bash
#!/bin/bash
NAME="kubernetes"
NAMESPACE=${1:-default}
: ${REQUIRED_VAR:?"REQUIRED_VAR must be set"}
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

while true; do
    STATUS=$(kubectl get pod mypod -o jsonpath='{.status.phase}')
    [ "$STATUS" = "Running" ] && break
    sleep 5
done
```

### 2.4 Functions

```bash
check_pod_exists() {
    local pod_name=$1
    kubectl get pod "$pod_name" &>/dev/null
}
```

### 2.5 Init Container Patterns

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

---

## 3. Text Processing Tools

### 3.1 grep with kubectl

```bash
kubectl get pods | grep -v "Running"
kubectl logs nginx-pod | grep -i error
```

### 3.2 awk Field Extraction

```bash
kubectl get pods | awk 'NR>1 {print $1}'
kubectl get pods | awk '$3 != "Running" {print $1, $3}'
```

### 3.3 sed Editing

```bash
sed -i 's/replicas: [0-9]*/replicas: 5/' deployment.yaml
```

### 3.4 JSON Parsing with jq

```bash
kubectl get pod nginx -o json | jq '.metadata.name'
kubectl get pods -o json | jq -r '.items[].metadata.name'
```

### 3.5 YAML Parsing with yq

```bash
yq '.metadata.name' deployment.yaml
yq -i '.spec.replicas = 5' deployment.yaml
```

---

## 4. SSH and Remote Access

### 4.1 SSH Key Generation

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 4.2 SSH Tunneling

```bash
ssh -L 8080:localhost:80 user@server
ssh -L 6443:kubernetes-api:6443 user@bastion
```

### 4.3 Bastion Host Usage

```bash
ssh -J bastion user@internal-server
```

### 4.4 rsync

```bash
rsync -avzP ./local/ user@remote:/path/
```

---

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

```bash
kubectl top nodes
kubectl top pods --sort-by=memory
```

---

## 6. Storage Management Basics

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

---

## 7. curl and API Calls

### 7.1 HTTP Methods

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"John"}' https://api.example.com/users
```

### 7.2 Kubernetes API Calls

```bash
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl -s --cacert $CACERT -H "Authorization: Bearer $TOKEN" \
  "https://kubernetes.default.svc/api/v1/namespaces/default/pods"
```

### 7.3 Useful curl Options

```bash
curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health
```

---

## 8. Practical One-Liners Collection

### 8.1 Kubernetes Operations

```bash
kubectl get pods -A | awk '$4 != "Running" && NR>1 {print $1, $2, $4}'
kubectl get pods -A -o json | jq -r '.items[] | select(.status.containerStatuses[]?.restartCount > 5) | .metadata.name'
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

---

## Conclusion

1. **Environment Variables**: Foundation for K8s ConfigMap/Secret
2. **Shell Scripting**: Essential for init containers, health checks
3. **Text Processing**: Core to kubectl output parsing
4. **SSH**: Important for node debugging
5. **Performance Monitoring**: Foundation of troubleshooting

---

[Previous: Linux Basics](01-linux-basics.md) | [Next: Container Basics](03-container-basics.md)
