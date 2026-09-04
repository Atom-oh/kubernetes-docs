# Kubernetes の概要

> **対応バージョン**: Kubernetes 1.31, 1.32, 1.33 **最終更新**: February 11, 2026

Kubernetes (K8s) は、コンテナ化されたアプリケーションのデプロイ、スケーリング、管理を自動化するオープンソースのコンテナオーケストレーションプラットフォームです。このドキュメントでは、Kubernetes の基本概念、アーキテクチャ、主要コンポーネント、機能を説明します。

## ラボ環境のセットアップ

このドキュメントの例に沿って進めるには、次のツールと環境が必要です。

### 必要なツール

* **kubectl**: Kubernetes クラスターを操作するためのコマンドラインツール
* **Container Runtime**: Docker、containerd、CRI-O など
* **minikube** または **kind**: ローカル Kubernetes クラスター（開発および学習用）

### インストール方法

**kubectl のインストール**:

```bash
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Windows (PowerShell)
curl -LO "https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe"
```

**minikube のインストール**:

```bash
# macOS
brew install minikube

# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
chmod +x minikube-linux-amd64
sudo mv minikube-linux-amd64 /usr/local/bin/minikube

# Windows (PowerShell)
New-Item -Path 'c:\' -Name 'minikube' -ItemType Directory
Invoke-WebRequest -OutFile 'c:\minikube\minikube.exe' -Uri 'https://github.com/kubernetes/minikube/releases/latest/download/minikube-windows-amd64.exe'
```

### ローカルクラスターの起動

```bash
minikube start
```

## 目次

