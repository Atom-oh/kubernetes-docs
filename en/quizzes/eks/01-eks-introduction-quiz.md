# Amazon EKS Introduction Quiz

This quiz tests your understanding of the basic concepts and features of Amazon Elastic Kubernetes Service (EKS). It covers topics such as EKS architecture, components, management methods, and pricing models.

## Multiple Choice Questions

1. What is the main benefit of Amazon EKS (Elastic Kubernetes Service)?
   - A) No need to manage your own Kubernetes control plane infrastructure
   - B) Lower cost than other managed Kubernetes services
   - C) Can only use AWS services
   - D) Can only run in a single availability zone

<details>
<summary>Show Answer</summary>

**Answer: A) No need to manage your own Kubernetes control plane infrastructure**

**Explanation:**
The main benefit of Amazon EKS (Elastic Kubernetes Service) is that you don't need to manage your own Kubernetes control plane infrastructure. Since AWS manages the availability and scalability of the Kubernetes control plane, users can focus on running their workloads.

Key benefits of EKS:
- **Managed Control Plane**: AWS manages control plane nodes, etcd cluster, API server, etc.
- **High Availability**: The control plane is deployed across multiple availability zones, eliminating single points of failure.
- **Automatic Upgrades and Patches**: AWS manages Kubernetes version upgrades and security patches.
- **Integration with AWS Services**: Seamlessly integrates with various AWS services including IAM, VPC, ELB, ECR, etc.
- **Standard Kubernetes**: Provides fully compatible Kubernetes to prevent vendor lock-in.

Issues with other options:
- EKS is not necessarily cheaper than other managed Kubernetes services. There is actually an hourly fee for the control plane.
- EKS can run any Kubernetes-compatible applications and services, not just AWS services.
- EKS clusters are deployed across multiple availability zones by default for high availability.
</details>

2. Where is the Amazon EKS cluster control plane deployed?
   - A) Within the user's VPC
   - B) Deployed across multiple availability zones in an AWS-managed account
   - C) In a single availability zone chosen by the user
   - D) Running on user's EC2 instances

<details>
<summary>Show Answer</summary>

**Answer: B) Deployed across multiple availability zones in an AWS-managed account**

**Explanation:**
The Amazon EKS cluster control plane is deployed across multiple availability zones in an AWS-managed account. This is one of the core aspects of EKS as a managed service.

Key characteristics of EKS control plane deployment:
- **AWS-Managed Infrastructure**: The control plane runs in an AWS-owned and managed account.
- **Multi-AZ Deployment**: Deployed across at least 3 availability zones for high availability.
- **Auto Recovery**: AWS monitors the health of control plane components and automatically replaces failed components.
- **Endpoint Accessibility**: Control plane endpoints can be configured as publicly accessible or accessible only within the VPC.
- **Auto Scaling**: Control plane capacity automatically adjusts based on cluster load.

Issues with other options:
- The control plane is not deployed within the user's VPC. Instead, a connection is established between the user's VPC and the AWS-managed VPC through ENI (Elastic Network Interface).
- The control plane is deployed across multiple availability zones, not a single one, to ensure high availability.
- The control plane runs on AWS-managed infrastructure, not on user's EC2 instances.
</details>

3. Which is NOT a valid method for managing worker nodes in Amazon EKS?
   - A) Self-managed node groups
   - B) Managed node groups
   - C) Fargate profiles
   - D) EKS automatic node provisioning

<details>
<summary>Show Answer</summary>

**Answer: D) EKS automatic node provisioning**

**Explanation:**
"EKS automatic node provisioning" is not an officially provided worker node management method in Amazon EKS. This feature does not exist.

The actual methods for managing worker nodes in Amazon EKS are:

1. **Self-managed node groups**:
   - Users directly create and manage EC2 instances.
   - Can be managed through Auto Scaling groups.
   - Provides complete control over node configuration.
   - Has the highest operational overhead.

2. **Managed node groups**:
   - AWS manages node provisioning and lifecycle.
   - Node upgrades, patches, and adjustments are automated.
   - Based on EC2 Auto Scaling groups.
   - Uses standard Amazon Linux or Bottlerocket AMI.

3. **Fargate profiles**:
   - A serverless computing option that eliminates the need to manage individual EC2 instances.
   - Provisions computing resources per pod.
   - Has the lowest infrastructure management overhead.
   - Has certain limitations (e.g., no DaemonSet support, certain resource restrictions).

