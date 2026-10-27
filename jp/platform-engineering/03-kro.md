# Kube Resource Orchestrator (kro)

> **最終更新日**: 2026年10月23日 · **ベースライン**: kro 0.9.4

## 概念と対象範囲

正式名称は Kube Resource Orchestrator で、Kubernetes SIG Cloud Provider のサブプロジェクトです。ResourceGraphDefinition (RGD) は、Kubernetes リソース間の入力スキーマ、関係性、ステータスを定義します。検証とコンパイルの後、kro は生成された CRD のインスタンスを動的に調整します。

RGD は API とリソースグラフを定義するものであり、アプリケーションのインスタンスではありません。インスタンスの spec で入力を指定し、spec.resources のテンプレートで Deployment や Service などのオブジェクトを作成します。ACK リソースなどの既存 CRD も参加できますが、kro はそれらのコントローラーや AWS IAM 権限を提供しません。

YAML 内の `${...}` 式では CEL を使用します。以前の .parent、.children、childResources、resourceKind、statusMappings、Go テンプレートの例は、この API ではありません。同じアプリケーション CRD を独自に作成し、RGD と所有権を競合させないでください。

## Helm、Kustomize、Operator との比較

| ツール | 主な役割と境界 |
| --- | --- |
| Helm | Go テンプレートの Chart をレンダリングし、リリース履歴を管理します。v2 の Chart 依存関係は Chart.yaml で宣言します。 |
| Kustomize | ベースとパッチを使ってマニフェストを変換します。ランタイムコントローラーではありません。 |
| カスタム Operator | ドメイン固有の復旧、移行、バックアップをコードで実装できます。 |
| kro | CEL 参照からリソースグラフを推論し、インスタンスを調整します。データベースの復旧アルゴリズムを生成するものではありません。 |

Helm Chart で kro をインストールし、GitOps で RGD とインスタンスを管理できます。これらのツールは併用できます。Helm から kro に移行しても、セキュリティ、復旧、運用が自動的に改善されるわけではありません。Kubernetes Deployment コントローラーは、Helm が最初に作成した Deployment も引き続き管理します。

## インストールと権限

公式リポジトリは kubernetes-sigs/kro です。以前の kro-run パスはリダイレクトされる場合があります。以下は、バージョンを固定した OCI Chart の**オフラインでの確認**です。以前の kro-project ダウンロード URL や、実在しない CLI インストール方法は使用しないでください。このリリースでは独立した CLI バイナリは配布されていません。kubectl と Helm を使用してください。

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

インストール前に、対応 Kubernetes バージョン、アドミッションポリシー、Namespace、既存の CRD とコントローラーを確認してください。以前の 1.31～1.33 という一覧は、現在のサポート対象として示したものではありません。Helm upgrade では crds/ は自動更新されません。0.9.4 のリリースと CRD の変更を、別の手順で確認してください。

デフォルトの rbac.mode=unrestricted は、広範なクラスターアクセスを許可します。以下の例は aggregation モードでレンダリングされますが、CRD、RGD、GraphRevisions、ConfigMaps に対する基本権限も含まれます。生成されるアプリケーション API と子リソースの権限を追加してください。この ClusterRole は例で使用するリソースタイプへのアクセスを許可し、クラスター全体にわたるアクセスを付与する可能性があります。RGD と集約ラベルは、信頼されたプラットフォーム管理者が管理してください。

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

## NginxApp の完全な例

RGD、インスタンス、RBAC のファイルは examples/platform/kro にもあります。Ingress はデフォルトで無効です。有効にする前に、承認済みの IngressClass とコントローラー、ホストの DNS、同じ Namespace 内の TLS Secret を用意してください。className=internal という文字列を指定するだけでは、内部ロードバランサーは構成されません。この例では、インスタンスから `ingress.className` と `ingress.host` を直接設定できます。マルチテナントクラスターでは、これを利用して別のチームのホストを乗っ取れる可能性があります。本番環境の RGD では、クラスを固定し、インスタンス名と Namespace からホストを導出してください。

このイメージは、Helm の例と同じ nginx-unprivileged タグを使用します。root 以外の UID、読み取り専用ルートファイルシステム、/tmp ボリュームを設定していますが、イメージの実行確認はしていません。デプロイ前に、ダイジェスト、アーキテクチャ、ポリシーを確認してください。

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

schema.spec の SimpleSchema では、型、デフォルト値、範囲を定義します。kro はこれを、生成される CRD の OpenAPI スキーマに変換します。CEL の schema.metadata/spec はインスタンスを参照し、deployment/service はリソース ID を参照します。投影するステータスは schema.status の下に定義してください。

この例の readyWhen は、Deployment 自身の availableReplicas と observedGeneration を確認します。readiness 条件がなければ、オブジェクトが存在し参照を解決できることで処理が先に進む場合があります。readyWhen は Boolean 値を返し、自身のリソース ID のみを参照する必要があります。アプリケーションの SLO とデータベースの確認は別途行います。

Service は Deployment のセレクターを参照し、Ingress は Service 名を参照して依存関係を作成します。依存関係のないリソースは同じ Wave にまとめられます。循環依存は拒否されます。includeWhen は条件付きの組み込みを制御し、条件が変わったときにリソースを追加または削除できます。既存リソースへの externalRef は、そのリソースを所有して作成または削除することとは異なります。

### 適用順序と確認

承認済みクラスターでは、確認済みの RBAC と RGD を適用し、RGD が Active で、生成された nginxapps.platform.example.com CRD が Established であることを確認してから、インスタンスを適用してください。kubectl apply が成功しても、グラフのコンパイルやアプリケーションの準備完了が証明されるわけではありません。

