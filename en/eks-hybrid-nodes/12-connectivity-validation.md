# Validating Pod Connectivity Without SNAT, and PrivateLink

> **Supported Versions**: EKS 1.36, Cilium 1.18.13 (AWS build), CoreDNS add-on v1.14.7-eksbuild.10, default VPC CNI configuration
> **Last Updated**: October 19, 2026

Some firewalls must identify on-premises Pods by **Pod IP**, not by node IP. This page records a test of that requirement: Cilium was switched to native routing with masquerading disabled, and 38 connectivity checks inside and outside the cluster were run. It also covers the PrivateLink path that lets on-premises Pods call AWS APIs (STS, S3) without going through the internet, and how DNS behaves when the link goes down.

The test environment **simulates on-premises**. A second VPC is attached through a Transit Gateway (TGW) and its EC2 instances are registered as hybrid nodes. Running hybrid nodes on EC2 is not supported and is billed at the hybrid node rate. The numbers come from a single run on October 19, 2026. Re-validate them on a real on-premises network over Direct Connect or VPN.

## Support Scope First

In the "Supported capabilities" table of [Configure CNI for hybrid nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html), the only Cilium **Networking Mode supported by AWS is "VXLAN encapsulation"**. The same page explains that masquerading can be disabled, in which case Pod CIDRs must be routable on the on-premises network, and recommends the Cilium BGP Control Plane to make them routable.

| Configuration | Where Pod IPs are visible | AWS support | Hybrid Nodes Gateway |
|---|---|---|---|
| VXLAN + masquerade (default) | Nowhere outside the cluster: node IP | Supported | Usable |
| VXLAN + masquerade off + BGP | Cloud to on-premises, on-premises servers | Supported | Usable |
| **Native routing + masquerade off** (this page) | The above, **plus the hybrid-node-to-hybrid-node segment** | **Outside the supported scope** | Not usable (needs VTEP, that is, VXLAN) |

With VXLAN, traffic between hybrid nodes carries the node IP in the outer header, so a firewall on that segment cannot see Pod IPs. The choice depends on whether you need Pod IPs on that segment too. The second row, which stays in the supported scope, is enough for most cases. Consider the third row only if you have commercial Cilium support or in-house expertise instead of AWS support.

## Configuration

### Address Ranges

| Range | Value | Notes |
|---|---|---|
| Cloud VPC | `10.0.0.0/16` | Cloud nodes and Pods (VPC CNI) |
| Remote node network | `172.18.0.0/16` | Simulated on-premises VPC (hybrid node hosts) |
| Remote pod network | `172.17.0.0/16` | Cilium cluster-pool, `/25` per node |
| Service | `172.16.0.0/16` | |

### Cilium Values (overlay on the base values)

```yaml
routingMode: native
ipv4NativeRoutingCIDR: "172.17.0.0/16"   # remote pod network
autoDirectNodeRoutes: false              # hosts are in different subnets; the on-prem router forwards
enableIPv4Masquerade: false              # no SNAT
vtep:
  enabled: false                         # no gateway
```

The Cilium chart does not restart the agents when the ConfigMap changes (`rollOutCiliumPods` defaults to `false`), so run `kubectl -n kube-system rollout restart ds/cilium` after changing values. Afterwards, check that `cilium-dbg status` shows `Routing: Network: Native`. The ConfigMap still contains `tunnel-protocol: vxlan`, which had no effect: a capture on the host NIC showed zero VXLAN packets (UDP 8472 and 4789).

### Routing and SNAT Exceptions

| Where | Setting | Why |
|---|---|---|
| On-premises router | Each node's Pod block (`/25`) to that node | In production, advertise with the Cilium BGP Control Plane. The test used static routes in the on-premises VPC route table; they go stale when a node rejoins and gets a different Pod block. |
| Cloud route tables, TGW | `172.17.0.0/16` toward on-premises | Return traffic reaches Pod IPs directly |
| VPC CNI | `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS=172.17.0.0/16,172.18.0.0/16` | Cloud Pods keep their IP toward on-premises too. **Without the node range (172.18), on-premises servers see the cloud node IP.** |
| Cluster security group | All of `172.17.0.0/16`, UDP/TCP 53 from `172.18.0.0/16` | Pod traffic, and DNS from hostNetwork Pods (which call CoreDNS from the node IP) |

## Connectivity Matrix Results

