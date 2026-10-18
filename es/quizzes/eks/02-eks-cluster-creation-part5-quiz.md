# Cuestionario sobre creación de clústeres EKS - Parte 5

> **Última actualización**: 11 de septiembre de 2026

Este cuestionario cubre operaciones de EKS, logging, aplicación de políticas y aislamiento de tenants. Las preguntas finales conectan estos temas con la validación de acceso y la retirada de recursos del capítulo conceptual. Los comandos requieren clúster/Región/kubeconfig, IAM y requisitos previos de controladores revisados; en esta revisión no se desplegó en la nube ni se hicieron pruebas en producción.

## Preguntas de opción múltiple

1. ¿Qué enfoque puede combinar una base On-Demand que no sea Spot con capacidad interrumpible?
   * A) Todos los nodos On-Demand
   * B) Grupos separados On-Demand y Spot, con colocación de cargas de trabajo
   * C) Seleccionar Reserved como `capacityType` de todos los grupos
   * D) Todas las cargas de trabajo deben usar Fargate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Grupos separados On-Demand y Spot, con colocación de cargas de trabajo**

Una combinación puede servir para una base sensible a interrupciones más capacidad tolerante a ellas. Usa grupos administrados separados para On-Demand y Spot, con colocación explícita de cargas de trabajo. No es una estrategia universalmente «más eficaz» para reducir costes: la utilización, los requisitos de fiabilidad, los precios de Región/tipo de instancia y la carga operativa determinan el resultado.

AWS anuncia ahorros de Spot de hasta el 90 % frente a On-Demand; no garantiza ese descuento para cada grupo de capacidad ni que esta guía haya medido ahorros. On-Demand evita la recuperación de capacidad Spot, pero sigue sujeto a mantenimiento/fallos. Para Spot importan los checkpoints, los reintentos y la capacidad de reserva.

El dimensionamiento adecuado, Cluster Autoscaler/Karpenter, imágenes Graviton compatibles y los descuentos por compromiso apropiados son otras opciones. Reserved Instances/Savings Plans son acuerdos de facturación, no otro ajuste de capacidad ordinario de un grupo administrado. Fargate puede encajar en algunos patrones de demanda; compara la capacidad aprovisionada y el coste total en vez de suponer que siempre gana un tipo de cómputo.

</details>

2. ¿Por qué distribuir cargas de trabajo adecuadas entre varias AZ?
   * A) Para reducir siempre la latencia
   * B) Para garantizar un throughput superior
   * C) Para reducir la exposición al fallo de una sola AZ
   * D) Para replicar automáticamente entre Regiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Para reducir la exposición al fallo de una sola AZ**

Varias AZ reducen la dependencia de un único dominio de fallo. El plano de control administrado de EKS se distribuye entre AZ, pero la disponibilidad de la aplicación también requiere réplicas distribuidas correctamente, endpoints saludables, capacidad de reserva y almacenamiento/red compatibles.

Los controladores de Kubernetes pueden crear pods de reemplazo; los pods independientes no se recrean automáticamente. La falta de capacidad, una afinidad estricta o volúmenes EBS zonales pueden impedir la recuperación. Enumerar varias subredes no garantiza que todas las réplicas de la aplicación se distribuyan entre ellas. Revisa Topology Spread/anti-afinidad y la colocación real.

Los PDB regulan las expulsiones voluntarias, no las interrupciones de AZ. Las actualizaciones rolling y el failover entre AZ requieren validación a nivel de aplicación y un diseño de recuperación de datos. Varias AZ no replican automáticamente entre Regiones y pueden añadir costes de transferencia entre AZ.

</details>

3. ¿Cuál es el CNI predeterminado para los nodos EC2 convencionales de EKS?
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Amazon VPC CNI**

Amazon VPC CNI es el CNI predeterminado para los nodos EC2 convencionales de EKS. Asigna direcciones VPC mediante modos compatibles de IP secundaria o prefijos. Auto Mode proporciona sus propias capacidades de red administradas; Hybrid Nodes usa un CNI alternativo compatible. No instales un sustituto sin configurar encima de un CNI existente.

Los grupos de seguridad para pods requieren su propia configuración compatible de instancia/CNI y selección de políticas; no hay automáticamente un grupo único para cada pod. NetworkPolicy nativa también requiere cómputo compatible y habilitación explícita.

