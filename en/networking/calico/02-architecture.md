# Part 2: Calico Architecture Deep Dive

> **Supported Versions**: Calico v3.29+ / Kubernetes 1.28+
> **Last Updated**: February 22, 2025

## Overview

This section provides an in-depth exploration of Calico's architecture. Understanding how each component works and interacts is essential for effective deployment, troubleshooting, and optimization of Calico in production environments.

## Full Architecture Diagram

![Calico Architecture](../../assets/calico_architecture.png)

```mermaid
flowchart TD
    subgraph KubernetesAPI["Kubernetes Control Plane"]
        K8sAPI[Kubernetes API Server]
        ETCD[(etcd)]
    end

    subgraph CalicoControl["Calico Control Plane"]
        APIServer[Calico API Server]
        KubeControllers[kube-controllers]
        Typha1[Typha Pod 1]
        Typha2[Typha Pod 2]
        Typha3[Typha Pod 3]
    end

    subgraph Node1["Worker Node 1"]
        Felix1[Felix]
        BIRD1[BIRD]
        confd1[confd]
        IPTables1[iptables/eBPF]
        Routes1[Routing Table]
    end

    subgraph Node2["Worker Node 2"]
        Felix2[Felix]
        BIRD2[BIRD]
        confd2[confd]
        IPTables2[iptables/eBPF]
        Routes2[Routing Table]
    end

    subgraph Node3["Worker Node 3"]
        Felix3[Felix]
        BIRD3[BIRD]
        confd3[confd]
        IPTables3[iptables/eBPF]
        Routes3[Routing Table]
    end

    %% Control plane connections
    K8sAPI <--> ETCD
    K8sAPI <--> APIServer
    K8sAPI --> KubeControllers
    KubeControllers --> K8sAPI

    %% Typha connections
    K8sAPI --> Typha1
    K8sAPI --> Typha2
    K8sAPI --> Typha3

    %% Node 1 connections
    Typha1 --> Felix1
    Felix1 --> IPTables1
    Felix1 --> Routes1
    Felix1 --> confd1
    confd1 --> BIRD1

    %% Node 2 connections
    Typha2 --> Felix2
    Felix2 --> IPTables2
    Felix2 --> Routes2
    Felix2 --> confd2
    confd2 --> BIRD2

    %% Node 3 connections
    Typha3 --> Felix3
    Felix3 --> IPTables3
    Felix3 --> Routes3
    Felix3 --> confd3
    confd3 --> BIRD3

    %% BGP mesh
    BIRD1 <-.->|BGP| BIRD2
    BIRD2 <-.->|BGP| BIRD3
    BIRD1 <-.->|BGP| BIRD3

    classDef k8s fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef calico fill:#FA8320,stroke:#333,stroke-width:1px,color:white
    classDef node fill:#00C7B7,stroke:#333,stroke-width:1px,color:white

    class K8sAPI,ETCD k8s
    class APIServer,KubeControllers,Typha1,Typha2,Typha3 calico
    class Felix1,Felix2,Felix3,BIRD1,BIRD2,BIRD3,confd1,confd2,confd3,IPTables1,IPTables2,IPTables3,Routes1,Routes2,Routes3 node
```

## Felix: The Calico Agent

Felix is the primary Calico agent that runs on every node in the cluster. It is responsible for programming routes and ACLs (Access Control Lists) on the host to provide desired connectivity and network policy enforcement.

### Felix Responsibilities

```mermaid
flowchart LR
    subgraph Felix["Felix Agent"]
        A[Datastore Watcher]
        B[Route Manager]
        C[ACL Manager]
        D[Interface Manager]
        E[IPAM Manager]
    end

    subgraph Outputs["System Configuration"]
        F[iptables Rules]
        G[IP Sets]
        H[Routing Table]
        I[Network Interfaces]
    end

    A --> B
    A --> C
    A --> D
    A --> E

    B --> H
    C --> F
    C --> G
    D --> I

    style Felix fill:#FA8320,stroke:#333,color:white
```

