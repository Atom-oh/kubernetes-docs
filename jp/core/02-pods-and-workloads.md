# Kubernetes Podとワークロード

> **サポート対象バージョン**: Kubernetes 1.35、1.36、1.37
> **最終更新日**: 2026年10月12日

このドキュメントでは、Kubernetesにおける基本的な実行単位であるPodと、それらを管理するさまざまなワークロードリソースについて詳しく説明します。Podの概念から始めて、Deployment、StatefulSet、DaemonSetなど、さまざまなワークロードリソースの特性とユースケースを取り上げます。

## ラボ環境のセットアップ

このドキュメントの例を試すには、以下のツールと環境が必要です。

### 必要なツール
- APIサーバーとマイナーバージョンが1つ以内のkubectl
- 動作するKubernetesクラスター（EKS、minikube、kindなど）

### サンプルアプリケーションのデプロイ

```bash
# Create namespace
kubectl create namespace workloads-demo

# Create a simple deployment
kubectl -n workloads-demo apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
EOF

# Check deployment status
kubectl -n workloads-demo get deployments,pods
```

## 目次
- [Podの概念](#pod-concepts)
- [Podのライフサイクル](#pod-lifecycle)
- [Podの設計パターン](#pod-design-patterns)
- [ワークロードリソースの概要](#workload-resources-overview)
- [ReplicaSet](#replicaset)
- [Deployment](#deployment)
- [StatefulSet](#statefulset)
- [DaemonSet](#daemonset)
- [JobとCronJob](#jobs-and-cronjobs)

## Podの概念

> **重要な概念**: PodはKubernetesでデプロイ可能な最小のコンピューティング単位であり、ストレージとネットワークを共有する1つ以上のコンテナで構成されます。

PodはKubernetesでデプロイ可能な最小のコンピューティング単位です。Podは、ストレージとネットワークを共有し、まとめてスケジュールされる1つ以上のコンテナのグループです。

### Podの特性

1. **コンテキストの共有**: コンテナはPodのネットワークと通常はIPCを共有します。プロセス名前空間の共有には`shareProcessNamespace: true`が必要です。コンテナのルートファイルシステムは個別に保たれます。
2. **同じNode**: Pod内のすべてのコンテナは、常に同じNodeで実行されます。
3. **一意のIPアドレス**: 各Podにはクラスター内で一意のIPアドレスが割り当てられます。
4. **一時的な存在**: Podは本質的に一時的なものであり、障害が発生した場合は新しいPodに置き換えられることがあります。
5. **原子的な単位**: Podはデプロイ、スケジューリング、レプリケーションにおける原子的な単位です。

### Podの構造

Podは次のコンポーネントで構成されます。

1. **コンテナ**: Pod内で実行される1つ以上のコンテナ
2. **ボリューム**: Pod内のコンテナ間で共有されるストレージ
3. **ネットワーク**: Podに割り当てられるIPアドレスとポート
4. **コンテナ仕様**: コンテナイメージ、環境変数、リソース要件など

![Kubernetes Podの境界を示す図。アプリケーションコンテナ、サイドカーコンテナ、Initコンテナが1つのPodのIPアドレスとネットワーク名前空間を共有し、マウント可能な4種類のストレージボリューム（emptyDir、configMap、secret、persistentVolumeClaim）も示されています。](../.gitbook/assets/en-core-02-pods-and-workloads-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-core-02-pods-and-workloads-0.html)

### Podの例

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multi-container-pod
  labels:
    app: web
spec:
  containers:
  - name: web
    image: nginx:1.30.6
    ports:
    - containerPort: 80
    volumeMounts:
    - name: shared-data
      mountPath: /usr/share/nginx/html
  - name: content-updater
    image: alpine
    command: ["/bin/sh", "-c"]
    args:
    - |
      while true; do
        echo "Current time: $(date)" > /content/index.html;
        sleep 10;
      done
    volumeMounts:
    - name: shared-data
      mountPath: /content
  volumes:
  - name: shared-data
    emptyDir: {}
```

### 実例: WebアプリケーションPod

以下は、Webアプリケーションとサイドカーコンテナを含むPodの例です。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
  labels:
    app: web
    environment: production
spec:
  containers:
  - name: web-application
    image: nginx:1.30.6
    volumeMounts:
    - name: log-volume
      mountPath: /var/log/nginx
    ports:
    - containerPort: 80
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
  - name: log-collector
    image: fluentd:v1.19-debian-1
    volumeMounts:
    - name: log-volume
      mountPath: /var/log/nginx
    resources:
      requests:
        memory: "64Mi"
        cpu: "50m"
      limits:
        memory: "128Mi"
        cpu: "100m"
  volumes:
  - name: log-volume
    emptyDir: {}
```

この例では、実際のシナリオとして以下を示しています。
- Nginx Webサーバーをメインコンテナとして実行する
- Fluentdログコレクターをサイドカーコンテナとして実行する
- 2つのコンテナ間でログボリュームを共有する
- 各コンテナのリソース要求と上限を設定する

この構成は、マイクロサービスアーキテクチャで、ロギング、監視、プロキシなどの機能を分離しながら、密接に連携するコンテナを実行するのに適しています。

これらのロギング用マニフェストは、ボリュームの接続方法を示しています。Fluentdでログを収集するには、明示的なtailソースと出力の設定も必要です。ディレクトリをマウントするだけではログは収集されません。イメージとアプリケーション設定は説明用であり、本番環境で使用するバージョンの推奨ではありません。ネイティブサイドカーは`restartPolicy: Always`を指定した`initContainers`を使用します（v1.33以降安定版）。通常の複数コンテナPodでは、起動順序やシャットダウン順序は保証されません。

### Podの定義

PodはYAMLまたはJSON形式のマニフェストファイルを使って定義します。基本的なPod定義の例を示します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels:
    app: nginx
spec:
  containers:
  - name: nginx
    image: nginx:1.30.6
    ports:
    - containerPort: 80
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

### 単一コンテナPodと複数コンテナPod

**単一コンテナPod**:
- 最も一般的なユースケース
- アプリケーションコンテナを1つだけ含む
- 構造がシンプルで直感的

**複数コンテナPod**:
- 密接に連携する複数のコンテナを含む
- コンテナ間のローカル通信が可能（localhost）
- 共有ボリュームによるデータ共有
- まとめてスケーリング、配置される

### 複数コンテナPodのパターン

1. **サイドカーパターン**: メインコンテナの機能を拡張する補助コンテナ
   - 例: ログコレクター、ファイル同期、プロキシ

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-with-sidecar
spec:
  containers:
  - name: web
    image: nginx:1.30.6
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  - name: log-collector
    image: fluentd:v1.19-debian-1
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  volumes:
  - name: logs
    emptyDir: {}
```

2. **アンバサダーパターン**: 外部サービスへのプロキシとして機能するコンテナ
   - 例: データベースプロキシ、サービスメッシュのサイドカー

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-ambassador
spec:
  containers:
  - name: app
    image: myapp:1.0
  - name: ambassador
    image: envoyproxy/envoy:v1.20.0
    ports:
    - containerPort: 9901
```

3. **アダプターパターン**: メインコンテナの出力を標準化するコンテナ
   - 例: ログ形式の変換、メトリクスの変換

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-adapter
spec:
  containers:
  - name: app
    image: myapp:1.0
    volumeMounts:
    - name: app-logs
      mountPath: /var/log/app
  - name: adapter
    image: adapter:1.0
    volumeMounts:
    - name: app-logs
      mountPath: /var/log/app
  volumes:
  - name: app-logs
    emptyDir: {}
```

4. **Initコンテナパターン**: メインコンテナの起動前に実行されるコンテナ
   - 例: 設定ファイルの作成、データベースのマイグレーション、権限の設定

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: init-db
    image: busybox:1.34
    command: ['sh', '-c', 'until nslookup db; do echo waiting for db; sleep 2; done;']
  containers:
  - name: app
    image: myapp:1.0
```

### Podのネットワーク

Pod内のコンテナには、次のネットワーク特性があります。

1. **同じIPアドレス**: Pod内のすべてのコンテナは同じIPアドレスを共有します。
2. **ポートの共有**: Pod内のコンテナはポート空間を共有するため、通常、同じIPアドレス、プロトコル、ポートの組み合わせにバインドすることはできません。
3. **localhost通信**: Pod内のコンテナはlocalhost経由で相互に通信できます。
4. **Pod間通信**: 各Podには一意のIPアドレスが割り当てられ、他のPodと直接通信できます。

### Podのストレージ

Podでは、データの保存や共有にさまざまな種類のボリュームを使用できます。

1. **emptyDir**: Podの作成時に作成され、Podの削除時に削除される一時ボリューム
2. **hostPath**: ホストNodeのファイルシステムからPodにマウントされるボリューム
3. **persistentVolumeClaim**: 永続ストレージを要求するボリューム
4. **configMap**: ボリュームとしてマウントされたConfigMap
5. **secret**: ボリュームとしてマウントされたSecret
6. **projected**: 複数のボリュームソースを同じディレクトリにマッピングするもの

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-volumes
spec:
  containers:
  - name: app
    image: myapp:1.0
    volumeMounts:
    - name: data
      mountPath: /data
    - name: config
      mountPath: /etc/config
  volumes:
  - name: data
    emptyDir: {}
  - name: config
    configMap:
      name: app-config
```

## Podのライフサイクル

Podは作成から終了まで、さまざまなライフサイクル段階を経ます。アプリケーションの安定性と可用性を確保するには、このライフサイクルを理解することが重要です。

### Podのフェーズ

Podは次のフェーズを経ます。

1. **Pending**: Podはクラスターに受け付けられていますが、1つ以上のコンテナのセットアップがまだ完了していません。
2. **Running**: PodはNodeに割り当てられ、すべてのコンテナが作成されており、少なくとも1つのコンテナが実行中、起動中、または再起動中です。
3. **Succeeded**: Pod内のすべてのコンテナが正常に終了しており、再起動されません。
4. **Failed**: Pod内のすべてのコンテナが終了しており、少なくとも1つのコンテナが失敗して終了しています。
5. **Unknown**: 何らかの理由でPodの状態を取得できませんでした。

### コンテナの状態

Pod内の各コンテナは、次の状態をとることがあります。

1. **Waiting**: コンテナが実行される前の状態（イメージのダウンロード中、依存関係の待機中など）
2. **Running**: プロセスが実行中の状態。ただし、これだけではアプリケーションの健全性や準備完了を示しません。
3. **Terminated**: コンテナの実行が完了したか、何らかの理由で失敗した状態

### PodのConditions

Podは、次のConditionsによって状態をより詳細に示します。

1. **PodScheduled**: PodがNodeにスケジュールされたかどうか
2. **ContainersReady**: Pod内のすべてのコンテナが準備完了かどうか
3. **Initialized**: 通常のInitコンテナが完了し、再起動可能なInitコンテナ（ネイティブサイドカー）が起動したかどうか
4. **Ready**: Podがリクエストを処理でき、Serviceの負荷分散プールに追加できるかどうか

### コンテナのProbe

Kubernetesには、コンテナの状態を確認するためのProbeが用意されています。

1. **livenessProbe**: コンテナが生存しているかを確認し、失敗時にはコンテナを再起動します。
2. **readinessProbe**: コンテナがリクエストを処理する準備ができているかを確認し、失敗時にはServiceのトラフィック対象から除外します。
3. **startupProbe**: コンテナ内のアプリケーションが起動したかを確認し、成功するまで他のProbeを無効にします。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-probes
spec:
  containers:
  - name: app
    image: myapp:1.0
    ports:
    - containerPort: 8080
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
    startupProbe:
      httpGet:
        path: /startup
        port: 8080
      failureThreshold: 30
      periodSeconds: 10
```

### Podの終了プロセス

Podを終了すると、次のプロセスが実行されます。

1. **APIサーバーへの削除リクエスト**: ユーザーまたはコントローラーがPodの削除を要求します。
2. **終了猶予期間の開始**: デフォルトの終了猶予期間（30秒）が設定されます。
3. **APIの更新**: APIサーバーがPodの削除タイムスタンプを更新します。
4. **Endpointの更新**: EndpointSliceはEndpointを終了中かつ未準備としてマークします。これとNodeのシャットダウンへの反映は並行して行われます。
5. **停止シグナル**: kubeletは猶予期間内にpreStopフックを実行し、その後ランタイムに停止シグナルを送信するよう依頼します（通常はSIGTERM。ただし、イメージまたはコンテナによって上書きされている場合を除きます）。
6. **正常なシャットダウンの待機**: アプリケーションが正常にシャットダウンするための時間が与えられます。
7. **SIGKILLシグナル**: 終了猶予期間の経過後もコンテナが終了しない場合、SIGKILLシグナルが送信されます。
8. **リソースのクリーンアップ**: kubeletがPodのリソースをクリーンアップします。

### Initコンテナ

Initコンテナは、Pod内のアプリコンテナが起動する前に実行される特別なコンテナです。

1. **順次実行**: Initコンテナは、定義された順序で1つずつ実行されます。
2. **前提条件**: 各Initコンテナは、前のコンテナが正常に完了した後にのみ起動します。
3. **失敗時の再起動**: Initコンテナが失敗した場合、Podの再起動ポリシーに従って再起動されます。
4. **目的**: アプリコンテナの起動前のセットアップ、依存関係の確認、権限の設定など

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: init-pod
spec:
  initContainers:
  - name: init-myservice
    image: busybox:1.34
    command: ['sh', '-c', 'until nslookup myservice; do echo waiting for myservice; sleep 2; done;']
  - name: init-mydb
    image: busybox:1.34
    command: ['sh', '-c', 'until nslookup mydb; do echo waiting for mydb; sleep 2; done;']
  containers:
  - name: app
    image: myapp:1.0
```

### PodのDisruption

PodのDisruptionは、自発的なものと非自発的なものに分けられます。

1. **自発的なDisruption**: クラスター管理者や自動化ツールによって発生するDisruption
   - Nodeのドレイン
   - Deploymentの更新
   - Podの削除

2. **非自発的なDisruption**: ハードウェア障害、カーネルパニック、ネットワーク分断などによるDisruption

PodDisruptionBudgetは、Eviction API（たとえばdrain）を介した自発的な退避を制限します。Podの直接削除やDeploymentのローリングアップデートはこれを迂回するため、ロールアウト時の可用性は別途設定してください。非自発的な障害を防ぐことはできません。

## Podの設計パターン

Podを設計する際に検討すべきパターンとベストプラクティスがいくつかあります。これらを理解して適用することで、アプリケーションの安定性、スケーラビリティ、保守性を向上させられます。

### 単一責任の原則

Podは単一責任の原則に従う必要があります。

1. **主要な機能を1つにする**: 各Podは、1つの主要な機能またはプロセスを担当します。
2. **独立してスケーリングできるようにする**: 各機能を独立してスケーリングできるように設計します。
3. **ライフサイクルを分離する**: 各機能が独自のライフサイクルを持てるように設計します。

### Podテンプレート

Podテンプレートは、ワークロードリソース（Deployment、StatefulSetなど）でPodを作成するために使用する仕様です。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:  # Pod template starts
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - containerPort: 80
  # Pod template ends
```

### Podのアフィニティとアンチアフィニティ

Podのアフィニティとアンチアフィニティは、PodをどのNodeにスケジュールするかを制御するルールです。

1. **Podアフィニティ**: 特定のPodと同じNodeまたはトポロジードメインにスケジュールします。
2. **Podアンチアフィニティ**: 特定のPodとは異なるNodeまたはトポロジードメインにスケジュールします。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: "kubernetes.io/hostname"
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - web
          topologyKey: "kubernetes.io/hostname"
  containers:
  - name: web
    image: nginx:1.30.6
```

### Nodeアフィニティ

Nodeアフィニティは、Podのスケジューリング先を特定のNodeに制限するルールです。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: gpu
            operator: In
            values:
            - "true"
  containers:
  - name: gpu-container
    image: gpu-app:1.0
```

### TaintとToleration

Taintは特定のPodがスケジュールされないようにNodeに適用され、TolerationはTaintのあるNodeへのスケジューリングを許可するためにPodに適用されます。

```bash
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule
```

```yaml
# Apply toleration to Pod
apiVersion: v1
kind: Pod
metadata:
  name: tolerant-pod
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
  containers:
  - name: app
    image: myapp:1.0
```

### リソース要求と上限

Pod内のコンテナにリソース要求と上限を設定することは、クラスターリソースを効率的に使用し、安定性を確保するうえで重要です。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

### Podのセキュリティコンテキスト

セキュリティコンテキストは、Podまたはコンテナレベルのセキュリティ設定を定義します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

### Podの優先度とプリエンプション

クラスターのリソースが不足しているときに、どのPodをスケジュールし、どのPodをプリエンプトするかは、Podの優先度とプリエンプションによって決まります。

```yaml
# Priority class definition
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical pods only."
---
# Pod using priority class
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: app
    image: myapp:1.0
```

## ワークロードリソースの概要

Kubernetesには、Podを管理するためのさまざまなワークロードリソースがあります。それぞれ特定のユースケースや要件に合わせて設計されています。

### ワークロードリソースの種類

Kubernetesの主なワークロードリソースは次のとおりです。

1. **ReplicaSet**: 指定された数のPodレプリカを維持します。
2. **Deployment**: ReplicaSetを管理し、宣言的な更新を提供します。
3. **StatefulSet**: 状態の永続化が必要なアプリケーション向けのリソースです。
4. **DaemonSet**: すべてのNodeでPodのコピーを1つ実行します。
5. **Job**: 完了後に終了する単発タスクを実行します。
6. **CronJob**: スケジュールに従って定期的にJobを実行します。

### ワークロードリソースの選択基準

適切なワークロードリソースを選ぶ基準は次のとおりです。

1. **状態の永続性**: アプリケーションが状態を保持する必要があるかどうか
2. **実行パターン**: 継続的に実行されるのか、単発なのか、定期的なのか
3. **デプロイ要件**: ローリングアップデート、ブルー／グリーンデプロイなどの要件
4. **Nodeのカバレッジ**: すべてのNodeで実行する必要があるかどうか
5. **スケーラビリティ要件**: 水平スケーリングが必要かどうか

## ReplicaSet

ReplicaSetは、指定された数のPodレプリカが常に実行されるようにします。Podに障害が発生したり、削除されたりすると、ReplicaSetは自動的に置き換え用のPodを作成します。

### ReplicaSetの主な機能

1. **Podレプリカの維持**: 指定された数のPodレプリカを維持します。
2. **Podの選択**: ラベルセレクターを使って管理対象のPodを識別します。
3. **Podの作成**: 必要に応じて新しいPodを作成します。
4. **Podの削除**: 過剰なPodを削除します。

### ReplicaSetの定義

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: frontend
  labels:
    app: guestbook
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      tier: frontend
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      containers:
      - name: php-redis
        image: gcr.io/google_samples/gb-frontend:v3
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
        ports:
        - containerPort: 80
```

### ReplicaSetの動作

1. **ラベルセレクターとの照合**: ReplicaSetはラベルセレクターに一致するPodを識別します。
2. **現在の状態の確認**: 現在実行中のPod数を確認します。
3. **望ましい状態との比較**: 現在のPod数と望ましいレプリカ数を比較します。
4. **調整処理**: 必要に応じてPodを作成または削除します。

### ReplicaSetとReplication Controllerの比較

ReplicaSetはReplication Controllerの後継であり、より強力なラベルセレクターを備えています。

1. **Replication Controller**: 等価性に基づくセレクターのみをサポートします（例: app=nginx）。
2. **ReplicaSet**: 集合に基づくセレクターをサポートします（例: app in (nginx, apache)）。

### ReplicaSetのユースケース

ReplicaSetは通常、直接ではなくDeploymentを介して間接的に使用します。ただし、次のケースでは直接使用できます。

1. **シンプルなレプリケーション**: Podレプリカを維持するだけの場合
2. **カスタム更新**: 独自の更新メカニズムが必要な場合
3. **レガシーサポート**: レガシーアプリケーションをサポートする場合

## Deployment

DeploymentはReplicaSetを管理し、Podの宣言的な更新を行います。アプリケーションのローリングアップデート、ロールバック、スケーリングなどを管理します。

### Deploymentの主な機能

1. **宣言的な更新**: 望ましい状態を宣言すると、Deploymentが現在の状態をその状態に変更します。
2. **ローリングアップデート**: ダウンタイムなしでアプリケーションを更新します。
3. **ロールバック**: 以前のバージョンに簡単に戻せます。
4. **スケーリング**: アプリケーションのレプリカ数を調整します。
5. **Deploymentの履歴**: 以前のDeploymentバージョンの記録を保持します。

### Deploymentの定義

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
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
    spec:
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
          limits:
            cpu: 200m
            memory: 200Mi
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

### Deploymentの更新戦略

Deploymentでは、次の2つの更新戦略を利用できます。

1. **RollingUpdate**: ダウンタイムを発生させずにPodを段階的に更新します（デフォルト）。
   - **maxSurge**: 望ましいPod数を超えて作成できるPodの最大数
   - **maxUnavailable**: 更新中に利用できなくなるPodの最大数

2. **Recreate**: 新しいPodを作成する前に、既存のPodをすべて削除します（一時的なダウンタイムが発生します）。

### Deploymentのロールバック

Deploymentでは、以前のバージョンにロールバックできます。

```bash
# Check deployment history
kubectl -n workloads-demo rollout history deployment/nginx-deployment

# Check details of specific version
kubectl -n workloads-demo rollout history deployment/nginx-deployment --revision=2

# Rollback to previous version
kubectl -n workloads-demo rollout undo deployment/nginx-deployment

# Rollback to specific version
kubectl -n workloads-demo rollout undo deployment/nginx-deployment --to-revision=2
```

### Deploymentのスケーリング

Deploymentは簡単にスケーリングできます。

```bash
# Imperative scaling
kubectl -n workloads-demo scale deployment/nginx-deployment --replicas=5

# Declarative scaling (after modifying YAML file)
kubectl apply -f deployment.yaml
```

### Deploymentの一時停止と再開

Deploymentのロールアウトは一時停止および再開できます。

```bash
# Pause rollout
kubectl -n workloads-demo rollout pause deployment/nginx-deployment

# Apply multiple changes
kubectl -n workloads-demo set image deployment/nginx-deployment nginx=nginx:1.30.6-alpine
kubectl -n workloads-demo set resources deployment/nginx-deployment -c=nginx --limits=cpu=200m,memory=256Mi

# Resume rollout
kubectl -n workloads-demo rollout resume deployment/nginx-deployment
```

### Deploymentの状態

DeploymentのConditionsには`Progressing`、`Available`、`ReplicaFailure`があります。ロールアウトが停滞すると、reasonが`ProgressDeadlineExceeded`の`Progressing=False`が報告されることがあります。Kubernetesが自動的にロールバックすることはありません。「Complete」はロールアウトの完了を示すものであり、Conditionの種類ではありません。

## StatefulSet

StatefulSetは、状態の永続化が必要なアプリケーション向けのワークロードリソースです。各Podに一意の識別子を割り当て、安定したネットワーク識別子と永続ストレージを提供します。

### StatefulSetの主な機能

1. **安定した一意のネットワーク識別子**: 再起動後もPod名とホスト名が維持されます。
2. **安定した永続ストレージ**: Podが再スケジュールされても、同じストレージにアクセスできます。
3. **順序に従ったデプロイとスケーリング**: Podは順序に従って作成、更新、削除されます。
4. **順序に従った自動ローリングアップデート**: Podは順序に従って更新されます。

### StatefulSetの定義

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  selector:
    matchLabels:
      app: nginx
  serviceName: "nginx"
  replicas: 3
  updateStrategy:
    type: RollingUpdate
  podManagementPolicy: OrderedReady
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - containerPort: 80
          name: web
        volumeMounts:
        - name: www
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
  - metadata:
      name: www
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "standard"
      resources:
        requests:
          storage: 1Gi
```

### StatefulSetのPod識別子

StatefulSetは、次の形式でPodに一意の識別子を割り当てます。
```
<StatefulSet name>-<ordinal index>
```

たとえば、`web` StatefulSetは`web-0`、`web-1`、`web-2`のようなPodを作成します。

### StatefulSetのHeadless Service

StatefulSetは通常、Headless Service（clusterIP: None）と組み合わせて使用します。これにより、各PodのDNSレコードが作成されます。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  ports:
  - port: 80
    name: web
  clusterIP: None
  selector:
    app: nginx
```

この場合、各Podには次の形式のDNS名が割り当てられます。
```
<Pod name>.<service name>.<namespace>.svc.cluster.local
```

例: `web-0.nginx.default.svc.cluster.local`

### StatefulSetのストレージ

StatefulSetは`volumeClaimTemplates`を使って、各Pod用のPersistentVolumeClaim（PVC）を自動的に作成します。Podが再スケジュールされても、これらのPVCは維持されます。

### StatefulSetの更新戦略

StatefulSetでは、次の2つの更新戦略を利用できます。

1. **RollingUpdate**: Podを順番に更新します（デフォルト）。
2. **OnDelete**: Podが削除された場合にのみ更新します。

### Pod管理ポリシー

StatefulSetでは、次の2つのPod管理ポリシーを利用できます。

1. **OrderedReady**: Podを順番に作成、終了します（デフォルト）。
2. **Parallel**: Podを並行して作成、終了します。

### StatefulSetのユースケース

StatefulSetは、次のようなアプリケーションに適しています。

1. **データベース**: MySQL、PostgreSQL、MongoDBなど
2. **分散システム**: Kafka、ZooKeeper、Elasticsearchなど
3. **メッセージキュー**: RabbitMQなど
4. **その他のステートフルアプリケーション**: ファイルサーバー、セッションストアなど

### StatefulSetの例: 永続ストレージを使うMySQLインスタンス

この例では、1つのMySQLインスタンスに対して安定した識別子とPVCを設定します。レプリケーションやデータベースの自動フェイルオーバーは**設定しません**。`replicas`を増やすと、それぞれ独立したデータベースが作成されます。同じnamespace内に`password`キーを持つ`mysql-secret`を作成し、デフォルトのStorageClassを用意してください（または適切なクラスを明示的に設定してください）。検証済みのMySQL 8.4パッチバージョンまたはダイジェストを使用してください。認証情報を変更する場合は、Secretを更新するだけではなく、データベース側でローテーションする必要があります。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  clusterIP: None
  selector:
    app: mysql
  ports:
  - name: mysql
    port: 3306
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  podManagementPolicy: OrderedReady
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.4
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
        ports:
        - name: mysql
          containerPort: 3306
        startupProbe:
          tcpSocket:
            port: mysql
          periodSeconds: 10
          failureThreshold: 60
        readinessProbe:
          exec:
            command:
            - sh
            - -c
            - 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -h 127.0.0.1 -u root -e "SELECT 1"'
          periodSeconds: 10
          timeoutSeconds: 5
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            memory: 2Gi
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ReadWriteOnce]
      resources:
        requests:
          storage: 10Gi
```

レプリケーションとリーダー昇格を行うには、データベースOperator、または別途テスト済みのレプリケーション手順書を使用してください。StatefulSet単体では、どちらも提供されません。[上流のレプリケーションチュートリアル](https://kubernetes.io/docs/tasks/run-application/run-replicated-stateful-application/)では、安全でない学習用のデフォルト設定が明示的に使用されており、本番環境向けの構成ではありません。

## DaemonSet

DaemonSetは、すべてのNode（または特定のNode）でPodのコピーを1つ実行します。Nodeがクラスターに追加されるとPodが自動的に追加され、Nodeが削除されるとPodも削除されます。

### DaemonSetの主な機能

1. **すべてのNodeで実行**: クラスター内のすべてのNodeでPodを実行します。
2. **Nodeの選択**: Nodeセレクターを使って特定のNodeのみで実行できます。
3. **自動デプロイ**: 新しいNodeが追加されるとPodを自動的にデプロイします。
4. **自動クリーンアップ**: Nodeが削除されるとPodを自動的にクリーンアップします。

### DaemonSetの定義

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd-elasticsearch
  namespace: kube-system
  labels:
    k8s-app: fluentd-logging
spec:
  selector:
    matchLabels:
      name: fluentd-elasticsearch
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  template:
    metadata:
      labels:
        name: fluentd-elasticsearch
    spec:
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        effect: NoSchedule
      containers:
      - name: fluentd-elasticsearch
        image: quay.io/fluentd_elasticsearch/fluentd:v2.5.2
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 200Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
          readOnly: true
      terminationGracePeriodSeconds: 30
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
```

CRIランタイムでは、ログコレクターがDocker JSONログではなく、`/var/log/pods`（通常は`/var/log/containers`からリンクされています）配下のCRIログを解析するように設定してください。ログコレクターには、独自のソース／出力設定とRBACも必要です。

### DaemonSetの更新戦略

DaemonSetでは、次の2つの更新戦略を利用できます。

1. **RollingUpdate**: Podを順番に更新します（デフォルト）。
   - **maxUnavailable**: 更新中に利用できなくなるPodの最大数

2. **OnDelete**: Podが削除された場合にのみ更新します。

### DaemonSetのNode選択

DaemonSetは、特定のNodeのみで実行するように設定できます。

```yaml
spec:
  template:
    spec:
      nodeSelector:
        disk: ssd
```

### DaemonSetのTaint許容

DaemonSetにTolerationを設定すると、TaintのあるNodeでも実行できます。

```yaml
spec:
  template:
    spec:
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        effect: NoSchedule
```

### DaemonSetのユースケース

DaemonSetは、次の目的で使用されます。

1. **ログコレクター**: Fluentd、Logstashなど
2. **監視エージェント**: Prometheus Node Exporter、Datadog Agentなど
3. **ネットワークプラグイン**: Calico、Ciliumなど
4. **ストレージデーモン**: Ceph、GlusterFSなど
5. **セキュリティエージェント**: Falco、Sysdigなど

### DaemonSetの例: Prometheus Node Exporter

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      hostPID: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.3.1
        args:
        - --path.procfs=/host/proc
        - --path.sysfs=/host/sys
        - --path.rootfs=/host/root
        - --web.listen-address=:9100
        ports:
        - containerPort: 9100
          protocol: TCP
          name: http
        resources:
          limits:
            cpu: 250m
            memory: 180Mi
          requests:
            cpu: 102m
            memory: 180Mi
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
      tolerations:
      - operator: "Exists"
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
```

## JobとCronJob

JobとCronJobは、単発または定期的なタスクを実行するためのワークロードリソースです。

### Job

Jobは1つ以上のPodを作成し、指定された数のPodが正常に終了するまで実行を続けます。

#### Jobの主な機能

1. **完了状況の追跡**: 成功したPodを追跡します。再試行回数の上限や期限によってJobが失敗することがあります。
2. **並列実行**: 複数のPodを並列に実行できます。
3. **再試行**: 失敗したPodを自動的に再試行します。
4. **完了後のクリーンアップ**: Jobの完了後にPodを削除するよう設定できます。

#### Jobの定義

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  completions: 5      # Number of Pods that must successfully complete
  parallelism: 2      # Number of Pods to run in parallel
  backoffLimit: 4     # Number of retries on failure
  activeDeadlineSeconds: 100  # Job time limit (seconds)
  ttlSecondsAfterFinished: 100  # Deletion time after completion (seconds)
  template:
    spec:
      containers:
      - name: pi
        image: perl:5.34
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
        resources:
          requests:
            cpu: 100m
            memory: 50Mi
          limits:
            cpu: 100m
            memory: 100Mi
      restartPolicy: Never  # or OnFailure
```

#### Jobの完了モード

Jobには、次の2つの完了モードがあります。

1. **NonIndexed**: 指定された数のPodが正常に完了したときにJobが完了する標準モード
2. **Indexed**: 各Podに0から始まるインデックスが割り当てられ、それぞれが特定のインデックス範囲のタスクを実行します。

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-job
spec:
  completions: 5
  parallelism: 3
  completionMode: Indexed  # Enable Indexed mode
  template:
    spec:
      containers:
      - name: worker
        image: busybox:1.34
        command: ["sh", "-c", "echo Processing item ${JOB_COMPLETION_INDEX}"]
      restartPolicy: Never
```

#### Jobのユースケース

Jobは、次の目的で使用されます。

1. **バッチ処理**: データ処理、ETLタスク
2. **計算タスク**: 科学計算、レンダリング
3. **データベースのマイグレーション**: Schemaの更新
4. **単発の管理タスク**: バックアップ、クリーンアップタスク

### CronJob

CronJobは、指定されたスケジュールに従って定期的にJobを実行します。Linuxのcronジョブと同様に動作します。

#### CronJobの主な機能

1. **スケジュール実行**: cron式を使用して実行スケジュールを指定します。
2. **Jobの管理**: スケジュールに従ってJobを作成します。
3. **同時実行ポリシー**: 前のJobがまだ実行中の場合の動作を定義します。
4. **履歴の上限**: 完了したJobの履歴数を制限します。

#### CronJobの定義

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello
spec:
  schedule: "*/1 * * * *"  # Run every minute
  timeZone: "America/New_York"  # Timezone (stable since Kubernetes 1.27)
  concurrencyPolicy: Forbid  # Allow, Forbid, Replace
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  startingDeadlineSeconds: 60
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox:1.34
            command:
            - /bin/sh
            - -c
            - date; echo Hello from the Kubernetes cluster
          restartPolicy: OnFailure
```

#### Cron式

Cron式は、次の形式です。
```
+------------------- minute (0 - 59)
| +----------------- hour (0 - 23)
| | +--------------- day of month (1 - 31)
| | | +------------- month (1 - 12)
| | | | +----------- day of week (0 - 6) (Sunday to Saturday; use 0 for Sunday)
| | | | |
| | | | |
* * * * *
```

Cron式の一般的な例:
- `*/5 * * * *`: 5分ごと
- `0 * * * *`: 毎時0分
- `0 0 * * *`: 毎日午前0時
- `0 0 * * 0`: 毎週日曜日の午前0時
- `0 0 1 * *`: 毎月1日の午前0時
- `0 0 1 1 *`: 毎年1月1日の午前0時

#### 同時実行ポリシー

CronJobには、次の3つの同時実行ポリシーがあります。

1. **Allow**: 複数のJobを同時に実行できます（デフォルト）。
2. **Forbid**: 前のJobがまだ実行中の場合、新しいJobをスキップします。
3. **Replace**: 前のJobが実行中の場合、新しいJobで置き換えます。

#### CronJobのユースケース

CronJobは、次の目的で使用されます。

1. **定期バックアップ**: データベースのバックアップ、スナップショットの作成
2. **データ同期**: 定期的なデータ同期
3. **レポートの生成**: 日次／週次／月次レポートの生成
4. **クリーンアップタスク**: 一時ファイルの削除、ログローテーション
5. **通知と監視**: 状態確認、アラート送信

#### CronJobの例: データベースのバックアップ

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
            - |
              set -eu
              backup_file="/backup/db-$(date +%Y%m%d-%H%M%S).dump"
              trap 'rm -f "$backup_file.partial"' EXIT
              pg_dump -Fc > "$backup_file.partial"
              pg_restore --list "$backup_file.partial" > /dev/null
              mv "$backup_file.partial" "$backup_file"
              find /backup -maxdepth 1 -type f -name 'db-*.dump' -mtime +7 -delete
            volumeMounts:
            - name: backup-volume
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-volume
            persistentVolumeClaim:
              claimName: backup-pvc
```

CronJobのスケジュール実行は厳密ではないため、Jobは重複実行されても問題ないようにする必要があります。`Forbid`が適用されるのは、同じCronJobから作成されたJobに限られます。履歴の上限が削除するのはJob／Podオブジェクトであり、バックアップファイルではありません。バックアップの例は毎日02:00 UTCに実行され、`backup-pvc`、`postgres-secret`、および接続可能なデータベースが必要です。`pg_dump`のメジャーバージョンはサーバーと同じか、それより新しい必要があります。`PGDATABASE`が`PGUSER`と異なる場合は、`PGDATABASE`を指定してください。実際のリストアテストは別途実施してください。

## まとめ

このドキュメントでは、Kubernetesの基本構成要素であるPodと、さまざまなワークロードリソースについて説明しました。Podの概念から始めて、Deployment、StatefulSet、DaemonSet、Job、CronJobなど、さまざまなワークロードリソースの特性とユースケースを取り上げました。これらのリソースにはそれぞれ独自の目的と機能があり、適切に使用することで、アプリケーションを効率的にデプロイし、管理できます。

## クイズ

この章で学んだ内容を確認するには、[Podとワークロードのクイズ](../quizzes/core/02-pods-and-workloads-quiz.md)に挑戦してください。
