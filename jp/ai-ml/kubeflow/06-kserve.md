# パート 6: KServe（Kubernetes 上のモデルサービング）

> **確認対象バージョン**: KServe 0.18.0 / Models Web Application 0.18.0 / Community Distribution 26.03.1
> **最終更新日**: 2026年10月12日

## ラボ環境のセットアップ

互換性のある Kubernetes 環境、KServe コントローラーと CRD、ServingRuntime、ストレージへのアクセス、認証済みのネットワーク経路を用意してください。Kubeflow 全体の導入は必須ではなく、Web アプリも任意です。Knative モードでは Knative Serving とネットワーク機能が必要です。Standard モードで KEDA 経路を使う場合は、KEDA とメトリクスプロバイダーも必要です。GPU の要否はワークロードによります。

## KServe と Kubeflow

KServe は KFServing から発展し、独立したサービングプロジェクトになりました。この章では、Community Distribution 26.03.1 に含まれる **KServe と Models Web Application 0.18.0** を確認します。

2026年10月12日時点で確認した最新の公開 KServe リリースは **0.21.0**（2026年9月25日）です。その前に 0.20.0（2026年8月6日）がリリースされています。どちらも、このディストリビューションで確認する 0.18.0 の基準バージョンではありません。

コントローラー、CRD、Web アプリは別々の成果物であり、相互の互換性を確認する必要があります。バージョン番号は一致する場合も異なる場合もあります。実際に使うイメージ、CRD スキーマ、Web アプリのリビジョンを記録してください。

ここで扱う `InferenceService` はサービング API の一つであり、KServe アーキテクチャ全体を網羅するものではありません。ServingRuntime/ClusterServingRuntime、ModelMesh、別個の LLMInferenceService API では、依存関係や運用方法がそれぞれ異なります。

## InferenceService: Predictor、Transformer、Explainer

InferenceService では predictor が必須で、transformer と explainer は任意です。Predictor はモデルサーバーを構成し、transformer は前処理や後処理を行い、explainer は説明リクエストを処理します。すべての予測に説明が自動で付加されるわけではありません。対応状況はランタイムとプロトコルによります。

modelFormat、ServingRuntime、ファイル構成とライブラリのバージョン、URI と認証情報、ポートと probe、リクエストプロトコルを整合させてください。URI を指定しただけでは、どのモデルでもサービングできるわけではありません。カスタムコンテナもクライアントとの契約、および KServe のルーティングとヘルスチェックの要件を満たす必要があります。

公式の runtime-config chart は、デフォルトではリソースを生成しません。`kserve.servingruntime.enabled=true` を指定してレンダリングすると、12 個の ClusterServingRuntime が生成されます。カタログに掲載されているだけでは、イメージが最新であること、セキュリティサポートがあること、モデルと互換性があることの証明にはなりません。

