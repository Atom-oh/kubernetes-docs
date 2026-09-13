# Getting Started with Auto Mode

> **Supported Versions**: EKS Auto Mode GA; example baseline EKS 1.36
> **Last Updated**: September 12, 2026

This chapter covers new-cluster creation and enabling Auto Mode on an existing cluster. Choose **one** creation method; running all three creates separate billed infrastructure. Use the existing-cluster section only for the cluster you intend to modify.

The examples use the commercial Seoul region and reviewed, pre-created IAM roles. They were checked with eksctl 0.229.0, Terraform 1.15.7/AWS provider 6.64.0, and CDK 2.269.0/constructs 10.5.0 using local validation and synthesis. **No live cluster was created or migrated during this audit.** IAM/SCP permissions, quotas, routing, instance availability and workload compatibility still need environment-specific verification. These examples are not a tested production deployment.

EKS 1.36 is in standard support on the review date. The original Auto Mode feature floor of 1.29 does not establish current EKS support eligibility. Check the AWS version calendar before running an example. `STANDARD` upgrade policy allows automatic upgrade after standard support ends; it does not stop billing.

## Prerequisites and IAM Roles

Use temporary role credentials, AWS CLI v2, kubectl compatible with EKS 1.36, Bash, Python 3 and jq. Have an administrator approve the following distinct roles and the caller's provisioning/PassRole permissions:

| Role | Trust and permissions |
|------|-----------------------|
| Cluster role | Trust `eks.amazonaws.com` for `sts:AssumeRole` and `sts:TagSession`. Current AWS guidance recommends `AmazonEKSClusterPolicy`, `AmazonEKSComputePolicy`, `AmazonEKSBlockStoragePolicyV2`, `AmazonEKSLoadBalancingPolicy` and `AmazonEKSNetworkingPolicy` |
| Auto Mode node role | Trust `ec2.amazonaws.com`; attach `AmazonEKSWorkerNodeMinimalPolicy` and `AmazonEC2ContainerRegistryPullOnly` |
| Workload role | Separate application permissions, for example through EKS Pod Identity; do not put application permissions in the node role |

The existing cluster role ARN cannot be replaced when enabling Auto Mode; update its approved policies/trust through its owning IaC workflow. Do not overwrite a shared trust policy blindly. The code below consumes reviewed roles and does not create them. Existing volumes may need additional migration checks before changing a storage policy.

Auto Mode provides its Pod Identity agent functionality; an IAM OIDC provider is not required just to enable Auto Mode. Configure OIDC separately if your applications use IRSA.

### Common account and local context

Set the required environment variables to approved real values. For a new cluster, choose a unique name; for an existing cluster, verify its identity and ownership. Run the remaining commands in this dedicated Bash session. Keep the generated directory private.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the approved account ID}"
: "${CLUSTER_NAME:?Set a unique new name, or the approved existing cluster name}"
: "${AUTO_CLUSTER_ROLE_ARN:?Set the reviewed EKS cluster role ARN}"
: "${AUTO_NODE_ROLE_ARN:?Set the reviewed Auto Mode node role ARN}"
: "${API_CLIENT_CIDR:?Set the approved public client IPv4 CIDR}"
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
test "$AWS_REGION" = ap-northeast-2 || { printf 'This concrete example uses Seoul subnets/AZs; adapt it before using another region.\n' >&2; exit 1; }
export AWS_DEFAULT_REGION="$AWS_REGION"
export EXPECTED_ACCOUNT_ID CLUSTER_NAME AUTO_CLUSTER_ROLE_ARN AUTO_NODE_ROLE_ARN API_CLIENT_CIDR
python3 - <<'PY'
import ipaddress, os, re
account = os.environ["EXPECTED_ACCOUNT_ID"]
if not re.fullmatch(r"[0-9]{12}", account):
    raise SystemExit("Invalid account")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", os.environ["CLUSTER_NAME"]):
    raise SystemExit("Invalid cluster name")
