# EKS Hybrid Nodes GPU Integration クイズ

> **関連ドキュメント**: [GPU Integration](../../eks-hybrid-nodes/05-gpu-integration.md)

## 選択問題

### 1. NVIDIA GPU Multi-Instance GPU (MIG) technology の重要な特徴は何ですか？

A. 複数の GPUs を 1 つに結合する
B. 1 つの GPU を物理的に分離された複数の instances に分割する
C. GPU memory のみを共有する
D. Software-level Time-Slicing

<details>
<summary>解答を表示</summary>

**解答: B. 1 つの GPU を物理的に分離された複数の instances に分割する**

**説明:**
MIG (Multi-Instance GPU) は、NVIDIA A100 や H100 などの GPUs を最大 7 つの物理的に分離された instances に分割します。各 instance は独立した memory、cache、compute resources を持ちます。

**MIG と Time-Slicing の比較:**

| 機能 | MIG | Time-Slicing |
|---------|-----|--------------|
| 分離レベル | 物理的 (完全分離) | 時間ベース (software) |
| Memory 分離 | 完全分離 | 共有 |
| 対応 GPUs | A100, H100 | すべての NVIDIA GPUs |
| QoS 保証 | はい | いいえ |

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

### 2. NVIDIA GPU MIG configuration における "1g.5gb" は何を意味しますか？

A. 1GB memory、5 GPU cores
B. 1 GPU Instance (1 compute slice)、5GB GPU memory
C. 1 GPU、5GB system memory
D. 5GB throughput あたり 1 秒

<details>
<summary>解答を表示</summary>

**解答: B. 1 GPU Instance (1 compute slice)、5GB GPU memory**

**説明:**
MIG instance name format: `<compute-slices>g.<memory-size>gb`

- **1g**: 1 compute slice
- **5gb**: 5GB GPU memory

**A100 MIG Profile の例:**
- `1g.5gb`: 1 compute slice、5GB memory (最大 7)
- `2g.10gb`: 2 compute slices、10GB memory (最大 3)
- `3g.20gb`: 3 compute slices、20GB memory (最大 2)
- `4g.40gb`: 4 compute slices、40GB memory (最大 1)
- `7g.40gb`: 7 compute slices、40GB memory (full GPU)

```bash
# Check MIG instances
nvidia-smi mig -lgi
```

</details>

### 3. GPU Time-Slicing で oversubscription が発生した場合、想定される挙動は何ですか？

A. GPU task が完全に失敗する
B. Context switching による performance degradation
C. GPU が自動的に追加される
D. Memory が自動的に拡張される

<details>
<summary>解答を表示</summary>

**解答: B. Context switching による performance degradation**

**説明:**
Time-Slicing により、複数の workloads が 1 つの GPU を時間分割ベースで共有できます。Oversubscription が発生すると、頻繁な context switching により performance degradation が発生します。

```yaml
# GPU Time-Slicing Configuration
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
        resources:
        - name: nvidia.com/gpu
          replicas: 4  # Split 1 GPU into 4
```

**Time-Slicing に関する考慮事項:**
- Memory は共有されるため、OOM が発生する可能性があります
- Inference workloads に適しています
- Training には MIG または dedicated GPUs が推奨されます
- 適切な replicas count の設定が重要です

</details>

### 4. Dynamic Resource Allocation (DRA) の主な利点は何ですか？

A. Static resource allocation のみをサポートする
B. Vendor-specific plugins なしですべての devices をサポートする
C. Custom resources のための柔軟な request/allocation mechanism
D. CPU と memory のみを管理する

<details>
<summary>解答を表示</summary>

**解答: C. Custom resources のための柔軟な request/allocation mechanism**

**説明:**
Kubernetes 1.26 で導入された DRA (Dynamic Resource Allocation) は、GPUs、FPGAs、network devices などの custom resources に対して、より柔軟な request と allocation mechanism を提供します。

**DRA の主要 components:**
- **ResourceClass**: Drivers が提供する resource types を定義します
- **ResourceClaim**: Resources の request
- **ResourceClaimTemplate**: 再利用可能な claim template

```yaml
# Using DRA in Pod
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  containers:
  - name: cuda-app
    resources:
      claims:
      - name: gpu
  resourceClaims:
  - name: gpu
    source:
      resourceClaimTemplateName: gpu-claim-template
```

</details>

### 5. DRA (Dynamic Resource Allocation) で ResourceClaim status が "Bound" になるために満たす必要がある条件は何ですか？

A. Claim の作成のみ
B. Driver が resources を割り当て、Pod が schedule される
C. Pod が終了する
D. Claim が削除される

<details>
<summary>解答を表示</summary>

**解答: B. Driver が resources を割り当て、Pod が schedule される**

**説明:**
ResourceClaim status flow:

1. **Pending**: Claim が作成され、まだ割り当てられていない
2. **Allocated**: Driver が resource allocation を完了した
3. **Bound**: Pod に bound され、使用中

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

### 6. NVIDIA GPU Operator の主な役割は何ですか？

A. GPU hardware の製造
B. Kubernetes における GPU drivers、runtimes、plugins の自動管理
C. GPU performance testing のみ
D. GPU の購入と配送管理

<details>
<summary>解答を表示</summary>

**解答: B. Kubernetes における GPU drivers、runtimes、plugins の自動管理**

**説明:**
NVIDIA GPU Operator は、Kubernetes の GPU infrastructure を自動的に管理します:

- NVIDIA driver の installation/updates
- NVIDIA Container Toolkit の installation
- NVIDIA Device Plugin の deployment
- GPU monitoring (DCGM Exporter)
- MIG management

```bash
# Install GPU Operator (Helm)
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace
```

```yaml
# GPU Operator Custom Configuration
apiVersion: nvidia.com/v1
kind: ClusterPolicy
metadata:
  name: cluster-policy
spec:
  driver:
    enabled: true
    version: "535.104.12"
  toolkit:
    enabled: true
  devicePlugin:
    enabled: true
  mig:
    strategy: mixed
```

</details>

### 7. H100 と H200 GPUs の主な違いは何ですか？

A. H200 は H100 より memory capacity が少ない
B. H200 は H100 より高い bandwidth の HBM3e memory を提供する
C. H200 は MIG をサポートしていない
D. H200 は data centers 向けではない

<details>
<summary>解答を表示</summary>

**解答: B. H200 は H100 より高い bandwidth の HBM3e memory を提供する**

**説明:**
H200 は H100 の後継であり、改良された memory system を提供します:

| 機能 | H100 | H200 |
|---------|------|------|
| Memory Type | HBM3 | HBM3e |
| Memory Capacity | 80GB | 141GB |
| Memory Bandwidth | 3.35TB/s | 4.8TB/s |
| MIG Support | はい (最大 7) | はい (最大 7) |
| LLM Inference | 優秀 | 最適化済み |

```yaml
# H200 Node Selection
apiVersion: v1
kind: Pod
spec:
  nodeSelector:
    nvidia.com/gpu.product: "NVIDIA-H200"
  containers:
  - name: llm
    resources:
      limits:
        nvidia.com/gpu: 1
```

H200 は、その memory capacity と bandwidth により、特に large language model (LLM) inference で優れた performance を示します。

</details>
