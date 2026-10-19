# Parte 8: Cuestionario sobre los componentes internos del datapath de eBPF

> **Cilium 1.20.2 · 2026-10-15**

1. **En Cilium 1.20, ¿qué mecanismo de asociación se usa para los programas por dispositivo cuando el kernel lo admite, y qué ocurre en caso contrario?**
   - A) Siempre se usan filtros `clsact` heredados; tcx solo se usa con netkit
   - B) `bpf_link` de tcx (kernel 6.6 o posterior); de lo contrario, `clsact` + `cls_bpf` en modo direct-action
   - C) XDP en todos los veth; en caso contrario, el agente se niega a iniciar
   - D) Hooks cgroup en todas las interfaces; en caso contrario, iptables

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) `bpf_link` de tcx (kernel 6.6 o posterior); de lo contrario, `clsact` + `cls_bpf` en modo direct-action**

   `bpf.enableTCX` tiene el valor predeterminado `true`. El enlace se fija bajo `/sys/fs/bpf/cilium/...` y se actualiza de forma atómica durante la recarga. El agente solo falla si no funciona ni tc-bpf ni tcx.

   </details>

2. **El tráfico de Pod a Pod en el mismo nodo usa el enrutamiento de host de BPF y `bpf_redirect_peer`. ¿Dónde se aplica la política de ingreso del Pod de destino?**
   - A) En el programa `bpf_lxc` del emisor, que realiza una llamada encadenada a `cilium_call_policy[destination endpoint ID]`
   - B) En el hook tc de salida del veth de destino, mediante el mapa de políticas fijado para el endpoint emisor
   - C) En una cadena iptables en el espacio de nombres de red del destino, que el agente instala para cada endpoint
   - D) En el programa XDP de la NIC del nodo, antes de que el paquete llegue a un veth

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) En el programa `bpf_lxc` del emisor, que realiza una llamada encadenada a `cilium_call_policy[destination endpoint ID]`**

   `redirect_peer` omite el hook tc de salida del destino, así que `cil_lxc_policy` del destino se almacena en una matriz global de programas y la invoca el emisor. Una ranura vacía genera `DROP_EP_NOT_READY`.

   </details>

3. **¿Cuál es el tipo y la estructura de claves del mapa de políticas por endpoint `cilium_policy_v3_<id>`?**
   - A) HASH con clave de dirección IP del Pod remoto y puerto de destino
   - B) ARRAY indexada por número de puerto, con una ranura por protocolo
   - C) PROG_ARRAY indexada por número de regla de política, con una llamada encadenada a un programa por regla
   - D) LPM_TRIE con clave de identidad, dirección, protocolo y prefijo de puerto

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) LPM_TRIE con clave de identidad, dirección, protocolo y prefijo de puerto**

   La clave contiene `sec_label`, un bit `egress`, `protocol` y `dport`. El prefijo de puerto permite guardar un rango de puertos en unas pocas entradas, y un `sec_label` de 0 actúa como comodín L3.

   </details>

4. **Un tutorial recomienda inspeccionar `cilium_tunnel_map` para encontrar el nodo remoto de un destino overlay en Cilium 1.20. ¿Qué es correcto?**
   - A) Usar `cilium-dbg bpf tunnel list` para volcar la tabla de nodos a endpoints
   - B) El mapa existe, pero solo se llena cuando está habilitado el cifrado IPsec o WireGuard
   - C) El mapa ya no existe; el endpoint del túnel es un campo del valor de `cilium_ipcache_v2`
   - D) El mapa ahora es por endpoint, se llama `cilium_tunnel_map_<id>` y contiene una entrada por nodo

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) El mapa ya no existe; el endpoint del túnel es un campo del valor de `cilium_ipcache_v2`**

   Ningún código BPF de 1.20 hace referencia a `cilium_tunnel_map`. `cilium_ipcache_v2` (LPM_TRIE) devuelve `sec_identity` y `tunnel_endpoint` junto con `flag_has_tunnel_ep`. Usa `cilium-dbg bpf ipcache list`.

   </details>

5. **¿Cuál es el valor predeterminado de `--bpf-map-dynamic-size-ratio` en 1.20.2 y qué mapas dimensiona?**
   - A) 0.0025 de la RAM; mapas CT, NAT, vecinos de NodePort y socket reverse-NAT
   - B) 0 (deshabilitado); solo los mapas de políticas, dimensionados por `--bpf-policy-map-max`
   - C) 0.25 de la RAM; todos los mapas BPF, incluidos los mapas LB y el ipcache
   - D) 0.0025 de la RAM; solo el ipcache y los mapas de políticas

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) 0.0025 de la RAM; mapas CT, NAT, vecinos de NodePort y socket reverse-NAT**

   El dimensionamiento dinámico está activado de forma predeterminada. Configurar una marca de tamaño, como `--bpf-ct-global-tcp-max`, deshabilita el dimensionamiento dinámico únicamente para ese mapa. Los mapas LB usan `--bpf-lb-map-max`.

   </details>

