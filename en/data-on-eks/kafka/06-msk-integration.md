# Part 6: MSK Integration

> **Supported Versions**: Amazon MSK (Provisioned & Serverless), MSK Connect\
> **Last Updated**: July 9, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* AWS CLI v2 (for managing the MSK cluster and IAM policies)
* kubectl v1.28 or later, a working EKS cluster
* The `aws-msk-iam-auth` client library (for Kafka clients using IAM authentication)
* An EKS cluster with External Secrets Operator or IRSA configured (for credential injection)

Earlier parts covered running Kafka yourself on EKS with Strimzi. This part covers connecting EKS workloads to Amazon MSK — AWS's fully managed Kafka service — and the trade-offs against the self-managed Strimzi approach. It also clears up a common point of confusion: how Kafka relates to Kinesis Data Streams, a completely separate AWS streaming service.

## Amazon MSK vs. Self-Managed Strimzi

Both approaches get an EKS workload talking to Kafka, but they differ in where the brokers actually run and who operates them. MSK runs brokers on AWS-managed infrastructure outside your cluster; Strimzi runs brokers as Pods inside your EKS cluster.

| Aspect | Amazon MSK (Provisioned) | Amazon MSK Serverless | Strimzi (self-managed on EKS) |
| --- | --- | --- | --- |
| **Operational burden** | AWS handles broker patching, hardware replacement, and storage expansion | AWS removes broker sizing entirely (fully auto-scaling) | The Operator automates rolling upgrades/reconciliation, but you still own upgrade timing, capacity planning, and incident response |
| **Cost model** | Per-broker-hour + storage (GB-month) + data transfer | Throughput-based (per partition, per GB in/out) | Direct EC2/EBS cost — usually cheaper at scale, but you carry the operational headcount cost separately |
| **Autoscaling** | Storage auto-expansion supported; broker scaling is manual/API-driven | Fully automatic per-partition scaling; brokers aren't exposed as a concept | Semi-automated via tools like Cruise Control, but you generally trigger it |
| **Custom configuration** | Broker configuration (`server.properties`) can be customized | No custom broker config; some APIs/features are restricted (e.g., certain ACL types, connector types) | Nearly everything is tunable — listeners, interceptors, KRaft controller settings |
| **Version support** | AWS curates a supported Kafka version list, which can lag upstream | Fixed version, no version choice | Adopt any Kafka version Strimzi supports, whenever upstream ships it |
| **Multi-tenancy** | Isolation via cluster/resource policies; fine-grained customization is limited | Tenant isolation is delegated to AWS's internal implementation | Fine-grained tenancy via namespaces, `KafkaUser` ACLs, and custom listeners |
| **Observability/GitOps fit** | Integrates via CloudWatch/Prometheus exporters; AWS console is the primary management surface | Same | Fits naturally into the same GitOps/observability pipeline (Argo CD, Prometheus Operator) as the rest of the platform |

### Why choose MSK

* Your team lacks deep Kafka broker operations expertise, or you don't want Kafka operations to be a core competency
* You're already heavily invested in AWS-native operations tooling (console, IAM, CloudWatch)
* Traffic is hard to predict, and MSK Serverless lets you eliminate broker capacity planning altogether

### Why run Kafka yourself on EKS with Strimzi anyway (even though MSK exists)

* You want to manage Kafka with the **same tools and same deployment pipeline** as the rest of your platform — other workloads, GitOps, Prometheus/Grafana — without adding a second AWS console/IAM surface to operate
* You need **portability** that isn't tied to a single cloud (on-prem, multi-cloud migration potential)
* At very large scale, managing EC2/EBS directly is more cost-efficient than per-broker-hour pricing
* You need the latest Kafka features (new KIPs, custom interceptors, specific KRaft tuning options) that MSK hasn't caught up to yet

## Connecting to MSK from EKS

For an EKS workload to reach MSK brokers, you need both a network path and an authentication mechanism.

### Network path

* **Same VPC**: If the EKS cluster and the MSK cluster live in the same VPC, subnet routing alone gets you connectivity — simplest and lowest latency.
* **Different VPC**: You'll need VPC peering or an AWS Transit Gateway to connect the two VPCs. MSK does support public access (public broker endpoints), but production setups typically favor private connectivity.
* **Security groups**: The MSK cluster's security group must explicitly allow inbound traffic from the EKS node (or pod, if pods have their own security groups) security group on the relevant broker ports — plaintext 9092, TLS 9094, SASL/SCRAM 9096, IAM 9098. Nothing is allowed by default.

