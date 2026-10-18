# MWAA 集成测验

检查已预置的 MWAA 3.3.1/Python 3.12 的管理边界和 EKS 连通性。

1. 客户的 EKS 集群中的 kubectl 能检查 MWAA 调度器吗？

<details>
<summary>显示答案</summary>

**答案**：不能。MWAA 使用 AWS 管理的 Fargate 基础设施，并连接到客户 VPC 中的私有子网。

**说明**：这并不意味着 MWAA 与 VPC 无关。用户仍需管理 DAG、IAM、网络、容量选项和升级。

</details>

2. MWAA 向 EKS 提交 Pod 时必须检查哪三个边界？

<details>
<summary>显示答案</summary>

**答案**：网络可达性、基于 IAM 的 EKS 身份验证，以及 Kubernetes RBAC。

**说明**：kubeconfig 和 in_cluster=False 本身并不能提供端点连通性或命名空间权限。

</details>

3. 在 EKS API 身份验证模式下，添加 aws-auth 映射能授予访问权限吗？

<details>
<summary>显示答案</summary>

**答案**：不能。在此模式下应使用访问条目。

**说明**：访问条目在 API_AND_CONFIG_MAP 模式下也有效。应将组名与实际的 RoleBinding 匹配，并检查其他授权。

</details>

4. MWAA 是否禁止安装 Linux 运行时或系统依赖项？

<details>
<summary>显示答案</summary>

**答案**：可以通过启动脚本安装受支持的运行时。

**说明**：官方示例包含 sudo。需要验证启动时间、网络和版本限制；这不等同于可以任意替换受管基础镜像。

</details>

5. Git → CI → S3 → MWAA 是否能保证合并后立即执行？

<details>
<summary>显示答案</summary>

**答案**：不能。文件同步和 DAG 解析都需要完成。

**说明**：文档中介绍的 S3 基线本身不能证明所有 Airflow bundle 功能都不可用。若要单独配置，应检查所选版本是否支持。

</details>

6. 在 2026-09-12 审查的支持表中，最新的 Airflow 版本和 MWAA 可用日期是什么？

<details>
<summary>显示答案</summary>

**答案**：Airflow 3.3.1，自 2026-09-01 起可用，并使用 Python 3.12。

**说明**：上游 3.3.1 于 2026-08-12 发布，因此固定等待三个月的说法不正确。应另行检查现有环境的版本。

</details>

7. MWAA 是否只适用于仅依赖 PyPI 或不太重要的流水线？

<details>
<summary>显示答案</summary>

**答案**：不是。它可以运行外部 EKS 工作负载镜像；应根据运维、功能和恢复要求做决定。

**说明**：KPO 子 Pod 的镜像与 MWAA 自身的运行时不同。还应区分预置的 MWAA 与基于 YAML 的 MWAA Serverless。

</details>

8. 成本比较时是否应直接采用自托管节省 30–60% 的固定比例？

<details>
<summary>显示答案</summary>

**答案**：如果没有证据和等效条件，就不应采用。

**说明**：应比较相同的吞吐量/延迟目标，并计入 worker 范围、EKS、数据库、存储、NAT、日志和工程投入。

</details>

9. 本章的 3.3.1/Python 3.12 环境如何固定 Kubernetes provider 版本？

<details>
<summary>显示答案</summary>

**答案**：使用匹配的 Airflow/Python constraints，并指定 apache-airflow-providers-cncf-kubernetes==10.21.0。

**说明**：先检查基础镜像。上传到 S3 后，验证环境使用的 requirements 对象版本和安装日志。

</details>

10. 将本地生成的 kubeconfig 提供给 MWAA 前必须检查什么？

<details>
<summary>显示答案</summary>

**答案**：检查集群、context、CA、exec.command 和 IAM 凭证选择，并移除本地 AWS_PROFILE 引用。

**说明**：不要嵌入静态令牌或长期密钥。应验证 aws get-token 能运行，并从 MWAA 访问目标端点。

</details>

11. 哪种绑定可将 Kubernetes 组仅关联到 data-processing 命名空间中的 Role？

<details>
<summary>显示答案</summary>

**答案**：在该命名空间中使用 RoleBinding。

**说明**：ClusterRoleBinding 不能表达命名空间边界。其他授权会叠加生效；创建 Pod 时还要考虑服务账户选择问题。

</details>

12. 如果始终看不到 MWAA_EKS_OK，且子 Pod 处于 ImagePullBackOff，是否应先扩大 MWAA 角色的 S3 权限？

<details>
<summary>显示答案</summary>

**答案**：不应。先检查 EKS 节点/Fargate 的镜像拉取身份、镜像仓库连通性和镜像是否存在。

**说明**：子 Pod 不会自动继承 MWAA 执行角色。应单独配置实际工作负载所需的数据权限。

</details>

---

[返回学习资料](../../../data-on-eks/airflow/04-mwaa-integration.md)
