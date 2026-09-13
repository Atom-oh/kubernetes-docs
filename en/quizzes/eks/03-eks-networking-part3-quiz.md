# EKS Networking Quiz - Part 3

> **Last Updated**: September 11, 2026

This quiz covers the [Part 3 troubleshooting concepts](../../eks/03-eks-networking-part3.md), private connectivity, multi-cluster design and mesh operations. Current examples use EKS Kubernetes 1.36 and VPC CNI 1.23.0; historical App Mesh configuration is explicitly identified. Resource-creation examples require reviewed IAM, network and ownership prerequisites. This audit performs local checks, not an EKS deployment.

### 1. What changes when an application is enrolled in a sidecar-based service mesh?

- A. All Pod traffic leaves the VPC
- B. A proxy handles enrolled service traffic
- C. Service discovery is removed
- D. All traffic requires Transit Gateway

<details>
<summary>Show Answer</summary>

**Answer: B. An injected proxy processes enrolled service traffic.**

In sidecar mode, the application and proxy share one Pod network namespace and IP. The proxy is part of the data plane; the control plane distributes routing, security and identity configuration. NetworkPolicy, VPC routing and Service discovery still matter. The logical path is:
```text
Application → client proxy → Pod network → destination proxy → application
```
Interception depends on enrollment, excluded ports, protocol and mode; not every packet must traverse a Service VIP. Ambient meshes use a different node-proxy/waypoint design, so the question is explicitly about sidecar mode. Meshes can provide retries, routing, mTLS and telemetry without rewriting the main service implementation, but applications may still need trace-context propagation, compatible protocols and timeout handling.

Use the selected mesh’s supported injector/revision, not a hand-added old Envoy image or simultaneous injectors. AWS App Mesh is a historical example: support and access end September 30, 2026. Existing deployments need migration planning; it is not the default new-installation example. See [Istio installation](../../service-mesh/istio/01-installation.md) for the maintained implementation path.

</details>

### 2. What do VPC endpoints provide for private EKS workloads?

- A. Unlimited bandwidth
- B. Private connectivity to supported services
- C. An automatic 50% discount
- D. Automatic AWS authentication

<details>
<summary>Show Answer</summary>

**Answer: B. Private paths to supported AWS service endpoints without internet/NAT for those requests.**

Interface endpoints create ENIs in selected subnets/AZs and normally incur hourly/data-processing charges. Gateway endpoints for S3/DynamoDB add route-table entries and have no endpoint charge; service/storage/request charges still apply. Endpoints do not grant IAM permissions, guarantee lower cost/latency, or automatically satisfy compliance.

For private ECR image pulls, plan `ecr.api`, `ecr.dkr` and the S3 layer-download path, endpoint SG HTTPS rules, DNS support/private DNS, route tables and endpoint/IAM policies. Other required services depend on the workloads: regional STS for IRSA, `eks-auth` for Pod Identity, EC2 APIs for CNI, Logs/monitoring and others as used. The EKS service endpoint does not replace the private Kubernetes API endpoint. ECR Public and first pull-through-cache requests/Windows foreign layers can need additional external connectivity or a prepared image mirror.

This parameterized CloudFormation example adds only three endpoints to an **existing** VPC. Review existing endpoints/private-DNS ownership before creating it. It deliberately leaves service-specific endpoint policies for the security owner to define; endpoint default access does not override IAM. Prepare a change set rather than assuming this is a complete isolated-cluster deployment:
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: ECR API/DKR and S3 endpoints in an existing VPC; not a complete private EKS stack
Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  PrivateSubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
    Description: Existing subnets in distinct Availability Zones
  PrivateRouteTableIds:
    Type: CommaDelimitedList
    Description: Route tables used by the image-pulling workloads
  EndpointSecurityGroupId:
    Type: AWS::EC2::SecurityGroup::Id
    Description: Existing same-VPC SG permitting HTTPS from the intended nodes/Pods
