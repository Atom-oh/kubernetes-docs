# EKS Cluster Creation - Conclusion and Best Practices

> **Last Updated**: September 11, 2026

## Comparison of EKS Cluster Creation Methods

We have explored various methods for creating EKS clusters. Let's compare the advantages and disadvantages of each method.

Choose a tool by reproducibility, reviewability, team skills and lifecycle ownership. Every option can create a cluster that still needs workload/network/security validation. Keep each resource under one intended owner and review plans/change sets; do not mix manual changes with IaC without reconciling state.

### eksctl

**Advantages:**
- Concise EKS-focused workflows; speed depends on the requested resources
- Cluster creation with a single command
- Declarative configuration support through YAML files
- Support for various features like node groups and Fargate profiles

**Disadvantages:**
- May be limited for complex infrastructure requirements
- Integration with existing infrastructure can be difficult

**Suitable Use Cases:**
- Rapid prototyping
- Development and test environments
- Production environments with reviewed configuration, ownership and lifecycle controls

### AWS Management Console

**Advantages:**
- Easy to understand with visual interface
- Step-by-step guided cluster creation
- Visual confirmation of various options

**Disadvantages:**
- Manual process makes automation difficult
- Repetitive tasks are time-consuming
- Configuration management and version control are difficult

**Suitable Use Cases:**
- Learning and exploration
- One-time cluster creation
- Small teams or projects

### AWS CLI

**Advantages:**
- Automation possible through scripts
- Fine-grained control available
- Easy integration with AWS services

**Disadvantages:**
- Complex command structure
- Multiple command executions required
- Error handling can be difficult

**Suitable Use Cases:**
- Part of automation scripts
- CI/CD pipeline integration
- Environments requiring fine-grained control

### Terraform

**Advantages:**
- Infrastructure as Code (IaC)
- State management and change tracking
- Integration with various AWS services
- Modularization and reusability

**Disadvantages:**
- Has a learning curve
- Initial setup takes time
- State needs protected storage, locking and recovery; a local backend does not itself require extra infrastructure

**Suitable Use Cases:**
- Large-scale production environments
- Multi-environment management (development, staging, production)
- Complex infrastructure requirements

### AWS CDK

**Advantages:**
- Use familiar programming languages (TypeScript, Python, etc.)
- High level of abstraction
- Code reuse and modularization
- Tight integration with AWS services

**Disadvantages:**
- Has a learning curve
- Debugging can be complex
- Construct/version coverage varies; review synthesized CloudFormation and custom-resource behavior

**Suitable Use Cases:**
- Developer-centric environments
- Complex application infrastructure
- Integration with existing application code

## EKS Cluster Creation Best Practices

### Networking

1. **VPC Design**
   - Deploy subnets in at least 2 availability zones
   - Choose public/private placement from actual ingress/egress requirements; private-only designs can use service endpoints and private connectivity
   - Plan usable addresses, CNI warm/prefix pools and upgrade headroom; distinguish subnet space from node ENI/maxPods limits
   - Use the selected controller’s subnet discovery tags/configuration; tags do not establish routes or security boundaries

2. **Security Group Configuration**
   - Apply the principle of least privilege
   - Permit actual API, kubelet, DNS, webhook and application paths; kubelet uses TCP 10250, not an arbitrary broad ephemeral-port range
   - Restrict source IPs
   - Utilize security group references

3. **Network Policies**
   - Choose a supported policy engine: native VPC CNI policy or an appropriate Calico/Cilium design; do not enable conflicting engines
   - Restrict pod-to-pod communication
   - Verify namespace ingress/egress restrictions and DNS with positive/negative tests; matching Kubernetes NetworkPolicy allows are additive

### Security

1. **IAM Roles and Policies**
   - Apply the principle of least privilege
   - Use EKS Pod Identity or IRSA according to compute, agent/SDK and trust requirements; scope application permissions
   - Configure fine-grained permission policies

2. **Encryption**
   - Enable EBS volume encryption
   - Verify EKS default API-data envelope encryption (KMSv2 for 1.28+) and whether a customer-managed KMS key is required; base64 is not encryption
   - Encrypt data in transit (TLS)

3. **Authentication and Authorization**
   - Use EKS IAM authentication and access entries/access policies as appropriate; a separate client aws-iam-authenticator binary is not inherently required when using AWS CLI tokens
   - Review Kubernetes RBAC and EKS access-policy grants together; their allowed permissions are additive
   - Separate identities and namespaces, with RBAC, Pod Security and network controls; namespaces alone are not complete tenant isolation