For node auto-scaling, EKS supports tools like Kubernetes Cluster Autoscaler or Karpenter, but there is no official feature called "EKS automatic node provisioning."
</details>

4. What CNI plugin is used by default for pod networking in Amazon EKS clusters?
   - A) Flannel
   - B) Calico
   - C) AWS VPC CNI
   - D) Weave Net

<details>
<summary>Show Answer</summary>

**Answer: C) AWS VPC CNI**

**Explanation:**
The CNI (Container Network Interface) plugin used by default for pod networking in Amazon EKS clusters is AWS VPC CNI. This plugin directly integrates Amazon VPC networking with Kubernetes pods.

Key features of AWS VPC CNI:
- **VPC-native IP address assignment**: Pods receive IP addresses directly from the VPC, existing in the same network space as other resources in the VPC.
- **Secondary IP address usage**: Assigns secondary IP addresses connected to each node's Elastic Network Interface (ENI) to pods.
- **Security group integration**: Security groups can be applied at the pod level (SecurityGroupsForPods feature).
- **VPC flow log visibility**: Pod traffic is visible in VPC flow logs.
- **Leverage AWS networking features**: Features like VPC peering, Transit Gateway, PrivateLink can be directly utilized by pods.

AWS VPC CNI is an open-source project, and you can check the code on GitHub: https://github.com/aws/amazon-vpc-cni-k8s

Other CNI plugins (Flannel, Calico, Weave Net, etc.) can be installed on EKS, but AWS VPC CNI is provided by default.
</details>

5. What is the method for managing authentication and authorization for Kubernetes resources in Amazon EKS?
   - A) Using only Kubernetes service accounts
   - B) Integration of AWS IAM and Kubernetes RBAC
   - C) EKS-specific permission management system
   - D) User authentication through AWS Cognito

<details>
<summary>Show Answer</summary>

**Answer: B) Integration of AWS IAM and Kubernetes RBAC**

**Explanation:**
Amazon EKS manages authentication and authorization for Kubernetes resources through the integration of AWS IAM (Identity and Access Management) and Kubernetes RBAC (Role-Based Access Control). This integrated approach combines AWS's powerful identity management capabilities with Kubernetes's fine-grained permission control.

Key features:
- **IAM Authentication**: Authenticates to the Kubernetes API server using AWS IAM credentials.
- **aws-auth ConfigMap**: Maps IAM roles or users to Kubernetes users and groups.
- **RBAC Authorization**: Uses the Kubernetes RBAC system to control permissions within the cluster.
- **IRSA (IAM Roles for Service Accounts)**: Links IAM roles to Kubernetes service accounts, allowing pods to securely access AWS services.

How it works:
1. Users obtain an authentication token for the Kubernetes API server using the `aws eks get-token` command (via AWS CLI or AWS SDK).
2. This token is signed using IAM credentials.
3. The Kubernetes API server validates the token using the AWS IAM authenticator.
4. Based on the mappings in the aws-auth ConfigMap, users are assigned Kubernetes users and groups.
5. The Kubernetes RBAC system allows or denies requests based on permissions granted to those users or groups.

Issues with other options:
- Using only Kubernetes service accounts limits integration with AWS services.
- EKS does not have a separate dedicated permission management system; it integrates standard Kubernetes RBAC with AWS IAM.
- AWS Cognito is not directly used for EKS authentication, though it can be configured as an OIDC provider.
</details>

6. What is the recommended method for pods to access AWS services (e.g., S3, DynamoDB) in an Amazon EKS cluster?
   - A) Granting IAM roles to nodes using EC2 instance profiles
   - B) Injecting AWS credentials directly into pods as environment variables
   - C) Linking IAM roles to Kubernetes service accounts (IRSA)
   - D) Storing AWS credentials as Kubernetes Secrets and mounting them

<details>
<summary>Show Answer</summary>

**Answer: C) Linking IAM roles to Kubernetes service accounts (IRSA)**

**Explanation:**
The recommended method for pods to access AWS services in an Amazon EKS cluster is linking IAM roles to Kubernetes service accounts. This feature is called IRSA (IAM Roles for Service Accounts) and provides fine-grained permissions at the pod level.

