# Kubeflow Notebooks 测验

基线版本：Notebooks 1.11.0 / Community Distribution 26.03.1。

## 选择题

1. Notebook controller 会协调（reconcile）哪些内容？

   - A) 用户笔记本电脑上的浏览器进程
   - B) 根据 Notebook CR 生成的 StatefulSet、Service 以及已配置的路由资源
   - C) 为每个用户创建一个 EC2 实例
   - D) 仅一个 HTML 仪表板

<details>
<summary>显示答案</summary>

**答案：B) 根据 Notebook CR 生成的 StatefulSet、Service 以及已配置的路由资源**

StatefulSet controller 负责创建 Pod，由 Kubernetes 完成调度。仪表板只是一个 UI 入口。
</details>

2. 这里确切的版本基线是什么？

   - A) 所有组件的 Workspaces 均已 GA
   - B) Notebooks v1.11.0；26.03.1 将 Workspaces 称为 beta，而其镜像为 v2.0.0-alpha.3
   - C) Notebook 与 Workspace 是完全相同的 API
   - D) 本章中 v1 已有确定的停止支持日期

<details>
<summary>显示答案</summary>

**答案：B) Notebooks v1.11.0；26.03.1 将 Workspaces 称为 beta，而其镜像为 v2.0.0-alpha.3**

发布说明与镜像标签并不一致。请核实实际的 API/迁移支持情况，而不要据此推断已经 GA 或 v1 的淘汰日期。
</details>

3. Profile 是否会自动将每个 notebook 与其他所有用户隔离？

   - A) 是，包括 AWS 和存储
   - B) 不会；Profile 可以共享，网络、存储、IAM 和应用授权仍然是彼此独立的
   - C) 是，因为 namespace（命名空间）会阻断网络数据包
   - D) 是，因为 RBAC 会取消所有无关的授权

<details>
<summary>显示答案</summary>

**答案：B) 不会；Profile 可以共享，网络、存储、IAM 和应用授权仍然是彼此独立的**

完整的 UI 会选择一个 Profile namespace。而 Notebook CRD 本身并不要求每个 namespace 中都存在 Profile 对象。
</details>

4. 当 notebook Pod 被替换后，哪些内容会保留下来？

   - A) 所有进程内存
   - B) 在容器中任何位置安装的所有软件包
   - C) 保留下来的持久卷上的数据；容器层中的软件包和内核内存不会保留
   - D) 所有挂接的 EC2 实例

<details>
<summary>显示答案</summary>

**答案：C) 保留下来的持久卷上的数据；容器层中的软件包和内核内存不会保留**

请检查挂载位置、PVC/卷的生命周期以及备份。ReadWriteOnce 是单节点访问模式，并不保证只有单个 Pod 可以使用。
</details>

5. 经过实际检查的 idle-culling 默认配置是什么？

   - A) 已启用，空闲阈值为 1 分钟
   - B) 已禁用；空闲阈值 1440 分钟，检查周期 1 分钟
   - C) 对所有 RStudio 和 shell 进程启用
   - D) 仅对 GPU notebook 禁用

<details>
<summary>显示答案</summary>

**答案：B) 已禁用；空闲阈值 1440 分钟，检查周期 1 分钟**

culler 依据 Jupyter kernel 的活动情况进行判断。API 调用失败或返回空结果时，旧的活动时间保持不变，仍可能导致 notebook 被停止。请针对实际使用的镜像和访问路径进行测试。
</details>

6. v1.11.0 如何表示一个已停止的 Notebook？

   - A) spec.replicas: 0
   - B) 通过是否存在 kubeflow-resource-stopped；controller 会把 StatefulSet 的副本数设为零
   - C) 注解值为 false 表示正在运行
   - D) 删除它的 PVC

<details>
<summary>显示答案</summary>

**答案：B) 通过是否存在 kubeflow-resource-stopped；controller 会把 StatefulSet 的副本数设为零**

NotebookSpec 没有 replicas 字段。移除该注解即可恢复运行。即使值为字符串 false，也仍然算作该注解存在。
</details>

7. 使用自定义镜像 digest 能够保证什么？

   - A) 所有用户拥有完全一致的完整运行时环境
   - B) 所引用的镜像内容一致；但挂载的数据和运行时的变更仍可能不同
   - C) 自动兼容所有 GPU 驱动
   - D) UI 的镜像限制无法通过 API 绕过

<details>
<summary>显示答案</summary>

**答案：B) 所引用的镜像内容一致；但挂载的数据和运行时的变更仍可能不同**

请使用经过测试的 server-prefix/端口/UID 行为、依赖项和架构。仅使用可变标签并不能固定镜像内容。
</details>

## 简答题

8. 为什么停止一个空闲的 GPU notebook 并不能保证立即降低成本？

<details>
<summary>显示答案</summary>

Pod 的资源请求可以被释放，但其他工作负载、PDB、NodePool 的限制/中断策略以及容量管理都会影响节点是否被终止。只要节点仍在运行，EC2 费用就会继续产生。
</details>

9. 对于 notebook 而言，RBAC、Istio 授权和 NetworkPolicy 有何区别？

<details>
<summary>显示答案</summary>

RBAC 管控 Kubernetes API 操作。Istio 授权控制由已配置的代理和策略处理的请求。NetworkPolicy 在 CNI 实施的前提下管控允许的 Pod 网络流量。它们中任何一项单独使用都无法保证存储/IAM/应用层面的隔离。
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/03-notebooks.md)
