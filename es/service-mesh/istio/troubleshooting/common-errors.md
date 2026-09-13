# Errores habituales de Istio y sus soluciones

> **Última actualización**: September 11, 2026 · Comprobaciones de CLI/configuración: Istio 1.31.0

Empiece por el fallo observado, la configuración efectiva y el modo de la carga de trabajo. Los comandos siguientes son ejemplos de diagnóstico, no instrucciones para restablecer la malla. Consulte las [indicaciones de compatibilidad de instalación](../01-installation.md) para su versión de Kubernetes/EKS.

Los ejemplos utilizan un espacio de nombres de aplicación existente app, un Deployment/Service myapp en el puerto 8080, un espacio de nombres de ingreso istio-ingress y el sufijo DNS predeterminado del clúster. Sustitúyalos por recursos y dominios reales. Los bloques YAML de Deployment son **fragmentos de fusión estratégica para un Deployment existente**, no aplicaciones nuevas completas. En esta revisión no se desplegó ningún clúster ni se probaron cargas de trabajo de producción.

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

Durante el apagado pueden producirse reinicios de conexión, tuberías rotas, EOF y HTTP 503. Por sí solos no demuestran que Envoy haya terminado primero. Correlacione los registros de aplicación/proxy, las marcas de respuesta, el momento de eliminación del Pod y los cambios de EndpointSlice.

### Causa raíz

Los contenedores de aplicación tradicionales y un sidecar incluido en containers no tienen un orden de apagado garantizado. Un proxy puede terminar mientras la aplicación aún lo necesita; la aplicación también puede dejar de aceptar trabajo antes de que terminen las solicitudes existentes. En cambio, los sidecars nativos de Kubernetes utilizan initContainers con restartPolicy:Always y terminan después de los contenedores principales.

El período de gracia del Pod incluye la ejecución de preStop. No siempre es de 30 segundos y los procesos que ya terminaron no se vuelven a matar después. Las actualizaciones de endpoints, la propagación del equilibrador de carga y las conexiones de larga duración pueden crear ventanas de fallo adicionales.

### Soluciones

#### Método 1: presupuestar el apagado de la aplicación y del proxy

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

Los valores de 30/60 segundos son ejemplos, no mínimos universales. Presupueste conjuntamente el apagado de la aplicación, los hooks y el drenaje del proxy. holdApplicationUntilProxyStarts se refiere al **inicio**, no al orden de apagado. Los cambios de ProxyConfig requieren Pods nuevos para surtir efecto.

En 1.31, la ruta ordinaria terminationDrainDuration se basa en el tiempo. Cuando EXIT_ON_ZERO_ACTIVE_CONNECTIONS está habilitado, el agente espera en su lugar el período mínimo de drenaje y consulta los recuentos de conexiones de los listeners descendentes; esa ruta no utiliza el temporizador de drenaje ordinario como límite superior fijo. Siguen aplicándose los límites de gracia de Kubernetes y la ausencia o los errores de estadísticas. Valide el comportamiento elegido con conexiones representativas.

#### Método 2: considerar el orden de sidecars nativos

Para una combinación compatible de Kubernetes/Istio, esta anotación selecciona la inyección nativa para Pods recién creados aptos para inyección:

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

La función de Kubernetes es estable desde 1.33; la anotación de sidecars nativos de Istio está documentada como Alpha. Verifique los initContainers realmente inyectados y el comportamiento de apagado de la aplicación. El orden por sí solo no garantiza cero solicitudes fallidas ni espera indefinidamente más allá del período de gracia del Pod. Las cargas de trabajo Ambient no tienen un Envoy por Pod que pueda configurarse así.

No existe una anotación documentada sidecar.istio.io/terminationGracePeriodSeconds. Establezca el campo real spec.terminationGracePeriodSeconds.

#### Método 3: valores predeterminados de toda la instalación

Lo siguiente es una **entrada de instalación de istioctl**, no un recurso que deba reconciliar el operador de Istio integrado en el clúster que fue eliminado:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      terminationDrainDuration: 30s
      holdApplicationUntilProxyStarts: true
