# MSK Integration Quiz

This quiz tests your understanding of the trade-offs between Amazon MSK and self-managed Strimzi, how to connect EKS workloads to MSK, MSK Connect, and the differences between Kafka and Kinesis Data Streams.

## Multiple Choice Questions

1. What is the most fundamental difference between Amazon MSK and self-managed Strimzi on EKS?
   - A) MSK doesn't use the Kafka protocol
   - B) Where the brokers actually run and who is responsible for operating them
   - C) Strimzi cannot run on Kubernetes
   - D) MSK doesn't support the concept of partitions

<details>

<summary>Show Answer</summary>

**Answer: B) Where the brokers actually run and who is responsible for operating them**

**Explanation:**
MSK runs brokers on AWS-managed infrastructure, and AWS handles patching, hardware replacement, and storage expansion on your behalf. Strimzi runs brokers as Pods inside your EKS cluster; even though the Operator automates rolling upgrades and reconciliation, you still own decisions like upgrade timing, capacity planning, and incident response. Both implement the same Apache Kafka protocol, so there's no protocol-level difference.
</details>

2. Which statement correctly describes MSK Serverless?
   - A) Broker configuration (`server.properties`) can be freely customized
   - B) Broker sizing is not exposed to the user, and billing is throughput-based
   - C) It only works with ZooKeeper-based clusters
   - D) It is always cheaper than MSK Provisioned

<details>

<summary>Show Answer</summary>

**Answer: B) Broker sizing is not exposed to the user, and billing is throughput-based**

**Explanation:**
MSK Serverless auto-scales per partition, and users never think about broker count or instance types. Instead, it's billed based on throughput — per partition, per GB in/out. Custom broker configuration isn't supported, and some APIs/features (certain ACL types, connector types) are restricted. Whether it's cheaper than Provisioned depends on your traffic pattern, so it can't be assumed to always be cheaper.
</details>

3. What combination lets an EKS pod authenticate to an MSK broker without distributing any separate IAM credentials?
   - A) SASL/SCRAM with Secrets Manager
   - B) IRSA with the `AWS_MSK_IAM` SASL mechanism
   - C) mTLS with AWS Private CA
   - D) A plaintext listener with security groups alone

<details>

<summary>Show Answer</summary>

**Answer: B) IRSA with the `AWS_MSK_IAM` SASL mechanism**

**Explanation:**
IRSA (IAM Roles for Service Accounts) grants a pod an IAM role, and setting `sasl.mechanism=AWS_MSK_IAM` on the Kafka client makes it authenticate using SigV4-signed requests. The key advantage is that there are no separate credentials — passwords, certificates — to distribute or rotate. SASL/SCRAM and mTLS are also valid authentication methods, but they require syncing credentials from Secrets Manager or issuing/mounting certificates, respectively.
</details>

4. What network configuration is required for an EKS workload to reach an MSK cluster in a different VPC?
   - A) MSK must always be switched to public access
   - B) VPC peering or an AWS Transit Gateway must connect the two VPCs
   - C) The Kafka protocol automatically crosses VPC boundaries
   - D) A NAT gateway alone is sufficient, no further configuration needed

<details>

<summary>Show Answer</summary>

**Answer: B) VPC peering or an AWS Transit Gateway must connect the two VPCs**

**Explanation:**
If the EKS cluster and the MSK cluster live in different VPCs, you need VPC peering or a Transit Gateway to establish routing between them. MSK does support public access, but that's an optional, separate configuration, and production environments generally favor private connectivity for security reasons. Even with a network path in place, connectivity is still blocked if the MSK cluster's security group doesn't allow inbound traffic from the EKS node/pod security group.
</details>

5. Which statement about MSK cluster security group configuration is correct?
   - A) All traffic within the same VPC is allowed by default
   - B) Inbound traffic to broker ports must be explicitly allowed from the EKS node (or pod) security group
   - C) Security groups aren't needed when using IAM authentication
   - D) Security group configuration only applies to MSK Serverless

<details>

<summary>Show Answer</summary>

**Answer: B) Inbound traffic to broker ports must be explicitly allowed from the EKS node (or pod) security group**

**Explanation:**
An MSK cluster's security group allows no inbound traffic by default. You must explicitly add an inbound rule permitting the EKS worker node (or pod, if using per-pod security groups) security group as the source for the relevant broker ports — plaintext 9092, TLS 9094, SASL/SCRAM 9096, IAM 9098. This network-layer security group rule is needed regardless of which authentication mechanism (IAM, SCRAM, mTLS) you use.
</details>

