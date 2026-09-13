# Multi-Account, Multi-Cluster EKS Architecture Quiz

> This quiz tests your understanding of [Multi-Account, Multi-Cluster EKS Architecture](../../governance/03-eks-multi-account-multi-cluster.md).

---

1. What is a valid validation objective for two-cluster A/B EKS?
   - A) Fixing a single-AZ EKS control plane
   - B) Testing containment of upgrade/add-on/webhook failures to one cluster
   - C) Automatically covering every Region outage
   - D) Guaranteeing lower cost

<details>
<summary>Show Answer</summary>

**Answer: B) Testing containment of upgrade/add-on/webhook failures to one cluster**

**Explanation:**
Cluster-specific failure containment can justify the design. Shared VPC, DNS, Account, and data dependencies require separate analysis.

</details>

---

2. Which statement correctly describes ARC zonal shift's fail-safe behavior?
   - A) Traffic is blocked immediately for any workload once a zonal shift occurs
   - B) If a workload's endpoints exist only in the impaired AZ, EKS keeps sending traffic to that AZ anyway
   - C) Every workload is automatically relocated to another AZ
   - D) This behavior only occurs on EKS Fargate

<details>
<summary>Show Answer</summary>

**Answer: B) If a workload's endpoints exist only in the impaired AZ, EKS keeps sending traffic to that AZ anyway**

**Explanation:**
This is the fail-safe behavior — a workload deployed to only a single AZ is not protected by zonal shift. Test N-1 load and single-AZ exceptions; this does not mean a practice run always stops that workload.

</details>

---

3. What does the EC2 link-local 1,024 packet/sec allowance imply?
   - A) Check combined DNS/IMDS/NTP traffic and actual DNS metrics
   - B) Unlimited capacity reserved exclusively for DNS
   - C) A 100 Gbps-per-AZ limit
   - D) Proof that CoreDNS is the most common failure

<details>
<summary>Show Answer</summary>

**Answer: A) Check combined DNS/IMDS/NTP traffic and actual DNS metrics**

**Explanation:**
Review the shared link-local allowance and VPC DNS ENI limit. Verify linklocal_allowance_exceeded and DNS latency instead of inferring cause from Pod density alone.

</details>

---

4. What should be checked when disabling ALB target-group cross-zone balancing?
   - A) Guaranteed ALB cross-zone transfer savings
   - B) Per-AZ capacity, distinguishing empty-AZ 503 from unhealthy-target failover
   - C) Automatic cluster restarts
   - D) All targets become healthy

<details>
<summary>Show Answer</summary>

**Answer: B) Per-AZ capacity, distinguishing empty-AZ 503 from unhealthy-target failover**

**Explanation:**
Target stickiness and Lambda targets have restrictions; empty and unhealthy targets differ. ALB cross-zone regional data transfer has no additional transfer charge.

</details>
