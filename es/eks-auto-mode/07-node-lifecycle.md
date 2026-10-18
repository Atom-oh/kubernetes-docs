# Gestión del ciclo de vida de los nodos

> **Versiones compatibles**: disponibilidad general de EKS Auto Mode; ejemplos revisados para EKS 1.36
> **Última actualización**: 12 de septiembre de 2026

La expiración, las actualizaciones de imágenes administradas y la recuperación de aplicaciones son partes distintas del ciclo de vida de los nodos. Que un objeto Node de Kubernetes sea reciente no demuestra que se hayan aplicado todas las correcciones de CVE ni que una carga de trabajo cumpla los requisitos. Estos ejemplos se revisaron con fuentes oficiales y esquemas y fixtures locales; no se realizaron rotaciones de nodos en vivo, cambios en la nube ni pruebas de rendimiento.

## Expiración y límite de vida útil de Auto Mode

`spec.template.spec.expireAfter` determina la expiración basada en la antigüedad de los NodeClaims creados a partir de esa plantilla. El campo heredado de la era de Provisioner `ttlSecondsUntilExpired` no se utiliza en estos NodePools `karpenter.sh/v1`.

Distinga estos tres ajustes:

| Concepto | Comportamiento de Auto Mode |
|---------|-----------------------------|
| Expiración predeterminada | AWS documenta **336h (14 días)**, no 7 ni 21 días |
| Gracia de terminación | Si se omite en el NodePool, Auto Mode establece **24h en el NodeClaim** de forma predeterminada; inspeccione el claim aunque el pool no lo muestre |
| Vida útil máxima de una instancia administrada | AWS impone **21 días (504h)**; esto no garantiza que un nodo vaya a permanecer disponible hasta entonces |

No sustituya los valores predeterminados de Auto Mode por el valor predeterminado de 720h de Karpenter upstream. Una duración mayor o la sintaxis `Never` de upstream no proporciona retención indefinida de una instancia administrada de Auto Mode. No intente extender el máximo de AWS combinando 504h con un período de drenaje largo.

Antes de ejecutar los comandos de solo lectura que siguen, utilice la comprobación de cuenta y contexto y la variable privada `WORK_DIR` de [Operaciones](./05-operations.md). Los pools de ejemplo presuponen un NodeClass `default` revisado. Son configuraciones de laboratorio acotadas y con taints; se necesitan selectores y tolerations correspondientes para las cargas de trabajo, además de pruebas de recuperación de las aplicaciones.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: with-expiration
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
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```

### Qué hace realmente la expiración

La expiración es un **disparador de interrupción forzosa**. Inicia la terminación y el drenaje cuando el NodeClaim alcanza la antigüedad definida por la política; no espera a que una capacidad de reemplazo aprovisionada previamente esté en estado Ready. Los presupuestos de interrupción del NodePool no limitan la velocidad de la expiración. Los controladores de cargas de trabajo y el aprovisionamiento pueden crear la capacidad de reemplazo que haga falta; aquí no se garantiza el antiguo orden de cinco pasos de «primero el nuevo nodo queda Ready y después se drena el anterior».

El controlador de terminación impide la programación ordinaria de cargas nuevas, intenta drenar mediante la API Eviction, gestiona la separación de volúmenes y termina la instancia. Los PDB y `do-not-disrupt` de los Pods pueden influir en el drenaje, pero el plazo de gracia de terminación y la vida útil máxima de AWS impiden que sean una protección de disponibilidad indefinida. La gracia de apagado del Pod y la gracia de terminación del nodo son ajustes distintos. Los datos del almacenamiento local o efímero necesitan un plan de recuperación.

Cambiar `expireAfter` en el pool no reescribe los NodeClaims existentes; puede provocar drift y se aplica a los claims de reemplazo. Otros métodos de interrupción pueden acortar la vida del nodo. Un presupuesto de un nodo no puede hacer que varias expiraciones simultáneas se ejecuten en secuencia.

### Cómo elegir una duración

Los ejemplos anteriores de 24h, 48h, 72h, 168h y 336h específicos para distintos entornos son decisiones de política, no valores predeterminados de producción de AWS ni intervalos de rotación obligatorios para PCI/HIPAA/SOC2. El ejemplo anterior de desarrollo de 504h representaba el límite del servicio, no un `expireAfter` recomendado más tiempo de drenaje.

Elija una política en función de la urgencia de los parches, los puntos de control de las cargas de trabajo, el calentamiento de la caché, el comportamiento de las réplicas y el cuórum, la capacidad disponible y las pruebas de recuperación. La rotación frecuente puede aumentar las descargas de imágenes, la reprogramación y el trabajo de recuperación facturable. Por sí sola, no aumenta la probabilidad de que EC2 interrumpa una instancia Spot específica ni garantiza que un parche publicado recientemente esté disponible.

## AMI administradas y configuración de NodeClass

Auto Mode utiliza **variantes de Bottlerocket administradas por AWS**. No ofrece un selector `amiFamily` entre AL2023 y Bottlerocket, `amiSelectorTerms` personalizado, `userData` arbitrario, acceso por SSH ni Session Manager de SSM. No copie estas interfaces de EC2NodeClass de Karpenter autogestionado ni de recetas para grupos de nodos administrados convencionales.

El NodeClass compatible que sigue configura el almacenamiento y la identidad de red; no selecciona ni fija una AMI:

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: lifecycle-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
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
```

