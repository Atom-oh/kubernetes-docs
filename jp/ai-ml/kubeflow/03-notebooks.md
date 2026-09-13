# パート 3: Kubeflow Notebooks

> **サポート対象バージョン**: Kubeflow Notebooks 1.11.0; Community Distribution 26.03.1
> **最終更新**: September 12, 2026

## ラボ環境のセットアップ

互換性のある Kubernetes cluster、Notebooks 1.11.0 controller/web app、namespace 権限、storage、および認証済みアクセスパスを使用します。ディストリビューションの互換性については、[パート 1](01-architecture-installation.md)を参照してください。GPU workload には、サポートされる driver/device plugin と適切な node capacity が必要です。Karpenter は capacity provisioner の一つであり、notebook の前提条件ではありません。

## Kubeflow Notebooks とは？

Notebooks web app は、image/resource/volume 設定を含む `Notebook` を作成します。その controller は StatefulSet、Service、および設定されている場合は Istio VirtualService を管理します。StatefulSet controller が Pod を作成し、Kubernetes がそれらをスケジュールします。dashboard は web-app のエントリポイントであり、Pod creator や汎用 traffic proxy ではありません。

namespace スコープの Notebook resource には PodSpec が含まれ、GitOps または Kubernetes API 経由で管理することもできます。管理対象の StatefulSet を直接編集すると、reconciliation によって元に戻される可能性があります。

## バージョンのコンテキスト: Notebooks v1 と Workspaces

この章では、ディストリビューション 26.03.1 における **Notebooks v1.11.0** とその `Notebook` API を確認します。Workspaces は `Workspace` と `WorkspaceKind` を使用する別個の v2 design であり、CRD の drop-in replacement ではありません。

26.03.1 のリリース説明では Workspaces は beta とされていますが、tag 付きの controller/backend/frontend manifest は **v2.0.0-alpha.3** image を参照しています。リリースの表現とデプロイ済み image tag を区別してください。この確認では、v2 GA や v1 のサポート終了日を確定するものではありません。導入前に、実際の release、API、および migration support を検証してください。

## マルチテナンシーモデル: Profile と分離された Isolation Policy

完全な Kubeflow UI は、選択した Profile namespace に notebook を作成します。Profile は team member 間で共有でき、Notebook CRD 自体はすべての namespace に Profile があることを必須としていません。standalone installation と full-platform access model も異なります。

Profile の ownership/membership、RBAC、および Istio AuthorizationPolicy は access control の一部を提供します。これらは無関係な RBAC grant を取り消すものでも、すべての Pod traffic、storage access、AWS access を自動的に block するものでもありません。NetworkPolicy enforcement、Pod privilege、volume permission、workload IAM、および application authorization を個別に評価してください。

### 永続ストレージ

デフォルトの UI は通常、workspace PVC を `/home/jovyan` に mount します。**その volume に保存されたデータのみ**が Pod replacement をまたいで永続化されます。`/opt/conda`、system directory、または container writable layer にインストールされた package と、in-memory kernel state は、その PVC では保持されません。home directory 内の user package は永続化される場合がありますが、新しい image と互換性がなくなる可能性があります。

PVC/volume lifecycle、backup、および reclaim policy を確認してください。EBS ReadWriteOnce は、一つの **node** からの read/write mount を意味し、一つの Pod による排他的使用を意味するものではありません。Single-Pod enforcement には、CSI ReadWriteOncePod などの別個の support が必要です。EBS には AZ/attachment constraint があります。shared EFS storage には POSIX permission と concurrent-access design が必要です。

### Idle Culling

確認した v1.11.0 のデフォルトは、`ENABLE_CULLING=false`、`CULL_IDLE_TIME=1440`、および `IDLENESS_CHECK_PERIOD=1` です。時間の単位は分です。installation だけでは culling は有効になりません。

culler は Jupyter の `/api/kernels` と last activity を使用します。browser の終了や shell process 内の GPU work を包括的に検出するものではありません。RStudio/code-server が同じ API を公開するとは想定しないでください。request の失敗または空の kernel list では last-activity value が変更されないため、古い値でも stop につながる可能性があります。有効化前に、実際の image と access policy で検出を検証してください。

