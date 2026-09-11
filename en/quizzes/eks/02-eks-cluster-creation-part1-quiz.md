# EKS Cluster Creation Quiz - Part 1

> **Last Updated**: September 11, 2026

> Commands are independent examples, not a script to run from top to bottom. Use a dedicated training account/cluster, reviewed IAM permissions and a private temporary kubeconfig (`EXAMPLE_KUBECONFIG`). Replace example IDs and required variables. Creation commands incur charges. This audit checked sources, syntax and local fixtures; it did not provision AWS resources or verify application availability.

This quiz tests your understanding of concepts, tools, and best practices related to Amazon EKS cluster creation. It covers topics such as cluster creation methods, VPC configuration, and node group setup.

## Basic Concept Questions

1. Which tool has no built-in command that directly provisions an EKS control plane?
   * A) AWS Management Console
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>Show Answer</summary>

**Answer: D) kubectl**

kubectl manages resources through a Kubernetes API and has no native EKS provisioning command. An already installed infrastructure controller such as ACK can reconcile a resource submitted with kubectl into an EKS cluster; that is a controller integration, not a built-in kubectl AWS operation.

Tools that can be used to create Amazon EKS clusters include:

1. **AWS Management Console**:
   * Create EKS clusters through a web interface.
   * Suitable for beginners as it allows visual configuration of cluster components.
   * Guides through the cluster creation process via a step-by-step wizard.
2.  **AWS CLI**:

    * Create EKS clusters from the command line.
    * Uses the `aws eks create-cluster` command.
    * Suitable for scripts and automation.

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**:

    * A command-line tool specifically designed for EKS cluster creation.
    * Originally developed by Weaveworks; the current project is maintained in the eksctl-io organization with AWS/community contributions.
    * Can create a cluster with a single command.

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **Infrastructure as Code (IaC) tools**:

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    These tools allow defining and deploying EKS clusters as code.

kubectl is used to manage Kubernetes resources (pods, services, deployments, etc.) after a cluster is created. To connect to an EKS cluster, configure an authorized kubeconfig, commonly with `aws eks update-kubeconfig`.

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

After that, you can use kubectl to manage cluster resources.

</details>

2. What VPC component must be specified when creating an Amazon EKS cluster?
   * A) Public subnets only
   * B) Private subnets only
   * C) Subnets across at least 2 availability zones
   * D) NAT Gateway

<details>

<summary>Show Answer</summary>

**Answer: C) Subnets across at least 2 availability zones**

**Explanation:** When creating an Amazon EKS cluster, the VPC component that must be specified is subnets across at least 2 availability zones. This is an AWS requirement to ensure high availability of EKS clusters.

**EKS cluster VPC requirements:**

1. **Subnets required in at least 2 availability zones (AZs)**:
   * Since the EKS control plane is deployed across multiple availability zones, subnets must be specified in at least 2 availability zones when creating a cluster.
   * This supports regional control plane availability. Workload availability also needs replica placement, capacity, storage and dependency planning.
2. **Subnet types**:
   * You can use only public subnets, only private subnets, or a mix of public and private subnets.
   * For production environments, it's recommended to place worker nodes in private subnets for security, and use public subnets for load balancers.
3. **Subnet CIDR size**:
   * Each cluster subnet needs at least six available IPs for EKS; AWS recommends sixteen. Plan node/Pod/load-balancer capacity separately.
   * Since EKS assigns VPC IP addresses to each pod, sufficiently large CIDR blocks are needed based on expected pod counts.
4. **Tag requirements**:
   * Tags below concern discovery/ownership for specific integrations, not universal EKS creation requirements:
     * Legacy or controller-specific ownership tag: `kubernetes.io/cluster/<cluster-name>: shared`
     * Public subnets: `kubernetes.io/role/elb: 1`
     * Private subnets: `kubernetes.io/role/internal-elb: 1`

**VPC configuration example (using eksctl):**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["203.0.113.10/32"]
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
    public:
      us-west-2a:
        id: subnet-0123456789abcdef2
      us-west-2b:
        id: subnet-0123456789abcdef3
```

**VPC configuration using AWS CLI:**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

A NAT gateway is one possible internet egress path. Required VPC endpoints, mirrored images and private connectivity can support operation without internet access. Private subnet placement and eliminating internet egress are separate decisions. Replace the example VPC, subnets and client CIDR with reviewed actual values.

</details>

3. Which role separation applies when configuring a conventional EKS control plane with EC2 workers?
   * A) Only a cluster role is needed
   * B) Only an EC2 node role is needed
   * C) Separate cluster and EC2 node roles
   * D) Replace both with a Fargate execution role

<details>
<summary>Show Answer</summary>

**Answer: C) Separate cluster and EC2 node roles**

The cluster role trusts `eks.amazonaws.com` and lets EKS manage cluster infrastructure. Conventional EKS needs `AmazonEKSClusterPolicy` or equivalent permissions. The EC2 node role trusts `ec2.amazonaws.com` and is supplied through an instance profile. EKS configures the instance profile for managed node groups; node bootstrap does not create IAM roles.

The EC2 baseline is `AmazonEKSWorkerNodePolicy` and `AmazonEC2ContainerRegistryPullOnly`, or equivalent least privilege. CNI permissions are also required; prefer a separate IRSA/Pod Identity role. Without that, the node role needs the CNI permissions. The IPv4 `AmazonEKS_CNI_Policy` is not an IPv6 policy. Storage, load-balancer and logging controller permissions are not universally required on every node.

This example creates new conventional cluster/node roles. Use an authorized account/role and stop on errors. A name conflict does not attach policies to the existing role.

```bash
IAM_EXAMPLE_DIR=$(mktemp -d /tmp/eks-iam-example.XXXXXX)
: "${IAM_EXAMPLE_DIR:?}"
: "${NEW_CLUSTER_ROLE_NAME:?Choose an unused role name for this example}"
: "${NEW_NODE_ROLE_NAME:?Choose a different unused role name}"
cat > "$IAM_EXAMPLE_DIR/cluster-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "eks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
cat > "$IAM_EXAMPLE_DIR/node-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
# Attach policies only after successfully creating the new role.
aws iam create-role --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/cluster-trust.json" &&
aws iam attach-role-policy --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

if aws iam create-role --role-name "$NEW_NODE_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/node-trust.json"; then
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy &&
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
fi
```

Creating only a control plane with `CreateCluster` does not yet require an EC2 node role. Add it for EC2 compute. Fargate uses a distinct Pod execution role, separate from application AWS permissions. Auto Mode needs its additional cluster policies/`sts:TagSession` and minimal node-role policies. Review provisioning identity permissions such as `iam:PassRole` separately.

[Node role requirements](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [Auto Mode roles](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)

</details>

4. What is the correct command to create an EKS cluster using eksctl?
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>Show Answer</summary>

**Answer: B) `eksctl create cluster --name my-cluster --region us-west-2`**

**Explanation:** The correct command to create an EKS cluster using eksctl is `eksctl create cluster --name my-cluster --region us-west-2`. This command creates an EKS cluster with default settings in the specified name and region.

**eksctl command structure:**

* `eksctl`: Base command
* `create`: Action to create a resource
* `cluster`: Type of resource to create (cluster)
* `--name my-cluster`: Specify cluster name
* `--region us-west-2`: Specify AWS region

**Basic cluster creation command:**

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

Defaults depend on the eksctl version. Explicitly select EKS version, AL2023, node count and endpoints in the file below. Creation can provision VPC, node and IAM resources; review configuration and costs in an authorized test account.

**Advanced command with additional options:**

```bash
eksctl create cluster \
  --name my-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --with-oidc \
  --node-ami-family AmazonLinux2023 \
  --node-private-networking \
  --managed
