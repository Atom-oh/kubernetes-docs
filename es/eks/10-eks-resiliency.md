# Resiliencia y alta disponibilidad en EKS

> **Versión de referencia de las API de los ejemplos**: Kubernetes 1.36; elija versiones de EKS con soporte vigente y controladores compatibles
> **Última actualización**: 12 de septiembre de 2026

Estos ejemplos muestran patrones de configuración; no constituyen una plataforma de producción probada. Úselos en un entorno de pruebas bajo su control y sustituya las imágenes, las rutas de comprobación de estado y las referencias de IAM e infraestructura por valores revisados. En esta auditoría no se ejecutaron clústeres, conmutaciones por error ni experimentos de caos.

RTO es el objetivo de tiempo de recuperación aceptable, incluida la detección y el restablecimiento del servicio. RPO es la ventana aceptable de pérdida de datos respecto al punto de recuperación. Usar varias AZ, replicar datos o contar con un SLA del plano de control no garantiza por sí solo una pérdida de datos nula ni un tiempo concreto de recuperación de la carga de trabajo.

## Visión general de la resiliencia

La resiliencia es **la capacidad de reducir el impacto de los fallos mientras se recupera el funcionamiento normal o se mantiene el servicio**. Va más allá de la alta disponibilidad (HA): implica diseñar el sistema anticipando fallos y preparándose para responder a ellos.

### Modelo de madurez de la resiliencia

| Nivel | Ámbito | Ejemplos de controles | Tiempos orientativos de ediciones anteriores, sin mediciones |
| --- | --- | --- | --- |
| 1. Básico | Pod/carga de trabajo | Probes, recursos, presupuesto de evicciones y cierre | Segundos–minutos |
| 2. Multi-AZ | Pérdida de una AZ | Distribución, capacidad disponible en otras AZ y recuperación del tráfico y los datos | Segundos–minutos |
| 3. Celdas | Partición del servicio | Enrutamiento y límites de dependencias y capacidad | Segundos para un impacto parcial–minutos |
| 4. Multirregión | Pérdida de una región | Conmutación regional del tráfico y los datos y procedimientos operativos | Desde objetivos próximos a cero hasta minutos u horas, según el diseño |

Las ediciones anteriores en distintos idiomas usaban intervalos orientativos diferentes. Este modelo ayuda a organizar las decisiones de diseño; no certifica el sistema ni garantiza que un nivel superior se recupere antes. Defina y mida objetivos para cada recorrido del usuario y sus dependencias.