culling は stop annotation を追加し、PVC を削除せずに StatefulSet replica を zero に減らします。Pod request を解放しても、必ずしも EC2 node が終了するわけではありません。ほかの workload、PDB、および Karpenter policy/budget も影響します。node が終了するまで instance charge は継続する可能性があります。

## Notebook Reconciliation Flow

![Notebook web app が CR を作成し、controller が StatefulSet、Service、および routing を reconciliation する一方、Kubernetes が Pod を作成して配置します。](../../.gitbook/assets/en-ai-ml-kubeflow-03-notebooks-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-03-notebooks-0.html)

Notebook v1.11.0 には `spec.replicas` field がありません。controller は `kubeflow-resource-stopped` が**存在する**場合に StatefulSet replica を zero にし、存在しない場合に one にします。値が `"false"` であっても stop します。resume するには annotation の値を変更するのではなく、annotation を削除してください。

```bash
# Stop the selected notebook: active kernels/processes terminate.
kubectl annotate notebook -n team-a analysis \
  kubeflow-resource-stopped="2026-09-12T00:00:00Z" --overwrite
# Resume by removing the annotation.
kubectl annotate notebook -n team-a analysis kubeflow-resource-stopped-
```

この timestamp は annotation format の例です。これらの command を実行する前に、実際の namespace/notebook に置き換え、作業を保存してください。Istio sidecar injection は、Notebook controller が直接実行するのではなく、設定された admission webhook によって実行されます。

## EKS における Notebook の GPU Scheduling

GPU request は、`resources.limits["nvidia.com/gpu"]` などの標準 extended resource を使用します。Device plugin、driver、node capacity、taint/toleration、および affinity は一致している必要があります。GPU resource を宣言するだけでは、適切な node が出現することは保証されません。

Karpenter は、EC2 capacity、quota、limit、networking、および bootstrap 成功を条件として、eligible Pending Pod と一致する NodePool に対して provision できます。Notebook の stop と EC2 scale-down は別個の operation です。配置と disruption の条件については、[Karpenter](../../autoscaling/02-karpenter.md)を参照してください。

## Custom Notebook Image

確認した spawner のデフォルトでは、`allowCustomImage` は `true` です。Notebook API を直接呼び出せる user に対しては、UI dropdown の制限だけで image selection を強制することはできません。必要な constraint は RBAC と admission を通じても適用してください。

image は server port、`/notebook/<namespace>/<name>/` prefix または rewrite configuration、UID/GID、writable home、probe、および runtime dependency を満たす必要があります。Jupyter Docker Stacks image が、すべての Kubeflow convention や SDK を自動的に含むわけではありません。pinned dependency を build し、ECR または別の registry の image digest を参照し、CPU architecture と GPU driver の互換性を検証してください。

同一の tag が同一の bytes を保証するわけではありません。同一の digest であっても、PVC の user package/setting、startup script、または runtime installation が異なる場合、environment が同一になるわけではありません。

## 検証とソース

26.03.1 の notebook-controller overlay は Kustomize を使用してローカルで render しました。v1.11.0 の CRD、stop handling、culling、および spawner configuration を確認しました。実際の notebook、GPU execution、PVC recovery、idle detection、および EKS provisioning は実行していません。

- [v1.11.0 Notebook controller](https://github.com/kubeflow/notebooks/blob/v1.11.0/components/notebook-controller/controllers/notebook_controller.go)
- [v1.11.0 culling implementation](https://github.com/kubeflow/notebooks/blob/v1.11.0/components/notebook-controller/controllers/culling_controller.go)
- [v1.11.0 spawner defaults](https://github.com/kubeflow/notebooks/blob/v1.11.0/components/crud-web-apps/jupyter/manifests/base/configs/spawner_ui_config.yaml)
- [26.03.1 Workspaces image tag](https://github.com/kubeflow/community-distribution/blob/26.03.1/applications/workspaces/upstream/controller/base/manager/kustomization.yaml)

## 次のステップ

[パート 4: Katib](04-katib.md)で experiment と hyperparameter tuning を続けます。

[メインページに戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../../quizzes/ai-ml/kubeflow/03-notebooks-quiz.md)に挑戦してください。
