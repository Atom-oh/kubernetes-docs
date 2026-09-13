# EKS Cluster Creation

> **Last Updated**: September 11, 2026

There are several ways to create an Amazon EKS cluster. In this chapter, we will learn in detail how to create an EKS cluster using various tools and methods.

The creation methods in this chapter are alternatives. Choose one for a new dedicated cluster, and do not manage the same resources with several tools simultaneously. Replace example names, accounts, roles, VPCs, subnets and CIDRs with approved actual values. Shell examples use Bash unless stated otherwise; stop on prerequisite failures. No AWS provisioning or workload measurement was performed during this audit.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Creating a Cluster Using eksctl](#creating-a-cluster-using-eksctl)
3. [Creating a Cluster Using AWS Management Console](#creating-a-cluster-using-aws-management-console)
4. [Creating a Cluster Using AWS CLI](#creating-a-cluster-using-aws-cli)
5. [Creating a Cluster Using Terraform](#creating-a-cluster-using-terraform)
6. [Creating a Cluster Using AWS CDK](#creating-a-cluster-using-aws-cdk)
7. [Configuring Cluster Access](#configuring-cluster-access)
8. [Cluster Validation](#cluster-validation)
9. [Cluster Upgrade](#cluster-upgrade)
10. [Cluster Deletion](#cluster-deletion)

## Prerequisites

Before creating an EKS cluster, the following prerequisites are required:

### 1. AWS Account

A valid AWS account is required. If you don't have an AWS account, you can sign up at the [AWS website](https://aws.amazon.com/).

### 2. IAM Permissions

Required permissions depend on the tool and the resources it manages. A policy granting `eks:*`, `ec2:*`, `iam:*` and `cloudformation:*` on every resource is not a required least-privilege policy.

| Task | Permission scope to review |
| --- | --- |
| EKS cluster/node group management | Required EKS actions and target resources |
| Passing existing IAM roles | `iam:PassRole` for approved role ARNs and service conditions |
| Creating IAM roles/policies/OIDC providers | Tool-managed IAM resources and name/tag scope |
| Creating networking | EC2 actions for the new VPC, subnets and security groups |
| Using eksctl/CDK | Relevant CloudFormation stacks, execution roles and bootstrap resources |

The provisioning identity, cluster service role and node role are separate. SCPs, permissions boundaries and session policies still apply. Review your organization's provisioning permissions against the synthesized template/plan. Auto Mode role requirements differ from conventional node groups.

References: [EKS IAM actions and resources](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html), [Auto Mode roles](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

### 3. Tool Installation

#### AWS CLI

Choose the package for your OS/CPU and follow signature verification in the [official AWS CLI v2 installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). For an existing v1/v2 installation, review its update/migration procedure first.

| Environment | Official package/installation method |
| --- | --- |
| macOS | Signed `AWSCLIV2.pkg` |
| Linux x86_64 | `awscli-exe-linux-x86_64.zip` with PGP signature verification |
| Linux ARM64 | `awscli-exe-linux-aarch64.zip` with PGP signature verification |
| Windows | MSI installer for supported Windows versions |

Do not use the Linux x86_64 package unchanged on ARM. Check the active CLI with `aws --version`. If your organization uses IAM Identity Center, configure an approved profile as follows. Otherwise follow its federation procedure rather than assuming long-lived access keys.

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

See [IAM Identity Center authentication](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html). Keep using the approved account, role and region for subsequent commands.

#### kubectl and eksctl — Linux/macOS

This chapter's EKS 1.36 examples use kubectl **1.36.4** and eksctl **0.230.0** as their baseline. Prefer the same kubectl minor as the server; supported skew is ±1 minor. Do not blindly install the newest minor from upstream `stable.txt` for an older EKS cluster.

This Bash example selects AMD64/ARM64 and verifies official checksums before installation. It needs `curl`, `tar`, `awk`, and `sha256sum` or `shasum`; installation in `/usr/local/bin` requires administrator permission. Download or checksum failure stops installation.

```bash
(
  set -e
  case "$(uname -s)" in
    Linux) EKS_TOOL_OS=linux; EKS_ARCHIVE_OS=Linux ;;
    Darwin) EKS_TOOL_OS=darwin; EKS_ARCHIVE_OS=Darwin ;;
    *) printf 'Use the official installer for this operating system\n' >&2; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64) EKS_TOOL_ARCH=amd64 ;;
    aarch64|arm64) EKS_TOOL_ARCH=arm64 ;;
    *) printf 'Select a supported CPU architecture\n' >&2; exit 1 ;;
  esac
  EKS_TOOL_ARCHIVE="eksctl_${EKS_ARCHIVE_OS}_${EKS_TOOL_ARCH}.tar.gz"
  EKS_TOOL_DIR=$(mktemp -d)
  : "${EKS_TOOL_DIR:?}"
  trap 'rm -f -- "$EKS_TOOL_DIR/kubectl" "$EKS_TOOL_DIR/kubectl.sha256" "$EKS_TOOL_DIR/eksctl" "$EKS_TOOL_DIR/eksctl_checksums.txt" "$EKS_TOOL_DIR/$EKS_TOOL_ARCHIVE" "$EKS_TOOL_DIR/selected.sha256"; rmdir -- "$EKS_TOOL_DIR"' EXIT
  cd "$EKS_TOOL_DIR" || exit 1
  verify_sha() {
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum --check "$1"
    else
      shasum -a 256 --check "$1"
    fi
  }
  EKS_KUBECTL_VERSION=v1.36.4
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl" -o kubectl || exit 1
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl.sha256" -o kubectl.sha256 || exit 1
  printf '%s  kubectl\n' "$(tr -d '[:space:]' < kubectl.sha256)" > selected.sha256
  verify_sha selected.sha256 || exit 1

  EKSCTL_VERSION=0.230.0
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/$EKS_TOOL_ARCHIVE" -o "$EKS_TOOL_ARCHIVE" || exit 1
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/eksctl_checksums.txt" -o eksctl_checksums.txt || exit 1
  awk -v name="$EKS_TOOL_ARCHIVE" '$2 == name {print; count++} END {if (count != 1) exit 1}' \
    eksctl_checksums.txt > selected.sha256 || exit 1
  verify_sha selected.sha256 || exit 1
  tar -xzf "$EKS_TOOL_ARCHIVE" eksctl || exit 1
  sudo install -m 0755 kubectl /usr/local/bin/kubectl || exit 1
  sudo install -m 0755 eksctl /usr/local/bin/eksctl || exit 1
  kubectl version --client
  eksctl version
)
```

Official procedures: [Linux kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/), [macOS kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/), [eksctl installation](https://eksctl.io/installation/).

#### Windows

Follow the [official kubectl installation procedure](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) in PowerShell. For this chapter's AMD64 example, use [kubectl 1.36.4](https://dl.k8s.io/release/v1.36.4/bin/windows/amd64/kubectl.exe) and the `.sha256` file at the same path. Select the Windows ZIP matching your CPU and `eksctl_checksums.txt` from the [eksctl 0.230.0 release](https://github.com/eksctl-io/eksctl/releases/tag/v0.230.0).

Compare `Get-FileHash -Algorithm SHA256` with the official hash and stop on mismatch. After verification, extract the ZIP, add the executable directory to PATH, and check `kubectl version --client` and `eksctl version`. Do not run PowerShell syntax in Bash.

Also prepare `jq` for JSON generation in the AWS CLI examples. No actual client download/installation or login was performed during this audit.

### 4. VPC and Subnets

A regional EKS cluster requires at least two subnets in different AZs of the same VPC. Each cluster subnet needs at least six available IPs for EKS; AWS recommends at least sixteen. Plan additional addresses for nodes, Pods, load balancers and upgrades. Enable VPC DNS hostnames and DNS resolution.

Internet access is not mandatory for every EKS cluster. Nodes and workloads need access to the Kubernetes API, images and required AWS services through NAT/internet paths or the necessary VPC endpoints and mirrored images. The private Kubernetes endpoint is reachable from the VPC or connected networks with appropriate DNS and routing.

#### VPC Tags for EKS Cluster

The `kubernetes.io/cluster/<cluster-name>` VPC tag is a legacy mechanism, not a universal current EKS creation requirement. Follow the chosen controller's subnet-discovery rules for load balancing:

- Subnets for public load balancers: `kubernetes.io/role/elb=1`
- Subnets for internal load balancers: `kubernetes.io/role/internal-elb=1`

Tags do not configure routing, security groups or free IP capacity. See [VPC/subnet requirements](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html) and [clusters without internet access](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html).

## Creating a Cluster Using eksctl

eksctl is the simplest way to create and manage EKS clusters. eksctl uses CloudFormation to create EKS clusters and related resources.

Store the eksctl kubeconfig at a dedicated path for this shell.

```bash
EKS_CLIENT_DIR=$(mktemp -d /tmp/eks-client.XXXXXX)
: "${EKS_CLIENT_DIR:?}"
EKS_KUBECONFIG="$EKS_CLIENT_DIR/kubeconfig"
export KUBECONFIG="$EKS_KUBECONFIG"
```

### Basic Cluster Creation

Create the basic cluster from a reviewed configuration file:

```bash
eksctl create cluster --config-file cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

Read and edit `cluster.yaml` below before running this command. It explicitly selects EKS 1.36, AL2023, existing VPC subnets and node-group capacities. Replace the example identifiers and documentation CIDR with actual approved values. These are selected settings, not claims about every eksctl version's defaults.

### Creating a Cluster Using a Configuration File

For more complex configurations, you can define the cluster using a YAML file:

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: '1.36'
vpc:
  id: vpc-12345678
  subnets:
    private:
      us-west-2a:
        id: subnet-12345678
      us-west-2b:
        id: subnet-87654321
    public:
      us-west-2a:
        id: subnet-23456789
      us-west-2b:
        id: subnet-98765432
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
managedNodeGroups:
- name: ng-1
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
  privateNetworking: true
  volumeSize: 80
  volumeType: gp3
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
- name: ng-2
  instanceType: c5.xlarge
  desiredCapacity: 2
  privateNetworking: true
  spot: true
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
fargateProfiles:
- name: fp-default
  selectors:
  - namespace: default
    labels:
      env: fargate
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
```

To create a cluster using this configuration file, run the following command:

```bash
eksctl create cluster -f cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

The configuration above demonstrates EC2 nodes and an optional application Fargate profile. CoreDNS stays on EC2; moving it to Fargate requires reviewing CoreDNS compute settings as well as the profile.

### Creating Managed Node Groups

To add a managed node group to an existing cluster, run the following command:

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed --node-ami-family AmazonLinux2023 --node-private-networking
```

Or you can use a configuration file:

```yaml
# nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: my-nodegroup
  instanceType: m5.large
  desiredCapacity: 3
  minSize: 1
  maxSize: 5
  volumeSize: 80
  volumeType: gp3
  amiFamily: AmazonLinux2023
  privateNetworking: true
  disableIMDSv1: true
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### Creating an EKS Auto Mode Cluster

EKS Auto Mode is a new feature released in 2024 that automates Kubernetes cluster infrastructure to significantly reduce operational overhead. Auto Mode automatically handles infrastructure management including compute, networking, and storage.

#### Key Features of EKS Auto Mode

- **Automated Node Management**: Automatically adds/removes nodes based on workload requirements
- **Enhanced Security**: Immutable AMI, SELinux enforcing mode, read-only root filesystem
- **Node maintenance**: Nodes are replaced for expiration and drift. Twenty-one days is not a control plane minor-version upgrade cycle
- **Integrated Components**: Pod networking, DNS, storage, GPU support provided by default
- **Cost Optimization**: Automatic termination of unused instances and workload consolidation

#### Basic Auto Mode Cluster Creation

Review the CIDR and networking in `auto-cluster.yaml` below first. Do not duplicate Auto Mode networking, DNS and block storage with self-managed add-ons. Mixed clusters need explicit placement and component scope for each compute type.

```bash
eksctl create cluster --config-file auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### Creating an Auto Mode Cluster Using a Configuration File

```yaml
# auto-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-auto-cluster
  region: us-west-2
  version: '1.36'
autoModeConfig:
  enabled: true
  nodePools:
  - system
  - general-purpose
vpc:
  cidr: 10.0.0.0/16
  nat:
    gateway: Single
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
accessConfig:
  authenticationMode: API
```

Create cluster:
```bash
eksctl create cluster -f auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### Auto Mode vs Traditional Approach Comparison

| Feature | Traditional EKS | EKS Auto Mode |
|---------|-----------------|---------------|
| Node Management | Managed node groups or customer-managed nodes | AWS-managed node lifecycle |
| Scaling | Configure Cluster Autoscaler, self-managed Karpenter or another strategy | Managed node auto scaling |
| Upgrades | Plan control plane, node and add-on updates | AWS manages node/component updates; plan control plane minors under the support policy |
| Security | User configured | Enhanced security by default |
| Networking | CNI plugin setup | Automatic networking configuration |
| Storage | CSI installation and permissions required | Managed EBS provisioner `ebs.csi.eks.amazonaws.com` |
| GPU Support | Select compatible accelerated AMIs and required device plugins | Managed drivers/plugins for supported instances |

#### Auto Mode Cluster Validation

After the cluster is created, you can check its status with the following commands:

```bash
# Check cluster status
kubectl get nodes

# Check Auto Mode node pools
kubectl get nodepools

# Check Auto Mode node classes
kubectl get nodeclasses

# Check system pod status
kubectl get pods -n kube-system
```

#### Creating Custom Node Pools

In Auto Mode, you can create custom node pools in addition to the default node pools:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-nodepool
spec:
  template:
    metadata:
      labels:
        workload-type: gpu
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p3.2xlarge
        - p3.8xlarge
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 336h
      taints:
      - key: nvidia.com/gpu
        value: present
        effect: NoSchedule
  limits:
    cpu: '1000'
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

> **Note**: In Auto Mode you cannot use `EC2NodeClass`, `amiFamily`, or custom `userData` (`/etc/eks/bootstrap.sh`). AWS manages the node AMI and bootstrap; subnets, security groups, and ephemeral storage are defined through an `eks.amazonaws.com/v1` `NodeClass` instead.

The GPU example retains p3, which is in the current official supported list. Check AZ capacity, quotas and GPU memory/model requirements. GPU Pods must request `nvidia.com/gpu` and tolerate the taint above. This YAML was reviewed; no GPU node was provisioned or benchmarked.

#### Auto Mode Limitations

- No direct node access via SSH or SSM
- Default expiration is 336 hours (14 days), with a maximum supported `expireAfter` setting of 21 days. Review draining, PDB/NodePool blockers and the default 24-hour termination grace period together
- Cannot modify default node pools and node classes
- Certain instance type restrictions possible

#### Auto Mode Monitoring

Managed infrastructure does not automatically configure every workload's CloudWatch metrics. `cluster_node_count` belongs to **ContainerInsights**, not `AWS/EKS`, and requires a configured Container Insights collection pipeline. Configure collection for your environment and query a time range with actual data.

```bash
# Requires a configured Container Insights collection pipeline and metric data.
aws cloudwatch list-metrics --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --start-time "${METRICS_START_TIME:?Set a reviewed ISO8601 start time}" \
  --end-time "${METRICS_END_TIME:?Set a later ISO8601 end time}" \
  --period 3600 --statistics Average
```

An empty result does not establish zero nodes or Auto Mode failure. Check collection, dimensions and the time range first. No CloudWatch queries or measurements were run in this audit. See the [official Container Insights metric catalog](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html).

### Creating Fargate Profiles

To create a Fargate profile, run the following command:

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

Or you can use a configuration file:

```yaml
# fargate.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: my-fargate-profile
  selectors:
  - namespace: default
    labels:
      env: fargate
```

```bash
eksctl create fargateprofile -f fargate.yaml
```

### Updating a Cluster

Review control plane, node and add-on compatibility, then follow [Cluster Upgrade](#cluster-upgrade).

### Deleting a Cluster

Review workloads, load balancers, data retention and the owning tool, then follow [Cluster Deletion](#cluster-deletion).

## Creating a Cluster Using AWS Management Console

The steps to create an EKS cluster using the AWS Management Console are as follows:

1. Log in to the [AWS Management Console](https://console.aws.amazon.com/).
2. Search for "EKS" or select "Elastic Kubernetes Service" from the services list.
3. On the "Clusters" page, click the "Create cluster" button.

### Creating an EKS Auto Mode Cluster (Quick Configuration)

EKS Auto Mode reduces infrastructure setup. Workload identity, networking, capacity, availability and recovery still need explicit configuration and validation.

#### 1. Select Quick Configuration

4. Ensure the "Quick configuration" option is selected.
5. Enter the following information:
   - **Cluster name**: Enter a unique name for the cluster.
   - **Kubernetes version**: Select the Kubernetes version to use (latest version recommended).

#### 2. Configure IAM Roles

6. **Cluster IAM role** selection:
   - For your first Auto Mode cluster, use the "Create recommended role" option.
   - If you have an existing role, you can reuse it.
   - Recommended role name: `AmazonEKSAutoClusterRole`

7. **Node IAM role** selection:
   - For your first Auto Mode cluster, use the "Create recommended role" option.
   - Recommended role name: `AmazonEKSAutoNodeRole`

#### 3. Configure Networking

8. **Select VPC**:
   - Create new VPC: Select the "Create VPC" option to create a new VPC for EKS.
   - Use existing VPC: Select a previously created EKS VPC.

9. **Subnet configuration** (optional):
   - EKS Auto Mode automatically selects private subnets in the VPC.
   - You can add or remove subnets as needed.

#### 4. Review Configuration and Create

10. Select **View quick configuration defaults** to review all configuration values.
11. Click **Create cluster**. (Cluster creation takes approximately 15 minutes)

### Creating a Cluster with Custom Configuration

If you need more granular control, you can use custom configuration.

### Cluster Configuration

4. On the "Configure cluster" page, enter the following information:
   - **Cluster name**: Enter a unique name for the cluster.
   - **Kubernetes version**: Select the Kubernetes version to use.
   - **Cluster service role**: Create a new role or select an existing role.
   - **EKS Auto Mode**: Check the checkbox to enable Auto Mode.
   - **Tags**: Add tags if needed.
   - Click the "Next" button.

### Specify Networking

5. On the "Specify networking" page, enter the following information:
   - **VPC**: Create a new VPC or select an existing VPC.
   - **Subnets**: Select the subnets to use for the cluster. At least 2 subnets must be in different availability zones.
   - **Security groups**: Select the security groups to use for the cluster.
   - **Cluster endpoint access**: Configure access to the cluster API server endpoint.
     - **Public**: The API server can be accessed from the internet.
     - **Private**: Access from the VPC or connected networks requires appropriate DNS and routing.
     - **Public and Private**: The API server can be accessed from both the internet and within the VPC.
   - Click the "Next" button.

### Configure Logging

6. On the "Configure logging" page, enter the following information:
   - **Control plane logging**: Select the log types to enable.
     - API server logs
     - Audit logs
     - Authenticator logs
     - Controller manager logs
     - Scheduler logs
   - Click the "Next" button.

### Select Add-ons

The following add-ons describe conventional compute. Auto Mode manages overlapping networking, DNS and block-storage capabilities; select components according to the compute types in your cluster.

7. On the "Select add-ons" page, enter the following information:
   - **Amazon VPC CNI**: CNI plugin for pod networking.
   - **CoreDNS**: DNS service within the cluster.
   - **kube-proxy**: Provides network proxy and load balancing.
   - **Storage/networking add-ons**: Conventional compute needs the appropriate installed components and IAM permissions. Auto Mode provides managed EBS/networking/DNS capabilities; do not install overlapping components on Auto Mode nodes.
   - Click the "Next" button.

### Review and Create

8. On the "Review and create" page, review the configuration and click the "Create" button.

### Adding Node Groups for Non-Auto Mode Clusters

For conventional EC2 compute, add node groups after cluster creation. Other supported choices, such as Fargate profiles, have their own setup; a managed node group is not mandatory for every non-Auto Mode cluster.

### Add Node Group

1. On the "Node group configuration" page, enter the following information:
   - **Node group name**: Enter a unique name for the node group.
   - **Node IAM role**: Create a new role or select an existing role.
   - Click the "Next" button.

2. On the "Set compute and scaling configuration" page, enter the following information:
   - **AMI type**: Select the AMI type to use for the nodes.
   - **Instance type**: Select the EC2 instance type to use for the nodes.
   - **Disk size**: Specify the disk size for the nodes.
   - **Node count**: Specify the minimum, maximum, and desired number of nodes.
   - Click the "Next" button.

3. On the "Specify networking" page, enter the following information:
   - **Subnets**: Select the subnets to use for the node group.
   - **Remote access configuration**: Leave SSH disabled unless an approved management path requires it; do not specify an SSH key without reviewing source security groups.
   - Click the "Next" button.

4. On the "Review and create" page, review the configuration and click the "Create" button.

## Creating a Cluster Using AWS CLI

These examples create a **new cluster**. Choose Auto Mode or conventional EKS; do not run both creation commands consecutively with the same name. Use Bash, `jq`, a current AWS CLI v2 and an authorized AWS role. EKS 1.36 is the verified example version; review regional support and compatibility before selecting another version.

The two subnets must be in different AZs of the same VPC. Prepare DNS, free IPs, security groups and node access to images/services separately. The actual API field names are `endpointPrivateAccess` and `endpointPublicAccess`. Creator administrator access bootstraps this dedicated example; manage subsequent access through access entries.

### Prepare common inputs

Pre-create the cluster role for the selected mode and verify required `iam:PassRole` and service-linked role creation permissions. Review the account, region, subnets and approved CIDR before executing a creation command.

```bash
: "${EKS_CLUSTER_NAME:?Choose a unique new cluster name}"
: "${EKS_REGION:?Choose the intended AWS region}"
: "${EKS_CLUSTER_ROLE_ARN:?Pre-created cluster role for the chosen mode}"
: "${EKS_SUBNET_A:?Existing subnet in the intended VPC}"
: "${EKS_SUBNET_B:?Existing subnet in a different AZ of the same VPC}"
: "${EKS_PUBLIC_API_CIDR:?Approved client CIDR, normally /32}"
EKS_CREATION_DIR=$(mktemp -d /tmp/eks-create.XXXXXX)
: "${EKS_CREATION_DIR:?}"
EKS_KUBECONFIG="$EKS_CREATION_DIR/kubeconfig"
unset EKS_CREATED_CLUSTER_ARN
aws sts get-caller-identity
```

### Creating an EKS Auto Mode Cluster

The cluster role needs `sts:AssumeRole` and `sts:TagSession` trust for `eks.amazonaws.com`, with `AmazonEKSClusterPolicy`, `AmazonEKSComputePolicy`, `AmazonEKSBlockStoragePolicyV2`, `AmazonEKSLoadBalancingPolicy` and `AmazonEKSNetworkingPolicy`, or equivalent custom permissions.

The node role trusts `ec2.amazonaws.com` and uses `AmazonEKSWorkerNodeMinimalPolicy` plus `AmazonEC2ContainerRegistryPullOnly`. Grant workloads AWS permissions separately through Pod Identity/IRSA. Enable compute, load balancing and block storage together, and disable bootstrap of the default self-managed add-ons.

```bash
: "${EKS_AUTO_NODE_ROLE_ARN:?Pre-created Auto Mode node role}"
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  --arg nodeRole "$EKS_AUTO_NODE_ROLE_ARN" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: false,
  computeConfig: {
    enabled: true, nodePools: ["system", "general-purpose"], nodeRoleArn: $nodeRole
  },
  kubernetesNetworkConfig: {ipFamily: "ipv4", elasticLoadBalancing: {enabled: true}},
  storageConfig: {blockStorage: {enabled: true}}
}' > "${EKS_CREATION_DIR:?}/create-auto.json"
cat "$EKS_CREATION_DIR/create-auto.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-auto.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### Verify creation and access

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

Auto Mode can have no nodes before workloads require them. Check NodePool/NodeClass status and subsequent Pod scheduling. Cluster `ACTIVE` does not prove application health or guarantee a fixed creation duration.

```bash
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodepools.karpenter.sh
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodeclasses.eks.amazonaws.com
```

### Creating a Conventional Cluster

Use this alternative only if you did not select Auto Mode. The cluster role needs conventional EKS cluster permissions; the EC2 node role and CNI/add-on permissions are separate. Bootstrapping default networking add-ons does not install EBS CSI or AWS LBC.

```bash
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: true,
  kubernetesNetworkConfig: {ipFamily: "ipv4"}
}' > "${EKS_CREATION_DIR:?}/create-standard.json"
cat "$EKS_CREATION_DIR/create-standard.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-standard.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### Wait for creation and configure kubeconfig

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

#### Create a managed node group

Prepare worker-node and ECR pull permissions for the EC2 node role, and a separate CNI role or reviewed node-role CNI permissions. Do not reuse the Auto Mode minimal node role unchanged. Private subnets also require NAT or the necessary VPC endpoints. This AL2023 example does not enable SSH by default.

```bash
: "${EKS_MANAGED_NODE_ROLE_ARN:?Pre-created conventional EC2 node role}"
: "${EKS_NODEGROUP_NAME:?Unique managed node group name}"
aws eks create-nodegroup \
  --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" \
  --subnets "${EKS_SUBNET_A:?}" "${EKS_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --node-role "$EKS_MANAGED_NODE_ROLE_ARN" \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --disk-size 20 --region "${EKS_REGION:?}"

aws eks wait nodegroup-active --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
aws eks describe-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version}' --output json
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodes
```

`minSize`/`maxSize` alone do not enable Pod-demand-based node scaling. Inspect status and health errors, then configure an autoscaler if needed. On creation failure, inspect the recorded names/ARN and related resources. These creation and wait commands were not executed during the audit.

References: [CreateCluster API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateCluster.html), [CreateNodegroup API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html), [Auto Mode IAM and creation](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

## Creating a Cluster Using Terraform

The following complete example supports **one new cluster**, choosing Auto Mode or a conventional managed node group before the first apply. Do not append the alternative as a second cluster resource or toggle an existing cluster without a migration plan. Terraform state and its provider lock file belong to this specific deployment.

### EKS Auto Mode Cluster Terraform Configuration

Save as `main.tf`. The example pins AWS provider **6.64.0** and uses EKS **1.36**. Supply existing private subnet IDs explicitly; a custom `Type=Private` tag is not a reliable substitute for verifying routes and connectivity. The precondition checks VPC/AZ relationships during planning, but does not verify private routing, service endpoints, DNS, IP capacity or load-balancer subnet tags.

Auto Mode needs compute, load balancing and block storage enabled together, with `bootstrap_self_managed_addons = false`. The cluster role includes `sts:TagSession` and all five required policies. IAM attachment dependencies preserve permissions while EKS deletes managed infrastructure.

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_partition" "current" {}
data "aws_subnet" "selected" {
  for_each = toset(var.private_subnet_ids)
  id       = each.value
}

locals {
  cluster_policies = var.enable_auto_mode ? toset([
    "AmazonEKSClusterPolicy",
    "AmazonEKSComputePolicy",
    "AmazonEKSBlockStoragePolicyV2",
    "AmazonEKSLoadBalancingPolicy",
    "AmazonEKSNetworkingPolicy",
  ]) : toset(["AmazonEKSClusterPolicy"])
  node_policies = var.enable_auto_mode ? toset([
    "AmazonEKSWorkerNodeMinimalPolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    ]) : toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    # Conventional bootstrap baseline; see the CNI role caveat in the text.
    "AmazonEKS_CNI_Policy",
  ])
}

resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = var.enable_auto_mode ? ["sts:AssumeRole", "sts:TagSession"] : ["sts:AssumeRole"]
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  for_each   = local.cluster_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["sts:AssumeRole"]
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each   = local.node_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.node.name
}

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = false
  }
  bootstrap_self_managed_addons = !var.enable_auto_mode

  compute_config {
    enabled       = var.enable_auto_mode
    node_pools    = var.enable_auto_mode ? ["system", "general-purpose"] : null
    node_role_arn = var.enable_auto_mode ? aws_iam_role.node.arn : null
  }
  kubernetes_network_config {
    ip_family = "ipv4"
    elastic_load_balancing {
      enabled = var.enable_auto_mode
    }
  }
  storage_config {
    block_storage {
      enabled = var.enable_auto_mode
    }
  }
  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.public_api_cidrs
  }
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Keep policies attached until EKS finishes deleting managed infrastructure.
  depends_on = [
    aws_iam_role_policy_attachment.cluster,
    aws_iam_role_policy_attachment.node,
  ]
  lifecycle {
    precondition {
      condition = (
        alltrue([for subnet in data.aws_subnet.selected : subnet.vpc_id == var.vpc_id]) &&
        length(toset([for subnet in data.aws_subnet.selected : subnet.availability_zone])) >= 2
      )
      error_message = "Supply subnets in at least two AZs of the selected VPC."
    }
  }
  tags = var.tags
}

resource "aws_eks_node_group" "standard" {
  count           = var.enable_auto_mode ? 0 : 1
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main-nodegroup"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = aws_eks_cluster.main.version
  ami_type        = "AL2023_x86_64_STANDARD"
  capacity_type   = "ON_DEMAND"
  instance_types  = ["m5.large"]
  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }
  update_config {
    max_unavailable = 1
  }
  depends_on = [aws_iam_role_policy_attachment.node]
  tags       = var.tags
}

resource "aws_eks_access_entry" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = var.operator_role_arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_eks_access_entry.operator.principal_arn
  policy_arn    = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  access_scope {
    type = "cluster"
  }
}

variable "enable_auto_mode" {
  description = "Creation-time choice. Changing an existing cluster requires a separate migration plan."
  type        = bool
  default     = true
}
variable "cluster_name" {
  description = "Unique name for this new cluster."
  type        = string
}
variable "kubernetes_version" {
  description = "EKS-supported minor version; 1.36 is the reviewed example."
  type        = string
  default     = "1.36"
}
variable "region" {
  type = string
}
variable "vpc_id" {
  type = string
}
variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition     = length(distinct(var.private_subnet_ids)) >= 2
    error_message = "At least two distinct subnet IDs are required."
  }
}
variable "public_api_cidrs" {
  type = list(string)
  validation {
    condition = length(var.public_api_cidrs) > 0 && alltrue([
      for cidr in var.public_api_cidrs :
      can(cidrhost(cidr, 0)) && cidr != "0.0.0.0/0" && cidr != "::/0"
    ])
    error_message = "Supply reviewed client CIDRs instead of unrestricted public API access."
  }
}
variable "operator_role_arn" {
  description = "Existing approved IAM role allowed to administer this cluster."
  type        = string
}
variable "tags" {
  type = map(string)
  default = {
    Environment = "dev"
    Project     = "eks-creation-example"
  }
}

output "cluster_name" {
  value = aws_eks_cluster.main.name
}
output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}
output "cluster_security_group_id" {
  value = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}
output "cluster_arn" {
  value = aws_eks_cluster.main.arn
}
```

The operator access entry grants the approved IAM role cluster administration; the creator is not automatically granted Kubernetes administrator access. That operator role must already exist and the person using kubectl must be able to assume it.

The conventional-node alternative includes CNI permissions on the node role as an initial bootstrap baseline. This is a shared permission boundary, not a hardened production workload identity design. Review a dedicated CNI role and restrict Pod access to IMDS before production use. Application AWS permissions belong on workload-specific identities; do not attach unrelated add-on permissions to every node.

### Running Terraform

Use a fresh working directory and an authenticated provisioning role. Replace the sample IDs and documentation CIDR with the intended account's resources and approved client CIDR. The default chooses Auto Mode:

```hcl
# terraform.tfvars — replace every example identifier before planning.
cluster_name       = "eks-docs-unique-name"
region             = "us-west-2"
vpc_id             = "vpc-0123456789abcdef0"
private_subnet_ids = ["subnet-0123456789abcdef0", "subnet-1123456789abcdef0"]
public_api_cidrs   = ["203.0.113.10/32"]
operator_role_arn  = "arn:aws:iam::111122223333:role/ApprovedOperator"
enable_auto_mode  = true
```

```bash
# Run in a new directory containing main.tf and the reviewed terraform.tfvars.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=reviewed.tfplan
# Apply only the plan you reviewed for the intended account/region/resources.
terraform apply reviewed.tfplan

: "${EKS_REGION:?Use the same region as terraform.tfvars}"
: "${EKS_OPERATOR_ROLE_ARN:?Use the same operator role as terraform.tfvars}"
aws eks update-kubeconfig --name "$(terraform output -raw cluster_name)" \
  --region "$EKS_REGION" --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

Review the state/backend, the proposed IAM and network changes, and all billable resources before apply. `terraform validate` cannot verify AWS account permissions, quotas, routing or whether the selected nodes can run your workloads. Node group scaling bounds do not install a Pod-demand-based autoscaler.

### Traditional Terraform Configuration

For a **new conventional cluster**, use the same complete `main.tf` and set the following value in `terraform.tfvars` before the first plan:

```hcl
enable_auto_mode = false
```

This disables all three Auto Mode capabilities, bootstraps the conventional networking add-ons, selects conventional EC2 node permissions and creates the AL2023 managed node group. It does not install EBS CSI, AWS LBC, Metrics Server or a node autoscaler; configure the components your workload requires separately. Switching this value after deployment changes infrastructure and IAM and requires a separate migration review.

Validation: Terraform **1.15.7** with the signed AWS provider **6.64.0** passed local `terraform validate` with zero errors/warnings. **No plan, apply or AWS API call was executed.** Both modes still need deployment validation; the example is not evidence of production readiness.

References: [AWS provider EKS cluster](https://github.com/hashicorp/terraform-provider-aws/blob/v6.64.0/website/docs/r/eks_cluster.html.markdown), [managed node group](https://github.com/hashicorp/terraform-provider-aws/blob/v6.64.0/website/docs/r/eks_node_group.html.markdown), [Auto Mode role requirements](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

## Creating a Cluster Using AWS CDK

Use `aws-cdk-lib/aws-eks-v2` for this **new-stack** example. It creates a native `AWS::EKS::Cluster` and access entry; no Lambda custom resource is needed to enable Auto Mode. Do not treat replacing an existing deployed construct with this example as an in-place migration.

The example uses CDK library **2.269.0**, CLI **2.1141.0** and EKS **1.36**. It imports existing private subnets by attributes without a synthesis-time VPC lookup. Verify the supplied subnet/AZ correspondence, VPC DNS, routing, service access and load-balancer subnet tags before deployment. An imported VPC definition does not validate those conditions.

### EKS Auto Mode Cluster Using TypeScript

Save as `lib/eks-auto-mode-stack.ts`. The caller supplies an existing, approved operator role; only that role receives this cluster's administrator access. Workload permissions remain separate.

```typescript
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks-v2';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface EksAutoModeProps extends cdk.StackProps {
  readonly clusterName: string;
  readonly vpcId: string;
  readonly privateSubnetIds: string[];
  readonly availabilityZones: string[];
  readonly publicApiCidrs: string[];
  readonly operatorRoleArn: string;
}

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EksAutoModeProps) {
    super(scope, id, props);

    if (props.privateSubnetIds.length < 2 ||
        props.privateSubnetIds.length !== props.availabilityZones.length ||
        new Set(props.availabilityZones).size < 2 ||
        props.publicApiCidrs.length === 0) {
      throw new Error('Supply corresponding private subnets/AZs in at least two AZs and approved API CIDRs');
    }
    const vpc = ec2.Vpc.fromVpcAttributes(this, 'Vpc', {
      vpcId: props.vpcId,
      availabilityZones: props.availabilityZones,
      privateSubnetIds: props.privateSubnetIds,
    });

    const clusterRole = new iam.Role(this, 'ClusterRole', {
      assumedBy: new iam.ServicePrincipal('eks.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSClusterPolicy',
        'AmazonEKSComputePolicy',
        'AmazonEKSBlockStoragePolicyV2',
        'AmazonEKSLoadBalancingPolicy',
        'AmazonEKSNetworkingPolicy',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });
    clusterRole.assumeRolePolicy!.addStatements(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('eks.amazonaws.com')],
      actions: ['sts:TagSession'],
    }));

    const nodeRole = new iam.Role(this, 'NodeRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSWorkerNodeMinimalPolicy',
        'AmazonEC2ContainerRegistryPullOnly',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });

    const cluster = new eks.Cluster(this, 'Cluster', {
      clusterName: props.clusterName,
      version: eks.KubernetesVersion.V1_36,
      vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE.onlyFrom(...props.publicApiCidrs),
      defaultCapacityType: eks.DefaultCapacityType.AUTOMODE,
      bootstrapSelfManagedAddons: false,
      bootstrapClusterCreatorAdminPermissions: false,
      // All required policies/trust are defined above. Avoid adding the older
      // BlockStoragePolicy that CDK 2.269.0 otherwise attaches automatically.
      role: clusterRole.withoutPolicyUpdates(),
      compute: {
        nodePools: ['system', 'general-purpose'],
        nodeRole: nodeRole.withoutPolicyUpdates(),
      },
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUDIT,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
        eks.ClusterLoggingTypes.SCHEDULER,
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    cluster.node.addDependency(clusterRole, nodeRole);
    cluster.grantClusterAdmin('OperatorAccess', props.operatorRoleArn);

    new cdk.CfnOutput(this, 'ClusterName', { value: cluster.clusterName });
    new cdk.CfnOutput(this, 'ClusterEndpoint', { value: cluster.clusterEndpoint });
  }
}
```

The cluster role explicitly includes `sts:TagSession` and the five Auto Mode policies, including `AmazonEKSBlockStoragePolicyV2`. `withoutPolicyUpdates()` keeps CDK 2.269.0 from adding the older block-storage policy; this example is responsible for supplying all required permissions. Dependencies retain those roles until cluster deletion completes. The node role has only the Auto Mode minimal worker and ECR pull policies.

`bootstrapSelfManagedAddons: false` avoids overlapping self-managed networking add-ons. Auto Mode manages compute, load balancing and block storage together. The operator access entry is created separately from the cluster execution role.

### CDK App Entry Point

Save as `bin/eks-auto-mode.ts`; keep the shebang on the first line. Environment values are mandatory to prevent accidental use of example account, VPC or role values.

```typescript
#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { EksAutoModeStack } from '../lib/eks-auto-mode-stack';

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Set ${name} before synthesis/deployment`);
  return value;
}
function list(name: string): string[] {
  return required(name).split(',').map(value => value.trim()).filter(Boolean);
}
const app = new cdk.App();
new EksAutoModeStack(app, 'EksAutoModeStack', {
  env: {
    account: required('CDK_DEFAULT_ACCOUNT'),
    region: required('CDK_DEFAULT_REGION'),
  },
  clusterName: required('EKS_CLUSTER_NAME'),
  vpcId: required('EKS_VPC_ID'),
  privateSubnetIds: list('EKS_PRIVATE_SUBNET_IDS'),
  availabilityZones: list('EKS_AVAILABILITY_ZONES'),
  publicApiCidrs: list('EKS_PUBLIC_API_CIDRS'),
  operatorRoleArn: required('EKS_OPERATOR_ROLE_ARN'),
});
```

### CDK Deployment

Create a fresh project, save the two files above after initialization, and supply the values for the intended account/region. Use an authenticated, authorized AWS role. Review the synthesized IAM/network configuration and diff before deploying. The CDK library/CLI versions are separate packages and do not share the same version number.

```bash
mkdir eks-auto-mode
cd eks-auto-mode
npx --yes --package aws-cdk@2.1141.0 cdk init app --language typescript
npm install --save-exact aws-cdk-lib@2.269.0 constructs@10.5.0
npm install --save-dev --save-exact aws-cdk@2.1141.0 typescript@5.9.3

# Save the source files above, then set the required environment values.
: "${CDK_DEFAULT_ACCOUNT:?Set the intended AWS account ID}"
: "${CDK_DEFAULT_REGION:?Set the intended AWS region}"
: "${EKS_CLUSTER_NAME:?Use a unique name for this new cluster}"
: "${EKS_VPC_ID:?}"
: "${EKS_PRIVATE_SUBNET_IDS:?Comma-separated existing subnet IDs}"
: "${EKS_AVAILABILITY_ZONES:?Corresponding comma-separated AZs}"
: "${EKS_PUBLIC_API_CIDRS:?Approved client CIDRs, normally /32}"
: "${EKS_OPERATOR_ROLE_ARN:?Existing operator role you may assume}"
# Export the variables so the CDK application receives them.
export CDK_DEFAULT_ACCOUNT CDK_DEFAULT_REGION EKS_CLUSTER_NAME EKS_VPC_ID
export EKS_PRIVATE_SUBNET_IDS EKS_AVAILABILITY_ZONES EKS_PUBLIC_API_CIDRS EKS_OPERATOR_ROLE_ARN

npx tsc --noEmit
npx cdk synth
# Bootstrap creates AWS resources; review the account/region and execution policy.
npx cdk bootstrap "aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION"
npx cdk diff
npx cdk deploy

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$CDK_DEFAULT_REGION" \
  --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

The audit compiled both TypeScript files and synthesized the stack locally with dummy identifiers: all three Auto Mode capabilities, scoped API CIDRs, the required roles and one operator access entry were verified. No Lambda/custom resource was generated. Missing required input was rejected. **No bootstrap, lookup, deploy, cluster creation or AWS API call was executed**, so account quotas, networking and workload availability remain deployment checks.

References: [EKS V2 construct library](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks_v2-readme.html), [Auto Mode cluster role](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html), [Auto Mode creation](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

## Configuring Cluster Access

Set the cluster name, region and dedicated kubeconfig path produced by the selected method. For the Terraform/CDK examples, set the approved operator role in `EKS_OPERATOR_ROLE_ARN`. It can be omitted when using CLI creator access. Writing kubeconfig does not grant Kubernetes permissions.

```bash
: "${EKS_CLUSTER_NAME:?Use the selected cluster name}"
: "${EKS_REGION:?Use the selected region}"
: "${EKS_KUBECONFIG:?Set the dedicated kubeconfig path for this method}"
aws sts get-caller-identity
if [[ -n ${EKS_OPERATOR_ROLE_ARN:-} ]]; then
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig "$EKS_KUBECONFIG"
else
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --kubeconfig "$EKS_KUBECONFIG"
fi
eks_kubectl() {
  kubectl --kubeconfig "${EKS_KUBECONFIG:?}" "$@"
}
eks_kubectl config current-context
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query cluster.accessConfig.authenticationMode
```

### RBAC Configuration

Use access entries for new IAM access. This example grants a new role read access in the existing `dev` namespace; do not duplicate the operator entry managed by your creation tool. Authentication mode must be `API` or `API_AND_CONFIG_MAP`. The legacy `aws-auth` method is deprecated; do not overwrite its entire ConfigMap. Follow the official migration procedure when needed.

```bash
# A new reader identity, distinct from the operator already granted by IaC.
: "${EKS_READER_ROLE_ARN:?Existing approved IAM role without an access entry yet}"
if eks_kubectl get namespace dev &&
   aws eks create-access-entry --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --principal-arn "$EKS_READER_ROLE_ARN" \
  --type STANDARD --kubernetes-groups eks-docs-readers; then
EKS_ACCESS_DIR=$(mktemp -d /tmp/eks-access.XXXXXX)
: "${EKS_ACCESS_DIR:?}"
cat > "$EKS_ACCESS_DIR/rbac.yaml" << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: eks-docs-reader
  namespace: dev
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: eks-docs-readers
  namespace: dev
subjects:
- kind: Group
  name: eks-docs-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: eks-docs-reader
  apiGroup: rbac.authorization.k8s.io
EOF
eks_kubectl create -f "$EKS_ACCESS_DIR/rbac.yaml"
fi
```

This reader role grants neither Secret API access nor mutation permissions. Authenticate as that role and check `kubectl auth can-i`; other RBAC/EKS policy grants can add permissions. [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)

## Cluster Validation

Use `eks_kubectl` and the same dedicated kubeconfig from the access section. Control plane access alone does not establish node or workload health.

### Basic Validation

```bash
eks_kubectl cluster-info
eks_kubectl get nodes
eks_kubectl get pods -n kube-system
eks_kubectl get events --sort-by='.lastTimestamp'
```

### Auto Mode Specific Validation

AWS manages the Auto Mode provisioning controller. Do not expect a self-managed controller Pod in a `karpenter` namespace. Inspect NodePool/NodeClass conditions and events, plus NodeClaims for workloads requiring capacity.

```bash
eks_kubectl get nodepools.karpenter.sh
eks_kubectl get nodeclasses.eks.amazonaws.com
eks_kubectl get nodeclaims.karpenter.sh
```

### Deploy Sample Application

Use a new namespace to check image access, scheduling, HTTP readiness and a Service. A Fargate-only configuration first needs a profile matching this namespace.

```bash
EKS_SAMPLE_DIR=$(mktemp -d /tmp/eks-validate.XXXXXX)
: "${EKS_SAMPLE_DIR:?}"
unset EKS_SAMPLE_NAMESPACE EKS_SAMPLE_UID
EKS_SAMPLE_CANDIDATE=$(basename "$EKS_SAMPLE_DIR" | tr '[:upper:].' '[:lower:]-')
if EKS_SAMPLE_UID=$(eks_kubectl create namespace "$EKS_SAMPLE_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  EKS_SAMPLE_NAMESPACE=$EKS_SAMPLE_CANDIDATE
fi
: "${EKS_SAMPLE_NAMESPACE:?Namespace creation failed}"
: "${EKS_SAMPLE_UID:?Namespace UID missing}"
cat > "$EKS_SAMPLE_DIR/sample-app.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: ${EKS_SAMPLE_NAMESPACE}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      automountServiceAccountToken: false
      containers:
      - name: app
        image: nginx:1.30.4-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app-service
  namespace: ${EKS_SAMPLE_NAMESPACE}
spec:
  type: ClusterIP
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: http
EOF
eks_kubectl apply -f "$EKS_SAMPLE_DIR/sample-app.yaml"
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" rollout status deployment/sample-app --timeout=180s
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" get pods,services
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" port-forward --address 127.0.0.1 service/sample-app-service 8080:80
```

While port forwarding runs, open `http://127.0.0.1:8080`, then stop it with Ctrl-C. This checks ClusterIP access, not an external load balancer. For an NLB, select Auto Mode’s `eks.amazonaws.com/nlb` or an installed, authorized AWS LBC’s `service.k8s.aws/nlb` and review networking/cost prerequisites separately. No deployment or port forwarding was executed during this audit.

## Cluster Upgrade

First review upgrade insights, removed APIs, webhook/add-on compatibility, node versions, spare IPs and the recovery plan. Bring lagging nodes to the current control plane version, then advance one supported minor at a time. Some components need compatible updates before the control plane.

Auto Mode does not upgrade control plane minors every 21 days. Operators plan minor upgrades and account for automatic upgrades under the version support policy.

```bash
aws eks describe-cluster-versions --region "${EKS_REGION:?}" --output table
aws eks describe-cluster --name "${EKS_CLUSTER_NAME:?}" --region "$EKS_REGION" \
  --query 'cluster.{version:version,status:status}' --output table
eks_kubectl get nodes

# After readiness/compatibility review, choose the next supported minor.
: "${NEXT_MINOR_VERSION:?Select one supported minor step, for example 1.35 to 1.36}"
EKS_UPDATE_ID=$(aws eks update-cluster-version --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --kubernetes-version "$NEXT_MINOR_VERSION" \
  --query update.id --output text)
: "${EKS_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --update-id "$EKS_UPDATE_ID" --query 'update.{status:status,errors:errors}'

# Alternative interface; do not execute both:
# eksctl upgrade cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" --version "$NEXT_MINOR_VERSION" --approve
```

Proceed to the data plane only after the update reports `Successful`. AWS incrementally updates Auto Mode nodes; conventional managed node groups need a separate update.

```bash
# Conventional managed node group only, after the control plane update is Successful.
aws eks update-nodegroup-version --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --nodegroup-name "${EKS_NODEGROUP_NAME:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

Plan self-managed/Hybrid Node updates, Fargate Pod replacement, add-on updates and kubectl updates for their respective mechanisms. Check PDBs and spare capacity rather than hiding failures with force flags. Eligible control plane upgrades can roll back one minor within seven days, subject to node/add-on/API compatibility and support-policy constraints; rollback does not replace application data recovery.

[Upgrade procedure](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [Rollback conditions](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

## Cluster Deletion

Delete through the original owning tool/state in the intended account and region. First remove workloads and Ingress/LoadBalancer Services while their controllers still run, then verify completion. Decide how PVCs/PVs, snapshots and logs will be retained or recovered. Do not bypass timeouts or finalizers with force options.

### Clean up the sample namespace

```bash
EKS_SAMPLE_CLEANUP_OK=true
if [[ -n ${EKS_SAMPLE_NAMESPACE:-} && -n ${EKS_SAMPLE_UID:-} ]]; then
  current_uid=$(eks_kubectl get namespace "$EKS_SAMPLE_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [[ "$current_uid" = "$EKS_SAMPLE_UID" ]]; then
    eks_kubectl delete namespace "$EKS_SAMPLE_NAMESPACE" --wait=true --timeout=180s || EKS_SAMPLE_CLEANUP_OK=false
  else
    EKS_SAMPLE_CLEANUP_OK=false
  fi
elif [[ -n ${EKS_SAMPLE_NAMESPACE:-} || -n ${EKS_SAMPLE_UID:-} ]]; then
  EKS_SAMPLE_CLEANUP_OK=false
fi
# Remove local files only after successful sample cleanup.
if [[ "$EKS_SAMPLE_CLEANUP_OK" = true ]]; then
if [[ -n ${EKS_SAMPLE_DIR:-} ]]; then
  rm -f -- "$EKS_SAMPLE_DIR/sample-app.yaml"
  rmdir -- "$EKS_SAMPLE_DIR"
fi
if [[ -n ${EKS_ACCESS_DIR:-} ]]; then
  rm -f -- "$EKS_ACCESS_DIR/rbac.yaml"
  rmdir -- "$EKS_ACCESS_DIR"
fi
else
  printf 'Sample cleanup could not be verified; stop before deleting the cluster\n' >&2
fi
```

Stop and investigate if cleanup fails. Compare the target ARN with the creation result or owning IaC state, not merely an unreviewed current lookup.

```bash
: "${EKS_EXPECTED_CLUSTER_ARN:?Copy the ARN from the creation result or owning IaC state}"
: "${EKS_CLUSTER_NAME:?}"
: "${EKS_REGION:?}"
EKS_DELETE_TARGET_VERIFIED=false
if [[ ${EKS_SAMPLE_CLEANUP_OK:-false} != true ]]; then
  printf 'Complete the sample cleanup check above first\n' >&2
else
current_arn=$(aws eks describe-cluster --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --query cluster.arn --output text) || current_arn=""
if [[ "$current_arn" = "$EKS_EXPECTED_CLUSTER_ARN" ]]; then
  EKS_DELETE_TARGET_VERIFIED=true
  aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
else
  printf 'Target mismatch; stop and check the account, region and owning tool\n' >&2
fi
fi
```

### Delete Using eksctl

Use this for a cluster created by eksctl.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  eksctl delete cluster --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" --wait
fi
```

### Delete Using AWS CLI

For a cluster created directly with the CLI, set the owned node group/profile names listed above and repeat for each resource. Wait for deletion and verify none remain before deleting the cluster.

```bash
# For a cluster created directly with the AWS CLI, after workload/data cleanup.
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  if [[ -n ${EKS_NODEGROUP_NAME:-} ]]; then
    aws eks delete-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" &&
    aws eks wait nodegroup-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
  fi
  if [[ -n ${EKS_FARGATE_PROFILE_NAME:-} ]]; then
    aws eks delete-fargate-profile --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION" &&
    aws eks wait fargate-profile-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION"
  fi
  remaining_nodes=$(aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(nodegroups)' --output text) || remaining_nodes=unknown
  remaining_profiles=$(aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(fargateProfileNames)' --output text) || remaining_profiles=unknown
  if [[ "$remaining_nodes" = 0 && "$remaining_profiles" = 0 ]]; then
    aws eks delete-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" &&
      aws eks wait cluster-deleted --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  else
    printf 'Owned node groups/Fargate profiles remain, or their status could not be verified\n' >&2
  fi
fi
```

### Delete Using Terraform

Use the original configuration, backend and workspace; apply only the reviewed destruction plan for the intended resources/account.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  terraform plan -destroy -out=reviewed-destroy.tfplan &&
    terraform apply reviewed-destroy.tfplan
fi
```

### Delete Using CDK

Use the original application, inputs, account and region and verify the target stack.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  npx cdk list
  npx cdk destroy EksAutoModeStack
fi
```

After completion, verify EKS/CloudFormation status and any remaining ELB, disk, NAT, log and IAM resources. Keep Auto Mode roles/policies until managed infrastructure deletion finishes. Do not assume cluster deletion removes a VPC, IAM role, logs or retained data owned elsewhere. No deletion commands were executed during the audit.

## Conclusion

There are several methods for creating an EKS cluster, each with its own advantages and disadvantages:

- **EKS Auto Mode**: Automates infrastructure operations; application readiness still requires validation
- **eksctl**: Simple and fast cluster creation
- **AWS Management Console**: Intuitive creation through GUI
- **AWS CLI**: Suitable for script automation
- **Terraform**: Manage infrastructure as code
- **AWS CDK**: Define infrastructure using programming languages

For production, choose the compute model and infrastructure tool that match your requirements, and validate IAM, connectivity, capacity, disruption and recovery behavior. A successful template or cluster creation is not evidence of production readiness.

### Audit validation scope

Both complete language versions were read and checked against official documentation and schemas. Validation covered shell/JSON/YAML, CDK compilation/synthesis, Terraform validate and mocked failure paths. No AWS provisioning, upgrades, deletion, application runtime/load testing or cost measurement was performed.
