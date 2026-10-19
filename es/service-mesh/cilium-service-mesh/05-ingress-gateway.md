# Ingress y Gateway de Cilium Service Mesh

> **Base de revisión**: Cilium 1.20.3; Gateway API 1.6.3; AWS Load Balancer Controller 3.6.0.
> **Última revisión**: 16 de octubre de 2026. Consulte los [requisitos previos de instalación](./README.md) para ver las matrices de Kubernetes/EKS; una versión más reciente, por sí sola, no demuestra compatibilidad.

## Descripción general

Cilium utiliza recursos Ingress y Gateway API de Kubernetes para configurar su plano de datos. eBPF gestiona el reenvío de Service y redirige el tráfico L7 a Envoy local al nodo. Envoy proporciona enrutamiento HTTP y terminación TLS; las rutas TCP/TLS opacas tienen otras capacidades. Los ejemplos siguientes describen puntos de entrada alternativos, no el despliegue completo de una aplicación.

## Arquitectura

![Componentes lógicos de configuración y tráfico: un balanceador de carga en la nube llega al frontend de un Service de Cilium; eBPF redirige el tráfico L7 a Envoy, cuya configuración se deriva de recursos Ingress o Gateway API.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-05-ingress-gateway-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-05-ingress-gateway-0.html)

El bloque Gateway/Ingress representa la configuración, no un proceso que reciba paquetes. Para tráfico L7, la ruta real es balanceador de carga → frontend Service/NodePort → eBPF/TPROXY → Envoy → backend. Cilium aplica la política en el límite externo `world` → `ingress` y, de nuevo, entre `ingress` y el backend. Las políticas deben permitir ambos tramos. La disponibilidad del balanceador de carga en la nube y el registro de destinos son requisitos previos independientes.

## Controlador de Ingress de Cilium

### Instalación y habilitación

```yaml
kubeProxyReplacement: true
l7Proxy: true
envoy:
  enabled: true
ingressController:
  enabled: true
  loadbalancerMode: shared
  default: false
  service:
    type: LoadBalancer
```

Estos son valores de Helm de **sobrescritura** para una instalación de Cilium ya planificada. Combínelos con la configuración CNI/IPAM específica de la plataforma y los parámetros del servidor de API accesible que indica la guía de instalación. Cambiar el reemplazo de kube-proxy en un clúster en ejecución es una migración, no una activación rutinaria de funcionalidad. Renderice y revise el chart fijado en 1.20.3 antes de aplicar cambios.

`ingressController.default` establece `cilium` como **IngressClass predeterminada**; no configura un backend alternativo. El chart crea la clase `cilium`; `ingressController.ingressClassName` no es un valor admitido. Especifique `spec.ingressClassName` para no depender de la clase predeterminada del clúster.

En el modo compartido, los recursos Ingress administrados por Cilium usan el Service compartido `cilium-ingress` en el namespace de la versión de Helm (aquí, `kube-system`). Una anotación por Ingress puede seleccionar el modo dedicado; otros controladores y recursos Gateway API no comparten automáticamente este frontend. Cambiar de modo puede modificar direcciones e interrumpir conexiones. `LoadBalancer` requiere una implementación capaz de aprovisionarlo y reconciliarlo; use la superposición para EKS que aparece más abajo si AWS LBC administra el Service.

### Ejemplo de recurso Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: default
  annotations:
    ingress.cilium.io/loadbalancer-mode: shared
    ingress.cilium.io/tls-passthrough: 'false'
spec:
  ingressClassName: cilium
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls-secret
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

Cree los Services nombrados y endpoints listos en `default`; cada uno debe exponer el puerto 80 del Service. Proporcione `app-tls-secret` con un certificado que cubra `app.example.com` y dirija el DNS a este frontend. La sección TLS termina TLS del cliente en Envoy; el puerto de backend indicado usa HTTP sin cifrar. De forma predeterminada, Cilium establece `enforceHttps: true` y redirige HTTP para hosts con TLS habilitado. Esto no establece mTLS entre cargas de trabajo.

### Enrutamiento basado en rutas

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-routing
  namespace: default
