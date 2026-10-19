# Linkerd 安装与设置

> **最后更新**：October 16, 2026 · 公共 CLI：edge-26.10.1 · 对应 chart：2026.10.1

本指南介绍受控的 Kubernetes 安装、Helm/CLI 所有权、高可用性（HA）、可选扩展、EKS 注意事项、升级和移除。上游项目发布 edge 构件；稳定版发行版的安装/支持指南因供应商而异。像 2.20 这样的里程碑版本并不意味着上游提供 stable-2.20.0 下载。

以下命令使用 Bash，除非标注为 PowerShell。请使用预期的 kubeconfig/context 和安装所有者。CLI 与 Helm 安装流程是**替代方案**：不要将 CLI 生成的资源应用到由 Helm 管理的 release 上。离线检查不能确定生产环境的容量配置、存储、网络强制执行或应用兼容性。

## 先决条件

### Kubernetes 和 Gateway API

| Track/版本 | Kubernetes 依据 | Gateway API 依据 |
|---|---|---|
| Linkerd 2.20 里程碑版本/发行版 | 已发布的矩阵为 1.31–1.35；请确认供应商支持情况 | 已发布的矩阵为 1.2.1–1.5.1 |
| 此处使用的公共 edge-26.10.1 | 已发布 CLI 的最低版本为 1.31.0；edge-26.8.2 提高了经过测试的最高版本至 1.36 | 已发布版本支持 1.5.1；本指南使用其标准 bundle |
| 历史版本 2.16 | 已发布的矩阵为 1.22–1.29 | 不建议用于当前安装 |
| 历史版本 2.15 / 2.14 | 已发布的范围分别为 1.22–1.29 / 1.21–1.28 | 请查看对应发行版；不要推断其适用于“以及之后的每个 Kubernetes 版本” |

CLI 的最低版本检查并不是最高支持版本检查。通过 check --pre 并不能证明其兼容新发布的 Kubernetes 或 Gateway API 版本。对于 EKS，还应检查在那里可用的版本和支持期限。本次审计中的 Helm 验证使用了 Kubernetes 1.35 的 capabilities。

### 容量和平台

不要依据一条通用的 100m CPU/200Mi 声明来确定整个控制平面的容量。请检查 controller、policy 容器、代理、init 容器和扩展的渲染后 requests/limits；并测量实际流量和连接负载。HA 要求至少有三个符合条件的节点，以满足其必需的节点反亲和性，同时还要有足够容量支持滚动更新。跨 Zone 分布是偏好设置，并不保证分布在三个不同 Zone。

本指南面向运行 Linux 的 Kubernetes 节点。下载 Windows CLI 并不能证明支持 Windows 工作负载配置。请单独检查所选发行版对工作负载/平台的支持情况。对于 Cilium kube-proxy replacement，请查看 socketLB.hostNamespaceOnly；将 Linkerd CNI 与 Cilium 链接使用时，cni.exclusive 必须允许其他插件。

### 网络路径和预检

请验证源/目标路径，而不只是列出一组要对所有地方开放的端口：

| 路径 | 固定版本渲染中的默认示例 |
|---|---|
| API server 到 admission 服务 | Service 443 到 injector/SP-validator 8443 和 policy-validator 9443 |
| Proxy 到控制平面 | Identity 8080、destination 8086、policy 8090 |
| 已纳入网格的应用流量 | Proxy 入站 4143，以及实际的应用/Service 路径 |
| 安装 Viz 时 | Tap API server 8089、tap gRPC 8088、metrics API 8085、Prometheus 9090 |
| 诊断 | Proxy metrics 4191；Web UI 8084，另有 Web 管理/就绪端口 9994 |

这些是组件端口，并不是不受限制的安全组规则集合。还要考虑 DNS、Kubernetes API 以及所选 CNI/网络策略的行为。检查实际的 Service targetPorts 和 webhook 配置。