Revise el rol del perfil de instancia, su entrada de acceso y la selección real de subredes y grupos de seguridad; después, haga referencia a `lifecycle-nodeclass` solo desde el pool previsto. Auto Mode administra sus ajustes de IMDSv2 y hop limit; no los sustituya mediante `metadataOptions`. Utilice `ephemeralStorage` en vez de `blockDeviceMappings`; el cifrado de EBS del disco raíz o de datos del nodo no establece el cifrado de los PVC de la aplicación. Consulte [Configuración de NodePool](./02-nodepool-configuration.md) para conocer los ajustes compatibles de claves y certificados.

### Las comparaciones históricas de sistemas operativos no son un menú de selección de Auto Mode

AL2023 es una distribución Amazon Linux de propósito general con algunos componentes upstream de Fedora; no es simplemente RHEL. AL2023 de uso general y los hosts Bottlerocket operados de forma independiente ofrecen opciones de administración distintas de los nodos de Auto Mode con acceso restringido. Auto Mode también admite cargas de trabajo de GPU mediante sus imágenes administradas; aquí es incorrecto concluir que «GPU implica que se necesita AL2023».

Los intervalos originales de arranque de 40–60s para AL2023 y 20–30s/20–40s para Bottlerocket, así como los intervalos del cuestionario de 20–40s frente a 15–25s, no tienen una procedencia de medición verificada. Se conservan como ejemplos históricos, no como una clasificación de velocidad de los sistemas operativos ni como predicción para estos manifiestos. Las descargas de imágenes, la arquitectura, el tipo de instancia y la disponibilidad de la carga deben medirse por separado.

## Drift y actualizaciones de imágenes administradas

AWS documenta que publica AMI de Auto Mode aproximadamente cada semana y permite reemplazar por drift los nodos que cumplen los requisitos. Esa frecuencia no es un SLA de aplicación de parches para cada CVE. La publicación de una AMI optimizada para EKS de otra familia no se convierte automáticamente en una actualización de imagen de Auto Mode.

| Cambio u observación | Interpretación correcta |
|-----------------------|-------------------------|
| Actualización de AMI administrada de Auto Mode | Puede provocar drift en claims existentes; inspeccione las condiciones reales y el estado del despliegue |
| Cambio en los requisitos de NodePool | No todos los cambios causan drift; ampliar los valores permitidos compatibles puede hacer que un nodo existente siga cumpliendo los requisitos |
| Cambio de plantilla `expireAfter` | Los claims existentes conservan el valor almacenado; los claims de reemplazo usan la política actualizada |
| Peso, límites o ajustes de interrupción | Ajustes de comportamiento, no un disparador general de drift |
| Cambio del estado deseado de NodeClass | Utilice los campos compatibles y observe el controlador administrado; una etiqueta cosmética no garantiza un disparador de emergencia para aplicar parches |
| Cambio de `amiFamily` o `blockDeviceMappings` | No son campos válidos de NodeClass en Auto Mode |

