# Guía del laboratorio de almacenamiento

> **Dificultad**: Intermedia
> **Tiempo estimado**: 40 minutos
> **Última actualización**: 11 de septiembre de 2026

## Objetivos de aprendizaje
- Crear PersistentVolumes (PV) y PersistentVolumeClaims (PVC)
- Montar y usar volúmenes en Pods
- Comparar los tipos de volumen `emptyDir` y `hostPath`

## Requisitos previos
- [ ] kubectl y un clúster de Kubernetes
- [ ] Haber completado el módulo de [Almacenamiento](../../core/04-storage.md)

Usa un clúster desechable existente de kind/minikube de **un solo nodo**, con permisos para crear espacios de nombres y PV, y usar hostPath. No uses esta receta de hostPath como almacenamiento de producción ni debilites una política de admisión de todo el clúster para permitirlo. La ruta pertenece al nodo de Kubernetes (el contenedor o la VM del nodo puede ser distinto del sistema de archivos del cliente). El laboratorio evita expresamente una StorageClass predeterminada y el aprovisionador dinámico, y solo utiliza datos de prueba no sensibles.

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

## Ejercicio 1: Volumen emptyDir

### Pasos

**Paso 1.1: Crear un Pod con emptyDir**
El contenedor de inicialización crea el archivo antes de que se inicie el lector. El escritor emite cinco líneas de ejemplo y sigue en ejecución; así se evita una condición de carrera al inicio en la que tail salga antes de que exista el archivo. Son líneas generadas por el laboratorio, no resultados de auditoría registrados.

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

**Paso 1.2: Verificar el uso compartido de datos entre contenedores**
```bash
# Check reader container logs
storage_kubectl logs emptydir-demo -c reader --tail=5

# Check file in writer container
storage_kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>¿Necesitas una pista?</summary>

- `emptyDir` dura mientras exista el Pod y sobrevive al reinicio de un contenedor dentro de ese Pod; un Pod de reemplazo obtiene un volumen nuevo.
- Permite compartir datos entre los contenedores del Pod, pero no es almacenamiento duradero frente a una falla del nodo.
- Al retirar el Pod del nodo termina la vida útil de ese `emptyDir`.
</details>

### Verificación
```bash
storage_kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## Ejercicio 2: Crear un PV y un PVC

### Pasos

**Paso 2.1: Crear un PersistentVolume**
Ambos recursos especifican `storageClassName: ""`; el PVC nombra el PV previsto y el PV reserva el espacio de nombres y el nombre del PVC previstos. Así se evita que el PVC del laboratorio use silenciosamente una clase predeterminada y aprovisione otro disco. `DirectoryOrCreate` y la afinidad de nodo hacen explícito que el almacenamiento pertenece a un nodo.

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

**Paso 2.2: Crear un PersistentVolumeClaim**
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
El PVC debe vincularse al PV indicado por `STORAGE_LAB_PV`. La solicitud de almacenamiento es de 500Mi y el PV correspondiente anuncia 1Gi, pero la capacidad de hostPath no es una cuota del sistema de archivos. ReadWriteOnce define semántica de acceso desde un solo nodo; no implica exclusividad para un Pod ni un bloqueo de aplicación.

**Paso 2.3: Crear un Pod con el PVC**
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

**Paso 2.4: Probar la persistencia de los datos**
Esto solo prueba la recreación de un Pod mientras se conservan el mismo PVC, el mismo PV y el mismo directorio del nodo. Retain es una política de retención del almacenamiento subyacente, no una copia de seguridad ni una garantía de que los datos sobrevivan a la eliminación del nodo o la VM, a la limpieza de /tmp o a una falla del disco. Tras eliminar el PVC, el PV retenido normalmente pasa a Released y no se puede reutilizar automáticamente con un PVC nuevo.

```bash
storage_kubectl exec pvc-demo -- sh -c 'printf "Persistent Data\n" > /data/index.txt'
storage_kubectl delete pod pvc-demo --wait=true --timeout=120s
storage_kubectl apply -f "${STORAGE_LAB_DIR:?}/pvc-pod.yaml"
storage_kubectl wait --for=condition=Ready pod/pvc-demo --timeout=120s
storage_kubectl exec pvc-demo -- cat /data/index.txt
```

<details>
<summary>¿Necesitas una pista?</summary>

- PV es un recurso del ámbito del clúster; PVC, del ámbito de un espacio de nombres.
- El estado `Bound` indica que el PVC está vinculado a un PV.
- Retain deja el almacenamiento subyacente para recuperarlo manualmente tras eliminar el PVC; no hace que hostPath sea duradero.
</details>

### Verificación
```bash
storage_kubectl exec pvc-demo -- cat /data/index.txt
# Output: Persistent Data (persists even after Pod recreation)
```

---

## Ejercicio 3: Comparar tipos de volumen

### Pasos

**Paso 3.1: Comparar la información de los volúmenes**
```bash
storage_kubectl get pod emptydir-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
storage_kubectl get pod pvc-demo -o jsonpath='{.spec.volumes[*]}{"\n"}'
kubectl --context "${STORAGE_LAB_CONTEXT:?}" get pv "${STORAGE_LAB_PV:?}" \
  -o custom-columns='NAME:.metadata.name,CAPACITY:.spec.capacity.storage,ACCESS:.spec.accessModes[0],STATUS:.status.phase'
```

---

## Limpieza
La limpieza de los objetos de la API que sigue **no borra el directorio retenido en el nodo**. Elimina únicamente ese directorio registrado mediante el acceso aprobado al nodo desechable o retira el nodo o clúster de prueba dedicado. No confundas el /tmp del cliente con la ruta del nodo ni elimines directorios amplios del host. Esta auditoría no borró datos del nodo.

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


## Referencias y alcance de la validación

* [Volúmenes persistentes, reserva y recuperación](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
* [`emptyDir` y hostPath](https://kubernetes.io/docs/concepts/storage/volumes/)
* [Valores predeterminados de StorageClass](https://kubernetes.io/docs/concepts/storage/storage-classes/)

La validación solo abarca manifiestos y comandos locales. Durante esta auditoría no se creó, montó, eliminó ni midió ningún PV, PVC, directorio del nodo, Pod o disco en la nube.

## Próximos pasos
- [Cuestionario de almacenamiento](../../quizzes/core/04-storage-quiz.md)
- [Laboratorio de ConfigMap y Secret](./05-configuration-secrets-lab.md)
