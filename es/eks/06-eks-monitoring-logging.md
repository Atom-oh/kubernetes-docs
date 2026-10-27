# Supervisión y registro de Amazon EKS

> **Última actualización**: 23 de octubre de 2026

La supervisión y el registro eficaces son esenciales para mantener la fiabilidad, la disponibilidad y el rendimiento de los clústeres de Amazon EKS. Este documento abarca diversas herramientas, técnicas y prácticas recomendadas para implementar la supervisión y el registro en clústeres de EKS.

## Tabla de contenido

1. [Descripción general de la supervisión y el registro](#monitoring-and-logging-overview)
2. [Registro del plano de control de EKS](#eks-control-plane-logging)
3. [Registro de contenedores](#container-logging)
4. [Supervisión del clúster](#cluster-monitoring)
5. [Alertas y gestión de eventos](#alerting-and-event-management)
6. [Análisis y visualización de registros](#log-analysis-and-visualization)
7. [Prácticas recomendadas de supervisión y registro](#monitoring-and-logging-best-practices)
8. [Solución de problemas y depuración](#troubleshooting-and-debugging)

## Descripción general de la supervisión y el registro

### Importancia de la supervisión y el registro

La supervisión y el registro en clústeres de Amazon EKS son importantes por las siguientes razones:

1. **Visibilidad**: ofrecen visibilidad del estado, el rendimiento y el comportamiento del clúster
2. **Detección de problemas**: detectan problemas con anticipación, antes de que se vuelvan críticos
3. **Análisis de tendencias**: identifican tendencias de rendimiento y uso de recursos a lo largo del tiempo
4. **Planificación de capacidad**: permiten prever y planificar los requisitos de recursos
5. **Seguridad y auditoría**: respaldan las investigaciones y aportan las pruebas necesarias para los controles aplicables
6. **Solución de problemas**: permiten diagnosticar y resolver rápidamente los problemas cuando ocurren

### Arquitectura de supervisión y registro

Una arquitectura integral de supervisión y registro para un clúster de EKS consta de los siguientes componentes:

AWS entrega a CloudWatch Logs los registros de los tipos seleccionados del plano de control administrado. Los entornos de ejecución de contenedores escriben archivos de registro CRI; kubelet administra la rotación y el acceso a los registros, mientras que un recopilador de nodos lee los archivos. Las métricas y los seguimientos utilizan las rutas de recopilación/exportación configuradas.

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Architecture diagram showing EKS control-plane logs, pod logs, and node metrics flowing through Fluent Bit and Prometheus into CloudWatch Logs/Metrics, Amazon OpenSearch, and Grafana/Alertmanager.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-0.html)
-->

### Estrategia de supervisión y registro

Sigue estos pasos para desarrollar una estrategia eficaz de supervisión y registro:

1. **Definir objetivos**: define los objetivos y requisitos de supervisión y registro
2. **Identificar métricas y registros**: identifica las métricas y los registros clave que se recopilarán
3. **Seleccionar herramientas**: selecciona herramientas de supervisión y registro que satisfagan los requisitos
4. **Establecer líneas de referencia**: establece líneas de referencia para el comportamiento normal
5. **Configurar alertas**: configura alertas para eventos y umbrales importantes
6. **Automatizar**: automatiza los procesos de supervisión y registro tanto como sea posible
7. **Revisar periódicamente**: revisa y mejora periódicamente la estrategia de supervisión y registro

## Registro del plano de control de EKS

EKS exporta a CloudWatch Logs los registros seleccionados del plano de control administrado. Un recopilador del lado del nodo no examina el sistema de archivos del plano de control administrado. La entrega de registros se realiza según el mejor esfuerzo; configura el acceso y la retención, y detecta los registros faltantes, para luego verificar que efectivamente lleguen.

### Tipos de registros del plano de control

| Tipo | Propósito |
|---|---|
| `api` | Diagnósticos del componente del servidor de API |
| `audit` | Solicitudes de Kubernetes seleccionadas según la política y el nivel de auditoría |
| `authenticator` | Diagnósticos de autenticación de IAM de EKS |
| `controllerManager` | Operaciones del administrador de controladores principal |
| `scheduler` | Decisiones y diagnósticos del planificador |

El registro de auditoría no registra de forma incondicional todos los cuerpos de las solicitudes ni todas las acciones de las aplicaciones. Los registros relacionados con secretos pueden incluir solo metadatos, y la política excluye algunos eventos. Los registros de las API de AWS de CloudTrail y los registros de acceso a datos de las aplicaciones son fuentes de evidencia independientes.

### Inspeccionar y habilitar el registro

Antes de realizar un cambio, comprueba la región, el ARN, la configuración de registro actual y el estado de actualización del clúster que administras. Los cambios de registro requieren la capacidad de direcciones IP de subred documentada y generan cargos por ingesta/almacenamiento en CloudWatch.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```

Para un cambio aprobado, esto habilita los cinco tipos de registros e inspecciona la actualización devuelta:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
UPDATE_ID=$(aws eks update-cluster-config \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query 'update.id' --output text)
if [[ -z "$UPDATE_ID" || "$UPDATE_ID" == None ]]; then
  printf '%s\n' 'No update ID returned; inspect the request result.' >&2
  exit 1
fi
aws eks describe-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" \
  --query 'update.{ID:id,Status:status,Errors:errors}'
```

El comando final comprueba el estado; no espera a que termine la operación. Repite DescribeUpdate hasta que el estado sea Successful o se produzca un fallo terminal; después, confirma la configuración efectiva y la llegada de registros. Un ID de actualización no demuestra que la operación haya finalizado. Habilitar solo los tipos seleccionados no tiene por qué deshabilitar otros tipos existentes; cualquier deshabilitación explícita es una decisión independiente sobre retención/visibilidad.

Con la CLI de eksctl revisada, si se omite --approve, se muestra una vista previa del cambio. Asigna CLUSTER_NAME y AWS_REGION al mismo clúster verificado e inspecciona la vista previa:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler
```

Después de revisar ese plan, usa el comando de aplicación por separado:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

### Consultar los registros del plano de control

Usa el grupo real `/aws/eks/CLUSTER_NAME/cluster`. Los dos primeros ejemplos son heurísticas de búsqueda de texto para los flujos de los componentes seleccionados, no mediciones completas de tasas de error.

**Diagnósticos de API:**

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver-/ and @logStream not like /audit/
| filter @message like /[Ee]rror/
| sort @timestamp desc
| limit 20
```

**Diagnósticos de autenticación de IAM:**

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /[Ff]ailed|[Dd]enied|[Uu]nauthorized/
| sort @timestamp desc
| limit 20
```

**Denegaciones de auditoría:** usa los campos JSON detectados en lugar de buscar una cadena literal `responseStatus.code` en el texto JSON sin procesar. Confirma la estructura de los campos en un evento de muestra.

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code in [401, 403]
| sort @timestamp desc
| limit 20
```

### Retención y gestión de costos

Inspecciona la entrada exacta del grupo en los resultados de búsqueda por prefijo:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws logs describe-log-groups --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/eks/$CLUSTER_NAME/cluster" \
  --query 'logGroups[].{Name:logGroupName,RetentionDays:retentionInDays,KmsKey:kmsKeyId}'
```

Si una política aprobada exige 30 días, el cambio es `aws logs put-retention-policy --region "$AWS_REGION" --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" --retention-in-days 30`. Treinta días es un ejemplo de política, no un requisito de cumplimiento universal. Reducir la retención puede hacer que caduquen pruebas antiguas; aumentarla no recupera los registros eliminados. La retención, por sí sola, no demuestra que la entrega a un archivo sea correcta, que los datos sean íntegros ni que se cumpla la normativa.

### Registro de capacidades de EKS (GitOps, ACK, kro)

La función del 4 de junio de 2026 es compatible: los controladores de capacidades de ACK, kro y Argo CD se ejecutan en infraestructura administrada por AWS **fuera del clúster** y pueden entregar registros estructurados de los controladores mediante CloudWatch Vended Logs. Esto usa una configuración de entrega por capacidad, independiente de los cinco tipos de registros estándar del plano de control.

| Capacidad | Tipos de registros |
|---|---|
| ACK | `EKS_CAPABILITY_ACK_LOGS` |
| kro | `EKS_CAPABILITY_KRO_LOGS` |
| Argo CD | `EKS_CAPABILITY_ARGOCD_APPLICATION_LOGS`, `EKS_CAPABILITY_ARGOCD_APPLICATIONSET_LOGS`, `EKS_CAPABILITY_ARGOCD_COMMITSERVER_LOGS`, `EKS_CAPABILITY_ARGOCD_REPOSERVER_LOGS`, `EKS_CAPABILITY_ARGOCD_SERVER_LOGS` |

Obtén el ARN real de la capacidad antes de configurar su origen de entrega:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CAPABILITY_NAME:?Set the actual capability name}"
aws eks describe-capability --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --capability-name "$CAPABILITY_NAME" \
  --query 'capability.capabilityArn' --output text
```

El propietario configura PutDeliverySource con ese ARN/tipo de registro, PutDeliveryDestination con el destino aprobado y CreateDelivery para conectarlos. Revisa las políticas de destino, el cifrado, los permisos entre cuentas y la retención antes de habilitar la entrega.

Los destinos de CloudWatch Logs admiten consultas de Logs Insights. Los destinos de S3 son objetos para el flujo de trabajo seleccionado con S3/Athena, y Firehose envía registros a su destino configurado; no se consultan automáticamente mediante CloudWatch Logs Insights. Los registros de ACK incluyen controllerGroup para filtrar por controlador de servicio. Confirma la entrega real y los campos de consulta, y ten en cuenta los cargos de Vended Logs.

Cada origen de entrega que se agrega pone la capacidad en estado `UPDATING` durante unos segundos; mientras tanto, los cambios adicionales fallan con `ConflictException` (unos 6,6–7 segundos en las pruebas de octubre de 2026). Agrega los orígenes de uno en uno y espera a que el estado sea `ACTIVE`. Para obtener información general sobre las capacidades, consulta [Capacidades de EKS](./13-eks-capabilities.md).

Referencias: [registro del plano de control de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html), [política de auditoría y ejemplos de consultas](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html), [registros de controladores de capacidades](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html).

## Registro de contenedores

Los entornos de ejecución de contenedores escriben stdout/stderr en los archivos de registro CRI del nodo. Kubelet administra la rotación y proporciona acceso a los registros de los Pod; un recopilador sigue los archivos y reenvía los registros al backend seleccionado. Un mensaje JSON de la aplicación sigue estando dentro del contenedor CRI y no debe analizarse como si toda la línea de registro del contenedor fuera JSON de Docker.

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Architecture diagram showing container stdout/stderr picked up by kubelet, read by a log agent, and fanned out to CloudWatch Logs, Amazon OpenSearch, and Amazon S3.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-1.html)
-->

### Elegir quién administra el recopilador

El complemento CloudWatch Observability incluye un recopilador de registros de contenedores; si esa es la pila seleccionada, usa la configuración que administra. El ejemplo independiente de Fluent Bit que aparece a continuación es una alternativa para una canalización de registros administrada de forma independiente. No instales recopiladores superpuestos que lean los mismos archivos o envíen a los mismos destinos, a menos que exista un plan explícito para la duplicación y los costos.

### Ejemplo de Fluent Bit conectado

Este ejemplo usa AWS chart 0.2.0 con la imagen 3.4.14 (Fluent Bit 5.0.9), cuya versión publicada y configuración se verificaron. Está dirigido a nodos EC2 propios con Linux/containerd; la afinidad excluye deliberadamente las etiquetas de Fargate, Auto Mode e Hybrid de este ejemplo. Esos modos necesitan su propio diseño compatible de recopilación/identidad. El recopilador tolera taints en los nodos seleccionados; por tanto, revisa su ubicación y los permisos de admisión del agente de plataforma.

Prepara el espacio de nombres logging, un rol IRSA con privilegios mínimos llamado EKSLogWriter para la cuenta de servicio logging/eks-log-collector y el grupo de registros de CloudWatch que administras. Sustituye de forma coherente la cuenta, el rol, la región y el grupo específico del clúster. Configura el proveedor/trust audience/subject de OIDC de IAM tal como se describe en el capítulo de seguridad. El recopilador necesita permisos de escritura/flujo de CloudWatch y conectividad regional con STS/backend. Estos requisitos previos de IAM son independientes del RBAC de metadatos de Kubernetes.

Guárdalo como fluent-bit-values.yaml:

```yaml
fullnameOverride: eks-log-collector
image:
  tag: 3.4.14
serviceAccount:
  create: true
  name: eks-log-collector
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSLogWriter
nodeSelector:
  kubernetes.io/os: linux
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: NotIn
          values:
          - fargate
          - auto
          - hybrid
tolerations:
- operator: Exists
service:
  extraService: 'Flush 5

    Log_Level info

    Daemon Off

    HTTP_Server On

    HTTP_Listen 0.0.0.0

    HTTP_Port 2020

    Health_Check On

    storage.path /var/fluent-bit/state/storage

    storage.sync normal

    storage.checksum On

    storage.backlog.mem_limit 20M

    '
input:
  path: /var/log/containers/*.log
  db: /var/fluent-bit/state/tail.db
  multilineParser: cri
  skipLongLines: 'On'
  extraInputs: 'storage.type filesystem

    Read_from_Head On

    '
filter:
  kubeURL: https://kubernetes.default.svc:443
  mergeLog: 'On'
  mergeLogKey: data
  keepLog: 'On'
  k8sLoggingParser: 'Off'
  k8sLoggingExclude: 'Off'
  extraFilters: 'Use_Kubelet Off

    '
cloudWatch:
  enabled: false
cloudWatchLogs:
  enabled: true
  region: us-west-2
  logGroupName: /aws/eks/my-cluster/application
  logStreamPrefix: unmatched-
  logStreamTemplate: $kubernetes['namespace_name'].$kubernetes['pod_name'].$kubernetes['container_name']
  autoCreateGroup: false
  extraOutputs: 'auto_create_group false

    storage.total_limit_size 512M

    '
volumes:
- name: varlog
  hostPath:
    path: /var/log
    type: Directory
- name: state
  hostPath:
    path: /var/lib/eks-log-collector
    type: DirectoryOrCreate
volumeMounts:
- name: varlog
  mountPath: /var/log
  readOnly: true
- name: state
  mountPath: /var/fluent-bit/state
```

Chart 0.2.0 habilita de forma predeterminada la salida nativa cloudWatchLogs y deshabilita la salida anterior cloudWatch. Por lo tanto, establecer solo cloudWatch.region no configura la salida nativa activa. Los valores anteriores establecen la región/grupo de la salida real y conservan el registro completo; log_key enviaría solo el valor seleccionado y podría eliminar el contexto de Kubernetes.

logStreamTemplate usa la sintaxis de acceso a registros con un prefijo alternativo. logStreamPrefix es un prefijo literal, no una expresión de Kubernetes por registro. El analizador multilínea CRI gestiona el contenedor, mientras que Merge_Log coloca los campos JSON de la aplicación bajo data y conserva log. Las anotaciones de las cargas de trabajo no pueden elegir un analizador ni excluirse de la recopilación de este ejemplo.

### Limitar el RBAC de metadatos durante la representación

El ClusterRole amplio del chart publicado incluye nodes/proxy y una regla heredada de PodSecurityPolicy. Este modo de metadatos del servidor de API establece explícitamente Use_Kubelet Off y necesita permisos de lectura para los Pod/Namespace seleccionados, no acceso de proxy de kubelet. Guarda este post-renderer de Python 3 + PyYAML como fluent-bit-rbac.py. Rechaza identidades inesperadas del chart en lugar de dejar silenciosamente un rol amplio distinto:

```python
#!/usr/bin/env python3
"""Helm post-renderer for this pinned, owned metadata-only Fluent Bit setup."""
import sys
import yaml

objects = [obj for obj in yaml.safe_load_all(sys.stdin) if obj is not None]
roles = [obj for obj in objects if obj.get("kind") == "ClusterRole"]
bindings = [obj for obj in objects if obj.get("kind") == "ClusterRoleBinding"]
if len(roles) != 1 or roles[0].get("metadata", {}).get("name") != "eks-log-collector":
    raise SystemExit("Unexpected chart RBAC; review this renderer before proceeding")
if len(bindings) != 1 or bindings[0].get("roleRef", {}).get("name") != "eks-log-collector":
    raise SystemExit("Unexpected chart role binding")
subjects = bindings[0].get("subjects", [])
if len(subjects) != 1 or any(
    subjects[0].get(key) != value
    for key, value in {
        "kind": "ServiceAccount", "name": "eks-log-collector", "namespace": "logging"
    }.items()
):
    raise SystemExit("Unexpected collector identity")
if any(obj.get("kind") == "PodSecurityPolicy" for obj in objects):
    raise SystemExit("Obsolete PodSecurityPolicy output is not supported by this example")
roles[0]["rules"] = [{
    "apiGroups": [""],
    "resources": ["namespaces", "pods"],
    "verbs": ["get", "list", "watch"],
}]
yaml.safe_dump_all(objects, sys.stdout, sort_keys=False)
```

Para una nueva versión propia, instala conjuntamente los valores y el renderer:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
chmod +x fluent-bit-rbac.py
helm install eks-log-collector eks/aws-for-fluent-bit \
  --version 0.2.0 --namespace logging --create-namespace \
  -f fluent-bit-values.yaml --post-renderer ./fluent-bit-rbac.py \
  --wait --timeout 5m
```

Usa el mismo post-renderer revisado en cada actualización y vuelve a validarlo si cambian la versión del chart, la identidad de la versión, el espacio de nombres o el modo de metadatos. El ConfigMap representado se monta en el DaemonSet real; aplicar solo un ConfigMap no relacionado no cambiaría su configuración. El rol/cuenta de IRSA y el grupo de registros son requisitos previos, no recursos creados por este ejemplo de chart.

### Almacenamiento en búfer, rotación y comportamiento ante fallos

Los registros del host se leen en modo de solo lectura; los puntos de control y el estado del búfer del sistema de archivos usan un directorio independiente, local al nodo. La base de datos de seguimiento de registros registra posiciones y no constituye un archivo duradero en el backend. El reemplazo de un nodo puede eliminar ese estado. Read_from_Head On lee el contenido conservado del archivo cuando no existe un punto de control; por tanto, planifica el reprocesamiento y la gestión de duplicados.

Los límites de cola de salida de 512M y el ajuste de memoria de la cola pendiente son asignaciones de ejemplo. Cuando una cola de salida alcanza storage.total_limit_size, Fluent Bit puede descartar sus fragmentos más antiguos. Skip_Long_Lines On también omite deliberadamente los registros demasiado grandes. Los búferes finitos, los reintentos y el estado local del nodo no garantizan una entrega sin pérdidas ni exactamente una vez. Supervisa los reintentos, los registros descartados, la capacidad del disco y los fallos de destino; valida los límites con la tasa real de registros y el período de interrupción previsto.

### Distribución opcional a OpenSearch

Después de preparar el dominio VPC propio y la asignación IAM/FGAC del recopilador, guarda esta superposición como fluent-bit-opensearch-values.yaml y sustituye el nombre de host del punto de conexión. Añade `-f fluent-bit-opensearch-values.yaml` a la misma operación de Helm revisada. Mantener CloudWatch habilitado envía copias a ambos destinos; establece cloudWatchLogs.enabled=false solo si decides usar OpenSearch como único destino.

```yaml
opensearch:
  enabled: true
  host: vpc-eks-logs-EXAMPLE.us-west-2.es.amazonaws.com
  port: '443'
  tls: 'On'
  awsAuth: 'On'
  awsRegion: us-west-2
  index: eks-logs
  generateId: 'On'
  suppressTypeName: 'On'
  extraOutputs: 'tls.verify On

    storage.total_limit_size 512M

    '
```

Usa la verificación TLS del certificado/nombre de host y un diseño fijo y gobernado de índices/rotación. Un patrón de índice por Pod puede crear un número excesivo de índices/shards. Generate_ID reduce la indexación duplicada en los reintentos; las salidas independientes y la recuperación de fallos siguen necesitando validación. Escribir correctamente en un destino no demuestra que la entrega al otro también haya sido correcta.

### Otras pilas de registro

Fluentd sigue siendo una opción cuando una implementación administrada incluye los complementos necesarios de analizadores/salidas, montajes del host, identidad y configuración TLS. Un analizador JSON genérico no decodifica un contenedor CRI, y deshabilitar ssl_verify no soluciona los errores de certificado. El repositorio heredado del chart de Helm de Elastic está archivado; para una implementación de Elastic, usa la ruta de instalación del producto/Operator que se mantiene actualmente.

El chart loki-stack está marcado como obsoleto y el agente Promtail llegó al final de su vida útil el 2 de marzo de 2026. Para Loki, usa una implementación actual compatible y un cliente compatible, como Alloy, con almacenamiento, control de acceso y retención explícitos. Consulta la [guía de Loki](../observability/logging/01-loki.md) y la [guía de recopiladores](../observability/logging/05-collectors.md) para conocer la configuración específica. La retirada del agente Promtail no incluye al cliente lambda-promtail, que se mantiene por separado.

### Registros estructurados de aplicaciones

El siguiente ejemplo conservado contiene datos de aplicación sintéticos; no es una nueva medición ni un registro de esta auditoría. Su marca de tiempo conserva el valor ilustrativo original:

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

En la canalización configurada, el registro CRI proporciona la marca de tiempo de transporte y el JSON de la aplicación se encuentra bajo data. Verifica la zona horaria y el comportamiento del reloj antes de sobrescribir las marcas de tiempo con un campo de la aplicación. Los identificadores de usuario/sesión aún pueden ser sensibles o permitir la vinculación; minimízalos y nunca registres credenciales ni tokens de sesión sin procesar.

El ejemplo siguiente presupone la estructura de registros de este recopilador. Otros recopiladores pueden usar rutas de campos distintas:

```text
fields @timestamp, kubernetes.namespace_name, kubernetes.pod_name, data.level, log
| filter kubernetes.namespace_name = "production"
| filter data.level in ["ERROR", "error"]
| sort @timestamp desc
| limit 100
```

La validación abarcó los metadatos publicados del chart/imagen, las conexiones reales de Helm entre ConfigMap/DaemonSet, los esquemas nativos de Kubernetes y los casos de fallo del post-renderer. No se instaló ninguna imagen, no se inició ningún proceso de recopilación, no se envió ningún registro a AWS ni se probó el acceso a un sistema de archivos de producción. Valida los permisos reales de los nodos, las credenciales de IRSA y la entrega integral antes del despliegue.

Referencias: [versión 3.4.14 de la imagen de AWS](https://github.com/aws/aws-for-fluent-bit/releases/tag/v3.4.14), [salida de CloudWatch](https://docs.fluentbit.io/manual/data-pipeline/outputs/cloudwatch), [almacenamiento en búfer de Fluent Bit](https://docs.fluentbit.io/manual/data-pipeline/buffering), [ciclo de vida de Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/).

## Supervisión del clúster

La supervisión eficaz del clúster es esencial para hacer seguimiento del estado, el rendimiento y el uso de recursos de tu clúster de EKS. En esta sección se exploran diversas herramientas y técnicas para supervisar clústeres de EKS.

![Diagrama que relaciona soluciones de supervisión (CloudWatch Container Insights con AMP/AMG, la pila de Prometheus con kube-state-metrics, Node Exporter y Grafana, y el rastreo de X-Ray/OpenTelemetry) con la telemetría de nivel de clúster, nodo y Pod que cubren en un clúster de EKS.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-2.html)

### CloudWatch Container Insights

El complemento CloudWatch Observability combina las capacidades de Container Insights, la recopilación de registros de contenedores y Application Signals. Usa una única instalación administrada y evita que su recopilador Fluent Bit se superponga con otro recopilador que lea los mismos archivos. Configura la identidad, el acceso compatible a los nodos y la conectividad con el backend antes de esperar que lleguen datos.

#### Inspeccionar el clúster y las versiones compatibles del complemento

Para este ejemplo estándar de Linux EC2, prepara el agente EKS Pod Identity correspondiente y un rol de CloudWatch dedicado, con la relación de confianza limitada a este clúster y a amazon-cloudwatch/cloudwatch-agent. El operador necesita los permisos necesarios para el complemento/la asociación y permiso para pasar el rol aprobado. Revisa las versiones de Helm existentes, las anotaciones de ServiceAccount y las asociaciones, además de la lista de complementos de EKS; si ya existe un recopilador, sigue el proceso de migración/actualización de quien lo administra.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
CLUSTER_VERSION=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.version --output text)
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks describe-addon-versions --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability --kubernetes-version "$CLUSTER_VERSION"
```

Selecciona una versión compatible y revisada del catálogo en lugar de degradar a la versión fija de ejemplo v5.0.0. Los esquemas de configuración del complemento dependen de la versión. La representación local de referencia usó Helm chart 6.6.0, cuyo DaemonSet de Fluent Bit utiliza la misma ServiceAccount cloudwatch-agent que la ruta de identidad del agente.

#### Configuración explícita de Auto Monitor

Guárdalo como cloudwatch-config.json para el ejemplo de instalación nueva. Conserva la configuración predeterminada de registros de contenedores y deshabilita la selección automática amplia de cargas de trabajo y los reinicios automáticos hasta que se revise el despliegue de la aplicación:

```json
{
  "manager": {
    "applicationSignals": {
      "autoMonitor": {
        "monitorAllServices": false,
        "restartPods": false
      }
    }
  }
}
```

Esto controla la selección/reinicio de Auto Monitor, no todas las fuentes posibles de telemetría. Las anotaciones existentes, los selectores personalizados o las aplicaciones instrumentadas manualmente requieren una revisión aparte. Si tienes Python 3 y jsonschema disponibles localmente, recupera el esquema de la versión seleccionada y valida la configuración:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the cluster Region}"
: "${CLOUDWATCH_ADDON_VERSION:?Choose a reviewed compatible add-on build}"
aws eks describe-addon-configuration --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --output json > cloudwatch-addon-review.json
python3 - "$CLOUDWATCH_ADDON_VERSION" <<'PY'
import json
import sys
import jsonschema
with open("cloudwatch-addon-review.json") as stream:
    review = json.load(stream)
if review["addonName"] != "amazon-cloudwatch-observability" or review["addonVersion"] != sys.argv[1]:
    raise SystemExit("Returned schema does not match the selected add-on build")
schema = json.loads(review["configurationSchema"])
with open("cloudwatch-config.json") as stream:
    config = json.load(stream)
validator = jsonschema.validators.validator_for(schema)
validator.check_schema(schema)
validator(schema).validate(config)
PY
```

#### Crear una instalación nueva administrada

El rol de CloudWatch ya debe contar con los permisos necesarios de CloudWatch/trace para las funciones elegidas. Lo siguiente vuelve a comprobar el esquema/versión revisados, rechaza un complemento o una asociación de recopilador existentes y evita apropiarse de recursos en conflicto:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CLOUDWATCH_ADDON_VERSION:?Set the reviewed, schema-checked compatible build}"
: "${CLOUDWATCH_ROLE_ARN:?Set the prepared CloudWatch Pod Identity role ARN}"
python3 - "$CLOUDWATCH_ADDON_VERSION" <<'PY'
import json
import sys
import jsonschema
with open("cloudwatch-addon-review.json") as stream:
    review = json.load(stream)
if review["addonName"] != "amazon-cloudwatch-observability" or review["addonVersion"] != sys.argv[1]:
    raise SystemExit("Selected add-on build changed; review its schema again")
schema = json.loads(review["configurationSchema"])
with open("cloudwatch-config.json") as stream:
    config = json.load(stream)
jsonschema.validators.validator_for(schema)(schema).validate(config)
PY
EXISTING_ADDONS=$(aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" --output json)
python3 - "$EXISTING_ADDONS" <<'PY'
import json, sys
if "amazon-cloudwatch-observability" in json.loads(sys.argv[1])["addons"]:
    raise SystemExit("Add-on already exists; use its owner's reviewed upgrade procedure")
PY
EXISTING_ASSOCIATIONS=$(aws eks list-pod-identity-associations \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace amazon-cloudwatch --service-account cloudwatch-agent --output json)
python3 - "$EXISTING_ASSOCIATIONS" <<'PY'
import json, sys
if json.loads(sys.argv[1])["associations"]:
    raise SystemExit("Collector association already exists; inspect its owner before installation")
PY
ASSOCIATIONS=$(python3 - "$CLOUDWATCH_ROLE_ARN" <<'PY'
import json, sys
print(json.dumps([{"serviceAccount": "cloudwatch-agent", "roleArn": sys.argv[1]}]))
PY
)
aws eks create-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --pod-identity-associations "$ASSOCIATIONS" \
  --configuration-values file://cloudwatch-config.json --resolve-conflicts NONE
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability \
  --query 'addon.{Status:status,Version:addonVersion,Health:health.issues}'
```

CreateAddon es asíncrono. Inspecciona el estado y el estado de salud hasta que el complemento esté ACTIVE; luego, verifica los Pod del agente/recopilador, los puntos de datos reales de ContainerInsights y los grupos de registros previstos. Una solicitud correcta, el estado ACTIVE o un panel no demuestran que la ingesta sea completa. El comando DescribeAddon final anterior es una comprobación, no un comando de espera. Valida los fallos y los permisos antes de volver a intentarlo; no uses una sobrescritura no revisada ni borres la configuración existente para forzar la instalación.

#### Cambios de la versión 5.0.0

El cambio predeterminado de APM del 26 de febrero de 2026 es real: la versión 5.0.0+ habilita Auto Monitor de Application Signals de forma predeterminada en instalaciones nuevas y actualizaciones. monitorAllServices tiene el valor predeterminado true; restartPods tiene el valor predeterminado false. El alcance abarca Deployments, DaemonSets y StatefulSets compatibles asignados a servicios; se excluyen kube-system y amazon-cloudwatch de forma predeterminada. Las cargas de trabajo nuevas o reiniciadas dentro del alcance pueden instrumentarse sin anotaciones por carga de trabajo; no se garantiza la reinstrumentación inmediata de los Pod que ya están en ejecución.

Elige lenguajes/cargas de trabajo compatibles, revisa las integraciones existentes de OpenTelemetry/APM, el muestreo y los costos, y controla cualquier despliegue con reinicios. Las exclusiones explícitas tienen prioridad. Container Insights admite configuraciones de Linux y Windows, pero Application Signals no es compatible con nodos Windows de EKS. La recopilación/identidad de Fargate y los nodos Hybrid necesita las rutas específicas de plataforma documentadas; no deduzcas que es compatible basándote en un ejemplo genérico de DaemonSet.

#### Métricas, paneles y alarmas

Selecciona el clúster real en las vistas de Container Insights de la consola e inspecciona los nombres de métricas, dimensiones y datos recientes publicados. Las métricas de CPU/memoria/sistema de archivos del nodo describen el uso del nodo. La utilización de CPU/memoria del Pod usa los límites de los nodos como denominadores, no las solicitudes de los Pod. Hay agregaciones de espacios de nombres/servicios/clúster para las métricas documentadas, pero un porcentaje agregado no representa automáticamente la utilización ponderada por capacidad de un clúster heterogéneo.

Los paneles ayudan a inspeccionar los datos; no crean todas las alarmas ni garantizan la entrega de notificaciones. Los ejemplos de CloudWatch Alarms que aparecen más adelante usan métricas de nodos y Maximum con dimensiones seleccionadas explícitamente. Verifica la disponibilidad de las métricas y configura la alarma y la ruta de entrega adecuadas para la carga de trabajo.

La validación usó el chart publicado existente, su configuración de registro predeterminada representada y los argumentos de Auto Monitor, además de nueve casos simulados de esquema/propiedad/flujo de fallos. El esquema de prueba sintético comprueba el comportamiento del asistente y no sustituye al esquema en vivo específico de la versión indicado anteriormente. Durante esta auditoría no se probó ningún complemento, instrumentación de cargas de trabajo, exportación de telemetría ni recurso de AWS.

Referencias: [instalación del complemento CloudWatch y Auto Monitor](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html), [anuncio de APM predeterminado](https://aws.amazon.com/about-aws/whats-new/2026/02/application-performance-monitoring-cloudwatch-eks/), [métricas de Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html).

### EKS Node Monitoring Agent

EKS Node Monitoring Agent publica condiciones de estado del sistema, el almacenamiento, la red y los aceleradores a nivel de nodo. Se convirtió en software de código abierto el 24 de febrero de 2026 y está incluido en EKS Auto Mode. Para una instalación del complemento que se administre por separado, inspecciona la versión real del clúster, los complementos existentes y las versiones compatibles del agente antes de elegir una versión:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
KUBERNETES_VERSION=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.version --output text)
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks describe-addon-versions --addon-name eks-node-monitoring-agent \
  --kubernetes-version "$KUBERNETES_VERSION" --region "$AWS_REGION"
```

Instala o actualiza a través del administrador del complemento existente, con una versión revisada y una configuración de nodo compatible. Un comando para crear un complemento no es un procedimiento de actualización para una instalación existente.

Los nombres de las condiciones por sí solos no indican si un nodo está en mal estado. Lee el estado y el motivo, interpretando el significado de cada condición: Ready=False es distinto de MemoryPressure=False.

```bash
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{range .status.conditions[*]}{"  "}{.type}{"="}{.status}{" reason="}{.reason}{"\n"}{end}{end}'
```

La supervisión y la habilitación de reparaciones son cuestiones separadas. Auto Mode tiene habilitada la reparación automática de nodos; los grupos de nodos administrados usan nodeRepairConfig y Karpenter usa su indicador de función NodeRepair. Inspecciona un grupo de nodos administrado real antes de atribuir al agente un comportamiento de reparación:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${NODEGROUP_NAME:?Set an actual managed node group name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-nodegroup --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Name:nodegroupName,Repair:nodeRepairConfig,Health:health.issues}'
```

La elegibilidad para una reparación depende de la condición, el motivo, el tiempo de espera y las salvaguardas aplicables. En los valores predeterminados documentados no hay acciones de reparación automática para MemoryPressure ni DiskPressure. No des por sentado que todas las condiciones informadas o la instalación de un agente demostrarán que se reemplazará un nodo. La personalización de un agente de código abierto también requiere probar la semántica de sus condiciones en relación con la configuración de reparación seleccionada.

Referencias: [anuncio de código abierto](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-eks-node-monitoring-agent-open-source/), [reparación automática de nodos](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html).

### Prometheus y Grafana

Prometheus es una base de datos de series temporales y un sistema de supervisión, y Grafana es una herramienta de paneles para visualizar métricas. Puedes usar ambas herramientas conjuntamente para supervisar tu clúster de EKS de forma integral.

#### Amazon Managed Service for Prometheus y Grafana

AMP almacena y consulta las métricas de Prometheus ingeridas; AMG consulta las fuentes de datos configuradas y presenta paneles. Crear cualquiera de los espacios de trabajo no despliega automáticamente un scraper, no concede su identidad de AWS ni conecta la fuente de datos. Este ejemplo inspecciona los espacios de trabajo existentes que administras y amplía la versión de kube-prometheus-stack que aparece más adelante, evitando instalar un segundo Prometheus.

**Identidad de ingesta de AMP y valores**

Prepara un rol IRSA para ServiceAccount monitoring/amp-writer. Su política de confianza debe usar el proveedor OIDC de este clúster y las condiciones exactas sub=system:serviceaccount:monitoring:amp-writer y aud=sts.amazonaws.com. Concede aps:RemoteWrite en el ARN del espacio de trabajo previsto. El proceso de Prometheus debe recibir el token proyectado y poder acceder a STS y al punto de conexión de AMP; el RBAC de Kubernetes constituye una ruta de permisos independiente. No adjuntes también una asociación de Pod Identity no relacionada ni claves estáticas de AWS a este ejemplo.

Lo siguiente lee el espacio de trabajo y escribe una superposición para el chart revisado 92.9.0. Acepta las formas documentadas del punto de conexión, con o sin /api/v1/, y agrega remote_write exactamente una vez. Se requiere Python 3; no se crea ningún espacio de trabajo:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the AMP workspace Region}"
: "${AMP_WORKSPACE_ID:?Set the owned AMP workspace ID}"
: "${AMP_WRITE_ROLE_ARN:?Set the prepared IRSA writer role ARN}"
: "${CLUSTER_NAME:?Set the source cluster name}"
aws amp describe-workspace --region "$AWS_REGION" \
  --workspace-id "$AMP_WORKSPACE_ID" --output json > amp-workspace.json
python3 - "$AWS_REGION" "$AMP_WORKSPACE_ID" "$AMP_WRITE_ROLE_ARN" "$CLUSTER_NAME" <<'PY'
import json
import sys
from urllib.parse import urlsplit, urlunsplit

region, workspace_id, role_arn, cluster = sys.argv[1:]
with open("amp-workspace.json") as stream:
    workspace = json.load(stream)["workspace"]
if workspace["workspaceId"] != workspace_id or workspace["status"]["statusCode"] != "ACTIVE":
    raise SystemExit("Review the workspace identity and ACTIVE status")
arn = workspace["arn"].split(":", 5)
if len(arn) != 6 or arn[2] != "aps" or arn[3] != region or arn[5] != "workspace/" + workspace_id:
    raise SystemExit("Workspace ARN does not match the selected Region/ID")
endpoint = urlsplit(workspace["prometheusEndpoint"])
path = endpoint.path.rstrip("/")
if path.endswith("/api/v1"):
    path = path[:-7]
if (endpoint.scheme != "https" or not endpoint.hostname or endpoint.username
        or endpoint.password or endpoint.query or endpoint.fragment
        or path != "/workspaces/" + workspace_id):
    raise SystemExit("Inspect the workspace endpoint before configuring remote write")
remote_write = urlunsplit((endpoint.scheme, endpoint.netloc, path + "/api/v1/remote_write", "", ""))
values = {
    "prometheus": {
        "serviceAccount": {
            "create": True, "name": "amp-writer", "createTokenSecret": True,
            "annotations": {"eks.amazonaws.com/role-arn": role_arn},
        },
        "prometheusSpec": {
            "externalLabels": {"cluster": cluster},
            "remoteWrite": [{"url": remote_write, "sigv4": {"region": region}}],
        },
    },
}
with open("amp-values.json", "w") as stream:
    json.dump(values, stream, indent=2)
    stream.write("\n")
print("Wrote amp-values.json; review it with all existing release values")
PY
```

Combina amp-values.json con monitoring-values.yaml en los valores de instalación/actualización revisados por el administrador. La superposición reemplaza la lista remoteWrite; conserva deliberadamente los destinos y las etiquetas externas existentes. Para una nueva versión, añade -f amp-values.json al comando de instalación de más adelante. Para una versión existente, conserva todos los ajustes actuales y revisa la diferencia representada y el despliegue antes de aplicar el procedimiento de actualización del administrador. Cambiar la ServiceAccount cambia la identidad del Pod de Prometheus. Chart 92.9.0 usa un Secret de token de ServiceAccount explícito para la autorización predeterminada de ServiceMonitor del servidor de API/kubelet. Protege ese Secret y sigue el procedimiento de rotación/revocación; es distinto del token IRSA de corta duración y con audiencia vinculada. Deshabilitar createTokenSecret sin reemplazar todas las credenciales de los monitores que dependen de él rompe la representación o la autenticación.

Para varias réplicas, configura las etiquetas de deduplicación de alta disponibilidad y la topología de réplicas documentadas para AMP, en lugar de suponer que los scrapes duplicados no tienen costo. Establece los presupuestos de cardinalidad, retención e ingesta según la carga de trabajo real. Comprueba los fallos/atrasos de remote-write y consulta datos recientes en el espacio de trabajo previsto; un despliegue correcto de Helm no demuestra la ingesta.

**Autenticación y conexión de fuente de datos de AMG**

```bash
set -euo pipefail
: "${AMG_REGION:?Set the Grafana workspace Region}"
: "${AMG_WORKSPACE_ID:?Set the owned Grafana workspace ID}"
aws grafana describe-workspace --region "$AMG_REGION" \
  --workspace-id "$AMG_WORKSPACE_ID" \
  --query 'workspace.{ID:id,Status:status,Version:grafanaVersion,Endpoint:endpoint,Role:workspaceRoleArn,Authentication:authentication,PermissionType:permissionType}'
```

La autenticación de usuarios del espacio de trabajo (IAM Identity Center/SAML), los permisos de usuarios de Grafana y el rol IAM de la fuente de datos de AWS del espacio de trabajo son controles distintos. Una cuenta de servicio de Grafana es una identidad para la API HTTP de Grafana; crear una cuenta de servicio ADMIN no crea una fuente de datos AMP ni concede aps:QueryMetrics. Evita aprovisionar una identidad de API con permisos amplios solo para ver métricas.

En AMG 12+, selecciona el complemento de fuente de datos Amazon Managed Service for Prometheus. En esa versión de AMG se eliminó la compatibilidad con SigV4 del complemento Prometheus Core, y las fuentes de datos AMP existentes migran al complemento AMP. Usa la documentación correspondiente a la versión real del espacio de trabajo. Mediante la configuración aprobada del espacio de trabajo, selecciona la cuenta/región/espacio de trabajo previsto, configura su identidad de consulta y prueba una serie conocida. El flujo de configuración documentado de fuentes de datos de AWS usa permisos administrados por el servicio; un espacio de trabajo administrado por el cliente necesita su propia configuración IAM revisada, no un cambio automático de propiedad.

El rol de consulta suele necesitar aps:QueryMetrics, aps:GetSeries, aps:GetLabels y aps:GetMetricMetadata, limitados al espacio de trabajo; la detección u otras funciones habilitadas pueden requerir acciones adicionales. El punto de conexión de consulta no es la URL de ingesta remote_write. Si aprovisionas un espacio de trabajo por separado, la CLI usa --workspace-name y requiere --account-access-type, configuración de autenticación y permisos; la automatización de IAM administrada por el servicio está vinculada al flujo de trabajo documentado en la consola. Completa la configuración de identidad, asignación de usuarios y acceso a la red antes de considerar que el espacio de trabajo está listo para usarse.

Referencias: [remote write de AMP](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-onboard-ingest-metrics-existing-Prometheus.html), [complemento AMP de AMG](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-prometheus-data-source.html), [configuración de fuentes de datos de AWS](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-AMP-adding-AWS-config.html). Durante esta auditoría no se probó ningún espacio de trabajo, flujo de autenticación ni ingesta de telemetría.

#### Prometheus y Grafana autoadministrados

Este ejemplo utiliza una versión propia de kube-prometheus-stack, que incluye el Prometheus Operator necesario para los ejemplos de ServiceMonitor y PrometheusRule. Un chart independiente de Prometheus no proporciona automáticamente esos CRD/controladores. Inspecciona los Operator, las versiones y la propiedad de los CRD existentes antes de instalar; para una pila existente, sigue el procedimiento de actualización de quien la administra.

La línea base revisada es chart 92.9.0 / Operator 0.94.1, representada para EKS 1.36. Presupone nodos EC2 estándar con Linux y una StorageClass ebs-gp3 cifrada preparada, con permisos de EBS CSI funcionales. Para Auto Mode u otra implementación de almacenamiento, selecciona su clase compatible real y la ubicación de los nodos. La retención y los tamaños de PVC siguientes son asignaciones de ejemplo, no garantías de capacidad medidas.

Prepara el espacio de nombres monitoring y el Secret grafana-admin con las claves admin-user/admin-password mediante el proceso aprobado de administración de secretos. Los valores hacen referencia a ese Secret en lugar de incluir una contraseña compartida en los valores de Helm o en los argumentos de los comandos. Guarda lo siguiente como monitoring-values.yaml:

```yaml
grafana:
  admin:
    existingSecret: grafana-admin
    userKey: admin-user
    passwordKey: admin-password
  service:
    type: ClusterIP
  rbac:
    namespaced: true
  sidecar:
    dashboards:
      searchNamespace: monitoring
    datasources:
      searchNamespace: monitoring
  persistence:
    enabled: true
    storageClassName: ebs-gp3
    size: 10Gi
    accessModes:
    - ReadWriteOnce
  deploymentStrategy:
    type: Recreate
prometheus:
  prometheusSpec:
    retention: 14d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: ebs-gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 20Gi
kubeEtcd:
  enabled: false
kubeControllerManager:
  enabled: false
kubeScheduler:
  enabled: false
kubeProxy:
  enabled: false
kubelet:
  serviceMonitor:
    tlsConfig:
      insecureSkipVerify: false
      ca:
        configMap:
          name: kubelet-serving-ca
          key: ca.crt
```

Los sidecars de paneles/fuentes de datos de Grafana solo observan monitoring con un rol limitado a ese espacio de nombres. Se accede al servicio ClusterIP localmente mediante el reenvío de puertos. El ejemplo de PVC de una sola réplica usa Recreate para evitar escritores simultáneos durante el despliegue; por tanto, planifica una interrupción de la interfaz de usuario durante el reemplazo. No es un diseño de Grafana de alta disponibilidad.

De forma predeterminada, el chart omite la verificación del certificado del servidor kubelet. En cambio, estos valores requieren un ConfigMap monitoring/kubelet-serving-ca preparado, con ca.crt que contenga la cadena de CA de servicio de kubelet de confianza, y certificados cuyos SAN coincidan con los puntos de conexión consultados. Verifica esa relación de confianza mediante el proceso de administración de certificados del propietario del nodo; la CA del servidor de API de EKS no es automáticamente la CA del servicio de kubelet. Si no se dispone de ese requisito previo, resuelve la configuración de certificados antes de habilitar la recopilación. No vuelvas silenciosamente a insecureSkipVerify para que un destino fallido parezca estar en buen estado. En esta auditoría no se probó ningún protocolo de enlace TLS de kubelet.

Los trabajos de scraping de etcd/controller-manager/scheduler/kube-proxy están deshabilitados en este ejemplo porque la configuración no proporciona sus puntos de conexión directos. Habilita un trabajo solo después de configurar su punto de conexión real, accesible y autorizado; las métricas del servidor de API o de CloudWatch son fuentes independientes y no hacen que funcione un destino ServiceMonitor de un componente ausente.

Para una versión nueva administrada:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm install monitoring prometheus-community/kube-prometheus-stack \
  --version 92.9.0 --namespace monitoring --create-namespace \
  -f monitoring-values.yaml --wait --timeout 10m
```

La espera de Helm no demuestra que funcionen todos los recursos creados por Operator, destinos y rutas de notificación. Inspecciona los recursos generados, la vinculación de PVC, el estado de los destinos de Prometheus y los datos de métricas:

```bash
kubectl get pods,svc,pvc -n monitoring
kubectl get prometheus,alertmanager -n monitoring
```

Accede a Grafana en `http://127.0.0.1:3000` mientras se ejecuta este comando, usando las credenciales del almacén de secretos aprobado:

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

Protege la base de datos/PVC de Grafana y las definiciones de paneles exportadas. Usa el proceso compatible de rotación de credenciales de Grafana; cambiar únicamente un Secret de inicialización no demuestra que haya cambiado la contraseña de un usuario de una base de datos existente. No publiques la interfaz con una contraseña de ejemplo compartida.

La representación del chart confirma el servicio real de Prometheus monitoring-kube-prometheus-prometheus, el servicio Grafana monitoring-grafana y el UID de fuente de datos prometheus. Los ServiceMonitor/PrometheusRule personalizados deben coincidir con los selectores release=monitoring que utiliza esta versión. Los manifiestos representados y las comprobaciones de esquema son evidencia local; no se probó ninguna pila, PVC ni inicio de sesión en un clúster activo.

Referencia: [chart kube-prometheus-stack y guía de actualización](https://github.com/prometheus-community/helm-charts/tree/kube-prometheus-stack-92.9.0/charts/kube-prometheus-stack).

#### Métricas clave de Prometheus

La disponibilidad de las métricas depende del destino real de scraping y los permisos, no solo del nombre del panel:

- Node exporter proporciona series de CPU, memoria, sistema de archivos y red del nodo en los nodos compatibles.
- Kubelet/cAdvisor proporciona métricas de recursos de contenedores; kube-state-metrics proporciona el estado de objetos de Kubernetes, como los reinicios y la disponibilidad.
- El servidor de API expone métricas autorizadas. Las métricas directas de etcd/controller-manager/scheduler requieren sus propios puntos de conexión accesibles; la configuración anterior no habilita esos destinos.

La ausencia de una serie puede indicar un exporter ausente, un scraping fallido, una plataforma no compatible o un cambio en la métrica. No significa automáticamente que el uso sea cero ni que el sistema esté en buen estado.

#### Paneles útiles de Grafana

Comienza con los paneles de Kubernetes, node-exporter y servidor de API incluidos en la versión revisada de kube-prometheus-stack y selecciona su UID de fuente de datos prometheus. Los ID de paneles de la comunidad, por sí solos, no establecen un contrato compatible de métricas/etiquetas. Inspecciona las consultas, unidades, reglas de grabación necesarias y referencias a fuentes de datos de cada panel importado. Un gráfico sin datos no demuestra que el componente supervisado esté en buen estado.

Los ID de la comunidad indicados anteriormente siguen existiendo, pero varios títulos y propósitos implícitos eran inexactos. La verificación del catálogo arroja las siguientes referencias; no se probó la compatibilidad de importación/ejecución:

| ID | Título real del catálogo | Nota sobre el alcance |
| --- | --- | --- |
| [15661](https://grafana.com/grafana/dashboards/15661-k8s-dashboard-en-20250125/) | K8S Dashboard | Vista general de recursos de K8S |
| [1860](https://grafana.com/grafana/dashboards/1860-node-exporter-full/) | Node Exporter Full | Requiere series node-exporter compatibles |
| [6417](https://grafana.com/grafana/dashboards/6417-kubernetes-cluster-prometheus/) | Kubernetes Cluster (Prometheus) | Vista general del clúster/contenedores; última actualización del catálogo en 2018 |
| [12006](https://grafana.com/grafana/dashboards/12006-kubernetes-apiserver/) | Kubernetes apiserver | Panel de latencia/caché del servidor de API; última actualización del catálogo en 2020 |
| [13770](https://grafana.com/grafana/dashboards/13770-1-kubernetes-all-in-one-cluster-monitoring-kr/) | 1 Kubernetes All-in-one Cluster Monitoring KR | Panel todo en uno en coreano, optimizado para el entorno de VM de su libro |

#### Ejemplos de consultas PromQL

Estos ejemplos coinciden con las etiquetas job y metrics_path de la pila revisada. Conserva la identidad del espacio de nombres para los Pod y la etiqueta cluster cuando exista, especialmente en un espacio de trabajo AMP compartido. Las etiquetas externas de Prometheus se adjuntan al enviar datos externamente; no aparecen automáticamente en todas las series almacenadas localmente. Las agregaciones max reducen las observaciones duplicadas del mismo objeto identificado, no las cargas de trabajo distintas. Revisa las etiquetas antes de adaptar este patrón.

Porcentaje de CPU no inactiva del nodo, promediado entre las CPU:

```promql
100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))
```

Los diez Pod con mayor cantidad de bytes de conjunto de trabajo de memoria de contenedor:

```promql
topk(10, sum by (cluster, namespace, pod) (max by (cluster, namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD"})))
```

Contadores de reinicios actuales por UID de Pod; esto no detecta CrashLoopBackOff:

```promql
sum by (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid, container) (kube_pod_container_status_restarts_total{job="kube-state-metrics"}))
```

Porcentaje de sistema de archivos raíz no disponible, excluyendo los sistemas de archivos de tamaño cero:

```promql
(100 * (1 - max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_avail_bytes{job="node-exporter",mountpoint="/"}) / max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}))) and on (cluster, instance, device, mountpoint, fstype) (max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}) > 0)
```

Los porcentajes de CPU describen aquí el tiempo no inactivo, la memoria se mide en bytes y los reinicios son contadores para la vida útil actual del Pod/contenedor. Usa rate/increase en un período elegido si quieres conocer los cambios de los contadores. El cálculo del sistema de archivos usa el espacio disponible y puede incluir espacio reservado que no está disponible para los usuarios ordinarios. Estos ejemplos sirven para investigar, no son umbrales de alerta universales.

### Rastreo distribuido con AWS X-Ray

X-Ray sigue siendo un backend de trazas compatible. Sus SDK y daemon pasaron a mantenimiento con solo correcciones de seguridad el 25 de febrero de 2026; el calendario actual de AWS no publica una fecha de fin para esa fase. Para nuevas instrumentaciones, usa una integración compatible de OpenTelemetry/ADOT. Un daemon o recopilador de X-Ray no necesita permisos cluster-admin de Kubernetes para enviar trazas, y ese rol de Kubernetes no concede permisos de escritura de AWS.

#### Propiedad del recopilador y requisitos previos

Elige un único responsable de instrumentación/recopilación. La ruta de Application Signals del complemento CloudWatch indicada anteriormente es una alternativa; no agregues otro agente de SDK a un proceso ya instrumentado sin revisar los spans duplicados y los conflictos. El ejemplo explícito siguiente usa OpenTelemetry Operator 0.158.0 con ADOT Collector 0.50.0 y una canalización solo de trazas.

Prepara estas dependencias a través de sus respectivos responsables antes de aplicar el recopilador:

- Un Operator en funcionamiento con los CRD/webhooks correspondientes. El manifiesto publicado de upstream usa cert-manager; utiliza su ruta de instalación/actualización documentada. El complemento EKS ADOT es otra ruta de administración, con un esquema específico para cada versión. La versión de Collector no contiene un manifiesto de instalación de Operator.
- Un espacio de nombres dedicado tracing-demo y una ServiceAccount adot-traces con confianza IRSA preparada para este clúster, sub=system:serviceaccount:tracing-demo:adot-traces y aud=sts.amazonaws.com. Concede las acciones de escritura X-Ray necesarias (PutTraceSegments para esta canalización) y proporciona conectividad con STS/X-Ray. Este recopilador solo de OTLP no detecta objetos de Kubernetes ni requiere RBAC para todo el clúster.
- El Secret tracing-demo/otel-receiver-tls con tls.crt/tls.key y un certificado de servidor válido para adot-traces-collector.tracing-demo.svc. Monta su CA de confianza en la aplicación. La emisión/renovación de certificados y la recarga/reinicialización del recopilador son responsabilidades operativas.
- Una CNI que aplique NetworkPolicy y una salida de la aplicación revisada. El ejemplo permite la entrada desde los Pod del espacio de nombres default etiquetados app=my-app; se aplica a todos los Pod del espacio de nombres dedicado tracing-demo. Las etiquetas seleccionan el tráfico, pero no autentican una carga de trabajo ni sustituyen los controles RBAC sobre quién puede crear Pod.

Revisa la [versión de Operator publicada](https://github.com/open-telemetry/opentelemetry-operator/releases/tag/v0.158.0) y la [versión de ADOT](https://github.com/aws-observability/aws-otel-collector/releases/tag/v0.50.0) en lugar de aplicar una URL de Collector como manifiesto de Operator. El CRD v1beta1 utiliza un valor object para spec.config. Cambia juntos el ejemplo de región en los campos env/exporter:

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-traces
  namespace: tracing-demo
spec:
  mode: deployment
  replicas: 1
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-traces
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: "true"
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: "1"
      memory: 512Mi
  volumes:
  - name: receiver-tls
    secret:
      secretName: otel-receiver-tls
  volumeMounts:
  - name: receiver-tls
    mountPath: /etc/otel/tls
    readOnly: true
  config:
    receivers:
      otlp:
        protocols:
          http:
            endpoint: 0.0.0.0:4318
            tls:
              cert_file: /etc/otel/tls/tls.crt
              key_file: /etc/otel/tls/tls.key
    processors:
      memory_limiter:
        check_interval: 1s
        limit_percentage: 75
        spike_limit_percentage: 15
      batch: {}
    exporters:
      awsxray:
        region: us-west-2
        local_mode: true
        no_verify_ssl: false
        index_all_attributes: false
        telemetry:
          enabled: false
    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
    service:
      extensions: [health_check]
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch]
          exporters: [awsxray]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tracing-ingress
  namespace: tracing-demo
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: default
      podSelector:
        matchLabels:
          app: my-app
    ports:
    - protocol: TCP
      port: 4318
```

El Operator deriva el servicio receiver ClusterIP del puerto OTLP/HTTP: adot-traces-collector en tracing-demo, TCP 4318. El receiver no valida una identidad de usuario ni una declaración de autorización de negocio; este ejemplo usa TLS de servidor y el límite de red seleccionado. Un aislamiento más estricto puede requerir mTLS o un autenticador de receiver compatible. Configúralos de forma coherente en ambos extremos antes de ampliar el acceso.

La aceptación del recopilador no confirma el almacenamiento. Comprueba el Deployment/Service generado, el protocolo de enlace TLS, la selección de credenciales de AWS, los fallos del exporter y una traza conocida en X-Ray. El ejemplo en memoria de una sola réplica no es una canalización sin pérdidas ni de alta disponibilidad; dimensiona y prueba los búferes, la contrapresión, el comportamiento de reintento y el manejo de fallos para la carga de trabajo. Una comprobación del esquema del CRD no valida toda la configuración de componentes ni demuestra que el recopilador se inicie.

#### Instrumentar la aplicación y propagar el contexto

Para una aplicación Python 3.10+, fija opentelemetry-sdk==1.44.0 y opentelemetry-exporter-otlp-proto-http==1.44.0 en el archivo de dependencias de la aplicación. Configura cada servicio por separado; un recopilador compartido no debe sobrescribir el service.name de cada servicio entrante con un único valor global. El punto de conexión del exporter HTTP incluye /v1/traces; un punto de conexión gRPC en 4317 utiliza otro protocolo/configuración.

```bash
export OTEL_SERVICE_NAME=my-app
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

El archivo de CA debe montarse en el contenedor de la aplicación. Crea una instancia RequestTracing durante el inicio de la aplicación, llama a handle_request desde el controlador real del servidor con nombres normalizados para los encabezados entrantes y una operación que use los encabezados salientes proporcionados, y llama a close durante el cierre ordenado. La instrumentación automática del framework/cliente puede gestionar estos límites; evita instrumentar dos veces la misma operación:

```python
import os
from urllib.parse import urlsplit

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class RequestTracing:
    def __init__(self):
        endpoint = os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or parsed.path != "/v1/traces":
            raise ValueError("Set the HTTPS OTLP/HTTP traces endpoint including /v1/traces")
        self.provider = TracerProvider(
            resource=Resource.create({
                "service.name": os.environ["OTEL_SERVICE_NAME"],
                "k8s.cluster.name": os.environ["CLUSTER_NAME"],
            }),
            sampler=ParentBased(TraceIdRatioBased(0.1)),
        )
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            certificate_file=os.environ["OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"],
            timeout=10,
        )
        self.provider.add_span_processor(BatchSpanProcessor(exporter))
        self.tracer = self.provider.get_tracer("example.request-handler")
        self.propagator = TraceContextTextMapPropagator()

    def handle_request(self, incoming_headers, operation):
        parent = self.propagator.extract(incoming_headers)
        with self.tracer.start_as_current_span("request", context=parent, kind=SpanKind.SERVER):
            outgoing_headers = {}
            self.propagator.inject(outgoing_headers)
            return operation(outgoing_headers)

    def close(self):
        self.provider.shutdown()
```

Este adaptador muestra la propagación de W3C tracecontext y un span de servidor; no implementa un servidor HTTP ni todos los spans de cliente. Las integraciones de borde de AWS que usan X-Amzn-Trace-Id necesitan el propagador/puente compatible; no se debe suponer que la extracción solo de W3C lee ese encabezado. El muestreo de cabecera al 10 % es un ejemplo para nuevas raíces, con decisiones de los padres conservadas; no puede garantizar la retención de todos los errores o solicitudes lentas posteriores. El muestreo de cola necesita un diseño independiente que enrute conjuntamente todos los spans de una traza y disponga de búfer suficiente.

#### Mapas de trazas e investigación

Inspecciona los mapas de trazas, las distribuciones de latencia y los detalles de errores/fallos en las vistas de rastreo de X-Ray/CloudWatch disponibles para la cuenta. Un mapa refleja los spans instrumentados, muestreados y entregados correctamente; la ausencia de una arista no demuestra que los servicios nunca se comuniquen. Correlaciona los ID de traza con registros y métricas retenidos adecuadamente, y excluye credenciales, datos personales y atributos de solicitudes sin límites.

Esta auditoría valida únicamente API/esquemas publicados y comportamientos locales sintéticos. No afirma que se haya desplegado un recopilador, instrumentación activa, exportación de trazas ni prueba de capacidad de producción. Referencias: [calendario de mantenimiento de X-Ray](https://aws.amazon.com/blogs/mt/aws-x-ray-sdks-daemon-migration-to-opentelemetry/), [administración de EKS ADOT](https://docs.aws.amazon.com/eks/latest/userguide/opentelemetry.html), [exporter AWS X-Ray](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awsxrayexporter).

### Kubernetes Dashboard

El [proyecto Kubernetes Dashboard](https://github.com/kubernetes-retired/dashboard) está archivado y ya no se mantiene. Sus responsables señalan Headlamp, bajo Kubernetes SIG UI, para las necesidades actuales de interfaz. No se debe usar como ruta de instalación actual la antigua receta de manifiesto sin procesar de Dashboard v2.7 y token cluster-admin.

Elige una interfaz mantenida y revisa sus requisitos reales de autenticación, TLS, autorización y actualización. Usa la identidad IAM/RBAC y el alcance de espacio de nombres previstos, siguiendo los ejemplos de access-entry/RBAC del capítulo de seguridad. Una interfaz no necesita una ServiceAccount cluster-admin sin restricciones como usuario predeterminado; exponer un token bearer de administrador no sustituye un diseño de acceso.

### Métricas personalizadas y supervisión

Puedes implementar soluciones personalizadas para recopilar y supervisar métricas específicas de las aplicaciones:

#### Integración de la biblioteca cliente de Prometheus

Para la API Prometheus Java client 1.8.0, usa los paquetes actuales io.prometheus.metrics y dependencias alineadas. En un proyecto Java de Gradle existente:

```groovy
dependencies {
    implementation(platform("io.prometheus:prometheus-metrics-bom:1.8.0"))
    implementation("io.prometheus:prometheus-metrics-core")
    implementation("io.prometheus:prometheus-metrics-exporter-httpserver")
}
```

Guarda el ejemplo como App.java. El método main expone métricas en el puerto 9400 y espera; el controlador real de solicitudes de la aplicación debe llamar a processRequest con su operación. Iniciar un punto de conexión de métricas por sí solo no contabiliza solicitudes de negocio. No se presenta ningún recuento sintético de solicitudes como tráfico medido:

```java
import io.prometheus.metrics.core.metrics.Counter;
import io.prometheus.metrics.core.metrics.Histogram;
import io.prometheus.metrics.exporter.httpserver.HTTPServer;
import java.io.IOException;

public class App {
    private static final Counter requests = Counter.builder()
        .name("app_requests_total").help("Requests processed by this application.")
        .register();
    private static final Histogram latency = Histogram.builder()
        .name("app_request_latency_seconds").help("Request processing time in seconds.")
        .register();

    public static void processRequest(Runnable operation) {
        requests.inc();
        long started = System.nanoTime();
        try {
            operation.run();
        } finally {
            latency.observe((System.nanoTime() - started) / 1_000_000_000.0);
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        HTTPServer server = HTTPServer.builder().port(9400).buildAndStart();
        Runtime.getRuntime().addShutdownHook(new Thread(server::close));
        Thread.currentThread().join();
    }
}
```

Las API y coordenadas de dependencias del código se verificaron con el cliente publicado; en el entorno de esta auditoría no había un compilador/entorno de ejecución de Java, por lo que este ejemplo no se compiló ni ejecutó. Intégralo en la compilación, el ciclo de vida y la ruta de solicitudes de la aplicación antes del despliegue. Limita los valores de las etiquetas; los ID de solicitud, ID de usuario y URL sin procesar no son dimensiones métricas predeterminadas adecuadas.

#### Recopilar métricas personalizadas

Supón que los Pod de la aplicación que administras están en default, llevan la etiqueta app=my-app y realmente sirven /metrics por TCP 9400. El Service selecciona Pod; ServiceMonitor selecciona las etiquetas del Service y el puerto con nombre. Su etiqueta release=monitoring y namespaceSelector lo conectan con la pila anterior:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-metrics
  namespace: default
  labels:
    app: my-app
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
  - name: metrics
    port: 9400
    targetPort: 9400
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-monitor
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
    - default
  selector:
    matchLabels:
      app: my-app
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

Verifica los EndpointSlices del Service y el estado del destino de Prometheus, y permite el acceso únicamente al recopilador previsto a través de los controles de red/política de seguridad aplicables. Este ejemplo de métricas HTTP dentro del clúster requiere un límite de red revisado; configura TLS/autenticación si el punto de conexión de métricas los necesita. ServiceMonitor no instrumenta la aplicación ni crea un servidor de métricas que no exista.

Referencias: [inicio rápido del cliente Java](https://prometheus.github.io/client_java/getting-started/quickstart/), [configuración de Prometheus](https://prometheus.io/docs/prometheus/latest/configuration/configuration/).

#### Paneles personalizados

Crea paneles personalizados en Grafana para visualizar las métricas de la aplicación:

1. Inicia sesión en Grafana
2. Haz clic en el icono "+" y selecciona "Dashboard"
3. Haz clic en "Add panel"
4. Selecciona "Prometheus" como fuente de datos
5. Escribe una consulta PromQL (por ejemplo, `rate(app_requests_total[5m])`)
6. Configura el título y la descripción del panel, y el tipo de visualización
7. Haz clic en "Save"

## Alertas y gestión de eventos

La gestión eficaz de alertas y eventos es esencial para detectar y responder rápidamente a los problemas del clúster de EKS. En esta sección se exploran diversas herramientas y técnicas para administrar alertas y eventos en clústeres de EKS.

![Diagrama de arquitectura que muestra métricas y registros de CloudWatch, eventos de AWS, métricas de Prometheus y registros de Loki, y eventos de Kubernetes y aplicaciones enrutados a través de CloudWatch Alarms, EventBridge, Prometheus Alertmanager y un enrutador de eventos hacia SNS (suscripciones de correo electrónico y SQS), Lambda, Slack y PagerDuty, y OpsGenie.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-3.html)

### CloudWatch Alarms

Confirma los puntos de datos recientes y el espacio de nombres, nombre y conjunto de dimensiones exactos de la métrica antes de crear una alarma. Estos ejemplos usan los agregados de nodos ContainerInsights documentados solo con ClusterName y Maximum. Esto puede revelar un punto crítico en un nodo; no es una medida de utilización ponderada por capacidad de todo el clúster. Usa dimensiones específicas de nodo para identificar el nodo afectado.

Los umbrales 80/80/85 por ciento y los dos períodos de evaluación de cinco minutos son opciones de política ilustrativas. Que Maximum supere el umbral en dos períodos no significa que hubiera saturación continua cada segundo de diez minutos. La falta de datos sigue siendo falta de datos, no una prueba de utilización saludable. Revisa la definición de alarma existente antes de reutilizar su nombre, porque PutMetricAlarm actualiza una alarma existente. Los permisos de notificación, las suscripciones y las pruebas de entrega son requisitos independientes.

#### CPU de nodo

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the metric Region}"
: "${ALARM_PREFIX:?Set a reviewed alarm-name prefix owned by this workflow}"
: "${SNS_TOPIC_ARN:?Set the approved notification topic ARN}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name "${ALARM_PREFIX}-node-cpu" \
  --alarm-description "Example: maximum reported node cpu utilization exceeds 80 percent" \
  --metric-name node_cpu_utilization --namespace ContainerInsights \
  --statistic Maximum --period 300 --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --evaluation-periods 2 --datapoints-to-alarm 2 --treat-missing-data missing \
  --alarm-actions "$SNS_TOPIC_ARN"
```

#### Memoria de nodo

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the metric Region}"
: "${ALARM_PREFIX:?Set a reviewed alarm-name prefix owned by this workflow}"
: "${SNS_TOPIC_ARN:?Set the approved notification topic ARN}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name "${ALARM_PREFIX}-node-memory" \
  --alarm-description "Example: maximum reported node memory utilization exceeds 80 percent" \
  --metric-name node_memory_utilization --namespace ContainerInsights \
  --statistic Maximum --period 300 --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --evaluation-periods 2 --datapoints-to-alarm 2 --treat-missing-data missing \
  --alarm-actions "$SNS_TOPIC_ARN"
```

#### Sistema de archivos del nodo

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the metric Region}"
: "${ALARM_PREFIX:?Set a reviewed alarm-name prefix owned by this workflow}"
: "${SNS_TOPIC_ARN:?Set the approved notification topic ARN}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name "${ALARM_PREFIX}-node-disk" \
  --alarm-description "Example: maximum reported node disk utilization exceeds 85 percent" \
  --metric-name node_filesystem_utilization --namespace ContainerInsights \
  --statistic Maximum --period 300 --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --evaluation-periods 2 --datapoints-to-alarm 2 --treat-missing-data missing \
  --alarm-actions "$SNS_TOPIC_ARN"
```

Estos comandos de alarma no se ejecutaron en AWS. Referencia: [métricas y dimensiones de Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html).

### Prometheus Alertmanager

Prometheus evalúa las reglas de alerta; Alertmanager agrupa, deduplica y enruta las alertas resultantes. El Operator no consume automáticamente un ConfigMap con un nombre arbitrario para el Alertmanager que administra. La pila revisada utiliza Alertmanager 0.34.0; conecta explícitamente su configuración y los archivos de credenciales.

#### Configuración de Alertmanager

Para el ejemplo de Slack, prepara monitoring/notification-credentials mediante el proceso aprobado de gestión de secretos, con una clave slack-url que contenga la URL real del webhook. Mantén las credenciales fuera de los ConfigMap, del texto del repositorio y de los argumentos de comandos de Helm. Guarda esta definición de enrutamiento sin secretos como alertmanager-config.yaml:

```yaml
global:
  resolve_timeout: 5m
route:
  group_by: [cluster, namespace, alertname]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: slack-notifications
  routes:
  - matchers:
    - alertname="Watchdog"
    receiver: discard
receivers:
- name: discard
- name: slack-notifications
  slack_configs:
  - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-url
    channel: "#eks-alerts"
    send_resolved: true
    title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.summary }} — {{ .Annotations.description }}{{ "\n" }}{{ end }}'
```

El webhook debe estar autorizado para el destino Slack previsto; el campo channel no anula los permisos de la aplicación de Slack. Este ejemplo descarta la alerta Watchdog, que siempre está activa, para evitar enviar mensajes periódicos a Slack. Un monitor de latido/vigilancia real necesita un receiver configurado aparte y detección externa de ausencias; descartar Watchdog no prueba la entrega de alertas.

Valida el archivo localmente con el amtool correspondiente y luego crea el Secret de configuración solo para una instalación nueva administrada. Si ya existe un Secret/versión, sigue el procedimiento de actualización revisado de su administrador:

```bash
amtool --no-version-check check-config alertmanager-config.yaml
kubectl create secret generic alertmanager-routing -n monitoring \
  --from-file=alertmanager.yaml=alertmanager-config.yaml
```

Guarda lo siguiente como alertmanager-values.yaml y combínalo con todos los valores revisados de la versión de monitoring. configSecret selecciona el Secret y el Operator espera su clave alertmanager.yaml; secrets monta notification-credentials en /etc/alertmanager/secrets/notification-credentials. Revisa los recursos adicionales AlertmanagerConfig seleccionados en monitoring con release=monitoring antes del despliegue:

```yaml
alertmanager:
  alertmanagerSpec:
    useExistingSecret: true
    configSecret: alertmanager-routing
    secrets:
    - notification-credentials
    alertmanagerConfigSelector:
      matchLabels:
        release: monitoring
    alertmanagerConfigNamespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: monitoring
```

Comprueba el estado de la configuración generada/recargada y los fallos de notificación; luego, usa una alerta de prueba etiquetada a través de un destino de prueba aprobado antes de confiar en las notificaciones de guardia. El análisis local y las pruebas de rutas no demuestran la disponibilidad del Secret, los permisos del webhook, la conectividad SMTP ni la entrega real. El ejemplo del chart de una sola réplica también necesita un diseño de disponibilidad independiente.

#### Configuración de reglas de alerta

La etiqueta de versión de la regla coincide con el selector de Prometheus. Comprueba si hay reglas equivalentes incluidas para evitar alertas duplicadas. CrashLoopBackOff es un motivo de espera de Kubernetes; un umbral de tasa de reinicios por sí solo no demuestra esa condición. Estos ejemplos requieren las series indicadas de kube-state-metrics y usan la identidad de espacio de nombres/Pod UID/contenedor o nodo:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kubernetes-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: kubernetes-example
    rules:
    - alert: KubernetesPodCrashLooping
      expr: max by (cluster, namespace, pod, uid, container) (max_over_time(kube_pod_container_status_waiting_reason{job="kube-state-metrics",reason="CrashLoopBackOff"}[5m])) >= 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "CrashLoopBackOff observed for {{ $labels.namespace }}/{{ $labels.pod }}"
        description: "Inspect container {{ $labels.container }} logs and events; the rule tracks recent waiting reasons, not a restart-count guarantee."
    - alert: KubernetesNodeMemoryPressure
      expr: max by (cluster, node) (kube_node_status_condition{job="kube-state-metrics",condition="MemoryPressure",status="true"}) == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} reports MemoryPressure"
        description: "Inspect node capacity and workloads; the observed condition has matched for five minutes."
    - alert: KubernetesNodeDiskPressure
      expr: max by (cluster, node) (kube_node_status_condition{job="kube-state-metrics",condition="DiskPressure",status="true"}) == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} reports DiskPressure"
        description: "Inspect disk space and inodes; the observed condition has matched for five minutes."
```

La regla CrashLoopBackOff examina ventanas recientes repetidas de cinco minutos; no cuenta los reinicios. La presión del nodo es una condición observada de kubelet, distinta de un porcentaje genérico de utilización. Las series ausentes/obsoletas pueden impedir que se active una alerta; por tanto, supervisa por separado el estado del scraping y la disponibilidad de las métricas. Los umbrales y tiempos de espera son ejemplos, no garantías de respuesta ante incidentes.

### Reglas de eventos de EventBridge

Usa los nombres de eventos y campos de carga útil publicados por el servicio emisor. El catálogo de eventos directos de EKS incluye resultados de creación/actualización/eliminación de complementos, eventos de estado de salud de complementos degradado/restablecido y terminación programada de Fargate. No publica los nombres genéricos EKS Cluster State Change ni EKS Node Group State Change usados en los ejemplos antiguos. La actividad de la API de EKS entregada mediante CloudTrail utiliza un detail-type y una carga útil distintos.

#### Eventos directos de estado de complementos y actividad de API de CloudTrail

Lo siguiente escribe dos alternativas delimitadas a la cuenta y región seleccionadas. Abarcan la actividad coincidente de esa cuenta/región, no la de un solo clúster. Para limitar más una regla, inspecciona un evento capturado de ese tipo específico y prueba sus campos documentados; no des por sentado que todos los eventos contienen detail.clusterName.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the owned Region}"
: "${ACCOUNT_ID:?Set the owned 12-digit AWS account ID}"
python3 - "$AWS_REGION" "$ACCOUNT_ID" <<'PY'
import json
import re
import sys
region, account = sys.argv[1:]
if not re.fullmatch(r"[0-9]{12}", account):
    raise SystemExit("ACCOUNT_ID must contain 12 digits")
base = {"source": ["aws.eks"], "account": [account], "region": [region]}
patterns = {
    "eks-addon-health-pattern.json": dict(base, **{
        "detail-type": ["EKS Addon Health Degraded", "EKS Addon Health Restored"],
    }),
    "eks-update-api-pattern.json": dict(base, **{
        "detail-type": ["AWS API Call via CloudTrail"],
        "detail": {
            "eventSource": ["eks.amazonaws.com"],
            "eventName": ["UpdateClusterVersion", "UpdateNodegroupVersion"],
        },
    }),
}
for filename, pattern in patterns.items():
    with open(filename, "w") as stream:
        json.dump(pattern, stream, indent=2)
        stream.write("\n")
PY
```

El patrón de CloudTrail coincide con los eventos de API UpdateClusterVersion y UpdateNodegroupVersion, incluidas las solicitudes aplicables de actualización/reversión. Un evento de API de CloudTrail registra un intento o una solicitud aceptada, no la finalización de una actualización asíncrona. Inspecciona los campos de error y correlaciona las solicitudes correctas con el ID de actualización y el estado de DescribeUpdate. Asegúrate de que la entrega de eventos de administración de CloudTrail pertinente esté configurada. La entrega directa y la derivada de CloudTrail se realiza según el mejor esfuerzo; por tanto, usa también comprobaciones del estado del servicio y supervisión de fallos.

#### Conectar un destino SNS administrado

Prepara un tema SNS estándar, sus suscripciones confirmadas y un rol de ejecución de destino de EventBridge en la misma cuenta/región. El rol debe confiar en EventBridge y permitir sns:Publish en el tema previsto, con los permisos KMS aplicables al cifrado. El operador necesita los permisos correspondientes para reglas/destinos y permiso para pasar el rol aprobado. EventBridge admite actualmente un rol de ejecución para destinos SNS; las políticas basadas en recursos son una alternativa, no una consecuencia automática de agregar un destino.

Elige un archivo de patrón generado y un nombre nuevo de regla que administres. La comprobación previa rechaza los nombres existentes, pero PutRule es una operación de inserción/actualización, así que coordina la propiedad y los cambios simultáneos. La regla se crea deshabilitada y un fallo parcial de PutTargets detiene el flujo:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed Region}"
: "${ACCOUNT_ID:?Set the reviewed account ID}"
: "${RULE_NAME:?Set a new owned rule name}"
: "${PATTERN_FILE:?Select one reviewed pattern JSON file}"
: "${SNS_TOPIC_ARN:?Set the prepared standard SNS topic ARN}"
: "${EVENTBRIDGE_ROLE_ARN:?Set the prepared EventBridge target execution role ARN}"
python3 - "$AWS_REGION" "$ACCOUNT_ID" "$RULE_NAME" "$PATTERN_FILE" \
  "$SNS_TOPIC_ARN" "$EVENTBRIDGE_ROLE_ARN" <<'PY'
import json
import re
import sys
region, account, name, path, topic, role = sys.argv[1:]
if not re.fullmatch(r"[0-9]{12}", account) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name):
    raise SystemExit("Review the account ID and rule name")
with open(path) as stream:
    pattern = json.load(stream)
if pattern.get("account") != [account] or pattern.get("region") != [region] or pattern.get("source") != ["aws.eks"]:
    raise SystemExit("Pattern scope differs from the selected account/Region/service")
t, r = topic.split(":", 5), role.split(":", 5)
if (len(t) != 6 or len(r) != 6 or t[0] != "arn" or r[0] != "arn"
        or t[1] != r[1] or t[2:5] != ["sns", region, account]
        or r[2:5] != ["iam", "", account] or not r[5].startswith("role/")
        or not t[5] or t[5].endswith(".fifo")):
    raise SystemExit("Use the reviewed same-account standard topic and target role")
with open("eks-event-targets.json", "w") as stream:
    json.dump([{"Id": "ops-sns", "Arn": topic, "RoleArn": role}], stream)
PY
EXISTING=$(aws events list-rules --region "$AWS_REGION" --event-bus-name default \
  --name-prefix "$RULE_NAME" --query 'Rules[].Name' --output json)
python3 - "$RULE_NAME" "$EXISTING" <<'PY'
import json
import sys
if sys.argv[1] in json.loads(sys.argv[2]):
    raise SystemExit("Rule already exists; use its owner's reviewed update procedure")
PY
aws events put-rule --region "$AWS_REGION" --event-bus-name default \
  --name "$RULE_NAME" --state DISABLED --event-pattern "file://$PATTERN_FILE"
aws events put-targets --region "$AWS_REGION" --event-bus-name default \
  --rule "$RULE_NAME" --targets file://eks-event-targets.json \
  --output json > eks-event-targets-result.json
python3 - <<'PY'
import json
with open("eks-event-targets-result.json") as stream:
    result = json.load(stream)
if result["FailedEntryCount"] != 0:
    raise SystemExit("Target configuration failed; inspect FailedEntries before retrying")
print("Rule remains DISABLED; review the target and pattern before enabling")
PY
```

Revisa la respuesta completa del destino, el rol, las suscripciones, la política de reintento/cola de mensajes fallidos de entrega y un evento capturado representativo. Puedes comprobar la coincidencia del patrón con TestEventPattern; no prueba los permisos del destino ni la entrega. Habilítala solo después de esa revisión:

```bash
aws events enable-rule --region "$AWS_REGION" --event-bus-name default --name "$RULE_NAME"
```

Supervisa las invocaciones coincidentes/fallidas y verifica un evento integral aprobado después de la activación. Una regla, un destino o una respuesta de API correcta no garantizan por sí solos la entrega de alertas. Durante esta auditoría no se crearon recursos, eventos ni notificaciones de EventBridge/SNS.

Referencias: [catálogo de eventos de EKS de EventBridge](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html), [permisos de destinos](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html).

### Supervisión de eventos de Kubernetes

Los eventos de Kubernetes ayudan a investigar la programación, las descargas de imágenes, los reinicios y otras actividades de objetos. Son observaciones efímeras y de mejor esfuerzo, y pueden agrupar ocurrencias repetidas; no constituyen una pista de auditoría completa y duradera. Inspecciona primero el espacio de nombres previsto:

```bash
kubectl events -n default --types=Warning
kubectl events -n default --types=Warning --watch
```

#### Versión y administración del recopilador

El exporter original de Opsgenie no se mantiene. Su bifurcación activa pasó de resmoio a mustafaakin/kubernetes-event-exporter. La versión publicada más reciente examinada aquí es v1.7, de febrero de 2024, aunque el repositorio tiene actividad de desarrollo posterior. Que un repositorio esté activo o que su etiqueta más reciente sea antigua no demuestra que exista una imagen de producción actualizada con los parches vigentes.

La siguiente referencia se verificó con el código fuente de configuración/watcher de v1.7. Requiere una imagen propia, revisada y actualizada mediante el proceso de compilación, que conserve este contrato de configuración/CLI, se ejecute como UID 65532 y pueda leer la configuración montada con un sistema de archivos raíz de solo lectura. Establece su digest inmutable durante la representación; no se proporciona ninguna imagen pública latest ni un digest inventado. Durante esta auditoría no se creó ninguna imagen, no se revisaron vulnerabilidades ni se probó la compatibilidad en tiempo de ejecución.

#### Alcance de espacio de nombres, RBAC y configuración

Este ejemplo se ejecuta en el espacio de nombres existente monitoring, pero solo observa Events de core/v1 en default. omitLookup=true deshabilita las solicitudes GET independientes usadas para enriquecer etiquetas/anotaciones del objeto involucrado; por tanto, el Role concede solo lectura de eventos en default, no lectura comodín de Secrets ni de todos los recursos de API. La elección de líder está deshabilitada para la única réplica, así que no se conceden permisos de escritura de leases. Mantén alineados el espacio de nombres, Role y RoleBinding cuando adaptes el alcance.

Guárdalo como event-exporter-template.yaml. Contiene un marcador de imagen y debe representarse antes de usarse. La regla match apunta a un receiver con nombre; ese receiver envía JSON a stdout, que puede recopilar la canalización de registros de contenedores existente que administras. Esta configuración exporta únicamente eventos Warning:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: event-exporter
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: event-exporter-read
  namespace: default
rules:
- apiGroups: [""]
  resources: [events]
  verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: event-exporter-read
  namespace: default
subjects:
- kind: ServiceAccount
  name: event-exporter
  namespace: monitoring
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: event-exporter-read
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: event-exporter-config
  namespace: monitoring
data:
  config.yaml: |
    logLevel: warn
    logFormat: json
    namespace: default
    omitLookup: true
    maxEventAgeSeconds: 60
    metricsNamePrefix: event_exporter_
    leaderElection:
      enabled: false
    route:
      routes:
      - match:
        - type: Warning
          receiver: event-log
    receivers:
    - name: event-log
      stdout:
        deDot: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: event-exporter
  namespace: monitoring
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: event-exporter
  template:
    metadata:
      labels:
        app: event-exporter
    spec:
      serviceAccountName: event-exporter
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: event-exporter
        image: REVIEWED_EVENT_EXPORTER_IMAGE
        args:
        - -conf=/etc/event-exporter/config.yaml
        - -metrics-address=127.0.0.1:2112
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 250m
            memory: 128Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        volumeMounts:
        - name: config
          mountPath: /etc/event-exporter
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: event-exporter-config
```

Se requieren Python 3 y PyYAML para la representación. Inspecciona primero los recursos event-exporter existentes y quién los administra; para una instalación existente, sigue el procedimiento de actualización de su responsable:

```bash
set -euo pipefail
: "${EVENT_EXPORTER_IMAGE:?Set the reviewed, patched image reference including @sha256 digest}"
python3 - "$EVENT_EXPORTER_IMAGE" <<'PY'
import re
import sys
import yaml
image = sys.argv[1]
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}", image):
    raise SystemExit("Use a reviewed image pinned by SHA256 digest")
with open("event-exporter-template.yaml") as stream:
    objects = list(yaml.safe_load_all(stream))
deployment = next(obj for obj in objects if obj["kind"] == "Deployment")
container = deployment["spec"]["template"]["spec"]["containers"][0]
if container["image"] != "REVIEWED_EVENT_EXPORTER_IMAGE":
    raise SystemExit("Review the template before replacing its image")
container["image"] = image
with open("event-exporter-rendered.yaml", "w") as stream:
    yaml.safe_dump_all(objects, stream, sort_keys=False)
PY
```

Para una instalación nueva que administres, revisa el manifiesto representado, la identidad de descarga de imágenes y la conectividad de API antes de aplicarlo. Recreate evita réplicas superpuestas durante el despliegue, pero introduce interrupciones; no es un recopilador de alta disponibilidad:

```bash
kubectl apply -f event-exporter-rendered.yaml
kubectl rollout status deployment/event-exporter -n monitoring --timeout=120s
kubectl logs -n monitoring deployment/event-exporter --tail=100
```

#### Pérdidas, eventos repetidos y cargas útiles de alertas

El watcher v1.7 examinado gestiona las notificaciones de adición e ignora las devoluciones de llamada de actualización/eliminación. Por lo tanto, el recuento/las actualizaciones de series de eventos repetidos no son un contador fiable de ocurrencias exportadas. maxEventAgeSeconds=60 es un límite de admisión ilustrativo, no la retención del backend: los eventos más antiguos pueden descartarse durante el inicio, el control de tasa o las interrupciones. La nueva enumeración/reinicios también pueden repetir observaciones. Selecciona y prueba el manejo de actualizaciones, el almacenamiento en búfer y el destino duradero necesarios antes de usar el recuento de eventos para tomar decisiones operativas.

Inspecciona también los contadores de observación/descarte, además de los registros. Este ejemplo enlaza el listener de métricas del exporter a loopback; un operador autorizado puede inspeccionarlo mediante un reenvío de puertos local. No agrega automáticamente el punto de conexión a Prometheus:

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  deployment/event-exporter 2112:2112
```

Lee /metrics en `http://127.0.0.1:2112/metrics` mientras está activo el reenvío. Un despliegue o un registro stdout no confirma por sí solo el almacenamiento en CloudWatch/OpenSearch; verifica el recopilador de registros existente y el destino previsto. Los mensajes de eventos pueden contener detalles operativos sensibles, así que revisa el acceso, el filtrado y la retención.

No envíes un objeto Event de Kubernetes sin procesar a Alertmanager cambiando solo una URL de webhook. El punto de conexión actual /api/v2/alerts de Alertmanager espera su esquema de matriz de alertas; la ruta antigua /api/v1/alerts no es la API actual. Un adaptador específico debe traducir la identidad, las etiquetas, las anotaciones y la semántica de resolución. La ruta stdout/registros anterior no pretende implementar ese adaptador.

Referencias: [repositorio mantenido del exporter](https://github.com/mustafaakin/kubernetes-event-exporter), [watcher v1.7](https://github.com/mustafaakin/kubernetes-event-exporter/blob/v1.7/pkg/kube/watcher.go), [API v2 de Alertmanager](https://github.com/prometheus/alertmanager/blob/v0.34.0/api/v2/openapi.yaml).

### Integración de canales de notificación

Usa receivers compatibles con la versión real de Alertmanager. Los fragmentos siguientes son entradas bajo receivers en alertmanager-config.yaml, no recursos de Kubernetes. Para elegir uno, agrega el receiver y cambia route.receiver o una ruta hija coincidente por su nombre exacto; luego, valida toda la configuración y actualiza el Secret seleccionado. Una entrada de receiver que no se use no enruta ninguna alerta.

#### Integración con Slack

El ejemplo conectado de Slack anterior usa un archivo de webhook montado. Confirma que el canal esté permitido y evita publicar todas las etiquetas/anotaciones de las alertas sin revisar los datos sensibles. Nunca incluyas un token o webhook real de Slack en un ejemplo de Provider/ConfigMap enviado al repositorio.

#### Integración con PagerDuty

Para una integración Events API v2, prepara la clave pagerduty-routing-key en notification-credentials. routing_key_file hace referencia a esa clave de integración, no a un token genérico de la API REST de PagerDuty. Conecta las alertas críticas mediante una ruta hija revisada si solo deben generar avisos las alertas críticas:

```yaml
name: pagerduty-notifications
pagerduty_configs:
- routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
  send_resolved: true
  severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
  description: '{{ .CommonLabels.alertname }}'
```

#### Integración de correo electrónico

Sustituye el host/dirección/usuario SMTP de ejemplo reservado por la configuración del servicio de correo aprobado y prepara smtp-password en el mismo Secret de credenciales. Exige TLS y verifica la confianza del servidor, la autorización del remitente y la entrega. Este es un receiver de correo electrónico de Alertmanager, no un Provider de Flux:

```yaml
name: email-notifications
email_configs:
- to: oncall@example.com
  from: alerts@example.com
  smarthost: smtp.example.com:587
  auth_username: alerting-user
  auth_password_file: /etc/alertmanager/secrets/notification-credentials/smtp-password
  require_tls: true
  send_resolved: true
```

#### Receiver nativo de Amazon SNS

Alertmanager 0.34.0 tiene un receiver nativo de SNS; no hace falta un servicio webhook sns-forwarder sin definir para esa ruta. Sustituye la región/cuenta/tema de ejemplo por los del tema estándar que administras. Asigna a la ServiceAccount real de Alertmanager una identidad de AWS compatible con sns:Publish en ese tema, además de los permisos KMS aplicables si el tema está cifrado y de conectividad de red. El rol de Prometheus o de la aplicación no se convierte automáticamente en el rol de Alertmanager. No se incluyen claves de acceso estáticas de AWS:

```yaml
name: sns-notifications
sns_configs:
- sigv4:
    region: us-west-2
  topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
  send_resolved: true
  subject: 'EKS {{ .CommonLabels.alertname }}'
```

Confirma las suscripciones del tema y las políticas de destino, y prueba la entrega por separado. Los temas FIFO tienen consideraciones adicionales de deduplicación/agrupación; este fragmento apunta a un tema estándar. El análisis del receiver no prueba IAM ni la publicación en SNS.

Los Providers de notificaciones de Flux enrutan eventos de reconciliación de Flux junto con recursos Alert de Flux y fuentes de eventos seleccionadas. Por el mero hecho de existir, no reciben alertas arbitrarias de Prometheus ni eventos de Kubernetes. Mantén ese flujo de trabajo separado de la configuración de receivers de Alertmanager que se muestra aquí.

Referencia: [configuración y receivers de Alertmanager](https://prometheus.io/docs/alerting/latest/configuration/).

### Gestión y escalamiento de alertas

Implementa estrategias para gestionar y escalar alertas de forma eficaz:

#### Niveles de gravedad de las alertas

Clasifica las alertas en los siguientes niveles de gravedad:

- **Crítica**: problemas graves que requieren atención inmediata
- **Advertencia**: problemas que requieren atención, pero no una acción inmediata
- **Información**: alertas informativas

#### Política de escalamiento de alertas

Implementa políticas de escalamiento de alertas con herramientas como PagerDuty:

1. **Primera respuesta**: alertar al ingeniero de guardia
2. **Escalamiento 1**: alertar al ingeniero suplente si no hay respuesta después de 15 minutos
3. **Escalamiento 2**: alertar al líder del equipo si no hay respuesta después de 30 minutos
4. **Escalamiento 3**: alertar al gerente si no hay respuesta después de 45 minutos

#### Reducir la fatiga por alertas

Implementa estrategias para reducir la fatiga por alertas:

1. **Agrupación de alertas**: agrupar alertas relacionadas para reducir las notificaciones duplicadas
2. **Filtrado de alertas**: filtrar para entregar solo las alertas importantes
3. **Limitación de frecuencia de alertas**: limitar la frecuencia de las alertas repetidas
4. **Ventanas horarias de alertas**: entregar alertas que no sean críticas para el negocio solo durante el horario laboral

## Análisis y visualización de registros

El análisis y la visualización de registros desempeñan un papel importante en el diagnóstico y la resolución de problemas del clúster de EKS. En esta sección se exploran diversas herramientas y técnicas para analizar y visualizar registros de clústeres de EKS.

![Diagrama de la canalización de análisis y visualización de registros: los registros del plano de control y los servicios de AWS van directamente a CloudWatch Logs; los registros de contenedores y aplicaciones pasan por recopiladores de registros (Fluent Bit, Fluentd, Vector, CloudWatch Agent) a cuatro almacenes (CloudWatch Logs, Amazon OpenSearch, Amazon S3, Grafana Loki), y cada almacén alimenta su herramienta de análisis y visualización asociada: CloudWatch Logs Insights, OpenSearch Dashboards, Athena con QuickSight y Grafana Explore con paneles.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-4.html)

### CloudWatch Logs Insights

Selecciona los grupos de registros reales y un intervalo de tiempo acotado antes de realizar consultas. Los flujos de contenedores, API/audit y authenticator tienen esquemas distintos. Con los valores independientes de Fluent Bit anteriores, el JSON analizado de la aplicación se encuentra bajo data, los metadatos de Kubernetes bajo kubernetes y se conserva el campo original log. Otros recopiladores/configuraciones pueden usar rutas de campos distintas; inspecciona primero un evento almacenado.

#### Consulta de registros de contenedores

Para registros estructurados de aplicaciones con un campo level de tipo cadena:

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message, log
| filter kubernetes.namespace_name = "default"
| filter kubernetes.container_name = "app"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 20
```

Los registros de texto sin formato o con JSON que no se pudo analizar no tendrán data.level. Inspecciona por separado el campo log en lugar de interpretar un resultado vacío como «sin errores».

#### Respuestas de error de API en los registros de auditoría

Cuando el registro de auditoría esté habilitado y los registros contengan responseStatus, usa el código de respuesta numérico en lugar de buscar la palabra Error en todo el texto del servidor de API:

```
fields @timestamp, verb, objectRef.resource, responseStatus.code, user.username
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code >= 400
| sort @timestamp desc
| limit 20
```

Esto encuentra las respuestas registradas en los flujos/intervalo seleccionados de auditoría, no todas las solicitudes de API intentadas. Una respuesta 4xx puede deberse a un problema del emisor o de autorización; no representa automáticamente una interrupción del plano de control. La política de auditoría, las etapas, la ingesta y la retención afectan a la cobertura.

#### Inspeccionar eventos del autenticador

Inspecciona el formato actual de los mensajes del autenticador antes de agregar un filtro de fallos:

```
fields @timestamp, @message
| filter @logStream like /authenticator/
| sort @timestamp desc
| limit 50
```

Una subcadena fija de «autenticación fallida» puede pasar por alto fallos reales o coincidir con texto no relacionado. Compara los campos observados de mensaje/estado y correlaciónalos con las respuestas 401/403 de auditoría. La autenticación y la autorización de Kubernetes son comprobaciones independientes; un solo flujo no constituye evidencia completa de ambas.

#### Recuento de registros por nivel

Para el mismo esquema de aplicación estructurado:

```
fields toupper(data.level) as level, kubernetes.namespace_name
| filter ispresent(data.level)
| stats count(*) as log_records by @log, level, kubernetes.namespace_name
| sort log_records desc
```

Son recuentos de registros, no solicitudes únicas ni tasas de error. Los reintentos, los mensajes repetidos y los registros duplicados del recopilador pueden cambiar el recuento. Analizar un formato supuesto delimitado por espacios no permite clasificar de forma fiable registros JSON arbitrarios de contenedores/plano de control.

Referencias: [detección de campos JSON](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData-discoverable-fields.html), [funciones de consulta](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-operations-functions.html).

### Amazon OpenSearch Service

Usa Amazon OpenSearch Service (anteriormente Amazon Elasticsearch Service) para almacenar, analizar y visualizar registros de tu clúster de EKS:

#### Preparar un dominio de OpenSearch administrado

Usa un dominio preparado mediante el proceso de aprovisionamiento revisado del administrador de plataforma. Elige un motor/versión, capacidad y política de retención compatibles con la carga de trabajo. Para este ejemplo de registro, usa un dominio VPC con una ruta de red aprobada, HTTPS, cifrado en reposo, cifrado entre nodos y control de acceso detallado (FGAC). Inspecciona el dominio real antes de configurar el recopilador:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the owned domain Region}"
: "${OPENSEARCH_DOMAIN:?Set the owned domain name}"
aws opensearch describe-domain --region "$AWS_REGION" \
  --domain-name "$OPENSEARCH_DOMAIN" \
  --query 'DomainStatus.{ARN:ARN,Engine:EngineVersion,Endpoint:Endpoint,EndpointV2:EndpointV2,Endpoints:Endpoints,VPC:VPCOptions,HTTPS:DomainEndpointOptions.EnforceHTTPS,AtRest:EncryptionAtRestOptions.Enabled,NodeToNode:NodeToNodeEncryptionOptions.Enabled,FGAC:AdvancedSecurityOptions.Enabled}'
```

La accesibilidad de red, la política de acceso al dominio y FGAC son capas independientes. La identidad SigV4 del recopilador debe estar permitida por las políticas del dominio/IAM y asignarse a un rol limitado de ingesta de OpenSearch. Mantén separada la administración de la ingesta. Una configuración de base de datos de usuarios internos también puede asignar identidades IAM; no combines credenciales HTTP básicas y credenciales SigV4 en la misma solicitud.

Proporciona credenciales mediante la ruta aprobada de identidad/gestión de secretos. Una contraseña de administrador compartida publicada y una política de acceso público comodín no son una configuración de registro apropiada. Trasladar un dominio público existente a una VPC requiere un dominio nuevo y una migración de datos; no es un cambio de punto de conexión in situ. Cambiar el tipo/dirección de un recurso Terraform existente también requiere un plan de migración de estado/propiedad.

Usa el nombre de host del punto de conexión devuelto en la configuración del recopilador y valida su CA/nombre de host y la ingesta autorizada. La inspección del dominio por sí sola no es una prueba de ingesta ni de preparación para producción.

Referencias: [FGAC de OpenSearch](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html), [dominios VPC y migración](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/vpc.html).

#### Enviar registros a OpenSearch con Fluent Bit

Usa los valores conectados de Fluent Bit, el post-renderer RBAC y la superposición OpenSearch de la sección Registro de contenedores. Proporciona el punto de conexión real que administras, los permisos SigV4 y la asignación FGAC de ingesta. Aplicar un ConfigMap fluent-bit-config no relacionado no modifica una versión de Helm que monta un ConfigMap con otro nombre.

#### Visualización de registros con OpenSearch Dashboards

Crea las siguientes visualizaciones en OpenSearch Dashboards:

1. **Explorador de registros**: búsqueda y filtrado de registros
2. **Paneles**: crear paneles basados en datos de registros
3. **Visualizaciones**: crear gráficos y diagramas basados en datos de registros
4. **Alertas**: configurar alertas según patrones de registros

### Grafana Loki

Grafana Loki es un sistema de agregación de registros que utiliza un enfoque basado en etiquetas similar al de Prometheus:

#### Instalar Loki

Usa la [guía actual de configuración de Loki](../observability/logging/01-loki.md) para una implementación administrada y un cliente compatible, como Alloy. La combinación obsoleta loki-stack/Promtail no es la ruta de instalación actual. Configura el almacenamiento, la autenticación y las políticas de etiquetas/retención antes de enviar registros de producción.

#### Ejemplos de consultas LogQL

Estas consultas presuponen que el recopilador crea etiquetas de flujo para namespace y pod y almacena el JSON de la aplicación con un campo level de nivel superior. Las etiquetas y la extracción de JSON no son automáticamente iguales a la envoltura de datos de CloudWatch/Fluent Bit:

```logql
{namespace="default"} |= "ERROR"

{namespace="default", pod=~"app-.*"} | json | __error__=""

sum by (level) (
  count_over_time(
    {namespace="default"} | json | __error__="" | level=~"INFO|WARN|ERROR" [5m]
  )
)
```

El filtro de errores del analizador JSON va después del análisis. Las consultas de métricas deben excluir los errores de canalización; investiga por separado los registros rechazados o con formato incorrecto para que el filtrado no oculte problemas de recopilación. Los niveles de ejemplo coinciden con el ejemplo de registro estructurado en mayúsculas; adapta el campo y las mayúsculas/minúsculas a los datos reales. Las etiquetas de flujo deben tener cardinalidad acotada; los ID de solicitud y de usuario deben permanecer en campos de registros controlados, no en etiquetas de flujo predeterminadas de cardinalidad alta.

#### Crear paneles de Grafana

Crea paneles de registros en Grafana con la fuente de datos Loki:

1. Inicia sesión en Grafana
2. Haz clic en el icono "+" y selecciona "Dashboard"
3. Haz clic en "Add panel"
4. Selecciona "Loki" como fuente de datos
5. Escribe una consulta LogQL
6. Configura el título y la descripción del panel, y el tipo de visualización
7. Haz clic en "Save"

### AWS CloudTrail

CloudTrail registra la actividad de API de AWS compatible, como la gestión de clústeres, complementos y grupos de nodos de EKS. No sustituye los registros de auditoría de la API de Kubernetes ni los registros de solicitudes de aplicaciones. Primero inspecciona los trails existentes de la organización/cuenta, en lugar de crear un trail duplicado para un bucket no preparado:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region to inspect}"
aws cloudtrail describe-trails --region "$AWS_REGION" --include-shadow-trails \
  --query 'trailList[].{Name:Name,ARN:TrailARN,HomeRegion:HomeRegion,Organization:IsOrganizationTrail,MultiRegion:IsMultiRegionTrail}'
```

Después de seleccionar el trail que administras y su región de origen:

```bash
set -euo pipefail
: "${TRAIL_ARN:?Choose the existing owned trail ARN}"
: "${TRAIL_HOME_REGION:?Use the home Region of the selected trail}"
aws cloudtrail get-trail-status --region "$TRAIL_HOME_REGION" --name "$TRAIL_ARN"
aws cloudtrail get-event-selectors --region "$TRAIL_HOME_REGION" --trail-name "$TRAIL_ARN"
```

Comprueba los errores de registro/entrega y los selectores de eventos. Un trail nuevo necesita su propia política revisada de bucket/entrega, permisos de cifrado/clave, retención y configuración de propiedad. La existencia de un recurso trail no demuestra que los registros lleguen al almacenamiento; crear un trail e iniciar el registro son operaciones distintas.

#### Eventos de administración recientes

El historial de eventos de CloudTrail está disponible sin crear un trail y cubre los eventos de administración de los últimos 90 días en la región seleccionada. Este ejemplo de solo lectura solicita la última hora y limita el lote mostrado a 50 elementos:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region to query}"
python3 - <<'PY'
import datetime
import json
end = datetime.datetime.now(datetime.timezone.utc)
request = {
    "LookupAttributes": [{"AttributeKey": "EventSource", "AttributeValue": "eks.amazonaws.com"}],
    "StartTime": (end - datetime.timedelta(hours=1)).isoformat(),
    "EndTime": end.isoformat(),
}
with open("cloudtrail-lookup.json", "w") as stream:
    json.dump(request, stream, indent=2)
PY
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --cli-input-json file://cloudtrail-lookup.json --max-items 50 --output json
```

Si la CLI devuelve un NextToken, continúa con --starting-token y la misma solicitud/ventana para inspeccionar el resto. Analiza la cadena JSON de CloudTrailEvent para obtener los campos completos de identidad/solicitud/error; Username por sí solo no atribuye completamente al emisor. El historial de eventos no es un plan de retención a largo plazo y no incluye todas las categorías de eventos de datos.

#### CloudTrail Lake para clientes existentes que cumplan los requisitos

CloudTrail Lake dejó de aceptar clientes nuevos el 31 de mayo de 2026 y ahora recibe actualizaciones críticas de errores y seguridad. Los clientes existentes pueden continuar bajo las condiciones documentadas. Los almacenes de datos de eventos de la organización pueden incluir cuentas miembro nuevas; los almacenes de nivel de cuenta existentes no amplían automáticamente la ingesta de Lake a las cuentas agregadas recientemente. CloudTrail Trails, Insights y Aggregated Events siguen siendo compatibles. Para nuevos diseños analíticos, revisa las instrucciones actuales de migración/ingesta de CloudWatch de AWS en lugar de exigir una nueva suscripción a Lake.

Para un almacén existente que cumpla los requisitos, sustituye EVENT_DATA_STORE_ID por el ID real seleccionado en el editor de consultas de Lake. No es un alias arbitrario de tabla, como eks_events. Lo siguiente conserva el intervalo ilustrativo original del 1 al 11 de julio de 2025; no es una consulta ejecutada durante esta auditoría y el almacén debe conservar realmente ese período:

```sql
SELECT eventTime, eventName, userIdentity.arn, requestParameters
FROM EVENT_DATA_STORE_ID
WHERE eventSource = 'eks.amazonaws.com'
  AND eventTime >= '2025-07-01 00:00:00'
  AND eventTime < '2025-07-12 00:00:00'
ORDER BY eventTime DESC
```

El límite superior exclusivo incluye todo el último día sin suponer que las marcas de tiempo solo tienen precisión de segundos enteros. La consulta devuelve la actividad de administración de AWS EKS disponible; los campos de identidad individuales pueden variar según el tipo de emisor. La ejecución de consultas puede generar cargos por el servicio.

Referencias: [historial de eventos de CloudTrail](https://aws.amazon.com/cloudtrail/features/), [cambio de disponibilidad de Lake](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake-service-availability-change.html), [elegir el almacén de datos de eventos](https://docs.aws.amazon.com/help-panel/awscloudtrail/latest/console/query-editor-eds.html).

### Prácticas recomendadas para el análisis de registros

Prácticas recomendadas para analizar eficazmente los registros del clúster de EKS:

#### Registro estructurado

Usa formatos de registro estructurados (por ejemplo, JSON) en tus aplicaciones:

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

#### ID de correlación

El ejemplo JSON de 2025 anterior es ilustrativo, incluida su duración e identificadores ficticios; no es una nueva medición. Los identificadores de usuario/sesión pueden seguir siendo sensibles aunque sean seudónimos. Incluye solo los campos necesarios, con acceso y retención apropiados.

Para una aplicación Java con SLF4J y un backend de registro compatible con MDC, usa un identificador acotado y restaura el contexto anterior para las llamadas anidadas. Este asistente independiente del framework elimina el tipo Request sin definir e incluye la importación UUID:

```java
import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.MDC;

public final class CorrelationContext {
    private static final Pattern SAFE_ID = Pattern.compile("[A-Za-z0-9._-]{1,128}");

    public static void run(String suppliedId, Runnable operation) {
        String correlationId = suppliedId != null && SAFE_ID.matcher(suppliedId).matches()
            ? suppliedId : UUID.randomUUID().toString();
        String previous = MDC.get("correlation_id");
        MDC.put("correlation_id", correlationId);
        try {
            operation.run();
        } finally {
            if (previous == null) {
                MDC.remove("correlation_id");
            } else {
                MDC.put("correlation_id", previous);
            }
        }
    }
}
```

Llama a CorrelationContext.run con el encabezado de solicitud extraído y la operación real. Configura el encoder/patrón para incluir correlation_id; agregar un valor a MDC no cambia automáticamente el formato de registro. Un ID de correlación proporcionado por quien hace la llamada es metadato de rastreo, no autenticación. El contexto MDC está ligado al hilo: propágalo y restáuralo a través de límites de executor/reactivos mediante el mecanismo compatible del backend/framework. El código fuente del asistente se revisó; en este entorno no había un compilador/entorno de ejecución de Java.

Referencias: [API MDC de SLF4J](https://www.slf4j.org/apidocs/org/slf4j/MDC.html), [MDC y grupos de hilos de Logback](https://logback.qos.ch/manual/mdc.html).

#### Uso de niveles de registro

Usa niveles de registro adecuados para indicar la importancia de los registros:

- **ERROR**: errores y excepciones de la aplicación
- **WARN**: problemas potenciales o situaciones inesperadas
- **INFO**: eventos generales de la aplicación
- **DEBUG**: información detallada útil para la depuración
- **TRACE**: información de depuración muy detallada

#### Política de retención de registros

Elige la retención en función de los requisitos operativos, de acceso a datos y conservación aprobados. Reducir la retención puede hacer caducar datos ya almacenados; una duración no es una garantía de cumplimiento ni una conservación inmutable. Para un grupo de registros de CloudWatch que administras, lo siguiente modifica la retención en vez de limitarse a inspeccionar los registros:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the log group Region}"
: "${LOG_GROUP:?Set the reviewed owned log group}"
: "${RETENTION_DAYS:?Choose a supported approved retention value such as 30}"
aws logs put-retention-policy --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" --retention-in-days "$RETENTION_DAYS"
```

Para un bucket de uso general de S3, PutBucketLifecycleConfiguration reemplaza toda la configuración del ciclo de vida. Inspecciona y conserva todas las reglas no relacionadas, los requisitos de versionado/Retención de objetos y el ajuste del tamaño mínimo para las transiciones. Usa el propietario de cuenta previsto para reducir el riesgo de errores de bucket:

```bash
set -euo pipefail
: "${LOG_BUCKET:?Set the owned general purpose S3 bucket}"
: "${ACCOUNT_ID:?Set its expected AWS account ID}"
aws s3api get-bucket-versioning --bucket "$LOG_BUCKET" --expected-bucket-owner "$ACCOUNT_ID"
aws s3api get-bucket-lifecycle-configuration --bucket "$LOG_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" --output json > current-lifecycle.json
```

Si el servicio devuelve específicamente NoSuchLifecycleConfiguration, confirma que no exista configuración e inicializa current-lifecycle.json con {"Rules":[]} para el caso de una política nueva. No interpretes AccessDenied u otra consulta fallida como una política vacía. Revisa las reglas existentes antes de agregar el ejemplo siguiente.

Guarda esta política ilustrativa de objetos actuales a 90 días como log-lifecycle-example.json. Transiciona los registros elegibles a Standard-IA después de 30 días y hace caducar los objetos actuales después de 90 días. Se omite la combinación original de Glacier en el día 60/caducidad en el día 90 porque solo proporciona 30 días nominales en Glacier Flexible Retrieval, cuyo cargo mínimo de almacenamiento es de 90 días.

```json
{
  "Rules": [
    {
      "ID": "example-logs-expiry-90d",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Expiration": {
        "Days": 90
      }
    },
    {
      "ID": "example-logs-standard-ia-30d",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
```

Estas reglas de antigüedad de objetos también se aplican a los objetos ya existentes, y las acciones son asíncronas. La fecha real de transición, la eliminación manual anticipada o la sobrescritura aún pueden generar cargos por duración mínima. Standard-IA tiene un cargo mínimo de 30 días; Glacier Flexible Retrieval, de 90 días; y Deep Archive, de 180 días. Elige cualquier calendario de archivo más prolongado teniendo en cuenta estas restricciones y los costos reales de acceso/recuperación; estas cifras son reglas del servicio, no ahorros medidos.

Para una adición revisada, guarda y ejecuta lo siguiente como merge-log-lifecycle.py. Conserva las reglas existentes y rechaza los ID de ejemplo que entren en conflicto; no resuelve filtros superpuestos ni aprueba la política de retención combinada:

```python
import json

with open("current-lifecycle.json") as stream:
    current = json.load(stream)
with open("log-lifecycle-example.json") as stream:
    example = json.load(stream)
if not isinstance(current.get("Rules"), list) or not isinstance(example.get("Rules"), list):
    raise SystemExit("Both files must contain an explicitly reviewed Rules array")
existing_ids = {rule.get("ID") for rule in current["Rules"] if rule.get("ID")}
new_ids = [rule.get("ID") for rule in example["Rules"]]
if any(not name for name in new_ids) or len(new_ids) != len(set(new_ids)):
    raise SystemExit("Example rules need distinct nonempty IDs")
if existing_ids.intersection(new_ids):
    raise SystemExit("A rule ID already exists; review its owner and changes instead of replacing it")
merged = {"Rules": current["Rules"] + example["Rules"]}
if len(merged["Rules"]) > 1000:
    raise SystemExit("The merged configuration exceeds the lifecycle rule limit")
with open("reviewed-full-lifecycle.json", "w") as stream:
    json.dump(merged, stream, indent=2)
    stream.write("\n")
print("Wrote a candidate preserving existing Rules; review overlaps, retention impact and minimum-size setting")
```



```bash
python3 merge-log-lifecycle.py
```

Inspecciona la propuesta completa y compárala con una configuración reciente del bucket; coordina con otros escritores porque esta API reemplaza la configuración. Desde septiembre de 2024, las configuraciones nuevas o modificadas impiden de forma predeterminada la transición de objetos de menos de 128 KB. Las configuraciones antiguas que no se modifican pueden conservar el comportamiento anterior. Un filtro de tamaño puede anular el valor predeterminado y este ajuste también puede afectar a otras reglas conservadas. Elige explícitamente el valor revisado all_storage_classes_128K o varies_by_storage_class; la respuesta GET expone TransitionDefaultMinimumObjectSize cuando está disponible.

Solo después de revisar toda la configuración y sus efectos en los datos existentes, envía el archivo completo:

```bash
set -euo pipefail
: "${LOG_BUCKET:?Set the reviewed owned bucket}"
: "${ACCOUNT_ID:?Set its expected AWS account ID}"
: "${TRANSITION_MINIMUM_OBJECT_SIZE:?Choose the reviewed minimum-size behavior}"
aws s3api put-bucket-lifecycle-configuration --bucket "$LOG_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" \
  --transition-default-minimum-object-size "$TRANSITION_MINIMUM_OBJECT_SIZE" \
  --lifecycle-configuration file://reviewed-full-lifecycle.json
```

En un bucket con versionado habilitado, la caducidad de la versión actual normalmente crea un marcador de eliminación y deja las versiones no actuales. La caducidad de versiones no actuales, la limpieza de marcadores de eliminación y las restricciones de Retención de objetos/replicación requieren una revisión propia; este ejemplo no afirma que borre todas las versiones ni que vacíe el bucket. Los objetos pequeños que no se transicionen aún pueden cumplir la regla de caducidad.

Durante esta auditoría no se aplicó ninguna política de retención ni acción de ciclo de vida de objetos. Referencias: [API de reemplazo del ciclo de vida](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html), [restricciones de transición](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html), [caducidad/versionado/duración mínima](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html).

## Prácticas recomendadas de supervisión y registro

Exploremos las prácticas recomendadas para implementar eficazmente la supervisión y el registro en clústeres de EKS.

### Prácticas recomendadas de supervisión

#### Supervisión por capas

Supervisa todas las capas del clúster de EKS:

1. **Capa de infraestructura**: instancias EC2, VPC, subredes, grupos de seguridad
2. **Capa del clúster**: plano de control, nodos, Pod, servicios
3. **Capa de aplicación**: rendimiento de las aplicaciones y experiencia del usuario

#### Supervisión de las señales doradas

Concéntrate en las «4 señales doradas» sugeridas en el libro SRE de Google:

1. **Latencia**: tiempo que se tarda en procesar las solicitudes
2. **Tráfico**: número de solicitudes al sistema
3. **Errores**: tasa de solicitudes fallidas
4. **Saturación**: grado de «ocupación» del sistema (por ejemplo, uso de memoria)

#### Supervisión proactiva

Usa las tendencias y anomalías para identificar riesgos en desarrollo. Las previsiones son estimaciones y no garantizan que se prediga un incidente:

1. **Análisis de tendencias**: analiza las tendencias de uso de recursos a lo largo del tiempo
2. **Detección de anomalías**: detecta patrones anormales
3. **Análisis predictivo**: prevé los requisitos futuros de recursos

#### Escalado automatizado

Este HPA ilustrativo presupone un Deployment propio default/my-app, una API de métricas de recursos funcional y solicitudes adecuadas de CPU/memoria. Los objetivos de utilización son porcentajes de las solicitudes, no de la capacidad del nodo ni de los límites del contenedor. Con varias métricas, HPA elige la recomendación con mayor número de réplicas; los fallos de métricas pueden impedir la reducción de escala. Inspecciona las condiciones de HPA y comprueba si el escalado horizontal realmente beneficia a la carga de trabajo:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Supervisión de métricas de negocio

Supervisa las métricas de negocio además de las métricas técnicas:

1. **Actividad de usuarios**: número de usuarios activos, duración de la sesión
2. **Transacciones**: recuento y valor de las transacciones
3. **Tasa de conversión**: tasa de conversión de usuarios, tasa de cancelación
4. **Cumplimiento de SLI/SLO**: mide el indicador y su objetivo definido. Un SLA es un acuerdo que puede incluir consecuencias; cumplir un SLO interno por sí solo no demuestra el cumplimiento contractual.

### Prácticas recomendadas de registro

#### Registro centralizado

Recopila los registros requeridos en destinos aprobados, con controles explícitos de acceso, retención y supervisión de fallos de ingesta:

1. **Formato coherente**: usa un formato de registro coherente en todas las aplicaciones
2. **Repositorio central**: usa un repositorio central de registros, como CloudWatch Logs, OpenSearch o Loki
3. **Reenvío de registros**: usa agentes de reenvío como Fluent Bit o Fluentd

#### Incluir información contextual

Incluye suficiente información contextual en los registros:

1. **Marca de tiempo**: marca de tiempo precisa (se recomienda el formato ISO 8601)
2. **ID de solicitud**: ID único para hacer seguimiento de solicitudes en sistemas distribuidos
3. **Identificadores aprobados**: los ID de usuario/sesión pueden seguir siendo sensibles o identificativos. Incluye solo los identificadores necesarios, con acceso y retención adecuados.
4. **Información del servicio**: nombre, versión e ID de instancia del servicio
5. **Detalles del error**: código de error, mensaje de error, seguimiento de pila

#### Filtrado del nivel de registro

Establece niveles de registro adecuados según el entorno:

1. **Entorno de desarrollo**: usa DEBUG/TRACE deliberadamente durante la investigación y filtra secretos incluso en las pruebas.
2. **Entorno de ensayo**: nivel INFO
3. **Entorno de producción**: elige una cobertura INFO/WARN útil; cualquier período temporal de DEBUG debe tener un volumen/duración acotados y filtrado de datos sensibles.

#### Protección de información sensible

Protege la información sensible en los registros:

1. **Enmascaramiento de información personal**: enmascara la información de identificación personal (PII)
2. **Excluir credenciales**: excluye credenciales como contraseñas, tokens y claves de API
3. **Cifrado**: cifra los registros en reposo y en tránsito

### Prácticas recomendadas para alertas

#### Prioridad de las alertas

Prioriza las alertas para reducir la fatiga por alertas:

1. **P1 (Crítica)**: problemas graves que requieren acción inmediata
2. **P2 (Alta)**: problemas importantes que deben atenderse dentro de la ventana de respuesta acordada del servicio; una urgencia alta no implica automáticamente esperar al horario laboral.
3. **P3 (Media)**: problemas que requieren atención durante el mantenimiento programado
4. **P4 (Baja)**: alertas informativas

#### Agrupación de alertas

Combina los siguientes campos de ruta con la configuración completa de Alertmanager anterior, conservando su receiver y rutas hijas. Agrupa por el contexto del servicio en vez de crear automáticamente un grupo por cada instancia:

```yaml
route:
  group_by: ['cluster', 'namespace', 'alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### Alertas prácticas

Incluye información suficiente en las alertas para facilitar la solución de problemas:

1. **Título claro**: un título que describa claramente el problema
2. **Evidencia e impacto**: describe los síntomas y el impacto observados; etiqueta las causas sospechadas como hipótesis hasta verificarlas.
3. **Pasos para solucionar problemas**: pasos o enlaces para la investigación
4. **Métricas y registros relacionados**: enlaces a métricas y registros útiles para el diagnóstico

#### Pruebas de alertas

Prueba periódicamente el sistema de alertas:

1. **Simulación de alertas**: genera alertas de prueba
2. **Pruebas de escalamiento**: prueba las rutas de escalamiento
3. **Inyección de fallos**: inyecta fallos en entornos controlados

### Prácticas recomendadas para la optimización de costos

#### Optimización del volumen de registros

Optimiza el volumen de registros para reducir costos:

1. **Muestreo**: muestrea solo cuando la cobertura requerida lo permita y documenta las lagunas; conserva las pruebas de auditoría/error exigidas.
2. **Filtrado**: filtra los registros innecesarios
3. **Compresión**: comprime los registros

#### Gestión de la cardinalidad de métricas

Gestiona la cardinalidad de métricas para reducir costos:

1. **Valores de etiquetas acotados**: controla los valores distintos y las combinaciones de etiquetas, no solo la cantidad de nombres de etiquetas.
2. **Agregación**: agrega métricas detalladas en niveles superiores
3. **Resolución de recopilación**: elige intervalos de scraping y agregación que conserven la señal requerida; una recopilación poco granular puede ocultar picos.

#### Jerarquización del almacenamiento

Implementa niveles de almacenamiento rentables:

1. **Almacenamiento activo**: registros recientes y de acceso frecuente
2. **Almacenamiento templado**: registros a los que se accede con menos frecuencia
3. **Almacenamiento frío**: registros archivados

## Solución de problemas y depuración

Exploremos diversas técnicas para solucionar problemas y depurar problemas en clústeres de EKS.

![Diagrama que relaciona tres áreas de solución de problemas de EKS (problemas del clúster, problemas de cargas de trabajo, problemas comunes) con tres familias de herramientas de depuración: herramientas de Kubernetes kubectl, herramientas de AWS y herramientas de diagnóstico de red, con las herramientas kubectl en el centro, usadas en las tres áreas.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-5.html)

### Solución de problemas del clúster

#### Comprobar el estado del clúster

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
LOG_GROUP="/aws/eks/$CLUSTER_NAME/cluster"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Endpoint:endpoint,Logging:logging}'
aws logs describe-log-streams --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" --order-by LastEventTime --descending \
  --max-items 10 --query 'logStreams[].{Name:logStreamName,LastEvent:lastEventTimestamp}'
```

Elige un flujo real devuelto para lecturas acotadas de GetLogEvents, o usa las consultas anteriores. Esta inspección no habilita ni deshabilita el registro. Si falta el registro, usa el procedimiento de configuración revisado por separado y verifica que la actualización haya finalizado.

#### Solución de problemas de nodos

Confirma el contexto de Kubernetes y selecciona el nodo real antes de interpretar una condición. El estado Ready del nodo, su elegibilidad para programación y el estado de la aplicación son señales distintas:

```bash
kubectl config current-context
kubectl get nodes
: "${NODE_NAME:?Choose the node to inspect}"
kubectl describe node "$NODE_NAME"
kubectl get node "$NODE_NAME" -o jsonpath='{.spec.providerID}{"\n"}{.status.nodeInfo.kubeletVersion}{"\n"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}'
```

Para un grupo de nodos administrado, selecciona su nombre real e inspecciona su estado/salud. Esto no se aplica a todos los nodos de Auto Mode, Fargate o autoadministrados:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster}"
: "${AWS_REGION:?Set its Region}"
: "${NODEGROUP_NAME:?Choose the actual managed node group}"
aws eks describe-nodegroup --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Status:status,Version:version,Health:health.issues,Resources:resources}'
```

Usa la ruta aprobada de acceso/diagnóstico del responsable del nodo. La disponibilidad de SSH, el usuario de inicio de sesión y las herramientas de systemd dependen del sistema operativo y de la configuración del nodo; no son características universales de EKS. Auto Mode, Fargate y Bottlerocket requieren los procedimientos aplicables de plataforma/servicio administrado. En una sesión ya autorizada de un nodo EC2 estándar con Linux y systemd, inspecciona los registros acotados de kubelet, el espacio y los inodos:

```bash
sudo journalctl -u kubelet --since "30 minutes ago" --no-pager
df -h
df -i
```

La salida de la consola de EC2 puede ayudar con problemas de arranque en una instancia propia accesible, pero no es un flujo completo de registros de kubelet/aplicaciones. Usa los diagnósticos documentados del entorno de ejecución informado en lugar de suponer que todos los nodos ejecutan Docker.

#### Solución de problemas de Pod

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned namespace}"
: "${POD_NAME:?Choose the actual Pod}"
: "${CONTAINER_NAME:?Choose its application container}"
kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o wide
kubectl describe pod "$POD_NAME" -n "$NAMESPACE"
kubectl events -n "$NAMESPACE" --for="pod/$POD_NAME"
kubectl logs "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" --tail=100
```

Si hay disponible una instancia anterior terminada de ese contenedor, inspecciona también sus registros:

```bash
kubectl logs "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" --previous --tail=100
```

El comando de registros anteriores solo se aplica cuando hay disponible una instancia anterior del contenedor que haya terminado. No recupera Pod antiguos arbitrarios ni registros perdidos con un nodo. Lee conjuntamente los códigos de salida, los últimos motivos de terminación, las sondas y los eventos de recursos; el recuento de reinicios por sí solo no demuestra OOM ni una causa raíz específica. El comando de shell /bin/bash no está disponible en todas las imágenes de aplicaciones.

### Solución de problemas de red

#### Solución de problemas de Service

```bash
set -euo pipefail
: "${NAMESPACE:?Set the service namespace}"
: "${SERVICE_NAME:?Choose the actual Service}"
kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o yaml
kubectl get endpointslices.discovery.k8s.io -n "$NAMESPACE" \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl get pods -n "$NAMESPACE" --show-labels
kubectl get networkpolicies -n "$NAMESPACE"
```

Usa EndpointSlices para inspeccionar los puntos de conexión actuales; la API heredada Endpoints está obsoleta, pero no se ha eliminado en todas partes. Comprueba el selector, las direcciones de los puntos de conexión disponibles, el puerto/targetPort de Service y el protocolo. La resolución de DNS, la disponibilidad de los puntos de conexión y la accesibilidad de red son comprobaciones independientes.

Un reenvío local de puertos puede inspeccionar un puerto seleccionado de Service, pero sigue una ruta de diagnóstico y no demuestra que funcione el tráfico habitual de Pod a Service ni un balanceador de carga. Establece el puerto real de Service:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the service namespace}"
: "${SERVICE_NAME:?Choose the Service}"
: "${SERVICE_PORT:?Choose its service port number}"
kubectl port-forward --address 127.0.0.1 -n "$NAMESPACE" \
  "svc/$SERVICE_NAME" "8080:$SERVICE_PORT"
```

#### Política de red y contexto de diagnóstico

Inspecciona tanto la salida del origen como la entrada del destino, los selectores de espacio de nombres/Pod, el acceso DNS y la CNI que aplica las políticas. Los grupos de seguridad, las rutas, las ACL de red, las políticas de service mesh y TLS pueden constituir capas adicionales. Un sondeo desde un Pod temporal arbitrario puede tener etiquetas, ServiceAccount, grupos de seguridad o sidecars distintos a los de la carga de trabajo que falla.

Para una investigación autorizada, agrega un contenedor de diagnóstico efímero al Pod seleccionado mediante una imagen revisada sin privilegios y compatible con el perfil restringido. Establece DEBUG_IMAGE en un digest aprobado, no en una etiqueta antigua de BusyBox ni en una imagen latest no revisada:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned Pod namespace}"
: "${POD_NAME:?Choose the Pod}"
: "${CONTAINER_NAME:?Choose the target container}"
: "${DEBUG_IMAGE:?Set the reviewed non-root diagnostic image digest}"
kubectl debug "$POD_NAME" -n "$NAMESPACE" -it \
  --image="$DEBUG_IMAGE" --profile=restricted --target="$CONTAINER_NAME" -- sh
```

Esto modifica el Pod al agregarle un contenedor efímero y requiere los permisos RBAC/admisión correspondientes. El registro permanece hasta que se elimina el Pod; salir del shell no elimina la entrada del contenedor efímero. El destino del espacio de nombres de procesos depende de la compatibilidad del entorno de ejecución. La imagen debe contener las herramientas previstas y ejecutarse sin capacidades prohibidas por el perfil. No cambies silenciosamente a un perfil privilegiado para eludir un diagnóstico denegado.

Dentro del shell de diagnóstico, establece también allí los valores de destino; las variables del shell anfitrión no se heredan automáticamente. Si las herramientas están disponibles en la imagen elegida:

```bash
: "${SERVICE_DNS:?Set the intended service DNS name inside this shell}"
: "${SERVICE_PORT:?Set its port inside this shell}"
nslookup "$SERVICE_DNS"
nc -zv "$SERVICE_DNS" "$SERVICE_PORT"
```

Usa el sufijo DNS real del clúster cuando se necesite un FQDN. Una conexión TCP correcta no valida HTTP, la autenticación de la aplicación ni TLS. La captura de paquetes y la depuración de nodos requieren un contexto/privilegios revisados por separado, además de filtros, duración y almacenamiento acotados; un comando tcpdump genérico sin privilegios no se puede usar universalmente. Las capturas pueden contener credenciales o datos de usuario, incluso truncadas. Durante esta auditoría no se inició ningún Pod de diagnóstico, contenedor efímero, captura de paquetes ni sesión de nodo.

### Solución de problemas de registro y supervisión

#### Solución de problemas de Fluent Bit

Para el recopilador independiente instalado en este capítulo, tanto el DaemonSet como el ConfigMap representados son eks-log-collector en logging:

```bash
kubectl get daemonset eks-log-collector -n logging
kubectl get pods -n logging -l app.kubernetes.io/instance=eks-log-collector
kubectl logs -n logging -l app.kubernetes.io/instance=eks-log-collector \
  -c aws-for-fluent-bit --prefix --tail=100
kubectl get configmap eks-log-collector -n logging -o yaml
```

Si el complemento CloudWatch administra la recopilación, inspecciona amazon-cloudwatch y sus recursos reales. Verifica la configuración montada, el acceso a los archivos del nodo, la selección de IRSA/Pod Identity, RBAC, la conectividad de salida y los indicadores de búfer/cola pendiente/descarte. No crees un kube-system/fluent-bit-config no relacionado suponiendo que el recopilador lo lee. Revisa la configuración/salida de registros para detectar datos sensibles antes de compartirla.

#### Solución de problemas de Prometheus

```bash
kubectl get prometheus,alertmanager -n monitoring
kubectl get pods,pvc -n monitoring
kubectl get servicemonitors,prometheusrules -n monitoring
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-kube-prometheus-prometheus 9090:9090
```

Inspecciona `http://127.0.0.1:9090/targets` durante el reenvío. Comprueba el Pod real, el error del destino, la confianza del certificado, el puerto Service con nombre, los selectores de espacio de nombres/etiquetas, las reglas y las muestras recientes. La existencia de un objeto ServiceMonitor no demuestra que Prometheus lo seleccione ni que se pueda acceder a su punto de conexión. Para AMP, inspecciona por separado los fallos/atrasos de remote-write y el espacio de trabajo previsto.

#### Solución de problemas de Grafana

```bash
kubectl get deployment monitoring-grafana -n monitoring
kubectl logs deployment/monitoring-grafana -n monitoring -c grafana --tail=100
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

Abre `http://127.0.0.1:3000` e inspecciona la fuente de datos configurada, las credenciales, el intervalo de tiempo y la consulta. El UID de la fuente de datos Prometheus de la pila local es prometheus; AMG/AMP tiene su complemento y requisitos de IAM propios. Un panel vacío puede deberse a una fuente de datos/etiqueta/intervalo de tiempo incorrectos o a un fallo de ingesta, no a un uso cero.

### Problemas comunes y soluciones

#### Error ImagePullBackOff

Inspecciona el error de descarga, el repositorio/digest de la imagen, la arquitectura, la autorización del registro y la ruta de red del nodo. No siempre se requiere acceso a Internet si se dispone de los puntos de conexión/rutas privadas adecuados. Para ECR, valida la identidad de ejecución de la instancia EC2 o del Pod Fargate y la política del repositorio; IRSA/Pod Identity de la aplicación no es la identidad de descarga de imágenes del kubelet.

Para un registro privado que usa un Secret de descarga, prepara un archivo Docker auth JSON autónomo y protegido mediante el proceso aprobado de credenciales. Un archivo que solo contiene referencias al asistente de credenciales no basta para un imagePullSecret de Kubernetes. Para un Secret nuevo que administres, pasa la ruta del archivo en lugar de una contraseña como argumento del comando:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DOCKER_CONFIG_JSON:?Set the protected self-contained registry auth JSON file}"
kubectl create secret generic regcred -n "$NAMESPACE" \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=".dockerconfigjson=$DOCKER_CONFIG_JSON"
```

Vincúlalo solo a la carga de trabajo prevista que administras. Para un Deployment, este parche estratégico combina la entrada imagePullSecrets con nombre con las entradas existentes. Modifica la plantilla del Pod y activa un despliegue; inspecciona primero el procedimiento de despliegue de su responsable:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DEPLOYMENT:?Set the owned Deployment name}"
kubectl patch deployment "$DEPLOYMENT" -n "$NAMESPACE" --type=strategic \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}}}'
```

Sigue el procedimiento de rotación del responsable para un Secret existente y conserva las demás referencias al registro. No apliques un parche a la ServiceAccount predeterminada del espacio de nombres como solución general. La creación de un Secret por sí sola no verifica el inicio de sesión en el registro, la existencia de la imagen ni que la descarga haya funcionado.

#### Error CrashLoopBackOff

Correlaciona los registros actuales/anteriores del contenedor seleccionado, el código de salida, el motivo de terminación, las sondas de inicio/vida, la configuración y los eventos de recursos. OOMKilled, un fallo de sonda y la salida de la aplicación son causas distintas. La ausencia de una dependencia de inicio o un comando incorrecto también pueden reiniciar un contenedor. Usa el procedimiento de diagnóstico acotado anterior si la imagen normal carece de herramientas; no reinicies/eliminies evidencias antes de recopilarlas.

#### Estado NotReady del nodo

Inspecciona el estado Ready/motivo, la actualización del nodo/lease, las condiciones de presión y los diagnósticos reales del entorno de ejecución/kubelet a través de la ruta de acceso de plataforma correspondiente. El espacio en bytes en disco, el agotamiento de inodos, la conectividad de red/API y los fallos del entorno de ejecución requieren correcciones diferentes. No infieras un activador de reparación automática ni que sea seguro drenar el nodo solo por el estado NotReady mostrado.

#### Problemas de conexión de Service

Sigue la ruta Service-to-EndpointSlice-to-Pod anterior y luego examina los controles de red de origen/destino y el puerto/protocolo de escucha de la aplicación. Prueba desde un contexto de carga de trabajo representativo. Un reenvío de puertos correcto, una consulta DNS o un enlace TCP por sí solos no demuestran que el servicio esté sano de extremo a extremo.

### Herramientas de depuración

Usa kubectl para el estado/eventos de Kubernetes, la CLI de AWS para el estado del servicio administrado correspondiente y herramientas de red aprobadas dentro del contexto para la conectividad. Conserva la evidencia y separa la inspección de las acciones que crean un Pod, cambian una plantilla, drenan un nodo o modifican el registro.

#### Recuperar un resultado de CloudWatch Logs Insights

StartQuery devuelve un ID de consulta asíncrona, no los resultados finales. Este ejemplo de Bash/Python usa segundos de época UTC sin la opción date -v exclusiva de macOS, realiza un número acotado de consultas de estado e imprime resultados solo después de Complete:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the log group Region}"
: "${LOG_GROUP:?Set the owned log group to query}"
python3 - "$LOG_GROUP" <<'PY'
import datetime
import json
import sys
end = datetime.datetime.now(datetime.timezone.utc)
request = {
    "logGroupName": sys.argv[1],
    "startTime": int((end - datetime.timedelta(hours=1)).timestamp()),
    "endTime": int(end.timestamp()),
    "queryString": "fields @timestamp, @message | sort @timestamp desc | limit 50",
}
with open("logs-query-request.json", "w") as stream:
    json.dump(request, stream, indent=2)
PY
STARTED=$(aws logs start-query --region "$AWS_REGION" \
  --cli-input-json file://logs-query-request.json --output json)
QUERY_ID=$(python3 - "$STARTED" <<'PY'
import json
import sys
value = json.loads(sys.argv[1]).get("queryId")
if not isinstance(value, str) or not value:
    raise SystemExit("StartQuery did not return a query ID")
print(value)
PY
)
printf 'Started query %s\n' "$QUERY_ID" >&2
for ((query_attempt = 1; query_attempt <= 20; query_attempt++)); do
  aws logs get-query-results --region "$AWS_REGION" --query-id "$QUERY_ID" \
    --output json > logs-query-result.json
  QUERY_STATE=$(python3 - <<'PY'
import json
with open("logs-query-result.json") as stream:
    print(json.load(stream)["status"])
PY
)
  case "$QUERY_STATE" in
    Complete)
      cat logs-query-result.json
      exit 0
      ;;
    Scheduled|Running)
      if (( query_attempt < 20 )); then sleep 3; fi
      ;;
    *)
      printf 'Query %s ended with status %s; inspect logs-query-result.json\n' "$QUERY_ID" "$QUERY_STATE" >&2
      exit 1
      ;;
  esac
done
printf 'Query %s is still %s; inspect it again or stop it explicitly if no longer needed\n' "$QUERY_ID" "$QUERY_STATE" >&2
exit 2
```

El límite de consultas de estado no es un tiempo de espera del servicio. Una consulta que siga ejecutándose permanece activa; vuelve a inspeccionarla o usa explícitamente StopQuery si ya no la necesitas. Limita el grupo de registros/intervalo de tiempo y los permisos IAM necesarios, y ten en cuenta los costos de consulta. Durante esta auditoría no se ejecutó ninguna consulta de CloudWatch ni operación de depuración del clúster.

## Conclusión

En este documento, exploramos diversas herramientas, técnicas y prácticas recomendadas para la supervisión y el registro en clústeres de Amazon EKS. Implementar una estrategia eficaz de supervisión y registro te permite conocer continuamente el estado del clúster, detectar problemas con anticipación y responder rápidamente cuando ocurren.

Temas principales tratados:

1. **Descripción general de la supervisión y el registro**: importancia y arquitectura de la supervisión y el registro
2. **Registro del plano de control de EKS**: tipos de registros del plano de control y cómo habilitarlos
3. **Registro de contenedores**: recopilación de registros de contenedores con Fluent Bit y CloudWatch Container Insights
4. **Supervisión del clúster**: supervisión del clúster con CloudWatch, Prometheus y Grafana
5. **Alertas y gestión de eventos**: configuración de alertas con CloudWatch alarms y Prometheus Alertmanager
6. **Análisis y visualización de registros**: análisis de registros con CloudWatch Logs Insights, OpenSearch y Grafana Loki
7. **Prácticas recomendadas de supervisión y registro**: prácticas recomendadas para una supervisión y un registro eficaces
8. **Solución de problemas y depuración**: problemas comunes y soluciones

La supervisión y el registro en clústeres de EKS son procesos continuos que deben mejorarse constantemente para satisfacer los requisitos del clúster y las aplicaciones.

## Referencias

- [Prácticas recomendadas de supervisión de Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/eks-observe.html)
- [Prácticas recomendadas de registro de Amazon EKS](https://docs.aws.amazon.com/prescriptive-guidance/latest/amazon-eks-observability-best-practices/logging-best-practices.html)
- [Arquitectura de supervisión de Kubernetes](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)
- [Documentación de Prometheus](https://prometheus.io/docs/introduction/overview/)
- [Documentación de Grafana](https://grafana.com/docs/grafana/latest/)
- [Documentación de Fluent Bit](https://docs.fluentbit.io/manual/)
- [Documentación de Amazon CloudWatch](https://docs.aws.amazon.com/cloudwatch/)
- [Documentación de Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/)

## Cuestionario

Para poner a prueba lo aprendido en este capítulo, prueba el [cuestionario del tema](../quizzes/eks/06-eks-monitoring-logging-quiz.md).