6. Which statement about MSK Connect is correct?
   - A) It can only connect to MSK clusters, not to other Kafka clusters
   - B) As long as it has network reachability to the bootstrap brokers, it can also run connectors against a Strimzi cluster on EKS
   - C) Users must manage the scaling and patching of the Connect workers themselves
   - D) Connector plugins can only be registered as container images

<details>

<summary>Show Answer</summary>

**Answer: B) As long as it has network reachability to the bootstrap brokers, it can also run connectors against a Strimzi cluster on EKS**

**Explanation:**
MSK Connect is not restricted to MSK clusters. As long as a connector can reach the bootstrap brokers over the network, it can be pointed at any Kafka cluster, including a self-managed Strimzi cluster on EKS. AWS manages provisioning, scaling, and patching of the Connect worker infrastructure, so users don't manage that themselves. Custom connector plugins are registered by uploading a ZIP of JARs to S3.
</details>

7. Which statement correctly describes the relationship between Kafka and Kinesis Data Streams?
   - A) Because MSK is "Kafka-compatible," a Kinesis client can connect directly to MSK
   - B) Kafka and Kinesis are separate services using different protocols and are not directly compatible
   - C) Kinesis internally implements the Kafka protocol as-is
   - D) A Kafka client can connect directly to a Kinesis stream just by changing configuration

<details>

<summary>Show Answer</summary>

**Answer: B) Kafka and Kinesis are separate services using different protocols and are not directly compatible**

**Explanation:**
Kinesis Data Streams is an entirely separate service with its own AWS-proprietary API/SDK; it has no understanding of the Kafka producer/consumer protocol. When MSK is described as "Kafka-compatible," that only means it implements the Apache Kafka protocol — it does not imply interoperability with Kinesis. Bridging the two requires a separate layer, such as Kinesis sink/source connectors running under Kafka Connect (or MSK Connect).
</details>

8. What is the correct way to actually bridge Kafka and Kinesis Data Streams?
   - A) Point the Kafka client's `bootstrap.servers` at the Kinesis endpoint
   - B) Use a Kinesis sink/source connector under Kafka Connect or MSK Connect
   - C) Use a configuration flag that switches an MSK cluster into "Kinesis mode"
   - D) They can reference each other directly since they share the same partition model

<details>

<summary>Show Answer</summary>

**Answer: B) Use a Kinesis sink/source connector under Kafka Connect or MSK Connect**

**Explanation:**
Because Kafka and Kinesis are protocol-incompatible, bridging them requires a connector to do the translation. A Kinesis sink connector reads messages from a Kafka topic and writes them to a Kinesis stream; a Kinesis source connector reads records from a Kinesis stream and writes them to a Kafka topic. These connectors can be deployed on MSK Connect or run directly on EKS via Strimzi's `KafkaConnect`/`KafkaConnector` CRs.
</details>

9. Which of the following is NOT a valid reason to keep running Kafka yourself on EKS with Strimzi even though MSK exists?
   - A) You want Kafka to fit into the same GitOps/observability pipeline as the rest of the platform
   - B) You need portability to on-prem or multi-cloud environments
   - C) You need a recent Kafka feature that MSK doesn't support yet
   - D) You don't want to have any broker operations staff at all

<details>

<summary>Show Answer</summary>

**Answer: D) You don't want to have any broker operations staff at all**

**Explanation:**
Self-managed Strimzi automates a lot through the Operator, but decisions like upgrade timing, capacity planning, and incident response remain your responsibility. If you want to eliminate broker operations burden entirely, MSK — especially MSK Serverless — is actually the better fit. GitOps integration, portability, and access to the newest Kafka features are all legitimate reasons to run Strimzi on EKS instead.
</details>

10. Which statement most accurately describes the cost model difference between MSK Provisioned and self-managed Strimzi?
    - A) MSK is always cheaper than Strimzi
    - B) MSK bills per broker-hour plus storage, while Strimzi incurs direct EC2/EBS cost plus separate operational staffing cost
    - C) Strimzi has no billing model and is completely free
    - D) The two cost models are identical

<details>

<summary>Show Answer</summary>

**Answer: B) MSK bills per broker-hour plus storage, while Strimzi incurs direct EC2/EBS cost plus separate operational staffing cost**

**Explanation:**
MSK Provisioned bills based on per-broker-hour pricing, storage (GB-month), and data transfer. Strimzi has you pay for EC2/EBS infrastructure directly — usually cheaper at scale — but the cost of the staff who operate it is a separate, additional consideration. Which option wins on total cost of ownership depends on traffic volume, your organization's operational capability, and labor costs.
</details>

## Short Answer Questions

11. What is the exact name of the SASL mechanism an EKS pod uses to authenticate to MSK using an IAM role?

<details>

<summary>Show Answer</summary>

