# EKS Auto Mode Migration Guide Quiz

> **Related Document**: [Migration Guide](../../eks-auto-mode/09-migration-guide.md)
> **Last Updated**: September 12, 2026

## Multiple Choice Questions

### 1. What should happen before enabling or removing migration capacity?

- A) Delete old node groups
- B) Inventory workloads, dependencies, ownership and recovery requirements
- C) Drain all Pods
- D) Assume matching instance names prove compatibility

<details>
<summary>Show Answer</summary>

**Answer: B) Inventory workloads, dependencies, ownership and recovery requirements**

**Explanation:**
Bind the account, cluster and old group identities, then inspect placement, data, IAM, networking, controllers, cost and application health. Validate each wave before scaling/deletion; the final validation stage is not the first health check. The source establishes the private WORK_DIR and KUBE_CONTEXT used below.

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get deployments,statefulsets,daemonsets,jobs,cronjobs -A -o json |
jq '[.items[] | (.spec.template // .spec.jobTemplate.spec.template) as $t |
 {kind,namespace:.metadata.namespace,name:.metadata.name,uid:.metadata.uid,
  nodeSelector:$t.spec.nodeSelector,affinity:$t.spec.affinity,tolerations:$t.spec.tolerations,
  serviceAccountName:$t.spec.serviceAccountName,hostNetwork:$t.spec.hostNetwork,
  pvcNames:[$t.spec.volumes[]?.persistentVolumeClaim.claimName // empty]}]' \
  > "$WORK_DIR/workload-placement.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
jq '[.items[] | {namespace:.metadata.namespace,name:.metadata.name,node:.spec.nodeName,
  phase:.status.phase,deletionTimestamp:.metadata.deletionTimestamp,
  ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported"),
  owners:[.metadata.ownerReferences[]?|{kind,name,controller}]}]' \
  > "$WORK_DIR/pod-state.json"
```


</details>

### 2. How can old managed nodes and Auto Mode coexist predictably?

- A) They cannot coexist
- B) Use explicit placement and controller ownership for each workload
- C) Only through a separate cluster
- D) Only by matching AWS resource tags

<details>
<summary>Show Answer</summary>

**Answer: B) Use explicit placement and controller ownership for each workload**

**Explanation:**
A specific old node-group selector and an exact Auto pool/compute-type selector distinguish the fleets. A generic Karpenter label also matches self-managed Karpenter. Keep mixed-node DNS/agents and existing storage/load-balancer controllers until their dependencies are migrated. These are Pod-spec fragments; the guide includes complete canary Deployments.

Old managed group:
```yaml
# Pod template spec fragment
nodeSelector:
  eks.amazonaws.com/nodegroup: REPLACE_WITH_OLD_NODEGROUP
tolerations: []
```

Auto canary:
```yaml
# Pod template spec fragment
nodeSelector:
  karpenter.sh/nodepool: migration-pool
  eks.amazonaws.com/compute-type: auto
tolerations:
- key: migration
  operator: Equal
  value: auto-mode
  effect: NoSchedule
