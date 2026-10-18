# パート5: ベストプラクティスとセキュリティ

> **レビューの基準日**: 2026年9月12日 · 上流版Spark 4.2.0／Hadoop 3.5.0／AWS SDK v2 2.35.4

## 対象範囲

この章では、パート1のKubernetesへの直接サブミットを基に、一時的なS3認証情報、メトリクス／イベントログ、History Server、ネットワーキング、RBACを扱います。
Spark 4.2ではKubernetes 1.34以降を使用し、互換性のあるkubectl、spark-jobs名前空間、EKSアクセスを準備してください。
OperatorとEMRには、それぞれ独自の設定方法と権限経路があります。

IRSAまたはPod Identityを設定できる管理者権限、既存のS3バケットとロール、レジストリ、イメージビルド用ツールを用意します。
PodMonitorの例はPrometheus Operatorがインストールされている場合に限り適用してください。
以下のアカウント、バケット、イメージ、リージョンの値は、**置き換えるための例**です。
設定チェックリストを埋めても、運用の安全性、復旧性、性能が立証されるわけではありません。

## 1. バージョン互換のS3Aイメージを作成する

確認済みのSpark 4.2ディストリビューションにはHadoopクライアント3.5.0が含まれますが、追加のS3A依存関係がすべて含まれるわけではありません。
`hadoop-aws`は**同じHadoopバージョン**に合わせてください。
3.5.0でMavenが解決する実行時依存関係は次のとおりです。

| アーティファクト | バージョン |
| --- | --- |
| org.apache.hadoop:hadoop-aws | 3.5.0 |
| software.amazon.awssdk:bundle | 2.35.4 |
| software.amazon.s3.analyticsaccelerator:analyticsaccelerator-s3 | 1.3.1 |
| org.wildfly.openssl:wildfly-openssl | 2.2.5.Final |

無関係な古いAWS SDKのJARを混在させたり、`hadoop-aws`だけをコピーしたりしないでください。
このPOMはHadoop commonを再コピーせずに、実行時依存関係を解決します。
別のSparkイメージまたはEMRランタイムでは、同梱されるバージョンを再確認してください。

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>docs.review</groupId>
  <artifactId>spark-s3a-runtime</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.apache.hadoop</groupId>
      <artifactId>hadoop-aws</artifactId>
      <version>3.5.0</version>
    </dependency>
  </dependencies>
</project>
```

Dockerfileとして保存します。選択したイメージのプラットフォームは、ワークロードとHistory Serverのノードに合わせてください。

```dockerfile
FROM spark:4.2.0-scala2.13-java21-ubuntu
COPY --chown=185:185 s3a-jars/ /opt/spark/jars/
USER 185
```

```bash
# Save the XML below as s3a-pom.xml.
mvn -f s3a-pom.xml org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies \
  -DincludeScope=runtime -DoutputDirectory="$PWD/s3a-jars"
: "${SPARK_S3_IMAGE:?Set a registry/repository/tag you can publish}"
: "${SPARK_IMAGE_PLATFORM:?Set a platform matching the target nodes, for example linux/amd64}"
docker build --platform "$SPARK_IMAGE_PLATFORM" --tag "$SPARK_S3_IMAGE" .
# Authenticate to your registry through your normal procedure, then publish the tested image.
docker push "$SPARK_S3_IMAGE"
```

ドライバー、エグゼキューター、History Serverのすべてで、依存関係を含むイメージを使います。
`--packages`はサブミッター経由で依存関係を解決するものであり、`spark-class`で起動したHistory Serverに自動で依存関係をインストールするわけではありません。
レジストリへのアクセス、イメージの検査、互換性、実際のS3読み書きを検証したうえで、運用にはテスト済みイメージのダイジェストを固定してください。

## 2. IRSAとPod Identityを区別する

このHadoop 3.5.0／SDK v2の組み合わせでは、次の設定を使います。

| アイデンティティ経路 | fs.s3a.aws.credentials.provider |
| --- | --- |
| IRSA | software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider |
| EKS Pod Identity | software.amazon.awssdk.auth.credentials.ContainerCredentialsProvider |

IRSAでは、OIDC信頼、ServiceAccountアノテーション、投影されたWeb Identityトークンを使います。
Pod Identityでは、関連付けとAgentのコンテナ認証情報経路を使います。IRSAのアノテーションでは設定できません。
両方を無条件に組み合わせないでください。

S3Aの既定チェーンにはコンテナ／インスタンス認証情報ラッパーが含まれますが、Web Identityプロバイダーは含まれません。
古い`com.amazonaws.auth.WebIdentityTokenCredentialsProvider`は、このSDK v2だけを使う組み合わせでは自動的に対応付けられませんでした。
ほかの一部の旧式エイリアスは対応付けられるため、古い名前はすべて常に失敗するという意味ではありません。
アイデンティティ経路を明示すると、ほかの認証情報ソースへ意図せずフォールバックする可能性も抑えられます。
一時認証情報にも、正しい信頼設定、権限、ネットワーク接続が必要です。

次の**IRSAの例**を`serviceaccounts.yaml`として保存します。ロールを置き換え、先にクラスターのOIDCプロバイダー、Audience、正確なnamespace／ServiceAccountのSubjectに対する信頼を設定してください。
エグゼキューターとHistory Serverには、ドライバーのKubernetes管理権限を与えません。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-data-driver
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/docs-spark-driver
automountServiceAccountToken: true
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-data-executor
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/docs-spark-executor
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-data-history
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/docs-spark-history
automountServiceAccountToken: false
```