spec:
  ingressClassName: cilium
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /users
        pathType: Prefix
        backend:
          service:
            name: users-service
            port:
              number: 80
      - path: /orders
        pathType: Prefix
        backend:
          service:
            name: orders-service
            port:
              number: 80
      - path: /products
        pathType: Prefix
        backend:
          service:
            name: products-service
            port:
              number: 80
      - path: /health
        pathType: Exact
        backend:
          service:
            name: health-service
            port:
              number: 80
```

`Prefix` compara elementos de ruta: coinciden `/users` y `/users/42`, pero no `/users-old`. `Exact` solo coincide con `/health`. Cilium ordena las reglas Ingress así: primero Exact, luego ImplementationSpecific/regex y después Prefix; dentro de cada grupo, primero se evalúan las coincidencias más largas. Gateway API tiene sus propias reglas de precedencia; el orden de la lista YAML no es un mecanismo general para establecer prioridad de enrutamiento.

### Terminación TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
  namespace: default
spec:
  ingressClassName: cilium
  tls:
  - hosts:
    - secure.example.com
    secretName: app-tls-secret
  rules:
  - host: secure.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: secure-app
            port:
              number: 80
```

Genere el Secret a partir de **archivos PEM reales**, en vez de aplicar Base64 de marcador de posición. El mismo Secret que se use en ambos ejemplos debe contener un certificado cuyos SAN cubran tanto `app.example.com` como `secure.example.com`; de lo contrario, use Secrets separados. Aprovisione un certificado de confianza pública o privada configurada explícitamente mediante su PKI y planifique su renovación.

```bash
openssl x509 -in ./tls.crt -noout -dates -ext subjectAltName
kubectl -n default create secret tls app-tls-secret \
  --cert=./tls.crt --key=./tls.key --dry-run=client -o yaml
```

El último comando solo renderiza el Secret. Revíselo y aplíquelo mediante el flujo de administración de secretos elegido; evite escribir la clave privada en registros compartidos.

### TLS passthrough

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-passthrough
  namespace: default
  annotations:
    ingress.cilium.io/tls-passthrough: 'true'
spec:
  ingressClassName: cilium
  rules:
  - host: backend.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tls-backend
            port:
              number: 443
```

El backend termina TLS y administra un certificado para `backend.example.com`. Cilium compara el SNI TLS; Ingress con passthrough requiere un hostname y la ruta `/`. No se puede reescribir la ruta HTTP ni los encabezados dentro del tráfico cifrado. El backend ve una conexión nueva desde Envoy/nodo, no el socket del cliente original, y Envoy no puede insertar encabezados HTTP de reenvío en este flujo.

## Gateway API

### Habilitar Gateway API

```yaml
gatewayAPI:
  enabled: true
  gatewayClass:
    create: true
  secretsNamespace:
    create: true
    name: cilium-secrets
    sync: true
```

Instale las **CRD Standard de Gateway API 1.6.3** antes de habilitar el controlador; es la versión utilizada por la referencia de instalación de Cilium 1.20.3. Revise las actualizaciones de CRD para todos los controladores que comparten el clúster. No sustituya todo el archivo de valores de Cilium por este fragmento: complementa los requisitos previos de reemplazo de kube-proxy/L7 anteriores.

Las claves admitidas son `gatewayAPI.gatewayClass.create` y `gatewayAPI.secretsNamespace`. `secretNamespace` y `gatewayClassName` en las ubicaciones anteriores se ignoran. De forma predeterminada, las referencias a certificados siguen nombrando Secrets del namespace del Gateway; el namespace de Secrets sincronizados del controlador no reubica la referencia del usuario.

### GatewayClass

Con el parámetro de chart anterior, Cilium administra la GatewayClass `cilium` con el nombre de controlador `io.cilium/gateway-controller`. Inspecciónela con `kubectl get gatewayclass cilium -o yaml`; no cree un segundo responsable para el mismo objeto. Una GatewayClass selecciona un controlador y parámetros, no un balanceador físico compartido.

### Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    hostname: '*.example.com'
    allowedRoutes:
      namespaces:
        from: Same
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: wildcard-tls
        namespace: default
    allowedRoutes:
      namespaces:
        from: Same
```

