# EKSクラスター作成クイズ - Part 5

> **最終更新**: 2026年9月11日

このクイズでは、EKSの運用、ログ記録、ポリシー適用、テナント分離を扱います。最後の設問では、概念ガイドにあるアクセス検証とクラスター廃止を取り上げます。コマンドの実行には、対象クラスター/リージョン/kubeconfig、IAM、コントローラーの前提条件を確認してください。このレビューでは、クラウドへのデプロイや本番環境でのテストは行っていません。

## 選択問題

1. 割り込みに弱いベースライン容量と、中断可能な容量を組み合わせる方法はどれですか？
   * A) すべてのノードをOn-Demandにする
   * B) On-DemandグループとSpotグループを分け、ワークロードを配置する
   * C) 各グループの`capacityType`をReservedにする
   * D) すべてのワークロードにFargateを使う

<details>
<summary>解答を表示</summary>

**解答: B) On-DemandグループとSpotグループを分け、ワークロードを配置する**

中断に敏感なベースラインと、中断に耐えられる容量を分ける構成が適する場合があります。On-Demand用とSpot用のマネージドグループを別々に用意し、ワークロードを明示的に配置します。これは常に「最も効果的」なコスト戦略というわけではありません。ワークロードの使用率、信頼性要件、リージョンやインスタンスの料金、運用負荷によって結果は変わります。

AWSが示すSpotの割引はOn-Demand比で最大90%ですが、すべての容量プールで割引が保証されるわけでも、このガイドで削減額を測定したわけでもありません。On-DemandではSpotによる回収を避けられますが、保守や障害のリスクは残ります。Spotにはチェックポイント、再試行、余剰容量が重要です。

適正サイズへの調整、Cluster Autoscaler/Karpenter、互換性のあるGravitonイメージ、適切なコミットメント割引も選択肢です。Reserved Instances/Savings Plansは請求上の割引契約であり、マネージドノードグループに設定する通常の別容量タイプではありません。Fargateが適する需要パターンもありますが、常に特定のコンピューティング方式が有利と決めつけず、プロビジョニング容量と総コストを比較してください。

</details>

2. 適切なワークロードを複数のAZに分散する理由は何ですか？
   * A) 常にレイテンシーが下がる
   * B) スループットの向上が保証される
   * C) 1つのAZの障害に依存するリスクを減らす
   * D) リージョン間で自動的にレプリケーションされる

<details>
<summary>解答を表示</summary>

**解答: C) 1つのAZの障害に依存するリスクを減らす**

複数のAZを使うと、単一の障害ドメインへの依存を減らせます。EKSマネージドコントロールプレーンは複数AZに分散していますが、アプリケーションの可用性には、適切に分散したレプリカ、正常なエンドポイント、余剰容量、互換性のあるネットワーク/ストレージも必要です。

Kubernetesコントローラーは置き換え用Podを作成できますが、管理対象コントローラーのないPod自体は自動的に再作成されません。容量不足、厳格なアフィニティ、ゾーンに紐づくEBSボリュームによって復旧できない場合もあります。サブネットを複数指定しただけで、すべてのアプリケーションレプリカが分散されるとは限りません。トポロジー分散/アンチアフィニティと実際の配置を確認してください。

PDBが制御するのは自発的な退避であり、AZ障害ではありません。ローリングアップデートとAZ間フェイルオーバーはアプリケーション単位で検証し、データ復旧設計も必要です。複数AZを使ってもリージョン間レプリケーションは自動化されず、AZ間データ転送料が発生する場合があります。

</details>

3. 一般的なEKS EC2ノードでデフォルトのCNIは何ですか？
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>解答を表示</summary>

**解答: C) Amazon VPC CNI**

一般的なEKS EC2ノードでは、デフォルトでAmazon VPC CNIを使用します。サポートされるセカンダリIPまたはプレフィックスモードを使ってVPCアドレスを割り当てます。Auto Modeには独自のマネージドネットワーク機能があり、Hybrid Nodesではサポートされる別のCNIを使います。既存CNIの設定を確認せずに別のCNIを重ねてインストールしないでください。

