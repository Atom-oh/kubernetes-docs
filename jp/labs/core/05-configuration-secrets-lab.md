# ConfigMap と Secret のラボガイド

> **難易度**: 初級
> **所要時間**: 35 分
> **最終更新日**: 2026年9月11日

## 学習目標
- ConfigMap を作成し、Pod で使用する
- Secret を作成し、安全に注入する
- 環境変数による方法と volume mount による方法を比較する

## 前提条件
- [ ] kubectl、Kubernetes クラスター
- [ ] [Configuration](../../core/05-configuration-secrets.md) の学習を完了していること

Bash と既存の使い捨て kind/minikube クラスターを使用します。手順は同じシェルで実行し、前提条件のコマンドが失敗したら中止してください。namespace を作成する前に、選択中の context がこのラボ用クラスターであることを確認してください。以下の認証情報はすべて公開しても問題のないダミーデータであり、このラボではデータベースに接続しません。

```bash
CONFIG_LAB_DIR=$(mktemp -d /tmp/k8s-docs-config.XXXXXX)
: "${CONFIG_LAB_DIR:?mktemp failed}"
CONFIG_LAB_CONTEXT=$(kubectl config current-context)
: "${CONFIG_LAB_CONTEXT:?No context selected}"
printf 'Selected context: %s\n' "$CONFIG_LAB_CONTEXT"
unset CONFIG_LAB_NAMESPACE CONFIG_LAB_UID
CONFIG_LAB_CANDIDATE=$(basename "$CONFIG_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
if CONFIG_LAB_UID=$(kubectl --context "$CONFIG_LAB_CONTEXT" create namespace "$CONFIG_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  CONFIG_LAB_NAMESPACE=$CONFIG_LAB_CANDIDATE
fi
: "${CONFIG_LAB_NAMESPACE:?Namespace creation failed}"
: "${CONFIG_LAB_UID:?Namespace UID missing}"
config_kubectl() {
  kubectl --context "${CONFIG_LAB_CONTEXT:?}" --namespace "${CONFIG_LAB_NAMESPACE:?}" "$@"
}
```

---

## 演習 1: ConfigMap の作成と使用

### 手順

**ステップ 1.1: ConfigMap を作成する**
```bash
# Create from literal values
config_kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

config_kubectl get configmap app-config -o yaml
```

**ステップ 1.2: ファイルから ConfigMap を作成する**
```bash
cat > "${CONFIG_LAB_DIR:?}/app.properties" << 'EOF'
database.host=mysql
database.port=3306
database.name=myapp
EOF

config_kubectl create configmap app-properties --from-file="${CONFIG_LAB_DIR:?}/app.properties"
config_kubectl describe configmap app-properties
```

これらのプロパティはサンプルの設定テキストです。MySQL Service、データベース、認証フローは作成も検証もされません。

**ステップ 1.3: ConfigMap を環境変数として注入する**
```bash
cat > "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-env-demo
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: busybox:1.38.0
    command: ["sh", "-ec", "echo APP_ENV=$APP_ENV LOG_LEVEL=$LOG_LEVEL; exec sleep 3600"]
    envFrom:
    - configMapRef:
        name: app-config
EOF

config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml"
config_kubectl wait --for=condition=ready pod/config-env-demo --timeout=120s
config_kubectl logs config-env-demo
```

想定される出力:
```
APP_ENV=production LOG_LEVEL=info
```

**ステップ 1.4: ConfigMap を volume として mount する**
```bash
cat > "${CONFIG_LAB_DIR:?}/configmap-vol-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-vol-demo
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: busybox:1.38.0
    command: ["sh", "-ec", "cat /config/app.properties; exec sleep 3600"]
    volumeMounts:
    - name: config-volume
      mountPath: /config
      readOnly: true
  volumes:
  - name: config-volume
    configMap:
      name: app-properties
EOF

config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-vol-pod.yaml"
config_kubectl wait --for=condition=ready pod/config-vol-demo --timeout=120s
config_kubectl logs config-vol-demo
```

