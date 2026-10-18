# Kubernetes 上の Flink アーキテクチャクイズ

Flink 2.2.1 / Operator 1.15.0 における実行 role とリソース境界を確認します。

1. JobManager は常に初期 graph を構築し、client は計算を一切行わないのですか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。Application の main() は JM 上で実行されますが、通常の 2.2 Session CLI の送信では、client 側で graph を構築します。

**解説:** JM は実行、slot、checkpoint、recovery を調整し、TM は task を実行します。User main() 自体が JM のリソースを消費することもあります。

</details>

2. TaskManager の slot が4つなら、operator subtask は最大4つですか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。Chaining と slot sharing によって、複数の operator を1つの slot に配置できます。

**解説:** 従来の固定 slot は主に managed memory の割り当て単位であり、CPU core や独立した CPU 分離の境界ではありません。

</details>

3. Application mode では常に Job ごとに1つの cluster が作成され、共有 EKS リソースは完全に分離されますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。1つの application/main() から複数の job を作成でき、node、network、storage、quota が共有される場合があります。

**解説:** Application level の lifecycle/JVM 分離は役立ちますが、絶対的な分離ではありません。複数の execute に対する 2.2 の Application HA の制限を確認してください。

</details>

4. 既存の Session cluster に送信すると、常に直ちに実行が始まりますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。Cluster の起動による遅延は減らせますが、slot、CPU、状態の recovery、共有負荷によって実行が遅れる場合があります。

**解説:** Session job は JM/TM のリソースを共有します。1つの TM の障害が、その TM を使う複数の job に影響することがあります。

</details>

5. この章で Per-Job を、現行の3つ目の Native Kubernetes mode として数えるべきですか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。ここで扱う lifecycle の選択肢は Application と Session で、Per-Job は過去の方式です。

**解説:** Application/Session と、Native/Standalone の resource management の選択肢は、別々の分類です。

</details>

6. Native TaskManager pod と、それを実行する EKS node は誰が管理しますか？

<details>
<summary>回答を表示</summary>

**回答:** Flink の Kubernetes ResourceManager が API 経由で TM pod を要求し、Karpenter/Cluster Autoscaler が別途 node capacity を管理します。

**解説:** TM が解放されるタイミングは、idle timeout、resource profile、需要に左右されます。Job が完了しても、すべての pod/node が直ちに削除されるわけではありません。

</details>

7. Standalone-on-Kubernetes の TaskManager 数は、手動で YAML を編集した場合にしか変更できませんか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。Operator のような外部 controller が Kubernetes resource を reconcile できます。

**解説:** Native resource management とは異なり、Flink runtime が TM pod を直接要求することはありません。HA などの機能に必要な API 権限は、別途評価してください。

</details>

8. Operator 1.15.0 の2つの cluster/job CR は何ですか？ また、Native mode のみをサポートしますか？

<details>
<summary>回答を表示</summary>

**回答:** FlinkDeployment と FlinkSessionJob で、Native と Standalone の両方をサポートします。

**解説:** Deployment は Application/Session cluster を定義し、SessionJob は既存の管理対象 Session cluster を指定します。Version enum に含まれるだけでは、integration の互換性を証明できません。

</details>

---

[学習資料に戻る](../../../data-on-eks/flink/01-architecture.md)
