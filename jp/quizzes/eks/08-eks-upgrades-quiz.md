# Amazon EKSアップグレードクイズ

> **最終更新**: 2026年9月12日

このクイズでは、Amazon EKSクラスターのアップグレード手順、ベストプラクティス、トラブルシューティング、および関連事項への理解を確認します。

## クイズの概要

- EKSクラスターのアップグレード計画
- コントロールプレーンのアップグレード
- ノードグループのアップグレード
- アドオンとコンポーネントのアップグレード
- アップグレードのテストと検証
- アップグレード時のトラブルシューティング

## 選択問題

### 1. Amazon EKSクラスターのアップグレードを計画する際、最初に行うべき最も重要な手順は何ですか？

- A. 直ちにコントロールプレーンをアップグレードする
- B. すべてのワークロードを一度にアップグレードする
- C. 互換性を確認し、テストと復旧の計画を立てる
- D. すべてのノードグループを同時にアップグレードする

<details>
<summary>回答を表示</summary>

**回答: C. 互換性を確認し、テストと復旧の計画を立てる**

変更の順序を決める前に、対象のEKSバージョン、APIの変更、ワークロードの依存関係を確認します。互換性の棚卸しは判断材料になりますが、利用可能性を保証するものではありません。

**互換性の確認**

- マニフェスト、Helmリリース、APIクライアント、CRD、変換／admission webhook、operatorを調べます。CNI／DNS、ロードバランサー、サービスメッシュ、ストレージ、監視、ログ、バックアップの各コンポーネントも含めます。
- サポート対象のクラスター版はEKSクラスターバージョンカタログで確認します。`describe-addon-versions`が示すのは、Kubernetesバージョンに対するアドオンの互換性です。
- 代表的な期間のEKS Upgrade Insightsと、利用できる監査ログ／メトリクスを確認します。公開されている場合、該当するAPIサーバーメトリクスは`apiserver_requested_deprecated_apis`です。系列がない、要求が拒否された、またはスキャン結果が空であることは、非推奨クライアントが存在しない証拠にはなりません。Insightsは観測期間内の過去の使用状況を保持する場合があります。
- オブジェクトの現在の`.apiVersion`は、返却された表現であり、クライアントが最初に要求したAPIバージョンとは限りません。デプロイ済み設定、ソース、実行時の呼び出し元を確認してください。

[ソースガイド](../../eks/08-eks-upgrades.md)から`eks-upgrade-preflight.py`を保存し、前提条件を確認したうえで、アカウント／コンテキスト／対象の読み取り専用棚卸しを実行します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"
export CLUSTER_NAME AWS_REGION EXPECTED_ACCOUNT_ID KUBE_CONTEXT TARGET_VERSION
umask 077
python3 eks-upgrade-preflight.py > preflight.json
# Review this evidence and the workload/backup/capacity plan before a separate change step.
```

このヘルパーはクエリに失敗すると停止します。`preflight.json`のすべての指摘を確認してください。このスクリプトはアップグレードを実行せず、互換性も証明しません。現在のAWSカタログを使い、現行版より1つ上のサポート対象マイナーバージョンを選びます。

レビュー済みのPlutoリリースを使い、レンダリング済みマニフェスト、Helmメタデータ、last-applied設定をスキャンします。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"; : "${MANIFEST_DIR:?}"
pluto detect-files --directory "$MANIFEST_DIR" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-helm --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-api-resources --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
```

先行処理がゼロ以外の終了コードになった場合、このシェルブロックは調査のために停止します。その結果に対処してから残りの確認を完了してください。APIリソースの検出は保存済みアノテーションに依存するため、実行時のすべての要求は確認できません。kube-no-troubleプロジェクトが提供するのは`kubent`バイナリであり、`kubectl-no-trouble`ではありません。

**過去のAPI削除例**（移行履歴であり、現在のEKSアップグレード対象を示すものではありません）:

| Kubernetesリリース | 提供が終了したAPI／移行先 |
| --- | --- |
| 1.22 | `networking.k8s.io/v1beta1` Ingressなど複数のbeta API。安定版APIとそのフィールドスキーマへ移行します。 |
| 1.25 | `policy/v1beta1` PodSecurityPolicy: ポリシー適用方式を移行します。`batch/v1beta1` CronJob → `batch/v1` |
| 1.26 | `autoscaling/v2beta2` HPA → `autoscaling/v2`。flow-controlの`v1beta1`も削除されました。 |
| 1.27 | `storage.k8s.io/v1beta1` CSIStorageCapacity → `storage.k8s.io/v1` |
| 1.29 / 1.32 | FlowSchema / PriorityLevelConfigurationの`v1beta2` / `v1beta3`がそれぞれ削除されました。フィールド／デフォルト値を移行し、`flowcontrol.apiserver.k8s.io/v1`を使います。 |

kubeletが1.25以降の場合、上流ポリシーではAPIサーバーより最大3マイナーバージョン古いkubeletが許可されますが、新しいkubeletは許可されません。それより古いkubeletでは2マイナーバージョン差までです。高可用性アップグレード中にAPIサーバーのバージョンが混在すると、この範囲は狭まります。これはサポート境界であり、すべてのアドオンやアプリケーションが動作する証明ではありません。EKSの保守的な準備では、次のコントロールプレーンアップグレード前にノードを**現在の**コントロールプレーン版へ合わせます。

**リハーサルと計画テンプレート**

レビュー済みのインフラ定義を使い、実環境に近いネットワーク、IAM、コンピューティングタイプ、データ、コントローラーを備えた別環境を用意します。本番との差異、費用、クリーンアップの所有者を記録します。開発／ステージングから開始し、業務機能、スケーリング、復旧、アラートを試します。本番環境で意図せず障害注入をしないでください。古い1.27→1.28の例は履歴上の例であり、現在のプロビジョニング推奨ではありません。

