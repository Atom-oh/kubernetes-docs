# Cluster Architecture Quiz

This quiz tests your understanding of Kubernetes cluster architecture, main components, communication paths, and high availability configurations.

## Multiple Choice Questions

1. Which of the following is NOT a core component of the Kubernetes control plane?
   - A) kube-apiserver
   - B) etcd
   - C) kube-proxy
   - D) kube-scheduler
   
<details>

<summary>Show Answer</summary>

**Answer: C) kube-proxy**

**Explanation:**
kube-proxy is a node component, not a control plane component. The core control plane components are kube-apiserver, etcd, kube-scheduler, kube-controller-manager, and cloud-controller-manager. kube-proxy runs on each node and maintains network rules and performs connection forwarding.
</details>

2. Which component in Kubernetes acts as the "source of truth" that stores all cluster data?
   - A) kube-apiserver
   - B) etcd
   - C) kube-controller-manager
   - D) kubelet
   
<details>

<summary>Show Answer</summary>

**Answer: B) etcd**

**Explanation:**
etcd is a consistent and highly available key-value store that stores all cluster data and acts as Kubernetes' "source of truth". All cluster state, configuration, and metadata are stored in etcd, and all other control plane components interact through kube-apiserver to read and write information from etcd.
</details>

3. Which of the following is NOT a Kubernetes node component?
   - A) kubelet
   - B) kube-proxy
   - C) Container runtime
   - D) kube-controller-manager
   
<details>

<summary>Show Answer</summary>

**Answer: D) kube-controller-manager**

**Explanation:**
kube-controller-manager is a control plane component, not a node component. Node components are kubelet, kube-proxy, and container runtime (containerd, CRI-O, etc.). kube-controller-manager runs on the control plane and executes various controller processes such as node controller and replication controller.
</details>

4. Which control plane component in Kubernetes selects nodes to run newly created pods?
   - A) kube-apiserver
   - B) kube-scheduler
   - C) kubelet
   - D) kube-controller-manager
   
<details>

<summary>Show Answer</summary>

**Answer: B) kube-scheduler**

**Explanation:**
kube-scheduler is the control plane component that selects nodes to run newly created pods. The scheduling process consists of filtering (identifying nodes that can run the pod) and scoring (assigning scores to suitable nodes), and finally assigns the pod to the optimal node. kube-scheduler considers resource requirements, hardware/software/policy constraints, affinity/anti-affinity specifications, data locality, and workload interference.
</details>

5. Which control plane component interacts with cloud provider APIs?
   - A) kube-apiserver
   - B) etcd
   - C) cloud-controller-manager
   - D) kubelet
   
<details>

<summary>Show Answer</summary>

**Answer: C) cloud-controller-manager**

**Explanation:**
cloud-controller-manager is a control plane component that contains cloud-specific control logic and interacts with cloud provider APIs. This allows separation between the Kubernetes core and cloud provider APIs. cloud-controller-manager runs cloud-specific controllers such as node controller, route controller, service controller, and volume controller.
</details>

6. What is the agent that runs on each node and manages the execution of containers within pods?
   - A) kube-proxy
   - B) kubelet
   - C) containerd
   - D) kube-scheduler
   
<details>

<summary>Show Answer</summary>

**Answer: B) kubelet**

**Explanation:**
kubelet is an agent that runs on each node and manages the execution of containers within pods. kubelet receives PodSpecs through various mechanisms and ensures containers run healthily according to those specs. Key functions include running containers according to PodSpecs, monitoring and reporting container status, managing container lifecycle, managing volume mounts, reporting node status, and performing container health checks.
</details>

7. Which node component in Kubernetes maintains network rules for service IPs and performs connection forwarding?
   - A) kubelet
   - B) kube-proxy
   - C) CNI plugin
   - D) containerd
   
<details>

<summary>Show Answer</summary>

**Answer: B) kube-proxy**

**Explanation:**
kube-proxy is a network proxy that runs on each node and is responsible for implementing the Kubernetes service concept. It maintains network rules on nodes and performs connection forwarding. Key functions include maintaining network rules for service IPs and ports, connection forwarding, implementing load balancing, and supporting service discovery. kube-proxy supports several operating modes including userspace mode, iptables mode, and IPVS mode.
</details>

8. What is the standard interface for running containers in Kubernetes?
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) CPI (Container Platform Interface)
   
<details>

<summary>Show Answer</summary>

**Answer: A) CRI (Container Runtime Interface)**

