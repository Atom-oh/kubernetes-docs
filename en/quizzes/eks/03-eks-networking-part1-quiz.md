# Amazon EKS Networking Quiz (Part 1)

This quiz tests your understanding of basic networking concepts in Amazon EKS, VPC CNI, network policies, and service discovery. It focuses on the networking architecture and components of EKS clusters.

## Multiple Choice Questions

### 1. What is the default CNI (Container Network Interface) plugin used in Amazon EKS?

A. Calico
B. Flannel
C. Amazon VPC CNI
D. Weave Net

<details>
<summary>Show Answer</summary>

**Answer: C. Amazon VPC CNI**

**Explanation:**
Amazon EKS uses the Amazon VPC CNI plugin by default. This plugin assigns VPC IP addresses to Kubernetes pods and enables communication between pods using the native features of AWS VPC networking.

**Key Features:**

1. **Native VPC Networking**: Each pod receives a unique IP address within the VPC. This allows pods to communicate directly with other services within the VPC.

2. **Secondary IP Address Assignment**: Secondary IP addresses are assigned to each node's Elastic Network Interface (ENI) and provided to pods.

3. **Security Group Integration**: AWS security groups can be applied at the pod level, enabling fine-grained network security control.

4. **Performance**: Network performance is improved by not using overlay networks.

5. **AWS Service Integration**: Seamlessly integrates with other AWS services like AWS Load Balancer Controller and AWS App Mesh.

**Configuration Example:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-network-policy: "true"
  enable-pod-eni: "true"
  warm-ip-target: "5"
  minimum-ip-target: "10"
```

Amazon VPC CNI is open source and managed on GitHub. It can be replaced with other CNI plugins like Calico or Cilium as needed, but Amazon VPC CNI is the default option for EKS and officially supported by AWS.
</details>

### 2. How does VPC CNI assign IP addresses to pods in Amazon EKS?

A. Assigns a separate Elastic Network Interface (ENI) to each pod
B. Assigns secondary IP addresses to the node's Elastic Network Interface (ENI) and provides them to pods
C. Uses overlay networks to assign virtual IP addresses
D. Assigns a separate VPC subnet to each pod

<details>
<summary>Show Answer</summary>

**Answer: B. Assigns secondary IP addresses to the node's Elastic Network Interface (ENI) and provides them to pods**

**Explanation:**
Amazon VPC CNI works by assigning secondary IP addresses to the node's Elastic Network Interface (ENI) and providing these IP addresses to pods. This method is also called the "IP-per-Pod" model.

**How It Works:**

1. **ENI Allocation**: Each EC2 instance (node) can have one or more ENIs. The number of IP addresses that can be assigned per ENI is determined by the instance type.

2. **IP Address Pool Management**: The `aws-node` DaemonSet of VPC CNI runs on each node and manages the available IP address pool.

3. **IP Address Assignment**: When a pod is created, the CNI assigns an IP address from the pool and connects it to the pod's network namespace.

4. **IP Address Reclamation**: When a pod terminates, the CNI reclaims the IP address and returns it to the pool.

**Example Configuration:**
```bash
# Maximum pods per node calculation
Maximum pods = (Number of ENIs × (IP addresses per ENI - 1)) + 2

