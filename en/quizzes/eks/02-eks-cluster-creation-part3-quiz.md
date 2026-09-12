# EKS Cluster Creation Quiz - Part 3

> **Last Updated**: September 11, 2026

This quiz covers EKS networking, node capacity, multi-tenancy, autoscaling, and node security. Commands and manifests are learning examples; cloud deployment and end-to-end behavior have not been executed during this review. Confirm the target account, Region, kubeconfig, compatible add-on versions, and resource ownership before using them.

## Basic Concept Questions

1. In the conventional IPv4 secondary-IP calculation, what determines ENI and per-ENI address limits?
   * A) Namespace name
   * B) EC2 instance type
   * C) Service name
   * D) Deployment name

<details>
<summary>Show Answer</summary>

**Answer: B) EC2 instance type**

For Linux IPv4 **secondary-IP mode**, with sufficient subnet addresses and no custom networking or security groups for Pods, the instance type supplies the ENI and per-ENI address limits. This estimates the conventional node Pod limit, not “IP addresses per Pod.”

The conventional formula reserves the primary address of **each** ENI:

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
```
The extra two are the historical host-network allowance for `aws-node` and `kube-proxy`. The table preserves this secondary-IP calculation; it is **not** the effective `maxPods` for every AMI, CNI mode, or managed node group.

| Instance Type | Max ENIs | IPs per ENI | Max Pods |
| ------------- | -------- | ----------- | -------- |
| t3.small      | 3        | 4           | 11       |
| t3.medium     | 3        | 6           | 17       |
| m5.large      | 3        | 10          | 29       |
| m5.xlarge     | 4        | 15          | 58       |
| m5.2xlarge    | 4        | 15          | 58       |
| m5.4xlarge    | 8        | 30          | 234      |
| c5.large      | 3        | 10          | 29       |
| c5.xlarge     | 4        | 15          | 58       |
| r5.large      | 3        | 10          | 29       |
| r5.xlarge     | 4        | 15          | 58       |

**Check actual capacity and EC2 limits:**

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,CAPACITY:.status.capacity.pods,ALLOCATABLE:.status.allocatable.pods
aws ec2 describe-instance-types --region us-west-2 \
  --instance-types m5.large m5.4xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4PerENI:NetworkInfo.Ipv4AddressesPerInterface}'
```
Subnet exhaustion can stop Pod creation even below the node limit. CPU/memory requests, other host-network Pods, custom networking, security groups for Pods, and kubelet configuration also matter. Managed node groups cap `maxPods` at 110 for instances with fewer than 30 vCPUs and 250 otherwise, independently of the larger formula result.

IPv4 prefix delegation assigns a `/28` to one secondary-address **slot** on an ENI; several prefixes can occupy one ENI. It does not create more subnet address space. See question 5 for prerequisites and migration.

For a custom AL2023 AMI, configure `spec.kubelet.config.maxPods` in NodeConfig after calculating and testing a suitable value. With a managed node group and no custom AMI ID, EKS calculates the recommended value. Raising kubelet’s limit alone cannot make IP addresses or compute capacity available. Do not pass the nonexistent eksctl `--kubelet-extra-args` option.

</details>

2. With no NetworkPolicy selecting a Pod, what is its NetworkPolicy isolation state?
   * A) Non-isolated, subject to other network controls
   * B) Same-namespace traffic only
   * C) Explicit allow rules required
   * D) All traffic denied

<details>
<summary>Show Answer</summary>

**Answer: A) Non-isolated, subject to other network controls**

Without a policy selecting a Pod for a traffic direction, Kubernetes NetworkPolicy leaves that direction non-isolated. This does **not** bypass security groups, route tables, NACLs, other policy APIs, or an application's listener.

Amazon VPC CNI has native NetworkPolicy enforcement when enabled on supported Linux EC2 nodes. Current standard/admin policy guidance requires VPC CNI 1.21 or later and kernel 5.10 or later; verify the selected add-on's compatibility. Windows and Fargate are not covered by that enforcement path. Use controller-managed Pods (for example Deployments) and check AWS's interface and Service-port limitations.

Calico policy with AWS VPC networking and Cilium AWS-CNI chaining are alternatives with their own installation requirements. Do not install an unconfigured second CNI or stack policy agents unintentionally. AWS Network Firewall filters routed VPC traffic; it does not implement Kubernetes NetworkPolicy selectors.

The examples below are for a **new, dedicated** `network-policy-lab` namespace. The first policy isolates ingress only. The next two allow specific traffic; the `prod` peer requires both the built-in namespace label and the backend Pod label.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: network-policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: backend}
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector:
        matchLabels: {app: frontend}
    ports:
    - {protocol: TCP, port: 8080}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prod-to-database
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: database}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: prod
      podSelector:
        matchLabels: {app: backend}
    ports:
    - {protocol: TCP, port: 5432}
```
For egress isolation, separately allow the actual DNS path and application dependencies. A denied connection is meaningful only after baseline connectivity, DNS, readiness, and an allowed positive control succeed. Do not apply blanket deny policies to `kube-system` or a shared `default` namespace as a quick test.

</details>

3. Which is a conventional internet-egress path for a private IPv4 subnet?
   * A) Attach an IGW to the subnet
   * B) Route to a public NAT gateway, then to the VPC IGW
   * C) Give each Pod an Elastic IP
   * D) A private NAT gateway directly through an IGW

<details>
<summary>Show Answer</summary>

**Answer: B) Route to a public NAT gateway, then to the VPC IGW**

For private IPv4 nodes and Pods that need public IPv4 internet egress, a common design routes the private subnet's default route to a **public NAT gateway in a public subnet**. That public subnet routes to an internet gateway attached to the **VPC**, and the NAT gateway has an Elastic IP. A NAT instance is another design with additional routing, source/destination-check and operational requirements.

With the default IPv4 VPC CNI SNAT behavior, off-VPC Pod traffic first uses the node's primary IPv4 address. Public nodes with a public IPv4 address and an IGW route can use a different path. Native IPv6 egress can use an egress-only internet gateway; AWS service access through VPC endpoints may need no internet NAT. Do not treat NAT as a universal prerequisite for every Pod.

**One-AZ CloudFormation routing example:** this demonstrates public/private route associations; it is not a complete EKS VPC. EKS cluster subnets require at least two AZs. For a zonal NAT design, consider a NAT gateway and private route per AZ to avoid a cross-AZ dependency. NAT gateways and public IPv4 addresses incur charges. Review the complete EKS VPC template in the concept guide for a cluster deployment.

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: One-AZ IPv4 NAT routing demonstration; not a complete EKS VPC
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: EKS-VPC

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.0.0/24
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: Public-Subnet-1

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.2.0/24
      Tags:
        - Key: Name
          Value: Private-Subnet-1

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: EKS-IGW

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  NatGatewayEIP:
    Type: AWS::EC2::EIP
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatGatewayEIP.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: EKS-NAT-GW

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Public-RT

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Private-RT

  PrivateRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway

  PublicSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  PrivateSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PrivateSubnet1
      RouteTableId: !Ref PrivateRouteTable
```
The `SubnetRouteTableAssociation` resources are essential: creating routes in an unassociated table does not change either subnet's route.

