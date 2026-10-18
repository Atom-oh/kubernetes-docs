# Argo Rollouts Experimentクイズ

このクイズでは、Experiment CRDのリソース階層、トラフィック分離、分析結果の判定、結果の伝播について理解度を確認します。

1. Experiment CRDの主な目的は何ですか？
   - A) すべての本番トラフィックを新しいバージョンへ切り替える
   - B) 一時的なReplicaSetと分析によって新しいバージョンを検証する
   - C) Rolloutのリビジョン履歴を保存する
   - D) クラスターノードに負荷テストを実行する

<details>
<summary>回答を表示</summary>

**回答: B) 一時的なReplicaSetと分析によって新しいバージョンを検証する**

**解説:**
Experimentは一時的なReplicaSetを起動し、完了時にレプリカ数を0へ縮小します。Serviceセレクターとルーターで意図した分離を実現する必要があります。ReplicaSetを分けるだけでは、実際のユーザーに影響しないことは保証されません。

</details>

2. Rolloutのカナリア戦略でExperimentステップがFailedまたはErrorで終了すると、何が起きますか？
   - A) ステップがスキップされ、Rolloutは次のステップに進む
   - B) 失敗したExperimentが自動的に再試行される
   - C) Rolloutが中止され、安定版がそのまま維持される
   - D) Rolloutが一時停止状態で待機する

<details>
<summary>回答を表示</summary>

**回答: C) Rolloutが中止され、安定版がそのまま維持される**

**解説:**
Experimentステップは進行を止めるステップです。ExperimentがSuccessfulフェーズで完了した場合にだけRolloutが続行されます。Failed/Errorの場合はRolloutが中止され、Degraded状態になります。Inconclusiveの場合は調査とオペレーターの判断を待つためにInconclusiveExperimentで一時停止します。中止してもデータベースの変更や外部への副作用は元に戻りません。

</details>

3. `demo-app` Rolloutのrevision 2更新で最初のステップ（index 0）にExperimentが作成されるとします。名前の衝突がない場合、正しいベース名の形式はどれですか？ 新バージョンのPodTemplateHashは`74d8d8b4fb`です。
   - A) `demo-app-experiment-1`
   - B) `demo-app-74d8d8b4fb-2-0`
   - C) `experiment-demo-app-0-2`
   - D) `demo-app-2-0-74d8d8b4fb`

<details>
<summary>回答を表示</summary>

**回答: B) `demo-app-74d8d8b4fb-2-0`**

**解説:**
Experiment名は`<rollout-name>-<new-version PodTemplateHash>-<revision>-<step-index>`です。作成されるReplicaSetの名前は`<experiment-name>-<template-name>`（例: `demo-app-74d8d8b4fb-2-0-baseline`）、AnalysisRunの名前は`<experiment-name>-<analysis-name>`です。

</details>

4. 例のServiceが`traffic-class=production`を選択し、ExperimentのPodが`traffic-class=experiment`を持つ場合、そのPodがServiceから除外されるのはなぜですか？
   - A) ExperimentのPodは別のNamespaceに作られるため
   - B) ExperimentのPodはNetworkPolicyによってブロックされるため
   - C) Serviceセレクターの`traffic-class`とExperiment Podのラベルが異なるため
   - D) ExperimentのPodには常に失敗するreadinessProbeが設定されるため

<details>
<summary>回答を表示</summary>

**回答: C) Serviceセレクターの`traffic-class`とExperiment Podのラベルが異なるため**

**解説:**
この例ではラベルとセレクターを使って選択対象を明示的に分けています。アプリのラベルだけを選択する別のServiceであれば、ExperimentのPodも対象になる可能性があります。意図的にトラフィックを送るには、テンプレートの`service`属性を設定してExperiment専用のServiceを作成するか、`trafficRouting`を設定したRolloutで`weight`を使います。

</details>

5. テンプレートの`weight`フィールドを使ってExperiment Podに実際のトラフィックを送るための前提条件は何ですか？
   - A) Rolloutに、重み付けされたExperimentに対応するtrafficRoutingが設定されている
   - B) テンプレートのレプリカ数が安定版のレプリカ数と一致している
   - C) AnalysisTemplateでwebプロバイダーを使っている
   - D) ExperimentがRolloutなしの単独リソースとして作成されている

<details>
<summary>回答を表示</summary>

**回答: A) Rolloutに、重み付けされたExperimentに対応するtrafficRoutingが設定されている**

**解説:**
weightはRolloutの各Experimentステップのテンプレートに属します。ALB/Istioなど、対応するルーターが必要です。通常のカナリア重み付けに対応していても、Experimentのトラフィック分割に対応するとは限りません。trafficRoutingを設定しない場合は、`service`属性でExperiment専用Serviceを作成し、ルーティングを自分で接続してください。

</details>

6. AnalysisTemplateのメトリクスに`failureLimit: 1`を設定した場合、AnalysisRun全体がFailedになるのはいつですか？
   - A) 測定に1回失敗した直後
   - B) 測定に2回失敗した後（failed > failureLimit）
   - C) 連続して1回失敗した場合のみ
   - D) countで指定した測定がすべて完了した場合のみ

<details>
<summary>回答を表示</summary>

**回答: B) 測定に2回失敗した後（failed > failureLimit）**

**解説:**
`failureLimit`は許容する失敗回数です。AnalysisRunは失敗数がこの上限を超えた時点でFailedと判定されます。1.10.0の実装では`failed > failureLimit`を比較します。同様に、`inconclusiveLimit`を超えるとInconclusiveになり、`consecutiveErrorLimit`（連続する収集エラーの上限。デフォルトは4）を超えるとErrorになります。

</details>

7. Experimentの`duration`タイマーはいつ開始しますか？
   - A) Experimentリソースの作成直後
   - B) 最初のAnalysisRun測定が成功したとき
   - C) `spec.templates`のすべてのReplicaSetが正常（available）になったとき
   - D) RolloutがExperimentステップに到達する直前

<details>
<summary>回答を表示</summary>

**回答: C) `spec.templates`のすべてのReplicaSetが正常（available）になったとき**

**解説:**
Experimentコントローラーは各テンプレートのReplicaSetを作成し、すべてのPodが利用可能になるまで待機します。その後にdurationタイマーを開始し、AnalysisRunを作成します。そのため、Podの起動に時間がかかってもExperimentの実行時間は短くなりません。

</details>

8. Experimentが完了すると、成功・失敗にかかわらず、そのReplicaSetはどうなりますか？
   - A) 次のExperimentのために保持される
   - B) レプリカ数が0に縮小され、`service`属性で作成されたServiceも削除される
   - C) 安定版ReplicaSetに昇格する
   - D) 手動で削除されるまで残る

<details>
<summary>回答を表示</summary>

**回答: B) レプリカ数が0に縮小され、`service`属性で作成されたServiceも削除される**

**解説:**
Experimentは一時的なリソースです。完了後、デフォルトでは30秒の縮小遅延を経てレプリカ数が0になります。生成されたServiceは、利用可能なレプリカ数が0になった後に削除されます。保持ポリシーによってはReplicaSetやAnalysisRunオブジェクトが残る場合があります。Successfulなら処理を進め、Failed/Errorなら中止し、Inconclusiveなら一時停止します。

</details>
