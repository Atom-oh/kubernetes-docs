# Cilium Test Guide

This document provides methods to test and validate Cilium's features. It is written based on Cilium version 1.17 and verifies compatibility with Kubernetes version 1.30 and above.

## Prerequisites

- Kubernetes cluster (1.30 or above)
- kubectl installed and configured
- Cilium CLI installed
- Helm 3.12 or above (optional)

## 1. Cilium Installation and Basic Testing

### 1.1 Install Cilium CLI

```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Verify version
cilium version
```

### 1.2 Install Cilium

```bash
# Basic installation
cilium install --version 1.17.0

# Or installation using Helm
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.17.0 \
  --namespace kube-system
```

### 1.3 Check Installation Status

```bash
# Check Cilium status
cilium status

# Verify all Cilium components are running properly
kubectl get pods -n kube-system -l k8s-app=cilium
```

### 1.4 Basic Connectivity Test

```bash
# Run Cilium connectivity test
cilium connectivity test
```

## 2. Network Policy Testing

### 2.1 Deploy Test Application

```bash
# Create test namespace
kubectl create namespace cilium-test

# Deploy test application
kubectl -n cilium-test apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  selector:
    matchLabels:
      app: frontend
  replicas: 2
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  selector:
    matchLabels:
      app: backend
  replicas: 2
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  type: ClusterIP
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  type: ClusterIP
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 80
EOF

# Verify deployment
kubectl -n cilium-test get pods,svc
```

### 2.2 Verify Basic Connectivity

```bash
# Test connectivity from frontend to backend
FRONTEND_POD=$(kubectl -n cilium-test get pods -l app=frontend -o jsonpath='{.items[0].metadata.name}')
kubectl -n cilium-test exec $FRONTEND_POD -- curl -s backend
```

### 2.3 Apply Network Policy

```bash
# Apply Cilium network policy
kubectl -n cilium-test apply -f - <<EOF
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-to-backend"
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
EOF

# Verify policy
kubectl -n cilium-test get ciliumnetworkpolicies
```

### 2.4 Test Connectivity After Policy Application

```bash
# Test connectivity from frontend to backend (allowed)
FRONTEND_POD=$(kubectl -n cilium-test get pods -l app=frontend -o jsonpath='{.items[0].metadata.name}')
kubectl -n cilium-test exec $FRONTEND_POD -- curl -s backend

# Test connectivity from other Pod to backend (blocked)
kubectl -n cilium-test run test-pod --image=curlimages/curl --rm -it -- curl -s --connect-timeout 5 backend
```

## 3. Hubble Visibility Testing

### 3.1 Enable Hubble

```bash
# Enable Hubble
cilium hubble enable

# Check status
cilium status
```

### 3.2 Install Hubble UI (Optional)

```bash
# Install Hubble UI
cilium hubble enable --ui

# Set up port forwarding
cilium hubble ui
```

### 3.3 Observe Hubble Flows

```bash
# Install Hubble CLI
export HUBBLE_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/hubble/master/stable.txt)
curl -L --remote-name-all https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Set up Hubble connection
cilium hubble port-forward &

# Observe network flows
hubble observe --namespace cilium-test
```

## 4. Performance Testing

### 4.1 Basic Performance Test

```bash
# Create performance test namespace
kubectl create namespace perf-test

# Deploy performance test application
kubectl -n perf-test apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: perf-client
spec:
  selector:
    matchLabels:
      app: perf-client
  replicas: 1
  template:
    metadata:
      labels:
        app: perf-client
    spec:
      containers:
      - name: netperf
        image: networkstatic/iperf3
        command: ["sleep", "infinity"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: perf-server
spec:
  selector:
    matchLabels:
      app: perf-server
  replicas: 1
  template:
    metadata:
      labels:
        app: perf-server
    spec:
      containers:
      - name: netperf
        image: networkstatic/iperf3
        command: ["iperf3", "-s"]
        ports:
        - containerPort: 5201
---
apiVersion: v1
kind: Service
metadata:
  name: perf-server
spec:
  type: ClusterIP
  selector:
    app: perf-server
  ports:
  - port: 5201
    targetPort: 5201
EOF

# Verify deployment
kubectl -n perf-test get pods
```

