# Kube Resource Orchestrator (kro)

> **最終更新日**: 2026年9月12日 · **基準バージョン**: kro 0.9.4

## 概念と適用範囲

正式名称は Kube Resource Orchestrator で、Kubernetes SIG Cloud Provider のサブプロジェクトです。ResourceGraphDefinition（RGD）は、Kubernetes リソース間の入力スキーマ、関係、ステータスを定義します。検証とコンパイルの後、kro は生成された CRD のインスタンスを動的に調整します。

RGD が定義するのは API とリソースグラフであり、アプリケーションのインスタンスではありません。インスタンスの `spec` が入力を渡し、`spec.resources` のテンプレートが Deployment や Service などのオブジェクトを作成します。ACK リソースなど既存の CRD もグラフに含められますが、kro がそれらの controller や AWS IAM 権限を提供するわけではありません。

YAML 内の `${...}` 式では CEL を使います。以前の `.parent`、`.children`、`childResources`、`resourceKind`、`statusMappings`、Go template の例は、現在の API ではありません。同じアプリケーション CRD を別途作成すると、RGD と所有権が競合するため避けてください。

## Helm、Kustomize、Operator との比較

| ツール | 主な役割と適用範囲 |
| --- | --- |
| Helm | Go template の chart をレンダリングし、release 履歴を管理します。chart v2 の依存関係は `Chart.yaml` で宣言します。 |
| Kustomize | base と patch で manifest を変換します。実行時に調整を行う controller ではありません。 |
| 独自 operator | ドメイン固有の復旧、移行、バックアップをコードで実装できます。 |
| kro | CEL の参照からリソースグラフを推論し、インスタンスを調整します。データベース復旧のアルゴリズムを生成するものではありません。 |

Helm chart で kro をインストールし、GitOps で RGD とインスタンスを管理できます。これらのツールは併用できます。Helm から kro に移行しても、セキュリティ、復旧、運用が自動的に改善されるわけではありません。また、Helm が作成した Deployment も、引き続き Kubernetes の Deployment controller が管理します。

## インストールと権限

公式リポジトリは `kubernetes-sigs/kro` です。古い `kro-run` のパスはリダイレクトされる場合があります。ここで示すのは、バージョンを固定した OCI chart の**オフラインでの確認**です。以前の `kro-project` のダウンロード URL や、実在しない CLI のインストール手順は使わないでください。このリリースでは独立した CLI バイナリは配布されていません。`kubectl` と Helm を使います。

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

インストール前に、サポート対象の Kubernetes バージョン、admission policy、namespace、既存の CRD と controller を確認してください。以前記載されていた 1.31～1.33 は、現在のサポート対象バージョンとして示していません。Helm upgrade では `crds/` は自動更新されません。別途、kro 0.9.4 のリリース内容と CRD の変更を確認してください。

デフォルトの `rbac.mode=unrestricted` は、広範なクラスタアクセスを許可します。この例では aggregation mode をレンダリングしますが、そこにも CRD、RGD、GraphRevision、ConfigMap に対する基本権限が含まれます。生成されるアプリケーション API と子リソースへの権限を追加してください。この ClusterRole は例に使うリソース種別を許可し、クラスタ全体にアクセスできる場合があります。信頼されたプラットフォーム管理者が RGD と aggregation label を管理する必要があります。

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

## NginxApp の全体例

RGD、インスタンス、RBAC のファイルは `examples/platform/kro` にもあります。Ingress はデフォルトで無効です。有効にする前に、承認済みの IngressClass/controller、host DNS、および同じ namespace にある TLS Secret を準備してください。`className=internal` という文字列を指定しただけでは、internal load balancer は構成されません。

この image には Helm の例と同じ `nginx-unprivileged` tag を使います。non-root UID、read-only root filesystem、`/tmp` volume を設定していますが、image を実行して検証したわけではありません。デプロイ前に digest、architecture、policy を確認してください。

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
      image: string | default="nginxinc/nginx-unprivileged:1.30.6-alpine"
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
  image: nginxinc/nginx-unprivileged:1.30.6-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

`schema.spec` の SimpleSchema は、型、デフォルト値、制約範囲を記述します。kro はこれを生成する CRD の OpenAPI schema に変換します。CEL の `schema.metadata/spec` はインスタンスを参照し、`deployment/service` はリソース ID を参照します。公開する status は `schema.status` の下に定義してください。

