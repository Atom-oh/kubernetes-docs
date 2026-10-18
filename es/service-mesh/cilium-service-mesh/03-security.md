# Seguridad de Cilium Service Mesh

> **Última actualización**: 16 de octubre de 2026 · Cilium/chart 1.20.3 · SPIRE incluido 1.15.3. Consulta la [descripción general](./README.md) para ver las versiones probadas de Kubernetes/EKS y los requisitos de plataforma.

## Descripción general

Evalúa tres controles distintos: autorización de cargas de trabajo, autenticación entre pares y cifrado de datos de aplicación. La autenticación mutua fuera de banda de Cilium, el cifrado de transporte WireGuard/IPsec y la beta independiente de mTLS de ztunnel tienen requisitos y limitaciones diferentes.

Los ejemplos de políticas siguientes describen la ruta ordinaria de políticas/autenticación fuera de banda de Cilium. **No des por sentado que conservan la misma aplicación L4 al habilitar el cifrado de ztunnel**; la limitación beta se explica abajo.

## Arquitectura de seguridad

![Separación lógica de identidad/política, autenticación fuera de banda y opciones de cifrado.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-0.html)

Estos bloques agrupan responsabilidades; no certifican que todas las combinaciones conserven todas las políticas. En particular, la beta de ztunnel usa una ruta de identidad/datos distinta y su CA predeterminada no requiere la integración SPIRE mostrada para la autenticación fuera de banda.

## Autenticación mutua y cifrado de datos

### Autenticación mutua Cilium existente

El mecanismo fuera de banda sigue documentado como **beta/incompleto** en Cilium 1.20.3. Los agentes de Cilium autentican las identidades de seguridad de Cilium mediante SVID proporcionados por SPIRE; exigir autenticación mediante una regla de política de red no convierte por sí mismo la conexión de la aplicación en TLS.

![Intercambio ilustrativo de autenticación fuera de banda entre agentes antes de que continúe el tráfico protegido por políticas.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-1.html)

Los registros de autenticación se almacenan en caché para relaciones de identidad. El diagrama no representa un certificado/handshake nuevo para cada solicitud HTTP ni necesariamente para cada conexión de aplicación. Además de los requisitos de autenticación, aplica reglas explícitas de autorización.

### mTLS nativo mediante ztunnel (actualización de 2026)

Cilium 1.20.3 incluye **Ztunnel Transparent Encryption (Beta)**. Selecciónalo con este fragmento de modo después de preparar el material bootstrap/CA necesario:

```yaml
encryption:
  enabled: true
  type: ztunnel
  ztunnel:
    ca:
      type: internal
```

El valor predeterminado publicado usa la opción de CA interna de Cilium. Un Secret `cilium-ztunnel-secrets` proporciona `bootstrap-private.key`, `bootstrap-root.crt`, `ca-private.key` y `ca-root.crt`; el script oficial de generación es un ejemplo, no un diseño completo de PKI/rotación para producción. La opción `bootstrapRootCert` del chart solo proporciona un certificado público; no genera las claves privadas que necesita la CA interna.

El agente de Cilium configura la redirección iptables en los namespaces de red de los pods inscritos, envía el estado de la carga de trabajo al ztunnel del nodo y sirve sus interfaces de control/certificados. El chart crea el DaemonSet `ztunnel-cilium`. La inscripción del namespace usa `io.cilium/mtls-enabled=true`; instalar el modo no inscribe todos los namespaces.

La guía publicada establece estos límites:

- Deben estar inscritos tanto el origen como el destino; no se admite la comunicación entre una carga inscrita y otra no inscrita.
- La inscripción se configura por namespace, no por pod. Los pods que usan la red del host no se pueden inscribir.
- Solo se redirige TCP para mTLS; UDP y otros protocolos quedan fuera de esta ruta de cifrado.
- ClusterMesh no es compatible y el kernel debe admitir las operaciones iptables requeridas.
- El cifrado tiene lugar antes de que los paquetes salgan del pod. Por ello, las políticas L4 ordinarias no funcionan en esta ruta, excepto cuando apuntan directamente al puerto HBONE 15008.

Esta integración usa un modelo de identidad de carga de trabajo por namespace/cuenta de servicio. Es distinto de la ruta SPIFFE numérica `/identity/<id>` que usa la autenticación fuera de banda.

Las comprobaciones de solo lectura para una instalación de prueba preparada incluyen:

