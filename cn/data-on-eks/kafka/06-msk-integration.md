# 第 6 部分：MSK 集成

> **审查基线**：MSK Standard/Express Provisioned、MSK Serverless、MSK Connect；Java IAM helper 2.3.9\
> **最后审查时间**：October 16, 2026

## 职责和先决条件

Amazon MSK 在 AWS 托管的基础设施上、EKS 集群之外运行 Kafka broker。
Strimzi 则将它们作为由团队负责运维的 Kubernetes 工作负载运行。两者都需要
对应用程序、topic、访问控制、保留和恢复作出决策。托管 broker 并不意味着
无需了解 Kafka 的行为。

使用 AWS CLI v2，以及与 EKS 集群兼容的 kubectl。IAM 客户端需要受支持的
身份验证 helper 和可正常工作的工作负载凭证链。EKS Pod Identity 或 IRSA
可以提供临时凭证；External Secrets Operator 可用于其他密钥管理工作流，
但不是 IAM 的先决条件。

## 比较实际的 MSK 变体

| 选项 | 容量和配置 | 需要计入的费用 |
| --- | --- | --- |
| MSK Provisioned Standard | 选择 broker 和存储；如有需要，配置存储自动扩缩；只能编辑受支持的 broker 设置 | Broker 时长、预置存储、可选的吞吐量/分层存储和网络费用 |
| MSK Provisioned Express | 选择 broker 计算资源；存储自动扩缩并按使用量计费；强制执行配置/吞吐量护栏 | Broker 时长、流入数据量、已用存储和适用的网络费用 |
| MSK Serverless | AWS 管理 broker 容量；用户仍需规划 topic、分区、保留和服务配额 | **集群时长**、分区时长、流入/流出数据量、已用存储和适用的网络费用 |
| EKS 上的 Strimzi | 运维节点、磁盘、broker/controller 拓扑和受支持的 Operator 配置 | EKS/EC2/EBS、网络、备用容量、可观测性和运维工作量 |

Express 是一种 **Provisioned broker 类型**，而不是 Serverless。当前文档
要求使用三个 AZ，并列出了 API/功能限制，包括对 KStreams 的支持不完整，
且不支持 KIP-932。应检查受支持的 broker/版本组合，而不是假设所有 Kafka
功能的行为都完全相同。

Serverless 要求使用 IAM 身份验证/授权；不支持 Kafka ACL。它只允许使用
列出的 topic 设置。例如，可以配置保留期限，而 `cleanup.policy` 只能在
创建 topic 时设置。其默认保留还包括**每个分区 250 GiB 的限制**，不只是
七天。流量较大时，数据可能在达到时间限制前先达到该大小。容量自动扩缩
并不意味着任意分区数量或突发速率都不受限制。

这些产品都提供 CloudWatch 指标，但 Serverless 监控并不等同于 Provisioned
提供的 broker 级 Prometheus/开放监控接口。对于 Serverless 多租户环境，
IAM topic/group policy 仍由你负责。在 Strimzi 中，Kubernetes namespace
本身并不能授权 Kafka topic 访问。

MSK 可以通过 API 和基础设施即代码进行管理；GitOps 并非 Strimzi 独有。
Strimzi 部署的可移植性仍取决于存储、网络、身份和受支持的 Operator 版本。
应比较经过测量的总成本和恢复要求；“自管理在规模扩大时总是更便宜”和
“Serverless 在流量突增时最便宜”都不是可靠的默认判断。

## 从 EKS 进行网络连接

客户端必须能够访问元数据中公布的**所有 broker 端点**，而不只是
bootstrap 地址。验证 DNS、路由、安全组、NACL、Pod/节点源身份和出站流量。
仅仅共享一个 VPC 并不足够。

对于不同的 VPC，可以选择路由对等连接/Transit Gateway，以及受支持的 MSK
**多 VPC 私有连接**（使用 PrivateLink）。托管多 VPC 功能要求位于同一区域，
并有集群/身份验证/AZ 子网方面的要求。公共端点是受支持集群的一项明确
选项，并非跨 VPC 访问的先决条件。

| 直接端点示例 | 端口 |
| --- | --- |
| 私有 IPv4 TLS | 9094 |
| 私有 IPv4 SASL/SCRAM | 9096 |
| 私有 IPv4 IAM | 9098 |
| 公共 TLS / SCRAM / IAM（受支持且已启用时） | 9194 / 9196 / 9198 |

IPv6 和托管多 VPC 端点可能使用不同的端口。获取实际的 bootstrap 响应，
并选择适用于预期网络/身份验证路径的字段；不要把所有端点都改写为 9098。

