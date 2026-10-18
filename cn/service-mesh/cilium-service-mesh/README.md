# Cilium 服务网格概览

> **最后更新**：2026年10月16日 · Cilium/chart 1.20.3 · CLI 0.20.1 · Hubble CLI 1.20.2

Cilium 将 Kubernetes 网络、eBPF 策略/负载均衡以及可选的应用层代理功能结合在一起。选定的 L7 流量由 Cilium 的 Envoy 集成处理；移除每个应用的 sidecar 并不会移除代理、内核要求或运维组件。

## 架构与安全边界

![与 Istio sidecar 模式的逻辑对比：Cilium 使用 eBPF 数据通路，并将选定的 L7 流量重定向到共享 Envoy。这并不构成加密/性能保证，也不是 Istio ambient 模式的示意图。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-readme-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-readme-0.html)

Envoy 可以作为进程与 Cilium agent 一起运行，也可以作为单独管理的 `cilium-envoy` DaemonSet 运行。所选 chart 的常规渲染配置使用专用 DaemonSet。实际部署位置和 L7 跳数取决于启用的功能/策略；并非每个数据包都会经过 Envoy。

| 组件 | 作用 |
|---|---|
| Cilium agent | 节点数据通路、端点身份和策略执行 |
| Cilium operator | 所选模式下的 IPAM 和其他集群/控制器职责 |
| Envoy | 匹配 L7 策略、Ingress 和 Gateway API 处理 |
| Hubble | 流量观测；L7 记录需要相应的代理可见性 |
| Hubble Relay / UI | 用于聚合和可视化的附加组件 |
| SPIRE（如已配置） | beta 双向认证功能的身份基础设施 |

### 双向认证不会自动加密流量

Cilium 1.20.3 将**带外双向认证标记为 beta 且尚未完成**。其基于 mTLS 的身份握手在 Cilium 安全身份之间通过 agent 带外进行。这并不会像 Istio 或 Linkerd 工作负载代理那样，使用相同的 TLS 传输模型封装每个应用连接。

WireGuard/IPsec 是各自独立的加密机制，具有各自支持的模式和适用范围。WireGuard 不是 TLS，仅启用 SPIRE 并不会加密应用数据，也不会为每个端点启用认证规则。所选版本还说明，双向认证与 ClusterMesh 或外部服务网格 mTLS 方案不兼容。

Cilium 1.20.3 还提供独立的 [ztunnel 透明加密 beta](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/network/encryption-ztunnel.rst)，通过 `encryption.type: ztunnel` 选择。它提供 TCP 工作负载 mTLS 和命名空间注册功能；通信双方都必须注册。它不支持 ClusterMesh 和使用 host network 的 Pod，且发布的指南警告，此路径上普通 L4 策略无法生效，除非目标是 HBONE 端口 15008。这是一种独立的部署选择，有其自身的 CA/引导要求。

在采用此 beta 路径之前，请查看[安全指南](03-security.md)以及已发布的安全模型/限制。应将路由、认证、授权和加密视为不同的需求。

Cilium 也可以为 Istio 部署提供底层 CNI。这种网络集成并不意味着二者的认证机制可以互换；请查看特定模式下的 socket 负载均衡、CNI 共存和 L7 策略归属。

## 能力与实测成本对比

| 主题 | Cilium | Istio | Linkerd |
|---|---|---|---|
| 数据平面模型 | eBPF 加共享 Envoy，用于选定的 L7 工作 | sidecar 模式，或 ambient ztunnel/waypoint 角色 | 每个 Pod 配置代理，包括 native sidecar 部署方式 |
| Pod 网络 | 根据模式提供 CNI 或与 CNI 链接 | 需要底层 Pod 网络；其 CNI 会重定向网格流量 | 需要底层 Pod 网络；可选 CNI 会重定向网格流量 |
| 策略 | Kubernetes/Cilium 网络策略和 L7 功能 | 网格授权/路由，另设网络策略层 | Server/route 授权和出站路由，不提供仅限 L4 的策略 |
| Gateway API | 可选启用的控制器和文档所述的一致性/功能 | Gateway 和网格路由角色 | 支持 Service/Server 父路由角色 |
| 安全性 | 带外认证，需单独配置加密；另有受限的 ztunnel mTLS beta | 工作负载网格 mTLS 加策略 | 工作负载网格 mTLS 加策略 |