```bash
kubectl -n kube-system get daemonset ztunnel-cilium
kubectl get namespaces -l io.cilium/mtls-enabled=true
kubectl -n kube-system get configmap cilium-config -o yaml
```

Una etiqueta de namespace, un proxy saludable o un paquete observado en el puerto 15008, por sí solos, no demuestran que todo el tráfico esperado esté cifrado y autorizado. Comprueba que la inscripción se completó, ambos extremos de la ruta elegida, la identidad/confianza del certificado y los casos de tráfico no admitidos.

### Cuándo elegir Cilium o Istio para mTLS

Elige según la identidad, la autorización y la cobertura del tráfico que necesites. Una instalación de Cilium existente puede usar políticas de identidad junto con WireGuard/IPsec o evaluar la beta independiente de ztunnel dentro de sus límites. Ten en cuenta los proxies, la CA y las dependencias operativas adicionales que estén habilitados realmente.

Istio proporciona mTLS mediante proxies de carga de trabajo en los modos sidecar y ambient, cada uno con sus propios límites de funcionalidad/plataforma. `PeerAuthentication` `STRICT` exige mTLS entrante; por sí sola no emite identidades, instala proxies ni autoriza a todos los llamantes. No reduzcas la comparación a un único interruptor de cifrado. El [capítulo de sidecar/ambient](../istio/comparison/03-sidecar-vs-ambient.md) conserva las versiones y los escenarios medidos realmente.

### Configuración de autenticación mutua basada en SPIRE

Para la autenticación **fuera de banda**, combina este overlay con los valores de instalación revisados:

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      trustDomain: spiffe.cilium
      agentSocketPath: /run/spire/sockets/agent/agent.sock
      install:
        enabled: true
        server:
          dataStorage:
            enabled: true
            size: 1Gi
```

Prepara una StorageClass/PV adecuada para el StatefulSet de SPIRE. Una clase llamada `gp3` no está presente automáticamente en todos los clústeres EKS. Se requiere `authentication.enabled`; el trust domain y la configuración del socket del agente deben ir dentro de `authentication.mutual.spire`, no bajo `install.server` ni `install.agent`. El chart incluido no implementa los antiguos ejemplos `server.replicas`, `server.nodeAttestor`, `agent.workloadAttestor` ni `server.ca.ttl`.

SPIRE Server atestigua a los agentes y firma SVID. Los agentes realizan la atestación de cargas de trabajo; la integración de Cilium también delega la recuperación y registra entradas para las identidades de seguridad de Cilium. Habilitar SPIRE por sí solo no exige autenticación en todo el tráfico ni habilita WireGuard/IPsec.

### Aplicación de políticas de autenticación mutua

`authentication` es un **objeto dentro de una regla de permiso ingress/egress**. No es un array ni un interruptor de nivel superior `spec.authentication`. Esta política de ámbito de clúster selecciona deliberadamente una aplicación/namespace:

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: production-backend-auth
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

### Autenticación mutua por namespace

Este ejemplo namespaced selecciona las cargas de trabajo en `production` y permite pares autenticados de ese namespace por TCP 8080:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: namespace-auth
  namespace: production
spec:
  endpointSelector: {}
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

Es un permiso ilustrativo dentro del mismo namespace, no un ejemplo de mínimo privilegio válido para todas las aplicaciones. Evalúa por separado otros puertos, clientes, sondas y permisos concedidos por políticas existentes. Afecta a ingress; no configura implícitamente una política completa de dependencias egress.

### Autenticación mutua por servicio

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: service-auth
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

Aquí las etiquetas de origen y destino describen cargas de trabajo, no el inicio de sesión de un usuario final. Los permisos de Kubernetes deben controlar quién puede crear cargas, cambiar esas etiquetas o usar sus cuentas de servicio.

## Reglas L7 de CiliumNetworkPolicy

### Política de seguridad HTTP L7

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-security-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:role: reader
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/.*$
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:role: admin
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^(GET|POST|PUT|PATCH|DELETE)$
          path: ^/api/.*$
          headers:
          - Authorization
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: monitoring
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/health$
        - method: ^GET$
          path: ^/metrics$
```

Las reglas HTTP dentro de una regla son alternativas. `headers: [Authorization]` solo exige que la cabecera esté presente: no valida un bearer token, su firma, caducidad ni permisos. La antigua cadena `Authorization: Bearer .*` no era un verificador JWT ni una coincidencia general de valores mediante expresión regular. Implementa la autenticación y autorización de la aplicación por separado.