```markdown
# EKS upgrade plan: fill from evidence, not assumed results

- Account / Region / cluster ARN / kube context: TBD
- Current / target minor and EKS support status: TBD
- Node groups, Fargate, Auto Mode, hybrid nodes: inventory required
- Add-on / controller / CRD / webhook versions and owner: TBD
- Compatibility evidence, observation window and unresolved findings: TBD
- Backup coverage, application consistency, restore test and RPO/RTO: TBD
- Subnet IPs, EC2 quotas, placement, surge capacity and cost: TBD
- Rehearsal environment and differences from production: TBD

## Ordered change gates

- [ ] Align nodes to the current control-plane version; verify supported skew
- [ ] Complete API migrations and any required bridge add-on versions
- [ ] Complete a representative non-production rehearsal
- [ ] Upgrade the control plane by one minor; verify the exact update ID
- [ ] Upgrade nodes/add-ons in their reviewed dependency order
- [ ] Verify workloads and monitor agreed SLOs before retiring old capacity

## Test coverage and evidence

- [ ] Deployments: create, readiness, rollout and scaling
- [ ] StatefulSets / PVCs: write, reschedule, read and restore
- [ ] Services, DNS, Ingress / Gateway and external dependencies
- [ ] Jobs / CronJobs, operators, CRDs and admission webhooks
- [ ] API latency, Pod startup, network and resource baselines
- [ ] Controlled node/network/resource-pressure recovery in a test environment
- [ ] Alert delivery and incident ownership
- Result / timestamp / environment / evidence location: NOT RUN

## Recovery decision

- Stop criteria and incident owner: TBD
- Previous minor, upgrade completion time and 7-day rollback deadline: TBD
- Rollback eligibility, compute-type order and add-on compatibility: TBD
- Data restore or forward-fix procedure when version rollback is unsuitable: TBD
```

「すべて互換」「CRD変更なし」と先に記入せず、実際の観察結果を記録してください。バージョンのロールバックでアプリケーションデータは復元されません。ロールバックの対象条件とコンピューティングの順序は質問5で扱います。A、B、Dは根拠を省くか、変更範囲を広げすぎて、診断と復旧を難しくします。

参考資料: [API移行ガイド](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)、[バージョンスキューポリシー](https://kubernetes.io/releases/version-skew-policy/)、[EKSアップグレード](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)、[Pluto](https://pluto.docs.fairwinds.com/)、[kube-no-trouble](https://github.com/doitintl/kube-no-trouble)。

</details>

### 2. 事前準備としてノードを現在の版に合わせた後、次のマイナーバージョンへインプレースアップグレードする正しい順序は何ですか？

- A. APIサーバーが古い版のまま、kubeletを対象マイナーバージョンへ上げる
- B. コントロールプレーンを対象マイナーバージョンへ上げ、その後、対象版のノードグループをレビュー済みの段階に分けてアップグレードする
- C. コントロールプレーンと対象版ノードの変更をすべて同時に開始する
- D. マイナーバージョンを上げるたびに新しいクラスターが必須である

<details>
<summary>回答を表示</summary>

**回答: B. コントロールプレーンを対象マイナーバージョンへ上げ、その後、対象版のノードグループをレビュー済みの段階に分けてアップグレードする**

ノードを**現在の**コントロールプレーンのマイナーバージョンへ合わせるのは準備です。ノードを**対象**マイナーバージョンへ進めるのは、コントロールプレーンがその版をサポートした後です。EKSは一度に1つのマイナーバージョンずつアップグレードします。サポートされるバージョンスキューは、アプリケーション互換性を保証しません。コントロールプレーン変更前に必要となる中継アドオン版を含め、各コンポーネントの依存関係に従ってください。

**準備と実行**

1. アカウント、コンテキスト、現在版／対象版のサポート状況、クラスター／ノードの健全性、Insights、サブネットのIP容量、アクセスを確認します。置換用の容量とワークロードの中断制御も計画します。
2. バックアップと復元を検証します。EKS利用者はマネージドコントロールプレーンに対して`etcdctl`を実行できません。`kubectl get all`では多くのリソースや永続データが表示されません。適切に構成したAWS Backup for EKS、またはVelero／アプリケーションのバックアップを使い、対象範囲と復元をテストしてください。
3. 質問1のpreflightを確認します。この別個の変更手順に先立ち、競合する更新がないことを確認したレビュー済み対象版について、[ソースガイド](../../eks/08-eks-upgrades.md)から`eks-wait-update.py`を保存します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster}"
: "${AWS_REGION:?Set the reviewed Region}"
: "${TARGET_VERSION:?Set the next supported EKS minor version}"
umask 077
aws eks update-cluster-version \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --output json --no-cli-pager \
  > control-plane-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' control-plane-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

ポーラーはこの正確な要求を監視します。成功となるのは`Successful`だけです。失敗、キャンセル、不明な状態、APIエラーでは手順を停止します。クライアント側のタイムアウトはAWSの処理をキャンセルしません。`ACTIVE`だけではこの更新の成功を証明できません。また、`aws eks wait update-successful`はEKS CLIのwaiterではありません。

別の方法として、`eksctl upgrade cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --version "$TARGET_VERSION"`は変更をプレビューし、`--approve`で開始します。CLI変更とTerraform変更を両方送信せず、所有者と実行経路を1つ選びます。

