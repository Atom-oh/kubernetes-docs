# Redes L2–L7 y balanceo de carga

> **Base de revisión**: Cilium 1.20.3, CLI 0.20.1; los ejemplos de Istio usan la API 1.31.
> **Última revisión**: 16 de octubre de 2026

## Configuración del entorno de laboratorio

Use un clúster desechable preparado según las guías de [instalación](README.md) y [redes](03-networking.md). Compruebe la compatibilidad de la plataforma y el kernel, así como las diferencias de versión admitidas por `kubectl`. El laboratorio HTTP requiere dos nodos Linux aptos para programar cargas. El experimento DSR/Maglev también requiere un clúster preparado sin kube-proxy, un endpoint real del servidor de API accesible y una ruta de red compatible.

Elija valores de instalación completos para el experimento. Repetir comandos `cilium install --config ...` no es un procedimiento para migrar funciones en caliente, y eliminar kube-proxy después de una instalación arbitraria no es un atajo seguro.

## Comprensión de las capas OSI

OSI es un modelo conceptual, no siete procesos de Cilium ni una secuencia fija de puntos de enlace de políticas.

| Capa | Función y ejemplos | Relación con Cilium |
|---|---|---|
| Capa física L1 | Bits, medios, transceptores, repetidores | Requisitos de la red y el hardware subyacentes |
| Enlace de datos L2 | Tramas Ethernet, direccionamiento MAC, bridges y switches | Tratamiento de paquetes y anuncios L2 de servicios configurados explícitamente |
| Red L3 | Paquetes IP, enrutamiento, ICMP | Enrutamiento, políticas de identidad/CIDR y gestión de fragmentos admitida |
| Transporte L4 | Segmentos TCP y flujos fiables; datagramas UDP sin garantías de entrega ni orden | Políticas de puertos/protocolos, estado de conexiones y traducción de servicios |
| Sesión L5 | Organización de sesiones y diálogos | Funcionalidad conceptual que a menudo implementan las aplicaciones y los protocolos |
| Presentación L6 | Representación, codificación y transformaciones criptográficas | TLS suele ubicarse aquí de forma conceptual, pero no constituye siempre una capa independiente de Linux |
| Aplicación L7 | HTTP, DNS, gRPC y otros protocolos de aplicación | Políticas de proxy admitidas; que exista un protocolo de aplicación no implica que Cilium pueda analizarlo para aplicar políticas |

### Funciones reales por capa

- **L2:** L2 Announcements es un mecanismo beta, configurado para responder mediante ARP/NDP para direcciones IP de Service aptas. Requiere el reemplazo de kube-proxy y los dispositivos/la conectividad de red local adecuados. El nodo elegido recibe el tráfico de ese Service; esto no ofrece ACL arbitrarias de MAC/VLAN, un bridge L2 de propósito general ni garantiza capturar todos los paquetes. `externalTrafficPolicy: Local` tiene una incompatibilidad documentada; las notas de la versión 1.20.2 incluyen una corrección para las pérdidas de tráfico con esa combinación, así que compruebe el comportamiento en la versión que utilice.
- **L3:** Las políticas de IP/identidad y el enrutamiento tienen requisitos que dependen del modo. Multicast es una función beta que se habilita por separado y requiere VXLAN; la versión mínima documentada del kernel es 5.10 en AMD64 y 6.0 en AArch64. No suponga que funciona en todos los modos de enrutamiento.
- **L4:** Las políticas de puertos TCP/UDP, el seguimiento de conexiones, el balanceo de carga de servicios por socket o paquete y la afinidad admitida operan en distintos puntos de enlace. La decisión por socket puede tomarse antes de construir el paquete.
- **L7:** Los grupos de políticas integrados actualmente son HTTP y DNS. gRPC utiliza la ruta HTTP/2 admitida. Se eliminaron las reglas L7 de Kafka. Las funciones TLS/SNI requieren la configuración de proxy documentada; el contenido de aplicaciones cifrado no se puede inspeccionar automáticamente.

