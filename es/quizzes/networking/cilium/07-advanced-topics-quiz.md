# Cuestionario avanzado de Cilium

> **Versión compatible**: Cilium 1.17
> **Última actualización**: February 22, 2026

## Tecnología eBPF

1. **¿Dónde se ejecutan los programas eBPF?**
   - A) Espacio de usuario
   - B) Espacio del kernel
   - C) Dentro de contenedores
   - D) Dentro de máquinas virtuales

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Espacio del kernel</p>
   <p><strong>Explicación</strong>: Los programas eBPF se ejecutan de forma segura dentro del kernel de Linux y pueden ampliar y modificar la funcionalidad del kernel.</p>
   </details>

2. **¿Qué mecanismo garantiza la seguridad de los programas eBPF?**
   - A) Virtualización
   - B) Contenerización
   - C) Verificador estático
   - D) Cifrado

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) Verificador estático</p>
   <p><strong>Explicación</strong>: El verificador de eBPF comprueba la seguridad de los programas antes de cargarlos para evitar bucles infinitos o fallos del kernel.</p>
   </details>

3. **¿Cuál NO es un beneficio principal de usar eBPF en Cilium?**
   - A) Implementar funcionalidades de red sin módulos del kernel
   - B) Alto rendimiento y baja sobrecarga
   - C) Aplicación detallada de políticas de red
   - D) Aceleración de hardware requerida

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: D) Aceleración de hardware requerida</p>
   <p><strong>Explicación</strong>: eBPF puede proporcionar alto rendimiento mediante software sin requerir aceleración de hardware.</p>
   </details>

## Modelos de red

4. **¿Qué modo de ruta de datos NO es compatible con Cilium?**
   - A) VXLAN
   - B) Geneve
   - C) Direct Routing
   - D) MPLS

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: D) MPLS</p>
   <p><strong>Explicación</strong>: Cilium admite VXLAN, Geneve y Direct Routing, pero no admite MPLS.</p>
   </details>

5. **¿Qué tecnología utiliza Cilium en el modo de reemplazo de kube-proxy?**
   - A) iptables
   - B) IPVS
   - C) XDP basado en eBPF
   - D) netfilter

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) XDP basado en eBPF</p>
   <p><strong>Explicación</strong>: Cilium utiliza eBPF y XDP (eXpress Data Path) para reemplazar kube-proxy y proporcionar mayor rendimiento.</p>
   </details>

6. **¿Qué funcionalidad del modelo de red de Cilium rastrea las rutas de los paquetes durante la comunicación de Pod a Pod?**
   - A) tcpdump
   - B) Hubble Flow Monitoring
   - C) Wireshark
   - D) Prometheus

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Hubble Flow Monitoring</p>
   <p><strong>Explicación</strong>: Hubble es la herramienta Hubble Flow Monitoring de Cilium que puede rastrear y visualizar la comunicación de Pod a Pod en tiempo real.</p>
   </details>

## IPAM y políticas de red

7. **¿Qué modo de IPAM (gestión de direcciones IP) en Cilium se integra con AWS EKS?**
   - A) Cluster Pool
   - B) Kubernetes Host Scope
   - C) AWS ENI
   - D) CRD-based

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) AWS ENI</p>
   <p><strong>Explicación</strong>: Cilium se integra con EKS mediante el modo AWS ENI (Elastic Network Interface) para asignar directamente direcciones IP de VPC a los Pods.</p>
   </details>

8. **¿Qué permite la regla 'toFQDNs' en las políticas de red de Cilium?**
   - A) Tráfico hacia direcciones IP específicas
   - B) Tráfico hacia puertos específicos
   - C) Tráfico hacia nombres de dominio específicos
   - D) Tráfico de protocolos específicos

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) Tráfico hacia nombres de dominio específicos</p>
   <p><strong>Explicación</strong>: La regla toFQDNs permite el tráfico hacia nombres de dominio específicos (FQDNs) y Cilium supervisa las consultas DNS para permitir dinámicamente las direcciones IP de esos dominios.</p>
   </details>

9. **¿Qué selector NO es compatible con Cilium CiliumNetworkPolicy?**
   - A) endpointSelector
   - B) nodeSelector
   - C) namespaceSelector
   - D) serviceSelector

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: D) serviceSelector</p>
   <p><strong>Explicación</strong>: Cilium admite endpointSelector, nodeSelector y namespaceSelector, pero no admite directamente serviceSelector.</p>
   </details>

