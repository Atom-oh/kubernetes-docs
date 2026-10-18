# Estrategias de ubicación de cargas de trabajo

< [Anterior: Integración de GPU](./05-gpu-integration.md) | [Tabla de contenido](./README.md) | [Siguiente: Administración del ciclo de vida de los nodos](./07-node-lifecycle.md) >

> **Versiones compatibles**: versiones de EKS compatibles con Karpenter; se revisaron las interfaces de Kubernetes 1.36.5 y Karpenter/provider 1.14.1 (línea base de revisión fijada).
> **Última actualización**: October 16, 2026

Este capítulo ubica las cargas de trabajo en nodos Hybrid y en la nube, y explica los límites del escalado hacia la nube y del costo de eliminación de Pods. Los ejemplos son patrones de configuración y parches validados localmente. Durante la auditoría no se creó capacidad en la nube, no se modificaron nodos ni se crearon aplicaciones o cargas de trabajo de GPU.

## Restricciones de ubicación y permisos

| Mecanismo | Función | Lo que no garantiza |
|---|---|---|
| `nodeSelector` / afinidad de nodo obligatoria | Filtra los nodos aptos durante la programación | La presencia de datos, dependencias en buen estado o la migración de Pods existentes después de cambiar las etiquetas |
| Afinidad de nodo preferida | Agrega preferencias de programación | Ubicación estricta con prioridad en las instalaciones, una proporción fija o el movimiento automático de Pods en ejecución |
| Taint / toleration | Excluye los Pods que no tienen la toleration correspondiente | Una toleration coincidente no atrae a un Pod ni demuestra que use una GPU |
| Anti-afinidad de Pods / distribución de topología | Controla o puntúa la distribución entre dominios aptos | Disponibilidad completa ante fallos compartidos de hosts físicos, energía, almacenamiento o red |
| PDB | Restringe las solicitudes de desalojo voluntario admitidas | Disponibilidad general, ubicación o protección frente a todas las rutas de eliminación o reducción de escala |

Usa la etiqueta `eks.amazonaws.com/compute-type=hybrid` junto con etiquetas de ubicación administradas por el propietario. `DoesNotExist` para la etiqueta de tipo de cómputo no define la “nube”: los nodos válidos de la nube pueden tener etiquetas de tipo de cómputo, y que un nodo no tenga etiquetas no demuestra que su ubicación en la nube esté aprobada.

Los ejemplos usan `workload.example.com/location=onprem` en los nodos Hybrid, como en [Arranque de nodos](./04-node-bootstrap.md), y `cloud` en el pool de Karpenter específico que aparece a continuación. Las etiquetas son parámetros operativos, no controles autónomos de residencia de datos ni de seguridad. También importan la topología del almacenamiento, el tráfico de salida, IAM y la administración confiable de los nodos.

Establece la etiqueta de ubicación mediante la configuración del propietario real del nodo: por ejemplo, la opción de kubelet `--node-labels=workload.example.com/location=onprem` de nodeadm o el ajuste equivalente de etiquetas de nodo de Bottlerocket. Un NodeConfig mínimo que solo contiene credenciales no agrega automáticamente esta etiqueta personalizada.

### Taints opcionales

Un taint de Hybrid es opcional. Antes de agregar uno, asegúrate de que los Pods necesarios de CNI, DNS, infraestructura de GPU y aplicaciones tengan las tolerations requeridas; el ejemplo anterior de GPU no tolera automáticamente todos los taints que se puedan inventar.

```bash
# Identified node only; owner-approved scheduling-policy change.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${NODE_NAME:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  taint node "$NODE_NAME" eks.amazonaws.com/compute-type=hybrid:NoSchedule
```

Para un taint específico de GPU, usa una convención revisada, como `nvidia.com/gpu=present:NoSchedule`, y alinea las tolerations de infraestructura y cargas de trabajo. Un Pod que solo use CPU también puede tolerar ese taint; la admisión y la política de solicitudes de recursos son aspectos independientes.

