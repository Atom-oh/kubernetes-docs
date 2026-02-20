# EKS Hybrid Nodes Air-Gap Environment Setup Quiz

> **Related Document**: [Air-Gap Environment Setup](../../eks-hybrid-nodes/03-airgap-setup.md)

## Multiple Choice Questions

### 1. Which is NOT a valid replication policy type in Harbor?

A. Push-based
B. Pull-based
C. Event-based
D. Sync-based

<details>
<summary>Show Answer</summary>

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
  "trigger": {
    "type": "event_based"
  },
  "filters": [
    {"type": "name", "value": "myapp/**"},
    {"type": "tag", "value": "v*"}
  ]
}
```

</details>

### 2. What Secret type is used when integrating Harbor private registry with Kubernetes?

A. Opaque
B. kubernetes.io/dockerconfigjson
C. kubernetes.io/tls
D. kubernetes.io/service-account-token

<details>
<summary>Show Answer</summary>

**Answer: B. kubernetes.io/dockerconfigjson**

**Explanation:**
Docker/Container registry authentication information is stored as a `kubernetes.io/dockerconfigjson` type Secret.

```bash
# Create Harbor Registry Secret
kubectl create secret docker-registry harbor-secret \
  --docker-server=harbor.example.com \
  --docker-username=admin \
  --docker-password=Harbor12345 \
  --docker-email=admin@example.com
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

### 3. What is the default vulnerability scanner provided in Harbor for image scanning?

A. Clair
B. Trivy
C. Anchore
D. Snyk

<details>
<summary>Show Answer</summary>

**Answer: B. Trivy**

**Explanation:**
Since Harbor 2.0, Trivy is included as the default vulnerability scanner. Clair can also be optionally used.

```bash
# Harbor Vulnerability Scan API
POST /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/scan

# Get Scan Results
GET /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/additions/vulnerabilities
```

**Harbor Scan Policy Settings:**
- Projects > Configuration > Vulnerability scanning
- Automatically scan images on push: enabled
- Prevent vulnerable images from running: enabled (CVE severity threshold)

</details>

### 4. What is the most accurate definition of an air-gap environment?

A. An environment with slow internet connection
B. An environment physically isolated from external networks
C. An environment connected only via VPN
D. An environment with firewalls installed

<details>
<summary>Show Answer</summary>

**Answer: B. An environment physically isolated from external networks**

**Explanation:**
An air-gap environment is physically separated from the internet or external networks for security reasons. It is commonly used in:

- Military/defense facilities
- Financial institution core systems
- Nuclear power plant control systems
- Healthcare institution sensitive data processing systems

```
Air-gap environment characteristics:
+------------------+     Physical isolation     +------------------+
|   External       | <---- No connection ---->  |   Air-gap        |
|   Network        |                            |   Environment    |
| (Internet, Cloud)|                            | (On-premises DC) |
+------------------+                            +------------------+
```

In air-gap environments, all software and images must be transferred offline.

</details>

### 5. What is the correct sequence for mirroring container images to Harbor in an air-gap environment?

A. Install Harbor -> Tag image -> Push image -> Pull image
B. Pull image -> Save image -> Offline transfer -> Load and push to Harbor
C. Install Harbor -> Direct ECR connection -> Auto sync
D. Build image -> Direct deploy -> Skip Harbor

<details>
<summary>Show Answer</summary>

**Answer: B. Pull image -> Save image -> Offline transfer -> Load and push to Harbor**

**Explanation:**
In air-gap environments, there is no internet connection, so images must be manually transferred:

```bash
# 1. Pull image on internet-connected system
docker pull nginx:1.25

# 2. Save image to tar file
docker save nginx:1.25 -o nginx-1.25.tar

# 3. Offline transfer (USB, external hard drive, etc.)
# Physically move media to air-gap environment

# 4. Load image in air-gap environment
docker load -i nginx-1.25.tar

# 5. Tag and push to Harbor
docker tag nginx:1.25 harbor.airgap.local/library/nginx:1.25
docker push harbor.airgap.local/library/nginx:1.25
```

For managing large numbers of images, tools like `skopeo` or `crane` are more efficient.

</details>

### 6. What is the correct method for offline installation of nodeadm in an air-gap environment?

A. Download directly from GitHub using curl
B. apt-get install nodeadm
C. Pre-download binaries and dependencies for offline installation
D. pip install nodeadm

<details>
<summary>Show Answer</summary>

**Answer: C. Pre-download binaries and dependencies for offline installation**

**Explanation:**
In air-gap environments, internet access is not possible, so all necessary files must be prepared in advance:

```bash
# Prepare on internet-connected system
# 1. Download nodeadm binary
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64

# 2. Download required dependency packages (e.g., Ubuntu)
apt-get download containerd.io kubelet kubectl

# 3. Transfer all files to air-gap environment

# Install in air-gap environment
# 4. Install nodeadm
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# 5. Install dependency packages
sudo dpkg -i containerd.io_*.deb kubelet_*.deb kubectl_*.deb

# 6. Run nodeadm
sudo nodeadm init --config-source file://nodeadm-config.yaml
```

</details>

### 7. Which is NOT an environment variable that needs to be set when configuring a proxy server in an air-gap environment?

A. HTTP_PROXY
B. HTTPS_PROXY
C. NO_PROXY
D. FTP_PROXY

<details>
<summary>Show Answer</summary>

**Answer: D. FTP_PROXY**

