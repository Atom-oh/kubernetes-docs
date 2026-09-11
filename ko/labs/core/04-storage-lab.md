# 스토리지 실습 가이드

> **난이도**: 중급
> **예상 소요 시간**: 40분
> **마지막 업데이트**: 2026년 9월 11일

## 학습 목표
- PersistentVolume(PV)과 PersistentVolumeClaim(PVC)을 생성합니다
- Pod에서 볼륨을 마운트하여 사용합니다
- emptyDir과 hostPath 볼륨 타입을 비교합니다

## 사전 요구 사항
- [ ] kubectl, Kubernetes 클러스터
- [ ] [스토리지](../../core/04-storage.md) 학습 완료

namespace·PV·hostPath 권한이 있는 기존의 폐기 가능한 **단일 노드 kind/minikube** 클러스터를 사용합니다. hostPath 예제를 운영 스토리지로 사용하거나 허용하려고 클러스터 전체 어드미션 정책을 완화하지 마세요. 경로는 Kubernetes 노드의 것이며 노드 컨테이너·VM과 클라이언트 파일 시스템은 다를 수 있습니다. 기본 StorageClass·동적 provisioner를 사용하지 않고 민감하지 않은 테스트 데이터만 사용합니다.

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

## 실습 1: emptyDir 볼륨

### 단계

**Step 1.1: emptyDir을 사용하는 Pod 생성**
init container가 reader보다 먼저 파일을 만듭니다. writer는 샘플5줄을 쓴 뒤 유지되므로 파일이 생기기 전에 tail이 종료되는 시작 순서 경합을 피합니다. 실습에서 생성할 줄이며 감사의 실행 로그가 아닙니다.

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

**Step 1.2: 컨테이너 간 데이터 공유 확인**
```bash
# reader 컨테이너의 로그 확인
storage_kubectl logs emptydir-demo -c reader --tail=5

# writer 컨테이너에서 파일 확인
storage_kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>힌트가 필요하신가요?</summary>

- emptyDir은 Pod 수명에 속하며 같은 Pod 안의 컨테이너 재시작에는 남지만 교체 Pod에는 새 볼륨이 생깁니다.
- 같은 Pod의 컨테이너끼리 공유하며 노드 장애용 영속 스토리지는 아닙니다.
- 노드에서 Pod가 제거되면 해당 emptyDir 수명도 끝납니다.
</details>

### 검증
```bash
storage_kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## 실습 2: PV/PVC 생성

### 단계

**Step 2.1: PersistentVolume 생성**
두 리소스 모두 `storageClassName: ""`를 명시합니다. PVC는 PV를 지정하고 PV는 namespace·claim을 예약하므로 기본 클래스로 다른 디스크가 동적 생성되지 않게 합니다. `DirectoryOrCreate`와 node affinity로 노드 로컬 전제를 명시합니다.

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

**Step 2.2: PersistentVolumeClaim 생성**
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
`STORAGE_LAB_PV`의 PV에 바인딩되는지 확인합니다. 요청은500Mi이고 PV는1Gi로 선언되지만 hostPath 용량은 파일 시스템 quota가 아닙니다. ReadWriteOnce는 단일 노드 접근 의미이며 Pod 하나만의 독점이나 앱 잠금이 아닙니다.

**Step 2.3: PVC를 사용하는 Pod 생성**
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

**Step 2.4: 데이터 영속성 테스트**
같은 PVC·PV·노드 디렉터리를 유지한 채 Pod만 재생성하는 실습입니다. Retain은 reclaim 정책이며 백업이나 노드·VM 삭제, /tmp 정리, 디스크 장애에 대한 내구성 보장이 아닙니다. claim 삭제 후 보존된 PV는 보통 Released가 되며 새 claim이 자동 재사용하지 않습니다.

```bash
storage_kubectl exec pvc-demo -- sh -c 'printf "Persistent Data\n" > /data/index.txt'
storage_kubectl delete pod pvc-demo --wait=true --timeout=120s
storage_kubectl apply -f "${STORAGE_LAB_DIR:?}/pvc-pod.yaml"
storage_kubectl wait --for=condition=Ready pod/pvc-demo --timeout=120s
storage_kubectl exec pvc-demo -- cat /data/index.txt
```

<details>
<summary>힌트가 필요하신가요?</summary>

- PV는 클러스터 수준 리소스, PVC는 네임스페이스 수준 리소스입니다
- `Bound` 상태는 PVC가 PV에 바인딩되었음을 의미합니다
- Retain은 claim 삭제 후 backing storage를 수동 reclaim 대상으로 남기며 hostPath에 내구성을 부여하지 않습니다.
</details>

### 검증
```bash
storage_kubectl exec pvc-demo -- cat /data/index.txt
# 출력: Persistent Data (Pod 재생성 후에도 유지)
```

---

## 실습 3: 볼륨 타입 비교

### 단계

**Step 3.1: 볼륨 정보 비교**
```bash
storage_kubectl get pod emptydir-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
storage_kubectl get pod pvc-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
kubectl --context "${STORAGE_LAB_CONTEXT:?}" get pv "${STORAGE_LAB_PV:?}" \
  -o custom-columns='NAME:.metadata.name,CAPACITY:.spec.capacity.storage,ACCESS:.spec.accessModes[0],STATUS:.status.phase'
```

---

## 정리
아래 API 리소스 정리는 **보존된 노드 디렉터리를 지우지 않습니다**. 승인된 테스트 노드 접근 방식으로 기록된 해당 디렉터리만 정리하거나 전용 테스트 노드·클러스터를 종료하세요. 클라이언트 /tmp와 노드 경로를 혼동하거나 넓은 호스트 디렉터리를 삭제하지 마세요. 감사에서는 노드 데이터를 삭제하지 않았습니다.

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


## 참고 자료와 검증 범위

* [Persistent volumes, reservation and reclaim](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
* [emptyDir and hostPath](https://kubernetes.io/docs/concepts/storage/volumes/)
* [StorageClass defaulting](https://kubernetes.io/docs/concepts/storage/storage-classes/)

로컬 매니페스트·명령만 검증합니다. 감사에서 PV·PVC·노드 디렉터리·Pod·클라우드 디스크를 생성·마운트·삭제·측정하지 않았습니다.

## 다음 단계
- [스토리지 퀴즈](../../quizzes/core/04-storage-quiz.md)
- [ConfigMap과 Secret 실습](./05-configuration-secrets-lab.md)
