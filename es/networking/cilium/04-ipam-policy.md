# IPAM y políticas de red

> **Base de revisión**: Cilium 1.20.3; probado con Kubernetes 1.33–1.36. Las versiones de API de los recursos y los requisitos de plataforma se comprueban por separado.
> **Última revisión**: 16 de octubre de 2026

## Preparación del entorno de laboratorio

Prepare un clúster Linux desechable con los [perfiles de instalación](README.md) y los [requisitos de red](03-networking.md). Mantenga kubectl dentro de la diferencia de versiones permitida respecto del servidor de API. Los perfiles de IPAM siguientes son alternativas de instalación o de una migración documentada; no son opciones de ConfigMap para aplicar una tras otra a un clúster en ejecución.

El laboratorio de políticas utiliza el namespace y las cargas coincidentes definidos más abajo. Sustituye al antiguo manifiesto Star Wars de Cilium 1.14, cuyas etiquetas no coincidían con estas políticas. Revise primero las políticas globales de Kubernetes y Cilium y la configuración de admisión existentes; crear un namespace no las anula.

```bash
cilium status --wait
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl get ciliumnodeconfigs --all-namespaces -o yaml
helm -n kube-system get values cilium --all
```

Si utiliza otros nombres de namespace o de instalación Helm, ajústelos. Los valores declarados de Helm, los ConfigMaps, las opciones específicas de nodo, la configuración del Operator y el estado aplicado por los agentes muestran aspectos distintos. Un resultado de grep que contenga `ipam` no basta para comprobar toda la configuración efectiva.

## Estrategias de gestión de direcciones IP

Pod IPAM de Cilium asigna direcciones a las cargas de trabajo. Kubernetes asigna las **ClusterIPs** de los Services. **LoadBalancer IPAM** de Cilium es una función independiente que asigna direcciones a balanceadores de carga. Un `CiliumPodIPPool` no asigna las ClusterIPs de los Services.

### Asignadores y estado de referencia

| Configuración | ¿Quién asigna la capacidad por nodo y las IP de los Pods? | Estado que debe consultarse |
|---|---|---|
| `cluster-pool` (predeterminado genérico) | Cilium Operator asigna CIDR por nodo y cada agente asigna direcciones locales | `CiliumNode.spec.ipam.podCIDRs` y estado del Operator |
| `kubernetes` / ámbito de host | Kubernetes proporciona los PodCIDR de los nodos y cada agente asigna direcciones dentro de ellos | `Node.spec.podCIDRs` / `spec.podCIDR` de Kubernetes y anotaciones compatibles del proveedor |
| `multi-pool` | El Operator asigna bloques de pools con nombre según la demanda del agente; el agente asigna las IP de los Pods | `CiliumPodIPPool`, `CiliumNode.spec.ipam.pools.requested` / `allocated` |
| `crd` | Un asignador externo proporciona direcciones disponibles; el agente las consume y libera | `CiliumNode.spec.ipam.pool` / `status.ipam.used` y los campos de IPv6 aplicables |
| `eni` | El Operator gestiona las ENI, IP y prefijos de AWS; el agente convierte el estado de las interfaces al de su asignador multi-pool | `CiliumNode.status.eni.enis` y estado de pools y demanda específico del modo |
| `azure` | Integración del Operator y del agente del proyecto original para clústeres autogestionados de Azure VM/VMSS | Estado de asignación de Azure y CiliumNode |
| `delegated-plugin` | Cilium CNI invoca otro plugin de IPAM, como Azure IPAM de AKS administrado | Estado del proveedor y del plugin; no lo sustituya por la configuración de Azure IPAM del proyecto original |
| Integración con GKE | La integración de GKE del proyecto original utiliza IPAM `kubernetes` de ámbito de host; Dataplane V2 administrado tiene su propia gestión | Configuración del proveedor y CIDR de los nodos; no existe un valor IPAM `gke` independiente |

Tanto cluster-pool como el ámbito de host de Kubernetes asignan localmente las direcciones individuales de los Pods. La diferencia está en quién asigna los **prefijos de los nodos**. Ninguno elimina la coordinación ni garantiza que un pool definido por el usuario no se solape con la VPC, la red de nodos, el rango de Services u otro clúster.