<details>
<summary>ヒントが必要ですか？</summary>

- `envFrom` はここで使用する ConfigMap のキーを環境変数として取り込みます。
- mount した各キーはファイルになります。更新は kubelet の同期／キャッシュ機構を通じて最終的に反映されますが、即時ではありません。
- `subPath` mount には更新が反映されません。環境変数はコンテナ起動時に固定されるため、新しい値を読み込むには Pod を置き換えてください。ファイルを一度だけ読み込むプロセスにも、明示的な reload／再起動が必要です。
</details>

---

## 演習 2: Secret の管理

### 手順

**ステップ 2.1: Secret を作成する**
```bash
# Public dummy values only. Do not substitute real credentials in shell history.
(
  umask 077
  printf '%s' 'lab-user' > "${CONFIG_LAB_DIR:?}/DB_USER"
  printf '%s' 'not-a-real-password' > "${CONFIG_LAB_DIR:?}/DB_PASSWORD"
)
config_kubectl create secret generic db-secret \
  --from-file=DB_USER="${CONFIG_LAB_DIR:?}/DB_USER" \
  --from-file=DB_PASSWORD="${CONFIG_LAB_DIR:?}/DB_PASSWORD"
# Show key names only, never their values or encoded contents.
config_kubectl get secret db-secret \
  -o go-template='{{range $key, $value := .data}}{{printf "%s\n" $key}}{{end}}'
```

表示してよいのはキー名だけです。ファイルから入力すれば、コマンド引数に実際の認証情報を埋め込まずに済みます。ただし、これらのローカルファイルには平文が含まれるため、ラボ終了後に削除してください。Secret API の応答にある Base64 はエンコードであり、暗号化ではありません。保存時の暗号化、最小権限の RBAC、ローテーションは別途設定する必要があります。この namespace で Pod を作成する権限があれば、Secret を読み取れる場合もあります。

**ステップ 2.2: Secret を Pod に注入する**
非 root コンテナは、ユーザー名、パスワード、長さを表示せず、値が存在することだけを確認します。Secret volume は読み取り専用です。`0440` は 8 進数表記の YAML mode であり、JSON では十進数の `288` です。`fsGroup` により、このコンテナのグループに読み取り権限を付与します。2つの注入方法は比較のために示しており、アプリケーションに値を重複して持たせる必要があるという意味ではありません。

```bash
cat > "${CONFIG_LAB_DIR:?}/secret-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: secret-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 2000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -ec
    - |
      test -n "$DB_USER"
      test -n "$DB_PASSWORD"
      test -s /run/credentials/DB_USER
      test -s /run/credentials/DB_PASSWORD
      printf 'Dummy credentials available through environment and files\n'
      exec sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
    env:
    - name: DB_USER
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_USER
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_PASSWORD
    volumeMounts:
    - name: credentials
      mountPath: /run/credentials
      readOnly: true
  volumes:
  - name: credentials
    secret:
      secretName: db-secret
      defaultMode: 0440
EOF
config_kubectl apply -f "${CONFIG_LAB_DIR:?}/secret-pod.yaml"
config_kubectl wait --for=condition=Ready pod/secret-demo --timeout=120s
config_kubectl logs secret-demo
```

想定される出力:
```
Dummy credentials available through environment and files
```

**ステップ 2.3: オフラインのダミーテキストで Base64 を確認する**
```bash
printf '%s' 'lab-only' | base64 | base64 -d
printf '\n'
```

<details>
<summary>ヒントが必要ですか？</summary>

- このオフライン例で表示するのは公開文字列 `lab-only` だけです。実際に使われている Secret を共有端末やログ上で decode しないでください。
- Secret を更新しても、実行中コンテナの環境変数は変わりません。通常の Secret volume projection は最終的に更新されますが、アプリケーション側でファイルを読み直す必要があります。`subPath` は更新されません。
- 外部 Secret ストア／controller を使うには、それぞれに identity、認可、ローテーションの設定が必要です。ツールをインストールしただけでは、それらの保証は得られません。
</details>

