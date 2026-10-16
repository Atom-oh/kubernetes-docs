# Pod と Workload クイズ

このクイズでは、Kubernetes の基本的な実行単位である Pod と、それらを管理するさまざまな Workload リソースについての理解を確認します。

## 多肢選択問題

1. Kubernetes でデプロイ可能なコンピューティング単位のうち、最小のものは何ですか？
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Node
   
<details>

<summary>回答を表示</summary>

**回答: B) Pod**

**解説:**
Pod は Kubernetes でデプロイ可能な最小のコンピューティング単位です。Pod は、ストレージとネットワークを共有し、一緒にスケジュールされる 1 つ以上の Container のグループです。Container は Pod に含まれるより小さな単位ですが、Kubernetes が直接管理するデプロイ単位ではありません。
</details>

2. 次のうち、Pod の特性では**ない**ものはどれですか？
   - A) Pod 内のすべての Container は同じ IP アドレスを共有する
   - B) Pod 内のすべての Container は常に同じ Node 上で実行される
   - C) Pod は複数の Node にまたがって実行できる
   - D) Pod には一意の IP アドレスがある
   
<details>

<summary>回答を表示</summary>

**回答: C) Pod は複数の Node にまたがって実行できる**

**解説:**
Pod 内のすべての Container は常に同じ Node 上で実行されます。Pod は複数の Node にまたがって実行することはできません。これは Pod の基本的な特性の 1 つであり、Pod 内の Container がローカルで通信し、Volume を共有することを可能にします。Pod 内のすべての Container は同じ network namespace を共有するため同じ IP アドレスを持ち、各 Pod は cluster 内で一意の IP アドレスを持ちます。
</details>

3. メイン Container の機能を補助 Container で拡張するマルチ Container Pod のパターンは何ですか？
   - A) Ambassador pattern
   - B) Sidecar pattern
   - C) Adapter pattern
   - D) Init pattern
   
<details>

<summary>回答を表示</summary>

**回答: B) Sidecar pattern**

**解説:**
Sidecar pattern では、メイン Container の機能を拡張する補助 Container を追加します。たとえば、ログコレクター、ファイル同期ツール、Proxy は Sidecar Container として実装できます。Ambassador pattern では外部 Service への Proxy として機能する Container を追加し、Adapter pattern ではメイン Container の出力を標準化する Container を追加し、Init pattern ではメイン Container の起動前に実行される Container を追加します。
</details>

4. Container がリクエストを処理する準備ができているかを確認し、失敗した場合に Service トラフィックから除外する Probe はどれですか？
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>回答を表示</summary>

**回答: B) readinessProbe**

**解説:**
readinessProbe は、Container がリクエストを処理する準備ができているかを確認し、失敗した場合に Service トラフィックから除外します。livenessProbe は Container が稼働中かを確認し、失敗した場合に再起動します。startupProbe は Container 内のアプリケーションが起動したかを確認し、成功するまで他の Probe を無効にします。healthProbe は Kubernetes には存在しません。
</details>

5. 次のうち、ReplicaSet の主な機能では**ない**ものはどれですか？
   - A) 指定された数の Pod Replica を維持する
   - B) Pod が失敗または削除されたときに、代替 Pod を自動的に作成する
   - C) Rolling Update を実行する
   - D) Label Selector によって管理する Pod を識別する
   
<details>

<summary>回答を表示</summary>

**回答: C) Rolling Update を実行する**

**解説:**
Rolling Update は ReplicaSet ではなく Deployment の主な機能であり、ReplicaSet では直接サポートされません。ReplicaSet の主な機能は、指定された数の Pod Replica の維持、Pod が失敗または削除されたときの代替 Pod の自動作成、および Label Selector による管理対象 Pod の識別です。Deployment は ReplicaSet を管理して、Rolling Update、Rollback、その他の機能を提供します。
</details>

6. 組み込みの Deployment 更新戦略では**ない**ものはどれですか？（2 つ選択してください。）
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>回答を表示</summary>

**回答: C) BlueGreen および D) Canary**

**解説:**
Kubernetes の Deployment は、デフォルトで RollingUpdate と Recreate の 2 つの更新戦略を提供します。BlueGreen と Canary はデプロイメントパターンですが、Deployment の更新戦略として直接提供されるものではありません。これらのパターンは、Service や Ingress などの他の Kubernetes リソース、または Argo Rollouts のような追加ツールを使用して実装できます。
</details>

