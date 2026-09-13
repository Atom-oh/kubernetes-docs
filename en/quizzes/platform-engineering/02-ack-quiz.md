# AWS Controllers for Kubernetes (ACK) Quiz

[ACK](../../platform-engineering/02-ack.md)

These questions retain the original 15 topics using the reviewed controller behavior.

## 1. What is ACK's main purpose?

<details>
<summary>Show answer</summary>

Declaratively manage AWS resources through Kubernetes APIs and custom resources. It does not guarantee automatic cost savings or immediate readiness.

</details>

## 2. What component is installed for each service?

<details>
<summary>Show answer</summary>

A service controller, with its CRDs. Select the required services and inspect supported resources and fields in versioned CRDs.

</details>

## 3. How should controllers receive AWS credentials?

<details>
<summary>Show answer</summary>

Configure workload identity such as IRSA or supported EKS Pod Identity. Verify OIDC trust/association, ServiceAccount, SDK/agent compatibility and minimal IAM permissions. Do not store access keys in ConfigMaps or use root credentials.

</details>

## 4. Which value retains AWS resources after CR deletion?

<details>
<summary>Show answer</summary>

`services.k8s.aws/deletion-policy: retain`. The current runtime does not accept orphan. Precedence is the CR, namespace service-specific annotation, then controller default. Retained AWS resources still require ownership and operations.

</details>

## 5. How are existing resources adopted?

<details>
<summary>Show answer</summary>

Use ResourceAdoption's `adoption-policy: adopt` and service-specific adoption-fields, verifying gates, identifiers, region and account. resource-imported:true is not this configuration; adopt-or-create can create a missing resource. Subsequent reconciliation can mutate resources, so distinguish adoption from read-only behavior.

</details>

## 6. What does GA status establish?

<details>
<summary>Show answer</summary>

It identifies the controller's official maturity stage, not support for every AWS API or operational requirement. Distinguish maturity from a CRD's v1alpha1 string and verify fields, releases and operational suitability.

</details>

## 7. Which condition indicates synchronization, and what are its limits?

<details>
<summary>Show answer</summary>

ACK.ResourceSynced=True describes controller synchronization. It is not proof of app readiness, database connectivity or message delivery. Inspect other conditions and AWS service state.

</details>

## 8. Does separating team namespaces complete isolation?

<details>
<summary>Show answer</summary>

No. Default installScope=cluster watches CRs across namespaces. Restrict watchNamespace/installScope, ServiceAccount/IAM/RBAC and cross-namespace/CARM behavior together. Namespace mode can still have cluster read permissions for its namespace cache.

</details>

## 9. What pattern aligns desired and observed AWS state?

<details>
<summary>Show answer</summary>

The reconciliation loop repeatedly handles supported fields and controller logic. Transient errors and AWS quotas affect it; it does not immediately repair every possible drift.

</details>

## 10. Which Kubernetes extension defines resource inputs?

<details>
<summary>Show answer</summary>

CRDs. The S3 example uses Bucket.spec.policy. The reviewed versions have no separate BucketPolicy or IAM RolePolicyAttachment CRDs; verify actual kinds and schemas.

</details>

## 11. Where can the ARN be found?

<details>
<summary>Show answer</summary>

When provided for the resource, use status.ackResourceMetadata.arn, including NLB and TargetGroup. Additional status fields differ by resource.

</details>

## 12. How does CARM differ from cross-cluster references?

<details>
<summary>Show answer</summary>

CARM configures a controller to manage another AWS account through target-role assumption, requiring trust, AssumeRole permissions, mappings and controller settings. It does not make competing mutation by several clusters safe. Separate mutation ownership from read-only references.

</details>

## 13. What belongs in a Development-tagged S3 Bucket example?

<details>
<summary>Show answer</summary>

Use a globally unique name, actual region, tagging.tagSet, all four Block Public Access settings and encryption. The principal/IAM Role must exist before the bucket policy is applied. Replace illustrative names and account IDs.

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: app-data
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: replace-with-globally-unique-bucket-name
  createBucketConfiguration:
    locationConstraint: us-west-2
  publicAccessBlock:
    blockPublicACLs: true
    blockPublicPolicy: true
    ignorePublicACLs: true
    restrictPublicBuckets: true
  encryption:
    rules:
    - applyServerSideEncryptionByDefault:
        sseAlgorithm: AES256
  tagging:
    tagSet:
    - key: Environment
      value: Development
  policy: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n      \"\
    Effect\": \"Allow\",\n      \"Principal\": {\n        \"AWS\": \"arn:aws:iam::123456789012:role/MyApplicationRole\"\
    \n      },\n      \"Action\": \"s3:GetObject\",\n      \"Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name/*\"\
    \n    }\n  ]\n}"
```

</details>

## 14. How is the ACK S3 chart inspected, and what precedes installation?

<details>
<summary>Show answer</summary>

The command renders a pinned OCI chart offline. Prepare infra, its ServiceAccount, IRSA/Pod Identity and IAM permissions before a real install/upgrade. Rendering is not AWS deployment verification.

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

</details>

## 15. What status and logs should be inspected?

<details>
<summary>Show answer</summary>

Specify namespace and fully qualified kinds; inspect conditions/events, controller image/logs, actual account/region/permissions and references. The chart label is app.kubernetes.io/instance=ack-s3. Clearing finalizers is not a routine fix.

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

</details>