`NoSchedule` afecta la programación de nuevos Pods, mientras que `PreferNoSchedule` es una preferencia de evitación flexible. `NoExecute` puede desalojar Pods existentes según sus tolerations y cualquier valor de `tolerationSeconds`. Ni cambiar una etiqueta ni una regla de afinidad obligatoria con `IgnoredDuringExecution` reubica automáticamente los Pods que ya están en ejecución.

## Preparar el pool de escalado hacia la nube

Karpenter crea capacidad de EC2 para los Pods pendientes aptos. No agrega servidores locales. HPA/KEDA o un controlador de aplicaciones ajusta la demanda de réplicas; el aprovisionador de nodos es un bucle de control independiente. Las cuotas de AWS, la disponibilidad de ofertas, las IP de subred, IAM, el arranque de nodos y las dependencias de las cargas de trabajo pueden impedir la expansión.

Usa una versión de Karpenter compatible con la versión minor de Kubernetes del clúster; la matriz de compatibilidad actual requiere al menos la **1.13 para Kubernetes 1.36**. Este ejemplo se verificó con las CRD de la **1.14.1**, fijadas como línea base de revisión; no refleja los cambios de la 1.15.0 (10 de octubre de 2026). Es un ejemplo de `EC2NodeClass` de Karpenter autoadministrado, no un `NodeClass` de Auto Mode.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cloud-burst-pool
spec:
  template:
    metadata:
      labels:
        workload.example.com/location: cloud
    spec:
      taints:
        - key: workload.example.com/cloud-burst
          value: "true"
          effect: NoSchedule
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: [amd64]
        - key: kubernetes.io/os
          operator: In
          values: [linux]
        - key: topology.kubernetes.io/zone
          operator: In
          values: [ap-northeast-2a, ap-northeast-2b]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [spot, on-demand]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [m6i.xlarge, m6i.2xlarge, m6i.4xlarge]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: hybrid-cloud-burst
  limits:
    cpu: "1000"
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
      - nodes: "1"
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: hybrid-cloud-burst
spec:
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-0123456789abcdef0
  subnetSelectorTerms:
    - id: subnet-0123456789abcdef0
    - id: subnet-0fedcba9876543210
  securityGroupSelectorTerms:
    - id: sg-0123456789abcdef0
  instanceProfile: REPLACE_WITH_APPROVED_EC2_NODE_INSTANCE_PROFILE
