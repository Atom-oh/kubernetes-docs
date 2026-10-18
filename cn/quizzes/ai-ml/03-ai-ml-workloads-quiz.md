# AI/ML 工作负载测验

复习资源分配、训练与服务、存储、网络、安全、可观测性以及成本方面的适用边界。

## 测验问题

### 1. NVIDIA 设备插件公开 GPU 后，Pod 应如何申请 GPU？

- A. 只在 requests 中设置 nvidia.com/gpu:0.5
- B. 为 nvidia.com/gpu 设置整数 limits；如果也设置 request，两者的数量必须相同
- C. 只添加 nvidia.com/gpu 节点注解
- D. 将 RuntimeClass 命名为 nvidia-mps，即可自动启用共享

<details>
<summary>显示答案</summary>

**答案：B. 为 nvidia.com/gpu 设置整数 limits；如果也设置 request，两者的数量必须相同**

只设置 limits 时，request 会自动采用相同的值。可分配的 GPU 容量不是节点标签。GPU Feature Discovery 标签、MIG、MPS 和时间切片都需要单独配置；共享时隙并不保证能按比例获得 GPU 显存。

[分配和共享](../../ai-ml/01-ai-ml-workloads.md#nvidia-gpu-operator-and-device-allocation)
</details>

### 2. 在安装的旧版 Kubeflow 资源中，哪个能够理解 TensorFlow 的分布式角色？

- A. Deployment 会自动创建所有 TF_CONFIG 值
- B. Job 能保证训练成功，并同时调度所有 worker
- C. TFJob 提供特定于框架的角色和配置
- D. TFJob 内置于 Kubernetes，无需安装

<details>
<summary>显示答案</summary>

**答案：C. TFJob 提供特定于框架的角色和配置**

需要先安装相应的 CRD 和控制器，并配置重启策略、框架策略、检查点、存储和网络。恢复能力和成组调度并非普遍保证。提供实际训练代码时，普通 Job 也可以运行训练任务。

[Trainer 和旧版 API](../../ai-ml/kubeflow/05-training-operator.md)
</details>

### 3. 应如何通过 CSI 连接现有的 FSx for Lustre 文件系统？

- A. 将 Lustre CR 与包含现有 ID 的 StorageClass 结合使用
- B. 使用包含 volumeHandle/dnsname/mountname 的静态 PV，并绑定 PVC
- C. SCRATCH_2 支持所有持久化备份和吞吐量选项
- D. 对未挂载的 /data 运行 FIO 就能测量 FSx

<details>
<summary>显示答案</summary>

**答案：B. 使用包含 volumeHandle/dnsname/mountname 的静态 PV，并绑定 PVC**

静态挂载与动态创建文件系统是两种不同方式。应比较容量、IOPS/吞吐量、延迟、访问模式、权限、可用区与网络，以及备份能力。在实际挂载的卷上选择专用测试路径进行基准测试。

[静态和动态存储](../../ai-ml/01-ai-ml-workloads.md#storage-and-caching)
</details>

### 4. 分配 AI/ML 资源时应依据什么？

- A. 每个训练任务都需要 GPU
- B. 实测的 CPU、内存和 GPU 使用量、模型大小、I/O、延迟及吞吐量
- C. 始终请求最大资源
- D. 省略 requests 始终最有效率

<details>
<summary>显示答案</summary>

**答案：B. 实测的 CPU、内存和 GPU 使用量、模型大小、I/O、延迟及吞吐量**

CPU 和其他加速器也可能适用。OMP/MKL 线程设置会影响相关支持库，但不会配置 GPU 共享。CUDA 分配器设置与 Kubernetes 的 GPU 分配和隔离不同。VPA 的影响取决于运行模式、重启行为以及工作负载是否兼容。

[资源放置](../../ai-ml/01-ai-ml-workloads.md#placement-and-topology)
</details>

### 5. 选择 KServe 等模型服务平台时应检查什么？

- A. 任意模型 URI 都能立即使用
- B. 运行时镜像、模型格式、协议、存储和部署模式均符合要求
- C. 普通 Deployment 无法提供推理服务
- D. 所有模式的金丝雀发布和缩容至零行为都相同

<details>
<summary>显示答案</summary>

**答案：B. 运行时镜像、模型格式、协议、存储和部署模式均符合要求**

Deployment 可以运行推理服务器。KServe 的 Knative/Standard 模式和不同版本的 Seldon API 各有差异。可解释性、处理流程、加权路由和批量推理都不是默认普遍启用的功能。对于新用途，TorchServe 不是仍受维护的默认选择。

[KServe 模式和运行时](../../ai-ml/kubeflow/06-kserve.md)
</details>

### 6. 要根据 GPU 利用率或请求负载进行 HPA 扩缩容，需要什么？

- A. 已分配的 nvidia.com/gpu 会自动成为利用率 Resource 指标
- B. 配置指标导出器和自定义/外部指标适配器，并确保标签、单位和聚合方式正确
- C. 增加副本以修复模型准确率偏低
- D. 为同一个 Deployment 添加多个 HPA，让扩缩容效果叠加

<details>
<summary>显示答案</summary>

**答案：B. 配置指标导出器和自定义/外部指标适配器，并确保标签、单位和聚合方式正确**

标准 metrics-server 的 Resource 路径提供 CPU 和内存指标。GPU 或请求指标需要单独采集，并通过适配器公开。Pod 指标必须映射到命名空间和 Pod 标签；全局平均值可能丢失这种映射。应由一个控制器负责扩缩容，并验证负载或队列长度是否比延迟百分位数更适合作为按比例扩缩容的信号。

[HPA 示例](../../ai-ml/01-ai-ml-workloads.md#hpa-and-metrics)
</details>

### 7. 关于分布式训练的网络配置，哪项说法正确？

- A. 仅凭 zone 注解即可决定 Pod 的放置位置
- B. 挂载 GPU hostPath 就能配置 EFA/GPUDirect
- C. 一并验证节点标签决定的放置位置、硬件、驱动和插件、通信库以及网络策略
- D. NCCL 始终通过 MPI 传输数据

<details>
<summary>显示答案</summary>

**答案：C. 一并验证节点标签决定的放置位置、硬件、驱动和插件、通信库以及网络策略**

NCCL 通过 EFA 通信时会使用 AWS OFI NCCL 和 libfabric；MPI 可用于启动进程。Multus/SR-IOV、MTU 和 RDMA 配置因环境而异。通用网卡示例不能直接当作 EKS 配置使用。NetworkPolicy 如果阻止必需流量，可能影响服务可用性和性能。

[分布式训练边界](../../ai-ml/01-ai-ml-workloads.md#kubeflow-and-distributed-training)
</details>

### 8. 关于模型和数据保护，哪项说法正确？

- A. Secret 中的 base64 编码就是加密
- B. Kubernetes RBAC 会授予访问 S3/KMS 的权限
- C. 分别配置 API RBAC、工作负载 IAM、加密和密钥管理、文件凭证以及网络
- D. 默认将大型模型存储在 Secrets 中，并将解密密钥存入环境变量

<details>
<summary>显示答案</summary>

**答案：C. 分别配置 API RBAC、工作负载 IAM、加密和密钥管理、文件凭证以及网络**

Secrets 有大小限制，而且 base64 只是编码。大型模型应存放在对象存储中，并检查授权和完整性。Pod service account 并非总要拥有 Secret get 权限才能挂载 Secret 卷：通过 API 读取 Secret 与由 kubelet 投递卷数据是不同的路径。PodSecurityPolicy 已被移除；请使用当前的准入控制和 PSS。

[数据和 model 访问](../../ai-ml/01-ai-ml-workloads.md#data-and-model-access)
</details>

### 9. ML 服务的可观测性应区分哪些指标？

- A. GPU 利用率决定模型准确率
- B. ServiceMonitor 直接根据 Pod 标签选择目标
- C. 服务错误、延迟和吞吐量，资源使用情况，以及基于真实标签评估的模型质量彼此不同
- D. 所有容器日志都是 Docker JSON 格式

<details>
<summary>显示答案</summary>

**答案：C. 服务错误、延迟和吞吐量，资源使用情况，以及基于真实标签评估的模型质量彼此不同**

ServiceMonitor 根据 Service 标签和命名端口进行选择。应明确延迟指标是否包括失败请求，并避免把同一请求同时计为成功和错误。评估模型质量需要标签或真实结果。还要验证 CRI 日志分帧与应用 JSON、Grafana 数据源和面板结构、按标签聚合告警，以及零流量时的行为。

[指标和日志](../../ai-ml/01-ai-ml-workloads.md#prometheus-and-grafana)
</details>

### 10. 应如何验证成本优化效果？

- A. 对每种工作负载都使用 Spot 实例
- B. 最新一代实例始终最便宜
- C. 衡量所需性能、总成本、中断后的恢复和检查点能力，以及 Pod/节点是否确实被回收
- D. 夜间 On-Demand 费率会自动降低

<details>
<summary>显示答案</summary>

**答案：C. 衡量所需性能、总成本、中断后的恢复和检查点能力，以及 Pod/节点是否确实被回收**

Pod 数量减少并不意味着 EC2 实例会终止。检查可用性、配额、AMI 和驱动程序以及 NodePool 限制。训练节点的 taint 需要匹配的 toleration；CPU/GPU 混合节点组不等同于 EKS Hybrid Nodes。创建一个未被使用的 Autoscaler ConfigMap 不会改变控制器参数。

[Spot 和 node provisioning](../../ai-ml/01-ai-ml-workloads.md#spot-and-node-provisioning)
</details>

---

[返回学习材料](../../ai-ml/01-ai-ml-workloads.md)
