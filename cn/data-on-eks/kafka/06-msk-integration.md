# 第 6 部分：MSK 集成

> **支持的版本**：Amazon MSK（Provisioned 和 Serverless）、MSK Connect\
> **最后更新**：July 9, 2026

## 实验环境设置

要跟随本文档中的示例操作，您需要以下工具和环境：

### 必需工具

* AWS CLI v2（用于管理 MSK 集群和 IAM 策略）
* kubectl v1.28 或更高版本，以及一个可用的 EKS 集群
* `aws-msk-iam-auth` 客户端库（供使用 IAM 身份验证的 Kafka 客户端使用）
* 已配置 External Secrets Operator 或 IRSA 的 EKS 集群（用于凭证注入）

前面的部分介绍了如何使用 Strimzi 在 EKS 上自行运行 Kafka。本部分介绍如何将 EKS 工作负载连接到 Amazon MSK（AWS 的全托管 Kafka 服务），以及与自主管理的 Strimzi 方案相比的取舍。它还澄清了一个常见的困惑点：Kafka 与 Kinesis Data Streams 的关系；后者是完全独立的 AWS 流式服务。

## Amazon MSK 与自主管理的 Strimzi

两种方法都能让 EKS 工作负载与 Kafka 通信，但它们在 broker 实际运行的位置以及由谁负责运维方面有所不同。MSK 在集群外由 AWS 管理的基础设施上运行 broker；Strimzi 则在您的 EKS 集群内以 Pod 形式运行 broker。

| 方面 | Amazon MSK（Provisioned） | Amazon MSK Serverless | Strimzi（在 EKS 上自主管理） |
| --- | --- | --- | --- |
| **运维负担** | AWS 负责 broker 补丁、硬件更换和存储扩展 | AWS 完全免除 broker 容量规划（全自动扩缩容） | Operator 自动执行滚动升级/协调，但您仍需负责升级时机、容量规划和事件响应 |
| **成本模型** | 按每 broker 小时 + 存储（GB-月）+ 数据传输计费 | 基于吞吐量（每 partition、每 GB 输入/输出） | 直接承担 EC2/EBS 成本——通常在大规模下更便宜，但您还需另行承担运维人力成本 |
| **自动扩缩容** | 支持存储自动扩展；broker 扩缩容通过手动/API 驱动 | 按 partition 全自动扩缩容；broker 不是对外暴露的概念 | 可通过 Cruise Control 等工具半自动实现，但通常仍需您触发 |
| **自定义配置** | 可以自定义 broker 配置（`server.properties`） | 不支持自定义 broker 配置；部分 API/功能受限（例如某些 ACL 类型、connector 类型） | 几乎所有内容都可调——listener、interceptor、KRaft controller 设置 |
| **版本支持** | AWS 维护受支持的 Kafka 版本列表，可能落后于上游 | 固定版本，不能选择版本 | 可在上游发布后随时采用 Strimzi 支持的任何 Kafka 版本 |
| **多租户** | 通过集群/资源策略隔离；细粒度自定义能力有限 | 租户隔离由 AWS 的内部实现负责 | 通过 namespace、`KafkaUser` ACL 和自定义 listener 实现细粒度租户隔离 |
| **可观测性/GitOps 适配** | 通过 CloudWatch/Prometheus exporter 集成；AWS console 是主要管理界面 | 相同 | 可自然融入与平台其余部分相同的 GitOps/可观测性流水线（Argo CD、Prometheus Operator） |

### 为什么选择 MSK

* 您的团队缺乏深厚的 Kafka broker 运维专业能力，或者不希望 Kafka 运维成为核心竞争力
* 您已经深度采用 AWS 原生运维工具（console、IAM、CloudWatch）
* 流量难以预测，而 MSK Serverless 可以让您完全免除 broker 容量规划

### 为什么仍要在 EKS 上使用 Strimzi 自行运行 Kafka（即使已有 MSK）

* 您希望使用与平台其余部分**相同的工具和相同的部署流水线**来管理 Kafka——其他工作负载、GitOps、Prometheus/Grafana——而无需增加第二个 AWS console/IAM 管理界面
* 您需要不绑定于单一云的**可移植性**（本地部署、多云迁移潜力）
* 在非常大的规模下，直接管理 EC2/EBS 比按每 broker 小时计费更具成本效益
* 您需要 MSK 尚未跟进的最新 Kafka 功能（新的 KIP、自定义 interceptor、特定的 KRaft 调优选项）

