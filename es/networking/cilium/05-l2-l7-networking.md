# Networking y balanceo de carga L2–L7

> **Línea base revisada**: Cilium 1.20.2, CLI 0.20.1; los ejemplos de Istio usan la API 1.31.
> **Última actualización**: October 15, 2026

## Configuración del entorno de laboratorio

Utiliza un clúster desechable preparado mediante las guías de [instalación](README.md) y [networking](03-networking.md). Comprueba la compatibilidad de plataforma/kernel y la divergencia de versiones de kubectl. El laboratorio HTTP necesita dos nodos Linux planificables. El experimento DSR/Maglev también necesita un clúster preparado sin kube-proxy, un endpoint real de API server accesible y una ruta de red compatible.

Elige valores de instalación completos para el experimento. Los comandos repetidos `cilium install --config ...` no constituyen un procedimiento de migración de funcionalidades en vivo, y eliminar kube-proxy tras una instalación arbitraria no es un atajo seguro.

## Comprender las capas OSI

OSI es un modelo conceptual, no siete procesos de Cilium ni una secuencia fija de hooks de políticas.

| Capa | Función / ejemplos | Relación con Cilium |
|---|---|---|
| L1 física | Bits, medios, transceptores, repetidores | Requisitos de hardware/red subyacentes |
| L2 enlace de datos | Tramas Ethernet, direccionamiento MAC, bridges/switches | Manejo de paquetes y anuncios de Service L2 configurados explícitamente |
| L3 red | Paquetes IP, routing, ICMP | Routing, política de identidad/CIDR y manejo de fragmentos compatible |
| L4 transporte | Segmentos TCP y flujos confiables; datagramas UDP sin garantías de entrega/orden | Política de puerto/protocolo, estado de conexión, traducción de Service |
| L5 sesión | Organización de sesiones/diálogos | Funcionalidad conceptual que a menudo se implementa dentro de aplicaciones/protocolos |
| L6 presentación | Representación, codificación y transformaciones criptográficas | TLS a menudo se asigna aquí conceptualmente, no es una capa Linux separada universal |
| L7 aplicación | HTTP, DNS, gRPC y otros protocolos de aplicación | Políticas de proxy compatibles; la existencia de un protocolo de aplicación no implica un analizador de políticas de Cilium |

### Funcionalidades específicas de cada capa

- **L2:** L2 Announcements es un mecanismo beta de respuesta ARP/NDP configurado para IP de Service elegibles. Necesita reemplazo de kube-proxy y dispositivos/conectividad de red local adecuados. El nodo elegido recibe el tráfico de ese Service; esto no es compatibilidad arbitraria con ACL de MAC/VLAN ni un bridge L2 general o la promesa de capturar cada paquete. `externalTrafficPolicy: Local` tiene una incompatibilidad documentada.
- **L3:** La política IP/de identidad y el routing tienen requisitos específicos de cada modo. Multicast es una funcionalidad beta habilitada por separado que requiere VXLAN; el mínimo de kernel documentado es 5.10 en AMD64 y 6.0 en AArch64. No asumas que funciona en todos los modos de routing.
- **L4:** La política de puertos TCP/UDP, el seguimiento de conexiones, el balanceo de carga de Service en socket/paquetes y la afinidad compatible operan en hooks diferentes. Una decisión de socket puede ocurrir antes de la construcción del paquete.
- **L7:** Los grupos de políticas integrados actuales son HTTP y DNS. gRPC utiliza la ruta HTTP/2 compatible. Las reglas L7 de Kafka se eliminaron. Las funcionalidades TLS/SNI requieren la configuración de proxy documentada; el contenido de aplicaciones cifrado no se puede inspeccionar automáticamente.

La política HTTP/gRPC usa Envoy; la política DNS usa el proxy DNS de Cilium. Envoy puede ser un proceso administrado por el agente o un DaemonSet `cilium-envoy` dedicado, según los valores/la compatibilidad de actualización. Los valores predeterminados del chart 1.20 recién instalado con L7 habilitado prefieren el DaemonSet, y el perfil siguiente lo establece explícitamente. Añadir una política no invalida todas las configuraciones de instalación.

## Laboratorio de política HTTP