Las definiciones de CRD y tipos publicadas utilizan `pool` y `used` para la asignación genérica basada en CRD. Algunos documentos explicativos siguen usando `available`/`inuse`; consulte el esquema instalado y los campos de cada modo en vez de copiar esos nombres antiguos. ENI en 1.20.3 utiliza la ruta de interfaces y multi-pool, por lo que los campos genéricos basados en CRD no son su fuente universal de referencia.

### Integración de Kubernetes y CNI

El kubelet solicita las operaciones del sandbox del Pod al runtime de contenedores. Si admite CNI, el runtime invoca el plugin CNI de Cilium. La asignación depende del backend seleccionado; después, el plugin y el agente configuran la red del endpoint. En el modo de ámbito de host, Kubernetes debe proporcionar los CIDR de las familias de direcciones necesarias, por ejemplo mediante un asignador de CIDR de nodos correctamente configurado.

## Configuración de IPAM

Estos son **fragmentos de valores de Helm** que debe integrar en el perfil de instalación correspondiente. Revise primero los rangos de direcciones de Pods, Services, nodos y redes externas.

### Cluster Pool

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


El Operator coordina los bloques por nodo; no atiende una solicitud central por cada dirección de Pod. Añadir varios CIDR a `clusterPoolIPv4PodCIDRList` amplía el espacio común de asignación. Esto difiere de seleccionar pools con nombre para cada carga.

No sustituya las entradas existentes de la lista de pools para ampliar un clúster en ejecución. Añada un CIDR sin solapamientos mediante el procedimiento documentado de ampliación. El tamaño de máscara por nodo no es una opción que pueda cambiarse de forma rutinaria. El número de direcciones de un bloque no equivale a su capacidad útil de Pods, porque algunas se reservan o se utilizan en funciones locales del nodo.

Para un clúster que ya esté preparado para doble pila en Kubernetes y Cilium:

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


Activar estas dos opciones de familias de direcciones en Cilium no configura por sí solo los CIDR de Services de Kubernetes, la conectividad IPv6 de la red subyacente ni el soporte de la nube.

### Multi-Pool y CiliumPodIPPool

El modo documentado es `multi-pool`; en 1.20, la API del recurso sigue siendo `cilium.io/v2alpha1`. En la **[versión preliminar 1.21]**, `CiliumPodIPPool` se expone como `cilium.io/v2`, que pasa a ser la versión de almacenamiento; `v2alpha1` queda obsoleta y `spec.ipv4.pool`/`spec.ipv6.pool` incorporan `reservedRanges` por CIDR, campos disponibles solo en `v2`. No deduzca la madurez de una función únicamente por el sufijo de su API. El tutorial multi-pool del proyecto original también requiere `kubeProxyReplacement=true` y `bpf.masquerade=true`; con masquerade de iptables se necesitaría `egressMasqueradeInterfaces`. El ejemplo incluye esas opciones. Consulte los detalles de asignación, dimensionamiento y migración en [IPAM en detalle](10-ipam-deep-dive.md). En un clúster nuevo con este modo, cree un pool predeterminado para las asignaciones ordinarias:

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


Este pool adicional con nombre utiliza los campos actuales `cidrs` y `maskSize`:

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


El recurso de pool tiene ámbito de clúster. `podSelector` y `namespaceSelector` son campos independientes; cuando configura ambos, deben coincidir los dos. El antiguo ejemplo con `ipv4.cidr`, `blockSize` y un `selector` genérico no era válido.

Para el ejemplo de selección:

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


Aplique estos recursos solo en una instalación multi-pool preparada. La anotación `require-pool-match` del namespace impide recurrir automáticamente al pool predeterminado cuando se exige una coincidencia con un selector de otro pool.

