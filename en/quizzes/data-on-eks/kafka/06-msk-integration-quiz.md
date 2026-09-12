# MSK Integration Quiz

Review MSK variants, IAM/networking, MSK Connect and Kinesis comparisons.

## 1. How do MSK and Strimzi on EKS differ, and which responsibilities remain?

<details>
<summary>Show answer</summary>

MSK runs brokers on AWS-managed infrastructure outside EKS; Strimzi runs them in your Kubernetes environment. Application, topic/retention, access-control and recovery design remain necessary.

</details>

## 2. Which MSK Serverless billing items are easy to miss when considering only throughput?

<details>
<summary>Show answer</summary>

Cluster hours, partition hours and used storage, in addition to data-in/out and applicable networking. Autoscaling still has service quotas and is not always cheapest.

</details>

## 3. What authentication path does an EKS pod need for MSK IAM access?

<details>
<summary>Show answer</summary>

A role/trust setup such as Pod Identity or IRSA, temporary-credential loading/refresh, a supported Kafka helper, network/TLS and data-plane permissions. External Secrets Operator or an inherited node role is not a substitute.

</details>

## 4. Are peering and Transit Gateway the only ways to reach MSK from another VPC?

<details>
<summary>Show answer</summary>

No. Supported MSK multi-VPC private connectivity uses PrivateLink. Check same-Region, authentication and AZ/subnet requirements and the actual endpoints. Public access is not mandatory.

</details>

## 5. Does sharing a VPC and having an IAM policy guarantee connectivity?

<details>
<summary>Show answer</summary>

No. Check DNS, routes, SGs, NACLs, egress, actual source identity and every advertised broker address. IAM authentication cannot succeed before TCP/TLS connectivity; inspect existing SG rules too.

</details>

## 6. Can MSK Connect immediately use every network-reachable Strimzi listener?

<details>
<summary>Show answer</summary>

No. The current cluster-authentication API offers NONE/IAM, and broker trust, authentication and worker settings must match. Do not assume the preceding TLS/SCRAM listener works by merely supplying its address.

</details>

## 7. Does changing Kafka bootstrap.servers to a Kinesis endpoint make the client compatible?

<details>
<summary>Show answer</summary>

No. Kinesis Data Streams uses its own APIs. A connector or stream-processing layer must bridge keys, records, retries and checkpoints.

</details>

## 8. Does Kafka integrate with Lambda and Firehose only through Connect?

<details>
<summary>Show answer</summary>

No. MSK also has native Lambda and Firehose integrations. Bridging Kafka and Kinesis is a separate task requiring runtime, format, ordering and duplicate-handling validation.

</details>

## 9. Must you choose Strimzi instead of MSK to use GitOps?

<details>
<summary>Show answer</summary>

No. MSK APIs/IaC can be integrated into GitOps. Evaluate Strimzi for required configuration, portability and operational capability, including storage, network and identity dependencies.

</details>

## 10. How does MSK Express differ from Serverless?

<details>
<summary>Show answer</summary>

Express is a Provisioned broker type with selected broker compute and automatically scaling pay-as-used storage. Check its three-AZ and feature requirements. Compare broker-hour, data-in, storage and other applicable costs.

</details>

## 11. Which MSK IAM SASL mechanisms are available to Java and non-Java clients?

<details>
<summary>Show answer</summary>

Java can use AWS_MSK_IAM or OAUTHBEARER. Python, JavaScript, Go and .NET use OAUTHBEARER with official AWS signers/helpers. Do not configure AWS_MSK_IAM indiscriminately across languages.

</details>

## 12. Does adding aws-msk-iam-auth alone complete IAM authentication?

<details>
<summary>Show answer</summary>

No. The Java helper implements the configured mechanism. Working role credentials/refresh, trust, data permissions, networking and TLS are also required. Non-Java clients use the appropriate official language helper.

</details>

## 13. What matters for MSK Connect runtime versions and plugin updates?

<details>
<summary>Show answer</summary>

Documented combinations are Connect 2.7.1/Java 11 and 3.7.x/Java 17. These differ from broker versions; validate dependencies/APIs as well as bytecode. Plugins copy S3 content at creation, so overwriting the object does not update them.

</details>

## 14. Compare increasing Kafka partition count with Kinesis capacity modes.

<details>
<summary>Show answer</summary>

Increasing Kafka partitions does not redistribute old records or allow an in-place decrease. Kinesis uses shards and distinguishes Provisioned, On-demand Standard and On-demand Advantage modes.

</details>

## 15. Why is seven days alone an incomplete description of default Serverless retention?

<details>
<summary>Show answer</summary>

Default retention.bytes is 250 GiB per partition, so the size limit can be reached first. Check time, size, cleanup policy and service constraints together. Kinesis Data Streams defaults to 24 hours and supports up to 365 days.

</details>

## 16. Write the SG command for same-VPC private IPv4 IAM access and explain its scope.

<details>
<summary>Show answer</summary>

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

Use the actual node/pod source SG and inspect existing rules. IPv6, public and multi-VPC endpoints can use different ports; inspect the bootstrap response. This command changes the SG.

</details>

## 17. Which permissions belong in the orders producer and orders-consumer policies?

<details>
<summary>Show answer</summary>

Use policies.py to derive policies from the exact cluster ARN/UUID. The producer uses cluster Connect/WriteDataIdempotently and orders DescribeTopic/WriteData. The consumer uses cluster Connect, orders DescribeTopic/ReadData and its group's DescribeGroup/AlterGroup. AlterCluster and *Topic* are unnecessary. Design scoped transactional-ID permissions separately for transactions.

</details>

## 18. Write the Java AWS_MSK_IAM properties and explain what remains necessary.

<details>
<summary>Show answer</summary>

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

Add the selected bootstrap.servers, serializers/deserializers and consumer group.id. JVM CA trust, workload credentials, IAM permissions and networking are required. Keep hostname verification enabled.

</details>

---

[Return to learning material](../../../data-on-eks/kafka/06-msk-integration.md) | [Next quiz](./07-monitoring-quiz.md)
