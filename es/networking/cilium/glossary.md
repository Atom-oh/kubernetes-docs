# Glosario y abreviaturas

> **Referencia de revisión**: Cilium 1.20.2.
> **Última actualización**: October 15, 2026.

Una referencia alfabética para Cilium, eBPF, Kubernetes y redes. Las entradas repetidas se consolidan.

## A

**API (Application Programming Interface)** - General

- Un conjunto de definiciones de interfaz que permiten la comunicación entre aplicaciones

**ARP (Address Resolution Protocol)** - Redes

- Resuelve una dirección IPv4 en una dirección de capa de enlace en el enlace local, normalmente una dirección MAC Ethernet.
- Para un destino remoto, un host resuelve su siguiente salto. IPv6 usa Neighbor Discovery en lugar de ARP.

**AWS ENI (Elastic Network Interface)** - Redes

- Interfaz de red virtual proporcionada por Amazon Web Services
- Se utiliza en el modo AWS ENI IPAM de Cilium

## B

**BGP (Border Gateway Protocol)** - Redes

- Un protocolo de enrutamiento entre dominios que se utiliza para anunciar la accesibilidad entre pares.
- Cilium BGP Control Plane anuncia los prefijos seleccionados; no es un modo de enrutamiento nativo ni programa las rutas del datapath local.

**BPF (Berkeley Packet Filter)** - eBPF

- Tecnología para el filtrado de paquetes, predecesora de eBPF
- Desarrollada originalmente para la captura de paquetes de red

**BPF Maps** - eBPF

- Estructuras de datos administradas por el kernel que utilizan los programas BPF y el espacio de usuario para compartir estado o eventos.
- Muchos tipos usan claves y valores; los búferes circulares, las colas y las pilas tienen operaciones distintas. Un búfer circular BPF no admite la búsqueda/actualización/eliminación de mapas.

## C

**CGroup (Control Group)** - Kubernetes

- Los grupos de control de Linux organizan procesos y contabilizan o controlan recursos como CPU y memoria.
- Los entornos de ejecución de contenedores usan cgroups; por sí mismos, no constituyen aislamiento de espacios de nombres de procesos/red.

**CIDR (Classless Inter-Domain Routing)** - Redes

- Método para la asignación de direcciones IP y la agregación de enrutamiento
- Ejemplo: 192.168.1.0/24 representa el rango de direcciones IP de 192.168.1.0 a 192.168.1.255

**Cilium** - Cilium

- Solución de redes, seguridad y observabilidad de código abierto basada en eBPF
- Se utiliza como una implementación de Kubernetes CNI

**Cilium Agent** - Cilium

- El componente local del nodo de Cilium que administra endpoints, programas BPF y el estado de políticas/datapath. Se ejecuta en nodos aptos administrados por Cilium.

**Cilium Operator** - Cilium

- El controlador a nivel de clúster para tareas como el registro de CRD, IPAM/LB IPAM según el modo, recolección de basura y controladores Ingress/Gateway habilitados.
- El número de réplicas es configurable. La administración opcional de identidades y la sincronización de ClusterMesh dependen de las funciones habilitadas; no es el componente de reenvío de paquetes del nodo.

**ClusterMesh** - Cilium

- Funciones de metadatos/conectividad de red multiclúster de Cilium para descubrimiento de servicios, balanceo de carga y políticas de identidad remota.
- Requiere direccionamiento, confianza y rutas accesibles compatibles; no proporciona almacenamiento compartido ni replica automáticamente todos los recursos de políticas.

**CNI (Container Network Interface)** - Kubernetes

- Container Network Interface: una especificación y complementos para configurar la conectividad de red de contenedores.
- En Kubernetes actual, el entorno de ejecución de contenedores CRI carga/invoca complementos CNI. Los indicadores anteriores de administración directa de CNI de kubelet se eliminaron en Kubernetes 1.24.

**CoreDNS** - Kubernetes

- Servidor DNS utilizado habitualmente en clústeres de Kubernetes
- Desempeña un papel importante en el descubrimiento de servicios

**CRD (Custom Resource Definition)** - Kubernetes

- Método para definir recursos personalizados mediante la extensión de la API de Kubernetes
- Cilium usa CRD para definir políticas de red, etc.

## D

**DaemonSet**

- Un controlador de Kubernetes que ejecuta Pods de daemon en nodos aptos seleccionados por sus restricciones de programación; no tiene por qué cubrir todos los nodos.

**DNAT (Destination Network Address Translation)** - Redes

- Tipo de NAT que modifica la dirección IP de destino de los paquetes
- Se utiliza para el balanceo de carga y el reenvío de puertos

**DNS (Domain Name System)** - Redes