# For m5.large instance
# Number of ENIs: 3, IP addresses per ENI: 10
Maximum pods = (3 × (10 - 1)) + 2 = 29
```

**Key Considerations:**

1. **IP Address Limit**: The maximum number of pods that can run per node is limited depending on the instance type.

2. **Warm IPs**: VPC CNI can pre-allocate a certain number of IP addresses through the `WARM_IP_TARGET` setting to reduce pod startup time.

3. **Prefix Delegation**: Newer versions of VPC CNI support the prefix delegation feature, which allocates /28 CIDR blocks (16 IPs) to each ENI, increasing IP address density.

4. **Security Groups**: Enabling the `ENABLE_POD_ENI` setting allows configuring separate security groups for specific pods (Security Groups for Pods feature).

Issues with other options:
- **A**: Generally, a separate ENI is not assigned to each pod. This is inefficient due to ENI limits per EC2 instance.
- **C**: VPC CNI does not use overlay networks. This is a characteristic of other CNI plugins like Flannel or Weave Net.
- **D**: Assigning a separate VPC subnet to each pod is not possible in AWS VPC architecture.
</details>

### 3. Why does pod-to-pod communication in Amazon EKS occur directly within the VPC without going outside?

A. Because all pods are located in the same subnet
B. Because pods share the node's network namespace
C. Because pods are directly assigned VPC IP addresses
D. Because pod-to-pod communication always goes through a service mesh

<details>
<summary>Show Answer</summary>

**Answer: C. Because pods are directly assigned VPC IP addresses**

**Explanation:**
The main reason pod-to-pod communication in Amazon EKS occurs directly within the VPC without going outside is that the Amazon VPC CNI plugin directly assigns VPC IP addresses to each pod.

**Key Mechanisms:**

1. **VPC IP Address Assignment**: Each pod receives a unique IP address from the VPC subnet. This IP address is a secondary IP address connected to the node's ENI.

2. **Direct Routing**: Since pods have VPC IP addresses, they can communicate directly with other resources in the VPC (other pods, EC2 instances, RDS databases, etc.).

3. **VPC Routing Tables**: Pod-to-pod communication follows VPC routing tables and is routed directly within the same VPC without going outside.

**Advantages:**

1. **Network Performance**: Reduced latency and improved throughput by not using overlay networks or NAT.

2. **Security**: Can leverage existing AWS network security mechanisms like VPC security groups and network ACLs.

3. **Visibility**: Can monitor and analyze pod-to-pod traffic through VPC Flow Logs.

4. **AWS Service Integration**: Since pods have VPC IP addresses, they integrate seamlessly with AWS services like VPC endpoints and PrivateLink.

**Example Scenario:**

When Pod A (IP: 10.0.1.23) communicates with Pod B (IP: 10.0.2.45):
1. Pod A sends packets directly to Pod B's IP address (10.0.2.45).
2. Packets are routed according to the VPC routing table.
3. Packets reach Pod B directly within the VPC.
4. Throughout this process, packets do not go outside the VPC.

Issues with other options:
- **A**: Pods can be distributed across multiple subnets, and pods in different subnets can still communicate directly within the VPC.
- **B**: Pods do not share the node's network namespace. Each pod has its own network namespace.
- **D**: Pod-to-pod communication does not always go through a service mesh. Service mesh is an optional additional layer.
</details>

### 4. What is the most appropriate Kubernetes resource for controlling inbound and outbound traffic to pods in Amazon EKS?

A. Service
B. Ingress
C. NetworkPolicy
D. SecurityContext

<details>
<summary>Show Answer</summary>

**Answer: C. NetworkPolicy**

**Explanation:**
The most appropriate Kubernetes resource for controlling inbound and outbound traffic to pods in Amazon EKS is NetworkPolicy. NetworkPolicy is Kubernetes' network security mechanism that allows fine-grained control of communication between pods.

**Key Features of NetworkPolicy:**

1. **Selective Application**: Can apply policies to specific pods using label selectors.

2. **Inbound and Outbound Rules**: Can control both ingress (inbound) and egress (outbound) traffic.

3. **Various Selectors**: Can filter traffic based on namespaces, labels, IP CIDR blocks, ports, etc.

4. **Default Deny Policy**: Traffic not explicitly allowed is denied by default.

**NetworkPolicy Example:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          purpose: frontend
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          purpose: database
    ports:
    - protocol: TCP
      port: 5432
```

**NetworkPolicy Implementation in EKS:**

To use NetworkPolicy in Amazon EKS, a CNI plugin that supports network policies is required. The default Amazon VPC CNI does not directly support network policies, so additional configuration is needed:

1. **Install Calico**: Calico is the most common way to implement NetworkPolicy in EKS.
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
   ```

2. **Enable Network Policy in Amazon VPC CNI**: Newer versions of Amazon VPC CNI provide network policy support.
   ```bash
   kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
   ```

Issues with other options:
- **A. Service**: Service provides network access to pods but does not have traffic control or filtering capabilities.
- **B. Ingress**: Ingress is used to route HTTP/HTTPS traffic to services within the cluster but does not define general network policies.
- **D. SecurityContext**: SecurityContext defines security settings at the pod or container level but is not related to network traffic control.
</details>

### 5. What DNS service is used for service discovery within an EKS cluster?

A. Amazon Route 53
B. CoreDNS
C. kube-dns
D. AWS Cloud Map

<details>
<summary>Show Answer</summary>

**Answer: B. CoreDNS**

**Explanation:**
The DNS service used by default for service discovery within Amazon EKS clusters is CoreDNS. CoreDNS is a flexible and extensible DNS server that provides DNS-based service discovery within Kubernetes clusters.

**Key Features of CoreDNS:**

1. **Kubernetes Integration**: CoreDNS integrates with the Kubernetes API to automatically create DNS records for services and pods.

2. **Plugin Architecture**: CoreDNS can extend functionality through various plugins.

3. **High Availability**: In EKS, CoreDNS is typically deployed with multiple replicas to ensure high availability.

4. **Configurability**: Various DNS settings can be configured through the Corefile.

**CoreDNS Deployment in EKS:**

When you create an EKS cluster, CoreDNS is automatically deployed. CoreDNS runs as a Deployment in the `kube-system` namespace:

```bash
kubectl get deployment coredns -n kube-system
```

**CoreDNS Configuration Example:**

CoreDNS configuration is stored in a ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

**How Service Discovery Works:**

1. **Service Creation**: When a Kubernetes Service is created, CoreDNS automatically creates a DNS record.

2. **DNS Name Format**:
   - Service: `<service-name>.<namespace>.svc.cluster.local`
   - Pod: `<pod-ip>.<namespace>.pod.cluster.local`

3. **DNS Lookup**: When a pod within the cluster performs a DNS lookup with a service name, CoreDNS responds with that service's ClusterIP.

**Example:**
```bash
# If my-service service exists in the default namespace
nslookup my-service.default.svc.cluster.local