```

**Reemplaza todos los ID de recursos de AWS de ejemplo y el perfil de instancia antes de aplicar la configuración.** Selecciona una AMI de AL2023 inmutable y aprobada para la región, la arquitectura y la versión de Kubernetes; `amiFamily: AL2023` proporciona la familia de arranque cuando se selecciona una AMI por ID. El perfil de instancia es un **perfil de nodo de EC2** preparado, no el rol Hybrid de SSM/IAM Roles Anywhere. Las subredes y los grupos de seguridad deben corresponder realmente a las zonas de disponibilidad y a la red privada previstas.

La restricción de zonas de disponibilidad va en `requirements`; nunca falsifiques una zona de AWS incluyéndola en las etiquetas de la plantilla. El taint de activación voluntaria del pool limita la elegibilidad a las cargas de trabajo con la toleration coincidente. No otorga acceso a los datos ni al registro.

Los límites `1000` CPU / `4000Gi` se mantienen como **ejemplos de planificación** grandes, no como asignación recomendada ni límite de gasto. Ajústalos antes de usarlos. Karpenter comprueba los límites con consistencia eventual, por lo que un aprovisionamiento rápido puede superarlos. `budgets: [{nodes: "1"}]` limita la concurrencia de las interrupciones voluntarias correspondientes; no reserva capacidad mínima.

Usa una definición completa de NodePool. Aplicar un segundo objeto parcial con el mismo nombre no es una forma segura de “heredar la configuración anterior”. Los cambios de vencimiento, selección de AMI y política de interrupción necesitan su propio despliegue revisado.

## Cargas de trabajo locales, exclusivas de la nube y aptas para escalado

Crea un espacio de nombres de laboratorio aprobado, como `hybrid-placement-lab`, y prepara resúmenes de imagen reales, configuraciones de seguridad de aplicaciones, comprobaciones, almacenamiento y acceso al registro antes de ejecutar cargas de trabajo. Estos ejemplos comienzan con **cero réplicas** y usan intencionalmente imágenes no utilizables. Los recuentos anteriores de 3/5/10 réplicas son posibles escenarios de dimensionamiento, no capacidades medidas ni promesas de que las aplicaciones funcionarán.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hybrid-local-processor
  namespace: hybrid-placement-lab
spec:
  replicas: 0
  selector:
    matchLabels:
      app: hybrid-local-processor
  template:
    metadata:
      labels:
        app: hybrid-local-processor
    spec:
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/location: onprem
      tolerations:
        - key: eks.amazonaws.com/compute-type
          operator: Equal
          value: hybrid
          effect: NoSchedule
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: processor
          image: registry.example.invalid/approved/data-processor:replace-with-approved-digest
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: "2"
              memory: 4Gi
            limits:
              cpu: "4"
              memory: 8Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hybrid-cloud-api
  namespace: hybrid-placement-lab
spec:
  replicas: 0
  selector:
    matchLabels:
      app: hybrid-cloud-api
  template:
    metadata:
      labels:
        app: hybrid-cloud-api
    spec:
      nodeSelector:
        workload.example.com/location: cloud
        karpenter.sh/nodepool: cloud-burst-pool
      tolerations:
        - key: workload.example.com/cloud-burst
          operator: Equal
          value: "true"
          effect: NoSchedule
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: api
          image: registry.example.invalid/approved/inference-api:replace-with-approved-digest
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: "2"
              memory: 4Gi
            limits:
              cpu: "4"
              memory: 8Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hybrid-burst-app
  namespace: hybrid-placement-lab
spec:
  replicas: 0
  selector:
    matchLabels:
      app: hybrid-burst-app
  template:
    metadata:
      labels:
        app: hybrid-burst-app
    spec:
      tolerations:
        - key: eks.amazonaws.com/compute-type
          operator: Equal
          value: hybrid
          effect: NoSchedule
        - key: workload.example.com/cloud-burst
          operator: Equal
          value: "true"
          effect: NoSchedule
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: eks.amazonaws.com/compute-type
                    operator: In
                    values: [hybrid]
                  - key: workload.example.com/location
                    operator: In
                    values: [onprem]
              - matchExpressions:
                  - key: workload.example.com/location
                    operator: In
                    values: [cloud]
                  - key: karpenter.sh/nodepool
                    operator: In
                    values: [cloud-burst-pool]
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: workload.example.com/location
                    operator: In
                    values: [onprem]
      topologySpreadConstraints:
        - maxSkew: 2
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: hybrid-burst-app
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: registry.example.invalid/approved/latency-app:replace-with-approved-digest
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: "1"
              memory: 2Gi
            limits:
              cpu: "2"
              memory: 4Gi
```

El procesador local requiere tanto la etiqueta Hybrid como la etiqueta de las instalaciones. La API en la nube requiere el pool de escalado propiedad del grupo especificado. Otros grupos de EC2 aprobados necesitan sus propias reglas explícitas de selección; la ausencia de etiquetas no equivale a una autorización alternativa.

La aplicación con escalado tiene dos términos de afinidad de nodo unidos por **OR**: el conjunto aprobado de las instalaciones o el pool de la nube aprobado. Las expresiones de un mismo término son condiciones **AND**. Prefiere la ubicación en las instalaciones, pero también se aplican la puntuación del scheduler, las solicitudes de recursos, los taints y las preferencias de topología. Karpenter puede relajar las preferencias de programación al planificar nuevos nodos; esto no es un sensor de saturación ni una garantía de que primero se ocupen todas las plazas de las instalaciones.

