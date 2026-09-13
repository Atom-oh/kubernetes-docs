# Introduction to EKS Quiz

> **Last Updated**: September 11, 2026

This quiz tests your understanding of the basic concepts and features of Amazon Elastic Kubernetes Service (EKS). It covers topics such as EKS architecture, components, management methods, and pricing models.

For standalone API examples, set `EXAMPLE_CLUSTER`, `EXAMPLE_REGION`, `EXAMPLE_CONTEXT` and other marked variables to the reviewed target. The IRSA example requires an existing `EXAMPLE_NAMESPACE`, an `APP_POLICY_ARN` scoped to the required bucket/prefix, and an application using an IRSA-compatible AWS SDK. The two exercises use separate `EKS_INTRO_*` variables for their dedicated cluster.

## Multiple Choice Questions

1. What is the main benefit of Amazon EKS (Elastic Kubernetes Service)?
   * A) No need to manage your own Kubernetes control plane infrastructure
   * B) Lower cost than other managed Kubernetes services
   * C) Can only use AWS services
   * D) Can only run in a single availability zone

<details>

<summary>Show Answer</summary>

**Answer: A) No need to manage your own Kubernetes control plane infrastructure**

**Explanation:** The main benefit of Amazon EKS (Elastic Kubernetes Service) is that you don't need to manage your own Kubernetes control plane infrastructure. Since AWS manages the availability and scalability of the Kubernetes control plane, users can focus on running their workloads.

Key benefits of EKS:

* **Managed Control Plane**: AWS manages control plane nodes, etcd cluster, API server, etc.
* **High Availability**: The regional control plane spans multiple Availability Zones. Workload availability still depends on replicas, placement, capacity and dependencies.
* **Managed maintenance**: AWS patches the control plane. Operators plan minor-version upgrades; automatic upgrades also occur under the version support policy.
* **Integration with AWS Services**: Seamlessly integrates with various AWS services including IAM, VPC, ELB, ECR, etc.
* **Standard Kubernetes**: Conformant Kubernetes APIs improve portability; AWS-specific identities, storage and integrations still need migration work.

Issues with other options:

* EKS is not necessarily cheaper than other managed Kubernetes services. There is actually an hourly fee for the control plane.
* EKS can run any Kubernetes-compatible applications and services, not just AWS services.
* The regional EKS control plane spans multiple Availability Zones; users must separately distribute worker nodes and application replicas.

</details>

2. Where is the Amazon EKS cluster control plane deployed?
   * A) Within the user's VPC
   * B) Deployed across multiple availability zones in an AWS-managed account
   * C) In a single availability zone chosen by the user
   * D) Running on user's EC2 instances

<details>

<summary>Show Answer</summary>

**Answer: B) Deployed across multiple availability zones in an AWS-managed account**

**Explanation:** The Amazon EKS cluster control plane is deployed across multiple availability zones in an AWS-managed account. This is one of the core aspects of EKS as a managed service.

Key characteristics of EKS control plane deployment:

* **AWS-Managed Infrastructure**: The control plane runs in an AWS-owned and managed account.
* **Multi-AZ Deployment**: Regional EKS control plane components are distributed across multiple Availability Zones.
* **Auto Recovery**: AWS monitors the health of control plane components and automatically replaces failed components.
* **Endpoint Accessibility**: Configure public access, private access, or both. Private access also requires DNS and routing from the VPC or connected networks.
* **Auto Scaling**: Standard control plane capacity adjusts automatically; optional Provisioned Control Plane tiers are explicitly selected.

Issues with other options:

* The control plane is not deployed within the user's VPC. Instead, a connection is established between the user's VPC and the AWS-managed VPC through ENI (Elastic Network Interface).
* The control plane is deployed across multiple availability zones, not a single one, to ensure high availability.
* The control plane runs on AWS-managed infrastructure, not on user's EC2 instances.

</details>

3. Which description of EKS compute management is incorrect?
   * A) Self-managed EC2 nodes
   * B) Managed node groups
   * C) Fargate profiles
   * D) Bottlerocket as a separate serverless compute service

<details>
<summary>Show Answer</summary>

**Answer: D) Bottlerocket as a separate serverless compute service**

Bottlerocket is an operating system for container nodes, not an independent serverless execution option.

1. **Self-managed nodes**: Customers manage EC2/Auto Scaling groups, AMIs, updates and node configuration.
2. **Managed node groups**: AWS manages provisioning and replacement workflows, while operators initiate AMI/version updates. Minimum and maximum sizes alone do not enable demand-based scaling.
3. **Fargate**: Profiles select Pods for isolated compute. Check limitations such as DaemonSets, GPUs and EBS.
4. **EKS Auto Mode**: An actual EKS capability that automates node provisioning, scaling and replacement.
5. **Hybrid Nodes**: Connect on-premises/edge machines to the AWS-managed control plane.

Conventional EC2 nodes can use separately configured Cluster Autoscaler or self-managed Karpenter for demand-based scaling.

</details>

4. What is the default CNI on conventional EC2-based EKS nodes?
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>Show Answer</summary>

**Answer: C) AWS VPC CNI**

**Explanation:** The CNI (Container Network Interface) plugin used by default for pod networking in Amazon EKS clusters is AWS VPC CNI. This plugin directly integrates Amazon VPC networking with Kubernetes pods.

Key features of AWS VPC CNI:

* **VPC-native IP address assignment**: Pods receive IP addresses directly from the VPC, existing in the same network space as other resources in the VPC.
* **Secondary IP address usage**: Assigns secondary IP addresses connected to each node's Elastic Network Interface (ENI) to pods.
* **Security group integration**: Security groups for Pods require supported instances, VPC resource controller permissions, CNI configuration and a SecurityGroupPolicy.
* **VPC flow log visibility**: Pod traffic is visible in VPC flow logs.
* **Leverage AWS networking features**: Features like VPC peering, Transit Gateway, PrivateLink can be directly utilized by pods.

