# Multi-cluster Service Mesh

> **Supported Versions**: Istio 1.18+
> **Last Updated**: November 24, 2025
> **Kubernetes Compatibility**: 1.32+

Multi-cluster Service Mesh connects multiple Kubernetes clusters into a unified service mesh.

## Table of Contents

1. [Do You Really Need Multi-cluster?](#do-you-really-need-multi-cluster)
2. [Architecture Selection Guide](#architecture-selection-guide)
3. [Istio vs AWS VPC Lattice](#istio-vs-aws-vpc-lattice)
4. [Topology](#topology)
5. [Primary-Remote Setup](#primary-remote-setup)
6. [Multi-Primary Setup](#multi-primary-setup)
7. [Cross-cluster Communication](#cross-cluster-communication)
8. [Using with VPC Lattice](#using-with-vpc-lattice)
9. [Practical Examples](#practical-examples)
10. [Performance and Cost Comparison](#performance-and-cost-comparison)
11. [Troubleshooting](#troubleshooting)

## Do You Really Need Multi-cluster?

Multi-cluster Service Mesh is powerful but increases complexity and cost. Careful consideration is needed before adoption.

### Decision Flow

```mermaid
flowchart TD
    Start[Multi-cluster<br/>Consideration]

    Q1{Already have<br/>multiple clusters?}
    Q2{Regional<br/>separation needed?}
    Q3{DR/HA<br/>required?}
    Q4{Strong L7<br/>features needed?}
    Q5{Can handle<br/>operational complexity?}

    SingleCluster[Single-cluster<br/>Istio<br/>Simplest]
    VPCLattice[AWS VPC Lattice<br/>AWS Managed]
    MultiClusterIstio[Multi-cluster<br/>Istio<br/>Full Control]
    Hybrid[Hybrid:<br/>Istio + Lattice<br/>Best of Both]

    Start --> Q1
    Q1 -->|No| SingleCluster
    Q1 -->|Yes| Q2
    Q2 -->|No| SingleCluster
    Q2 -->|Yes| Q3
    Q3 -->|No| VPCLattice
    Q3 -->|Yes| Q4
    Q4 -->|No| VPCLattice
    Q4 -->|Yes| Q5
    Q5 -->|No| VPCLattice
    Q5 -->|Yes| Hybrid

    Hybrid -.->|Option| MultiClusterIstio

    %% Style definitions
    classDef question fill:#F8B52A,stroke:#333,stroke-width:2px,color:black;
    classDef simple fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef managed fill:#FF9900,stroke:#333,stroke-width:2px,color:black;
    classDef advanced fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef hybrid fill:#3B48CC,stroke:#333,stroke-width:2px,color:white;

    %% Apply classes
    class Q1,Q2,Q3,Q4,Q5 question;
    class SingleCluster simple;
    class VPCLattice managed;
    class MultiClusterIstio advanced;
    class Hybrid hybrid;
```

### When Multi-cluster is Needed

#### 1. Geographic Distribution and Latency Optimization

```mermaid
flowchart LR
    subgraph US[US Region]
        C1[EKS Cluster<br/>us-east-1]
    end

    subgraph EU[Europe Region]
        C2[EKS Cluster<br/>eu-west-1]
    end

    subgraph APAC[Asia Region]
        C3[EKS Cluster<br/>ap-northeast-2]
    end

    Mesh[Istio Mesh<br/>Unified Management]

    Mesh -.->|Config sync| C1
    Mesh -.->|Config sync| C2
    Mesh -.->|Config sync| C3

    C1 <-->|Cross-region<br/>mTLS| C2
    C2 <-->|Cross-region<br/>mTLS| C3
    C1 <-->|Cross-region<br/>mTLS| C3

    %% Style definitions
    classDef cluster fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef mesh fill:#FF9900,stroke:#333,stroke-width:2px,color:black;

    %% Apply classes
    class C1,C2,C3 cluster;
    class Mesh mesh;
```

**When needed**:
- Global user-facing services (latency goal <100ms)
- Data sovereignty compliance (GDPR, financial data localization)
- Regional traffic routing and failure isolation

#### 2. Disaster Recovery (DR)

```mermaid
flowchart TB
    subgraph Active[Active Cluster<br/>Primary Region]
        Prod1[Production<br/>Workloads]
    end

    subgraph Standby[Standby Cluster<br/>DR Region]
        Prod2[Standby<br/>Workloads]
    end

    DNS[Global DNS<br/>Route53]
    Users[Users]

    Users -->|Normal| DNS
    DNS -->|100% traffic| Active
    DNS -.->|0% traffic| Standby

    Active -.->|Real-time<br/>config replication| Standby

    Failover[Disaster Occurs]
    Failover -->|Failover| DNS
    DNS -->|0% traffic| Active
    DNS -->|100% traffic| Standby

    %% Style definitions
    classDef active fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef standby fill:#3B48CC,stroke:#333,stroke-width:2px,color:white;
    classDef dns fill:#FF9900,stroke:#333,stroke-width:2px,color:black;
    classDef failover fill:#E6522C,stroke:#333,stroke-width:2px,color:white;

    %% Apply classes
    class Prod1 active;
    class Prod2 standby;
    class DNS dns;
    class Failover failover;
```

**When needed**:
- RTO (Recovery Time Objective) <1 hour
- RPO (Recovery Point Objective) <15 minutes
- Automatic Failover on regional failure

#### 3. Environment Separation and Staged Deployment

**When needed**:
- Dev/Staging/Prod cluster separation with unified management
- Blue/Green deployments at cluster level
- Canary deployments with gradual regional expansion

#### 4. Organizational Boundaries and Security Isolation

**When needed**:
- Independent cluster operation per team/department
- Enhanced Multi-tenancy
- Physical isolation for regulatory compliance

### When Multi-cluster is NOT Needed

#### 1. Single Region, Small Scale Services

```mermaid
flowchart TD
    subgraph SingleCluster[Single EKS Cluster]
        NS1[Namespace: prod]
        NS2[Namespace: staging]
        NS3[Namespace: dev]

        Istio[Istio Control Plane]

        Istio -.->|Manages| NS1
        Istio -.->|Manages| NS2
        Istio -.->|Manages| NS3
    end

    Note[Multi-cluster not needed<br/>- Namespace separation sufficient<br/>- NetworkPolicy for isolation<br/>- Simple management]

    %% Style definitions
    classDef namespace fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef istio fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef note fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class NS1,NS2,NS3 namespace;
    class Istio istio;
    class Note note;
```

**Use instead**:
- Kubernetes Namespace separation
- NetworkPolicy for network isolation
- RBAC for access control

#### 2. When Operational Complexity Cannot Be Handled

**Multi-cluster operational requirements**:
- Minimum 2-3 Istio experts
- East-West Gateway management and monitoring
- Cross-cluster certificate management
- Cross-cluster debugging capability

**If your team is small**:
- Single-cluster Istio or
- AWS VPC Lattice (managed service)

#### 3. When Cost is a Key Consideration

**Multi-cluster additional costs**:
- LoadBalancer for East-West Gateway ($20-50/month per region)
- Cross-region data transfer ($0.02/GB)
- Control Plane redundancy (2-3x resources)

### Checklist

Answer these questions before adoption:

**Architecture**:
- [ ] Are 2 or more clusters already in operation?
- [ ] Is multi-region deployment needed?
- [ ] Are cross-cluster service calls frequent?

**Business Requirements**:
- [ ] Targeting global users?
- [ ] Is Disaster Recovery (DR) essential?
- [ ] Are RTO/RPO requirements strict?

**Security and Compliance**:
- [ ] Is data localization needed?
- [ ] Is strong cross-cluster isolation needed?

**Operational Capability**:
- [ ] Do you have Istio experts?
- [ ] Can you debug complex networking issues?
- [ ] Can you afford additional costs?

**Results**:
- 9+ checks: Multi-cluster Istio recommended
- 5-8 checks: Consider VPC Lattice or Hybrid
- 4 or fewer checks: Start with Single-cluster Istio

## Architecture Selection Guide

### Optimal Solution by Scenario

| Scenario | Single-cluster | Multi-cluster Istio | VPC Lattice | Hybrid |
|------|----------------|---------------------|-------------|--------|
| **Single region, small scale** | Optimal | Overkill | Unnecessary | Unnecessary |
| **Multi-region, strong L7 needed** | Not possible | Optimal | Limited | Recommended |
| **AWS-centric, simple connectivity** | Limited | Overkill | Optimal | Unnecessary |
| **DR, automatic Failover** | Not possible | Optimal | Manual | Recommended |
| **Cost optimization priority** | Optimal | Expensive | Recommended | Medium |
| **Operational simplification** | Optimal | Complex | Optimal | Medium |
| **Fine-grained traffic control** | Possible | Optimal | Limited | Recommended |

### Comparison of Each Solution

#### Single-cluster Istio

**Pros**:
- Simplest management
- Low cost
- Fast debugging
- All Istio features available

**Cons**:
- Single point of failure
- Complete service outage on regional failure
- No geographic distribution possible

**Suitable when**:
- Single region service
- Small team (<50 people)
- High availability not essential

#### Multi-cluster Istio

**Pros**:
- Complete geographic distribution
- Automatic DR and Failover
- All L7 features (Retry, Timeout, Circuit Breaker)
- Fine-grained traffic control
- Unified observability

**Cons**:
- High operational complexity
- East-West Gateway management required
- Cross-region data transfer costs
- Difficult debugging

**Suitable when**:
- Global services
- Strong DR needed
- Fine-grained L7 control essential

#### AWS VPC Lattice

**Pros**:
- AWS fully managed
- Simple setup
- Low operational burden
- Safe cross-VPC connectivity
- Cost effective

**Cons**:
- Limited L7 features (no Retry, Circuit Breaker)
- AWS lock-in
- No fine-grained traffic control
- Lacks Istio observability

**Suitable when**:
- AWS-centric architecture
- Only simple service connectivity needed
- Operational simplification priority

## Istio vs AWS VPC Lattice

### Feature Comparison

| Feature | Istio Multi-cluster | AWS VPC Lattice | Hybrid |
|------|---------------------|-----------------|--------|
| **Traffic Routing** | |||
| Header-based routing | Fully supported | Limited | Istio handles |
| Weighted routing | Supported | Supported | Both possible |
| Path-based routing | Supported | Supported | Both possible |
| **Resilience** | |||
| Retry | Fine-grained control | Not supported | Istio handles |
| Timeout | Fine-grained control | Basic only | Istio handles |
| Circuit Breaker | Supported | Not supported | Istio handles |
| **Security** | |||
| mTLS | Automatic | Supported | Both |
| AuthN/AuthZ | Fine-grained policies | IAM only | Istio handles |
| **Observability** | |||
| Distributed tracing | Jaeger/Zipkin | Limited | Istio handles |
| Metrics | Detailed | Basic only | Istio handles |
| **Operations** | |||
| Management complexity | High | Low | Medium |
| Cost | High | Low | Medium |
| AWS integration | Manual | Native | Good |

### Architecture Pattern Comparison

#### Pattern 1: Istio Multi-cluster Only

```mermaid
flowchart TB
    subgraph Cluster1[Cluster 1<br/>us-east-1]
        Istiod1[Istiod]
        EWG1[East-West<br/>Gateway]
        App1[App Services]
    end

    subgraph Cluster2[Cluster 2<br/>us-west-2]
        Istiod2[Istiod]
        EWG2[East-West<br/>Gateway]
        App2[App Services]
    end

    Istiod1 <-.->|Service<br/>Discovery| Istiod2
    EWG1 <-->|mTLS<br/>Cross-region| EWG2

    App1 -->|Envoy| EWG1
    EWG2 -->|Envoy| App2

    %% Style definitions
    classDef istio fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef gateway fill:#FF9900,stroke:#333,stroke-width:2px,color:black;
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Istiod1,Istiod2 istio;
    class EWG1,EWG2 gateway;
    class App1,App2 app;
```

**Pros**:
- Full Istio features
- Unified observability
- Fine-grained control

**Cons**:
- East-West Gateway management required
- High complexity
- Cross-region data transfer costs

#### Pattern 2: VPC Lattice Only

```mermaid
flowchart TB
    subgraph VPC1[VPC 1<br/>us-east-1]
        App1[App Services]
    end

    subgraph VPC2[VPC 2<br/>us-west-2]
        App2[App Services]
    end

    subgraph Lattice[AWS VPC Lattice]
        SN[Service Network]
        SVC1[Service 1]
        SVC2[Service 2]
    end

    App1 -->|Register| SVC1
    App2 -->|Register| SVC2
    SVC1 <-->|Routing| SN
    SVC2 <-->|Routing| SN

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef lattice fill:#FF9900,stroke:#333,stroke-width:2px,color:black;

    %% Apply classes
    class App1,App2 app;
    class SN,SVC1,SVC2 lattice;
```

**Pros**:
- AWS fully managed
- Simple setup
- Low operational burden

**Cons**:
- Cannot use Istio features
- Limited traffic control
- Not Kubernetes native

#### Pattern 3: Hybrid (Recommended)

```mermaid
flowchart TB
    subgraph Cluster1[Cluster 1<br/>us-east-1]
        subgraph IstioMesh1[Istio Mesh]
            Istiod1[Istiod]
            App1A[Service A]
            App1B[Service B]
        end
    end

    subgraph Cluster2[Cluster 2<br/>us-west-2]
        subgraph IstioMesh2[Istio Mesh]
            Istiod2[Istiod]
            App2A[Service A]
            App2B[Service B]
        end
    end

    subgraph Lattice[AWS VPC Lattice]
        SN[Service Network<br/>Cross-cluster]
    end

    IstioMesh1 -->|Intra-cluster:<br/>Full Istio features| App1A
    App1A <-->|Intra-cluster:<br/>mTLS, Retry| App1B

    IstioMesh2 -->|Intra-cluster:<br/>Full Istio features| App2A
    App2A <-->|Intra-cluster:<br/>mTLS, Retry| App2B

    App1B <-->|Cross-cluster:<br/>VPC Lattice| SN
    SN <-->|Cross-cluster:<br/>VPC Lattice| App2B

    %% Style definitions
    classDef istio fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef lattice fill:#FF9900,stroke:#333,stroke-width:2px,color:black;

    %% Apply classes
    class Istiod1,Istiod2 istio;
    class App1A,App1B,App2A,App2B app;
    class SN lattice;
```

**Pros**:
- Intra-cluster: All advanced Istio features (Retry, Circuit Breaker, fine-grained routing)
- Cross-cluster: Simple VPC Lattice management and stability
- Reduced operational complexity (no East-West Gateway)
- Cost optimization (minimize cross-region traffic)

**Cons**:
- Need to understand two technology stacks
- Cross-cluster limited to Lattice features

**Suitable when**:
- AWS environment
- Complex traffic control needed intra-cluster
- Only simple connectivity needed cross-cluster

## Multi-cluster Overview

With Multi-cluster Service Mesh you can:
- Multi-region deployment
- Disaster Recovery (DR)
- Environment separation (dev/staging/prod)
- Cross-cluster service discovery and communication

## Topology

### Primary-Remote

```mermaid
flowchart TB
    subgraph PrimaryCluster["Primary Cluster<br/>us-east-1"]
        Istiod[Istiod<br/>Control Plane]
        ServiceA[Service A]
    end

    subgraph RemoteCluster["Remote Cluster<br/>us-west-2"]
        ServiceB[Service B]
        ServiceC[Service C]
    end

    Istiod -.->|Push config| ServiceB
    Istiod -.->|Push config| ServiceC
    ServiceA <-->|mTLS| ServiceB
    ServiceB <-->|mTLS| ServiceC

    %% Style definitions
    classDef primary fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef remote fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef service fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Istiod primary;
    class ServiceB,ServiceC remote;
    class ServiceA service;
```

**Characteristics**:
- Single Control Plane (Primary)
- Multiple Data Planes (Remote)
- Simple management
- Single point of failure (Primary)

### Multi-Primary

```mermaid
flowchart TB
    subgraph Cluster1["Cluster 1<br/>us-east-1"]
        Istiod1[Istiod<br/>Control Plane]
        ServiceA1[Service A]
    end

    subgraph Cluster2["Cluster 2<br/>us-west-2"]
        Istiod2[Istiod<br/>Control Plane]
        ServiceA2[Service A]
    end

    Istiod1 <-.->|Sync| Istiod2
    ServiceA1 <-->|Load Balancing| ServiceA2

    %% Style definitions
    classDef primary fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef service fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Istiod1,Istiod2 primary;
    class ServiceA1,ServiceA2 service;
```

**Characteristics**:
- Multiple Control Planes
- High availability
- Complex management
- Regional autonomy

## Primary-Remote Setup

### 1. Primary Cluster Setup

```bash
# Context setup
export CTX_CLUSTER1=cluster1

# Install Istio
istioctl install --context="${CTX_CLUSTER1}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster1
      network: network1
EOF

# Install East-West Gateway
samples/multicluster/gen-eastwest-gateway.sh \
  --mesh mesh1 --cluster cluster1 --network network1 | \
  istioctl install --context="${CTX_CLUSTER1}" -y -f -

# Expose Gateway
kubectl apply --context="${CTX_CLUSTER1}" -f \
  samples/multicluster/expose-services.yaml
```

### 2. Remote Cluster Setup

```bash
# Context setup
export CTX_CLUSTER2=cluster2

# Create Remote Secret
istioctl create-remote-secret \
  --context="${CTX_CLUSTER1}" \
  --name=cluster1 | \
  kubectl apply -f - --context="${CTX_CLUSTER2}"

# Install Istio with Remote configuration
istioctl install --context="${CTX_CLUSTER2}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network1
      remotePilotAddress: ${DISCOVERY_ADDRESS}
EOF
```

## Multi-Primary Setup

### 1. Set Both Clusters as Primary

```bash
# Cluster 1
istioctl install --context="${CTX_CLUSTER1}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster1
      network: network1
EOF

# Cluster 2
istioctl install --context="${CTX_CLUSTER2}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network2
EOF
```

### 2. Cross-register Remote Secrets

```bash
# Cluster 1's Secret to Cluster 2
istioctl create-remote-secret \
  --context="${CTX_CLUSTER1}" \
  --name=cluster1 | \
  kubectl apply -f - --context="${CTX_CLUSTER2}"

# Cluster 2's Secret to Cluster 1
istioctl create-remote-secret \
  --context="${CTX_CLUSTER2}" \
  --name=cluster2 | \
  kubectl apply -f - --context="${CTX_CLUSTER1}"
```

## Cross-cluster Communication

### Service Entry

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: httpbin-cluster2
spec:
  hosts:
  - httpbin.default.svc.cluster.local
  location: MESH_INTERNAL
  ports:
  - number: 8000
    name: http
    protocol: HTTP
  resolution: DNS
  addresses:
  - 240.0.0.1
  endpoints:
  - address: ${CLUSTER2_INGRESS_HOST}
    ports:
      http: 15443
```

## Using with VPC Lattice

### Hybrid Architecture Implementation

You can combine Istio and VPC Lattice to create the best of both.

#### Step 1: Install Istio Independently in Each Cluster

```bash
# Cluster 1 (single cluster mode)
export CTX_CLUSTER1=cluster1
istioctl install --context="${CTX_CLUSTER1}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1-cluster1
      multiCluster:
        enabled: false  # Disable Multi-cluster
      network: network1
EOF

# Cluster 2 (independent installation)
export CTX_CLUSTER2=cluster2
istioctl install --context="${CTX_CLUSTER2}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1-cluster2
      multiCluster:
        enabled: false  # Disable Multi-cluster
      network: network2
EOF
```

#### Step 2: Create VPC Lattice Service Network

```bash
# Create Service Network
aws vpc-lattice create-service-network \
  --name my-service-network \
  --auth-type AWS_IAM

# Save Service Network ID
SERVICE_NETWORK_ID=$(aws vpc-lattice list-service-networks \
  --query 'items[?name==`my-service-network`].id' \
  --output text)

# Connect VPC (Cluster 1 VPC)
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier $SERVICE_NETWORK_ID \
  --vpc-identifier $VPC1_ID

# Connect VPC (Cluster 2 VPC)
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier $SERVICE_NETWORK_ID \
  --vpc-identifier $VPC2_ID
```

#### Step 3: Register Kubernetes Service to VPC Lattice

```yaml
# Register Cluster 1's service to VPC Lattice
apiVersion: application-networking.k8s.aws/v1alpha1
kind: ServiceExport
metadata:
  name: my-service
  namespace: default
  annotations:
    application-networking.k8s.aws/lattice-service-network: my-service-network
spec: {}
---
# Routing from Cluster 1 to VPC Lattice
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: remote-service-via-lattice
  namespace: default
spec:
  hosts:
  - remote-service.lattice.svc.cluster.local
  location: MESH_EXTERNAL
  ports:
  - number: 80
    name: http
    protocol: HTTP
  resolution: DNS
  endpoints:
  - address: ${LATTICE_SERVICE_DNS}  # VPC Lattice DNS
    ports:
      http: 80
---
# Don't apply mTLS for VPC Lattice traffic
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: remote-service-via-lattice
  namespace: default
spec:
  host: remote-service.lattice.svc.cluster.local
  trafficPolicy:
    tls:
      mode: SIMPLE  # VPC Lattice handles TLS
```

#### Step 4: IAM Policy Setup

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "vpc-lattice-svcs:SourceVpc": [
            "${VPC1_ID}",
            "${VPC2_ID}"
          ]
        }
      }
    }
  ]
}
```

### Traffic Flow

```mermaid
sequenceDiagram
    autonumber
    participant App1 as Cluster 1<br/>Service A
    participant Envoy1 as Envoy<br/>(Cluster 1)
    participant Lattice as VPC Lattice
    participant App2 as Cluster 2<br/>Service B

    Note over App1,App2: Cross-cluster call

    App1->>Envoy1: 1\. HTTP request
    Note over Envoy1: Istio collects<br/>metrics locally
    Envoy1->>Lattice: 2\. Route to VPC Lattice DNS
    Note over Lattice: AWS managed<br/>service discovery
    Lattice->>App2: 3\. Forward to Cluster 2 service
    Note over App2: Istio collects<br/>metrics in Cluster 2
    App2->>Lattice: 4\. Response
    Lattice->>Envoy1: 5\. Forward response
    Envoy1->>App1: 6\. Response
```

### Pros and Considerations

**Pros**:
- Intra-cluster: All Istio features (Retry, Circuit Breaker, fine-grained routing)
- Cross-cluster: Simple VPC Lattice management
- No East-West Gateway needed -> Reduced operational burden
- AWS native integration

**Considerations**:
- Cross-cluster traffic limited to VPC Lattice features
- VPC Lattice cannot finely control Retry, Timeout
- Istio distributed tracing breaks at cluster boundaries (traced independently in each cluster)

## Practical Examples

### Example 1: Global E-commerce (Multi-Primary + VPC Lattice)

#### Architecture

```mermaid
flowchart TB
    subgraph US[US Region<br/>us-east-1]
        subgraph Cluster1[EKS Cluster 1]
            Istiod1[Istiod]
            Frontend1[Frontend<br/>Service]
            Cart1[Cart<br/>Service]
            Order1[Order<br/>Service]
        end
    end

    subgraph EU[Europe Region<br/>eu-west-1]
        subgraph Cluster2[EKS Cluster 2]
            Istiod2[Istiod]
            Frontend2[Frontend<br/>Service]
            Cart2[Cart<br/>Service]
            Order2[Order<br/>Service]
        end
    end

    subgraph Payment[Payment Service<br/>ap-northeast-2]
        subgraph Cluster3[EKS Cluster 3]
            Istiod3[Istiod]
            Payment3[Payment<br/>Service]
        end
    end

    Lattice[VPC Lattice<br/>Service Network]

    Frontend1 <-->|Istio<br/>internal call| Cart1
    Cart1 <-->|Istio| Order1

    Frontend2 <-->|Istio<br/>internal call| Cart2
    Cart2 <-->|Istio| Order2

    Order1 -->|VPC Lattice| Lattice
    Order2 -->|VPC Lattice| Lattice
    Lattice -->|Routing| Payment3

    %% Style definitions
    classDef istio fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef lattice fill:#FF9900,stroke:#333,stroke-width:2px,color:black;

    %% Apply classes
    class Istiod1,Istiod2,Istiod3 istio;
    class Frontend1,Cart1,Order1,Frontend2,Cart2,Order2,Payment3 app;
    class Lattice lattice;
```

**Decision**:
- **Intra-cluster (Frontend <-> Cart <-> Order)**: Use Istio
  - Reason: Frequent calls, complex routing, Circuit Breaker needed
- **Cross-cluster (Order -> Payment)**: Use VPC Lattice
  - Reason: Relatively simple calls, leverage AWS IAM authentication, simple management

#### Configuration Example

**Cluster 1/2: Frontend -> Cart (Istio)**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cart-service
  namespace: default
spec:
  hosts:
  - cart.default.svc.cluster.local
  http:
  - match:
    - headers:
        user-type:
          exact: premium
    route:
    - destination:
        host: cart.default.svc.cluster.local
        subset: v2
      weight: 100
  - route:
    - destination:
        host: cart.default.svc.cluster.local
        subset: v1
      weight: 100
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: cart-service
spec:
  host: cart.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 1024
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutiveErrors: 5
      interval: 10s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**Cluster 1/2: Order -> Payment (VPC Lattice)**

```yaml
# ServiceEntry for VPC Lattice
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: payment-service-lattice
  namespace: default
spec:
  hosts:
  - payment.lattice.svc.cluster.local
  location: MESH_EXTERNAL
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  resolution: DNS
  endpoints:
  - address: payment-service-abc123.vpc-lattice.amazonaws.com
---
# DestinationRule: VPC Lattice TLS
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: payment-service-lattice
spec:
  host: payment.lattice.svc.cluster.local
  trafficPolicy:
    tls:
      mode: SIMPLE  # VPC Lattice handles TLS
```

### Example 2: Disaster Recovery (DR) Scenario

#### Active-Standby with Route53 Failover

```yaml
# Cluster 1 (Active): Health Check Endpoint
apiVersion: v1
kind: Service
metadata:
  name: health-check
  namespace: istio-system
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    external-dns.alpha.kubernetes.io/hostname: api.example.com
    external-dns.alpha.kubernetes.io/set-identifier: "us-east-1-primary"
    external-dns.alpha.kubernetes.io/aws-health-check-id: "health-check-primary"
spec:
  type: LoadBalancer
  selector:
    app: health-check
  ports:
  - port: 80
    targetPort: 8080
---
# Cluster 2 (Standby): Health Check Endpoint
apiVersion: v1
kind: Service
metadata:
  name: health-check
  namespace: istio-system
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    external-dns.alpha.kubernetes.io/hostname: api.example.com
    external-dns.alpha.kubernetes.io/set-identifier: "us-west-2-standby"
    external-dns.alpha.kubernetes.io/aws-health-check-id: "health-check-standby"
spec:
  type: LoadBalancer
  selector:
    app: health-check
  ports:
  - port: 80
    targetPort: 8080
```

**Route53 Health Check and Failover Policy**:

```bash
# Create Primary Health Check
aws route53 create-health-check \
  --caller-reference "$(date +%s)" \
  --health-check-config \
    Type=HTTPS,ResourcePath=/healthz,FullyQualifiedDomainName=${PRIMARY_LB_DNS},Port=443

# Failover Routing Policy
aws route53 change-resource-record-sets \
  --hosted-zone-id ${ZONE_ID} \
  --change-batch file://failover-config.json
```

**failover-config.json**:

```json
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "A",
        "SetIdentifier": "Primary",
        "Failover": "PRIMARY",
        "AliasTarget": {
          "HostedZoneId": "${NLB_ZONE_ID}",
          "DNSName": "${PRIMARY_LB_DNS}",
          "EvaluateTargetHealth": true
        },
        "HealthCheckId": "${PRIMARY_HEALTH_CHECK_ID}"
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "A",
        "SetIdentifier": "Secondary",
        "Failover": "SECONDARY",
        "AliasTarget": {
          "HostedZoneId": "${NLB_ZONE_ID}",
          "DNSName": "${STANDBY_LB_DNS}",
          "EvaluateTargetHealth": true
        }
      }
    }
  ]
}
```

## Performance and Cost Comparison

### Performance Comparison

| Metric | Single-cluster | Multi-cluster Istio | Hybrid (Istio + Lattice) |
|--------|----------------|---------------------|--------------------------|
| **Intra-cluster latency** | ~2ms | ~2ms | ~2ms |
| **Cross-cluster latency** | N/A | +5-10ms (East-West GW) | +3-5ms (VPC Lattice) |
| **Throughput (RPS)** | 10,000 | 8,500 | 9,200 |
| **CPU overhead** | +10% | +15% | +12% |
| **Memory usage** | +50MB/pod | +70MB/pod | +55MB/pod |

### Cost Comparison (Monthly, 2 clusters)

| Item | Single-cluster | Multi-cluster Istio | Hybrid | VPC Lattice only |
|------|----------------|---------------------|--------|---------------|
| **Control Plane** | $50 | $100 (x2) | $100 (x2) | $0 |
| **East-West Gateway** | $0 | $100 (NLB x2) | $0 | $0 |
| **Cross-region transfer** | $0 | $200 (10TB) | $100 (5TB) | $100 (5TB) |
| **VPC Lattice** | $0 | $0 | $30 | $50 |
| **Operations personnel** | $10,000 | $15,000 | $12,000 | $8,000 |
| **Total estimated cost** | ~$10,050 | ~$15,400 | ~$12,230 | ~$8,150 |

**Cost saving tips**:
- Cross-region transfer costs can be reduced with VPC Peering
- VPC Lattice is throughput-based billing -> traffic optimization essential
- 90% resource overhead reduction with Ambient Mode

### ROI Analysis

**Multi-cluster Istio investment value**:
- Strongly recommended when downtime cost > $1,000/hour
- Recommended when global customer experience is important
- Excessive investment for small startups

**Hybrid approach sweet spot**:
- AWS-centric architecture
- Complex logic intra-cluster
- Simple connectivity cross-cluster

## Troubleshooting

```bash
# Verify cross-cluster connectivity
istioctl ps --context="${CTX_CLUSTER1}"
istioctl ps --context="${CTX_CLUSTER2}"

# Check Remote Secret
kubectl get secrets -n istio-system --context="${CTX_CLUSTER1}"

# Verify cross-cluster traffic
kubectl logs -n istio-system -l app=istiod --context="${CTX_CLUSTER1}"
```

## References

### Official Documentation

- [Istio Multi-cluster](https://istio.io/latest/docs/setup/install/multicluster/)
- [Multi-Primary](https://istio.io/latest/docs/setup/install/multicluster/multi-primary/)
- [Primary-Remote](https://istio.io/latest/docs/setup/install/multicluster/primary-remote/)
- [AWS VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [AWS Gateway API Controller](https://www.gateway-api-controller.eks.aws.dev/)

### Blogs and Case Studies

- [Tetrate - Multi-cluster Istio](https://tetrate.io/blog/multicluster-istio/)
- [Solo.io - Istio Multi-cluster Best Practices](https://www.solo.io/blog/istio-multicluster/)

### Related Documents

- [Ambient Mode](01-ambient-mode.md) - Resource optimization
- [mTLS](../security/01-mtls.md) - Secure cross-cluster communication
- [VPC Lattice](../../09-vpc-lattice.md) - AWS managed service networking

## Summary

Multi-cluster Service Mesh is powerful but increases complexity and cost. Decision guide:

| Choice | Suitable when | Key pros | Key cons |
|------|------------|-----------|----------|
| **Single-cluster** | Single region, small scale | Simple management, low cost | Single point of failure, no geographic distribution |
| **Multi-cluster Istio** | Global services, strong L7 needed | Full control, all Istio features | High complexity, high cost |
| **VPC Lattice** | AWS-centric, simple connectivity | AWS managed, low operational burden | Limited Istio features, AWS lock-in |
| **Hybrid** | AWS environment, complex internal + simple external | Balanced complexity and features | Need to understand two technology stacks |

**Recommended approach**:
1. Start with Single-cluster
2. When multi-region needed -> Consider Hybrid (Istio + VPC Lattice)
3. When strong L7 control essential -> Multi-cluster Istio
4. When operational simplification priority -> VPC Lattice only