for key in ("AUTO_CLUSTER_ROLE_ARN", "AUTO_NODE_ROLE_ARN"):
    if not re.fullmatch(r"arn:aws:iam::" + account + r":role/[A-Za-z0-9+=,.@_/-]+", os.environ[key]):
        raise SystemExit("Role account/ARN mismatch: " + key)
network = ipaddress.ip_network(os.environ["API_CLIENT_CIDR"], strict=True)
if network.version != 4 or network.prefixlen < 24:
    raise SystemExit("Use a reviewed /24 or narrower IPv4 CIDR")
PY
check_account() {
  local account
  account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$account" = "$EXPECTED_ACCOUNT_ID" || { printf 'Wrong AWS account; stop.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-mode.XXXXXXXX")
export KUBECONFIG="$WORK_DIR/kubeconfig"
printf 'Private evidence/config directory: %s\n' "$WORK_DIR"
```

## Creating a New Cluster

### eksctl with approved private subnets

This example reuses a reviewed VPC and two private subnets in distinct AZs. Set `VPC_ID`, `PRIVATE_SUBNET_A` and `PRIVATE_SUBNET_B` first. Confirm the subnet route tables provide the required outbound service/image access through NAT or appropriate endpoints. `MapPublicIpOnLaunch=false` alone does not prove a subnet has private routing.

The selected private subnets are also the cluster subnets. This matters because the default Auto Mode NodeClass inherits cluster subnet selection; a generic eksctl-created cluster with public cluster subnets can launch Auto Mode nodes there.

```bash
# Use approved PRIVATE subnets in the same VPC and at least two AZs.
: "${VPC_ID:?Set the approved VPC ID}"
: "${PRIVATE_SUBNET_A:?Set the first private subnet ID}"
: "${PRIVATE_SUBNET_B:?Set the second private subnet ID in another AZ}"
export VPC_ID
check_account
aws ec2 describe-subnets --region "$AWS_REGION" \
  --subnet-ids "$PRIVATE_SUBNET_A" "$PRIVATE_SUBNET_B" > "$WORK_DIR/subnets.json"
python3 - <<'PY'
import json, os
from pathlib import Path
out = Path(os.environ["WORK_DIR"])
subnets = json.loads((out / "subnets.json").read_text())["Subnets"]
if len(subnets) != 2 or len({s["AvailabilityZone"] for s in subnets}) != 2:
    raise SystemExit("Two subnets in distinct AZs are required")
if not all(s["VpcId"] == os.environ["VPC_ID"] and
           s["OwnerId"] == os.environ["EXPECTED_ACCOUNT_ID"] and
           s["State"] == "available" and not s["MapPublicIpOnLaunch"] for s in subnets):
    raise SystemExit("Subnet account/VPC/state/public-IP settings do not match")
config = {
    "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
    "metadata": {"name": os.environ["CLUSTER_NAME"], "region": os.environ["AWS_REGION"], "version": "1.36"},
    "accessConfig": {"authenticationMode": "API"},
    "upgradePolicy": {"supportType": "STANDARD"},
    "iam": {"serviceRoleARN": os.environ["AUTO_CLUSTER_ROLE_ARN"], "withOIDC": False},
    "autoModeConfig": {"enabled": True, "nodePools": ["general-purpose", "system"],
                       "nodeRoleARN": os.environ["AUTO_NODE_ROLE_ARN"]},
    "vpc": {"id": os.environ["VPC_ID"],
            "controlPlaneSubnetIDs": [s["SubnetId"] for s in subnets],
            "subnets": {"private": {s["AvailabilityZone"]: {"id": s["SubnetId"]} for s in subnets}},
            "clusterEndpoints": {"publicAccess": True, "privateAccess": True},
            "publicAccessCIDRs": [os.environ["API_CLIENT_CIDR"]]}
}
(out / "cluster.json").write_text(json.dumps(config, indent=2) + "\n")
PY
# REVIEW cluster.json and routes/permissions first. Creates billed EKS resources.
check_account
eksctl create cluster --config-file "$WORK_DIR/cluster.json" \
  --write-kubeconfig=false --timeout=45m