TorchServe の[プロジェクト告知](https://github.com/pytorch/serve)には、新機能、バグ修正、セキュリティパッチを提供する予定はないと記載されています。古いランタイムカタログに含まれていても、新しい本番環境で使う保守対象のデフォルトにはなりません。モデル形式と GPU 要件に対応する、保守されているランタイムを検証してください。

## デプロイモード: Knative と Standard

0.18.0 での正式なモード名は **Knative** と **Standard** です。`Serverless` と `RawDeployment` は非推奨の annotation 値で、これらの名称に正規化されるエイリアスです。`serving.kserve.io/deploymentMode` と、インストール済みの `inferenceservice-config` を確認してください。コード上のフォールバックは Standard ですが、ダウンロードした OCI resource chart のデフォルトは Knative です。用語だけからインストール時のデフォルトを推測しないでください。

| 項目 | Knative | Standard |
| --- | --- | --- |
| ワークロードリソース | Knative Service/Revision 経路 | Deployment/Service と選択したオートスケーラー |
| スケールダウン | KPA とポリシーが対応し、`minReplicas=0` の場合はゼロまでスケール可能 | デフォルトの HPA 経路では最低 1 レプリカを維持します。KEDA なら適切な外部アクティベーションシグナルを使ってゼロまでスケールできます |
| デフォルトの最小レプリカ数 | KServe のデフォルトは 1 です。Knative を選んだだけではゼロになりません | HPA はゼロの指定を最低 1 に引き上げます |
| 依存関係 | Knative Serving/ネットワーク機能と選択したオートスケーラー | 選択した ingress/gateway、HPA のメトリクスまたは KEDA など |
| 起動レイテンシー | ゼロから起動する際のスケジューリング、イメージ取得、モデル読み込み | レプリカが起動済みでも、再起動、更新、スケールアウトには起動時間がかかります |

どちらのモードも、レプリカの可用性やレイテンシー SLA を保証しません。モデルの読み込み、readiness、容量、timeout、復旧を検証してください。KEDA でゼロからスケールするには、Pod が動作していない状態でも観測できるシグナルと再アクティベーション経路が必要です。CPU やメモリのメトリクスだけでは、リクエストに応じて起動することを意味しません。

![InferenceService の調整は、稼働中のモデルサーバーへのリクエスト処理とは別です。Knative と Standard の各経路で、条件付きのオートスケーリング動作を示しています。](../../.gitbook/assets/en-ai-ml-kubeflow-06-kserve-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-06-kserve-0.html)

## オートスケーリングとメトリクス

Knative KPA は同時実行数（concurrency）や RPS に基づくスケーリングに対応します。Knative の HPA クラスは別の方式です。Standard は `serving.kserve.io/autoscalerClass` により `hpa`、`keda`、`external`、`none` を選択します。Standard のデプロイがすべて HPA を作成するわけではありません。

CPU、外部、または対応する Pod メトリクスを使うには、実際の metrics-server、adapter、provider が必要です。GPU をリクエストしても GPU メトリクスが自動で作成されるわけではありません。応答速度は観測間隔、安定化の設定、モデルの動作に左右されます。同時実行数メトリクスが常に速い応答につながるとは限りません。

## 段階的な更新とカナリアトラフィック

このバージョンの `canaryTrafficPercent` は、**Knative Revision のトラフィック分割経路**で動作を確認しました。KServe は、直前にデプロイされた revision と新しい revision を Knative Service のトラフィック送信先に設定し、Knative のネットワーク機能がリクエストを振り分けます。KServe コントローラーがすべての推論リクエストを中継するわけではありません。

Standard の Deployment によるローリング更新を、この revision ごとの割合指定ルーティングと同一視しないでください。Standard で重み付きルーティングを行うには、個別に設計した Service、gateway、mesh、またはリリースツールと、明確な管理主体が必要です。[Istio のトラフィック管理](../../service-mesh/istio/traffic-management/04-traffic-splitting.md)や[Argo Rollouts](../../service-mesh/istio/advanced/08-argo-rollouts.md)を使う場合は、KServe 管理下のオブジェクトを複数の仕組みが重複して管理しないようにしてください。

割合を指定しただけでは、品質を検証したり、昇格やロールバックを自動化したりできません。比較用メトリクス、エラーとレイテンシー、保持中の revision とモデル成果物、ルートの readiness を確認してください。

## EKS 上の GPU 推論

Pod の `nvidia.com/gpu` リクエストは、スケジューリングとデバイス割り当てに使われます。実際に GPU で推論を実行するには、互換性のある CUDA/driver、サーバーイメージ、モデルバックエンド、デバイス設定が必要です。Triton のモデル設定、またはフレームワークによるデバイス選択を確認してください。GPU をリクエストしただけで、CPU 用モデルが自動的に GPU へ移るわけではありません。

Karpenter は、対象となる Pending Pod と NodePool、クォータ、利用可能な容量に応じてノードをプロビジョニングします。KServe/Knative/HPA/KEDA による Pod スケーリングと、EC2 のプロビジョニングや回収は別々の制御ループです。モデル Pod がゼロでも、他のワークロードや中断ポリシーによってノードが残り、費用が発生し続ける場合があります。

## 検証と参照元

公式の 0.18.0 OCI CRD、resource、runtime-config 各 chart を取得してローカルでレンダリングし、スキーマと設定を確認しました。モードのエイリアス処理、HPA の最小レプリカ数、KEDA ScaledObject、Knative のトラフィック処理に関するコードも確認しました。モデルのダウンロードやサービング、GPU、クラスターのオートスケーリング、実トラフィックによるカナリア試験は実施していません。

- [0.18.0 のモード名とデフォルト](https://github.com/kserve/kserve/blob/v0.18.0/pkg/constants/constants.go)
- [HPA の最小レプリカ数の処理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/hpa/hpa_reconciler.go)
- [KEDA ScaledObject の処理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/keda/keda_reconciler.go)
- [Knative のトラフィック処理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/knative/ksvc_reconciler.go)
- [0.20.0 リリース](https://github.com/kserve/kserve/releases/tag/v0.20.0)
- [0.21.0 リリース（確認時点で最新）](https://github.com/kserve/kserve/releases/tag/v0.21.0)

## 次のステップ

モデル成果物のデプロイと検証は別の手順として扱いつつ、このサービング経路を[Kubeflow シリーズ](README.md)のアーキテクチャ、Pipelines、Notebooks、Katib、Trainer の各章につなげてください。

---

[メインページに戻る](./README.md)

## クイズ

この章の学習内容を確認するには、[トピック別クイズ](../../quizzes/ai-ml/kubeflow/06-kserve-quiz.md)に挑戦してください。
