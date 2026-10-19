# 指南路线图测验

1. 在领域图中，存储和数据库领域属于哪一层？
   - A) 基础
   - B) 连接
   - C) 状态
   - D) 横切关注点
<details>
<summary>显示答案</summary>

**答案：C) 状态**

**说明：**
在领域图表中，存储（EBS gp2 与 gp3 对比，通过 fio 测量）和数据库（数据库 Operator 生态概览，以及包含 1 亿行数据的 ClickHouse 基准测试）都属于“状态”层。基础层包括 Linux 和容器；连接层包括网络和服务网格；横切关注点包括安全与策略、GitOps、平台工程、容器镜像仓库、可观测性和运维指南。

</details>

2. 路线图的学习流程图中，各层的顺序是什么？
   - A) 编排 → 基础 → 连接 → 状态 → 数据与 AI → 横切关注点
   - B) 基础 → 编排 → 连接 → 状态 → 数据与 AI → 横切关注点
   - C) 基础 → 连接 → 编排 → 数据与 AI → 状态 → 横切关注点
   - D) 横切关注点 → 基础 → 编排 → 连接 → 状态 → 数据与 AI
<details>
<summary>显示答案</summary>

**答案：B) 基础 → 编排 → 连接 → 状态 → 数据与 AI → 横切关注点**

**说明：**
学习流程图显示了指南中 15 个领域的“流程：从基础（Linux/容器）经过编排（Kubernetes/EKS）、连接（网络/服务网格）、状态（存储/数据库）、数据与 AI（数据流水线/AI-ML），再到横切关注点（安全/GitOps/平台/容器镜像仓库/可观测性/运维）”。这是一条连贯的学习路径，从 Linux 内核开始，覆盖整个云原生技术栈。

</details>

3. 以下哪个领域**不**属于路线图的已测量基准系列？
   - A) 服务网格（Istio sidecar 与 ambient 对比）
   - B) 存储（EBS gp2 与 gp3 对比）
   - C) 数据库（EKS 上的 ClickHouse）
   - D) GitOps（ArgoCD、Flux）
<details>
<summary>显示答案</summary>

**答案：D) GitOps（ArgoCD、Flux）**

**说明：**
已测量基准系列由“报告此前在 AWS 资源上运行结果的文档”组成：Istio sidecar 与 ambient 对比（按 mTLS 数据平面测量 P50/P99 延迟和发布期间的 503 率）、EBS gp2 与 gp3 基准测试（相同容量下 10 倍 IOPS 差距以及 gp2 突发积分耗尽临界点）、EKS 上的 ClickHouse 基准测试（1 亿行数据的摄取吞吐量、压缩率和查询延迟）、EKS 上的 Kafka 基准测试（例如单次运行中 RF3/RF1 的吞吐量记录），以及 Pod 网络基准测试：共五项。GitOps 属于横切领域，但系列中没有针对它的已测量页面。

</details>

4. 推荐路径 ③“数据与 AI 平台”的阅读顺序是什么？
   - A) AI/ML → 数据流水线 → 数据库 → 存储
   - B) 存储 → 数据库 → 数据流水线（Kafka → Spark → Airflow → Flink）→ AI/ML（vLLM → Ray → Kubeflow）
   - C) 数据流水线 → 存储 → AI/ML → 数据库
   - D) 数据库 → 存储 → AI/ML → 数据流水线
<details>
<summary>显示答案</summary>

**答案：B) 存储 → 数据库 → 数据流水线（Kafka → Spark → Airflow → Flink）→ AI/ML（vLLM → Ray → Kubeflow）**

**说明：**
路径 ③ 为“存储 → 数据库 → 数据流水线（Kafka → Spark → Airflow → Flink）→ AI/ML（vLLM → Ray → Kubeflow）”，并指出，如果需要 GPU 和调度控制，还应学习 Kubernetes 核心概念下的自定义调度器部分。此路径从状态层进入数据与 AI 层。

</details>

5. 在推荐路径 ①“基础设施入门”中，路线图建议如何检查自己的理解？
   - A) 完成每篇文档的测验，同时并行进行实验
   - B) 先阅读整个已测量基准系列
   - C) 导出图表分享卡
   - D) 将 llms.txt URL 提供给 LLM 并要求总结
