# Cuestionario de introducción a las redes de Kubernetes

Revisado el 11 de septiembre de 2026. Consulte la [introducción a las redes](../../networking/README.md) y sus referencias oficiales para conocer las condiciones de versión y plataforma.

## Preguntas del cuestionario

### 1. ¿Qué afirmación NO garantiza el modelo de redes de Kubernetes?

- A. Los Pods normales tienen conectividad directa en la red de Pods, sujeta a la segmentación intencional
- B. Los agentes del nodo pueden acceder a los Pods de su propio nodo
- C. Los contenedores de un Pod normal comparten su espacio de nombres de red
- D. Un Pod recreado siempre conserva la misma IP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Un Pod recreado siempre conserva la misma IP**

Un Pod de reemplazo puede recibir otra IP, y reiniciar un contenedor dentro del mismo Pod no necesariamente recrea su entorno de red aislado. Los Services proporcionan descubrimiento estable aunque cambien los endpoints. Las políticas de red y el enrutamiento siguen determinando si una conexión concreta puede establecerse.

</details>

### 2. ¿Cuál es la función principal de CNI en Kubernetes actualmente?

- A. Programar Pods a través del servidor de API
- B. Proporcionar la interfaz de runtime para configurar la red y las direcciones de los contenedores
- C. Reemplazar todas las implementaciones de balanceo de carga de Services
- D. Descargar imágenes de contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Proporcionar la interfaz de runtime para configurar la red y las direcciones de los contenedores**

kubelet solicita operaciones del entorno aislado mediante CRI; el runtime de contenedores administra e invoca los complementos CNI. Los complementos implementan operaciones de red y pueden delegar IPAM o usar un agente específico del proveedor. Un par veth es una implementación común, no un requisito de todos los CNI.

</details>

### 3. ¿Qué distingue el enrutamiento overlay del enrutamiento nativo?

- A. Overlay siempre es más rápido
- B. Overlay encapsula el tráfico sobre otra red; el enrutamiento nativo usa las rutas subyacentes sin esa capa overlay
- C. El enrutamiento nativo siempre requiere VXLAN
- D. Solo AWS puede usar una red overlay

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Overlay encapsula el tráfico sobre otra red; el enrutamiento nativo usa las rutas subyacentes sin esa capa overlay**

VXLAN/IPIP son ejemplos de encapsulación. El enrutamiento nativo requiere un diseño de rutas adecuado; puede usar BGP, pero no siempre lo necesita. Compare la MTU, el cifrado, las políticas, el tráfico y el hardware antes de afirmar diferencias de rendimiento.

</details>

### 4. ¿Qué tipo de Service predeterminado proporciona una IP virtual interna al clúster?

- A. NodePort
- B. LoadBalancer
- C. ClusterIP
- D. ExternalName

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. ClusterIP**

ClusterIP es el tipo predeterminado. Su exposición interna habitual no es una frontera de seguridad ni garantiza la conectividad. NodePort usa direcciones/puertos configurados del nodo; LoadBalancer requiere una implementación y puede ser interno; ExternalName proporciona un alias DNS. Los Services headless omiten la IP virtual.

</details>

### 5. ¿Qué proyecto combina un plano de datos de red basado en eBPF con Hubble?

- A. Flannel
- B. El proyecto original Weave Net
- C. Cilium
- D. AWS VPC CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Cilium**

Cilium usa eBPF e incluye observabilidad mediante Hubble; las funciones L7 aplicables usan Envoy. Otros proyectos también usan eBPF, incluidas las opciones de plano de datos de Calico y el agente de políticas de AWS. El nombre de la tecnología por sí solo no establece una clasificación de rendimiento universal.

</details>

### 6. ¿Qué afirmación NO describe correctamente las capacidades documentadas de políticas de EKS VPC-CNI/Auto Mode?