Resources:
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcId: !Ref VpcId
      RouteTableIds: !Ref PrivateRouteTableIds
      VpcEndpointType: Gateway
  ECRApiEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.api
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
  ECRDkrEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.dkr
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
```
When a new node group is required, `eksctl create nodegroup` uses **`--subnet-ids`**; the earlier `--vpc-private-subnets` flag was incorrect for this command. The example creates billable managed nodes after private API/service paths are ready; use it only if eksctl is the intended owner, with no existing `private-ng`. The instance size is illustrative, not sizing guidance.
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${PRIVATE_SUBNET_A:?Set an existing private subnet}"
: "${PRIVATE_SUBNET_B:?Set another private subnet}"
eksctl create nodegroup --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --name private-ng --managed --version auto --node-type m5.large \
  --nodes 2 --nodes-min 2 --nodes-max 3 --node-private-networking \
  --subnet-ids "$PRIVATE_SUBNET_A,$PRIVATE_SUBNET_B"
```

</details>

### 3. Which option provides hub routing among several non-overlapping VPCs?

- A. A public load balancer is mandatory
- B. Transit Gateway with complete routing
- C. Every cluster must share a VPC
- D. A NAT gateway provides Kubernetes discovery

<details>
<summary>Show Answer</summary>

**Answer: B. AWS Transit Gateway**

Transit Gateway is one design for many VPCs; it is not universally the most effective multi-cluster architecture. Compare VPC peering, shared VPCs, PrivateLink service exposure, VPC Lattice and mesh gateways against trust boundaries, scale, DNS, address overlap and cost. NAT also has private-connectivity uses; it does not provide service discovery.

For a TGW design, plan non-overlapping routable Pod/VPC CIDRs, attachments in each participating AZ, TGW route-table associations/propagation, workload-subnet routes and return routes. A TGW route alone is insufficient. Kubernetes ClusterIPs are virtual service addresses, not automatically routable remote endpoints. Export reachable Pod endpoints or gateway/load-balancer service addresses through an explicit discovery design. Read the actual route state before changing it:
```bash
set -euo pipefail
: "${AWS_REGION:?Set the transit gateway Region}"
: "${TGW_ROUTE_TABLE_ID:?Set the intended TGW route table}"
: "${VPC_ROUTE_TABLE_ID:?Set a workload-subnet route table}"
aws ec2 search-transit-gateway-routes --region "$AWS_REGION" \
  --transit-gateway-route-table-id "$TGW_ROUTE_TABLE_ID" \
  --filters Name=state,Values=active
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --route-table-ids "$VPC_ROUTE_TABLE_ID"
```
TGW does not have a firewall SG attached to it. Use endpoint/node/Pod SGs, NACLs, NetworkPolicy and inspected routing as appropriate. Cross-VPC SG referencing is a supported TGW feature under its documented attachment/Region constraints; it is distinct from attaching an SG to the TGW and does not replace routing.

Cloud Map requires namespace completion, a Service, registration and health/deregistration management. TGW does not automatically share private hosted-zone DNS. Use approved private-zone associations or Route 53 Resolver endpoints/rules. Do not forward to another VPC’s `base+2` resolver as if it were that cluster’s CoreDNS. This **Corefile fragment** assumes two real, reachable inbound resolvers that already resolve the exported `cluster2.example.internal` records. Merge it through the DNS configuration owner and retain the cluster-local zone:
```text
cluster2.example.internal:53 {
    errors
    cache 30
    forward . 10.1.20.10 10.1.21.10
}
```
The following ingress policy permits a remote source CIDR to one API port, based on the source address actually visible after NAT/proxies. Other matching policies can widen the allowance. Egress/DNS requirements must be designed separately; cross-cluster namespace/Pod labels are not automatically shared.
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: remote-api-ingress
  namespace: multicluster-demo
spec:
  podSelector:
    matchLabels:
      app: api-service
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 10.1.0.0/16
    ports:
    - protocol: TCP
      port: 8080