AWS VPC CNI is an open-source project, and you can check the code on GitHub: https://github.com/aws/amazon-vpc-cni-k8s

Alternative CNIs on EC2 nodes require their own compatibility and support review. Fargate and Auto Mode do not support arbitrary CNI replacement; Hybrid Nodes require a compatible on-premises CNI. `hostNetwork` Pods share node networking.

</details>

5. How do you grant an IAM identity access to the EKS Kubernetes API?
   * A) Authenticate every IAM user through a ServiceAccount alone
   * B) IAM authentication with access entries using access policies and/or Kubernetes RBAC
   * C) EKS IAM policies automatically grant every Kubernetes resource permission
   * D) Automatically connect Cognito to every cluster

<details>
<summary>Show Answer</summary>

**Answer: B) IAM authentication with access entries using access policies and/or Kubernetes RBAC**

IAM access to the Kubernetes API and a Pod's access to AWS APIs are separate paths.

1. `aws eks get-token` creates an authentication token signed with IAM credentials.
2. EKS authenticates the IAM identity. Use an **access entry** for new access configuration.
3. Associate an EKS access policy, or specify Kubernetes groups and create RoleBindings/ClusterRoleBindings. RBAC and the EKS authorizer grant additive permissions; if neither allows the request, it is denied.
4. The legacy `aws-auth` ConfigMap is deprecated. Existing mappings are not all migrated automatically, so verify each identity and permission when moving to access entries.

IAM policies control calls to the EKS service API. EKS access policies are Kubernetes permission templates, not IAM policies. IRSA/Pod Identity separately grant workloads AWS permissions. Kubernetes ServiceAccount tokens and a configured OIDC provider can also authenticate to Kubernetes; IAM is not the only authentication mechanism.

</details>

6. Which option uses an OIDC federation relationship to grant a Kubernetes ServiceAccount temporary AWS credentials?
   * A) Granting IAM roles to nodes using EC2 instance profiles
   * B) Embedding long-lived AWS access keys in Pod environment variables
   * C) Linking IAM roles to Kubernetes service accounts (IRSA)
   * D) Storing AWS credentials as Kubernetes Secrets and mounting them

<details>

<summary>Show Answer</summary>

**Answer: C) Linking IAM roles to Kubernetes service accounts (IRSA)**

IRSA exchanges a ServiceAccount token through the cluster OIDC provider for temporary AWS credentials. Restrict the trust policy to the namespace/ServiceAccount and `aud=sts.amazonaws.com`. EKS Pod Identity also provides temporary credentials, without a separate OIDC provider; check its compute, agent and SDK requirements. This example demonstrates the IRSA approach.

Key benefits of IRSA:

* **Principle of least privilege**: You can grant only the minimum permissions needed for each application.
* **Permission isolation**: Different pods running on the same node can have different IAM permissions.
* **Simplified credential management**: No need to directly manage AWS credentials.
* **Enhanced security**: Credentials are not hardcoded in code or configuration.

How to set up IRSA:

1.  Associate an OpenID Connect (OIDC) provider with the EKS cluster:

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" --approve
    ```
2.  Create an IAM role for the service account:

    ```bash
    eksctl create iamserviceaccount \
      --name=app-sa \
      --namespace="${EXAMPLE_NAMESPACE:?}" \
      --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" \
      --attach-policy-arn="${APP_POLICY_ARN:?Use a reviewed policy scoped to the required bucket/prefix}" \
      --approve
    ```
3.  Reference the service account in a Pod in the same namespace. This is a template: replace the image with your application using an IRSA-compatible SDK, then apply it with `-n "$EXAMPLE_NAMESPACE"`:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: app-sa
      containers:
      - name: my-container
        image: registry.example.com/team/app:reviewed
    ```

Issues with other options:

* Pods that can reach IMDS may obtain node-role credentials. Restrict IMDS access and use workload-specific roles; IRSA alone does not block that access.
* Embedding long-lived access keys in Pod environment variables adds exposure and rotation risk. IRSA/Pod Identity credential-provider environment variables are a different mechanism.
* Storing AWS credentials as Kubernetes Secrets adds credential management burden and complicates credential rotation.

</details>

7. Which statement about the logging feature of Amazon EKS clusters is correct?
   * A) All logs are sent to CloudWatch Logs by default
   * B) Control plane logs can optionally be sent to CloudWatch Logs
   * C) Only worker node logs can be sent to CloudWatch Logs
   * D) EKS does not provide logging functionality

<details>

<summary>Show Answer</summary>

**Answer: B) Control plane logs can optionally be sent to CloudWatch Logs**

**Explanation:** In Amazon EKS clusters, control plane logs can optionally be sent to CloudWatch Logs. This feature is disabled by default, and users can choose to enable the log types they need.

Key features of EKS control plane logging:

* **Optional activation**: Can be enabled during cluster creation or on existing clusters.
* **Log type selection**: You can select only the log types you need from:
  * API server (api)
  * Audit (audit)
  * Authenticator (authenticator)
  * Controller manager (controllerManager)
  * Scheduler (scheduler)
* **CloudWatch Logs integration**: Selected logs are sent to AWS CloudWatch Logs for storage, analysis, and monitoring.
* **Cost consideration**: CloudWatch Logs ingestion, retention and query charges can apply.

How to enable logging:

```bash
# Enable logging using AWS CLI
aws eks update-cluster-config \
    --region "${EXAMPLE_REGION:?}" \
    --name "${EXAMPLE_CLUSTER:?}" \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable logging using eksctl
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
```

Worker node logging:

* Worker node logs are not included in the EKS control plane logging feature.
* To send worker node logs to CloudWatch Logs, you need to install the CloudWatch agent or configure a logging solution like Fluentd/Fluent Bit.