After an independently reviewed deployment, inspect its actual IDs and routes. If creating a NAT gateway through the CLI instead, capture its returned ID and wait for `nat-gateway-available` before creating a route. A failed NAT creation must stop the workflow.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region}"
: "${VPC_ID:?Set the deployed VPC ID}"
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
aws ec2 describe-nat-gateways --region "$AWS_REGION" \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query 'NatGateways[].{Id:NatGatewayId,Subnet:SubnetId,State:State}'
```
eksctl's `vpc.nat.gateway: Single` is valid for its managed VPC creation workflow, but introduces a single-AZ dependency. `HighlyAvailable` creates a zonal NAT in each AZ. These options do not repair the routing of arbitrary existing subnets. For a lab stack, delete only the resources you created after removing dependent workloads/ENIs; confirm the NAT and its EIP are released.

</details>

4. Which Pod setting shares node networking instead of using a Pod branch ENI?
   * A) A matching Pod label
   * B) A matching ServiceAccount label
   * C) hostNetwork: true
   * D) A selected SecurityGroupPolicy

<details>
<summary>Show Answer</summary>

**Answer: C) hostNetwork: true**

A host-network Pod shares the node's network namespace and security groups. Security groups for Pods use branch ENIs for selected Pods with their own network namespace.

Prerequisites for this Linux EC2 example include a supported trunking instance type, a compatible VPC CNI, the cluster role's `AmazonEKSVPCResourceController` permissions, and `ENABLE_POD_ENI=true`. EC2 `t` families and EKS Auto Mode do not support this feature. Verify DNS, control-plane and application rules, branch-ENI capacity, and `POD_SECURITY_GROUP_ENFORCING_MODE`; SNAT and policy behavior differ between modes. Use the add-on owner's configuration workflow instead of applying an old CNI manifest.

SecurityGroupPolicy selects Pods with **either** `podSelector` or `serviceAccountSelector`; a specially created service account is not mandatory for pod selection. `ENIConfig` is a custom-networking resource and is not required merely to use Pod security groups.

For the service-account selector alternative below, first create a dedicated `pod-sg-lab` namespace, replace the SG placeholder with an existing reviewed group in the correct VPC, and meet the prerequisites. This sleeping client demonstrates selection; it does not prove database connectivity. A matching ServiceAccount label and the Pod's `serviceAccountName` are both present.

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: pod-sg-lab
spec:
  serviceAccountSelector:
    matchLabels:
      role: db-client
  securityGroups:
    groupIds:
    - sg-REPLACE_WITH_REVIEWED_GROUP
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: db-client
  namespace: pod-sg-lab
  labels:
    role: db-client
automountServiceAccountToken: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: pod-sg-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: db-client}
  template:
    metadata:
      labels: {app: db-client}
    spec:
      serviceAccountName: db-client
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
Alternatively, replace `serviceAccountSelector` with `podSelector: {matchLabels: {app: db-client}}`. Keep the policy and selected Pods in the same namespace. Verify a **newly created** Pod's branch ENI and actual allowed/denied connections; creating a policy does not retrofit running Pods. Clean up only this lab namespace and its policy after testing, and do not delete an SG still used by other resources.

</details>



5. What is the main capacity benefit of IPv4 prefix delegation?
   * A) Guaranteed faster Pod-to-Pod traffic
   * B) More Pod IP capacity per node
   * C) Public IPv4 addresses for every Pod
   * D) Automatic network isolation

<details>
<summary>Show Answer</summary>

**Answer: B) More Pod IP capacity per node**

In Linux IPv4 prefix mode, one `/28` (16 addresses) consumes one ENI secondary-address slot. Multiple prefixes may be attached to an ENI; the maximum ENI count itself does not increase. This can raise IP-based Pod density and reduce address-allocation API work, subject to kubelet and resource limits.

For `m5.large`, the conventional secondary-IP calculation gives 29 Pods. A compatible managed node group in prefix mode can use a recommended `maxPods` of 110, not an unrestricted “over 110.” The theoretical address slots are not an application capacity guarantee.

**Prerequisites and tradeoffs:**

* Use a supported Nitro instance and compatible CNI (the historical Linux IPv4 minimum is 1.9.0; select a currently supported build).
* The subnet needs contiguous `/28` blocks. A fragmented subnet can fail with `InsufficientCidrBlocks` despite having many free individual IPs. Subnet CIDR reservations can preserve prefix space.
* Prefixes consume real subnet addresses in blocks. They do not enlarge a CIDR or guarantee lower IP consumption, better utilization, or lower cost.
* `WARM_PREFIX_TARGET` specifies spare prefixes. `WARM_IP_TARGET` specifies spare IPs; `MINIMUM_IP_TARGET` sets a minimum total allocation. The latter two override `WARM_PREFIX_TARGET` when configured. Tune them against launch latency and unused address consumption.
* Plan replacement node groups and a controlled cordon/drain migration. Do not just toggle the variable and restart every Pod. Check PDBs, volumes, spare capacity and rollback; validate new nodes before removing old groups.

The following is a **new-cluster configuration example**, not an update command for an existing cluster. It uses private API access, so the administrator needs a routed management path. The compatible EKS default CNI build is selected when no version is supplied; record and review the actual resolved version before deployment. `withOIDC` participates in eksctl's CNI IAM integration; review the resulting role. The size bounds do not install an autoscaler.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: prefix-demo
  region: us-west-2
  version: "1.36"
vpc:
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
iam:
  withOIDC: true
addons:
- name: vpc-cni
  configurationValues: |
    {"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
managedNodeGroups:
- name: prefix-linux
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  privateNetworking: true
  disableIMDSv1: true
```

</details>

6. Which Kubernetes object contains the Corefile consumed by CoreDNS?
   * A) A node security group
   * B) The coredns ConfigMap
   * C) A StorageClass
   * D) A PodDisruptionBudget

<details>
<summary>Show Answer</summary>

**Answer: B) The coredns ConfigMap**

The `coredns` ConfigMap contains `data.Corefile`. The correct **configuration owner** depends on whether CoreDNS is an EKS managed add-on or self-managed.

For the managed add-on, both the AWS console and `aws eks update-addon --configuration-values` can customize supported fields. A direct ConfigMap edit can be overwritten on an add-on update: store the complete custom Corefile in the add-on's `corefile` configuration key. Preserve existing configuration keys and review the schema for the exact add-on version.

Use a new local working directory to save the current configuration before editing:

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?Set the cluster}"
: "${EXAMPLE_REGION:?Set the Region}"
: "${EXAMPLE_KUBECONFIG:?Set a private kubeconfig path}"
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --addon-name coredns > coredns-addon-before.json
COREDNS_VERSION=$(jq -er '.addon.addonVersion' coredns-addon-before.json)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --query configurationSchema --output text > coredns-schema.json
jq -e '(.addon.configurationValues // "{}") | fromjson | select(type == "object")' \
  coredns-addon-before.json > coredns-values-before.json
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  get configmap coredns -o json | jq -er '.data.Corefile' > Corefile.reviewed
```
Edit `Corefile.reviewed`, preserving the Kubernetes zone, forwarding, `ready`, health and monitoring plugins required by this installation. These are separate customization examples, not a replacement Corefile:

* Add static records to the existing server block; use the actual internal addresses:

```text
hosts {
    10.0.0.1 example.com
    10.0.0.2 api.example.com
    fallthrough
}
```
* Use a separate server block for a conditional forwarder; the upstream must be reachable and must not loop back to this CoreDNS service:

```text
example.org:53 {
    errors
    forward . 10.0.0.53
    cache 30
}
```
* Replace the existing cache stanza instead of adding a duplicate. `prefetch` duration needs a unit:

```text
cache {
    success 10000
    denial 5000
    prefetch 10 10m 10%
}
```
* Optional error-class query logging (review volume and sensitive names):

```text
log {
    class error
}
```
`autopath` is a separate plugin for server-side search-path completion, not a `kubernetes` subdirective. `autopath off` inside the Kubernetes block is invalid. To disable an existing `autopath @kubernetes`, remove that directive; do not add it to installations that never enabled it.

After schema and syntax review, update the **same** add-on version:

```bash
# After reviewing the complete Corefile and existing configuration:
jq --rawfile corefile Corefile.reviewed '.corefile = $corefile' \
  coredns-values-before.json > coredns-values-reviewed.json