Crea un namespace nuevo y workloads coincidentes. Las imágenes/digests y la ruta de disponibilidad conocida del servidor proceden de las definiciones de despliegue de pruebas del CLI oficial.

```bash
set -euo pipefail
kubectl create namespace cilium-l2l7-demo
kubectl label namespace cilium-l2l7-demo docs-audit-lab=cilium-l2l7-05
```

Detente si el namespace ya existe; elige de forma coherente un nombre nuevo en lugar de reutilizar los recursos de otra ejecución.

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

Verifica también la conectividad de línea base de outsider. El Service expone el puerto 80, pero su backend escucha en **8080**; la política de entrada del Pod utiliza el puerto del backend. Esto sustituye la configuración de aplicación anterior inexistente/no coincidente y un Pod de cliente cuyas etiquetas/punto de entrada predeterminados no coincidían con el ejemplo.

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

Tras la realización de la política, el cliente nombrado puede realizar solicitudes GET a `/`. POST a `/api/v1` se permite mediante esta regla únicamente con el encabezado exacto `x-demo-tenant: team-a`; el backend aún debe implementar esa operación de API. Otros métodos/rutas/pares se deniegan solo en la medida en que ninguna otra política aplicable los permita. Verifica la política realizada y la evidencia de flujos, además de las respuestas de la aplicación.

El encabezado es un **filtro de demostración, no autenticación**. La condición anterior de “token” de 32 caracteres no validaba identidad, firma, emisor, vencimiento ni autorización. En el traductor publicado, una cadena `headers` que contiene un valor coincide literalmente con ese valor: `X-Auth-Token: ^[a-zA-Z0-9]{32}$` no es un validador de token con expresiones regulares. Usa `headerMatches` explícitos para el requisito previsto de exactitud/presencia, y autentica a los usuarios en la aplicación/capa de autenticación adecuada.

Los métodos y las rutas admiten expresiones regulares. La política HTTP integrada de Cilium no tiene un predicado arbitrario para el cuerpo de solicitudes. La presencia de encabezados, la igualdad exacta, el filtrado de URL y la autorización de la aplicación son controles diferentes.

## Integración de Service Mesh

Cilium proporciona networking y políticas de red compatibles, mientras que Istio posee sus proxies configurados y el comportamiento del mesh. La integración no omite automáticamente los sidecars de Istio, elimina su coste de mTLS, unifica todos los rastreos ni garantiza solicitudes más rápidas.

```text
Configuration: istiod --> Istio Envoy proxies
Request: app --> source sidecar --> Cilium/network --> destination sidecar --> app
```

### Preservar la intercepción de tráfico de Istio

La guía actual de integración de Cilium ofrece coexistencia con kube-proxy y una opción de reemplazo completo configurada cuidadosamente. Un fragmento de coexistencia es:

**`istio-cilium-values.yaml`**

```yaml
kubeProxyReplacement: false
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```


Para una configuración de reemplazo completo preparada intencionalmente, `kubeProxyReplacement: true` también requiere un endpoint de API accesible y los requisitos previos del reemplazo. Mantén `socketLB.hostNamespaceOnly: true` para evitar que la traducción de socket de Pod omita la intercepción de Istio, y `cni.exclusive: false` al compartir la configuración CNI del nodo.

La redirección del sidecar de Istio puede usar un init container o el agente de nodo Istio CNI; el modo ambient usa su ruta de nodo/CNI correspondiente. Sigue la [guía de instalación de Istio mantenida](../../service-mesh/istio/01-installation.md) y selecciona un modo. El API server de Kubernetes debe alcanzar el webhook de admisión de Istio. Las redes de plano de control administrado/overlay pueden necesitar una solución documentada de routing o host network; no prescribas `istiod hostNetwork: true` para todos los clústeres overlay.

### Mantener mTLS y asignar la responsabilidad L7

No apliques inspección HTTP de Cilium en texto plano al tráfico de workloads cifrado por Istio. Este ejemplo mantiene mTLS de Istio y el routing L7 en Istio, y utiliza una política de Cilium **solo L3/L4**. Deshabilitar mTLS solo para que el antiguo ejemplo L7 combinado funcione cambiaría el diseño de seguridad.