El enrutamiento nativo de VPC evita una superposición convencional en este diseño, pero no garantiza un rendimiento medido. Valida el ancho de banda, el enrutamiento, la capacidad de IP, el comportamiento de las políticas y los requisitos de la aplicación. Integraciones como Load Balancer Controller también necesitan su propia instalación y permisos.

</details>

4. ¿Qué mecanismo de identidad de carga de trabajo usa el emisor OIDC de EKS y un token de ServiceAccount proyectado?
   * A) IAM Roles for Service Accounts (IRSA)
   * B) Una política de acceso de EKS
   * C) Solo un RoleBinding de Kubernetes
   * D) Una etiqueta de nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) IAM Roles for Service Accounts (IRSA)**

**IAM Roles for Service Accounts (IRSA)** usa un token de ServiceAccount proyectado, el emisor OIDC del clúster y una relación de confianza IAM para obtener credenciales temporales de STS. Limita la confianza a la audiencia prevista (`sts.amazonaws.com`) y al `subject` exacto de namespace/ServiceAccount; después concede solo las acciones/recursos AWS necesarios.

Usa la ServiceAccount prevista en el pod y una cadena de credenciales SDK compatible. Verifica la identidad del rol asumido; el acceso satisfactorio a AWS podría venir de otras credenciales. IRSA no impide por sí sola el acceso a credenciales IMDS del nodo.

EKS Pod Identity es otro mecanismo para asociar roles a ServiceAccounts, con un flujo distinto de agente/asociación. Es compatible con EC2/Auto Mode aptos y Hybrid Nodes configurados específicamente; Fargate necesita otro mecanismo compatible, como IRSA. Ninguno de los dos es una entrada de acceso de EKS: los permisos AWS de la carga de trabajo y el acceso a la API de Kubernetes son distintos.

</details>

5. ¿Qué controlador escala los ASG de grupos de nodos administrados EKS existentes según la demanda de programación de Kubernetes?
   * A) Horizontal Pod Autoscaler
   * B) Vertical Pod Autoscaler
   * C) Cluster Autoscaler
   * D) ResourceQuota

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cluster Autoscaler**

Cluster Autoscaler ajusta grupos de nodos/ASG existentes que descubre. Requiere instalación compatible, RBAC de Kubernetes, permisos AWS dedicados y etiquetas de descubrimiento correctas; no se instala al configurar los valores mínimo/máximo.

Para escalar hacia arriba considera las solicitudes/restricciones de programación; para reducir escala, las condiciones de reubicación/interrupción. No todos los pods Pending se pueden programar añadiendo nodos y la lógica de utilización para scale-down no equivale al umbral de uso de CPU de HPA.

HPA ajusta réplicas y VPA recomienda/cambia las solicitudes de recursos de los pods; ambos pueden cambiar indirectamente la demanda de nodos. Karpenter es otro aprovisionador de capacidad que usa NodePools/NodeClaims, no un sustituto universalmente más rápido ni un controlador de ASG. Valida los bucles de control y las restricciones de las cargas.

</details>

## Preguntas de respuesta corta

6. ¿Cómo se habilita y verifica el logging del plano de control de EKS en CloudWatch?

<details>
<summary>Respuesta y explicación</summary>

Habilita los tipos de log del plano de control necesarios: `api`, `audit`, `authenticator`, `controllerManager` y `scheduler`. En la consola de EKS usa **Observabilidad → Registro del plano de control → Administrar registro**, no la antigua instrucción de la pestaña Logging.

Este ejemplo habilita los cinco; elige el conjunto revisado para tu entorno:

```bash
set -euo pipefail
LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

Consulta el ID de actualización devuelto hasta que el estado sea `Successful`; resuelve los fallos antes de hacer otro cambio. La alternativa con eksctl requiere `--approve` para aplicar el cambio de logging:

```bash
# Alternative to the AWS CLI update, not a second concurrent update.
eksctl utils update-cluster-logging --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --enable-types=api,audit,authenticator,controllerManager,scheduler --approve
```

Los logs se envían a `/aws/eks/<cluster-name>/cluster` en la Región del clúster. Los streams rotan y puede haber varios por tipo; la entrega es de mejor esfuerzo y suele tardar unos minutos. Verifica la configuración habilitada, las marcas de tiempo actuales de los streams y los eventos pertinentes reales. La existencia de un log group no lo demuestra. Configura la retención y los controles de acceso, contempla los costes de ingesta/almacenamiento y evita publicar eventos de auditoría sensibles. Los logs de nodos y aplicaciones requieren colectores distintos.

</details>

7. ¿Cómo se recopilan en CloudWatch los logs de kubelet de nodos Linux convencionales de EKS?

<details>
<summary>Respuesta y explicación</summary>

Los logs de kubelet son logs de nodo, distintos del logging del plano de control de EKS. En la ruta Linux AL2023 optimizada para EKS, inspecciona el journal de systemd de `kubelet.service`; no supongas que existe `/var/log/kubelet.log` o `/var/log/kube-proxy.log`. kube-proxy suele registrar logs como contenedor. Los archivos/stdout de VPC CNI dependen de su configuración.

El **add-on de Amazon CloudWatch Observability para EKS administrado** instala el agente/operator y Fluent Bit. Un manifiesto quickstart sin procesar no es ese add-on administrado. No sobrescribas ServiceAccounts existentes ni reemplaces todo un ConfigMap de Fluent Bit sin revisar quién lo administra.

Este ejemplo es para un **laboratorio Linux en EC2**, con Pod Identity Agent listo y un rol existente aprobado cuya confianza incluye la ServiceAccount `amazon-cloudwatch/cloudwatch-agent` de este clúster. Revisa sus permisos CloudWatch; `CloudWatchAgentServerPolicy` es la base administrada por AWS, no la afirmación de que todos sus permisos sean mínimos para el ámbito de logs. Fluent Bit del chart actual usa esa misma ServiceAccount; esta configuración no requiere otra ServiceAccount IAM `fluent-bit`.

Primero elige un build compatible del add-on e inspecciona su esquema. La versión del chart y la cadena del build del add-on EKS son distintas:

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}"
CLUSTER_VERSION=$(aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.version --output text)
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --kubernetes-version "$CLUSTER_VERSION"
: "${CLOUDWATCH_ADDON_VERSION:?Choose a reviewed compatible build with the configuration fields below}"
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --query configurationSchema --output text > cloudwatch-addon-schema.json
```

Guarda lo siguiente como `cloudwatch-addon-values.yaml`. Se renderizó con el chart oficial 6.6.0. La anulación completa Linux de `dataplane-log.conf` recopila solo registros del journal de kubelet; los archivos vacíos de aplicación/host deshabilitan esas rutas de logs predeterminadas. El resto de las secciones globales de Fluent Bit conserva sus valores. El add-on también recopila métricas de Container Insights; no es una instalación de agente solo para logs. El auto-monitoring de Application Signals está deshabilitado explícitamente para no instrumentar automáticamente servicios en este ejercicio.

```yaml
manager:
  applicationSignals:
    autoMonitor:
      monitorAllServices: false
containerLogs:
  fluentBit:
    config:
      extraFiles:
        application-log.conf: ''
        host-log.conf: ''
        dataplane-log.conf: |
          [INPUT]
            Name                systemd
            Tag                 dataplane.kubelet
            Systemd_Filter      _SYSTEMD_UNIT=kubelet.service
            DB                  /var/fluent-bit/state/kubelet.db
            Path                /var/log/journal
            Read_From_Tail      On

          [FILTER]
            Name                modify
            Match               dataplane.kubelet
            Rename              _HOSTNAME hostname
            Rename              MESSAGE message

          [OUTPUT]
            Name                cloudwatch_logs
            Match               dataplane.kubelet
            region              ${AWS_REGION}
            log_group_name      /aws/containerinsights/${CLUSTER_NAME}/dataplane
            log_stream_prefix   ${HOST_NAME}-
            auto_create_group   true
```

Confirma la ruta del journal montado y el directorio de estado con permisos de escritura en los nodos previstos. Estas anulaciones Linux no configuran la recopilación en Windows; los entornos mixtos, Hybrid y Auto Mode requieren las rutas documentadas para ellos. Comprueba el esquema del add-on elegido y conserva las configuraciones existentes no relacionadas antes de adaptar esto a una actualización.

