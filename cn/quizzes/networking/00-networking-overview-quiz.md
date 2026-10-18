# Kubernetes 网络概览测验

审阅日期：2026 年 9 月 11 日。请结合[网络概览](../../networking/README.md)及其官方参考资料，确认版本和平台条件。

## 测验题目

### 1. 以下哪项不是 Kubernetes 网络模型所保证的？

- A. 普通 Pod 之间可直接通过 Pod 网络通信，但可以有意实施网络隔离
- B. 节点代理可以访问本节点上的 Pod
- C. 普通 Pod 中的容器共享该 Pod 的网络命名空间
- D. 重新创建的 Pod 始终保留原 IP 地址

<details>
<summary>显示答案</summary>

**答案：D. 重新创建的 Pod 始终保留原 IP 地址**

替换后的 Pod 可能获得不同的 IP；而同一 Pod 中的容器重启时，也不一定会重新创建网络沙箱。Service 可在后端端点变化时提供稳定的发现方式。网络策略和路由仍会决定某个具体连接能否成功。

</details>

### 2. 在当前 Kubernetes 中，CNI 的主要作用是什么？

- A. 通过 API server 调度 Pod
- B. 提供配置容器网络和地址的运行时接口
- C. 取代所有 Service 负载均衡实现
- D. 下载容器镜像

<details>
<summary>显示答案</summary>

**答案：B. 提供配置容器网络和地址的运行时接口**

Kubelet 通过 CRI 请求创建沙箱等操作；容器运行时负责管理并调用 CNI 插件。插件实现网络操作，也可能委托 IPAM 或使用特定于平台的代理。veth 对是常见实现方式，但并非每种 CNI 都必须使用。

</details>

### 3. Overlay 与原生路由的区别是什么？

- A. Overlay 总是更快
- B. Overlay 在另一网络之上封装流量；原生路由直接使用底层路由，而不经过该 Overlay
- C. 原生路由总是需要 VXLAN
- D. 只有 AWS 才能使用 Overlay

<details>
<summary>显示答案</summary>

**答案：B. Overlay 在另一网络之上封装流量；原生路由直接使用底层路由，而不经过该 Overlay**

VXLAN 和 IPIP 是封装方式的例子。原生路由需要合适的路由设计；可以使用 BGP，但并非总是需要 BGP。做性能判断前，应结合 MTU、加密、策略、流量和硬件进行比较。

</details>

### 4. 哪种默认 Service 类型提供集群内部虚拟 IP？

- A. NodePort
- B. LoadBalancer
- C. ClusterIP
- D. ExternalName

<details>
<summary>显示答案</summary>

**答案：C. ClusterIP**

ClusterIP 是默认类型。它通常只在集群内部暴露，但这不是安全边界，也不保证一定可达。NodePort 使用配置的节点地址和端口；LoadBalancer 需要相应实现，也可以配置为内部负载均衡器；ExternalName 提供 DNS 别名。Headless Service 不分配虚拟 IP。

</details>

### 5. 哪个项目将基于 eBPF 的网络数据平面与 Hubble 结合使用？

- A. Flannel
- B. 原始 Weave Net 项目
- C. Cilium
- D. AWS VPC CNI

<details>
<summary>显示答案</summary>

**答案：C. Cilium**

Cilium 使用 eBPF，并包含 Hubble 可观测性组件；适用的 L7 功能会使用 Envoy。其他项目也采用 eBPF，包括 Calico 的某些数据平面选项和 AWS 的策略代理。仅凭技术名称，无法得出普遍适用的性能排名。

</details>

### 6. 以下哪项不是文档所述 EKS VPC CNI/Auto Mode 策略能力的准确描述？

- A. VPC CNI 使用 VPC 地址以及 EC2 ENI 或前缀
- B. 每个节点可容纳的 Pod 数取决于实例限制、地址分配模式和 kubelet 限制
- C. 受支持的 EKS 部署提供标准网络策略和 Admin 网络策略能力
- D. 基于 DNS 的 ApplicationNetworkPolicy 表示当前支持检查 HTTP 方法和请求正文

<details>
<summary>显示答案</summary>

**答案：D. 基于 DNS 的 ApplicationNetworkPolicy 表示当前支持检查 HTTP 方法和请求正文**

AWS 文档说明，Auto Mode 支持基于 DNS/FQDN 的 ApplicationNetworkPolicy；Auto Mode 和受支持的 EC2/VPC CNI 安装还支持 Admin ClusterNetworkPolicy。基于 DNS 的网络层控制与 HTTP 检查不同。Linux EC2、Windows 和 Fargate 的支持条件各不相同；标准 EC2 附加组件也不是 Auto Mode 的实现。

</details>

### 7. 哪一组项目提供 BGP 控制平面选项？

- A. Flannel 和原始 Weave Net
- B. Calico 和 Cilium
- C. AWS VPC CNI 和 Flannel
- D. 原始 Weave Net 和 AWS VPC CNI

<details>
<summary>显示答案</summary>

**答案：B. Calico 和 Cilium**

Calico 和 Cilium 都可以向适用的对等体通告路由。BGP 对等连接本身不提供应用服务发现、工作负载身份验证或加密。请核实路由归属，以及所选 CNI 当前的 BGP API 和拓扑要求。

</details>

### 8. 哪种流量不属于普通 Pod 间 Kubernetes NetworkPolicy 隔离的范围？

- A. 不同 Pod 之间的流量
- B. Pod 发往外部端点的流量
- C. 共享同一 Pod 网络命名空间的容器之间通过 localhost 通信
- D. 从外部进入 Pod 的流量

<details>
<summary>显示答案</summary>

**答案：C. 共享同一 Pod 网络命名空间的容器之间通过 localhost 通信**

共享 Pod 网络命名空间的容器可以通过 localhost 通信。NetworkPolicy 需要有策略执行实现，并具有明确的例外和依实现而异的细节。不要据此推断所有主机流量、经过地址转换的流量或隧道流量都会以相同方式受到控制。

</details>

### 9. 评估大型集群时，哪项是有用的可扩展性指标？

- A. 项目是否单独提供仪表板
- B. 控制器/API 负载、状态传播、每节点资源，以及真实变更频率下的行为
- C. 标志设计
- D. 发布频率

<details>
<summary>显示答案</summary>

**答案：B. 控制器/API 负载、状态传播、每节点资源，以及真实变更频率下的行为**

应测试策略和端点数量级、更新传播、连接变化、故障恢复以及实际数据平面负载。节点数阈值或 eBPF 标签本身不能证明某方案适用。产品组件及其扩展机制必须符合所选安装模式。

</details>

### 10. Ingress 与 Service 之间的正确关系是什么？

- A. Ingress 是仅支持 L4 的 API，Service 是仅支持 L7 的 API
- B. Ingress 描述 HTTP/HTTPS 路由；Service 描述网络端点和发现
- C. Service 始终对外暴露
- D. Ingress 仅支持 UDP

<details>
<summary>显示答案</summary>

**答案：B. Ingress 描述 HTTP/HTTPS 路由；Service 描述网络端点和发现**

Ingress 需要控制器或数据平面，并且通常会引用 Service 后端。数据平面可以直接连接端点 Pod IP 或 NodePort，因此 Service 虚拟 IP 不一定会多经过一次数据包转发。实际使用时，应检查具体实现支持的 Service 协议和负载均衡方式。

</details>
