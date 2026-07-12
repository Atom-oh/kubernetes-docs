# Cuestionario de fundamentos de eBPF

> **Versiones compatibles**: Linux Kernel 4.18+, Kubernetes 1.25+
> **Última actualización**: February 23, 2026

Este cuestionario evalúa tu comprensión general de eBPF (extended Berkeley Packet Filter), desde los conceptos básicos hasta sus aplicaciones en entornos de Kubernetes.

## Preguntas de opción múltiple

1. ¿Qué NO verifica el verificador de eBPF?
   - A) Que no haya bucles infinitos
   - B) Que no haya acceso a memoria fuera de los límites
   - C) La velocidad de ejecución del programa
   - D) Que no se usen variables no inicializadas

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) La velocidad de ejecución del programa**

**Explicación:**
El verificador de eBPF comprueba que no haya bucles infinitos (verificación de estructura DAG), que no haya acceso a memoria fuera de los límites, que no se usen variables no inicializadas, que las llamadas a funciones auxiliares sean correctas y que la terminación del programa esté garantizada para asegurar la seguridad del programa. La velocidad de ejecución del programa no es un elemento de verificación para el verificador.

</details>

2. ¿Qué valor de retorno de un programa XDP (eXpress Data Path) envía el paquete de vuelta a la misma NIC?
   - A) XDP_DROP
   - B) XDP_PASS
   - C) XDP_TX
   - D) XDP_REDIRECT

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) XDP_TX**

**Explicación:**
Los valores de retorno de los programas XDP tienen los siguientes significados:
- `XDP_DROP`: Descarta el paquete
- `XDP_PASS`: Lo pasa a la pila del kernel
- `XDP_TX`: Devuelve el paquete a la misma NIC
- `XDP_REDIRECT`: Lo reenvía a otra interfaz
- `XDP_ABORTED`: Manejo de errores

XDP_TX se usa cuando quieres enviar el paquete de vuelta a la interfaz de red que lo recibió.

</details>

3. ¿Cuál NO es un rol principal de eBPF Maps?
   - A) Compartir datos entre el kernel y el espacio de usuario
   - B) Almacenar estado
   - C) Compilar programas eBPF
   - D) Transmitir datos de eventos

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) Compilar programas eBPF**

**Explicación:**
eBPF maps son estructuras de datos usadas para compartir datos entre el kernel y el espacio de usuario, y para almacenar estado. Los maps se usan para transmitir datos de eventos (PERF_EVENT_ARRAY, RINGBUF), almacenamiento clave-valor (HASH), recopilación de estadísticas (PERCPU_ARRAY) y más. La compilación de programas eBPF la realizan Clang/LLVM y no es un rol de los maps.

</details>

4. ¿Cuál es la principal ventaja que proporciona eBPF cuando Cilium reemplaza a kube-proxy?
   - A) Rendimiento O(n) proporcional al número de servicios
   - B) Requiere evaluación de reglas iptables
   - C) Rendimiento O(1) mediante búsqueda en map
   - D) Usa Netfilter

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) Rendimiento O(1) mediante búsqueda en map**

**Explicación:**
El kube-proxy tradicional (modo iptables) tiene una degradación de rendimiento O(n) a medida que aumenta el número de servicios. Cilium usa eBPF maps para proporcionar rendimiento de búsqueda constante O(1). Esto ofrece una mejora significativa de rendimiento en todos los aspectos, incluidos el tiempo de establecimiento de conexiones, el uso de CPU y las conexiones por segundo.

</details>

5. ¿Cuál es el propósito principal de bpftrace?
   - A) Compilar programas eBPF a C
   - B) Cargar módulos del kernel
   - C) Trazado de alto nivel al estilo DTrace
   - D) Construir imágenes de contenedor

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) Trazado de alto nivel al estilo DTrace**