Key benefits of IRSA:
- **Principle of least privilege**: You can grant only the minimum permissions needed for each application.
- **Permission isolation**: Different pods running on the same node can have different IAM permissions.
- **Simplified credential management**: No need to directly manage AWS credentials.
- **Enhanced security**: Credentials are not hardcoded in code or configuration.

How to set up IRSA:
1. Associate an OpenID Connect (OIDC) provider with the EKS cluster:
   ```bash
   eksctl utils associate-iam-oidc-provider --cluster=<cluster-name> --approve
   ```

2. Create an IAM role for the service account:
   ```bash
   eksctl create iamserviceaccount \
     --name=<service-account-name> \
     --namespace=<namespace> \
     --cluster=<cluster-name> \
     --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
     --approve
   ```

3. Reference the service account in the pod manifest:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: my-pod
   spec:
     serviceAccountName: <service-account-name>
     containers:
     - name: my-container
       image: my-image
   ```

Issues with other options:
- Using EC2 instance profiles gives all pods on the same node the same permissions, violating the principle of least privilege.
- Injecting AWS credentials as environment variables risks credential exposure and makes credential rotation difficult.
- Storing AWS credentials as Kubernetes Secrets adds credential management burden and complicates credential rotation.
</details>

7. Which statement about the logging feature of Amazon EKS clusters is correct?
   - A) All logs are sent to CloudWatch Logs by default
   - B) Control plane logs can optionally be sent to CloudWatch Logs
   - C) Only worker node logs can be sent to CloudWatch Logs
   - D) EKS does not provide logging functionality

<details>
<summary>Show Answer</summary>

**Answer: B) Control plane logs can optionally be sent to CloudWatch Logs**

**Explanation:**
In Amazon EKS clusters, control plane logs can optionally be sent to CloudWatch Logs. This feature is disabled by default, and users can choose to enable the log types they need.

Key features of EKS control plane logging:
- **Optional activation**: Can be enabled during cluster creation or on existing clusters.
- **Log type selection**: You can select only the log types you need from:
  - API server (api)
  - Audit (audit)
  - Authenticator (authenticator)
  - Controller manager (controllerManager)
  - Scheduler (scheduler)
- **CloudWatch Logs integration**: Selected logs are sent to AWS CloudWatch Logs for storage, analysis, and monitoring.
- **Cost consideration**: CloudWatch Logs pricing applies to log storage.

How to enable logging:
```bash
# Enable logging using AWS CLI
aws eks update-cluster-config \
    --region <region> \
    --name <cluster-name> \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable logging using eksctl
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster <cluster-name> --region <region>
```

Worker node logging:
- Worker node logs are not included in the EKS control plane logging feature.
- To send worker node logs to CloudWatch Logs, you need to install the CloudWatch agent or configure a logging solution like Fluentd/Fluent Bit.

Issues with other options:
- Not all logs are sent to CloudWatch Logs by default. Users must explicitly enable them.
- It's not that only worker node logs can be sent to CloudWatch Logs; control plane logs can also be sent.
- EKS does provide control plane logging functionality.
</details>

8. Which is NOT a cost component of an Amazon EKS cluster?
   - A) EKS control plane hourly fee
   - B) EC2 instance costs for worker nodes
   - C) Fargate pod execution costs
   - D) Kubernetes license fees

<details>
<summary>Show Answer</summary>

**Answer: D) Kubernetes license fees**

**Explanation:**
Kubernetes license fees are not a cost component of Amazon EKS clusters. Kubernetes is open-source software managed by the Cloud Native Computing Foundation (CNCF) and is free to use under the Apache 2.0 license. Therefore, there are no separate Kubernetes license fees when using EKS.

Actual cost components of Amazon EKS clusters include:

1. **EKS control plane hourly fee**:
   - A fixed hourly fee is charged for each EKS cluster (e.g., $0.10 per hour).
   - This cost is constant regardless of cluster size or workload.
   - Fees are charged per region if spanning multiple regions.

2. **EC2 instance costs for worker nodes**:
   - Costs are incurred for EC2 instances used in self-managed or managed node groups.
   - Costs vary based on instance type, size, quantity, and runtime.
   - Costs can be optimized through Reserved Instances, Savings Plans, and Spot Instances.

3. **Fargate pod execution costs**:
   - When using Fargate, costs are charged based on vCPU and memory resources allocated to pods.
   - Costs are calculated per second based on pod runtime.
   - No node management overhead, but generally more expensive than EC2-based nodes.

4. **Additional AWS resource costs**:
   - EBS volumes
   - Load balancers (NLB, ALB)
   - CloudWatch logs and metrics
   - NAT Gateway
   - Data transfer

Cost optimization strategies:
- Selecting appropriate instance types
- Configuring auto-scaling
- Using Spot Instances
- Cluster automation and scheduled scaling
- Optimizing resource requests and limits
- Cost monitoring and analysis
</details>

9. What is the correct method for implementing load balancing in an Amazon EKS cluster?
   - A) Using the built-in EKS load balancer
   - B) Integrating Kubernetes Service resources with AWS Load Balancer Controller
   - C) Manually creating and configuring EC2 load balancers
   - D) EKS does not support load balancing

<details>
<summary>Show Answer</summary>

**Answer: B) Integrating Kubernetes Service resources with AWS Load Balancer Controller**

**Explanation:**
The correct method for implementing load balancing in an Amazon EKS cluster is integrating Kubernetes Service resources with AWS Load Balancer Controller. This approach combines Kubernetes's declarative resource management with AWS's load balancing capabilities.

Methods for implementing load balancing in EKS:

1. **Default LoadBalancer type Service**:
   - Creating a `LoadBalancer` type Service in Kubernetes provisions a Classic Load Balancer (CLB) or Network Load Balancer (NLB) by default.
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: my-service
   spec:
     type: LoadBalancer
     ports:
     - port: 80
       targetPort: 8080
     selector:
       app: my-app
   ```