Pod用Security Groupsには、対応するインスタンス/CNI設定とポリシー選択が別途必要です。Podごとに自動で一意のSecurity Groupが割り当てられるわけではありません。ネイティブNetworkPolicyにも、サポートされるコンピューティング環境と明示的な有効化が必要です。

この設計ではVPCネイティブのルーティングを使い、一般的なオーバーレイを避けますが、測定済みの性能保証ではありません。帯域幅、ルーティング、IP容量、ポリシー動作、アプリケーション要件を検証してください。Load Balancer Controllerなどの統合にも、個別のインストールと権限が必要です。

</details>

4. EKS OIDC issuerと投影ServiceAccount tokenを使うワークロードIDの仕組みはどれですか？
   * A) IAM Roles for Service Accounts (IRSA)
   * B) EKS access policy
   * C) Kubernetes RoleBindingだけ
   * D) ノードラベル

<details>
<summary>解答を表示</summary>

**解答: A) IAM Roles for Service Accounts (IRSA)**

**IAM Roles for Service Accounts** (IRSA)は、投影ServiceAccount token、クラスターのOIDC issuer、IAM trustを使ってSTS一時認証情報を取得します。trustは対象のaudience（`sts.amazonaws.com`）と正確なnamespace/ServiceAccount subjectに限定し、必要なAWSアクション/リソースだけを許可します。

Podで意図したServiceAccountを使い、互換性のあるSDK credential chainを確認してください。想定したroleを引き受けたことも検証します。AWSへのアクセス成功だけでは、別の認証情報が使われていないことを確認できません。IRSAだけでノードIMDS認証情報へのアクセスを防げるわけではありません。

EKS Pod IdentityもServiceAccountにroleを関連付ける仕組みですが、agent/associationの流れが異なります。利用可能なEC2/Auto Mode、および明示的に設定された対応Hybrid Nodesで利用できます。FargateではIRSAなど別の対応方式が必要です。どちらもEKS access entryではありません。ワークロードへのAWS権限とKubernetes APIへのアクセス権限は別です。

</details>

5. Kubernetesのスケジューリング需要に応じて、既存のEKSマネージドノードグループASGをスケールするコントローラーはどれですか？
   * A) Horizontal Pod Autoscaler
   * B) Vertical Pod Autoscaler
   * C) Cluster Autoscaler
   * D) ResourceQuota

<details>
<summary>解答を表示</summary>

**解答: C) Cluster Autoscaler**

Cluster Autoscalerは、検出された既存のノードグループ/ASGを調整します。対応したインストール、Kubernetes RBAC、専用のAWS権限、正しい検出タグが必要です。最小/最大サイズを設定しただけでインストールされるものではありません。

スケールアウトではスケジューリング要求と制約を考慮し、スケールインでは再配置/中断条件を考慮します。ノードを追加すればすべてのPending Podを配置できるわけではありません。また、スケールダウンの使用率判定はCPU使用率に基づくHPAの閾値と同じではありません。

HPAはレプリカ数を調整し、VPAはPod requestを推奨または変更します。どちらも間接的にノード需要を変える可能性があります。KarpenterはNodePool/NodeClaimを使う別の容量プロビジョナーであり、常に高速な代替手段でもASGコントローラーでもありません。制御ループとワークロード制約を検証してください。

</details>

## 短答問題

6. EKSコントロールプレーンのログをCloudWatchに有効化し、届いていることをどう確認しますか？

<details>
<summary>解答と解説</summary>

必要なコントロールプレーンログタイプを有効にします: `api`、`audit`、`authenticator`、`controllerManager`、`scheduler`です。EKSコンソールでは、古い「Logging」タブの手順ではなく、**Observability → Control plane logging → Manage logging**を使います。

次の例では5種類すべてを有効にします。環境に応じてレビュー済みの種類を選んでください。

