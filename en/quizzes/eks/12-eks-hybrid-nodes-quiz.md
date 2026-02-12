# Amazon EKS Hybrid Nodes Quiz

This quiz tests your understanding of Amazon EKS Hybrid Nodes architecture, nodeadm tool, Harbor registry integration, GPU integration, Dynamic Resource Allocation (DRA), network configuration, and cost optimization.

## Quiz Overview
- EKS Hybrid Nodes Architecture and Components
- Node Bootstrapping with nodeadm
- Harbor Private Registry Integration
- GPU and Accelerator Integration (MIG, Time-Slicing)
- Dynamic Resource Allocation (DRA)
- Hybrid Network Configuration
- Cost Optimization Strategies

## Multiple Choice Questions

### 1. Which is NOT a suitable use case for EKS Hybrid Nodes?

A. Utilizing GPU servers in on-premises data centers
B. Data locality requirements for regulatory compliance
C. Running purely cloud-native workloads
D. Latency-sensitive edge workloads

<details>
<summary>View Answer</summary>

**Answer: C. Running purely cloud-native workloads**

**Explanation:**
Purely cloud-native workloads are more efficiently run on regular EKS node groups or Fargate. Hybrid Nodes are used when there are special requirements (on-premises, edge, regulatory, etc.).

**Suitable Use Cases for EKS Hybrid Nodes:**
- Utilizing on-premises GPU/specialized hardware
- Data sovereignty/regulatory compliance requirements
- Latency-sensitive edge computing
- Cloud migration transition period
- Protecting existing infrastructure investments

```bash
# Hybrid Node Registration Example
nodeadm init \
  --cluster-name my-cluster \
  --region us-west-2 \
  --hybrid-node
```

</details>

### 2. What is the primary role of nodeadm?

A. Creating EKS clusters
B. Installing and bootstrapping node components like kubelet and containerd
C. Making Pod scheduling decisions
D. Managing cluster network policies

<details>
<summary>View Answer</summary>

**Answer: B. Installing and bootstrapping node components like kubelet and containerd**

**Explanation:**
nodeadm is the official tool for EKS node bootstrapping. It installs and configures necessary components including kubelet, containerd, and aws-iam-authenticator.

```bash
# Install nodeadm
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# Initialize node with nodeadm
sudo nodeadm init \
  --config-source file://nodeadm-config.yaml

# nodeadm Configuration File Example (nodeadm-config.yaml)
---
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: us-west-2
    apiServerEndpoint: https://xxxxx.gr7.us-west-2.eks.amazonaws.com
    certificateAuthority: LS0tLS1CRUdJTi...
  kubelet:
    config:
      maxPods: 110
    flags:
      - "--node-labels=node.kubernetes.io/lifecycle=hybrid"
```

**nodeadm Features:**
- Kubernetes component installation (kubelet, containerd)
- AWS IAM Authenticator configuration
- kubelet certificate bootstrapping
- Node label and taint settings

</details>

### 3. What Secret type is used when integrating Harbor private registry with Kubernetes?

A. Opaque
B. kubernetes.io/dockerconfigjson
C. kubernetes.io/tls
D. kubernetes.io/service-account-token

<details>
<summary>View Answer</summary>

**Answer: B. kubernetes.io/dockerconfigjson**

**Explanation:**
Docker/Container registry authentication information is stored as a `kubernetes.io/dockerconfigjson` type Secret. This Secret is referenced by imagePullSecrets to pull private images.

```bash
# Create Harbor Registry Secret
kubectl create secret docker-registry harbor-secret \
  --docker-server=harbor.example.com \
  --docker-username=admin \
  --docker-password=Harbor12345 \
  --docker-email=admin@example.com

# Or create directly with YAML
apiVersion: v1
kind: Secret
metadata:
  name: harbor-secret
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: eyJhdXRocyI6eyJoYXJib3IuZXhhbXBsZS5jb20iOnsidXNlcm5hbWUiOiJhZG1pbiIsInBhc3N3b3JkIjoiSGFyYm9yMTIzNDUiLCJhdXRoIjoiWVdSdGFXNDZTR0Z5WW05eU1USXpORFU9In19fQ==
```

```yaml
# Use imagePullSecrets in Pod
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: app
    image: harbor.example.com/project/my-app:v1
  imagePullSecrets:
  - name: harbor-secret
```

</details>

### 4. What is the key characteristic of NVIDIA GPU Multi-Instance GPU (MIG) technology?

