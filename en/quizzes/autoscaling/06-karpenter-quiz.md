# Karpenter Quiz

> **Last Updated**: September 11, 2026

This quiz tests your understanding of Karpenter node autoscaler concepts, NodePool/EC2NodeClass configuration, cost optimization, Consolidation, Drift, interruption handling, and Amazon EKS integration.

## Multiple Choice Questions

1. In this AWS example, which architectural difference distinguishes Karpenter from Cluster Autoscaler?
   - A) Higher Kubernetes version requirements
   - B) Direct EC2 instance provisioning without Auto Scaling Groups
   - C) Only supports AWS and no other clouds
   - D) Only supports CPU-based scaling

<details>

<summary>Show Answer</summary>

**Answer: B) Direct EC2 instance provisioning without Auto Scaling Groups**

**Explanation:**
With the AWS provider, Karpenter requests EC2 capacity (including EC2 Fleet) through NodeClaims rather than scaling an Auto Scaling Group. Cluster Autoscaler generally adjusts configured node groups. Instance choices still depend on Pod/NodePool/NodeClass constraints, quotas and availability. API launch time, Node Ready time and application readiness are distinct; no seconds-only outcome is guaranteed.
</details>

2. What CRD defines node provisioning policies (instance types, capacity types, disruption settings) in the Karpenter v1 API?
   - A) NodeClaim
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>Show Answer</summary>

**Answer: B) NodePool**

**Explanation:**
NodePool (karpenter.sh/v1) defines template requirements and lifecycle policy. expireAfter is under spec.template.spec, while consolidation/budgets are under spec.disruption. EC2NodeClass (karpenter.k8s.aws/v1) supplies AWS settings through nodeClassRef. NodeClaim tracks an individual node’s requested capacity and lifecycle.
</details>

3. How do you configure Karpenter to use Spot instances for cost optimization?
   - A) disruption.capacityType: spot
   - B) Specify karpenter.sh/capacity-type: spot in requirements
   - C) Set spotEnabled: true in nodeClassRef
   - D) Set spot: true in limits

<details>

<summary>Show Answer</summary>

**Answer: B) Specify karpenter.sh/capacity-type: spot in requirements**

**Explanation:**
NodePool requirements can allow spot, on-demand and, where configured, reserved capacity. Values in an In requirement are a set: their order does not express preference. Among allowed capacity types, Karpenter prioritizes reserved, then Spot, then On-Demand, subject to available offerings and constraints. Spot pricing and interruption exposure vary; savings are not guaranteed.
</details>

4. What does Karpenter's Consolidation feature do?
   - A) Consolidate logs from multiple nodes
   - B) Evaluate feasible node deletion or lower-cost replacement under workload constraints
   - C) Consolidate multiple clusters into one
   - D) Consolidate multiple NodePools into one

<details>

<summary>Show Answer</summary>

**Answer: B) Evaluate feasible node deletion or lower-cost replacement under workload constraints**

**Explanation:**
Consolidation looks for feasible deletions or lower-cost replacements while respecting workload constraints and applicable disruption controls. It can remove a node, replace one with a cheaper one, or consolidate several; node count need not always decrease. WhenEmpty restricts consolidation to eligible empty nodes. consolidateAfter is an eligibility delay following relevant Pod changes, not a guaranteed termination deadline or a CPU-utilization threshold.
</details>

5. What is the purpose of Karpenter's expireAfter setting?
   - A) Maximum time a pod can run on a node
   - B) Node age at which expiration-driven draining begins
   - C) Cache expiration time for the Karpenter controller
   - D) Validity period of NodePool policies

<details>

<summary>Show Answer</summary>

**Answer: B) Node age at which expiration-driven draining begins**

**Explanation:**
expireAfter starts expiration-driven draining once the node reaches that age. A blocking PDB or do-not-disrupt Pod can delay completion without a terminationGracePeriod. A configured terminationGracePeriod can eventually force-delete remaining Pods; external interruption deadlines may also remove capacity. Replacement uses current eligible AMIs/types, not necessarily newer ones. Expiration does not guarantee that a replacement is Ready first.
</details>

