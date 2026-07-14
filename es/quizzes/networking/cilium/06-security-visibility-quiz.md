# Cuestionario sobre seguridad y visibilidad de Cilium

> **Versión compatible**: Cilium 1.17
> **Última actualización**: February 22, 2026

## Conceptos básicos de Network Policy

1. **¿Cuál es la principal diferencia entre Kubernetes NetworkPolicy y Cilium NetworkPolicy?**
   - A) Cilium NetworkPolicy no admite políticas L7
   - B) Kubernetes NetworkPolicy no admite políticas L7
   - C) Cilium NetworkPolicy solo se puede aplicar a Nodes específicos
   - D) Kubernetes NetworkPolicy proporciona un mayor rendimiento

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Kubernetes NetworkPolicy no admite políticas L7</p>
   <p><strong>Explicación</strong>: Kubernetes NetworkPolicy solo admite políticas de nivel L3/L4, mientras que Cilium NetworkPolicy admite una gama más amplia de políticas, desde L3 hasta L7.</p>
   </details>

2. **¿Cuál es el grupo de API de Cilium NetworkPolicy?**
   - A) networking.k8s.io
   - B) cilium.io
   - C) policy.cilium.io
   - D) network.cilium.io

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) cilium.io</p>
   <p><strong>Explicación</strong>: Cilium NetworkPolicy utiliza el grupo de API cilium.io.</p>
   </details>

3. **¿Cuál es la función de 'endpointSelector' en Cilium NetworkPolicy?**
   - A) Selecciona los Pods de destino a los que se aplica la política
   - B) Selecciona los Nodes de destino a los que se aplica la política
   - C) Selecciona los namespaces de destino a los que se aplica la política
   - D) Selecciona los Services de destino a los que se aplica la política

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) Selecciona los Pods de destino a los que se aplica la política</p>
   <p><strong>Explicación</strong>: endpointSelector se utiliza para seleccionar los Pods de destino (endpoints) a los que se aplica la política.</p>
   </details>

4. **¿Qué controla la regla 'ingress' en Cilium NetworkPolicy?**
   - A) El tráfico entrante a los Pods seleccionados
   - B) El tráfico saliente de los Pods seleccionados
   - C) El tráfico interno dentro de los Pods seleccionados
   - D) El tráfico hacia fuera del cluster

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) El tráfico entrante a los Pods seleccionados</p>
   <p><strong>Explicación</strong>: Las reglas de ingress controlan el tráfico entrante a los Pods seleccionados.</p>
   </details>

5. **¿Qué controla la regla 'egress' en Cilium NetworkPolicy?**
   - A) El tráfico entrante a los Pods seleccionados
   - B) El tráfico saliente de los Pods seleccionados
   - C) El tráfico interno dentro de los Pods seleccionados
   - D) El tráfico desde fuera del cluster

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) El tráfico saliente de los Pods seleccionados</p>
   <p><strong>Explicación</strong>: Las reglas de egress controlan el tráfico saliente de los Pods seleccionados.</p>
   </details>

## Políticas L7

6. **¿Qué atributo no se puede filtrar en las políticas HTTP L7 de Cilium?**
   - A) Ruta
   - B) Método
   - C) Encabezados
   - D) Tiempo de respuesta

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: D) Tiempo de respuesta</p>
   <p><strong>Explicación</strong>: Las políticas HTTP L7 de Cilium pueden filtrar atributos de solicitudes HTTP, como la ruta, el método y los encabezados, pero el tiempo de respuesta no es un objetivo de filtrado.</p>
   </details>

7. **¿Qué atributo se puede filtrar en las políticas Kafka L7 de Cilium?**
   - A) Topic
   - B) Partición
   - C) Offset
   - D) Todas las opciones anteriores

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) Topic</p>
   <p><strong>Explicación</strong>: Las políticas Kafka L7 de Cilium pueden filtrar principalmente según el topic, la clave de API y atributos similares.</p>
   </details>

8. **¿Qué permite la regla 'matchPattern' en las políticas DNS L7 de Cilium?**
   - A) Coincidencia exacta de nombres de dominio
   - B) Coincidencia de patrones de nombres de dominio con comodines
   - C) Coincidencia de direcciones IP
   - D) Coincidencia de números de puerto

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Coincidencia de patrones de nombres de dominio con comodines</p>
   <p><strong>Explicación</strong>: La regla matchPattern puede coincidir con patrones de nombres de dominio que incluyen comodines (*). Ejemplo: *.example.com</p>
   </details>

9. **¿Qué componente se necesita para aplicar las políticas L7 de Cilium?**
   - A) kube-proxy
   - B) Envoy proxy
   - C) NGINX ingress controller
   - D) HAProxy

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Envoy proxy</p>
   <p><strong>Explicación</strong>: Cilium utiliza el proxy Envoy para aplicar políticas L7.</p>
   </details>

10. **¿Qué protocolo NO es compatible con las políticas L7 de Cilium?**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) SMTP</p>
    <p><strong>Explicación</strong>: Cilium admite protocolos L7 como HTTP, gRPC y Kafka, pero SMTP no es compatible de forma predeterminada.</p>
    </details>

