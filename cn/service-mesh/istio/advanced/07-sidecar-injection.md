# Sidecar 注入

Sidecar 注入是 Istio 自动将 Envoy proxy 注入应用 Pod 的机制。

## 概述

Sidecar 注入方法：
- 自动注入 (Webhook)
- 手动注入 (istioctl)

## 自动注入配置

### Namespace 层级

```bash
# Add Label to Namespace
kubectl label namespace default istio-injection=enabled

# Verify
kubectl get namespace default -L istio-injection
```

### Pod 层级

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

## 手动注入

```bash
# Inject Sidecar into manifest
istioctl kube-inject -f deployment.yaml | kubectl apply -f -

# Or save to file
istioctl kube-inject -f deployment.yaml -o deployment-injected.yaml
kubectl apply -f deployment-injected.yaml
```

## Sidecar 资源配置

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

## 排除注入

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

## 故障排除

```bash
# Check injection status
kubectl get namespace default -o yaml | grep istio-injection

# Check webhook
kubectl get mutatingwebhookconfigurations

# Check sidecar
kubectl get pods -n default -o jsonpath='{.items[*].spec.containers[*].name}'
```

## 参考资料

- [Istio Sidecar Injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
