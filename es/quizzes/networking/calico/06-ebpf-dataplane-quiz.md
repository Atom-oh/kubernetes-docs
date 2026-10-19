# Cuestionario sobre el dataplane eBPF

> **Documento relacionado**: [Dataplane eBPF](../../../networking/calico/06-ebpf-dataplane.md)
> **Última actualización**: 12 de septiembre de 2026

## Cuestionario

1. ¿Cuál es la versión mínima genérica del kernel de Linux que indica la guía actual de eBPF de Calico 3.32, sin contar la excepción de backport de RHEL?
   - A) 4.15+
   - B) 5.0+
   - C) 5.3+
   - D) 5.10+

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) 5.10+**

**Explicación:**
La versión base genérica es 5.10. La guía documenta RHEL 8.4 con el kernel 4.18.0-305 o posterior como excepción con backport. Algunas funciones requieren versiones más recientes: las reglas de registro eBPF requieren 5.16 y los controles de ancho de banda QoS documentados requieren 6.6/TCX. La versión del sistema operativo o del kernel, por sí sola, no demuestra la compatibilidad completa de la plataforma.

</details>

2. ¿Cómo se debe evaluar la mejora de rendimiento al cambiar al dataplane eBPF de Calico?
   - A) Aumento del caudal del 5–10 %
   - B) Medir la carga de trabajo y la configuración reales; no hay un porcentaje universal
   - C) Aumento del caudal del 50–60 %
   - D) Aumento del caudal del 100 %

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Medir la carga de trabajo y la configuración reales; no hay un porcentaje universal**

**Explicación:**
Ambos dataplanes procesan paquetes en el kernel. La mejora depende de la ruta del tráfico, las reglas, conntrack, la CPU y la NIC, el registro y la carga. La guía conserva distintos valores históricos reportados sin evidencia sin procesar; no garantizan una mejora del 20–40 % ni un costo constante de las políticas.

</details>

3. ¿Qué significa BTF y por qué es importante para el dataplane eBPF de Calico?
   - A) Binary Transfer Format: para codificar paquetes de red
   - B) BPF Type Format: para depuración y compatibilidad con CO-RE
   - C) Byte Translation Function: para convertir direcciones
   - D) Block Transfer Filter: para limitar la velocidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) BPF Type Format: para depuración y compatibilidad con CO-RE**

**Explicación:**
BTF proporciona metadatos de tipos que utilizan las herramientas y la reubicación CO-RE. Es distinto de las comprobaciones de seguridad del verificador y no garantiza que todos los programas compilados funcionen en cualquier kernel. Calico selecciona objetos según la versión y comprueba las funciones disponibles; que exista un archivo no basta para confirmar que todo esté listo.

</details>

4. ¿Qué es Direct Server Return (DSR) en el contexto del dataplane eBPF de Calico?
   - A) Un método para que los Pods contacten directamente con el servidor de API de Kubernetes
   - B) Una optimización de balanceo de carga en la que el tráfico de retorno evita el balanceador de carga
   - C) Una técnica de resolución DNS para descubrir servicios
   - D) Un patrón de acceso al almacenamiento para volúmenes persistentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una optimización de balanceo de carga en la que el tráfico de retorno evita el balanceador de carga**

**Explicación:**
DSR permite que un nodo backend remoto devuelva el tráfico sin pasar por el nodo de Kubernetes que reenvió inicialmente la solicitud del Service. Calico realiza la traducción de origen. Se necesita una estructura de red y una ruta de retorno compatibles; DSR no evita automáticamente todos los balanceadores de carga de nube externos ni funciona con cualquiera de ellos.

</details>

5. ¿Qué es el balanceo de carga en el momento de la conexión en el dataplane eBPF de Calico?
   - A) Balanceo de carga que ocurre cuando un nodo se une al clúster
   - B) Traducción de la IP del Service al establecer una conexión TCP
   - C) Un mecanismo de comprobación de estado de los Pods backend
   - D) Conmutación por error automática cuando se interrumpen las conexiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Traducción de la IP del Service al establecer una conexión TCP**

**Explicación:**
Para los sockets TCP compatibles, CTLB traduce el destino del Service durante `connect()`, antes de procesar los paquetes. El modo habilitado también puede incluir hooks para sockets UDP. Evita esa ruta de DNAT del Service, pero no todas las políticas, rutas, operaciones de conntrack ni otras formas de NAT. DSR es una optimización distinta para la ruta de retorno externo.

</details>

6. ¿Qué afirmación describe correctamente la coordinación de kube-proxy con eBPF de Calico?
   - A) kube-proxy siempre debe permanecer sin cambios junto con eBPF
   - B) Calico puede gestionar los Services coordinándose con kube-proxy según la plataforma
   - C) kube-proxy se actualiza automáticamente para usar eBPF
   - D) kube-proxy gestiona IPv6 mientras que eBPF gestiona IPv4

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Calico puede gestionar los Services coordinándose con kube-proxy según la plataforma**

