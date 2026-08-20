# Kubeflow Notebooks クイズ

このクイズでは、Kubeflow Notebooks のアーキテクチャ、Profile ベースのマルチテナンシーモデル、ストレージとアイドル時の culling 動作、EKS 上の GPU スケジューリング、カスタム notebook image に関する理解を確認します。

## 選択式問題

1. Kubeflow Notebooks は、ユーザーが spawner で選択した項目（image、CPU/memory/GPU、storage）を実行中の notebook server に変換するために、どの Kubernetes ネイティブのメカニズムを使用しますか？
   - A) dashboard が `kubectl` に対して直接実行する shell script
   - B) controller が StatefulSet/pod に reconcile する `Notebook` custom resource
   - C) dashboard の database を毎分ポーリングする cron job
   - D) ユーザーが手動でインストールする Helm chart

<details>

<summary>回答を表示</summary>

**回答: B) controller が StatefulSet/pod に reconcile する `Notebook` custom resource**

**解説:**
Central Dashboard の spawner は、必要な環境を記述する `Notebook` custom resource を作成します。controller はその resource を監視し、dashboard が直接 pod を作成するのではなく、要求された image、resources、PVC を持つ通常の Kubernetes object（StatefulSet/pod）へと reconcile します。
</details>

2. Kubeflow Community Distribution 26.03 時点で、Kubeflow Notebooks v2 の正確な状況はどれですか？
   - A) すでに GA となっており、v1 を完全に置き換えている
   - B) alpha 版としてもまだ存在しない
   - C) リリースが近づいており、新しい `Workspace`/`WorkspaceKind` CRD を対象とした alpha manifest がテスト用に利用可能だが、まだ GA ではない
   - D) v1 を無期限に維持する方針となり、キャンセルされた

<details>

<summary>回答を表示</summary>

**回答: C) リリースが近づいており、新しい `Workspace`/`WorkspaceKind` CRD を対象とした alpha manifest がテスト用に利用可能だが、まだ GA ではない**

**解説:**
26.03 distribution の時点では、新しい `Workspace` および `WorkspaceKind` custom resource を基盤とする Notebooks v2 は、テスト用の alpha manifest が利用可能ですが、一般提供には至っていません。本番環境で使用されるアーキテクチャは引き続き v1 の `Notebook` CRD であり、v2 が GA 対応となった後は保守専用のステータスに移行する見込みです。
</details>

3. Kubeflow Notebooks のマルチテナンシーモデルにおいて、Profile とは何ですか？
   - A) ユーザーが保存した notebook の UI theme と keyboard shortcut
   - B) ユーザーごとの namespace を作成し、そのユーザーのアクセス範囲を定める RBAC binding と Istio authorization policy をプロビジョニングする仕組み
   - C) ユーザーが過去に spawn した image の記録
   - D) ユーザーの AWS IAM identity に関連付けられた billing account

<details>

<summary>回答を表示</summary>

**回答: B) ユーザーごとの namespace を作成し、そのユーザーのアクセス範囲を定める RBAC binding と Istio authorization policy をプロビジョニングする仕組み**

**解説:**
Profile は、ユーザー（または team）専用の namespace、その namespace に対する権限の範囲を定める RBAC binding、および内部の service に到達できる identity を制限する Istio `AuthorizationPolicy` をプロビジョニングします。Notebook は常に Profile namespace 内に作成され、これによりデフォルトであるユーザーの notebook を別のユーザーのものから分離します。
</details>

4. pod の再起動に対する notebook の耐障害性において、PersistentVolumeClaim が重要なのはなぜですか？
   - A) pod が再起動するたびに PVC が自動的に削除され、再作成されるため
   - B) 永続的な object は pod ではなく claim であり、そこから mount されたファイルとインストール済み package は pod の再起動、node の交換、stop/start cycle を経ても維持されるため
   - C) PVC が重要なのは RStudio image のみであり、JupyterLab では重要ではないため
   - D) PVC はユーザーファイルではなく log の保存にのみ使用されるため

<details>

<summary>回答を表示</summary>

**回答: B) 永続的な object は pod ではなく claim であり、そこから mount されたファイルとインストール済み package は pod の再起動、node の交換、stop/start cycle を経ても維持されるため**

**解説:**
spawner により、ユーザーは通常 notebook の home directory に mount される PVC をアタッチできます。PVC は pod の lifecycle とは独立して永続化されるため、ユーザーの作業は pod の再起動、node の交換、または意図的な stop/start cycle を経ても保持されます。また、notebook を削除せず停止する culling では、PVC はそのまま残ります。
</details>