```bash
set -euo pipefail
LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
戻されたupdate IDを`Successful`になるまで確認し、失敗した場合は次の変更に進む前に処理します。eksctlを使う場合は、ログ設定を反映するため`--approve`が必要です。

```bash
# Alternative to the AWS CLI update, not a second concurrent update.
eksctl utils update-cluster-logging --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --enable-types=api,audit,authenticator,controllerManager,scheduler --approve
```
ログはクラスターのリージョンにある`/aws/eks/<cluster-name>/cluster`へ送られます。ログストリームはローテーションされ、種類ごとに複数作られる場合があります。配信はベストエフォートで、通常は数分以内です。有効な設定、最新のストリーム時刻、実際の関連イベントを確認してください。ロググループが存在するだけでは配信の証明になりません。保持期間とアクセス制御を設定し、取り込み/保存コストを考慮し、機微な監査イベントの公開を避けてください。ワーカーノードとアプリケーションのログには別の収集手段が必要です。

</details>

7. 一般的なEKS LinuxノードのkubeletログをCloudWatchへ収集するにはどうしますか？

<details>
<summary>解答と解説</summary>

kubeletログはノードログであり、EKSコントロールプレーンログとは別です。EKS最適化AL2023 Linux環境では`kubelet.service`のsystemd journalを確認してください。`/var/log/kubelet.log`や`/var/log/kube-proxy.log`が存在すると決めつけてはいけません。kube-proxyは通常コンテナとしてログを出します。VPC CNIのログファイル/stdoutは設定によって異なります。

マネージド**Amazon CloudWatch Observability EKS add-on**はagent/operatorとFluent Bitをインストールします。quickstartの生manifestは、このマネージドadd-onと同じものではありません。既存ServiceAccountを上書きしたり、既存Fluent Bit ConfigMap全体を置き換えたりする前に、その所有者と設定を確認してください。

この例は**Linux EC2ラボ**向けで、Pod Identity Agentが利用可能であり、このクラスター向けに承認されたroleが`amazon-cloudwatch/cloudwatch-agent` ServiceAccountを信頼することを前提とします。CloudWatch権限をレビューしてください。`CloudWatchAgentServerPolicy`はAWS管理の基準ポリシーであり、すべてのログ範囲に対する最小権限だとは限りません。現行チャートのFluent Bitも同じServiceAccountを使うため、この構成では別の`fluent-bit` IAM ServiceAccountは不要です。

互換性のあるadd-on buildを選び、スキーマを確認してください。Helm chart versionとEKS add-on build文字列は別の値です。

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}"
CLUSTER_VERSION=$(aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.version --output text)
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --kubernetes-version "$CLUSTER_VERSION"
: "${CLOUDWATCH_ADDON_VERSION:?Choose a reviewed compatible build with the configuration fields below}"
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --query configurationSchema --output text > cloudwatch-addon-schema.json
```
次を`cloudwatch-addon-values.yaml`として保存してください。公式chart 6.6.0でレンダリングした設定です。Linux用の完全な`dataplane-log.conf` overrideはkubelet journalレコードだけを収集します。空のapplication/hostファイルにより、これらのデフォルトログ経路は無効になります。他のグローバルFluent Bitセクションはデフォルトを維持します。add-onはContainer Insightsメトリクスも収集するため、ログ専用agentのインストールではありません。この演習ではサービスを自動計装しないようApplication Signalsの自動監視を明示的に無効化しています。

```yaml
manager:
  applicationSignals:
    autoMonitor:
      monitorAllServices: false
containerLogs:
  fluentBit:
    config:
      extraFiles:
        application-log.conf: ''
        host-log.conf: ''
        dataplane-log.conf: |
          [INPUT]
            Name                systemd
            Tag                 dataplane.kubelet
            Systemd_Filter      _SYSTEMD_UNIT=kubelet.service
            DB                  /var/fluent-bit/state/kubelet.db
            Path                /var/log/journal
            Read_From_Tail      On

          [FILTER]
            Name                modify
            Match               dataplane.kubelet
            Rename              _HOSTNAME hostname
            Rename              MESSAGE message

          [OUTPUT]
            Name                cloudwatch_logs
            Match               dataplane.kubelet
            region              ${AWS_REGION}
            log_group_name      /aws/containerinsights/${CLUSTER_NAME}/dataplane
            log_stream_prefix   ${HOST_NAME}-
            auto_create_group   true
```
対象ノードにjournalのmount pathと書き込み可能なstate directoryがあることを確認してください。これらのLinux overrideはWindows収集を設定しません。混在環境、Hybrid、Auto Modeでは、それぞれの文書化されたpathが必要です。選択したadd-onのスキーマを確認し、updateへ適用する前に無関係な既存設定を保持してください。