7. 状態の永続化が必要なアプリケーション向けの Workload リソースはどれですか？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>回答を表示</summary>

**回答: C) StatefulSet**

**解説:**
StatefulSet は、状態の永続化が必要なアプリケーション向けの Workload リソースです。各 Pod に一意の識別子を割り当て、安定したネットワーク識別子と永続ストレージを提供します。データベース、分散システム、Message Queue など、状態を維持する必要があるアプリケーションに適しています。Deployment と ReplicaSet はステートレスなアプリケーション向けであり、DaemonSet はすべての Node 上で Pod のコピーが実行されることを保証します。
</details>

8. すべての（または特定の）Node 上で Pod のコピーが実行されることを保証する Workload リソースはどれですか？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>回答を表示</summary>

**回答: D) DaemonSet**

**解説:**
DaemonSet は、すべての（または特定の）Node 上で Pod のコピーが実行されることを保証します。Node が cluster に追加されると Pod も自動的に追加され、Node が削除されると Pod も削除されます。主に、ログコレクター、モニタリング Agent、ネットワーク Plugin などのバックグラウンド Service の実行に使用されます。Deployment と ReplicaSet は指定された数の Pod Replica を維持し、StatefulSet は状態の永続化が必要なアプリケーション向けです。
</details>

9. 1 回限りのタスクを実行するための Workload リソースはどれですか？
   - A) Deployment
   - B) Job
   - C) CronJob
   - D) DaemonSet
   
<details>

<summary>回答を表示</summary>

**回答: B) Job**

**解説:**
Job は、1 つ以上の Pod を作成し、指定された数の Pod が正常に終了するまで実行を継続する Workload リソースです。1 回限りのタスクの実行に使用されます。Deployment は継続的に実行するアプリケーション向けであり、CronJob はスケジュールに従って定期的に Job を実行し、DaemonSet はすべての Node 上で Pod のコピーを実行します。
</details>

10. スケジュールに従って定期的にタスクを実行する Workload リソースはどれですか？
    - A) Deployment
    - B) Job
    - C) CronJob
    - D) StatefulSet
    
<details>

<summary>回答を表示</summary>

**回答: C) CronJob**

**解説:**
CronJob は、指定されたスケジュールに従って定期的に Job を実行する Workload リソースです。Linux の cron Job と同様に動作し、バックアップ、レポート生成、メール送信などの定期タスクに使用されます。Deployment は継続的に実行するアプリケーション向けであり、Job は 1 回限りのタスクを実行し、StatefulSet は状態の永続化が必要なアプリケーション向けです。
</details>

## 短答問題

11. Pod 内の Container が起動する前に実行される特別な Container の名前は何ですか？

<details>

<summary>回答を表示</summary>

**回答: Init Container**

**解説:**
Init Container は、Pod 内のアプリ Container が起動する前に実行される特別な Container です。Init Container は定義された順序で 1 つずつ実行され、各 Init Container は前の Init Container が正常に完了した後にのみ起動します。Init Container が失敗した場合は、Pod の再起動ポリシーに従って再起動されます。主に、アプリ Container の起動前のセットアップ、依存関係の確認、権限設定に使用されます。
</details>

12. Pod が終了するとき、image/container で上書きされていない場合のデフォルトの停止シグナルは何ですか？

<details>

<summary>回答を表示</summary>

**回答: SIGTERM**

**解説:**
Pod が終了すると、kubelet は preStop hook を実行し、その後、デフォルトで runtime に SIGTERM を送信するよう要求します。hook は猶予期間の一部を消費します。image の STOPSIGNAL またはサポートされている Container の上書きにより、異なるシグナルを選択できます。これにより、アプリケーションは正常にシャットダウンするための時間を確保できます。Container がデフォルトの終了期間（30 秒）内に終了しない場合は、SIGKILL シグナルが送信されます。アプリケーションは SIGTERM シグナルを受信すると、進行中の作業を完了し、接続を閉じ、リソースをクリーンアップし、その他のタスクを実行できます。
</details>

13. Deployment が管理するリソースの名前は何ですか？

<details>

<summary>回答を表示</summary>

**回答: ReplicaSet**

