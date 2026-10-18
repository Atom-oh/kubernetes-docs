# SageMaker AI で PII 向けに Qwen をファインチューニングする

> **最終更新日**: 2026年9月16日

合成データを使った CPU 演習と QLoRA の手順を含みます。別のランタイムで、2026年9月16日に実際の GPU スモーク実行を完了しました。9月1日のプロビジョニングに関する所見は、引き続き履歴記録です。

このガイドでは、文書から PII 候補を抽出するモデルのトレーニングと評価方法を説明します。アノテーションの取り決めを定め、データ漏洩を防いでデータを分割・拡張し、QLoRA 設定を選択して、見落としと過剰なマスキングの両方を測定します。

モデルは `TYPE<TAB>ORIGINAL` 形式の候補を出力します。Python コードがそれらを検証して置換します。モデル自体は文書全体を書き換えません。この分離により、検出エラーと置換バグを区別できます。

## 実践的な学習パスから始める

| 順序 | 章 | 完了後に説明できること |
| --- | --- | --- |
| 1 | [合成データと拡張](06-data-augmentation-workshop.md) | アノテーションの取り決め、データ群の分離、訓練データだけへの拡張、ソースとラベルの監査 |
| 2 | [QLoRA トレーニングと SageMaker ワークフロー](05-qlora-finetuning-workshop.md) | NF4、LoRA、損失マスク、実際に対象となるモジュール、バッチ数とステップ数の予算、調整と診断 |
| 3 | [PII 評価とマスキングパイプライン](07-pii-evaluation-release.md) | 再現率/F1、残存する PII、PII を含まない文書への誤ったマスキング、最終評価と合格基準 |
| 4 | [SageMaker AI と MLflow の実行契約](03-sagemaker-mlflow-execution.md) | ソース一式、S3 入力チャネル、Training Job、成果物、クリーンアップ |

Python 3.12 と JSONL を使える場合は、データと評価から始めてください。どちらの CPU 演習にも AWS アカウントやモデルの重みは必要ありません。トレーニングの手順説明や GPU 確認手順は、GPU トレーニングを実際に完了した証拠にはなりません。

新しい拡張演習では、合成データの40群を先に分割し、その後で訓練データだけを拡張します。この演習用データセットは、2,200件のレコードを含む旧 generator 1.0.0 のデータセットを上書きしません。小規模な演習や正解を既知とする評価のスコアは、実運用でのモデル性能を示すものではありません。

## SageMaker 実行の準備状況 {#sagemaker-execution-readiness}

[GPU スモーク実行の実績記録](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/execution-smoke-20260916.json)には、2026年9月16日に別の実行経路で PyTorch 2.11/AL2023/CUDA 13 を使った記録があります。同じ Qwen モデルを NF4 で読み込み、アテンションの4つの射影にランク16の LoRA を適用しました。最適化を4ステップ実行した結果、アダプターの重みが変化し、保存後に再読み込みした状態も一致しました。課金対象の1,140秒から算出した GPU 計算費用は約1.46米ドルです。ストレージ、ログ、税金、請求調整分は含みません。

生成の評価対象は合成検証文書4件だけです。ベースラインのエンティティF1は1.0000でしたが、所定の形式で応答できたのは4件中2件でした。調整後のモデルはF1が0.8125で、4件すべてが所定の形式でしたが、誤検出したエンティティの組を6件追加しました。**実行に成功したことは、品質が向上した証拠ではありません。** 同日、全規模の600ステップ訓練ジョブが送信されましたが、この記録には最終テストの結果は含まれていません。このジョブでは、独立した400件のテストセットを評価する前に、検証損失に基づいてチェックポイントを選択します。[実行設定と成果物の保持](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/README.md#recorded-gpu-execution-september-16-2026)を参照してください。

旧パッケージでは、マネージド SageMaker Training Job または一時的な EKS GPU Job で Qwen/Qwen3-30B-A3B-Instruct-2507 を訓練する設計を提案しています。どちらの GPU 実行経路にも、最初から最後まで成功した記録はありません。

旧経路で固定されていた PyTorch 2.8 DLC は、2026年8月6日にパッチ提供を終了しました。そのため、リソースの作成と GPU 実行は引き続きブロックされています。イメージ、依存パッケージ、MLflow の組み合わせを一体として検証するには、[QLoRA ランタイムの説明](05-qlora-finetuning-workshop.md)と[実行契約](03-sagemaker-mlflow-execution.md)に従ってください。サポート確認のチェックだけを削除しても、ランタイムの移行にはなりません。

## 設計と実装を詳しく読む

| ドキュメント | 目的 |
| --- | --- |
| [パート 1: プラットフォームアーキテクチャ](01-platform-architecture.md) | モデル、データ、Python 処理、MLflow の責務 |
| [パート 2: データと決定論的トークン化](02-pii-data-tokenization.md) | 旧データセットの9種類のラベル、置換範囲、指標の正確な定義 |
| [パート 3: 実行](03-sagemaker-mlflow-execution.md) | SageMaker/EKS の送信、永続化、復旧、クリーンアップ |
| [パート 4: Unified Studio ガバナンス](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | ドメイン、プロジェクト、メンバーシップ |
| [パート 5: 事実に基づく検証記録](04-validation-results.md) | 実行済みの作業、未実行の作業、過去の記録に残るリソース |

## 検証記録の解釈

- 新しいデータ処理・評価コマンドは、合成入力を使って CPU 上で確認されています。訓練済みモデルのF1、GPUの最大メモリ使用量、訓練時間を確認するには、別途測定が必要です。
- 2026年9月12日のレビューでは、トークン化、評価、実行、クリーンアップを対象とするローカル回帰テストが追加されました。
- 2026年9月1日の AWS 記録では、クォータと MLflow App/プロジェクトのプロビジョニング失敗経路を確認し、GPU ジョブの送信前に作業を停止しました。
- その記録では、実験用の App、S3、IAM リソースを削除しましたが、Unified Studio のプロジェクトが1つ残りました。現在の状態を確認するには、改めて棚卸しする必要があります。

ソース、抽出値、トークン対応表、生の生成結果を一般ログや MLflow のパラメーター/タグに記録しないでください。実行環境の自動記録・トレース機能と成果物の内容も確認してください。元に戻せる対応表、訓練済みアダプター、非公開のリソース台帳は別々に扱い、それぞれの保持期間とアクセス要件を定めてください。

サンプルパッケージ: `examples/ai-ml/qwen-pii-finetuning/`。各ワークショップには、使用する CLI と出力例が記載されています。

## 参考資料

- [Qwen モデルカード](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA 論文](https://arxiv.org/abs/2305.14314)
- [実験設定](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [履歴上のプロビジョニング結果](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