Antes de usar HTTPS, cree `wildcard-tls` en `default` con un certificado para los hostnames del listener. `*.example.com` no cubre el dominio raíz `example.com` ni nombres de varios niveles como `a.b.example.com`. Estos listeners terminan HTTP/HTTPS; los ejemplos TCP y TLS passthrough posteriores usan Gateways independientes para mantener claros los protocolos y responsables. Cada Service de Gateway generado podría requerir su propio balanceador de carga en la nube.

### HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-routes
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    namespace: default
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1/users
    backendRefs:
    - name: users-v1
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /v2/users
    backendRefs:
    - name: users-v2
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /api
      headers:
      - name: X-API-Version
        value: '2'
    backendRefs:
    - name: api-v2
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: api-v1
      port: 80
```

Cada backend es un Service existente en el namespace de la Route, con puerto 80 y endpoints listos. `sectionName: https` limita intencionalmente esta Route al listener HTTPS. Compruebe `Accepted` y `ResolvedRefs` en la entrada correcta de `status.parents`, y las condiciones `Programmed`/`Accepted` del Gateway/listener con el `observedGeneration` actual. Una configuración aceptada no demuestra por sí sola que funcionen el DNS, la confianza del certificado, el estado de los destinos o la conectividad de la aplicación.

### División del tráfico por peso

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: canary-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  hostnames:
  - app.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: app-stable
      port: 80
      weight: 90
    - name: app-canary
      port: 80
      weight: 10
```

Los pesos son probabilidades relativas de selección; no garantizan que cada grupo de diez solicitudes contenga exactamente nueve solicitudes estables. Las conexiones, reintentos y el muestreo pueden cambiar los recuentos observados. Este ejemplo solo se asocia a HTTPS y usa un hostname distinto del ejemplo de API.

### Transformación de solicitudes y respuestas

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: transform-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    filters:
    - type: RequestHeaderModifier
      requestHeaderModifier:
        set:
        - name: X-Doc-Route
          value: api-v2
        remove:
        - X-Internal-Header
    - type: URLRewrite
      urlRewrite:
        hostname: internal-api.default.svc
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /v2/api
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        set:
        - name: X-Doc-Gateway
          value: cilium
    backendRefs:
    - name: api-service
      port: 80
  hostnames:
  - transform.example.com
```

Los valores de encabezado son **cadenas literales**. `X-Doc-Route` y `X-Doc-Gateway` son marcadores de diagnóstico, no identificadores de solicitud generados ni tiempos de respuesta medidos. La reescritura de host usa `URLRewrite.hostname`; no se duplica como una modificación del encabezado `Host`. Estos encabezados no autentican al solicitante. El tratamiento del encabezado `Server` de la respuesta también depende de la transformación de ese encabezado en Envoy del controlador; si desea cambiar ese comportamiento, use un `CiliumGatewayClassConfig` verificado.

### Redirección

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-http
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: http
  hostnames:
  - '*.example.com'
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        port: 443
        statusCode: 308
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-path
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  hostnames:
  - old.example.com
  rules:
  - matches:
    - path:
        type: Exact
        value: /old-path
    filters:
    - type: RequestRedirect
      requestRedirect:
        path:
          type: ReplaceFullPath
          replaceFullPath: /new-path
        statusCode: 308
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-host
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  hostnames:
  - old.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /legacy
    filters:
    - type: RequestRedirect
      requestRedirect:
        hostname: legacy.example.com
        statusCode: 307
```

La redirección del esquema se asocia **solo a `http`**, de modo que las solicitudes HTTPS no puedan volver a redirigirse indefinidamente a la misma URL. Las otras dos Routes se asocian solo a `https` y a un hostname de origen restringido. Las redirecciones permanentes 308 y temporales 307 conservan el método/cuerpo de la solicitud; los clientes se comportan de forma distinta con 301/302, así que no se deben recomendar universalmente para escrituras. Redirigir una solicitud HTTP inicial no puede deshacer los datos de texto plano que el cliente ya envió. RequestRedirect y URLRewrite son filtros distintos y no se pueden combinar en una misma regla.

### TCPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: tcp-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: tcp
    protocol: TCP
    port: 9000
    allowedRoutes:
      namespaces:
        from: Same
      kinds:
      - kind: TCPRoute
---
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: tcp-route
  namespace: default
spec:
  parentRefs:
  - name: tcp-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: tcp-service
      port: 9000
```

Gateway API 1.6.3 sirve TCPRoute en **v1**; no sirve la versión antigua `v1alpha2`. TCPRoute reenvía un flujo TCP opaco y no inspecciona rutas HTTP. TCP puede transportar HTTP o TLS, pero eso no confiere a esta Route funciones de enrutamiento HTTP ni semántica de terminación TLS. La traducción de Gateway L4 de Cilium 1.20.3 usa EndpointSlices de backend; no dé por supuesto que la implementación de endpoints del frontend Envoy L7 sea idéntica.

### TLSRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: tls-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: tls
    protocol: TLS
    port: 443
    hostname: secure.example.com
    tls:
      mode: Passthrough
    allowedRoutes:
      namespaces:
        from: Same
      kinds:
      - kind: TLSRoute
---
apiVersion: gateway.networking.k8s.io/v1
kind: TLSRoute
metadata:
  name: tls-route
  namespace: default
spec:
  parentRefs:
  - name: tls-gateway
    sectionName: tls
  hostnames:
  - secure.example.com
  rules:
  - backendRefs:
    - name: tls-backend
      port: 443
```

En esta base, TLSRoute también se sirve en **v1**. Requiere un listener `TLS` compatible con `mode: Passthrough`, no el listener de terminación HTTPS anterior. El backend administra el certificado de `secure.example.com`; SNI selecciona el backend mientras el contenido HTTP permanece cifrado. Compruebe el Service generado, el estado del listener y la confianza TLS de extremo a extremo.

## Patrones de integración con EKS

### NLB + Cilium Ingress

```yaml
ingressController:
  enabled: true
  loadbalancerMode: shared
  enableProxyProtocol: false
  service:
    type: LoadBalancer
    loadBalancerClass: service.k8s.aws/nlb
    allocateLoadBalancerNodePorts: true
    externalTrafficPolicy: Cluster
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-scheme: internal
      service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
      service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
      service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol: TCP
      service.beta.kubernetes.io/aws-load-balancer-healthcheck-port: traffic-port
```

Este NLB es **interno** por diseño: el único punto de entrada público es CloudFront, que llega a él mediante un origen de VPC de CloudFront. Su grupo de seguridad solo debe admitir el grupo de seguridad del origen de VPC (o la lista de prefijos administrada por CloudFront), nunca un CIDR público.

Esta superposición describe **NLB administrado por AWS LBC → NodePort de EC2 → Envoy de Cilium Ingress**. Requiere AWS LBC 3.6.0, sus requisitos previos de IAM/subredes/grupos de seguridad, nodos EC2 compatibles, una configuración de EKS/CNI admitida por Cilium y NodePorts asignados. No es una receta de instalación de Cilium para EKS Auto Mode ni Fargate. `service.k8s.aws/nlb` selecciona explícitamente AWS LBC; la anotación heredada `aws-load-balancer-type: nlb` no expresa esa propiedad.

Use destinos de tipo instancia para este frontend L7. El Service compartido de Ingress de Cilium 1.20.3 tiene un EndpointSlice sintético (`192.192.192.192:9999`, sin referencias a Pods de destino). El resolvedor de destinos IP de AWS LBC requiere referencias a Pods y omite estos endpoints. Cambiar simplemente este Service a `ip` **no descubre** los procesos Envoy locales al nodo. Esto es específico del frontend L7 de Cilium; los Services normales de cargas de trabajo y los EndpointSlices Gateway L4 actuales son distintos.

