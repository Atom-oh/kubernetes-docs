# Migrate EKS node IAM permissions to IRSA and Pod Identity

> **Last Updated**: November 21, 2026

When an application's S3 permission is attached to the EC2 node's instance profile — the node IAM role — every Pod on that node that can reach the instance metadata service (IMDS) gets the same permission. A grant added for one payments Pod also opens to the log shipper and the batch Jobs on the node. CloudTrail records all of them as the same node instance session, so you cannot tell which workload made a call.

This workbook compares the two ways to move that permission to a per-workload identity: IRSA (IAM Roles for Service Accounts) and EKS Pod Identity. It then lays out a migration order for production clusters and shows a live demo that migrates three copies of the same app side by side.

## Where credentials come from

![Three Pods get credentials on three paths. The node-role Pod gets them from IMDSv2, the IRSA Pod from STS AssumeRoleWithWebIdentity, and the Pod Identity Pod through the Pod Identity Agent on its node and EKS Auth. Each Pod signs its S3 request with the credentials it received.](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-0.svg)

The AWS SDKs and the AWS CLI inside a Pod walk the [default credential provider chain](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html) from the top. Static keys in environment variables, the web identity token (IRSA) and the container credential provider (Pod Identity) all come before IMDS. A new Pod into which EKS injected the IRSA or Pod Identity variables therefore uses the new role without code changes. A Pod with nothing injected falls through to the last step, IMDS, and receives the node role.

| Path | Injected into the Pod | SDK calls | Resulting role |
| --- | --- | --- | --- |
| Node instance profile | Nothing | IMDSv2 `169.254.169.254` | Node IAM role (shared by every Pod on the node) |
| IRSA | `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`, token volume | Regional STS (Security Token Service) `AssumeRoleWithWebIdentity` | Role in the ServiceAccount annotation |
| EKS Pod Identity | `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`, token volume | Pod Identity Agent on the same node, `169.254.170.23` | Role in the association |

With an IMDS response hop limit of 2 or more, an ordinary Pod without host networking can obtain an IMDSv2 token and the node role's credentials. Managed node group launch templates often set this value to 2. That is why the last migration step lowers the hop limit to 1.

<a id="irsa-flow"></a>
## How IRSA works

![IRSA flow. A webhook sees the ServiceAccount annotation and injects environment variables and a projected token (aud sts.amazonaws.com). The SDK sends the token to STS AssumeRoleWithWebIdentity; STS verifies the signature through the IAM OIDC provider, checks aud and sub in the trust policy and returns temporary credentials.](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-1.svg)

