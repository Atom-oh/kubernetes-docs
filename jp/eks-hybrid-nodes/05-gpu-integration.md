# GPU Server の統合

< [前へ: Node Bootstrap](./04-node-bootstrap.md) | [目次](./README.md) | [次へ: Workload Placement](./06-workload-placement.md) >

> **サポート対象バージョン**: DRA GPU の例では、サポート対象の EKS バージョンで Kubernetes 1.34.2+ が必要です。確認済みのインターフェイス: GPU Operator 26.7.0、DRA driver 0.5.0、device plugin 0.20.0。
> **最終更新**: October 12, 2026

この章では、準備済みの NVIDIA GPU ホストを EKS Hybrid Nodes と統合します。割り当て、GPU Operator の所有権、MIG、および time-slicing を扱います。**この監査では、GPU、driver のインストール、モデルのダウンロード、または inference benchmark は実行していません。** 例には、承認済みの OS/kernel/driver/toolkit/runtime/image の組み合わせと、実際のハードウェアでのテストが必要です。

## GPU ごとに 1 つの割り当て所有者を選択する

| パス | 前提条件と割り当て |
|---|---|
| スタンドアロン NVIDIA device plugin | 準備済みのホスト driver、NVIDIA Container Toolkit、および runtime。`nvidia.com/gpu` などの拡張リソースを公開します |
| スタンドアロン DRA driver | 準備済みの driver と CDI runtime。ResourceSlices を公開し、DeviceClass/ResourceClaim を介して割り当てます |
| `ClusterPolicy` を使用する GPU Operator | Operator 管理の device-plugin ワークフロー。driver/toolkit/MIG コンポーネントの所有権は、すでにインストール済みのものと一致している必要があります |
| `GPUCluster` を使用する GPU Operator 26.7 | 新規インストール向けの Operator 管理 DRA ワークフロー。クラスター内の `ClusterPolicy` とは相互排他的です |

AWS は、サポート対象の静的キャパシティプロビジョニングを使用する新規 EKS 1.34+ デプロイメントに DRA を推奨しています。**NVIDIA DRA driver は EKS Auto Mode ではサポートされません**。EKS Auto Mode は自身の GPU device plugin をすでに管理しているためです。AWS は Auto Mode および Karpenter の動的キャパシティに対して NVIDIA device plugin を案内しています（[EKS standard-support release notes](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html) の Kubernetes 1.37 セクション、2026 年 10 月 12 日に確認）。以下のスタンドアロン例は、特定された Hybrid GPU node のみを対象としています。Auto Mode または他の GPU node に重複する割り当てマネージャーをインストールしないでください。

`workload.example.com/gpu-allocation=device-plugin` や `dra` のような、重複しない所有者管理ラベルを使用してください。これらのラベルはスケジューリング入力であり、セキュリティ境界でも正常な GPU ハードウェアの証明でもありません。いずれかのパスを有効にする前に、同じ物理デバイスを公開している他の plugin/Operator がないことを確認してください。

## ホストコホートを準備して検証する

- Hybrid identity、CNI、時刻同期を含む [Node Bootstrap](./04-node-bootstrap.md) を完了してください。
- GPU モデル/フォームファクター、firmware、driver branch、OS/kernel、および runtime を NVIDIA のマトリックスおよび AWS Hybrid OS サポートと照合してください。新しい NVIDIA マトリックスに記載されているすべての Kubernetes バージョンを EKS が提供するわけではありません。
- 実際の NVIDIA driver と toolkit がインストールされていることを確認してください。オンプレミスであることは driver が存在することを意味しません。
- legacy の例では、設定済みの containerd NVIDIA runtime handler をバックエンドとする、`nvidia` という名前の既存の `RuntimeClass` を準備してください。class 名だけでは handler は設定されません。
- DRA 0.5.0 GPU 割り当てでは、リリース済みの前提条件ガイドで Kubernetes **1.34.2+**、スタンドアロン driver **565+**、Toolkit **1.18+**、および CDI 対応 runtime が必要とされています。GPU Operator DRA ワークフローでは driver **580+** が必要です。これらは互換性の下限であり、現在の patch/branch 推奨ではありません。
- 承認済みの NFD/GFD インストールまたはホストインベントリプロセスを通じて discovery ラベルを準備してください。例で有効化されているというだけで、2 つ目の discovery controller をデプロイしないでください。

