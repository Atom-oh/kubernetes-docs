# Glosario de Calico

> **Última actualización**: February 22, 2026

Este documento proporciona definiciones de términos y conceptos clave relacionados con las redes y la seguridad de Calico. Comprender estos términos es esencial para implementar y operar Calico de forma eficaz en entornos de Kubernetes.

## Categorías de términos

Los términos están organizados en las siguientes categorías:
- **Términos de redes** - Conceptos generales de redes
- **Componentes de Calico** - Componentes y servicios específicos de Calico
- **Términos de políticas** - Conceptos de políticas de red y seguridad
- **Términos de operaciones** - Conceptos operativos y de administración

---

## Términos de redes

### A

**AS (Autonomous System)**
- Una colección de redes IP y routers bajo el control de una única organización que presenta una política de enrutamiento común a Internet. En Calico, los números AS se utilizan para la configuración de peering BGP.

**ASN (Autonomous System Number)**
- Un identificador único asignado a un Autonomous System. Los nodos de Calico pueden configurarse con ASN privados (64512-65534) para el enrutamiento BGP interno.

### B

**BGP (Border Gateway Protocol)**
- El protocolo de gateway exterior estándar utilizado para intercambiar información de enrutamiento entre sistemas autónomos. Calico utiliza BGP para distribuir rutas de direcciones IP de Pod entre nodos y hacia redes externas.

**Block Affinity**
- La asociación entre un bloque de direcciones IP y un nodo específico. Calico asigna bloques IP a los nodos para mejorar la eficiencia del enrutamiento y reducir el número de rutas en el clúster.

### C

**CIDR (Classless Inter-Domain Routing)**
- Un método para asignar direcciones IP y realizar enrutamiento IP. Ejemplo: 10.244.0.0/16 representa un rango de 65,536 direcciones IP.

**CNI (Container Network Interface)**
- Una especificación y conjunto de bibliotecas para configurar interfaces de red en contenedores Linux. Calico implementa la especificación CNI para proporcionar redes a los Pod de Kubernetes.

**Conntrack (Connection Tracking)**
- Una característica del kernel de Linux que realiza seguimiento de las conexiones de red para la inspección de paquetes con estado. Calico utiliza conntrack para implementar políticas de red y NAT.

### D

**DNAT (Destination NAT)**
- Traducción de direcciones de red que modifica la dirección IP de destino de los paquetes. Se utiliza en Kubernetes para el balanceo de carga de Service.

**Direct Routing**
- Un modo de red en el que el tráfico entre Pod de distintos nodos se enruta directamente sin encapsulación. Requiere que la red subyacente admita el enrutamiento de Pod CIDR.

**DSR (Direct Server Return)**
- Una técnica de balanceo de carga en la que el tráfico de respuesta evita el balanceador de carga y va directamente del servidor al cliente. El dataplane eBPF de Calico admite DSR para mejorar el rendimiento.

### E

**eBPF (extended Berkeley Packet Filter)**
- Una tecnología del kernel de Linux que permite ejecutar programas aislados en el espacio del kernel. Calico utiliza eBPF como un dataplane alternativo a iptables para mejorar el rendimiento.

**Encapsulation**
- El proceso de encapsular paquetes de red dentro de otros paquetes. Calico admite la encapsulación IPIP y VXLAN para redes overlay.

### F

**FQDN (Fully Qualified Domain Name)**
- Un nombre de dominio completo que especifica la ubicación exacta de un host en la jerarquía DNS. Calico admite políticas de red basadas en FQDN para el control de egress.

**Full Mesh**
- Una topología BGP en la que cada nodo establece peering con todos los demás nodos. Es adecuada para clústeres pequeños, pero no escala bien más allá de 100 nodos.

### I

**IPAM (IP Address Management)**
- El sistema responsable de asignar, rastrear y administrar direcciones IP. Calico incluye un sistema IPAM integrado con asignación basada en bloques.

**IPIP (IP-in-IP)**
- Un protocolo de encapsulación que envuelve paquetes IP dentro de otros paquetes IP. Tiene menor sobrecarga que VXLAN, pero compatibilidad limitada con proveedores de nube.

**IPset**
- Una característica del kernel de Linux para almacenar conjuntos de direcciones IP, redes o puertos. Calico utiliza ipsets para hacer coincidir eficientemente el tráfico con múltiples direcciones.