```bash
# New installation only, after the schema/role/configuration review.
: "${CLOUDWATCH_ROLE_ARN:?Existing approved Pod Identity role}"
CW_ASSOCIATIONS=$(jq -cn --arg role "$CLOUDWATCH_ROLE_ARN" \
  '[{serviceAccount:"cloudwatch-agent",roleArn:$role}]')
aws eks create-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --pod-identity-associations "$CW_ASSOCIATIONS" \
  --configuration-values file://cloudwatch-addon-values.yaml --resolve-conflicts NONE
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --query 'addon.{status:status,health:health,version:addonVersion}'
```
指定したadd-on操作の完了を待ち、health error、agent/Fluent Bit Pod、`/aws/containerinsights/<cluster>/dataplane`に届いた新しいイベントを確認します。Helmのrender成功やロググループの存在だけでは、収集を証明しません。IAM、ネットワークendpoint、ログ保持、取り込み/メトリクス費用も確認します。既存の可観測性環境を使う場合は、計画した移行が必要です。ログを重複させる2つ目のcollectorを動かしたり、サービスを暗黙に再起動したりしないでください。ここではagentのインストール、journal収集、CloudWatch配信を実行していません。

</details>

8. PSPに代わる仕組みは何ですか。また、同等のadmission制御をどう評価しますか？

<details>
<summary>解答と解説</summary>

PodSecurityPolicyはKubernetes 1.21で非推奨となり、1.25で削除されました。現在サポートされるEKS versionには、そのAPIはありません。Pod Security Admission (PSA)はPod Security Standards (PSS) profileを適用しますが、すべてのPSP機能を項目ごとに置き換えるものではありません。

新しいEKS 1.36ラボnamespaceでは、将来のクラスター更新で選択したpolicy versionが暗黙に変わらないよう、profile versionを固定します。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: psa-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```
既存の本番namespaceでは、Restrictedをenforceする前にaudit/warnの結果とアプリケーション互換性を評価してください。PSAは検証を行いますが、旧PSPのmutation/defaulting動作は提供しません。host namespace、capability、volume、ID、seccompに関する旧制御を適切な代替策へ割り当ててください。

**Kyvernoの代替例:** 次は、レビュー対象のKyverno 1.19.1/chart 3.9.1で利用できる、現行CELベースの`policies.kyverno.io/v1` ValidatingPolicyを使います。Legacy ClusterPolicyは1.19で非推奨ですが、すでに削除されたという意味ではありません。互換性のあるcontroller/CRDは別途インストールし、レビュー済みの`policy-engine-lab` namespaceを使います。通常、init、ephemeralのすべてのcontainerを確認します。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```
**Gatekeeperの代替例:** ConstraintTemplateだけではルールは適用されません。templateと以下のConstraintはGatekeeper 3.23.1のレビュー済み例です。`templates.gatekeeper.sh/v1`と生成されるConstraint APIではversionが異なります。

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8snoprivilegedlab

      containers[c] {
        c := input.review.object.spec.containers[_]
      }
      containers[c] {
        c := input.review.object.spec.initContainers[_]
      }
      containers[c] {
        c := input.review.object.spec.ephemeralContainers[_]
      }
      violation[{"msg": msg}] {
        c := containers[_]
        c.securityContext.privileged == true
        msg := sprintf("Privileged container is not allowed: %v", [c.name])
      }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```
この2つのengineは代替案であり、1つの制御を示す例です。PSPとの完全な同等性や、本番向けhardening policyを示すものではありません。許可/`securityContext`欠落の場合と、privilegedな通常/init/ephemeral containerをテストしてください。admissionのfailure policy、webhook可用性、例外を考慮します。GuardDuty、Security Hub、Inspectorは対応リソース向けの脅威/姿勢/脆弱性に関する補完機能ですが、admission時のPod拒否を代替しません。

</details>

## ハンズオン問題

9. On-DemandとSpotのグループを分け、配置制御とautoscalingの前提条件を設定してください。

<details>
<summary>解答と解説</summary>

マネージドグループを**分けて**作成します。重要なワークロード向けOn-Demandは2～5ノード、中断に耐えられるワークロード向けSpotは2～10ノードが例です。測定済みのコスト削減額や容量保証ではありません。作成方法を1つ選び、未使用のグループ名を使ってください。事前にprivate subnetのegress/endpoint、IAM、AMI/imageの互換性を確認します。

eksctl設定では、サポートされる`managedNodeGroups`および`spot` fieldを使います。すべてのノードにautoscaler controller用権限を付与してはいけません。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: critical-workloads
  amiFamily: AmazonLinux2023
  instanceType: m5.xlarge
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  spot: false
  labels:
    workload-type: critical
    node-lifecycle: on-demand
- name: general-workloads
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large]
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    workload-type: general
    node-lifecycle: spot
  taints:
  - key: spot
    value: "true"
    effect: PreferNoSchedule
```
設定ファイルを保存してレビューした後、既存クラスターに`eksctl create nodegroup -f nodegroups.yaml`を実行します。次にAWS CLIの代替例を示します。EKS APIのtaint effectは大文字の名前と構造化された値を使い、Kubernetes/eksctlのCamelCaseとは異なります。

