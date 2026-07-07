# Cilium Security and Visibility Quiz

> **Supported Version**: Cilium 1.17
> **Last Updated**: February 22, 2026

## Network Policy Basics

1. **What is the main difference between Kubernetes NetworkPolicy and Cilium NetworkPolicy?**
   - A) Cilium NetworkPolicy does not support L7 policies
   - B) Kubernetes NetworkPolicy does not support L7 policies
   - C) Cilium NetworkPolicy can only be applied to specific nodes
   - D) Kubernetes NetworkPolicy provides higher performance

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Kubernetes NetworkPolicy does not support L7 policies</p>
   <p><strong>Explanation</strong>: Kubernetes NetworkPolicy only supports L3/L4 level policies, while Cilium NetworkPolicy supports a broader range of policies from L3 to L7.</p>
   </details>

2. **What is the API group for Cilium NetworkPolicy?**
   - A) networking.k8s.io
   - B) cilium.io
   - C) policy.cilium.io
   - D) network.cilium.io

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) cilium.io</p>
   <p><strong>Explanation</strong>: Cilium NetworkPolicy uses the cilium.io API group.</p>
   </details>

3. **What is the role of 'endpointSelector' in Cilium NetworkPolicy?**
   - A) Selects target Pods to which the policy applies
   - B) Selects target nodes to which the policy applies
   - C) Selects target namespaces to which the policy applies
   - D) Selects target services to which the policy applies

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) Selects target Pods to which the policy applies</p>
   <p><strong>Explanation</strong>: endpointSelector is used to select the target Pods (endpoints) to which the policy applies.</p>
   </details>

4. **What does the 'ingress' rule control in Cilium NetworkPolicy?**
   - A) Incoming traffic to selected Pods
   - B) Outgoing traffic from selected Pods
   - C) Internal traffic within selected Pods
   - D) Traffic to outside the cluster

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) Incoming traffic to selected Pods</p>
   <p><strong>Explanation</strong>: Ingress rules control incoming traffic to the selected Pods.</p>
   </details>

5. **What does the 'egress' rule control in Cilium NetworkPolicy?**
   - A) Incoming traffic to selected Pods
   - B) Outgoing traffic from selected Pods
   - C) Internal traffic within selected Pods
   - D) Traffic from outside the cluster

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Outgoing traffic from selected Pods</p>
   <p><strong>Explanation</strong>: Egress rules control outgoing traffic from the selected Pods.</p>
   </details>

## L7 Policies

6. **Which attribute cannot be filtered in Cilium's L7 HTTP policies?**
   - A) Path
   - B) Method
   - C) Headers
   - D) Response Time

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: D) Response Time</p>
   <p><strong>Explanation</strong>: Cilium's L7 HTTP policies can filter HTTP request attributes such as path, method, and headers, but response time is not a filtering target.</p>
   </details>

7. **Which attribute can be filtered in Cilium's L7 Kafka policies?**
   - A) Topic
   - B) Partition
   - C) Offset
   - D) All of the above

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) Topic</p>
   <p><strong>Explanation</strong>: Cilium's L7 Kafka policies can filter primarily based on topic, API key, and similar attributes.</p>
   </details>

8. **What does the 'matchPattern' rule allow in Cilium's L7 DNS policies?**
   - A) Exact domain name matching
   - B) Domain name pattern matching with wildcards
   - C) IP address matching
   - D) Port number matching

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Domain name pattern matching with wildcards</p>
   <p><strong>Explanation</strong>: The matchPattern rule can match domain name patterns including wildcards (*). Example: *.example.com</p>
   </details>

9. **What component is required to apply Cilium's L7 policies?**
   - A) kube-proxy
   - B) Envoy proxy
   - C) NGINX ingress controller
   - D) HAProxy

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Envoy proxy</p>
   <p><strong>Explanation</strong>: Cilium uses the Envoy proxy to apply L7 policies.</p>
   </details>

10. **Which protocol is NOT supported by Cilium's L7 policies?**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) SMTP</p>
    <p><strong>Explanation</strong>: Cilium supports L7 protocols such as HTTP, gRPC, and Kafka, but SMTP is not supported by default.</p>
    </details>

