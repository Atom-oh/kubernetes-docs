# Pod と Workload のラボガイド

> **難易度**: 初級
> **所要時間**: 50 分
> **最終更新**: 2026年9月11日

## 学習目標
- YAML を使って Pod を作成および管理する
- Deployment をデプロイしてスケールする
- ローリングアップデートとロールバックを実施する

## 前提条件
- [ ] kubectl がインストールされ、クラスター（minikube または kind）にアクセスできること
- [ ] [Pod と Workload](../../core/02-pods-and-workloads.md) の学習を完了していること

使い捨ての既存 kind/minikube クラスターを用意し、ラボ用 namespace の作成とサンプルイメージの取得に必要な権限を確認してください。セットアップを実行する前に、選択中の context を確認します。Bash セッションは1つだけ使ってください。このラッパーが context と namespace を固定します。以下の手順を実行すると実際に変更が加わります。この監査ではクラスター操作を行っていません。

```bash
WORKLOADS_LAB_DIR=$(mktemp -d /tmp/k8s-docs-workloads.XXXXXX)
: "${WORKLOADS_LAB_DIR:?mktemp failed}"
WORKLOADS_LAB_CONTEXT=$(kubectl config current-context)
: "${WORKLOADS_LAB_CONTEXT:?No current context selected}"
printf 'Selected context: %s\n' "$WORKLOADS_LAB_CONTEXT"
WORKLOADS_LAB_CANDIDATE=$(basename "$WORKLOADS_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
unset WORKLOADS_LAB_NAMESPACE WORKLOADS_LAB_GOOD_REVISION
if WORKLOADS_LAB_UID=$(kubectl --context "$WORKLOADS_LAB_CONTEXT" create namespace "$WORKLOADS_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  WORKLOADS_LAB_NAMESPACE=$WORKLOADS_LAB_CANDIDATE
else
  printf 'Namespace creation failed; do not continue with workload commands\n' >&2
fi
workload_kubectl() {
  kubectl --context "${WORKLOADS_LAB_CONTEXT:?}" \
    --namespace "${WORKLOADS_LAB_NAMESPACE:?Create the lab namespace first}" "$@"
}
```

---

## 演習 1: Pod の作成と管理

### 手順

**手順 1.1: Pod の YAML を作成する**
```bash
cat > "${WORKLOADS_LAB_DIR:?}/nginx-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: nginx-lab
  labels:
    app: nginx
    env: lab
spec:
  automountServiceAccountToken: false
  containers:
  - name: nginx
    image: nginx:1.30.6
    ports:
    - name: http
      containerPort: 80
    resources:
      requests:
        memory: 64Mi
        cpu: 100m
      limits:
        memory: 128Mi
        cpu: 200m
    readinessProbe:
      httpGet:
        path: /
        port: http
      periodSeconds: 3
EOF
workload_kubectl apply -f "$WORKLOADS_LAB_DIR/nginx-pod.yaml"
```

**手順 1.2: Pod の状態を確認する**
Running フェーズだけでは Ready であることを意味しません。ログの確認や exec の前に、設定済みの HTTP readiness probe が成功するまで待ちます。タイムアウトを成功とみなさず、失敗の原因を調べてください。

```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
workload_kubectl describe pod nginx-lab
workload_kubectl logs nginx-lab
```

**手順 1.3: Pod の内部にアクセスする**
```bash
workload_kubectl exec -it nginx-lab -- sh
# Inside the container:
nginx -v
ls /usr/share/nginx/html/
exit
```

### 確認
```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
```

---

## 演習 2: Deployment

### 手順

**手順 2.1: Deployment を作成する**
意図的な不正イメージへの更新中も、`maxUnavailable` を 0、`maxSurge` を 1 に設定することで、Deployment は既存の Ready なレプリカを維持します。追加分の Pod と終了処理中の Pod に加え、単独 Pod のための空きキャパシティも必要です。無関係な障害が発生した場合の可用性までは保証されません。

```bash
cat > "${WORKLOADS_LAB_DIR:?}/nginx-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  revisionHistoryLimit: 5
  progressDeadlineSeconds: 120
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app: nginx-deploy
  template:
    metadata:
      labels:
        app: nginx-deploy
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
        readinessProbe:
          httpGet:
            path: /
            port: http
          periodSeconds: 3
EOF
workload_kubectl apply -f "$WORKLOADS_LAB_DIR/nginx-deployment.yaml"
```

**手順 2.2: Deployment の状態を確認する**
```bash
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get deployment nginx-deploy
workload_kubectl get replicasets,pods -l app=nginx-deploy
```

**手順 2.3: スケーリング**
```bash
workload_kubectl scale deployment nginx-deploy --replicas=5
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get pods -l app=nginx-deploy
```

<details>
<summary>ヒントを見る</summary>

