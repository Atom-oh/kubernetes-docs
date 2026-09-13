# Linkerd 安装和设置

> **最后更新**：2026 年 9 月 11 日 · 公共 CLI：edge-26.9.1 · 匹配 chart：2026.9.1

本指南涵盖受控 Kubernetes 安装、Helm/CLI 所有权、高可用、可选扩展、EKS 注意事项、升级和移除。上游项目发布 edge 制品；稳定发行版具有厂商专属安装/支持指南。2.20 等里程碑不是上游 stable-2.20.0 下载版本。

除标为 PowerShell 外，以下命令使用 Bash。使用目标 kubeconfig/上下文和安装所有者。CLI 与 Helm 安装流程是**备选方案**：不要在 Helm 管理的发布上应用 CLI 生成资源。离线检查不确立生产容量、存储、网络执行或应用兼容性。

## 前提条件

### Kubernetes 和 Gateway API

| 分支/版本 | Kubernetes 证据 | Gateway API 证据 |
|---|---|---|
| Linkerd 2.20 里程碑/发行版 | 公布矩阵为 1.31–1.35；确认厂商支持 | 公布矩阵为 1.2.1–1.5.1 |
| 本文使用的公共 edge-26.9.1 | 发布 CLI 最低 1.31.0；edge-26.8.2 将已测试最高版本提高到 1.36 | 发布支持 1.5.1；本指南使用其标准资源包 |
| 历史 2.16 | 公布矩阵 1.22–1.29 | 不是当前安装建议 |
| 历史 2.15 / 2.14 | 公布范围 1.22–1.29 / 1.21–1.28 | 检查对应版本；不要推断“及所有后续 Kubernetes 版本” |

CLI 最低版本检查不是最高支持版本检查。check --pre 通过不证明与新发布 Kubernetes 或 Gateway API 版本兼容。EKS 还需检查其可用版本和支持期。本审计 Helm 验证使用 Kubernetes 1.35 能力。

### 容量和平台

不要用通用 100m CPU/200Mi 声称来规划整个控制平面。检查控制器、policy 容器、代理、初始化容器和扩展的渲染 requests/limits；测量实际流量和连接负载。高可用要求至少三个合格节点以满足必需节点反亲和性，并在发布期间有足够容量。可用区分散是偏好，不保证三个不同可用区。

流程面向 Linux Kubernetes 节点。Windows CLI 下载不证明支持 Windows 工作负载配置。单独检查所选版本的工作负载/平台支持。对于 Cilium kube-proxy 替代，审核 socketLB.hostNamespaceOnly；Linkerd CNI 与 Cilium 链接时，cni.exclusive 必须允许其他插件。

### 网络路径和预检

验证源/目标路径，不只是列出应到处开放的端口：

| 路径 | 固定渲染中的默认示例 |
|---|---|
| API 服务器到准入服务 | Service 443 到 injector/SP-validator 8443 和 policy-validator 9443 |
| 代理到控制平面 | Identity 8080、destination 8086、policy 8090 |
| 网格内应用流量 | 代理入站 4143，加实际应用/服务路径 |
| Viz（已安装时） | Tap API 服务器 8089、tap gRPC 8088、metrics API 8085、Prometheus 9090 |
| 诊断 | 代理指标 4191；Web UI 8084，独立 Web 管理/就绪 9994 |

这些是组件端口，不是无限制安全组规则集。包括 DNS、Kubernetes API 和所选 CNI/网络策略行为。检查实际 Service targetPorts 和 webhook 配置。

```bash
LINKERD_CHART_VERSION=2026.9.1
CNI_ENABLED=false  # Set true only after installing/verifying Linkerd CNI.
kubectl config current-context
kubectl version
kubectl get nodes -L kubernetes.io/os,kubernetes.io/arch,topology.kubernetes.io/zone
kubectl get crd httproutes.gateway.networking.k8s.io \
  -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
# For a new lab without a conflicting installed bundle, after ownership review:
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
linkerd check --pre --linkerd-cni-enabled="$CNI_ENABLED"
```