**iptables**
- Un firewall del kernel de Linux que opera en la capa de red. Calico utiliza iptables (o nftables) para el filtrado de paquetes y NAT en el dataplane estándar.

### M

**MTU (Maximum Transmission Unit)**
- El mayor tamaño de paquete que puede transmitirse en un segmento de red. La encapsulación reduce la MTU efectiva (IPIP: -20 bytes, VXLAN: -50 bytes).

### N

**NAT (Network Address Translation)**
- El proceso de modificar la información de direcciones IP en los encabezados de paquetes. Calico utiliza NAT para el egress de Pod y la implementación de Service.

**nftables**
- El sucesor de iptables, que proporciona un framework moderno para la clasificación de paquetes. Calico admite nftables como alternativa a iptables.

### O

**Overlay Network**
- Una red virtual construida sobre una red física existente. Calico admite modos overlay IPIP y VXLAN para entornos en los que el enrutamiento directo no es posible.

### R

**Route Reflector**
- Un router BGP que refleja rutas entre clientes, eliminando la necesidad de peering full-mesh. Es esencial para escalar BGP en clústeres Calico grandes.

**Routing Table**
- Una estructura de datos que almacena rutas a destinos de red. Calico programa rutas para Pod CIDR en la tabla de enrutamiento del kernel de Linux.

### S

**SNAT (Source NAT)**
- Traducción de direcciones de red que modifica la dirección IP de origen de los paquetes. Se utiliza para el tráfico de egress de Pod y el enmascaramiento.

### V

**veth (Virtual Ethernet)**
- Un par de interfaces de red virtuales utilizadas para conectar espacios de nombres de red. Cada Pod de Calico tiene un par veth que lo conecta a la red del host.

**VXLAN (Virtual Extensible LAN)**
- Un protocolo de encapsulación que extiende redes de capa 2 sobre infraestructura de capa 3. Proporciona mejor compatibilidad con la nube que IPIP, pero con mayor sobrecarga.

### W

**WireGuard**
- Un protocolo VPN moderno que proporciona cifrado rápido y seguro. Calico utiliza WireGuard para cifrar el tráfico de Pod a Pod entre nodos.

**Workload Endpoint**
- La representación de Calico de una interfaz de red para una carga de trabajo (Pod, VM o contenedor). Almacena direcciones IP, etiquetas y asociaciones de políticas.

---

## Componentes de Calico

### B

**BIRD (BIRD Internet Routing Daemon)**
- El daemon BGP utilizado por Calico para la distribución de rutas. BIRD administra el peering BGP, el anuncio de rutas y la funcionalidad de Route Reflector.

### C

**calicoctl**
- La herramienta de línea de comandos para administrar recursos de Calico. Se utiliza para ver el estado, configurar políticas, administrar IPAM y solucionar problemas.

**Calico API Server**
- Un componente opcional que proporciona una extensión de API de Kubernetes para recursos de Calico. Permite el acceso de kubectl a los CRD de Calico.

**CNI Plugin**
- El binario que implementa la especificación CNI para Calico. Es responsable de configurar las redes de Pod (pares veth, rutas, asignación IP).

**confd**
- Una herramienta de administración de configuración que genera archivos de configuración de BIRD a partir del datastore de Calico. Vigila los cambios y actualiza BIRD dinámicamente.

### D

**Dikastes**
- Un proxy sidecar utilizado para la aplicación de políticas L7 en Calico (principalmente en Calico Enterprise). Proporciona visibilidad y control de capa de aplicación.

### F

**Felix**
- El agente principal de Calico que se ejecuta en cada nodo. Es responsable de programar rutas, reglas de iptables/eBPF y aplicar políticas de red.

### K

**kube-controllers**
- Un conjunto de controladores que sincronizan datos entre Kubernetes y el datastore de Calico. Incluye controladores de policy, namespace, serviceaccount, workloadendpoint y node.

### T

**Tigera Operator**
- Un operator de Kubernetes que administra la instalación y el ciclo de vida de Calico. Proporciona configuración declarativa mediante CRD.

**Typha**
- Un proxy fan-out que se sitúa entre Felix y el datastore. Reduce la carga en el servidor de API al almacenar en caché y multiplexar conexiones.

---

## Términos de políticas

### A

**Action**
- El resultado de la evaluación de una regla de política: Allow, Deny, Log o Pass. Determina cómo se maneja el tráfico coincidente.

