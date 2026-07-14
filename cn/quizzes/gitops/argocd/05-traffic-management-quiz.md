# ArgoCD 流量管理测验

本测验检验你对使用 ArgoCD 和 Argo Rollouts 进行渐进式交付和流量管理的理解。

1. 什么是 Argo Rollouts？
   - A) ArgoCD 的日志解决方案
   - B) 用于渐进式交付策略的 Kubernetes controller
   - C) Git 分支管理工具
   - D) 流量监控仪表板

<details>
<summary>显示答案</summary>

**答案：B) 用于渐进式交付策略的 Kubernetes controller**

**说明：**
Argo Rollouts 是一个 Kubernetes controller，提供高级 Deployment 功能，例如 Canary Deployment、Blue-Green Deployment，以及带有自动化分析的渐进式交付。

</details>

2. 哪种 Deployment 策略会将流量从旧版本逐步切换到新版本？
   - A) Recreate
   - B) Rolling Update
   - C) Canary
   - D) Blue-Green

<details>
<summary>显示答案</summary>

**答案：C) Canary**

**说明：**
Canary Deployment 会逐步将流量从旧版本切换到新版本（例如 10%、25%、50%、100%），从而可以在每个步骤进行测试和验证。

</details>

3. 在使用 Argo Rollouts 的 Blue-Green Deployment 中，Promotion 期间会发生什么？
   - A) 删除蓝色环境
   - B) 流量从稳定（蓝色）Service 切换到预览（绿色）Service
   - C) 两个版本会永久同时运行
   - D) 创建一个新环境

<details>
<summary>显示答案</summary>

**答案：B) 流量从稳定（蓝色）Service 切换到预览（绿色）Service**

**说明：**
在 Blue-Green Deployment 中，Promotion 会通过更新活跃 Service selector，将流量从当前稳定版本切换到预览版本。Promotion 后会缩减旧 ReplicaSet 的规模。

</details>

4. Argo Rollouts 中的 AnalysisTemplate 是什么？
   - A) 用于创建新应用程序的模板
   - B) 用于自动化 Canary 分析的指标和成功条件定义
   - C) 日志配置
   - D) 资源配额模板

<details>
<summary>显示答案</summary>

**答案：B) 用于自动化 Canary 分析的指标和成功条件定义**

**说明：**
AnalysisTemplate 定义要查询的指标（来自 Prometheus、Datadog 等）以及成功/失败条件。在 Rollout 期间，AnalysisRun 会执行这些模板，以自动确定 Deployment 是否应继续进行。

</details>

5. 哪个 Ingress controller 原生集成了 Argo Rollouts 以进行流量拆分？
   - A) 仅 Traefik
   - B) 仅 NGINX Ingress
   - C) 包括 NGINX、ALB、Istio 和 Traefik 在内的多个 controller
   - D) 没有，需要手动配置

<details>
<summary>显示答案</summary>

**答案：C) 包括 NGINX、ALB、Istio 和 Traefik 在内的多个 controller**

**说明：**
Argo Rollouts 原生集成了多个 Ingress controller 和 Service mesh 的流量管理功能，包括 NGINX Ingress、AWS ALB、Istio、Linkerd、SMI 和 Traefik。

</details>

6. Canary 策略中的 `setWeight` 步骤有什么作用？
   - A) 设置 Pod 的 CPU 权重
   - B) 设置路由到 Canary 版本的流量百分比
   - C) 设置 Deployment 的重要性
   - D) 设置回滚阈值

<details>
<summary>显示答案</summary>

**答案：B) 设置路由到 Canary 版本的流量百分比**

**说明：**
Canary 策略中的 `setWeight` 步骤用于配置应有多少百分比的流量路由到 Canary（新）版本。例如，`setWeight: 20` 会将 20% 的流量路由到 Canary。

</details>

7. Canary Deployment 期间 AnalysisRun 失败时会发生什么？
   - A) Deployment 无论如何都会继续
   - B) 会发送警报，但不会发生其他事情
   - C) Rollout 会自动中止并回滚
   - D) cluster 会关闭

<details>
<summary>显示答案</summary>

**答案：C) Rollout 会自动中止并回滚**

**说明：**
当 AnalysisRun 失败时（指标超过失败阈值），Argo Rollouts 会自动中止 Rollout 并启动到稳定版本的回滚，从而防止不良 Deployment 影响所有流量。

</details>

8. 如何在特定步骤暂停 Rollout 以进行手动验证？
   - A) 使用不带 duration 的 `pause` 步骤
   - B) 使用 `stop` 步骤
   - C) 使用带有 duration: forever 的 `wait` 步骤
   - D) 无法实现

<details>
<summary>显示答案</summary>

**答案：A) 使用不带 duration 的 `pause` 步骤**

**说明：**
添加不带 duration 的 `pause` 步骤会创建无限期暂停，需要手动 Promotion（通过 CLI 或 UI）才能继续。这对于 Deployment 过程中的手动验证关卡非常有用。

</details>
