# Part 3: SageMaker AI と MLflow の実行

実践的な学習を始めるには、[QLoRA トレーニングワークショップ](05-qlora-finetuning-workshop.md)から始めてください。この章では、既存の実装と運用上の契約について説明します。

> **最終更新日**: September 12, 2026

## 実行に関する注意

**コミット済みの GPU 実行パスは、現在イメージがパッチ提供期間の終了に達しているためブロックされています。** 公式カタログでは、`2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker` のパッチ提供終了日が `2026-08-06` とされています。`src/runtime_contract.py` は、事前チェック、プロビジョニング、Training Job の送信、EKS の作成、トレーニングの前にこの境界を確認します。イメージ、`torch`、依存関係の一式をまとめて更新し、GPU スモークテストを検証してください。日付チェックだけを削除しても、ランタイムのアップグレードにはなりません。

この章では、`examples/ai-ml/qwen-pii-finetuning/` にある修正済みの契約について説明します。ローカルテスト、リクエストのプレビュー、所有リソースのクリーンアップは引き続き利用できます。2026 年 9 月 1 日の AWS 実験は、**トレーニングの送信前に停止しました**。今回のレビューでも、AWS リソースの作成や GPU トレーニングは行っていません。

AWS は、新しい SageMaker 管理 MLflow デプロイメントには **MLflow Apps** を推奨しています。既存の Tracking Server は別のリソースです。現行の App ドキュメントには MLflow `3.10` と記載されていますが、この過去の例ではクライアントと EKS サーバーに `3.1.4` を固定しています。ローカルで `3.1.4` のアーティファクトを正常にエクスポートできても、管理対象 App との完全な互換性が検証されたことにはなりません。ランタイムのアップグレード検証には、この組み合わせも含めてください。

## 管理対象パスの 8 つのステップ

### 1. 読み取り専用の事前チェック

**Python 3.12 仮想環境を有効化し**、パッケージ README に記載されている依存関係をインストールした状態で、次のコマンドを実行します。

```bash
cd examples/ai-ml/qwen-pii-finetuning
export AWS_REGION=ap-northeast-2
python3 src/runtime_contract.py --check-execution
```

現時点では、このコマンドはパッチ提供期間の終了に関する説明とともに失敗するはずです。例をサポート対象のランタイムにアップグレードした後、管理者が確認した `EXPECTED_ACCOUNT_ID`、`DATAZONE_DOMAIN_ID`、`DATAZONE_PROJECT_PROFILE_ID`、`DATAZONE_OWNER_GROUP_ID` を設定し、`./launch/aws/preflight.sh` を実行してください。これらの変数に含まれるのはリソース識別子であり、パスワードやサービスアカウントキーではありません。

事前チェックでは、ツール、呼び出し元、リージョン、クォータ、DLC、既存の実験との衝突を確認します。表示名や STS ロール文字列からドメイン、プロファイル、グループを再構成することはありません。リストが空でも、あらゆる状況でリソースが存在しないことや、後続の作成が許可されていることの証明にはなりません。プレフィックスを共有するリソースの所有者を確認し、無差別に削除しないでください。

### 2. ソースバンドルのビルド

```bash
./launch/aws/build_source_bundle.sh
```

バンドルには `src/*.py`、`config/experiment.yaml`、`requirements.lock`、およびそれと同一の `requirements.txt` が含まれます。データやローカルの認証情報ファイルを再帰的にパッケージ化することはありません。ソースや構成に直接埋め込まれた機密値は検出しないため、バンドルを確認してください。その SHA-256 は**そのビルド**を識別するものであり、tar のタイムスタンプが再現可能である保証はありません。

### 3. MLflow App と Unified Studio プロジェクトの作成

これは **AWS に変更を加え、料金が発生するステップ**であり、ランタイムと権限の検証後にのみ実行できます。

```bash
./launch/aws/provision.sh
```