```
Istio multi-primary and primary-remote are different control-plane layouts; select the supported model and verify east-west gateways, identity trust and endpoint health. Existing App Mesh multi-cluster use must account for its September 2026 retirement. Compare hourly, processing and cross-AZ charges using the actual path; same-VPC or public load-balancer designs are not inherently invalid, but require their own security/cost analysis.

</details>

### 4. Which VPC CNI feature allocates IPv4 addresses in /28 blocks to increase address-slot density?

- A. hostNetwork for all Pods
- B. Prefix delegation
- C. NodePort for every Service
- D. Global Accelerator for Pod-to-Pod traffic

<details>
<summary>Show Answer</summary>

**Answer: B. Prefix delegation**

A delegated IPv4 /28 supplies 16 Pod addresses while consuming one ENI address slot. It can reduce allocation API work and improve Pod startup/density; it is not a universal packet-throughput optimization or a cure for total subnet exhaustion. IPv6 uses different prefix sizing. Supported Nitro hardware, contiguous free prefixes, kubelet maxPods and resource capacity still constrain density.

Merge this JSON fragment into the exact EKS add-on configuration after schema/ownership review, or use the corresponding Helm `env` values. The old lowercase `amazon-vpc-cni` ConfigMap keys do not configure the Linux CNI:
```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```
`WARM_PREFIX_TARGET=1` means one spare prefix, not prefix size. Positive `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` take precedence over the warm-prefix target. Large warm pools reserve more subnet space. Plan a node-group transition and maxPods settings; toggling the DaemonSet alone does not make existing nodes support any arbitrary density.

| Instance | Conventional secondary-IPv4 maxPods formula | Illustrative prefix-mode ceiling for these small instances |
|---|---:|---:|
| t3.medium | 17 | 110 |
| m5.large | 29 | 110 |
| c5.xlarge | 58 | 110 |
| r5.2xlarge | 58 | 110 |

These are configuration limits, not benchmark results or guarantees that every Pod fits. The former 250 entries for c5.xlarge/r5.2xlarge were incorrect: EKS’s recommended ceiling is 110 at fewer than 30 vCPUs and 250 at 30 or more vCPUs. Pod SG branch interfaces have separate limits. Prefix allocation needs contiguous /28 blocks, not a universal minimum /24 subnet, and does not automatically simplify SG policy.
```bash
set -euo pipefail
: "${AWS_REGION:?Set the node Region}"
kubectl get nodes -o 'custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,PODS:.status.allocatable.pods'
kubectl -n kube-system get daemonset aws-node -o yaml
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
aws ec2 describe-instance-types --region "$AWS_REGION" \
  --instance-types t3.medium m5.large c5.xlarge r5.2xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,vCPUs:VCpuInfo.DefaultVCpus,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4Slots:NetworkInfo.Ipv4AddressesPerInterface}'
```

</details>

### 5. Which proxy does Istio sidecar mode use, and how is it diagnosed?

<details>
<summary>Show Answer</summary>

**Answer: Envoy**

Istio sidecar mode uses Envoy, with istiod supplying discovery, routing and certificate configuration. The old Pilot/Citadel functions were consolidated into istiod and Mixer is not a current required component. Other meshes can use different proxies; Envoy is not a requirement of Kubernetes or every mesh.

Envoy supports connection pools, HTTP/TCP routing, retries, outlier detection, TLS and telemetry when configured. Merely adding an Envoy container does not arrange transparent traffic interception, workload identity, xDS or mTLS. For a real mesh, use its supported injector and proxy build. The old standalone Envoy 1.20 image and incomplete Deployment were not a valid current installation.

The following **standalone reverse-proxy bootstrap** illustrates the original listener/route/cluster concepts. It is locally validated with upstream Envoy 1.39.1. A separate HTTP application must listen on `127.0.0.1:8080` in the same network namespace. The proxy and admin listener bind only loopback; this is not a production or Kubernetes mesh deployment:
```yaml
admin:
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901
static_resources:
  listeners:
  - name: local-proxy
    address:
      socket_address:
        address: 127.0.0.1
        port_value: 15001
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: demo_http
          route_config:
            name: local-route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: /
                route:
                  cluster: local-app
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: local-app
    connect_timeout: 0.25s
    type: STATIC
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: local-app
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 8080
```
Save it as `envoy-config.yaml` and validate it with the matching upstream binary. Validation parses the configuration; it does not prove that the backend or workload identity works.
```bash
envoy --mode validate --concurrency 1 --config-path envoy-config.yaml
```
For an existing Kubernetes mesh proxy, discover the configured admin port and container name instead of assuming 19000. App Mesh’s default admin port is 9901; Istio commonly uses 15000, and deployment settings can differ. Run this port-forward in one terminal:
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the existing mesh workload namespace}"
: "${MESH_POD:?Set the existing proxy Pod}"
: "${ENVOY_ADMIN_PORT:?Use the admin port actually configured by that mesh}"
kubectl -n "$MESH_NAMESPACE" port-forward --address 127.0.0.1 \
  "pod/$MESH_POD" "19000:$ENVOY_ADMIN_PORT"
```
Then issue bounded read-only queries from another terminal. Config dumps can contain internal topology or sensitive configuration; do not publish them or expose the admin listener externally.
```bash
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/config_dump
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/stats
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/clusters
```
Inspect upstream health, connection-pool limits, retries, filter cost, memory and request latency together. Tune from measured workload behavior; deleting security filters solely to reduce overhead changes the security model.

