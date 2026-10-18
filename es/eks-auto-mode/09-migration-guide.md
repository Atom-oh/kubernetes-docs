# Migración de Managed Node Groups a Auto Mode

> **Versiones compatibles**: EKS Auto Mode con disponibilidad general; ejemplos revisados para EKS 1.36
> **Última actualización**: 12 de septiembre de 2026

Antes de retirar la capacidad existente, compruebe las aplicaciones, el almacenamiento y qué controlador gestiona cada recurso. Los ejemplos siguientes muestran operaciones por etapas cuyos esquemas y casos de prueba de CLI se comprobaron localmente; no acreditan una migración de producción sin interrupciones. Durante la auditoría descrita en la fuente no se modificaron recursos de nube ni del clúster.

![Vista general de la migración existente en siete etapas. Valide cada grupo de cargas de trabajo antes de escalar o eliminar la capacidad antigua; la fase final de validación es una auditoría posterior a la limpieza, no la primera comprobación del estado.](../.gitbook/assets/en-eks-auto-mode-09-migration-guide-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-auto-mode-09-migration-guide-0.html)

El paso final de validación del diagrama no autoriza el desalojo, el escalado a cero ni la eliminación sin comprobaciones previas del estado y un plan de reversión.

## 1. Inventariar los recursos y fijar el contexto operativo

Utilice una combinación de EKS y complementos que siga siendo compatible. El antiguo mínimo de 1.29 indicaba la versión que incorporó la función, no una recomendación de compatibilidad actual. Compruebe la compatibilidad de VPC CNI, kube-proxy, EBS CSI, el controlador de snapshots y Pod Identity Agent cuando estén instalados. Consulte tanto los mínimos oficiales de migración **como** la lista de compatibilidad para la versión de Kubernetes que utiliza.

Registre qué controlador gestiona cada recurso, dónde se ejecutan las cargas, los agentes del sistema, los volúmenes y sus AZ, las clases de balanceadores, IAM, los procedimientos de recuperación y los costos. Las comprobaciones siguientes verifican la cuenta y, tanto para el clúster como para el node group, el ARN y la fecha de creación; también verifican el endpoint de la API. Comprueban la identidad en ese momento y no bloquean de forma atómica a otros controladores. Si la API se expone intencionadamente a través de un proxy, revise una alternativa para esta comprobación; no ignore una discrepancia.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended account}"
: "${AWS_REGION:?Set the cluster region}"
: "${CLUSTER_NAME:?Set the cluster name}"
: "${OLD_NODEGROUP:?Set the reviewed managed node group}"
: "${KUBECONFIG:?Set the reviewed kubeconfig}"
export KUBECONFIG
export KUBE_CONTEXT="${KUBE_CONTEXT:-$CLUSTER_NAME}"
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-migration.XXXXXXXX")
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --output json \
  > "$WORK_DIR/cluster-before.json"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
  --region "$AWS_REGION" --output json > "$WORK_DIR/nodegroup-before.json"