### Core Functions

1. **Route Programming**: Manages routes for pod CIDR blocks
2. **ACL Enforcement**: Programs iptables/nftables/eBPF rules for network policies
3. **Interface Management**: Configures workload endpoint interfaces
4. **Health Reporting**: Reports node and endpoint health to the datastore
5. **IPAM Coordination**: Manages IP address allocation for local workloads

### Felix Data Plane Options

Felix supports multiple data plane backends:

| Data Plane | Description | Best For |
|------------|-------------|----------|
| **iptables** | Traditional Linux firewall | Compatibility, mature deployments |
| **nftables** | Modern Linux firewall | Newer kernels, better performance |
| **eBPF** | In-kernel programmable | Maximum performance, kube-proxy replacement |

### FelixConfiguration Resource

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Logging configuration
  logSeverityScreen: Info
  logSeverityFile: Warning
  logFilePath: /var/log/calico/felix.log

  # Data plane selection
  bpfEnabled: false                    # Set true for eBPF data plane
  bpfDataIfacePattern: ^((en|wl|eth).*|bond[0-9]+)$
  bpfConnectTimeLoadBalancingEnabled: true
  bpfExternalServiceMode: Tunnel

  # iptables configuration
  iptablesBackend: Auto               # Auto, Legacy, NFT
  iptablesRefreshInterval: 90s
  iptablesPostWriteCheckIntervalSecs: 1
  iptablesLockFilePath: /run/xtables.lock
  iptablesLockTimeoutSecs: 0
  iptablesLockProbeIntervalMillis: 50

  # Performance tuning
  ipipMTU: 1440
  vxlanMTU: 1410
  wireguardMTU: 1420

  # Health and metrics
  healthEnabled: true
  healthPort: 9099
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
  prometheusGoMetricsEnabled: true
  prometheusProcessMetricsEnabled: true

  # Policy configuration
  defaultEndpointToHostAction: Drop
  failsafeInboundHostPorts:
    - protocol: TCP
      port: 22
    - protocol: UDP
      port: 68
  failsafeOutboundHostPorts:
    - protocol: UDP
      port: 53
    - protocol: UDP
      port: 67

  # Interface configuration
  interfacePrefix: cali
  chainInsertMode: Insert

  # Reporting
  reportingIntervalSecs: 30
  reportingTTLSecs: 90
```

### Felix iptables Rule Structure

Felix organizes iptables rules into chains for efficient processing:

```
                         ┌─────────────────────────────────────────┐
                         │              FORWARD Chain              │
                         └─────────────────┬───────────────────────┘
                                           │
                         ┌─────────────────▼───────────────────────┐
                         │          cali-FORWARD (Calico)          │
                         └─────────────────┬───────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
┌─────────────▼─────────────┐ ┌────────────▼────────────┐ ┌─────────────▼─────────────┐
│   cali-from-wl-dispatch   │ │   cali-to-wl-dispatch   │ │    cali-from-host-ep     │
│  (from workload traffic)  │ │  (to workload traffic)  │ │   (from host endpoints)   │
└─────────────┬─────────────┘ └────────────┬────────────┘ └─────────────┬─────────────┘
              │                            │                            │
┌─────────────▼─────────────┐ ┌────────────▼────────────┐ ┌─────────────▼─────────────┐
│    cali-fw-caliXXXXXX     │ │    cali-tw-caliXXXXXX   │ │    Per-endpoint policy    │
│    (per-endpoint rules)   │ │   (per-endpoint rules)  │ │          chains           │
└───────────────────────────┘ └─────────────────────────┘ └───────────────────────────┘
```

### Felix Data Flow

```mermaid
sequenceDiagram
    participant DS as Datastore (via Typha)
    participant F as Felix
    participant IPT as iptables/eBPF
    participant RT as Routing Table
    participant IF as Network Interface

    DS->>F: Policy Update
    F->>F: Calculate required rules
    F->>IPT: Program iptables rules
    F->>IPT: Update IP sets

    DS->>F: Workload Endpoint Update
    F->>IF: Configure veth interface
    F->>RT: Add/update routes
    F->>IPT: Program endpoint rules

    DS->>F: IPPool Update
    F->>RT: Update IPIP/VXLAN routes
    F->>IF: Configure tunnel interface
