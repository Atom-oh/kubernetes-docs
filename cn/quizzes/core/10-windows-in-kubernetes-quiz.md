# Kubernetes 中的 Windows 测验

本测验用于检查你对 Kubernetes 中 Windows 节点和工作负载管理的概念与实践知识。内容涵盖 Windows 容器基础、Kubernetes 中的 Windows 节点配置、网络、存储、安全和监控。

## 选择题

1. Kubernetes 中的 Windows 节点支持哪些容器运行时？
   - A) 支持 Windows CRI 的 containerd
   - B) CRI-O 和 Docker
   - C) containerd 和 CRI-O
   - D) Docker、containerd 和 gVisor

<details>
<summary>显示答案</summary>

**答案：A) 支持 Windows CRI 的 containerd**

**说明：**
Kubernetes 中 Windows 节点官方支持的容器运行时，是支持 Windows CRI 的 containerd。

- **containerd**：目前推荐用于 Windows 节点的容器运行时。containerd 轻量且稳定，自 Kubernetes 1.20 起官方支持在 Windows 节点上使用。

CRI-O 在 Windows 节点上没有获得官方支持。CRI-O 主要是面向 Linux 容器的 Container Runtime Interface（CRI）实现。

gVisor 是用于容器隔离的沙箱运行时，但目前不支持 Windows 节点。

配置容器运行时时，应确认它与所使用的 Kubernetes 版本兼容。
</details>

2. 在 Kubernetes 中配置同时包含 Windows 和 Linux 节点的集群时，需要使用哪种网络方案？
   - A) 所有 CNI 插件都同时支持 Windows 和 Linux 节点
   - B) 使用支持 Windows 的 CNI 插件，例如 Flannel、Calico 和 Antrea
   - C) Windows 节点只能使用 kubenet，不能使用 CNI 插件
   - D) Windows 节点必须始终只使用 host network 模式

<details>
<summary>显示答案</summary>

**答案：B) 使用支持 Windows 的 CNI 插件，例如 Flannel、Calico 和 Antrea**

**说明：**
在 Kubernetes 中配置混合 Windows/Linux 集群时，必须使用特定的、支持 Windows 的 CNI（Container Network Interface）插件。并非所有 CNI 插件都支持 Windows。

支持 Windows 节点的主要 CNI 插件包括：

- **Flannel**：支持 Windows 节点使用 overlay 网络模式（vxlan）。
- **Calico**：支持 Windows 节点，可使用 BGP 和 VXLAN 模式。
- **Antrea**：支持 Windows 节点，使用 OVS（Open vSwitch）。

Azure CNI 和 AWS VPC CNI 也分别在各自的环境中支持 Windows。

配置 Windows 节点的 CNI 插件时要注意：
- Windows 节点的网络栈与 Linux 节点不同。
- Windows 上可能无法使用某些网络功能。
- 应确认 CNI 插件支持的 Windows 版本及其配置要求。

kubenet 不受支持。常规 Windows Pod 不能使用 hostNetwork；HostProcess Pod 则要求设置 hostNetwork: true。
</details>

3. Kubernetes 支持对 Windows 应用容器使用哪种隔离模式？
   - A) Hyper-V 隔离
   - B) 进程隔离
   - C) 虚拟机隔离
   - D) 沙箱隔离

<details>
<summary>显示答案</summary>

**答案：B) 进程隔离**

**说明：**
Kubernetes 支持 Windows 应用容器使用进程隔离。在此模式下，Windows 容器共享主机操作系统内核，每个容器以独立的进程组运行。

进程隔离模式的特点：
- 必须与主机 OS 使用相同的内核版本。
- 资源开销较低，启动速度较快。
- 与 Linux 容器常见的隔离模式类似。

Windows 还提供另一种隔离模式：Hyper-V 隔离。
- 每个容器都在轻量级虚拟机中运行。
- 可以使用与主机 OS 不同的内核版本。
- 隔离级别更高，但开销也更大。

**Kubernetes 不支持 Hyper-V 隔离，也没有可启用该模式的 Pod 注解**。以上内容仅用于介绍 Windows OS 的背景。

虚拟机隔离不是 Windows 容器的官方隔离模式，“沙箱隔离”也不是 Windows 容器使用的术语。
</details>

4. 在 Kubernetes 中使用 Windows 节点时，以下哪项**不是**正确的限制？
   - A) 不能使用 privileged 容器
   - B) 不能使用 HostPath 卷
   - C) Pod 只支持部分 SecurityContext 功能
   - D) Windows 容器之间不能共享进程命名空间

<details>
<summary>显示答案</summary>

**答案：B) 不能使用 HostPath 卷**

**说明：**
Windows 节点可以使用 HostPath 卷。因此，“不能使用 HostPath 卷”这一说法不正确。

在 Windows 节点上使用 HostPath 卷时，必须遵循 Windows 路径格式：
```yaml
volumes:
- name: data
  hostPath:
    path: 'C:\data'
```

Windows 节点在 Kubernetes 中的实际限制包括：

- **特权模式**：不支持 privileged 标志。需要访问主机的可信节点代理可以使用 HostProcess。
- **SecurityContext 限制**：Windows 节点只支持部分 SecurityContext 功能。例如，不支持 runAsUser、runAsGroup、fsGroup、seccomp、SELinux 等。
- **命名空间共享**：同一个 Pod 中的容器会共享网络和 localhost，但不会共享进程命名空间或根文件系统。

Windows 节点的其他限制：
- 如果希望 DaemonSet 在所有节点（Linux 和 Windows）上运行，必须使用 nodeSelector。
- 某些存储驱动和卷类型可能受限。
- 仅适用于 Linux 的 alpha/beta 功能在 Windows 节点上可能无法使用。
</details>

5. Kubernetes 用什么节点标签标识 Windows 节点？
   - A) kubernetes.io/os=windows
   - B) beta.kubernetes.io/os=windows
   - C) node.kubernetes.io/windows=true
   - D) kubernetes.io/windows=enabled

<details>
<summary>显示答案</summary>

**答案：A) kubernetes.io/os=windows**

**说明：**
Kubernetes 用于标识 Windows 节点的标准节点标签是 `kubernetes.io/os=windows`。该标签表明节点的操作系统类型，供 Kubernetes 调度器将 Pod 调度到合适的节点。

若要将 Windows Pod 调度到 Windows 节点，可使用 nodeSelector：
```yaml
nodeSelector:
  kubernetes.io/os: windows
```

也可以使用节点亲和性：
```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/os
          operator: In
          values:
          - windows
```

`beta.kubernetes.io/os=windows` 曾用于早期 Kubernetes 版本，但现已弃用。

`node.kubernetes.io/windows=true` 和 `kubernetes.io/windows=enabled` 都不是 Kubernetes 标准标签。

注意：Linux 节点使用标签 `kubernetes.io/os=linux`。
</details>


6. 与 Nano Server 相比，哪种 Microsoft 基础镜像对传统 Windows 应用提供更广泛的 Windows API 支持？
   - A) mcr.microsoft.com/windows/servercore
   - B) mcr.microsoft.com/windows/nanoserver
   - C) mcr.microsoft.com/dotnet/framework/runtime
   - D) mcr.microsoft.com/powershell

<details>
<summary>显示答案</summary>

**答案：A) mcr.microsoft.com/windows/servercore**

**说明：**
Kubernetes 不会选择默认基础镜像。对于传统 Windows 应用，合适的选择是 `mcr.microsoft.com/windows/servercore`。该镜像基于 Windows Server Core 安装，包含运行大多数 Windows 应用所需的核心组件。

Windows 容器可用的主要基础镜像：

1. **Windows Server Core**（`mcr.microsoft.com/windows/servercore`）：
   - 镜像大小因发行版本、层和压缩方式而异。
   - 支持大多数 Windows 应用。
   - 包含 Windows PowerShell；需要的 .NET Framework 运行时镜像应另行选择。
   - 使用最广泛的 Windows 基础镜像。

2. **Nano Server**（`mcr.microsoft.com/windows/nanoserver`）：
   - 镜像大小因发行版本、层和压缩方式而异。
   - Windows API 支持有限。
   - 适用于 .NET Core 应用。
   - 攻击面最小。

3. **.NET Framework**（`mcr.microsoft.com/dotnet/framework/runtime`）：
   - 面向 .NET Framework 应用的镜像。
   - 基于 Server Core。
   - 包含特定版本的 .NET Framework。

4. **PowerShell**（`mcr.microsoft.com/powershell`）：
   - 用于运行 PowerShell 脚本的镜像。
   - 提供基于 Nano Server 或 Server Core 的版本。

