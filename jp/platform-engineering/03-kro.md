# Kube Resource Orchestrator (kro)

> **最終更新**: September 12, 2026 · **ベースライン**: kro 0.9.4

## 概念とスコープ

正式名称は Kube Resource Orchestrator であり、Kubernetes SIG Cloud Provider のサブプロジェクトです。ResourceGraphDefinition (RGD) は、Kubernetes リソース全体の入力スキーマ、関係、およびステータスを定義します。検証とコンパイルの後、kro は生成された CRD のインスタンスを動的に reconcile します。

RGD は API とリソースグラフを定義するものであり、アプリケーションインスタンスではありません。インスタンスの spec は入力を提供し、spec.resources のテンプレートは Deployment や Service などのオブジェクトを作成します。ACK リソースなどの既存の CRD も参加できますが、kro はそれらの controller や AWS IAM 権限を提供しません。

YAML 内の `${...}` 式は CEL を使用します。以前の .parent、.children、childResources、resourceKind、statusMappings、および Go-template の例はこの API ではありません。同じアプリケーション CRD を独自に作成して、RGD と所有権を競合させないでください。

## Helm、Kustomize、Operator との比較

| ツール | 主な役割と境界 |
| --- | --- |
| Helm | Go-template chart をレンダリングし、release 履歴を管理します。v2 chart の依存関係は Chart.yaml で宣言します。 |
| Kustomize | base と patch を使用して manifest を変換します。runtime controller ではありません。 |
| Custom operator | ドメイン固有の recovery、migration、backup をコードで実装できます。 |
| kro | CEL 参照からリソースグラフを推論してインスタンスを reconcile します。データベース recovery アルゴリズムを生成するものではありません。 |

Helm chart は kro をインストールでき、GitOps は RGD とインスタンスを管理できます。これらのツールは連携して使用できます。Helm から kro に移行しても、security、recovery、operations が自動的に向上するわけではありません。Kubernetes Deployment controller も、Helm が元々作成した Deployment を引き続き管理します。

## インストールと権限

公式リポジトリは kubernetes-sigs/kro です。古い kro-run パスはリダイレクトされる場合があります。これは固定された OCI chart の**オフライン検査**です。以前の kro-project download URL や架空の CLI インストールは使用しないでください。この release では別個の CLI binary は配布されません。kubectl と Helm を使用してください。

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

インストール前に、サポート対象の Kubernetes バージョン、admission policy、namespace、既存の CRD/controller を検証してください。以前の 1.31–1.33 の一覧は、現行のサポートとして提示されていません。Helm upgrade は crds/ を自動的に更新しません。別のプロセスで 0.9.4 release と CRD の変更をレビューしてください。

デフォルトの rbac.mode=unrestricted は広範な cluster アクセスを許可します。この例では aggregation mode をレンダリングしますが、これにも CRD、RGD、GraphRevision、ConfigMap の基本権限が含まれます。生成されたアプリケーション API と子リソースの権限を追加してください。この ClusterRole は例のリソースタイプを許可し、cluster 全体へのアクセスを付与できます。信頼された platform administrator が RGD と aggregation label を管理すべきです。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kro:controller:reviewed-nginxapps
  labels:
    rbac.kro.run/aggregate-to-controller: "true"