### Scalability and Availability

1. **Node Group Configuration**
   - Deploy nodes across multiple availability zones
   - Identify the compute owner: managed/self-managed node groups, Karpenter, Auto Mode or Fargate; do not assume every mode is an operator-managed ASG
   - Utilize various instance types (including Spot instances)

2. **Cluster Autoscaler**
   - Use a compatible Cluster Autoscaler/Karpenter release where needed; Auto Mode manages its own capacity. Avoid competing owners for the same pool
   - Distinguish workload replica scaling from node provisioning; validate requests, unschedulable Pods and capacity constraints
   - Tune disruption/consolidation budgets and timing through the chosen controller; test application drain and recovery

3. **High Availability Configuration**
   - Utilize multiple availability zones
   - Use PodDisruptionBudget for applicable voluntary evictions; it does not prevent node failures or every forced disruption
   - Set replica counts, topology spread, readiness and capacity for the intended failure scenarios

### Monitoring and Logging

1. **Control Plane Logging**
   - Consider all five control-plane log types (api, audit, authenticator, controllerManager, scheduler) with retention, access and cost controls
   - Integrate with CloudWatch Logs

2. **Node and Pod Monitoring**
   - Choose the required CloudWatch Container Insights/add-on signals and supported compute configuration
   - Use Prometheus/Grafana or the existing monitoring platform intentionally; avoid duplicate collection and unreviewed automatic instrumentation
   - Configure custom metrics

3. **Alerts and Notifications**
   - Configure CloudWatch alarms
   - Set up authorized notification destinations and confirm delivery/ownership; do not assume a subscription is confirmed
   - Configure notifications for critical events

### Cost Optimization

1. **Instance Type Selection**
   - Choose instance types appropriate for workloads
   - Use Spot for interruption-tolerant workloads with tested capacity/failure handling
   - Consider Graviton after validating application, image, agent and add-on architecture compatibility

2. **Auto Scaling**
   - Configure automatic scaling based on demand
   - Optimize scale-down policies
   - Consider scheduled scaling

3. **Resource Requests and Limits**
   - Set appropriate CPU and memory requests
   - Set limits according to workload behavior; account for memory OOM and CPU throttling rather than treating all limits as free protection
   - Set resource quotas and limit ranges

4. **Fargate Utilization**
   - Use Fargate only where its scheduling, networking, storage and privilege restrictions fit the workload
   - Optimize Fargate profiles
   - Evaluate cost vs. performance

## Next Steps

After successfully creating an EKS cluster, consider the following steps:

1. **Establish Cluster Upgrade Strategy**
   - Plan against the EKS support catalog and exact add-on/client/node compatibility, not only upstream Kubernetes releases
   - Compare in-place and replacement-cluster strategies; current EKS control-plane rollback is conditional and does not restore application data
   - Automate upgrade testing

2. **Disaster Recovery Planning**
   - Define RPO/RTO and back up application data, configuration and required keys; test consistency and restore, not just snapshot creation
   - Choose multi-Region recovery only with explicit replication, DNS/failover, IAM/KMS and cost assumptions
   - Test failure scenarios

3. **CI/CD Pipeline Integration**
   - Implement GitOps workflows
   - Build automated deployment pipelines
   - Automate testing and validation

4. **Additional Service Integration**
   - AWS Load Balancer Controller where the selected compute/ingress path requires it; avoid duplicating Auto Mode-managed controllers
   - ExternalDNS with scoped DNS ownership and IAM permissions
   - cert-manager where Kubernetes certificate issuance is required; ALB ACM certificate management is a separate path
   - EBS/EFS storage according to compute support and provisioning owner; Auto Mode EBS and Fargate storage paths differ from ordinary EC2 add-ons

5. **Security Hardening**
   - Implement vulnerability scanning
   - Compliance monitoring
   - Automate security policies

Creating an EKS cluster is just the beginning of your Kubernetes journey. It is important to maintain a stable and efficient Kubernetes environment through continuous management, monitoring, and optimization.


## Verification References

- [EKS networking requirements](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [Private EKS clusters](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)
- [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [API-data envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)
- [Access policy permissions](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Conditional cluster rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

Implementation details and locally checked examples are in [creation Part 4](02-eks-cluster-creation-part4.md), [Part 5](02-eks-cluster-creation-part5.md) and [networking Part 2](03-eks-networking-part2.md). Production readiness requires the corresponding environment and failure/restore tests.