La comprobación de estado TCP verifica la accesibilidad de transporte en el NodePort, no la ruta de aplicación `/healthz`, la validez de TLS ni una ruta HTTP específica de host. El balanceo entre zonas usa la anotación actual de atributos del balanceador y requiere revisar costos/tráfico. No cambie en el sitio la propiedad del controlador ni el tipo de balanceador de un Service existente suponiendo que será una migración sin interrupciones.

**Identidad del cliente y protocolo PROXY opcional:** Cilium conserva el origen que ve en su frontend para el procesamiento HTTP de Envoy con ambas políticas de tráfico externo, `Cluster` y `Local`. Que ese origen sea el cliente original depende primero del NLB ascendente y de los atributos del grupo de destinos. Los destinos TCP de instancia suelen conservar la IP del cliente; el protocolo PROXY no siempre es necesario. Si su topología lo requiere, coordine esta superposición adicional con la configuración del NLB:

```yaml
ingressController:
  enableProxyProtocol: true
  service:
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: '*'
```

Esto habilita PPv2 en el NLB y su analizador en Cilium Ingress. El despliegue coordinado requiere habilitar ambos lados; activar solo uno interrumpe el tráfico. El analizador requiere un encabezado PROXY, por lo que las sondas HTTP/TLS directas que no lo incluyen fallan. AWS LBC desaconseja combinar PPv2 con destinos de instancia y `externalTrafficPolicy: Local`; el ejemplo conserva `Cluster`. Las comprobaciones HTTP/HTTPS también necesitan un analizador compatible. Restrinja el acceso directo a la ruta del proxy de confianza: los metadatos PP y los encabezados HTTP reenviados no son identidades autenticadas. `gatewayAPI.enableProxyProtocol` es un parámetro distinto para Gateway API; el indicador de Ingress no lo configura.

### ALB + Cilium

Se puede combinar ALB → Envoy de Cilium, pero los siguientes requisitos previos deben diseñarse y probarse para el entorno real. No existe un atajo universal y funcional de `target-type: ip` para los EndpointSlices L7 sintéticos descritos arriba.

| Límite | Decisión necesaria |
|---|---|
| Controlador y namespace | Un Ingress de ALB usa `spec.ingressClassName: alb`. Su Service backend debe estar en el **mismo namespace**; el Service compartido `cilium-ingress` suele estar en `kube-system`, no en `default`. |
| Destinos | Para una ruta basada en nodos, use un Service NodePort planificado explícitamente y `target-type: instance` de ALB; verifique los nodos aptos, la asignación de NodePort y los grupos de seguridad. No convierta silenciosamente un Service que ya administra un NLB. |
| TLS | Decida si ALB termina TLS y reenvía HTTP o HTTPS. Asociar un certificado de servidor de ACM no equivale a mTLS de cliente. Si ALB reenvía HTTP, las redirecciones HTTPS de Cilium pueden crear un bucle, salvo que se coordinen los listeners y el comportamiento de redirección. |
| Estado | Las comprobaciones de ALB usan su propio encabezado Host, no `app.example.com` automáticamente; una ruta de aplicación específica del host podría responder 404. Defina y pruebe una ruta/puerto de comprobación de estado adecuado. |
| Atribución del cliente | Configure el número de saltos XFF de confianza de Cilium para la cadena de proxy real, depure los encabezados no confiables y evite el acceso directo al backend que omita ALB. |

El ejemplo anterior usaba un namespace y destinos IP incorrectos y omitía estas decisiones; se reemplazó por estos requisitos de implementación. Esta guía no ha desplegado ni probado bajo carga esta composición.

### Arquitectura híbrida

![El tráfico de clientes externos se divide entre un ALB y un NLB de AWS; ALB envía el tráfico al Gateway de Cilium para enrutar L7 a la aplicación web y al servidor API, mientras NLB lo envía al balanceador Cilium para distribuir L4 al servicio gRPC.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-05-ingress-gateway-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-05-ingress-gateway-1.html)

Este es un diagrama de composición lógica, no un manifiesto de despliegue validado. La ruta ALB requiere las decisiones anteriores sobre namespace, destinos, TLS, estado y confianza. La ruta L4 de NLB puede transportar un flujo gRPC sin interpretar métodos RPC individuales. Añadir Cilium detrás de ALB no elimina los cargos de ALB ni convierte las funciones de ALB en funciones nativas de Cilium.