A. Combines multiple GPUs into one
B. Splits a single GPU into multiple physically isolated instances
C. Only shares GPU memory
D. Software-level time-slicing

<details>
<summary>View Answer</summary>

**Answer: B. Splits a single GPU into multiple physically isolated instances**

**Explanation:**
MIG (Multi-Instance GPU) partitions GPUs like NVIDIA A100 and H100 into up to 7 physically isolated instances. Each instance has independent memory, cache, and compute resources.

**MIG vs Time-Slicing Comparison:**

| Feature | MIG | Time-Slicing |
|-----|-----|--------------|
| Isolation Level | Physical (complete isolation) | Time-based (software) |
| Memory Isolation | Complete isolation | Shared |
| Supported GPUs | A100, H100 | All NVIDIA GPUs |
| QoS Guarantee | Yes | No |

```yaml
# MIG Configuration ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: nvidia-mig-config
  namespace: gpu-operator
data:
  config.yaml: |
    version: v1
    mig-configs:
      all-1g.5gb:
        - devices: all
          mig-enabled: true
          mig-devices:
            "1g.5gb": 7
      all-3g.20gb:
        - devices: all
          mig-enabled: true
          mig-devices:
            "3g.20gb": 2
```

```yaml
# MIG Resource Request
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/mig-1g.5gb: 1
```

</details>

### 5. What is the main advantage of Dynamic Resource Allocation (DRA)?

A. Only supports static resource allocation
B. Supports all devices without vendor-specific plugins
C. Flexible request/allocation mechanism for custom resources
D. Only manages CPU and memory

<details>
<summary>View Answer</summary>

**Answer: C. Flexible request/allocation mechanism for custom resources**

**Explanation:**
DRA (Dynamic Resource Allocation), introduced in Kubernetes 1.26, provides a more flexible request and allocation mechanism for custom resources like GPUs, FPGAs, and network devices.

**Core DRA Components:**
- **ResourceClass**: Defines resource types provided by drivers
- **ResourceClaim**: Request for resources
- **ResourceClaimTemplate**: Reusable claim template

```yaml
# ResourceClass Definition
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClass
metadata:
  name: nvidia-gpu
driverName: gpu.nvidia.com

---
# ResourceClaimTemplate
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClaimTemplate
metadata:
  name: gpu-claim-template
spec:
  spec:
    resourceClassName: nvidia-gpu
    parametersRef:
      apiGroup: gpu.nvidia.com
      kind: GpuClaimParameters
      name: single-gpu

---
# Using DRA in Pod
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      claims:
      - name: gpu
  resourceClaims:
  - name: gpu
    source:
      resourceClaimTemplateName: gpu-claim-template
```

**DRA vs Device Plugin Comparison:**
- DRA: More flexible resource attribute specification
- DRA: Supports resource sharing between Pods
- DRA: Dynamic resource allocation at runtime

</details>

### 6. What is the recommended method for network connectivity between on-premises and cloud for EKS Hybrid Nodes?

A. Public internet connection
B. AWS Direct Connect or Site-to-Site VPN
C. SSH tunneling
D. HTTP proxy

<details>
<summary>View Answer</summary>

**Answer: B. AWS Direct Connect or Site-to-Site VPN**

**Explanation:**
EKS Hybrid Nodes require stable and secure network connectivity to the EKS control plane. AWS Direct Connect (dedicated line) or Site-to-Site VPN is recommended.

**Network Requirements:**
- EKS API server endpoint access (443/TCP)
- AWS service endpoint access (ECR, S3, STS, etc.)
- Stable low-latency connection

```bash
# Check Site-to-Site VPN configuration
aws ec2 describe-vpn-connections \
  --filters Name=state,Values=available

# Monitor VPN connection status
aws cloudwatch get-metric-statistics \
  --namespace AWS/VPN \
  --metric-name TunnelState \
  --dimensions Name=VpnId,Value=vpn-xxxxxx
```

```yaml
# Hybrid Node nodeadm Network Configuration
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: us-west-2
    apiServerEndpoint: https://xxxxx.gr7.us-west-2.eks.amazonaws.com
  hybrid:
    ssm: false  # Use VPN/Direct Connect instead of SSM
  containerd:
    config: |
      [plugins."io.containerd.grpc.v1.cri".registry.mirrors."harbor.onprem.local"]
        endpoint = ["https://harbor.onprem.local"]
```