```

**Cluster creation using a configuration file:**

```bash
# Create cluster.yaml file
cat > cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR:?Set your approved client CIDR}"]

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    amiFamily: AmazonLinux2023
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    ssh:
      allow: false
EOF

# Create cluster using configuration file
eksctl create cluster -f cluster.yaml
```

**Problems with other options:**

* `eksctl create-cluster`: Incorrect command format. eksctl uses spaces, not hyphens (-), to separate commands.
* `eksctl new cluster`: 'new' is not a valid eksctl command.
* `eksctl start cluster`: 'start' is not a valid eksctl command. Use the documented lifecycle commands rather than inventing a verb.

eksctl provides various commands for EKS cluster management:

* `eksctl create cluster`: Create a new cluster
* `eksctl get cluster`: List clusters
* `eksctl upgrade cluster`: Update a cluster
* `eksctl delete cluster`: Delete a cluster
* `eksctl create nodegroup`: Add a node group
* `eksctl scale nodegroup`: Scale a node group

</details>

5. Which Kubernetes versions can you choose for a new EKS cluster?
   * A) Only the latest upstream version
   * B) Always exactly latest plus two versions
   * C) Versions offered in EKS standard or extended support in the target region
   * D) Every Kubernetes version

<details>
<summary>Show Answer</summary>

**Answer: C) Versions offered in EKS standard or extended support in the target region**

An EKS minor receives **14 months of standard support from its EKS release date**, followed by **12 months of paid extended support**. The official list on September 11, 2026 is standard **1.34–1.36** and extended **1.31–1.33**. Upstream 1.37 release alone does not imply EKS support. Query the target region for versions available for new clusters.

Extended support is enabled by default; the upgrade policy and end-of-support dates can trigger automatic control plane upgrades. Plan node/add-on updates separately. Follow AWS support-date notices rather than treating the maximum support window as a reason to delay upgrades.

These are distinct examples for discovery, config generation, AWS creation and upgrading an existing cluster. Prepare the authorized target, roles, subnets and CIDR; do not blindly execute creation and upgrade examples as one workflow.

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table

# Generate a versioned config for review; this does not create the cluster.
EKS_VERSION_DIR=$(mktemp -d /tmp/eks-version.XXXXXX)
: "${EKS_VERSION_DIR:?}"
eksctl create cluster --name "${NEW_CLUSTER_NAME:?}" --region "$EXAMPLE_REGION" \
  --version 1.36 --dry-run > "$EKS_VERSION_DIR/version-example.yaml"
# Review all generated defaults, AMI, endpoint CIDRs and costs before creating.

# AWS CLI creation uses --kubernetes-version; the API JSON field is version.
aws eks create-cluster --name "$NEW_CLUSTER_NAME" --region "$EXAMPLE_REGION" \
  --kubernetes-version 1.36 --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API \
  --resources-vpc-config "subnetIds=${SUBNET_A:?},${SUBNET_B:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"

# Updating an existing control plane is a separate operation.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query cluster.version
# Only after upgrade-readiness checks and choosing the next supported minor:
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

Forward control plane upgrades must advance one minor at a time. Review required features, remaining support and add-on/workload compatibility together. Test the target version instead of assuming an older version is always safer. Grepping version strings from add-on metadata does not replace cluster-version discovery.

[EKS version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

</details>

6. Which option does not provision compute for an EKS workload by itself?
   * A) Managed node groups
   * B) Self-managed node groups
   * C) Fargate profiles
   * D) A Kubernetes namespace

<details>

<summary>Show Answer</summary>

**Answer: D) A Kubernetes namespace**

A namespace organizes Kubernetes resources but does not provide compute. Managed EC2 node groups, self-managed EC2 nodes and Fargate profiles are valid compute paths. EKS Auto Mode also provisions managed nodes, and Hybrid Nodes connect customer-managed on-premises/edge capacity. These mechanisms do not all use the managed-node-group API.


Creation commands below are alternatives for an existing cluster and unused group/profile names. Replace all required variables with reviewed values. Check CNI/node authorization and private-subnet connectivity. Fargate requires a Pod execution role, compatible Pods and private subnets; its profile does not create application Pods.

**1. Managed Node Groups:**

* **Features**:
  * AWS manages node provisioning and lifecycle
  * Automatic EC2 instance creation and registration
  * Automatic ASG (Auto Scaling Group) configuration
  * Operator-initiated node Kubernetes version updates
  * EC2 health replacement; EKS node repair needs its supported health signals/configuration
  * Operator-initiated AMI updates through the managed workflow
*   **Creation method**:

    ```bash
    # Create managed node group using eksctl
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-mng --managed --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5

    # Create managed node group using AWS CLI
    aws eks create-nodegroup \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --nodegroup-name my-mng --ami-type AL2023_x86_64_STANDARD \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --instance-types t3.medium \
      --scaling-config minSize=1,maxSize=5,desiredSize=3 \
      --node-role "${NODE_ROLE_ARN:?}"
    ```

**2. Self-managed Node Groups:**

* **Features**:
  * User manages node provisioning and lifecycle
  * More customization options
  * Can use custom AMIs or bootstrap scripts
  * Suitable for specific instance types or configuration requirements
*   **Creation method**:

    ```bash
    # Create self-managed node group using eksctl
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-smng --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5 \
      --managed=false

    # Can also be created manually using CloudFormation or EC2 launch templates.
    ```

**3. Fargate Profiles:**

* **Features**:
  * Serverless container execution environment
  * No node management required
  * Per-pod resource allocation and billing
  * Selective execution based on specific namespaces and labels
*   **Creation method**:

    ```bash
    # Create Fargate profile using eksctl
    eksctl create fargateprofile \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-fargate-profile \
      --namespace my-namespace \
      --labels app=my-app

    # Create Fargate profile using AWS CLI
    aws eks create-fargate-profile \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --fargate-profile-name my-fargate-profile \
      --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --selectors '[{"namespace":"my-namespace","labels":{"app":"my-app"}}]'
    ```

**Comparison of each option:**

| Feature | Managed node groups | Self-managed nodes | Fargate |
| --- | --- | --- | --- |
| Infrastructure management | AWS manages replacement workflow; operators configure updates/scaling | Operators manage AMI, bootstrap and lifecycle | AWS manages hosts; users manage apps, profiles and requests |
| Cost | Evaluate instance, utilization, commitment and operations | Evaluate optimization together with operations | Compare allocated Pod sizes, runtime and constraints |
| Scaling | Separate node autoscaler/policy required | Separate automation required | Provides compute for matching Pods; application replica scaling is separate |

Auto Mode NodePools and Fargate profiles are different resources from EC2 managed node groups. Fargate still requires workload, security and availability management, and is not universally cheaper or more expensive.

</details>

7. Which is not an AWS-published EKS-optimized AMI family for new EKS 1.36 nodes?
   * A) Amazon Linux 2023
   * B) Bottlerocket
   * C) Windows Server 2022
   * D) Ubuntu Core

<details>
<summary>Show Answer</summary>

**Answer: D) Ubuntu Core**

Do not treat Ubuntu Core as an AWS-published EKS-optimized AMI. Canonical Ubuntu Server images and customer-built AMIs have separate publishers, compatibility and support paths; they are not the same product as Ubuntu Core.

**Choices for this example**

- **AL2023**: Use an EKS-optimized AMI and `nodeadm` bootstrap. Check Kubernetes minor, CPU architecture, region and CNI compatibility.
- **Bottlerocket**: A container-focused OS with configuration and update mechanisms distinct from general-purpose Linux nodes.
- **Windows**: Match supported Windows Server host/container versions and prepare Windows networking, authentication and system-workload prerequisites. This is not a Windows example for Auto Mode/Fargate.

**AL2 is a migration source for legacy environments.** EKS-optimized AL2 AMI publication/support ended November 26, 2025; AL2 OS support ended June 30, 2026. EKS extended Kubernetes support does not extend AL2 support. Do not recommend AL2 for new EKS 1.36 deployments.

```bash
# Alternative examples; create only the reviewed group needed by your workload.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}"   --name al2023-nodes --managed --node-ami-family AmazonLinux2023 --node-private-networking

eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name bottlerocket-nodes --managed --node-ami-family Bottlerocket --node-private-networking

# Only after preparing the cluster for Windows:
eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name windows-nodes --managed --node-ami-family WindowsServer2022FullContainer --node-private-networking
```

Custom AMIs can also be used in managed node group launch templates. Pinning an AMI requires verifying its OS/runtime, cluster metadata and bootstrap configuration. Installing only `docker.io` on an arbitrary Ubuntu image does not produce a working EKS node. Use a Canonical image for the target EKS version with a reviewed eksctl/launch-template configuration. The advanced question distinguishes launch-template `ImageId`, node group `amiType` and user-data merging constraints.

Review security updates, measured workload performance, Kubernetes/driver compatibility, operations and special requirements such as GPUs when selecting an image.

[AL2 transition](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html) · [AL2023/nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [Windows prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)

</details>

8. What are the defaults when endpoint access is omitted from the CreateCluster API?
   * A) Public enabled, private disabled
   * B) Private only
   * C) Both endpoints enabled
   * D) Access cannot be changed after creation

<details>
<summary>Show Answer</summary>

**Answer: A) Public enabled, private disabled**

The API defaults to public enabled and private disabled. eksctl, CDK and console creation paths can explicitly select different settings; this is not a universal tool default. Access settings can be changed after creation.

| Public | Private | Access path |
| --- | --- | --- |
| On | Off | Public endpoint and publicAccessCidrs; also account for actual node/CI egress addresses |
| On | On | Private path for requests in the VPC; allowed public CIDRs externally |
| Off | On | Private path from the VPC or connected networks |
| Off | Off | Invalid configuration |

**The cluster security group controls private-endpoint and kubelet traffic, not public-endpoint access.** `publicAccessCidrs` applies only to the public endpoint. Authentication/authorization is still required independently of network reachability. Replace the IPv4 example CIDR with the actual approved client egress address.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.resourcesVpcConfig

# Select the actual approved client egress CIDR, not an arbitrary example range.
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text)
: "${ENDPOINT_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

Verify that the prior update is `Successful` and that administration/CI networks can use private DNS, routing and API access before disabling public access. Do not immediately send overlapping asynchronous updates; set both access flags in one request.

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

Private API access and eliminating internet egress are separate design choices. Evaluate identity, network and operational controls together; private access alone does not guarantee security or availability. Account for VPN/Direct Connect/administration hosts and connectivity costs. IPv6 endpoints and Hybrid Nodes have additional DNS/CIDR considerations covered in the official guidance.

[Cluster endpoint access controls](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)

</details>

9. What is NOT a consideration when selecting instance types for node groups in Amazon EKS clusters?
   * A) Workload requirements (CPU, memory, storage)
   * B) Cost optimization
   * C) The local kubeconfig context alias
   * D) Instance generation (e.g., t3 vs t2)

<details>

<summary>Show Answer</summary>

**Answer: C) The local kubeconfig context alias**

A kubeconfig alias is a local client name and does not change instance performance, pricing or availability. In contrast, whether a type is offered in the required AZs, actual capacity and account quotas are important selection constraints.

**Actual considerations when selecting node group instance types:**

1. **Workload requirements (CPU, memory, storage)**:
   * Select instance types that match application resource requirements
   * Memory-intensive workloads: Memory optimized instances such as r5, r6g
   * Compute-intensive workloads: Compute optimized instances such as c5, c6g
   * Balanced workloads: General purpose instances such as m5, m6g
   * GPU workloads: Accelerated computing instances such as p3, g4dn
2. **Cost optimization**:
   * On-demand vs Spot instances
   * Reserved Instances or Savings Plans
   * Proper size instance selection (avoid over-provisioning)
   * Cost savings through ARM-based Graviton instances (e.g., m6g, c6g)
3. **Instance generation**:
   * Compare generation-specific price/performance for the actual workload
   * For burstable families, include CPU credit behavior and baseline performance
   * Latest generations provide enhanced networking, storage performance, etc.
4. **Networking requirements**:
   * Enhanced networking support (ENA, EFA, etc.)
   * Network bandwidth requirements
   * Networking limits related to maximum pods per instance
5. **Storage requirements**:
   * Whether local instance storage is needed (e.g., i3, d3 instances)
   * EBS optimization support
   * Storage throughput and IOPS requirements
6. **CPU architecture**:
   * x86 (Intel, AMD) vs ARM (AWS Graviton)
   * Application compatibility considerations

**Availability zones and node group deployment:**

Required AZ coverage constrains usable instance types. A catalog offering is not a guarantee of immediate capacity:

* Deploy node groups across multiple availability zones for high availability
* Plan node capacity and Pod topology spread, then verify actual placement
* Can select all availability zones in the region or specific availability zones

```bash
# Deploy node group to specific availability zones
eksctl create nodegroup \
  --cluster "${EXAMPLE_CLUSTER:?}" --region us-west-2 \
  --name my-nodegroup --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --node-zones us-west-2a,us-west-2b
