# ストレージラボガイド

> **難易度**: 中級
> **所要時間**: 40 分
> **最終更新日**: 2026年9月11日

## 学習目標
- PersistentVolume (PV) と PersistentVolumeClaim (PVC) を作成する
- Pod で volume を mount して使用する
- emptyDir と hostPath の volume タイプを比較する

## 前提条件
- [ ] kubectl、Kubernetes クラスター
- [ ] [Storage](../../core/04-storage.md) の学習を完了していること

namespace、PV、hostPath を扱う権限のある、既存の**単一ノードの使い捨て kind/minikube**クラスターを使用してください。この hostPath の手順を本番ストレージとして使ったり、hostPath を許可するためにクラスター全体の admission policy を弱めたりしないでください。パスが属するのは Kubernetes ノードです（ノードがコンテナ／VM の場合、クライアント側のファイルシステムとは異なることがあります）。このラボでは default StorageClass／動的 provisioner を明示的に避け、機密性のないテストデータだけを使います。

```bash
STORAGE_LAB_DIR=$(mktemp -d /tmp/k8s-docs-storage.XXXXXX)
: "${STORAGE_LAB_DIR:?mktemp failed}"
STORAGE_LAB_CONTEXT=$(kubectl config current-context)
: "${STORAGE_LAB_CONTEXT:?No context selected}"
printf 'Selected context: %s\n' "$STORAGE_LAB_CONTEXT"
unset STORAGE_LAB_NAMESPACE STORAGE_LAB_NODE STORAGE_LAB_PV_UID
read -r -a STORAGE_LAB_NODES <<< "$(kubectl --context "$STORAGE_LAB_CONTEXT" get nodes -o jsonpath='{.items[*].metadata.name}')"
if [ "${#STORAGE_LAB_NODES[@]}" -eq 1 ]; then
  STORAGE_LAB_NODE=${STORAGE_LAB_NODES[0]}
fi
: "${STORAGE_LAB_NODE:?This hostPath lab requires one disposable node}"
STORAGE_LAB_CANDIDATE=$(basename "$STORAGE_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
if STORAGE_LAB_UID=$(kubectl --context "$STORAGE_LAB_CONTEXT" create namespace "$STORAGE_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  STORAGE_LAB_NAMESPACE=$STORAGE_LAB_CANDIDATE
fi
: "${STORAGE_LAB_NAMESPACE:?Namespace creation failed}"
STORAGE_LAB_PV="${STORAGE_LAB_NAMESPACE}-pv"
STORAGE_LAB_NODE_PATH="/tmp/${STORAGE_LAB_NAMESPACE}-data"
storage_kubectl() {
  kubectl --context "${STORAGE_LAB_CONTEXT:?}" --namespace "${STORAGE_LAB_NAMESPACE:?}" "$@"
}
```

---

## 演習 1: emptyDir volume

### 手順

**ステップ 1.1: emptyDir を使用する Pod を作成する**
init container は reader の開始前にファイルを作成します。writer はサンプルの5行を出力して稼働し続けます。これにより、ファイルが存在する前に `tail` が終了する起動時の競合を避けます。これらはラボで生成する行であり、記録された監査ログではありません。

```bash
cat > "${STORAGE_LAB_DIR:?}/emptydir-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: emptydir-demo
spec:
  automountServiceAccountToken: false
  initContainers:
  - name: initialize-file
    image: busybox:1.38.0
    command:
    - sh
    - -c
    - touch /data/log.txt
    volumeMounts: &id001
    - name: shared-data
      mountPath: /data
    resources: &id002
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        memory: 64Mi
  containers:
  - name: writer
    image: busybox:1.38.0
    command:
    - sh
    - -c
    - for i in 1 2 3 4 5; do date >> /data/log.txt; done; exec sleep 3600
    volumeMounts: *id001
    resources: *id002
    readinessProbe:
      exec:
        command:
        - sh
        - -c
        - test -s /data/log.txt
  - name: reader
    image: busybox:1.38.0
    command:
    - tail
    - -f
    - /data/log.txt
    volumeMounts: *id001
    resources: *id002
  volumes:
  - name: shared-data
    emptyDir: {}
EOF
storage_kubectl apply -f "$STORAGE_LAB_DIR/emptydir-pod.yaml"
storage_kubectl wait --for=condition=Ready pod/emptydir-demo --timeout=120s
```