2. **AWS Load Balancer Controller**:
   - Install AWS Load Balancer Controller for more advanced features to manage Application Load Balancer (ALB) and Network Load Balancer (NLB).
   - ALB can be provisioned and configured through Ingress resources.
   - Various load balancer attributes can be configured through annotations.

   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: my-ingress
     annotations:
       kubernetes.io/ingress.class: alb
       alb.ingress.kubernetes.io/scheme: internet-facing
       alb.ingress.kubernetes.io/target-type: ip
   spec:
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

3. **Service annotations**:
   - Annotations can be added to services to specify load balancer type and configuration.
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: my-service
     annotations:
       service.beta.kubernetes.io/aws-load-balancer-type: nlb
       service.beta.kubernetes.io/aws-load-balancer-internal: "true"
   spec:
     type: LoadBalancer
     # ...
   ```

Issues with other options:
- There is no separate "built-in EKS load balancer" component in EKS. Load balancing is provided through the integration of Kubernetes Service resources and AWS load balancers.
- While it's possible to manually create and configure EC2 load balancers, it doesn't align with Kubernetes's declarative approach and complicates management.
- EKS fully supports load balancing.
</details>

10. Which is NOT a valid method for managing storage in an Amazon EKS cluster?
    - A) Provisioning EBS volumes using the EBS CSI driver
    - B) Mounting EFS file systems using the EFS CSI driver
    - C) Automatic volume provisioning through EKS built-in storage manager
    - D) Connecting high-performance file systems using the FSx for Lustre CSI driver

<details>
<summary>Show Answer</summary>

**Answer: C) Automatic volume provisioning through EKS built-in storage manager**

**Explanation:**
"EKS built-in storage manager" is a feature that does not exist. Amazon EKS does not have a built-in storage manager for automatic volume provisioning; storage is managed through CSI (Container Storage Interface) drivers.

The actual methods for managing storage in Amazon EKS clusters include:

1. **EBS CSI driver**:
   - Allows connecting Amazon EBS (Elastic Block Store) volumes to Kubernetes pods.
   - Suitable for applications requiring block storage (databases, etc.).
   - Supports dynamic provisioning, snapshots, and volume resizing.
   - Accessible only within a single availability zone (ReadWriteOnce access mode).

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

2. **EFS CSI driver**:
   - Allows mounting Amazon EFS (Elastic File System) to Kubernetes pods.
   - Suitable for shared file systems that need to be accessed by multiple pods simultaneously.
   - Accessible across multiple availability zones (ReadWriteMany access mode).
   - Suitable for web servers, CMS, CI/CD pipelines, etc.

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

3. **FSx for Lustre CSI driver**:
   - Allows connecting Amazon FSx for Lustre to Kubernetes pods.
   - Suitable for high-performance workloads such as high-performance computing, machine learning, and big data analytics.
   - Provides high throughput and low latency.

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
     storageCapacity: "1200"
   ```