Las políticas HTTP/gRPC usan Envoy; las políticas DNS usan el proxy DNS de Cilium. Según los valores y la compatibilidad de actualización, Envoy puede ser un proceso administrado por el agente o un DaemonSet dedicado `cilium-envoy`. En las instalaciones nuevas, los valores predeterminados del chart 1.20 favorecen el DaemonSet cuando L7 está habilitado, y el perfil siguiente lo configura explícitamente. Añadir una política no anula todos los ajustes de instalación.

## Laboratorio de políticas HTTP

Cree un namespace nuevo y cargas de trabajo con etiquetas coincidentes. Las imágenes, sus digests y la ruta de readiness conocida del servidor proceden de las definiciones oficiales de despliegue de prueba de la CLI.

```bash
set -euo pipefail
kubectl create namespace cilium-l2l7-demo
kubectl label namespace cilium-l2l7-demo docs-audit-lab=cilium-l2l7-05
```

Si el namespace ya existe, deténgase y elija un nombre nuevo de forma coherente en vez de reutilizar recursos de otra ejecución.

**`l7-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-l2l7-demo
  labels:
    app: client
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-l2l7-demo
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app1
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app1
  template:
    metadata:
      labels:
        app: app1
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: client
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: app1-service
  namespace: cilium-l2l7-demo
spec:
  selector:
    app: app1
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f l7-app.yaml
kubectl -n cilium-l2l7-demo wait --for=condition=Ready pod/client pod/outsider --timeout=120s
kubectl -n cilium-l2l7-demo rollout status deployment/app1 --timeout=120s
kubectl -n cilium-l2l7-demo get pods,services -o wide
kubectl -n cilium-l2l7-demo exec client -- \
  curl --fail --silent --show-error --max-time 5 http://app1-service/
```

Compruebe también la conectividad de referencia desde un cliente externo a la política. El Service expone el puerto 80, pero su backend escucha en **8080**; la política de entrada al Pod usa el puerto del backend. Esto reemplaza la configuración de aplicación antigua, que no existía o no coincidía, y un Pod cliente cuyas etiquetas predeterminadas y punto de entrada no correspondían al ejemplo.

**`app1-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: app1-http
  namespace: cilium-l2l7-demo
spec:
  endpointSelector:
    matchLabels:
      app: app1
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-l2l7-demo
        k8s:app: client
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/api/v1$
          headerMatches:
          - name: x-demo-tenant
            value: team-a
```


```bash
kubectl apply -f app1-http.yaml
kubectl -n cilium-l2l7-demo get cnp app1-http -o yaml
```

Una vez aplicada la política, el cliente indicado puede hacer solicitudes GET a `/`. Esta regla solo permite POST a `/api/v1` si se incluye exactamente la cabecera `x-demo-tenant: team-a`; el backend aún debe implementar esa operación de API. Los demás métodos, rutas o pares solo se deniegan si ninguna otra política aplicable los permite. Compruebe tanto la política efectivamente aplicada como las pruebas del flujo, además de las respuestas de la aplicación.

La cabecera es un **filtro de demostración, no un mecanismo de autenticación**. La condición antigua del «token» de 32 caracteres no validaba identidad, firma, emisor, caducidad ni autorización. En el traductor publicado, una cadena en `headers` que contiene un valor busca ese valor de forma literal: `X-Auth-Token: ^[a-zA-Z0-9]{32}$` no valida un token mediante una expresión regular. Use explícitamente `headerMatches` para el requisito de presencia o coincidencia exacta que corresponda, y autentique a los usuarios en la aplicación o en la capa de autenticación adecuada.

Los métodos y las rutas admiten expresiones regulares. La política HTTP integrada de Cilium no permite predicados arbitrarios sobre el cuerpo de las solicitudes. La presencia de una cabecera, la igualdad exacta, el filtrado de URL y la autorización de la aplicación son controles distintos.

## Integración con service mesh

Cilium proporciona redes y las políticas de red admitidas, mientras que Istio administra los proxies configurados y el comportamiento de la malla. La integración no omite automáticamente los sidecars de Istio, elimina el coste de mTLS, unifica todos los traces ni garantiza solicitudes más rápidas.