**要求の成功後**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,platformVersion:platformVersion}'
aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
kubectl --context "$KUBE_CONTEXT" get --raw='/readyz'
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" get pods -n kube-system
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp'
```

API readiness endpointの確認には権限が必要で、健全性を示す指標の1つにすぎません。古い`ComponentStatus`オブジェクトや、マネージドetcd Podがあるという前提ではなく、実際のワークロード、DNS、コントローラーを調べてください。Auto ModeのみのクラスターではノードレベルのCoreDNSを使います。混在クラスターではAuto Mode以外のノード用にDNSが残ります。標準の`aws-node`、kube-proxy、CoreDNS Deploymentが見当たらないことだけで、Auto Modeの障害とは言えません。`kubectl top`にはMetrics Serverが必要です。メトリクスが取得できることは要求の成功とは別です。

レビュー済みのノードグループ／canaryから進め、必要なアドオン順序に従って各段階を検証します。Auto Modeはコントロールプレーンアップグレード後にノードを管理します。既存のFargate Podはkubeletバージョンを維持するため、所有者が制御する置換と可用性を調整してください。

**可用性と所要時間**

古い「20～30分」という見積もりは、根拠となる計測が提供されていません。所要時間の保証ではなく、過去の計画例としてのみ残します。リハーサルに基づく作業枠を確保してください。APIサーバーが置き換わる間、APIクライアントは再接続する必要があります。既存コンテナは動作し続ける場合がありますが、APIに依存するコントローラーやアプリケーションには影響し得ます。通常のコントロールプレーンアップグレードは開始後に一時停止／キャンセルできません。更新IDとエラーを保存し、必要に応じてAWS Supportへ相談します。後のバージョンロールバックには別の適格条件があります。

**Terraform所有の例**

既存リソース／モジュールを変更し、その他の設定と依存関係を維持してください。この抜粋は完全な定義ではなく、既存クラスター用に2つ目のリソースを作るものでもありません。

```hcl
# Fragment of the existing, state-managed cluster resource.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.target_version

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.cluster_security_group_id]
  }

  lifecycle {
    prevent_destroy = true
  }
}
```

既存のIAM、サブネット、セキュリティグループの値とレビュー済み対象版を指定してください。意図しない置換や無関係な変更がないか、provider planを確認します。`prevent_destroy`はTerraformによる破棄を防ぐもので、サービス中断は防ぎません。空の`ignore_changes = []`は待機もアップグレード検証もしません。providerには独自のwaiter／timeoutがあります。IaCのタイムアウトはサービス処理のキャンセルではなく、Git revertもEKSバージョンのロールバックではありません。変更後は質問6の範囲を限定した検証を行います。このレビューでは実クラスターに対する実行はしていません。

AはkubeletをAPIサーバーより新しくしてしまいます。Cは検証段階をなくします。Dは誤りです。新クラスターへの移行は任意であり、トラフィック／データ移行に別のコストがかかります。

参考資料: [EKS更新手順](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)、[EKSバックアップ](https://docs.aws.amazon.com/eks/latest/userguide/integration-backup.html)、[Terraform EKSリソース](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster)。

</details>

### 3. EKSノードグループを制御しながらアップグレードするには、どの方法が適切ですか？

- A. すべてのノードを同時に終了する
- B. 段階的なマネージドノードグループ更新、または検証済みのblue/green移行を使う
- C. ノードのバージョンを無期限に変更しない
- D. マネージドノード上のkubeletバイナリを個別に置き換える

<details>
<summary>回答を表示</summary>

**回答: B. 段階的なマネージドノードグループ更新、または検証済みのblue/green移行を使う**

戦略は、ワークロードが許容できる中断、容量、ステートフルストレージ、コンピューティングの所有者に基づいて選びます。マネージド更新もblue/green移行も、サービス無停止を保証するものではありません。

**マネージドノードグループ**

`DEFAULT`更新戦略は古いノードを退役させる前に置換容量を作成します。`MINIMAL`は先に古い容量を削減します。`maxUnavailable`は同時に利用できなくなる数を制限します。通常のローリングevictionはPDBに従いますが、force updateはそれを迂回できます。これらの戦略は、コンソールのrolling／force選択肢とは異なります。更新失敗が自動的なフリートロールバックを意味するわけではありません。

ソースガイドの`eks-wait-update.py`を保存し、質問1のアカウント／コンテキスト／容量確認を完了してください。EKS最適化AMIを使う既存グループでは、Kubernetesバージョンと互換性のあるAMIリリースの両方を明示します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${TARGET_VERSION:?Set the reviewed target, no newer than the control plane}"
: "${TARGET_AMI_RELEASE:?Set the reviewed EKS-optimized AMI release}"
umask 077
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" --output json > nodegroup-before.json
if jq -e '.nodegroup.amiType == "CUSTOM"' nodegroup-before.json >/dev/null; then
  echo "Use the custom launch-template path for this node group" >&2
  exit 1
fi
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --release-version "$TARGET_AMI_RELEASE" \
  --output json > nodegroup-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' nodegroup-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

要求やポーリングが失敗すると、この処理は停止します。次のグループへ進む前に、実際のノードバージョン／Ready状態、Pod配置、イベント、アプリケーションSLOを確認します。カスタムAMIの場合は、レビュー済みの**同じ既存launch template**の新しいバージョンを使い、`--kubernetes-version`と`--release-version`を省略します。ソースガイドのカスタムAMI用の別手順に従ってください。kubeletパッケージだけをインプレース編集して、AMI／runtime／bootstrapもアップグレードされたと想定しないでください。

`eksctl upgrade nodegroup`では`--kubernetes-version`を使い、`eksctl create nodegroup`では`--version`を使います。作成時は未サポートの`--taints`フラグや不完全な一行手順を使わず、レビュー済みサブネット、IAM、AMI、ラベル、taintを既存クラスター設定に保ちます。

**Blue/greenの手順**

1. blueの容量を維持します。インフラ所有者とgreenを作成し、コントロールプレーンより新しくないバージョン、互換性のあるAMI／アーキテクチャ、プライベートネットワーク、十分なクォータ／IP／AZ容量を確保します。
2. greenノードがReadyであることを確認し、DNS、ネットワーク、ストレージ、ワークロード依存関係をテストします。適切なワークロードがtolerateするまでは、canary向けにgreenへtaintを付けます。
3. ワークロードPod templateを段階的に移行します。preferred affinityはあくまで希望であり、既存Podを移動しません。配置が必須なら明示的な選択を使い、ワークロード所有者を通じて制御したrolloutを開始します。
4. 古い各ノードのワークロードを調べ、一度に1台ずつdrainします。evictionに失敗したら停止してください。drain失敗後も終了処理を続けてはいけません。
5. ワークロード／データ／トラフィックの根拠と復旧期間を確認した後に限り、blueを退役させます。「yes」という入力やReadyノードの一覧だけでは、移行完了の証拠になりません。

以下は完全な**独立canary fixture**であり、既存アプリケーションの置き換えマニフェストではありません。Namespaceを慎重に準備してください。hostnameのrequired anti-affinityにより、条件を満たすLinux greenノードが少なくとも3台必要です。tolerationはtaintを許可し、node selectorはgreenを選びます。アプリケーションイメージ／設定、disruption policy、rolloutパラメータは別途調整してください。

```yaml
# Independent fixture in an explicitly prepared test namespace.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  replicas: 3
  selector:
    matchLabels:
      app: upgrade-canary
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 0
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
        example.com/upgrade: green
      tolerations:
        - key: example.com/upgrade
          operator: Equal
          value: green
          effect: NoSchedule
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: upgrade-canary
              topologyKey: kubernetes.io/hostname
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: http
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - mkdir -p /tmp/www; printf 'ok\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 5
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: upgrade-canary
```

Deployment自身のrolling updateは、そのstrategyで制御され、PDBによるものではありません。PDBが制御するのは任意のevictionであり、通常のDeployment／ReplicaSetによるスケールダウンやすべてのインフラ終了処理ではありません。適切な容量がなくなるとrequired anti-affinityでスケジュールできない場合があります。このfixtureのイメージ実行やクラスター実行はしていません。

対象ノードを1台ずつ処理する場合は、ソースガイドの範囲を限定したdrainを使い、管理外Podと`emptyDir`データの保護を維持します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
: "${NODE_NAME:?Set one reviewed old node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
# Stop on failure. Do not terminate the instance or delete the node group here.
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
```

