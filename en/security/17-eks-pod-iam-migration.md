# From Node Instance Profile to IRSA and EKS Pod Identity: How It Works and How to Migrate

> **Supported Versions**: Amazon EKS versions in standard support, EC2 Linux nodes (Pod Identity does not support Fargate)
> **Last Updated**: November 19, 2026

Many EKS clusters start by attaching S3, DynamoDB or SQS permissions to the **node IAM role (instance profile)**. It works, but **every Pod on that node shares the same permissions**. This guide covers moving from that state to per-Pod permissions with **IRSA (IAM Roles for Service Accounts)** and **EKS Pod Identity**. It first shows how each of the three mechanisms obtains credentials, then walks through a demo that deploys all three side by side and a step-by-step migration runbook.

Demo code: [`examples/security/pod-iam-migration`](../../examples/security/pod-iam-migration/README.md)

## 1. Why migrate: the node role is the role of "everything on the node"

When code has no keys, the AWS SDK walks the **default credential provider chain** in order. If it finds no environment variables, no web identity token and no container credentials endpoint, it finally asks **IMDS (169.254.169.254)**. IMDS returns temporary credentials for the EC2 instance profile, which is the node role.

```text
                    EC2 Worker Node  (instance profile = NodeInstanceRole)
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                                                                          │
 │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                 │
 │   │ payments-api │   │  batch-job   │   │ compromised  │                 │
 │   │ (needs S3)   │   │ (needs SQS)  │   │ (needs none) │                 │
 │   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                 │
 │          │ SDK chain: env? ✗ web identity? ✗ container creds? ✗           │
 │          └──────────────────┼──────────────────┘                         │
 │                             ▼                                            │
 │          ┌────────────────────────────────────┐                          │
 │          │ IMDS  169.254.169.254              │  with hop limit 2 the    │
 │          │ /latest/meta-data/iam/             │  response also reaches   │
 │          │   security-credentials/NodeRole    │  the Pod network         │
 │          └─────────────────┬──────────────────┘                          │
 └────────────────────────────┼─────────────────────────────────────────────┘
                              ▼
          All three Pods get the same credentials:
          arn:aws:sts::111122223333:assumed-role/NodeInstanceRole/i-0abc...
          = union of S3 + SQS + ECR + EC2 (ENI) permissions
```

There are three problems.

| Problem | Consequence |
|---|---|
| Union of permissions | The node role ends up holding the permissions of every workload that may be scheduled on the node |
| Blast radius | Compromising one Pod that needs no permissions at all exposes the entire node role |
| No attribution | CloudTrail records only `NodeInstanceRole/i-0abc...`, so you cannot tell which Pod made the call |

The IMDSv2 PUT token response travels only as far as its IP TTL (`HttpPutResponseHopLimit`). A Pod in its own network namespace is one extra hop away, so with a hop limit of **1** the response never reaches the Pod, and with **2** it does. The default depends on the tool that created the node group and its launch template, so check it yourself.

```bash
aws ec2 describe-instances --filters "Name=tag:eks:cluster-name,Values=$CLUSTER_NAME" \
  --query 'Reservations[].Instances[].[InstanceId,MetadataOptions.HttpTokens,MetadataOptions.HttpPutResponseHopLimit]' \
  --output table
```

## 2. How IRSA works

IRSA makes **IAM trust the cluster's OIDC issuer**. The Pod presents a Kubernetes-signed ServiceAccount token (JWT) to STS; STS verifies the signature against the public keys (JWKS) from the OIDC discovery document and then hands over the role.

### 2.1 Components

