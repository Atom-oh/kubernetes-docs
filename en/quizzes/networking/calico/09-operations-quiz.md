# Operations Quiz

> **Related Document**: [Operations](../../../networking/calico/09-operations.md)
> **Last Updated**: September 12, 2026

## Quiz

1. Which statement correctly describes Calico installation ownership?
   - A) Install manifest and Helm operators together for redundancy
   - B) Choose an operator/Helm or direct-manifest owner that matches the platform
   - C) Enabling BPF is required for every installation
   - D) A fresh operator manifest includes every Calico CRD automatically

<details>
<summary>Show Answer</summary>

**Answer: B) Choose an operator/Helm or direct-manifest owner that matches the platform**

**Explanation:**
The Helm chart installs the Tigera Operator. Use one owner, pin the version, manage matching CRDs, and choose the actual networking profile. The example is full Calico CNI on self-managed Linux; EKS VPC CNI policy-only is a different configuration.

</details>

2. What does `calicoctl node status` inspect?
   - A) Every node in the kubeconfig context
   - B) The local node’s BGP status with the required node access
   - C) Every application’s HTTP readiness
   - D) All IPAM allocation leaks

<details>
<summary>Show Answer</summary>

**Answer: B) The local node’s BGP status with the required node access**

**Explanation:**
It is a local BGP diagnostic, not a cluster-wide readiness probe. BGP-disabled profiles do not need a BGP success result. Select the affected node and inspect its actual BIRD socket where appropriate.

</details>

3. What does `calicoctl ipam show --show-blocks` provide?
   - A) Calico IPAM block utilization, with node affinity inspected separately
   - B) An automatic safe release of empty blocks
   - C) All VPC CNI ENI allocations
   - D) A transactional datastore backup

<details>
<summary>Show Answer</summary>

**Answer: A) Calico IPAM block utilization, with node affinity inspected separately**

**Explanation:**
The command reports IP block/pool use. Use BlockAffinity for the block-to-node relationship. It applies to Calico IPAM; inspect the actual allocator for VPC CNI or host-local.

</details>

4. What is the type of `felix_int_dataplane_apply_time_seconds` in the reviewed release?
   - A) Counter of denied packets
   - B) Histogram with mandatory _bucket series
   - C) Summary with quantiles, _sum and _count
   - D) Gauge of allocated IP blocks

<details>
<summary>Show Answer</summary>

**Answer: C) Summary with quantiles, _sum and _count**

**Explanation:**
This is a Summary of incremental dataplane apply time. A local quantile is not a cluster-wide p99. Use sum/count rates for a mean while observations exist; do not invent histogram buckets.

</details>

5. Which statement about Typha metrics ports is correct?
   - A) The binary defaults to 9091; the guide explicitly configures operator Typha metrics on 9093
   - B) Every Typha installation uses 9093 automatically
   - C) Typha always shares kube-controllers port 9094
   - D) Metrics are enabled merely by creating a Service

<details>
<summary>Show Answer</summary>

**Answer: A) The binary defaults to 9091; the guide explicitly configures operator Typha metrics on 9093**

**Explanation:**
Typha metrics are disabled by default. The operator’s typhaMetricsPort enables/configures reporting and its Service. A ServiceMonitor must select the matching Service port and be selected by Prometheus.

</details>

6. What should you check when a Pod has no IP?
   - A) Immediately release an address and restart every Calico agent
   - B) Scheduling/events, the selected node, and the actual CNI/IPAM allocator
   - C) Only DNS records
   - D) Whether all BGP sessions have the same ASN

<details>
<summary>Show Answer</summary>

**Answer: B) Scheduling/events, the selected node, and the actual CNI/IPAM allocator**

**Explanation:**
A Pending Pod may not be scheduled yet. For allocation failures, inspect kubelet/CNI and allocator evidence, eligible pools and capacity/affinity constraints. Felix process logs are not the source of every Pod allocation error.

</details>

