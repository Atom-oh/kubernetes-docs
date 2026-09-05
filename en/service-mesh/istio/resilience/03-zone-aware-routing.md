# Zone Aware Routing

Zone Aware Routing is a feature that optimizes traffic by recognizing Kubernetes Availability Zones. It reduces latency and cross-AZ data transfer costs by prioritizing communication within the same AZ.

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Basic Configuration](#basic-configuration)
4. [Advanced Configuration](#advanced-configuration)
5. [Configuration on AWS EKS](#configuration-on-aws-eks)
6. [Practical Examples](#practical-examples)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

## Overview

Zone Aware Routing provides the following benefits:

![A client pod in Availability Zone A sends 80% of its traffic to two service pods in its own zone and fails over 10% each to service pods in Availability Zone B and Availability Zone C.](../../../.gitbook/assets/en-service-mesh-istio-resilience-03-zone-aware-routing-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-03-zone-aware-routing-0.html)

### Benefits

1. **Reduced Latency**: Minimize network latency with same-AZ communication
2. **Cost Savings**: Reduce cross-AZ data transfer costs
   - AWS: $0.01-0.02 per GB for cross-AZ transfer
3. **Improved Availability**: Automatic failover to other AZs during failures
4. **Performance Optimization**: Optimized network bandwidth

## How It Works

### Locality Load Balancing Algorithm

![A request is routed by first checking for healthy pods in the same zone; if none, it checks the adjacent zone; and if none there either, it falls back to another region.](../../../.gitbook/assets/en-service-mesh-istio-resilience-03-zone-aware-routing-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-03-zone-aware-routing-1.html)

### Locality Hierarchy

Istio uses the following hierarchical Locality:

```
Region/Zone/SubZone

Example:
us-east-1/us-east-1a/*
us-east-1/us-east-1b/*
us-west-2/us-west-2a/*
```

**Priority**:
1. **Same Zone**: Same Region, Same Zone
2. **Same Region**: Same Region, Different Zone
3. **Different Region**: Different Region

### How It Works Without Pod AZ Labels

**Important**: Pods themselves do not need AZ labels. Istio reads **Node Topology labels** to automatically determine Pod Locality.

#### How It Works

![Istiod's service discovery reads the topology.kubernetes.io/zone label on each Node to determine Pod locality without needing zone labels on the pods themselves, then generates EDS and pushes that locality information to the Envoy proxy.](../../../.gitbook/assets/en-service-mesh-istio-resilience-03-zone-aware-routing-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-03-zone-aware-routing-2.html)

#### Step-by-Step Process

**Step 1: Istiod Collects Pod Information**

```bash
# Istiod queries Pod information via Kubernetes API
kubectl get pod <pod-name> -o json | jq '.spec.nodeName'
# Output: "ip-10-0-1-10.ec2.internal"
```

**Step 2: Query Topology Labels of Node Running the Pod**

```bash
# Query Node info using Pod's nodeName
kubectl get node ip-10-0-1-10.ec2.internal -o json | \
  jq '.metadata.labels."topology.kubernetes.io/zone"'
# Output: "us-east-1a"
```

**Step 3: Generate EDS (Endpoint Discovery Service)**

Istiod generates EDS with Pod IP and Locality information:

```json
{
  "cluster_name": "outbound|8080||myapp.default.svc.cluster.local",
  "endpoints": [
    {
      "locality": {
        "region": "us-east-1",
        "zone": "us-east-1a"
      },
      "lb_endpoints": [
        {
          "endpoint": {
            "address": {
              "socket_address": {
                "address": "10.0.1.10",
                "port_value": 8080
              }
            }
          }
        }
      ]
    },
    {
      "locality": {
        "region": "us-east-1",
        "zone": "us-east-1b"
      },
      "lb_endpoints": [
        {
          "endpoint": {
            "address": {
              "socket_address": {
                "address": "10.0.2.20",
                "port_value": 8080
              }
            }
          }
        }
      ]
    }
  ]
}
```

**Step 4: Envoy Performs Locality-Based Routing**

Envoy compares its own Locality with received EDS information for routing:

```bash
# Check Envoy's Locality (based on node it's running on)
kubectl exec <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/config_dump | \
  jq '.configs[] | select(.["@type"] | contains("BootstrapConfigDump")) | .bootstrap.node.locality'

# Output:
# {
#   "region": "us-east-1",
#   "zone": "us-east-1a"
# }
```

#### Verification Method

```bash
# 1. Check which Node the Pod is running on
kubectl get pod <pod-name> -o wide
# NAME        READY   STATUS    NODE
# myapp-abc   2/2     Running   ip-10-0-1-10.ec2.internal

# 2. Check the Node's Zone label
kubectl get node ip-10-0-1-10.ec2.internal \
  -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}'
# Output: us-east-1a

# 3. Check Endpoint Locality recognized by Envoy
istioctl proxy-config endpoints <pod-name> | grep myapp
# ENDPOINT          STATUS    OUTLIER CHECK     CLUSTER                    LOCALITY
# 10.0.1.10:8080    HEALTHY   OK                myapp.default              us-east-1/us-east-1a
# 10.0.2.20:8080    HEALTHY   OK                myapp.default              us-east-1/us-east-1b
```

#### Why Pod Labels Are Not Needed

**Traditional Approach (Unnecessary)**:
```yaml
# Not needed
apiVersion: v1
kind: Pod
metadata:
  labels:
    topology.kubernetes.io/zone: us-east-1a  # Unnecessary!
```

**Istio Approach (Automatic)**:
```yaml
# Only Node labels needed
apiVersion: v1
kind: Node
metadata:
  name: ip-10-0-1-10.ec2.internal
  labels:
    topology.kubernetes.io/zone: us-east-1a  # This is all you need!
    topology.kubernetes.io/region: us-east-1
```

**Reasons**:
1. **Pods Don't Move**: Pods don't move to other nodes after creation
2. **Node is the Source of Truth**: Pod's physical location is always determined by the Node
3. **Eliminate Redundancy**: No need to add labels to each Pod, just manage Node labels
4. **Automatic Sync**: Istiod always queries latest Node info from Kubernetes API

#### AWS EKS Automatic Setup

AWS EKS automatically adds Topology labels when creating nodes:

```bash
# Check EKS nodes
kubectl get nodes -L topology.kubernetes.io/zone,topology.kubernetes.io/region

# Example output:
# NAME                           ZONE         REGION
# ip-10-0-1-10.ec2.internal      us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal      us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal      us-east-1c   us-east-1
```

These labels are automatically obtained from the following sources:
- **EC2 Instance Metadata**: `http://169.254.169.254/latest/meta-data/placement/availability-zone`
- **AWS API**: Query EC2 info via Node's `spec.providerID`

## Basic Configuration

### 1. Set Topology Labels on Kubernetes Nodes

AWS EKS automatically adds the following labels:

```yaml
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```

**Verification**:
```bash
kubectl get nodes -L topology.kubernetes.io/zone -L topology.kubernetes.io/region

# Example output:
# NAME                          ZONE         REGION
# ip-10-0-1-10.ec2.internal     us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal     us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal     us-east-1c   us-east-1
```

### 2. Enable Zone Aware Routing in DestinationRule

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true  # Enable Zone Aware Routing
```

### 3. Configure Distribution Ratios

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        # Traffic originating from us-east-1a
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80   # 80% to same AZ
            "us-east-1/us-east-1b/*": 10   # 10% to adjacent AZ
            "us-east-1/us-east-1c/*": 10   # 10% to adjacent AZ

        # Traffic originating from us-east-1b
        - from: us-east-1/us-east-1b/*
          to:
            "us-east-1/us-east-1b/*": 80
            "us-east-1/us-east-1a/*": 10
            "us-east-1/us-east-1c/*": 10

        # Traffic originating from us-east-1c
        - from: us-east-1/us-east-1c/*
          to:
            "us-east-1/us-east-1c/*": 80
            "us-east-1/us-east-1a/*": 10
            "us-east-1/us-east-1b/*": 10
```

## Advanced Configuration

### Failover Configuration

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-failover
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failover:
        # When us-east-1a fails, go to us-east-1b
        - from: us-east-1/us-east-1a
          to: us-east-1/us-east-1b

        # When us-east-1b fails, go to us-east-1c
        - from: us-east-1/us-east-1b
          to: us-east-1/us-east-1c

        # When us-east-1c fails, go to us-east-1a
        - from: us-east-1/us-east-1c
          to: us-east-1/us-east-1a
```

### Use with Outlier Detection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-resilient
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    # Zone Aware Routing
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80
            "us-east-1/us-east-1b/*": 20

    # Outlier Detection
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50

      # Maintain minimum healthy instances per zone
      minHealthPercent: 50
```

### Multi-Region Configuration

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-multi-region
  namespace: default
spec:
  host: myapp.global
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true

        # Cross-region distribution
        distribute:
        # Traffic originating from us-east-1
        - from: us-east-1/*/*
          to:
            "us-east-1/*/*": 90      # 90% to same region
            "us-west-2/*/*": 10      # 10% to other region

        # Traffic originating from us-west-2
        - from: us-west-2/*/*
          to:
            "us-west-2/*/*": 90
            "us-east-1/*/*": 10

        # Region failover
        failover:
        - from: us-east-1
          to: us-west-2
        - from: us-west-2
          to: us-east-1
```

## Configuration on AWS EKS

### 1. Create Multi-AZ Node Groups

```yaml
# eksctl configuration
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-east-1

nodeGroups:
  - name: ng-zone-a
    instanceType: t3.medium
    desiredCapacity: 2
    availabilityZones:
      - us-east-1a
    labels:
      zone: us-east-1a

  - name: ng-zone-b
    instanceType: t3.medium
    desiredCapacity: 2
    availabilityZones:
      - us-east-1b
    labels:
      zone: us-east-1b

  - name: ng-zone-c
    instanceType: t3.medium
    desiredCapacity: 2
    availabilityZones:
      - us-east-1c
    labels:
      zone: us-east-1c
```

### 2. Distribute Pods Across Zones

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 9
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      # Even distribution across zones
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: myapp

      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
```

### 3. Enable Zone Aware Routing in Istio

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80
            "us-east-1/us-east-1b/*": 10
            "us-east-1/us-east-1c/*": 10
```

## Practical Examples

### Example 1: Microservice Chain

```yaml
# Frontend → Backend → Database

# Frontend (All AZs)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 6
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: frontend
---
# Backend (All AZs)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 9
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: backend
---
# Database (Single AZ - StatefulSet)
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: database
spec:
  replicas: 1
  template:
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
---
# Zone Aware Routing configuration
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend
spec:
  host: backend
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 90
            "us-east-1/us-east-1b/*": 5
            "us-east-1/us-east-1c/*": 5
```

### Example 2: Cost Optimization

```yaml
# Minimize cross-AZ costs
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cost-optimized
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        # Concentrate 95% in same AZ
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 95
            "us-east-1/us-east-1b/*": 3
            "us-east-1/us-east-1c/*": 2
```

### Example 3: High Availability

```yaml
# Availability first (allow cross-AZ)
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-availability
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        # Even distribution across all AZs
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 34
            "us-east-1/us-east-1b/*": 33
            "us-east-1/us-east-1c/*": 33

        # Failover configuration
        failover:
        - from: us-east-1/us-east-1a
          to: us-east-1/us-east-1b
```

## Monitoring

### Prometheus Metrics

```promql
# Traffic distribution across zones
sum(rate(istio_requests_total[5m])) by (source_zone, destination_zone)

# Same zone traffic ratio
(
  sum(rate(istio_requests_total{source_zone=destination_zone}[5m]))
  /
  sum(rate(istio_requests_total[5m]))
) * 100

# Error rate by zone
sum(rate(istio_requests_total{response_code=~"5.."}[5m])) by (destination_zone)
/
sum(rate(istio_requests_total[5m])) by (destination_zone)

# Locality information check
envoy_cluster_upstream_cx_active{envoy_cluster_name=~".*myapp.*"}
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Istio Zone Aware Routing",
    "panels": [
      {
        "title": "Traffic Distribution by Zone",
        "targets": [
          {
            "expr": "sum(rate(istio_requests_total[5m])) by (source_zone, destination_zone)",
            "legendFormat": "{{source_zone}} → {{destination_zone}}"
          }
        ]
      },
      {
        "title": "Same Zone Traffic Percentage",
        "targets": [
          {
            "expr": "(sum(rate(istio_requests_total{source_zone=destination_zone}[5m])) / sum(rate(istio_requests_total[5m]))) * 100",
            "legendFormat": "Same Zone %"
          }
        ]
      }
    ]
  }
}
```

### Real-time Verification

```bash
# Check Envoy endpoints
istioctl proxy-config endpoints <pod-name> -n <namespace>

# Check locality information
kubectl exec -n <namespace> <pod-name> -c istio-proxy -- \
  curl localhost:15000/clusters | grep myapp

# Example output:
# myapp.default.svc.cluster.local::10.0.1.10:8080::region::us-east-1::zone::us-east-1a::
# myapp.default.svc.cluster.local::10.0.2.20:8080::region::us-east-1::zone::us-east-1b::
```

## Troubleshooting

### Zone Aware Routing Not Working

```bash
# 1. Check node Topology labels
kubectl get nodes -L topology.kubernetes.io/zone -L topology.kubernetes.io/region

# If labels are missing, add manually:
kubectl label nodes <node-name> topology.kubernetes.io/zone=us-east-1a
kubectl label nodes <node-name> topology.kubernetes.io/region=us-east-1

# 2. Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>

# 3. Check Envoy configuration
istioctl proxy-config clusters <pod-name> -n <namespace> -o json | \
  jq '.[] | select(.name | contains("myapp")) | .loadAssignment.endpoints[].locality'

# 4. Check pod zone distribution
kubectl get pods -n <namespace> -o wide \
  -L topology.kubernetes.io/zone
```

### High Ratio of Traffic Going to Other Zones

```bash
# Root cause analysis:
# 1. Unbalanced pod count per zone
kubectl get pods -n <namespace> -o wide | \
  awk '{print $7}' | sort | uniq -c

# 2. Some pods are unhealthy
kubectl get pods -n <namespace> -o wide | \
  grep -v "Running"

# 3. Pods excluded by Outlier Detection
kubectl exec -n <namespace> <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep outlier_detection
```

### Topology Labels Missing on EKS

```bash
# Resolve by installing AWS Node Termination Handler
kubectl apply -f https://github.com/aws/aws-node-termination-handler/releases/download/v1.19.0/all-resources.yaml

# Or add labels manually
for node in $(kubectl get nodes -o name); do
  ZONE=$(kubectl get $node -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}')
  if [ -z "$ZONE" ]; then
    # Get AZ from AWS EC2 metadata
    ZONE=$(kubectl get $node -o jsonpath='{.spec.providerID}' | \
      xargs -I {} aws ec2 describe-instances --instance-ids {} --query 'Reservations[0].Instances[0].Placement.AvailabilityZone' --output text)
    kubectl label $node topology.kubernetes.io/zone=$ZONE
  fi
done
```

## Best Practices

### 1. Even Pod Distribution Across Zones

```yaml
# Use topologySpreadConstraints
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule
```

### 2. Cost Optimization

```yaml
# Prioritize same zone (80% or more)
distribute:
- from: us-east-1/us-east-1a/*
  to:
    "us-east-1/us-east-1a/*": 80
    "us-east-1/us-east-1b/*": 10
    "us-east-1/us-east-1c/*": 10
```

### 3. Ensure High Availability

```yaml
# Failover configuration is essential
failover:
- from: us-east-1/us-east-1a
  to: us-east-1/us-east-1b
```

### 4. Single AZ Recommended for StatefulSet

```yaml
# Deploy StatefulSet (Database, etc.) in single AZ
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - us-east-1a
```

## References

- [Istio Locality Load Balancing](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/)
- [Kubernetes Topology Aware Hints](https://kubernetes.io/docs/concepts/services-networking/topology-aware-hints/)
- [AWS EKS Multi-AZ](https://docs.aws.amazon.com/eks/latest/userguide/disaster-recovery-resiliency.html)
