# Glosario de Calico

> **Referencia revisada**: Calico 3.32.2; terminología comparativa contrastada con Cilium 1.20.1.
> **Última actualización**: 12 de septiembre de 2026

Este documento define términos y conceptos clave relacionados con las redes y la seguridad de Calico. Comprenderlos es fundamental para implementar y operar Calico de forma eficaz en entornos de Kubernetes.

## Categorías de términos

Los términos se organizan en estas categorías:
- **Términos de redes**: conceptos generales de redes
- **Componentes de Calico**: componentes y servicios específicos de Calico
- **Términos de políticas**: conceptos de políticas de red y seguridad
- **Términos de operaciones**: conceptos operativos y de administración

---

## Términos de redes

### A

**AS (Autonomous System)**
- Conjunto de redes IP y routers bajo el control de una organización que presenta una política de enrutamiento común a Internet. En Calico, los números AS se utilizan para configurar las sesiones BGP entre pares.

**ASN (Autonomous System Number)**
- Identificador utilizado por BGP. RFC 6996 reserva los rangos **64512–65534** y **4200000000–4294967294** para uso privado. Los ASN privados se pueden reutilizar dentro de dominios administrativos y no deben tratarse como asignaciones públicas globalmente únicas.

### B

**BGP (Border Gateway Protocol)**
- Protocolo de enrutamiento que se utiliza tanto entre sistemas autónomos (eBGP) como dentro de un sistema autónomo (iBGP). Calico puede utilizar BGP para distribuir rutas de Pods y Services; no todos los dataplanes ni perfiles de superposición de Calico lo requieren.

**Block Affinity**
- Asociación entre un bloque de IPAM y su propietario, que normalmente es un nodo. Sin afinidad estricta, las asignaciones aptas pueden tomar direcciones prestadas del bloque de otro nodo. La afinidad no garantiza que todas las direcciones de Pods locales procedan de un bloque propiedad del nodo; inspecciona el tipo y el estado del recurso y el asignador real.

### C

**CIDR (Classless Inter-Domain Routing)**
- Método para asignar direcciones IP y enrutar tráfico IP. Por ejemplo, 10.244.0.0/16 representa un rango de 65 536 direcciones IP.

**CNI (Container Network Interface)**
- Especificación para configurar la conectividad de red de contenedores y sus complementos asociados. Calico proporciona implementaciones de CNI; el comportamiento difiere entre las redes de Linux y las configuraciones HNS compatibles con Windows.

**Conntrack (Connection Tracking)**
- Estado que se utiliza para hacer seguimiento de flujos en políticas con estado y NAT. El dataplane estándar de Linux utiliza el seguimiento de conexiones del kernel; el dataplane BPF de Calico también mantiene mapas de conntrack de BPF. No son objetivos de ajuste intercambiables.

### D

**DNAT (Destination NAT)**
- Traducción de direcciones de red que modifica la dirección IP de destino de los paquetes. En Kubernetes se utiliza para el balanceo de carga de Services.

**Direct Routing**
- Modo de red en el que el tráfico entre Pods de distintos nodos se enruta directamente, sin encapsulación. Requiere que la red subyacente pueda enrutar los CIDR de los Pods.

**DSR (Direct Server Return)**
- Modo de balanceo de carga de Services en el que el backend devuelve el tráfico sin pasar por el nodo que lo reenvió originalmente. El dataplane BPF de Calico lo admite con restricciones específicas de red y dirección de origen; no es compatible universalmente con los balanceadores de carga en la nube.

### E

**eBPF (extended Berkeley Packet Filter)**
- Tecnología de programación del kernel de Linux que el dataplane BPF de Calico utiliza para redes, políticas y gestión de Services. La compatibilidad y el rendimiento dependen del kernel, la plataforma y la carga de trabajo; no garantiza menos sobrecarga en todas las implementaciones.

**Encapsulation**
- Proceso de envolver paquetes de red dentro de otros paquetes. Calico admite la encapsulación IPIP y VXLAN para redes de superposición.

### F

**FQDN (Fully Qualified Domain Name)**
- Nombre DNS completo. La función documentada de política de egreso basada en dominios de Calico requiere una edición comercial; las entradas CIDR de un NetworkSet de código abierto no se convierten en reglas DNS. No debe confundirse con la política de capa de aplicación HTTP, que se integra por separado.