La selección utiliza primero `ipam.cilium.io/ip-pool` o las anotaciones de pool por familia de direcciones del Pod o namespace; después utiliza los selectores automáticos y, finalmente, el pool predeterminado. La selección automática debe coincidir con exactamente un pool para esa familia. Si los selectores se solapan, la asignación falla. Las anotaciones de pool afectan a **las nuevas asignaciones**, no a las IP de Pods que ya están en ejecución. También puede definir pools predeterminados por nodo mediante `CiliumNodeConfig`.

Seleccionar un pool no sustituye la autorización de red. Controle quién puede cambiar etiquetas y anotaciones de las cargas y aplique las políticas de tráfico por separado. Los CIDR de los pools no deben solaparse. No retire rangos o pools en uso sin un procedimiento adecuado; `maskSize`, `allowFirstIP` y `allowLastIP` son inmutables. La reserva de la primera y la última dirección tiene excepciones documentadas para prefijos pequeños.

Existe un procedimiento documentado de migración en línea de **cluster-pool a multi-pool**. Esto no permite cambiar arbitrariamente el modo de IPAM en un clúster activo ni realizar una migración inversa sin planificación. Siga sus requisitos previos y compruebe las cargas y la capacidad. Este capítulo no ejecuta ninguna migración.

### AWS ENI

Utilice el perfil completo de instalación EKS/ENI para configurar el enrutamiento, IAM del Operator, la capacidad de subredes e instancias y la preparación de nodos. El fragmento siguiente muestra las claves actuales, incluida la delegación opcional de prefijos IPv4:

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

`eni.enabled=true` hace que el chart seleccione `routingMode` con valor `native` y habilite las rutas de endpoints por defecto. Por eso esas claves se omiten aquí (plantilla Helm `cilium-configmap.yaml` de 1.20.2).


`eni.awsEnablePrefixDelegation` requiere que las instancias y subredes admitan los prefijos solicitados. Un `/28` de IPv4 contiene 16 direcciones, pero no garantiza 16 Pods programables adicionales en cualquier configuración. La opción está deshabilitada por defecto. No añada la clave inexistente `eni-prefix-delegation-enabled`.

El Operator realiza las llamadas a la API de EC2. La preasignación reduce los retrasos por Pod, pero no elimina las cuotas, los errores de API ni el agotamiento de subredes. `eni.eniTags` añade etiquetas a las interfaces gestionadas. Deje que el SDK resuelva el endpoint adecuado de EC2, salvo que haya configurado deliberadamente una alternativa validada mediante `eni.ec2APIEndpoint`.

Este ejemplo utiliza IPv4. La referencia de ENI documenta IPv6 como Beta, con un comportamiento de prefijos y asignación diferente. Validar la plataforma requiere más que activar `ipv6.enabled`. En el modo de encadenamiento con AWS VPC CNI, AWS VPC CNI sigue gestionando las direcciones. EC2 convencional, Hybrid Nodes, Fargate y Auto Mode tienen distintos límites de instalación y soporte; Fargate y Auto Mode no pueden utilizar este perfil de sustitución.

<span id="querying-per-node-podcidrs-via-ciliumnode-cr"></span>


## Consultar el estado de asignación por nodo

### Ejemplo de CiliumNode

Este ejemplo muestra **la estructura orientativa de un objeto para consulta**, no un manifiesto que deba aplicar sobre el estado gestionado por el Operator:

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


La primera dirección puede ser `CiliumInternalIP`, no la `InternalIP` del nodo en la red subyacente. Puede haber varias InternalIPs, familias de direcciones y entradas de asignación. Incluso una dirección de tipo InternalIP es solo un posible siguiente salto que debe evaluar en el diseño de red; no es automáticamente válida desde cualquier router.

### Inventario específico de cada modo

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

Un campo ausente o vacío puede ser normal en otro modo de IPAM. Para el ámbito de host de Kubernetes, consulte el objeto Node de Kubernetes:

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

Estas consultas conservan todas las direcciones y CIDR relevantes, sin seleccionar silenciosamente `[0]`. Generan un inventario, no comandos `ip route add`. Seleccione interfaces y siguientes saltos y verifique las rutas de ida y vuelta mediante el procedimiento de enrutamiento de la red. No suponga que debe instalar cada CIDR a través de la primera dirección en un router ajeno.

