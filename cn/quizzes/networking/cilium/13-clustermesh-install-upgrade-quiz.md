# 第 13 部分：版本、安装/升级与 Cluster Mesh 测验

> **Cilium 1.20.2 · 2026-10-15**

1. **对于升级和回滚，上游测试的是哪条升级路径？**
   - A) 仅允许连续的小版本升级（例如 1.19 到 1.20，或反向回滚），且先更新到当前小版本的最新补丁
   - B) 只要安装了最新补丁，任意 N 到 N+2 小版本升级都可以
   - C) 只要升级前 Chart 检查通过，就可以升级到任何最新小版本
   - D) 仅升级 Agent，Operator 可在之后再升级一个小版本

   <details>
   <summary>显示答案</summary>

   **答案**：A) 仅允许连续的小版本升级（例如 1.19 到 1.20，或反向回滚），且先更新到当前小版本的最新补丁

   跳过小版本未经测试，所有组件都必须运行相同版本。先更新到最新补丁可以确保回滚目标已经包含所有修复。

   </details>

2. **升级到新的小版本时，为什么不能运行 `helm upgrade --reuse-values`？**
   - A) 它会删除 Cilium CRD
   - B) 它会将 `upgradeCompatibility` 重置为新版本
   - C) 它会强制将 OCI Chart 换为经典仓库 Chart
   - D) 它会重用旧版本 release 的 values 并忽略新 Chart 默认值，可能渲染出无效 manifest

   <details>
   <summary>显示答案</summary>

   **答案**：D) 它会重用旧版本 release 的 values 并忽略新 Chart 默认值，可能渲染出无效 manifest

   使用 `helm get values` 保存当前值，检查重命名或已移除的键，并通过 `-f` 传入。只有在 Chart 版本未变时（例如在同一版本应用 Cluster Mesh 配置）才能使用 `--reuse-values`。

   </details>

3. **`maxConnectedClusters` 的默认值是多少？将它设为 511 会带来什么代价？**
   - A) 255；必须禁用 KVStoreMesh
   - B) 255；集群本地身份的最大数量会从 65535 降至 32767
   - C) 127；集群名称长度上限会减半
   - D) 511；身份范围不变，但仅支持 Overlay 模式

   <details>
   <summary>显示答案</summary>

   **答案**：B) 255；集群本地身份的最大数量会从 65535 降至 32767

   集群 ID 会占用数值身份中的位。所有集群中的该值都必须完全相同，而且只能在安装时设置，因为在运行中的集群中修改它可能会中断连接并错误执行策略。

   </details>

4. **1.20 与 1.21 预发布版中，`clustermesh.apiserver.tls.authMode` 的默认值分别是什么？**
   - A) 1.20 为 `legacy`，1.21 为 `migration`
   - B) 1.20 为 `cluster`，1.21 为 `cluster-strict`
   - C) 1.20 为 `migration`，1.21 为 `cluster`（并新增 `cluster-strict` 选项）
   - D) 两者均为 `migration`

   <details>
   <summary>显示答案</summary>

   **答案**：C) 1.20 为 `migration`，1.21 为 `cluster`（并新增 `cluster-strict` 选项）

   在 `cluster` 模式下，每个集群会以 `remote-<cluster-name>` 身份进行身份验证，并且需要共享 CA。若使用用户提供的证书且 `tls.auto.enabled=false`，应使用新的 CN 重新签发远程证书，或将 `authMode` 改回 `migration`。

   </details>

5. **在 Cilium 1.19 及之后版本的 Cluster Mesh 中，没有集群标签的策略选择器会匹配哪些端点？**
   - A) 所有已连接集群的端点
   - B) 不匹配任何对象，策略会被拒绝
   - C) 仅远程集群的全局命名空间中的端点
   - D) 仅本地集群的端点

   <details>
   <summary>显示答案</summary>

   **答案**：D) 仅本地集群的端点

   `policy-default-local-cluster`（Helm 设置 `clustermesh.policyDefaultLocalCluster`）在 1.19 中默认启用。通过标签 `io.cilium.k8s.policy.cluster` 选择远程集群，或使用 `Exists` 表达式匹配任何集群。1.18 及之前版本默认会匹配所有集群。

   </details>

