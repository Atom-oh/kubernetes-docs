# EKS Networking

> **Last Updated**: September 11, 2026

## Overview

This chapter covers VPC/subnet planning and security-group paths for a conventional EKS cluster. AWS manages the control plane in AWS-managed infrastructure; the customer VPC contains the cluster connectivity ENIs, node/Pod interfaces and load-balancer/endpoint resources. Do not interpret the customer VPC boundary as the physical location of the managed control plane or regional S3/ECR/STS services.

## EKS Networking Architecture

<!-- Audit 2026-09-11: parent asset repair required. MoveAWS-managedcontrolplaneandregionalS3/ECR/STSservicesoutsidethecustomerVPCboundary;showcustomerclusterENIs/interfaceendpointendsinsideVPC. ScopeNATpathasIPv4internetexample,notalltraffic.
![EKS networking architecture overview showing traffic from the internet through the IGW to the ALB in the public subnet and worker nodes in the private subnet.](../.gitbook/assets/en-eks-03-eks-networking-part1-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-03-eks-networking-part1-0.html)
-->

| Component | Role |
| --- | --- |
| VPC and subnets | Address/routing boundaries; each subnet belongs to one AZ |
| Route tables | Select next hops for destination ranges |
| Internet gateway | Attaches to the VPC; public subnets route to it |
| Public NAT gateway | Provides a common private-IPv4 internet-egress path when placed in a public subnet with an EIP/IGW route |
| Security groups | Stateful rules associated with supported network interfaces/resources |
| Network ACLs | Stateless subnet-boundary rules, including required return traffic |
| CNI | Configures Pod networking; behavior depends on the selected implementation/mode |

### Traffic Paths

<!-- Audit 2026-09-11: parent asset repair required. NodePortusesallocatedportsfromthedefaultrange,nottheentire30000–32767rangeoneverynode;separateNLBServicefromALBIngress/GatewayandIPvsinstancetargetpaths. KOPNGfooterappearscropped;parentfullPagecapture.
![Diagram of how kubectl calls, kubelet traffic, pod-to-pod traffic, and service traffic flow inside an EKS cluster.](../.gitbook/assets/en-eks-03-eks-networking-part1-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-03-eks-networking-part1-1.html)
-->

Pod-to-Pod traffic can stay on one node or cross node interfaces/VPC routes. Same-node traffic does not necessarily traverse the VPC fabric, so VPC Flow Logs are not a complete record of all Pod communication. Service traffic uses the configured service-proxy path and selected backends; a Service is not a dedicated forwarding appliance. External ingress and egress depend on scheme, routes, target type and security controls. Control-plane traffic is a separate path from application traffic.

![Diagram showing how EKS networking components connect across three lanes: inbound, outbound, and control-plane traffic.](../.gitbook/assets/en-eks-03-eks-networking-part1-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-03-eks-networking-part1-2.html)

The figure illustrates public ingress and zonal-NAT IPv4 egress. It is one design, not a requirement to create public subnets/NAT for every EKS cluster. Fully private endpoints, centralized egress and native IPv6 paths have different requirements and costs.
## VPC and Subnet Requirements

<!-- Audit 2026-09-11: parent asset repair required. InternetaccessisnotuniversalEKSprerequisite;fullyprivateendpointsareanalternative. IGWattachesVPC,notpublicsubnet. Replacearbitrarysmall/mediumCIDRswithmeasuredplanninginputs.
![Diagram of the EKS VPC prerequisite checklist, moving from subnets through IP space and DNS to internet access.](../.gitbook/assets/en-eks-03-eks-networking-part1-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-03-eks-networking-part1-3.html)
-->

* For a regional EKS cluster, select eligible subnets in at least two AZs. Each cluster subnet needs at least six available IPs for EKS; AWS recommends at least sixteen. Leave room for replacement control-plane ENIs during upgrades and for other resources.
* Enable VPC DNS support and DNS hostnames. Cluster subnets and node/Pod subnets need not be identical, but all paths must be routable as required.
* Nodes need access to the Kubernetes API, image registries and the AWS services they use. This does not always require public internet access: private endpoints/mirrors can supply those paths. The EKS AWS-service endpoint is distinct from the cluster Kubernetes API endpoint.
* Review custom control-plane egress routing if `controlPlaneEgressMode=CUSTOMER_ROUTED` is enabled; cluster-subnet routes and security rules must reach the required webhook/OIDC and other endpoints.
* Changing cluster subnets retains the original VPC/AZ-set constraints. Associating a new VPC CIDR is not instantaneous for every control-plane operation; AWS documents reconciliation that can take up to an hour.
### CIDR Planning

