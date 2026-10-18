# EKS Spot本番実験クイズ

> **関連ガイド**: [EKS Spot本番実験と結果評価](../../ops/17-spot-production-experiments.md)

## 1. PDBがあるSpotノードでdrainテストに合格しました。何が確認できましたか？

- A) 実際にSpot reclamationが起きても、常に同じ可用性が維持される
- B) 自発的なevictionの経路が動作すること。実際のreclamationは別途テストが必要
- C) PDBを確認するまでEC2インスタンスは終了しない
- D) アプリケーションには終了まで常に2分が与えられる

<details>
<summary>回答を表示</summary>

**回答: B) 自発的なevictionの経路が動作すること。実際のreclamationは別途テストが必要**

**解説:** PDBでEC2インスタンスの喪失を防ぐことはできません。実際のreclamationと予告なしの喪失を通じて、通知の到着、eviction遅延、強制終了、サービスへの影響をテストしてください。

</details>

## 2. Spot専用のselectorを持つPodがPendingです。On-Demandノードを追加するとどうなりますか？

- A) selectorに関係なくPodが直ちに移動する
- B) PDBがselectorをOn-Demandに変更する
- C) Podは引き続きOn-Demandノードにスケジュールできない
- D) NodePoolのweightがselectorより優先される

<details>
<summary>回答を表示</summary>

**回答: C) Podは引き続きOn-Demandノードにスケジュールできない**

**解説:** フォールバックには利用可能な容量とPodの制約との互換性が両方必要です。NodePoolで使えるcapacity typeの種類を増やすだけでは、Spot専用のPod selectorは解除されません。

</details>

## 3. NodePoolをOn-Demand専用に変更すると、サービスが起動しました。このドリルで何を検証しましたか？

- A) EC2からSpot容量不足が返された後、自動的にフォールバックすること
- B) 設定に基づく切り替え、スケジューリング、On-Demandでの起動
- C) すべてのAZでSpot容量が必ず得られること
- D) 既存のSpot Podがすべて直ちに移動すること

<details>
<summary>回答を表示</summary>

**回答: B) 設定に基づく切り替え、スケジューリング、On-Demandでの起動**

**解説:** このドリルでは容量エラーを注入していません。実際のプロビジョニング経路のエラー処理とフォールバックは別途検証してください。再現できない場合は未検証と記録します。

</details>

## 4. FISは`completed`を報告し、代替ノードはReadyです。サービスレベルの合格を確認するには何が必要ですか？

- A) FISの状態だけ
- B) ノードのReady状態だけ
- C) クライアントエラー、レイテンシー、スループット、正確性のすべてが基準を満たすこと
- D) クライアントのタイムアウトは無視し、LBの5xx応答がないこと

<details>
<summary>回答を表示</summary>

**回答: C) クライアントエラー、レイテンシー、スループット、正確性のすべてが基準を満たすこと**

**解説:** FISの完了は障害注入の状態を示します。サービスの復旧確認には、Podのreadiness、LBターゲットの健全性、実際のリクエスト成功、処理の正確性も必要です。

</details>

## 5. Spotによるコスト削減を正しく比較する方法はどれですか？

- A) Spotの割引率をサービス全体の節約率として報告する
- B) 同等の条件下で、正確性のチェックに合格した一意の成功オペレーションごとの実効コストを比較する
- C) リトライとOn-Demandへの置き換えにかかるコストを除外する
- D) 置き換え時の重複コストをEC2請求と追加コスト項目の両方に計上する

<details>
<summary>回答を表示</summary>

**回答: B) 同等の条件下で、正確性のチェックに合格した一意の成功オペレーションごとの実効コストを比較する**

**解説:** オーバーヘッド、コミット割引、置き換え、リトライを含め、料金を二重計上しないでください。短期間の実行を月次へ外挿する場合は、推定値と明記します。

</details>

## 6. 実験データがない場合、結果をどのように記録すべきですか？

- A) 予想される復旧時間を測定値として入力する
- B) エラー数を0として合格にする
- C) NOT RUNと未測定項目を記録し、本番への拡大は保留する
- D) 公式ドキュメントを実験完了の証拠とみなす

<details>
<summary>回答を表示</summary>

**回答: C) NOT RUNと未測定項目を記録し、本番への拡大は保留する**

**解説:** 文書に記載された動作、仮説、測定値はそれぞれ異なる種類の証拠です。実行IDと生の結果がなければ、本番の準備ができていることは確認できません。

</details>