没有任何产品能够脱离工作负载和配置，普遍适用地排出 CPU、内存或延迟高低。此前固定的每节点/每 Pod 数值以及 100-Pod 内存图并非注明来源的基准测试，而且未说明组件、节点数量和工作负载细节。请基于相同基线比较实测增量成本，并计入 agent/代理、控制器、遥测和身份基础设施。

当 Cilium 的网络模型和所需 L7 功能适合环境时，Cilium 可能是一个不错的选择，尤其是在该环境中已经运行 Cilium 的情况下。请评估 CNI 迁移、内核/平台支持、共享节点故障的影响、安全要求和现有策略依赖。对于金融/实时工作负载，“无 sidecar”或“eBPF”都不能证明能够达到特定的延迟或成本目标。

更全面的能力边界请参阅维护中的[服务网格比较](../istio/comparison/01-service-mesh-comparison.md)。

## 版本和平台先决条件

对于所选版本：

- Kubernetes 通用 e2e 兼容性列表为 **1.33–1.36**。已发布的 EKS CI 文件列出 **1.33–1.35**，默认版本为 1.35。这两者是不同的证据集；更新版本或提供商列表中未列出的组合需要单独验证。
- Helm chart 中宽松的 `kubeVersion >=1.21.0-0` 并不是经过测试的支持矩阵，而且不会自动涵盖更新的 Kubernetes 版本。
- 主机需要使用受支持的 AMD64/AArch64 Linux，通常要求内核版本为 5.10 或更高，或具备文档所述的等效回移补丁。L7 重定向和其他高级功能还有额外的内核/模块要求。
- 此 Cilium 版本对应的 Gateway API 参考版本为 **v1.6.3**。更改 CRD 前，请检查必需/可选的 CRD 以及 1.20 TLSRoute 升级说明；未经兼容性审查，不要直接换用目录中的最新版本。

```bash
cilium version --client
cilium version
cilium status --wait --wait-duration 5m
kubectl -n kube-system get daemonset cilium
# For the dedicated Envoy mode selected below:
kubectl -n kube-system get daemonset cilium-envoy
```

CLI 自身的版本与正在运行的 Cilium 镜像版本是不同的信息。请保留完整的状态输出和故障信息；grep 匹配到“Envoy”或“Hubble”并不能证明其已就绪。在嵌入式模式下，可能不会出现专用 Envoy DaemonSet。

### EKS 安装选项

| 模式/平台 | 必须注意的区别 |
|---|---|
| Cilium AWS ENI 模式 | Cilium 管理 ENI IPAM/原生路由；需要规划 IAM、路由以及节点/Pod 注册。通用的 1.20.3 ENI 参考文档将 IPv6 标记为 Beta，而 EKS 安装页面仍标注仅支持 IPv4；此处使用 IPv4 示例，并单独验证特定平台的 IPv6 先决条件/支持情况 |
| AWS VPC CNI 链接模式 | AWS VPC CNI 保留接口/IPAM 管理职责；Cilium 随后附加其数据通路；必须评估高级 L7/IPsec 的限制 |
| EKS Fargate | 不支持替代 CNI；必须使用 AWS VPC CNI |
| EKS Auto Mode | 不支持替代 CNI 和网络策略插件 |
| EKS Hybrid Nodes | 遵循 AWS 单独提供的 Cilium 版本/配置/功能指南，不要套用 EC2 ENI 参数 |

AWS 对 EC2 节点 CNI 的支持仅限 Amazon VPC CNI；其他兼容的 CNI 需要依赖各自的运维/供应商支持。不得根据通用 Cilium 兼容性表推断 Hybrid Nodes 的独立支持范围。

对于现有的 AWS VPC CNI 集群，一行 Helm 安装命令并不能构成迁移计划。应通过经过测试的流程处理 API 引导访问、kube-proxy 替换、CNI 管理权、IAM、节点就绪污点，以及重新创建现有的非托管 Pod。本次审查未创建集群，也未替换其 CNI。

## 启用所选功能

对于已正确安装 Cilium 的部署，请将以下功能叠加配置保存为 `cilium-mesh-features.yaml`：

```yaml
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```

受支持的 L7 标志是 `l7Proxy`；`proxy.enabled` 不能替代它。原生 chart 检查确认，`proxy.enabled:false` 时 L7 仍保持启用，而 `l7Proxy:false` 会将其禁用。

