# IPAM y políticas de red

> **Base de revisión**: Cilium 1.20.2; Kubernetes 1.33–1.36 probado. Las versiones de las API de recursos y los requisitos de plataforma se verifican por separado.
> **Última actualización**: October 15, 2026

## Configuración del entorno de laboratorio

Use los [perfiles de instalación](README.md) y los [requisitos previos de red](03-networking.md) para preparar un clúster Linux desechable. Mantenga kubectl dentro de la diferencia de versiones compatible con el servidor de API. Los perfiles de IPAM siguientes son alternativas para la instalación o una migración documentada, no interruptores de ConfigMap para aplicar secuencialmente a un clúster en ejecución.

El laboratorio de políticas usa su propio espacio de nombres y las cargas de trabajo coincidentes que se muestran a continuación, sustituyendo el manifiesto antiguo de Star Wars de Cilium 1.14 cuyas etiquetas no coincidían con estas políticas. Inspeccione primero la configuración existente de políticas de todo el clúster de Kubernetes/Cilium y de admisión; un nuevo espacio de nombres no las anula.

```bash
cilium status --wait
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl get ciliumnodeconfigs --all-namespaces -o yaml
helm -n kube-system get values cilium --all
```

Use el nombre real del espacio de nombres/release si es distinto. Los valores deseados de Helm y ConfigMaps, las anulaciones de nodos, la configuración del Operator y el estado realizado del agente responden a preguntas diferentes. Un resultado de grep que contenga `ipam` no es una comprobación completa de la configuración efectiva.

## Estrategias de administración de direcciones IP

El IPAM de Pod de Cilium asigna direcciones de cargas de trabajo. Kubernetes asigna los **ClusterIPs** de Service; el **LoadBalancer IPAM** de Cilium es una funcionalidad independiente para direcciones de LoadBalancer. Un `CiliumPodIPPool` no asigna ClusterIPs de Service.

### Asignadores y estado autoritativo

| Configuración | ¿Quién asigna la capacidad del nodo / IP de Pod? | Estado que se debe inspeccionar |
|---|---|---|
| `cluster-pool` (valor predeterminado genérico) | Cilium Operator asigna CIDR por nodo; cada agente asigna direcciones locales | `CiliumNode.spec.ipam.podCIDRs` y el estado del Operator |
| `kubernetes` / ámbito de host | Kubernetes proporciona PodCIDRs de nodo; cada agente asigna dentro de ellos | `Node.spec.podCIDRs` / `spec.podCIDR` de Kubernetes y las anotaciones compatibles del proveedor |
| `multi-pool` | Operator asigna bloques de pools con nombre en respuesta a la demanda del agente; el agente asigna IP de Pod | `CiliumPodIPPool`, `CiliumNode.spec.ipam.pools.requested` / `allocated` |
| `crd` | Un asignador externo proporciona direcciones disponibles; el agente las consume/libera | `CiliumNode.spec.ipam.pool` / `status.ipam.used` (y los campos IPv6 aplicables) |
| `eni` | Operator administra ENI/IP/prefijos de AWS; el agente traduce el estado de la interfaz en su asignador multi-pool | `CiliumNode.status.eni.enis` y el estado de pool/demanda específico del modo |
| `azure` | Integración upstream de Operator/agente para clústeres Azure VM/VMSS autoadministrados | Estado de asignación de Azure/CiliumNode |
| `delegated-plugin` | Cilium CNI invoca otro plugin IPAM, como Azure IPAM de AKS administrado | Estado del proveedor/plugin; no sustituya la configuración upstream de Azure IPAM |
| Integración de GKE | La integración upstream de GKE usa IPAM `kubernetes` de ámbito de host; el Dataplane V2 administrado tiene su propia propiedad | Configuración del proveedor y CIDR de Node; no es un valor de IPAM `gke` independiente |

Tanto cluster-pool como el ámbito de host de Kubernetes asignan direcciones individuales de Pod localmente. La diferencia es quién asigna los **prefijos de nodo**. Ninguno elimina la coordinación ni garantiza que un pool proporcionado por el usuario no pueda solaparse con una VPC, una red de nodos, un rango de Service u otro clúster.