```

## BIRD: BGP Routing Daemon

BIRD (BIRD Internet Routing Daemon) is the BGP daemon used by Calico for distributing routes between nodes.

### BIRD in Calico Architecture

```mermaid
flowchart TD
    subgraph Cluster["Kubernetes Cluster"]
        subgraph Node1["Node 1"]
            BIRD1[BIRD]
            RT1[Routes: 192.168.1.0/26]
        end

        subgraph Node2["Node 2"]
            BIRD2[BIRD]
            RT2[Routes: 192.168.2.0/26]
        end

        subgraph Node3["Node 3"]
            BIRD3[BIRD]
            RT3[Routes: 192.168.3.0/26]
        end
    end

    subgraph External["External Network"]
        TOR[ToR Switch]
        Router[Core Router]
    end

    BIRD1 <-->|iBGP| BIRD2
    BIRD2 <-->|iBGP| BIRD3
    BIRD1 <-->|iBGP| BIRD3

    BIRD1 <-->|eBGP| TOR
    BIRD2 <-->|eBGP| TOR
    BIRD3 <-->|eBGP| TOR

    TOR <--> Router

    classDef bird fill:#FA8320,stroke:#333,color:white
    classDef external fill:#326CE5,stroke:#333,color:white

    class BIRD1,BIRD2,BIRD3 bird
    class TOR,Router external
```

### BGP Session Types

| Session Type | Use Case | Configuration |
|--------------|----------|---------------|
| **Node-to-Node Mesh** | Default for small clusters | Automatic, full mesh |
| **Route Reflector** | Large clusters (100+ nodes) | Dedicated RR nodes |
| **External Peering** | On-premises integration | Manual BGP peer config |

### BGP Configuration Examples

#### Node-to-Node Mesh (Default)

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
```

#### Route Reflector Configuration

```yaml
# Disable node-to-node mesh
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
---
# Configure route reflector nodes
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: node-rr-1
  labels:
    route-reflector: "true"
spec:
  bgp:
    routeReflectorClusterID: 224.0.0.1
---
# Configure BGP peer to route reflector
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-rr
spec:
  nodeSelector: "!has(route-reflector)"
  peerSelector: route-reflector == "true"
```

#### External BGP Peering

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tor-switch-peer
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  nodeSelector: rack == 'rack-1'
  password:
    secretKeyRef:
      name: bgp-passwords
      key: tor-password
  sourceAddress: UseNodeIP
  keepOriginalNextHop: false
```

### Route Propagation Process

```mermaid
sequenceDiagram
    participant Pod as New Pod
    participant Felix as Felix
    participant BIRD as BIRD (Local)
    participant Peer as BIRD (Peer Nodes)

    Pod->>Felix: Pod Created
    Felix->>Felix: Allocate IP from block
    Felix->>Felix: Program local route
    Felix->>BIRD: Route available

    BIRD->>BIRD: Add to RIB
    BIRD->>Peer: BGP UPDATE message
    Peer->>Peer: Process UPDATE
    Peer->>Peer: Install in RIB
    Peer->>Felix: Route update
    Felix->>Felix: Program route
```

### BIRD Status Commands

```bash
# Access BIRD CLI on a Calico node
kubectl exec -n calico-system calico-node-xxxxx -c calico-node -- birdcl

# Show BGP protocol status
birdcl> show protocols
name     proto    table    state  since       info
kernel1  Kernel   master   up     2024-01-01
device1  Device   master   up     2024-01-01
direct1  Direct   master   up     2024-01-01
Mesh_10_0_1_10  BGP  master  up   2024-01-01  Established
Mesh_10_0_1_11  BGP  master  up   2024-01-01  Established

