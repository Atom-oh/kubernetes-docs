# Cuestionario de seguridad y visibilidad de Cilium

> **Versión de referencia**: Cilium 1.20.3; Hubble CLI 1.20.2.
> **Última revisión**: 16 de octubre de 2026.

[Volver a la guía](../../../networking/cilium/06-security-visibility.md)

## Conceptos básicos de las políticas de red

1. **¿Cómo amplía CiliumNetworkPolicy la NetworkPolicy estándar de Kubernetes?**

   - A) No puede seleccionar Pods
   - B) Puede añadir reglas L7 para protocolos compatibles
   - C) Solo protege los nodos
   - D) Garantiza una latencia menor

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Puede añadir reglas L7 para protocolos compatibles**

   NetworkPolicy estándar controla la conectividad L3/L4. Cilium añade capacidades como políticas HTTP y DNS; la elección de API no garantiza un mejor rendimiento.

   </details>

2. **¿Qué versión de API usa CiliumNetworkPolicy?**

   - A) networking.k8s.io/v1
   - B) cilium.io/v2
   - C) policy.cilium.io/v1
   - D) network.cilium.io/v1

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) cilium.io/v2**

   El grupo es cilium.io y la versión de política servida que se usa en este capítulo es v2.

   </details>

3. **¿Qué selecciona endpointSelector en una CiliumNetworkPolicy con ámbito de namespace?**

   - A) Los endpoints coincidentes dentro del namespace de la política
   - B) Todos los nodos de Kubernetes
   - C) El servidor de Prometheus
   - D) Solo los Services de tipo LoadBalancer

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Los endpoints coincidentes dentro del namespace de la política**

   Identifica los endpoints que rige la política. Las políticas de nodos usan el mecanismo independiente clusterwide nodeSelector.

   </details>

4. **En una NetworkPolicy estándar con policyTypes: [Ingress], ¿qué valor no contiene reglas que permitan tráfico de entrada?**

   - A) ingress: [{}]
   - B) ingress: []
   - C) ingress: [{from: [{}]}]
   - D) Una regla que permite todas las direcciones de origen

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) ingress: []**

   Una lista vacía no añade ninguna regla de autorización; un objeto de regla vacío permite todo el tráfico de entrada. Las demás políticas de autorización aplicables siguen siendo aditivas.

   </details>

5. **¿Qué dirección controla la política de egress para los Pods seleccionados?**

   - A) Solo las conexiones entrantes
   - B) Las conexiones salientes
   - C) Solo el tráfico dentro de un proceso
   - D) Solo las respuestas del servidor de API

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Las conexiones salientes**

   Egress controla la conectividad saliente. Un Pod aislado necesita permisos explícitos para dependencias como su resolvedor DNS real.

   </details>

## Políticas L7

6. **¿Cuál de estos campos no es un criterio de coincidencia de solicitud en una política HTTP de Cilium?**

   - A) Ruta
   - B) Método
   - C) Encabezados
   - D) Latencia de respuesta

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Latencia de respuesta**

   La política HTTP coincide con atributos de solicitud compatibles. Poder observar la duración de una respuesta no convierte la latencia en un campo de regla HTTP que permita tráfico.

   </details>

7. **¿Qué se necesita para que la política toFQDNs ilustrada aprenda las respuestas DNS?**

   - A) Solo una regla TCP 443
   - B) Solo una IP externa arbitraria
   - C) Un resolvedor accesible y reglas coincidentes para el proxy DNS
   - D) Una regla para un tema de Kafka

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Un resolvedor accesible y reglas coincidentes para el proxy DNS**

   Permitir DNS y observarlo mediante el proxy es distinto de permitir después la IP de destino. El ejemplo cubre DNS por UDP y TCP hacia endpoints de resolvedor verificados.

   </details>

8. **¿Qué permite matchPattern en DNS?**

   - A) Asignar puertos
   - B) Buscar patrones comodín en nombres de dominio
   - C) Validar firmas JWT
   - D) Consultar automáticamente la reputación de dominios maliciosos

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Buscar patrones comodín en nombres de dominio**

   Coincide con nombres de consulta/dominio mediante la sintaxis comodín compatible. No obtiene una fuente de inteligencia sobre amenazas.

   </details>

9. **¿Qué proxy implementa las reglas HTTP descritas aquí?**

   - A) kube-proxy
   - B) Envoy
   - C) Prometheus
   - D) Hubble Relay

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Envoy**

   Cilium integra Envoy para las políticas HTTP. La política DNS usa el proxy DNS, por lo que no todas las reglas L7 deben describirse como reglas de Envoy.

   </details>

10. **¿Qué capacidad de políticas L7 de Cilium ya no está presente en la API actual?**

   - A) Coincidencia con el método HTTP
   - B) Coincidencia con la ruta HTTP
   - C) Reglas para temas de Kafka
   - D) Reglas para nombres DNS

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Reglas para temas de Kafka**

   Se eliminaron las políticas L7 de Kafka. No copie reglas kafka antiguas en recursos CiliumNetworkPolicy actuales.

   </details>

## Cifrado y seguridad

11. **¿Qué par nombra modos alternativos de cifrado del transporte entre nodos de Cilium?**

   - A) IPsec y WireGuard
   - B) HTTP y DNS
   - C) Relay y Grafana
   - D) SYN y ACK

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) IPsec y WireGuard**

   Seleccione el modo necesario y compruebe sus requisitos previos. La autenticación mutua de SPIRE y el mTLS de cargas de trabajo con ztunnel, que está en beta, son funciones distintas y tienen otros ámbitos.

   </details>

