# Glosario y abreviaturas

> **Última actualización**: February 22, 2026

Este documento proporciona explicaciones de términos clave y abreviaturas relacionadas con Cilium. Este glosario ayuda a comprender los conceptos de Cilium, eBPF, Kubernetes y redes.

## Categorías de términos

Los términos se clasifican en las siguientes categorías:
- Azul: **términos relacionados con Cilium**
- Naranja: **términos relacionados con eBPF**
- Verde: **términos relacionados con Kubernetes**
- Morado: **términos relacionados con redes**
- Blanco: **términos generales**

## A

**API (Application Programming Interface)** - General
- Conjunto de definiciones de interfaz que permiten la comunicación entre aplicaciones

**AWS ENI (Elastic Network Interface)** - Networking
- Interfaz de red virtual proporcionada por Amazon Web Services
- Se utiliza en el modo AWS ENI IPAM de Cilium

**ARP (Address Resolution Protocol)** - Networking
- Protocolo que convierte direcciones IP en direcciones MAC
- Protocolo esencial para la comunicación en redes L2

## B

**BGP (Border Gateway Protocol)** - Networking
- Protocolo de gateway externo estándar utilizado para intercambiar información de enrutamiento en Internet
- Puede utilizarse como modo de enrutamiento nativo en Cilium

**BPF (Berkeley Packet Filter)** - eBPF
- Tecnología para el filtrado de paquetes, predecesora de eBPF
- Desarrollada originalmente para la captura de paquetes de red

**BPF Maps** - eBPF
- Almacenes de clave-valor utilizados para guardar y recuperar datos en programas eBPF
- Se utilizan para compartir datos entre el espacio de usuario y el espacio del kernel

## C

**CGroup (Control Group)** - Kubernetes
- Funcionalidad del kernel de Linux que limita y aísla el uso de recursos de grupos de procesos
- Se utiliza para limitar los recursos de los contenedores

**CIDR (Classless Inter-Domain Routing)** - Networking
- Método para la asignación de direcciones IP y la agregación de enrutamiento
- Ejemplo: 192.168.1.0/24 representa el rango de direcciones IP desde 192.168.1.0 hasta 192.168.1.255

**CNI (Container Network Interface)** - Kubernetes
- Interfaz estándar entre los runtimes de contenedores y los plugins de red
- Cilium es una de las implementaciones de CNI

**CoreDNS** - Kubernetes
- Servidor DNS utilizado habitualmente en clústeres de Kubernetes
- Desempeña un papel importante en el descubrimiento de servicios

**CRD (Custom Resource Definition)** - Kubernetes
- Método para definir recursos personalizados ampliando la API de Kubernetes
- Cilium utiliza CRD para definir políticas de red, etc.

**Cilium** - Cilium
- Solución de redes, seguridad y observabilidad de código abierto basada en eBPF
- Se utiliza como implementación de CNI para Kubernetes

## D

**DNAT (Destination Network Address Translation)** - Networking
- Tipo de NAT que modifica la dirección IP de destino de los paquetes
- Se utiliza para el equilibrio de carga y el reenvío de puertos

**DNS (Domain Name System)** - Networking
- Sistema que convierte nombres de dominio en direcciones IP
- Cilium admite políticas de red basadas en DNS

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF
- Tecnología que permite la ejecución segura de programas dentro del kernel de Linux
- Tecnología principal utilizada en Cilium

**Endpoint** - Cilium
- Unidad de carga de trabajo a la que se aplican políticas de red en Cilium
- Generalmente corresponde a Pods de Kubernetes

**Envoy** - Cilium
- Proxy L7 y componente de service mesh
- Se utiliza para la aplicación de políticas L7 en Cilium

## H

**Hubble** - Cilium
- Capa de observabilidad de Cilium
- Herramienta para la monitorización y el análisis en tiempo real de flujos de red

## I

**IPAM (IP Address Management)** - Networking
- Sistema responsable de asignar, rastrear y gestionar direcciones IP
- Cilium admite varios modos de IPAM

**IPsec** - Networking
- Conjunto de protocolos que proporciona comunicación segura mediante el cifrado de paquetes IP
- Puede utilizarse para el cifrado del tráfico entre nodos en Cilium

## K

**kube-proxy** - Kubernetes
- Proxy de red que implementa la abstracción de Service de Kubernetes
- Cilium puede sustituir a kube-proxy

## V

