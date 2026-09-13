# AWS Controllers for Kubernetes (ACK)

> **Reviewed**: September 12, 2026

## Concepts and Architecture

ACK connects Kubernetes custom resources to AWS APIs through service-specific controllers. CRDs define inputs; controllers reconcile desired state with observed AWS state. Creating a CR does not mean the AWS resource is ready. Inspect status and the service's own readiness.

ACK reuses Kubernetes APIs, RBAC and GitOps tools, but Kubernetes authorization and AWS IAM remain separate. A user's CR normally causes actions under the controller's AWS permissions. Permission to write a CR therefore delegates the ability to request AWS actions through that controller.

ACK is not a mandatory successor to CloudFormation or Terraform. AWS holds the actual resource; Kubernetes holds CR spec/status. Drift handling depends on supported fields and controller logic. Assign one mutation owner rather than letting several tools or clusters reconcile the same AWS resource.

![ACK reconciles Kubernetes custom resources through AWS APIs](../.gitbook/assets/en-platform-engineering-02-ack-0.png)

[Interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-02-ack-0.html)

## Versions and Support

| Controller | Version |
| --- | --- |
| s3 | 1.12.1 |
| iam | 1.9.0 |
| sqs | 1.7.0 |
| sns | 1.10.1 |
| elbv2 | 1.7.0 |
| route53 | 1.6.0 |
| rds | 1.12.0 |

These versions were checked against official releases and OCI charts. Consult the official service list for complete coverage and Alpha/Beta/GA status. GA does not imply every AWS API feature or every operational requirement is covered. A CRD's v1alpha1 API string is distinct from controller maturity.

The historical Kubernetes 1.16 minimum is not a current operations baseline. Verify a supported Kubernetes/EKS version, controller compatibility, Helm version and CRD upgrade process together.

## Installation Preparation and Offline Inspection

Use the OCI chart path below, rather than the former eks-charts s3-chart path. This command renders manifests without installing into a cluster.

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.12.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

Before a real install/upgrade, prepare the infra namespace and controller ServiceAccount, then configure IRSA or supported EKS Pod Identity. Verify IRSA OIDC trust conditions for the namespace/ServiceAccount, or Pod Identity agent/SDK compatibility and association. Creating an IAM role alone does not attach permissions to a ServiceAccount.

Review controller read/create/update/delete/tag and any PassRole permissions against the managed resources. AmazonS3FullAccess or Resource:"*" is not a least-privilege example. The data-access policies in the subguide are not a complete controller policy.

Successful rendering does not validate IAM, AWS API constraints, admission, CRD installation, endpoint connectivity or resource creation. Installing controllers and changing CRDs are separate operational changes.

## Namespace and Account Isolation

The default installScope is cluster. Merely installing releases into dev/prod namespaces can leave both controllers watching the same CRs. This example sets installScope=namespace and watchNamespace=infra and disables CARM and cross-namespace references. Use separate watch scopes, ServiceAccounts, IAM roles and RBAC for other teams.

Even in namespace mode, the current chart renders a ClusterRole granting namespaces get/list/watch for its namespace cache. Namespace mode does not remove every cluster permission. Inspect rendered Roles, ClusterRoles, Bindings and Secret/FieldExport access. Permission to alter namespace annotations, role mappings and reference targets also affects isolation.

CARM is cross-account management requiring target-role trust, AssumeRole permissions and controller configuration. It does not guarantee safe concurrent mutation by several clusters. Separate read-only references from mutation ownership.

## Creation, References and Status

Service schemas differ. S3 policy belongs in Bucket.spec.policy; there is no separate BucketPolicy CRD. IAM managed policies attach through Role.policies/policyRefs. The subguides show SQS queueName/string attributes and the dedicated SNS Topic/Subscription fields.

- [S3 / IAM](ack/01-s3-iam.md)
- [SQS / SNS](ack/02-sqs-sns.md)
- [ELBv2 / Route 53 / Aurora](ack/03-elbv2-route53-rds.md)

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