选择 Windows 容器镜像时，请考虑：
- 应用程序需求（所需的 Windows API）
- 镜像大小和启动时间
- 安全要求
- Windows 版本兼容性（检查镜像标签中的版本号）

Windows 容器镜像必须与主机 OS 版本相同，或与其兼容。
</details>

7. 在包含 Windows 和 Linux 节点的 Kubernetes 集群中，部署 DaemonSet 的推荐方法是什么？
   - A) 使用单个 DaemonSet 并部署到所有节点
   - B) 为每种 OS 创建独立的 DaemonSet，并使用 nodeSelector
   - C) Windows 节点使用 StatefulSet 代替 DaemonSet
   - D) 为所有 DaemonSet 添加 toleration

<details>
<summary>显示答案</summary>

**答案：B) 为每种 OS 创建独立的 DaemonSet，并使用 nodeSelector**

**说明：**
在同时包含 Windows 和 Linux 节点的 Kubernetes 集群中，推荐为每种 OS 创建独立的 DaemonSet，并使用 nodeSelector。

采用这种方法的原因：
- Windows 容器和 Linux 容器使用不同的镜像格式。
- 同一个应用在不同 OS 上可能需要不同配置。
- 某些功能可能只适用于特定 OS。

Windows DaemonSet 示例：
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: windows-agent
spec:
  selector:
    matchLabels:
      app: monitoring-agent
  template:
    metadata:
      labels:
        app: monitoring-agent
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: agent
        image: contoso/windows-monitoring-agent:v1
```

Linux DaemonSet 示例：
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: linux-agent
spec:
  selector:
    matchLabels:
      app: monitoring-agent
  template:
    metadata:
      labels:
        app: monitoring-agent
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: agent
        image: contoso/linux-monitoring-agent:v1
```

若使用单个 DaemonSet，可能因容器镜像不兼容而导致部分节点上的 Pod 启动失败。

Windows 节点可以运行 DaemonSet，因此无需改用 StatefulSet。

为所有 DaemonSet 添加 toleration 有助于将 Pod 调度到带污点的节点，但无法解决 OS 兼容性问题。
</details>

8. 关于 Windows 节点上 Pod 的 DNS 配置，以下哪项说法正确？
   - A) Windows 节点不支持 DNS 配置
   - B) Windows 节点必须使用 Windows DNS Server，不能使用 CoreDNS
   - C) Windows Pod 可以使用 CoreDNS，但存在 Windows DNS 后缀限制
   - D) 每个 Windows Pod 都必须单独配置 DNS 服务器

<details>
<summary>显示答案</summary>

**答案：C) Windows Pod 可以使用 CoreDNS，但存在 Windows DNS 后缀限制**

**说明：**
Windows Pod 可以使用 CoreDNS，但存在 Windows DNS 后缀限制。在同一 namespace 中，应使用不带点的 Service 名称或完整 FQDN；带点的部分名称不会使用 Linux 的搜索列表。

Windows Pod 的 DNS 配置：
- Windows 使用 HNS/DNS 设置和单个 namespace 后缀，而不是 /etc/resolv.conf。
- Pod 可以使用集群的 DNS 服务（CoreDNS）解析 Service 名称。
- 可以使用 `dnsPolicy` 和 `dnsConfig` 字段配置 DNS 设置。

示例：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-pod
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command:
    - powershell.exe
    - -Command
    - "Start-Sleep -Seconds 3600"
  dnsPolicy: ClusterFirst
```

在 Windows 节点上使用 DNS 时要注意：
- Windows 容器中的 DNS 客户端行为可能与 Linux 略有不同。
- Windows 容器默认提供一些 DNS 工具（例如 nslookup、Resolve-DnsName）。
- 应确认网络插件正确支持 DNS 解析。

无需在 Windows 节点上单独配置 DNS 服务器，也无需使用 Windows DNS Server。Kubernetes 的标准 DNS 机制可用于 Windows Pod。
</details>

9. 关于 Windows 节点上的 Pod 间通信，以下哪项说法正确？
   - A) Windows 节点不支持 Pod 间通信
   - B) Windows 节点上的 Pod 只能与同一节点上的 Pod 通信
   - C) Windows 节点上的 Pod 不能与 Linux 节点上的 Pod 通信
   - D) Windows 节点上的 Pod 可通过 CNI 插件与所有其他 Pod 通信

<details>
<summary>显示答案</summary>

**答案：D) Windows 节点上的 Pod 可通过 CNI 插件与所有其他 Pod 通信**

**说明：**
Windows 节点上的 Pod 可以通过合适的 CNI（Container Network Interface）插件与集群中的其他 Pod 通信，包括同一 Windows 节点上的 Pod、其他 Windows 节点上的 Pod，以及 Linux 节点上的 Pod。

Windows 节点上 Pod 间通信的主要特点：
- Windows Pod 可以按名称发现并访问集群中的 Service。
- Windows Pod 会从集群 IP 地址范围中获取唯一 IP。
- Pod 间通信的实现方式取决于所选的 CNI 插件。

支持 Windows 节点 Pod 间通信的 CNI 插件包括：
- Flannel（VXLAN 模式）
- Calico
- Antrea
- Azure CNI
- AWS VPC CNI

例如，使用 Flannel 时：
- Windows 节点上的 Pod 通过 VXLAN 封装与其他节点上的 Pod 通信。
- 每个 Pod 都会获得集群 CIDR 范围内的 IP 地址。
- 路由表会配置为将 Pod IP 路由到相应节点。

Windows 节点 Pod 间通信的注意事项：
- Windows 上可能无法使用某些高级网络功能。
- NetworkPolicy 支持情况可能因 CNI 插件而异。
- Windows 防火墙规则不应阻断 Pod 通信。

Windows 节点上的 Pod 可以与 Linux 节点上的 Pod 正常通信，这是 Kubernetes 的核心功能之一。
</details>

10. 关于 Kubernetes 中 Windows 容器的资源限制，以下哪项说法正确？
    - A) Windows 容器不支持资源限制
    - B) 支持 CPU 限制，但不支持内存限制
    - C) 支持内存限制，但不支持 CPU 限制
    - D) 同时支持 CPU 和内存限制

<details>
<summary>显示答案</summary>

**答案：D) 同时支持 CPU 和内存限制**

**说明：**
Kubernetes 中的 Windows 容器同时支持 CPU 和内存资源限制。Windows 节点可以像 Linux 节点一样限制和请求容器资源。

Windows 容器资源限制示例：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-resource-demo
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
```

Windows 容器资源管理的特点：
- **CPU 限制**：Windows 使用 CPU 共享和限制来管理容器之间的 CPU 资源分配。
- Windows 没有 Linux OOM killer；可用内存耗尽时，可能发生分配失败或分页，导致性能下降。
- **资源监控**：kubelet 会监控 Windows 容器的资源使用情况，并将其报告给 Kubernetes API。

Windows 容器资源管理的注意事项：
- Windows 容器的默认资源开销可能高于 Linux 容器。
- 资源限制的具体实现可能因 Windows 版本而异。
- 内存限制设置过低可能导致 Windows 容器无法正常工作。
- Kubernetes 不支持 Hyper-V 隔离。

可以使用 `kubectl top pods` 和 `kubectl top nodes` 命令监控 Windows 节点的资源使用情况。
</details>
## 简答题

1. 说明向 Kubernetes 集群添加 Windows 节点的主要步骤和要求。

<details>
<summary>显示答案</summary>

**答案：**

**向 Kubernetes 集群添加 Windows 节点的步骤：**

1. **确认前提条件：**
   - 使用受支持的 Kubernetes/Windows 组合；上游 v1.37 支持 Windows Server 2022/2025。
   - 控制平面必须运行在 Linux 节点上。
   - 本题的 ltsc2022 示例使用 Windows Server 2022。
   - 使用兼容的 CNI 插件（例如 Flannel、Calico、Antrea 等）。

2. **配置网络：**
   - 安装支持 Windows 节点的 CNI 插件。
   - 配置集群 CIDR 和 Service CIDR。
   - 示例（Linux 侧的 Flannel 配置；Windows CNI 需单独安装）：
     ```yaml
     kind: ConfigMap
     apiVersion: v1
     metadata:
       name: kube-flannel-cfg
       namespace: kube-system
     data:
       cni-conf.json: |
         {
           "name": "cbr0",
           "plugins": [
             {
               "type": "flannel",
               "delegate": {
                 "hairpinMode": true,
                 "isDefaultGateway": true
               }
             },
             {
               "type": "portmap",
               "capabilities": {
                 "portMappings": true
               }
             }
           ]
         }
       net-conf.json: |
         {
           "Network": "10.244.0.0/16",
           "Backend": {
             "Type": "vxlan",
             "VNI": 4096,
             "Port": 4789
           }
         }
     ```