```bash
: "${DOCS_AWS_REGION:?Set the MSK region}"
: "${DOCS_MSK_CLUSTER_ARN:?Set the exact existing cluster ARN}"
aws kafka get-bootstrap-brokers \
  --region "$DOCS_AWS_REGION" \
  --cluster-arn "$DOCS_MSK_CLUSTER_ARN"
```

对于同一 VPC 中直接通过私有 IPv4 IAM 访问的情形，网络管理员在检查现有
规则后，可以应用以下范围严格受限的示例：

```bash
: "${DOCS_AWS_REGION:?Set the MSK region}"
: "${DOCS_MSK_SG_ID:?Set the existing MSK security group ID}"
: "${DOCS_EKS_SOURCE_SG_ID:?Set the actual EKS source security group ID}"
# Example: same-VPC, direct private IPv4 IAM endpoint on port 9098.
aws ec2 authorize-security-group-ingress \
  --region "$DOCS_AWS_REGION" \
  --group-id "$DOCS_MSK_SG_ID" \
  --protocol tcp --port 9098 \
  --source-group "$DOCS_EKS_SOURCE_SG_ID"
```

此命令会**更改**安全组。应根据网络路径使用实际的节点/Pod 源安全组；
不同 VPC 的安全组引用有各自的支持规则。现有安全组可能已经包含规则，
包括自引用规则。在建立 TCP/TLS 连接之前，IAM 身份验证无法成功。

## IAM 身份验证和工作负载身份

| 客户端 | 支持的 IAM 机制 |
| --- | --- |
| Java | `AWS_MSK_IAM`，或使用 AWS Java helper 的 `OAUTHBEARER` |
| Python、JavaScript、Go、.NET | 使用相应官方 AWS signer/helper 的 `OAUTHBEARER` |

`AWS_MSK_IAM` 并非所有语言的 Kafka 客户端都提供的通用机制。非 Java
helper 是 AWS 官方项目，并非仅仅是社区替代品。对于 Provisioned 集群，
也可能可以使用 SCRAM 或双向 TLS；请配置受支持的密钥/证书和 Kafka ACL
工作流。它们不能替代 Serverless 上的 IAM。

在测试 Kafka 之前，应配置工作负载角色关联/信任关系和临时凭证刷新。不要
假设继承的节点角色就是 Pod 预期使用的身份。私有环境还必须能够访问所选
凭证提供程序所需的身份服务。应在凭证刷新后测试重新身份验证。Java helper
文档说明了某些提供程序（包括 Pod Identity）存在 session name 一致性问题；
如果遇到该问题，请采用文档中说明的解决办法。

### 分离 producer 和 consumer policy

以下脚本从现有集群 ARN 推导出精确的资源 ARN。将其保存为 `policies.py`；
它会在本地生成 policy，但不会附加 policy。它省略旧的 `AlterCluster` 和
`*Topic*` 管理授权，包含 consumer-group 操作，并区分集群范围的幂等写入
权限与 topic 范围的写入权限。

```python
import json
import re
import sys
from pathlib import Path

def policies(cluster_arn, topic="orders", group="orders-consumer"):
    match = re.fullmatch(
        r"arn:(aws(?:-[a-z-]+)?):kafka:([a-z0-9-]+):(\d{12}):cluster/([A-Za-z0-9_-]+)/([A-Za-z0-9-]+)",
        cluster_arn,
    )
    if not match:
        raise ValueError("Supply an exact MSK cluster ARN, including its cluster UUID.")
    for name in [topic, group]:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,249}", name) or name in [".", ".."]:
            raise ValueError("Use an explicit topic/group name without wildcards.")
    partition, region, account, cluster_name, uuid = match.groups()
    prefix = f"arn:{partition}:kafka:{region}:{account}:"
    identity = f"{cluster_name}/{uuid}"
    topic_arn = prefix + f"topic/{identity}/{topic}"
    group_arn = prefix + f"group/{identity}/{group}"
    def statement(actions, resource):
        return {"Effect": "Allow", "Action": ["kafka-cluster:" + a for a in actions], "Resource": resource}
    return {
        "producer": {"Version": "2012-10-17", "Statement": [
            statement(["Connect", "WriteDataIdempotently"], cluster_arn),
            statement(["DescribeTopic", "WriteData"], topic_arn),
        ]},
        "consumer": {"Version": "2012-10-17", "Statement": [
            statement(["Connect"], cluster_arn),
            statement(["DescribeTopic", "ReadData"], topic_arn),
            statement(["DescribeGroup", "AlterGroup"], group_arn),
        ]},
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 policies.py EXACT_MSK_CLUSTER_ARN")
    for name, policy in policies(sys.argv[1]).items():
        Path(f"msk-{name}-policy.json").write_text(json.dumps(policy, indent=2) + "\n")
```