```

**Instance type selection examples:**

1. **Web application servers**:
   * General purpose instances: t3.medium, m5.large
   * Cost-effective with balanced performance
2. **Databases**:
   * Memory optimized instances: r5.xlarge, r6g.xlarge
   * High memory to CPU ratio
3. **Batch processing jobs**:
   * Compute optimized instances: c5.xlarge, c6g.xlarge
   * High CPU performance
4. **Machine learning workloads**:
   * GPU instances: p3.2xlarge, g4dn.xlarge
   * Accelerated computing capabilities

The families above are examples, not a current product catalog or measured performance ranking. Review workload, price, architecture, drivers and offerings/capacity in the required AZs together.

</details>

10. What is the correct command to configure kubectl after creating an Amazon EKS cluster?
    * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    * C) `kubectl config set-cluster my-cluster --region us-west-2`
    * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>Show Answer</summary>

**Answer: A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**Explanation:** The correct command to configure kubectl after creating an Amazon EKS cluster is `aws eks update-kubeconfig --name my-cluster --region us-west-2`. This command uses the AWS CLI's EKS module to update the kubeconfig file for the specified cluster.

**kubectl configuration process:**

1. **Updating kubeconfig file**:
   * The kubeconfig file stores configuration information needed for kubectl to communicate with Kubernetes clusters.
   * Selection order is explicit `--kubeconfig`, the first `KUBECONFIG` path, then `~/.kube/config`.
   * The command merges cluster/exec-auth configuration and changes the current context in the selected file; it does not grant cluster permissions.
2. **Command components**:
   * `--name`: EKS cluster name
   * `--region`: AWS region where the cluster is located
   * `--kubeconfig` (optional): Custom kubeconfig file path
   * `--role-arn` (optional): IAM role to use for cluster access
3.  **Full command example**:

    ```bash
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
4.  **Additional options**:

    ```bash
    # Use custom kubeconfig file
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # Use specific IAM role
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EksAdminRole --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # Set alias
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --alias my-cluster-alias --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
5.  **Verify configuration**:

    ```bash
    # Check current context
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config current-context

    # List all contexts
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config get-contexts

    # Test cluster connection
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" cluster-info
    ```

**Problems with other options:**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`: This command does not exist. There is no `get-kubeconfig` subcommand in AWS CLI.
* `kubectl config set-cluster my-cluster --region us-west-2`: This command has incorrect syntax. `kubectl config set-cluster` does not support the `--region` flag and does not automatically configure the authentication information needed for EKS clusters.
* `eksctl configure kubectl --name my-cluster --region us-west-2`: This command does not exist. eksctl does not have a `configure kubectl` subcommand. When creating a cluster with eksctl, kubeconfig is automatically configured, but for existing clusters, use `aws eks update-kubeconfig` or `eksctl utils write-kubeconfig`.

**Writing configuration for an existing cluster with eksctl:**

For an existing cluster, write its configuration without creating another cluster:

```bash
eksctl utils write-kubeconfig --cluster my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

This writes kubeconfig for the existing cluster. Verify IAM authentication and access-entry/RBAC authorization separately. Cluster creation also writes kubeconfig by default unless disabled.

**Managing multiple clusters:**

When managing multiple EKS clusters, you can add them to the kubeconfig file by running the `aws eks update-kubeconfig` command for each cluster:

```bash
# Configure first cluster
aws eks update-kubeconfig --name cluster1 --region us-west-2 --alias cluster1-west --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Configure second cluster
aws eks update-kubeconfig --name cluster2 --region us-east-1 --alias cluster2-east --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Switch context
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --context cluster1-west get nodes
```

Therefore, the correct command to configure kubectl after creating an Amazon EKS cluster is `aws eks update-kubeconfig --name my-cluster --region us-west-2`.

</details>

## Hands-on Exercises

### Exercise 1: Create EKS Cluster Using eksctl

**Scenario:** prepare a conventional EC2 managed-node-group cluster for a development team. This is a training design, not evidence of tested production readiness or a measured cost result.

**Requirements:** use two AZs, two `t3.medium` AL2023 nodes initially, scaling bounds of 2–5, private node networking, and both API endpoints with an approved public CIDR. Bounds alone do not install an autoscaler. Check burstable-instance CPU credits, memory, IP capacity, quotas and actual workload needs before choosing `t3.medium`.

<details>
<summary>Show Answer</summary>

**1. Prepare tools and identity.** Use the checksummed, architecture-specific installation instructions in [Part 1](../../eks/02-eks-cluster-creation-part1.md). This example was reviewed against EKS 1.36 and eksctl 0.230.0; check the Region's available EKS versions and compatible client/add-on versions before running it. `kubectl` must satisfy version-skew limits. Use an existing approved operator IAM role that your login can assume; provisioning permissions and Kubernetes access are separate.

**2. Generate and review a private local configuration.** The generated name is for a new training cluster. The public CIDR must be your actual allowed egress range. The two AZs are examples for `us-west-2`, subject to offerings and capacity.

```bash
# Use a dedicated training account/role with reviewed provisioning permissions.
aws sts get-caller-identity
eksctl version
kubectl version --client
EKS_LAB_DIR=$(mktemp -d /tmp/eks-creation-lab.XXXXXX)
: "${EKS_LAB_DIR:?}"
EKS_LAB_CLUSTER="creation-quiz-$(date +%s)-$$"
EKS_LAB_REGION=us-west-2
EKS_LAB_KUBECONFIG="$EKS_LAB_DIR/kubeconfig"
: "${APPROVED_API_CIDR:?Set your actual approved administration egress CIDR}"
: "${OPERATOR_ROLE_ARN:?Set an existing IAM role ARN, not an STS session ARN}"

cat > "$EKS_LAB_DIR/cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_LAB_CLUSTER}
  region: ${EKS_LAB_REGION}
  version: "1.36"
availabilityZones: ["us-west-2a", "us-west-2b"]
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR}"]
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: false
  accessEntries:
    - principalARN: "${OPERATOR_ROLE_ARN}"
      type: STANDARD
      accessPolicies:
        - policyARN: arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy
          accessScope:
            type: cluster
managedNodeGroups:
  - name: dev-ng
    amiFamily: AmazonLinux2023
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    privateNetworking: true
    disableIMDSv1: true
    ssh:
      allow: false
    tags:
      Environment: development
      Owner: training
EOF

# Review the local configuration; this command does not create resources.
eksctl create cluster -f "$EKS_LAB_DIR/cluster.yaml" --dry-run \
  > "$EKS_LAB_DIR/resolved.yaml"
```

This grants the named operator cluster-admin access specifically for the lab and disables automatic creator-admin access. It does not create the operator role or grant the caller permission to assume it. eksctl creates the required cluster/node roles; review its generated policy scope. The conventional baseline can place VPC CNI permissions on the node role. For stronger workload isolation, configure a dedicated `aws-node` role using the official CNI IAM guidance. Do not add broad image-push, DNS, storage, load-balancer or logging permissions to all nodes merely because those add-ons might be used later.

**3. Provision only after reviewing the configuration and costs.** The default new-VPC topology can create NAT and other billed infrastructure. `eksctl` uses CloudFormation for VPC/subnet/security-group/role/cluster/node-group resources. Failure can leave partial resources; inspect its stack events rather than assuming automatic complete cleanup.

```bash
# Provisioning step: creates billable AWS resources.
if eksctl create cluster -f "${EKS_LAB_DIR:?}/cluster.yaml" --write-kubeconfig=false; then
  EKS_LAB_ARN=$(aws eks describe-cluster \
    --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
    --query cluster.arn --output text)
  : "${EKS_LAB_ARN:?Could not record the created cluster ARN}"
  aws eks update-kubeconfig --name "$EKS_LAB_CLUSTER" \
    --region "$EKS_LAB_REGION" --role-arn "${OPERATOR_ROLE_ARN:?}" \
    --kubeconfig "${EKS_LAB_KUBECONFIG:?}" --alias "$EKS_LAB_CLUSTER"