この例の `readyWhen` は Deployment 自身の `availableReplicas` と `observedGeneration` を確認します。readiness condition がなければ、リソースの存在と参照の解決だけで処理が進むことがあります。`readyWhen` は Boolean を返し、その条件を定義するリソース自身の ID だけを参照する必要があります。アプリケーション SLO とデータベースの確認は別途行ってください。

Service は Deployment の selector を参照し、Ingress は Service 名を参照するため、依存関係が作られます。依存関係のないリソースは同じ wave で処理できますが、循環依存は拒否されます。`includeWhen` は条件に応じたリソースの追加を制御し、条件が変われば追加または削除できます。既存リソースへの `externalRef` は、リソースを作成・削除する所有権を得ることとは異なります。

### 適用順序と確認

承認済みのクラスタでは、レビュー済みの RBAC と RGD を適用します。RGD が Active であり、生成された `nginxapps.platform.example.com` CRD が Established であることを確認してから、インスタンスを適用してください。`kubectl apply` が成功しても、グラフのコンパイルやアプリケーションの readiness が確認できたことにはなりません。

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

バージョン 0.9.4 では、RGD の `spec` が変更されると、不変の GraphRevision を記録してコンパイルします。最新の revision が失敗しても、以前の revision には自動で戻りません。その結果、インスタンスの処理が停止することがあります。GraphAccepted、GraphVerified、GraphRevisionsResolved の状態とエラーメッセージを確認し、有効な `spec` を適用してください。

GraphRevision は `internal.kro.run` API です。安定した外部向けツールの契約があると想定せず、確認と診断に使ってください。Git 上の `spec` を元に戻しても、新しい revision での検証が必要です。また、データベースのデータや外部への副作用がトランザクションとしてロールバックされるわけではありません。

`group`、`kind`、`apiVersion`、`scope` は RGD 内で変更できません。互換性を保った schema の進化と、新しい API への移行を区別し、既存インスタンスと保存データを確認してください。conversion webhook が自動生成されるとは限りません。

## 削除と所有権

インスタンスを削除すると、kro は ApplySet inventory と deletion wave を使い、依存している子リソースを先に削除します。管理対象リソースがなくなるまで finalizer は保持されます。子リソースの finalizer によって、後続の wave が止まる場合があります。外部参照は読み取り専用で、kro によって削除されません。

子リソースがすべて直ちに garbage collection されるという説明は正確ではありません。`ResourcesReady=Unknown/UnderDeletion` の状態、inventory、子リソースの finalizer を確認してください。controller を削除する前に、インスタンス、RGD、CRD、データの削除と保持の計画を立ててください。CRD を削除すると、そのインスタンスデータにも影響します。

## 移行と運用

Helm と kro が同じオブジェクトを取り合わないよう、名前、selector、所有権、field manager、GitOps controller を確認してください。検証済みの新しい名前を使うグラフへ移行して traffic を切り替えるか、レビュー済みの所有権移管手順を選んでください。StatefulSet、PVC、データベースを所有する release を安易に uninstall して移行しないでください。

環境間で同じ API contract とレビュー済みの image digest を使い、namespace、replica、Ingress、policy ごとに個別のインスタンスを用意してください。ApplicationSet などの fleet tool を使う場合は、対象となる各クラスタに kro、RGD、必要な権限が要ります。kro が任意のリモートクラスタへ自動接続することはありません。

stateful application では、database operator または managed service によるバックアップ、復元、フェイルオーバー、移行の仕組みも必要です。リソースを調整するだけではデータは復旧しません。グラフの規模と権限を制限し、再利用できる単位を定義して、必要な status だけを公開してください。Secret の内容を status、label、log にコピーしないでください。

## 検証と参考資料

各言語のガイド（元は 504 行）とクイズ（元は 423 行）をレビューしました。これには、各言語で 16 個の異なる code block と 20 個の設問トピックが含まれます。公式 kro 0.9.4 chart は aggregation mode でレンダリングし、RGD の構造を確認しました。依存関係の cel-go 0.31.0 で、公開されている 14 個の異なる式をコンパイルして評価しました。4 つの合成ケースでは、Ingress の有効・無効、replica 不足、古い `observedGeneration` を確認しました。

これらは動的な合成入力を使った CEL の確認です。完全な kro graph compiler、Kubernetes API discovery、生成 CRD の admission、実行中の controller による検証ではありません。container、Ingress/TLS、データベース、クラスタリソースは実行していません。

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [バージョン固定の API とソース](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [RGD schema](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [アクセス制御](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [グラフ revision](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [インスタンスの削除](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[kro クイズ](../quizzes/platform-engineering/03-kro-quiz.md)
