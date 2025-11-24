# Sidecar Injection

Sidecar Injection은 Istio가 애플리케이션 파드에 Envoy 프록시를 자동으로 주입하는 메커니즘입니다.

## 개요

Sidecar Injection 방식:
- 자동 주입 (Webhook)
- 수동 주입 (istioctl)

## 자동 주입 설정

### Namespace 레벨

```bash
# Namespace에 Label 추가
kubectl label namespace default istio-injection=enabled

# 확인
kubectl get namespace default -L istio-injection
```

### Pod 레벨

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  annotations:
    sidecar.istio.io/inject: "true"  # 이 파드만 주입
spec:
  containers:
  - name: myapp
    image: myapp:latest
```

## 수동 주입

```bash
# 매니페스트에 Sidecar 주입
istioctl kube-inject -f deployment.yaml | kubectl apply -f -

# 또는 파일로 저장
istioctl kube-inject -f deployment.yaml -o deployment-injected.yaml
kubectl apply -f deployment-injected.yaml
```

## Sidecar 리소스 설정

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

## Injection 제외

```yaml
# 특정 파드 제외
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

## 문제 해결

```bash
# Injection 상태 확인
kubectl get namespace default -o yaml | grep istio-injection

# Webhook 확인
kubectl get mutatingwebhookconfigurations

# Sidecar 확인
kubectl get pods -n default -o jsonpath='{.items[*].spec.containers[*].name}'
```

## 참고 자료

- [Istio Sidecar Injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