fi
```

**4. Verify actual status, access and scaling bounds.** Wait for `ACTIVE` node-group/cluster states and `Ready` nodes, inspect unhealthy system Pods and verify expected AZ placement. A successful create request or an RBAC listing alone does not establish a secure, working cluster.

```bash
aws eks describe-cluster --name "${EKS_LAB_CLUSTER:?}" \
  --region "${EKS_LAB_REGION:?}" \
  --query 'cluster.{status:status,version:version,endpoint:resourcesVpcConfig,access:accessConfig}'
aws eks describe-nodegroup --cluster-name "$EKS_LAB_CLUSTER" \
  --nodegroup-name dev-ng --region "$EKS_LAB_REGION" \
  --query 'nodegroup.{status:status,scaling:scalingConfig,ami:amiType}'
kubectl --kubeconfig "${EKS_LAB_KUBECONFIG:?}" config current-context
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get nodes -o wide
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get pods -n kube-system
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" auth can-i get nodes
```

**5. Add only the required components.** Cluster Autoscaler requires the scoped IAM/service-account/discovery setup in advanced question 2; bounds do not react to workload demand on their own. `kubectl top` requires an installed and healthy Metrics Server. In the audited Metrics Server 0.9.0 baseline, Kubernetes 1.34+ is supported; verify the version actually installed. Measure representative usage before claiming cost savings or sizing correctly.

**6. Clean up this training cluster.** First remove any lab-created LoadBalancer Services/Ingresses and wait for their controllers to release AWS resources; inspect PVC reclaim policies and retained volumes. This exercise itself creates no such application resources. Then delete only the recorded cluster:

```bash
# Only after removing this lab's workloads and checking retained resources.
if CURRENT_LAB_ARN=$(aws eks describe-cluster \
  --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
  --query cluster.arn --output text) &&
  [ "$CURRENT_LAB_ARN" = "${EKS_LAB_ARN:?Original cluster ARN required}" ]; then
  eksctl delete cluster --name "$EKS_LAB_CLUSTER" --region "$EKS_LAB_REGION" --wait
else
  printf '%s\n' 'Cluster lookup/identity mismatch; no deletion attempted.' >&2
fi
```

Check CloudFormation and AWS resource inventories afterward for failed deletions, retained volumes and independently created roles/endpoints. Keep the configuration/ARN record until cleanup is confirmed; remove the temporary kubeconfig directory locally when no longer needed.

</details>

### Exercise 2: Create EKS Cluster Using AWS Management Console

**Scenario:** review a conventional managed-node-group design that may inform a later production deployment. Its workload sizing, routing, IAM, availability, upgrades and recovery remain environment-specific assumptions requiring tests. This walkthrough has not been provisioned or load-tested during the audit.

<details>
<summary>Show Answer</summary>

**1. Prepare separate IAM roles.**

- Cluster role: trust `eks.amazonaws.com` and attach `AmazonEKSClusterPolicy`.
- EC2 node role: trust `ec2.amazonaws.com`, attach `AmazonEKSWorkerNodePolicy` and `AmazonEC2ContainerRegistryPullOnly`. Give VPC CNI its own IRSA/Pod Identity role where supported. If deliberately using the simpler IPv4 node-role fallback, explicitly attach `AmazonEKS_CNI_Policy` and document the shared-permission tradeoff.
- Provisioning/operator identity: use approved resource-scoped IAM permissions and `iam:PassRole` for these roles. Add an EKS access entry for the existing operator role with the lab's required access policy. Creating kubeconfig alone grants no Kubernetes authorization.

**2. Review VPC and subnets.** The following official example remains a usable reference; the date in its URL is not an EKS version:

```text
https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
```

Read the CloudFormation template before creating a uniquely named training stack. Its defaults create a VPC with **two public and two private subnets across two AZs, an internet gateway, and two NAT gateways/EIPs**. Thus it is a NAT-backed design with outbound internet, not a no-egress private cluster. Review CIDR overlap, AZs, IP capacity and NAT charges rather than retaining defaults for production.

Record `VpcId`, `SubnetIds` and `SecurityGroups`. `SubnetIds` contains **both public and private subnets**; inspect each route table and select the actual private subnets for nodes. The output custom security group is not proof that all required communication rules exist. Review the EKS cluster security group, additional groups and control-plane/node communication rules.

**3. Create a conventional cluster.** In the EKS console, choose the custom configuration path and disable Auto Mode for this exercise. Select an available, compatible version in EKS standard support (1.36 is the audited example), the cluster service role, and the reviewed VPC/subnets.

- Select API access-entry authentication and grant the named operator appropriate access; do not rely on an unexplained creator-admin default.
- For private-only API access, verify the administration network's private routing/DNS first. Alternatively enable public and private access and restrict `publicAccessCidrs` to the approved administration egress range.
- Keep compatible VPC CNI, kube-proxy and CoreDNS add-ons for this conventional EC2 cluster; review their configuration/permissions. Enable the required control-plane logs and account for logging charges.
- Review and create the cluster, then wait for `ACTIVE`. Creation duration is variable; a quoted number of minutes is not a completion test.

**4. Add a managed node group.** Select the EC2 node role, AL2023 x86_64 AMI, and a supported instance type such as the illustrative `m5.large`. The example uses a 50 GiB root disk, desired size 3, minimum 2 and maximum 5, and the reviewed private subnets. These are sizing examples, not production recommendations. Configure access, IMDS and storage encryption as required; wait for the node group to become `ACTIVE` and nodes to become `Ready`.

**5. Verify access and inspect the real AWS security groups.** Use the cluster name recorded in the console and your approved operator role:

```bash
CONSOLE_LAB_DIR=$(mktemp -d /tmp/eks-console-lab.XXXXXX)
: "${CONSOLE_LAB_DIR:?}"
CONSOLE_KUBECONFIG="$CONSOLE_LAB_DIR/kubeconfig"
aws eks update-kubeconfig --name "${CONSOLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --role-arn "${OPERATOR_ROLE_ARN:?}" \
  --kubeconfig "$CONSOLE_KUBECONFIG" --alias "$CONSOLE_CLUSTER"
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get pods -n kube-system

