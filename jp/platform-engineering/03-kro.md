# Kubernetes Resource Operator (KRO)

> **サポート対象バージョン**: Kubernetes 1.31, 1.32, 1.33
> **最終更新**: February 21, 2026

## 概要

Kubernetes Resource Operator (KRO) は、Kubernetes リソース間の関係を宣言的に定義して管理するためのフレームワークです。従来の Helm チャートの制約を超えて、KRO は ResourceGraphDefinition (RGD) を通じてリソースグラフをモデル化し、複雑なアプリケーションを単一の Custom Resource としてデプロイできるようにします。

## KRO のコアコンセプト

### Kubernetes Resource Operator とは？

Kubernetes Resource Operator (KRO) は、Kubernetes リソース間の関係を宣言的に定義して管理するためのフレームワークです。KRO は次のコアコンセプトに基づいています。

1. **宣言的なリソース関係**: リソース間の関係を明示的に定義することで、複雑なアプリケーション構造を表現します。
2. **状態ベースの Reconciliation**: 望ましい状態と実際の状態の差分を継続的に調整します。
3. **Resource Graph**: リソース間の依存関係と関係性をグラフ形式でモデル化します。
4. **自動ライフサイクル管理**: リソースの作成、更新、削除を自動的に処理します。

### ResourceGraphDefinition (RGD)

ResourceGraphDefinition (RGD) は、Custom Resource とそれに依存する Kubernetes ネイティブリソースの関係を定義する KRO のコアコンポーネントです。RGD は次の機能を提供します。

1. **親子関係の定義**: 親リソースと子リソースの間の階層構造を定義します。
2. **テンプレートベースのリソース作成**: 親リソースのプロパティに基づいて子リソースを動的に作成します。
3. **状態の伝播**: アプリケーション全体の状態を把握するために、子リソースの状態を親リソースへ伝播します。
4. **依存関係管理**: 正しい作成および更新順序を保証するために、子リソース間の依存関係を定義します。

### KRO と従来のアプローチの比較

KRO には、従来の Kubernetes リソース管理アプローチと比較して、次のような差別化要素があります。

| 機能 | KRO | Helm | Operator SDK | Kustomize |
|---------|-----|------|--------------|-----------|
| **リソース関係のモデリング** | 明示的なグラフ | 暗黙的 | コードベース | なし |
| **状態の伝播** | 自動 | 手動 | コードベース | なし |
| **依存関係管理** | 宣言的 | 暗黙的 | コードベース | なし |
| **拡張性** | 高 | 中 | 高 | 低 |
| **学習曲線** | 中 | 低 | 高 | 低 |
| **GitOps との親和性** | 高 | 中 | 中 | 高 |

### KRO アーキテクチャ

KRO は次のコンポーネントで構成されます。

1. **KRO Controller**: ResourceGraphDefinitions を監視し、リソースグラフを管理します。
2. **Resource Graph Engine**: リソース間の関係と依存関係を処理します。
3. **State Manager**: リソースの状態を追跡し、伝播します。
4. **Reconciliation Loop**: 望ましい状態と実際の状態の差分を調整します。

```
+-------------------+     +-------------------+     +-------------------+
|  Custom Resource  |     | ResourceGraph     |     | Kubernetes        |
|  (CR)             |<--->| Definition        |<--->| Native Resources  |
+-------------------+     +-------------------+     +-------------------+
         ^                        ^                         ^
         |                        |                         |
         v                        v                         v
+-----------------------------------------------------------------------+
|                          KRO Controller                                |
|                                                                       |
|  +----------------+  +----------------+  +----------------+           |
|  | Resource Graph |  | State Manager  |  | Reconciliation |           |
|  |     Engine     |  |                |  |     Loop       |           |
|  +----------------+  +----------------+  +----------------+           |
+-----------------------------------------------------------------------+
```

## KRO の起源と進化

### Kubernetes リソース管理における課題

Kubernetes アプリケーションの複雑さが増すにつれて、リソース管理アプローチも進化してきました。

