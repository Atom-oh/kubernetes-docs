# EKS Hybrid Nodes Air-Gap 环境设置测验

> **相关文档**: [Air-Gap 环境设置](../../eks-hybrid-nodes/03-airgap-setup.md)

## 选择题

### 1. 下列哪一项不是 Harbor 中有效的 replication policy 类型？

A. Push-based
B. Pull-based
C. Event-based
D. Sync-based

<details>
<summary>显示答案</summary>

**答案: D. Sync-based**

**说明:**
Harbor 支持 Push-based、Pull-based 和 Event-based replication policies。“Sync-based” 不是 Harbor 的官方术语。

**Harbor Replication Policy 类型:**
1. **Push-based**: 从源 Harbor 推送到目标 registry
2. **Pull-based**: 目标 Harbor 从源拉取 images
3. **Event-based**: 在 image push 事件发生时自动复制

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

### 2. 将 Harbor private registry 与 Kubernetes 集成时使用哪种 Secret 类型？

A. Opaque
B. kubernetes.io/dockerconfigjson
C. kubernetes.io/tls
D. kubernetes.io/service-account-token

<details>
<summary>显示答案</summary>

**答案: B. kubernetes.io/dockerconfigjson**

**说明:**
Docker/Container registry 认证信息会作为 `kubernetes.io/dockerconfigjson` 类型的 Secret 存储。

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

### 3. Harbor 为 image scanning 提供的默认 vulnerability scanner 是什么？

A. Clair
B. Trivy
C. Anchore
D. Snyk

<details>
<summary>显示答案</summary>

**答案: B. Trivy**

**说明:**
自 Harbor 2.0 起，Trivy 被包含为默认 vulnerability scanner。Clair 也可以选择性使用。

```bash
# Harbor Vulnerability Scan API
POST /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/scan

# Get Scan Results
GET /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/additions/vulnerabilities
```

**Harbor Scan Policy 设置:**
- Projects > Configuration > Vulnerability scanning
- Automatically scan images on push: enabled
- Prevent vulnerable images from running: enabled (CVE severity threshold)

</details>

### 4. air-gap（气隙）环境最准确的定义是什么？

A. 互联网连接速度很慢的环境
B. 与外部网络物理隔离的环境
C. 仅通过 VPN 连接的环境
D. 安装了 firewalls 的环境

<details>
<summary>显示答案</summary>

**答案: B. 与外部网络物理隔离的环境**

**说明:**
出于安全原因，air-gap 环境会与互联网或外部网络物理隔离。它通常用于：

- 军事/国防设施
- 金融机构核心系统
- 核电站控制系统
- 医疗机构敏感数据处理系统

```
Air-gap environment characteristics:
+------------------+     Physical isolation     +------------------+
|   External       | <---- No connection ---->  |   Air-gap        |
|   Network        |                            |   Environment    |
| (Internet, Cloud)|                            | (On-premises DC) |
+------------------+                            +------------------+
```

在 air-gap 环境中，所有 software 和 images 都必须离线传输。

</details>

### 5. 在 air-gap 环境中将 container images 镜像到 Harbor 的正确顺序是什么？

A. 安装 Harbor -> 标记 image -> 推送 image -> 拉取 image
B. 拉取 image -> 保存 image -> 离线传输 -> 加载并推送到 Harbor
C. 安装 Harbor -> 直接 ECR 连接 -> 自动同步
D. 构建 image -> 直接部署 -> 跳过 Harbor

<details>
<summary>显示答案</summary>

**答案: B. 拉取 image -> 保存 image -> 离线传输 -> 加载并推送到 Harbor**

**说明:**
在 air-gap 环境中没有互联网连接，因此 images 必须手动传输：

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

对于管理大量 images，`skopeo` 或 `crane` 等工具更高效。

</details>

### 6. 在 air-gap 环境中离线安装 nodeadm 的正确方法是什么？

A. 使用 curl 直接从 GitHub 下载
B. apt-get install nodeadm
C. 预先下载 binaries 和 dependencies 以便离线安装
D. pip install nodeadm

<details>
<summary>显示答案</summary>

**答案: C. 预先下载 binaries 和 dependencies 以便离线安装**

**说明:**
在 air-gap 环境中无法访问互联网，因此必须提前准备所有必要文件：

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

### 7. 在 air-gap 环境中配置 proxy server 时，不需要设置的环境变量是哪一个？

A. HTTP_PROXY
B. HTTPS_PROXY
C. NO_PROXY
D. FTP_PROXY

<details>
<summary>显示答案</summary>

**答案: D. FTP_PROXY**

**说明:**
在 container 和 Kubernetes 环境中常用的 proxy 环境变量是 HTTP_PROXY、HTTPS_PROXY 和 NO_PROXY。FTP_PROXY 很少使用。

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

**需要包含在 NO_PROXY 中的地址:**
- Cluster internal services (*.cluster.local)
- Pod/Service CIDR
- Node IP range
- Harbor registry address

</details>

### 8. 下列哪一项不是验证 air-gap 环境就绪状态的有效 checklist 项？

A. Harbor registry accessibility
B. Required container images presence
C. Internet connection speed test
D. DNS resolution capability

<details>
<summary>显示答案</summary>

**答案: C. Internet connection speed test**

**说明:**
根据定义，air-gap 环境没有互联网连接，因此互联网速度测试没有意义。Air-gap 就绪状态验证 checklist：

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

**验证脚本示例:**
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

### 9. 在 air-gap 环境中运行 EKS Hybrid Nodes 时，更新 container images 的推荐方法是什么？

A. 直接在 nodes 上运行 docker pull
B. 建立定期 image mirroring 和离线传输流程
C. 仅使用固定版本，不进行 image 更新
D. 临时允许互联网连接

<details>
<summary>显示答案</summary>

**答案: B. 建立定期 image mirroring 和离线传输流程**

**说明:**
Air-gap 环境需要系统化的 image 管理流程：

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

**建议:**
- 设置每月或每季度 image 更新周期
- 为安全漏洞补丁建立紧急更新流程
- Image signing 和完整性验证

</details>

### 10. 在 Harbor 中镜像 images 时优化带宽的正确方法是什么？

A. 每次都重新传输整个 images
B. 使用基于 layer 的增量传输和压缩
C. 无论 image 大小如何都以相同方式处理
D. 每次都重新构建而不是 mirroring

<details>
<summary>显示答案</summary>

**答案: B. 使用基于 layer 的增量传输和压缩**

**说明:**
Container images 由 layers 组成，仅传输已更改的 layers 可以显著节省带宽：

```bash
# Efficient image copy using skopeo
skopeo copy \
  --src-tls-verify=false \
  docker://source-registry.com/myapp:v1 \
  docker://harbor.airgap.local/myapp:v1

# Layer-based copy using crane
crane copy source-registry.com/myapp:v1 harbor.airgap.local/myapp:v1
```

**优化策略:**

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
