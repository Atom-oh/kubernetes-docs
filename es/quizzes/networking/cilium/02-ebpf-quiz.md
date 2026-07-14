# Cuestionario de eBPF de Cilium

> **Versión compatible**: Cilium 1.17, Linux Kernel 4.19+
> **Última actualización**: February 22, 2026

## Conceptos básicos de eBPF

1. **¿Qué significa eBPF?**
   - A) Extended Berkeley Packet Filter
   - B) Enhanced Berkeley Process Filter
   - C) Extended Binary Processing Framework
   - D) Enhanced Backend Processing Function

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) Extended Berkeley Packet Filter</p>
   <p><strong>Explicación</strong>: eBPF significa Extended Berkeley Packet Filter, que es una extensión de la tecnología BPF original.</p>
   </details>

2. **¿Dónde se ejecutan los programas eBPF?**
   - A) Espacio de usuario
   - B) Espacio del kernel
   - C) Hipervisor
   - D) Container Runtime

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Espacio del kernel</p>
   <p><strong>Explicación</strong>: Los programas eBPF se ejecutan de forma segura dentro del kernel de Linux.</p>
   </details>

3. **¿Qué mecanismo garantiza la seguridad de los programas eBPF?**
   - A) Sandbox
   - B) Máquina virtual
   - C) Verificador estático
   - D) Contenerización

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) Verificador estático</p>
   <p><strong>Explicación</strong>: El verificador de eBPF comprueba la seguridad del programa antes de cargarlo para evitar bucles infinitos o fallos del kernel.</p>
   </details>

4. **¿Cómo se denominan los eventos del kernel a los que pueden adjuntarse los programas eBPF?**
   - A) Disparadores
   - B) Hooks
   - C) Detectores de eventos
   - D) Callbacks

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Hooks</p>
   <p><strong>Explicación</strong>: Los programas eBPF se adjuntan a varios puntos de hook en el kernel y se ejecutan cuando ocurren eventos.</p>
   </details>

5. **¿Qué se utiliza para compartir datos entre programas eBPF y aplicaciones de espacio de usuario?**
   - A) Memoria compartida
   - B) Pipes
   - C) BPF Maps
   - D) Sockets

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) BPF Maps</p>
   <p><strong>Explicación</strong>: BPF Maps son almacenes de clave-valor utilizados para compartir datos entre programas eBPF y aplicaciones de espacio de usuario.</p>
   </details>

## eBPF y Cilium

6. **¿Cuál es la razón principal por la que Cilium utiliza eBPF?**
   - A) Implementar funciones de red sin módulos del kernel
   - B) Proporcionar una mejor interfaz de usuario
   - C) Usar menos memoria
   - D) Proceso de instalación más sencillo

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) Implementar funciones de red sin módulos del kernel</p>
   <p><strong>Explicación</strong>: Cilium utiliza eBPF para implementar redes de alto rendimiento, balanceo de carga, políticas de seguridad y otras funciones sin módulos del kernel.</p>
   </details>

7. **¿Cuál NO es una función implementada mediante eBPF en Cilium?**
   - A) Aplicación de políticas de red
   - B) Balanceo de carga de Service
   - C) Cifrado de paquetes de red
   - D) Autenticación de usuarios

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: D) Autenticación de usuarios</p>
   <p><strong>Explicación</strong>: Cilium utiliza eBPF para implementar la aplicación de políticas de red, el balanceo de carga de Service y el procesamiento de paquetes de red, pero la autenticación de usuarios normalmente la gestionan otros sistemas.</p>
   </details>

8. **¿Qué función de eBPF utiliza Cilium para reemplazar kube-proxy?**
   - A) XDP (eXpress Data Path)
   - B) TC (Traffic Control) BPF
   - C) Socket BPF
   - D) Tracing BPF

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) TC (Traffic Control) BPF</p>
   <p><strong>Explicación</strong>: Cilium utiliza principalmente programas TC (Traffic Control) BPF para reemplazar la funcionalidad de balanceo de carga de Service de kube-proxy.</p>
   </details>

9. **¿Por qué el balanceo de carga basado en eBPF de Cilium es superior a kube-proxy?**
   - A) Admite más tipos de Service
   - B) Mejor interfaz de usuario
   - C) Menor latencia y mayor rendimiento
   - D) Configuración más sencilla

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: C) Menor latencia y mayor rendimiento</p>
   <p><strong>Explicación</strong>: El balanceo de carga basado en eBPF de Cilium procesa paquetes directamente en el espacio del kernel, lo que proporciona menor latencia y mayor rendimiento.</p>
   </details>