| Component | Location | Role |
|---|---|---|
| OIDC issuer | EKS control plane | Signs SA tokens, publishes `/.well-known/openid-configuration` and JWKS |
| IAM OIDC identity provider | Each AWS account | Registers that issuer as an IAM federated principal |
| IAM role trust policy | IAM | `sub` (`system:serviceaccount:<ns>:<sa>`) and `aud` (`sts.amazonaws.com`) conditions |
| SA annotation | Kubernetes | `eks.amazonaws.com/role-arn: <role arn>` |
| Pod Identity Webhook | EKS control plane (mutating webhook) | Injects env vars and a projected token volume at Pod creation |
| AWS SDK | Container | Calls and refreshes `AssumeRoleWithWebIdentity` |

### 2.2 Credential flow

```text
 ① kubectl apply (Pod, serviceAccountName: s3-reader)
        │
        ▼
 ┌────────────────────────── EKS Control Plane ──────────────────────────┐
 │  kube-apiserver ──admission──▶ Pod Identity Webhook                   │
 │        │                       SA has role-arn annotation?            │
 │        │                       └─ yes → mutate Pod spec:              │
 │        │                          env  AWS_ROLE_ARN=arn:...:role/X     │
 │        │                          env  AWS_WEB_IDENTITY_TOKEN_FILE=    │
 │        │                               /var/run/secrets/eks.amazonaws.com/serviceaccount/token
 │        │                          vol  projected SA token              │
 │        │                               (audience: sts.amazonaws.com)   │
 │  OIDC issuer  https://oidc.eks.<region>.amazonaws.com/id/<ID>          │
 │     └─ /.well-known/openid-configuration , /keys (JWKS)  ◀────┐        │
 └────────┼──────────────────────────────────────────────────────┼────────┘
          │ ② kubelet requests the token, mounts it, rotates it   │
          ▼                                                      │
 ┌──────── Worker Node ────────┐                                 │
 │ Pod                          │                                │
 │  SDK: token file in env      │                                │
 │  → web identity provider     │                                │
 └──────────────┬───────────────┘                                │
                │ ③ sts:AssumeRoleWithWebIdentity                │
                │    RoleArn=X, WebIdentityToken=<JWT>            │
                ▼                                                 │
 ┌─────────────── AWS STS ─────────────────┐  ④ fetch JWKS to verify signature
 │ - iss matches the account OIDC provider? │──────────────────────┘
 │ - verify JWT signature and expiry        │
 │ - evaluate sub/aud in role X trust policy│
 └──────────────┬──────────────────────────┘
                │ ⑤ temporary credentials (AccessKey/Secret/SessionToken, expiry)
                ▼
            Pod → S3 (CloudTrail: assumed-role/X/<session>)
```