## Encryption and Security

11. **Which protocols can be used for network traffic encryption in Cilium?**
    - A) IPsec
    - B) WireGuard
    - C) Both A and B
    - D) TLS

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) Both A and B</p>
    <p><strong>Explanation</strong>: Cilium can encrypt inter-node traffic using both IPsec and WireGuard.</p>
    </details>

12. **What traffic does Cilium's encryption feature protect?**
    - A) Inter-node traffic only
    - B) Inter-pod traffic only
    - C) Node-to-pod traffic only
    - D) All cluster traffic

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Inter-pod traffic only</p>
    <p><strong>Explanation</strong>: Cilium's encryption feature primarily protects inter-pod traffic.</p>
    </details>

13. **What does Cilium's Host Firewall feature protect?**
    - A) Pod network interfaces
    - B) Host network interfaces
    - C) Service endpoints
    - D) Container runtime

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Host network interfaces</p>
    <p><strong>Explanation</strong>: Cilium's Host Firewall protects the host's own network interfaces, enhancing host-level security.</p>
    </details>

14. **Which Cilium security feature matches this description? "Filters traffic based on specific fields or patterns of specific application layer protocols"**
    - A) Network policies
    - B) L7 policies
    - C) Encryption
    - D) Intrusion detection

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) L7 policies</p>
    <p><strong>Explanation</strong>: L7 (application layer) policies can filter traffic based on specific fields or patterns in protocols such as HTTP, gRPC, and Kafka.</p>
    </details>

15. **What is Cilium's Identity-based security model based on?**
    - A) Pod name
    - B) Node name
    - C) Labels
    - D) IP address

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) Labels</p>
    <p><strong>Explanation</strong>: Cilium's Identity is based on Pod labels, which allows consistent security policies to be applied even when IP addresses change.</p>
    </details>

## Visibility and Monitoring

16. **What is Hubble?**
    - A) Cilium's network visibility tool
    - B) Cilium's load balancer
    - C) Cilium's encryption protocol
    - D) Cilium's DNS server

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) Cilium's network visibility tool</p>
    <p><strong>Explanation</strong>: Hubble is Cilium's network visibility tool that can observe and analyze network flows based on eBPF.</p>
    </details>

17. **Which feature is NOT provided by Hubble UI?**
    - A) Service dependency map
    - B) Network flow visualization
    - C) Policy violation alerts
    - D) Code deployment management

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) Code deployment management</p>
    <p><strong>Explanation</strong>: Hubble UI provides service dependency maps, network flow visualization, and policy violation alerts, but does not provide code deployment management.</p>
    </details>

18. **What is the command to observe network flows for a specific Pod using Hubble CLI?**
    - A) `hubble observe --pod <pod-name>`
    - B) `hubble watch --pod <pod-name>`
    - C) `hubble monitor --pod <pod-name>`
    - D) `hubble inspect --pod <pod-name>`

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) <code>hubble observe --pod &lt;pod-name&gt;</code></p>
    <p><strong>Explanation</strong>: The <code>hubble observe --pod &lt;pod-name&gt;</code> command can observe network flows for a specific Pod in real-time.</p>
    </details>

19. **Which metric is NOT collected by Hubble?**
    - A) HTTP status codes
    - B) TCP connection status
    - C) Dropped packet count
    - D) Container CPU usage

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) Container CPU usage</p>
    <p><strong>Explanation</strong>: Hubble collects network-related metrics (HTTP status codes, TCP connection status, dropped packet count, etc.) but does not collect system metrics such as container CPU usage.</p>
    </details>

20. **How do you integrate Cilium with Prometheus?**
    - A) Add Prometheus annotations to Cilium Operator
    - B) Install Cilium plugin on Prometheus server
    - C) Create ServiceMonitor resource for Cilium
    - D) Import Cilium dashboard to Prometheus

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) Create ServiceMonitor resource for Cilium</p>
    <p><strong>Explanation</strong>: When using Prometheus Operator, you can collect Cilium metrics by creating a ServiceMonitor resource for Cilium.</p>
    </details>