drainに失敗すると、ノードがcordonされたまま、または一部だけdrainされた状態になる可能性があります。調査と復旧を慎重に行ってください。移行を完了させる目的だけで`--force`、`--delete-emptydir-data`、`--disable-eviction`を追加しないでください。

**Terraform blue/greenの例**

既存のリソースアドレス／設定を維持します。これらのEKS最適化AMI用抜粋では、blueとgreenの両グループに正の容量を保ちます。greenのtaintは上記canaryで意図的に一致させています。

```hcl
# Existing blue resource address is retained; green is separate capacity.
# Inputs describe reviewed EKS-optimized AMIs, not a custom launch template.
variable "capacity" {
  type    = object({ desired = number, min = number, max = number })
  default = { desired = 3, min = 3, max = 6 }
  validation {
    condition = (
      var.capacity.min >= 1 &&
      var.capacity.desired >= var.capacity.min &&
      var.capacity.max >= var.capacity.desired &&
      alltrue([for n in values(var.capacity) : floor(n) == n])
    )
    error_message = "Retain positive integer capacity: 1 <= min <= desired <= max."
  }
}

resource "aws_eks_node_group" "blue" {
  cluster_name    = var.cluster_name
  node_group_name = "blue-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.blue_version
  release_version = var.blue_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "blue" }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_node_group" "green" {
  cluster_name    = var.cluster_name
  node_group_name = "green-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.green_version
  release_version = var.green_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "green" }
  taint {
    key    = "example.com/upgrade"
    value  = "green"
    effect = "NO_SCHEDULE"
  }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}
```

既存のクラスター／ロール／サブネット、互換性のあるインスタンスタイプ／AMIファミリー、別途レビュー済みのblue／greenバージョンとリリースを指定します。greenのバージョンは、コントロールプレーンですでにサポートされている必要があります。`desired_size`をignoreする規則は、autoscalerがそのフィールドを所有する前提です。Terraformが所有者である場合は削除してください。minimum／maximumの変更は引き続き適用され、マネージドノードグループのスケーリング設定変更はPDBに従いません。green作成中にblueをゼロへ下げるBoolean切替や、無効な`max_size = 0`を使わないでください。ノード作成、ワークロード移行、退役は別々の変更です。Terraform dependencyだけではワークロードのReadyを証明できません。

事前に復旧条件を定めてください。blueを保持している間は、API／データ互換性の範囲内でワークロード配置を戻せる場合があります。コントロールプレーンとMNGバージョンを戻すには、質問5にある追加条件があります。A、C、Dは中断を広げるか、サポート外のskewを蓄積するか、マネージドな置換ライフサイクルを迂回します。

参考資料: [マネージドノード更新](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)、[更新の動作](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)、[PDB](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)、[Terraformノードグループ](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group)。

</details>

### 4. EKSアップグレード中のアドオン管理では、どの方法が正しいですか？

- A. アドオンのアップグレードを無視する
- B. 互換性にかかわらず、すべてのアドオンをコントロールプレーンより前にアップグレードする
- C. 互換性のあるバージョンを選び、各コンポーネントの依存関係と中継バージョンの順序に従う
- D. すべてのアドオンを削除して再インストールする

<details>
<summary>回答を表示</summary>

**回答: C. 互換性のあるバージョンを選び、各コンポーネントの依存関係と中継バージョンの順序に従う**

「すべてのアドオンをコントロールプレーンの後に更新する」という共通ルールはありません。コンポーネントによっては、コントロールプレーンの両バージョンと互換性のある中間バージョンが先に必要です。別のコンポーネントはコントロールプレーン変更後に更新します。各リリースでサポートされるKubernetes版、アーキテクチャ、コンピューティングタイプ、API、アップグレード経路を確認してください。EKSマネージドアドオンはコントロールプレーンと同時に自動アップグレードされず、「managed」であることはすべてのセキュリティリリースが自動的にインストールされる保証でもありません。

**調査、選定、設定の維持**

インストール済みで所有者が明確なマネージドアドオン1つについて、現状、互換候補、レビュー対象版のschemaを調べます。配列の先頭要素は「互換性のある最新バージョン」を保証しません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"
: "${TARGET_VERSION:?Set the Kubernetes version for this stage}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json > addon-before.json
aws eks describe-addon-versions --addon-name "$ADDON_NAME" \
  --kubernetes-version "$TARGET_VERSION" --region "$AWS_REGION" \
  --output json > addon-candidates.json
# Select ADDON_VERSION after reviewing compatibility, architecture, compute type, and upgrade path.
: "${ADDON_VERSION:?Set the reviewed add-on version}"
aws eks describe-addon-configuration --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --output json > addon-schema.json
jq -r '.addon.configurationValues // "{}"' addon-before.json > addon-config-candidate.json
```

`addon-before.json`にはバージョン／設定／ID情報が含まれます。単一の`aws-node` ConfigMapはCNIの完全なバックアップではありません。DaemonSet設定、カスタムリソース、IAM／Pod Identityも対象になる場合があります。証拠ファイルを保護してください。`addon-config-candidate.json`はレビュー用の入力であり、自動的に有効な対象設定になるわけではありません。新しいschemaに対して必要な設定をマージし、削除／デフォルト化されるフィールドとリリースノートを確認します。

このレビューを完了した後、ソースガイドの正確な要求用ポーラーと完全な対象設定ファイルを使います。

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"; : "${ADDON_VERSION:?}"
: "${REVIEWED_ADDON_CONFIG_FILE:?Provide the complete reviewed target configuration JSON}"
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG_FILE" \
  --resolve-conflicts PRESERVE --output json > addon-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' addon-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID ADDON_NAME
unset NODEGROUP_NAME
python3 eks-wait-update.py
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json
```

