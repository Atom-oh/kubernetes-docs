# MLflow Model Registry クイズ

このクイズでは、MLflow Model Registry（Registered Model、Model Version、alias、および登録と Tracking のつながり）に関する理解度を確認します。

## 選択問題

1. MLflow における Registered Model とは何ですか？
   - A) トレーニング Run のメトリクスのスナップショット
   - B) 単一の Run から独立した安定したモデルの識別情報を与える、名前付き・バージョン管理された Model Version のコレクション
   - C) モデル artifact からビルドされたコンテナイメージ
   - D) tracking server のデータベースの保存済みコピー

<details>

<summary>回答を表示</summary>

**回答: B) 単一の Run から独立した安定したモデルの識別情報を与える、名前付き・バージョン管理された Model Version のコレクション**

**解説:**
Registered Model は名前（例: `fraud-detector`）で識別され、そのライフサイクルを通じて Model Version、alias、tag、説明を蓄積します。これは、任意の 1 つのトレーニング Run や Experiment より長く存続する識別情報を「モデル」に持たせるために存在します。
</details>

2. Model Version は作成されるとどうなりますか？
   - A) モデルの改善に合わせてその場で編集できる
   - B) イミュータブルである — 新しいトレーニング結果は古いものへの編集ではなく、新しい version になる
   - C) 30 日後に自動的に削除される
   - D) 同じ名前で登録された次の version とマージされる

<details>

<summary>回答を表示</summary>

**回答: B) イミュータブルである — 新しいトレーニング結果は古いものへの編集ではなく、新しい version になる**

**解説:**
各 Model Version には番号（version 1、version 2 など）が付けられ、登録後は変更されません。新しい候補モデルは、常に同じ Registered Model 名の下で新しい version になります。
</details>

3. Model Version が Tracking（Part 1）とのつながりとして保持するものは何ですか？
   - A) registry 内に保存されたトレーニング dataset のコピー
   - B) 元になった `LoggedModel` または Run への参照
   - C) cluster の node 設定のスナップショット
   - D) 何も保持しない — Model Version は Tracking から完全に独立している

<details>

<summary>回答を表示</summary>

**回答: B) 元になった `LoggedModel` または Run への参照**

**解説:**
すべての Model Version は、それを生成した Run（および Part 1 で取り上げた `LoggedModel` entity）を参照します。これにより lineage と再現性が実現します。
</details>

4. MLflow Model Registry における alias とは何ですか？
   - A) モデル作成時に割り当てられる、永続的で変更不可能なラベル
   - B) `champion` や `challenger` のように、特定の Model Version を指す変更可能な名前付きポインタ
   - C) tracking server の URL の短縮表記
   - D) Registered Model 名の同義語

<details>

<summary>回答を表示</summary>

**回答: B) `champion` や `challenger` のように、特定の Model Version を指す変更可能な名前付きポインタ**

**解説:**
version 番号とは異なり、alias は時間の経過とともに別の Model Version を指すように移動できます。たとえば、新しい version が評価に合格した後、`champion` を version 4 から version 7 に再指定できます。
</details>

5. 現在の MLflow で、alias が従来の stage ベースのライフサイクルモデル（Staging/Production/Archived）に取って代わった理由は何ですか？
   - A) stage はどのバージョンの MLflow でもサポートされなくなった
   - B) alias の方が柔軟である: version は複数の alias を持つことも、持たないこともでき、alias 名は固定されたライフサイクルラベルのセットに制限されない
   - C) alias は stage より必要なディスク容量が少ない
   - D) stage は API を通じてクエリできなかった

<details>

<summary>回答を表示</summary>

**回答: B) alias の方が柔軟である: version は複数の alias を持つことも、持たないこともでき、alias 名は固定されたライフサイクルラベルのセットに制限されない**

**解説:**
stage モデルでは、各 version が固定されたラベル（`Staging`、`Production`、`Archived`）のいずれか 1 つに結び付けられていました。tag と組み合わせた alias により、より柔軟でカスタム可能な命名が可能になり、1 つの version に同時に複数の alias を付与できます。古い MLflow deployment では現在も stage モデルを見かける場合がありますが、これはレガシーなアプローチです。
</details>