次の Operator 実行チェックはホスト GPU メタデータを読み取ります。CUDA または LLM benchmark ではありません。

```bash
nvidia-smi --query-gpu=name,driver_version,uuid,memory.total --format=csv,noheader
```

前の例における `cpu: 128`、`memory: 1024Gi`、`nvidia.com/gpu: 8` の出力は、**未検証の例示**であり、この監査での測定値ではありません。Kubernetes GPU キャパシティは、設定に応じて物理 GPU、MIG instance、または time-slicing replica を表すことがあります。

## 選択した Hybrid node 上のスタンドアロン device plugin

次の values には、事前インストール済みの driver/runtime と、既存の互換性のある discovery セットアップが必要です。2 つの node-selector ラベルは chart の GPU-discovery affinity と組み合わされます。一致する node がない場合は、インベントリ/ラベルを修正してください。Pod を実行するためだけに affinity を削除しないでください。

```yaml
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  workload.example.com/gpu-allocation: device-plugin
runtimeClassName: nvidia
migStrategy: none
failOnInitError: true
deviceListStrategy: envvar
gfd:
  enabled: false
nfd:
  enabled: false
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

`device-plugin-values.yaml` として保存してください。確認済みの chart は **0.20.0** です。デプロイ前に、目的のアップグレードパスと image の互換性を確認してください。

```bash
# Cluster write; installs a privileged infrastructure component.
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" get nodes \
  -l 'eks.amazonaws.com/compute-type=hybrid,workload.example.com/gpu-allocation=device-plugin' \
  -o json > plugin-nodes.json
jq -e '.items | length > 0 and
  all(.[]; .metadata.labels["nvidia.com/mps.capable"] != "true")' plugin-nodes.json
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update nvdp
helm install hybrid-gpu-plugin nvdp/nvidia-device-plugin \
  --version 0.20.0 --namespace gpu-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values device-plugin-values.yaml --wait --timeout 10m
```

GPU infrastructure operator が所有する namespace と release を使用してください。レンダリングされた RBAC、ホストパス、特権、registry アクセス、および toleration を確認してください。Helm `--wait` の成功は CUDA 互換性や workload パフォーマンスの証明ではありません。

公開済みの 0.20.0 chart は、`nvidia.com/mps.capable=true` と選択した Hybrid コホートで制限された MPS control DaemonSet もレンダリングします。この排他的 GPU の例では、そのようなラベルがすでに設定されている場合に停止します。ラベルを無批判にクリアするのではなく、既存の MPS 所有権を調査してください。chart に DaemonSet が 1 つしか含まれていないと想定しないでください。

## 別の Hybrid GPU コホート上のスタンドアロン DRA

現在の driver project は **`kubernetes-sigs/dra-driver-nvidia-gpu`** です。DRA API の安定性、EKS サポート、および個々の vendor feature の成熟度は、別々に確認する必要があります。現在の NVIDIA 26.7 ドキュメントでは、full-GPU と既存 MIG の割り当ては GA とされています。dynamic MIG、MPS、一部の sharing、および NVML allocation-health feature には個別の Alpha gate があります。デモを開始させるためにすべての feature gate を有効にしないでください。

タグ付き repository README の古い説明では、GPU 割り当てはサポートされないと記載されています。リリース済みの前提条件/インストールドキュメントと現在の NVIDIA capability table が、より新しい feature 固有のガイダンスを提供します。本番デプロイメントでは、正確なバージョンとサポート契約を記録してください。

この例では、通常の H100/H200 割り当てに Multi-Node NVLink オーケストレーションが必要ないため、ComputeDomains を無効にしています。ComputeDomains には、追加の Grace Blackwell/MNNVL、IMEX、および discovery の要件があります。

```yaml
gpuResourcesEnabledOverride: true
nvidiaDriverRoot: /
resources:
  gpus:
    enabled: true
  computeDomains:
    enabled: false
featureGates: {}
kubeletPlugin:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
    workload.example.com/gpu-allocation: dra
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  containers:
    gpus:
      resources:
        requests:
          cpu: 50m
          memory: 128Mi
        limits:
          cpu: "1"
          memory: 512Mi
webhook:
  enabled: false
