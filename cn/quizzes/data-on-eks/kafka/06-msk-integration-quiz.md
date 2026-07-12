# MSK 集成测验

本测验检验你对 Amazon MSK 与 self-managed Strimzi 之间权衡的理解，以及如何将 EKS workloads 连接到 MSK、MSK Connect，以及 Kafka 和 Kinesis Data Streams 之间的差异。

## 多项选择题

1. Amazon MSK 与在 EKS 上 self-managed Strimzi 之间最根本的区别是什么？
   - A) MSK 不使用 Kafka 协议
   - B) brokers 实际运行的位置，以及由谁负责运维它们
   - C) Strimzi 无法在 Kubernetes 上运行
   - D) MSK 不支持 partitions 概念

<details>

<summary>显示答案</summary>

**答案：B) brokers 实际运行的位置，以及由谁负责运维它们**

**解释：**
MSK 在 AWS-managed infrastructure 上运行 brokers，AWS 会代你处理 patching、hardware replacement 和 storage expansion。Strimzi 将 brokers 作为 Pods 运行在你的 EKS cluster 内；即使 Operator 会自动执行 rolling upgrades 和 reconciliation，upgrade timing、capacity planning 和 incident response 等决策仍由你负责。两者都实现相同的 Apache Kafka 协议，因此不存在协议层面的差异。
</details>

2. 哪个说法正确描述了 MSK Serverless？
   - A) Broker 配置（`server.properties`）可以自由自定义
   - B) Broker sizing 不会暴露给用户，billing 基于 throughput
   - C) 它只适用于基于 ZooKeeper 的 clusters
   - D) 它总是比 MSK Provisioned 更便宜

<details>

<summary>显示答案</summary>

**答案：B) Broker sizing 不会暴露给用户，billing 基于 throughput**

**解释：**
MSK Serverless 会按 partition 自动扩缩容，用户无需考虑 broker 数量或 instance types。相反，它根据 throughput 计费 —— 按 partition、按 GB in/out。它不支持自定义 broker 配置，并且部分 APIs/features（某些 ACL types、connector types）受到限制。它是否比 Provisioned 更便宜取决于你的流量模式，因此不能假定它总是更便宜。
</details>

3. 哪种组合可以让 EKS pod 在不分发任何单独 IAM credentials 的情况下向 MSK broker 进行身份验证？
   - A) SASL/SCRAM 与 Secrets Manager
   - B) IRSA 与 `AWS_MSK_IAM` SASL mechanism
   - C) mTLS 与 AWS Private CA
   - D) 仅使用 plaintext listener 和 security groups

<details>

<summary>显示答案</summary>

**答案：B) IRSA 与 `AWS_MSK_IAM` SASL mechanism**

**解释：**
IRSA (IAM Roles for Service Accounts) 会为 pod 授予 IAM role，并且在 Kafka client 上设置 `sasl.mechanism=AWS_MSK_IAM` 会使其使用 SigV4-signed requests 进行身份验证。关键优势是没有单独的 credentials（如 passwords、certificates）需要分发或轮换。SASL/SCRAM 和 mTLS 也是有效的身份验证方法，但它们分别需要从 Secrets Manager 同步 credentials，或签发/挂载 certificates。
</details>

4. EKS workload 要访问位于不同 VPC 中的 MSK cluster，需要什么 network configuration？
   - A) MSK 必须始终切换为 public access
   - B) 必须通过 VPC peering 或 AWS Transit Gateway 连接这两个 VPC
   - C) Kafka 协议会自动跨越 VPC 边界
   - D) 仅有 NAT gateway 就足够，不需要进一步配置

<details>

<summary>显示答案</summary>

**答案：B) 必须通过 VPC peering 或 AWS Transit Gateway 连接这两个 VPC**

**解释：**
如果 EKS cluster 和 MSK cluster 位于不同的 VPC，你需要 VPC peering 或 Transit Gateway 在它们之间建立 routing。MSK 确实支持 public access，但那是可选的独立配置，并且生产环境通常出于安全原因更倾向于 private connectivity。即使已有 network path，如果 MSK cluster 的 security group 不允许来自 EKS node/pod security group 的 inbound traffic，连接仍会被阻止。
</details>