7. What belongs in BGP troubleshooting?
   - A) Only a successful ping
   - B) The affected node’s session state, source/peer addresses and ASNs, TCP 179, authentication/TTL and filters
   - C) Randomly changing every ASN until a session opens
   - D) Reading the first Calico Pod in the cluster regardless of node

<details>
<summary>Show Answer</summary>

**Answer: B) The affected node’s session state, source/peer addresses and ASNs, TCP 179, authentication/TTL and filters**

**Explanation:**
A TCP connection does not prove BGP Established or prefix acceptance. Check the expected routes and correct IPv4/IPv6 BIRD socket. Use these checks only when the chosen networking profile enables BGP.

</details>

8. Which statement about an apparent policy failure is correct?
   - A) kube-proxy and Service translation can never affect the investigation
   - B) Pod annotations list every effective policy decision
   - C) Felix Debug logs are automatically per-packet deny logs
   - D) Check endpoint identity, selectors, direction, tier/order, existing flows and the actual Service/dataplane path

<details>
<summary>Show Answer</summary>

**Answer: D) Check endpoint identity, selectors, direction, tier/order, existing flows and the actual Service/dataplane path**

**Explanation:**
Calico enforces policy, while Service translation, endpoint selection and source-address changes can affect which traffic is evaluated. Inspect the complete path and test both allowed and denied cases instead of assuming a component is irrelevant.

</details>

9. What is required for a Calico upgrade?
   - A) Patch the managed DaemonSet to remove all canary agents
   - B) Follow the installation/version-specific CRD, operator and stored-data migration procedure
   - C) Always set Installation.spec.version before starting
   - D) Assume Helm rollback reverses all CRD and data changes

<details>
<summary>Show Answer</summary>

**Answer: B) Follow the installation/version-specific CRD, operator and stored-data migration procedure**

**Explanation:**
Use compatible source/target versions, update the existing installation owner and manage CRDs before new fields are needed. Test the rollout and recovery. An older operator or raw YAML export is not a guaranteed downgrade.

</details>

10. How should default-deny policy be introduced?
   - A) Validate a selected namespace and explicitly permit its required dependencies before expanding scope
   - B) Immediately apply an empty all-endpoint GlobalNetworkPolicy everywhere
   - C) Infer API server endpoints from an invented Pod label
   - D) Use endpoint count zero as proof that denial works

<details>
<summary>Show Answer</summary>

**Answer: A) Validate a selected namespace and explicitly permit its required dependencies before expanding scope**

**Explanation:**
DNS, API, identity, monitoring and application paths need explicit review. Test negative and positive cases, preserve a recovery path, and account for workload versus host endpoint policy.

</details>

11. Which description matches current OSS flow observability?
   - A) FlowLogsFileReporter is the required OSS API field
   - B) Every flow log is exactly one packet record
   - C) Operator/Helm can deploy Goldmane and Whisker; the current flow-log guide marks the feature tech preview
   - D) Flow logs and Felix process logs are identical

<details>
<summary>Show Answer</summary>

**Answer: C) Operator/Helm can deploy Goldmane and Whisker; the current flow-log guide marks the feature tech preview**

**Explanation:**
Goldmane supplies aggregated flow data to Whisker. It is available in OSS with the documented installation prerequisites; old file/DNS logger fields are not a valid replacement. Protect sensitive flow data and assess the preview status.

</details>

12. How can calicoctl be configured for Kubernetes datastore access?
   - A) Set CNI_PATH only
   - B) Use DATASTORE_TYPE=kubernetes with appropriate kubeconfig access, or an explicit supported config file
   - C) An arbitrary ~/.config path is always auto-discovered
   - D) A Calico kubeconfig provides access to EKS-managed etcd

<details>
<summary>Show Answer</summary>

**Answer: B) Use DATASTORE_TYPE=kubernetes with appropriate kubeconfig access, or an explicit supported config file**

**Explanation:**
The guide shows a typical environment configuration. An explicit --config file is another supported path. Select the intended cluster and RBAC; direct etcdv3 access is a separate deployment configuration.

</details>