**applyOnForward**
- Una configuración de política que aplica reglas al tráfico reenviado (tráfico que pasa por el host). Se utiliza para controlar el tráfico entre Pod y redes externas.

### D

**Default Deny**
- Una postura de seguridad en la que todo el tráfico se bloquea a menos que se permita explícitamente. Se implementa mediante una política global sin reglas de allow.

**DoNotTrack**
- Una opción de política que omite el seguimiento de conexiones para el tráfico coincidente. Es útil para escenarios de alto rendimiento donde el manejo sin estado es aceptable.

### E

**Egress**
- Tráfico de red saliente desde un Pod. Las políticas de egress controlan con qué destinos puede comunicarse un Pod.

### G

**GlobalNetworkPolicy**
- Un recurso de política de Calico que se aplica en todos los namespaces de un clúster. Se utiliza para reglas de seguridad de todo el clúster.

**GlobalNetworkSet**
- Un conjunto de direcciones IP o CIDR con ámbito de clúster. GlobalNetworkPolicies hace referencia a él para definiciones coherentes de endpoints externos.

### H

**Host Endpoint**
- Un recurso de Calico que representa la interfaz de red de un host. Permite aplicar políticas de red al tráfico de nivel de host.

### I

**Ingress**
- Tráfico de red entrante hacia un Pod. Las políticas de ingress controlan qué orígenes pueden comunicarse con un Pod.

### N

**NetworkPolicy**
- Un recurso de Kubernetes o Calico que especifica cómo se permite que los Pod se comuniquen. Opera en L3-L4 (y L7 con Calico Enterprise).

**NetworkSet**
- Un conjunto de direcciones IP o CIDR con ámbito de namespace. Proporciona una forma de agrupar endpoints externos para usarlos en políticas de red.

### O

**Order**
- Un valor numérico que determina la secuencia de evaluación de las políticas. Los números más bajos se evalúan primero. Las políticas con el mismo orden se evalúan alfabéticamente.

### P

**Pass**
- Una acción de política que pasa al siguiente tier sin tomar una decisión. Se utiliza en modelos de políticas por niveles para delegar decisiones.

**Policy Selector**
- Una expresión basada en etiquetas que determina a qué endpoints se aplica una política. Utiliza la sintaxis de selectores de Calico (e.g., `app == 'web'`).

**PreDNAT**
- Un tipo de política que se aplica antes del NAT de destino. Se utiliza para controlar el acceso a los servicios NodePort y LoadBalancer.

### S

**Staged Policy**
- Una política en modo de vista previa que registra lo que ocurriría sin aplicarlo realmente. Disponible en Calico Enterprise para probar políticas.

**Selector**
- Una expresión que coincide con recursos según las etiquetas. Calico utiliza selectores tanto para objetivos de políticas como para coincidencias de origen/destino.

### T

**Tier**
- Un mecanismo de agrupación de políticas que proporciona una evaluación jerárquica de políticas. Las políticas en tiers de orden inferior se evalúan primero.

---

## Términos de operaciones

### A

**APIServer (Calico)**
- El componente que proporciona acceso a la API para los recursos de Calico. Puede habilitarse para la integración con kubectl.

### B

**Block**
- Una unidad de asignación de direcciones IP en Calico IPAM. El tamaño predeterminado es /26 (64 direcciones). Los bloques se asignan a nodos para un enrutamiento eficiente.

**Block Affinity**
- La vinculación entre un bloque IP y un nodo. Garantiza que los Pod de un nodo reciban IP de los bloques asignados a ese nodo.

### D

**Dataplane**
- El componente responsable del reenvío de paquetes y la aplicación de políticas. Calico admite dataplanes iptables y eBPF.

**Datastore**
- El almacenamiento backend para la configuración de Calico. Admite Kubernetes API (predeterminado) o etcd.

### F

**FelixConfiguration**
- El CRD que configura el comportamiento de Felix en todo el clúster. Controla el registro, las métricas, la configuración del dataplane y más.

**Flow Logs**
- Registros de conexiones de red procesadas por Calico. Incluyen origen, destino, acción y metadatos.

### H

**Health Check**
- Sondas de liveness y readiness para los componentes de Calico. Felix expone endpoints de salud en el puerto 9099.

### I

**Installation**
- El CRD de Tigera Operator que define la configuración de implementación de Calico. Especifica el modo de red, los recursos y la configuración de componentes.

### M

**Metrics**
- Estadísticas en formato Prometheus expuestas por los componentes de Calico. Felix (9091), Typha (9093) y kube-controllers exponen métricas operativas.