4. **Other storage options**:
   - Amazon S3 (Simple Storage Service) through CSI drivers or S3 mounters
   - Amazon FSx for Windows File Server
   - Amazon FSx for NetApp ONTAP
   - Third-party storage solutions (Portworx, Rook, etc.)

Storage management best practices:
- Select appropriate storage types for workload requirements
- Configure StorageClass for dynamic provisioning
- Establish backup and recovery strategies
- Monitor storage performance
- Select appropriate storage classes and sizes for cost optimization
</details>

## Hands-on Exercises

### Exercise 1: Creating and Configuring an EKS Cluster

**Scenario:**
You are a DevOps engineer at your company, and you need to set up an Amazon EKS cluster for your development team. The cluster is for the development environment and should be cost-effective while providing all necessary features.

**Requirements:**
1. Create a cost-effective EKS cluster
2. Configure appropriate node groups
3. Set up basic monitoring
4. Configure kubectl access to the cluster

**Solution:**

<details>
<summary>Show Solution</summary>

#### 1. Create EKS Cluster Using eksctl

```bash
# Install eksctl (if not already installed)
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version

# Create cluster
cat << EOF > eks-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: dev-cluster
  region: us-west-2
  version: "1.28"

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: false
        ebs: true
        fsx: false
        efs: false
        albIngress: true
        xRay: false
        cloudWatch: true

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

eksctl create cluster -f eks-cluster.yaml
```

#### 2. Configure and Verify kubectl

```bash
# Update kubectl configuration
aws eks update-kubeconfig --name dev-cluster --region us-west-2

# Verify cluster connection
kubectl get nodes
kubectl cluster-info
```

#### 3. Verify Basic Monitoring Components

```bash
# Check basic system pods
kubectl get pods -n kube-system

# Install metrics server (if not provided by default)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify metrics server operation
kubectl get deployment metrics-server -n kube-system
kubectl top nodes
```

#### 4. Install AWS Load Balancer Controller

```bash
# Create IAM policy
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json
aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam-policy.json

# Set up IRSA
eksctl create iamserviceaccount \
  --cluster=dev-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::<AWS_ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve

# Install controller with Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=dev-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

#### 5. Check Cluster Status

```bash
# Check node status
kubectl get nodes -o wide

# Check system pod status
kubectl get pods -n kube-system

# Check cluster events
kubectl get events --sort-by='.lastTimestamp'

# Check cluster info
kubectl cluster-info
```

#### 6. Deploy Test Application

```bash
# Deploy simple nginx
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# Verify deployment
kubectl get deployment nginx
kubectl get service nginx
```

Through this exercise, you learned how to create a cost-effective EKS cluster, set up basic monitoring, and configure the load balancer controller to expose applications externally. The t3.medium instance type is a cost-effective choice suitable for development environments, and auto-scaling settings allow nodes to scale as needed.
</details>

### Exercise 2: Deploying Applications and Exposing Services in an EKS Cluster

**Scenario:**
Your team has developed a web application based on microservices architecture. You need to deploy this application to the EKS cluster and configure it to be accessible from outside.

**Requirements:**
1. Deploy frontend and backend services
2. Configure inter-service communication
3. Configure external access through ingress controller
4. Set up basic scaling

**Solution:**

<details>
<summary>Show Solution</summary>

#### 1. Create Namespace

```bash
kubectl create namespace web-app
kubectl config set-context --current --namespace=web-app
```

#### 2. Deploy Backend Service

```yaml
# backend-deployment.yaml
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
      containers:
      - name: backend
        image: nginx:alpine  # Replace with actual backend image
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
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
    targetPort: 8080
```

```bash
kubectl apply -f backend-deployment.yaml
```

#### 3. Deploy Frontend Service

```yaml
# frontend-deployment.yaml
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
      containers:
      - name: frontend
        image: nginx:alpine  # Replace with actual frontend image
        ports:
        - containerPort: 80
        env:
        - name: BACKEND_URL
          value: "http://backend-service"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
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
    targetPort: 80
