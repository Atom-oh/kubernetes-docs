# EKS 上の Flink 詳細ガイド

Apache Flink は、有界および無界の stream を処理する、状態を持つ分散エンジンです。
JobManager は実行と recovery を調整し、TaskManager は operator task を実行してデータを交換します。Checkpoint の一貫性と、外部 sink での exactly-once 動作には、それぞれ別の要件があります。第3章では source、state、sink を合わせて説明します。

> **最終更新日**: September 12, 2026
> 統合の基準: **Flink 2.2.1 / Java 17 / Operator 1.15.0**。

第3章の Iceberg の例では、runtime との整合性を取るため、別途 **Flink 2.1.3 / Iceberg 1.11.0** を使用します。
S3 plugin の SDK サポートとマネージドサービスとの差異について、各章の制限事項を確認してください。

最新の安定版 Flink release は 2.3.0 です。これらの例では、公開されている Operator および connector の互換性表と合わせて確認する基準として、2.2.1 を使用します。
CRD enum が version string を受け付けることは、統合の互換性を証明するものではありません。
Kubernetes/kubectl のバージョンは、現在の EKS サポートと version-skew policy に基づいて選択してください。「Kubernetes 1.21+」は、現行 EKS でのサポートを保証するものではありません。

## Kubernetes 上で何を誰が管理するか

- **FlinkDeployment** は Application または Session cluster を定義します。
- **FlinkSessionJob** は既存の管理対象 Session cluster に送信する job を定義します。
- Operator は cluster/job の lifecycle を reconcile し、**Native と Standalone の両 mode** をサポートします。
- Native mode では、JobManager の Kubernetes ResourceManager が TaskManager pod を要求/解放します。Standalone mode では、Operator などの外部 manager が Kubernetes resource を管理します。
- Task slot は CPU core とも、operator subtask 1つとも同じではありません。Chaining と slot sharing により、複数の operator を1つの slot に配置できます。State、memory、CPU はそれぞれ個別にサイズを決めてください。

以下は **Native mode の論理的な制御フロー** を示します。Pod の解放時期は idle timeout、capacity の必要性、cleanup policy に左右されます。Job が完了しても node のコストがすぐになくなるわけではありません。

![Native mode における Flink Operator、Kubernetes API、JobManager、TaskManager。](../../.gitbook/assets/en-data-on-eks-flink-readme-0.png)

[インタラクティブな図](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-flink-readme-0.html)

## 章の一覧

1. [アーキテクチャ](01-architecture.md): process/slot sharing と、Application/Session と Native/Standalone の軸。
2. [Flink Kubernetes Operator](02-flink-kubernetes-operator.md): CRD、インストール、upgrade、autoscaling。
3. [State、checkpoint、streaming](03-state-checkpointing-streaming.md): backend、recovery、connector の実際の保証。
4. [運用と HA](04-operations-ha.md): metric、HA storage、node capacity、マネージドサービスとの比較。

ここでは Operator による宣言的管理を主な経路として扱い、CLI の例ではその下で動く runtime を説明します。Operator を使わずに実行する方法もサポートされています。

## 参考資料

- [Flink release と connector の互換性](https://flink.apache.org/downloads/)
- [Flink 2.2 のアーキテクチャ](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/concepts/flink-architecture/)
- [Flink 2.2 の deployment mode](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/overview/)
- [Native Kubernetes deployment](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/resource-providers/native_kubernetes/)
- [Java の互換性](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/java_compatibility/)
- [Operator 1.15.0 の deployment mode](https://github.com/apache/flink-kubernetes-operator/blob/release-1.15.0/docs/content/docs/custom-resource/overview.md)

[クイズ](../../quizzes/data-on-eks/flink/01-architecture-quiz.md)