3. **准备 Windows 节点：**
   - 安装并更新 Windows Server。
   - 启用所需的 Windows 功能：
     ```powershell
     Install-WindowsFeature -Name Containers
     Restart-Computer -Force
     ```
   - 安装容器运行时（推荐 containerd）：
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```

4. **安装 kubelet 和 kube-proxy：**
   - 下载 Kubernetes 二进制文件：
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
   - 创建 kubelet 配置文件：
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
   - 注册并启动 kubelet 服务：
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
   - 配置并启动 kube-proxy（通常以 DaemonSet 方式部署）。

5. **加入节点：**
   - 运行 kubeadm join 命令，或手动配置 TLS 证书和 kubeconfig。
   - 确认节点已注册到集群：
     ```bash
     kubectl get nodes
     ```

6. **添加节点标签：**
   - 如果 Windows 节点没有自动获得操作系统标签，则手动添加：
     ```bash
     kubectl label node <windows-node-name> kubernetes.io/os=windows
     ```

7. **部署测试工作负载：**
   - 部署一个运行 Windows 容器的简单 Pod：
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: windows-test-pod
     spec:
       os:
         name: windows
       nodeSelector:
         kubernetes.io/os: windows
       containers:
       - name: windows-server
         image: mcr.microsoft.com/windows/servercore:ltsc2022
         command:
         - powershell.exe
         - -Command
         - "Start-Sleep -Seconds 3600"
     ```

**关键注意事项：**

1. **版本兼容性：**
   - Windows Server 版本必须与容器镜像版本兼容。
   - 确认 Kubernetes 版本及其 Windows 支持功能。

2. **网络：**
   - 使用支持 Windows 节点的 CNI 插件。
   - 确认网络策略支持情况。
   - 确认端口要求（kubelet、containerd、CNI 等）。

3. **存储：**
   - 确认 Windows 节点支持所用的存储驱动和卷类型。
   - 确认 CSI 驱动兼容性。

4. **监控与日志：**
   - 部署适用于 Windows 节点的监控代理。
   - 配置 Windows 事件日志收集。

5. **安全：**
   - 配置 Windows 防火墙规则。
   - 按需设置 Group Managed Service Accounts（gMSA）。
   - 配置网络安全组。

6. **自动化：**
   - 自动化配置 Windows 节点（Ansible、PowerShell DSC 等）。
   - 制定节点升级策略。
</details>

2. 说明 Windows 容器和 Linux 容器的主要区别，以及在 Kubernetes 中如何管理这些差异。

<details>
<summary>显示答案</summary>

**答案：**

**Windows 容器和 Linux 容器的主要区别：**

1. **底层技术：**
   - **Linux 容器**：使用 Linux namespace、cgroup 和内核功能进行隔离。
   - **Windows 容器**：使用 Windows 隔离技术（job object、Hyper-V 隔离等）。

2. **镜像结构：**
   - **Linux 容器**：镜像相对较小（几十到几百 MB）。
   - **Windows 容器**：镜像通常更大（数 GB），基础镜像体积也更大。

3. **隔离模式：**
   - **Linux 容器**：通常基于 namespace；也有其他沙箱运行时。
   - **Windows 容器**：Kubernetes 支持进程隔离；Hyper-V 不在 Kubernetes 的支持范围内。

4. **文件系统：**
   - **Linux 容器**：分层文件系统（例如 OverlayFS）。
   - **Windows 容器**：基于 NTFS 的筛选驱动程序。

5. **网络：**
   - **Linux 容器**：支持多种网络模式和驱动程序。
   - **Windows 容器**：网络模式有限，只支持特定的 CNI 插件。

6. **资源管理：**
   - **Linux 容器**：通过 cgroup 进行细粒度资源控制。
   - **Windows 容器**：通过 Job Object 控制资源，但存在一些限制。

7. **安全上下文：**
   - **Linux 容器**：支持多种安全上下文选项（SELinux、AppArmor 等）。
   - **Windows 容器**：安全上下文选项有限，不支持 privileged 容器。

8. **对主机 OS 的依赖：**
   - **Linux 容器**：可以运行在多种 Linux 发行版上。
   - **Windows 容器**：要求版本与主机 OS 相同或兼容。

**在 Kubernetes 中管理这些差异：**

1. **节点选择与调度：**
   - **使用节点标签**：`kubernetes.io/os=windows` 或 `kubernetes.io/os=linux`。
   - **使用 nodeSelector**：
     ```yaml
     os:
       name: windows
     nodeSelector:
       kubernetes.io/os: windows
     ```
   - **使用节点亲和性**：
     ```yaml
     affinity:
       nodeAffinity:
         requiredDuringSchedulingIgnoredDuringExecution:
           nodeSelectorTerms:
           - matchExpressions:
             - key: kubernetes.io/os
               operator: In
               values:
               - windows
     ```

2. **工作负载隔离：**
   - **创建针对不同 OS 的 Deployment**：
     ```yaml
     # Deployment for Windows workloads
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: windows-app
     spec:
       selector:
         matchLabels:
           app: myapp
           os: windows
       template:
         metadata:
           labels:
             app: myapp
             os: windows
         spec:
           os:
             name: windows
           nodeSelector:
             kubernetes.io/os: windows
           containers:
           - name: windows-app
             image: myregistry/windows-app:latest

     ---
     # Deployment for Linux workloads
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: linux-app
     spec:
       selector:
         matchLabels:
           app: myapp
           os: linux
       template:
         metadata:
           labels:
             app: myapp
             os: linux
         spec:
           nodeSelector:
             kubernetes.io/os: linux
           containers:
           - name: linux-app
             image: myregistry/linux-app:latest
     ```

3. **DaemonSet 管理：**
   - **创建针对不同 OS 的 DaemonSet**：
     ```yaml
     # DaemonSet for Windows nodes
     apiVersion: apps/v1
     kind: DaemonSet
     metadata:
       name: windows-agent
     spec:
       selector:
         matchLabels:
           app: monitoring-agent
       template:
         metadata:
           labels:
             app: monitoring-agent
         spec:
           os:
             name: windows
           nodeSelector:
             kubernetes.io/os: windows
           containers:
           - name: agent
             image: myregistry/windows-agent:latest
     ```

4. **镜像管理：**
   - **使用多架构镜像**：相同标签下支持多种 OS/架构。
   - **使用区分 OS 的镜像标签**：`myapp:linux` 和 `myapp:windows`。
   - **设置镜像拉取策略**：`imagePullPolicy: Always`。

5. **资源请求和限制：**
   - **为每种 OS 设置合适的资源值**：
     ```yaml
     resources:
       requests:
         memory: "2Gi"  # Windows containers typically need more memory
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```

6. **网络：**
   - **选择兼容的 CNI 插件**：Flannel、Calico、Antrea 等。
   - **应用网络策略时考虑 OS 差异**：
     ```yaml
     apiVersion: networking.k8s.io/v1
     kind: NetworkPolicy
     metadata:
       name: allow-specific-traffic
     spec:
       podSelector:
         matchLabels:
           app: myapp
       ingress:
       - from:
         - podSelector:
             matchLabels:
               app: frontend
     ```

7. **存储：**
   - **使用与 OS 兼容的 StorageClass：**
     ```yaml
     apiVersion: v1
     kind: PersistentVolumeClaim
     metadata:
       name: windows-pvc
     spec:
       storageClassName: windows-storage  # Windows node compatible storage class
       accessModes:
         - ReadWriteOnce
       resources:
         requests:
           storage: 10Gi
     ```

8. **安全上下文：**
   - **为各 OS 应用合适的安全设置：**
     ```yaml
     # Security context for Linux pods
     securityContext:
       runAsUser: 1000
       runAsGroup: 3000
       fsGroup: 2000

     # These Linux-only fields are rejected with spec.os.name: windows.
     ```

9. **监控与日志：**
   - **部署各 OS 专用的监控代理。**
   - **调整日志收集路径**：Windows（`C:\k\logs`）与 Linux（`/var/log`）。

10. **CI/CD 流水线：**
    - **配置针对不同 OS 的构建和测试流水线。**
    - **制定多 OS 部署策略。**
</details>

3. 说明如何在 Windows 容器中使用 Group Managed Service Account（gMSA），以及它的优点。

<details>
<summary>显示答案</summary>

**答案：**

**Group Managed Service Account（gMSA）概述：**

gMSA 是一种用于 Windows 域环境服务认证的特殊 Active Directory 账户。在 Kubernetes 的 Windows 容器中使用 gMSA，可以运行需要域认证的应用，尤其适用于以下场景：

