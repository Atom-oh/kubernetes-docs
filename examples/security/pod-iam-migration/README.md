# Node instance profile → IRSA / EKS Pod Identity migration demo

Companion to `ko|en/security/17-eks-pod-iam-migration.md`. One workload is
deployed three times; only the identity wiring differs, so you can compare the
three mechanisms side by side and then close the node-role leak.

| Namespace | Identity after migration | What the demo shows |
|---|---|---|
| `demo-node` | node instance profile (via IMDS) | legacy state, kept to show the lockdown effect |
| `demo-irsa` | IRSA (`eks.amazonaws.com/role-arn` annotation) | OIDC trust + `AssumeRoleWithWebIdentity` |
| `demo-podid` | EKS Pod Identity association | agent on `169.254.170.23` + `AssumeRoleForPodIdentity` |
| `default/neighbor` | nothing granted | inherits the node role until step 5 |

> These scripts were written and syntax-checked but **not run against a live
> account** in the authoring session. Run them in a sandbox account first; they
> create IAM roles, an S3 bucket and modify node IMDS options.

## Prerequisites

- An EKS cluster with an EC2 managed node group (Linux). `cluster.yaml` creates one with eksctl.
  Pod Identity is not available on Fargate.
- `aws` CLI v2, `kubectl`, `eksctl`, `python3`; credentials that can manage IAM, EKS and EC2.
- `kubectl` context pointing at the cluster.

## Run

```bash
export CLUSTER_NAME=pod-iam-demo AWS_REGION=ap-northeast-2 NODEGROUP_NAME=ng-default
# eksctl create cluster -f cluster.yaml          # optional, ~15 min

./01-baseline.sh             # S3 permission on the NODE role, deploy 3 namespaces + neighbor
./04-verify.sh               # every pod = node role, neighbor can read S3
./02-irsa.sh                 # demo-irsa -> IRSA
./03-pod-identity.sh         # demo-podid -> Pod Identity
./04-verify.sh               # three different identities
./05-lockdown-node-role.sh   # remove legacy policy, IMDS hop limit 1
./04-verify.sh               # demo-node + neighbor DENIED, IRSA/Pod Identity still ALLOWED
./06-irsa-to-pod-identity.sh # optional: IRSA -> Pod Identity, dual trust first
./99-cleanup.sh
```

Expected `04-verify.sh` output after step 5:

```text
=== demo-node   deploy/whoami
mechanism : (none injected) -> IMDS / node role
identity  : Unable to locate credentials ...
s3 ls     : DENIED
IMDS      : BLOCKED
=== demo-irsa   deploy/whoami
mechanism : IRSA
identity  : arn:aws:sts::111122223333:assumed-role/pod-iam-demo-irsa-s3-reader/botocore-session-...
s3 ls     : ALLOWED
=== demo-podid  deploy/whoami
mechanism : Pod Identity
identity  : arn:aws:sts::111122223333:assumed-role/pod-iam-demo-podid-s3-reader/eks-pod-iam-...
s3 ls     : ALLOWED
=== default     neighbor
mechanism : (none injected) -> IMDS / node role
s3 ls     : DENIED
```

## Files

- `policies/` — S3 read policy, IRSA trust template, Pod Identity trust, ABAC policy using
  Pod Identity session tags (`${aws:PrincipalTag/kubernetes-namespace}`).
- `manifests/` — workload template, neighbor pod, optional NetworkPolicy that denies
  `169.254.169.254/32` (does not cover hostNetwork pods).
- `queries/cloudtrail-node-role-usage.sql` — CloudTrail Lake query to inventory which
  APIs are called with the node role before you remove anything.

## Notes

- Step 5 changes IMDS options on **running** instances only. Make it persistent in the
  launch template (`MetadataOptions.HttpPutResponseHopLimit: 1`, `HttpTokens: required`)
  and roll the node group. Pods that still need instance metadata (for example
  controllers that auto-discover region/VPC ID) must be given explicit values first.
- Env vars and projected tokens are injected at pod creation: every identity change
  needs a pod restart.
