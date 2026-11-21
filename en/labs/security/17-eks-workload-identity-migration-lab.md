# EKS Workload IAM Migration Lab: From the Node Role to IRSA and Pod Identity

> **Difficulty**: Advanced
> **Estimated Time**: 40–60 minutes (about 30 minutes more with `harden`)
> **Supported Versions**: Verified on Amazon EKS 1.36, AWS CLI 2.35.11 (inside the Pods)
> **Last Updated**: November 21, 2026

## Learning Objectives

- Start with three copies of the same orders app that all use the node IAM role, then move one copy to IRSA and another to EKS Pod Identity.
- See for yourself how the injected environment variables, tokens and role trust policies differ between the two methods.
- Revoke the S3 permission from the node role, watch only the unmigrated Pod get denied, and observe the eventual consistency of IAM and associations.
- (Optional) Lower the IMDS hop limit to 1 to close the node-credential path for ordinary Pods.
- Use a server-side dry run to check what a new Pod receives when one ServiceAccount has both an IRSA annotation and a Pod Identity association.

This lab walks step by step through the [live demo](../../security/17-eks-workload-identity-migration.md#live-demo) in [Migrate EKS node IAM permissions to IRSA and Pod Identity](../../security/17-eks-workload-identity-migration.md). Read the workbook's [IRSA flow](../../security/17-eks-workload-identity-migration.md#irsa-flow) and [Pod Identity flow](../../security/17-eks-workload-identity-migration.md#pod-identity-flow) sections first.

## Time and Cost

| Step | Measured time | Notes |
| --- | --- | --- |
| `up` | 174 s (run `t1121`) | Mostly node group creation; 3–5 min depending on the environment |
| `migrate-irsa` | 6 s | |
| `migrate-podid` | 11 s | Includes 5 s until the association reached admission |
| `diff` | 8 s | Read-only |
| `revoke` | 13 s to the first `denied` | The command returns after 17–18 s |
| `harden` (optional) | 878 s | Rolling replacement of the node group |
| `restore` | 15 s; 578 s after `harden` | For repeated practice |
| `down` | 323 s (run `t1121`) | Mostly node group deletion |

The cost is mostly one t3.medium On-Demand instance (US$0.052 per hour in Seoul) and a 20 GiB gp3 volume. An hour of lab time costs about US$0.06; S3 requests and API calls are negligible. Always clean up with `down` when you finish.

## Prerequisites

- [ ] **An existing EKS cluster** (verified on 1.36). The script creates no cluster, VPC, subnet or security group. It assumes the common setup where the cluster's vpc-cni runs on the node role.
- [ ] **The `eks-pod-identity-agent` add-on** installed. The script only checks for it; it does not install it.
- [ ] The cluster issuer registered as an **IAM OIDC provider**. The script does not create this either.
- [ ] **Private subnets** in the cluster VPC and their Name tags. Only subnets with `MapPublicIpOnLaunch=false` are accepted; nodes pull `public.ecr.aws/aws-cli/aws-cli` through the VPC's existing NAT path.
- [ ] Tools: AWS CLI v2, kubectl, jq, bash, git.
- [ ] Permissions: credentials with EKS, EC2 (launch templates), IAM and S3 permissions plus cluster-admin access to the cluster. Use temporary credentials rather than long-lived access keys.

### Preflight Commands

```bash
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER> VPC_NAME=<Name tag of the cluster VPC> \
  SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>

aws sts get-caller-identity --query Arn --output text
aws eks describe-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent \
  --query addon.status --output text                       # ACTIVE
ISSUER=$(aws eks describe-cluster --name "$CLUSTER" \
  --query cluster.identity.oidc.issuer --output text | sed 's#^https://##')
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws iam get-open-id-connect-provider --open-id-connect-provider-arn \
  "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${ISSUER}" --query ClientIDList   # ["sts.amazonaws.com"]
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=$VPC_NAME" \
  --query 'Vpcs[0].VpcId' --output text)
aws eks describe-cluster --name "$CLUSTER" --query cluster.resourcesVpcConfig.vpcId --output text  # must equal $VPC_ID
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$SUBNET_NAMES" \
  --query 'Subnets[].[Tags[?Key==`Name`]|[0].Value,SubnetId,MapPublicIpOnLaunch]' --output table
```

Check that the add-on is `ACTIVE`, the OIDC provider lookup succeeds, the cluster VPC ID matches the VPC found by `VPC_NAME`, and every subnet shows `MapPublicIpOnLaunch` as `False`. If any of these fails, `up` stops before it creates anything.

### Code and Environment File

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs/examples/security/eks-workload-identity

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/eks-workload-identity-demo"
mkdir -p "$STATE_DIR"
cat > "$STATE_DIR/env" <<'EOF'
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER>
export VPC_NAME=<Name tag of the cluster VPC>
export SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>
EOF

export RUN_ID=lab01     # 4–12 lowercase letters or digits; goes into resource names wid-<RUN_ID>-*
export NS="wid-$RUN_ID"
export KUBECONFIG="$STATE_DIR/kubeconfig-$RUN_ID"   # the dedicated kubeconfig demo.sh writes
```

`demo.sh` sources this env file on every run, so `watch` in the second terminal uses the same values. The file is sourced after your shell variables, so a value in the file wins over a shell variable of the same name. When you run `kubectl` directly below, use the `KUBECONFIG` above so the commands cannot reach another cluster context. The file appears the first time you run `up`.

The commands and results the script prints mask the account ID, OIDC issuer ID, cluster name and launch template IDs as `<ACCOUNT_ID>`, `<OIDC_ID>`, `<CLUSTER>` and `<LAUNCH_TEMPLATE_ID>`. The expected outputs below are masked the same way. They come from rehearsals in the Seoul Region on November 21, 2026, and each block names its run ID (`d1124` or `t1121`). Your screen shows your own `RUN_ID` and timestamps.

## Step 0: Deploy the Lab Environment (`up`)

**Command** (terminal A)

```bash
./demo.sh up "$RUN_ID"
```

**Expected output** (measured, run `t1121`, 174 s)

```text
==> bucket and test object
==> node role (with the app's S3 permission, the legacy pattern)
==> IRSA and Pod Identity roles
==> creating node group wid-t1121 (3–5 min)
==> namespace, ServiceAccounts and three copies of the orders app
Waiting for deployment "orders-legacy" rollout to finish: 0 of 1 updated replicas are available...
deployment "orders-legacy" successfully rolled out
deployment "orders-irsa" successfully rolled out
deployment "orders-podid" successfully rolled out
==> ready. In a second terminal run: ./demo.sh watch t1121
```

**What to check**

```bash
./demo.sh status "$RUN_ID"
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `status` should show the node group as `ACTIVE t3.medium lt-version=1`, the inline policy `OrdersReadInvoices` on all three roles (`wid-<RUN_ID>-node`, `-irsa`, `-podid`), the bucket `present`, `pod-id 0 association(s)`, `irsa SA (not annotated)` and three Pods `Running`.
- The launch template's `MetadataOptions` are `HttpTokens: required`, `HttpPutResponseHopLimit: 2` and `HttpEndpoint: enabled`.

**Why.** `up` builds the same starting point as a production node group. IMDSv2 is required, but with hop limit 2 an ordinary Pod without host networking can still get an IMDS token and the node role's credentials, and that node role carries the app's `s3:GetObject`. The IRSA and Pod Identity roles are created up front but not yet linked to any ServiceAccount.

## Step 1: Check the Starting State (`watch`)

**Command** (terminal B, same directory)

```bash
export RUN_ID=lab01
./demo.sh watch "$RUN_ID"     # refreshes every 2 s; Ctrl-C to stop
```

**Expected screen** (measured, run `d1124`)

```text
04:11:37 EKS workload identity — <CLUSTER>/wid-d1124  (Ctrl-C to stop)

COPY            CREDENTIALS    ROLE                           S3        AT
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36
orders-irsa     node (IMDS)    wid-d1124-node  ← node       allowed   04:11:35
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36

node role: wid-d1124-node   bucket object: invoices/2026-11.txt
```

**What to check.** All three rows show `node (IMDS)`, `wid-<RUN_ID>-node ← node` and `allowed`, and the `AT` time moves every 3 seconds. The screen is drawn from the newest log line of each copy's newest Pod. You can read the raw JSON from terminal A:

```bash
kubectl -n "$NS" logs deploy/orders-legacy --tail=3
# format: {"t":"HH:MM:SS","src":"imds","role":"wid-<RUN_ID>-node","s3":"allowed"}
```

**Why.** None of the three Pods has injected credential variables, so the AWS CLI's default provider chain falls through to its last step, IMDS, and gets the node role. `app.sh` sets `src` from whether `AWS_WEB_IDENTITY_TOKEN_FILE` or `AWS_CONTAINER_CREDENTIALS_FULL_URI` is present, and takes the role name from the `sts get-caller-identity` ARN. It prints no tokens or keys.

## Step 2: Migrate to IRSA (`migrate-irsa`)

**Command** (terminal A)

```bash
./demo.sh migrate-irsa "$RUN_ID"
```

**Expected output** (measured, run `t1121`, 6 s)

```text
==> IRSA: point the ServiceAccount at its own role, then restart the copy
$ kubectl -n wid-t1121 annotate serviceaccount orders-irsa --overwrite eks.amazonaws.com/role-arn=arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-irsa
$ kubectl -n wid-t1121 rollout restart deployment/orders-irsa
$ kubectl -n wid-t1121 rollout status deployment/orders-irsa --timeout=180s
Waiting for deployment "orders-irsa" rollout to finish: 1 old replicas are pending termination...
deployment "orders-irsa" successfully rolled out
```

In terminal B the `orders-irsa` row changes to `IRSA (STS)`, `wid-<RUN_ID>-irsa`, `allowed`; the other two rows stay the same (measured, run `d1124`).

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:59
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:01
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:12:00
```

**Check it yourself.** See what changed in the Kubernetes objects.

```bash
# 1) The ServiceAccount annotation
kubectl -n "$NS" get sa orders-irsa \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'

# 2) Names of the environment variables the webhook added to the new Pod (no values)
POD=$(kubectl -n "$NS" get pod -l app=orders,track=irsa \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'

# 3) The projected token mount path
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].volumeMounts[*]}{.mountPath}{"\n"}{end}'
```

**What to check**

- The annotation is `arn:aws:iam::<ACCOUNT_ID>:role/wid-<RUN_ID>-irsa`.
- Next to the manifest's own `BUCKET`, `KEY`, `AWS_REGION` and so on, the variable list shows the webhook's `AWS_STS_REGIONAL_ENDPOINTS`, `AWS_ROLE_ARN` and `AWS_WEB_IDENTITY_TOKEN_FILE`.
- The mount paths now include `/var/run/secrets/eks.amazonaws.com/serviceaccount`.
- The `orders-legacy` and `orders-podid` Pods do not have these variables.

**Why.** The EKS mutating webhook reads the ServiceAccount's `eks.amazonaws.com/role-arn` annotation **when a Pod is created** and adds the variables and token volume. Running Pods do not change, so the script runs `rollout restart` right after annotating. In the new Pod the AWS CLI finds the web identity token provider, which comes before IMDS in the chain, and gets the IRSA role through STS `AssumeRoleWithWebIdentity`.

## Step 3: Migrate to Pod Identity (`migrate-podid`)

**Command** (terminal A)

```bash
./demo.sh migrate-podid "$RUN_ID"
```

**Expected output** (measured, run `t1121`, 11 s)

```text
==> Pod Identity: associate the ServiceAccount with its role in the EKS API, then restart
$ aws eks create-pod-identity-association --cluster-name <CLUSTER> --namespace wid-t1121 --service-account orders-podid --role-arn arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-podid --tags Lab=eks-workload-identity-demo\,LabRun=t1121 --query association.associationId --output text
==> waiting for the association change to reach Pod admission (eventually consistent)
    2s  not yet   injected after 5s
$ kubectl -n wid-t1121 rollout restart deployment/orders-podid
$ kubectl -n wid-t1121 rollout status deployment/orders-podid --timeout=180s
Waiting for deployment "orders-podid" rollout to finish: 1 old replicas are pending termination...
deployment "orders-podid" successfully rolled out
```

In terminal B the `orders-podid` row changes to `Pod Identity`, `wid-<RUN_ID>-podid`, `allowed` (measured, run `d1124`).

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:12:27
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:29
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:27
```

**Check it yourself**

```bash
# The association lives in the EKS API; the ServiceAccount has no annotation
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "$NS" \
  --query 'associations[].[serviceAccount,associationId]' --output text
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'

POD=$(kubectl -n "$NS" get pod -l app=orders,track=podid \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'
```

**What to check**

- There is one association, for `orders-podid`, and the ServiceAccount annotations are empty.
- The new Pod has `AWS_STS_REGIONAL_ENDPOINTS`, `AWS_CONTAINER_CREDENTIALS_FULL_URI` and `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`.
- `injected after Ns` in the output is the time from creating the association until admission injected it. It was 5 s in both rehearsals.

**Why wait for injection.** Associations are eventually consistent. In the first rehearsal a rollout right after creating the association produced a Pod without the Pod Identity variables, and that Pod kept using the node role. So the script sends the Deployment's Pod template through `kubectl create --dry-run=server` and rolls out only after the mutating webhook actually injects the variables. A server-side dry run stores nothing but goes through the same admission steps as a real Pod, which is exactly what this check needs.

## Step 4: Compare the Two Methods (`diff`)

**Command**

```bash
./demo.sh diff "$RUN_ID"
```

**Expected output** (measured, run `t1121`)

```text
1. What EKS injected into each new Pod (env var names)
  irsa   AWS_STS_REGIONAL_ENDPOINTS, AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
  podid  AWS_STS_REGIONAL_ENDPOINTS, AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE

2. The projected ServiceAccount token (claims only)
  irsa   {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["sts.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-irsa","lifetime_s":86400}
  podid  {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["pods.eks.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-podid","lifetime_s":79636}

3. Who each role trusts
  irsa             {"principal":{"Federated":"arn:aws:iam::<ACCOUNT_ID>:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>"},"action":"sts:AssumeRoleWithWebIdentity","conditions":["<issuer>:aud","<issuer>:sub"]}
  podid            {"principal":{"Service":"pods.eks.amazonaws.com"},"action":["sts:AssumeRole","sts:TagSession"],"conditions":["aws:RequestTag/eks-cluster-arn","aws:RequestTag/kubernetes-namespace","aws:RequestTag/kubernetes-service-account"]}

4. Where the SDK goes for credentials
  irsa   Pod → STS AssumeRoleWithWebIdentity (regional endpoint) → temporary credentials
  podid  Pod → Pod Identity Agent 169.254.170.23 on the node → EKS Auth AssumeRoleForPodIdentity → credentials
  legacy Pod → IMDSv2 169.254.169.254 → node role credentials

5. Wiring lives in
  irsa   ServiceAccount annotation + IAM OIDC provider + per-role trust on issuer/sub
  podid  EKS association (1 found) + one service principal trust, reusable across clusters
```

**Reading the output**

- **1**: Both methods add variables to the new Pod, with different names. IRSA passes the role ARN and a token file, and the SDK calls STS itself. Pod Identity passes no role ARN, only a credentials URI and an authorization token file; the association decides which role the Pod gets.
- **2**: Both tokens are ServiceAccount tokens signed by the same cluster issuer, with `sub` in the same format. The difference is `aud`: a `sts.amazonaws.com` token is accepted only by STS, a `pods.eks.amazonaws.com` token only by EKS Auth. The Pod Identity token lifetime varies by run because the webhook adds random jitter (measured 79,636 s and 86,171 s).
- **3**: The IRSA role trusts a per-cluster OIDC provider with `aud` and `sub` conditions, so its trust policy grows with each cluster. The Pod Identity role trusts one service principal with session-tag conditions, so it needs no trust policy change in another cluster.
- **4–5** are fixed summary text the script prints. Only `1 found` in item 5 is an actual association count.

**Why.** The difference between the two methods is who takes the token and turns it into a role. With IRSA the Pod goes to STS directly and STS verifies the signature through the OIDC provider. With Pod Identity the Agent on the same node asks EKS Auth, which finds the association and returns credentials with session tags.

## Step 5: Revoke the Node Role Permission (`revoke`)

**Command**

```bash
./demo.sh revoke "$RUN_ID"
```

**Expected output** (measured, run `t1121`, 13 s to the first `denied`)

```text
==> remove the app's S3 permission from the node role
$ aws iam delete-role-policy --role-name wid-t1121-node --policy-name OrdersReadInvoices
==> waiting for IAM to propagate: legacy copy should flip to denied
    1s  legacy still: allowed     5s  legacy still: allowed     9s  legacy still: allowed   legacy denied after 13s
  orders-irsa   allowed via wid-t1121-irsa
  orders-podid  allowed via wid-t1121-podid
```

Terminal B (measured, run `d1124`; the same right after `revoke` and 60 s later):

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       denied    04:12:56
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:58
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:58
```

**What to check**

- Only `orders-legacy` becomes `denied`, and its role is still the node role: it still gets credentials, but that role no longer has the permission.
- The IRSA and Pod Identity copies stay `allowed`, which proves they no longer depend on the node role's application permission.
- Check the logs for late `allowed` reads over the next few minutes.

```bash
kubectl -n "$NS" logs deploy/orders-legacy --since=10m | jq -r 'select(.s3=="allowed") | .t' | tail -n 3
```

**Why.** IAM policy changes propagate with eventual consistency. Both rehearsals saw the first denial after 13 s, but in the first rehearsal two more `allowed` reads appeared about 4.5 minutes later. `revoke` returns at the first `denied`, so in production keep watching for several minutes after removing a node policy before you decide.

## Step 6 (Optional): Close the IMDS Path (`harden`)

This takes about 15 minutes (878 s measured), so you can start it right after `revoke` and continue with Step 7.

**Command**

```bash
./demo.sh harden "$RUN_ID"
./demo.sh status "$RUN_ID"      # in another terminal: nodegroup UPDATING → ACTIVE
```

**Expected output** (measured, run `d1124`, 878 s). The script updates the node group to a new launch template version and prints a dot every 15 s until it finishes.

```text
==> block Pod access to IMDS on the demo node group (hop limit 1)
$ aws eks update-nodegroup-version --cluster-name <CLUSTER> --nodegroup-name wid-d1124 --launch-template id=<LAUNCH_TEMPLATE_ID>\,version=2 --query update.id --output text
...
deployment "orders-legacy" successfully rolled out
==> legacy copy now has no credentials at all; IRSA and Pod Identity are unaffected
```

The last log line of each copy after the replacement (measured, run `d1124`):

```text
legacy: {"t":"04:00:27","src":"imds","role":"no-credentials","s3":"no-creds"}
irsa: {"t":"04:00:26","src":"irsa","role":"wid-d1124-irsa","s3":"allowed"}
podid: {"t":"04:00:27","src":"pod-identity","role":"wid-d1124-podid","s3":"allowed"}
```

**What to check**

```bash
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `HttpPutResponseHopLimit` is `1` and `HttpEndpoint` is still `enabled`.
- `orders-legacy` gets no credentials at all (`no-credentials` / `no-creds`); the other two copies stay `allowed` on the new node.

**Why.** With hop limit 1 the IMDSv2 token response cannot cross from the node's network namespace into the Pod, so an ordinary Pod cannot get the node role's credentials. **Do not turn IMDS off (`HttpEndpoint=disabled`).** The Pod Identity Agent runs on the host network and gets the node role's credentials from IMDS to call EKS Auth; with IMDS off, `orders-podid` would lose its credentials too. hostNetwork Pods reach IMDS regardless of the hop limit, so control them separately.

Before `restore` or `down` after `harden`, wait until the node group is `ACTIVE` again. `restore` after `harden` rolls back to hop limit 2 and takes about 10 minutes (578 s measured).

## Step 7: Experiment — IRSA Annotation and Association Together

The workbook says that when one ServiceAccount has both an IRSA annotation and an association, the EKS webhook injects only the Pod Identity variables into new Pods. Check it yourself after Step 3. Do not create an association for `orders-irsa`: the script's `restore` and `down` delete only the `orders-podid` association, so it would be left behind. Instead, briefly add an IRSA annotation to `orders-podid`, which already has the association.

**7.1 A function that shows the injection result** — it sends the Deployment's Pod template through a server-side dry run, the same way `podid_injected()` in `demo.sh` does.

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

injected() { # deployment name
  kubectl -n "$NS" get deployment "$1" -o json |
    jq --arg n "probe-$RUN_ID" '{apiVersion:"v1",kind:"Pod",metadata:{name:$n},spec:.spec.template.spec}' |
    kubectl -n "$NS" create --dry-run=server -o json -f - |
    jq -r '[.spec.containers[0].env[]?.name
            | select(test("^AWS_(ROLE_ARN|WEB_IDENTITY_TOKEN_FILE|CONTAINER_)"))] | join(", ")'
}
```

**7.2 Baseline: a ServiceAccount with only the annotation, and one with only the association**

```bash
injected orders-irsa     # expected: AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
injected orders-podid    # expected: AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.3 Add an IRSA annotation to `orders-podid`, which has the association, and dry-run again**