**Explanation:**
CRI (Container Runtime Interface) is the standard interface for running containers in Kubernetes. Through CRI, Kubernetes can support various container runtimes such as containerd and CRI-O. CRI defines APIs for communication between kubelet and container runtimes, enabling operations such as creating, starting, stopping, and deleting containers. CNI (Container Network Interface) is the interface for networking, and CSI (Container Storage Interface) is the interface for storage.
</details>

9. What interface is used to implement pod networking in Kubernetes clusters?
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) API (Application Programming Interface)
   
<details>

<summary>Show Answer</summary>

**Answer: B) CNI (Container Network Interface)**

**Explanation:**
CNI (Container Network Interface) is the standard interface for implementing pod networking in Kubernetes. CNI plugins are responsible for connecting network interfaces to pods and assigning IP addresses. Various CNI plugins exist, including Calico, Cilium, Flannel, and Weave Net, each with different features and performance characteristics. Through CNI, Kubernetes can support various networking solutions.
</details>

10. What provides a standard interface with storage systems in Kubernetes clusters?
    - A) CRI (Container Runtime Interface)
    - B) CNI (Container Network Interface)
    - C) CSI (Container Storage Interface)
    - D) CPI (Cloud Provider Interface)
    
<details>

<summary>Show Answer</summary>

**Answer: C) CSI (Container Storage Interface)**

**Explanation:**
CSI (Container Storage Interface) provides a standard interface between Kubernetes and storage systems. Through CSI, storage providers can develop their own storage drivers without modifying Kubernetes code. CSI defines standardized APIs for operations such as volume creation, deletion, mounting, and unmounting. Various CSI drivers exist, including AWS EBS CSI driver, Azure Disk CSI driver, and GCP PD CSI driver.
</details>

## Short Answer Questions

11. What is the name of the component in the Kubernetes control plane that runs multiple controller processes?

<details>

<summary>Show Answer</summary>

**Answer: kube-controller-manager**

**Explanation:**
kube-controller-manager is the control plane component that runs multiple controller processes. Each controller manages a specific aspect of the cluster. Major controllers include node controller, replication controller, endpoint controller, service account & token controller, job controller, cronjob controller, daemonset controller, statefulset controller, PV controller, namespace controller, and garbage collector.
</details>

12. What consensus algorithm does Kubernetes use to ensure consistency of etcd data?

<details>

<summary>Show Answer</summary>

**Answer: Raft**

**Explanation:**
etcd uses the Raft consensus algorithm to ensure strong consistency of data in distributed systems. Raft achieves consensus in distributed systems through leader election, log replication, and safety. etcd clusters are typically composed of 3 or 5 nodes, and the cluster can continue to operate as long as a majority (quorum) of nodes are functioning normally.
</details>

13. What is the default operating mode of kube-proxy in Kubernetes?

<details>

<summary>Show Answer</summary>

**Answer: iptables**

**Explanation:**
The default operating mode of kube-proxy is iptables mode. In this mode, kube-proxy uses Linux iptables to implement NAT and route traffic to service IPs to pods. Other operating modes include userspace mode (legacy) and IPVS mode (high performance). IPVS mode provides better performance for large clusters but requires the IPVS module in the Linux kernel.
</details>

14. What is the name of the configuration file for communicating with the API server in a Kubernetes cluster?

<details>

<summary>Show Answer</summary>

**Answer: kubeconfig**

**Explanation:**
kubeconfig is a configuration file for communicating with the Kubernetes API server. This file contains cluster information, authentication information (certificates, tokens, etc.), and contexts (combinations of clusters and users). The kubectl command uses the $HOME/.kube/config file by default, but a different file can be specified through the --kubeconfig flag or KUBECONFIG environment variable.
</details>

15. How many control plane nodes are generally recommended as the minimum for configuring a high availability cluster in Kubernetes?

<details>

<summary>Show Answer</summary>

**Answer: 3**

**Explanation:**
The generally recommended minimum number of control plane nodes for a high availability cluster in Kubernetes is 3. This is because etcd clusters operate on a majority (quorum) basis. With 3 nodes, the cluster can continue to operate even if 1 node fails (2 is the majority). With 5 nodes, the cluster can continue to operate even if 2 nodes fail (3 is the majority). Using an odd number of nodes is generally recommended.
</details>

## Hands-on Questions

