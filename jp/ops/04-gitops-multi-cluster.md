# Argo CDマルチクラスター構成とIAM Identity Center

> **レビュー基準**：Argo CD 3.5.5／chart 10.10.5、Terraform 1.15.7／Helm Provider 3.3.0、ESO 2.12.0。\
> **最終レビュー日**：2026年10月16日。ローカルのスキーマ、レンダリング、テスト用代替サービスを確認しました。実際のEKSへのインストール、SSOログイン、Secrets Managerからの読み出しは行っていません。

< [前へ：CIパイプライン](03-ci-pipelines.md) | [目次](README.md) | [次へ：GitOpsオートメーション](05-gitops-automation.md) >

この章では、管理EKSクラスター（hub）上のArgo CDから、2つのワークロードクラスター（spoke）を管理します。CIで承認済みイメージdigestを作成し、レビュー済みのGit変更でデプロイ対象のdigestを選択します。一元管理しても、各クラスターに必要な認証、認可、ネットワーク設定は置き換わりません。

## マルチクラスターアーキテクチャ

| 場所 | 責務 | 必要なアクセス |
| --- | --- | --- |
| Hub Application Controller | 望ましい状態を比較して同期 | 接続先EKS APIと許可されたKubernetesリソース |
| Hub Server／ApplicationSet | ユーザー操作とクラスター関連処理 | 該当機能に必要な認証情報とhub Secret |
| Repo Server | Git／Helmソースのレンダリング | 承認済みリポジトリと利用可能なリポジトリ認証情報 |
| Spoke | アプリケーションとNodePoolを稼働 | 対象IAMプリンシパルのEKS Access EntryとRBAC |
| ESO | 外部値をKubernetes Secretへ同期 | 実際のControllerロールによる指定Secretへのアクセス |

Blue／greenはクラスターの識別に使います。例のワーカーNodePoolは異なるAZに配置しますが、EKSコントロールプレーンはリージョン単位です。hubに障害が起きてもspoke上の既存Podはすぐに停止しない場合がありますが、デプロイや調整が停止することがあります。hubの認証情報が侵害されると複数のspokeに影響する可能性があります。Git履歴だけでは、すべての手動変更、ログイン、データベース操作を監査できません。

### 接続先の前提条件

1. 対象クラスターの認証が必要なhub Application ControllerとServer／ApplicationSetアカウントに、サポート対象のPod IdentityまたはIRSAを設定します。Repo ServerのGit／ECRアクセスは別の設定です。
2. 管理ロールが**接続先ロールの正確なARNだけ**を引き受けられるようにし、接続先ロールの信頼ポリシーも意図した管理ロールだけに制限します。
3. 対象EKSの認証モードを確認し、そのロールのAccess Entryを作成します。`demo-app`名前空間に必要なリソース向けのアクセスと、クラスター範囲のNodePool管理を分離します。この例では名前空間を事前に作成します。
4. hubからプライベートな対象APIエンドポイントへのDNS、ルーティング、セキュリティグループアクセスを確認します。IAM権限だけではネットワーク接続は得られません。

ロールとAccess Entryは、レビュー済みの[Argo CDインストールガイド](../gitops/argocd/01-installation.md)と[EKSアクセス管理ガイド](../eks/02-eks-cluster-creation-part3.md)を参照してください。`aws-auth.mapRoles`全体を置き換えたり、デフォルトで`system:masters`を付与したりしないでください。

Argo CD 3.5.5の`awsAuthConfig.roleARN`経路ではロールを引き受けますが、ExternalIdフィールドは公開されていません。この経路から送られないExternalIdを必須とする信頼条件を設定すると、認証できません。その条件が必要なら、サポート対象の別の認証経路を設計してください。

### 実際のエンドポイントを使った宣言的な登録

対象ごとにこのスクリプトを実行します。`CLUSTER_COLOR`、クラスター名、ロールを変えると、デフォルトのkubeconfigコンテキストを変更せずに個別のSecretを作成できます。名前空間アクセスは`demo-app`に限定し、NodePool向けのクラスターリソースアクセスを有効にします。この設定だけでは対象側のRBAC権限は付与されません。

