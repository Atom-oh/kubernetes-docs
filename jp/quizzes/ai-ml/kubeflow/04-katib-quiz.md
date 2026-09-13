# Part 4: Katib — ハイパーパラメーターチューニングと AutoML クイズ

このクイズでは、Katib の Experiment / Trial / Suggestion アーキテクチャ、サポートされる探索アルゴリズム、early stopping（早期停止）、メトリクス収集、そして EKS 上で Katib を実行する際のリソース負荷に関する考慮事項の理解度を確認します。

## 多肢選択問題

1. Katib のアーキテクチャにおいて、Experiment、Trial、Suggestion の関係はどのようなものですか？
   - A) 同一の CRD に対する 3 つの言い換えであり、互換的に使用できる
   - B) 1 つの Suggestion が多数の Experiment を所有し、各 Experiment が 1 つの Trial を所有する
   - C) 1 つの Experiment が多数の Trial を所有し、各 Trial が特定のハイパーパラメーターの組み合わせを実行する。一方 Suggestion サービスがその組み合わせを提案する
   - D) 1 つの Trial が多数の Experiment を所有し、単一のグローバルな Suggestion によって調整される

<details>
<summary>回答を表示</summary>

**回答: C) 1 つの Experiment が多数の Trial を所有し、各 Trial が特定のハイパーパラメーターの組み合わせを実行する。一方 Suggestion サービスがその組み合わせを提案する**

**解説:**
Experiment オブジェクトはチューニングの内容を記述します。maxTrialCount は完了数の基準であり、学習成功回数でも変更不可の支出上限でもありません。各 Trial は特定のハイパーパラメーターの組み合わせ 1 つによる単一の学習実行です。Suggestion サービスはアルゴリズムを実装しており、過去の観測結果をどのように利用するかはそのアルゴリズムに依存します。
</details>

2. ハイパーパラメーターが目的メトリクスにどう対応するかの確率モデルを構築し、そのモデルを使って次に試すべき最も有望な点を選択する探索アルゴリズムはどれですか？
   - A) Grid search
   - B) Random search
   - C) Bayesian optimization
   - D) Hyperband

<details>
<summary>回答を表示</summary>

**回答: C) Bayesian optimization**

**解説:**
Bayesian optimization はハイパーパラメーターと目的値を関係づける確率モデルを構築し、それを用いて、これまでの最良結果を改善する可能性が最も高い次の候補を選択します。Random search は過去の trial を記憶せず独立にサンプリングします。Grid search は離散的な組み合わせを網羅的に列挙します。Hyperband は小さな予算を広く割り当て、早期の生存者にそれを再配分します。
</details>

3. すべての構成に完全かつ均等な学習予算を与える場合と比べて、Hyperband はどのようなトレードオフを取りますか？
   - A) すべての構成を完全に学習させ切ってから比較する
   - B) 多数の構成に小さな予算を与え、成績の悪いものを早期に切り捨て、解放された予算を生存者に再配分する
   - C) 常に一度に 1 つの構成しか試さない
   - D) 中間的な性能を完全に無視し、構成をランダムに選択する

<details>
<summary>回答を表示</summary>

**回答: B) 多数の構成に小さな予算を与え、成績の悪いものを早期に切り捨て、解放された予算を生存者に再配分する**

**解説:**
Hyperband は構成ごとの網羅的な情報を犠牲にして早期の枝刈りを行います。まず多数の構成を安価に実行し、最も見込みの薄いものを積極的に切り捨て、解放されたリソース予算を依然として有望な構成に与えます。
</details>

4. Experiment の spec において、`objective` フィールドは何を定義しますか？
   - A) 各 Trial の実行に使用されるコンテナイメージ
   - B) 最適化対象のメトリクスと、それを最大化するか最小化するか
   - C) 並列実行できる Trial の数
   - D) 探索アルゴリズム内部のハイパーパラメーター

<details>
<summary>回答を表示</summary>

**回答: B) 最適化対象のメトリクスと、それを最大化するか最小化するか**

