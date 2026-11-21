# EKS workload identity migration demo

A live demo for [security/17](../../../ko/security/17-eks-workload-identity-migration.md): three copies of one "orders" app read the same S3 object. All three start on the node instance profile. On stage you move one copy to IRSA and one to EKS Pod Identity, then remove the S3 permission from the node role and watch only the legacy copy lose access.

The script runs on an **existing** EKS cluster. It adds one tainted managed node group with its own node role, two workload roles, a private S3 bucket and a namespace, each named after the run ID or tagged `Lab=eks-workload-identity-demo` and `LabRun=<RUN_ID>`. The script changes or deletes only resources that match that name or tag; IAM roles, the bucket and the node group are checked for both tags before any change. It never creates a VPC, subnet, security group, cluster, add-on or IAM OIDC provider, opens no inbound ports and touches no other node group or Pod Identity association.

## Requirements

- An EKS cluster (tested on 1.36) with the `eks-pod-identity-agent` add-on and an IAM OIDC provider already registered for its issuer.
- Private subnets in the cluster's VPC, found by Name tag. Set `CLUSTER`, `VPC_NAME` and `SUBNET_NAMES` (no defaults), or put them in `~/.local/state/eks-workload-identity-demo/env`, which the script sources. Nodes pull `public.ecr.aws/aws-cli/aws-cli` through the VPC's existing NAT path.
- AWS CLI v2, kubectl, jq and bash on the presenter's machine; an identity with EKS, EC2 (launch templates), IAM and S3 permissions plus cluster-admin access to the cluster.
- Cost while it is up: one t3.medium On-Demand instance with a 20 GiB gp3 volume (about US$1.3 per day in Seoul at US$0.052 per hour), plus negligible S3 and API calls.

## Commands

```bash
cd examples/security/eks-workload-identity
export AWS_REGION=ap-northeast-2
export CLUSTER=<cluster> VPC_NAME=<vpc-name-tag> SUBNET_NAMES=<private-subnet-tag-1>,<private-subnet-tag-2>
RUN_ID=d1124

./demo.sh up      "$RUN_ID"   # before the talk, ~5 min
./demo.sh watch   "$RUN_ID"   # terminal 2: live table, refreshes every 2 s
./demo.sh migrate-irsa  "$RUN_ID"
./demo.sh migrate-podid "$RUN_ID"
./demo.sh diff    "$RUN_ID"
./demo.sh revoke  "$RUN_ID"
./demo.sh harden  "$RUN_ID"   # optional, rolls the node group (~15 min)
./demo.sh restore "$RUN_ID"   # back to the start (15 s; ~10 min if harden ran)
./demo.sh page-up   "$RUN_ID" # optional public read-only page for the audience (~10 min)
./demo.sh page-down "$RUN_ID" # remove it (down also does this)
./demo.sh down    "$RUN_ID"   # after the talk
```

`app.sh` is the loop inside each copy: every 3 seconds it calls `sts get-caller-identity` and `s3api get-object` with the AWS CLI's default credential chain and prints one JSON line (`src`, `role`, `s3`). It prints no credentials or tokens. `watch` reads the newest Pod of each copy. Commands echo what they run. Output masks the account ID, OIDC issuer ID, cluster name and launch template IDs so the screen is safe to project; set `MASK_CLUSTER=0` to show the cluster name and launch template IDs.

## Public read-only page (optional)

`page-up` gives the audience a live page in their own browsers. `dashboard.py` (stdlib only) and `dashboard.html` run as one Pod in the demo namespace. A background thread polls the Kubernetes API every 2 seconds for the newest Pod of each copy: its last `app.sh` line and the names of the injected `AWS_*` variables. Requests are served from memory with `Cache-Control: max-age=1`, so viewers never trigger API calls. The Pod's ServiceAccount has no AWS permissions; its Role can only list Pods and read their logs in this namespace.