**ステップ 1.2: コンテナ間でデータを共有できることを確認する**
```bash
# Check reader container logs
storage_kubectl logs emptydir-demo -c reader --tail=5

# Check file in writer container
storage_kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>ヒントが必要ですか？</summary>

- `emptyDir` は Pod のライフサイクルに属し、同じ Pod 内のコンテナが再起動しても保持されます。置き換えた Pod には新しい volume が割り当てられます。
- 同じ Pod 内のコンテナ間でデータを共有できますが、ノード障害に耐える永続ストレージではありません。
- Pod がノードから削除されると、その `emptyDir` のライフサイクルは終了します。
</details>

### 検証
```bash
storage_kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## 演習 2: PV/PVC の作成

### 手順

**ステップ 2.1: PersistentVolume を作成する**
どちらのリソースも `storageClassName: ""` を明示します。PVC は対象の PV を指定し、PV は namespace／claim を予約します。これにより、ラボの PVC が default class を暗黙に使って別のディスクをプロビジョニングするのを防ぎます。`DirectoryOrCreate` と node affinity によって、ノードローカルという前提を明示します。

```bash
cat > "${STORAGE_LAB_DIR:?}/pv.yaml" << EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: ${STORAGE_LAB_PV:?}
spec:
  capacity:
    storage: 1Gi
  volumeMode: Filesystem
  storageClassName: ""
  accessModes: [ReadWriteOnce]
  persistentVolumeReclaimPolicy: Retain
  claimRef:
    namespace: ${STORAGE_LAB_NAMESPACE:?}
    name: lab-pvc
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchFields:
        - key: metadata.name
          operator: In
          values: ["${STORAGE_LAB_NODE:?}"]
  hostPath:
    path: ${STORAGE_LAB_NODE_PATH:?}
    type: DirectoryOrCreate
EOF
if STORAGE_LAB_PV_UID=$(kubectl --context "${STORAGE_LAB_CONTEXT:?}" create -f "$STORAGE_LAB_DIR/pv.yaml" -o jsonpath='{.metadata.uid}'); then
  kubectl --context "$STORAGE_LAB_CONTEXT" get pv "$STORAGE_LAB_PV"
else
  unset STORAGE_LAB_PV_UID
  printf 'PV creation failed; do not bind to an unverified existing PV\n' >&2
fi
```

**ステップ 2.2: PersistentVolumeClaim を作成する**
```bash
# Empty storageClassName prevents default/dynamic provisioning.
: "${STORAGE_LAB_PV_UID:?Create the owned PV first}"
cat > "${STORAGE_LAB_DIR:?}/pvc.yaml" << EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: lab-pvc
spec:
  storageClassName: ""
  volumeName: ${STORAGE_LAB_PV:?}
  volumeMode: Filesystem
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 500Mi
EOF
storage_kubectl apply -f "$STORAGE_LAB_DIR/pvc.yaml"
storage_kubectl wait --for=jsonpath='{.status.phase}'=Bound pvc/lab-pvc --timeout=120s
storage_kubectl get pvc lab-pvc
kubectl --context "${STORAGE_LAB_CONTEXT:?}" get pv "$STORAGE_LAB_PV"
```

claim は `STORAGE_LAB_PV` に保存した PV に bind されることを確認します。要求量は 500Mi、対応する PV の申告容量は 1Gi ですが、hostPath の容量はファイルシステムの quota ではありません。ReadWriteOnce は単一ノードでのアクセス意味論であり、Pod が1つに限定されることや、アプリケーションのロックを意味しません。

**ステップ 2.3: PVC を使用する Pod を作成する**
```bash
cat > "${STORAGE_LAB_DIR:?}/pvc-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: pvc-demo
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sleep
    - '3600'
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        memory: 64Mi
    volumeMounts:
    - name: persistent-storage
      mountPath: /data
  volumes:
  - name: persistent-storage
    persistentVolumeClaim:
      claimName: lab-pvc
EOF
storage_kubectl apply -f "$STORAGE_LAB_DIR/pvc-pod.yaml"
storage_kubectl wait --for=condition=Ready pod/pvc-demo --timeout=120s
```

**ステップ 2.4: データが保持されることをテストする**
これは、同じ PVC、PV、ノード上のディレクトリを残したまま Pod を再作成するテストに限られます。`Retain` は回収ポリシーであり、バックアップでも、ノード／VM の削除、`/tmp` のクリーンアップ、ディスク障害後にデータが残るという保証でもありません。claim を削除すると、保持された PV は通常 `Released` になり、新しい claim で自動的に再利用されることはありません。