- `kubectl get pods -w` は変更をリアルタイムで監視します
- ReplicaSet は Deployment によって自動的に管理されます
- ラベルで絞り込むには `-l` オプションを使います
</details>

### 確認
```bash
READY=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
printf 'Ready replicas: %s\n' "$READY"
[ "$READY" = "5" ]
```

---

## 演習 3: ローリングアップデート

### 手順

**手順 3.1: イメージを更新する**
これは、サポートが継続している同じ NGINX リリースのベースイメージのバリエーションを変更するものであり、サポート対象外の古い NGINX バージョンへの変更ではありません。`kubernetes.io/change-cause` により、非推奨の `--record` フラグを使わずに変更の意図を記録できます。ロールバック演習に備え、完了したリビジョンを記録してください。

```bash
workload_kubectl annotate deployment/nginx-deploy \
  kubernetes.io/change-cause="NGINX 1.30.6 Debian to Alpine variant" --overwrite
unset WORKLOADS_LAB_GOOD_REVISION
if workload_kubectl set image deployment/nginx-deploy nginx=nginx:1.30.6-alpine &&
   workload_kubectl rollout status deployment/nginx-deploy --timeout=120s; then
  WORKLOADS_LAB_GOOD_REVISION=$(workload_kubectl get deployment nginx-deploy \
    -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}')
  : "${WORKLOADS_LAB_GOOD_REVISION:?No completed revision recorded}"
else
  printf 'Healthy rollout not confirmed; stop before the failure/rollback exercise\n' >&2
fi
```

**手順 3.2: 更新履歴を確認する**
```bash
workload_kubectl rollout history deployment/nginx-deploy
workload_kubectl get replicasets -l app=nginx-deploy -o wide
```

### 確認
```bash
workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
# Expected configured image: nginx:1.30.6-alpine
```

---

## 演習 4: ロールバック

### 手順

**手順 4.1: 無効なイメージで更新する（意図的なエラー）**
予約済みの `.invalid` レジストリは、この隔離されたラボで意図的に失敗させるために使います。ロールアウトのタイムアウトはスケジューリング、クォータ、API の問題でも発生するため、Pod のイベントと状態を確認してください。ロールバックで復元されるのは保持された Pod テンプレートであり、外部データ、ConfigMap/Secret の内容、データベースのマイグレーションは戻りません。

```bash
workload_kubectl annotate deployment/nginx-deploy \
  kubernetes.io/change-cause="Intentional lab image-pull failure" --overwrite
workload_kubectl set image deployment/nginx-deploy nginx=registry.invalid/training/nginx:unavailable
if workload_kubectl rollout status deployment/nginx-deploy --timeout=30s; then
  printf 'Unexpected completion; inspect which image is running\n'
else
  printf 'Rollout did not complete; inspect Pod status/events to identify the cause\n'
fi
```

**手順 4.2: エラーを確認してロールバックする**
```bash
workload_kubectl get pods -l app=nginx-deploy
workload_kubectl describe deployment nginx-deploy
workload_kubectl get events --sort-by=.metadata.creationTimestamp
workload_kubectl rollout undo deployment/nginx-deploy \
  --to-revision="${WORKLOADS_LAB_GOOD_REVISION:?Complete Step 3.1 first}"
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

### 確認
```bash
IMAGE=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
printf 'Current image: %s\n' "$IMAGE"
[ "$IMAGE" = "nginx:1.30.6-alpine" ]
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

---

## クリーンアップ
```bash
# Delete the isolated lab namespace only if its recorded identity still matches.
if [[ -n ${WORKLOADS_LAB_NAMESPACE:-} && -n ${WORKLOADS_LAB_UID:-} ]]; then
  current_uid=$(kubectl --context "${WORKLOADS_LAB_CONTEXT:?}" get namespace "$WORKLOADS_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [ "$current_uid" = "$WORKLOADS_LAB_UID" ]; then
    kubectl --context "$WORKLOADS_LAB_CONTEXT" delete namespace "$WORKLOADS_LAB_NAMESPACE" --timeout=120s
  else
    printf 'Namespace missing or identity changed; automatic deletion skipped\n'
  fi
fi
if [[ -n ${WORKLOADS_LAB_DIR:-} ]]; then
  rm -f -- "$WORKLOADS_LAB_DIR/nginx-pod.yaml" "$WORKLOADS_LAB_DIR/nginx-deployment.yaml"
  rmdir -- "$WORKLOADS_LAB_DIR"
fi
unset -f workload_kubectl
```


## 参考資料と検証範囲

* [Deployment、ロールアウト、ロールバック](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
* [kubectl rollout undo](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_undo/)
* [Readiness probe と liveness probe](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

マニフェストとコマンドはローカルで確認しました。この監査では、クラスターへのデプロイ、イメージ取得、スケーリング、ロールバック、namespace の削除を実行していません。

## 次のステップ
- [Pod と Workload のクイズ](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [Service とネットワーキングのラボ](./03-services-networking-lab.md)
