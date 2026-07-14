# Cuestionario sobre la arquitectura de Cilium Service Mesh

Este cuestionario evalúa tu comprensión de la arquitectura de Cilium Service Mesh, el datapath eBPF, el proxy Envoy por nodo y el modelo CRD.

## Preguntas del cuestionario

### 1. ¿Cuál es la diferencia clave entre Cilium Service Mesh y los service meshes tradicionales basados en sidecar?

A. No es nativo de Kubernetes
B. Usa eBPF para procesar tráfico L3/L4 a nivel del kernel
C. Procesa todo el tráfico en el espacio de usuario
D. Usa múltiples proxies por Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usa eBPF para procesar tráfico L3/L4 a nivel del kernel**

**Explicación:**
Cilium Service Mesh usa eBPF (extended Berkeley Packet Filter) para procesar tráfico L3/L4 directamente dentro del kernel de Linux. Esto es fundamentalmente diferente de los service meshes tradicionales que procesan todo el tráfico a través de proxies sidecar en el espacio de usuario. El tráfico solo se reenvía a un proxy Envoy compartido por nodo cuando se requiere procesamiento L7.

</details>

### 2. ¿Cuál NO es un punto de enganche de eBPF donde pueden ejecutarse los programas de Cilium?

A. XDP (eXpress Data Path)
B. TC (Traffic Control)
C. Capa de aplicación
D. cgroup

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Capa de aplicación**

**Explicación:**
Los programas eBPF se ejecutan a nivel del kernel, y sus puntos de enganche clave son XDP (controlador NIC), TC (entrada de la pila de red), Socket Operations (nivel de socket) y cgroup (grupo de procesos). La Capa de aplicación está en el espacio de usuario y, por lo tanto, no es un punto de enganche de eBPF.

</details>

### 3. ¿Cuál es la ventaja del modelo de proxy Envoy por nodo de Cilium?

A. Permite una configuración más compleja
B. Aumenta el uso de memoria por Pod
C. Eficiencia de recursos y baja latencia
D. No puede cifrar todo el tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Eficiencia de recursos y baja latencia**

**Explicación:**
Usar un proxy Envoy por nodo consume significativamente menos memoria que desplegar sidecars por Pod. En un cluster de 100 Pods, Istio usa aproximadamente 5 GB (50 MB por Pod), mientras que Cilium usa solo unos 500 MB (100 MB por nodo). Además, el tráfico L3/L4 se procesa directamente en eBPF, lo que reduce significativamente la latencia.

</details>

### 4. ¿Cuál es el propósito principal del CRD CiliumEnvoyConfig?

A. Definir políticas de red de Kubernetes
B. Definir la configuración del proxy Envoy para servicios específicos
C. Definir reglas de programación de Pods
D. Definir clases de almacenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Definir la configuración del proxy Envoy para servicios específicos**

**Explicación:**
CiliumEnvoyConfig es un CRD con ámbito de namespace que define la configuración del proxy Envoy (listeners, routes, clusters, etc.) para servicios específicos. Esto permite configurar características L7 como enrutamiento HTTP, manipulación de encabezados y balanceo de carga.

</details>

### 5. ¿Qué algoritmo de balanceo de carga proporciona hashing consistente cuando Cilium reemplaza kube-proxy?

A. Aleatorio
B. Round Robin
C. Maglev
D. Least Connection

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Maglev**

**Explicación:**
Maglev es un algoritmo de hashing consistente desarrollado por Google y usado en el balanceador de carga basado en eBPF de Cilium. Este algoritmo proporciona afinidad de sesión que mantiene la mayoría de las conexiones existentes incluso cuando cambian los backends. Ofrece alto rendimiento con un tiempo de búsqueda O(1).

</details>

### 6. ¿Qué afirmación sobre Cilium Identity es correcta?

A. Identifica workloads basándose en direcciones IP
B. Genera ID numéricos mediante hashing de las labels de Pod
C. Usa direcciones MAC para la identificación
D. Debe ser asignada manualmente por los usuarios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Genera ID numéricos mediante hashing de las labels de Pod**