</details>

### 7. Which is NOT a valid replication policy type in Harbor?

A. Push-based
B. Pull-based
C. Event-based
D. Sync-based

<details>
<summary>View Answer</summary>

**Answer: D. Sync-based**

**Explanation:**
Harbor supports Push-based, Pull-based, and Event-based replication policies. "Sync-based" is not an official Harbor term.

**Harbor Replication Policy Types:**
1. **Push-based**: Push from source Harbor to target registry
2. **Pull-based**: Target Harbor pulls images from source
3. **Event-based**: Automatic replication on image push events

```yaml
# Harbor Replication Policy API Example
POST /api/v2.0/replication/policies
{
  "name": "ecr-replication",
  "src_registry": {
    "id": 1
  },
  "dest_registry": {
    "id": 2
  },
  "dest_namespace": "production",
  "trigger": {
    "type": "event_based"
  },
  "filters": [
    {
      "type": "name",
      "value": "myapp/**"
    },
    {
      "type": "tag",
      "value": "v*"
    }
  ],
  "enabled": true,
  "deletion": false
}
```

</details>

### 8. What is the expected behavior when oversubscription occurs in GPU Time-Slicing?

A. Complete GPU task failure
B. Performance degradation due to context switching
C. Automatic GPU addition
D. Automatic memory expansion

<details>
<summary>View Answer</summary>

**Answer: B. Performance degradation due to context switching**

**Explanation:**
Time-Slicing allows multiple workloads to share a single GPU on a time-division basis. When oversubscription occurs, frequent context switching causes performance degradation.

```yaml
# GPU Time-Slicing Configuration (NVIDIA Device Plugin)
apiVersion: v1
kind: ConfigMap
metadata:
  name: device-plugin-config
  namespace: nvidia-device-plugin
data:
  config.yaml: |
    version: v1
    sharing:
      timeSlicing:
        renameByDefault: false
        failRequestsGreaterThanOne: false
        resources:
        - name: nvidia.com/gpu
          replicas: 4  # Split 1 GPU into 4
```

```yaml
# Time-Slicing GPU Request
apiVersion: v1
kind: Pod
metadata:
  name: gpu-timeslice-pod
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/gpu: 1  # Actually 1/4 of a GPU
```

**Time-Slicing Considerations:**
- Memory is shared, so OOM can occur
- Suitable for inference workloads
- MIG or dedicated GPUs recommended for training
- Proper replicas count setting is important

</details>

### 9. What authentication method is used for IAM in EKS Hybrid Nodes?

A. Static tokens
B. x509 certificates only
C. IAM Roles Anywhere or IAM user credentials
D. LDAP authentication

<details>
<summary>View Answer</summary>

**Answer: C. IAM Roles Anywhere or IAM user credentials**

**Explanation:**
EKS Hybrid Nodes require AWS IAM authentication from on-premises. IAM Roles Anywhere allows using IAM roles from on-premises servers.

```bash
# Create IAM Roles Anywhere Trust Anchor
aws rolesanywhere create-trust-anchor \
  --name hybrid-nodes-anchor \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$CERT_DATA}"

# Create IAM Roles Anywhere Profile
aws rolesanywhere create-profile \
  --name hybrid-node-profile \
  --role-arns arn:aws:iam::123456789012:role/HybridNodeRole \
  --duration-seconds 3600

# Get credentials (on node)
aws_signing_helper credential-process \
  --certificate /path/to/cert.pem \
  --private-key /path/to/key.pem \
  --trust-anchor-arn arn:aws:rolesanywhere:region:account:trust-anchor/id \
  --profile-arn arn:aws:rolesanywhere:region:account:profile/id \
  --role-arn arn:aws:iam::account:role/HybridNodeRole
```

```yaml
# Using IAM Roles Anywhere in nodeadm Configuration
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
  iam:
    mode: rolesAnywhere
    rolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:us-west-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:us-west-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/HybridNodeRole
      certificatePath: /etc/pki/hybrid/cert.pem
      privateKeyPath: /etc/pki/hybrid/key.pem
```

</details>

### 10. Which is NOT a suitable cost optimization strategy for Hybrid Nodes environments?

A. Use on-premises GPUs for inference workloads
B. Handle burst traffic on cloud nodes
C. Migrate all workloads to Hybrid Nodes
D. Run data-locality-required workloads on-premises

<details>
<summary>View Answer</summary>

