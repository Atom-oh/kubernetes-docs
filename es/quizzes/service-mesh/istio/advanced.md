# Cuestionario de temas avanzados de Istio

> **Versiones de referencia de la revisión**: Istio 1.31.0, Kubernetes 1.32–1.37, Argo Rollouts 1.10.1
> **Última revisión**: 16 de octubre de 2026

Las preguntas distinguen la configuración, el comportamiento en ejecución y las pruebas que lo demuestran. Los ejemplos son independientes: elige la topología pertinente y conserva los requisitos previos de la guía enlazada. Los datos históricos utilizados en los cálculos no son precios actuales ni resultados de nuevas pruebas de rendimiento.

## Preguntas de opción múltiple (1–5)

### Pregunta 1: Modos ambient y sidecar

¿Qué cambio arquitectónico puede reducir la sobrecarga de proxy por carga de trabajo en modo ambient?

- A. Ambient ofrece siempre más funciones que los sidecars.
- B. Un ztunnel por nodo gestiona el tráfico L4, y los waypoints desplegados por separado realizan el procesamiento L7 necesario.
- C. La instalación es, con garantía, diez veces más rápida.
- D. Todas las políticas se refuerzan sin cambiar la configuración.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Ambient elimina la necesidad de tener un proxy sidecar en cada Pod de las cargas incorporadas a la malla. ztunnel proporciona la capa segura L4; la incorporación del destino a un waypoint y las políticas L7 compatibles determinan el procesamiento adicional. Un waypoint no es un salto compartido universal que cualquiera de los ztunnels pueda elegir arbitrariamente.

| Aspecto | Comparación correcta |
|---|---|
| CPU y memoria | Mide tráfico, políticas, telemetría, número de nodos y réplicas de waypoint equivalentes. No existe un ahorro universal del 98 %. |
| Incorporación | Ambient puede incorporar Pods existentes sin sidecar sin reiniciar la aplicación; retirar un sidecar existente requiere reemplazar la carga de trabajo. |
| Funciones | La compatibilidad difiere. EnvoyFilter no está disponible en waypoints; ambient multiclúster tiene sus propios límites topológicos en fase beta. |
| Madurez | Las funciones principales de ambient alcanzaron disponibilidad general en Istio 1.24; eso no implica que todas las funciones posteriores sean GA. |
| Seguridad | mTLS y las políticas dependen de la ruta real del tráfico y de los mecanismos de asociación compatibles; exige el paso por waypoint cuando la aplicación de políticas L7 sea obligatoria. |

Por ejemplo, **suponiendo** 1.000 sidecars de 50 MB y 0,1 vCPU cada uno, el total es 50.000 MB y 100 vCPU. Diez ztunnels supuestos de 50 MB y 0,1 vCPU, más un waypoint de 200 MB y 0,5 vCPU, suman 700 MB y 1,5 vCPU. Las reducciones aritméticas son del 98,6 % y el 98,5 %; estos datos arbitrarios no son pruebas de rendimiento ni garantías de capacidad.

Incorporación después de instalar los componentes ambient compatibles y revisar las etiquetas de revisión o inyección existentes:

```bash
kubectl label namespace ambient-demo istio.io/dataplane-mode=ambient --overwrite
kubectl get daemonset ztunnel -n istio-system
istioctl ztunnel-config workloads --workload-namespace ambient-demo
```

El namespace debe existir, estar destinado a ambient y contener cargas compatibles. Estos comandos por sí solos no instalan CNI o ztunnel, configuran waypoints ni migran de forma segura los Pods con sidecar inyectado.

