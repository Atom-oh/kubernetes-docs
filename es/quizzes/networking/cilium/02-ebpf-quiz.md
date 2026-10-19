# Cuestionario de eBPF de Cilium

> **Versión de referencia**: Cilium 1.20.3; Linux 5.10 o posterior, o backports equivalentes documentados; los ejemplos de límites usan Linux 6.12.
> **16 de octubre de 2026**


## Conceptos básicos de eBPF

1. **¿Qué significan las siglas eBPF?**
   - A) Extended Berkeley Packet Filter
   - B) Enhanced Berkeley Process Filter
   - C) Extended Binary Processing Framework
   - D) Enhanced Backend Processing Function

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: A) Extended Berkeley Packet Filter</p>
   <p><strong>Explicación</strong>: eBPF significa Extended Berkeley Packet Filter y es una extensión de la tecnología BPF original.</p>
   </details>

2. **¿Dónde se ejecutan los programas eBPF de Linux de esta guía cuando se activan sus hooks?**
   - A) Solo en el espacio de usuario
   - B) En el kernel
   - C) En Hubble Relay
   - D) En el proceso del runtime del contenedor

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) En el kernel**

   Estos programas se ejecutan en el kernel mediante la ruta compatible del intérprete o del JIT. Los cargadores y las herramientas de observación se ejecutan en el espacio de usuario. La ejecución en el kernel no garantiza seguridad absoluta.

   </details>

3. **¿Qué significa que el verificador BPF acepte un programa?**
   - A) Los fallos del kernel son imposibles
   - B) Se ha demostrado que la política prevista de la aplicación es correcta
   - C) El programa superó las comprobaciones de tipo, acceso a memoria y restricciones de ejecución
   - D) Ya no hacen falta más pruebas

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) El programa superó las comprobaciones de tipo, acceso a memoria y restricciones de ejecución**

   El verificador restringe la ejecución; siguen siendo posibles errores del verificador, del JIT, de los helpers y del kernel, así como errores en la lógica del programa.

   </details>

4. **¿Cómo se llaman los eventos del kernel a los que pueden asociarse programas eBPF?**
   - A) Disparadores
   - B) Hooks
   - C) Detectores de eventos
   - D) Callbacks

   <details>
   <summary>Mostrar respuesta</summary>
   <p><strong>Respuesta</strong>: B) Hooks</p>
   <p><strong>Explicación</strong>: Los programas eBPF se conectan a distintos puntos de hook del kernel y se ejecutan cuando ocurren eventos.</p>
   </details>

5. **¿Qué mecanismo comparte estado o eventos entre programas BPF y el espacio de usuario?**
   - A) Variables de entorno
   - B) Solo archivos ordinarios en disco
   - C) Mapas BPF
   - D) Anotaciones de Kubernetes

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Mapas BPF**

   Los mapas incluyen estructuras clave-valor, búferes de eventos y contenedores de referencias. Los pins conservan referencias, no el contenido de los mapas tras un reinicio; volver a cargar un programa no reutiliza automáticamente un mapa.

   </details>

## eBPF y Cilium

6. **¿Por qué eBPF puede ayudar a implementar el datapath de Cilium?**
   - A) Los hooks y mapas programables del kernel evitan crear un módulo personalizado nuevo por cada cambio del datapath
   - B) Elimina todas las dependencias de módulos del kernel
   - C) Configura automáticamente cualquier red en la nube
   - D) Garantiza un menor uso de memoria

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Los hooks y mapas programables del kernel evitan crear un módulo personalizado nuevo por cada cambio del datapath**

   Cilium utiliza funciones compatibles del kernel para el reenvío, las políticas y la traducción de servicios. Siguen siendo necesarios los requisitos de funciones del kernel y las pruebas específicas de cada carga de trabajo.

   </details>

7. **¿Qué afirmación describe correctamente los modos de cifrado WireGuard/IPsec de Cilium?**
   - A) Todas las operaciones criptográficas son instrucciones BPF
   - B) No se necesita configuración ni administrar claves
   - C) Siempre se cifra todo el tráfico
   - D) BPF integra el tráfico con las funciones WireGuard/IPsec del kernel; la cobertura y la gestión de claves dependen del modo

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) BPF integra el tráfico con las funciones WireGuard/IPsec del kernel; la cobertura y la gestión de claves dependen del modo**

   El encaminamiento del tráfico mediante BPF y el cifrado del kernel son responsabilidades distintas. El cifrado de nodos no habilita automáticamente mTLS entre cargas de trabajo.

   </details>