### 2.3 Key configuration

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::111122223333:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:demo-irsa:s3-reader",
      "oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com"
    }
  }
}
```

- **The cluster-specific OIDC provider ARN is baked into the trust policy.** Reusing a role across clusters means one statement per cluster, which runs into the trust policy size limit.
- Each account must register the OIDC provider, and there is a per-account quota on OIDC providers.
- Widening the `sub` condition with `StringLike` and `*` lets other ServiceAccounts in that cluster take the role. Always pin the namespace and SA with `StringEquals`.
- The STS call goes directly from the Pod, so a private cluster needs an STS VPC endpoint.

## 3. How EKS Pod Identity works

Pod Identity removes the OIDC integration from IAM and lets **EKS manage "which SA uses which role" directly**. The mapping lives in an EKS API **Pod Identity association**, not in an SA annotation. On the node, the **Pod Identity Agent** fetches credentials on behalf of the SDK.

### 3.1 Components

| Component | Location | Role |
|---|---|---|
| `eks-pod-identity-agent` add-on | DaemonSet on each node, hostNetwork | Serves credentials on `169.254.170.23:80` (IPv6 `[fd00:ec2::23]:80`) |
| Pod Identity association | EKS API | (cluster, namespace, serviceaccount) → role ARN |
| IAM role trust policy | IAM | `Principal: { Service: pods.eks.amazonaws.com }`, `sts:AssumeRole` + `sts:TagSession` |
| Pod Identity Webhook | EKS control plane | Injects env vars and a projected token into Pods whose SA has an association |
| Node role | IAM | Lets the agent call `eks-auth:AssumeRoleForPodIdentity` (included in `AmazonEKSWorkerNodePolicy`) |

### 3.2 Credential flow

```text
 ⓪ aws eks create-pod-identity-association
       --namespace demo-podid --service-account s3-reader --role-arn arn:...:role/Y
        │  (stored in the EKS API, the SA object is unchanged)
        ▼
 ┌────────────────────────── EKS Control Plane ──────────────────────────┐
 │  kube-apiserver ──admission──▶ Pod Identity Webhook                   │
 │                                association exists?                    │
 │                                └─ yes → mutate Pod spec:              │
 │                                   env AWS_CONTAINER_CREDENTIALS_FULL_URI=
 │                                       http://169.254.170.23/v1/credentials
 │                                   env AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE=
 │                                       /var/run/secrets/pods.eks.amazonaws.com/serviceaccount/eks-pod-identity-token
 │                                   vol projected SA token               │
 │                                       (audience: pods.eks.amazonaws.com)
 └──────────────────────────────────────────────────────────────────────┘
          │
          ▼
 ┌──────────────────────────── Worker Node ──────────────────────────────┐
 │  Pod                                   eks-pod-identity-agent         │
 │  ┌─────────────────────────┐           (hostNetwork DaemonSet)        │
 │  │ SDK: container          │  ①  GET /v1/credentials                  │
 │  │ credential provider     │ ────────────────────────▶ 169.254.170.23 │
 │  │ Authorization: <token>  │                          │               │
 │  └─────────────────────────┘                          │ ② request     │
 │            ▲                                          │   signed with │
 │            │ ④ AccessKey/Secret/SessionToken          │   node role   │
 │            └──────────────────────────────────────────┤               │
 └───────────────────────────────────────────────────────┼───────────────┘
                                                         ▼
 ┌──────────────────── EKS Auth API ─────────────────────────────────────┐
 │ eks-auth:AssumeRoleForPodIdentity(clusterName, token)                 │
 │  - validate SA token → namespace / serviceaccount                     │
 │  - look up association → role Y                                       │
 │  - AssumeRole on role Y + attach session tags ────────────▶ AWS STS    │
 │      eks-cluster-arn, eks-cluster-name, kubernetes-namespace,          │
 │      kubernetes-service-account, kubernetes-pod-name, kubernetes-pod-uid
 └──────────────────────────────────────┬────────────────────────────────┘
                                        │ ③ temporary credentials
                                        ▼
                                  Agent → Pod (④)