```bash
set -euo pipefail
umask 077
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
# Preview only: reviewed-cni-values.yaml must describe the existing intended CNI mode.
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system --kube-version 1.35.0 \
  -f reviewed-cni-values.yaml -f cilium-mesh-features.yaml \
  > cilium-mesh-rendered.yaml
```

此操作会预览一个兼容的 Kubernetes 版本示例，并与安装中经过审查的 CNI 配置合并。请检查结果，并由现有负责人按照该版本支持的升级流程操作。这并非完整的 CNI 安装，也不代表可以更改网络模式。

| 可选功能 | 其他要求 |
|---|---|
| Gateway API | kube-proxy 替换、L7 代理、所需的 v1.6.3 CRD，以及适当的负载均衡器/host-network 设计 |
| Ingress controller | 其受支持的配置和暴露模型；不会自动处理所有网格流量 |
| Hubble 指标 | 所选的指标系列和已配置的采集器；Relay/UI 本身不会创建 Prometheus |
| 双向认证 | beta 审查、显式启用、SPIRE/存储/连通性、适用的认证策略，以及单独评估的加密 |

对于**隔离的 beta 认证评估**，必须补上旧示例中缺少的顶层标志：

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      install:
        enabled: true
```

如果没有设置 `authentication.enabled:true`，chart 会拒绝 SPIRE 集成。所提供的 SPIRE server 默认使用持久化存储，因此必须预先配置合适的 PVC 供应机制。此片段不能建立生产级安全性、跨集群认证或应用流量加密。

## L7 策略与观测示例

在 `bookinfo` 中准备一个由 Cilium 管理、标签为 `app:productpage` 的 HTTP 应用，并在同一命名空间中准备一个由 Cilium 管理、标签为 `app:frontend` 的客户端。如果使用 Bookinfo，请部署其所有必需的应用依赖；只有 productpage 的 Deployment 并不构成完整的 Bookinfo 应用。请使用经过验证的镜像，并根据应用配置就绪条件。

以下策略会选中该端点，并允许所示客户端/方法/路径组合。它不会创建任何工作负载：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: productpage-l7
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: productpage
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: bookinfo
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: ^/productpage$
        - method: GET
          path: ^/health$
```

请先评估其他策略和预期的默认拒绝效果，再通过策略负责人应用此策略。此示例允许两个路径，并不允许完整浏览器工作流所需的所有静态资源或依赖项。认证/加密与此 L7 允许策略相互独立。

```bash
# Keep this terminal running; configure the intended kube context first.
cilium hubble port-forward --port-forward 4245

# In another terminal, use the selected Hubble CLI:
hubble status --server localhost:4245
hubble observe --server localhost:4245 --namespace bookinfo --protocol http --follow
# Service-name filters are an alternative to --namespace in this CLI.
hubble observe --server localhost:4245 --to-service bookinfo/productpage
```

所选 Hubble CLI 不允许同时使用 `--namespace` 和 `--to-service`。请使用命名空间观测，或使用带命名空间前缀的服务名称。L7 记录需要实际的匹配流量和代理可见性；在 L7 代理之前发生的丢弃可能需要更全面地检查流量/丢弃记录。没有观测到流量，并不能证明应用路径已被允许、拒绝或运行正常。

## 文档结构与参考资料

| 指南 | 范围 |
|---|---|
| [架构](01-architecture.md) | 数据通路、Envoy 和 API 模型 |
| [流量管理](02-traffic-management.md) | 路由和负载均衡 |
| [安全](03-security.md) | 策略、认证和加密边界 |
| [可观测性](04-observability.md) | Hubble 和指标 |
| [Ingress/Gateway](05-ingress-gateway.md) | 外部流量和 Gateway API |
| [最佳实践](06-best-practices.md) | 运维、迁移和验证 |

- [已发布的 Kubernetes 兼容性](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [系统要求](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [使用 Istio 的 Cilium 网络](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/istio.rst)
- [Envoy 模式](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/network/proxy/envoy.rst)
- [双向认证限制](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [Gateway API 先决条件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/gateway-api/installation.rst)
- [EKS ENI 要求](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)和 [AWS VPC CNI 链接模式](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/cni-chaining-aws-cni.rst)
- [EKS 替代 CNI](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)和 [Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium 1.20.3 ENI IPAM / IPv6 Beta](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