# Result
Name:   my-service.default.svc.cluster.local
Address: 10.100.43.150  # Service's ClusterIP
```

**CoreDNS Scaling and Optimization:**

In EKS, CoreDNS does not automatically scale with cluster size, so in large clusters, you may need to scale manually:

```bash
kubectl scale deployment coredns --replicas=4 -n kube-system
```

Also, you can optimize performance by adjusting cache settings:

```yaml
cache {
    success 10000
    denial 1000
    prefetch 10 10m 20%
}
```

Issues with other options:
- **A. Amazon Route 53**: Route 53 is AWS's DNS service but is not used by default for service discovery within EKS clusters.
- **C. kube-dns**: kube-dns was used in previous versions of Kubernetes but has been replaced by CoreDNS in EKS.
- **D. AWS Cloud Map**: Cloud Map is AWS's service discovery service but is not used as the default DNS service within EKS clusters.
</details>

## Short Answer Questions

### 6. What is the main factor limiting the maximum number of pods per node in an Amazon EKS cluster, and what methods can be used to increase it?

<details>
<summary>Show Answer</summary>

**Answer:**
The main factor limiting the maximum number of pods per node in an Amazon EKS cluster is **the number of ENIs (Elastic Network Interfaces) per EC2 instance type and the number of allocatable IP addresses per ENI**. The primary method to increase this is to **enable the Prefix Delegation feature**.

**Detailed Explanation:**

1. **Maximum Pods Per Node Calculation Formula**:
   ```
   Maximum pods = (Number of ENIs × (IP addresses per ENI - 1)) + 2
   ```
   - The first IP address of each ENI is reserved for the node itself.
   - The additional 2 are for kube-proxy and aws-node pods.

2. **Limits by Instance Type Examples**:
   - **t3.small**: (3 ENIs × (4 IPs - 1)) + 2 = 11 pods
   - **m5.large**: (3 ENIs × (10 IPs - 1)) + 2 = 29 pods
   - **c5.4xlarge**: (8 ENIs × (30 IPs - 1)) + 2 = 234 pods

3. **Expansion Through Prefix Delegation**:
   Prefix delegation is a feature that allocates /28 CIDR blocks (16 IPs) instead of individual IP addresses to each ENI.

   **How to Enable**:
   ```bash
   # Modify ConfigMap
   kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

   # Optionally set prefix allocation mode
   kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1
   ```

   **Calculation Formula After Enabling Prefix Delegation**:
   ```
   Maximum pods = (Number of ENIs × (Prefixes per ENI × IPs per prefix - 1)) + 2
   ```

   Example: m5.large with prefix delegation enabled
   - Without prefix delegation: 29 pods
   - With prefix delegation enabled: (3 ENIs × (1 prefix × 16 IPs - 1)) + 2 = 47 pods

4. **Other Methods to Increase Maximum Pod Count**:
   - **Use Larger Instance Types**: Change to instance types that support more ENIs and IP addresses
   - **Custom CNI Configuration**: Adjust kubelet configuration using `--max-pods` flag (not recommended)
   - **Use Alternative CNI Plugins**: Switch to CNI plugins using overlay networks like Calico, Cilium

5. **Considerations**:
   - Prefix delegation is only supported on EC2 Nitro-based instances.
   - When prefix delegation is enabled, you cannot use the SecurityGroupsForPods feature.
   - As the number of pods per node increases, node resource (CPU, memory) contention may occur, so selecting appropriate instance size is important.

6. **Monitoring and Optimization**:
   ```bash
   # Check current IP address usage
   kubectl exec -n kube-system ds/aws-node -- curl -s http://localhost:61679/v1/enis | jq

   # Check prefix delegation status
   kubectl describe daemonset aws-node -n kube-system | grep PREFIX
   ```

While enabling prefix delegation can significantly increase the maximum pod count per node, it's important to choose the appropriate configuration based on your cluster's requirements and workload characteristics.
</details>

### 7. What is the name of the feature that allows assigning specific AWS security groups to pods in Amazon EKS, and how do you configure it?

<details>
<summary>Show Answer</summary>

**Answer:**
The name of the feature that allows assigning specific AWS security groups to pods in Amazon EKS is **Security Groups for Pods** or **Pod ENI (Elastic Network Interface)**. This feature can be configured by enabling the **ENABLE_POD_ENI** option in VPC CNI.

**Detailed Explanation:**

1. **Security Groups for Pods Overview**:
   This feature creates a separate ENI (also called trunk ENI) for specific pods and attaches security groups to this ENI, enabling fine-grained network security control at the pod level.

2. **Prerequisites**:
   - Amazon VPC CNI plugin version 1.7.7 or higher
   - Kubernetes version 1.17 or higher
   - EC2 Nitro-based instances
   - Prefix delegation feature must be disabled

3. **Configuration Steps**:

   a. **Enable Pod ENI Feature in VPC CNI**:
   ```bash
   kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true
   ```

   b. **Create SecurityGroupPolicy Resource**:
   ```yaml
   apiVersion: vpcresources.k8s.aws/v1beta1
   kind: SecurityGroupPolicy
   metadata:
     name: allow-db-access
     namespace: app
   spec:
     podSelector:
       matchLabels:
         role: db-client
     securityGroups:
       groupIds:
         - sg-0123456789abcdef0
   ```

   c. **Grant IAM Permissions to Service Account**:
   The VPC CNI service account needs the following permissions:
   - ec2:CreateNetworkInterface
   - ec2:DeleteNetworkInterface
   - ec2:DescribeNetworkInterfaces
   - ec2:DescribeSecurityGroups
   - ec2:ModifyNetworkInterfaceAttribute
   - ec2:CreateTags

4. **Pod Configuration Example**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: db-client
     namespace: app
     labels:
       role: db-client
   spec:
     containers:
     - name: app
       image: amazonlinux:2
       command: ['sleep', '3600']
   ```