- 需要与 Active Directory 集成的 .NET 应用。
- 使用 Windows 身份验证连接 SQL Server。
- 需要 Kerberos 身份验证的服务。
- 需要访问域资源的应用。

**如何在 Windows 容器中使用 gMSA：**

1. 准备 AD/DNS 连通性和受支持的凭证获取方式：加入域的主机，或单独配置的 portable identity provider。容器本身不能加入域。
2. 检查 `Get-KdsRootKey`。只有在确有需要时才由 AD 管理员创建密钥，并预留复制时间（最长 10 小时）。将时间回拨 10 小时仅适用于单 DC 测试环境。
3. 只向专用的授权主机组授予密码读取权限，不要授予所有 Domain Computers。使用 CredentialSpec 模块的 `New-CredentialSpec` 生成实际 SID/GUID/DNS/NetBIOS 值。
4. 安装 GMSACredentialSpec CRD 以及变更/验证 webhook。使用 `windows.k8s.io/v1`，将生成的 JSON 放入 `GMSACredentialSpec.credspec`。它不是 Secret，也不包含 gMSA 密码。
5. 授予 ServiceAccount 对指定资源的 `use` 权限，并设置 Pod 的 `serviceAccountName` 和 `windowsOptions.gmsaCredentialSpecName`。
6. 验证应用实际的 Kerberos 身份验证并运行 `klist`。`whoami` 报告的是本地进程用户，而不是 gMSA 网络身份。

完整的生成资源及 RBAC 示例见[本章的 gMSA 操作流程](../../core/10-windows-in-kubernetes.md)。

**使用 gMSA 的优点：**

1. **增强安全性：**
   - 无需在容器中硬编码凭证。
   - 密码自动管理和轮换。
   - 便于遵循最小权限原则。

2. **Active Directory 集成：**
   - 可以将使用 Windows 身份验证的现有应用容器化。
   - 支持 Kerberos 和 NTLM 身份验证。
   - 可无缝访问域资源。

3. **集中式身份管理：**
   - 通过 Active Directory 统一管理身份。
   - 可以应用组策略。
   - 改善审计和合规性。

4. **应用兼容性：**
   - 支持需要域身份验证的传统 .NET 应用。
   - 支持使用 Windows 集成身份验证连接 SQL Server。
   - 支持 IIS Web 应用的 Windows 身份验证。

5. **简化运维：**
   - 凭证管理自动化。
   - 容器重启后凭证仍然有效。
   - 多个容器可以共用同一身份。

**使用 gMSA 时的注意事项：**

1. **网络要求：**
   - Windows 节点必须能连接域控制器。
   - 必须正确配置 DNS。
   - 必须开放所需端口（Kerberos、LDAP 等）。

2. **权限管理：**
   - 仅授予 gMSA 必需的最小权限。
   - 配置恰当的组成员资格。
   - 定期复核权限。

3. **可扩展性：**
   - 大型集群要考虑域控制器的负载。
   - 使用多个 gMSA 账户以隔离权限。

4. **故障排查：**
   - 排查域连通性问题。
   - 核实 credential spec 配置错误。
   - 检查容器运行时日志。
</details>

4. 说明如何在 Kubernetes 中为 Windows 节点配置日志记录和监控，以及它们与 Linux 节点有何不同。

<details>
<summary>显示答案</summary>

**答案：**

**为 Windows 节点配置日志和监控：**

**1. 日志配置：**

**Windows 节点的主要日志来源：**
- Windows Event Log（System、Application、Security）。
- ETW（Event Tracing for Windows）事件。
- 应用日志文件（通常位于 `C:\` 驱动器中）。
- kubelet 和容器运行时日志（通常位于 `C:\k\logs` 或类似路径）。

**配置 Windows 节点日志的方法：**

1. **设置 Fluent Bit 或 Fluentd：**
   使用本章介绍的 Fluent Bit Windows 服务或经过审查的 HostProcess 收集器读取主机事件日志。将 .evtx 文件挂载到普通容器中并不能让 winlog 读取主机 API。以下输入配置要求具备读取 Security 日志的权限，以及持久化的 checkpoint 目录。

2. **配置 Windows Event Log 收集：**
   ```ini
   # Fluent Bit Windows configuration
   [INPUT]
       Name            winlog
       Channels        System,Application,Security
       Interval_Sec    1
       DB              C:\fluent-bit\winlog.db

   [OUTPUT]
       Name            es
       Match           *
       Host            elasticsearch-master
       Port            9200
       Index           windows_logs
       Suppress_Type_Name On
       tls             On
       tls.verify      On
   ```

3. **收集容器日志：**
   - containerd 日志路径：`C:\var\log\containers`。
   - kubelet 日志路径：`C:\k\logs` 或 Windows Event Log。

**2. 监控配置：**

**Windows 节点的主要指标：**
- CPU、内存和磁盘使用量。
- 网络流量。
- 进程数。
- 页面文件使用量。
- 容器资源使用量。

**配置 Windows 节点监控的方法：**

1. **设置 Prometheus Windows Exporter：**
   ```yaml
   apiVersion: apps/v1
   kind: DaemonSet
   metadata:
     name: windows-exporter
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: windows-exporter
     template:
       metadata:
         labels:
           app: windows-exporter
       spec:
         os:
           name: windows
         nodeSelector:
           kubernetes.io/os: windows
         containers:
         - name: windows-exporter
           image: ghcr.io/prometheus-community/windows-exporter:REPLACE_WITH_TESTED_RELEASE
           args:
           - --collectors.enabled=cpu,memory,logical_disk,net,service,os,system,container
           ports:
           - containerPort: 9182
             name: metrics
             protocol: TCP
         hostNetwork: true
         securityContext:
           windowsOptions:
             hostProcess: true
             runAsUserName: NT AUTHORITY\SYSTEM
   ```

2. **配置 Prometheus 抓取：**
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: windows-exporter
     namespace: monitoring
     labels:
       app: windows-exporter
   spec:
     selector:
       app: windows-exporter
     ports:
     - name: metrics
       port: 9182
       targetPort: metrics
   ---
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: windows-exporter
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: windows-exporter
     endpoints:
     - port: metrics
       interval: 30s
   ```

3. **设置 Grafana 仪表板：**
   - 为 Windows 节点指标创建专用仪表板。
   - 添加 Windows 专用面板（例如页面文件用量、服务状态等）。

**3. 故障排查工具：**

**Windows 节点故障排查工具：**
- PowerShell 命令（`Get-Process`、`Get-Service`、`Get-EventLog`）。
- Windows Performance Monitor（PerfMon）。
- Event Viewer。
- `kubectl debug` 命令（在 Windows 节点上支持有限）。

**Windows 节点故障排查示例：**
```powershell
# Check kubelet logs
Get-EventLog -LogName Application -Source kubelet -Newest 50

# Check containerd status
Get-Service containerd

# Verify network connectivity
Test-NetConnection -ComputerName api.kubernetes.cluster -Port 443
```

**与 Linux 节点的主要区别：**

1. **日志存储位置：**
   - **Linux**：以文本文件形式存储在 `/var/log/` 目录中。
   - **Windows**：以二进制格式存储在 Windows Event Log 中，也可能以文本文件形式存储在不同位置。

2. **日志收集机制：**
   - **Linux**：通常基于文件收集（tail、read）。
   - **Windows**：必须通过 Windows Event Log API 收集。

3. **指标收集：**
   - **Linux**：从 `/proc`、`/sys` 文件系统采集指标。
   - **Windows**：使用 WMI（Windows Management Instrumentation）或 Performance Counter API。

4. **容器日志：**
   - **Linux**：标准输出/错误会重定向到文件。
   - **Windows**：stdout/stderr 同样使用 CRI 日志；ETW/文件日志则需要应用或主机收集器。

5. **资源监控：**
   - **Linux**：通过 cgroup 监控容器资源使用量。
   - **Windows**：通过 Job Object 监控资源，有些指标的计算方式不同。

6. **监控代理：**
   - **Linux**：有多种代理可用（node-exporter、cAdvisor 等）。
   - **Windows**：代理支持较少，需要使用 Windows 专用代理。

7. **调试工具：**
   - **Linux**：提供多种 CLI 工具（ps、top、netstat、strace 等）。
   - **Windows**：使用 PowerShell 命令和 GUI 工具，CLI 工具较少。

**最佳实践：**

1. **集成日志方案：**
   - 使用 EFK（Elasticsearch、Fluent Bit、Kibana）或 ELK 技术栈。
   - 为 Windows 和 Linux 节点分别配置。

2. **集成监控方案：**
   - 使用 Prometheus + Grafana 监控所有节点。
   - 创建针对不同 OS 的仪表板。