Utilice las condiciones `Drifted` de los NodeClaims. Una anotación de hash no es un estado booleano de drift, y no encontrar una condición no demuestra que no haya drift. Lea el motivo, la transición y la generación, y compárelos con el estado actual del recurso:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
jq '[.items[] | {
  name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
  createdAt:.metadata.creationTimestamp,deletionTimestamp:.metadata.deletionTimestamp,
  pool:.metadata.labels["karpenter.sh/nodepool"],
  expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
  imageID:.status.imageID,
  drift:([.status.conditions[]?|select(.type=="Drifted")|
    {status,reason,lastTransitionTime,observedGeneration}] |
    if length == 0 then {status:"NotReported"} else .[0] end),
  conditions:[.status.conditions[]?|{type,status,reason,lastTransitionTime,observedGeneration}]
}]'
```

El drift es un método de interrupción controlada, sujeto a los presupuestos aplicables, la viabilidad de la programación y las restricciones de drenaje. La configuración siguiente limita a un nodo las interrupciones voluntarias permitidas y pausa **solo el drift** los días laborables de 00:00 a 08:00 UTC, equivalente a las 09:00–17:00 en Seúl. Las antiguas expresiones horarias `0 9-17`/`0 9-18` volvían a iniciar períodos largos y solapados.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: controlled-drift
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
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
    - nodes: '1'
    - nodes: '0'
      schedule: 0 0 * * mon-fri
      duration: 8h
      reasons:
      - Drifted
  limits:
    cpu: '100'
    memory: 400Gi
```

Esto no pausa la expiración, las interrupciones de EC2 ni la reparación. `consolidateAfter` afecta a la consolidación, no a un plazo para aplicar parches a la AMI. Las anotaciones `do-not-disrupt` de Pod y Node son distintas; la gracia predeterminada del NodeClaim de Auto Mode importa al evaluar si una anotación de Pod impide el drift.

## Aplicación de parches y recuperación manual excepcional

AWS administra los parches del sistema operativo del nodo y de los componentes de Auto Mode; usted sigue siendo responsable de las dependencias de las aplicaciones y los contenedores, así como de la seguridad de las cargas de trabajo. Registre la información de la imagen real, el aviso o la versión de AWS correspondiente, el avance del despliegue y las comprobaciones de la aplicación. Una marca de tiempo reciente o una etiqueta `SecurityPatch` no demuestra que se haya aplicado una corrección.

Para una corrección urgente:

1. Verifique que la imagen administrada y la corrección necesarias estén disponibles para este clúster y determine qué cargas de trabajo están afectadas.
2. Con el contexto previsto, revise un único UID de NodeClaim, su correspondencia con el nodo, el pool, las condiciones actuales, los PDB, la durabilidad de los datos y la capacidad sobrante o que se pueda obtener.
3. Si cumple el requisito, prefiera el despliegue de drift administrado. Si hace falta un reemplazo manual, utilice un procedimiento de mantenimiento revisado que afecte a un solo recurso y confirme que el reemplazo y la aplicación estén listos antes de continuar con otro recurso.
4. Vuelva a comprobar el estado y la evidencia de la imagen después de cada cambio; deténgase si el estado es desconocido, falla la capacidad o se produce una regresión de la aplicación.

El comando siguiente solo recopila evidencia:

```bash
: "${NODECLAIM_NAME:?Select one NodeClaim for review}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaim "$NODECLAIM_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
       pool:.metadata.labels["karpenter.sh/nodepool"],imageID:.status.imageID,
       expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
       conditions:[.status.conditions[]?|{type,status,reason}]}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[]|{namespace:.metadata.namespace,name:.metadata.name,
       observedGeneration:.status.observedGeneration,generation:.metadata.generation,
       currentHealthy:.status.currentHealthy,desiredHealthy:.status.desiredHealthy,
       disruptionsAllowed:.status.disruptionsAllowed}]'
```

`kubectl delete nodes -l ...` es una solicitud de eliminación en bloque, no una actualización gradual y secuencial. La eliminación manual de nodos o claims no está limitada por un presupuesto de NodePool; `drain --delete-emptydir-data` puede descartar datos locales, y ejecutar drain por sí solo no garantiza que exista un reemplazo. Por tanto, los comandos de eliminación sin restricciones del cuestionario anterior y su supuesto «disparador para aplicar parches» basado en cambiar etiquetas no constituyen un procedimiento de emergencia.

## Consolidación, drift y expiración