**Full Mesh**
- Topología BGP en la que cada uno de los N nodos participantes establece una sesión con todos los demás: N(N−1)/2 sesiones. La capacidad depende de los cambios de topología, las rutas y el hardware; 100 nodos no constituyen un límite universal del protocolo.

### I

**IPAM (IP Address Management)**
- Sistema responsable de asignar, rastrear y administrar direcciones IP. Calico incluye un sistema IPAM integrado que asigna direcciones por bloques.

**IPIP (IP-in-IP)**
- Encapsulación IP. El modo IPv4 IP-in-IP de Calico añade una cabecera IPv4 externa de 20 bytes y requiere que la red subyacente permita el protocolo IP 4; no utiliza un puerto UDP.

**IPset**
- Función del kernel de Linux para almacenar conjuntos de direcciones IP, redes o puertos. Calico utiliza ipsets para comparar tráfico de forma eficiente con varias direcciones.

**iptables**
- Interfaz de espacio de usuario para las reglas de filtrado de paquetes y NAT de Netfilter en Linux. Los backends «legacy» y «nft» de iptables difieren del dataplane Nftables nativo independiente de Calico; cambiar el backend de iptables no selecciona ese dataplane.

### M

**MTU (Maximum Transmission Unit)**
- Tamaño máximo de paquete para un enlace o una ruta. Con una red subyacente efectiva de 1500 bytes, algunos valores de MTU de ejemplo para Calico son 1480 para IPv4 IPIP, 1450/1430 para VXLAN IPv4/IPv6 y 1440/1420 para WireGuard IPv4/IPv6. Utiliza la MTU mínima real de la ruta y el modo elegido, incluidas las restricciones específicas de la plataforma; son cálculos, no mediciones de rendimiento.

### N

**NAT (Network Address Translation)**
- Proceso de modificar la información de direcciones IP en las cabeceras de los paquetes. Calico utiliza NAT para el tráfico de salida de los Pods y la implementación de Services.

**nftables**
- Framework de filtrado de paquetes de Linux que utiliza el modo Nftables nativo de Calico. Es una opción de dataplane de la instalación distinta de Iptables con el backend NFT.

### O

**Overlay Network**
- Red virtual construida sobre una red física existente. Calico admite los modos de superposición IPIP y VXLAN en entornos donde no es posible el enrutamiento directo.

### R

**Route Reflector**
- Dispositivo BGP que refleja rutas a sus clientes. Si hay N nodos en total, incluidos r reflectores completamente interconectados, y cada cliente establece una sesión con los r reflectores, la topología tiene r(N−r)+r(r−1)/2 sesiones. Con N=100 y r=2 hay 197 sesiones, en lugar de las 4950 de una malla completa; un único reflector tiene 99 sesiones, pero no proporciona redundancia de reflectores.

**Routing Table**
- Estructura de datos que almacena rutas a destinos de red. Calico programa las rutas a los CIDR de los Pods en la tabla de enrutamiento del kernel de Linux.

### S

**SNAT (Source NAT)**
- Traducción de direcciones de red que modifica la dirección IP de origen de los paquetes. Se utiliza para el tráfico de salida de los Pods y el enmascaramiento de direcciones.

### V

**veth (Virtual Ethernet)**
- Interfaz virtual Linux emparejada que suele crear el complemento CNI para conectar el espacio de nombres de red de un Pod con el host. Felix no la crea para todos los Pods; los Pods con hostNetwork, Windows y otros tipos de conexión de red tienen un comportamiento distinto.

**VXLAN (Virtual Extensible LAN)**
- Protocolo de encapsulación que extiende redes de capa 2 sobre infraestructura de capa 3. Ofrece mejor compatibilidad con la nube que IPIP, pero añade más sobrecarga.

### W

**WireGuard**
- Protocolo de túnel cifrado que Calico utiliza para el tráfico compatible entre pares de nodos configurados y compatibles. No cifra automáticamente el tráfico entre Pods del mismo nodo, el tráfico de pares no compatibles ni todo el tráfico externo; tampoco equivale a mTLS de aplicación.

**Workload Endpoint**
- Representación de Calico, con ámbito de espacio de nombres, de la interfaz de una carga de trabajo; incluye direcciones, etiquetas y referencias a perfiles que se utilizan en los cálculos de políticas. Normalmente la administra un orquestador o complemento y no constituye una lista almacenada de todas las decisiones de políticas efectivas.

---

## Componentes de Calico

### B

