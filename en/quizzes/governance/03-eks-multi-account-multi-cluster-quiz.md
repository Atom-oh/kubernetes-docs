# Multi-Account, Multi-Cluster EKS Architecture Quiz

> This quiz tests your understanding of [Multi-Account, Multi-Cluster EKS Architecture](../../governance/03-eks-multi-account-multi-cluster.md).

---

1. What is the primary reason an A/B EKS Runtime (splitting the blast radius across two clusters) provides real availability improvement?
   - A) To defend against AZ failures, because the EKS managed control plane isn't multi-AZ
   - B) To contain failures the organization itself creates, like failed cluster upgrades, add-on regressions, and bad cluster-wide policy rollouts
   - C) Because it's an officially recommended standard AWS pattern
   - D) To reduce cost

<details>
<summary>Show Answer</summary>

**Answer: B) To contain failures the organization itself creates, like failed cluster upgrades, add-on regressions, and bad cluster-wide policy rollouts**

**Explanation:**
The EKS managed control plane is already multi-AZ, and ARC zonal shift/autoshift only acts on the data plane. The value of an A/B EKS Runtime is protection against failures the organization itself creates — this is not an official AWS-recommended pattern, but a working hypothesis the organization must validate itself.

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
This is the fail-safe behavior — a workload deployed to only a single AZ is not protected by zonal shift. This is why it's recommended to formalize the rule that clusters targeted by ARC zonal autoshift must not host single-AZ workloads.

</details>

---

3. What's true about the packet rate limit from a single ENI to Route 53 Resolver?
   - A) It's 1,024 packets/sec (not adjustable), and can be the root cause of CoreDNS failures on high-pod-density nodes
   - B) There's no limit at all
   - C) It's capped at 100 Gbps per AZ
   - D) It's not counted toward NAU (Network Address Usage)

<details>
<summary>Show Answer</summary>

**Answer: A) It's 1,024 packets/sec (not adjustable), and can be the root cause of CoreDNS failures on high-pod-density nodes**

**Explanation:**
This limit is not adjustable, and CoreDNS is the most common single point of failure across both A/B setups and AZ redundancy. On high-pod-density nodes, this packet limit can become the actual root cause of DNS failures, making NodeLocal DNS worth adopting.

</details>

---

4. What's the risk of disabling ALB target group cross-zone load balancing?
   - A) It actually increases cost
   - B) Sticky sessions and Lambda targets can't be used, and if any AZ has zero healthy targets, all requests landing in that AZ get 503s
   - C) The EKS cluster restarts automatically
   - D) NAT Gateway quota is exceeded

<details>
<summary>Show Answer</summary>

**Answer: B) Sticky sessions and Lambda targets can't be used, and if any AZ has zero healthy targets, all requests landing in that AZ get 503s**

**Explanation:**
Disabling cross-zone load balancing reduces cross-AZ cost, but with significant trade-offs. AWS recommends keeping the default (enabled) unless you can guarantee per-AZ capacity.

</details>
