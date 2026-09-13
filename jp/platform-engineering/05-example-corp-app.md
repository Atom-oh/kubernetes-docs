# ExampleCorp 注文システム: ACK + kro の統合

> **最終更新**: September 12, 2026 · kro 0.9.4 / AWS Load Balancer Controller 3.5.0

## シナリオと検証範囲

ExampleCorp は架空の企業です。このガイドは、kro のアプリケーショングラフと ACK が管理するインフラストラクチャを接続する統合コントラクトを定義します。動作する Order API や公開されたアプリケーションイメージを提供するエンドツーエンドのラボではありません。以前の架空の ECR イメージは、実行可能なものとしては提示されていません。

ACK は NLB、TargetGroup、Listener、Route 53 レコード、および Aurora を管理します。kro は Service、ConfigMap、TargetGroupBinding (TGB)、および Deployment リソースを作成します。**別個の AWS Load Balancer Controller (LBC) が TGB を reconcile し、Pod IP ターゲットの登録/登録解除を行います。** ACK と kro をインストールするだけでは、その接続は実装されません。

![AWS LBC が ACK インフラストラクチャと kro アプリケーションの間で TargetGroupBinding を reconcile する](../.gitbook/assets/en-platform-engineering-05-example-corp-app-0.png)

[インタラクティブな図](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-05-example-corp-app-0.html)

## インフラストラクチャとアプリケーションの前提条件

まず [ACK リソースの例](ack/03-elbv2-route53-rds.md) にある現在のスキーマとライフサイクルのガイダンスを確認してください。承認済みの VPC/プライベートサブネット/セキュリティグループ、内部 NLB/Listener、ip タイプの TargetGroup、DNS、および Aurora クラスター/インスタンスを準備します。TargetGroup ARN は、以前の `.status.targetGroupARN` ではなく `.status.ackResourceMetadata.arn` から読み取ってください。

AWS LBC、その CRD、IAM/ServiceAccount、および webhook は別途準備します。このガイドが確認しているのは OSS LBC 3.5.0 の elbv2.k8s.aws/v1beta1 TGB であり、EKS Auto Mode の異なるロードバランシング API ではありません。TGB の作成者は controller の IAM 権限の範囲内で TargetGroup を参照できるため、許可する ARN、namespace、および書き込みアクセスを制限してください。

運用者は、次のコントラクトを満たす Order API イメージを提供する必要があります。

- 設定されたポートで HTTP を提供し、readiness を `/readyz` で公開する。
- ConfigMap の設定から DB_WRITER_HOST、DB_READER_HOST、DB_PORT、および DB_NAME を読み取る。
- DB_CREDENTIALS_DIR 以下の認証情報ファイルを読み取り、ローテーションする。パスワードを環境変数、ConfigMap、または status に置かないこと。
- UID 10001、読み取り専用の root、制限されたリソース、および書き込み可能な /tmp ボリュームで動作する。実際のイメージが異なる場合は、セキュリティポリシーに従ってコントラクトを適合させてください。

production と order-db-credentials は、承認済みの provider/ESO フローを通じて準備してください。RDS が管理する Secrets Manager の認証情報は、Kubernetes Secret を自動的に作成しません。アプリケーションのデータベース/ユーザー、最小限の DB 権限、TLS 検証、およびコネクションプーリングは別個の要件です。CR でデータベース名を指定しても、そのデータベースは作成されません。

## Readiness gate と作成順序

LBC の Pod readiness gate を使うには、**Pod の作成前に** namespace に elbv2.k8s.aws/pod-readiness-gate-inject=enabled のラベルを付与します。対応する Service とその ip タイプの TGB が既に存在している必要があります。グラフは CEL によって Service → TGB → Deployment の順序を強制します。Deployment のアノテーションが TGB 名を参照することで、その依存関係を確立します。

