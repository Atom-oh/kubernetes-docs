# Argo Rollouts con enrutamiento por zona

> **Base de verificación**: Istio 1.31.0, Argo Rollouts 1.10.1, Kubernetes 1.32–1.37
> **Última revisión**: 16 de octubre de 2026
> **Dificultad**: Avanzada

Esta guía diferencia las versiones canary zonales independientes de la conmutación por error entre zonas de disponibilidad (AZ). El ejemplo principal es un **esquema de enrutamiento y aislamiento zonal**: un grupo de clientes selecciona los Services estable/canary de una zona. No implementa la conmutación automática a otra zona cuando desaparecen esos endpoints.

## Tabla de contenido

1. [Definición del problema](#problem-definition)
2. [Descripción de la arquitectura](#architecture-overview)
3. [Decisiones clave de diseño](#key-design-decisions)
4. [Guía de implementación](#implementation-guide)
5. [Flujo del tráfico](#traffic-flow)
6. [Solución de problemas](#troubleshooting)
7. [Prácticas recomendadas](#best-practices)

## Definición del problema {#problem-definition}

### Interrupciones de Spot y PDB

AWS puede retirar capacidad Spot, por lo que hay que planificar la pérdida correlacionada de capacidad. Los avisos de interrupción se envían según disponibilidad y no están garantizados; los avisos de detención o terminación suelen conceder dos minutos, mientras que la hibernación comienza de inmediato. Los grupos de nodos administrados de EKS intentan reemplazar nodos y redistribuir la capacidad, pero no garantizan que un reemplazo esté Ready antes de vaciar el nodo interrumpido.

Un PodDisruptionBudget limita las operaciones voluntarias de desalojo realizadas a través de la API de Eviction. No evita interrupciones de EC2, fallos de nodos, la eliminación directa de Pods ni todas las actualizaciones iniciadas por controladores. Rollouts no crea ni administra los PDB que aparecen a continuación; el equipo de la aplicación los define y Kubernetes calcula su estado.

Con nueve Pods coincidentes en estado saludable y un valor entero de **`minAvailable: 6`**, el margen ilustrativo para interrupciones voluntarias es de tres. Si solo quedan seis saludables, ese margen es cero. No significa «un mínimo del 33 % que exige seis Pods»: con nueve Pods esperados, `minAvailable: "33%"` se redondea hacia arriba a tres. `maxUnavailable` porcentual tiene otra semántica y requiere considerar cómo el controlador escala.

Dividir ese presupuesto global en `minAvailable: 1` por zona cambia el nivel de protección. Si se pierde una zona, los presupuestos de las dos restantes pueden permitir desalojos voluntarios hasta dejar un Pod saludable en cada una, en lugar de preservar seis a nivel global. Esto puede servir para operaciones independientes, pero representa otra política de disponibilidad y capacidad. Un presupuesto que selecciona Pods estables y canary tampoco garantiza capacidad en cada destino ponderado por separado.

### Objetivos y restricciones

| Diseño | Versiones zonales independientes | Conmutación por error entre AZ | Restricción principal |
|---|---|---|---|
| Una revisión/subconjunto compartido con endpoints en varias AZ | No permite control independiente de revisiones por zona | Posible dentro del grupo de endpoints seleccionado | Capacidad saludable y versiones/estado de datos compatibles en la otra AZ |
| Rollouts por zona y Services filtrados por zona, como aquí | Sí | La configuración de localidad no la proporciona | Si el grupo de una zona seleccionada queda vacío, sigue vacío |
| Enrutamiento de entrada independiente y consciente del estado de salud antes de las pasarelas/cadenas zonales | Se puede diseñar | Requiere su propia política/controlador y pruebas | Coordinación adicional de enrutamiento, capacidad, identidad y recuperación |

No afirmes que se obtienen las tres propiedades —filtrado zonal estricto, hashes independientes por zona y conmutación transparente por error— con solo añadir un DestinationRule. Un diseño de enrutamiento de entrada independiente queda fuera de este esquema de despliegue y no se ha probado en producción aquí.

## Descripción de la arquitectura {#architecture-overview}

Un Service común llamado `test` proporciona el nombre DNS. Para los clientes con sidecar, un VirtualService elige una ruta zonal mediante una **etiqueta explícita en el Pod cliente**. Cada ruta apunta a los Services estable/canary de esa zona. Un Rollout independiente controla los hashes de esos Services y los pesos de su ruta con nombre propio.

Istiod compila la configuración en Envoy. Los objetos VirtualService/DestinationRule no son saltos de red. Un cliente fuera de la malla puede usar la selección normal de endpoints de Kubernetes del Service común y omitir estas reglas de ruta; las etiquetas de enrutamiento no son un límite de seguridad.

Los Pods de cada zona se programan únicamente en su AZ configurada. Por ello, los Services de la zona A no contienen endpoints de reserva de las zonas B o C. Un estado de despliegue independiente tampoco elimina las dependencias compartidas del plano de control, el servidor de API, la red o la base de datos.

## Decisiones clave de diseño {#key-design-decisions}

### 1. Propiedad de las rutas

Rollouts 1.10 concilia los pesos de ruta configurados y los destinos administrados compatibles; no reemplaza a ciegas todos los arreglos de destinos. Usar nombres de ruta diferentes evita que los controladores compitan por los pesos deseados. Sin embargo, tres controladores que actualicen un mismo VirtualService aún pueden encontrar conflictos de `resourceVersion` de Kubernetes y demoras de conciliación. Si se necesita un aislamiento más sólido del plano de control, se pueden usar objetos independientes o enrutamiento de entrada.

Este esquema usa rutas distintas (`zone-a-route`, `zone-b-route`, `zone-c-route`) y **distribución del tráfico a nivel de host**. No combina la gestión de los hashes de Service con la gestión de subconjuntos en DestinationRule. La [guía de integración](08-argo-rollouts.md) explica ambas alternativas.

### 2. Etiquetas de cliente y AZ real

`sourceLabels` selecciona las cargas de trabajo de origen cuando Istiod crea su configuración de malla; no coincide con encabezados de solicitud durante la ejecución. Las etiquetas de nodo, como `topology.kubernetes.io/zone`, no se copian automáticamente a los Pods. La etiqueta de Pod personalizada `routing.example.com/zone: a` debe corresponderse con una ubicación verificada en la AZ prevista.

Estos selectores se aplican a los clientes de la malla, no a solicitudes externas genéricas que llegan a una pasarela de entrada. Conserva el ámbito de la pasarela `mesh`. En este ejemplo, los grupos de clientes desconocidos reciben una respuesta 503 explícita en lugar de seleccionar otra zona en silencio.

### 3. La localidad no permite salir del grupo seleccionado

Un subconjunto seleccionado por `zone: a` y un hash de Rollout A no pueden conmutar por error a un subconjunto de la zona B. Lo mismo ocurre con un Service filtrado por zona. La detección de valores atípicos solo cambia la elegibilidad de endpoints dentro del grupo de upstream seleccionado; no salta a otra ruta de VirtualService.

Además, `localityLbSetting.distribute`, `failover` y `failoverPriority` son alternativas; no son campos que puedan combinarse libremente. Los valores `failover.from/to` son **regiones**, no cadenas `region/zone`. Esas entradas no establecen un ciclo de AZ A→B→C→A.

## Guía de implementación {#implementation-guide}

### Requisitos previos

Usa los requisitos previos del controlador, la CLI, la inyección, Prometheus y las cargas de trabajo de [Integración de Argo Rollouts](08-argo-rollouts.md). Esta es una demostración HTTP aislada con sidecars e inyección predeterminada/heredada; en una malla con revisiones, utiliza la revisión/etiqueta instalada. El laboratorio requiere nodos de trabajo Linux compatibles respaldados por EC2, cuotas, red, acceso a imágenes y observabilidad. Fargate queda fuera de este esquema; elige una versión de EKS actualmente compatible con el rango de Istio.

Los nombres de AZ de ejemplo `us-east-1a/b/c` deben reemplazarse por las etiquetas de nodo reales. La asignación de nombres de AZ puede variar entre cuentas; al coordinar zonas físicas entre cuentas, verifica los ID de AZ. La imagen fijada de la demostración solo es Linux amd64, por lo que cada AZ seleccionada necesita nodos compatibles o una imagen de reemplazo verificada por separado.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone,kubernetes.io/arch
```

### 1. Namespace y Services comunes/por zona

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: zone-rollouts-demo
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Service
metadata:
  name: test
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
```

El Service común es una entrada DNS para los clientes de la malla, no un mecanismo de autorización. Los seis Services zonales tienen un selector real de `zone` del Pod; Rollouts agrega el hash de cada versión estable/canary.

### 2. Contrato de la plantilla del cliente

Integra esto en un **Deployment existente llamado `zone-client-a`** y conserva su selector, contenedores, imagen verificada, recursos y demás restricciones de ubicación. Añade la etiqueta de ruta `a` a la plantilla real del Pod, no solo a los metadatos del Deployment:

```yaml
metadata:
  name: zone-client-a
  namespace: zone-rollouts-demo
spec:
  template:
    metadata:
      labels:
        routing.example.com/zone: a
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
```

Prepara clientes equivalentes B/C con las etiquetas correspondientes y restricciones de AZ reales al probarlos. Al combinar la afinidad con reglas existentes, conserva las restricciones AND/OR previstas; no amplíes por accidente los nodos elegibles. Comprueba `.spec.nodeName` frente a la zona del nodo seleccionado. Este fragmento no despliega un cliente ni copia automáticamente los metadatos del nodo.

### 3. VirtualService compartido con rutas independientes

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test
  namespace: zone-rollouts-demo
spec:
  hosts:
  - test
  - test.zone-rollouts-demo.svc.cluster.local
  gateways:
  - mesh
  http:
  - name: zone-a-route
    match:
    - sourceLabels:
        routing.example.com/zone: a
    route:
    - destination:
        host: test-stable-a
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-a
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-b-route
    match:
    - sourceLabels:
        routing.example.com/zone: b
    route:
    - destination:
        host: test-stable-b
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-b
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-c-route
    match:
    - sourceLabels:
        routing.example.com/zone: c
    route:
    - destination:
        host: test-stable-c
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-c
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: unclassified-client
    directResponse:
      status: 503
      body:
        string: No reviewed client-zone route
```

Antes de enviar tráfico de prueba, verifica que cada controlador haya seleccionado los hashes previstos y que haya endpoints saludables. Los pesos iniciales son 100/0, no una división activa 90/10 sin explicación. Cada ruta con nombre desactiva explícitamente los reintentos de malla; el comportamiento de reintentos de la aplicación es independiente.

### 4. Rollouts por zona

La carga de trabajo, la cantidad de réplicas, las solicitudes/límites y las pausas son valores de entrada de demostración. Tres réplicas no se distribuyen automáticamente entre tres nodos. Para un despliegue real, revisa la distribución/anti-afinidad a nivel de nodo, la capacidad, los PDB y el margen para las versiones estable/canary.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-a
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: a
  template:
    metadata:
      labels:
        app: test
        zone: a
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
  strategy:
    canary:
      stableService: test-stable-a
      canaryService: test-canary-a
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-a-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-b
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: b
  template:
    metadata:
      labels:
        app: test
        zone: b
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1b
  strategy:
    canary:
      stableService: test-stable-b
      canaryService: test-canary-b
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-b-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-c
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: c
  template:
    metadata:
      labels:
        app: test
        zone: c
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1c
  strategy:
    canary:
      stableService: test-stable-c
      canaryService: test-canary-c
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-c-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
```

Cada Rollout tiene su propio selector, estado de imagen/revisión, Services y argumentos de análisis. Después del primer control del 5 %, una pausa indefinida requiere una promoción deliberada. La afinidad estricta a una zona deja los Pods afectados en estado Pending si esa AZ no tiene capacidad; no los reubica en otras AZ saludables.

### 5. PDB explícitos

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-a-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: a
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-b-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: b
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-c-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: c
```

Estos conservan el mínimo ilustrativo original de un Pod por zona. No equivalen al mínimo global anterior de seis ni protegen de forma independiente cada revisión ponderada por tráfico. Antes del mantenimiento voluntario, inspecciona `currentHealthy`, `desiredHealthy` y `disruptionsAllowed`.

### 6. Análisis por zona

Crea esta plantilla antes de los Rollouts. Usa el nombre real del Service canary zonal y las métricas estándar del reporter de origen, en vez de etiquetas de zona de Pod inventadas:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-check
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-2xx-rate
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

El numerador corresponde específicamente a **HTTP 2xx**, según la definición de éxito de esta guía. Una ventana con todos los resultados 5xx produce 0, no un numerador vacío; la falta de tráfico o de datos no puede superar los controles de valor finito/volumen. Los proxies de origen y el proveedor deben poder acceder al Prometheus configurado, y sus etiquetas reales deben coincidir con estos selectores.

Mantén tráfico representativo dentro de la malla hacia `http://test.zone-rollouts-demo.svc.cluster.local:8080/color`. La etiqueta del cliente selecciona su zona y el controlador elige el peso estable/canary de esa zona. Una espera inicial de cinco minutos supera el período de consulta de métricas de dos minutos; la estimación de veinte solicitudes y las cantidades medidas son ilustrativas, no medidas de confianza estadística.

## Flujo del tráfico {#traffic-flow}

### Ruta zonal normal

Un cliente A correctamente etiquetado y ubicado en la AZ revisada obtiene `zone-a-route`, que apunta a los Services estable/canary de A. La proporción observada depende del tamaño de la muestra, las sesiones y la disponibilidad, no de una garantía exacta por cada diez solicitudes.

### Pérdida de una zona

Si desaparecen todos los endpoints elegibles de A, la ruta de A no tiene un upstream saludable. Reducir el umbral de detección de valores atípicos o cambiar el PDB no puede crear endpoints de B en el Service de A. El ejemplo devuelve fallos hasta que cambie la capacidad o una política de enrutamiento de nivel superior diseñada explícitamente.

Para mantener la continuidad entre AZ, elige una arquitectura con endpoints remotos saludables en el mismo grupo de versiones seleccionado o implementa y prueba una política de conmutación por error independiente en la capa de entrada. Ten en cuenta la capacidad remota, la coherencia de datos, la autenticación, las solicitudes en curso y la vuelta a la zona original. El código zonal anterior no ofrece conmutación transparente ni cíclica por error.

### Alternativa de localidad con endpoints compartidos

Lo siguiente corresponde a una **configuración diferente**: un Service `shared-app` existente o un subconjunto seleccionado cuyos endpoints elegibles abarcan AZ y tienen un estado de versión compatible. No habilita la conmutación por error de los Services zonales anteriores. Si un DestinationRule ya administra ese host/subconjuntos compartidos, integra allí este trafficPolicy en vez de crear una regla que compita:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: shared-endpoint-locality
  namespace: zone-rollouts-demo
spec:
  host: shared-app.zone-rollouts-demo.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
```

Las prioridades de localidad prefieren la región/zona coincidente y pueden dirigir el tráfico posterior a endpoints elegibles y saludables. No definen un orden cíclico fijo de AZ. `consecutive5xxErrors` es el campo actual; la detección consecutiva depende del tráfico, mientras que `interval` se aplica al trabajo de detección periódica. Expulsar todos los endpoints puede causar errores, y una solicitud que ya falló no se vuelve a reproducir automáticamente. Consulta [Enrutamiento con conocimiento de zonas](../resilience/03-zone-aware-routing.md).

## Solución de problemas {#troubleshooting}

```bash
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo
kubectl get virtualservice test -n zone-rollouts-demo -o yaml
kubectl get services test-stable-a test-canary-a -n zone-rollouts-demo -o yaml
kubectl get pods -n zone-rollouts-demo -l app=test -o wide --show-labels
kubectl get endpointslices -n zone-rollouts-demo -l kubernetes.io/service-name=test-canary-a
kubectl get pdb -n zone-rollouts-demo -o wide

istioctl proxy-config routes <client-a-pod> -n zone-rollouts-demo
istioctl proxy-config endpoints <client-a-pod> -n zone-rollouts-demo --cluster 'outbound|8080||test-canary-a.zone-rollouts-demo.svc.cluster.local'
kubectl get analysisruns -n zone-rollouts-demo
kubectl logs -n argo-rollouts deployment/argo-rollouts
```

- **Conflictos de actualización**: Distingue la propiedad de una misma ruta de los conflictos temporales de versión del objeto en un VirtualService compartido. Tener nombres de subconjunto diferentes no resuelve por sí solo ninguna de las dos causas.
- **Se seleccionó la zona equivocada**: Compara las etiquetas reales del Pod cliente, la ubicación del nodo y las rutas compiladas. No supongas que las etiquetas de zona del nodo se copiaron a los Pods.
- **Sin alternativa**: Primero inspecciona los endpoints elegibles del Service/subconjunto seleccionado. Si no hay ninguno fuera de A, una detección más rápida de valores atípicos no proporciona conmutación por error entre AZ.
- **Sin tráfico canary**: Confirma el recorrido por la malla, los EndpointSlices listos, los selectores de hash, los pesos reales y una cantidad de muestras suficiente.
- **Análisis bloqueado o fallido**: Inspecciona el resultado sin procesar y el error del proveedor, no solo la fase agregada del rollout. La telemetría integrada no incluye etiquetas de zona personalizadas.

## Prácticas recomendadas {#best-practices}

### 1. Coordinar explícitamente los cambios de versión

Promote reanuda una pausa existente; no despliega una imagen nueva ni demuestra que otra AZ esté saludable. Actualiza en Git la imagen deseada de una zona (o directamente en el laboratorio aislado), observa el análisis y el estado de la carga de trabajo y luego decide si se debe avanzar otra zona. Una espera fija de cinco minutos no basta por sí sola como evidencia.

```bash
# Isolated lab alternative to changing Git; affects zone A only.
kubectl argo rollouts set image test-a app=argoproj/rollouts-demo@sha256:e32df3d15f759d36c323b3dccb7003d38df1a4274d37217715151f085c24c58f -n zone-rollouts-demo
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo --watch
# After the intended manual pause and review:
kubectl argo rollouts promote test-a -n zone-rollouts-demo
```

Abort no revierte la imagen deseada en Git. Coordina GitOps para que no sobrescriba los pesos administrados de cada zona ni los selectores de hash de Service; consulta la guía de integración anterior.

### 2. Alternativa de análisis continuo

Si se necesita monitoreo continuo, sustituye deliberadamente la secuencia de pasos en línea. La plantilla en segundo plano omite `count`, y `startingStep: 2` significa el tercer paso:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-continuous
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
  - name: http-2xx-rate
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
---
spec:
  strategy:
    canary:
      analysis:
        templates:
        - templateName: zone-canary-continuous
        startingStep: 2
        args:
        - name: service-name
          value: test-canary-a
        - name: namespace
          value: zone-rollouts-demo
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - setWeight: 25
      - pause:
          duration: 5m
      - setWeight: 50
      - pause: {}
```

Al adaptar este fragmento de A a B/C, conserva la ruta, los Services y los argumentos de la zona correcta. El análisis independiente aún puede depender de la disponibilidad compartida de Prometheus, la red y el plano de control.

### 3. Reglas de monitoreo

Esta PrometheusRule requiere Prometheus Operator y selectores coincidentes para las etiquetas y el namespace de las reglas. Un Prometheus complementario independiente de Istio no carga automáticamente este CRD.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: zone-rollout-alerts
  namespace: zone-rollouts-demo
spec:
  groups:
  - name: zone-rollout
    rules:
    - alert: HighErrorRateZoneACanary
      expr: |-
        ((sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a",response_code=~"5..|0"}[2m])) or vector(0)) / sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) > 0.05
        and
        (sum(increase(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) >= 20
      for: 2m
      annotations:
        summary: Zone A canary has elevated 5xx/zero-status rate with observed traffic
    - alert: UnexpectedDemoZoneRoute
      expr: |-
        sum(rate(istio_requests_total{
          reporter="source",source_workload="zone-client-a",source_workload_namespace="zone-rollouts-demo",
          destination_service_namespace="zone-rollouts-demo",destination_service_name=~"test-(stable|canary)-(b|c)"
        }[5m])) > 0
      for: 5m
      annotations:
        summary: Demo client A is using a B/C destination Service; inspect route/placement assumptions
```

La primera regla comprueba los fallos 5xx/estado cero; los 4xx también reducen la tasa de análisis 2xx, pero no activan esta regla de errores en particular. El tráfico bajo o ausente requiere una señal de salud de telemetría/tráfico esperado diseñada por separado; la ausencia no demuestra que la versión canary esté saludable.

La segunda es una **alerta de invariantes de enrutamiento de demostración**, no un detector universal de zonas físicas. Supone que el Deployment de origen real es `zone-client-a`, está ubicado en A y que los Services B/C conservan sus selectores zonales. Para mediciones de zonas físicas, usa localidad de nodos/endpoints verificada o telemetría enriquecida explícitamente, como se describe en las guías de enrutamiento/observabilidad.

### 4. Recuperación y capacidad

Diversifica la capacidad Spot y conserva suficiente capacidad tolerante a fallos según el modelo real de aprovisionamiento de EKS/nodos. La afinidad zonal, la gestión de interrupciones y la política PDB no garantizan capacidad de reemplazo. Comprueba el comportamiento del ciclo de vida del grupo de nodos y el proceso de terminación/restauración de la aplicación.

Este esquema no incluye resultados medidos de recursos ni latencia. Dimensiona Istiod, los proxies y el controlador Rollouts con base en la presión de conciliación medida, la cantidad de endpoints, el uso de recursos y la latencia de rutas normales y de fallo para la carga de trabajo real.

## Referencias y siguientes pasos

- [Integración de Argo Rollouts](08-argo-rollouts.md)
- [Enrutamiento con conocimiento de zonas](../resilience/03-zone-aware-routing.md)
- [Detección de valores atípicos](../resilience/01-outlier-detection.md)
- [DestinationRule](../traffic-management/03-destination-rule.md)
- [Selectores de origen de Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Conmutación por error de localidad de Istio](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/)
- [API DestinationRule de Istio](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Integración de Istio con Argo Rollouts](https://argoproj.github.io/argo-rollouts/features/traffic-management/istio/)
- [Interrupciones de Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Configuración y redondeo de PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Afinidad de nodos](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Avisos de interrupción de EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [Comportamiento de Spot en grupos de nodos administrados de EKS](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [ID de AZ y asignación de cuentas de AWS](https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html)
- [Regiones y zonas de disponibilidad de AWS](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)

Usa como punto de partida las guías de integración y enrutamiento mantenidas para validar el laboratorio. [Multi-clúster](02-multi-cluster.md) incorpora requisitos adicionales de confianza, conectividad y diseño de dominios de fallo; no es una extensión de este esquema mediante un único ajuste.