guard_context() {
  check_account || return
  local endpoint
  aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --output json \
    > "$WORK_DIR/cluster-current.json" || return
  endpoint=$(kubectl --context "$KUBE_CONTEXT" config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}') || return
  jq -e --arg endpoint "$endpoint" --slurpfile before "$WORK_DIR/cluster-before.json" '
    .cluster.arn == $before[0].cluster.arn and
    .cluster.createdAt == $before[0].cluster.createdAt and
    .cluster.endpoint == $endpoint and .cluster.status == "ACTIVE"
  ' "$WORK_DIR/cluster-current.json" >/dev/null
}
guard_nodegroup() {
  guard_context || return
  aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
    --region "$AWS_REGION" --output json > "$WORK_DIR/nodegroup-current.json" || return
  jq -e --slurpfile before "$WORK_DIR/nodegroup-before.json" '
    .nodegroup.nodegroupArn == $before[0].nodegroup.nodegroupArn and
    .nodegroup.createdAt == $before[0].nodegroup.createdAt and .nodegroup.status == "ACTIVE"
  ' "$WORK_DIR/nodegroup-current.json" >/dev/null
}
guard_nodegroup
printf 'Private migration evidence: %s\n' "$WORK_DIR"
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get deployments,statefulsets,daemonsets,jobs,cronjobs -A -o json |
jq '[.items[] | (.spec.template // .spec.jobTemplate.spec.template) as $t |
 {kind,namespace:.metadata.namespace,name:.metadata.name,uid:.metadata.uid,
  nodeSelector:$t.spec.nodeSelector,affinity:$t.spec.affinity,tolerations:$t.spec.tolerations,
  serviceAccountName:$t.spec.serviceAccountName,hostNetwork:$t.spec.hostNetwork,
  pvcNames:[$t.spec.volumes[]?.persistentVolumeClaim.claimName // empty]}]' \
  > "$WORK_DIR/workload-placement.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
jq '[.items[] | {namespace:.metadata.namespace,name:.metadata.name,node:.spec.nodeName,
  phase:.status.phase,deletionTimestamp:.metadata.deletionTimestamp,
  ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported"),
  owners:[.metadata.ownerReferences[]?|{kind,name,controller}]}]' \
  > "$WORK_DIR/pod-state.json"