10. **¿Cuál NO es una métrica recopilada mediante eBPF en Cilium?**
    - A) Estado de conexión de red
    - B) Motivos de descarte de paquetes
    - C) Tiempo de respuesta de Service
    - D) Hora de inicio de sesión de usuario

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Hora de inicio de sesión de usuario</p>
    <p><strong>Explicación</strong>: Cilium utiliza eBPF para recopilar métricas relacionadas con la red, como el estado de conexión de red, los motivos de descarte de paquetes y el tiempo de respuesta de Service, pero no recopila métricas de nivel de aplicación como la hora de inicio de sesión de usuario.</p>
    </details>

## Programación de eBPF

11. **¿Qué lenguaje se utiliza principalmente para escribir programas eBPF?**
    - A) Python
    - B) Go
    - C) C
    - D) Rust

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) C</p>
    <p><strong>Explicación</strong>: Los programas eBPF se escriben principalmente en C y se compilan a bytecode de eBPF mediante el compilador LLVM.</p>
    </details>

12. **¿Cuál NO es un framework para desarrollar programas eBPF?**
    - A) BCC (BPF Compiler Collection)
    - B) libbpf
    - C) bpftrace
    - D) libpcap

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) libpcap</p>
    <p><strong>Explicación</strong>: libpcap es una biblioteca de captura de paquetes y no es un framework para el desarrollo de programas eBPF. BCC, libbpf y bpftrace son frameworks para desarrollar programas eBPF.</p>
    </details>

13. **¿Cuál NO es un tipo de mapa de eBPF?**
    - A) Hash Map
    - B) Array Map
    - C) LRU Map
    - D) Graph Map

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Graph Map</p>
    <p><strong>Explicación</strong>: eBPF admite varios tipos de mapas, incluidos hash maps, array maps y LRU maps, pero no admite graph maps.</p>
    </details>

14. **¿Cuál es el número máximo de instrucciones en un programa eBPF?**
    - A) 1,000
    - B) 4,096
    - C) 10,000
    - D) Ilimitado

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) 4,096</p>
    <p><strong>Explicación</strong>: Los programas eBPF están limitados a un máximo de 4,096 instrucciones. Este límite garantiza la seguridad.</p>
    </details>

15. **¿Qué llamada al sistema se utiliza para cargar programas eBPF en el kernel?**
    - A) bpf()
    - B) ebpf()
    - C) sysfs()
    - D) ioctl()

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) bpf()</p>
    <p><strong>Explicación</strong>: La llamada al sistema bpf() se utiliza para cargar programas eBPF en el kernel y para crear y acceder a mapas de eBPF.</p>
    </details>

## Rendimiento y monitorización de eBPF

16. **¿Cuál es el principal beneficio proporcionado por XDP (eXpress Data Path)?**
    - A) Mejor seguridad
    - B) Programación más sencilla
    - C) Menor latencia
    - D) Mayor compatibilidad

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) Menor latencia</p>
    <p><strong>Explicación</strong>: XDP procesa paquetes en el nivel del controlador de red, evitando la pila de red del kernel para proporcionar una latencia muy baja.</p>
    </details>

17. **¿Qué herramienta se utiliza para monitorizar el rendimiento de los programas eBPF en Cilium?**
    - A) top
    - B) bpftool
    - C) htop
    - D) iotop

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) bpftool</p>
    <p><strong>Explicación</strong>: bpftool es una herramienta utilizada para inspeccionar y gestionar programas y mapas de eBPF, y también se utiliza para la monitorización del rendimiento.</p>
    </details>

18. **¿Cuál es la herramienta de monitorización de red basada en eBPF de Cilium?**
    - A) Prometheus
    - B) Hubble
    - C) Grafana
    - D) Jaeger

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: B) Hubble</p>
    <p><strong>Explicación</strong>: Hubble es la herramienta de monitorización de red basada en eBPF de Cilium que puede observar y analizar flujos de red en tiempo real.</p>
    </details>

19. **¿Qué herramienta se utiliza para encontrar cuellos de botella de rendimiento en programas eBPF?**
    - A) strace
    - B) ltrace
    - C) perf
    - D) gdb

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: C) perf</p>
    <p><strong>Explicación</strong>: perf es una herramienta de análisis de rendimiento de Linux utilizada para encontrar cuellos de botella de rendimiento en programas eBPF.</p>
    </details>

20. **¿Qué comando se utiliza para depurar programas eBPF en Cilium?**
    - A) `cilium bpf`
    - B) `cilium debug`
    - C) `cilium monitor`
    - D) `cilium trace`

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) `cilium bpf`</p>
    <p><strong>Explicación</strong>: El comando `cilium bpf` se utiliza para inspeccionar y depurar los programas y mapas de eBPF de Cilium.</p>
    </details>