```

Revise el cambio renderizado con el responsable de la instalación y despliegue deliberadamente las cargas de trabajo afectadas. El antiguo bucle preStop de shell/netstat no tenía límite, contaba sockets en escucha y presuponía que había utilidades en la imagen del proxy. No esperaba de forma fiable a que terminara el trabajo de la aplicación.

### Método de verificación

```bash
kubectl -n "$NS" get pod "$POD" -o json
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
kubectl -n "$NS" get events --field-selector "involvedObject.name=$POD"
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Capture los registros mientras el Pod aún exista. --previous recupera una instancia anterior del contenedor en el mismo Pod; no significa «contenedor actual mientras termina» ni recupera registros arbitrarios de Pods eliminados.

### Buenas prácticas

Implemente el tratamiento de SIGTERM en la aplicación y un contrato real de disponibilidad. Crear /tmp/not-ready no cambia nada salvo que la aplicación o la sonda lo lea. Un retraso preStop acotado puede proporcionar tiempo de propagación, pero no demuestra la convergencia de endpoints ni sustituye el apagado ordenado de la aplicación. No existe una prohibición universal de usar sleep en la aplicación ni un mínimo universal de 60 segundos. Mida los fallos HTTP/no HTTP sin ocultarlos y con reintentos de escritura deshabilitados; consulte la [comparación de despliegues](../comparison/03-sidecar-vs-ambient.md).

## Problemas de inyección de sidecars {#sidecar-injection-issues}

### Problema 1: no se inyecta el sidecar

Compruebe las ubicaciones de sidecars regulares y nativos antes de concluir que falta un proxy:

```bash
kubectl -n "$NS" get pod "$POD" -o jsonpath='{.spec.containers[*].name}{"\n"}{.spec.initContainers[*].name}{"\n"}'
kubectl get namespace "$NS" --show-labels
kubectl -n "$NS" get deployment myapp -o yaml
istioctl x check-inject "$POD" -n "$NS"
kubectl get mutatingwebhookconfigurations
kubectl -n "$ISTIO_NS" get pods -l app=istiod --show-labels
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

La incorporación a Ambient carece deliberadamente de un sidecar de aplicación istio-proxy. Para modo sidecar, inspeccione la revisión/etiqueta del espacio de nombres, las etiquetas de plantilla del Pod, hostNetwork, los selectores de webhook y los eventos de admisión. La inyección automática excluye Pods con red del host y determinados espacios de nombres del sistema.

Utilice la revisión/etiqueta de la instalación prevista o la etiqueta de inyección heredada siguiendo la [guía de inyección](../advanced/07-sidecar-injection.md). No combine selecciones contradictorias de istio-injection e istio.io/rev. Las etiquetas afectan a Pods recién creados; no modifican un Pod existente. Recree únicamente la carga de trabajo prevista mediante su responsable de despliegue tras revisar el efecto.

La anulación preferida por Pod es una **etiqueta** bajo la plantilla de Pod de la carga de trabajo:

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

La anotación correspondiente está obsoleta. Una etiqueta false puede ser una exclusión deliberada, no un error que deba sobrescribirse a ciegas. Una etiqueta true tampoco evita todas las restricciones de selección de webhook o plataforma. Istiod sirve la inyección; el antiguo selector de registros app=sidecar-injector no identifica el inyector integrado actual.

### Problema 2: escasez de recursos del sidecar

Inspeccione las razones de terminación del contenedor, los eventos, el uso y la limitación de CPU. OOMKilled puede indicar un problema con el límite de memoria; CrashLoopBackOff es un estado de reinicio/espera progresiva con muchas causas posibles. Un error de validación de runAsNonRoot/usuario no numérico es un problema de contexto de seguridad/imagen y no se soluciona con más RAM.

Si las mediciones justifican un cambio de recursos, establezca conjuntamente solicitudes y límites en la plantilla de Pod. Estas cantidades de ejemplo necesitan dimensionamiento específico de la carga de trabajo:

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

Valide los ajustes de recursos recién inyectados y los LimitRange/ResourceQuota del espacio de nombres. Evite sobrescribir los ajustes de seguridad de la imagen solo para superar la admisión.

## Fallo de conexión mTLS {#mtls-connection-failure}

### Descripción del problema

Los errores de conexión ascendente, los 503 y WRONG_VERSION_NUMBER pueden tener causas de TLS, protocolo, endpoints o red. PeerAuthentication controla el **mTLS entrante aceptado**. Los ajustes TLS de DestinationRule controlan el TLS saliente del Envoy del cliente. Establecer la PeerAuthentication del cliente en STRICT no obliga por sí solo a ese cliente a originar mTLS.

### PeerAuthentication y DestinationRule

Con mTLS automático habilitado y sin una anulación TLS explícita de DestinationRule, Istio selecciona mTLS de cargas de trabajo para endpoints conocidos de la malla. Una anulación DISABLE explícita puede entrar en conflicto con un destino que requiere STRICT. Elimine una anulación no intencionada mediante su responsable o utilice ISTIO_MUTUAL para un destino Istio-mTLS configurado deliberadamente; no lo fuerce en servicios externos arbitrarios TLS/sin cifrar.

La siguiente política sin selector se aplica al **espacio de nombres app** cuando sus clientes estén preparados para la aplicación estricta:

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

Una política sin selector en el espacio de nombres raíz configurado (normalmente istio-system) tiene ámbito de toda la malla, no solo de los servicios de ese espacio de nombres. Revise el impacto de la migración antes de aplicarla. Ambient no permite deshabilitar su mTLS de transporte mediante PeerAuthentication DISABLE. La autenticación y AuthorizationPolicy son independientes; un 403 no es automáticamente un fallo TLS.

### Comandos de depuración

```bash
istioctl x describe pod "$POD" -n "$NS"
kubectl get peerauthentication -A -o yaml
kubectl get destinationrule -A -o yaml
istioctl proxy-config clusters "$POD" -n "$NS" \
  --fqdn myapp.app.svc.cluster.local -o json