# Show BGP routes
birdcl> show route protocol Mesh_10_0_1_10
192.168.1.0/26     via 10.0.1.10 on eth0 [Mesh_10_0_1_10 2024-01-01] * (100/0) [i]
192.168.1.64/26    via 10.0.1.10 on eth0 [Mesh_10_0_1_10 2024-01-01] * (100/0) [i]

# Show route details
birdcl> show route 192.168.1.0/26 all
```

## confd: Configuration Management

confd is a lightweight configuration management tool that watches the Calico datastore and generates BIRD configuration files.

### confd Workflow

```mermaid
flowchart LR
    subgraph Datastore["Calico Datastore"]
        BGPConfig[BGPConfiguration]
        BGPPeers[BGPPeer]
        Nodes[Node Resources]
    end

    subgraph confd["confd Process"]
        Watcher[Datastore Watcher]
        Templates[Config Templates]
        Generator[Config Generator]
    end

    subgraph BIRD["BIRD Daemon"]
        Config[bird.cfg]
        Daemon[BIRD Process]
    end

    BGPConfig --> Watcher
    BGPPeers --> Watcher
    Nodes --> Watcher

    Watcher --> Generator
    Templates --> Generator
    Generator --> Config
    Config --> Daemon

    classDef store fill:#326CE5,stroke:#333,color:white
    classDef process fill:#FA8320,stroke:#333,color:white
    classDef bird fill:#00C7B7,stroke:#333,color:white

    class BGPConfig,BGPPeers,Nodes store
    class Watcher,Templates,Generator process
    class Config,Daemon bird
```

### confd Template Processing

confd uses Go templates to generate BIRD configuration:

```
# Template: /etc/calico/confd/templates/bird.cfg.template
# Output: /etc/calico/confd/config/bird.cfg

router id {{.NodeIP}};

protocol kernel {
    learn;
    persist;
    scan time 2;
    import all;
    export {{if .ExportKernel}}all{{else}}none{{end}};
}

protocol device {
    scan time 2;
}

{{range .BGPPeers}}
protocol bgp {{.Name}} {
    local as {{$.LocalAS}};
    neighbor {{.PeerIP}} as {{.PeerAS}};
    import all;
    export {{if .ExportFilter}}filter {{.ExportFilter}}{{else}}all{{end}};
    {{if .Password}}password "{{.Password}}";{{end}}
    graceful restart;
}
{{end}}
```

## Typha: Scaling Component

Typha is a fan-out proxy that sits between the Kubernetes API server and Felix agents. It reduces load on the API server by caching and distributing datastore updates.

### Why Typha?

```mermaid
flowchart TD
    subgraph Without["Without Typha (Small Cluster)"]
        API1[Kubernetes API]
        F1[Felix 1]
        F2[Felix 2]
        F3[Felix 3]

        API1 -->|Watch| F1
        API1 -->|Watch| F2
        API1 -->|Watch| F3
    end

    subgraph With["With Typha (Large Cluster)"]
        API2[Kubernetes API]
        T1[Typha 1]
        T2[Typha 2]
        FF1[Felix 1-100]
        FF2[Felix 101-200]

        API2 -->|Watch| T1
        API2 -->|Watch| T2
        T1 -->|Fan-out| FF1
        T2 -->|Fan-out| FF2
    end

    style Without fill:#ffcccc,stroke:#333
    style With fill:#ccffcc,stroke:#333
```

### Typha Scaling Calculation

The recommended number of Typha replicas depends on cluster size:

```
Typha Replicas = max(3, ceil(Nodes / 200))