<!-- Audit 2026-09-11: parent asset repair required. Removeuniversal1–10node/24,10–100node/20,100+node/16and20–30%headroomguarantees;countreserved/ENI/warm/controlplane/LB/upgradeIPs. RFC1918onlylabeltoobroad;nonoverlapandsupportedCIDRrulesmatter.
![Diagram of the VPC CIDR planning procedure, from cluster sizing through IP demand, headroom, and overlap checks to the final CIDR.](../.gitbook/assets/en-eks-03-eks-networking-part1-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-03-eks-networking-part1-4.html)
-->

Plan addresses from expected nodes, ordinary and branch-ENI Pods, warm pools/prefix blocks, control-plane interfaces, load balancers/endpoints, growth and update capacity. Check overlap with service CIDRs, connected VPCs and on-premises networks. Node count alone does not select a safe VPC CIDR, and a fixed 20–30% reserve is not a universal capacity rule.

The following are **total IPv4 address counts**, not cluster-size recommendations or usable Pod capacity:

| CIDR | Total addresses |
| --- | ---: |
| /24 | 256 |
| /22 | 1,024 |
| /20 | 4,096 |
| /16 | 65,536 |

For ordinary AWS IPv4 subnet allocations, AWS reserves the first four and last address of each subnet: a /24 therefore has 251 assignable addresses and a /22 has 1,019, before workloads and infrastructure consume any. This is per subnet, not five addresses for the entire VPC; BYOIP has documented exceptions. Existing subnet CIDRs cannot simply be enlarged in place. Prefix delegation requires contiguous blocks and does not create new address space.
### Example Subnet Design

<!-- Audit 2026-09-11: parent asset repair required. Private10.0.2.0/22and10.0.6.0/22arenoncanonical;canonicalfirstoverlapspublicsubnets. Use10.0.4.0/22and10.0.8.0/22;showzonalpublicNATplacementandIGWroute;rawIPcountsnotusable.
![EKS subnet design diagram pairing a public subnet, NAT Gateway, and private subnet in each of two Availability Zones.](../.gitbook/assets/en-eks-03-eks-networking-part1-5.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-03-eks-networking-part1-5.html)
-->

For a VPC of `10.0.0.0/16`, these aligned ranges do not overlap. They illustrate a public-load-balancer/zonal-NAT design, not measured sizing. A public subnet has an associated route to an IGW; a tag or subnet name does not make it public. Private nodes can use NAT or the appropriate private service endpoints.

| Type | AZ | CIDR | Example use |
| --- | --- | --- | --- |
| Public | us-west-2a | 10.0.0.0/24 | Public load balancers and zonal NAT |
| Public | us-west-2b | 10.0.1.0/24 | Public load balancers and zonal NAT |
| Private | us-west-2a | 10.0.4.0/22 | Worker nodes/Pods |
| Private | us-west-2b | 10.0.8.0/22 | Worker nodes/Pods |

The former `10.0.2.0/22` and `10.0.6.0/22` were not aligned network addresses. AWS canonicalizes CIDRs; the former first range would become `10.0.0.0/22` and overlap the public subnets. Validate network boundaries and overlap before provisioning. AZ-local NAT paths avoid a cross-AZ NAT dependency, but redundant capacity/routes and workload placement still need review.
### Subnet Discovery Tags

<!-- Audit 2026-09-11: parent asset repair required. Tagrequirementsdependcontroller/version/features;LBC>=2.12.1canuseSubnetDiscoveryByReachabilitywithoutroletags. owned/sharedarenotsecurityisolation;privatesubnetscanhaveegress. Removewithouttagsalwaysfailsclaim.
![Diagram of the AWS Load Balancer Controller discovering public and private subnets by tag to place internet-facing and internal load balancers.](../.gitbook/assets/en-eks-03-eks-networking-part1-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-03-eks-networking-part1-6.html)
-->

