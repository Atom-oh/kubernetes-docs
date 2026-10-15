# 5. Cloud and CNI Network Design Workbook

> **Last Updated**: September 15, 2026

**Prerequisites:** [Protocols](01-protocol-projects.md), [routing](02-routing-policy-convergence.md), [Linux observation](04-linux-performance.md), and Kubernetes Pod/Service/EndpointSlice concepts. Live observation requires an approved existing lab account/cluster and the necessary read permissions.

**Goal:** Connect design, observations and policy from DNS to the backend and return path. Commands in this chapter query existing resources; they do not create resources or inject faults. Without an account, complete the design exercises and label the result **design review**.

Prepare AWS CLI and a kubectl version compatible with the cluster, then verify the lab profile/context. If a tool is absent, follow the platform-specific [AWS CLI installation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and [kubectl installation](https://kubernetes.io/docs/tasks/tools/) instructions. This workbook does not assume tool installation or credential issuance succeeded automatically.

## 1. Turn the AWS scope into questions {#design-questions}

The [official AWS Advanced Networking scope](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html) covers cloud/hybrid design, implementation, operations, security and automation. Apply each area as a question about your design.

| Area | Question | Evidence |
|---|---|---|
| Addressing/routing | What destination prefix and next hop apply, and is there a return path? | VPC/subnet/TGW routes and actual source/destination addresses |
| Name resolution | Which resolver, zone or forwarding rule answers? | Query name/type, resolver, answer, TTL and time |
| Entry point | What frontend does DNS select, and what backend is registered? | Listener, target type/port, health check and actual target |
| Isolation | Which layer enforces allowed and forbidden flows? | SG/NACL/CNI policy scope and observed enforcement |
| Resilience | Which flows are affected when one component fails? | Failure boundary, alternative path, state/recovery plan |
| Performance/cost | What conditions govern latency, throughput, address capacity and data movement? | Measurement interval/direction/resources and current cost inputs |

Exam scope maps learning topics. It is not a deployment answer key or a performance guarantee for a particular design.

## 2. Establish environment and permission {#inventory}

Replace these names with **actual approved lab values**. The strings below are not working account details.

```bash
LAB_AWS_PROFILE='REPLACE_WITH_LAB_PROFILE'
LAB_AWS_REGION='REPLACE_WITH_LAB_REGION'
LAB_CONTEXT='REPLACE_WITH_LAB_KUBERNETES_CONTEXT'
LAB_NAMESPACE='REPLACE_WITH_LAB_NAMESPACE'
LAB_SERVICE='REPLACE_WITH_LAB_SERVICE'
```

**Operator-approved query terminal:**

```bash
aws --version
kubectl version --client
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  sts get-caller-identity
kubectl --context "$LAB_CONTEXT" auth can-i get services -n "$LAB_NAMESPACE"
kubectl --context "$LAB_CONTEXT" auth can-i list endpointslices.discovery.k8s.io \
  -n "$LAB_NAMESPACE"
```

Stop when the account, role or context differs from the lab target. `no`, `AccessDenied` and expired credentials indicate unavailable observation access. Do not automatically grant administrator permissions or retry against another account. Ask an authorized operator for the minimum evidence needed.

Keep original account IDs, ARNs, IPs and resource names in approved notes. Use consistent aliases in a public report. Collecting configuration credentials, Secrets or tokens is unnecessary.

## 3. Map a request to actual resources {#request-path}

Select one request's hostname, protocol, port and time. The following are relationships to check, not necessarily separate physical hops.

| Observation target | Relationship | Common mistake |
|---|---|---|
| DNS | Frontend address returned by the selected resolver | Treating name resolution as TCP/HTTP success |
| LB listener/target group | Frontend protocol/rule and target type/port | Assuming listener and backend ports are equal |
| Service | Selector or separately managed endpoints, port/targetPort | Assuming a Service object guarantees endpoints |
| EndpointSlice/Pod | Actual address/port, readiness, node and timestamp | Equating endpoint readiness with LB health |
| CNI/node/VPC | Addressing, routes, policy and forwarding implementation | Assuming all EKS compute modes use the same DaemonSet and path |
| Return path | Reply destination, SNAT, state tracking and routing | Concluding bidirectional success from forward reachability |

AWS Load Balancer Controller is a **control-plane** reconciler using AWS APIs. Application requests do not traverse its controller Pod.

An ordinary `ip` target connects to a registered backend IP; an `instance` target uses a node/NodePort path. Check the supported compute/CNI combination, actual registrations, proxy implementation and traffic policy. Service describes logical endpoint selection: do not always draw ClusterIP as another packet hop. Read the [AWS target-type explanation](https://docs.aws.amazon.com/eks/latest/best-practices/load-balancing.html) alongside [Kubernetes virtual IP implementation](https://kubernetes.io/docs/reference/networking/virtual-ips/).

### Observe Service and EndpointSlice

```bash
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get service "$LAB_SERVICE" \
  -o jsonpath='{.spec.type}{"\n"}{.spec.selector}{"\n"}{.spec.ports}{"\n"}{.spec.externalTrafficPolicy}{"\n"}'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get endpointslices.discovery.k8s.io \
  -l "kubernetes.io/service-name=$LAB_SERVICE" -o json
```

Correlate addresses and conditions **within the same endpoint object**. Do not flatten address and `ready` arrays separately and invent their pairing. `items: []` means no endpoint was observed with that selection; it does not identify DNS or firewall as the cause. Consider Services without selectors and manually managed endpoints.

After verifying the actual selector, query only the relevant Pods.

```bash
LAB_SELECTOR='REPLACE_WITH_VERIFIED_KEY=VALUE'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get pods -l "$LAB_SELECTOR" -o wide
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" get networkpolicies
```

A NetworkPolicy object list does not prove that a policy engine is enabled or enforcement works. Separately establish CNI, compute mode, supported API, selected Pods, direction, ports and actual traffic. Other policy CRDs or managed policies require evidence from their respective owners.

### Observe AWS targets and routes

Specify the operator-verified target group and VPC. Also record evidence connecting that target group to the selected Service.

```bash
LAB_TARGET_GROUP_ARN='REPLACE_WITH_VERIFIED_TARGET_GROUP_ARN'
LAB_VPC_ID='REPLACE_WITH_LAB_VPC_ID'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-groups --target-group-arns "$LAB_TARGET_GROUP_ARN" \
  --query 'TargetGroups[].{Type:TargetType,Port:Port,Protocol:Protocol,Vpc:VpcId,HealthPath:HealthCheckPath}'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-health --target-group-arn "$LAB_TARGET_GROUP_ARN"
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  ec2 describe-route-tables --filters "Name=vpc-id,Values=$LAB_VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
```

`healthy` is the result of the configured health check, not an end user's entire DNS/TLS/authorization/request path. For a `null` field, first determine whether that protocol/configuration requires it. A target type outside this workbook's `ip`/`instance` model requires a revised path model.

Without an explicit subnet route-table association, check whether the main table applies. Connect destination, target and route state to the actual source subnet, then inspect the destination's return path. Do not fill missing permissions or telemetry with assumptions.

## 4. Hybrid design exercise {#hybrid-design}

**Design scenario:** Production VPC A needs shared DNS/services. Development VPC B must not directly access A's data service. On-premises clients may access only designated shared services. Use aliases when actual addresses/accounts are unavailable.

1. Record source, destination, protocol, allow/deny intent and return path.
2. Distinguish VPC/subnet/TGW route tables from attachments.
3. Separate TGW **association**, which selects the attachment's lookup table, from **propagation**, which installs learned routes. An attachment can associate with one table and propagate into multiple tables. Propagation does not make an attachment use that table.
4. State the responsibilities of routing separation and SG/NACL/workload policy.
5. Identify private zones, resolvers, forwarding rules and bidirectional DNS paths.
6. Consider overlapping CIDRs, missing return routes and incorrect propagation one at a time, explaining affected flows.

Check the [TGW association/propagation explanation](https://repost.aws/knowledge-center/transit-gateway-connect-vpcs-from-vpn) and compare a real environment with [Cross-Org VPC connectivity](../05-cross-org-vpc-connectivity.md). BGP policy knowledge helps express intent; on-premises device commands are not applied directly to TGW.

## 5. Reason from observations {#failure-workbook}

Use **supplied evidence or evidence collected with approval**. These are analysis exercises, not instructions to change production account policies.

| Observation | Next check | Unsupported conclusion |
|---|---|---|
| DNS answers but TCP fails | Target, port, route, access controls and listener | Healthy DNS proves a healthy backend |
| EndpointSlice is ready but target unhealthy | Registered IP/port, health-check configuration and path | Readiness equals LB health |
| Same-node succeeds, cross-node fails | Actual CNI/node/VPC path, policy, MTU and return route | A single cause called “CNI bug” |
| Only small requests succeed | Packet size, PMTU feedback, retransmission and application conditions | Every failure is an MTU problem |
| Only one TGW direction works | Associations and both sides' route tables | Propagation automatically guarantees the return path |

Packet/host observation requires its own permissions and vantage point. Do not describe resource `get` output as a measured kernel forwarding path. Obtain node/Pod namespace observations from an authorized operator or a separately prepared lab guide.

## 6. Deliverables and completion {#completion}

- Allowed/forbidden flow matrix and forward/return path diagram.
- Actual role of each component: control plane, routing, policy or application.
- Service/EndpointSlice/target/route evidence tied to context, target and timestamp.
- At least two hypotheses, with reasons for confirmed, rejected or unknown status.
- Pre-deployment checks, observation scope, recovery owner and post-recovery checks.

Without live evidence, mark **design review complete**, not cloud operational validation complete. Queries in this chapter do not change resources, so no network restoration command is required. Manage saved originals under the approved retention/disposal rules.

## Related reading

- [EKS networking](../../eks/03-eks-networking-part1.md), [VPC CNI](../01-vpc-cni.md), [AWS Load Balancer Controller](../03-aws-lb-controller.md)
- [Pod benchmark conditions](../06-pod-network-benchmark.md), [Cilium visibility](../cilium/06-security-visibility.md)
- [EKS network policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [NLB/EKS support conditions](https://docs.aws.amazon.com/eks/latest/userguide/network-load-balancing.html)
- [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [AWS CLI target health](https://docs.aws.amazon.com/cli/latest/reference/elbv2/describe-target-health.html)

[Previous: Linux performance](04-linux-performance.md) · [Quiz](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) · [Next: Automation and assessment](06-automation-capstone.md)
