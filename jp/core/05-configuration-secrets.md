# 設定と Secret

> **サポート対象バージョン**: Kubernetes 1.35、1.36、1.37
> **最終更新**: 2026年10月16日

Kubernetes では、設定管理はアプリケーション設定をコードから分離して管理するうえで重要な要素です。この章では、ConfigMap、Secret、環境変数、Volume を通じた設定のマウントなど、Kubernetes の設定管理方法を詳しく説明します。

## Lab 環境のセットアップ

このドキュメントの例に沿って進めるには、次のツールと環境が必要です。

### 必要なツール
- API サーバーとのマイナーバージョン差が 1 以内の kubectl
- 動作する Kubernetes クラスター（EKS、minikube、kind など）

### 設定例のセットアップ

```bash
# Create namespace
kubectl create namespace config-demo

# Create ConfigMap
kubectl -n config-demo create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=APP_DEBUG=false \
  --from-literal=APP_PORT=8080

# Create Secret
kubectl -n config-demo create secret generic app-secrets \
  --from-literal=DB_USER=admin \
  --from-literal=DB_PASSWORD=s3cr3t \
  --from-literal=API_KEY=abcdef123456

# Create Pod using ConfigMap and Secret
kubectl -n config-demo apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-test-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: ["sh", "-c", 'test -n "$DB_PASSWORD" && echo "Secret available" && sleep 3600']
    env:
    - name: APP_ENV
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: APP_ENV
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: app-secrets
          key: DB_PASSWORD
  restartPolicy: Never
EOF

# Check Pod logs
kubectl -n config-demo logs config-test-pod
```

## 設定管理の概要

![クラスター管理者、GitOps パイプライン、外部システムが ConfigMap と Secret を作成し、Pod はそれらを環境変数、Volume マウント、image pull secret として使用します。また、高度な機能として ConfigMap は sidecar の自動リロードに、Secret は KSOPS 暗号化および Vault Injector の動的インジェクションに使用されます。](../.gitbook/assets/en-core-05-configuration-secrets-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-0.html)

## 目次

