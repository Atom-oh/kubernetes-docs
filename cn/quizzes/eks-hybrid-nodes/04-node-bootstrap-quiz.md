# EKS Hybrid Nodes 节点引导测验

> **相关文档**：[节点引导](../../eks-hybrid-nodes/04-node-bootstrap.md)
> **最后更新**：2026 年 9 月 12 日

### 1. Hybrid nodeadm 的作用是什么？

A. 创建 EKS control plane

B. 使用 `aws/eks-hybrid` 实现安装和初始化 Hybrid 节点组件

C. 调度应用 Pod

D. 替换 CNI controller

<details>
<summary>显示答案</summary>

**答案：B. 使用 `aws/eks-hybrid` 实现安装和初始化 Hybrid 节点组件**

**解释**：使用 Hybrid 安装程序，而不是 EC2 `amazon-eks-ami` 中的 `nodeadm`。先安装依赖再执行初始化，并选择正确的操作系统/运行时来源，验证已批准的二进制文件。当前 SSM 新安装和升级要求 nodeadm 版本为 1.0.19 或更高。

</details>

### 2. 常规 Hybrid NodeConfig 使用哪些集群输入？

A. 集群名称和区域，以及受支持的凭证 provider

B. 仅 VPC ID 和子网 ID

C. 三个必须手工填写的字段：名称、端点和 CA

D. IAM 用户访问密钥和密码

<details>
<summary>显示答案</summary>

**答案：A. 集群名称和区域，以及受支持的凭证 provider**

**解释**：文档中的 Hybrid 配置使用 `spec.cluster.name`/`region`，以及 `spec.hybrid.ssm` 或 `spec.hybrid.iamRolesAnywhere`。已准备好的 Hybrid 角色提供集群发现权限。对于常规 Hybrid 初始化，要求手动复制原始 PEM CA 是不正确的。

</details>

### 3. nodeadm 支持哪一组凭证 provider？

A. IAM 用户密钥和 LDAP

B. 静态 Kubernetes token 和本地密码

C. SSM hybrid activation 和 IAM Roles Anywhere

D. EC2 instance profile 和 kubeconfig 密码

<details>
<summary>显示答案</summary>

**答案：C. SSM hybrid activation 和 IAM Roles Anywhere**

**解释**：在 `ssm` 和 `iam-ra` 中选择且只选择一个。SSM 配置在 `spec.hybrid.ssm` 下包含 `activationCode` 和 `activationId`；IAM Roles Anywhere 使用 `spec.hybrid.iamRolesAnywhere`。两种方式都需要已准备好的 Hybrid 角色和集群访问权限。

</details>

### 4. 哪项不是 kubelet 配置字段？

A. `maxPods`

B. `clusterDNS`

C. `clusterDomain`

D. `podScheduler`

<details>
<summary>显示答案</summary>

**答案：D. `podScheduler`**

**解释：**`podScheduler` 不是 kubelet 配置字段；scheduler 在 control plane 中运行。之前把 `clusterCIDR` 作为选项的题目也有歧义，因为它同样不是 kubelet 配置字段。NodeConfig 的 kubelet 设置不能代替 CNI IPAM 规划。

</details>

### 5. 自动化记录“init 命令已完成”能证明什么？

A. 节点永久处于 Ready 状态

B. init 命令已完成，且当时的本地检查已通过；仍须验证集群就绪状态

C. 所有镜像拉取和凭证续期都已测试

D. 可以安全地克隆主机及其身份

<details>
<summary>显示答案</summary>

**答案：B. init 命令已完成，且当时的本地检查已通过；仍须验证集群就绪状态**

**解释**：自动化记录应绑定主机、配置和二进制文件；中断时保留 started 状态，并拒绝自动重放状态未知的操作。`network-online.target` 和 `RemainAfterExit` 都不能证明 AWS 连通或节点已 Ready。

</details>

### 6. 如何理解 Kubernetes API server CA？

A. 每次 TLS 握手时都会自动签发 kubelet client certificate

B. 它是 registry 登录凭证

