# Part 6: MSK Integration

> **Review baseline**: MSK Standard/Express Provisioned, MSK Serverless, MSK Connect; Java IAM helper 2.3.8\
> **Last reviewed**: September 12, 2026

## Responsibilities and prerequisites

Amazon MSK runs Kafka brokers outside your EKS cluster on AWS-managed infrastructure.
Strimzi runs them as Kubernetes workloads that your team operates. Both require
application, topic, access-control, retention and recovery decisions. A managed
broker does not remove the need to understand Kafka behavior.

Use AWS CLI v2 and kubectl compatible with the EKS cluster. An IAM client needs a
supported authentication helper and a functioning workload credential chain.
EKS Pod Identity or IRSA can supply temporary credentials; External Secrets
Operator is optional for other secret-management workflows, not an IAM prerequisite.

## Compare the actual MSK variants

| Option | Capacity and configuration | Costs to include |
| --- | --- | --- |
| MSK Provisioned Standard | Choose brokers and storage; configure storage autoscaling if needed; only supported broker settings are editable | Broker hours, provisioned storage, optional throughput/tiered storage and network |
| MSK Provisioned Express | Choose broker compute; storage scales automatically and is billed as used; enforced configuration/throughput guardrails | Broker hours, data-in, used storage and applicable network charges |
| MSK Serverless | AWS manages broker capacity; users still plan topics, partitions, retention and service quotas | **Cluster hours**, partition hours, data-in/out, used storage and applicable network charges |
| Strimzi on EKS | Operate nodes, disks, broker/controller topology and supported Operator configuration | EKS/EC2/EBS, networking, spare capacity, observability and operational effort |

Express is a **Provisioned broker type**, not Serverless. Its current documentation
requires three AZs and lists API/feature constraints, including incomplete KStreams
support and no KIP-932 support. Check the supported broker/version combination
instead of assuming every Kafka feature works identically.

Serverless requires IAM authentication/authorization; Kafka ACLs are not supported.
It permits only listed topic settings. For example, retention is configurable,
while `cleanup.policy` can be set only at topic creation. Its default retention
also includes a **250 GiB limit per partition**, not just seven days. More traffic can reach
that size before the time limit. Capacity autoscaling does not make arbitrary
partition counts or burst rates unlimited.

CloudWatch metrics exist for these offerings, but Serverless monitoring is not
the same broker-level Prometheus/open-monitoring interface as Provisioned.
IAM topic/group policies remain your responsibility for Serverless multi-tenancy.
In Strimzi, Kubernetes namespaces alone do not authorize Kafka topic access.

MSK can be managed with APIs and infrastructure as code; GitOps is not exclusive
to Strimzi. Portability of a Strimzi deployment still depends on storage, networking,
identity and supported Operator versions. Compare measured total cost and recovery
requirements; neither “self-managed is always cheaper at scale” nor “Serverless
is cheapest for spikes” is a sound default.

## Network connectivity from EKS

The client must reach **all broker endpoints advertised in metadata**, not just
the bootstrap address. Validate DNS, routes, security groups, NACLs, pod/node source
identity and egress. Sharing a VPC is not sufficient by itself.

For different VPCs, options include routed peering/Transit Gateway and supported
MSK **multi-VPC private connectivity** using PrivateLink. The managed multi-VPC
feature is same-Region and has cluster/authentication/AZ-subnet requirements.
Public endpoints are an explicit supported-cluster option, not a prerequisite
for cross-VPC access.

| Direct endpoint example | Port |
| --- | --- |
| Private IPv4 TLS | 9094 |
| Private IPv4 SASL/SCRAM | 9096 |
| Private IPv4 IAM | 9098 |
| Public TLS / SCRAM / IAM, when supported and enabled | 9194 / 9196 / 9198 |

IPv6 and managed multi-VPC endpoints can use different ports. Retrieve the actual
bootstrap response and select the field for the intended network/authentication
path; do not rewrite every endpoint to 9098.

```bash
: "${DOCS_AWS_REGION:?Set the MSK region}"
: "${DOCS_MSK_CLUSTER_ARN:?Set the exact existing cluster ARN}"
aws kafka get-bootstrap-brokers \
  --region "$DOCS_AWS_REGION" \
  --cluster-arn "$DOCS_MSK_CLUSTER_ARN"
```