## Gateway multiinquilino

### Gateway por namespace

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium-shared
spec:
  controllerName: io.cilium/gateway-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: team-a-gateway
  namespace: team-a
spec:
  gatewayClassName: cilium-shared
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.team-a.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: team-a-tls
    allowedRoutes:
      namespaces:
        from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: team-b-gateway
  namespace: team-b
spec:
  gatewayClassName: cilium-shared
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.team-b.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: team-b-tls
    allowedRoutes:
      namespaces:
        from: Same
```

Cree primero cada namespace y su propio Secret TLS válido. Compartir la GatewayClass `cilium-shared` **no significa** que ambos Gateways compartan un único Service/balanceador de carga. `from: Same` limita la asociación de Routes al namespace de cada Gateway; RBAC debe controlar por separado quién puede cambiar Gateways, Secrets, Routes y etiquetas de namespace.

### Enrutamiento entre namespaces

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: shared-gateway
  namespace: gateway-system
spec:
  gatewayClassName: cilium
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.example.com'
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: shared-tls
---
apiVersion: v1
kind: Namespace
metadata:
  name: app-team
  labels:
    gateway-access: 'true'
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-route
  namespace: app-team
spec:
  parentRefs:
  - name: shared-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - app.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: app-service
      port: 80
```

Cree `gateway-system` y su Secret `shared-tls` con certificados que cubran los hostnames permitidos. El selector de namespace autoriza la asociación de Route; no autentica usuarios ni autoriza solicitudes de aplicación. Un administrador debe controlar la etiqueta `gateway-access`.

El backend `app-service` mostrado es local a `app-team`, así que no necesita ReferenceGrant. Si una Route hace referencia a `backend-team/shared-api`, el namespace backend debe conceder explícitamente esa referencia:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: ReferenceGrant
metadata:
  name: allow-app-team
  namespace: backend-team
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: app-team
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shared-api-route
  namespace: app-team
spec:
  parentRefs:
  - name: shared-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - shared-api.example.com
  rules:
  - backendRefs:
    - name: shared-api
      namespace: backend-team
      port: 80
```

Antes de usar esta alternativa, cree `backend-team/shared-api` con el puerto 80 del Service. La asociación Route → Gateway entre namespaces usa `allowedRoutes`; las referencias Route → Service backend entre namespaces usan `ReferenceGrant`. Son comprobaciones de permisos distintas. En Gateway API 1.6.3 se sirve ReferenceGrant v1; v1beta1 también sigue disponible.

## Configuración avanzada del balanceo de carga

### Comprobación de estado de Service

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: health-check-config
  namespace: default
spec:
  services:
  - name: my-service
    namespace: default
    ports:
    - 80
    listener: health-check-config-listener
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: health-check-config-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: health-check-config
          route_config:
            name: health-check-config-routes
            virtual_hosts:
            - name: app
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/my-service
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/my-service
    connect_timeout: 5s
    type: EDS
    health_checks:
    - timeout: 5s
      interval: 10s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: /health
        host: health-check.local
        expected_statuses:
        - start: 200
          end: 300
    outlier_detection:
      consecutive_5xx: 5
      interval: 10s
      base_ejection_time: 30s
      max_ejection_percent: 50
      enforcing_consecutive_5xx: 100
```

Esta es una cadena CEC autónoma completa: puerto 80 del Service → Listener nombrado → ruta HTTP → clúster EDS. Cilium proporciona la configuración de endpoints xDS para el Service referenciado. Cree `default/my-service` con backends listos y no lo asigne también a otro CEC ni a una configuración Ingress/Gateway generada. La personalización CEC no es un mecanismo para modificar recursos que administra un controlador.

Todos los backends deben aceptar realmente `Host: health-check.local` y `/health`. Los rangos de estado de Envoy excluyen el límite superior, así que `[200, 300)` abarca todas las respuestas 2xx. Las comprobaciones activas y la detección pasiva de valores atípicos son mecanismos distintos; los límites de expulsión y el comportamiento de emergencia no garantizan que se excluyan todos los endpoints con fallos. Valídelos según el número de backends y el modelo de fallos.