Examples:
- 50 nodes:   3 Typha replicas (minimum)
- 200 nodes:  3 Typha replicas
- 500 nodes:  3 Typha replicas
- 1000 nodes: 5 Typha replicas
- 2000 nodes: 10 Typha replicas
```

### Typha Deployment Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      k8s-app: calico-typha
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  template:
    metadata:
      labels:
        k8s-app: calico-typha
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      tolerations:
      - key: CriticalAddonsOnly
        operator: Exists
      priorityClassName: system-cluster-critical
      serviceAccountName: calico-typha
      containers:
      - name: calico-typha
        image: calico/typha:v3.29.0
        ports:
        - containerPort: 5473
          name: calico-typha
          protocol: TCP
        env:
        - name: TYPHA_LOGSEVERITYSCREEN
          value: "info"
        - name: TYPHA_LOGFILEPATH
          value: "none"
        - name: TYPHA_LOGSEVERITYSYS
          value: "none"
        - name: TYPHA_CONNECTIONREBALANCINGMODE
          value: "kubernetes"
        - name: TYPHA_DATASTORETYPE
          value: "kubernetes"
        - name: TYPHA_HEALTHENABLED
          value: "true"
        - name: TYPHA_PROMETHEUSMETRICSENABLED
          value: "true"
        - name: TYPHA_PROMETHEUSMETRICSPORT
          value: "9093"
        livenessProbe:
          httpGet:
            path: /liveness
            port: 9098
          periodSeconds: 30
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /readiness
            port: 9098
          periodSeconds: 10
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 1000m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  ports:
  - port: 5473
    protocol: TCP
    targetPort: calico-typha
    name: calico-typha
  selector:
    k8s-app: calico-typha
```

### Typha Fan-out Architecture

```mermaid
flowchart TD
    subgraph APIServer["Kubernetes API Server"]
        Watch1[Watch Stream 1]
        Watch2[Watch Stream 2]
    end

    subgraph Typha["Typha Layer"]
        T1[Typha Pod 1]
        T2[Typha Pod 2]
        Cache1[(Local Cache)]
        Cache2[(Local Cache)]
    end

    subgraph Nodes["Worker Nodes"]
        subgraph Group1["Node Group 1"]
            F1[Felix]
            F2[Felix]
            F3[Felix]
            Fn1[Felix...]
        end
        subgraph Group2["Node Group 2"]
            F4[Felix]
            F5[Felix]
            F6[Felix]
            Fn2[Felix...]
        end
    end

    Watch1 --> T1
    Watch2 --> T2
    T1 --> Cache1
    T2 --> Cache2

    Cache1 --> F1
    Cache1 --> F2
    Cache1 --> F3
    Cache1 --> Fn1

    Cache2 --> F4
    Cache2 --> F5
    Cache2 --> F6
    Cache2 --> Fn2

    classDef api fill:#326CE5,stroke:#333,color:white
    classDef typha fill:#FA8320,stroke:#333,color:white
    classDef felix fill:#00C7B7,stroke:#333,color:white

    class Watch1,Watch2 api
    class T1,T2,Cache1,Cache2 typha
    class F1,F2,F3,F4,F5,F6,Fn1,Fn2 felix
```

## kube-controllers: Kubernetes Integration

The calico-kube-controllers pod runs a set of controllers that sync Kubernetes resources with Calico datastore.

### Controllers Overview

| Controller | Purpose |
|------------|---------|
| **Node Controller** | Syncs Kubernetes nodes with Calico node resources |
| **Policy Controller** | Syncs Kubernetes NetworkPolicy with Calico policy |
| **Namespace Controller** | Syncs namespace labels for profile management |
| **ServiceAccount Controller** | Syncs service account labels for RBAC |
| **WorkloadEndpoint Controller** | Cleans up stale workload endpoints |

### Controller Reconciliation Loop

```mermaid
sequenceDiagram
    participant K8s as Kubernetes API
    participant KC as kube-controllers
    participant DS as Calico Datastore

    loop Every reconciliation interval
        KC->>K8s: List Kubernetes resources
        KC->>DS: List Calico resources
        KC->>KC: Compare and calculate diff

        alt Resources out of sync
            KC->>DS: Create/Update/Delete resources
            KC->>KC: Log reconciliation action
        else Resources in sync
            KC->>KC: No action needed
        end
    end
```

### kube-controllers Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: calico-kube-controllers-config
  namespace: calico-system
