# Istio 安装与初始设置

> **最后更新**：2026年10月16日 · 安装固定版本：Istio 1.31.2

截至2026年10月16日，Istio 1.31.2 是当前的 1.31 补丁版本；它包含 [ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/) 安全修复，以及 1.31.1 的 `BackendTLSPolicy` 明文回退修复。以下命令示例已从 1.31.1 更新；较早版本的 chart 渲染结果并不能验证 1.31.2 的所有值，因此应用前请渲染并检查所选 chart。

本文介绍如何在 Amazon EKS 集群上安装和初始配置 Istio。

## 目录

1. [先决条件](#prerequisites)
2. [选择安装方法](#choosing-an-installation-method)
3. [使用 istioctl 安装](#installation-using-istioctl)
4. [使用 Helm 安装](#installation-using-helm)
5. [使用 istioctl 声明式安装](#declarative-installation-with-istioctl)
6. [安装配置文件](#installation-profiles)
7. [验证安装](#installation-verification)
8. [部署示例应用程序](#sample-application-deployment)
9. [卸载 Istio](#istio-removal)
10. [故障排除](#troubleshooting)

## 先决条件 {#prerequisites}

安装 Istio 前，必须满足以下要求：

### 1. Amazon EKS 集群

- **Kubernetes 版本**：本 Istio 1.31.2 示例适用于 EKS 1.34–1.37（于2026年10月16日审阅）。Istio 1.31 支持 1.32–1.37；EKS 1.31–1.33 处于扩展支持阶段，1.34–1.37 处于标准支持阶段。请同时查看 [Istio 版本矩阵](https://istio.io/latest/docs/releases/supported-releases/)和 [EKS 生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)。
- **节点类型**：至少 2 个工作节点（建议：3 个或更多）
- **节点规格**：至少 2 个 vCPU、4GB RAM（建议：t3.medium 或更高规格）

这些示例面向 Linux EC2 工作节点。Fargate 无法运行这些 Istio 安装路径所需的 DaemonSet/特权网络功能。EKS Auto Mode 采用不同的托管网络/负载均衡模型；请单独验证其先决条件。

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
- **Helm**：当前受支持的 Helm 3 或 Helm 4 版本（最低 3.6；参见官方安装指南）

### 4. 集群资源

以下资源 requests 值仅供规划参考，并非通用最低配置；请根据实测负载进行容量规划：
- **控制平面**：1 vCPU，1.5GB RAM
- **Sidecar（每个 Pod）**：0.1 vCPU，128MB RAM

## 选择安装方法 {#choosing-an-installation-method}

选择一种受支持的安装路径；不要在同一个控制平面上同时运行 istioctl 和 Helm 安装：

| 方法 | 优点 | 缺点 | 推荐用例 |
|------|------|------|---------------|
| **istioctl** | 简单快速，提供验证功能 | 在自动化中需要显式协调 | 开发和生产 |
| **Helm** | 适合 GitOps，版本管理方便 | 配置可能较复杂 | 生产环境、CI/CD 管道 |

## 使用 istioctl 安装 {#installation-using-istioctl}

istioctl 是 Istio 官方 CLI 工具，也是最简单的安装方法。

### 1. 安装 istioctl

```bash
# Download the current 1.31 patch
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.2 sh -

# Add istioctl to PATH
cd istio-1.31.2
export PATH=$PWD/bin:$PATH

# Verify installation
istioctl version
```

### 2. 安装前验证集群

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

## 使用 Helm 安装 {#installation-using-helm}

istiod 1.31.0 和 1.31.2 的 chart 存档中不包含 `eks` 平台配置文件（`files/profile-platform-eks.yaml`；于2026年10月16日检查）。以下 chart 示例现已固定为 1.31.2，但本次审阅未渲染该 chart；安装前请检查所选 chart。这些示例不设置 `global.platform=eks`，以免假设该配置文件存在，并明确设置 EKS 先决条件和负载均衡器参数。

Helm 是适用于 GitOps 工作流的 Kubernetes 包管理器。

### 1. 添加 Helm 仓库

```bash
# Add Istio Helm repository
helm repo add istio https://blob.istio.io/istio-release/charts
helm repo update
```

### 2. 安装 istio-base

istio-base 用于安装 Istio 的 CRD（自定义资源定义）。

```bash
# Create istio-system namespace
kubectl create namespace istio-system

# Install istio-base chart
helm install istio-base istio/base \
  -n istio-system \
  --set defaultRevision=default \
  --version 1.31.2
```

### 3. 安装 istiod

istiod 是 Istio 控制平面。

```bash
# Install istiod chart
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.31.2 \
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
  --version 1.31.2 \
  --wait
```

### 5. 使用 values.yaml 自定义安装

```yaml
# values.yaml
global:
  hub: docker.io/istio
  tag: 1.31.2

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
  --version 1.31.2 \
  -f values.yaml \
  --wait
```

## 使用 istioctl 声明式安装 {#declarative-installation-with-istioctl}

上游集群内 operator 已在 1.23 中弃用，并在 1.24 中移除。`istioctl operator init/remove` 和向集群应用 IstioOperator 对象都不是当前的安装方法。[IstioOperator 文件格式仍受支持，可作为 istioctl 的输入](https://istio.io/latest/blog/2024/in-cluster-operator-deprecation-announcement/)。

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

## 安装配置文件 {#installation-profiles}

Istio 提供多种适用于不同用例的配置文件。

### 可用配置文件

| 配置文件 | 描述 | 组件 | 推荐用途 |
|-------|------|----------|----------|
| **default** | 适用于生产部署的默认设置 | istiod、Ingress Gateway | 大多数生产环境 |
| **demo** | 演示设置，并非包含所有功能 | istiod、Ingress Gateway、egress gateway、高跟踪采样率 | 开发和演示 |
| **minimal** | 仅安装最少组件 | 仅 istiod | 资源受限的环境 |
| **remote** | 用于多集群环境中的远程集群 | - | 多集群设置 |
| **empty** | 无默认配置 | - | 完全自定义设置 |
| **preview** | 包含实验性功能 | 各种实验性功能 | 测试环境 |
| **ambient** | 无 Sidecar 的 L4 网格 | istiod、CNI、ztunnel；L7 waypoint 需单独配置 | Ambient 部署 |

组件列表适用于 istioctl。使用 Helm 时必须分别安装每个 chart；配置文件不会安装其他 chart。

### 查看配置文件

```bash
helm show values istio/istiod --version 1.31.2
istioctl manifest generate --set profile=default > default.yaml
istioctl manifest generate --set profile=demo > demo.yaml
diff -u default.yaml demo.yaml
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
  --set components.pilot.k8s.resources.requests.memory=2Gi \
  -y
```

## 验证安装 {#installation-verification}

### 1. 检查控制平面

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

## 部署示例应用程序 {#sample-application-deployment}

Istio 包含一个名为 Bookinfo 的示例应用程序。

请从解压后的 `istio-1.31.2` 目录运行以下命令，并先将默认命名空间（`kubectl config set-context --current --namespace=default`）设为当前命名空间。如果使用 Helm，请先安装上文所述的可选 Gateway。后续的仪表板命令还要求单独安装遥测插件。

### 1. 为命名空间启用自动 Sidecar 注入

```bash
# Add label to default namespace
kubectl label namespace default istio-injection=enabled --overwrite

# Verify label
kubectl get namespace -L istio-injection
```

更改注入标签后，现有 Pod 需要重新创建。请使用未设置冲突的 `istio.io/rev` 或 ambient 标签的命名空间。

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

## 卸载 Istio {#istio-removal}

这些清理命令适用于一次性实验环境。清除操作会移除共享网格资源；从运行中的网格卸载前，请先移除已注入的工作负载，或在不启用注入的情况下重启它们。Helm 卸载会保留 CRD。

### 使用 istioctl 卸载

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

### 使用 Helm 卸载

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

## 故障排除 {#troubleshooting}

### 常见问题

#### 1. Sidecar 自动注入失败

**症状**：Envoy Sidecar 未注入 Pod

**解决方案**：
```bash
# Check namespace label
kubectl get namespace -L istio-injection

# Add label if missing
kubectl label namespace default istio-injection=enabled --overwrite

# Check Webhook
kubectl get mutatingwebhookconfiguration
```

#### 2. istiod Pod 无法启动

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

#### 3. Ingress Gateway 未获取外部 IP

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

### 收集日志

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

Istio 安装已完成！请参阅以下文档，开始使用 Istio：

1. **[基本概念](02-basic-concepts.md)**：了解 Istio 核心概念和架构
2. **[流量管理](traffic-management/README.md)**：了解 Gateway、VirtualService、DestinationRule
3. **[安全](security/README.md)**：配置 mTLS、身份验证和授权

## 参考资料

- [Istio 官方安装指南](https://istio.io/latest/docs/setup/install/)
- [Istio 配置文件文档](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
- [Istio EKS 平台指南](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
- [Istio 故障排除指南](https://istio.io/latest/docs/ops/diagnostic-tools/)

- [EKS Fargate 限制](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Istio 1.31 发布说明和制品迁移](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)
