# EKS workload identity migration demo

Run on a disposable commercial AWS account or lab environment. The script creates a dedicated EKS 1.35 cluster, one Amazon Linux 2023 EC2 managed node, a VPC and network address translation (NAT) gateway, the Pod Identity Agent, an IAM OpenID Connect (OIDC) provider, two workload IAM roles, and a private S3 bucket with one text object. EKS, EC2, Amazon Elastic Block Store (EBS), NAT and public IPv4 charges accrue until cleanup.

Requirements include AWS CLI v2, current eksctl, kubectl compatible with EKS 1.35, curl, jq, Python 3 and ripgrep. Use an AWS identity authorized to provision the lab through EKS, CloudFormation, EC2, IAM and S3, including `iam:PassRole` for roles passed to EKS. Use the same AWS account, region and run ID for every step. The EKS public API accepts the creating host's single IPv4 address. Its nodes use private subnets with NAT.

```bash
cd examples/security/eks-workload-identity
export AWS_REGION=ap-northeast-2
RUN_ID="$(date -u +%y%m%d%H%M%S)"
# Optional if the automatic public IP lookup is unsuitable:
# export API_CIDR=203.0.113.42/32
./demo.sh config "$RUN_ID" | eksctl create cluster --dry-run -f -
./demo.sh create "$RUN_ID"
./demo.sh compare "$RUN_ID"
./demo.sh delete "$RUN_ID"
```

Record the run ID before provisioning. If creation or comparison fails, execute `delete` with that ID before starting a fresh run. The comparison creates one-shot Job names, ServiceAccounts and tagged IAM roles. The script verifies cluster ownership tags before mutating node permissions. If cleanup reports an error, address it and rerun `delete`.

## Verified comparison

Measured on November 20, 2026 on EKS 1.35 in the Seoul Region, using AWS CLI 2.35.11.

| Stage | Legacy | IRSA | Pod Identity |
| --- | --- | --- | --- |
| Before node permission removal | Node role / allowed | IRSA role / allowed | Pod Identity role / allowed |
| After node permission removal | Node role / denied | IRSA role / allowed | Pod Identity role / allowed |

All Jobs issue `sts:GetCallerIdentity` and `s3:GetObject` for the same fixture. The legacy Job uses host networking to reach IMDSv2 intentionally. The workload Jobs use regular pod networking and disable SDK fallback to IMDS. The IAM policy grants access to the one object ARN. Cleanup removes the lab bucket and its fixture along with the cluster and its supporting resources.

The Job output prints the caller ARN within the cluster. The comparison script checks it against the expected account and IAM role and prints a role label and the S3 result. It treats networking or credential acquisition errors as failures. The demonstration assumes there are no additional account policies granting or restricting access to the fixture.
