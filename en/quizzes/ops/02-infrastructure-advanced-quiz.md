# Infrastructure Advanced Quiz

> **Related Document**: [Infrastructure Advanced](../../ops/02-infrastructure-advanced.md)

## Multiple Choice Questions

### 1. What is the primary purpose of NLB weighted target groups in a blue/green deployment?

- A) To reduce costs by using fewer load balancers
- B) To control traffic distribution between cluster versions
- C) To improve SSL termination performance
- D) To eliminate the need for health checks

<details>
<summary>Show Answer</summary>

**Answer: B) To control traffic distribution between cluster versions**

**Explanation:**
NLB weighted target groups allow gradual traffic shifting between blue (current) and green (new) clusters. By adjusting weights (e.g., 90:10, 50:50, 0:100), operators can perform controlled rollouts and quickly rollback if issues are detected.

</details>

### 2. In a single-zone EKS cluster strategy, why might you deploy data nodes to only one Availability Zone?

- A) To reduce cross-AZ data transfer costs
- B) To simplify DNS configuration
- C) To avoid using multiple subnets
- D) To eliminate the need for persistent volumes

<details>
<summary>Show Answer</summary>

**Answer: A) To reduce cross-AZ data transfer costs**

**Explanation:**
Cross-AZ data transfer incurs costs in AWS. For data-intensive workloads with local storage (like databases), keeping all replicas in a single AZ eliminates these costs while relying on application-level replication for durability.

</details>

### 3. What Kubernetes feature ensures pods are distributed across different zones or nodes?

- A) PodAffinity
- B) TopologySpreadConstraints
- C) ResourceQuota
- D) LimitRange

<details>
<summary>Show Answer</summary>

**Answer: B) TopologySpreadConstraints**

**Explanation:**
TopologySpreadConstraints control how pods are spread across topology domains (zones, nodes, regions). They ensure even distribution for high availability and can be configured with `maxSkew`, `topologyKey`, and `whenUnsatisfiable` parameters.

</details>

### 4. How does Route53 weighted routing differ from NLB weighted target groups?

- A) Route53 works at DNS level, NLB works at connection level
- B) Route53 only supports equal weights
- C) NLB doesn't support health checks
- D) Route53 requires VPC peering

<details>
<summary>Show Answer</summary>

**Answer: A) Route53 works at DNS level, NLB works at connection level**

**Explanation:**
Route53 weighted routing distributes traffic at DNS resolution time, while NLB weighted target groups distribute at the connection level. DNS-based routing has TTL considerations, while NLB provides more immediate traffic shifting.

</details>

### 5. What is the recommended `maxSkew` value for TopologySpreadConstraints in a 3-AZ deployment?

- A) 0
- B) 1
- C) 3
- D) 10

<details>
<summary>Show Answer</summary>

**Answer: B) 1**

**Explanation:**
A `maxSkew` of 1 ensures pods are evenly distributed with at most one pod difference between topology domains. This provides good balance while still allowing scheduling flexibility when nodes have resource constraints.

</details>

### 6. In blue/green cluster architecture, what should be shared between clusters?

- A) Worker nodes
- B) External DNS and load balancer
- C) etcd storage
- D) Kubernetes API server

<details>
<summary>Show Answer</summary>

**Answer: B) External DNS and load balancer**

**Explanation:**
Blue/green clusters are separate EKS clusters that share external infrastructure like DNS records and load balancers. This allows traffic to be shifted between clusters without changing client-facing endpoints.

</details>

### 7. What happens when `whenUnsatisfiable: DoNotSchedule` is set in TopologySpreadConstraints?

- A) Pods are scheduled anywhere regardless of constraints
- B) Pods remain pending if constraints cannot be satisfied
- C) Pods are automatically deleted
- D) The constraint is ignored

<details>
<summary>Show Answer</summary>

**Answer: B) Pods remain pending if constraints cannot be satisfied**

**Explanation:**
`DoNotSchedule` prevents pod scheduling when the spread constraint would be violated. This ensures strict adherence to topology requirements but may result in pending pods if cluster topology doesn't support the constraint.

</details>

### 8. For automated failover between blue/green clusters, what AWS service can be used with health checks?

- A) AWS Config
- B) Route53 health checks with failover routing
- C) AWS Inspector
- D) AWS Trusted Advisor

<details>
<summary>Show Answer</summary>

**Answer: B) Route53 health checks with failover routing**

**Explanation:**
Route53 health checks continuously monitor endpoint availability and can automatically switch traffic to a healthy cluster using failover routing policy. This enables automated disaster recovery without manual intervention.

</details>

### 9. What is a key consideration when using NLB cross-zone load balancing?

- A) It's always free
- B) It may incur additional data transfer charges
- C) It requires VPC peering
- D) It only works with TCP protocol

<details>
<summary>Show Answer</summary>

**Answer: B) It may incur additional data transfer charges**

**Explanation:**
When cross-zone load balancing is enabled, NLB distributes traffic evenly across all registered targets in all enabled AZs, which can result in cross-AZ data transfer charges. Consider this cost when architecting multi-AZ deployments.

</details>

### 10. In a zonal cluster deployment (a-zone blue, c-zone green), what is the primary benefit?

- A) Reduced networking complexity
- B) Failure isolation and independent upgrade paths
- C) Lower compute costs
- D) Automatic data replication

<details>
<summary>Show Answer</summary>

**Answer: B) Failure isolation and independent upgrade paths**

**Explanation:**
Zonal clusters provide failure domain isolation - an issue in one zone doesn't affect the other cluster. This also enables independent upgrade testing and gradual rollouts, reducing risk during Kubernetes version upgrades.

</details>