```

Los archivos privados contienen metadatos operativos; consérvelos para la recuperación. Si una consulta falla, trate el resultado como un error. `kubectl top` requiere una API de métricas operativa, y una muestra puntual de CPU no sustituye al historial de la carga.

| Configuración existente | Consideración para la migración |
|------------------------|---------------------------------|
| AMI/arranque/datos de usuario personalizados | Auto Mode usa Bottlerocket administrado, no AL2023/AMI/userData arbitrarios |
| Permisos de IAM de los nodos | Prepare el rol/perfil del nodo/la entrada de acceso; migre los permisos de las cargas de trabajo a IRSA/Pod Identity revisados en lugar de recurrir al rol del nodo/IMDS |
| Rol de IAM del clúster | Añada al rol existente los permisos y la relación de confianza necesarios para Auto Mode; habilitarlo mediante CLI no crea automáticamente todos los roles |
| Selectores/afinidad/taints | Incluya Deployments, StatefulSets, DaemonSets, Jobs y CronJobs; elimine deliberadamente las reglas de ubicación incompatibles |
| CNI alternativo/configuración de red | Compruebe la compatibilidad documentada antes de habilitarlo; un NodeClass no corrige una configuración de red no compatible |
| Propiedad del escalado/IaC | Coordine Cluster Autoscaler, GitOps y al propietario de IaC original para que no reviertan los cambios de migración |

### Datos, balanceadores de carga y DNS en clústeres con distintos tipos de nodo

Los drivers de almacenamiento y los controladores utilizan interfaces diferentes:

| Recurso | Autogestionado | Auto Mode |
|----------|--------------|-----------|
| Aprovisionador de StorageClass de EBS | `ebs.csi.aws.com` | `ebs.csi.eks.amazonaws.com` |
| loadBalancerClass del Service NLB | `service.k8s.aws/nlb` | `eks.amazonaws.com/nlb` |
| Controlador de IngressClass ALB | `ingress.k8s.aws/alb` | `eks.amazonaws.com/alb` |
| apiVersion de TargetGroupBinding | `elbv2.k8s.aws/v1beta1` | `eks.amazonaws.com/v1` |
| Clase de cómputo | `karpenter.k8s.aws/v1 EC2NodeClass` | `eks.amazonaws.com/v1 NodeClass` |

Editar el nombre de StorageClass de un PVC existente no cambia su driver, y el controlador administrado no adopta automáticamente un balanceador existente. Para EBS, utilice un plan probado de restauración desde backup o snapshot, o el procedimiento actual documentado por AWS: **detener la carga, usar Retain y recrear estáticamente los PV/PVC**. Este último reutiliza el volumen EBS, pero recrea los objetos de vinculación de Kubernetes; no cambia el driver sobre los objetos existentes. Verifique la restauración de backups, los responsables del volumen, la AZ y KMS, la política de recuperación, los finalizers, las vinculaciones y la coherencia de los datos de la aplicación. Esta guía no incluye un script destructivo de migración de volúmenes.

Mantenga el AWS Load Balancer Controller autogestionado mientras gestione recursos. Cree y pruebe el nuevo balanceador administrado y cambie el tráfico mediante un plan DNS blue/green revisado antes de retirar el anterior. Revise por separado la inmutabilidad de las clases, las anotaciones y qué controlador gestiona los TargetGroupBindings; cambiar el grupo de API no basta para transferir su gestión de forma segura.

Los nodos de Auto Mode tienen DNS local. **Conserve el Deployment de CoreDNS mientras lo necesite algún nodo que no utilice Auto Mode.** Mantenga los agentes de CNI, proxy, almacenamiento e identidad que necesiten los demás tipos de nodo y delimite dónde deben ejecutarse. Los componentes administrados de un clúster formado solo por nodos Auto Mode no justifican retirar antes de tiempo las dependencias de un clúster mixto.

## 2. Habilitar Auto Mode sin un pool predeterminado de uso irrestricto

Complete primero la preparación de IAM/acceso en [Introducción](./01-getting-started.md). El rol existente del clúster necesita las políticas documentadas de Compute, **BlockStoragePolicyV2**, LoadBalancing, Networking y Cluster, además de la relación de confianza requerida para `sts:TagSession`. El ejemplo presupone autenticación API o API_AND_CONFIG_MAP, así como un rol/perfil de nodo personalizado preparado con una entrada de acceso EC2.

Este procedimiento comienza **sin pools integrados**, por lo que crea su propio NodeClass en el siguiente paso; no dé por hecho que existe `default`. Un pool de propósito general sin restricciones podría recibir cargas que ya están pendientes antes del cambio previsto. El ejemplo detiene la operación si el clúster ya ejecuta Auto Mode, en lugar de sustituir su lista de pools.

Espere a que finalice la actualización identificada por su ID específico. Que el clúster esté `ACTIVE` no demuestra por sí solo que esa actualización de configuración haya terminado correctamente.

```bash
wait_eks_update() {
  local id="$1" group="${2:-}" attempt status
  local extra=()
  test -n "$group" && extra=(--nodegroup-name "$group")
  for ((attempt=0; attempt<120; attempt++)); do
    aws eks describe-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
      --update-id "$id" "${extra[@]}" --output json > "$WORK_DIR/update-current.json" || return
    status=$(jq -er '.update.status' "$WORK_DIR/update-current.json") || return
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled)
        jq '{id:.update.id,status:.update.status,errorCodes:[.update.errors[]?.errorCode]}' \
          "$WORK_DIR/update-current.json" >&2
        return 1 ;;
      InProgress) sleep 10 ;;
      *) printf 'Unknown update state; inspect saved evidence.\n' >&2; return 1 ;;
    esac
  done
  printf 'Update still unconfirmed; stop and retain its ID.\n' >&2
  return 1
}
```

```bash
guard_context
jq -e '.cluster.computeConfig.enabled != true and
       (.cluster.accessConfig.authenticationMode == "API" or
        .cluster.accessConfig.authenticationMode == "API_AND_CONFIG_MAP")' \
  "$WORK_DIR/cluster-current.json" >/dev/null
jq -n --arg name "$CLUSTER_NAME" '{
  name:$name,
  computeConfig:{enabled:true,nodePools:[]},
  storageConfig:{blockStorage:{enabled:true}},
  kubernetesNetworkConfig:{elasticLoadBalancing:{enabled:true}}
}' > "$WORK_DIR/enable-request.json"
aws eks update-cluster-config --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/enable-request.json" --output json \
  > "$WORK_DIR/enable-response.json"