5. 关于 MSK cluster security group 配置，哪个说法是正确的？
   - A) 默认允许同一 VPC 内的所有 traffic
   - B) 必须显式允许来自 EKS node（或 pod）security group 到 broker ports 的 inbound traffic
   - C) 使用 IAM authentication 时不需要 security groups
   - D) Security group 配置仅适用于 MSK Serverless

<details>

<summary>显示答案</summary>

**答案：B) 必须显式允许来自 EKS node（或 pod）security group 到 broker ports 的 inbound traffic**

**解释：**
MSK cluster 的 security group 默认不允许任何 inbound traffic。你必须显式添加 inbound rule，允许 EKS worker node（或在使用 per-pod security groups 时的 pod）security group 作为相关 broker ports 的 source —— plaintext 9092、TLS 9094、SASL/SCRAM 9096、IAM 9098。无论你使用哪种 authentication mechanism（IAM、SCRAM、mTLS），都需要这条 network-layer security group rule。
</details>

6. 关于 MSK Connect，哪个说法是正确的？
   - A) 它只能连接到 MSK clusters，不能连接到其他 Kafka clusters
   - B) 只要它能够通过网络访问 bootstrap brokers，它也可以针对 EKS 上的 Strimzi cluster 运行 connectors
   - C) 用户必须自行管理 Connect workers 的 scaling 和 patching
   - D) Connector plugins 只能注册为 container images

<details>

<summary>显示答案</summary>

**答案：B) 只要它能够通过网络访问 bootstrap brokers，它也可以针对 EKS 上的 Strimzi cluster 运行 connectors**

**解释：**
MSK Connect 并不局限于 MSK clusters。只要 connector 能够通过网络访问 bootstrap brokers，就可以将它指向任何 Kafka cluster，包括 EKS 上的 self-managed Strimzi cluster。AWS 会管理 Connect worker infrastructure 的 provisioning、scaling 和 patching，因此用户无需自行管理。Custom connector plugins 通过将 JARs 的 ZIP 上传到 S3 来注册。
</details>

7. 哪个说法正确描述了 Kafka 与 Kinesis Data Streams 之间的关系？
   - A) 因为 MSK 是 “Kafka-compatible”，Kinesis client 可以直接连接到 MSK
   - B) Kafka 和 Kinesis 是使用不同协议的独立服务，并不直接兼容
   - C) Kinesis 在内部原样实现 Kafka 协议
   - D) Kafka client 只需更改配置即可直接连接到 Kinesis stream

<details>

<summary>显示答案</summary>

**答案：B) Kafka 和 Kinesis 是使用不同协议的独立服务，并不直接兼容**

**解释：**
Kinesis Data Streams 是一个完全独立的服务，拥有自己的 AWS-proprietary API/SDK；它并不理解 Kafka producer/consumer 协议。当 MSK 被描述为 “Kafka-compatible” 时，这只表示它实现了 Apache Kafka 协议，并不意味着它能与 Kinesis 互操作。桥接二者需要单独的一层，例如运行在 Kafka Connect（或 MSK Connect）下的 Kinesis sink/source connectors。
</details>

8. 实际桥接 Kafka 和 Kinesis Data Streams 的正确方式是什么？
   - A) 将 Kafka client 的 `bootstrap.servers` 指向 Kinesis endpoint
   - B) 在 Kafka Connect 或 MSK Connect 下使用 Kinesis sink/source connector
   - C) 使用一个将 MSK cluster 切换到 “Kinesis mode” 的配置标志
   - D) 它们可以直接互相引用，因为它们共享相同的 partition model

<details>

<summary>显示答案</summary>

**答案：B) 在 Kafka Connect 或 MSK Connect 下使用 Kinesis sink/source connector**

