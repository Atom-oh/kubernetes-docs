# Supervisión y registro de Amazon EKS

> **Última actualización**: October 16, 2026

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

La supervisión y el registro en clústeres de Amazon EKS son importantes por los siguientes motivos:

1. **Visibilidad**: Proporcionan visibilidad del estado, el rendimiento y el comportamiento del clúster
2. **Detección de problemas**: Detectan los problemas pronto, antes de que se vuelvan críticos
3. **Análisis de tendencias**: Identifican tendencias de rendimiento y uso de recursos a lo largo del tiempo
4. **Planificación de capacidad**: Pronostican y planifican los requisitos de recursos
5. **Seguridad y auditoría**: Facilitan las investigaciones y aportan las pruebas que exigen los controles aplicables
6. **Solución de problemas**: Permiten diagnosticar y resolver rápidamente los problemas cuando ocurren

### Arquitectura de supervisión y registro

Una arquitectura completa de supervisión y registro para un clúster de EKS consta de los siguientes componentes:

AWS entrega los registros administrados del plano de control a CloudWatch Logs. Los entornos de ejecución de contenedores escriben archivos de registro CRI; kubelet administra su rotación y el acceso a ellos, mientras que un recopilador de los nodos lee los archivos. Las métricas y los seguimientos utilizan las rutas de recopilación y exportación configuradas.

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Diagrama de arquitectura que muestra los registros del plano de control de EKS, los registros de los Pod y las métricas de los nodos fluyendo a través de Fluent Bit y Prometheus hacia CloudWatch Logs/Metrics, Amazon OpenSearch y Grafana/Alertmanager.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-0.html)
-->

### Estrategia de supervisión y registro

Siga estos pasos para desarrollar una estrategia eficaz de supervisión y registro:

1. **Definir objetivos**: Defina los objetivos y requisitos de supervisión y registro
2. **Identificar métricas y registros**: Identifique las métricas y los registros clave que se deben recopilar
3. **Seleccionar herramientas**: Seleccione herramientas de supervisión y registro que satisfagan los requisitos
4. **Establecer líneas de base**: Establezca líneas de base para el comportamiento normal
5. **Configurar alertas**: Configure alertas para eventos y umbrales importantes
6. **Automatizar**: Automatice los procesos de supervisión y registro en la medida de lo posible
7. **Revisión periódica**: Revise y mejore periódicamente la estrategia de supervisión y registro

## Registro del plano de control de EKS

EKS exporta tipos seleccionados de registros del plano de control administrado a CloudWatch Logs. Un recopilador de los nodos no extrae datos del sistema de archivos del plano de control administrado. La entrega de registros es de mejor esfuerzo; configure el acceso, la retención y la detección de registros faltantes, y luego verifique que los registros hayan llegado realmente.

### Tipos de registros del plano de control

| Tipo | Propósito |
|---|---|
| `api` | Diagnósticos del componente del servidor de API |
| `audit` | Solicitudes de Kubernetes seleccionadas por la directiva y el nivel de auditoría |
| `authenticator` | Diagnósticos de autenticación de IAM de EKS |
| `controllerManager` | Operaciones del administrador de controladores principal |
| `scheduler` | Decisiones y diagnósticos del programador |

El registro de auditoría no constituye un registro incondicional del cuerpo de cada solicitud ni de cada acción de la aplicación. Los registros relacionados con secretos pueden contener solo metadatos, y la directiva excluye algunos eventos. Los registros de API de AWS de CloudTrail y los registros de acceso a datos de las aplicaciones son fuentes de evidencia independientes.

### Inspeccionar y habilitar el registro

Antes de realizar cambios, compruebe la Región, el ARN, la configuración de registro actual y el estado de actualización del clúster que administra. Los cambios de registro requieren la capacidad de direcciones IP de subred documentada e implican cargos por ingesta y almacenamiento de CloudWatch.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```

Para un cambio aprobado, este comando habilita los cinco tipos de registro e inspecciona la actualización devuelta:

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

El comando final comprueba el estado; no espera a que termine la operación. Repita DescribeUpdate hasta que el estado sea Successful o se produzca un error terminal; después, confirme la configuración efectiva y la llegada de registros. Un ID de actualización no demuestra que la operación haya finalizado. Habilitar solo algunos tipos no necesariamente deshabilita otros tipos que ya estén habilitados; cualquier desactivación explícita es una decisión aparte sobre retención y visibilidad.

Con la CLI de eksctl revisada, omitir --approve muestra una vista previa del cambio. Asigne CLUSTER_NAME y AWS_REGION al mismo clúster verificado e inspeccione la vista previa:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler
```

Después de revisar el plan, utilice el comando de aplicación independiente:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

### Consultar los registros del plano de control

Utilice el grupo real `/aws/eks/CLUSTER_NAME/cluster`. Los dos primeros ejemplos son heurísticas de búsqueda de texto para los flujos de los componentes seleccionados, no mediciones completas de la tasa de errores.

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

**Denegaciones de auditoría:** utilice los campos JSON descubiertos en lugar de buscar una cadena literal `responseStatus.code` en el texto JSON sin procesar. Confirme la forma del campo en un evento de muestra.

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code in [401, 403]
| sort @timestamp desc
| limit 20
```

### Retención y gestión de costos

Inspeccione la entrada exacta del grupo en la búsqueda por prefijo devuelta:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws logs describe-log-groups --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/eks/$CLUSTER_NAME/cluster" \
  --query 'logGroups[].{Name:logGroupName,RetentionDays:retentionInDays,KmsKey:kmsKeyId}'
```

Si una política aprobada exige 30 días, el cambio es `aws logs put-retention-policy --region "$AWS_REGION" --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" --retention-in-days 30`. Treinta días es un ejemplo de política, no un requisito de cumplimiento universal. Reducir la retención puede hacer que caduquen pruebas más antiguas; aumentarla no recupera registros eliminados. La retención por sí sola no demuestra la entrega de archivos, su integridad ni el cumplimiento.

### Registro de EKS Capabilities (GitOps, ACK, kro)

La función del 4 de junio de 2026 es compatible: los controladores de ACK, kro y Argo CD capabilities se ejecutan en infraestructura administrada por AWS **fuera del clúster** y pueden entregar registros estructurados de los controladores mediante CloudWatch Vended Logs. Esto utiliza una configuración de entrega por capability, separada de los cinco tipos estándar de registros del plano de control.

| Capability | Tipos de registros |
|---|---|
| ACK | `EKS_CAPABILITY_ACK_LOGS` |
| kro | `EKS_CAPABILITY_KRO_LOGS` |
| Argo CD | `EKS_CAPABILITY_ARGOCD_APPLICATION_LOGS`, `EKS_CAPABILITY_ARGOCD_APPLICATIONSET_LOGS`, `EKS_CAPABILITY_ARGOCD_COMMITSERVER_LOGS`, `EKS_CAPABILITY_ARGOCD_REPOSERVER_LOGS`, `EKS_CAPABILITY_ARGOCD_SERVER_LOGS` |

Recupere el ARN real de la capability antes de configurar su origen de entrega:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CAPABILITY_NAME:?Set the actual capability name}"
aws eks describe-capability --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --capability-name "$CAPABILITY_NAME" \
  --query 'capability.capabilityArn' --output text
```

El propietario configura PutDeliverySource con ese ARN/tipo de registro, PutDeliveryDestination con el destino aprobado y CreateDelivery para conectarlos. Revise las políticas de destino, el cifrado, los permisos entre cuentas y la retención antes de habilitar la entrega.

Los destinos de CloudWatch Logs admiten consultas de Logs Insights. Los destinos de S3 contienen objetos para el flujo de trabajo de S3/Athena seleccionado, y Firehose envía los registros al destino configurado; no se consultan automáticamente mediante CloudWatch Logs Insights. Los registros de ACK incluyen controllerGroup para filtrar por controlador de servicio. Confirme la entrega real y los campos de consulta, y tenga en cuenta los cargos de Vended Logs.

Referencias: [Registro del plano de control de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html), [ejemplos de directivas de auditoría y consultas](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html), [registros de controladores de capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html).

## Registro de contenedores

Los entornos de ejecución de contenedores escriben stdout/stderr en los archivos de registro CRI del nodo. Kubelet administra la rotación y proporciona acceso a los registros de los Pod; un recopilador sigue los archivos y reenvía los registros al backend seleccionado. Un mensaje JSON de una aplicación sigue estando dentro del contenedor CRI y no debe analizarse como si toda la línea de registro del contenedor fuera JSON de Docker.

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Diagrama de arquitectura que muestra stdout/stderr de los contenedores recopilados por kubelet, leídos por un agente de registros y distribuidos a CloudWatch Logs, Amazon OpenSearch y Amazon S3.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-1.html)
-->

### Elegir quién administra el recopilador

El complemento CloudWatch Observability incluye un recopilador de registros de contenedores; si esa es la pila seleccionada, utilice la configuración que administra. El ejemplo independiente de Fluent Bit que aparece a continuación es una alternativa para una canalización de registros administrada por separado. No instale recopiladores que se superpongan y lean los mismos archivos o destinos, salvo que exista un plan explícito para la duplicación y los costos.

### Ejemplo de Fluent Bit conectado

Este ejemplo utiliza AWS chart 0.2.0 con la imagen 3.4.14 (Fluent Bit 5.0.9), cuya versión publicada y configuración se verificaron. Está dirigido a nodos Linux/containerd de EC2 administrados; la afinidad excluye deliberadamente las etiquetas Fargate, Auto Mode e Hybrid de este ejemplo. Esos modos necesitan su propio diseño compatible de recopilación e identidad. El recopilador tolera las taints de los nodos seleccionados, por lo que debe revisar su ubicación y los permisos de admisión de los agentes de la plataforma.

Prepare el espacio de nombres logging, un rol IRSA EKSLogWriter con privilegios mínimos para la cuenta de servicio logging/eks-log-collector y el grupo de registros de CloudWatch correspondiente. Reemplace la cuenta, el rol, la Región y el grupo específico del clúster de forma coherente. Configure el proveedor OIDC de IAM y la confianza audience/subject como se describe en el capítulo de seguridad. El recopilador necesita permisos para escribir flujos de CloudWatch y conectividad regional con STS y el backend. Estos requisitos previos de IAM son independientes del RBAC de Kubernetes para metadatos.

Guárdelo como fluent-bit-values.yaml:

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

Chart 0.2.0 habilita de forma predeterminada la salida nativa cloudWatchLogs y deshabilita la salida anterior cloudWatch. Por lo tanto, establecer solo cloudWatch.region no configura la salida nativa activa. Los valores anteriores configuran la Región y el grupo de la salida real, y conservan el registro completo; log_key enviaría solo el valor seleccionado y podría eliminar el contexto de Kubernetes.

logStreamTemplate utiliza la sintaxis de record-accessor con un prefijo alternativo. logStreamPrefix es un prefijo literal, no una expresión de Kubernetes por registro. El analizador multilínea CRI procesa el contenedor de registros, mientras que Merge_Log coloca los campos JSON de la aplicación bajo data y conserva log. Las anotaciones de las cargas de trabajo no pueden elegir un analizador ni excluirse de la recopilación de este ejemplo.

### Limitar el RBAC de metadatos durante la generación

El ClusterRole amplio del chart publicado incluye nodes/proxy y una regla heredada de PodSecurityPolicy. Este modo de metadatos de API Server establece explícitamente Use_Kubelet Off y necesita permisos de lectura para los Pod/Namespace seleccionados, no acceso de proxy a kubelet. Guarde este post-renderer de Python 3 + PyYAML como fluent-bit-rbac.py. Rechaza identidades inesperadas del chart en lugar de dejar silenciosamente un rol amplio distinto:

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

Para una nueva versión administrada, instale los valores y el renderer juntos:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
chmod +x fluent-bit-rbac.py
helm install eks-log-collector eks/aws-for-fluent-bit \
  --version 0.2.0 --namespace logging --create-namespace \
  -f fluent-bit-values.yaml --post-renderer ./fluent-bit-rbac.py \
  --wait --timeout 5m
```

Conserve el mismo post-renderer revisado en cada actualización y vuelva a validarlo si cambia la versión del chart, la identidad de la versión, el espacio de nombres o el modo de metadatos. La ConfigMap generada se monta en el DaemonSet real; aplicar solamente una ConfigMap sin relación no cambiaría su configuración. El rol de cuenta/IRSA y el grupo de registros son requisitos previos, no recursos creados por este ejemplo del chart.

### Almacenamiento en búfer, rotación y comportamiento ante fallos

Los registros del host se leen en modo de solo lectura; el estado de los puntos de control y del búfer del sistema de archivos se almacena en un directorio distinto, local al nodo. La base de datos tail registra las posiciones y no constituye por sí misma un archivo duradero en el backend. El reemplazo de un nodo puede eliminar ese estado. Read_from_Head On lee el contenido retenido de los archivos si no existe un punto de control, por lo que debe planificar la recuperación de registros atrasados y cómo gestionar duplicados.

Los límites de la cola de salida de 512M y el ajuste de memoria del backlog son asignaciones de ejemplo. Cuando la cola de salida alcanza storage.total_limit_size, Fluent Bit puede descartar sus bloques más antiguos. Skip_Long_Lines On también omite deliberadamente los registros de tamaño excesivo. Los búferes finitos, los reintentos y el estado local del nodo no garantizan una entrega sin pérdida ni exactamente una vez. Supervise los reintentos, los registros descartados, la capacidad del disco y los fallos del destino; valide los límites con respecto a la tasa real de registros y la ventana de interrupción.

### Distribución opcional a OpenSearch

