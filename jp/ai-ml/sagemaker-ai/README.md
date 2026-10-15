# SageMaker AI で PII 向けに Qwen をファインチューニングする

> **最終更新**: September 16, 2026

合成データを使った CPU 演習と QLoRA の手順を含みます。別のランタイムで、2026年9月16日に実際の GPU スモーク実行を完了しました。9月1日のプロビジョニングに関する所見は、引き続き履歴記録です。

このガイドでは、文書から PII 候補を抽出するモデルのトレーニングと評価方法を説明します。アノテーション契約を定義し、リークなくデータを分割・拡張し、QLoRA 設定を選択して、見落としと過剰なマスキングの両方を測定します。

モデルは `TYPE<TAB>ORIGINAL` 形式の候補を出力します。Python コードがそれらを検証して置換します。モデル自体は文書全体を書き換えません。この分離により、検出エラーと置換バグを区別できます。

## 実践的な学習パスから始める

| 順序 | 章 | 完了後に説明できること |
| --- | --- | --- |
| 1 | [合成データと拡張](06-data-augmentation-workshop.md) | アノテーション契約、ファミリー分離、トレーニングのみの拡張、ソース/ラベル監査 |
| 2 | [QLoRA トレーニングと SageMaker ワークフロー](05-qlora-finetuning-workshop.md) | NF4、LoRA、loss mask、実際の target module、batch/step 予算、チューニングと診断 |
| 3 | [PII 評価とマスキングパイプライン](07-pii-evaluation-release.md) | Recall/F1、残存 PII、negative document におけるマスキング、最終評価と受け入れ |
| 4 | [SageMaker AI と MLflow の実行契約](03-sagemaker-mlflow-execution.md) | source bundle、S3 channel、Training Job、artifact、クリーンアップ |

Python 3.12 と JSONL を使用できる場合は、データと評価から始めてください。どちらの CPU 演習にも AWS アカウントやモデルの重みは必要ありません。トレーニングのウォークスルーと GPU チェック手順は、完了した GPU トレーニングの証跡とは別のものです。

新しい拡張演習では、トレーニングデータのみを拡張する前に、40 の合成ファミリーを分割します。その別個のデータセットは、2,200 レコードからなる履歴上の generator 1.0.0 コーパスを上書きしません。小規模な演習または oracle スコアは、実運用におけるモデル性能の主張ではありません。

## SageMaker 実行の準備状況

[実際の GPU スモーク実行の記録](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/execution-smoke-20260916.json)には、2026年9月16日の PyTorch 2.11/AL2023/CUDA 13 による別のパスが記録されています。これは同じ Qwen モデルを NF4 でロードし、4 つの attention projection に rank-16 LoRA を適用します。4 回の optimizer step により、保存・再ロードした状態が一致する変更済み adapter weight が生成されました。請求対象の 1,140 秒は、ストレージ、ログ、税金、調整を除き、GPU コンピューティングがおよそ USD 1.46 であることを示します。

生成は合成 validation document 4 件のみを対象としました。baseline は entity F1 1.0000 でしたが、正しくフォーマットされた応答は 2/4 のみでした。チューニング済みモデルは F1 0.8125、フォーマット済み応答は 4/4 でしたが、6 件の false-positive entity pair を追加しました。**実行の成功は品質向上の証拠ではありません。** その日に 600-step の完全ジョブが送信されましたが、この記録には最終テスト結果は含まれていません。完全ジョブは、別個の 400-document test set を評価する前に validation loss に基づいて checkpoint を選択します。[実行設定と artifact 保持](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/README.md#recorded-gpu-execution-september-16-2026)を参照してください。

履歴上のパッケージでは、managed SageMaker Training Job または一時的な EKS GPU Job を通じて、Qwen/Qwen3-30B-A3B-Instruct-2507 のトレーニングを提案しています。どちらの GPU パスにも、エンドツーエンドの成功記録はありません。

その履歴上のパスで固定された PyTorch 2.8 DLC は 2026-08-06 に patch support を終了したため、resource creation と GPU 実行は引き続きブロックされています。image、dependency、MLflow の組み合わせをまとめて検証するには、[QLoRA ランタイムに関する説明](05-qlora-finetuning-workshop.md)と[実行契約](03-sagemaker-mlflow-execution.md)に従ってください。support check だけを削除しても、移行手順にはなりません。

## 設計と実装を詳しく読む

| ドキュメント | 目的 |
| --- | --- |
| [パート 1: プラットフォームアーキテクチャ](01-platform-architecture.md) | モデル、データ、Python 処理、MLflow の責務 |
| [パート 2: データと決定論的トークン化](02-pii-data-tokenization.md) | 履歴上の 9 タイプのデータ、置換 span、正確な metric 定義 |
| [パート 3: 実行](03-sagemaker-mlflow-execution.md) | SageMaker/EKS の送信、永続化、復旧、クリーンアップ |
| [パート 4: Unified Studio ガバナンス](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Domain/project/membership |
| [パート 5: 事実に基づく検証記録](04-validation-results.md) | 実行済み作業、未実行作業、履歴上の残存リソース |

## 検証記録の解釈

- 新しいデータ/評価コマンドは、合成入力を用いて CPU で確認されています。トレーニング済みモデルの F1、GPU peak memory、トレーニング時間には、別途測定が必要です。
- 2026-09-12 のレビューでは、tokenization、evaluation、execution、cleanup に対するローカル regression coverage が追加されました。
- 2026-09-01 の AWS 記録は quota と MLflow App/project のプロビジョニング失敗パスを対象としており、GPU 送信前に停止しました。
- その記録では experiment App/S3/IAM リソースをクリーンアップしましたが、1 つの Unified Studio project は残されています。現在の状態を確定するには、新しい inventory が必要です。

ソース、抽出した値、token mapping、raw completion を一般ログや MLflow parameter/tag に送信しないでください。実行環境内の autolog/tracing と artifact の内容も確認してください。reversible mapping、トレーニング済み adapter、private resource inventory は、それぞれ保持/アクセス要件が異なる別種の artifact です。

サンプルパッケージ: `examples/ai-ml/qwen-pii-finetuning/`。各ワークショップには、正確な CLI と出力例が用意されています。

## 参考資料

- [Qwen モデルカード](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA 論文](https://arxiv.org/abs/2305.14314)
- [実験設定](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [履歴上のプロビジョニング結果](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