用途ごとにデータ権限を分離します。

- Driver: `spark-events`配下への読み書きなど、必要な入出力アクセスとイベントログ書き込み。S3Aのrename／multipart要件と、必要なKMS権限を確認する。
- Executors: 実際のデータ処理に必要なバケット／プレフィックスだけを許可する。
- History Server: イベントログのプレフィックスを一覧／読み取りし、必要に応じてKMSで復号する。この例ではcleanerを無効にしているため、削除権限は不要。

Pod Identityでは、IRSAアノテーションを削除し、これら3つのServiceAccountについて関連付け、ロール信頼、Agent／ノードのEKS Auth権限を設定します。
また、以下のプロパティを`ContainerCredentialsProvider`に変更してください。
IAM OIDCプロバイダーはIRSAの前提条件ですが、すべてのアイデンティティ経路に共通する要件ではありません。

## 3. ドライバーのRBACとジョブ設定

次の内容を`driver-rbac.yaml`として保存します。
この基本設定ではPVCを作成せず、追加権限が必要になる別機能も有効にしていません。それらを追加する前に機能ごとに確認してください。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: spark-data-driver
  namespace: spark-jobs
rules:
- apiGroups:
  - ''
  resources:
  - pods
  - services
  - configmaps
  verbs:
  - create
  - get
  - list
  - watch
  - delete
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: spark-data-driver
  namespace: spark-jobs
subjects:
- kind: ServiceAccount
  name: spark-data-driver
  namespace: spark-jobs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: spark-data-driver