istioctl proxy-config secret "$POD" -n "$NS"
```

Utilice el proxy cliente pertinente para la configuración del clúster saliente y el proxy receptor para la política entrante. El comando experimental describe es una ayuda de diagnóstico, no una prueba de que todas las rutas estén cifradas. Inspeccione la validez de los certificados, la identidad, el dominio de confianza, el socket de transporte real y las marcas de respuesta. Los diagnósticos de waypoint y ztunnel difieren; consulte la [guía de mTLS](../security/01-mtls.md).

## Fallo de enrutamiento de VirtualService {#virtualservice-routing-failure}

### Problema 1: el tráfico no se enruta

Un 404 puede proceder de Envoy o de la aplicación. Identifique su origen y los detalles de respuesta antes de cambiar rutas. Un VirtualService con hosts:myapp.example.com que enruta al Service interno myapp es **válido** cuando está asociado al gateway apropiado y coincide con el Host/authority de la solicitud. El host de frontend y el nombre del servicio backend no tienen que ser idénticos.

Para tráfico de malla, coincida con el host de servicio solicitado; para tráfico de ingreso, coincida con el dominio admitido por el gateway y asocie el VirtualService a ese gateway. Los nombres de destino cortos se resuelven respecto al espacio de nombres del recurso de configuración, por lo que los FQDN explícitos reducen la ambigüedad entre espacios de nombres.

### Problema 2: subconjunto no encontrado o sin hosts ascendentes sanos

Este par completo muestra el enrutamiento de malla a un subconjunto con nombre:

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

El Service debe seleccionar realmente endpoints listos etiquetados con version:v 1. Un nombre de subconjunto DestinationRule coincidente por sí solo no crea Pods, corrige un selector de Service ni hace sanos los endpoints. Compruebe el puerto del Service de destino, la selección de protocolo, la visibilidad de políticas y las rutas competidoras. Los ejemplos de espacio de nombres/host anteriores presuponen el sufijo predeterminado cluster.local.

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

Analyze es una ayuda de configuración estática; inspeccione la ruta/clúster/endpoints efectivos del proxy que realmente transporta la solicitud. La propagación de configuración no es instantánea. Una solicitud de ingreso enrutada a un Service no hereda automáticamente la selección de subconjunto de otro VirtualService exclusivo de la malla.


## Problemas de configuración de Gateway {#gateway-configuration-issues}

### Problema 1: el tráfico no llega al gateway

Una conexión rechazada o un tiempo de espera agotado antes de recibir una respuesta HTTP puede indicar problemas de DNS, discrepancias de listener/puerto de Service, destinos del equilibrador de carga ausentes o filtrado de red. Localice primero el Deployment/Service real del gateway; su espacio de nombres y nombre dependen del método de instalación.

```bash
kubectl -n "$GW_NS" get svc,pods --show-labels
kubectl -n "$GW_NS" get gateways.networking.istio.io -o yaml
kubectl -n "$NS" get virtualservice -o yaml
# For installations using Kubernetes Gateway API instead:
kubectl get gatewayclasses.gateway.networking.k8s.io
kubectl -n "$GW_NS" get gateways.gateway.networking.k8s.io -o yaml
kubectl -n "$NS" get httproutes.gateway.networking.k8s.io -o yaml
```

Inspeccione los campos ingress de loadBalancer del Service: los proveedores pueden publicar una IP, un nombre de host o ambos. En EKS compruebe también el estado y tipo de destinos del equilibrador de carga, los grupos de seguridad y la ruta de red utilizando la configuración real del controlador; reiniciar Istiod no repara un destino AWS no sano.

Istio Gateway (networking.istio.io) y Kubernetes Gateway API (gateway.networking.k 8s.io) son recursos diferentes. Para Gateway API inspeccione Accepted, Programmed y condiciones de los padres de HTTPRoute como ResolvedRefs, junto con los eventos del controlador. Una errata en el nombre del gateway, una discrepancia de listener o una asociación de ruta denegada requieren una solución distinta de un fallo de conectividad externa.

### Problema 2: HTTPS y asociación de rutas

Este ejemplo utiliza la **API Gateway de Istio**. Sustituya el selector por las etiquetas reales de los Pods del gateway, utilice un dominio propio y un certificado válido, y asegúrese de que el Service del Deployment exponga 443. Utiliza el mismo subconjunto de backend definido en la sección anterior:

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

Aquí SIMPLE termina el TLS descendente, por lo que la ruta utiliza http. En cambio, un listener TLS PASSTHROUGH necesita enrutamiento TLS/SNI apropiado. No mezcle un listener con terminación y solo una ruta tls ni espere coincidencia de rutas HTTP dentro de tráfico opaco de paso directo.

credentialName se refiere a una credencial accesible para la carga de trabajo del gateway. En este ejemplo, el Pod del gateway y el Secret TLS están en istio-ingress:

```bash
kubectl -n "$GW_NS" create secret tls myapp-tls-secret   --cert=path/to/fullchain.pem   --key=path/to/key.pem
```

Utilice el proceso de renovación del responsable actual del certificado si ese Secret ya está gestionado. Este comando no obtiene un certificado ni hace confiable a un emisor autofirmado. Compruebe la coincidencia de dominio/SAN, la cadena servida, la caducidad, la confianza del cliente y el estado de SDS del gateway. El espacio de nombres de un objeto de configuración Gateway independiente no sustituye universalmente al espacio de nombres de credenciales de la carga de trabajo del gateway.

## Problemas de memoria y rendimiento {#memory-and-performance-issues}

### Problema 1: aumento del consumo de memoria de Envoy

Compare la memoria/CPU real del contenedor, los límites, las conexiones, las rutas/clústeres/listeners y la cardinalidad de telemetría. Un ConfigMap o Secret grande sin relación no se carga automáticamente en todos los proxies; solo la configuración y los datos consumidos por ese proxy pueden explicar su consumo. Una fuga de memoria requiere evidencia específica de la versión.

Cuando predomina la configuración no utilizada, un recurso Sidecar con ámbito limitado puede restringir la configuración importada por una carga de trabajo **sidecar** seleccionada:

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

Este ejemplo incluye únicamente servicios de app e istio-system. Inventaríe las dependencias reales entre espacios de nombres/externas antes de limitar las importaciones y evite selectores Sidecar superpuestos. Esto delimita configuración, no es un cortafuegos de salida ni una política de waypoint de ambient. Dimensione las solicitudes/límites de memoria según el comportamiento observado utilizando las anotaciones de plantilla de Pod mostradas antes.

### Problema 2: latencia alta

Un P99 superior a un segundo solo es un síntoma respecto a un presupuesto definido de carga de trabajo. Compruebe el tiempo de la aplicación, la latencia ascendente, la saturación, la limitación de CPU, los grupos de conexiones, el contenido y la amplificación por reintentos antes de cambiar tiempos de espera.

Lo siguiente es una **alternativa** al VirtualService myapp anterior que añade un plazo de ruta de cinco segundos con los reintentos deshabilitados explícitamente:

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

Un plazo limita la espera; no acelera el backend. Los reintentos a ciegas pueden amplificar la sobrecarga y repetir escrituras ambiguas. Si los reintentos son apropiados para una operación idempotente concreta, presupuéstelos explícitamente dentro del plazo de extremo a extremo y mida los intentos reales. Consulte [Reintentos y tiempos de espera](../traffic-management/05-retry-timeout.md).

## Caducidad de certificados {#certificate-expiration}

### Descripción del problema

La caducidad de x 509 y los fallos de negociación pueden afectar al certificado final de la carga de trabajo, a una CA firmante intermedia/raíz, a un certificado de ingreso o a un desfase de reloj. Los períodos de validez dependen de la CA/proveedor y la configuración; «diez años» o «24 horas» no son un diagnóstico universal.

### Diagnóstico y recuperación

Inspeccione el paquete público de confianza real y los certificados de cargas de trabajo cargados:

```bash
# Public trust bundle, not a private CA key.
kubectl -n "$NS" get configmap istio-ca-root-cert \
  -o jsonpath='{.data.root-cert\.pem}' > root-cert.pem