Lo siguiente es una configuración de **modo sidecar** para un namespace `istio-cilium-demo` ya preparado con workloads `productpage` y `reviews`, un Service de reviews en el puerto 9080, y Pods de reviews etiquetados `version: v1`/`v2`. No es un despliegue completo de Bookinfo.

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


La DestinationRule define los subconjuntos referenciados por el VirtualService. El encabezado `end-user: jason` selecciona una ruta de demostración; no es una identidad autenticada. Verifica la inyección exitosa del sidecar, las etiquetas reales de los endpoints, la disponibilidad de los subconjuntos y la telemetría del mesh.

No reutilices la regla Cilium 9080 como receta de política para ambient: HBONE de ambient usa tunelización cifrada en el puerto 15008 y cambia el límite de tráfico/identidad visible. Aplica la política de Istio adecuada y las protecciones de red de Cilium específicas de la plataforma para esa topología.

## Arquitectura de balanceo de carga

Los mapas de Service de Cilium, los mapas de backend, el estado de NAT inverso y el seguimiento de conexiones son compatibles con diferentes etapas de reenvío. El balanceo de carga L7 de Envoy es otro componente; no combines su lista de algoritmos con el datapath de Service BPF.

### Modos y algoritmos de reenvío BPF

| Configuración / mecanismo | Significado y límites |
|---|---|
| `loadBalancer.mode: snat` | Modo de reenvío predeterminado; las rutas de Service externas aplicables usan traducción de origen/estado inverso en lugar de una ruta de retorno directo |
| `dsr` | Las respuestas de backend remotos pueden omitir el nodo de balanceo de carga de entrada. La red debe permitir esa ruta de retorno; no puede recuperar una IP de cliente ya traducida por un proxy ascendente |
| `hybrid` | TCP usa DSR y UDP usa SNAT. Este es un comportamiento de balanceador de carga válido, distinto de la combinación inválida de túnel/auto-direct-routing |
| Reenvío basado en anotaciones | Comportamiento compatible de participación voluntaria por Service; las anotaciones de reenvío son elecciones en el momento de la creación y cambiarlas puede interrumpir conexiones |
| `loadBalancer.algorithm: random` | Algoritmo predeterminado de selección de backend BPF |
| `maglev` | Selección consistente para rutas N–S externas compatibles, incluida la aceleración XDP compatible; las conexiones E–W socket-LB ordinarias no están sujetas a Maglev |
| `sessionAffinity: ClientIP` | Afinidad de Service de Kubernetes independiente. La clave es la IP de origen externa o, para el tráfico socket-LB dentro del clúster aplicable, la cookie del namespace de red del cliente |

Maglev no garantiza que las sesiones sobrevivan a la eliminación de un backend. Los nodos necesitan un estado de backend, tamaño de tabla y semilla consistentes. El tamaño de tabla predeterminado es 16381; 65521 usado a continuación es un valor permitido, no una recomendación universal. Las tablas más grandes consumen memoria. La expiración de afinidad y el estado de conexión son independientes del hash.

El despacho DSR puede usar opciones IP de routing nativo, Geneve en configuraciones documentadas de nativo/overlay Geneve, o la ruta IPIP/IP6IP6 documentada solo para nativo. El overlay VXLAN no es intercambiable con el despacho DSR de Geneve. IPIP tiene sus propias restricciones de puerto/traducción; verifica la guía de la versión antes de seleccionarlo.

La aceleración XDP necesita dispositivos/drivers compatibles. `native` espera que los dispositivos seleccionados la admitan; `best-effort` la habilita donde sea compatible. No se habilita simplemente escribiendo la clave anterior `enable-xdp-acceleration`, y el reenvío XDP temprano puede no ser visible en el punto de captura posterior de tcpdump.

### Cilium y kube-proxy

| Aspecto | Comparación correcta |
|---|---|
| Implementación Linux de Service | Cilium usa hooks/mapas BPF; kube-proxy tiene modos iptables y nftables, además de IPVS obsoleto desde Kubernetes 1.35 |
| Plataforma | Se aplican los requisitos de Linux/kernel declarados por Cilium; kube-proxy de kernelspace de Windows es una implementación diferente |
| Estado de conexión | El estado BPF de conexión/NAT de Cilium es distinto de conntrack de netfilter Linux; “opcional frente a siempre” es demasiado amplio |
| L7 | Cilium integra proxies compatibles; el reenvío de Service de kube-proxy no es un motor de políticas HTTP |
| Rendimiento | Mide el mismo workload y configuración; ningún nombre de producto establece una clasificación fija |

