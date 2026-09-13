# Storage Lab Guide

> **Difficulty**: Intermediate
> **Estimated Time**: 40 minutes
> **Last Updated**: September 11, 2026

## Learning Objectives
- Create PersistentVolume (PV) and PersistentVolumeClaim (PVC)
- Mount and use volumes in Pods
- Compare emptyDir and hostPath volume types

## Prerequisites
- [ ] kubectl, Kubernetes cluster
- [ ] Completed [Storage](../../core/04-storage.md) learning

Use an existing disposable **single-node kind/minikube** cluster with permission for namespaces, PVs and hostPath. Do not use this hostPath recipe as production storage or weaken a cluster-wide admission policy to allow it. The path belongs to the Kubernetes node (a node container/VM may differ from your client filesystem). The lab explicitly avoids a default StorageClass/dynamic provisioner and uses only nonsensitive test data.

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

## Exercise 1: emptyDir Volume

### Steps

**Step 1.1: Create a Pod using emptyDir**
The init container creates the file before the reader starts. The writer emits five sample lines and stays alive; this avoids a startup race where tail exits before the file exists. These are lab-generated lines, not recorded audit output.

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
    image: busybox:1.37.0
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
    image: busybox:1.37.0
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
    image: busybox:1.37.0
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

**Step 1.2: Verify data sharing between containers**
```bash
# Check reader container logs
storage_kubectl logs emptydir-demo -c reader --tail=5

# Check file in writer container
storage_kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>Need a hint?</summary>

- emptyDir belongs to the Pod lifetime and survives a container restart within that Pod; a replacement Pod gets a new volume.
- It shares data among containers in that Pod, but is not durable storage for node failure.
- Removing the Pod from the node ends that emptyDir lifetime.
</details>

### Verification
```bash
storage_kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## Exercise 2: PV/PVC Creation

### Steps

**Step 2.1: Create PersistentVolume**
Both resources explicitly use `storageClassName: ""`; the PVC names the intended PV and the PV reserves the namespace/claim. This prevents the lab PVC from silently using a default class and provisioning another disk. `DirectoryOrCreate` and node affinity make the node-local assumption explicit.

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

**Step 2.2: Create PersistentVolumeClaim**
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
Expect the claim to bind to the PV stored in `STORAGE_LAB_PV`. The request is500Mi and the matching PV advertises1Gi, but hostPath capacity is not a filesystem quota. ReadWriteOnce means single-node access semantics, not one-Pod exclusivity or an application lock.

**Step 2.3: Create a Pod using PVC**
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
    image: busybox:1.37.0
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

**Step 2.4: Test data persistence**
This only tests Pod recreation while the same PVC, PV and node directory remain. Retain is a reclamation policy, not a backup or a promise that data survives node/VM deletion, /tmp cleanup or disk failure. After claim deletion the retained PV normally becomes Released and is not automatically reusable by a new claim.

```bash
storage_kubectl exec pvc-demo -- sh -c 'printf "Persistent Data\n" > /data/index.txt'
storage_kubectl delete pod pvc-demo --wait=true --timeout=120s
storage_kubectl apply -f "${STORAGE_LAB_DIR:?}/pvc-pod.yaml"
storage_kubectl wait --for=condition=Ready pod/pvc-demo --timeout=120s
storage_kubectl exec pvc-demo -- cat /data/index.txt
```

<details>
<summary>Need a hint?</summary>

- PV is a cluster-level resource, PVC is a namespace-level resource
- `Bound` status means PVC is bound to a PV
- Retain leaves the backing storage for manual reclamation after claim deletion; it does not make hostPath durable.
</details>

### Verification
```bash
storage_kubectl exec pvc-demo -- cat /data/index.txt
# Output: Persistent Data (persists even after Pod recreation)
```

---

## Exercise 3: Volume Type Comparison

### Steps

**Step 3.1: Compare volume information**
```bash
storage_kubectl get pod emptydir-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
storage_kubectl get pod pvc-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
kubectl --context "${STORAGE_LAB_CONTEXT:?}" get pv "${STORAGE_LAB_PV:?}" \
  -o custom-columns='NAME:.metadata.name,CAPACITY:.spec.capacity.storage,ACCESS:.spec.accessModes[0],STATUS:.status.phase'
```

---

## Cleanup
API-object cleanup below does **not erase the retained node directory**. Remove only that recorded directory through your approved access to the disposable node, or retire the dedicated test node/cluster. Do not mistake the client’s /tmp for the node’s path or delete a broad host directory. No node data deletion was performed by the audit.

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


## References and validation scope

* [Persistent volumes, reservation and reclaim](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
* [emptyDir and hostPath](https://kubernetes.io/docs/concepts/storage/volumes/)
* [StorageClass defaulting](https://kubernetes.io/docs/concepts/storage/storage-classes/)

Validation covers local manifests and commands only. No PV, PVC, node directory, Pod or cloud disk was created, mounted, deleted or measured during this audit.

## Next Steps
- [Storage Quiz](../../quizzes/core/04-storage-quiz.md)
- [ConfigMap and Secret Lab](./05-configuration-secrets-lab.md)