`PRESERVE`は既存フィールドとの競合に対応するもので、明示的な設定payloadが完全にマージされ、受理され、機能する保証ではありません。`NONE`は競合時に失敗します。`OVERWRITE`はカスタマイズをEKSデフォルトで置き換える可能性があります。自動復旧手段としてoverwriteを使わないでください。次の依存コンポーネントへ進む前に、更新の成功**と**アドオンの健全性／ワークロード動作を確認します。30秒sleepは完了確認ではありません。

**コンポーネントごとの確認事項**

| コンポーネント | 次へ進む前に確認すること |
| --- | --- |
| VPC CNI | サポート対象の更新経路、IP割当、ノード／Podネットワーク、カスタムネットワーク、IAM |
| CoreDNS | DNS解決、Corefile／schema変更、スケジューリング／readiness、PDB設定 |
| kube-proxy | Kubernetesスキュー、Service到達性、実際のデータプレーン |
| Cluster Autoscaler | サポート対象Kubernetesマイナー、discovery／IAM、スケーリングの所有者 |
| Metrics Server | サポート対象版、APIServiceの利用可否、kubelet TLS／アクセス |
| Load Balancer Controller / ExternalDNS / mesh | Controller／chart／CRD／API互換性、IAM、webhook、トラフィック動作 |

Auto ModeのみのクラスターはノードレベルのDNS／ネットワーク機能を提供し、これらの標準ノードアドオンを同じ形では必要としません。混在クラスターではCoreDNS Deploymentの対象範囲など、Auto Mode以外のノードに必要なコンポーネントを維持してください。更新／削除の前に所有者を特定します。

**Terraform管理のアドオン**

既存のstate所有リソースでレビュー済みのバージョン／設定mapを使い、IAM／Pod Identity設定を維持します。これらの抜粋は標準ノードのアドオン用であり、Auto Modeの一律な導入方法ではありません。

```hcl
# Fragments of existing, imported/state-managed standard-node add-ons.
# Preserve each resource's existing IAM/Pod Identity settings as applicable.
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = var.cluster_name
  addon_name                  = "vpc-cni"
  addon_version               = var.addon_versions["vpc-cni"]
  configuration_values        = file(var.addon_config_files["vpc-cni"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.addon_versions["coredns"]
  configuration_values        = file(var.addon_config_files["coredns"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = var.cluster_name
  addon_name                  = "kube-proxy"
  addon_version               = var.addon_versions["kube-proxy"]
  configuration_values        = file(var.addon_config_files["kube-proxy"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

現行providerでは`resolve_conflicts_on_create`と`resolve_conflicts_on_update`が分かれています。作成時は`PRESERVE`を受け付けず、`NONE`は移行時の競合を意図的に明らかにします。アドオン更新のために重複クラスターリソースを追加しないでください。現在の段階で更新するコンポーネントだけを変更します。独立した3リソースを並べても安全な更新順序が定まるわけではありません。リソース破棄や設定変更には個別のレビューが必要です。

**自己管理Helmリリース**

既存リリースの所有者を通じ、レビュー済みのchart参照／バージョンと移行済みvaluesを使います。インストール、所有権移行、アップグレードは別の操作です。CRD、ID、ServiceAccount、リソース／スケジューリング設定、現行動作を維持してください。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${RELEASE:?}"; : "${ADDON_NAMESPACE:?}"
: "${CHART_REF:?Set the verified repository/chart or OCI reference}"
: "${CHART_VERSION:?Set a reviewed compatible chart version}"
: "${REVIEWED_VALUES_FILE:?Set the complete reviewed target values file}"
umask 077
helm get values "$RELEASE" --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > addon-values-before.yaml
helm show values "$CHART_REF" --version "$CHART_VERSION" > addon-values-defaults.yaml
# Merge/migrate values and handle CRDs/IAM through the owner before this step.
helm upgrade "$RELEASE" "$CHART_REF" --version "$CHART_VERSION" \
  --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  -f "$REVIEWED_VALUES_FILE" --wait --timeout 15m
```

最終コマンドの前にレビュー済みvaluesを準備してください。`--wait`はアプリケーションSLOを証明せず、すべてのCRD移行も処理しません。アップグレード中に2つ目のcontrollerを一括インストールしたり、無関係なautoscalerフラグを変更したりしないでください。各リリースのPod、イベント、代表的な機能を確認し、常に「完了」と出力するのではなく失敗を記録します。

Aはセキュリティと互換性の維持を無視します。Bは古いコントロールプレーンと互換性のない版を導入する可能性があります。Dは所有権／設定を不必要に捨て、ネットワークやDNSを中断させる可能性があります。

参考資料: [EKSアドオンの更新](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html)、[Auto Modeのネットワーキング](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)、[Terraformアドオン](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon)、[Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/)。

</details>

### 5. EKSアップグレード中に問題が発生した場合、最も効果的な対応は何ですか？

- A. 直ちに新しいクラスターを作る
- B. 証拠を集めず、AWS Supportだけに頼る
- C. ログと仮説検証を用いて体系的にトラブルシューティングする
- D. アップグレードの問題を無視する

<details>
<summary>回答を表示</summary>

**回答: C. ログと仮説検証を用いて体系的にトラブルシューティングする**

症状、発生時刻、影響を受けるワークロード、業務影響を定義し、特定の変更と関連付けます。仮説を試す前に証拠を集めます。期待される影響をレビューしてから限定的な修正を行い、復旧を確認して再発防止策を記録します。考えられる原因は確定した根本原因ではありません。

**読み取り専用の診断**

アカウント／コンテキストと正確な操作IDを確認します。次のcollectorは問い合わせ前に操作タイプを検証し、新しい非公開の証拠ディレクトリを使います。問い合わせが失敗した場合は停止します。すでに書き出されたファイルは部分的な証拠であり、診断成功を意味しません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${UPDATE_ID:?Set the exact affected update ID}"
: "${ISSUE_KIND:?Set control-plane, nodegroup, or addon}"
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
args=(--name "$CLUSTER_NAME" --region "$AWS_REGION" --update-id "$UPDATE_ID")
case "$ISSUE_KIND" in
  control-plane) ;;
  nodegroup) : "${NODEGROUP_NAME:?}"; args+=(--nodegroup-name "$NODEGROUP_NAME") ;;
  addon) : "${ADDON_NAME:?}"; args+=(--addon-name "$ADDON_NAME") ;;
  *) echo "Unknown ISSUE_KIND" >&2; exit 2 ;;