openssl crl2pkcs7 -nocrl -certfile root-cert.pem |
  openssl pkcs7 -print_certs -text -noout
istioctl proxy-config secret "$POD" -n "$NS"
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

El ConfigMap de confianza estándar puede diferir con una integración personalizada; inspeccione el proveedor de CA configurado. La inspección PKCS7 muestra todos los certificados del paquete PEM, no solo el primero. Correlacione la validez con la hora UTC actual, los errores de CA/CSR, los tokens de identidad, la accesibilidad de Istiod/SDS y el proceso de renovación de certificados.

istioctl 1.31 no tiene el comando x ca root. No elimine ni regenere una CA solo porque haya caducado un certificado final: una sustitución no planificada de la raíz de confianza puede interrumpir todas las cargas de trabajo dependientes. Repare el problema real de renovación/conectividad/proveedor y utilice el procedimiento compatible de rotación de CA con la superposición de confianza requerida. Reinicie únicamente las cargas de trabajo específicamente afectadas cuando el proceso de recuperación lo requiera.

## Fallo de resolución DNS {#dns-resolution-failure}

### Descripción del problema

Ante un host inexistente o una consulta cuyo tiempo de espera se agota, distinga entre DNS de la aplicación, CoreDNS/DNS ascendente, existencia del Service/sufijos de búsqueda y captura DNS de Istio.

