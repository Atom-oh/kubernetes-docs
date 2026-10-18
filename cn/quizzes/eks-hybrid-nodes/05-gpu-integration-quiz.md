# EKS Hybrid Nodes GPU 集成测验

> **相关文档**：[GPU 集成](../../eks-hybrid-nodes/05-gpu-integration.md)
> **最后更新**：2026 年 10 月 12 日

### 1. 以下哪项陈述正确描述了 MIG？

A. 它将多个物理 GPU 合并为一个

B. 它创建受支持的、由硬件支持的计算/内存实例，但仍需考虑主机/驱动程序和应用程序 SLO

C. 它保证每个租户和每种故障的完全隔离

D. 它与软件时间切片完全相同

<details>
<summary>显示答案</summary>

**答案：B. 它创建受支持的、由硬件支持的计算/内存实例，但仍需考虑主机/驱动程序和应用程序 SLO**

**说明：** MIG 在 GPU 硬件层提供内存/故障和资源隔离。受支持的分区规格及限制取决于 GPU SKU 和驱动程序。这并不能保证共享主机的完整安全隔离或应用程序延迟。

</details>

### 2. A100 40GB 的常见规格表包含哪个分区规格？

A. 4g.40gb

B. 4g.20gb

C. 4g.80gb

D. 1g 表示一整块物理 GPU

<details>
<summary>显示答案</summary>

**答案：B. 4g.20gb**

**说明：** A100 40GB 示例包括 1g.5gb、2g.10gb、3g.20gb、4g.20gb 和 7g.40gb。4g.40gb 属于 A100 80GB 的规格集合。规格中的 g 表示计算切片数量；标称内存标签并不保证精确的可用内存容量。

</details>

### 3. 时间切片 replicas:4 提供什么？

A. 四个物理 GPU 和四个私有内存区域

B. 每个已配置 GPU 的四个逻辑访问槽，共享其内存/故障域

C. 为每个 Pod 保证四分之一的计算能力

D. 自动扩展 GPU 内存

<details>
<summary>显示答案</summary>

**答案：B. 每个已配置 GPU 的四个逻辑访问槽，共享其内存/故障域**

**说明：** 争用和工作负载行为可能改变延迟/吞吐量。请求更多副本并不能保证按比例获得计算能力。renameByDefault:true 会通告 nvidia.com/gpu.shared；应将配置连接到实际插件，而不是创建未使用的 ConfigMap。

</details>

### 4. 当前 DRA 为 GPU 分配增加了什么？

A. 无需任何供应商驱动程序即可支持 GPU

B. 仅静态 CPU 和内存请求

C. 通过 DeviceClasses 和 ResourceClaims 进行结构化设备选择/分配

D. 自动对所有 GPU 应用程序进行生产验证

<details>
<summary>显示答案</summary>

**答案：C. 通过 DeviceClasses 和 ResourceClaims 进行结构化设备选择/分配**

**说明：** 仍需要供应商驱动程序、ResourceSlices、兼容的 kubelet/runtime 和已启用的 API。当前 v1 声明使用 requests[].exactly，且 Pod resourceClaims 直接引用 resourceClaimTemplateName。

</details>

### 5. 应如何评估当前的 ResourceClaim？

A. 等待通用的 status.phase:Bound 枚举

B. 仅创建声明即可证明 GPU 可用

C. 检查 allocation.devices.results、预留、Pod 事件和驱动程序准备情况

D. 只检查旧的 resourceHandles 字段

<details>
<summary>显示答案</summary>

**答案：C. 检查 allocation.devices.results、预留、Pod 事件和驱动程序准备情况**

**说明：** 对于当前的 ResourceClaims，不存在通用的、已存储的 Pending→Allocated→Bound 阶段序列。分配/预留并不能证明设备注入或应用程序执行成功。

</details>

### 6. 以下哪项关于 GPU Operator 26.7 所有权的陈述是正确的？

A. GPUCluster 和 ClusterPolicy 应始终一起运行