</details>

### 6. What provides DNS on conventional EKS nodes, and how should it be configured?

<details>
<summary>Show Answer</summary>

**Answer: CoreDNS (identify the actual DNS/add-on owner first).**

CoreDNS is the usual DNS add-on on conventional EKS compute. Creation method/add-on ownership can differ; EKS Auto Mode includes managed cluster DNS and does not inherently need the traditional CoreDNS Deployment. Identify the compute/DNS owner before applying the following conventional-add-on checks. A ResourceNotFound response requires ownership investigation, not automatic reinstallation:
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name coredns
kubectl -n kube-system get deployment coredns -o yaml
kubectl -n kube-system get configmap coredns -o yaml
kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=kube-dns
```
Service DNS normally follows `<service>.<namespace>.svc.<cluster-domain>`; `cluster.local` is a common domain, not an immutable one. Headless/ExternalName records differ from normal ClusterIP records. Do not assume every arbitrary Pod IP has a useful reverse-DNS record.

This is an illustrative **Corefile**, not a ConfigMap to blindly overwrite. Preserve managed configuration, the actual cluster domain, probes and DNS Service. `pods insecure` permits syntactic Pod-IP DNS responses without Pod verification; choose the intended Kubernetes plugin mode.
```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf
    cache 30
    loop
    reload
    loadbalance
}
```
`errors` records failures; `health` and `ready` serve different probe roles; `kubernetes` answers cluster records; `forward` resolves other domains; `prometheus` exposes metrics; `cache`, `reload` and `loadbalance` affect caching/config reload/record order. The `loop` plugin detects certain simple forwarding loops during startup, not all dynamic DNS loops forever. `loadbalance` changes DNS answer ordering, not Service packet forwarding.

For conditional forwarding, use approved reachable DNS servers and permit UDP/TCP53. A VPC subnet’s first address such as10.0.0.1 is not a sample corporate DNS server. The `file` plugin serves an authoritative zone file that must be created/mounted and maintained with valid SOA/records; it is not a substitute for a stub-domain forward. Public resolvers require deliberate egress and disclosure policy; they cannot resolve private hosted zones by magic.

This cache fragment fixes the original argument order: `prefetch AMOUNT DURATION PERCENTAGE`. Replace the existing cache directive rather than adding a second one:
```text
cache 30 {
    success 10000
    denial 1024
    prefetch 10 2m 10%
}
```
In upstream CoreDNS 1.14.7, `denial1000` is accepted but normalized to1024; `success10000` normalizes to9984. Explicit1024 keeps the original effective denial capacity. These capacities are implementation behavior, not a measured DNS sizing recommendation.

Choose a **single scaling owner**. Use EKS-managed CoreDNS autoscaling when supported by the exact add-on version/schema, or a separately owned HPA/cluster-proportional autoscaler. The following HPA is only for a deliberately self-managed Deployment with metrics-server and CPU requests; do not combine it with another replica manager:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns
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
The original resource example (100m CPU request, 70Mi memory request, 170Mi memory limit) is illustrative, not workload-validated. Monitor query rate, errors, cache hit/miss behavior, memory/OOM and response latency, then size it. For diagnosis use an existing approved diagnostic workload with DNS tools; inspect dnsPolicy/dnsConfig/resolv.conf, kube-dns EndpointSlices and policy/SG/upstream paths. Test a cluster Service and an approved external/private name separately. The earlier obsolete dnsutils image and unowned bare Pod were not prerequisites for DNS diagnosis.

</details>

### 7. How should an existing App Mesh deployment be secured, observed and migrated?

<details>
<summary>Show Answer</summary>

**Answer: Review the existing graph, identity and telemetry, then validate a supported replacement.**

**Historical operations and migration exercise:** AWS App Mesh support and resource access end on **September 30, 2026**. Do not follow the original recipe to provision a new mesh, Private CA and public Grafana. For an existing deployment, inventory its graph and plan migration before the cutoff. ECS Service Connect is not an EKS installation target; evaluate a supported Kubernetes mesh/gateway architecture for the features actually used.
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the namespace of the existing mesh workloads}"
kubectl get meshes.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get virtualnodes.appmesh.k8s.aws,virtualservices.appmesh.k8s.aws,virtualrouters.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get deployments,services
```
**1. Map the existing graph.** Mesh namespace selectors choose participating namespaces; VirtualNode pod selectors choose workloads, listeners and service discovery. VirtualService names route to a VirtualNode or VirtualRouter; router routes select weighted VirtualNodes. Inventory backend references, endpoint DNS, health checks, IAM/IRSA, injector settings and application listening ports. The original `service-a:latest` placeholder and missing service-b workloads were not a working application. Do not overwrite existing ServiceAccounts or attach full-access policies as a troubleshooting step.

