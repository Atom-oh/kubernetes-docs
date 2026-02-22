# Calico Introduction Quiz

> **Related Document**: [Calico Introduction](../../../networking/calico/01-introduction.md)
> **Last Updated**: February 22, 2026

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
Project Calico was started in 2014 at Metaswitch. It has since grown to become one of the most widely used Kubernetes CNI plugins globally. In 2016, Tigera was founded to commercialize Calico, and in 2019, Calico Enterprise was released.

</details>

2. Which company founded Tigera and commercialized Calico?
   - A) Google
   - B) Red Hat
   - C) Metaswitch founders
   - D) VMware

<details>
<summary>Show Answer</summary>

**Answer: C) Metaswitch founders**

**Explanation:**
Tigera was founded in 2016 by the original creators of Project Calico from Metaswitch. Tigera now maintains both the open-source Calico project and offers commercial products including Calico Enterprise and Calico Cloud.

</details>

3. Which of the following is NOT a core feature of Calico?
   - A) BGP-based routing
   - B) Built-in service mesh with sidecar injection
   - C) Kubernetes standard and extended network policies
   - D) Support for eBPF dataplane

<details>
<summary>Show Answer</summary>

**Answer: B) Built-in service mesh with sidecar injection**

**Explanation:**
Calico provides high-performance networking with BGP-based routing, powerful network policies (both Kubernetes standard and Calico extended), and eBPF dataplane support. However, unlike Cilium, Calico does not include a built-in service mesh. Service mesh functionality is available separately through Calico Enterprise or by integrating with other service mesh solutions like Istio.

</details>

4. What is the primary advantage of Calico's BGP-based networking compared to traditional overlay networks?
   - A) Simpler configuration
   - B) Better security encryption
   - C) Direct routing without encapsulation overhead
   - D) Built-in DNS resolution

<details>
<summary>Show Answer</summary>

**Answer: C) Direct routing without encapsulation overhead**

**Explanation:**
BGP-based networking in Calico enables direct routing of packets between nodes without the overhead of encapsulation (like VXLAN or IPIP). This results in better network performance, lower latency, and easier integration with existing network infrastructure. Traditional overlay networks add encapsulation headers which increase packet size and processing overhead.

</details>

5. Which environments does Calico support?
   - A) Cloud only
   - B) On-premises only
   - C) Cloud, on-premises, and hybrid
   - D) Kubernetes only, no VM support

<details>
<summary>Show Answer</summary>

**Answer: C) Cloud, on-premises, and hybrid**

**Explanation:**
Calico is a versatile networking solution that supports multiple environments including public cloud (AWS, Azure, GCP), on-premises data centers, and hybrid deployments. It can also be used with virtual machines and bare-metal workloads, not just Kubernetes containers.

</details>

6. What dataplane options does Calico support?
   - A) iptables only
   - B) eBPF only
   - C) iptables and eBPF
   - D) IPVS only

<details>
<summary>Show Answer</summary>

**Answer: C) iptables and eBPF**

**Explanation:**
Calico supports both iptables and eBPF dataplanes. The iptables dataplane is the traditional and most mature option, while eBPF mode was introduced in 2020 and provides improved performance with lower CPU usage. Users can choose the dataplane that best fits their requirements and kernel version support.

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
calicoctl is a command-line interface tool for managing Calico resources such as network policies, IP pools, BGP configurations, and nodes. It provides direct access to the Calico datastore and is essential for troubleshooting, diagnostics, and advanced configuration tasks that may not be easily accomplished through kubectl alone.

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
Calico Enterprise is Tigera's commercial offering that builds upon the open-source Calico project. It adds enterprise features such as advanced threat detection, compliance reporting, multi-cluster management, and commercial support. The core networking and policy functionality is shared between both versions.

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
Calico introduced eBPF dataplane support in 2020. This was a significant milestone that allowed Calico to provide improved performance with features like Direct Server Return (DSR), connection-time load balancing, and the ability to replace kube-proxy, all while using less CPU than the iptables dataplane.

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
Calico Cloud, launched in 2022, is a SaaS (Software as a Service) offering from Tigera that provides Calico Enterprise features as a managed service. It simplifies deployment and management of advanced network security, observability, and compliance features without the operational overhead of self-managing the enterprise components.

</details>

---

[Return to Learning Materials](../../../networking/calico/01-introduction.md) | [Next Quiz: Architecture](./02-architecture-quiz.md)