### 4.2 Run iperf3 Performance Test

```bash
# Get client Pod name
CLIENT_POD=$(kubectl -n perf-test get pods -l app=perf-client -o jsonpath='{.items[0].metadata.name}')

# Get server service IP
SERVER_IP=$(kubectl -n perf-test get svc perf-server -o jsonpath='{.spec.clusterIP}')

# TCP performance test
kubectl -n perf-test exec $CLIENT_POD -- iperf3 -c $SERVER_IP -t 30

# UDP performance test
kubectl -n perf-test exec $CLIENT_POD -- iperf3 -c $SERVER_IP -u -b 1G -t 30
```

## 5. Advanced Feature Testing

### 5.1 kube-proxy Replacement Mode Test

```bash
# Reinstall Cilium with kube-proxy replacement mode
cilium uninstall
cilium install --kube-proxy-replacement=strict

# Check status
cilium status

# Test service connectivity
cilium connectivity test
```

### 5.2 Encryption Test

```bash
# Reinstall Cilium with IPsec encryption
cilium uninstall
cilium install --encryption=ipsec

# Or install with WireGuard encryption
cilium uninstall
cilium install --encryption=wireguard

# Check status
cilium status

# Check encryption status
kubectl -n kube-system exec -ti ds/cilium -- cilium encrypt status
```

### 5.3 BGP Test (Advanced)

```bash
# Install Cilium with BGP configuration
helm install cilium cilium/cilium --version 1.17.0 \
  --namespace kube-system \
  --set bgp.enabled=true \
  --set bgp.announce.loadbalancerIP=true

# Check BGP peering status
kubectl -n kube-system exec -ti ds/cilium -- cilium bgp peers
```

## 6. Compatibility Testing

### 6.1 Check Kubernetes Version Compatibility

```bash
# Check Kubernetes version
kubectl version --short

# Check Cilium version
cilium version
```

### 6.2 Check Kernel Version Compatibility

```bash
# Check node kernel version
kubectl get nodes -o wide
kubectl debug node/<node-name> -it --image=ubuntu -- uname -r
```

### 6.3 Check CNI Compatibility

```bash
# Check CNI configuration
kubectl -n kube-system exec -ti ds/cilium -- ls -la /etc/cni/net.d/
kubectl -n kube-system exec -ti ds/cilium -- cat /etc/cni/net.d/05-cilium.conf
```

## 7. Troubleshooting Tests

### 7.1 Collect Cilium Diagnostic Information

```bash
# Collect Cilium diagnostic information
cilium status --verbose
cilium clustermesh status
cilium hubble status

# Collect system information
cilium sysdump
```

### 7.2 Log Analysis

```bash
# Check Cilium agent logs
kubectl -n kube-system logs -l k8s-app=cilium

# Check Cilium operator logs
kubectl -n kube-system logs -l name=cilium-operator

# Check Hubble relay logs
kubectl -n kube-system logs -l k8s-app=hubble-relay
```

### 7.3 Connectivity Troubleshooting

```bash
# Check specific endpoint information
kubectl -n kube-system exec -ti ds/cilium -- cilium endpoint list

# Get detailed endpoint information
ENDPOINT_ID=$(kubectl -n kube-system exec -ti ds/cilium -- cilium endpoint list | grep <pod-name> | awk '{print $1}')
kubectl -n kube-system exec -ti ds/cilium -- cilium endpoint get $ENDPOINT_ID

# Policy tracing
kubectl -n kube-system exec -ti ds/cilium -- cilium policy trace --src-k8s-pod=<namespace>:<pod-name> --dst-k8s-pod=<namespace>:<pod-name> -d TCP/<port>
```

## 8. Cleanup

```bash
# Delete test namespaces
kubectl delete namespace cilium-test
kubectl delete namespace perf-test

# Remove Cilium (if needed)
cilium uninstall
```

## References

- [Cilium Official Documentation](https://docs.cilium.io/)
- [Cilium GitHub Repository](https://github.com/cilium/cilium)
- [Hubble Documentation](https://github.com/cilium/hubble)
- [Cilium Network Policy Examples](https://docs.cilium.io/en/stable/policy/language/)
