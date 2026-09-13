# パート6: KServe — Kubernetes 上のモデルサービング

> **レビュー基準**: KServe 0.18.0 / Models Web Application 0.18.0 / Community Distribution 26.03.1
> **最終更新**: September 12, 2026

## ラボ環境のセットアップ

互換性のある Kubernetes、KServe controller/CRD、ServingRuntime、ストレージアクセス、および認証済みのネットワーク経路を使用します。完全な Kubeflow は必須ではなく、web app は任意です。Knative モードには Knative Serving/networking が必要であり、Standard の KEDA パスには KEDA とメトリクスプロバイダーが必要です。GPU はワークロードに依存します。

## KServe と Kubeflow

KServe は KFServing から発展し、独立したサービングプロジェクトになりました。この章では、Community Distribution 26.03.1 にバンドルされた **KServe および Models Web Application 0.18.0** を取り上げます。確認した最新の公開 KServe リリースは **0.20.0（2026年8月6日）** ですが、distribution の 0.18.0 基準とは異なります。

Controller、CRD、web app はそれぞれ別の成果物であり、互換性の確認が必要です。これらのバージョン番号は常に一致するとも、常に異なるとも限りません。実際の image、CRD schema、および web-app revision を記録してください。

ここで扱うサービング API は `InferenceService` であり、KServe アーキテクチャ全体ではありません。ServingRuntime/ClusterServingRuntime、ModelMesh、および別個の LLMInferenceService API には、それぞれ異なる依存関係と運用モデルがあります。

## InferenceService: Predictor、Transformer、Explainer

InferenceService には必須の predictor と、任意の transformer/explainer があります。Predictor はモデルサーバーを設定し、transformer は前処理/後処理を提供し、explainer は説明リクエストを処理します。説明はすべての予測に自動的に付加されるわけではなく、runtime/protocol のサポートが重要です。

modelFormat、ServingRuntime、ファイルレイアウト/library version、URI/認証情報、port/probe、およびリクエスト protocol を一致させてください。URI だけでは、すべてのモデルを提供可能にはできません。Custom container も、client contract と KServe の routing/health-check 要件を満たす必要があります。

公式の runtime-config chart は、デフォルトではリソースを出力しません。`kserve.servingruntime.enabled=true` を使用してレンダリングすると、12 個の ClusterServingRuntime が生成されます。catalog に存在することは、image の最新性、security support、またはモデル互換性を保証するものではありません。