```bash
kubectl -n "$NS" annotate sa orders-podid \
  "eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/wid-${RUN_ID}-irsa"
injected orders-podid    # expected: AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.4 Clean up: remove the annotation and do not roll out**

```bash
kubectl -n "$NS" annotate sa orders-podid eks.amazonaws.com/role-arn-
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'   # should be empty
```

**What to check.** If 7.3 shows only the Pod Identity variables and no `AWS_ROLE_ARN`, the result matches the workbook. The workbook's result was checked on the demo cluster while writing it, but no output log was saved, so the values above are expected values. Record what your cluster returns. A dry run creates no Pod, so the running `orders-podid` is not affected.

**Why.** For a ServiceAccount that has an association, the EKS webhook prefers the Pod Identity variables even when an IRSA annotation is present, and injects no IRSA variables. Conversely, if you add an association later, Pods that are **already running** keep their IRSA variables until they are recreated. So when you switch methods, recreate the Pods with a rollout and remove the unused annotation so the two configurations do not mix.

<!-- COORDINATOR: page-up/page-down are being added to demo.sh by a parallel change. Adjust command names, timings and prerequisites below once that change lands. -->
## Public Demo Page (Optional)

> This section describes a feature that is being added to `demo.sh`. If `page-up` is not in your script's `./demo.sh` help, skip it.

You can bring up a read-only status page the audience can open in a browser. It shows only each copy's credential source, role and S3 result, and has no controls that change anything. The path is CloudFront → CloudFront VPC origin → **internal** ALB → dashboard Pod, and the ALB security group admits only the CloudFront VPC-origin side. No internet-facing load balancer or public IP is created.

Add three values to the env file:

```bash
export PAGE_DOMAIN=<page host name>
export PAGE_CERT_ARN=<ACM certificate ARN in us-east-1 covering PAGE_DOMAIN>
export PAGE_ZONE_ID=<public hosted zone ID for PAGE_DOMAIN>
```

```bash
./demo.sh page-up "$RUN_ID"     # about 10 min
./demo.sh page-down "$RUN_ID"   # about 10 min; down runs this first
```

## Cleanup (`down`)

If you ran `harden`, first make sure the node group is `ACTIVE`. To practice again with the same RUN_ID, you can run `./demo.sh restore "$RUN_ID"` instead of `down` to return to the starting state.

**Command**

```bash
./demo.sh down "$RUN_ID"
```

**Expected output** (measured, run `t1121`, 323 s)

```text
==> deleted namespace
==> deleting node group (3–5 min)
==> deleted launch template
==> deleted role wid-t1121-node
==> deleted role wid-t1121-irsa
==> deleted role wid-t1121-podid
{
    "BucketArn": "arn:aws:s3:::wid-t1121-<ACCOUNT_ID>-ap-northeast-2",
    "BucketRegion": "ap-northeast-2",
    "AccessPointAlias": false
}
==> deleted bucket
==> done
```

The JSON in the middle is the output of the bucket check. It does not go through the screen masking, so your real account ID appears there; take care if you are sharing your screen.

**Check for leftovers.** `down` deletes the dedicated kubeconfig, so use the AWS CLI.

```bash
aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" 2>&1 | grep -c ResourceNotFound   # 1
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "wid-$RUN_ID" \
  --query 'length(associations)'                                                             # 0