For direct private IPv4 IAM access in the same VPC, a network administrator can
apply this narrowly scoped example after checking existing rules:

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

The command **changes** a security group. Use the actual node/pod source SG for the
network path; different-VPC SG references have their own support rules. Existing
SGs may already contain rules, including self-reference rules. IAM authentication
cannot succeed before TCP/TLS connectivity is established.

## IAM authentication and workload identity

| Client | Supported IAM mechanism |
| --- | --- |
| Java | `AWS_MSK_IAM` or `OAUTHBEARER` using the AWS Java helper |
| Python, JavaScript, Go, .NET | `OAUTHBEARER` with the corresponding official AWS signer/helper |

`AWS_MSK_IAM` is not a generic mechanism provided by every language's Kafka client.
The non-Java helpers are official AWS projects, not merely community equivalents.
For Provisioned clusters, SCRAM or mutual TLS may also be available; configure
their supported secret/certificate and Kafka ACL workflow. They are not alternatives
to IAM on Serverless.

Configure the workload role association/trust and temporary-credential refresh
before testing Kafka. Do not assume an inherited node role is the intended pod
identity. Private environments must also reach the identity services required by
their chosen credential provider. Test re-authentication after credentials refresh.
The Java helper documents a session-name consistency issue with some providers,
including Pod Identity; apply its documented workaround if that issue occurs.

### Separate producer and consumer policies

The following script derives exact resource ARNs from the existing cluster ARN.
Save it as `policies.py`; it writes policies locally and does not attach them.
It omits the old `AlterCluster` and `*Topic*` administration grants, includes
consumer-group actions, and distinguishes cluster-scoped idempotent-write permission
from topic-scoped writes.

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

The existing topic is `orders`, and the consumer must use group
`orders-consumer`. Topic creation belongs to a separate administrative identity.
The producer policy covers **non-transactional idempotent** writes using the
documented IAM action set. A transactional producer additionally needs scoped
transactional-ID actions and compatible broker support; IAM supports
`WriteTxnMarkers` on MSK Kafka 3.8 and later. Do not grant every transactional ID
or disable idempotence merely to conceal an authorization error.

Effective access also depends on other attached policies, explicit denies, SCPs,
permission boundaries and cross-account resource policies. These documents are
not a complete authorization boundary by themselves. MSK control-plane actions
such as `kafka:GetBootstrapBrokers` are separate from `kafka-cluster:*` data-plane
actions and can belong to the deployment/operator identity.

### Java client configuration

Add `software.amazon.msk:aws-msk-iam-auth:2.3.8` and its dependencies, or use the
verified release's all-in-one JAR. Save this as `iam.properties`:

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

For Java's OAuth mechanism, use this alternative rather than combining the two:

```properties
security.protocol=SASL_SSL
sasl.mechanism=OAUTHBEARER
sasl.jaas.config=org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required;
sasl.login.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
ssl.endpoint.identification.algorithm=https
```

Add the selected `bootstrap.servers`, key/value serializers or deserializers,
and consumer `group.id` in the application. The JVM must trust the broker's TLS
certificate chain; keep hostname verification enabled. These properties configure
the mechanism but cannot create missing workload credentials or IAM permissions.

## MSK Connect: compatibility before deployment

MSK Connect runs managed Kafka Connect workers and can target an independently
hosted Kafka cluster. **Network reachability alone is insufficient.** The current
`KafkaClusterClientAuthentication` API accepts `NONE` or `IAM`; broker trust,
authentication and supported worker settings must match. The TLS/SCRAM Strimzi
listener from Part 2 is not a drop-in target merely because its hostname resolves.
Do not remove its authentication to force an integration.

The service's documented Connect runtimes are **2.7.1 / Java 11** and
**3.7.x / Java 17**. They are distinct from the Kafka broker version and from the
Kafka 4.3.1 Connect runtime used in Part 5. Check plugin bytecode, dependencies,
Connect APIs and the vendor support matrix. A JAR that loads on Java 17 still needs
integration testing on the selected managed runtime.

The Part 5 artifacts contain no base class above Java 17, but that does **not**
certify MSK Connect compatibility. The following registers the Aiven 3.4.3 ZIP
after that compatibility review. It assumes an existing private S3 bucket in the
target Region and permission to upload/register the plugin.

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