```

`autoModeConfig.nodePools` is valid in the current eksctl schema. Enabling Auto Mode through eksctl coordinates compute, load balancing and block storage, and the supplied node role is used for the default pools. The resulting kubeconfig is created in the verification section.

If creation fails, keep the configuration and inspect the named CloudFormation stacks. A timeout is not evidence that no resources were created. Reconcile ownership and partial resources before retrying or deleting anything.

### Terraform

Save the following as `main.tf` in a dedicated directory. This method creates a VPC with one billed NAT gateway, a lab availability/cost choice rather than per-AZ NAT redundancy. Adapt CIDRs and AZs to avoid conflicts before use.

The example pins EKS module 21.25.0 and VPC module 5.21.0. The EKS module requires AWS provider **6.59 or later**; keep the generated dependency lock file. Version 21.25.0 still attaches the earlier `AmazonEKSBlockStoragePolicy` when creating its own cluster role, so this example supplies the reviewed roles from the prerequisites. It uses EKS's default API-data encryption rather than creating a separate customer-managed KMS key.

```hcl
terraform {
  required_version = ">= 1.5.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.59, < 7.0"
    }
  }
}

variable "expected_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "Set the intended 12-digit AWS account."
  }
}
variable "cluster_name" { type = string }
variable "auto_cluster_role_arn" { type = string }
variable "auto_node_role_arn" { type = string }
variable "api_client_cidr" {
  type = string
  validation {
    condition = can(cidrnetmask(var.api_client_cidr)) && try(
      tonumber(split("/", var.api_client_cidr)[1]) >= 24, false
    )
    error_message = "Use an approved narrow IPv4 CIDR (/24 through /32)."
  }
}

provider "aws" {
  region              = "ap-northeast-2"
  allowed_account_ids = [var.expected_account_id]
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.21.0"
  name    = "${var.cluster_name}-vpc"
  cidr    = "10.0.0.0/16"

  azs                  = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
  private_subnets      = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets       = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true
  public_subnet_tags   = { "kubernetes.io/role/elb" = "1" }
  private_subnet_tags  = { "kubernetes.io/role/internal-elb" = "1" }
}

module "eks" {
  source             = "terraform-aws-modules/eks/aws"
  version            = "21.25.0"
  name               = var.cluster_name
  kubernetes_version = "1.36"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets

  endpoint_public_access                   = true
  endpoint_private_access                  = true
  endpoint_public_access_cidrs             = [var.api_client_cidr]
  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = true # Dedicated lab creator only.
  upgrade_policy                           = { support_type = "STANDARD" }

  # Reviewed pre-created roles: this module release still attaches the older
  # AmazonEKSBlockStoragePolicy when it creates the cluster role itself.
  create_iam_role      = false
  iam_role_arn         = var.auto_cluster_role_arn
  create_node_iam_role = false
  compute_config = {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = var.auto_node_role_arn
  }
  # EKS default API-data encryption; no separate customer-managed KMS key here.
  create_kms_key    = false
  encryption_config = null
  enable_irsa       = false # Pod Identity does not require a cluster OIDC provider.
  tags              = { Environment = "lab", Terraform = "true" }
}

output "cluster_endpoint" { value = module.eks.cluster_endpoint }
output "cluster_name" { value = module.eks.cluster_name }
```

The module's `compute_config` input coordinates its corresponding EKS compute, storage and load-balancing resource blocks. It is different from the old module-v20 `cluster_compute_config` name. Creator administrator access is explicit here for the dedicated lab; define narrower, reviewed access entries for production.

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
fields = {"expected_account_id": "EXPECTED_ACCOUNT_ID", "cluster_name": "CLUSTER_NAME",
          "auto_cluster_role_arn": "AUTO_CLUSTER_ROLE_ARN", "auto_node_role_arn": "AUTO_NODE_ROLE_ARN",
          "api_client_cidr": "API_CLIENT_CIDR"}
(Path(os.environ["WORK_DIR"]) / "terraform.tfvars.json").write_text(
    json.dumps({key: os.environ[value] for key, value in fields.items()}, indent=2) + "\n")
PY
check_account
terraform init
terraform validate
terraform plan -var-file="$WORK_DIR/terraform.tfvars.json" -out="$WORK_DIR/tfplan"
# REVIEW the saved plan; this applies billed infrastructure changes.
terraform apply "$WORK_DIR/tfplan"
```