```

The Pod never talks to STS directly. It shows its token to the agent on a link-local address, and the agent calls the EKS Auth API with the node role. The node role holds only this "broker" permission; the actual application permissions exist only on role Y linked by the association.

### 3.3 Key configuration

```json
{
  "Effect": "Allow",
  "Principal": { "Service": "pods.eks.amazonaws.com" },
  "Action": ["sts:AssumeRole", "sts:TagSession"]
}
```

- **The trust policy contains no cluster information.** The association decides which cluster and SA may use the role, so reusing a role across clusters never changes the trust policy.
- Conversely, to enforce in IAM that "only a specific cluster may use this role", add conditions such as `aws:RequestTag/eks-cluster-arn` to the trust policy, or control who can create associations (`eks:CreatePodIdentityAssociation`, `iam:PassRole`).
- **Session tags** enable ABAC. For example, a single role can let each namespace read only its own S3 prefix.

```json
{
  "Effect": "Allow",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-bucket/${aws:PrincipalTag/kubernetes-namespace}/*"
}
```

- Roles in other accounts are handled with the association's target role (role chaining) feature or a second AssumeRole in application code. Check support in the SDK and add-on versions you run.
- There is a **minimum SDK version**. Old SDKs that do not support `AWS_CONTAINER_CREDENTIALS_FULL_URI` plus a token file skip Pod Identity and fall through to IMDS. The node role is then used, so verify this before migrating.

## 4. Comparing the three mechanisms

| Item | Node instance profile | IRSA | EKS Pod Identity |
|---|---|---|---|
| Permission scope | Node (shared by all Pods) | ServiceAccount | ServiceAccount |
| Where the mapping lives | Instance profile | SA annotation + role trust | EKS API association |
| What IAM trusts | `ec2.amazonaws.com` | Per-cluster OIDC provider | `pods.eks.amazonaws.com` (shared) |
| Per-account setup | None | Register OIDC provider (per cluster) | None (install the add-on only) |
| Reusing a role across clusters | — | Add trust statements, size limit | No trust change, add associations only |
| Credential path | Pod → IMDS | Pod → STS (`AssumeRoleWithWebIdentity`) | Pod → Agent → EKS Auth → STS |
| Node component | None | None | Pod Identity Agent DaemonSet |
| CloudTrail principal | `NodeRole/i-xxx` | `RoleX/<session>` | `RoleY/eks-<cluster>-<pod>-...` + session tags |
| ABAC | Not possible | Limited (`sub`-based) | Session tags on namespace, SA, Pod |
| Fargate | N/A (Pod execution role) | Supported | Not supported |
| Kubernetes outside EKS (self-managed, other clouds) | — | Works with any OIDC issuer | EKS only |
| Good fit | Node functions (kubelet, ECR pull) | Fargate, non-EKS clusters, existing IRSA estate | New EKS workloads, many clusters and accounts |

The rule of thumb is simple: **on EKS with EC2 nodes, default to Pod Identity for new permissions**, and use IRSA where Pod Identity is unavailable, such as Fargate or clusters outside EKS. Both can coexist in one cluster.

### 4.1 Which one wins when both are configured

After the webhook injects env vars, the SDK credential chain makes the choice. The default chain in AWS SDKs is generally:

```text
 1. Static env keys          AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
 2. Shared config/credentials ~/.aws/...  (profile)
 3. Web identity (IRSA)      AWS_WEB_IDENTITY_TOKEN_FILE + AWS_ROLE_ARN
 4. Container credentials    AWS_CONTAINER_CREDENTIALS_FULL_URI (Pod Identity)
 5. IMDS                     169.254.169.254  → node role
```

So with both an annotation and an association, **IRSA wins.** When switching from IRSA to Pod Identity, the change only takes effect after you remove the annotation and restart the Pods. Also, **static keys injected from a Secret (step 1) override both**, so find them during the inventory phase. Check each language SDK's documentation for its exact order.

## 5. Hands-on comparison demo

The same workload is deployed in three namespaces; only the SA wiring differs. The `default/neighbor` Pod is a "neighbor" that was granted nothing.

```text
 S3 bucket pod-iam-demo-<acct>-<region>
        ▲             ▲                 ▲                  ▲
        │ NodeRole    │ IRSA role       │ Pod Identity role│ NodeRole (!)
 ┌──────┴─────┐ ┌─────┴──────┐  ┌───────┴──────┐   ┌───────┴───────┐
 │ demo-node  │ │ demo-irsa  │  │ demo-podid   │   │ default/      │
 │ whoami     │ │ whoami     │  │ whoami       │   │ neighbor      │
 │ SA: as-is  │ │ SA+annot.  │  │ SA+assoc.    │   │ no grants     │
 └────────────┘ └────────────┘  └──────────────┘   └───────────────┘
```

```bash
cd examples/security/pod-iam-migration
export CLUSTER_NAME=pod-iam-demo AWS_REGION=ap-northeast-2 NODEGROUP_NAME=ng-default

./01-baseline.sh             # grant S3 read to the node role (reproduce the legacy state)
./04-verify.sh               # every Pod is NodeRole, even neighbor can read S3
./02-irsa.sh                 # demo-irsa → IRSA
./03-pod-identity.sh         # demo-podid → Pod Identity
./04-verify.sh
./05-lockdown-node-role.sh   # remove app permission from node role + IMDS hop limit 1
./04-verify.sh
```

Expected results per step. `04-verify.sh` prints the injected env, `sts get-caller-identity`, `s3 ls` and IMDS reachability for each Pod.

| Pod | After 01 | After 02·03 | After 05 |
|---|---|---|---|
| `demo-node` | NodeRole, S3 ALLOWED | NodeRole, ALLOWED | No credentials, DENIED |
| `demo-irsa` | NodeRole, ALLOWED | `pod-iam-demo-irsa-s3-reader`, ALLOWED | IRSA, ALLOWED |
| `demo-podid` | NodeRole, ALLOWED | `pod-iam-demo-podid-s3-reader`, ALLOWED | Pod Identity, ALLOWED |
| `default/neighbor` | **NodeRole, ALLOWED** | **NodeRole, ALLOWED** | DENIED, IMDS BLOCKED |

The `neighbor` row is the point of the whole migration. **Adding** IRSA or Pod Identity alone does not remove node role exposure. It only takes effect once step 5 cleans up the node role and blocks IMDS.

To check the injected env directly:

```bash
kubectl -n demo-irsa  exec deploy/whoami -- env | grep ^AWS_
# AWS_ROLE_ARN=arn:aws:iam::111122223333:role/pod-iam-demo-irsa-s3-reader
# AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
# AWS_STS_REGIONAL_ENDPOINTS=regional

kubectl -n demo-podid exec deploy/whoami -- env | grep ^AWS_CONTAINER
# AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials
# AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE=/var/run/secrets/pods.eks.amazonaws.com/serviceaccount/eks-pod-identity-token
```

The token payload (JWT) shows the audience difference.

```bash
kubectl -n demo-podid exec deploy/whoami -- sh -c \
  'cut -d. -f2 "$AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE" | tr "_-" "/+" | base64 -d 2>/dev/null; echo'
# {"aud":["pods.eks.amazonaws.com"],"sub":"system:serviceaccount:demo-podid:s3-reader", ...}
# The IRSA token has "aud":["sts.amazonaws.com"]
```

> The demo scripts were only syntax-checked in the authoring session and were not run against a real account. The output above is the expected format from the official documentation; run the scripts in a sandbox account first to confirm.

## 6. Migration runbook

```text
 Phase 0        Phase 1         Phase 2            Phase 3          Phase 4
 Inventory ──▶  Role design ──▶ Switch workload ──▶ Verify, bake ──▶ Lock node role
 (who uses      (least privilege (IRSA or           (CloudTrail      (remove policies,
  the node role)  per workload)   Pod Identity)      principal)       block IMDS)
      ▲                                                               │
      └──────────── new workloads start with the Phase 2 method ◀─────┘
```

### Phase 0. Inventory: who actually uses the node role

1. **List node role policies**: anything beyond the baseline policies is a migration target.

   ```bash
   NODE_ROLE=$(aws eks describe-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $NG \
     --query nodegroup.nodeRole --output text | awk -F/ '{print $NF}')
   aws iam list-attached-role-policies --role-name $NODE_ROLE
   aws iam list-role-policies --role-name $NODE_ROLE
   ```

   The node itself needs `AmazonEKSWorkerNodePolicy`, ECR pull (`AmazonEC2ContainerRegistryPullOnly` or `ReadOnly`), and `AmazonEKS_CNI_Policy` if the VPC CNI uses the node role. Keep `AmazonSSMManagedInstanceCore` if you use SSM access.

2. **Check actual calls**: use IAM Access Advisor (last access per service) and CloudTrail to see which APIs the node role calls. Services other than EC2, ECR, EKS and STS are almost certainly Pods borrowing the node role. A sample query is in [`queries/cloudtrail-node-role-usage.sql`](../../examples/security/pod-iam-migration/queries/cloudtrail-node-role-usage.sql).

3. **Find the calling Pods**: CloudTrail has no Pod name, so match services against the cluster's workloads. Record each workload's SDK version and whether it uses static keys from a Secret.

   ```bash
   # Workloads that receive static keys via env
   kubectl get deploy,sts,ds -A -o json | jq -r '.items[] | select(
     [.spec.template.spec.containers[].env[]?.name] | index("AWS_ACCESS_KEY_ID"))
     | "\(.metadata.namespace)/\(.metadata.name)"'
   # SAs already using IRSA
   kubectl get sa -A -o json | jq -r '.items[] | select(.metadata.annotations["eks.amazonaws.com/role-arn"])
     | "\(.metadata.namespace)/\(.metadata.name) -> \(.metadata.annotations["eks.amazonaws.com/role-arn"])"'
   ```

4. **Check hostNetwork Pods**: they share the node's network namespace, so hop limit 1 does not block them. Decide on them separately.

### Phase 1. Per-workload role design

- Default to one role per workload (= ServiceAccount). Do not copy the node role policies; use IAM Access Analyzer's CloudTrail-based policy generation to keep only the actions actually used.
- Create a **dedicated ServiceAccount** per workload. Attaching a role to the `default` SA grants it to every Pod in that namespace.
- Choose the mechanism: Pod Identity for EC2 nodes, IRSA for Fargate or non-EKS. If several namespaces use different resources with the same pattern, Pod Identity session-tag ABAC can reduce the number of roles.

### Phase 2-A. Switch to IRSA

```bash
# 1) Register the cluster OIDC provider (once per cluster and account)
eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --approve

# 2) Create the role: trust policy sub = system:serviceaccount:<ns>:<sa>
aws iam create-role --role-name app-x --assume-role-policy-document file://irsa-trust.json
aws iam put-role-policy --role-name app-x --policy-name app --policy-document file://app.json

# 3) Annotate the SA
kubectl -n app annotate sa app-x eks.amazonaws.com/role-arn=arn:aws:iam::<acct>:role/app-x

# 4) Restart: the webhook only mutates new Pods
kubectl -n app rollout restart deploy/app-x
```

### Phase 2-B. Switch to Pod Identity

```bash
# 1) Agent add-on (once per cluster)
aws eks create-addon --cluster-name $CLUSTER_NAME --addon-name eks-pod-identity-agent

# 2) Create the role: trust = pods.eks.amazonaws.com
aws iam create-role --role-name app-x --assume-role-policy-document file://podid-trust.json
aws iam put-role-policy --role-name app-x --policy-name app --policy-document file://app.json

# 3) Association
aws eks create-pod-identity-association --cluster-name $CLUSTER_NAME \
  --namespace app --service-account app-x --role-arn arn:aws:iam::<acct>:role/app-x

# 4) Restart
kubectl -n app rollout restart deploy/app-x
```

With Terraform or eksctl, manage the same thing declaratively via the `aws_eks_pod_identity_association` resource or eksctl `iam.podIdentityAssociations`. AWS managed add-ons (VPC CNI, EBS CSI and so on) can be linked through the pod identity association in the add-on configuration.

The Phase 2 principle is **remove the old path only after the new one works**. The node role keeps its permissions while workloads switch, so a missing permission on the new role does not cause an outage. In exchange, Phase 3 must confirm that the application really uses the new role.

### Phase 3. Verify and bake

| Check | How | Expected |
|---|---|---|
| Injection | `kubectl exec ... env \| grep ^AWS_` | IRSA: `AWS_WEB_IDENTITY_TOKEN_FILE`, Pod Identity: `AWS_CONTAINER_CREDENTIALS_FULL_URI` |
| Effective principal | `aws sts get-caller-identity` (or application logs) | New role ARN |
| Audit | `userIdentity.arn` of the service calls in CloudTrail | Node role calls converge to zero |
| Errors | `AccessDenied` in application logs | None (otherwise add permissions to the new role) |

If an old SDK does not recognize Pod Identity, it **silently falls back to IMDS and uses the node role** even though the env vars are injected. Judge by "the CloudTrail principal changed", not "the env vars are present".

### Phase 4. Lock down the node role

Proceed only after confirming every workload's CloudTrail principal has changed.

1. Remove application policies from the node role, leaving only the node baseline policies.
2. Block IMDS from Pods.
   - Launch template: `HttpTokens=required`, `HttpPutResponseHopLimit=1`, then roll the node group
   - eksctl: `disableIMDSv1: true`, `disablePodIMDS: true`
   - Additionally, block egress to `169.254.169.254/32` with a NetworkPolicy (does not apply to hostNetwork Pods)
3. Moving the VPC CNI (`aws-node`) to IRSA or Pod Identity lets you drop `AmazonEKS_CNI_Policy` from the node role as well.
4. Afterwards, prevent new workloads from re-adding permissions to the node role through IAM change permissions and IaC review.

Blocking IMDS can break controllers that **auto-discover the region and VPC ID** from metadata. For example, the AWS Load Balancer Controller needs explicit `--aws-region` and `--aws-vpc-id`. Find IMDS-dependent Pods during Phase 0.

### Rollback

| Step | Rollback |
|---|---|
| Phase 2 | Remove the annotation or delete the association → restart. The node role still has its permissions, so recovery is immediate |
| Phase 4 policy removal | Reattach the policy to the node role (allow for IAM propagation delay) |
| Phase 4 IMDS | Roll the node group back to the previous launch template version, or `modify-instance-metadata-options` |

## 7. Moving from IRSA to Pod Identity

Workloads already on IRSA switch without downtime using the same principle.

```text
 t0  IRSA only       trust: [OIDC]                SA: annotation      Pod env: WEB_IDENTITY
 t1  dual trust      trust: [OIDC, pods.eks]      SA: annotation      (no change)
 t2  association     + create-pod-identity-association                (no change: IRSA wins)
 t3  remove annot.   + rollout restart                                Pod env: CONTAINER_CREDENTIALS
 t4  after bake      trust: [pods.eks]  delete OIDC statement, clean up unused OIDC provider
```

At t2 the association exists but the annotation remains, so the SDK keeps using IRSA; the real switch happens at t3 when the annotation is removed and Pods restart. The demo's `06-irsa-to-pod-identity.sh` follows exactly this order.

## 8. Checklist

- [ ] Listed the application policies on the node role and the services it actually calls, using CloudTrail
- [ ] Flagged static-key Secrets, existing IRSA SAs and hostNetwork Pods separately
- [ ] Created a dedicated ServiceAccount and a least-privilege role per workload
- [ ] The SDK version supports the chosen mechanism (web identity / container credentials)
- [ ] Confirmed after switching that the CloudTrail principal is the new role
- [ ] Reduced the node role to the baseline policies
- [ ] Applied IMDSv2 required + hop limit 1 in the launch template and rolled the nodes
- [ ] Set the region and VPC ID explicitly on IMDS-dependent controllers
- [ ] Added IAM and IaC review rules that block adding permissions to the node role

## References

- [Amazon EKS: IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Amazon EKS: Learn how EKS Pod Identity grants pods access to AWS services](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Amazon EKS: Understand how EKS Pod Identity works](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)
- [Amazon EKS: Set up the EKS Pod Identity Agent](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-agent-setup.html)
- [Amazon EKS: Use pod identity with the AWS SDK (minimum SDK versions)](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
- [Amazon EKS: Grant pods access to AWS resources based on tags](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-abac.html)
- [EKS Best Practices Guide: Identity and Access Management](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)
- [Amazon EC2: Configure the instance metadata options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html)
- [AWS SDKs and Tools: Standardized credential providers](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
- Related chapters: [EKS Security Best Practices](./06-eks-security-best-practices.md), [Kubernetes Authentication and Authorization](./02-kubernetes-auth-authz.md)