COREDNS_UPDATE_ID=$(aws eks update-addon \
  --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --resolve-conflicts PRESERVE \
  --configuration-values file://coredns-values-reviewed.json \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --update-id "$COREDNS_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
The response may still be `InProgress`. Recheck this update ID until `Successful`; stop on failure and inspect its errors before making another change. Then verify Deployment readiness, logs, internal Service lookup and the custom DNS cases. Restore the saved configuration through the same owner if needed.

For self-managed CoreDNS, edit the reviewed ConfigMap through its GitOps/manifest owner. With `reload`, Corefile changes are detected after ConfigMap projection and the reload interval; a restart is not universally required. Watch reload errors and DNS behavior. Changes to Deployment settings may still need a rollout.

**Scaling and resources:** EKS managed CoreDNS supports an `autoScaling` configuration object when the chosen version meets AWS prerequisites. Keep only one controller responsible for replicas. The following CPU HPA is an **alternative for self-managed CoreDNS**, requiring Metrics Server and CPU requests; do not run it alongside EKS CoreDNS autoscaling:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns-autoscaler
  namespace: kube-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: coredns
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```
The 2–10 replica range and 60% target are examples, not measured sizing. Review memory, CPU throttling, cache growth, topology and DNS latency; change resources through the add-on schema or the self-managed workload owner rather than replacing an entire resources object by container array index.

</details>

7. Which combination supports logical isolation for trusted teams sharing one EKS cluster?
   * A) Namespaces alone
   * B) Namespaces, RBAC, enforced policies and quotas
   * C) Node selectors alone
   * D) A shared cluster-admin role

<details>
<summary>Show Answer</summary>

**Answer: B) Namespaces, RBAC, enforced policies and quotas**

For mutually trusted teams sharing a cluster, namespaces plus RBAC, enforced network policies and quotas provide useful logical separation. They are not a universal solution for hostile tenants.

The platform administrator creates new `tenant-a`/`tenant-b` namespaces and enforces an appropriate Pod Security Admission policy (for this Linux EKS 1.36 example, Restricted with version `v1.36`). The following is the `tenant-a` policy set; apply equivalent, reviewed policy for `tenant-b`. An authenticated group mapping for `tenant-a-users` is also required.

Application permissions are explicit. The tenant cannot directly change ResourceQuota, LimitRange, NetworkPolicy, Roles or RoleBindings through this Role. Cluster-scoped resources remain platform-owned.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```
**Limits and validation:**

* Workload creation can still use accessible service accounts and mount Secrets in the namespace. This Role is not a Secret-confidentiality boundary within a tenant. Enforce permitted identities, mounts and security settings with admission policies; keep platform credentials outside tenant namespaces.
* The DNS rule assumes ordinary CoreDNS Pods labeled `k8s-app=kube-dns` in `kube-system`. Adapt and test for NodeLocal DNSCache or another DNS path. It allows DNS queries, not all egress to system Pods; it does not hide cross-namespace DNS names.
* Quotas cap admitted resource requests/counts; they do not reserve physical nodes, guarantee bandwidth, or eliminate noisy neighbors. LimitRange values are illustrative defaults.
* Verify effective permissions and policy enforcement with a tenant identity, allowed connections, denied cross-tenant connections, and quota rejection cases before onboarding.
* Dedicated node groups reduce some sharing but node selectors/taints alone are not security boundaries. For stronger isolation, evaluate sandboxed runtimes, virtual control planes or separate clusters/accounts/networks, including their shared dependencies and operational costs.

Namespace sharing can reduce control-plane overhead and simplify centralized operations. The required isolation level, not a universal “optimal” claim, determines the design.

</details>

8. Which item does not itself change an EC2 instance type’s technical capacity?
   * A) vCPU and memory size
   * B) Network and storage limits
   * C) A display-only name tag
   * D) ENI and address limits

<details>
<summary>Show Answer</summary>

**Answer: C) A display-only name tag**

Instance selection must consider CPU, memory, accelerator needs, architecture-compatible images/AMIs and drivers, Pod density, network bandwidth, EBS/instance-store performance, AZ availability, interruption tolerance and cost. Kubernetes version can matter through supported AMIs, drivers and features; it is not irrelevant.

The original family examples below illustrate workload shapes, not a current price/performance ranking. `m5` is general purpose, `r5` is memory optimized and `c5` is compute optimized. Graviton alternatives require Arm-compatible images and dependencies. GPU workloads additionally need an appropriate accelerated AMI and device plugin. Instance-store data is ephemeral; labels alone do not provide database durability or placement.

These are **alternative node-group configuration files** for an existing, reviewed cluster (`eksctl create nodegroup -f ...`), using unused group names and private subnets with required egress/endpoints. Review actual region/AZ offerings. Bounds do not install Cluster Autoscaler; a batch group at zero needs a correctly configured autoscaler or manual scaling.

**Web servers**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: web-servers
  instanceType: m5.large
  minSize: 2
  maxSize: 10
  labels:
    role: web
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**Database workloads**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: database-nodes
  instanceType: r5.xlarge
  minSize: 3
  maxSize: 5
  labels:
    role: database
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**Batch processing**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: batch-processors
  instanceType: c5.2xlarge
  minSize: 0
  maxSize: 20
  labels:
    role: batch
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**Interruptible Spot workers**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: spot-workers
  instanceTypes:
  - m5.large
  - m5a.large
  - m5d.large
  - m5ad.large
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    lifecycle: spot
  amiFamily: AmazonLinux2023
  privateNetworking: true
```
EKS provides 14 months of standard version support followed by 12 months of extended support. Check the EKS support calendar, upgrade requirements and add-on compatibility separately from upstream Kubernetes releases. These examples do not claim measured cost savings or capacity.

</details>

9. Which Kubernetes object constrains voluntary Pod eviction during a drain?
   * A) StorageClass
   * B) PodDisruptionBudget
   * C) ConfigMap
   * D) IngressClass

<details>
<summary>Show Answer</summary>

**Answer: B) PodDisruptionBudget**

A PDB constrains voluntary evictions through the Eviction API. It is one part of an update strategy, not a guarantee of availability. Node failure, direct Pod deletion and a Deployment's own rolling update are not prevented by a PDB.

For a reviewed `update-lab` Deployment with three replicas labeled `app=my-app`, this example permits eviction only when at least two selected healthy Pods remain:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
An alternative is `maxUnavailable: "50%"`; specify only one budget field. Percentage rounding is **up**, so this allows two unavailable Pods out of three, or one out of one. It is not a promise that at least half remain. Choose budgets against quorum, readiness, workload behavior and spare schedulable capacity.

Managed node-group `DEFAULT` updates launch replacement capacity before draining selected old nodes. `MINIMAL` reduces temporary capacity needs by terminating selected old nodes first. `maxUnavailable` controls concurrent node unavailability; PDBs constrain Pod eviction separately. Avoid `--force` as a routine response to a blocked drain because it can override Pod eviction protection.

Configure the node update policy and wait for this specific update to succeed **before** starting a version update:

```bash
set -euo pipefail
NODEGROUP_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":1,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODEGROUP_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
Poll `describe-update` for that ID until `Successful`, handling `Failed`/`Cancelled` explicitly. The original eksctl `update nodegroup --max-unavailable` command is not a supported replacement. Check the real PDB `disruptionsAllowed`, readiness, application health and volume relocation; a three-replica layout is an example, not a universal minimum.