**2. Distinguish TLS from mutual authentication.** A listener in STRICT mode with only a server certificate requires encrypted connections but does not by itself authenticate clients. App Mesh mTLS needs client certificates and server-side client trust, as well as client-side server trust/SAN checks. Client certificates and listener validation trust use files or SDS, not an ACM client-certificate reference. App-to-Envoy traffic inside the workload is not automatically encrypted by proxy-to-proxy mTLS.

The following is a **legacy configuration review example**, not a new installation. Its files must already be securely mounted in the proxy, certificates must have the required identities/usages, service-b must exist, and the matching namespace must belong to the intended Mesh. Add approved client SAN restrictions as required by the trust design; trusting a CA alone accepts its eligible client certificates:
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
  - portMapping:
      port: 8080
      protocol: http
    tls:
      mode: STRICT
      certificate:
        file:
          certificateChain: /certs/server.crt
          privateKey: /certs/server.key
      validation:
        trust:
          file:
            certificateChain: /certs/trusted-client-ca.pem
    outlierDetection:
      baseEjectionDuration:
        unit: s
        value: 30
      interval:
        unit: s
        value: 10
      maxEjectionPercent: 50
      maxServerErrors: 5
  backends:
  - virtualService:
      virtualServiceRef:
        name: service-b
      clientPolicy:
        tls:
          enforce: true
          ports: [8080]
          certificate:
            file:
              certificateChain: /certs/client.crt
              privateKey: /certs/client.key
          validation:
            trust:
              file:
                certificateChain: /certs/trusted-server-ca.pem
            subjectAlternativeNames:
              match:
                exact: [service-b.app-namespace.svc.cluster.local]
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
  logging:
    accessLog:
      file:
        path: /dev/stdout
```
Do not select all ACTIVE CAs from an account into one variable. Creating a root CA requires an explicit configuration and activation/certificate steps and incurs charges; it does not immediately produce a usable certificate. Preserve exact intended ARNs. App Mesh Kubernetes CRD fields are case-sensitive (`certificateARN`, `certificateAuthorityARNs`); `${CA_ARN}` in a plain YAML file is not shell interpolation. The shown file-based example avoids pretending that a missing CA workflow has run.

For existing plaintext peers, stage a documented PERMISSIVE transition, provision client/server identities and trust, test both accepted and rejected peers, then require STRICT. Inspect `ssl.handshake`, `ssl.no_certificate`, `ssl.fail_verify_no_cert` and `ssl.fail_verify_san` plus real request results. A successful server-TLS handshake alone is insufficient proof of mTLS.

**3. Preserve observability during migration.** `Mesh.spec.tracing`, `Mesh.spec.logging` and `Mesh.spec.serviceDiscovery` from the original recipe are not fields in the reviewed controller 1.13.1 CRD. Access logging belongs on VirtualNode (as above). App Mesh Envoy image tracing settings are separate, for example this **container environment fragment** requires a working local X-Ray daemon/collector on2000, permissions, endpoint access and trace-context propagation:
```yaml
env:
- name: ENABLE_ENVOY_XRAY_TRACING
  value: "1"