**BIRD (BIRD Internet Routing Daemon)**
- Daemon de enrutamiento utilizado en los perfiles de Calico que usan BGP. La versión 3.32.2 de Calico utiliza la línea de BIRD 1.6.8 con parches propios; una configuración arbitraria de BIRD 2 de upstream no es equivalente.

### C

**calicoctl**
- Herramienta de línea de comandos para administrar recursos de Calico. Se utiliza para consultar el estado, configurar políticas, administrar IPAM y solucionar problemas.

**Calico API Server**
- Integración de API de Calico, distinta del servidor de API de Kubernetes y disponible en la edición de código abierto. La API projectcalico.org/v3 expuesta a los usuarios y los CRD de respaldo o el modo de API nativa dependen de la instalación configurada; sigue la guía de instalación mantenida, en lugar de tratar todos los grupos de API como alias.

**CNI Plugin**
- Binario que implementa la especificación CNI para Calico. Configura la red de los Pods (pares veth, rutas y asignación de direcciones IP).

**confd**
- Herramienta de administración de configuración que genera archivos de configuración de BIRD a partir del datastore de Calico. Observa los cambios y actualiza BIRD dinámicamente.

### D

**Dikastes**
- Componente de decisión de políticas de capa de aplicación que se utiliza con Istio/Envoy. Envoy gestiona el tráfico y solicita autorización a Dikastes; Dikastes no es el proxy que reenvía el tráfico. Esta integración está documentada para Calico de código abierto y tiene requisitos previos específicos de versión.

### F

**Felix**
- Agente por nodo que programa el dataplane seleccionado, las políticas y las rutas pertinentes. El complemento CNI configura las interfaces de los Pods y su IPAM; Felix no reenvía cada paquete en el espacio de usuario.

### G

**Goldmane / Whisker**
- API de agregación de flujos y, respectivamente, interfaz web de código abierto. Su implementación, controles de acceso y estado de vista previa son independientes de las métricas básicas de Felix.

### K

**kube-controllers**
- Controladores de reconciliación de Kubernetes y Calico, incluidas tareas de nodos e IPAM y sincronización que depende del datastore. El conjunto de controladores habilitados depende de la instalación y el datastore; enumerar sus tipos no significa que todos se ejecuten en cada implementación con datastore de Kubernetes.

### T

**Tigera Operator**
- Operador de Kubernetes que administra la instalación y el ciclo de vida de Calico. Proporciona configuración declarativa mediante CRD.

**Typha**
- Servicio de distribución de actualizaciones del datastore y caché que reduce la carga de observación de cada instancia de Felix. Puede utilizar varios tipos de observadores y sincronizadores y varias réplicas; no es un único observador universal para todo el clúster ni un servicio automático de federación de políticas. El capítulo avanzado describe el escalado mediante el operador.

---

## Términos de políticas

### A

**Action**
- Resultado de una regla de Calico: Allow y Deny terminan la evaluación de políticas para esa ruta; Log continúa; Pass delega en el siguiente nivel aplicable y, finalmente, en los perfiles. Log no concede el tráfico por sí solo.

**applyOnForward**
- Opción de GlobalNetworkPolicy para el tráfico reenviado a través de endpoints de host. No crea endpoints de host y es obligatoria con políticas preDNAT/doNotTrack. Las políticas de cargas de trabajo y las de reenvío del host tienen ámbitos distintos.

### D

**Default Deny**
- Postura que deniega el tráfico en un ámbito seleccionado, salvo que el conjunto de políticas efectivas lo permita. Introdúcela con dependencias explícitas y un ámbito de espacio de nombres probado; no utilices una política vacía sin calificar para todo el clúster.

**DoNotTrack**
- La opción doNotTrack de GlobalNetworkPolicy se aplica antes del seguimiento de conexiones al tráfico de endpoints de host y requiere applyOnForward. Las rutas de respuesta sin estado necesitan reglas explícitas; no se puede combinar con preDNAT.

### E

**Egress**
- Tráfico de red saliente de un Pod. Las políticas de egreso controlan con qué destinos se puede comunicar.

### G

**GlobalNetworkPolicy**
- Política de Calico con ámbito de clúster que puede seleccionar cargas de trabajo de varios espacios de nombres o endpoints de host. Sus selectores determinan el ámbito real; tener ámbito de clúster no significa que afecte automáticamente a todos los Pods.

**GlobalNetworkSet**
- Conjunto etiquetado de direcciones IP/CIDR con ámbito de clúster. Los selectores de políticas pueden coincidir con él, incluso desde políticas de Calico con ámbito de espacio de nombres cuando se selecciona el espacio de nombres global adecuado. No se limita a referencias desde GlobalNetworkPolicy.

