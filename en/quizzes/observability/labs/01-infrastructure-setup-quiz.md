# Observability Lab Part 1: Infrastructure Setup Quiz

> **Last Updated**: February 22, 2026

Test your understanding of the infrastructure setup concepts covered in the Observability End-to-End Lab Part 1.

---

1. What is the primary role difference between the Managed Cluster and Service Cluster in a multi-cluster EKS architecture?
   - A) The Managed Cluster runs application workloads while the Service Cluster handles networking only
   - B) The Managed Cluster hosts observability and platform tools while the Service Cluster runs application workloads
   - C) The Service Cluster manages all clusters while the Managed Cluster is for testing
   - D) There is no functional difference; they are interchangeable

<details>
<summary>Show Answer</summary>

**Answer: B) The Managed Cluster hosts observability and platform tools while the Service Cluster runs application workloads**

**Explanation:**
In a multi-cluster architecture, the Managed Cluster (often called the management or platform cluster) hosts shared services like observability stacks, GitOps tools (ArgoCD), and platform components. The Service Cluster(s) run the actual application workloads. This separation provides better resource isolation, security boundaries, and allows independent scaling of platform services versus application workloads.

</details>

---

2. Why is IRSA (IAM Roles for Service Accounts) preferred over using IAM instance profiles for EKS workloads?
   - A) IRSA is faster to configure than instance profiles
   - B) IRSA provides pod-level IAM permissions following the principle of least privilege
   - C) Instance profiles are deprecated in AWS
   - D) IRSA allows unlimited IAM policies per pod

<details>
<summary>Show Answer</summary>

**Answer: B) IRSA provides pod-level IAM permissions following the principle of least privilege**

**Explanation:**
IRSA (IAM Roles for Service Accounts) enables fine-grained, pod-level IAM permissions by associating IAM roles with Kubernetes service accounts. Unlike instance profiles that grant the same permissions to all pods on a node, IRSA follows the principle of least privilege by allowing each workload to have only the specific permissions it needs. This improves security posture and makes it easier to audit and manage permissions.

</details>

---

3. What is a key trade-off when choosing Terraform over eksctl for EKS cluster provisioning?
   - A) Terraform cannot create EKS clusters at all
   - B) Terraform provides better state management and infrastructure-as-code practices but has a steeper learning curve
   - C) eksctl is more suitable for production environments
   - D) Terraform only works with AWS GovCloud regions

<details>
<summary>Show Answer</summary>

**Answer: B) Terraform provides better state management and infrastructure-as-code practices but has a steeper learning curve**

**Explanation:**
Terraform offers robust state management, drift detection, dependency graphing, and works across multiple cloud providers using declarative HCL syntax. However, it requires learning HCL and understanding Terraform concepts. eksctl is purpose-built for EKS with simpler YAML configuration and faster cluster creation, but offers less flexibility for complex infrastructure management. Terraform is often preferred for production environments where infrastructure-as-code practices and state management are critical.

</details>

---

4. Why does Aurora PostgreSQL use a writer/reader instance configuration in a production observability setup?
   - A) To reduce licensing costs
   - B) To provide high availability and separate read-heavy observability queries from write operations
   - C) Aurora only supports this configuration
   - D) To enable cross-region replication exclusively

<details>
<summary>Show Answer</summary>

**Answer: B) To provide high availability and separate read-heavy observability queries from write operations**

**Explanation:**
Aurora PostgreSQL's writer/reader configuration separates write operations (metrics ingestion, log storage) from read operations (dashboard queries, alerting queries). Observability workloads are typically read-heavy, with constant dashboard refreshes and alert evaluations. Reader instances handle these queries without impacting write performance. This configuration also provides high availability—if the writer fails, a reader can be promoted automatically, minimizing downtime.

</details>

---

5. What are the essential components that must be configured when creating an Amazon Managed Service for Prometheus (AMP) workspace?
   - A) Only the workspace name is required
   - B) Workspace, IAM role with remote write permissions, and VPC endpoints for secure access
   - C) Only S3 bucket configuration for storage
   - D) Workspace and mandatory CloudWatch integration

<details>
<summary>Show Answer</summary>

**Answer: B) Workspace, IAM role with remote write permissions, and VPC endpoints for secure access**

**Explanation:**
When setting up AMP, you need to create a workspace (the logical container for your Prometheus data), configure an IAM role with `aps:RemoteWrite` permissions for data ingestion, and optionally set up VPC endpoints for private network access. The IAM role is used with IRSA to allow your collectors to authenticate and write metrics. VPC endpoints ensure traffic doesn't traverse the public internet, improving security and reducing latency.