**Explicación:**
Sigue el procedimiento del responsable de la instalación. El arranque automático condicional puede gestionar kube-proxy; las plataformas que conservan un proxy administrado deben deshabilitar la limpieza y configurar un servidor de estado de salud que no entre en conflicto. Una opción de limpieza, por sí sola, no habilita Services; eliminar kube-proxy tampoco es un procedimiento universal.

</details>

7. ¿Para qué se usan los mapas BPF en el dataplane eBPF de Calico?
   - A) Para almacenar datos de ubicación geográfica para el enrutamiento geográfico
   - B) Para almacenar datos de estado y configuración compartidos entre el kernel y el espacio de usuario
   - C) Para asociar nombres DNS con direcciones IP
   - D) Para crear diagramas de topología de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para almacenar datos de estado y configuración compartidos entre el kernel y el espacio de usuario**

**Explicación:**
Los mapas contienen datos de rutas, NAT, conntrack, afinidad y estructuras auxiliares de programas, contadores y conjuntos de IP. Las distintas familias usan tipos como hash, LRU hash y LPM trie, entre otros. Las políticas se compilan en programas BPF; no se almacenan todas en un único mapa universal de tuplas a acciones con tiempo constante.

</details>

8. ¿Cómo se compara XDP en modo nativo del controlador con los puntos de conexión TC?
   - A) XDP procesa los paquetes antes en la pila de red que TC
   - B) TC procesa los paquetes antes en la pila de red que XDP
   - C) XDP solo procesa tráfico de entrada y TC solo tráfico de salida
   - D) No hay diferencia; son alias

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) XDP procesa los paquetes antes en la pila de red que TC**

**Explicación:**
XDP conectado al controlador nativo puede actuar antes de que se asigne un skb, mientras que TC opera con el contexto de paquetes basado en skb. XDP genérico se ejecuta más tarde y ya tiene un skb. Importan la compatibilidad del controlador, el hardware y el programa; el nombre del hook no garantiza una ventaja fija de rendimiento.

</details>

9. ¿Qué ajuste de FelixConfiguration habilita el dataplane eBPF en Calico?
   - A) dataplaneMode: eBPF
   - B) bpfEnabled: true
   - C) useEBPF: yes
   - D) felixBackend: ebpf

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) bpfEnabled: true**

**Explicación:**
`bpfEnabled: true` es el campo de Felix que se usa en el procedimiento del manifiesto independiente. En las instalaciones del operador, se selecciona `Installation.spec.calicoNetwork.linuxDataplane: BPF`. Respeta quién administra la instalación, el acceso directo a la API, la coordinación del proxy y el procedimiento de transición compatible para todo el clúster.

</details>

10. ¿Qué controla el ajuste `bpfExternalServiceMode` en Calico?
    - A) Cómo acceden los Pods a servicios externos fuera del clúster
    - B) Cómo acceden los clientes externos a los Services NodePort y LoadBalancer
    - C) Qué servidores DNS externos se usan para descubrir servicios
    - D) El modo de autenticación del acceso a la API externa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cómo acceden los clientes externos a los Services NodePort y LoadBalancer**

**Explicación:**
Para los backends remotos de un Service, Tunnel usa el nodo de ingreso y la ruta del túnel tanto para la solicitud como para la respuesta; DSR encapsula la solicitud, pero la respuesta vuelve directamente desde el nodo backend. Ambos modos requieren la ruta VXLAN/MTU correspondiente. DSR añade restricciones de validación de origen y de balanceador de carga externo.

</details>

11. ¿Qué herramienta se usa habitualmente para depurar e inspeccionar los programas y mapas eBPF de Calico?
    - A) tcpdump
    - B) bpftool
    - C) netstat
    - D) iptables-save

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) bpftool**

**Explicación:**
`bpftool` inspecciona los ID, tipos y estados reales de los programas y mapas BPF. La imagen del nodo de Calico también incluye `calico-node -bpf`; consulta su subcomando de ayuda y proporciona argumentos completos, como `policy dump <interface> <hook>`. Un listado, por sí solo, no demuestra que la aplicación tenga conectividad.

</details>

12. ¿Qué enfoque es adecuado para migrar al dataplane de Calico 3.32?
    - A) Habilitar eBPF inmediatamente en todos los nodos a la vez
    - B) Deshabilitar kube-proxy primero y después habilitar eBPF
    - C) Verificar la compatibilidad y el acceso directo a la API y seguir el proceso coordinado de migración y reversión del responsable
    - D) Reinstalar Calico desde cero con eBPF habilitado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Verificar la compatibilidad y el acceso directo a la API y seguir el proceso coordinado de migración y reversión del responsable**

**Explicación:**
El arranque automático del operador tiene requisitos previos limitados; las demás instalaciones deben seguir el procedimiento manual y específico de su plataforma. No mantengas un canary persistente en modo mixto ni deshabilites todas las instancias de kube-proxy antes de una prueba preparada. La transición gradual oficial puede interrumpir el tráfico de NodePort y la reversión puede restablecer las conexiones.

</details>
