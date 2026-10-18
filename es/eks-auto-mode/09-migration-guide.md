# Migración de Managed Node Groups a Auto Mode

> **Versiones compatibles**: EKS Auto Mode GA; ejemplos revisados para EKS 1.36
> **Última actualización**: September 12, 2026

La migración requiere comprobar las aplicaciones, el almacenamiento y la propiedad de los controladores **antes** de retirar la capacidad antigua. Los ejemplos siguientes son operaciones por etapas con esquemas y fixtures de CLI comprobados localmente; no constituyen un procedimiento de producción verificado sin tiempo de inactividad. Durante esta auditoría no se realizaron modificaciones en la nube ni en el clúster.

![Vista general de la migración existente en siete etapas. Valide cada grupo de cargas de trabajo antes de escalar o eliminar la capacidad antigua; la fase final de validación es una auditoría posterior a la limpieza, no la primera comprobación del estado.](../.gitbook/assets/en-eks-auto-mode-09-migration-guide-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-auto-mode-09-migration-guide-0.html)

El paso final de validación del diagrama no autoriza el desalojo, el escalado a cero ni la eliminación sin comprobaciones previas del estado y un plan de reversión.

## 1. Inventariar y vincular el contexto operativo

Use una combinación de EKS/complementos compatible actualmente. El antiguo mínimo de 1.29 era un límite histórico de disponibilidad de la función, no una recomendación sobre las versiones compatibles actuales. Confirme que sean compatibles VPC CNI, kube-proxy, EBS CSI, el controlador de snapshots y Pod Identity Agent cuando estén instalados; use los mínimos oficiales de migración **y** la lista de compatibilidad para su versión de Kubernetes.

Registre la propiedad de los controladores, la ubicación de las cargas de trabajo, los agentes del sistema, los volúmenes/AZ, las clases de balanceadores de carga, IAM, los procedimientos de recuperación y los costos. La protección siguiente comprueba la cuenta, el ARN del clúster/la hora de creación/el endpoint de la API y el ARN del node group/la hora de creación. Son comprobaciones de identidad puntuales, no un bloqueo atómico frente a controladores concurrentes. Un endpoint deliberadamente intermediado requiere una alternativa revisada; no se debe omitir silenciosamente una discrepancia.

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

Los archivos privados contienen metadatos operativos; consérvelos para la recuperación. Los errores de consulta siguen siendo errores. `kubectl top` requiere una API de métricas operativa, y una instantánea actual de CPU no sustituye al historial de las cargas de trabajo.

| Configuración existente | Consideración para la migración |
|------------------------|---------------------------------|
| AMI/arranque/datos de usuario personalizados | Auto Mode usa Bottlerocket administrado, no AL2023/AMI/userData arbitrarios |
| Permisos de IAM de los nodos | Prepare el rol/perfil del nodo/la entrada de acceso; migre los permisos de las cargas de trabajo a IRSA/Pod Identity revisados en lugar de recurrir al rol del nodo/IMDS |
| Rol de IAM del clúster | Añada al rol existente los permisos y la relación de confianza necesarios para Auto Mode; habilitarlo mediante CLI no crea automáticamente todos los roles |
| Selectores/afinidad/taints | Incluya Deployments, StatefulSets, DaemonSets, Jobs y CronJobs; elimine deliberadamente las reglas de ubicación incompatibles |
| CNI alternativo/configuración de red | Compruebe la compatibilidad documentada antes de habilitarlo; un NodeClass no corrige una configuración de red no compatible |
| Propiedad del escalado/IaC | Coordine Cluster Autoscaler, GitOps y al propietario de IaC original para que no reviertan los cambios de migración |

### Datos, balanceadores de carga y DNS en nodos mixtos

Los controladores/controladores utilizan interfaces diferentes:

