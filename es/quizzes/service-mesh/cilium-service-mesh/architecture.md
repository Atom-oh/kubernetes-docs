# Cuestionario sobre la arquitectura de Cilium Service Mesh

Revisado con Cilium 1.20.3. Consulta la [guía de arquitectura](../../../service-mesh/cilium-service-mesh/01-architecture.md) para conocer la configuración, las salvedades y las referencias principales.

### 1. ¿Qué característica tiene la arquitectura de Cilium?

- **A.** Reemplaza el servidor de API de Kubernetes
- **B.** Combina el procesamiento L3/L4 con eBPF y Envoy para el tráfico L7 aplicable
- **C.** Envía cada paquete a través de un Envoy por Pod
- **D.** No puede usar recursos de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Combina el procesamiento L3/L4 con eBPF y Envoy para el tráfico L7 aplicable**

Cilium implementa las redes y las políticas L3/L4 con eBPF. Las funciones L7 aplicables usan Envoy, administrado por el agente o en un DaemonSet independiente. Esto describe la ubicación de los componentes, no garantiza un resultado de rendimiento universal.

</details>

### 2. ¿Cuál de estos elementos no es un mecanismo de conexión al kernel que se use para describir el plano de datos de Cilium?

- **A.** TC/TCX
- **B.** Hooks de socket de cgroup
- **C.** El controlador HTTP de la aplicación
- **D.** XDP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. El controlador HTTP de la aplicación**

Un controlador HTTP es código de la aplicación, no un hook del kernel. Cilium puede usar TC/TCX y hooks de cgroup; la aceleración XDP requiere una configuración y un dispositivo adecuados. Que haya eBPF no significa que todos estos hooks se ejecuten con cada paquete.

</details>

### 3. ¿Qué implica compartir un proceso Envoy a nivel de nodo?

- **A.** Exactamente 100 MB de memoria por nodo
- **B.** Una latencia de solicitud garantizada de 0,1 ms
- **C.** Un límite compartido para el ciclo de vida, los recursos y los fallos del proxy que debe dimensionarse según la carga de trabajo
- **D.** Que no hace falta configurar el cifrado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Un límite compartido para el ciclo de vida, los recursos y los fallos del proxy que debe dimensionarse según la carga de trabajo**

Compartir Envoy puede reducir el número de instancias de proxy frente al uso de sidecars por Pod, pero el uso total de recursos también incluye agentes, mapas, el plano de control y los componentes opcionales. El costo real depende del número de nodos, el tráfico, las políticas y las funciones; la antigua comparación fija de 5 GB frente a 500 MB no era un resultado medido.

</details>

### 4. ¿Qué define un CiliumEnvoyConfig?

- **A.** Solo la programación de Pods
- **B.** Recursos Envoy de bajo nivel con alcance de espacio de nombres y la redirección de servicios o sincronización de backends asociada
- **C.** Un reemplazo de todos los CiliumEndpoint
- **D.** Una configuración universal que se acepta únicamente porque `kubectl apply` tiene éxito

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Recursos Envoy de bajo nivel con alcance de espacio de nombres y la redirección de servicios o sincronización de backends asociada**

CEC conecta servicios de Kubernetes con Listeners, Routes y Clusters de Envoy. Cilium puede asignar las direcciones de escucha omitidas y completar los orígenes xDS. Kubernetes no valida todos los campos Envoy incrustados, así que aun así hay que comprobar la aceptación y el comportamiento en tiempo de ejecución. CCEC tiene alcance de clúster, pero `*` no se convierte por ello en un comodín de servicios.

</details>

### 5. ¿Qué afirmación sobre Maglev es correcta?

- **A.** Es un analizador de cookies HTTP
- **B.** Reemplaza la afinidad de sesión ClientIP de Kubernetes
- **C.** Proporciona una selección coherente de backends para el tráfico externo aplicable, independientemente de la afinidad de sesión
- **D.** Garantiza que los backends retirados sigan atendiendo las conexiones existentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Proporciona una selección coherente de backends para el tráfico externo aplicable, independientemente de la afinidad de sesión**

Maglev asigna flujos de forma coherente a los backends para el balanceo de carga norte-sur aplicable. La ruta documentada de sockets este-oeste no usa Maglev. La afinidad ClientIP y el seguimiento de conexiones son mecanismos independientes; Maglev no puede mantener disponible un backend que ya no lo está.

</details>

### 6. ¿Cómo se asigna una identidad de seguridad a una carga de trabajo de Cilium?

- **A.** Siempre es idéntica a la IP del Pod
- **B.** Cilium asigna un ID numérico a un conjunto de etiquetas relevantes para la identidad; varios Pods pueden compartirlo
- **C.** Los usuarios calculan un hash de etiquetas y crean un CiliumIdentity supuesto
- **D.** Cada Pod tiene una identidad numérica permanente y global

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Cilium asigna un ID numérico a un conjunto de etiquetas relevantes para la identidad; varios Pods pueden compartirlo**

Entre las etiquetas relevantes para la identidad pueden estar el espacio de nombres, la cuenta de servicio y algunas etiquetas de la carga de trabajo. El asignador resuelve el conjunto de etiquetas a un ID; no es un hash calculado por el usuario ni tiene que ser único para cada Pod. Inspecciona CiliumEndpoint/CiliumIdentity y la lista de identidades de `cilium-dbg` del agente.

</details>