## 从 EKS 连接到 MSK

EKS 工作负载要访问 MSK broker，既需要网络路径，也需要身份验证机制。

### 网络路径

* **相同 VPC**：如果 EKS 集群和 MSK 集群位于同一个 VPC，仅通过 subnet 路由即可实现连接——最简单且延迟最低。
* **不同 VPC**：您需要 VPC peering 或 AWS Transit Gateway 来连接两个 VPC。MSK 确实支持公共访问（公共 broker endpoint），但生产环境通常倾向于私有连接。
* **安全组**：MSK 集群的安全组必须明确允许来自 EKS node（或 Pod，如果 Pod 有自己的安全组）安全组在相关 broker 端口上的入站流量——plaintext 9092、TLS 9094、SASL/SCRAM 9096、IAM 9098。默认不允许任何流量。

```bash
# Allow the IAM auth port on the MSK security group from the EKS node security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

### 身份验证机制对比

| 机制 | 工作原理 | EKS 集成点 |
| --- | --- | --- |
| **IAM 身份验证（`AWS_MSK_IAM`）** | 客户端使用 `AWS_MSK_IAM`（专用的自定义 SASL 机制，而非 OAUTHBEARER 扩展）和由 SigV4 签名的请求进行身份验证；IAM 策略控制每个 topic 的权限 | 通过 IRSA 为 Pod 授予 IAM role——完全无需分发凭证 |
| **SASL/SCRAM** | 基于用户名/密码；凭证存储在 AWS Secrets Manager 中 | 通过 External Secrets Operator 将 Secrets Manager 中的 SCRAM 凭证同步到 Kubernetes Secret |
| **双向 TLS（mTLS）** | 客户端证书由 AWS Private CA 签发；通过证书验证身份 | 通过 cert-manager 或 External Secrets Operator 将证书/密钥挂载到 Pod 中 |

IAM 身份验证最适合 EKS。借助 IRSA（IAM Roles for Service Accounts），您可以为 Pod 授予范围受限的 IAM role，并且仅通过 IAM 策略表达 topic 级访问控制——无需分发或轮换密码和证书。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
        "kafka-cluster:AlterCluster",
        "kafka-cluster:DescribeCluster"
      ],
      "Resource": "arn:aws:kafka:us-east-1:111122223333:cluster/my-msk-cluster/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:*Topic*",
        "kafka-cluster:WriteData",
        "kafka-cluster:ReadData"
      ],
      "Resource": "arn:aws:kafka:us-east-1:111122223333:topic/my-msk-cluster/*/orders"
    }
  ]
}
```

在客户端侧，将 `aws-msk-iam-auth` 库添加到 classpath 中（或使用您的语言对应的软件包），然后使用以下配置设置 Kafka 客户端：

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

## MSK Connect

MSK Connect 是 AWS 的全托管 Kafka Connect 产品。AWS 负责 Connect worker 基础设施的预置、扩缩容和打补丁；您通过上传到 S3 的方式注册 connector plugin（JAR bundle）。

重要细节是：MSK Connect **不仅限于 MSK 集群**。只要能通过网络访问 bootstrap broker，MSK Connect 也可以针对通过 Strimzi 在 EKS 上运行的自主管理 Kafka 集群运行 connector。

```bash
# Upload a custom connector plugin to S3 and register it as an MSK Connect custom plugin
aws kafkaconnect create-custom-plugin \
  --name debezium-postgres-plugin \
  --content-type ZIP \
  --location s3Location='{bucketArn=arn:aws:s3:::my-connect-plugins,fileKey=debezium-postgres-2.7.zip}'
```

| 方面 | MSK Connect | Strimzi `KafkaConnect`（在 EKS 上自行运维） |
| --- | --- | --- |
| **运维负担** | AWS 管理 worker 基础设施；您只需管理 connector 配置 | 您需要自行管理 worker Pod 扩缩容、监控和资源调优 |
| **灵活性** | 仅限于 AWS 支持的 connector 框架 | 可完全自由使用任意 connector、自定义 SMT（Single Message Transform）、sidecar |
| **可移植性** | 仅限 AWS 的服务，难以迁移到其他地方 | 可原样移植到任何其他 Kubernetes 集群 |
| **可观测性** | 通过 CloudWatch Logs/Metrics 查看 connector 状态 | 融入与其余 EKS 工作负载相同的 Prometheus/Grafana 流水线 |