```bash
# Allow the IAM auth port on the MSK security group from the EKS node security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

### Comparing authentication mechanisms

| Mechanism | How it works | EKS integration point |
| --- | --- | --- |
| **IAM authentication (`AWS_MSK_IAM`)** | The client authenticates with a SigV4-signed request using `AWS_MSK_IAM`, a dedicated custom SASL mechanism (not an OAUTHBEARER extension); IAM policies control per-topic permissions | Grant the pod an IAM role via IRSA — no credentials to distribute at all |
| **SASL/SCRAM** | Username/password based; credentials stored in AWS Secrets Manager | Sync SCRAM credentials from Secrets Manager into a Kubernetes Secret via External Secrets Operator |
| **Mutual TLS (mTLS)** | Client certificates issued by AWS Private CA; identity verified via certificate | Mount certificates/keys into pods via cert-manager or External Secrets Operator |

IAM authentication is the most natural fit for EKS. With IRSA (IAM Roles for Service Accounts), you grant a pod a scoped IAM role and express topic-level access control purely through IAM policy — no passwords or certificates to distribute or rotate.

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

On the client side, add the `aws-msk-iam-auth` library to your classpath (or the equivalent package for your language), then configure the Kafka client with:

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

## MSK Connect

MSK Connect is AWS's fully managed Kafka Connect offering. AWS handles provisioning, scaling, and patching the Connect worker infrastructure; you register connector plugins (JAR bundles) by uploading them to S3.

The important detail: MSK Connect is **not limited to MSK clusters**. As long as it has network reachability to the bootstrap brokers, MSK Connect can also run connectors against a self-managed Kafka cluster running on EKS via Strimzi.

```bash
# Upload a custom connector plugin to S3 and register it as an MSK Connect custom plugin
aws kafkaconnect create-custom-plugin \
  --name debezium-postgres-plugin \
  --content-type ZIP \
  --location s3Location='{bucketArn=arn:aws:s3:::my-connect-plugins,fileKey=debezium-postgres-2.7.zip}'
```

| Aspect | MSK Connect | Strimzi `KafkaConnect` (self-operated on EKS) |
| --- | --- | --- |
| **Operational burden** | AWS manages worker infrastructure; you only manage connector configuration | You manage worker pod scaling, monitoring, and resource tuning yourself |
| **Flexibility** | Limited to the connector framework AWS supports | Full freedom for arbitrary connectors, custom SMTs (Single Message Transforms), sidecars |
| **Portability** | AWS-only service, hard to move elsewhere | Portable as-is to any other Kubernetes cluster |
| **Observability** | Connector status via CloudWatch Logs/Metrics | Integrates into the same Prometheus/Grafana pipeline as the rest of your EKS workloads |

## Comparing and Bridging with Kinesis Data Streams

Kinesis Data Streams and Kafka are often mentioned in the same breath, but they are **not compatible protocols**. Kinesis is an AWS-native streaming service with its own API/SDK, and it has no understanding of Kafka's producer/consumer protocol. The fact that MSK is described as "Kafka-compatible" does not mean it interoperates with Kinesis — MSK is a managed implementation of the Apache Kafka protocol, and Kinesis is an entirely separate service.

| Aspect | Apache Kafka (MSK/Strimzi) | Kinesis Data Streams |
| --- | --- | --- |
| **Protocol** | Open-source Kafka protocol, compatible with a broad client/tooling ecosystem | AWS-proprietary API, not compatible with Kafka clients |
| **Scaling unit** | Partitions (defined at topic creation, can be repartitioned) | Shards (read/write capacity units, adjusted via split/merge) |
| **Operational complexity** | Requires operating brokers/controllers (MSK offloads this to AWS) | Fully managed, no server concept at all |
| **AWS service integration** | Indirect, via connectors (Kafka Connect, MSK Connect) | Native, direct integration with Lambda triggers, Firehose, Kinesis Data Analytics |
| **Ecosystem** | Broad open-source ecosystem: Kafka Streams, ksqlDB, Flink, Debezium | Smaller, AWS-service-centric ecosystem, but simpler to integrate |
| **Retention** | Effectively unlimited (pay for storage only; default 7 days) | Default 24 hours, extendable up to 365 days (at increasing cost) |

### The real bridging pattern

If you need to actually connect Kafka and Kinesis — for migration, or to bridge with legacy Kinesis consumers — the practical pattern is a **Kinesis connector running under Kafka Connect (or MSK Connect)**, not any built-in protocol compatibility.

* **Kinesis Sink connector**: reads messages from a Kafka topic and writes them to a Kinesis stream — useful for feeding a Kafka-based pipeline's output into the Kinesis consumption ecosystem (Lambda, Firehose)
* **Kinesis Source connector**: reads records from a Kinesis stream and writes them to a Kafka topic — useful for keeping existing Kinesis producers in place while incrementally migrating consumers to Kafka

These connectors can be deployed on MSK Connect or run directly on EKS via Strimzi's `KafkaConnect`/`KafkaConnector` CRs — the same MSK Connect vs. Strimzi trade-offs from the previous section apply here too.

## Decision Guide

Use this checklist to narrow down between self-managed Strimzi, MSK Provisioned, MSK Serverless, and Kinesis.

* **Does your team have Kafka operations expertise and need fine-grained tuning/custom configuration?** → Yes: Strimzi (self-managed on EKS) / No: consider MSK
* **Is multi-cloud/on-prem portability a hard requirement?** → Yes: Strimzi / No: MSK is worth evaluating
* **Is traffic unpredictable or spiky, and do you want to eliminate broker capacity planning entirely?** → Yes: MSK Serverless / No: MSK Provisioned or Strimzi
* **Are you already deeply invested in AWS-native event processing (Lambda, Firehose) and don't need the Kafka ecosystem (Kafka Streams, ksqlDB, etc.)?** → Yes: evaluate Kinesis Data Streams / No: stick with Kafka (MSK/Strimzi)
* **Do you want to manage Kafka through the same GitOps pipeline as the rest of your EKS platform, without adding an AWS console/IAM surface?** → Yes: Strimzi / No: MSK

In practice the answer is often "both" — starting a new service on MSK Serverless for speed, then migrating to Strimzi once you need custom tuning, is a common trajectory.

## Next Steps

Whether you run MSK or Strimzi, you need continuous visibility into broker metrics and consumer lag to know the cluster is healthy. That's the subject of [Part 7: Monitoring](./07-monitoring.md).

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md).