- name: XRAY_DAEMON_PORT
  value: "2000"
```
Collect the proxy’s actual `/stats` or Prometheus endpoint with an approved collector. CloudWatch requires configured scraping/export/EMF; do not assume `AWS/AppMesh` RequestCount/Latency metrics appear automatically. Inventory the actual namespace, metric names, dimensions and units before building a dashboard. Keep the existing CloudWatch/Prometheus/Grafana owner, credentials and supported StorageClasses. Avoid floating manifests, hardcoded Grafana admin passwords and an unreviewed public LoadBalancer. This optional Grafana provisioning fragment only identifies an existing Prometheus datasource; it does not install or secure either system:
```yaml
apiVersion: 1
datasources:
- name: Prometheus
  type: prometheus
  url: http://prometheus-server.prometheus.svc.cluster.local
  access: proxy
  isDefault: true
```
**4. Map traffic behavior explicitly.** This legacy router example assumes both versioned VirtualNodes already exist and have healthy endpoints. Weights are not exact request-count guarantees. Outlier detection is endpoint ejection, distinct from connection-pool circuit-breaking limits. The four original HTTP retry event strings are valid: `client-error` means 409 and `stream-error` means refused streams. Choose retries for idempotent operations within the overall timeout budget; retries can amplify failure load.
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
  - portMapping:
      port: 8080
      protocol: http
  routes:
  - name: service-a-route
    httpRoute:
      match:
        prefix: /
      action:
        weightedTargets:
        - virtualNodeRef:
            name: service-a-v1
          weight: 90
        - virtualNodeRef:
            name: service-a-v2
          weight: 10
      retryPolicy:
        maxRetries: 3
        perRetryTimeout:
          unit: ms
          value: 2000
        httpRetryEvents:
        - gateway-error
```
**5. Validate and cut over gradually.** Compare routing, authorized/unauthorized peers, DNS, TLS rotation, retries, failure recovery, traces and metric continuity before moving traffic. Preserve a rollback path within the remaining product-support window. The original100–200m CPU and128–256Mi proxy memory values are **unverified example estimates**, not measurements or guaranteed sizing. Measure real saturation, memory, latency and error rates. No mesh, CA, collector or cloud dashboard was provisioned in this audit.

</details>

### 8. Which variable configures attached ENI MTU in VPC CNI 1.23.0?

- A. `ENI_MTU`
- B. `AWS_VPC_ENI_MTU`
- C. `VPC_MTU_SIZE`
- D. `MAX_ENI`

<details>
<summary>Show Answer</summary>

**Answer: B. `AWS_VPC_ENI_MTU`**

`POD_MTU` configures Pod virtual interfaces and derives from the ENI MTU when unset. `ENI_MTU` was the wrong name. Match the actual path MTU and planned node/Pod rollout; an accepted numeric value does not guarantee that gateways/tunnels/remote endpoints accept that packet size. SGs are not MTU-setting devices.

</details>

### 9. Where does the strict Pod-SG TCP early-demux workaround belong?

- A. Application Deployment
- B. CoreDNS ConfigMap
- C. CNI init container
- D. LoadBalancer annotation

<details>
<summary>Show Answer</summary>

**Answer: C. `aws-vpc-cni-init`**

The documented `DISABLE_TCP_EARLY_DEMUX=true` setting belongs to the init container, represented by Helm `init.env`. Setting it on the main `aws-node` container does not apply that init-time change. Confirm the strict-mode kubelet-probe issue; standard Pod-SG mode does not require this workaround.

</details>

### 10. Which rule-order optimization does Kubernetes NetworkPolicy guarantee?

- A. Put the hottest rule first
- B. Sort names alphabetically
- C. Create restrictive policies last
- D. No order guarantee

<details>
<summary>Show Answer</summary>

**Answer: D. None; matching allows are additive.**

There is no portable “first match wins” or newest-policy precedence. Selectors/directions and the union of allows determine isolation. Vendor tier/order APIs are separate. Preserve required restrictions and measure policy programming/runtime cost rather than deleting rules based solely on count.

</details>

### 11. A subnet is exhausted. Does increasing WARM_IP_TARGET add address capacity?

- A. Yes, it expands the subnet
- B. No, it increases spare-address demand
- C. Yes, it bypasses ENI limits
- D. Yes, it repairs every ContainerCreating Pod