Discovery belongs to the selected controller and version. For AWS Load Balancer Controller 3.5, role tags guide public/internal subnet selection; eligible values are `1` or an empty value. Modern LBC does not universally require the old cluster ownership tag. With no role-tag candidates, LBC 2.12.1+ can use route-based discovery when `SubnetDiscoveryByReachability` is enabled. Cluster-tag filtering, free IPs and per-AZ selection still matter. EKS Auto Mode has its own documented tag requirements.

* Internet-facing placement: `kubernetes.io/role/elb`.
* Internal placement: `kubernetes.io/role/internal-elb`.
* `kubernetes.io/cluster/<cluster-name>` may affect filtering/priority; `owned`/`shared` are not security boundaries or automatic routing rules.

```bash
# After reviewing subnet ownership and its associated routes, tag the intended public subnet.
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" --subnet-ids "${PUBLIC_SUBNET_ID:?}" \
  --query 'Subnets[].{id:SubnetId,vpc:VpcId,cidr:CidrBlock,free:AvailableIpAddressCount,tags:Tags}'
aws ec2 create-tags --region "$EXAMPLE_REGION" --resources "$PUBLIC_SUBNET_ID" \
  --tags Key=kubernetes.io/role/elb,Value=1
```
Use the internal-elb role tag for a reviewed private/internal placement instead. Do not tag arbitrary existing subnets or disable cluster-tag checks to work around an unreviewed discovery failure. Explicit subnet selection must still meet load-balancer eligibility requirements.
### Security-Group Paths

<!-- Audit 2026-09-11: parent asset repair required. Replace1025–65535kubeletrangewithactualTCP10250;distinguishprivateAPI443,DNS53,webhook/workloadports,andstatefulSGvsNACLreturnports. EKSdefaultclusterSGmaybesharedwithMNG;publicAPIusesCIDRs;alloutboundnotuniversalneed.
![Diagram of the 443/TCP and 1025-65535/TCP rules between the control plane and worker node security groups, plus node-to-node and outbound paths.](../.gitbook/assets/en-eks-03-eks-networking-part1-7.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-03-eks-networking-part1-7.html)
-->

EKS creates a default cluster security group and associates it with cluster ENIs and, normally, managed-node interfaces. It is not a universal two-group layout. Additional cluster SGs are not automatically node SGs; custom launch-template groups and Pod security groups change the paths. Inspect actual associations before editing rules:

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,subnets:subnetIds,public:endpointPublicAccess,private:endpointPrivateAccess,publicCIDRs:publicAccessCidrs}'
```

| Flow | Typical destination port | Scope to review |
| --- | --- | --- |
| Nodes / authorized connected clients → private Kubernetes API | TCP 443 | Cluster endpoint SGs and approved sources |
| Control plane → kubelet | TCP 10250 | Target node SGs and routes |
| Nodes/Pods → DNS backend | UDP and TCP 53 | Actual CoreDNS/NodeLocal DNS path |
| Control plane → admission webhook | Configured backend port | Webhook Service/endpoint and SG path |
| Application / load balancer → workload | Configured application/health-check ports | Target type, target SGs and health checks |

AWS documents TCP 443, TCP 10250 and TCP/UDP 53 to the cluster SG as the minimum outbound set when narrowing the default cluster SG, plus the actual application, inter-node and service-access requirements. The old `1025–65535` kubelet range is not that minimum. SGs are stateful; allowed return traffic does not require blindly opening the ephemeral range. NACLs are stateless and must allow the corresponding return paths.

Default self-ingress and self-egress/EFA rules can be recreated on cluster updates. Adding a narrow SG does not negate a broader allow rule in another attached SG. Public API access uses `publicAccessCidrs`; the cluster SG controls the private endpoint path. Review egress for registries/AWS APIs and use the appropriate endpoints or routes rather than assuming every cluster requires `ALL → 0.0.0.0/0`.

## Next Steps and Quiz

[EKS Networking Part 2](./03-eks-networking-part2.md) covers services, load balancing and policies. Check your understanding with the [Part 1 quiz](../quizzes/eks/03-eks-networking-part1-quiz.md).

## References

- [EKS VPC/subnets](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [Private clusters](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)
- [Subnet sizing](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)
- [Security groups](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html)
- [LBC subnet discovery](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/subnet_discovery.md)