| Recurso | Autogestionado | Auto Mode |
|----------|--------------|-----------|
| Aprovisionador de StorageClass de EBS | `ebs.csi.aws.com` | `ebs.csi.eks.amazonaws.com` |
| loadBalancerClass del Service NLB | `service.k8s.aws/nlb` | `eks.amazonaws.com/nlb` |
| Controlador de IngressClass ALB | `ingress.k8s.aws/alb` | `eks.amazonaws.com/alb` |
| apiVersion de TargetGroupBinding | `elbv2.k8s.aws/v1beta1` | `eks.amazonaws.com/v1` |
| Clase de cómputo | `karpenter.k8s.aws/v1 EC2NodeClass` | `eks.amazonaws.com/v1 NodeClass` |

Un PVC existente no cambia de controlador al editar el nombre de su StorageClass, y el controlador administrado no adopta automáticamente un balanceador de carga existente. Para EBS, utilice un plan probado de restauración desde backup/snapshot o el flujo de trabajo actual documentado por AWS de **detención de las cargas de trabajo, Retain y recreación estática de PV/PVC**. Este último reutiliza un volumen EBS, pero recrea los objetos de vinculación de Kubernetes; no cambia el controlador en el mismo lugar. Verifique la restauración de backups, la propiedad del volumen/AZ/KMS, la política de recuperación, los finalizers, las vinculaciones y la coherencia de la aplicación. Aquí no se proporciona ningún script destructivo de migración de volúmenes.

Mantenga el AWS Load Balancer Controller autogestionado mientras sea propietario de recursos. Cree/pruebe el nuevo balanceador de carga administrado y cambie el tráfico mediante un plan DNS blue/green revisado antes de retirar el antiguo. Revise por separado la inmutabilidad de las clases, las anotaciones y la propiedad de TargetGroupBinding; cambiar un grupo de API no es una operación de adopción segura.

Los nodos de Auto Mode tienen DNS local al nodo. **Conserve el Deployment de CoreDNS mientras haya nodos que no sean de Auto Mode y lo necesiten.** Mantenga los agentes necesarios de CNI/proxy/almacenamiento/identidad para los tipos de nodo restantes y limite su ubicación; que los componentes de Auto Mode estén administrados no justifica eliminar antes de tiempo dependencias del clúster mixto.

## 2. Habilitar Auto Mode sin un pool predeterminado sin restricciones

Complete primero la preparación de IAM/acceso en [Introducción](./01-getting-started.md). El rol existente del clúster necesita las políticas documentadas de Compute, **BlockStoragePolicyV2**, LoadBalancing, Networking y Cluster, además de la relación de confianza requerida para `sts:TagSession`. El ejemplo presupone autenticación API o API_AND_CONFIG_MAP, así como un rol/perfil de nodo personalizado preparado con una entrada de acceso EC2.

Esta ruta por etapas empieza **sin pools integrados**. Por tanto, crea su propio NodeClass en el paso siguiente; no suponga que existe `default`. Habilitar un pool de propósito general sin restricciones podría programar cargas de trabajo pendientes existentes antes del cambio previsto. El ejemplo se niega a operar en un clúster que ya ejecuta Auto Mode, en lugar de reemplazar su lista de pools existente.

Use el ID de actualización específico para esperar a que finalice. Que el clúster esté `ACTIVE` por sí solo no demuestra que esta actualización de configuración haya tenido éxito.

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

Compute, block storage y el balanceo de carga administrado deben habilitarse o deshabilitarse conjuntamente. La validación nativa de la solicitud no demuestra que IAM/la admisión del servicio vayan a aceptarla; deténgase si se produce un error y conserve la evidencia de la actualización. No vuelva a ejecutarla a ciegas tras una respuesta incierta. Los cambios del modo de autenticación tienen restricciones independientes de migración/reversión.

## 3. Crear un pool selectivo y probar ambos lados

Reemplace los marcadores de posición del perfil/subred/grupo de seguridad del NodeClass por recursos existentes revisados. El rol del perfil necesita la entrada de acceso correcta para el nodo; estos manifiestos no crean IAM, VPC ni credenciales de aplicación.

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

