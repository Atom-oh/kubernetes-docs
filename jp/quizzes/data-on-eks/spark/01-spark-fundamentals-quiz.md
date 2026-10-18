# Kubernetes 上の Spark 基礎クイズ

Deployment mode、責任範囲、resource、dynamic allocation、終了条件を確認します。

## 1. Spark 4.2 がサポートする Kubernetes deployment mode と、その前提条件は何ですか？

<details>
<summary>回答を表示</summary>

Cluster mode と client mode の両方をサポートし、Spark 4.2 では Kubernetes 1.34+ が文書化されています。Client mode は2.4からあり、notebook 専用ではありません。kubectl は実際の API server と互換性がある必要があります。

</details>

## 2. Executor pod を要求するのは誰で、pod を配置/起動し、Spark task を割り当てるのはそれぞれ誰ですか？

<details>
<summary>回答を表示</summary>

Driver が API 経由で executor pod を要求します。Kubernetes scheduler が node を選び、kubelet が container を起動します。Driver の Spark scheduler が、登録済み executor に task を割り当てます。API server も driver も、Kubernetes の scheduling を置き換えません。

</details>

## 3. YARN 層を取り除けば、インフラ運用や driver の権限は不要になりますか？

<details>
<summary>回答を表示</summary>

いいえ。Node、Kubernetes、image、network、storage、observability は引き続き必要です。Submitter の API authentication と driver の namespace RBAC も必要です。この例では executor 用に別の service account を使います。AWS data permission と Kubernetes RBAC は別のものです。

</details>

## 4. Dynamic-allocation/shuffle-tracking の flag を常に明示的に両方設定する必要がありますか？

<details>
<summary>回答を表示</summary>

いいえ。Dynamic allocation は有効にしますが、shuffle tracking は Spark 4.2 ではデフォルトで true であり、3.0から存在します。標準の Kubernetes ESS はサポートされません。条件に応じて decommission による保持や、適切な reliable ShuffleDataIO が代替になります。複数の仕組みを重ねると、削除が遅れる場合があります。

</details>

## 5. Decommission を有効にすると、どのような終了処理が追加されますか？

<details>
<summary>回答を表示</summary>

Spark 4.2 は /opt/decom.sh を実行する preStop hook を挿入します。公式 image にこの script が含まれており、executor JVM に SIGPWR を送って待機します。Block migration には、storage decommission 設定に加えて、実際の保存先、時間、capacity も必要です。

</details>

## 6. terminationGracePeriodSeconds を60に増やせば、すべての block が移行されますか？

<details>
<summary>回答を表示</summary>

いいえ。Spark 4.2 は template の値を上書きするため、spark.kubernetes.executor.terminationGracePeriodSeconds=60s も設定します。デフォルトの30秒も設定値の60秒も preStop を含み、使える時間の上限にすぎません。強制終了、Spot の期限、移行先 capacity の不足によって完了できない場合があります。

</details>

## 7. allocation.batch.size と initial/minimum executor count はどう違いますか？

<details>
<summary>回答を表示</summary>

batch.size は pod request の batch 数を制御します。Min/initial/max は executor の範囲と起動数を定義し、既存の executor.instances も考慮されます。この例の min2/initial3/instances3 は3個で開始します。Node provisioning は別の処理です。

</details>

## 8. Spark core、CPU limit、memory、pod template はどのように解釈すべきですか？

<details>
<summary>回答を表示</summary>

Core はデフォルトの CPU request と executor の task capacity に関係し、CPU limit には limit.cores が必要です。JVM の例では heap 1 GiB と overhead の最小値384 MiBから、request/limit は1408 MiBになります。Template は submitter が読み取り、Spark が組み立てます。kubectl apply する不完全な pod ではありません。

</details>

## 9. Shuffle tracking と decommission を使う場合、何を引き続き確認する必要がありますか？

<details>
<summary>回答を表示</summary>

Tracking/idle timeout、強制終了、node capacity、再計算を確認します。Client mode では、到達可能な driver endpoint と、該当する場合は実際の driver pod owner も必要です。中間 block を保持しても、checkpoint、driver recovery、エンドツーエンドの exactly-once の代わりにはなりません。

</details>

---

[学習資料に戻る](../../../data-on-eks/spark/01-spark-fundamentals.md)
