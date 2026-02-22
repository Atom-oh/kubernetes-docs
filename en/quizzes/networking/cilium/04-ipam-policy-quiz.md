# Cilium IPAM and Network Policy Quiz

> **Supported Version**: Cilium 1.17
> **Last Updated**: July 21, 2025

## IPAM (IP Address Management)

1. **What is Cilium's default IPAM mode?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) CRD-based
   - D) AWS ENI

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Cluster Scope</p>
   <p><strong>Explanation</strong>: Cilium's default IPAM mode is Cluster Scope, which allocates IP addresses centrally across the entire cluster.</p>
   </details>

2. **Which Cilium IPAM mode has each node allocate IPs from its own CIDR range?**
   - A) Cluster Scope
   - B) Kubernetes Host Scope
   - C) CRD-based
   - D) AWS ENI

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Kubernetes Host Scope</p>
   <p><strong>Explanation</strong>: In Kubernetes Host Scope IPAM mode, each node allocates IP addresses from its own CIDR range.</p>
   </details>

3. **What is the recommended IPAM mode when using Cilium on AWS EKS?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) CRD-based

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) AWS ENI</p>
   <p><strong>Explanation</strong>: On AWS EKS, it is recommended to use AWS ENI IPAM mode to directly allocate VPC IP addresses to Pods.</p>
   </details>

4. **What Kubernetes feature does Cilium's 'PodCIDR' IPAM mode utilize?**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>Explanation</strong>: Cilium's PodCIDR IPAM mode utilizes the NodeSpec.PodCIDR field that Kubernetes assigns to each node.</p>
   </details>

5. **What command is used to check Cilium's IPAM configuration?**
   - A) `cilium status --ipam`
   - B) `cilium ipam`
   - C) `cilium config get ipam`
   - D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`</p>
   <p><strong>Explanation</strong>: Cilium's IPAM configuration is stored in the cilium-config ConfigMap and can be verified with this command.</p>
   </details>

## Network Policy Basics

6. **What is the API version of Cilium NetworkPolicy?**
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) cilium.io/v2</p>
   <p><strong>Explanation</strong>: Cilium NetworkPolicy uses the cilium.io/v2 API version.</p>
   </details>

7. **What is the role of 'endpointSelector' in Cilium NetworkPolicy?**
   - A) Select target Pods for policy application
   - B) Select target nodes for policy application
   - C) Select target namespaces for policy application
   - D) Select target services for policy application

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) Select target Pods for policy application</p>
   <p><strong>Explanation</strong>: endpointSelector is used to select the target Pods (endpoints) to which the policy applies.</p>
   </details>

8. **What does the 'ingress' rule control in Cilium NetworkPolicy?**
   - A) Traffic coming into the selected Pods
   - B) Traffic going out from the selected Pods
   - C) Traffic within the selected Pods
   - D) Traffic to outside the cluster

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) Traffic coming into the selected Pods</p>
   <p><strong>Explanation</strong>: Ingress rules control traffic coming into the selected Pods.</p>
   </details>

9. **What does the 'egress' rule control in Cilium NetworkPolicy?**
   - A) Traffic coming into the selected Pods
   - B) Traffic going out from the selected Pods
   - C) Traffic within the selected Pods
   - D) Traffic from outside the cluster

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Traffic going out from the selected Pods</p>
   <p><strong>Explanation</strong>: Egress rules control traffic going out from the selected Pods.</p>
   </details>

10. **What is the role of the 'labels' field in Cilium NetworkPolicy?**
    - A) Select Pods for policy application
    - B) Identifier for the policy itself
    - C) Select namespaces for policy application
    - D) Select nodes for policy application

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Identifier for the policy itself</p>
    <p><strong>Explanation</strong>: The labels field is used as an identifier for the policy itself and is used when other policies reference this policy.</p>
    </details>

## Advanced Network Policy

11. **What does the 'toCIDR' rule in Cilium NetworkPolicy allow?**
    - A) Traffic to specific IP address ranges
    - B) Traffic to specific domain names
    - C) Traffic to specific services
    - D) Traffic to specific ports

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) Traffic to specific IP address ranges</p>
    <p><strong>Explanation</strong>: The toCIDR rule is used to allow traffic to specific IP address ranges (CIDR notation).</p>
    </details>

12. **What does the 'toFQDNs' rule in Cilium NetworkPolicy allow?**
    - A) Traffic to specific IP addresses
    - B) Traffic to specific ports
    - C) Traffic to specific domain names
    - D) Traffic of specific protocols

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) Traffic to specific domain names</p>
    <p><strong>Explanation</strong>: The toFQDNs rule allows traffic to specific domain names (FQDNs), with Cilium monitoring DNS lookups to dynamically allow IP addresses for those domains.</p>
    </details>

13. **What does the 'world' entity mean in the 'toEntities' rule of Cilium NetworkPolicy?**
    - A) All internal cluster endpoints
    - B) All external networks
    - C) All nodes
    - D) All namespaces

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) All external networks</p>
    <p><strong>Explanation</strong>: The 'world' entity refers to all networks outside the cluster.</p>
    </details>

14. **What does the 'toServices' rule in Cilium NetworkPolicy allow?**
    - A) Traffic to specific Kubernetes services
    - B) Traffic to specific external services
    - C) Traffic to specific ports
    - D) Traffic of specific protocols

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) Traffic to specific Kubernetes services</p>
    <p><strong>Explanation</strong>: The toServices rule is used to allow traffic to specific Kubernetes services.</p>
    </details>

15. **What is the role of 'nodeSelector' in Cilium NetworkPolicy?**
    - A) Select target Pods for policy application
    - B) Select target nodes for policy application
    - C) Select target namespaces for policy application
    - D) Select target services for policy application

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Select target nodes for policy application</p>
    <p><strong>Explanation</strong>: nodeSelector is used to select the target nodes to which the policy applies.</p>
    </details>

## L7 Policy

16. **What attributes can be filtered in Cilium's L7 HTTP policy?**
    - A) Path
    - B) Method
    - C) Headers
    - D) All of the above

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) All of the above</p>
    <p><strong>Explanation</strong>: Cilium's L7 HTTP policy can filter various HTTP request attributes including path, method, and headers.</p>
    </details>

17. **What attributes can be filtered in Cilium's L7 Kafka policy?**
    - A) Topic
    - B) API Key
    - C) Client ID
    - D) All of the above

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) All of the above</p>
    <p><strong>Explanation</strong>: Cilium's L7 Kafka policy can filter various Kafka request attributes including topic, API key, and client ID.</p>
    </details>

18. **What does the 'matchPattern' rule in Cilium's L7 DNS policy allow?**
    - A) Exact domain name matching
    - B) Domain name pattern matching with wildcards
    - C) IP address matching
    - D) Port number matching

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Domain name pattern matching with wildcards</p>
    <p><strong>Explanation</strong>: The matchPattern rule can match domain name patterns including wildcards (*). Example: *.example.com</p>
    </details>

19. **What attributes can be filtered in Cilium's L7 gRPC policy?**
    - A) Method name
    - B) Service name
    - C) Metadata
    - D) All of the above

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) All of the above</p>
    <p><strong>Explanation</strong>: Cilium's L7 gRPC policy can filter various gRPC request attributes including method name, service name, and metadata.</p>
    </details>

20. **What component is required to apply Cilium's L7 policy?**
    - A) kube-proxy
    - B) Envoy Proxy
    - C) NGINX Ingress Controller
    - D) HAProxy

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Envoy Proxy</p>
    <p><strong>Explanation</strong>: Cilium uses Envoy Proxy to apply L7 policies.</p>
    </details>