## Cifrado y seguridad

11. **¿Qué protocolos se pueden utilizar para el cifrado del tráfico de red en Cilium?**
    - A) IPsec
    - B) WireGuard
    - C) Tanto A como B
    - D) TLS

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) Tanto A como B</p>
    <p><strong>Explicación</strong>: Cilium puede cifrar el tráfico entre Nodes usando tanto IPsec como WireGuard.</p>
    </details>

12. **¿Qué tráfico protege la funcionalidad de cifrado de Cilium?**
    - A) Solo el tráfico entre Nodes
    - B) Solo el tráfico entre Pods
    - C) Solo el tráfico de Node a Pod
    - D) Todo el tráfico del cluster

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Solo el tráfico entre Pods</p>
    <p><strong>Explicación</strong>: La funcionalidad de cifrado de Cilium protege principalmente el tráfico entre Pods.</p>
    </details>

13. **¿Qué protege la funcionalidad Host Firewall de Cilium?**
    - A) Interfaces de red de Pods
    - B) Interfaces de red del host
    - C) Endpoints de Service
    - D) Container runtime

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Interfaces de red del host</p>
    <p><strong>Explicación</strong>: Host Firewall de Cilium protege las propias interfaces de red del host, lo que mejora la seguridad a nivel de host.</p>
    </details>

14. **¿Qué funcionalidad de seguridad de Cilium coincide con esta descripción? "Filtra el tráfico según campos o patrones específicos de protocolos específicos de la capa de aplicación"**
    - A) Políticas de red
    - B) Políticas L7
    - C) Cifrado
    - D) Detección de intrusiones

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Políticas L7</p>
    <p><strong>Explicación</strong>: Las políticas L7 (capa de aplicación) pueden filtrar el tráfico según campos o patrones específicos en protocolos como HTTP, gRPC y Kafka.</p>
    </details>

15. **¿En qué se basa el modelo de seguridad basado en Identity de Cilium?**
    - A) Nombre del Pod
    - B) Nombre del Node
    - C) Labels
    - D) Dirección IP

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) Labels</p>
    <p><strong>Explicación</strong>: Identity de Cilium se basa en los labels de los Pods, lo que permite aplicar políticas de seguridad coherentes incluso cuando cambian las direcciones IP.</p>
    </details>

## Visibilidad y monitorización

16. **¿Qué es Hubble?**
    - A) La herramienta de visibilidad de red de Cilium
    - B) El balanceador de carga de Cilium
    - C) El protocolo de cifrado de Cilium
    - D) El servidor DNS de Cilium

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) La herramienta de visibilidad de red de Cilium</p>
    <p><strong>Explicación</strong>: Hubble es la herramienta de visibilidad de red de Cilium que puede observar y analizar flujos de red basándose en eBPF.</p>
    </details>

17. **¿Qué funcionalidad NO proporciona Hubble UI?**
    - A) Mapa de dependencias de Service
    - B) Visualización de flujos de red
    - C) Alertas de infracción de políticas
    - D) Gestión de despliegues de código

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Gestión de despliegues de código</p>
    <p><strong>Explicación</strong>: Hubble UI proporciona mapas de dependencias de Service, visualización de flujos de red y alertas de infracción de políticas, pero no proporciona gestión de despliegues de código.</p>
    </details>

18. **¿Cuál es el comando para observar flujos de red de un Pod específico mediante Hubble CLI?**
    - A) `hubble observe --pod <pod-name>`
    - B) `hubble watch --pod <pod-name>`
    - C) `hubble monitor --pod <pod-name>`
    - D) `hubble inspect --pod <pod-name>`

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) <code>hubble observe --pod &lt;pod-name&gt;</code></p>
    <p><strong>Explicación</strong>: El comando <code>hubble observe --pod &lt;pod-name&gt;</code> puede observar flujos de red de un Pod específico en tiempo real.</p>
    </details>

19. **¿Qué métrica NO recopila Hubble?**
    - A) Códigos de estado HTTP
    - B) Estado de conexión TCP
    - C) Recuento de paquetes descartados
    - D) Uso de CPU del Container

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Uso de CPU del Container</p>
    <p><strong>Explicación</strong>: Hubble recopila métricas relacionadas con la red (códigos de estado HTTP, estado de conexión TCP, recuento de paquetes descartados, etc.), pero no recopila métricas del sistema como el uso de CPU del Container.</p>
    </details>

20. **¿Cómo se integra Cilium con Prometheus?**
    - A) Añadir anotaciones de Prometheus a Cilium Operator
    - B) Instalar el plugin de Cilium en el servidor Prometheus
    - C) Crear un recurso ServiceMonitor para Cilium
    - D) Importar el dashboard de Cilium a Prometheus

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) Crear un recurso ServiceMonitor para Cilium</p>
    <p><strong>Explicación</strong>: Al utilizar Prometheus Operator, puedes recopilar métricas de Cilium creando un recurso ServiceMonitor para Cilium.</p>
    </details>