**Explanation:**
The proxy environment variables commonly used in container and Kubernetes environments are HTTP_PROXY, HTTPS_PROXY, and NO_PROXY. FTP_PROXY is rarely used.

```bash
# Set proxy environment variables
export HTTP_PROXY=http://proxy.company.local:8080
export HTTPS_PROXY=http://proxy.company.local:8080
export NO_PROXY=localhost,127.0.0.1,.cluster.local,10.0.0.0/8

# containerd proxy configuration
sudo mkdir -p /etc/systemd/system/containerd.service.d
cat <<EOF | sudo tee /etc/systemd/system/containerd.service.d/proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.company.local:8080"
Environment="HTTPS_PROXY=http://proxy.company.local:8080"
Environment="NO_PROXY=localhost,127.0.0.1,.cluster.local"
EOF

sudo systemctl daemon-reload
sudo systemctl restart containerd
```

**Addresses to include in NO_PROXY:**
- Cluster internal services (*.cluster.local)
- Pod/Service CIDR
- Node IP range
- Harbor registry address

</details>

### 8. Which is NOT a valid checklist item for verifying air-gap environment readiness?

A. Harbor registry accessibility
B. Required container images presence
C. Internet connection speed test
D. DNS resolution capability

<details>
<summary>Show Answer</summary>

**Answer: C. Internet connection speed test**

**Explanation:**
By definition, an air-gap environment has no internet connection, so internet speed testing is meaningless. Air-gap readiness verification checklist:

```bash
# 1. Verify Harbor registry access
curl -k https://harbor.airgap.local/api/v2.0/health

# 2. Verify required images exist
docker pull harbor.airgap.local/library/pause:3.9

# 3. Verify DNS resolution
nslookup harbor.airgap.local

# 4. Verify nodeadm binary
nodeadm version

# 5. Verify dependency packages
dpkg -l | grep -E "containerd|kubelet"

# 6. Verify TLS certificates
openssl s_client -connect harbor.airgap.local:443 -showcerts
```

**Verification script example:**
```bash
#!/bin/bash
echo "=== Air-gap Environment Verification ==="

# Harbor connection
if curl -sk https://harbor.airgap.local/api/v2.0/health | grep -q "healthy"; then
  echo "[OK] Harbor is healthy"
else
  echo "[FAIL] Harbor connection failed"
fi

# Required images check
REQUIRED_IMAGES="pause:3.9 coredns:v1.10.1"
for img in $REQUIRED_IMAGES; do
  if docker manifest inspect harbor.airgap.local/library/$img > /dev/null 2>&1; then
    echo "[OK] $img exists"
  else
    echo "[FAIL] $img missing"
  fi
done
```

</details>

### 9. What is the recommended method for updating container images when operating EKS Hybrid Nodes in an air-gap environment?

A. Run docker pull directly on nodes
B. Establish a periodic image mirroring and offline transfer process
C. Use only fixed versions without image updates
D. Temporarily allow internet connection

<details>
<summary>Show Answer</summary>

**Answer: B. Establish a periodic image mirroring and offline transfer process**

**Explanation:**
Air-gap environments require a systematic image management process:

```
Image Update Workflow:

[Internet-connected Environment]    [Air-gap Environment]
+-----------------------+           +-----------------------+
| 1. Check/download     |           | 4. Load images        |
|    image list         |           |                       |
| 2. Vulnerability scan | --------> | 5. Push to Harbor     |
| 3. Package as tar     | Offline   | 6. Update deployments |
+-----------------------+ Transfer  +-----------------------+
```

```bash
# Image list management (images.txt)
public.ecr.aws/eks-distro/kubernetes/pause:3.9
public.ecr.aws/eks-distro/coredns/coredns:v1.10.1
docker.io/library/nginx:1.25

# Batch download script
#!/bin/bash
while read -r image; do
  echo "Pulling $image..."
  docker pull "$image"
  name=$(echo "$image" | tr '/:' '_')
  docker save "$image" -o "${name}.tar"
done < images.txt

# Batch upload script (air-gap environment)
#!/bin/bash
for tarfile in *.tar; do
  docker load -i "$tarfile"
  # Retag and push to Harbor
done
```

**Recommendations:**
- Set monthly or quarterly image update cycles
- Establish emergency update procedures for security vulnerability patches
- Image signing and integrity verification

</details>

### 10. What is the correct method to optimize bandwidth when mirroring images in Harbor?

A. Retransfer entire images every time
B. Use layer-based incremental transfer and compression
C. Process identically regardless of image size
D. Rebuild every time instead of mirroring

<details>
<summary>Show Answer</summary>

**Answer: B. Use layer-based incremental transfer and compression**

**Explanation:**
Container images are composed of layers, and transferring only changed layers can significantly save bandwidth:

```bash
# Efficient image copy using skopeo
skopeo copy \
  --src-tls-verify=false \
  docker://source-registry.com/myapp:v1 \
  docker://harbor.airgap.local/myapp:v1

# Layer-based copy using crane
crane copy source-registry.com/myapp:v1 harbor.airgap.local/myapp:v1
```

**Optimization Strategies:**

| Method | Description | Savings |
|--------|-------------|---------|
| Layer caching | Transfer only changed layers | 50-80% |
| Compression | Apply gzip/zstd compression | 30-50% |
| Multi-architecture | Mirror only required architectures | 50% |
| Tag filtering | Mirror only required tags | Variable |

```yaml
# Filtering in Harbor replication policy
{
  "filters": [
    {"type": "tag", "value": "v*"},
    {"type": "label", "value": "production=true"}
  ]
}
```

</details>

