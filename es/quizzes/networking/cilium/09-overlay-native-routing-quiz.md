# Cuestionario de análisis detallado de overlay y enrutamiento nativo: parte 9

> **Cilium 1.20.2 · 2026-10-15**

## Mecánica de túneles

1. **¿Qué coloca Cilium en el VNI de 24 bits de un paquete encapsulado?**
   - A) El ID del nodo de destino
   - B) La identidad de seguridad de origen del endpoint emisor
   - C) El ID del clúster de Cilium
   - D) Un valor aleatorio por nodo que el receptor asigna mediante `cilium_tunnel_map`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) La identidad de seguridad de origen del endpoint emisor**

   El VNI contiene la identidad de origen (`world-ipv4`/`world-ipv6` se envían como `world`, y `host` se reescribe como `remote-node`). El receptor también tiene ipcache, así que el VNI es una optimización, no la única fuente de verdad. `cilium_tunnel_map` se eliminó del datapath en 1.18 (el agente solo quita el pin de un mapa residual) y su paquete Go se eliminó en 1.19; los endpoints de túnel residen en el valor de ipcache.

   </details>

2. **¿En qué se diferencia Geneve de VXLAN con respecto al transporte de identidad en Cilium?**
   - A) Geneve transporta la identidad en una opción TLV; VXLAN la transporta en el VNI
   - B) Geneve no transporta identidad; la política se evalúa solo en el emisor
   - C) Geneve usa el puerto UDP de origen externo para transportar la identidad
   - D) No hay diferencia: en ambos la identidad está en el VNI, y las opciones Geneve solo se usan para la dirección y el puerto del servicio DSR

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) No hay diferencia: en ambos la identidad está en el VNI, y las opciones Geneve solo se usan para la dirección y el puerto del servicio DSR**

   La única opción Geneve que inserta Cilium (clase `0x014B`, tipo `0x81`) es para DSR. El rango de puertos de origen externos (`tunnelSourcePortRange`) solo afecta la entropía y no interviene en la identidad.

   </details>

3. **En modo túnel, ¿qué componente crea los encabezados UDP/IP externos?**
   - A) El programa `bpf_lxc`, que escribe los encabezados en el paquete
   - B) El cilium-agent en espacio de usuario
   - C) El controlador vxlan/geneve del kernel detrás del dispositivo `cilium_vxlan`/`cilium_geneve` basado en flujo, después de que BPF establece la clave de túnel y lo redirige allí
   - D) El firmware de la NIC

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) El controlador vxlan/geneve del kernel detrás del dispositivo `cilium_vxlan`/`cilium_geneve` basado en flujo, después de que BPF establece la clave de túnel y lo redirige allí**

   BPF llama a `bpf_skb_set_tunnel_key` y redirige el paquete al ifindex del dispositivo de túnel; el controlador del kernel realiza la encapsulación. En el lado receptor, el kernel desencapsula y `cil_from_overlay` lee la clave de túnel.

   </details>

4. **¿Qué ocurre si se establece `routingMode: tunnel` junto con `autoDirectNodeRoutes: true` en Cilium 1.20.2?**
   - A) El agente termina con un error fatal porque los paquetes deben pasar por el dispositivo de túnel
   - B) Cilium usa rutas directas dentro de una subred y túneles entre subredes
   - C) El indicador se ignora con una advertencia
   - D) Cilium vuelve al enrutamiento nativo

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) El agente termina con un error fatal porque los paquetes deben pasar por el dispositivo de túnel**

   La comprobación es `TunnelingEnabled() && EnableAutoDirectRouting` en `daemon_main.go`. No hay fallback por subred. El mensaje de v1.21.0-pre.3 dice «requires native routing mode», pero sigue siendo un error fatal.

   </details>

## MTU, masquerading y enrutamiento del host

5. **En un underlay de 1500 bytes con underlay IPv4, y con VXLAN y WireGuard habilitados, ¿qué MTU de ruta ve un pod?**
   - A) 1450
   - B) 1405
   - C) 1373
   - D) 1355

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) 1355**

   La MTU de ruta es la MTU base menos la sobrecarga (WireGuard 95 + túnel 50). 1450 corresponde solo a VXLAN; 1405, al enrutamiento nativo con WireGuard; y 1373, a VXLAN con IPsec (50 + 77).

   </details>