## Redes L2-L7

10. **¿Qué atributo no puede filtrarse mediante las políticas L7 de Cilium para solicitudes HTTP?**
    - A) Ruta
    - B) Método
    - C) Encabezados
    - D) Tiempo de respuesta

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Tiempo de respuesta</p>
    <p><strong>Explicación</strong>: Las políticas L7 de Cilium pueden filtrar atributos de solicitudes HTTP como la ruta, el método y los encabezados, pero el tiempo de respuesta no es un objetivo de filtrado.</p>
    </details>

11. **¿Qué NO proporcionan las funcionalidades de Service Mesh de Cilium?**
    - A) TLS mutuo (mTLS)
    - B) División de tráfico
    - C) Descubrimiento de servicios
    - D) Autenticación de usuarios

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Autenticación de usuarios</p>
    <p><strong>Explicación</strong>: Cilium Service Mesh proporciona TLS mutuo, división de tráfico y descubrimiento de servicios, pero la autenticación de usuarios suele gestionarse mediante un sistema de autenticación independiente.</p>
    </details>

12. **¿Qué funcionalidad proporciona la integración de Cilium con Envoy?**
    - A) Balanceo de carga L7
    - B) Visibilidad L7
    - C) Aplicación de políticas L7
    - D) Todas las anteriores

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Todas las anteriores</p>
    <p><strong>Explicación</strong>: Cilium se integra con el proxy Envoy para proporcionar balanceo de carga L7, visibilidad y aplicación de políticas.</p>
    </details>

## Seguridad y visibilidad

13. **¿Qué funcionalidad NO proporciona Hubble UI?**
    - A) Mapa de dependencias de servicios
    - B) Visualización de flujos de red
    - C) Alertas de violación de políticas
    - D) Gestión de despliegues de código

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Gestión de despliegues de código</p>
    <p><strong>Explicación</strong>: Hubble UI proporciona mapas de dependencias de servicios, visualización de flujos de red y alertas de violación de políticas, pero no proporciona gestión de despliegues de código.</p>
    </details>

14. **¿Qué protocolos pueden utilizarse para el cifrado del tráfico de red en Cilium?**
    - A) IPsec y WireGuard
    - B) TLS y SSH
    - C) SSL y HTTPS
    - D) DTLS y QUIC

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) IPsec y WireGuard</p>
    <p><strong>Explicación</strong>: Cilium puede cifrar el tráfico de red entre nodos mediante los protocolos IPsec y WireGuard.</p>
    </details>

15. **¿Qué funcionalidad de seguridad de Cilium coincide con esta descripción? "Filtra el tráfico según campos o patrones específicos de protocolos específicos de la capa de aplicación"**
    - A) Políticas de red
    - B) Políticas L7
    - C) Cifrado
    - D) Detección de intrusiones

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Políticas L7</p>
    <p><strong>Explicación</strong>: Las políticas L7 (capa de aplicación) pueden filtrar tráfico según campos o patrones específicos en protocolos como HTTP, gRPC y Kafka.</p>
    </details>

## Temas avanzados y casos de uso reales

16. **¿Cuál NO es una funcionalidad principal de Cilium Cluster Mesh?**
    - A) Descubrimiento de servicios entre clústeres
    - B) Políticas de red entre clústeres
    - C) Balanceo de carga entre clústeres
    - D) Uso compartido de almacenamiento entre clústeres

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Uso compartido de almacenamiento entre clústeres</p>
    <p><strong>Explicación</strong>: Cilium Cluster Mesh proporciona descubrimiento de servicios, políticas de red y balanceo de carga entre clústeres, pero no proporciona uso compartido de almacenamiento.</p>
    </details>

17. **¿Qué proporciona la funcionalidad Bandwidth Manager de Cilium?**
    - A) Monitoreo del ancho de banda de red
    - B) Limitación del ancho de banda de red y QoS
    - C) Optimización del ancho de banda de red
    - D) Predicción del ancho de banda de red

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Limitación del ancho de banda de red y QoS</p>
    <p><strong>Explicación</strong>: Bandwidth Manager de Cilium utiliza eBPF para proporcionar limitación del ancho de banda de red y QoS (Quality of Service) por Pod.</p>
    </details>