仅在审核现有 CRD 所有权及所有使用控制器后，按需应用 Gateway API 资源包。若选择 Linkerd CNI，在控制平面前安装/验证，并使用下文 CNI 感知检查。阅读实际检查输出和退出状态；旧示例长篇“全部绿色”记录不是您集群的结果。

## 安装 Linkerd CLI

### 固定 Linux/macOS 二进制

以下选择确切发布制品，并将 SHA256 与官方发布元数据比较。仅更改当前 shell 的 PATH：

```bash
set -euo pipefail
LINKERD_VERSION=edge-26.9.1
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64) suffix=linux-amd64; expected=094e1de06215fbe76fc011cf62c96214f8dae0cd5a58135fb40307be88b6b176 ;;
  Linux/aarch64|Linux/arm64) suffix=linux-arm64; expected=f92eddc52dc1f3089b65fd16014cdb1bc6b07c3fd177091c365cf3d8c0ea1a8b ;;
  Darwin/x86_64) suffix=darwin; expected=acff9471f26552dd0ebb9560925a98d5ca1213a13dfc81464a2b815c9201664d ;;
  Darwin/arm64) suffix=darwin-arm64; expected=5050da9d974e0c2f548a2e9f145540ec035582cfd67f47c58c37411ae3008913 ;;
  *) echo "No verified asset for this OS/architecture in this example" >&2; exit 1 ;;
esac
CLI_DIR="$PWD/linkerd-cli/$LINKERD_VERSION"
mkdir -p "$CLI_DIR"
curl --proto '=https' --tlsv1.2 -fsSL \
  "https://github.com/linkerd/linkerd2/releases/download/$LINKERD_VERSION/linkerd2-cli-$LINKERD_VERSION-$suffix" \
  -o "$CLI_DIR/linkerd.download"
if command -v sha256sum >/dev/null; then
  actual=$(sha256sum "$CLI_DIR/linkerd.download" | awk '{print $1}')
else
  actual=$(shasum -a 256 "$CLI_DIR/linkerd.download" | awk '{print $1}')
fi
test "$actual" = "$expected"
chmod 755 "$CLI_DIR/linkerd.download"
mv "$CLI_DIR/linkerd.download" "$CLI_DIR/linkerd"
export PATH="$CLI_DIR:$PATH"
linkerd version --client
```

所列制品覆盖 Linux amd64/arm64 和 macOS Intel/Apple Silicon。不要假定安装脚本的通用 ARM 分支意味着此版本发布 32 位 ARM 二进制。本审计执行了原生 Linux arm64 CLI；其他平台二进制从官方发布元数据识别。

### 官方安装器替代方案

旧 run.linkerd.io/install 脚本已弃用，安装的是 edge，不是 stable。当前安装器接受环境变量 LINKERD2_VERSION；旧 sh --version stable-2.16.0 命令不会选择受支持上游稳定制品。

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://run.linkerd.io/install-edge -o install-linkerd.sh
# Inspect the downloaded script before execution.
LINKERD2_VERSION=edge-26.9.1 INSTALLROOT="$PWD/linkerd-installer" sh ./install-linkerd.sh
export PATH="$PWD/linkerd-installer/bin:$PATH"
linkerd version --client
```

从版本兼容矩阵选择 Gateway API 资源包。安装器完成消息包含自己的示例版本；本指南检查所选发布后固定 1.5.1。包管理器和厂商发行版可能选择不同版本；验证制品来源和版本，不要假定 Homebrew/Chocolatey 就是此处固定版本。本流程不需要编辑 shell 配置文件。

### Windows 二进制

发布制品名为 windows.exe，不是 windows-amd64.exe：

```powershell
$ErrorActionPreference = "Stop"
$LinkerdVersion = "edge-26.9.1"
$ExpectedSha256 = "d50119c635a0052bfcc7e0b96dcc985676b237ebc87464380677c413344d99a9"
$Download = Join-Path (Get-Location) "linkerd.download.exe"
$Url = "https://github.com/linkerd/linkerd2/releases/download/$LinkerdVersion/linkerd2-cli-$LinkerdVersion-windows.exe"
Invoke-WebRequest -Uri $Url -OutFile $Download
if ((Get-FileHash -Algorithm SHA256 $Download).Hash.ToLowerInvariant() -ne $ExpectedSha256) {
    throw "Linkerd release checksum mismatch"
}
Move-Item $Download (Join-Path (Get-Location) "linkerd.exe") -Force
.\linkerd.exe version --client
```

其余 Bash 示例需要适当 shell，如已配置 WSL 环境，或转换为原生 PowerShell 命令。本审计未执行 PowerShell 或测试 Windows 工作负载。

## 控制平面安装

### CLI 安装

对于全新 CLI 管理安装，先应用 Linkerd CRD，再生成/安装控制平面：

```bash
linkerd install --crds > linkerd-crds.yaml
kubectl apply -f linkerd-crds.yaml
linkerd install --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-control-plane.yaml
# Review the generated resources and trust credentials before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