**Answer: C. Migrate all workloads to Hybrid Nodes**

**Explanation:**
Migrating all workloads to Hybrid Nodes increases complexity and reduces cost efficiency. Choose the appropriate location based on workload characteristics.

**Cost Optimization Strategies:**

| Workload Type | Recommended Location | Reason |
|-------------|----------|-----|
| Continuous GPU Inference | On-premises | Utilize existing hardware |
| Burst Traffic | Cloud | Elastic scaling |
| Data-Intensive | Near data | Reduce transfer costs |
| Stateless | Cloud | Easier management |
| Regulated | On-premises | Compliance |

```yaml
# Per-Workload Node Selection (NodeSelector)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  template:
    spec:
      nodeSelector:
        node.kubernetes.io/instance-type: hybrid  # On-premises GPU
      containers:
      - name: inference
        resources:
          limits:
            nvidia.com/gpu: 1
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: burst-handler
spec:
  template:
    spec:
      nodeSelector:
        eks.amazonaws.com/capacityType: SPOT  # Cloud Spot
```

</details>

## Short Answer Questions

### 1. What are the 3 required cluster information pieces when initializing a Hybrid Node with nodeadm?

<details>
<summary>View Answer</summary>

**Answer:**
1. **Cluster name (name)**
2. **API server endpoint (apiServerEndpoint)**
3. **Certificate Authority (CA) certificate (certificateAuthority)**

```yaml
# Required items in nodeadm Configuration File
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster                    # Required 1
    region: us-west-2
    apiServerEndpoint: https://xxxxx.eks.amazonaws.com  # Required 2
    certificateAuthority: LS0tLS1CRUdJTi...             # Required 3
```

```bash
# Get required information from EKS
aws eks describe-cluster --name my-cluster --query "cluster.{name:name,endpoint:endpoint,ca:certificateAuthority.data}" --output json
```

</details>

### 2. What does "1g.5gb" mean in NVIDIA GPU MIG configuration?

<details>
<summary>View Answer</summary>

**Answer:**
- **1g**: 1 GPU Instance (1 compute slice)
- **5gb**: 5GB GPU memory

MIG instance name format: `<compute-slices>g.<memory-size>gb`

**A100 MIG Profile Examples:**
- `1g.5gb`: 1 compute slice, 5GB memory (max 7)
- `2g.10gb`: 2 compute slices, 10GB memory (max 3)
- `3g.20gb`: 3 compute slices, 20GB memory (max 2)
- `4g.40gb`: 4 compute slices, 40GB memory (max 1)
- `7g.40gb`: 7 compute slices, 40GB memory (full GPU)

```bash
# Check MIG instances
nvidia-smi mig -lgi
```

</details>

### 3. What is the default vulnerability scanner provided in Harbor for image scanning?

<details>
<summary>View Answer</summary>

**Answer:** Trivy

**Explanation:**
Since Harbor 2.0, Trivy is included as the default vulnerability scanner. Clair can also be optionally used.

```bash
# Harbor Vulnerability Scan API
POST /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/scan

# Get Scan Results
GET /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/additions/vulnerabilities
```

**Harbor Scan Policy Settings:**
```yaml
# Enable auto-scan at project level
# Harbor UI: Projects > Configuration > Vulnerability scanning
# - Automatically scan images on push: enabled
# - Prevent vulnerable images from running: enabled (CVE severity threshold)
```

</details>

### 4. What condition must be met for a ResourceClaim status to become "Bound" in DRA (Dynamic Resource Allocation)?

<details>
<summary>View Answer</summary>

**Answer:** The driver must allocate actual resources for the ResourceClaim, and a Pod using that claim must be scheduled.

**ResourceClaim Status Flow:**
1. **Pending**: Claim created, not yet allocated
2. **Allocated**: Driver completed resource allocation
3. **Bound**: Bound to Pod and in use

```yaml
# Check ResourceClaim Status
kubectl get resourceclaim gpu-claim -o yaml

# Expected output
status:
  allocation:
    resourceHandles:
    - driverName: gpu.nvidia.com
      data: '{"gpu":"GPU-abc123"}'
  reservedFor:
  - name: gpu-workload
    uid: xxx-xxx-xxx
```

</details>

### 5. List 3 VPC endpoints needed for AWS service access in EKS Hybrid Nodes.

<details>
<summary>View Answer</summary>

