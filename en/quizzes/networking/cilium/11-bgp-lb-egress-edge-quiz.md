# Part 11: BGP Control Plane, Load Balancer IPs and Egress Quiz

> **Cilium 1.20.2 · 2026-10-15**

1. **On an EKS cluster using ENI IPAM, what does a `CiliumBGPAdvertisement` of type `PodCIDR` achieve?**
   - A) It advertises every ENI secondary IP as a /32 route to the peer
   - B) It programs the routes into the VPC route table
   - C) It advertises the VPC CIDR from each node
   - D) Nothing useful: ENI IPAM gives nodes no Cilium-owned PodCIDR, so there is no per-node prefix to advertise

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Nothing useful: ENI IPAM gives nodes no Cilium-owned PodCIDR, so there is no per-node prefix to advertise**

   `PodCIDR` advertisement only works with IPAM modes that allocate a PodCIDR per node (cluster-pool, Kubernetes host scope). With ENI, Pod IPs are VPC addresses already routed by the VPC, and the BGP Control Plane never programs cloud route tables.

   </details>

2. **How does a `CiliumBGPPeerConfig` choose which advertisements to send to a peer?**
   - A) By `families[].advertisements`, a label selector matched against the `metadata.labels` of `CiliumBGPAdvertisement` objects
   - B) By matching `advertisementType` in the peer's `families` entry
   - C) By listing advertisement names in `peerConfigRef`
   - D) By an annotation on the node

   <details>
   <summary>Show Answer</summary>

   **Answer: A) By `families[].advertisements`, a label selector matched against the `metadata.labels` of `CiliumBGPAdvertisement` objects**

   The ClusterConfig links to the PeerConfig by name, but the PeerConfig links to advertisements by labels on the advertisement object. If no advertisement matches, the session comes up and nothing is advertised.

   </details>

3. **A `LoadBalancer` Service is advertised by BGP with `externalTrafficPolicy: Local`. From which nodes is its VIP advertised?**
   - A) Only the node holding the Service's lease
   - B) Every node selected by the cluster config
   - C) Only nodes that have at least one local ready backend; the route follows the Pods
   - D) Only control-plane nodes

   <details>
   <summary>Show Answer</summary>

   **Answer: C) Only nodes that have at least one local ready backend; the route follows the Pods**

   With `Cluster` the VIP is advertised from all selected nodes. With `Local` it is withdrawn from nodes without a ready local endpoint. Leases belong to L2 announcements, not BGP.

   </details>

4. **After upgrading from Cilium 1.19 to 1.20, Grafana panels for BGP sessions are empty. Which change is the likely cause?**
   - A) The BGP metrics moved to the operator
   - B) The per-instance label `vrouter` is now `instance_name`, and the 1.20 upgrade notes do not mention it
   - C) BGP metrics are disabled unless `bgpControlPlane.metrics.enabled` is set
   - D) The metric prefix changed from `cilium_` to `bgp_`

   <details>
   <summary>Show Answer</summary>

   **Answer: B) The per-instance label `vrouter` is now `instance_name`, and the 1.20 upgrade notes do not mention it**

   The 1.19.8 metrics documentation uses `vrouter`; 1.20.2 uses `instance_name`. Queries and alerts that filter on the old label silently stop matching.

   </details>

5. **Two `CiliumBGPAdvertisement` objects match the same Service with different communities and different `localPreference` values (Cilium 1.18 and later). What is advertised?**
   - A) The union of the communities and the maximum `localPreference`
   - B) The attributes of the last advertisement applied
   - C) Only the first advertisement alphabetically
   - D) The route is withdrawn because of the conflict

   <details>
   <summary>Show Answer</summary>

   **Answer: A) The union of the communities and the maximum `localPreference`**

   "Last match wins" was the behavior before 1.18. Also remember `localPreference` is only sent to iBGP peers.

   </details>

6. **In which release were the v1 `CiliumBGPPeeringPolicy` and its control plane removed?**
   - A) 1.18
   - B) 1.20
   - C) 1.21
   - D) 1.19

   <details>
   <summary>Show Answer</summary>

   **Answer: D) 1.19**

   It was deprecated in 1.18 and removed together with `pkg/bgpv1` in 1.19, so clusters must migrate to the `cilium.io/v2` CRDs before upgrading to 1.19. The v2alpha1 copies of the v2 CRDs remain served but deprecated in 1.20 and 1.21-pre.

   </details>

7. **How should you handle fast failure detection on a multi-hop BGP session in Cilium 1.20?**
   - A) Enable BFD in `CiliumBGPPeerConfig.spec.bfd`
   - B) BFD is not supported; lower the hold and keepalive timers (CRD minimums 3 and 1) and use Graceful Restart for agent restarts
   - C) Set `ebgpMultihop` to 255, which enables fast failover
   - D) Use `connectRetryTimeSeconds: 1`

   <details>
   <summary>Show Answer</summary>

   **Answer: B) BFD is not supported; lower the hold and keepalive timers (CRD minimums 3 and 1) and use Graceful Restart for agent restarts**

   There is no BFD field in any 1.18 to 1.21-pre CRD. The commonly cited 9/3 timers are a recommended aggressive setting, not the CRD minimum. `ebgpMultihop` only sets the TTL; connect-retry affects reconnection, not failure detection.

   </details>

8. **You have existing `TLSRoute` objects at `v1alpha2` and plan to upgrade to Cilium 1.20 (Gateway API v1.6.1). What must you do?**
   - A) Nothing; the standard-channel CRDs convert objects automatically
   - B) Delete the TLSRoutes and recreate them after the upgrade
   - C) Back up the TLSRoutes and install the experimental-channel v1.6.1 TLSRoute CRD (which still includes `v1alpha2`) before upgrading Cilium
   - D) Install only the standard-channel v1.6 TLSRoute CRD, which keeps all versions

   <details>
   <summary>Show Answer</summary>

   **Answer: C) Back up the TLSRoutes and install the experimental-channel v1.6.1 TLSRoute CRD (which still includes `v1alpha2`) before upgrading Cilium**

   Installing the standard-channel v1.6 TLSRoute CRD makes stored `v1alpha2` objects unreadable, so they appear to disappear.

   </details>

9. **With default L2 announcement lease settings (15s duration, 5s renew deadline, 2s retry), what is the approximate failover window?**
   - A) 2 to 4 seconds
   - B) Exactly 15 seconds
   - C) 30 to 60 seconds
   - D) 10 to 20 seconds

   <details>
   <summary>Show Answer</summary>

   **Answer: D) 10 to 20 seconds**

   Failover falls between `leaseDuration - leaseRenewDeadline` and `leaseDuration + leaseRenewDeadline`. Tuning to 3s/1s/200ms gives 2 to 4 seconds but raises API QPS, so raise the client rate limit.

   </details>

10. **A `CiliumEgressGatewayPolicy` has an `egressGateway.nodeSelector` that matches no node. What happens to traffic from the selected Pods to the destination CIDRs?**
    - A) It is dropped
    - B) It is sent through a random node
    - C) It falls back to normal node masquerade
    - D) It is queued until a gateway appears

    <details>
    <summary>Show Answer</summary>

    **Answer: A) It is dropped**

    Egress Gateway has no health-based failover or fallback in 1.20.2 or 1.21.0-pre.3. With no matching gateway the traffic to the destination CIDRs is dropped.

    </details>