</details>

10. Which controller recommends or changes Pod CPU and memory requests?
   * A) Cluster Autoscaler
   * B) Karpenter
   * C) Horizontal Pod Autoscaler
   * D) Vertical Pod Autoscaler

<details>
<summary>Show Answer</summary>

**Answer: D) Vertical Pod Autoscaler**

VPA recommends or updates Pod resource requests. HPA changes replica counts. **Both** can indirectly change node demand; neither manages a managed node group's ASG directly.

| Component | Controlled object |
| --- | --- |
| Cluster Autoscaler | Desired capacity of discovered existing node groups/ASGs, based on schedulability and safe removal |
| Karpenter | Its own NodeClaims/EC2 capacity selected through NodePools and EC2NodeClasses; not managed-node-group ASGs |
| HPA / KEDA | Workload replicas from resource/custom/external metrics or events |
| VPA | Pod resource recommendations/requests according to update mode |

**Cluster Autoscaler:** use the same Kubernetes minor as the cluster. For the EKS 1.36 example, chart 9.59.0 must explicitly use image `v1.36.1` (its default image is 1.35.0). First configure a dedicated `cluster-autoscaler` ServiceAccount with the reviewed, tag-scoped IAM permissions and ASG discovery tags. Render and inspect RBAC, image and arguments before installation:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
Do not disable local-storage safeguards casually or let ASG target-tracking/predictive policies compete with Cluster Autoscaler over the same desired capacity.

**Karpenter alternative:** install and authorize a compatible controller separately. Replace the AMI ID, node role and discovery tag values with reviewed resources for this cluster; the AMI must match AL2023, Kubernetes version and architecture. Pin an AMI ID or a tested versioned alias instead of silently selecting `al2023@latest`. Limits and consolidation timing below are examples, not measured sizing or provisioning-speed guarantees.

```yaml
# Karpenter NodePool (karpenter.sh/v1)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
# Karpenter EC2NodeClass (karpenter.k8s.aws/v1)
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_VERIFIED_AL2023_AMI
  role: KarpenterNodeRole-my-cluster
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
**HPA:** this example requires an existing `my-app` Deployment in `autoscaling-lab`, Metrics Server and CPU requests:

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```
**VPA:** install the VPA CRD/controllers first. Start in recommendation-only mode and inspect recommendations before choosing an explicit supported update mode:

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
  namespace: autoscaling-lab
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
      controlledResources: ["cpu", "memory"]
```
`Off` changes no Pod resources. Applying recommendations may require recreation or supported in-place resizing, depending on VPA/Kubernetes versions and configuration; do not promise a restart in every mode. Updating CPU requests while a CPU-utilization HPA controls the same workload creates feedback through the utilization denominator. The recommendation-only example avoids that conflict until a coordinated design is reviewed.

</details>

## Hands-on Exercises

### Exercise 1: Implementing Network Policies in an EKS Cluster

**Scenario:** allow frontend → backend and backend → database while denying frontend → database. Keep the original Calico learning goal using AWS VPC CNI for IP allocation.

**Scope:** an existing disposable Linux IPv4 EKS cluster, no conflicting global/tier policy, standard CoreDNS, and an administrator-reviewed Calico installation. This is a connectivity exercise, not a production microservice/database recipe. Cloud installation and traffic tests were not executed in this audit.


<details>
<summary>Show Solution</summary>

**1. Prepare the policy engine.** Follow the official Calico EKS **Amazon VPC networking** path. Disable native AWS VPC CNI NetworkPolicy through its configuration owner; it conflicts with Calico enforcement. Preserve `aws-node` networking. Enable its `ANNOTATE_POD_IP=true` setting and grant its ServiceAccount Pod patch permission. This dedicated RBAC example adds that permission without appending malformed YAML to the add-on's ClusterRole:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-cni-pod-annotation
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-cni-pod-annotation
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-cni-pod-annotation
subjects:
- kind: ServiceAccount
  name: aws-node
  namespace: kube-system
```
Save and review the RBAC, then apply it only to the intended `aws-node` ServiceAccount; configure the environment variable through the managed add-on or self-managed manifest owner. Do not proceed until its rollout and annotation behavior are healthy. If Calico is already installed, review and reuse it instead of running the new-installation commands below.

```bash
# Download pinned manifests for inspection; do not overwrite an existing installation.
curl --fail --location --output calico-crds.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
curl --fail --location --output tigera-operator.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
# After review, on the intended new lab installation:
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" create -f calico-crds.yaml
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create -f tigera-operator.yaml
```
After the operator CRDs are established, create the following reviewed `Installation` and `APIServer` resources. Operator installation alone does not configure AWS VPC networking. The API server is required for the `projectcalico.org/v3` policy examples:

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
```

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get tigerastatus
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get apiservice v3.projectcalico.org
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n calico-system get pods
```
Require the Calico components and aggregated API to be available, then verify actual enforcement below. Node `Ready` alone is insufficient. The optional Goldmane/Whisker UI is not needed for this exercise.

**2. Create an owned namespace and temporary database credential.** Use one Bash session for the remaining snippets. The namespace name and UID are recorded so cleanup cannot intentionally target another namespace:

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed lab cluster kubeconfig}"
NETWORK_LAB_DIR=$(mktemp -d /tmp/eks-calico-lab.XXXXXX)
NETWORK_NAMESPACE="calico-quiz-$(date +%s)-$$"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$NETWORK_NAMESPACE"
NETWORK_NAMESPACE_UID=$(kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
  get namespace "$NETWORK_NAMESPACE" -o jsonpath='{.metadata.uid}')
: "${NETWORK_NAMESPACE_UID:?}"
jq -n --arg name "$NETWORK_NAMESPACE" --arg uid "$NETWORK_NAMESPACE_UID" \
  '{namespace:$name,namespaceUID:$uid}' > "$NETWORK_LAB_DIR/ownership.json"
openssl rand -hex 32 > "$NETWORK_LAB_DIR/db-password"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
  create secret generic database-auth \
  --from-file=password="$NETWORK_LAB_DIR/db-password"
```
**3. Deploy the three tiers.** Python HTTP servers stand in for frontend/backend so the diagnostic TCP client is available in both containers. The PostgreSQL 17 image uses `POSTGRES_PASSWORD_FILE` and a namespace-local Secret; it performs no external database operation. The DB's `emptyDir` is **lost on Pod replacement**. Do not put valuable data here. The DB image's initialization behavior is retained; this is not a Restricted-profile production database manifest. Major-version image tags are mutable: record resolved digests for a reproducible run.

```bash
# The HTTP layers are diagnostic stand-ins, not business applications.
for tier in frontend backend; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $tier
spec:
  replicas: 1
  selector:
    matchLabels: {app: $tier}
  template:
    metadata:
      labels: {app: $tier}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: diagnostic
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: $tier
spec:
  selector: {app: $tier}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
done

kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
spec:
  replicas: 1
  selector:
    matchLabels: {app: database}
  template:
    metadata:
      labels: {app: database}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      containers:
      - name: database
        image: postgres:17-alpine
        env:
        - name: POSTGRES_PASSWORD_FILE
          value: /run/secrets/postgres/password
        ports:
        - containerPort: 5432
        readinessProbe:
          exec:
            command: [pg_isready, -U, postgres]
          initialDelaySeconds: 5
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
        volumeMounts:
        - {name: data, mountPath: /var/lib/postgresql/data}
        - {name: auth, mountPath: /run/secrets/postgres, readOnly: true}
      volumes:
      - name: data
        emptyDir: {}
      - name: auth
        secret: {secretName: database-auth}