**Explicación:**
bpftrace es un lenguaje de trazado de alto nivel al estilo DTrace que te permite trazar el sistema con comandos simples de una sola línea. Por ejemplo, puedes realizar fácilmente tareas como contar llamadas al sistema, rastrear bytes leídos por proceso, trazar aperturas de archivos y rastrear conexiones TCP.

</details>

6. En TracingPolicy de Tetragon, ¿qué acción termina inmediatamente un proceso cuando se detecta acceso malicioso a archivos?
   - A) action: Block
   - B) action: Sigkill
   - C) action: Deny
   - D) action: Terminate

<details>
<summary>Ver respuesta</summary>

**Respuesta: B) action: Sigkill**

**Explicación:**
En TracingPolicy de Tetragon, `action: Sigkill` en `matchActions` termina inmediatamente el proceso con una señal SIGKILL cuando ocurre un evento que coincide con la política. Esto se usa para bloquear el acceso a archivos sensibles o conexiones de red maliciosas en tiempo real.

</details>

7. ¿Cuál NO es una característica principal de Hubble?
   - A) Observación de flujos de red
   - B) Seguimiento de consultas DNS
   - C) Compilar programas eBPF
   - D) Monitoreo de decisiones de política

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) Compilar programas eBPF**

**Explicación:**
Hubble es una plataforma de observabilidad de red integrada en Cilium que recopila y monitorea flujos de red, consultas DNS, solicitudes HTTP, decisiones de política y más. Hubble es una herramienta de observabilidad y no proporciona funcionalidad de compilación de programas eBPF.

</details>

8. ¿Qué problema resuelve CO-RE (Compile Once, Run Everywhere)?
   - A) Mejorar la velocidad de ejecución de los programas eBPF
   - B) Portabilidad entre distintas versiones del kernel
   - C) Reducir el uso de memoria
   - D) Reducir la latencia de red

<details>
<summary>Ver respuesta</summary>

**Respuesta: B) Portabilidad entre distintas versiones del kernel**

**Explicación:**
CO-RE usa libbpf y BTF (BPF Type Format) para permitir que los programas eBPF compilados una sola vez se ejecuten en varias versiones del kernel. Esto reduce las dependencias de headers del kernel y maneja automáticamente la reubicación de structs, eliminando la necesidad de recompilar para cada versión del kernel.

</details>

9. ¿Qué detecta Falco usando eBPF?
   - A) Uso de ancho de banda de red
   - B) Comportamiento anómalo en tiempo de ejecución
   - C) Capacidad del disco
   - D) Temperatura de la CPU

<details>
<summary>Ver respuesta</summary>

**Respuesta: B) Comportamiento anómalo en tiempo de ejecución**

**Explicación:**
Falco es un proyecto de CNCF que usa eBPF para detectar comportamiento anómalo en tiempo de ejecución. Detecta y alerta sobre amenazas de seguridad, como lectura de archivos sensibles, ejecución de shells en contenedores e intentos de escalada de privilegios, basándose en reglas.

</details>

10. ¿Cuál es el límite de tamaño de la pila para programas eBPF?
    - A) 128 bytes
    - B) 256 bytes
    - C) 512 bytes
    - D) 1024 bytes

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) 512 bytes**

**Explicación:**
Los programas eBPF tienen un límite de tamaño de pila de 512 bytes. Para sortear este límite, necesitas usar maps como PERCPU_ARRAY para asignar búferes más grandes. Este límite existe para garantizar la seguridad del kernel.

</details>

## Preguntas de respuesta corta

11. ¿Cómo se llama el compilador que convierte bytecode eBPF en código de máquina nativo?

<details>
<summary>Ver respuesta</summary>

**Respuesta: Compilador JIT (compilador Just-In-Time)**

**Explicación:**
El compilador JIT convierte bytecode eBPF en código de máquina nativo. Esto proporciona una mejora de rendimiento de 4 a 5 veces en comparación con el intérprete, y se aplican optimizaciones específicas de la arquitectura. Se puede habilitar estableciendo `/proc/sys/net/core/bpf_jit_enable` en 1.

</details>