TGB には、ターゲットが healthy になるのを待つ readyWhen はありません。Pod の作成をターゲットの health を待たせると、healthy なターゲットになる Pod が存在しないためデッドロックする可能性があります。TGB の存在、LBC の reconcile、ターゲットの health、および Pod の readiness は異なる状態です。webhook の failurePolicy/インジェクション、ロールアウト、シャットダウンの猶予時間、および登録解除の遅延を検証してください。

## ResourceGraphDefinition

これらのファイルは examples/platform/examplecorp にもあります。OrderApp/status/finalizers と Service、ConfigMap、Deployment、TGB リソースに対する集約 RBAC を確認し、追加してください。RGD を作成する権限は、controller の権限の使用を委譲することになります。

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: examplecorp-webapps
spec:
  schema:
    apiVersion: v1alpha1
    group: platform.example.com
    kind: OrderApp
    scope: Namespaced
    spec:
      replicas: integer | default=3 minimum=1 maximum=10
      image: string | required=true
      port: integer | default=8080 minimum=1 maximum=65535
      targetGroupARN: string | required=true
      vpcID: string | required=true
      credentialsSecretName: string | required=true
      aurora:
        writerEndpoint: string | required=true
        readerEndpoint: string | required=true
        port: integer | default=5432
        dbName: string | required=true
    status:
      availableReplicas: ${deployment.status.availableReplicas}
      serviceIP: ${service.spec.clusterIP}
  resources:
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
        selector:
          app.kubernetes.io/name: ${schema.metadata.name}
        ports:
        - name: http
          port: ${schema.spec.port}
          targetPort: http
  - id: dbConfig
    template:
      apiVersion: v1
      kind: ConfigMap
      metadata:
        name: ${schema.metadata.name + "-db"}
        namespace: ${schema.metadata.namespace}
        labels:
          app.kubernetes.io/name: ${schema.metadata.name}
      data:
        DB_WRITER_HOST: ${schema.spec.aurora.writerEndpoint}
        DB_READER_HOST: ${schema.spec.aurora.readerEndpoint}
        DB_PORT: ${string(schema.spec.aurora.port)}
        DB_NAME: ${schema.spec.aurora.dbName}
  - id: targetGroupBinding
    template:
      apiVersion: elbv2.k8s.aws/v1beta1
      kind: TargetGroupBinding
      metadata:
        name: ${schema.metadata.name + "-tgb"}
        namespace: ${schema.metadata.namespace}
        labels:
          app.kubernetes.io/name: ${schema.metadata.name}
      spec:
        targetGroupARN: ${schema.spec.targetGroupARN}
        targetType: ip
        vpcID: ${schema.spec.vpcID}
        serviceRef:
          name: ${service.metadata.name}
          port: ${schema.spec.port}
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
            annotations:
              platform.example.com/target-group-binding: ${targetGroupBinding.metadata.name}
          spec:
            automountServiceAccountToken: false
            securityContext:
              runAsNonRoot: true
              runAsUser: 10001
              runAsGroup: 10001
              fsGroup: 10001
              seccompProfile:
                type: RuntimeDefault
            containers:
            - name: order-api
              image: ${schema.spec.image}
              ports:
              - name: http
                containerPort: ${schema.spec.port}
              securityContext:
                allowPrivilegeEscalation: false
                readOnlyRootFilesystem: true
                capabilities:
                  drop:
                  - ALL
              resources:
                requests:
                  cpu: 100m
                  memory: 64Mi
                limits:
                  cpu: 500m
                  memory: 128Mi
              readinessProbe:
                httpGet:
                  path: /readyz
                  port: http
              volumeMounts:
              - name: tmp
                mountPath: /tmp
              - name: db-credentials
                mountPath: /var/run/order-db
                readOnly: true
              envFrom:
              - configMapRef:
                  name: ${dbConfig.metadata.name}
              env:
              - name: DB_CREDENTIALS_DIR
                value: /var/run/order-db
            volumes:
            - name: tmp
              emptyDir:
                sizeLimit: 64Mi
            - name: db-credentials
              secret:
                secretName: ${schema.spec.credentialsSecretName}
