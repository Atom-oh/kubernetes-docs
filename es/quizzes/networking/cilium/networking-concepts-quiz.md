# Cuestionario sobre conceptos de redes de Cilium

> **Versión compatible**: Cilium 1.17
> **Última actualización**: February 22, 2026

## Modelo OSI y conceptos básicos

1. **¿En qué capa del modelo OSI opera principalmente Cilium?**
   - A) L2 (capa de enlace de datos)
   - B) L3/L4 (capa de red/transporte)
   - C) L7 (capa de aplicación)
   - D) Todas las capas de L3 a L7

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: D) Todas las capas de L3 a L7</p>
   <p><strong>Explicación</strong>: Cilium proporciona funciones de red y seguridad no solo en L3/L4 (direcciones IP, puertos), sino también hasta las capas L7 (HTTP, gRPC, Kafka, etc.).</p>
   </details>

2. **¿Cuál de las siguientes es una dirección L2 (capa de enlace de datos)?**
   - A) Dirección IP
   - B) Dirección MAC
   - C) Número de puerto
   - D) URL

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Dirección MAC</p>
   <p><strong>Explicación</strong>: Una dirección MAC (Media Access Control) es un identificador único de una tarjeta de interfaz de red y se utiliza en la capa L2.</p>
   </details>

3. **¿Cuál de los siguientes es un protocolo L3 (capa de red)?**
   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) IP</p>
   <p><strong>Explicación</strong>: IP (Internet Protocol) es un protocolo responsable del enrutamiento de paquetes en la capa de red (L3).</p>
   </details>

## Redes de contenedores

4. **¿Cuál es el modelo de red predeterminado de Cilium?**
   - A) Modo puente
   - B) Red superpuesta
   - C) Red subyacente
   - D) Red del host

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Red superpuesta</p>
   <p><strong>Explicación</strong>: Cilium utiliza de forma predeterminada un modelo de red superpuesta mediante VXLAN o Geneve.</p>
   </details>

5. **¿Cuál es el protocolo de red superpuesta predeterminado que utiliza Cilium?**
   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) VXLAN</p>
   <p><strong>Explicación</strong>: Cilium utiliza de forma predeterminada el protocolo VXLAN (Virtual Extensible LAN) para configurar redes superpuestas.</p>
   </details>

6. **¿Cuál es el principal beneficio del modo Direct Routing de Cilium?**
   - A) Mayor seguridad
   - B) Mejor compatibilidad
   - C) Menor latencia y mayor rendimiento
   - D) Configuración más sencilla

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) Menor latencia y mayor rendimiento</p>
   <p><strong>Explicación</strong>: El modo Direct Routing proporciona menor latencia y mayor rendimiento porque no utiliza encapsulación de red superpuesta.</p>
   </details>

## Administración de direcciones IP (IPAM)

7. **¿Cuál es el modo IPAM predeterminado de Cilium?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) Basado en CRD
   - D) AWS ENI

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Cluster Scope</p>
   <p><strong>Explicación</strong>: El modo IPAM predeterminado de Cilium es Cluster Scope, que asigna direcciones IP de forma centralizada en todo el cluster.</p>
   </details>

8. **¿Cuál es el modo IPAM recomendado al usar Cilium en AWS EKS?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) Basado en CRD

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) AWS ENI</p>
   <p><strong>Explicación</strong>: En AWS EKS, se recomienda utilizar el modo IPAM AWS ENI para asignar directamente direcciones IP de VPC a los Pods.</p>
   </details>

9. **¿Qué función de Kubernetes utiliza el modo IPAM 'PodCIDR' de Cilium?**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>Explicación</strong>: El modo IPAM PodCIDR de Cilium utiliza el campo NodeSpec.PodCIDR asignado por Kubernetes a cada nodo.</p>
   </details>

## Services y balanceo de carga

10. **¿Qué función NO proporciona el modo de reemplazo de kube-proxy de Cilium?**
    - A) Compatibilidad con Service ClusterIP
    - B) Compatibilidad con Service NodePort
    - C) Compatibilidad con Service LoadBalancer
    - D) Funcionalidad de Service Mesh

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Funcionalidad de Service Mesh</p>
    <p><strong>Explicación</strong>: El modo de reemplazo de kube-proxy de Cilium admite los tipos básicos de Service de Kubernetes, pero la funcionalidad de Service Mesh se proporciona mediante una función independiente de Cilium Service Mesh.</p>
    </details>