El inventario puede ayudar a [planificar la red de EKS Hybrid Nodes](../../eks-hybrid-nodes/02-network-configuration.md), pero no sustituye las comprobaciones de enrutamiento y conectividad de ese entorno.

## Diseño e implementación de políticas de red

### Semántica de recursos y reglas

- Un `CiliumNetworkPolicy` selecciona endpoints de su namespace; `CiliumClusterwideNetworkPolicy` tiene ámbito de clúster. El `nodeSelector` del firewall de host solo se admite en este último, con el firewall de host configurado.
- `endpointSelector` identifica los endpoints a los que se aplica la política; ingress y egress describen el tráfico respecto de ellos. `spec.labels` de una regla de Cilium almacena identificación o metadatos opcionales; no contiene referencias para heredar otra política. `metadata.labels` de Kubernetes etiqueta el propio recurso.
- Se combinan los permisos de tráfico de las políticas aplicables, mientras que las reglas de denegación explícita tienen su precedencia documentada. Otra regla L4 sin restricciones puede permitir tráfico que una regla L7 coincidente restringe.
- La denegación predeterminada se aplica por dirección. Conserve expresamente las rutas de DNS y de aplicaciones necesarias y compruebe la política efectiva junto con los flujos reales. Desactivar la denegación predeterminada no ofrece un modo universal de prueba sin aplicación de políticas L7.

### Laboratorio con cargas y políticas coincidentes

Ejecute estos pasos en una misma sesión de shell en el clúster desechable:

```bash
set -euo pipefail
kubectl create namespace cilium-ipam-policy-demo
kubectl label namespace cilium-ipam-policy-demo docs-audit-lab=cilium-ipam-policy-04
```

Si el namespace ya existe, deténgase y elija otro nombre nuevo de forma coherente en todos los recursos. Estas cargas utilizan las imágenes de prueba de la CLI oficial y las etiquetas que seleccionan las políticas:

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

Compruebe primero la conectividad inicial también desde outsider. La antiafinidad del backend requiere otro nodo apto. La regla de base de datos siguiente muestra una dependencia adicional de la aplicación; el laboratorio no despliega ni valida un servidor de base de datos.

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


Aplique `backend-l4.yaml`, espere a que el agente del backend haya aplicado la política y pruebe solicitudes nuevas. Frontend debería conservar el acceso. Para demostrar que se deniega outsider, examine el flujo; no basta con que curl termine con un código distinto de cero.

### Política HTTP L7

Esta es **una definición alternativa del mismo recurso `backend-access`**, no una segunda política de permisos superpuesta. Aplicarla sustituye la versión L4 del laboratorio. Compruebe también las demás políticas aplicables.

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

Una vez aplicada, la política permite GET `/` y POST `/` solo con el valor exacto `content-type: application/json`. El proxy debería denegar las solicitudes con otros métodos o rutas. La aplicación debe implementar la operación permitida: un permiso de política no garantiza que la aplicación responda correctamente. La ruta de disponibilidad conocida del servidor de demostración es GET `/`.

Los campos de método y ruta HTTP son expresiones regulares. Mantenga los anclajes de los ejemplos y escape los metacaracteres al adaptarlos. Las reglas HTTP y gRPC requieren Envoy y tráfico de aplicación visible; configure la terminación o interceptación TLS si corresponde. El servicio y método de gRPC aparecen en la ruta HTTP/2, y los metadatos en los encabezados. No existe un campo independiente `rules.grpc` ni filtrado arbitrario del contenido protobuf.

### Límites de las políticas para Kafka

Cilium actual ya no ofrece la API retirada `rules.kafka`. No aplique el antiguo YAML de temas, claves de API e identificadores de cliente. Utilice reglas de conectividad L4 para el **puerto real de escucha** del broker y configure en este la autenticación y autorización, como el acceso a temas. NetworkPolicy no sustituye la autorización del broker ni habilita el cifrado.

### Política DNS/FQDN

Este ejemplo presupone que el resolver seleccionado es un Pod CoreDNS/kube-dns de `kube-system` en TCP/UDP 53. Compruebe primero el resolver real del Pod. NodeLocal DNS, OpenShift y las rutas de DNS administrado requieren configuraciones que coincidan con sus propios resolvers.

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


