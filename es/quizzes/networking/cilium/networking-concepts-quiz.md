# Cuestionario sobre conceptos de redes de Cilium

> **Versión de referencia**: Cilium 1.20.3.
> **Última revisión**: 16 de octubre de 2026.

[Volver a la guía](../../../networking/cilium/networking-concepts.md)

## OSI y conceptos básicos

1. **¿Qué descripción de las capacidades de las políticas de Cilium es correcta?**

   - A) Solo un firewall general basado en direcciones MAC
   - B) Solo L3/L4, sin integración con proxy
   - C) Solo políticas HTTP
   - D) Controles L3/L4 y reglas L7 compatibles que estén configuradas

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Controles L3/L4 y reglas L7 compatibles que estén configuradas**

   Cilium combina la aplicación de políticas L3/L4 con funciones de proxy compatibles para HTTP/gRPC y DNS. Esto no significa que implemente todas las capas OSI ni que incluya la API L7 de Kafka, que se eliminó.

   </details>

2. **¿Cuál de estas direcciones pertenece a la capa de enlace?**

   - A) Dirección IP
   - B) Dirección MAC
   - C) Número de puerto
   - D) URL

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Dirección MAC**

   Una dirección MAC identifica una interfaz de la capa de enlace. Se puede asignar localmente o cambiar, por lo que no se garantiza que sea única globalmente ni auténtica.

   </details>

3. **¿Qué protocolo proporciona direccionamiento IP en la capa de red?**

   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) IP**

   IP proporciona direccionamiento lógico y entrega de paquetes en la capa de red; TCP y UDP tienen semánticas de transporte distintas.

   </details>

## Redes de contenedores

4. **Sin sobrescrituras específicas de la plataforma, ¿cuál es el valor predeterminado genérico de enrutamiento en Helm de Cilium?**

   - A) Modo puente de Docker
   - B) Modo túnel/superposición
   - C) Modo nativo con BGP obligatorio
   - D) Red del host para todas las cargas de trabajo

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Modo túnel/superposición**

   El valor predeterminado genérico es el modo túnel. Los perfiles de instalación específicos de una plataforma pueden elegir otro modo; no es una regla invariable para EKS ni para todas las nubes.

   </details>

5. **¿Qué protocolo se usa de forma predeterminada en el perfil genérico de túnel de Cilium?**

   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) VXLAN**

   VXLAN es el protocolo de túnel predeterminado y, en Cilium, utiliza UDP 8472 de forma predeterminada. El puerto UDP asignado a VXLAN estándar es 4789.

   </details>

6. **¿Cuál es una característica concreta del enrutamiento nativo?**

   - A) Cifrado automático
   - B) No necesita rutas de retorno
   - C) No encapsula la superposición en esa ruta
   - D) Garantiza el mejor rendimiento

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) No encapsula la superposición en esa ruta**

   El enrutamiento nativo evita las cabeceras de superposición, pero requiere que los Pods sean alcanzables y que existan rutas de retorno válidas. El rendimiento depende de la carga de trabajo y la implementación.

   </details>

## IPAM

7. **Sin sobrescrituras específicas de la plataforma, ¿cuál es el modo IPAM predeterminado genérico de Helm?**

   - A) kubernetes
   - B) cluster-pool
   - C) Un modo denominado PodCIDR
   - D) eni

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) cluster-pool**

   En el modo cluster-pool, el operador asigna CIDR a los nodos y cada agente asigna localmente las direcciones IP de los Pods. Usa el nombre real del modo, no la expresión ambigua «Cluster Scope».

   </details>

8. **¿Qué modo IPAM de Cilium utiliza ENI de EC2 y direcciones de VPC?**

   - A) Kubernetes host-scope
   - B) cluster-pool
   - C) ENI
   - D) Genérico respaldado por CRD

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) ENI**

   El modo ENI tiene requisitos previos específicos de AWS. No es una recomendación universal para todos los modos de cómputo de EKS ni para todas las configuraciones de encadenamiento de CNI.

   </details>

9. **¿Qué campos de Node se utilizan con `ipam.mode: kubernetes`?**

   - A) `spec.podCIDR / spec.podCIDRs`
   - B) `spec.CIDR`
   - C) `spec.Subnet`
   - D) `spec.IPRange`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) `spec.podCIDR / spec.podCIDRs`**

   Kubernetes asigna CIDR de Pods a los nodos. Cilium los utiliza en el modo IPAM Kubernetes host-scope; PodCIDR no es el nombre literal del modo IPAM.

   </details>

## Servicios y balanceo de carga

10. **¿Qué función no habilita por sí solo el reemplazo de kube-proxy?**

   - A) Reenvío de ClusterIP
   - B) Reenvío de NodePort
   - C) Reenvío de los servicios LoadBalancer compatibles
   - D) mTLS entre cargas de trabajo

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) mTLS entre cargas de trabajo**

   El reenvío de servicios es independiente de la autenticación y el cifrado entre cargas de trabajo. Además, aprovisionar un balanceador externo requiere su propio controlador o proveedor.

   </details>