- Un sistema distribuido de nombres que publica registros como direcciones A/AAAA, alias CNAME e información de servicios SRV.
- La política DNS de Cilium y la política FQDN de IP aprendidas son controles relacionados pero distintos.

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF

- Extended Berkeley Packet Filter: hooks programables del kernel e infraestructura asociada utilizada por Cilium.
- El verificador comprueba las propiedades del programa antes de aceptarlo. No garantiza que las implementaciones del kernel o del verificador estén libres de vulnerabilidades.

**Endpoint** - Cilium

- Un endpoint de red administrado por Cilium, normalmente un Pod, con estado local de datapath/políticas.
- Su ID de endpoint es local para el agente y es distinto de una identidad de seguridad compartida por varios endpoints.

**Envoy** - Cilium

- Un proxy de código abierto utilizado por Cilium para políticas HTTP/gRPC configuradas, visibilidad L7 y enrutamiento de servicios basado en proxy.
- La política DNS usa el proxy DNS de Cilium. La política Kafka L7 ya no es compatible; no todas las reglas L7 implementan automáticamente una instancia de Envoy.

## F

**FQDN (Fully Qualified Domain Name)**

- Fully Qualified Domain Name: un nombre absoluto que identifica su posición completa en el árbol DNS, a menudo escrito con el punto final de raíz, por ejemplo `www.example.com.`.
- `toFQDNs` de Cilium permite direcciones IP de destino aprendidas. Por sí solo, no autentica un servidor HTTPS ni restringe todos los valores HTTP Host en una IP compartida.

## G

**GENEVE (Generic Network Virtualization Encapsulation)**

- Protocolo de encapsulación para virtualización de red

**gRPC (gRPC Remote Procedure Call)**

- Marco de RPC (Remote Procedure Call) de alto rendimiento desarrollado por Google

## H

**Hubble** - Cilium

- Capa de observabilidad de red de Cilium: eventos de flujo, metadatos de protocolos compatibles, métricas e interfaces de consulta.
- El historial es limitado y las observaciones pueden perderse o filtrarse. Las alertas, el almacenamiento duradero y la respuesta automatizada requieren integraciones configuradas.

## I

**Identity** - Cilium

- Un identificador de seguridad numérico derivado de etiquetas relevantes para la seguridad. Varios endpoints pueden compartirlo dentro del ámbito de asignación aplicable.
- El campo `security-labels` de CiliumIdentity es la fuente de verdad en el modo de asignación CRD. Las identidades reservadas y locales al nodo no están todas representadas por estos objetos con ámbito de clúster.

**IPAM (IP Address Management)** - Redes

- IP Address Management: asignación, seguimiento y recuperación de direcciones.
- Los modos de Cilium tienen distintos propietarios de asignación y fuentes de datos, incluidos modos específicos para cluster-pool, multi-pool, ámbito de host de Kubernetes y nube. El nombre de una plataforma no necesariamente es un valor `ipam.mode` independiente.

**IPsec** - Redes

- Internet Protocol Security: un conjunto de mecanismos para la autenticación/integridad de la capa IP y, con la configuración adecuada, la confidencialidad.
- Cilium utiliza IPsec para el cifrado compatible del tráfico entre nodos; la administración de claves y las limitaciones específicas de la ruta siguen aplicando.

**Istio**

- Plataforma de código abierto que implementa service mesh

## K

**Kafka**

- Una plataforma distribuida de transmisión de eventos. Sigue siendo una carga de trabajo posible, pero Cilium actual no proporciona la antigua API de políticas Kafka topic L7.

**kube-proxy** - Kubernetes

- Un componente de Kubernetes que implementa el reenvío de IP/puerto virtual de Service mediante mecanismos de red de nodo compatibles.
- Cilium puede reemplazar esta función con eBPF; la aceleración XDP es opcional y la plataforma debe admitir la configuración elegida.

**Kubernetes**

- Plataforma de código abierto que automatiza la implementación, el escalado y la administración de aplicaciones en contenedores

## L

**L2 (Layer 2)**

- Capa de enlace de datos del modelo OSI

**L3 (Layer 3)**

- Capa de red del modelo OSI

**L4 (Layer 4)**

- Capa de transporte del modelo OSI

**L7 (Layer 7)**

- Capa de aplicación del modelo OSI

**LoadBalancer**

- Una función de distribución de tráfico. Kubernetes `type: LoadBalancer` solicita una implementación a un controlador/proveedor; no se garantiza un balanceador de carga externo sin uno.

## M

**MAC (Media Access Control) Address**

- Dirección Media Access Control: una dirección de capa de enlace asociada con una interfaz.
- Las direcciones pueden administrarse localmente o cambiarse; no se debe asumir su unicidad ni autenticidad.

**mTLS (mutual TLS)**