8. **¿Qué hooks puede utilizar Cilium para reemplazar kube-proxy?**
   - A) Solo hooks XDP
   - B) Solo rutas de paquetes TC
   - C) Solo probes de tracing
   - D) Hooks de socket, rutas de paquetes TC y aceleración XDP opcional

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Hooks de socket, rutas de paquetes TC y aceleración XDP opcional**

   La ruta depende del tráfico y de la configuración. La traducción de servicios puede ocurrir antes de que existan paquetes, en hooks de socket, en rutas de paquetes o mediante aceleración XDP compatible.

   </details>

9. **¿Cómo debe evaluarse la afirmación de que una configuración de Cilium es más rápida?**
   - A) Suponer que todas las consultas a mapas BPF tienen latencia garantizada
   - B) Medir la carga de trabajo registrando el protocolo, el enrutamiento, las políticas, el cifrado y la configuración del proxy
   - C) Tomar la ejecución en el kernel como prueba suficiente
   - D) Comparar solo los nombres de los productos

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Medir la carga de trabajo registrando el protocolo, el enrutamiento, las políticas, el cifrado y la configuración del proxy**

   Los componentes del kernel y del espacio de usuario tienen costes que dependen de la carga de trabajo. Los resultados sintéticos y la elección del hook no garantizan la latencia de la aplicación.

   </details>

10. **¿De dónde pueden provenir las observaciones HTTP de Hubble?**
    - A) Tráfico arbitrario descifrado automáticamente
    - B) Solo contadores de hardware de CPU
    - C) Una ruta compatible de proxy L7 combinada con información de flujos de red
    - D) Todos los paquetes, independientemente de la configuración

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: C) Una ruta compatible de proxy L7 combinada con información de flujos de red**

    La visibilidad L7 depende de la configuración del proxy, las políticas y la observabilidad. Los registros de flujos no son automáticamente spans de aplicación ni métricas de negocio arbitrarias.

    </details>

## Programación de eBPF

11. **¿Qué afirmación sobre compiladores y toolchains es correcta?**
    - A) Clang compila directamente código fuente tanto de C como de Rust
    - B) C suele usar el backend BPF de Clang; Rust tiene su propio ecosistema de herramientas
    - C) Una comprobación sintáctica de C en el host demuestra que el verificador del kernel aceptará el programa
    - D) BTF proporciona las funciones del kernel que faltan

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: B) C suele usar el backend BPF de Clang; Rust tiene su propio ecosistema de herramientas**

    La sintaxis del host, la compilación para el destino BPF, la verificación del kernel y el comportamiento en ejecución son comprobaciones distintas. CO-RE no crea helpers ni configuración que falten.

    </details>

12. **¿Cuál NO es un framework para desarrollar programas eBPF?**
    - A) BCC (BPF Compiler Collection)
    - B) libbpf
    - C) bpftrace
    - D) libpcap

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) libpcap</p>
    <p><strong>Explicación</strong>: libpcap es una biblioteca de captura de paquetes, no un framework para desarrollar programas eBPF. BCC, libbpf y bpftrace sí son frameworks para ese desarrollo.</p>
    </details>

13. **¿Cuál NO es un tipo de mapa eBPF?**
    - A) Hash Map
    - B) Array Map
    - C) LRU Map
    - D) Graph Map

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: D) Graph Map</p>
    <p><strong>Explicación</strong>: eBPF admite varios tipos de mapas, incluidos hash maps, array maps y LRU maps, pero no admite graph maps.</p>
    </details>