12. **¿Qué cubre el perfil predeterminado de túneles de nodo WireGuard del capítulo?**

   - A) Todos los paquetes, incluido cualquier tráfico externo
   - B) El tráfico compatible de Pods administrados por Cilium que cruza entre nodos
   - C) Todo el tráfico entre Pods del mismo nodo mediante el túnel
   - D) Todo el tráfico del host sin excepciones

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) El tráfico compatible de Pods administrados por Cilium que cruza entre nodos**

   El tráfico entre Pods del mismo nodo no usa estos túneles. El cifrado entre nodos es una opción beta independiente con exclusiones del plano de control; aun así, puede requerirse TLS en la aplicación.

   </details>

13. **¿Qué pretende proteger Cilium Host Firewall?**

   - A) Solo JavaScript del navegador
   - B) El tráfico de red del host
   - C) Todas las llamadas al sistema de los contenedores automáticamente
   - D) Una base de datos de contraseñas de Grafana

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) El tráfico de red del host**

   La política de host es un control de red. La aplicación de políticas de ejecución para procesos/llamadas al sistema corresponde a mecanismos independientes, como las políticas de Tetragon configuradas; también debe comprobarse la compatibilidad con el cifrado.

   </details>

14. **¿La coincidencia con un encabezado Authorization autentica su token bearer?**

   - A) Sí, cualquier encabezado presente es un JWT verificado
   - B) Sí, un valor que parece una expresión regular verifica las firmas
   - C) No; la coincidencia con el encabezado no valida el token
   - D) Sí, si HTTP usa el puerto 8443

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) No; la coincidencia con el encabezado no valida el token**

   Use lógica real de autenticación/autorización. Una cadena con valor en headers se compara literalmente, y el número de puerto TLS no descifra la carga útil.

   </details>

15. **¿Qué determina principalmente una identidad de seguridad de Cilium?**

   - A) Una IP de Pod única garantizada para siempre
   - B) El conjunto de etiquetas relevantes para la seguridad
   - C) La cookie del navegador del usuario
   - D) La última respuesta HTTP observada

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) El conjunto de etiquetas relevantes para la seguridad**

   Los endpoints que comparten etiquetas relevantes para la seguridad pueden compartir una identidad. La política basada solo en identidades no proporciona autenticación de usuarios finales ni cifrado del tráfico.

   </details>

## Visibilidad y monitorización

16. **¿Cuál es la función principal de Hubble?**

   - A) Observabilidad de flujos de red
   - B) Despliegue de imágenes de contenedor
   - C) Un WAF completo sin reglas
   - D) Aislamiento automático de todos los Pods sospechosos

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Observabilidad de flujos de red**

   Hubble expone metadatos de flujos, veredictos y observaciones de protocolos compatibles. Las reglas de detección y las integraciones de respuesta requieren una configuración independiente.

   </details>

17. **¿Qué capacidad ofrece Hubble UI?**

   - A) Rotar credenciales de aplicaciones
   - B) Mapas de dependencias entre Services y exploración de flujos
   - C) Enviar automáticamente incidentes a Slack
   - D) Instalar políticas de llamadas al sistema de ejecución

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Mapas de dependencias entre Services y exploración de flujos**

   La interfaz visualiza observaciones de red mediante Relay. No es un controlador de notificaciones, despliegues ni políticas de ejecución.

   </details>

18. **¿Qué comando sigue los eventos de flujo de cualquiera de los dos endpoints que coincidan con el Pod frontend?**

   - A) `hubble observe --pod cilium-security-demo/frontend --follow`
   - B) `hubble watch --pod frontend`
   - C) `cilium hubble status`
   - D) `hubble observe --pod app=frontend`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) `hubble observe --pod cilium-security-demo/frontend --follow`**

   Use el nombre del Pod con su namespace y --follow para recibir un flujo continuo. Los nombres de Pod no son selectores de etiquetas; los filtros direccionales y por etiquetas son opciones independientes.

   </details>

19. **¿Qué métrica no proporcionan los plugins de métricas ilustrados de Hubble?**

   - A) Recuentos de códigos de respuesta HTTP
   - B) Recuentos de indicadores TCP
   - C) Recuentos de paquetes descartados observados
   - D) Uso de CPU del contenedor

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Uso de CPU del contenedor**

   Esos plugins observan eventos de red/proxy. El plugin TCP no proporciona una métrica general de conexiones simultáneas o RTT, y deben tenerse en cuenta las observaciones faltantes o perdidas.

   </details>

20. **Si Prometheus Operator está instalado, ¿qué se necesita para recopilar métricas de Hubble mediante ServiceMonitor?**

   - A) Solo importar un dashboard de Grafana
   - B) Un destino público estático hubble-metrics.cilium.io:9091
   - C) Métricas habilitadas y un ServiceMonitor seleccionado por Prometheus
   - D) Solo crear un ConfigMap no relacionado

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Métricas habilitadas y un ServiceMonitor seleccionado por Prometheus**

   El Service headless del chart expone el puerto con nombre hubble-metrics, normalmente 9965. Los selectores de namespace/etiquetas de Prometheus y la accesibilidad del endpoint deben coincidir.

   </details>