命令生成清单；kubectl 执行安装。CLI 默认生成的信任锚和签发者凭证寿命有限，需要轮换规划。共享信任多集群需要有意提供凭证，不能在每集群独立生成根。

### Helm 安装

Helm 提供可重复的发布/values 流程。将 chart 版本与 CLI 标签分开固定：

```bash
helm repo add linkerd-edge https://helm.linkerd.io/edge
helm repo update linkerd-edge
helm show chart linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
```

匹配公共 chart 为 2026.9.1 的 linkerd-crds、linkerd-control-plane、linkerd-viz、linkerd-multicluster 和 linkerd2-cni。当前核心 chart appVersion 为 edge-26.9.1。不要安装未固定的旧 stable 仓库 chart，却假定它匹配此 CLI。

#### 信任锚和签发者

Helm 需要信任锚证书加签发者证书/私钥，或有意配置的受支持外部签发者 Secret 集成。不需要上传根 CA 私钥。

使用已安装的 [Smallstep CLI](https://smallstep.com/docs/step-cli/installation/) 及公布的 certificate-create 接口。此 ECDSA P-256 示例保留原始演示寿命，但修复 --not-after 后错误的续行：

```bash
umask 077
mkdir linkerd-pki
(
  cd linkerd-pki
  # Demonstration lifetimes, not a universal certificate policy.
  step certificate create root.linkerd.cluster.local ca.crt ca.key \
    --profile root-ca --kty EC --curve P-256 \
    --not-after 87600h --no-password --insecure
  step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
    --profile intermediate-ca --kty EC --curve P-256 \
    --not-after 8760h --no-password --insecure \
    --ca ca.crt --ca-key ca.key
  openssl verify -CAfile ca.crt issuer.crt
  openssl x509 -in issuer.crt -noout -text
)
```

安装前检查证书链、算法和有效期。根私钥保留在 Kubernetes 外；下方仅提供公有信任锚和签发者签名凭证。--no-password/--insecure 创建未加密本地密钥，因此示例使用受限目录/umask。生产 PKI 需要获准密钥存储和轮换流程。审计对照官方文档检查这些标志；未执行 Smallstep 证书生成。

#### 自定义 values

将以下保存为 linkerd-values.yaml。这些是容量示例，不是工作负载保证：

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
  logLevel: warn,linkerd=info
  logFormat: plain
identity:
  issuer:
    clockSkewAllowance: 20s
    issuanceLifetime: 24h0m0s
controllerResources: &id001
  cpu:
    request: 100m
    limit: 1000m
  memory:
    request: 50Mi
    limit: 250Mi
destinationResources: *id001
identityResources: *id001
proxyInjectorResources: *id001
```

proxy.logLevel 和 proxy.logFormat 是实际嵌套键。destinationResources、identityResources 和 proxyInjectorResources 受支持，尽管基础 values 文件中不全包含；打包高可用文件和模板使用它们。旧 namespace.labels 映射和顶层 proxyLogLevel/proxyLogFormat 未被使用。Chart 默认向配置的代理日志选择器追加标头/请求日志抑制规则；检查最终环境值。

```bash
helm install linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --create-namespace --wait

helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  > linkerd-rendered.yaml
# Review the render, then install through Helm (do not apply the render as another owner).
helm install linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  --wait --timeout 10m
linkerd check
```

生成清单和 Helm values 备份可能包含签发者私钥。保持受限，不要粘贴到诊断报告。后续升级保留同一发布/凭证所有者。

## 高可用（HA）安装

使用固定 chart 打包的 values-ha.yaml：

```bash
helm pull linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
tar -xOf "linkerd-control-plane-$LINKERD_CHART_VERSION.tgz" \
  linkerd-control-plane/values-ha.yaml > linkerd-ha.yaml
# For the Helm render/install above, use:
# -f linkerd-ha.yaml -f linkerd-values.yaml
# For a new CLI-owned installation, render with:
linkerd install --ha --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-ha-rendered.yaml
```

Helm 渲染和安装时，将所示 HA 文件放在自定义 values **之前**。检查后续覆盖不会禁用必需高可用设置。

打包配置档为关键组件启用三个副本、必需按节点分离、优先按可用区分离、PDB 和 Fail 准入 webhook 策略。这些是冗余服务实例，不是三成员共识法定人数。可用性还取决于 API 服务器/网络访问、凭证、容量和应用。

旧手写 destination.replicas/identity.resources/proxyInjector.resources 字段未配置目标容器。根 podDisruptionBudget 映射未创建任何 PDB，根 topologySpreadConstraints 未被使用。对旧示例离线渲染显示三个副本，但缺少控制器资源设置和 PDB。使用实际打包配置档并检查结果。

```bash
kubectl -n linkerd get pods -o wide
kubectl -n linkerd get pdb
kubectl -n linkerd get deployments -o yaml
```

少于三个合格节点时，必需反亲和性可能使副本 Pending。依赖高可用前检查准入 Fail 行为和中断；不要将削弱 webhook 策略作为通用可用性修复。


## 扩展安装

### Viz：仪表板和指标

对于 CLI 管理的扩展：

```bash
linkerd viz install > linkerd-viz.yaml
# Review the optional extension and its metrics backend.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Helm 使用时，将以下保存为 viz-values.yaml，并检查渲染的 PVC、Deployment 和资源设置：

```yaml
prometheus:
  enabled: true
  resources:
    cpu:
      request: 300m
      limit: 1000m
    memory:
      request: 300Mi
      limit: 1Gi
  persistence:
    storageClass: gp3
    size: 10Gi
    accessMode: ReadWriteOnce
dashboard:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
tap:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi
metricsAPI:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
```

```bash
helm install linkerd-viz linkerd-edge/linkerd-viz \
  --version "$LINKERD_CHART_VERSION" -n linkerd-viz --create-namespace \
  -f viz-values.yaml --wait --timeout 10m
linkerd viz check
```

所选 chart 在 persistence **映射存在时**支持持久化。不使用 persistence.enabled 作为开关。PVC 模板要求 accessMode；旧示例省略它，渲染出 null 访问模式。省略映射则使用 emptyDir。gp3 StorageClass 是示例前提，不是 Viz 创建的资源；EKS 上验证 EBS CSI 驱动、权限和卷拓扑。

捆绑 Prometheus 为单副本；持久化选择 Recreate 部署策略。PVC 在适当 Pod 替换中保留数据，但不使指标存储高可用，也不保证可用性不中断。Chart 2026.9.1 默认 Prometheus v2.55.1 和六小时保留。明确选择后端维护、保留和可用性要求。

对于已配置外部 Prometheus，这是**替代** values 文件：

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
```

切换前配置外部服务器的 Linkerd 抓取/重标记和访问策略。验证真实 Viz 查询和指标，不只看 HTTP 就绪端点。dashboard、tap 和 metricsAPI 资源设置受支持。grafana.enabled 不是部署开关：此 chart 为独立管理的 Grafana 暴露链接设置。

初始流程使用 localhost 仪表板命令。dashboard.enforcedHostRegexp 验证 Host 值；不是用户身份验证，空值选择 chart 默认主机限制。组织入口需要独立身份验证/授权、获准网络暴露和允许的主机。

### 分布式追踪

edge-26.9.1 没有 linkerd jaeger 子命令。公共 linkerd-jaeger chart 历史止于 2025.9.4；不是匹配 2026.9.1 的扩展。用独立管理 Collector/后端及所选代理追踪配置替换过时安装/检查/升级/卸载说明。

追踪需要入站追踪上下文、应用传播和兼容采集/导出协议。Viz 拓扑或指标图不是分布式追踪。完整数据路径参阅[可观测性指南](05-observability.md)和[官方追踪文档](https://linkerd.io/docs/features/distributed-tracing/)。本安装审计不声称未测试的 Collector/Jaeger 部署端到端正常。若旧安装已有 linkerd-jaeger 发布，清点并迁移数据，再通过原所有者退役；当前 CLI 无法管理此已移除扩展。

### 多集群

CLI 可渲染基础扩展：

```bash
linkerd multicluster install > linkerd-multicluster.yaml
# Review network exposure, shared trust and actual gateway configuration first.
kubectl apply -f linkerd-multicluster.yaml
linkerd multicluster check
```

应用前选择适合网络的网关暴露方式。仅安装扩展不链接集群、不创建共享信任，也不授予远程 Kubernetes API 访问。

对于使用 **AWS Load Balancer Controller** 的 EKS 部署，此示例选择内部 NLB，并保留到 Linkerd 网关的 TCP 传输：

```yaml
gateway:
  replicas: 1
  serviceType: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
remoteMirrorServiceAccountName: linkerd-service-mirror-remote-access-default
```

保存为 multicluster-values.yaml，再使用 Helm 替代方式：

```bash
helm install linkerd-multicluster linkerd-edge/linkerd-multicluster \
  --version "$LINKERD_CHART_VERSION" -n linkerd-multicluster --create-namespace \
  -f multicluster-values.yaml --wait --timeout 10m
```

loadBalancerClass 选择目标控制器。EKS Auto Mode 使用不同类/配置约定；不要混合这些假设或随意更改现有 Service 所有权。确保远程网络能解析/访问内部网关及探测路径。不要在无关 ACM 监听器终止 Linkerd 传输 mTLS。

gateway.resources 不被固定 chart 使用。网关代理资源来自注入配置；检查生成 Pod，不要假定被忽略的 values 块更改了 limits。此 chart 附带高可用覆盖使用 gateway.replicas 和反亲和性。

当前 edge 远程凭证拒绝 exec 身份验证提供程序。使用[多集群指南](06-multi-cluster.md)支持的凭证流程，验证生成的 service-mirror 控制器/版本及最小权限 API 访问。

## CNI 和 Amazon EKS 配置

### 可选 Linkerd CNI

Linkerd CNI 与主 CNI 链接；不替代 Amazon VPC CNI 或 Cilium。在控制平面和网格工作负载使用启用 CNI 的配置**之前**，它必须在适用节点就绪：

```bash
# Optional branch, before control-plane installation.
helm install linkerd-cni linkerd-edge/linkerd2-cni \
  --version "$LINKERD_CHART_VERSION" -n linkerd-cni --create-namespace --wait
kubectl -n linkerd-cni rollout status daemonset/linkerd-cni --timeout=180s
CNI_ENABLED=true
linkerd check --pre --linkerd-cni-enabled
# Use --linkerd-cni-enabled=true for CLI control-plane installation,
# or --set cniEnabled=true for the control-plane Helm chart.
```

验证节点 CNI 配置/二进制目录和已安装插件行为。默认值为 /etc/cni/net.d 和 /opt/cni/bin，不是通用平台路径。所选控制平面 chart 使用 cniEnabled；渲染必须显示预期省略 linkerd-init。

没有 Linkerd CNI 时，正常初始化容器重定向路径需要 NET_ADMIN 能力。使用 CNI 后，这项工作移到节点插件。此版本默认启用原生 Sidecar，因此诊断注入时同时检查 containers 和 initContainers。发布的 Identity Deployment 有意使用普通代理并禁用启动等待；不要把该引导例外归为注入失败。禁用原生 Sidecar 会改变初始化容器网络/启动顺序；绕过 UID 不是通用安全修复。

对于 Cilium kube-proxy 替代，Linkerd 文档设置使用 socketLB.hostNamespaceOnly=true，使 Pod 流量保留 Service 地址以便发现。链接 Linkerd CNI 还需要 cni.exclusive=false。与主 CNI 所有者审核这些更改，不要盲目替换配置。

### 现有 EKS 集群

使用现有受支持集群，对照 Linkerd 分支和 EKS 可用性验证版本。旧 EKS 1.28 创建命令已不适合作为当前指导。此 Linux 节点流程假定兼容 EC2 节点；Fargate 无法运行这里的 Linkerd CNI DaemonSet，因此不是可互换目标。

若准备专用 kubeconfig：

```bash
: "${EKS_CLUSTER_NAME:?Set the intended existing cluster}"
: "${EKS_REGION:?Set its region}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --query 'cluster.{version:version,endpoint:endpoint}' --output json
aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --kubeconfig "$PWD/linkerd.kubeconfig" --alias linkerd-lab
export KUBECONFIG="$PWD/linkerd.kubeconfig"
kubectl config current-context
kubectl -n kube-system get daemonset aws-node   -o jsonpath='{.spec.template.spec.containers[*].image}'
```

更改集群前验证目标端点/上下文。标准 Linkerd 控制器使用 Kubernetes API 凭证；linkerd-destination 仅为发现 Service 不需要 IAM 角色。AWS API 权限属于实际调用方，如 Load Balancer Controller、EBS CSI 或遥测采集器，并使用其受支持 IRSA/Pod Identity 设置。

### EKS 仪表板和网络注意事项

旧互联网 ALB 示例在没有身份验证设计时发布管理仪表板。在组织认证入口配置并测试前，使用 localhost 管理。

Web Service 的 8084 端口有效。独立管理/就绪端口为 9994，chart 的就绪探针使用该端口 /ready。不要假定 UI 监听器具有相同健康语义。ALB 设计必须对齐目标健康、安全组、主机验证、证书所有权和身份验证；仅 TLS 证书不验证仪表板用户。

将安全组和 NetworkPolicy 规则限定到实际源/目标角色。组件端口表是诊断信息，不是要求向所有来源暴露代理指标或 webhook 端口。在实际集群验证 CNI 启动、DNS、准入、身份和跨节点路径。

## 安装验证

```bash
linkerd check
linkerd check --proxy -n my-app
linkerd viz check
linkerd multicluster check
kubectl -n linkerd get pods,services,pdb -o wide
kubectl -n linkerd-viz get pods,services -o wide
```

仅对已安装扩展运行扩展检查。check --proxy 检查数据平面；不表示“包含所有扩展”。这些检查不验证应用业务逻辑。

对于示例应用，应用前审核固定应用清单，仅为所选命名空间加注解，并重建目标工作负载。可变 emojivoto URL 加对全部在线 Deployment 的导出再应用，不是可复现应用输入。确认镜像/架构、Service 端口、就绪和实际 HTTP/TCP 结果。

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
linkerd viz stat deploy/my-app -n my-app
linkerd viz top deploy/my-app -n my-app
```

将 my-app 替换为实际命名空间和 Deployment。metrics/tap/top 依赖配置的扩展和受支持协议；不证明全部流量加密或全部业务操作成功。

## Linkerd 升级

### 升级规划

选择确切目标 CLI/chart，审核发布说明、兼容性、受支持版本偏差和当前健康。此目标不承诺可从所有历史 2.14/2.16 安装直接升级；遵循必需中间升级和厂商指南。Edge 标签不是语义版本保证。通过各自所有者依次升级 CLI、CRD/控制平面、已安装扩展，最后升级数据平面代理。

现有安装使用 check 和 check --proxy。check --pre 是包含命名空间/设置假设的全新安装预检，不替代升级规划。任何升级前保留当前信任凭证并审核已移除 CRD 版本。

### CLI 管理的安装

```bash
# First install/verify the selected target CLI and review the supported upgrade path.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds > linkerd-crds-upgrade.yaml
kubectl apply -f linkerd-crds-upgrade.yaml
linkerd upgrade > linkerd-upgrade.yaml
# Review retained configuration and credentials before applying.
kubectl apply -f linkerd-upgrade.yaml
linkerd check
linkerd viz install > linkerd-viz-upgrade.yaml
kubectl apply -f linkerd-viz-upgrade.yaml
linkerd viz check
# Likewise review/install the selected multicluster extension if present.
linkerd prune > linkerd-obsolete.yaml
# Review ownership and contents before any kubectl delete -f linkerd-obsolete.yaml.
```

扩展使用 install 命令渲染更新，没有 viz upgrade 子命令。help 命令返回 0 仍可能是父命令帮助；检查可用命令列表和生成资源内容。删除前审核 prune 输出。多集群控制器更新可能需要通过受支持流程重新链接。

### Helm 管理的安装

```bash
umask 077
helm get values linkerd-control-plane -n linkerd > current-values.yaml
helm get manifest linkerd-control-plane -n linkerd > current-manifest.yaml
# Migrate intentional overrides to reviewed-values.yaml; preserve current trust credentials.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --wait
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd \
  --reset-values -f reviewed-values.yaml --wait --timeout 10m
# Upgrade each installed extension with its own reviewed values and pinned chart.
linkerd check
```

已审核 values 必须包含有意设置的 HA/CNI 及**现有**信任/签发者配置或受支持外部 Secret 引用。不保留这些输入就使用 --reset-values，可能改变行为或失败；--reuse-values 可能保留过时设置。比较目标默认值和覆盖，绝不要仅因常规升级重新生成 CA。

### 数据平面更新

按可用性策略每次更新一个目标工作负载：

```bash
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, proxies: ([.spec.containers[]?, .spec.initContainers[]?] | map(select(.name == "linkerd-proxy") | {image, restartPolicy}))}'
```

stat 是流量统计命令，不是代理镜像版本清单。上方同时检查普通和原生 Sidecar 位置。重建后检查相关版本偏差指南及实际就绪/流量。

## 故障排除

### 准入和资源

```bash
kubectl -n linkerd get service linkerd-proxy-injector
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config -o yaml
kubectl -n linkerd get networkpolicy
kubectl -n linkerd get events --sort-by='.lastTimestamp'
: "${LINKERD_POD:?Set a control-plane Pod name}"
kubectl -n linkerd describe pod "$LINKERD_POD"
```

注入失败可能涉及 CA 包、webhook 选择/网络、被拒绝配置或 Pod 安全；不总是 Service 连接问题。Pending 可反映反亲和性、污点、卷、配额或资源。更改资源 limits 或安全设置前检查实际事件。

### 证书

默认安装中，信任根位于 **ConfigMap**，签发者签名密钥/证书位于 Secret：

```bash
set -euo pipefail
kubectl -n linkerd get configmap linkerd-identity-trust-roots \
  -o jsonpath='{.data.ca-bundle\.crt}' > trust-bundle.pem
openssl crl2pkcs7 -nocrl -certfile trust-bundle.pem |
  openssl pkcs7 -print_certs -text -noout
kubectl -n linkerd get secret linkerd-identity-issuer -o json |
  jq -er '.data["crt.pem"] // .data["tls.crt"]' |
  base64 -d | openssl x509 -noout -dates
```

默认签发者格式使用 crt.pem；配置的 kubernetes.io/tls 集成使用 tls.crt。检查配置方案，不要假定所有签发者 Secret 字段相同。自定义信任集成可改变存储所有者。检查全部信任证书、时钟/有效期、签发者可用性和身份错误；避免无计划根替换。

### 组件和代理日志

```bash
kubectl -n linkerd logs deployment/linkerd-destination -c destination
kubectl -n linkerd logs deployment/linkerd-destination -c policy
kubectl -n linkerd logs deployment/linkerd-identity -c identity
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector
: "${APP_POD:?Set an application Pod name}"
kubectl -n my-app logs "$APP_POD" -c linkerd-proxy
linkerd diagnostics proxy-metrics "$APP_POD" -n my-app
```

使用安装版本实际组件/容器名。删除或替换 Pod 前保留相关日志。

## 卸载

### 先移除应用代理

为失去网格传输策略、路由和可观测性做计划。通过工作负载所有者移除注入来源和手动代理配置，重建工作负载，并在移除控制平面前验证两个容器位置：

```bash
# Choose the actual application namespace/Deployment and review all injection sources.
kubectl annotate namespace my-app linkerd.io/inject-
# Also remove any Pod-template injection override/manual proxy using its manifest owner.
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, containers: ([.spec.containers[]?, .spec.initContainers[]?] | map(.name))}'
```

仅移除命名空间注解不会覆盖 Pod 模板注解或移除手动注入代理。退出网格后验证应用连接和安全。不要使用 force 绕过剩余注入工作负载。

### CLI 管理的移除

```bash
# Only after applications are unmeshed and extension dependencies are removed.
linkerd viz uninstall > remove-viz.yaml
linkerd multicluster uninstall > remove-multicluster.yaml
# Inspect each manifest and remove only the extensions actually installed via CLI.
kubectl delete -f remove-viz.yaml
kubectl delete -f remove-multicluster.yaml
linkerd uninstall > remove-linkerd.yaml
# This includes namespace-scoped resources and cluster-wide CRDs.
kubectl delete -f remove-linkerd.yaml
```

仅移除已安装扩展。生成的控制平面移除包含 CRD；删除 CRD 会删除自定义资源实例。清点并备份必须保留的内容。这不只是删除 Deployment。

### Helm 管理的移除

```bash
# Only the releases actually installed through Helm, after unmeshing applications.
helm uninstall linkerd-viz -n linkerd-viz
helm uninstall linkerd-multicluster -n linkerd-multicluster
helm uninstall linkerd-control-plane -n linkerd
# Inventory/back up CR instances before removing the CRDs.
helm uninstall linkerd-crds -n linkerd
```

若安装了 Linkerd CNI，在没有工作负载依赖后单独遵循节点插件清理，并验证主 CNI 完整。仅在验证所有权和剩余内容后删除命名空间，不要无条件清理四个命名空间。

## 后续步骤

- [架构](02-architecture.md)
- [流量管理](03-traffic-management.md)
- [安全和证书生命周期](04-security.md)
- [可观测性](05-observability.md)
- [多集群](06-multi-cluster.md)
- [安装测验](../../quizzes/service-mesh/linkerd/installation.md)

## 参考资料

- [发布模型](https://linkerd.io/releases/)和 [edge-26.9.1 制品](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1)
- [Kubernetes 矩阵](https://linkerd.io/docs/reference/k8s-versions/)和 [Gateway API 兼容性](https://linkerd.io/docs/features/gateway-api/)
- [Helm 安装](https://linkerd.io/docs/tasks/install-helm/)和[官方 edge chart 索引](https://helm.linkerd.io/edge/index.yaml)
- [高可用行为](https://linkerd.io/docs/features/ha/)和[集群/Cilium 配置](https://linkerd.io/docs/reference/cluster-configuration/)
- [证书生成](https://linkerd.io/docs/tasks/generate-certificates/)和 [Smallstep create 参考](https://smallstep.com/docs/step-cli/reference/certificate/create/)
- [CNI](https://linkerd.io/docs/features/cni/)、[升级](https://linkerd.io/docs/tasks/upgrade/)和[卸载](https://linkerd.io/docs/tasks/uninstall/)
- [AWS Load Balancer Controller Service 设置](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)和 [EKS Fargate 约束](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
