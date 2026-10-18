# DAGパターンとKubernetesPodOperatorのクイズ

Airflow 3.3.1とKubernetes provider 10.21.0に基づきます。実行構造、マージ動作、権限、バンドルのバージョン管理、検証の限界を確認してください。

## 概念

1. CeleryExecutorで同期KPOタスクを実行するとき、新しいワークロードPodを作成するのはどのプロセスですか？

<details>
<summary>回答を表示</summary>

**回答:** KPOは、既存のCelery workerからKubernetes APIを呼び出します。

**解説:** ワークロードは別のPodで実行されます。複数のタスクが同じworker Podを共有できます。また、ワークロードのイメージにAirflowが必要とは限りません。

</details>

2. CeleryExecutorからKubernetesExecutorに変更すると、新しいKPO実行におけるPodの作成数はどのように変わる可能性がありますか？

<details>
<summary>回答を表示</summary>

**回答:** 既存のCelery workerを使う代わりに、タスク実行用PodとワークロードPodの両方が作成される場合があります。

**解説:** 論理的な実行役割が2つあっても、新しいPodが必ず2つ作られるとは限りません。リトライ、再接続、遅延実行も実際に稼働するPod数に影響します。

</details>

3. provider 10.21.0で`pod_template_file`と`pod_template_dict`の両方を指定すると、順番にマージされますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。ファイルが選択され、その呼び出しで渡された辞書は追加でマージされません。

**解説:** 選択されたテンプレートは`full_pod_spec`とKPOが構築したPodに合わせて調整されます。無条件に5つのソースがマージされるわけではありません。

</details>

4. `container_resources`にlimitsだけを指定した場合、テンプレート内のrequestsは保持されますか？

<details>
<summary>回答を表示</summary>

**回答:** 保持されると思い込まないでください。このマージではresourcesオブジェクト全体が置き換わり、以前のrequestsが失われます。

**解説:** 必要なrequestsとlimitsをすべて指定し、最終的なPodを確認してください。他のフィールドでは動作が異なり、リストの連結、キー単位のラベルのマージ、falsy値の継承などがあります。

</details>

5. KPOの`service_account_name`を設定するだけで、PodにS3アクセス権が付与されますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。対応するIAMの信頼設定または関連付けと、互換性のある認証情報プロバイダーが必要です。

**解説:** IRSAまたはPod Identityの設定、SDKが選択する認証情報、実際の許可/拒否動作を確認してください。KPOの呼び出し元が必要とするKubernetes RBACと、子Podに必要なAWS権限は異なります。

</details>

6. Tolerationを設定するだけで、ワークロードを専用のtaint付きNodePoolに配置できますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。Tolerationはtaintを許容するだけです。セレクターや必須のアフィニティも必要になる場合があります。

**解説:** KPO Podは通常のKubernetesスケジューリングを使います。専用プールでもノード障害、Spotの回収、ディスク圧迫は発生します。

</details>

7. バージョン管理を有効にしたGitDagBundleでは、再実行のたびに以前のコミットを使う必要がありますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。リクエスト、DAG、グローバルの再実行設定に加えて、呼び出し単位のデフォルトによって最新バージョンが選ばれる場合があります。

**解説:** 3.3.1では、未設定の場合、clear/rerunのフォールバックはFalse、backfillはTrueです。バンドルのバージョン管理を無効にすると、実行ごとのバージョン追跡もなくなります。コミットを固定しても、データやイメージが固定されるわけではありません。

</details>

8. LocalDagBundle、S3DagBundle、GCSDagBundleを使えば、後で実行するworkerがparserの正確なスナップショットを読むことが保証されますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。これらのバンドルは現時点で実行ごとのバンドルバージョン管理を提供しません。

**解説:** ファイルやオブジェクトは解析後に変更される可能性があります。デプロイの一貫性と関連ファイルの配布は別途管理してください。

</details>

9. Airflow 3ではgit-syncサイドカーが削除されましたか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。公式Helm chartは引き続き対応しています。

**解説:** GitDagBundleのバージョン管理は別の機能です。git-syncを使っても移行が強制されるわけではなく、各実行のコミットが自動的に保持されるわけでもありません。

</details>

10. 固定名のSparkApplicationを適用し、COMPLETEDだけを待つと何が問題になりますか？

<details>
<summary>回答を表示</summary>

**回答:** 前回のCOMPLETED状態を新しい実行の成功と誤認したり、誤ったNamespaceを監視したり、FAILEDの処理が遅れたりする可能性があります。

**解説:** 実行を識別する情報、Namespace、終端状態の処理、クリーンアップの契約を明示してください。ネイティブのSpark Operatorを使う場合も、生成されたCRを対象のCRDに照らして検証する必要があります。

</details>

## 短答

11. KubernetesPodOperatorのimport文を示し、コンテナリソース用の引数名を答えてください。

<details>
<summary>回答を表示</summary>

**回答:** `from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator`を使います。コンテナリソースには`container_resources`を指定します。

**解説:** KubernetesのV1ResourceRequirementsを使用してください。汎用の`resources`引数を同じ設定として扱わないでください。

</details>

12. 10.21.0では、`is_delete_operator_pod=False`だけでPodの保持が保証されますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。この引数はコンストラクターに残っていますが使われません。`on_finish_action`と`on_kill_action`を別々に設定してください。

**解説:** 正常終了とkillは別の経路です。再接続しても、外部書き込みが厳密に1回だけ行われる保証にはなりません。

</details>

13. NamespaceスコープのKPO Roleを使えば、呼び出し元が自身のタスクのPodだけを操作できるように制限できますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。例のRoleでは、そのNamespace内にある許可対象のPodリソース全体へ影響する可能性があります。

**解説:** 呼び出し元のServiceAccountとワークロード側のServiceAccountを区別してください。他のIDや危険な仕様を選択できる信頼されていないDAG作成者に対しては、Admission制御と信頼境界を設けてください。

</details>

## 応用

14. `kpo_smoke`の引数のうち、run IDを渡し、完了時またはkill時にPodを削除する設定を示してください。

<details>
<summary>回答を表示</summary>

**回答:** 章の完全なDAG内にある、該当する引数は次のとおりです。

```python
run_smoke = KubernetesPodOperator(
    task_id="run_smoke",
cmds=["python", "-B", "-c"],
arguments=[
    "import sys; print('KPO_SMOKE_OK run_id=' + sys.argv[1])",
    "{{ run_id }}",
],
on_finish_action="delete_pod",
on_kill_action="delete_pod",
)
```

**解説:** shellコマンドに埋め込むのではなく、run_idを独立した引数として渡してください。assetによって起動された実行に`ds`があるとは限りません。DAG、RBAC、テンプレートの完全な設定は本文を参照してください。

</details>

15. テンプレートの`automountServiceAccountToken=True`をFalseで上書きし、dry_runを確認した後、他に何を検証する必要がありますか？

<details>
<summary>回答を表示</summary>

**回答:** 最終的にマージされた値とAdmission後のPodを調べ、レンダリング、task instanceのラベル、実際の実行も個別に確認します。

**解説:** レビューしたマージ関数では、falsyなFalseではなく、ベース側のTrueが継承されることがあります。dry_runではAdmissionやタスクの成功は証明されません。また、本文に記載されたローカル確認はクラスター上の実行に代わるものではありません。

</details>

---

[学習教材に戻る](../../../data-on-eks/airflow/03-dag-patterns.md)