```


</details>

### 3. Which order reduces migration risk?

- A) Critical production first
- B) Representative low-risk workloads, then progressively more critical dependencies
- C) Everything at once
- D) Random order

<details>
<summary>Show Answer</summary>

**Answer: B) Representative low-risk workloads, then progressively more critical dependencies**

**Explanation:**
Development/staging, non-critical production and critical production are useful phases when they reflect actual dependencies. Update the owning controller/GitOps placement, then verify application behavior, storage, IAM, DNS and traffic. A soft preference or a fabricated `node-type=auto-mode` label does not prove migration. Stop on failed or unknown health; a fixed sleep is not validation.

</details>

### 4. Which rollback sequence preserves a recovery path?

- A) Delete and recreate the cluster first
- B) Restore compatible old capacity and placement, verify health, then retire exact Auto resources
- C) Delete the Auto NodePool first
- D) Only disable Auto Mode

<details>
<summary>Show Answer</summary>

**Answer: B) Restore compatible old capacity and placement, verify health, then retire exact Auto resources**

**Explanation:**
Keep the Auto pool while old capacity becomes Ready. Review and restore the intended placement without retaining a conflicting Auto selector or clearing unrelated affinity. Verify data and traffic as well as Pods. Only then retire migration-owned capacity. A NodePool deletion can cascade to nodes; scaling JSON cannot recreate a deleted node group. This is a workload migration rollback, not a Kubernetes-version rollback.

</details>

### 5. What is required before reducing the old managed node group's desired size?

- A) Immediately set it to zero
- B) Validate migrated workloads, cordon/empty old application capacity and coordinate its owner
- C) Always halve the size
- D) Only wait five minutes

<details>
<summary>Show Answer</summary>

**Answer: B) Validate migrated workloads, cordon/empty old application capacity and coordinate its owner**

**Explanation:**
MNG scaling-configuration changes use ASG scale-down and do not respect PDBs. The source checks old-node cordons and active non-DaemonSet Pods and stops on failed queries. Review system dependencies and exported job results, and keep controllers from repopulating old nodes. Halving desired size with a sleep does not establish safety. Original IaC/scaling ownership still applies.

</details>

### 6. How should cost be monitored during migration?

- A) Ignore cost until all old resources are deleted
- B) Use current node count as exact billed cost
- C) Track overlapping fleets/load balancers alongside availability and performance
- D) Assume Auto Mode removes all old charges automatically

<details>
<summary>Show Answer</summary>

**Answer: C) Track overlapping fleets/load balancers alongside availability and performance**

**Explanation:**
Both fleets and traffic paths may be billed during coexistence. Use actual billing evidence and configured operational publishers. The original thresholds below remain unverified planning examples, not default Auto Mode metrics or normal ranges.

| Signal | Prior baseline example | Prior alert example |
|--------|------------------------|---------------------|
| Pending Pods | 0–5 | >10 for 5 min |
| Provisioning time | <90 sec | >120 sec |
| Availability | >99.9% | <99.5% |
| API latency | <200 ms | >500 ms |

Pending is not synonymous with unschedulable, Running is not application readiness, and missing collector data is not zero failures.

</details>

### 7. Which action may be deferred to preserve rollback options after workload validation?

- A) Checking application behavior
- B) Checking expected placement
- C) Deleting the old node-group definition
- D) Checking data and controller health

<details>
<summary>Show Answer</summary>

**Answer: C) Deleting the old node-group definition**

**Explanation:**
Retain the old definition/configuration for a deliberate stabilization window, while accounting for any retained resources and costs. The former one-to-two-week interval is an example, not a universal requirement. Check actual readiness and successful Jobs instead of demanding every Pod be Running. Delete through the original IaC owner only after data/traffic/workload validation.

</details>

### 8. What is the correct approach to an existing self-managed Karpenter controller?

- A) Always remove it before enabling Auto Mode
- B) Keep compatible Karpenter during coexistence, finalize old owned resources, then uninstall
- C) Delete all shared Karpenter CRDs
- D) Select all Karpenter-labeled nodes for deletion

<details>
<summary>Show Answer</summary>

**Answer: B) Keep compatible Karpenter during coexistence, finalize old owned resources, then uninstall**

**Explanation:**
AWS documents direct coexistence migration. The v1.1 migration floor does not replace current Kubernetes compatibility requirements. Use distinct NodeClass references and a tainted Auto pool. Do not modify/delete shared NodePool/NodeClaim CRDs. Retire old owned NodePools/claims while the existing controller can complete finalization, confirm instance/dependency cleanup, then remove only its release/IAM/queue resources.

</details>

## References

- [Managed node-group scaling and PDBs](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Auto Mode migration reference](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)
- [Karpenter coexistence migration](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)
