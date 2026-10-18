# パート1: Kubernetes 上で Spark を実行する基礎

> **レビュー基準**: Spark 4.2.0、Kubernetes 1.34 以降。例で使うイメージは Java 21 を使用\
> **最終確認日**: 2026年9月12日

## クラスターモードとクライアントモード

Kubernetes では Spark の**両方のデプロイモード**を利用できます。クライアントモードは Spark 2.4 からサポートされており、Notebook 専用ではありません。

| モード | Driver の配置場所 | 運用上の影響 |
| --- | --- | --- |
| クラスター | ジョブ投入ごとに作成される driver Pod | ジョブ投入元には API へのアクセス権が必要です。driver には専用のサービスアカウントと RBAC が必要です。 |
| クライアント | Pod 内またはホスト上で動作するジョブ投入アプリケーション | executor は driver が通知する RPC／block-manager エンドポイントに接続できる必要があります。driver を稼働させ続けてください。 |

Kubernetes API に到達できても、executor と driver の接続が成立するとは限りません。クライアントモードのネットワークでは、安定した Service／hostname と固定 port が必要な場合があります。driver が Pod 内で動く場合、executor の owner-reference garbage collection には**実際の** driver Pod 名を設定してください。Kubernetes 外で動く driver に Pod owner をでっち上げてはいけません。

## 何が何をスケジュールするか

API server は認証と admission を処理し、API object を保存します。Kubernetes scheduler が Pod を配置し、node kubelet が container を起動します。Spark driver は executor Pod を要求し、登録済み executor 上で stage／task を調整する Spark scheduler を動かします。これらは別々のレイヤーです。

![クラスター配置モード: ジョブ投入元と driver が Pod API object を作成し、Kubernetes scheduler と kubelet が container を配置／起動する。driver は別途 Spark task を割り当てる。](../../.gitbook/assets/en-data-on-eks-spark-01-spark-fundamentals-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-spark-01-spark-fundamentals-0.html)

1. ジョブ投入元が driver Pod と関連リソースを要求します。
2. Kubernetes が driver を配置して起動し、driver が executor Pod を要求します。
3. Kubernetes が executor を配置して起動し、executor は driver に登録します。
4. driver が Spark task を割り当て、executor は task を実行して結果と状態を報告します。
5. 正常終了時、Spark は設定に応じて executor をクリーンアップします。ログを確認できるよう、完了または失敗した driver Pod が残る場合があります。すべてが直ちに削除されると想定せず、失敗時の挙動と owner reference を考慮してください。

YARN や Spark Standalone という別個の制御レイヤーは不要になりますが、Kubernetes の容量、node、storage、network、image の運用は引き続き必要です。

## クラスターモードの具体例

前提条件: ローカル環境の Spark 4.2.0、互換性のある kubectl、現在選択中の kubeconfig context、Kubernetes 1.34 以降、namespace のリソース容量、image を取得する権限が必要です。ジョブ投入元の API 認証情報と、クラスター内の driver に適用される RBAC は別々です。SparkPi の例に AWS 上のデータへの権限は不要ですが、S3 を使う workload には選択した workload identity と互換性のある Hadoop／AWS library が必要です。

namespace 管理者が `rbac.yaml` を確認して適用します。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: spark-jobs
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-driver
  namespace: spark-jobs
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-executor
  namespace: spark-jobs
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: spark-driver
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
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: spark-driver
  namespace: spark-jobs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: spark-driver
subjects:
- kind: ServiceAccount
  name: spark-driver
  namespace: spark-jobs
```

この Role は、PVC を動的作成しない基本例に必要な権限を備えています。追加の volume／resource 管理機能では、それに対応する範囲限定の権限が必要になる場合があります。executor Pod には、API token の自動 mount を無効にした別のサービスアカウントを使います。driver が Pod を作成できる namespace では、信頼できるジョブコード／ジョブ投入元だけを許可してください。RBAC だけでは、信頼できないアプリケーションコードを隔離できません。

これらは `kubectl apply` で単独の Pod として適用するのではなく、**Pod template** として保存します。Spark がイメージやコマンドなどのフィールドを補完します。

driver template、`driver-template.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: spark-driver-template
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 185
    runAsGroup: 185
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: spark-kubernetes-driver
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

executor template、`executor-template.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: spark-executor-template
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 185
    runAsGroup: 185
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: spark-kubernetes-executor
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
  automountServiceAccountToken: false
  terminationGracePeriodSeconds: 60
```

これらのファイルには、**ジョブ投入を実行するプロセス**からアクセスできる必要があります。クラスターモードでは、Spark が executor template を driver 内に mount します。Spark が template の field の一部を上書きするため、template、operator webhook、Spark 設定を組み合わせる場合は、生成された Pod を調べてください。