```

```bash
kubectl apply -f frontend-deployment.yaml
```

#### 4. Create Ingress Resource (Using AWS ALB Ingress Controller)

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
spec:
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
```

```bash
kubectl apply -f ingress.yaml
```

#### 5. Configure Horizontal Pod Autoscaling (HPA)

```yaml
# hpa.yaml
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
```

```bash
kubectl apply -f hpa.yaml
```

#### 6. Check Deployment Status

```bash
# Check deployment status
kubectl get deployments -n web-app

# Check service status
kubectl get services -n web-app

# Check ingress status
kubectl get ingress -n web-app

# Check HPA status
kubectl get hpa -n web-app

# Get ALB address
kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

#### 7. Load Test and Verify Scaling

```bash
# Get ALB address
ALB_ADDRESS=$(kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Load test (requires separate tool)
# Example: Using Apache Bench
ab -n 10000 -c 100 http://$ALB_ADDRESS/

# Verify scaling
kubectl get hpa -n web-app -w
```

Through this exercise, you learned how to deploy a microservices architecture application to an EKS cluster, expose it externally using AWS ALB Ingress Controller, and configure auto-scaling through HPA. Resource requests and limits were appropriately set to ensure efficient resource usage, and path-based routing was implemented through ingress rules.
</details>

## Advanced Topics

The following are questions about advanced Amazon EKS topics. This section tests your understanding of advanced EKS features and integrations.

1. What is the correct description when configuring a Fargate profile in Amazon EKS?
   - A) Fargate profiles specify that pods should run on Fargate based on specific namespaces and labels
   - B) Fargate profiles automatically run all pods on Fargate
   - C) Fargate profiles restrict pod execution to specific EC2 instance types
   - D) Fargate profiles set resource quotas for the entire cluster

<details>
<summary>Show Answer</summary>

**Answer: A) Fargate profiles specify that pods should run on Fargate based on specific namespaces and labels**

**Explanation:**
An Amazon EKS Fargate profile is a configuration that specifies which pods should run on Fargate based on specific namespaces and labels. This allows configuring a hybrid architecture using both serverless container execution environments and EC2-based nodes.

Key features of Fargate profiles:
- **Selective execution**: Only pods matching the conditions defined in the profile run on Fargate, not all pods.
- **Namespace and label selectors**: Pods are selected based on specific namespace and label combinations.
- **Subnet specification**: You can specify private subnets where pods will run.
- **IAM role**: Specify the IAM execution role for Fargate pods.

Fargate profile creation example:
```bash
eksctl create fargateprofile \
  --cluster my-cluster \
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
- DaemonSets are not supported on Fargate.
- Privileged containers cannot run.
- HostNetwork and HostPort are not supported.
- GPU workloads are not supported.
- Per-pod costs apply, so cost planning is necessary.
- Storage is limited to ephemeral storage (persistent volumes possible through EFS).

Issues with other options:
- Fargate profiles do not automatically run all pods on Fargate; only pods matching selectors run on Fargate.
- Fargate profiles are not related to EC2 instance types; Fargate is a serverless container execution environment.
- Fargate profiles do not set cluster-wide resource quotas. Resource quotas are managed through Kubernetes ResourceQuota.
</details>

2. What is the correct order when performing a cluster upgrade in Amazon EKS?
   - A) Worker node upgrade -> Control plane upgrade -> Add-on upgrade
   - B) Control plane upgrade -> Worker node upgrade -> Add-on upgrade
   - C) Add-on upgrade -> Control plane upgrade -> Worker node upgrade
   - D) Upgrade all components simultaneously

<details>
<summary>Show Answer</summary>

**Answer: B) Control plane upgrade -> Worker node upgrade -> Add-on upgrade**

**Explanation:**
The correct order for an Amazon EKS cluster upgrade is to first upgrade the control plane, then the worker nodes, and finally the add-ons. This order follows Kubernetes's version compatibility model and minimizes potential issues during the upgrade process.

#### 1. Control Plane Upgrade
- The control plane acts as the cluster's brain and should be upgraded first.
- Kubernetes is designed so that the control plane can be up to 2 minor versions ahead of nodes.
- Control plane upgrades can be performed through the AWS Management Console, AWS CLI, or eksctl.

```bash
# Control plane upgrade using AWS CLI
aws eks update-cluster-version --name my-cluster --kubernetes-version 1.28

# Control plane upgrade using eksctl
eksctl upgrade cluster --name=my-cluster --version=1.28 --approve
```