```bash
LINKERD_CHART_VERSION=2026.10.1
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

只有在需要时才应用 Gateway API bundle；应用前请检查现有 CRD 的所有权以及所有使用它们的 controller。如果选择 Linkerd CNI，应先安装/验证它，再安装控制平面，并使用下文介绍的 CNI 感知检查。请查看实际检查输出和退出状态；旧示例中冗长的“全部通过”输出并不是针对你的集群得出的结果。

## 安装 Linkerd CLI

### 固定版本的 Linux/macOS 二进制文件

以下命令会选择确切的已发布构件，并将其 SHA256 与官方发行版元数据进行比较。它只会在当前 shell 中修改 PATH：

```bash
set -euo pipefail
LINKERD_VERSION=edge-26.10.1
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64) suffix=linux-amd64; expected=66d634f5318c8016f0b5face246a688964b6e2c86d6c3be34be68ab9fcd2a8cc ;;
  Linux/aarch64|Linux/arm64) suffix=linux-arm64; expected=431989b15b48acfd6e344ff16a0d3505574c0cce551a2d4aeae82246ce65a5cc ;;
  Darwin/x86_64) suffix=darwin; expected=bcf7acaf8a946cffd262d075dcaa50e9b583d8191bfa6e1c20fd3593fe6db524 ;;
  Darwin/arm64) suffix=darwin-arm64; expected=abaaaeba9334feae7c1f16dd43a6f85b6051eadf49425f0ae30cbf16eba29f70 ;;
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

列出的构件适用于 Linux amd64/arm64 和 macOS Intel/Apple Silicon。不要因为安装脚本中有通用 ARM 分支，就假设此发行版提供 32 位 ARM 二进制文件。本次审计实际运行了原生 Linux arm64 CLI；其他平台的二进制文件则依据官方发行版元数据进行了确认。

### 官方安装程序替代方案

旧版 run.linkerd.io/install 脚本已弃用，且安装的是 edge，而非 stable。当前安装程序接受环境变量 LINKERD2_VERSION；旧命令 sh --version stable-2.16.0 并不会选择一个受支持的上游 stable 构件。

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://run.linkerd.io/install-edge -o install-linkerd.sh
# Inspect the downloaded script before execution.
LINKERD2_VERSION=edge-26.10.1 INSTALLROOT="$PWD/linkerd-installer" sh ./install-linkerd.sh
export PATH="$PWD/linkerd-installer/bin:$PATH"
linkerd version --client
```

请根据发行版兼容性矩阵选择 Gateway API bundle。安装程序完成消息中包含其自身的版本示例；本指南在检查所选发行版后固定使用 1.5.1。软件包管理器和供应商发行版可能会选择不同版本；请验证其构件来源和版本，不要假设使用 Homebrew/Chocolatey 就意味着采用了本指南固定的发行版。本指南不需要修改 shell 配置文件。

### Windows 二进制文件

发行版构件名为 windows.exe，而不是 windows-amd64.exe：

```powershell
$ErrorActionPreference = "Stop"
$LinkerdVersion = "edge-26.10.1"
$ExpectedSha256 = "7f6d3b1183bfed8d555e55fbb4934695e1376c8a3fab77a5d3f8954ec0306dc7"
$Download = Join-Path (Get-Location) "linkerd.download.exe"
$Url = "https://github.com/linkerd/linkerd2/releases/download/$LinkerdVersion/linkerd2-cli-$LinkerdVersion-windows.exe"
Invoke-WebRequest -Uri $Url -OutFile $Download
if ((Get-FileHash -Algorithm SHA256 $Download).Hash.ToLowerInvariant() -ne $ExpectedSha256) {
    throw "Linkerd release checksum mismatch"
}
Move-Item $Download (Join-Path (Get-Location) "linkerd.exe") -Force
.\linkerd.exe version --client
```

其余 Bash 示例需要使用合适的 shell（例如配置好的 WSL 环境），或者转换为原生 PowerShell 命令。本次审计未执行 PowerShell，也未测试 Windows 工作负载。

## 安装控制平面

### CLI 安装

对于由 CLI 管理的新安装，应先应用 Linkerd CRD，再生成/安装控制平面：

```bash
linkerd install --crds > linkerd-crds.yaml
kubectl apply -f linkerd-crds.yaml
linkerd install --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-control-plane.yaml
# Review the generated resources and trust credentials before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