**Answer:**
1. **ec2.region.amazonaws.com** (EC2 API)
2. **ecr.api.region.amazonaws.com** (ECR API)
3. **sts.region.amazonaws.com** (STS - IAM authentication)

**Additional Recommended Endpoints:**
- `ecr.dkr.region.amazonaws.com` (ECR Docker Registry)
- `s3.region.amazonaws.com` (S3 - ECR image storage)
- `logs.region.amazonaws.com` (CloudWatch Logs)
- `ssm.region.amazonaws.com` (Systems Manager)

```bash
# Create VPC Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.us-west-2.sts \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxx \
  --security-group-ids sg-xxx
```

</details>

## Hands-on Exercises

### 1. Configure Kubernetes Secret and ServiceAccount to pull images from a Harbor private registry.
- Harbor URL: harbor.company.local
- Project: production
- User: k8s-puller (password: PullSecret123)

<details>
<summary>View Answer</summary>

```bash
# 1. Create Docker Registry Secret
kubectl create secret docker-registry harbor-creds \
  --docker-server=harbor.company.local \
  --docker-username=k8s-puller \
  --docker-password=PullSecret123 \
  --namespace=default
```

```yaml
# 2. Link imagePullSecrets to ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: harbor-puller
  namespace: default
imagePullSecrets:
- name: harbor-creds

---
# 3. Use in Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: harbor-puller
      containers:
      - name: app
        image: harbor.company.local/production/myapp:v1.0
        ports:
        - containerPort: 8080
```

**Verification Commands:**
```bash
# Check Secret
kubectl get secret harbor-creds -o yaml

# Check ServiceAccount
kubectl get sa harbor-puller -o yaml

# Check Pod image pulling
kubectl describe pod -l app=myapp | grep -A 5 "Events:"
```

</details>

### 2. Write a ConfigMap to configure NVIDIA GPU Time-Slicing to split 1 GPU into 4 virtual GPUs.

<details>
<summary>View Answer</summary>

```yaml
# 1. Time-Slicing ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: device-plugin-config
  namespace: nvidia-device-plugin
data:
  config.yaml: |
    version: v1
    flags:
      migStrategy: none
    sharing:
      timeSlicing:
        renameByDefault: false
        failRequestsGreaterThanOne: false
        resources:
        - name: nvidia.com/gpu
          replicas: 4

---
# 2. Update NVIDIA Device Plugin DaemonSet (reference ConfigMap)
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-device-plugin-daemonset
  namespace: nvidia-device-plugin
spec:
  selector:
    matchLabels:
      name: nvidia-device-plugin-ds
  template:
    metadata:
      labels:
        name: nvidia-device-plugin-ds
    spec:
      containers:
      - name: nvidia-device-plugin-ctr
        image: nvcr.io/nvidia/k8s-device-plugin:v0.14.3
        env:
        - name: CONFIG_FILE
          value: /etc/kubernetes/nvidia-device-plugin/config.yaml
        volumeMounts:
        - name: device-plugin-config
          mountPath: /etc/kubernetes/nvidia-device-plugin
      volumes:
      - name: device-plugin-config
        configMap:
          name: device-plugin-config
```

```yaml
# 3. Pod Using Time-Slicing GPU
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime-ubuntu22.04
    command: ["nvidia-smi", "-L"]
    resources:
      limits:
        nvidia.com/gpu: 1  # Logical 1 GPU (physical 1/4)
```

**Verification Commands:**
```bash
# Check GPU resources
kubectl describe node | grep nvidia.com/gpu

# Expected output: nvidia.com/gpu: 4 (1 physical GPU * 4 replicas)

# Verify Time-slicing applied
kubectl get pods -n nvidia-device-plugin
kubectl logs -n nvidia-device-plugin -l name=nvidia-device-plugin-ds
```

</details>

### 3. Write a nodeadm configuration file for an EKS Hybrid Node.
- Cluster name: hybrid-cluster
- Region: us-west-2
- Node labels: `location=onprem`, `gpu=nvidia-a100`
- Configure containerd to pull images from on-premises Harbor (harbor.onprem.local)

<details>
<summary>View Answer</summary>

