# Cuestionario avanzado de Cilium

> **Base de revisión**: Cilium 1.20.3; Cilium CLI 0.20.1; Hubble CLI 1.20.2.
> **Última revisión**: 16 de octubre de 2026.

[Volver a la guía](../../../networking/cilium/07-advanced-topics.md)

## Tecnología eBPF

1. **¿Dónde se ejecutan los programas eBPF del plano de datos de Linux que se analizan en este curso?**

   - A) Solo en un navegador
   - B) En hooks compatibles del kernel de Linux
   - C) Solo dentro de Envoy
   - D) En el servidor de API de Kubernetes

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) En hooks compatibles del kernel de Linux**

   Cilium conecta programas eBPF a hooks del kernel. Los componentes de espacio de usuario los cargan y administran.

   </details>

2. **¿Qué mecanismo comprueba un programa eBPF antes de que el kernel lo acepte?**

   - A) El cifrado
   - B) La planificación de contenedores
   - C) El verificador
   - D) DNS

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) El verificador**

   El verificador comprueba propiedades como el acceso a memoria y la ejecución acotada. No ofrece una garantía absoluta frente a vulnerabilidades de implementación ni a todos los fallos del kernel.

   </details>

3. **¿Cuál no es un requisito general del plano de datos eBPF por software de Cilium?**

   - A) Funciones compatibles del kernel
   - B) Privilegios adecuados
   - C) Una configuración de red compatible
   - D) Descarga de procesamiento a hardware dedicado

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Descarga de procesamiento a hardware dedicado**

   La descarga a hardware no es obligatoria. El rendimiento depende de la ruta, la carga de trabajo, el kernel y el hardware reales.

   </details>

## Modelos de red

4. **¿Cuál no es una de las opciones nativas o de túnel de Cilium descritas en este curso?**

   - A) VXLAN
   - B) Geneve
   - C) Enrutamiento nativo
   - D) Un modo de plano de datos MPLS

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Un modo de plano de datos MPLS**

   Esto describe las opciones de configuración de Cilium; no prohíbe usar una infraestructura de red subyacente externa basada en MPLS.

   </details>

5. **¿Qué implementa el reemplazo de kube-proxy de Cilium?**

   - A) Solo cadenas iptables
   - B) Solo reglas IPVS
   - C) Gestión de Services mediante eBPF, con aceleración XDP opcional
   - D) Un conmutador de hardware externo obligatorio

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Gestión de Services mediante eBPF, con aceleración XDP opcional**

   Los programas eBPF en la ruta de sockets y paquetes implementan la gestión de Services. XDP acelera rutas de reenvío externas compatibles; no es necesario para todos los Services.

   </details>

6. **¿Qué componente de observabilidad de Cilium expone registros de flujo con contexto de Kubernetes?**

   - A) Helm
   - B) Hubble
   - C) kube-scheduler
   - D) etcdctl

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Hubble**

   Hubble expone observaciones acotadas, no una captura sin pérdida de todos los paquetes. Las herramientas de análisis de paquetes tienen otras funciones.

   </details>

## IPAM y políticas de red

7. **¿Qué modo IPAM de Cilium usa ENI de EC2 para asignar direcciones de la VPC?**

   - A) Cluster pool
   - B) Ámbito de host de Kubernetes
   - C) ENI
   - D) Basado en CRD genéricas

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) ENI**

   El modo ENI usa interfaces de red y asignación de direcciones de AWS. Esto no significa que todos los modos de cómputo de EKS admitan un CNI alternativo; compruebe los requisitos previos de la plataforma.

   </details>

8. **¿Qué usa `toFQDNs` para permitir conexiones salientes?**

   - A) Un JWT verificado
   - B) Solo un puerto fijo de Service
   - C) Direcciones IP de destino aprendidas para nombres DNS coincidentes
   - D) Descifrado automático de TLS

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Direcciones IP de destino aprendidas para nombres DNS coincidentes**

   Permitir consultas DNS u observarlas mediante el proxy y permitir después la conectividad IP son aspectos distintos. La regla no autentica la aplicación remota.

   </details>

