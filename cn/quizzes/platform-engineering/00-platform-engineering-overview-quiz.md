# Platform Engineering（平台工程）概述测验

> 本测验用于测试你对 [Platform Engineering Overview](../../platform-engineering/00-platform-engineering-overview.md) 文档的理解。

---

1. Platform Engineering 的核心目标是什么？
   - A) 培训所有开发者直接管理基础设施
   - B) 构建 Internal Developer Platform（IDP），为开发者提供自助服务
   - C) 用自动化完全取代运营团队的角色
   - D) 将所有应用迁移到 serverless

<details>
<summary>显示答案</summary>

**答案：B) 构建 Internal Developer Platform（IDP），为开发者提供自助服务**

**解释：**
Platform Engineering 是构建 IDP 的实践，使开发者无需直接处理基础设施复杂性，就能快速、安全地部署应用。其目标不是教开发者进行基础设施管理，而是提供抽象化的自助服务接口。

</details>

---

2. 在 AWS CAF 成熟度模型中，哪个阶段对应“通过 IaC 实现基础设施自动化”和“自助式产品交付”？
   - A) START
   - B) ADVANCE
   - C) EXCEL
   - D) 所有阶段通用

<details>
<summary>显示答案</summary>

**答案：B) ADVANCE**

**解释：**
在 AWS CAF 成熟度模型中，ADVANCE 阶段侧重于扩展自动化并构建集中式可观测性。基础设施自动化（IaC、自助式产品）是在 START 基础之上构建的 ADVANCE 能力。START 涵盖基础能力建设，而 EXCEL 涵盖持续优化。

</details>

---

3. 哪个陈述正确描述了 Platform Engineering、DevOps 和 SRE 之间的关系？
   - A) 三者是相互排斥的方法
   - B) Platform Engineering 取代 DevOps 和 SRE
   - C) Platform Engineering 将 DevOps 原则和 SRE 实践打包为一个产品
   - D) SRE 是包含 Platform Engineering 和 DevOps 的超集

<details>
<summary>显示答案</summary>

**答案：C) Platform Engineering 将 DevOps 原则和 SRE 实践打包为一个产品**

**解释：**
这三种方法是互补的。DevOps 提供文化和方法论，SRE 提供运营工程实践，而 Platform Engineering 将这些内容打包成名为 Internal Developer Platform 的产品。

</details>

---

4. 在基于 Kubernetes 的 IDP 参考架构中，ArgoCD、FluxCD 和 KRO 属于哪一层？
   - A) Developer Interface Layer
   - B) Integration/Orchestration Layer
   - C) Resource Layer
   - D) Infrastructure Layer

<details>
<summary>显示答案</summary>

**答案：B) Integration/Orchestration Layer**

**解释：**
Integration/Orchestration Layer 负责声明式状态管理和部署自动化。ArgoCD 和 FluxCD 提供基于 GitOps 的部署，KRO 提供资源图编排。Developer Interface Layer 用于 Backstage 等 UI/CLI，Resource Layer 用于 ACK/Helm/Operators，Infrastructure Layer 用于 EKS/VPC/IAM。

</details>

---

5. 关于 Golden Paths，哪个说法不正确？
   - A) 它们是平台团队提供的推荐部署路径
   - B) 它们是开发者必须遵循的强制规则
   - C) 它们指导开发者使用经过验证的方法快速上手
   - D) 开发者可以在需要时偏离它们，但在大多数情况下它们是最佳选择

<details>
<summary>显示答案</summary>

**答案：B) 它们是开发者必须遵循的强制规则**

**解释：**
Golden Paths 是“推荐的”，而不是“强制执行的”。它们提供平台团队已经验证和优化的部署方法，但开发者可以在需要时选择不同的方法。目标是设计 Golden Paths，使其成为大多数使用场景下的最佳选择。

</details>

---

6. 在结合 KRO 的 ResourceGraphDefinition（RGD）和 ACK 的自助服务模式中，当开发者提交单个 manifest 时，会自动创建哪组资源？
   - A) Deployment + ConfigMap + PVC
   - B) Deployment + Service + RDS Instance + IAM Role
   - C) StatefulSet + Service + DynamoDB Table
   - D) Pod + Ingress + S3 Bucket

<details>
<summary>显示答案</summary>

**答案：B) Deployment + Service + RDS Instance + IAM Role**

**解释：**
在 KRO RGD + ACK 自助服务模式中，开发者的单个 WebApplication manifest 会触发 KRO 自动创建 Kubernetes 原生资源（Deployment + Service）以及通过 ACK 创建 AWS 资源（RDS Instance、IAM Role）。这是 IDP 的核心价值：抽象化基础设施复杂性。

</details>

---

7. 在 AWS CAF 成熟度模型中，DORA metrics 属于哪个阶段和能力领域？
   - A) START - Cost Management
   - B) ADVANCE - Central Observability
   - C) EXCEL - Platform Metrics
   - D) 所有阶段通用

<details>
<summary>显示答案</summary>

**答案：C) EXCEL - Platform Metrics**

**解释：**
DORA metrics（Deployment Frequency、Lead Time、MTTR、Change Failure Rate）属于 EXCEL 阶段中的“Platform Metrics”能力。这代表最高成熟度级别，即通过与组织目标一致的指标实现持续优化。

</details>

---

8. 在 IDP 的核心价值中，哪一项默认嵌入安全性和合规性，使开发者无需显式安全配置即可在安全环境中工作？
   - A) Self-Service
   - B) Guardrails
   - C) Standardization
   - D) Automation

<details>
<summary>显示答案</summary>

**答案：B) Guardrails**

**解释：**
Guardrails 默认将安全性和合规性嵌入平台。即使开发者没有显式配置安全设置，平台也会自动应用安全策略（Pod Security Standards、network policies、image scanning 等）。Self-Service 与直接预置相关，Standardization 与 Golden Paths 相关，Automation 与消除重复性任务相关。

</details>
