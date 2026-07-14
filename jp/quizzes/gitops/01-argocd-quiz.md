# ArgoCD クイズ

このクイズでは、ArgoCD と GitOps の理解度を確認します。

## 質問 1: GitOps のコア原則

<details>
<summary>GitOps の 4 つのコア原則は何ですか？</summary>

**回答:**
1. **宣言的設定**: システムの望ましい状態をコードとして定義する
2. **バージョン管理**: すべての変更を Git で追跡する
3. **自動同期**: リポジトリと実行環境の差異を自動的に調整する
4. **自己修復**: システムを望ましい状態に自動的に復旧する

これらの原則により、GitOps は単なるデプロイツールを超えた完全な運用モデルとして機能します。
</details>

## 質問 2: ArgoCD アーキテクチャ

<details>
<summary>ArgoCD の主要コンポーネントとその役割は何ですか？</summary>

**回答:**
- **API Server**: REST API と web UI を提供し、認証と認可を処理する
- **Repository Server**: Git リポジトリに接続し、マニフェストを生成する
- **Application Controller**: アプリケーションの状態を監視し、同期を実行する
- **Redis**: キャッシュとセッションストレージ
- **Dex**: OIDC 認証サーバー（オプション）

各コンポーネントは個別にスケールでき、高可用性構成をサポートします。
</details>

## 質問 3: Application リソース

<details>
<summary>ArgoCD Application リソースに必要なコンポーネントは何ですか？</summary>

**回答:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/example/app-config
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

**必須要素:**
- `source`: Git リポジトリ情報
- `destination`: デプロイ先のターゲットクラスターと namespace
- `project`: ArgoCD プロジェクト（権限管理用）
</details>

## 質問 4: Sync ポリシー

<details>
<summary>ArgoCD の自動 Sync と手動 Sync の違いは何ですか？</summary>

**回答:**
**自動 Sync:**
```yaml
syncPolicy:
  automated:
    prune: true      # Automatically delete unnecessary resources
    selfHeal: true   # Automatically recover from drift
```
- Git が変更されると自動的にクラスターへ適用される
- drift が検出されると自動的に復旧する
- 本番環境では慎重に使用する

**手動 Sync:**
- ユーザーが明示的に同期をトリガーする
- 変更をレビューした後に適用する
- より安全だが、運用上のオーバーヘッドが増える
</details>

## 質問 5: ApplicationSet

<details>
<summary>ArgoCD ApplicationSet の目的と主な generator タイプは何ですか？</summary>

**回答:**
**目的:**
- マルチクラスターのデプロイを自動化する
- テンプレートベースの Application 作成
- 環境固有の設定管理

**主な Generator:**
- **List Generator**: 静的な値のリストに基づく
- **Cluster Generator**: 登録済みクラスターに基づく
- **Git Generator**: Git リポジトリ構造に基づく
- **Matrix Generator**: 複数の generator を組み合わせる
- **Pull Request Generator**: PR ベースの一時環境

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-apps
spec:
  generators:
  - clusters: {}
  template:
    metadata:
      name: '{{name}}-app'
    spec:
      source:
        repoURL: https://github.com/example/apps
        path: '{{name}}'
      destination:
        server: '{{server}}'