## 与 Kinesis Data Streams 的比较和桥接

Kinesis Data Streams 和 Kafka 经常被一同提及，但它们**并非兼容协议**。Kinesis 是具有自身 API/SDK 的 AWS 原生流式服务，不理解 Kafka 的 producer/consumer 协议。MSK 被描述为“Kafka-compatible”并不意味着它可以与 Kinesis 互操作——MSK 是 Apache Kafka 协议的托管实现，而 Kinesis 是完全独立的服务。

| 方面 | Apache Kafka（MSK/Strimzi） | Kinesis Data Streams |
| --- | --- | --- |
| **协议** | 开源 Kafka 协议，兼容广泛的客户端/工具生态系统 | AWS 专有 API，与 Kafka 客户端不兼容 |
| **扩缩容单位** | partition（在创建 topic 时定义，可以重新分区） | shard（读/写容量单位，通过拆分/合并调整） |
| **运维复杂度** | 需要运维 broker/controller（MSK 将此工作卸载给 AWS） | 全托管，完全没有 server 概念 |
| **AWS 服务集成** | 间接集成，通过 connector（Kafka Connect、MSK Connect） | 原生集成，可直接集成 Lambda trigger、Firehose、Kinesis Data Analytics |
| **生态系统** | 广泛的开源生态系统：Kafka Streams、ksqlDB、Flink、Debezium | 较小、以 AWS 服务为中心的生态系统，但集成更简单 |
| **保留期** | 实际上无限（仅为存储付费；默认 7 天） | 默认 24 小时，可延长至最多 365 天（成本随之增加） |

### 实际的桥接模式

如果您确实需要连接 Kafka 和 Kinesis——用于迁移，或与遗留 Kinesis consumer 桥接——实用模式是在 Kafka Connect（或 MSK Connect）下运行 **Kinesis connector**，而不是依赖任何内置协议兼容性。

* **Kinesis Sink connector**：从 Kafka topic 读取消息并将其写入 Kinesis stream——适合将基于 Kafka 的流水线输出提供给 Kinesis 消费生态系统（Lambda、Firehose）
* **Kinesis Source connector**：从 Kinesis stream 读取记录并将其写入 Kafka topic——适合在逐步将 consumer 迁移到 Kafka 的同时保留现有 Kinesis producer

这些 connector 可以部署在 MSK Connect 上，也可以通过 Strimzi 的 `KafkaConnect`/`KafkaConnector` CR 直接在 EKS 上运行——上一节的 MSK Connect 与 Strimzi 取舍同样适用于此处。

## 决策指南

使用此清单在自主管理的 Strimzi、MSK Provisioned、MSK Serverless 和 Kinesis 之间缩小选择范围。

* **您的团队是否具备 Kafka 运维专业能力，并且需要细粒度调优/自定义配置？** → 是：Strimzi（在 EKS 上自主管理）/ 否：考虑 MSK
* **多云/本地部署可移植性是否是硬性要求？** → 是：Strimzi / 否：MSK 值得评估
* **流量是否不可预测或存在峰值，并且您希望完全免除 broker 容量规划？** → 是：MSK Serverless / 否：MSK Provisioned 或 Strimzi
* **您是否已深度采用 AWS 原生事件处理（Lambda、Firehose），且不需要 Kafka 生态系统（Kafka Streams、ksqlDB 等）？** → 是：评估 Kinesis Data Streams / 否：坚持使用 Kafka（MSK/Strimzi）
* **您是否希望通过与 EKS 平台其余部分相同的 GitOps 流水线管理 Kafka，而无需增加 AWS console/IAM 管理界面？** → 是：Strimzi / 否：MSK

在实践中，答案通常是“两者都用”——为了快速启动新服务而从 MSK Serverless 开始，然后在需要自定义调优时迁移到 Strimzi，是一种常见路径。

## 后续步骤

无论您运行的是 MSK 还是 Strimzi，都需要持续了解 broker 指标和 consumer lag，才能确认集群健康。这正是[第 7 部分：监控](./07-monitoring.md)的主题。

[返回主页](./README.md)

## 测验

要测试您在本章中所学的内容，请尝试[主题测验](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)。