11. **¿Qué algoritmos de balanceo de carga de servicios BPF tiene Cilium?**

   - A) Random y Maglev
   - B) Solo round robin
   - C) Menor número de conexiones de forma predeterminada
   - D) Rotación periódica de timeout de Maglev

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Random y Maglev**

   Random es el algoritmo predeterminado y Maglev es una alternativa en las rutas compatibles. Los algoritmos de Envoy, la afinidad ClientIP y los timeouts de afinidad son conceptos distintos.

   </details>

12. **¿Qué permite un Global Service configurado?**

   - A) Asignación automática de una IP pública mundial
   - B) Balanceo de carga de servicios entre clústeres conectados
   - C) Replicación automática de todas las políticas
   - D) Almacenamiento persistente compartido

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Balanceo de carga de servicios entre clústeres conectados**

   Se requieren ClusterMesh y nombres y espacios de nombres de Service coincidentes. Aún hay que validar el comportamiento de los endpoints y la caché, así como la gestión de fallos.

   </details>

## Políticas de red

13. **¿Qué selecciona `toCIDR`?**

   - A) Rangos de direcciones de destino
   - B) Nombres de host DNS autenticados
   - C) Solo Services con nombre
   - D) Solo puertos TCP

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Rangos de direcciones de destino**

   Los selectores CIDR tienen reglas de clasificación de endpoints: de forma predeterminada, se excluyen los Pods y nodos administrados dentro del clúster; en esta versión hay que habilitarlo mediante una opción explícita en estado Beta. No es un mecanismo de autenticación.

   </details>

14. **¿Qué representa la entidad `world`?**

   - A) Todas las identidades conocidas del clúster
   - B) Endpoints externos, no identidades conocidas del clúster o de ClusterMesh
   - C) Todos los nodos de Kubernetes
   - D) Todos los espacios de nombres

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Endpoints externos, no identidades conocidas del clúster o de ClusterMesh**

   `world` no es sinónimo de todos los endpoints de todos los clústeres. Selecciona la entidad o el alcance de identidad adecuados y los puertos necesarios.

   </details>

15. **¿Qué antigua capacidad L7 de Cilium se eliminó?**

   - A) Coincidencia de rutas HTTP
   - B) Reglas para consultas DNS
   - C) Reglas para temas de Kafka
   - D) Coincidencia de métodos HTTP

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Reglas para temas de Kafka**

   Las políticas actuales admiten funciones de proxy relacionadas con HTTP/gRPC y reglas DNS; los ejemplos antiguos de políticas Kafka no se deben copiar en la API actual.

   </details>

## Conceptos avanzados

16. **¿Qué par nombra modos alternativos de cifrado del transporte entre nodos de Cilium?**

   - A) HTTP y DNS
   - B) TCP y UDP
   - C) IPsec y WireGuard
   - D) Relay y Prometheus

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) IPsec y WireGuard**

   Elige el modo de cifrado entre nodos adecuado y valida su cobertura. La autenticación mutua de SPIRE y el mTLS entre cargas de trabajo de ztunnel en estado Beta cumplen funciones distintas y tienen otros requisitos previos.

   </details>

17. **¿Cómo se llama la función de red multiclúster de Cilium?**

   - A) Cluster Federation
   - B) ClusterMesh
   - C) Global Cluster
   - D) NodePort Mesh

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) ClusterMesh**

   ClusterMesh comparte metadatos de red y admite la conectividad entre clústeres configurada; siguen siendo necesarios los requisitos previos de direccionamiento, confianza y red subyacente.

   </details>

18. **¿Qué hace el plano de control BGP de Cilium?**

   - A) Programa todas las rutas aprendidas en el plano de datos local
   - B) Anuncia a los peers prefijos seleccionados de Pods/Services
   - C) Crea automáticamente registros DNS
   - D) Garantiza todo el tráfico entre clústeres

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Anuncia a los peers prefijos seleccionados de Pods/Services**

   Anunciar rutas es distinto de asignar direcciones y reenviar paquetes. Inspecciona las rutas del peer y prueba el tráfico en ambos sentidos.

   </details>

19. **¿Qué hace Egress Gateway con el tráfico saliente que coincide con la configuración?**

   - A) Aplica SNAT a una IP de gateway seleccionada
   - B) Conserva todas las IP de origen originales de los Pods
   - C) Cifra automáticamente el tráfico externo
   - D) Crea interfaces de gateway sin requisitos previos

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Aplica SNAT a una IP de gateway seleccionada**

   Proporciona una dirección de origen configurada mediante traducción. Hay que considerar las interfaces y rutas preparadas, así como la convergencia de las políticas para Pods nuevos.

   </details>

20. **¿Qué optimiza el enrutamiento de host BPF?**

   - A) Conmutación automática entre enrutamiento nativo y de superposición
   - B) Reenvío de paquetes dentro del host y uso de la pila de red del host
   - C) Autorización del firewall del host
   - D) Cifrado del almacenamiento

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Reenvío de paquetes dentro del host y uso de la pila de red del host**

   Con los requisitos previos y los límites de integración correspondientes, el enrutamiento de host BPF puede omitir partes de la pila de red y de netfilter del host. No es lo mismo que elegir entre enrutamiento nativo o de túnel entre nodos.

   </details>
