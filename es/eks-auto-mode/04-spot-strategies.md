# Estrategias de utilización de instancias Spot

> **Versiones compatibles**: EKS Auto Mode GA; versión base del ejemplo: EKS 1.36
> **Última actualización**: 12 de septiembre de 2026

Spot intercambia interrupciones e incertidumbre de capacidad por precios de EC2 potencialmente más bajos. La capacidad mixta, la diversificación y las réplicas pueden mejorar la resiliencia, pero ninguna de ellas por sí sola garantiza la disponibilidad ni el ahorro. Usa la cuenta y el contexto revisados, así como el NodeClass de los capítulos anteriores.

Los manifiestos son ejemplos de laboratorio comprobados localmente con esquemas; no son una prueba de conmutación por error en producción. Usan una taint/toleration `spot-lab` y una selección explícita de pool para reducir la colocación accidental de cargas de trabajo ajenas. Las taints no constituyen un límite de seguridad entre clientes (tenants). Revisa el número de réplicas y los límites de recursos antes de aplicar los manifiestos; estos ejemplos pueden crear nodos facturables. No se aprovisionaron instancias Spot ni se consultó la API EC2 Spot Price History ni los datos de facturación de ningún cliente durante esta auditoría.

## Capacidad mixta y una base deliberada

El pool siguiente permite tanto Spot como On-Demand. Dentro de un pool elegible, Auto Mode prioriza los tipos de capacidad permitidos; Spot tiene preferencia sobre On-Demand cuando ambos están permitidos y disponibles. Si también se permite `reserved` y existe una reserva adecuada, esta tiene mayor prioridad. El orden de los elementos de la lista y el peso de NodePool no fijan el porcentaje de capacidad Spot.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: spot-lab
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
  namespace: spot-lab
spec:
  replicas: 10
  selector:
    matchLabels:
      app: spot-friendly
  template:
    metadata:
      labels:
        app: spot-friendly
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values:
                - spot
      containers:
      - name: app
        image: nginx:1.30.6
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: mixed-capacity
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

La afinidad preferida del Pod es una preferencia, no un requisito ni una reserva. No promete una conmutación instantánea a On-Demand, una proporción fija ni el reemplazo dentro de una ventana de interrupción. La capacidad existente, las restricciones, las cuotas y la disponibilidad real siguen siendo relevantes.

Para un Deployment de base independiente que deba usar On-Demand, sustituye la preferencia por Spot de la plantilla del Pod por una selección estricta como la siguiente, conservando la toleration del laboratorio. Mantén en ejecución un número adecuado de réplicas de base; permitir On-Demand en un pool no mantiene por sí solo capacidad de reserva lista.

```yaml
nodeSelector:
  karpenter.sh/nodepool: mixed-capacity
  karpenter.sh/capacity-type: on-demand
tolerations:
- key: spot-lab
  operator: Equal
  value: 'true'
  effect: NoSchedule
```

Este selector exige intencionalmente `on-demand`; no incluye capacidad `reserved`. Revisa las etiquetas y la configuración de reservas si más adelante usas reservas de capacidad. On-Demand no garantiza la durabilidad de los datos ni la disponibilidad de capacidad.

## Diversificar la capacidad compatible

Un pool de capacidad Spot está vinculado a un tipo de instancia y una zona de disponibilidad (AZ). Disponer de más tipos/AZ compatibles ofrece más opciones al asignador; no hace que las interrupciones sean independientes ni duplica la capacidad por el mero hecho de enumerar dos arquitecturas.

El ejemplo permite la generación 5 y posteriores en vez de fijar el límite superior en 7. Confirma la compatibilidad de las imágenes, los binarios, el almacenamiento y el rendimiento antes de ampliar las restricciones.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
        - i
        - d
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - large
        - xlarge
        - 2xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: '100'
    memory: 400Gi