[Guía de ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

### Pregunta 2: Descubrimiento multiclúster

¿Qué componente lee los registros de servicios de Kubernetes a los que tiene acceso autorizado y genera la configuración de descubrimiento de los proxies en una malla multiclúster de Istio con sidecars?

- A. Istiod
- B. Solo CoreDNS
- C. Solo un gateway este-oeste
- D. Solo un objeto ServiceEntry

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Cada Istiod principal lee las API de Kubernetes a las que tiene acceso autorizado. En primary-remote, las cargas remotas utilizan el plano de control principal; la instalación remota no es un segundo Istiod completo administrado por un «superprincipal». En multi-primary, cada principal tiene su propio plano de control y acceso autorizado al descubrimiento remoto.

Istiod genera y distribuye la configuración de los proxies; no copia los objetos Kubernetes VirtualService o DestinationRule ni los datos de la aplicación a todos los clústeres. Distribuye la configuración por separado. La confianza compartida debe configurarse explícitamente: utilizar el mismo meshID no crea una CA común.

CoreDNS admite reenvío y otras configuraciones, pero no es el registro multiclúster de Istio. Los gateways transportan tráfico entre redes. ServiceEntry añade entradas al registro, incluidos servicios externos u otros registrados explícitamente.

Genera el Secret remoto real en lugar de inventar un campo `data.kubeconfig`:

```bash
# After the remote installation; contexts must identify the intended clusters.
istioctl create-remote-secret --context="$CTX_CLUSTER2" --name=cluster2   | kubectl --context="$CTX_CLUSTER1" apply -f -
```

El Secret concede al principal acceso a la **API remota**. Protege sus credenciales y revisa el RBAC generado. No conecta las redes ni replica objetos de políticas.

[Guía multiclúster](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### Pregunta 3: Propósito de EnvoyFilter

¿Cuál es el propósito principal de EnvoyFilter?

- A. Crear Services de Kubernetes.
- B. Generar automáticamente todos los VirtualServices.
- C. Personalizar partes seleccionadas de la configuración generada del proxy Envoy.
- D. Sustituir todos los ajustes de instalación de Istiod.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Prioriza las API compatibles de enrutamiento, telemetría, seguridad o extensiones. EnvoyFilter resulta adecuado cuando esas API no ofrecen el comportamiento compatible necesario y se comprende la configuración generada. Por ejemplo, este filtro Lua, exclusivo de sidecars, modifica un encabezado de una solicitud saliente ilustrativa:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: quiz-header
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(handle)
                handle:headers():replace("x-quiz-example", "yes")
              end
```

El namespace y el selector deben coincidir con los proxies previstos. Sin selector, normalmente se abarcan los proxies del namespace del recurso; un recurso del namespace raíz puede tener alcance en toda la malla. No escribas dos claves `workloadSelector` en un mismo objeto YAML. Un encabezado insertado por Lua no es una identidad autenticada.

Los demás casos de uso necesitan todas sus dependencias: un módulo Wasm requiere un artefacto y un entorno de ejecución verificados, y su montaje o una vía de entrega WasmPlugin compatible; la limitación global de solicitudes necesita un servicio accesible, descriptores coincidentes y una política ante fallos. Insertar únicamente el nombre de un filtro no proporciona esos sistemas. EnvoyFilter no es compatible con los waypoints de ambient.

Durante las actualizaciones, valida la versión exacta de Istio y Envoy, el alcance efectivo, el orden de filtros, la configuración tipada y la configuración generada del proxy. Los valores de instalación de Istiod siguen siendo configuración de Helm o istioctl; el YAML IstioOperator continúa siendo una entrada de istioctl, aunque se haya retirado el operador que se ejecutaba dentro del clúster.

[Guía de EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>

### Pregunta 4: Inyección de sidecars

¿Qué controles pueden deshabilitar la inyección automática de sidecars en los Pods nuevos?

- A. Establecer explícitamente la etiqueta de namespace `istio-injection=disabled`.
- B. Establecer la etiqueta `sidecar.istio.io/inject: "false"` en la plantilla de Pod de la carga.
- C. Reiniciar Istiod sin cambiar la configuración.
- D. Tanto A como B.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

```bash
kubectl label namespace example istio-injection=disabled --overwrite
kubectl get namespace example -L istio-injection,istio.io/rev
```

Este fragmento pertenece a spec del Deployment existente; conserva la imagen, los selectores y los demás campos:

```yaml
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: 'false'
```

Una etiqueta de deshabilitación en el namespace o en el Pod prevalece. En particular, activar la inyección en el Pod **no** anula `istio-injection=disabled`. Retirar únicamente `istio-injection=enabled` no la deshabilita en todos los casos: también debes revisar las etiquetas de revisión, la activación en Pods y los valores predeterminados del inyector. La anotación de inyección antigua está obsoleta y se sustituye por la etiqueta; evita ajustes antiguos y nuevos contradictorios.

Los cambios afectan a los Pods nuevos, no a los proxies ya inyectados. Para modificar Pods existentes, utiliza el despliegue progresivo revisado de la carga. Un namespace mixto puede habilitar la inyección y excluir determinadas plantillas de carga; esa exclusión también modifica la participación de la carga en la malla y sus mecanismos de seguridad.

```bash
kubectl get pod "$POD" -n "$NAMESPACE" -o json   | jq '{containers: [.spec.containers[].name],
         initContainers: [.spec.initContainers[]? | {name, restartPolicy}]}'
```

Un sidecar nativo puede aparecer en initContainers con `restartPolicy: Always`; comprobar solo los contenedores ordinarios o esperar exactamente `2/2` Ready no es suficiente. La incorporación a ambient es un mecanismo distinto.

[Guía de inyección](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

### Pregunta 5: Distribución del tráfico con Argo Rollouts

¿Qué **recurso declarativo** de Istio contiene los pesos de las rutas HTTP que actualiza Argo Rollouts?

- A. El proceso del controlador de Rollouts
- B. VirtualService
- C. Solo un Service de Kubernetes
- D. Solo Gateway

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Rollouts actualiza los pesos de la ruta identificada, Istiod traduce la configuración y **Envoy ejecuta** el enrutamiento. VirtualService no es un proceso que gestione paquetes. Un 10 % es un peso probabilístico; no garantiza que exactamente diez de cada cien solicitudes lleguen al canary. Los reintentos y las conexiones duraderas afectan a las observaciones.

La alternativa basada en subsets requiere un Service que seleccione la aplicación, ambos subsets y que Rollouts gestione sus etiquetas de revisión:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  host: test
  subsets:
  - name: stable
    labels:
      app: test
  - name: canary
    labels:
      app: test
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  hosts:
  - test
  - test.rollouts-demo.svc.cluster.local
  http:
  - name: primary
    route:
    - destination:
        host: test
        port:
          number: 8080
        subset: stable
      weight: 100
    - destination:
        host: test
        port:
          number: 8080
        subset: canary
      weight: 0
    retries:
      attempts: 0
```

Integra este fragmento de estrategia en el Rollout completo y coincidente de la guía; no lo apliques como un recurso incompleto ni lo combines con una estrategia distinta basada en hosts:

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: test-subsets
            routes:
            - primary
          destinationRule:
            name: test-subsets
            canarySubsetName: canary
            stableSubsetName: stable
      steps:
      - setWeight: 10
      - pause: {}
```

Deben existir el Service `test`, el selector y la plantilla completos del Rollout, el controlador con su RBAC y el namespace `rollouts-demo`. Rollouts actualiza las etiquetas de revisión de los subsets. `retries.attempts: 0` impide los reintentos de la malla en esta ruta; los reintentos de la aplicación son independientes.

El análisis de tráfico solo se ejecuta si se configura. Un fallo del análisis automático puede abortar un rollout, pero no revierte los efectos producidos en la aplicación o la base de datos. Utiliza el ejemplo completo de la guía basado en hosts o en subsets, con una sola estrategia cada vez.

[Guía de Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

## Preguntas de respuesta corta (6–10)

### Pregunta 6: Análisis de recursos y costes de ambient

Con los datos supuestos originales —500 Pods, cinco nodos r5.xlarge, 730 horas al mes y 0,252 USD por nodo y hora—, calcula los recursos de los proxies y explica si implican un ahorro en la factura. Cada sidecar utiliza 50 MB y 0,1 vCPU; cada ztunnel, 50 MB y 0,1 vCPU; el waypoint supuesto, 200 MB y 0,5 vCPU.

<details>
<summary>Respuesta de ejemplo</summary>

Los precios y recursos son **datos del ejercicio**, no cotizaciones actuales de AWS ni mediciones del consumo de Istio. Los cálculos siguientes de MB y GB utilizan unidades decimales.

| Recurso | Sidecars | Ambient en los cinco nodos supuestos | Reducción aritmética |
|---|---|---|---|
| Memoria | 500 × 50 = 25.000 MB | 5 × 50 + 200 = 450 MB | 24.550 MB, 98,2 % |
| CPU | 500 × 0,1 = 50 vCPU | 5 × 0,1 + 0,5 = 1 vCPU | 49 vCPU, 98 % |

Un r5.xlarge tiene cuatro vCPU y 32 GiB de memoria. Cinco nodos solo proporcionan 20 vCPU antes de atender al sistema y a las aplicaciones, por lo que los sidecars supuestos de 50 vCPU ya hacen inviable este escenario fijo de cinco nodos. El límite inferior de CPU, contando solo los proxies, es ceil(50/4) = 13 nodos; excluye CPU de aplicaciones, reservas del sistema, memoria, límites de IP, ubicación y requisitos de resiliencia.

No compares ese límite inferior de 13 nodos con «un nodo ambient» mientras sigues contabilizando recursos de ztunnel para cinco nodos. Recalcula los recursos de ztunnel para el **número real de nodos que se conservarán**, e incluye la alta disponibilidad y la capacidad de tráfico de los waypoints y todas las demás cargas.

Con la tarifa supuesta:

- Un nodo durante un mes cuesta `0.252 × 730 = $183.96`.
- Mantener los mismos cinco nodos cuesta `$919.80/month` en ambos modos: disponer de más recursos libres en los proxies no reduce por sí solo esa factura.
- Trece nodos durante un mes costarían `$2,391.48`, lo que corrige el cálculo anterior; no demuestra que ese sea el conjunto de nodos necesario en producción.
- Si los conjuntos validados contienen Nₛ y Nₐ nodos, la diferencia de cómputo es `(Nₛ − Nₐ) × $183.96/month`, antes de otros costes o compromisos.

Para una comparación completa, incluye los cargos de EKS y del plano de control, los balanceadores, el tráfico entre zonas o regiones, el almacenamiento, la telemetría y los compromisos de compra reales. Los sidecars sí utilizan comunicación local; ambient no elimina automáticamente los cargos de red ni los errores por falta de memoria.

Con el esfuerzo de migración supuesto de 6.000 USD, el plazo de recuperación es `6000 / S` meses solo si el ahorro neto mensual medido S es positivo. Si la capacidad facturada no cambia, S puede ser cero y el cálculo no tiene un resultado finito. La aritmética de los proxies por sí sola no permite afirmar el anterior ahorro del 92 % ni un retorno en 2,7 meses.

[Guía de ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>


### Pregunta 7: Malla EKS primary-remote

Describe el diseño primary-remote para dos clústeres EKS existentes en us-east-1 y us-west-2. Incluye descubrimiento, confianza, requisitos de red y un ejemplo de verificación entre clústeres.

<details>
<summary>Respuesta de ejemplo</summary>

Este diseño utiliza **sidecars**. La versión beta actual de ambient multiclúster admite multi-primary y multi-network, pero no este modelo primary-remote. El Istiod principal atiende a los proxies remotos; no existe un Istiod remoto completo que deba recibir configuración de un principal superior.

Antes de instalar, establece una configuración revisada de confianza común, acceso a las API, DNS, grupos de seguridad y firewalls, y las rutas L4 necesarias para el control y los datos. Los identificadores de red distintos identifican redes separadas, pero no crean conectividad. En un diseño con varias redes, ambos lados necesitan los gateways este-oeste adecuados para acceder a los endpoints remotos. Los costes de red entre regiones y la recuperación ante fallos siguen siendo responsabilidades independientes.

La configuración esencial del principal se proporciona como entrada de istioctl:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      externalIstiod: true
      multiCluster:
        clusterName: cluster1
      network: network1
```

En la configuración remota, **198.51.100.10 es una dirección de ejemplo para documentación**, no un endpoint de EKS:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: remote
  values:
    istiodRemote:
      injectionPath: /inject/cluster/cluster2/net/network2
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network2
      remotePilotAddress: 198.51.100.10
```

El namespace remoto también identifica al principal que lo administra:

```bash
kubectl --context="$CTX_CLUSTER2" annotate namespace istio-system   topology.istio.io/controlPlaneClusters=cluster1 --overwrite
```

Sigue la guía mantenida para preparar la confianza, generar los gateways con la misma versión de Istio, exponer el descubrimiento y la inyección del principal e instalar el perfil remoto antes de crear el Secret de acceso remoto de la pregunta 2. En este ejemplo de dos redes, la ruta de inyección remota termina en `net/network2`.

Un NLB de EKS suele proporcionar un nombre DNS. La versión admite un remotePilotAddress con valor DNS, pero generar el chart no demuestra conectividad de descubrimiento o inyección ni la validez de los nombres de certificado. Completa el diseño oficial de DNS, certificados y URL de inyección para un plano de control externo; no sustituyas una IP ausente del balanceador por una dirección arbitraria.

Para verificarlo, utiliza los ejemplos `helloworld` y `curl` de la misma distribución de Istio. Crea la misma identidad de namespace y Service en ambos clústeres y las cargas versionadas según la documentación. Un Service sin endpoints locales puede proporcionar DNS local de Kubernetes mientras Istio descubre endpoints remotos:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: helloworld
  namespace: sample
spec:
  selector:
    app: helloworld
  ports:
  - name: http
    port: 5000
    targetPort: 5000
```

Este Service por sí solo no despliega ninguna aplicación. El backend real del ejemplo escucha en el puerto 5000; declarar containerPort 8080 no hace que un proceso nginx estándar escuche en ese puerto. Después de desplegar el ejemplo completo, selecciona el Pod y el contenedor curl conocidos e inspecciona la configuración del plano de datos y las respuestas:

```bash
kubectl --context="$CTX_CLUSTER1" get service,endpointslice -n sample
kubectl --context="$CTX_CLUSTER2" get service,endpointslice -n sample
istioctl --context="$CTX_CLUSTER1" proxy-status
istioctl --context="$CTX_CLUSTER1" proxy-config endpoints "$CURL_POD" -n sample   --cluster 'outbound|5000||helloworld.sample.svc.cluster.local'
kubectl --context="$CTX_CLUSTER1" exec -n sample "$CURL_POD" -c curl --   curl --fail --max-time 5 http://helloworld.sample.svc.cluster.local:5000/hello
```

Con varias redes, el cliente puede ver un endpoint de gateway este-oeste en lugar de una IP de Pod remoto accesible directamente. Una respuesta solo demuestra esa llamada: prueba ambas direcciones, las versiones de los endpoints, la confianza, las políticas y los escenarios de fallo.

Dos destinos ponderados con **el mismo host, subset y puerto** no significan 80 % local y 20 % remoto. Utiliza un modelo compatible de localidad o de destinos explícitos con endpoints elegibles. Para observar tráfico entre clústeres, elige un único emisor de telemetría y las etiquetas source_cluster y destination_cluster reales.

[Guía multiclúster](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### Pregunta 8: Cuota compartida de solicitudes por usuario

Implementa una cuota compartida de 100 solicitudes por minuto y usuario para `/api/premium/*`. Explica los requisitos de identidad, los descriptores y el comportamiento ante fallos.

<details>
<summary>Respuesta de ejemplo</summary>

La ruta de la solicitud es: **entrada autenticada → gateway Envoy dedicado → decisión del servicio compartido de límites y Redis → backend o rechazo**. Un bucket local de un proxy no es una cuota compartida entre las réplicas del gateway.

Este ejemplo está condicionado a estos requisitos:

- Un gateway dedicado en `istio-system` con la etiqueta real `app: premium-gateway`, configuración coincidente de TLS y rutas, y Services backend existentes.
- Una capa de autenticación confiable retira el x-user-id enviado por el cliente y aporta una identidad canónica de usuario no vacía. Solo esa ruta autenticada puede llegar al gateway y al backend. Un encabezado controlado directamente por el cliente no es una identidad de usuario.
- El endpoint Redis existente del laboratorio aislado que se muestra a continuación es accesible. En producción, deben diseñarse por separado la autenticación y TLS de Redis, la persistencia, la alta disponibilidad, la conmutación ante fallos y los ajustes adecuados de conexión; el número de réplicas no los proporciona por sí solo.

El descriptor coincidente es una **secuencia de dos entradas**: `(header_match=premium, user_id=<trusted user>)`. La configuración del servidor debe anidar la entrada dinámica de usuario bajo la entrada premium. Un descriptor de nivel superior que solo contenga user_id no coincidiría.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: |
    domain: premium-ratelimit
    descriptors:
    - key: header_match
      value: premium
      descriptors:
      - key: user_id
        rate_limit:
          unit: minute
          requests_per_unit: 100
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ratelimit
  template:
    metadata:
      labels:
        app: ratelimit
        sidecar.istio.io/inject: 'true'
    spec:
      containers:
      - name: ratelimit
        image: docker.io/envoyproxy/ratelimit:8fe6ea42@sha256:a61547259607d40aff153050c2a87873ca1676d1d9f5f06937d412000dcc2df1
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8081
          name: grpc
        env:
        - name: LOG_LEVEL
          value: info
        - name: CONFIG_TYPE
          value: FILE
        - name: RUNTIME_ROOT
          value: /data
        - name: RUNTIME_SUBDIRECTORY
          value: ratelimit
        - name: RUNTIME_APPDIRECTORY
          value: config
        - name: RUNTIME_WATCH_ROOT
          value: 'false'
        - name: RUNTIME_IGNOREDOTFILES
          value: 'true'
        - name: USE_STATSD
          value: 'false'
        - name: REDIS_SOCKET_TYPE
          value: tcp
        - name: REDIS_URL
          value: redis-ratelimit.istio-system.svc.cluster.local:6379
        - name: HOST
          value: '::'
        - name: GRPC_HOST
          value: '::'
        - name: HEALTHY_WITH_AT_LEAST_ONE_CONFIG_LOADED
          value: 'true'
        volumeMounts:
        - name: config-volume
          mountPath: /data/ratelimit/config
          readOnly: true
        command:
        - /bin/ratelimit
        resources:
          requests:
            memory: 128Mi
            cpu: 100m
          limits:
            memory: 512Mi
            cpu: 500m
        readinessProbe:
          httpGet:
            path: /healthcheck
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config-volume
        configMap:
          name: ratelimit-config
---
apiVersion: v1
kind: Service
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  ports:
  - port: 8080
    name: http
    targetPort: 8080
  - port: 8081
    name: grpc
    targetPort: 8081
  selector:
    app: ratelimit
```

La imagen corresponde al commit verificado 8fe6ea42 del proyecto original y fija un digest, en lugar de una etiqueta master cambiante. El puerto gRPC es **8081** y el de salud HTTP, **8080**. Esta carga necesita un inyector coincidente y acceso real a la malla y a la red. Configura las credenciales protegidas de Redis mediante los mecanismos adecuados de Secret y montaje. Confirma que se cargue la nueva configuración; el modo de archivos mostrado no demuestra que exista recarga en caliente.

Utiliza el clúster gRPC generado por Istio para aplicar las políticas establecidas de descubrimiento de servicios y TLS:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: premium-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: premium-ratelimit
          failure_mode_deny: true
          timeout: 0.1s
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: outbound|8081||ratelimit.istio-system.svc.cluster.local
                authority: ratelimit.istio-system.svc.cluster.local
            transport_api_version: V3
---
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: premium-ratelimit-actions
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: VIRTUAL_HOST
    match:
      context: GATEWAY
    patch:
      operation: MERGE
      value:
        rate_limits:
        - actions:
          - header_value_match:
              descriptor_value: premium
              headers:
              - name: :path
                string_match:
                  prefix: /api/premium/
          - request_headers:
              header_name: x-user-id
              descriptor_key: user_id
              skip_if_absent: false
```

El conjunto de acciones se limita deliberadamente al gateway dedicado; en un gateway compartido, restringe los vhosts reales generados. Las solicitudes fuera del prefijo no generan un descriptor premium. Mantén coherentes la normalización de rutas y la política de autenticación, incluidas las rutas codificadas y las vías alternativas de acceso al backend.

Rechaza las solicitudes premium con identidad ausente o vacía antes de que puedan eludir la generación del descriptor:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: premium-requires-identity
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: premium-gateway
  action: DENY
  rules:
  - to:
    - operation:
        paths:
        - /api/premium/*
    when:
    - key: request.headers[x-user-id]
      notValues:
      - '*'
```

Esta política DENY solo comprueba la ausencia del encabezado. No autentica el valor proporcionado ni sustituye los controles obligatorios de entrada confiable y de vías alternativas, las políticas ALLOW existentes, TLS o la autorización de la aplicación.

Con `failure_mode_deny: true`, un error del servicio de límites produce normalmente HTTP 500, mientras que superar la cuota produce 429. El presupuesto RPC de 100 ms es un ejemplo que debe probarse frente a la latencia de Redis y de la red. Ningún encabezado o contador aislado demuestra que se aplique la cuota.

| Caso de verificación | Comportamiento esperado que debe probarse |
|---|---|
| Una identidad autenticada a través de dos réplicas del gateway | Un único presupuesto compartido por descriptor y ventana |
| Una segunda identidad | Un descriptor de usuario independiente |
| Identidad ausente o falsificada | Rechazo en la comprobación del encabezado o el límite de autenticación; no una vía gratuita para eludir la cuota |
| Ruta fuera del prefijo premium | Sin descriptor premium; las demás políticas de seguridad y límites siguen vigentes |
| Redis o RLS no disponibles | Rechazo deliberado ante fallos y observación del estado y la latencia |
| Límite de ventana o reinicio de Redis | Medir los contadores y las ventanas; no prometer que se rechace exactamente la solicitud 101 en ejecuciones independientes |

Utiliza un número limitado de solicitudes contra un endpoint autorizado de solo lectura y nuevas identidades y ventanas de prueba. Cincuenta solicitudes seguidas de otras 150 no crean dos presupuestos limpios e independientes. Los encabezados de límites de la respuesta requieren respuestas compatibles del servicio y configuración del filtro; no inventes valores de cuota restante o reinicio.

Inspecciona la salud de RLS, la configuración cargada y las estadísticas reales de Envoy (`ratelimit.ok`, `ratelimit.over_limit`, `ratelimit.error` bajo el prefijo de estadísticas HTTP). Comprueba los nombres y etiquetas Prometheus emitidos en lugar de inventar `rejected_total`. No ejecutes `KEYS *` de Redis en un conjunto grande de claves de producción ni interpretes contadores específicos de la implementación como cuota restante. La imagen distroless fijada de RLS no es una shell con redis-cli.

[Guía de límites de solicitudes](../../../service-mesh/istio/resilience/02-rate-limiting.md) · [Guía de EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>


### Pregunta 9: Blue/Green con análisis

Configura un Rollout Blue/Green con análisis de la versión de prueba y análisis posterior a la promoción. Explica el cambio de tráfico y el comportamiento ante fallos sin tratar la ausencia de métricas como éxito.

<details>
<summary>Respuesta de ejemplo</summary>

Esta es una **alternativa** a la estrategia canary de la pregunta 5. Requiere el controlador y las CRD de Argo Rollouts 1.10, cargas y clientes de demostración con Istio inyectado, Prometheus recopilando métricas coincidentes del emisor source, y capacidad Linux amd64 para la imagen de demostración verificada. Es un ejemplo de laboratorio, no un despliegue de producción probado.

Crea los Services y el Rollout completo en el namespace existente `rollouts-demo`. Rollouts gestiona los selectores de hash de revisión de los Services; GitOps no debe sobrescribir esos campos dinámicos.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: test-active
  namespace: rollouts-demo
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
  name: test-preview
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test
  namespace: rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
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
  strategy:
    blueGreen:
      activeService: test-active
      previewService: test-preview
      autoPromotionEnabled: true
      prePromotionAnalysis:
        templates:
        - templateName: preview-analysis
        args:
        - name: service-name
          value: test-preview
        - name: namespace
          value: rollouts-demo
      postPromotionAnalysis:
        templates:
        - templateName: active-analysis
        args:
        - name: service-name
          value: test-active
        - name: namespace
          value: rollouts-demo
      scaleDownDelaySeconds: 600
```

La imagen inicial fija el digest verificado de la demostración azul; la guía proporciona el digest verde correspondiente para actualizarla. Con una nueva revisión, preview apunta a la candidata. Tras superar el análisis previo, `autoPromotionEnabled: true` permite la promoción automática. Establécelo en false si se requiere una promoción manual deliberada; es una decisión de política independiente.

Aquí el tráfico procede de clientes incorporados a la malla hacia Services internos. La exposición en el borde en producción requiere un Gateway real, TLS, asociaciones de host coincidentes y autorización. Crear un segundo nombre de host de VirtualService no lo añade al Gateway ni protege el acceso a preview.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-bluegreen
  namespace: rollouts-demo
spec:
  hosts:
  - test-active
  - test-active.rollouts-demo.svc.cluster.local
  http:
  - name: active
    route:
    - destination:
        host: test-active
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-preview-route
  namespace: rollouts-demo
spec:
  hosts:
  - test-preview
  - test-preview.rollouts-demo.svc.cluster.local
  http:
  - name: preview
    route:
    - destination:
        host: test-preview
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
```

Ambas rutas deshabilitan explícitamente los reintentos de la malla. El Service preview no cambia automáticamente a la versión estable anterior al promover. El selector del Service activo pasa a la nueva revisión; finalmente se **reduce el número de réplicas** de los ReplicaSets antiguos, que no necesariamente se eliminan. Cambiar un selector no revierte las conexiones existentes ni los efectos en la aplicación o la base de datos.

Antes y durante el análisis de preview, genera tráfico representativo y autorizado a través del Service preview. Las consultas Prometheus no generan tráfico. El ejemplo exige una estimación de 20 solicitudes por ventana de dos minutos, éxito 2xx finito ≥95 %, p95 ≤0,5 segundos y errores 5xx o de estado cero ≤1 %:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: preview-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
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
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: active-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
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
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
```

Las dos plantillas usan deliberadamente los mismos criterios de aprobación con argumentos de Service diferentes. `initialDelay: 5m` permite que la ventana de dos minutos avance más allá de la transición, pero sigue siendo necesario verificar la actualidad de las métricas y el tráfico real. Evita utilizar muestras antiguas de la versión activa como pruebas de la candidata.

Prometheus devuelve un vector, así que las condiciones consultan `result[0]` solo después de comprobar la longitud y que el valor sea finito. El `or vector(0)` del numerador cubre los casos sin 2xx o con todos 5xx y sin 5xx en un servicio sano; el denominador y la comprobación de volumen impiden aprobar telemetría ausente o sin tráfico. La métrica de éxito solo cuenta 2xx; los 4xx reducen el éxito aunque no estén en el numerador de errores 5xx o de estado cero.

`failureLimit: 0` aborta ante la primera medición fallida. Si se establece en 2, el tercer fallo supera el límite; cinco muestras con fallos tolerados no exigen cinco éxitos. Cinco muestras a intervalos de 30 segundos no garantizan una fase de exactamente 2,5 minutos de tiempo real, especialmente con esperas iniciales y errores del proveedor.

Un fallo previo a la promoción mantiene el destino activo anterior. Un fallo posterior aborta y restaura la selección activa previa mientras el ReplicaSet antiguo siga disponible según las reglas del controlador. No garantiza una reversión universal e instantánea. Conserva capacidad suficiente de la versión anterior y verifica la propagación, las sesiones, el drenaje y la compatibilidad de la base de datos.

```bash
kubectl argo rollouts get rollout test -n rollouts-demo --watch
kubectl get analysisrun -n rollouts-demo
kubectl get service test-active test-preview -n rollouts-demo -o yaml
```

Inspecciona las condiciones reales del AnalysisRun y el árbol de revisiones, en lugar de copiar salidas de estado o usar nombres de métricas inexistentes. La reducción de réplicas, la propagación de endpoints y la recuperación de la aplicación deben probarse en el entorno previsto.

[Guía de Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

### Pregunta 10: Comportamiento de DNS y medición

Explica la captura DNS de Istio frente a la resolución DNS de destinos de Envoy, muestra una configuración válida y diseña una comparación de rendimiento reproducible. Evalúa las cifras originales no verificadas sin presentarlas como mediciones nuevas.

<details>
<summary>Respuesta de ejemplo</summary>

El DNS de la aplicación, la captura DNS de Istio, el comportamiento de CoreDNS y sus cachés, y la resolución de destinos de Envoy son mecanismos distintos. Una nueva solicitud HTTP no implica necesariamente una consulta DNS o conexión nueva. La captura DNS no es una caché universal de respuestas arbitrarias de servidores DNS.

En modo sidecar, istio-agent gestiona las solicitudes DNS capturadas; ambient utiliza su propia ruta DNS documentada y habilita la captura por defecto desde Istio 1.25. Los nombres conocidos de la malla pueden resolverse mediante la tabla de nombres; los desconocidos se reenvían. Envoy resuelve por separado los endpoints de destinos basados en DNS.

Registra un servicio HTTPS externo al que se conecta la aplicación mediante un ServiceEntry válido:

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.github.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

Esto no origina una segunda capa TLS, crea un firewall de salida ni permite al sidecar ver las rutas de solicitudes HTTP cifradas. Siguen siendo necesarias las políticas de red adecuadas y la validación TLS de la aplicación.

Para la captura en sidecars, integra esta entrada de istioctl en los valores de instalación existentes y reemplaza progresivamente las cargas afectadas mediante el proceso habitual de cambios:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: 'true'
```

**No existe** el campo `trafficPolicy.dnsRefreshRate` en DestinationRule, y `consecutiveErrors` no es el campo actual de outlier detection. Los clústeres DNS generados por Istio 1.31 respetan el TTL de DNS; el valor predeterminado de `dnsRefreshRate` de la malla es 60 segundos para el comportamiento de respaldo pertinente. Configurar cinco minutos no establece un intervalo fijo universal que anule los TTL positivos.

No insertes el filtro y tipo inventados `envoy.filters.network.dns_cache`. El proxy de reenvío dinámico y el modo actual DYNAMIC_DNS de ServiceEntry son diseños compatibles distintos, con requisitos propios, no un interruptor genérico de caché. Si necesitas personalizar un clúster, utiliza la guía DNS para definir un alcance explícito y una configuración validada para la versión.

Para una prueba limitada, utiliza un contenedor cliente que sepas que contiene curl y un endpoint HTTPS de prueba **propio o autorizado**, con DNS y TTL controlables. Establece BENCH_URL explícitamente. Se miden tiempos del proceso cliente, no solo la latencia DNS de Envoy:

```bash
: "${BENCH_URL:?Set an authorized HTTPS benchmark endpoint}"
for i in $(seq 1 20); do
  curl --silent --show-error --fail --max-time 5 --output /dev/null     --write-out '%{http_code},%{time_namelookup},%{time_connect},%{time_appconnect},%{time_starttransfer},%{time_total}
'     "$BENCH_URL" || break
  sleep 0.2
done
```

Registra el cliente y la imagen, las versiones de Istio y Kubernetes, el modo de proxy, el TTL y los cambios de respuesta, la ruta DNS, la reutilización de conexiones, la concurrencia, el contenido, TLS y el procedimiento con caché fría o caliente. Cada proceso curl nuevo reinicia su estado local; controla la reutilización de conexiones por separado. No hagas pruebas de carga contra una API pública de GitHub ni supongas que una imagen con curl contiene también ApacheBench. Gestiona explícitamente las muestras fallidas antes de calcular estadísticas.

El texto coreano original indicaba EKS 1.34, Istio 1.28.0, r5.xlarge en us-east-1 y api.github.com, pero no proporcionaba muestras brutas ni un artefacto reproducible de la prueba. Conserva ese **contexto histórico**, sin volver a etiquetarlo como un resultado de Istio 1.31:

| Cifra original sin verificar | Antes | Después | Solo aritmética |
|---|---:|---:|---:|
| Tiempo medio de respuesta |287 ms|152 ms|47,04 % menos|
| p95 |350 ms|180 ms|48,57 % menos|
| p99 |420 ms|210 ms|50 % menos|
| Rendimiento |12,34 RPS|23,15 RPS|87,60 % más|
| Tasa de aciertos de caché indicada |0 %|99 %|No se proporcionaron pruebas válidas de aciertos y fallos|
| Reutilización de conexiones indicada |0 %|95 %|No se proporcionó una medición válida de reutilización|

No se puede atribuir toda la diferencia en el tiempo de respuesta a DNS. Con concurrencia 10, el tiempo medio por solicitud de ApacheBench es aproximadamente `1000 × 10 / RPS` ms, mientras que el valor «para todas las solicitudes concurrentes» es `1000 / RPS` ms; las etiquetas originales estaban invertidas. Estas correcciones no autentican la prueba de rendimiento.

Entre las métricas útiles de captura están `istio_agent_dns_requests_total`, `istio_agent_dns_upstream_requests_total`, `istio_agent_dns_upstream_failures_total` y el histograma de duración de consultas al servidor DNS, cuando se exporten realmente. Éxitos/(éxitos+fallos) mide el éxito de las consultas, no los aciertos de caché. `envoy_cluster_upstream_cx_active` es un gauge; aplicarle rate() no mide la reutilización de conexiones.

Inspecciona la configuración DNS de los clústeres generados, los contadores realmente exportados y las trazas del resolvedor y las conexiones. Prueba cambios DNS y recuperación ante fallos, además de la latencia media; no recomiendes intervalos de 5–15 minutos ni mejoras fijas de rendimiento sin pruebas de la carga de trabajo.

[Guía DNS](../../../service-mesh/istio/advanced/04-dns-cache.md)

</details>

## Puntuación

- Preguntas 1–5: 10 puntos cada una, 50 en total. Respuestas: **B, A, C, D, B**.
- Preguntas 6–10: 10 puntos cada una, 50 en total. Valora los mecanismos correctos, los requisitos completos, la configuración válida, la verificación útil y la exposición honesta de los límites de medición.
- Total: 100 puntos. La puntuación refleja la comprensión de estas preguntas; no certifica experiencia operativa.

## Materiales de estudio

- [Ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [Multiclúster](../../../service-mesh/istio/advanced/02-multi-cluster.md)
- [EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)
- [DNS](../../../service-mesh/istio/advanced/04-dns-cache.md)
- [gRPC](../../../service-mesh/istio/advanced/05-grpc.md)
- [WebSocket](../../../service-mesh/istio/advanced/06-websocket.md)
- [Inyección](../../../service-mesh/istio/advanced/07-sidecar-injection.md)
- [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)
- [KEDA](../../../service-mesh/istio/advanced/10-keda-autoscaling.md)