Issues with other options:

* Not all logs are sent to CloudWatch Logs by default. Users must explicitly enable them.
* It's not that only worker node logs can be sent to CloudWatch Logs; control plane logs can also be sent.
* EKS does provide control plane logging functionality.

</details>

8. Which is NOT a cost component of an Amazon EKS cluster?
   * A) EKS control plane hourly fee
   * B) EC2 instance costs for worker nodes
   * C) Fargate pod execution costs
   * D) Kubernetes license fees

<details>

<summary>Show Answer</summary>

**Answer: D) Kubernetes license fees**

**Explanation:** Kubernetes license fees are not a cost component of Amazon EKS clusters. Kubernetes is open-source software managed by the Cloud Native Computing Foundation (CNCF) and is free to use under the Apache 2.0 license. Therefore, there are no separate Kubernetes license fees when using EKS.

Actual cost components of Amazon EKS clusters include:

1. **EKS control plane hourly fee**:
   * Standard and extended support have different cluster rates, with additional charges for optional Provisioned Control Plane tiers.
   * An EKS cluster is a regional resource; a multi-region deployment needs separate clusters and charges.
   * Account separately for Auto Mode, EKS Capabilities, Hybrid Nodes and AWS infrastructure charges.
2. **EC2 instance costs for worker nodes**:
   * Costs are incurred for EC2 instances used in self-managed or managed node groups.
   * Costs vary based on instance type, size, quantity, and runtime.
   * Costs can be optimized through Reserved Instances, Savings Plans, and Spot Instances.
3. **Fargate pod execution costs**:
   * When using Fargate, costs are charged based on vCPU and memory resources allocated to pods.
   * Linux Fargate billing starts at image download, is rounded to seconds and has a one-minute minimum; requested resources are rounded to supported configurations.
   * Compare total provisioned capacity, utilization and operational effort; neither Fargate nor EC2 is universally cheaper.
4. **Additional AWS resource costs**:
   * EBS volumes
   * Load balancers (NLB, ALB)
   * CloudWatch logs and metrics
   * NAT Gateway
   * Data transfer

Cost optimization strategies:

* Selecting appropriate instance types
* Configuring auto-scaling
* Using Spot Instances
* Cluster automation and scheduled scaling
* Optimizing resource requests and limits
* Cost monitoring and analysis

</details>

9. Which option provides declarative ALB/NLB integration on a conventional EKS cluster without Auto Mode?
   * A) Using the built-in EKS load balancer
   * B) Integrating Kubernetes Service resources with AWS Load Balancer Controller
   * C) Manually creating and configuring EC2 load balancers
   * D) EKS does not support load balancing

<details>

<summary>Show Answer</summary>

**Answer: B) Integrating Kubernetes Service resources with AWS Load Balancer Controller**

**Explanation:** The correct method for implementing load balancing in an Amazon EKS cluster is integrating Kubernetes Service resources with AWS Load Balancer Controller. This approach combines Kubernetes's declarative resource management with AWS's load balancing capabilities.

Methods for implementing load balancing in EKS:

1.  **Default LoadBalancer type Service**:

    * The selected controller determines the load balancer. This example explicitly selects an installed, authorized AWS LBC with `service.k8s.aws/nlb`; the legacy integration can create a CLB.

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
2.  **AWS Load Balancer Controller**:

    * Install AWS Load Balancer Controller for more advanced features to manage Application Load Balancer (ALB) and Network Load Balancer (NLB).
    * ALB can be provisioned and configured through Ingress resources.
    * Various load balancer attributes can be configured through annotations.

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/target-type: ip
    spec:
      ingressClassName: alb
      rules:
      - http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80
    ```
3.  **Service annotations**:

    * Annotations can be added to services to specify load balancer type and configuration.

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
        service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
      selector:
        app: my-app
      ports:
      - port: 80
        targetPort: 8080
    ```

Issues with other options:

* Auto Mode provides managed load balancing with different classes, including `eks.amazonaws.com/nlb`. It does not require installing the in-cluster AWS LBC; do not mix their classes or unsupported annotations.
* While it's possible to manually create and configure EC2 load balancers, it doesn't align with Kubernetes's declarative approach and complicates management.
* EKS fully supports load balancing.

</details>

10. Which is NOT a valid method for managing storage in an Amazon EKS cluster?
    * A) Provisioning EBS volumes using the EBS CSI driver
    * B) Mounting EFS file systems using the EFS CSI driver
    * C) Mounting an EBS volume in a Fargate Pod
    * D) Connecting high-performance file systems using the FSx for Lustre CSI driver

<details>

<summary>Show Answer</summary>

**Answer: C) Mounting an EBS volume in a Fargate Pod**

Fargate cannot mount EBS volumes. Conventional EC2 nodes use an installed EBS CSI driver with IAM permissions. Auto Mode provides managed EBS provisioning through `ebs.csi.eks.amazonaws.com`, distinct from the conventional `ebs.csi.aws.com` driver.

The actual methods for managing storage in Amazon EKS clusters include:

1.  **EBS CSI driver**:

    * Allows connecting Amazon EBS (Elastic Block Store) volumes to Kubernetes pods.
    * Suitable for applications requiring block storage (databases, etc.).
    * Supports dynamic provisioning, snapshots with a snapshot controller, and expansion when the StorageClass permits it.
    * EBS is AZ-scoped. ReadWriteOnce means read-write mounting from one node, not one Pod; multiple Pods on that node may use the volume. Access mode does not define its AZ.

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    parameters:
      type: gp3
      encrypted: "true"
    ```
2.  **EFS CSI driver**:

    * Allows mounting Amazon EFS (Elastic File System) to Kubernetes pods.
    * Suitable for shared file systems that need to be accessed by multiple pods simultaneously.
    * Accessible across multiple availability zones (ReadWriteMany access mode).
    * Suitable for web servers, CMS, CI/CD pipelines, etc.

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: efs-sc
    provisioner: efs.csi.aws.com
    parameters:
      provisioningMode: efs-ap
      fileSystemId: fs-0123456789abcdef0
      directoryPerms: "700"
    ```