```

Roleは、列挙したリソースに対する権限をnamespace内で付与します。「ドライバー自身のエグゼキューター」だけに限定するものではありません。
Kubernetes RBACでは、これらのルールにPodラベル条件は追加されません。
RoleBindingからClusterRoleをバインドする場合も、名前空間スコープのリソース権限をそのnamespace内に限定できます。
オブジェクト名だけでなく、**ルールとバインドのスコープ**を確認してください。

Pod作成権限は、別のServiceAccountまたはホストアクセスと組み合わさる可能性があります。そのため、namespace内のRoleだけで完全な境界ができるわけではありません。
信頼ドメインを分離し、Pod Security／admission、危険なPod仕様の制限、IAM、ネットワーキングを使ってください。
APIトークンの自動マウントを無効にすることと、別途注入するIRSAトークンは異なります。

バケットとリージョンを置き換え、`job.properties`として保存します。

```properties
spark.kubernetes.namespace=spark-jobs
spark.kubernetes.authenticate.driver.serviceAccountName=spark-data-driver
spark.kubernetes.authenticate.executor.serviceAccountName=spark-data-executor
spark.hadoop.fs.s3a.aws.credentials.provider=software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider
spark.hadoop.fs.s3a.endpoint.region=ap-northeast-2
spark.eventLog.enabled=true
spark.eventLog.dir=s3a://my-spark-bucket/spark-events/
spark.eventLog.logStageExecutorMetrics=true
spark.metrics.conf.*.sink.prometheusServlet.class=org.apache.spark.metrics.sink.PrometheusServlet
spark.metrics.conf.*.sink.prometheusServlet.path=/metrics/prometheus
spark.ui.prometheus.enabled=true
spark.ui.port=4040
spark.driver.port=7078
spark.driver.blockManager.port=7079
spark.blockManager.port=7079
spark.port.maxRetries=0
spark.authenticate=true
spark.network.crypto.enabled=true
spark.network.crypto.cipher=AES/GCM/NoPadding
spark.network.crypto.authEngineVersion=2
spark.network.crypto.saslFallback=false
spark.io.encryption.enabled=true
```

`spark.authenticate`が認証するのは内部接続であり、UIのユーザーではありません。
Kubernetesモードでは、アプリケーションごとに生成されたシークレットがエグゼキューターの環境へ伝播し、Podを読み取る権限を持つアイデンティティから見える場合があります。
Pod読み取り権限と、安全に生成してマウントするSecretファイルを使う方法を確認してください。
固定された認証シークレットをpropertiesやGitにコミットしないでください。

ここでのRPC暗号化設定は、バージョンが一致する現行のSparkを対象にしています。ほかのクライアント／shuffleサービスとの互換性を検証してください。
IO暗号化の対象は、サポートされるSparkの一時ローカルデータであり、S3／EBS／KMSやUIのTLSではありません。
UIには別途、認証、認可、TLSのアクセス経路が必要です。

## 4. 実行ごとの受信ルールとサブミット

Roleラベルだけを選択すると、同じnamespace内の**ほかのジョブのエグゼキューター**も許可されます。
次の内容を`make-network-policy.py`として保存します。
サブミット前に生成する一意の実行IDを使い、Podラベルとポリシーの両方に指定します。
Prometheusのnamespace／Podラベルは、実際のインストール値に置き換えてください。

```python
import json
import os
import re
from pathlib import Path

run_id = os.environ["SPARK_RUN_ID"]
if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?", run_id):
    raise ValueError("SPARK_RUN_ID must be a lowercase DNS label, at most 40 characters")
monitor_ns = os.environ.get("PROMETHEUS_NAMESPACE", "monitoring")
def peer(role):
    return {"podSelector": {"matchLabels": {"docs-job": run_id, "spark-role": role}}}
def policy(role, ingress):
    return {
        "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
        "metadata": {"name": run_id + "-" + role, "namespace": "spark-jobs"},
        "spec": {"podSelector": {"matchLabels": {"docs-job": run_id, "spark-role": role}},
                 "policyTypes": ["Ingress"], "ingress": ingress}}
driver = policy("driver", [
    {"from": [peer("executor")], "ports": [{"protocol": "TCP", "port": 7078}, {"protocol": "TCP", "port": 7079}]},
    {"from": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": monitor_ns}},
               "podSelector": {"matchLabels": {"app.kubernetes.io/name": "prometheus"}}}],
     "ports": [{"protocol": "TCP", "port": 4040}]},
])
executor = policy("executor", [
    {"from": [peer("driver"), peer("executor")], "ports": [{"protocol": "TCP", "port": 7079}]},
])
Path("job-networkpolicy.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": [driver, executor]}, indent=2) + "\n")
```

ServiceAccountとRBACをレビューして適用した後、同じ実行IDを使ってポリシーとジョブをサブミットします。

```bash
kubectl apply -f serviceaccounts.yaml
kubectl apply -f driver-rbac.yaml
```

```bash
# Set SPARK_S3_IMAGE to the built/published image accessible to your EKS nodes.
: "${SPARK_S3_IMAGE:?Set the tested Spark S3 image reference}"
export SPARK_RUN_ID="spark-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
# Set this to the actual namespace/Pod labels of the Prometheus collector.
export PROMETHEUS_NAMESPACE=monitoring
python3 make-network-policy.py
kubectl apply -f job-networkpolicy.json

K8S_API_SERVER="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
: "${K8S_API_SERVER:?Select the intended context}"
spark-submit \
  --master "k8s://${K8S_API_SERVER}" --deploy-mode cluster \
  --name "$SPARK_RUN_ID" --properties-file job.properties \
  --conf "spark.kubernetes.container.image=$SPARK_S3_IMAGE" \
  --conf "spark.kubernetes.driver.label.docs-job=$SPARK_RUN_ID" \
  --conf "spark.kubernetes.executor.label.docs-job=$SPARK_RUN_ID" \
  --conf spark.executor.instances=2 \
  --conf spark.driver.memory=1g --conf spark.executor.memory=1g \
  --class org.apache.spark.examples.SparkPi \
  local:///opt/spark/examples/jars/spark-examples.jar 10