<details>
<summary>Show Answer</summary>

**Answer: B. No; it asks for more spare addresses.**

A larger warm target can reduce allocation latency when capacity exists, but also reserves addresses and can worsen exhaustion. Identify subnet space, ENI slots, maxPods, API throttling and prefix fragmentation independently. Prefix delegation does not create more total IPv4 addresses.

</details>

### 12. Which API should be inspected for current Service backend addresses and conditions?

- A. Only Node events
- B. Ingress annotations
- C. EndpointSlice
- D. Only the Service ClusterIP

<details>
<summary>Show Answer</summary>

**Answer: C. EndpointSlice**

Query EndpointSlices in the Service namespace using `kubernetes.io/service-name=<service>`. Check addresses, ports and ready/serving/terminating conditions together with the Service selector and targetPort. The legacy Endpoints object can truncate large endpoint sets; an empty result can indicate selector/readiness problems rather than a load-balancer failure.

</details>

### 13. What does trafficDistribution: PreferSameZone mean?

- A. Never cross an AZ boundary
- B. Prefer same zone with fallback
- C. Move existing Pods to one AZ
- D. Override all Local traffic policies

<details>
<summary>Show Answer</summary>

**Answer: B. Prefer available same-zone endpoints, with fallback.**

It is a routing preference for a compatible service proxy, not an AZ isolation policy. Ensure enough local capacity. An existing topology-mode Auto annotation takes precedence. Local internal/external traffic policies impose stricter node-local requirements for their respective traffic and can drop traffic when no local endpoint exists.

</details>

### 14. Calculate the bandwidth-delay product for a hypothetical 10 Gbps flow with 20 ms RTT.

<details>
<summary>Show Answer</summary>

**Answer: 25,000,000 bytes, approximately 23.84 MiB.**

```text
10,000,000,000 bits/s × 0.020 s / 8 = 25,000,000 bytes
```
This is an arithmetic example, not an EKS benchmark or a recommendation to set every socket buffer to that value. Account for actual EC2 single-flow/burst limits, TCP auto-tuning, window scaling, concurrent connections and memory pressure. The earlier 16 MiB maxima cannot be called optimal without measurements. Keepalive operates on enabled idle sockets; it is separate from HTTP pooling and buffer sizing.

</details>

### 15. How do you separate DNS, Service selection and application connectivity failures?

<details>
<summary>Show Answer</summary>

**Answer: Collect evidence, then test the actual protocol with positive controls.**

Check the affected Pod’s events before classifying ContainerCreating as networking. Resolve a known cluster Service and the intended hostname, inspect Service/EndpointSlice selector-port-readiness consistency, then compare Pod-IP and Service-URL access from the same source. Test a known allowed path so a missing tool, failed DNS or dead backend is not mistaken for a policy denial. Use the bounded diagnostics from the source chapter:
```bash
set -euo pipefail
: "${APP_NAMESPACE:?Set the affected namespace}"
: "${APP_POD:?Set the affected Pod}"
: "${APP_SERVICE:?Set the affected Service}"
kubectl -n "$APP_NAMESPACE" describe pod "$APP_POD"
kubectl -n "$APP_NAMESPACE" get events --field-selector "involvedObject.name=$APP_POD" --sort-by=.metadata.creationTimestamp
kubectl -n "$APP_NAMESPACE" get service "$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get networkpolicy
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
```
For a load balancer, identify the controller/class, scheme, target type and target-health reason. Verify actual application/health ports, SG and route paths, TLS/SNI and Host routing. ICMP behavior alone cannot prove TCP/UDP NetworkPolicy enforcement. Change one confirmed cause, retain the owner’s rollback path and repeat the same checks. No production network test is claimed by these examples.

</details>

Official references: [Private EKS](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [VPC CNI 1.23.0](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md), [CoreDNS cache](https://coredns.io/plugins/cache/), [App Mesh mTLS](https://docs.aws.amazon.com/app-mesh/latest/userguide/mutual-tls.html), [App Mesh metrics](https://docs.aws.amazon.com/app-mesh/latest/userguide/metrics.html), [Envoy 1.39.1](https://github.com/envoyproxy/envoy/releases/tag/v1.39.1).
