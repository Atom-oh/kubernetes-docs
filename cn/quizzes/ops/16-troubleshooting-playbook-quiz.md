# 故障排查手册测验

> **相关文档**: [Kubernetes/EKS 故障排查手册](../../ops/16-troubleshooting-playbook.md)

## 选择题

### 1. 一个 `Pending` Pod 显示以下 `FailedScheduling` 事件。对此消息的正确解读是什么？

```
0/15 nodes are available: 1 Insufficient cpu, 1 Insufficient memory,
6 node(s) didn't match Pod's node affinity/selector, 8 node(s) had untolerated taint(s).
```

- A) 所有 15 个 Node 都缺少 CPU 和内存
- B) 只有一个 Node 符合此 Pod 的条件，而该 Node 缺少 CPU 和内存
- C) scheduler 已损坏，无法评估任何 Node
- D) 由于 8 个 Node 的 Pod 过多（`Too many pods`），调度失败

<details>
<summary>显示答案</summary>

**答案：B) 只有一个 Node 符合此 Pod 的条件，而该 Node 缺少 CPU 和内存**

**说明：**
scheduler 按每个 Node 汇总拒绝原因。8 个 Node 因没有匹配的 toleration 而被 taint 拒绝，6 个因 nodeSelector/affinity 标签不匹配而被拒绝，剩下的一个 Node 缺少 CPU 和内存。换言之，恰好有一个 Node 满足调度约束，但它已满载——因此你需要扩大 toleration/标签范围，或添加满足这些条件的 Node（使用 Karpenter 时，标签键必须出现在 NodePool requirements 中）。

</details>

### 2. 使用私有 ECR image 的 Pod 处于 `ImagePullBackOff`，且 `describe` 事件显示 `Failed to pull image "...dkr.ecr...": ... 401 Unauthorized`。应首先怀疑什么？

- A) image tag 拼写错误
- B) Node IAM role 缺少 ECR 拉取权限（`AmazonEC2ContainerRegistryPullOnly` 或 `ReadOnly`）
- C) Docker Hub 速率限制（`toomanyrequests`）
- D) 私有 subnet 没有 NAT/VPC endpoints

<details>
<summary>显示答案</summary>

**答案：B) Node IAM role 缺少 ECR 拉取权限（`AmazonEC2ContainerRegistryPullOnly` 或 `ReadOnly`）**

**说明：**
`Failed to pull image` 后面的内容就是诊断结果。`401 Unauthorized` / `no basic auth credentials` 表示 registry 身份验证失败；对于 ECR，kubelet 使用 Node IAM role 进行身份验证，因此请检查该 role 的 ECR 拉取权限。tag 拼写错误会显示为 `not found` / `manifest unknown`，网络路径问题会显示为 `dial tcp ... i/o timeout`，而 Docker Hub 限制会显示为 `toomanyrequests`。

</details>

### 3. 一个 `CrashLoopBackOff` Pod 的 `lastState.terminated` 显示 `Reason: OOMKilled`、`Exit Code: 137`。哪项说法正确？

- A) app 自行检测到错误，并以代码 1 退出
- B) 内核因超过内存 limit 而发送 SIGKILL；提高 limit 或修复内存泄漏
- C) 它收到 SIGTERM 并正常关闭，因此无需操作
- D) image architecture（arm64/amd64）与 Node 不匹配

<details>
<summary>显示答案</summary>

**答案：B) 内核因超过内存 limit 而发送 SIGKILL；提高 limit 或修复内存泄漏**

**说明：**
退出代码 137 是 SIGKILL（128+9）。当 Reason 为 `OOMKilled` 时，内核 OOM killer 会因 container 超过其内存 limit 而终止它；相同的 137 代码而 Reason 为 `Error` 则是因其他原因导致的 SIGKILL，例如 container 未在 `terminationGracePeriodSeconds` 内退出的 liveness 失败。正常的 SIGTERM 退出代码为 143，architecture 不匹配在 shell entrypoint 下显示为 126（`cannot execute binary file: Exec format error`），或在 image 直接 exec binary 时显示为 Reason `StartError`。使用 `kubectl logs <pod> -c <container> --previous` 读取崩溃前的日志。

</details>

### 4. 所有 Pod 都是 `1/1 Running`，但请求始终无法到达 Service。`kubectl get endpointslices -l kubernetes.io/service-name=<svc>` 的 ENDPOINTS 列为空。最可能的原因是什么？

- A) CoreDNS Pod 已停止，因此名称解析失败
- B) Service `selector` 与 Pod labels 不匹配
- C) `targetPort` 与 container 监听的 port 不同
- D) NetworkPolicy 阻止 ingress

<details>
<summary>显示答案</summary>

**答案：B) Service `selector` 与 Pod labels 不匹配**