```text
Configuration: istiod --> Istio Envoy proxies
Request: app --> source sidecar --> Cilium/network --> destination sidecar --> app
```

### Conservar la interceptación de tráfico de Istio

La guía de integración actual de Cilium ofrece la coexistencia con kube-proxy y una opción de reemplazo completo que requiere una configuración cuidadosa. Este es un fragmento para la coexistencia:

**`istio-cilium-values.yaml`**

```yaml
kubeProxyReplacement: false
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```


Para un entorno de reemplazo completo preparado expresamente, `kubeProxyReplacement: true` también requiere un endpoint de API accesible y que se cumplan los requisitos previos del reemplazo. Mantenga `socketLB.hostNamespaceOnly: true` para evitar que la traducción de sockets de Pods eluda la interceptación de Istio, y `cni.exclusive: false` al compartir la configuración de CNI del nodo.

La redirección de sidecars de Istio puede usar un contenedor init o el agente CNI de Istio en los nodos; ambient usa la ruta de nodo/CNI correspondiente. Siga la [guía de instalación mantenida de Istio](../../service-mesh/istio/01-installation.md) y seleccione un modo. El servidor de API de Kubernetes debe poder acceder al webhook de admisión de Istio. Las redes de planos de control administrados o con overlay pueden necesitar una solución de enrutamiento o de red del host documentada; no recomiende `istiod hostNetwork: true` para todos los clústeres con overlay.

### Conservar mTLS y asignar la responsabilidad de L7

No aplique inspección HTTP de texto sin cifrar de Cilium al tráfico de cargas de trabajo cifrado por Istio. Este ejemplo conserva mTLS y el enrutamiento L7 en Istio, y usa en Cilium una política **solo L3/L4**. Deshabilitar mTLS solo para que funcione el antiguo ejemplo L7 combinado cambiaría el diseño de seguridad.

La siguiente configuración es para el modo sidecar, en un namespace `istio-cilium-demo` ya preparado con las cargas `productpage` y `reviews`, un Service `reviews` en el puerto 9080 y Pods `reviews` etiquetados con `version: v1`/`v2`. No es un despliegue completo de Bookinfo.

**`istio-reviews.yaml`**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: istio-cilium-demo
spec:
  hosts:
  - reviews.istio-cilium-demo.svc.cluster.local
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v2
        port:
          number: 9080
  - route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v1
        port:
          number: 9080
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: istio-cilium-demo
spec:
  host: reviews.istio-cilium-demo.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-cilium-demo