6. **¿Qué controla `--bpf-lb-map-max` (valor predeterminado 65536)?**
   - A) Solo el mapa `cilium_lb4_services_v2`; los backends y rev-NAT conservan sus propios valores predeterminados
   - B) La cantidad de backends por Service; se rechazan los endpoints adicionales al superar el límite
   - C) El tamaño de la tabla de búsqueda Maglev, que debe ser un número primo de una lista fija
   - D) El tamaño de reserva para seis opciones por mapa LB (services, backends, rev-NAT, affinity, source-range y Maglev)

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) El tamaño de reserva para seis opciones por mapa LB (services, backends, rev-NAT, affinity, source-range y Maglev)**

   Cada una de las seis opciones por mapa tiene el valor predeterminado 0, que significa «usar `lb-map-max`». El tamaño de la tabla Maglev se controla mediante una marca aparte. Al cambiar el tamaño, se vuelven a crear los mapas y se interrumpen las conexiones hasta que se llenan de nuevo.

   </details>

7. **Con socket-LB habilitado, ¿dónde se traduce un ClusterIP y cómo sigue viendo la aplicación la dirección del Service en las respuestas?**
   - A) En el veth mediante DNAT en cada paquete; `cilium_lb4_reverse_nat` la restaura en la ruta de respuesta
   - B) En `connect()`/`sendmsg()` mediante hooks cgroup; los hooks `recvmsg`/`getpeername` usan `cilium_lb4_reverse_sk` para restaurarla
   - C) Mediante DNAT iptables de kube-proxy en el espacio de nombres de red del host; conntrack restaura la dirección original
   - D) En la NIC mediante XDP antes de que la pila vea el paquete; el relé de Hubble la restaura

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) En `connect()`/`sendmsg()` mediante hooks cgroup; los hooks `recvmsg`/`getpeername` usan `cilium_lb4_reverse_sk` para restaurarla**

   No se realiza DNAT en el tráfico de red, por lo que tcpdump en el Pod muestra la IP del backend. La ruta por paquete que usa `cilium_lb4_reverse_nat` solo se aplica cuando no se puede usar socket-LB (por ejemplo, en modo exclusivo del espacio de nombres de host, L7 LB o SCTP).

   </details>

8. **Un paquete llega a `cilium_vxlan` en modo overlay. ¿Cómo obtiene `cil_from_overlay` la identidad de origen?**
   - A) Lee el ID del túnel (VNI) con `bpf_skb_get_tunnel_key`, que el emisor estableció con su identidad de origen
   - B) Busca la IP de origen externa en `cilium_lxc`, que asigna identidades a las IP de los nodos
   - C) Lee un encabezado HTTP que el proxy Envoy local inyectó en la solicitud
   - D) Analiza la identidad a partir del nombre del Pod de origen mediante la caché de etiquetas del endpoint

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Lee el ID del túnel (VNI) con `bpf_skb_get_tunnel_key`, que el emisor estableció con su identidad de origen**

   Se rechaza una identidad de host en el ID del túnel con `DROP_INVALID_IDENTITY`. En el enrutamiento nativo no hay VNI, por lo que la identidad de origen se obtiene de `cilium_ipcache_v2` mediante la IP de origen (o de marcas con IPsec/WireGuard).

   </details>

9. **Un administrador edita una CiliumNetworkPolicy. ¿Qué hace el agente con el datapath?**
   - A) Vuelve a compilar `bpf_lxc.c` con clang para cada endpoint afectado y recarga el programa en su veth
   - B) Reemplaza los enlaces tcx fijados en todos los dispositivos para que la nueva política se aplique de forma atómica
   - C) Actualiza las entradas de `cilium_policy_v3_<id>`; solo recarga los programas si cambia el hash de configuración del endpoint o del nodo
   - D) Reinicia el Pod del agente Cilium para que todos los endpoints regeneren sus programas

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Actualiza las entradas de `cilium_policy_v3_<id>`; solo recarga los programas si cambia el hash de configuración del endpoint o del nodo**

   Los cambios de políticas se realizan mediante operaciones de mapa (`RegenerateWithoutDatapath`). Los objetos de plantilla se almacenan en caché por hash de configuración de plantilla y los valores por endpoint residen en `.rodata.config`.

   </details>

10. **¿Qué afirmación sobre la canalización de eventos de Hubble en 1.20 es correcta?**
    - A) BPF escribe en un búfer circular que Hubble Relay lee directamente del sistema de archivos BPF de cada nodo
    - B) Los eventos van a `cilium_events` (matriz de eventos perf), luego al monitor del agente y a una cola de Hubble, y finalmente a un búfer circular en memoria (4095 flujos)
    - C) El agente persiste los flujos en disco y los reproduce para Hubble Relay después de un reinicio
    - D) Los programas de llamada en cadena de `bpf_lxc` emiten los eventos L7 cuando coincide el mapa de redirección del proxy

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: B) Los eventos van a `cilium_events` (matriz de eventos perf), luego al monitor del agente y a una cola de Hubble, y finalmente a un búfer circular en memoria (4095 flujos)**

    Puede haber pérdidas en el búfer perf (`perf_event_ring_buffer`) o en la cola del observador (`observer_events_queue`). Los registros L7 proceden de Envoy y del proxy DNS como eventos del agente, no de BPF.

    </details>
