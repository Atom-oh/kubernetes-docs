# 故障排查手册测验

> **相关文档**: [Kubernetes/EKS 故障排查手册](../../ops/16-troubleshooting-playbook.md)

## 选择题

### 1. FailedScheduling 报告了一个 CPU 不足、一个内存不足、六个亲和性不匹配和八个污点不匹配。应如何解读？

- A) 原因计数可能重叠；应逐个检查节点状态
- B) 必定是同一个节点同时缺少 CPU 和内存
- C) 15 个节点都缺少 CPU
- D) 调度器没有评估任何节点

<details>
<summary>显示答案</summary>

**答案：A) 原因计数可能重叠；应逐个检查节点状态**

调度器可能按节点汇总多种拒绝原因。仅凭计数无法将节点划分为互不重叠的集合，也无法识别具体是哪个节点。检查 nodeName 和 PodScheduled，以区分调度阶段与镜像拉取或 CNI 初始化等待。

</details>

### 2. 普通 EC2 工作节点上的 ECR 镜像拉取失败，并返回 401 Unauthorized。首先应检查什么？

- A) Docker Hub 的速率限制
- B) kubelet 镜像凭证路径和节点角色的 ECR 权限
- C) 容器的存活探针路径
- D) 应用程序的 S3 存储桶名称

<details>
<summary>显示答案</summary>

**答案：B) kubelet 镜像凭证路径和节点角色的 ECR 权限**

不要把应用程序的 IRSA 身份与镜像拉取身份混为一谈。Fargate 使用 Pod 执行角色。crictl pull 不会自动复用 kubelet 凭证提供程序或 imagePullSecrets，因此它不是等价的身份验证测试。

</details>

### 3. 一个容器的终止原因是 OOMKilled，退出码为 137。下一步应怎么做？

- A) 运行时间长就能证明存在内存泄漏
- B) 检查容器限制、节点压力、内存时间序列和内核事件
- C) 立即将限制加倍
- D) 将其视为正常处理 SIGTERM 后的退出并忽略

<details>
<summary>显示答案</summary>

**答案：B) 检查容器限制、节点压力、内存时间序列和内核事件**

137 通常表示 SIGKILL（128+9）；OOMKilled 则进一步说明发生了 OOM。单凭这些信息不能证明存在内存泄漏，也不能证明故障完全由容器限制引起。若退出码为 137 但原因不同，应单独调查。根据应用程序的行为，处理 SIGTERM 后的退出码也可能不是 143。

</details>

### 4. 如果某个 IP 出现在 EndpointSlice 的 ENDPOINTS 列中，可以得出什么结论？

- A) 每个 Pod 都处于 Ready 状态
- B) Service 请求一定会成功
- C) 该地址存在；应分别检查 ready、serving 和 terminating
- D) 所有 NetworkPolicy 都允许流量

<details>
<summary>显示答案</summary>

**答案：C) 该地址存在；应分别检查 ready、serving 和 terminating**

未就绪的 Pod 也可能出现在其中，并带有 ready=false。容器的 READY 计数与 Pod Ready condition 也不同。若地址缺失，应检查 selector、namespace 和 EndpointSlice 的管理方式；没有 selector 的 Service 可能需要手动管理 EndpointSlice。

</details>

### 5. 当 DiskPressure=True 时，对应哪个自动污点？

- A) node.kubernetes.io/unreachable
- B) node.kubernetes.io/not-ready
- C) node.kubernetes.io/disk-pressure
- D) node.kubernetes.io/memory-pressure

<details>
<summary>显示答案</summary>

**答案：C) node.kubernetes.io/disk-pressure**

节点可以保持 Ready，但压力仍会阻止新工作负载调度。除了可用字节数，还应检查 inode 和文件系统布局。Ready=Unknown 对应 unreachable；Ready=False 对应 not-ready。

</details>

### 6. PVC 使用 WaitForFirstConsumer StorageClass，且目前还没有使用它的 Pod。应如何判断？

- A) 一定是 CSI IAM 权限错误
- B) 名为 gp3 的 StorageClass 一定配置错误
- C) 这可能是正常情况：绑定或置备会等待使用者的调度约束
- D) 立即删除 PV

<details>
<summary>显示答案</summary>

**答案：C) 这可能是正常情况：绑定或置备会等待使用者的调度约束**

行为取决于 volumeBindingMode，而不是 StorageClass 的名称。API 默认值是 Immediate，因此应检查实际配置值。如果使用者 Pod 也处于 Pending，应检查 FailedScheduling 和拓扑约束。删除 PVC 并不是默认的诊断操作。

</details>

### 7. Pod 创建后才给 ServiceAccount 添加 IRSA 注解，而旧 Pod 没有注入字段。下一步该怎么做？

- A) 重新创建集群
- B) 检查 serviceAccountName 和 webhook 配置，再评估影响后重新创建 Pod
- C) 向节点角色授予 AdministratorAccess
- D) 无论 ServiceAccount 如何配置，都等待现有环境自行改变

<details>
<summary>显示答案</summary>

**答案：B) 检查 serviceAccountName 和 webhook 配置，再评估影响后重新创建 Pod**

凭证注入发生在 Pod 创建时，现有 Pod 不会自动修改。重新创建后，应验证注入结果和实际调用 AWS 的身份。其他 SDK 凭证提供程序可能优先使用；如果 IMDS 访问被阻止，也无法回退到节点角色。

</details>

### 8. Karpenter 报告 nodepool 的所有可用实例类型都超出限制。这是什么意思？

- A) 只有当前用量恰好达到限制时才会发生
- B) 添加任何候选实例都会超过 NodePool 剩余的可用容量
- C) 该区域不存在任何 EC2 实例类型
- D) Pod 一定缺少 toleration

<details>
<summary>显示答案</summary>

**答案：B) 添加任何候选实例都会超过 NodePool 剩余的可用容量**

例如，当前 CPU 用量为 7、限制为 8，而最小候选实例有 2 个 CPU；即使用量尚未达到限制，也会出现此错误。还应检查其他资源限制、DaemonSet 开销和节点要求。Nominated 事件不能证明节点或 Pod 已就绪。

</details>

### 9. 在 secondary-IP 模式下，WARM_IP_TARGET=3、MINIMUM_IP_TARGET=6，且已有一个 IP 正在使用。哪种解读正确？

- A) IP 总数必须是四个
- B) 同时满足两个目标可能需要六个 IP，其中五个空闲
- C) MINIMUM_IP_TARGET 表示至少需要六个空闲 IP
- D) Pod 过多就能证明子网耗尽

<details>
<summary>显示答案</summary>

**答案：B) 同时满足两个目标可能需要六个 IP，其中五个空闲**

Warm target 表示需要保留的空闲地址；minimum target 则是已用和空闲地址总量的下限。IPAM 协调、ENI 限制和前缀分配粒度都会影响实际数量。正值的 IP target 优先于 WARM_ENI_TARGET。前缀模式需要受支持的实例和连续的 /28 地址块；应将 max-pods 问题与实际 IP 耗尽分开诊断。

</details>