---
apiVersion: v1
kind: Service
metadata:
  name: database
spec:
  selector: {app: database}
  ports:
  - {port: 5432, targetPort: 5432, protocol: TCP}
EOF

for tier in frontend backend database; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    rollout status "deployment/$tier" --timeout=180s
done
```
**4. Establish the baseline.** All three TCP paths and DNS must work before applying policy. Port 5432 success only proves a TCP connection, not SQL authentication or application correctness.

```bash
# Distinguish DNS failure from TCP denial. Status 42 means a TCP failure.
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    exec "deployment/$1" -c diagnostic -- python -c '
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
try:
    address = socket.gethostbyname(host)
except OSError as error:
    print("DNS failure:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, port), timeout=3)
    connection.close()
except OSError as error:
    print("TCP connection failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP connection succeeded")
' "$2" "$3"
}

# Baseline: all three must succeed BEFORE the policy is applied.
check_tcp frontend backend 8080
check_tcp backend database 5432
check_tcp frontend database 5432
```
**5. Apply and test the policy.** The selected Pods are isolated in both directions; unmatched traffic is denied. Explicit rules allow the two application paths and UDP/TCP DNS. Namespace selectors are required to reach CoreDNS outside the lab namespace. Adapt the DNS rule for NodeLocal DNSCache or different labels before testing.

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: tier-boundaries
spec:
  selector: all()
  types: [Ingress, Egress]
  ingress:
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
  egress:
  - action: Allow
    protocol: UDP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
EOF

# Allow policy propagation, then verify positive controls and the denied path.
POLICY_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp frontend backend 8080
  check_tcp backend database 5432
  if check_tcp frontend database 5432; then
    sleep 2
  else
    result=$?
    if [ "$result" -ne 42 ]; then
      printf '%s\n' 'DNS/exec failure is not proof of policy denial.' >&2
      exit 1
    fi
    # Database availability must still hold after the negative observation.
    check_tcp backend database 5432
    POLICY_VERIFIED=true
    break
  fi
done
[ "$POLICY_VERIFIED" = true ] || {
  printf '%s\n' 'Expected denial was not observed; inspect policy enforcement.' >&2
  exit 1
}
```
Policy propagation is asynchronous. A timeout, DNS failure, absent diagnostic binary, or an unavailable database by itself is not evidence of successful isolation. The procedure uses a working baseline and positive controls; investigate other policies/routes if observations differ.

**6. Cleanup.** Delete only the owned namespace after confirming its UID. This removes the test workloads, policy, Secret and ephemeral data, not the cluster-wide Calico installation. Remove the local password file after the exercise. Leave shared CNI/RBAC configuration in place unless a separate administrator-reviewed rollback owns it.

```bash
CURRENT_NETWORK_UID=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get namespace "${NETWORK_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_NETWORK_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_NETWORK_UID" = "${NETWORK_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
    delete namespace "$NETWORK_NAMESPACE" --wait=true || exit 1
else
  printf '%s\n' 'Namespace UID changed; no deletion attempted.' >&2
  exit 1
fi
```

</details>

### Exercise 2: Configuring IRSA and S3 Access in an EKS Cluster

**Scenario:** give one workload read-only access to an approved `training/` prefix in an existing S3 bucket, using IRSA instead of the node role. Verify the actual assumed-role identity and compare against a deliberately credential-free Pod.

**Prerequisites:** Bash, jq, AWS CLI, eksctl and kubectl; an existing authorized EKS cluster; admin access to a new namespace and IAM role; an approved non-sensitive existing S3 object. This commercial-partition example assumes an object without additional customer-KMS requirements. Bucket/KMS policies, SCPs, DNS, STS and S3 network paths may impose further requirements. No S3 object is created, changed or deleted.


<details>
<summary>Show Solution</summary>

**1. Scope the lab and verify OIDC.** Set `EXAMPLE_CLUSTER`, `EXAMPLE_REGION`, `S3_BUCKET`, and `S3_TEST_KEY` (under `training/`). The OIDC provider is shared cluster infrastructure; do not delete it during cleanup. Stop if namespace creation or provider verification fails.

```bash
set -euo pipefail
umask 077
# Commercial AWS partition example; use an existing approved S3 training prefix.
: "${EXAMPLE_CLUSTER:?}"
: "${EXAMPLE_REGION:?}"
: "${S3_BUCKET:?Existing bucket containing the approved training object}"
: "${S3_TEST_KEY:?Existing non-sensitive object key under training/}"
case "$S3_TEST_KEY" in training/*) ;; *) printf '%s\n' 'Use a training/ key.' >&2; exit 1 ;; esac
IRSA_LAB_DIR=$(mktemp -d /tmp/eks-irsa-lab.XXXXXX)
: "${IRSA_LAB_DIR:?}"
IRSA_LAB_ID="irsa-quiz-$(date +%s)-$$"
IRSA_NAMESPACE="$IRSA_LAB_ID"
IRSA_ROLE_NAME="$IRSA_LAB_ID"
IRSA_SERVICE_ACCOUNT=s3-reader
IRSA_KUBECONFIG="$IRSA_LAB_DIR/kubeconfig"

aws sts get-caller-identity --output json > "$IRSA_LAB_DIR/caller.json" || exit 1
IRSA_ACCOUNT_ID=$(jq -er '.Account' "$IRSA_LAB_DIR/caller.json") || exit 1
jq -e '.Arn | startswith("arn:aws:")' "$IRSA_LAB_DIR/caller.json" >/dev/null || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$IRSA_LAB_DIR/cluster.json" || exit 1
IRSA_ISSUER=$(jq -er '.identity.oidc.issuer' "$IRSA_LAB_DIR/cluster.json") || exit 1
case "$IRSA_ISSUER" in https://*) ;; *) printf '%s\n' 'Invalid OIDC issuer.' >&2; exit 1 ;; esac
IRSA_ISSUER_HOST="${IRSA_ISSUER#https://}"
IRSA_PROVIDER_ARN="arn:aws:iam::$IRSA_ACCOUNT_ID:oidc-provider/$IRSA_ISSUER_HOST"

aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$IRSA_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create namespace "$IRSA_NAMESPACE" || exit 1
IRSA_NAMESPACE_UID=$(kubectl --kubeconfig "$IRSA_KUBECONFIG" \
  get namespace "$IRSA_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${IRSA_NAMESPACE_UID:?}"
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "$IRSA_NAMESPACE_UID" \
  '{namespace:$namespace,namespaceUID:$uid}' > "$IRSA_LAB_DIR/ownership.json" || exit 1

# The cluster's provider is shared infrastructure; eksctl checks/associates it.
eksctl utils associate-iam-oidc-provider --cluster "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --approve || exit 1
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$IRSA_PROVIDER_ARN" \
  --output json > "$IRSA_LAB_DIR/provider.json" || exit 1
jq -e '.ClientIDList | index("sts.amazonaws.com") != null' \
  "$IRSA_LAB_DIR/provider.json" >/dev/null || exit 1
```
**2. Create a unique, scoped role.** Trust requires both `aud=sts.amazonaws.com` and the exact namespace/ServiceAccount `sub`. Role creation failure stops policy attachment; record the immutable RoleId for cleanup.