这些命令会生成清单；实际安装由 kubectl 执行。CLI 默认生成的信任锚和 issuer 凭据有固定有效期，需要规划轮换。共享信任的多集群配置需要有意提供凭据，而不是在每个集群上分别生成根证书。

### Helm 安装

Helm 提供可重复的 release/values 工作流。chart 版本应与 CLI tag 分开固定：

```bash
helm repo add linkerd-edge https://helm.linkerd.io/edge
helm repo update linkerd-edge
helm show chart linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
```

对应的公共 chart 包括 2026.10.1 版本的 linkerd-crds、linkerd-control-plane、linkerd-viz、linkerd-multicluster 和 linkerd2-cni。当前核心 chart 的 appVersion 为 edge-26.10.1。不要安装一个未固定版本的旧 stable 仓库 chart，却假设它与此 CLI 匹配。

#### 信任锚和 issuer

Helm 需要信任锚证书以及 issuer 证书/私钥，或者需要有意配置受支持的外部 issuer-secret 集成。它不要求上传根 CA 私钥。

请使用已安装的 [Smallstep CLI](https://smallstep.com/docs/step-cli/installation/) 及其已发布的证书创建接口。这个 ECDSA P-256 示例保留了原演示中的有效期，但修正了 --not-after 之后错误的续行：

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

安装前请检查证书链、算法和有效期。根私钥应留在 Kubernetes 之外；下文只会提供公有信任锚和 issuer 签名凭据。--no-password/--insecure 会创建未加密的本地密钥，因此示例使用了访问受限的目录/umask。生产 PKI 需要经批准的密钥存储和轮换流程。本次审计根据官方文档检查了这些标志，但没有实际运行 Smallstep 证书生成命令。

#### 自定义 values

将以下内容保存为 linkerd-values.yaml。这些是容量配置示例，并非对工作负载的保证：

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

proxy.logLevel 和 proxy.logFormat 是实际的嵌套键。虽然基础 values 文件中并未全部列出，但 destinationResources、identityResources 和 proxyInjectorResources 均受支持；打包的 HA 文件和模板会使用它们。旧版 namespace.labels map 和顶层 proxyLogLevel/proxyLogFormat 并未被使用。默认情况下，chart 会将 header/request 日志抑制规则追加到配置的 proxy 日志选择器中；请检查最终的环境变量值。

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

生成的清单和 Helm values 备份可能包含 issuer 私钥。请限制其访问权限，不要将它们粘贴到诊断报告中。后续升级时应由相同的 release/凭据所有者持续管理。

## 高可用性（HA）安装

使用固定版本 chart 随附的 values-ha.yaml：

```bash
helm pull linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
tar -xOf "linkerd-control-plane-$LINKERD_CHART_VERSION.tgz" \
  linkerd-control-plane/values-ha.yaml > linkerd-ha.yaml
# For the Helm render/install above, use:
# -f linkerd-ha.yaml -f linkerd-values.yaml
# For a new CLI-owned installation, render with:
linkerd install --ha --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-ha-rendered.yaml
```

对于 Helm，请在渲染和安装时都将指定的 HA 文件放在自定义 values **之前**。请确认后续覆盖项不会禁用必需的 HA 设置。

打包的配置会为关键组件启用三个副本、必需的节点隔离、偏好的 Zone 隔离、PDB 以及 Fail admission-webhook 策略。这些是冗余的服务实例，并非由三个成员组成的共识仲裁组。可用性还取决于 API server/网络访问、凭据、容量和应用本身。

以前手写的 destination.replicas/identity.resources/proxyInjector.resources 字段没有配置预期的容器。根级 podDisruptionBudget map 不会创建任何 PDB，根级 topologySpreadConstraints 也未被使用。对旧示例进行离线渲染后发现有三个副本，但 controller 资源设置缺失，且没有 PDB。请使用实际打包的配置文件并检查渲染结果。

```bash
kubectl -n linkerd get pods -o wide
kubectl -n linkerd get pdb
kubectl -n linkerd get deployments -o yaml
```

如果符合条件的节点少于三个，必需的反亲和性可能导致副本处于 Pending 状态。在依赖 HA 之前，请检查 admission Fail 行为和中断情况；不要将放宽 webhook 策略作为通用的可用性修复方法。


## 安装扩展

### Viz：dashboard 和 metrics

对于由 CLI 管理的扩展：

```bash
linkerd viz install > linkerd-viz.yaml
# Review the optional extension and its metrics backend.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

对于 Helm，将以下内容保存为 viz-values.yaml，并检查渲染后的 PVC、Deployment 和资源设置：

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

所选 chart 仅在存在 persistence **map** 时支持持久化。它不会使用 persistence.enabled 作为开关。其 PVC 模板要求设置 accessMode；旧示例省略了该项，渲染出的 access mode 为 null。省略该 map 时会使用 emptyDir。gp3 StorageClass 是一个示例先决条件，并非由 Viz 创建；在 EKS 上请验证 EBS CSI driver、权限和卷拓扑。

内置 Prometheus 只有一个副本；启用持久化后会选择 Recreate Deployment 策略。PVC 可在合适的 Pod 替换期间保留数据，但不能让 metrics 存储实现 HA，也不能保证服务不中断。Chart 2026.10.1 默认使用 Prometheus v2.55.1，保留时间为六小时。请明确选择后端维护、保留期限和可用性要求。

对于已经配置好的外部 Prometheus，以下是一个**替代方案** values 文件：

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
```

切换之前，请配置外部服务器的 Linkerd 抓取/重标记规则和访问策略。请验证实际的 Viz 查询和 metrics，而不只是 HTTP 就绪端点。dashboard、tap 和 metricsAPI 的资源设置均受支持。grafana.enabled 并不是 Deployment 开关：此 chart 提供 Grafana 链接设置，供单独管理的 Grafana 使用。

初次使用时请通过 localhost dashboard 命令访问。dashboard.enforcedHostRegexp 会验证 Host 值，但它不是用户身份验证；该值为空时会采用 chart 默认的主机限制。组织的 ingress 需要单独配置身份验证/授权、经批准的网络暴露方式以及允许的主机。

### 分布式追踪

edge-26.10.1 没有 linkerd jaeger 子命令。公共 linkerd-jaeger chart 的历史版本停留在 2025.9.4；它不是与 2026.10.1 匹配的扩展。请将过时的安装/检查/升级/卸载说明替换为单独管理的 collector/backend，以及所选的 proxy tracing 配置。

Tracing 需要传入 trace context、应用传播以及兼容的 collector/export 协议。Viz 拓扑图或 metrics 图表并不是分布式 trace。完整数据路径请参阅[可观测性指南](05-observability.md)和[官方 tracing 文档](https://linkerd.io/docs/features/distributed-tracing/)。本安装审计并未声称未经测试的 collector/Jaeger 部署能够端到端正常工作。如果旧安装中已有 linkerd-jaeger release，请清点并迁移其数据，然后通过原有所有者将其退役；当前 CLI 无法管理这个已移除的扩展。

### 多集群

CLI 可以渲染基础扩展：

```bash
linkerd multicluster install > linkerd-multicluster.yaml
# Review network exposure, shared trust and actual gateway configuration first.
kubectl apply -f linkerd-multicluster.yaml
linkerd multicluster check
```

应用之前，请根据网络情况选择适当的 gateway 暴露方式。仅安装扩展并不会连接集群、创建共享信任或授予远程 Kubernetes API 访问权限。

对于使用 **AWS Load Balancer Controller** 的 EKS 部署，以下示例选择内部 NLB，并保留到 Linkerd gateway 的 TCP 传输：

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

将内容保存为 multicluster-values.yaml，然后使用 Helm 替代方案：

```bash
helm install linkerd-multicluster linkerd-edge/linkerd-multicluster \
  --version "$LINKERD_CHART_VERSION" -n linkerd-multicluster --create-namespace \
  -f multicluster-values.yaml --wait --timeout 10m
```

loadBalancerClass 用于选择预期的 controller。EKS Auto Mode 使用不同的 class/配置契约；不要混用这些假设，也不要随意更改现有 Service 的所有权。确保远程网络可以解析/访问内部 gateway 及其探测路径。不要在无关的 ACM listener 处终止 Linkerd 的传输 mTLS。

固定版本的 chart 不会使用 gateway.resources。Gateway proxy 资源来自注入配置；请检查最终生成的 Pod，不要假设被忽略的 values 区块更改了其 limits。此 chart 附带的 HA 覆盖文件使用 gateway.replicas 和反亲和性。

当前 edge 远程凭据不接受 exec auth provider。请使用[多集群指南](06-multi-cluster.md)支持的凭据流程，并验证生成的 service-mirror controller/版本及最小权限 API 访问。

## CNI 和 Amazon EKS 配置

### 可选的 Linkerd CNI

Linkerd CNI 会与主 CNI 链接使用；它不会取代 Amazon VPC CNI 或 Cilium。在控制平面和已纳入网格的工作负载使用启用 CNI 的配置**之前**，它必须在适用节点上就绪：

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

请验证节点的 CNI 配置/二进制文件目录以及已安装插件的行为。默认路径为 /etc/cni/net.d 和 /opt/cni/bin，但并非所有平台都使用这些路径。所选控制平面 chart 会使用 cniEnabled；渲染结果应显示 linkerd-init 被按预期省略。

未使用 Linkerd CNI 时，常规 init-container 重定向路径需要 NET_ADMIN capability。启用 CNI 后，这项工作由节点插件执行。此发行版默认启用 native sidecar，因此诊断 proxy 注入时请同时检查 containers 和 initContainers。已发布的 Identity Deployment 会有意使用常规 proxy 并禁用启动等待；不要将此引导例外判断为注入失败。禁用 native sidecar 会改变 init-container 的网络/启动顺序；绕过 UID 并不是通用的安全修复方法。

对于 Cilium kube-proxy replacement，Linkerd 文档中的配置使用 socketLB.hostNamespaceOnly=true，使 Pod 流量保留 Service 地址，以便进行服务发现。链接使用 Linkerd CNI 时，还需要设置 cni.exclusive=false。请与主 CNI 的所有者共同审查这些更改，不要盲目替换其配置。

### 现有 EKS 集群

请使用现有的受支持集群，并根据 Linkerd track 和 EKS 可用情况验证其版本。以前用于创建 EKS 1.28 的命令已不再适合作为当前指南。此 Linux 节点流程假设节点由兼容的 EC2 实例提供支持；Fargate 无法运行此处所示的 Linkerd CNI DaemonSet，因此不能作为此流程的可互换目标。

如果要准备专用 kubeconfig：

```bash
: "${EKS_CLUSTER_NAME:?Set the intended existing cluster}"
: "${EKS_REGION:?Set its region}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --query 'cluster.{version:version,endpoint:endpoint}' --output json
aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --kubeconfig "$PWD/linkerd.kubeconfig" --alias linkerd-lab
export KUBECONFIG="$PWD/linkerd.kubeconfig"
kubectl config current-context
kubectl -n kube-system get daemonset aws-node   -o jsonpath='{.spec.template.spec.containers[*].image}'
```

进行集群变更前，请确认 endpoint/context 符合预期。标准 Linkerd controller 使用 Kubernetes API 凭据；linkerd-destination 发现 Services 并不需要 IAM role。AWS API 权限应授予实际调用方，例如 Load Balancer Controller、EBS CSI 或 telemetry collector，并采用其支持的 IRSA/Pod Identity 配置。

### EKS dashboard 和网络注意事项

旧版面向互联网的 ALB 示例发布了管理 dashboard，却没有设计身份验证方案。在配置并测试好经过身份验证的组织 ingress 之前，请通过 localhost 进行管理。

Web Service 的 8084 端口有效。其单独的管理/就绪端口为 9994，chart 在该端口上的就绪探测路径为 /ready。不要认为 UI listener 上的健康检查语义相同。ALB 设计必须协调目标健康检查、安全组、主机验证、证书所有权和身份验证；仅有 TLS 证书并不能验证 dashboard 用户的身份。

安全组和 NetworkPolicy 规则应按实际源/目标角色进行限制。组件端口表是诊断信息，并不是要求向所有来源暴露 proxy metrics 或 webhook 端口。请在实际集群中验证 CNI 启动、DNS、admission、identity 和跨节点路径。

## 安装验证

```bash
linkerd check
linkerd check --proxy -n my-app
linkerd viz check
linkerd multicluster check
kubectl -n linkerd get pods,services,pdb -o wide
kubectl -n linkerd-viz get pods,services -o wide
```

只对已安装的扩展运行检查。check --proxy 会检查数据平面；它并不表示“检查所有扩展”。这些检查无法验证应用业务逻辑。

对于示例应用，请先查看固定版本的应用清单，再应用它；只为选定的 namespace 添加注解，并重新创建预期工作负载。可变的 emojivoto URL 加上对每个运行中的 Deployment 进行往返导出，并不是可复现的应用输入。请确认镜像/架构、Service 端口、就绪状态以及实际 HTTP/TCP 结果。

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
linkerd viz stat deploy/my-app -n my-app
linkerd viz top deploy/my-app -n my-app
```

请将 my-app 替换为实际的 namespace 和 Deployment。Metrics/tap/top 依赖已配置的扩展和受支持的协议；它们不能证明所有流量都已加密，也不能证明所有业务操作均已成功。

## 升级 Linkerd

### 升级规划

选择确切的目标 CLI/chart，审查发行说明、兼容性、支持的版本偏差和当前健康状态。此处显示的目标版本并不意味着可以从所有历史 2.14/2.16 安装直接升级；请遵循所需的中间升级步骤和供应商指南。Edge tag 不提供语义化版本保证。请分别通过各自的所有者升级 CLI、CRD/控制平面、已安装的扩展，最后再升级数据平面 proxy。

对现有安装使用 check 和 check --proxy。check --pre 是针对新安装的预检，其中包含 namespace/设置假设，不能代替升级规划。请保留当前信任凭据，并在升级前检查已移除的 CRD 版本。

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

扩展提供用于渲染更新的 install 命令，而没有 viz upgrade 子命令。即使帮助命令返回退出码 0，它也可能只是父命令的帮助信息；请检查可用命令列表和生成的资源内容。删除任何内容前，请先检查 prune 的输出。多集群 controller 更新可能需要通过受支持的工作流重新建立链接。

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

审核后的 values 必须包含有意设置的 HA/CNI 配置，以及**现有的**信任/issuer 配置或受支持的外部 secret 引用。如果不保留这些输入而使用 --reset-values，可能会改变行为或导致失败；--reuse-values 则可能保留过时的设置。请比较目标默认值和覆盖项；切勿仅仅为了常规升级而重新生成 CA。

### 数据平面更新

根据可用性策略，每次更新一个预期工作负载：

```bash
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, proxies: ([.spec.containers[]?, .spec.initContainers[]?] | map(select(.name == "linkerd-proxy") | {image, restartPolicy}))}'
```

stat 是流量统计命令，并不是 proxy 镜像版本清单。上文会同时检查常规容器和 native sidecar 位置。请检查相关版本偏差指南，并在重新创建后确认实际就绪状态/流量。

## 故障排查

### Admission 和资源

```bash
kubectl -n linkerd get service linkerd-proxy-injector
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config -o yaml
kubectl -n linkerd get networkpolicy
kubectl -n linkerd get events --sort-by='.lastTimestamp'
: "${LINKERD_POD:?Set a control-plane Pod name}"
kubectl -n linkerd describe pod "$LINKERD_POD"
```

注入失败可能与 CA bundle、webhook 选择/网络、被拒绝的配置或 Pod 安全性有关，并不总是 Service 连通性问题。Pending 状态可能由反亲和性、污点、卷、配额或资源引起。请先检查实际事件，再更改资源限制或安全设置。

### 证书

在默认安装中，信任根位于 **ConfigMap** 中，而 issuer 签名密钥/证书位于 Secret 中：

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

默认 issuer 格式使用 crt.pem；配置了 kubernetes.io/tls 集成时则使用 tls.crt。请检查已配置的方案，不要假设每个 issuer Secret 都有相同字段。自定义信任集成可能会改变存储所有者。请检查所有信任证书、时钟/有效期、issuer 可用性和 identity 错误；避免未经规划就替换根证书。

### 组件和 proxy 日志

```bash
kubectl -n linkerd logs deployment/linkerd-destination -c destination
kubectl -n linkerd logs deployment/linkerd-destination -c policy
kubectl -n linkerd logs deployment/linkerd-identity -c identity
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector
: "${APP_POD:?Set an application Pod name}"
kubectl -n my-app logs "$APP_POD" -c linkerd-proxy
linkerd diagnostics proxy-metrics "$APP_POD" -n my-app
```

请使用已安装版本中的实际组件/容器名称。删除或替换 Pod 之前，请保留相关日志。

## 卸载

### 先移除应用 proxy

请规划好移除网格传输策略、路由和可观测性的影响。通过工作负载所有者移除注入来源和手动 proxy 配置，重新创建工作负载，并在移除控制平面前检查两种容器位置：

```bash
# Choose the actual application namespace/Deployment and review all injection sources.
kubectl annotate namespace my-app linkerd.io/inject-
# Also remove any Pod-template injection override/manual proxy using its manifest owner.
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, containers: ([.spec.containers[]?, .spec.initContainers[]?] | map(.name))}'
```

仅移除 namespace 注解并不能覆盖 Pod 模板上的注解，也不能移除手动注入的 proxy。解除网格后，请验证应用连通性和安全性。不要使用 force 绕过仍有注入工作负载的情况。

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

只移除已安装的扩展。生成的控制平面移除清单包含 CRD；删除这些 CRD 会删除其自定义资源实例。请清点并备份需要保留的内容。这不只是删除 Deployment。

### Helm 管理的移除

```bash
# Only the releases actually installed through Helm, after unmeshing applications.
helm uninstall linkerd-viz -n linkerd-viz
helm uninstall linkerd-multicluster -n linkerd-multicluster
helm uninstall linkerd-control-plane -n linkerd
# Inventory/back up CR instances before removing the CRDs.
helm uninstall linkerd-crds -n linkerd
```

如果安装了 Linkerd CNI，请在没有工作负载依赖它之后，另行遵循节点插件清理流程，并确认主 CNI 仍然完好。只有在验证所有权和剩余内容之后才删除 namespace，不要无条件清理四个 namespace。

## 后续步骤

- [架构](02-architecture.md)
- [流量管理](03-traffic-management.md)
- [安全与证书生命周期](04-security.md)
- [可观测性](05-observability.md)
- [多集群](06-multi-cluster.md)
- [安装测验](../../quizzes/service-mesh/linkerd/installation.md)

## 参考资料

- [发行版模型](https://linkerd.io/releases/)和[edge-26.10.1 构件](https://github.com/linkerd/linkerd2/releases/tag/edge-26.10.1)
- [Kubernetes 矩阵](https://linkerd.io/docs/reference/k8s-versions/)和[Gateway API 兼容性](https://linkerd.io/docs/features/gateway-api/)
- [Helm 安装](https://linkerd.io/docs/tasks/install-helm/)和[官方 edge chart 索引](https://helm.linkerd.io/edge/index.yaml)
- [HA 行为](https://linkerd.io/docs/features/ha/)和[集群/Cilium 配置](https://linkerd.io/docs/reference/cluster-configuration/)
- [证书生成](https://linkerd.io/docs/tasks/generate-certificates/)和[Smallstep create 参考](https://smallstep.com/docs/step-cli/reference/certificate/create/)
- [CNI](https://linkerd.io/docs/features/cni/)、[升级](https://linkerd.io/docs/tasks/upgrade/)和[卸载](https://linkerd.io/docs/tasks/uninstall/)
- [AWS Load Balancer Controller Service 设置](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)和[EKS Fargate 限制](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