```bash
# fixtures/register-cluster.sh
#!/usr/bin/env bash
set -euo pipefail
: "${ARGOCD_CONTEXT:?Set the hub kubeconfig context}"
: "${TARGET_EKS_NAME:?Set the actual target EKS cluster name}"
: "${TARGET_AWS_REGION:?Set the target AWS region}"
: "${TARGET_ROLE_ARN:?Set the pre-authorized target role ARN}"
: "${CLUSTER_COLOR:?Set blue or green}"
case "$CLUSTER_COLOR" in blue|green) ;; *) exit 2 ;; esac
[[ "$TARGET_ROLE_ARN" =~ ^arn:aws:iam::[0-9]{12}:role/.+ ]] || exit 2
umask 077
REVIEW_TMP="$(mktemp -d)"
trap 'rm -rf -- "$REVIEW_TMP"' EXIT
aws eks describe-cluster --name "$TARGET_EKS_NAME" --region "$TARGET_AWS_REGION" \
  --query 'cluster.{name:name,server:endpoint,ca:certificateAuthority.data}' \
  --output json > "$REVIEW_TMP/cluster.json"
jq -e '(.name | type == "string" and length > 0)
  and (.server | type == "string" and startswith("https://"))
  and (.ca | type == "string" and length > 0)' "$REVIEW_TMP/cluster.json" >/dev/null
jq --arg role "$TARGET_ROLE_ARN" --arg color "$CLUSTER_COLOR" '{
  apiVersion:"v1",kind:"Secret",
  metadata:{name:("workload-"+$color),namespace:"argocd",labels:{
    "argocd.argoproj.io/secret-type":"cluster",
    "environment":"production","cluster-color":$color,"gitops-target":"true"
  }},
  type:"Opaque",
  stringData:{
    name:("workload-"+$color),server:.server,namespaces:"demo-app",
    clusterResources:"true",
    config:({
      awsAuthConfig:{clusterName:.name,roleARN:$role},
      tlsClientConfig:{insecure:false,caData:.ca}
    }|tojson)
  }
}' "$REVIEW_TMP/cluster.json" > "$REVIEW_TMP/secret.json"
kubectl --context "$ARGOCD_CONTEXT" apply -f "$REVIEW_TMP/secret.json"
```

クラスターを検出するOperatorのIDと、hub Podが使うロールは異なるIDです。EKSホスト名や証明書を推測して作成しないでください。名前空間を追加する場合は、クラスターSecret、AppProject、対象側の権限をまとめて更新します。対象のRBACに加え、`resource.respectRBAC`などのキャッシュ設定を確認し、不要なリソース監視を避けてください。

`argocd cluster add <kubeconfig-context>`は、対象のServiceAccount／RBACを作成する場合がある代替コマンドです。読み取り専用ではありません。パスワードを引数で渡さず、対話型ログインまたはSSO CLIログインを使ってください。

## Argo CDのTerraformインストール

このrootは、既存hub、インストール権限、実行環境のAWS CLIがあることを前提とします。Helm Provider 3では`kubernetes = { ... }`オブジェクト形式を使います。Exec認証は短期間のEKSトークンを取得するため、EKS認証データソースのトークンをTerraform stateに保存しません。AWS Providerだけがロールを引き受ける構成では、別プロセスのAWS CLI execも意図した認証情報を使うよう設定してください。

```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "= 3.3.0"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

data "aws_eks_cluster" "hub" {
  name = var.management_cluster_name
}

provider "helm" {
  kubernetes = {
    host                   = data.aws_eks_cluster.hub.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.hub.certificate_authority[0].data)
    exec = {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.management_cluster_name, "--region", var.aws_region]
    }
  }
}

resource "helm_release" "argocd" {
  name             = "argocd"
  namespace        = "argocd"
  create_namespace = true
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "10.10.5"
  timeout          = 900
  wait             = true
  values           = [file("${path.module}/argocd-values.yaml")]
}
```

```hcl
# terraform/variables.tf
variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}

variable "management_cluster_name" {
  type = string
  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$", var.management_cluster_name))
    error_message = "Use the actual EKS management cluster name."
  }
}
```

[第1章](01-infrastructure-setup.md)のアカウント／環境固有バケットを使って、`encrypt = true`、`use_lockfile = true`、重複しないstate keyを含む別の`backend.hcl`を設定します。`terraform init -backend-config=backend.hcl`を実行してplanをレビューしてください。古いDynamoDBロック設定や、別rootのstate keyをコピーしないでください。