```bash
kubectl -n kube-system get svc kube-dns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=kube-dns
# Run from the affected app container only if it includes these tools.
kubectl -n "$NS" exec "$POD" -c myapp -- cat /etc/resolv.conf
kubectl -n "$NS" exec "$POD" -c myapp -- nslookup myapp.app.svc.cluster.local
```

No suponga que la imagen mínima de aplicación o proxy incluye utilidades de diagnóstico. Utilice un contenedor de diagnóstico aprobado cuando sea necesario. Compruebe NetworkPolicy para UDP/TCP 53, la accesibilidad del nodo/resolvedor y la configuración dnsPolicy/búsqueda del Pod afectado.

Un ServiceEntry registra un servicio externo en Istio; no repara CoreDNS, crea un registro DNS público ni hace resoluble un nombre de host ascendente no resuelto:

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

Sustituya api.example.com por el nombre de host externo real. La resolución DNS determina los endpoints ascendentes. Según el modo, la versión y la configuración, la captura DNS/asignación de IP de Istio puede responder a nombres de servicios con direcciones sintéticas; eso tampoco demuestra que el endpoint ascendente real se resuelva o sea accesible. Consulte las [indicaciones de captura DNS](../advanced/04-dns-cache.md). Para una aplicación que ya envía HTTPS, declarar HTTPS aquí no requiere añadir una segunda capa de origen TLS.