1. **直接的な kubectl 管理**: 個別の YAML ファイルを手動で適用します — リソース間の関係や順序の管理が困難です
2. **Helm**: テンプレートベースのパッケージ化によりデプロイを簡素化しますが、Go テンプレートの複雑さとリリース状態管理に制約があります
3. **Operator SDK**: 完全な Custom Controller 開発が可能ですが、Go プログラミング知識と高い開発・保守コストが必要です
4. **KRO**: 宣言的な ResourceGraphDefinition により、コーディングなしでリソースグラフを定義します — Operator の力と Helm のシンプルさを組み合わせます

### KRO が解決する課題

| 既存の制約 | KRO の解決策 |
|---------------------|----------------|
| Helm テンプレートの複雑さ | 純粋な YAML + リソース参照構文 |
| Operator 開発コスト | RGD 宣言により CRD + controller を自動生成 |
| リソース間の状態伝播がない | statusMappings による子→親の自動状態伝播 |
| 手動の依存関係順序付け | リソースグラフ内での自動依存関係解決 |

## ラボ環境のセットアップ

このドキュメントの例を実行するには、次のツールと環境が必要です。

### 必要なツール
- kubectl v1.31 以上
- Helm v3.10 以上
- kro CLI v0.5.0 以上
- 動作する Kubernetes cluster (EKS、minikube、kind など)

### KRO のインストール

```bash
# Install KRO controller
kubectl apply -f https://github.com/kro-project/kro/releases/download/v0.5.0/kro-controller.yaml

# Install KRO CLI
curl -L https://github.com/kro-project/kro/releases/download/v0.5.0/kro-cli-$(uname -s)-$(uname -m) -o kro
chmod +x kro
sudo mv kro /usr/local/bin/

# Verify installation
kubectl get pods -n kro-system
```

## Helm と KRO の比較

### Helm

Helm は、Kubernetes アプリケーションをパッケージ化してデプロイするために広く使われているツールです。Helm には次の特徴があります。

- **テンプレートベース**: Go テンプレート言語を使用して Kubernetes manifests を生成します
- **Chart の概念**: アプリケーションをパッケージ化する単位です
- **リリース管理**: デプロイ済みアプリケーションのバージョン管理です
- **中央リポジトリ**: charts を共有・再利用するためのリポジトリです

### Kubernetes Resource Operator (KRO)

KRO は、Kubernetes Custom Resource を使用してアプリケーションを管理するアプローチです。

- **宣言的 API**: Kubernetes ネイティブなリソース定義です
- **状態ベース**: 望ましい状態を宣言し、controller が実際の状態を調整します
- **GitOps Friendly**: バージョン管理システムと容易に統合できます
- **拡張性**: Custom Resource Definitions (CRDs) による拡張です

### 比較表

| 機能 | Helm | KRO |
|---------|------|-----|
| **パッケージ化方式** | Chart (tgz アーカイブ) | Custom Resource |
| **テンプレートエンジン** | Go templates | なし (純粋な YAML) |
| **バージョン管理** | リリース履歴 | Git ベース |
| **ロールバック機構** | helm rollback | GitOps ベースのロールバック |
| **依存関係管理** | requirements.yaml | ResourceGraphDefinition |
| **カスタマイズ** | values.yaml | CR spec |
| **インストール方法** | helm install | kubectl apply |
| **アップグレード方法** | helm upgrade | kubectl apply |
| **削除方法** | helm uninstall | kubectl delete |
| **Hooks** | install/upgrade/delete hooks | Kubernetes イベントベース |

## Helm から KRO へ移行する理由

1. **Kubernetes ネイティブなアプローチ**: KRO は Kubernetes の宣言的 API モデルに従い、より一貫した体験を提供します
2. **改善されたバージョン管理**: 各リソースの変更を個別に追跡できます
3. **きめ細かな制御**: 個々のリソースレベルでより詳細に制御できます
4. **簡素化された依存関係管理**: 明示的な依存関係宣言により、複雑な関係管理が容易になります
5. **強化されたセキュリティ**: 最小権限の原則に従い、必要な権限だけを付与できます
6. **改善された状態管理**: リソースの状態を自動的に伝播および集約します
7. **GitOps ワークフロー統合**: 宣言的なアプローチにより GitOps ツールと容易に統合できます

## 実践例: Nginx Helm Chart から KRO への移行

### 既存の Helm Chart (values.yaml)

```yaml
# Nginx Helm chart values.yaml
replicaCount: 2

image:
  repository: nginx
  tag: 1.21.0
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  hosts:
    - host: example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
```