12. ¿Cómo se llama el tipo de programa eBPF que traza dinámicamente llamadas a funciones del kernel?

<details>
<summary>Ver respuesta</summary>

**Respuesta: Kprobes (o Kprobe)**

**Explicación:**
Kprobes es un tipo de programa eBPF que traza dinámicamente llamadas a funciones del kernel. A diferencia de Uprobes, que traza funciones de espacio de usuario, Kprobes traza funciones dentro del kernel. Por ejemplo, puedes trazar la función `tcp_connect` para recopilar información de conexiones TCP.

</details>

13. ¿Cómo se llama la plataforma de observabilidad de red integrada en Cilium?

<details>
<summary>Ver respuesta</summary>

**Respuesta: Hubble**

**Explicación:**
Hubble es una plataforma de observabilidad de red integrada en Cilium que recopila datos del dataplane de eBPF, incluidos flujos de red, consultas DNS, solicitudes HTTP y decisiones de política. Puedes observar el tráfico de red del cluster en tiempo real mediante Hubble CLI, Hubble UI y Hubble Relay.

</details>

14. ¿Qué capability de Linux se requiere para cargar programas eBPF? (kernel 5.8 y superior)

<details>
<summary>Ver respuesta</summary>

**Respuesta: CAP_BPF**

**Explicación:**
En kernel 5.8 y superior, se requiere la capability `CAP_BPF` para cargar programas eBPF. En versiones anteriores, se requería `CAP_SYS_ADMIN`. Además, `CAP_PERFMON` se necesita para adjuntarse a eventos de monitoreo de rendimiento, y `CAP_NET_ADMIN` se necesita para adjuntar programas XDP/TC.

</details>

15. ¿Cómo se llama el proyecto de CNCF que monitorea el consumo de energía de contenedores usando eBPF?

<details>
<summary>Ver respuesta</summary>

**Respuesta: Kepler (Kubernetes-based Efficient Power Level Exporter)**

**Explicación:**
Kepler es un proyecto que usa eBPF para monitorear el consumo de energía de contenedores. Proporciona métricas en formato Prometheus, como `kepler_container_joules_total` (consumo de energía por contenedor) y `kepler_container_gpu_joules_total` (consumo de energía de GPU).

</details>

## Preguntas prácticas

16. Escribe los comandos para usar bpftool a fin de listar los programas eBPF cargados actualmente en el sistema y consultar información detallada sobre un programa específico.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**
```bash
# List loaded eBPF programs
sudo bpftool prog list

# Query detailed information for a specific program (ID: 123)
sudo bpftool prog show id 123

# Dump program bytecode
sudo bpftool prog dump xlated id 123

# Dump JIT compiled code
sudo bpftool prog dump jited id 123
```

**Explicación:**
`bpftool prog list` muestra una lista de todos los programas eBPF cargados actualmente. Puedes comprobar el ID, tipo, nombre, ubicación de adjunción, etc. de cada programa. Usa `bpftool prog show id <ID>` para consultar información detallada sobre un programa específico, y `dump xlated` y `dump jited` para ver el bytecode y el código nativo compilado por JIT.

</details>

17. Escribe un comando de una sola línea de bpftrace para trazar en tiempo real las conexiones TCP que ocurren desde todos los procesos del sistema.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**
```bash
# TCP connection tracing (Method 1: using kprobe)
sudo bpftrace -e 'kprobe:tcp_connect { printf("%s (PID: %d) connecting...\n", comm, pid); }'

# TCP connection tracing (Method 2: using tracepoint, more detailed info)
sudo bpftrace -e 'tracepoint:tcp:tcp_connect { printf("%s -> %s:%d\n", ntop(args->saddr), ntop(args->daddr), args->dport); }'

# Count TCP connections by process
sudo bpftrace -e 'kprobe:tcp_connect { @[comm] = count(); }'
```

