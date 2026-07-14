# Inyección de Sidecar

La inyección de Sidecar es el mecanismo mediante el cual Istio inyecta automáticamente el proxy Envoy en los Pods de aplicaciones.

## Descripción general

Métodos de inyección de Sidecar:
- Inyección automática (Webhook)
- Inyección manual (istioctl)

## Configuración de inyección automática

### Nivel de Namespace

```bash
# Add Label to Namespace
kubectl label namespace default istio-injection=enabled

# Verify
kubectl get namespace default -L istio-injection
```

### Nivel de Pod

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

## Inyección manual

```bash
# Inject Sidecar into manifest
istioctl kube-inject -f deployment.yaml | kubectl apply -f -

# Or save to file
istioctl kube-inject -f deployment.yaml -o deployment-injected.yaml
kubectl apply -f deployment-injected.yaml
```

## Configuración de recursos de Sidecar

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

## Exclusión de la inyección

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

## Solución de problemas

```bash
# Check injection status
kubectl get namespace default -o yaml | grep istio-injection

# Check webhook
kubectl get mutatingwebhookconfigurations

# Check sidecar
kubectl get pods -n default -o jsonpath='{.items[*].spec.containers[*].name}'
```

## Referencias

- [Istio Sidecar Injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
