# パート 4: パフォーマンスとコストの調整クイズ

基準: Spark 4.2.0 / Karpenter 1.14 · 2026年9月。

## 1. shuffle では R シリーズと NVMe が常に最速ですか？

<details>
<summary>回答を表示</summary>

いいえ。タスク/ステージの所要時間、spill、shuffle fetch の待機時間、偏り、CPU/メモリ/ディスク/ネットワークのボトルネックを測定してください。処理に成功したジョブあたりの利用可能容量とコストを比較します。他のインスタンスファミリーや EBS が本質的に不適切というわけではありません。

</details>

## 2. Graviton を評価するときは何を確認すべきですか？

<details>
<summary>回答を表示</summary>

Spark イメージ、JNI、コーデック、BLAS、Python wheel、プラグインで arm64 がサポートされていることを確認し、代表的なワークロードをベンチマークしてください。既にテスト済みのマルチアーキテクチャイメージを使えば、独自にビルドせずに済む場合があります。

</details>

## 3. マウントされていない NVMe デバイスをフォーマットしても安全ですか？

<details>
<summary>回答を表示</summary>

いいえ。Nitro では EBS も NVMe として表示され、マウントされていないディスクにデータやパーティションが含まれる場合があります。デバイス名とマウント状態だけでは、破棄可能なインスタンスストアだとは判断できません。

</details>

## 4. AL2023 で instanceStorePolicy: RAID0 は何を構成しますか？

<details>
<summary>回答を表示</summary>

Karpenter は NodeConfig を使って kubelet/containerd のエフェメラルストレージ用にインスタンスストア RAID0 を構成し、割り当て可能な容量を提示します。RAID0 はバックアップではありません。NodeClass には AMI、IAM、サブネット、その他の設定も必要です。

</details>

## 5. このラボで hostPath なしに NVMe スクラッチ領域を使えるのはなぜですか？

<details>
<summary>回答を表示</summary>

準備済みの NodeClass では kubelet のファイルシステムにインスタンスストアを使用するため、ディスクベースの emptyDir もそこを利用します。別のノード構成や tmpfs を使う場合は、バックエンドのストレージが変わります。

</details>

## 6. Spark が認識するスクラッチボリュームの名前は何ですか？

<details>
<summary>回答を表示</summary>

spark-local-dir-scratch のように、プレフィックスが spark-local-dir- で、その後にサフィックスが続く名前です。以前の spark-local-dir という名前は一致せず、同じマウントパスに追加の emptyDir が作られることがあります。

</details>

## 7. emptyDir の sizeLimit はディスク容量を予約しますか？

<details>
<summary>回答を表示</summary>

いいえ。requests、ノードの割り当て可能容量、他の Pod、ログ、書き込み可能レイヤーを考慮してください。ノードが先に容量不足になる可能性があります。メモリベースの tmpfs はメモリ予算を消費します。

</details>

## 8. オンデマンドのドライバーと Spot のエグゼキューターを分けても保証されないことは何ですか？

<details>
<summary>回答を表示</summary>

ドライバーの障害/構成のずれ/有効期限をなくすわけではなく、エグゼキューターの喪失を無害にするわけでもありません。Spot のみを選択する設定ではオンデマンドにフォールバックできず、容量不足時に Pod が Pending のままになることがあります。

</details>

## 9. taint/toleration とノードセレクターはどう違いますか？

<details>
<summary>回答を表示</summary>

toleration は taint のあるノードを使用できるようにし、セレクターは一致するノードを選びます。他の Pod も同じ toleration を持つ場合があります。また、NoSchedule は既存の Pod を退避させません。

</details>

## 10. Spot の警告と decommission フラグがあれば、移行の完了が保証されますか？

<details>
<summary>回答を表示</summary>

いいえ。警告はベストエフォートであり、休止状態への移行には 2 分間の猶予はありません。EventBridge/SQS/中断処理、ドレイン、フック/シグナル、時間、ピア容量、ネットワークのすべてが重要です。Pod の 120 秒の猶予によって、クラウド側の有効期間が延びるわけではありません。

</details>

## 11. リモートストレージであれば、どれでも自動的に shuffle のフォールバックになりますか？

<details>
<summary>回答を表示</summary>

いいえ。spark.storage.decommission.fallbackStorage.path と、動作するファイルシステム/権限を設定してください。RDD キャッシュの復旧と shuffle の復旧は異なります。再計算、フェッチ失敗、再試行上限によってジョブが失敗する場合もあります。

</details>

## 12. DRA と Karpenter はどのシグナルを使いますか？

<details>
<summary>回答を表示</summary>

DRA は Spark タスクのバックログやアイドル/キャッシュ/shuffle の状態からエグゼキューター数を調整します。Karpenter は Pod のリクエストとスケジューリング制約からノードをプロビジョニングします。metrics-server は必須ではありません。allocation.batch.size は Kubernetes の割り当て側が作成する速度を制御します。

</details>

## 13. consolidateAfter を executorIdleTimeout より大きく設定すれば、DRA が必ず先に解放しますか？

<details>
<summary>回答を表示</summary>

いいえ。タイマーは異なるイベントを起点とし、shuffle/キャッシュがエグゼキューターを保持する場合があります。WhenEmpty を使うと通常のワークロード Pod の集約は抑えられますが、構成のずれ、有効期限、Spot の終了は別の問題です。

</details>

## 14. JVM ヒープ 4g と cores=2 が、Pod のメモリと CPU の上限全体ですか？

<details>
<summary>回答を表示</summary>

いいえ。この例では、デフォルトのオーバーヘッド 409MiB が加わり、合計メモリは 4505MiB になります。cores はデフォルトの CPU request と Spark の並列数に影響します。spark.kubernetes.executor.limit.cores で CPU 上限を明示的に設定してください。PySpark、オフヒープメモリ、明示的なオーバーヘッドは別途確認してください。

</details>

[ガイド](../../../data-on-eks/spark/04-performance-tuning.md)