5. とりわけ GPU 対応 notebook において、アイドル時の culling が重要なのはなぜですか？
   - A) GPU は notebook pod からまったく要求できないため、culling は無関係である
   - B) 実行中の notebook pod は、アクティブに使用されているかどうかにかかわらず存在する間 GPU allocation を保持するため、アイドル状態の GPU notebook は高価な capacity を数時間にわたり占有する可能性がある
   - C) culling が notebook の PVC を削除して GPU memory を解放するため
   - D) GPU node では capacity を回復するために cluster 全体の再起動が必要であり、culling がそれをトリガーするため

<details>

<summary>回答を表示</summary>

**回答: B) 実行中の notebook pod は、アクティブに使用されているかどうかにかかわらず存在する間 GPU allocation を保持するため、アイドル状態の GPU notebook は高価な capacity を数時間にわたり占有する可能性がある**

**解説:**
notebook pod は、誰かが実際に使用しているかどうかにかかわらず、実行中は要求した CPU、memory、GPU allocation を継続して保持します。culling は設定された期間の後にアイドル状態の notebook を停止します（削除はしません）。そのため、アイドル状態の GPU 対応 server が高価な accelerator capacity を無期限に占有することを防げる GPU notebook では、特に価値があります。
</details>

6. EKS 上の notebook pod はどのように GPU access を要求しますか？また、cluster autoscaling とはどのように連携しますか？
   - A) cluster の他の部分とは別の、Notebooks 専用 GPU scheduler を使用する
   - B) 他の pod と同様に `resources.limits."nvidia.com/gpu"` を設定し、training job や inference workload で使用される同じ GPU 対応 node pool（例: Karpenter 管理の NodePool）を競合して使用する
   - C) notebook の GPU access は、administrator が node に SSH して手動で割り当てる必要がある
   - D) notebook pod は GPU を要求できず、KServe endpoint のみが要求できる

<details>

<summary>回答を表示</summary>

**回答: B) 他の pod と同様に `resources.limits."nvidia.com/gpu"` を設定し、training job や inference workload で使用される同じ GPU 対応 node pool（例: Karpenter 管理の NodePool）を競合して使用する**

**解説:**
spawner での GPU 選択は、NVIDIA device plugin によって allocatable として公開される、pod spec 上の標準的な `nvidia.com/gpu` resource request に変換されます。これは独立した GPU subsystem ではありません。notebook pod は他の GPU workload と同じ GPU node pool を競合して使用し、EKS ではその capacity は一般に Karpenter によって動的にプロビジョニングされます。
</details>

7. team が stock spawner image をそのまま使用するのではなく、custom notebook image を構築する一般的な理由は何ですか？
   - A) Kubeflow では custom image が必須であり、stock image はまったく使用できないため
   - B) 実行中の container 内で package を手動でインストールする代わりに、team 固有の dependency をあらかじめインストールし、すべての data scientist に同一で再現可能な environment を提供するため
   - C) stock image が PVC mount をサポートしていないため
   - D) custom image により Profile namespace が不要になるため

<details>

<summary>回答を表示</summary>

**回答: B) 実行中の container 内で package を手動でインストールする代わりに、team 固有の dependency をあらかじめインストールし、すべての data scientist に同一で再現可能な environment を提供するため**

**解説:**
ほとんどの本番 team は、upstream の Kubeflow/Jupyter base image を基に custom image を構築し、固定した Python/R package、internal library、対応する GPU framework version を追加したうえで、image を registry（例: EKS 上の Amazon ECR）に push し、spawner から直接参照します。これにより、同じ image tag を使用する 2 人のユーザーには、手動 install による差異ではなく、同一の package set が提供されます。
</details>

## 短答式問題

8. notebook pod の GPU request が EKS 上で Karpenter とどのように連携するか、またこれが cost にとって重要である理由を、1 文または 2 文で説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
notebook Pod の spec が `nvidia.com/gpu` resource を要求し、既存の node に capacity がない場合、Karpenter は pending Pod を満たすために新しい GPU 対応 EC2 instance をプロビジョニングします。GPU instance は高価であるため、idle-culling と notebook の GPU request の right-sizing は、アクティブな session の合間に team が未使用の GPU capacity に支払う cost を直接左右します。
</details>

9. namespace ごとの Istio isolation は、通常の Kubernetes namespace RBAC 単独では提供できない、Kubeflow Profile にどのような利点をもたらしますか？

<details>

<summary>回答を表示</summary>

**回答:**
RBAC は、namespace 内の Kubernetes API object を誰が create/read/modify できるかを制御しますが、network traffic については制御しません。Istio の namespace ごとの `AuthorizationPolicy` は、どの service が network layer でユーザーの notebook Pod に実際に request を送信できるかをさらに制限し、RBAC 単独では cross-namespace の object access が一部許可される場合でも、ユーザーの notebook server 間の isolation を提供します。
</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/03-notebooks.md)