```

`dra-values.yaml` として保存してください。このパスは、ホスト driver root が `/` であり、CDI が設定済みであることを前提としています。Operator がインストールした driver は通常異なる root を使用します。この値をそのデプロイメントにコピーしないでください。

```bash
# Alternative cluster write, only for the separately selected DRA cohort.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}"
helm install hybrid-gpu-dra \
  oci://registry.k8s.io/dra-driver-nvidia/charts/dra-driver-nvidia-gpu \
  --version 0.5.0 --namespace gpu-dra-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values dra-values.yaml --wait --timeout 10m
```

`gpuResourcesEnabledOverride=true` は、この chart で GPU resource に依然として必要です。これは、すべての GPU feature が Alpha であるという主張ではありません。この最小例では任意の admission webhook は無効です。有効化するには、到達可能な webhook endpoint と、検証済みの TLS/cert-manager または既存 secret の設定が必要です。

### GPU Operator の代替手段と所有権

管理対象コンポーネントのライフサイクルが意図するインストールに合致する場合は、Operator を使用してください。`driver.enabled=false` が適切なのは、**ホスト driver がすでに検証済みの場合のみ**です。同様に、必要な runtime 設定が準備できてから toolkit 管理を無効にしてください。Operator のアップグレードにより、driver、validator、resource advertisement、および node の可用性が変わる可能性があります。

**新規の Operator 管理 DRA** では、ドキュメントに次の values が含まれています。

```yaml
clusterPolicy:
  deployCR: false
gpuCluster:
  deployCR: true
driver:
  enabled: false
nfd:
  enabled: false
draDriver:
  computeDomains:
    enabled: false
```

この断片は、承認済みの事前インストール済み driver、CDI runtime、および discovery インストールを前提としています。GPUCluster は ClusterPolicy の toolkit/MIG-management 動作を自動的に提供しません。**26.7.0** の完全な chart values を確認してから、クラスターの GPU 所有者を介してデプロイしてください。

`GPUCluster` は `gpu-cluster` という名前のクラスタースコープ singleton です。`ClusterPolicy` と共存できません。ClusterPolicy またはスタンドアロン DRA Helm release から GPUCluster へのインプレース移行は、このワークフローではサポートされません。ドキュメント化された新規インストールパスを使用してください。Operator 管理デプロイメント用に、追加のスタンドアロン DRA release をインストールしないでください。

Operator controller の `nodeSelector` は、すべての operand を制限するものでは**ありません**。operand 配置は GPU discovery と `nvidia.com/gpu.deploy.*` ラベルを使用します。除外対象の cloud/Auto Mode GPU と将来の node も確認してください。その境界を維持できない場合は、分離されたクラスターまたは適切にスコープされたスタンドアロンパスを使用してください。

GPUCluster reconciliation は GPU validator を実行して claim を割り当てることができます。その readiness status と DCGM telemetry は DRA device-allocation health と同等ではありません。`NVMLDeviceHealthCheck` は Alpha であり、この release ではデフォルトで無効です。

## 現行の DRA manifest

これらの例では **`resource.k8s.io/v1`** を使用します。Kubernetes 1.31 の以前の alpha 形式は、現行クラスター向けの drop-in manifest ではありません。DRA には、動作する vendor driver、ResourceSlices、互換性のある kubelet/runtime、および有効化された API が必要です。DeviceClass だけでは GPU を検出しません。

```yaml
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-full-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu"
---
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-large-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu" &&
          device.capacity["gpu.nvidia.com"].memory.isGreaterThan(quantity("40Gi"))
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: single-large-gpu
  namespace: ai-workloads
spec:
  spec:
    devices:
      requests:
        - name: gpu
          exactly:
            deviceClassName: hybrid-large-gpu
            allocationMode: ExactCount
            count: 1