- Mutual TLS: TLS en el que ambos pares se autentican, normalmente validando los certificados del otro.
- La autenticación de pares es distinta de la autorización de aplicaciones. La autenticación mutua fuera de banda de Cilium y el mTLS de carga de trabajo ztunnel Beta son funciones independientes con diferentes propiedades de protección del tráfico.

**MTU (Maximum Transmission Unit)**

- Maximum Transmission Unit: el paquete de capa de red más grande transportado en un enlace/interfaz sin fragmentación, incluido su encabezado IP pero no el encabezado de capa de enlace.
- La MTU de ruta está limitada por la ruta; la sobrecarga de túnel/cifrado afecta al tamaño utilizable del paquete interno. No es TCP MSS ni el tamaño de la carga útil de la aplicación.

## N

**NAT (Network Address Translation)**

- Proceso de modificar la información de dirección IP en paquetes IP

**NodePort**

- Un método de exposición de Service de Kubernetes que utiliza un puerto de nodo asignado en direcciones de nodos aptos.
- La selección de direcciones, la política de tráfico, el firewall y el enrutamiento de la plataforma determinan la accesibilidad; declarar un NodePort no garantiza acceso público.

## O

**OSI (Open Systems Interconnection) Model**

- Modelo conceptual que clasifica la comunicación de red en 7 capas abstractas

**Overlay Network**

- Red virtual construida sobre una red existente

## P

**Pod**

- La unidad informática implementable más pequeña en Kubernetes

**Proxy**

- Un componente que media la comunicación entre pares; no tiene por qué ser un servidor físico independiente.

## R

**RBAC (Role-Based Access Control)**

- Método para controlar el acceso a recursos del sistema según roles

## S

**Service**

- Una abstracción de Kubernetes para acceder a un conjunto lógico de backends, a menudo Pods seleccionados por etiquetas.
- Los Services ClusterIP ordinarios tienen una IP virtual; los Services sin encabezado no. ExternalName usa alias DNS, y los Services sin selector pueden usar EndpointSlices administrados manualmente.

**SNAT (Source Network Address Translation)**

- Tipo de NAT que modifica la dirección IP de origen de los paquetes

**Socket**

- Un endpoint de comunicación del sistema operativo utilizado para comunicación de red o local entre procesos.

## T

**TCP (Transmission Control Protocol)**

- Protocolo de transporte orientado a conexión que proporciona flujos de bytes fiables

**TLS (Transport Layer Security)**

- Protocolo criptográfico que protege la comunicación a través de redes

## U

**UDP (User Datagram Protocol)**

- Protocolo de transporte sin conexión

## V

**VETH (Virtual Ethernet)**

- Dispositivo ethernet virtual, normalmente creado en pares

**VNI (VXLAN Network Identifier)**

- VXLAN Network Identifier: un campo de 24 bits en el encabezado VXLAN.
- Cilium puede transportar información de identidad en metadatos de superposición; el ancho del campo no promete millones de redes de tenants configuradas de forma independiente.

**VTEP (VXLAN Tunnel Endpoint)**

- Endpoint responsable de la encapsulación y desencapsulación de paquetes VXLAN

**VXLAN (Virtual Extensible LAN)** - Redes

- Tecnología de virtualización de red que superpone redes de Layer 2 sobre redes de Layer 3
- Uno de los modos de redes superpuestas de Cilium

## W

**WireGuard** - Redes

- Un protocolo de túnel VPN utilizado por Cilium para tráfico compatible entre nodos.
- El tráfico de Pod en el mismo nodo no está cifrado por su túnel de nodo; el tráfico externo y el cifrado de nodo opcional tienen límites independientes. El rendimiento relativo a IPsec requiere una medición comparable.

## X

**XDP (eXpress Data Path)** - eBPF

- eXpress Data Path: un hook de procesamiento de paquetes; XDP nativo se ejecuta en la ruta de recepción de un controlador de red compatible.
- PASS continúa en la pila de red; otras acciones pueden descartar, transmitir o redirigir. La aceleración XDP compatible de Cilium es opcional, no una garantía universal de rendimiento o protección contra DDoS.

## Referencias principales

- [Identidades de Cilium](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/internals/security-identities.rst)
- [Esquema CiliumIdentity](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumidentities.yaml)
- [Cilium Operator](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/internals/cilium_operator.rst)
- [Modos de administración de identidades](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/kubernetes/identity-management-mode.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-wireguard.rst)
- [BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Kubernetes CNI/CRI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html)
- [ARP / RFC 826](https://www.rfc-editor.org/rfc/rfc826.txt)
- [IPv6 Neighbor Discovery / RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.txt)
- [VXLAN / RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)
- [Direccionamiento MAC / RFC 7042](https://www.rfc-editor.org/rfc/rfc7042.txt)

## Cuestionario

[Cuestionario del tema](../../quizzes/networking/cilium/glossary-quiz.md)