Terraformファイルと同じ場所に次の`argocd-values.yaml`を保存します。これは[レビュー済みインストールガイド](../gitops/argocd/01-installation.md)のHA構成を出発点として再利用します。同じConfigMapを別のTerraformリソースやkubectl手順で同時管理しないでください。

```yaml
# fixtures/argocd-values.yaml
fullnameOverride: argocd
global:
  domain: argocd.example.com
configs:
  params:
    server.insecure: false
  cm:
    url: https://argocd.example.com
    users.anonymous.enabled: 'false'
    exec.enabled: 'false'
controller:
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: '1'
      memory: 2Gi
  pdb:
    enabled: true
    minAvailable: 1
server:
  replicas: 2
  service:
    type: ClusterIP
  ingress:
    enabled: false
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
  pdb:
    enabled: true
    minAvailable: 1
repoServer:
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: '1'
      memory: 1Gi
  pdb:
    enabled: true
    minAvailable: 1
applicationSet:
  replicas: 2
  pdb:
    enabled: true
    minAvailable: 1
notifications:
  enabled: true
redis:
  enabled: false
redis-ha:
  enabled: true
  replicas: 3
  persistentVolume:
    enabled: false
  haproxy:
    enabled: true
    replicas: 3
```

この出発点ではHTTPSのClusterIPを公開し、外部Ingressを無効にしています。実際のSSOには正しいルーティングを設定した到達可能なHTTPSドメインが必要です。インストールガイドのALB例を追加する際は、HTTPSバックエンドを`server.insecure=false`に合わせてください。HTTPに変更するならバックエンドとヘルスチェックのプロトコルを両方変更します。ネイティブgRPCとgRPC-Webのルーティングも区別してください。

Application Controllerの複数レプリカは**クラスターのシャーディング**を行います。1つのactive leader以外がすべてstandbyになる構成ではありません。ApplicationSetには独立したleader electionがあります。statelessなServerでは、レプリカが複数あるだけでsticky sessionが必須になるわけではありません。バンドルされたストレージ設定ではDexのデフォルト単一レプリカを維持してください。

Redisは再構築可能なキャッシュです。コア設定はKubernetesオブジェクトに保存されます。Redis HAだけであらゆる障害時の無停止動作が保証されるわけではありません。レプリカ、PDB、ノード配置、予備容量をあわせて設計してください。PDBはAZ障害やすべての強制終了を防ぐものではありません。ServiceMonitorはPrometheus OperatorのCRDが存在してから有効にします。

## NodePoolのGitOps管理

NodePoolはKubernetesカスタムリソースであり、Argo CDで管理できます。ただしTerraformで管理できないという意味ではありません。リソースごとに管理者を1つ選び、同じ名前の組み込み／Terraform管理リソースを誤って引き継がないよう、意図を持って管理を移行してください。

以下では既存のAuto Mode `default` NodeClassを使います。Subnet selectorには目的のAZを含める必要があります。次の完全なファイル構成を作成してください。

```text
nodepools/
  base/kustomization.yaml
  base/nodepool.yaml
  overlays/blue/kustomization.yaml
  overlays/green/kustomization.yaml
```

```yaml
# nodepools/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - nodepool.yaml
```

```yaml
# nodepools/base/nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: workloads
  annotations:
    argocd.argoproj.io/sync-options: Prune=confirm,Delete=confirm
spec:
  template:
    metadata:
      labels:
        workload-type: applications
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: [amd64, arm64]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [m7i.large, m7i.xlarge, m7g.large, m7g.xlarge]
  limits:
    cpu: "100"
    memory: 200Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
```

```yaml
# nodepools/overlays/blue/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
patches:
  - target:
      group: karpenter.sh
      version: v1
      kind: NodePool
      name: workloads
    patch: |
      - op: add
        path: /spec/template/metadata/labels/cluster-color
        value: blue
      - op: add
        path: /spec/template/spec/requirements/-
        value:
          key: topology.kubernetes.io/zone
          operator: In
          values: [ap-northeast-2a]
```

```yaml
# nodepools/overlays/green/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
patches:
  - target:
      group: karpenter.sh
      version: v1
      kind: NodePool
      name: workloads
    patch: |
      - op: add
        path: /spec/template/metadata/labels/cluster-color
        value: green
      - op: add
        path: /spec/template/spec/requirements/-
        value:
          key: topology.kubernetes.io/zone
          operator: In
          values: [ap-northeast-2c]
```