**解説:**
Deployment は ReplicaSet を管理します。Deployment は ReplicaSet を作成し、ReplicaSet は Pod を作成して管理します。Deployment は ReplicaSet を通じて Rolling Update、Rollback、スケーリング、その他の機能を提供します。アプリケーションの新しいバージョンをデプロイするとき、Deployment は新しい ReplicaSet を作成し、以前の ReplicaSet を徐々にスケールダウンします。
</details>

14. StatefulSet 内の Pod に割り当てられる一意の識別子の形式は何ですか？（たとえば、StatefulSet 名が 'web' の場合）

<details>

<summary>回答を表示</summary>

**回答: \<StatefulSet name\>-\<ordinal index\> (e.g., web-0, web-1, web-2)**

**解説:**
StatefulSet は、Pod に `<StatefulSet name>-<ordinal index>` という形式の一意の識別子を割り当てます。たとえば、`web` StatefulSet は `web-0`、`web-1`、`web-2` のような Pod を作成します。この識別子は Pod が再スケジュールされた場合でも維持され、安定したネットワーク識別子と永続ストレージを提供するために使用されます。
</details>

15. CronJob で、以前の Job がまだ実行中の場合に新しい Job をスキップする並行実行ポリシーは何ですか？

<details>

<summary>回答を表示</summary>

**回答: Forbid**

**解説:**
CronJob の `Forbid` 並行実行ポリシーは、以前の Job がまだ実行中の場合に新しい Job をスキップします。CronJob は 3 つの並行実行ポリシーを提供します。`Allow`（複数の Job を同時に実行可能、デフォルト）、`Forbid`（以前の Job がまだ実行中の場合に新しい Job をスキップ）、`Replace`（以前の Job がまだ実行中の場合に新しい Job で置き換え）です。これらのポリシーは `concurrencyPolicy` フィールドで設定できます。
</details>

## ハンズオン問題

16. 次の要件を満たすマルチ Container Pod YAML ファイルを作成してください。
    - Pod 名: web-app
    - 1 つ目の Container: nginx Web Server（image: nginx:1.30.4）
    - 2 つ目の Container: ログコレクター（image: fluentd:v1.19-debian-1）
    - 2 つの Container 間でログディレクトリを共有するための emptyDir Volume
    - nginx Container は port 80 を公開する
    - ログ Volume は nginx Container では /var/log/nginx に、fluentd Container では /fluentd/log に mount する

<details>

<summary>回答を表示</summary>

**回答:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
spec:
  containers:
    - name: nginx
      image: nginx:1.30.4
      ports:
        - containerPort: 80
      volumeMounts:
        - name: log-volume
          mountPath: /var/log/nginx
    - name: log-collector
      image: fluentd:v1.19-debian-1
      volumeMounts:
        - name: log-volume
          mountPath: /fluentd/log
  volumes:
    - name: log-volume
      emptyDir: {}