Las definiciones de CRD/tipos publicadas usan `pool` y `used` para la asignación genérica respaldada por CRD. Parte de la documentación explicativa aún indica `available`/`inuse`; use el esquema instalado y los campos específicos del modo en lugar de copiar esos nombres antiguos. ENI en 1.20.2 usa la ruta de interfaz/multi-pool, por lo que los campos genéricos respaldados por CRD no son su fuente de verdad universal.

### Integración de Kubernetes/CNI

El kubelet solicita operaciones de sandbox de Pod mediante el runtime de contenedores; un runtime compatible con CNI invoca el plugin CNI de Cilium. La asignación depende del backend seleccionado, tras lo cual el plugin/agente configura la red del endpoint. En modo de ámbito de host, Kubernetes debe proporcionar los CIDR de familia de direcciones requeridos, por ejemplo mediante un asignador de CIDR de nodo correctamente configurado.

## Configuración de IPAM

Estos son **fragmentos de valores de Helm** para fusionar con el perfil de instalación correspondiente. Revise primero los rangos de direcciones de Pod/Service/nodo/externas.

### Pool de clúster

**`cluster-pool-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
ipv4:
  enabled: true
ipv6:
  enabled: false
```


El Operator coordina bloques de nodos, no una solicitud central para cada dirección de Pod. Varios CIDR en `clusterPoolIPv4PodCIDRList` amplían el espacio de asignación común; esto es diferente de seleccionar pools con nombre por carga de trabajo.

No sustituya entradas de la lista de pools existentes para ampliar un clúster activo. Agregue un CIDR sin conflictos mediante el procedimiento de expansión documentado. El tamaño de máscara de nodo no es una configuración mutable rutinaria. Los recuentos de direcciones por bloque no son idénticos a la capacidad utilizable de Pod porque las direcciones se reservan o usan por componentes locales del nodo.

Para un clúster ya preparado para doble pila de Kubernetes/Cilium:

**`dual-stack-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList:
    - fd00:10:244::/104
    clusterPoolIPv6MaskSize: 120
ipv4:
  enabled: true
ipv6:
  enabled: true
```


Habilitar estas dos marcas de familias de direcciones de Cilium no configura por sí solo los CIDR de Service de Kubernetes, la conectividad IPv6 subyacente ni la compatibilidad de la nube.

### Multi-Pool y CiliumPodIPPool

El modo documentado es `multi-pool`; la API de recursos sigue siendo `cilium.io/v2alpha1` en 1.20 (en la **[preversión 1.21]** `CiliumPodIPPool` se sirve como `cilium.io/v2`, que pasa a ser la versión de almacenamiento, `v2alpha1` queda en desuso y `spec.ipv4.pool`/`spec.ipv6.pool` añaden `reservedRanges` por CIDR; esos campos existen solo en `v2`). No infiera la madurez de una funcionalidad únicamente a partir de ese sufijo de API. El tutorial upstream de multi-pool también requiere `kubeProxyReplacement=true` y `bpf.masquerade=true` (el enmascaramiento de iptables necesitaría `egressMasqueradeInterfaces`); el ejemplo siguiente los incluye. Para los detalles internos de asignación, el dimensionamiento de pools y la migración, consulte [análisis detallado de IPAM](10-ipam-deep-dive.md). En un clúster nuevo que use este modo, proporcione un pool predeterminado para las asignaciones ordinarias:

**`multi-pool-values.yaml`**

```yaml
kubeProxyReplacement: true
bpf:
  masquerade: true
ipam:
  mode: multi-pool
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4:
          cidrs:
          - 10.244.0.0/16
          maskSize: 24
```


Este pool con nombre adicional usa los campos actuales `cidrs` y `maskSize`:

**`blue-pool.yaml`**

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumPodIPPool
metadata:
  name: blue-pool
spec:
  ipv4:
    cidrs:
    - 10.245.0.0/16
    maskSize: 24
  namespaceSelector:
    matchLabels:
      ipam-pool: blue
  podSelector:
    matchLabels:
      role: blue