`kustomize build nodepools/overlays/blue`とgreen側の両方をレビューします。標準のインスタンスタイプ要件を使い、セルフマネージドKarpenterの`karpenter.k8s.aws/*`キーをAuto Modeに混在させないでください。ワークロードのselector、アーキテクチャ、配置要件を各NodePoolに合わせます。

セルフマネージド向け`EC2NodeClass`の`amiSelectorTerms`、`blockDeviceMappings`、`instanceStorePolicy`などのフィールドをAuto Mode `NodeClass`へコピーしないでください。カスタムAuto Modeクラスでは実在するノードロール、Subnet／Security Groupのselector、`ephemeralStorage`などのサポート対象フィールドを使います。別のノードロールには、対応するAuto Mode node access entryも必要です。永続データベースストレージはエフェメラルディスクと分けて設計してください。[NodePool／NodeClassガイド](../eks-auto-mode/02-nodepool-configuration.md)を参照してください。

### Projectと手動承認

hubに次のAppProjectを作成し、Git URLを承認済みリポジトリへ置き換えてください。宛先名は登録スクリプトに合わせます。インフラProjectはNodePoolを許可し、アプリケーションProjectは必要な名前空間スコープの種類だけを許可します。AppProjectはKubernetes RBACを置き換えず、信頼できないコードを隔離するものでもありません。

```yaml
# fixtures/projects.yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: infrastructure
  namespace: argocd
spec:
  sourceRepos: [https://github.com/REPLACE_ORG/infra-manifests.git]
  destinations:
    - name: workload-blue
      namespace: demo-app
    - name: workload-green
      namespace: demo-app
  clusterResourceWhitelist:
    - group: karpenter.sh
      kind: NodePool
  namespaceResourceWhitelist: []
---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: applications
  namespace: argocd
spec:
  sourceRepos: [https://github.com/REPLACE_ORG/app-manifests.git]
  destinations:
    - name: workload-blue
      namespace: demo-app
    - name: workload-green
      namespace: demo-app
  clusterResourceWhitelist: []
  namespaceResourceWhitelist:
    - group: apps
      kind: Deployment
    - group: ""
      kind: Service
    - group: ""
      kind: ConfigMap
    - group: autoscaling
      kind: HorizontalPodAutoscaler
    - group: policy
      kind: PodDisruptionBudget
```

```yaml
# fixtures/nodepool-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nodepools-blue
  namespace: argocd
spec:
  project: infrastructure
  source:
    repoURL: https://github.com/REPLACE_ORG/infra-manifests.git
    targetRevision: main
    path: nodepools/overlays/blue
  destination:
    name: workload-blue
    namespace: demo-app
  syncPolicy:
    syncOptions:
      - ServerSideApply=true
    retry:
      limit: 3
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 1m
```

greenでは、Application名、宛先、overlay pathをまとめて変更します。このインフラ例はレビューのため自動同期を無効にしています。Applicationのcascade finalizerを省略し、NodePoolのprune／削除には確認を必須とします。`automated.prune=false`だけですべての削除経路を防げるわけではありません。

NodePool変更はdriftやノード置換を引き起こすことがあります。Disruption budgetが制御するのは対象となる自発的な中断であり、すべての有効期限切れ、Spot中断、強制削除ではありません。Auto Modeノードの寿命上限、PDB、drain時間、置換容量をあわせて検討してください。

## ApplicationSetの戦略

同期を有効にする前に、生成されるApplicationと実際のpathを確認してください。これらの例は既存の`demo-app`名前空間を使います。各Applicationディレクトリには有効なKustomizationが必要で、リソース名を重複させないでください。

### Cluster Generator

登録済みクラスターのうち、`gitops-target=true`ラベルが付いたものだけを選択します。この例と次のMatrix例は**代替案**です。同じfrontendリソースを両方に管理させないでください。

```yaml
# fixtures/cluster-appset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: frontend-clusters
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: [missingkey=error]
  syncPolicy:
    preserveResourcesOnDeletion: true
  generators:
    - clusters:
        selector:
          matchLabels:
            gitops-target: "true"
            environment: production
  template:
    metadata:
      name: '{{.nameNormalized}}-frontend'
    spec:
      project: applications
      source:
        repoURL: https://github.com/REPLACE_ORG/app-manifests.git
        targetRevision: main
        path: 'apps/frontend/overlays/{{index .metadata.labels "cluster-color"}}'
      destination:
        name: '{{.name}}'
        namespace: demo-app
      syncPolicy:
        automated:
          prune: false
          selfHeal: true
```

