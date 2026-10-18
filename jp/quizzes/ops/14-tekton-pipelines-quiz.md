# Tekton Pipelines クイズ

1. Task、TaskRun、Workspace の説明として正しいものはどれですか？
   - A) Task の定義は、それだけですでに実行中の Pod である
   - B) TaskRun は Task を実行し、Workspace はボリュームをバインドするためのフィールドである
   - C) Workspace は常に独立した CRD である
   - D) 同じ Pod 内の Step 同士は完全に分離されている

<details>
<summary>回答を表示</summary>

**回答: B) TaskRun は Task を実行し、Workspace はボリュームをバインドするためのフィールドである**

Task と Pipeline は定義であり、Run は実行です。同じ Pod 内の Step はネットワークとボリュームを共有するため、信頼境界にはなりません。

</details>

---

2. TaskRun 間でソースを共有する場合、正しいものはどれですか？
   - A) emptyDir を使うと、Pod 間で同じファイルを共有できる
   - B) Run ごとの PVC を使用できる。RWO/RWX 自体は信頼境界ではない
   - C) 異なる subPath を使えば、外部 PR とリリースで 1 つの PVC を安全に共有できる
   - D) Results には常に無制限の文字列を格納できる

<details>
<summary>回答を表示</summary>

**回答: B) Run ごとの PVC を使用できる。RWO/RWX 自体は信頼境界ではない**

Run ごとのストレージには `volumeClaimTemplate` を使い、異なる信頼レベル間では書き込み可能なデータを分離してください。小さな値には Results、大きなレポートにはアーティファクトストレージを使います。

</details>

---

3. GitHub HMAC を検証した後、外部 PR をどのように扱うべきですか？
   - A) リリースパイプラインの IRSA と署名権限を使う
   - B) 権限を制限した、別の実行信頼レベルで処理する
   - C) HMAC の検証に成功したので、そのシェルコマンドをスクリプトに直接埋め込む
   - D) 検証済みリクエストは、必ず main ブランチへの push である

<details>
<summary>回答を表示</summary>

**回答: B) 権限を制限した、別の実行信頼レベルで処理する**

HMAC が検証するのは配信元であり、そのコードにデプロイを許可するものではありません。この章で扱う特権付き CI 経路は、承認済みリポジトリの保護された main ブランチへの push に限定されます。

</details>

---

4. Chains の `slsa/v1` formatter が生成する provenance のバージョンはどれですか？
   - A) SLSA provenance v1.0
   - B) SLSA provenance v0.2。v1.0 には `slsa/v2alpha3` または `slsa/v2alpha4` を使う
   - C) 署名鍵が任意のバージョンを自動的に選択する
   - D) 常に Kubernetes v1 API と同じバージョンである

<details>
<summary>回答を表示</summary>

**回答: B) SLSA provenance v0.2。v1.0 には `slsa/v2alpha3` または `slsa/v2alpha4` を使う**

Formatter の名前と SLSA 仕様のバージョンは異なります。Pipeline レベルの provenance は Pipeline の完了後に作成され、別途検証と昇格が必要です。

</details>

---

5. `finally` Task について正しい説明はどれですか？
   - A) すべてのエラー、キャンセル、タイムアウトの後に必ず実行される
   - B) 通常の Task の後に実行されるが、Results の欠落、キャンセル、タイムアウトによってスキップまたは実行不能になる場合がある
   - C) 宣言した順序で常に逐次実行される
   - D) 欠落した image Result のデフォルト値を自動的に補う

<details>
<summary>回答を表示</summary>

**回答: B) 通常の Task の後に実行されるが、Results の欠落、キャンセル、タイムアウトによってスキップまたは実行不能になる場合がある**

最後のレポートが参照するのは Run 名と `tasks.status` のみです。`finally` Task 間の実行順序を前提にせず、タイムアウト時の動作も考慮してください。

</details>

---

6. CI が成功し、`chains.tekton.dev/signed=true` が確認できた後に必要な作業は何ですか？
   - A) 任意のタグをすぐに本番環境へデプロイする
   - B) 信頼できる鍵、ダイジェスト、ビルダー、ソース provenance を検証してから、GitOps の変更をレビューする
   - C) 署名 JSON を検証せずに Base64 デコードするだけでよい
   - D) ArgoCD 自身がアプリケーションイメージを pull することを確認する

<details>
<summary>回答を表示</summary>

**回答: B) 信頼できる鍵、ダイジェスト、ビルダー、ソース provenance を検証してから、GitOps の変更をレビューする**

署名済みを示す annotation は、暗号学的な検証や承認の代わりにはなりません。ArgoCD はマニフェストを同期し、イメージは kubelet またはコンテナランタイムが pull します。

</details>

---

7. Pipelines 1.17 で、コントローラーの ServiceMonitor に使うポートとカウンターはどれですか？
   - A) `metrics` / `pipelinerun_count`
   - B) `http-metrics` / `tekton_pipelines_controller_pipelinerun_total`
   - C) `http` / すべての namespace に対する自動カウンター
   - D) `9097` / 実行時間のヒストグラム

<details>
<summary>回答を表示</summary>

**回答: B) `http-metrics` / `tekton_pipelines_controller_pipelinerun_total`**

実際の Service ラベルとポートを Prometheus のセレクターに合わせてください。現在の完了カウンターにはステータスが含まれますが、namespace ラベルはありません。

</details>

---

8. `coschedule=workspaces` の場合、`volumeClaimTemplate` で作成された PVC は完了後にデフォルトでどうなりますか？
   - A) 常に直ちに削除される
   - B) 保持される。正確な値が `true` の自動クリーンアップ annotation を指定すると、完了時に削除できる
   - C) ユーザーが事前に用意した PVC も常に削除される
   - D) PipelineRun にはデフォルトで 7 日間の TTL が設定されている

<details>
<summary>回答を表示</summary>

**回答: B) 保持される。正確な値が `true` の自動クリーンアップ annotation を指定すると、完了時に削除できる**

他の `coschedule` モードや既存の PVC ではライフサイクルが異なります。Run の記録を削除する前に、完了時刻、保持期間、ログや署名のアーカイブを確認してください。

</details>