spec:
  mtls:
    mode: STRICT
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: reviews-l4
  namespace: istio-cilium-demo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: istio-cilium-demo
        k8s:app: productpage
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
```


DestinationRule define los subconjuntos a los que hace referencia VirtualService. La cabecera `end-user: jason` selecciona una ruta de demostración; no identifica a un usuario autenticado. Compruebe que la inyección de sidecars se haya realizado correctamente, que las etiquetas reales de los endpoints sean las esperadas, que los subconjuntos estén listos y que haya telemetría de la malla.

No reutilice la regla Cilium del puerto 9080 como receta de política ambient: ambient utiliza un túnel cifrado HBONE en el puerto 15008 y cambia los límites de tráfico e identidad visibles. Para esa topología, aplique la política de Istio adecuada y las protecciones de red de Cilium específicas de la plataforma.

## Arquitectura de balanceo de carga

Los mapas de servicios y backends de Cilium, el estado de reverse NAT y el seguimiento de conexiones respaldan distintas etapas del reenvío. El balanceo L7 de Envoy es otro componente; no mezcle su lista de algoritmos con el datapath BPF de los servicios.

### Modos y algoritmos de reenvío BPF

| Ajuste o mecanismo | Significado y límites |
|---|---|
| `loadBalancer.mode: snat` | Modo de reenvío predeterminado; las rutas externas de servicios que correspondan usan traducción del origen y estado inverso, no una ruta de retorno directo |
| `dsr` | Las respuestas del backend remoto pueden omitir el nodo de entrada del balanceador. La red debe permitir esa ruta de retorno; no puede recuperar una IP de cliente que un proxy anterior ya haya traducido |
| `hybrid` | TCP usa DSR y UDP usa SNAT. Este es un comportamiento válido del balanceador, distinto de la combinación no válida de túnel y enrutamiento directo automático |
| Reenvío mediante anotación | Comportamiento por Service que se habilita de forma explícita; la elección de anotación se realiza al crear el Service y cambiarla puede interrumpir conexiones |
| `loadBalancer.algorithm: random` | Algoritmo predeterminado de selección de backends BPF |
| `maglev` | Selección coherente para las rutas norte-sur externas admitidas, incluida la aceleración XDP compatible; Maglev no se aplica a las conexiones este-oeste normales de socket-LB |
| `sessionAffinity: ClientIP` | Afinidad independiente del Service de Kubernetes. La clave es la IP de origen externa o, para el tráfico de socket-LB dentro del clúster que corresponda, la cookie del espacio de nombres de red del cliente |

Maglev no garantiza que las sesiones sobrevivan a la eliminación de un backend. Los nodos necesitan un estado coherente de los backends, el tamaño de tabla y la semilla. El tamaño predeterminado de la tabla es 16381; 65521, que se utiliza más abajo, es un valor permitido, no una recomendación universal. Las tablas más grandes consumen más memoria. La caducidad de la afinidad y el estado de las conexiones son independientes del hash.

El envío DSR puede usar opciones IP con enrutamiento nativo, Geneve en las configuraciones documentadas con enrutamiento nativo o overlay Geneve, o la ruta documentada IPIP/IP6IP6 solo con enrutamiento nativo. El overlay VXLAN no equivale al envío Geneve DSR. IPIP tiene sus propias limitaciones de puerto y traducción; consulte la guía de la versión antes de elegirlo.

La aceleración XDP requiere dispositivos y controladores admitidos. `native` presupone que los dispositivos seleccionados lo admiten; `best-effort` la habilita donde sea compatible. No se activa simplemente escribiendo la clave antigua `enable-xdp-acceleration`, y es posible que el reenvío temprano de XDP no sea visible en el punto de captura posterior de tcpdump.

### Cilium y kube-proxy

| Aspecto | Comparación correcta |
|---|---|
| Implementación de Service en Linux | Cilium usa hooks y mapas BPF; kube-proxy tiene modos iptables y nftables, además de IPVS, obsoleto desde Kubernetes 1.35 |
| Plataforma | Se aplican los requisitos de Linux/kernel indicados por Cilium; kube-proxy en modo kernelspace de Windows es otra implementación |
| Estado de conexión | El estado BPF de conexión/NAT de Cilium es distinto del conntrack de netfilter de Linux; «opcional frente a siempre activo» es una generalización excesiva |
| L7 | Cilium se integra con los proxies admitidos; el reenvío de Services de kube-proxy no es un motor de políticas HTTP |
| Rendimiento | Mida la misma carga de trabajo con la misma configuración; el nombre del producto no determina cuál tendrá un rendimiento fijo superior |

No deduzca que kube-proxy está configurado para DSR solo porque el subsistema IPVS subyacente de Linux disponga de capacidades de enrutamiento directo.

## Laboratorio preparado de DSR/Maglev

Este perfil es para un clúster de prueba IPv4 nuevo y preparado, con overlay Geneve y sin kube-proxy. No migra un CNI existente, elimina kube-proxy ni configura controles de antisuplantación/enrutamiento de la nube. Use un CIDR de Pods que no entre en conflicto y valide la ruta de retorno externa.

**`lb-values.yaml`**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```


Proporcione el endpoint real de la API y una semilla Maglev por clúster que se haya guardado de forma persistente. La semilla es la codificación base64 de 12 bytes aleatorios; genérela una sola vez, guárdela con los valores del clúster y reutilícela, en vez de volver a generarla en cada actualización.