```bash
set -euo pipefail
# Alternative to eksctl; use unused group names and approved role/subnet IDs.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${CRITICAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=5,desiredSize=2 \
  --instance-types m5.xlarge --capacity-type ON_DEMAND --ami-type AL2023_x86_64_STANDARD \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --node-role "${NODE_ROLE_ARN:?}" \
  --labels workload-type=critical,node-lifecycle=on-demand
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$CRITICAL_NODEGROUP_NAME"

aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "${GENERAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types m5.large m5a.large m5d.large m5ad.large --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --subnets "$PRIVATE_SUBNET_A" "$PRIVATE_SUBNET_B" \
  --node-role "$NODE_ROLE_ARN" --labels workload-type=general,node-lifecycle=spot \
  --taints '[{"key":"spot","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GENERAL_NODEGROUP_NAME"
```
新しく作成しレビューした`placement-lab` namespace内で、次のsleeping containerはスケジューリングだけを示します。アプリケーション動作について主張する前に、レビュー済みの実アプリimageと置き換えてください。重要なワークロードのselectorはOn-Demand labelを要求します。一般ワークロードはSpotを優先しますが、他の場所へfallbackする場合があります。tolerationは配置を許可するもので、強制はしません。`PreferNoSchedule`はソフト制御です。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
  namespace: placement-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: critical-app
  template:
    metadata:
      labels:
        app: critical-app
    spec:
      automountServiceAccountToken: false
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: workload-type
                operator: In
                values:
                - critical
              - key: node-lifecycle
                operator: In
                values:
                - on-demand
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: general-app
  namespace: placement-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: general-app
  template:
    metadata:
      labels:
        app: general-app
    spec:
      automountServiceAccountToken: false
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 1
            preference:
              matchExpressions:
              - key: node-lifecycle
                operator: In
                values:
                - spot
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      tolerations:
      - key: spot
        operator: Equal
        value: 'true'
        effect: PreferNoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-app-pdb
  namespace: placement-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: critical-app
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: general-app-hpa
  namespace: placement-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: general-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```
記載したrequest/limit値は例です。PDBが保護するのは自発的な退避であり、Spotの容量回収やAZ障害は防ぎません。HPAにはMetrics Serverと、負荷とメトリクスの意味のある関係が必要です。このsleepingデモはスケーリング性能のベンチマークではありません。

専用のCluster Autoscaler ServiceAccount/roleを準備し、tagで範囲を限定したAWS権限と実際のASG検出tagを設定してください。ノードグループtagがASG tagである証明にはなりません。EKS 1.36向けには、レビュー済みchart/imageの組み合わせをrenderして、インストール前に内容を確認してください。

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
別途のレビューによる理由がない限り、ローカルストレージ/system Pod用の保護設定を維持してください。Cluster Autoscaler管理の混在グループでは、CPU/メモリ/GPUの形状が相互に比較可能であることも重要です。マネージドノードグループにはSpotのrebalance/drain処理がすでにあります。2つ目のNode Termination Handlerを安易に追加しないでください。self-managed容量には別途レビューしたライフサイクル処理が必要です。代表的なワークロード条件で中断からの復旧、配置、データ永続性、総コストを検証してください。

</details>

## 応用問題

10. EKSテナント分離の方式を比較し、実際の境界を説明してください。

<details>
<summary>解答と解説</summary>

実際の信頼、データ、可用性、ガバナンス要件に合わせてテナント境界を選びます。以下は**代替となる設計案**です。各例をすべて1つの共有namespaceに組み合わせる指示ではありません。

**クラスター/アカウントを分ける:** 専用API/control-planeリソースにより結合を減らし、ライフサイクルを個別に選びやすくなりますが、運用費用は増えます。共有IAM、VPC、storage、quota、外部serviceまで自動的に分離されるわけではなく、別テナントが絶対に影響しない保証もありません。条件を限定しない`eksctl create cluster`コマンドを2つ実行するのではなく、レビュー済みのクラスター作成ガイドを使ってください。

**制御を適用したnamespace:** namespaceは名前を分離しますが、すべてのセキュリティ境界や容量を分けるわけではありません。platform管理者が新しいテナントnamespaceを作成し、policy label、quota、RBAC境界を管理します。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-b
  labels:
    tenant: b
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```
以下のtenant-aの完全な例には、旧RoleBinding例に欠けていたRole、明示的なワークロード権限、namespace内通信と範囲を限定したDNS、ResourceQuota、LimitRangeがあります。認証済みの`tenant-a-users` groupと、同様にレビューしたtenant-b用リソースを別々に設定してください。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```
このpolicyには互換性のある適用engineが必要です。通常のCoreDNS labelを前提とするため、NodeLocal DNSCacheを使う場合は経路を調整してください。quotaはadmission時の上限であり、予約ノードや保証帯域ではありません。ワークロード作成権限によりnamespace内のServiceAccountやSecretを使える場合があります。admission制御でこれらを制限し、platform credentialをテナントnamespaceの外に保管してください。共有kernel/control-planeリソースについても脅威モデルを確認します。

**仮想クラスター:** 仮想API/control planeによりクラスター範囲の設定を分けられますが、共有ノードのワークロードはホストkernel/CNI/CSIを共有します。レビュー済みのvCluster 0.36.1設定は現行の`sync.fromHost.nodes` fieldを使い、host-node同期は無効のままです。テナント作成に必須ではありません。同期を有効にするとホストmetadataが露出する可能性があります。専用ノードを使うprivate/dedicated-node構成では、前提条件と分離特性が異なります。

以下を`vcluster-values.yaml`として保存し、storage classを承認済みの利用可能なclassに置き換えます。権限の強いsyncer/controllerをテナントがhost RoleBinding経由で変更できないよう、host namespaceはplatform側で別々に管理してください。

```yaml
sync:
  fromHost:
    nodes:
      enabled: false