11. **¿Qué algoritmos utiliza Cilium para el balanceo de carga de Service?**
    - A) Round robin
    - B) Menor número de conexiones
    - C) Hash de IP
    - D) Todos los anteriores

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Todos los anteriores</p>
    <p><strong>Explicación</strong>: Cilium admite varios algoritmos de balanceo de carga, incluidos round robin, menor número de conexiones y hash de IP.</p>
    </details>

12. **¿Qué permite la función Global Service de Cilium?**
    - A) Acceso a Service distribuidos globalmente
    - B) Balanceo de carga de Service entre varios clusters
    - C) Asignación global de direcciones IP
    - D) Aplicación global de políticas de red

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Balanceo de carga de Service entre varios clusters</p>
    <p><strong>Explicación</strong>: La función Global Service de Cilium permite el balanceo de carga para el mismo Service entre varios clusters mediante Cluster Mesh.</p>
    </details>

## Políticas de red

13. **¿Qué permite la regla 'toCIDR' en las políticas de red de Cilium?**
    - A) Tráfico hacia rangos de direcciones IP específicos
    - B) Tráfico hacia nombres de dominio específicos
    - C) Tráfico hacia Services específicos
    - D) Tráfico hacia puertos específicos

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) Tráfico hacia rangos de direcciones IP específicos</p>
    <p><strong>Explicación</strong>: La regla toCIDR se utiliza para permitir tráfico hacia rangos de direcciones IP específicos (en notación CIDR).</p>
    </details>

14. **¿Qué significa la entidad 'world' en las reglas 'toEntities' de las políticas de red de Cilium?**
    - A) Todos los endpoints internos del cluster
    - B) Todas las redes externas
    - C) Todos los nodos
    - D) Todos los namespaces

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Todas las redes externas</p>
    <p><strong>Explicación</strong>: La entidad 'world' se refiere a todas las redes externas al cluster.</p>
    </details>

15. **¿Qué protocolo NO es compatible con las políticas L7 de Cilium?**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) SMTP</p>
    <p><strong>Explicación</strong>: Cilium admite protocolos L7 como HTTP, gRPC y Kafka, pero no admite SMTP de forma predeterminada.</p>
    </details>

## Conceptos avanzados de redes

16. **¿Qué protocolos pueden utilizarse en la función Transparent Encryption de Cilium?**
    - A) IPsec
    - B) WireGuard
    - C) Tanto A como B
    - D) TLS

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) Tanto A como B</p>
    <p><strong>Explicación</strong>: Cilium puede cifrar el tráfico entre nodos mediante IPsec y WireGuard.</p>
    </details>

17. **¿Qué tecnología utiliza la función Multi-cluster de Cilium?**
    - A) Cluster Federation
    - B) Cluster Mesh
    - C) Multi-cluster Networking
    - D) Global Cluster

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Cluster Mesh</p>
    <p><strong>Explicación</strong>: Cilium utiliza la tecnología Cluster Mesh para proporcionar conectividad entre varios clusters de Kubernetes.</p>
    </details>

18. **¿Qué es posible mediante la compatibilidad con BGP de Cilium?**
    - A) Intercambio de rutas con routers externos
    - B) Anuncio de IP externa para Services LoadBalancer
    - C) Enrutamiento directo entre clusters
    - D) Todos los anteriores

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Todos los anteriores</p>
    <p><strong>Explicación</strong>: La compatibilidad con BGP de Cilium permite el intercambio de rutas con routers externos, el anuncio de IP externa para Services LoadBalancer y el enrutamiento directo entre clusters.</p>
    </details>

19. **¿Cuál es el objetivo principal de la función Egress Gateway de Cilium?**
    - A) Conservar la dirección IP de origen del tráfico externo
    - B) Cambiar la dirección IP de destino del tráfico externo
    - C) Cifrar el tráfico externo
    - D) Bloquear el tráfico externo

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) Conservar la dirección IP de origen del tráfico externo</p>
    <p><strong>Explicación</strong>: Egress Gateway aplica SNAT al tráfico que va desde los Pods hacia fuera del cluster a una IP específica, proporcionando una IP de origen coherente.</p>
    </details>

20. **¿Qué afirmación es correcta sobre la función Host Routing de Cilium?**
    - A) Enrutamiento entre la red del host y la red de Pods
    - B) Enrutamiento directo entre hosts
    - C) Protección de la interfaz de red del host
    - D) Balanceo de carga basado en host

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Enrutamiento directo entre hosts</p>
    <p><strong>Explicación</strong>: Host Routing de Cilium proporciona enrutamiento directo entre hosts sin una red superpuesta.</p>
    </details>