```bash
jq -n --arg provider "${IRSA_PROVIDER_ARN:?}" --arg issuer "${IRSA_ISSUER_HOST:?}" \
  --arg subject "system:serviceaccount:${IRSA_NAMESPACE:?}:${IRSA_SERVICE_ACCOUNT:?}" \
  '{
    Version:"2012-10-17",
    Statement:[{
      Effect:"Allow",
      Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",
      Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",
        ($issuer+":sub"):$subject
      }}
    }]
  }' > "${IRSA_LAB_DIR:?}/trust.json" || exit 1

jq -n --arg bucket "${S3_BUCKET:?}" \
  '{
    Version:"2012-10-17",
    Statement:[
      {
        Effect:"Allow",Action:"s3:ListBucket",Resource:("arn:aws:s3:::"+$bucket),
        Condition:{StringLike:{"s3:prefix":["training/","training/*"]}}
      },
      {
        Effect:"Allow",Action:"s3:GetObject",
        Resource:("arn:aws:s3:::"+$bucket+"/training/*")
      }
    ]
  }' > "$IRSA_LAB_DIR/s3-policy.json" || exit 1

# Stop on creation failure; never attach this policy to a pre-existing role.
aws iam create-role --role-name "${IRSA_ROLE_NAME:?}" \
  --assume-role-policy-document "file://$IRSA_LAB_DIR/trust.json" \
  --tags "Key=TrainingLab,Value=${IRSA_LAB_ID:?}" \
  --query Role --output json > "$IRSA_LAB_DIR/created-role.json" || exit 1
IRSA_ROLE_ARN=$(jq -er '.Arn' "$IRSA_LAB_DIR/created-role.json") || exit 1
IRSA_ROLE_ID=$(jq -er '.RoleId' "$IRSA_LAB_DIR/created-role.json") || exit 1
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "${IRSA_NAMESPACE_UID:?}" \
  --arg roleName "$IRSA_ROLE_NAME" --arg roleArn "$IRSA_ROLE_ARN" --arg roleId "$IRSA_ROLE_ID" \
  '{namespace:$namespace,namespaceUID:$uid,roleName:$roleName,roleARN:$roleArn,roleID:$roleId}' \
  > "$IRSA_LAB_DIR/ownership.json" || exit 1
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" \
  --policy-name ScopedTrainingS3Read \
  --policy-document "file://$IRSA_LAB_DIR/s3-policy.json" || exit 1
```
**3. Deploy and verify.** Allow for IAM propagation before retrying a failed test. The three containers check identity, prefix listing count, and object length without logging object contents or credentials. The identity must match the newly created role; S3 success alone could otherwise come from a broader node role.

```bash
# JSON construction preserves literal object keys and prevents YAML interpolation errors.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg sa "${IRSA_SERVICE_ACCOUNT:?}" \
  --arg role "${IRSA_ROLE_ARN:?}" --arg region "${EXAMPLE_REGION:?}" \
  --arg bucket "${S3_BUCKET:?}" --arg key "${S3_TEST_KEY:?}" '
  {
    apiVersion:"v1",kind:"List",items:[
      {
        apiVersion:"v1",kind:"ServiceAccount",
        metadata:{name:$sa,namespace:$ns,annotations:{
          "eks.amazonaws.com/role-arn":$role,
          "eks.amazonaws.com/sts-regional-endpoints":"true"
        }}
      },
      {
        apiVersion:"v1",kind:"Pod",metadata:{name:"irsa-check",namespace:$ns},
        spec:{
          serviceAccountName:$sa,nodeSelector:{"kubernetes.io/os":"linux"},restartPolicy:"Never",
          containers:[
            {name:"identity",args:["--region",$region,"sts","get-caller-identity"]},
            {name:"list-prefix",args:["--region",$region,"s3api","list-objects-v2","--bucket",$bucket,
              "--prefix","training/","--max-keys","1","--query","KeyCount","--output","json"]},
            {name:"object-metadata",args:["--region",$region,"s3api","head-object","--bucket",$bucket,
              "--key",$key,"--query","ContentLength","--output","json"]}
          ] | map(.+{
            image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",command:["aws"],
            resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
          })
        }
      }
    ]
  }' > "${IRSA_LAB_DIR:?}/workload.json" || exit 1
kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" create -f "$IRSA_LAB_DIR/workload.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Succeeded pod/irsa-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs irsa-check -c identity > "$IRSA_LAB_DIR/pod-identity.json" || exit 1
jq -e --arg account "${IRSA_ACCOUNT_ID:?}" --arg role "${IRSA_ROLE_NAME:?}" \
  '.Account == $account and (.Arn | startswith("arn:aws:sts::"+$account+":assumed-role/"+$role+"/"))' \
  "$IRSA_LAB_DIR/pod-identity.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c list-prefix
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c object-metadata
```
**4. Controlled negative comparison.** The new namespace's default ServiceAccount must have no IRSA annotation or EKS Pod Identity association, and no other credentials may be injected. Disable IMDS fallback in this test client and require the specific missing-credentials failure. A random network or authorization error is not a valid negative result.

```bash
# Controlled comparison: no IRSA, no Pod Identity association, no IMDS fallback.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg region "${EXAMPLE_REGION:?}" '
{
  apiVersion:"v1",kind:"Pod",
  metadata:{name:"no-role-check",namespace:$ns},
  spec:{
    automountServiceAccountToken:false,
    serviceAccountName:"default",
    nodeSelector:{"kubernetes.io/os":"linux"},
    restartPolicy:"Never",
    containers:[{
      name:"identity",image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",
      command:["aws"],args:["--region",$region,"sts","get-caller-identity"],
      env:[{name:"AWS_EC2_METADATA_DISABLED",value:"true"}],
      resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
    }]
  }
}' > "${IRSA_LAB_DIR:?}/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create -f "$IRSA_LAB_DIR/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Failed pod/no-role-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get pod no-role-check -o json > "$IRSA_LAB_DIR/negative-status.json" || exit 1
jq -e '.status.containerStatuses[] | select(.name=="identity") |
  .state.terminated.exitCode == 255' "$IRSA_LAB_DIR/negative-status.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs no-role-check -c identity > "$IRSA_LAB_DIR/negative-log.txt" || exit 1
grep -F 'Unable to locate credentials' "$IRSA_LAB_DIR/negative-log.txt" >/dev/null || {
  printf '%s\n' 'Unexpected failure: inspect the saved log; do not claim isolation.' >&2
  exit 1
}
```
This is a credential-provider comparison, not proof that arbitrary Pods cannot access IMDS or that containers are security boundaries. Restrict node credentials separately. IRSA uses a projected web-identity token and STS temporary credentials; compatible SDKs refresh them. Do not dump all `AWS_*` environment variables or token files.

**5. Cleanup only owned resources.** Keep the recorded namespace UID and IAM RoleId. The guarded cleanup removes the lab namespace, its inline policy and its unique role; it retains the S3 bucket/object, shared OIDC provider and cluster. If setup only partly succeeded, inspect `ownership.json` and clean up just the resources actually recorded.