controlPlane:
  statefulSet:
    persistence:
      volumeClaim:
        enabled: true
        storageClass: REPLACE_WITH_APPROVED_STORAGE_CLASS
        size: 5Gi
        retentionPolicy: Retain
    imagePullPolicy: IfNotPresent
```

```bash
helm repo add vcluster https://charts.loft.sh
helm repo update vcluster
helm template vcluster-tenant-a vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-a-host -f vcluster-values.yaml > tenant-a-reviewed.yaml
helm template vcluster-tenant-b vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-b-host -f vcluster-values.yaml > tenant-b-reviewed.yaml
```

render後のRBAC、storage、resource request、image、同期設定を確認し、レビュー済みのHelm/GitOps所有者を通じてデプロイします。公開chartはデフォルトで`vcluster-pro:0.36.1`をrenderします。デプロイ前にedition、利用可能な機能、licenseを確認してください。render成功は利用権、永続性、クラスター起動、本番分離の検証ではありません。仮想クラスターやhost namespaceを削除する前にテナントstateをbackupし、PVC/PV保持動作を確認します。

**AWS IDとガバナンス:** scopeを限定したtrustとresource権限を持つ、テナント別IRSAまたはサポートされるPod Identity roleを使います。これらAWS IDはKubernetes認可を補完します。SCPは対象となるmember account主体の最大権限を定めます。アクセスを付与する機能ではなく、Kubernetes namespaceを区別もしません。

次のS3拒否例は、**tenant Aのmember account/OUだけ**に付けるSCPを示し、レビュー済みのtenant B bucketを対象にします。AとBを区別する目的で共有アカウントに付けてはいけません。

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyTenantBStoreFromTenantAAccount",
    "Effect": "Deny",
    "Action": ["s3:*"],
    "Resource": [
      "arn:aws:s3:::amzn-s3-demo-tenant-b",
      "arn:aws:s3:::amzn-s3-demo-tenant-b/*"
    ]
  }]
}
```
SCPはmanagement accountやservice-linked roleを制限せず、無関係な外部アカウントの主体にも直接適用されません。resource policy、IAM権限、データ保護は引き続き必要です。これはアカウントレベルのguardrailの一例で、完全なテナント分離policyではありません。選んだ設計で実効アクセスとrollback/保持をテストしてください。ここではクラスター、仮想クラスター、SCPを作成していません。