```

これは**受信トラフィックの例**です。送信を制限する場合は、DNS、Kubernetes API、S3／STSまたはEKS Auth／認証情報エンドポイント、実際のデータソース経路も必要です。
NetworkPolicyを強制するCNIが必要であり、ポリシーは加算的に適用されます。
ほかの許可ポリシー、ノード／hostNetworkの動作、ラベルを偽装できるPod作成者も考慮してください。
ラベルは暗号学的に保証されたジョブアイデンティティではなく、すべての迂回を防ぐ保証もありません。

ポート7078／7079は固定されており、`port.maxRetries=0`では競合後に別ポートへ移動できません。
使用中のポートがあれば起動に失敗します。
Spark Connect、追加プラグイン、JMX exporterを使う場合は、それぞれ別のアクセス経路を設計してください。

## 5. Prometheus: 異なるエンドポイント

パート2のチャートメトリクスが示すのはOperator自身の情報であり、すべてのSpark JVMにJMX Agentを自動でインストールするわけではありません。
Java Agentは別の追加プロセスではなく、JVM内で動作します。

| 収集経路 | 意味 |
| --- | --- |
| Driver `/metrics/prometheus/` | PrometheusServletのDropwizardレジストリ。実験的と記載されている |
| Driver `/metrics/executors/prometheus/` | ドライバーが収集するエグゼキューターの集計値 |
| JmxSink＋JMX exporter | 選択したJVM MBean／exporterマッピング。JARと設定が必要 |

各エグゼキューターに個別のSpark UIがあるわけではありません。
これらのServlet／JMX経路では、利用可能な時系列、名前、ラベル、単位が同一とは限りません。
`spark.ui.prometheus.enabled`はエグゼキューター集計エンドポイントを制御し、既定は`true`です。
ドライバーのDropwizardエンドポイントは、別途上で述べたsink設定を使います。

次を`podmonitor.yaml`として保存します。
metadataのラベルとnamespaceは、実際のPrometheusの`podMonitorSelector`／`podMonitorNamespaceSelector`に合わせてください。
Collectorの検出に必要なRBACと、前述の受信ルールも一致させる必要があります。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: spark-drivers
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
    - spark-jobs
  selector:
    matchLabels:
      spark-role: driver
    matchExpressions:
    - key: docs-job
      operator: Exists
  podMetricsEndpoints:
  - port: spark-ui
    path: /metrics/prometheus/
    interval: 30s
  - port: spark-ui
    path: /metrics/executors/prometheus/
    interval: 30s
```

実際のtargetがUPで、両方の経路から期待する時系列が返ることを確認します。
短いジョブはスクレイプの間に終了する場合があります。
メトリクスの保持とイベントログは互いを補完します。Grafanaダッシュボードを流用する前に、実際の時系列、ラベル、単位を確認してください。

## 6. 完了後のジョブを調査する

ドライバーJVMが停止すると、Podオブジェクトが残っていてもライブUIは消えます。
History Serverが再構築するUIの情報源は**永続化されたイベントログ**であり、stdout／stderr、Structured Streamingチェックポイント、出力データ、復旧バックアップではありません。
イベントの欠落、削除、破損、不完全な書き込み、flush漏れがあると、再構築できる範囲が限られます。
再生コストはログ量と並列度によって異なり、compactionによってイベントが破棄される場合があります。
小さなレプリカを1つ用意すれば常に十分とは考えないでください。

イメージ、バケット、リージョンを置き換え、次を`history-server.yaml`として保存します。
ファイルをマウントしただけでは読み込まれません。**コマンドで`--properties-file`を指定して**明示的に読み込みます。
`spark-class`はフォアグラウンドで実行され、コンテナのライフサイクル管理に適しています。
S3アクセスには、上記で準備したHistory Server専用の読み取り専用IAMロールを使います。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: spark-history-config
  namespace: spark-jobs
data:
  history.properties: 'spark.history.fs.logDirectory=s3a://my-spark-bucket/spark-events/

    spark.hadoop.fs.s3a.aws.credentials.provider=software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider

    spark.hadoop.fs.s3a.endpoint.region=ap-northeast-2

    spark.history.ui.port=18080

    spark.history.fs.cleaner.enabled=false

    '
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spark-history
  namespace: spark-jobs