3. **告警配置：**
   - 为 Windows 专用事件设置告警规则。
   - 监控关键 Windows 服务状态。

4. **日志保留策略：**
   - 配置 Windows 事件日志大小和保留时间。
   - 配置日志轮换策略。

5. **安全监控：**
   - 收集和分析 Windows 安全事件日志。
   - 监控权限变更和登录尝试。

请注明监控 namespace、Prometheus Operator/ServiceMonitor 发现配置以及经过测试的版本标签。限制 HostProcess 的 PSS 例外范围，并限制端口 9182 的防火墙来源。根据发行版确认主机日志路径/通道；在 EKS Windows 上，kubelet/kube-proxy 日志位于 EKS Windows 中。Elasticsearch 示例还要求配置可信 CA 和身份验证。
</details>

5. 说明 Kubernetes 中 Windows 容器的存储选项和卷挂载配置方法。

<details>
<summary>显示答案</summary>

**答案：**

**Windows 容器的存储选项：**

**1. 基本卷类型：**

1. **emptyDir：**
   - 在 Pod 生命周期内存储临时数据。
   - 在 Windows 节点本地 NTFS 卷上创建。
   - 删除 Pod 时数据也会删除。

   ```yaml
   volumes:
   - name: temp-data
     emptyDir: {}
   ```

2. **hostPath：**
   - 直接访问 Windows 节点的文件系统。
   - 仅在双引号 YAML 字符串中需要转义反斜杠；普通或单引号字符串中的路径使用单个反斜杠。
   - 不能跨节点共享数据。

   ```yaml
   volumes:
   - name: logs
     hostPath:
       path: 'C:\Logs'
       type: DirectoryOrCreate
   ```

3. **configMap 和 secret：**
   - 用于存储配置数据和敏感信息。
   - 在 Windows 容器中的使用方式相同。
   - 文件权限设置在 Windows 上的应用方式不同。

   ```yaml
   volumes:
   - name: config
     configMap:
       name: app-config
   ```

4. **persistentVolumeClaim（PVC）：**
   - 用于申请持久化存储。
   - 需要与 Windows 兼容的 StorageClass。
   - 需要确认 CSI 驱动支持情况。

   ```yaml
   volumes:
   - name: data
     persistentVolumeClaim:
       claimName: windows-pvc
   ```

**2. 支持 Windows 容器的存储方案：**

1. **Azure Disk/File（AKS）：**
   - Azure Kubernetes Service 支持 Windows 节点。
   - 可以使用基于 SMB 协议的 Azure Files。
   - 支持 Azure Disk CSI 驱动。

   ```yaml
   # Azure File PVC
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: azure-file-pvc
   spec:
     accessModes:
     - ReadWriteMany
     storageClassName: azurefile-csi
     resources:
       requests:
         storage: 100Gi
   ```

2. **AWS EBS（EKS）：**
   - Amazon EKS 支持 Windows 节点。
   - 可使用 EBS CSI 驱动。
   - 访问范围受限于单个 AZ。

   ```yaml
   # AWS EBS PVC
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: ebs-windows-pvc
   spec:
     accessModes:
     - ReadWriteOnce
     storageClassName: ebs-sc
     resources:
       requests:
         storage: 50Gi
   ```

3. **SMB/CIFS 卷：**
   - 适用于 Windows 环境的网络文件系统。
   - 需要与 Windows 兼容的 SMB CSI 驱动。
   - 支持多个 Pod 以 ReadWriteMany 模式访问。

   ```yaml
   # SMB CSI driver example
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: smb-windows-pvc
   spec:
     accessModes:
     - ReadWriteMany
     storageClassName: smb-csi
     resources:
       requests:
         storage: 100Gi
   ```

4. **iSCSI：**
   - Windows 具备 iSCSI 功能，并不代表支持 Kubernetes 内置的 iscsi 卷插件。请使用明确支持 Windows 文件系统卷的存储厂商 CSI 驱动。Windows Pod 不支持原始块卷 volumeDevices。

**3. Windows 容器的卷挂载配置：**

1. **卷挂载路径：**
   - Windows 容器使用 Windows 路径格式。
   - 通常使用 `C:\` 驱动器内的路径。
   - 仅在双引号 YAML 字符串中需要转义反斜杠；普通或单引号字符串中的路径使用单个反斜杠。

   ```yaml
   volumeMounts:
   - name: data
     mountPath: 'C:\data'
   ```

2. **只读挂载：**
   - Windows 容器支持只读挂载。
   - 通过 NTFS 权限应用。

   ```yaml
   volumeMounts:
   - name: config
     mountPath: 'C:\config'
     readOnly: true
   ```

3. **Subpath 挂载：**
   - 可以只挂载卷中的特定子路径。
   - 注意 Windows 路径分隔符。

   ```yaml
   volumeMounts:
   - name: shared-data
     mountPath: 'C:\app\logs'
     subPath: logs
   ```

**4. Windows 容器存储配置示例：**

1. **Web 应用配置：**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: windows-web-app
   spec:
     os:
       name: windows
     nodeSelector:
       kubernetes.io/os: windows
     containers:
     - name: web
       image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
       volumeMounts:
       - name: website
         mountPath: 'C:\inetpub\wwwroot'
       - name: logs
         mountPath: 'C:\inetpub\logs'
       - name: config
         mountPath: 'C:\config'
         readOnly: true
     volumes:
     - name: website
       persistentVolumeClaim:
         claimName: website-content-pvc
     - name: logs
       emptyDir: {}
     - name: config
       configMap:
         name: web-config
   ```

2. **数据库配置：**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: linux-sql-for-windows-apps
   spec:
     nodeSelector:
       kubernetes.io/os: linux
       kubernetes.io/arch: amd64
     containers:
     - name: sql
       image: mcr.microsoft.com/mssql/server:2022-latest
       env:
       - name: ACCEPT_EULA
         value: "Y"
       - name: MSSQL_SA_PASSWORD
         valueFrom:
           secretKeyRef:
             name: sql-credentials
             key: sa-password
       volumeMounts:
       - name: data
         mountPath: /var/opt/mssql/data
       - name: backup
         mountPath: /var/opt/mssql/backup
     volumes:
     - name: data
       persistentVolumeClaim:
         claimName: sql-data-pvc
     - name: backup
       persistentVolumeClaim:
         claimName: sql-backup-pvc
     os:
       name: linux
   ```

**5. 使用 Windows 容器存储时的注意事项：**

1. **路径分隔符：**
   - 仅在双引号 YAML 字符串中需要转义反斜杠；普通或单引号字符串中的路径使用单个反斜杠。
   - 也可以使用正斜杠（`/`），但要确认应用兼容性。

2. **文件权限：**
   - Windows 使用 NTFS 权限模型。
   - 无法像 Linux 那样使用 chmod/chown 设置权限。
   - 容器中的权限由容器用户上下文决定。

3. **性能注意事项：**
   - 网络存储（SMB/CIFS）可能产生延迟。
   - 对性能要求高时，建议使用本地存储或直连块存储。

4. **StorageClass 兼容性：**
   - 确认 StorageClass 与 Windows 节点兼容。
   - 确认 CSI 驱动支持 Windows。

5. **备份与恢复：**
   - 考虑与 Windows Volume Shadow Copy Service（VSS）集成。
   - 实施应用一致性备份机制。

SQL Server 容器镜像运行在 Linux 上；Windows 应用通过网络连接。请准备兼容 Linux 的 PVC、SQL 进程写入权限以及已有的 sql-credentials Secret。

请先创建示例 StorageClass。Windows EBS StorageClass 需要 NTFS 和 WaitForFirstConsumer；仅仅使用某个名称并不会安装驱动或创建 StorageClass。
</details>

## 实践题

1. 为同时包含 Windows 和 Linux 节点的 Kubernetes 集群编写一个符合以下要求的 Deployment 清单：
   - 应用名称：web-app。
   - Windows 容器镜像：mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022。
   - 副本数：2。
   - 端口：80。
   - 环境变量：WEBSITE_NAME=MyWindowsApp。
   - 卷：将 ConfigMap web-config 挂载到 C:\inetpub\wwwroot\web.config。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
        ports:
        - containerPort: 80
        env:
        - name: WEBSITE_NAME
          value: "MyWindowsApp"
        volumeMounts:
        - name: config-volume
          mountPath: 'C:\inetpub\wwwroot\web.config'
          subPath: web.config
      volumes:
      - name: config-volume
        configMap:
          name: web-config
---
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**说明：**

1. **Deployment 资源：**
   - 使用 `nodeSelector`，只调度到 Windows 节点。
   - 按要求设置 2 个副本。
   - 使用 IIS Web 服务器镜像。

2. **容器配置：**
   - 暴露端口 80。
   - 设置环境变量 `WEBSITE_NAME`。
   - 使用 Windows 路径格式，将 ConfigMap 挂载到指定文件路径。

3. **卷配置：**
   - 将 ConfigMap 挂载为卷。
   - 使用 `subPath` 将 ConfigMap 中的指定键挂载为文件。

4. **Service 定义：**
   - 创建用于访问应用的 ClusterIP Service。
   - 通过端口 80 访问。

**注意：**
- 仅在双引号 YAML 字符串中需要转义反斜杠；普通或单引号路径使用单个反斜杠。
- Windows 容器的资源需求可能高于 Linux 容器；生产环境中应设置合适的资源请求和限制。

仅设置 WEBSITE_NAME 并不会重命名 IIS 站点。请在已有的 web-config ConfigMap 中提供 web.config 所需的键；subPath 挂载不会自动更新。
</details>

2. 为同时运行在 Windows 和 Linux 节点上的监控代理编写 DaemonSet 清单。每种 OS 都应使用合适的镜像和配置。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: monitoring-agent-linux
  namespace: monitoring
  labels:
    app: monitoring-agent
    os: linux
spec:
  selector:
    matchLabels:
      app: monitoring-agent
      os: linux
  template:
    metadata:
      labels:
        app: monitoring-agent
        os: linux
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: agent
        image: prom/node-exporter:latest
        ports:
        - containerPort: 9100
          name: metrics
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
        args:
        - --path.procfs=/host/proc
        - --path.sysfs=/host/sys
        - --path.rootfs=/host/root
        securityContext:
          runAsNonRoot: true
          runAsUser: 65534
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
      hostNetwork: true
      hostPID: true
      dnsPolicy: ClusterFirstWithHostNet
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: monitoring-agent-windows
  namespace: monitoring
  labels:
    app: monitoring-agent
    os: windows
spec:
  selector:
    matchLabels:
      app: monitoring-agent
      os: windows
  template:
    metadata:
      labels:
        app: monitoring-agent
        os: windows
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: agent
        image: ghcr.io/prometheus-community/windows-exporter:REPLACE_WITH_TESTED_RELEASE
        ports:
        - containerPort: 9182
          name: metrics
        args:
        - --collectors.enabled=cpu,memory,logical_disk,net,service,os,system,container
      hostNetwork: true
      securityContext:
        windowsOptions:
          hostProcess: true
          runAsUserName: NT AUTHORITY\SYSTEM
---
apiVersion: v1
kind: Service
metadata:
  name: monitoring-agent
  namespace: monitoring
  labels:
    app: monitoring-agent
spec:
  type: ClusterIP
  ports:
  - name: metrics
    port: 9100
    targetPort: metrics
    protocol: TCP
  selector:
    app: monitoring-agent
```