```

**解説:**
この YAML ファイルは、nginx Web Server と fluentd ログコレクターを含むマルチ Container Pod を定義します。`log-volume` という名前の emptyDir Volume を作成し、nginx Container では `/var/log/nginx` に、fluentd Container では `/fluentd/log` に mount します。これによりファイルが共有されます。実際の収集には、`/fluentd/log/*.log` 用の Fluentd tail source と出力設定も必要です。nginx Container は port 80 を公開します。これは Sidecar pattern の例です。
</details>

17. 次の要件を満たす Deployment YAML ファイルを作成してください。
    - 名前: nginx-deployment
    - Label: app=nginx, tier=frontend
    - Replica 数: 3
    - Rolling Update 戦略: max surge 1、max unavailable 0
    - Container image: nginx:1.30.4
    - Container port: 80
    - Resource request: CPU 100m、memory 128Mi
    - Resource limit: CPU 200m、memory 256Mi
    - Liveness Probe: HTTP GET /、初期遅延 30 秒、間隔 10 秒
    - Readiness Probe: HTTP GET /、初期遅延 5 秒、間隔 5 秒

<details>

<summary>回答を表示</summary>

**回答:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: nginx
        tier: frontend
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.4
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5
```

**解説:**
この YAML ファイルは、nginx:1.30.4 image を使用する 3 Replica の Deployment を定義します。Rolling Update 戦略は、max surge 1（希望する数を超えて作成できる Pod の最大数）および max unavailable 0（更新中に利用不可にできる Pod の最大数）で構成され、ダウンタイムなしの更新を可能にします。各 Container は port 80 を公開し、CPU request 100m、memory request 128Mi、CPU limit 200m、memory limit 256Mi の Resource 制約を持ちます。Liveness Probe と Readiness Probe は、HTTP GET リクエストを通じて Container の状態を確認します。
</details>

18. 次の要件を満たす CronJob YAML ファイルを作成してください。
    - 名前: database-backup
    - Schedule: 毎日 UTC 午前 2 時に実行する（cron 式と timeZone を使用）
    - 並行実行ポリシー: Forbid
    - 成功した Job の履歴上限: 3
    - 失敗した Job の履歴上限: 1
    - Container image: postgres:14
    - Command: pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - 環境変数: PGHOST=postgres-service、postgres-secret から取得する PGUSER と PGPASSWORD
    - Volume: backup-pvc を /backup に mount する
    - 再起動ポリシー: OnFailure

<details>

<summary>回答を表示</summary>

**回答:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"
  timeZone: "Etc/UTC"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:14
              env:
                - name: PGHOST
                  value: postgres-service
                - name: PGUSER
                  valueFrom:
                    secretKeyRef:
                      name: postgres-secret
                      key: username
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: postgres-secret
                      key: password
              command:
                - /bin/sh
                - -c
                - pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          restartPolicy: OnFailure
          volumes:
            - name: backup-volume
              persistentVolumeClaim:
                claimName: backup-pvc
```

**解説:**
この YAML ファイルは、毎日午前 2 時に実行されるデータベースバックアップ CronJob を定義します。`concurrencyPolicy: Forbid` は、以前の Job がまだ実行中の場合に新しい Job をスキップします。`successfulJobsHistoryLimit: 3` と `failedJobsHistoryLimit: 1` は、成功した Job と失敗した Job の履歴をそれぞれ 3 件と 1 件に制限します。Container は postgres:14 image を使用し、pg_dump Command を実行してデータベースをバックアップします。環境変数 PGHOST は直接設定され、PGUSER と PGPASSWORD は postgres-secret から取得されます。バックアップファイルを保存するため、backup-pvc Volume は /backup ディレクトリに mount されます。再起動ポリシーは OnFailure に設定されているため、Job が失敗すると Container は再起動されます。
</details>

## 発展問題

19. Primary 1 台と Replica 2 台で構成される MySQL cluster に対して StatefulSet が提供する責務と、データベース Operator または Replication Controller が必要とする責務を説明してください。通常の Init Container からローカル MySQL server を構成するのが不適切である理由は何ですか？

<details>
<summary>回答を表示</summary>

**回答:**

- StatefulSet は、安定した Pod 名、governing headless Service、Pod ごとの PVC、およびデフォルトで順序付けられたスケーリングを提供します。ストレージの可用性を前提として、失敗した Pod を同じ ordinal とストレージで置き換えます。
- StatefulSet は、データベースデータのコピー、Replication の構成、Primary の選出または昇格、古い Primary のフェンシング、データベース Client のリダイレクトを行いません。検証済みのデータベース Operator/runbook が、これらの動作、Replication の認証情報、バックアップ、リストア確認を実装する必要があります。
- 通常の Init Container は、ローカルのアプリケーション Container が起動する前に完了します。Init Container からローカル SQL 接続を試みても、まだ起動していない MySQL server を構成することはできません。Replication のセットアップは、適切なデータベースライフサイクルの段階で実行する必要があります。
- 独立した 3 台の MySQL Pod は、Replication された HA データベースではありません。Replica 間で同じ server ID を再利用したり、ConfigMap に Replication password を埋め込んだりすることも不適切です。
- Kubernetes の identity/storage の配線については、この章の single-instance StatefulSet の例を参照してください。3 台にスケールして Replication や自動フェイルオーバーがあると主張してはいけません。

</details>

20. さまざまな Workload リソース（Deployment、StatefulSet、DaemonSet、Job、CronJob）の特性とユースケースを比較し、次のシナリオに最も適切な Workload リソースを選択して、その理由を説明してください。
    - Web アプリケーションの Frontend
    - 分散データベース cluster
    - ログ収集 Agent
    - 毎日のデータバックアップ
    - 1 回限りのデータ移行

<details>

<summary>回答を表示</summary>

**回答:**

**Workload リソースの比較**

| Workload リソース | 主な特性 | ユースケース |
|--------------|---------|---------|
| **Deployment** | - ステートレスなアプリケーション<br>- Rolling Update のサポート<br>- Auto Scaling<br>- ReplicaSet の管理 | - Web Server<br>- API Server<br>- ステートレスな Microservice<br>- Frontend アプリケーション |
| **StatefulSet** | - 安定したネットワーク識別子<br>- 永続ストレージ<br>- 順次デプロイとスケーリング<br>- 順序付けられた Pod 作成を保証 | - データベース<br>- 分散システム<br>- Message Queue<br>- ステートフルなアプリケーション |
| **DaemonSet** | - すべての Node 上で実行<br>- Node 追加時の自動デプロイ<br>- Node 削除時の自動クリーンアップ<br>- Node 選択が可能 | - ログコレクター<br>- モニタリング Agent<br>- ネットワーク Plugin<br>- ストレージ Daemon |
| **Job** | - 1 回限りのタスク<br>- 完了の追跡（失敗する可能性あり）<br>- 並列実行が可能<br>- 失敗時の再試行 | - Batch 処理<br>- データ移行<br>- コンピューティングタスク<br>- 1 回限りの管理タスク |
| **CronJob** | - Schedule ベースの実行<br>- 定期タスク<br>- 並行実行ポリシー<br>- 履歴上限 | - スケジュールされたバックアップ<br>- データ同期<br>- レポート生成<br>- クリーンアップタスク |

**シナリオ別の適切な Workload リソース**

1. **Web アプリケーションの Frontend**
  - **適切なリソース: Deployment**
  - **理由**: Web アプリケーションの Frontend は通常ステートレスなアプリケーションです。Deployment は Rolling Update によってダウンタイムなしで新しいバージョンをデプロイでき、水平スケーリングが容易で、自動復旧を提供します。また、HorizontalPodAutoscaler と組み合わせて、トラフィックに基づいて自動スケーリングすることもできます。

2. **分散データベース cluster**
  - **適切なリソース: StatefulSet**
  - **理由**: 分散データベースでは状態の永続化が必要であり、各インスタンスには一意の識別子と永続ストレージが必要です。StatefulSet は安定したネットワーク識別子（`<StatefulSet name>-<ordinal index>`）と永続ストレージを提供し、順序付けられたデプロイとスケーリングをサポートします。データベースは Replication と整合性を実装する必要があります。MySQL、PostgreSQL、MongoDB、Cassandra などの分散データベース cluster に適しています。

3. **ログ収集 Agent**
  - **適切なリソース: DaemonSet**
  - **理由**: ログ収集 Agent は cluster 内のすべての Node 上で実行する必要があります。DaemonSet は、すべての（または特定の）Node 上で Pod のコピーが実行されることを保証し、新しい Node が cluster に追加されるとログ収集 Agent を自動的にデプロイします。Fluentd、Logstash、Filebeat などのログ収集 Agent のデプロイに適しています。

4. **毎日のデータバックアップ**
  - **適切なリソース: CronJob**
  - **理由**: 毎日のデータバックアップは、設定されたスケジュールに従って定期的に実行する必要があるタスクです。CronJob は cron 式を使用して実行 Schedule を指定でき、毎日特定の時刻にバックアップタスクを実行するよう設定できます。また、`concurrencyPolicy` を通じて以前のバックアップがまだ実行中の場合の動作を定義でき、Job の履歴を制限できます。バックアップファイルの保持には別のポリシーが必要です。

5. **1 回限りのデータ移行**
  - **適切なリソース: Job**
  - **理由**: データ移行は、正常に完了する必要がある 1 回限りのタスクです。Job は指定された数の Pod が正常に終了するまで実行を継続し、失敗時の再試行メカニズムを提供します。さらに、大規模なデータ移行は、`parallelism` 設定を通じて複数の Pod を並列で実行することで、より高速に処理できます。

**結論**

各 Workload リソースは特定のユースケース向けに設計されているため、アプリケーション要件に基づいて適切なリソースを選択することが重要です。Deployment はステートレスなアプリケーション、StatefulSet は状態の永続化が必要なアプリケーション、DaemonSet はすべての Node 上で実行する必要がある Service、Job は 1 回限りのタスク、CronJob は定期タスクに適しています。これらの特性を理解し、適切な Workload リソースを選択することで、Kubernetes で効率的にアプリケーションを管理できます。
</details>

---

[学習教材に戻る](../../core/02-pods-and-workloads.md) | [次のクイズ: Services と Networking](../core/03-services-networking-quiz.md)