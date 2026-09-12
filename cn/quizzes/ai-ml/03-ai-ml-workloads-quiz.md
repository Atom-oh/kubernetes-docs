# AI/ML 工作负载测验

复习资源分配、训练/服务、存储、网络、安全性、可观测性和成本边界。

## 测验问题

### 1. Pod 应如何请求由 NVIDIA device plugin 暴露的 GPU？

- A. 仅设置 nvidia.com/gpu:0.5 请求
- B. 指定整数 nvidia.com/gpu limits；如果也提供 request，则其值应相等
- C. 仅添加 nvidia.com/gpu node annotation
- D. 将 RuntimeClass 命名为 nvidia-mps 以自动启用共享

<details>
<summary>显示答案</summary>

**答案：B. 指定整数 nvidia.com/gpu limits；如果也提供 request，则其值应相等**

单独设置 limits 隐含相等的 request。可分配的 GPU 容量不是 node label。GPU Feature Discovery labels、MIG、MPS 和 time-slicing 需要单独配置；共享 slot 不保证获得 GPU memory 的一部分。

[分配和共享](../../ai-ml/01-ai-ml-workloads.md#nvidia-gpu-operator-and-device-allocation)
</details>

### 2. 已安装的旧版 Kubeflow resource 中，哪个能够理解 TensorFlow distributed roles？

- A. Deployment 自动创建所有 TF_CONFIG values
- B. Job 保证训练成功以及 worker 的同时放置
- C. TFJob 提供特定于框架的 roles/configuration
- D. TFJob 内置于 Kubernetes 中，无需安装

<details>
<summary>显示答案</summary>

**答案：C. TFJob 提供特定于框架的 roles/configuration**

安装其 CRD/controller，并配置 restart policy、framework strategy、checkpoints、storage 和 networking。恢复和 gang scheduling 并非通用保证。提供实际执行代码时，常规 Job 也可以进行训练。

[Trainer 和旧版 API](../../ai-ml/kubeflow/05-training-operator.md)
</details>

### 3. 应如何通过 CSI 连接现有的 FSx for Lustre filesystem？

- A. 将 Lustre CR 与包含现有 ID 的 StorageClass 相结合
- B. 使用包含 volumeHandle/dnsname/mountname 的 static PV 和已绑定的 PVC
- C. SCRATCH_2 支持所有 persistent backup/throughput 选项
- D. 针对未挂载的 /data 运行 FIO 可测量 FSx

<details>
<summary>显示答案</summary>

**答案：B. 使用包含 volumeHandle/dnsname/mountname 的 static PV 和已绑定的 PVC**

静态挂载不同于动态创建 filesystem。比较容量、IOPS/throughput、latency、access patterns、permissions、AZ/network 和 backups。在实际挂载的 volume 上针对专用测试路径进行 benchmark。

[静态和动态存储](../../ai-ml/01-ai-ml-workloads.md#storage-and-caching)
</details>

### 4. 什么应指导 AI/ML 资源分配？

- A. 每个 training job 都需要 GPU
- B. 实测的 CPU/memory/GPU 使用量、model size、I/O、latency 和 throughput
- C. 始终请求最大资源
- D. 省略 requests 始终最有效率

<details>
<summary>显示答案</summary>

**答案：B. 实测的 CPU/memory/GPU 使用量、model size、I/O、latency 和 throughput**

CPU 和其他 accelerator 也可能合适。OMP/MKL thread settings 会影响支持库，而不是 GPU sharing。CUDA allocator settings 与 Kubernetes GPU allocation/isolation 不同。VPA 的影响取决于 mode、restart behavior 和 workload compatibility。

[资源放置](../../ai-ml/01-ai-ml-workloads.md#placement-and-topology)
</details>

### 5. 选择 KServe 等 serving platform 时应检查什么？

- A. 任意 model URI 都能立即运行
- B. Runtime image、model format、protocol、storage 和 deployment mode 符合要求
- C. 普通 Deployment 无法提供 inference
- D. 所有模式提供相同的 canary 和 scale-to-zero 行为

<details>
<summary>显示答案</summary>

**答案：B. Runtime image、model format、protocol、storage 和 deployment mode 符合要求**

Deployment 可以运行 inference server。KServe Knative/Standard 和有版本的 Seldon API 各不相同。Explainability、processing、weighted routing 和 batch inference 并非普遍启用的默认功能。TorchServe 不是新用途的受维护默认选项。

[KServe 模式和 runtimes](../../ai-ml/kubeflow/06-kserve.md)
</details>

### 6. 基于 GPU utilization 或 request load 进行 HPA scaling 需要什么？

- A. 已分配的 nvidia.com/gpu 会自动成为 utilization Resource metric
- B. 具有正确 labels、units 和 aggregation 的 exporters 及 custom/external metrics adapters
- C. 增加 replicas 以修复较低的 model accuracy
- D. 为同一个 Deployment 附加多个 HPA 以实现叠加扩缩容

<details>
<summary>显示答案</summary>

**答案：B. 具有正确 labels、units 和 aggregation 的 exporters 及 custom/external metrics adapters**

标准 metrics-server Resource 路径公开 CPU/memory。GPU/request metrics 需要单独的 collection/adapters。Pod metrics 必须映射到 namespace/Pod labels；全局平均值可能丢失该映射。使用一个 scaling owner，并验证 load/queue 是否比 latency percentiles 更适合作为比例信号。

[HPA 示例](../../ai-ml/01-ai-ml-workloads.md#hpa-and-metrics)
</details>

### 7. 关于 distributed-training networking，哪项说法正确？

- A. 单独的 zone annotation 控制放置
- B. GPU hostPath mounts 配置 EFA/GPUDirect
- C. 一并验证 node-label placement、hardware、drivers/plugins、communication libraries 和 network policies
- D. NCCL 始终通过 MPI 传输数据

<details>
<summary>显示答案</summary>

**答案：C. 一并验证 node-label placement、hardware、drivers/plugins、communication libraries 和 network policies**

EFA 上的 NCCL 使用 AWS OFI NCCL 和 libfabric；MPI 可以启动 processes。Multus/SR-IOV、MTU 和 RDMA configuration 因环境而异。通用 NIC 示例并非可直接使用的 EKS settings。NetworkPolicy 可能因阻止所需流量而影响 availability/performance。

[分布式训练边界](../../ai-ml/01-ai-ml-workloads.md#kubeflow-and-distributed-training)
</details>

### 8. 哪项 model/data protection 说法正确？

- A. Secret base64 就是 encryption
- B. Kubernetes RBAC 授予 S3/KMS permissions
- C. 分别配置 API RBAC、workload IAM、encryption/key management、file credentials 和 networking
- D. 默认将大型 models 存储在 Secrets 中，并将 decryption keys 存储在 environment variables 中

<details>
<summary>显示答案</summary>

**答案：C. 分别配置 API RBAC、workload IAM、encryption/key management、file credentials 和 networking**

Secrets 有大小限制，base64 是 encoding。对大型 models 使用带 authorization/integrity checks 的 object storage。Pod service account 并不总是需要 Secret get permission 才能挂载 Secret volume：API 读取与 kubelet volume delivery 不同。PodSecurityPolicy 已被移除；请使用当前 admission/PSS controls。

[数据和 model 访问](../../ai-ml/01-ai-ml-workloads.md#data-and-model-access)
</details>

### 9. ML service observability 应区分什么？

- A. GPU utilization 决定 accuracy
- B. ServiceMonitor 直接选择 Pod labels
- C. Service errors/latency/throughput、resource use 和带 ground-truth 的 model quality 是不同的
- D. 所有 container logs 都是 Docker JSON

<details>
<summary>显示答案</summary>

**答案：C. Service errors/latency/throughput、resource use 和带 ground-truth 的 model quality 是不同的**

ServiceMonitor 选择 Service labels/named ports。定义 latency 是否包括 failures，并避免将一个 request 同时计为 success 和 error。Quality 需要 labels/ground truth。验证 CRI framing 与 app JSON、Grafana datasource/panel schema、带 labels 的 alert aggregation 以及 zero-traffic behavior。

[指标和日志](../../ai-ml/01-ai-ml-workloads.md#prometheus-and-grafana)
</details>

### 10. 应如何验证 cost optimization？

- A. 对每个 workload 使用 Spot
- B. 最新 instances 始终最便宜
- C. 衡量所需 performance、total cost、interruption recovery/checkpointing 以及实际的 Pod/node reclamation
- D. 夜间会自动降低 On-Demand rates

<details>
<summary>显示答案</summary>

**答案：C. 衡量所需 performance、total cost、interruption recovery/checkpointing 以及实际的 Pod/node reclamation**

更少的 Pods 并不意味着 EC2 termination。检查 availability、quotas、AMI/drivers 和 NodePool limits。Training taints 需要匹配的 tolerations；混合 CPU/GPU groups 不是 EKS Hybrid Nodes。创建未使用的 Autoscaler ConfigMap 不会改变 controller flags。

[Spot 和 node provisioning](../../ai-ml/01-ai-ml-workloads.md#spot-and-node-provisioning)
</details>

---

[返回学习材料](../../ai-ml/01-ai-ml-workloads.md)