**Explicación:**
bpftrace es un lenguaje de trazado de alto nivel al estilo DTrace que te permite trazar el sistema con comandos simples de una sola línea. `kprobe:tcp_connect` se activa cuando se llama a la función `tcp_connect` del kernel. `comm` representa el nombre del proceso y `pid` representa el ID del proceso. Usar tracepoints te permite obtener también direcciones IP de origen/destino e información de puertos.

</details>

18. Escribe el comando para usar Hubble CLI a fin de observar solo paquetes descartados de un namespace específico.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**
```bash
# Observe dropped packets in a specific namespace
hubble observe --namespace production --verdict DROPPED

# Observe dropped packets with real-time streaming
hubble observe --namespace production --verdict DROPPED -f

# Output detailed information of dropped packets in JSON format
hubble observe --namespace production --verdict DROPPED -o json

# Observe dropped packets from a specific Pod
hubble observe --from-pod production/frontend --verdict DROPPED
```

**Explicación:**
Hubble es una herramienta de observabilidad de red integrada en Cilium. La opción `--namespace` filtra por un namespace específico, y `--verdict DROPPED` filtra solo los paquetes descartados. La opción `-f` proporciona streaming en tiempo real, y `-o json` proporciona salida en formato JSON. Analizar paquetes descartados ayuda a diagnosticar problemas de NetworkPolicy o errores de configuración.

</details>

## Preguntas avanzadas

19. Explica las tres ventajas principales que tiene eBPF frente a los módulos del kernel y describe específicamente qué beneficios aporta cada una en entornos de Kubernetes.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**

Ventajas principales de eBPF frente a los módulos del kernel y sus beneficios en entornos de Kubernetes:

**1. Seguridad (seguridad garantizada mediante el verificador)**
- **Ventaja**: El verificador de eBPF comprueba bucles infinitos, infracciones de acceso a memoria, variables no inicializadas, etc. antes de cargar el programa para evitar caídas del kernel.
- **Beneficio para Kubernetes**: Los plugins CNI (Cilium) y las herramientas de seguridad (Tetragon, Falco) pueden ejecutarse de forma segura en clusters de producción. A diferencia de los módulos del kernel, incluso si hay errores, todo el sistema no se bloqueará, manteniendo alta disponibilidad.

**2. Portabilidad (independencia de la versión del kernel mediante CO-RE)**
- **Ventaja**: Usando CO-RE (Compile Once, Run Everywhere) y BTF, los programas eBPF compilados una sola vez pueden ejecutarse en diversas versiones del kernel. No se necesita recompilación para cada versión del kernel.
- **Beneficio para Kubernetes**: Las mismas soluciones de networking y seguridad pueden desplegarse en entornos heterogéneos de nodos (nodos con distintas versiones del kernel). Los problemas de compatibilidad se reducen considerablemente durante las actualizaciones del cluster o la adición de nodos.

**3. Carga dinámica (carga/descarga de programas sin reinicio)**
- **Ventaja**: Los programas eBPF se pueden cargar y descargar dinámicamente sin reiniciar el sistema. La funcionalidad se puede añadir o cambiar en tiempo de ejecución.
- **Beneficio para Kubernetes**: Las políticas de red, las reglas de seguridad y la configuración de observabilidad se pueden aplicar inmediatamente sin reiniciar nodos. Los cambios en Cilium NetworkPolicy o Tetragon TracingPolicy se reflejan en tiempo real, lo que permite mejoras de seguridad sin interrupción operativa.

**Ventajas adicionales:**
- **Rendimiento**: La compilación JIT proporciona rendimiento a nivel de código nativo, habilitando búsquedas de servicios O(1) al reemplazar kube-proxy.
- **Dificultad de desarrollo**: Es relativamente más fácil que el desarrollo de módulos del kernel, lo que permite un desarrollo y despliegue rápidos de funcionalidades.

</details>

20. Diseña un enfoque para detectar y bloquear el acceso a archivos sensibles dentro de contenedores usando una solución de seguridad basada en eBPF (Tetragon o Falco) en un cluster de Kubernetes. Incluye ejemplos de TracingPolicy o reglas de Falco en tu explicación.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**