```bash
: "${DOCS_MSK_CLUSTER_ARN:?Set the exact existing MSK cluster ARN}"
python3 policies.py "$DOCS_MSK_CLUSTER_ARN"
# Review msk-producer-policy.json and msk-consumer-policy.json,
# then attach each to the appropriate workload role through your IAM workflow.
```

现有 topic 为 `orders`，consumer 必须使用 group `orders-consumer`。创建
topic 应由单独的管理身份负责。Producer policy 通过文档所述的 IAM 操作集
涵盖**非事务性幂等**写入。事务性 producer 还需要范围受限的事务 ID 操作，
并且 broker 必须兼容；MSK Kafka 3.8 及更高版本的 IAM 支持
`WriteTxnMarkers`。不要授予所有事务 ID 的权限，也不要仅仅为了掩盖授权
错误而禁用幂等性。

有效访问权限还取决于其他附加的 policy、显式拒绝、SCP、权限边界和跨账户
资源 policy。这些文档本身并不构成完整的授权边界。诸如
`kafka:GetBootstrapBrokers` 这样的 MSK 控制面操作，与
`kafka-cluster:*` 数据面操作相互独立，可以归属于部署者/运维者身份。

### Java 客户端配置

添加 `software.amazon.msk:aws-msk-iam-auth:2.3.9` 及其依赖项，或使用经过
验证版本的 all-in-one JAR。将以下内容保存为 `iam.properties`：

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

对于 Java 的 OAuth 机制，请使用以下替代配置，不要将两种配置组合起来：

```properties
security.protocol=SASL_SSL
sasl.mechanism=OAUTHBEARER
sasl.jaas.config=org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required;
sasl.login.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
ssl.endpoint.identification.algorithm=https
```

在应用程序中添加所选的 `bootstrap.servers`、key/value serializer 或
deserializer，以及 consumer 的 `group.id`。JVM 必须信任 broker 的 TLS
证书链；保持主机名验证启用。这些属性用于配置机制，但无法创建缺失的
工作负载凭证或 IAM 权限。

## MSK Connect：部署前先确认兼容性

MSK Connect 运行托管的 Kafka Connect worker，并可连接到独立托管的 Kafka
集群。**仅有网络可达性并不足够。**当前的
`KafkaClusterClientAuthentication` API 接受 `NONE` 或 `IAM`；broker 信任、
身份验证和受支持的 worker 设置必须相互匹配。第 2 部分中的 TLS/SCRAM
Strimzi listener 并非只要主机名可以解析就能直接用作目标。不要为了强行
集成而移除其身份验证。

该服务文档列出的 Connect 运行时为 **2.7.1 / Java 11** 和
**3.7.x / Java 17**。它们与 Kafka broker 版本不同，也不同于第 5 部分使用的
Kafka 4.3.1 Connect 运行时。请检查插件字节码、依赖项、Connect API 和供应商
支持矩阵。在 Java 17 上能够加载的 JAR，仍需在所选托管运行时上进行集成测试。

第 5 部分的构件不包含 Java 17 以上版本的基类，但这**并不能证明其与 MSK
Connect 兼容**。以下命令会在完成兼容性审查后注册 Aiven 3.4.3 ZIP。它假设
目标区域中已有一个私有 S3 bucket，并且你有权限上传/注册插件。

```bash
: "${DOCS_AWS_REGION:?Set the target region}"
: "${DOCS_PLUGIN_BUCKET:?Set an existing private S3 bucket in that region}"
DOCS_PLUGIN_ZIP="s3-sink-connector-for-apache-kafka-3.4.3.zip"
DOCS_PLUGIN_KEY="plugins/aiven-s3/3.4.3/${DOCS_PLUGIN_ZIP}"
# Download the reviewed release artifact and verify its published digest first.
aws s3 cp "$DOCS_PLUGIN_ZIP" "s3://${DOCS_PLUGIN_BUCKET}/${DOCS_PLUGIN_KEY}" \
  --region "$DOCS_AWS_REGION"
export DOCS_PLUGIN_BUCKET DOCS_PLUGIN_KEY
python3 - <<'PY'
import json
import os
from pathlib import Path
Path("custom-plugin.json").write_text(json.dumps({
    "name": "aiven-s3-3-4-3-reviewed",
    "contentType": "ZIP",
    "location": {"s3Location": {
        "bucketArn": "arn:aws:s3:::" + os.environ["DOCS_PLUGIN_BUCKET"],
        "fileKey": os.environ["DOCS_PLUGIN_KEY"]
    }}
}, indent=2) + "\n")
PY
aws kafkaconnect create-custom-plugin \
  --region "$DOCS_AWS_REGION" \
  --cli-input-json file://custom-plugin.json
```