# Security groups are AWS resources; kubeconfig does not contain their rules.
aws eks describe-cluster --name "$CONSOLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_CLUSTER_SG_ID:?Copy the cluster SG ID from the result above}"
```

**6. Optional NetworkPolicy exercise.** First verify that the selected CNI and its configuration enforce NetworkPolicy. AWS VPC CNI policy support must be enabled and supported by the node/OS setup. The following ingress-only default deny is confined to a newly created empty lab namespace; it does not deny egress or prove policy enforcement just because `apply` succeeds.

```bash
# An optional isolated policy example, after enabling CNI policy enforcement.
NP_LAB_NAMESPACE="np-quiz-$(date +%s)-$$"
if kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" create namespace "$NP_LAB_NAMESPACE"; then
  NP_LAB_UID=$(kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    get namespace "$NP_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}')
  : "${NP_LAB_UID:?Namespace identity lookup failed}"
  cat > "${CONSOLE_LAB_DIR:?}/default-deny.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: ${NP_LAB_NAMESPACE}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
EOF
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    apply -f "$CONSOLE_LAB_DIR/default-deny.yaml"
fi
```

Test allowed and denied traffic with dedicated test Pods and add the application's required allow policies before using this pattern for real workloads. Do not apply it to an existing shared `default` namespace. Remove the isolated namespace when finished:

```bash
# Remove only the namespace created above, after confirming its UID.
if CURRENT_NP_UID=$(kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" \
  get namespace "${NP_LAB_NAMESPACE:?}" -o jsonpath='{.metadata.uid}') &&
  [ "$CURRENT_NP_UID" = "${NP_LAB_UID:?Original namespace UID required}" ]; then
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" delete namespace "$NP_LAB_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace lookup/identity mismatch; no deletion attempted.' >&2
fi
```

**7. Console cleanup:** remove lab workloads and wait for associated cloud resources to be released, then delete this lab's managed node group, wait for deletion, and delete the lab cluster. Delete the lab VPC CloudFormation stack only after its EKS resources and external dependencies are gone. Remove only IAM roles/endpoints created exclusively for this lab; retain shared resources and inspect any failed or retained resources. This review did not execute those operations.

</details>

## Advanced Topics

The following are questions about advanced topics related to Amazon EKS cluster creation. This section tests your understanding of advanced concepts and best practices for EKS cluster creation.

1. What is a main benefit of custom launch templates for EKS EC2 managed node groups?
   * A) Guaranteed shorter cluster creation
   * B) Custom node user data and volume configuration
   * C) Control plane plug-in installation
   * D) Automatic updates of all existing nodes to each newly published AMI

<details>
<summary>Show Answer</summary>

**Answer: B) Custom node user data and volume configuration**

Launch templates customize **EC2 managed node groups**, including storage, instance metadata and OS-specific user data. They do not configure the EKS control plane or EKS Auto Mode nodes.

**AL2023 user data:** use MIME multipart data. With an EKS-selected AMI (no `ImageId` in the template), EKS supplies/merges the node configuration. With a custom AMI ID, supply the complete `NodeConfig` described in advanced question 5. AL2023's systemd services run `nodeadm`; do not call `/etc/eks/bootstrap.sh`, run `nodeadm init` again, or start kubelet manually. Additional software must support the selected OS and have a reachable, trusted package source.

This minimal customization is for the EKS-selected AL2023 AMI case; it only creates an application directory:

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_CUSTOMIZATION"

--EKS_CUSTOMIZATION
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_CUSTOMIZATION--
```

**Storage:** the following is one valid `LaunchTemplateData` fragment. Confirm the AMI's root device name. Attaching a volume does not format or mount it. Both example volumes are encrypted and deleted with the instance; use a CSI-managed PV and an appropriate reclaim/backup policy for application data that must survive node replacement.

```json
{
  "BlockDeviceMappings": [
    {
      "DeviceName": "/dev/xvda",
      "Ebs": {
        "VolumeSize": 100,
        "VolumeType": "gp3",
        "Iops": 3000,
        "Throughput": 125,
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    },
    {
      "DeviceName": "/dev/sdf",
      "Ebs": {
        "VolumeSize": 500,
        "VolumeType": "gp3",
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    }
  ]
}
```

**Networking and metadata:** replace the example security group with one whose rules permit the required control plane, node, DNS and workload traffic. When custom security groups are provided, EKS does **not** automatically add the cluster security group. Specify security groups at either the instance or network-interface level, not both.

```json
{
  "NetworkInterfaces": [
    {
      "DeviceIndex": 0,
      "Groups": ["sg-0123456789abcdef0"],
      "DeleteOnTermination": true
    }
  ],
  "MetadataOptions": {
    "HttpEndpoint": "enabled",
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1
  }
}
```

The hop limit of 1 assumes Pods use IRSA or EKS Pod Identity rather than node credentials. Workloads that require IMDSv2 access from a container can require a hop limit of 2. Neither this setting nor IMDSv2 creates isolation for `hostNetwork` Pods. Multiple interfaces, placement and instance-store devices require compatible instance types and the EKS launch-template restrictions; they are not universally interchangeable options.

**Create the node group:** choose either the eksctl configuration or the AWS CLI example after reviewing real IDs, permissions and network routes. These are alternatives, not sequential instructions:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    subnets: ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
```

```bash
# Use an existing reviewed template version and a new node group name.
aws eks create-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --launch-template "id=${LAUNCH_TEMPLATE_ID:?},version=${LAUNCH_TEMPLATE_VERSION:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --node-role "${NODE_ROLE_ARN:?}"
```

Keep `SubnetId` and `IamInstanceProfile` out of the launch template: subnets and the node IAM role belong to the node-group request. With a launch template, do not also set node-group `diskSize` or `remoteAccess`. Set instance type(s) in the template **or** the node-group request. When `ImageId` is present, omit node-group `amiType`, `releaseVersion` and `version`, and verify the custom AMI's kubelet/control-plane compatibility.

An explicit `ImageId` pins an AMI; a template without it can use an EKS-selected AMI. Neither case automatically updates existing nodes whenever an AMI is published. Updating a custom template requires a new version of the **same** template and an explicit node-group update, which replaces instances.

References: [launch-template constraints](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [CreateNodegroup fields](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html), [AL2023 initialization](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html).

</details>

2. Which approach is insufficient by itself to optimize EKS costs?
   * A) Use Spot for interruption-tolerant workloads
   * B) Configure and authorize Cluster Autoscaler
   * C) Choose the newest instance generation for every workload without measurement
   * D) Evaluate Fargate selectively against workload needs and total cost

<details>
<summary>Show Answer</summary>

**Answer: C) Choose the newest instance generation for every workload without measurement**

Choosing every node solely because it is the newest generation is not sufficient cost analysis. Compare the workload's architecture, throughput, latency, memory, regional availability and interruption tolerance. A newer generation can be more economical; neither newer nor older is always cheaper for the same useful work.

1. **Spot and diversification:** AWS advertises discounts of up to 90% versus On-Demand for Spot; this is a possible pricing discount, not a measured or guaranteed saving for this lab. Account for interruptions and replacement capacity. For Cluster Autoscaler, mixed types in one node group should have the same CPU/memory/GPU shape because scheduling simulation uses the first type. Verify any local-disk dependency separately.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: spot-ng
    amiFamily: AmazonLinux2023
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    spot: true
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 5
```

2. **Cluster Autoscaler:** minimum/maximum sizes only set scaling bounds. Install and authorize a controller to change desired capacity in response to unschedulable Pods and removable capacity. Do not give every node broad autoscaling permissions. Before this **new installation**, prepare a `kube-system/cluster-autoscaler` service account with a dedicated IRSA role (OIDC trust scoped to that service account) or a supported Pod Identity setup. Scope scaling writes to the intended cluster's Auto Scaling groups, and tag those groups with `k8s.io/cluster-autoscaler/enabled=true` and `k8s.io/cluster-autoscaler/<cluster-name>=owned`. Node-group resource tags alone do not prove ASG discovery is configured.

The controller minor version must match the cluster. Chart 9.59.0 defaults to controller 1.35.0, so this EKS 1.36 example explicitly selects 1.36.1. Other cluster versions need a matching controller version. Confirm there is no existing CA installation managing the same groups.

```bash
# EKS 1.36 example: first prepare the dedicated service account/IAM role
# and discovery tags on the target Auto Scaling groups.
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  --set-string "autoDiscovery.clusterName=${EXAMPLE_CLUSTER:?}" \
  --set-string "awsRegion=${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  --wait --timeout 5m
```

3. **Fargate and right-sizing:** Fargate reduces host-management work but charges for allocated resources and runtime, not only measured CPU use. Match profiles to supported Pods and private-subnet networking; compare total cost against EC2. `kubectl top` requires Metrics Server, and a short sample is not a capacity plan.
4. **Graviton:** test ARM64 images and dependencies before creating an ARM node group. A generation-specific “up to 40% better price/performance” claim is not a universal 40% bill reduction or a guarantee of equal performance.

```bash
# Metrics Server must already be installed and healthy.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top nodes
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top pods --all-namespaces

# Alternative compute examples: each creates separately billed resources.
eksctl create fargateprofile --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name fp-dev --namespace dev
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name arm-ng \
  --managed --node-ami-family AmazonLinux2023 \
  --node-type m6g.large --nodes 2 --node-private-networking
```

5. **Commitments:** Reserved Instances and Savings Plans can reduce qualifying predictable usage costs. Advertised savings of up to 72% depend on the product, term, payment option and usage; unused commitments can erase savings.
6. **Requests and limits:** measure representative workloads before choosing values. Requests affect scheduling and autoscaler decisions; overly small limits can cause CPU throttling or OOM termination. These are illustrative per-container values:

```yaml
# Fragment inside spec.template.spec.containers[].
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

7. **Cost allocation:** use Cost Explorer and configured allocation reports/tools. Kubernetes labels do not automatically become activated AWS cost-allocation tags. Include control plane, Auto Mode fees where applicable, storage, load balancers, NAT, transfer and logging costs.

References: [CA on EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html), [CA chart](https://github.com/kubernetes/autoscaler/tree/master/charts/cluster-autoscaler), [CA 1.36.1](https://github.com/kubernetes/autoscaler/releases/tag/cluster-autoscaler-1.36.1), [Spot pricing](https://aws.amazon.com/ec2/spot/), [Fargate pricing](https://aws.amazon.com/fargate/pricing/), [Graviton](https://aws.amazon.com/ec2/graviton/), [Savings Plans](https://aws.amazon.com/savingsplans/).

</details>

3. Which design satisfies both private-only Kubernetes API access and no outbound internet from nodes/Pods?
   * A) Private API, private node subnets without internet egress, required service endpoints and a private administration path
   * B) Private nodes alone, leaving all API and egress settings unchanged
   * C) Disable both public and private Kubernetes API endpoints
   * D) Disable the public API while retaining unrestricted NAT egress

<details>
<summary>Show Answer</summary>

**Answer: A) Private API, private node subnets without internet egress, required service endpoints and a private administration path**

Separate two decisions: **who can reach the Kubernetes API** and **where nodes/Pods can send traffic**. A private-only API does not remove NAT routes, block workload egress or ensure that every packet stays in one VPC. Connected networks can reach the private API when routing, DNS, security groups and authorization permit.

For this question, the requirement is both private-only API access and nodes/Pods without outbound internet. Enable the private endpoint, disable the public endpoint, use private node subnets without an internet egress path, and provide the service endpoints, registry images and administration path the workloads need.

**Endpoint transition:** first enable private access, wait for that update to succeed, and test authenticated `kubectl` access from the intended private network. Only then use the separate private-only alternative below. Check the returned update until `Successful`, then recheck access. The public endpoint is restricted by `publicAccessCidrs`, not the cluster security group; the latter governs private endpoint traffic.

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

**Node placement:** this fragment uses an existing VPC and private subnets; replace IDs and verify routes before use. It does not create VPC endpoints or remove existing NAT routes. Running eksctl from an unrelated internet-only workstation will not provide access to a private-only Kubernetes API.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
managedNodeGroups:
  - name: private-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 3
    privateNetworking: true
```

**AWS service connectivity:** the following ECR and S3 examples are only part of the design. Review existing endpoints first to avoid duplicate private-DNS conflicts. Interface endpoints need private DNS and HTTPS ingress from intended clients; the S3 gateway endpoint needs the private route tables and suitable endpoint/bucket policies.

```bash
# Example fragments for a reviewed no-internet VPC design.
# Interface endpoint SG must allow HTTPS from the intended nodes/clients.
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.api" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.dkr" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.s3" \
  --vpc-endpoint-type Gateway \
  --route-table-ids "${PRIVATE_ROUTE_TABLE_A:?}" "${PRIVATE_ROUTE_TABLE_B:?}"
```

| Dependency | Private connectivity when no internet path exists |
| --- | --- |
| Private ECR image pulls | `ecr.api`, `ecr.dkr`, and S3 gateway; copy public images to a reachable private registry |
| EC2 APIs used by nodes/CNI | `ec2`, appropriate permissions and endpoint policy |
| IRSA credentials | Regional `sts`; configure SDKs to use the regional endpoint |
| OIDC discovery/JWKS from inside the VPC | `oidc-eks`, for example when setting up the IAM OIDC provider; separate from STS |
| EKS Pod Identity credentials | `eks-auth` plus a supported Pod Identity Agent/setup |
| EKS management API | `eks`; this does not replace the Kubernetes API private endpoint |
| Logs, autoscaling, load balancing, SSM | Endpoints and permissions for the services actually used; SSM also needs its messaging connectivity |

Endpoint services and DNS names vary by Region/partition. Check each workload's full dependencies, including image registries, package downloads, external APIs and add-on features. An endpoint for one AWS service is not a general-purpose internet substitute.

**Administration:** use routed VPN/Direct Connect connectivity, a controlled host with private access, or an appropriately configured SSM session. A bastion does not inherently need a public IP. SSM still needs its agent, IAM authorization and service connectivity.

A private API with NAT-backed private nodes is also a valid EKS design, but it does not meet this question's no-internet-egress requirement. Likewise, a subnet's public route alone does not prove an individual node is internet-accessible; address assignment and security controls matter.

References: [private-cluster requirements](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [API endpoint access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [EKS PrivateLink and OIDC](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html).

</details>

4. Which is NOT the EKS managed node-group mechanism for applying a new node AMI?
   * A) Replace instances through a managed rolling update
   * B) Create and validate a separate blue/green node group
   * C) Upgrade OS packages on running instances instead of replacing them
   * D) Validate a new AMI in a small canary node group before broader replacement