**解説:**
`objective` はメトリクス（accuracy や loss など）と目標（最大化または最小化）を指定し、オプションで目標値を含めることができ、その値に到達した時点で Experiment を早期終了させられます。探索空間は別途 `parameters` の下で定義され、各 Trial のジョブの実行方法は `trialTemplate` の下で定義されます。
</details>

5. このレビューでは、Katib 0.19.0 の medianstop のしきい値計算について何が検証されましたか？
   - A) median の Trial が完了した時点で Experiment 全体を停止する
   - B) 最初の start_step 個の観測値における成功 Trial の平均値を保存し、それらの算術平均を計算する
   - C) 提案されたすべての Trial のうち、ちょうど半分だけを実行できるようにする
   - D) 最終的な答えとして median のハイパーパラメーター値を選択する

<details>
<summary>回答を表示</summary>

**回答: B) 最初の start_step 個の観測値における成功 Trial の平均値を保存し、それらの算術平均を計算する**

**解説:**
公式ガイドは median のルールとして説明していますが、0.19.0 は算術平均を計算します。成功 Trial の平均値が [1, 2, 100] の場合、未変更の関数では統計的な median の 2 ではなく約 34.333 が得られます。デフォルトは min_trials_required=3 および start_step=4 であり、collector およびタイムスタンプの要件も適用されます。
</details>

6. Katib は通常、実行中の Trial の学習コンテナから目的メトリクスの値をどのように取得しますか？
   - A) 学習コンテナがコード内から Katib API を直接呼び出す必要がある
   - B) 設定された pull collector がメトリクスを収集する、または Push モードの report_metrics() が DB manager に送信する
   - C) Katib がコンテナを一時停止し、そのメモリを直接検査する
   - D) Kubernetes スケジューラーがリソース使用量からメトリクスを自動的に抽出する

<details>
<summary>回答を表示</summary>

**回答: B) 設定された pull collector がメトリクスを収集する、または Push モードの report_metrics() が DB manager に送信する**

**解説:**
StdOut / File / TensorFlowEvent および Custom collector は Push モードと共存します。任意の HTTP スクレイピングは組み込みのデフォルトではありません。Pull の injection には namespace のラベル付け、webhook、および対象 Pod / コンテナの設定が必要です。ジョブが成功しただけではメトリクスが収集された証明にはなりません。
</details>

7. 同じ `maxTrialCount` を低い並列度で実行する場合と比べて、高い `parallelTrialCount` が EKS クラスターにより急峻なリソース負荷を生じさせるのはなぜですか？
   - A) `parallelTrialCount` は作成される Pod の数に影響しない
   - B) 高い並列度では、多数の Trial（および GPU などのリソースリクエスト）が分散されずに同時にクラスターへ到達し、短く急峻な需要スパイクを生じさせる
   - C) EKS はデフォルトで `parallelTrialCount` を 1 に制限する
   - D) 並列の Trial は常に同一ノード上で実行されるため、追加の需要は発生しない

<details>
<summary>回答を表示</summary>

**回答: B) 高い並列度では、多数の Trial（および GPU などのリソースリクエスト）が分散されずに同時にクラスターへ到達し、短く急峻な需要スパイクを生じさせる**

**解説:**
同時実行される各 Trial は完全な学習ジョブです。需要は 並列度 × Trial あたりの Pod 数 × Pod あたりのリソース に、collector とサービスのオーバーヘッドを加えたものになります。そのため、`maxTrialCount` の合計が控えめに見える Experiment でも需要が急激に跳ね上がる可能性があります。
</details>

8. EKS において、`parallelTrialCount` の高い Experiment を開始した直後に、新しく作成された Trial の Pod がしばらく pending のままになっている場合、考えられる説明は何ですか？
   - A) Suggestion サービスがクラッシュしている
   - B) キャパシティを待っている可能性がある。Pod の events、NodePool の conditions、クォータ、EC2 のキャパシティ、ブートストラップの状態を通じて確認する
   - C) Katib は常に新しい Trial を一定のウォームアップ期間だけ停止させる
   - D) metrics-collector サイドカーが Pod の起動をブロックしている