for r in node irsa podid; do
  aws iam get-role --role-name "wid-$RUN_ID-$r" >/dev/null 2>&1 && echo "left: wid-$RUN_ID-$r"
done                                                                                          # no output
aws ec2 describe-launch-templates --filters "Name=tag:LabRun,Values=$RUN_ID" \
  --query 'LaunchTemplates[].LaunchTemplateName' --output text                               # empty
aws ec2 describe-instances --filters "Name=tag:LabRun,Values=$RUN_ID" \
  "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text                              # empty
aws s3api head-bucket --bucket "wid-$RUN_ID-$(aws sts get-caller-identity --query Account --output text)-$AWS_REGION" \
  2>&1 | grep -c 404                                                                         # 1
```

Also check with your usual kubeconfig that `kubectl get namespace wid-$RUN_ID` returns `NotFound`. If you brought up the public demo page, check that no CloudFront distribution or internal ALB is left. You can keep the env file for the next lab; delete `$STATE_DIR` if you no longer need it.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| Only the usage text (`Usage: ./demo.sh <command> RUN_ID`) appears | RUN_ID must be 4–12 lowercase letters or digits; no hyphens or capitals. |
| `set CLUSTER to an existing EKS cluster name` or similar | `CLUSTER`, `VPC_NAME` or `SUBNET_NAMES` is empty. Check the env file path and contents; env file values win over shell variables. |
| `cluster VPC is not <VPC_NAME>` | The VPC found by `VPC_NAME` is not the cluster VPC. Check the cluster VPC's Name tag again. |
| `private subnet '<name>' not found in <VPC_NAME>` | The subnet is not in the cluster VPC, or it is a public subnet with `MapPublicIpOnLaunch=true`. Use private subnet Name tags. |
| `eks-pod-identity-agent add-on is required` | Install it with `aws eks create-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent` and wait for `ACTIVE`. Coordinate with the cluster administrator. |
| `IAM OIDC provider for the cluster is required` | Register the cluster issuer as an IAM OIDC provider (for example `eksctl utils associate-iam-oidc-provider --cluster "$CLUSTER" --approve`). |
| `role ... is not tagged for run ...; refusing to modify it` | A role with the same name already exists without this lab's tags. Use a different RUN_ID. |
| `up` hangs at node group creation | Check `aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" --query nodegroup.health`. Without a NAT path from the private subnets, the node cannot join or pull the image. |
| `watch` keeps showing `starting` | The Pod is not `Running` yet or has no logs. Check with `kubectl -n "$NS" get pods` and `kubectl -n "$NS" describe pod`. |
| `association change not visible to admission within 120s` | Check that the association exists with `aws eks list-pod-identity-associations` and run `migrate-podid` again. If the association exists, it skips creation and goes straight to the injection check. |
| `orders-podid` still on the node role after `migrate-podid` | The Pod was created before injection. Check its variables with the Step 3 command; if they are missing, run `kubectl -n "$NS" rollout restart deploy/orders-podid` again. |
| `legacy copy did not flip within 180s` | IAM propagation is slow. Keep watching `watch`. Running `revoke` again reports the policy as already removed and only waits again. |
| S3 result is `error` | An error other than `AccessDenied` or missing credentials. Check the Pod's path to the STS and S3 endpoints (NAT, VPC endpoints, DNS). |
| Expected role but `denied` | Role identity and resource access are separate. Check the bucket policy, SCPs, permission boundaries and VPC endpoint policies. |

## References

- [Migrate EKS node IAM permissions to IRSA and Pod Identity](../../security/17-eks-workload-identity-migration.md) — the workbook for this lab
- [Demo code and presenter runbook](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity)
- [IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [How EKS Pod Identity works](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)
- [Managed node group launch templates](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)

## Next Steps

- Check your understanding with the [EKS workload IAM migration quiz](../../quizzes/security/17-eks-workload-identity-migration-quiz.md).
- Use the workbook's [production migration order](../../security/17-eks-workload-identity-migration.md) to plan dependency discovery and canary cutover for your real workloads.