#### 2. Worker Node Upgrade
- After the control plane upgrade is complete, upgrade the worker nodes.
- For managed node groups, upgrades can be done through AWS Management Console, AWS CLI, or eksctl.
- For self-managed nodes, nodes must be replaced with new AMIs.

```bash
# Managed node group upgrade
aws eks update-nodegroup-version --cluster-name my-cluster --nodegroup-name my-nodegroup

# Managed node group upgrade using eksctl
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

#### 3. Add-on Upgrade
- Finally, upgrade cluster add-ons (kube-proxy, CoreDNS, Amazon VPC CNI, etc.).
- Add-ons are designed to be compatible with specific Kubernetes versions, so they should be upgraded after the control plane and node upgrades.

```bash
# Add-on upgrade using AWS CLI
aws eks update-addon --cluster-name my-cluster --addon-name vpc-cni --addon-version v1.12.0-eksbuild.1

# Add-on upgrade using eksctl
eksctl update addon --name vpc-cni --version v1.12.0-eksbuild.1 --cluster my-cluster
```

#### Upgrade Best Practices:
- Check cluster status and backup before upgrade
- Test upgrade in test environment first
- Consider blue/green deployment strategy
- Configure PodDisruptionBudget to minimize workload disruption during upgrade
- Upgrade one minor version at a time
- Validate workloads and system components after upgrade

Issues with other options:
- Upgrading worker nodes before the control plane can cause version compatibility issues.
- Upgrading add-ons first may result in new add-on versions being incompatible with the old Kubernetes version.
- Upgrading all components simultaneously is risky, and it's difficult to identify the cause if problems occur.
</details>

3. Which is NOT a key feature of the VPC CNI plugin in Amazon EKS?
   - A) Assigning VPC IP addresses to pods
   - B) Applying security groups at the pod level
   - C) Encrypting network traffic between pods
   - D) Expanding IP addresses through prefix delegation

<details>
<summary>Show Answer</summary>

**Answer: C) Encrypting network traffic between pods**

**Explanation:**
The Amazon VPC CNI (Container Network Interface) plugin does not automatically encrypt network traffic between pods. Pod-to-pod traffic encryption is not a basic feature of VPC CNI, and requires additional tools such as service meshes (e.g., AWS App Mesh, Istio) or network policy solutions (e.g., Calico, Cilium).

The actual key features of the Amazon VPC CNI plugin include:

1. **Assigning VPC IP addresses to pods**:
   - Each pod receives a unique IP address within the VPC.
   - This allows pods to communicate directly with other resources in the VPC.
   - Pod IPs are routable within the VPC, eliminating the need for complex overlay networks.

2. **Applying security groups at the pod level**:
   - AWS security groups can be applied to individual pods through the SecurityGroupsForPods feature.
   - This allows implementing fine-grained network security policies at the pod level.
   - Example configuration:
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
   - By default, each node can allocate a limited number of IP addresses (varies by instance type) to pods.
   - Using the prefix delegation feature, you can allocate /28 CIDR blocks (16 IPs) to each node, increasing the available IP addresses.
   - This solves IP address shortage problems in high-density deployment scenarios.

4. **Custom networking**:
   - Pods can be placed in specific subnets.
   - Pod networking can be configured using multiple network interfaces.

5. **Host networking integration**:
   - Pods can directly use the host network stack.
   - Useful for workloads where network performance is critical.

VPC CNI configuration examples:
```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Enable security group pods feature
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# Enable custom networking
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
```

To implement network traffic encryption between pods, consider the following alternatives:
- Using AWS App Mesh with TLS
- Implementing Istio service mesh
- Using Cilium's transparent encryption feature
- Implementing TLS/mTLS at the application level
</details>

4. What is the correct method for configuring IAM role-based access control (RBAC) for cluster authentication in Amazon EKS?
   - A) Directly assigning Kubernetes RBAC roles to IAM users
   - B) Configuring IAM role and Kubernetes group mappings in the aws-auth ConfigMap
   - C) Directly attaching IAM policies to the EKS cluster
   - D) Linking IAM roles to Kubernetes service accounts

<details>
<summary>Show Answer</summary>

**Answer: B) Configuring IAM role and Kubernetes group mappings in the aws-auth ConfigMap**

**Explanation:**
The correct method for configuring IAM role-based access control (RBAC) for cluster authentication in Amazon EKS is to configure mappings between IAM roles and Kubernetes groups using the `aws-auth` ConfigMap. This method allows integrating AWS IAM credentials with the Kubernetes RBAC system.

#### How aws-auth ConfigMap works:
1. EKS uses AWS IAM Authenticator to authenticate API requests.
2. The `aws-auth` ConfigMap maps IAM entities (users or roles) to Kubernetes users and groups.
3. The Kubernetes RBAC system grants permissions to these users and groups.

#### aws-auth ConfigMap configuration example:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EksAdminRole
      username: eks-admin
      groups:
        - system:masters
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-team
      groups:
        - dev-group
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin-user
      username: admin
      groups:
        - system:masters
    - userarn: arn:aws:iam::123456789012:user/read-only-user
      username: read-only
      groups:
        - read-only-group
```