**解释：**
由于 Kafka 和 Kinesis 协议不兼容，桥接它们需要 connector 来执行转换。Kinesis sink connector 从 Kafka topic 读取 messages 并写入 Kinesis stream；Kinesis source connector 从 Kinesis stream 读取 records 并写入 Kafka topic。这些 connectors 可以部署在 MSK Connect 上，也可以通过 Strimzi 的 `KafkaConnect`/`KafkaConnector` CRs 直接在 EKS 上运行。
</details>

9. 尽管存在 MSK，以下哪项不是继续在 EKS 上使用 Strimzi 自行运行 Kafka 的有效理由？
   - A) 你希望 Kafka 适配与平台其他部分相同的 GitOps/observability pipeline
   - B) 你需要对 on-prem 或 multi-cloud environments 的可移植性
   - C) 你需要 MSK 尚未支持的较新 Kafka feature
   - D) 你完全不想拥有任何 broker operations staff

<details>

<summary>显示答案</summary>

**答案：D) 你完全不想拥有任何 broker operations staff**

**解释：**
Self-managed Strimzi 通过 Operator 自动化了很多事情，但 upgrade timing、capacity planning 和 incident response 等决策仍由你负责。如果你想完全消除 broker operations 负担，MSK（尤其是 MSK Serverless）实际上更合适。GitOps 集成、可移植性以及访问最新 Kafka features 都是在 EKS 上运行 Strimzi 的合理理由。
</details>

10. 哪个说法最准确地描述了 MSK Provisioned 与 self-managed Strimzi 之间 cost model 的差异？
    - A) MSK 总是比 Strimzi 更便宜
    - B) MSK 按 broker-hour 加 storage 计费，而 Strimzi 会产生直接的 EC2/EBS cost 以及单独的 operational staffing cost
    - C) Strimzi 没有 billing model，完全免费
    - D) 两种 cost models 完全相同

<details>

<summary>显示答案</summary>

**答案：B) MSK 按 broker-hour 加 storage 计费，而 Strimzi 会产生直接的 EC2/EBS cost 以及单独的 operational staffing cost**

**解释：**
MSK Provisioned 基于 per-broker-hour pricing、storage（GB-month）和 data transfer 计费。Strimzi 让你直接为 EC2/EBS infrastructure 付费——通常在规模较大时更便宜——但运维它的人员成本是一个单独的额外考虑因素。哪种选项在 total cost of ownership 上胜出，取决于 traffic volume、组织的 operational capability 和 labor costs。
</details>

## 简答题

11. EKS pod 使用 IAM role 向 MSK 进行身份验证时所用的 SASL mechanism 的确切名称是什么？

<details>

<summary>显示答案</summary>

**答案：`AWS_MSK_IAM`**

**解释：**
`AWS_MSK_IAM` 是 MSK 提供的 SASL mechanism，允许 clients 使用 SigV4-signed credentials（IAM role 或 user）进行身份验证。在 client configuration 中，你设置 `security.protocol=SASL_SSL` 和 `sasl.mechanism=AWS_MSK_IAM`，并将 `aws-msk-iam-auth` library 中的 `IAMLoginModule` 和 `IAMClientCallbackHandler` 注册为 JAAS login module 和 callback handler。
</details>

12. MSK client 为使用 IAM authentication，必须将哪个 library 添加到其 classpath（或该语言对应的 package manager）？

<details>

<summary>显示答案</summary>

**答案：`aws-msk-iam-auth`**

**解释：**
`aws-msk-iam-auth` 是 AWS 提供的 client library，用于实现 `AWS_MSK_IAM`，这是一种专用的 custom SASL mechanism（不是 OAUTHBEARER extension），让 Kafka clients 能够生成 SigV4-signed requests，并使用 IAM credentials 向 MSK brokers 进行身份验证。Java client 以 Maven artifact 的形式分发，其他语言（Python、Go 等）也有相应的 community implementations。
</details>

13. AWS 的 fully managed Kafka Connect service 名称是什么？在该服务中，AWS 负责 connector workers 的 provisioning 和 scaling。

<details>