| Mecanismo | Disparador y control |
|-----------|----------------------|
| Consolidación | Ubicación viable de menor coste, según las solicitudes y restricciones; se aplican los controles de interrupción controlada |
| Drift | El claim existente ya no coincide con el estado deseado administrado; se aplican los controles de interrupción controlada |
| Expiración | La antigüedad del claim alcanza la política almacenada; es un disparador forzoso que no está sujeto a los presupuestos de NodePool |

El controlador de interrupciones controladas evalúa el drift antes que la consolidación, pero la expiración sigue una ruta forzosa separada. No hay una prioridad universal de «drift > expiración > consolidación» ni un contrato de «la primera condición tiene prioridad». Un nodo con cinco días de antigüedad puede consolidarse antes de cumplir una expiración a los siete días; no es necesario que un nodo expirado con ocho días esté infrautilizado para que comience su terminación.

Las siguientes son políticas de laboratorio alternativas, no resultados garantizados en coste o seguridad:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-priority
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
        name: default
      expireAfter: 336h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-priority
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
        name: default
      expireAfter: 72h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```

`WhenEmpty` limita el alcance de la consolidación, pero no desactiva el drift ni la expiración. Coordine las aplicaciones con la expiración y la gracia seleccionadas; no infiera la disponibilidad a partir del nombre de una política.

## Antigüedad del objeto Node y evidencia de la imagen

`Node.metadata.creationTimestamp`, la hora de creación del NodeClaim y la hora de lanzamiento de EC2 son observaciones distintas. `Node.status.nodeInfo.osImage` describe el sistema operativo; no es un ID de AMI. Las columnas repetidas de fecha CREATED/AGE anteriores y el script de edad del «estado del parche de seguridad» no demostraban el estado de los parches.

Capture los campos seleccionados de Node y, después, calcule la antigüedad fraccionaria portable y sus intervalos explícitos. Las marcas de tiempo no válidas, ausentes, sin zona horaria o futuras deben quedar como desconocidas:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '{items:[.items[] | {
  name:.metadata.name,uid:.metadata.uid,createdAt:.metadata.creationTimestamp,
  pool:.metadata.labels["karpenter.sh/nodepool"],
  osImage:.status.nodeInfo.osImage,kernelVersion:.status.nodeInfo.kernelVersion
}]}' > "$WORK_DIR/node-lifecycle.json"
```

```bash
python3 - <<'PY'
import json, os
from datetime import datetime, timezone
from pathlib import Path
now = datetime.now(timezone.utc)
rows = []
for item in json.loads((Path(os.environ["WORK_DIR"]) / "node-lifecycle.json").read_text())["items"]:
    result = {"node": item["name"], "pool": item.get("pool")}
    try:
        created = datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00"))
        if created.tzinfo is None or created > now:
            raise ValueError("unusable timestamp")
        hours = (now - created).total_seconds() / 3600
        bucket = "<1d" if hours < 24 else "1d–<3d" if hours < 72 else "3d–<7d" if hours < 168 else ">=7d"
        result.update(nodeObjectAgeHours=round(hours, 3), bucket=bucket)
    except (KeyError, AttributeError, TypeError, ValueError):
        result["bucket"] = "UnknownTimestamp"
    rows.append(result)
summary = [{"bucket": bucket, "count": sum(row["bucket"] == bucket for row in rows)}
           for bucket in ("<1d", "1d–<3d", "3d–<7d", ">=7d", "UnknownTimestamp")]
print(json.dumps({"observedAt": now.isoformat(), "nodes": rows, "distribution": summary}, indent=2))
PY
```

Los intervalos son `[0,1)`, `[1,3)`, `[3,7)` y `>=7` días; exactamente siete días pertenece al último intervalo. Una lista de Nodes vacía obtenida correctamente se distingue de un error de API. Esta instantánea es un diagnóstico, no un panel que se actualiza en vivo ni una comprobación de cumplimiento de parches.

### Prometheus y Grafana

Instale kube-state-metrics y permita las etiquetas `karpenter.sh/nodepool` y `eks.amazonaws.com/compute-type`. El archivo de reglas siguiente para **un solo clúster** elimina las series duplicadas de las consultas de scrape y une las etiquetas de Auto Mode con el indicador temporal de creación de Node. Las consultas multiclúster deben conservar una etiqueta real de clúster en cada agrupación y unión. La ausencia de métricas o las marcas de tiempo futuras no se convierten en nodos con antigüedad cero y estado saludable.