```

`type == "gpu"` selector は、同じ `gpu.nvidia.com` driver の下で公開される MIG および VFIO device を除外します。2 番目の class は、公開済みメモリが **40 GiB より大きい**ものを選択します。H100/H200 専用 selector ではありません。実際のキャパシティと NVML `productName` について ResourceSlice を確認してください。`NVIDIA-H200` のような GFD node label は、DRA product-name attribute と一致する必要はありません。

この API の DeviceClass に `suitableNodes` field はありません。workload はその node selector/affinity で制約し、DRA に device と node の可用性を照合させてください。request は `requests[].exactly` を使用します。Pod claim は、古い `source` wrapper を使用せず、`resourceClaimTemplateName` を直接参照します。

## 制限付き GPU smoke Job

承認済み namespace（例: `ai-workloads`）と、選択した driver/runtime、non-root UID、および読み取り専用 root filesystem で動作する、**digest で固定された**テスト済み image を使用してください。以下の placeholder image は意図的に使用不能です。両方の Job はデフォルトで**suspend**されているため、適用しても GPU work は開始されません。

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-plugin-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      runtimeClassName: nvidia
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: device-plugin
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
              nvidia.com/gpu: 1
            limits:
              cpu: 500m
              memory: 256Mi
              nvidia.com/gpu: 1
---
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-dra-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: dra
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
            claims:
              - name: gpu-resource
      resourceClaims:
        - name: gpu-resource
          resourceClaimTemplateName: single-large-gpu
```

最初の Job は排他的 legacy-device-plugin の例用であり、2 番目は別の DRA コホート用です。同じ GPU を両方のメカニズムで要求しないでください。複数の container が参照していても、単一の DRA claim は 1 つの割り当てです。

所有者が image を置き換え、配置/runtime/security を検証し、GPU テストを承認した後、通常のデプロイプロセスを通じて意図した Job のみを unsuspend してください。TTL cleanup 前にその結果を取得してください。120 秒の deadline は、Job が開始した後を制限するものであり、image の準備時間や外部メンテナンス操作の時間を制限するものではありません。

1 device claim に対して `CUDA_VISIBLE_DEVICES=0,1,2,3` を設定しないでください。device manager/runtime が割り当て済み device を提供します。CUDA の process-visible index は物理 GPU index と異なる可能性があります。手動 override により割り当てが非表示になったり誤認されたりする可能性があり、追加 GPU を付与するものではありません。

`nvidia-smi -L` が確認するのは device visibility のみです。承認済みハードウェア上で、制限された CUDA operation と実際の application を別途検証してください。このドキュメントでは、そのような実行またはパフォーマンス結果は主張していません。

## MIG と time-slicing

MIG は、サポート対象 GPU をハードウェアに裏付けられた compute/memory instance に分割します。time-slicing より強力な resource および memory/fault isolation を提供しますが、共有ホスト/driver を完全なセキュリティ境界に変えるものでも、application の latency SLO を保証するものでもありません。サポート対象 profile と instance 制限は GPU SKU と driver に依存します。

一般的な **A100 40 GB** profile は次のとおりです。

| Profile | 公称 profile メモリ | その profile の最大 instance 数 |
|---|---|---|
| `1g.5gb` | 5 GB | 7 |
| `2g.10gb` | 10 GB | 3 |
| `3g.20gb` | 20 GB | 2 |
| `4g.20gb` | 20 GB | 1 |
| `7g.40gb` | 40 GB | 1 |

`4g.40gb` は **A100 80 GB** profile set に属します。古い quiz ではこれらの SKU table が混在していました。`1g` は profile の GPU compute slice 数を指し、物理 GPU の数ではありません。公称メモリラベルは、正確な使用可能メモリを保証するものではありません。mixed profile の配置には追加の geometry 制約があります。

MIG の有効化/再構成は所有者が制御するメンテナンス操作であり、GPU workload を中断することがあります。上記の baseline standalone-plugin values は `migStrategy: none` を使用します。Pod request を `nvidia.com/mig-1g.5gb` に変更しても、MIG instance は作成されません。まず実際の MIG geometry と plugin の適切な strategy を準備してください。

Time-slicing は、物理的に分離された GPU やメモリ partition ではなく、複数の**論理アクセス slot**を公開します。たとえば、別途確認済みの device-plugin 設定では次を使用できます。

```yaml
# Fragment of device-plugin configuration, not a Kubernetes resource.
version: v1
sharing:
  timeSlicing:
    renameByDefault: true
    failRequestsGreaterThanOne: true
    resources:
      - name: nvidia.com/gpu
        replicas: 4
```

この設定は、named ConfigMap/config selection を通じて plugin と意図した node に接続してください。接続されていない ConfigMap は何も変更しません。`renameByDefault: true` では、公開される resource は `nvidia.com/gpu.shared` です。この共有 resource に対して、排他的 GPU smoke request を変更せずに使用しないでください。