No infieras una configuración DSR de kube-proxy simplemente porque el subsistema Linux IPVS subyacente tiene capacidades de routing directo.

## Laboratorio DSR/Maglev preparado

Este perfil es para un clúster de pruebas nuevo, preparado y sin kube-proxy con **IPv4 Geneve-overlay**. No migra un CNI existente, elimina kube-proxy ni configura controles de anti-spoofing/routing en la nube. Usa un CIDR de Pod sin conflictos y valida la ruta de retorno externa.

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


Proporciona el endpoint real de API y una semilla Maglev persistente por clúster. La semilla es una codificación base64 de 12 bytes aleatorios; genérala una vez, almacénala con los valores del clúster y reutilízala, en vez de regenerarla en cada actualización.

```bash
: "${API_SERVER_HOST:?Set the reachable real API server host, not its ClusterIP}"
: "${API_SERVER_PORT:?Set the actual API server port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.2 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

Usa el namespace creado por esta guía en el clúster seleccionado; si este es un clúster desechable diferente, repite primero allí los pasos de creación/etiquetado del namespace. La aplicación de política HTTP y este backend de LB externo usan etiquetas diferentes, por lo que la regla HTTP anterior solo para cliente no bloquea accidentalmente este experimento.

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

Usa un nodo de entrada accesible **diferente del nodo de backend**, y un cliente externo no sujeto al socket LB dentro del clúster de Cilium. Desde ese cliente, solicita `http://ENTRY_NODE_IP:NODEPORT/` usando los valores reales. Un curl de Pod a ClusterIP no prueba ni el comportamiento DSR externo ni el de Maglev. Verifica las rutas de solicitud/respuesta y el estado de backend/conexión; no los infieras solo de una respuesta HTTP correcta.

## Enmascaramiento

El enmascaramiento de salida de Pod cambia una dirección de origen cuando es necesario para la ruta externa configurada. No es cifrado ni un firewall, y es distinto del DNAT de Service y del reenvío DSR.

El siguiente fragmento excluye el rango de destino de ejemplo `10.0.0.0/8` del enmascaramiento de origen **solo cuando la red realmente admite esas rutas de origen/retorno de Pod**:

**`masquerade-values.yaml`**

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```


`ipv4NativeRoutingCIDR` expresa el rango enrutable asumido y la exclusión de enmascaramiento correspondiente. No instala rutas ni cambia todo el datapath a routing nativo. Una exclusión amplia sin rutas de retorno funcionales puede interrumpir la conectividad.

- El enmascaramiento BPF depende de la funcionalidad BPF NodePort en esta versión y solo se aplica en dispositivos que llevan el programa BPF. Inspecciona los dispositivos seleccionados; usa la configuración `devices` documentada cuando sea necesario.
- La implementación de iptables usa el comportamiento `egressMasqueradeInterfaces` documentado. No trates ese campo ni los ejemplos eliminados de `masquerade-interfaces`/`masquerade-all` como controles BPF universales.
- El enmascaramiento BPF de IPv6 está documentado como beta. Ninguna implementación elimina los requisitos de plataforma/kernel de Cilium, y ambas procesan en última instancia el tráfico en el kernel.
- Las excepciones de dirección de nodo, las exclusiones de ip-masq-agent y los gateways de nube/NAT posteriores pueden afectar el origen observado. Usa un observador controlado junto con estado/capturas del lado del nodo; alcanzar un sitio público arbitrario no prueba una implementación NAT concreta.

En el agente correspondiente:

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
```

## Manejo de fragmentos y MTU

El rastreador de fragmentos publicado almacena la identidad de datagramas y los puertos L4 de origen/destino en mapas LRU acotados. Puede recuperar el contexto de puerto para fragmentos posteriores que carecen de un encabezado L4; **no es un motor BPF de reensamblado de payload** ni una garantía frente a ataques de fragmentos.

