# Cilium テストガイド

このドキュメントでは、Cilium の機能をテストおよび検証する方法を紹介します。Cilium バージョン 1.17 をベースとしており、Kubernetes バージョン 1.30 以降との互換性を検証します。

## 前提条件

- Kubernetes クラスター（1.30 以降）
- kubectl がインストールおよび設定済みであること
- Cilium CLI がインストール済みであること
- Helm 3.12 以降（任意）

## 1. Cilium のインストールと基本テスト

### 1.1 Cilium CLI のインストール

```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Verify version
cilium version
```

### 1.2 Cilium のインストール

```bash
# Basic installation
cilium install --version 1.17.0

# Or installation using Helm
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.17.0 \
  --namespace kube-system
```

### 1.3 インストール状態の確認

```bash
# Check Cilium status
cilium status

# Verify all Cilium components are running properly
kubectl get pods -n kube-system -l k8s-app=cilium
```

### 1.4 基本的な接続テスト

```bash
# Run Cilium connectivity test
cilium connectivity test
```

## 2. Network Policy テスト

### 2.1 テストアプリケーションのデプロイ

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

### 2.2 基本的な接続の確認

```bash
# Test connectivity from frontend to backend
FRONTEND_POD=$(kubectl -n cilium-test get pods -l app=frontend -o jsonpath='{.items[0].metadata.name}')
kubectl -n cilium-test exec $FRONTEND_POD -- curl -s backend
```

### 2.3 Network Policy の適用

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

### 2.4 Policy 適用後の接続テスト

```bash
# Test connectivity from frontend to backend (allowed)
FRONTEND_POD=$(kubectl -n cilium-test get pods -l app=frontend -o jsonpath='{.items[0].metadata.name}')
kubectl -n cilium-test exec $FRONTEND_POD -- curl -s backend

# Test connectivity from other Pod to backend (blocked)
kubectl -n cilium-test run test-pod --image=curlimages/curl --rm -it -- curl -s --connect-timeout 5 backend
```

## 3. Hubble 可視性テスト

### 3.1 Hubble の有効化

```bash
# Enable Hubble
cilium hubble enable

# Check status
cilium status
```

### 3.2 Hubble UI のインストール（任意）

```bash
# Install Hubble UI
cilium hubble enable --ui

# Set up port forwarding
cilium hubble ui
```

### 3.3 Hubble フローの監視

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

## 4. パフォーマンステスト

### 4.1 基本的なパフォーマンステスト

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

### 4.2 iperf3 パフォーマンステストの実行

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

## 5. 高度な機能のテスト

### 5.1 kube-proxy 置換モードのテスト

```bash
# Reinstall Cilium with kube-proxy replacement mode
cilium uninstall
cilium install --kube-proxy-replacement=strict

# Check status
cilium status

# Test service connectivity
cilium connectivity test
```

### 5.2 暗号化テスト

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

### 5.3 BGP テスト（高度）

```bash
# Install Cilium with BGP configuration
helm install cilium cilium/cilium --version 1.17.0 \
  --namespace kube-system \
  --set bgp.enabled=true \
  --set bgp.announce.loadbalancerIP=true

# Check BGP peering status
kubectl -n kube-system exec -ti ds/cilium -- cilium bgp peers
```

## 6. 互換性テスト

### 6.1 Kubernetes バージョンの互換性確認

```bash
# Check Kubernetes version
kubectl version --short

# Check Cilium version
cilium version
```

### 6.2 Kernel バージョンの互換性確認

```bash
# Check node kernel version
kubectl get nodes -o wide
kubectl debug node/<node-name> -it --image=ubuntu -- uname -r
```

### 6.3 CNI の互換性確認

```bash
# Check CNI configuration
kubectl -n kube-system exec -ti ds/cilium -- ls -la /etc/cni/net.d/
kubectl -n kube-system exec -ti ds/cilium -- cat /etc/cni/net.d/05-cilium.conf
```

## 7. トラブルシューティングテスト

### 7.1 Cilium 診断情報の収集

```bash
# Collect Cilium diagnostic information
cilium status --verbose
cilium clustermesh status
cilium hubble status

# Collect system information
cilium sysdump
```

### 7.2 ログ分析

```bash
# Check Cilium agent logs
kubectl -n kube-system logs -l k8s-app=cilium

# Check Cilium operator logs
kubectl -n kube-system logs -l name=cilium-operator

# Check Hubble relay logs
kubectl -n kube-system logs -l k8s-app=hubble-relay
```

### 7.3 接続トラブルシューティング

```bash
# Check specific endpoint information
kubectl -n kube-system exec -ti ds/cilium -- cilium endpoint list

# Get detailed endpoint information
ENDPOINT_ID=$(kubectl -n kube-system exec -ti ds/cilium -- cilium endpoint list | grep <pod-name> | awk '{print $1}')
kubectl -n kube-system exec -ti ds/cilium -- cilium endpoint get $ENDPOINT_ID

# Policy tracing
kubectl -n kube-system exec -ti ds/cilium -- cilium policy trace --src-k8s-pod=<namespace>:<pod-name> --dst-k8s-pod=<namespace>:<pod-name> -d TCP/<port>
```

## 8. クリーンアップ

```bash
# Delete test namespaces
kubectl delete namespace cilium-test
kubectl delete namespace perf-test

# Remove Cilium (if needed)
cilium uninstall
```

## 参照資料

- [Cilium 公式ドキュメント](https://docs.cilium.io/)
- [Cilium GitHub リポジトリ](https://github.com/cilium/cilium)
- [Hubble ドキュメント](https://github.com/cilium/hubble)
- [Cilium Network Policy の例](https://docs.cilium.io/en/stable/policy/language/)
