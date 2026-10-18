# MSK 集成测验

复习 MSK 的不同类型、IAM 与网络、MSK Connect，以及与 Kinesis 的比较。

## 1. MSK 与在 EKS 上运行的 Strimzi 有何不同？哪些职责仍由你承担？

<details>
<summary>显示答案</summary>

MSK 在 EKS 之外的 AWS 托管基础设施上运行 broker；Strimzi 则在你的 Kubernetes 环境中运行 broker。应用、topic 与保留策略、访问控制和恢复方案仍需你设计。

</details>

## 2. 只考虑吞吐量时，MSK Serverless 哪些费用容易被忽略？

<details>
<summary>显示答案</summary>

除数据流入/流出费用以及适用的网络费用外，还要考虑集群运行时长、partition 运行时长和已用存储。自动扩缩容仍受服务配额限制，而且它并非总是最便宜的选择。

</details>

## 3. EKS Pod 通过 IAM 访问 MSK 需要什么身份验证路径？

<details>
<summary>显示答案</summary>

需要配置角色及其信任关系，例如 Pod Identity 或 IRSA；还需要能够加载并刷新临时凭证的机制、受支持的 Kafka helper、网络与 TLS，以及数据平面权限。External Secrets Operator 或继承的节点角色不能替代这些要求。

</details>

## 4. 从另一个 VPC 访问 MSK 时，除了 VPC 对等连接和 Transit Gateway，还有其他方式吗？

<details>
<summary>显示答案</summary>

有。受支持的 MSK 多 VPC 私有连接使用 PrivateLink。请核实同一区域、身份验证方式以及可用区/子网要求，并检查实际端点。无需强制启用公有访问。

</details>

## 5. 共享 VPC 并配置 IAM policy 就能保证连通吗？

<details>
<summary>显示答案</summary>

不能。要检查 DNS、路由、安全组、网络 ACL、出站流量、实际源身份以及所有 broker 广告的地址。在建立 TCP/TLS 连接之前，IAM 身份验证无法成功；也要检查已有的安全组规则。

</details>

## 6. MSK Connect 能立即使用 Strimzi 的所有网络可达 listener 吗？

<details>
<summary>显示答案</summary>

不能。当前集群身份验证 API 提供 NONE 和 IAM。broker 信任配置、身份验证方式与 worker 设置必须匹配。不能假设只要提供地址，前面提到的 TLS/SCRAM listener 就能使用。

</details>

## 7. 把 `bootstrap.servers` 改成 Kinesis 端点，Kafka client 就能兼容吗？

<details>
<summary>显示答案</summary>

不能。Kinesis Data Streams 使用自己的 API。需要 connector 或流处理层来桥接 key、record、重试和检查点。

</details>

## 8. Kafka 是否只能通过 Connect 与 Lambda 和 Firehose 集成？

<details>
<summary>显示答案</summary>

不是。MSK 也提供原生的 Lambda 和 Firehose 集成。桥接 Kafka 与 Kinesis 是另一项工作，需要验证运行时、格式、顺序和重复处理方式。

</details>

## 9. 使用 GitOps 是否必须选择 Strimzi 而不是 MSK？

<details>
<summary>显示答案</summary>

不必。可以把 MSK API/IaC 集成到 GitOps 中。评估 Strimzi 时，应考虑所需配置、可移植性和运维能力，以及存储、网络和身份依赖。

</details>

## 10. MSK Express 与 Serverless 有何不同？

<details>
<summary>显示答案</summary>

Express 是一种预置 broker 类型：你选择 broker 计算规格，存储按实际使用量计费并自动扩展。请检查其三可用区要求和功能要求，并比较 broker 小时、数据流入、存储及其他适用费用。

</details>

## 11. Java 和非 Java client 可使用哪些 MSK IAM SASL 机制？

<details>
<summary>显示答案</summary>

Java 可使用 `AWS_MSK_IAM` 或 `OAUTHBEARER`。Python、JavaScript、Go 和 .NET 使用 `OAUTHBEARER` 搭配 AWS 官方 signer/helper。不要不加区分地为所有语言配置 `AWS_MSK_IAM`。

</details>

## 12. 只添加 `aws-msk-iam-auth` 就完成 IAM 身份验证了吗？

<details>
<summary>显示答案</summary>

没有。Java helper 实现所配置的机制；此外还需要可用的角色凭证及其刷新、信任关系、数据权限、网络和 TLS。非 Java client 应使用对应语言的官方 helper。

</details>

## 13. MSK Connect 运行时版本和 plugin 更新有哪些注意事项？

<details>
<summary>显示答案</summary>

文档列出的组合是 Connect 2.7.1/Java 11 和 3.7.x/Java 17。这些是 Connect 版本，与 broker 版本不同；除了字节码，也要验证依赖和 API。plugin 创建时会复制 S3 内容，因此覆盖对象不会更新已有 plugin。

</details>

## 14. 比较增加 Kafka partition 数量与 Kinesis 容量模式。

<details>
<summary>显示答案</summary>

增加 Kafka partition 数量不会重新分配旧 record，也不能原地减少 partition。Kinesis 使用 shard，并区分 Provisioned、On-demand Standard 和 On-demand Advantage 模式。

</details>

## 15. 为什么仅用“默认保留七天”描述 Serverless 保留策略并不完整？

<details>
<summary>显示答案</summary>

默认的 `retention.bytes` 是每个 partition 250 GiB，因此可能先达到大小上限。请一并检查时间、大小、清理策略和服务限制。Kinesis Data Streams 默认保留 24 小时，最长支持 365 天。

</details>

## 16. 写出同一 VPC 内通过私有 IPv4 使用 IAM 访问的安全组命令，并说明适用范围。

<details>
<summary>显示答案</summary>

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

使用实际的节点/Pod 源安全组，并检查已有规则。IPv6、公有和多 VPC 端点可能使用不同端口；请检查 bootstrap 响应。此命令会修改安全组。

</details>

## 17. `orders` producer policy 和 orders-consumer policy 分别需要哪些权限？

<details>
<summary>显示答案</summary>

使用 `policies.py` 根据准确的集群 ARN/UUID 生成 policy。producer 需要集群级 `Connect`/`WriteDataIdempotently`，以及 `orders` 的 `DescribeTopic`/`WriteData`。consumer 需要集群级 `Connect`、`orders` 的 `DescribeTopic`/`ReadData`，以及其 consumer group 的 `DescribeGroup`/`AlterGroup`。无需 `AlterCluster` 和 `*Topic*`。事务所需的限定 transactional ID 权限应单独设计。

</details>

## 18. 写出使用 Java `AWS_MSK_IAM` 的 properties，并说明还需要什么。

<details>
<summary>显示答案</summary>

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

还要添加选定的 `bootstrap.servers`、serializer/deserializer 和 consumer group `id`。还需要 JVM CA 信任、工作负载凭证、IAM 权限和网络连通性。请保持主机名验证启用。

</details>

---

[返回学习材料](../../../data-on-eks/kafka/06-msk-integration.md) | [下一个测验](./07-monitoring-quiz.md)