```


El recurso de pool tiene ámbito de clúster. `podSelector` y `namespaceSelector` son campos independientes, y ambos deben coincidir cuando los dos están configurados. El antiguo ejemplo de `ipv4.cidr`, `blockSize` y `selector` genérico no era válido.

Para el ejemplo de selectores:

**`blue-namespace.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ipam-selection-demo
  labels:
    ipam-pool: blue
  annotations:
    ipam.cilium.io/require-pool-match: 'true'
```


**`blue-pod.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: blue-client
  namespace: ipam-selection-demo
  labels:
    role: blue
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


Aplique estos solo en una instalación multi-pool preparada. La anotación `require-pool-match` del espacio de nombres evita el respaldo automático al pool predeterminado cuando se requiere una coincidencia de selector no predeterminada.

La elección de pool sigue las anotaciones explícitas `ipam.cilium.io/ip-pool` de Pod/espacio de nombres o las de pool de familia de direcciones, después los selectores automáticos y, finalmente, el pool predeterminado. La selección automática debe coincidir exactamente con un pool para la familia de direcciones; los selectores solapados provocan un error de asignación. Las anotaciones de pool afectan a las **nuevas asignaciones**, no a las IP de Pod ya en ejecución. Los valores predeterminados específicos de nodo también se pueden configurar mediante `CiliumNodeConfig`.

La selección de pool no sustituye la autorización de red: controle quién puede cambiar las etiquetas/anotaciones de las cargas de trabajo y aplique la política de tráfico por separado. Los pools no deben tener CIDR solapados. Los rangos/pools en uso no se deben eliminar a la ligera; `maskSize`, `allowFirstIP` y `allowLastIP` son inmutables. La reserva de la primera/última dirección tiene excepciones documentadas para prefijos pequeños.

Existe una migración en línea documentada actualmente de **cluster-pool a multi-pool**. Esto no autoriza cambios de IPAM arbitrarios en vivo ni una migración inversa no planificada. Siga sus requisitos previos y comprobaciones de carga de trabajo/capacidad; este capítulo no ejecuta ninguna migración.

### AWS ENI

Use el perfil completo de instalación de EKS/ENI para enrutamiento, IAM de Operator, capacidad de subred/instancia y preparación de nodos. El siguiente fragmento ilustra las claves actuales, incluida la delegación opcional de prefijo IPv4:

**`eni-values-fragment.yaml`**

```yaml
ipam:
  mode: eni
eni:
  enabled: true
  eniTags:
    team: platform
  awsEnablePrefixDelegation: true
ipv4:
  enabled: true
ipv6:
  enabled: false
```

`eni.enabled=true` ya hace que el gráfico establezca de forma predeterminada `routingMode` en `native` y habilite rutas de endpoint, por lo que esas claves se omiten aquí (plantilla Helm `cilium-configmap.yaml` en 1.20.2).


`eni.awsEnablePrefixDelegation` requiere que la configuración de instancia/subred admita los prefijos solicitados. Un IPv4 `/28` contiene 16 direcciones, no la garantía de 16 Pod adicionales planificables en cada configuración. El valor predeterminado está deshabilitado. No agregue la clave inventada `eni-prefix-delegation-enabled`.

El Operator realiza las llamadas a la API de EC2; la preasignación reduce las demoras por Pod, pero no puede eliminar el agotamiento de cuotas, API o subred. `eni.eniTags` etiqueta las interfaces administradas. Permita que el SDK resuelva el endpoint de EC2 adecuado a menos que exista una anulación deliberada y validada de `eni.ec2APIEndpoint`.

Este ejemplo es IPv4. La referencia de ENI documenta IPv6 como beta con un comportamiento diferente de prefijos/asignación; la validación de la plataforma es independiente de habilitar `ipv6.enabled`. El encadenamiento de AWS VPC CNI mantiene la propiedad de direcciones con AWS VPC CNI. EC2 ordinario, Hybrid Nodes, Fargate y Auto Mode tienen límites distintos de instalación/compatibilidad; Fargate y Auto Mode no pueden usar este perfil de reemplazo.

