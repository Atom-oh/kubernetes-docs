# Resiliencia y alta disponibilidad de EKS

> **Línea base de la API de ejemplo**: Kubernetes 1.36; elija versiones compatibles de EKS y de los controladores que tengan soporte actualmente
> **Última actualización**: 12 de septiembre de 2026

Estos son patrones de configuración, no una plataforma de producción probada. Use un ámbito de pruebas propio y sustituya las imágenes de aplicación, las rutas de comprobación de estado y las referencias a IAM e infraestructura por entradas revisadas. En esta auditoría no se ejecutaron clústeres, conmutaciones por error ni experimentos de caos.

RTO es el objetivo aceptable de tiempo de recuperación, incluidos la detección y el restablecimiento; RPO es la ventana aceptable de punto de recuperación/pérdida de datos. Multi-AZ, la replicación y un SLA del plano de control no garantizan automáticamente que no se pierdan datos ni un tiempo de recuperación determinado para las cargas de trabajo.

## Descripción general de la resiliencia

La resiliencia es **la capacidad de minimizar el impacto durante los fallos mientras se recupera un estado normal o se mantiene el servicio**. Va más allá de la alta disponibilidad (HA) simple y representa una filosofía de diseño que anticipa y prepara la respuesta a los fallos.

### Modelo de madurez de resiliencia

| Nivel | Ámbito | Ejemplos de controles | Tiempos de recuperación ilustrativos anteriores, no mediciones |
| --- | --- | --- | --- |
| 1. Básico | Pod/carga de trabajo | Sondeos, recursos, presupuesto de interrupciones, apagado | Segundos–minutos |
| 2. Multi-AZ | Pérdida de AZ | Ubicación, capacidad restante, recuperación del tráfico/datos | Segundos–minutos |
| 3. Celda | Partición de servicio | Enrutamiento y dependencias/capacidad acotadas | Segundos para impacto parcial–minutos |
| 4. Multi-Región | Pérdida regional | Conmutación por error del tráfico/datos regionales y operaciones | Objetivos cercanos a cero hasta minutos/horas, según el diseño |

Las ediciones anteriores en otros idiomas usaban distintos intervalos de tiempo ilustrativos. Este modelo organiza las decisiones de diseño; no es una certificación ni una garantía de que un nivel superior se recupere más rápido. Defina y mida objetivos para cada recorrido de usuario y sus dependencias.

