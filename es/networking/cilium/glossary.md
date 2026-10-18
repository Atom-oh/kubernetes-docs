# Glosario y abreviaturas

> **Referencia de versión**: Cilium 1.20.3.
> **Última revisión**: 16 de octubre de 2026.

Referencia alfabética de Cilium, eBPF, Kubernetes y redes. Las entradas duplicadas se consolidaron.

## A

**API (Application Programming Interface)** - General

- Conjunto de definiciones de interfaces que permiten la comunicación entre aplicaciones.

**ARP (Address Resolution Protocol)** - Redes

- Resuelve una dirección IPv4 en una dirección de capa de enlace del enlace local, normalmente una dirección MAC de Ethernet.
- Para un destino remoto, el host resuelve el siguiente salto. IPv6 utiliza Neighbor Discovery en lugar de ARP.

**AWS ENI (Elastic Network Interface)** - Redes

- Interfaz de red virtual proporcionada por Amazon Web Services.
- Se utiliza en el modo IPAM de Cilium basado en AWS ENI.

## B

**BGP (Border Gateway Protocol)** - Redes

- Protocolo de enrutamiento entre dominios que se usa para anunciar alcance de red entre pares.
- Cilium BGP Control Plane anuncia prefijos seleccionados; no es un modo de enrutamiento nativo ni programa las rutas del plano de datos local.

**BPF (Berkeley Packet Filter)** - eBPF

- Tecnología de filtrado de paquetes que precedió a eBPF.
- Se desarrolló originalmente para capturar paquetes de red.

**BPF Maps** - eBPF

- Estructuras de datos administradas por el kernel que los programas BPF y los procesos de espacio de usuario utilizan para compartir estado o eventos.
- Muchos tipos usan claves y valores; los búferes circulares, las colas y las pilas tienen operaciones distintas. Un BPF ring buffer no admite map lookup/update/delete.

## C

**CGroup (Control Group)** - Kubernetes

- Los grupos de control de Linux organizan procesos y contabilizan o controlan recursos como CPU y memoria.
- Los runtimes de contenedores utilizan cgroups; por sí solos, estos no proporcionan aislamiento de espacios de nombres de procesos ni de red.

**CIDR (Classless Inter-Domain Routing)** - Redes

- Método de asignación de direcciones IP y agregación de rutas.
- Ejemplo: 192.168.1.0/24 representa el rango de direcciones IP desde 192.168.1.0 hasta 192.168.1.255.

**Cilium** - Cilium

- Solución de redes, seguridad y observabilidad de código abierto basada en eBPF.
- Se utiliza como implementación de CNI para Kubernetes.

**Cilium Agent** - Cilium

- Componente de Cilium local al nodo que administra endpoints, programas BPF y el estado de las políticas y del plano de datos. Se ejecuta en los nodos aptos administrados por Cilium.

**Cilium Operator** - Cilium

- Controlador a nivel de clúster para tareas como registrar CRD, gestionar IPAM y la asignación de direcciones para LoadBalancer según el modo, realizar la recolección de basura y habilitar los controladores de Ingress/Gateway.
- El número de réplicas es configurable. La administración opcional de identidades y la sincronización de ClusterMesh dependen de las funciones habilitadas; este componente no reenvía los paquetes de los nodos.

**ClusterMesh** - Cilium

- Funciones de conectividad y metadatos de red multiclúster de Cilium para descubrimiento de servicios, balanceo de carga y políticas basadas en identidades remotas.
- Requiere direccionamiento compatible, confianza y rutas accesibles; no proporciona almacenamiento compartido ni replica automáticamente todos los recursos de políticas.

**CNI (Container Network Interface)** - Kubernetes

- Especificación y conjunto de plugins para configurar la conectividad de red de contenedores.
- En las versiones actuales de Kubernetes, el runtime de contenedores CRI carga e invoca los plugins CNI. Las opciones de kubelet que antes administraban CNI directamente se eliminaron en Kubernetes 1.24.

**CoreDNS** - Kubernetes

- Servidor DNS que se utiliza habitualmente en clústeres de Kubernetes.
- Desempeña un papel importante en el descubrimiento de servicios.

**CRD (Custom Resource Definition)** - Kubernetes

- Método para definir recursos personalizados mediante la ampliación de la API de Kubernetes.
- Cilium usa CRD para definir, entre otras cosas, políticas de red.

## D

**DaemonSet**

- Controlador de Kubernetes que ejecuta Pods daemon en los nodos aptos que seleccionan sus restricciones de planificación; no es necesario que abarque todos los nodos.

**DNAT (Destination Network Address Translation)** - Redes

- Tipo de NAT que modifica la dirección IP de destino de los paquetes.
- Se utiliza para el balanceo de carga y el reenvío de puertos.

**DNS (Domain Name System)** - Redes