Después de preparar el dominio de VPC administrado y la asignación IAM/FGAC del recopilador, guarde esta superposición como fluent-bit-opensearch-values.yaml y reemplace el nombre de host del punto de conexión. Añada `-f fluent-bit-opensearch-values.yaml` a la misma operación Helm revisada. Si se mantiene habilitado CloudWatch, se enviarán copias a ambos destinos; establezca cloudWatchLogs.enabled=false solo si se elige intencionalmente OpenSearch como único destino.

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

Utilice la verificación del certificado y del nombre de host TLS, además de un diseño fijo y controlado de índices y rotación. Un patrón de índices por Pod puede generar una cantidad excesiva de índices y shards. Generate_ID reduce la indexación duplicada en los reintentos; las salidas independientes y la recuperación de fallos requieren validación de todos modos. Escribir correctamente en un destino no demuestra que se haya entregado al otro.

### Otras pilas de registro

Fluentd sigue siendo una opción cuando una implementación administrada proporciona los complementos de análisis/salida, montajes del host, identidad y configuración TLS necesarios. Un analizador JSON genérico no decodifica un contenedor CRI, y desactivar ssl_verify no es una solución a los errores de certificado. El repositorio del chart heredado de Elastic Helm está archivado; para una implementación de Elastic, utilice la ruta de instalación mantenida del producto/operador.

El chart loki-stack está marcado como obsoleto y el agente Promtail llegó al final de su vida útil el 2 de marzo de 2026. Para Loki, utilice una implementación actual compatible y un cliente compatible, como Alloy, con almacenamiento, controles de acceso y retención explícitos. Consulte la [guía de Loki](../observability/logging/01-loki.md) y la [guía de recopiladores](../observability/logging/05-collectors.md) para conocer la configuración específica. El retiro del agente Promtail no incluye el cliente lambda-promtail, que se mantiene por separado.

### Registros estructurados de aplicaciones

El ejemplo conservado a continuación contiene datos sintéticos de una aplicación; no es una nueva medición ni un registro de esta auditoría. La marca de tiempo sigue siendo el valor ilustrativo original:

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

En la canalización configurada, el registro CRI proporciona la marca de tiempo de transporte y el JSON de la aplicación queda bajo data. Verifique el comportamiento de la zona horaria y del reloj antes de sobrescribir marcas de tiempo con un campo de la aplicación. Los identificadores de usuario/sesión aún pueden ser sensibles o permitir correlaciones; minimícelos y no registre nunca credenciales ni tokens de sesión sin procesar.

El siguiente ejemplo supone la forma de registro de este recopilador. Otros recopiladores pueden usar rutas de campos diferentes:

```text
fields @timestamp, kubernetes.namespace_name, kubernetes.pod_name, data.level, log
| filter kubernetes.namespace_name = "production"
| filter data.level in ["ERROR", "error"]
| sort @timestamp desc
| limit 100
```

La validación abarcó los metadatos publicados del chart y la imagen, la conexión real entre la ConfigMap de Helm y el DaemonSet, los esquemas nativos de Kubernetes y los casos de error del post-renderer. No se instaló ninguna imagen, no se inició el proceso del recopilador, no se enviaron registros a AWS ni se probó el acceso al sistema de archivos de producción. Valide los permisos reales de los nodos, las credenciales IRSA y la entrega de extremo a extremo antes de la implementación.