update_id=$(jq -er '.update.id' "$WORK_DIR/enable-response.json")
wait_eks_update "$update_id"
guard_context
jq -e '.cluster.computeConfig.enabled == true and
       .cluster.computeConfig.nodePools == [] and
       .cluster.storageConfig.blockStorage.enabled == true and
       .cluster.kubernetesNetworkConfig.elasticLoadBalancing.enabled == true' \
  "$WORK_DIR/cluster-current.json" >/dev/null
```

Las funciones de cómputo, almacenamiento en bloque y balanceo de carga administrado deben habilitarse o deshabilitarse juntas. Validar la estructura de la solicitud no demuestra que IAM y el servicio vayan a aceptarla. Si se produce un error, deténgase y conserve los datos de la actualización. No repita la solicitud a ciegas si la respuesta deja dudas sobre su resultado. Los cambios del modo de autenticación tienen sus propias restricciones de migración y reversión.

## 3. Crear un pool selectivo y probar la capacidad antigua y la nueva

Sustituya los marcadores del perfil, las subredes y los grupos de seguridad de NodeClass por recursos existentes revisados. El rol del perfil necesita la entrada de acceso adecuada para los nodos. Estos manifiestos no crean recursos de IAM o VPC ni credenciales de aplicación.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: migration-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: migration-nodeclass
spec:
  instanceProfile: eks-migration-node-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: migration-pool
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: migration-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: migration
        value: auto-mode
        effect: NoSchedule
    metadata:
      labels:
        migration: auto-mode
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
    - nodes: '1'
  limits:
    cpu: '32'
    memory: 128Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-canary
  namespace: migration-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: legacy-canary
  template:
    metadata:
      labels:
        app: legacy-canary
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        eks.amazonaws.com/nodegroup: REPLACE_WITH_OLD_NODEGROUP
      tolerations: []
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auto-canary
  namespace: migration-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: auto-canary
  template:
    metadata:
      labels:
        app: auto-canary
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: migration-pool
        eks.amazonaws.com/compute-type: auto
      tolerations:
      - key: migration
        operator: Equal
        value: auto-mode
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

Sustituya `REPLACE_WITH_OLD_NODEGROUP` antes de utilizar el canary del grupo antiguo. Los ejemplos completos de nginx usan la imagen que se ejecuta como usuario no root y el contexto de seguridad revisados en el capítulo de operaciones. Comprueban la ubicación y la disponibilidad básicas, no el estado de la aplicación, su identidad ni su ruta de tráfico.

El canary de Auto Mode selecciona tanto el pool concreto como `eks.amazonaws.com/compute-type=auto`. Comprobar únicamente que existe `karpenter.sh/nodepool` también seleccionaría nodos de Karpenter autogestionado. Una toleration permite que un Pod se ejecute en un nodo con el taint correspondiente; por sí sola no selecciona un pool.

| Configuración de MNG | Correspondencia en Auto Mode |
|-------------|-------------------|
| Tipos de instancia/tipo de capacidad | Requisitos exactos de instancia o categorías deliberadamente más amplias; requisito de tipo de capacidad |
| Etiquetas/taints | `spec.template.metadata.labels` / `spec.template.spec.taints` |
| Recuento mínimo/deseado/máximo de nodos | No equivale a los límites de CPU/memoria `spec.limits`; considere la semántica de pools estáticos por separado si se requieren nodos deseados fijos |
| Subred/grupos de seguridad | Selectores de NodeClass personalizados y reglas revisadas |
| AMI/arranque | Auto Mode no ofrece una correspondencia arbitraria de familia de AMI/userData |

## 4. Migrar por grupos y detenerse ante un fallo

Comience con cargas representativas de bajo riesgo. Después, migre staging y las cargas de producción no críticas; migre las críticas una vez validadas sus dependencias. Cambie **la configuración declarativa gestionada por el controlador o por GitOps**, no solo un Pod en ejecución.

Revise todas las reglas de ubicación. Si añade un selector de Auto Mode y conserva el del node group antiguo, ambas condiciones podrían impedir que el Pod se programe. No borre con `affinity: null` afinidades de Pod, restricciones de ubicación por seguridad o tolerations que no estén relacionadas con la migración. Los StatefulSets, los Jobs activos y las cargas con volúmenes locales requieren procedimientos que protejan sus datos.

Para un Deployment con al menos una réplica deseada, lo siguiente comprueba el despliegue y la disponibilidad observada de las réplicas:

```bash
: "${WORKLOAD_NAMESPACE:?Select the namespace}"
: "${DEPLOYMENT_NAME:?Select one migrated Deployment}"
kubectl --context "$KUBE_CONTEXT" -n "$WORKLOAD_NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=10m
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get deployment "$DEPLOYMENT_NAME" -o json |
jq -e '(.spec.replicas // 1) as $desired |
  $desired > 0 and .status.observedGeneration >= .metadata.generation and
  .status.updatedReplicas == $desired and .status.readyReplicas == $desired and
  .status.availableReplicas == $desired' >/dev/null
