# Cuestionario de IPAM y Network Policy de Cilium

> **Versión compatible**: Cilium 1.17
> **Última actualización**: February 22, 2026

## IPAM (IP Address Management)

1. **¿Cuál es el modo IPAM predeterminado de Cilium?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) CRD-based
   - D) AWS ENI

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Cluster Scope</p>
   <p><strong>Explicación</strong>: El modo IPAM predeterminado de Cilium es Cluster Scope, que asigna direcciones IP de forma centralizada en todo el cluster.</p>
   </details>

2. **¿Qué modo IPAM de Cilium hace que cada nodo asigne IPs desde su propio rango CIDR?**
   - A) Cluster Scope
   - B) Kubernetes Host Scope
   - C) CRD-based
   - D) AWS ENI

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Kubernetes Host Scope</p>
   <p><strong>Explicación</strong>: En el modo IPAM Kubernetes Host Scope, cada nodo asigna direcciones IP desde su propio rango CIDR.</p>
   </details>

3. **¿Cuál es el modo IPAM recomendado al usar Cilium en AWS EKS?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) CRD-based

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) AWS ENI</p>
   <p><strong>Explicación</strong>: En AWS EKS, se recomienda usar el modo IPAM AWS ENI para asignar directamente direcciones IP de VPC a los Pods.</p>
   </details>

4. **¿Qué característica de Kubernetes utiliza el modo IPAM 'PodCIDR' de Cilium?**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>Explicación</strong>: El modo IPAM PodCIDR de Cilium utiliza el campo NodeSpec.PodCIDR que Kubernetes asigna a cada nodo.</p>
   </details>

