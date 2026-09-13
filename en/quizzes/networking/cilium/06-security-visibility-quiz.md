# Cilium Security and Visibility Quiz

> **Review baseline**: Cilium 1.20.1; Hubble CLI 1.19.4.
> **Last reviewed**: September 12, 2026.

[Return to the guide](../../../networking/cilium/06-security-visibility.md)

## Network Policy Basics

1. **How does CiliumNetworkPolicy extend standard Kubernetes NetworkPolicy?**

   - A) It cannot select Pods
   - B) It can add supported L7 protocol rules
   - C) It only protects nodes
   - D) It guarantees lower latency

   <details>
   <summary>Show Answer</summary>

   **Answer: B) It can add supported L7 protocol rules**

   Standard NetworkPolicy controls L3/L4 connectivity. Cilium adds capabilities such as HTTP and DNS policy; performance is not guaranteed by the API choice.

   </details>

2. **Which API version is used for CiliumNetworkPolicy?**

   - A) networking.k8s.io/v1
   - B) cilium.io/v2
   - C) policy.cilium.io/v1
   - D) network.cilium.io/v1

   <details>
   <summary>Show Answer</summary>

   **Answer: B) cilium.io/v2**

   The group is cilium.io and the served policy version used in this chapter is v2.

   </details>

3. **What does endpointSelector select in a namespaced CiliumNetworkPolicy?**

   - A) Matching endpoints in the policy namespace
   - B) All Kubernetes nodes
   - C) The Prometheus server
   - D) Only LoadBalancer Services

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Matching endpoints in the policy namespace**

   It identifies the endpoints governed by the policy. Node policies use the separate clusterwide nodeSelector mechanism.

   </details>

4. **For a standard NetworkPolicy with policyTypes: [Ingress], which value contains no ingress allow rules?**

   - A) ingress: [{}]
   - B) ingress: []
   - C) ingress: [{from: [{}]}]
   - D) An allow rule for all source addresses

   <details>
   <summary>Show Answer</summary>

   **Answer: B) ingress: []**

   An empty list supplies no allow rule; an empty rule object allows all ingress. Other applicable allow policies remain additive.

   </details>

5. **Which direction does egress policy control for selected Pods?**

   - A) Incoming connections only
   - B) Outgoing connections
   - C) Only traffic inside a process
   - D) Only the API server's responses

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Outgoing connections**

   Egress controls outbound connectivity. An isolated Pod needs explicit allowances for dependencies such as its real DNS resolver.

   </details>

## L7 Policies

6. **Which is not a request match field in Cilium HTTP policy?**

   - A) Path
   - B) Method
   - C) Headers
   - D) Response latency

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Response latency**

   HTTP policy matches supported request attributes. Observing response duration does not make latency an HTTP allow-rule field.

   </details>

7. **What is needed for the illustrated toFQDNs policy to learn DNS answers?**

   - A) Only a TCP 443 rule
   - B) Only an arbitrary external IP
   - C) A reachable resolver and matching DNS proxy rules
   - D) A Kafka topic rule

   <details>
   <summary>Show Answer</summary>

   **Answer: C) A reachable resolver and matching DNS proxy rules**

   DNS allowance/proxy observation and subsequent destination-IP allowance are distinct. The example covers UDP and TCP DNS to verified resolver endpoints.

   </details>

8. **What does DNS matchPattern provide?**

   - A) Port allocation
   - B) Domain-name wildcard matching
   - C) JWT signature validation
   - D) Automatic malicious-domain reputation

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Domain-name wildcard matching**

   It matches query/domain names with supported wildcard syntax. It does not fetch a threat-intelligence feed.

   </details>

9. **Which proxy implements the HTTP rules discussed here?**

   - A) kube-proxy
   - B) Envoy
   - C) Prometheus
   - D) Hubble Relay

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Envoy**

   Cilium integrates Envoy for HTTP policy. DNS policy uses the DNS proxy, so not every L7 rule should be described as an Envoy rule.

   </details>

10. **Which former Cilium L7 policy capability is absent from the current API?**

   - A) HTTP method matching
   - B) HTTP path matching
   - C) Kafka topic rules
   - D) DNS name rules

   <details>
   <summary>Show Answer</summary>

   **Answer: C) Kafka topic rules**

   Kafka L7 policy was removed. Do not copy the old kafka rules into current CiliumNetworkPolicy resources.

   </details>

## Encryption and Security