この処理では、実験用バケット、実行ロールと MLflow ロール、MLflow App、オーナーメンバーシップを持つプロジェクトを作成します。バケットでは Block Public Access、AES-256、バージョニングを使用し、IAM ポリシーは Access Analyzer で確認されます。App の準備完了状態は `Created`/`Updated` です。プロジェクトの `ACTIVE` は、すべてのプロジェクト環境のデプロイ成功を意味しません。

非公開インベントリでは、作成を試みた状態と成功した応答を区別します。名前の衝突や応答の喪失があっても、名前を指定した削除が許可されるわけではありません。エラー時のクリーンアップは、所有が確認できたリソースを対象とします。作成状況が不明な場合は、照合が必要です。強制終了されたプロセスやインスタンスでは、シェルの trap が実行されないことがあります。

### 4. データセットのアップロード

アップロード前に、バケットとインベントリを作成します。次の 5 つの入力を検証します。

```bash
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json
# Actual S3 upload and SHA-256 readback verification:
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json --execute
```

入力は `generated/source.tar.gz`、`data/{train,validation,test}.jsonl`、`data/dataset-manifest.json` です。このヘルパーは分割データのハッシュ、バケットのアカウント所有権、実験タグを確認し、実行ごとの `qwen-pii/<experiment-id>/source/` および `dataset/` プレフィックスに書き込みます。オブジェクトを読み戻して SHA-256 を比較します。この小規模な合成データの例では、各ファイルのサイズは 64 MiB 以下に制限されています。アップロードに失敗すると、一部のオブジェクトが残ることがあるため、インベントリを保管してください。

非公開の運用記録には、識別子とハッシュを使用してください。署名付き URL はアクセス権限を付与するため、公開ドキュメントやログに投稿してはいけません。

### 5. SageMaker Training Job リクエストの送信

```bash
python3 -m launch.sagemaker_train \
  --mode smoke --inventory results/resource-inventory.json
```

デフォルトでは、AWS に送信せず、`results/previews/` に一意の名前を付けた JSON ファイルを書き込みます。送信済みの `<job-name>-request.json` や `<job-name>-job.json` を上書きすることはありません。サポート対象のランタイムを検証した後、送信するには `--execute` を追加します。全量実行には、別途 `--mode full --execute` が必要です。ランチャーはスモークテストの証跡や入力ハッシュを自動承認しません。

構成は、ソースバンドル内の `/opt/ml/code/config/experiment.yaml` から読み込まれます。4 つのデータファイルは `/opt/ml/input/data/dataset/` に配置されます。内容が一致するよう、ローカルの `--config` とバンドルは同じソースからビルドしてください。

送信前に、ランチャーはクリーンアップツールと共有のロックを取得し、リクエストとジョブジャーナルの両方を予約します。ジョブの作成に成功した後、監視に失敗したり中断されたりすると、停止リクエストの送信が試みられます。`stop_requested` は終了が確認されたことを意味しません。`submission_unknown`、`stop_unconfirmed`、またはホスト喪失の後は、AWS の状態と所有権を照合してください。再送信のために既存のジャーナルや孤立したリクエストを上書きしないでください。

過去の構成では、`ml.g6e.4xlarge` を 1 台、300 GiB、スモークテスト 10 ステップ、全量実行 80 ステップ、`MaxRuntimeInSeconds: 10800` を指定しています。この制限は、終了処理、アップロード、MLflow、S3、その他のリソースを含む総費用を制限するものではありません。

### 6. スモークテスト／全量実行のゲート

実行を再び有効にする前に、サポート対象のイメージ、依存関係、MLflow の組み合わせを検証してください。その後、スモークテストの最終状態、データセットのハッシュ、メトリクス、アダプターファイルを確認します。ログと MLflow に、ソーステキスト、エンティティ値、対応付け、または未加工の出力が含まれていないか確認してください。**アーティファクトのファイル名を許可リストで管理しても、内容の安全性は証明されません。** この手順は、自動 PII スキャナーが実装済みであることを意味しません。