9. **¿Qué selector se usa para una política de host de nodos en un CiliumClusterwideNetworkPolicy?**

   - A) `endpointSelector` para todos los nodos
   - B) `nodeSelector`
   - C) Un `serviceSelector` de nivel superior
   - D) Un `namespaceSelector` de nivel superior

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) `nodeSelector`**

   `nodeSelector` es un campo de política de host para todo el clúster. No describa todas las formas de selector de Kubernetes como campos de nivel superior intercambiables de CiliumNetworkPolicy.

   </details>

## Redes L2-L7

10. **¿Cuál no es un campo de coincidencia de solicitudes en una política HTTP de Cilium?**

   - A) Ruta
   - B) Método
   - C) Encabezados
   - D) Latencia de respuesta

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Latencia de respuesta**

   Las reglas HTTP inspeccionan los campos de solicitud compatibles cuando HTTP está visible. Medir la latencia no añade un campo de reglas de permiso basado en latencia.

   </details>

11. **¿Qué no proporciona por sí sola una política de red basada en identidades?**

   - A) Selección de endpoints
   - B) Restricciones de acceso de red
   - C) Reglas específicas por dirección
   - D) Autenticación de tokens de usuario final

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Autenticación de tokens de usuario final**

   La autenticación de usuarios requiere la lógica adecuada en la aplicación o la puerta de enlace. La autenticación mutua con SPIRE y mTLS de cargas de trabajo con ztunnel Beta son funciones configuradas por separado y tienen sus propias limitaciones.

   </details>

12. **¿Qué puede proporcionar la integración de Cilium con Envoy cuando se configura en la ruta adecuada?**

   - A) Balanceo de carga HTTP
   - B) Visibilidad HTTP
   - C) Aplicación de políticas HTTP
   - D) Todo lo anterior

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Todo lo anterior**

   Estas funciones dependen de la ruta del proxy y de la configuración elegidas; habilitar una función de red distinta no activa todas las capacidades L7.

   </details>

## Seguridad y visibilidad

13. **¿Cuál es una función de Hubble UI?**

   - A) Crear incidentes automáticamente en Slack
   - B) Mapas de dependencias de Services y exploración de flujos
   - C) Administrar despliegues de código fuente
   - D) Rotar claves de firma JWT

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Mapas de dependencias de Services y exploración de flujos**

   Las notificaciones y respuestas automatizadas necesitan integraciones adicionales. La interfaz visualiza los flujos de red observados.

   </details>

14. **¿Qué modos alternativos de cifrado del transporte entre nodos ofrece Cilium?**

   - A) IPsec y WireGuard
   - B) HTTP y DNS
   - C) Relay y Prometheus
   - D) TCP y UDP

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) IPsec y WireGuard**

   Deben comprobarse su cobertura y requisitos previos. El tráfico dentro del mismo nodo no se cifra mediante túneles entre nodos, y mTLS de cargas de trabajo es una función distinta.

   </details>

15. **¿Qué capa de políticas coincide con los métodos y las rutas HTTP?**

   - A) Solo coincidencia de direcciones L2
   - B) Política L7
   - C) Solo coincidencia CIDR de L3
   - D) Cifrado del transporte

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Política L7**

   La política HTTP actual de Cilium puede inspeccionar estos campos; se eliminaron las reglas para temas de Kafka. La coincidencia de encabezados no equivale a autenticar tokens.

   </details>

## Temas avanzados y casos de uso

16. **¿Cuál no es una capacidad de ClusterMesh?**

   - A) Descubrimiento de Services entre clústeres
   - B) Uso de identidades de endpoints remotos en políticas
   - C) Balanceo de carga de Services entre clústeres
   - D) Almacenamiento persistente compartido

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Almacenamiento persistente compartido**

   ClusterMesh gestiona metadatos y conectividad de red. No proporciona almacenamiento compartido ni replica automáticamente todos los recursos de políticas.

   </details>

17. **¿Qué descripción de Bandwidth Manager es correcta?**

   - A) Solo muestra gráficos de ancho de banda
   - B) Aplica los límites de ancho de banda configurados por Pod
   - C) Garantiza una reserva de capacidad del enlace físico para cada Pod
   - D) Predice el tráfico futuro mediante aprendizaje automático

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Aplica los límites de ancho de banda configurados por Pod**

   El tráfico de salida usa EDT y el de entrada, un token bucket de eBPF. Los límites se aplican por Pod, con las limitaciones documentadas para egress-L7 y kind; no son reservas de capacidad garantizadas.

   </details>