```yaml
# nodeadm-config.yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: hybrid-cluster
    region: us-west-2
    apiServerEndpoint: https://XXXXX.gr7.us-west-2.eks.amazonaws.com
    certificateAuthority: |
      LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUM...
      # Base64 encoded CA certificate

  kubelet:
    config:
      maxPods: 110
      clusterDNS:
        - 10.100.0.10
    flags:
      - "--node-labels=location=onprem,gpu=nvidia-a100"
      - "--register-with-taints=dedicated=gpu:NoSchedule"

  containerd:
    config: |
      version = 2

      [plugins."io.containerd.grpc.v1.cri".registry]
        [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
          [plugins."io.containerd.grpc.v1.cri".registry.mirrors."harbor.onprem.local"]
            endpoint = ["https://harbor.onprem.local"]

        [plugins."io.containerd.grpc.v1.cri".registry.configs]
          [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.onprem.local".tls]
            ca_file = "/etc/containerd/certs.d/harbor.onprem.local/ca.crt"
          [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.onprem.local".auth]
            username = "k8s-node"
            password = "NodePullSecret123"

  hybrid:
    # IAM Roles Anywhere Configuration (on-premises IAM authentication)
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:us-west-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:us-west-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
      certificatePath: /etc/pki/hybrid/node-cert.pem
      privateKeyPath: /etc/pki/hybrid/node-key.pem
```

**Execute nodeadm:**
```bash
# Place CA certificate
sudo mkdir -p /etc/containerd/certs.d/harbor.onprem.local/
sudo cp harbor-ca.crt /etc/containerd/certs.d/harbor.onprem.local/ca.crt

# Initialize with nodeadm
sudo nodeadm init --config-source file://nodeadm-config.yaml

# Check node status
kubectl get nodes -l location=onprem
```

</details>

## Advanced Questions

### 1. A manufacturing company wants to run real-time quality inspection AI models on edge servers in factories. Design an MLOps pipeline utilizing EKS Hybrid Nodes, GPU (MIG), and Harbor registry. Include model update, rollback, and monitoring strategies.

<details>
<summary>View Answer</summary>

**Manufacturing Quality Inspection AI MLOps Pipeline Design**

**1. Architecture Overview:**

```
[Cloud (AWS)]                    [Edge (Factory)]
+---------------------+          +---------------------+
|  EKS Control Plane  |<--VPN-->|  Hybrid Nodes       |
|  Harbor (Primary)   |          |  Harbor (Mirror)    |
|  MLflow             |          |  GPU Servers (A100) |
|  Model Registry     |          |  Inference Service  |
+---------------------+          +---------------------+
```

**2. Harbor Registry Configuration (Redundancy):**

```yaml
# Harbor Replication Policy (Cloud -> Edge)
apiVersion: v1
kind: ConfigMap
metadata:
  name: harbor-replication-config
data:
  policy.json: |
    {
      "name": "edge-model-sync",
      "src_registry": {"id": 0},
      "dest_registry": {
        "url": "https://harbor.factory.local",
        "credential_type": "basic",
        "access_key": "replicator"
      },
      "trigger": {"type": "event_based"},
      "filters": [
        {"type": "name", "value": "qc-models/**"},
        {"type": "tag", "value": "prod-*"}
      ],
      "enabled": true
    }
```

**3. GPU MIG Configuration (Quality Inspection Optimized):**

```yaml
# A100 MIG Configuration - For Quality Inspection Models
apiVersion: v1
kind: ConfigMap
metadata:
  name: mig-config
  namespace: nvidia-gpu-operator
data:
  config.yaml: |
    version: v1
    mig-configs:
      qc-inference:
        - devices: all
          mig-enabled: true
          mig-devices:
            "2g.10gb": 3  # 3 medium models running simultaneously
      qc-mixed:
        - devices: [0]
          mig-enabled: true
          mig-devices:
            "3g.20gb": 1  # Large model
            "1g.5gb": 2   # Small models
```

**4. Inference Service Deployment (Canary):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qc-inference-stable
  namespace: qc-system
  labels:
    app: qc-inference
    version: stable
spec:
  replicas: 2
  selector:
    matchLabels:
      app: qc-inference
      version: stable
  template:
    metadata:
      labels:
        app: qc-inference
        version: stable
    spec:
      nodeSelector:
        location: onprem
        gpu: nvidia-a100
      containers:
      - name: inference
        image: harbor.factory.local/qc-models/defect-detector:prod-v2.1
        resources:
          limits:
            nvidia.com/mig-2g.10gb: 1
        ports:
        - containerPort: 8080
        env:
        - name: MODEL_NAME
          value: "defect_detector_v2.1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080