C. 它用于验证 server certificate 是否可信；client certificate 的批准/签发是另一回事

D. 它能取代 Hybrid IAM 角色

<details>
<summary>显示答案</summary>

**答案：C. 它用于验证 server certificate 是否可信；client certificate 的批准/签发是另一回事**

**解释**：验证 server 主机名和 CA 证书链。不要把 `curl -k` 当作信任验证。集群 CA、私有 registry CA 和 IAM Roles Anywhere 主机身份分别用于不同的信任场景。

</details>

### 7. 加入集群失败或初始化只完成一部分时，适当的处理方式是什么？

A. 运行 `nodeadm status`，然后立即执行 `uninstall --force`

B. 检查范围受限的私有 kubelet 日志和 nodeadm debug，验证身份与网络，再协调已记录的状态

C. 删除共享集群中的所有 Cilium CRD

D. 删除 Node 对象并假定 SSM 已注销

<details>
<summary>显示答案</summary>

**答案：B. 检查范围受限的私有 kubelet 日志和 nodeadm debug，验证身份与网络，再协调已记录的状态**

**解释**：所检查的 CLI 提供 `nodeadm debug`，不提供 `nodeadm status`。debug 会连接 AWS/集群服务；请妥善保护输出。删除 Node 对象既不会停止 kubelet，也不会注销 SSM。uninstall 是受控的移除操作，不是通用的身份验证修复方法。

</details>

### 8. 关于 Bottlerocket Pod Identity，哪项说法正确？

A. 它与 Ubuntu 完全相同，使用 NodeConfig 和 nodeadm

B. `settings.hybrid.ssm` 就是完整的文档化引导契约

C. Bottlerocket 1.39.0 及更高版本使用 provider 的引导凭证文件支持和 `hybrid-bottlerocket` agent DaemonSet

D. Base64 用户数据会加密私钥

<details>
<summary>显示答案</summary>

**答案：C. Bottlerocket 1.39.0 及更高版本使用 provider 的引导凭证文件支持和 `hybrid-bottlerocket` agent DaemonSet**

**解释**：Bottlerocket 使用不同的 settings/bootstrap-container 输入。兼容的 agent 最低版本为 v1.3.7-eksbuild.2，临时凭证路径为 `/var/eks-hybrid/.aws/credentials`。选择当前兼容的 add-on 并保护用户数据；编码不等于加密。

</details>

### 9. 哪项 Cilium 生命周期操作的范围正确？

A. 原地更改现有 cluster-pool CIDR

B. 执行限定于 Hybrid 范围的预检，并在升级前验证 DaemonSet 覆盖范围和验证 Deployment 的就绪状态

C. 不经审核，总是重复使用所有旧 Helm 值

D. 为修复一个节点而卸载所有名称中包含 cilium 的 CRD

<details>
<summary>显示答案</summary>

**答案：B. 执行限定于 Hybrid 范围的预检，并在升级前验证 DaemonSet 覆盖范围和验证 Deployment 的就绪状态**

**解释**：预检使用单独的节点选择器。现有 pool 元素和 mask size 不得更改；扩展时可以在审核后新增 pool 条目，并相应调整 EKS/路由配置。移除 CNI/CRD 是会造成干扰且应由资源所有者负责的操作。

</details>

### 10. 在所检查的版本中，`nodeadm uninstall --force` 表示什么？

A. 保证删除所有已挂载路径，包括 `/var/lib/kubelet`

B. 通用的确认绕过方式，可以代替 drain

C. 会删除更多默认路径，但 v1.0.9 及更高版本对 `/var/lib/kubelet` 的保护仍然生效

D. 会自动验证新的替代节点

<details>
<summary>显示答案</summary>

**答案：C. 会删除更多默认路径，但 v1.0.9 及更高版本对 `/var/lib/kubelet` 的保护仍然生效**

**解释**：不要盲目删除已挂载的 kubelet 路径。应先迁出工作负载，审核数据及 provider/CNI 清理步骤，并保留恢复证据。获批的重新安装顺序应是 install → config check → init；卸载后不能只执行 init。

</details>