```

`consolidationPolicy` y `consolidateAfter` controlan la consolidación, no el tiempo que se tarda en responder a una interrupción de EC2. Varias arquitecturas requieren imágenes y dependencias compatibles con varias arquitecturas. Ampliar el rango de generaciones o tamaños solo resulta útil si siguen siendo adecuados para la carga de trabajo y están disponibles en las AZ seleccionadas.

## Separar los presupuestos de interrupciones voluntarias de las interrupciones de EC2

Auto Mode ofrece gestión nativa de interrupciones Spot; para este fin no requiere un Node Termination Handler adicional ni una cola SQS gestionada por el usuario. No despliegues el DaemonSet NTH anterior, que estaba averiado, en nodos de Auto Mode. Si coexisten otros tipos de nodos, configura por separado la gestión de sus interrupciones, con una selección de destino y permisos deliberados.

Los presupuestos de interrupción de NodePool limitan las interrupciones voluntarias, como la consolidación y la desviación. No pueden impedir que EC2 recupere capacidad Spot, prolongar el aviso ni garantizar que la capacidad de reemplazo esté lista.

Se tienen en cuenta todos los presupuestos aplicables a la vez y se aplica el margen más restrictivo. Las entradas `10%` y `3` que aparecen a continuación no son alternativas. Los porcentajes se redondean hacia arriba, y los nodos que se están eliminando o no están listos consumen el margen; para 20 nodos que, por lo demás, estén en buen estado, estas dos entradas permiten como máximo dos nuevas interrupciones voluntarias fuera de la ventana de presupuesto cero.

Este ejemplo protege **de lunes a viernes, de 09:00 a 18:00 en Seúl (KST)**, iniciando una ventana de nueve horas a las **00:00 UTC**. Los horarios de los presupuestos de Karpenter usan UTC. El horario anterior `0 9-18 * * mon-fri` iniciaba otra ventana de nueve horas cada hora, extendiendo el intervalo bloqueado hasta el día siguiente en vez de terminar a las 18:00.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-with-disruption-budget
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
    - nodes: '3'
    - nodes: '0'
      schedule: 0 0 * * mon-fri
      duration: 9h
  limits:
    cpu: '100'
    memory: 400Gi
```

Adapta la ventana a tu calendario operativo; otras zonas horarias y los cambios de horario de verano requieren una conversión deliberada. Un presupuesto voluntario cero puede retrasar tareas de mantenimiento útiles y aun así no detiene las interrupciones involuntarias.

## Apagado ordenado dentro del tiempo realmente disponible

Normalmente, EC2 emite un aviso de dos minutos antes de detener o terminar una instancia por una interrupción, pero la entrega del aviso es de mejor esfuerzo y no está garantizada. La hibernación tiene un comportamiento distinto, con inicio inmediato. No consideres que los dos minutos son tiempo garantizado para cada Pod: la detección, la expulsión, el trabajo de la aplicación y los cambios de enrutamiento consumen tiempo, y los fallos pueden impedir que se gestione el aviso.

`terminationGracePeriodSeconds` es un presupuesto de apagado de Kubernetes, no una ampliación del plazo de EC2. `preStop` se ejecuta dentro de ese presupuesto, antes de la señal de parada normal. Un `sleep 90` sin más desperdicia la mayor parte de un presupuesto de 120 segundos y no implementa el apagado de la aplicación ni la creación de puntos de control.

Este ejemplo específico de nginx inicia la salida ordenada de inmediato, tiene una sonda HTTP real de disponibilidad y registra correctamente el nombre del nodo. Para otra aplicación, implementa y prueba su propio gestor de señales de parada, la transición de disponibilidad, la finalización del trabajo en curso y los puntos de control persistentes. Los 60 segundos elegidos son un presupuesto máximo de ejemplo, no tiempo garantizado disponible.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
  namespace: spot-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: nginx:1.30.6
        lifecycle:
          preStop:
            exec:
              command:
              - nginx
              - -s
              - quit
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: spot-aware
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: spot-with-disruption-budget
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: spot-aware-budget
  namespace: spot-lab
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: spot-aware
```

`NODE_NAME` recibe el nombre del nodo mediante la Downward API. No indica si la instancia es Spot, y los campos del Pod de la Downward API no exponen automáticamente las etiquetas del nodo. Por lo general, las aplicaciones deberían gestionar la terminación ordenada independientemente de la opción de compra. Si se necesita el tipo de capacidad, proporciona metadatos verificados mediante un mecanismo revisado en lugar de depender de las credenciales de IMDS del nodo.

El ejemplo requiere dos dominios de zonas de disponibilidad elegibles y distribuye las seis réplicas con `maxSkew: 1`. Las restricciones estrictas `DoNotSchedule` pueden dejar Pods en estado Pending cuando una zona de disponibilidad o la capacidad no están disponibles; no crean capacidad. Revisa las ventajas y desventajas antes de exigir tres dominios, y no des por sentado que la distribución entre AZ también distribuye los tipos de instancia dentro de una AZ.

El PDB limita la expulsión voluntaria de la aplicación; no puede conservar una VM recuperada por EC2. Más réplicas solo ayudan si también se validan la gestión del tráfico, la capacidad elegible, la topología y la recuperación ante fallos.

## Adecuación de la carga de trabajo

| Carga de trabajo | Punto de partida y validación requerida |
|----------|--------|
| Web sin estado/inferencia | Capacidad Spot tolerante a interrupciones, con una base crítica deliberada y latencia/conmutación por error probadas |
| Lotes/CI | Spot puede ser adecuado para trabajo reintentable e idempotente; los trabajos con plazos estrictos pueden necesitar otra capacidad |
| Entrenamiento prolongado o procesamiento con estado | Puntos de control persistentes periódicos y reanudación/reproducción probadas, no una garantía de crear el último punto de control en el último momento |
| Base de datos de una sola instancia o quórum crítico | Evita la exposición a interrupciones si no cuentas con una arquitectura de recuperación explícita; On-Demand por sí solo no protege los datos locales |
| Desarrollo/pruebas | Usa límites de costo y tolera la escasez de capacidad; no des por sentado que los trabajos que solo usan Spot siempre se iniciarán |

Mantén la única copia de estado importante fuera del almacenamiento local desechable del nodo. Valida el almacenamiento persistente, las copias de seguridad y la restauración independientemente de la opción de compra de la instancia.

## Ilustración histórica de costos, no una cotización actual

La guía anterior publicó estos importes mensuales sin indicar una región, una combinación de horas de instancia, el ámbito de facturación ni una medición reproducible. Se conservan como **ejemplos didácticos sin verificar**, no como ahorros medidos con la versión actual de EKS.

| Ejemplo | Importe anterior de On-Demand | Importe anterior de Spot | Reducción aritmética |
|---------|------------------------|-------------------|----------------------|
| Lotes | $1,000/mes | $300/mes | 70% |
| Desarrollo/pruebas | $2,000/mes | $500/mes | 75% |
| CI/CD | $500/mes | $150/mes | 70% |
| API no crítica | $3,000/mes | $1,200/mes | 60% |

AWS anuncia descuentos de EC2 Spot de hasta un 90%; esto no es un descuento mínimo ni una garantía de ahorro para toda la carga de trabajo. Spot Instance Advisor resume datos del último mes sobre interrupciones y ahorros, promediados entre zonas de disponibilidad, y puede tener retrasos. Usa el historial de precios Spot actual específico de cada AZ o los datos de facturación reales para calcular precios; los intervalos históricos de interrupción no predicen lo que ocurrirá con tu siguiente trabajo.

Compara el mismo trabajo útil, la misma región, el mismo período y el mismo objetivo de disponibilidad:

```text
Baseline total =
  sum(baseline On-Demand node-hours[type] * On-Demand rate[type])
  + other baseline costs