Una política de ruta HTTP requiere una ruta L7 inspeccionable compatible. El TLS de la aplicación, las sondas y el tráfico de otras dependencias requieren la configuración pertinente; indicar un número de puerto no activa TLS.

### Política de seguridad Kafka L7

El esquema L7 de Cilium 1.20.3 rechaza el antiguo objeto `rules.kafka`. La sustitución siguiente limita **solo la conectividad de red**:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-network-boundary
  namespace: kafka
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: kafka
      k8s:app: kafka
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kafka
        k8s:role: producer
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kafka
        k8s:role: consumer
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

Configura TLS/SASL en el listener Kafka real y las ACL del broker para producción/consumo, temas y grupos de consumidores. Eliminar una regla L7 obsoleta deja acceso L4; no conserva la autorización por tema.

### Política de seguridad DNS L7

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-security
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: web-application
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
        - matchPattern: '*.*.svc.cluster.local'
        - matchName: api.stripe.com
        - matchName: sts.us-east-1.amazonaws.com
  - toFQDNs:
    - matchName: api.stripe.com
    - matchName: sts.us-east-1.amazonaws.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

El ejemplo presupone endpoints de CoreDNS etiquetados `k8s-app=kube-dns` en `kube-system`, además del sufijo DNS ordinario `cluster.local`. Permite DNS por UDP y TCP. El FQDN de un Service contiene las etiquetas del servicio y del namespace, por lo que `*.*.svc.cluster.local` difiere del antiguo `*.svc.cluster.local`.

El permiso de HTTPS externo es independiente del permiso para consultar DNS. `sts.us-east-1.amazonaws.com` es un endpoint regional específico de AWS; AWS no usa el antiguo `api.aws.amazon.com` como endpoint universal de API. Elige los endpoints reales de región/servicio del SDK, incluidas las variantes IPv6/doble pila o de endpoint privado que correspondan. Las respuestas del DNS interno no conceden automáticamente acceso a todos los Services internos.

Revisa el comportamiento de la lista de búsqueda del resolvedor y NodeLocal DNS, si están habilitados. Los comodines S3 amplios pueden permitir destinos adicionales al bucket previsto, y una política DNS/IP no garantiza que se impida la exfiltración mediante destinos permitidos.

## Autenticación mutua

### Modos de autenticación

| Modo | Significado en la API de políticas fuera de banda |
|---|---|
| `required` | Exige autenticación correcta para el tráfico permitido coincidente |
| `disabled` | Exención explícita de autenticación para esa regla coincidente |
| `test-always-fail` | Modo de prueba que provoca deliberadamente un fallo de autenticación |

El esquema publicado no tiene modo `optional`. La ausencia de un requisito explícito no equivale a una exención cuidadosamente delimitada cuando hay reglas superpuestas; inspecciona la política resultante en lugar de suponer que las reglas de autenticación funcionan como permisos independientes ordinarios.

### Ejemplos de políticas de autenticación mutua

Una exención debe ser explícita, acotada y estar justificada:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: authentication-exception
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: secure-service
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: trusted-client
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
    authentication:
      mode: required
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        k8s:app: prometheus
    toPorts:
    - ports:
      - port: '9090'
        protocol: TCP
    authentication:
      mode: disabled
```

La regla de Prometheus especifica **autenticación deshabilitada**, no «autenticar si es posible». Solo concede acceso a la carga de monitorización y al puerto indicados. El TLS en el puerto de escucha de cualquiera de las aplicaciones es una configuración aparte.

### Autenticación basada en SPIFFE ID

Para el trust domain SPIRE predeterminado de autenticación **fuera de banda**, una identidad de seguridad de Cilium tiene esta forma:

```text
spiffe://spiffe.cilium/identity/<numeric-security-identity>
```

Selecciona los pares permitidos mediante políticas de endpoint/identidad; el objeto `authentication` no tiene un campo arbitrario de lista permitida de SPIFFE ID. Cambiar un comentario por un URI de estilo Istio `/ns/.../sa/...` no restringe el acceso. La beta de ztunnel descrita arriba usa otro modelo de identidad de carga de trabajo.

## Cifrado

### Cifrado transparente con WireGuard

```yaml
encryption:
  enabled: true
  type: wireguard