Pesos como 100 y 50 son puntuaciones de programación, no una asignación de capacidad de 2:1. Un nodo puede alojar varios Pods o ninguno compatible, por lo que “ocho nodos significa que los Pods1–8 se ejecutan localmente y los Pods9+ usan capacidad ilimitada en la nube” no es un modelo válido.

Cuando vuelve la capacidad de las instalaciones, los Pods en ejecución en la nube no se trasladan de vuelta automáticamente. Cualquier reequilibrio requiere una política independiente y controlada de despliegue o desalojo, teniendo en cuenta los datos y la disponibilidad.

Para el entrenamiento de GPU en las instalaciones y las API de CPU en la nube, mantén explícitos los requisitos de GPU y el movimiento de datos. Usa los patrones acotados de Job/asignación de [Integración de GPU](./05-gpu-integration.md). La solicitud anterior de entrenamiento de **4 GPU / 16 CPU / 64Gi** era un ejemplo de dimensionamiento; requiere capacidad real de GPU, dispositivos compatibles y acceso duradero a los datos de entrada y a los puntos de control. Un Deployment que se reinicia repetidamente para ejecutar un proceso de entrenamiento finito no sustituye a un Job ni al controlador de entrenamiento apropiado.

### Topología y localidad de los datos

Asigna etiquetas precisas de dominios de fallo antes de usar `topology.kubernetes.io/zone`; usa valores reales de zonas de disponibilidad de AWS para los nodos de la nube y dominios significativos para las instalaciones. No etiquetes todos los hosts Hybrid como si fueran zonas de disponibilidad de AWS para satisfacer un selector.

Con `ScheduleAnyway`, la regla de distribución del ejemplo de escalado es una preferencia de puntuación y puede superar `maxSkew`. Con `DoNotSchedule`, el sesgo se comprueba con respecto al **mínimo global entre los dominios aptos**, teniendo en cuenta `minDomains` cuando está configurado; no siempre se calcula como una simple diferencia entre el máximo y el mínimo de todas las zonas del clúster.

La distribución estricta o la anti-afinidad pueden dejar Pods en estado Pending cuando no hay suficientes nodos o dominios aptos. La elegibilidad de los nodos también depende de la afinidad, los taints y la política de topología. La distribución estricta y el uso máximo de la capacidad local pueden ser objetivos incompatibles; elige deliberadamente el equilibrio.

La anti-afinidad obligatoria por nombre de host puede mantener réplicas coincidentes en distintos nodos de Kubernetes cuando hay capacidad suficiente. No garantiza que las réplicas restantes estén en buen estado, tengan suficiente capacidad de servicio ni eviten un fallo físico compartido.

Las etiquetas de localidad de datos no crean ni replican datos. Para datos persistentes locales, usa un PV/PVC local administrado correctamente, con afinidad de nodo del PV y el flujo de asociación apropiado de `WaitForFirstConsumer`. Un `hostPath: /mnt/data` sin más no verifica el conjunto de datos ni proporciona persistencia portátil. Un Pod asociado a almacenamiento local no puede recurrir sin más a un nodo de EC2; planifica la replicación, el almacenamiento accesible o una ruta de aplicación independiente.

## El costo de eliminación de Pods es una preferencia

`controller.kubernetes.io/pod-deletion-cost` es una anotación entera de un Pod. Su rango válido es **−2147483648 a 2147483647** y su valor predeterminado es 0 si no está presente; se permiten valores negativos. La reducción de escala de ReplicaSet prefiere, **en la medida de lo posible**, los valores más bajos entre sus Pods.

En el controlador revisado de Kubernetes1.36.5, estas comparaciones preceden al costo de eliminación:

1. Pods sin asignar antes que Pods asignados.
2. Pending antes que Unknown y luego Running.
3. NotReady antes que Ready.
4. Solo entonces, menor costo de eliminación antes que mayor costo.

Las comparaciones adicionales incluyen la colocación conjunta de réplicas, el tiempo en estado Ready, los recuentos de reinicios y la antigüedad de creación. Por lo tanto, un Pod en mal estado en las instalaciones con costo1000 puede eliminarse antes que un Pod saludable en la nube con costo0. El costo1000 no protege contra el desalojo, un despliegue, un fallo del nodo, la eliminación manual ni otro controlador.

El ejemplo original “10 réplicas →4; eliminar los6 Pods de la nube y conservar los4 Pods de las instalaciones” es solo una **ilustración condicional**: todos los Pods tendrían que pertenecer al mismo ReplicaSet, cumplir criterios compatibles de mayor prioridad y encontrarse en un estado estable. No es un resultado garantizado, especialmente entre revisiones de Deployment.

La capacidad de las instalaciones también conlleva costos de energía, mantenimiento y oportunidad; conservarla es un objetivo operativo que se debe evaluar, no una regla económica universal. Los valores del costo de eliminación no imponen por sí solos un presupuesto de gasto ni un objetivo de disponibilidad.

## Asignar el costo después de asociar un Pod propio

Una solicitud de admisión normal `CREATE` de un Pod normalmente no tiene asignado `spec.nodeName`. Un webhook mutador que solo actúa en CREATE no puede determinar de forma confiable la ubicación eventual del nodo. El ejemplo anterior del webhook tampoco tenía una configuración funcional de Service/TLS/backend/RBAC y podía bloquear la creación de Pods mediante su política de fallo. No lo instales como solución de producción.

Para una operación pequeña y controlada, calcula el costo **después de la programación**. El siguiente script lee un Pod seleccionado, comprueba el UID del ReplicaSet controlador y la clasificación del nodo, y escribe un JSON Patch privado para su revisión. No examina ni modifica todos los espacios de nombres.

Establece `NAMESPACE`, `POD_NAME` y `EXPECTED_RS_UID` según la cadena real de propiedad Deployment/ReplicaSet del propietario de la aplicación, no solo a partir de una etiqueta compartida. El script solo reconoce las convenciones de ubicación y el pool de la nube de este capítulo.