**说明：**

1. **面向 Linux 节点的 DaemonSet：**
   - 使用 `nodeSelector`，仅调度到 Linux 节点。
   - 使用 Prometheus Node Exporter 镜像。
   - 挂载主机的 `/proc`、`/sys` 和 `/` 目录以采集系统指标。
   - 配置安全上下文，以非 root 用户运行。

2. **面向 Windows 节点的 DaemonSet：**
   - 使用 `nodeSelector`，仅调度到 Windows 节点。
   - 使用 Windows Exporter 镜像。
   - 指定要采集的指标收集器。
   - 应用 Windows 专用配置。

3. **共用 Service：**
   - 创建一个 Service，同时选择两个 DaemonSet 的 Pod。
   - 使用命名 targetPort，让不同 endpoint 分别映射到 Linux 的 9100 端口和 Windows 的 9182 端口。
   - Prometheus 可通过该 Service 抓取指标。

**注意：**
- 应为每种 OS 使用合适的镜像和配置。
- 由于 Windows 和 Linux 节点的指标采集方式不同，应将它们部署在不同的 DaemonSet 中。
- 使用标签区分 OS 类型，便于在监控系统中筛选和可视化指标。
- 在生产环境中，还需要配置资源请求和限制、安全上下文、ServiceAccount 等。

创建监控 namespace，并将 exporter 标签替换为经过测试的版本。HostProcess 以主机权限运行；应严格限定其 PSS 例外范围，并将 9182 端口的防火墙访问限制为 Prometheus 来源。Prometheus 必须发现并抓取每个 Service endpoint，才能收集所有节点的指标。
</details>

3. 编写一个 Pod 清单，用于在 Windows 容器中部署通过 Active Directory 身份验证的 .NET 应用。必须使用 Group Managed Service Account（gMSA）。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ad-auth-app
  labels:
    app: ad-auth-app
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      gmsaCredentialSpecName: gmsa-cred-spec
  containers:
  - name: dotnet-app
    image: myregistry/ad-auth-app:latest
    ports:
    - containerPort: 80
    env:
    - name: ASPNETCORE_ENVIRONMENT
      value: Production
    volumeMounts:
    - name: app-config
      mountPath: C:\app\appsettings.json
      subPath: appsettings.json
    resources:
      requests:
        memory: 2Gi
        cpu: 500m
      limits:
        memory: 4Gi
        cpu: 1000m
  volumes:
  - name: app-config
    configMap:
      name: ad-auth-app-config
  serviceAccountName: windows-app
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ad-auth-app-config
data:
  appsettings.json: "{\n  \"Logging\": {\n    \"LogLevel\": {\n      \"Default\":\
    \ \"Information\",\n      \"Microsoft\": \"Warning\"\n    }\n  },\n  \"ConnectionStrings\"\
    : {\n    \"DefaultConnection\": \"Server=sql-server;Database=AppDB;Integrated\
    \ Security=True;\"\n  },\n  \"ActiveDirectory\": {\n    \"Domain\": \"example.com\"\
    ,\n    \"UseWindowsAuthentication\": true\n  }\n}\n"
---
apiVersion: v1
kind: Service
metadata:
  name: ad-auth-app
spec:
  selector:
    app: ad-auth-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**说明：**

1. **gMSACredentialSpec 和授权：**
   - 前置条件中的 GMSACredentialSpec 包含生成的凭证元数据，不包含密码。
   - webhook 在检查 ServiceAccount 是否有权使用该资源后，会展开指定的凭证配置。

2. **Windows Pod 配置：**
   - 使用 `nodeSelector` 将 Pod 调度到 Windows 节点。
   - 通过 `securityContext.windowsOptions.gmsaCredentialSpecName` 引用 gMSA 凭证配置。
   - 使用 .NET 应用镜像。
   - 设置适当的资源请求和限制。

3. **卷和配置：**
   - 使用 ConfigMap 提供应用设置。
   - 以 Windows 路径格式挂载配置文件。
   - 包含使用 Windows 集成身份验证的 SQL Server 连接字符串。

4. **Service 定义：**
   - 创建用于访问应用的 ClusterIP Service。

**gMSA 配置前提条件：**

首先创建本章的 `gmsa-cred-spec` 资源、`windows-app` ServiceAccount 以及限定到指定资源名称的 use RBAC 授权。必须安装 CRD 和两个 webhook。为 Windows Server 2022 构建并验证自定义应用镜像及配置。gMSA 提供网络凭证；应用也必须使用 Windows 身份验证。ConfigMap 的 subPath 挂载不会自动更新；配置更改后应重新创建 Pod。
</details>

4. 为同时包含 Windows 和 Linux 节点的集群编写 NetworkPolicy 清单，并满足以下要求：
   - Windows Web 应用 Pod（标签：app=windows-web）只能访问 Linux 数据库 Pod（标签：app=linux-db）。
   - 数据库 Pod 只允许端口 3306 的访问。
   - Web 应用 Pod 可通过端口 80 从外部访问。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
# NetworkPolicy for Windows web application
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: windows-web-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: windows-web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - ports:
    - port: 80
      protocol: TCP
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: linux-db
    ports:
    - port: 3306
      protocol: TCP
---
# NetworkPolicy for Linux database
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: linux-db-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: linux-db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: windows-web
    ports:
    - port: 3306
      protocol: TCP