- A. VPC CNI usa direcciones de VPC y ENI/prefijos de EC2
- B. La capacidad de Pods por nodo depende de los límites de la instancia, el modo de asignación y los límites de kubelet
- C. Las implementaciones compatibles de EKS ofrecen capacidades de políticas de red Standard y Admin
- D. La ApplicationNetworkPolicy basada en DNS implica la inspección actual de métodos/cuerpos HTTP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. La ApplicationNetworkPolicy basada en DNS implica la inspección actual de métodos/cuerpos HTTP**

AWS documenta ApplicationNetworkPolicy de DNS/FQDN para Auto Mode, y Admin ClusterNetworkPolicy para Auto Mode e instalaciones compatibles de EC2/VPC CNI. Los controles de capa de red basados en DNS son distintos de la inspección HTTP. Las condiciones de compatibilidad difieren entre Linux EC2, Windows y Fargate; el complemento estándar de EC2 no es la implementación de Auto Mode.

</details>

### 7. ¿Qué par ofrece una opción de plano de control BGP?

- A. Flannel y el proyecto original Weave Net
- B. Calico y Cilium
- C. AWS VPC CNI y Flannel
- D. El proyecto original Weave Net y AWS VPC CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Calico y Cilium**

Calico y Cilium pueden anunciar rutas a pares adecuados. El emparejamiento BGP no proporciona por sí solo descubrimiento de servicios de aplicaciones, autenticación de cargas de trabajo ni cifrado. Verifique la propiedad de las rutas, la API BGP actual del CNI elegido y los requisitos de topología.

</details>

### 8. ¿Qué tráfico queda fuera del aislamiento normal de NetworkPolicy entre Pods de Kubernetes?

- A. El tráfico entre distintos Pods
- B. El egreso de un Pod a un endpoint externo
- C. La comunicación localhost entre contenedores que comparten el espacio de nombres de red de un Pod
- D. El tráfico externo que entra a un Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. La comunicación localhost entre contenedores que comparten el espacio de nombres de red de un Pod**

Los contenedores que comparten el espacio de nombres de red de un Pod pueden comunicarse mediante localhost. NetworkPolicy requiere una implementación que aplique las políticas y tiene excepciones definidas y detalles que dependen de la implementación. No infiera que todos los flujos del host, traducidos o encapsulados se controlan de la misma manera.

</details>

### 9. ¿Qué criterio ayuda a evaluar la escalabilidad de un clúster grande?

- A. Solo si el proyecto tiene un panel
- B. La carga del controlador/API, la propagación del estado, los recursos por nodo y el comportamiento ante cambios realistas
- C. La apariencia del logotipo
- D. Solo la frecuencia de publicación de versiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La carga del controlador/API, la propagación del estado, los recursos por nodo y el comportamiento ante cambios realistas**

Pruebe la cardinalidad de políticas/endpoints, la propagación de actualizaciones, los cambios frecuentes de conexiones, la recuperación de fallos y la carga real del plano de datos. Un umbral de cantidad de nodos o la etiqueta eBPF por sí solos no demuestran que sea una opción adecuada. Los componentes del producto y los mecanismos de escalado deben coincidir con el modo de instalación elegido.

</details>

### 10. ¿Cuál es la relación correcta entre Ingress y Service?

- A. Ingress es una API solo L4 y Service solo L7
- B. Ingress describe el enrutamiento HTTP/HTTPS; Services describen los endpoints de red y el descubrimiento
- C. Los Services siempre son externos
- D. Ingress solo admite UDP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Ingress describe el enrutamiento HTTP/HTTPS; Services describen los endpoints de red y el descubrimiento**

Ingress necesita un controlador/plano de datos y normalmente referencia backends Service. El plano de datos puede conectarse a IP de Pods de endpoint o a NodePorts, así que la IP virtual del Service no necesariamente agrega un salto de paquete. Los protocolos Service y la compatibilidad del balanceador deben verificarse en la implementación real.

</details>