## 7. E2の混在経路では全体のエラー率が0.0556%、最悪の連続60秒ウィンドウでは0.8333%でした。60秒の基準が0.1%の場合、何が言えますか？

- A) 全体のエラー率が低いため合格
- B) p99が低いため失敗を無視できる
- C) ウィンドウの基準に不合格である。設定を修正し、再テストする必要がある
- D) Spotを本番サービスで一切使用できない

<details>
<summary>回答を表示</summary>

**回答: C) ウィンドウの基準に不合格である。設定を修正し、再テストする必要がある**

**解説:** 長時間にわたる正常な区間が全体のエラー率を下げることがあります。評価ウィンドウを実際のビジネスSLOに合わせ、1回の合成テストをすべての構成に一般化しないでください。

</details>

## 8. Podは作成時からGuaranteedです。対象の通常コンテナでCPU requestとlimitがともに200mから50mへ下がります。memory request=limitは64Miのままで、他のコンテナはすべてGuaranteedのリソース設定を維持します。何が起きますか？

- A) CPUを減らすと必ずPodがBurstableになる
- B) downscale後もCPUとmemoryのrequestとlimitがそれぞれ等しいため、Podは元のGuaranteedクラスを維持する
- C) 同じresizeによって作成時にBurstableだったPodもGuaranteedになる
- D) memoryのrequestとlimitが異なっていても、CPUの値が等しければGuaranteedを維持する

<details>
<summary>回答を表示</summary>

**回答: B) downscale後もCPUとmemoryのrequestとlimitがそれぞれ等しいため、Podは元のGuaranteedクラスを維持する**

**解説:** QoSクラスは作成時に決まり、resizeでは変更されません。このコンテナ単位の設計では、該当する各コンテナについて、CPUとmemoryのrequestがそれぞれ対応する正のlimitと等しい状態を維持し、CPUのrequestとlimitを同時に減らします。Guaranteedを維持しても、downscale後にアプリケーションSLOを満たす証明にも、Spot reclamationを防ぐことにもなりません。

</details>

## 9. E10で初期化の完了、CPU downscaleの適用、downscale後のサービス品質を確認するには、どの証拠が必要ですか？

- A) PodがRunningなら3つすべて確認できる
- B) `pods/resize` PATCHが成功すれば、初期化、downscaleの完了、SLOへの適合が証明される
- C) 実際のstartupProbeと`started=true`、希望リソースと報告リソース、generationとresize状態を確認し、downscale後のアプリケーションSLOも確認する
- D) containerIDとGuaranteedクラスが変わっていないため、リクエストエラーやレイテンシーのチェックは不要

<details>
<summary>回答を表示</summary>

**回答: C) 実際のstartupProbeと`started=true`、希望リソースと報告リソース、generationとresize状態を確認し、downscale後のアプリケーションSLOも確認する**

**解説:** Running状態や`started`値だけでは初期化完了を確認できません。対象の各コンテナに実際の初期化を検査するstartupProbeが必要です。PATCHの成功はリクエストが受理されたことを示すだけなので、kubeletが報告するリソース、観測されたgeneration、PodResizePending、PodResizeInProgressを確認してください。resize適用後の品質は別途評価します。readiness/LB状態と、エラー、p99、スループット、throttlingなどのアプリケーションSLOの証拠を使います。

</details>

## 10. 2026-09-12のSpot測定値と公開済みの初期テンプレートから、フェーズを考慮したCPU resizeについて何が確認できますか？

- A) E2の全体p99が低かったため、起動時CPU増加の効果が証明された
- B) 初期テンプレートと測定にはフェーズを考慮した設定と必要な証拠がなく、E10は引き続きNOT RUNである
- C) 初期テンプレートだけでAdmission後のPodのリソースとQoSを確認できる
- D) ロードマップの過去のレポートとローカルプロトタイプのチェックで、複合的なSpot実験も完了した

<details>
<summary>回答を表示</summary>

**回答: B) 初期テンプレートと測定にはフェーズを考慮した設定と必要な証拠がなく、E10は引き続きNOT RUNである**

**解説:** 3つの初期Deploymentではrequestを50m/64Mi、limitを500m/256Miとしています。この設定自体がGuaranteedの要件を満たしません。フェーズを考慮したresize opt-in、resizePolicy、startupProbeがなく、実際のリソース、QoS、比較可能なwarmup性能について前後の証拠もありません。初期テンプレートはAdmission後のPod状態の観測ではありません。過去のロードマップレポート、ローカルプロトタイプのチェック、Spot測定値を区別し、E10は別途実行してください。

</details>
