# Migrate EKS node IAM permissions to IRSA and Pod Identity

> **Last Updated**: November 20, 2026

When the IAM role in an EC2 node's instance profile grants application access to Amazon S3, workloads that reach the Instance Metadata Service (IMDS) may use the same IAM role. This lab reads the same S3 object using the node role, IAM Roles for Service Accounts (IRSA), and EKS Pod Identity. Then it removes the read permission from the node and checks which requests still succeed.

## Where the credentials come from

![The node path fetches credentials from IMDSv2. IRSA exchanges a web identity token at STS. Pod Identity uses the Agent and EKS Auth to retrieve credentials. Each Pod signs its S3 request using the returned credentials.](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-0.svg)

1. **Instance profile**. The EC2 instance profile contains the node IAM role. If a Pod can reach IMDS and the AWS SDK selects the EC2 metadata provider, the SDK uses an IMDSv2 session token to retrieve temporary node-role credentials. Requests signed with those credentials appear under a node-role session.
2. **IRSA**. EKS injects `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE` and a projected ServiceAccount token into new Pods that use a ServiceAccount annotated with the role ARN. The SDK exchanges the token via AWS Security Token Service (STS) `AssumeRoleWithWebIdentity`. IAM trusts the cluster's OpenID Connect (OIDC) issuer and checks the trust policy's audience (`sts.amazonaws.com`) and subject (`system:serviceaccount:<namespace>:<serviceaccount>`). [AWS IRSA documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
3. **EKS Pod Identity**. An EKS association binds a cluster, namespace and ServiceAccount to a role. EKS injects `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` and a projected token with the `pods.eks.amazonaws.com` audience. The SDK sends the token to the Agent on its node at `169.254.170.23`. The Agent uses the node role's `eks-auth:AssumeRoleForPodIdentity` permission to call EKS Auth and returns the workload's temporary role credentials. The role grants `sts:AssumeRole` and `sts:TagSession` to `pods.eks.amazonaws.com`. [How Pod Identity works](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html) · [Role trust policy](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html)

For IRSA and Pod Identity, EKS configures the projected volume and environment variables at Pod creation. The kubelet obtains and refreshes the ServiceAccount token in the volume, and the AWS SDK caches and refreshes the temporary AWS credentials. In all three cases, the AWS CLI uses the returned credentials to sign the S3 API request. The IAM permissions policy governs access to S3. The ServiceAccount binding and role trust policy govern who can obtain the workload credentials.

## Choosing the workload identity

| Topic | IRSA | EKS Pod Identity |
| --- | --- | --- |
| Binding | ServiceAccount role ARN annotation and IAM OIDC provider | EKS association |
| Credential path | Pod → regional STS | Pod → node Agent → EKS Auth |
| Role trust | OIDC issuer, audience and subject | EKS service principal and cluster, namespace and ServiceAccount request tags |
| Compute | EKS EC2 and Fargate, among other supported environments | Supported EKS Linux EC2 nodes. Auto Mode includes the agent capability |
| Cross-account access | Trust the OIDC provider in the target account or chain roles | The association's initial role belongs to the cluster account. Configure a target role or role chaining for cross-account access |
| Workload attribution | Workload IAM role and service logs | Workload IAM role and EKS session tags |

In a private cluster, provide a route to regional STS for IRSA Pods and to EKS Auth for the Pod Identity Agent. With no internet egress, check the corresponding VPC interface endpoints, DNS and security groups. The workload also needs connectivity to its destination service, such as S3. Include the Agent's link-local address in `NO_PROXY` if using a proxy. [Pod Identity requirements](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) · [Private cluster requirements](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)

## Migration sequence for an existing cluster

1. **Inventory dependencies.** Compare node IAM policies with actual IAM sessions in CloudTrail and identify AWS API calls from Deployments, StatefulSets, DaemonSets, CronJobs and controllers. Enable the corresponding S3 data event logging to observe object reads. Keep `AmazonEKSWorkerNodePolicy` or equivalent permissions for node registration and the Pod Identity Agent. Keep `AmazonEC2ContainerRegistryPullOnly` or equivalent permissions for Amazon Elastic Container Registry (ECR) image pulls. Move the VPC Container Network Interface (CNI) policy to an `aws-node` workload role when supported. Verify the CNI credentials and IP assignment for new Pods before removing that policy from the node role. [EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [S3 CloudTrail events](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html)
2. **Create a scoped IAM role and a dedicated ServiceAccount per workload.** For IRSA, register the cluster issuer as an IAM OIDC provider, create a role that checks the exact audience and subject, and annotate the ServiceAccount with `eks.amazonaws.com/role-arn`. For Pod Identity, check Agent readiness and the node's EKS Auth permission, then create the association with a role scoped by request tags. Confirm compute and SDK support. [IRSA SDK versions](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html) · [Pod Identity SDK versions](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
3. **Create a fresh canary Pod.** Change `serviceAccountName` in the Pod template. Inspect the names of the injected environment variables, verify the caller ARN with the application's credential provider, and call the APIs the application needs. Keep token and key values out of logs. Explicit credentials and providers earlier in the default chain can take precedence. Common SDKs evaluate IRSA's web-identity provider before the container provider, so use a separate ServiceAccount to verify Pod Identity. [Credential provider chain](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
4. **Roll out in batches.** Observe errors, `AccessDenied`, temporary credential refresh and scheduled jobs. Remove the application-specific policy statements once workloads have demonstrated independence from them. Keep the previous Pod template and exact IAM policy for the rollback window. After removing permissions, restore the minimal policy and wait for it to propagate before rolling back Pods that depended on it.
5. **Restrict node credential access.** Enforce IMDSv2 and restrict regular Pod access on node groups after testing compatibility. On a managed node group with a custom launch template, set `HttpTokens=required` and `HttpPutResponseHopLimit=1` in a new template version and roll the nodes. If the existing group has no custom launch template, validate a new node group before moving workloads. Karpenter uses `EC2NodeClass.spec.metadataOptions`. EKS Auto Mode enforces IMDSv2 and a hop limit of 1 by default. Control `hostNetwork` Pods, privileged Pods and node-level access separately. `AWS_EC2_METADATA_DISABLED=true` disables the SDK metadata provider. [Managed node group launch templates](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html) · [Auto Mode IMDS settings](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html) · [EKS IAM best practices](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)

<details>
<summary>Canary cutover commands</summary>

These commands bind the prepared IAM roles to dedicated ServiceAccounts and switch a canary Deployment. Set `KUBE_CONTEXT` to the target cluster context. In GitOps environments, apply the same ServiceAccount change through the declarative source.

The IRSA role trust policy scopes the issuer and ServiceAccount. Replace `<OIDC_ISSUER>` with the cluster issuer without the `https://` prefix.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/<OIDC_ISSUER>"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {
      "<OIDC_ISSUER>:aud": "sts.amazonaws.com",
      "<OIDC_ISSUER>:sub": "system:serviceaccount:<NAMESPACE>:<IRSA_SA>"
    }}
  }]
}
```

The Pod Identity role trusts the EKS service and checks its request tags. Leave session tags enabled on the association when using these conditions.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pods.eks.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"],
    "Condition": {"StringEquals": {
      "aws:RequestTag/eks-cluster-arn": "<CLUSTER_ARN>",
      "aws:RequestTag/kubernetes-namespace": "<NAMESPACE>",
      "aws:RequestTag/kubernetes-service-account": "<POD_IDENTITY_SA>"
    }}
  }]
}
```

