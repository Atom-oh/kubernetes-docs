# スケジューラーのスコアリング戦略ラボ: `LeastAllocated` と `MostAllocated`

> **難易度**: 中級
> **想定時間**: 30分
> **最終更新日**: 2026年9月17日

## 学習目標
- このラボ専用の使い捨て複数ノード `kind` クラスターを起動する
- `nodeName` を指定した Pod を使って、ノード間で不均一な初期 CPU 使用率を作る
- その初期状態に対して、デフォルトスケジューラーの `LeastAllocated` による配置動作を観察する
- `NodeResourcesFit` の `MostAllocated` スコアリング戦略を設定した2つ目のスケジューラーをデプロイし、配置判断を比較する
- `MostAllocated` によるビンパッキングが、Karpenter／Cluster Autoscaler と並行して動くバッチワークロードに適している理由を説明する

## 前提条件
- [ ] `kubectl`、`docker`（または kind がサポートする別のコンテナランタイム）
- [ ] `kind` v0.20 以降（このラボで未インストールならローカルにインストールする）
- [ ] [スケジューリング、プリエンプション、退避](../../core/08-scheduling-preemption-eviction.md)を完了していること。特に[NodeResourcesFit のスコアリング戦略](../../core/08-scheduling-preemption-eviction.md#noderesourcesfit-scoring-strategy-leastallocated-vs-mostallocated)のセクション

このラボでは専用の使い捨て複数ノード `kind` クラスターを作成します。既存クラスターは再利用しません。この実験には、CPU 割り当てを個別に観測できるワーカーノードが少なくとも3台必要です。ラボの最後にすべて削除します。同じシェルでコマンドを順番に実行し、手順が失敗した場合は停止してください。

```bash
SCHED_LAB_DIR=$(mktemp -d /tmp/k8s-docs-sched.XXXXXX)
: "${SCHED_LAB_DIR:?mktemp failed}"
cd "$SCHED_LAB_DIR"

if ! command -v kind >/dev/null 2>&1; then
  KIND_ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
  curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v0.33.0/kind-linux-${KIND_ARCH}"
  chmod +x ./kind
  SCHED_LAB_KIND=./kind
else
  SCHED_LAB_KIND=kind
fi
"$SCHED_LAB_KIND" version
```

---

## ラボ1: テスト用クラスターと不均一な初期状態を作る

### 手順

**手順1.1: ワーカーノード3台の kind クラスターを作成する**
```bash
cat > "$SCHED_LAB_DIR/kind-config.yaml" << 'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: scheduler-strategy-lab
nodes:
- role: control-plane
- role: worker
- role: worker
- role: worker
EOF

export KUBECONFIG="$SCHED_LAB_DIR/kubeconfig"
"$SCHED_LAB_KIND" create cluster --config "$SCHED_LAB_DIR/kind-config.yaml"
kubectl wait --for=condition=Ready nodes --all --timeout=120s
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"  cpu="}{.status.allocatable.cpu}{"\n"}{end}'
```
4台すべてのノードで、割り当て可能な CPU は同じ値になります。kind ノードはホストを共有するコンテナであるため、割り当て可能な値は実際のノードごとのハードウェア分割ではなく、ホストを反映します。各ノードで `cpu=16` のような値が表示されることがありますが、正確な値はマシンによって異なります。

**手順1.2: ワーカーノード名を記録する**
```bash
mapfile -t SCHED_LAB_WORKERS < <(kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | grep -v control-plane)
printf 'Workers: %s\n' "${SCHED_LAB_WORKERS[*]}"
kubectl create namespace sched-lab
```

**手順1.3: Pod を固定して CPU 使用率に差を作る**

`spec.nodeName` を使うとスケジューラーを完全に迂回できます。これを使って、3台のワーカーの初期使用率を変えます。1台目は75%、2台目は約37%、3台目は0%にします。

```bash
{
  for i in $(seq 1 12); do
cat << EOF
apiVersion: v1
kind: Pod
metadata:
  name: filler-busy-${i}
  namespace: sched-lab
  labels: { role: filler }
spec:
  nodeName: ${SCHED_LAB_WORKERS[0]}
  containers:
  - name: filler
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
---
EOF
  done
  for i in $(seq 1 6); do
cat << EOF
apiVersion: v1
kind: Pod
metadata:
  name: filler-medium-${i}
  namespace: sched-lab
  labels: { role: filler }
spec:
  nodeName: ${SCHED_LAB_WORKERS[1]}
  containers:
  - name: filler
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
---
EOF
  done
} > "$SCHED_LAB_DIR/filler-pods.yaml"

kubectl apply -f "$SCHED_LAB_DIR/filler-pods.yaml"
kubectl -n sched-lab wait --for=condition=Ready pod -l role=filler --timeout=120s
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### 期待される結果
おおよそ次の値が表示されます。
- `${SCHED_LAB_WORKERS[0]}`（**A** と呼ぶ）: リクエスト済み12000m、約75%
- `${SCHED_LAB_WORKERS[1]}`（**B** と呼ぶ）: リクエスト済み6000m、約37%
- `${SCHED_LAB_WORKERS[2]}`（**C** と呼ぶ）: リクエスト済み約0m、0%

正確な割合は kind が認識するホストの CPU 数によって異なります。重要なのは、使用率が A > B > C の順になることです。

---

## ラボ2: デフォルトスケジューラー（`LeastAllocated`）を観察する

### 手順

**手順2.1: デフォルトスケジューラーで新しい Pod を6つスケジュールする**
```bash
for i in $(seq 1 6); do
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: batch-default-${i}
  namespace: sched-lab
  labels: { role: batch-default }
spec:
  containers:
  - name: batch
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
EOF
done
kubectl -n sched-lab wait --for=condition=Ready pod -l role=batch-default --timeout=60s
```

**手順2.2: 配置先を記録する**
```bash
kubectl -n sched-lab get pods -l role=batch-default -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### 期待される結果
6つすべての Pod が、最も空いているノード **C** に配置され、使用率はおよそ B と同じになります。これが `LeastAllocated` の動作です。デフォルトスケジューラーは、新しい Pod ごとに空きキャパシティが最も多いノードを選ぶため、一部のノードに負荷を集中させず、ノード間の使用率を均等に近づけます。この手順を終えると、3台のワーカーノードすべてに負荷がかかり、スケールダウンの候補となる空きノードはなくなります。

---

## ラボ3: `MostAllocated` を使う2つ目のスケジューラーをデプロイして比較する

### 手順

**手順3.1: リセットする（初期状態のフィラーは残し、ラボ2でスケジュールした Pod を削除する）**
```bash
kubectl -n sched-lab delete pod -l role=batch-default --wait=true
```

**手順3.2: `MostAllocated` を設定した2つ目の kube-scheduler をデプロイする**
```bash
cat > "$SCHED_LAB_DIR/most-allocated-scheduler.yaml" << 'EOF'
apiVersion: v1
kind: ServiceAccount
metadata:
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: most-allocated-scheduler-as-kube-scheduler
roleRef: { apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: system:kube-scheduler }
subjects:
- kind: ServiceAccount
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: most-allocated-scheduler-as-volume-scheduler
roleRef: { apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: system:volume-scheduler }
subjects:
- kind: ServiceAccount
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: most-allocated-scheduler-config
  namespace: kube-system
data:
  config.yaml: |
    apiVersion: kubescheduler.config.k8s.io/v1
    kind: KubeSchedulerConfiguration
    leaderElection:
      leaderElect: false
    profiles:
    - schedulerName: most-allocated-scheduler
      pluginConfig:
      - name: NodeResourcesFit
        args:
          scoringStrategy:
            type: MostAllocated
            resources:
            - { name: cpu, weight: 1 }
            - { name: memory, weight: 1 }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: most-allocated-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector: { matchLabels: { app: most-allocated-scheduler } }
  template:
    metadata: { labels: { app: most-allocated-scheduler } }
    spec:
      serviceAccountName: most-allocated-scheduler
      containers:
      - name: kube-scheduler
        image: registry.k8s.io/kube-scheduler:v1.37.0
        command: ["kube-scheduler", "--config=/etc/kubernetes/scheduler-config/config.yaml", "-v=2"]
        volumeMounts:
        - { name: config, mountPath: /etc/kubernetes/scheduler-config }
      volumes:
      - name: config
        configMap: { name: most-allocated-scheduler-config }
EOF

kubectl apply -f "$SCHED_LAB_DIR/most-allocated-scheduler.yaml"
kubectl -n kube-system rollout status deployment/most-allocated-scheduler --timeout=120s
```
`image: registry.k8s.io/kube-scheduler:v1.37.0` は、クラスターで実際に使っているマイナーバージョンに合わせてください。`kubectl version` で確認します。API サーバーのバージョンから1つを超えるマイナーバージョン差があるスケジューラーバイナリは、起動を拒否したり、予測できない動作をしたりする場合があります。

**手順3.3: 今度は `schedulerName` を指定して、同じ6つの Pod をスケジュールする**
```bash
for i in $(seq 1 6); do
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: batch-mostalloc-${i}
  namespace: sched-lab
  labels: { role: batch-mostalloc }
spec:
  schedulerName: most-allocated-scheduler
  containers:
  - name: batch
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
EOF
done
kubectl -n sched-lab wait --for=condition=Ready pod -l role=batch-mostalloc --timeout=60s
```

**手順3.4: 配置先を記録して比較する**
```bash
kubectl -n sched-lab get pods -l role=batch-mostalloc -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### 期待される結果と参照結果

この手順を、このラボの作成時に一度実行しました。3台のワーカーノードがある kind クラスターで、各ノードの割り当て可能な CPU は16、`kubectl version` の報告は `v1.37.0` でした。

| スケジューラー／戦略 | 新しい6つの Pod の配置先 | 最終 CPU 使用率（A／B／C） |
|---|---|---|
| デフォルト（`LeastAllocated`） | 6つすべてノード C | 75% / 37% / 37%（3台すべてに負荷あり） |
| `MostAllocated` | ノード A に3つ、ノード B に3つ | 93% / 56% / 0%（ノード C は完全にアイドル状態） |

絶対的な使用率はホストの CPU 数によって異なりますが、**傾向**は再現されるはずです。`LeastAllocated` は空いているノードを隣接ノードと同程度になるまで使う一方、`MostAllocated` はすでに負荷が高いノードにさらに Pod を集め、空いているノードをそのまま残します。Cluster Autoscaler や Karpenter の統合処理で終了されるのは、まさにそのアイドルノードです。そのため、オートスケーラーと並行して動くバッチ／短時間のジョブには `MostAllocated` がより適しています。一方、各ノードに余裕を持たせたい長時間稼働のレイテンシ重視サービスには、`LeastAllocated` が引き続き安全なデフォルトです。

---

## クリーンアップ
```bash
unset KUBECONFIG
"$SCHED_LAB_KIND" delete cluster --name scheduler-strategy-lab --kubeconfig "$SCHED_LAB_DIR/kubeconfig"
rm -rf -- "$SCHED_LAB_DIR"
unset SCHED_LAB_DIR SCHED_LAB_KIND SCHED_LAB_WORKERS
```

## 参考資料と検証範囲

- [スケジューラー設定: Kubernetes ドキュメント](https://kubernetes.io/docs/reference/scheduling/config/)
- [NodeResourcesFit のスコアリング戦略](https://kubernetes.io/docs/reference/config-api/kube-scheduler-config.v1/)
- [複数スケジューラーの設定](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/)

このラボは、分離された使い捨ての `kind` クラスターで、クラスター作成、フィラーポッド、両方のスケジューラーでの実行、クリーンアップまで一通り実行しました。共有クラスターやクラウドリソースには触れていません。上の参照結果表には仮説ではなく、その実行で実際に観測した出力を記録しています。

## 次のステップ
- [スケジューリング、プリエンプション、退避のクイズ](../../quizzes/core/08-scheduling-preemption-eviction-quiz.md)
- [カスタムスケジューラーの構築](../../scheduling/01-custom-scheduler-part1.md)