</details>

---

6. What methods can be used to connect Amazon Managed Grafana (AMG) to data sources?
   - A) Only manual configuration through the Grafana UI
   - B) AWS data source configuration, Grafana API provisioning, or Terraform/CloudFormation
   - C) Only through AWS CLI commands
   - D) Data sources are automatically discovered without configuration

<details>
<summary>Show Answer</summary>

**Answer: B) AWS data source configuration, Grafana API provisioning, or Terraform/CloudFormation**

**Explanation:**
AMG supports multiple methods for data source configuration: AWS-native data source configuration (which handles authentication automatically for AWS services like AMP, CloudWatch, X-Ray), Grafana API-based provisioning for programmatic setup, and Infrastructure-as-Code tools like Terraform or CloudFormation. This flexibility allows teams to choose the approach that best fits their workflow, whether it's GitOps-driven automation or manual configuration during initial setup.

</details>

---

7. What settings are required when registering a Service Cluster with ArgoCD in a multi-cluster setup?
   - A) Only the cluster endpoint URL
   - B) Cluster endpoint, authentication credentials (service account token or IAM), and cluster name/label
   - C) Only the kubeconfig file path
   - D) Cluster registration is automatic once both clusters are in the same VPC

<details>
<summary>Show Answer</summary>

**Answer: B) Cluster endpoint, authentication credentials (service account token or IAM), and cluster name/label**

**Explanation:**
Registering an external cluster with ArgoCD requires the cluster's API server endpoint, authentication credentials (either a service account token with appropriate RBAC permissions or IAM-based authentication for EKS), and metadata like cluster name and labels. The cluster name and labels are used in ApplicationSets for targeting deployments. For EKS, IAM-based authentication via IRSA is recommended as it avoids managing long-lived tokens.

</details>

---

8. How should Amazon OpenSearch Service domains be integrated with EKS for log storage?
   - A) OpenSearch cannot be used with EKS
   - B) Using VPC endpoints, fine-grained access control, and IRSA-based authentication for log shippers
   - C) Only through public endpoints with IP whitelisting
   - D) OpenSearch integration requires CloudWatch as an intermediary

<details>
<summary>Show Answer</summary>

**Answer: B) Using VPC endpoints, fine-grained access control, and IRSA-based authentication for log shippers**

**Explanation:**
For secure OpenSearch integration with EKS, deploy OpenSearch in VPC mode with VPC endpoints for private access. Enable fine-grained access control to manage index-level permissions. Configure log shippers (like FluentBit or Grafana Alloy) with IRSA to authenticate using IAM roles. This setup ensures logs are transmitted securely within the VPC, access is controlled at the index level, and authentication follows AWS security best practices.

</details>

---

9. What is the role of the S3 DAG bucket in an Amazon MWAA (Managed Workflows for Apache Airflow) environment?
   - A) It stores Airflow execution logs only
   - B) It stores DAG files, plugins, and requirements that MWAA loads to define and execute workflows
   - C) It serves as a backup for the MWAA database
   - D) It provides temporary storage for task outputs

<details>
<summary>Show Answer</summary>

**Answer: B) It stores DAG files, plugins, and requirements that MWAA loads to define and execute workflows**

**Explanation:**
The S3 DAG bucket is the source of truth for MWAA workflow definitions. It stores DAG (Directed Acyclic Graph) Python files that define workflows, custom plugins for extending Airflow functionality, and requirements.txt for additional Python dependencies. MWAA continuously syncs this bucket, automatically detecting and loading new or updated DAGs. This S3-based approach enables GitOps workflows where DAG changes are deployed through CI/CD pipelines.

</details>

---

10. Why is Argo Rollouts installed on the Service Cluster rather than the Managed Cluster?
    - A) Argo Rollouts cannot communicate across clusters
    - B) Rollouts controllers need direct access to the workloads they manage for canary/blue-green deployments
    - C) It reduces licensing costs to install on fewer clusters
    - D) The Managed Cluster doesn't support CRD installation

<details>
<summary>Show Answer</summary>

**Answer: B) Rollouts controllers need direct access to the workloads they manage for canary/blue-green deployments**

**Explanation:**
Argo Rollouts controllers manage the progressive delivery of applications through canary, blue-green, or other deployment strategies. They need direct access to modify ReplicaSets, Services, and other resources in the cluster where workloads run. While ArgoCD can deploy from a central location, Rollouts controllers actively manage traffic shifting and pod scaling during deployments, requiring them to run alongside the workloads they control. This is why Rollouts is installed on each Service Cluster.

</details>