```

Cilium crea pares de claves por nodo y distribuye las claves públicas mediante información de CiliumNode. Se cifra el tráfico compatible entre pods gestionados por Cilium en **nodos distintos**; el tráfico en el mismo nodo no se cifra. El kernel debe admitir WireGuard. El chart no tiene una opción `encryption.wireguard.userspaceFallback`.

Permite la ruta UDP 51871 necesaria entre nodos y ten en cuenta MTU/encapsulación. El encadenamiento con AWS VPC CNI tiene requisitos adicionales de MTU, entre ellos la opción documentada `cni.enableRouteMTUForCNIChaining`; sigue el modo de instalación elegido en vez de aplicarla a ciegas.

#### Arquitectura WireGuard

![Gestión lógica de WireGuard entre nodos a cargo de los agentes Cilium; el cifrado lo realizan las interfaces WireGuard del kernel.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-2.html)

El bloque Agent representa la gestión/distribución de claves, no un salto de tránsito en userspace para cada paquete. Una captura en la interfaz WireGuard puede mostrar los paquetes internos sin cifrar; para evaluar el cifrado, verifica la ruta de red exterior correcta.

La cobertura entre nodos es una opción beta aparte:

```yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: true
```

Los nodos del plano de control se excluyen del cifrado de nodos de forma predeterminada para evitar fallos de bootstrap al actualizar claves. La matriz de tráfico publicada también identifica exclusiones relacionadas con aceleración XDP, DSR sin Geneve y respuestas de egress gateway. WireGuard de nodo no cifra el tramo cliente-clúster de una solicitud externa.

### Cifrado IPsec

```yaml
encryption:
  enabled: true
  type: ipsec
  ipsec:
    secretName: cilium-ipsec-keys
    keyFile: keys
    keyWatcher: true
    keyRotationDuration: 5m
```

El Secret debe existir en el namespace de Cilium. En el ejemplo AES-GCM documentado, la entrada `keys` tiene esta estructura:

```text
3+ rfc4106(gcm(aes)) <fresh-20-byte-random-value-in-hex> 128
```

El signo `+` selecciona claves derivadas por túnel. La forma antigua de clave global sin `+` quedó obsoleta por motivos de seguridad; no la copies como recomendación actual. Genera y protege material de clave nuevo mediante el flujo documentado de CLI/Secret en vez de reutilizar una clave de ejemplo.

`keyRotationDuration: 5m` es un período de transición/limpieza de la clave antigua tras un cambio de clave, **no un planificador que genera una clave nueva cada cinco minutos**. Actualiza los ID y el material de claves mediante el procedimiento compatible, coordina todos los clústeres si usas ClusterMesh y no rotes mientras haya nodos con versiones mezcladas durante una actualización.

Comprueba la compatibilidad de ESP/firewall, las interfaces de cifrado reales y el CIDR de enrutamiento nativo. El IPsec actual requiere el comportamiento documentado de proxy DNS transparente con L7, no admite encadenamiento CNI ni políticas de host y no cifra el tráfico dentro del mismo nodo.

### Comparación de cifrado

| Tema | WireGuard | IPsec | ztunnel beta |
|---|---|---|---|
| Claves/identidad | Pares de claves generados por nodo | Material de clave distribuido con derivación por túnel | Certificados mTLS de cargas de trabajo y material bootstrap/CA |
| Ruta de datos | Interfaces WireGuard del kernel | IPsec/XFRM del kernel | Proxy TLS por nodo y redirección en el namespace del pod |
| Tráfico en el mismo nodo/cobertura | Tráfico del mismo nodo sin cifrar; consulta la matriz de tráfico publicada | Tráfico del mismo nodo sin cifrar; se aplican límites del modo | Ambos extremos inscritos; solo TCP; se aplican límites de políticas |
| Configuración de cifrado | Suite ChaCha20-Poly1305 del protocolo WireGuard | Algoritmos configurados compatibles con el kernel, como AES-GCM | TLS negociado por el proxy compatible |
| Rendimiento | Mide la CPU, MTU y mezcla de tráfico reales | Mide el algoritmo/hardware, el túnel y las limitaciones de descifrado por túnel | Mide la sobrecarga del proxy/TLS y de la carga de trabajo; no forma parte de los benchmarks de la comparación anterior |

El cifrado transparente también puede tener una ventana de descubrimiento de endpoints durante la cual un destino permitido desconocido se trata como externo. Cilium documenta los modos de egress restringido y de cifrado estricto como mitigaciones, con límites concretos: egress estricto depende de IPv4/CIDR; ingress estricto requiere WireGuard e interfaces gestionadas y no es compatible con encadenamiento CNI. No interpretes «cifrado habilitado» como prueba de protección fail-closed para todas las rutas.

## Seguridad basada en identidad

### Identidad Cilium

Cilium asigna una identidad numérica a cada conjunto de etiquetas relevantes para la identidad; varios pods pueden compartirla. No es un hash calculado por el usuario ni un identificador permanente del pod.

### Componentes de identidad

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
CILIUM_POD='<agent-on-the-workload-node>'
kubectl -n default get ciliumendpoints
kubectl get ciliumidentities
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg encrypt status
```

