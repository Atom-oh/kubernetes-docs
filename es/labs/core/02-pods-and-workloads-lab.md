# Guía de laboratorio: Pods y cargas de trabajo

> **Dificultad**: Principiante
> **Tiempo estimado**: 50 minutos
> **Última actualización**: 11 de septiembre de 2026

## Objetivos de aprendizaje
- Crear y administrar Pods mediante YAML
- Desplegar y escalar Deployments
- Realizar actualizaciones progresivas y reversiones

## Requisitos previos
- [ ] kubectl instalado y acceso al clúster (minikube o kind)
- [ ] Haber completado el contenido de aprendizaje [Pods y cargas de trabajo](../../core/02-pods-and-workloads.md)

Usa un clúster kind/minikube existente y desechable, con permiso para crear un espacio de nombres para el laboratorio y descargar las imágenes de ejemplo. Confirma el contexto seleccionado antes de ejecutar la preparación. Mantén una sola sesión de Bash; el wrapper fija el contexto y el espacio de nombres. Estos pasos realizan cambios reales si los ejecutas; en esta auditoría no se realizaron operaciones en ningún clúster.

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

## Ejercicio 1: Creación y administración de Pods

### Pasos

**Paso 1.1: Escribir el YAML del Pod**
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

**Paso 1.2: Comprobar el estado del Pod**
Que la fase sea `Running` no significa que esté listo. Espera a que se cumpla la sonda HTTP de disponibilidad configurada antes de consultar los registros o ejecutar comandos dentro del Pod; inspecciona los fallos en lugar de tratar un timeout como un resultado satisfactorio.

```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
workload_kubectl describe pod nginx-lab
workload_kubectl logs nginx-lab
```

**Paso 1.3: Acceder al interior del Pod**
```bash
workload_kubectl exec -it nginx-lab -- sh
# Inside the container:
nginx -v
ls /usr/share/nginx/html/
exit
```

### Verificación
```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
```

---

## Ejercicio 2: Deployment

### Pasos

**Paso 2.1: Crear el Deployment**
Durante la actualización intencional con una imagen incorrecta, el Deployment conserva las réplicas antiguas que están listas porque `maxUnavailable` está en 0 y `maxSurge` en 1. Se necesita capacidad libre para el aumento temporal de réplicas y los Pods en proceso de terminación, además del Pod independiente. Esto no garantiza disponibilidad ante otros fallos no relacionados.

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

**Paso 2.2: Comprobar el estado del Deployment**
```bash
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get deployment nginx-deploy
workload_kubectl get replicasets,pods -l app=nginx-deploy
```

**Paso 2.3: Escalar**
```bash
workload_kubectl scale deployment nginx-deploy --replicas=5
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get pods -l app=nginx-deploy
```

<details>
<summary>¿Necesitas una pista?</summary>

- `kubectl get pods -w` supervisa los cambios en tiempo real
- El Deployment administra automáticamente ReplicaSet
- Usa la opción `-l` para filtrar por etiquetas
</details>

### Verificación
```bash
READY=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
printf 'Ready replicas: %s\n' "$READY"
[ "$READY" = "5" ]
```

---

## Ejercicio 3: Actualización progresiva

### Pasos

**Paso 3.1: Actualizar la imagen**
Esto cambia la variante de la imagen base de la misma versión mantenida de NGINX; no cambia a una versión antigua y sin soporte de NGINX. `kubernetes.io/change-cause` registra el motivo sin usar la opción obsoleta `--record`. Guarda la revisión completada para el ejercicio de reversión.

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

**Paso 3.2: Consultar el historial de actualizaciones**
```bash
workload_kubectl rollout history deployment/nginx-deploy
workload_kubectl get replicasets -l app=nginx-deploy -o wide
```

### Verificación
```bash
workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
# Expected configured image: nginx:1.30.6-alpine
```

---

## Ejercicio 4: Reversión

### Pasos

**Paso 4.1: Actualizar con una imagen no válida (error intencional)**
El registro reservado `.invalid` genera un fallo intencional en este laboratorio aislado. Un timeout de la actualización también puede deberse a problemas de programación, cuota o API; por eso, confirma los eventos y el estado de los Pods. La reversión restaura una plantilla de Pod retenida, no datos externos, el contenido de ConfigMap/Secret ni las migraciones de bases de datos.

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

**Paso 4.2: Comprobar el error y revertir**
```bash
workload_kubectl get pods -l app=nginx-deploy
workload_kubectl describe deployment nginx-deploy
workload_kubectl get events --sort-by=.metadata.creationTimestamp
workload_kubectl rollout undo deployment/nginx-deploy \
  --to-revision="${WORKLOADS_LAB_GOOD_REVISION:?Complete Step 3.1 first}"
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

### Verificación
```bash
IMAGE=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
printf 'Current image: %s\n' "$IMAGE"
[ "$IMAGE" = "nginx:1.30.6-alpine" ]
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

---

## Limpieza
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


## Referencias y alcance de la validación

* [Deployments, actualizaciones progresivas y reversiones](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
* [kubectl rollout undo](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_undo/)
* [Sondas de disponibilidad y actividad](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

Los manifiestos y comandos se comprobaron localmente. En esta auditoría no se desplegó ningún clúster, no se descargaron imágenes, no se escalaron cargas de trabajo, no se realizó ninguna reversión ni se eliminó ningún espacio de nombres.

## Próximos pasos
- [Cuestionario sobre Pods y cargas de trabajo](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [Laboratorio de Services y redes](./03-services-networking-lab.md)
