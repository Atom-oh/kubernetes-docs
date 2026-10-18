# EKS Hybrid Nodes 受限互联网环境配置测验

> **相关文档**：[受限互联网环境配置](../../eks-hybrid-nodes/03-airgap-setup.md)
> **最后更新**：2026 年 9 月 12 日

### 1. 关于 EKS Hybrid Nodes 的连接需求，哪项说法正确？

A. 通过物理方式传输镜像后，就不再需要连接 AWS

B. 节点仍需连接 EKS 控制平面和凭证服务

C. 私有 S3 存储桶负责托管 EKS 控制平面

D. VPN 连接等同于物理隔离

<details>
<summary>显示答案</summary>

**答案：B. 节点仍需连接 EKS 控制平面和凭证服务**

**说明：**
限制对公网的访问与通过私有网络连接 AWS 可以同时实现。物理断网的网络无法提供 Hybrid Nodes 所需的实时控制平面和凭证服务连接路径。

</details>

### 2. 为什么将 PHZ 中的 hybrid-assets.eks.amazonaws.com 别名指向 S3 仍然不够？

A. S3 从不支持私有 DNS

B. 必须先安装 ECR

C. DNS 不会保留原始 TLS 主机名，也不会处理对象路由或授权

D. 所有 HTTPS 请求都会自动使用 IAM 角色

<details>
<summary>显示答案</summary>

**答案：C. DNS 不会保留原始 TLS 主机名，也不会处理对象路由或授权**

**说明：**
S3 接口端点支持私有 DNS。但 DNS 别名不会改写 TLS SNI、HTTP Host 标头、对象路径或身份验证。应使用经批准的镜像准备流程，或实际可访问的自定义 manifest URL；不要关闭证书验证。

</details>

### 3. nodeadm v1.0.20 的 private 安装模式会做什么？

A. 根据本地 manifest 安装所有操作系统依赖

B. 跳过操作系统软件包安装，但仍安装凭证和 EKS 制品

C. 使所有 AWS API 调用都变为可选

D. 自动为每个 S3 制品下载签名

<details>
<summary>显示答案</summary>

**答案：B. 跳过操作系统软件包安装，但仍安装凭证和 EKS 制品**

**说明：**
已发布的配置要求同时使用 `--manifest-override` 和 `--private-mode`。运行时和操作系统依赖须另行准备。SSM 的安装器/签名来源是单独构造的；manifest 使用 `file://` 并不意味着制品也支持 `file://`。

</details>

### 4. 制品准备脚本遇到缺少校验和或校验和不匹配时应如何处理？

A. 发出警告后继续发布其余文件

B. 只要有一个文件通过校验就接受本次运行

C. 根据下载的文件生成新的预期校验和

D. 停止处理并保留失败的候选制品以供调查

<details>
<summary>显示答案</summary>

**答案：D. 停止处理并保留失败的候选制品以供调查**

**说明：**
每个必需文件都必须匹配可信且经过审核的校验和记录。重新生成预期值会使校验失去意义。哈希值一致本身也不能独立证明发布者身份。

</details>

### 5. IAM Roles Anywhere 更新服务适用于哪种情况？

A. 所有安装方式都使用该服务，包括 SSM

B. 启用 enableCredentialsFile 时使用该服务；普通 credential-process 用法是另一条路径

C. 该服务并不存在，应始终将其删除

D. 该服务可以免除证书续期

<details>
<summary>显示答案</summary>

**答案：B. 启用 enableCredentialsFile 时使用该服务；普通 credential-process 用法是另一条路径**

**说明：**
`aws_signing_helper_update.service` 确实存在于凭证文件模式中。应为相应服务和调用进程配置合适的环境变量，包括 nodeadm 的代理检测及 `--with-proxy` 行为。证书生命周期管理和 AWS 网络连接仍不可缺少。

</details>

### 6. Hybrid Nodes 制品清单应包含哪些镜像？

A. 所有节点都固定使用同一组 VPC CNI 镜像

B. 只包含 kubelet，因为它就是 CNI 镜像

C. 实际受支持的 CNI、DNS、数据平面、sandbox 和工作负载镜像，包括 init container 及相应平台

D. 将任意 Kubernetes 补丁版本号加上 -eksbuild.1 就能构造出有效标签

<details>
<summary>显示答案</summary>

**答案：C. 实际受支持的 CNI、DNS、数据平面、sandbox 和工作负载镜像，包括 init container 及相应平台**

**说明：**
VPC CNI 不是 Hybrid Nodes 使用的 CNI。应根据实际部署的 manifest 和获准的 digest 准备制品。私有 ECR 拉取还需要 S3 层下载路径和工作负载的镜像拉取凭证；仅列出仓库并不足够。

</details>

### 7. nodeadm 启动前，哪种配置检查方式有效？

A. nodeadm init --dry-run

B. nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml

C. 执行 curl -k 后报告节点就绪

D. 配置文件缺失时跳过并返回成功

<details>
<summary>显示答案</summary>

**答案：B. nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml**

**说明：**
应使用内容完整且受到保护的配置文件。`config check` 只验证配置，不证明私有网络可用，也不会注册节点。检查过的 `init` 命令没有 `--dry-run` 标志。

</details>

### 8. 哪种代理配置修改最能保留现有 kube-proxy DaemonSet？

A. 使用新的 JSON Patch 数组替换 /containers/0/env

B. 删除 NODE_NAME，因为代理不需要它

C. 按容器名和 env 名称审核后使用 strategic merge，并保留现有参数和 NODE_NAME

D. 始终将 .eks.amazonaws.com 排除在代理之外

<details>
<summary>显示答案</summary>

**答案：C. 按容器名和 env 名称审核后使用 strategic merge，并保留现有参数和 NODE_NAME**

**说明：**
JSON Patch 若向已存在的 env 成员执行 add，可能替换整个数组。应将补丁限定在 kube-proxy，并保留其他值。范围过宽的 `.eks.amazonaws.com` 代理绕过规则也会匹配公网 hybrid-assets 下载主机名。

</details>

### 9. 使用传输过来的 OCI 镜像归档前，必须完成哪些检查？

A. 只需确认 tar 导入成功

B. 验证获批哈希、digest 和平台内容、目标引用，以及实际运行时拉取行为

C. 关闭源 registry 的 TLS 验证以避免证书错误

D. 假定只需支持构建主机使用的架构

<details>
<summary>显示答案</summary>

**答案：B. 验证获批哈希、digest 和平台内容、目标引用，以及实际运行时拉取行为**

**说明：**
Skopeo 的 `--all` 会保留平台列表；如果无法保留 digest，`--preserve-digests` 会报错。导入后的名称、containerd 的 `k8s.io` 命名空间、`imagePullPolicy` 和垃圾回收都会影响实际 Pod 是否能启动。

</details>

### 10. 私有制品仓库采用哪种更新做法较为合适？

A. 每周自动覆盖生产环境的 latest 键

B. 将 head-object 返回的 AccessDenied 当作对象不存在

C. 在来源、兼容性和代表性节点验证通过后，批准新的不可变候选版本

D. 保证所有环境的带宽节省为 50–80%

<details>
<summary>显示答案</summary>

**答案：C. 在来源、兼容性和代表性节点验证通过后，批准新的不可变候选版本**

**说明：**
应使用自有存储桶、明确的预期所有者，并分离发布者和读取者权限；遇到未知错误应停止处理。条件式对象写入不能让整次上传具备原子性。此前提及的带宽百分比未经验证，只是历史示例，不能视为保证的测量结果。

</details>
