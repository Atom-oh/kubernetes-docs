# EKS Hybrid Nodes 前提条件クイズ

> **関連ドキュメント**: [前提条件](../../eks-hybrid-nodes/01-prerequisites.md)

## 多肢選択問題

### 1. EKS Hybrid Nodes のユースケースとして適していないものはどれですか？

A. オンプレミスのデータセンターにある GPU サーバーの活用
B. 規制コンプライアンスのためのデータローカリティ要件
C. 純粋なクラウドネイティブワークロードの実行
D. レイテンシに敏感なエッジワークロード

<details>
<summary>回答を表示</summary>

**回答: C. 純粋なクラウドネイティブワークロードの実行**

**解説:**
純粋なクラウドネイティブワークロードは、通常の EKS node groups または Fargate で実行する方が効率的です。Hybrid Nodes は、特別な要件（オンプレミス、エッジ、規制など）がある場合に使用されます。

**EKS Hybrid Nodes に適したユースケース:**
- オンプレミスの GPU/特殊ハードウェアの活用
- データ主権/規制コンプライアンス要件
- レイテンシに敏感なエッジコンピューティング
- クラウド移行の移行期間
- 既存インフラ投資の保護

</details>

### 2. EKS Hybrid Nodes でサポートされているオペレーティングシステムはどれですか？

A. Windows Server 2019 のみ
B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9
C. macOS Ventura 以降
D. FreeBSD 13 以降

<details>
<summary>回答を表示</summary>

**回答: B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9**

**解説:**
EKS Hybrid Nodes は Linux ベースのオペレーティングシステムのみをサポートします。サポートされる OS version には次が含まれます:
- Ubuntu 20.04 LTS, 22.04 LTS
- Amazon Linux 2023
- Red Hat Enterprise Linux (RHEL) 8, 9
- Bottlerocket (container-optimized OS)

```bash
# Check OS version
cat /etc/os-release

# Check kernel version (5.4 or later recommended)
uname -r
```

</details>

### 3. Hybrid Nodes で GPU ワークロードを実行するための最小要件ではないものはどれですか？

A. NVIDIA Driver 525 以降
B. CUDA Toolkit 11.8 以降
C. 最小 4GB の GPU メモリ
D. x86_64 または arm64 architecture が必須である

<details>
<summary>回答を表示</summary>

**回答: D. x86_64 または arm64 architecture が必須である**

**解説:**
x86_64 または arm64 architecture は CPU architecture の要件であり、GPU ワークロードの直接的な要件ではありません。GPU ワークロードの主な要件は次のとおりです:

- **NVIDIA Driver**: 525 以降 (CUDA 12 support)
- **CUDA Toolkit**: 11.8 以降
- **GPU Memory**: 最小 4GB 推奨（ワークロードによって異なります）
- **containerd**: 1.6 以降 (GPU container support)

```bash
# Check NVIDIA driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader

# Check CUDA version
nvcc --version
```

</details>

### 4. EKS Hybrid Nodes の最小ハードウェア要件は何ですか？

A. CPU 1 core, Memory 512MB
B. CPU 2 cores, Memory 2GB
C. CPU 4 cores, Memory 8GB
D. CPU 8 cores, Memory 16GB

<details>
<summary>回答を表示</summary>

**回答: B. CPU 2 cores, Memory 2GB**

**解説:**
EKS Hybrid Nodes の最小ハードウェア要件は次のとおりです:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores or more |
| Memory | 2GB | 4GB or more |
| Disk | 20GB | 50GB or more (SSD recommended) |
| Network | 100Mbps | 1Gbps or more |

本番環境では、ワークロード要件に応じてより高い仕様が必要になる場合があります。

</details>

### 5. EKS Hybrid Nodes configuration に必要な software component ではないものはどれですか？

A. containerd runtime
B. kubelet
C. Docker Engine
D. aws-iam-authenticator

<details>
<summary>回答を表示</summary>

**回答: C. Docker Engine**

**解説:**
EKS Hybrid Nodes は container runtime として containerd を使用するため、Docker Engine は不要です。必要な components は次のとおりです:

- **containerd**: Container runtime (1.6 以降)
- **kubelet**: Kubernetes node agent
- **aws-iam-authenticator**: AWS IAM authentication
- **CNI plugins**: Container networking

```bash
# nodeadm automatically installs components
sudo nodeadm init --config-source file://nodeadm-config.yaml

# Check installed components
systemctl status containerd
systemctl status kubelet
```

</details>

### 6. Hybrid Nodes で H100 GPU を使用するために必要な最小 NVIDIA driver version は何ですか？

A. 450.x
B. 470.x
C. 525.x
D. 535.x

<details>
<summary>回答を表示</summary>

**回答: D. 535.x**

**解説:**
NVIDIA H100 GPU は Hopper architecture を使用し、最新の drivers が必要です:

| GPU Model | Minimum Driver Version | Recommended Driver Version |
|-----------|----------------------|---------------------------|
| A100 | 450.x | 525.x or later |
| H100 | 525.x | 535.x or later |
| H200 | 535.x | 545.x or later |

```bash
# Verify H100 driver installation
nvidia-smi

# Update driver
sudo apt-get update
sudo apt-get install nvidia-driver-535
```

H100 の主要機能（MIG expansion、Transformer Engine など）を最大限に活用するには、driver version 535.x 以降が推奨されます。

</details>
