# Errores habituales de Istio y sus soluciones

> **Última actualización**: 11 de septiembre de 2026 · Comprobaciones de CLI y configuración: Istio 1.31.0

Parta del fallo observado, la configuración en uso y el modo de funcionamiento de la carga de trabajo. Los comandos siguientes son ejemplos de diagnóstico, no instrucciones para reinicializar la malla. Consulte las [indicaciones de compatibilidad de la instalación](../01-installation.md) para su versión de Kubernetes o EKS.

Los ejemplos utilizan un espacio de nombres de aplicación existente, app; un Deployment y un Service llamados myapp, en el puerto 8080; el espacio de nombres de entrada istio-ingress; y el sufijo DNS predeterminado del clúster. Sustitúyalos por sus recursos y dominios reales. Los bloques YAML de Deployment son **fragmentos para aplicar mediante strategic merge a un Deployment existente**, no definiciones completas de aplicaciones nuevas. En esta revisión no se desplegó ningún clúster ni se probaron cargas de trabajo de producción.

```bash
NS=app
GW_NS=istio-ingress
ISTIO_NS=istio-system
: "${POD:?Set the exact application Pod name}"
kubectl config current-context
istioctl version
kubectl -n "$NS" get pod "$POD" -o wide
```

## Índice

1. [Errores de conexión durante la terminación de Pods](#connection-errors-during-pod-termination)
2. [Problemas de inyección de sidecars](#sidecar-injection-issues)
3. [Fallo de conexión mTLS](#mtls-connection-failure)
4. [Fallo de enrutamiento de VirtualService](#virtualservice-routing-failure)
5. [Problemas de configuración de Gateway](#gateway-configuration-issues)
6. [Problemas de memoria y rendimiento](#memory-and-performance-issues)
7. [Caducidad de certificados](#certificate-expiration)
8. [Fallo de resolución DNS](#dns-resolution-failure)
9. [Tiempo de espera de inicialización de Envoy agotado](#envoy-initialization-timeout)
10. [Herramientas de depuración](#debugging-tools)

## Errores de conexión durante la terminación de Pods {#connection-errors-during-pod-termination}

### Descripción del problema

Durante el apagado pueden aparecer errores de conexión restablecida, broken pipe, EOF y HTTP 503. Por sí solos, no demuestran que Envoy terminara primero. Correlacione los registros de la aplicación y del proxy, los indicadores de respuesta, el momento de eliminación del Pod y los cambios de EndpointSlice.

### Causa raíz

No se garantiza el orden de apagado entre los contenedores de aplicación tradicionales y un sidecar definido en containers. El proxy puede terminar mientras la aplicación aún lo necesita, o la aplicación puede dejar de aceptar trabajo antes de finalizar las solicitudes en curso. En cambio, los sidecars nativos de Kubernetes se definen en initContainers con restartPolicy:Always y terminan después de los contenedores principales.

El periodo de gracia del Pod incluye la ejecución de preStop. No siempre dura 30 segundos, y los procesos que ya han terminado no se vuelven a finalizar después. Las actualizaciones de endpoints, la propagación de cambios al balanceador de carga y las conexiones de larga duración pueden abrir otras ventanas de fallo.

### Soluciones

#### Método 1: asignar tiempo al apagado de la aplicación y del proxy

Esta anotación configura el drenaje del proxy; **no** instala un hook preStop ni espera incondicionalmente a todas las solicitudes activas:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      terminationGracePeriodSeconds: 60
```

Los valores de 30 y 60 segundos son ejemplos, no mínimos universales. Calcule conjuntamente el tiempo necesario para apagar la aplicación, ejecutar los hooks y drenar el proxy. holdApplicationUntilProxyStarts afecta al **inicio**, no al orden de apagado. Los cambios de ProxyConfig requieren crear nuevos Pods para surtir efecto.

En 1.31, el comportamiento habitual de terminationDrainDuration se basa en un temporizador. Si se habilita EXIT_ON_ZERO_ACTIVE_CONNECTIONS, el agente espera el periodo mínimo de drenaje y consulta el número de conexiones de los listeners que reciben tráfico de los clientes. En ese caso, el temporizador de drenaje habitual no actúa como límite superior fijo. Siguen siendo relevantes el periodo de gracia de Kubernetes y las estadísticas ausentes o erróneas. Valide el comportamiento elegido con conexiones representativas.

#### Método 2: considerar el orden de apagado de los sidecars nativos

En una combinación compatible de Kubernetes e Istio, esta anotación selecciona la inyección nativa para los nuevos Pods que cumplan los requisitos de inyección:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
      labels: {}
    spec: {}
```

La función de Kubernetes es estable desde 1.33; la anotación de sidecars nativos de Istio está documentada como Alpha. Compruebe los initContainers realmente inyectados y cómo se apaga la aplicación. El orden de apagado no garantiza la ausencia de solicitudes fallidas ni permite esperar indefinidamente más allá del periodo de gracia del Pod. Las cargas de trabajo Ambient no tienen un Envoy por Pod que pueda configurarse de esta manera.

No existe una anotación documentada sidecar.istio.io/terminationGracePeriodSeconds. Establezca el campo real spec.terminationGracePeriodSeconds.

#### Método 3: valores predeterminados para toda la instalación

Lo siguiente es una **configuración de entrada para instalar con istioctl**, no un recurso destinado a la reconciliación mediante el antiguo operador de Istio instalado en el clúster, que ya se ha eliminado:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      terminationDrainDuration: 30s
      holdApplicationUntilProxyStarts: true
```

Revise el cambio renderizado con el responsable de la instalación y planifique la actualización de las cargas de trabajo afectadas. El antiguo bucle preStop de shell y netstat no tenía límite de espera, contaba sockets en escucha y presuponía la presencia de utilidades en la imagen del proxy. No esperaba de forma fiable a que la aplicación terminara su trabajo.

### Método de verificación

```bash
kubectl -n "$NS" get pod "$POD" -o json
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
kubectl -n "$NS" get events --field-selector "involvedObject.name=$POD"
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Capture los registros mientras el Pod aún exista. --previous recupera una instancia anterior del contenedor dentro del mismo Pod; no muestra el contenedor actual durante su terminación ni recupera los registros de cualquier Pod eliminado.

### Buenas prácticas

Implemente el manejo de SIGTERM y comprobaciones de disponibilidad que reflejen el estado real de la aplicación. Crear /tmp/not-ready no cambia nada si ni la aplicación ni la sonda consultan ese archivo. Una espera acotada en preStop puede dar tiempo a propagar los cambios, pero no demuestra que los endpoints hayan convergido ni sustituye el apagado ordenado de la aplicación. No existe una prohibición universal de utilizar sleep en la aplicación ni un mínimo universal de 60 segundos. Mida los errores HTTP y de otros protocolos tal como se producen, con los reintentos de escritura deshabilitados; consulte la [comparación de actualizaciones](../comparison/03-sidecar-vs-ambient.md).

## Problemas de inyección de sidecars {#sidecar-injection-issues}

### Problema 1: no se inyecta el sidecar

Compruebe dónde se definen tanto los sidecars tradicionales como los nativos antes de concluir que falta el proxy:

```bash
kubectl -n "$NS" get pod "$POD" -o jsonpath='{.spec.containers[*].name}{"\n"}{.spec.initContainers[*].name}{"\n"}'
kubectl get namespace "$NS" --show-labels
kubectl -n "$NS" get deployment myapp -o yaml
istioctl x check-inject "$POD" -n "$NS"
kubectl get mutatingwebhookconfigurations
kubectl -n "$ISTIO_NS" get pods -l app=istiod --show-labels
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

Las cargas de trabajo incorporadas a Ambient no utilizan deliberadamente un sidecar de aplicación istio-proxy. En modo sidecar, inspeccione la revisión o el tag del espacio de nombres, las etiquetas de la plantilla del Pod, hostNetwork, los selectores del webhook y los eventos de admisión. La inyección automática excluye los Pods con red del host y determinados espacios de nombres del sistema.

Utilice la revisión o el tag de la instalación prevista, o la etiqueta heredada de inyección, según la [guía de inyección](../advanced/07-sidecar-injection.md). No combine selecciones contradictorias de istio-injection e istio.io/rev. Las etiquetas afectan a los Pods nuevos y no modifican los existentes. Tras revisar el impacto, recree únicamente la carga de trabajo prevista mediante el responsable de su actualización.

La forma preferida de modificar la selección para un Pod es una **etiqueta** en la plantilla de Pods de la carga de trabajo:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations: {}
      labels:
        sidecar.istio.io/inject: 'true'
    spec: {}
```

La anotación correspondiente está obsoleta. Una etiqueta false puede indicar una exclusión intencionada; no debe sobrescribirse a ciegas como si fuera un error. Una etiqueta true tampoco evita todas las restricciones de selección del webhook o de la plataforma. Istiod realiza la inyección; el antiguo selector de registros app=sidecar-injector no identifica el inyector integrado actual.

### Problema 2: escasez de recursos del sidecar

Inspeccione los motivos de terminación del contenedor, los eventos, el uso de recursos y la limitación de CPU. OOMKilled puede indicar un problema con el límite de memoria. CrashLoopBackOff indica reinicios con esperas progresivas y puede tener muchas causas. Un error de validación de runAsNonRoot relacionado con un usuario no numérico afecta al contexto de seguridad o a la imagen y no se soluciona añadiendo RAM.

Si las mediciones justifican modificar los recursos, configure conjuntamente requests y limits en la plantilla del Pod. Las cantidades del ejemplo deben ajustarse a las necesidades de cada carga de trabajo:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/proxyCPU: 200m
        sidecar.istio.io/proxyCPULimit: 1000m
        sidecar.istio.io/proxyMemory: 256Mi
        sidecar.istio.io/proxyMemoryLimit: 512Mi
      labels: {}
    spec: {}
```

Valide la configuración de recursos del nuevo proxy inyectado y los objetos LimitRange y ResourceQuota del espacio de nombres. No sobrescriba la configuración de seguridad de la imagen solo para superar la admisión.

## Fallo de conexión mTLS {#mtls-connection-failure}

### Descripción del problema

Los errores de conexión al destino, las respuestas 503 y WRONG_VERSION_NUMBER pueden deberse a TLS, al protocolo, a los endpoints o a la red. PeerAuthentication controla el **mTLS que se acepta en el tráfico entrante**. La configuración TLS de DestinationRule controla el TLS saliente del Envoy del cliente. Establecer la PeerAuthentication del cliente en STRICT no obliga, por sí solo, a que ese cliente inicie conexiones mTLS.

### PeerAuthentication y DestinationRule

Si mTLS automático está habilitado y DestinationRule no define una configuración TLS explícita que lo sustituya, Istio selecciona mTLS de cargas de trabajo para los endpoints conocidos de la malla. Un valor DISABLE explícito puede entrar en conflicto con un destino que exige STRICT. Elimine una configuración no intencionada mediante su responsable o utilice ISTIO_MUTUAL para un destino configurado expresamente con mTLS de Istio. No lo fuerce en servicios externos arbitrarios que utilicen TLS o tráfico sin cifrar.

La siguiente política sin selector se aplica al **espacio de nombres app**, una vez que sus clientes estén preparados para exigir mTLS estricto:

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
```

Una política sin selector en el espacio de nombres raíz configurado, normalmente istio-system, abarca toda la malla, no solo los servicios de ese espacio de nombres. Revise el impacto de la migración antes de aplicarla. Ambient no permite deshabilitar su mTLS de transporte mediante PeerAuthentication DISABLE. La autenticación y AuthorizationPolicy funcionan por separado; un 403 no implica necesariamente un fallo de TLS.

### Comandos de depuración

```bash
istioctl x describe pod "$POD" -n "$NS"
kubectl get peerauthentication -A -o yaml
kubectl get destinationrule -A -o yaml
istioctl proxy-config clusters "$POD" -n "$NS" \
  --fqdn myapp.app.svc.cluster.local -o json
istioctl proxy-config secret "$POD" -n "$NS"
```

Consulte la configuración de los clusters salientes en el proxy del cliente que realiza la llamada y la política entrante en el proxy receptor. El comando experimental describe ayuda al diagnóstico, pero no demuestra que todas las rutas estén cifradas. Inspeccione la validez de los certificados, la identidad, el dominio de confianza, el socket de transporte en uso y los indicadores de respuesta. Los diagnósticos de waypoint y ztunnel son diferentes; consulte la [guía de mTLS](../security/01-mtls.md).

## Fallo de enrutamiento de VirtualService {#virtualservice-routing-failure}

### Problema 1: el tráfico no se enruta

Un 404 puede proceder de Envoy o de la aplicación. Identifique el origen y los detalles de la respuesta antes de cambiar las rutas. Un VirtualService con hosts:myapp.example.com que enruta al Service interno myapp es **válido** si está asociado al gateway adecuado y coincide con el Host o authority de la solicitud. El host del frontend y el nombre del servicio backend no tienen que ser iguales.

Para el tráfico de la malla, haga coincidir el host del servicio solicitado. Para el tráfico de entrada, utilice un dominio admitido por el gateway y asocie el VirtualService a ese gateway. Los nombres de destino cortos se resuelven en relación con el espacio de nombres del recurso de configuración; los FQDN explícitos reducen la ambigüedad entre espacios de nombres.

### Problema 2: no se encuentra el subconjunto o no hay destinos disponibles

Este par de recursos completos muestra cómo enrutar tráfico de la malla a un subconjunto con nombre:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: app
spec:
  host: myapp.app.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

El Service debe seleccionar endpoints realmente disponibles con la etiqueta version:v1. Un nombre de subconjunto coincidente en DestinationRule no crea Pods, corrige el selector de un Service ni hace que los endpoints estén disponibles. Compruebe el puerto del Service de destino, la selección de protocolo, la visibilidad de las políticas y las rutas que puedan competir entre sí. Los ejemplos anteriores de espacios de nombres y hosts presuponen el sufijo predeterminado cluster.local.

### Depuración

```bash
istioctl analyze -n "$NS"
istioctl proxy-config routes "$POD" -n "$NS"
istioctl proxy-config endpoints "$POD" -n "$NS"
kubectl -n "$NS" get svc myapp -o yaml
kubectl -n "$NS" get pods -l app=myapp --show-labels
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Analyze ayuda a revisar la configuración estática. Inspeccione las rutas, los clusters y los endpoints en uso en el proxy que realmente transporta la solicitud. La configuración no se propaga de forma instantánea. Una solicitud de entrada enrutada a un Service no hereda automáticamente la selección de subconjunto de otro VirtualService que solo se aplique dentro de la malla.


## Problemas de configuración de Gateway {#gateway-configuration-issues}

### Problema 1: el tráfico no llega al gateway

Una conexión rechazada o un tiempo de espera agotado antes de recibir una respuesta HTTP puede indicar problemas de DNS, discrepancias entre el listener y el puerto del Service, ausencia de destinos del balanceador de carga o filtrado de red. Localice primero el Deployment y el Service reales del gateway; su espacio de nombres y su nombre dependen del método de instalación.

```bash
kubectl -n "$GW_NS" get svc,pods --show-labels
kubectl -n "$GW_NS" get gateways.networking.istio.io -o yaml
kubectl -n "$NS" get virtualservice -o yaml
# For installations using Kubernetes Gateway API instead:
kubectl get gatewayclasses.gateway.networking.k8s.io
kubectl -n "$GW_NS" get gateways.gateway.networking.k8s.io -o yaml
kubectl -n "$NS" get httproutes.gateway.networking.k8s.io -o yaml
```

Inspeccione los campos ingress de loadBalancer del Service: el proveedor puede publicar una IP, un nombre de host o ambos. En EKS, compruebe también el estado y el tipo de los destinos del balanceador de carga, los grupos de seguridad y la ruta de red según la configuración real del controlador. Reiniciar Istiod no recupera un destino de AWS que falla sus comprobaciones de estado.

Istio Gateway (networking.istio.io) y Kubernetes Gateway API (gateway.networking.k8s.io) son recursos distintos. Para Gateway API, inspeccione Accepted, Programmed y las condiciones de los padres de HTTPRoute, como ResolvedRefs, junto con los eventos del controlador. Una errata en el nombre del gateway, un listener que no coincide o una asociación de ruta denegada requieren soluciones diferentes de las de un fallo de conectividad externa.

### Problema 2: HTTPS y asociación de rutas

Este ejemplo utiliza la **API de Gateway de Istio**. Sustituya el selector por las etiquetas reales de los Pods del gateway, utilice un dominio propio y un certificado válido, y compruebe que el Service del Deployment exponga el puerto 443. El ejemplo utiliza el mismo subconjunto de backend definido en la sección anterior:

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: myapp-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls-secret
    hosts:
    - myapp.example.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp-ingress
  namespace: app
spec:
  hosts:
  - myapp.example.com
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
  gateways:
  - istio-ingress/myapp-gateway
```

En este caso, SIMPLE termina el TLS de la conexión del cliente, por lo que la ruta utiliza http. Un listener TLS PASSTHROUGH, en cambio, requiere un enrutamiento TLS o SNI adecuado. No combine un listener que termina TLS con una ruta que solo define tls, ni espere seleccionar rutas basándose en la ruta HTTP dentro de tráfico opaco que atraviesa el gateway sin descifrarse.

credentialName hace referencia a una credencial accesible para la carga de trabajo del gateway. En este ejemplo, tanto el Pod del gateway como el Secret TLS están en istio-ingress:

```bash
kubectl -n "$GW_NS" create secret tls myapp-tls-secret   --cert=path/to/fullchain.pem   --key=path/to/key.pem
```

Si el Secret ya está gestionado, utilice el proceso de renovación del responsable del certificado. Este comando no obtiene un certificado ni hace que los clientes confíen en un emisor autofirmado. Compruebe la coincidencia del dominio y los SAN, la cadena presentada, la caducidad, la confianza del cliente y el estado de SDS del gateway. El espacio de nombres de un objeto Gateway de configuración independiente no sustituye en todos los casos al espacio de nombres de las credenciales de la carga de trabajo del gateway.

## Problemas de memoria y rendimiento {#memory-and-performance-issues}

### Problema 1: aumento del consumo de memoria de Envoy

Compare el uso real de memoria y CPU del contenedor, los límites, las conexiones, las rutas, los clusters, los listeners y la cardinalidad de la telemetría. Un ConfigMap o Secret grande que no tenga relación con el proxy no se carga automáticamente en él. Solo la configuración y los datos que ese proxy consume pueden explicar su uso de recursos. Para diagnosticar una fuga de memoria se necesitan pruebas específicas de la versión.

Si el consumo se debe principalmente a configuración no utilizada, un recurso Sidecar de alcance limitado puede restringir la configuración que importa una carga de trabajo seleccionada en modo **sidecar**:

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: myapp-scope
  namespace: app
spec:
  workloadSelector:
    labels:
      app: myapp
  egress:
  - hosts:
    - ./*
    - istio-system/*
```

Este ejemplo incluye únicamente servicios de app e istio-system. Inventaríe las dependencias reales con otros espacios de nombres y servicios externos antes de reducir las importaciones, y evite selectores Sidecar que se solapen. El recurso limita la configuración importada; no es un cortafuegos de salida ni una política de waypoint de Ambient. Ajuste requests y limits de memoria al comportamiento observado mediante las anotaciones de la plantilla del Pod mostradas antes.

### Problema 2: latencia alta

Un P99 superior a un segundo solo indica un problema en relación con un objetivo de latencia definido para la carga de trabajo. Antes de cambiar los tiempos de espera, revise el tiempo de la aplicación, la latencia del destino, la saturación, la limitación de CPU, los pools de conexiones, las cargas de datos y la amplificación causada por los reintentos.

Lo siguiente es una **alternativa** al VirtualService myapp anterior: añade un límite de cinco segundos para la ruta y deshabilita expresamente los reintentos:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
    timeout: 5s
```

El límite acota la espera, pero no acelera el backend. Reintentar a ciegas puede agravar la sobrecarga y repetir escrituras cuyo resultado es incierto. Si una operación idempotente concreta admite reintentos, reserve explícitamente tiempo para ellos dentro del límite total de extremo a extremo y mida los intentos reales. Consulte [Reintentos y tiempos de espera](../traffic-management/05-retry-timeout.md).

## Caducidad de certificados {#certificate-expiration}

### Descripción del problema

La caducidad de certificados X.509 y los fallos de negociación pueden afectar al certificado de la carga de trabajo, a una CA firmante intermedia o raíz, a un certificado de entrada o a un desfase del reloj. Los periodos de validez dependen de la CA, del proveedor y de la configuración; «diez años» o «24 horas» no bastan para establecer un diagnóstico universal.

### Diagnóstico y recuperación

Inspeccione el paquete público de confianza en uso y los certificados cargados por las cargas de trabajo:

```bash
# Public trust bundle, not a private CA key.
kubectl -n "$NS" get configmap istio-ca-root-cert \
  -o jsonpath='{.data.root-cert\.pem}' > root-cert.pem
openssl crl2pkcs7 -nocrl -certfile root-cert.pem |
  openssl pkcs7 -print_certs -text -noout
istioctl proxy-config secret "$POD" -n "$NS"
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

Una integración personalizada puede utilizar un ConfigMap de confianza distinto del estándar; inspeccione el proveedor de CA configurado. La inspección PKCS7 muestra todos los certificados del paquete PEM, no solo el primero. Correlacione la validez con la hora UTC actual, los errores de CA y CSR, los tokens de identidad, la conectividad con Istiod y SDS, y el proceso de renovación de certificados.

istioctl 1.31 no dispone del comando x ca root. No elimine ni regenere una CA solo porque haya caducado un certificado de una carga de trabajo: sustituir la raíz de confianza sin planificación puede interrumpir todas las cargas que dependen de ella. Corrija el problema real de renovación, conectividad o proveedor, y utilice el procedimiento admitido de rotación de CA, manteniendo ambas raíces de confianza durante la transición cuando sea necesario. Reinicie únicamente las cargas afectadas que lo requieran como parte del proceso de recuperación.

## Fallo de resolución DNS {#dns-resolution-failure}

### Descripción del problema

Si aparece un error de host inexistente o se agota el tiempo de una consulta, distinga entre el DNS de la aplicación, CoreDNS y sus servidores DNS, la existencia del Service, los sufijos de búsqueda y la captura DNS de Istio.

```bash
kubectl -n kube-system get svc kube-dns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=kube-dns
# Run from the affected app container only if it includes these tools.
kubectl -n "$NS" exec "$POD" -c myapp -- cat /etc/resolv.conf
kubectl -n "$NS" exec "$POD" -c myapp -- nslookup myapp.app.svc.cluster.local
```

No dé por hecho que una imagen mínima de aplicación o de proxy incluye utilidades de diagnóstico. Utilice un contenedor de diagnóstico aprobado cuando sea necesario. Compruebe las reglas de NetworkPolicy para UDP y TCP en el puerto 53, la conectividad con el nodo y el resolvedor, y la configuración de dnsPolicy y de búsqueda del Pod afectado.

Un ServiceEntry registra un servicio externo en Istio, pero no repara CoreDNS ni crea un registro DNS público. Tampoco permite resolver un nombre de host de destino que ya falla:

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: app
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

Sustituya api.example.com por el nombre de host externo real. La resolución DNS determina los endpoints de destino. Según el modo, la versión y la configuración, la captura DNS y la asignación de IP de Istio pueden responder a los nombres de servicios con direcciones sintéticas. Esto no demuestra que el endpoint real pueda resolverse o alcanzarse. Consulte las [indicaciones de captura DNS](../advanced/04-dns-cache.md). Si la aplicación ya envía HTTPS, declarar HTTPS en este recurso no obliga a añadir otra capa que inicie TLS.

## Tiempo de espera de inicialización de Envoy agotado {#envoy-initialization-timeout}

### Descripción del problema

El mensaje «Esperando a que el proxy Envoy esté listo» puede deberse a problemas de conectividad con xDS o la CA, configuración rechazada, recursos insuficientes, certificados, tokens o configuración de arranque. Compruebe el estado del Pod y de sus contenedores de inicialización, los registros del proxy y de Istiod, los eventos y proxy-status antes de aumentar las esperas de las sondas.

holdApplicationUntilProxyStarts retrasa el inicio de la aplicación hasta que el proxy está listo, pero no soluciona el problema de un Envoy que no logra estarlo. Una readinessProbe que solo define initialDelaySeconds no es válida porque carece de una acción de comprobación.

Si la aplicación realmente implementa /ready en el puerto 8080, este fragmento define comprobaciones concretas de inicio y disponibilidad:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      containers:
      - name: myapp
        startupProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
          failureThreshold: 3
```

Adapte la acción y los umbrales a la aplicación. StartupProbe determina cuánto tiempo se tolera el arranque; readiness determina si el endpoint puede recibir tráfico. Ninguna de las dos corrige un fallo de conectividad con Istiod. Inspeccione las reescrituras de sondas inyectadas y la configuración de disponibilidad en uso en el proxy antes de atribuir un fallo de una sonda de la aplicación a la inicialización de Envoy.

## Herramientas de depuración {#debugging-tools}

### Comandos de istioctl

```bash
istioctl analyze -A
istioctl proxy-status
istioctl proxy-config all "$POD" -n "$NS"
istioctl proxy-config log "$POD" -n "$NS"
# Temporarily change levels only on the selected Envoy.
istioctl proxy-config log "$POD" -n "$NS" --level http:debug
# Restore the previously recorded levels afterwards; --reset restores defaults.
istioctl bug-report --include "$NS" --duration 10m

# Ambient has ztunnel diagnostics; Envoy commands apply to waypoints.
istioctl ztunnel-config workloads -n "$ISTIO_NS"
istioctl ztunnel-config certificates -n "$ISTIO_NS"
```

Los comandos experimentales pueden cambiar y no sustituyen la verificación del tráfico. Registre los niveles de log antes de modificarlos temporalmente para depurar y restáurelos después. reset restaura los valores predeterminados, que pueden diferir de los ajustes personalizados anteriores. Limite la duración del diagnóstico y revise la configuración y los registros recopilados antes de compartir un archivo de informe de errores.

### API de administración de Envoy

Escuche únicamente en la interfaz de bucle local:

```bash
# Keep this command running; use a second terminal for the HTTP requests.
kubectl -n "$NS" port-forward --address 127.0.0.1 "$POD" 15000:15000

```

En otra terminal:

```bash
curl --fail --silent --show-error http://127.0.0.1:15000/clusters
curl --fail --silent --show-error http://127.0.0.1:15000/stats/prometheus
curl --fail --silent --show-error http://127.0.0.1:15000/config_dump
```

Estos comandos se aplican a Envoy, incluidos los sidecars y los waypoints. ztunnel utiliza otra interfaz de administración. Cierre el reenvío de puertos al terminar. Para cambiar los niveles de log, utilice preferentemente el comando istioctl del proxy seleccionado mostrado antes y restaure después los niveles que haya registrado.

### Comprobación habitual de registros

```bash
kubectl -n "$NS" logs "$POD" -c myapp
kubectl -n "$NS" logs "$POD" -c istio-proxy
# Only when that container has a prior instance in this same Pod:
kubectl -n "$NS" logs "$POD" -c istio-proxy --previous
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
```

Recopilar registros de un Pod actual en ejecución no conserva los de los Pods eliminados. Guarde la hora de la solicitud, el ID de traza o solicitud, los indicadores de respuesta y los cambios relevantes de endpoints y configuración junto con las pruebas del incidente.

## Referencias

- [Solución de problemas de inyección](https://istio.io/latest/docs/ops/common-problems/injection/) y [configuración de inyección](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [Problemas de red](https://istio.io/latest/docs/ops/common-problems/network-issues/) y [dirección TLS/mTLS automático](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Anotaciones de Istio](https://istio.io/latest/docs/reference/config/annotations/) y [código de apagado del proxy de la versión 1.31](https://github.com/istio/istio/blob/1.31.0/pkg/envoy/agent.go)
- [Terminación de Pods de Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) y [sidecars nativos](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Diagnósticos de proxies](https://istio.io/latest/docs/ops/diagnostic-tools/proxy-cmd/), [integración de CA](https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/) e [ingreso seguro](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Diagnóstico DNS de Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/) y [proxy DNS de Istio](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [Observabilidad](../observability/README.md), [Seguridad](../security/README.md), [Gestión del tráfico](../traffic-management/README.md)