```

Verifique también las solicitudes reales, DNS, los destinos de los balanceadores de carga, los volúmenes y su comportamiento de lectura/escritura, la identidad, los registros/métricas y los SLO de la aplicación. La configuración de actualización gradual de un Deployment y las protecciones de la API de Eviction de un PDB son controles distintos. Que `rollout status` tenga éxito o que la fase del Pod sea `Running` no constituye por sí solo evidencia de disponibilidad integral; los Jobs completados pueden estar correctamente en estado `Succeeded`.

### Desalojo opcional de un solo nodo

Solo después de revisar la capacidad de reemplazo, la ubicación de las cargas de trabajo, los PDB y la durabilidad de los datos, seleccione **un** nodo administrado antiguo y su UID registrado:

```bash
: "${NODE_NAME:?Select exactly one old managed node}"
: "${EXPECTED_NODE_UID:?Set its previously reviewed UID}"
guard_nodegroup
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get node "$NODE_NAME" -o json \
  > "$WORK_DIR/node-before-drain.json"
jq -e --arg uid "$EXPECTED_NODE_UID" --arg group "$OLD_NODEGROUP" '
  .metadata.uid == $uid and .metadata.labels["eks.amazonaws.com/nodegroup"] == $group and
  .metadata.labels["eks.amazonaws.com/compute-type"] != "auto" and
  .metadata.deletionTimestamp == null and
  any(.status.conditions[]?; .type=="Ready" and .status=="True")