<details>
<summary>回答を表示</summary>

**回答: B) キャパシティを待っている可能性がある。Pod の events、NodePool の conditions、クォータ、EC2 のキャパシティ、ブートストラップの状態を通じて確認する**

**解説:**
pending であること自体は、Karpenter がプロビジョニングに成功していることの証明にはなりません。affinity、taint、ボリューム、クォータ、キャパシティ上限、ブートストラップの失敗も原因になり得ます。観測された events と controller の状態を利用してください。
</details>

## 短答問題

9. Katib がサポートする探索アルゴリズムを 2 つ挙げ、それぞれがどのような問題に最も適しているかを 1 文で説明してください。

<details>
<summary>回答を表示</summary>

**回答:** 次のうち任意の 2 つ: random search（大規模あるいは十分に理解されていない探索空間に対する安価なベースライン）、grid search（小規模で低次元の離散空間の網羅的なカバー）、Bayesian optimization（目的値の確率モデルにより、1 回の Trial が高コストな場合に必要な総 Trial 数を削減する）、Hyperband（安価で情報量のある早期シグナルを用いて成績の悪い構成を早期に枝刈りする）、CMA-ES（共分散適応による進化戦略）、PBT（checkpoint の共有を必要とする、population ベースの別種の学習戦略）。

**解説:**
各アルゴリズムは探索コストと探索効率のトレードオフの取り方が異なり、適切な選択は 1 回の Trial のコストと探索空間にどれだけ構造があるかによって決まります。
</details>

10. Hyperband が行うことと、early stopping（median-stopping rule など）が行うことの違いは何ですか。どちらも計算リソースの無駄を避けることを目的としています。

<details>
<summary>回答を表示</summary>

**回答:** Hyperband は各構成にどれだけのリソース予算を与えるかを事前に決定する探索戦略です。early stopping は、すでに進行中の Trial に対して、その時点の学習における他の Trial との相対的な性能に基づいて適用される実行時のチェックです。

**解説:**
両者は異なるレベルで動作します。Hyperband の枝刈りは探索アルゴリズム全体の予算配分戦略の一部であり、early stopping は Trial の実行中にその Trial ごとに行われる判断です。ただし互換性のある collector / ログ設定が前提であり、あらゆる組み合わせが自動的にサポートされるわけではありません。
</details>

## ハンズオン / 応用問題

11. 各 Trial が GPU を 1 つリクエストする Experiment を設定しており、クラスターには GPU インスタンス用の Karpenter NodePool があって、新しいキャパシティのプロビジョニングには通常数分かかります。`maxTrialCount: 60` を設定し、`parallelTrialCount` を検討中です。この環境で高い値（例: 20）に設定する場合と低い値（例: 4）に設定する場合のトレードオフを数文で説明してください。

<details>
<summary>回答を表示</summary>

**回答:** 高い `parallelTrialCount`（例: 20）は、キャパシティが利用可能であれば少ないラウンド数で Trial を処理できますが、20 件の GPU リクエストが同時に発生する急激なバーストを生み、Karpenter が GPU ノードをプロビジョニングできる速度を上回るおそれがあります。その結果、初期の Trial は学習ではなく pending 状態になり、他のワークロードが同じ GPU NodePool を奪い合っている場合には共有クラスターのキャパシティを急激に消費する可能性もあります。低い `parallelTrialCount`（例: 4）は同じ 60 件の Trial をより多くのラウンドに分散させ、Karpenter が段階的にプロビジョニングする時間を与えてキャパシティスパイクのリスクを下げますが、経過時間は長くなる可能性があります。実際の時間とコストは、キャパシティ、実行時間、失敗、停止、ノードの回収状況に依存します。

**解説:**
`parallelTrialCount` と `maxTrialCount` は独立した設定として扱うのではなく、クラスターのオートスケーリング挙動を踏まえて一緒にチューニングする必要があります。特に Trial が GPU のように希少あるいはプロビジョニングの遅いリソースをリクエストする場合はなおさらです。
</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/04-katib.md)