```bash
: "${API_SERVER_HOST:?Set the reachable real API server host, not its ClusterIP}"
: "${API_SERVER_PORT:?Set the actual API server port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.3 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

Use el namespace creado por esta guía en el clúster seleccionado; si se trata de otro clúster desechable, repita allí primero los pasos de creación y etiquetado del namespace. La aplicación de política HTTP y el backend de este balanceador externo usan etiquetas distintas, así que la regla HTTP anterior, que solo afecta al cliente, no bloqueará por accidente este experimento.

**`lb-echo.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lb-echo
  template:
    metadata:
      labels:
        app: lb-echo
    spec:
      automountServiceAccountToken: false
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  type: NodePort
  selector:
    app: lb-echo
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f lb-echo.yaml
kubectl -n cilium-l2l7-demo rollout status deployment/lb-echo --timeout=120s
kubectl -n cilium-l2l7-demo get pods -l app=lb-echo -o wide
kubectl -n cilium-l2l7-demo get service lb-echo -o wide
NODEPORT=$(kubectl -n cilium-l2l7-demo get service lb-echo -o jsonpath='{.spec.ports[0].nodePort}')
```

Use un nodo de entrada accesible que sea **distinto del nodo backend**, y un cliente externo que no esté sujeto al balanceo de carga de socket de Cilium dentro del clúster. Desde ese cliente, solicite `http://ENTRY_NODE_IP:NODEPORT/` con los valores reales. Un curl de Pod a ClusterIP no demuestra el comportamiento externo de DSR ni de Maglev. Compruebe las rutas de solicitud/respuesta y el estado del backend y de la conexión; no los deduzca únicamente de que la respuesta HTTP haya sido correcta.

## Enmascaramiento

El enmascaramiento de la salida de Pods cambia la dirección de origen cuando la ruta externa configurada lo requiere. No es cifrado ni un firewall, y es distinto de DNAT de Services y del reenvío DSR.

El siguiente fragmento excluye el rango de destino de ejemplo `10.0.0.0/8` del enmascaramiento de origen **solo si la red admite realmente esas rutas de origen/retorno de Pods**:

**`masquerade-values.yaml`**

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```


`ipv4NativeRoutingCIDR` expresa el rango que se supone enrutable y la exclusión de enmascaramiento correspondiente. No instala rutas ni cambia todo el datapath al enrutamiento nativo. Una exclusión amplia sin rutas de retorno funcionales puede interrumpir la conectividad.

- El enmascaramiento BPF depende en esta versión de la función BPF NodePort y solo se aplica en los dispositivos que ejecutan el programa BPF. Inspeccione los dispositivos seleccionados; use la configuración documentada `devices` cuando haga falta.
- La implementación de iptables utiliza el comportamiento documentado de `egressMasqueradeInterfaces`. No trate ese campo ni los ejemplos genéricos obsoletos `masquerade-interfaces`/`masquerade-all` como controles BPF universales.
- El enmascaramiento BPF IPv6 está documentado como beta. Ninguna de las implementaciones elimina los requisitos de plataforma/kernel de Cilium; ambas procesan el tráfico en el kernel.
- Las excepciones de direcciones de nodo, las exclusiones de ip-masq-agent y las pasarelas posteriores de nube/NAT pueden afectar a la dirección de origen observada. Use un observador controlado junto con el estado o las capturas del nodo; poder acceder a un sitio público arbitrario no demuestra una implementación de NAT concreta.

En el agente correspondiente:

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
```

## Tratamiento de fragmentos y MTU

El seguimiento de fragmentos publicado guarda la identidad del datagrama y los puertos de origen/destino L4 en mapas LRU limitados. Puede recuperar el contexto de puertos para fragmentos posteriores sin cabecera L4; **no es un motor BPF que reensamble cargas útiles** ni garantiza protección frente a ataques con fragmentos.

La función documentada incluye seguimiento de IPv4 e IPv6, habilitado de forma predeterminada mediante las opciones correspondientes, y está marcada como beta. La opción válida de IPv4 sigue siendo `enable-ipv4-fragment-tracking`. `bpf-fragments-map-max` controla la capacidad del mapa de datagramas registrados; los ajustes antiguos `fragment-tracking-timeout` y `max-fragments-per-flow` no forman parte del contrato de configuración publicado.