**说明：**
EndpointSlice 会列出与 Service selector 匹配的**Ready Pod**的 IP。如果每个 Pod 都是 Ready，而 slice 仍为空，则 selector 和 Pod labels 不一致（在 Helm chart 中，`selectorLabels` 和 `podLabels` 不一致是常见原因）。错误的 `targetPort` 会显示 IP 加 `connection refused`，NetworkPolicy 阻止会显示 IP 加超时，而 CoreDNS 中断会显示 `NXDOMAIN`/解析失败。在 Kubernetes 1.33+ 中，`kubectl get endpoints` 会显示弃用警告，因此应改为检查 EndpointSlices。

</details>

### 5. 一个 Node 的 conditions 显示 `DiskPressure=True (KubeletHasDiskPressure)`。node controller（kube-controller-manager）会自动为该 Node 添加哪个 taint？

- A) `node.kubernetes.io/unreachable`
- B) `node.kubernetes.io/not-ready`
- C) `node.kubernetes.io/disk-pressure`
- D) `node.kubernetes.io/memory-pressure`

<details>
<summary>显示答案</summary>

**答案：C) `node.kubernetes.io/disk-pressure`**

**说明：**
每个 Node condition 都有匹配的自动 taint：`DiskPressure` → `node.kubernetes.io/disk-pressure`、`MemoryPressure` → `node.kubernetes.io/memory-pressure`、`PIDPressure` → `node.kubernetes.io/pid-pressure`、`Ready=False` → `node.kubernetes.io/not-ready`，以及 `Ready=Unknown`（kubelet 停止发布 status，原因是 `NodeStatusUnknown`）→ `node.kubernetes.io/unreachable`。这就是为何一个 Node 可以是 `Ready`，但新的 Pod 会因 `node(s) had untolerated taint(s)` 而避开它。DiskPressure 通常由填满 root volume 的 image cache 和 container logs 导致，而 Pod 会因 `The node was low on resource: ephemeral-storage` 被 `Evicted`。

</details>

### 6. 一个 PVC 处于 `Pending`，且 `describe pvc` 仅显示 `WaitForFirstConsumer: waiting for first consumer to be created before binding`。尚未部署使用此 PVC 的任何 Pod。正确的判断是什么？

- A) StorageClass 名称拼写错误；使用 `kubectl get sc` 检查
- B) EBS CSI controller 缺少 IAM 权限
- C) 这是正常现象——`volumeBindingMode: WaitForFirstConsumer` 会将 volume 创建推迟到 Pod 被调度时
- D) PV 位于另一个 AZ，导致 `volume node affinity conflict`

<details>
<summary>显示答案</summary>

**答案：C) 这是正常现象——`volumeBindingMode: WaitForFirstConsumer` 会将 volume 创建推迟到 Pod 被调度时**

**说明：**
EKS 默认创建的 `gp2` StorageClass 使用 `WaitForFirstConsumer` binding mode。你为 EBS CSI driver 创建的 `gp3` StorageClass 只有在明确设置 `volumeBindingMode: WaitForFirstConsumer` 时才会如此——API 默认值是 `Immediate`——而验证 cluster 上的 `gp3` class 确实如此，正如手册中的 `kubectl get storageclass` 输出所示。该延迟是有意的：EBS volume 会在 Pod 最终被调度所在的 AZ 中创建，因此，在没有 Pod 使用某个 PVC 时它保持 `Pending` 并不是问题。StorageClass 拼写错误会显示为 `storageclass.storage.k8s.io "<name>" not found`，缺少 IAM 权限会显示为 `ProvisioningFailed` + `UnauthorizedOperation`/`AccessDenied`，而 AZ 不匹配会在 Pod 的 `FailedScheduling` 事件中显示为 `volume node affinity conflict`。

</details>

### 7. 从 Pod 内部发起的 AWS API 调用返回 `AccessDenied`，而被拒绝的 principal 是 Node IAM role 而不是 service account role。`kubectl get sa` 显示 `eks.amazonaws.com/role-arn` annotation，但 Pod env 中没有 `AWS_ROLE_ARN`/`AWS_WEB_IDENTITY_TOKEN_FILE`。原因和修复方法是什么？

- A) IAM role 的 permission policy 不足 → 向 policy 添加 actions
- B) annotation 是在 Pod 创建**之后**添加的，因此 webhook 从未注入 credentials → `kubectl rollout restart`
- C) 没有 OIDC provider → 重新创建 cluster
- D) EKS Pod Identity agent 已停止 → 重启 agent

<details>
<summary>显示答案</summary>

**答案：B) annotation 是在 Pod 创建之后添加的，因此 webhook 从未注入 credentials → `kubectl rollout restart`**