**Diseño de seguridad para acceso a archivos sensibles basado en eBPF**

**1. Definición de requisitos de seguridad**
- Objetivos de detección: `/etc/shadow`, `/etc/passwd`, `/etc/sudoers`, `/var/run/secrets/` (Kubernetes secrets)
- Enfoque de respuesta: Alerta al detectar, terminación de proceso para casos graves

**2. Implementación de Tetragon TracingPolicy**

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: sensitive-file-protection
spec:
  kprobes:
    # Monitor sensitive file opens
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        # Detect and log Kubernetes secret access
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /var/run/secrets/kubernetes.io/
          matchActions:
            - action: Post  # Event logging

        # Block system authentication file access
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /etc/shadow
                - /etc/sudoers
          matchNamespaces:
            - namespace: default
              operator: In
          matchActions:
            - action: Sigkill  # Immediately terminate process
```

**3. Implementación de reglas de Falco**

```yaml
# /etc/falco/rules.d/sensitive-files.yaml
- rule: Read Kubernetes Secrets
  desc: Detect reading of Kubernetes secret files in containers
  condition: >
    open_read and
    container and
    (fd.name startswith /var/run/secrets/kubernetes.io/ or
     fd.name startswith /etc/shadow or
     fd.name startswith /etc/sudoers) and
    not proc.name in (kubelet, containerd)
  output: >
    Sensitive file access detected
    (file=%fd.name user=%user.name process=%proc.name
     container=%container.name namespace=%k8s.ns.name
     pod=%k8s.pod.name)
  priority: WARNING
  tags: [security, filesystem]

- rule: Write to Sensitive System Files
  desc: Detect writing to sensitive system files
  condition: >
    open_write and
    container and
    fd.name in (/etc/passwd, /etc/shadow, /etc/sudoers)
  output: >
    Attempt to modify sensitive file
    (file=%fd.name user=%user.name process=%proc.name
     container=%container.name)
  priority: CRITICAL
  tags: [security, filesystem]
```

**4. Despliegue y monitoreo**

```bash
# Install Tetragon and apply policy
helm install tetragon cilium/tetragon -n kube-system
kubectl apply -f sensitive-file-protection.yaml

# Monitor events
kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon \
  -c export-stdout -f | tetra getevents -o compact

# Install Falco (eBPF driver)
helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf

# Check Falco alerts
kubectl logs -n falco -l app.kubernetes.io/name=falco -f
```

**5. Explicación de la arquitectura**

```
┌─────────────────────────────────────────────────┐
│              Kubernetes Cluster                 │
│  ┌─────────────────┐    ┌─────────────────┐    │
│  │   Application   │    │   Application   │    │
│  │      Pod        │    │      Pod        │    │
│  └────────┬────────┘    └────────┬────────┘    │
│           │                      │             │
│  ┌────────▼──────────────────────▼────────┐   │
│  │              eBPF Layer                 │   │
│  │  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ Tetragon    │  │  Falco      │     │   │
│  │  │ TracingPol. │  │  Rules      │     │   │
│  │  └──────┬──────┘  └──────┬──────┘     │   │
│  │         │                 │            │   │
│  │         ▼                 ▼            │   │
│  │   [File Access Event Capture]          │   │
│  └────────────────────────────────────────┘   │
│                      │                         │
│  ┌───────────────────▼───────────────────┐   │
│  │           Security Response            │   │
│  │  • Event logging (Post)               │   │
│  │  • Process termination (Sigkill)      │   │
│  │  • SIEM alert forwarding              │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

Este diseño aprovecha la visibilidad a nivel de kernel de eBPF para detectar y responder al acceso a archivos sensibles en tiempo real sin modificar las aplicaciones.

</details>

---

[Volver a materiales de aprendizaje](../../basics/05-ebpf-fundamentals.md) | [Siguiente cuestionario: Tecnología de contenedores](./03-container-technology-quiz.md)