6. What field sets resource limits for a NodePool in Karpenter?
   - A) spec.template.limits
   - B) spec.limits
   - C) spec.maxResources
   - D) spec.resourceQuota

<details>

<summary>Show Answer</summary>

**Answer: B) spec.limits**

**Explanation:**
spec.limits constrains total resources for a dynamic NodePool. String quantities such as cpu: "1000" avoid API/GitOps type differences. Limit checks are eventually consistent during parallel provisioning, so rapid scale-out can overshoot. This is not a strict cost or billing cap.
</details>

7. What does Karpenter's Drift feature detect and handle?
   - A) Network traffic changes
   - B) State where existing nodes don't match current configuration due to NodePool/EC2NodeClass changes
   - C) Pod scheduling drift
   - D) Kubernetes version changes

<details>

<summary>Show Answer</summary>

**Answer: B) State where existing nodes don't match current configuration due to NodePool/EC2NodeClass changes**

**Explanation:**
Drift compares existing NodeClaims against relevant desired/resolved configuration. Some changes do not cause drift (for example weight or budgets), and a mutable AMI selector can change resolution without a manifest edit. Drift handling is subject to disruption controls and cannot guarantee immediate convergence of every node. Drift is stable in v1; the old drift feature gate is gone.
</details>

8. What field in EC2NodeClass sets the node's root volume size and type?
   - A) spec.rootVolume
   - B) spec.blockDeviceMappings
   - C) spec.storage
   - D) spec.ebsConfig

<details>

<summary>Show Answer</summary>

**Answer: B) spec.blockDeviceMappings**

**Explanation:**
spec.blockDeviceMappings configures EBS devices. For the AL2023 example the root mapping is /dev/xvda; use the actual AMI/family layout for other images, including Bottlerocket’s separate data device. Size, type, encryption and KMS permissions must match the intended volumes. An additional EBS mapping does not automatically format or mount a filesystem.
</details>

## Short Answer Questions

9. Which stages must you measure when assessing Karpenter scale-out latency?

<details>

<summary>Show Answer</summary>

**Answer: Measure provisioning and readiness stages; there is no universal fixed duration.**

**Explanation:**
Measure demand detection/batching, EC2 request and capacity fulfillment, boot/bootstrap, Node registration/Ready, then image pulling and application readiness. IAM/API retries, IP capacity, storage and application initialization affect different stages. The document has no historical measured timings that establish a universal comparison with Cluster Autoscaler.
</details>

10. How is priority determined when multiple NodePools exist in Karpenter?

<details>

<summary>Show Answer</summary>

**Answer: Weight-based priority using the weight field**

**Explanation:**
For eligible dynamic NodePools, higher spec.weight expresses a provisioning preference. Scheduling batches, workload requirements, existing capacity, NodePool limits and unavailable offerings can lead to another pool. It is not an absolute per-Pod guarantee or a fixed Spot/On-Demand ratio; static NodePools have separate constraints. Capacity-type preference inside one pool is independent of array order.
</details>

11. Which Kubernetes resource constrains voluntary Pod eviction during node removal?

<details>

<summary>Show Answer</summary>

**Answer: PDB (PodDisruptionBudget)**

**Explanation:**
A PDB restricts voluntary eviction based on healthy matching replicas. It neither creates those replicas nor prevents involuntary instance loss, forceful repair or expiry of a configured terminationGracePeriod. minAvailable: 2 is an eviction constraint, not a promise that two Pods are always running or serving traffic.
</details>

12. How does Karpenter select subnets and security groups to use in EC2NodeClass?

<details>

<summary>Show Answer</summary>

**Answer: subnetSelectorTerms and securityGroupSelectorTerms, using supported tags/IDs and other documented selectors.**