Las alertas de antigüedad conservan los antiguos umbrales de diez días y tres desviaciones estándar como **señales ilustrativas para la revisión**. No son valores predeterminados de Auto Mode; las políticas mixtas de pools y el escalado automático normal pueden producir distribuciones amplias de antigüedad. Cargue esto como archivo de reglas de Prometheus o coloque sus grupos dentro de `spec` en un PrometheusRule seleccionado por su operador:

```yaml
groups:
- name: node-lifecycle
  rules:
  - record: eks_auto:node_object_age_days
    expr: "(\n  ((time() - max by (node) (kube_node_created)) >= 0) / 86400\n) * on\
      \ (node) group_left (label_karpenter_sh_nodepool)\nmax by (node,label_karpenter_sh_nodepool)\
      \ (\n  kube_node_labels{label_karpenter_sh_nodepool!=\"\",label_eks_amazonaws_com_compute_type=\"\
      auto\"}\n)"
  - alert: ReviewNodeObjectAge
    expr: eks_auto:node_object_age_days > 10
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: Review this node against its actual lifecycle policy
  - alert: ReviewNodeAgeSpread
    expr: stddev(eks_auto:node_object_age_days) > 3
    for: 4h
    labels:
      severity: info
    annotations:
      summary: Age spread is a review signal, not proof of failed rotation
```

```promql
# median_object_age_days
quantile(0.5, eks_auto:node_object_age_days)

# mean_by_pool
avg by (label_karpenter_sh_nodepool) (eks_auto:node_object_age_days)

# oldest_five
topk(5, eks_auto:node_object_age_days)

# less_than_1d
sum((eks_auto:node_object_age_days >= bool 0) * (eks_auto:node_object_age_days < bool 1))

# 1d_to_under_3d
sum((eks_auto:node_object_age_days >= bool 1) * (eks_auto:node_object_age_days < bool 3))

# 3d_to_under_7d
sum((eks_auto:node_object_age_days >= bool 3) * (eks_auto:node_object_age_days < bool 7))

# 7d_or_more
sum(eks_auto:node_object_age_days >= bool 7)
```

`kube_node_created` es una métrica gauge de marca de tiempo, no un histograma ni un contador. No existe un `kube_node_created_bucket` predeterminado; `rate()` junto con `histogram_quantile()` no puede crear un histograma de antigüedad de nodos. Utilice `quantile()` para la mediana de antigüedad actual y cubos booleanos explícitos para un gráfico de barras. Estas sumas de cubos devuelven cero cuando hay nodos observados pero ninguno pertenece al intervalo; si no hay datos de entrada, el resultado sigue ausente.

| Panel de Grafana | Evidencia |
|------------------|-----------|
| Distribución actual de antigüedad | Las cuatro consultas de intervalos explícitos |
| Promedio por pool / nodos más antiguos | Unión de etiquetas y `avg` / `topk` |
| Claims próximos a expirar | Hora real de creación del NodeClaim y `expireAfter` almacenado; la antigüedad de Node por sí sola no basta |
| Tasa de reemplazo | Historial configurado de eventos o registros, o un publicador de contador verificado; no conteos inferidos de los objetos actuales |
| Despliegue de parches | Información de la versión o imagen administrada, condiciones de claims y estado de la aplicación |

## Referencias

- [Valores predeterminados de NodePool de Auto Mode y gracia de terminación](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Seguridad de Auto Mode y vida útil máxima de las instancias](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Sistema operativo administrado y responsabilidades de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Configuración compatible de NodeClass](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Interrupción, expiración y drift de Karpenter](https://karpenter.sh/v1.14/concepts/disruption/)
- [Métricas de Node de Kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [Operadores de agregación de Prometheus](https://prometheus.io/docs/prometheus/latest/querying/operators/)
- [Relación entre AL2023 y Fedora](https://docs.aws.amazon.com/linux/al2023/ug/relationship-to-fedora.html)

< [Anterior: Gestión de costos](./06-cost-management.md) | [Tabla de contenido](./README.md) | [Siguiente: Optimización de cargas de trabajo](./08-workload-optimization.md) >