```
</details>

## 質問 6: セキュリティのベストプラクティス

<details>
<summary>ArgoCD のセキュリティを強化する主な方法は何ですか？</summary>

**回答:**
1. **RBAC 設定**:
   ```yaml
   policy.default: role:readonly
   policy.csv: |
     p, role:admin, applications, *, */*, allow
     p, role:dev, applications, get, dev/*, allow
     g, dev-team, role:dev
   ```

2. **SSO 統合**:
   - OIDC、SAML、LDAP 統合
   - 一元的な認証管理

3. **ネットワークセキュリティ**:
   - Ingress TLS 設定
   - Network policy の適用
   - プライベート Git リポジトリを使用する

4. **Secret 管理**:
   - External Secrets Operator を使用する
   - Sealed Secrets または Helm Secrets
   - 機密情報用に Git リポジトリを分離する

5. **監査ログ**:
   - すべての変更を追跡する
   - アクセスログを監視する
</details>

## 質問 7: マルチクラスター管理

<details>
<summary>ArgoCD で複数のクラスターをどのように管理しますか？</summary>

**回答:**
1. **クラスター登録**:
   ```bash
   argocd cluster add my-cluster-context
   ```

2. **クラスターごとの Application デプロイ**:
   ```yaml
   destination:
     server: https://my-cluster-api-server
     namespace: production
   ```

3. **ApplicationSet による自動化**:
   ```yaml
   generators:
   - clusters:
       selector:
         matchLabels:
           environment: production
   ```

4. **クラスター権限管理**:
   - クラスターごとに service account を設定する
   - 最小権限の原則を適用する
   - Namespace ベースの分離

5. **監視とアラート**:
   - クラスターごとのステータスダッシュボード
   - Sync 失敗アラート
   - リソース使用状況の監視
</details>

## 質問 8: トラブルシューティング

<details>
<summary>ArgoCD アプリケーションが「OutOfSync」状態の場合、何を確認すべきですか？</summary>

**回答:**
1. **Git リポジトリのステータスを確認する**:
   ```bash
   # Check repository access permissions
   argocd repo list
   argocd repo get <repo-url>
   ```

2. **マニフェストを検証する**:
   ```bash
   # Validate manifests locally
   kubectl apply --dry-run=client -f manifests/
   ```

3. **Sync ポリシーを確認する**:
   - Auto sync の設定
   - Prune と SelfHeal のオプション
   - Sync 条件（Sync Windows）

4. **リソースのステータスを分析する**:
   ```bash
   # Check application details
   argocd app get <app-name>
   argocd app diff <app-name>
   ```

5. **ログを確認する**:
   ```bash
   # ArgoCD controller logs
   kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
   ```

6. **手動 Sync を試す**:
   ```bash
   argocd app sync <app-name> --prune
   ```
</details>

## 質問 9: 最新の GitOps トレンド

<details>
<summary>2023 年の GitOps 分野における主要なトレンドは何ですか？</summary>

**回答:**
1. **マルチクラスター GitOps**:
   - ApplicationSet によるマルチクラスターのデプロイ自動化
   - クラスター間の設定 Sync とポリシー適用

2. **ハイブリッドおよびマルチクラウド GitOps**:
   - オンプレミスとクラウド環境にわたる一貫したデプロイ戦略
   - さまざまなクラウドプロバイダー間での Workload ポータビリティ

3. **GitOps とポリシー管理の統合**:
   - OPA（Open Policy Agent）と Kyverno の統合
   - コンプライアンスとガバナンスの自動化
   - セキュリティポリシーのコード化とバージョン管理

4. **Progressive Delivery**:
   - Canary および Blue-Green デプロイの自動化
   - Argo Rollouts との統合
   - メトリクスベースの自動ロールバック
</details>

## 質問 10: Amazon EKS 統合

<details>
<summary>ArgoCD を Amazon EKS と統合する際の考慮事項は何ですか？</summary>

**回答:**
1. **IAM 権限の設定**:
   ```yaml
   # IRSA (IAM Roles for Service Accounts) configuration
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/argocd-role
   ```

2. **ALB Ingress 設定**:
   ```yaml
   annotations:
     kubernetes.io/ingress.class: alb
     alb.ingress.kubernetes.io/scheme: internet-facing
     alb.ingress.kubernetes.io/target-type: ip
   ```

3. **EKS クラスター登録**:
   ```bash
   # Register EKS cluster to ArgoCD
   argocd cluster add arn:aws:eks:region:account:cluster/cluster-name
   ```

4. **ECR 統合**:
   - ECR イメージの自動更新
   - Image Updater の設定

5. **AWS Load Balancer Controller**:
   - Service ロードバランシングの最適化
   - Target Group Binding の活用

6. **セキュリティに関する考慮事項**:
   - VPC エンドポイントを使用する
   - Security group の設定
   - Network policy の適用
</details>

---

**スコア:**
- 8-10 問正解: 優秀（ArgoCD エキスパートレベル）
- 6-7 問正解: 良好（追加学習を推奨）
- 4-5 問正解: 平均（基本概念の見直しが必要）
- 0-3 問正解: 不十分（内容全体の再学習が必要）