- Sistema de nombres distribuido que publica registros como direcciones A/AAAA, alias CNAME e información de servicios SRV.
- La política DNS de Cilium y la política FQDN, que se basa en las IP de destino aprendidas, están relacionadas, pero son controles distintos.

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF

- Hooks de kernel programables e infraestructura asociada que utiliza Cilium.
- El verificador comprueba las propiedades del programa antes de aceptarlo. Esto no garantiza que las implementaciones del kernel o del verificador estén libres de vulnerabilidades.

**Endpoint** - Cilium

- Endpoint de red administrado por Cilium, normalmente un Pod, con estado local del plano de datos y de las políticas.
- Su ID de endpoint es local al agente y distinto de una identidad de seguridad que pueden compartir varios endpoints.

**Envoy** - Cilium

- Proxy de código abierto que Cilium utiliza para políticas HTTP/gRPC configuradas, visibilidad de capa 7 y enrutamiento de servicios mediante proxy.
- La política DNS utiliza el proxy DNS de Cilium. La política Kafka de capa 7 ya no está admitida; no toda regla de capa 7 despliega automáticamente una instancia de Envoy.

## F

**FQDN (Fully Qualified Domain Name)**

- Nombre absoluto que identifica su posición completa en el árbol DNS y que suele escribirse con el punto final de la raíz; por ejemplo, `www.example.com.`.
- `toFQDNs` de Cilium permite usar las IP de destino aprendidas. Por sí solo, no autentica un servidor HTTPS ni restringe todos los valores de HTTP Host que comparten una IP.

## G

**GENEVE (Generic Network Virtualization Encapsulation)**

- Protocolo de encapsulación para la virtualización de redes.

**gRPC (gRPC Remote Procedure Call)**

- Framework RPC (Remote Procedure Call) de alto rendimiento desarrollado por Google.

## H

**Hubble** - Cilium

- Capa de observabilidad de red de Cilium: eventos de flujo, metadatos de protocolos compatibles, métricas e interfaces de consulta.
- El historial es limitado y algunas observaciones pueden perderse o filtrarse. Las alertas, el almacenamiento duradero y la respuesta automatizada requieren integraciones configuradas.

## I

**Identity** - Cilium

- Identificador numérico de seguridad derivado de etiquetas relevantes para la seguridad. Varios endpoints pueden compartirlo dentro del ámbito de asignación correspondiente.
- En el modo de asignación basado en CRD, el campo `security-labels` de CiliumIdentity es la fuente de verdad. Las identidades reservadas y locales al nodo no están representadas en su totalidad por estos objetos de ámbito de clúster.

**IPAM (IP Address Management)** - Redes

- Asignación, seguimiento y recuperación de direcciones IP.
- Los modos de Cilium tienen distintos responsables de asignación y fuentes de datos, entre ellos cluster-pool, multi-pool, host-scope de Kubernetes y modos específicos de la nube. El nombre de una plataforma no necesariamente corresponde a un valor independiente de `ipam.mode`.

**IPsec** - Redes

- Conjunto de mecanismos para autenticación e integridad en la capa IP y, con la configuración adecuada, confidencialidad.
- Cilium utiliza IPsec para cifrar el tráfico entre nodos compatible; siguen aplicándose los requisitos de administración de claves y las limitaciones específicas de cada ruta.

**Istio**

- Plataforma de código abierto que implementa una malla de servicios.

## K

**Kafka**

- Plataforma distribuida de transmisión de eventos. Sigue siendo una carga de trabajo posible, pero las versiones actuales de Cilium ya no ofrecen la API anterior de políticas Kafka de capa 7 por tema.

**kube-proxy** - Kubernetes

- Componente de Kubernetes que reenvía las direcciones IP virtuales y los puertos de Service mediante mecanismos de red de nodo compatibles.
- Cilium puede sustituir esta función con eBPF. La aceleración XDP es opcional y la plataforma debe admitir la configuración elegida.

**Kubernetes**

- Plataforma de código abierto que automatiza el despliegue, el escalado y la administración de aplicaciones en contenedores.

## L

**L2 (Layer 2)**

- Capa de enlace de datos del modelo OSI.

**L3 (Layer 3)**

- Capa de red del modelo OSI.

**L4 (Layer 4)**

- Capa de transporte del modelo OSI.

**L7 (Layer 7)**

- Capa de aplicación del modelo OSI.

**LoadBalancer**

- Función de distribución de tráfico. Un Service de Kubernetes con `type: LoadBalancer` solicita una implementación a un controlador o proveedor; sin uno, no se garantiza un balanceador de carga externo.

## M

**MAC (Media Access Control) Address**

- Dirección de capa de enlace asociada a una interfaz.
- Las direcciones pueden administrarse localmente o cambiar; no se debe dar por sentada su unicidad ni autenticidad.

**mTLS (mutual TLS)**

