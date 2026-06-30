# vCluster Quiz

1. How is vCluster superior to traditional Namespace-based multi-tenancy?
   - A) vCluster creates additional physical clusters
   - B) Provides each tenant with a full Kubernetes API while sharing host cluster resources
   - C) vCluster completely isolates the network
   - D) vCluster requires dedicated nodes

<details>
<summary>Show Answer</summary>

**Answer: B) Provides each tenant with a full Kubernetes API while sharing host cluster resources**

**Explanation:**
vCluster provides each tenant with an independent Kubernetes API (CRD installation, RBAC management, Namespace creation, etc.) through a virtual control plane. Actual workloads run on the host cluster, providing strong isolation without the cost of additional physical clusters.

</details>

---

2. What is the core role of vCluster's Syncer component?
   - A) Manage virtual cluster DNS
   - B) Synchronize virtual cluster resources to the host cluster and reflect host state back
   - C) Connect networks between virtual clusters
   - D) Collect virtual cluster logs

<details>
<summary>Show Answer</summary>

**Answer: B) Synchronize virtual cluster resources to the host cluster and reflect host state back**

**Explanation:**
The Syncer is vCluster's core component that translates resources created in the virtual cluster (Pods, Services, ConfigMaps, etc.) into actual resources on the host cluster. It also syncs host information (Nodes, StorageClasses, etc.) back to the virtual cluster, performing bidirectional resource management.

</details>

---

3. What is the advantage of using vCluster for per-PR preview environments?
   - A) Deploy code to production without PR merge
   - B) Quickly create/delete isolated Kubernetes environments per PR for integration testing
   - C) Grant cluster admin privileges to PR reviewers
   - D) Reduce CI pipeline execution time

<details>
<summary>Show Answer</summary>

**Answer: B) Quickly create/delete isolated Kubernetes environments per PR for integration testing**

**Explanation:**
vCluster can be created in under 30 seconds, allowing CI/CD pipelines to provision isolated Kubernetes environments per PR. When PRs are merged or closed, the vCluster is deleted to reclaim resources, enabling integration testing of each PR's changes in an independent environment.

</details>

---

4. What is the purpose of vCluster's Sleep Mode feature?
   - A) Enhance virtual cluster security
   - B) Release resources of unused virtual clusters to reduce costs
   - C) Back up virtual cluster data
   - D) Optimize virtual cluster performance

<details>
<summary>Show Answer</summary>

**Answer: B) Release resources of unused virtual clusters to reduce costs**

**Explanation:**
Sleep Mode automatically stops workloads in vClusters that have been inactive for a specified period. When an API request comes in, the vCluster automatically wakes up. This significantly reduces costs for dev/test vClusters that are unused during nights and weekends.

</details>

---

5. How do you use the host cluster's StorageClass in a virtual cluster?
   - A) Recreate the StorageClass in the virtual cluster
   - B) Use syncFromHost settings to synchronize the host's StorageClass to the virtual cluster
   - C) Manually mount PVs
   - D) Install CSI drivers separately in the virtual cluster

<details>
<summary>Show Answer</summary>

**Answer: B) Use syncFromHost settings to synchronize the host's StorageClass to the virtual cluster**

**Explanation:**
vCluster's `syncFromHost` configuration syncs host cluster resources like StorageClasses, IngressClasses, and Nodes so they're visible in the virtual cluster. PVCs in the virtual cluster use the host cluster's StorageClasses to provision actual PVs.

</details>

---

6. How does the developer self-service workflow work in Backstage + vCluster integration?
   - A) Developers create vClusters directly with kubectl
   - B) Backstage Template generates vCluster request → pushes to GitOps repo → ArgoCD syncs to provision vCluster
   - C) Backstage directly calls the Kubernetes API to create vClusters
   - D) Admins manually create vClusters and assign them to developers

<details>
<summary>Show Answer</summary>

**Answer: B) Backstage Template generates vCluster request → pushes to GitOps repo → ArgoCD syncs to provision vCluster**

**Explanation:**
When a developer enters parameters (environment name, resource size, etc.) in a Backstage Template, the Template generates vCluster Helm Release manifests and pushes them to the GitOps repository. ArgoCD detects the change and syncs it to the cluster, automatically provisioning the vCluster.

</details>

---

7. What is the role of NetworkPolicy in vCluster security isolation?
   - A) Limit CPU usage between virtual clusters
   - B) Prevent virtual cluster Pods from accessing other vCluster Pods or host cluster resources via network isolation
   - C) Encrypt Ingress traffic for virtual clusters
   - D) Filter DNS queries

<details>
<summary>Show Answer</summary>

**Answer: B) Prevent virtual cluster Pods from accessing other vCluster Pods or host cluster resources via network isolation**

**Explanation:**
Since vCluster Pods run on the host cluster, without NetworkPolicies they can network-access Pods from other vClusters. Applying NetworkPolicies to each vCluster's namespace to allow only intra-namespace communication and block external access implements strong network isolation.

</details>

---

8. When should you choose vCluster over a physical cluster?
   - A) When complete hardware isolation is required
   - B) When fast provisioning, cost efficiency, and CRD isolation are needed but full node isolation is not
   - C) When regulatory requirements mandate separate AWS accounts
   - D) When running GPU workloads

<details>
<summary>Show Answer</summary>

**Answer: B) When fast provisioning, cost efficiency, and CRD isolation are needed but full node isolation is not**

**Explanation:**
vCluster offers sub-30-second creation, cost efficiency through host cluster resource sharing, and CRD/RBAC/Namespace isolation. It's ideal for dev/test environments, CI/CD ephemeral environments, and training environments. Physical clusters are more appropriate for production workloads requiring regulatory compliance, full hardware isolation, or dedicated network isolation.

</details>
