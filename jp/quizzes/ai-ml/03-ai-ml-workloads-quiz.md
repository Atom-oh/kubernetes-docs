# AI/ML ワークロードクイズ

リソース割り当て、トレーニング/サービング、ストレージ、ネットワーキング、セキュリティ、可観測性、コストの境界を復習しましょう。

## クイズ問題

### 1. NVIDIA device plugin によって公開される GPU を Pod はどのようにリクエストすべきですか？

- A. nvidia.com/gpu:0.5 を requests のみに設定する
- B. 整数の nvidia.com/gpu limits を指定し、requests も指定する場合は同じ値にする
- C. nvidia.com/gpu node annotation のみを追加する
- D. RuntimeClass に nvidia-mps という名前を付けて、自動的に共有を有効にする

<details>
<summary>回答を表示</summary>

**回答: B. 整数の nvidia.com/gpu limits を指定し、requests も指定する場合は同じ値にする**

limits のみを指定した場合、同じ値の requests が暗黙的に設定されます。割り当て可能な GPU 容量は node label ではありません。GPU Feature Discovery labels、MIG、MPS、time-slicing には個別の設定が必要です。共有スロットは GPU memory の一部を保証しません。

[割り当てと共有](../../ai-ml/01-ai-ml-workloads.md#nvidia-gpu-operator-and-device-allocation)
</details>

### 2. インストール済みのレガシー Kubeflow リソースで、TensorFlow の分散ロールを理解するものはどれですか？

- A. Deployment はすべての TF_CONFIG 値を自動的に作成する
- B. Job はトレーニングの成功と worker の同時配置を保証する
- C. TFJob はフレームワーク固有のロール/設定を提供する
- D. TFJob は Kubernetes に組み込まれており、インストールは不要である

<details>
<summary>回答を表示</summary>

**回答: C. TFJob はフレームワーク固有のロール/設定を提供する**

その CRD/controller をインストールし、restart policy、framework strategy、checkpoints、storage、networking を設定します。リカバリと gang scheduling は普遍的な保証ではありません。実際の実行コードを提供すれば、通常の Job でもトレーニングできます。

[Trainer とレガシー API](../../ai-ml/kubeflow/05-training-operator.md)
</details>

### 3. 既存の FSx for Lustre filesystem は、CSI を介してどのように接続すべきですか？

- A. Lustre CR と既存 ID を含む StorageClass を組み合わせる
- B. volumeHandle/dnsname/mountname を持つ静的 PV とバインド済み PVC を使用する
- C. SCRATCH_2 はすべての永続的な backup/throughput オプションをサポートする
- D. mount されていない /data に対する FIO は FSx を計測する

<details>
<summary>回答を表示</summary>

**回答: B. volumeHandle/dnsname/mountname を持つ静的 PV とバインド済み PVC を使用する**

静的アタッチメントは動的な filesystem 作成とは異なります。容量、IOPS/throughput、latency、access pattern、permissions、AZ/network、backups を比較します。実際に mount された volume 上の専用テストパスでベンチマークを実行します。

[静的および動的ストレージ](../../ai-ml/01-ai-ml-workloads.md#storage-and-caching)
</details>

### 4. AI/ML のリソース割り当ては、何を指針とすべきですか？

- A. すべてのトレーニング Job には GPU が必要である
- B. 計測された CPU/memory/GPU 使用量、model size、I/O、latency、throughput
- C. 常に最大のリソースをリクエストする
- D. requests を省略することが常に最も効率的である

<details>
<summary>回答を表示</summary>

**回答: B. 計測された CPU/memory/GPU 使用量、model size、I/O、latency、throughput**

CPU やその他の accelerator が適切な場合もあります。OMP/MKL thread 設定は、GPU 共有ではなく補助ライブラリに影響します。CUDA allocator 設定は Kubernetes の GPU 割り当て/分離とは異なります。VPA の効果は mode、restart の動作、workload との互換性に依存します。

[リソース配置](../../ai-ml/01-ai-ml-workloads.md#placement-and-topology)
</details>

### 5. KServe などの serving platform を選択する際、何を確認すべきですか？

- A. どの model URI もすぐに動作する
- B. Runtime image、model format、protocol、storage、deployment mode が要件に合致している
- C. 通常の Deployment では inference を提供できない
- D. すべての mode が同一の canary および scale-to-zero 動作を提供する

<details>
<summary>回答を表示</summary>

**回答: B. Runtime image、model format、protocol、storage、deployment mode が要件に合致している**

Deployment で inference server を実行できます。KServe Knative/Standard とバージョン管理された Seldon API には違いがあります。Explainability、processing、weighted routing、batch inference は、どの環境でも有効なデフォルトではありません。TorchServe は新規利用向けに維持されているデフォルトではありません。

[KServe の mode と runtime](../../ai-ml/kubeflow/06-kserve.md)
</details>

### 6. GPU utilization または request load に基づく HPA scaling に必要なものは何ですか？

- A. 割り当てられた nvidia.com/gpu は自動的に utilization の Resource metric になる
- B. 正しい labels、units、aggregation を備えた exporters と custom/external metrics adapters
- C. model accuracy が低い場合は replicas を増やす
- D. 加算的な scaling のため、同じ Deployment に複数の HPA をアタッチする

<details>
<summary>回答を表示</summary>

**回答: B. 正しい labels、units、aggregation を備えた exporters と custom/external metrics adapters**

標準の metrics-server Resource path は CPU/memory を公開します。GPU/request metrics には、個別の collection/adapters が必要です。Pod metrics は namespace/Pod labels にマッピングされる必要があります。グローバル平均ではこのマッピングが失われる可能性があります。scaling owner は 1 つにし、load/queue が latency percentile より適切な比例シグナルかどうかを検証します。

[HPA の例](../../ai-ml/01-ai-ml-workloads.md#hpa-and-metrics)
</details>

### 7. 分散トレーニングのネットワーキングについて正しい記述はどれですか？

- A. zone annotation のみで配置を制御する
- B. GPU hostPath mount が EFA/GPUDirect を設定する
- C. node-label 配置、hardware、drivers/plugins、communication libraries、network policies をまとめて検証する
- D. NCCL は常に MPI を通じてデータを転送する

<details>
<summary>回答を表示</summary>

**回答: C. node-label 配置、hardware、drivers/plugins、communication libraries、network policies をまとめて検証する**

EFA 上の NCCL は AWS OFI NCCL と libfabric を使用します。MPI は process を起動できます。Multus/SR-IOV、MTU、RDMA の設定は環境固有です。一般的な NIC の例は、すぐに使える EKS 設定ではありません。NetworkPolicy は必要な traffic をブロックすることで、可用性/パフォーマンスに影響する場合があります。

[分散トレーニングの境界](../../ai-ml/01-ai-ml-workloads.md#kubeflow-and-distributed-training)
</details>

### 8. model/data protection に関する正しい記述はどれですか？

- A. Secret の base64 は encryption である
- B. Kubernetes RBAC は S3/KMS permissions を付与する
- C. API RBAC、workload IAM、encryption/key management、file credentials、networking を個別に設定する
- D. 大きな model は Secrets に保存し、decryption keys はデフォルトで environment variables に保存する

<details>
<summary>回答を表示</summary>

**回答: C. API RBAC、workload IAM、encryption/key management、file credentials、networking を個別に設定する**

Secrets にはサイズ制限があり、base64 は encoding です。大きな model には、authorization/integrity checks を備えた object storage を使用します。Pod service account に、Secret volume を mount するための Secret get permission が常に必要とは限りません。API reads と kubelet volume delivery は異なります。PodSecurityPolicy は削除されました。現在の admission/PSS controls を使用します。

[データと model access](../../ai-ml/01-ai-ml-workloads.md#data-and-model-access)
</details>

### 9. ML service の可観測性では、何を区別すべきですか？

- A. GPU utilization が accuracy を決定する
- B. ServiceMonitor は Pod labels を直接選択する
- C. Service errors/latency/throughput、resource use、ground-truth model quality は別個のものである
- D. すべての container logs は Docker JSON である

<details>
<summary>回答を表示</summary>

**回答: C. Service errors/latency/throughput、resource use、ground-truth model quality は別個のものである**

ServiceMonitor は Service labels/named ports を選択します。latency に failures を含めるかを定義し、1 つの request を success と error の両方としてカウントしないようにします。quality には labels/ground truth が必要です。CRI framing と app JSON、Grafana datasource/panel schema、label 付き alert aggregation、zero-traffic 時の動作を検証します。

[メトリクスとログ](../../ai-ml/01-ai-ml-workloads.md#prometheus-and-grafana)
</details>

### 10. コスト最適化はどのように検証すべきですか？

- A. すべての workload に Spot を使用する
- B. 最新の instance が常に最も安価である
- C. 必要な performance、total cost、interruption recovery/checkpointing、実際の Pod/node reclamation を測定する
- D. 夜間には On-Demand rates が自動的に下がる

<details>
<summary>回答を表示</summary>

**回答: C. 必要な performance、total cost、interruption recovery/checkpointing、実際の Pod/node reclamation を測定する**

Pod が少なくなっても、EC2 が終了するとは限りません。availability、quotas、AMI/drivers、NodePool limits を確認します。トレーニングの taints には一致する tolerations が必要です。CPU/GPU の混在 groups は EKS Hybrid Nodes ではありません。未使用の Autoscaler ConfigMap を作成しても controller flags は変わりません。

[Spot と node provisioning](../../ai-ml/01-ai-ml-workloads.md#spot-and-node-provisioning)
</details>

---

[学習教材に戻る](../../ai-ml/01-ai-ml-workloads.md)