B. 选择 ClusterPolicy 进行 device-plugin 管理，或选择新的 GPUCluster 工作流进行托管 DRA；二者不能共存

C. 设置 driver.enabled:false 会安装缺失的主机驱动程序

D. 控制器 nodeSelector 会自动限制每个受管理的组件

<details>
<summary>显示答案</summary>

**答案：B. 选择 ClusterPolicy 进行 device-plugin 管理，或选择新的 GPUCluster 工作流进行托管 DRA；二者不能共存**

**说明：** GPUCluster 是一个名为 gpu-cluster 的集群范围单例。托管 DRA 工作流不是从 ClusterPolicy/独立 DRA 原地迁移而来。准备相应的驱动程序/CDI/发现组件，并单独审查受管理组件的标签。

</details>

### 7. H100SXM/H200SXM 对比说明了什么？

A. 每种 H100 变体都具有相同的内存

B. NVIDIA 列出的 H100SXM 规格为 80GB/3.35TB/s，H200SXM 为 141GB/4.8TB/s；应用程序结果仍需测量

C. H200 不支持 MIG

D. H200 始终使每个应用程序的吞吐量翻倍

<details>
<summary>显示答案</summary>

**答案：B. NVIDIA 列出的 H100SXM 规格为 80GB/3.35TB/s，H200SXM 为 141GB/4.8TB/s；应用程序结果仍需测量**

**说明：** 这些是供应商 SKU 规格，而非审计基准。H100NVL/PCIe 变体有所不同。模型大小、精度、批处理、软件、互连和争用也会影响实际性能。

</details>

### 8. 以下哪项 EKS GPU 部署边界是正确的？

A. 在每个 Auto Mode 节点上安装额外的 NVIDIA device plugin

B. 所有类型的 EKS 节点都不支持 DRA

C. 使用范围受限的 Hybrid 分配组；当前 EKS Auto Mode 不支持 NVIDIA DRA driver，并且已管理其 device plugin

D. 尽可能通过多个管理器发布每个物理 GPU

<details>
<summary>显示答案</summary>

**答案：C. 使用范围受限的 Hybrid 分配组；当前 EKS Auto Mode 不支持 NVIDIA DRA driver，并且已管理其 device plugin**

**说明：** AWS 建议将 DRA 用于新的、受支持的 EKS 1.34+ 静态容量部署。使用文档规定的 driver 先决条件，并防止重复的设备所有权。Kubernetes API 成熟度与各个供应商功能门控是分开的。

</details>

### 9. 一个容器请求一个 DRA GPU。它应如何设置 CUDA_VISIBLE_DEVICES？

A. 始终设置为 0,1,2,3

B. 设置主机上发现的每个物理索引

C. 使用该变量请求额外三个 GPU

D. 让设备管理器/runtime 暴露已分配的设备；不要使用无关的物理索引覆盖它

<details>
<summary>显示答案</summary>

**答案：D. 让设备管理器/runtime 暴露已分配的设备；不要使用无关的物理索引覆盖它**

**说明：** 进程可见的 CUDA 索引可能不同于物理 GPU 索引。手动覆盖可能隐藏或误识别设备，并且不会授予额外的 GPU。引用同一个声明的多个容器仍共享同一份设备分配。

</details>

### 10. 暂停的冒烟测试 Job 和本地字段模式校验证明了什么？

A. GPU 驱动程序和模型已成功执行

B. 所有 GPU 工作负载均满足其延迟 SLO

C. 已审查的清单/配置通过了限定范围的本地检查；实际 GPU 验证需要所有者批准和执行

D. 无需进行清理验证

<details>
<summary>显示答案</summary>

**答案：C. 已审查的清单/配置通过了限定范围的本地检查；实际 GPU 验证需要所有者批准和执行**

**说明：** 使用已批准的摘要替换故意不可用的镜像，并在取消暂停一个 Job 之前验证运行时/放置/安全性。捕获结果，并在清理期间验证声明的取消准备（unprepare）/释放。仅凭 nvidia-smi 能看到设备，并不能证明 CUDA/LLM 基准测试结果。

</details>