Actual total =
  sum(billed Spot node-hours[type, AZ] * time-weighted Spot rate[type, AZ])
  + sum(billed On-Demand fallback node-hours[type] * On-Demand rate[type])
  + other actual costs

Net savings = Baseline total - Actual total
```

Usa horas de forma coherente con las tarifas por hora y pondera los precios cambiantes según los intervalos de uso realmente facturados. Las horas facturadas de Spot y de la capacidad de respaldo deben incluir los reintentos, el solapamiento y el trabajo de recuperación por los que realmente se haya pagado. No restes un segundo cargo genérico por «sobrecoste de interrupción» si ese trabajo ya está incluido en las horas facturadas.

Incluye de forma coherente en los otros costos las tarifas de gestión pertinentes de Auto Mode, los cargos del plano de control, EBS, redes/NAT, transferencia de datos, registro y licencias. Las tarifas de Auto Mode son adicionales a la opción de compra de EC2. El antiguo atajo `interrupt count × recovery time × instance count` era ambiguo en cuanto a las unidades y a si las interrupciones ya se habían contabilizado en todo el clúster.

## Validación operativa

Antes de depender de Spot, prueba el comportamiento de interrupción y recuperación en un entorno aprobado, incluidos los casos sin aviso o con aviso tardío, la falta de capacidad de reemplazo, el trabajo en curso, la descarga de imágenes, la recuperación del almacenamiento y las restricciones estrictas de topología. Observa el trabajo perdido real y el costo facturado de recuperación. Esta auditoría solo realizó comprobaciones locales de esquemas, ventanas de programación y configuración; no ejecutó estos experimentos de fallo.

## Referencias

- [Avisos de interrupción Spot](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [Gestión nativa de interrupciones de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [Prioridad del tipo de capacidad](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Presupuestos de interrupción y horarios UTC de Karpenter](https://karpenter.sh/v1.14/concepts/disruption/)
- [Terminación de Pods y preStop](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Distribución de topología](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Campos de la Downward API](https://kubernetes.io/docs/concepts/workloads/pods/downward-api/)
- [Apagado ordenado de nginx](https://nginx.org/en/docs/control.html)
- [Información publicada por EC2 sobre descuentos Spot](https://aws.amazon.com/ec2/spot/)
- [Spot Instance Advisor](https://aws.amazon.com/ec2/spot/instance-advisor/)
- [API del historial de precios Spot](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSpotPriceHistory.html)
- [Precios de EKS Auto Mode](https://aws.amazon.com/eks/pricing/)

< [Anterior: Comportamiento del escalado](./03-scaling-behavior.md) | [Tabla de contenidos](./README.md) | [Siguiente: Operaciones](./05-operations.md) >