Ejemplo explícito con el mapa de configuración adicional del chart:

**`fragment-values.yaml`**

```yaml
extraConfig:
  enable-ipv4-fragment-tracking: 'true'
  bpf-fragments-map-max: '8192'
```


8192 es un ejemplo de capacidad, no el número máximo de fragmentos por flujo. Al diagnosticar la capacidad, inspeccione `cilium_ipv4_frag_datagrams`/`cilium_ipv6_frag_datagrams` y su nivel de presión; la presión no es un contador de reensamblado correcto ni de prevención de ataques.

Prefiera un tamaño de paquete correcto y una ruta funcional de detección de MTU de ruta. PMTUD depende de las señales de error pertinentes y del comportamiento de la red; no garantiza que el tamaño se optimice automáticamente en todas partes. `MTU` de Cilium es la **sobrescritura de la red subyacente**. Como se explica en la [guía de redes](03-networking.md), la sobrecarga normal de VXLAN es de 50 bytes con underlay IPv4 y de 70 con IPv6; establecer a ciegas la base en 1450 para una ruta de 1500 bytes puede descontar la sobrecarga dos veces.

## Observabilidad y solución de problemas

Inspeccione el nodo correcto, el modo real de despliegue de Envoy, la política deseada, el estado efectivo del endpoint y el tráfico reciente. Use `cilium-dbg` para las operaciones locales del agente y la CLI independiente para las operaciones del clúster. Los comandos `policy trace` que se eliminaron y la regeneración forzada de endpoints no son el punto de partida de este diagnóstico.

Mantenga activo en otra terminal un port-forward de un puerto habilitado de Hubble Relay y observe los flujos pertinentes:

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

El rechazo de una política HTTP puede aparecer como HTTP 403, no como un veredicto de paquete DROPPED. Un timeout también puede deberse a problemas de readiness, DNS, enrutamiento, TLS u observación. Correlacione las capas en vez de interpretar cada error como una política aplicada correctamente.

## Límites de validación y fuentes

Estos ejemplos se comprobaron frente a los esquemas y fuentes de la versión, con fixtures locales acotados; no se probaron en producción ni constituyen un benchmark de un clúster en vivo. La ejecución de imágenes, la accesibilidad de webhooks, el tráfico mTLS, las rutas de retorno DSR, el comportamiento de NAT y la fragmentación aún requieren validación en el entorno preparado. Elimine únicamente los recursos de la aplicación etiquetados que se hayan creado para esta ejecución; no elimine el CNI del clúster como parte de la limpieza del laboratorio.

- [Reemplazo de kube-proxy/DSR/Maglev de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/kubeproxy-free.rst), [enmascaramiento](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/masquerading.rst), [tratamiento de fragmentos](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/fragmentation.rst), [implementación del mapa de fragmentos](https://github.com/cilium/cilium/blob/v1.20.3/pkg/maps/fragmap/fragmap.go)
- [Anuncios L2](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/l2-announcements.rst), [multicast](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/multicast.rst), [traductor de reglas HTTP](https://github.com/cilium/cilium/blob/v1.20.3/pkg/envoy/policy/envoy_l7_rules_translator.go), [valores predeterminados del chart de Envoy](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/templates/_helpers.tpl)
- [Integración de Cilium/Istio](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/istio.rst), [modos CNI/contenedor init de Istio](https://istio.io/latest/docs/setup/additional-setup/cni/), [requisitos del webhook](https://istio.io/latest/docs/ops/configuration/mesh/webhook/), [esquemas de Istio 1.31](https://github.com/istio/istio/blob/1.31.0/manifests/charts/base/files/crd-all.gen.yaml)
- [Modos de proxy/afinidad de Services de Kubernetes](https://kubernetes.io/docs/reference/networking/virtual-ips/), [valores de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)


[Volver a la página principal](README.md)

## Cuestionario

[Repase las preguntas sobre L2–L7 y balanceo de carga](../../quizzes/networking/cilium/05-l2-l7-networking-quiz.md).
