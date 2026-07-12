# 第 6 部分：MSK 集成

> **支持的版本**: Amazon MSK (Provisioned & Serverless), MSK Connect\
> **最后更新**: July 9, 2026

## 实验环境设置

要跟随本文档中的示例进行操作，你需要以下工具和环境：

### 必需工具

* AWS CLI v2（用于管理 MSK cluster 和 IAM policies）
* kubectl v1.28 或更高版本，以及一个可用的 EKS cluster
* `aws-msk-iam-auth` client library（用于使用 IAM authentication 的 Kafka clients）
* 配置了 External Secrets Operator 或 IRSA 的 EKS cluster（用于 credential injection）

前面的部分介绍了如何使用 Strimzi 在 EKS 上自行运行 Kafka。本部分介绍如何将 EKS workloads 连接到 Amazon MSK —— AWS 的完全托管 Kafka 服务 —— 以及它与自管理 Strimzi 方式之间的取舍。它还澄清了一个常见的混淆点：Kafka 与 Kinesis Data Streams 之间的关系，后者是一个完全独立的 AWS streaming service。

## Amazon MSK 与自管理 Strimzi

这两种方式都能让 EKS workload 与 Kafka 通信，但它们的不同之处在于 brokers 实际运行的位置以及由谁来运维。MSK 在你的 cluster 之外、由 AWS 管理的基础设施上运行 brokers；Strimzi 则将 brokers 作为 Pods 运行在你的 EKS cluster 内。

| 方面 | Amazon MSK (Provisioned) | Amazon MSK Serverless | Strimzi（在 EKS 上自管理） |
| --- | --- | --- | --- |
| **运维负担** | AWS 负责 broker patching、hardware replacement 和 storage expansion | AWS 完全移除 broker sizing（完全自动扩展） | Operator 会自动化 rolling upgrades/reconciliation，但你仍然负责 upgrade timing、capacity planning 和 incident response |
| **成本模型** | 按 broker-hour + storage (GB-month) + data transfer 计费 | 基于 throughput（按 partition、每 GB in/out） | 直接 EC2/EBS 成本 —— 通常在规模化时更便宜，但你需要单独承担运维人员成本 |
| **自动扩展** | 支持 storage auto-expansion；broker scaling 需要手动或通过 API 驱动 | 完全自动的 per-partition scaling；brokers 不作为概念暴露 | 可通过 Cruise Control 等工具实现半自动化，但通常由你触发 |
| **自定义配置** | 可以自定义 broker configuration (`server.properties`) | 不支持自定义 broker config；部分 APIs/features 受限（例如某些 ACL types、connector types） | 几乎所有内容都可调优 —— listeners、interceptors、KRaft controller settings |
| **版本支持** | AWS 维护受支持的 Kafka version list，可能落后于 upstream | 固定版本，不能选择版本 | 只要 Strimzi 支持，就可以在 upstream 发布后采用任意 Kafka version |
| **多租户** | 通过 cluster/resource policies 隔离；细粒度定制有限 | Tenant isolation 委托给 AWS 的内部实现 | 通过 namespaces、`KafkaUser` ACLs 和 custom listeners 实现细粒度租户能力 |
| **Observability/GitOps 适配** | 通过 CloudWatch/Prometheus exporters 集成；AWS console 是主要管理界面 | 相同 | 能自然融入与平台其余部分相同的 GitOps/observability pipeline（Argo CD、Prometheus Operator） |

### 为什么选择 MSK

* 你的团队缺乏深入的 Kafka broker 运维经验，或者不希望将 Kafka 运维作为核心能力
* 你已经大量投入 AWS-native operations tooling（console、IAM、CloudWatch）
* 流量难以预测，而 MSK Serverless 可以让你完全消除 broker capacity planning

### 尽管 MSK 存在，为什么仍要使用 Strimzi 在 EKS 上自行运行 Kafka

* 你希望用与平台其余部分**相同的工具和相同的 deployment pipeline** 来管理 Kafka —— 其他 workloads、GitOps、Prometheus/Grafana —— 而无需增加第二套 AWS console/IAM 操作界面
* 你需要不绑定到单一 cloud 的**可移植性**（on-prem、multi-cloud migration potential）
* 在非常大的规模下，直接管理 EC2/EBS 比按 broker-hour 定价更具成本效益
* 你需要最新的 Kafka features（新的 KIPs、custom interceptors、特定的 KRaft tuning options），而 MSK 还没有跟上