5. **How It Works**:
   - When a pod with labels matching a SecurityGroupPolicy is created, VPC CNI creates a branch ENI for that pod.
   - The specified security groups are attached to this branch ENI.
   - The pod's traffic is routed through this branch ENI, and the attached security group rules are applied.

6. **Verification Methods**:
   ```bash
   # Check pod's ENI information
   kubectl describe pod db-client -n app

   # Check SecurityGroupPolicy
   kubectl get securitygrouppolicy -n app

   # Check VPC CNI logs
   kubectl logs -n kube-system -l k8s-app=aws-node
   ```

7. **Limitations**:
   - There are limits on the number of branch ENIs per node (varies by instance type).
   - Cannot be used together with the prefix delegation feature.
   - Security groups cannot be changed after the pod is created.
   - Pod startup time may increase slightly.

8. **Use Cases**:
   - Pods accessing AWS services that control access with security groups like RDS, ElastiCache
   - When fine-grained control of inbound/outbound traffic for specific pods is needed
   - Workloads requiring network isolation according to regulatory requirements

The Security Groups for Pods feature is a powerful tool for enhancing EKS networking security, but it should be used appropriately considering the resource overhead from additional ENI usage and limitations.
</details>

### 8. When using Service type LoadBalancer in Amazon EKS, what type of load balancer does AWS Load Balancer Controller create by default, and how do you change it?

<details>
<summary>Show Answer</summary>

**Answer:**
When using Service type LoadBalancer in Amazon EKS, AWS Load Balancer Controller creates a **Classic Load Balancer (CLB)** by default. To change this to a **Network Load Balancer (NLB)**, you need to add a specific **annotation** to the service.

**Detailed Explanation:**

1. **Default Behavior**:
   When you create a `LoadBalancer` type Kubernetes Service, the AWS cloud controller manager provisions a Classic Load Balancer by default.

2. **How to Change to Network Load Balancer**:
   Add the following annotation to the Service:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-type: nlb
   ```

3. **Complete Service Example (Using NLB)**:
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: my-service
     annotations:
       service.beta.kubernetes.io/aws-load-balancer-type: nlb
   spec:
     type: LoadBalancer
     ports:
     - port: 80
       targetPort: 8080
     selector:
       app: my-app
   ```