11. **Which pair names alternative Cilium node transport encryption modes?**

   - A) IPsec and WireGuard
   - B) HTTP and DNS
   - C) Relay and Grafana
   - D) SYN and ACK

   <details>
   <summary>Show Answer</summary>

   **Answer: A) IPsec and WireGuard**

   Select the required mode and its prerequisites. SPIRE mutual authentication and Beta ztunnel workload mTLS are separate features with different scope.

   </details>

12. **What is covered by the chapter's default WireGuard node-tunnel profile?**

   - A) Every packet, including arbitrary external traffic
   - B) Supported Cilium-managed Pod traffic crossing nodes
   - C) All same-node Pod traffic through the tunnel
   - D) All host traffic without exceptions

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Supported Cilium-managed Pod traffic crossing nodes**

   Same-node traffic does not use these node tunnels. Node-to-node encryption is a separate Beta option with control-plane exclusions; application TLS may still be required.

   </details>

13. **What is Cilium Host Firewall intended to protect?**

   - A) Only browser JavaScript
   - B) The host's network traffic
   - C) All container syscalls automatically
   - D) A Grafana password database

   <details>
   <summary>Show Answer</summary>

   **Answer: B) The host's network traffic**

   Host policy is a network control. Runtime process/syscall enforcement belongs to separate mechanisms such as configured Tetragon policies; encryption compatibility must be checked.

   </details>

14. **Does matching an Authorization header authenticate its bearer?**

   - A) Yes, any present header is a verified JWT
   - B) Yes, a regex-looking value verifies signatures
   - C) No; header matching does not validate the token
   - D) Yes, if HTTP uses port 8443

   <details>
   <summary>Show Answer</summary>

   **Answer: C) No; header matching does not validate the token**

   Use actual authentication/authorization logic. A valued headers string is literal matching, and a TLS port number does not decrypt the payload.

   </details>

15. **What primarily determines a Cilium security identity?**

   - A) A guaranteed unique Pod IP forever
   - B) The security-relevant label set
   - C) The user's browser cookie
   - D) The last observed HTTP response

   <details>
   <summary>Show Answer</summary>

   **Answer: B) The security-relevant label set**

   Endpoints sharing security-relevant labels can share an identity. Identity-based policy alone does not provide end-user authentication or traffic encryption.

   </details>

## Visibility and Monitoring

16. **What is Hubble's main role?**

   - A) Network-flow observability
   - B) Container image deployment
   - C) A complete WAF without rules
   - D) Automatic isolation of every suspicious Pod

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Network-flow observability**

   Hubble exposes flow metadata, verdicts and supported protocol observations. Detection rules and response integrations require separate configuration.

   </details>

17. **Which is a Hubble UI capability?**

   - A) Rotating application credentials
   - B) Service dependency maps and flow exploration
   - C) Automatically sending Slack incidents
   - D) Installing runtime syscall policies

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Service dependency maps and flow exploration**

   The UI visualizes network observations through Relay. It is not a notification, deployment or runtime-policy controller.

   </details>

18. **Which command follows flow events for either endpoint matching the frontend Pod?**

   - A) `hubble observe --pod cilium-security-demo/frontend --follow`
   - B) `hubble watch --pod frontend`
   - C) `cilium hubble status`
   - D) `hubble observe --pod app=frontend`

   <details>
   <summary>Show Answer</summary>

   **Answer: A) `hubble observe --pod cilium-security-demo/frontend --follow`**

   Use a namespace-qualified Pod name and --follow for a stream. Pod names are not label selectors; directional and label filters are separate flags.

   </details>

19. **Which is not supplied by the illustrated Hubble metric plugins?**

   - A) HTTP response status counts
   - B) TCP flag counts
   - C) Observed drop counts
   - D) Container CPU usage

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Container CPU usage**

   Those plugins observe network/proxy events. The TCP plugin does not provide a general concurrent-connection or RTT metric, and missing/lost observations must be considered.

   </details>

20. **With Prometheus Operator installed, what is needed to scrape Hubble through ServiceMonitor?**

   - A) Only importing a Grafana dashboard
   - B) A static public hubble-metrics.cilium.io:9091 target
   - C) Enabled metrics and a ServiceMonitor selected by Prometheus
   - D) Only creating an unrelated ConfigMap

   <details>
   <summary>Show Answer</summary>

   **Answer: C) Enabled metrics and a ServiceMonitor selected by Prometheus**

   The chart's headless Service exposes the named hubble-metrics port, normally 9965. Prometheus namespace/label selectors and endpoint reachability must match.

   </details>
