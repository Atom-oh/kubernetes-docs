# ArgoCD 流量管理测验

本测验旨在测试你对使用 ArgoCD 和 Argo Rollouts 进行渐进式交付和流量管理的理解。

1. Argo Rollouts 是什么？
   - A) ArgoCD 的日志解决方案
   - B) 用于渐进式交付策略的 Kubernetes controller
   - C) Git 分支管理工具
   - D) 流量监控仪表板

<details>
<summary>显示答案</summary>

**答案：B) 用于渐进式交付策略的 Kubernetes controller**

**说明：**
Argo Rollouts 是一个 Kubernetes controller，提供高级 Deployment 功能，例如 canary 部署、blue-green 部署，以及带有自动化分析的渐进式交付。

</details>

2. 哪种部署策略会逐步将流量从旧版本转移到新版本？
   - A) Recreate
   - B) Rolling Update
   - C) Canary
   - D) Blue-Green

<details>
<summary>显示答案</summary>

**答案：C) Canary**

**说明：**
Canary 部署会以递增的比例（例如 10%、25%、50%、100%）逐步将流量从旧版本转移到新版本，从而可以在每个步骤进行测试和验证。

</details>

3. 在使用 Argo Rollouts 的 Blue-Green 部署中，promotion 期间会发生什么？
   - A) blue 环境被删除
   - B) 流量从 stable (blue) Service 切换到 preview (green) Service
   - C) 两个版本永远同时运行
   - D) 创建一个新环境

<details>
<summary>显示答案</summary>

**答案：B) 流量从 stable (blue) Service 切换到 preview (green) Service**

**说明：**
在 Blue-Green 部署中，promotion 通过更新活动 Service selector，将流量从当前 stable 版本切换到 preview 版本。旧 ReplicaSet 会在 promotion 后缩容。

</details>

4. Argo Rollouts 中的 AnalysisTemplate 是什么？
   - A) 用于创建新应用程序的模板
   - B) 用于自动化 canary 分析的指标和成功标准的定义
   - C) 日志配置
   - D) resource quota 模板

<details>
<summary>显示答案</summary>

**答案：B) 用于自动化 canary 分析的指标和成功标准的定义**

**说明：**
AnalysisTemplates 定义要查询的指标（来自 Prometheus、Datadog 等）以及成功/失败标准。在 rollout 期间，AnalysisRuns 会执行这些模板，以自动确定 Deployment 是否应继续。

</details>

5. 哪种 Ingress controller 与 Argo Rollouts 原生集成以进行流量分割？
   - A) 仅 Traefik
   - B) 仅 NGINX Ingress
   - C) 多种，包括 NGINX、ALB、Istio 和 Traefik
   - D) 没有，必须手动配置

<details>
<summary>显示答案</summary>

**答案：C) 多种，包括 NGINX、ALB、Istio 和 Traefik**

**说明：**
Argo Rollouts 与多种 Ingress controller 和 service mesh 原生集成以进行流量管理，其中包括 NGINX Ingress、AWS ALB、Istio、Linkerd、SMI 和 Traefik。

</details>

6. Canary 策略中的 `setWeight` step 有什么作用？
   - A) 设置 Pods 的 CPU 权重
   - B) 设置要路由到 canary 版本的流量百分比
   - C) 设置 Deployment 的重要程度
   - D) 设置 rollback 阈值

<details>
<summary>显示答案</summary>

**答案：B) 设置要路由到 canary 版本的流量百分比**

**说明：**
Canary 策略中的 `setWeight` step 会配置应将多少百分比的流量路由到 canary（新）版本。例如，`setWeight: 20` 会将 20% 的流量路由到 canary。

</details>

7. Canary 部署期间 AnalysisRun 失败时会发生什么？
   - A) Deployment 无论如何都会继续
   - B) 会发送警报，但不会发生其他事情
   - C) rollout 会自动中止并回滚
   - D) cluster 会关闭

<details>
<summary>显示答案</summary>

**答案：C) rollout 会自动中止并回滚**

**说明：**
当 AnalysisRun 失败时（指标超过失败阈值），Argo Rollouts 会自动中止 rollout，并启动到 stable 版本的回滚，从而防止不良 Deployment 影响所有流量。

</details>

8. 如何在特定 step 暂停 Rollout 以进行手动验证？
   - A) 使用不带持续时间的 `pause` step
   - B) 使用 `stop` step
   - C) 使用带有 duration: forever 的 `wait` step
   - D) 无法实现

<details>
<summary>显示答案</summary>

**答案：A) 使用不带持续时间的 `pause` step**

**说明：**
添加不带持续时间的 `pause` step 会创建无限期暂停，需要通过 CLI 或 UI 进行手动 promotion 才能继续。这对于 Deployment 过程中的手动验证关卡非常有用。

</details>

9. 如何通过 Kong Ingress Controller 分割 canary 流量？
   - A) 直接使用 `trafficRouting.kong` 字段
   - B) 通过 Gateway API plugin (`trafficRouting.plugins`) 操作 HTTPRoute
   - C) Kong 无法与 Argo Rollouts 集成
   - D) 使用 Istio VirtualService 绕过它进行路由

<details>
<summary>显示答案</summary>

**答案：B) 通过 Gateway API plugin (`trafficRouting.plugins`) 操作 HTTPRoute**

**说明：**
Kong 没有原生 Argo Rollouts 集成——不存在 `trafficRouting.kong` 字段。它仅通过 argoproj-labs 的 Gateway API plugin 获得支持，该 plugin 会操作标准 HTTPRoute resource。其他符合 Gateway API 的 controller，例如 Traefik 和 kgateway，也使用同一个 plugin。

</details>

10. Argo Rollouts Gateway API plugin 在每个 canary weight step 实际更新哪个 resource？
    - A) Service 的 `selector` labels
    - B) Ingress 的 `canary-weight` annotation
    - C) HTTPRoute 的 `backendRefs[].weight`
    - D) DestinationRule 的 subset labels

<details>
<summary>显示答案</summary>

**答案：C) HTTPRoute 的 `backendRefs[].weight`**

**说明：**
Gateway API plugin 会在每个 setWeight step 直接更新标准 Gateway API HTTPRoute resource 的 `backendRefs[].weight` 值。这是一种通用机制，对任何实现 Gateway API 的 controller 都同样适用——Kong、Traefik、kgateway 等均是如此。

</details>