4. **Internal Load Balancer Configuration**:
   By default, load balancers created are internet-facing. To configure as internal load balancer:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-internal: "true"
   ```

5. **Additional Configuration Options**:

   a. **Target Type Setting (IP Mode)**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
   ```

   b. **Specify Security Groups**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-0123456789abcdef0
   ```

   c. **Specify Subnets**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
   ```

   d. **Disable Cross-Zone Load Balancing**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "false"
   ```

   e. **Enable Access Logs**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-access-log-enabled: "true"
   service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name: "my-elb-logs"
   service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix: "my-app"
   ```

   f. **SSL Certificate Configuration (HTTPS)**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:region:account-id:certificate/certificate-id
   service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
   ```

6. **Using AWS Load Balancer Controller**:
   In newer EKS clusters, you can use AWS Load Balancer Controller to leverage more features:

   a. **Installation**:
   ```bash
   helm repo add eks https://aws.github.io/eks-charts
   helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
     -n kube-system \
     --set clusterName=my-cluster \
     --set serviceAccount.create=false \
     --set serviceAccount.name=aws-load-balancer-controller
   ```

   b. **Using Application Load Balancer (ALB) with Ingress**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: my-ingress
     annotations:
       kubernetes.io/ingress.class: alb
       alb.ingress.kubernetes.io/scheme: internet-facing
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

7. **Load Balancer Type Comparison**:

   | Characteristic | Classic Load Balancer | Network Load Balancer | Application Load Balancer |
   |----------------|----------------------|----------------------|--------------------------|
   | Protocol | TCP, SSL, HTTP, HTTPS | TCP, UDP, TLS | HTTP, HTTPS |
   | Layer | 4 & 7 | 4 | 7 |
   | Performance | Good | Very Good | Good |
   | Latency | Medium | Very Low | Low |
   | Static IP | No | Yes | No |
   | Path-based Routing | No | No | Yes |
   | WebSockets | Limited | Yes | Yes |
   | Container-based Targets | No | Yes (IP mode) | Yes (IP mode) |

8. **Best Practices**:
   - Use Ingress with ALB for most HTTP/HTTPS traffic
   - Use NLB for TCP/UDP traffic or when very high throughput is needed
   - Unless there are legacy applications or special requirements, use NLB or ALB instead of CLB
   - Always enable cross-zone load balancing in production environments

Using AWS Load Balancer Controller allows more effective management of AWS load balancers through Kubernetes Services and Ingress resources, with fine-grained configuration possible through various annotations.
</details>

## Hands-on Questions

### 9. Write a NetworkPolicy that allows communication only between pods within a specific namespace and blocks communication with pods from other namespaces in an Amazon EKS cluster.

<details>
<summary>Show Answer</summary>

**Answer:**
The following is a NetworkPolicy that allows communication only between pods within a specific namespace and blocks communication with pods from other namespaces:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-to-same-namespace
  namespace: app-namespace  # Namespace name to apply
spec:
  podSelector: {}  # Apply to all pods in the namespace
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: app-namespace  # Same namespace
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: app-namespace  # Same namespace
  # Allow DNS lookups (to CoreDNS in kube-system)
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

**Detailed Explanation:**

1. **NetworkPolicy Component Explanation**:

   - **metadata.namespace**: Specifies the namespace where this policy will be applied.
   - **spec.podSelector: {}**: An empty pod selector applies the policy to all pods in the namespace.
   - **policyTypes**: Controls both Ingress (inbound) and Egress (outbound) traffic.
   - **ingress.from.namespaceSelector**: Allows traffic only from the same namespace.
   - **egress.to.namespaceSelector**: Allows traffic only to the same namespace.
   - **Allow DNS Lookups**: Allows DNS traffic to CoreDNS in the kube-system namespace.

2. **Implementation Steps**:

   a. **Create Namespace**:
   ```bash
   kubectl create namespace app-namespace
   ```

   b. **Add Label to Namespace** (automatically added in Kubernetes 1.21+):
   ```bash
   kubectl label namespace app-namespace kubernetes.io/metadata.name=app-namespace
   ```

   c. **Apply NetworkPolicy**:
   ```bash
   kubectl apply -f network-policy.yaml
   ```

   d. **Verify Policy**:
   ```bash
   kubectl describe networkpolicy restrict-to-same-namespace -n app-namespace
   ```

3. **Testing Method**:

   a. **Deploy Test Pod in Same Namespace**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: test-pod-1
     namespace: app-namespace
   spec:
     containers:
     - name: busybox
       image: busybox
       command: ['sleep', '3600']
   ```

   b. **Deploy Test Pod in Different Namespace**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: test-pod-2
     namespace: default
   spec:
     containers:
     - name: busybox
       image: busybox
       command: ['sleep', '3600']
   ```

   c. **Connection Test**:
   ```bash
   # Test communication within same namespace (should succeed)
   kubectl exec -n app-namespace test-pod-1 -- ping -c 2 $(kubectl get pod test-pod-3 -n app-namespace -o jsonpath='{.status.podIP}')

   # Test communication to other namespace (should fail)
   kubectl exec -n app-namespace test-pod-1 -- ping -c 2 $(kubectl get pod test-pod-2 -n default -o jsonpath='{.status.podIP}')
   ```

4. **Notes and Considerations**:

   a. **Verify NetworkPolicy Support**:
   To use NetworkPolicy in Amazon EKS, a CNI plugin that supports network policies is required:
   ```bash
   # Install Calico
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml

   # Or enable network policy in Amazon VPC CNI
   kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
   ```

   b. **Default Deny Policy**:
   When NetworkPolicy is applied, all traffic not explicitly allowed is denied by default.

   c. **Allow DNS Access**:
   You must allow traffic to CoreDNS in the kube-system namespace so that pods can perform DNS lookups.

   d. **System Service Access**:
   You may need to allow access to system services like the Kubernetes API server, monitoring services as needed.

5. **Extensions and Improvements**:

   a. **Allow Communication Only Between Specific Pods**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-specific-pods
     namespace: app-namespace
   spec:
     podSelector:
       matchLabels:
         app: web
     policyTypes:
     - Ingress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: api
   ```

   b. **Allow Only Specific Ports**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-specific-ports
     namespace: app-namespace
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             kubernetes.io/metadata.name: app-namespace
       ports:
       - protocol: TCP
         port: 8080
   ```

   c. **Allow External Service Access**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-external-service
     namespace: app-namespace
   spec:
     podSelector:
       matchLabels:
         app: web
     policyTypes:
     - Egress
     egress:
     - to:
       - ipBlock:
           cidr: 10.0.0.0/16  # VPC CIDR
       - ipBlock:
           cidr: 0.0.0.0/0
           except:
           - 10.0.0.0/8
           - 172.16.0.0/12
           - 192.168.0.0/16
   ```

