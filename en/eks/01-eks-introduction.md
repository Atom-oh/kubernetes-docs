# Introduction to EKS

> **Supported Versions**: Amazon EKS standard support 1.34–1.36; extended support 1.31–1.33
> **Last Updated**: September 11, 2026

Amazon Elastic Kubernetes Service (EKS) is a managed service for running Kubernetes on AWS. In this chapter, we will explore the basic concepts of EKS, its architecture, and the differences from standard Kubernetes.

## EKS and Kubernetes

EKS is a managed service that provides standard Kubernetes APIs. For detailed information about the basic concepts and operation of Kubernetes, refer to the [Introduction to Kubernetes](../basics/04-kubernetes-introduction.md) document.

### Key Benefits of EKS

1. **Managed Control Plane**: AWS manages the availability and scalability of the Kubernetes control plane
2. **Enhanced Security**: Authentication and authorization through integration with AWS IAM
3. **AWS Service Integration**: Seamless integration with other AWS services (ELB, ECR, IAM, etc.)
4. **Various Compute Options**: EC2-based nodes, EKS Auto Mode, Fargate and Hybrid Nodes. Bottlerocket is a node operating system, not a separate compute service
5. **Auto Scaling**: Auto scaling support through Cluster Autoscaler, Karpenter, etc.
6. **Managed Node Groups**: Automated node lifecycle management

## EKS Architecture and Components

The overall architecture of Amazon EKS is as follows:

### Control Plane

EKS provides a highly available control plane. The control plane runs across multiple availability zones and consists of the following components:

* **API Server**: Exposes the Kubernetes API and handles interaction with the cluster.
* **etcd**: A distributed key-value store that stores the cluster state.
* **Controller Manager**: Runs controllers that manage the cluster state.
* **Scheduler**: Assigns pods to nodes.

In EKS, these control plane components are managed by AWS, so users don't need to manage them directly.

### Data Plane

The EKS data plane can be configured with the following options:

1. **Managed Node Groups**: EC2 node groups whose provisioning and replacement workflow AWS manages. Operators select and initiate node version/AMI updates; a control plane upgrade does not automatically update these nodes.
2. **Self-Managed Nodes**: EC2 instances managed directly by the user.
3. **AWS Fargate**: Per-Pod compute selected through Fargate profiles. Operators still manage workload configuration and resource requests.
4. **EKS Auto Mode**: AWS manages EC2 node provisioning, scaling and updates plus supported networking, load balancing and block storage capabilities.
5. **Hybrid Nodes**: Customer-managed on-premises/edge machines connect to an AWS-hosted EKS control plane; reliable connectivity is required.

### Networking

On conventional EC2-based EKS nodes, Amazon VPC CNI is the default and allocates VPC addresses to ordinary Pods. `hostNetwork` Pods share node networking. Auto Mode manages its own networking capability, while Hybrid Nodes use a compatible on-premises CNI rather than Amazon VPC CNI.

## Differences Between Standard Kubernetes and EKS

### Management Responsibility

* **Self-managed Kubernetes**: Operators manage the control plane and data plane; other managed distributions may divide responsibility differently.
* **EKS**: AWS manages the control plane. Data plane responsibility depends on the compute option. Workload security, identity, configuration, availability and data protection remain customer responsibilities.

### Networking

* **Standard Kubernetes**: You can choose from various CNI plugins.
* **EKS**: Conventional EC2-based clusters default to Amazon VPC CNI. Alternative CNIs and Auto Mode/Hybrid Nodes have different feature and support constraints.

### Load Balancing

* **Standard Kubernetes**: A separate controller must be installed to use `LoadBalancer` type services.
* **EKS**: On a conventional cluster, install and authorize AWS Load Balancer Controller for NLB Services and ALB Ingresses; the legacy controller can create Classic Load Balancers. Auto Mode provides managed NLB/ALB integration with its own classes and supported configuration. A Service type alone does not identify the controller. Fargate supports ALB/NLB IP targets.

### Storage

* **Standard Kubernetes**: Various storage drivers must be installed and configured manually.
* **EKS**: On a conventional cluster, install the EBS CSI driver/add-on and grant its IAM permissions. Auto Mode has managed EBS support with provisioner `ebs.csi.eks.amazonaws.com`, distinct from `ebs.csi.aws.com`. EFS and FSx integrations have separate prerequisites; EBS volumes cannot be mounted by Fargate or Hybrid Nodes.