---
# Canary Deployment (New Model)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qc-inference-canary
  namespace: qc-system
  labels:
    app: qc-inference
    version: canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: qc-inference
      version: canary
  template:
    spec:
      containers:
      - name: inference
        image: harbor.factory.local/qc-models/defect-detector:prod-v2.2-rc1
```

**5. Traffic Distribution (Istio):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: qc-inference-vs
spec:
  hosts:
  - qc-inference
  http:
  - match:
    - headers:
        x-canary:
          exact: "true"
    route:
    - destination:
        host: qc-inference
        subset: canary
  - route:
    - destination:
        host: qc-inference
        subset: stable
      weight: 95
    - destination:
        host: qc-inference
        subset: canary
      weight: 5
```

**6. Automatic Rollback Policy:**

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: qc-inference-canary
  namespace: qc-system
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: qc-inference-canary
  service:
    port: 8080
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: accuracy
      templateRef:
        name: model-accuracy
      thresholdRange:
        min: 0.95  # Rollback if below 95%
    - name: latency-p99
      threshold: 200  # Rollback if exceeds 200ms
    - name: error-rate
      threshold: 1    # Rollback if exceeds 1%
```

**7. Monitoring and Alerting:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: qc-model-alerts
spec:
  groups:
  - name: qc-inference.rules
    rules:
    - alert: ModelAccuracyDegraded
      expr: |
        qc_model_accuracy{model="defect_detector"} < 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Quality inspection model accuracy degraded"
        runbook: "https://wiki/runbooks/qc-model-accuracy"

    - alert: InferenceLatencyHigh
      expr: |
        histogram_quantile(0.99, rate(qc_inference_duration_seconds_bucket[5m])) > 0.2
      for: 3m
      labels:
        severity: warning

    - alert: GPUMemoryPressure
      expr: |
        nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes > 0.9
      for: 5m
      labels:
        severity: warning
```

</details>

### 2. A global AI startup wants to manage GPU resources distributed across multiple regions (Korea, Japan, US) with a single EKS cluster. Develop a multi-region GPU resource management strategy considering Hybrid Nodes, DRA, and cost optimization.

<details>
<summary>View Answer</summary>

**Global GPU Resource Management Strategy**

**1. Architecture Overview:**

```
                    +-------------------------+
                    |  EKS Control Plane      |
                    |  (us-west-2)            |
                    +-----------+-------------+
                                |
        +-----------------------+------------------------+
        |                       |                        |
        v                       v                        v
+---------------+     +---------------+     +---------------+
| Korea (Seoul) |     | Japan (Tokyo) |     | US (Oregon)   |
| On-prem GPU   |     | EC2 GPU       |     | On-prem GPU   |
| A100 x 8      |     | p4d.24xl x 4  |     | H100 x 16     |
| Direct Connect|     | Native Node   |     | VPN           |
+---------------+     +---------------+     +---------------+
```

**2. GPU Resource Abstraction via DRA:**

```yaml
# GPU ResourceClass Definitions (per region)
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClass
metadata:
  name: gpu-korea-a100
driverName: gpu.nvidia.com
parametersRef:
  apiGroup: gpu.nvidia.com
  kind: GpuClassParameters
  name: a100-params

---
apiVersion: gpu.nvidia.com/v1
kind: GpuClassParameters
metadata:
  name: a100-params
spec:
  sharing:
    strategy: TimeSlicing
    timeSlicingConfig:
      replicas: 4
  nodeSelector:
    topology.kubernetes.io/region: ap-northeast-2
    gpu.nvidia.com/gpu-model: A100

---
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClass
metadata:
  name: gpu-japan-p4d
driverName: gpu.nvidia.com

---
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClass
metadata:
  name: gpu-us-h100
driverName: gpu.nvidia.com
```

**3. Smart GPU Scheduler:**

```yaml
# GPU Preference Definition by Workload Type
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpu-scheduler-config
data:
  policy.yaml: |
    # Inference Workloads: Cost optimization, latency consideration
    inference:
      preferredRegions:
        - ap-northeast-2  # Korea users first
        - ap-northeast-1  # Japan backup
      gpuPreference:
        - gpu-korea-a100  # On-premises first (cost)
        - gpu-japan-p4d   # Cloud backup

    # Training Workloads: Performance optimization
    training:
      preferredRegions:
        - us-west-2       # Where H100 is
      gpuPreference:
        - gpu-us-h100     # Latest GPU
        - gpu-korea-a100

    # Batch Workloads: Cost optimization
    batch:
      preferredRegions:
        - any             # Anywhere available
      gpuPreference:
        - gpu-korea-a100  # On-premises first
        - gpu-us-h100
        - gpu-japan-p4d   # Spot instances
```