EKS regional gestiona el plano de control en tres AZ. El SLA actual del endpoint establece una disponibilidad mensual del 99.95% para Standard Control Plane, medida en intervalos de cinco minutos, y del 99.99% para Provisioned Control Plane, en intervalos de un minuto. Estos compromisos dan derecho a créditos de servicio bajo determinadas condiciones; no garantizan los SLO, el RTO o el RPO de la aplicación. [SLA de AWS EKS](https://aws.amazon.com/eks/sla/)


> No todos los servicios requieren el nivel 4. Elija el nivel según los requisitos del SLA, la normativa y el presupuesto.

***

## Nivel 1: resiliencia básica en los Pods

### Probes de liveness, readiness y startup

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

La imagen anterior es un marcador de posición para la aplicación, no un artefacto publicado. Sustitúyala por un digest verificado e implemente las comprobaciones de estado previstas antes del despliegue. La probe de startup condiciona el inicio de las de liveness y readiness; liveness no debe fallar solo porque un servicio dependiente responda lentamente. Los valores de recursos y probes son orientativos. Los Jobs y los contenedores init no necesitan siempre estas mismas probes.

### PodDisruptionBudget (PDB)

Un PDB limita las evicciones voluntarias compatibles de los Pods que coinciden con su selector. No mantiene un número de Pods ante el fallo de una AZ o del hardware, la eliminación directa de Pods ni las actualizaciones progresivas o reducciones de réplicas del propio Deployment. La estrategia del controlador, la distribución y la capacidad de reserva requieren controles separados.

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

### Cierre ordenado

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

Este fragmento de la especificación de un Pod está destinado a una aplicación bajo su control. La acción nativa sleep de preStop es GA desde Kubernetes 1.34 y es válida para la versión de referencia 1.36. Esperar cinco segundos solo introduce una demora; no garantiza que se propaguen los cambios de endpoints o del balanceador. El periodo de gracia incluye el hook, y las actualizaciones de terminación de EndpointSlice se producen en paralelo al cierre del nodo. Los endpoints en terminación pueden seguir apareciendo con ready=false y una condición serving que permita drenar conexiones.

A continuación, el runtime envía la señal de parada configurada, normalmente SIGTERM, aunque la imagen y el runtime pueden cambiarla. La aplicación debe procesarla y completar o rechazar el trabajo antes de la terminación forzosa. No elimine manualmente PID 1 en preStop ni suponga una secuencia estricta de retirada de endpoints. Pruebe las conexiones de larga duración, la retirada del registro y el vaciado de los datos pendientes.

***

## Nivel 2: estrategia Multi-AZ

### Restricciones de distribución topológica de Pods

La distribución topológica influye en la ubicación de los Pods. No crea capacidad disponible ni traslada automáticamente los Pods existentes después de un fallo.

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

| Parámetro | Descripción |
| --- | --- |
| `maxSkew` | Con DoNotSchedule, diferencia entre el número de Pods del dominio candidato y el mínimo global |
| `topologyKey` | Criterio de distribución, como zona o nombre de host |
| `whenUnsatisfiable` | `DoNotSchedule` impone una restricción obligatoria; `ScheduleAnyway` expresa una preferencia |
| `minDomains` | Si quedan menos dominios elegibles, el mínimo global pasa a ser cero |

Por ejemplo, si quedan dos zonas elegibles con dos Pods coincidentes en cada una, minDomains=3 establece un mínimo global de cero y puede bloquear los Pods de reemplazo con maxSkew=1. minDomains=2 permite calcular la distribución de otro Pod si las demás restricciones y la capacidad lo permiten. No exige que estén ocupadas exactamente dos o tres AZ. Verifique por separado la distribución inicial en tres AZ y la capacidad de reserva en las AZ que seguirían disponibles. ScheduleAnyway es una preferencia; siguen aplicándose las demás restricciones del scheduler.

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

Los requisitos de Karpenter permiten determinadas zonas, pero no crean de antemano una distribución uniforme de nodos ni reservan capacidad para fallos. Use una versión compatible con EKS. El esquema toma como referencia la versión mantenida 1.14.1, no un requisito mínimo incondicional basado en el antiguo 1.0+. El EC2NodeClass referenciado, las AMI, el rol, las subredes y la capacidad deben haberse revisado previamente.

Los presupuestos porcentuales calculan ceil(total × porcentaje) y restan los nodos en eliminación y NotReady; prevalece el presupuesto aplicable más restrictivo. No limitan todas las interrupciones, caducidades, reparaciones o eliminaciones manuales. Los horarios están en UTC; el ejemplo bloquea las interrupciones de lunes a viernes entre las 09:00 y las 18:00 de Corea y Japón. Un presupuesto de cero no evita todos los fallos.

Los pools separados para Spot y On-Demand pueden usar pesos 100/50. Esos pesos son preferencias de aprovisionamiento y no garantizan que el pool de menor peso solo se utilice cuando Spot no esté disponible. También influyen la capacidad existente, las restricciones y la agrupación de solicitudes. Los límites de NodePool acotan el aprovisionamiento; no crean capacidad de antemano.

### Preferencia de Service por la misma zona

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

PreferSameZone y PreferSameNode son GA desde Kubernetes 1.35 y son válidos para esta versión de referencia 1.36. PreferClose es el alias anterior de PreferSameZone. Se trata de una preferencia, no de una restricción estricta de localidad ni de una garantía de latencia o coste. Compruebe el comportamiento real del proxy y de EndpointSlice y las políticas de tráfico Local. La anotación anterior topology-mode=Auto usa otra heurística de asignación de indicaciones; topology-aware-hints corresponde a la orientación antigua.

Fuentes: [PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/), [terminación de Pods](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [distribución topológica](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/), [distribución del tráfico de Service](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution) e [interrupciones de Karpenter](https://karpenter.sh/docs/concepts/disruption/).

### ARC Zonal Shift

El cambio zonal manual y el cambio zonal automático son operaciones distintas. La integración con EKS marca como no programables los nodos de la zona afectada y retira sus endpoints de EndpointSlices; no expulsa los Pods ni termina esos nodos. Auto Mode evita crear nodos y suspende las interrupciones voluntarias pertinentes en la AZ afectada. Los grupos de nodos administrados suspenden el reequilibrio entre AZ y evitan nuevos lanzamientos allí. La integración actual con Karpenter requiere las versiones, los ajustes y la configuración de IAM documentados. El cambio zonal de un balanceador es una operación sobre otro recurso.

Primero compruebe la cuenta, el recurso administrado exacto, la integración habilitada, la configuración de práctica existente y el comportamiento de las alarmas. Pruebe la capacidad de la aplicación, DNS, los datos y los nodos en las zonas que seguirían disponibles. El cambio zonal no aísla por completo la red: EKS dispone de una salvaguarda cuando todos los endpoints del servicio están en la zona afectada. Tampoco puede trasladar un volumen EBS zonal existente. Un entorno exclusivamente Auto Mode usa CoreDNS del sistema de nodos; los nodos mixtos o ajenos a Auto Mode siguen necesitando el Deployment y su capacidad.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resource region}"
: "${ARC_RESOURCE_ARN:?Set the exact owned EKS cluster or eligible load-balancer ARN}"
aws sts get-caller-identity
aws arc-zonal-shift get-managed-resource \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN"
```
Los siguientes bloques son pasos operativos independientes, no un único script de instalación. Crear la configuración de práctica inicia cambios de tráfico periódicos; inspeccione la configuración existente en lugar de recrearla. El identificador de la alarma de resultados es una cadena ARN, no un objeto alarmName/region. Habilite autoshift por separado cuando el entorno esté preparado.

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
[Comportamiento y requisitos de ARC en EKS](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html) · [Integración con Auto Mode y Karpenter](https://aws.amazon.com/blogs/containers/arc-zonal-shift-support-for-eks-auto-mode-and-karpenter/)

### Consideraciones de almacenamiento

WaitForFirstConsumer retrasa el aprovisionamiento y la vinculación iniciales hasta que se pueda considerar la ubicación decidida por el scheduler. **EBS sigue vinculado a una AZ.** Si se pierde esa AZ, un Pod de reemplazo en otra no puede adjuntar el mismo volumen. Restaure o migre los datos mediante un plan de copias de seguridad o replicación revisado y pruebe el RPO y el RTO.

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
Esta StorageClass usa el controlador EBS CSI estándar. Auto Mode usa ebs.csi.eks.amazonaws.com y tiene sus propios requisitos de nodos, IAM y migración. Establezca encrypted: "true" explícitamente en ambos diseños e inspeccione el volumen EBS y la clave KMS creados. El cifrado de los discos raíz y de datos de los nodos de Auto Mode no demuestra que todos los PVC de las cargas de trabajo estén cifrados; el valor predeterminado actual de ese parámetro de StorageClass en Auto Mode es false. Retain conserva un volumen liberado para una recuperación o limpieza controladas; no es una copia de seguridad y puede mantener recursos facturables.

Para compartir un sistema de archivos entre AZ, use un EFS **Regional** existente, destinos de montaje accesibles, reglas de seguridad para TCP 2049, permisos de puntos de acceso revisados e IAM compatible con CSI. EFS One Zone ofrece un diseño de resiliencia distinto. Los identificadores son marcadores de posición; aquí no se crea ningún sistema de archivos.

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
La solicitud de 5Gi del PVC no impone una cuota de almacenamiento de EFS. El cifrado TLS del montaje y el cifrado en reposo del sistema de archivos son ajustes separados. Retain también requiere documentar la limpieza de los puntos de acceso y los datos.

[EBS CSI en EKS](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [Parámetros de StorageClass en Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

### Enrutamiento de Istio según la localidad

En este ejemplo de Istio con sidecars, Istio obtiene la localidad del nodo donde se ejecuta el Pod, salvo que se configure la sustitución de localidad documentada. Las etiquetas de zona ordinarias del Pod no la definen automáticamente. Verifique los endpoints y las localidades reales del proxy y la capacidad disponible y accesible. El comportamiento documentado de conmutación por localidad requiere detección de valores atípicos.

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
Como **configuración alternativa de distribución ponderada**, sustituya localityLbSetting de loadBalancer por el siguiente fragmento. Incluye las tres zonas de origen. Los valores 80/10/10 son pesos configurados, no mediciones de localidad ni garantías de capacidad para la conmutación. No combine una regla distribute con una política de failover incompatible.

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
El documento original citaba más del 80% de tráfico local, una reducción de costes del 60–80% y una latencia inferior a 1 ms dentro de la misma AZ. Son cifras orientativas cuya fuente de medición no está disponible. El estado de los endpoints, la reutilización de conexiones, la composición del conjunto de endpoints, los bytes por solicitud y los precios pueden cambiar el resultado.

[Conmutación por localidad](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/) · [Distribución ponderada](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/distribute/)

---

## Nivel 3: arquitectura basada en celdas

### Concepto de celda

Una celda es **una unidad de servicio autónoma con su propio almacén de datos, caché y cola**. Busca limitar el impacto de los fallos cuando el enrutamiento, la capacidad y las dependencias hacen efectiva la separación entre celdas.

### Estrategias de partición en celdas

| Estrategia | Descripción | Uso adecuado |
| --- | --- | --- |
| Por cliente | Asignar una celda mediante un hash del ID del cliente | SaaS multiinquilino |
| Por región | Dividir según la ubicación geográfica | Servicios globales |
| Por capacidad | Crear otra celda al alcanzar la capacidad | Distribución uniforme de la carga |
| Por nivel de servicio | Asignar celdas según el nivel contratado | Diferenciación entre Premium y Standard |

### Implementación de celdas mediante namespaces

Los namespaces, las cuotas y NetworkPolicy establecen límites lógicos, no dominios de fallo independientes. Los nodos compartidos, el plano de control, el CNI, DNS, los routers y los servicios de datos siguen siendo dependencias. Verifique que el plugin de red aplica las políticas; el tráfico permitido es la unión de todas las políticas aplicables. El namespace y la carga de trabajo del router del ejemplo deben existir con las etiquetas exactas.

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
La regla de DNS permite TCP y UDP hacia los Pods CoreDNS coincidentes de kube-system. DNS local del nodo y DNS del sistema de Auto Mode siguen otra ruta y requieren una comprobación específica del modo. Esta política no permite tráfico externo arbitrario: añada reglas revisadas de endpoints o de una pasarela de salida para los servicios necesarios. Excluir únicamente 10.0.0.0/8 de 0.0.0.0/0 no aísla todas las redes privadas ni todas las celdas.

[Semántica de NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

### Shuffle Sharding

Asignar de forma estable cada cliente a un subconjunto de celdas puede reducir el solapamiento entre clientes, siempre que el enrutamiento, los límites de admisión y la disponibilidad de los datos implementen ese diseño.

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

C(8,2)=28. Una asignación uniforme e independiente da una probabilidad de coincidencia del mismo par de 1/28, aproximadamente el 3.6%. El fallo de una celda concreta afecta, en promedio, a 2/8=25% de las asignaciones; no establece un máximo del 25% de los clientes o de la carga. Un ConfigMap o un hash, por sí solos, no implementan conmutación por error ni replicación de datos.

***

## Nivel 4: varios clústeres y regiones

Elija un patrón para cada recorrido del usuario y sus requisitos de consistencia de datos. Añadir un segundo clúster o región no garantiza un RTO o RPO próximo a cero. Los tiempos y costes originales de la tabla son estimaciones de diseño sin mediciones, no resultados obtenidos ni compromisos de AWS.

| Patrón | RTO orientativo anterior | RPO orientativo anterior | Coste orientativo anterior | Condición del diseño |
| --- | --- | --- | --- | --- |
| Activo-activo | Objetivo ~0 | Objetivo ~0 | 2x+ | Enrutamiento, consistencia, resolución de conflictos y capacidad |
| Activo-pasivo | Minutos–horas | Minutos | 1.5x | Preparación del sistema en espera, retraso de replicación y promoción |
| Aislamiento regional | Sin especificar | Sin especificar | 1x por región | Servicio regional independiente; no implica conmutación regional automática |
| Hub-Spoke | Minutos | Minutos | 1.3x | El hub es una dependencia compartida, salvo que se proteja por separado |

### Argo CD ApplicationSet

Estas tres alternativas requieren un controlador Argo CD/ApplicationSet existente, clústeres accesibles registrados explícitamente con las etiquetas documentadas, credenciales del repositorio y un AppProject creado previamente y limitado al repositorio, los destinos y los tipos de recursos revisados. Sustituya el repositorio y la revisión de ejemplo por valores bajo su control. Las Applications generadas usan sincronización manual: revise los destinos y manifiestos renderizados antes de habilitar la sincronización automática o la eliminación automática de recursos. Ningún generador aprovisiona un clúster EKS.

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
#### Directorios Git × clústeres registrados

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
El segundo componente de la matriz hace coincidir el nombre base del directorio con una etiqueta del clúster registrado y utiliza el valor real de server. Los nombres de región no se pueden convertir en URL de la API de EKS. Si falta una etiqueta o no hay coincidencias, puede que no se genere ninguna Application. Inspeccione el conjunto generado, además de validar el esquema.

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
[Parámetros de la matriz de ApplicationSet](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Matrix/)

### Global Accelerator

Use endpoints ALB/NLB existentes y elegibles, con TLS y comprobaciones de estado probados y suficiente capacidad regional. El siguiente ejemplo de aprovisionamiento es opcional y no se ejecutó aquí. Guarde los ID de recursos devueltos y prepare un plan de limpieza bajo su control; un fallo a mitad del proceso no elimina los recursos ya creados. Deshabilitar un acelerador no elimina los cargos asociados al recurso.

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
El traffic dial establece, para las conexiones nuevas, el porcentaje del tráfico que ya se dirige a ese grupo regional de endpoints. Dos ajustes del 50% no crean un reparto global 50/50. El ejemplo deja ambos al 100%. Cambiar el dial no traslada de forma forzosa las conexiones existentes, y las reglas de failover pueden ignorar un dial de cero. Los pesos de los endpoints y los traffic dials son controles distintos. El estado de los endpoints ALB/NLB sigue las comprobaciones de Elastic Load Balancing; configurar /healthz en Global Accelerator no cambia las comprobaciones de sus grupos de destino.

[Semántica de traffic dial](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups-traffic-dial.html) · [Estado de los endpoints](https://repost.aws/knowledge-center/global-accelerator-unhealthy-endpoints) · [Reglas de conmutación por error](https://repost.aws/knowledge-center/global-accelerator-failover-different-region)

### Federación Istio multi-primary

El diseño con sidecars, varios planos de control primarios y varias redes requiere un modelo de identidad con confianza compartida, nombres distintos para cada clúster y red, acceso a las API remotas de Kubernetes y a las pasarelas este-oeste, servicios y namespaces compatibles y un comportamiento coherente de los datos. Un ServiceEntry por sí solo no establece la federación. Limite el acceso a las pasarelas a las redes previstas; un balanceador de capa 7 que termina TLS es incompatible con AUTO_PASSTHROUGH.

El siguiente IstioOperator es **una entrada para la instalación mediante istioctl**, no un operador dentro del clúster que se deba aplicar con kubectl. Prepare la configuración equivalente para Tokio y toda la configuración oficial de pasarelas y descubrimiento. Las opciones de captura y asignación automática de DNS no sustituyen esos pasos.

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
Los archivos remote-secret contienen credenciales: manténgalos privados, exclúyalos del control de versiones y elimine las copias locales después de la instalación conforme a la política de gestión de credenciales. Los comandos anteriores modifican el entorno después de preparar la confianza y la red; no son un diagnóstico de solo lectura.

Después, el enrutamiento explícito puede usar las **etiquetas workload-region que configure en las plantillas de Pods de cada clúster**. Las etiquetas topológicas del nodo no se copian automáticamente a los Pods. Trate x-region como una entrada de enrutamiento, no como autorización. Los pesos 80/20 no implementan un protocolo de conmutación de datos.

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
Para un servicio DNS externo independiente, otro ServiceEntry puede describir su entrada de registro, como muestra el siguiente ejemplo. Es un patrón alternativo para servicios externos, con sus propios requisitos de DNS, TLS y aplicación; no descubre el servicio Kubernetes de un segundo clúster.

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
[Requisitos y pasos completos de Istio multi-primary](https://istio.io/latest/docs/setup/install/multicluster/multi-primary_multi-network/)

---

## Patrones de resiliencia de aplicaciones

Los ejemplos anteriores de PDB y cierre solo se aplican a las cargas de trabajo bajo su control que coinciden con sus selectores. Tanto minAvailable como maxUnavailable redondean los porcentajes hacia arriba: el 75% de tres exige tres Pods Ready, mientras que un maxUnavailable del 25% permite uno no disponible. Los despliegues progresivos del controlador y la eliminación directa necesitan controles separados.

### Circuit breaker con Istio

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
Estos límites se aplican al pool de proxy/destino configurado, no establecen un máximo de concurrencia para todo el clúster. http2MaxRequests limita las solicitudes HTTP activas; maxRetries limita los **reintentos pendientes simultáneos**, no el número de intentos por solicitud. minHealthPercent controla cuándo está activa la detección de valores atípicos; no reserva ese porcentaje de capacidad en buen estado. Ajuste la expulsión por errores, los límites de conexiones y los reintentos a partir de mediciones.

### Reintentos y tiempos de espera

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
La ruta exclusiva para GET presupone que la aplicación hace que esas solicitudes sean realmente seguras de reintentar. Los tres reintentos se añaden al intento original, pero el presupuesto total de 10s, el límite de 3s por intento, las esperas entre reintentos y el límite de concurrencia pueden impedir que se ejecuten todos. Los reintentos pueden agravar la sobrecarga o repetir efectos secundarios; las escrituras requieren un contrato de idempotencia explícito. retryRemoteLocalities permite usar alternativas, pero no garantiza capacidad remota disponible. En Envoy, retriable-4xx significa actualmente **solo 409**, no 408. Los conflictos de bloqueo optimista pueden exigir volver a leer el estado en lugar de repetir la solicitud.

[DestinationRule de Istio](https://istio.io/latest/docs/reference/config/networking/destination-rule/) · [Condiciones de reintento de Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter)

---

## Ingeniería del caos

La ingeniería del caos pone a prueba una hipótesis de estado estable que pueda refutarse mediante fallos controlados. Empiece en un entorno de pruebas representativo bajo su control. Los experimentos en producción requieren revisar por separado el alcance del impacto, la autorización, la telemetría, las condiciones de parada y la recuperación. Aplicar un recurso personalizado puede activar un fallo. Estas configuraciones se comprobaron sin conexión, no se ejecutaron y no demuestran que el entorno esté preparado para producción.

```bash
# Read-only: verify the exact cluster/namespace and opt-in test workload.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=web-app,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb
```
### AWS Fault Injection Service (FIS)

Prepare el rol IAM del experimento y su política de confianza, la entrada de acceso de EKS necesaria o el mapeo antiguo documentado, los recursos Kubernetes ServiceAccount/Role/RoleBinding del namespace y los permisos EC2 y de red específicos de la acción según la guía oficial. Los ARN de rol y alarma siguientes son marcadores de posición de una misma región y cuenta; sustitúyalos todos de forma coherente. La alarma debe existir, recibir datos útiles y haberse probado. Una condición de parada no restaura datos ni garantiza un impacto nulo.

Los destinos de Pods usan clusterIdentifier, namespace y selectores; **no se pueden proporcionar ARN de clúster como resourceArns de aws:eks:pod**. La acción requiere kubernetesServiceAccount. La eliminación de Pods usa la ruta de eliminación directa, por lo que un PDB no la impide. COUNT(1) selecciona un destino del conjunto que se ha habilitado para la prueba; no simula una caída de AZ.

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
Sustituya el CIDR de destino orientativo por el de la dependencia de pruebas revisada. Esta acción de red requiere inyección de fallos con privilegios de root y no admite Fargate ni redes bridge. Afecta a IPv4; ALL o un CIDR IPv4 no afecta a IPv6. Revise las restricciones actuales de sistema de archivos raíz de solo lectura y de seguridad del contenedor. No reduzca la seguridad de la carga de producción para ejecutar este ejemplo. FIS usa un Pod inyector y, salvo para pod-delete, contenedores efímeros. Terminar un proceso no elimina de la especificación del Pod el registro inmutable del contenedor efímero.

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
La subred debe ser una subred de pruebas dedicada bajo su control, sin cargas de trabajo ajenas. La acción clona su NACL, añade reglas de denegación y restaura la asociación original al finalizar. El tráfico interno de la subred sigue funcionando incluso con scope=all. No equivale a un corte de energía de toda una AZ. Antes de iniciar la prueba, verifique las cuotas de NACL, IAM, la subred exacta y el acceso de administración y telemetría. La parada y la recuperación son asíncronas; confirme el estado final del experimento y la recuperación real de la red y las cargas de trabajo.

```bash
# MUTATION: stop only the recorded experiment ID, not all account experiments.
: "${AWS_REGION:?Set the experiment region}"
: "${EXPERIMENT_ID:?Set the exact running FIS experiment ID}"
aws fis stop-experiment --region "$AWS_REGION" --id "$EXPERIMENT_ID"
```
[Requisitos y RBAC de FIS para Pods EKS](https://docs.aws.amazon.com/fis/latest/userguide/eks-pod-actions.html) · [Parámetros de acciones y comportamiento de subredes](https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html)

### Litmus Chaos (proyecto CNCF en incubación)

El operador 3.31.0 revisado define ChaosEngine, ChaosExperiment y ChaosResult. No define ChaosHub ni ChaosSchedule. Antes de usar estos ejemplos de motores, instale una versión revisada y cada ChaosExperiment requerido, con RBAC de alcance limitado e imágenes verificadas para los ejecutores y auxiliares. Los archivos actuales de fallos del catálogo incluyen imágenes predeterminadas de CI/latest; no los aplique sin revisarlos. Validar el esquema no demuestra la compatibilidad con su clúster y runtime.

Estos ejemplos empiezan con engineState: stop. Una vez preparados los destinos indicados, evalúe un experimento cada vez siguiendo el flujo de la versión instalada. Un motor activo puede eliminar Pods repetidamente durante el experimento; una duración de 30 segundos no garantiza una única eliminación. TARGET_PODS queda sin resolver de forma deliberada hasta que seleccione un Pod por su nombre y UID actuales. No lo deje vacío ni amplíe la selección a todos los Pods de producción.

#### Eliminación de Pods

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
#### Drenaje de nodos sin terminar la instancia

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
El drenaje afecta a otras cargas de trabajo del nodo además de las que coinciden con el selector de aplicación. Use un nodo de pruebas dedicado, un nombre explícito no vacío, evicciones que respeten el PDB y un plan de recuperación que vuelva a permitir la programación en el nodo. Un selector genérico kubernetes.io/os=linux no identifica un nodo bajo su control. Este experimento no termina el nodo EC2.

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
TARGET_HOSTNAMES es una cadena que contiene un array JSON. Los requisitos de runtime, socket y privilegios deben coincidir con los nodos Linux de pruebas seleccionados; el ejemplo no es portable a todos los tipos de nodos EKS. Limite la carga seleccionada para que el porcentaje no pueda afectar a Pods ajenos. Observe ChaosResult y el estado de la aplicación: que exista un recurso no demuestra que el experimento se haya completado correctamente.

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine,chaosresult
```
[Operador Litmus 3.31.0](https://github.com/litmuschaos/chaos-operator/releases/tag/3.31.0) · [Catálogo oficial de fallos](https://github.com/litmuschaos/chaos-charts/tree/master/faults/kubernetes) · [Estado del proyecto en CNCF](https://www.cncf.io/projects/litmus/)

### Chaos Mesh

Los ejemplos usan los esquemas de CRD de la versión publicada 2.8.4. Antes de instalar el chart Helm, revise el runtime y el socket, la selección de nodos, los privilegios del daemon, el acceso al panel y la compatibilidad del clúster. La inyección privilegiada de fallos del host debe usar una clase de nodos de pruebas aprobada explícitamente. Validar el esquema no demuestra que sea compatible con Auto Mode, Fargate o Hybrid Nodes.

Los NetworkChaos, IOChaos y TimeChaos siguientes están pausados mediante la anotación experiment.chaos-mesh.org/pause de esta versión. Aplicar un manifiesto pausado sigue siendo una escritura en el clúster. Revise los destinos y el estado antes de quitar la pausa por separado; al detenerlo, espere al estado de recuperación. Pausar no recupera datos eliminados, y los fallos de una sola ejecución tienen una semántica de pausa distinta.

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
Use un volumen de pruebas desechable montado en /audit-data. Este ejemplo no establece el filtro de ruta opcional; confirme los archivos seleccionados antes de activarlo. percent indica el porcentaje de operaciones en que se inyecta el fallo, no un límite de capacidad. No dirija el ejemplo al directorio de datos de PostgreSQL de producción del documento original. Verifique la recuperación y la integridad de los datos frente a una referencia conocida.

#### Desfase de tiempo

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
El desfase -2h afecta al comportamiento de CLOCK_REALTIME del programa seleccionado para la inyección; no cambia universalmente dos horas el nodo y todos sus relojes. Compruebe el mecanismo de inyección y el uso del reloj por la aplicación antes de sacar conclusiones sobre tokens, el scheduler o los leases. La duración acota la ventana de fallo prevista, no garantiza el tiempo de recuperación de la aplicación.

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo \
  get networkchaos,iochaos,timechaos -o yaml
```
[Chart de Chaos Mesh 2.8.4](https://github.com/chaos-mesh/chaos-mesh/tree/v2.8.4/helm/chaos-mesh) · [Controlador de pausa](https://github.com/chaos-mesh/chaos-mesh/blob/v2.8.4/controllers/common/desiredphase/controller.go)

### Marco de Game Day

Antes de inyectar el fallo, defina los umbrales para abortar, un observador independiente y un responsable concreto de la recuperación. Registre por separado la detección y el restablecimiento, incluidas las observaciones fallidas o sin datos. Detenga un experimento antes de empezar el siguiente y verifique el restablecimiento; que termine la duración del fallo no basta para declarar la prueba satisfactoria.

| Fase | Actividad | Entregable |
| --- | --- | --- |
| 1. Registrar el estado estable | Recoger métricas de referencia | Captura del panel |
| 2. Inyectar el fallo | Ejecutar experimentos FIS/Litmus | Registros del experimento |
| 3. Observar la recuperación | Supervisar el proceso de recuperación automática | Medición del tiempo de recuperación |
| 4. Analizar el impacto | Analizar los cambios en errores y latencia | Informe de impacto |
| 5. Revisión posterior | Identificar mejoras y acciones | Plan de mejora |

***

## Lista de comprobación de implementación

### Nivel 1: básico

* [ ] Elegir probes de estado adecuadas para cada aplicación de larga duración
* [ ] Establecer las solicitudes y los límites de recursos
* [ ] Configurar PodDisruptionBudget
* [ ] Implementar el cierre ordenado con un hook preStop
* [ ] Establecer un terminationGracePeriodSeconds adecuado

### Nivel 2: Multi-AZ

* [ ] Aplicar restricciones de distribución topológica de Pods
* [ ] Verificar la distribución real de Pods y nodos y la capacidad de reserva de las AZ que seguirían disponibles
* [ ] Planificar la recuperación del almacenamiento zonal; usar WaitForFirstConsumer para el nuevo aprovisionamiento
* [ ] Revisar los requisitos de ARC, la preparación N-1, las alarmas y la autorización independiente de autoshift
* [ ] Supervisar los costes de tráfico entre AZ

### Nivel 3: basado en celdas

* [ ] Definir los límites de las celdas mediante namespaces o clústeres
* [ ] Implementar el router de celdas
* [ ] Verificar los límites de las celdas y la aplicación de políticas del plugin de red
* [ ] Implementar Shuffle Sharding
* [ ] Establecer ResourceQuota para cada celda

### Nivel 4: multirregión

* [ ] Elegir el patrón de arquitectura multirregión
* [ ] Configurar Global Accelerator
* [ ] Desplegar en varios clústeres con ArgoCD ApplicationSet
* [ ] Establecer la estrategia de replicación de datos
* [ ] Mantener la coherencia mediante GitOps

***

## Consideraciones de costes

La tabla conserva las estimaciones orientativas del documento original; no son precios actuales ni ahorros medidos. Los cargos entre AZ dependen del servicio, la ruta y dirección del tráfico y la región. $0.01/GB no es una tarifa universal de EKS que incluya todos los costes. Calcule el coste de los recursos reales y de la capacidad de reserva para fallos usando las páginas de precios actuales de cada servicio. No se repitieron las pruebas de costes o caos.

| Elemento | Impacto en el coste | Estrategia de reducción |
| --- | --- | --- |
| Multirregión activo-activo | 2x+ respecto a una sola región | Reducir un 50–70% la parte pasiva con activo-pasivo |
| Tráfico entre AZ | $0.01/GB dentro de la misma región | Reducir un 60–80% mediante enrutamiento por localidad |
| Instancias Spot | Ahorro del 60–90% respecto a On-Demand | Usarlas en cargas sin estado |
| Ingeniería del caos | Estimación anterior de $100–500/mes; se factura el uso real de FIS y los recursos | Limitar los recursos y la duración de los experimentos |
| Arquitectura de celdas | Estimación anterior de un incremento del 10–20% | Medir el coste del aislamiento y su valor operativo |

***

## Próximos pasos

* [Depuración avanzada y respuesta a incidentes en EKS](11-eks-advanced-debugging.md)
* [Cuestionario de alta disponibilidad en EKS](../quizzes/eks/10-eks-resiliency-quiz.md)
* [Malla de servicios Istio](../service-mesh/02-istio.md): circuit breaker y reintentos en profundidad