<span id="querying-per-node-podcidrs-via-ciliumnode-cr"></span>


## Consulta del estado de asignación por nodo

### Ejemplo de CiliumNode

Esta es una **forma de objeto ilustrativa de solo lectura**, no un manifiesto para aplicar sobre el estado administrado por Operator:

**`ciliumnode-example.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNode
metadata:
  name: hybrid-node-001
spec:
  addresses:
  - ip: 10.85.0.1
    type: CiliumInternalIP
  - ip: 10.80.1.10
    type: InternalIP
  ipam:
    podCIDRs:
    - 10.85.0.0/25
```


La primera dirección puede ser `CiliumInternalIP`, no la `InternalIP` del nodo subyacente. Pueden existir varias InternalIP/familias de direcciones y varias entradas de asignación. Incluso una InternalIP tipada solo es una candidata para un diseño de red, no un siguiente salto automáticamente válido desde cada router.

### Inventario específico del modo

Guarde esta consulta como `ciliumnode-inventory.jq`:

**`ciliumnode-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.spec.addresses[]? |
    select(.type == "InternalIP") | .ip] | unique),
  clusterPoolPodCIDRs: (.spec.ipam.podCIDRs // []),
  multiPoolAllocations: (.spec.ipam.pools.allocated // []),
  eniInterfaceIDs: ((.status.eni.enis // {}) | keys),
  operatorStatus: (.status.ipam["operator-status"] // {})
}
```


```bash
kubectl get ciliumnodes -o json | jq -f ciliumnode-inventory.jq
```

Un campo ausente/vacío puede ser normal para un modo de IPAM diferente. Para el ámbito de host de Kubernetes, inspeccione el Node de Kubernetes en su lugar:

**`kubernetes-node-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.status.addresses[]? |
    select(.type == "InternalIP") | .address] | unique),
  podCIDRs: (.spec.podCIDRs // []),
  legacyPodCIDR: (.spec.podCIDR // null)
}
```


```bash
kubectl get nodes -o json | jq -f kubernetes-node-inventory.jq
```

Estas consultas conservan todas las direcciones/CIDR relevantes en lugar de seleccionar silenciosamente `[0]`. Generan inventario, no comandos `ip route add`. Seleccione interfaces/siguientes saltos y verifique las rutas de reenvío/retorno mediante el procedimiento de enrutamiento de la red. No suponga que cada CIDR debe instalarse mediante la primera dirección en un router no relacionado.

El inventario puede servir de base para la [planificación de red de EKS Hybrid Nodes](../../eks-hybrid-nodes/02-network-configuration.md), pero no sustituye las comprobaciones de enrutamiento y accesibilidad de ese entorno.

## Diseño e implementación de políticas de red

### Semántica de recursos y reglas

- Un `CiliumNetworkPolicy` con ámbito de espacio de nombres selecciona endpoints en su espacio de nombres; `CiliumClusterwideNetworkPolicy` proporciona ámbito de todo el clúster. El `nodeSelector` de firewall de host solo se admite en el segundo, con el firewall de host configurado.
- `endpointSelector` identifica sujetos; ingress/egress describen el tráfico relativo a ellos. `spec.labels` de reglas de Cilium almacena identificación/metadatos opcionales, no referencias que hereden otra política. `metadata.labels` de Kubernetes etiqueta el propio recurso.
- El tráfico permitido por las políticas aplicables se combina; las reglas explícitas de denegación tienen la precedencia documentada. Otra autorización L4 sin restricciones puede omitir una autorización L7 solapada con restricciones.
- La denegación predeterminada es específica de la dirección. Conserve deliberadamente las rutas requeridas de DNS/aplicación e inspeccione la política realizada junto con los flujos reales. Simplemente deshabilitar la denegación predeterminada no es un modo universal de prueba en seco de L7.

### Laboratorio de políticas coincidentes

Ejecute estos pasos en una shell en el clúster desechable:

```bash
set -euo pipefail
kubectl create namespace cilium-ipam-policy-demo
kubectl label namespace cilium-ipam-policy-demo docs-audit-lab=cilium-ipam-policy-04
```