1. [ConfigMap](#configmap)
2. [Secret](#secret)
3. [環境変数](#environment-variables)
4. [Volume を通じた設定のマウント](#mounting-configuration-through-volumes)
5. [設定のベストプラクティス](#configuration-best-practices)
6. [Amazon EKS での設定管理](#configuration-management-in-amazon-eks)

## ConfigMap

> **重要な概念**: ConfigMap は設定データをキーと値のペアで保存し、アプリケーションコードと設定を分離します。

ConfigMap は、設定データをキーと値のペアで保存する API オブジェクトです。ConfigMap を使用すると、設定データをコンテナイメージから分離でき、アプリケーションの可搬性が向上します。

### ConfigMap と Secret の比較

| 機能 | ConfigMap | Secret |
|---------|-----------|--------|
| **目的** | 一般的な設定データ | 機密性の高い設定データ |
| **API 表現** | UTF-8 の `data` または Base64 の `binaryData` | Base64 の `data`。書き込み時は `stringData` も使用可能 |
| **サイズ上限** | 1 MiB | 1 MiB |
| **保存時の暗号化** | API サーバーまたはプラットフォームの設定による | API サーバーまたはプラットフォームの設定による |
| **Volume タイプ** | configMap | secret |
| **ユースケース** | 環境変数、設定ファイル | パスワード、トークン、証明書 |
| **自動更新** | Volume としてマウント時に遅延する可能性あり | Volume としてマウント時に遅延する可能性あり |

### ConfigMap の作成方法

ConfigMap はさまざまな方法で作成できます。

1. **命令型の作成**:

```bash
# Create from literal values
kubectl create configmap my-config --from-literal=key1=value1 --from-literal=key2=value2

# Create from file
kubectl create configmap my-config --from-file=config.properties

# Create from directory
kubectl create configmap my-config --from-file=config-dir/
```

2. **宣言型の作成**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  # Simple key-value pairs
  database.host: "mysql"
  database.port: "3306"

  # File-like configuration
  config.yaml: |
    server:
      port: 8080
    logging:
      level: INFO
    features:
      enabled: true
```

### ConfigMap の使用方法

ConfigMap は次の方法で使用できます。

1. **環境変数として使用**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: config-env-pod
spec:
  containers:
  - name: app
    image: nginx
    env:
    # Single key-value reference
    - name: DB_HOST
      valueFrom:
        configMapKeyRef:
          name: my-config
          key: database.host
    # All key-value references
    envFrom:
    - configMapRef:
        name: my-config
```

![ConfigMap のキーと値のデータ（key1、key2、config.properties）は、環境変数、マウントされた Volume、コマンドライン引数という 3 つの方法で Pod により使用されます。環境変数のパスは env.key1/env.key2 に、Volume のパスはコンテナ内の /etc/config 配下のファイルに解決されます。](../.gitbook/assets/en-core-05-configuration-secrets-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-1.html)

### ConfigMap の作成

ConfigMap はさまざまな方法で作成できます。

#### 命令型

```bash
# Create from literal values
kubectl create configmap my-config --from-literal=key1=value1 --from-literal=key2=value2

# Create from file
kubectl create configmap my-config --from-file=config.properties

# Create from directory
kubectl create configmap my-config --from-file=config-dir/
```

#### 宣言型

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  # Simple key-value pairs
  key1: value1
  key2: value2
  # File-like configuration
  config.properties: |
    property1=value1
    property2=value2
  # JSON configuration
  config.json: |
    {
      "property1": "value1",
      "property2": "value2"
    }
```

### ConfigMap の使用

ConfigMap は Pod 内で次の方法により使用できます。

#### 環境変数として使用

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    # Use single key-value pair
    - name: SPECIAL_KEY
      valueFrom:
        configMapKeyRef:
          name: my-config
          key: key1
    # Use all key-value pairs as environment variables
    envFrom:
    - configMapRef:
        name: my-config
  restartPolicy: Never
```

#### Volume としてマウント

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls /etc/config/" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

#### 特定のキーのみをマウント

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/config/key1" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
      items:
      - key: key1
        path: key1
  restartPolicy: Never
```

### ConfigMap の更新

変更可能な ConfigMap と Secret を通常の Volume としてマウントした場合、内容は最終的に更新されます。反映までの時間は kubelet の同期間隔と変更検出・キャッシュの設定によって異なります。アプリケーション側でファイルを読み直すか再読み込みする必要があります。`subPath` マウントには更新が反映されません。実行中プロセスの環境変数は変わらないため、新しい値を使うには Deployment のロールアウトなどで Pod を再作成します。

```bash
kubectl edit configmap my-config
```

または

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  key1: updated-value1
  key2: value2
```

```bash
kubectl apply -f updated-configmap.yaml
```

## Secret

Secret は、パスワード、OAuth トークン、SSH キーなどの機密情報を保存する API オブジェクトです。Secret は ConfigMap と似ていますが、機密データの保存に追加のセキュリティ機能を提供します。

![Kubernetes Secret のサポートタイプ（Opaque、TLS、dockerconfigjson、basic-auth）、その Base64 エンコードとオプションの etcd 暗号化ストレージ、そして Pod が環境変数、マウントされた Volume、image pull secret として使用する 3 つの方法を示しています。](../.gitbook/assets/en-core-05-configuration-secrets-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-2.html)

### Secret のタイプ

Kubernetes はさまざまなタイプの Secret を提供しています。

- **Opaque**: デフォルトタイプで、任意のユーザー定義データを保存します。
- **kubernetes.io/service-account-token**: ServiceAccount トークンを保存します。
- **kubernetes.io/dockercfg**: `.dockercfg` ファイルのシリアライズ形式を保存します。
- **kubernetes.io/dockerconfigjson**: `.docker/config.json` ファイルのシリアライズ形式を保存します。
- **kubernetes.io/basic-auth**: Basic 認証の認証情報を保存します。
- **kubernetes.io/ssh-auth**: SSH 認証の認証情報を保存します。
- **kubernetes.io/tls**: TLS 証明書とキーを保存します。
- **bootstrap.kubernetes.io/token**: Bootstrap トークンデータを保存します。

### Secret の作成

Secret はさまざまな方法で作成できます。

#### 命令型

```bash
# Create from literal values
kubectl create secret generic my-secret --from-literal=username=admin --from-literal=password=secret

# Create from files
kubectl create secret generic my-secret --from-file=username=username.txt --from-file=password=password.txt

# Create TLS secret
kubectl create secret tls my-tls-secret --cert=path/to/cert.crt --key=path/to/key.key

# Create Docker registry secret
kubectl create secret docker-registry my-registry-secret \
  --docker-server=DOCKER_REGISTRY_SERVER \
  --docker-username=DOCKER_USER \
  --docker-password=DOCKER_PASSWORD \
  --docker-email=DOCKER_EMAIL
```

#### 宣言型

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
data:
  # base64 encoded values
  username: YWRtaW4=  # admin
  password: c2VjcmV0  # secret
```

または、`stringData` フィールドを使用してエンコードされていない値を指定できます。

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
stringData:
  # Unencoded values
  username: admin
  password: secret
```

### Secret の使用

Secret は Pod 内で次の方法により使用できます。

#### 環境変数として使用

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: ["/bin/sh", "-c", 'test -n "$USERNAME" && echo "Secret available"']
    env:
    # Use single key-value pair
    - name: USERNAME
      valueFrom:
        secretKeyRef:
          name: my-secret
          key: username
    # Use all key-value pairs as environment variables
    envFrom:
    - secretRef:
        name: my-secret
  restartPolicy: Never
```

#### Volume としてマウント

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls /etc/secret/" ]
    volumeMounts:
    - name: secret-volume
      mountPath: /etc/secret
  volumes:
  - name: secret-volume
    secret:
      secretName: my-secret
  restartPolicy: Never
```

#### Image Pull Secret

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: private-image-pod
spec:
  containers:
  - name: private-image-container
    image: private-registry.example.com/my-app:v1
  imagePullSecrets:
  - name: my-registry-secret
```

### Secret のセキュリティに関する考慮事項

Secret はデフォルトで Base64 エンコードされていますが、これは暗号化ではありません。Secret のセキュリティを強化するには、次の方法を検討してください。

1. **etcd 暗号化**: etcd に保存される Secret を暗号化します。
2. **RBAC**: Secret へのアクセスを制限します。
3. **NetworkPolicy**: 対応する環境では、API や外部ストアへのネットワークアクセスを制限します。Secret オブジェクトへの認可は NetworkPolicy ではなく RBAC で制御します。
4. **外部 Secret 管理ツール**: AWS Secrets Manager、HashiCorp Vault などの外部 Secret 管理ツールを使用します。

ここに示す認証情報はすべて学習用のダミー値です。Secret の内容や Base64 化した実値をログに出したり、コミットしたりしないでください。CLI 引数に値を直接記述するのではなく、保護された入力ファイルまたは外部の Secret 管理サービスを使用します。Secret を使う Pod を作成できるユーザーは、Secret を直接読み取る権限がなくても、その値を取得できる場合があります。

#### etcd 暗号化の設定

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64 encoded key>
    - identity: {}
```

セルフマネージドクラスターでは、このファイルを `--encryption-provider-config` で読み込み、暗号化キーを保護したうえで、既存の Secret を再書き込みして暗号化します。この設定ファイルは `kubectl apply` で適用する Kubernetes リソースではありません。EKS の暗号化は AWS が管理します（以下を参照）。

<span id="environment-variables"></span>

## 環境変数

環境変数は、設定情報をコンテナに渡すシンプルな方法です。Kubernetes は環境変数を設定する複数の方法を提供しています。

![Kubernetes が Container の環境変数を設定できる 4 つのソース、すなわち直接指定する静的値、ConfigMap のキーまたは完全な envFrom 参照、Secret のキーまたは完全な envFrom 参照、そして Downward API のフィールドまたはリソース参照を示しています。](../.gitbook/assets/en-core-05-configuration-secrets-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-3.html)

### 直接設定

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: ENVIRONMENT
      value: "production"
    - name: LOG_LEVEL
      value: "INFO"
  restartPolicy: Never
```

### ConfigMap から設定

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: ENVIRONMENT
      valueFrom:
        configMapKeyRef:
          name: my-config
          key: key1
  restartPolicy: Never
```

### Secret から設定

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: ["/bin/sh", "-c", 'test -n "$DATABASE_PASSWORD" && echo "Secret available"']
    env:
    - name: DATABASE_PASSWORD
      valueFrom:
        secretKeyRef:
          name: my-secret
          key: password
  restartPolicy: Never
```

### Downward API を通じた設定

Downward API を使用すると、Pod とコンテナの情報を環境変数として公開できます。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: downward-api-pod
  labels:
    app: myapp
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: POD_NAME
      valueFrom:
        fieldRef:
          fieldPath: metadata.name
    - name: POD_NAMESPACE
      valueFrom:
        fieldRef:
          fieldPath: metadata.namespace
    - name: POD_IP
      valueFrom:
        fieldRef:
          fieldPath: status.podIP
    - name: NODE_NAME
      valueFrom:
        fieldRef:
          fieldPath: spec.nodeName
    - name: CONTAINER_CPU_REQUEST
      valueFrom:
        resourceFieldRef:
          containerName: test-container
          resource: requests.cpu
  restartPolicy: Never
```

<span id="mounting-configuration-through-volumes"></span>

## Volume を通じた設定のマウント

Volume を通じて設定ファイルをコンテナにマウントする方法は、環境変数よりも柔軟な設定管理方法を提供します。

![Pod は ConfigMap または Secret をバックエンドとする Volume を定義し、その Container はそれらの Volume を参照する Volume Mount を介してマウントします。完全な Volume マウント、特定のキーのみ（items）、読み取り専用（readOnly）、subPath マウントという 4 つのマウントオプションがあります。](../.gitbook/assets/en-core-05-configuration-secrets-4.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-4.html)

### ConfigMap Volume

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-volume-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls -la /etc/config" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

### Secret Volume

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-volume-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls -la /etc/secret" ]
    volumeMounts:
    - name: secret-volume
      mountPath: /etc/secret
  volumes:
  - name: secret-volume
    secret:
      secretName: my-secret
  restartPolicy: Never
```

### 特定ファイルのマウント

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: specific-file-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/config/config.properties" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
      items:
      - key: config.properties
        path: config.properties
  restartPolicy: Never
```

### 読み取り専用マウント

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: readonly-mount-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls -la /etc/config" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
      readOnly: true
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

### SubPath マウント

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: subpath-mount-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/config/config.properties" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config/config.properties
      subPath: config.properties
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

<span id="configuration-best-practices"></span>

## 設定のベストプラクティス

Kubernetes で設定を管理するときは、次のベストプラクティスを検討してください。

### 1. 設定をコードから分離する

アプリケーションコードと設定を別々に管理します。これにより、設定変更時にアプリケーションを再ビルドする必要がなくなります。

### 2. 環境別の設定管理

開発、テスト、本番など、異なる環境の設定を別々に管理します。namespace を使用して環境を分離し、環境ごとに異なる ConfigMap と Secret を使用できます。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: development
data:
  environment: development
  log_level: DEBUG
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: production
data:
  environment: production
  log_level: INFO
```

### 3. 機密情報には Secret を使用する

パスワード、API キー、証明書などの機密情報を保存するには、常に Secret を使用してください。ConfigMap は機密でない設定データにのみ使用します。

### 4. イミュータビリティを維持する

設定を変更する場合は、既存のものを変更するのではなく新しいバージョンを作成します。これによりロールバックが容易になり、設定変更履歴を追跡できます。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config-v1
immutable: true
data:
  log_level: INFO
  # Configuration data
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config-v2
immutable: true
data:
  log_level: DEBUG
  # Updated configuration data
```

### 5. 設定変更時に Pod を再起動する

環境変数として使用する設定を更新するには、Pod の再起動が必要です。Deployment を使用してローリングアップデートを実行してください。

```bash
kubectl rollout restart deployment/my-deployment
```

### 6. 設定を検証する

適用する前に設定を検証します。無効な設定はアプリケーションの障害を引き起こす可能性があります。

### 7. 設定を文書化する

設定オプションとその影響を文書化します。これはチームメンバーが設定を理解し、管理するのに役立ちます。

### リソース要求と QoS

リソース要求はスケジューリングと実行時の割り当てを導きますが、アプリケーションがその量を必ず消費するという意味ではありません。CPU limit は CPU 使用を抑制し、memory limit は OOM による終了を引き起こすことがあります。クイズのコンテナ単位の例では、Guaranteed になるにはすべてのコンテナで CPU と memory の request/limit がそれぞれ等しくなければなりません。BestEffort ではどちらも設定せず、それ以外は Burstable です。Pod 単位のリソース設定も QoS に影響する場合があります。ノードのメモリ逼迫による退避では、priority と request に対する使用量も考慮されます。[リソース管理](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)と [Pod QoS](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/)を参照してください。

## Amazon EKS における設定管理 {#configuration-management-in-amazon-eks}

Amazon EKS では、Kubernetes の基本的な設定管理機能に加えて、AWS のさまざまなサービスを使用し、設定と Secret を管理できます。このセクションでは、EKS で設定を管理するさまざまな方法と AWS サービスとの統合について説明します。

![Amazon EKS クラスターでは、ネイティブ Kubernetes ConfigMap と Secret を使用するとともに、AWS Secrets Manager、Parameter Store、AppConfig、KMS、IAM と統合します。External Secrets Operator、ASCP、IRSA、ACK などの統合ツールは Secret を作成またはマウントし、KMS で暗号化して、Pod にスコープを限定した IAM 権限を付与します。](../.gitbook/assets/en-core-05-configuration-secrets-5.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-5.html)

### AWS Secrets Manager との統合

AWS Secrets Manager は、データベース認証情報、API キー、その他の Secret を安全に保存・管理するサービスです。External Secrets Operator は Kubernetes Secret の状態を調整し、Secrets Store CSI Driver と組み合わせた ASCP は外部の値をファイルとしてマウントします。Kubernetes Secret への同期と自動ローテーションには、CSI Driver のオプション設定が必要です。

#### External Secrets Operator のインストール

```bash
# Install External Secrets Operator using Helm
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

#### SecretStore を作成する

```yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: my-namespace
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: my-serviceaccount
```

#### ExternalSecret を作成する

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: my-namespace
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: db-credentials
  data:
  - secretKey: username
    remoteRef:
      key: prod/db/credentials
      property: username
  - secretKey: password
    remoteRef:
      key: prod/db/credentials
      property: password
```

#### IRSA（IAM Roles for Service Accounts）のセットアップ

External Secrets Operator には AWS Secrets Manager にアクセスするための適切な IAM 権限が必要です。IRSA を使用して、IAM ロールを Kubernetes ServiceAccount に関連付けられます。

```bash
# Create OIDC provider
eksctl utils associate-iam-oidc-provider \
  --cluster my-cluster \
  --approve

# Create IAM role and service account
eksctl create iamserviceaccount \
  --cluster my-cluster \
  --namespace my-namespace \
  --name my-serviceaccount \
  --attach-policy-arn arn:aws:iam::123456789012:policy/ReadAppDatabaseSecret \
  --approve
```

まず `prod/db/credentials` の完全な ARN に対象を限定し、`secretsmanager:GetSecretValue` と `secretsmanager:DescribeSecret` を許可する `ReadAppDatabaseSecret` policy を作成します。カスタマー管理キーが必要な場合に限り、対象を絞った `kms:Decrypt` を追加してください。IAM trust policy は、このクラスター、namespace、ServiceAccount に一致させます。SecretStore を作成する前に、ESO と v1 CRD、namespace、ServiceAccount を用意します。

### AWS Parameter Store の使用

AWS Systems Manager Parameter Store は、設定データと Secret 値を階層的に保存・管理するサービスです。ローテーション、ライフサイクル、アクセス要件に応じて Parameter Store と Secrets Manager を選択してください。料金はパラメータの tier と API 使用量によって異なります。

#### ASCP（AWS Secrets and Configuration Provider）のインストール

```bash
# Install ASCP
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system

# Install AWS provider
kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
```

#### SecretProviderClass を作成する

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: aws-parameters
  namespace: my-namespace
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: /my-app/config/log-level
        objectType: ssmparameter
      - objectName: /my-app/config/environment
        objectType: ssmparameter
```

#### Pod で Parameter Store の値を使用する

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: parameter-store-pod
  namespace: my-namespace
spec:
  serviceAccountName: parameter-reader
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: parameters-store-volume
      mountPath: "/mnt/parameters"
      readOnly: true
  volumes:
  - name: parameters-store-volume
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: aws-parameters
```

`parameter-reader` には、2 つの parameter ARN に対する `ssm:GetParameters` を許可する IRSA ロールまたは Pod Identity の関連付けを設定し、必要な場合は対象を絞った KMS 復号権限を付与します。先ほどの Secrets Manager ロールには SSM 権限がありません。ASCP が利用できるのは対応するノードとアドオンの組み合わせに限られ、CSI マウントは Fargate では動作しません。Hybrid Nodes では、明示的にサポートされたアドオンのバージョンと認証情報の設定が必要です。

### AWS AppConfig による動的設定

AWS AppConfig はアプリケーション設定を管理およびデプロイするサービスです。AppConfig を使用すると、アプリケーションを再デプロイせずに設定を動的に更新できます。

#### AppConfig Agent の Sidecar パターン

アプリケーションは agent のローカル HTTP endpoint から設定を取得し、定期的に再取得して反映する必要があります。共有 `emptyDir` を用意するだけでは、agent は `/config/config.json` に書き込みません。先に application、environment、configuration profile、deployment を作成し、対象の設定に対する `appconfig:StartConfigurationSession` と `appconfig:GetLatestConfiguration` を Pod の IAM identity に許可します。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-namespace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: appconfig-reader
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: CONFIG_URL
          value: http://localhost:2772/applications/MyApp/environments/Production/configurations/MyConfig
      - name: appconfig-agent
        image: public.ecr.aws/aws-appconfig/aws-appconfig-agent:2.x
        env:
        - name: SERVICE_REGION
          value: us-west-2
        - name: POLL_INTERVAL
          value: "45s"
        - name: REQUEST_TIMEOUT
          value: "15s"
        - name: HTTP_PORT
          value: "2772"
        - name: HTTP_HOST
          value: localhost
        - name: PREFETCH_LIST
          value: MyApp:Production:MyConfig
```

アプリケーション image は `CONFIG_URL` からの設定取得と、sidecar の起動中に再試行する処理を実装している必要があります。デプロイ前に `appconfig-reader` と権限を絞った AWS identity を作成し、本番ではテスト済みの agent バージョンまたは digest を固定してください。ここに示すのはコンテナ agent の設定であり、Lambda extension の環境変数ではありません。

### EKS Fargate Profile による設定

EKS Fargate を使用すると、ノードを管理せずに Kubernetes Pod を実行できます。Fargate Profile は EKS API リソースであり、Kubernetes ネイティブのオブジェクトではありません。次の `eksctl` 設定では、プライベートサブネット ID と Pod execution role を置き換え、`eksctl create fargateprofile -f fargate-profile.yaml` で作成します。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: my-profile
  podExecutionRoleARN: arn:aws:iam::123456789012:role/my-pod-execution-role
  selectors:
  - namespace: my-namespace
    labels:
      environment: production
  subnets:
  - subnet-1234567890abcdef0
  - subnet-0abcdef1234567890
```

### AWS KMS による Secret の暗号化

<span id="secret-encryption-with-aws-kms"></span>

Kubernetes 1.28 以降の EKS クラスターでは、Secret と ConfigMap を含むすべての Kubernetes API データが、AWS 所有キーを使って[デフォルトで envelope encryption により暗号化](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)されます。カスタマー管理 KMS キーは任意であり、暗号化を有効にするために必須ではありません。

対象となる既存クラスターにカスタマー管理キーを関連付けるには、`update-cluster-config` ではなく `associate-encryption-config` を使用します。適用前にキーのリージョン、policy、権限、関連付けの制約を確認してください。次の例ではキーを 1 つ作成し、返された ARN を再利用します。

```bash
set -eu
KEY_ARN=$(aws kms create-key --region us-west-2 \
  --description "EKS customer-managed encryption key" \
  --query KeyMetadata.Arn --output text)
aws kms create-alias --region us-west-2 \
  --alias-name alias/eks-secrets --target-key-id "$KEY_ARN"

aws eks associate-encryption-config --region us-west-2 \
  --cluster-name my-cluster \
  --encryption-config "resources=secrets,provider={keyArn=$KEY_ARN}"
```

更新 ID を使って `aws eks describe-update` で完了を確認し、`aws eks describe-cluster --name my-cluster --region us-west-2 --query cluster.encryptionConfig` の結果も確認します。カスタマー管理設定が表示されないことは、デフォルト暗号化が無効であることを意味しません。

### AWS IAM による Secret アクセス制御

IRSA（IAM Roles for Service Accounts）を使って IAM ロールを Kubernetes ServiceAccount に関連付けると、Pod は AWS サービスに安全にアクセスできます。

#### ServiceAccount を作成する

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: my-namespace
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-iam-role
```

#### Pod で ServiceAccount を使用する

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: my-namespace
spec:
  serviceAccountName: my-service-account
  containers:
  - name: app
    image: my-app:latest
```

### EKS 設定のベストプラクティス

EKS で設定を管理するときは、次のベストプラクティスを検討してください。

1. **ワークロード ID を使用する**: 対応するコンピューティング環境では EKS Pod Identity または IRSA を使い、権限を必要最小限にします。Fargate アプリケーションには IRSA を使用します。Pod execution role はインフラストラクチャ用であり、アプリケーションの認証情報には使いません。

2. **Secret を暗号化する**: KMS を使用して EKS クラスター内の Secret を暗号化します。

3. **外部 Secret 管理**: AWS Secrets Manager や Parameter Store などの外部 Secret 管理サービスを使用して機密情報を管理します。

4. **設定のバージョン管理**: AWS AppConfig または Parameter Store を使用して設定バージョンを管理します。

5. **環境別の設定分離**: 開発、テスト、本番環境の設定を別々に管理します。Kubernetes namespace と AWS リソースタグを使用します。

6. **IAM ポリシーを最小化する**: AWS サービスへアクセスする際は、最小権限の原則に従います。

7. **設定の自動化**: AWS CloudFormation、AWS CDK、Terraform などのツールを使用して設定管理を自動化します。

### EKS 設定管理ツール

EKS で設定を管理するのに役立つツールを見ていきましょう。

#### AWS Controllers for Kubernetes（ACK）

ACK は Kubernetes から AWS リソースを管理できるツールです。ACK を使用すると、Kubernetes マニフェストを通じて AWS リソースを作成および管理できます。

```yaml
apiVersion: secretsmanager.services.k8s.aws/v1alpha1
kind: Secret
metadata:
  name: my-secret
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: my-secret
  description: "My secret created via ACK"
  recoveryWindowInDays: 30
```

ACK Secrets Manager controller と、それに必要な IAM ロールおよび CRD を先にインストールしてください。この manifest が管理するのは Secrets Manager の Secret コンテナの metadata であり、password の生成や Kubernetes Secret の作成は行いません。管理された Secret の運用手順を通じて値を登録してください。

#### eksctl

eksctl は EKS クラスターを作成および管理するためのコマンドラインツールです。eksctl を使用してクラスター設定を管理できます。

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
secretsEncryption:
  keyARN: arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
```

```bash
eksctl create cluster -f cluster.yaml
```

#### AWS CDK

AWS CDK（Cloud Development Kit）は、プログラミング言語を使用して AWS リソースを定義するためのツールです。CDK を使用して EKS クラスターと関連リソースを定義できます。

この補助関数は既存の CDK EKS cluster と Secret construct を使用し、その Secret の読み取り権限だけを付与します。namespace は事前に作成し、クラスターには互換性のある kubectl provider を設定してください。

```typescript
import * as eks from 'aws-cdk-lib/aws-eks';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

export function addSecretReader(
  cluster: eks.Cluster,
  secret: secretsmanager.ISecret,
): eks.ServiceAccount {
  const serviceAccount = cluster.addServiceAccount('SecretReader', {
    name: 'my-service-account',
    namespace: 'my-namespace',
  });
  secret.grantRead(serviceAccount);
  return serviceAccount;
}
```

## まとめ

この章では、Kubernetes の設定管理方法について学びました。ConfigMap と Secret はアプリケーション設定を管理する基本的な方法を提供し、この設定を環境変数と Volume を通じてコンテナに渡すことができます。また、設定管理のベストプラクティスと外部設定管理ツールについても説明しました。

Amazon EKS 環境では、Kubernetes の基本的な設定管理機能と AWS サービスを併用することで、より強力で安全な設定管理を実現できます。AWS Secrets Manager、Parameter Store、KMS、IAM などのサービスと統合して Secret を安全に管理し、IRSA を通じて Pod に最小限の権限を付与できます。さらに、AWS AppConfig を使用すると、アプリケーションを再デプロイせずに設定を動的に更新できます。

効果的な設定管理は、Kubernetes アプリケーションの保守性、スケーラビリティ、セキュリティを向上させるうえで重要です。アプリケーションの要件に適した設定管理戦略を選択し、ベストプラクティスに従うことが重要です。EKS 環境では、AWS サービスとの統合を通じて、より強力な設定管理ソリューションを構築できます。

次の章では、Kubernetes のセキュリティについて学びます。

## クイズ

この章で学んだ内容を確認するには、[設定と Secret のクイズ](../quizzes/core/05-configuration-secrets-quiz.md)に挑戦してください。

## 参考資料

- [Kubernetes 公式ドキュメント - ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Kubernetes 公式ドキュメント - Secret](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes 公式ドキュメント - 環境変数](https://kubernetes.io/docs/tasks/inject-data-application/define-environment-variable-container/)
- [Kubernetes 公式ドキュメント - ConfigMap を使用するよう Pod を設定する](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
- [Kubernetes 公式ドキュメント - Secret を使用して認証情報を安全に配布する](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)
- [Helm 公式ドキュメント](https://helm.sh/docs/)
- [Kustomize 公式ドキュメント](https://kustomize.io/)
- [External Secrets Operator 公式ドキュメント](https://external-secrets.io/latest/)
- [AWS Secrets Manager 公式ドキュメント](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [AWS Systems Manager Parameter Store 公式ドキュメント](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [AWS AppConfig 公式ドキュメント](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- [EKS 公式ドキュメント - IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS 公式ドキュメント - Secret の暗号化](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html)
- [AWS Controllers for Kubernetes（ACK）公式ドキュメント](https://aws-controllers-k8s.github.io/community/)