**VXLAN (Virtual Extensible LAN)** - Networking
- Tecnología de virtualización de red que superpone redes de Layer 2 sobre redes de Layer 3
- Uno de los modos de red superpuesta de Cilium

## W

**WireGuard** - Networking
- Protocolo VPN moderno y rápido
- Puede utilizarse para el cifrado del tráfico entre nodos en Cilium

## X

**XDP (eXpress Data Path)** - eBPF
- Funcionalidad de eBPF que procesa paquetes en el nivel del controlador de red
- Proporciona procesamiento de paquetes de muy alto rendimiento

**DaemonSet**
- Recurso de Kubernetes que ejecuta una copia de un Pod en todos los nodos

## E

**eBPF (extended Berkeley Packet Filter)**
- Tecnología que permite la ejecución segura de programas dentro del kernel de Linux

**Endpoint**
- Endpoint de red (generalmente un Pod) al que se aplican políticas de red en Cilium

**Envoy**
- Proxy de borde y de Service de código abierto utilizado como proxy L7 y bus de comunicación

## F

**FQDN (Fully Qualified Domain Name)**
- Nombre de dominio completo de un host (p. ej., www.example.com)

## G

**GENEVE (Generic Network Virtualization Encapsulation)**
- Protocolo de encapsulación para la virtualización de red

**gRPC (gRPC Remote Procedure Call)**
- Framework RPC (Remote Procedure Call) de alto rendimiento desarrollado por Google

## H

**Hubble**
- Componente de visibilidad y monitorización de red de Cilium

## I

**IPAM (IP Address Management)**
- Planificación, seguimiento y gestión de direcciones IP

**IPsec (Internet Protocol Security)**
- Conjunto de protocolos para la seguridad de la comunicación IP

**Istio**
- Plataforma de código abierto que implementa service mesh

## K

**Kafka**
- Plataforma distribuida de streaming

**kube-proxy**
- Proxy de red que implementa la abstracción de Service de Kubernetes

**Kubernetes**
- Plataforma de código abierto que automatiza el despliegue, el escalado y la gestión de aplicaciones en contenedores

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
- Dispositivo o Service que distribuye el tráfico entre varios servidores

## M

**MAC (Media Access Control) Address**
- Identificador único asignado a interfaces de red

**MTU (Maximum Transmission Unit)**
- Tamaño máximo de paquete que puede transmitirse a través de una red

**mTLS (mutual TLS)**
- Extensión de TLS en la que tanto el cliente como el servidor se autentican mutuamente mediante certificados

## N

**NAT (Network Address Translation)**
- Proceso de modificar la información de direcciones IP en paquetes IP

**NodePort**
- Tipo de Service de Kubernetes que expone un puerto estático en la IP de cada nodo

## O

**OSI (Open Systems Interconnection) Model**
- Modelo conceptual que clasifica la comunicación de red en 7 capas abstractas

**Overlay Network**
- Red virtual construida sobre una red existente

## P

**Pod**
- Unidad de cómputo desplegable más pequeña de Kubernetes

**Proxy**
- Servidor que actúa como intermediario entre el cliente y el servidor

## R

**RBAC (Role-Based Access Control)**
- Método para controlar el acceso a recursos del sistema según roles

## S

**Service**
- Abstracción de Kubernetes que proporciona un Endpoint estable para un conjunto de Pods

**SNAT (Source Network Address Translation)**
- Tipo de NAT que modifica la dirección IP de origen de los paquetes

**Socket**
- Endpoint para la comunicación entre procesos a través de una red

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
- Dispositivo Ethernet virtual, normalmente creado en pares

**VNI (VXLAN Network Identifier)**
- Identificador de 24 bits que identifica redes VXLAN

**VTEP (VXLAN Tunnel Endpoint)**
- Endpoint responsable de la encapsulación y desencapsulación de paquetes VXLAN

**VXLAN (Virtual Extensible LAN)**
- Tecnología de virtualización de red que superpone redes de Layer 2 sobre redes de Layer 3

## W

**WireGuard**
- Protocolo de túnel VPN moderno, rápido y seguro

## X

**XDP (eXpress Data Path)**
- Tecnología basada en eBPF para el procesamiento muy rápido de paquetes de red

## Cuestionario

Para comprobar lo que aprendiste en este capítulo, prueba el [cuestionario del tema](../../quizzes/networking/cilium/glossary-quiz.md).