```

## インスタンスの入力

以下の example.invalid のアドレス/イメージおよび ARN/VPC ID はプレースホルダーです。実際の ACK のエンドポイント/ARN を読み取り、使用前にアプリケーションイメージのダイジェストと Secret を検証してください。手動でコピーしたエンドポイントは ACK の変更に自動的に追従しないため、承認済みの GitOps による入力更新の経路を用意してください。

```yaml
apiVersion: platform.example.com/v1alpha1
kind: OrderApp
metadata:
  name: order-api
  namespace: production
spec:
  replicas: 3
  image: example.invalid/order-api:replace-with-reviewed-image
  port: 8080
  targetGroupARN: arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/replace-with-approved-tg/0123456789abcdef
  vpcID: vpc-0123456789abcdef0
  credentialsSecretName: order-db-credentials
  aurora:
    writerEndpoint: replace-with-writer-endpoint.example.invalid
    readerEndpoint: replace-with-reader-endpoint.example.invalid
    port: 5432
    dbName: orders
```

## 検証と運用

```bash
kubectl get orderapps.platform.example.com order-api -n production -o yaml
kubectl get deploy,svc,targetgroupbindings.elbv2.k8s.aws,configmap \
  -n production -l app.kubernetes.io/name=order-api
kubectl get pods -n production -l app.kubernetes.io/name=order-api -o wide
```

CR の condition と Deployment の状態を、Pod の readiness gate、EndpointSlice、TGB の状態、AWS のターゲット health、DNS/HTTP、およびデータベースの TLS 接続性と併せて確認してください。readiness がデータベースを確認するかどうかは実際のアプリケーションに依存します。生成されるすべてのリソースのメタデータには同じクエリ用ラベルが付きます。

新しい決済サービスには、レビュー済みのイメージ、別個の TargetGroup/Listener のルーティング計画、およびデータベースのユーザー/権限/スキーマのコントラクトが必要です。Aurora を共有しても、データ、パフォーマンス、コストの分離は保証されません。複数の TGB/クラスター間で TargetGroup を共有する場合は、multiClusterTargetGroup のライフサイクルを意図的に扱う必要があります。デフォルトの所有権モデルを無視すると、他のターゲットが登録解除される可能性があります。

Aurora のレプリカは、サポートされているクラス/リージョンの組み合わせを使用して ACK DBInstance 経由で追加します。名前やタグによって writer の役割が決まるわけではありません。[RDS の例](ack/03-elbv2-route53-rds.md) にある promotionTier、エンドポイント、およびフェイルオーバーのガイダンスに従い、実際の負荷とリカバリをテストしてください。

Deployment のイメージを更新すると通常は RollingUpdate が実行され、自動的な Blue/Green やゼロダウンタイムが保証されるわけではありません。Blue/Green には、別個のアプリケーションバージョン、ターゲット/ルーティングの切り替え、検証メトリクス、ロールバック条件、およびデータベースの互換性が必要です。CR を削除/置換すると、子の TGB/Deployment やターゲットの関連付けがクリーンアップされる可能性があり、無害なバージョン切り替えではありません。

## 実施した確認

元の両方のガイドとすべての例を読み、現在の RGD/TGB スキーマと比較しました。cel-go で 21 個の一意な式をコンパイル/評価し、4 つのリソース、Service/Pod の selector、ConfigMap/Service の参照、Deployment より前の TGB の依存関係、および status を確認しました。これらは合成入力を用いたローカルの確認です。AWS リソース、アプリケーションイメージ、データベース、ターゲット health、Pod の mutation、トラフィックはいずれも実行していません。

- [ACK](02-ack.md)
- [kro](03-kro.md)
- [AWS LBC 3.5.0 TGB](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/targetgroupbinding/targetgroupbinding.md)
- [Pod readiness gate](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/pod_readiness_gate.md)