**4. ResourceClaim Templates per Workload:**

```yaml
# For Inference Workloads
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClaimTemplate
metadata:
  name: inference-gpu-claim
spec:
  spec:
    resourceClassName: gpu-korea-a100
    parametersRef:
      apiGroup: gpu.nvidia.com
      kind: GpuClaimParameters
      name: inference-params

---
apiVersion: gpu.nvidia.com/v1
kind: GpuClaimParameters
metadata:
  name: inference-params
spec:
  count: 1
  requirements:
    memory: "5Gi"  # MIG 1g.5gb level
    computeCapability: "8.0"

---
# For Training Workloads
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClaimTemplate
metadata:
  name: training-gpu-claim
spec:
  spec:
    resourceClassName: gpu-us-h100
    parametersRef:
      apiGroup: gpu.nvidia.com
      kind: GpuClaimParameters
      name: training-params

---
apiVersion: gpu.nvidia.com/v1
kind: GpuClaimParameters
metadata:
  name: training-params
spec:
  count: 4
  requirements:
    memory: "80Gi"
    interconnect: "nvlink"  # High-speed GPU communication
```

**5. Cost Optimization Policies:**

```yaml
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: gpu-spot-provisioner
spec:
  requirements:
  - key: karpenter.sh/capacity-type
    operator: In
    values: ["spot", "on-demand"]
  - key: node.kubernetes.io/instance-type
    operator: In
    values: ["p4d.24xlarge", "p3.16xlarge"]
  - key: topology.kubernetes.io/zone
    operator: In
    values: ["ap-northeast-1a", "ap-northeast-1c"]

  # Spot instances preferred
  weight: 100

  limits:
    resources:
      nvidia.com/gpu: 32

  # Cost optimization: Scale down quickly when unused
  ttlSecondsAfterEmpty: 300
  ttlSecondsUntilExpired: 2592000  # 30 days

---
# Cost-based Scheduling Priority
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: cost-optimized-batch
value: 100
preemptionPolicy: Never
description: "Low priority batch jobs using spot/on-prem GPUs"

---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: latency-critical-inference
value: 1000
preemptionPolicy: PreemptLowerPriority
description: "High priority inference with preemption rights"
```

**6. Global Load Balancing:**

```yaml
# Istio-based Region-Aware Routing
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: global-inference-routing
spec:
  hosts:
  - inference.global.ai-startup.com
  http:
  - match:
    - headers:
        x-client-region:
          exact: "APAC"
    route:
    - destination:
        host: inference.ap-northeast-2.svc.cluster.local
      weight: 80
    - destination:
        host: inference.ap-northeast-1.svc.cluster.local
      weight: 20
  - match:
    - headers:
        x-client-region:
          exact: "US"
    route:
    - destination:
        host: inference.us-west-2.svc.cluster.local
  # Default: Latency-based routing
  - route:
    - destination:
        host: inference.ap-northeast-2.svc.cluster.local
```

**7. Cost Monitoring and Optimization:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gpu-cost-optimization
spec:
  groups:
  - name: gpu.cost.rules
    rules:
    # Detect GPU idle time
    - alert: GPUUnderutilized
      expr: |
        avg_over_time(DCGM_FI_DEV_GPU_UTIL[1h]) < 20
      for: 2h
      labels:
        severity: info
      annotations:
        summary: "GPU utilization below 20% - cost optimization review needed"

    # On-premises vs Cloud cost comparison
    - record: gpu:cost:hourly
      expr: |
        # Cloud GPU hourly cost
        sum(kube_pod_container_resource_requests{resource="nvidia.com/gpu"}
          * on(node) group_left()
          kube_node_labels{label_node_kubernetes_io_instance_type=~"p4d.*"}) * 32.77
        +
        # On-premises calculated as fixed cost (depreciation)
        sum(kube_pod_container_resource_requests{resource="nvidia.com/gpu"}
          * on(node) group_left()
          kube_node_labels{label_location="onprem"}) * 5.00
```

**Expected Cost Savings:**
- On-premises GPU utilization: 60% savings vs cloud
- Spot instances: 70% savings vs on-demand
- Region-based routing: 40% savings on data transfer
- Idle GPU optimization: Additional 20% savings

</details>