rules:
  - apiGroups: [platform.example.com]
    resources: [nginxapps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [platform.example.com]
    resources: [nginxapps/status, nginxapps/finalizers]
    verbs: [get, update, patch]
  - apiGroups: [apps]
    resources: [deployments]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [services]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [networking.k8s.io]
    resources: [ingresses]
    verbs: [get, list, watch, create, update, patch, delete]
```

## 完全な NginxApp の例

RGD、インスタンス、および RBAC ファイルは examples/platform/kro にもあります。Ingress はデフォルトで無効です。有効化する前に、承認済みの IngressClass/controller、host DNS、および同じ namespace 内の TLS Secret を準備してください。className=internal という文字列だけでは internal load balancer は設定されません。

image は Helm の例と同じ nginx-unprivileged tag を使用します。non-root UID、read-only root、および /tmp volume が設定されていますが、image の実行はテストされていません。デプロイメント前に digest、architecture、および policy を検証してください。

### ResourceGraphDefinition

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: reviewed-nginxapps
spec:
  schema:
    apiVersion: v1alpha1
    group: platform.example.com
    kind: NginxApp
    scope: Namespaced
    spec:
      replicas: integer | default=2 minimum=1 maximum=5
      image: string | default="nginxinc/nginx-unprivileged:1.30.4-alpine"
      ingress:
        enabled: boolean | default=false
        className: string | default="internal"
        host: string | default="app.example.com"
        tlsSecret: string | default="app-tls"
    status:
      availableReplicas: ${deployment.status.availableReplicas}
      serviceIP: ${service.spec.clusterIP}
  resources:
    - id: deployment
      readyWhen:
        - ${deployment.status.availableReplicas >= deployment.spec.replicas}
        - ${deployment.status.observedGeneration >= deployment.metadata.generation}
      template:
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          replicas: ${schema.spec.replicas}
          selector:
            matchLabels:
              app.kubernetes.io/name: ${schema.metadata.name}
          template:
            metadata:
              labels:
                app.kubernetes.io/name: ${schema.metadata.name}
            spec:
              automountServiceAccountToken: false
              securityContext:
                runAsNonRoot: true
                runAsUser: 101
                runAsGroup: 101
                fsGroup: 101
                seccompProfile:
                  type: RuntimeDefault
              containers:
                - name: web
                  image: ${schema.spec.image}
                  ports:
                    - name: http
                      containerPort: 8080
                  securityContext:
                    allowPrivilegeEscalation: false
                    readOnlyRootFilesystem: true
                    capabilities:
                      drop: [ALL]
                  resources:
                    requests:
                      cpu: 100m
                      memory: 64Mi
                    limits:
                      cpu: 500m
                      memory: 128Mi
                  readinessProbe:
                    httpGet:
                      path: /
                      port: http
                  volumeMounts:
                    - name: tmp
                      mountPath: /tmp
              volumes:
                - name: tmp
                  emptyDir:
                    sizeLimit: 64Mi
    - id: service
      template:
        apiVersion: v1
        kind: Service
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          type: ClusterIP
          selector: ${deployment.spec.selector.matchLabels}
          ports:
            - name: http
              port: 8080
              targetPort: http
    - id: ingress
      includeWhen:
        - ${schema.spec.ingress.enabled}
      template:
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          ingressClassName: ${schema.spec.ingress.className}
          tls:
            - hosts:
                - ${schema.spec.ingress.host}
              secretName: ${schema.spec.ingress.tlsSecret}
          rules:
            - host: ${schema.spec.ingress.host}
              http:
                paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service:
                        name: ${service.metadata.name}
                        port:
                          number: 8080
```

### インスタンス

```yaml
apiVersion: platform.example.com/v1alpha1
kind: NginxApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.4-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

schema.spec 内の SimpleSchema は型、default、および境界を記述します。kro はこれを生成される CRD の OpenAPI schema に変換します。CEL の schema.metadata/spec はインスタンスを参照し、deployment/service はリソース ID を参照します。投影する status は schema.status の下に定義してください。

この例の readyWhen は Deployment 自身の availableReplicas と observedGeneration をチェックします。readiness condition がない場合、存在と解決可能な参照だけで進行するには十分な場合があります。readyWhen は Boolean 値を返し、自身のリソース ID のみを参照する必要があります。アプリケーション SLO とデータベースのチェックは別に維持します。

Service は Deployment selector を参照し、Ingress は Service 名を参照するため、依存関係が作成されます。独立したリソースは wave を共有できます。cycle は拒否されます。includeWhen は条件付きの追加を制御し、条件が変わった場合にリソースを追加または prune できます。既存リソースへの externalRef は、作成または削除の所有権を取得することとは異なります。

### 適用順序と検査

承認済みの cluster では、レビュー済みの RBAC と RGD を適用し、RGD が Active であり、生成された nginxapps.platform.example.com CRD が Established であることを検証してから、インスタンスを適用してください。kubectl apply が成功しても、グラフのコンパイルやアプリの readiness が証明されるわけではありません。

```bash
kubectl get rgd reviewed-nginxapps -o yaml
kubectl get graphrevisions \
  -l internal.kro.run/resource-graph-definition-name=reviewed-nginxapps
kubectl get crd nginxapps.platform.example.com -o yaml
kubectl get nginxapps.platform.example.com reviewed-web -n example -o yaml
kubectl get deployments,services,ingresses -n example \
  -l app.kubernetes.io/name=reviewed-web
```

## GraphRevision と変更

バージョン 0.9.4 では、RGD spec が変更されたときに immutable な GraphRevision を記録してコンパイルします。最新 revision が失敗しても、以前の revision に自動的に fallback されません。インスタンスの進行が停止する可能性があります。GraphAccepted、GraphVerified、GraphRevisionsResolved、および error message を検査してから、有効な spec を適用してください。

GraphRevision は internal.kro.run API です。安定した外部 tooling contract を前提とせず、検査と診断に使用してください。Git spec を戻しても、新しい revision での検証が必要であり、データベースデータや外部への影響を transaction 的に rollback するものではありません。

group、kind、apiVersion、および scope は RGD 内では immutable です。互換性のある schema 進化と新しい API への migration を区別し、既存のインスタンスと保存済みデータをレビューしてください。conversion webhook が自動的に生成されると想定しないでください。

## 削除と所有権

インスタンスが削除されると、kro は ApplySet inventory と deletion wave を使用して依存先を先に削除し、管理対象リソースが消えるまで finalizer を保持します。子の finalizer は後続の wave をブロックする可能性があります。外部参照は read-only であり、kro が削除することはありません。

すべての子が直ちに garbage collection されると言うのは不正確です。ResourcesReady=Unknown/UnderDeletion、inventory、および子の finalizer を検査してください。controller を削除する前に、インスタンス、RGD、CRD、およびデータの cleanup と保持を計画してください。CRD の削除はインスタンスデータにも影響します。

## Migration と運用

Helm と kro が同じオブジェクトを競合して管理しないよう、名前、selector、所有権、field manager、および GitOps controller をレビューしてください。検証済みの新しい名前のグラフと traffic cutover、またはレビュー済みの ownership transfer プロセスを選択してください。StatefulSet、PVC、またはデータベースを所有する release を安易に uninstall して migration しないでください。

環境間で同じ API contract とレビュー済みの image digest を使用し、namespace、replica、ingress、および policy には個別のインスタンスを使用してください。ApplicationSet などの fleet tool では、各対象 cluster に kro、RGD、および権限が必要です。kro は任意の remote cluster に自動接続しません。

stateful application には、引き続き database-operator または managed-service による backup、restore、failover、および migration の振る舞いが必要です。リソースの reconciliation だけではデータ recovery になりません。グラフサイズと権限を制限し、再利用可能な単位を定義し、有用な status のみを公開してください。Secret の内容を status、label、または log にコピーしないでください。

## 検証と参照

各言語の元の 504 行の guide と 423 行の quiz をレビューしました。これには言語ごとに 16 個の固有の code block と 20 の question topic が含まれます。公式の kro 0.9.4 chart は aggregation mode でレンダリングされ、RGD 構造がチェックされました。その cel-go 0.31.0 dependency は、公開された 14 個の固有の式をコンパイルして評価しました。4 つの synthetic case は ingress のオン/オフ、不足した replica、および古い observedGeneration を対象にしました。

これらは動的な synthetic input を使用した CEL check であり、完全な kro graph compiler、Kubernetes API discovery、生成 CRD の admission、または実行中の controller による検証ではありません。Container、Ingress/TLS、データベース、および cluster resource は実行されていません。

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [バージョン付き API とソース](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [RGD schema](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [アクセス制御](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [Graph revision](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [インスタンス削除](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[kro クイズ](../quizzes/platform-engineering/03-kro-quiz.md)