- TLS mutuo, en el que ambos pares se autentican, normalmente validando los certificados del otro.
- La autenticación de pares es distinta de la autorización de aplicaciones. La autenticación mutua fuera de banda de Cilium y mTLS para cargas de trabajo con ztunnel —en estado Beta— son funciones independientes con propiedades distintas de protección del tráfico.

**MTU (Maximum Transmission Unit)**

- Paquete más grande de la capa de red que puede transportarse por un enlace/interfaz sin fragmentación; incluye su encabezado IP, pero no el encabezado de capa de enlace.
- La MTU de ruta depende del camino; la sobrecarga de túneles o cifrado afecta el tamaño utilizable del paquete interno. No es el MSS de TCP ni el tamaño de la carga útil de la aplicación.

## N

**NAT (Network Address Translation)**

- Proceso de modificar la información de direcciones IP en paquetes IP.

**NodePort**

- Método de exposición de un Service de Kubernetes mediante un puerto de nodo asignado en las direcciones aptas de los nodos.
- La selección de direcciones, la política de tráfico, el firewall y el enrutamiento de la plataforma determinan la conectividad; declarar un NodePort no garantiza acceso público.

## O

**OSI (Open Systems Interconnection) Model**

- Modelo conceptual que clasifica la comunicación de red en 7 capas abstractas.

**Overlay Network**

- Red virtual construida sobre una red existente.

## P

**Pod**

- Unidad de cómputo más pequeña que se puede desplegar en Kubernetes.

**Proxy**

- Componente que media la comunicación entre pares; no tiene por qué ser un servidor físico independiente.

## R

**RBAC (Role-Based Access Control)**

- Método para controlar el acceso a los recursos del sistema según los roles.

## S

**Service**

- Abstracción de Kubernetes para acceder a un conjunto lógico de backends, a menudo Pods seleccionados por etiquetas.
- Los Services ClusterIP ordinarios tienen una IP virtual; los Services headless no. ExternalName usa alias DNS y los Services sin selector pueden utilizar EndpointSlices administrados manualmente.

**SNAT (Source Network Address Translation)**

- Tipo de NAT que modifica la dirección IP de origen de los paquetes.

**Socket**

- Endpoint de comunicación del sistema operativo para comunicaciones de red o entre procesos locales.

## T

**TCP (Transmission Control Protocol)**

- Protocolo de transporte orientado a conexión que proporciona flujos de bytes fiables.

**TLS (Transport Layer Security)**

- Protocolo criptográfico que protege las comunicaciones a través de redes.

## U

**UDP (User Datagram Protocol)**

- Protocolo de transporte sin conexión.

## V

**VETH (Virtual Ethernet)**

- Dispositivo Ethernet virtual que normalmente se crea en pares.

**VNI (VXLAN Network Identifier)**

- Campo de 24 bits en el encabezado VXLAN.
- Cilium puede transportar información de identidad en los metadatos del overlay; el ancho de este campo no promete millones de redes de inquilinos configuradas de forma independiente.

**VTEP (VXLAN Tunnel Endpoint)**

- Endpoint responsable de encapsular y desencapsular paquetes VXLAN.

**VXLAN (Virtual Extensible LAN)** - Redes

- Tecnología de virtualización de redes que superpone redes de capa 2 sobre redes de capa 3.
- Uno de los modos de red overlay de Cilium.

## W

**WireGuard** - Redes

- Protocolo de túnel VPN que Cilium utiliza para el tráfico compatible entre nodos.
- El tráfico de Pods en el mismo nodo no se cifra mediante el túnel de nodo; el tráfico externo y el cifrado opcional de nodos tienen limitaciones distintas. Para comparar el rendimiento con IPsec se necesitan mediciones comparables.

## X

**XDP (eXpress Data Path)** - eBPF

- Hook de procesamiento de paquetes; XDP nativo se ejecuta en la ruta de recepción de un controlador de red compatible.
- PASS continúa hacia la pila de red; otras acciones pueden descartar, transmitir o redirigir el paquete. La aceleración XDP compatible con Cilium es opcional y no garantiza un rendimiento universal ni protección contra DDoS.

## Referencias principales

- [Identidades de Cilium](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/internals/security-identities.rst)
- [Esquema de CiliumIdentity](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumidentities.yaml)
- [Cilium Operator](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/internals/cilium_operator.rst)
- [Modos de administración de identidades](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/kubernetes/identity-management-mode.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-wireguard.rst)
- [BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [CNI/CRI de Kubernetes](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Services de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html)
- [ARP / RFC 826](https://www.rfc-editor.org/rfc/rfc826.txt)
- [Neighbor Discovery de IPv6 / RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.txt)
- [VXLAN / RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)
- [Direcciones MAC / RFC 7042](https://www.rfc-editor.org/rfc/rfc7042.txt)

## Cuestionario

[Cuestionario del tema](../../quizzes/networking/cilium/glossary-quiz.md)