ACK.ResourceSynced=True describes controller synchronization; it is not a database connection or app-readiness check. Inspect other conditions such as ACK.Terminal/ACK.Recoverable and service status. When supplied for the resource, its ARN is under status.ackResourceMetadata.arn; NLB and TargetGroup ARNs use this path too.

Supported Ref fields can connect resources in the same namespace. Applying several YAML documents is not an AWS-wide transaction. Verify referenced-resource readiness and external identifiers/ARNs.

## Adoption and Retention

Use the ResourceAdoption annotations below. The current S3 chart enables this feature gate. Review identifiers, account and region, and plan ownership transfer from other tools before adoption.

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: existing-data
  namespace: infra
  annotations:
    services.k8s.aws/adoption-policy: adopt
    services.k8s.aws/adoption-fields: '{"name":"REPLACE_WITH_EXISTING_BUCKET"}'
    services.k8s.aws/deletion-policy: retain
spec:
  name: REPLACE_WITH_EXISTING_BUCKET
```

The runtime accepts adopt and adopt-or-create. adopt reads existing state into spec/status; adopt-or-create can create a missing resource. Subsequent normal reconciliation can mutate an adopted resource, so adoption is not merely read access. Read-only behavior is a separate feature with its own gate and lifecycle. The former resource-imported:"true" annotation does not configure adoption. Official documentation also identifies AdoptedResource as the older approach.

The retention value is **retain**. The current runtime does not accept orphan. Precedence is the individual CR's services.k8s.aws/deletion-policy, the namespace's service-specific deletion-policy, then controller default. Retaining AWS resources leaves ongoing cost, ownership and backup responsibilities.

## Observability, Scaling and Recovery

Enable metrics.service.create and match the target namespace and port name below. Prometheus Operator CRDs and the Prometheus ServiceMonitor selectors are separate prerequisites.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ack-s3
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: [infra]
  selector:
    matchLabels:
      app.kubernetes.io/name: s3-chart
      app.kubernetes.io/instance: ack-s3
  endpoints:
    - port: metricsport
      interval: 30s
```

The reviewed runtime defines ack_outbound_api_requests_total and ack_outbound_api_requests_error_total. Do not invent reconcile success/failure or API-latency metric names. Verify controller-runtime metric names, labels and versions at the actual endpoint. CloudTrail auditing depends on the service/API logging support and configured events.

Replica configuration is deployment.replicas; review leaderElection.enabled when running several replicas. replicaCount is not this chart's setting. Additional leader-elected replicas do not automatically increase parallel throughput. Tune reconcile concurrency/resync with observed quotas, throttling and resource usage.

Version environment-specific manifests and charts in Git, keeping credentials out. Recovery needs AWS data/backups, identifiers, retention policy and ownership as well as CRs. Creating a CR in another region does not implement data replication or recovery.

## Troubleshooting

For creation failures, inspect conditions/events, controller image/logs, account/region, IAM trust/policies, references and service constraints. Distinguish Kubernetes RBAC from AWS IAM errors. For Terminating resources, identify the AWS deletion, dependency or retention condition the finalizer is waiting for.

Do not routinely clear finalizers. Doing so can leave untracked AWS resources. Resolve the cause first; use a last-resort recovery procedure only after reviewing actual resource state, backups and subsequent ownership.

## Verification and References

The eight original guide files and two quizzes in Korean/English, including 56 unique code blocks, were read. Seven official OCI charts were rendered and 18 resource examples checked against versioned CRDs with unknown-spec-field rejection. No AWS resource creation, controller execution, admission/CEL, message delivery or database connectivity was tested.

- [ACK services](https://aws-controllers-k8s.github.io/community/docs/community/services/)
- [Resource adoption](https://aws-controllers-k8s.github.io/community/docs/user-docs/features/#resourceadoption)
- [Retention](https://aws-controllers-k8s.github.io/community/docs/user-docs/deletion-policy/)
- [S3 chart 1.12.1](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.12.1/helm)
- [Runtime 0.63.0](https://github.com/aws-controllers-k8s/runtime/tree/v0.63.0)

[ACK quiz](../quizzes/platform-engineering/02-ack-quiz.md)