Each check verified not just the HTTP response but **the source address the server recorded**: the nginx access log (`$remote_addr`), or for the server outside Kubernetes, a `socat` listener that echoes the peer address. Result: 38 PASS, 0 FAIL.

| Segment | Checks | What was checked | Result |
|---|---|---|---|
| Pod to Pod, direct | 7 | Same hybrid node, between hybrid nodes, hybrid and cloud in both directions, cloud to cloud | Source seen by the server = client Pod IP |
| ClusterIP Service | 3 | Hybrid to hybrid backend, hybrid to cloud backend, cloud to hybrid backend | kube-proxy rewrites only the destination; the source Pod IP is kept |
| DNS | 4 | Service names from two hybrid Pods and a hostNetwork Pod, a public name | Resolved through CoreDNS (cloud nodes) and the VPC resolver |
| Kubernetes API | 2 | `kubernetes.default.svc/livez`, ServiceAccount token | 200, and 403 (authenticated, no RBAC grant) |
| Control plane to hybrid | 3 | API server proxy (webhook path), `exec` and `logs`, metrics-server | Proxy requests come from an EKS-managed ENI in the cloud VPC |
| On-premises server outside Kubernetes | 2 | Hybrid Pod and cloud Pod to `socat` on a hybrid host | The server received the 172.17.x and 10.0.x Pod IPs |
| Internet | 3 | Two hybrid Pods, one cloud Pod | All leave through the single cloud NAT gateway, the only address translation on the path |
| Cilium policy | 3 | `fromCIDR: 10.0.0.0/16` on a hybrid Pod | Hybrid Pod blocked, cloud Pod allowed, restored after deletion |
| MTU, bulk transfer | 2 | 32 MiB in both directions, sha256 compared | Match. Pod MTU 9001, DF ping with 8500-byte packets passes |
| ALB IP targets | 1 | Two hybrid Pods | Healthy |
| PrivateLink | 8 | See below | All PASS |

The working `fromCIDR` policy is also evidence of no SNAT. Cloud Pods use VPC CNI and have no Cilium identity, so policies can only match them by IP range, which works only if the Pod IP arrives unchanged.

Pod MTU is 9001 and the TGW limit is 8500. TCP was fine because the TGW clamps the MSS. Check path MTU separately for protocols without MSS clamping, such as UDP, and for DX or VPN paths.

### Three Failures on the First Run

| Symptom | Cause | Fix |
|---|---|---|
| hostNetwork Pod cannot resolve Service names | hostNetwork Pods call CoreDNS from the node IP (172.18.x), and the cluster SG had no port 53 rule for that range | Allow UDP and TCP 53 from `172.18.0.0/16` in the cluster SG |
| On-premises server sees a node IP from cloud Pods | The VPC CNI SNAT exclusion list had the Pod range but not the on-premises node range | Add `172.18.0.0/16` to `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS` |
| Anonymous `GET /version` returns 401 | EKS 1.36 allows anonymous requests only to health endpoints | Use `/livez` or `/readyz` for reachability checks |

## Calling AWS APIs from On-Premises Pods over PrivateLink

To keep on-premises Pods off the internet when they call AWS APIs, place interface endpoints in the cloud VPC and reach them over DX or VPN.

```
hybrid Pod (172.17.x)
  -> CoreDNS -> VPC resolver: sts.<region>.amazonaws.com and s3.<region>.amazonaws.com resolve to endpoint ENIs (10.0.x)
  -> TGW (DX/VPN in production), source Pod IP preserved
  -> STS and S3 interface endpoints (2 AZs, private DNS)
```

Hybrid Pods resolve names through cluster DNS (CoreDNS) and then the VPC resolver, so the endpoints' private DNS applies as is. On-premises servers outside Kubernetes need a [Route 53 Resolver inbound endpoint](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-inbound-queries.html) to get the same answers.

### Components

| Component | Setting |
|---|---|
| STS interface endpoint | Private DNS enabled |
| S3 interface endpoint | Private DNS enabled. **In a VPC without an S3 gateway endpoint, set `DnsOptions.PrivateDnsOnlyForInboundResolverEndpoint: AllResolvers`.** The first attempt without it failed with "To set PrivateDnsOnlyForInboundResolverEndpoint to true, the VPC must have a Gateway endpoint". |
| Endpoint security group | TCP 443 only from `10.0.0.0/16` (VPC) and `172.17.0.0/16` (hybrid Pods). The node range `172.18.0.0/16` is deliberately left out |
| IAM | Cluster OIDC provider, a role bound to the ServiceAccount (IRSA) |
| Bucket policy | The test role is allowed only when `aws:SourceVpce` is the S3 endpoint |