Pueden contribuir el namespace, la cuenta de servicio y las etiquetas de carga de trabajo seleccionadas. Los ID 1–6 corresponden a host, world, unmanaged, health, init y remote-node; los ID de cargas de trabajo asignados dependen de la instalación. Inspecciona el agente del nodo pertinente y conserva completos los errores/estado de los comandos.

### Política basada en identidad

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: identity-based-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: frontend
        k8s:environment: production
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        k8s:app: prometheus
    toPorts:
    - ports:
      - port: '9090'
        protocol: TCP
```

### Comparación de IP e identidad

![Los selectores de identidad evitan reescribir manualmente listas de direcciones con cada cambio de pod, mientras Cilium sigue manteniendo el estado de asignación de dirección a identidad.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-4.html)

Los selectores de políticas pueden mantenerse estables aunque cambien las IP. Cilium sigue teniendo que actualizar el estado del endpoint/caché IP; una identidad puede liberarse y reasignarse. El diagrama no promete que el ID numérico sea inmutable después de cada reinicio.

## Integración con PKI externa

### Integración con cert-manager

Estos objetos ilustran la creación de un Secret de CA upstream. **No conectan por sí mismos ese Secret a SPIRE**:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: cilium-ca-issuer
spec:
  ca:
    secretName: cilium-ca-secret
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: cilium-spire-ca
  namespace: cilium-spire
spec:
  secretName: spire-ca-secret
  duration: 8760h
  renewBefore: 720h
  isCA: true
  privateKey:
    algorithm: ECDSA
    size: 256
    rotationPolicy: Always
  usages:
  - cert sign
  - crl sign
  subject:
    organizations:
    - Cilium
  commonName: SPIRE upstream CA
  issuerRef:
    name: cilium-ca-issuer
    kind: ClusterIssuer
    group: cert-manager.io
```

Prepara una CA/clave de firma válida en `cilium-ca-secret`, dentro del namespace de recursos de clúster configurado para cert-manager, y con vida restante suficiente. Valida las restricciones de la CA, los usos de firma y las cadenas de confianza. La duración de un año es un ejemplo de vida útil de una CA subordinada, no una recomendación universal.

Un servidor SPIRE gestionado externamente debe usar un UpstreamAuthority compatible y acceder al material montado o a la API del emisor. Para una autoridad de disco que se une a una PKI existente, SPIRE requiere `cert_file_path`, `key_file_path` y `bundle_file_path` de la raíz de confianza; planifica la recarga/rotación y el solapamiento de confianza. Actualizar un Secret de Kubernetes no demuestra por sí solo que todos los consumidores de certificados hayan adoptado la CA nueva.

No sustituyas el ConfigMap de SPIRE incluido por un archivo parcial no relacionado. Para SPIRE operado externamente, revisa por separado la dirección del servidor externo de Cilium, el trust domain, el registro delegado de identidades y los requisitos previos de autenticación.

### Integración con Vault

Lo siguiente es solo un **fragmento de plugin** para un servidor SPIRE 1.15.4 configurado de forma independiente, no una configuración completa de servidor ni un Deployment de Kubernetes:

```hcl
plugins {
  UpstreamAuthority "vault" {
    plugin_data {
      vault_addr = "https://vault.vault.svc:8200"
      pki_mount_point = "pki"
      ca_cert_path = "/vault/ca/ca.crt"
      k8s_auth {
        k8s_auth_mount_point = "kubernetes"
        k8s_auth_role_name = "spire-upstream"
        token_path = "/var/run/secrets/vault/token"
      }
    }
  }
}
```