6. モデルがログに記録されるのと同時に新しい Model Version を作成するのは、次のどれですか？
   - A) ログ記録後に `mlflow.register_model(model_uri, name)` を呼び出す
   - B) flavor 固有の `log_model` 呼び出しに `registered_model_name` を渡す
   - C) モデルファイルを tracking server の artifact store に手動でコピーする
   - D) 既存の Model Version に tag を設定する

<details>

<summary>回答を表示</summary>

**回答: B) flavor 固有の `log_model` 呼び出しに `registered_model_name` を渡す**

**解説:**
`mlflow.sklearn.log_model(..., registered_model_name="fraud-detector")` のような呼び出しに `registered_model_name` を渡すと、モデルをログに記録する同じ呼び出しで新しい Model Version が登録されます。`mlflow.register_model(model_uri, name)` は、前のステップですでにログに記録されたモデルを登録するための代替手段です。
</details>

7. 一般的なガバナンスワークフローでは、何が `champion` alias を新しい version に移動させますか？
   - A) トレーニング script が、Run の終了直後に自動で移動させる
   - B) 評価または承認プロセス — 多くの場合 CI/CD pipeline の一部 — が、候補 version がゲートを通過した後にのみ移動させる
   - C) serving system が `models:/fraud-detector@champion` を最初に解決したときに移動させる
   - D) version 番号が高いことに基づき、MLflow が自動で移動させる

<details>

<summary>回答を表示</summary>

**回答: B) 評価または承認プロセス — 多くの場合 CI/CD pipeline の一部 — が、候補 version がゲートを通過した後にのみ移動させる**

**解説:**
registry のガバナンス価値は、「候補を生成すること」と「候補を昇格させること」を分離することにあります。`champion` alias の移動は意図的なアクションであり、通常は評価基準の合格をゲートとする承認 pipeline 内で自動化されます。
</details>

8. serving system が `models:/fraud-detector/7` ではなく `models:/fraud-detector@champion` を解決することで得られるものは何ですか？
   - A) より高速な inference latency
   - B) コード変更なしで、現在 `champion` alias を保持している version を自動的に取得する安定した参照
   - C) 別の tracking server へのアクセス
   - D) 自動的なモデル再トレーニング

<details>

<summary>回答を表示</summary>

**回答: B) コード変更なしで、現在 `champion` alias を保持している version を自動的に取得する安定した参照**

**解説:**
alias ベースの URI は、モデルの利用者を特定の version 番号から切り離します。`champion` が新たに検証された version を指すように再指定されると、その URI に対する次回の解決では新しい version が取得されます。
</details>

## 記述問題

9. Model Version と alias の違い、およびその違いが serving system にとって重要である理由を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
Model Version はイミュータブルであり、番号が付けられます。作成後は変更されず、新しいトレーニング結果は既存のものへの編集ではなく、常に新しい version になります。alias は変更可能です。これは、いつでも別の Model Version を指すように再指定できる、`champion` や `challenger` のような名前付きポインタです。

この違いは、serving system がハードコードされた version 番号ではなく、`models:/fraud-detector@champion` のような安定した名前を解決するように一度だけ記述できるため重要です。alias が新たに承認された version に移動されると、serving system は次回の解決時にコードや設定の更新なしで自動的に変更を取得します。
</details>

10. Model Version の lineage が、「現在 production で serving しているモデルを生成した正確な code と data は何か」という監査上の質問をどのように支えるかを説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
各 Model Version は、それを生成した Run（および Part 1 で取り上げた基盤となる `LoggedModel`）への参照を保持します。その連鎖をたどると — `champion` alias から、それが指す Model Version へ、さらにその version から元の Run へ — Tracking 中にその Run がログに記録した parameter、code 参照、dataset 情報に到達します。

Model Version はイミュータブルであり、この lineage リンクが失われることはないため、監査担当者は、現在 `champion` として alias 付けされたモデルを、別個の記録やチームの記憶に頼ることなく、それを作成した正確なトレーニング Run まで常に追跡できます。
</details>

---

[学習教材に戻る](../../../ai-ml/mlflow/02-model-registry.md) | [次のクイズ: EKS Deployment](./03-eks-deployment-quiz.md)