esac
umask 077
EVIDENCE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-upgrade-diagnosis.XXXXXXXX")
printf 'Evidence directory: %s\n' "$EVIDENCE_DIR"
aws eks describe-update "${args[@]}" --output json --no-cli-pager \
  > "$EVIDENCE_DIR/update.json" 2> "$EVIDENCE_DIR/update.stderr"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,health:health,logging:logging}' \
  --output json --no-cli-pager > "$EVIDENCE_DIR/cluster.json"
kubectl --context "$KUBE_CONTEXT" get nodes -o wide > "$EVIDENCE_DIR/nodes.txt"
kubectl --context "$KUBE_CONTEXT" get pods -A -o wide > "$EVIDENCE_DIR/pods.txt"
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp' \
  > "$EVIDENCE_DIR/events.txt"
printf 'Snapshots collected; review errors and workload evidence before changing anything.\n'
```

ノードグループまたはアドオンの操作では、`describe-nodegroup`または`describe-addon`で対象リソースの`health.issues`とバージョン／設定も調べます。状況に応じて、ノードのProviderID、EC2状態、IAM／bootstrap／AMI／ネットワーク、スケジューリング制約を確認します。更新の`Failed`状態だけから原因を断定しないでください。

期間を限定して既存のコントロールプレーンログを読み取ります。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${START_TIME_MS:?Set the reviewed start timestamp in epoch milliseconds}"
: "${END_TIME_MS:?Set the reviewed analysis-window end timestamp}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.logging' --output json --no-cli-pager
# Read existing logs; enabling logging is a separate change and does not backfill history.
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$START_TIME_MS" --end-time "$END_TIME_MS" \
  --max-items 200 --output json --no-cli-pager
```

ログ記録の有効化は別のクラスター変更であり、過去のイベントを補完しません。ロググループがない、権限エラー、検索結果が空である場合は可視性に制約があります。該当Podが存在する場合は、明示的に調べます。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${AFFECTED_NAMESPACE:?}"; : "${AFFECTED_POD:?}"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" describe pod "$AFFECTED_POD"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" logs "$AFFECTED_POD" \
  --all-containers=true --prefix=true --since=15m --tail=100
```

Pod agentのログは、ホストのkubelet／runtime journalをすべて含むわけではありません。Auto Mode、Fargate、標準EC2では診断アクセスが異なります。snapshotを保護し、AWS Supportへ共有する前に機密設定をマスキングしてください。クラスター全体のdumpを無差別に取らないでください。

| 症状 | 証拠を用いて検証する仮説 |
| --- | --- |
| コントロールプレーン要求が失敗 | 正確な更新エラー、前提条件、サブネットIP／セキュリティグループ、AWSサービス側の障害 |
| NodeがNot Ready／PodがPending | AMI／bootstrap、EC2容量、IAM／ネットワーク／CNI、taint、affinity、PVCトポロジー、リソース |
| アドオンがCrashLoopBackOff | 設定／schema、ID、image／起動、リソース、バージョン互換性 |
| アプリケーションAPIエラー | 削除済みAPIの呼び出し元、admission／変換webhook、権限、アプリケーションの回帰 |

リトライ、ノードグループ削除、アドオン設定のoverwriteは診断ではありません。アドオンを復旧するには互換性のあるバージョン**と**レビュー済み設定／IDが必要です。質問4の正確な更新監視にも従ってください。

**現行EKSのロールバック条件**

現行のEKSガイドでは、インプレースのコントロールプレーンロールバックがサポートされています。これはアプリケーションデータの復元や、故障ノードの置換とは異なります。

- インプレースアップグレード完了から7日以内に、直前のマイナーバージョンへ戻します。現在版で作成したクラスターは対象外です。さらに古い版へ順次戻すこともサポートされません。
- 対象版は引き続きサポートされている必要があります。延長サポート中の対象には`EXTENDED`ポリシーが必要で、その料金がかかります。延長サポート終了時の自動アップグレードはロールバックできません。標準サポート終了時のケースには、文書化されたポリシー条件があります。
- `ACTIVE`状態、競合する更新、後方互換性のない機能、その他の前提条件を確認します。`ROLLBACK_READINESS`の`ERROR`／`UNKNOWN` Insightsは阻止要因であり、`WARNING`は助言です。`--force`はInsights確認を迂回しますが、対象資格／前提条件やAuto Modeのdisruption制御は迂回しません。通常アップグレード時のInsightsに対する一時的な`--force`適用とは別です。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}' --output json --no-cli-pager
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
```

各指摘は`describe-insight --id "$INSIGHT_ID"`で調べます。Insights一覧が空であることを、すべての前提条件が満たされた証拠とみなさないでください。

| コンピューティングタイプ | 順序と制限 |
| --- | --- |
| マネージドノードグループ | ソースガイドとカスタムAMI要件に従い、適用対象グループの`UpdateNodegroupVersion`をコントロールプレーンより先に実行し、実際のノードを確認します。 |
| 自己管理／ハイブリッド | 所有者が互換性のあるノードとワークロード移行をコントロールプレーンより前に調整します。 |
| Auto Mode | サービスが先にノードを戻し、その後コントロールプレーンを戻します。ノード段階でクラスター状態が`ACTIVE`でも更新IDを追跡してください。 |
| Fargate | kubeletのインプレースロールバックはありません。Pod／controller／HPA／GitOps／Jobの動作と可用性を調整し、新しいkubeletの置換Podがコントロールプレーンのロールバック前に再作成されないようにします。 |

該当するノード順序とすべての前提条件を検証した後、コントロールプレーンの要求には`rollback-cluster`コマンドではなく`update-cluster-version`を使います。先にソースガイドのポーラーを保存してください。

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ROLLBACK_VERSION:?}"
: "${WAIT_TIMEOUT_SECONDS:?Set an explicit client wait for the approved rollback}"
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --output json --no-cli-pager > rollback-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' rollback-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID WAIT_TIMEOUT_SECONDS
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

