# Pod Connectivity Without SNAT and PrivateLink Quiz

> **Last Updated**: October 19, 2026

[Study guide: Validating Pod Connectivity Without SNAT, and PrivateLink](../../eks-hybrid-nodes/12-connectivity-validation.md)

1. Which Cilium networking mode does AWS support for EKS Hybrid Nodes?
   - A) Native routing only
   - B) VXLAN encapsulation only
   - C) Both VXLAN and native routing

<details>
<summary>Show Answer</summary>

**Answer: B) VXLAN encapsulation only**

**Explanation:**
The Supported capabilities table in Configure CNI for hybrid nodes lists VXLAN encapsulation as the networking mode. Native routing is outside the supported scope, and the Hybrid Nodes Gateway needs VTEP (VXLAN), so it cannot be used with native routing.

</details>

2. You keep VXLAN, disable masquerading and advertise Pod CIDRs with Cilium BGP. On which segment can a firewall still not see Pod IPs?
   - A) Between cloud Pods and on-premises Pods
   - B) Toward on-premises servers outside Kubernetes
   - C) Between hybrid nodes

<details>
<summary>Show Answer</summary>

**Answer: C) Between hybrid nodes**

**Explanation:**
Traffic between hybrid nodes is encapsulated in VXLAN, and the outer header carries the node IP. Traffic leaving the cluster keeps the Pod IP once masquerading is off.

</details>

3. After switching to native routing, an on-premises server sees a cloud node IP when a cloud Pod calls it. What do you check first?
   - A) Whether the VPC CNI `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS` includes the on-premises node range
   - B) Cilium's `enableIPv4Masquerade` value
   - C) The default route in the TGW route table

<details>
<summary>Show Answer</summary>

**Answer: A) Whether the VPC CNI `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS` includes the on-premises node range**

**Explanation:**
SNAT for cloud Pods is done by VPC CNI, not Cilium. If the exclusion list has only the Pod range (172.17.0.0/16) and not the on-premises node range (172.18.0.0/16), traffic to on-premises servers is translated to the node IP.

</details>

4. Only hostNetwork Pods fail to resolve cluster Service names; regular hybrid Pods are fine. What is the most likely cause?
   - A) CoreDNS is not on hybrid nodes
   - B) hostNetwork Pods call CoreDNS from the node IP, and the cluster SG does not allow port 53 from the node range
   - C) hostNetwork Pods cannot use DNS

<details>
<summary>Show Answer</summary>

**Answer: B) hostNetwork Pods call CoreDNS from the node IP, and the cluster SG does not allow port 53 from the node range**

**Explanation:**
Regular Pods leave with their Pod IP (172.17.x); hostNetwork Pods leave with the node IP (172.18.x). Allow UDP and TCP 53 from `172.18.0.0/16` in the cluster SG. `dnsPolicy: ClusterFirstWithHostNet` is also required.

</details>

5. On-premises Pods should reach S3 over a private path. Which statement is correct?
   - A) An S3 gateway endpoint also works from on-premises.
   - B) An S3 interface endpoint is needed; without a gateway endpoint, the test had to set `DnsOptions` to `AllResolvers`.
   - C) S3 does not support PrivateLink.

<details>
<summary>Show Answer</summary>

**Answer: B) An S3 interface endpoint is needed; without a gateway endpoint, the test had to set `DnsOptions` to `AllResolvers`.**

**Explanation:**
Gateway endpoints cannot be used from on-premises. In the test, the first creation without `PrivateDnsOnlyForInboundResolverEndpoint` failed with an error saying the VPC must have a gateway endpoint.

</details>

6. The endpoint SG allows TCP 443 only from `172.17.0.0/16` (the Pod range). What happens when a regular Pod and a hostNetwork Pod on the same hybrid node call the STS endpoint?
   - A) Both succeed.
   - B) Both fail.
   - C) The regular Pod succeeds and the hostNetwork Pod times out.

<details>
<summary>Show Answer</summary>

**Answer: C) The regular Pod succeeds and the hostNetwork Pod times out.**

**Explanation:**
Without SNAT, the regular Pod's source is its Pod IP and the hostNetwork Pod's source is the node IP (172.18.x). Security groups on the AWS side can therefore tell on-premises Pods apart by the Pod range.

</details>

7. In the test on a Kubernetes 1.36, Cilium 1.18 mixed mode cluster, which kube-dns Service setting kept hybrid Pods on the on-premises CoreDNS during a link outage?
   - A) `trafficDistribution: PreferClose`
   - B) `externalTrafficPolicy: Local`
   - C) `sessionAffinity: ClientIP`

<details>
<summary>Show Answer</summary>

**Answer: A) `trafficDistribution: PreferClose`**

**Explanation:**
ClusterIP load balancing on hybrid nodes is done by Cilium BPF, and the tested Cilium 1.18.13 ignored `PreferSameZone`. The AWS docs example also uses `PreferClose`. It is a deprecated alias since Kubernetes 1.35, yet it was the only value that worked here. A zone label set at join time, CoreDNS in every zone and Cilium `loadBalancer.serviceTopology: true` are also required.

</details>