### AWS CDK

Use this stack in a CDK application targeting the approved account and `ap-northeast-2`. Supply `ClusterName`, `ClusterRoleArn`, `NodeRoleArn`, `OperatorRoleArn` and `ApiClientCidr` as CloudFormation parameters. The operator parameter must be the reviewed IAM role whose credentials you will use with kubectl, not an STS assumed-role session ARN.

This uses an actual **L1 `eks.CfnCluster`**. Casting the original `eks.Cluster` L2 construct's `defaultChild` to `CfnCluster` does not turn its custom resource into an `AWS::EKS::Cluster` or reliably configure Auto Mode. Here all three Auto Mode capabilities, API access and the node role are explicit. An access entry grants the reviewed lab operator Kubernetes administrator access; bootstrap access for the CloudFormation execution identity is disabled. Replace this lab-wide grant with appropriate access scopes for production. The referenced IAM roles are outside this stack's lifecycle.

```typescript
import * as cdk from 'aws-cdk-lib/core';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as eks from 'aws-cdk-lib/aws-eks';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    // Pre-created, reviewed roles; see the IAM prerequisites in this chapter.
    const clusterRole = new cdk.CfnParameter(this, 'ClusterRoleArn', { type: 'String' });
    const nodeRole = new cdk.CfnParameter(this, 'NodeRoleArn', { type: 'String' });
    const operatorRole = new cdk.CfnParameter(this, 'OperatorRoleArn', {
      type: 'String',
      allowedPattern: '^arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$',
      constraintDescription: 'The reviewed lab operator IAM role ARN, not an STS session ARN',
    });
    const clientCidr = new cdk.CfnParameter(this, 'ApiClientCidr', {
      type: 'String',
      allowedPattern: '^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}/(?:2[4-9]|3[0-2])$',
      constraintDescription: 'An approved narrow IPv4 CIDR (/24 through /32)',
    });
    const clusterName = new cdk.CfnParameter(this, 'ClusterName', { type: 'String' });
    const vpc = new ec2.Vpc(this, 'EksVpc', {
      maxAzs: 3,
      natGateways: 1, // Lab tradeoff: billed, and not per-AZ NAT redundancy.
      subnetConfiguration: [
        { cidrMask: 24, name: 'Public', subnetType: ec2.SubnetType.PUBLIC },
        { cidrMask: 24, name: 'Private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      ],
    });
    for (const subnet of vpc.publicSubnets) {
      cdk.Tags.of(subnet).add('kubernetes.io/role/elb', '1');
    }
    for (const subnet of vpc.privateSubnets) {
      cdk.Tags.of(subnet).add('kubernetes.io/role/internal-elb', '1');
    }
    // An actual L1 AWS::EKS::Cluster, not an L2 defaultChild cast.
    const cluster = new eks.CfnCluster(this, 'EksAutoModeCluster', {
      name: clusterName.valueAsString,
      version: '1.36',
      roleArn: clusterRole.valueAsString,
      accessConfig: {
        authenticationMode: 'API',
        bootstrapClusterCreatorAdminPermissions: false,
      },
      resourcesVpcConfig: {
        subnetIds: vpc.privateSubnets.map(subnet => subnet.subnetId),
        endpointPrivateAccess: true,
        endpointPublicAccess: true,
        publicAccessCidrs: [clientCidr.valueAsString],
      },
      computeConfig: {
        enabled: true,
        nodePools: ['general-purpose', 'system'],
        nodeRoleArn: nodeRole.valueAsString,
      },
      kubernetesNetworkConfig: { elasticLoadBalancing: { enabled: true } },
      storageConfig: { blockStorage: { enabled: true } },
      upgradePolicy: { supportType: 'STANDARD' },
    });
    // CloudFormation's execution role may differ from the interactive operator.
    new eks.CfnAccessEntry(this, 'LabOperatorAccess', {
      clusterName: cluster.ref,
      principalArn: operatorRole.valueAsString,
      type: 'STANDARD',
      accessPolicies: [{
        policyArn: cdk.Fn.sub('arn:${AWS::Partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy'),
        accessScope: { type: 'cluster' }, // Explicit, reviewed admin access for this lab only.
      }],
    });
    new cdk.CfnOutput(this, 'ClusterNameOutput', { value: cluster.ref });
    new cdk.CfnOutput(this, 'ClusterEndpoint', { value: cluster.attrEndpoint });
  }
}
```