data:
  config: |
    {
      "logSeverityScreen": "info",
      "healthEnabled": true,
      "prometheusPort": 9094,
      "controllers": {
        "node": {
          "hostEndpoint": {
            "autoCreate": "Disabled"
          },
          "syncLabels": "Enabled",
          "leakGracePeriod": "15m"
        },
        "policy": {
          "reconcilerPeriod": "5m"
        },
        "workloadEndpoint": {
          "reconcilerPeriod": "5m"
        },
        "namespace": {
          "reconcilerPeriod": "5m"
        },
        "serviceAccount": {
          "reconcilerPeriod": "5m"
        }
      }
    }
```

## Datastore Options

Calico supports two datastore backends for storing its configuration and state.

### Kubernetes API Datastore (Recommended)

```mermaid
flowchart LR
    subgraph Components["Calico Components"]
        Felix[Felix]
        Typha[Typha]
        KC[kube-controllers]
    end

    subgraph K8s["Kubernetes"]
        API[API Server]
        ETCD[(etcd)]
    end

    Felix <--> Typha
    Typha <--> API
    KC <--> API
    API <--> ETCD

    classDef calico fill:#FA8320,stroke:#333,color:white
    classDef k8s fill:#326CE5,stroke:#333,color:white

    class Felix,Typha,KC calico
    class API,ETCD k8s
```

**Advantages:**
- No separate etcd cluster to manage
- Uses Kubernetes RBAC for access control
- Simpler operational model
- Works with any Kubernetes distribution

### etcd Datastore (Legacy)

```mermaid
flowchart LR
    subgraph Components["Calico Components"]
        Felix[Felix]
        Typha[Typha]
        KC[kube-controllers]
    end

    subgraph Datastores["Datastores"]
        K8sAPI[K8s API Server]
        CalicoETCD[(Calico etcd)]
    end

    Felix <--> Typha
    Typha <--> CalicoETCD
    KC <--> K8sAPI
    KC <--> CalicoETCD

    classDef calico fill:#FA8320,stroke:#333,color:white
    classDef store fill:#326CE5,stroke:#333,color:white

    class Felix,Typha,KC calico
    class K8sAPI,CalicoETCD store
```

**Advantages:**
- Decoupled from Kubernetes API server
- Can be used for non-Kubernetes workloads (VMs, bare metal)
- Historical option for very large clusters

### Datastore Comparison

| Feature | Kubernetes API | etcd |
|---------|----------------|------|
| **Operational Complexity** | Lower | Higher |
| **Scalability** | Good (with Typha) | Excellent |
| **Non-K8s Workloads** | Limited | Full support |
| **Backup/Restore** | Via K8s | Separate tooling |
| **Access Control** | K8s RBAC | etcd auth |
| **Recommendation** | Default choice | Special cases only |

## Component Interaction Sequence

```mermaid
sequenceDiagram
    participant User
    participant K8sAPI as Kubernetes API
    participant KC as kube-controllers
    participant Typha
    participant Felix
    participant BIRD
    participant DataPlane as iptables/eBPF

    User->>K8sAPI: Create NetworkPolicy
    K8sAPI->>KC: Policy event
    KC->>K8sAPI: Create CalicoNetworkPolicy

    K8sAPI->>Typha: Policy update
    Typha->>Felix: Distribute policy
    Felix->>Felix: Calculate rules
    Felix->>DataPlane: Program rules

    User->>K8sAPI: Create Pod
    K8sAPI->>KC: Pod event
    KC->>K8sAPI: Create WorkloadEndpoint

    K8sAPI->>Typha: Endpoint update
    Typha->>Felix: Distribute endpoint
    Felix->>DataPlane: Program endpoint rules
    Felix->>BIRD: Update routes
    BIRD->>BIRD: Distribute via BGP
