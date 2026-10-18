# EKS 上のモデル学習クイズ

現行 API、ジョブランチャー、復旧範囲に関する 15 問です。

## 1. テンソル並列化では何を分割しますか？

<details>
<summary>回答と解説</summary>

各層内のテンソル演算と重みです。データ並列化 (DP) はレプリカ間でデータを分割し、パイプライン並列化 (PP) は層をステージに分けます。エキスパート並列化はエキスパートとトークンの振り分けを分割します。それぞれ通信方式が異なります。
</details>

## 2. 200B モデルとグローバルバッチはどのように計画すべきですか？

<details>
<summary>回答と解説</summary>

モデルの規模だけを理由に 3D 並列化を必須とせず、学習状態、活性化、通信、デバイスメッシュを考慮してください。TP8×PP4×DP2 は 64 ランクですが、microbatch 1×accumulation 32×DP2 ではグローバルバッチは 64 になります。
</details>

## 3. slurmctld と slurmdbd は状態をどのように分担しますか？

<details>
<summary>回答と解説</summary>

slurmctld は実行中のジョブ、ノード、パーティションの状態、スケジューリング、StateSaveLocation を管理します。slurmdbd はアカウンティングデータベースのレコードを扱い、コントローラーの復旧状態を代替するものではありません。
</details>

## 4. Slinky 1.2.3 のコンピュートグループ API とは何ですか？

<details>
<summary>回答と解説</summary>

slinky.slurm.net/v1beta1 の NodeSet で、Controller の参照/テンプレートを使用します。デフォルトでは StatefulSet 形式でスケールし、任意で DaemonSet 形式にもできます。DaemonSet モードでは replicas は無視されます。kind は SlurmNodeSet ではありません。
</details>

## 5. FI_PROVIDER=efa だけで EFA 経由の NCCL は有効になりますか？

<details>
<summary>回答と解説</summary>

いいえ。EFA インターフェイス、driver/libfabric/aws-ofi-nccl、device plugin による Pod への割り当て、security group、同一 AZ への配置が必要です。ログと collective test で実際の通信経路を確認してください。400 Gbps が常に利用できるとは限りません。
</details>

## 6. BioNeMo3.0.0 で確認すべきことは何ですか？

<details>
<summary>回答と解説</summary>

BioNeMo Recipes で、モデル、TransformerEngine、学習レシピがサポートされているか確認してください。以前の 1.5 MegaMolBART モジュールを未検証のまま再利用しないでください。イメージ、データ、モデルのリビジョン、デバイス、収束、生物学的評価を検証します。
</details>

## 7. Optimum Neuron Trainer はすべての HF model の training を保証しますか？

<details>
<summary>回答と解説</summary>

いいえ。バージョンごとの学習モデル実装、設定、SDK/PyTorch、ハードウェア、データ、collator の互換性を確認してください。推論のサポートと学習のサポートは異なります。事前学習済みモデルと未定義のデータセットだけでは、テンソル並列学習は実装できません。
</details>

## 8. FSx と S3 の integration はどのように検証すべきですか？

<details>
<summary>回答と解説</summary>

静的マウントと動的プロビジョニングを区別し、DRA、インポート/エクスポートのポリシー、処理完了、権限を確認してください。EFS PVC の容量はクォータではなく、ローカルストレージだけでは S3 の耐久性は保証されません。
</details>

## 9. Volcano minAvailable:4 は4つの node を必要としますか？

<details>
<summary>回答と解説</summary>

いいえ。Pod またはメンバーの数を指定します。3 台のノードに 4 個の Pod を配置できる場合もあります。最小メンバー数、必要リソース、gang plugin を確認してください。同時起動や学習の成功が保証されるわけではありません。
</details>

## 10. BF16 は FP16 とどのように異なりますか？

<details>
<summary>回答と解説</summary>

指数部は 8 bit、仮数部は 7 bit です。指数部のビット数は FP32 と同じですが、精度や表現可能な最大有限値が同じという意味ではありません。通常、FP16 のような loss scaling は不要ですが、ハードウェア、演算、収束を検証してください。autocast はすべての学習状態を変換するわけではありません。
</details>

## 11. activation checkpoint と recovery checkpoint はどのように異なりますか？

<details>
<summary>回答と解説</summary>

activation checkpointing は、逆伝播時に再計算を行う代わりにメモリ使用量を抑えます。これはディスク上に保存するモデル/optimizer/RNG の復旧状態とは異なります。3～4 倍の削減を前提とせず、use_reentrant、RNG/状態、勾配を確認してください。
</details>

## 12. ZeRO Stage3 は自動的に CPU に offload しますか？

<details>
<summary>回答と解説</summary>

いいえ。optimizer の状態、勾配、パラメーターを分割します。offload は別途設定してください。メモリ削減量は無制限に増えるわけではなく、DP のサイズ、状態、バッファー、活性化に依存します。
</details>

## 13. MPIJob slotsPerWorker は何を確立しますか？

<details>
<summary>回答と解説</summary>

Worker hostfile に記録するスロット数です。実際のプロセス数は mpirun -np、マッピング、ランチャーの設定に依存します。1 ランク/GPU の割り当てには明示的な設定が必要です。Operator 0.8.2 は v2beta1 API を使用します。
</details>

## 14. checkpoint frequency と recovery はどのように検証すべきですか？

<details>
<summary>回答と解説</summary>

保存にかかる時間、障害率、許容できる作業損失、保持コストに基づいて間隔を選択します。状態全体、マニフェスト、チェックサム、リモート保存の完了、実際の再開を確認してください。このガイドでは、中断せず 4 回更新した場合と、2 回更新した後に再開した場合の CPU 計算結果が一致することを確認します。
</details>

## 15. 同一 AZ の EFA placement と Karpenter disruption budget は何を意味しますか？

<details>
<summary>回答と解説</summary>

通信する worker が実際に同じ AZ に配置されるよう、Pod と NodePool の制約を組み合わせます。パフォーマンス向上にはプレイスメントグループが推奨されます。Budget 0 は自発的な中断を制限しますが、Spot の回収、障害、強制終了は防ぎません。
</details>

[ガイドに戻る](../../ai-ml/05-model-training.md)