### H

**Host Endpoint**
- Representación de una interfaz del host que se utiliza para políticas del host y, si se configura, para políticas de tráfico reenviado. Crearlo puede cambiar cómo se gestiona el tráfico; revisa primero las políticas, los perfiles, las reglas de seguridad y el acceso de administración.

### I

**Ingress**
- Tráfico de red entrante a un Pod. Las políticas de ingreso controlan qué orígenes pueden comunicarse con él.

### N

**NetworkPolicy**
- Dos API distintas: la NetworkPolicy networking.k8s.io/v1 de Kubernetes y la NetworkPolicy projectcalico.org/v3 de Calico. Calico añade acciones, orden, niveles y selectores; las reglas HTTP requieren una integración de capa de aplicación compatible e independiente, incluida la integración de Dikastes de código abierto, mientras que las reglas basadas en dominios tienen restricciones de edición.

**NetworkSet**
- Conjunto de direcciones IP o CIDR con ámbito de espacio de nombres. Permite agrupar endpoints externos para utilizarlos en políticas de red.

### O

**Order**
- Prioridad numérica de evaluación: primero el orden de los niveles y, luego, el orden de las políticas dentro de cada nivel. Cuando el orden sea importante, utiliza prioridades distintas y explícitas en vez de depender de empates; una acción terminal anterior puede volver irrelevantes las políticas posteriores.

### P

**Pass**
- Omite el resto de las políticas del nivel actual y continúa en el siguiente nivel aplicable; después del último nivel aplicable, evalúa los perfiles del endpoint. No equivale a una autorización final.

**Profile**
- Etiquetas compartidas heredadas por los endpoints. Los perfiles pueden contener reglas de políticas heredadas, pero ese uso está obsoleto en favor de NetworkPolicy/GlobalNetworkPolicy; no confundas los perfiles con RBAC de Kubernetes.

**Policy Selector**
- Expresión basada en etiquetas que determina a qué endpoints se aplica una política. Utiliza la sintaxis de selectores de Calico (por ejemplo, `app == 'web'`).

**PreDNAT**
- La opción preDNAT de GlobalNetworkPolicy evalúa el tráfico entrante de los endpoints de host antes de NAT de destino. Requiere applyOnForward y no se puede combinar con doNotTrack ni con una dirección de política de egreso.

### S

**Staged Policy**
- Recurso de política que no aplica las reglas y sirve para evaluar cambios propuestos. Las políticas preparadas (staged policies) están disponibles en la edición de código abierto con los requisitos previos documentados para los recursos y la observabilidad; crear una no garantiza por sí mismo un registro de decisiones completo.

**Selector**
- Expresión que coincide con recursos según sus etiquetas. Calico utiliza selectores tanto para los destinos de las políticas como para la comparación de orígenes y destinos.

### T

**Tier**
- Grupo ordenado de políticas. Los niveles con menor valor numérico tienen precedencia. Allow/Deny son terminales, Pass delega y, si en un nivel seleccionado no coincide ninguna regla, se utiliza su defaultAction, que normalmente es Deny.

---

## Términos de operaciones

### A

**APIServer (Calico)**
- Recurso del operador que configura la integración de la API de Calico. No es el plano de control de Kubernetes ni una función exclusiva de Enterprise; el acceso a la API también requiere la ruta de API configurada correctamente y RBAC.

### B

**Block**
- Unidad de asignación de Calico IPAM. Los tamaños predeterminados son IPv4 /26 e IPv6 /122, cada uno con 64 direcciones. Las reservas y restricciones de asignación pueden reducir la capacidad utilizable para cargas de trabajo, especialmente en Windows.

**Block Affinity**
- Asociación entre un bloque de IPAM y su propietario, que normalmente es un nodo. Sin afinidad estricta, las asignaciones aptas pueden tomar direcciones prestadas del bloque de otro nodo. La afinidad no garantiza que todas las direcciones de Pods locales procedan de un bloque propiedad del nodo; inspecciona el tipo y el estado del recurso y el asignador real.

### D

**Dataplane**
- Implementación que procesa paquetes. Calico ofrece Iptables, Nftables y BPF en Linux, además de configuraciones HNS compatibles con Windows; otras integraciones tienen sus propios requisitos.