```bash
kubectl get rgd reviewed-nginxapps -o yaml
kubectl get graphrevisions \
  -l internal.kro.run/resource-graph-definition-name=reviewed-nginxapps
kubectl get crd nginxapps.platform.example.com -o yaml
kubectl get nginxapps.platform.example.com reviewed-web -n example -o yaml
kubectl get deployments,services,ingresses -n example \
  -l app.kubernetes.io/name=reviewed-web
```

## GraphRevisions と変更

バージョン 0.9.4 では、RGD の spec が変更されると、不変の GraphRevisions が記録され、コンパイルされます。最新のリビジョンが失敗しても、以前のリビジョンには自動で戻りません。インスタンスの処理が停止することがあります。GraphAccepted、GraphVerified、GraphRevisionsResolved とエラーメッセージを確認し、有効な spec を適用してください。

GraphRevision は internal.kro.run API です。安定した外部ツールの契約があると想定せず、確認と診断に使用してください。Git の spec を以前の内容に戻しても、新しいリビジョンでの検証が必要です。また、データベースのデータや外部への影響がトランザクションとしてロールバックされるわけではありません。

RGD 内では、group、kind、apiVersion、scope は不変です。互換性のあるスキーマ進化と新しい API への移行を区別し、既存インスタンスと保存データを確認してください。変換 Webhook が自動生成されると想定しないでください。

## 削除と所有権

インスタンスが削除されると、kro は ApplySet のインベントリと削除 Wave を使い、依存するリソースから先に削除します。管理対象のリソースがなくなるまで finalizer は保持されます。子リソースの finalizer により、後続の Wave が停止する場合があります。外部参照は読み取り専用であり、kro が削除することはありません。

すべての子リソースが直ちにガベージコレクションされるという説明は正確ではありません。ResourcesReady=Unknown/UnderDeletion、インベントリ、子リソースの finalizer を確認してください。コントローラーを削除する前に、インスタンス、RGD、CRD、データのクリーンアップと保持を計画してください。CRD の削除はインスタンスデータにも影響します。

## 移行と運用

名前、セレクター、所有権、フィールドマネージャー、GitOps コントローラーを確認し、Helm と kro が同じオブジェクトを奪い合わないようにしてください。検証済みの新しい名前を持つグラフを作成してトラフィックを切り替えるか、確認済みの所有権移管プロセスを選んでください。StatefulSet、PVC、データベースを所有するリリースを安易にアンインストールして移行しないでください。

環境間で同じ API 契約と確認済みのイメージダイジェストを使用し、Namespace、レプリカ、Ingress、ポリシーごとに別々のインスタンスを用意してください。ApplicationSet などのフリート管理ツールを使う場合は、各ターゲットクラスターに kro、RGD、権限が必要です。kro は任意のリモートクラスターに自動接続するものではありません。

ステートフルなアプリケーションには、データベース Operator またはマネージドサービスによるバックアップ、復元、フェイルオーバー、移行の動作が引き続き必要です。リソースの調整だけではデータは復旧できません。グラフの規模と権限を制限し、再利用可能な単位を定義し、有用なステータスのみを公開してください。Secret の内容をステータス、ラベル、ログにコピーしないでください。

## EKS マネージド kro

EKS Capabilities の kro 機能は、AWS 所有のインフラストラクチャ上で同じアップストリームコントローラー（実測値 `0.9.4-eks-1`）を実行します。2026年10月のテストでは、この章の `NginxApp` RGD を使用し、Ingress クラスとホストを固定するよう変更しました。CEL 式は変更せずに動作し、インスタンスのライフサイクル時間も OSS と同等でした。異なるのは権限と運用です。

- デフォルトのアクセスエントリーポリシー `AmazonEKSKROPolicy` が対象とするのは、`kro.run` と CRD のみです。上記の `kro:controller:reviewed-nginxapps` などの ClusterRole を、アクセスエントリー上の Kubernetes グループにバインドしてください。バインドされていない場合、RGD は forbidden ではなく、`cache sync timeout` を伴う `ControllerReady=False` を報告します。ルールは同じで、異なるのはバインド方法（集約ラベルではなくグループを使用）だけです。
- バージョンは AWS が選択するため、固定できません。コントローラーフラグとリソース制限も変更できません。
- Namespace 内に子リソースと同じ名前の CR がある場合、kro はそれを引き取り、上書きします（OSS も同じ動作です）。子リソース名には RGD 固有のサフィックスを追加してください。

測定結果と選択の指針については、[EKS Capabilities](../eks/13-eks-capabilities.md) を参照してください。

## 検証と参考資料

元の 504 行のガイド 2 本と 423 行のクイズ 2 本を確認しました。言語ごとに、重複を除いた 16 個のコードブロックと 20 個の設問トピックが含まれています。公式 kro 0.9.4 Chart を aggregation モードでレンダリングし、RGD の構造を確認しました。その依存関係にある cel-go 0.31.0 で、公開されている重複のない 14 個の式をコンパイルして評価しました。Ingress の有効・無効、レプリカ不足、古い observedGeneration の 4 つの合成ケースを確認しました。

これらは動的な合成入力を使用した CEL の確認であり、kro の完全なグラフコンパイラー、Kubernetes API ディスカバリー、生成 CRD のアドミッション、実行中のコントローラーによる検証ではありません。コンテナー、Ingress/TLS、データベース、クラスターリソースは実行していません。

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [バージョン付き API とソース](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [RGD スキーマ](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [アクセス制御](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [グラフリビジョン](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [インスタンスの削除](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[kro クイズ](../quizzes/platform-engineering/03-kro-quiz.md)
