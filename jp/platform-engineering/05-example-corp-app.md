# ExampleCorpの注文システム: ACKとkroの統合

> **最終更新日**: 2026年10月16日 · kro 0.9.4 / AWS Load Balancer Controller 3.6.0

## シナリオと検証範囲

ExampleCorpは架空の企業です。このガイドでは、kroのアプリケーショングラフとACK管理のインフラストラクチャを接続する統合コントラクトを定義します。動作するOrder APIや、公開済みのアプリケーションイメージを提供するエンドツーエンドのラボではありません。以前の架空のECRイメージは、実行可能なものとして提示していません。

ACKはNLB、TargetGroup、Listener、Route 53レコード、Auroraを管理します。kroはService、ConfigMap、TargetGroupBinding (TGB)、Deploymentリソースを作成します。**別個のAWS Load Balancer Controller (LBC) がTGBを調整し、Pod IPターゲットを登録/登録解除します。** ACKとkroをインストールするだけでは、この接続は実装されません。

![ACKインフラストラクチャとkroアプリケーション間のTargetGroupBindingをAWS LBCが調整する構成図](../.gitbook/assets/en-platform-engineering-05-example-corp-app-0.png)

[インタラクティブな図](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-05-example-corp-app-0.html)

## インフラストラクチャとアプリケーションの前提条件

最初に、[ACKリソースの例](ack/03-elbv2-route53-rds.md)にある現在のスキーマとライフサイクルのガイダンスを確認してください。承認済みのVPC/プライベートサブネット/セキュリティグループ、内部NLB/Listener、ipタイプのTargetGroup、DNS、Auroraクラスター/インスタンスを準備します。TargetGroup ARNは、以前使われていた`.status.targetGroupARN`ではなく、`.status.ackResourceMetadata.arn`から読み取ってください。

AWS LBC、そのCRD、IAM/ServiceAccount、webhookは別途準備します。このガイドが確認するのはOSS LBC 3.6.0のelbv2.k8s.aws/v1beta1 TGBであり、EKS Auto Modeの別のロードバランシングAPIではありません。TGBを作成できる主体は、コントローラーのIAM権限で許可されたTargetGroupを参照できるため、許可するARN、名前空間、書き込み権限を制限してください。

運用者は、以下のコントラクトを満たすOrder APIイメージを用意する必要があります。

- 設定したポートでHTTPを提供し、`/readyz`でreadinessを返す。
- DB_WRITER_HOST、DB_READER_HOST、DB_PORT、DB_NAMEをConfigMapの設定から読み取る。
- DB_CREDENTIALS_DIR配下の認証情報ファイルを読み取り、ローテーションに対応する。パスワードを環境変数、ConfigMap、statusに格納しない。
- UID 10001、読み取り専用root、上限を設定したリソース、書き込み可能な`/tmp`ボリュームで動作する。実際のイメージが異なる場合は、セキュリティポリシーに従ってコントラクトを適合させる。

productionとorder-db-credentialsは、承認済みのprovider/ESOフローで準備します。RDS管理のSecrets Manager認証情報からKubernetes Secretが自動作成されるわけではありません。アプリケーションのデータベース/ユーザー、最小限のDB権限、TLS検証、コネクションプールは、それぞれ別途必要です。CRでデータベース名を指定しても、データベース自体は作成されません。

## Readiness gateと作成順序

LBCのPod readiness gateを使うには、**Podを作成する前に**名前空間に`elbv2.k8s.aws/pod-readiness-gate-inject=enabled`ラベルを付けます。対応するServiceとip型TGBがすでに存在している必要があります。グラフではCELによってService → TGB → Deploymentの順序を強制します。DeploymentのアノテーションがTGB名を参照し、その依存関係を示します。

TGBには、ターゲットがhealthyになるまで待つreadyWhenはありません。ターゲットのhealthを待ってからPodを作成すると、healthyなターゲットになるPodがまだないためデッドロックする可能性があります。TGBの存在、LBCの調整、ターゲットのhealth、Podのreadinessはそれぞれ別の状態です。webhookのfailurePolicy/注入、ロールアウト、シャットダウン猶予時間、登録解除の遅延を確認してください。

## ResourceGraphDefinition

これらのファイルはexamples/platform/examplecorpにもあります。OrderApp/status/finalizersと、Service、ConfigMap、Deployment、TGBリソースの集約RBACを確認して追加してください。RGDの作成権限を与えると、コントローラー権限の使用を委譲することになります。

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

## インスタンスへの入力

以下のexample.invalidのアドレス/イメージ、ARN/VPC IDはプレースホルダーです。実際のACKエンドポイント/ARNを取得し、利用する前にアプリケーションイメージのダイジェストとSecretを検証してください。手動でコピーしたエンドポイントはACKの変更に自動追従しません。承認済みのGitOps経由で入力を更新できるようにしてください。

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

CRのconditionとDeploymentの状態を、Pod readiness gate、EndpointSlice、TGBの状態、AWSターゲットのhealth、DNS/HTTP、データベースのTLS接続性と併せて確認してください。readinessがデータベースを確認するかは、実際のアプリケーションによって異なります。生成されるすべてのリソースメタデータに同じクエリ用ラベルが付与されます。

新しい決済サービスには、レビュー済みイメージ、別個のTargetGroup/Listenerルーティング計画、データベースユーザー/権限/スキーマの契約が必要です。Auroraを共有しても、データ、性能、コストの分離は保証されません。複数のTGB/クラスターでTargetGroupを共有する場合は、multiClusterTargetGroupのライフサイクルを意図的に管理します。デフォルトの所有権モデルを無視すると、ほかのターゲットが登録解除される可能性があります。

Auroraレプリカは、サポート対象のクラス/リージョンの組み合わせでACK DBInstanceから追加します。名前やタグでwriterの役割が決まるわけではありません。[RDSの例](ack/03-elbv2-route53-rds.md)にあるpromotionTier、エンドポイント、フェイルオーバーのガイダンスに従い、実際の負荷と復旧をテストしてください。

Deploymentのイメージを更新すると通常はRollingUpdateが行われます。自動Blue/Greenやゼロダウンタイムが保証されるわけではありません。Blue/Greenには、別個のアプリケーションバージョン、ターゲット/ルーティングの切り替え、検証メトリクス、ロールバック条件、データベース互換性が必要です。CRを削除/置換すると、子リソースのTGB/Deploymentやターゲットとの関連付けがクリーンアップされる可能性があります。これは安全なバージョン切り替えではありません。

## 実施した確認

元の両ガイドとすべての例を読み、現在のRGD/TGBスキーマと比較しました。cel-goで一意な式21個をコンパイル/評価し、4つのリソース、Service/Podセレクター、ConfigMap/Serviceの参照、Deploymentより前に必要なTGBの依存関係、statusを確認しました。これらは合成入力を用いたローカル確認です。AWSリソース、アプリケーションイメージ、データベース、ターゲットhealth、Podの変更、トラフィックはいずれも実行していません。

- [ACK](02-ack.md)
- [kro](03-kro.md)
- [AWS LBC 3.6.0 TGB](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/targetgroupbinding/targetgroupbinding.md)
- [Pod readiness gate](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/deploy/pod_readiness_gate.md)