```bash
# New installation only, after the schema/role/configuration review.
: "${CLOUDWATCH_ROLE_ARN:?Existing approved Pod Identity role}"
CW_ASSOCIATIONS=$(jq -cn --arg role "$CLOUDWATCH_ROLE_ARN" \
  '[{serviceAccount:"cloudwatch-agent",roleArn:$role}]')
aws eks create-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --pod-identity-associations "$CW_ASSOCIATIONS" \
  --configuration-values file://cloudwatch-addon-values.yaml --resolve-conflicts NONE
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --query 'addon.{status:status,health:health,version:addonVersion}'
```

Espera a que termine la operación específica del add-on e inspecciona errores de estado, pods del agente/Fluent Bit y eventos recientes bajo `/aws/containerinsights/<cluster>/dataplane`. Un render correcto de Helm o que exista el log group no demuestra la recopilación. Revisa IAM, endpoints de red, retención y costes de ingesta/métricas. Las instalaciones de observabilidad existentes requieren una migración planificada; no ejecutes un segundo colector que duplique logs ni habilites silenciosamente reinicios de aplicaciones. Aquí no se instaló ningún agente activo, no se recopiló el journal ni se verificó la entrega a CloudWatch.

</details>

8. ¿Qué sustituyó a PSP y cómo deben evaluarse los controles de admisión equivalentes?

<details>
<summary>Respuesta y explicación</summary>

PodSecurityPolicy quedó obsoleto en Kubernetes 1.21 y se eliminó en 1.25. Las versiones de EKS compatibles actualmente no proporcionan esa API. Pod Security Admission (PSA) aplica los perfiles de Pod Security Standards (PSS), pero no sustituye campo por campo todas las funciones de PSP.

Para un namespace de laboratorio EKS 1.36 nuevo, fija la versión del perfil para que una futura actualización del clúster no cambie silenciosamente la versión de política elegida:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: psa-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```

En namespaces de producción existentes, evalúa los resultados de audit/warn y la compatibilidad de las aplicaciones antes de aplicar Restricted. PSA valida, pero no proporciona el comportamiento antiguo de mutación/valores predeterminados de PSP. Asocia los controles antiguos de namespaces del host, capacidades, volúmenes, ID y seccomp a los reemplazos adecuados.

**Alternativa con Kyverno:** lo siguiente usa la `ValidatingPolicy` CEL actual `policies.kyverno.io/v1`, disponible en la ruta revisada Kyverno 1.19.1/chart 3.9.1. `ClusterPolicy` heredada está obsoleta en 1.19; no se afirma que ya se haya eliminado. Instala por separado el controlador/CRD compatible y usa un namespace revisado `policy-engine-lab`. Se comprueban los contenedores normales, init y efímeros:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```

**Alternativa con Gatekeeper:** un `ConstraintTemplate` por sí solo no aplica una regla. La plantilla y el `Constraint` de abajo son un ejemplo revisado para Gatekeeper 3.23.1; `templates.gatekeeper.sh/v1` y la API `Constraint` generada tienen versiones distintas:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8snoprivilegedlab

      containers[c] {
        c := input.review.object.spec.containers[_]
      }
      containers[c] {
        c := input.review.object.spec.initContainers[_]
      }
      containers[c] {
        c := input.review.object.spec.ephemeralContainers[_]
      }
      violation[{"msg": msg}] {
        c := containers[_]
        c.securityContext.privileged == true
        msg := sprintf("Privileged container is not allowed: %v", [c.name])
      }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```

Estos dos ejemplos de motores son alternativas y demuestran un control, no la paridad completa con PSP ni una política completa de hardening para producción. Prueba los casos permitidos/sin `securityContext` y los contenedores privilegiados normales/init/efímeros. Ten en cuenta la política de fallos de admisión, la disponibilidad del webhook y las exenciones. GuardDuty, Security Hub e Inspector complementan la detección de amenazas, la postura y la vulnerabilidad de recursos compatibles; no sustituyen el rechazo de pods en la admisión.

</details>

## Preguntas prácticas

9. Configura grupos On-Demand y Spot separados, con controles de colocación y requisitos previos de autoescalado.

<details>
<summary>Respuesta y explicación</summary>

Usa grupos administrados **separados**: On-Demand con 2–5 nodos para cargas críticas y Spot con 2–10 para cargas tolerantes a interrupciones. Son ejemplos, no ahorros medidos ni garantías de capacidad. Elige un método de creación y nombres de grupo no utilizados; verifica primero el egress/endpoints de subredes privadas, IAM y compatibilidad de AMI/imágenes.

La configuración de eksctl usa los campos compatibles `managedNodeGroups` y `spot`. No concedas a todos los nodos los permisos del controlador de autoescalado:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: critical-workloads
  amiFamily: AmazonLinux2023
  instanceType: m5.xlarge
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  spot: false
  labels:
    workload-type: critical
    node-lifecycle: on-demand
- name: general-workloads
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large]
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    workload-type: general
    node-lifecycle: spot
  taints:
  - key: spot
    value: "true"
    effect: PreferNoSchedule
```