1. **Trust setup.** Each cluster has an OIDC (OpenID Connect) issuer URL. Register that issuer once as an IAM OIDC provider in the account. The role's trust policy names the provider as its `Federated` principal and conditions on `aud` (`sts.amazonaws.com`) and `sub` (`system:serviceaccount:<namespace>:<serviceaccount>`).
2. **Injection at Pod creation.** When the ServiceAccount carries `eks.amazonaws.com/role-arn`, an EKS mutating webhook adds `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE` and a projected token volume at `/var/run/secrets/eks.amazonaws.com/serviceaccount/token` to every new Pod. Running Pods do not change, so a rollout is required.
3. **Token issue and refresh.** The kubelet requests a ServiceAccount token for the audience `sts.amazonaws.com`, writes it to the file and refreshes it before it expires.
4. **Token exchange.** The SDK sends the token to regional STS `AssumeRoleWithWebIdentity`. STS verifies its signature with the issuer keys registered through the IAM OIDC provider, checks the `aud` and `sub` conditions and returns temporary credentials. The Pod talks to STS directly, so it needs a network path to STS. [AWS IRSA documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

<a id="pod-identity-flow"></a>
## How EKS Pod Identity works

![Pod Identity flow. An association in the EKS API maps the ServiceAccount to a role, and EKS injects container-credential variables and a projected token (aud pods.eks.amazonaws.com). The SDK calls the Pod Identity Agent on its node; the Agent uses the node role's eks-auth permission to call EKS Auth AssumeRoleForPodIdentity, and EKS returns credentials for the role with session tags.](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-2.svg)

1. **Agent setup.** Install the `eks-pod-identity-agent` add-on once per cluster. The agent is a DaemonSet on the node's host network that uses ports 80 and 2703 on the link-local address `169.254.170.23` (IPv6 `[fd00:ec2::23]`). EKS Auto Mode has it built in.
2. **Role and association.** The role trusts the service principal `pods.eks.amazonaws.com` for `sts:AssumeRole` and `sts:TagSession`. There is no per-cluster provider, so the same role works in another cluster without a trust policy change. The binding is an association in the EKS API (cluster, namespace, ServiceAccount → role); no Kubernetes object is annotated.
3. **Injection at Pod creation.** For a ServiceAccount with an association, EKS injects `AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` and a projected token for the audience `pods.eks.amazonaws.com` into new Pods.
4. **Credential lookup.** The SDK sends the token to the agent on its node. The agent calls EKS Auth with the node role's `eks-auth:AssumeRoleForPodIdentity` permission (part of `AmazonEKSWorkerNodePolicy`). EKS Auth validates the token and the association, assumes the role and returns credentials with session tags such as `eks-cluster-arn`, `kubernetes-namespace` and `kubernetes-service-account`. The node role keeps only the permission the agent needs to call EKS Auth; the application's business permission lives on the Pod Identity role. [How Pod Identity works](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)

## IRSA and Pod Identity compared

AWS recommends EKS Pod Identity whenever possible. IRSA still fits some runtimes and team structures. [AWS comparison](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)

| Attribute | IRSA | EKS Pod Identity |
| --- | --- | --- |
| Per-cluster setup | Register an IAM OIDC provider for each cluster | Pod Identity Agent add-on for each cluster (built into Auto Mode) |
| Where the binding lives | Kubernetes ServiceAccount annotation | EKS API association (no Kubernetes object changes) |
| Trust policy | `Federated` OIDC provider with `aud`/`sub` conditions; one more statement per cluster | One principal, `pods.eks.amazonaws.com`; unchanged for new clusters |
| Scale limits | 100 OIDC providers per account by default; the default 2,048-character trust policy typically fits about four bindings per role | 5,000 associations per cluster; the role trust policy does not grow |
| Credential path | Pod → regional STS (the Pod uses STS API quota) | Pod → node agent → EKS Auth (the Pod does not call STS) |
| Session information | Role session name; no session tags | Cluster, namespace and ServiceAccount session tags enable ABAC (attribute-based access control) |
| Runtimes | EKS on EC2 and Fargate, EKS Anywhere, ROSA, self-managed Kubernetes on EC2 | Linux EC2 nodes in EKS only; no Fargate, Windows, Outposts or EKS Anywhere |
| Cross-account | Target-account role trusts this cluster's OIDC provider | Association role is in the cluster's account; delegate with a target role or role chaining |
| Separation of duties | IAM admins create the OIDC provider; cluster operators annotate | IAM manages roles only; bindings live in the EKS API |

In short, Pod Identity is simpler and scales better for new EKS workloads on EC2. Use IRSA for Fargate or Windows nodes, or when the same setup must also run on Kubernetes outside EKS. Both can run in one cluster. When one ServiceAccount has both an IRSA annotation and an association, the EKS webhook injects only the Pod Identity variables into new Pods, not the IRSA ones. On the demo cluster, a `kubectl create --dry-run=server` check returned `AWS_ROLE_ARN` and `AWS_WEB_IDENTITY_TOKEN_FILE` with only the annotation, and only `AWS_CONTAINER_CREDENTIALS_FULL_URI` and `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` once the association was added. Running Pods keep their IRSA variables until they are recreated, so switch with a rollout and remove the unused annotation.

In private clusters, secure a path to regional STS for IRSA Pods and to EKS Auth (`eks-auth`) for the Pod Identity Agent. Without an internet path, check the corresponding VPC interface endpoints, DNS and security groups. Behind a proxy, add `169.254.170.23` and `[fd00:ec2::23]` to `NO_PROXY`. [Pod Identity considerations](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) · [Private cluster requirements](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)

## Migration order for production clusters

1. **Inventory dependencies.** Compare node-role policies with the IAM sessions CloudTrail actually records, and list the AWS APIs that Deployments, StatefulSets, DaemonSets, CronJobs and controllers call. Seeing S3 object access in CloudTrail requires data events on that bucket. Keep `AmazonEKSWorkerNodePolicy` for node registration and the Pod Identity Agent, and `AmazonEC2ContainerRegistryPullOnly` (or equivalent) for Amazon ECR (Elastic Container Registry) pulls. The VPC CNI (Container Network Interface) `AmazonEKS_CNI_Policy` can move to a dedicated `aws-node` role; verify CNI credentials and IP assignment for new Pods before removing it from the node role. [EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [S3 CloudTrail events](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html)
2. **Create a scoped IAM role and a dedicated ServiceAccount per workload.** For IRSA, register the cluster issuer as an IAM OIDC provider, create a role that checks the exact audience and subject, and annotate the ServiceAccount with `eks.amazonaws.com/role-arn`. For Pod Identity, check Agent readiness and the node's EKS Auth permission, then create the association with a role scoped by request tags. Confirm compute and SDK support. [IRSA SDK versions](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html) · [Pod Identity SDK versions](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
3. **Create canary Pods.** Change `serviceAccountName` in the Pod template or roll out new Pods, then check the injected variable names, the caller ARN of the running process and the AWS APIs it needs. Never log tokens or keys. Explicit credentials or an earlier provider in the default chain can take precedence. [Default credential provider chain](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
4. **Switch workloads one at a time.** Watch error rates, `AccessDenied`, token and credential refresh, and scheduled runs. Once a workload no longer relies on the node role's business permission, remove only that policy statement. Keep the previous Pod template and an exact copy of the node policy for the rollback window. To roll back after removing the permission, restore that minimal policy first, confirm propagation, then deploy the previous Pods.
5. **Restrict node credential access.** Starting with node groups whose compatibility you have tested, enforce IMDSv2 and restrict regular Pod access to IMDS. On a managed node group with a custom launch template, set `HttpTokens=required` and `HttpPutResponseHopLimit=1` in a new template version and roll the nodes. Karpenter uses `EC2NodeClass.spec.metadataOptions`; EKS Auto Mode enforces IMDSv2 and a hop limit of 1 by default. `hostNetwork` Pods reach IMDS regardless of the hop limit, so control them separately. Do not turn IMDS off (`HttpEndpoint=disabled`): the Pod Identity Agent itself runs on the host network and gets the node role's credentials from IMDS to call EKS Auth. [Managed node group launch templates](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html) · [EKS IAM best practices](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)

<details>
<summary>Trust policies and canary commands</summary>

The IRSA role trust policy scopes the cluster issuer and the ServiceAccount. Use the issuer without `https://` for `<OIDC_ISSUER>`.

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

The Pod Identity role trusts the EKS service principal. These conditions scope the cluster, namespace and ServiceAccount through session tags, so keep session tags enabled on the association.

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

# Roll out the canary with the ServiceAccount chosen above
SA="$IRSA_SA"   # or "$POD_IDENTITY_SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" set serviceaccount \
  deployment "$CANARY_DEPLOYMENT" "$SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$CANARY_DEPLOYMENT" --timeout=5m
```

</details>

<a id="live-demo"></a>
## Live demo: migrating three copies of one app

![Demo flow. At first all three copies of the orders app get the node role from IMDS and read S3. After migrate-irsa one copy gets the IRSA role from STS; after migrate-podid another gets the Pod Identity role through the agent. After revoke removes the node role's S3 permission, only the legacy copy is denied.](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-3.svg)

The demo adds one dedicated managed node group (t3.medium, private subnets, tainted) to an existing EKS 1.36 cluster and runs three copies of the same orders app on it. Every 3 seconds each copy calls STS `GetCallerIdentity` and S3 `GetObject` and prints one JSON line with the credential source, role name and S3 result. The starting point matches the cluster's production node group, IMDSv2 required with hop limit 2, and the node role carries the app's `s3:GetObject`. The legacy Pod is an ordinary Pod without host networking. [Demo code and presenter runbook](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity) · [Slides (Korean)](https://presentation.atomai.click/eks-workload-identity/)

```bash
cd examples/security/eks-workload-identity
export AWS_REGION=ap-northeast-2
export CLUSTER=<cluster name> VPC_NAME=<Name tag of the cluster VPC> \
  SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>
./demo.sh up d1124            # before the talk: node group, roles, bucket, three copies
./demo.sh watch d1124         # second terminal: live table
./demo.sh migrate-irsa d1124  # ServiceAccount annotation + rollout
./demo.sh migrate-podid d1124 # association + injection check + rollout
./demo.sh diff d1124          # compare injected variables, tokens, trust policies
./demo.sh revoke d1124        # remove the S3 permission from the node role
./demo.sh harden d1124        # (optional, ~15 min) roll the nodes to hop limit 1
./demo.sh restore d1124       # back to the start (rehearse again)
./demo.sh down d1124          # clean up
```

With `page-up` you can share a read-only live page with the audience. The path is CloudFront → VPC origin → internal ALB → dashboard Pod, and the ALB security group admits only the CloudFront VPC origin. The dashboard Pod has no AWS permissions, only a Role that reads Pods and logs in this namespace.

Everything the script creates carries the run ID in its name or a `LabRun` tag, and the script changes or deletes only resources that match that name or tag. It creates no VPC, subnet, security group, add-on or OIDC provider; it only checks that they exist. The [hands-on lab](../labs/security/17-eks-workload-identity-migration-lab.md) walks through each step with commands, expected output and checkpoints.

### Measured in the Seoul Region

We rehearsed twice on November 21, 2026 on an EKS 1.36 cluster in `ap-northeast-2`, with AWS CLI 2.35.11 inside the Pods. Pod Identity injection failed in the first rehearsal (see below), so the script was fixed; the table shows the second rehearsal, run end to end with the fixed script. Only `harden` comes from the first rehearsal.

| Step | orders-legacy | orders-irsa | orders-podid | Time |
| --- | --- | --- | --- | --- |
| Start | IMDS · node role · read allowed | IMDS · node role · read allowed | IMDS · node role · read allowed | — |
| `migrate-irsa` | unchanged | STS · IRSA role · read allowed | unchanged | 6 s |
| `migrate-podid` | unchanged | unchanged | Agent · Pod Identity role · read allowed | 11 s (including 5 s until injection was visible after creating the association) |
| `revoke` | node role · **read denied** | read allowed | read allowed | denied after 13 s |
| `harden` (optional, first rehearsal) | **no credentials** (IMDS response blocked) | read allowed | read allowed | node roll 878 s |

`diff` shows how the two differ. Both tokens are ServiceAccount tokens signed by the same cluster issuer, but the audience and the receiver differ.

| Compared | IRSA Pod | Pod Identity Pod |
| --- | --- | --- |
| Injected variables | `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`, `AWS_STS_REGIONAL_ENDPOINTS` | `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`, `AWS_STS_REGIONAL_ENDPOINTS` |
| Token `aud` | `sts.amazonaws.com` | `pods.eks.amazonaws.com` |
| Token `sub` | `system:serviceaccount:wid-d1124:orders-irsa` | `system:serviceaccount:wid-d1124:orders-podid` |
| Token lifetime | 86,400 s (24 h) | about 22–24 h (the webhook adds jitter; measured 79,636 s and 86,171 s) |
| Role trust principal | `Federated`: cluster OIDC provider, conditions `aud` and `sub` | `Service`: `pods.eks.amazonaws.com`, three request-tag conditions |

Rehearsals exposed two eventual-consistency effects. First, in the first rehearsal a Pod rolled out right after the association was created had no Pod Identity variables and kept using the node role, so it was denied too once the node policy was removed. `migrate-podid` therefore sends the Deployment's Pod template through `kubectl create --dry-run=server` to see what the mutating webhooks inject, and rolls out only after that. In the second rehearsal, injection became visible 5 seconds after the association was created. Second, after `revoke` in the first rehearsal the legacy Pod was denied within 13 seconds, but two more allowed reads appeared about 4.5 minutes later; all 11 reads in the minute checked right after that were denied. In production, keep watching for several minutes after removing a node policy before you conclude.

## Troubleshooting

- **The node role appears.** Check that the Pod is new, references the correct ServiceAccount, and has the IRSA annotation or an exact association. Inspect the SDK version, the default provider chain and the injected variable names.
- **IRSA token exchange fails.** Check the IAM provider for the token issuer, the `aud`/`sub` trust conditions and reachability of STS.
- **Pod Identity credential lookup fails.** Check the Agent on that node, EKS Auth connectivity, node IAM permissions, association propagation and the role's request-tag trust conditions. An association can take several seconds to take effect after creation.
- **The expected role is denied by S3.** Identity and resource access are separate. Check the object ARN, bucket policy, SCPs (Service Control Policies), permissions boundaries and VPC endpoint policies. For objects encrypted with an AWS KMS (Key Management Service) key (SSE-KMS), also check permission on the key.
