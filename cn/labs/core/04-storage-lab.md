# 存储实验指南

> **难度**：中级
> **预计时间**：40 分钟
> **最后更新**：2026 年 9 月 11 日

## 学习目标
- 创建 PersistentVolume (PV) 和 PersistentVolumeClaim (PVC)
- 在 Pod 中挂载和使用卷
- 比较 emptyDir 和 hostPath 卷类型

## 先决条件
- [ ] kubectl、Kubernetes 集群
- [ ] 已完成[存储](../../core/04-storage.md)学习

使用现有的、可随时销毁的**单节点 kind/minikube**集群，并确保拥有操作命名空间、PV 和 hostPath 的权限。请勿将此 hostPath 配置用于生产存储，也不要放宽集群级准入策略来允许使用它。该路径属于 Kubernetes 节点（节点容器/VM 中的路径可能与客户端文件系统不同）。本实验明确避开默认 StorageClass/动态置备程序，并且只使用非敏感测试数据。

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

## 练习 1：emptyDir 卷

### 步骤

**步骤 1.1：创建使用 emptyDir 的 Pod**
init 容器会在 reader 启动前创建文件。writer 写入五行示例内容并保持运行；这样可以避免文件尚不存在时 tail 提前退出造成的启动竞争。这些行由实验生成，并非记录的审计输出。

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

**步骤 1.2：验证容器之间的数据共享**
```bash
# Check reader container logs
storage_kubectl logs emptydir-demo -c reader --tail=5

# Check file in writer container
storage_kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>需要提示吗？</summary>

- emptyDir 的生命周期与 Pod 关联，并且在该 Pod 内的容器重启后仍会保留；替代 Pod 会获得一个新卷。
- 它会在该 Pod 中的容器之间共享数据，但不是能应对节点故障的持久存储。
- 从节点移除 Pod 后，emptyDir 的生命周期也随之结束。
</details>

### 验证
```bash
storage_kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## 练习 2：创建 PV/PVC

### 步骤

**步骤 2.1：创建 PersistentVolume**
这两个资源都显式使用 `storageClassName: ""`；PVC 指定目标 PV，PV 则预留给该命名空间/声明。这样可以避免实验 PVC 悄悄使用默认 StorageClass 并置备另一块磁盘。`DirectoryOrCreate` 和节点亲和性明确体现了此处使用节点本地存储的假设。

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

**步骤 2.2：创建 PersistentVolumeClaim**
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
预期该声明会绑定到 `STORAGE_LAB_PV` 中记录的 PV。请求容量为 500Mi，匹配的 PV 声明容量为 1Gi，但 hostPath 容量并不是文件系统配额。ReadWriteOnce 表示单节点访问语义，并不意味着只能由一个 Pod 使用，也不等同于应用锁。

**步骤 2.3：创建使用 PVC 的 Pod**
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

**步骤 2.4：测试数据持久性**
此操作仅测试在同一个 PVC、PV 和节点目录保持不变时重新创建 Pod 的情况。Retain 是回收策略，并非备份，也不保证数据在节点/VM 删除、清理 /tmp 或磁盘故障后仍然存在。删除声明后，保留的 PV 通常会变为 Released，并且不会自动供新的声明使用。

```bash
storage_kubectl exec pvc-demo -- sh -c 'printf "Persistent Data\n" > /data/index.txt'
storage_kubectl delete pod pvc-demo --wait=true --timeout=120s
storage_kubectl apply -f "${STORAGE_LAB_DIR:?}/pvc-pod.yaml"
storage_kubectl wait --for=condition=Ready pod/pvc-demo --timeout=120s
storage_kubectl exec pvc-demo -- cat /data/index.txt
```

<details>
<summary>需要提示吗？</summary>

- PV 是集群级资源，PVC 是命名空间级资源
- `Bound` 状态表示 PVC 已绑定到 PV
- Retain 会在删除声明后保留底层存储，以便手动回收；它不会让 hostPath 变得持久可靠。
</details>

### 验证
```bash
storage_kubectl exec pvc-demo -- cat /data/index.txt
# Output: Persistent Data (persists even after Pod recreation)
```

---

## 练习 3：卷类型比较

### 步骤

**步骤 3.1：比较卷信息**
```bash
storage_kubectl get pod emptydir-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
storage_kubectl get pod pvc-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
kubectl --context "${STORAGE_LAB_CONTEXT:?}" get pv "${STORAGE_LAB_PV:?}" \
  -o custom-columns='NAME:.metadata.name,CAPACITY:.spec.capacity.storage,ACCESS:.spec.accessModes[0],STATUS:.status.phase'
```

---

## 清理
下面的 API 对象清理**不会擦除保留在节点上的目录**。请通过获准的方式访问可随时销毁的节点，仅移除该记录的目录；或者销毁专用测试节点/集群。不要把客户端的 /tmp 误认为节点上的路径，也不要删除范围较大的主机目录。本次审计没有删除任何节点数据。

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


## 参考资料与验证范围

* [Persistent volumes, reservation and reclaim](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
* [emptyDir and hostPath](https://kubernetes.io/docs/concepts/storage/volumes/)
* [StorageClass defaulting](https://kubernetes.io/docs/concepts/storage/storage-classes/)

验证仅涵盖本地清单和命令。本次审计期间未创建、挂载、删除或测量任何 PV、PVC、节点目录、Pod 或云磁盘。

## 后续步骤
- [存储测验](../../quizzes/core/04-storage-quiz.md)
- [ConfigMap 和 Secret 实验](./05-configuration-secrets-lab.md)