La funcionalidad documentada incluye rastreo IPv4 e IPv6, habilitado de forma predeterminada mediante las flags correspondientes, y está marcada como beta. La flag IPv4 válida sigue siendo `enable-ipv4-fragment-tracking`. `bpf-fragments-map-max` controla la capacidad del mapa de datagramas rastreados; las configuraciones anteriores `fragment-tracking-timeout` y `max-fragments-per-flow` no forman parte del contrato de configuración publicado.

Un ejemplo explícito que usa el mapa de configuración adicional del chart:

**`fragment-values.yaml`**

```yaml
extraConfig:
  enable-ipv4-fragment-tracking: 'true'
  bpf-fragments-map-max: '8192'
```


8192 es un ejemplo de capacidad, no un número máximo de fragmentos por flujo. Inspecciona `cilium_ipv4_frag_datagrams` / `cilium_ipv6_frag_datagrams` y su presión al diagnosticar la capacidad; la presión no es un contador de éxito de reensamblado ni de prevención de ataques.

Prefiere un tamaño de paquete correcto y una ruta de descubrimiento de MTU de ruta funcional. PMTUD depende de la señalización de errores pertinente y del comportamiento de la red; no garantiza un tamaño óptimo automático en todas partes. El `MTU` de Cilium es la **anulación de red subyacente**. Como se explica en la [guía de networking](03-networking.md), la sobrecarga ordinaria de VXLAN es de 50 bytes para el underlay IPv4 y de 70 para IPv6; establecer ciegamente la base en 1450 para una ruta de 1500 bytes puede restar la sobrecarga dos veces.

## Observabilidad y solución de problemas

Inspecciona el nodo correcto, el modo de despliegue real de Envoy, la política deseada, el estado realizado del endpoint y el tráfico reciente. Usa `cilium-dbg` para operaciones locales del agente y el CLI independiente para operaciones del clúster. Los comandos eliminados `policy trace` y la regeneración forzada de endpoints no son el punto de partida para este diagnóstico.

Mantén en ejecución en otra terminal un port-forward de Hubble Relay habilitado y luego observa los flujos relevantes:

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

El rechazo de política HTTP puede aparecer como HTTP 403 en lugar de un veredicto de paquete DROPPED. Un timeout por sí solo también puede significar problemas de disponibilidad, DNS, routing, TLS u observación. Correlaciona las capas en lugar de interpretar cada error como éxito de la política.

## Límites de validación y fuentes

Estos son ejemplos comprobados respecto de fuentes/esquemas de la versión con fixtures locales acotados, no una plataforma probada en producción ni un benchmark de clúster en vivo. La ejecución de imágenes, la accesibilidad del webhook, el tráfico mTLS, las rutas de retorno DSR, el comportamiento NAT y la fragmentación aún requieren validación en el entorno preparado. Limpia únicamente los recursos de aplicación etiquetados de esta ejecución; no elimines el CNI del clúster como limpieza del laboratorio.

- [Reemplazo de kube-proxy/DSR/Maglev de Cilium](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/kubeproxy-free.rst), [enmascaramiento](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/masquerading.rst), [manejo de fragmentos](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/fragmentation.rst), [implementación de mapa de fragmentos](https://github.com/cilium/cilium/blob/v1.20.2/pkg/maps/fragmap/fragmap.go)
- [Anuncios L2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/l2-announcements.rst), [multicast](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/multicast.rst), [traductor de reglas HTTP](https://github.com/cilium/cilium/blob/v1.20.2/pkg/envoy/policy/envoy_l7_rules_translator.go), [valores predeterminados del chart Envoy](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/templates/_helpers.tpl)
- [Integración Cilium/Istio](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/servicemesh/istio.rst), [modos CNI/init-container de Istio](https://istio.io/latest/docs/setup/additional-setup/cni/), [requisitos de webhook](https://istio.io/latest/docs/ops/configuration/mesh/webhook/), [esquemas de Istio 1.31](https://github.com/istio/istio/blob/1.31.0/manifests/charts/base/files/crd-all.gen.yaml)
- [Modos de proxy/afinidad de Service de Kubernetes](https://kubernetes.io/docs/reference/networking/virtual-ips/), [valores de Cilium 1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)


[Volver a la página principal](README.md)

## Cuestionario

[Revisa las preguntas de L2–L7 y balanceo de carga](../../quizzes/networking/cilium/05-l2-l7-networking-quiz.md).
