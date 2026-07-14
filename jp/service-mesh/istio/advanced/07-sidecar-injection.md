# Sidecar Injection

Sidecar Injectionは、IstioがEnvoy proxyをアプリケーションPodに自動的に注入する仕組みです。

## 概要

Sidecar Injectionの方法:
- 自動注入（Webhook）
- 手動注入（istioctl）

## 自動注入の設定

### Namespaceレベル

```bash
# Add Label to Namespace
kubectl label namespace default istio-injection=enabled

# Verify
kubectl get namespace default -L istio-injection
```

### Podレベル

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  annotations:
    sidecar.istio.io/inject: "true"  # Inject only this pod
spec:
  containers:
  - name: myapp
    image: myapp:latest
```

## 手動注入

```bash
# Inject Sidecar into manifest
istioctl kube-inject -f deployment.yaml | kubectl apply -f -

# Or save to file
istioctl kube-inject -f deployment.yaml -o deployment-injected.yaml
kubectl apply -f deployment-injected.yaml
```

## Sidecarリソースの設定

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  annotations:
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
spec:
  containers:
  - name: myapp
    image: myapp:latest
```

## 注入からの除外

```yaml
# Exclude specific pod
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  annotations:
    sidecar.istio.io/inject: "false"
spec:
  containers:
  - name: myapp
    image: myapp:latest
```

## トラブルシューティング

```bash
# Check injection status
kubectl get namespace default -o yaml | grep istio-injection

# Check webhook
kubectl get mutatingwebhookconfigurations

# Check sidecar
kubectl get pods -n default -o jsonpath='{.items[*].spec.containers[*].name}'
```

## 参考資料

- [Istio Sidecar Injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