4 replica は 4 つの独立したメモリ領域を予約するものではなく、より多くの ticket を要求しても比例した compute を保証しません。競合、context switch、および workload の動作は latency/throughput に影響する可能性があります。固定された 1 つの原因を想定するのではなく測定してください。time-slicing には replica 間の memory/fault isolation はありません。inference をオーバーサブスクライブしても自動的に安全になるわけではなく、training が共有と常に互換性がないわけでもありません。

## H100/H200 仕様のコンテキスト

| NVIDIA 仕様 | H100 **SXM** | H200 **SXM** |
|---|---|---|
| GPU メモリ | 80 GB HBM3 | 141 GB HBM3e |
| 公表メモリ帯域幅 | 3.35 TB/s | 4.8 TB/s |
| MIG | 最大 7、モデル固有の profile | 最大 7、モデル固有の profile |

これらは vendor のハードウェア仕様であり、この Kubernetes 環境の測定値ではありません。H100 NVL/PCIe variant は異なるキャパシティ/帯域幅を持ちます。SXM 行をすべての H100 に一般化しないでください。より大きなメモリにより workload を収められる場合がありますが、実際の inference/training パフォーマンスはモデル、精度、batching、software、interconnect、および競合にも依存します。

## 割り当てを確認し、安全にクリーンアップする

明示的な administrator kubeconfig/context を使用し、ハードウェア/Pod diagnostics を非公開に保ってください。

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceslices -o json > gpu-slices.json
jq '[.items[] | select(.spec.driver == "gpu.nvidia.com") |
  {name: .metadata.name, node: .spec.nodeName,
   devices: [.spec.devices[] | {name, attributes, capacity}]}]' gpu-slices.json
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceclaims -n ai-workloads -o json > gpu-claims.json
jq '[.items[] | {name: .metadata.name,
  allocation: .status.allocation.devices.results,
  reservedFor: .status.reservedFor}]' gpu-claims.json
```

現在の ResourceClaims には、汎用的に保存される `Pending → Allocated → Bound` phase enum はありません。allocation result、reservation、Pod scheduling/event、および driver preparation を確認してください。reservation は、container が GPU を正常に使用した証明ではありません。古い `resourceHandles` の例は、現在の structured-allocation 形式ではありません。

ログを確認するときは、選択した driver release によって実際にレンダリングされた workload name/label を使用してください。Operator 管理 DRA とスタンドアロン DRA release が、古い `app=nvidia-dra-driver` selector を共有するとは限りません。

結果を取得した後に、所有するテスト Job/Pod のみを削除してください。生成された claim がリリースされ、device の準備が解除されていることを確認してください。保持された claim や finalizer は、停止した container より長く残ることがあります。workload が claim の準備解除に kubelet plugin をまだ必要としている間は、DRA kubelet plugin を削除しないでください。

Operator 管理 DRA では、その順序付けられた Helm hook/finalizer の teardown に従ってください。`helm uninstall --no-hooks` を使用したり、共有 claim の finalizer を無批判に削除したり強制削除したりしないでください。ハードウェアを再利用する前に、失敗した cleanup を resource owner と調整してください。

## 主な参照資料

- [AWS NVIDIA device management](https://docs.aws.amazon.com/eks/latest/userguide/device-management-nvidia.html)
- [AWS Hybrid inference: scoped device plugin](https://aws.amazon.com/blogs/containers/run-genai-inference-across-environments-with-amazon-eks-hybrid-nodes/)
- [GPU Operator platform/component matrix](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html)
- [GPU Operator DRA/GPUCluster workflow](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/dra-intro-install.html)
- [DRA driver 0.5.0 prerequisites](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/prerequisites.md)
- [DRA ResourceSlice attributes](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/reference/resourceslice-attributes.md)
- [Kubernetes DRA](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/)
- [NVIDIA device plugin 0.20.0](https://github.com/NVIDIA/k8s-device-plugin/tree/v0.20.0)
- [MIG profiles](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-mig-profiles.html) と [time-slicing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)
- [H100 specifications](https://www.nvidia.com/en-us/data-center/h100/) と [H200 specifications](https://www.nvidia.com/en-us/data-center/h200/)

< [前へ: Node Bootstrap](./04-node-bootstrap.md) | [目次](./README.md) | [次へ: Workload Placement](./06-workload-placement.md) >