Guarda y revisa el archivo; luego usa `eksctl create nodegroup -f nodegroups.yaml` para el clúster existente. A continuación se muestra la alternativa con AWS CLI. Los efectos de taint en la API EKS usan nombres en mayúscula y valores estructurados, a diferencia de CamelCase en Kubernetes/eksctl:

```bash
set -euo pipefail
# Alternative to eksctl; use unused group names and approved role/subnet IDs.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${CRITICAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=5,desiredSize=2 \
  --instance-types m5.xlarge --capacity-type ON_DEMAND --ami-type AL2023_x86_64_STANDARD \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --node-role "${NODE_ROLE_ARN:?}" \
  --labels workload-type=critical,node-lifecycle=on-demand
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$CRITICAL_NODEGROUP_NAME"

aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "${GENERAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types m5.large m5a.large m5d.large m5ad.large --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --subnets "$PRIVATE_SUBNET_A" "$PRIVATE_SUBNET_B" \
  --node-role "$NODE_ROLE_ARN" --labels workload-type=general,node-lifecycle=spot \
  --taints '[{"key":"spot","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GENERAL_NODEGROUP_NAME"
```

En un namespace nuevo y revisado `placement-lab`, estos contenedores inactivos solo demuestran la programación. Sustitúyelos por imágenes reales revisadas de la aplicación antes de afirmar que se ha probado su comportamiento. El selector crítico requiere etiquetas On-Demand. La carga general prefiere Spot, pero puede caer en otro lugar; una toleration permite la colocación, no la fuerza, y `PreferNoSchedule` es un control flexible.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
  namespace: placement-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: critical-app
  template:
    metadata:
      labels:
        app: critical-app
    spec:
      automountServiceAccountToken: false
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: workload-type
                operator: In
                values:
                - critical
              - key: node-lifecycle
                operator: In
                values:
                - on-demand
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: general-app
  namespace: placement-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: general-app
  template:
    metadata:
      labels:
        app: general-app
    spec:
      automountServiceAccountToken: false
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 1
            preference:
              matchExpressions:
              - key: node-lifecycle
                operator: In
                values:
                - spot
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      tolerations:
      - key: spot
        operator: Equal
        value: 'true'
        effect: PreferNoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-app-pdb
  namespace: placement-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: critical-app
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: general-app-hpa
  namespace: placement-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: general-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

Los valores de solicitudes/límites conservados son ilustrativos. La protección PDB se aplica a expulsiones voluntarias y no detiene la recuperación Spot ni los fallos de AZ. HPA requiere Metrics Server y una relación significativa entre carga/métrica; la demostración inactiva no es un benchmark de escalado.