## 从 EKS 连接到 MSK

要让 EKS workload 访问 MSK brokers，你同时需要网络路径和 authentication mechanism。

### 网络路径

* **Same VPC**：如果 EKS cluster 和 MSK cluster 位于同一个 VPC，仅靠 subnet routing 就能获得连接性 —— 最简单且延迟最低。
* **Different VPC**：你需要 VPC peering 或 AWS Transit Gateway 来连接两个 VPC。MSK 确实支持 public access（public broker endpoints），但生产环境通常倾向于 private connectivity。
* **Security groups**：MSK cluster 的 security group 必须在相关 broker ports 上显式允许来自 EKS node（或 pod，如果 pods 有自己的 security groups）security group 的 inbound traffic —— plaintext 9092、TLS 9094、SASL/SCRAM 9096、IAM 9098。默认情况下不允许任何流量。

```bash
# Allow the IAM auth port on the MSK security group from the EKS node security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

### Authentication mechanisms 对比

| 机制 | 工作方式 | EKS 集成点 |
| --- | --- | --- |
| **IAM authentication (`AWS_MSK_IAM`)** | Client 使用 `AWS_MSK_IAM` 通过 SigV4-signed request 进行身份验证，这是一个专用的 custom SASL mechanism（不是 OAUTHBEARER extension）；IAM policies 控制 per-topic permissions | 通过 IRSA 为 pod 授予 IAM role —— 完全不需要分发 credentials |
| **SASL/SCRAM** | 基于 username/password；credentials 存储在 AWS Secrets Manager 中 | 通过 External Secrets Operator 将 SCRAM credentials 从 Secrets Manager 同步到 Kubernetes Secret |
| **Mutual TLS (mTLS)** | 由 AWS Private CA 颁发 client certificates；通过 certificate 验证身份 | 通过 cert-manager 或 External Secrets Operator 将 certificates/keys 挂载到 pods 中 |

IAM authentication 最适合 EKS。使用 IRSA (IAM Roles for Service Accounts)，你可以为 pod 授予作用域受限的 IAM role，并完全通过 IAM policy 表达 topic-level access control —— 无需分发或轮换密码或证书。

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

在 client 端，将 `aws-msk-iam-auth` library 添加到你的 classpath（或使用对应语言的等效 package），然后按如下方式配置 Kafka client：

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

## MSK Connect

MSK Connect 是 AWS 的完全托管 Kafka Connect 产品。AWS 负责 Connect worker infrastructure 的 provisioning、scaling 和 patching；你通过将 connector plugins（JAR bundles）上传到 S3 来注册它们。

重要细节是：MSK Connect **并不限于 MSK clusters**。只要它能够通过网络访问 bootstrap brokers，MSK Connect 也可以针对通过 Strimzi 运行在 EKS 上的自管理 Kafka cluster 运行 connectors。

```bash
# Upload a custom connector plugin to S3 and register it as an MSK Connect custom plugin
aws kafkaconnect create-custom-plugin \
  --name debezium-postgres-plugin \
  --content-type ZIP \
  --location s3Location='{bucketArn=arn:aws:s3:::my-connect-plugins,fileKey=debezium-postgres-2.7.zip}'
