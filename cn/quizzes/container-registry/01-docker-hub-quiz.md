# Docker Hub 测验
> **最后更新**：2026 年 9 月 11 日

1. 如何界定经 NAT 出网的节点发起的匿名 Docker Hub 拉取？
   - A) 每个 Kubernetes Pod
   - B) 源 IPv4 地址或 IPv6 /64 子网
   - C) Kubernetes 命名空间
   - D) 拉取次数不受限制

<details>
<summary>显示答案</summary>

**答案**：B) 源 IPv4 地址或 IPv6 /64 子网

**说明**：共享 NAT 地址的节点可能会共同消耗同一份匿名拉取额度。应通过当前政策和响应头获取实际限额与重置窗口；已登录账户的拉取归属方式和滥用控制是另外的问题。

</details>

2. 在 Kubernetes 中，用什么资源存储用于拉取私有镜像的 Docker Hub 凭证？
   - A) ConfigMap
   - B) 类型为 `kubernetes.io/dockerconfigjson` 的 Secret
   - C) ServiceAccount
   - D) PersistentVolumeClaim

<details>
<summary>显示答案</summary>

**答案**：B) 类型为 `kubernetes.io/dockerconfigjson` 的 Secret

**说明**：Kubernetes 使用 `kubernetes.io/dockerconfigjson` 类型的 Secret 存储镜像仓库凭证。随后可在 Pod 配置中通过 `imagePullSecrets` 引用该 Secret，也可将它关联到 ServiceAccount 以便自动注入。

</details>

3. 在 Kubernetes 集群中缓解 Docker Hub 拉取速率限制，建议采取什么措施？
   - A) 使用更多 IP 地址
   - B) 配置拉取缓存或仓库同步副本
   - C) 禁用镜像拉取
   - D) 只使用本地镜像

<details>
<summary>显示答案</summary>

**答案**：B) 配置拉取缓存或仓库同步副本

**说明**：拉取缓存可以减少重复下载镜像层。缓存未命中、可变标签检查和刷新仍会访问上游，因此缓存无法完全消除速率限制。

</details>

4. 如何使用命名空间的默认 ServiceAccount，为新建 Pod 提供默认的镜像拉取凭证？
   - A) 将 Secret 添加到 kube-system 命名空间
   - B) 为该命名空间中的 default ServiceAccount 打补丁，添加 imagePullSecrets
   - C) 设置集群级 ConfigMap
   - D) 修改 kubelet 配置

<details>
<summary>显示答案</summary>

**答案**：B) 为该命名空间中的 default ServiceAccount 打补丁，添加 imagePullSecrets

**说明**：将 `imagePullSecrets` 添加到该 ServiceAccount。如果使用此账户的新 Pod 自身未指定拉取 Secret 列表，就会继承该列表。现有 Pod、其他 ServiceAccount 和其他命名空间不会被追溯更新。

</details>

5. Docker Official Images 与 Docker Hub 上其他镜像有什么区别？
   - A) 属于精选计划，其中的上游镜像和文档经过审查
   - B) 始终可以免费使用
   - C) 不受拉取速率限制
   - D) 每天自动更新

<details>
<summary>显示答案</summary>

**答案**：A) 属于精选计划，其中的上游镜像和文档经过审查

**说明**：Docker Official Images 会与上游/社区维护者合作，并按照计划标准接受审查。该徽标不能保证特定标签不存在漏洞；应核实所选摘要和维护状态。

</details>

6. Docker Verified Publisher 镜像有什么用途？
   - A) 它们是由随机贡献者提供的免费镜像
   - B) 它们来自经 Docker 验证的商业软件供应商
   - C) 它们是已弃用的旧镜像
   - D) 它们可以绕过安全扫描

<details>
<summary>显示答案</summary>

**答案**：B) 它们来自经 Docker 验证的商业软件供应商

**说明**：Docker Verified Publisher 镜像由与 Docker 合作并通过验证流程的商业软件供应商提供。这可以帮助确认镜像确实来自相应软件供应商，并由其维护，从而降低供应链安全风险。

</details>

7. 哪种 Docker Hub 订阅套餐提供无限量私有仓库？
   - A) Free 套餐
   - B) 仅 Pro
   - C) 仅 Team
   - D) Pro、Team 和 Business，但须遵守各自套餐政策

<details>
<summary>显示答案</summary>

**答案**：D) Pro、Team 和 Business，但须遵守各自套餐政策

**说明**：用量表列出的 Pro、Team 和 Business 均提供无限量私有仓库，但受套餐和合理使用条件约束。Personal 套餐包含一个私有仓库。

</details>

8. 使用 Docker Hub 公共镜像会带来哪种供应链安全风险？
   - A) 镜像可能包含漏洞或恶意代码
   - B) 镜像总是过时
   - C) 镜像无法扫描
   - D) 镜像体积过大

<details>
<summary>显示答案</summary>

**答案**：A) 镜像可能包含漏洞或恶意代码

**说明**：Docker Hub 上的公共镜像可能包含已知漏洞、过时依赖，少数情况下还可能包含恶意代码（例如仿冒拼写攻击或维护者账户遭入侵）。组织应在使用前扫描镜像，优先选择 Official Images 或 Verified Publisher 镜像，并考虑维护自有的精选基础镜像。

</details>

9. 创建 Docker Hub 镜像拉取 Secret 的正确 kubectl 命令是什么？
    - A) `kubectl create secret docker-registry my-secret --docker-server=https://index.docker.io/v1/ --docker-username=USER --docker-password=TOKEN`
    - B) `kubectl create configmap my-secret --docker-server=docker.io`
    - C) `kubectl apply secret docker my-secret`
    - D) `kubectl set image secret my-secret`

<details>
<summary>显示答案</summary>

**答案**：A) `kubectl create secret docker-registry my-secret --docker-server=https://index.docker.io/v1/ --docker-username=USER --docker-password=TOKEN`

**说明**：该命令会创建 `kubernetes.io/dockerconfigjson` 类型的 Secret。示例使用 Docker Hub 标准的 `https://index.docker.io/v1/` 凭证键。请将 USER/TOKEN 替换为相应凭证，且不要将它们提交到代码仓库；应在使用该凭证的 Pod 所属命名空间中创建 Secret。

</details>

10. 截至 2026 年 9 月，关于 Docker Hub Automated Builds 的适当建议是什么？
    - A) 将其作为所有新 CI 流水线的默认方案
    - B) 该功能没有公布退役计划
    - C) 在 2027 年 4 月 1 日前从已弃用功能迁出
    - D) 所有免费账户都可以使用

<details>
<summary>显示答案</summary>

**答案**：C) 在 2027 年 4 月 1 日前从已弃用功能迁出

**说明**：官方文档将 Automated Builds 标记为已弃用，并给出 2027 年 4 月 1 日的退役日期。旧版原生集成使用 GitHub/Bitbucket；GitLab CI 可以独立构建并推送镜像。

</details>