<details>
<summary>Show Answer</summary>

**Answer: C) Upgrade OS packages on running instances instead of replacing them**

EKS managed node-group updates replace EC2 instances. Updating OS packages on the running instances is not the managed AMI update mechanism. Avoid the ambiguous claim that all “in-place upgrades” are unsupported: AWS also uses that phrase for retaining the node-group resource while changing its launch-template AMI version, which still replaces instances.

**Rolling update:** `DEFAULT` creates replacement capacity before retiring old nodes; `MINIMAL` can terminate selected old nodes before creating replacements. `maxUnavailable` defaults to 1 but is configurable, so it is not always exactly one node at a time. Check quotas, AZ capacity, Pod placement and update strategy. With a custom AMI, explicitly select the new version of the same launch template; the following command instead illustrates the EKS-selected AMI case:

```bash
# EKS-selected AMI case: inspect first, then initiate a reviewed update.
aws eks describe-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'nodegroup.{status:status,version:version,ami:amiType,release:releaseVersion,update:updateConfig}'
if NODE_UPDATE_ID=$(aws eks update-nodegroup-version \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODE_UPDATE_ID" \
    --region "$EXAMPLE_REGION" \
    --query 'update.{status:status,errors:errors}'
fi
```

Record the returned update ID and repeat `describe-update` until a terminal state. A successful API submission is not completion. Investigate reported errors before proceeding. A PDB that prevents eviction can result in `PodEvictionFailure`; do not bypass it with `--force` merely to make the command finish.