TorchServe の [project notice](https://github.com/pytorch/serve) では、新機能、bug fix、security patch は今後予定されていないとされています。古い runtime catalog に含まれていても、新しい本番用途において保守されているデフォルトになるわけではありません。モデル形式と GPU 要件に対応する、保守された runtime を検証してください。

## Deployment モード: Knative と Standard

0.18.0 での名称は **Knative** と **Standard** です。Serverless と RawDeployment の annotation 値は、これらの名称に正規化される非推奨の alias です。serving.kserve.io/deploymentMode と、インストール済みの inferenceservice-config を確認してください。コードの fallback は Standard ですが、ダウンロードした OCI resource chart のデフォルトは Knative です。用語だけからインストール時のデフォルトを推測しないでください。

| 項目 | Knative | Standard |
| --- | --- | --- |
| Workload リソース | Knative Service/Revision パス | Deployment/Service と選択した autoscaler |
| スケールダウン | KPA/policy のサポートと minReplicas=0 によりゼロが可能 | デフォルトの HPA パスでは少なくとも 1 つを維持する。KEDA は適切な外部アクティベーションシグナルによりゼロをサポートできる |
| デフォルトの minReplicas | KServe のデフォルトは 1。Knative を選択するだけではゼロは有効にならない | HPA は要求されたゼロを少なくとも 1 に制限する |
| 依存関係 | Knative Serving/networking と選択した autoscaler | 選択した ingress/gateway、HPA metrics または KEDA など |
| 起動レイテンシー | ゼロから起動する際の scheduling/image/model loading | warm replica があっても、restart、rollout、scale-out では起動レイテンシーが発生する |

どちらのモードも、利用可能な replica やレイテンシー SLA を保証しません。model loading、readiness、capacity、timeout、および recovery を検証してください。KEDA のゼロからのスケールには、実行中の Pod がなくても観測可能なシグナルと再アクティベーション経路が必要です。CPU/memory metrics だけでは、リクエスト駆動のアクティベーションを意味しません。

![InferenceService の reconciliation は、実行中のモデルサーバーへのリクエストとは別です。Knative と Standard のパスは、条件付きの autoscaling 動作を示しています。](../../.gitbook/assets/en-ai-ml-kubeflow-06-kserve-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-06-kserve-0.html)

## Autoscaling と Metrics

Knative KPA は concurrency/RPS をサポートしますが、Knative の HPA class は別のパスです。Standard は serving.kserve.io/autoscalerClass を通じて hpa、keda、または external/none を選択します。すべての Standard Deployment が HPA を作成するわけではありません。

CPU、external、またはサポートされる Pod metrics には、実際の metrics-server/adapter/provider の依存関係が必要です。GPU request は GPU metrics を自動的に作成しません。レスポンス速度は観測間隔、stabilization、およびモデルの動作に依存します。concurrency metrics が常に高速であるわけではありません。

## 段階的更新と Canary Traffic

このバージョンの canaryTrafficPercent は、**Knative Revision の traffic-splitting パス**で確認されました。KServe は、直前に rollout された revision と新しい revision を Knative Service の traffic target として設定し、Knative networking がリクエストを分散します。KServe controller は、すべての inference call の proxy ではありません。

Standard Deployment の rolling update を、その revision-percentage routing と同一視しないでください。Standard での weighted routing には、別途設計された service/gateway/mesh または rollout tooling と、明確な所有権が必要です。[Istio traffic management](../../service-mesh/istio/traffic-management/04-traffic-splitting.md) または [Argo Rollouts](../../service-mesh/istio/advanced/08-argo-rollouts.md) を使用する場合は、KServe 管理 object との所有権の競合を避けてください。

割合だけでは品質の検証や promotion/rollback の自動化はできません。比較 metrics、error/latency、保持された revision/model artifact、および route readiness を確認してください。

## EKS での GPU Inference

Pod の nvidia.com/gpu request は scheduling/device allocation を有効にします。実際の GPU inference には、互換性のある CUDA/driver、server image、model backend、および device configuration が必要です。Triton model configuration または framework の device selection を確認してください。GPU request により、CPU モデルが自動的に GPU へ移行するわけではありません。

Karpenter は、条件を満たす Pending Pod、NodePool、quota、および利用可能な capacity に対して provisioning を行います。KServe/Knative/HPA/KEDA の Pod scaling と、EC2 の provisioning/reclamation は別のループです。model Pod がゼロであっても、他の workload や disruption policy により node とコストが稼働し続ける場合があります。

## 検証とソース

公式の 0.18.0 OCI CRD/resource/runtime-config chart をローカルで pull および render して、schema/config を確認しました。mode aliasing、HPA minimum、KEDA ScaledObject、および Knative traffic のコードをレビューしました。モデルの download/serving、GPU、cluster autoscaling、または実際の canary request は実行していません。

- [0.18.0 のモード名とデフォルト](https://github.com/kserve/kserve/blob/v0.18.0/pkg/constants/constants.go)
- [HPA の最小 replica 処理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/hpa/hpa_reconciler.go)
- [KEDA ScaledObject 処理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/keda/keda_reconciler.go)
- [Knative traffic 処理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/knative/ksvc_reconciler.go)
- [0.20.0 リリース](https://github.com/kserve/kserve/releases/tag/v0.20.0)

## 次のステップ

このサービングパスを、[Kubeflow series](README.md) の architecture、Pipelines、Notebooks、Katib、および Trainer の各章につなげつつ、model-artifact deployment と検証は別個のステップとして扱ってください。

---

[メインページに戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../../quizzes/ai-ml/kubeflow/06-kserve-quiz.md) に挑戦してください。