`nameNormalized`はKubernetes名に適しており、`name`は登録先の宛先名です。ハイフンを含むラベルキーにはGo templateの`index`を使います。Git file generatorでは、生成された`.path`メタデータとの衝突を避けるため、`sourcePath`などの設定フィールドを使ってください。

### MatrixとGit Directory Generator

```yaml
# fixtures/matrix-appset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: application-matrix
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: [missingkey=error]
  syncPolicy:
    preserveResourcesOnDeletion: true
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  gitops-target: "true"
                  environment: production
          - git:
              repoURL: https://github.com/REPLACE_ORG/app-manifests.git
              revision: main
              directories:
                - path: apps/*
                - path: apps/internal
                  exclude: true
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.path.basenameNormalized}}'
    spec:
      project: applications
      source:
        repoURL: https://github.com/REPLACE_ORG/app-manifests.git
        targetRevision: main
        path: '{{.path.path}}/overlays/{{index .metadata.labels "cluster-color"}}'
      destination:
        name: '{{.name}}'
        namespace: demo-app
      syncPolicy:
        automated:
          prune: false
          selfHeal: true
```

このMatrixには子Generatorが**2つ**あります。2つのクラスターと一致する3つのアプリから、組み合わせが6つ生成されます。Combination Generatorを任意の深さで入れ子にはできません。`apps/internal`自体を除外してください。`apps/internal/*`だけの除外では親ディレクトリが残る場合があります。

Go templateを適用できるのは文字列フィールドです。`prune: '{{.prune}}'`のような文字列templateをブール値フィールドに置いたり、`if`式をYAMLキーとして使ったりしないでください。明示的なブール値か、検証済みの`templatePatch`を使います。外部入力がsource path、Project、宛先を自由に選べるようにすると、権限昇格経路が生じる可能性があります。

`preserveResourcesOnDeletion=true`は、生成されたApplicationが削除された場合にリソースを残す選択肢です。既存finalizerを除去する移行ではなく、明示的なpruningや手動のリソース削除とも異なります。Gitから削除されたリソースの後始末を誰が行うか決めてください。

### 適用順序とPRプレビュー

- Sync waveは1つのApplication内のリソース適用順序を決めます。生成Applicationに付けたwave annotationだけでは、クラスターをまたぐApplicationSetのデプロイを順番にしません。
- クラスター間の承認／healthの段階的な進行には、別の昇格ワークフローまたはサポート対象のApplicationSet RollingSyncを使います。機能設定、health gate、自動同期の制約は[ApplicationSetガイド](../gitops/argocd/04-applicationsets.md)を参照してください。
- PR generatorはPRのコードやマニフェストを実行できます。隔離された保護対象のプレビュークラスター、制限付きAppProject／RBAC、ResourceQuota、検証済みイメージdigestを使ってください。`preview`ラベルは信頼境界ではありません。
- PRを閉じるとGeneratorの出力から削除され、設定済みの削除動作が実行されます。`info`はTTLではありません。また`CreateNamespace=true`で作った名前空間がApplicationとともに削除される保証もありません。finalizer、リソース保持、名前空間の後始末を誰が担うか定義してください。

検証済みPR、templatePatch、RollingSyncの例は[ApplicationSetの章](../gitops/argocd/04-applicationsets.md)にあります。

## IAM Identity Center SSO

この章では、Argo CDが文書化しているIAM Identity Centerとの連携方法である、**Dexを使ったSAML 2.0**を扱います。Identity CenterのOAuth／trusted identity propagation機能を、汎用のArgo CD OIDC issuerであるかのように扱わないでください。SAML sign-in URLはOIDC discovery endpointではありません。

1. IAM Identity Centerの**Applications**で、カスタマーマネージドSAML 2.0アプリケーションを作成します。
2. 実際のドメインを使い、ACS URLとAudienceを`https://argocd.example.com/api/dex/callback`に合わせます。このアプリケーションに許可するユーザー／グループを割り当てます。
3. この**アプリケーションの**sign-in URLと署名証明書を取得します。外部IdPをIdentity Centerへ接続するためのIdentity Sourceメタデータと混同しないでください。
4. 対応するmappingを使って`email`などの必要なユーザー属性を設定します。実際のassertionでsubjectと属性の値を確認してください。
5. BEGIN／END行を含むPEM全体をBase64エンコードして`caData`に設定します。署名検証を有効のままにしてください。