**Blue/green:** create a separate compatible AL2023 node group, test workload scheduling and readiness, then migrate gradually. Retain old capacity until application checks, volume/AZ constraints and rollback requirements are satisfied. Merely listing node labels is not validation, and traffic follows Service endpoints/Pods rather than node-group names. Do not automatically delete the old group immediately after creating the new one.

**Canary:** use a small, separately labeled and tainted group. The taint discourages unrelated Pods from landing there; only the test workload selects and tolerates it. System DaemonSets can still run when their tolerations allow it. This is an illustrative configuration for an existing test cluster:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: canary-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 1
    minSize: 1
    maxSize: 2
    privateNetworking: true
    labels:
      example.com/upgrade-track: canary
    taints:
      - key: example.com/upgrade-track
        value: canary
        effect: NoSchedule
```

Create an unused `upgrade-lab` namespace in your dedicated test context before applying this complete demonstration Deployment. A real canary must also exercise the application's own dependencies and representative traffic; this NGINX Pod only checks basic scheduling and readiness.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: upgrade-canary
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      nodeSelector:
        example.com/upgrade-track: canary
      tolerations:
        - key: example.com/upgrade-track
          operator: Equal
          value: canary
          effect: NoSchedule
      containers:
        - name: nginx
          image: nginx:1.30.4
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
```

**Disruption budgets and capacity:** this separate example assumes a real `my-app` workload in `app-namespace`, normally with at least three ready replicas. It is not the PDB for the single-replica canary above:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: app-namespace
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

A PDB limits voluntary evictions handled through the eviction API; it does not guarantee availability, prevent hardware failures, or stop direct Pod/Deployment deletion. `minAvailable: 2` blocks eviction when only two matching Pods are healthy. Verify spare capacity, topology, probes, termination behavior and recovery from failures. Blue/green or canary plans do not by themselves prove safe rollback, especially for stateful data.

References: [managed update behavior](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html), [AL2023 migration](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [Pod disruption budgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/).

</details>

5. Which action is not part of bootstrapping an EKS-optimized AL2023 EC2 worker?
   * A) Configure kubelet/container runtime
   * B) Install AWS-managed control plane components on the worker
   * C) Configure node client authentication/connectivity
   * D) Register the node

<details>
<summary>Show Answer</summary>

**Answer: B) Install AWS-managed control plane components on the worker**

Workers do not install the API server, etcd, controller manager or scheduler; these belong to the AWS-managed control plane. **CoreDNS in conventional EKS is a data-plane cluster add-on, not one of those control plane components.**

EKS-optimized AL2023 AMIs use `nodeadm` to configure containerd and kubelet. `nodeadm-config` establishes baseline configuration before user data, and `nodeadm-run` completes configuration and starts daemons afterward. The AMI runs this automatically; do not invoke `nodeadm init` again from user data. The AL2 `/etc/eks/bootstrap.sh` flow is not the current AL2023 bootstrap path.

**Separate node joining from cluster networking**

1. Provision the node IAM role/instance profile and required node access authorization before launch. Bootstrap does not create IAM roles. Use the AMI-generated kubeconfig/authentication path instead of a manual kubeconfig that unnecessarily assumes the instance's own role again.
2. Kubelet registers the node. Readiness depends on runtime/CNI health as well as cluster connectivity.
3. Conventional EKS deploys/manages `aws-node`, `kube-proxy` and CoreDNS as cluster add-ons. Host bootstrap does not install all of these add-ons; do not overwrite CNI configuration with an invented file.
4. Do not manually falsify provider-owned `eks.amazonaws.com/nodegroup` or `topology.kubernetes.io/zone` labels. Manage custom labels/taints through node group/provisioner configuration.

**NodeConfig input example**

The following runs on the administration workstation to generate user data from an existing IPv4 cluster's actual metadata. It is for reviewed EKS-optimized AL2023-based custom AMIs/self-managed nodes; managed node groups without a custom AMI ID use EKS metadata generation/merging. `NodeConfig` is host bootstrap configuration, not a normal Kubernetes resource to submit with `kubectl apply`.

```bash
# Run on the administration workstation to prepare reviewed IPv4 node user data.
NODE_CONFIG_DIR=$(mktemp -d /tmp/eks-nodeconfig.XXXXXX)
: "${NODE_CONFIG_DIR:?}"
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster --output json > "$NODE_CONFIG_DIR/cluster.json" || exit 1

jq -e '
  (.name | type == "string" and length > 0) and
  (.endpoint | startswith("https://")) and
  (.certificateAuthority.data | type == "string" and length > 0) and
  (.kubernetesNetworkConfig.ipFamily == "ipv4") and
  (.kubernetesNetworkConfig.serviceIpv4Cidr | type == "string" and length > 0)
' "$NODE_CONFIG_DIR/cluster.json" >/dev/null || exit 1

jq '{
  apiVersion: "node.eks.aws/v1alpha1",
  kind: "NodeConfig",
  spec: {
    cluster: {
      name: .name,
      apiServerEndpoint: .endpoint,
      certificateAuthority: .certificateAuthority.data,
      cidr: .kubernetesNetworkConfig.serviceIpv4Cidr
    }
  }
}' "$NODE_CONFIG_DIR/cluster.json" > "$NODE_CONFIG_DIR/nodeconfig.json" || exit 1

{
  printf 'MIME-Version: 1.0\n'
  printf 'Content-Type: multipart/mixed; boundary="EKS_NODE_CONFIG"\n\n'
  printf '%s\n' '--EKS_NODE_CONFIG' 'Content-Type: application/node.eks.aws' ''
  cat "$NODE_CONFIG_DIR/nodeconfig.json"
  printf '\n%s\n' '--EKS_NODE_CONFIG--'
} > "$NODE_CONFIG_DIR/user-data.mime"
printf 'Review user data: %s\n' "$NODE_CONFIG_DIR/user-data.mime"
# An EC2 LaunchTemplateData.UserData JSON field needs the MIME file base64 encoded.
# The console user-data editor can accept raw text when its encoding option is set accordingly.
```

Do not hardcode one DNS service IP or maxPods value for every node. Follow the cluster service CIDR, instance/CNI/prefix settings and documented sizing rules. These inspection commands describe conventional EC2 configurations; managed components differ on Auto Mode/Fargate.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -L eks.amazonaws.com/nodegroup,topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" describe node "${EXAMPLE_NODE:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get daemonset aws-node kube-proxy
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get deployment coredns
```

Node joining, daemon execution, network behavior and runtime logs were not executed/collected during this audit.

[AL2023/nodeadm lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [NodeConfig API](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/)

</details>

## Official References

- [EKS supported versions](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [VPC CNI IAM role](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [NetworkPolicy prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Metrics Server requirements](https://github.com/kubernetes-sigs/metrics-server#requirements)
- [eksctl configuration schema](https://schema.eksctl.io/)