**Explanation:**
The selectors can use supported tags or explicit resource IDs (and security-group names where supported). Conditions within one term are ANDed; terms are ORed. Within a selected AZ, Karpenter normally chooses the matching subnet with the most available IP addresses. This does not itself guarantee even AZ distribution or private routing; verify topology constraints, routes and actual security groups.
</details>

## Hands-on Questions

13. Write a dynamic NodePool that permits Spot with On-Demand fallback, allows m5/c5/r5 types, and makes empty nodes eligible for consolidation after 30 minutes.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    metadata:
      labels:
        nodepool: cost-optimized
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - c5.large
        - c5.xlarge
        - c5.2xlarge
        - r5.large
        - r5.xlarge
        - r5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**Explanation:**
Spot preference comes from Karpenter’s capacity-type policy, not listing spot first. Broader eligible types can improve options, but do not guarantee availability. WhenEmpty/consolidateAfter: 30m makes eligible empty nodes candidates after the delay; budgets/PDBs and reconciliation can defer removal. weight: 100 is a relative preference only. The referenced default EC2NodeClass and node identity must already be valid.
</details>

14. Write an EC2NodeClass with a 100Gi gp3 encrypted root volume, tag-based subnet/security group selection, and IMDSv2 required settings.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
      example.com/network-role: private
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  instanceProfile: KarpenterNodeInstanceProfile-my-cluster
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      iops: 3000
      throughput: 125
      encrypted: true
      deleteOnTermination: true
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1
    httpTokens: required
  tags:
    Environment: production
    ManagedBy: karpenter
```

**Explanation:**
This is an AL2023 learning example. @latest may change the resolved AMI and trigger drift; pin and test an approved release or AMI before production rollout. The private marker is a custom tag that must exist on subnets whose routes you verified. IMDSv2 reduces several metadata attack paths but does not universally prevent SSRF; hop limit1 limits many non-host-network container paths and must be tested with the CNI/workload identity design. The named instance profile, node access, KMS/volume configuration and network paths are prerequisites.
</details>

15. Write commands to verify Karpenter installation status and debug provisioning issues.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# 1. Check Karpenter pod status
kubectl get pods -n karpenter

# 2. Check Karpenter controller logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# 3. Check NodePool status
kubectl get nodepool
kubectl describe nodepool default

# 4. Check EC2NodeClass status
kubectl get ec2nodeclass
kubectl describe ec2nodeclass default

# 5. Check pods waiting to be scheduled
kubectl get pods --all-namespaces --field-selector status.phase=Pending

# 6. Check nodes created by Karpenter
kubectl get nodes -l karpenter.sh/nodepool

# 7. Check node details and labels/taints
kubectl describe node <node-name>

# 8. Check Karpenter events
kubectl get events --all-namespaces --sort-by='.metadata.creationTimestamp'
kubectl get nodeclaims -o wide

# 9. Check detailed provisioning logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. Forward the metrics endpoint; keep this terminal open until done.
kubectl port-forward -n karpenter svc/karpenter 8080:8080
```

In another terminal, after the forwarding ready message:

```bash
curl --fail --show-error http://127.0.0.1:8080/metrics | grep karpenter_
```

**Explanation:**
Inspect controller readiness, NodePool/EC2NodeClass/NodeClaim conditions, Pod scheduling events and AWS-side prerequisites together. Pending is not synonymous with insufficient compute, and a missing filtered log line is not proof of success. Run the port-forward in a separate terminal, wait for its ready message, fetch metrics from another terminal, then stop it with Ctrl+C. A Prometheus server is not required for this direct metrics read; no command here was executed against a cluster.
</details>

---

**Scoring:**
- 13-15 correct: Excellent (Karpenter expert level)
- 10-12 correct: Good (practical application capable)
- 7-9 correct: Average (additional learning recommended)
- 0-6 correct: Insufficient (basic concepts review needed)

[Return to Learning Materials](../../autoscaling/02-karpenter.md)