```bash
#!/bin/bash
set -euo pipefail
# Run in the directory containing driver-template.yaml and executor-template.yaml.
KUBE_CONTEXT="$(kubectl config current-context)"
KUBE_API_URL="$(kubectl --context "$KUBE_CONTEXT" config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
case "$KUBE_API_URL" in https://*) ;; *) echo "Expected an HTTPS Kubernetes API URL" >&2; exit 1;; esac
SPARK_APP_NAME="spark-pi-$(date -u +%Y%m%d%H%M%S)"
spark-submit \
  --master "k8s://${KUBE_API_URL}" \
  --deploy-mode cluster \
  --name "$SPARK_APP_NAME" \
  --class org.apache.spark.examples.SparkPi \
  --conf "spark.kubernetes.context=$KUBE_CONTEXT" \
  --conf spark.kubernetes.namespace=spark-jobs \
  --conf spark.kubernetes.container.image=spark:4.2.0-scala2.13-java21-ubuntu \
  --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark-driver \
  --conf spark.kubernetes.authenticate.executor.serviceAccountName=spark-executor \
  --conf "spark.kubernetes.driver.pod.name=$SPARK_APP_NAME-driver" \
  --conf spark.kubernetes.driver.podTemplateFile=driver-template.yaml \
  --conf spark.kubernetes.executor.podTemplateFile=executor-template.yaml \
  --conf spark.kubernetes.executor.terminationGracePeriodSeconds=60s \
  --conf spark.driver.cores=1 \
  --conf spark.driver.memory=1g \
  --conf spark.kubernetes.driver.limit.cores=1 \
  --conf spark.executor.cores=1 \
  --conf spark.executor.memory=1g \
  --conf spark.kubernetes.executor.limit.cores=1 \
  --conf spark.executor.instances=3 \
  local:///opt/spark/examples/jars/spark-examples.jar 10
kubectl -n spark-jobs logs "$SPARK_APP_NAME-driver"
kubectl -n spark-jobs get pod "$SPARK_APP_NAME-driver" -o jsonpath='{.status.phase}{"\n"}'
```

ジョブ投入 script を実行する前に `rbac.yaml` を適用してください。バージョンを固定した公式 image には `spark-examples.jar` の symlink が含まれます。`local:///` は artifact が container 内にすでにあるという意味であり、ローカル PC のファイルを upload するという意味ではありません。必要に応じて、通常のソフトウェアサプライチェーン手順に従い image を mirror／pin してください。補助 script は一意な driver 名と選択した kubeconfig context を使用します。障害調査に備え、これらの値を記録してください。

executor を3つ固定で要求していますが、quota、admission、scheduling、イメージ取得、node の容量によって Pod が Pending のままになることがあります。driver／executor の event と log を確認してください。`spark-submit` の実行だけでは、task が正常に実行された証拠になりません。

## リソースの request、limit、task slot

| Spark 設定 | Kubernetes／既定プロファイルへの影響 |
| --- | --- |
| `spark.driver.cores` | 上書きしない限り、driver の CPU request |
| `spark.executor.cores` | executor の task 実行数と既定の CPU request |
| `spark.kubernetes.{driver,executor}.request.cores` | Kubernetes の CPU request を上書きしますが、executor の Spark task-slot 設定は変えません |
| `spark.kubernetes.{driver,executor}.limit.cores` | CPU limit を明示します。cores を設定しただけで CPU limit が自動設定されるわけではありません |
| driver memory | request と limit には heap と、設定または計算された overhead が含まれます |
| executor memory | request と limit には heap、overhead、該当する off-heap／PySpark memory が含まれます |

この JVM 例では、heap 1 GiB に既定の最小 overhead 384 MiB を加えるため、memory request／limit は **1,408 MiB** になります。これは検証済みの既定値に基づく計算であり、すべての job に適用できるサイズではありません。Python／native memory と独自 ResourceProfile は別途確認してください。task 実行数より小さい CPU request では、CPU 競合が起きる可能性があります。request を変更することと、executor が実行できる Spark task 数を変更することは別です。

## 動的リソース割り当て

Spark DRA は task の滞留／待機状態に応じて**executor 数**を変更します。デバイス向けの Kubernetes DRA や、Pending Pod に応じて動作する node autoscaler とは別の機能です。

Kubernetes 上の標準 Spark は、YARN 形式の external shuffle service をサポートしません。Shuffle tracking は選択肢の1つですが、Spark で利用できる方法はそれだけではありません。decommission による shuffle 保持や、要件を満たす信頼性の高い ShuffleDataIO 実装も代替手段であり、それぞれに条件があります。

shuffle tracking を使うプロファイルの例:

```properties
spark.dynamicAllocation.enabled=true
spark.dynamicAllocation.shuffleTracking.enabled=true
spark.dynamicAllocation.minExecutors=2
spark.dynamicAllocation.initialExecutors=3
spark.dynamicAllocation.maxExecutors=20
spark.kubernetes.allocation.batch.size=5
```

これらの property は `--conf` または properties file で指定します。Shuffle tracking は Spark 3.0 で導入され、**Spark 4.2 ではすでに既定で有効**です。ここで明示するのは選択を記録するためです。2つの flag を常に明示しなければならないという以前の説明は正しくありません。

