# Harbor 测验
> **最后更新**：2026 年 9 月 11 日

1. Harbor 在云原生计算基金会（CNCF）中的状态是什么？
   - A) Sandbox 项目
   - B) Incubating 项目
   - C) Graduated 项目
   - D) 已归档项目

<details>
<summary>显示答案</summary>

**答案**：C) Graduated 项目

**说明**：Harbor 是 CNCF Graduated 项目，这是 CNCF 最高的成熟度级别。该状态表明 Harbor 已展现出广泛且活跃的采用、开放的治理流程，以及对社区可持续发展和安全的坚定承诺。Harbor 于 2020 年毕业。

</details>

2. Harbor 默认使用哪个组件扫描漏洞？
   - A) Clair
   - B) Trivy
   - C) Anchore
   - D) Snyk

<details>
<summary>显示答案</summary>

**答案**：B) Trivy

**说明**：从 Harbor 2.2 开始，Trivy 取代 Clair 成为默认漏洞扫描器。Trivy 是 Aqua Security 的开源扫描器，可全面检测容器镜像中的漏洞，包括操作系统软件包和应用程序依赖项。Harbor 仍支持可插拔扫描器，用户可根据需要选用其他方案。

</details>

3. 在 Kubernetes 环境中安装 Harbor，建议采用什么方式？
   - A) Docker Compose
   - B) 手动编写 YAML manifest
   - C) Helm Chart
   - D) Operator 模式

<details>
<summary>显示答案</summary>

**答案**：C) Helm Chart

**说明**：对于 Kubernetes 环境，建议使用官方 Harbor Helm Chart 安装。它会处理数据库、Redis 和存储等复杂依赖，并提供丰富的配置选项。Docker Compose 适合非 Kubernetes 部署或快速测试，但不建议用于 Kubernetes 生产部署。

</details>

4. 在 Harbor RBAC 模型中，与 Developer 相比，Project Maintainer 拥有哪些权限？
   - A) Maintainer 可以推送镜像，Developer 不可以
   - B) Maintainer 可以扫描/删除镜像；Developer 可以推送/拉取，但不能管理项目成员
   - C) Maintainer 和 Developer 的权限完全相同
   - D) Developer 比 Maintainer 拥有更多权限

<details>
<summary>显示答案</summary>

**答案**：B) Maintainer 可以扫描/删除镜像；Developer 可以推送/拉取，但不能管理项目成员

**说明**：Harbor 的项目级 RBAC 定义了多个角色：Project Admin、Maintainer、Developer 和 Guest。Maintainer 可以扫描/删除镜像以及管理标签，但不能编辑项目配置或管理成员。Developer 可以推送/拉取镜像，但不具备这些管理权限。Project Admin 拥有完整控制权，包括成员管理。

</details>

5. Harbor robot account 有什么用途？
   - A) 执行自动化管理任务
   - B) 为 CI/CD 系统提供具有限定范围凭证的非人工服务账户
   - C) 管理 Harbor 内部组件
   - D) 在不同 Harbor 实例间复制镜像

<details>
<summary>显示答案</summary>

**答案**：B) 为 CI/CD 系统提供具有限定范围凭证的非人工服务账户

**说明**：Robot account 为 CI/CD 流水线等自动化工作流提供系统间身份验证。它支持配置过期时间和项目范围的权限，例如仓库推送/拉取，并且无需使用人工用户凭证。这符合安全最佳实践，可避免共享凭证并支持凭证轮换。

</details>

6. Harbor 的推送式与拉取式复制模式有何区别？
   - A) 推送式更快；拉取式更可靠
   - B) 推送式将镜像发送到远程仓库；拉取式从远程仓库获取镜像
   - C) 推送式需要手动触发；拉取式会自动执行
   - D) 两者没有区别，只是别名不同

<details>
<summary>显示答案</summary>

**答案**：B) 推送式将镜像发送到远程仓库；拉取式从远程仓库获取镜像

**说明**：推送式复制会主动将 Harbor 中的镜像发送到远程仓库，适合向边缘位置分发镜像。拉取式复制会将远程仓库的镜像拉入 Harbor，适合镜像外部仓库或用于灾难恢复。拉取工作流支持手动和定时复制。基于事件的复制会响应本地 Harbor 制品事件；它不会订阅任意外部仓库的变更。

</details>

7. Harbor 集成哪些镜像签名与验证工具？
   - A) GPG
   - B) Cosign 和 Notation
   - C) OpenSSL
   - D) HashiCorp Vault

<details>
<summary>显示答案</summary>

**答案**：B) Cosign 和 Notation

**说明**：Harbor 会存储由 Cosign 和 Notation 生成的签名。Notary v1 已在 Harbor 2.9 中移除。仓库中存在签名的策略不能替代在准入时根据可信签名密钥或身份执行验证。

</details>

8. Harbor 的代理缓存功能有什么用途？
   - A) 缓存 DNS 查询
   - B) 作为 Docker Hub 等远程仓库的拉取缓存
   - C) 缓存 Helm Chart 依赖项
   - D) 加速 Harbor 内部操作

<details>
<summary>显示答案</summary>

**答案**：B) 作为 Docker Hub 等远程仓库的拉取缓存

**说明**：Harbor 代理缓存会为外部仓库创建缓存代理。用户经由 Harbor 拉取镜像时，镜像会被缓存在本地。之后再拉取同一镜像时，Harbor 会从缓存提供镜像，从而减少外部带宽使用、提高拉取性能并减少对上游的请求。缓存未命中、新鲜度检查和上游账户限额仍然适用。

</details>

9. 在隔离网络环境中部署 Harbor 时，哪个组件的漏洞数据库更新需要特别考虑？
   - A) Harbor core 服务
   - B) 数据库（PostgreSQL）
   - C) 漏洞扫描器（Trivy）
   - D) Redis 缓存

<details>
<summary>显示答案</summary>

**答案**：C) 漏洞扫描器（Trivy）

**说明**：在隔离网络环境中，Trivy 无法通过互联网下载漏洞数据库更新。必须在联网机器上手动下载 Trivy 数据库，将其传输到隔离环境，并配置 Trivy 使用离线数据库。否则漏洞扫描会使用过时数据或完全失败。

</details>

10. Harbor 的垃圾回收何时触发？
    - A) 每小时自动运行
    - B) 必须通过 Harbor UI/API 手动触发或设置计划任务
    - C) 每次删除镜像后运行
    - D) 存储容量达到 80% 时运行

<details>
<summary>显示答案</summary>

**答案**：B) 必须通过 Harbor UI/API 手动触发或设置计划任务

**说明**：Harbor 垃圾回收（GC）不会自动运行。必须通过 Harbor 管理 UI 或 API 手动触发，或配置为计划任务。GC 会删除不再被任何 manifest 引用的镜像层（blob）。GC 可以回收存储空间，但可能影响仓库性能，因此应安排在低活动时段执行。

</details>