```

| 方面 | MSK Connect | Strimzi `KafkaConnect`（在 EKS 上自运维） |
| --- | --- | --- |
| **运维负担** | AWS 管理 worker infrastructure；你只管理 connector configuration | 你需要自行管理 worker pod scaling、monitoring 和 resource tuning |
| **灵活性** | 受限于 AWS 支持的 connector framework | 对任意 connectors、custom SMTs (Single Message Transforms)、sidecars 拥有完全自由 |
| **可移植性** | 仅限 AWS 的服务，很难迁移到其他地方 | 可原样移植到任何其他 Kubernetes cluster |
| **Observability** | 通过 CloudWatch Logs/Metrics 查看 connector status | 集成到与 EKS workloads 其余部分相同的 Prometheus/Grafana pipeline 中 |

## 与 Kinesis Data Streams 的比较与桥接

Kinesis Data Streams 和 Kafka 经常被一起提及，但它们**不是兼容的协议**。Kinesis 是一种 AWS-native streaming service，拥有自己的 API/SDK，并不了解 Kafka 的 producer/consumer protocol。MSK 被描述为“Kafka-compatible”并不意味着它能与 Kinesis 互操作 —— MSK 是 Apache Kafka protocol 的托管实现，而 Kinesis 是一个完全独立的服务。

| 方面 | Apache Kafka (MSK/Strimzi) | Kinesis Data Streams |
| --- | --- | --- |
| **协议** | Open-source Kafka protocol，兼容广泛的 client/tooling ecosystem | AWS-proprietary API，不兼容 Kafka clients |
| **扩展单位** | Partitions（在 topic 创建时定义，可重新分区） | Shards（read/write capacity units，通过 split/merge 调整） |
| **运维复杂度** | 需要运维 brokers/controllers（MSK 将其卸载给 AWS） | 完全托管，完全没有 server 概念 |
| **AWS service integration** | 间接，通过 connectors（Kafka Connect、MSK Connect） | 原生，直接与 Lambda triggers、Firehose、Kinesis Data Analytics 集成 |
| **生态系统** | 广泛的 open-source ecosystem：Kafka Streams、ksqlDB、Flink、Debezium | 更小、以 AWS-service 为中心的 ecosystem，但更易于集成 |
| **Retention** | 实际上不受限制（只需为 storage 付费；默认 7 天） | 默认 24 小时，可扩展到最长 365 天（成本随之增加） |

### 真正的桥接模式

如果你需要真正连接 Kafka 和 Kinesis —— 用于迁移，或与 legacy Kinesis consumers 桥接 —— 实用模式是在 Kafka Connect（或 MSK Connect）下运行 **Kinesis connector**，而不是依赖任何内置的 protocol compatibility。

* **Kinesis Sink connector**：从 Kafka topic 读取 messages 并写入 Kinesis stream —— 适用于将基于 Kafka 的 pipeline 输出送入 Kinesis consumption ecosystem（Lambda、Firehose）
* **Kinesis Source connector**：从 Kinesis stream 读取 records 并写入 Kafka topic —— 适用于在逐步将 consumers 迁移到 Kafka 的同时，保留现有 Kinesis producers

这些 connectors 可以部署在 MSK Connect 上，也可以通过 Strimzi 的 `KafkaConnect`/`KafkaConnector` CRs 直接运行在 EKS 上 —— 上一节中的 MSK Connect 与 Strimzi 取舍同样适用于这里。

## 决策指南

使用此 checklist 在自管理 Strimzi、MSK Provisioned、MSK Serverless 和 Kinesis 之间缩小选择范围。

* **你的团队是否具备 Kafka 运维经验，并且需要细粒度调优/自定义配置？** → 是：Strimzi（在 EKS 上自管理）/ 否：考虑 MSK
* **multi-cloud/on-prem 可移植性是否是硬性要求？** → 是：Strimzi / 否：MSK 值得评估
* **流量是否不可预测或有突发峰值，并且你想完全消除 broker capacity planning？** → 是：MSK Serverless / 否：MSK Provisioned 或 Strimzi
* **你是否已经深入投入 AWS-native event processing（Lambda、Firehose），并且不需要 Kafka ecosystem（Kafka Streams、ksqlDB 等）？** → 是：评估 Kinesis Data Streams / 否：继续使用 Kafka（MSK/Strimzi）
* **你是否希望通过与 EKS platform 其余部分相同的 GitOps pipeline 来管理 Kafka，而不增加 AWS console/IAM 界面？** → 是：Strimzi / 否：MSK

在实践中，答案通常是“both” —— 为了速度在 MSK Serverless 上启动一个新服务，然后在需要 custom tuning 时迁移到 Strimzi，这是常见路径。

## 后续步骤

无论你运行 MSK 还是 Strimzi，都需要持续查看 broker metrics 和 consumer lag，以了解 cluster 是否健康。这是[第 7 部分：监控](./07-monitoring.md)的主题。

[返回主页面](./)

## 测验

要测试你在本章中学到的内容，请尝试[主题测验](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)。