#### Kubernetes RBAC role and binding configuration:
```yaml
# Create developer role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: developer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "deployments", "jobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

---
# Bind role to developer group
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-binding
  namespace: dev
subjects:
- kind: Group
  name: dev-group
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

#### IAM and RBAC configuration using eksctl:
```bash
# Add IAM role mapping
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:role/EksAdminRole \
  --username eks-admin \
  --group system:masters

# Add IAM user mapping
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:user/admin-user \
  --username admin \
  --group system:masters
```

#### Best practices:
- Apply the principle of least privilege
- Prefer IAM roles over individual IAM users
- Separate permissions by namespace
- Regularly review access permissions
- Grant cluster administrator permissions (system:masters) sparingly

Issues with other options:
- Kubernetes RBAC roles cannot be directly assigned to IAM users. Since IAM and Kubernetes are separate systems, mapping through the aws-auth ConfigMap is required.
- Directly attaching IAM policies to the EKS cluster is not related to RBAC permissions within the cluster. IAM policies control API call permissions on the cluster itself.
- Linking IAM roles to Kubernetes service accounts (IRSA) is for pods to access AWS services and serves a different purpose than cluster authentication and authorization.
</details>

5. What is the correct description of Amazon EKS's Kubernetes version support policy?
   - A) All Kubernetes versions are supported indefinitely
   - B) Each Kubernetes version is supported for 12 months after release
   - C) Only the latest version and previous 3 versions are supported
   - D) Each Kubernetes version is supported for 14 months after release

<details>
<summary>Show Answer</summary>

**Answer: D) Each Kubernetes version is supported for 14 months after release**

**Explanation:**
According to Amazon EKS's Kubernetes version support policy, each Kubernetes version is supported for 14 months after its release on EKS. After this period, the version is no longer supported, and you must upgrade your cluster to a supported version.

#### Key characteristics of EKS version support policy:
1. **14-month support period**:
   - Each Kubernetes version is supported for 14 months from the date it was released on EKS.
   - Support end dates are announced in advance by AWS.

2. **Standard support schedule**:
   - The Kubernetes community releases a new version approximately every 4 months.
   - EKS typically supports new Kubernetes versions within 2-3 months after the community release.
   - This results in typically 3-4 Kubernetes versions being supported simultaneously on EKS.

3. **No automatic upgrades**:
   - AWS does not automatically upgrade clusters even as support ends.
   - Cluster administrators must explicitly perform upgrades.

4. **Impact after support ends**:
   - Clusters running on unsupported versions continue to operate, but AWS no longer provides security patches or bug fixes.
   - New clusters cannot be created on unsupported versions.
   - AWS support is not available.

#### Version upgrade best practices:
- Establish regular upgrade schedules
- Monitor support end dates
- Test upgrades in test environments first
- Backup cluster before upgrade
- Upgrade one minor version at a time
- Consider blue/green deployment strategy

#### Checking version support status:
```bash
# Check available EKS versions
aws eks describe-addon-versions | grep kubernetesVersion

# Check specific cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"
```

Issues with other options:
- Not all Kubernetes versions are supported indefinitely. Each version is only supported for a defined period.
- Each version is supported for 14 months, not 12 months.
- There is no fixed rule of "only the latest version and previous 3 versions are supported"; the number of supported versions varies based on the Kubernetes community release schedule and EKS support policy.
</details>