14. **¿Qué afirmación coincide con los límites de Linux 6.12 que se explican en esta guía?**
    - A) Todos los programas tienen un límite de 4.096 instrucciones
    - B) Se acepta cualquier programa de menos de un millón de instrucciones
    - C) No existen límites de programa ni de análisis
    - D) La ruta de carga con capacidad BPF admite hasta un millón de instrucciones; la ruta sin privilegios, 4.096; y la complejidad del verificador tiene un límite independiente

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: D) La ruta de carga con capacidad BPF admite hasta un millón de instrucciones; la ruta sin privilegios, 4.096; y la complejidad del verificador tiene un límite independiente**

    La longitud del programa y la exploración del verificador son límites distintos. La capacidad o el token, el tipo de programa y otras comprobaciones pueden impedir la carga; a menudo, BPF sin privilegios está deshabilitado.

    </details>

15. **¿Qué llamada de sistema se usa para cargar programas eBPF en el kernel?**
    - A) bpf()
    - B) ebpf()
    - C) sysfs()
    - D) ioctl()

    <details>
    <summary>Mostrar respuesta</summary>
    <p><strong>Respuesta</strong>: A) bpf()</p>
    <p><strong>Explicación</strong>: La llamada de sistema bpf() carga programas eBPF en el kernel y también permite crear y acceder a mapas eBPF.</p>
    </details>

## Rendimiento y observabilidad de eBPF

16. **¿Qué diferencia a XDP nativo del controlador del procesamiento posterior basado en skb?**
    - A) Siempre omite todos los subsistemas del kernel
    - B) Garantiza una tasa fija de paquetes
    - C) Puede procesar un paquete antes de asignar un skb
    - D) Funciona igual en todas las NIC y en modo genérico

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: C) Puede procesar un paquete antes de asignar un skb**

    XDP nativo se ejecuta al principio del procesamiento de recepción. El modo genérico, la descarga a hardware y la compatibilidad del controlador varían; el rendimiento real debe medirse.

    </details>

17. **¿Qué significado tiene el siguiente comando de bpftool?**
    - A) bpftool -p map dump mide la latencia de consultas
    - B) bpftool prog profile id ID duration 10 cycles instructions requests profiling metrics
    - C) bpftool prog load siempre conecta tracepoints
    - D) bpftool prog show habilita las funciones del kernel que faltan

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: B) bpftool prog profile id ID duration 10 cycles instructions requests profiling metrics**

    El perfilado requiere nombres de métricas, permisos y compatibilidad del kernel y la PMU. La impresión con formato, la carga y la conexión a eventos son operaciones distintas.

    </details>

18. **¿Qué es Hubble en este contexto?**
    - A) Un compilador del kernel
    - B) Un reemplazo de todos los SDK de tracing de aplicaciones
    - C) Observabilidad de red de Cilium mediante el datapath y los eventos de proxy disponibles
    - D) Un sincronizador automático de políticas

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: C) Observabilidad de red de Cilium mediante el datapath y los eventos de proxy disponibles**

    Hubble observa flujos y eventos L7 compatibles. Los límites y filtros de recopilación afectan los resultados; obtener JSON no equivale por sí solo a visualizar un mapa de servicios.

    </details>

19. **¿Qué cuenta el laboratorio basado en mapas?**
    - A) Todos los intentos de execve por ruta única del ejecutable, sin pérdidas
    - B) Eventos de ejecución correctos, agrupados por el nombre corto del proceso (campo comm), sujetos a límites de capacidad y medición
    - C) Solo los Pods del namespace default
    - D) Todos los procesos desde cualquier reinicio anterior

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: B) Eventos de ejecución correctos, agrupados por el nombre corto del proceso (campo comm), sujetos a límites de capacidad y medición**

    sched_process_exec observa transiciones de ejecución correctas. Los nombres pueden colisionar; este ejemplo de todo el host usa estado en memoria acotado y algunos contadores de pérdida.

    </details>

20. **¿Qué comando, ejecutado en el agente, inspecciona las entradas del mapa de backends de servicios?**
    - A) cilium-dbg bpf lb list --backends
    - B) cilium debug --all-kernels
    - C) cilium policy trace --enable
    - D) hubble compile bpf

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: A) cilium-dbg bpf lb list --backends**

    Usa cilium-dbg en el agente del nodo correcto. cilium-dbg map get muestra contenido almacenado en caché en espacio de usuario; usa el decodificador adecuado sin modificar los mapas sin procesar.

    </details>

[Consulta la guía](../../../networking/cilium/02-ebpf.md).
