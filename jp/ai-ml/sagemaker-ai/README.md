# SageMaker AI で PII 向けに Qwen をファインチューニングする

> **最終更新**: September 15, 2026

合成データの CPU 演習と QLoRA の手順が含まれています。AWS プロビジョニングに関する所見は、2026 年 9 月 1 日時点の履歴記録です。

このガイドでは、ドキュメントから PII 候補を抽出するモデルをトレーニングおよび評価する方法を説明します。アノテーション契約を定義し、データリークなしでデータを分割・拡張し、QLoRA 設定を選択して、見逃しと過剰なマスキングの両方を測定します。

モデルは `TYPE<TAB>ORIGINAL` 形式の候補を出力します。Python コードがそれらを検証して置換します。モデルはドキュメント全体を書き換えません。この分離により、検出エラーと置換バグを区別できます。

## 実践的な学習パスから始める

| 順序 | 章 | この後に説明できるようになること |
| --- | --- | --- |
| 1 | [合成データと拡張](06-data-augmentation-workshop.md) | アノテーション契約、ファミリー分離、トレーニング専用の拡張、ソース/ラベル監査 |
| 2 | [QLoRA トレーニングと SageMaker ワークフロー](05-qlora-finetuning-workshop.md) | NF4、LoRA、loss mask、実際の target module、batch/step budget、チューニングと診断 |
| 3 | [PII 評価とマスキングパイプライン](07-pii-evaluation-release.md) | Recall/F1、残存 PII、ネガティブドキュメントのマスキング、最終評価と受け入れ |
| 4 | [SageMaker AI と MLflow の実行契約](03-sagemaker-mlflow-execution.md) | ソースバンドル、S3 channel、Training Job、artifact、クリーンアップ |

Python 3.12 と JSONL を使用できる場合は、データと評価から始めてください。どちらの CPU 演習にも AWS アカウントやモデルの重みは必要ありません。トレーニングのウォークスルーと GPU チェック手順は、GPU トレーニングが完了した証拠とは別のものです。

新しい拡張演習では、トレーニングのみを拡張する前に 40 の合成ファミリーを分割します。その別個のデータセットは、2,200 レコードからなる履歴 generator 1.0.0 コーパスを上書きしません。小規模な演習や oracle スコアは、実世界のモデル性能を示すものではありません。

## SageMaker 実行の準備状況

履歴パッケージでは、マネージド SageMaker Training Job または一時的な EKS GPU Job による Qwen/Qwen3-30B-A3B-Instruct-2507 のトレーニングを提案しています。どちらの GPU パスにも、エンドツーエンドで成功した記録はありません。

固定された PyTorch 2.8 DLC は 2026-08-06 にパッチサポートを終了したため、リソース作成と GPU 実行はブロックされています。イメージ、依存関係、MLflow の組み合わせをまとめて検証するには、[QLoRA runtime discussion](05-qlora-finetuning-workshop.md) と [実行契約](03-sagemaker-mlflow-execution.md) に従ってください。サポートチェックだけを削除しても、移行手順にはなりません。

## 設計と実装を詳しく読む

| ドキュメント | 目的 |
| --- | --- |
| [パート 1: プラットフォームアーキテクチャ](01-platform-architecture.md) | モデル、データ、Python 処理、MLflow の責任範囲 |
| [パート 2: データと決定論的トークン化](02-pii-data-tokenization.md) | 履歴上の 9 種類のデータ、置換 span、正確なメトリクス定義 |
| [パート 3: 実行](03-sagemaker-mlflow-execution.md) | SageMaker/EKS の送信、永続化、リカバリ、クリーンアップ |
| [パート 4: Unified Studio ガバナンス](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Domain/project/membership |
| [パート 5: 事実に基づく検証記録](04-validation-results.md) | 実行済み作業、未実行作業、履歴上の残存リソース |

## 検証記録の解釈

- 新しいデータ/評価コマンドは、合成入力を使用して CPU で確認されています。トレーニング済みモデルの F1、GPU ピークメモリ、トレーニング時間には、別途測定が必要です。
- 2026-09-12 のレビューでは、トークン化、評価、実行、クリーンアップに対するローカルの regression coverage が追加されました。
- 2026-09-01 の AWS 記録は、quota と MLflow App/project プロビジョニングの失敗パスを対象としており、GPU 送信の前に停止しました。
- その記録では experiment App/S3/IAM リソースをクリーンアップしましたが、1 つの Unified Studio project が残されました。現在の状態を確認するには、新しいインベントリが必要です。

ソース、抽出値、token mapping、または生の completion を一般ログや MLflow parameter/tag に送信しないでください。実行環境内の autolog/tracing と artifact 内容も確認してください。可逆的な mapping、トレーニング済み adapter、プライベートなリソースインベントリは、それぞれ保持・アクセス要件が異なる別個の artifact です。

例示パッケージ: `examples/ai-ml/qwen-pii-finetuning/`。各ワークショップには、正確な CLI と出力例が記載されています。

## 参考資料

- [Qwen モデルカード](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA 論文](https://arxiv.org/abs/2305.14314)
- [実験設定](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [履歴上のプロビジョニング結果](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