EKS regional administra su plano de control en tres AZ. El SLA actual del endpoint es de un 99,95 % de tiempo de actividad mensual para Standard Control Plane (intervalos de medición de cinco minutos) y de un 99,99 % para Provisioned Control Plane (intervalos de un minuto). Se trata de compromisos de créditos de servicio sujetos a condiciones, no de garantías de SLO/RTO/RPO de la aplicación. [SLA de AWS EKS](https://aws.amazon.com/eks/sla/)


> No todos los servicios requieren el nivel 4. Elija el nivel adecuado según los requisitos de SLA, la normativa y el presupuesto.

***

## Nivel 1: resiliencia básica (nivel de Pod)

### Sondeos de actividad, disponibilidad e inicio

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

La imagen anterior es un marcador de posición explícito de la aplicación, no un artefacto publicado. Sustitúyala por un resumen criptográfico verificado e implementa el contrato de estado antes del despliegue. El sondeo de inicio bloquea los de actividad y disponibilidad; el sondeo de actividad no debería fallar solo porque un servicio descendente responda lentamente. Los valores de recursos y sondeos son ilustrativos. Los Jobs y los contenedores de inicialización no necesitan necesariamente esos mismos sondeos.

### PodDisruptionBudget (PDB)

Un PDB limita las expulsiones voluntarias admitidas para los Pods que coinciden con la selección. No conserva el número de Pods ante un fallo de AZ/hardware, la eliminación directa de un Pod ni una actualización gradual/reducción de escala propias de un Deployment. La estrategia del controlador, la ubicación y la capacidad de reserva son controles independientes.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

```bash
# Check PDB status
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb web-app-pdb
# Inspect the actual workload health and ongoing disruptions.
# Illustrative only: three Ready replicas and no ongoing/unhealthy deductions permit one eviction.
```

### Apagado ordenado

```yaml
spec:
  terminationGracePeriodSeconds: 60
  containers:
  - name: app
    lifecycle:
      preStop:
        sleep:
          seconds: 5
```

Este es un fragmento de la especificación de Pod para la aplicación propia. El sleep nativo de preStop tiene disponibilidad general desde Kubernetes 1.34 y es válido en la línea base 1.36. Una espera de cinco segundos solo introduce una demora; no garantiza la propagación a los endpoints ni al balanceador de carga. El período de gracia incluye el hook, y las actualizaciones de terminación de EndpointSlice se ejecutan en paralelo con el apagado del nodo. Los endpoints en terminación pueden seguir apareciendo con `ready=false` y una condición `serving` para permitir el drenaje.

A continuación, el tiempo de ejecución envía la señal de detención configurada (normalmente SIGTERM; la configuración de la imagen/tiempo de ejecución puede variar). La aplicación debe gestionarla y finalizar o rechazar el trabajo antes de la terminación forzada. No elimine manualmente el PID 1 en preStop dando por sentado que los endpoints se quitarán en un orden estricto. Pruebe las conexiones de larga duración, la baja de registro y el vaciado reales.

***

## Nivel 2: estrategia Multi-AZ

### Restricciones de distribución de topología de Pods

La distribución de topología influye en la ubicación; no crea capacidad en buen estado ni reubica automáticamente los Pods existentes tras un fallo.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      topologySpreadConstraints:
      # Hard constraint for the documented N-1 example; review eligible domains and capacity.
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
        minDomains: 2
      # Soft constraint: Even distribution across nodes
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-app
      containers:
      - name: app
        image: web-app:1.0
```

| Parámetro           | Descripción                                              |
| ------------------- | -------------------------------------------------------- |
| `maxSkew` | Con DoNotSchedule, diferencia entre el recuento del dominio candidato y el mínimo global |
| `topologyKey`       | Base de distribución (zona, nombre de host, etc.)                |
| `whenUnsatisfiable` | `DoNotSchedule` (estricto) o `ScheduleAnyway` (flexible)        |
| `minDomains` | Si quedan menos dominios aptos, el mínimo global pasa a ser cero |

Por ejemplo, si quedan dos zonas aptas con dos Pods coincidentes cada una, `minDomains=3` establece en cero el mínimo global y puede impedir Pods de reemplazo con `maxSkew=1`. `minDomains=2` permite calcular la distribución de otro Pod si las demás restricciones y la capacidad lo permiten. No exige que haya exactamente dos o tres AZ ocupadas. Establezca por separado las condiciones para la ubicación inicial en tres AZ y la capacidad adicional en las AZ restantes. ScheduleAnyway es una preferencia; siguen aplicándose las demás restricciones del planificador.

### NodePool Multi-AZ de Karpenter

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand", "spot"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m6i.xlarge", "m6i.2xlarge", "m7i.xlarge", "m7i.2xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: "20%"    # Applicable voluntary budget, rounded up and reduced by deleting/NotReady nodes
    - nodes: "0"
      schedule: "0 0 * * MON-FRI"   # UTC 00:00–09:00 = Korea/Japan 09:00–18:00; not all failure types
      duration: 9h
```

Los requisitos de Karpenter permiten zonas; no aprovisionan nodos de manera uniforme por adelantado ni reservan capacidad para fallos. Use una versión compatible con EKS; la línea base del esquema es la versión mantenida 1.14.1, no un mínimo histórico incondicional de 1.0+. Ya deben haberse revisado EC2NodeClass, las AMI, el rol, las subredes y la capacidad a los que se hace referencia.

Los presupuestos porcentuales usan ceil(total × porcentaje), menos los nodos en proceso de eliminación y los nodos NotReady; se aplica el presupuesto correspondiente más restrictivo. No limitan la frecuencia de todas las interrupciones, expiraciones, reparaciones o eliminaciones manuales. Los horarios están en UTC; el ejemplo corresponde a un único intervalo entre semana, de 09:00 a 18:00 en Corea/Japón. Un presupuesto de cero no impide todos los fallos.

Los grupos de Spot y On-Demand separados pueden usar ponderaciones de 100/50, pero estas son preferencias de aprovisionamiento, no una garantía de que el grupo de menor ponderación solo se use cuando Spot no esté disponible. También influyen la capacidad existente, las restricciones y el procesamiento por lotes. Los límites de NodePool limitan el aprovisionamiento, no realizan el escalado previo.

### Preferencia del Service por la misma zona

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

PreferSameZone/PreferSameNode tienen disponibilidad general desde Kubernetes 1.35 y son válidos para esta línea base 1.36; PreferClose es el alias anterior de PreferSameZone. Se trata de una preferencia, no de una garantía estricta de localidad, latencia o costo. Compruebe el comportamiento real del proxy/EndpointSlice y las políticas de tráfico Local. La anotación anterior `topology-mode=Auto` usa una heurística distinta para asignar sugerencias; la orientación sobre topology-aware-hints es obsoleta.

Fuentes: [PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/), [terminación de Pod](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [distribución de topología](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/), [distribución del tráfico de Service](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution), [interrupciones de Karpenter](https://karpenter.sh/docs/concepts/disruption/).

### ARC Zonal Shift

La conmutación zonal manual y la conmutación zonal automática son operaciones distintas. La integración de EKS pone en estado cordon los nodos de la zona afectada y elimina sus endpoints de EndpointSlices; no expulsa los Pods ni termina esos nodos. Auto Mode evita crear nodos y suspende las interrupciones voluntarias pertinentes en la AZ afectada; los grupos de nodos administrados suspenden el reequilibrio de AZ y evitan lanzar nuevos nodos allí. La integración actual de Karpenter requiere la versión/configuración/IAM indicados en su documentación. La conmutación de un balanceador de carga es una operación independiente del recurso.

Primero verifique la cuenta, el recurso administrado exacto, la integración habilitada, la configuración de práctica existente y el comportamiento de las alarmas. Pruebe la aplicación, el DNS, los datos y la capacidad de nodos en las zonas restantes. La conmutación zonal no es un aislamiento absoluto de la red: EKS tiene un mecanismo de seguridad si todos los endpoints del servicio están en la zona afectada. No puede mover un volumen EBS zonal existente. Auto Mode puro usa CoreDNS del sistema de nodos; los nodos mixtos/no pertenecientes a Auto Mode siguen necesitando el Deployment y su capacidad.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resource region}"
: "${ARC_RESOURCE_ARN:?Set the exact owned EKS cluster or eligible load-balancer ARN}"
aws sts get-caller-identity
aws arc-zonal-shift get-managed-resource \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN"
```
Los siguientes bloques son pasos operativos separados, no un único script de configuración. La configuración de práctica inicia cambios de tráfico recurrentes; inspeccione una configuración existente en lugar de volver a crearla. El identificador de una alarma de resultado es una cadena ARN, no un objeto alarmName/region. Habilite la conmutación automática por separado cuando esté listo.

```bash
# MUTATION: authorizes recurring weekly traffic-shifting practice runs.
: "${OUTCOME_ALARM_ARN:?Set the reviewed CloudWatch alarm ARN in the resource region}"
aws arc-zonal-shift create-practice-run-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --outcome-alarms "alarmIdentifier=$OUTCOME_ALARM_ARN,type=CLOUDWATCH"
```
```bash
# MUTATION: enable automatic shifts only after the readiness review.
aws arc-zonal-shift update-zonal-autoshift-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --zonal-autoshift-status ENABLED
```
```bash
# MUTATION: a separate, manually initiated one-hour shift.
set -euo pipefail
: "${AWAY_FROM_AZ:?Set an AZ of this resource}"
SHIFT_ID=$(aws arc-zonal-shift start-zonal-shift \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --away-from "$AWAY_FROM_AZ" --expires-in 1h \
  --comment "Owned resilience exercise" --query zonalShiftId --output text)
test -n "$SHIFT_ID" && test "$SHIFT_ID" != None
printf '%s\n' "$SHIFT_ID" > owned-zonal-shift-id.txt
```
```bash
# MUTATION: cancel only the recorded manual shift after checking its ownership.
: "${SHIFT_ID:?Use the exact ID recorded for this exercise}"
aws arc-zonal-shift cancel-zonal-shift \
  --region "$AWS_REGION" --zonal-shift-id "$SHIFT_ID"
```
[Comportamiento y requisitos previos de EKS ARC](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html) · [Integración con Auto Mode/Karpenter](https://aws.amazon.com/blogs/containers/arc-zonal-shift-support-for-eks-auto-mode-and-karpenter/)

### Consideraciones sobre el almacenamiento

WaitForFirstConsumer demora el aprovisionamiento/vinculación inicial hasta que se pueda tener en cuenta la ubicación del planificador. **EBS sigue vinculado a una AZ.** Tras la pérdida de una AZ, un Pod de reemplazo en otra AZ no puede conectar ese mismo volumen. Restaure o migre los datos mediante un plan revisado de copia de seguridad/replicación y pruebe el RPO/RTO.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-ebs
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: 'true'
allowVolumeExpansion: true
reclaimPolicy: Retain
```
Este StorageClass usa el controlador EBS CSI estándar. Auto Mode usa `ebs.csi.eks.amazonaws.com` y sus propios requisitos compatibles de nodos/IAM/migración. Establezca explícitamente `encrypted: "true"` en cualquiera de los dos diseños e inspeccione el volumen EBS/la clave KMS creados. El cifrado del disco raíz/de datos del nodo de Auto Mode no demuestra que todos los PVC de las cargas de trabajo estén cifrados; el valor predeterminado actual del parámetro de StorageClass de Auto Mode es false. Retain conserva un volumen liberado para una recuperación/eliminación controlada; no es una copia de seguridad y puede conservar recursos facturables.

Para el acceso compartido al sistema de archivos entre AZ, use un sistema de archivos EFS **Regional** existente, puntos de montaje accesibles, reglas de seguridad TCP 2049, permisos revisados de puntos de acceso e IAM compatible con CSI. EFS One Zone no ofrece el mismo diseño de resiliencia. Estos ID son marcadores de posición; aquí no se crea ningún sistema de archivos.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '700'
  basePath: /resilience-demo
reclaimPolicy: Retain
mountOptions:
- tls
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: resilience-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: resilience-efs
  resources:
    requests:
      storage: 5Gi
```
La solicitud de 5Gi del PVC no es una cuota de almacenamiento de EFS aplicada. El cifrado TLS del montaje y el cifrado en reposo del sistema de archivos son configuraciones independientes. Retain también requiere un proceso documentado para limpiar los datos y los puntos de acceso.

[EBS CSI de EKS](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [Parámetros de StorageClass de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

### Enrutamiento con reconocimiento de localidad de Istio

En el ejemplo de modo sidecar de Istio, Istio obtiene la localidad del nodo que ejecuta el Pod, salvo que se configure la anulación de localidad documentada; las etiquetas de zona habituales del Pod no la definen automáticamente. Verifique los endpoints/localidades reales del proxy y la capacidad en buen estado accesible. Para el comportamiento documentado de conmutación por error de localidad se requiere la detección de valores atípicos.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-app-locality
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
    loadBalancer:
      simple: ROUND_ROBIN
      localityLbSetting:
        enabled: true
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```
Como **configuración alternativa de distribución ponderada**, sustituya `localityLbSetting` de `loadBalancer` por el siguiente fragmento. Incluye las tres zonas de origen; 80/10/10 son ponderaciones configuradas, no mediciones de localidad ni una garantía de capacidad de conmutación por error. No combine una regla distribute con una política failover incompatible.

```yaml
localityLbSetting:
  enabled: true
  distribute:
  - from: ap-northeast-2/ap-northeast-2a/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 80
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2b/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 80
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2c/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 80
```
Las cifras originales de más del 80 % de tráfico local, reducción de costos del 60–80 % y latencia inferior a 1 ms en la misma AZ se conservan únicamente como ilustraciones no verificadas. No se dispone de las fuentes de medición; el estado, la reutilización de conexiones, la mezcla de endpoints, los bytes de las solicitudes y los precios modifican el resultado.

[Conmutación por error de localidad](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/) · [Distribución ponderada](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/distribute/)

---

## Nivel 3: arquitectura basada en celdas

### Concepto de celda

Una celda es **una unidad de servicio autónoma con su propio almacén de datos, caché y cola**. Su objetivo es acotar el impacto de los fallos cuando el enrutamiento, la capacidad y las dependencias hacen cumplir el límite de la celda.

### Estrategias de partición en celdas

| Estrategia       | Descripción                       | Adecuada para                     |
| -------------- | --------------------------------- | -------------------------------- |
| Basada en clientes | Asignar una celda según el hash del ID del cliente   | SaaS multiinquilino                |
| Basada en regiones   | Particionar por ubicación geográfica  | Servicios globales                  |
| Basada en capacidad | Crear una nueva celda al alcanzar la capacidad | Distribución uniforme de la carga           |
| Basada en niveles     | Asignar una celda según el nivel de servicio              | Diferenciación Premium/Standard |

### Implementación de celdas basadas en namespaces

Los namespaces, las cuotas y NetworkPolicy proporcionan límites lógicos, no dominios de fallo independientes. Los nodos compartidos, el plano de control, CNI, DNS, los enrutadores y los servicios de datos siguen siendo dependencias. Verifique que el complemento de red aplique las políticas; el tráfico permitido es la unión de todas las políticas aplicables. El namespace/la carga de trabajo del enrutador que aparece a continuación debe existir con las etiquetas exactas.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-1
  labels:
    cell: '1'
    customer-range: a-f
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-1-quota
  namespace: cell-1
spec:
  hard:
    requests.cpu: '20'
    requests.memory: 40Gi
    limits.cpu: '40'
    limits.memory: 80Gi
    pods: '100'
    services: '20'
    persistentvolumeclaims: '50'
```
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: cell-1-limits
  namespace: cell-1
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    type: Container
```
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cell-1-isolation
  namespace: cell-1
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: cell-router
      podSelector:
        matchLabels:
          app: cell-router
    ports:
    - protocol: TCP
      port: 8080
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
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
DNS permite tráfico TCP y UDP a los Pods de CoreDNS coincidentes en kube-system. El DNS del sistema local al nodo/Auto Mode sigue una ruta distinta y requiere una verificación específica para cada modo. Esta política no permite deliberadamente el tráfico externo arbitrario: añada reglas revisadas para los endpoints o la puerta de enlace de salida que necesiten los servicios. Excluir solo 10.0.0.0/8 de 0.0.0.0/0 no aísla todas las redes privadas ni todas las celdas.

[Semántica de NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

### Fragmentación por barajado (Shuffle Sharding)

La asignación estable a un subconjunto de celdas puede reducir el solapamiento entre clientes, si el enrutamiento, los límites de admisión y la disponibilidad de los datos implementan ese diseño.

```
With 2 Cell combinations from a pool of 8 Cells:
- Customer A → Cell 1, Cell 5
- Customer B → Cell 2, Cell 7
- Customer C → Cell 1, Cell 3

When Cell 1 fails:
- Customer A → Can use Cell 5 if failover routing/data/capacity are ready
- Customer B → Not affected ✅
- Customer C → Can use Cell 3 if failover routing/data/capacity are ready
```

C(8,2)=28. Una asignación uniforme e independiente da una probabilidad exacta de colisión de pares de 1/28 (aproximadamente 3,6 %). Un fallo de una celda fija afecta a 2/8=25 % de las asignaciones en promedio, no a un máximo del 25 % de los clientes ni de la carga. Un ConfigMap o un hash, por sí solos, no implementan ni la conmutación por error ni la replicación de datos.

***

## Nivel 4: varios clústeres / varias regiones

Elija un patrón para cada recorrido de usuario y sus requisitos de coherencia de datos. Un segundo clúster o región, por sí solo, no garantiza un RTO/RPO cercano a cero. Los valores de tiempo/costo que aparecen a continuación son ilustraciones de diseño no verificadas, no resultados medidos ni compromisos de AWS.

| Patrón | Ilustración anterior de RTO | Ilustración anterior de RPO | Ilustración anterior de costo | Condición de diseño |
| --- | --- | --- | --- | --- |
| Activo-Activo | Objetivo ~0 | Objetivo ~0 | 2x+ | Enrutamiento, coherencia, gestión de conflictos y capacidad |
| Activo-Pasivo | Minutos–horas | Minutos | 1,5x | Preparación del entorno en espera, retraso de replicación y promoción |
| Aislamiento regional | No especificado | No especificado | 1x por región | Servicio regional independiente; no implica conmutación por error regional automática |
| Concentrador-radial | Minutos | Minutos | 1,3x | El concentrador es una dependencia compartida, salvo que se proteja por separado |

### ApplicationSet de Argo CD

Estas tres alternativas requieren un controlador de Argo CD/ApplicationSet existente, clústeres registrados explícitamente y accesibles con las etiquetas documentadas, credenciales del repositorio y un AppProject creado previamente y restringido al repositorio/destinos/tipos de recursos revisados. Sustituya el repositorio y la revisión de ejemplo por datos propios. Los Applications generados tienen sincronización manual: revise los destinos/manifiestos renderizados antes de habilitar cualquier política automatizada de sincronización/poda. Ningún generador aprovisiona un clúster de EKS.

#### Generador de clústeres

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-clusters
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - clusters:
      selector:
        matchLabels:
          resilience-example: 'true'
  template:
    metadata:
      name: web-app-{{.nameNormalized}}
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/web-app/overlays/{{.metadata.labels.region}}
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
#### Directorios de Git × clústeres registrados

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-region-directories
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - git:
          repoURL: https://github.com/example/owned-gitops.git
          revision: REPLACE_WITH_REVIEWED_COMMIT
          directories:
          - path: regions/*
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
              region: '{{.path.basename}}'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.path.basename}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: '{{.path.path}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
El segundo elemento hijo de matrix compara el nombre base del directorio con la etiqueta del clúster registrado y usa el valor real del servidor. Los nombres de región no se pueden convertir en URL de la API de EKS. Si falta la etiqueta o no hay coincidencias, puede que no se genere ningún Application; inspeccione el conjunto generado, no solo la validez del esquema.

#### Clúster × lista de aplicaciones

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-cluster-app-matrix
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
      - list:
          elements:
          - app: frontend
            port: '80'
          - app: backend
            port: '8080'
          - app: worker
            port: '9090'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.app}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/{{.app}}
        helm:
          parameters:
          - name: cluster.name
            value: '{{.name}}'
          - name: service.port
            value: '{{.port}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
[Parámetros de matrix de ApplicationSet](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Matrix/)

### Global Accelerator

Use endpoints ALB/NLB existentes y aptos, con TLS probado, comprobaciones de estado y suficiente capacidad regional. Lo siguiente es un ejemplo opcional de aprovisionamiento; no se ha ejecutado aquí. Guarde los ID de recursos devueltos y un plan propio para su limpieza; un fallo a mitad del proceso no elimina los recursos creados previamente. Deshabilitar un acelerador no elimina los cargos por sus recursos.

```bash
# MUTATIONS: creates a disabled, billable accelerator and its configuration.
set -euo pipefail
: "${GA_API_REGION:?Set the documented Global Accelerator API region}"
: "${ACCELERATOR_NAME:?Set a unique owned name}"
: "${REGION_ONE:?Set the first endpoint region}"
: "${REGION_TWO:?Set the second endpoint region}"
: "${REGION_ONE_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
: "${REGION_TWO_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
test "$REGION_ONE" != "$REGION_TWO"
ACCELERATOR_ARN=$(aws globalaccelerator create-accelerator \
  --region "$GA_API_REGION" --name "$ACCELERATOR_NAME" \
  --ip-address-type IPV4 --no-enabled --query Accelerator.AcceleratorArn --output text)
test -n "$ACCELERATOR_ARN" && test "$ACCELERATOR_ARN" != None
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" \
  --protocol TCP --port-ranges FromPort=443,ToPort=443 \
  --query Listener.ListenerArn --output text)
test -n "$LISTENER_ARN" && test "$LISTENER_ARN" != None
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_ONE" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_ONE_LB_ARN,Weight=100"
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_TWO" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_TWO_LB_ARN,Weight=100"
```
```bash
# MUTATION: run separately after endpoint health, routing, data and rollback checks.
: "${ACCELERATOR_ARN:?Use the accelerator just reviewed}"
aws globalaccelerator update-accelerator \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" --enabled
```
Un dial de tráfico es el porcentaje del tráfico que ya se dirige a ese grupo regional de endpoints para las conexiones nuevas; dos diales del 50 % no establecen un reparto global 50/50. El ejemplo deja ambos al 100 %. Un cambio del dial no mueve por la fuerza las conexiones existentes y las reglas de conmutación por error pueden ignorar un dial de cero. Las ponderaciones de los endpoints y los diales de tráfico son controles distintos. El estado de los endpoints ALB/NLB depende de las comprobaciones de estado de Elastic Load Balancing; definir una anulación de Global Accelerator `/healthz` no configura esas comprobaciones de los grupos de destino.

[Semántica del dial de tráfico](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups-traffic-dial.html) · [Estado de los endpoints](https://repost.aws/knowledge-center/global-accelerator-unhealthy-endpoints) · [Reglas de conmutación por error](https://repost.aws/knowledge-center/global-accelerator-failover-different-region)

### Federación multi-primary de Istio

El diseño sidecar multi-primary/múltiples redes requiere un modelo de identidad de confianza compartido, nombres distintos de clúster/red, API de Kubernetes remotas accesibles, puertas de enlace este-oeste, servicios/namespaces compatibles y un comportamiento de datos adecuado. Un ServiceEntry por sí solo no establece la federación. Limite el acceso a la puerta de enlace a las redes previstas; un balanceador de carga TLS de capa 7 que termina TLS no es compatible con AUTO_PASSTHROUGH.

El siguiente IstioOperator es una **entrada de instalación de istioctl**, no un operador dentro del clúster para aplicar con kubectl. Prepare la configuración correspondiente de Tokio y la configuración completa oficial de puerta de enlace/detección. Los indicadores de captura/asignación automática de DNS no sustituyen esa configuración.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: resilience-mesh
      multiCluster:
        clusterName: cluster-seoul
      network: network-seoul
```
```bash
# MUTATIONS: source-cluster credentials/RBAC and destination Secret may be created.
set -euo pipefail
umask 077
: "${SEOUL_CONTEXT:?Verify the owned Seoul context}"
: "${TOKYO_CONTEXT:?Verify the owned Tokyo context}"
test "$SEOUL_CONTEXT" != "$TOKYO_CONTEXT"
test ! -e tokyo-remote-secret.yaml && test ! -e seoul-remote-secret.yaml
istioctl create-remote-secret --context "$TOKYO_CONTEXT" --name cluster-tokyo > tokyo-remote-secret.yaml
istioctl create-remote-secret --context "$SEOUL_CONTEXT" --name cluster-seoul > seoul-remote-secret.yaml
# Inspect Secret metadata without printing token data; verify destination contexts first.
kubectl --context "$SEOUL_CONTEXT" -n istio-system apply -f tokyo-remote-secret.yaml
kubectl --context "$TOKYO_CONTEXT" -n istio-system apply -f seoul-remote-secret.yaml
```
Los archivos de remote-secret contienen credenciales: manténgalos en privado, exclúyalos del control de versiones y elimine las copias locales según la política de gestión de credenciales tras la instalación. Los comandos anteriores son un paso que modifica el estado después de configurar la confianza/red, no un diagnóstico de solo lectura.

El enrutamiento explícito puede usar las etiquetas de región de la carga de trabajo en las **plantillas de Pod que configure en cada clúster**. Las etiquetas de topología de los nodos no se copian automáticamente a los Pods. Trate `x-region` como entrada de enrutamiento, no como autorización. Estas ponderaciones 80/20 no implementan un protocolo de conmutación por error de datos.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cross-cluster-routing
  namespace: resilience-demo
spec:
  hosts:
  - web-app.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-region:
          exact: tokyo
    route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
  - route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: seoul
      weight: 80
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
      weight: 20
```
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cross-cluster-subsets
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  subsets:
  - name: seoul
    labels:
      workload-region: ap-northeast-2
  - name: tokyo
    labels:
      workload-region: ap-northeast-1
```
Para un servicio DNS externo no relacionado, se puede describir una entrada en su registro mediante un ServiceEntry independiente, como se muestra a continuación. Se trata de un patrón alternativo para servicios externos, con sus propios requisitos de DNS/TLS/aplicación, no de un mecanismo para descubrir el servicio de Kubernetes en un segundo clúster.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: reviewed-remote-service
  namespace: resilience-demo
spec:
  hosts:
  - remote-service.example.com
  location: MESH_EXTERNAL
  ports:
  - number: 443
    name: https
    protocol: TLS
  resolution: DNS
```
[Requisitos previos y pasos completos para Istio multi-primary](https://istio.io/latest/docs/setup/install/multicluster/multi-primary_multi-network/)

---

## Patrones de resiliencia de aplicaciones

Los ejemplos anteriores de PDB y apagado solo se aplican a las cargas de trabajo propias correspondientes. Para los porcentajes, tanto minAvailable como maxUnavailable se redondean hacia arriba: el 75 % de tres significa que se requieren tres Pods Ready, mientras que un maxUnavailable del 25 % permite uno. Las actualizaciones graduales de los controladores y la eliminación directa son controles independientes.

### Disyuntor mediante Istio

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-circuit-breaker
  namespace: resilience-demo
spec:
  host: backend-service.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
```
Estos límites se aplican al proxy/grupo de destino configurado, no a un límite de concurrencia para todo el clúster. `http2MaxRequests` limita las solicitudes HTTP activas; `maxRetries` limita los **reintentos pendientes simultáneamente**, no el número de intentos por solicitud. `minHealthPercent` controla cuándo está activa la detección de valores atípicos; no reserva ese porcentaje de capacidad en buen estado. La expulsión por errores, los límites de conexiones y los reintentos requieren ajustes basados en mediciones.

### Reintentos/tiempos de espera

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-retry-timeout
  namespace: resilience-demo
spec:
  hosts:
  - backend-service.resilience-demo.svc.cluster.local
  http:
  - match:
    - method:
        exact: GET
    route:
    - destination:
        host: backend-service.resilience-demo.svc.cluster.local
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: 5xx,reset,connect-failure
      retryRemoteLocalities: true
```
La ruta solo para GET presupone que la aplicación realmente realiza estas solicitudes de forma segura para reintentar. Los tres reintentos se suman al intento original, pero el presupuesto total de 10 s, el límite de 3 s por intento, la espera entre reintentos y el límite de concurrencia pueden impedir que se ejecuten todos los intentos. Los reintentos pueden agravar la sobrecarga o duplicar efectos secundarios; las escrituras requieren un contrato explícito de idempotencia. retryRemoteLocalities permite alternativas, pero no garantiza capacidad remota en buen estado. Actualmente, retriable-4xx de Envoy significa **solo 409**, no 408; los conflictos de bloqueo optimista pueden requerir volver a leer el estado en lugar de repetir la solicitud.

[DestinationRule de Istio](https://istio.io/latest/docs/reference/config/networking/destination-rule/) · [Condiciones de reintento de Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter)

---

## Ingeniería del caos

La ingeniería del caos prueba una hipótesis refutable sobre el estado estable mediante fallos controlados. Empiece en un entorno de pruebas representativo y propio; los experimentos en producción requieren una revisión independiente del radio de impacto, la autoridad, la telemetría, las condiciones de detención y la recuperación. Aplicar un CR puede provocar un fallo. Las configuraciones de aquí se comprobaron sin conexión, no se ejecutaron, y no demuestran que estén listas para producción.

```bash
# Read-only: verify the exact cluster/namespace and opt-in test workload.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=web-app,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb
```
### AWS Fault Injection Service (FIS)

Prepare el rol de experimento de IAM/la política de confianza, la entrada de acceso de EKS requerida (o la asignación heredada documentada), la ServiceAccount/Role/RoleBinding de Kubernetes con ámbito de namespace y los permisos de EC2/red específicos de la acción, según la guía oficial. El rol y los ARN de alarmas siguientes son marcadores de posición de una región/cuenta de ejemplo: sustitúyalos todos de forma coherente. La alarma debe existir, recibir datos relevantes y haberse probado; una condición de detención no restaura los datos ni garantiza que no haya impacto.

Los objetivos de Pod usan clusterIdentifier/namespace/selectors; **no se pueden proporcionar ARN de clúster como resourceArns para aws:eks:pod**. `kubernetesServiceAccount` es obligatorio en la acción. La eliminación de Pod usa la ruta de eliminación directa, por lo que un PDB no la impide. COUNT(1) selecciona un objetivo del conjunto habilitado y no simula una interrupción de AZ.

#### Eliminación de un Pod

```json
{
  "description": "Delete one selected test Pod; not an AZ outage",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "delete-one": {
      "actionId": "aws:eks:pod-delete",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
#### Latencia de red en un Pod

```json
{
  "description": "Add bounded IPv4 latency to one selected test Pod",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "latency": {
      "actionId": "aws:eks:pod-network-latency",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "duration": "PT1M",
        "delayMilliseconds": "200",
        "jitterMilliseconds": "50",
        "sources": "10.20.0.0/24",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
Sustituya el CIDR de destino ilustrativo por la dependencia de pruebas revisada. Esta acción de red requiere una inyección de fallos con privilegios/root y no es compatible con Fargate ni con redes bridge. Afecta a IPv4; ALL o un CIDR IPv4 no afecta a IPv6. Revise las restricciones actuales del sistema de archivos de solo lectura y la seguridad de los contenedores. No debilite el perfil de seguridad de la carga de trabajo de producción solo para ejecutar este ejemplo. FIS usa un Pod inyector y, para las acciones distintas de pod-delete, contenedores efímeros; terminar un proceso no elimina del Pod spec el registro inmutable del contenedor efímero.

#### Interrupción de red en una subred

```json
{
  "description": "One owned test subnet network disruption, not a complete AZ outage",
  "targets": {
    "test-subnet": {
      "resourceType": "aws:ec2:subnet",
      "selectionMode": "COUNT(1)",
      "resourceArns": [
        "arn:aws:ec2:ap-northeast-2:123456789012:subnet/subnet-0123456789abcdef0"
      ]
    }
  },
  "actions": {
    "network": {
      "actionId": "aws:network:disrupt-connectivity",
      "parameters": {
        "duration": "PT1M",
        "scope": "all"
      },
      "targets": {
        "Subnets": "test-subnet"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
La subred debe ser una subred de pruebas propia, dedicada y sin cargas de trabajo ajenas al experimento. Esta acción clona su NACL, añade reglas de denegación y restaura la asociación original al completarse; el tráfico dentro de la subred sigue funcionando incluso con `scope=all`. No equivale a una pérdida total de energía de una AZ. Compruebe las cuotas de NACL, IAM, la subred exacta y el acceso de administración/telemetría antes de empezar. La detención y la recuperación son asíncronas; confirme el estado final del experimento y la recuperación real de la red/carga de trabajo.

```bash
# MUTATION: stop only the recorded experiment ID, not all account experiments.
: "${AWS_REGION:?Set the experiment region}"
: "${EXPERIMENT_ID:?Set the exact running FIS experiment ID}"
aws fis stop-experiment --region "$AWS_REGION" --id "$EXPERIMENT_ID"
```
[Requisitos previos/RBAC de FIS para Pods de EKS](https://docs.aws.amazon.com/fis/latest/userguide/eks-pod-actions.html) · [Parámetros de acciones y comportamiento de subredes](https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html)

### Litmus Chaos (incubación de CNCF)

El operador revisado 3.31.0 define ChaosEngine, ChaosExperiment y ChaosResult. No define ChaosHub ni ChaosSchedule. Instale una versión revisada y cada ChaosExperiment requerido con RBAC de ámbito restringido e imágenes verificadas de runner/helper antes de usar estos ejemplos de engine. Los archivos de fallos actuales del catálogo incluyen valores predeterminados de imagen CI/latest; no los aplique sin revisarlos. La verificación del esquema no demuestra la compatibilidad con su clúster/tiempo de ejecución.

Estos ejemplos empiezan con `engineState: stop`. Después de preparar los objetivos indicados, evalúe un experimento a la vez con el workflow de la versión instalada. Un engine activo puede eliminar Pods repetidamente durante su duración; una duración de 30 segundos no promete una sola eliminación exacta. El valor fijo TARGET_PODS queda deliberadamente sin resolver hasta que seleccione un Pod por su nombre/UID actuales. No debe dejarse vacío ni ampliarse a un selector de producción completo.

#### Eliminación de Pod

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '30'
        - name: CHAOS_INTERVAL
          value: '10'
        - name: FORCE
          value: 'false'
        - name: TARGET_PODS
          value: REPLACE_WITH_ONE_REVIEWED_POD_NAME
        - name: PODS_AFFECTED_PERC
          value: '100'
```
#### Drenaje de nodo, no terminación de instancia

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: node-drain-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: node-drain-sa
  experiments:
  - name: node-drain
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_NODE
          value: REPLACE_WITH_ONE_OWNED_TEST_NODE
```
El drenaje afecta a las cargas de trabajo del nodo, además de a las que coinciden con el selector de la aplicación. Use un nodo de pruebas dedicado, un nombre explícito no vacío, un comportamiento de expulsión que tenga en cuenta los PDB y un plan de recuperación/descordonamiento. Nunca sustituya la propiedad por un selector genérico `kubernetes.io/os=linux`. Este experimento no termina el nodo EC2.

#### Error de DNS

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-dns-error-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-dns-error-sa
  experiments:
  - name: pod-dns-error
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_HOSTNAMES
          value: '["backend-service.resilience-demo.svc.cluster.local"]'
        - name: MATCH_SCHEME
          value: exact
        - name: CONTAINER_RUNTIME
          value: containerd
        - name: SOCKET_PATH
          value: /run/containerd/containerd.sock
        - name: PODS_AFFECTED_PERC
          value: '100'
```
TARGET_HOSTNAMES es una cadena que contiene una matriz JSON. Las suposiciones sobre el tiempo de ejecución/socket/privilegios deben coincidir con los nodos Linux de pruebas seleccionados; el ejemplo no es portátil a todos los tipos de nodo de EKS. Restrinja la carga de trabajo seleccionada para que este porcentaje no pueda afectar a Pods ajenos al experimento. Observe ChaosResult y el estado de la aplicación; que exista un recurso no demuestra que el experimento haya tenido éxito.

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine,chaosresult
```
[Operador Litmus 3.31.0](https://github.com/litmuschaos/chaos-operator/releases/tag/3.31.0) · [Catálogo oficial de fallos](https://github.com/litmuschaos/chaos-charts/tree/master/faults/kubernetes) · [Estado del proyecto CNCF](https://www.cncf.io/projects/litmus/)

### Chaos Mesh

Los ejemplos usan las formas CRD de la versión publicada 2.8.4. Revise la compatibilidad del clúster, el runtime/socket, la selección de nodos, los privilegios del daemon y el acceso al dashboard del Helm Chart antes de la instalación. La inyección de fallos privilegiada en el host debe usar una clase de nodo de pruebas aprobada explícitamente; no dé por sentado que es compatible con Auto Mode/Fargate/Hybrid Nodes solo porque el esquema sea válido.

NetworkChaos/IOChaos/TimeChaos se pausan con la anotación `experiment.chaos-mesh.org/pause` de esta versión. Aplicar un manifiesto en pausa sigue siendo una escritura en el clúster. Revise los objetivos y el estado antes de quitar la pausa por separado; al detenerlo, espere al estado de recuperación. La pausa no revierte los datos eliminados y los fallos de una sola ejecución tienen una semántica de pausa distinta.

#### Latencia de red

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: delay
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  delay:
    latency: 100ms
    jitter: 50ms
    correlation: '25'
  duration: 1m
```
#### Partición de red

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-partition
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: partition
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  direction: both
  target:
    mode: fixed
    value: '1'
    selector:
      namespaces:
      - resilience-demo
      labelSelectors:
        app: backend
        experiment-approved: 'true'
  duration: 1m
```
#### Latencia de E/S

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: IOChaos
metadata:
  name: review-io-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: latency
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  volumePath: /audit-data
  delay: 100ms
  percent: 50
  duration: 1m
```
Use un volumen de pruebas desechable montado en `/audit-data`. En este ejemplo no se configura el filtro opcional de rutas; confirme los archivos seleccionados antes de activarlo. percent es el porcentaje de operaciones de inyección, no un límite de capacidad. No apunte este ejemplo al directorio de datos de PostgreSQL de producción original. Verifique la recuperación y la integridad de los datos a partir de una línea base conocida.

#### Desfase horario

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: TimeChaos
metadata:
  name: review-time-offset
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  timeOffset: -2h
  clockIds:
  - CLOCK_REALTIME
  duration: 1m
```
El desfase de -2h se aplica al comportamiento de CLOCK_REALTIME del programa inyectado seleccionado, no a un cambio universal de dos horas en el nodo y todos sus relojes. Compruebe el mecanismo de inyección y el uso del reloj de la aplicación antes de inferir el comportamiento de los tokens, el planificador o las concesiones. La duración limita la ventana prevista del fallo, no el tiempo de recuperación garantizado de la aplicación.

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo \
  get networkchaos,iochaos,timechaos -o yaml
```
[Helm Chart de Chaos Mesh 2.8.4](https://github.com/chaos-mesh/chaos-mesh/tree/v2.8.4/helm/chaos-mesh) · [Controlador de pausa](https://github.com/chaos-mesh/chaos-mesh/blob/v2.8.4/controllers/common/desiredphase/controller.go)

### Marco para días de juego

Defina los umbrales de interrupción, un observador independiente y un responsable concreto de la recuperación antes de inyectar fallos. Registre por separado la detección y el restablecimiento, incluidas las observaciones fallidas o sin datos. Detenga un experimento antes de comenzar el siguiente y verifique el restablecimiento en lugar de declarar el éxito solo porque haya transcurrido el tiempo del fallo.

| Fase                  | Actividad                            | Entregable               |
| ---------------------- | ----------------------------------- | ------------------------- |
| 1. Registrar el estado estable | Recopilar líneas base de métricas            | Captura del dashboard        |
| 2. Inyectar el fallo      | Ejecutar experimentos de FIS/Litmus          | Registros del experimento           |
| 3. Observar la recuperación    | Supervisar el proceso de recuperación automática  | Medición del tiempo de recuperación |
| 4. Analizar el impacto      | Analizar la tasa de errores y los cambios de latencia | Informe de impacto             |
| 5. Revisar el análisis posterior al incidente  | Identificar mejoras y elementos de acción | Plan de mejora          |

***

## Lista de comprobación de implementación

### Nivel 1: básico

* [ ] Elegir sondeos de estado adecuados para cada aplicación de larga duración
* [ ] Establecer solicitudes/límites de recursos
* [ ] Configurar PodDisruptionBudget
* [ ] Implementar un apagado ordenado (hook preStop)
* [ ] Establecer un valor adecuado para terminationGracePeriodSeconds

### Nivel 2: Multi-AZ

* [ ] Aplicar restricciones de distribución de topología de Pods
* [ ] Verificar la distribución real de Pods/nodos y la capacidad adicional en las AZ restantes
* [ ] Planificar la recuperación del almacenamiento zonal; usar WaitForFirstConsumer para aprovisionar recursos nuevos
* [ ] Revisar la aptitud para ARC, la preparación N-1, las alarmas y la autorización independiente para la conmutación automática
* [ ] Supervisar los costos del tráfico entre AZ

### Nivel 3: basado en celdas

* [ ] Definir los límites de las celdas (Namespace o clúster)
* [ ] Implementar un enrutador de celdas
* [ ] Verificar los límites de las celdas y que el complemento de red aplique las políticas
* [ ] Implementar Shuffle Sharding
* [ ] Establecer ResourceQuota por celda

### Nivel 4: Multi-Región

* [ ] Decidir el patrón de arquitectura Multi-Región
* [ ] Configurar Global Accelerator
* [ ] Desplegar varios clústeres con ArgoCD ApplicationSet
* [ ] Establecer una estrategia de replicación de datos
* [ ] Mantener la coherencia con GitOps

***

## Consideraciones sobre los costos

A continuación se conservan las ilustraciones de costos originales no verificadas; no son precios actuales ni ahorros medidos. Los cargos entre AZ dependen del servicio, la ruta/dirección del tráfico y la región; $0,01/GB no es una tarifa universal e integral de EKS. Calcule el precio real de los recursos y la capacidad de reserva para fallos con las páginas de precios actuales de los servicios. No se volvieron a ejecutar pruebas de costos/caos.

| Elemento                       | Impacto en los costos                          | Estrategia de reducción de costos                      |
| -------------------------- | ------------------------------------ | -------------------------------------------- |
| Multi-Región Activo-Activo | 2x+ en comparación con una sola región        | Reducir el costo pasivo entre un 50 y un 70 % con Activo-Pasivo |
| Tráfico entre AZ           | $0,01/GB (dentro de la misma región)        | Reducirlo entre un 60 y un 80 % con enrutamiento con reconocimiento de localidad    |
| Instancia Spot              | Ahorro del 60–90 % en comparación con On-Demand | Aplicarlo a cargas de trabajo sin estado                 |
| Ingeniería del caos | Ilustración anterior de $100–500/mes; se aplican los costos reales de uso de FIS/recursos | Limitar los recursos y la duración del experimento |
| Arquitectura basada en celdas | Ilustración anterior de un aumento del 10–20 % | Medir el costo de aislamiento y el valor operativo |

***

## Próximos pasos

* [Depuración avanzada y respuesta a incidentes en EKS](11-eks-advanced-debugging.md)
* [Cuestionario sobre alta disponibilidad de EKS](../quizzes/eks/10-eks-resiliency-quiz.md)
* [Service Mesh de Istio](../service-mesh/02-istio.md) - Análisis detallado de disyuntores y reintentos