' "$WORK_DIR/node-before-drain.json" >/dev/null
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
printf 'Drain returned successfully. Validate application health before selecting another node.\n'
```

Este procedimiento no incluye un bucle de cordon/drain masivo, una espera fija como prueba de buen estado ni una opción para continuar tras un fallo. Por defecto, drain rechaza los Pods sin controlador y los datos locales de emptyDir si no se han gestionado expresamente. No añada `--force`, `--disable-eviction` ni `--delete-emptydir-data` para ocultar un fallo. Un drain fallido o interrumpido puede dejar el nodo marcado como no programable: inspecciónelo y restaure la programación únicamente si lo indica el plan de recuperación. Valide las aplicaciones afectadas antes de seleccionar otro nodo.

## 5. Reducir la capacidad solo después de retirar las cargas de trabajo antiguas

**Cambiar el número deseado de nodos de un MNG no respeta los PDB**: EKS reduce la capacidad mediante el ASG. Ese proceso difiere del drain habitual durante una actualización de versión del managed node group. Reducir el número deseado a la mitad y esperar cinco minutos no demuestra que el sistema se haya estabilizado.

Coordine el cambio con quien gestione el escalado y la IaC originales e impida que nuevas cargas se programen en los nodos antiguos. El ejemplo de API comprueba que todos los nodos antiguos observados estén marcados como no programables y que no tengan Pods activos ajenos a DaemonSets; después solicita tamaños mínimo y deseado de cero. Siguen siendo posibles las carreras con controladores que ignoren cordon o sustituyan nodos, por lo que debe mantener las restricciones de ubicación de la migración. Revise las dependencias restantes de DaemonSets y del sistema y exporte primero los artefactos necesarios de los Jobs completados.

```bash
guard_nodegroup
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l "eks.amazonaws.com/nodegroup=$OLD_NODEGROUP" -o json > "$WORK_DIR/old-nodes.json"
jq -e 'all(.items[]; .spec.unschedulable == true)' "$WORK_DIR/old-nodes.json" >/dev/null
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json \
  | jq '{items:[.items[]|{metadata:{name:.metadata.name,namespace:.metadata.namespace,
         ownerReferences:.metadata.ownerReferences},spec:{nodeName:.spec.nodeName},
         status:{phase:.status.phase}}]}' > "$WORK_DIR/pods-before-scale.json"
jq --slurpfile nodes "$WORK_DIR/old-nodes.json" '
  ($nodes[0].items|map(.metadata.name)) as $names |
  [.items[] | select(.spec.nodeName as $n | $names|index($n)) |
   select(.status.phase!="Succeeded" and .status.phase!="Failed") |
   select(any(.metadata.ownerReferences[]?; .kind=="DaemonSet" and .controller==true)|not) |
   {namespace:.metadata.namespace,name:.metadata.name,phase:.status.phase}]
' "$WORK_DIR/pods-before-scale.json" > "$WORK_DIR/old-active-workloads.json"
jq -e 'length == 0' "$WORK_DIR/old-active-workloads.json" >/dev/null

guard_nodegroup
aws eks update-nodegroup-config --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
  --region "$AWS_REGION" --scaling-config minSize=0,desiredSize=0 --output json \
  > "$WORK_DIR/scale-zero-response.json"
update_id=$(jq -er '.update.id' "$WORK_DIR/scale-zero-response.json")
wait_eks_update "$update_id" "$OLD_NODEGROUP"
```

Espere a que desaparezcan los nodos y las instancias antiguos y vuelva a comprobar las aplicaciones. Conserve la definición del node group y su configuración de escalado durante el período de reversión acordado. Un número deseado de cero no garantiza que pueda recuperar capacidad de inmediato.

## 6. Retirar la infraestructura antigua mediante su herramienta de gestión

Tras validar las cargas, los datos y el tráfico y completar el período de estabilización previsto, elimine el grupo mediante su **herramienta de gestión original**: Terraform, CloudFormation, eksctl u otro flujo. Eliminar directamente mediante la API de EKS un grupo gestionado por IaC puede dejar diferencias respecto de su configuración declarada, stacks, roles de IAM u otros recursos.

El ejemplo siguiente solo se aplica a un grupo revisado **gestionado directamente mediante la API**. Exige un número deseado de cero, vuelve a comprobar los nodos y las cargas y detiene la operación si encuentra etiquetas de CloudFormation. Esa comprobación no detecta todas las herramientas externas de IaC; determinar quién gestiona el grupo sigue siendo un requisito previo.

```bash
guard_nodegroup
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l "eks.amazonaws.com/nodegroup=$OLD_NODEGROUP" -o json > "$WORK_DIR/old-nodes.json"
jq -e 'all(.items[]; .spec.unschedulable == true)' "$WORK_DIR/old-nodes.json" >/dev/null
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json \
  | jq '{items:[.items[]|{metadata:{name:.metadata.name,namespace:.metadata.namespace,
         ownerReferences:.metadata.ownerReferences},spec:{nodeName:.spec.nodeName},
         status:{phase:.status.phase}}]}' > "$WORK_DIR/pods-before-scale.json"