18. **¿Cuál es el ámbito del cortafuegos de host de Cilium?**

   - A) Solo HTTP entre contenedores
   - B) Solo el cifrado del almacenamiento
   - C) El tráfico de red del host
   - D) La autorización de SaaS externo

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) El tráfico de red del host**

   El cortafuegos de host aplica políticas de red al nodo o host; no es un sistema general de control de llamadas al sistema en tiempo de ejecución.

   </details>

19. **¿Qué hace Egress Gateway con el tráfico saliente coincidente?**

   - A) Aplica SNAT para usar una IP de puerta de enlace seleccionada y predecible
   - B) Conserva siempre la IP de origen original del Pod
   - C) Cifra automáticamente todas las conexiones externas
   - D) Crea una IP pública en cualquier nube sin requisitos previos

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Aplica SNAT para usar una IP de puerta de enlace seleccionada y predecible**

   Es necesario aprovisionar las IP, interfaces y rutas de la puerta de enlace. Los Pods nuevos pueden enviar tráfico antes de que se aplique la política; también hay incompatibilidades con ClusterMesh y CiliumEndpointSlice.

   </details>

20. **¿Qué acción realiza Cilium BGP Control Plane?**

   - A) Instalar todas las rutas aprendidas en el plano de datos local de Linux
   - B) Anunciar a los peers prefijos seleccionados de Pods o Services
   - C) Crear registros DNS para todos los Services
   - D) Asignar interfaces de router externas

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Anunciar a los peers prefijos seleccionados de Pods o Services**

   El anuncio BGP es independiente del enrutamiento del plano de datos local, la asignación de direcciones y DNS. Compruebe el router externo y las rutas reales de ida y vuelta.

   </details>

## Rendimiento y solución de problemas

21. **¿Qué mecanismo puede gestionar el reenvío de Services externos compatible desde el hook del controlador nativo?**

   - A) Un panel de Grafana
   - B) Aceleración XDP
   - C) Un sufijo de búsqueda DNS
   - D) Un archivo de registro de aplicación más grande

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Aceleración XDP**

   XDP requiere una NIC, un controlador y una ruta compatibles. No se puede presuponer una mejora fija de latencia o rendimiento para cualquier carga de trabajo.

   </details>

22. **¿Qué comando independiente de Cilium CLI crea activamente cargas de trabajo para probar escenarios de conectividad?**

   - A) `cilium status`
   - B) `cilium connectivity test`
   - C) `hubble status`
   - D) `kubectl get nodes`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) `cilium connectivity test`**

   Es una prueba activa que crea recursos y genera tráfico, no una consulta de estado de solo lectura. Use un ámbito de prueba aislado y revise la limpieza.

   </details>

23. **Dentro del agente de Cilium propietario del endpoint, ¿qué comando muestra los detalles de un endpoint?**

   - A) `cilium endpoint list`
   - B) `cilium policy get`
   - C) `cilium-dbg endpoint get ENDPOINT_ID`
   - D) `cilium status --all-endpoints`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) `cilium-dbg endpoint get ENDPOINT_ID`**

   Obtenga el ID local del nodo en la lista de ese agente. Un ID de otro agente no tiene por qué identificar la misma carga de trabajo.

   </details>

24. **¿Qué comando local del agente enumera los mapas BPF abiertos que conoce el administrador de mapas?**

   - A) `cilium-dbg map list`
   - B) `cilium bpf maps`
   - C) `cilium status --maps`
   - D) `cilium bpf map list`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) `cilium-dbg map list`**

   No es un inventario de todos los mapas BPF del kernel. La respuesta anterior `cilium bpf maps` no era un comando válido.

   </details>

25. **¿Qué comando muestra los eventos locales emitidos por programas BPF de Cilium?**

   - A) `cilium tcpdump`
   - B) `cilium capture`
   - C) `cilium-dbg monitor`
   - D) `cilium packet-capture`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) `cilium-dbg monitor`**

   Muestra los tipos de eventos o trazas compatibles. La agregación, supresión y los búferes afectan a la visibilidad; no garantiza capturar todos los paquetes.

   </details>