Instantiate `EksAutoModeStack` from your CDK app, with the intended account/region in `StackProps.env`. Review `cdk synth`/`cdk diff` before an authorized deployment. The local audit compiled this TypeScript and checked the synthesized cluster properties; it did not execute `cdk deploy`.

## Enabling Auto Mode on an Existing Cluster

Enabling Auto Mode and moving workloads onto its nodes are separate operations. Before proceeding:

- Use the owning Terraform/CDK/eksctl configuration if IaC manages the cluster; avoid unmanaged drift.
- Verify the existing cluster role has the Auto Mode permissions and `sts:TagSession` trust above. The sample verifies that its ARN matches the role you reviewed.
- Check current compatible versions of installed add-ons against the [required migration minima](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html). A historical minimum is not a recommendation to install that old build.
- Plan access entries before enabling API authentication. `CONFIG_MAP` to `API_AND_CONFIG_MAP` is a one-way migration; it preserves the existing ConfigMap path while adding access entries.
- Retain existing worker groups and the CoreDNS Deployment for non-Auto nodes. Review the supported CNI/network configuration. Enabling Auto Mode does not automatically migrate existing EBS volumes or load balancers.

For an eksctl-managed cluster, the current command is `eksctl update auto-mode-config --config-file <reviewed-config>`. It is **not** `eksctl update cluster --enable-auto-mode`, and you should not add `--drain-all-nodegroups` merely to enable the feature.

The following AWS CLI alternative enables compute, load balancing and block storage in the same request. It is for a cluster that is not already Auto Mode-enabled. It retains each update ID and waits for a terminal result instead of assuming that request acceptance means completion:

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --output json > "$WORK_DIR/before.json"
jq -e --arg role "$AUTO_CLUSTER_ROLE_ARN" '
  .cluster.status == "ACTIVE" and .cluster.roleArn == $role and
  .cluster.computeConfig.enabled != true
' "$WORK_DIR/before.json" >/dev/null

wait_update() {
  local id=$1 status
  for attempt in $(seq 1 120); do
    aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
      --update-id "$id" --output json > "$WORK_DIR/update-$id.json" || return
    status=$(jq -er '.update.status' "$WORK_DIR/update-$id.json") || return
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled) printf 'Update %s: %s; inspect the private response.\n' "$id" "$status" >&2; return 1 ;;
      InProgress) sleep 15 ;;
      *) printf 'Unknown update state; stop.\n' >&2; return 1 ;;
    esac
  done
  printf 'Update wait timed out; do not assume completion or resubmit blindly.\n' >&2
  return 1
}
# One-way authentication migration; review existing access before running.
mode=$(jq -er '.cluster.accessConfig.authenticationMode' "$WORK_DIR/before.json")
case "$mode" in
  CONFIG_MAP)
    auth_id=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
      --access-config authenticationMode=API_AND_CONFIG_MAP --query update.id --output text)
    wait_update "$auth_id"
    ;;
  API|API_AND_CONFIG_MAP) ;;
  *) printf 'Unknown authentication mode; stop.\n' >&2; exit 1 ;;