**说明：**
IRSA 的工作方式是 pod-identity-webhook 在 **Pod 创建时** 注入 `AWS_ROLE_ARN` 和 `AWS_WEB_IDENTITY_TOKEN_FILE` env（以及 token volume）。如果完全没有注入痕迹，说明 Pod 是在 annotation 存在之前创建的，或 SA 名称不同；SDK 因找不到 credentials 而回退到 Node role。重新创建 Pod 即可修复。permission policy 不足（A）看起来不同——env 正常，但特定 API 被拒绝——而 Pod Identity（D）可通过 `AWS_CONTAINER_CREDENTIALS_FULL_URI` env 识别。

</details>

### 8. 一个 Pod 处于 `Pending`，没有新的 NodeClaim 出现，且 Karpenter 事件显示 `all available instance types exceed limits for nodepool "graviton"`。原因是什么？

- A) Pod 的 nodeSelector 标签键不在 NodePool requirements 中
- B) 没有针对 NodePool taint 的 toleration
- C) NodePool `spec.limits`（cpu/memory）已达到上限
- D) EC2 在该 AZ 中没有容量（`InsufficientInstanceCapacity`）

<details>
<summary>显示答案</summary>

**答案：C) NodePool `spec.limits`（cpu/memory）已达到上限**

**说明：**
Karpenter 会遍历一个 Pod 的每个 NodePool，并将拒绝每个 NodePool 的原因记录为事件。`exceed limits` 表示它可添加的任何 instance 都会使 NodePool 超过其 `spec.limits`；`kubectl get nodepool -o custom-columns=...spec.limits.cpu,...status.resources.cpu` 显示 limit 和 usage 相等。缺少标签键会显示为 `label "<key>" does not have known values`，缺少 toleration 会显示为 `did not tolerate <key>=<value>:NoSchedule`，而 EC2 容量不足会在 Karpenter controller logs 中显示为 `InsufficientInstanceCapacity`。

</details>

### 9. EKS Node 上的 Pod 停滞在 `ContainerCreating`，并出现事件 `FailedCreatePodSandBox ... plugin type="aws-cni" ... failed to assign an IP address to container`。subnet 的 `AvailableIpAddressCount` 是个位数，并且 `aws-node` 使用 VPC CNI 默认值运行（`WARM_ENI_TARGET=1`，未设置 `WARM_IP_TARGET`/`MINIMUM_IP_TARGET`）。哪项说法正确？

- A) 默认值 `WARM_ENI_TARGET=1` 会使每个 Node 都附加一个完整备用 ENI 所含数量的 IP，因此 subnet 耗尽的速度远早于 Pod 数量所暗示的速度；设置 `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` 会缩小此 warm pool，因为它们优先于 warm-ENI 规则
- B) 设置 `WARM_ENI_TARGET=0` 就足够了，因为在设置 `WARM_ENI_TARGET` 时会忽略 `WARM_IP_TARGET`
- C) `ENABLE_PREFIX_DELEGATION=true` 通过附加更多 ENI 来增加 IP，因此它适用于任何 instance family
- D) `FailedCreatePodSandBox` 表示 scheduler 找不到 Node，因此这与 `Too many pods` 是同一种失败

<details>
<summary>显示答案</summary>

**答案：A) 默认值 `WARM_ENI_TARGET=1` 会使每个 Node 都附加一个完整备用 ENI 所含数量的 IP，因此 subnet 耗尽的速度远早于 Pod 数量所暗示的速度；设置 `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` 会缩小此 warm pool，因为它们优先于 warm-ENI 规则**

**说明：**
仅使用默认的 `WARM_ENI_TARGET=1` 时，ipamd 会在每个 Node 上保留一个完整的备用 ENI（m5.xlarge 上每个 ENI 有 15 个 IP），因此在小型 subnet 中，预先占用的 IP 会在 Pod 之前很久就耗尽。一旦设置 `WARM_IP_TARGET`/`MINIMUM_IP_TARGET`，它们就会覆盖 warm-ENI 规则——手册的验证 cluster 使用 `WARM_IP_TARGET=3`、`MINIMUM_IP_TARGET=6`，因此一个 Node 在其 Pod 使用的 IP 之外只保留 3 个备用 IP，并且已分配的 IP 总数永远不少于 6 个（`MINIMUM_IP_TARGET` 限制的是总数，即正在使用的加备用的 IP，而非备用数量）。B 将优先级颠倒了。prefix delegation（C）会将 /28 prefixes 分配给现有 ENI slots，而不是添加 ENI，并且需要基于 Nitro 的 instances 以及重新计算 max-pods。D 混淆了两种症状：`FailedCreatePodSandBox` 在调度后触发，即 kubelet 向一个已无剩余 IP 的 Node 请求 CNI 分配 IP 时；`Too many pods` 则是 scheduler 因 `allocatable.pods` 已达到上限而拒绝 Node——两者有相同的根本原因（没有可分配的 IP），但发生在不同阶段。

</details>