This uploads and registers a **plugin**, not a running connector. Creating the
connector still requires a service execution role, Kafka/network settings, source/
destination permissions, capacity and converter configuration. MSK Connect's default
key/value converters are StringConverter; the CDC example's JSON schema-envelope
settings must be configured deliberately.

MSK Connect copies the S3 object at plugin creation. Overwriting the object does
not update the plugin, and custom plugins cannot be edited in place. Use a new
versioned plugin resource and a tested connector transition plan; preserve and
verify offsets before replacing an active data pipeline. Autoscaling also has
configured limits and does not parallelize a single-task source.

## Kafka and Kinesis Data Streams

Kinesis Data Streams has its own APIs; replacing `bootstrap.servers` with a Kinesis
endpoint does not convert a Kafka client. A connector or explicit stream-processing
bridge must translate records, keys, retry behavior and checkpoints.

| Aspect | Kafka / MSK / Strimzi | Kinesis Data Streams |
| --- | --- | --- |
| Parallelism | Topic partitions; increasing count does not redistribute old records or provide an in-place decrease | Shards; manual sizing in Provisioned or service-managed capacity in on-demand modes |
| Capacity choices | Depend on Standard, Express, Serverless or self-managed deployment | Provisioned, On-demand Standard and On-demand Advantage |
| Retention | Topic/service settings, storage and cleanup policy; time and size limits both matter | Default 24 hours; configurable up to 365 days |
| AWS integrations | Includes native Lambda and Firehose integration with MSK, plus connectors | Native Lambda, Firehose and Managed Service for Apache Flink integrations |

“Kafka only integrates with AWS through Connect” is incorrect. Also use the current
**Amazon Managed Service for Apache Flink** name rather than Kinesis Data Analytics.
For bridging, a Kinesis sink writes Kafka records to Kinesis and a source does the
reverse. Select a maintained plugin compatible with the chosen runtime and test
ordering, partition-key behavior, record-size limits and duplicate handling.
Protocol differences do not prescribe one universal bridging product.

## Choosing an option

Start with required Kafka APIs, data rates and skew, partition/retention limits,
latency, recovery objectives, compliance, team operations and full cost. Verify
current regional and broker-version support. IaC/GitOps can be used with either
MSK or Strimzi. Changing services later requires an explicit data, schema,
identity and consumer-offset migration; it is not automatically a simple or common
next step.

## References and validation

Policy generation, Java class/JAAS configuration, plugin bytecode and CLI request
shapes can be checked locally. Those checks do not prove effective IAM authorization,
workload credential refresh, broker access, a managed connector deployment or delivery.

- [MSK Express brokers](https://docs.aws.amazon.com/msk/latest/developerguide/msk-broker-types-express.html)
- [MSK Serverless](https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html)
- [Serverless configuration](https://docs.aws.amazon.com/msk/latest/developerguide/serverless-config.html)
- [MSK pricing dimensions](https://aws.amazon.com/msk/pricing/)
- [MSK multi-VPC private connectivity](https://docs.aws.amazon.com/msk/latest/developerguide/aws-access-mult-vpc.html)
- [MSK port information](https://docs.aws.amazon.com/msk/latest/developerguide/port-info.html)
- [IAM client mechanisms and official language helpers](https://docs.aws.amazon.com/msk/latest/developerguide/configure-clients-for-iam-access-control.html)
- [MSK IAM action/resource dependencies](https://docs.aws.amazon.com/msk/latest/developerguide/kafka-actions.html)
- [IAM use cases](https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control-use-cases.html)
- [aws-msk-iam-auth 2.3.8](https://github.com/aws/aws-msk-iam-auth/tree/v2.3.8)
- [MSK Connect](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect.html)
- [MSK Connect plugin packaging and Java versions](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect-plugins.html)
- [MSK Connect client authentication API](https://docs.aws.amazon.com/MSKC/latest/mskc/API_KafkaClusterClientAuthentication.html)
- [Lambda with MSK](https://docs.aws.amazon.com/lambda/latest/dg/with-msk.html)
- [Firehose with MSK](https://docs.aws.amazon.com/msk/latest/developerguide/integrations-kinesis-data-firehose.html)
- [Kinesis capacity modes](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html)
- [Kinesis retention](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)

## Next steps

[Part 7: Monitoring](./07-monitoring.md)

[Return to main page](./README.md)

## Quiz

[Topic quiz](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