Prepara una ServiceAccount/rol dedicado para Cluster Autoscaler, con permisos AWS limitados por etiquetas y etiquetas de descubrimiento ASG reales. Las etiquetas del grupo de nodos no demuestran que estén las etiquetas del ASG. Para EKS 1.36, renderiza el par revisado de chart/imagen e inspecciónalo antes de instalar:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```

Mantén las protecciones de almacenamiento local/pods de sistema salvo que otra revisión justifique cambiarlas. Las formas de CPU/memoria/GPU comparables importan dentro de grupos gestionados por CA con tipos mixtos. Los grupos de nodos administrados ya gestionan el rebalanceo de Spot y el drain; no añadas a ciegas otro Node Termination Handler. La capacidad autogestionada necesita su propia gestión del ciclo de vida revisada. Valida la recuperación ante interrupciones, la colocación, la persistencia de datos y el coste total bajo condiciones representativas de carga.

</details>

## Preguntas avanzadas

10. Compara los enfoques de aislamiento de tenants en EKS y sus límites reales.

<details>
<summary>Respuesta y explicación</summary>

Elige el límite de tenant según los requisitos reales de confianza, datos, disponibilidad y gobernanza. Los siguientes son **diseños alternativos**, no instrucciones para combinar todos los ejemplos en un único namespace compartido.

**Clústeres/cuentas separados:** los recursos dedicados de API/plano de control reducen el acoplamiento y permiten elegir ciclos de vida independientes, con un coste operativo mayor. No aíslan automáticamente IAM, VPC, almacenamiento, cuotas ni servicios externos compartidos, ni garantizan que un tenant nunca pueda afectar a otro. Usa la guía revisada de creación de clústeres en vez de ejecutar dos comandos `eksctl create cluster` sin calificar.

**Namespaces con controles aplicados:** los namespaces separan nombres, no toda la seguridad o capacidad. Un administrador de plataforma crea los namespaces nuevos de tenants y administra sus límites de etiquetas de política, cuotas y RBAC:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-b
  labels:
    tenant: b
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```

El siguiente ejemplo completo para tenant A incluye el Role que faltaba en el antiguo RoleBinding, permisos explícitos de carga, tráfico dentro del namespace más DNS acotado, ResourceQuota y LimitRange. Configura el grupo autenticado `tenant-a-users` y, por separado, recursos equivalentes revisados para tenant B:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```

La política requiere un motor de aplicación compatible y supone las etiquetas ordinarias de CoreDNS; adáptala para las rutas NodeLocal DNSCache. Las cuotas son límites de admisión, no nodos reservados ni ancho de banda garantizado. Las cargas pueden usar ServiceAccounts y Secrets locales al namespace, así que limita su creación mediante admisión y mantén las credenciales de plataforma fuera de los namespaces de tenants. Los recursos de kernel/plano de control compartidos aún requieren revisión del modelo de amenazas.

**Clústeres virtuales:** una API/plano de control virtual puede separar la configuración de ámbito de clúster, mientras las cargas en nodos compartidos siguen compartiendo el kernel/CNI/CSI del host. La configuración revisada de vCluster 0.36.1 usa los campos actuales `sync.fromHost.nodes` y deja deshabilitada la sincronización de nodos del host. No es obligatorio crear un tenant; habilitarla puede exponer metadatos del host. Las arquitecturas con nodos privados/dedicados tienen requisitos y propiedades de aislamiento distintos.

Guarda lo siguiente como `vcluster-values.yaml` y sustituye la StorageClass por una clase aprobada y operativa. Usa namespaces de host independientes controlados por la plataforma para que los tenants no puedan editar el syncer/controlador privilegiado mediante un RoleBinding del host:

```yaml
sync:
  fromHost:
    nodes:
      enabled: false
controlPlane:
  statefulSet:
    persistence:
      volumeClaim:
        enabled: true
        storageClass: REPLACE_WITH_APPROVED_STORAGE_CLASS
        size: 5Gi
        retentionPolicy: Retain
    imagePullPolicy: IfNotPresent
```

```bash
helm repo add vcluster https://charts.loft.sh
helm repo update vcluster
helm template vcluster-tenant-a vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-a-host -f vcluster-values.yaml > tenant-a-reviewed.yaml
helm template vcluster-tenant-b vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-b-host -f vcluster-values.yaml > tenant-b-reviewed.yaml
```

Inspecciona el RBAC renderizado, almacenamiento, solicitudes de recursos, imagen y configuración de sincronización; después despliega mediante el propietario de Helm/GitOps revisado. El chart publicado renderiza `vcluster-pro:0.36.1` de forma predeterminada; revisa la edición elegida, la disponibilidad de funciones y las licencias antes del despliegue. Renderizar no verifica derechos de uso, persistencia, arranque del clúster ni aislamiento en producción. Haz copias de seguridad del estado del tenant y comprende la retención de PVC/PV antes de eliminar un clúster virtual o su namespace de host.

**Identidad y gobernanza AWS:** usa roles IRSA o Pod Identity compatibles por tenant, con confianza y permisos de recursos limitados. Estas identidades AWS complementan la autorización de Kubernetes. Una SCP fija permisos máximos para principales de cuentas miembro cubiertas; no concede acceso ni distingue namespaces de Kubernetes.

La denegación S3 siguiente ilustra una SCP asociada solo a la **cuenta/OU miembro de tenant A**, con como objetivo un bucket revisado de tenant B. No la asocies a una cuenta compartida esperando que distinga entre A y B:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyTenantBStoreFromTenantAAccount",
    "Effect": "Deny",
    "Action": ["s3:*"],
    "Resource": [
      "arn:aws:s3:::amzn-s3-demo-tenant-b",
      "arn:aws:s3:::amzn-s3-demo-tenant-b/*"
    ]
  }]
}
```