Traffic path: viewer → CloudFront (HTTPS on `PAGE_DOMAIN`, GET/HEAD only, HTTP redirects to HTTPS) → CloudFront VPC origin → **internal** ALB (HTTP 80) → dashboard Pod. The ALB security group admits only the `CloudFront-VPCOrigins-Service-SG` of the VPC, or the CloudFront origin-facing managed prefix list if that group does not exist yet. There is no internet-facing load balancer and no public CIDR rule. Requires the AWS Load Balancer Controller. Set `PAGE_DOMAIN`, `PAGE_CERT_ARN` (ACM in us-east-1) and `PAGE_ZONE_ID` (public hosted zone) in the env file. Extra cost while up: about US$0.55 per day for the ALB, plus negligible CloudFront requests.

Measured on November 21, 2026: `page-up` took about 10 minutes (most of it the VPC origin and distribution deployments). The page followed every step: baseline (three `node (IMDS)` cards), IRSA, Pod Identity, then `revoke` with only the legacy card turning `denied`.

## Presenter runbook

| Step | Say | Run | Expect on the watch screen |
| --- | --- | --- | --- |
| 0 | "Today the app's S3 permission lives on the node role." Share the page URL. | (watch and the public page already running) | All three rows: `node (IMDS)`, `wid-<run>-node ← node`, `allowed` |
| 1 | "IRSA: annotate the ServiceAccount, restart." | `migrate-irsa` (~6 s) | `orders-irsa` → `IRSA (STS)`, `wid-<run>-irsa`, `allowed` |
| 2 | "Pod Identity: one EKS API call, no annotation." | `migrate-podid` (~11 s) | `orders-podid` → `Pod Identity`, `wid-<run>-podid`, `allowed` |
| 3 | "Same outcome, different wiring." | `diff` | Injected env vars, token `aud` (`sts.amazonaws.com` vs `pods.eks.amazonaws.com`), trust principals |
| 4 | "Now remove the permission from the node." | `revoke` (~15 s) | `orders-legacy` → `denied`; the other two stay `allowed` |
| 5 (optional) | "Close the IMDS path for Pods." | start `harden` right after step 4, show `status` → `UPDATING`, explain the result from the rehearsal | after ~15 min: `orders-legacy` → `no-credentials` / `no-creds`; the other two stay `allowed` |
| after | — | `restore` | Back to step 0 |

Notes from rehearsals:

- **Pod Identity associations are eventually consistent.** `migrate-podid` dry-runs the Deployment's Pod template against the API server (`--dry-run=server`, which runs the mutating webhooks) until EKS injects the Pod Identity variables, and only then restarts the copy. Restarting too early yields a Pod that still uses the node role.
- **IAM removal is eventually consistent too.** `revoke` returns at the first `denied`. In rehearsals the legacy copy was denied after about 13 seconds; in the first rehearsal two `allowed` reads still appeared about 4.5 minutes later. Say so on stage.
- **`harden` is too slow to run live.** It creates a launch template version with hop limit 1 and rolls the managed node group (surge node, drain, terminate): 878 seconds in rehearsal. Never run it before the talk on the live RUN_ID (step 0 would already show `no-credentials`). Start it right after `revoke`, move on, and check the watch screen at the end if time allows. Wait for the node group to be `ACTIVE` again before `restore` (another roll back to hop limit 2) or `down`.

## Measured run

Second rehearsal on November 21, 2026, run end to end with the current script (EKS 1.36, ap-northeast-2, AWS CLI 2.35.11 in the Pods). `harden` and `restore` after `harden` come from the first rehearsal.

| Step | Time | Result |
| --- | --- | --- |
| `up` | about 5 min | three copies on the node role, all `allowed` |
| `migrate-irsa` | 6 s | IRSA copy on `wid-<run>-irsa`, token `aud sts.amazonaws.com`, lifetime 86,400 s |
| `migrate-podid` | 11 s | Pod Identity copy on `wid-<run>-podid`, token `aud pods.eks.amazonaws.com`; the new association became visible to admission after 5 s |
| `revoke` | 13 s to first `denied` (same in the first rehearsal) | legacy `denied`, the other two `allowed` |
| `harden` | 878 s | legacy `no-credentials`, the other two `allowed` |
| `restore` without `harden` | 15 s | back to the start |
| `restore` after `harden` | 578 s | back to the start |

The final watch screen after `revoke`:

```text
COPY            CREDENTIALS    ROLE                           S3        AT
orders-legacy   node (IMDS)    wid-d1124-node  ← node       denied    04:12:56
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:58
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:58
```