### 7. 集計結果のエクスポート

| ファイル | 意味 |
|---|---|
| `dataset-manifest.json` | 生成時の設定、件数、分割データのハッシュ |
| `resolved-config.json` | 実際の設定、環境、ステップ数 |
| `dependency-versions.json` | 観測されたインストール済みバージョン。完全なロックが保証されるわけではない |
| `baseline-metrics.json`, `tuned-metrics.json` | 同じテスト分割データを使った集計評価 |
| `run-summary.json` | フェーズごとの所要時間、メトリクス、アダプターの一覧 |
| `adapter/adapter_config.json`, `adapter/adapter_model.safetensors` | MLflow に保存された最終アダプター |

SageMaker の `/opt/ml/model` 出力と MLflow アーティファクトは、保存場所が異なります。バケットや App を削除する前に、必要な結果をダウンロードして検証してください。アダプターを共有する前に、内容とアクセス権限を確認してください。未加工の予測、トークンの対応付け、中間チェックポイントはエクスポートされません。

`peak_gpu_memory_bytes` は、モデル読み込み後にリセットした CUDA のデフォルトデバイスについて、PyTorch が割り当てたメモリのピーク値です。GPU メモリの総量でも、読み込み時のピークでも、複数デバイスの合計でもありません。性能向上やコスト比較を公表する根拠となるトレーニング結果は存在しません。

### 8. ティアダウンと検証

```bash
./launch/aws/teardown.sh
./launch/aws/verify_cleanup.sh
```

まず記録済みの Training Job を確認して停止します。トレーニング記録がある場合、ティアダウンは再度停止処理を行い、エクスポート前にそれらのアーティファクトバケットが削除されるのを防ぎます。必要な SageMaker/MLflow アーティファクトを別途保存した後にのみ、次に進んでください。

```bash
./launch/aws/teardown.sh results/resource-inventory.json \
  --discard-training-artifacts
```

このフラグはバックアップを実行しません。所有する EKS リソースが残っている場合、共通のティアダウン処理も停止します。以下の手動復旧を行うか、EKS パスでエクスポートと削除を検証してから進んでください。その後、所有が確認された App、プロジェクト、S3、IAM リソースをクリーンアップします。AWS の `AccessDenied`、通信障害、削除のタイムアウト、S3 のオブジェクト単位のエラーを、リソースが存在しないことの証明として扱ってはいけません。所有権の証拠がない古いインベントリは、管理者による照合が必要です。このツールは、共有の TrainingJobs ロググループや無関係なリソースを削除しません。

残存状態や不明な状態があれば、検証は失敗します。成功の対象範囲は、照会したアカウント、リージョン、インベントリ、チェックに限られ、AWS アカウント全体が空であることを証明するものではありません。クリーンアップが不完全だったり、クラスターが残っていたりすると、料金が発生し続ける可能性があります。

## EKS + MLflow の比較パス

ランタイムのアップグレード後、エントリーポイントは `./launch/eks/run.sh smoke` と、別途レビューした後の `./launch/eks/run.sh full` です。現時点では、パッチ提供期間の終了に関するガードで停止します。

| 項目 | 例における契約と制限 |
|---|---|
| クラスター | テンプレートは EKS `1.36`、`g6e.4xlarge` を 1 台使用。リージョンでの提供状況とサポートを再確認する |
| GPU プラグイン | `0.20.0` に固定。新しい DLC、AMI、ドライバーとの組み合わせで検証する |
| kubeconfig | 実行ごとのファイルと明示的なコンテキストを使用。既存クラスターとの衝突は拒否する |
| MLflow | ClusterIP、SQLite、`emptyDir` を使用。アプリケーション認証、永続ストレージ、テナント分離はない |
| データ | ServiceAccount にスコープを限定した AWS 権限を使う S3 SDK。マニフェストの SHA-256 とバケットのアカウントを検証する |
| Job | `backoffLimit: 0`、`activeDeadlineSeconds: 10800`。障害時に 3 時間以内にすべてのリソースが確実に解放されるわけではない |
| エクスポート | 実験、クラスター、実行 ID が一致する完了済みの実行から、8 個のアーティファクトと SHA-256 を検証する |
| シャットダウン | エクスポートとハッシュの検証後に所有クラスターをクリーンアップする。エクスポートに失敗すると、復旧のためクラスターが残ることがある |

