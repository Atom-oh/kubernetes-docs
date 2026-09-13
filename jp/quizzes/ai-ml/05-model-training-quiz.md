# EKS での Model Training クイズ

現在の API、launcher、および recovery boundary に関する15問です。

## 1. tensor parallelism は何を分割しますか？

<details>
<summary>回答と解説</summary>

layer 内の tensor operation と weight です。DP は replica 間で data を分割し、PP は layer stage を分割し、expert parallelism は expert/token dispatch を分割します。これらの communication はそれぞれ異なります。
</details>

## 2. 200B model と global batch はどのように計画すべきですか？

<details>
<summary>回答と解説</summary>

size だけを理由に3Dを必須としないでください。training state、activation、communication、および device mesh を考慮します。TP8×PP4×DP2 は64rank ですが、microbatch1×accumulation32×DP2 では global batch64 になります。
</details>

## 3. slurmctld と slurmdbd の state responsibility はどのように異なりますか？

<details>
<summary>回答と解説</summary>

slurmctld は実行中の job/node/partition state、scheduling、および StateSaveLocation を管理します。slurmdbd は accounting database record を処理し、controller recovery state の代わりにはなりません。
</details>

## 4. Slinky1.2.2 の compute-group API とは何ですか？

<details>
<summary>回答と解説</summary>

Controller reference/template を使用する slinky.slurm.net/v1beta1 NodeSet です。デフォルトでは StatefulSet-style、または任意で DaemonSet-style の scaling です。DaemonSet mode では replicas は無視されます。kind は SlurmNodeSet ではありません。
</details>

## 5. FI_PROVIDER=efa だけで EFA 経由の NCCL は有効になりますか？

<details>
<summary>回答と解説</summary>

いいえ。EFA interface、driver/libfabric/aws-ofi-nccl、device plugin/Pod allocation、security group、および同一 AZ への placement が必要です。log/collective test を使用して実際の transport を確認してください。400Gbps は常に利用できるわけではありません。
</details>

## 6. BioNeMo3.0.0 で確認すべきことは何ですか？

<details>
<summary>回答と解説</summary>

BioNeMo Recipes における Model/TransformerEngine/training-recipe support です。以前の1.5 MegaMolBART module を未検証のまま再利用しないでください。image/data/model revision、device、convergence、および biological evaluation を検証します。
</details>

## 7. Optimum Neuron Trainer はすべての HF model の training を保証しますか？

<details>
<summary>回答と解説</summary>

いいえ。version 化された training-model implementation、configuration、SDK/PyTorch、hardware、data、および collator を対応させます。inference support は training support と異なります。pretrained model と未定義の dataset だけでは TP training は実装されません。
</details>

## 8. FSx と S3 の integration はどのように検証すべきですか？

<details>
<summary>回答と解説</summary>

static mount と dynamic provisioning を区別し、DRA/import/export policy、completion、および permission を検証します。EFS PVC capacity は quota ではなく、local storage だけでは S3 durability は確立されません。
</details>

## 9. Volcano minAvailable:4 は4つの node を必要としますか？

<details>
<summary>回答と解説</summary>

いいえ。これは Pod/member を数えます。3つの node で4つの Pod を配置できる場合があります。minimum-member/resource condition と gang plugin を確認してください。これは同時 startup や training success を保証しません。
</details>

## 10. BF16 は FP16 とどのように異なりますか？

<details>
<summary>回答と解説</summary>

exponent は8bit、mantissa は7bit です。exponent-bit count は FP32 と同じですが、precision や正確な maximum finite value が同じという意味ではありません。FP16-style loss scaling は通常不要ですが、hardware/operation/convergence を検証してください。autocast はすべての training state を cast するわけではありません。
</details>

## 11. activation checkpoint と recovery checkpoint はどのように異なりますか？

<details>
<summary>回答と解説</summary>

activation checkpointing は backward 時の再計算を増やす代わりに memory 使用量を削減します。これは disk 上の model/optimizer/RNG recovery state とは異なります。固定の3–4x の節約を前提とせず、use_reentrant、RNG/state、および gradient を確認してください。
</details>

## 12. ZeRO Stage3 は自動的に CPU に offload しますか？

<details>
<summary>回答と解説</summary>

いいえ。optimizer state、gradient、および parameter を partition します。offload は別途設定します。memory reduction は無制限の scaling ではなく、DP size、state、buffer、および activation に依存します。
</details>

## 13. MPIJob slotsPerWorker は何を確立しますか？

<details>
<summary>回答と解説</summary>

Worker hostfile slot です。実際の process count は mpirun -np/mapping および launcher setup に依存します。one-rank-per-GPU binding には明示的な configuration が必要です。Operator0.8.2 は v2beta1 API を使用します。
</details>

## 14. checkpoint frequency と recovery はどのように検証すべきですか？

<details>
<summary>回答と解説</summary>

save latency、failure rate、許容できる lost work、および retention cost に基づいて interval を選択します。complete state/manifest/checksum、remote completion、および実際の resume を確認します。この guide では、4回の uninterrupted update の同一 CPU result と、2回後に resume した結果を確認します。
</details>

## 15. 同一 AZ の EFA placement と Karpenter disruption budget は何を意味しますか？

<details>
<summary>回答と解説</summary>

communication する worker が実際に AZ を共有するよう、Pod/NodePool constraint を接続します。performance のために placement group を推奨します。Budget0 は voluntary disruption を制限しますが、Spot reclamation、failure、または forced termination は制限しません。
</details>

[ガイドに戻る](../../ai-ml/05-model-training.md)