### Configuración del pool de conexiones {#connection-pool-configuration}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: connection-pool
  namespace: default
spec:
  services:
  - name: high-traffic-service
    namespace: default
    ports:
    - 80
    listener: connection-pool-listener
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: connection-pool-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: connection-pool
          route_config:
            name: connection-pool-routes
            virtual_hosts:
            - name: app
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/high-traffic-service
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/high-traffic-service
    connect_timeout: 5s
    type: EDS
    typed_extension_protocol_options:
      envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
        '@type': type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions
        explicit_http_config:
          http2_protocol_options:
            max_concurrent_streams: 1000
            initial_stream_window_size: 65536
            initial_connection_window_size: 1048576
    circuit_breakers:
      thresholds:
      - priority: DEFAULT
        max_connections: 10000
        max_pending_requests: 10000
        max_requests: 10000
        max_retries: 5
```

Cree `default/high-traffic-service` en el puerto 80 con backends que admitan explícitamente HTTP/2 sin cifrar (h2c). La opción de protocolo tipada selecciona HTTP/2 ascendente; no negocia el protocolo automáticamente. `accept_http_10` solo aceptaría HTTP/1.0, no configura un pool de conexiones HTTP/1.1. Para backends HTTP/1, elija la configuración explícita correspondiente.

Los umbrales de disyuntor se aplican por clúster/prioridad de Envoy, no son cuotas ni recomendaciones de capacidad para toda la flota. `max_retries` limita los reintentos simultáneos; no es la cantidad de reintentos por solicitud. La ruta de aquí establece `num_retries: 0`. Aumentar los límites de conexiones/flujos requiere probar los recursos y el backend; los valores numéricos son ilustrativos.

## Comparación con AWS Load Balancer Controller

| Capacidad | Cilium Ingress/Gateway | AWS Load Balancer Controller 3.6 |
|---|---|---|
| Plano de datos | Reenvío de Service/L4 con eBPF; Envoy para funciones HTTP/TLS | ALB o NLB de AWS |
| Gateway API | Compruebe las tablas de funciones/conformidad de la versión fijada de Cilium | HTTPRoute/GRPCRoute se asignan a ALB; TCPRoute/UDPRoute/TLSRoute, a NLB; no se admite L4 y L7 mezclado en un mismo Gateway |
| TLS e identidad | Terminación/passthrough TLS de Ingress; el cifrado/autenticación de cargas de trabajo es una [configuración de seguridad](./03-security.md) independiente | Certificados de servidor ACM; el mTLS de cliente de ALB requiere su modo de autenticación mutua/almacén de confianza |
| Costo | Recursos de nodo/proxy **más cualquier balanceador de carga en la nube aprovisionado y cargos de red** | ALB/NLB aprovisionado, capacidad/uso y cargos de red |
| Personalización | Funciones Gateway API admitidas y CEC administrados por separado; los objetos generados siguen siendo propiedad del controlador | Funciones de listener/regla/grupo de destinos de AWS expuestas mediante las API/anotaciones de LBC |
| Rendimiento | Mida la topología, el cifrado y la carga de trabajo reales | Mida la misma carga y los límites del servicio; no hay un orden universal por latencia |

LBC 3.6 documenta **Gateway API 1.6.0** como su base de pruebas; la referencia de instalación de Cilium usa **1.6.3**. Si un clúster comparte estas CRD, necesita pruebas de compatibilidad; no suponga que la entrada más reciente del catálogo está admitida por todos los controladores.

Elija ALB cuando necesite integraciones L7 de AWS, NLB cuando necesite el comportamiento de transporte/destinos correspondiente, y funciones de Cilium según los requisitos de enrutamiento/políticas dentro del clúster. Actualmente, NLB admite grupos de destinos ponderados con valores de **0–999** para flujos nuevos; la exposición de esa función por el controlador y la semántica de una Route concreta son cuestiones aparte. Los cambios de peso normales conservan las conexiones existentes, pero, según la documentación de AWS, establecer el peso de un grupo de destinos en **0** cierra sus conexiones existentes después de un período corto. No describa esa operación como un drenaje que conserve las conexiones.

La figura de decisión anterior repetía afirmaciones no admitidas sobre costos, latencia, mTLS y Gateway API. La tabla sustituye esas afirmaciones, pero no elimina ninguna de las dos opciones de integración.

## Supervisión

### Métricas de Gateway

```bash
kubectl get gatewayclass cilium -o yaml
kubectl get gateway,httproute,tcproute,tlsroute -A
kubectl -n default describe gateway main-gateway
kubectl -n default get httproute api-routes -o yaml
kubectl -n kube-system exec ds/cilium -- cilium-dbg status --verbose
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin metrics -f downstream_rq
```

### Métricas de Prometheus

Primero habilite y recopile el endpoint Prometheus de Envoy de Cilium mediante la [guía de observabilidad](./04-observability.md). Configure una etiqueta de destino `cluster` estable si una misma instancia de Prometheus recibe datos de varios clústeres. La imagen nativa de Envoy de Cilium expone `envoy_http_conn_manager_prefix`, con valores generados como `listener-insecure`, `listener-secure` y variantes específicas del puerto, no un valor fijo `cilium-gateway`. Se pueden reutilizar prefijos entre Gateways del mismo Envoy; estos ejemplos describen un **proxy/HCM recopilado**, no contabilidad garantizada por Gateway. Inspeccione las etiquetas reales antes de crear paneles.

Las tres consultas siguientes muestran la tasa de solicitudes iniciadas, el porcentaje de contadores de respuesta completados clasificados como 5xx y la duración p99 en **segundos**. El numerador faltante de 5xx solo se completa a partir del denominador observado correspondiente; la ausencia de tráfico/telemetría no se convierte en un cero saludable. El filtro de denominador positivo omite series inactivas. El histograma `downstream_rq_time` de Envoy usa **milisegundos**, de ahí el `/ 1000`. Agregue los buckets del histograma conservando `le` antes de calcular el cuantil. Las pocas muestras, los intervalos sin scraping y la ausencia de histogramas también requieren supervisión aparte.

```promql
sum by (cluster, instance, envoy_http_conn_manager_prefix) (
  rate(envoy_http_downstream_rq_total[5m])
)
```

```promql
100 *
(
  sum by (cluster, instance, envoy_http_conn_manager_prefix) (
    rate(envoy_http_downstream_rq_xx{envoy_response_code_class="5"}[5m])
  )
  or
  0 * sum by (cluster, instance, envoy_http_conn_manager_prefix) (
    rate(envoy_http_downstream_rq_xx[5m])
  )
)
/
(
  sum by (cluster, instance, envoy_http_conn_manager_prefix) (
    rate(envoy_http_downstream_rq_xx[5m])
  ) > 0
)
```

```promql
histogram_quantile(
  0.99,
  sum by (cluster, instance, envoy_http_conn_manager_prefix, le) (
    rate(envoy_http_downstream_rq_time_bucket[5m])
  )
) / 1000
```

## Pasos siguientes

- [Prácticas recomendadas](./06-best-practices.md): requisitos previos y límites operativos

## Referencias

- [Ingress de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/ingress.rst)
- [Tráfico, IP de origen y política de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/ingress-reference.rst)
- [Instalación de Gateway API en Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/gateway-api/gateway-api.rst)
- [Valores Helm de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)
- [CRD Standard de Gateway API 1.6.3](https://github.com/kubernetes-sigs/gateway-api/tree/v1.6.3/config/crd/standard)
- [Configuración de NLB de AWS LBC 3.6](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/service/nlb.md)
- [Anotaciones de AWS LBC 3.6](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/service/annotations.md)
- [Gateway API de AWS LBC 3.6](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/gateway/gateway.md)
- [Atributos del grupo de destinos NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html)
- [Pesos de listener NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [Estadísticas de solicitudes de Envoy 1.38](https://www.envoyproxy.io/docs/envoy/v1.38.6/configuration/http/http_conn_man/stats)