La regla L7 de DNS redirige el tráfico del resolver seleccionado a través del proxy DNS de Cilium, que aprende las respuestas de nombre a IP. Permitir únicamente el puerto 53 no proporciona esa observación. `matchPattern: "*"` permite consultas DNS al resolver seleccionado; los permisos de salida HTTPS se limitan por separado a las IP aprendidas para los nombres de `toFQDNs`. Sustituya `api.example.com` por un nombre de prueba controlado y resoluble antes de afirmar que la prueba externa ha funcionado.

`*.googleapis.com` coincide con un único nivel de subdominio; no coincide con el dominio raíz ni con varios niveles. En esta versión, `**.googleapis.com` puede coincidir con uno o varios niveles de subdominio, pero sigue excluyendo el dominio raíz. Importan el TTL, la caché de DNS y las consultas nuevas. Permitir las IP de un nombre no equivale a autorizar el hostname HTTP, la URL o al usuario de una aplicación.

Por defecto, el proxy DNS se ejecuta en el agente. El proxy DNS independiente se documenta como Alpha. Las políticas DNS no requieren Envoy en todos los casos. Para OpenShift, el ejemplo oficial utiliza el resolver de `openshift-dns` y el puerto 5353; no copie esta regla sin adaptarla.

### CIDR, Services y entidades

| Regla | Límite |
|---|---|
| `toCIDR` / `toCIDRSet` | Seleccionan prefijos IP, principalmente de pares externos. Por defecto, no sustituyen los selectores de Pods y nodos gestionados por Cilium; la selección opcional documentada de CIDR para `pods`/`nodes` está en Beta y consume identidades |
| `toServices` | Convierte los selectores de Service o las direcciones de EndpointSlice sin selector en selectores de política. No crea un Service ni una ruta; los casos sin selector heredan los límites del modo CIDR |
| `world` | Categoría amplia de identidades externas al clúster; no significa únicamente Internet público ni selecciona un clúster remoto concreto |
| `cluster` / `cluster-mesh` | `cluster` incluye endpoints del clúster local y las entidades reservadas y nodos remotos documentados; `cluster-mesh` selecciona además los endpoints de clústeres de la malla |
| `all` | Combinación amplia que incluye pares del clúster, de la malla y externos; no es un atajo al mínimo privilegio |

Para acceder al servidor de API, consulte el comportamiento documentado de la entidad `kube-apiserver`; no suponga que `toServices: default/kubernetes` funciona como un selector ordinario de cargas.

## Escenarios multiclúster

Cluster Mesh comparte estado mientras mantiene separados los clústeres de Kubernetes y sus namespaces de red. Los nodos remotos no se convierten en objetos Node locales de Kubernetes y las políticas no se distribuyen automáticamente.

```text
State:  cluster A Cluster Mesh control plane <-- mTLS --> cluster B control plane
Data:   Pod A --> node A datapath --> reachable network --> node B datapath --> Pod B
```

El servidor de API de Cluster Mesh sincroniza el estado; los paquetes de los Pods no tienen que atravesarlo. El mTLS del plano de control no cifra por sí solo el tráfico entre Pods.

### Requisitos previos y secuencia parcial de configuración

Prepare clústeres separados con CIDR de Pods sin solapamientos, InternalIPs de nodos accesibles, rutas de red permitidas, el mismo modo de datapath y versiones de Cilium con una diferencia máxima de una versión menor, según la documentación. El enrutamiento nativo también requiere que todos los rangos remotos de Pods sean accesibles y estén cubiertos por el CIDR de enrutamiento nativo configurado. Asigne nombres e ID únicos de Cilium durante la instalación, por ejemplo `cluster-a`/1 y `cluster-b`/2, y configure la confianza entre certificados.

La secuencia siguiente es parcial y comienza **después** de preparar esos requisitos y la ruta privada del plano de control por NodePort. Los nombres de los contextos de kubeconfig no tienen que coincidir con los nombres de clúster de Cilium:

```bash
export CTX_A=prepared-context-a
export CTX_B=prepared-context-b
cilium clustermesh enable --context "$CTX_A" --service-type NodePort
cilium clustermesh enable --context "$CTX_B" --service-type NodePort
cilium clustermesh connect --context "$CTX_A" --destination-context "$CTX_B"
cilium clustermesh status --context "$CTX_A" --wait
cilium clustermesh status --context "$CTX_B" --wait
```

Estos comandos no aprovisionan VPC peering, VPN, rutas, firewalls, endpoints privados ni confianza entre certificados. Siga el procedimiento completo de su plataforma; no cambie el nombre o el ID de un clúster activo sin planificación.

### Services globales y políticas entre clústeres

Cree namespaces coincidentes y cargas backend reales en cada clúster preparado; después utilice **el mismo nombre y namespace de Service** con puertos compatibles:

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


`service.cilium.io/global` es la anotación actual. Un Service global comparte los backends locales por defecto. `service.cilium.io/shared: "false"` deja de compartirlos con otros clústeres, pero no impide necesariamente que los clientes locales utilicen backends remotos. Las ClusterIPs locales no tienen que ser iguales.

Esta anotación no garantiza por sí sola la conmutación automática ante fallos. Por defecto, se conserva el estado de clústeres inaccesibles (`clustermesh.cacheTTL: 0s`). Un TTL positivo puede retirar los datos remotos obsoletos tras una desconexión del plano de control; no es una sonda de salud de la aplicación ni garantiza una operación sin interrupciones.

Aplique esta política de entrada en el namespace `mesh-demo` del clúster de destino cuando exista la carga de origen indicada en `cluster-a`:

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


La etiqueta de clúster utiliza **el nombre del clúster de Cilium** configurado, no un contexto de kubeconfig. En Cilium actual, los selectores de endpoint se limitan por defecto al clúster local, salvo que seleccione explícitamente otros clústeres. Instale las políticas necesarias de forma independiente en cada clúster y pruebe ambas direcciones de tráfico.

## Validación y retirada de recursos

Los ejemplos se comprobaron en la fuente mediante esquemas específicos de la versión, contratos de configuración y código, y casos de prueba locales acotados. Esa auditoría no acredita asignación real de IP, aplicación de políticas en el kernel, aprovisionamiento de nube, una base de datos en ejecución ni tráfico correcto entre clústeres.

Revise tanto el estado declarado como el aplicado, compruebe primero que la conectividad inicial funciona y después correlacione las denegaciones esperadas con sus flujos. Retire únicamente las cargas y políticas del namespace de esta ejecución tras verificar quién las gestiona. En el ejercicio independiente de multi-pool, retire las cargas y compruebe que sus asignaciones ya no estén en uso antes de considerar eliminar el pool. No elimine estado activo de CiliumNode o de pools como atajo.

## Fuentes

- [Modos y migración de IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/index.rst), [Cluster pool](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/cluster-pool.rst), [Ámbito de host](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/kubernetes.rst), [Multi-pool](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/multi-pool.rst), [Procedimiento de migración](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst)
- [Esquema de PodIPPool](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2alpha1/ciliumpodippools.yaml), [Esquema de CiliumNode](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnodes.yaml), [IPAM ENI](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst), [Valores de Helm](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml), [Límites de CNI en EKS](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [API de reglas de políticas](https://github.com/cilium/cilium/blob/v1.20.3/pkg/policy/api/rule.go), [Reglas L3](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer3.rst), [Reglas L7](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst), [Políticas DNS](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/dns.rst), [Implementación de comodines](https://github.com/cilium/cilium/blob/v1.20.3/pkg/fqdn/matchpattern/matchpattern.go)
- [Configuración de Cluster Mesh](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/setup.rst), [Arquitectura](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/intro.rst), [Services globales](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/global-services.rst), [Política entre clústeres](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/policy.rst)


[Volver a la página principal](README.md)

## Cuestionario

[Compruebe sus conocimientos de IPAM y políticas](../../quizzes/networking/cilium/04-ipam-policy-quiz.md).