Referencias: [versión 3.4.14 de la imagen de AWS](https://github.com/aws/aws-for-fluent-bit/releases/tag/v3.4.14), [salida de CloudWatch](https://docs.fluentbit.io/manual/data-pipeline/outputs/cloudwatch), [almacenamiento en búfer de Fluent Bit](https://docs.fluentbit.io/manual/data-pipeline/buffering), [ciclo de vida de Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/).

## Supervisión del clúster

La supervisión eficaz del clúster es esencial para hacer un seguimiento del estado, el rendimiento y el uso de recursos de su clúster de EKS. En esta sección se exploran varias herramientas y técnicas para supervisar clústeres de EKS.

![Diagrama que relaciona las soluciones de supervisión (CloudWatch Container Insights con AMP/AMG, la pila de Prometheus con kube-state-metrics, Node Exporter y Grafana, y el seguimiento con X-Ray/OpenTelemetry) con la telemetría de nivel de clúster, nodo y Pod que cubren en un clúster de EKS.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-2.html)

### CloudWatch Container Insights

El complemento CloudWatch Observability combina las capacidades de Container Insights, recopilación de registros de contenedores y Application Signals. Utilice una sola instalación administrada y evite que su recopilador Fluent Bit se superponga con otro recopilador que lea los mismos archivos. Configure la identidad, el acceso compatible a los nodos y la conectividad con el backend antes de esperar datos.

#### Inspeccionar el clúster y las versiones compatibles del complemento

Para este ejemplo estándar de Linux EC2, prepare el agente EKS Pod Identity correspondiente y un rol de CloudWatch dedicado, cuya confianza se limite a este clúster y a amazon-cloudwatch/cloudwatch-agent. El operador necesita los permisos requeridos para el complemento y las asociaciones, así como permiso para pasar el rol aprobado. Compruebe las versiones de Helm existentes, las anotaciones de ServiceAccount y las asociaciones, además de la lista de complementos de EKS; si ya hay un recopilador, la migración/actualización debe seguir el proceso de quien lo administra.

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

Seleccione una versión compatible y revisada del catálogo en lugar de volver a una versión v5.0.0 fija de ejemplo. Los esquemas de configuración de los complementos dependen de la versión. La renderización de referencia local utilizó aquí Helm chart 6.6.0, cuyo DaemonSet de Fluent Bit utiliza la misma ServiceAccount cloudwatch-agent que la ruta de identidad del agente.

#### Configuración explícita de Auto Monitor

Guarde esto como cloudwatch-config.json para el ejemplo de instalación nueva. Conserva la configuración predeterminada de registros de contenedores y deshabilita la selección automática amplia de cargas de trabajo y los reinicios automáticos hasta que se revise la implementación de la aplicación:

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

Esto controla la selección y los reinicios de Auto Monitor, no todas las fuentes posibles de telemetría. Las anotaciones existentes, los selectores personalizados o las aplicaciones instrumentadas manualmente requieren una revisión independiente. Si dispone localmente de Python 3 y jsonschema, recupere el esquema de la versión seleccionada y compruebe la configuración:

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

#### Crear una nueva instalación administrada

El rol de CloudWatch ya debe tener los permisos necesarios de CloudWatch/traces para las funciones seleccionadas. Lo siguiente vuelve a comprobar el esquema y la versión revisados, rechaza un complemento o una asociación de recopilador ya existentes y evita apropiarse de recursos en conflicto:

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

CreateAddon es asíncrono. Inspeccione el estado y el estado de salud hasta que el complemento esté ACTIVE; después, verifique los Pod del agente/recopilador, los puntos de datos reales de ContainerInsights y los grupos de registros previstos. Una solicitud correcta, el estado ACTIVE o un panel de control por sí solos no demuestran que la ingesta sea completa. El comando DescribeAddon final anterior comprueba el estado; no espera a que termine la operación. Valide los errores y permisos antes de volver a intentarlo; no sobrescriba sin revisión ni elimine la configuración existente para forzar la instalación.

#### Cambios de la versión 5.0.0

El cambio de APM predeterminado del 26 de febrero de 2026 es real: a partir de la versión 5.0.0, Application Signals Auto Monitor queda habilitado de forma predeterminada en las instalaciones y actualizaciones nuevas. monitorAllServices tiene true como valor predeterminado; restartPods tiene false. El alcance abarca Deployments, DaemonSets y StatefulSets compatibles asignados a servicios, excluyendo kube-system y amazon-cloudwatch de forma predeterminada. Las cargas de trabajo nuevas o reiniciadas dentro del alcance pueden instrumentarse sin anotaciones por carga de trabajo; no se garantiza que los Pod que ya estén ejecutándose se reinstrumenten de inmediato.

Elija lenguajes/cargas de trabajo compatibles, revise las integraciones existentes de OpenTelemetry/APM, el muestreo y los costos, y controle cualquier implementación de reinicio. Las exclusiones explícitas tienen prioridad. Container Insights admite configuraciones Linux y Windows, pero Application Signals no es compatible con los nodos Windows de EKS. La recopilación/identidad de Fargate y los nodos Hybrid debe seguir las rutas específicas documentadas para cada plataforma; no deduzca la compatibilidad a partir de un ejemplo genérico de DaemonSet.

#### Métricas, paneles de control y alarmas

Seleccione el clúster real en las vistas de Container Insights de la consola e inspeccione los nombres de las métricas, las dimensiones y los datos recientes publicados. Las métricas de CPU/memoria/sistema de archivos de los nodos describen el uso de los nodos. La utilización de CPU/memoria de los Pod usa los límites de los nodos como denominadores, no las solicitudes de los Pod. Hay agregados de espacio de nombres/servicio/clúster para las métricas documentadas, pero un porcentaje agregado no equivale automáticamente a un valor de utilización ponderado por capacidad para un clúster heterogéneo.

Los paneles ayudan a inspeccionar datos; no crean todas las alarmas ni garantizan la entrega de notificaciones. Los ejemplos de alarmas de CloudWatch que aparecen más adelante utilizan métricas de nodo y Maximum con dimensiones seleccionadas explícitamente. Verifique la disponibilidad de las métricas y configure la alarma y la ruta de entrega adecuadas para la carga de trabajo.

La validación utilizó el chart publicado existente, su configuración de registro predeterminada renderizada y los argumentos de Auto Monitor, además de nueve casos simulados de esquema, propiedad y flujo de errores. El esquema de prueba sintético comprueba el comportamiento del ayudante y no sustituye el esquema en vivo específico de la versión que aparece arriba. Durante esta auditoría no se utilizó ningún complemento, instrumentación de cargas de trabajo, exportación de telemetría ni recurso de AWS.

Referencias: [instalación del complemento CloudWatch y Auto Monitor](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html), [anuncio de APM predeterminado](https://aws.amazon.com/about-aws/whats-new/2026/02/application-performance-monitoring-cloudwatch-eks/), [métricas de Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html).

### Agente de supervisión de nodos de EKS

EKS Node Monitoring Agent publica condiciones de estado del sistema, almacenamiento, redes y aceleradores a nivel de nodo. Se convirtió en software de código abierto el 24 de febrero de 2026 y está incluido en EKS Auto Mode. Para una instalación del complemento administrada por separado, inspeccione la versión real del clúster, los complementos existentes y las versiones compatibles del agente antes de elegir una versión:

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

Instálelo o actualícelo a través de quien administre el complemento existente, con una versión revisada y una configuración de nodos compatible. Un comando para crear un complemento no constituye un procedimiento de actualización para una instalación existente.

El nombre de una condición por sí solo no indica si un nodo está en mal estado. Lea el estado y el motivo, e interprete el significado de cada condición: Ready=False no es lo mismo que MemoryPressure=False.

```bash
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{range .status.conditions[*]}{"  "}{.type}{"="}{.status}{" reason="}{.reason}{"\n"}{end}{end}'
```

La habilitación de la supervisión y la reparación son independientes. Auto Mode tiene habilitada la reparación automática de nodos; los grupos de nodos administrados utilizan nodeRepairConfig y Karpenter utiliza su indicador de función NodeRepair. Inspeccione un grupo de nodos administrado real antes de atribuir al agente un comportamiento de reparación:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${NODEGROUP_NAME:?Set an actual managed node group name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-nodegroup --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Name:nodegroupName,Repair:nodeRepairConfig,Health:health.issues}'
```

La elegibilidad para la reparación depende de la condición, el motivo, el tiempo de espera y las salvaguardas aplicables. En la configuración predeterminada documentada, MemoryPressure y DiskPressure no tienen una acción de reparación automática. No suponga que cada condición informada ni la instalación de un agente probarán que se reemplazará un nodo. La personalización de un agente de código abierto también requiere comprobar la semántica de sus condiciones con la configuración de reparación seleccionada.

Referencias: [anuncio de código abierto](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-eks-node-monitoring-agent-open-source/), [reparación automática de nodos](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html).

### Prometheus y Grafana

Prometheus es una base de datos de series temporales y un sistema de supervisión; Grafana es una herramienta de paneles para visualizar métricas. Puede usar ambas herramientas juntas para supervisar de forma integral su clúster de EKS.

#### Amazon Managed Service for Prometheus y Grafana

AMP almacena y consulta métricas de Prometheus ingeridas; AMG consulta las fuentes de datos configuradas y presenta paneles. Crear cualquiera de los dos espacios de trabajo no implementa automáticamente un scraper, no concede identidad de AWS ni conecta la fuente de datos. Este ejemplo inspecciona espacios de trabajo administrados existentes y amplía la versión de kube-prometheus-stack que aparece a continuación, evitando instalar un segundo Prometheus.

**Identidad de ingesta de AMP y valores**

Prepare un rol IRSA para ServiceAccount monitoring/amp-writer. Su política de confianza debe utilizar el proveedor OIDC de este clúster y las condiciones exactas sub=system:serviceaccount:monitoring:amp-writer y aud=sts.amazonaws.com. Conceda aps:RemoteWrite en el ARN del espacio de trabajo previsto. El proceso de Prometheus debe recibir el token proyectado y tener acceso a STS y al punto de conexión de AMP; RBAC de Kubernetes es una ruta de permisos independiente. No asocie además una identidad de Pod Identity que no corresponda ni claves estáticas de AWS a este ejemplo.

Lo siguiente lee el espacio de trabajo y escribe una superposición para el chart revisado 92.9.0. Acepta los formatos de punto de conexión documentados, con o sin /api/v1/, y añade remote_write una sola vez. Se requiere Python 3; no se crea ningún espacio de trabajo:

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

Combine amp-values.json con monitoring-values.yaml en los valores de instalación/actualización revisados por el responsable. La superposición reemplaza la lista remoteWrite; conserve intencionalmente los destinos y las etiquetas externas existentes. Para una nueva versión, añada -f amp-values.json al comando de instalación que aparece a continuación. Para una versión existente, conserve toda la configuración actual y revise la diferencia renderizada y la implementación antes de aplicar el procedimiento de actualización del responsable. Cambiar ServiceAccount cambia la identidad del Pod de Prometheus. Chart 92.9.0 utiliza un Secret de token explícito de ServiceAccount para la autorización predeterminada de ServiceMonitor del servidor de API/kubelet. Proteja ese Secret y siga su procedimiento de rotación/revocación; es distinto del token IRSA efímero y vinculado a la audiencia. Deshabilitar createTokenSecret sin reemplazar todas las credenciales de monitor dependientes interrumpe la renderización o la autenticación.

Para varias réplicas, configure las etiquetas de deduplicación HA documentadas de AMP y la topología de réplicas en lugar de suponer que los scrape duplicados no tienen costo. Establezca los presupuestos de cardinalidad, retención e ingesta a partir de la carga de trabajo real. Compruebe los fallos/backlog de remote-write y consulte datos recientes en el espacio de trabajo previsto; una implementación correcta de Helm no demuestra que haya ingesta.

**Autenticación de AMG y conexión de fuentes de datos**

```bash
set -euo pipefail
: "${AMG_REGION:?Set the Grafana workspace Region}"
: "${AMG_WORKSPACE_ID:?Set the owned Grafana workspace ID}"
aws grafana describe-workspace --region "$AMG_REGION" \
  --workspace-id "$AMG_WORKSPACE_ID" \
  --query 'workspace.{ID:id,Status:status,Version:grafanaVersion,Endpoint:endpoint,Role:workspaceRoleArn,Authentication:authentication,PermissionType:permissionType}'
```

La autenticación de usuarios del espacio de trabajo (IAM Identity Center/SAML), los permisos de los usuarios de Grafana y el rol IAM de la fuente de datos de AWS del espacio de trabajo son controles distintos. Una cuenta de servicio de Grafana es una identidad para la API HTTP de Grafana; crear una cuenta de servicio ADMIN no crea una fuente de datos de AMP ni concede aps:QueryMetrics. Evite aprovisionar una identidad de API con privilegios amplios solo para ver métricas.

En AMG 12 y versiones posteriores, seleccione el complemento de fuente de datos Amazon Managed Service for Prometheus. En esa versión de AMG se eliminó la compatibilidad con SigV4 del complemento Prometheus Core, y las fuentes de datos de AMP existentes se migran al complemento AMP. Utilice la documentación correspondiente a la versión real del espacio de trabajo. Mediante la configuración aprobada del espacio de trabajo, seleccione la cuenta/Región/espacio de trabajo previsto, configure su identidad de consulta y pruebe una serie conocida. El flujo de configuración documentado de fuentes de datos de AWS utiliza permisos administrados por el servicio; un espacio de trabajo administrado por el cliente necesita su propia configuración IAM revisada, no un cambio automático de propiedad.

El rol de consulta normalmente necesita aps:QueryMetrics, aps:GetSeries, aps:GetLabels y aps:GetMetricMetadata dentro del ámbito del espacio de trabajo; la detección u otras funciones habilitadas pueden requerir acciones adicionales. Su punto de conexión de consulta no es la URL de ingesta remote_write. Si aprovisiona un espacio de trabajo por separado, la CLI utiliza --workspace-name y requiere --account-access-type, configuración de autenticación y de permisos; la automatización IAM administrada por el servicio está vinculada al flujo documentado de la consola. Complete la configuración de identidad, asignación de usuarios y acceso a la red antes de considerar que el espacio de trabajo está listo para usarse.

Referencias: [remote write de AMP](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-onboard-ingest-metrics-existing-Prometheus.html), [complemento AMP de AMG](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-prometheus-data-source.html), [configuración de fuentes de datos de AWS](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-AMP-adding-AWS-config.html). Durante esta auditoría no se utilizó ningún espacio de trabajo, flujo de autenticación ni ingesta de telemetría.

#### Prometheus y Grafana autoadministrados

Este ejemplo utiliza una sola versión administrada de kube-prometheus-stack, que incluye el Prometheus Operator que requieren los ejemplos de ServiceMonitor y PrometheusRule. Un chart independiente de Prometheus no proporciona automáticamente esos CRD/controladores. Inspeccione los operadores, versiones y propiedad de CRD existentes antes de instalar; si la pila ya existe, utilice el procedimiento de actualización de quien la administra.

La línea de base revisada es chart 92.9.0 / Operator 0.94.1, renderizada para EKS 1.36. Supone nodos Linux EC2 estándar y una StorageClass ebs-gp3 cifrada y preparada, con permisos de EBS CSI funcionales. Para Auto Mode u otra implementación de almacenamiento, seleccione la clase compatible real y la ubicación de los nodos. La retención y los tamaños de PVC que aparecen a continuación son asignaciones de ejemplo, no garantías de capacidad medidas.

Prepare el espacio de nombres monitoring y el Secret grafana-admin con claves admin-user/admin-password mediante el proceso aprobado de gestión de secretos. Los valores hacen referencia a ese Secret en lugar de incluir una contraseña compartida en los valores Helm o los argumentos de comandos. Guarde lo siguiente como monitoring-values.yaml:

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

Los sidecars de paneles/fuentes de datos de Grafana solo observan monitoring, con un rol limitado al espacio de nombres. Se accede a su servicio ClusterIP localmente mediante reenvío de puertos. El ejemplo de PVC con una sola réplica utiliza Recreate para evitar escritores simultáneos durante una implementación; por tanto, prevea una interrupción de la interfaz de usuario durante el reemplazo. No es un diseño de Grafana de alta disponibilidad.

El chart omite de forma predeterminada la verificación del certificado del servidor de kubelet. Estos valores, en cambio, requieren una ConfigMap monitoring/kubelet-serving-ca preparada, con ca.crt que contenga la cadena de CA de confianza del servidor de kubelet, y certificados cuyos SAN coincidan con los puntos de conexión consultados. Verifique esa confianza mediante el proceso de administración de certificados del propietario del nodo; la CA del servidor de API de EKS no es automáticamente la CA del servidor de kubelet. Si no dispone de ese requisito previo, resuelva la configuración del certificado antes de habilitar la recopilación. No vuelva silenciosamente a insecureSkipVerify para que un destino fallido parezca estar en buen estado. En esta auditoría no se probó ningún handshake TLS de kubelet.

Los trabajos de scrape de etcd/controller-manager/scheduler/kube-proxy están deshabilitados en este ejemplo porque la configuración no proporciona sus puntos de conexión directos. Habilite un trabajo solo después de configurar su punto de conexión real, accesible y autorizado; las métricas del servidor de API o de CloudWatch son fuentes distintas y no hacen que funcione un destino ServiceMonitor de un componente inexistente.

Para una nueva versión administrada:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm install monitoring prometheus-community/kube-prometheus-stack \
  --version 92.9.0 --namespace monitoring --create-namespace \
  -f monitoring-values.yaml --wait --timeout 10m
```

Que Helm espere no demuestra que todos los recursos creados por el operador, destinos y rutas de notificación funcionen. Inspeccione los recursos generados, la vinculación de los PVC, el estado de los destinos de Prometheus y los datos de métricas:

```bash
kubectl get pods,svc,pvc -n monitoring
kubectl get prometheus,alertmanager -n monitoring
```

Acceda a Grafana en `http://127.0.0.1:3000` mientras se ejecuta este comando, utilizando las credenciales del almacén de secretos aprobado:

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

Proteja la base de datos/PVC de Grafana y las definiciones de paneles exportadas. Utilice el proceso compatible de rotación de credenciales de Grafana; cambiar solo un Secret inicial no demuestra que haya cambiado la contraseña de un usuario existente en la base de datos. No publique la interfaz de usuario con una contraseña de muestra compartida.

La renderización del chart confirma el servicio real de Prometheus monitoring-kube-prometheus-prometheus, el servicio de Grafana monitoring-grafana y el UID de fuente de datos prometheus. Los ServiceMonitor/PrometheusRule personalizados deben coincidir con los selectores release=monitoring que utiliza esta versión. Los manifiestos renderizados y las comprobaciones del esquema son evidencia local; no se utilizó ninguna pila, PVC ni inicio de sesión en un clúster activo.

Referencia: [chart kube-prometheus-stack y guía de actualización](https://github.com/prometheus-community/helm-charts/tree/kube-prometheus-stack-92.9.0/charts/kube-prometheus-stack).

#### Métricas clave de Prometheus

La disponibilidad de métricas depende del destino real de scrape y de sus permisos, no solo del nombre del panel:

- Node exporter proporciona series de CPU, memoria, sistema de archivos y red de los nodos compatibles.
- Kubelet/cAdvisor proporciona métricas de recursos de contenedores; kube-state-metrics proporciona el estado de objetos de Kubernetes, como reinicios y disponibilidad.
- El servidor de API expone métricas autorizadas. Las métricas directas de etcd/controller-manager/scheduler necesitan sus propios puntos de conexión accesibles; la configuración anterior no habilita esos destinos.

Una serie faltante puede indicar un exporter ausente, un scrape fallido, una plataforma no compatible o una métrica que ha cambiado. No significa automáticamente que el uso sea cero ni que el sistema esté en buen estado.

#### Paneles de Grafana útiles

Comience con los paneles de Kubernetes, node-exporter y servidor de API incluidos en la versión revisada de kube-prometheus-stack, y seleccione su UID de fuente de datos prometheus. Que existan ID de paneles de la comunidad no establece por sí solo un contrato compatible de métricas/etiquetas. Inspeccione las consultas, unidades, reglas de grabación requeridas y referencias a fuentes de datos de cada panel importado. Un gráfico sin datos no demuestra que el componente supervisado esté en buen estado.

Los ID de comunidad indicados anteriormente siguen existiendo, pero varios títulos y propósitos implícitos eran inexactos. La verificación del catálogo da las siguientes referencias; no se probó la compatibilidad de importación/ejecución:

| ID | Título real del catálogo | Nota sobre el alcance |
| --- | --- | --- |
| [15661](https://grafana.com/grafana/dashboards/15661-k8s-dashboard-en-20250125/) | Panel de K8S | Vista general de recursos de K8S |
| [1860](https://grafana.com/grafana/dashboards/1860-node-exporter-full/) | Node Exporter Full | Requiere series de node-exporter compatibles |
| [6417](https://grafana.com/grafana/dashboards/6417-kubernetes-cluster-prometheus/) | Kubernetes Cluster (Prometheus) | Vista general del clúster/contenedores; última actualización del catálogo en 2018 |
| [12006](https://grafana.com/grafana/dashboards/12006-kubernetes-apiserver/) | Kubernetes apiserver | Panel de latencia/caché del servidor de API; última actualización del catálogo en 2020 |
| [13770](https://grafana.com/grafana/dashboards/13770-1-kubernetes-all-in-one-cluster-monitoring-kr/) | 1 Kubernetes All-in-one Cluster Monitoring KR | Panel integral en coreano, optimizado para el entorno de máquinas virtuales de su libro |

#### Ejemplos de consultas PromQL

Estos ejemplos coinciden con las etiquetas job y metrics_path de la pila revisada. Conserve la identidad del espacio de nombres para los Pod y la etiqueta cluster cuando exista, especialmente en un espacio de trabajo AMP compartido. Las etiquetas externas de Prometheus se adjuntan al enviar datos externamente; no aparecen automáticamente en todas las series almacenadas localmente. Las agregaciones max agrupan observaciones duplicadas del mismo objeto identificado, no cargas de trabajo distintas. Revise las etiquetas antes de adaptar este patrón.

Porcentaje de CPU no inactiva de los nodos, promediado entre las CPU:

```promql
100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))
```

Los diez Pod principales por bytes de conjunto de trabajo de memoria de contenedor:

```promql
topk(10, sum by (cluster, namespace, pod) (max by (cluster, namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD"})))
```

Contadores de reinicio actuales por UID del Pod; esto no detecta CrashLoopBackOff:

```promql
sum by (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid, container) (kube_pod_container_status_restarts_total{job="kube-state-metrics"}))
```

Porcentaje de sistema de archivos raíz no disponible, excluyendo sistemas de archivos de tamaño cero:

```promql
(100 * (1 - max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_avail_bytes{job="node-exporter",mountpoint="/"}) / max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}))) and on (cluster, instance, device, mountpoint, fstype) (max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}) > 0)
```

Los porcentajes de CPU aquí describen el tiempo no inactivo, la memoria se expresa en bytes y los reinicios son contadores correspondientes al ciclo de vida actual del Pod/contenedor. Utilice rate/increase durante una ventana elegida para consultar cambios en los contadores. El cálculo del sistema de archivos utiliza el espacio disponible y puede incluir el espacio reservado para usuarios ordinarios. Son ejemplos para investigar, no umbrales de alerta universales.

### Seguimiento distribuido con AWS X-Ray

X-Ray sigue siendo un backend de seguimientos compatible. Sus SDK y daemon entraron en una fase de mantenimiento limitada a correcciones de seguridad el 25 de febrero de 2026; el cronograma actual de AWS no publica una fecha de finalización para esa fase. Para instrumentar sistemas nuevos, utilice la integración compatible de OpenTelemetry/ADOT. Un daemon o recopilador de X-Ray no necesita cluster-admin de Kubernetes para enviar seguimientos, y ese rol de Kubernetes no concede permisos de escritura en AWS.

#### Propiedad del recopilador y requisitos previos

Elija una sola parte responsable de la instrumentación/recopilación. La ruta de Application Signals del complemento CloudWatch que aparece arriba es una alternativa; no añada otro agente de SDK a un proceso ya instrumentado sin revisar los tramos duplicados y los conflictos. El ejemplo explícito siguiente utiliza OpenTelemetry Operator 0.158.0 con ADOT Collector 0.50.0 y una canalización solo de seguimientos.

Prepare estas dependencias a través de sus responsables antes de aplicar el recopilador:

- Un Operator funcional con los CRD/webhooks correspondientes. El manifiesto publicado de upstream utiliza cert-manager; siga su ruta documentada de instalación/actualización. El complemento EKS ADOT es otra ruta de administración con un esquema específico de la versión. La versión de Collector no incluye un manifiesto de instalación de Operator.
- Un espacio de nombres dedicado tracing-demo y ServiceAccount adot-traces con confianza IRSA preparada para este clúster, sub=system:serviceaccount:tracing-demo:adot-traces y aud=sts.amazonaws.com. Conceda las acciones de escritura de X-Ray necesarias (PutTraceSegments para esta canalización) y proporcione conectividad con STS/X-Ray. Este recopilador solo OTLP no detecta objetos de Kubernetes ni necesita RBAC de todo el clúster.
- Secret tracing-demo/otel-receiver-tls con tls.crt/tls.key y un certificado de servidor válido para adot-traces-collector.tracing-demo.svc. Monte su CA de confianza en la aplicación. La emisión y renovación del certificado y la recarga/reinicialización del recopilador siguen siendo responsabilidades operativas.
- Una CNI que aplique NetworkPolicy y una salida revisada para la aplicación. El ejemplo permite la entrada desde los Pod de default etiquetados app=my-app; se aplica a todos los Pod del espacio de nombres dedicado tracing-demo. Las etiquetas seleccionan tráfico, pero no autentican una carga de trabajo ni reemplazan los controles RBAC sobre quién puede crear Pod.

Revise las versiones publicadas de [Operator](https://github.com/open-telemetry/opentelemetry-operator/releases/tag/v0.158.0) y [ADOT](https://github.com/aws-observability/aws-otel-collector/releases/tag/v0.50.0) en lugar de aplicar una URL de Collector como si fuera un manifiesto de Operator. El CRD v1beta1 utiliza un objeto en spec.config. Cambie juntos el ejemplo de Región en los campos env/exporter:

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

El Operator deriva el Service receptor ClusterIP del puerto OTLP/HTTP: adot-traces-collector en tracing-demo, TCP 4318. El receptor no valida una identidad de usuario ni una afirmación de autorización empresarial; este ejemplo utiliza TLS de servidor y el límite de red seleccionado. Para un aislamiento más sólido, se puede exigir mTLS o un autenticador de receptor compatible. Configure ambos extremos de forma coherente antes de ampliar el acceso.

La aceptación del recopilador no confirma el almacenamiento. Compruebe el Deployment/Service generado, el handshake TLS, la selección de credenciales de AWS, los fallos del exporter y un seguimiento conocido en X-Ray. El ejemplo en memoria de una sola réplica no es una canalización sin pérdidas ni de alta disponibilidad; dimensione y pruebe los búferes, la contrapresión, el comportamiento de reintento y el manejo de fallos según la carga de trabajo. Una comprobación del esquema CRD no valida toda la configuración de componentes ni demuestra que el recopilador se inicie.

#### Instrumentar la aplicación y propagar el contexto

Para una aplicación Python 3.10+, alinee opentelemetry-sdk==1.44.0 y opentelemetry-exporter-otlp-proto-http==1.44.0 en el archivo de dependencias de la aplicación. Configure cada servicio por separado; un recopilador compartido no debe sobrescribir todos los service.name entrantes con un único valor global. El punto de conexión del exporter HTTP incluye /v1/traces; un punto de conexión gRPC en 4317 es un protocolo/configuración distintos.

```bash
export OTEL_SERVICE_NAME=my-app
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

El archivo de CA debe montarse en el contenedor de la aplicación. Cree una instancia de RequestTracing al iniciar la aplicación, llame a handle_request desde el controlador real del servidor con los nombres de los encabezados entrantes normalizados y una operación que utilice los encabezados salientes proporcionados, y llame a close durante el cierre ordenado. La instrumentación automática del framework/cliente puede encargarse de esos límites; evite instrumentar la misma operación dos veces:

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

Este adaptador muestra la propagación W3C tracecontext y un tramo de servidor; no implementa un servidor HTTP ni todos los tramos del cliente. Las integraciones de borde de AWS que utilizan X-Amzn-Trace-Id necesitan su propagador/puente compatible, en lugar de suponer que la extracción solo W3C lee ese encabezado. El muestreo de cabecera al 10 % es un ejemplo para nuevas raíces que conserva las decisiones de los padres; no puede garantizar que se conserven todos los errores o solicitudes lentas posteriores. El muestreo de cola necesita un diseño aparte que dirija juntos todos los tramos de un seguimiento y cuente con suficiente almacenamiento en búfer.

#### Mapas de seguimiento e investigación

Inspeccione los mapas de seguimiento, las distribuciones de latencia y los detalles de errores/fallos en las vistas de seguimiento de X-Ray/CloudWatch disponibles para la cuenta. Un mapa refleja los tramos instrumentados, muestreados y entregados correctamente; la ausencia de una conexión no demuestra que los servicios nunca se comuniquen. Correlacione los ID de seguimiento con registros y métricas conservados adecuadamente, excluyendo credenciales, datos personales y atributos de solicitud sin límites.

Esta auditoría solo valida las API/esquemas publicados y el comportamiento local sintético. No afirma que se haya implementado un recopilador, activado instrumentación real, exportado seguimientos ni probado la capacidad de producción. Referencias: [cronograma de mantenimiento de X-Ray](https://aws.amazon.com/blogs/mt/aws-x-ray-sdks-daemon-migration-to-opentelemetry/), [administración de EKS ADOT](https://docs.aws.amazon.com/eks/latest/userguide/opentelemetry.html), [exporter de AWS X-Ray](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awsxrayexporter).

### Kubernetes Dashboard

El [proyecto Kubernetes Dashboard](https://github.com/kubernetes-retired/dashboard) está archivado y ya no se mantiene. Sus responsables remiten a Headlamp, bajo Kubernetes SIG UI, para las necesidades actuales de interfaz. No debe utilizarse como ruta de instalación actual la receta antigua de manifiesto sin procesar de Dashboard v2.7 y token de cluster-admin.

Elija una interfaz de usuario mantenida y revise sus requisitos reales de autenticación, TLS, autorización y actualización. Utilice la identidad IAM/RBAC prevista y el alcance de espacios de nombres, siguiendo los ejemplos de access-entry/RBAC del capítulo de seguridad. Como usuario predeterminado, una interfaz de usuario no necesita una ServiceAccount irrestricta de cluster-admin; exponer un token bearer de administrador no sustituye un diseño de acceso.

### Métricas personalizadas y supervisión

Puede implementar soluciones personalizadas para recopilar y supervisar métricas específicas de las aplicaciones:

#### Integración de una biblioteca cliente de Prometheus

Para la API Java de Prometheus client 1.8.0, utilice los paquetes actuales io.prometheus.metrics y dependencias alineadas. En un proyecto Java existente de Gradle:

```groovy
dependencies {
    implementation(platform("io.prometheus:prometheus-metrics-bom:1.8.0"))
    implementation("io.prometheus:prometheus-metrics-core")
    implementation("io.prometheus:prometheus-metrics-exporter-httpserver")
}
```

Guarde el ejemplo como App.java. El método main expone las métricas en el puerto 9400 y espera; el controlador de solicitudes real de la aplicación debe llamar a processRequest con su operación. Iniciar un punto de conexión de métricas por sí solo no cuenta las solicitudes de negocio. No se presenta ningún recuento sintético de solicitudes como tráfico medido:

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

Las API de origen y las coordenadas de dependencias se comprobaron con el cliente publicado; en el entorno de esta auditoría no había compilador/entorno de ejecución de Java disponible, por lo que el ejemplo no se compiló ni ejecutó. Intégrelo con la compilación, el ciclo de vida y la ruta de solicitudes de la aplicación antes de implementarlo. Mantenga etiquetas con valores limitados; los ID de solicitud, los ID de usuario y las URL sin procesar no son dimensiones métricas predeterminadas adecuadas.

#### Recopilación de métricas personalizadas

Suponga que los Pod de la aplicación administrada están en default, tienen la etiqueta app=my-app y realmente sirven /metrics en TCP 9400. El Service selecciona los Pod; ServiceMonitor selecciona las etiquetas del Service y el puerto con nombre. Su etiqueta release=monitoring y namespaceSelector lo conectan a la pila anterior:

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

Verifique los EndpointSlices del Service y el estado de los destinos de Prometheus, permitiendo que solo el recopilador previsto pase por los controles aplicables de red/seguridad. Este ejemplo de métricas HTTP dentro del clúster necesita un límite de red revisado; configure TLS/autenticación si el punto de conexión de métricas lo requiere. ServiceMonitor no instrumenta la aplicación ni crea un servidor de métricas inexistente.

Referencias: [inicio rápido del cliente Java](https://prometheus.github.io/client_java/getting-started/quickstart/), [configuración de Prometheus](https://prometheus.io/docs/prometheus/latest/configuration/configuration/).

#### Paneles personalizados

Cree paneles personalizados en Grafana para visualizar las métricas de la aplicación:

1. Inicie sesión en Grafana
2. Haga clic en el icono "+" y seleccione "Dashboard"
3. Haga clic en "Add panel"
4. Seleccione "Prometheus" como fuente de datos
5. Escriba una consulta PromQL (por ejemplo, `rate(app_requests_total[5m])`)
6. Configure el título, la descripción y el tipo de visualización del panel
7. Haga clic en "Save"
## Alertas y gestión de eventos

Las alertas y la gestión de eventos eficaces son esenciales para detectar y responder rápidamente a los problemas del clúster de EKS. En esta sección se exploran diversas herramientas y técnicas para administrar alertas y eventos en clústeres de EKS.

![Diagrama de arquitectura que muestra métricas y registros de CloudWatch, eventos de AWS, métricas de Prometheus y registros de Loki, y eventos de Kubernetes y aplicaciones enrutados mediante CloudWatch Alarms, EventBridge, Prometheus Alertmanager y un enrutador de eventos a SNS (suscripciones de Email y SQS), Lambda, Slack y PagerDuty, y OpsGenie.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-3.html)

### CloudWatch Alarms

Confirme los puntos de datos recientes y el espacio de nombres, nombre y conjunto de dimensiones exactos de la métrica antes de crear una alarma. Estos ejemplos utilizan los agregados de nodos de ContainerInsights documentados, con solo ClusterName y Maximum. Esto puede revelar un punto crítico en un nodo; no es una medida de utilización ponderada por capacidad de todo el clúster. Utilice dimensiones específicas del nodo para identificar el nodo afectado.

Los umbrales 80/80/85 por ciento y dos períodos de evaluación de cinco minutos son decisiones de política ilustrativas. Que Maximum supere el umbral en dos períodos no significa que haya saturación continua cada segundo durante diez minutos. Los datos faltantes siguen faltando; no demuestran una utilización saludable. Revise la definición de la alarma existente antes de reutilizar su nombre, porque PutMetricAlarm actualiza una alarma existente. Los permisos de notificación, las suscripciones y las pruebas de entrega son requisitos previos independientes.

#### CPU del nodo

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

#### Memoria del nodo

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

Prometheus evalúa las reglas de alerta; Alertmanager agrupa, deduplica y enruta las alertas resultantes. Alertmanager administrado por Operator no utiliza automáticamente una ConfigMap con un nombre arbitrario. La pila revisada utiliza Alertmanager 0.34.0; conecte explícitamente su configuración y los archivos de credenciales.

#### Configuración de Alertmanager

Para el ejemplo de Slack, prepare monitoring/notification-credentials mediante el proceso aprobado de gestión de secretos, con una clave slack-url que contenga la URL real del webhook. Mantenga las credenciales fuera de ConfigMap, del texto del repositorio y de los argumentos de comandos Helm. Guarde esta definición de enrutamiento sin secretos como alertmanager-config.yaml:

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

El webhook debe tener autorización para el destino previsto de Slack; el campo channel no anula los permisos de la aplicación de Slack. Este ejemplo descarta la alerta Watchdog, que siempre está activa en el paquete, para evitar enviar mensajes periódicos a Slack. Un monitor real de pulsos de actividad requiere un receptor independiente configurado y detección externa de ausencia; descartar Watchdog no prueba la entrega de alertas.

Valide el archivo localmente con amtool de la versión correspondiente y, solo para una instalación nueva administrada, cree el Secret de configuración. Un Secret/versión existente requiere el procedimiento de actualización revisado de quien lo administra:

```bash
amtool --no-version-check check-config alertmanager-config.yaml
kubectl create secret generic alertmanager-routing -n monitoring \
  --from-file=alertmanager.yaml=alertmanager-config.yaml
```

Guarde lo siguiente como alertmanager-values.yaml y combínelo con todos los valores revisados de la versión de monitoring. configSecret selecciona el Secret y Operator espera su clave alertmanager.yaml; secrets monta notification-credentials en /etc/alertmanager/secrets/notification-credentials. Antes de la implementación, revise los demás recursos AlertmanagerConfig seleccionados en monitoring con release=monitoring:

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

Compruebe la configuración generada/el estado de recarga y los fallos de notificación, y utilice una alerta de prueba etiquetada a través de un destino de prueba aprobado antes de confiar en las notificaciones de guardia. El análisis local y las pruebas de rutas no demuestran la disponibilidad del Secret, los permisos del webhook, la conectividad SMTP ni la entrega real. El ejemplo del chart con una sola réplica también necesita un diseño de disponibilidad independiente.

#### Configuración de reglas de alerta

La etiqueta de versión de la regla coincide con el selector de Prometheus. Compruebe si hay reglas equivalentes incluidas para evitar alertas duplicadas. CrashLoopBackOff es un motivo de espera de Kubernetes; por sí solo, un umbral de tasa de reinicios no demuestra esa condición. Estos ejemplos requieren las series indicadas de kube-state-metrics y utilizan la identidad del espacio de nombres/Pod UID/contenedor o del nodo:

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

La regla CrashLoopBackOff examina ventanas recientes repetidas de cinco minutos; no cuenta los reinicios. La presión del nodo es una condición observada de kubelet, distinta de un porcentaje de utilización genérico. Las series faltantes/obsoletas pueden impedir que se active una alerta, así que supervise por separado el estado de los scrape y la disponibilidad de métricas. Los umbrales y tiempos de espera son ejemplos, no garantías de respuesta ante incidentes.

### Reglas de eventos de EventBridge

Utilice los nombres de eventos y los campos de carga publicados por el servicio emisor. El catálogo de eventos directos de EKS incluye resultados de creación/actualización/eliminación de complementos, eventos de estado de salud de complementos degradado/restaurado y terminación programada de Fargate. No publica los nombres genéricos EKS Cluster State Change ni EKS Node Group State Change utilizados en los ejemplos antiguos. La actividad de la API de EKS entregada mediante CloudTrail utiliza otro detail-type y otra carga.

#### Eventos directos de estado de los complementos y actividad de API de CloudTrail

Lo siguiente escribe dos alternativas acotadas a la cuenta y Región seleccionadas. Abarcan la actividad coincidente en toda esa cuenta/Región, no solo un clúster. Para acotar más una regla, inspeccione un evento capturado de ese tipo de evento específico y pruebe sus campos documentados; no suponga que todos los eventos incluyen detail.clusterName.

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

El patrón de CloudTrail coincide con eventos de API UpdateClusterVersion y UpdateNodegroupVersion, incluidas las solicitudes de actualización/anulación que correspondan. Un evento de llamada de API de CloudTrail registra un intento o una solicitud aceptada, no la finalización de una actualización asíncrona. Inspeccione los campos de error y correlacione las solicitudes correctas con el ID de actualización y el estado de DescribeUpdate. Asegúrese de que esté configurada la entrega de los eventos de administración relevantes de CloudTrail. La entrega directa y la derivada de CloudTrail son de mejor esfuerzo; utilice también comprobaciones del estado del servicio y supervisión de fallos.

#### Conectar un destino SNS administrado

Prepare un tema SNS estándar, suscripciones confirmadas y un rol de ejecución de destino de EventBridge en la misma cuenta/Región. El rol debe confiar en EventBridge y permitir sns:Publish en el tema previsto, con los permisos KMS aplicables si hay cifrado. El operador necesita los permisos correspondientes para reglas/destinos y permiso para pasar el rol aprobado. EventBridge admite actualmente un rol de ejecución para destinos SNS; las políticas basadas en recursos son una alternativa, no una consecuencia automática de añadir un destino.

Elija un archivo de patrón generado y un nombre nuevo de regla administrada. La comprobación previa rechaza un nombre que ya exista, pero PutRule permite actualizar o crear, por lo que debe coordinar la propiedad y los cambios simultáneos. La regla se crea deshabilitada y un fallo parcial de PutTargets detiene el flujo de trabajo:

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

Revise toda la respuesta del destino, el rol, las suscripciones, la política de reintentos de entrega/mensajes fallidos y un evento capturado representativo. Se puede comprobar la coincidencia del patrón con TestEventPattern; eso no prueba los permisos del destino ni la entrega. Habilítelo solo después de esa revisión:

```bash
aws events enable-rule --region "$AWS_REGION" --event-bus-name default --name "$RULE_NAME"
```

Supervise las invocaciones coincidentes/fallidas y verifique un evento integral aprobado después de la activación. Una regla, un destino o una respuesta correcta de API por sí solos no garantizan la entrega de alertas. Durante esta auditoría no se crearon recursos, eventos ni notificaciones de EventBridge/SNS.

Referencias: [catálogo de eventos de EKS de EventBridge](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html), [permisos de destinos](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html).

### Supervisión de eventos de Kubernetes

Los eventos de Kubernetes ayudan a investigar la programación, las descargas de imágenes, los reinicios y otras actividades de objetos. Son observaciones de mejor esfuerzo y de corta duración que pueden agregar ocurrencias repetidas; no constituyen un registro de auditoría completo y duradero. Inspeccione primero el espacio de nombres previsto:

```bash
kubectl events -n default --types=Warning
kubectl events -n default --types=Warning --watch
```

#### Versión y administración del recopilador

El exporter original de Opsgenie no se mantiene. Su bifurcación activa pasó de resmoio a mustafaakin/kubernetes-event-exporter. La última versión publicada inspeccionada aquí es v1.7, de febrero de 2024, aunque el repositorio tiene actividad de desarrollo posterior. Un repositorio activo o una última etiqueta antigua no demuestran que la imagen de producción actual tenga parches.

La siguiente referencia se comprobó con el código fuente de configuración/watcher de v1.7. Requiere una imagen administrada, revisada y corregida mediante su proceso de compilación, que conserve este contrato de configuración/CLI, se ejecute como UID 65532 y pueda leer la configuración montada con un sistema de archivos raíz de solo lectura. Establezca su digest inmutable durante la renderización; no se proporciona una imagen pública latest ni un digest inventado. En esta auditoría no se ejecutaron la compilación de la imagen, la revisión de vulnerabilidades ni las pruebas de compatibilidad en ejecución.

#### Alcance del espacio de nombres, RBAC y configuración

Este ejemplo se ejecuta en el espacio de nombres monitoring existente, pero observa solo Events de core/v1 en default. omitLookup=true deshabilita las solicitudes GET independientes utilizadas para enriquecer etiquetas/anotaciones del objeto implicado; por lo tanto, el Role solo concede lectura de eventos en default, no lectura con comodines de Secret ni de todos los recursos de API. La elección de líder está deshabilitada para la réplica única, por lo que no se conceden permisos de escritura de lease. Mantenga alineados el espacio de nombres, Role y RoleBinding al adaptar el alcance.

Guárdelo como event-exporter-template.yaml. Contiene un marcador de imagen y debe renderizarse antes de usarse. La regla match apunta a un receptor con nombre; ese receptor emite JSON a stdout, que puede recopilar la canalización de registros de contenedores existente y administrada. Esta configuración exporta solo eventos Warning:

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

Para renderizar, se requiere Python 3 y PyYAML. Inspeccione primero los recursos event-exporter existentes y quién los administra; si ya existe una instalación, utilice el procedimiento de actualización de su responsable:

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

Para una nueva instalación administrada, revise el manifiesto renderizado, la identidad de extracción de imágenes y la conectividad con la API antes de aplicarlo. Recreate evita réplicas superpuestas durante la implementación, pero ocasiona interrupciones; no es un recopilador de alta disponibilidad:

```bash
kubectl apply -f event-exporter-rendered.yaml
kubectl rollout status deployment/event-exporter -n monitoring --timeout=120s
kubectl logs -n monitoring deployment/event-exporter --tail=100
```

#### Pérdida, eventos repetidos y cargas de alertas

El watcher v1.7 inspeccionado procesa notificaciones de adición e ignora las devoluciones de llamada de actualización/eliminación. Por lo tanto, los cambios de recuento/serie de eventos repetidos no son un contador fiable de ocurrencias exportadas. maxEventAgeSeconds=60 es un límite ilustrativo de admisión, no la retención del backend: los eventos más antiguos pueden descartarse durante el inicio, la limitación de velocidad o el tiempo de inactividad. Volver a enumerar/reiniciar también puede repetir observaciones. Seleccione y pruebe el manejo de actualizaciones, el almacenamiento en búfer y un destino duradero necesarios antes de utilizar recuentos de eventos para tomar decisiones operativas.

Inspeccione los contadores de observación/descarte, además de los registros. Este ejemplo vincula el listener de métricas del exporter a loopback; un operador autorizado puede inspeccionarlo mediante un reenvío de puertos local. El endpoint no se añade automáticamente a Prometheus:

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  deployment/event-exporter 2112:2112
```

Lea /metrics en `http://127.0.0.1:2112/metrics` mientras se realiza el reenvío. Una actualización o un registro stdout no confirman por sí solos el almacenamiento en CloudWatch/OpenSearch; verifique el recopilador de registros existente y el destino previsto. Los mensajes de eventos pueden incluir detalles operativos sensibles; revise el acceso, el filtrado y la retención.

No envíe un objeto Event de Kubernetes sin procesar a Alertmanager cambiando solo una URL de webhook. El endpoint /api/v2/alerts actual de Alertmanager espera el esquema de una matriz de alertas; la ruta antigua /api/v1/alerts no es la API actual. Un adaptador específico debe traducir la identidad, las etiquetas, las anotaciones y la semántica de resolución. La ruta de stdout/registros anterior no pretende implementar ese adaptador.

Referencias: [repositorio mantenido del exporter](https://github.com/mustafaakin/kubernetes-event-exporter), [watcher v1.7](https://github.com/mustafaakin/kubernetes-event-exporter/blob/v1.7/pkg/kube/watcher.go), [API v2 de Alertmanager](https://github.com/prometheus/alertmanager/blob/v0.34.0/api/v2/openapi.yaml).

### Integración de canales de notificación

Utilice los receptores compatibles con la versión real de Alertmanager. Los fragmentos siguientes son entradas bajo receivers en alertmanager-config.yaml, no recursos de Kubernetes. Para elegir uno, añada su receptor y cambie route.receiver o una ruta secundaria coincidente por su nombre exacto; luego valide la configuración completa y actualice el Secret seleccionado. Una entrada de receptor sin utilizar no enruta alertas.

#### Integración con Slack

El ejemplo de Slack conectado que aparece arriba utiliza un archivo webhook montado. Confirme el canal autorizado y evite publicar todas las etiquetas/anotaciones de las alertas sin revisar si contienen datos sensibles. No incluya nunca un token o webhook real de Slack en un ejemplo de Provider/ConfigMap guardado en el repositorio.

#### Integración con PagerDuty

Para una integración de Events API v2, prepare la clave pagerduty-routing-key en notification-credentials. routing_key_file hace referencia a la clave de integración, no a un token genérico de la API REST de PagerDuty. Conecte las alertas críticas a través de una ruta secundaria revisada si solo deben generar páginas las alertas críticas:

```yaml
name: pagerduty-notifications
pagerduty_configs:
- routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
  send_resolved: true
  severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
  description: '{{ .CommonLabels.alertname }}'
```

#### Integración con correo electrónico

Reemplace el host/dirección/usuario SMTP de ejemplo reservado por la configuración del servicio de correo aprobado y prepare smtp-password en el mismo Secret de credenciales. Mantenga TLS obligatorio y verifique la confianza del servidor, la autorización del remitente y la entrega. Este es un receptor de correo electrónico de Alertmanager, no un Flux Provider:

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

#### Integración nativa con Amazon SNS

Alertmanager 0.34.0 tiene un receptor SNS nativo; para esa ruta no es necesario un servicio webhook sns-forwarder indefinido. Reemplace la Región/cuenta/tema de ejemplo por el tema estándar administrado. Proporcione a la ServiceAccount real de Alertmanager una identidad de AWS compatible con sns:Publish en ese tema, además de los permisos KMS aplicables a temas cifrados y conectividad de red. El rol de Prometheus o de la aplicación no se convierte automáticamente en el rol de Alertmanager. No se incluyen claves de acceso estáticas de AWS:

```yaml
name: sns-notifications
sns_configs:
- sigv4:
    region: us-west-2
  topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
  send_resolved: true
  subject: 'EKS {{ .CommonLabels.alertname }}'
```

Confirme por separado las suscripciones del tema, las políticas de destino y la entrega de prueba. Los temas FIFO requieren consideraciones adicionales de deduplicación/agrupación; este fragmento está dirigido a un tema estándar. Analizar la configuración del receptor no comprueba IAM ni la publicación en SNS.

Los Providers de notificaciones de Flux enrutan eventos de conciliación de Flux junto con recursos Alert de Flux y orígenes de eventos seleccionados. Por el simple hecho de existir, no reciben alertas arbitrarias de Prometheus ni eventos de Kubernetes. Mantenga ese flujo de trabajo separado de la configuración de receptores de Alertmanager mostrada aquí.

Referencia: [configuración y receptores de Alertmanager](https://prometheus.io/docs/alerting/latest/configuration/).

### Gestión y escalamiento de alertas

Implemente estrategias para gestionar y escalar las alertas de manera eficaz:

#### Niveles de gravedad de alertas

Clasifique las alertas en los siguientes niveles de gravedad:

- **Crítica**: Problemas graves que requieren atención inmediata
- **Advertencia**: Problemas que requieren atención, pero no inmediata
- **Información**: Alertas informativas

#### Política de escalamiento de alertas

Implemente políticas de escalamiento de alertas con herramientas como PagerDuty:

1. **Primera respuesta**: Alertar al ingeniero de guardia
2. **Escalamiento 1**: Alertar al ingeniero suplente si no hay respuesta tras 15 minutos
3. **Escalamiento 2**: Alertar al líder del equipo si no hay respuesta tras 30 minutos
4. **Escalamiento 3**: Alertar al gerente si no hay respuesta tras 45 minutos

#### Reducir la fatiga por alertas

Implemente estrategias para reducir la fatiga por alertas:

1. **Agrupación de alertas**: Agrupar alertas relacionadas para reducir las notificaciones duplicadas
2. **Filtrado de alertas**: Filtrar para entregar solo alertas importantes
3. **Limitación de alertas**: Limitar la frecuencia de alertas repetidas
4. **Ventanas horarias de alertas**: Entregar alertas no críticas para el negocio solo durante el horario laboral
## Análisis y visualización de registros

El análisis y la visualización de registros desempeñan un papel importante en el diagnóstico y la resolución de problemas del clúster de EKS. En esta sección se exploran diversas herramientas y técnicas para analizar y visualizar registros de clústeres de EKS.

![Diagrama de la canalización de análisis y visualización de registros: los registros del plano de control y de los servicios de AWS van directamente a CloudWatch Logs; los registros de contenedores y aplicaciones pasan por recopiladores de registros (Fluent Bit, Fluentd, Vector, CloudWatch Agent) a cuatro almacenes (CloudWatch Logs, Amazon OpenSearch, Amazon S3, Grafana Loki), y cada almacén alimenta su herramienta de análisis y visualización asociada: CloudWatch Logs Insights, OpenSearch Dashboards, Athena con QuickSight y Grafana Explore con paneles.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-4.html)

### CloudWatch Logs Insights

Antes de consultar, seleccione los grupos de registros reales y un intervalo de tiempo acotado. Los flujos de contenedores, API/auditoría y authenticator tienen esquemas diferentes. Con los valores de Fluent Bit independiente anteriores, el JSON de la aplicación analizado está bajo data, los metadatos de Kubernetes están bajo kubernetes y el campo log original se conserva. Otros recopiladores/configuraciones pueden utilizar rutas de campos diferentes; inspeccione primero un evento almacenado.

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

Los registros de texto sin formato o los fallos de análisis JSON no tendrán data.level. Inspeccione por separado su campo log en lugar de interpretar un resultado vacío como «no hay errores».

#### Respuestas de error de API en los registros de auditoría

Cuando el registro de auditoría está habilitado y los registros contienen responseStatus, utilice el código numérico de respuesta en lugar de buscar la palabra Error en todo el texto del servidor de API:

```
fields @timestamp, verb, objectRef.resource, responseStatus.code, user.username
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code >= 400
| sort @timestamp desc
| limit 20
```

Esto encuentra respuestas registradas en los flujos/intervalos de auditoría seleccionados, no todas las solicitudes de API intentadas. Una respuesta 4xx puede deberse a un problema del solicitante/autorización; no implica automáticamente una interrupción del plano de control. La directiva de auditoría, las fases, la ingesta y la retención afectan a la cobertura.

#### Inspeccionar eventos de authenticator

Inspeccione el formato actual de los mensajes de authenticator antes de añadir un filtro de errores:

```
fields @timestamp, @message
| filter @logStream like /authenticator/
| sort @timestamp desc
| limit 50
```

Una subcadena fija como “authentication failed” puede omitir fallos reales o coincidir con texto no relacionado. Compare los campos de mensaje/estado observados y correlaciónelos con las respuestas de auditoría 401/403. La autenticación y la autorización de Kubernetes son comprobaciones distintas; un único flujo no constituye evidencia completa de ambas.

#### Recuento de registros por nivel

Para el mismo esquema de aplicación estructurado:

```
fields toupper(data.level) as level, kubernetes.namespace_name
| filter ispresent(data.level)
| stats count(*) as log_records by @log, level, kubernetes.namespace_name
| sort log_records desc
```

Son recuentos de registros, no solicitudes únicas ni tasas de error. Los reintentos, los mensajes repetidos y los duplicados del recopilador pueden alterar el recuento. Analizar un formato supuesto delimitado por espacios no permite clasificar de forma fiable registros JSON, de contenedores o del plano de control arbitrarios.

Referencias: [descubrimiento de campos JSON](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData-discoverable-fields.html), [funciones de consulta](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-operations-functions.html).

### Amazon OpenSearch Service

Utilice Amazon OpenSearch Service (antes Amazon Elasticsearch Service) para almacenar, analizar y visualizar registros del clúster de EKS:

#### Preparar un dominio OpenSearch administrado

Utilice un dominio preparado mediante el proceso de aprovisionamiento revisado del responsable de la plataforma. Elija la versión de motor, capacidad y política de retención compatibles con la carga de trabajo. Para este ejemplo de registro, utilice un dominio de VPC con una ruta de red aprobada, HTTPS, cifrado en reposo, cifrado entre nodos y control de acceso detallado (FGAC). Inspeccione el dominio real antes de configurar el recopilador:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the owned domain Region}"
: "${OPENSEARCH_DOMAIN:?Set the owned domain name}"
aws opensearch describe-domain --region "$AWS_REGION" \
  --domain-name "$OPENSEARCH_DOMAIN" \
  --query 'DomainStatus.{ARN:ARN,Engine:EngineVersion,Endpoint:Endpoint,EndpointV2:EndpointV2,Endpoints:Endpoints,VPC:VPCOptions,HTTPS:DomainEndpointOptions.EnforceHTTPS,AtRest:EncryptionAtRestOptions.Enabled,NodeToNode:NodeToNodeEncryptionOptions.Enabled,FGAC:AdvancedSecurityOptions.Enabled}'
```

La accesibilidad de red, la política de acceso al dominio y FGAC son capas independientes. La identidad SigV4 del recopilador debe estar permitida por las políticas del dominio/IAM y asignada a un rol limitado de ingesta de OpenSearch. Mantenga separada la administración de la ingesta. Una configuración de base de datos de usuarios internos también puede asignar identidades IAM; no combine credenciales HTTP básicas y credenciales SigV4 en una misma solicitud.

Proporcione credenciales mediante la ruta aprobada de gestión de identidad/secretos. Una contraseña de administrador compartida publicada y una política de acceso público con comodines no son una configuración de registro apropiada. Trasladar un dominio público existente a una VPC requiere un dominio nuevo y migración de datos; no es un cambio de punto de conexión en el mismo dominio. Cambiar el tipo/dirección de recurso de Terraform existente también requiere un plan de migración de estado/propiedad.

Utilice el nombre de host del punto de conexión devuelto en la configuración del recopilador y valide la CA/nombre de host y la ingesta autorizada. Inspeccionar el dominio no constituye una prueba de ingesta ni de disponibilidad para producción.

Referencias: [FGAC de OpenSearch](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html), [dominios de VPC y migración](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/vpc.html).

#### Enviar registros a OpenSearch mediante Fluent Bit

Utilice los valores conectados de Fluent Bit, el post-renderer de RBAC y la superposición de OpenSearch de la sección Registro de contenedores. Proporcione el punto de conexión real administrado, los permisos SigV4 y la asignación FGAC para la ingesta. Aplicar una ConfigMap fluent-bit-config sin relación no altera una versión de Helm que monta una ConfigMap con otro nombre.

#### Visualización de registros con OpenSearch Dashboards

Cree las siguientes visualizaciones en OpenSearch Dashboards:

1. **Explorador de registros**: Búsqueda y filtrado de registros
2. **Paneles**: Crear paneles a partir de datos de registros
3. **Visualizaciones**: Crear gráficos a partir de datos de registros
4. **Alertas**: Configurar alertas basadas en patrones de registros

### Grafana Loki

Grafana Loki es un sistema de agregación de registros que utiliza un enfoque basado en etiquetas similar al de Prometheus:

#### Instalación de Loki

Utilice la [guía actual de configuración de Loki](../observability/logging/01-loki.md) para una implementación administrada y un cliente compatible, como Alloy. La combinación obsoleta de loki-stack/Promtail no es la ruta de instalación actual. Configure el almacenamiento, la autenticación y las políticas de etiquetas/retención antes de enviar registros de producción.

#### Ejemplos de consultas LogQL

Estas consultas suponen que el recopilador crea etiquetas de flujo namespace y pod, y almacena el JSON de la aplicación con un campo level de nivel superior. Las etiquetas y la extracción de JSON no son automáticamente idénticas al contenedor de datos de CloudWatch/Fluent Bit:

```logql
{namespace="default"} |= "ERROR"

{namespace="default", pod=~"app-.*"} | json | __error__=""

sum by (level) (
  count_over_time(
    {namespace="default"} | json | __error__="" | level=~"INFO|WARN|ERROR" [5m]
  )
)
```

El filtro de error del analizador JSON se aplica después del análisis. Las consultas de métricas deben excluir los errores de canalización; investigue por separado los registros rechazados o malformados para que el filtrado no oculte problemas de recopilación. Los niveles del ejemplo coinciden con la muestra de registros estructurados en mayúsculas; adapte el campo/las mayúsculas y minúsculas a los datos reales. Las etiquetas de flujo deben tener valores limitados; los ID de solicitud y usuario deben estar en campos de registro con controles adecuados, no en etiquetas de flujo predeterminadas de alta cardinalidad.

#### Creación de paneles de Grafana

Cree paneles de registros en Grafana utilizando la fuente de datos Loki:

1. Inicie sesión en Grafana
2. Haga clic en el icono "+" y seleccione "Dashboard"
3. Haga clic en "Add panel"
4. Seleccione "Loki" como fuente de datos
5. Escriba una consulta LogQL
6. Configure el título, la descripción y el tipo de visualización del panel
7. Haga clic en "Save"

### AWS CloudTrail

CloudTrail registra la actividad de API de AWS compatible, como la administración de clústeres, complementos y grupos de nodos de EKS. No reemplaza los registros de auditoría de la API de Kubernetes ni los registros de solicitudes de la aplicación. Primero inspeccione los trails de organización/cuenta existentes, en lugar de crear uno duplicado que apunte a un bucket no preparado:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region to inspect}"
aws cloudtrail describe-trails --region "$AWS_REGION" --include-shadow-trails \
  --query 'trailList[].{Name:Name,ARN:TrailARN,HomeRegion:HomeRegion,Organization:IsOrganizationTrail,MultiRegion:IsMultiRegionTrail}'
```

Después de seleccionar el trail administrado y su Región principal:

```bash
set -euo pipefail
: "${TRAIL_ARN:?Choose the existing owned trail ARN}"
: "${TRAIL_HOME_REGION:?Use the home Region of the selected trail}"
aws cloudtrail get-trail-status --region "$TRAIL_HOME_REGION" --name "$TRAIL_ARN"
aws cloudtrail get-event-selectors --region "$TRAIL_HOME_REGION" --trail-name "$TRAIL_ARN"
```

Compruebe los errores de registro/entrega y los selectores de eventos. Un trail nuevo necesita su propia configuración revisada de bucket/entrega, permisos de cifrado/clave, retención y propiedad. La existencia del recurso trail no demuestra que los registros lleguen al almacenamiento; crear un trail e iniciar el registro son operaciones distintas.

#### Eventos de administración recientes

El historial de eventos de CloudTrail está disponible sin crear un trail y abarca los últimos 90 días de eventos de administración de la Región seleccionada. Este ejemplo de solo lectura solicita la última hora y limita el lote mostrado a 50 elementos:

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

Si la CLI devuelve un NextToken, continúe con --starting-token y la misma solicitud/ventana para inspeccionar el resto. Analice la cadena JSON CloudTrailEvent para obtener todos los campos de identidad/solicitud/error; Username por sí solo no atribuye completamente al solicitante. El historial de eventos no es un plan de retención a largo plazo y no incluye todas las categorías de eventos de datos.

#### CloudTrail Lake para clientes existentes que cumplen los requisitos

CloudTrail Lake dejó de aceptar clientes nuevos el 31 de mayo de 2026 y ahora recibe actualizaciones críticas de errores/seguridad. Los clientes existentes pueden continuar bajo las condiciones documentadas. Los almacenes de datos de eventos de organización pueden incluir cuentas miembro nuevas; los almacenes existentes a nivel de cuenta no amplían automáticamente la ingesta de Lake a las cuentas añadidas recientemente. CloudTrail Trails, Insights y Aggregated Events siguen siendo compatibles. Para nuevos diseños analíticos, revise las directrices actuales de AWS para la migración/ingesta de CloudWatch en lugar de exigir un nuevo registro en Lake.

Para un almacén existente que cumpla los requisitos, reemplace EVENT_DATA_STORE_ID por el ID real seleccionado en el editor de consultas de Lake. No es un alias de tabla arbitrario como eks_events. Lo siguiente conserva el intervalo ilustrativo original del 1 al 11 de julio de 2025; no es una consulta ejecutada durante esta auditoría y el almacén debe conservar realmente ese período:

```sql
SELECT eventTime, eventName, userIdentity.arn, requestParameters
FROM EVENT_DATA_STORE_ID
WHERE eventSource = 'eks.amazonaws.com'
  AND eventTime >= '2025-07-01 00:00:00'
  AND eventTime < '2025-07-12 00:00:00'
ORDER BY eventTime DESC
```

El límite superior exclusivo incluye el último día completo sin suponer que las marcas de tiempo tengan solo precisión de segundos enteros. La consulta devuelve la actividad de administración de AWS de EKS disponible; los campos de identidad pueden variar según el tipo de solicitante. Ejecutar consultas puede implicar costos del servicio.

Referencias: [historial de eventos de CloudTrail](https://aws.amazon.com/cloudtrail/features/), [cambio de disponibilidad de Lake](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake-service-availability-change.html), [selección del almacén de datos de eventos](https://docs.aws.amazon.com/help-panel/awscloudtrail/latest/console/query-editor-eds.html).

### Prácticas recomendadas de análisis de registros

Prácticas recomendadas para analizar eficazmente los registros del clúster de EKS:

#### Registro estructurado

Utilice formatos de registro estructurados (por ejemplo, JSON) en sus aplicaciones:

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

El ejemplo JSON de 2025 anterior es ilustrativo, incluidos su duración e identificadores inventados; no es una nueva medición. Los identificadores de usuario/sesión pueden seguir siendo sensibles aunque sean seudónimos. Incluya solo los campos necesarios, con el acceso y la retención adecuados.

Para una aplicación Java con SLF4J y un backend de registro compatible con MDC, utilice un identificador de valores limitados y restablezca el contexto anterior para las llamadas anidadas. Este ayudante independiente del framework elimina el tipo Request indefinido e incluye la importación de UUID:

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

Llame a CorrelationContext.run con el encabezado de solicitud extraído y la operación real. Configure el encoder/patrón para incluir correlation_id; poner un valor en MDC no cambia automáticamente el formato del registro. Un ID de correlación proporcionado por el solicitante es metadato de seguimiento, no autenticación. El contexto MDC está vinculado al hilo: propáguelo y restáurelo a través de los límites executor/reactive utilizando el mecanismo compatible del framework/backend. El código fuente del ayudante se revisó; en este entorno no había compilador/entorno de ejecución de Java disponible.

Referencias: [API MDC de SLF4J](https://www.slf4j.org/apidocs/org/slf4j/MDC.html), [MDC de Logback y grupos de hilos](https://logback.qos.ch/manual/mdc.html).

#### Uso de niveles de registro

Utilice niveles de registro adecuados para indicar la importancia de los registros:

- **ERROR**: Errores y excepciones de la aplicación
- **WARN**: Problemas potenciales o situaciones inesperadas
- **INFO**: Eventos generales de la aplicación
- **DEBUG**: Información detallada útil para depurar
- **TRACE**: Información de depuración muy detallada

#### Política de retención de registros

Elija la retención según los requisitos aprobados de operación, acceso a datos y preservación. Reducir la retención puede hacer que caduquen datos ya almacenados; una duración no garantiza el cumplimiento ni constituye una conservación inmutable. Para un grupo de registros de CloudWatch administrado, lo siguiente cambia la retención, no se limita a inspeccionar los registros:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the log group Region}"
: "${LOG_GROUP:?Set the reviewed owned log group}"
: "${RETENTION_DAYS:?Choose a supported approved retention value such as 30}"
aws logs put-retention-policy --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" --retention-in-days "$RETENTION_DAYS"
```

Para un bucket de uso general de S3, PutBucketLifecycleConfiguration reemplaza toda la configuración del ciclo de vida. Inspeccione y conserve todas las reglas no relacionadas, los requisitos de control de versiones/Bloqueo de objetos y la configuración mínima de tamaño para las transiciones. Utilice el propietario de cuenta esperado para reducir el riesgo de equivocarse de bucket:

```bash
set -euo pipefail
: "${LOG_BUCKET:?Set the owned general purpose S3 bucket}"
: "${ACCOUNT_ID:?Set its expected AWS account ID}"
aws s3api get-bucket-versioning --bucket "$LOG_BUCKET" --expected-bucket-owner "$ACCOUNT_ID"
aws s3api get-bucket-lifecycle-configuration --bucket "$LOG_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" --output json > current-lifecycle.json
```

Si el servicio devuelve específicamente NoSuchLifecycleConfiguration, confirme que la configuración no existe e inicialice current-lifecycle.json con {"Rules":[]} para el caso de una política nueva. No interprete AccessDenied ni otra consulta fallida como una política vacía. Revise las reglas existentes antes de añadir el ejemplo siguiente.

Guarde esta política ilustrativa de objetos actuales a 90 días como log-lifecycle-example.json. Traslada los registros elegibles a Standard-IA después de 30 días y elimina los objetos actuales después de 90 días. La combinación original de Glacier en el día 60 y eliminación en el día 90 solo deja 30 días nominales en Glacier Flexible Retrieval, cuyo cargo mínimo de almacenamiento es de 90 días; se omite esa transición en este ejemplo de 90 días.

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

Estas reglas se basan en la antigüedad de los objetos, incluidos los que ya existen, y las acciones son asíncronas. El momento real de la transición, la eliminación manual anticipada o la sobrescritura pueden seguir generando cargos de duración mínima. Standard-IA tiene un cargo mínimo de 30 días; Glacier Flexible Retrieval, de 90 días; y Deep Archive, de 180 días. Al elegir un cronograma de archivado más largo, tenga en cuenta esas restricciones y los costos reales de acceso/recuperación; estos valores son reglas del servicio, no ahorros medidos.

Para una incorporación revisada, guarde y ejecute lo siguiente como merge-log-lifecycle.py. Conserva las Rules existentes y rechaza los ID de ejemplo que ya existan; no resuelve filtros superpuestos ni aprueba la política de retención combinada:

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

Inspeccione toda la configuración candidata y compárela con una configuración reciente del bucket; coordine con otros escritores porque esta API reemplaza la configuración. Desde septiembre de 2024, las configuraciones creadas/modificadas recientemente impiden de forma predeterminada las transiciones de objetos de menos de 128 KB. Las configuraciones antiguas sin modificar pueden conservar el comportamiento anterior. Un filtro de tamaño puede anular el valor predeterminado, y esta configuración también puede afectar a otras reglas que se conserven. Elija explícitamente el valor all_storage_classes_128K o varies_by_storage_class que se haya revisado; la respuesta GET muestra TransitionDefaultMinimumObjectSize cuando está disponible.

Solo después de revisar toda la configuración y su efecto en los datos existentes, envíe el archivo completo:

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

En un bucket con control de versiones habilitado, la eliminación de la versión actual normalmente crea un marcador de eliminación y deja las versiones no actuales. La eliminación de versiones no actuales, la limpieza de marcadores de eliminación y las restricciones de Bloqueo de objetos/replicación requieren su propia revisión; este ejemplo no afirma que elimine todas las versiones ni que vacíe el bucket. Los objetos pequeños que no se trasladan también pueden coincidir con la regla de eliminación.

Durante esta auditoría no se aplicó ninguna política de retención ni acción de ciclo de vida de objetos. Referencias: [API de reemplazo de la configuración del ciclo de vida](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html), [restricciones de transición](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html), [caducidad/control de versiones/duración mínima](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html).

## Prácticas recomendadas de supervisión y registro

Exploremos las prácticas recomendadas para implementar eficazmente la supervisión y el registro en clústeres de EKS.

### Prácticas recomendadas de supervisión

#### Supervisión multicapa

Supervise todas las capas del clúster de EKS:

1. **Capa de infraestructura**: Instancias EC2, VPC, subredes, grupos de seguridad
2. **Capa de clúster**: Plano de control, nodos, Pod, servicios
3. **Capa de aplicación**: Rendimiento de las aplicaciones, experiencia de usuario

#### Supervisión de señales doradas

Céntrese en las «4 señales doradas» sugeridas en el libro SRE de Google:

1. **Latencia**: Tiempo necesario para procesar solicitudes
2. **Tráfico**: Número de solicitudes al sistema
3. **Errores**: Tasa de solicitudes fallidas
4. **Saturación**: Nivel de ocupación del sistema (por ejemplo, uso de memoria)

#### Supervisión proactiva

Utilice tendencias y anomalías para identificar riesgos emergentes. Los pronósticos son estimaciones y no garantizan que se prediga un incidente:

1. **Análisis de tendencias**: Analizar las tendencias de uso de recursos a lo largo del tiempo
2. **Detección de anomalías**: Detectar patrones anormales
3. **Análisis predictivo**: Pronosticar requisitos futuros de recursos

#### Escalado automatizado

Este HPA ilustrativo supone un Deployment default/my-app administrado, una API de métricas de recursos funcional y solicitudes de CPU/memoria adecuadas. Los objetivos de utilización son porcentajes de las solicitudes, no de la capacidad del nodo ni de los límites del contenedor. Con varias métricas, HPA elige la recomendación de mayor número de réplicas; los fallos de métricas pueden impedir una reducción de escala. Inspeccione las condiciones de HPA y pruebe si el escalado horizontal realmente beneficia a la carga de trabajo:

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

Supervise métricas de negocio, además de métricas técnicas:

1. **Actividad de usuarios**: Número de usuarios activos, duración de las sesiones
2. **Transacciones**: Recuento de transacciones, valor de las transacciones
3. **Tasa de conversión**: Tasa de conversión de usuarios, tasa de cancelación
4. **Cumplimiento de SLI/SLO**: Mida el indicador y el objetivo definido. Un SLA es un acuerdo que puede incluir consecuencias; cumplir un SLO interno por sí solo no demuestra el cumplimiento contractual.

### Prácticas recomendadas de registro

#### Registro centralizado

Recopile los registros necesarios en destinos aprobados, con controles explícitos de acceso, retención y supervisión de fallos de ingesta:

1. **Formato uniforme**: Utilice un formato de registro uniforme en todas las aplicaciones
2. **Repositorio central**: Utilice un repositorio central de registros, como CloudWatch Logs, OpenSearch o Loki
3. **Reenvío de registros**: Utilice agentes de reenvío de registros, como Fluent Bit o Fluentd

#### Incluir información de contexto

Incluya información de contexto suficiente en los registros:

1. **Marca de tiempo**: Marca de tiempo precisa (se recomienda el formato ISO 8601)
2. **ID de solicitud**: ID único para el seguimiento de solicitudes en sistemas distribuidos
3. **Identificadores aprobados**: Los ID de usuario/sesión pueden seguir siendo sensibles o identificativos. Incluya solo los identificadores necesarios, con el acceso y la retención adecuados.
4. **Información del servicio**: Nombre del servicio, versión, ID de instancia
5. **Detalles del error**: Código de error, mensaje de error, seguimiento de pila

#### Filtrado por nivel de registro

Establezca niveles de registro adecuados según el entorno:

1. **Entorno de desarrollo**: Utilice DEBUG/TRACE deliberadamente durante la investigación, con filtrado de secretos incluso en las pruebas.
2. **Entorno de ensayo**: Nivel INFO
3. **Entorno de producción**: Elija una cobertura INFO/WARN útil; cualquier período temporal de DEBUG necesita límites de volumen/duración y filtrado de datos sensibles.

#### Protección de la información sensible

Proteja la información sensible de los registros:

1. **Enmascaramiento de PII**: Enmascare la información de identificación personal (PII)
2. **Excluir credenciales**: Excluya credenciales como contraseñas, tokens y claves de API
3. **Cifrado**: Cifre los registros en reposo y en tránsito

### Prácticas recomendadas de alertas

#### Prioridad de alertas

Priorice las alertas para reducir la fatiga por alertas:

1. **P1 (Crítica)**: Problemas graves que requieren atención inmediata
2. **P2 (Alta)**: Problemas importantes que deben atenderse dentro de la ventana de respuesta acordada del servicio; una urgencia alta no implica automáticamente esperar al horario laboral.
3. **P3 (Media)**: Problemas que requieren atención durante el mantenimiento programado
4. **P4 (Baja)**: Alertas informativas

#### Agrupación de alertas

Combine los siguientes campos de ruta con la configuración completa de Alertmanager anterior, conservando su receptor y las rutas secundarias. Agrupe por contexto del servicio en lugar de crear automáticamente un grupo por instancia:

```yaml
route:
  group_by: ['cluster', 'namespace', 'alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### Alertas prácticas

Incluya información suficiente en las alertas para solucionar problemas:

1. **Título claro**: Título que describa claramente el problema
2. **Evidencia e impacto**: Describa los síntomas y el impacto observados; señale como hipótesis las causas sospechadas hasta que se verifiquen.
3. **Pasos para solucionar problemas**: Pasos o enlaces para solucionar problemas
4. **Métricas y registros relacionados**: Enlaces a métricas y registros útiles para el diagnóstico

#### Pruebas de alertas

Pruebe periódicamente el sistema de alertas:

1. **Simulación de alertas**: Generar alertas de prueba
2. **Prueba de escalamiento**: Probar las rutas de escalamiento
3. **Inyección de fallos**: Inyectar fallos en entornos controlados

### Prácticas recomendadas para optimizar costos

#### Optimización del volumen de registros

Optimice el volumen de registros para reducir costos:

1. **Muestreo**: Muestree solo cuando la cobertura requerida lo permita y documente las brechas; conserve las pruebas de auditoría/errores requeridas.
2. **Filtrado**: Filtre los registros innecesarios
3. **Compresión**: Comprima los registros

#### Gestión de la cardinalidad de las métricas

Gestione la cardinalidad de las métricas para reducir costos:

1. **Valores de etiqueta limitados**: Controle los valores distintos y las combinaciones de etiquetas, no solo el número de nombres de etiquetas.
2. **Agregación**: Agregue métricas detalladas a niveles superiores
3. **Resolución de recopilación**: Elija intervalos de scrape y agregación que conserven la señal requerida; una recopilación más general puede ocultar picos.

#### Niveles de almacenamiento

Implemente niveles de almacenamiento rentables:

1. **Almacenamiento activo**: Registros recientes y a los que se accede con frecuencia
2. **Almacenamiento templado**: Registros a los que se accede con menos frecuencia
3. **Almacenamiento en frío**: Registros archivados

## Solución de problemas y depuración

Exploremos diversas técnicas para solucionar problemas y depurar clústeres de EKS.

![Diagrama que relaciona tres áreas de solución de problemas de EKS (problemas del clúster, problemas de cargas de trabajo y problemas comunes) con tres familias de herramientas de depuración: herramientas kubectl de Kubernetes, herramientas de AWS y herramientas de diagnóstico de red, con las herramientas kubectl en el centro y utilizadas por las tres áreas.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-5.png)

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

Elija un flujo real devuelto para lecturas acotadas con GetLogEvents o utilice las consultas anteriores. Esta inspección no habilita ni deshabilita el registro. Si no hay registros, utilice el procedimiento de configuración revisado por separado y verifique que la actualización haya finalizado.

#### Solución de problemas de nodos

Confirme el contexto de Kubernetes y seleccione el nodo real antes de interpretar una condición del nodo. El estado Ready, la posibilidad de programar cargas de trabajo y el estado de la aplicación son señales distintas:

```bash
kubectl config current-context
kubectl get nodes
: "${NODE_NAME:?Choose the node to inspect}"
kubectl describe node "$NODE_NAME"
kubectl get node "$NODE_NAME" -o jsonpath='{.spec.providerID}{"\n"}{.status.nodeInfo.kubeletVersion}{"\n"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}'
```

Para un grupo de nodos administrado, seleccione su nombre real e inspeccione su estado y salud. Esto no se aplica a todos los nodos Auto Mode, Fargate o autoadministrados:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster}"
: "${AWS_REGION:?Set its Region}"
: "${NODEGROUP_NAME:?Choose the actual managed node group}"
aws eks describe-nodegroup --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Status:status,Version:version,Health:health.issues,Resources:resources}'
```

Utilice la ruta de acceso/diagnóstico aprobada por el responsable del nodo. La disponibilidad de SSH, el usuario de inicio de sesión y las herramientas systemd dependen del sistema operativo y la configuración del nodo; no son funciones universales de EKS. Auto Mode, Fargate y Bottlerocket requieren sus procedimientos administrados/de plataforma aplicables. Para una sesión ya autorizada en un nodo Linux EC2 estándar con systemd, inspeccione registros acotados de kubelet, espacio e inodos:

```bash
sudo journalctl -u kubelet --since "30 minutes ago" --no-pager
df -h
df -i
```

La salida de la consola EC2 puede ayudar con problemas de arranque en una instancia propia accesible, pero no es un flujo completo de registros de kubelet/aplicaciones. Utilice los diagnósticos documentados del entorno de ejecución informado en lugar de suponer que todos los nodos ejecutan Docker.

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

Si hay disponible una instancia anterior terminada de ese contenedor, inspeccione también sus registros:

```bash
kubectl logs "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" --previous --tail=100
```

El comando de registros anteriores solo se aplica cuando existe una instancia anterior del contenedor que haya terminado. No recupera Pod antiguos arbitrarios ni registros perdidos con un nodo. Lea juntos los códigos de salida, los últimos motivos de terminación, las sondas y los eventos de recursos; el número de reinicios por sí solo no demuestra un OOM ni una causa raíz específica. Un comando de shell como /bin/bash no está disponible en todas las imágenes de aplicaciones.

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

Utilice EndpointSlices para inspeccionar los puntos de conexión actuales; la API heredada Endpoints está obsoleta, no eliminada universalmente. Compruebe el selector, las direcciones de puntos de conexión disponibles, el puerto/targetPort y el protocolo del Service. La resolución DNS, la disponibilidad de los puntos de conexión y la conectividad de red son comprobaciones distintas.

Un reenvío de puertos local puede inspeccionar un puerto de Service seleccionado, pero sigue una ruta de diagnóstico y no demuestra que funcionen el tráfico normal Pod-a-Service o un balanceador de carga. Establezca el puerto real del Service:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the service namespace}"
: "${SERVICE_NAME:?Choose the Service}"
: "${SERVICE_PORT:?Choose its service port number}"
kubectl port-forward --address 127.0.0.1 -n "$NAMESPACE" \
  "svc/$SERVICE_NAME" "8080:$SERVICE_PORT"
```

#### NetworkPolicy y contexto de diagnóstico

Inspeccione tanto la salida del origen como la entrada del destino, los selectores de espacios de nombres/Pod, el acceso DNS y la CNI que aplica las políticas. Los grupos de seguridad, las rutas, las ACL de red, las políticas de malla de servicios y TLS pueden añadir capas. Una sonda de un Pod temporal arbitrario puede tener etiquetas, ServiceAccount, grupos de seguridad o sidecars distintos de los de la carga de trabajo que falla.

Para una investigación autorizada, añada un contenedor de depuración efímero al Pod seleccionado utilizando una imagen revisada que no sea root y sea compatible con el perfil restringido. Establezca DEBUG_IMAGE en un digest aprobado, no en una etiqueta antigua de BusyBox ni en una imagen latest sin revisar:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned Pod namespace}"
: "${POD_NAME:?Choose the Pod}"
: "${CONTAINER_NAME:?Choose the target container}"
: "${DEBUG_IMAGE:?Set the reviewed non-root diagnostic image digest}"
kubectl debug "$POD_NAME" -n "$NAMESPACE" -it \
  --image="$DEBUG_IMAGE" --profile=restricted --target="$CONTAINER_NAME" -- sh
```

Esto modifica el Pod al añadir un contenedor efímero y requiere el permiso RBAC/admisión correspondiente. El registro permanece hasta que se elimine el Pod; salir del shell no elimina la entrada del contenedor efímero. La selección del espacio de nombres de procesos depende de la compatibilidad del entorno de ejecución. La imagen debe incluir las herramientas previstas y ejecutarse sin capacidades prohibidas por el perfil. No cambie silenciosamente a un perfil privilegiado para eludir una denegación de diagnóstico.

Dentro del shell de diagnóstico, establezca también allí los valores de destino; las variables del shell del host no se heredan automáticamente. Con las herramientas disponibles en la imagen elegida:

```bash
: "${SERVICE_DNS:?Set the intended service DNS name inside this shell}"
: "${SERVICE_PORT:?Set its port inside this shell}"
nslookup "$SERVICE_DNS"
nc -zv "$SERVICE_DNS" "$SERVICE_PORT"
```

Utilice el sufijo DNS real del clúster cuando se necesite un FQDN. Una conexión TCP correcta no valida HTTP, la autenticación de la aplicación ni TLS. La captura de paquetes y la depuración de nodos requieren un contexto/privilegio revisado por separado, así como filtros de captura, duración y almacenamiento acotados; un comando tcpdump genérico sin privilegios no se puede utilizar universalmente. Las capturas pueden contener credenciales o datos de usuario, aunque estén truncadas. En esta auditoría no se inició ningún Pod de diagnóstico, contenedor efímero, captura de paquetes ni sesión de nodo.

### Solución de problemas de registro y supervisión

#### Solución de problemas de Fluent Bit

Para el recopilador independiente instalado en este capítulo, el DaemonSet y la ConfigMap renderizados son ambos eks-log-collector en logging:

```bash
kubectl get daemonset eks-log-collector -n logging
kubectl get pods -n logging -l app.kubernetes.io/instance=eks-log-collector
kubectl logs -n logging -l app.kubernetes.io/instance=eks-log-collector \
  -c aws-for-fluent-bit --prefix --tail=100
kubectl get configmap eks-log-collector -n logging -o yaml
```

Si la recopilación está a cargo del complemento CloudWatch, inspeccione amazon-cloudwatch y sus recursos reales. Verifique la configuración montada, el acceso a los archivos del nodo, la selección de IRSA/Pod Identity, RBAC, conectividad de salida e indicadores de búfer/backlog/pérdida. No cree una kube-system/fluent-bit-config sin relación y suponga que el recopilador la lee. Revise la configuración y la salida de registros para detectar datos sensibles antes de compartirlas.

#### Solución de problemas de Prometheus

```bash
kubectl get prometheus,alertmanager -n monitoring
kubectl get pods,pvc -n monitoring
kubectl get servicemonitors,prometheusrules -n monitoring
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-kube-prometheus-prometheus 9090:9090
```

Inspeccione `http://127.0.0.1:9090/targets` mientras se realiza el reenvío. Compruebe los registros reales del Pod, el error del destino, la confianza del certificado, el puerto con nombre del Service, los selectores de espacio de nombres/etiquetas, las reglas y las muestras recientes. Un objeto ServiceMonitor por sí solo no demuestra que Prometheus lo seleccione ni que se pueda acceder a su punto de conexión. Para AMP, inspeccione por separado los fallos/backlog de remote-write y el espacio de trabajo previsto.

#### Solución de problemas de Grafana

```bash
kubectl get deployment monitoring-grafana -n monitoring
kubectl logs deployment/monitoring-grafana -n monitoring -c grafana --tail=100
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

Abra `http://127.0.0.1:3000` e inspeccione la fuente de datos configurada, las credenciales, el intervalo de tiempo y la consulta. El UID de la fuente de datos de Prometheus de la pila local es prometheus; AMG/AMP tiene un complemento y requisitos IAM propios. Un panel vacío puede deberse a una fuente de datos/etiqueta/intervalo de tiempo incorrectos o a una ingesta fallida, no a un uso nulo.

### Problemas comunes y soluciones

#### Error ImagePullBackOff

Inspeccione el error de descarga, el repositorio/digest de la imagen, la arquitectura, la autorización del registro y la ruta de red del nodo. No siempre se necesita acceso a Internet si hay puntos de conexión/rutas privados adecuados. Para ECR, valide la identidad de ejecución de EC2 o del Pod de Fargate y la política del repositorio; IRSA/Pod Identity de la aplicación no es la identidad de descarga de imágenes de kubelet.

Para un registro privado que utilice un Secret de extracción, prepare un archivo JSON de autenticación Docker autónomo mediante el proceso aprobado de credenciales. Un archivo que solo contenga referencias de credenciales auxiliares no es suficiente para un imagePullSecret de Kubernetes. Para un Secret nuevo administrado, pase la ruta del archivo en lugar de una contraseña como argumento de comando:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DOCKER_CONFIG_JSON:?Set the protected self-contained registry auth JSON file}"
kubectl create secret generic regcred -n "$NAMESPACE" \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=".dockerconfigjson=$DOCKER_CONFIG_JSON"
```

Adjúntelo solo a la carga de trabajo administrada prevista. Para un Deployment, este parche estratégico combina la entrada imagePullSecrets con nombre con las entradas existentes. Cambia la plantilla del Pod y activa una implementación; inspeccione antes el procedimiento de implementación del responsable:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DEPLOYMENT:?Set the owned Deployment name}"
kubectl patch deployment "$DEPLOYMENT" -n "$NAMESPACE" --type=strategic \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}}}'
```

Para un Secret existente, utilice el procedimiento de rotación de quien lo administra y conserve las demás referencias de registro. No aplique un parche a la ServiceAccount predeterminada del espacio de nombres como solución general. Crear el Secret no verifica el inicio de sesión en el registro, la existencia de la imagen ni que la descarga funcione.

#### Error CrashLoopBackOff

Correlacione los registros actuales/anteriores del contenedor seleccionado, el código de salida, el motivo de terminación, las sondas de inicio/actividad, la configuración y los eventos de recursos. OOMKilled, un fallo de sonda y la salida de la aplicación son causas distintas. La falta de una dependencia al inicio o un comando incorrecto también pueden provocar reinicios del contenedor. Utilice el procedimiento de diagnóstico acotado anterior cuando la imagen normal no tenga las herramientas necesarias; no reinicie ni elimine las pruebas antes de recopilarlas.

#### Estado NotReady del nodo

Inspeccione el estado/motivo Ready, la actualización del nodo/lease, las condiciones de presión y los diagnósticos reales de kubelet/entorno de ejecución mediante la ruta de acceso de plataforma correspondiente. El espacio en bytes, el agotamiento de inodos, la conectividad de red/API y los fallos del entorno de ejecución requieren medidas correctivas distintas. No deduzca que se activa una reparación automática ni que es seguro vaciar el nodo solo a partir del estado NotReady mostrado.

#### Problemas de conexión del Service

Siga la ruta Service-a-EndpointSlice-a-Pod anterior y luego examine los controles de red de origen/destino y el puerto/protocolo de escucha de la aplicación. Pruebe desde un contexto de carga de trabajo representativo. Que funcione un reenvío de puertos, una búsqueda DNS o un handshake TCP no demuestra por sí solo que el servicio esté sano de extremo a extremo.

### Herramientas de depuración

Utilice kubectl para el estado/eventos de Kubernetes, la CLI de AWS para el estado del servicio administrado correspondiente y herramientas de red aprobadas dentro del contexto para comprobar conectividad. Preserve las pruebas y distinga entre la inspección y las acciones que crean un Pod, cambian una plantilla, vacían un nodo o modifican el registro.

#### Obtener un resultado de CloudWatch Logs Insights

StartQuery devuelve un ID de consulta asíncrona, no los resultados finales. Este ejemplo de Bash/Python utiliza segundos epoch UTC sin la opción date -v exclusiva de macOS, realiza un número limitado de sondeos e imprime los resultados solo cuando el estado es Complete:

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

El límite de sondeos no es un tiempo de espera del servicio. Una consulta que siga en ejecución permanece activa; vuelva a inspeccionarla o use explícitamente StopQuery si ya no la necesita. Limite el grupo de registros/intervalo de tiempo y los permisos IAM necesarios, y tenga en cuenta los costos de consulta. Durante esta auditoría no se ejecutó ninguna consulta de CloudWatch ni operación de depuración de clúster.

## Conclusión

En este documento exploramos diversas herramientas, técnicas y prácticas recomendadas para supervisar y registrar clústeres de Amazon EKS. Implementar una estrategia eficaz de supervisión y registro permite conocer continuamente el estado del clúster, detectar los problemas pronto y responder con rapidez cuando ocurren.

Temas tratados:

1. **Descripción general de la supervisión y el registro**: Importancia y arquitectura de la supervisión y el registro
2. **Registro del plano de control de EKS**: Tipos de registros del plano de control y cómo habilitarlos
3. **Registro de contenedores**: Recopilación de registros de contenedores mediante Fluent Bit y CloudWatch Container Insights
4. **Supervisión del clúster**: Supervisión del clúster con CloudWatch, Prometheus y Grafana
5. **Alertas y gestión de eventos**: Configuración de alertas mediante CloudWatch alarms y Prometheus Alertmanager
6. **Análisis y visualización de registros**: Análisis de registros mediante CloudWatch Logs Insights, OpenSearch y Grafana Loki
7. **Prácticas recomendadas de supervisión y registro**: Prácticas recomendadas para una supervisión y un registro eficaces
8. **Solución de problemas y depuración**: Problemas comunes y soluciones

La supervisión y el registro de clústeres de EKS son procesos continuos que deben mejorarse constantemente para satisfacer los requisitos del clúster y las aplicaciones.

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

Para comprobar lo que aprendió en este capítulo, pruebe el [cuestionario del tema](../quizzes/eks/06-eks-monitoring-logging-quiz.md).