3.  **FSx for Lustre CSI driver**:

    * Allows connecting Amazon FSx for Lustre to Kubernetes pods.
    * Suitable for high-performance workloads such as high-performance computing, machine learning, and big data analytics.
    * Provides high throughput and low latency.

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: fsx-sc
    provisioner: fsx.csi.aws.com
    parameters:
      subnetId: subnet-0123456789abcdef0
      securityGroupIds: sg-0123456789abcdef0
      deploymentType: PERSISTENT_1
      automaticBackupRetentionDays: "1"
      dailyAutomaticBackupStartTime: "00:00"
      perUnitStorageThroughput: "200"
    ```
   Specify capacity in the PVC at `spec.resources.requests.storage` (for example, `1200Gi`), not a `storageCapacity` StorageClass parameter. Check deployment-specific capacity increments, subnet/security groups, Lustre client compatibility and driver IAM permissions.

4. **Other storage options**:
   * Amazon S3 (Simple Storage Service) through CSI drivers or S3 mounters
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * Third-party storage solutions (Portworx, Rook, etc.)

Storage management best practices:

* Select appropriate storage types for workload requirements
* Configure StorageClass for dynamic provisioning
* Establish backup and recovery strategies
* Monitor storage performance
* Select appropriate storage classes and sizes for cost optimization

</details>

## Hands-on Exercises

### Exercise 1: Creating and Configuring an EKS Cluster

**Scenario:** You are a DevOps engineer at your company, and you need to set up an Amazon EKS cluster for your development team. The cluster is for the development environment and should be cost-effective while providing all necessary features.

**Requirements:**

1. Create a cost-effective EKS cluster
2. Configure appropriate node groups
3. Set up basic monitoring
4. Configure kubectl access to the cluster

**Solution:**

<details>
<summary>Show Solution</summary>

Running these deployment commands creates billable AWS resources. They were not executed during the audit. Prepare Bash, a current AWS CLI v2, kubectl 1.36 and Helm, and use the [official eksctl installation procedure](https://eksctl.io/installation/) to check OS/CPU architecture and checksums. The example was reviewed against the eksctl 0.230.0 schema and EKS 1.36; it is not a validated production configuration.

Run the steps in one shell and stop on command failure. Set `EKS_INTRO_ADMIN_CIDR` to the approved client's actual external IPv4 CIDR, normally `/32`. The new cluster uses private nodes/private API access plus restricted public API access. A single NAT gateway is a development-lab choice, not a production availability design. Cluster-creator administrator access is for bootstrapping this dedicated lab only.

**1. Create a dedicated cluster**

```bash
# Use a dedicated nonproduction AWS account/role and an approved region.
eksctl version  # Example tool baseline: 0.230.0
aws --version
kubectl version --client
helm version

EKS_INTRO_DIR=$(mktemp -d /tmp/eks-intro.XXXXXX)
: "${EKS_INTRO_DIR:?}"
EKS_INTRO_CLUSTER=$(basename "$EKS_INTRO_DIR" | tr '[:upper:].' '[:lower:]-')
EKS_INTRO_REGION=us-west-2
: "${EKS_INTRO_ADMIN_CIDR:?Set your approved client egress IPv4 CIDR, normally /32}"
EKS_INTRO_KUBECONFIG="$EKS_INTRO_DIR/kubeconfig"
unset EKS_INTRO_CLUSTER_ARN EKS_INTRO_POLICY_ARN
aws sts get-caller-identity

cat > "$EKS_INTRO_DIR/eks-cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_INTRO_CLUSTER}
  region: ${EKS_INTRO_REGION}
  version: "1.36"
  tags:
    docs-lab: ${EKS_INTRO_CLUSTER}
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: true
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${EKS_INTRO_ADMIN_CIDR}"]
  nat:
    gateway: Single
managedNodeGroups:
- name: ng-1
  amiFamily: AmazonLinux2023
  instanceType: t3.medium
  privateNetworking: true
  disableIMDSv1: true
  disablePodIMDS: true
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

# Inspect the file, account, allowed CIDR and projected costs before provisioning.
cat "$EKS_INTRO_DIR/eks-cluster.yaml"
eksctl create cluster -f "$EKS_INTRO_DIR/eks-cluster.yaml" \
  --kubeconfig "$EKS_INTRO_KUBECONFIG" &&
  EKS_INTRO_CLUSTER_ARN=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
    --region "$EKS_INTRO_REGION" --query cluster.arn --output text)
: "${EKS_INTRO_CLUSTER_ARN:?Cluster creation/verification did not complete}"
```

If creation fails, inspect and clean up the CloudFormation stacks/resources for this unique name before reusing it. `minSize`/`maxSize` only set bounds; they do not install a demand-based node autoscaler. t3.medium is an example, requiring capacity, CPU-credit and regional-price review.

**2. Dedicated kubeconfig and connection checks**

```bash
aws eks update-kubeconfig --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --kubeconfig "${EKS_INTRO_KUBECONFIG:?}"
intro_kubectl() {
  kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" "$@"
}
intro_kubectl get nodes
intro_kubectl cluster-info
```

**3. Basic resource metrics**

Metrics Server 0.9.x supports Kubernetes 1.34+. This supplies resource metrics, not logging or long-term monitoring. Verify kubelet certificates and network reachability without disabling TLS verification.

```bash
intro_kubectl get pods -n kube-system

