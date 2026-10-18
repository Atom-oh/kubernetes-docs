# Linkerd 安装测验

审核日期：2026年10月16日，依据 edge-26.10.1 和 charts 2026.10.1。完整的前置条件和验证范围请参阅[安装指南](../../../service-mesh/linkerd/01-installation.md)。

### 1. 应如何获取本指南使用的确切公共 CLI？

A. 假设任何名为 linkerd 的软件包都是相同版本

B. 为操作系统/架构选择官方 edge-26.10.1 资源，验证其校验和及客户端版本

C. 使用 kubectl install linkerd

D. 向无法解析该标志的安装程序传递 --version stable-2.16.0

<details>
<summary>答案与说明</summary>

**答案：B**

本指南固定使用官方发布资源。安装程序替代方案使用 LINKERD2_VERSION，而旧版安装脚本已弃用，现在默认使用 edge。稳定版发行使用供应商指南。Windows 有一个 windows.exe 发布资源；不要臆造 windows-amd64.exe 文件名。

</details>

### 2. 哪个命令用于新安装前的预检？

A. linkerd check

B. linkerd check --pre

C. linkerd verify

D. linkerd install --dry-run

<details>
<summary>答案与说明</summary>

**答案：B**

check --pre 会检查 API 访问权限、Kubernetes 最低版本、Gateway API 前置条件以及安装权限/设置。它不能证明与之后发布的每个 Kubernetes 版本都兼容。请查阅确切的版本矩阵；如果选择了 CNI 安装路径，请使用了解 CNI 的标志。

</details>

### 3. 手动 Helm 路径需要哪些身份材料？

A. 一个 Envoy 镜像

B. 公共信任锚和签发者证书/私钥，或受支持的已配置签发者密钥集成

C. 每个代理 Pod 中的根 CA 私钥

D. 一个 Prometheus 配置文件

<details>
<summary>答案与说明</summary>

**答案：B**

对于此路径，控制平面 Helm chart 不会生成工作负载身份 CA 材料。请提供公共信任锚和签发者签名凭据。将根私钥保存在 Kubernetes 之外。外部签发者密钥集成需要相应的 scheme/owner 配置。

</details>

### 4. 打包的 HA 配置文件为关键控制平面组件设置了多少个副本？

A. 1

B. 2

C. 3

D. 5

<details>
<summary>答案与说明</summary>

**答案：C**

打包的配置文件为关键组件设置三个副本，并配置节点反亲和性、PDB 和 Fail 注入 Webhook 策略。这些是冗余的服务实例，不是参与仲裁的投票节点。仍然需要有足够的符合条件的节点和资源，以及正常工作的凭据/网络路径；仅有副本数并不能保证可用性。

</details>

### 5. 哪项不是 Viz 的主要功能？

A. Web 仪表板

B. 基于 Prometheus 的指标

C. 自动金丝雀晋级

D. HTTP 流量 tap

<details>
<summary>答案与说明</summary>

**答案：C**

Viz 提供指标/仪表板/tap 功能。金丝雀部署的推进需要单独的交付控制器和分析策略。当前的 Viz chart 提供指向外部 Grafana 的链接；grafana.enabled 不会部署或禁用随附的 Grafana。

</details>

### 6. 哪种 AWS 负载均衡器可以保留网关的原始 TCP 传输，而不终止 Linkerd mTLS？

A. ALB HTTP 侦听器

B. 仪表板 Ingress 资源

C. NLB TCP 侦听器

D. Gateway Load Balancer GENEVE 设备路径

<details>
<summary>答案与说明</summary>

**答案：C**

Linkerd 网关传输应使用 TCP 直通。NLB 选择内部型还是面向互联网型，取决于网络需求中的 scheme，而不是另一种负载均衡器产品。本指南中的内部 NLB 示例假设由 AWS Load Balancer Controller 管理，并且远程网络/探测路径可达。

</details>

### 7. 哪种升级顺序符合文档所述的工作流程？

A. 先升级数据平面，然后升级控制平面和 CRD

B. 目标 CLI、CRD、控制平面、已安装的扩展，最后是数据平面

C. CRD、数据平面，然后是控制平面

D. 删除 CA，然后重新安装所有内容

<details>
<summary>答案与说明</summary>

**答案：B**

首先检查目标版本的兼容性/发行说明以及当前运行状况。保留信任凭据，通过各资源所有者进行更新，然后重新创建预期的应用程序 Pod，以接收新代理。CLI 扩展使用 install 渲染更新；viz upgrade 不是子命令。遵循受支持的版本偏差范围，并在删除资源前检查 prune 输出。

</details>

### 8. linkerd install --crds 本身会做什么？

A. 安装 CLI 二进制文件

B. 生成 Linkerd CRD 清单

C. 立即应用所有集群资源

D. 为每个现有应用程序 Pod 注入代理

<details>
<summary>答案与说明</summary>

**答案：B**

此命令会输出清单。实际安装由 kubectl apply 或所选的部署所有者执行。Gateway API 前置条件与默认的 Linkerd CRD 输出分开处理，之后再安装控制平面。

</details>

### 9. 对 edge-26.10.1，应采用哪种追踪方案？

A. 运行 linkerd jaeger install，因为每个扩展仍由 CLI 提供

B. 配置受支持的收集器/后端和代理追踪，并传播应用程序上下文

C. 安装 Viz，并假设它会存储每条分布式追踪记录

D. 忽略追踪标头，因为代理可以重建所有应用程序跨度

<details>
<summary>答案与说明</summary>

**答案：B**

此 CLI 没有 jaeger 子命令，公共 linkerd-jaeger chart 的历史版本也早于所选发行版。请使用当前的追踪数据路径，并验证接收器/导出器的兼容性。指标/拓扑图不等同于已收集的分布式追踪数据。

</details>

### 10. 完整的卸载计划首先必须做什么？

A. 在应用程序仍已注入代理时删除 CRD

B. 移除应用程序注入/手动代理，并在移除扩展和控制平面之前验证重新创建的工作负载

C. 立即删除每个命名空间

D. 强制卸载以忽略仍已注入代理的工作负载

<details>
<summary>答案与说明</summary>

**答案：B**

通过工作负载所有者移除所有注入来源，重新创建并验证应用程序 Pod，然后通过各自的所有者移除已安装的扩展以及控制平面/CRD。删除 CRD 会移除其自定义资源。请单独检查 CNI 清理和命名空间所有权，并考虑网格安全性/路由功能丧失的影响。

</details>

### 11. linkerd check 不会验证什么？

A. Kubernetes API 访问权限

B. 控制平面证书有效性

C. 应用程序业务逻辑

D. 控制平面 Pod 健康状况

<details>
<summary>答案与说明</summary>

**答案：C**

核心健康检查不会验证业务结果或每条流量/安全路径。check --proxy 会增加相关的数据平面检查；已安装的扩展也有各自的检查。请将应用程序测试和实际流量验证分开进行。

</details>

### 12. 哪个命名空间注解会请求自动注入代理？

A. linkerd.io/inject: enabled

B. linkerd.io/proxy: true

C. sidecar.linkerd.io/inject: true

D. linkerd/auto-inject: yes

<details>
<summary>答案与说明</summary>

**答案：A**

此注解会为符合条件的新建 Pod 请求注入代理。Pod 级别的覆盖设置、Webhook 排除项和平台条件可能会改变结果；它并不保证每个新 Pod 都会注入代理。现有 Pod 必须重新创建；原生 sidecar 可能会出现在 initContainers 中。

</details>
