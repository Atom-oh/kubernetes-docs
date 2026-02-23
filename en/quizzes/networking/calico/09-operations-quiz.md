# Operations Quiz

> **Related Document**: [Operations](../../../networking/calico/09-operations.md)
> **Last Updated**: February 22, 2026

## Quiz

1. What are the three main installation methods for Calico?
   - A) Docker, Podman, containerd
   - B) Manifest-based (kubectl), Operator-based (Tigera), Helm
   - C) CLI, GUI, API
   - D) Binary, Package manager, Source compilation

<details>
<summary>Show Answer</summary>

**Answer: B) Manifest-based (kubectl), Operator-based (Tigera), Helm**

**Explanation:**
Calico can be installed using: 1) Manifest-based installation with kubectl apply on YAML manifests, 2) Operator-based installation using the Tigera Operator (recommended), or 3) Helm charts for customizable deployments. The Operator method is generally recommended for production as it manages the Calico lifecycle.

</details>

2. Which calicoctl command shows the status of Calico nodes including BGP peer status?
   - A) calicoctl get nodes
   - B) calicoctl node status
   - C) calicoctl describe node
   - D) calicoctl show peers

<details>
<summary>Show Answer</summary>

**Answer: B) calicoctl node status**

**Explanation:**
The `calicoctl node status` command displays the status of the Calico node including BGP peering information, showing which peers are established, their state, and any connection issues. This is essential for troubleshooting BGP routing problems.

</details>

3. What command displays IPAM block allocation across nodes?
   - A) calicoctl ipam show --show-blocks
   - B) calicoctl get ipamblocks
   - C) kubectl get ipamblocks -o wide
   - D) calicoctl describe ipam

<details>
<summary>Show Answer</summary>

**Answer: A) calicoctl ipam show --show-blocks**

**Explanation:**
The `calicoctl ipam show --show-blocks` command displays detailed IPAM information including which IP blocks are allocated to which nodes, the utilization of each block, and overall IP pool statistics. This is crucial for diagnosing IP allocation issues.

</details>

4. Which Prometheus metrics endpoint exposes Felix performance and policy statistics?
   - A) :9090/metrics
   - B) :9091/metrics
   - C) :9094/metrics
   - D) :8080/metrics

<details>
<summary>Show Answer</summary>

**Answer: B) :9091/metrics**

**Explanation:**
Felix exposes Prometheus metrics on port 9091 by default. These metrics include policy rule counts, dataplane programming latency, iptables/eBPF statistics, and error counts. This must be enabled in FelixConfiguration with `prometheusMetricsEnabled: true`.

</details>

5. What port does Typha use for its Prometheus metrics endpoint?
   - A) :9091/metrics
   - B) :9093/metrics
   - C) :9094/metrics
   - D) :9095/metrics

<details>
<summary>Show Answer</summary>

**Answer: B) :9093/metrics**

**Explanation:**
Typha exposes Prometheus metrics on port 9093 by default. Typha metrics include connection counts to Felix instances, datastore sync latency, and cache statistics. Monitoring Typha is important for understanding datastore fan-out performance in large clusters.

</details>

6. A pod cannot get an IP address. What is the first thing to check?
   - A) kube-proxy logs
   - B) IPPool availability and IPAM block allocation
   - C) DNS configuration
   - D) Node CPU usage

<details>
<summary>Show Answer</summary>

**Answer: B) IPPool availability and IPAM block allocation**

**Explanation:**
When a pod fails to get an IP, first check if the IPPool has available addresses using `calicoctl ipam show`. Verify that IPAM blocks can be allocated to the node and that the IPPool selector matches the node. Also check Felix logs for IPAM-related errors.

</details>

7. What should you verify when BGP peering between nodes fails to establish?
   - A) Pod DNS resolution
   - B) Network connectivity on BGP port (179), BGPConfiguration, and node selectors
   - C) Persistent volume bindings
   - D) Service account tokens