这会上传并注册一个**插件**，而不是运行中的 connector。创建 connector 仍
需要服务执行角色、Kafka/网络设置、源/目标权限、容量和 converter 配置。
MSK Connect 默认使用 StringConverter 作为 key/value converter；必须有意
配置 CDC 示例所需的 JSON schema-envelope 设置。

MSK Connect 会在创建插件时复制 S3 对象。覆盖该对象不会更新插件，且不能
就地编辑自定义插件。应使用新的版本化插件资源和经过测试的 connector
切换计划；替换活动数据管道之前，保留并验证 offsets。自动扩缩也有配置
限制，并且无法并行处理单任务 source。

## Kafka 和 Kinesis Data Streams

Kinesis Data Streams 使用自己的 API；将 `bootstrap.servers` 替换为 Kinesis
端点，并不会把 Kafka 客户端转换为 Kinesis 客户端。Connector 或显式的流处理
桥接程序必须转换记录、键、重试行为和检查点。

| 方面 | Kafka / MSK / Strimzi | Kinesis Data Streams |
| --- | --- | --- |
| 并行度 | Topic 分区；增加分区数不会重新分配旧记录，也不支持原地减少分区数 | Shard；Provisioned 模式下手动调整容量，按需模式下由服务管理容量 |
| 容量选项 | 取决于 Standard、Express、Serverless 或自管理部署 | Provisioned、On-demand Standard 和 On-demand Advantage |
| 保留 | Topic/服务设置、存储和清理策略；时间和大小限制都很重要 | 默认 24 小时；可配置至多 365 天 |
| AWS 集成 | 包括与 MSK 的原生 Lambda 和 Firehose 集成，以及 connectors | 原生 Lambda、Firehose 和 Managed Service for Apache Flink 集成 |

“Kafka 只能通过 Connect 与 AWS 集成”是不正确的。另外，应使用当前名称
**Amazon Managed Service for Apache Flink**，而不是 Kinesis Data Analytics。
桥接时，Kinesis sink 将 Kafka 记录写入 Kinesis，而 source 则反向传输。应选择
与所选运行时兼容且仍在维护的插件，并测试顺序、分区键行为、记录大小限制
和重复处理。协议差异并不能指定一种通用的桥接产品。

## 选择方案

从所需的 Kafka API、数据速率和偏斜、分区/保留限制、延迟、恢复目标、
合规性、团队运维能力和总成本入手。验证当前区域和 broker 版本的支持情况。
MSK 和 Strimzi 都可以使用 IaC/GitOps。之后更换服务需要明确迁移数据、schema、
身份和 consumer offset；这并不会自动成为一个简单或常见的下一步。

## 参考资料和验证

可以在本地检查 policy 生成、Java 类/JAAS 配置、插件字节码和 CLI 请求格式。
这些检查无法证明有效的 IAM 授权、工作负载凭证刷新、broker 访问、托管
connector 部署或数据传递能力。

- [MSK Express broker](https://docs.aws.amazon.com/msk/latest/developerguide/msk-broker-types-express.html)
- [MSK Serverless](https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html)
- [Serverless 配置](https://docs.aws.amazon.com/msk/latest/developerguide/serverless-config.html)
- [MSK 定价维度](https://aws.amazon.com/msk/pricing/)
- [MSK 多 VPC 私有连接](https://docs.aws.amazon.com/msk/latest/developerguide/aws-access-mult-vpc.html)
- [MSK 端口信息](https://docs.aws.amazon.com/msk/latest/developerguide/port-info.html)
- [IAM 客户端机制和官方语言 helper](https://docs.aws.amazon.com/msk/latest/developerguide/configure-clients-for-iam-access-control.html)
- [MSK IAM 操作/资源依赖关系](https://docs.aws.amazon.com/msk/latest/developerguide/kafka-actions.html)
- [IAM 使用案例](https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control-use-cases.html)
- [aws-msk-iam-auth 2.3.9](https://github.com/aws/aws-msk-iam-auth/tree/v2.3.9)
- [MSK Connect](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect.html)
- [MSK Connect 插件打包和 Java 版本](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect-plugins.html)
- [MSK Connect 客户端身份验证 API](https://docs.aws.amazon.com/MSKC/latest/mskc/API_KafkaClusterClientAuthentication.html)
- [将 Lambda 与 MSK 配合使用](https://docs.aws.amazon.com/lambda/latest/dg/with-msk.html)
- [将 Firehose 与 MSK 配合使用](https://docs.aws.amazon.com/msk/latest/developerguide/integrations-kinesis-data-firehose.html)
- [Kinesis 容量模式](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html)
- [Kinesis 保留期限](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)

## 后续步骤

[第 7 部分：监控](./07-monitoring.md)

[返回主页](./README.md)

## 测验

[主题测验](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