## EKS Cost Structure

The costs incurred when operating an EKS cluster are as follows:

1. **EKS Control Plane Cost**: An hourly fee is charged per cluster, with different standard/extended-support pricing and additional charges for optional provisioned control plane tiers.
2. **Compute Costs**:
   * EC2 instances (managed or self-managed nodes)
   * Fargate (charged based on pod runtime and resource usage)
3. **Storage Costs**: Costs for storage services such as EBS, EFS, FSx
4. **Network Costs**: Data transfer, NAT gateways, public IPv4 addresses and load balancer usage costs
5. **Managed Capability Costs**: Auto Mode, EKS Capabilities and Hybrid Nodes have their own charges in addition to the relevant cluster/infrastructure costs.

### Cost Optimization Strategies

1. **Use Spot Instances**: Compare current Spot prices and interruption tolerance; advertised savings are not a workload-level guarantee.
2. **Evaluate Fargate**: Compare provisioned Pod sizes, running time, feature limits and operational effort with EC2. Low application utilization alone does not guarantee savings.
3. **Configure Auto Scaling**: Automatically scale nodes up and down as needed.
4. **Locality Routing**: Where supported, prefer same-zone traffic while retaining adequate capacity and failover. Routing and load balancer settings determine any transfer savings.
5. **EKS Auto Mode**: Evaluate automatic scaling and consolidation savings together with the Auto Mode management charge.
6. **Hybrid Nodes**: Evaluate existing on-premises capacity together with per-vCPU Hybrid Nodes charges and connectivity/operations costs. This feature is not a synonym for mixing EC2 instance types.

## Integration with AWS Services

EKS integrates with the following AWS services:

![Diagram of AWS service integration around Amazon EKS: IAM, VPC, storage, CloudWatch, ECR, and SageMaker/Bedrock.](../.gitbook/assets/en-eks-01-eks-introduction-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-01-eks-introduction-0.html)

1. **IAM**: IAM identities authenticate to the cluster; EKS access entries authorize through access policies and/or Kubernetes RBAC groups. Pod Identity and IRSA separately grant workloads AWS permissions.
2. **VPC**: Provides networking infrastructure.
3. **CloudWatch**: Provides monitoring and logging.
4. **ALB/NLB**: Provides load balancing.
5. **ECR**: Provides container image registry.
6. **EBS/EFS/FSx**: Provides persistent storage.
7. **AWS App Mesh**: Existing integrations need migration planning: AWS ends support on September 30, 2026. Do not select it for a new deployment.
8. **AWS Certificate Manager**: Manages SSL/TLS certificates.
9. **AWS Secrets Manager**: Securely stores and manages sensitive information.
10. **AWS SageMaker**: Runs machine learning workloads.
11. **AWS Bedrock**: Leverages generative AI models.

## EKS Best Practices

1. **Cluster Design**:
   * Deploy nodes across multiple availability zones
   * Select appropriate instance types
   * Establish node group strategy
2. **Security**:
   * Apply the principle of least privilege
   * Implement network policies
   * Apply Pod Security Standards using Pod Security Admission and/or admission policies; the PodSecurityPolicy API was removed in Kubernetes 1.25
   * Image scanning and vulnerability management
3. **Networking**:
   * Proper subnet design
   * Security group configuration
   * Leverage Locality Routing
4. **Monitoring and Logging**:
   * Enable CloudWatch Container Insights
   * Configure control plane logging
   * Leverage Prometheus and Grafana
5. **Upgrade Strategy**:
   * Plan regular upgrades
   * Consider blue/green deployment strategy
   * Perform testing before upgrades

## Official references

- [EKS version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Compute and shared responsibilities](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [AWS Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [EBS CSI and Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
- [Fargate considerations](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [App Mesh support notice](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)
- [EKS pricing](https://aws.amazon.com/eks/pricing/)
- [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)

## Quiz

To test what you learned in this chapter, try the [Amazon EKS Introduction Quiz](../quizzes/eks/01-eks-introduction-quiz.md).