spec:
  replicas: 1
  selector:
    matchLabels:
      app: spark-history
  template:
    metadata:
      labels:
        app: spark-history
    spec:
      serviceAccountName: spark-data-history
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 185
        fsGroup: 185
      containers:
      - name: history
        image: registry.example.com/team/spark-s3:4.2.0
        command:
        - /opt/spark/bin/spark-class
        args:
        - org.apache.spark.deploy.history.HistoryServer
        - --properties-file
        - /etc/spark/history.properties
        ports:
        - name: http
          containerPort: 18080
        env:
        - name: SPARK_DAEMON_MEMORY
          value: 1g
        resources:
          requests:
            cpu: 250m
            memory: 1536Mi
          limits:
            cpu: '1'
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
        volumeMounts:
        - name: config
          mountPath: /etc/spark
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: spark-history-config
---
apiVersion: v1
kind: Service
metadata:
  name: spark-history
  namespace: spark-jobs
spec:
  type: ClusterIP
  selector:
    app: spark-history
  ports:
  - name: http
    port: 18080
    targetPort: http
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: spark-history-ingress
  namespace: spark-jobs
spec:
  podSelector:
    matchLabels:
      app: spark-history
  policyTypes:
  - Ingress
  ingress: []
```

```bash
# Replace the image, bucket, region and IAM role examples before applying.
kubectl apply -f history-server.yaml
kubectl -n spark-jobs rollout status deployment/spark-history --timeout=180s
kubectl -n spark-jobs logs deployment/spark-history
kubectl -n spark-jobs port-forward --address 127.0.0.1 service/spark-history 18080:18080
```

ローカルポート18080経由でアプリケーションを確認します。
ポートフォワードはコマンドが終了するまで有効で、診断用の経路です。
運用アクセスには、別途認証されたTLS経路を使ってください。
ClusterIPとSpark RPC認証では、UIユーザーを認証できません。

この例ではHistory Serverのcleanerを無効にしています。
S3のライフサイクル、保持、コストポリシーは別途設計してください。cleanerを有効にする場合は、削除権限、保持期間、ほかの利用者を確認します。
完了したジョブとNetworkPolicyを削除するときは、対象の実行IDだけを選んでください。

## 運用検証

実際のPodで、有効なAWSアイデンティティとS3プレフィックスの許可／拒否を検証します。
ドライバー終了後のHistory Serverアクセス、権限／ネットワーク障害、中断／再試行の挙動、データ復旧をテストします。
パート4のrequests／limitsとオーバーヘッドのモデルを使い、ドライバー／エグゼキューターのサイズを決めます。
検証済みの直接サブミット、Operator、EMRのライフサイクルと、適切なクライアント／クラスターモードを選択してください。Operatorまたはcluster modeを使うだけで、本番に必要な条件をすべて満たすわけではありません。

このレビューで確認したのは、ネイティブプロバイダーの生成、稼働中のSparkローカルメトリクスエンドポイント2つ、ジョブ終了後のイベントログ再生、YAML／ポリシーの意味です。
EKSへのデプロイ、S3権限テスト、イメージのビルド／公開、リモートエグゼキューターとの通信テストは含みません。

参考資料

- [Hadoop 3.5.0のS3A依存関係と認証情報](https://hadoop.apache.org/docs/r3.5.0/hadoop-aws/tools/hadoop-aws/index.html)
- [Hadoop 3.5.0の認証情報プロバイダーファクトリー](https://github.com/apache/hadoop/blob/rel/release-3.5.0/hadoop-tools/hadoop-aws/src/main/java/org/apache/hadoop/fs/s3a/auth/CredentialProviderListFactory.java)
- [EKS IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Spark 4.2のモニタリングとHistory Server](https://spark.apache.org/docs/4.2.0/monitoring.html)
- [SparkのエグゼキューターPrometheus設定](https://github.com/apache/spark/blob/v4.2.0/core/src/main/scala/org/apache/spark/internal/config/UI.scala)
- [Sparkのセキュリティ](https://spark.apache.org/docs/4.2.0/security.html)
- [Kubernetes NetworkPolicyの仕様](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes RBACとRoleBindingのスコープ](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

[README](./README.md)

[クイズ](../../quizzes/data-on-eks/spark/05-best-practices-quiz.md)