Reemplace `REPLACE_WITH_OLD_NODEGROUP` antes de usar el canary heredado. Los ejemplos completos de nginx usan la imagen revisada sin privilegios y el contexto de seguridad del capítulo de operaciones. Comprueban la ubicación/disponibilidad básica, no el estado, la identidad ni la ruta de tráfico de su aplicación.

El canary de Auto selecciona tanto el pool exacto como `eks.amazonaws.com/compute-type=auto`. La existencia de `karpenter.sh/nodepool` por sí sola también coincide con nodos de Karpenter autogestionado. Una toleration permite la ubicación; por sí sola no selecciona un pool.

| Configuración de MNG | Correspondencia en Auto Mode |
|-------------|-------------------|
| Tipos de instancia/tipo de capacidad | Requisitos exactos de instancia o categorías deliberadamente más amplias; requisito de tipo de capacidad |
| Etiquetas/taints | `spec.template.metadata.labels` / `spec.template.spec.taints` |
| Recuento mínimo/deseado/máximo de nodos | No equivale a los límites de CPU/memoria `spec.limits`; considere la semántica de pools estáticos por separado si se requieren nodos deseados fijos |
| Subred/grupos de seguridad | Selectores de NodeClass personalizados y reglas revisadas |
| AMI/arranque | Auto Mode no ofrece una correspondencia arbitraria de familia de AMI/userData |

## 4. Migrar por grupos y detenerse ante un fallo

Empiece con cargas de trabajo representativas de bajo riesgo; después, migre las de staging/no críticas de producción y, una vez aprobadas sus dependencias, las críticas. Cambie la configuración deseada del **controlador propietario/GitOps**, no solo un Pod en ejecución.

Revise toda la política de ubicación: añadir un selector de Auto y conservar al mismo tiempo un selector del antiguo node group puede hacer que la conjunción impida la programación. No elimine afinidades de Pod, ubicaciones de seguridad ni tolerations no relacionadas mediante `affinity: null`. StatefulSets, Jobs activos y cargas de trabajo con volúmenes locales necesitan su propio procedimiento con conocimiento de los datos.

Para un Deployment con réplicas distintas de cero, esto comprueba el rollout y la disponibilidad observada de las réplicas:

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

No hay ningún ciclo de cordon/desalojo masivo, espera fija para comprobar el estado ni opción de «continuar tras un fallo». El desalojo predeterminado rechaza los Pods no administrados/datos de emptyDir locales, salvo que se gestionen deliberadamente; no añada `--force`, `--disable-eviction` ni `--delete-emptydir-data` para hacer desaparecer un fallo. Un desalojo fallido/interrumpido puede dejar el nodo con cordon: inspecciónelo y restaure la programación solo si así lo indica el plan de recuperación. Valide las aplicaciones afectadas antes de elegir otro nodo.

## 5. Reducir la capacidad solo después de retirar las cargas de trabajo antiguas

**Cambiar el tamaño deseado de un MNG no respeta los PDB**: EKS utiliza el escalado de ASG. Esto es distinto del desalojo que se realiza normalmente al actualizar la versión de un managed node group. Reducir a la mitad el tamaño deseado y esperar cinco minutos no es una estabilización segura.

Coordine con el propietario original del escalado/IaC e impida la programación de nuevas aplicaciones en los nodos antiguos. El ejemplo de la API comprueba que todos los nodos antiguos observados tengan cordon y no contengan Pods activos que no sean de DaemonSet; después solicita que el tamaño mínimo/deseado sea cero. No elimina las condiciones de carrera con controladores que ignoren los cordons o reemplacen nodos; mantenga activas las medidas de ubicación de la migración. Revise todas las dependencias restantes de DaemonSet/sistema y exporte antes los artefactos necesarios de los Jobs completados.

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