## Tiempo de espera de inicialización de Envoy agotado {#envoy-initialization-timeout}

### Descripción del problema

«Esperando a que el proxy Envoy esté listo» puede deberse a conectividad xDS/CA, configuración rechazada, recursos, problemas de certificados/tokens o ajustes de arranque. Compruebe los estados de Pod/contenedores de inicialización, los registros de proxy/Istiod, los eventos y proxy-status antes de aumentar los retrasos de sondas.

holdApplicationUntilProxyStarts retrasa el inicio de la aplicación hasta que el proxy esté listo; no repara un Envoy que no puede estarlo. Una readinessProbe con solo initialDelaySeconds no es válida porque no tiene una acción de sonda.

Si la aplicación realmente implementa /ready en 8080, este fragmento proporciona un contrato concreto de inicio/disponibilidad:

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

Adapte la acción y los umbrales a la aplicación. StartupProbe controla la tolerancia de inicio; la disponibilidad controla la elegibilidad de endpoints. Ninguno corrige una accesibilidad de Istiod rota. Inspeccione las reescrituras de sondas inyectadas y los ajustes efectivos de disponibilidad del proxy antes de atribuir un fallo de sonda de aplicación a la inicialización de Envoy.

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

Los comandos experimentales pueden cambiar y no sustituyen la verificación del tráfico. Registre los niveles de log antes de una depuración temporal y restáurelos después; reset significa los valores predeterminados, que pueden diferir de ajustes personalizados anteriores. Limite la duración del diagnóstico y revise la configuración/datos de registros recopilados antes de compartir un archivo de informe de errores.

### API de administración de Envoy

Reenvíe únicamente a la interfaz de bucle local:

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

Estos comandos se aplican a Envoy, incluidos sidecars y waypoints, no a la interfaz de administración distinta de ztunnel. Cierre el reenvío de puertos al terminar. Para cambios de registro, prefiera el comando istioctl para el proxy seleccionado mostrado arriba y restaure después los niveles registrados.

### Comprobación habitual de registros

```bash
kubectl -n "$NS" logs "$POD" -c myapp
kubectl -n "$NS" logs "$POD" -c istio-proxy
# Only when that container has a prior instance in this same Pod:
kubectl -n "$NS" logs "$POD" -c istio-proxy --previous
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
```

Recopilar registros de un Pod actual/en ejecución no proporciona retención para Pods eliminados. Conserve la hora de la solicitud, el ID de traza/solicitud, las marcas de respuesta y los cambios pertinentes de endpoints/configuración junto con las pruebas del incidente.

## Referencias

- [Solución de problemas de inyección](https://istio.io/latest/docs/ops/common-problems/injection/) y [configuración de inyección](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [Problemas de red](https://istio.io/latest/docs/ops/common-problems/network-issues/) y [dirección TLS/mTLS automático](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Anotaciones de Istio](https://istio.io/latest/docs/reference/config/annotations/) y [código de apagado del proxy de la versión 1.31](https://github.com/istio/istio/blob/1.31.0/pkg/envoy/agent.go)
- [Terminación de Pods de Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) y [sidecars nativos](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Diagnósticos de proxies](https://istio.io/latest/docs/ops/diagnostic-tools/proxy-cmd/), [integración de CA](https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/) e [ingreso seguro](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Diagnóstico DNS de Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/) y [proxy DNS de Istio](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [Observabilidad](../observability/README.md), [Seguridad](../security/README.md), [Gestión del tráfico](../traffic-management/README.md)