# Fresh lab cluster only: do not overwrite an existing managed installation.
curl -fL https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml \
  -o "${EKS_INTRO_DIR:?}/metrics-server.yaml" &&
  intro_kubectl apply -f "$EKS_INTRO_DIR/metrics-server.yaml"
intro_kubectl rollout status deployment/metrics-server -n kube-system --timeout=180s
intro_kubectl top nodes
```

**4. Install AWS Load Balancer Controller**

The policy, controller and chart are pinned to 3.5.0. Use its IRSA role instead of granting unrelated add-on permissions to every node. Explicit region/VPC settings avoid reliance on IMDS discovery. Verify subnet tags, security groups and service quotas separately.

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use the new lab cluster}"
curl -fL https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.5.0/docs/install/iam_policy.json \
  -o "${EKS_INTRO_DIR:?}/lbc-policy.json" || exit 1
# Inspect the pinned policy before creating this lab-owned IAM policy.
EKS_INTRO_POLICY_ARN=$(aws iam create-policy \
  --policy-name "${EKS_INTRO_CLUSTER:?}-lbc" \
  --policy-document "file://$EKS_INTRO_DIR/lbc-policy.json" \
  --query Policy.Arn --output text)
: "${EKS_INTRO_POLICY_ARN:?Policy creation failed}"

# iam.withOIDC created the cluster OIDC provider in step1.
eksctl create iamserviceaccount \
  --cluster="$EKS_INTRO_CLUSTER" --region="${EKS_INTRO_REGION:?}" \
  --namespace=kube-system --name=aws-load-balancer-controller \
  --attach-policy-arn="$EKS_INTRO_POLICY_ARN" --approve

EKS_INTRO_VPC_ID=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query cluster.resourcesVpcConfig.vpcId --output text)
: "${EKS_INTRO_VPC_ID:?}"
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" install aws-load-balancer-controller \
  eks/aws-load-balancer-controller --version 3.5.0 -n kube-system \
  --set clusterName="$EKS_INTRO_CLUSTER" \
  --set region="$EKS_INTRO_REGION" --set vpcId="$EKS_INTRO_VPC_ID" \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --wait --timeout 5m
```

**5. Check cluster state**

```bash
intro_kubectl get nodes -o wide
intro_kubectl get pods -n kube-system
intro_kubectl get events --sort-by='.lastTimestamp'
intro_kubectl cluster-info
```

**6. Check a basic app through local port forwarding**

```bash
intro_kubectl create namespace intro-smoke
intro_kubectl -n intro-smoke create deployment nginx --image=nginx:1.30.4-alpine
intro_kubectl -n intro-smoke rollout status deployment/nginx --timeout=180s
intro_kubectl -n intro-smoke expose deployment nginx --port=80 --type=ClusterIP
intro_kubectl -n intro-smoke get deployment,service
# Run in a separate terminal using the same dedicated kubeconfig.
kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" -n intro-smoke \
  port-forward --address 127.0.0.1 service/nginx 8080:80
```

While port forwarding runs, open `http://127.0.0.1:8080`; stop forwarding with Ctrl-C. The next exercise configures external ALB access. Use the cleanup procedure after both exercises; expected behavior and potential savings are not measured audit results.

</details>

### Exercise 2: Deploying Applications and Exposing Services in an EKS Cluster

**Scenario:** Your team has developed a web application based on microservices architecture. You need to deploy this application to the EKS cluster and configure it to be accessible from outside.

**Requirements:**

1. Deploy frontend and backend services
2. Configure inter-service communication
3. Configure external access through ingress controller
4. Set up basic scaling

**Solution:**

<details>
<summary>Show Solution</summary>

Use the dedicated cluster and shell variables from exercise1, AWS LBC/IngressClass `alb`, and a healthy Metrics Server. This HTTP demo serves only public dummy responses and restricts ALB access to the selected client CIDR. It does not implement application authentication, TLS or production load validation.