Espere a que desaparezcan los nodos/instancias antiguos reales y vuelva a comprobar el estado de las aplicaciones. Conserve la definición del node group y la configuración de escalado registrada durante el período de reversión acordado. No se garantiza que la capacidad deseada cero pueda recuperarse de inmediato.

## 6. Retirar la infraestructura antigua a través de su propietario

Después de validar correctamente las cargas de trabajo, los datos y el tráfico, y tras un período deliberado de estabilización, elimine el grupo a través de su **propietario original**: Terraform, CloudFormation, eksctl u otro flujo de gestión. Eliminar mediante la API directa de EKS un grupo propiedad de IaC puede dejar drift, stacks, roles de IAM u otros recursos.

Lo siguiente se aplica únicamente a un grupo **administrado directamente mediante la API** y previamente revisado. Requiere un tamaño deseado cero, vuelve a comprobar el estado de los nodos/cargas de trabajo y rechaza las etiquetas visibles de propiedad de CloudFormation. Esa comprobación no puede detectar todos los propietarios externos de IaC; determinar la propiedad sigue siendo un requisito previo.

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

El waiter de eliminación debe completarse correctamente. AccessDenied, credenciales caducadas u otros errores de consulta no significan que el recurso esté ausente. Audite por separado los recursos de IAM/red/almacenamiento con propiedad independiente y la facturación; la eliminación del objeto de la API del node group no demuestra que hayan finalizado todos los costos asociados. El período de estabilización anterior de una a dos semanas es una opción de planificación, no un requisito universal.

## 7. Validación final y optimización

Conserve las evidencias de validación de cada grupo y realice una auditoría final posterior a la limpieza: estado esperado de controladores/Pods, ubicación, estado de PVC, DNS, tráfico de la aplicación, IAM, registros/métricas y asignación completa de costos. Haga un seguimiento de los costos **durante** la coexistencia, ya que pueden facturarse tanto los dos grupos de cómputo como ambos balanceadores de carga.

Las antiguas cifras de Pending 0–5 / >10 durante cinco minutos, inicio <90s / >120s, disponibilidad >99.9% / <99.5% y respuesta de API <200ms / >500ms son umbrales de ejemplo no verificados. Use publicadores reales, objetivos de la aplicación y valores de referencia medidos, no métricas predeterminadas supuestas de Auto Mode.

## Coexistencia con Karpenter autogestionado

AWS admite una migración con coexistencia directa. El requisito previo de **v1.1** es un límite mínimo de versión para la migración; cumpla también la matriz de compatibilidad actual de Kubernetes (por ejemplo, Kubernetes 1.36 requiere al menos Karpenter 1.13). Mantenga en ejecución el controlador existente mientras crea un pool de Auto Mode independiente con taint y migra grupos de cargas de trabajo seleccionados.

No modifique ni elimine los CRD compartidos `nodepools.karpenter.sh` o `nodeclaims.karpenter.sh` durante la migración. Registre la propiedad mediante la referencia de clase y el pool exacto, no mediante la etiqueta genérica de Karpenter. Cuando ya no queden cargas de trabajo antiguas, retire solo los NodePools/NodeClaims antiguos de su propiedad **mientras su controlador pueda completar la finalización**. Confirme que se hayan limpiado sus instancias/dependencias y, después, desinstale el release autogestionado y solo los recursos de IAM/cola que le pertenezcan. No lo desinstale primero ni elimine un namespace como sustituto de la limpieza de recursos.

## Revertir la capacidad y la ubicación antes de retirar la capacidad de Auto

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

Deshabilitar Auto Mode es opcional y es un proceso independiente. Primero resuelva todas las dependencias de cómputo, almacenamiento y balanceadores de carga propiedad de Auto. Si corresponde realizar ese cambio, las tres marcas deben ir en una sola solicitud; este fragmento solo prepara el archivo de solicitud para su revisión:

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