jq --slurpfile nodes "$WORK_DIR/old-nodes.json" '
  ($nodes[0].items|map(.metadata.name)) as $names |
  [.items[] | select(.spec.nodeName as $n | $names|index($n)) |
   select(.status.phase!="Succeeded" and .status.phase!="Failed") |
   select(any(.metadata.ownerReferences[]?; .kind=="DaemonSet" and .controller==true)|not) |
   {namespace:.metadata.namespace,name:.metadata.name,phase:.status.phase}]
' "$WORK_DIR/pods-before-scale.json" > "$WORK_DIR/old-active-workloads.json"
jq -e 'length == 0' "$WORK_DIR/old-active-workloads.json" >/dev/null

: "${NODEGROUP_MANAGEMENT:?Use the original IaC owner, or explicitly set direct-api for an API-managed group}"
test "$NODEGROUP_MANAGEMENT" = direct-api
guard_nodegroup
jq -e '.nodegroup.scalingConfig.desiredSize == 0 and
  ((.nodegroup.tags // {} | keys | map(select(startswith("aws:cloudformation:"))) | length) == 0)' \
  "$WORK_DIR/nodegroup-current.json" >/dev/null
aws eks delete-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
  --region "$AWS_REGION" --output json > "$WORK_DIR/delete-nodegroup-response.json"
aws eks wait nodegroup-deleted --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
  --region "$AWS_REGION"
```

El waiter de eliminación debe finalizar correctamente. AccessDenied, las credenciales caducadas y otros errores de consulta no demuestran que el recurso haya desaparecido. Audite por separado los recursos de IAM, red y almacenamiento gestionados de forma independiente, así como la facturación. Que desaparezca el objeto node group de la API no demuestra que hayan terminado todos los costos asociados. El antiguo ejemplo de una o dos semanas de estabilización es una decisión de planificación, no un requisito universal.

## 7. Validación final y optimización

Conserve las pruebas de validación de cada grupo de cargas y realice una auditoría final después de retirar los recursos: disponibilidad esperada de controladores y Pods, ubicación, estado de PVC, DNS, tráfico, IAM, registros, métricas y asignación completa de costos. Mida los costos **durante** la coexistencia: pueden facturarse las dos flotas de cómputo y también los dos balanceadores de carga.

Los antiguos valores de Pending 0–5 / >10 durante cinco minutos, inicio <90s / >120s, disponibilidad >99.9% / <99.5% y respuesta de API <200ms / >500ms son ejemplos de umbrales sin validación. Defina los umbrales a partir de las fuentes reales de métricas, los objetivos de la aplicación y mediciones de referencia; no los trate como métricas predeterminadas de Auto Mode.

## Coexistencia con Karpenter autogestionado

AWS admite migrar mediante coexistencia directa. El requisito de **v1.1** indica la versión mínima que incorporó esa migración; también debe cumplir la matriz de compatibilidad actual de Kubernetes. Por ejemplo, Kubernetes 1.36 requiere al menos Karpenter 1.13. Mantenga el controlador existente en ejecución mientras crea un pool de Auto Mode independiente con un taint y migra los grupos de cargas seleccionados.

No modifique ni elimine los CRD compartidos `nodepools.karpenter.sh` o `nodeclaims.karpenter.sh` durante la migración. Identifique qué controlador gestiona cada recurso mediante su referencia de clase y el pool concreto, no mediante la etiqueta genérica de Karpenter. Una vez retiradas las cargas antiguas, elimine únicamente los NodePools y NodeClaims antiguos correspondientes **mientras su controlador siga disponible para completar los finalizers**. Compruebe que se hayan eliminado sus instancias y dependencias; después desinstale la versión autogestionada y solo sus recursos de IAM y colas. No desinstale primero el controlador ni use la eliminación de un namespace como sustituto de la retirada de recursos.

## Restaurar la capacidad y la ubicación antes de retirar la capacidad de Auto Mode

Esta es una **reversión de la migración de cargas de trabajo/infraestructura**, no una reversión de la versión del plano de control de Kubernetes.

1. Mantenga intacto el pool de Auto. Primero restaure o aprovisione capacidad antigua compatible; si se eliminó el grupo antiguo, un JSON de escalado guardado no puede recrearlo.
2. Revise los valores de escalado registrados según la demanda actual de las cargas de trabajo. Para el grupo que aún exista y conserve la misma identidad, lo siguiente puede restaurar su configuración anterior:

```bash
guard_nodegroup
jq --arg name "$CLUSTER_NAME" --arg group "$OLD_NODEGROUP" '{
  clusterName:$name,nodegroupName:$group,scalingConfig:.nodegroup.scalingConfig
}' "$WORK_DIR/nodegroup-before.json" > "$WORK_DIR/restore-capacity-request.json"
aws eks update-nodegroup-config --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/restore-capacity-request.json" --output json \
  > "$WORK_DIR/restore-capacity-response.json"
update_id=$(jq -er '.update.id' "$WORK_DIR/restore-capacity-response.json")
wait_eks_update "$update_id" "$OLD_NODEGROUP"
```

3. Espere a que haya suficientes nodos antiguos en estado Ready y con agentes operativos de red/DNS/identidad/almacenamiento. Un estado de actualización correcta no demuestra que la capacidad de los Pods esté lista. Revise los UID de los nodos antes de quitar el cordon a cualquier nodo antiguo que siga existiendo.
4. Restaure el plan revisado de ubicación/tráfico/datos de los controladores. Elimine explícitamente los selectores de Auto incompatibles y conserve las afinidades no relacionadas. Verifique la disponibilidad real de las cargas de trabajo y el comportamiento de la aplicación en el grupo antiguo.
5. Solo entonces retire el pool/los recursos exactos de Auto propiedad de la migración a través de su propietario. Eliminar un NodePool puede eliminar en cascada sus nodos; nunca lo elimine como primer paso de la reversión ni seleccione todos los nodos con una etiqueta de Karpenter.

Deshabilitar Auto Mode es opcional y requiere un procedimiento separado. Resuelva primero todas las dependencias de cómputo, almacenamiento y balanceadores que gestione Auto Mode. Si procede deshabilitarlo, incluya las tres opciones en una única solicitud. El fragmento siguiente solo prepara el archivo para revisarlo:

```bash
jq -n --arg name "$CLUSTER_NAME" '{
  name:$name,
  computeConfig:{enabled:false},
  storageConfig:{blockStorage:{enabled:false}},
  kubernetesNetworkConfig:{elasticLoadBalancing:{enabled:false}}
}' > "$WORK_DIR/disable-request.json"
```

Envíelo mediante el flujo de trabajo revisado, con comprobaciones de contexto y seguimiento del ID de actualización si es necesario. Deshabilitar Auto Mode no restaura los selectores de aplicaciones, los datos ni el tráfico, y tampoco revierte los cambios del modo de autenticación.

## Referencias

- [Habilitar Auto Mode en un clúster existente](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)
- [Referencia de migración, EBS y balanceadores de carga](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)
- [Migración de managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-mng.html)
- [Migración de Karpenter autogestionado](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)
- [Escalado de managed node groups y comportamiento de PDB](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Redes de Auto Mode y DNS en nodos mixtos](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [Identidad de NodeClass y entrada de acceso](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Compatibilidad de Karpenter/Kubernetes](https://karpenter.sh/docs/upgrading/compatibility/)
- [Desalojar de forma segura un nodo de Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)
- [Interrupciones de Pod de Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)

< [Anterior: Optimización de cargas de trabajo](./08-workload-optimization.md) | [Tabla de contenido](./README.md) | [Volver a los temas de EKS](../README.md) >
