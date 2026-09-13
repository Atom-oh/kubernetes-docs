# Zonal Cluster Operations: Traffic Shifting, Upgrade Rollback, and Data-Layer AZ Affinity

> **Review baseline**: EKS rollback and ARC documentation, Strimzi 1.2.0, Valkey GLIDE 2.5.2, AWS Advanced JDBC Wrapper 4.4.0
> **Last reviewed**: September 11, 2026. Configuration examples were checked; live cluster cutovers and failure experiments were not performed.

< [Previous: Tekton Pipelines](14-tekton-pipelines.md) | [Table of Contents](./README.md) | [Next: Troubleshooting Playbook](16-troubleshooting-playbook.md) >

***

This guide combines **traffic shifting across clusters with AZ-local workers, conditional version rollback, and AZ-aware data reads**. A zonal fleet is not a default architecture for every team. Consider it when you can operate cell capacity, routing, deployments, and data dependencies independently.

Here, zonal describes **worker and application placement**. The [managed EKS control plane](https://docs.aws.amazon.com/eks/latest/userguide/eks-architecture.html) remains distributed across multiple AZs. The entire cluster does not reside inside one AZ.

## Table of Contents

1. [Why Zonal Operations](#why-zonal-operations)
2. [Traffic Layer: Target Group + TargetGroupBinding + Weight Shifting](#traffic-layer-target-group--targetgroupbinding--weight-shifting)
3. [Upgrades: Conditions for In-Place and Native Rollback](#upgrades-conditions-for-in-place-and-native-rollback)
4. [Data Layer: Prefer Same-AZ Reads](#data-layer-prefer-same-az-reads)
5. [Recommended Combination Summary](#recommended-combination-summary)

***

## Why Zonal Operations

| Aspect | Multi-AZ single cluster | Clusters with workers in one AZ each |
|--------|------------------------|--------------------------------------|
| Failure isolation | Replicas and spare capacity in healthy AZs handle recovery | A cell can lose all its workers; shared databases, routing, and regional dependencies can affect other cells |
| Cross-AZ cost | Depends on service and data paths | Local application traffic can decrease, but replication, shared services, and LB forwarding can still cross AZs |
| Upgrades | Control plane and nodes change in stages, with version skew managed | Sequential cell upgrades need compatible versions and capacity in the remaining cells |
| Operational complexity | One cluster | Multiple clusters and coordinated routing |

See AWS's [Cell-Based Architecture for Amazon EKS Guidance](https://aws.amazon.com/solutions/guidance/cell-based-architecture-for-amazon-eks/). Minimize dependencies between cells and size healthy cells to absorb the failed cell's traffic. Selecting per-cell LBs through DNS and weighting target groups behind one LB are different routing designs. Measure costs using the actual traffic paths and each service's charging rules.

Related guides: [Advanced Infrastructure](02-infrastructure-advanced.md) and [EKS Resiliency](../eks/10-eks-resiliency.md).

***

<span id="traffic-layer-target-group--targetgroupbinding--weight-shifting"></span>

## Traffic Layer: Target Group + TargetGroupBinding + Weight Shifting

![One load balancer listener distributes new traffic between two target groups; TargetGroupBinding in each cluster registers its pod targets.](../.gitbook/assets/en-ops-15-zonal-operations-guide-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-15-zonal-operations-guide-0.html)

For two clusters sharing one LB:

1. Create the NLB/ALB and target groups outside the clusters using IaC, so replacing a cluster does not delete the LB.
2. Bind each cluster's Service to its own target group using `TargetGroupBinding`.
3. Change weights in the **listener's forward action**. TGB itself has no weight field. Assign ownership of target groups and listener configuration explicitly between IaC and controllers.

The TGB example assumes the `production` namespace, `app-service:80`, an IP target group in the intended VPC, and AWS Load Balancer Controller already exist. Replace the example ARN and verify target health and network access.

This example uses a **separately installed AWS Load Balancer Controller**. Built-in Auto Mode TGB uses eks.amazonaws.com/v1 with different [tag and lifecycle rules](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-alb.html). AWS documents target-group deletion when that built-in TGB or cluster is deleted; do not mix that ownership model with this externally managed target group.

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: zone-a-tgb
  namespace: production
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:ap-northeast-2:ACCOUNT:targetgroup/zone-a-tg/xxxxxxxxxxxx
  serviceRef:
    name: app-service
    port: 80
  targetType: ip
```

```bash
set -euo pipefail
# NLB listener whose existing default action forwards to these two groups.
# Nondefault ALB rules require modify-rule, not this operation.
: "${LISTENER_ARN:?}" "${ZONE_A_TG_ARN:?}" "${ZONE_C_TG_ARN:?}"
aws elbv2 describe-listeners \
  --listener-arns "$LISTENER_ARN" \
  --query 'Listeners[0].DefaultActions' --output json > current-actions.json
jq -e --arg a "$ZONE_A_TG_ARN" --arg c "$ZONE_C_TG_ARN" '
  if $a == $c or length != 1 or .[0].Type != "forward"
     or ([.[0].ForwardConfig.TargetGroups[].TargetGroupArn] | sort)
        != ([$a, $c] | sort)
  then error("Expected one forward action with exactly the two selected groups")
  else
    .[0].ForwardConfig.TargetGroups |= map(
      .Weight = (if .TargetGroupArn == $a then 20 else 80 end))
  end
' current-actions.json > proposed-actions.json &&
aws elbv2 modify-listener \
  --listener-arn "$LISTENER_ARN" \
  --default-actions file://proposed-actions.json
```

Before execution, reconcile this change with the IaC plan. Ordinary NLB weight changes affect **new flows**, but **weight zero needs separate treatment**. The [current user guide](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html) states that shortly after setting zero, the group receives no new connections and existing connections are closed. Do not assume existing connections survive until natural closure; test application drain, reconnection, and retry behavior before switching to zero. Follow the [official guide](https://aws.amazon.com/blogs/networking-and-content-delivery/network-load-balancers-now-support-weighted-target-groups/) to inspect `NewFlowCount` and `ActiveFlowCount` per target group, health, error rates, and connection draining before changing nodes. Verify target-group protocol/IP-version compatibility and cross-zone settings. With targets confined to different AZs, disabling cross-zone balancing can prevent the intended weight distribution.

Route 53 weighted records select **LB DNS endpoints**, not target-group ARNs. TTLs, client caches, and long-lived connections also prevent instant DNS cutover. See [AWS Load Balancer Controller](../networking/03-aws-lb-controller.md) and [Advanced Infrastructure](02-infrastructure-advanced.md) for the surrounding setup.

**Planned shifts and failure response:** weight changes support planned transitions but do not provide automatic failure detection. [ARC zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html) is operator initiated. **Zonal autoshift** requires separate activation, practice, and alarm configuration. An EKS resource shift changes impaired-AZ endpoint/node handling within that cluster; it does not rewrite another cluster's target-group weights. Plan the LB resource's shift separately too.

> **EKS Auto Mode support:** following the [July 2026 release](https://aws.amazon.com/about-aws/whats-new/2026/07/eks-auto-mode-arc-zonal-shift/), enabling cluster zonal shift lets Auto Mode constrain new provisioning and voluntary disruption in the impaired AZ during a shift. This does not enable autoshift by itself. **Shifting away from the only AZ containing workers can cause an outage.** EKS shift needs healthy-AZ replicas, CoreDNS, and spare capacity. A cell whose workers occupy one AZ needs external cell routing as part of recovery.

***

## Upgrades: Conditions for In-Place and Native Rollback

[EKS native version rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html), introduced in July 2026, can return to the **immediately previous minor version if initiated within seven days after upgrade completion**. Seven days is an eligibility window, not a recovery-time guarantee. Check creation version, support status, subsequent upgrades, feature compatibility, and Rollback Readiness Insights.

- **Auto Mode:** EKS rolls back Auto Mode nodes first, then the control plane. PDBs and NodePool disruption budgets still apply; rollback is not instantaneous.
- **Managed node groups:** roll them back separately with `UpdateNodegroupVersion`. Operators prepare self-managed and Hybrid nodes separately. Nodes must not run a version newer than the control plane.
- **Add-ons, data, and applications:** rollback does not restore add-on versions, etcd data, persistent-volume data, or application changes. Plan compatibility and data-migration recovery independently.
- **`--force`:** can bypass readiness insights, but not eligibility prerequisites or Auto Mode disruption controls. Resolve issues before following the normal rollback procedure.

There is no additional charge for the rollback feature itself; existing cluster, compute, and traffic charges still apply. Choose in-place or blue/green after validating remaining-cell capacity and recovery objectives.

| Approach | Appropriate conditions |
|----------|------------------------|
| **Blue/green clusters** | Validate in a separate environment and retain traffic failback to the old environment; shared data changes need their own recovery plan |
| **Zonal in-place + native rollback** | An existing cell fleet can absorb traffic, and eligibility, compatibility, and recovery time have been tested |
| **Route 53 weighted DNS cutover** | Distinct LB endpoints, including cross-Region/account designs, with DNS caching and health behavior considered |

The operational sequence is **check remaining-cell capacity → shift weights → confirm connection draining → upgrade → validate → restore weights**. See [Upgrade Operations](11-upgrade-operations.md) and [EKS Upgrades](../eks/08-eks-upgrades.md) for detailed procedures and node-specific conditions.

***

## Data Layer: Prefer Same-AZ Reads

Prefer local reads when a suitable replica exists in the same AZ and the application accepts its consistency behavior. Writes, replication, initial metadata requests, and failure fallback can still cross AZs. Measure replication lag, errors, actual connection destinations, and transfer volume together.

![The application prefers Kafka, Valkey, and Aurora readers in its AZ; writes and read fallback may still cross AZ boundaries.](../.gitbook/assets/en-ops-15-zonal-operations-guide-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-15-zonal-operations-guide-1.html)

First determine the pod's AZ. The Downward API exposes pod fields; it does not directly query node labels.

- **Node metadata injection:** ordinary Pod-create admission occurs before scheduling, so the destination node is not yet known. The [AWS MSK guide](https://aws.amazon.com/blogs/big-data/optimize-traffic-costs-of-amazon-msk-consumers-on-amazon-eks-with-rack-awareness/) handles **`Pod/binding` requests** to read the selected node and inject its AZ ID. Configure Kyverno binding-request filters, node-read RBAC, and completion before pod startup together.
- **Post-scheduling lookup:** expose `spec.nodeName` through the Downward API and use a trusted initialization component to read node labels. Do not grant all applications broad node-read access.
- **EC2 IMDSv2:** where EC2 metadata access is intentionally available, obtain a token before reading placement information. Do not assume an IMDSv1 GET works or remove metadata restrictions indiscriminately. This is not directly applicable to Fargate.
- **Operator support:** Strimzi configures rack awareness for its managed brokers and supported client resources. It does not automatically set `client.rack` in unrelated application Deployments.

**Do not mix AZ names and AZ IDs.** Kafka's `broker.rack` and `client.rack` must use matching strings. If MSK uses AZ IDs, do not substitute a name such as `ap-northeast-2a`. GLIDE's `client_az` must likewise match the AZ values reported by the servers.

### Kafka: KIP-392 Follower Fetching

[KIP-392](https://cwiki.apache.org/confluence/display/KAFKA/KIP-392:+Allow+consumers+to+fetch+from+closest+replica), introduced in Kafka 2.4, allows consumers to read from a same-rack replica. This is the feature's introduction version, not a recommendation to deploy Kafka 2.4 today.

![A Kafka consumer receives a preferred-replica hint from the leader, then reads from a same-rack replica. Initial requests and replication can still cross AZs.](../.gitbook/assets/en-ops-15-zonal-operations-guide-10.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-15-zonal-operations-guide-10.html)

- **Brokers:** configure `replica.selector.class=org.apache.kafka.common.replica.RackAwareReplicaSelector` and `broker.rack`.
- **Consumers:** set `client.rack` to the consumer's rack. If no suitable local replica exists, selection falls back to the leader.
- **Strimzi 1.2.0:** the following is a **configuration excerpt to merge into an existing Kafka CR**, not a complete deployment. KafkaNodePools, listeners, storage, and other configuration are also required. From Strimzi 1.0 the CR API is `v1`; specify the rack type too.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    rack:
      type: topology-label
      topologyKey: topology.kubernetes.io/zone
    config:
      replica.selector.class: org.apache.kafka.common.replica.RackAwareReplicaSelector
```

This configures the brokers' `broker.rack`. Set ordinary application consumers' `client.rack` separately. KafkaConnect, MirrorMaker 2, and Bridge have their own CR rack settings. Follow the [Strimzi documentation](https://strimzi.io/docs/operators/1.2.0/configuring.html) to distribute broker placement as well. Follower fetching can increase read latency because of replication lag.

[KIP-881](https://cwiki.apache.org/confluence/display/KAFKA/KIP-881%3A+Rack-aware+Partition+Assignment+for+Kafka+Consumers) concerns rack-aware partition assignment, a separate mechanism. Check consumer-version and assignor support. See [Kafka on EKS](../data-on-eks/kafka/README.md) for deployment guidance.

### Redis/Valkey (ElastiCache): AZ-Affinity Read Strategies

These are the principal [Valkey GLIDE](https://valkey.io/blog/az-affinity-strategy/) `ReadFrom` choices discussed here. GLIDE 2.5.2 also has `ALL_NODES`; this is not the complete enum list.

| Strategy | Behavior |
|----------|----------|
| `PRIMARY` | Read from the primary (default) |
| `PREFER_REPLICA` | Round-robin across replicas, then primary if no replica is available |
| `AZ_AFFINITY` | Local replicas first, then other replicas or primary |
| `AZ_AFFINITY_REPLICAS_AND_PRIMARY` | Local replicas → local primary → replicas or primary in other AZs |

Consider replica reads when the application tolerates stale data; read percentage alone does not determine the strategy. Verify server AZ-metadata support/configuration, primary load, and fallback. Design requests needing **freshness or read-after-write** separately, for example with primary reads where appropriate for the data model.

This `valkey-glide==2.5.2` example **creates configuration for cluster mode** without opening a connection. It enables TLS; supply `credentials` where authentication is required. For cluster mode disabled, use `GlideClientConfiguration` and `GlideClient` instead.

```python
from glide import GlideClusterClientConfiguration, NodeAddress, ReadFrom


def cache_config(host: str, client_az: str, credentials=None):
    if not host or not client_az:
        raise ValueError("Cache endpoint and client AZ are required")
    return GlideClusterClientConfiguration(
        addresses=[NodeAddress(host, 6379)],
        use_tls=True,
        credentials=credentials,
        read_from=ReadFrom.AZ_AFFINITY_REPLICAS_AND_PRIMARY,
        client_az=client_az,
    )
```

The [HotelTrader case study](https://aws.amazon.com/blogs/database/how-hoteltrader-cut-inter-az-cost-95-and-latency-by-49-with-valkey-glide-on-amazon-elasticache/) reports 95% lower inter-AZ transfer cost and 49% lower average latency after **both AZ-aware routing and request batching**. These are results from that ECS/ElastiCache workload, not guarantees for the routing option alone.

### Aurora/RDS: Reader Endpoint Limits and Alternatives

Aurora's [default reader endpoint](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Reader.html) balances **connections** across read replicas; it does not guarantee AZ preference or per-query balancing. With no replicas, it can connect to the writer. DNS changes alone do not move existing pooled connections to another instance.

1. **Per-AZ custom endpoints:** explicitly select instance IDs after verifying their AZ and reader role. Replace the names in this creation example with real resources.

   ```bash
   aws rds create-db-cluster-endpoint \
     --db-cluster-identifier my-aurora-cluster \
     --db-cluster-endpoint-identifier reader-az-a \
     --endpoint-type READER \
     --static-members db-instance-az-a-1 db-instance-az-a-2
   ```

   The CLI/API supports `READER` endpoints. A member promoted to writer is excluded, and new replicas are not automatically added to a static list. Check [membership behavior](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Custom.Considerations.html) and provide an application fallback endpoint or explicit failure policy when no local reader remains.

2. **AWS Advanced JDBC Wrapper 4.4.0:** [`fastestResponse`](https://github.com/aws/aws-advanced-jdbc-wrapper/blob/4.4.0/docs/using-the-jdbc-driver/HostSelectionStrategies.md) selects a host using measured response time. Also load the `fastestResponseStrategy` plugin. This is not an AZ-label constraint; the fastest host is not guaranteed to be local.

[Issue #1139](https://github.com/aws/aws-advanced-jdbc-wrapper/issues/1139) was **closed in May 2025** after discussion that the response-time feature in 2.5.5 met the request. It is not an open feature request proving custom endpoints are the only solution.

### Complementary Kubernetes Service-Layer Options

[Topology Aware Routing](https://kubernetes.io/docs/concepts/services-networking/topology-aware-routing/) and [Istio Zone-Aware Routing](../service-mesh/istio/resilience/03-zone-aware-routing.md) complement Service endpoint selection. Local endpoint shortages, health changes, and configuration can send traffic to other AZs. They do not automatically control external DB/cache/Kafka connections. Preference is not a guarantee that the entire read path remains in one AZ.

***

## Recommended Combination Summary

| Layer | Selection criteria | Alternative/fallback |
|-------|--------------------|----------------------|
| Architecture | Independent cell operations and healthy-cell capacity | A multi-AZ single cluster remains a valid choice |
| Traffic shifting | LB forward-action weights and TGB target registration | Route 53 selects LB endpoints |
| Failure response | Manual zonal shift / separately enabled autoshift | Single-AZ worker cells need external cell routing |
| Upgrades | Tested eligibility, compatibility, and recovery time | Blue/green, with data recovery handled separately |
| Kafka reads | Broker selector plus matching consumer rack | Leader when no suitable local replica exists |
| Cache reads | GLIDE strategy matching freshness and AZ metadata | Verify remote fallback and primary load |
| DB reads | Maintained local reader list or response-time selection | Handle missing local readers and reconnection |

Measure load, cost, and recovery-time baselines, then rehearse traffic shifts and rollback outside production. Read-path optimization can also be introduced independently: validate consistency, fallback, and cost on a small scope before expanding.

***

< [Previous: Tekton Pipelines](14-tekton-pipelines.md) | [Table of Contents](./README.md) | [Next: Troubleshooting Playbook](16-troubleshooting-playbook.md) >