```bash
#!/usr/bin/env bash
# Read one owned, scheduled ReplicaSet Pod and write a reviewable JSON Patch.
# This script does not mutate the cluster.
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${NAMESPACE:?}" "${POD_NAME:?}"
: "${EXPECTED_RS_UID:?UID of the ReplicaSet owned by the application operator}"
[[ "$NAMESPACE" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ && ${#NAMESPACE} -le 63 ]]
[[ "$POD_NAME" =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ && ${#POD_NAME} -le 253 ]]
PLAN_DIR=$(mktemp -d ./deletion-cost-review.XXXXXXXX)
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get pod "$POD_NAME" -n "$NAMESPACE" -o json |
  jq '{metadata: {name: .metadata.name, namespace: .metadata.namespace,
      uid: .metadata.uid, resourceVersion: .metadata.resourceVersion,
      ownerReferences: .metadata.ownerReferences,
      deletionTimestamp: .metadata.deletionTimestamp},
    nodeName: .spec.nodeName,
    hasAnnotations: (.metadata.annotations | type == "object"),
    currentCost: .metadata.annotations["controller.kubernetes.io/pod-deletion-cost"]}' \
    > "$PLAN_DIR/pod.json"
jq -e --arg ns "$NAMESPACE" --arg pod "$POD_NAME" --arg owner "$EXPECTED_RS_UID" '
  .metadata.namespace == $ns and .metadata.name == $pod and
  (.metadata.uid | type == "string" and length > 0) and
  (.metadata.resourceVersion | type == "string" and length > 0) and
  .metadata.deletionTimestamp == null and
  ([.metadata.ownerReferences[]? | select(.controller == true)] | length == 1) and
  any(.metadata.ownerReferences[]?; .controller == true and
    .apiVersion == "apps/v1" and .kind == "ReplicaSet" and .uid == $owner) and
  (.nodeName | type == "string" and length > 0)' "$PLAN_DIR/pod.json" > /dev/null
NODE_NAME=$(jq -er '.nodeName' "$PLAN_DIR/pod.json")
[[ "$NODE_NAME" =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ ]]
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$NODE_NAME" -o json |
  jq '{metadata: {name: .metadata.name, uid: .metadata.uid, labels: {
    compute: .metadata.labels["eks.amazonaws.com/compute-type"],
    location: .metadata.labels["workload.example.com/location"],
    nodepool: .metadata.labels["karpenter.sh/nodepool"]}}}' > "$PLAN_DIR/node.json"
desired=$(jq -er --arg node "$NODE_NAME" '
  if .metadata.name != $node or (.metadata.uid | type != "string" or length == 0) then
    error("unexpected Node identity")
  elif .metadata.labels.compute == "hybrid" and .metadata.labels.location == "onprem" then "1000"
  elif .metadata.labels.compute != "hybrid" and .metadata.labels.location == "cloud"
       and .metadata.labels.nodepool == "cloud-burst-pool" then "0"
  else error("unknown or conflicting node classification") end' "$PLAN_DIR/node.json")
jq --arg cost "$desired" '
  [{op:"test",path:"/metadata/uid",value:.metadata.uid},
   {op:"test",path:"/metadata/resourceVersion",value:.metadata.resourceVersion},
   {op:"test",path:"/spec/nodeName",value:.nodeName}]
  + (if .hasAnnotations then [] else
       [{op:"add",path:"/metadata/annotations",value:{}}] end)
  + (if .currentCost == $cost then [] else
       [{op:"add",path:"/metadata/annotations/controller.kubernetes.io~1pod-deletion-cost",
         value:$cost}] end)' "$PLAN_DIR/pod.json" > "$PLAN_DIR/patch.json"
printf 'Review private snapshots and patch in %s; nothing was applied.\n' "$PLAN_DIR"
```

Inspecciona las instantáneas y la anotación deseada antes de aplicar el parche. El parche comprueba el UID, resourceVersion y nodo asociado del Pod, de modo que, si se reemplaza o se modifica simultáneamente, la operación falla en vez de sobrescribir el Pod más reciente. Agrega solo la clave del costo de eliminación y conserva las demás anotaciones.

Establece `PLAN_DIR` en tu shell con el directorio impreso por el script; un proceso hijo no establece esa variable en el proceso que lo invocó.

```bash
# Cluster write, only after the named Pod/owner and generated patch are reviewed.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${NAMESPACE:?}" "${POD_NAME:?}" "${PLAN_DIR:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  patch pod "$POD_NAME" -n "$NAMESPACE" --type=json \
  --patch-file "$PLAN_DIR/patch.json"
```

Si falla una comprobación o cambia la clasificación del nodo, vuelve a generar el parche y revísalo con el estado actualizado. No elimines las comprobaciones ni uses `--overwrite` en Pods que no estén relacionados. Coordina quién es responsable de la anotación con cualquier controlador existente.

Evita actualizar continuamente los costos a partir de métricas que cambian rápidamente; Kubernetes documenta la sobrecarga de las actualizaciones de la API. Un controlador de producción posterior a la asociación necesitaría permisos limitados con precisión, comprobaciones de propiedad, reintentos acotados y gestión de conflictos. El CronJob anterior, sin implementar y dirigido a todos los espacios de nombres, sin ServiceAccount/ConfigMap y con la imagen mutable `bitnami/kubectl:latest`, no constituye tal controlador.