6. **¿Qué configuración se requiere para usar DSR en `routingMode: tunnel`?**
   - A) VXLAN con `dsrDispatch: opt`
   - B) `tunnelProtocol: geneve` con `loadBalancer.dsrDispatch: geneve`
   - C) VXLAN con `loadBalancer.mode: hybrid`
   - D) Cualquier protocolo de túnel con `dsrDispatch: ipip`, sin otros cambios

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) `tunnelProtocol: geneve` con `loadBalancer.dsrDispatch: geneve`**

   El agente rechaza `dsr`/`hybrid` con túneles VXLAN, exige el envío Geneve para DSR en modo túnel y requiere el protocolo de túnel Geneve para el envío Geneve.

   </details>

7. **Se establece `bpf.datapathMode: auto` en un nodo cuyo kernel no tiene netkit. ¿Qué ocurre?**
   - A) El agente no se inicia
   - B) El agente cambia a `netkit-l2`
   - C) El agente recurre a veth y registra una advertencia; si se hubiera especificado `netkit`, habría fallado de forma definitiva
   - D) El agente sigue intentando usar netkit e impide la creación de pods

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) El agente recurre a veth y registra una advertencia; si se hubiera especificado `netkit`, habría fallado de forma definitiva**

   `auto` (nuevo en 1.20) sondea y rebaja con el registro «datapath autodiscovery failed, reverting from netkit to veth». Netkit también requiere BPF masquerade, KPR y que no se use el enrutamiento heredado del host.

   </details>

8. **El enrutamiento BPF del host es el valor predeterminado, pero se dejó activado el masquerading de iptables y se habilitó el reemplazo de kube-proxy. ¿Qué hace el agente?**
   - A) Registra que el enrutamiento BPF del host requiere BPF masquerade y recurre silenciosamente al enrutamiento heredado del host
   - B) Se niega a iniciarse
   - C) Habilita BPF masquerade automáticamente
   - D) Deshabilita el reemplazo de kube-proxy

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Registra que el enrutamiento BPF del host requiere BPF masquerade y recurre silenciosamente al enrutamiento heredado del host**

   El enrutamiento del host es de mejor esfuerzo. Las funciones solicitadas explícitamente por nombre que lo requieren (netkit, BBR para pods, BIG TCP) fallan de forma definitiva. Verifícalo con el campo `Host:` de la línea `Routing:` en `cilium-dbg status` (`Host: Legacy`).

   </details>

9. **¿A qué limita `kubernetes.io/egress-bandwidth: "10M"` el tráfico de un pod cuando está habilitado el administrador de ancho de banda?**
   - A) 10 MB/s
   - B) 10 Mbit/s por ReplicaSet
   - C) Nada, salvo que también se habilite BBR
   - D) 10 Mbit/s

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) 10 Mbit/s**

   El valor es una cantidad de Kubernetes en bits. El egreso se aplica por pod con EDT y FQ; BBR es opcional. Con IPsec, el administrador se deshabilita silenciosamente.

   </details>

10. **Con BPF masquerade y los ajustes predeterminados, ¿cómo se trata el tráfico de pod a nodo remoto?**
    - A) Siempre se enmascara
    - B) Nunca se enmascara
    - C) No se enmascara en el enrutamiento nativo, pero sí en modo túnel (salvo que la entrada de ipcache tenga `skip_tunnel`)
    - D) Solo se enmascara si el destino está fuera de los rangos RFC1918

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: C) No se enmascara en el enrutamiento nativo, pero sí en modo túnel (salvo que la entrada de ipcache tenga `skip_tunnel`)**

    Este es el paso 5 del orden de decisión en `bpf/lib/nat.h`. `enable-remote-node-masquerade=true` (1.19 o posterior, configurado mediante `extraConfig`) hace que ambos modos usen masquerade.

    </details>