### 7. ¿Qué tráfico puede usar Envoy?

- **A.** Todos los paquetes en cualquier configuración
- **B.** El tráfico con políticas HTTP L7 y el tráfico redirigido por una configuración compatible de Service/Ingress/Gateway
- **C.** Solo los flujos con una regla HTTP de CiliumNetworkPolicy; nunca el tráfico de Gateway
- **D.** Ninguno, a menos que cada Pod tenga un sidecar Envoy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. El tráfico con políticas HTTP L7 y el tráfico redirigido por una configuración compatible de Service/Ingress/Gateway**

La política HTTP redirige a Envoy el tráfico de entrada o salida correspondiente. El balanceo de carga de servicios mediante CEC y Gateway/Ingress también pueden requerir Envoy. La respuesta a una solicitud con proxy usa la conexión del proxy ya establecida; no se trata de una redirección opcional e independiente para cada respuesta.

</details>

### 8. ¿Para qué sirve el seguimiento de conexiones BPF de Cilium?

- **A.** Para reemplazar la API de Kubernetes
- **B.** Para mantener el estado de los flujos y reconocer el tráfico de respuesta, junto con las comprobaciones de políticas
- **C.** Para almacenar en caché de forma permanente el primer permiso para todos los paquetes futuros
- **D.** Para guardar credenciales de aplicaciones HTTP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Para mantener el estado de los flujos y reconocer el tráfico de respuesta, junto con las comprobaciones de políticas**

Los mapas CT registran el estado y la duración de los flujos, además de metadatos de traducción y proxy. El plano de datos publicado para los endpoints comprueba las políticas en el tráfico iniciador, tanto en conexiones nuevas como establecidas, con excepciones explícitas; también trata las respuestas reconocidas mediante seguimiento con estado. La caché de CT no exime de forma general de aplicar las políticas.

</details>

### 9. ¿En qué se diferencia CiliumClusterwideNetworkPolicy de CiliumNetworkPolicy?

- **A.** Tienen el mismo alcance como recursos de Kubernetes
- **B.** CCNP tiene alcance de clúster y CNP tiene alcance de espacio de nombres; los selectores siguen determinando qué endpoints se ven afectados
- **C.** Solo CNP puede expresar cualquier regla L7
- **D.** Toda CCNP deniega necesariamente el tráfico de todos los espacios de nombres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. CCNP tiene alcance de clúster y CNP tiene alcance de espacio de nombres; los selectores siguen determinando qué endpoints se ven afectados**

Ambas admiten las reglas de políticas L7 aplicables. El alcance del recurso y la selección de endpoints son conceptos distintos: un recurso con alcance de clúster no selecciona ni deniega automáticamente todas las cargas de trabajo. También importan los permisos concedidos por otras políticas aplicables.

</details>

### 10. ¿Cuál es el formato predeterminado del ID SPIFFE para la autenticación mutua beta fuera de banda de Cilium?

- **A.** `urn:spiffe:cluster/namespace/pod`
- **B.** `spiffe://spiffe.cilium/identity/<numeric-security-identity>`
- **C.** `spiffe://cluster.local/ns/<namespace>/sa/<service-account>` en todas las instalaciones de Cilium
- **D.** `https://spiffe.io/id/<pod-name>`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `spiffe://spiffe.cilium/identity/<numeric-security-identity>`**

El proveedor SPIRE publicado de Cilium construye la ruta `/identity/<numeric-id>` bajo el dominio de confianza configurado, que de forma predeterminada es `spiffe.cilium`. Los agentes actúan en nombre de las identidades de seguridad de Cilium. El intercambio de autenticación es fuera de banda; el cifrado de las aplicaciones requiere configurar WireGuard/IPsec por separado. La función fuera de banda sigue en fase beta e incompleta. La beta independiente de cifrado con ztunnel usa otro modelo de identidad de cargas de trabajo; esta respuesta no describe su ruta de certificados.

</details>

### 11. ¿Cuál de estas tareas no es responsabilidad del agente de Cilium?

- **A.** Administrar programas y mapas BPF locales
- **B.** Administrar las políticas locales y la configuración de Envoy
- **C.** Actuar como servidor de API de Kubernetes
- **D.** Administrar endpoints e identidades locales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Actuar como servidor de API de Kubernetes**

El agente se ejecuta en los nodos; el servidor de API de Kubernetes es un componente independiente del plano de control. Cilium Operator es un Deployment independiente para tareas de todo el clúster, como recolectar identidades y realizar operaciones pertinentes de IPAM.

</details>

### 12. ¿Qué afirmación sobre el tráfico entre Pods del mismo nodo es correcta?

- **A.** Siempre debe salir del nodo
- **B.** Una ruta BPF de host adecuada puede evitar las capas superiores de la red del host, pero la ruta real depende de la configuración
- **C.** Siempre se omiten todas las pilas de red de Linux y de los Pods
- **D.** Su latencia está garantizada en 0,1 ms

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Una ruta BPF de host adecuada puede evitar las capas superiores de la red del host, pero la ruta real depende de la configuración**

El enrutamiento de host con BPF puede omitir la pila superior del host/netfilter si se cumplen los requisitos. Las pilas de protocolo de los Pods siguen existiendo. El enrutamiento heredado, el modo de dispositivo del endpoint, las políticas L7 y las integraciones cambian la ruta; la latencia debe medirse.

</details>