Deténgase si el espacio de nombres ya existe y elija un nombre nuevo de forma coherente. Estas cargas de trabajo usan las imágenes de prueba de la CLI oficial y las etiquetas usadas por las políticas:

**`policy-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: cilium-ipam-policy-demo
  labels:
    app: frontend
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
  namespace: cilium-ipam-policy-demo
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
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
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
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-ipam-policy-demo
  labels:
    app: client
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


```bash
kubectl apply -f policy-app.yaml
kubectl -n cilium-ipam-policy-demo wait --for=condition=Ready \
  pod/frontend pod/outsider pod/client --timeout=120s
kubectl -n cilium-ipam-policy-demo rollout status deployment/backend --timeout=120s
kubectl -n cilium-ipam-policy-demo get pods -o wide --show-labels
BACKEND_IP=$(kubectl -n cilium-ipam-policy-demo get service backend -o jsonpath='{.spec.clusterIP}')
test -n "$BACKEND_IP"
kubectl -n cilium-ipam-policy-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 "http://$BACKEND_IP:8080/"
```

Primero confirme también la conectividad de referencia desde outsider. La antiafinidad de backend requiere otro nodo apto. La regla de base de datos siguiente ilustra una dependencia adicional de aplicación; este laboratorio no implementa ni valida un servidor de base de datos.

### Política L3/L4

**`backend-l4.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


Aplique `backend-l4.yaml`, espere a la realización de la política en el agente de backend y compruebe solicitudes nuevas. Frontend debe conservar el acceso; la denegación de outsider requiere evidencia de flujo, no solo una salida de curl distinta de cero.

### Política HTTP L7

Esta es una **definición alternativa del mismo recurso `backend-access`**, no una segunda política de autorización solapada. Al aplicarla se sustituye la versión L4 de este laboratorio; aun así, inspeccione otras políticas aplicables.