入力ローダーは ConfigMap からコードとアップロードのハッシュを読み込み、EKS Pod Identity を使って 5 つの S3 オブジェクトのみをダウンロードします。ServiceAccount は `qwen-input-reader` です。Pod Identity Agent、サポート対象の SDK、関連付けが必要です。EC2 インスタンスメタデータからの認証情報へのフォールバックは無効になっています。これによって、期限切れの DLC に対する実行ゲートが解除されるわけではありません。

トレーニングと MLflow の Pod の `emptyDir` データは、Pod またはクラスターの削除とともに失われます。実行ごとの `results/eks-<mode>.<suffix>/mlflow-export-<mode>.tar.gz` とエクスポートレシートはローカルファイルであり、ホスト外のバックアップではありません。別途承認されたストレージにコピーし、クリーンアップを検証してください。

トレーニングの実行に失敗し、完了した実行やエクスポートがない場合、自動削除の条件を満たせません。非公開インベントリに記録されたアカウント、クラスター ARN、作成日時、所有権タグ、スタック ID を AWS と照合してください。必要な結果を復旧するか明示的に破棄した後、**所有するそのクラスターだけ**を `eksctl delete cluster --name ... --region ... --wait` で削除してください。作成が一部だけ完了した場合や応答を失った場合も、手動での照合が必要です。その後 `verify_cleanup.sh` を実行し、スタック削除後に残ったリソースを調査してください。検証を回避するために所有権フラグを捏造してはいけません。

## 観測されたエラーと停止条件

| 状況 | 対応 |
|---|---|
| DLC がパッチ提供期間の終了に達した | 作成／トレーニングをブロックし、ランタイム一式をアップグレードする |
| 誤った構成パス | ソースバンドルから構成を読み込む |
| 名前の衝突、または作成応答の喪失 | 所有権が確認できない場合は自動削除を拒否する |
| エクスポートの欠落または失敗 | アダプターと集計ファイルを検証するまで成功を宣言しない |
| クエリの認可エラーまたは削除のタイムアウト | 不明／失敗として記録する |
| 過去のプロジェクトメンバーシップの欠落 | ドメイン管理者およびプロジェクトオーナーと照合する |

## パスの選択

SageMaker を使うと Training Job と MLflow の運用作業を減らせますが、アーティファクトの保持、権限、実験のクリーンアップには引き続き対応が必要です。EKS では Kubernetes を制御できる一方、クラスター、GPU プラグイン、MLflow ストレージの管理責任が加わります。比較する際は、構成、データハッシュ、モデルのリビジョン、実際の依存関係、GPU 環境を一緒に記録してください。

## 主な情報源

- [AWS DLC PyTorch 2.8 カタログとパッチ提供終了](https://github.com/aws/deep-learning-containers/blob/main/docs/src/data/pytorch-training/2.8-gpu-sagemaker.yml)
- [SageMaker Training Toolkit のコードディレクトリ](https://github.com/aws/sagemaker-training-toolkit/blob/master/src/sagemaker_training/entry_point.py)
- [MLflow App のセットアップ](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow-app-setup.html)
- [SageMaker MLflow のバージョン](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow.html)
- [S3 署名付き URL の有効期限](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [EKS Pod Identity の動作と制限](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Kubernetes Job の失敗と終了](https://kubernetes.io/docs/concepts/workloads/controllers/job/)

前へ: [Part 2: 合成 PII データとトークン化](02-pii-data-tokenization.md)

次へ: [Part 4: Unified Studio のガバナンス](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