Auto Modeでは、別の同時要求を送らず、ソースガイドにある`--rollback-config timeoutMinutes=...`の代替要求を使います。デフォルトは720分で、サポート範囲は120～10080分です。正確な完了期限ではありません。drift budgetがゼロ、またはノードdisruption除外があると処理が止まる場合があります。PDB／Pod disruption除外はtermination grace periodと相互作用し、無期限の保護を意味しません。`--force`もこれらの制御を迂回しません。

Auto Modeでは、コントロールプレーンを戻す前のノード段階に限ってbest-effortの`CancelUpdate`がサポートされます。進行中のdisruptionは完了する場合があります。timeout／キャンセル後もコントロールプレーンは変更されず、ノードはそのバージョンへ再調整されます。クライアントのtimeoutだけでは操作をキャンセルしません。再試行にも当初の適格期間が適用されます。

ロールバックではetcd／ワークロード／PVデータが保持され、バックアップが復元されるわけではありません。アドオンは自動で元に戻りません。前のマイナーバージョンには、必ずしも以前と同じplatform版ではなく、その時点の最新platform版が適用されます。CloudFormationのロールバックやGit revertは、このサービス操作ではありません。ソースガイドの全判断手順を使ってください。このレビューではAWSに対してコマンドを実行していません。

**インシデント記録**

以下の元のタイムスタンプは維持しています。シナリオと主張されている原因を裏付けるインシデント証拠は提示されていないため、仮説を含む例として扱います。

```markdown
# Upgrade troubleshooting report (illustrative, not a verified incident)

## Problem description

- Example symptom: CoreDNS Pods in CrashLoopBackOff after a node-group update
- Example impact: service discovery and application connections affected
- Original illustrative timestamp: 2023-07-15 14:30 UTC
- Provenance: no incident logs or measurement evidence supplied

## Investigation

1. Record the exact update ID, versions, changes and affected workloads.
2. Inspect CoreDNS logs/events, node conditions and resource availability.
3. Compare the owned Corefile/configuration with the reviewed baseline.
4. Check connectivity, network policies, scheduling and dependency changes.

## Hypotheses, not established findings

- A configuration parsing error is one possible explanation.
- A ConfigMap modification requires a diff/audit record and relevant log evidence.
- Record evidence that supports or rejects each hypothesis.

## Conditional remediation

1. If a configuration regression is demonstrated, restore compatible reviewed settings.
2. Coordinate any restart with replicas, readiness, PDB and DNS availability.
3. Verify service discovery and application SLOs, not just Pod phase.

## Prevention and record

- Version and back up owned configuration; rehearse restoration.
- Add regression checks and staged rollout gates.
- Actual actions, results and evidence: NOT RUN / TO BE RECORDED.
```

AWS Supportには、正確な更新ID、期間を限定したログ／エラー、影響、実施した対応を共有してください。Aは原因を解消せずに未計画の移行を追加する可能性があります。Bは有用な証拠を省き、Dは信頼性／セキュリティの問題を放置します。

参考資料: [EKSロールバック](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)、[Auto Modeのロールバック](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)、[EKSトラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)。

</details>

### 6. アップグレード後の最も包括的な検証方法は何ですか？

- A. ノード数だけを数える
- B. クラスターのバージョンだけを確認する
- C. 段階的に、要求状態、コンポーネント、ワークロード機能、代表的な性能を検証する
- D. 検証せずに本番トラフィックをすべて流す

<details>
<summary>回答を表示</summary>

**回答: C. 段階的に、要求状態、コンポーネント、ワークロード機能、代表的な性能を検証する**

最初に正確な更新要求、バージョン、ノード／アドオンの状態を確認します。次に機能を試し、アプリケーションメトリクスを記録済みbaselineと比較します。smoke testの成功は、本番準備完了やSLO達成の証明より限定的です。

| 領域 | 根拠 |
| --- | --- |
| コントロールプレーン | 更新結果、APIのreadiness／応答性、サポート対象のメトリクス／ログ。マネージドetcdには直接アクセスできません。 |
| ノード | Ready条件、想定したkubelet／AMI／runtime、スケジューリング、コンピューティングタイプ固有の健全性 |
| ネットワーク | Pod／Service／DNS、Ingress／Gateway、egress、依存先への接続 |
| ストレージ | プロビジョニング、利用者間の書き込み／読み取り、トポロジー、再スケジュール、アプリケーション整合性のある復元 |
| セキュリティ | 想定した認証／認可、Pod security、NetworkPolicy、暗号化動作 |
| ワークロード | Deployment rollout／スケーリング、StatefulSet、Job／CronJob、CRD／operator、webhook |
| 性能 | 代表的な期間における比較可能な要求レート、レイテンシ／エラー分布、起動時間、リソース使用量 |

ソースガイドの`eks-upgrade-smoke.py`を使い、レビュー済みのコンテキスト、互換性のあるStorageClass、CSI driver／IAM、スケジューリング、admission／ネットワークポリシー、費用を確認したうえで、範囲を限定したLinux EC2テストを行います。提示された実装をローカルに保存してください。定義されていない検証用イメージやスクリプトを参照するものではありません。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test cluster context}"
: "${TEST_STORAGE_CLASS:?Set an existing compatible test StorageClass}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
python3 eks-upgrade-smoke.py
```

このヘルパーは一意のNamespaceを作り、そのUIDを記録します。Deploymentのrollout／スケーリングと20回のHTTP要求を試し、別々のJobでPVC markerを書き込んで読み取ります。`WaitForFirstConsumer`がconsumerをスケジュールできるよう、バインドを待つ前にwriterを作り、readerの前にwriterを削除します。失敗時は証拠／リソースを残します。成功後の任意cleanupには同じNamespace UIDが必要です。`Retain` PVは残り、料金が発生する場合があります。すべてのワークロード、復元手順、Fargate／Auto設定、性能上限、セキュリティ制御をテストするものではありません。

表にある追加の機能／負荷テストは、所有者がレビューして選びます。`kubectl top`にはMetrics Serverが必要で、現在の使用状況を示すだけで、throughputやレイテンシーの根拠にはなりません。本番環境に対して無制限のwget loopを実行しないでください。対象トラフィック、期間、成功／エラー基準、baseline、環境差、実結果を記録します。synthetic fixtureからベンチマークを推測しないでください。

**任意のTerraform fixture**

この別管理fixtureはNamespace／Deployment／Service／PVCの学習例を維持します。providerをレビュー済みコンテキストに設定し、新しいNamespaceと互換性のあるStorageClassを指定してplanを確認します。既存Namespaceを取り込んだり破棄したりしないでください。これはfixtureであり、自動検証の判定ではありません。

```hcl
# Separate disposable fixture; configure the Kubernetes provider/context externally.
variable "validation_namespace" {
  type = string
  validation {
    condition     = can(regex("^eks-upgrade-validation-[a-z0-9]{8,16}$", var.validation_namespace))
    error_message = "Supply a new, unique namespace with the required validation prefix."
  }
}
variable "test_storage_class" {
  type = string
  validation {
    condition     = length(trimspace(var.test_storage_class)) > 0
    error_message = "Select an existing compatible test StorageClass."
  }
}

