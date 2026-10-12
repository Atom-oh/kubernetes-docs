# Istio 安装与初始设置

> **最后更新**: October 12, 2026 · 安装固定版本：Istio 1.31.1

截至 2026 年 10 月 12 日，Istio 1.31.1 是当前的 1.31 补丁版本；它修复了 `BackendTLSPolicy` 明文回退问题。下方 Helm 命令示例已从 1.31.0 更新；早期的 chart 渲染并不能验证所有 1.31.1 值，因此请在应用前渲染并检查所选 chart。

本文档介绍如何在 Amazon EKS 集群上安装和初始配置 Istio。

## 目录

1. [前提条件](#prerequisites)
2. [选择安装方法](#choosing-an-installation-method)
3. [使用 istioctl 安装](#installation-using-istioctl)
4. [使用 Helm 安装](#installation-using-helm)
5. [使用 istioctl 进行声明式安装](#declarative-installation-with-istioctl)
6. [安装配置文件](#installation-profiles)
7. [安装验证](#installation-verification)
8. [示例应用部署](#sample-application-deployment)
9. [Istio 移除](#istio-removal)
10. [故障排除](#troubleshooting)

## 前提条件

在安装 Istio 前，必须满足以下要求：

### 1. Amazon EKS 集群

- **Kubernetes 版本**：此 Istio 1.31.1 示例使用 EKS 1.34–1.37（于 2026 年 10 月 12 日审核）。Istio 1.31 支持 1.32–1.37；EKS 1.31–1.33 处于延长支持阶段，1.34–1.37 处于标准支持阶段。请同时查阅 [Istio 矩阵](https://istio.io/latest/docs/releases/supported-releases/) 和 [EKS 生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)。
- **节点类型**：至少 2 个 worker node（建议：3 个或更多）
- **节点规格**：至少 2 vCPU、4GB RAM（建议：t3.medium 或更大）

这些示例面向 Linux EC2 worker node。Fargate 无法运行这些 Istio 安装路径所需的 DaemonSet/特权网络。EKS Auto Mode 使用不同的托管网络/负载均衡模型；请单独验证其前提条件。

### 2. kubectl 安装与配置

```bash
# Verify kubectl installation
kubectl version --client

# Verify EKS cluster connection
kubectl get nodes
```

### 3. 必需工具

- **AWS CLI**：2.x 或更高版本
- **eksctl**：（可选）用于集群管理
- **Helm**：当前受支持的 Helm 3 或 Helm 4 版本（最低 3.6；请参阅官方安装指南）

### 4. 集群资源

以下为说明性规划请求，并非通用最低要求；应根据测量到的负载确定规模：
- **Control Plane**：1 vCPU、1.5GB RAM
- **Sidecar（每个 pod）**：0.1 vCPU、128MB RAM

## 选择安装方法

选择一种受支持的安装路径；不要在同一个 Control Plane 上同时运行 istioctl 和 Helm 安装：

| 方法 | 优点 | 缺点 | 推荐使用场景 |
|------|------|------|---------------|
| **istioctl** | 简单快速，提供验证功能 | 在自动化中需要显式协调 | 开发和生产环境 |
| **Helm** | 对 GitOps 友好，易于进行版本管理 | 配置可能较复杂 | 生产环境、CI/CD 管道 |

## 使用 istioctl 安装

istioctl 是 Istio 的官方 CLI 工具，也是最简单的安装方法。

### 1. 安装 istioctl

```bash
# Download the current 1.31 patch
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.1 sh -

# Add istioctl to PATH
cd istio-1.31.1
export PATH=$PWD/bin:$PATH

# Verify installation
istioctl version
```

### 2. 安装前集群验证

```bash
# Verify cluster meets Istio installation requirements
istioctl x precheck
```

### 3. 安装 Istio

```bash
# Install with default profile
istioctl install --set profile=default -y

# Check installation progress
kubectl get pods -n istio-system
```

### 4. 验证安装

```bash
# Check Istio components
kubectl get all -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod
```

## 使用 Helm 安装

上次审核期间渲染的 1.31.0 chart 不包含 `eks` 平台 profile。下方 chart 示例现已固定到 1.31.1，但本次审核未渲染该补丁版本的 chart；请在安装前检查所选 chart。这些示例未设置 `global.platform=eks`，而是采用显式的 EKS 前提条件和负载均衡器设置，以避免假定存在某个 profile。

Helm 是适用于 GitOps 工作流的 Kubernetes 包管理器。

### 1. 添加 Helm 仓库

```bash
# Add Istio Helm repository
helm repo add istio https://blob.istio.io/istio-release/charts
helm repo update
```

### 2. 安装 istio-base

istio-base 会安装 Istio 的 CRD（Custom Resource Definition）。

```bash
# Create istio-system namespace
kubectl create namespace istio-system

# Install istio-base chart
helm install istio-base istio/base \
  -n istio-system \
  --set defaultRevision=default \
  --version 1.31.1
```

### 3. 安装 istiod

istiod 是 Istio Control Plane。

```bash
# Install istiod chart
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.31.1 \
  --wait
```

### 4. 安装 Istio Ingress Gateway（可选）

```bash
# Verify the gateway namespace
kubectl get namespace istio-system

# Install Istio Ingress Gateway
helm install istio-ingressgateway istio/gateway \
  -n istio-system \
  --set labels.istio=ingressgateway \
  --set labels.app=istio-ingressgateway \
  --version 1.31.1 \
  --wait
```

### 5. 使用 values.yaml 进行自定义安装

```yaml
# values.yaml
global:
  hub: docker.io/istio
  tag: 1.31.1

autoscaleEnabled: true
autoscaleMin: 2
autoscaleMax: 5
resources:
  requests:
    cpu: 500m
    memory: 2048Mi

meshConfig:
  accessLogFile: /dev/stdout
```

```bash
# Install using values.yaml file
helm upgrade --install istiod istio/istiod \
  -n istio-system \
  --version 1.31.1 \
  -f values.yaml \
  --wait
```

## 使用 istioctl 进行声明式安装

上游集群内 operator 在 1.23 中已弃用，并在 1.24 中移除。`istioctl operator init/remove` 以及向集群应用 IstioOperator 对象已不是当前的安装方法。[IstioOperator 文件格式仍受支持，可作为 istioctl 的输入](https://istio.io/latest/blog/2024/in-cluster-operator-deprecation-announcement/)。

```yaml
# istio-operator.yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-control-plane
  namespace: istio-system
spec:
  profile: default
  meshConfig:
    accessLogFile: /dev/stdout
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 1000m
            memory: 4Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5
```

```bash
istioctl install -f istio-operator.yaml
kubectl rollout status deployment/istiod -n istio-system
```

## 安装配置文件

Istio 为不同使用场景提供多种 profile。

### 可用 profile

| Profile | 说明 | 组件 | 推荐使用场景 |
|-------|------|----------|----------|
| **default** | 用于生产部署的默认设置 | istiod、ingress gateway | 大多数生产环境 |
| **demo** | 演示设置，并非所有功能 | istiod、ingress gateway、egress gateway、高追踪采样率 | 开发和演示 |
| **minimal** | 仅安装最小组件 | 仅 istiod | 资源受限环境 |
| **remote** | 用于多集群环境中的远程集群 | - | 多集群设置 |
| **empty** | 无默认配置 | - | 完全自定义设置 |
| **preview** | 包含实验性功能 | 各种实验性功能 | 测试环境 |
| **ambient** | 无 Sidecar 的 L4 服务网格 | istiod、CNI、ztunnel；L7 waypoint 单独配置 | Ambient 部署 |

组件列表适用于 istioctl。Helm 要求分别安装每个 chart；一个 profile 不会安装其他 chart。

### 检查 profile

```bash
helm show values istio/istiod --version 1.31.1
istioctl manifest generate --set profile=default > default.yaml
istioctl manifest generate --set profile=demo > demo.yaml
diff -u default.yaml demo.yaml
```

### 按 profile 安装

```bash
# Install with demo profile
istioctl install --set profile=demo -y

# Install with minimal profile
istioctl install --set profile=minimal -y
```

### 自定义 profile

```bash
# Modify specific settings based on profile
istioctl install --set profile=default \
  --set meshConfig.accessLogFile=/dev/stdout \
  --set components.pilot.k8s.resources.requests.memory=2Gi \
  -y
```

## 安装验证

### 1. 检查 Control Plane

```bash
# Check all resources in istio-system namespace
kubectl get all -n istio-system

# Check istiod status
kubectl get deployment istiod -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod --tail=100
```

### 2. 检查 Istio 版本

```bash
# Control Plane version
istioctl version

# Or
kubectl get pods -n istio-system -o yaml | grep image:
```

### 3. 验证 Istio 配置

```bash
# Check Istio installation status
kubectl rollout status deployment/istiod -n istio-system
istioctl proxy-status

# Analyze Istio configuration
istioctl analyze -A
```

### 4. 检查 Webhook

```bash
# Check MutatingWebhookConfiguration
kubectl get mutatingwebhookconfiguration

# Check ValidatingWebhookConfiguration
kubectl get validatingwebhookconfiguration
```

## 示例应用部署

Istio 包含一个名为 Bookinfo 的示例应用。

请在解压后的 `istio-1.31.1` 目录中运行这些命令，并选择 default namespace（`kubectl config set-context --current --namespace=default`）。对于 Helm，请先安装上方可选的 gateway。后面的 dashboard 命令需要单独安装 telemetry addon。

### 1. 为 Namespace 启用自动 Sidecar 注入

```bash
# Add label to default namespace
kubectl label namespace default istio-injection=enabled --overwrite

# Verify label
kubectl get namespace -L istio-injection
```

更改注入标签后，现有 pod 需要重新创建。请使用没有冲突 `istio.io/rev` 或 ambient 标签的 namespace。

### 2. 部署 Bookinfo 应用

```bash
# Deploy Bookinfo application
kubectl apply -f samples/bookinfo/platform/kube/bookinfo.yaml

# Check pods (each pod should have 2 containers)
kubectl get pods

# Check services
kubectl get services
```

### 3. 验证应用访问

```bash
# Test productpage service
kubectl exec "$(kubectl get pod -l app=ratings -o jsonpath='{.items[0].metadata.name}')" \
  -c ratings -- curl -sS productpage:9080/productpage | grep -o "<title>.*</title>"
```

### 4. 配置 Ingress Gateway

```bash
# Create Bookinfo Gateway
cat <<'EOF' > bookinfo-gateway.yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: default
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo
  namespace: default
spec:
  hosts:
  - "*"
  gateways:
  - bookinfo-gateway
  http:
  - route:
    - destination:
        host: productpage
        port:
          number: 9080
EOF
kubectl apply -f bookinfo-gateway.yaml

# Check Gateway
kubectl get gateway.networking.istio.io

# Check VirtualService
kubectl get virtualservice
```

### 5. 配置外部访问

```bash
# Get Ingress Gateway External IP
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')

export GATEWAY_URL=$INGRESS_HOST:$INGRESS_PORT

# Access application
echo "http://$GATEWAY_URL/productpage"

# Access in browser or verify with curl
curl -s "http://$GATEWAY_URL/productpage" | grep -o "<title>.*</title>"
```

## Istio 移除

这些清理命令适用于一次性实验室环境。清除会移除共享服务网格资源；在卸载正在运行的服务网格之前，请移除已注入的工作负载，或在未注入的情况下重启它们。Helm 卸载会保留 CRD。

### 使用 istioctl 移除

```bash
# Remove sample application
kubectl delete -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl delete -f bookinfo-gateway.yaml

# Remove Istio
istioctl uninstall --purge -y

# Remove istio-system namespace
kubectl delete namespace istio-system

# Remove Istio label
kubectl label namespace default istio-injection-
```

### 使用 Helm 移除

```bash
# Remove Ingress Gateway
helm delete istio-ingressgateway -n istio-system

# Remove istiod
helm delete istiod -n istio-system

# Remove istio-base
helm delete istio-base -n istio-system

# Remove namespaces
kubectl delete namespace istio-system
```

## 故障排除

### 常见问题

#### 1. Sidecar 自动注入失败

**症状**：Envoy Sidecar 未注入到 pod 中

**解决方案**：
```bash
# Check namespace label
kubectl get namespace -L istio-injection

# Add label if missing
kubectl label namespace default istio-injection=enabled --overwrite

# Check Webhook
kubectl get mutatingwebhookconfiguration
```

#### 2. istiod Pod 未启动

**症状**：istiod pod 处于 Pending 或 CrashLoopBackOff 状态

**解决方案**：
```bash
# Check pod status
kubectl get pods -n istio-system

# Check pod events
kubectl describe pod -n istio-system -l app=istiod

# Check logs
kubectl logs -n istio-system -l app=istiod

# Check resources
kubectl top nodes
kubectl describe nodes
```

#### 3. Ingress Gateway 未接收外部 IP

**症状**：LoadBalancer 类型 Service 处于 Pending 状态

**解决方案**：
```bash
# Check service status
kubectl get svc -n istio-system istio-ingressgateway

# Check AWS Load Balancer Controller
kubectl get deployment -n kube-system aws-load-balancer-controller

# Check events
kubectl describe svc -n istio-system istio-ingressgateway
```

### 调试工具

#### istioctl analyze

```bash
# Analyze entire cluster
istioctl analyze -A

# Analyze specific namespace
istioctl analyze -n default
```

#### istioctl proxy-status

```bash
# Check all proxy status
istioctl proxy-status

# Check specific pod proxy status
istioctl proxy-status <POD_NAME>.<NAMESPACE>
```

#### istioctl dashboard

```bash
# Launch Kiali dashboard
istioctl dashboard kiali

# Launch Grafana dashboard
istioctl dashboard grafana

# Launch Prometheus dashboard
istioctl dashboard prometheus

# Envoy admin interface
istioctl dashboard envoy <POD_NAME>.<NAMESPACE>
```

### 日志收集

```bash
# Control Plane logs
kubectl logs -n istio-system -l app=istiod

# Ingress Gateway logs
kubectl logs -n istio-system -l app=istio-ingressgateway

# Envoy logs for specific pod
kubectl logs <POD_NAME> -c istio-proxy

# Save all Istio-related logs to file
istioctl bug-report
```

## 后续步骤

Istio 安装已完成！现在请参阅以下文档，开始使用 Istio：

1. **[基本概念](02-basic-concepts.md)**：了解 Istio 核心概念和架构
2. **[流量管理](traffic-management/README.md)**：学习 Gateway、VirtualService、DestinationRule
3. **[安全](security/README.md)**：配置 mTLS、认证、授权

## 参考资料

- [Istio 官方安装指南](https://istio.io/latest/docs/setup/install/)
- [Istio profile 文档](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
- [Istio EKS 平台指南](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
- [Istio 故障排除指南](https://istio.io/latest/docs/ops/diagnostic-tools/)

- [EKS Fargate 限制](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Istio 1.31 发布与制品迁移](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)