Los plugins van en `plugins` de nivel superior, no dentro de `server`. El campo es `pki_mount_point`; aquí, `token_path` va dentro de `k8s_auth`. El token es un token de cuenta de servicio de Kubernetes proyectado para el rol de autenticación Vault configurado, no un archivo de token Vault genérico.

Prepara la proyección/audience del token y la configuración de autenticación Kubernetes de Vault, vincula el rol a la carga de trabajo SPIRE prevista, monta la CA TLS usada para verificar Vault y concede la operación PKI `sign-intermediate` requerida. Coordina `ca_ttl` de SPIRE, los TTL de PKI de Vault, la confianza de las cargas y la rotación. Esta guía no afirma que esas dependencias externas se hayan desplegado o probado.

## Redes Zero Trust

### Política de denegación predeterminada

Este recurso de ámbito de clúster apunta deliberadamente al namespace aislado `policy-lab`:

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: policy-lab-default-deny
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: policy-lab
  enableDefaultDeny:
    ingress: true
    egress: true
  ingress: []
  egress: []
```

Los indicadores `enableDefaultDeny` son explícitos: un array Cilium ingress/egress vacío por sí solo no proporciona reglas que activen la denegación predeterminada. No traslades a Cilium esa suposición de los ejemplos de Kubernetes NetworkPolicy.

Añade dependencias concretas, como DNS, en reglas de permiso separadas:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: policy-lab-dns
  namespace: policy-lab
spec:
  endpointSelector: {}
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
```

No existe un requisito universal de permitir todo el tráfico de red del host. Evalúa el comportamiento real de kubelet/sondas, el resolvedor y las políticas de host. Estos ejemplos no cambian el tratamiento de host de Cilium ni protegen frente a un nodo privilegiado comprometido.

### Acceso de mínimo privilegio

Este ejemplo presupone una carga de trabajo gateway gestionada por Cilium, etiquetada `app=ingress-gateway` en `edge`, cargas de frontend/base de datos en `production` e integración SPIRE operativa:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: production-security
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: edge
        k8s:app: ingress-gateway
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
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
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
```

Usa las etiquetas e identidades observadas realmente en la implementación de gateway elegida. La ruta ingress/Gateway Envoy propia del nodo de Cilium y los balanceadores de carga externos pueden exponer identidades distintas; una etiqueta Pod arbitraria no es intercambiable con `reserved:ingress` ni con la dirección de un cliente externo. El ejemplo antiguo de ingress-nginx ya retirado no es una dependencia requerida.

### Microsegmentación

Estas políticas por capa de aplicación conservan el acceso DNS explícito para las capas que inician búsquedas de Services. Presuponen el mismo modelo de gateway y los puertos de escucha indicados:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: frontend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: edge
        k8s:app: ingress-gateway
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
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
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: backend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
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
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: database
  enableDefaultDeny:
    egress: true
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: backend
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
  egress: []
```

La base de datos habilita explícitamente la denegación predeterminada de egress sin una regla de permiso egress; aun así, se permiten las respuestas stateful a conexiones autorizadas. Añade deliberadamente dependencias reales de backup, replicación, autenticación u otro tipo. Restringir las rutas de red no impide por completo extraer datos mediante una solicitud de base de datos/aplicación que sí esté autorizada.

## Auditoría y monitorización de seguridad

### Modo de auditoría de políticas

`cilium.io/audit-mode: "true"` no es un interruptor de auditoría por política compatible. Una política con esa anotación arbitraria puede seguir aplicándose normalmente.

Para una **prueba de endpoint aislada**, la opción mutable real del endpoint es `PolicyAuditMode`. Inspecciona el endpoint local, habilita temporalmente la opción y restaura la aplicación de políticas tras la observación controlada:

```bash
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
ENDPOINT_ID='<local-endpoint-id-in-the-isolated-test>'
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID" PolicyAuditMode=true
# Observe the controlled test, then restore enforcement.
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID" PolicyAuditMode=false
```

Esto cambia la aplicación de políticas en ese endpoint; no adjunta un comportamiento de auditoría a un único objeto de política. No deduzcas que toda denegación L7 o fallo de seguridad se convierte en un evento de auditoría permitido; verifica el comportamiento concreto del datapath/proxy. `enableDefaultDeny: false` tampoco es un modo de auditoría L7 equivalente.

### Monitorización de infracciones de políticas