### KRO Custom Resource Definition

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: nginxapps.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: NginxApp
    listKind: NginxAppList
    plural: nginxapps
    singular: nginxapp
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                replicas:
                  type: integer
                  default: 1
                image:
                  type: object
                  properties:
                    repository:
                      type: string
                    tag:
                      type: string
                    pullPolicy:
                      type: string
                      enum: [Always, IfNotPresent, Never]
                service:
                  type: object
                  properties:
                    type:
                      type: string
                      enum: [ClusterIP, NodePort, LoadBalancer]
                    port:
                      type: integer
                ingress:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                    hosts:
                      type: array
                      items:
                        type: object
                        properties:
                          host:
                            type: string
                          paths:
                            type: array
                            items:
                              type: object
                              properties:
                                path:
                                  type: string
                                pathType:
                                  type: string
                resources:
                  type: object
                  properties:
                    limits:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
                    requests:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
```

### ResourceGraphDefinition の作成

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: nginxapp-graph
spec:
  resourceKind:
    group: kro.example.com
    kind: NginxApp
    version: v1
  childResources:
    - apiVersion: apps/v1
      kind: Deployment
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          replicas: {{.parent.spec.replicas}}
          selector:
            matchLabels:
              app: {{.parent.metadata.name}}
          template:
            metadata:
              labels:
                app: {{.parent.metadata.name}}
            spec:
              containers:
              - name: nginx
                image: {{.parent.spec.image.repository}}:{{.parent.spec.image.tag}}
                imagePullPolicy: {{.parent.spec.image.pullPolicy}}
                ports:
                - containerPort: {{.parent.spec.service.port}}
                resources:
                  {{- if .parent.spec.resources }}
                  limits:
                    {{- if .parent.spec.resources.limits.cpu }}
                    cpu: {{.parent.spec.resources.limits.cpu}}
                    {{- end }}
                    {{- if .parent.spec.resources.limits.memory }}
                    memory: {{.parent.spec.resources.limits.memory}}
                    {{- end }}
                  requests:
                    {{- if .parent.spec.resources.requests.cpu }}
                    cpu: {{.parent.spec.resources.requests.cpu}}
                    {{- end }}
                    {{- if .parent.spec.resources.requests.memory }}
                    memory: {{.parent.spec.resources.requests.memory}}
                    {{- end }}
                  {{- end }}

    - apiVersion: v1
      kind: Service
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          selector:
            app: {{.parent.metadata.name}}
          ports:
          - port: {{.parent.spec.service.port}}
            targetPort: {{.parent.spec.service.port}}
          type: {{.parent.spec.service.type}}

    - apiVersion: networking.k8s.io/v1
      kind: Ingress
      nameTemplate: "{{.parent.metadata.name}}"
      condition: "{{.parent.spec.ingress.enabled}}"
      template: |
        spec:
          rules:
          {{- range .parent.spec.ingress.hosts }}
          - host: {{.host}}
            http:
              paths:
              {{- range .paths }}
              - path: {{.path}}
                pathType: {{.pathType}}
                backend:
                  service:
                    name: {{$.parent.metadata.name}}
                    port:
                      number: {{$.parent.spec.service.port}}
              {{- end }}
          {{- end }}

  statusMappings:
    - childResource:
        kind: Deployment
        name: "{{.parent.metadata.name}}"
      conditions:
        - type: Available
          mapping:
            type: Ready
      fieldMappings:
        - child: "status.availableReplicas"
          parent: "status.availableReplicas"
        - child: "status.readyReplicas"
          parent: "status.readyReplicas"

    - childResource:
        kind: Service
        name: "{{.parent.metadata.name}}"
      fieldMappings:
        - child: "spec.clusterIP"
          parent: "status.serviceIP"
```

### KRO Custom Resource インスタンス

```yaml
apiVersion: kro.example.com/v1
kind: NginxApp
metadata:
  name: my-nginx
spec:
  replicas: 2
  image:
    repository: nginx
    tag: 1.21.0
    pullPolicy: IfNotPresent
  service:
    type: ClusterIP
    port: 80
  ingress:
    enabled: true
    hosts:
      - host: example.com
        paths:
          - path: /
            pathType: Prefix
  resources:
    limits:
      cpu: 100m
      memory: 128Mi
    requests:
      cpu: 50m
      memory: 64Mi
```