```

**说明：**

1. **Windows Web 应用 NetworkPolicy：**
   - 作用于带有标签 `app=windows-web` 的 Pod。
   - **Ingress 规则**：允许所有来源通过端口 80 访问。
   - **Egress 规则**：只允许访问带标签 `app=linux-db` 的 Pod 的 3306 端口。

2. **Linux 数据库 NetworkPolicy：**
   - 作用于带有标签 `app=linux-db` 的 Pod。
   - **Ingress 规则**：仅允许带标签 `app=windows-web` 的 Pod 通过端口 3306 访问。

**注意：**
- 要使网络策略生效，必须使用支持 NetworkPolicy 的 CNI 插件（例如 Calico、Antrea）。
- Windows 节点上的 NetworkPolicy 支持情况可能因 CNI 插件而异。
- 本示例假设使用默认 namespace；实际环境应指定合适的 namespace。
- 生产环境中可能还需要添加 DNS 查询、外部 Service 访问等 egress 规则。

**部署示例：**

Windows Web 应用 Pod：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: windows-web
  template:
    metadata:
      labels:
        app: windows-web
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: web
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
        ports:
        - containerPort: 80
```

Linux 数据库 Pod：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: linux-db
spec:
  replicas: 1
  selector:
    matchLabels:
      app: linux-db
  template:
    metadata:
      labels:
        app: linux-db
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: mysql
        image: mysql:8.0
        ports:
        - containerPort: 3306
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
```

NetworkPolicy 的 allow 规则会叠加生效；其他策略可能会授予额外访问权限。策略本身不会创建外部 LoadBalancer/Ingress。使用 DNS 的应用还需要允许向集群 DNS 的 UDP/TCP 53 端口出站。下方数据库示例仅用于教学，不提供持久化；实际服务需要持久化存储和备份。
</details>

5. 为运行在 Windows 节点上的 .NET Framework 应用编写 Deployment 清单。应用需要使用连接字符串作为环境变量来访问 Azure Blob Storage，并且要为日志配置持久化卷。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: windows-logs-pvc
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: azurefile-csi
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotnet-framework-app
  labels:
    app: dotnet-framework-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dotnet-framework-app
  template:
    metadata:
      labels:
        app: dotnet-framework-app
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: dotnet-app
        image: myregistry/dotnet-framework-app:latest
        ports:
        - containerPort: 80
        env:
        - name: AZURE_STORAGE_CONNECTION_STRING
          valueFrom:
            secretKeyRef:
              name: azure-storage-secret
              key: connection-string
        - name: LOG_LEVEL
          value: Information
        - name: ASPNET_ENVIRONMENT
          value: Production
        volumeMounts:
        - name: logs-volume
          mountPath: C:\app\logs
        - name: config-volume
          mountPath: C:\app\web.config
          subPath: web.config
        resources:
          requests:
            memory: 2Gi
            cpu: 500m
          limits:
            memory: 4Gi
            cpu: 1000m
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 60
          periodSeconds: 15
      volumes:
      - name: logs-volume
        persistentVolumeClaim:
          claimName: windows-logs-pvc
      - name: config-volume
        configMap:
          name: dotnet-app-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: dotnet-app-config
data:
  web.config: "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<configuration>\n  <system.web>\n\
    \    <compilation debug=\"false\" targetFramework=\"4.8\" />\n    <httpRuntime\
    \ targetFramework=\"4.8\" />\n  </system.web>\n  <system.webServer>\n    <handlers>\n\
    \      <remove name=\"ExtensionlessUrlHandler-Integrated-4.0\" />\n      <add\
    \ name=\"ExtensionlessUrlHandler-Integrated-4.0\" path=\"*.\" verb=\"*\" type=\"\
    System.Web.Handlers.TransferRequestHandler\" preCondition=\"integratedMode,runtimeVersionv4.0\"\
    \ />\n    </handlers>\n  </system.webServer>\n  <appSettings>\n    <add key=\"\
    BlobContainerName\" value=\"appdata\" />\n    <add key=\"LogDirectory\" value=\"\
    C:\\app\\logs\" />\n  </appSettings>\n</configuration>\n"
---
apiVersion: v1
kind: Service
metadata:
  name: dotnet-framework-app
spec:
  selector:
    app: dotnet-framework-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**说明：**

1. **Secret 配置：**
   - 部署前应从受保护的来源或外部 Secret 管理器创建 azure-storage-secret；本例不提供账户密钥。
   - 应用可通过环境变量安全地读取它。

2. **PersistentVolumeClaim：**
   - 为日志文件申请 10 GB 持久化存储。
   - 使用与 Windows 兼容的 Azure Files SMB CSI StorageClass。
   - 使用 ReadWriteMany，使不同节点上的副本都能挂载此共享目录。

3. **Deployment 配置：**
   - 使用 `nodeSelector`，只调度到 Windows 节点。
   - 使用 .NET Framework 应用镜像。
   - 通过环境变量提供 Azure Storage 连接字符串。
   - 为日志目录挂载持久卷。
   - 从 ConfigMap 挂载 web.config 文件。
   - 设置合适的资源请求和限制。
   - 配置 readiness 和 liveness probe 进行健康检查。

4. **ConfigMap 配置：**
   - 为 .NET Framework 应用提供 web.config 文件。
   - 包含应用设置和配置。

5. **Service 定义：**
   - 创建用于访问应用的 ClusterIP Service。

**注意：**
- 实际环境中应根据需要调整镜像仓库地址、StorageClass、资源需求等。
- .NET Framework 应用必须使用基于 Windows Server Core 的镜像。
- 生产环境可以通过 ingress controller 或负载均衡器配置外部访问。
- Azure Storage 连接字符串等敏感信息应与 Azure Key Vault 等外部 Secret 管理系统集成。

请让每个副本写入不同的文件名或 Pod 专属子目录。应用必须读取这些环境变量并实现 /health。ConfigMap 的 subPath 挂载不会自动更新。
</details>

## 高级主题

1. containerd 1.x 中，哪个设置用于选择 Windows Pod sandbox 镜像？
   - A) sandbox_image 设置
   - B) 日志级别和日志路径
   - C) 内存限制和 CPU 共享
   - D) 镜像拉取策略和 registry 配置

<details>
<summary>显示答案</summary>

**答案：A) sandbox_image 设置**

**说明：**
containerd 1.x 使用 `plugins."io.containerd.grpc.v1.cri".sandbox_image`。在 containerd 2.x 的 v3 配置中，该设置为 `plugins."io.containerd.cri.v1.images".pinned_images.sandbox`。应以已安装运行时的 `containerd config default` 和 Windows 安装流程为准；不要混用不同配置版本的说明。

sandbox 镜像必须支持主机上的 Windows build。仅适用于 Linux 的 pause 镜像不能在 Windows 上运行。CNI/HNS 负责配置网络，而 sandbox 维持 Pod 网络的生命周期。registry/镜像拉取配置、runhcs 运行时、CNI 路径和日志配置也都很重要。请使用发行版经过测试的 Windows sandbox 镜像，而不是直接复制旧的 3.6 标签。
</details>

2. 在 Windows 容器中使用 Hyper-V 隔离模式的主要优点是什么？
   - A) 性能更好且资源开销更低
   - B) 能够运行与主机 OS 版本不同的容器
   - C) 提高容器之间的网络通信速度
   - D) 支持更多 Windows API 和功能

<details>
<summary>显示答案</summary>

**答案：B) 能够运行与主机 OS 版本不同的容器**

**说明：**
Windows 容器使用 Hyper-V 隔离模式的主要优点，是能够运行与主机 OS 版本不同的容器。这是 Windows 容器的一项重要特性，在现代基础设施上运行旧版应用时尤其有用。

Hyper-V 隔离模式的主要优点：

1. **版本兼容性：**
   - 解决主机 OS 与容器 OS 版本不匹配的问题。
   - 例如，可以在 Windows Server 2022 主机上运行基于 Windows Server 2019 的容器。
   - 进程隔离模式无法做到这一点（进程隔离要求主机和容器使用相同的内核版本）。

2. **增强安全隔离：**
   - 每个容器都在轻量级虚拟机中运行，隔离更强。
   - 加强容器之间以及容器与主机之间的安全边界。
   - 适用于多租户环境或运行不可信代码的场景。

3. **内核级隔离：**
   - 每个容器都有自己的 Windows 内核实例。
   - 这样可实现内核级隔离，某个容器中的内核问题不会影响其他容器或主机。

**Kubernetes 不支持 Hyper-V 隔离，也没有可启用该模式的 Pod 注解**。以上内容仅用于介绍 Windows OS 的背景。

Hyper-V 隔离模式的缺点：
- 资源使用量更高（内存、CPU）。
- 启动时间更长。
- 主机必须启用 Hyper-V 功能。

其他选项的问题：
- Hyper-V 隔离的性能更低、资源开销更大（A 错误）。
- 容器之间的网络通信在进程隔离模式下实际上更快（C 错误）。
- Windows API 和功能支持取决于容器 OS 版本；Hyper-V 隔离本身不会提供更多 API（D 错误）。
</details>

3. 在 Kubernetes 中使用 Windows 节点时，关于 Pod 网络，以下哪项说法正确？
   - A) Windows 节点不使用 CNI 插件，而是使用自己的网络栈
   - B) Windows 节点使用与 Linux 节点相同的 CNI 插件，但配置不同
   - C) Windows 节点必须始终使用 host network 模式
   - D) Windows 节点不支持 overlay 网络

<details>
<summary>显示答案</summary>

**答案：B) Windows 节点使用与 Linux 节点相同的 CNI 插件，但配置不同**

**说明：**
Kubernetes 中的 Windows 节点可以使用与 Linux 节点相同的 CNI（Container Network Interface）插件，但由于 Windows 使用不同的网络栈，配置方式也不同。这样可以在混合 OS 集群中保持一致的网络模型，同时兼顾不同 OS 的特性。

Windows 节点 Pod 网络的特点：

1. **CNI 插件支持：**
   - Windows 节点支持多种 CNI 插件，包括 Flannel、Calico 和 Antrea。
   - 这些插件经过设计，可同时用于 Linux 和 Windows 节点。
   - 每个插件都提供 Windows 专用组件或配置项。

2. **网络模式：**
   - Windows 节点通常支持 overlay 网络（VXLAN、GENEVE 等）。
   - 支持多种网络模式，包括 L2bridge、L2tunnel、overlay 等。
   - Flannel 的 VXLAN 模式在 Windows 节点上使用广泛。

3. **配置差异：**
   - Windows 节点使用 HNS（Host Network Service）管理网络配置。
   - 网络 endpoint 的创建和管理方式与 Linux 不同。
   - Windows 上可能无法使用某些高级网络功能。

示例：Flannel CNI 配置：
```yaml
# Linux-side Flannel ConfigMap; Windows uses separate HNS/CNI configuration.
kind: ConfigMap
apiVersion: v1
metadata:
  name: kube-flannel-cfg
  namespace: kube-system
