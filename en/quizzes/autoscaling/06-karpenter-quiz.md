# Karpenter Quiz

This quiz tests your understanding of Karpenter node autoscaler concepts, NodePool/EC2NodeClass configuration, cost optimization, Consolidation, Drift, interruption handling, and Amazon EKS integration.

## Multiple Choice Questions

1. What is Karpenter's biggest difference compared to the existing Cluster Autoscaler?
   - A) Higher Kubernetes version requirements
   - B) Direct EC2 instance provisioning without Auto Scaling Groups
   - C) Only supports AWS and no other clouds
   - D) Only supports CPU-based scaling

<details>

<summary>Show Answer</summary>

**Answer: B) Direct EC2 instance provisioning without Auto Scaling Groups**

**Explanation:**
Karpenter's biggest differentiator is that it bypasses Auto Scaling Groups (ASG) and uses the EC2 Fleet API directly to provision nodes. Cluster Autoscaler scales through node groups/ASGs, so instance types are limited by node group configuration. Karpenter dynamically selects the optimal instance type from various options based on pod requirements and can provision nodes within seconds.
</details>

2. What CRD defines node provisioning policies in Karpenter v1beta1 API?
   - A) Provisioner
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>Show Answer</summary>

**Answer: B) NodePool**

**Explanation:**
In Karpenter v1beta1 API, the previous Provisioner CRD has been replaced by NodePool. NodePool defines node provisioning policies (instance types, capacity types, architectures, availability zones, etc.) and disruption settings (consolidation, expireAfter, etc.). EC2NodeClass defines AWS-specific configurations (subnets, security groups, AMIs, block devices, etc.), and NodePool references EC2NodeClass through nodeClassRef.
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
Use the `karpenter.sh/capacity-type` key in NodePool's `spec.template.spec.requirements` to specify capacity type. Use `values: ["spot"]` for Spot instances only, or `values: ["spot", "on-demand"]` to allow both. Karpenter selects optimal instances considering price and availability. Spot instances can save up to 90% compared to On-Demand.
</details>

4. What does Karpenter's Consolidation feature do?
   - A) Consolidate logs from multiple nodes
   - B) Consolidate workloads from multiple nodes to fewer nodes for cost savings
   - C) Consolidate multiple clusters into one
   - D) Consolidate multiple NodePools into one

<details>

<summary>Show Answer</summary>

**Answer: B) Consolidate workloads from multiple nodes to fewer nodes for cost savings**

**Explanation:**
Consolidation is Karpenter's core cost optimization feature. It consolidates (bin-packs) workloads from underutilized nodes to fewer nodes to increase resource utilization and reduce costs. `consolidationPolicy: WhenEmpty` only removes empty nodes, while `consolidationPolicy: WhenUnderutilized` also consolidates when utilization is low. `consolidateAfter` sets the wait time before consolidation.
</details>

5. What is the purpose of Karpenter's expireAfter setting?
   - A) Maximum time a pod can run on a node
   - B) Maximum time before a node is automatically replaced after creation
   - C) Cache expiration time for the Karpenter controller
   - D) Validity period of NodePool policies

<details>

<summary>Show Answer</summary>

**Answer: B) Maximum time before a node is automatically replaced after creation**

**Explanation:**
The `expireAfter` setting defines the maximum lifespan of a node. For example, setting `expireAfter: 720h` (30 days) automatically replaces nodes after 30 days. This is useful for regularly refreshing nodes for security patches, AMI updates, and utilizing newer instance types. Karpenter respects PDBs to safely move workloads to other nodes before terminating existing nodes.
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
NodePool's `spec.limits` defines the maximum resources that the NodePool can provision. For example, `limits: { cpu: 1000, memory: 1000Gi }` limits provisioning to 1000 CPU cores and 1000Gi memory total. This enables cost control and cluster capacity management. When limits are reached, Karpenter won't provision additional nodes.
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
The Drift feature detects when NodePool or EC2NodeClass configurations change and existing nodes don't match the new configuration. For example, when you update an AMI or change security groups, existing nodes become "drifted". Karpenter gradually replaces these nodes so all cluster nodes use the latest configuration. Enable with `featureGates.drift=true`.
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
EC2NodeClass's `spec.blockDeviceMappings` defines EBS volume configuration. Specify the root volume with `deviceName: /dev/xvda` and configure `volumeSize`, `volumeType`, `iops`, `throughput`, `encrypted`, `kmsKeyID`, etc. in the `ebs` subfield. For example, configure these attributes appropriately to use an encrypted 100Gi gp3 volume.
</details>