16. Write a command to create a backup of the etcd database. The backup file should be saved to `/backup/etcd-snapshot-$(date +%Y%m%d).db`, the etcd endpoint is `https://127.0.0.1:2379`, and the certificate files are in the `/etc/kubernetes/pki/etcd/` directory.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d).db \
--endpoints=https://127.0.0.1:2379 \
--cacert=/etc/kubernetes/pki/etcd/ca.crt \
--cert=/etc/kubernetes/pki/etcd/server.crt \
--key=/etc/kubernetes/pki/etcd/server.key
```

**Explanation:**
This command sets the ETCDCTL_API environment variable to 3 to use the etcdctl v3 API and creates a snapshot of the etcd database with the snapshot save command. The --endpoints flag specifies the etcd server endpoint, and the --cacert, --cert, --key flags specify the certificate files needed for TLS authentication. The backup file is saved to the /backup directory with a name that includes the current date.
</details>

17. Write a kube-scheduler configuration file (YAML) that meets the following requirements:
    - Scheduler name: custom-scheduler
    - Leader election enabled
    - Scoring plugin: Set NodeResourcesBalancedAllocation weight to 2
    - Filtering plugin: Disable NodeUnschedulable

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true

profiles:
  - schedulerName: custom-scheduler
    plugins:
      score:
        enabled:
          - name: NodeResourcesBalancedAllocation
        disabled: []
      filter:
        disabled:
          - name: NodeUnschedulable
```

**Explanation:**
This YAML file defines a KubeSchedulerConfiguration object. leaderElection.leaderElect: true enables leader election, and the profiles section defines a scheduler profile named custom-scheduler. In the plugins section, the weight of NodeResourcesBalancedAllocation is set to 2 in the score plugins, and NodeUnschedulable is disabled in the filter plugins.
</details>