**1. Create the namespace**

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Complete exercise1 first}"
unset EKS_INTRO_WEB_UID
EKS_INTRO_WEB_UID=$(intro_kubectl create namespace web-app -o jsonpath='{.metadata.uid}')
: "${EKS_INTRO_WEB_UID:?Stop if this namespace already exists}"
```

**2. Configure the backend**

Configure NGINX to listen on port80 and return dummy JSON for paths including `/api`.

```bash
cat > "${EKS_INTRO_DIR:?}/backend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location / {
            default_type application/json;
            return 200 '{"service":"backend","example":true}\n';
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      containers:
      - name: backend
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
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: backend-config
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: web-app
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/backend-deployment.yaml"
```

**3. Configure the frontend and service communication**

The standard NGINX image does not consume `BACKEND_URL`. This explicit NGINX configuration proxies `/proxy-api/` to `backend-service`, providing an actual service-to-service path.

```bash
cat > "${EKS_INTRO_DIR:?}/frontend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location /proxy-api/ {
            proxy_pass http://backend-service/;
        }
        location / {
            default_type text/plain;
            return 200 'frontend demo\n';
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      automountServiceAccountToken: false
      containers:
      - name: frontend
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
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: frontend-config
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: web-app
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/frontend-deployment.yaml"
```

**4. Create an AWS LBC Ingress**

The ALB does not strip `/api` automatically; this backend handles the path directly. `/` and `/proxy-api/` go to the frontend.

```bash
cat > "${EKS_INTRO_DIR:?}/ingress.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
    alb.ingress.kubernetes.io/inbound-cidrs: ${EKS_INTRO_ADMIN_CIDR:?}
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/ingress.yaml"
```

**5. Configure HPA**

CPU utilization is measured relative to requests. HPA changes Pod replicas, not node count, and requires Metrics Server plus spare node capacity.

```bash
cat > "${EKS_INTRO_DIR:?}/hpa.yaml" << 'EOF'
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/hpa.yaml"
```

**6. Check routing and state**

An ALB hostname does not prove its targets are healthy. If requests fail, inspect events, target health, security groups and the client CIDR.

```bash
intro_kubectl -n web-app rollout status deployment/backend --timeout=180s
intro_kubectl -n web-app rollout status deployment/frontend --timeout=180s
intro_kubectl -n web-app get deployments,services,ingress,hpa
intro_kubectl -n web-app describe ingress web-app-ingress
ALB_ADDRESS=$(intro_kubectl -n web-app get ingress web-app-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
: "${ALB_ADDRESS:?Wait for ALB provisioning and inspect events}"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/api"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/proxy-api/"
```

**7. Observe bounded load**

This sample load does not guarantee exceeding the CPU target or triggering HPA. Static NGINX responses may use little CPU, and requests to the frontend root do not load the backend. Observe metrics, HPA status and Pending Pods to determine actual scaling.

```bash
# Only target the lab ALB whose ownership and health you checked above.
: "${ALB_ADDRESS:?}"
ab -n 1000 -c 10 -s 10 "http://$ALB_ADDRESS/"
intro_kubectl -n web-app get hpa
intro_kubectl -n web-app top pods
intro_kubectl -n web-app get events --sort-by='.lastTimestamp'
# Optional observation; Ctrl-C stops watching, not the HPA.
intro_kubectl -n web-app get hpa -w
```

</details>

### Clean up the exercise resources

Confirm the account, ARN and tag identify the dedicated lab cluster. Delete application load balancers before the controller and wait for finalization. Investigate controller errors on timeout instead of removing finalizers.

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use only the dedicated cluster created in exercise1}"
EKS_INTRO_CLEANUP_READY=false
current_arn=$(aws eks describe-cluster --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --query cluster.arn --output text)
current_tag=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query 'cluster.tags."docs-lab"' --output text)
if [[ "$current_arn" = "$EKS_INTRO_CLUSTER_ARN" && "$current_tag" = "$EKS_INTRO_CLUSTER" ]]; then
  # Keep the controller running until it removes ALB resources/finalizers.
  intro_kubectl -n web-app delete ingress web-app-ingress --ignore-not-found --wait=true --timeout=180s &&
    intro_kubectl delete namespace web-app intro-smoke --ignore-not-found --wait=true --timeout=180s &&
    EKS_INTRO_CLEANUP_READY=true
else
  printf 'Ownership check failed; stop cleanup and inspect the selected account/cluster\n' >&2
fi
```

Proceed only after ownership verification and successful Ingress/namespace deletion. Confirm the IAM-role stack deletion and policy detachment before deleting the policy.

```bash
if [[ ${EKS_INTRO_CLEANUP_READY:-false} = true ]]; then
  helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" uninstall aws-load-balancer-controller -n kube-system
  eksctl delete iamserviceaccount --cluster="${EKS_INTRO_CLUSTER:?}" \
    --region="${EKS_INTRO_REGION:?}" --namespace=kube-system --name=aws-load-balancer-controller --approve --wait
  # Wait for the related IAM-role stack deletion to finish before deleting its policy.
  aws iam list-entities-for-policy --policy-arn "${EKS_INTRO_POLICY_ARN:?}"
  # Continue only when no attachment remains.
  aws iam delete-policy --policy-arn "$EKS_INTRO_POLICY_ARN" &&
    eksctl delete cluster --config-file="${EKS_INTRO_DIR:?}/eks-cluster.yaml" --wait
else
  printf 'Complete ownership and load balancer cleanup checks first\n' >&2
fi
```

Verify CloudFormation deletion and any remaining load balancers, security groups, NAT, EBS and log-retention costs. Make a separate retention/deletion decision for the CloudWatch log group. Do not assume partial creation or resources outside these steps were automatically cleaned up. Remove the dedicated directory’s manifests, policy and kubeconfig after the lab.

## Advanced Topics

The following are questions about advanced Amazon EKS topics. This section tests your understanding of advanced EKS features and integrations.

1. What is the correct description when configuring a Fargate profile in Amazon EKS?
   * A) Fargate profiles specify that pods should run on Fargate based on specific namespaces and labels
   * B) Fargate profiles automatically run all pods on Fargate
   * C) Fargate profiles restrict pod execution to specific EC2 instance types
   * D) Fargate profiles set resource quotas for the entire cluster

<details>

<summary>Show Answer</summary>

**Answer: A) Fargate profiles specify that pods should run on Fargate based on specific namespaces and labels**

**Explanation:** An Amazon EKS Fargate profile is a configuration that specifies which pods should run on Fargate based on specific namespaces and labels. This allows configuring a hybrid architecture using both serverless container execution environments and EC2-based nodes.

Key features of Fargate profiles:

* **Selective execution**: Only pods matching the conditions defined in the profile run on Fargate, not all pods.
* **Namespace and label selectors**: Pods are selected based on specific namespace and label combinations.
* **Subnet specification**: You can specify private subnets where pods will run.
* **IAM role**: The Pod execution role is used by Fargate infrastructure, such as for image pulls. Application containers need their own IRSA role for AWS API access.

Fargate profile creation example:

```bash
eksctl create fargateprofile \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

YAML-based Fargate profile definition:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: my-fargate-profile
    selectors:
      - namespace: my-namespace
        labels:
          app: my-app
      - namespace: another-namespace
```

Considerations when using Fargate:

* DaemonSets are not supported on Fargate.
* Privileged containers cannot run.
* HostNetwork and HostPort are not supported.
* GPU workloads are not supported.
* Per-pod costs apply, so cost planning is necessary.
* Persistent storage is available through statically provisioned EFS volumes. EBS volumes and EFS dynamic provisioning are not supported on Fargate.

Issues with other options:

* Fargate profiles do not automatically run all pods on Fargate; only pods matching selectors run on Fargate.
* Fargate profiles are not related to EC2 instance types; Fargate is a serverless container execution environment.
* Fargate profiles do not set cluster-wide resource quotas. Resource quotas are managed through Kubernetes ResourceQuota.

</details>

2. How should you plan an EKS upgrade?
   * A) Upgrade nodes to the target version first and review compatibility later
   * B) Prepare compatibility/current versions, then control plane → nodes, coordinating each add-on update
   * C) Upgrade every add-on blindly to latest as the entire preparation
   * D) Change all components simultaneously

<details>
<summary>Show Answer</summary>

**Answer: B) Prepare compatibility/current versions, then control plane → nodes, coordinating each add-on update**

First check current cluster/node versions, upgrade insights, removed APIs, webhook/CRD/add-on compatibility, spare subnet IPs and the recovery plan. Bring lagging nodes to the current control plane version before moving to the next minor.

**1. Control plane**

Advance one minor version at a time. Current kubelets cannot be newer than the API server and may be up to three minors older, but EKS recommends matching versions before and after upgrades. The maximum permitted skew is not a steady-state target.

```bash
# Inspect the current version and node versions before choosing the next minor.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status}' --output table
kubectl --context "${EXAMPLE_CONTEXT:?}" get nodes

# Choose one interface, after prerequisite checks and workload testing.
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?Select the next supported minor}"
# Alternative:
# eksctl upgrade cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --version "$NEXT_MINOR_VERSION" --approve

# Use the update ID returned above. Proceed only after status is Successful.
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "${CONTROL_PLANE_UPDATE_ID:?}" --query update.status
```

**2. Nodes**

After the control plane update succeeds, initiate managed node group updates and check their update status, node readiness and kubelet versions. Conventional node groups do not update automatically with the control plane. Operators update self-managed/Hybrid Nodes; recreate Fargate Pods to use the new version. AWS incrementally updates Auto Mode nodes.

```bash
aws eks update-nodegroup-version --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
# Alternative:
# eksctl upgrade nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --name "$EXAMPLE_NODEGROUP" --kubernetes-version "$NEXT_MINOR_VERSION"
```

**3. Add-ons and clients**

Review compatibility with both the current and target versions in advance. Some CNI, webhook or controller components need compatible updates before the control plane, so add-ons are not universally the last step. After the control plane update, bring remaining add-ons, Cluster Autoscaler and kubectl to supported versions and validate each.

```bash
aws eks describe-addon-versions --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}" \
  --query 'addons[].addonVersions[].addonVersion' --output table

# Select a compatible EKS add-on build after reviewing configuration changes.
aws eks update-addon --cluster-name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_ADDON_VERSION:?}" \
  --resolve-conflicts PRESERVE
```

`PRESERVE` retains user configuration; it does not guarantee compatibility. Check PDBs, spare capacity and graceful termination, and do not hide failures with force flags. Validate each stage and prepare restorable application/data backups. AWS control plane backups do not replace a customer data recovery plan.

EKS now supports rollback to the previous minor within seven days of an eligible completed upgrade. Node, add-on, API-change and support-policy constraints apply, and application data is not automatically restored. Follow the [upgrade procedure](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) and [rollback conditions](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html).

</details>

3. Which is NOT a key feature of the VPC CNI plugin in Amazon EKS?
   * A) Assigning VPC IP addresses to pods
   * B) Applying security groups at the pod level
   * C) Encrypting network traffic between pods
   * D) Expanding IP addresses through prefix delegation

<details>

<summary>Show Answer</summary>

**Answer: C) Encrypting network traffic between pods**

Amazon VPC CNI does not provide blanket Pod-to-Pod traffic encryption. Configure application TLS/mTLS or an explicitly supported mesh/CNI encryption feature. NetworkPolicy alone filters traffic; it does not encrypt it.

The actual key features of the Amazon VPC CNI plugin include:

1. **Assigning VPC IP addresses to pods**:
   * Ordinary Pods receive VPC IPs; `hostNetwork` Pods share the node network.
   * This allows pods to communicate directly with other resources in the VPC.
   * Pod IPs are routable within the VPC, eliminating the need for complex overlay networks.
2. **Applying security groups at the pod level**:
   * AWS security groups can be applied to individual pods through the SecurityGroupsForPods feature.
   * This allows implementing fine-grained network security policies at the pod level.
   *   Example configuration:

       ```yaml
       apiVersion: vpcresources.k8s.aws/v1beta1
       kind: SecurityGroupPolicy
       metadata:
         name: my-security-group-policy
         namespace: default
       spec:
         podSelector:
           matchLabels:
             app: my-app
         securityGroups:
           groupIds:
             - sg-0123456789abcdef0
       ```
3. **Expanding IP addresses through prefix delegation**:
   * By default, each node can allocate a limited number of IP addresses (varies by instance type) to pods.
   * Using the prefix delegation feature, you can allocate /28 CIDR blocks (16 IPs) to each node, increasing the available IP addresses.
   * This increases per-ENI address capacity but consumes existing subnet addresses. It requires contiguous free prefixes and does not create new subnet capacity.
4. **Custom networking**:
   * Pods can be placed in specific subnets.
   * Pod networking can be configured using multiple network interfaces.
5. **Kubernetes host networking**:
   * `hostNetwork` uses the node network; this is a Kubernetes Pod setting, not a CNI encryption or isolation feature.
   * Useful for workloads where network performance is critical.

Apply VPC CNI capabilities separately after checking their prerequisites.

| Setting | Required checks |
| --- | --- |
| `ENABLE_PREFIX_DELEGATION` | Supported instance/CNI version, contiguous free `/28` blocks, kubelet max-pods and a new-node transition plan |
| `ENABLE_POD_ENI` | Supported trunk/branch ENI instances, VPC resource controller permissions, SecurityGroupPolicy and DNS/security group rules |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | IPv4, Pod subnets/security groups in the same VPC/AZ, node ENIConfig selection and free IPs |