```bash
# Recover the recorded values from ownership.json if this is a later shell.
IRSA_CLEANUP_NAMESPACE_OK=false
if CURRENT_IRSA_UID=$(kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" \
  get namespace "${IRSA_NAMESPACE:?}" --ignore-not-found -o jsonpath='{.metadata.uid}'); then
  if [ -z "$CURRENT_IRSA_UID" ]; then
    IRSA_CLEANUP_NAMESPACE_OK=true
  elif [ "$CURRENT_IRSA_UID" = "${IRSA_NAMESPACE_UID:?Recorded UID required}" ]; then
    if kubectl --kubeconfig "$IRSA_KUBECONFIG" delete namespace "$IRSA_NAMESPACE" --wait=true; then
      IRSA_CLEANUP_NAMESPACE_OK=true
    else
      exit 1
    fi
  else
    printf '%s\n' 'Namespace UID mismatch; stop and inspect.' >&2
    exit 1
  fi
else
  printf '%s\n' 'Namespace lookup failed; stop and inspect.' >&2
  exit 1
fi

if [ "$IRSA_CLEANUP_NAMESPACE_OK" = true ]; then
  CURRENT_IRSA_ROLE_JSON=$(aws iam get-role --role-name "${IRSA_ROLE_NAME:?}" \
    --query Role --output json) || exit 1
  CURRENT_IRSA_ROLE_ID=$(printf '%s' "$CURRENT_IRSA_ROLE_JSON" | jq -er '.RoleId') || exit 1
  if [ "$CURRENT_IRSA_ROLE_ID" = "${IRSA_ROLE_ID:?Recorded IAM RoleId required}" ]; then
    IRSA_INLINE_POLICIES=$(aws iam list-role-policies --role-name "$IRSA_ROLE_NAME" \
      --query PolicyNames --output json) || exit 1
    printf '%s' "$IRSA_INLINE_POLICIES" |
      jq -e 'all(.[]; . == "ScopedTrainingS3Read")' >/dev/null || exit 1
    if printf '%s' "$IRSA_INLINE_POLICIES" | jq -e 'index("ScopedTrainingS3Read") != null' >/dev/null; then
      aws iam delete-role-policy --role-name "$IRSA_ROLE_NAME" \
        --policy-name ScopedTrainingS3Read || exit 1
    fi
    aws iam delete-role --role-name "$IRSA_ROLE_NAME"
  else
    printf '%s\n' 'IAM RoleId mismatch; no IAM deletion attempted.' >&2
    exit 1
  fi
fi
```

</details>

## Advanced Topics

The following questions are about advanced topics related to Amazon EKS cluster creation. This section tests your understanding of advanced concepts and best practices for EKS cluster creation.

1. Which claim is NOT guaranteed by IPv4 prefix delegation?
   * A) A prefix uses an ENI address slot
   * B) More IP capacity can fit on one node
   * C) Every application becomes ready faster
   * D) Contiguous subnet blocks are required

<details>
<summary>Show Answer</summary>

**Answer: C) Every application becomes ready faster**

Prefix delegation can reduce address-allocation latency: attaching another prefix to an existing ENI avoids some ENI creation/attachment work. AWS documents this benefit, so the original explanation that prefix delegation cannot reduce startup time and must add routing overhead was incorrect.

End-to-end Pod readiness still depends on scheduling, node launch, image pull, volume attachment, initialization, probes and application startup. No before/after benchmark was supplied here, and this audit did not execute one. Do not infer a fixed latency improvement or invent a cause for a slowdown.

Each IPv4 `/28` consumes one secondary-address slot and 16 addresses from a contiguous subnet block. It raises IP capacity per node, subject to `maxPods`, compute resources and subnet space. It does not expand the CIDR or guarantee fewer allocated addresses. Warm-pool settings trade spare-address consumption for allocation readiness.

Use the prerequisites and new-node-group migration in basic question 5: inspect fragmentation, configure a compatible CNI, validate calculated node capacity and migrate with spare capacity and PDB-aware draining. A blanket restart of existing Pods is not a complete transition plan.

</details>

2. Which practice is incorrect for mixed-instance managed node groups using Cluster Autoscaler?
   * A) Use comparable CPU/memory/GPU shapes
   * B) Verify image and AZ compatibility
   * C) Separate Spot and On-Demand groups
   * D) Mix arbitrary shapes because the autoscaler simulates every type

<details>
<summary>Show Answer</summary>

**Answer: D) Mix arbitrary shapes because the autoscaler simulates every type**

Diversity can improve capacity options, especially for Spot, but must respect the autoscaler's scheduling model. Cluster Autoscaler simulates a mixed group using its first instance type; candidates should have the same CPU, memory and GPU shape. Smaller alternatives can leave Pods pending, while larger ones can waste capacity. Similar names do not guarantee a matching shape: for example, `c5n.large` has different memory from `c5.large`.

A managed node group has one capacity type. Use **separate groups** for On-Demand baseline and Spot expansion; listing multiple `instanceTypes` does not mix purchase options in one managed group. EKS chooses the managed Spot allocation strategy; `spotAllocationStrategy` is not a supported eksctl `managedNodeGroups` field.

This example retains comparable `m5`-family shapes. It is a node-group configuration for a reviewed existing cluster with unused group names, not evidence of price/performance or guaranteed capacity. Verify per-AZ offerings and image/driver/storage compatibility:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: on-demand-base
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  spot: false
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
- name: spot-scaling
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large, m5n.large]
  privateNetworking: true
  spot: true
  desiredCapacity: 0
  minSize: 0
  maxSize: 20
```
Separate different workload shapes instead of combining memory, compute and general-purpose instances into one autoscaled group:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: compute-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [c5.2xlarge, c5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: compute}
  taints:
  - {key: workload-type, value: compute, effect: NoSchedule}
- name: memory-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [r5.2xlarge, r5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: memory}
  taints:
  - {key: workload-type, value: memory, effect: NoSchedule}
```
The workload must have a matching toleration **and** a selector/affinity if it must use a dedicated pool. Labels alone do not schedule it, and taints are not a tenant security boundary. Account for scale-from-zero discovery, daemon overhead, interruption handling, storage persistence and testing across all candidate types. Diversity may add monitoring and troubleshooting work; neither simpler management nor lower cost is automatic.

</details>

3. Which strategy creates a separate replacement node group before retiring the old one?
   * A) Untracked host package updates
   * B) Blue/green migration
   * C) Deleting every node at once
   * D) Changing only the cluster display name

<details>
<summary>Show Answer</summary>

**Answer: B) Blue/green migration**

Blue/green creates a separate replacement node group and migrates workloads after validation. It can preserve a rollback option while the old group and compatible application/data state remain. Two groups in one cluster still share the control plane and other dependencies; this is not complete isolation or a zero-downtime guarantee.

| Strategy | Benefit | Important limit |
| --- | --- | --- |
| Blue/green | Validate replacement capacity before final retirement | Extra cost/capacity; rollback depends on retained nodes and compatible state |
| Managed rolling update | EKS coordinates gradual node replacement | `DEFAULT` uses temporary extra nodes; PDB/capacity failures can block progress |
| Canary | Try a separate small workload/group first | Must actually limit workload/traffic scope; it adds validation and routing work |
| Manual host package mutation | Changes an individual host | Creates drift from the AMI; use a reviewed replacement-image lifecycle instead of an unqualified SSH/yum recipe |

**Replacement group example:** for an existing cluster and unused group name, review this file and use `eksctl create nodegroup -f green-nodegroup.yaml`. Confirm AL2023/architecture compatibility, add-ons, egress, IP space, quotas and storage topology first.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: green-nodegroup
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 3
  maxSize: 5
  labels:
    audit.example.com/pool: green