**Datastore**
- Acceso al almacenamiento y a la API para la configuración y el estado de Calico, mediante el datastore de la API de Kubernetes o implementaciones directas de etcdv3 compatibles. Se recomienda el datastore de Kubernetes; funciones como BPF tienen restricciones adicionales de datastore.

### F

**FelixConfiguration**
- Recurso de API para la configuración de Felix, incluidos los valores predeterminados del clúster y las anulaciones por nodo compatibles. Controla opciones de métricas, registro y dataplane; no sustituye a la API Installation del operador.

**Flow Logs**
- Registros agregados de flujos de conexión, distintos de las capturas de paquetes o los registros de procesos. Las instalaciones actuales de OSS con operador o Helm pueden utilizar Goldmane y Whisker; la guía de registros de flujos indica que la función está en vista previa técnica.

### H

**Health Check**
- Informes de actividad y disponibilidad de los componentes. Felix puede exponer endpoints de estado en su puerto configurado (9099 de forma predeterminada); el estado de un componente no demuestra que la aplicación sea accesible ni que se apliquen correctamente las políticas.

### I

**IPPool**
- Recurso independiente de Calico que define un rango de direcciones, la encapsulación, NAT y los criterios de asignación. IPAM de Calico puede asignar direcciones para usos compatibles de cargas de trabajo, túneles y balanceadores de carga; el pool no es un alias del PodCIDR de un nodo de Kubernetes. CIDR y blockSize son inmutables.

**Installation**
- CRD del operador de Tigera que define la configuración de implementación de Calico. Especifica el modo de red, los recursos y la configuración de componentes.

### M

**Metrics**
- Estadísticas de Prometheus cuya activación y puertos dependen del componente. Felix utiliza 9091 de forma predeterminada; Typha también utiliza 9091 de forma predeterminada, aunque suele configurarse explícitamente en 9093; kube-controllers utiliza 9094 de forma predeterminada. Consulta los valores reales y los tipos de métricas.

### P

**Pod CIDR**
- Rango de direcciones de Pods que puede describir el rango del clúster o una asignación a un nodo de Kubernetes. Un IPPool de Calico es un objeto separado; su relación con los PodCIDR de los nodos depende de IPAM. Con VPC CNI, Calico en modo exclusivo de políticas no asigna direcciones IP a los Pods.

### R

**Rollout**
- Actualización controlada de un componente. La reconciliación del operador y la configuración de actualizaciones graduales ayudan a administrar la disponibilidad, pero no garantizan tráfico ininterrumpido ni que se puedan revertir los cambios de esquema o datos.

### T

**TigeraStatus**
- CRD que informa del estado de los componentes de Calico. Muestra el estado de la implementación y de la configuración.

---

## Terminología de Calico frente a Kubernetes

| Término de Kubernetes | Equivalente en Calico | Notas |
|-----------------|-------------------|-------|
| NetworkPolicy | NetworkPolicy de Calico | Grupos de API y recursos distintos, con semánticas de reglas diferentes |
| - | GlobalNetworkPolicy | Política para todo el clúster (específica de Calico) |
| - | Tier | Jerarquía de políticas (específica de Calico) |
| Service CIDR | N/A | Calico respeta el Service CIDR de Kubernetes |
| Pod CIDR | IPPool cuando se utiliza IPAM de Calico | No es un alias ni coincide automáticamente con los PodCIDR de los nodos |
| Node | Calico Node | Datos de nodo relacionados; su ciclo de vida y representación dependen del datastore |
| Namespace | Namespace | Las políticas de Calico pueden seleccionar por espacio de nombres |
| Labels | Labels | La misma sintaxis de etiquetas, utilizada en selectores |
| Interfaz de red del Pod | WorkloadEndpoint | No es un Service Endpoint/EndpointSlice ni una lista completa de las políticas aplicadas |
| - | HostEndpoint | Políticas para interfaces del host (específicas de Calico) |

---

## Terminología de Calico frente a Cilium

Estas son comparaciones funcionales; no implican que los recursos sean intercambiables ni que las funciones estén garantizadas. Antes de migrar políticas, comprueba el modo, la plataforma y la versión instalada.