Enabling a flag alone can make old/new Pods behave differently or fail IP allocation. Follow the official transition procedure without conflicting with EKS-managed add-on configuration. Do not apply this conventional EC2 DaemonSet approach directly to Auto Mode, Fargate or Hybrid Nodes.

```bash
# Inspect current non-secret CNI flags; this does not enable any feature.
kubectl --context "${EXAMPLE_CONTEXT:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="aws-node")].env}{"\n"}'
```


To implement network traffic encryption between pods, consider the following alternatives:

* Existing App Mesh users need migration before its September 30, 2026 end of support.
* Implementing Istio service mesh
* Using Cilium's transparent encryption feature
* Implementing TLS/mTLS at the application level

</details>

4. How can a developer IAM role receive namespace-scoped Kubernetes read access?
   * A) Attach a Kubernetes Role directly to an IAM user
   * B) Use an EKS access entry to map the IAM role to a Kubernetes group and configure RBAC bindings
   * C) Attach only an S3 policy to the cluster IAM role
   * D) Grant a developer kubectl access solely through an application ServiceAccount IRSA setting

<details>
<summary>Show Answer</summary>

**Answer: B) Use an EKS access entry to map the IAM role to a Kubernetes group and configure RBAC bindings**

Use an **EKS access entry** for new IAM access. The cluster authentication mode must be `API` or `API_AND_CONFIG_MAP`. Prepare mapping migration and an administrator recovery path before changing an existing cluster's mode. `aws-auth` is deprecated and is not the only mapping mechanism.

This example associates an existing developer IAM role with `dev-readers`. An IAM identity and access entry do not automatically create Kubernetes RBAC objects.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.accessConfig.authenticationMode

aws eks create-access-entry --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --principal-arn "${DEV_ROLE_ARN:?Existing developer IAM role}" \
  --type STANDARD --kubernetes-groups dev-readers
```

An administrator applies this Role and RoleBinding in the existing `dev` namespace. It grants Pod/Deployment read access, without Secret or mutation permissions. Workload creation permissions can permit use of namespace Secrets and need separate review.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: dev-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-readers
  namespace: dev
subjects:
- kind: Group
  name: dev-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: dev-reader
  apiGroup: rbac.authorization.k8s.io
```

Using an identity allowed to assume the role, create a dedicated kubeconfig and verify actual permissions. The first check should allow and the second should deny, unless another RBAC grant or EKS access policy adds permission.

```bash
aws eks update-kubeconfig --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --role-arn "${DEV_ROLE_ARN:?}" --kubeconfig "${DEV_KUBECONFIG:?Use a dedicated file}"
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get pods -n dev
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get secrets -n dev
```

Alternatively, associate a namespace-scoped EKS access policy with the entry. Access policies and RBAC grants are additive; attaching an IAM policy alone does not grant Kubernetes permissions. IRSA/Pod Identity provide a separate path for Pods to call AWS APIs. Do not grant ordinary developers `system:masters` or overwrite the whole `aws-auth` ConfigMap.

</details>

5. Which description of EKS version support is correct?
   * A) All versions supported indefinitely
   * B) All support ends after 12 months
   * C) Always exactly the latest version plus three previous versions
   * D) 14 months standard plus 12 months paid extended support after EKS release

<details>
<summary>Show Answer</summary>

**Answer: D) 14 months standard plus 12 months paid extended support after EKS release**

An EKS minor version receives **14 months of standard support from its EKS release date**, followed by **12 months of paid extended support**. The clock does not start at the upstream release date.

* Official list on September 11, 2026: standard support **1.34–1.36**, extended support **1.31–1.33**. Upstream 1.37 release does not imply EKS availability.
* Extended support is enabled by default. Selecting the `STANDARD` upgrade policy opts out and makes the cluster subject to automatic upgrade after standard support ends.
* After extended support ends, AWS automatically upgrades the control plane to a supported version. Exact execution time is not guaranteed, so operators should plan upgrades proactively.
* Managed/self-managed/Hybrid Nodes do not update solely because the control plane automatically upgraded. Plan Fargate Pod replacement and add-on updates separately; Auto Mode nodes follow managed updates.
* Supported versions receive security patches; indefinite retention of every version is not supported. New clusters cannot be created on versions past end of support.

Check the release calendar and version information in the actual region. Grepping add-on metadata is not a substitute for the cluster version support list.

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,upgradePolicy:upgradePolicy}' --output json
```

Maintain an upgrade schedule, review removed APIs/compatibility, test in a nonproduction environment, prepare application/data recovery and advance one minor at a time. EKS offers at least three standard-support versions, without a fixed “latest plus three only” rule.

</details>


## Official references and validation scope

- [EKS version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Pod Identity and IRSA](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)
- [Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Auto Mode load balancing](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [FSx CSI configuration and PVC capacity](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)
- [Fargate limitations](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Prefix delegation](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)
- [Custom networking](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html)
- [EKS pricing](https://aws.amazon.com/eks/pricing/)
- [Fargate pricing](https://aws.amazon.com/fargate/pricing/)
- [eksctl 0.230.0 schema](https://github.com/eksctl-io/eksctl/blob/v0.230.0/pkg/apis/eksctl.io/v1alpha5/assets/schema.json)
- [LBC 3.5.0 installation](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/installation.md)
- [Metrics Server 0.9.0 compatibility](https://github.com/kubernetes-sigs/metrics-server/blob/v0.9.0/README.md)

This is a static review against official documentation and release schemas. No cluster/IAM/load balancer provisioning, application deployment, upgrade/rollback, NGINX execution, load test or cost measurement was performed. Expected example behavior is not a measured result.