Using NetworkPolicy allows implementing fine-grained network security control within EKS clusters, which is particularly useful in multi-tenant environments or workloads with regulatory requirements.
</details>

## Advanced Questions

### 10. Explain various strategies to solve the IP address exhaustion problem with VPC CNI in an Amazon EKS cluster, and compare the advantages and disadvantages of each approach.

<details>
<summary>Show Answer</summary>

**Answer:**
The following are various strategies to solve the IP address exhaustion problem with VPC CNI in an Amazon EKS cluster and the advantages and disadvantages of each approach:

## 1. Enable Prefix Delegation

**Description**: A feature that allocates /28 CIDR blocks (16 IPs) instead of individual IP addresses to each ENI.

**Implementation Method**:
```bash
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
```

**Advantages**:
- Significantly increases available IP addresses per node (up to 5x)
- Compatible with existing VPC CNI features
- Improved IP address allocation speed

**Disadvantages**:
- Only supported on EC2 Nitro-based instances
- Cannot be used together with Security Groups for Pods feature
- Possible compatibility issues with some AWS services

## 2. Enable Custom Networking Mode

**Description**: A feature that allocates pod IP addresses from separate subnets rather than the subnet where nodes are located.

**Implementation Method**:
```bash
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=failure-domain.beta.kubernetes.io/zone
```

Create ENIConfig for each availability zone:
```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  securityGroups:
    - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
```

**Advantages**:
- Prevents IP address exhaustion of node subnets
- Enables dedicated subnet configuration for pod networking
- Can use larger CIDR blocks

**Disadvantages**:
- Complex setup and management
- Additional subnets required
- ENIConfig reconfiguration needed when nodes are replaced

## 3. Add Secondary CIDR Blocks

**Description**: Add secondary CIDR blocks to the VPC and assign them to new subnets to expand IP address space.

**Implementation Method**:
1. Add secondary CIDR block to VPC through AWS console or CLI
2. Create new subnets in the secondary CIDR block
3. Use together with custom networking mode

**Advantages**:
- Greatly expands IP address space of existing VPC
- Can be implemented without affecting existing infrastructure
- Can use larger CIDR blocks

**Disadvantages**:
- Increased networking configuration complexity with VPC peering, Transit Gateway, etc.
- Routing table updates required
- Some AWS services may not fully support secondary CIDRs

## 4. Use Alternative CNI Plugins