---

## 演習 3: 環境変数と volume mount の比較

### 手順

**ステップ 3.1: ConfigMap を更新し、実行中の Pod を比較する**
```bash
config_kubectl patch configmap app-config --type=merge \
  -p '{"data":{"LOG_LEVEL":"debug"}}'
config_kubectl patch configmap app-properties --type=merge \
  -p '{"data":{"app.properties":"database.host=mysql\ndatabase.port=3306\ndatabase.name=myapp_v2\n"}}'

# The existing container still has LOG_LEVEL=info.
config_kubectl exec config-env-demo -- sh -c 'printf "LOG_LEVEL=%s\n" "$LOG_LEVEL"'

# Reopen the file up to 60 times, with five seconds between attempts.
CONFIG_LAB_PROJECTED=false
for ((attempt=1; attempt<=60; attempt++)); do
  if config_kubectl exec config-vol-demo -- sh -c 'grep -qx "database.name=myapp_v2" /config/app.properties'; then
    CONFIG_LAB_PROJECTED=true
    break
  fi
  sleep 5
done
if [ "$CONFIG_LAB_PROJECTED" = true ]; then
  config_kubectl exec config-vol-demo -- cat /config/app.properties
else
  printf 'Update not observed: inspect Pod events, kubelet connectivity and sync/cache settings\n' >&2
fi

# Replace this bare Pod to read the current environment values.
config_kubectl delete pod config-env-demo --wait=true --timeout=120s &&
  config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml" &&
  config_kubectl wait --for=condition=Ready pod/config-env-demo --timeout=120s &&
  config_kubectl logs config-env-demo
```

元の `config-vol-demo` のログには、起動時に一度だけ読み取った結果が記録されています。その後 mount 済みファイルを再確認すれば projection を検証できますが、アプリケーションが自動で reload したことの証明にはなりません。再試行回数と待機時間は、この演習で観察するための設定です。コマンドの実行時間も経過時間に加わり、Kubernetes がこの時間内に反映することを保証するものではありません。置き換えた Pod が正常に起動した後、そのログには `LOG_LEVEL=debug` と表示されるはずです。

---

## クリーンアップ
```bash
if [[ -n ${CONFIG_LAB_NAMESPACE:-} && -n ${CONFIG_LAB_UID:-} ]]; then
  current_uid=$(kubectl --context "${CONFIG_LAB_CONTEXT:?}" get namespace "$CONFIG_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [ "$current_uid" = "$CONFIG_LAB_UID" ]; then
    kubectl --context "$CONFIG_LAB_CONTEXT" delete namespace "$CONFIG_LAB_NAMESPACE" --timeout=120s
  fi
fi
if [[ -n ${CONFIG_LAB_DIR:-} ]]; then
  rm -f -- "$CONFIG_LAB_DIR/app.properties" "$CONFIG_LAB_DIR/configmap-env-pod.yaml" \
    "$CONFIG_LAB_DIR/configmap-vol-pod.yaml" "$CONFIG_LAB_DIR/secret-pod.yaml" \
    "$CONFIG_LAB_DIR/DB_USER" "$CONFIG_LAB_DIR/DB_PASSWORD"
  rmdir -- "$CONFIG_LAB_DIR"
fi
unset -f config_kubectl
```

## 参考資料と検証範囲

- [ConfigMap の projection と更新](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Secret のセキュリティと更新](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Secret のファイル権限と環境変数](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)

検証では、シェル構文、マニフェスト、ローカルの fixture を対象とします。この監査では Kubernetes Secret、Pod、namespace、外部 Secret ストアを作成または参照していません。

## 次のステップ
- [Configuration クイズ](../../quizzes/core/05-configuration-secrets-quiz.md)
- [EKS クラスター作成ラボ](../eks/01-eks-cluster-creation-lab.md)