data:
  cni-conf.json: |
    {
      "name": "cbr0",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "flannel",
          "delegate": {
            "hairpinMode": true,
            "isDefaultGateway": true
          }
        },
        {
          "type": "portmap",
          "capabilities": {
            "portMappings": true
          }
        }
      ]
    }
  net-conf.json: |
    {
      "Network": "10.244.0.0/16",
      "Backend": {
        "Type": "vxlan",
        "VNI": 4096,
        "Port": 4789
      }
    }
```

Windows 节点可能还需要其他配置：
```powershell
# Script running on Windows nodes
$env:KUBE_NETWORK = "cbr0"
$networkName = "vxlan0"
$networkMode = "overlay"
```

其他选项的问题：
- Windows 节点会使用 CNI 插件，并非只使用自己的网络栈（A 错误）。
- 常规 Windows Pod 不能使用 hostNetwork；HostProcess 是例外（C 错误）。
- Windows 节点支持 overlay 网络（例如 VXLAN）（D 错误）。
</details>

4. 关于 Kubernetes 中 Windows 节点的资源管理，以下哪项说法正确？
   - A) Windows 节点不支持资源限制
   - B) Windows 节点提供的资源限制比 Linux 节点更准确
   - C) Windows 节点使用 Job Object 实现资源限制
   - D) Windows 节点使用 cgroup 实现资源限制

<details>
<summary>显示答案</summary>

**答案：C) Windows 节点使用 Job Object 实现资源限制**

**说明：**
Kubernetes 中的 Windows 节点使用 Windows OS 功能 Job Object 为容器实现资源限制。Linux 节点则使用 cgroup。

Windows 节点资源管理的特点：

1. **Job Object：**
   - Windows 使用 Job Object 限制进程组的资源使用。
   - 容器运行时（兼容 Windows 的 containerd）会调用 Job Object API 应用 CPU 和内存限制。
   - Job Object 可以限制进程组的 CPU 时间、内存使用量、工作时间等。

2. **CPU 限制：**
   - CPU limit 会限制 CPU 时间；不要将 limit 与相对 CPU 共享权重混淆。
   - 这与 Linux 的 CPU 共享概念类似，但实现方式不同。
   - Windows 会根据 CPU 核数调整 CPU 共享。

3. **内存限制：**
   - Windows 容器使用 Job Object 设置内存限制。
   - Windows 没有 Linux OOM killer；内存超出可用量时，可能导致分配失败或分页以及性能下降。
   - Windows 的内存管理方式与 Linux 不同，因此即使设置相同的内存限制值，实际行为也可能不同。

4. **资源请求和限制配置：**
   - Windows Pod 和 Linux Pod 使用相同方式指定资源请求和限制：
     ```yaml
     resources:
       requests:
         memory: "2Gi"
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```
   - kubelet 会将这些值传给 Windows 容器运行时，再由运行时使用 Job Object 应用限制。

5. **监控和报告：**
   - kubelet 使用 Windows performance counter 监控容器资源使用情况。
   - 可通过 `kubectl top pods` 和 `kubectl top nodes` 查看这些信息。
   - metrics server 会收集这些信息，并通过 Kubernetes API 提供。

Windows 节点资源管理的注意事项：
- Windows 容器的默认资源使用量通常高于 Linux 容器。
- Windows 容器的内存开销可能更大，因此应预留足够的内存余量。
- 资源限制的具体行为可能因 Windows 版本而异。

其他选项的问题：
- Windows 节点支持资源限制（A 错误）。
- 任何一种 OS 都不能一概而论地说其资源限制更准确；二者机制不同（B 错误）。
- Windows 节点使用 Job Object，不使用 cgroup（D 错误）。
</details>

5. 在 Kubernetes 中使用 Windows 节点时，以下哪一项**不属于**合适的安全最佳实践？
   - A) 定期扫描并更新容器镜像，修复安全漏洞
   - B) 为所有 Windows Pod 启用 privileged 模式
   - C) 使用 gMSA（Group Managed Service Account）集成 Active Directory
   - D) 使用网络策略限制 Pod 间通信

<details>
<summary>显示答案</summary>

**答案：B) 为所有 Windows Pod 启用 privileged 模式**

**说明：**
“为所有 Windows Pod 启用 privileged 模式”**不属于**合适的安全最佳实践。实际上，Windows 容器不支持 privileged 模式；尝试设置该模式会导致 Pod 创建失败。

此选项不合适的原因：

1. **不支持 privileged 模式：**
   - 与 Linux 容器不同，Windows 容器不支持 privileged 模式。
   - 可信的主机级代理可使用 HostProcess；它与 privileged 标志不同。

2. **违反最小权限原则：**
   - 即使支持 privileged 模式，为所有 Pod 启用它也会违反最小权限原则。
   - 每个工作负载只能获得完成任务所需的最低权限。

3. **增加安全风险：**
   - privileged 模式允许容器访问主机系统，大幅提高安全风险。
   - 如果发生容器逃逸漏洞，整个主机系统都可能面临风险。

其他选项均属于合适的安全最佳实践：

A) **定期扫描并更新容器镜像，修复安全漏洞：**
   - 镜像扫描有助于发现和修复已知漏洞。
   - Windows 镜像应定期安装安全更新。
   - 建议将镜像扫描工具集成到 CI/CD 流水线中。

C) **使用 gMSA（Group Managed Service Account）集成 Active Directory：**
   - gMSA 让 Windows 容器能够安全地向 Active Directory 服务进行身份验证。
   - 使用 gMSA 替代硬编码凭证能够提高安全性。
   - 可自动管理和轮换密码。

D) **使用网络策略限制 Pod 间通信：**
   - 网络策略将最小权限原则应用于网络通信。
   - 将 Pod 间通信限制在必需范围内，可缩小攻击面。
   - 网络分段有助于防止攻击者横向移动。

强化 Windows 节点安全的其他最佳实践：
- 保持 Windows 节点安装最新安全补丁。
- 禁用不必要的 Windows 功能和角色。
- 正确配置 Windows 防火墙规则。
- 使用强身份验证机制。
- 从容器镜像中移除不必要的工具和组件。
- 实施运行时安全监控。
</details>

## 验证参考

- https://kubernetes.io/docs/concepts/windows/intro/
- https://kubernetes.io/docs/concepts/configuration/windows-resource-management/
- https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/#dns-windows
- https://kubernetes.io/docs/tasks/configure-pod-container/configure-gmsa/
- https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/
- https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/manage-serviceaccounts
- https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/gmsa-run-container
- https://github.com/prometheus-community/windows_exporter/blob/master/kubernetes/windows-exporter-daemonset.yaml
- https://github.com/fluent/fluent-bit-docs/blob/master/installation/downloads/windows.md
- https://github.com/containerd/containerd/blob/main/docs/cri/config.md
- https://learn.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker?view=sql-server-ver17&tabs=cli
