# 運用、HA、マネージド Flink のクイズ

収集経路、メモリ/復旧の境界、マネージドサービスのサポートを確認します。

1. レビュー対象の Kubernetes HA リーダー選出では、どのリソースを使用しますか？

<details>
<summary>回答を表示</summary>

**回答:** Fabric8 ConfigMapLock を使い、Kubernetes コントロールプレーンの可用性に依存します。

**解説:** 別のリーダー選出サーバーを追加したり、常に Lease リソースを使用したりするわけではありません。ZooKeeper HA もサポート対象の代替方式です。

</details>

2. HA の ConfigMap、HA の storageDir、チェックポイントディレクトリには同じデータが保存されますか？

<details>
<summary>回答を表示</summary>

**回答:** ConfigMap にはリーダー情報/参照先、HA の storageDir には JobManager の復旧メタデータ/ジョブグラフ、チェックポイントディレクトリにはチェックポイント状態が保存されます。

**解説:** HA パスを 1 つ設定しただけでは、すべての状態ファイルや復旧権限を準備できるわけではありません。

</details>

3. HA 専用の ConfigMap Role で、Native Flink に必要な権限すべてを付与できますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。ネイティブリソース管理には、Pod/Service などへの適切な権限も必要です。

**解説:** 呼び出し元ごとの要件を確認し、API エラー、ログ、再起動を調べてください。失敗が常にサイレントになるわけではありません。

</details>

4. Flink とノードのオートスケーラーが主に調整するものは何ですか？

<details>
<summary>回答を表示</summary>

**回答:** それぞれ、Vertex の並列度とノード容量です。

**解説:** 負荷、クォータ、状態の復旧、配置がそれぞれのスケーリングを関連付けます。Flink が常に先に動作するとは限りません。

</details>

5. Pending の Pod ごとに Karpenter がノードを必ず作成しますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。スケジュール不能な Pod と、イメージ取得、PVC、アドミッションなどが原因の Pod を区別してください。

**解説:** 制約、リソースリクエスト、インスタンスの提供状況、クォータによっては、プロビジョニングできない場合があります。

</details>

6. Flink の安定化時間より長い集約遅延を設定すれば、中断を防げますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。ノード障害、Spot の回収、構成のずれは個別に発生し得るため、保証にはなりません。

**解説:** プロビジョニング、復元、バックログの解消、中断/PDB ポリシーを組み合わせてテストしてください。

</details>

7. マネージド Flink 2.3 をサポートしていれば、上流のすべての機能を利用できますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。Java 17/Python 3.12 の組み合わせと、サービス固有の除外事項を確認してください。

**解説:** 制約には Java 21、ForSt、Native S3、カスタムテレメトリ、Studio が含まれます。AWS インフラストラクチャの HA と、アプリケーション/状態に関する責任を分けて考えてください。

</details>

8. マネージド型の KPU コストを EKS Spot とどのように比較すべきですか？

<details>
<summary>回答を表示</summary>

**回答:** 同等のスループット、レイテンシ、復旧目標を満たす場合の総コストと運用を比較します。

**解説:** KPU ではオーケストレーションと関連するストレージ/ネットワークのコストを、Spot では中断/復旧コストを含めてください。

</details>

9. RocksDB のマネージドメモリとネットワークバッファーは、1 つのプールを共有しますか？

<details>
<summary>回答を表示</summary>

**回答:** 別々の予算領域です。

**解説:** 確認した 4GiB の構成では、マネージドメモリの割合を 0.4 から 0.5 に変更してもネットワーク側は変わらず、タスクヒープが減りました。予算は実測 RSS とは異なります。

</details>

10. PodMonitor はあるのにターゲットがない場合、何を確認すべきですか？

<details>
<summary>回答を表示</summary>

**回答:** Prometheus の monitor/namespace セレクター、実際の Pod ラベル、名前付きポート、対象 namespace、ディスカバリー権限です。

**解説:** このチャートでは Operator Pod にデフォルトの instance ラベルがありませんでした。Deployment のメタデータが自動的に Pod ラベルになるわけではありません。

</details>

11. block-cache-usage は比率ですか。また、Flink Counter は常に Prometheus Counter ですか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。キャッシュ使用量はバイト単位で、レビュー対象の reporter は Flink Counter を Gauge としてエクスポートします。

**解説:** キャッシュ容量/ヒット/ミスも解釈してください。Histogram は Summary に対応します。エクスポートされた TYPE とラベルを確認してください。

</details>

12. Operator が管理する CR に kubernetes.cluster-id を直接設定すべきですか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。1.15 のバリデーターで禁止されています。ID は CR の名前/namespace から管理されます。

**解説:** 低レベルの CLI 構成をそのままコピーしないでください。kubernetes.namespace と high-availability.cluster-id も制限対象です。

</details>

13. JobManager レプリカが 2 つあり、チェックリストが完了していれば、即時かつ中断のない復旧が保証されますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。リーダー選出、ノード/AZ の配置、ストレージ、状態の復元、再生時間、実際の結果を検証してください。

**解説:** デフォルト設定を維持することが適切な場合もあります。設定だけでなく、測定した SLO/復旧結果と運用上の責任分担が重要です。

</details>

---

[学習教材に戻る](../../../data-on-eks/flink/04-operations-ha.md) | [Flink](../../../data-on-eks/flink/README.md)