resource "kubernetes_namespace_v1" "validation" {
  metadata {
    name = var.validation_namespace
  }
}

resource "kubernetes_persistent_volume_claim_v1" "validation_pvc" {
  metadata {
    name      = "validation-pvc"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_until_bound = false
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = var.test_storage_class
    resources {
      requests = { storage = "1Gi" }
    }
  }
}

resource "kubernetes_deployment_v1" "validation_app" {
  metadata {
    name      = "validation-app"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_for_rollout = true
  spec {
    replicas = 1
    strategy {
      type = "Recreate"
    }
    selector {
      match_labels = { app = "validation-app" }
    }
    template {
      metadata {
        labels = { app = "validation-app" }
      }
      spec {
        automount_service_account_token = false
        node_selector                   = { "kubernetes.io/os" = "linux" }
        security_context {
          run_as_non_root = true
          run_as_user     = 65532
          run_as_group    = 65532
          fs_group        = "65532"
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }
        container {
          name    = "http"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args = [
            "test -f /data/index.html || printf 'fixture\\n' > /data/index.html; exec httpd -f -p 8080 -h /data"
          ]
          port {
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "8080"
            }
            period_seconds = 5
          }
          resources {
            requests = { cpu = "10m", memory = "16Mi" }
            limits   = { cpu = "100m", memory = "64Mi" }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "data"
            mount_path = "/data"
          }
        }
        volume {
          name = "data"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.validation_pvc.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "validation_service" {
  metadata {
    name      = "validation-service"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  spec {
    selector = { app = "validation-app" }
    type     = "ClusterIP"
    port {
      port        = 80
      target_port = "8080"
    }
  }
}
```

`wait_until_bound = false`により、`WaitForFirstConsumer`のPVCがバインドする前にTerraformがconsumerを作成できます。Deploymentはrollout／readinessを待ちます。1 replicaと`Recreate`を使い、RWOボリュームが複数ノードへrolling attachされる前提を避けています。そのため停止時間が発生します。PVCは実際にmountされますが、ファイルを提供できるだけでは置換後の永続性やバックアップ復元の成功を証明しません。独立した書き込み／再作成／読み取りと復元の根拠を使ってください。cleanup前にPV reclaim policyを確認します。`_v1`のリソースフィールドはprovider文書と照合しました。Kubernetes providerのapplyや実fixtureの実行はしていません。

**検証ダッシュボード**

以下のConfigMapは、`monitoring`を監視し`grafana_dashboard=1`ラベルを使う既存Grafana dashboard sidecar、datasource UID `prometheus`、単一クラスターのkube-prometheus-stack scrape構成を前提とします。実際の導入に合わせて設定とjobラベルを調整してください。このfixtureのために2つ目の監視スタックを導入しないでください。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-validation-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  cluster-validation.json: |
    {
      "uid": "eks-upgrade-validation",
      "title": "EKS Upgrade Validation",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Ready nodes",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum(max by (node) (kube_node_status_condition{job=\"kube-state-metrics\",condition=\"Ready\",status=\"true\"}))"
            }
          ]
        },
        {
          "id": 2,
          "title": "Ready active Pods (%)",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * sum(max by (namespace, pod, uid) (kube_pod_status_ready{job=\"kube-state-metrics\",condition=\"true\"}) and on (namespace, pod, uid) (max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}) == 1)) / sum(max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}))"
            }
          ]
        },
        {
          "id": 3,
          "title": "API requests / second",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "reqps"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (code) (rate(apiserver_request_total{job=\"apiserver\"}[5m]))"
            }
          ]
        },
        {
          "id": 4,
          "title": "Node CPU busy (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - avg by (instance) (max by (instance, cpu) (rate(node_cpu_seconds_total{job=\"node-exporter\",mode=\"idle\"}[5m]))))"
            }
          ]
        },
        {
          "id": 5,
          "title": "Node memory used (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 16
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - max by (instance) (node_memory_MemAvailable_bytes{job=\"node-exporter\"}) / max by (instance) (node_memory_MemTotal_bytes{job=\"node-exporter\"}))"
            }
          ]
        }
      ]
    }
```

「Readyなactive Pod」はreadinessを使い、完了／失敗したライフサイクル状態を除きます。`Running`だけではreadinessを意味しません。CPUパネルはidle counterのrateを使い、メモリには独立した割合パネルがあります。明記した単一クラスター範囲内で重複exporterサンプルを縮約します。マルチクラスターのデータソースでは、系列を結合する前にclusterラベルで絞り込み／グループ化してください。メトリクス欠落やactive Podの分母がゼロの場合はunknown／no dataのまま扱い、正常なゼロ値に置き換えないでください。このダッシュボード自体は、アップグレードの検証やリリースゲートの適用を行いません。

更新ID、smoke testの証拠、テスト環境／時刻、メトリクスクエリ／期間、失敗、未検証範囲を非公開の結果ディレクトリに保存します。本番トラフィックを増やす前にcanaryトラフィックと復旧条件を確認してください。AとBも一部の確認には役立ちますが、どちらも機能全体を検証しません。Dでは、検証前に利用者へ影響する可能性があります。

参考資料: [Persistent Volume](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)、[Podライフサイクル](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)、[Terraform PVC](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/persistent_volume_claim_v1)、[Prometheus関数](https://prometheus.io/docs/prometheus/latest/querying/functions/)。

</details>