Shuffle tracking は、稼働中の shuffle data を持つ executor を保持しようとします。設定された tracking／cached-executor の idle timeout、強制終了、node の障害によって再計算が必要になる場合があります。これは永続的な共有ストレージではありません。複数の保持機能を重ねて有効にすると executor の解放が遅れることがあるため、組み合わせて動作をテストしてください。

初期 executor 数は `minExecutors`、`initialExecutors`、既存の `spark.executor.instances` の値を考慮します。この例では、固定数3と初期数3が一致します。`min=2` は最初に2つだけ起動するという意味ではありません。

`spark.kubernetes.allocation.batch.size` は Pod 要求の batch 数を制御します。EC2 の scale policy を直接設定するものではありません。API throttling、Pod 割り当てのタイミング、ResourceQuota、scheduling 制約、node の起動は別々の要素です。

## Graceful decommission はベストエフォート

以下の設定で executor／block-manager の decommission と、対象となる RDD／shuffle block の移行を有効にします。

```properties
spark.decommission.enabled=true
spark.storage.decommission.enabled=true
spark.storage.decommission.rddBlocks.enabled=true
spark.storage.decommission.shuffleBlocks.enabled=true
spark.kubernetes.executor.terminationGracePeriodSeconds=60s
```

選択した Spark 4.2 の Kubernetes 経路では、decommission を有効にすると `spark.kubernetes.decommission.script`（既定値は `/opt/decom.sh`）を実行する **preStop hook** が挿入されます。公式 image にはこの script が含まれます。script は executor JVM を見つけて **SIGPWR** を送信し、待機します。Spark の既定 decommission signal は PWR です。通常の Pod 終了はこの hook を介するため、通常の SIGTERM だけで必ずデータが移行すると想定してはいけません。

独自 image には正常に動作する script と必要な tool が必要です。signal を変更する場合は、script 側も合わせてください。Spark が template の lifecycle 設定を上書きすることがあります。実際の hook を確認し、計画的な scale-down と interruption の両方をテストしてください。

ジョブ投入では `spark.kubernetes.executor.terminationGracePeriodSeconds=60s` を明示します。Spark 4.2 は Pod template の値をこの設定で上書きし、その既定値は30秒です。template に `terminationGracePeriodSeconds: 60` だけを設定しても不十分です。

猶予時間には preStop の実行時間が含まれます。この時間は利用できる最大枠であり、データ移行の完了を約束するものでも、基盤となる Spot termination deadline を遅らせるものでもありません。正常な移行先 executor、disk／network の容量、時間、設定済みの fallback storage が必要です。node の突然の喪失や強制削除では、この機会自体が失われることがあります。

Spark の dynamic-allocation delete 経路を含む、明示的な deletion-grace 設定によって、利用できる時間が変わる場合もあります。

これらの flag は、失敗した driver の再起動、application checkpoint の代替、end-to-end exactly-once output の保証を行うものではありません。再計算できる中間 block と永続的な入出力を区別し、適切な復旧を計画してください。

## 参考資料と検証

driver を loopback に bind し、UI を無効にしたローカルでの SparkPi job は正常に実行されました。Native Spark 4.2 の feature-step test では、memory の対応付け、CPU limit の既定動作、Kubernetes client を作成せずに decommission hook が自動挿入されることを確認しました。これらの確認は、EKS へのジョブ投入、RBAC／CNI の適用、実際のデータ移行完了、AWS 上のデータへのアクセスを証明するものではありません。

- [Kubernetes 上の Spark 4.2.0](https://spark.apache.org/docs/4.2.0/running-on-kubernetes.html)
- [Spark 4.2.0 の設定](https://spark.apache.org/docs/4.2.0/configuration.html)
- [Spark 4.2.0 の動的割り当ての代替方式](https://spark.apache.org/docs/4.2.0/job-scheduling.html#dynamic-resource-allocation)
- [Driver resource の対応付け](https://github.com/apache/spark/blob/v4.2.0/resource-managers/kubernetes/core/src/main/scala/org/apache/spark/deploy/k8s/features/BasicDriverFeatureStep.scala)
- [Executor resource と decommission hook](https://github.com/apache/spark/blob/v4.2.0/resource-managers/kubernetes/core/src/main/scala/org/apache/spark/deploy/k8s/features/BasicExecutorFeatureStep.scala)
- [公式 decommission script](https://github.com/apache/spark/blob/v4.2.0/resource-managers/kubernetes/docker/src/main/dockerfiles/spark/decom.sh)
- [公式 Spark image tag](https://github.com/docker-library/official-images/blob/master/library/spark)

## 次のステップ

[パート2: Spark Operator](./02-spark-operator.md)

[メインページに戻る](./README.md)

## クイズ

[トピック別クイズ](../../quizzes/data-on-eks/spark/01-spark-fundamentals-quiz.md)