* [Kubernetes とは？](04-kubernetes-introduction.md#what-is-kubernetes)
* [Kubernetes の歴史](04-kubernetes-introduction.md#history-of-kubernetes)
* [Kubernetes アーキテクチャ](04-kubernetes-introduction.md#kubernetes-architecture)
* [Kubernetes の主要コンポーネント](04-kubernetes-introduction.md#kubernetes-main-components)
* [Kubernetes の基本オブジェクト](04-kubernetes-introduction.md#kubernetes-basic-objects)
* [Kubernetes の Workload リソース](04-kubernetes-introduction.md#kubernetes-workload-resources)
* [Kubernetes の Service とネットワーキング](04-kubernetes-introduction.md#kubernetes-services-and-networking)
* [Kubernetes ストレージ](04-kubernetes-introduction.md#kubernetes-storage)
* [Kubernetes の設定とセキュリティ](04-kubernetes-introduction.md#kubernetes-configuration-and-security)
* [Kubernetes と Amazon EKS の比較](04-kubernetes-introduction.md#kubernetes-vs-amazon-eks)
* [Kubernetes を始める](04-kubernetes-introduction.md#getting-started-with-kubernetes)

## Kubernetes とは？

Kubernetes はギリシャ語で「舵取り役」または「操縦士」を意味し、コンテナ化されたアプリケーションのデプロイ、スケーリング、運用を自動化するオープンソースシステムです。Google の社内 Borg システムから着想を得て、2014 年にオープンソースとして公開されました。

### Kubernetes の主な機能

1. **Service Discovery と Load Balancing**: コンテナを外部に公開し、トラフィックを分散
2. **Storage Orchestration**: ローカルまたはクラウドのストレージシステムを自動でマウント
3. **自動 Rollout と Rollback**: アプリケーションの状態を段階的に変更し、問題発生時は以前の状態に復元
4. **自動 Bin Packing**: リソース要件に基づいてコンテナをノードに配置
5. **Self-healing**: 失敗したコンテナを再起動し、応答しないコンテナを置換
6. **Secret と設定の管理**: 機密情報を保存し、設定を更新
7. **水平スケーリング**: シンプルなコマンドまたは UI によりアプリケーションをスケール
8. **バッチ実行**: バッチおよび CI ワークロードを管理

### Kubernetes が解決する課題

* **コンテナオーケストレーション**: 数百から数千のコンテナを効率的に管理
* **高可用性**: アプリケーションの継続的な稼働を確保
* **スケーラビリティ**: トラフィック増加に応じた自動スケーリング
* **災害復旧**: 障害時の自動復旧
* **リソース効率**: ハードウェアリソースを効率的に利用
* **宣言的設定**: Infrastructure as Code としてインフラストラクチャを管理
* **マルチクラウドとハイブリッドクラウド**: 多様な環境で一貫してデプロイおよび管理

## Kubernetes の歴史

### 背景

* **2003-2013**: Google は Borg というコンテナオーケストレーションシステムを社内で使用
* **2014 年 6 月**: Google が Kubernetes をオープンソースとして公開
* **2015 年 7 月**: Kubernetes 1.0 がリリースされ、Cloud Native Computing Foundation (CNCF) に寄贈
* **2016-2017**: 主要クラウドプロバイダーがマネージド Kubernetes サービスを開始
* **2018 年以降**: コンテナオーケストレーションの事実上の標準として確立

### 名前の由来

Kubernetes (κυβερνήτης) はギリシャ語で「舵取り役」または「操縦士」を意味します。これはコンテナ化されたアプリケーションを導く役割を象徴しています。「K」と「s」の間に 8 文字あるため、略称として K8s が使われます。

### ロゴの意味

Kubernetes のロゴは 7 本のスポークを持つ舵輪を描いており、コンテナ化されたアプリケーションの進路を導く Kubernetes の役割を象徴しています。

## Kubernetes アーキテクチャ

Kubernetes は master-node アーキテクチャに従います。Master ノード（control plane）がクラスターを管理し、worker ノードが実際のアプリケーションワークロードを実行します。

### Control Plane (Master) コンポーネント

![Kubernetes control plane コンポーネント: kubectl クライアントからのリクエストは kube-apiserver を経由して etcd に流れ、kube-scheduler、kube-controller-manager、cloud-controller-manager は API server を通じて監視および調整します](../.gitbook/assets/en-basics-04-kubernetes-introduction-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-0.html)

1. **kube-apiserver**: Kubernetes API を公開する control plane のフロントエンド
2. **etcd**: すべてのクラスターのデータを保存する一貫性と高可用性を備えた key-value store
3. **kube-scheduler**: Pod をノードに割り当てるコンポーネント
4. **kube-controller-manager**: controller プロセスを実行するコンポーネント
   * Node Controller: ノードの停止時に通知および対応
   * Replication Controller: 正しい Pod レプリカ数を維持
   * Endpoints Controller: Service と Pod を接続
   * Service Account & Token Controller: 新しい namespace 用のデフォルトアカウントと API アクセストークンを作成
5. **cloud-controller-manager**: クラウド固有の制御ロジックを含むコンポーネント
   * Node Controller: ノードが削除されたかをクラウドプロバイダーに確認
   * Route Controller: クラウドインフラストラクチャにルートを設定
   * Service Controller: クラウドプロバイダーの Load Balancer を作成、更新、削除
   * Volume Controller: volume を作成、アタッチ、マウント

### Node コンポーネント

![Kubernetes worker node のアーキテクチャ図: kubelet は control plane からの指示を受けて Container Runtime (Docker、containerd、CRI-O) を駆動し、Container Runtime は Pod 内のコンテナを実行します。kube-proxy はそれらのネットワークルールを維持します。](../.gitbook/assets/en-basics-04-kubernetes-introduction-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-1.html)

1. **kubelet**: 各ノードで実行され、Pod 内のコンテナが稼働していることを確認するエージェント
2. **kube-proxy**: Kubernetes Service の概念を実装する、各ノード上で実行されるネットワークプロキシ
3. **Container Runtime**: コンテナの実行を担うソフトウェア（Docker、containerd、CRI-O など）

### 完全なアーキテクチャ

![完全な Kubernetes クラスターのアーキテクチャ図: 外部クライアント（kubectl）は control plane の kube-apiserver に到達し、kube-apiserver は etcd、kube-scheduler、kube-controller-manager、cloud-controller-manager を調整し、2 つの worker node 上の kubelet と通信します。worker node では Container Runtime が Pod を実行し、kube-proxy がトラフィックを転送します。](../.gitbook/assets/en-basics-04-kubernetes-introduction-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-2.html)

## Kubernetes の主要コンポーネント

### API Server (kube-apiserver)

API server は Kubernetes API を公開する control plane のフロントエンドです。すべての内部および外部リクエストは API server を介して処理されます。

**主な機能**:

* REST API を提供
* 認証と認可
* リクエストの検証
* etcd との通信
* 水平スケーリング可能

### etcd

etcd は、すべてのクラスターのデータを保存する一貫性と高可用性を備えた key-value store です。

**主な特徴**:

* 分散システム
* 強整合性
* 高可用性
* セキュアなデータ保存
* 変更を監視する Watch 機能

### Scheduler (kube-scheduler)

Scheduler は、新しく作成された Pod を実行するノードを選択する control plane コンポーネントです。

**スケジューリングプロセス**:

1. **Filtering**: Pod を実行できるノードを識別
2. **Scoring**: 適切なノードにスコアを割り当て
3. **Binding**: Pod を最適なノードに割り当て

**考慮事項**:

* リソース要件（CPU、メモリ）
* ハードウェア、ソフトウェア、ポリシー上の制約
* affinity/anti-affinity の指定
* データの局所性
* ワークロードの干渉

### Controller Manager (kube-controller-manager)

Controller Manager は、複数の controller プロセスを実行する control plane コンポーネントです。

**主な Controller**:

* **Node Controller**: ノードの状態を監視して対応
* **Replication Controller**: Pod のレプリカ数を維持
* **Endpoints Controller**: Service と Pod を接続
* **Service Account & Token Controller**: namespace 用のデフォルトアカウントと API トークンを作成
* **Job Controller**: 一回限りのタスクを管理
* **CronJob Controller**: スケジュールされたタスクを管理
* **DaemonSet Controller**: すべてのノードで特定の Pod が実行されることを保証
* **StatefulSet Controller**: ステートフルなアプリケーションを管理
* **PV Controller**: PersistentVolume を管理

### Cloud Controller Manager (cloud-controller-manager)

Cloud Controller Manager は、クラウド固有の制御ロジックを含む control plane コンポーネントです。

**主な Controller**:

* **Node Controller**: クラウドプロバイダー API を通じてノードの状態を確認
* **Route Controller**: クラウド環境にルートを設定
* **Service Controller**: クラウド Load Balancer を作成、更新、削除
* **Volume Controller**: クラウドストレージ volume を作成、アタッチ、マウント

### kubelet

kubelet は、各ノードで実行され、Pod 内のコンテナが稼働していることを確認するエージェントです。

**主な機能**:

* PodSpec に従ってコンテナを実行
* コンテナの状態を報告
* コンテナのヘルスチェックを実行
* コンテナのライフサイクルを管理
* ノードの状態を報告

### kube-proxy

kube-proxy は、Kubernetes Service の概念を実装する、各ノード上で実行されるネットワークプロキシです。

**主な機能**:

* Service IP とポートのネットワークルールを維持
* 接続を転送
* Load Balancing を実装

**動作モード**:

* **userspace mode**: ユーザー空間でプロキシを実行（レガシー）
* **iptables mode**: Linux iptables を使用した NAT 実装（デフォルト）
* **IPVS mode**: Linux カーネルの IP Virtual Server を使用（高性能）

## Kubernetes の基本オブジェクト

Kubernetes オブジェクトは、クラスターの状態を表す永続的なエンティティです。これらのオブジェクトは、クラスター内で実行中のアプリケーション、利用可能なリソース、ポリシーなどを記述します。

### Pod

Pod は Kubernetes における最小のデプロイ可能単位であり、1 つ以上のコンテナのグループを表します。Pod 内のコンテナはストレージとネットワークを共有し、常に同じノードにまとめてスケジュールされます。

**主な特徴**:

* 一意の IP アドレスを持つ
* ネットワーク namespace を共有（同じ IP とポート空間）
* IPC namespace を共有
* hostname を共有
* コンテナ間で localhost 通信が可能

**Pod の例**:

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
    image: nginx:1.21
    ports:
    - containerPort: 80
  - name: log-sidecar
    image: busybox
    command: ["/bin/sh", "-c", "tail -f /var/log/nginx/access.log"]
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  volumes:
  - name: logs
    emptyDir: {}
```

### Namespace

Namespace は、単一クラスター内でリソースグループを分離する方法を提供します。複数のチームまたはプロジェクトが同じクラスターを共有する場合に有用です。

**デフォルト Namespace**:

* **default**: デフォルト namespace
* **kube-system**: Kubernetes システムが作成するオブジェクトの namespace
* **kube-public**: すべてのユーザーが読み取れるオブジェクトの namespace
* **kube-node-lease**: ノードの heartbeat 用 namespace

**Namespace の例**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
```

### Labels と Selectors

Labels はオブジェクトに付与する key-value ペアで、オブジェクトの識別と選択に使用します。Selectors は Labels に基づいてオブジェクトをフィルタリングする方法を提供します。

**Labels の例**:

```yaml
metadata:
  labels:
    app: nginx
    environment: production
    tier: frontend
```

**Selector の種類**:

* **Equality-based**: `=`, `!=`
* **Set-based**: `in`, `notin`, `exists`

**Selector の例**:

```yaml
selector:
  matchLabels:
    app: nginx
  matchExpressions:
    - {key: tier, operator: In, values: [frontend, middleware]}
    - {key: environment, operator: NotIn, values: [dev]}
```

### Annotations

Annotations は、オブジェクトに関する識別用ではないメタデータを保存する key-value ペアです。Annotations はツールまたはライブラリが使用する情報の保存に役立ちます。

**Annotations の例**:

```yaml
metadata:
  annotations:
    kubernetes.io/created-by: "admin"
    example.com/last-modified: "2023-07-01T12:00:00Z"
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
```

### Node

Node は Pod を実行する Kubernetes クラスター内の worker マシンです。Node は物理マシンまたは仮想マシンです。

**Node の状態**:

* **Addresses**: Hostname、Internal IP、External IP
* **Conditions**: Ready、DiskPressure、MemoryPressure、PIDPressure、NetworkUnavailable
* **Capacity**: CPU、Memory、最大 Pod 数
* **Info**: Kernel バージョン、Container Runtime バージョン、kubelet バージョン

**Node の例**:

```yaml
apiVersion: v1
kind: Node
metadata:
  name: worker-1
  labels:
    kubernetes.io/hostname: worker-1
    node-role.kubernetes.io/worker: ""
    topology.kubernetes.io/zone: us-east-1a
spec:
  # ...
status:
  capacity:
    cpu: "4"
    memory: 8Gi
    pods: "110"
  conditions:
    - type: Ready
      status: "True"
  # ...
```

## Kubernetes の Workload リソース

Workload リソースは、Pod の管理と実行に使用するオブジェクトです。これらのリソースは Pod の作成、スケーリング、更新、終了を管理します。

### ReplicaSet

ReplicaSet は、指定された数の Pod レプリカが常に実行されることを保証します。Pod が失敗または削除されると、ReplicaSet が自動的に代替 Pod を作成します。

**主な機能**:

* 指定された数の Pod レプリカを維持
* Pod template を定義
* Selectors により Pod を識別

**ReplicaSet の例**:

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: nginx-replicaset
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
        image: nginx:1.21
        ports:
        - containerPort: 80
```

### Deployment

Deployment は ReplicaSet をさらに 1 つのレベルで抽象化し、アプリケーションの宣言的な更新を提供します。Deployment は Rolling Update、Rollback、スケーリングなどの機能を提供します。

**主な機能**:

* 宣言的なアプリケーション更新
* Rolling Update と Rollback
* Deployment 履歴の管理
* スケーリング

**Deployment の例**:

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
        image: nginx:1.21
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
```

### StatefulSet

StatefulSet は、状態の維持を必要とするアプリケーション向けの Workload リソースです。各 Pod に一意の識別子を割り当て、安定したネットワーク識別子と永続ストレージを提供します。

**主な機能**:

* 安定した一意のネットワーク識別子
* 安定した永続ストレージ
* 順序付けられたデプロイとスケーリング
* 順序付けられた更新

**StatefulSet の例**:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  selector:
    matchLabels:
      app: mysql
  serviceName: mysql
  replicas: 3
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "standard"
      resources:
        requests:
          storage: 10Gi
```

### DaemonSet

DaemonSet は、すべてのノード（または特定のノード）で Pod のコピーが実行されることを保証します。ノードがクラスターに追加されると Pod は自動的に追加され、ノードが削除されると Pod も削除されます。

**主なユースケース**:

* ログコレクター（Fluentd、Logstash）
* モニタリングエージェント（Prometheus Node Exporter）
* ネットワークプラグイン（Calico、Cilium）
* ストレージデーモン（Ceph）

**DaemonSet の例**:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: fluentd
  template:
    metadata:
      labels:
        name: fluentd
    spec:
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
      containers:
      - name: fluentd
        image: fluentd:v1.14
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 100Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
```

### Job

Job は 1 つ以上の Pod を作成し、指定数の Pod が正常に終了するまで実行を続けます。バッチ処理タスクに適しています。

**主な機能**:

* 一回限りのタスク実行
* 並列タスク実行
* タスク完了を保証
* 失敗時に再試行

**Job の例**:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi-calculator
spec:
  completions: 5
  parallelism: 2
  backoffLimit: 3
  template:
    spec:
      containers:
      - name: pi
        image: perl
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
```

### CronJob

CronJob は、指定されたスケジュールに従って定期的に Job を実行します。Linux の cron job と同様に動作します。

**主な機能**:

* スケジュールに従ったタスク実行
* Cron 式のサポート
* 同時実行ポリシーの設定
* 履歴の上限

**CronJob の例**:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"  # Run at 02:00 daily
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: database-backup:v1
            env:
            - name: DB_HOST
              value: "db.example.com"
          restartPolicy: OnFailure
```

## Kubernetes の Service とネットワーキング

Kubernetes のネットワーキングモデルは、すべての Pod が一意の IP アドレスを持ち、特別な設定なしで相互に通信できることを前提としています。Service は Pod のセットに安定したエンドポイントを提供します。

### Service

Service は Pod のセットに単一のエンドポイントと Load Balancing を提供します。Pod は動的に作成および削除されるため、Service はそのような変更があっても安定したネットワークアドレスを提供します。

**Service の種類**:

* **ClusterIP**: クラスター内からのみアクセス可能な Service（デフォルト）
* **NodePort**: 各ノードの IP と特定のポートを通じて外部からアクセス可能
* **LoadBalancer**: クラウドプロバイダーの Load Balancer を使用して外部からアクセス可能
* **ExternalName**: 外部 Service の CNAME レコードを作成

![外部クライアントが NodePort および LoadBalancer Service を介してのみクラスターに到達し、ClusterIP Service は内部専用のままであり、3 つすべての Service type が同じ Pod セット（Pod 1、2、3）へのポート 80 リクエストを Load Balancing するアーキテクチャ図。](../.gitbook/assets/en-basics-04-kubernetes-introduction-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-3.html)

**Service の例**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**NodePort Service の例**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-nodeport
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080
  type: NodePort
```

**LoadBalancer Service の例**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-lb
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### Ingress

Ingress は、クラスター外部から内部 Service への HTTP および HTTPS ルーティングを管理する API オブジェクトです。Ingress は Load Balancing、SSL termination、名前ベースの virtual hosting などを提供します。

**Ingress Controller**:

* **NGINX Ingress Controller**: NGINX ベースの Ingress Controller
* **AWS ALB Ingress Controller**: AWS Application Load Balancer ベースの Ingress Controller
* **Traefik**: クラウドネイティブな edge router
* **Istio Ingress**: Service mesh ベースの Ingress

**Ingress の例**:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: example.com
    http:
      paths:
      - path: /app1
        pathType: Prefix
        backend:
          service:
            name: app1-service
            port:
              number: 80
      - path: /app2
        pathType: Prefix
        backend:
          service:
            name: app2-service
            port:
              number: 80
  tls:
  - hosts:
    - example.com
    secretName: example-tls
```

### NetworkPolicy

NetworkPolicy は Pod 間の通信を制御する方法を提供します。デフォルトではすべての Pod が相互に通信できますが、network policy を使用してこれを制限できます。&#x20;

![外部リクエストが default namespace 内の frontend、API、database Pod を通過し、role=db Pod には db-network-policy NetworkPolicy が適用され、monitoring namespace の Prometheus が namespace 境界を越えて 3 つすべての層を scrape するアーキテクチャ図。](../.gitbook/assets/en-basics-04-kubernetes-introduction-4.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-4.html)

**主な機能**:

* Pod 間の通信を制御
* Namespace 間の通信を制御
* ingress（受信）および egress（送信）トラフィックを制御
* ポートおよびプロトコルベースのフィルタリング

**NetworkPolicy の例**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 3306
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

### DNS

Kubernetes は Service Discovery をサポートするために、クラスター内に DNS Service を提供します。デフォルトでは CoreDNS が使用されます。

**DNS 名の形式**:

* **Service**: `<service-name>.<namespace>.svc.cluster.local`
* **Pod**: `<pod-IP-address-dots-replaced>.pod.cluster.local`

**DNS 設定例**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health
        kubernetes cluster.local in-addr.arpa ip6.arpa {
          pods insecure
          upstream
          fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

### Service Mesh

Service mesh は、マイクロサービス間の通信を管理するインフラストラクチャレイヤーです。Service mesh はトラフィック管理、セキュリティ、可観測性を提供します。

**主要な Service Mesh**:

* **Istio**: 最も広く使用されている Service mesh
* **Linkerd**: 軽量な Service mesh
* **AWS App Mesh**: AWS マネージド Service mesh

**Istio VirtualService の例**:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews-route
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
```

## Kubernetes ストレージ

Kubernetes は、コンテナ化されたアプリケーション向けにさまざまなストレージオプションを提供します。Pod が再起動または再スケジュールされてもデータを永続化する方法を提供します。

![Kubernetes ストレージアーキテクチャ: Pod 1 と Pod 2 は PersistentVolumeClaim（pvc-1、pvc-2）を通じて PersistentVolume（pv-1、pv-3）にバインドし、StorageClass（standard）が PV を動的にプロビジョニングします。各 PV はクラスター外部の AWS EBS volume（vol-1 から vol-3）により支えられます。](../.gitbook/assets/en-basics-04-kubernetes-introduction-5.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-5.html)

### Volume

Volume は Pod 内のコンテナにマウントできるディレクトリで、Pod のライフサイクルにわたってデータを永続化します。Volume は Pod 内のコンテナ間でデータを共有するためにも使用されます。

**主な Volume の種類**:

* **emptyDir**: 空のディレクトリとして開始し、Pod が削除されると削除
* **hostPath**: host node のファイルシステムを Pod にマウント
* **configMap**: ConfigMap を Volume としてマウント
* **secret**: Secret を Volume としてマウント
* **persistentVolumeClaim**: 永続 Volume を Pod にマウント

**emptyDir Volume の例**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - name: test-container
    image: nginx
    volumeMounts:
    - mountPath: /cache
      name: cache-volume
  volumes:
  - name: cache-volume
    emptyDir: {}
```

### PersistentVolume (PV)

PersistentVolume は、クラスター内のストレージリソースを表す API オブジェクトです。Pod から独立して存在し、cluster administrator によりプロビジョニングされます。

**アクセスモード**:

* **ReadWriteOnce (RWO)**: 単一のノードから read/write でマウント可能
* **ReadOnlyMany (ROX)**: 複数のノードから read-only でマウント可能
* **ReadWriteMany (RWX)**: 複数のノードから read/write でマウント可能

**PersistentVolume の例**:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-example
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: standard
  awsElasticBlockStore:
    volumeID: vol-0123456789abcdef0
    fsType: ext4
```

### PersistentVolumeClaim (PVC)

PersistentVolumeClaim は、ユーザーのストレージリクエストを表す API オブジェクトです。Pod は PVC を通じて PV にアクセスします。

**PersistentVolumeClaim の例**:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-example
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: standard
```

**PVC を使用する Pod の例**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
    - name: myfrontend
      image: nginx
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: pvc-example
```

### StorageClass

StorageClass は、管理者が提供するストレージの「クラス」を記述します。異なるサービス品質レベル、バックアップポリシー、または cluster administrator が決定する任意のポリシーを提供できます。

**StorageClass の例**:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  fsType: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
```

### Dynamic Provisioning

Dynamic Provisioning は、StorageClass を使用して PVC がリクエストされたときに PV を自動的に作成する機能です。

**Dynamic Provisioning の例**:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard  # Storage class for dynamic provisioning
```

### CSI (Container Storage Interface)

CSI は Kubernetes とストレージシステム間の標準インターフェースを提供します。これにより、ストレージプロバイダーは Kubernetes コードを変更せずに独自のストレージドライバーを開発できます。

**主要な CSI Driver**:

* **AWS EBS CSI Driver**: Amazon EBS volume 管理
* **AWS EFS CSI Driver**: Amazon EFS ファイルシステム管理
* **AWS FSx for Lustre CSI Driver**: FSx for Lustre ファイルシステム管理
* **GCE PD CSI Driver**: Google Compute Engine persistent disk 管理
* **Azure Disk CSI Driver**: Azure disk 管理

**CSI Driver デプロイの例**:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  fsType: ext4
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

## Kubernetes の設定とセキュリティ

Kubernetes は、アプリケーションの設定とセキュリティを管理するためのさまざまなオブジェクトおよびメカニズムを提供します。

### ConfigMap

ConfigMap は、設定データを key-value ペアとして保存する API オブジェクトです。Pod は ConfigMap データを環境変数、コマンドライン引数、または設定ファイルとして使用できます。

**ConfigMap の例**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  app.properties: |
    app.name=MyApp
    app.version=1.0.0
    app.environment=production
  log-level: INFO
  max-connections: "100"
```

**ConfigMap を使用する Pod の例**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    env:
    - name: LOG_LEVEL
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: log-level
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: app-config
```

### Secret

Secret は、パスワード、トークン、キーなどの機密情報を保存する API オブジェクトです。ConfigMap と似ていますが、機密データ向けに設計されています。

**Secret の種類**:

* **Opaque**: 任意のユーザー定義データ（デフォルト）
* **kubernetes.io/service-account-token**: Service account token
* **kubernetes.io/dockercfg**: シリアライズされた \~/.dockercfg ファイル
* **kubernetes.io/dockerconfigjson**: シリアライズされた \~/.docker/config.json ファイル
* **kubernetes.io/basic-auth**: basic authentication 用認証情報
* **kubernetes.io/ssh-auth**: SSH authentication 用認証情報
* **kubernetes.io/tls**: TLS client または server 用データ

**Secret の例**:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # base64 encoded "admin"
  password: cGFzc3dvcmQxMjM=  # base64 encoded "password123"
```

**Secret を使用する Pod の例**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: db-client
    image: db-client:1.0
    env:
    - name: DB_USERNAME
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: username
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: password
```

### RBAC (Role-Based Access Control)

RBAC は、Kubernetes API へのアクセスを制御するメカニズムです。Roles と RoleBindings を使用して、ユーザーまたは Service account に特定の権限を付与します。

**主な RBAC オブジェクト**:

* **Role**: namespace 内の権限セットを定義
* **ClusterRole**: クラスター全体の権限セットを定義
* **RoleBinding**: Role をユーザー、グループ、または Service account にバインド
* **ClusterRoleBinding**: ClusterRole をユーザー、グループ、または Service account にバインド

**Role の例**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**RoleBinding の例**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: jane
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

### ServiceAccount

ServiceAccount は、Pod 内で実行されるプロセスに ID を提供します。Pod は Service account を使用して Kubernetes API と通信します。

**ServiceAccount の例**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
```

**ServiceAccount を使用する Pod の例**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: sa-pod
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: myapp:1.0
```

### NetworkPolicy

NetworkPolicy は Pod 間の通信を制御する方法を提供します。デフォルトではすべての Pod が相互に通信できますが、network policy を使用してこれを制限できます。

**NetworkPolicy の例**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 3306
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

### PodSecurityPolicy

PodSecurityPolicy は Pod の作成と更新に関するセキュリティ条件を定義します。これは Kubernetes 1.21 以降非推奨となり、Pod Security Standards に置き換えられました。

**Pod SecurityContext の例**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-context-pod
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

### Pod Security Standards

Pod Security Standards は、Pod のセキュリティ要件を定義する 3 つのポリシーレベルを提供します。

1. **Privileged**: 制限なし、すべての機能を許可
2. **Baseline**: 既知の権限昇格を防止
3. **Restricted**: ベストプラクティスを適用する強力な制限

**Pod Security Standards 適用例**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Kubernetes と Amazon EKS の比較

Amazon EKS (Elastic Kubernetes Service) は AWS が提供するマネージド Kubernetes サービスです。EKS は Kubernetes のすべての基本機能を提供するとともに、AWS サービス統合と管理の利便性を追加します。

### 主な違い

| 特性           | 自己管理 Kubernetes                         | Amazon EKS                                                        |
| ------------------------ | ----------------------------------------------- | ----------------------------------------------------------------- |
| Control Plane の管理 | ユーザーが直接管理                           | AWS が管理                                                    |
| 高可用性        | ユーザーが設定する必要あり                             | デフォルトで提供（複数の Availability Zone にデプロイ） |
| アップグレード                 | ユーザーが直接実施                          | AWS が管理（ユーザーが開始可能）                                |
| セキュリティパッチ         | ユーザーが直接適用                           | AWS が自動適用                                      |
| 認証           | さまざまなオプションの設定が必要              | AWS IAM と統合                                           |
| ネットワーキング               | CNI plugin の選択と設定が必要 | Amazon VPC CNI がデフォルトで提供                                |
| Load Balancing           | 手動設定が必要                   | AWS Load Balancer Controller と統合                          |
| ストレージ                  | ストレージドライバーの設定が必要           | EBS、EFS、FSx CSI Driver と統合                              |
| モニタリング               | 手動セットアップが必要                           | CloudWatch Container Insights と統合                         |
| コスト                     | インフラストラクチャコストのみ                       | Control plane コスト + インフラストラクチャコスト                         |

### EKS の追加機能

1. **AWS IAM Integration**: Kubernetes RBAC と AWS IAM の統合
2. **AWS Load Balancer Controller**: ALB と NLB を Kubernetes Service および Ingress と統合
3. **EKS Managed Node Groups**: Node ライフサイクル管理の自動化
4. **Fargate Profiles**: サーバーレス Kubernetes Pod 実行
5. **VPC CNI Plugin**: AWS VPC ネットワーキングとの統合
6. **CloudWatch Container Insights**: コンテナのモニタリングとロギング
7. **AWS App Mesh**: Service mesh 統合
8. **AWS Distro for OpenTelemetry**: 分散トレーシングとモニタリング
9. **EKS Console and CLI**: 管理インターフェース
10. **EKS Blueprints**: ベストプラクティスに基づくクラスター設定

### EKS 固有のコンポーネント

1. **EKS Control Plane**: 複数の Availability Zone にわたる高可用性
2. **EKS Node AMI**: Kubernetes 向けに最適化された Amazon Linux または Ubuntu AMI
3. **EKS Managed Node Groups**: 自動スケーリングと更新をサポート
4. **EKS Fargate**: サーバーレスコンテナ実行環境
5. **EKS Connector**: 外部 Kubernetes クラスターを AWS console に接続
6. **EKS Anywhere**: オンプレミス環境で EKS 互換クラスターを実行
7. **EKS Distro**: AWS 管理の Kubernetes distribution

### AWS Service 統合

EKS は次の AWS Service と統合します。

1. **Amazon VPC**: ネットワーキングインフラストラクチャ
2. **AWS IAM**: 認証と認可
3. **Amazon ECR**: コンテナイメージリポジトリ
4. **AWS Load Balancer**: アプリケーショントラフィックの分散
5. **Amazon EBS/EFS/FSx**: 永続ストレージ
6. **AWS CloudWatch**: モニタリングとロギング
7. **AWS CloudTrail**: 監査とコンプライアンス
8. **AWS KMS**: 暗号化キー管理
9. **AWS WAF**: Web application firewall
10. **AWS Shield**: DDoS 保護
11. **AWS X-Ray**: 分散トレーシング
12. **AWS App Mesh**: Service mesh
13. **AWS SageMaker**: 機械学習ワークロード
14. **AWS Bedrock**: 生成 AI ワークロード

## Kubernetes を始める

Kubernetes を始める方法はいくつかあります。ここでは、ローカル開発環境と AWS EKS で Kubernetes を開始する方法を簡単に紹介します。

### ローカル開発環境

#### Minikube

Minikube は、ローカルマシン上で single-node Kubernetes クラスターを実行するツールです。

**インストールと起動**:

```bash
# Install
brew install minikube

# Start
minikube start

# Check status
minikube status

# Open dashboard
minikube dashboard
```

#### Kind (Kubernetes in Docker)

Kind は、Docker コンテナをノードとして使用してローカルで Kubernetes クラスターを実行するツールです。

**インストールと起動**:

```bash
# Install
brew install kind

# Create cluster
kind create cluster --name my-cluster

# Check cluster
kind get clusters
kubectl cluster-info --context kind-my-cluster
```

#### Docker Desktop

Docker Desktop は、Mac と Windows で Kubernetes を簡単に実行する機能を提供します。

**セットアップ**:

1. Docker Desktop をインストール
2. Settings > Kubernetes > 「Enable Kubernetes」をチェック
3. 「Apply & Restart」をクリック

### AWS EKS

#### eksctl による EKS Cluster の作成

eksctl は、EKS Cluster を作成および管理するためのシンプルな CLI ツールです。

**インストールと Cluster 作成**:

```bash
# Install eksctl
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Configure AWS CLI
aws configure

# Create EKS cluster
eksctl create cluster \
  --name my-cluster \
  --region ap-northeast-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed

# Check cluster
kubectl get nodes
```

#### AWS Management Console による EKS Cluster の作成

AWS Management Console からも EKS Cluster を作成できます。

**手順**:

1. AWS Management Console にログイン
2. EKS Service に移動
3. 「Create cluster」をクリック
4. Cluster 名、IAM role、VPC、subnet を設定
5. security group を設定
6. logging オプションを設定
7. Cluster を作成
8. node group を追加

### kubectl のインストールと設定

kubectl は Kubernetes クラスターを操作するためのコマンドラインツールです。

**インストール**:

```bash
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Windows (PowerShell)
curl -LO "https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe"
```

**基本コマンド**:

```bash
# Check cluster info
kubectl cluster-info

# List nodes
kubectl get nodes

# Check pods in all namespaces
kubectl get pods --all-namespaces

# Create deployment
kubectl create deployment nginx --image=nginx

# Expose service
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# Check logs
kubectl logs <pod-name>

# Execute command in pod container
kubectl exec -it <pod-name> -- /bin/bash
```

### Kubernetes Dashboard のインストール

Kubernetes Dashboard は、クラスターを管理するための Web ベース UI を提供します。

**インストールとアクセス**:

```bash
# Install dashboard
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# Create admin user
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kubernetes-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kubernetes-dashboard
EOF

# Get token
kubectl -n kubernetes-dashboard create token admin-user

# Access dashboard
kubectl proxy
```

Dashboard には `http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/` でアクセスできます。

## まとめ

Kubernetes は、コンテナ化されたアプリケーションのデプロイ、スケーリング、管理を自動化する強力なプラットフォームです。このドキュメントで扱った主な内容の概要は次のとおりです。

### コアアーキテクチャ

* **Control Plane**: クラスターの頭脳（API Server、etcd、Scheduler、Controller Manager）
* **Worker Nodes**: 実際のアプリケーションを実行するノード（kubelet、kube-proxy、Container Runtime）
* **宣言的設定**: 望ましい状態を定義し、Kubernetes が現在の状態を望ましい状態に一致させる

### 主なオブジェクトとリソース

* **基本オブジェクト**: Pod、Service、Volume、Namespace
* **Workload リソース**: Deployment、StatefulSet、DaemonSet、Job、CronJob
* **設定とセキュリティ**: ConfigMap、Secret、RBAC、ServiceAccount
* **ネットワーキング**: Service、Ingress、NetworkPolicy
* **ストレージ**: PersistentVolume、PersistentVolumeClaim、StorageClass

### 推奨学習パス

**ステップ 1: ローカル環境を構築**

* minikube または kind でローカルクラスターを作成
* kubectl コマンドを学習
* 基本オブジェクト（Pod、Deployment、Service）を実践

**ステップ 2: コア概念を習得**

* Workload リソースを理解して実践
* ConfigMap と Secret による設定管理
* Service と Ingress によるネットワーキングの設定
* PV と PVC によるストレージ管理

**ステップ 3: 高度な機能を学ぶ**

* RBAC とセキュリティポリシー
* Auto Scaling（HPA、VPA、Cluster Autoscaler）
* モニタリングとロギング（Prometheus、Grafana）
* Service mesh（Istio、Linkerd）

**ステップ 4: 本番運用**

* Amazon EKS またはその他のマネージド Kubernetes を使用
* CI/CD pipeline 統合
* 災害復旧とバックアップ戦略
* コスト最適化とリソース管理

### 次のステップ

* **EKS Deep Dive**: EKS 固有の機能（Fargate、VPC CNI、ALB Controller）
* **Advanced Networking**: CNI plugin（Calico、Cilium）
* **Observability**: metrics、logs、tracing
* **GitOps**: ArgoCD、Flux
* **Security Hardening**: Pod Security Standards、Network Policies、OPA/Gatekeeper

Kubernetes は継続的に進化しており、クラウドネイティブアプリケーションの開発と運用の中核要素となっています。このドキュメントが Kubernetes の学習を始める助けになれば幸いです。

### 追加学習リソース

* **公式ドキュメント**: [Kubernetes 公式ドキュメント](https://kubernetes.io/docs/) は最も正確で最新の情報を提供します
* **インタラクティブチュートリアル**: [Kubernetes チュートリアル](https://kubernetes.io/docs/tutorials/) でハンズオン練習が可能です
* **コミュニティ**: [Kubernetes Slack](https://slack.k8s.io/)、[Reddit r/kubernetes](https://reddit.com/r/kubernetes)
* **認定資格**: CKA（Certified Kubernetes Administrator）、CKAD（Certified Kubernetes Application Developer）
* **韓国コミュニティ**: Kubernetes Korea User Group、AWS Korea User Group

## クイズ

この章で学んだ内容を確認するには、[Kubernetes 概要クイズ](../quizzes/basics/04-kubernetes-introduction-quiz.md)に挑戦してください。

## 参考資料

* [Kubernetes 公式ドキュメント](https://kubernetes.io/docs/)
* [Amazon EKS ドキュメント](https://docs.aws.amazon.com/eks/)
* [Kubernetes GitHub リポジトリ](https://github.com/kubernetes/kubernetes)
* [CNCF (Cloud Native Computing Foundation)](https://www.cncf.io/)
* [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
* [Kubernetes Patterns](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)