```bash
storage_kubectl exec pvc-demo -- sh -c 'printf "Persistent Data\n" > /data/index.txt'
storage_kubectl delete pod pvc-demo --wait=true --timeout=120s
storage_kubectl apply -f "${STORAGE_LAB_DIR:?}/pvc-pod.yaml"
storage_kubectl wait --for=condition=Ready pod/pvc-demo --timeout=120s
storage_kubectl exec pvc-demo -- cat /data/index.txt
```

<details>
<summary>ヒントが必要ですか？</summary>

- PV はクラスター単位のリソース、PVC は namespace 単位のリソースです。
- `Bound` は PVC が PV に bind された状態を表します。
- `Retain` は claim 削除後も裏側のストレージを手動回収まで残しますが、hostPath を耐久性のあるストレージにするものではありません。
</details>

### 検証
```bash
storage_kubectl exec pvc-demo -- cat /data/index.txt
# Output: Persistent Data (persists even after Pod recreation)
```

---

## 演習 3: volume タイプの比較

### 手順

**ステップ 3.1: volume の情報を比較する**
```bash
storage_kubectl get pod emptydir-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
storage_kubectl get pod pvc-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
kubectl --context "${STORAGE_LAB_CONTEXT:?}" get pv "${STORAGE_LAB_PV:?}" \
  -o custom-columns='NAME:.metadata.name,CAPACITY:.spec.capacity.storage,ACCESS:.spec.accessModes[0],STATUS:.status.phase'
```

---

## クリーンアップ

以下の API オブジェクトを削除しても、保持されたノード上のディレクトリは**消去されません**。記録したそのディレクトリだけを、使い捨てノードへの承認済みアクセス経由で削除するか、専用テストノード／クラスターを廃棄してください。クライアント側の `/tmp` をノード上のパスと取り違えたり、広範囲の host ディレクトリを削除したりしないでください。この監査ではノードデータを削除していません。

```bash
# Keep protection finalizers; inspect a timeout instead of forcing removal.
if [[ -n ${STORAGE_LAB_NAMESPACE:-} && -n ${STORAGE_LAB_UID:-} ]]; then
  current_uid=$(kubectl --context "${STORAGE_LAB_CONTEXT:?}" get namespace "$STORAGE_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [ "$current_uid" = "$STORAGE_LAB_UID" ]; then
    if storage_kubectl delete pod emptydir-demo pvc-demo --ignore-not-found --wait=true --timeout=120s &&
       storage_kubectl delete pvc lab-pvc --ignore-not-found --wait=true --timeout=120s; then
      if [[ -n ${STORAGE_LAB_PV_UID:-} ]]; then
        current_pv_uid=$(kubectl --context "$STORAGE_LAB_CONTEXT" get pv "$STORAGE_LAB_PV" -o jsonpath='{.metadata.uid}') || current_pv_uid=""
        if [ "$current_pv_uid" = "$STORAGE_LAB_PV_UID" ]; then
          kubectl --context "$STORAGE_LAB_CONTEXT" delete pv "$STORAGE_LAB_PV" --timeout=120s
        fi
      fi
      kubectl --context "$STORAGE_LAB_CONTEXT" delete namespace "$STORAGE_LAB_NAMESPACE" --timeout=120s
    else
      printf 'Pod/PVC cleanup incomplete; inspect protection and mount state\n' >&2
    fi
  fi
fi
printf 'Node-local data path retained: %s\n' "${STORAGE_LAB_NODE_PATH:-not-created}"
if [[ -n ${STORAGE_LAB_DIR:-} ]]; then
  rm -f -- "$STORAGE_LAB_DIR/emptydir-pod.yaml" "$STORAGE_LAB_DIR/pv.yaml" "$STORAGE_LAB_DIR/pvc.yaml" "$STORAGE_LAB_DIR/pvc-pod.yaml"
  rmdir -- "$STORAGE_LAB_DIR"
fi
unset -f storage_kubectl
```

## 参考資料と検証範囲

- [PersistentVolume、予約、回収](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [emptyDir と hostPath](https://kubernetes.io/docs/concepts/storage/volumes/)
- [StorageClass のデフォルト指定](https://kubernetes.io/docs/concepts/storage/storage-classes/)

検証の対象はローカルのマニフェストとコマンドのみです。この監査では PV、PVC、ノード上のディレクトリ、Pod、クラウドディスクの作成、mount、削除、測定は行っていません。

## 次のステップ
- [Storage クイズ](../../quizzes/core/04-storage-quiz.md)
- [ConfigMap と Secret のラボ](./05-configuration-secrets-lab.md)
