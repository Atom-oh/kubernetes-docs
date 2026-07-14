# Istio 安装与初始设置

本文介绍如何在 Amazon EKS 集群上安装并初步配置 Istio。

## 目录

1. [前置条件](#prerequisites)
2. [选择安装方法](#choosing-an-installation-method)
3. [使用 istioctl 安装](#installation-using-istioctl)
4. [使用 Helm 安装](#installation-using-helm)
5. [使用 Istio Operator 安装](#installation-using-istio-operator)
6. [安装配置文件](#installation-profiles)
7. [安装验证](#installation-verification)
8. [示例应用程序部署](#sample-application-deployment)
9. [移除 Istio](#istio-removal)
10. [故障排除](#troubleshooting)

## 前置条件

在安装 Istio 之前，必须满足以下要求：

### 1. Amazon EKS 集群

- **Kubernetes 版本**：1.28 或更高版本（建议：1.34）
- **Node 类型**：至少 2 个 worker Node（建议：3 个或更多）
- **Node 大小**：至少 2 vCPU、4GB RAM（建议：t3.medium 或更大）

### 2. kubectl 安装与配置

```bash
# Verify kubectl installation
kubectl version --client

# Verify EKS cluster connection
kubectl get nodes
```

### 3. 所需工具

- **AWS CLI**：2.x 或更高版本
- **eksctl**：（可选）用于集群管理
- **Helm**：3.x 或更高版本（如果使用 Helm 安装方法）

### 4. 集群资源

最低资源要求：
- **Control Plane**：1 vCPU、1.5GB RAM
- **Sidecar（每个 Pod）**：0.1 vCPU、128MB RAM

## 选择安装方法

Istio 提供三种主要安装方法：

| 方法 | 优点 | 缺点 | 推荐使用场景 |
|------|------|------|---------------|
| **istioctl** | 简单快速，提供验证功能 | 难以自动化 | 开发和测试环境 |
| **Helm** | 对 GitOps 友好，易于版本管理 | 配置可能较复杂 | 生产环境、CI/CD 流水线 |
| **Istio Operator** | 声明式管理、自动升级 | 需要额外资源 | 大规模生产环境 |

## 使用 istioctl 安装

istioctl 是 Istio 的官方 CLI 工具，也是最简单的安装方法。

### 1. 安装 istioctl

```bash
# Download istioctl (latest version)
curl -L https://istio.io/downloadIstio | sh -

# Or download a specific version
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -

# Add istioctl to PATH
cd istio-1.28.0
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

Helm 是适用于 GitOps 工作流的 Kubernetes 包管理器。

### 1. 添加 Helm 仓库

```bash
# Add Istio Helm repository
helm repo add istio https://istio-release.storage.googleapis.com/charts
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
  --version 1.28.0
```

### 3. 安装 istiod

istiod 是 Istio Control Plane。

```bash
# Install istiod chart
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.28.0 \
  --wait
```

### 4. 安装 Istio Ingress Gateway（可选）

```bash
# Create istio-ingress namespace
kubectl create namespace istio-ingress

# Install Istio Ingress Gateway
helm install istio-ingress istio/gateway \
  -n istio-ingress \
  --version 1.28.0 \
  --wait
```

### 5. 使用 values.yaml 进行自定义安装

```yaml
# values.yaml
global:
  hub: docker.io/istio
  tag: 1.28.0

pilot:
  autoscaleEnabled: true
  autoscaleMin: 2
  autoscaleMax: 5
  resources:
    requests:
      cpu: 500m
      memory: 2048Mi

# AWS EKS specific settings
meshConfig:
  accessLogFile: /dev/stdout
  enableTracing: true
  defaultConfig:
    tracing:
      sampling: 100.0
```

```bash
# Install using values.yaml file
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.28.0 \
  -f values.yaml \
  --wait
```

## 使用 Istio Operator 安装

Istio Operator 以声明式方式管理 Istio。

### 1. 安装 Istio Operator

```bash
# Install Operator
istioctl operator init

# Verify Operator installation
kubectl get pods -n istio-operator
```

### 2. 创建 IstioOperator 资源

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

### 3. 通过 Operator 安装 Istio

```bash
# Apply IstioOperator resource
kubectl create ns istio-system
kubectl apply -f istio-operator.yaml

# Check installation progress
kubectl get istiooperator -n istio-system
```

## 安装配置文件

Istio 为不同使用场景提供多种配置文件。

### 可用配置文件

| 配置文件 | 描述 | 组件 | 推荐用途 |
|-------|------|----------|----------|
| **default** | 用于生产部署的默认设置 | istiod、Ingress Gateway | 大多数生产环境 |
| **demo** | 启用所有功能，用于学习 | istiod、Ingress Gateway、Egress Gateway、高追踪采样率 | 开发和演示 |
| **minimal** | 仅安装最少组件 | 仅 istiod | 资源受限环境 |
| **remote** | 用于多集群环境中的远程集群 | - | 多集群设置 |
| **empty** | 无默认配置 | - | 完全自定义设置 |
| **preview** | 包含实验性功能 | 各种实验性功能 | 测试环境 |

### 检查配置文件

```bash
# List available profiles
istioctl profile list

# Check specific profile configuration
istioctl profile dump default

# Compare two profiles
istioctl profile diff default demo
```

### 按配置文件安装

```bash
# Install with demo profile
istioctl install --set profile=demo -y

# Install with minimal profile
istioctl install --set profile=minimal -y
```

### 自定义配置文件

```bash
# Modify specific settings based on profile
istioctl install --set profile=default \
  --set meshConfig.accessLogFile=/dev/stdout \
  --set values.pilot.resources.requests.memory=2Gi \
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
istioctl verify-install

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

## 示例应用程序部署

Istio 包含一个名为 Bookinfo 的示例应用程序。

### 1. 为 Namespace 启用自动 Sidecar 注入

```bash
# Add label to default namespace
kubectl label namespace default istio-injection=enabled

# Verify label
kubectl get namespace -L istio-injection
```

### 2. 部署 Bookinfo 应用程序

```bash
# Deploy Bookinfo application
kubectl apply -f samples/bookinfo/platform/kube/bookinfo.yaml

# Check pods (each pod should have 2 containers)
kubectl get pods

# Check services
kubectl get services
```

### 3. 验证应用程序访问

```bash
# Test productpage service
kubectl exec "$(kubectl get pod -l app=ratings -o jsonpath='{.items[0].metadata.name}')" \
  -c ratings -- curl -sS productpage:9080/productpage | grep -o "<title>.*</title>"
```

### 4. 配置 Ingress Gateway

```bash
# Create Bookinfo Gateway
kubectl apply -f samples/bookinfo/networking/bookinfo-gateway.yaml

# Check Gateway
kubectl get gateway

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

## 移除 Istio

### 使用 istioctl 移除

```bash
# Remove sample application
kubectl delete -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl delete -f samples/bookinfo/networking/bookinfo-gateway.yaml

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
helm delete istio-ingress -n istio-ingress

# Remove istiod
helm delete istiod -n istio-system

# Remove istio-base
helm delete istio-base -n istio-system

# Remove namespaces
kubectl delete namespace istio-system
kubectl delete namespace istio-ingress
```

### 使用 Istio Operator 移除

```bash
# Remove IstioOperator resource
kubectl delete istiooperator istio-control-plane -n istio-system

# Remove Operator
istioctl operator remove

# Remove namespaces
kubectl delete namespace istio-system
kubectl delete namespace istio-operator
```

## 故障排除

### 常见问题

#### 1. Sidecar 自动注入失败

**症状**：Envoy Sidecar 未注入到 Pod 中

**解决方案**：
```bash
# Check namespace label
kubectl get namespace -L istio-injection

# Add label if missing
kubectl label namespace default istio-injection=enabled

# Check Webhook
kubectl get mutatingwebhookconfiguration
```

#### 2. istiod Pod 未启动

**症状**：istiod Pod 处于 Pending 或 CrashLoopBackOff 状态

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

#### 3. Ingress Gateway 未获取到外部 IP

**症状**：LoadBalancer 类型的 Service 处于 Pending 状态

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
3. **[安全](security/README.md)**：配置 mTLS、认证和授权

## 参考资料

- [Istio 官方安装指南](https://istio.io/latest/docs/setup/install/)
- [Istio 配置文件文档](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
- [AWS EKS Workshop - Istio](https://www.eksworkshop.com/intermediate/330_servicemesh_using_istio/)
- [Istio 故障排除指南](https://istio.io/latest/docs/ops/diagnostic-tools/)