```bash
# If you chose IRSA
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" annotate sa "$IRSA_SA" \
  "eks.amazonaws.com/role-arn=$IRSA_ROLE_ARN"

# If you chose Pod Identity and the Agent is ready
aws eks create-pod-identity-association --region "$AWS_REGION" --cluster-name "$CLUSTER" \
  --namespace "$NAMESPACE" --service-account "$POD_IDENTITY_SA" --role-arn "$POD_IDENTITY_ROLE_ARN"

# Set SA to the ServiceAccount you selected above
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" set serviceaccount \
  deployment "$CANARY_DEPLOYMENT" "$SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$CANARY_DEPLOYMENT" --timeout=5m
```

</details>

## Reproduce the S3 comparison

The demo uses a dedicated EKS cluster, one Linux EC2 worker, and one S3 object. Each role receives `s3:GetObject` for that object. The legacy Pod uses host networking to reach IMDSv2 deliberately. Both workload-identity Pods use regular Pod networking and disable the SDK's IMDS fallback. [Demo source and prerequisites](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity)

```bash
cd examples/security/eks-workload-identity
export AWS_REGION=ap-northeast-2
RUN_ID="$(date -u +%y%m%d%H%M%S)"
./demo.sh create "$RUN_ID"
./demo.sh compare "$RUN_ID"
./demo.sh delete "$RUN_ID"
```

AWS charges accrue while the cluster runs. Use the same run ID for `delete` if provisioning or comparison stops partway. The comparison asserts the calling role and checks the downloaded object body.

### Results from the Seoul Region

On November 20, 2026, we ran the comparison on a dedicated EKS 1.35 cluster in the Seoul Region (`ap-northeast-2`). The Amazon Linux 2023 node required IMDSv2 and had a response hop limit of 1. Each Job used AWS CLI 2.35.11 to call STS `GetCallerIdentity` and S3 `GetObject`.

| Pod | Before node permission removal | After node permission removal |
| --- | --- | --- |
| Legacy | Node role · read allowed | Node role · read denied |
| IRSA | IRSA role · read allowed | IRSA role · read allowed |
| Pod Identity | Pod Identity role · read allowed | Pod Identity role · read allowed |

`GetCallerIdentity` still identifies the legacy Job as the node role after revocation. IMDS can still issue node credentials, but the signed object request is denied. The workload roles retained their own S3 permissions and continued to read the same object. The legacy result took time to change while the IAM policy propagated, so the comparison checked it again from a fresh Job.

## Troubleshooting

- **The caller is the node role.** Check the Pod was recreated, references the intended ServiceAccount, and has the correct annotation or association. Verify the SDK version, credential chain and the names of the injected variables.
- **IRSA token exchange fails.** Check the IAM provider for the token issuer, the role's audience and subject, and the network path to STS.
- **Pod Identity credential retrieval fails.** Check the Agent on the Pod's node, EKS Auth connectivity, node permissions, association propagation and the trust policy's request tag conditions.
- **The expected role receives an S3 denial.** Check the exact object ARN, bucket policy, service control policy (SCP), permissions boundary and VPC endpoint policy. For objects using server-side encryption with AWS Key Management Service keys (SSE-KMS), check the permissions on the key.