| Concepto | Calico | Comparación con Cilium 1.20.1 |
| --- | --- | --- |
| Agente del nodo | Felix | Cilium Agent |
| BGP | BIRD en perfiles con BGP habilitado | El plano de control BGP integrado anuncia la alcanzabilidad; no programa el datapath ni establece el enrutamiento interno |
| Distribución del datastore | Typha | No hay un componente ni una API de Typha equivalentes |
| Asignación de IP de Pods | IPPool + IPAM seleccionado | Depende del modo de IPAM de Cilium; no hay un único API de pool universal |
| Política con ámbito de espacio de nombres | NetworkPolicy de Calico | CiliumNetworkPolicy; ambas difieren de la NetworkPolicy estándar de Kubernetes |
| Política de clúster | GlobalNetworkPolicy | CiliumClusterwideNetworkPolicy; difieren la semántica de reglas y el orden |
| CIDR externos reutilizables | NetworkSet / GlobalNetworkSet | CiliumCIDRGroup con ámbito de clúster, referenciado por cidrGroupRef o cidrGroupSelector en reglas CIDR; no es CiliumIPSet |
| Niveles de políticas | Tier de Calico | No hay una API de Tier equivalente a la de Calico; las demás API de políticas tienen sus propias reglas de orden |
| Interfaz de carga de trabajo | WorkloadEndpoint | CiliumEndpoint, con distinta semántica de ciclo de vida y estado |
| Protección del host | Políticas de HostEndpoint, incluidas reglas de reenvío configuradas | Firewall de host de Linux con políticas nodeSelector; el ámbito de reenvío no es idéntico |
| Dataplane | Iptables/Nftables/BPF en Linux; HNS en Windows | Requisitos de eBPF en Linux; no describas Windows como una versión beta compatible basándote en esta comparación |
| Cifrado | WireGuard de código abierto para rutas compatibles entre pares | WireGuard o IPsec, con límites según el modo y la plataforma |
| Política L7 | Integración independiente de Istio/Envoy/Dikastes documentada para OSS | Funciones de políticas basadas en Envoy con sus propios requisitos previos |
| Visibilidad de flujos | Goldmane/Whisker y métricas de componentes | Hubble y métricas de componentes |
| Controladores | kube-controllers / Tigera Operator | Cilium Operator; sus responsabilidades no tienen correspondencia uno a uno |
| CLI | calicoctl | cilium y cilium-dbg del agente tienen funciones distintas |

El conjunto de funciones de Calico compatibles con Windows es más limitado que el de Linux: por ejemplo, HNS IPv4 con los límites documentados para VXLAN/BGP, no paridad con WireGuard, eBPF ni HostEndpoint. Esta comparación no aporta pruebas para hacer afirmaciones incondicionales sobre rendimiento, madurez o tamaño de la comunidad. Compara una carga de trabajo y un requisito operativo concretos.

---

## Referencias cruzadas

### Análisis detallado de la arquitectura
- **Felix**: consulta [Parte 2: Arquitectura](02-architecture.md)
- **Configuración de BGP**: consulta [Parte 4: Análisis detallado de BGP](04-bgp-deep-dive.md)
- **Escalado de Typha**: consulta [Parte 7: Temas avanzados](07-advanced-topics.md)

### Política de red
- **NetworkPolicy de Kubernetes**: consulta [Parte 5: Política de red](05-network-policy.md)
- **GlobalNetworkPolicy**: consulta [Parte 5: Política de red](05-network-policy.md)
- **Políticas basadas en niveles**: consulta [Parte 5: Política de red](05-network-policy.md)

### Operaciones
- **Métodos de instalación**: consulta [Parte 9: Operaciones](09-operations.md)
- **Comandos de calicoctl**: consulta [Parte 9: Operaciones](09-operations.md)
- **Solución de problemas**: consulta [Parte 9: Operaciones](09-operations.md)

### Integración con EKS
- **VPC CNI + Calico**: consulta [Parte 8: Integración con EKS](08-eks-integration.md)
- **Métodos de instalación**: consulta [Parte 8: Integración con EKS](08-eks-integration.md)

---

## Referencias principales

- [Referencia de recursos de Calico](https://docs.tigera.io/calico/latest/reference/resources/)
- [Niveles de Calico](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [MTU de Calico](https://docs.tigera.io/calico/latest/networking/configuring/mtu)
- [ASN privados de RFC 6996](https://www.rfc-editor.org/rfc/rfc6996.txt)
- [API de grupos CIDR de Cilium](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/v2/cidrgroups_types.go)
- [Plano de control BGP de Cilium](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Firewall de host de Cilium](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/host-firewall.rst)

## Cuestionario

Para comprobar lo que aprendiste en este capítulo, prueba el [Cuestionario del glosario](../../quizzes/networking/calico/glossary-quiz.md).