```
**A real canary uses a separate Deployment:** the following is a minimal HTTP probe workload in a dedicated `update-lab` namespace, with unique labels so it does not accidentally join the existing Service. Replace it with a reviewed canary of your actual application before claiming application compatibility. Patching the node selector of the main Deployment rolls **all** of its replicas and is not a limited canary.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-canary
  namespace: update-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: my-app-canary}
  template:
    metadata:
      labels: {app: my-app-canary}
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        audit.example.com/pool: green
      containers:
      - name: web
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet: {path: /, port: 80}
        resources:
          requests: {cpu: 100m, memory: 64Mi}
          limits: {cpu: 500m, memory: 128Mi}
```
Validate readiness, API/CNI/DNS, application errors, resource pressure, persistent volumes and representative traffic over a reviewed observation window. Keep traffic routing explicit; a node label does not switch traffic. Once replacement capacity and workload/data behavior are verified, drain one confirmed old node at a time:

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
A blocked drain requires diagnosis, not `--force` or automatic emptyDir deletion. Confirm all migrated workloads and state before this separate final deletion:

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```
For a managed rolling alternative, complete the `update-nodegroup-config` operation in basic question 9 before submitting `update-nodegroup-version`, then track that returned update ID. A managed group can retain its resource identity while its EC2 nodes are replaced. Once old capacity is deleted or data changed incompatibly, “instant rollback” is no longer available.

</details>

4. Which action can conflict with Cluster Autoscaler ownership of a managed ASG?
   * A) Review discovery tags
   * B) Tune scan frequency using observations
   * C) Use accurate Pod resource requests
   * D) Add another policy that independently changes the same desired capacity

<details>
<summary>Show Answer</summary>

**Answer: D) Add another policy that independently changes the same desired capacity**

Cluster Autoscaler controls node-group capacity based on scheduling requests, not just average EC2 CPU. A target-tracking or predictive ASG policy changing the same desired capacity can fight that control loop and bypass the expected Kubernetes drain process. Do not directly reset desired capacity to two as an “optimization.”

**Useful controls:**

* Tune scan frequency against reaction time and API load. The documented default is 10 seconds; 30 seconds is an example to test, not a measured optimum. Likewise, provisioning timeouts must match your actual node startup behavior.
* Use reviewed ASG discovery tags and tag-scoped IAM. Tags identify eligible groups; they do not grant permissions or define a scaling algorithm.
* Match requests, labels and taints to real capacity. One instance type can be appropriate; comparable-shape diversity is useful when availability/Spot needs justify it (advanced question 2).
* Use priorities deliberately. Preemption is not an availability guarantee and can disrupt lower-priority workloads. Bind the following class through `priorityClassName` only after evaluating admission and workload policy:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-high-priority
value: 1000000
globalDefault: false
description: Reviewed priority for critical application Pods
```
**Overprovisioning:** reserve requests with preemptible low-priority Pods. For this example, Cluster Autoscaler's configured expendable-Pod cutoff must be below `-5` (for example `-10`), while application Pods must have higher priority. Otherwise the reserve Pods may not trigger replenishment as intended. Use a dedicated namespace and unused PriorityClass name:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-overprovisioning
value: -5
globalDefault: false
description: Temporary spare capacity for an autoscaling lab
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: overprovisioning
  namespace: autoscaling-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: overprovisioning}
  template:
    metadata:
      labels: {app: overprovisioning}
    spec:
      priorityClassName: audit-overprovisioning
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: reserve
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command: [sleep, '86400']
        resources:
          requests: {cpu: 1000m, memory: 1000Mi}
          limits: {cpu: 1000m, memory: 1000Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
This holds 1 CPU and 1000Mi of requested capacity, not pre-warmed application state, and incurs node cost. It does not avoid image pulls, volume attachment or application initialization. Size against observed demand and remove the owned reservation Deployment and PriorityClass after the test.

Use the complete rendered Cluster Autoscaler setup in basic question 10 rather than the old incomplete v1.23 Deployment. Karpenter is an alternative for separately managed capacity; its NodePool must reference a valid, authorized EC2NodeClass. KEDA/HPA scale workload replicas, which can create demand for either node autoscaler. Validate these interacting loops rather than enabling every scaling mechanism on the same resources.

</details>

5. Which is NOT a general security best practice for an EKS node group?
   * A) Require IMDSv2 and review metadata access
   * B) Use least-privilege IAM
   * C) Give every node a public IP
   * D) Review security-group rules

<details>
<summary>Show Answer</summary>

**Answer: C) Give every node a public IP**

Giving every node a public IP is not a general security best practice. Private subnets reduce direct internet exposure, but routes, security groups, IAM, software maintenance and workload controls still matter.

**Node identity and metadata:** require IMDSv2 with eksctl's supported `disableIMDSv1` field. A nested `metadataOptions` object is not an eksctl managed-node-group field; custom EC2 MetadataOptions belong in a reviewed launch template. IMDSv2 mitigates some SSRF paths but does not stop every Pod from reaching node credentials, especially host-network Pods. Review metadata access separately from workload identity and host dependencies.

**Least privilege and encrypted root volume:** this existing-cluster node-group example assumes the CNI already has its own IRSA/Pod Identity permissions. EBS CSI, log collectors and applications also need their own reviewed roles; attaching their broad permissions to every node contradicts least privilege.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: secure-nodes
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  disableIMDSv1: true
  volumeEncrypted: true
  iam:
    attachPolicyARNs:
    - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
    - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
```
EBS encryption protects a different layer from Kubernetes API data. EKS 1.28 and later encrypt all Kubernetes API data at rest with default envelope encryption; a customer-managed KMS key is optional, with additional grants/permissions and key lifecycle obligations. Do not disable or delete a cluster's key as routine cleanup.

**Network design:** a private API endpoint requires a routed administrator/node access path. Public API restrictions use `publicAccessCidrs`, not an inbound rule on the cluster SG. Review AWS's complete cluster/node SG requirements: TCP 443, TCP 10250, TCP/UDP 53 and workload-specific paths, with correct directions and peer groups. Two inbound port rules alone are not a complete node networking design.

Private IPv4 internet egress may use NAT; VPC endpoints and native IPv6 have different paths. Inbound traffic may arrive from load balancers or authorized connected networks. A private subnet alone proves neither complete isolation nor regulatory compliance.

**Container controls:** use a workload compatible with non-root and read-only execution. This controller-managed diagnostic Pod runs in a **new dedicated** `security-lab` namespace and needs no network or writable root:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-pod
  namespace: security-lab
spec:
  replicas: 1
  selector:
    matchLabels: &id001
      app: secure-pod
  template:
    metadata:
      labels: *id001
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: secure-container
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command:
        - sh
        - -c
        - echo read-only-lab; sleep 3600
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 32Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
```
An enforced deny policy can be demonstrated in that dedicated namespace; add explicit DNS/application allowances before using it for a real workload:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: security-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```
**Logging and detection:** control-plane CloudWatch logs have five configurable types:

```bash
# Enable the reviewed set of log types; this example enables all five.
if LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```
Wait for the returned update to succeed and verify actual log delivery and retention. This does not collect every container's application logs. GuardDuty EKS audit-log protection and Runtime Monitoring are distinct capabilities with separate configuration/coverage; enabling control-plane logs alone is not runtime threat detection.

</details>


## References

* [EKS prefix mode](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html)
* [EKS maxPods and prefix procedure](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
* [EKS network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
* [NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
* [Subnet route table association](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-subnetroutetableassociation.html)
* [Security groups for Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
* [CoreDNS managed add-on](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html)
* [CoreDNS cache](https://coredns.io/plugins/cache/)
* [CoreDNS reload](https://coredns.io/plugins/reload/)
* [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
* [Kubernetes PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
* [EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
* [EKS managed node updates](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)
* [Calico on EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
* [Calico NetworkPolicy](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
* [EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