18. Write an etcd startup command for configuring a high availability etcd cluster that meets the following requirements:
    - Node name: etcd-1
    - Cluster name: etcd-cluster
    - Client URL: https://192.168.1.10:2379
    - Peer URL: https://192.168.1.10:2380
    - Initial cluster: etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380
    - Data directory: /var/lib/etcd
    - Certificate files are in the /etc/kubernetes/pki/etcd/ directory

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
etcd \
--name=etcd-1 \
--initial-advertise-peer-urls=https://192.168.1.10:2380 \
--listen-peer-urls=https://192.168.1.10:2380 \
--listen-client-urls=https://192.168.1.10:2379,https://127.0.0.1:2379 \
--advertise-client-urls=https://192.168.1.10:2379 \
--initial-cluster-token=etcd-cluster \
--initial-cluster=etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380 \
--initial-cluster-state=new \
--data-dir=/var/lib/etcd \
--cert-file=/etc/kubernetes/pki/etcd/server.crt \
--key-file=/etc/kubernetes/pki/etcd/server.key \
--trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt \
--peer-cert-file=/etc/kubernetes/pki/etcd/peer.crt \
--peer-key-file=/etc/kubernetes/pki/etcd/peer.key \
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
```

**Explanation:**
This command starts an etcd node named etcd-1. --initial-advertise-peer-urls and --listen-peer-urls specify URLs for peer communication, and --listen-client-urls and --advertise-client-urls specify URLs for client communication. --initial-cluster-token specifies a unique identifier for the cluster, and --initial-cluster lists all nodes in the cluster. --initial-cluster-state=new indicates that a new cluster is being created. --data-dir specifies the directory where etcd data will be stored. Finally, the certificate-related flags specify the certificate files for TLS communication.
</details>

## Advanced Questions

19. Design a high availability architecture for a Kubernetes cluster and explain the deployment methods for control plane components and etcd, load balancer configuration, and response measures for failure scenarios.

<details>

<summary>Show Answer</summary>

**Answer:**

**High Availability Kubernetes Cluster Architecture Design**

1. **Control Plane Component Deployment**:
  - Distribute at least 3 control plane nodes across multiple availability zones
  - Deploy kube-apiserver, kube-scheduler, kube-controller-manager on each node
  - Run kube-scheduler and kube-controller-manager in leader election mode (only one instance active at a time)
  - kube-apiserver is horizontally scalable (all instances active simultaneously)

2. **etcd Deployment Methods**:
  - Stacked topology: Deploy etcd together with control plane nodes
  - External topology: Deploy etcd on separate nodes (higher isolation and scalability)
  - Distribute at least 3 etcd nodes across multiple availability zones (5 recommended)
  - etcd cluster uses Raft consensus algorithm to ensure data consistency

3. **Load Balancer Configuration**:
  - Place load balancer in front of kube-apiserver
  - Load balancer can operate at L4 (TCP) or L7 (HTTP/HTTPS) level
  - Detect unhealthy kube-apiserver instances through health checks and exclude traffic
  - In cloud environments, use cloud provider's managed load balancers (AWS ELB, GCP Cloud Load Balancer, etc.)
  - In on-premises environments, use HAProxy, NGINX, keepalived, etc.

4. **Failure Scenarios and Response Measures**:
  - **Single control plane node failure**:
  - kube-apiserver: Load balancer routes traffic to healthy nodes
  - kube-scheduler/kube-controller-manager: Instance on another node activated through leader election
  - etcd: Cluster continues to operate if majority is healthy (2 of 3, 3 of 5)

  - **Availability zone failure**:
  - Distribute nodes across multiple availability zones to handle single zone failures
  - Also distribute worker nodes across multiple availability zones

  - **Network partition**:
  - etcd operates on majority basis to prevent "split brain" during network partitions
  - etcd nodes in minority partition switch to read-only mode

  - **etcd data corruption/loss**:
  - Perform regular etcd backups
  - Document and test recovery procedures from backups

5. **Additional Considerations**:
  - **Certificate management**: Monitor certificate expiration and auto-renewal
  - **Audit logging**: Enable audit logs for important operations and store externally
  - **Monitoring and alerting**: Set up monitoring and alerting for control plane component status
  - **Automated recovery**: Implement automated recovery mechanisms (e.g., systemd service auto-restart)

With this high availability architecture, the Kubernetes cluster can continue to operate even if a single node, single availability zone, or some components fail.
</details>

20. Explain the networking architecture of a Kubernetes cluster, describe how pod-to-pod communication, service networking, and external communication work, and explain the role of CNI plugins. Also explain how to restrict pod-to-pod communication using network policies.

<details>

<summary>Show Answer</summary>

**Answer:**

**Kubernetes Networking Architecture**

1. **Kubernetes Networking Model**:
  - All pods have unique IP addresses
  - Pods can communicate without NAT
  - Nodes and pods can communicate without NAT
  - Containers within a pod communicate through localhost

2. **Pod-to-Pod Communication**:
  - **Between pods on the same node**: Communication through the node's local bridge network
  - **Between pods on different nodes**: Communication through overlay network or routing tables
  - CNI plugins handle pod IP address assignment and routing

3. **Service Networking**:
  - **ClusterIP**: Virtual IP accessible only within the cluster
  - **kube-proxy**: Routes traffic to service IPs to pods
  - iptables mode: Implements NAT using Linux iptables rules
  - IPVS mode: Provides high-performance load balancing using Linux kernel's IP Virtual Server
  - **CoreDNS**: DNS service that resolves service names to ClusterIPs
  - **Service discovery**: Discover services through environment variables or DNS

4. **External Communication**:
  - **Ingress**: Routes HTTP/HTTPS traffic to services
  - **NodePort**: Exposes services through specific ports on nodes
  - **LoadBalancer**: Exposes services through cloud provider's load balancer
  - **ExternalName**: Creates CNAME records for external services

5. **Role of CNI (Container Network Interface) Plugins**:
  - Connect network interfaces to pods
  - Allocate and manage IP addresses
  - Configure routing tables
  - Implement network policies
  - Major CNI plugins:
  - **Calico**: BGP-based networking, network policy support, high performance
  - **Cilium**: eBPF-based networking and security, L3-L7 security policies, high performance
  - **Flannel**: Simple overlay network, easy configuration
  - **Weave Net**: Multi-host container networking, encryption support

6. **Restricting Pod-to-Pod Communication Using Network Policies**:
  - Control pod-to-pod communication using NetworkPolicy resources
  - By default, all pods can communicate with each other (when no policies exist)
  - Network policy components:
  - **podSelector**: Selects pods to which the policy applies
  - **policyTypes**: Ingress (incoming), Egress (outgoing), or both
  - **ingress**: Rules for incoming traffic
  - **egress**: Rules for outgoing traffic

  - **Default deny policy example**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

  - **Policy example allowing communication only between specific pods**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

  - **Namespace-to-namespace communication control example**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            purpose: monitoring
      ports:
        - protocol: TCP
          port: 9090
```

7. **Network Policy Implementation Considerations**:
  - Network policies are implemented by CNI plugins
  - Not all CNI plugins support network policies
  - Verify in a test environment before applying policies
  - Recommended to start with a default deny policy and allow only necessary communication

The Kubernetes networking architecture enables communication between containers in a flexible and scalable manner, and provides granular security control through network policies.
</details>

---

[Return to Learning Materials](../../core/01-cluster-architecture.md) | [Next Quiz: Pods and Workloads](../core/02-pods-and-workloads-quiz.md)