<summary>显示答案</summary>

**答案：MSK Connect**

**解释：**
MSK Connect 是由 AWS 管理 Kafka Connect worker cluster 的 provisioning、scaling 和 patching 的服务。用户只需将 connector plugins（JARs 的 ZIP）上传到 S3 并注册 connector configuration。它不仅可以连接到 MSK clusters，也可以连接到任何网络可达的 Kafka cluster，包括 EKS 上的 Strimzi cluster。
</details>

14. Kinesis Data Streams 中对应 Kafka “partition” 的 scaling unit 名称是什么？

<details>

<summary>显示答案</summary>

**答案：Shard**

**解释：**
Kafka 将 topic 划分为多个 partitions，以实现 parallelism 和 scalability；partition count 在 topic 创建时定义，之后可以通过 repartitioning 调整。Kinesis 则将 read/write capacity 划分为 shards，并通过 shard split 和 merge operations 来调整 capacity。这两个概念服务于类似目的，但在 API 和 operational mechanics 上有所不同。
</details>

15. 哪种 Kafka Connect connector 会从 Kafka topic 读取 messages 并将它们写入 Kinesis stream？

<details>

<summary>显示答案</summary>

**答案：Kinesis Sink connector**

**解释：**
Kinesis Sink connector 将 Kafka topic 作为 source，读取 messages 并写入 Kinesis stream。相反，Kinesis Source connector 从 Kinesis stream 读取 records 并写入 Kafka topic。这两种 connectors 的存在正是因为 Kafka 和 Kinesis 没有协议兼容性——它们才是真正桥接两者之间数据的层。
</details>

## 实操题

16. 编写 AWS CLI command，允许从 EKS worker node security group（`sg-0efgh5678eksnode`）到 MSK cluster security group（`sg-0abcd1234msk`）上 IAM authentication port 的 inbound traffic。

<details>

<summary>显示答案</summary>

**答案：**
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

**解释：**
MSK 的 IAM authentication port 是 9098。在 `authorize-security-group-ingress` 中，`--group-id` 指定要添加规则的目标 security group（MSK security group），`--source-group` 指定允许的 traffic source（EKS node security group）。没有这条规则，即使 IAM authentication 尝试成功，也会在 TCP connection 阶段被阻止。如果使用不同的 auth mechanism，请相应调整 port（TLS: 9094，SASL/SCRAM: 9096）。
</details>

17. 编写一个 IAM policy JSON，授予使用 IAM authentication 的 Kafka client 仅对特定 MSK cluster 上的 `orders` topic 的 read/write access。

<details>

<summary>显示答案</summary>

**答案：**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
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

**解释：**
第一条 statement 授予连接到 cluster 并描述其状态所需的最低权限（`Connect`、`DescribeCluster`）。第二条 statement 将 resource ARN 限定到 `topic/my-msk-cluster/*/orders`，仅为 `orders` topic 授予 topic-related actions、write（`WriteData`）和 read（`ReadData`）权限。如此严格地限定 resource ARN 意味着 client 无法访问同一 cluster 上的任何其他 topic。
</details>

18. 编写一个 Kafka client configuration（properties）file，将 client 配置为使用 `AWS_MSK_IAM` mechanism。

<details>

<summary>显示答案</summary>

**答案：**
```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

**解释：**
`security.protocol=SASL_SSL` 指定将 SASL authentication 与 TLS encryption 一起使用。`sasl.mechanism=AWS_MSK_IAM` 选择基于 IAM 的 SASL mechanism。`sasl.jaas.config` 将 `aws-msk-iam-auth` library 中的 `IAMLoginModule` 注册为 JAAS login module，`sasl.client.callback.handler.class` 指定生成 SigV4-signed request 的 callback handler。仅使用此配置，client 就会自动使用其本地 credential chain 进行身份验证，包括通过 IRSA 注入的 IAM role。
</details>

---

[返回学习材料](../../../data-on-eks/kafka/06-msk-integration.md) | [下一个测验：Monitoring](./07-monitoring-quiz.md)