Las SCP no restringen la cuenta de administración ni los roles vinculados a servicios, y no limitan directamente a principales no relacionados de cuentas externas. Siguen siendo necesarios las políticas de recursos, permisos IAM y protecciones de datos. Esta es una barrera de protección a nivel de cuenta, no una política completa de aislamiento de tenants. Prueba el acceso efectivo y la reversión/retención según el diseño elegido; aquí no se crearon clústeres, clústeres virtuales ni SCP.

</details>

## Comprobaciones de acceso y ciclo de vida

11. ¿`update-kubeconfig` concede permisos de Kubernetes?
   * A) Sí, concede cluster-admin automáticamente
   * B) No; configura el cliente, mientras las entradas/políticas de acceso y RBAC determinan los permisos
   * C) Sí, mediante el certificado CA
   * D) Solo para un namespace nuevo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; configura el cliente, mientras las entradas/políticas de acceso y RBAC determinan los permisos**

La administración inicial depende de la configuración de bootstrap/herramientas. Conserva una identidad administradora conocida y prueba explícitamente el rol previsto.

</details>

12. ¿Un RoleBinding de namespace puede reducir el alcance de una política de acceso EKS cluster-admin?
   * A) Sí, RBAC siempre la anula
   * B) No, los permisos se acumulan
   * C) Sí, si el nombre del grupo es `system:masters`
   * D) Solo con `kubectl --as`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No, los permisos se acumulan**

Usa el ámbito de la política de acceso previsto o un grupo RBAC personalizado. `--as`/`--as-group` fuerza RBAC de Kubernetes y no prueba los permisos concedidos por una política de acceso EKS.

</details>

13. ¿Qué hace falta además de que la fase de un pod sea `Running`?
   * A) Nada
   * B) Solo el nombre de un log group
   * C) Readiness, salud/rollout y la ruta prevista de la aplicación
   * D) Que todo Job siga ejecutándose para siempre

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Readiness, salud/rollout y la ruta prevista de la aplicación**

`Running` puede incluir contenedores no preparados; los Jobs completados pueden estar correctamente en `Succeeded`. Valida el cómputo esperado y el comportamiento real de DNS/Service.

</details>

14. ¿Cuál es un plan adecuado de actualización de EKS?
   * A) Usar cualquier versión upstream más reciente
   * B) Saltar directamente dos versiones menores
   * C) Usar la información de publicación/preparación de EKS y avanzar una versión menor cada vez
   * D) Suponer que la reversión restaura todos los datos persistentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar la información de publicación/preparación de EKS y avanzar una versión menor cada vez**

La reversión condicional dentro de siete días no restaura etcd, las cargas de trabajo ni los datos. Revisa por separado la compatibilidad de componentes y las copias de seguridad.

</details>

15. ¿Qué se debe hacer antes de retirar un clúster?
   * A) Eliminar todos los PVC de inmediato
   * B) Eliminar por nombre los roles IAM genéricos
   * C) Eliminar primero la VPC
   * D) Revisar identidad/propiedad, copias de seguridad/política de recuperación, dependencias, protección y capacidades

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Revisar identidad/propiedad, copias de seguridad/política de recuperación, dependencias, protección y capacidades**

Usa el propietario original de IaC, recursos explícitos revisados y comprobaciones de finalización. Conserva los recursos compartidos y la evidencia de recuperación.

</details>

## Referencias

- [Add-on CloudWatch Observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)
- [Políticas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [Grupos de nodos administrados de EKS](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [Cluster Autoscaler para EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [Multi-tenancy de Kubernetes](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
- [Configuración de vCluster 0.36.1](https://github.com/loft-sh/vcluster/blob/v0.36.1/chart/values.yaml)
- [Ámbito de las SCP](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
- [Reversión de EKS](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