<details>
<summary>显示答案</summary>

**答案：A) 完成每篇文档的测验，同时并行进行实验**

**说明：**
路径 ① 的阅读顺序是“Linux 基础 → 容器技术 → Kubernetes 简介 → 核心概念（Pod/Service/存储/配置）→ EKS 集群创建 → 网络基础”，并建议“用每篇文档的测验检查自己的理解，同时并行完成实验”；实验从 `labs/README.md` 开始。已测量基准系列则作为路径 ②“平台/SRE”的支撑材料。

</details>

6. 你想在 LinkedIn 上发布一张图，并让流程动画在信息流中播放。哪套操作符合路线图的 30 秒步骤？
   - A) 用屏幕录制软件录下查看器，再转换为 GIF
   - B) 确认工具栏上的 Live/Still 切换项显示 Live，然后选择 Export (`E`) → WebM，下载 6 秒的轨迹动画
   - C) 选择 Export → SVG，并将其作为视频上传到 LinkedIn
   - D) 使用 Route Probe (`R`) 解析路径，再选择 Copy diagram 复制到剪贴板
<details>
<summary>显示答案</summary>

**答案：B) 确认工具栏上的 Live/Still 切换项显示 Live，然后选择 Export (`E`) → WebM，下载 6 秒的轨迹动画**

**说明：**
每张交互式图表的打开地址为 `https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`，查看器工具栏中的 **Export** 按钮（快捷键 `E`）可立即生成可分享文件；具体功能取决于查看器版本、浏览器支持和当前选择内容。操作步骤是：(1) 打开图表；(2) 确认 **Live/Still** 切换项显示 Live，因为沿箭头流动的动画会被录制；(3) 选择 **Export → WebM** 发布动态内容，或选择 **Export → Share Card** 生成静态 1200×630 预览；(4) 与源文档 URL 一起发布。WebM 会先显示“正在录制 6 秒动画…”，然后下载文件；它需要带有轨迹动画的图表和浏览器 MediaRecorder 支持。SVG 是适用于幻灯片的双主题矢量格式。

</details>

7. 关于 Export 菜单中的 **Route Share Card**，哪项说法正确？
   - A) 每张图都会显示它，并根据相邻形状自动推断路线
   - B) 只有 Route Probe (`R`) 解析出两个节点间的路径后才会显示，并且只沿用作者声明的有向关系
   - C) 它显示节点的上游/下游可达性，作为故障影响范围分析
   - D) 它仅支持复制到剪贴板，不支持下载
<details>
<summary>显示答案</summary>

**答案：B) 只有 Route Probe (`R`) 解析出两个节点间的路径后才会显示，并且只沿用作者声明的有向关系**

**说明：**
Export 菜单表格中，Route Share Card 是 1200×630 的 PNG（仅支持下载），且“只有 Route Probe (`R`) 解析出两个节点间的路径后才会显示”。真实性边界一节补充说明：“Route Share Card 只遵循作者声明的有向关系。它绝不会根据图形布局推断路线，也不会导出过期或不可达的路线。”上游/下游可达性属于单独的 Reach Share Card；即使是该卡片，也不得将其表述为影响分析、故障影响范围（blast radius）、故障或运行时因果关系。

</details>

8. 路线图对 Share Card 等导出文件的“真实性边界”持什么立场？
   - A) 导出文件是沟通素材（不是架构经过验证的证据），Share Card 也绝不声称架构已验证
   - B) Share Card 会自动显示“已验证”徽章，可以作为验证证据
   - C) 导出文件是正式交付物，会取代已发布的 HTML
   - D) Reach Share Card 衡量运行时故障传播，可直接放入事件报告
<details>
<summary>显示答案</summary>

**答案：A) 导出文件是沟通素材（不是架构经过验证的证据），Share Card 也绝不声称架构已验证**

**说明：**
该部分的第一条指出：“导出文件是沟通素材。它们不是架构经过验证的证据，也不能取代已发布的 HTML 或作者自己的验证。Share Card 绝不声称架构已验证。”同样，Reach Share Card 只显示*作者声明的可达性*，因此不得将其表述为影响分析、故障影响范围（blast radius）、故障或运行时因果关系。

</details>