### デプロイと検証

```bash
# Apply CRD and RGD
kubectl apply -f nginxapp-crd.yaml
kubectl apply -f nginxapp-rgd.yaml

# Apply custom resource instance
kubectl apply -f my-nginx.yaml

# Verify created resources
kubectl get deployments,services,ingress -l app=my-nginx

# Check custom resource status
kubectl get nginxapp my-nginx -o yaml
```

## KRO のユースケース

### 1. Microservices アプリケーション管理

KRO は、複数のコンポーネントで構成される Microservices アプリケーションの管理に最適です。各 Microservice は次のリソースで構成できます。

- Deployment or StatefulSet
- Service
- ConfigMap
- Secret
- HorizontalPodAutoscaler
- PodDisruptionBudget

KRO を使用すると、これらのリソース間の関係を明示的に定義し、単一の Custom Resource を通じて Microservice 全体を管理できます。

### 2. Database Cluster 管理

Database cluster (例: PostgreSQL、MySQL) には、複数のコンポーネントと複雑な設定が必要です。KRO は次のリソースを管理できます。

- Master and replica StatefulSets
- Service endpoints
- Persistent volume claims
- Backup and restore jobs
- Monitoring configuration

### 3. Multi-Cluster アプリケーションデプロイ

KRO は、複数の Kubernetes clusters にまたがるアプリケーションの管理にも使用できます。これにより、次のようなシナリオがサポートされます。

- リージョン別デプロイ
- 開発、ステージング、本番環境にわたる一貫したデプロイ
- ハイブリッドクラウド環境でのアプリケーション管理

## KRO のベストプラクティス

### 1. Resource Graph 設計

- **単一責任の原則**: 各 Custom Resource は明確な単一の責任を持つべきです。
- **適切な抽象化レベル**: 詳細すぎず抽象的すぎない、適切な抽象化レベルを選択します。
- **明確な境界**: リソース間の境界と責任を明確に定義します。
- **再利用性**: 共通パターンを特定し、再利用可能なコンポーネントとして抽出します。

### 2. 状態管理

- **意味のある状態**: ユーザーに意味のある状態情報を提供します。
- **状態の集約**: 複数の子リソースからの状態を適切に集約します。
- **Condition 定義**: 明確な condition タイプとステータスを定義します。
- **診断情報**: トラブルシューティングに役立つ診断情報を含めます。

### 3. バージョン管理

- **API バージョン管理**: Custom Resource API バージョンを適切に管理します。
- **Conversion Webhooks**: バージョン変換用の webhooks を実装します。
- **後方互換性**: 可能な限り後方互換性を維持します。
- **段階的な移行**: 大きな変更は段階的に導入します。

### 4. セキュリティ

- **最小権限**: controllers には必要最小限の権限だけを付与します。
- **RBAC Policies**: アクセスを制御するために適切な RBAC policies を定義します。
- **Secret 管理**: 機密情報を Secrets として管理します。
- **Validation Webhooks**: 入力検証用の webhooks を実装します。

## まとめ

Helm から KRO への移行は、Kubernetes ネイティブなアプローチへ移行するための重要なステップです。これにより、より宣言的で拡張性が高く、GitOps と親和性の高いアプリケーション管理が可能になります。特に複雑なアプリケーションでは、KRO はよりきめ細かな制御と改善されたバージョン管理を提供します。

ResourceGraphDefinition (RGD) は KRO のコアコンセプトであり、リソース間の関係を明示的に定義し、状態を伝播するメカニズムを提供します。これにより、複雑なアプリケーション構造をより容易にモデル化して管理できます。

移行プロセスには初期作業が追加で必要ですが、長期的な保守と運用の観点で大きなメリットがあります。段階的な移行アプローチにより、KRO のメリットを活用しながらリスクを最小化できます。

KRO はまだ進化中の技術ですが、Kubernetes エコシステムの将来の方向性を示す重要なアプローチです。宣言的 API、リソース関係のモデリング、状態伝播といったコンセプトは、クラウドネイティブアプリケーション管理の中核原則になりつつあります。

## クイズ

この章で学んだ内容を確認するには、[KRO クイズ](../quizzes/platform-engineering/03-kro-quiz.md) に挑戦してください。