**Explicación:**
Cilium Identity genera ID numéricos únicos mediante hashing de las labels de Pod (namespace, service account, labels definidas por el usuario, etc.). Este enfoque basado en ID tiene la ventaja de que las políticas no se ven afectadas cuando cambian las direcciones IP.

</details>

### 7. ¿Qué sucede con el flujo de tráfico cuando se aplica una política L7 en Cilium?

A. Todo el tráfico siempre pasa a través de Envoy
B. Solo el tráfico con políticas L7 se redirige a Envoy
C. Envoy se omite por completo
D. El tráfico se descarta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Solo el tráfico con políticas L7 se redirige a Envoy**

**Explicación:**
Para lograr eficiencia, Cilium solo redirige al proxy Envoy del nodo el tráfico con políticas L7. El tráfico que solo tiene políticas L3/L4 o no tiene políticas se procesa directamente en eBPF y se reenvía rápidamente dentro del kernel.

</details>

### 8. ¿Dónde se realiza el seguimiento de conexiones de Cilium?

A. daemon conntrack en el espacio de usuario
B. mapas eBPF
C. proxy Envoy
D. Kubernetes API server

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. mapas eBPF**

**Explicación:**
Cilium usa mapas eBPF para el seguimiento de conexiones. Los mapas CT (Connection Tracking) almacenan y buscan el estado de las conexiones dentro del kernel, lo que permite el almacenamiento en caché y la aplicación rápida de decisiones de políticas para las conexiones existentes.

</details>

### 9. ¿Cuál es la diferencia entre CiliumClusterwideNetworkPolicy y CiliumNetworkPolicy?

A. Ambas tienen el mismo ámbito
B. CiliumClusterwideNetworkPolicy se aplica a todo el cluster
C. CiliumNetworkPolicy tiene más características
D. CiliumClusterwideNetworkPolicy no admite políticas L7

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. CiliumClusterwideNetworkPolicy se aplica a todo el cluster**

**Explicación:**
CiliumNetworkPolicy tiene ámbito de namespace, mientras que CiliumClusterwideNetworkPolicy tiene ámbito de todo el cluster. Las políticas para todo el cluster son útiles para políticas de denegación predeterminada o reglas de seguridad que deben aplicarse a todos los namespaces. Ambos CRD admiten políticas L7.

</details>

### 10. ¿Cuál es el formato de los ID SPIFFE usados en Cilium Service Mesh?

A. urn:spiffe:cluster/namespace/pod
B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>
C. https://spiffe.io/id/\<pod-name\>
D. spiffe:\<namespace\>:\<pod-name\>

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>**

**Explicación:**
Los ID SPIFFE (Secure Production Identity Framework for Everyone) son identificadores únicos para workloads. Al integrarse con SPIRE en Cilium Service Mesh, cada workload recibe un ID SPIFFE con el formato `spiffe://cluster.local/ns/<namespace>/sa/<service-account>`. Este ID se usa para la autenticación mTLS.

</details>

### 11. ¿Cuál NO es una función del Cilium Agent?

A. Gestión de programas eBPF
B. Generación y sincronización de configuración de Envoy
C. Función de Kubernetes API server
D. Gestión de identidades

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Función de Kubernetes API server**

**Explicación:**
El Cilium Agent se ejecuta en cada nodo y es responsable de la gestión de programas eBPF, la compilación de políticas, la generación/sincronización de configuración de Envoy, la gestión de identidades, la gestión de endpoints y el registro de flujos. El Kubernetes API server forma parte del control plane de Kubernetes y está separado de Cilium.

</details>

### 12. ¿Qué optimización proporciona Cilium para la comunicación entre Pods en el mismo nodo?

A. Siempre se enruta a través de la red externa
B. Ruta directa del kernel mediante eBPF que omite la pila de red
C. Reenvía todo el tráfico a Envoy
D. La comunicación no es posible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Ruta directa del kernel mediante eBPF que omite la pila de red**

**Explicación:**
Para la comunicación entre Pods en el mismo nodo, Cilium usa eBPF para reenviar el tráfico mediante una ruta directa del kernel. Esto omite toda la pila de red de Linux y logra una latencia muy baja (~0.1ms).

</details>