5. **¿Qué comando se utiliza para comprobar la configuración IPAM de Cilium?**
   - A) `cilium status --ipam`
   - B) `cilium ipam`
   - C) `cilium config get ipam`
   - D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`</p>
   <p><strong>Explicación</strong>: La configuración IPAM de Cilium se almacena en el ConfigMap cilium-config y se puede verificar con este comando.</p>
   </details>

## Conceptos básicos de Network Policy

6. **¿Cuál es la versión de la API de Cilium NetworkPolicy?**
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) cilium.io/v2</p>
   <p><strong>Explicación</strong>: Cilium NetworkPolicy utiliza la versión de API cilium.io/v2.</p>
   </details>

7. **¿Cuál es la función de 'endpointSelector' en Cilium NetworkPolicy?**
   - A) Seleccionar Pods objetivo para la aplicación de la política
   - B) Seleccionar nodos objetivo para la aplicación de la política
   - C) Seleccionar namespaces objetivo para la aplicación de la política
   - D) Seleccionar services objetivo para la aplicación de la política

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) Seleccionar Pods objetivo para la aplicación de la política</p>
   <p><strong>Explicación</strong>: endpointSelector se utiliza para seleccionar los Pods objetivo (endpoints) a los que se aplica la política.</p>
   </details>

8. **¿Qué controla la regla 'ingress' en Cilium NetworkPolicy?**
   - A) El tráfico que entra en los Pods seleccionados
   - B) El tráfico que sale de los Pods seleccionados
   - C) El tráfico dentro de los Pods seleccionados
   - D) El tráfico hacia fuera del cluster

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) El tráfico que entra en los Pods seleccionados</p>
   <p><strong>Explicación</strong>: Las reglas de ingress controlan el tráfico que entra en los Pods seleccionados.</p>
   </details>

9. **¿Qué controla la regla 'egress' en Cilium NetworkPolicy?**
   - A) El tráfico que entra en los Pods seleccionados
   - B) El tráfico que sale de los Pods seleccionados
   - C) El tráfico dentro de los Pods seleccionados
   - D) El tráfico desde fuera del cluster

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) El tráfico que sale de los Pods seleccionados</p>
   <p><strong>Explicación</strong>: Las reglas de egress controlan el tráfico que sale de los Pods seleccionados.</p>
   </details>

10. **¿Cuál es la función del campo 'labels' en Cilium NetworkPolicy?**
    - A) Seleccionar Pods para la aplicación de la política
    - B) Identificador de la propia política
    - C) Seleccionar namespaces para la aplicación de la política
    - D) Seleccionar nodos para la aplicación de la política

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Identificador de la propia política</p>
    <p><strong>Explicación</strong>: El campo labels se utiliza como identificador de la propia política y se usa cuando otras políticas hacen referencia a esta política.</p>
    </details>

## Network Policy avanzada

11. **¿Qué permite la regla 'toCIDR' en Cilium NetworkPolicy?**
    - A) Tráfico hacia rangos de direcciones IP específicos
    - B) Tráfico hacia nombres de dominio específicos
    - C) Tráfico hacia services específicos
    - D) Tráfico hacia puertos específicos

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) Tráfico hacia rangos de direcciones IP específicos</p>
    <p><strong>Explicación</strong>: La regla toCIDR se utiliza para permitir tráfico hacia rangos de direcciones IP específicos (notación CIDR).</p>
    </details>

12. **¿Qué permite la regla 'toFQDNs' en Cilium NetworkPolicy?**
    - A) Tráfico hacia direcciones IP específicas
    - B) Tráfico hacia puertos específicos
    - C) Tráfico hacia nombres de dominio específicos
    - D) Tráfico de protocolos específicos

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) Tráfico hacia nombres de dominio específicos</p>
    <p><strong>Explicación</strong>: La regla toFQDNs permite tráfico hacia nombres de dominio específicos (FQDNs), mientras Cilium supervisa las consultas DNS para permitir dinámicamente las direcciones IP de esos dominios.</p>
    </details>

13. **¿Qué significa la entidad 'world' en la regla 'toEntities' de Cilium NetworkPolicy?**
    - A) Todos los endpoints internos del cluster
    - B) Todas las redes externas
    - C) Todos los nodos
    - D) Todos los namespaces

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Todas las redes externas</p>
    <p><strong>Explicación</strong>: La entidad 'world' hace referencia a todas las redes fuera del cluster.</p>
    </details>

14. **¿Qué permite la regla 'toServices' en Cilium NetworkPolicy?**
    - A) Tráfico hacia services específicos de Kubernetes
    - B) Tráfico hacia services externos específicos
    - C) Tráfico hacia puertos específicos
    - D) Tráfico de protocolos específicos

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) Tráfico hacia services específicos de Kubernetes</p>
    <p><strong>Explicación</strong>: La regla toServices se utiliza para permitir tráfico hacia services específicos de Kubernetes.</p>
    </details>

15. **¿Cuál es la función de 'nodeSelector' en Cilium NetworkPolicy?**
    - A) Seleccionar Pods objetivo para la aplicación de la política
    - B) Seleccionar nodos objetivo para la aplicación de la política
    - C) Seleccionar namespaces objetivo para la aplicación de la política
    - D) Seleccionar services objetivo para la aplicación de la política

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Seleccionar nodos objetivo para la aplicación de la política</p>
    <p><strong>Explicación</strong>: nodeSelector se utiliza para seleccionar los nodos objetivo a los que se aplica la política.</p>
    </details>

## Política L7

16. **¿Qué atributos se pueden filtrar en la política HTTP L7 de Cilium?**
    - A) Ruta
    - B) Método
    - C) Encabezados
    - D) Todos los anteriores

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Todos los anteriores</p>
    <p><strong>Explicación</strong>: La política HTTP L7 de Cilium puede filtrar diversos atributos de las solicitudes HTTP, incluidos la ruta, el método y los encabezados.</p>
    </details>

17. **¿Qué atributos se pueden filtrar en la política Kafka L7 de Cilium?**
    - A) Topic
    - B) API Key
    - C) Client ID
    - D) Todos los anteriores

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Todos los anteriores</p>
    <p><strong>Explicación</strong>: La política Kafka L7 de Cilium puede filtrar diversos atributos de las solicitudes de Kafka, incluidos topic, API key y client ID.</p>
    </details>

18. **¿Qué permite la regla 'matchPattern' en la política DNS L7 de Cilium?**
    - A) Coincidencia exacta de nombres de dominio
    - B) Coincidencia de patrones de nombres de dominio con comodines
    - C) Coincidencia de direcciones IP
    - D) Coincidencia de números de puerto

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Coincidencia de patrones de nombres de dominio con comodines</p>
    <p><strong>Explicación</strong>: La regla matchPattern puede coincidir con patrones de nombres de dominio, incluidos comodines (*). Ejemplo: *.example.com</p>
    </details>

19. **¿Qué atributos se pueden filtrar en la política gRPC L7 de Cilium?**
    - A) Nombre del método
    - B) Nombre del service
    - C) Metadatos
    - D) Todos los anteriores

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Todos los anteriores</p>
    <p><strong>Explicación</strong>: La política gRPC L7 de Cilium puede filtrar diversos atributos de las solicitudes gRPC, incluidos el nombre del método, el nombre del service y los metadatos.</p>
    </details>

20. **¿Qué componente se necesita para aplicar la política L7 de Cilium?**
    - A) kube-proxy
    - B) Envoy Proxy
    - C) NGINX Ingress Controller
    - D) HAProxy

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Envoy Proxy</p>
    <p><strong>Explicación</strong>: Cilium utiliza Envoy Proxy para aplicar políticas L7.</p>
    </details>