</details>

## アクセスとライフサイクルの確認

11. `update-kubeconfig`を実行すると、Kubernetes権限が付与されますか？
   * A) はい。自動的にcluster-adminになる
   * B) いいえ。クライアントを設定するもので、権限はaccess entry/policy/RBACで決まる
   * C) はい。CA証明書を通じて付与される
   * D) 新しいnamespaceを作る場合だけ付与される

<details>
<summary>解答を表示</summary>

**解答: B) いいえ。クライアントを設定するもので、権限はaccess entry/policy/RBACで決まる**

初期管理権限はbootstrap/toolの設定に依存します。既知の管理者identityを維持し、意図したroleで明示的にテストしてください。

</details>

12. namespaceのRoleBindingでEKS cluster-admin access policyの権限を狭められますか？
   * A) はい。RBACは常に優先される
   * B) いいえ。権限付与は加算される
   * C) はい。group名が`system:masters`なら可能
   * D) `kubectl --as`を使う場合に限り可能

<details>
<summary>解答を表示</summary>

**解答: B) いいえ。権限付与は加算される**

意図したaccess-policy scopeまたはカスタムRBAC groupを使ってください。`--as`/`--as-group`はKubernetes RBACを強制するもので、EKS access-policy権限のテストにはなりません。

</details>

13. Podのphaseが`Running`であること以外に、何を確認しますか？
   * A) 何も確認しなくてよい
   * B) log-group名だけ
   * C) readiness、rollout/health、意図したアプリケーション経路
   * D) すべてのJobを永久に実行状態にする

<details>
<summary>解答を表示</summary>

**解答: C) readiness、rollout/health、意図したアプリケーション経路**

`Running`でもcontainerがreadyとは限りません。Jobが正しく完了した場合は`Succeeded`になります。想定するコンピューティング環境と、実際のDNS/Service動作を検証してください。

</details>

14. 適切なEKSアップグレード計画はどれですか？
   * A) 最新のupstream versionなら何でも使う
   * B) minor versionを2つ飛ばしてアップグレードする
   * C) EKS release/readiness情報を確認し、minor versionを1つずつ上げる
   * D) rollbackですべての永続データが復元されると考える

<details>
<summary>解答を表示</summary>

**解答: C) EKS release/readiness情報を確認し、minor versionを1つずつ上げる**

7日以内の条件付きrollbackでも、etcd、ワークロード、データは巻き戻りません。コンポーネント互換性とbackupは別途確認してください。

</details>

15. クラスター廃止の前に何を行うべきですか？
   * A) すべてのPVCをすぐ削除する
   * B) 名前で汎用IAM roleを削除する
   * C) 最初にVPCを削除する
   * D) identity/所有者、backup/reclaim policy、依存関係、保護、機能を確認する

<details>
<summary>解答を表示</summary>

**解答: D) identity/所有者、backup/reclaim policy、依存関係、保護、機能を確認する**

元のIaC所有者、明示的にレビューしたリソース、完了確認を使ってください。共有リソースと復旧の証跡を保全します。

</details>

## 参考資料

- [CloudWatch Observability add-on](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)
- [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
- [vCluster 0.36.1 configuration](https://github.com/loft-sh/vcluster/blob/v0.36.1/chart/values.yaml)
- [SCP scope](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
- [EKS rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