### P

**Pod CIDR**
- El rango de direcciones IP asignado a los Pod de un clúster. Se configura en los recursos IPPool de Calico.

### R

**Rollout**
- El proceso de actualización de los componentes de Calico. El operator administra actualizaciones graduales para minimizar las interrupciones.

### T

**TigeraStatus**
- Un CRD que informa el estado de los componentes de Calico. Muestra la salud de la implementación y el estado de configuración.

---

## Terminología de Calico frente a Kubernetes

| Término de Kubernetes | Equivalente de Calico | Notas |
|-----------------|-------------------|-------|
| NetworkPolicy | NetworkPolicy | Calico amplía K8s NetworkPolicy con funciones adicionales |
| - | GlobalNetworkPolicy | Política para todo el clúster (específica de Calico) |
| - | Tier | Jerarquía de políticas (específica de Calico) |
| Service CIDR | N/A | Calico respeta K8s Service CIDR |
| Pod CIDR | IPPool | Calico administra la asignación de IP de Pod |
| Node | Node | Calico refleja los recursos Node de K8s |
| Namespace | Namespace | Las políticas de Calico pueden seleccionar por namespace |
| Labels | Labels | Misma sintaxis de etiquetas, utilizada en selectores |
| Endpoint | WorkloadEndpoint | Representación interna de endpoint de Calico |
| - | HostEndpoint | Políticas de interfaz de host (específicas de Calico) |

---

## Terminología de Calico frente a Cilium

| Término de Calico | Equivalente de Cilium | Descripción |
|-------------|-------------------|-------------|
| Felix | Cilium Agent | Agente principal del nodo |
| BIRD | BGP Control Plane | Daemon de enrutamiento BGP |
| Typha | - | Proxy fan-out de conexiones (específico de Calico) |
| IPPool | IPAM Pool | Pool de asignación de direcciones IP |
| NetworkPolicy | CiliumNetworkPolicy | Política con ámbito de namespace |
| GlobalNetworkPolicy | CiliumClusterwideNetworkPolicy | Política para todo el clúster |
| NetworkSet | CiliumIPSet | Agrupaciones de direcciones IP |
| Tier | - | Jerarquía de políticas (específica de Calico) |
| WorkloadEndpoint | CiliumEndpoint | Endpoint de red de Pod |
| HostEndpoint | - | Política de host (específica de Calico) |
| eBPF Dataplane | eBPF Dataplane | Procesamiento de paquetes de alto rendimiento |
| WireGuard | WireGuard | Cifrado entre nodos |
| - | Hubble | Plataforma de observabilidad (específica de Cilium) |
| Flow Logs | Hubble Flows | Visibilidad de flujos de red |
| kube-controllers | Cilium Operator | Sincronización de Kubernetes |
| calicoctl | cilium CLI | Herramienta de administración de línea de comandos |

---

## Referencias cruzadas

### Análisis profundo de arquitectura
- **Felix**: Consulte [Part 2: Architecture](02-architecture.md)
- **BGP Configuration**: Consulte [Part 4: BGP Deep Dive](04-bgp-deep-dive.md)
- **Typha Scaling**: Consulte [Part 7: Advanced Topics](07-advanced-topics.md#typha-sizing-formula)

### Política de red
- **Kubernetes NetworkPolicy**: Consulte [Part 5: Network Policy](05-network-policy.md)
- **GlobalNetworkPolicy**: Consulte [Part 5: Network Policy](05-network-policy.md)
- **Tier-Based Policies**: Consulte [Part 5: Network Policy](05-network-policy.md)

### Operaciones
- **Métodos de instalación**: Consulte [Part 9: Operations](09-operations.md#installation-guide)
- **Comandos calicoctl**: Consulte [Part 9: Operations](09-operations.md#calicoctl-command-reference)
- **Solución de problemas**: Consulte [Part 9: Operations](09-operations.md#troubleshooting)

### Integración con EKS
- **VPC CNI + Calico**: Consulte [Part 8: EKS Integration](08-eks-integration.md#vpc-cni--calico-architecture)
- **Métodos de instalación**: Consulte [Part 8: EKS Integration](08-eks-integration.md#installation-methods-comparison)

---

## Cuestionario

Para poner a prueba lo que aprendió en este capítulo, pruebe el [Cuestionario del glosario](../../quizzes/networking/calico/glossary-quiz.md).