## Short Answer Questions

9. What is the typical time for Karpenter to detect an unschedulable pod and provision an appropriate node?

<details>

<summary>Show Answer</summary>

**Answer: Within seconds**

**Explanation:**
Karpenter provisions nodes within seconds of detecting unschedulable pods. This contrasts with Cluster Autoscaler which takes minutes to scale through ASGs. Karpenter's fast scaling comes from using the EC2 Fleet API directly and analyzing pod requirements to immediately select optimal instances. This is a big advantage for workloads requiring burst traffic or fast scale-out.
</details>

10. How is priority determined when multiple NodePools exist in Karpenter?

<details>

<summary>Show Answer</summary>

**Answer: Weight-based priority using the weight field**

**Explanation:**
When multiple NodePools can satisfy a pod's requirements, use the `spec.weight` field to specify priority. NodePools with higher weight values are selected first. For example, set high weight on a Spot instance NodePool and low weight on an On-Demand NodePool, and Karpenter will try Spot first and use On-Demand if unavailable.
</details>

11. What Kubernetes resource does Karpenter respect to ensure workload availability when removing nodes?

<details>

<summary>Show Answer</summary>

**Answer: PDB (PodDisruptionBudget)**

**Explanation:**
Karpenter respects PodDisruptionBudget (PDB) when removing nodes (consolidation, expiration, drift, etc.). PDB defines minimum application availability, and Karpenter only drains nodes within bounds that don't violate the PDB. For example, with a PDB setting `minAvailable: 2`, Karpenter ensures at least 2 pods are always running while removing nodes.
</details>

12. How does Karpenter select subnets and security groups to use in EC2NodeClass?

<details>

<summary>Show Answer</summary>

**Answer: Tag-based selection through subnetSelectorTerms and securityGroupSelectorTerms**

**Explanation:**
EC2NodeClass uses `subnetSelectorTerms` and `securityGroupSelectorTerms` for tag-based selection of subnets and security groups. For example, `tags: { karpenter.sh/discovery: "my-cluster" }` selects resources with that tag. AWS resources must be tagged beforehand, and when multiple subnets are selected, Karpenter distributes them appropriately for availability zone distribution.
</details>

## Hands-on Questions

13. Write a NodePool that prioritizes Spot instances, allows various instance types (m5, c5, r5 families), and removes empty nodes after 30 minutes.

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
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
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
        apiVersion: karpenter.k8s.aws/v1
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**Explanation:**
This NodePool prioritizes Spot instances for cost optimization (listing spot first in `capacity-type`). Allowing various instance types improves Spot availability and price optimization. `consolidationPolicy: WhenEmpty` with `consolidateAfter: 30m` removes nodes that are empty for 30 minutes. `weight: 100` sets higher priority than other NodePools so this NodePool is selected first.
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
  amiFamily: AL2

  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"
        kubernetes.io/role: "private"

  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"

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
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 required

  tags:
    Environment: production
    ManagedBy: karpenter
```

**Explanation:**
This EC2NodeClass follows security best practices. `blockDeviceMappings` configures a 100Gi gp3 volume with encryption. `metadataOptions.httpTokens: required` makes IMDSv2 mandatory to prevent SSRF attacks. Tag-based selectors configure use of private subnets only. `instanceProfile` references a pre-created IAM instance profile.
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
kubectl get events --field-selector source=karpenter --sort-by='.lastTimestamp'

# 9. Check detailed provisioning logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. Check Karpenter metrics (if Prometheus is configured)
kubectl port-forward -n karpenter svc/karpenter 8080:8080 &
curl localhost:8080/metrics | grep karpenter_
```

**Explanation:**
When troubleshooting Karpenter issues, check multiple aspects. First verify controller pods are running normally and logs have no errors. Review NodePool and EC2NodeClass status and configuration. Check Pending pods and their reasons. Common issues include insufficient IAM permissions, subnet/security group tag issues, and instance limits. Karpenter events and metrics are also useful for diagnosis.
</details>

---

**Scoring:**
- 13-15 correct: Excellent (Karpenter expert level)
- 10-12 correct: Good (practical application capable)
- 7-9 correct: Average (additional learning recommended)
- 0-6 correct: Insufficient (basic concepts review needed)

[Return to Learning Materials](../../autoscaling/02-karpenter.md)