6. **`clustermesh-apiserver` 容器中的哪个组件会让 Agent 从本地缓存读取远程集群状态？**
   - A) `kvstoremesh`，它会将远程状态拉取到本地 etcd
   - B) `apiserver`，它会镜像远程集群
   - C) `etcd`，它会直接从远程 etcd 实例拉取数据
   - D) cilium-agent，每个远程 etcd 都会保持一个连接

   <details>
   <summary>显示答案</summary>

   **答案**：A) `kvstoremesh`，它会将远程状态拉取到本地 etcd

   `apiserver` 容器只会将本地集群的状态同步到本地 etcd。KVStoreMesh 自 1.16 起默认启用，并且在 1.21 预发布版中无条件启用。

   </details>

7. **Cilium 1.20 要求使用哪个版本的 Gateway API CRD？TLSRoute 有什么陷阱？**
   - A) v1.6.1；Helm Chart 会安装 CRD 并自动替换 TLSRoute
   - B) v1.4；完全不支持 TLSRoute
   - C) v1.6.1；安装 standard channel TLSRoute v1.6 后，现有 `v1alpha2` TLSRoute 对象会变得不可读，因此若已在使用它们，应选择 experimental v1.6.1 TLSRoute
   - D) v1.3.0；TLSRoute 需要 `bpf.tproxy` 标志

   <details>
   <summary>显示答案</summary>

   **答案**：C) v1.6.1；安装 standard channel TLSRoute v1.6 后，现有 `v1alpha2` TLSRoute 对象会变得不可读，因此若已在使用它们，应选择 experimental v1.6.1 TLSRoute

   Chart 不会安装 Gateway API CRD。切换 channel 前应备份 TLSRoute 对象，并使用 `kubectl apply --server-side` 应用 CRD。

   </details>

8. **Cilium 能否作为 EKS Auto Mode 的 CNI？**
   - A) 可以，配置 `cni.chainingMode=aws-cni` 即可
   - B) 不可以，AWS 表示 Auto Mode 不支持替代 CNI 或网络策略插件
   - C) 可以，但仅限 Overlay 模式
   - D) 可以，将 `aws-node` 修补为无法匹配节点的 node selector 即可

   <details>
   <summary>显示答案</summary>

   **答案**：B) 不可以，AWS 表示 Auto Mode 不支持替代 CNI 或网络策略插件

   应改用受管或自管节点组。`aws-node` 修补和 ENI 模式适用于标准节点组，不适用于 Auto Mode。

   </details>

9. **`cilium_drift_checker_config_delta > 0` 表示什么？**
   - A) Agent 无法访问 Kubernetes API Server
   - B) CiliumNodeConfig 验证失败
   - C) `cilium-config` ConfigMap 中存在运行中的 Agent 尚未应用的键，因此需要重启 Agent
   - D) Operator 与 Agent 运行了不同版本的镜像

   <details>
   <summary>显示答案</summary>

   **答案**：C) `cilium-config` ConfigMap 中存在运行中的 Agent 尚未应用的键，因此需要重启 Agent

   Drift checker 会比较被监视的 ConfigMap 和 Agent 启动时采用的设置。`cilium config set --restart=false` 是一种创建待应用变更的方式，之后该指标会报告此变更。

   </details>

10. **从 KVStore 迁移到 CRD 的 Double Write 过程中，`identity-allocation-mode` 取值顺序是什么？**
    - A) 先 `crd`，再 `doublewrite-readcrd`，最后 `kvstore`
    - B) 先 `doublewrite-readcrd`，再 `doublewrite-readkvstore`，最后 `crd`
    - C) 先 `kvstore`，再 `crd`；`doublewrite-readkvstore` 仅用于回滚
    - D) 先 `kvstore`，再 `doublewrite-readkvstore`，然后 `doublewrite-readcrd`，最后 `crd`

    <details>
    <summary>显示答案</summary>

    **答案**：D) 先 `kvstore`，再 `doublewrite-readkvstore`，然后 `doublewrite-readcrd`，最后 `crd`

    两个 Double Write 步骤都应先重新部署 Operator，再部署 Agent；最后的 `crd` 步骤则应先部署 Agent，再部署 Operator。此功能仍为 Beta；1.21 预发布版中已弃用一次性使用的 `migrate-identity` 工具。

    </details>