RBAC a nivel de espacio de nombres puede limitar el alcance de los parches de Pods; RBAC ordinario no permite expresar selectores arbitrarios de etiquetas de Pods como autorización. Conviene separar de forma adecuada un lector de metadatos de nodos y un escritor para el espacio de nombres de la aplicación. Este ejemplo administrativo para un solo Pod no concede permisos de escritura en todo el clúster.

## Interacción con Karpenter

Karpenter1.14.1 también lee `pod-deletion-cost` en su **heurística normalizada de costo de desalojo**, junto con la prioridad del Pod; es incorrecto afirmar que solo lo usa ReplicaSet. Karpenter combina los costos de los Pods con información de nodos e interrupciones. Un valor de1000 no garantiza conservar el Pod mil veces más.

| Control | Alcance |
|---|---|
| Costo de eliminación de ReplicaSet | Preferencia entre los candidatos a reducción de escala de ReplicaSet |
| Costo de interrupción de Karpenter | Heurística para evaluar candidatos; no prohíbe el desalojo |
| `WhenEmpty` | Puede consolidar nodos aptos sin Pods de cargas de trabajo pertinentes después del retraso y las comprobaciones configurados |
| `WhenEmptyOrUnderutilized` | Puede mover cargas de trabajo durante la consolidación, sujeto a las restricciones aplicables |
| PDB / presupuestos de interrupción / ajustes del ciclo de vida | Controles distintos con alcances diferentes; ninguno debe reemplazarse por una anotación de costo |

No se garantiza que los nodos vacíos desaparezcan de inmediato: siguen aplicándose la reconciliación, los presupuestos de interrupción, los finalizers y la terminación en la nube. Las preferencias de afinidad y distribución también pueden reducir las oportunidades de consolidación. Evalúalos conjuntamente en vez de suponer que cada reducción de escala de HPA provoca la eliminación correspondiente de un nodo de la nube.

![Flujo condicional de reducción de escala: el costo de eliminación es una preferencia, y Karpenter puede eliminar más adelante los nodos vacíos aptos de la nube.](../.gitbook/assets/en-eks-hybrid-nodes-06-workload-placement-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-06-workload-placement-0.html)

> **Corrección del diagrama:** la eliminación de Pods de la nube primero y la conservación completa de los Pods de las instalaciones son objetivos de mejor esfuerzo, no invariantes. Incluso los nodos “vacíos” pueden contener Pods de DaemonSet. La etiqueta anterior `WhenUnderutilized` debería decir `WhenEmptyOrUnderutilized` en el ejemplo de v1. Consulta arriba el orden de evaluación y las condiciones del ciclo de vida.

## Referencias principales

- [Asignar Pods a nodos](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Taints y tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
- [Distribución de topología de Pods](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Costo de eliminación de ReplicaSet](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)
- [Comparación para la reducción de escala de Kubernetes1.36.5](https://github.com/kubernetes/kubernetes/blob/v1.36.5/pkg/controller/controller_utils.go)
- [Interrupciones de Pods y alcance de PDB](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Volúmenes locales y afinidad de nodo de PV](https://kubernetes.io/docs/concepts/storage/volumes/#local)
- [Asociación de volúmenes de StorageClass](https://kubernetes.io/docs/concepts/storage/storage-classes/#volume-binding-mode)
- [NodePools de Karpenter](https://karpenter.sh/docs/concepts/nodepools/) y [compatibilidad](https://karpenter.sh/docs/upgrading/compatibility/)
- [Interrupciones de Karpenter](https://karpenter.sh/docs/concepts/disruption/)
- [Implementación del costo de desalojo de Karpenter1.14.1](https://github.com/kubernetes-sigs/karpenter/blob/v1.14.1/pkg/utils/disruption/disruption.go)

< [Anterior: Integración de GPU](./05-gpu-integration.md) | [Tabla de contenido](./README.md) | [Siguiente: Administración del ciclo de vida de los nodos](./07-node-lifecycle.md) >
