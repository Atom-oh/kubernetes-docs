# EKS Hybrid Nodes Air-Gap 環境セットアップクイズ

> **関連ドキュメント**: [Air-Gap 環境セットアップ](../../eks-hybrid-nodes/03-airgap-setup.md)

## 多肢選択問題

### 1. Harbor で有効な replication policy type ではないものはどれですか？

A. Push-based
B. Pull-based
C. Event-based
D. Sync-based

<details>
<summary>回答を表示</summary>

**回答: D. Sync-based**

**解説:**
Harbor は Push-based、Pull-based、Event-based の replication policies をサポートしています。"Sync-based" は Harbor の公式用語ではありません。

**Harbor Replication Policy の種類:**
1. **Push-based**: source Harbor から target registry へ push
2. **Pull-based**: Target Harbor が source から images を pull
3. **Event-based**: image push events に基づく自動 replication

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

### 2. Harbor private registry を Kubernetes と統合する場合、どの Secret type が使用されますか？

A. Opaque
B. kubernetes.io/dockerconfigjson
C. kubernetes.io/tls
D. kubernetes.io/service-account-token

<details>
<summary>回答を表示</summary>

**回答: B. kubernetes.io/dockerconfigjson**

**解説:**
Docker/Container registry の認証情報は `kubernetes.io/dockerconfigjson` type の Secret として保存されます。

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

### 3. Harbor で image scanning に提供される default vulnerability scanner は何ですか？

A. Clair
B. Trivy
C. Anchore
D. Snyk

<details>
<summary>回答を表示</summary>

**回答: B. Trivy**

**解説:**
Harbor 2.0 以降、Trivy が default vulnerability scanner として含まれています。Clair も optional で使用できます。

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

### 4. air-gap 環境（外部ネットワークから物理的に隔離された環境）の最も正確な定義は何ですか？

A. internet connection が遅い環境
B. 外部ネットワークから物理的に隔離された環境
C. VPN 経由でのみ接続される環境
D. firewalls が installed されている環境

<details>
<summary>回答を表示</summary>

**回答: B. 外部ネットワークから物理的に隔離された環境**

**解説:**
air-gap 環境は、security 上の理由から internet または外部ネットワークから物理的に分離された環境です。一般的に次のような場所で使用されます:

- 軍事/防衛施設
- 金融機関の core systems
- 原子力発電所の control systems
- 医療機関の sensitive data processing systems

```
Air-gap environment characteristics:
+------------------+     Physical isolation     +------------------+
|   External       | <---- No connection ---->  |   Air-gap        |
|   Network        |                            |   Environment    |
| (Internet, Cloud)|                            | (On-premises DC) |
+------------------+                            +------------------+
```

air-gap 環境では、すべての software と images を offline で転送する必要があります。

</details>

### 5. air-gap 環境で container images を Harbor に mirroring する正しい順序はどれですか？

A. Harbor を install -> image に tag を付ける -> image を push -> image を pull
B. image を pull -> image を save -> Offline transfer -> Harbor に load and push
C. Harbor を install -> Direct ECR connection -> Auto sync
D. image を build -> Direct deploy -> Harbor を skip

<details>
<summary>回答を表示</summary>

**回答: B. image を pull -> image を save -> Offline transfer -> Harbor に load and push**

**解説:**
air-gap 環境では internet connection がないため、images を手動で転送する必要があります:

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

大量の images を管理する場合は、`skopeo` や `crane` のような tools の方が効率的です。

</details>

### 6. air-gap 環境で nodeadm を offline installation する正しい方法はどれですか？

A. curl を使用して GitHub から直接 download
B. apt-get install nodeadm
C. offline installation 用に binaries と dependencies を事前に download
D. pip install nodeadm

<details>
<summary>回答を表示</summary>

**回答: C. offline installation 用に binaries と dependencies を事前に download**

**解説:**
air-gap 環境では internet access ができないため、必要なすべての files を事前に準備する必要があります:

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

### 7. air-gap 環境で proxy server を設定する場合、設定が必要な environment variable ではないものはどれですか？

A. HTTP_PROXY
B. HTTPS_PROXY
C. NO_PROXY
D. FTP_PROXY

<details>
<summary>回答を表示</summary>

**回答: D. FTP_PROXY**

**解説:**
container と Kubernetes 環境で一般的に使用される proxy environment variables は HTTP_PROXY、HTTPS_PROXY、NO_PROXY です。FTP_PROXY はほとんど使用されません。

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

**NO_PROXY に含める addresses:**
- Cluster internal services (*.cluster.local)
- Pod/Service CIDR
- Node IP range
- Harbor registry address

</details>

### 8. air-gap 環境の readiness を検証する checklist item として有効ではないものはどれですか？

A. Harbor registry へのアクセス可能性
B. Required container images presence
C. Internet connection speed test
D. DNS resolution capability

<details>
<summary>回答を表示</summary>

**回答: C. Internet connection speed test**

**解説:**
定義上、air-gap 環境には internet connection がないため、internet speed testing は意味がありません。air-gap readiness verification checklist:

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

**検証 script 例:**
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

### 9. air-gap 環境で EKS Hybrid Nodes を運用する際、container images を update する推奨方法は何ですか？

A. nodes 上で docker pull を直接実行する
B. 定期的な image mirroring と offline transfer process を確立する
C. image updates なしで fixed versions のみを使用する
D. 一時的に internet connection を許可する

<details>
<summary>回答を表示</summary>

**回答: B. 定期的な image mirroring と offline transfer process を確立する**

**解説:**
air-gap 環境では体系的な image management process が必要です:

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

**推奨事項:**
- monthly または quarterly の image update cycles を設定する
- security vulnerability patches のための emergency update procedures を確立する
- Image signing と integrity verification

</details>

### 10. Harbor で images を mirroring する際に bandwidth を最適化する正しい方法は何ですか？

A. 毎回 images 全体を retransmission する
B. layer-based incremental transfer と compression を使用する
C. image size に関係なく同じように処理する
D. mirroring せずに毎回 rebuild する

<details>
<summary>回答を表示</summary>

**回答: B. layer-based incremental transfer と compression を使用する**

**解説:**
Container images は layers で構成されており、変更された layers のみを転送することで bandwidth を大幅に節約できます:

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
