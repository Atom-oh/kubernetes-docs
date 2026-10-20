# EKS launch prerequisites

This is the historical GPU launcher described in the
[experiment README](../../README.md). Its pinned runtime remains blocked until
the supported image, dependencies and MLflow pairing have been upgraded and
validated together. Setting network variables does not bypass that guard.
The instructions below document preparation, not a completed EKS deployment.

## Approved existing VPC

Demo workloads must use the administrator-approved existing `fsi-demo-vpc`
in `ap-northeast-2`. Do not create a replacement VPC or choose another VPC
because its name happens to match. Confirm its account and ID against the
administrator's approval, and confirm that its account matches the experiment
inventory. Both supplied subnets must belong to that VPC and be the approved
private subnets in the indicated availability zones.

Replace each placeholder with an administrator-verified existing resource ID:

```bash
export DEMO_VPC_ID="vpc-REPLACE_WITH_APPROVED_DEMO_VPC"
export DEMO_PRIVATE_SUBNET_A="subnet-REPLACE_WITH_PRIVATE_SUBNET_IN_AP_NORTHEAST_2A"
export DEMO_PRIVATE_SUBNET_B="subnet-REPLACE_WITH_PRIVATE_SUBNET_IN_AP_NORTHEAST_2B"
```

All three variables must be nonempty. [run.sh](run.sh) exports and substitutes
them into [cluster.yaml](cluster.yaml); eksctl receives an existing VPC ID and
two private subnet IDs rather than creating a new VPC. The launcher checks
that values are present; it does not verify the VPC name, subnet membership,
routes or connectivity before creation. The operator must perform those
checks separately.

## Private nodes and API access

`managedNodeGroups[].privateNetworking: true` selects private subnets for the
GPU nodes. It does not set the separate Kubernetes API endpoint access options
in `vpc.clusterEndpoints`, create VPC endpoints, or provide internet egress.
This template does not configure those API endpoint access options.

Before an authorized run, verify:

- VPC DNS support and hostnames, subnet address capacity, route tables and
  security groups for the selected private subnets.
- A permitted path from nodes and the management host to the Kubernetes API.
  Review private API access and any public API CIDR restrictions separately;
  the management host must still be able to use kubectl and Helm.
- Approved HTTPS connectivity for ECR image pulls, S3 inputs and EKS Pod
  Identity. If using VPC endpoints, verify the required service names in Seoul,
  private DNS, endpoint client security groups, routes and endpoint policies.
- Approved access to the other current dependencies: the MLflow image comes
  from `ghcr.io`, the training Job installs Python packages with pip, and the
  trainer loads its model and tokenizer. The management host also fetches the
  NVIDIA Helm chart. Provide approved NAT/egress or prepared private
  image/package/model/chart mirrors and configure the consumers to use them.
  AWS VPC endpoints alone do not supply those external dependencies.

The [private endpoint example](../../../../security/eks-security/private-endpoints/README.md)
documents inputs for endpoint resources. It does not supply every prerequisite
of this launcher or establish that the demo VPC is reachable.

## Ownership and recovery

Preserve the private resource inventory and execution journal. An existing
shared VPC or subnet is not an experiment resource to delete. The launcher
refuses preexisting cluster/stack/role collisions, records creation intent,
and grants cleanup ownership only after the cluster and stack identities are
confirmed. Deletion requires the matching verified private export and
rechecks recorded ownership. Partial or unknown creation and failed export or
deletion require recovery; the launcher does not erase that evidence.

Local manifest/schema and mocked lifecycle tests do not demonstrate live DNS,
network reachability, GPU training or successful cleanup in the selected VPC.