<details>
<summary>Show Answer</summary>

**Answer: B) Network connectivity on BGP port (179), BGPConfiguration, and node selectors**

**Explanation:**
For BGP peering issues, verify: 1) Network connectivity between nodes on TCP port 179, 2) BGPConfiguration and BGPPeer resources are correctly defined, 3) Node selectors match intended nodes, 4) Check `calicoctl node status` and BIRD logs for specific peering errors.

</details>

8. A network policy is applied but traffic is not being blocked. What is a likely cause?
   - A) The cluster is using too much memory
   - B) Policy selectors don't match target pods, or policy order/tier is incorrect
   - C) The nodes need to be rebooted
   - D) Kubernetes version is too old

<details>
<summary>Show Answer</summary>

**Answer: B) Policy selectors don't match target pods, or policy order/tier is incorrect**

**Explanation:**
When policies don't work as expected, verify: 1) Pod selectors correctly match target pods (check labels), 2) Namespace selectors are correct, 3) Policy tier ordering (higher priority tiers evaluated first), 4) No conflicting Allow policies earlier in evaluation order. Use `calicoctl get policy` to review applied policies.

</details>

9. What is the recommended procedure for upgrading Calico versions?
   - A) Delete all resources and reinstall
   - B) Upgrade in place following version-specific migration guides
   - C) Create a new cluster and migrate workloads
   - D) Calico upgrades automatically with Kubernetes

<details>
<summary>Show Answer</summary>

**Answer: B) Upgrade in place following version-specific migration guides**

**Explanation:**
Calico upgrades should follow the official upgrade documentation for your installation method. This typically involves updating the Operator or manifests to the new version. Review version-specific migration notes as some upgrades require additional steps. Test in non-production first.

</details>

10. What is the default deny best practice for Calico network policies?
    - A) Never use deny policies
    - B) Apply default deny policies to namespaces, then explicitly allow required traffic
    - C) Only deny traffic from external sources
    - D) Deny all egress but allow all ingress

<details>
<summary>Show Answer</summary>

**Answer: B) Apply default deny policies to namespaces, then explicitly allow required traffic**

**Explanation:**
The security best practice is to apply a default deny policy that blocks all ingress (and optionally egress) traffic to pods in a namespace, then create specific policies to allow only required traffic flows. This implements the principle of least privilege for network access.

</details>

11. How do you configure Calico to export flow logs for network visibility?
   - A) Enable in kube-apiserver flags
   - B) Configure FlowLogsFileReporter or FlowLogsNetworkReporter in FelixConfiguration
   - C) Flow logs are always enabled by default
   - D) Install a separate flow log operator

<details>
<summary>Show Answer</summary>

**Answer: B) Configure FlowLogsFileReporter or FlowLogsNetworkReporter in FelixConfiguration**

**Explanation:**
Flow logs are configured through FelixConfiguration by enabling FlowLogsFileReporter (writes to files) or FlowLogsNetworkReporter (sends to a collector). Configure parameters like log interval, aggregation level, and which flows to capture. Note: Full flow log features require Calico Enterprise.

</details>

12. What environment variables must be set for calicoctl to connect to the datastore?
    - A) CALICO_HOST and CALICO_PORT
    - B) DATASTORE_TYPE and KUBECONFIG (or ETCD_ENDPOINTS for etcd datastore)
    - C) CALICO_API_SERVER and CALICO_TOKEN
    - D) CNI_PATH and CNI_CONFIG

<details>
<summary>Show Answer</summary>

**Answer: B) DATASTORE_TYPE and KUBECONFIG (or ETCD_ENDPOINTS for etcd datastore)**

**Explanation:**
For calicoctl to connect to the datastore, set `DATASTORE_TYPE=kubernetes` and ensure KUBECONFIG points to a valid kubeconfig file. For etcd datastore, set `DATASTORE_TYPE=etcdv3` along with `ETCD_ENDPOINTS` and optionally TLS-related variables for secure connections.

</details>