esac
compute=$(jq -nc --arg role "$AUTO_NODE_ROLE_ARN" \
  '{enabled:true,nodePools:["general-purpose","system"],nodeRoleArn:$role}')
# MUTATION: compute, load balancing and block storage change together.
check_account
update_id=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --compute-config "$compute" \
  --kubernetes-network-config '{"elasticLoadBalancing":{"enabled":true}}' \
  --storage-config '{"blockStorage":{"enabled":true}}' \
  --query update.id --output text)
wait_update "$update_id"
```

If an update fails, times out or returns an unknown state, inspect the private response and reconcile the operation before retrying. The node role used by default pools cannot be arbitrarily changed after enabling compute; follow the documented NodeClass/access-entry workflow when redesigning node identity.

## AWS Console

After completing the same IAM, add-on and access prerequisites, open the cluster's **EKS Auto Mode → Manage** settings, enable Auto Mode, select default pools and the reviewed node role, and monitor the resulting update. New-cluster creation offers the corresponding settings. Console placement can change; the required API capabilities and IAM roles remain the important checks.

## Verify Activation

After your chosen creation method succeeds, or the existing-cluster update completes:

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{status:status,compute:computeConfig,network:kubernetesNetworkConfig,storage:storageConfig,access:accessConfig}' \
  --output json > "$WORK_DIR/after.json"
jq -e '.status == "ACTIVE" and .compute.enabled == true and
       .network.elasticLoadBalancing.enabled == true and .storage.blockStorage.enabled == true' \
  "$WORK_DIR/after.json"
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodepools,nodeclasses
kubectl --context "$CLUSTER_NAME" wait nodepool/general-purpose nodepool/system \
  --for=condition=Ready --timeout=300s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes -L eks.amazonaws.com/compute-type
```

An idle cluster can have no Auto Mode nodes until eligible workloads need capacity. NodePool readiness is not an application availability test. Use a constrained test workload, check NodeClaims/nodes and application readiness, and then remove that test workload.

Auto Mode nodes run local CoreDNS as a system service. A pure Auto Mode migration can remove the traditional Deployment after workloads move; **mixed Auto/non-Auto clusters must retain it** for the other nodes.

## Cleanup and Next Steps

Delete only the resources owned by the creation method you chose, after exporting needed data and removing application load balancers/PVCs according to their retention policies. Use eksctl deletion with `--wait`, a reviewed Terraform destroy plan, or deletion of the reviewed CDK stack as appropriate. These examples reference existing IAM roles, and the eksctl example also reuses a VPC: do not delete those shared prerequisites as though the example created them.

An existing-cluster enablement is not a disposable-cluster lab. Do not delete its old worker groups or disable its controllers until workload, storage, DNS and traffic migration has been validated. Nodes, volumes, load balancers, NAT and the control plane can keep incurring charges after an interrupted operation; inspect residual resources rather than relying on a fixed sleep.

- [NodePool configuration](./02-nodepool-configuration.md)
- [Managed node group migration](./09-migration-guide.md)
- [Getting started quiz](../quizzes/eks-auto-mode/01-getting-started-quiz.md)

## References

- [Auto Mode CLI creation and IAM roles](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)
- [Enable Auto Mode on an existing cluster](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)
- [eksctl Auto Mode configuration](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html)
- [EKS support calendar](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Terraform EKS module v21.25.0](https://github.com/terraform-aws-modules/terraform-aws-eks/tree/v21.25.0)
- [CDK CfnCluster API](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks.CfnCluster.html)
- [IAM principal access through EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Auto Mode networking and DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [Migration boundaries](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)

< [Previous: Overview](./README.md) | [Table of Contents](./README.md) | [Next: NodePool Configuration](./02-nodepool-configuration.md) >