これらの設定をHelm管理下の`argocd-values.yaml`に統合します。プレースホルダーURL／証明書や、Base64化していないPEMの`caData`では認証できません。

```yaml
# fixtures/sso-values.yaml
# Merge into the Helm-owned argocd-values.yaml after configuring the SAML app.
dex:
  enabled: true
configs:
  cm:
    url: https://argocd.example.com
    dex.config: |
      connectors:
        - type: saml
          id: identity-center
          name: AWS IAM Identity Center
          config:
            ssoURL: https://REPLACE_WITH_APPLICATION_SIGN_IN_URL
            caData: BASE64_OF_COMPLETE_APPLICATION_SIGNING_CERTIFICATE_PEM
            entityIssuer: https://argocd.example.com/api/dex/callback
            redirectURI: https://argocd.example.com/api/dex/callback
            usernameAttr: email
            emailAttr: email
  rbac:
    policy.default: role:authenticated
    scopes: '[email]'
    policy.csv: |
      p, role:application-viewer, applications, get, applications/*, allow
      p, role:application-operator, applications, get, applications/*, allow
      p, role:application-operator, applications, sync, applications/*, allow
      g, viewer@example.com, role:application-viewer
      g, operator@example.com, role:application-operator
```

最小例ではIdentity Centerの**検証済みemail claim**を明示的にmappingします。サンプルを組織が管理する正確なIDへ置き換え、アカウントの変更や退職時にもmappingを更新してください。デフォルトの`role:authenticated`には権限がありません。デフォルトを`role:readonly`にすると、認証済みのすべてのユーザーにその権限を付与します。後続のdeny policyでdefault-roleの権限を取り消すことはできません。

**アプリケーションへのグループ割り当てとgroups assertionは別のものです**。Argo CDのIdentity Centerガイド自体も、group属性mappingをAWS公式ドキュメントではサポートされていない回避策として説明しています。グループが自動伝播すると仮定したり、表示名とGroup IDを混同したりしないでください。グループRBACが必要なら、まずサポート対象のIdP経路と実際のclaimを確認してから、`groupsAttr`、`scopes`、正確なpolicy値を一致させてください。

Argo CD SSOにはIAM SAML providerや`sts:AssumeRoleWithSAML`ロールの作成は不要です。これは別のAWSロールフェデレーション経路です。Argo CD RBAC、EKS IAM、Kubernetes RBACの権限が自動的に同一になるわけでもありません。

SSOユーザー、承認済み管理者が少なくとも1人いること、復旧経路を確認してからローカルadminを無効化してください。デバッグログやSAML assertionには個人情報／認証データが含まれる場合があります。共有ログに出力しないでください。ACS／Audience、証明書／時刻、割り当て、属性、RBACを別々に診断してください。

## Secret管理

各spokeにESO 2.12.0とv1 CRDをインストールします。[第1章](01-infrastructure-setup.md)のPod Identity associationを名前空間／ServiceAccount `external-secrets`に設定し、指定Secretの読み取り権限を再利用してください。hubにだけ関連付けたロールがspoke ESO Podに引き継がれるわけではありません。

```yaml
# fixtures/eso-values.yaml
# Reuse the existing external-secrets ServiceAccount Pod Identity association.
installCRDs: true
replicaCount: 2
leaderElect: true
serviceAccount:
  create: true
  name: external-secrets
  annotations: {}
serviceMonitor:
  enabled: false
```

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm upgrade --install external-secrets external-secrets/external-secrets \
  --version 2.12.0 --namespace external-secrets --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values eso-values.yaml