**`backend-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/$
          headerMatches:
          - name: content-type
            value: application/json
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


```bash
kubectl apply -f backend-http.yaml
kubectl -n cilium-ipam-policy-demo get cnp backend-access -o yaml
```

Después de la realización, la política permite GET `/`, y POST `/` solo con el valor exacto `content-type: application/json`. Una solicitud a otra ruta/método debe ser denegada por el proxy. La aplicación debe implementar por sí misma una operación permitida; el permiso de la política no garantiza que la aplicación tenga éxito. La ruta de preparación conocida del servidor de demostración es GET `/`.

Los campos de método/ruta HTTP son expresiones regulares. Mantenga los ejemplos anclados y escape los metacaracteres al adaptarlos. Las reglas HTTP/gRPC requieren Envoy y tráfico de aplicación visible; la terminación/intercepción de TLS se debe configurar cuando sea necesaria. La información de servicio/método gRPC se transporta en la ruta HTTP/2 y los metadatos en los encabezados, no en un campo `rules.grpc` independiente ni mediante filtrado arbitrario de la carga útil protobuf.

### Límite de la política Kafka

Cilium actual no proporciona la API eliminada `rules.kafka`. No aplique el YAML antiguo de topic/clave de API/ID de cliente. Use reglas de conectividad L4 adecuadas para el **puerto real de listener** del broker y configure en el broker la autenticación/autorización, como el acceso a topics. NetworkPolicy no sustituye la autorización del broker ni habilita el cifrado.

### Política DNS/FQDN

Este ejemplo presupone que el resolvedor seleccionado es un Pod CoreDNS/kube-dns en `kube-system` en TCP/UDP 53. Inspeccione primero el resolvedor real del Pod; las rutas DNS de NodeLocal, OpenShift y administradas necesitan su propia configuración coincidente.

**`dns-egress.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-egress
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```


La regla DNS L7 redirige el tráfico coincidente del resolvedor a través del proxy DNS de Cilium para que pueda aprender respuestas de nombre a IP. Permitir solo el puerto 53 no proporciona esa observación. `matchPattern: "*"` permite consultas DNS al resolvedor seleccionado; el egress HTTPS se limita por separado a las IP aprendidas para los nombres `toFQDNs`. Sustituya `api.example.com` por un nombre de prueba resoluble y controlado antes de afirmar que una prueba externa tuvo éxito.

`*.googleapis.com` coincide con una etiqueta bajo ese sufijo; no coincide con el ápice ni con varias etiquetas. En esta versión, `**.googleapis.com` puede coincidir con uno o más niveles de subdominio, excluyendo aún el ápice. El estado de TTL/caché DNS y las búsquedas nuevas importan. La autorización de nombre a IP no es una comprobación de autorización de hostname HTTP, URL o usuario de aplicación.

El proxy DNS predeterminado se ejecuta en el agente; un proxy DNS independiente separado se documenta como alfa. La política DNS no requiere Envoy universalmente. Para OpenShift, el ejemplo oficial usa la configuración de resolvedor `openshift-dns` y el puerto 5353 en lugar de copiar esta regla a ciegas.

### CIDR, Services y entidades

| Regla | Límite |
|---|---|
| `toCIDR` / `toCIDRSet` | Selecciona prefijos IP, principalmente pares externos. De forma predeterminada no sustituyen selectores de Pods/nodos administrados por Cilium; la coincidencia CIDR documentada de participación voluntaria para `pods`/`nodes` es beta y consume identidades |
| `toServices` | Resuelve selectores de Service o direcciones de EndpointSlice sin selector en selectores de política; no crea un Service ni enruta. Los casos sin selector heredan las limitaciones del modo CIDR |
| `world` | Categoría amplia de identidad fuera del clúster, no solo «Internet público» ni un selector de clúster remoto con nombre |
| `cluster` / `cluster-mesh` | `cluster` cubre endpoints del clúster local más las entidades reservadas/nodos remotos documentados; `cluster-mesh` además selecciona endpoints de clústeres en malla |
| `all` | Combinación amplia que incluye clúster/malla y pares externos; no es un atajo de privilegio mínimo |

Para el acceso al servidor de API, use el comportamiento documentado de la entidad `kube-apiserver` en lugar de suponer que `toServices: default/kubernetes` tiene la semántica ordinaria de selector de cargas de trabajo.

## Escenarios multiclúster

Cluster Mesh comparte estado y mantiene separados los clústeres Kubernetes y los espacios de nombres de red. Los nodos remotos no se convierten en objetos Node de Kubernetes locales, y los recursos de política no se distribuyen automáticamente.

```text
State:  cluster A Cluster Mesh control plane <-- mTLS --> cluster B control plane
Data:   Pod A --> node A datapath --> reachable network --> node B datapath --> Pod B
```

El servidor de API de Cluster Mesh sincroniza el estado; los paquetes de Pod no necesitan pasar por él. El mTLS del plano de control no cifra por sí solo el tráfico de Pod a Pod.

### Requisitos previos de configuración y secuencia parcial

Prepare clústeres separados con CIDR de Pod no solapados, InternalIP de nodos accesibles, rutas de red permitidas, el mismo modo de datapath y versiones de Cilium dentro de la diferencia documentada de una versión menor. El enrutamiento nativo además necesita que todos los rangos remotos de Pod sean accesibles y estén cubiertos por el CIDR de enrutamiento nativo configurado. Asigne nombres/ID de Cilium únicos durante la instalación (por ejemplo, `cluster-a`/1 y `cluster-b`/2) y configure la confianza en los certificados de pares.

La siguiente es una secuencia parcial **después de** que se preparen esos requisitos previos y la ruta del plano de control NodePort privado. Los nombres de contexto de kubeconfig no tienen que ser iguales a los nombres de clúster de Cilium:

```bash
export CTX_A=prepared-context-a
export CTX_B=prepared-context-b
cilium clustermesh enable --context "$CTX_A" --service-type NodePort
cilium clustermesh enable --context "$CTX_B" --service-type NodePort
cilium clustermesh connect --context "$CTX_A" --destination-context "$CTX_B"
cilium clustermesh status --context "$CTX_A" --wait
cilium clustermesh status --context "$CTX_B" --wait
```

Esto no aprovisiona peering de VPC/VPN, rutas, firewalls, endpoints privados ni confianza de certificados. Siga la configuración completa específica de la plataforma; no cambie a la ligera el nombre/ID de un clúster activo.

### Services globales y política entre clústeres

Cree espacios de nombres coincidentes y cargas de trabajo backend reales en cada clúster preparado; luego use el **mismo nombre de Service y espacio de nombres** con puertos compatibles:

**`global-service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: global-service
  namespace: mesh-demo
  annotations:
    service.cilium.io/global: 'true'