```bash
# Terminal 1
cilium hubble port-forward --port-forward 4245
# Terminal 2
hubble observe --server localhost:4245 --namespace production --verdict DROPPED --last 100
hubble observe --server localhost:4245 --namespace production --verdict DROPPED --drop-reason-desc POLICY_DENIED --last 100
hubble observe --server localhost:4245 --namespace policy-lab --verdict AUDIT --last 100
```

`DROPPED` incluye causas distintas de la denegación por política. La consulta filtrada por motivo se centra en los descartes informados como denegados por una política; los fallos L7/de autorización de aplicación necesitan observación propia. `AUDIT` es distinto de `DROPPED`. `--last 100` limita el historial y Relay puede devolver esa cantidad por cada instancia Hubble conectada; no es un contador completo del tráfico del clúster. Añade `--follow` solo si quieres una observación en streaming.

### Métricas de Prometheus

```yaml
prometheus:
  enabled: true
hubble:
  enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - flow
    - httpV2
    - icmp
    - port-distribution
    - tcp
```

Además de estos indicadores de habilitación, el agente y el exporter Hubble necesitan descubrimiento/scraping de Prometheus. `httpV2` sustituye a `http`, obsoleto; no habilites ambos. Las métricas HTTP requieren la visibilidad L7 correspondiente.

- `cilium_drop_count_total` cuenta paquetes descartados por motivo/dirección, no exclusivamente infracciones de políticas.
- `cilium_forward_count_total` cuenta paquetes reenviados, no solicitudes de aplicación exitosas.
- El exporter `drop` de Hubble expone información de flujos descartados como `hubble_drop_total`; usa una unidad de contabilidad distinta del contador de paquetes del agente.
- El nombre de métrica anterior `cilium_policy_verdict` no era una métrica documentada. En su lugar, utiliza eventos reales de veredictos de políticas o las métricas que exponga el exporter seleccionado.

## Siguientes pasos

- [Observabilidad](./04-observability.md)
- [Ingress y Gateway](./05-ingress-gateway.md)
- [Buenas prácticas](./06-best-practices.md)
- [Cuestionario de seguridad](../../quizzes/service-mesh/cilium-service-mesh/security.md)

## Referencias

- [Autenticación mutua de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [Ejemplo/forma de API de autenticación](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/mutual-authentication/mutual-authentication-example.rst)
- [Esquema CNP de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)
- [Beta de ztunnel de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/network/encryption-ztunnel.rst)
- [Implementación de CA de ztunnel](https://github.com/cilium/cilium/blob/v1.20.3/pkg/ztunnel/ca/ca_server.go)
- [Ejemplo de bootstrap de ztunnel](https://github.com/cilium/cilium/blob/v1.20.3/examples/kubernetes-ztunnel/generate-secrets.sh)
- [Alcance del cifrado/modo estricto](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/network/encryption.rst)
- [WireGuard](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/network/encryption-wireguard.rst)
- [IPsec y rotación de claves](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/network/encryption-ipsec.rst)
- [Valores Helm](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Políticas HTTP/DNS](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Comportamiento de denegación predeterminada](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/intro.rst)
- [API explícita de denegación predeterminada](https://github.com/cilium/cilium/blob/v1.20.3/pkg/policy/api/rule.go)
- [Opción mutable de auditoría de endpoint](https://github.com/cilium/cilium/blob/v1.20.3/pkg/option/endpoint.go)
- [CLI de configuración de endpoints](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/cmdref/cilium-dbg_endpoint_config.md)
- [Métricas](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/observability/metrics.rst)
- [Configuración del servidor SPIRE 1.15.4](https://github.com/spiffe/spire/blob/v1.15.4/doc/spire_server.md)
- [Autoridad Vault de SPIRE](https://github.com/spiffe/spire/blob/v1.15.4/doc/plugin_server_upstreamauthority_vault.md)
- [Autoridad de disco de SPIRE](https://github.com/spiffe/spire/blob/v1.15.4/doc/plugin_server_upstreamauthority_disk.md)
- [ACL de Kafka](https://kafka.apache.org/41/security/authorization-and-acls/)
- [Endpoints STS de AWS](https://docs.aws.amazon.com/general/latest/gr/sts.html)
- [Protocolo WireGuard](https://www.wireguard.com/protocol/)
- [Arquitectura Zero Trust de NIST (lectura adicional)](https://www.nist.gov/publications/zero-trust-architecture)