**Answer: `AWS_MSK_IAM`**

**Explanation:**
`AWS_MSK_IAM` is the SASL mechanism MSK provides that lets clients authenticate using SigV4-signed credentials (an IAM role or user). In client configuration, you set `security.protocol=SASL_SSL` and `sasl.mechanism=AWS_MSK_IAM`, and register the `IAMLoginModule` and `IAMClientCallbackHandler` from the `aws-msk-iam-auth` library as the JAAS login module and callback handler.
</details>

12. What is the name of the library an MSK client must add to its classpath (or the equivalent package manager for its language) to use IAM authentication?

<details>

<summary>Show Answer</summary>

**Answer: `aws-msk-iam-auth`**

**Explanation:**
`aws-msk-iam-auth` is a client library provided by AWS that implements `AWS_MSK_IAM`, a dedicated custom SASL mechanism (not an OAUTHBEARER extension), letting Kafka clients generate SigV4-signed requests and authenticate to MSK brokers with IAM credentials. The Java client is distributed as a Maven artifact, and equivalent community implementations exist for other languages (Python, Go, etc.).
</details>

13. What is the name of AWS's fully managed Kafka Connect service, where AWS handles provisioning and scaling of connector workers?

<details>

<summary>Show Answer</summary>

**Answer: MSK Connect**

**Explanation:**
MSK Connect is the service where AWS manages provisioning, scaling, and patching of the Kafka Connect worker cluster. Users simply upload connector plugins (a ZIP of JARs) to S3 and register connector configuration. It can connect not just to MSK clusters but to any network-reachable Kafka cluster, including a Strimzi cluster on EKS.
</details>

14. What is the Kinesis Data Streams scaling unit that corresponds to Kafka's "partition"?

<details>

<summary>Show Answer</summary>

**Answer: Shard**

**Explanation:**
Kafka splits a topic into multiple partitions for parallelism and scalability; the partition count is defined at topic creation and can later be adjusted via repartitioning. Kinesis instead divides read/write capacity into shards, and capacity is adjusted through shard split and merge operations. The two concepts serve a similar purpose but differ in API and operational mechanics.
</details>

15. What type of Kafka Connect connector reads messages from a Kafka topic and writes them to a Kinesis stream?

<details>

<summary>Show Answer</summary>

**Answer: Kinesis Sink connector**

**Explanation:**
A Kinesis Sink connector treats a Kafka topic as its source, reading messages and writing them to a Kinesis stream. Conversely, a Kinesis Source connector reads records from a Kinesis stream and writes them to a Kafka topic. Both connectors exist specifically because Kafka and Kinesis have no protocol compatibility — they are the layer that actually bridges data between the two.
</details>

## Hands-on Questions

16. Write the AWS CLI command that allows inbound traffic from the EKS worker node security group (`sg-0efgh5678eksnode`) to the IAM authentication port on the MSK cluster security group (`sg-0abcd1234msk`).

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

**Explanation:**
MSK's IAM authentication port is 9098. In `authorize-security-group-ingress`, `--group-id` specifies the target security group to add the rule to (the MSK security group), and `--source-group` specifies the allowed traffic source (the EKS node security group). Without this rule, even a successful IAM authentication attempt would be blocked at the TCP connection stage. If using a different auth mechanism, adjust the port accordingly (TLS: 9094, SASL/SCRAM: 9096).
</details>

17. Write an IAM policy JSON that grants a Kafka client using IAM authentication read/write access to only the `orders` topic on a specific MSK cluster.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
The first statement grants the minimum permissions to connect to the cluster and describe its state (`Connect`, `DescribeCluster`). The second statement scopes the resource ARN to `topic/my-msk-cluster/*/orders`, granting topic-related actions, write (`WriteData`), and read (`ReadData`) permissions only for the `orders` topic. Scoping the resource ARN this tightly means the client cannot access any other topic on the same cluster.
</details>

18. Write a Kafka client configuration (properties) file that configures the client to use the `AWS_MSK_IAM` mechanism.

<details>

<summary>Show Answer</summary>

**Answer:**
```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

**Explanation:**
`security.protocol=SASL_SSL` specifies using SASL authentication together with TLS encryption. `sasl.mechanism=AWS_MSK_IAM` selects the IAM-based SASL mechanism. `sasl.jaas.config` registers the `IAMLoginModule` from the `aws-msk-iam-auth` library as the JAAS login module, and `sasl.client.callback.handler.class` specifies the callback handler that generates the SigV4-signed request. With just this configuration, the client authenticates automatically using its local credential chain, including an IAM role injected via IRSA.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/06-msk-integration.md) | [Next Quiz: Monitoring](./07-monitoring-quiz.md)