```

## Packet Flow Analysis

### Ingress Packet Flow (Pod-to-Pod, Same Node)

```mermaid
flowchart TD
    subgraph SameNode["Single Node"]
        PodA[Pod A - 192.168.1.10]
        VethA[veth: caliXXXXXX]
        IPT[iptables/eBPF]
        VethB[veth: caliYYYYYY]
        PodB[Pod B - 192.168.1.11]
    end

    PodA -->|1. Send packet| VethA
    VethA -->|2. Enter host namespace| IPT
    IPT -->|3. Policy check + forward| VethB
    VethB -->|4. Deliver| PodB

    classDef pod fill:#326CE5,stroke:#333,color:white
    classDef infra fill:#FA8320,stroke:#333,color:white

    class PodA,PodB pod
    class VethA,VethB,IPT infra
```

### Egress Packet Flow (Pod-to-Pod, Different Nodes with IPIP)

```mermaid
flowchart TD
    subgraph Node1["Node 1 - 10.0.1.10"]
        PodA[Pod A - 192.168.1.10]
        VethA[veth: caliXXXXXX]
        IPT1[iptables/eBPF]
        Tunl1[tunl0 - IPIP]
        Eth1[eth0]
    end

    subgraph Network["Physical Network"]
        Switch[Network Switch]
    end

    subgraph Node2["Node 2 - 10.0.1.11"]
        Eth2[eth0]
        Tunl2[tunl0 - IPIP]
        IPT2[iptables/eBPF]
        VethB[veth: caliYYYYYY]
        PodB[Pod B - 192.168.2.10]
    end

    PodA -->|1. Original packet| VethA
    VethA -->|2. Route lookup| IPT1
    IPT1 -->|3. Policy check| Tunl1
    Tunl1 -->|4. IPIP encap| Eth1
    Eth1 -->|5. Outer: 10.0.1.10->10.0.1.11| Switch
    Switch -->|6. Forward| Eth2
    Eth2 -->|7. Receive| Tunl2
    Tunl2 -->|8. IPIP decap| IPT2
    IPT2 -->|9. Policy check| VethB
    VethB -->|10. Deliver| PodB

    classDef pod fill:#326CE5,stroke:#333,color:white
    classDef infra fill:#FA8320,stroke:#333,color:white
    classDef network fill:#00C7B7,stroke:#333,color:white

    class PodA,PodB pod
    class VethA,VethB,IPT1,IPT2,Tunl1,Tunl2,Eth1,Eth2 infra
    class Switch network
```

### Packet Structure Comparison

```
Original Pod-to-Pod Packet:
┌─────────────────────────────────────────────────────────────┐
│ Ethernet │   IP Header    │   TCP/UDP   │     Payload      │
│  Header  │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 192.168.2.10 │             │                  │
└─────────────────────────────────────────────────────────────┘

IPIP Encapsulated Packet:
┌───────────────────────────────────────────────────────────────────────────────┐
│ Ethernet │   Outer IP     │   Inner IP     │   TCP/UDP   │     Payload      │
│  Header  │ Src: 10.0.1.10 │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 10.0.1.11 │ Dst: 192.168.2.10 │             │                  │
│          │ Proto: 4 (IPIP)│                │             │                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Summary

Calico's architecture is designed for scalability, performance, and operational simplicity:

1. **Felix**: The workhorse agent on every node, programming routes and ACLs
2. **BIRD**: Distributes routes via BGP, enabling native routing integration
3. **confd**: Bridges the datastore to BIRD configuration
4. **Typha**: Scales the system by reducing API server load
5. **kube-controllers**: Keeps Kubernetes and Calico in sync
6. **Datastore**: Kubernetes API (recommended) or etcd for configuration storage

Understanding these components and their interactions is essential for:
- Troubleshooting connectivity issues
- Optimizing performance at scale
- Planning capacity and architecture
- Integrating with existing network infrastructure

[Previous: Part 1 - Introduction to Calico](01-introduction.md)

[Next: Part 3 - Networking Modes](03-networking-modes.md)

[Return to Calico Overview](README.md)

## Quiz

To test what you've learned in this chapter, try the [Architecture Quiz](../../quizzes/networking/calico/02-architecture-quiz.md).