```

Pod Identityでは、**稼働中のESO Controller**がAWSデフォルト認証情報チェーンを使います。この経路に`auth.jwt.serviceAccountRef`やIRSA annotationを追加しないでください。ESOが別の名前空間のServiceAccountになり代わって、そのアカウントのPod Identity associationを得ることはできません。

```yaml
# fixtures/external-secrets.yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: application-config
  namespace: demo-app
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: demo-app
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: application-config
    kind: SecretStore
  target:
    name: database-credentials
    creationPolicy: Owner
    deletionPolicy: Retain
  data:
    - secretKey: username
      remoteRef:
        key: myapp/production/database
        property: username
    - secretKey: password
      remoteRef:
        key: myapp/production/database
        property: password
        version: AWSCURRENT
    - secretKey: host
      remoteRef:
        key: myapp/production/database
        property: host
    - secretKey: port
      remoteRef:
        key: myapp/production/database
        property: port
    - secretKey: database
      remoteRef:
        key: myapp/production/database
        property: dbname
```

名前付きSecret `myapp/production/database`にはusername／password／host／port／dbnameの各フィールドが必要です。ControllerのIAM policyは正確なARNを許可しなければなりません。Customer-managed KMS keyを使う場合は、範囲を絞ったdecrypt権限と互換性のあるkey policyも必要です。これは名前を指定して読み取る例であり、探索／書き込み権限は含みません。

`@`、`:`、`/`を含むpasswordを文字列結合せず、アプリケーションのURL builderで接続URLを作成してください。Secretの環境変数は既存Pod内で自動更新されません。アプリケーション固有のreload／restart方法を用意してください。

1つのControllerロールを使うnamespaced SecretStoreだけでIAM分離が自動的に実現するわけではありません。Store変更権限とadmission policyを組み合わせ、Controllerロール／scopeの分離またはレビュー済みの`provider.aws.role`引き受けを設計してください。IRSAの`auth.jwt.serviceAccountRef`はOIDC trustとServiceAccountを別途必要とする、異なる認証経路です。

### 所有権、更新、ローテーション

- Git／Argo CDがExternalSecretを管理し、ESOが生成Secretを管理します。Helm／Git／ESOが同じフィールドを繰り返し上書きする状態を避けてください。まずCRD／Controller／Storeをインストールし、Readyを確認します。
- `refreshInterval`は値を再読み込みしますが、Secrets Managerのpasswordをローテーションしたり証明書を発行したりはしません。ローテーション関数、ネットワーク、データベース権限、サービス固有のローテーション設定は別途必要です。
- `AWSCURRENT`と`AWSPREVIOUS`はバージョンstageです。`AWSPREVIOUS`がまだない段階で必須にすると同期全体が失敗する場合があります。以前のpasswordが引き続き有効であることや、データベースのロールバックを保証するものではありません。
- `creationPolicy: Owner`と`deletionPolicy: Retain`は異なるライフサイクルイベントに関する設定です。外部値が消えたときの保持は、ExternalSecret自体が削除された場合のowner-reference cleanupを無効にしません。
- `IgnoreExtraneous`は差分ステータスに影響します。管理対象のExternalSecretを自動的に同期／pruningから除外するものではありません。
- `PushSecret`はAWSへの書き込み機能であり、読み取り専用ロールでは動きません。作成／更新／tag権限、任意機能の権限、所有権の競合、削除、暗号化をレビューしてください。誤って双方向同期ループを作らないでください。

## 検証の順序

hubのインストール／HTTPS、対象ロール／Access Entry／RBAC／ネットワーク、クラスターSecret、AppProject、手動レビュー済みNodePool、生成Application、実際のSSO許可／拒否ケース、ESO Ready状態とアプリケーションのreloadを順番に検証します。Secret値を出力せず、ステータスと条件を確認してください。

## 参考資料

- [Argo CDとIdentity CenterのSAML連携](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/identity-center/)
- [IAM Identity CenterカスタマーマネージドSAMLアプリケーション](https://docs.aws.amazon.com/singlesignon/latest/userguide/customermanagedapps-saml2-setup.html)
- [IAM Identity Centerの属性mapping](https://docs.aws.amazon.com/singlesignon/latest/userguide/mapawsssoattributestoapp.html)
- [ESO 2.12 AWS認証](https://external-secrets.io/v2.12.0/provider/aws-access/)
- [Helm Provider](https://registry.terraform.io/providers/hashicorp/helm/3.3.0/docs)
- [ProjectsとRBAC](../gitops/argocd/06-projects-rbac.md)
- [この章のクイズ](../quizzes/ops/04-gitops-multi-cluster-quiz.md)

< [前へ：CIパイプライン](03-ci-pipelines.md) | [目次](README.md) | [次へ：GitOpsオートメーション](05-gitops-automation.md) >