**Description**: Use alternative CNI plugins like Calico or Cilium instead of Amazon VPC CNI.

**Implementation Method**:
```bash
# Calico installation example
kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml

# Disable Amazon VPC CNI
kubectl patch daemonset aws-node -n kube-system -p '{"spec": {"template": {"spec": {"nodeSelector": {"non-existing": "true"}}}}}'
```

**Advantages**:
- Solves IP address limitations through overlay networks
- Richer network policy features
- Cloud provider-agnostic networking

**Disadvantages**:
- Lack of integration with AWS native features (security groups, etc.)
- Possible performance overhead
- Additional management complexity
- Outside AWS support scope

## 5. Use Larger Subnet CIDRs

**Description**: Use subnets with larger CIDR blocks when creating clusters.

**Implementation Method**:
When creating new clusters, use subnets with larger CIDR blocks (e.g., /16 or /17)

**Advantages**:
- Simple implementation
- No additional configuration needed
- All existing VPC CNI features available

**Disadvantages**:
- Difficult to apply to existing clusters
- Possible inefficient use of IP address space
- VPC design changes required

## 6. Optimize Warm IP and Minimum IP Settings

**Description**: Improve IP address usage efficiency by optimizing VPC CNI's IP address allocation behavior.

**Implementation Method**:
```bash
# Set warm IP target
kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5

# Set minimum IP target
kubectl set env daemonset aws-node -n kube-system MINIMUM_IP_TARGET=10

# Set maximum ENI
kubectl set env daemonset aws-node -n kube-system MAX_ENI=5
```

**Advantages**:
- Can be implemented with simple adjustment of existing settings
- No additional infrastructure changes needed
- Improved IP address allocation efficiency

**Disadvantages**:
- May not completely solve IP address shortage problem
- Possible pod startup delays
- Limited effectiveness depending on node type

## 7. Hybrid Approach

**Description**: Use a combination of multiple strategies. For example, use prefix delegation together with custom networking, or move some workloads to Fargate.

**Implementation Method**:
Selectively apply various strategies according to workload characteristics

**Advantages**:
- Optimized solution for workload characteristics
- Improved resource efficiency
- Gradual implementation possible

**Disadvantages**:
- Increased configuration and management complexity
- Need to understand various networking models
- Increased troubleshooting difficulty

## 8. Use Fargate

**Description**: Use Fargate instead of node-based workloads to delegate IP address management to AWS.

**Implementation Method**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    fargate: "true"

---
apiVersion: eks.amazonaws.com/v1alpha1
kind: FargateProfile
metadata:
  name: my-fargate-profile
  namespace: default
spec:
  selectors:
  - namespace: my-app
```

**Advantages**:
- Eliminates IP address management overhead
- No node management needed
- Serverless scalability

**Disadvantages**:
- Possible cost increase
- Some Kubernetes feature limitations (DaemonSets, privileged containers, etc.)
- Not suitable for all workloads

## Recommended Approaches and Best Practices

1. **Assess Current Situation**:
   - Analyze current IP address usage and expected growth rate
   - Understand workload characteristics and requirements
   - Review existing network configuration

2. **Short-term Solutions**:
   - Enable prefix delegation (simplest and most effective method)
   - Optimize warm IP and minimum IP settings
   - Clean up unnecessary pods

3. **Medium to Long-term Solutions**:
   - Configure custom networking
   - Add secondary CIDR blocks
   - Implement hybrid approach

4. **Monitoring and Alerting**:
   - Monitor IP address usage
   - Set threshold-based alerts
   - Regular capacity planning reviews

5. **Automation**:
   - Automate IP address usage monitoring and reporting
   - Automatically adjust network configuration when cluster scales
   - Establish documentation and operational procedures

IP address exhaustion is a common issue as EKS clusters grow, and appropriate strategies should be selected or combined based on cluster scale and workload characteristics. Prefix delegation is the simplest and most effective solution in most cases, but more comprehensive network design may be needed long-term.
</details>