spec:
  type: ClusterIP
  selector:
    app: global-app
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
```


`service.cilium.io/global` es la anotación actual. Un Service global comparte los backends locales de forma predeterminada; `service.cilium.io/shared: "false"` deja de compartirlos con pares sin impedir necesariamente que los clientes locales usen backends remotos. Los ClusterIPs locales no tienen que ser idénticos.

No prometa conmutación por error automática solo a partir de esta anotación. De forma predeterminada, se conserva el estado de clúster inaccesible (`clustermesh.cacheTTL: 0s`); un TTL positivo configurado puede revocar datos remotos obsoletos tras la desconexión del plano de control. Esto no es una sonda de estado de la aplicación ni una garantía de cero tiempo de inactividad.

Aplique esta política ingress en el espacio de nombres `mesh-demo` del clúster de destino cuando la carga de trabajo de origen nombrada exista en `cluster-a`:

**`cross-cluster-policy.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cluster-a-frontend
  namespace: mesh-demo
spec:
  endpointSelector:
    matchLabels:
      app: global-app
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: frontend-ns
        k8s:io.cilium.k8s.policy.cluster: cluster-a
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```


La etiqueta de clúster usa el **nombre de clúster de Cilium** configurado, no un contexto de kubeconfig. En Cilium actual, los selectores de endpoint usan de forma predeterminada el clúster local a menos que se seleccionen pares explícitamente. Instale las políticas requeridas de forma independiente en cada clúster y pruebe ambas direcciones de tráfico.

## Validación y limpieza

Los ejemplos se comprobaron con esquemas específicos de la versión, contratos de configuración/código fuente y fixtures locales acotados. Esta auditoría no afirma asignación de IP en vivo, aplicación de políticas de kernel, aprovisionamiento de nube, una base de datos en ejecución ni tráfico entre clústeres exitoso.

Inspeccione el estado deseado y realizado, verifique una línea base exitosa y luego correlacione las denegaciones esperadas con el flujo pertinente. Limpie solo las cargas de trabajo de políticas con ámbito de espacio de nombres de esta ejecución después de verificar la propiedad. Para el ejercicio multi-pool independiente, libere las cargas de trabajo y verifique que las asignaciones de pool ya no estén en uso antes de considerar eliminar el pool; nunca elimine el estado activo de CiliumNode/pool como atajo.

## Fuentes

- [Modos/migración de IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/index.rst), [pool de clúster](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool.rst), [ámbito de host](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/kubernetes.rst), [multi-pool](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/multi-pool.rst), [procedimiento de migración](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst)
- [Esquema de PodIPPool](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/client/crds/v2alpha1/ciliumpodippools.yaml), [esquema de CiliumNode](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnodes.yaml), [ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst), [valores de Helm](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml), [límites de EKS CNI](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [API de reglas de políticas](https://github.com/cilium/cilium/blob/v1.20.2/pkg/policy/api/rule.go), [reglas L3](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/policy/layer3.rst), [reglas L7](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/policy/layer7.rst), [políticas DNS](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/dns.rst), [implementación de comodines](https://github.com/cilium/cilium/blob/v1.20.2/pkg/fqdn/matchpattern/matchpattern.go)
- [Configuración de Cluster Mesh](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/setup.rst), [arquitectura](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/intro.rst), [Services globales](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/global-services.rst), [política entre clústeres](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/policy.rst)


[Volver a la página principal](README.md)

## Cuestionario

[Compruebe sus conocimientos de IPAM y políticas](../../quizzes/networking/cilium/04-ipam-policy-quiz.md).