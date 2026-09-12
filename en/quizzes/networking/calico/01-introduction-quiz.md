# Calico Introduction Quiz

> **Related Document**: [Calico Introduction](../../../networking/calico/01-introduction.md)
> **Last Updated**: September 12, 2026

## Quiz

1. In what year was Project Calico originally started?
   - A) 2012
   - B) 2014
   - C) 2016
   - D) 2018

<details>
<summary>Show Answer</summary>

**Answer: B) 2014**

**Explanation:**
Project Calico's origins are in 2014 at Metaswitch. Tigera was formed in 2016. Do not conflate the project's origin with later product launches or Calico release dates.

</details>

2. Which company is Calico's primary maintainer and supplies Calico Enterprise and Cloud?
   - A) Google
   - B) Red Hat
   - C) Tigera
   - D) VMware

<details>
<summary>Show Answer</summary>

**Answer: C) Tigera**

**Explanation:**
Tigera maintains Calico with community contributors and supplies commercial offerings. “Metaswitch founders” is a description of people, not the name of the company being asked for. A CNCF Landscape listing does not mean CNCF governs the project.

</details>

3. Which statement is NOT true of the default Calico installation?
   - A) BGP-based routing
   - B) It automatically injects Istio sidecars into every Pod
   - C) Kubernetes standard and extended network policies
   - D) Support for eBPF dataplane

<details>
<summary>Show Answer</summary>

**Answer: B) It automatically injects Istio sidecars into every Pod**

**Explanation:**
Calico provides networking, policy and selectable data planes. Mesh integrations are separate capabilities/configuration, not automatic injection of Istio sidecars by this lab's installation. Cilium mesh functions also require their own configuration; a CNI comparison should not imply that every mesh feature is enabled by default.

</details>

4. What can an unencapsulated Calico topology with correctly configured BGP and underlay routes provide?
   - A) Simpler configuration
   - B) Better security encryption
   - C) Routing without overlay encapsulation headers, where the underlay supports Pod routes
   - D) Built-in DNS resolution

<details>
<summary>Show Answer</summary>

**Answer: C) Routing without overlay encapsulation headers, where the underlay supports Pod routes**

**Explanation:**
BGP distributes routes. If the underlay can route Pod addresses and encapsulation is disabled, packets need no IPIP/VXLAN wrapper. BGP can also coexist with IPIP, so enabling BGP alone does not remove encapsulation. It neither encrypts traffic nor guarantees lower latency for every workload.

</details>

5. Across which environments can the appropriate Calico configurations and product editions be used?
   - A) Cloud only
   - B) On-premises only
   - C) Cloud, on-premises, and hybrid
   - D) Kubernetes only, no VM support

<details>
<summary>Show Answer</summary>

**Answer: C) Cloud, on-premises, and hybrid**

**Explanation:**
Calico has cloud, on-premises and hybrid use cases, but platform/kernel/data-plane and edition limitations still apply. GKE Dataplane V2 specifically uses Cilium rather than Calico. VM and Windows capabilities are not identical to Linux Kubernetes capabilities.

</details>

6. Which list includes supported Calico Linux data-plane choices?
   - A) iptables only
   - B) eBPF only
   - C) iptables, nftables and eBPF
   - D) IPVS only

<details>
<summary>Show Answer</summary>

**Answer: C) iptables, nftables and eBPF**

**Explanation:**
Calico supports these Linux data-plane choices. Encapsulation modes such as VXLAN/IPIP are a different choice, and IPVS is a kube-proxy backend rather than a complete Calico data plane. Select using kernel, platform and feature requirements; the lab explicitly uses iptables.

</details>

7. What is calicoctl?
   - A) A graphical user interface for Calico
   - B) A command-line tool for managing Calico resources
   - C) A Kubernetes operator for Calico
   - D) A monitoring dashboard

<details>
<summary>Show Answer</summary>

**Answer: B) A command-line tool for managing Calico resources**

**Explanation:**
calicoctl manages Calico resources and offers diagnostics such as IPAM/BGP operations. Use a matching client version. Many routine resource operations can instead use kubectl with the Calico API server. calicoctl node status requires an appropriate node environment; a laptop kubeconfig alone is insufficient.

</details>

8. What is the relationship between Calico OSS and Calico Enterprise?
   - A) They are completely separate products with no shared code
   - B) Calico Enterprise is the commercial version built on top of Calico OSS
   - C) Calico OSS is deprecated in favor of Calico Enterprise
   - D) Calico Enterprise only works with Calico Cloud

<details>
<summary>Show Answer</summary>

**Answer: B) Calico Enterprise is the commercial version built on top of Calico OSS**

**Explanation:**
Enterprise builds on Calico technology with commercial features and support. Open Source also includes policy tiers and Goldmane/Whisker observability and can run in production. Consult the current feature matrix rather than assuming every advanced feature is paid or that OSS is only for small clusters.

</details>

9. Which year did Calico introduce eBPF dataplane support?
   - A) 2018
   - B) 2019
   - C) 2020
   - D) 2022

<details>
<summary>Show Answer</summary>

**Answer: C) 2020**

**Explanation:**
The official February 25, 2020 announcement introduced the new data plane as a tech preview for Calico 3.13. It was not a GA announcement. eBPF executes in the Linux kernel and can replace parts of conventional packet processing, not the kernel itself. Performance depends on the measured workload.

</details>

10. What is Calico Cloud?
   - A) A managed Kubernetes service
   - B) A SaaS platform for Calico network security
   - C) A cloud storage solution
   - D) A CDN service for Kubernetes

<details>
<summary>Show Answer</summary>

**Answer: B) A SaaS platform for Calico network security**

**Explanation:**
Calico Cloud is Tigera's SaaS offering for network security and observability. It is not a Kubernetes hosting service, object store or CDN. Features and responsibilities differ from self-managed Enterprise; cluster integration/configuration is still required. The earlier unsupported 2022 launch date is unnecessary to this definition.

</details>

---

[Return to Learning Materials](../../../networking/calico/01-introduction.md) | [Next Quiz: Architecture](02-architecture-quiz.md)