An S3 gateway endpoint [cannot be used from on-premises](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html); on-premises Pods need the interface endpoint.

The bucket policy below blocks only the test role outside the endpoint. Other principals, such as operators, are not affected.

```json
{
  "Sid": "TestRoleOnlyThroughEndpoint",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::<bucket>", "arn:aws:s3:::<bucket>/*"],
  "Condition": {
    "StringNotEquals": {"aws:SourceVpce": "<s3-endpoint-id>"},
    "ArnEquals": {"aws:PrincipalArn": "<test-role-arn>"}
  }
}
```

### IRSA and Pod Identity

With IRSA the Pod calls STS `AssumeRoleWithWebIdentity` itself with its projected token, so the token exchange already goes through the STS endpoint. Create the cluster OIDC provider first if it does not exist. Setting `AWS_STS_REGIONAL_ENDPOINTS=regional` in the Pod `env` makes the SDK use the regional STS name, which the private DNS covers.

EKS Pod Identity needs [extra setup](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html) on hybrid nodes: `enableCredentialsFile` in the nodeadm configuration and the Pod Identity Agent add-on configuration `{"daemonsets":{"hybrid":{"create":true}}}`. The default agent DaemonSet in the test cluster excluded hybrid nodes, so this test used IRSA.

### Results (all 8 PASS)

| Check | Result |
|---|---|
| Resolve `sts`, `s3` and the bucket host name from a hybrid Pod | All return endpoint ENI addresses (10.0.x) |
| Hybrid Pod: `sts get-caller-identity` (IRSA) | Assumed-role ARN returned; the token exchange used the STS endpoint |
| Hybrid Pod: `PutObject` | Succeeds. The bucket policy blocks this role outside the endpoint, so the request went through it |
| Cloud Pod: `GetObject` of the same object | Same content |
| STS ENI:443 from a Pod and a hostNetwork Pod on the same node | Pod (172.17.x) gets HTTP 302, hostNetwork (172.18.x) times out |
| Same role from outside the endpoint (workstation) | Denied by the `aws:SourceVpce` condition |

The Pod passed and the hostNetwork Pod was blocked even though both left the same node. **Security groups on the AWS side can also tell on-premises Pods apart by the Pod range**, which is the most direct evidence that there is no SNAT.

## What Happens to DNS When the Link Goes Down

A DX or VPN outage was reproduced for about 95 seconds by adding blackhole routes (`/17` for the on-premises node and Pod ranges) to the TGW route table. The route change took about 17 seconds to take effect. On each hybrid node, a probe Pod resolved an on-premises Service name and a cloud Service name every second, then called the on-premises Service by name and by ClusterIP. During the outage the hybrid nodes went `NotReady` while their Pods kept running (the probe logs have no gaps); in the first run they were `Ready` again about 23 seconds after the link came back.

| Configuration | Name resolution on hybrid Pods during the outage | Calls to the on-premises Service | Notes |
|---|---|---|---|
| Default: both CoreDNS replicas on cloud nodes | **Every lookup fails** (26 of 43 to 44 samples failed) | ClusterIP returns 200, by name fails | Traffic inside on-premises still works, names do not |
| Zone label + 3 replicas + `PreferSameZone` (differs from the docs example) | About half fail (38 to 44 of 76 to 80) | Calls by name fail intermittently | Cilium ignores the hints and still balances to the unreachable cloud CoreDNS |
| Zone label + 4 replicas + **`PreferClose`** + enforced zone spread + Cilium restart | **0 failures** (all 96 to 97 samples) | By name and ClusterIP both 200 | Cloud Pods resolve fine; only their calls to on-premises fail, as expected |

The causes found at each step:

1. **Use the value in the AWS docs, `PreferClose`. Cilium did not act on `PreferSameZone`.** The AWS example uses `trafficDistribution: PreferClose`. The test used the newer name `PreferSameZone` because `PreferClose` became a deprecated alias in Kubernetes 1.35, and that caused the half failure rate. On hybrid nodes, ClusterIP load balancing is done by Cilium BPF, not kube-proxy, even with `kubeProxyReplacement: false`. The EndpointSlice had zone hints, yet `cilium-dbg bpf lb list` kept all three CoreDNS backends. With `trafficDistribution: PreferClose` only the two on-premises backends remained. The EndpointSlice hints look the same for both values, so check the backend list in Cilium on a hybrid node.
2. **Set the zone label at join time.** The test added the label later and then restarted Cilium with `kubectl -n kube-system rollout restart ds/cilium`; whether it takes effect without a restart was not checked. Joining with kubelet `--node-labels=topology.kubernetes.io/zone=<name>` in the nodeadm configuration avoids the question.
3. **Cloud AZs without CoreDNS are a problem too.** A cloud Pod whose zone has no CoreDNS is balanced across all backends, and queries that land on the on-premises CoreDNS fail during an outage. Run one replica per cloud AZ and at least one on-premises.
4. **Preferred anti-affinity did not guarantee placement.** After a CoreDNS restart, the on-premises replicas once dropped to one. `topologySpreadConstraints` with `whenUnsatisfiable: DoNotSchedule` enforces at least one replica per zone.
5. **CoreDNS on hybrid nodes bypasses PrivateLink.** It forwards to the node's resolver (on-premises DNS), so `sts` and `s3` resolved to public addresses. The calls still succeed through NAT and look healthy, but S3 requests were denied by the `aws:SourceVpce` bucket policy and four matrix checks failed. The fix was a Route 53 Resolver inbound endpoint in the cloud VPC plus an `amazonaws.com` block in CoreDNS. On a real network, a conditional forwarder on the on-premises DNS servers does the same.

Final CoreDNS add-on configuration values (`aws eks update-addon --configuration-values`):

```json
{
  "replicaCount": 4,
  "trafficDistribution": "PreferClose",
  "topologySpreadConstraints": [{
    "maxSkew": 1, "topologyKey": "topology.kubernetes.io/zone", "whenUnsatisfiable": "DoNotSchedule",
    "labelSelector": {"matchLabels": {"k8s-app": "kube-dns"}}
  }],
  "corefile": "...default .:53 block...\namazonaws.com:53 {\n    errors\n    cache 30\n    forward . <inbound endpoint IP 1> <inbound endpoint IP 2>\n}"
}
```

The `corefile` value replaces the whole Corefile, so it must include the default `.:53` block. After the Corefile change, one CoreDNS replica on a hybrid node picked up the ConfigMap late and answered with the old configuration for a while; `rollout restart deploy/coredns` fixed it. The inbound endpoint SG opens port 53 only to the VPC range and the hybrid Pod range. During an outage the inbound endpoint is unreachable too, so AWS API names do not resolve, but the endpoints themselves are unreachable then anyway.

## What to Watch in Operations

- **CoreDNS placement**: AWS recommends at least one CoreDNS replica on hybrid nodes and one on cloud nodes in a mixed mode cluster ([Configure CoreDNS replicas](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)). As measured above, the zone label, zone spread, `trafficDistribution` and Cilium `loadBalancer.serviceTopology: true` must all be right for it to help during an outage. Cut the link for real to verify after changing it.
- **Webhooks and control plane paths**: API server proxy requests came from an EKS-managed ENI in the cloud VPC. To run webhooks on hybrid nodes, Pod CIDRs must be routable and the on-premises firewall must allow the VPC range that holds those ENIs.
- **Static route drift**: A rejoined node can get a different Pod block. Without BGP, you need a step that reconciles routes after each join.
- **Internet egress**: This setup sent the on-premises default route to the cloud, so everything left through one NAT gateway. If on-premises uses its own internet path, that path's NAT and firewall policy must know the Pod range.
- **Cost**: Interface endpoints are billed per hour per AZ and per GB processed.

## Quiz

* [Pod Connectivity Without SNAT and PrivateLink Quiz](../quizzes/eks-hybrid-nodes/12-connectivity-validation-quiz.md)

## References

* [Configure CNI for hybrid nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html): supported networking mode, masquerading, BGP recommendation
* [Prepare networking for hybrid nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Configure webhooks for hybrid nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html): CoreDNS replica placement
* [Configure add-ons for hybrid nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html): Pod Identity Agent
* [Best practices for stability through network disconnections](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
* [AWS PrivateLink for Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
* [Access AWS services through AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-aws-services.html)
* [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md), [Network Configuration](02-network-configuration.md), [Network Separation Security Review](11-network-separation-security.md)
