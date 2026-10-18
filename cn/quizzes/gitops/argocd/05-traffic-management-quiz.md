# ArgoCD 流量管理测验

本测验旨在检验你对使用 ArgoCD 和 Argo Rollouts 进行渐进式交付和流量管理的理解。

1. 什么是 Argo Rollouts？
   - A) ArgoCD 的日志解决方案
   - B) 用于渐进式交付策略的 Kubernetes 控制器
   - C) Git 分支管理工具
   - D) 流量监控仪表板

<details>
<summary>显示答案</summary>

**答案：B) 用于渐进式交付策略的 Kubernetes 控制器**

**说明：**
Argo Rollouts 是一个 Kubernetes 控制器，提供高级部署功能，例如金丝雀部署、蓝绿部署，以及通过自动化分析实现渐进式交付。

</details>

2. 哪种策略通过明确的流量权重步骤和分析关卡来验证新版本？
   - A) 重建
   - B) 滚动更新
   - C) 金丝雀
   - D) 蓝绿

<details>
<summary>显示答案</summary>

**答案：C) 金丝雀**

**说明：**
金丝雀部署会分阶段逐步将流量从旧版本转移到新版本（例如 10%、25%、50%、100%），从而可以在每个步骤进行测试和验证。

</details>

3. 在使用 Argo Rollouts 进行蓝绿部署时，提升期间会发生什么？
   - A) 蓝色环境会被删除
   - B) 活跃 Service 的 selector 会切换到新的 ReplicaSet
   - C) 两个版本会永远同时运行
   - D) 会创建一个新环境

<details>
<summary>显示答案</summary>

**答案：B) 活跃 Service 的 selector 会切换到新的 ReplicaSet**

**说明：**
在蓝绿部署中，通过更新活跃 Service 的 selector，将流量从当前稳定版本切换到预览版本，从而完成提升。旧 ReplicaSet 会根据分析和延迟设置缩容；数据面传播并非瞬时完成。

</details>

4. Argo Rollouts 中的 AnalysisTemplate 是什么？
   - A) 用于创建新应用程序的模板
   - B) 对自动化金丝雀分析所用指标和成功标准的定义
   - C) 日志配置
   - D) 资源配额模板

<details>
<summary>显示答案</summary>

**答案：B) 对自动化金丝雀分析所用指标和成功标准的定义**

**说明：**
AnalysisTemplate 定义要查询的指标（来自 Prometheus、Datadog 等）以及成功/失败标准。在 Rollout 期间，AnalysisRun 会执行这些模板，以自动判断部署是否应继续。

</details>

5. Argo Rollouts 原生集成了哪些流量管理提供程序？
   - A) 仅 Traefik
   - B) 仅 NGINX Ingress
   - C) 多种，包括 NGINX、ALB、Istio 和 Traefik
   - D) 都不支持，需要手动配置

<details>
<summary>显示答案</summary>

**答案：C) 多种，包括 NGINX、ALB、Istio 和 Traefik**

**说明：**
Argo Rollouts 原生集成了多种 Ingress 控制器和服务网格以实现流量管理，包括 AWS ALB、Istio、Traefik 和 APISIX。保留 ingress-nginx/SMI API 支持，并不意味着这些项目仍在维护；也没有单独的原生 Linkerd 字段。

</details>

6. 使用流量路由器且默认 maxTrafficWeight=100 时，setWeight 配置什么？
   - A) 设置 Pod 的 CPU 权重
   - B) 设置路由到金丝雀版本的流量百分比
   - C) 设置部署的重要性
   - D) 设置回滚阈值

<details>
<summary>显示答案</summary>

**答案：B) 设置路由到金丝雀版本的流量百分比**

**说明：**
金丝雀策略中的 `setWeight` 步骤用于配置应路由到金丝雀（新）版本的流量百分比。例如，setWeight:20 表示请求的相对权重为 20/100。观察到的百分比会因样本、连接和 Cookie 而异。没有流量路由器时，系统会使用 Pod 数量近似实现该比例。

</details>

7. 与 Rollout 关联的分析达到 AnalysisRun 阶段 Failed 时，会发生什么？
   - A) 无论如何都会继续部署
   - B) 会发送警报，但不会发生其他情况
   - C) Rollout 会中止，流量会返回稳定版本
   - D) 集群会关闭

<details>
<summary>显示答案</summary>

**答案：C) Rollout 会中止，流量会返回稳定版本**

**说明：**
当 AnalysisRun 失败（指标超出失败阈值）时，Argo Rollouts 会中止 Rollout，并将流量切回稳定版本。它不会还原 Git 或数据库变更。failureLimit 用于区分测量失败与 AnalysisRun 失败；Inconclusive 会暂停流程，以便进行调查。

</details>

8. 如何在特定步骤暂停 Rollout，以便手动验证？
   - A) 使用不带持续时间的 `pause` 步骤
   - B) 使用 `stop` 步骤
   - C) 使用 duration: forever 的 `wait` 步骤
   - D) 无法实现

<details>
<summary>显示答案</summary>

**答案：A) 使用不带持续时间的 `pause` 步骤**

**说明：**
添加不带持续时间的 `pause` 步骤会创建无限期暂停，必须手动提升（通过 CLI 或 UI）才能继续。这适用于部署流程中的手动验证关卡。

</details>

9. 如何通过 Kong Ingress Controller 拆分金丝雀流量？
   - A) 直接使用 `trafficRouting.kong` 字段
   - B) 通过 Gateway API 插件（`trafficRouting.plugins`）操作 HTTPRoute
   - C) Kong 无法与 Argo Rollouts 集成
   - D) 使用 Istio VirtualService 绕过它进行路由

<details>
<summary>显示答案</summary>

**答案：B) 通过 Gateway API 插件（`trafficRouting.plugins`）操作 HTTPRoute**

**说明：**
Kong 没有原生的 Argo Rollouts 集成；不存在 `trafficRouting.kong` 字段。本章使用 argoproj-labs 的 Gateway API 插件，该插件会操作标准的 HTTPRoute 资源。其他符合 Gateway API 规范的控制器，例如 Traefik 和 kgateway，也使用同一插件。

</details>

10. 在每个金丝雀权重步骤，Argo Rollouts Gateway API 插件实际会更新哪个资源？
    - A) Service 的 `selector` 标签
    - B) Ingress 的 `canary-weight` 注释
    - C) HTTPRoute 的 `backendRefs[].weight`
    - D) DestinationRule 的子集标签

<details>
<summary>显示答案</summary>

**答案：C) HTTPRoute 的 `backendRefs[].weight`**

**说明：**
Gateway API 插件会在每个 setWeight 步骤中，直接更新标准 Gateway API HTTPRoute 资源的 `backendRefs[].weight` 值。此机制可与兼容的控制器配合使用；请验证已安装的 CRD、支持的 Route 功能以及数据面是否实际收敛。

</details>