18. **¿Qué protege la funcionalidad Host Firewall de Cilium?**
    - A) Solo la comunicación de contenedor a contenedor
    - B) Solo la comunicación de nodo a nodo
    - C) Las propias interfaces de red del host
    - D) Servicios externos en la nube

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) Las propias interfaces de red del host</p>
    <p><strong>Explicación</strong>: Host Firewall de Cilium protege las propias interfaces de red del host, mejorando la seguridad a nivel de host.</p>
    </details>

19. **¿Cuál es el propósito principal de la funcionalidad Egress Gateway de Cilium?**
    - A) Conservar la dirección IP de origen del tráfico externo
    - B) Cambiar la dirección IP de destino del tráfico externo
    - C) Cifrar el tráfico externo
    - D) Bloquear el tráfico externo

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) Conservar la dirección IP de origen del tráfico externo</p>
    <p><strong>Explicación</strong>: Egress Gateway de Cilium aplica SNAT al tráfico saliente desde los Pods hacia fuera del clúster a una IP específica, proporcionando una IP de origen coherente.</p>
    </details>

20. **¿Qué NO es posible mediante la compatibilidad con BGP de Cilium?**
    - A) Intercambio de rutas con routers externos
    - B) Anuncio de IP externas para servicios LoadBalancer
    - C) Enrutamiento directo entre clústeres
    - D) Creación automática de registros DNS

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Creación automática de registros DNS</p>
    <p><strong>Explicación</strong>: La compatibilidad con BGP de Cilium proporciona intercambio de rutas con routers externos, anuncio de IP externas para servicios LoadBalancer y enrutamiento directo entre clústeres, pero no proporciona creación automática de registros DNS.</p>
    </details>

## Rendimiento y solución de problemas

21. **¿Qué tecnología de optimización del rendimiento de Cilium reduce significativamente la latencia de procesamiento de paquetes?**
    - A) TCP BBR
    - B) XDP (eXpress Data Path)
    - C) DPDK
    - D) TSO (TCP Segmentation Offload)

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) XDP (eXpress Data Path)</p>
    <p><strong>Explicación</strong>: XDP procesa paquetes a nivel del controlador de red, omitiendo la pila de red del kernel para reducir significativamente la latencia.</p>
    </details>

22. **¿Cuál es el comando para diagnosticar problemas de conectividad de red en Cilium?**
    - A) `cilium status`
    - B) `cilium connectivity test`
    - C) `cilium monitor`
    - D) `cilium endpoint list`

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) `cilium connectivity test`</p>
    <p><strong>Explicación</strong>: El comando `cilium connectivity test` prueba diversos escenarios de conectividad de red dentro del clúster para diagnosticar problemas.</p>
    </details>

23. **¿Cuál es el comando para comprobar el estado de la política de red de un Pod específico en Cilium?**
    - A) `cilium endpoint list`
    - B) `cilium policy get`
    - C) `cilium endpoint get <endpoint-id>`
    - D) `cilium status --all-endpoints`

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) <code>cilium endpoint get &lt;endpoint-id&gt;</code></p>
    <p><strong>Explicación</strong>: El comando <code>cilium endpoint get &lt;endpoint-id&gt;</code> muestra información detallada y el estado de las políticas de red aplicadas a un endpoint (Pod) específico.</p>
    </details>

24. **¿Cuál es el comando para comprobar el estado de los mapas BPF en Cilium?**
    - A) `cilium map list`
    - B) `cilium bpf maps`
    - C) `cilium status --maps`
    - D) `cilium bpf map list`

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) `cilium bpf maps`</p>
    <p><strong>Explicación</strong>: El comando `cilium bpf maps` muestra una lista y el estado de todos los mapas BPF utilizados por Cilium.</p>
    </details>

25. **¿Cuál es el comando para la captura y el análisis de paquetes de red en Cilium?**
    - A) `cilium tcpdump`
    - B) `cilium capture`
    - C) `cilium monitor`
    - D) `cilium packet-capture`

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) `cilium monitor`</p>
    <p><strong>Explicación</strong>: El comando `cilium monitor` puede capturar y analizar en tiempo real los paquetes que pasan por la ruta de datos eBPF de Cilium.</p>
    </details>
