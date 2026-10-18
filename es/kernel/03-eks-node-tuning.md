# Ajuste del kernel de nodos de EKS

> **Versiones compatibles**: Amazon Linux 2023 (kernel 6.1 / 6.12 / 6.18), Kubernetes 1.33+ (Amazon EKS)
> **Última actualización**: 13 de septiembre de 2026

## Qué cubre este documento

- Qué cambiar y qué dejar con los valores predeterminados en los nodos de EKS, y cómo decidirlo
- Las rutas reales para aplicar parámetros del kernel en EKS y las dificultades de cada una
- Qué implica en la operación la transición del kernel de AL2023 (6.1 → 6.18)

## Primero: no cambies casi nada

Este es el consejo más importante de este documento.

Los valores predeterminados del kernel se eligen para **comportarse razonablemente con una amplia variedad de cargas de trabajo**, y el kernel ajusta muchos de ellos de forma automática bajo carga (por ejemplo, el ajuste automático de los búferes TCP). Ajustarlos sin evidencia tiene tres costos.

| Problema | Ejemplo |
|---|---|
| **Configuración imposible de reproducir** | Los valores varían de un nodo a otro, así que no se pueden reproducir los incidentes |
| **Fallos al actualizar el kernel** | Un parámetro válido en 6.1 cambia de nombre, de ubicación o desaparece en 6.18 |
| **Interferencia con el ajuste automático** | Definir explícitamente SO_RCVBUF/SO_SNDBUF por socket deshabilita el dimensionamiento automático de ese socket; los límites de sysctl son un control diferente |

**Para ajustar un parámetro, primero hay que medir.** Sigue este orden:

1. Identifica el síntoma (¿latencia, descartes o rendimiento?)
2. **Primero revisa los contadores de descartes**: `insert_failed` en `conntrack -S`, `dropped` en `tc -s qdisc` y descartes de la NIC en `ethtool -S`
3. Cambia solo los parámetros del punto donde aumenta ese contador
4. Mide antes y después en condiciones idénticas
5. Registra el cambio y su justificación como código (consulta las rutas de aplicación más abajo)

Para conocer el método de medición, consulta los fixtures del [benchmark de red de Pods](../networking/06-pod-network-benchmark.md).

## Rutas de aplicación: cómo cambiar los parámetros del kernel en EKS

Hay varias maneras y **cada una tiene un alcance y una dificultad distintos**. En la práctica, es importante entender bien estas diferencias.

| Ruta | Alcance | Persistencia | Notas |
|---|---|---|---|
| **Arranque del nodo** (User Data / `nodeadm`) | Todo el nodo | Se vuelve a aplicar al reemplazar el nodo | AL2023 usa la configuración de `nodeadm`. Es la opción más estándar |
| **Configuración de Bottlerocket** (`settings.kernel.sysctl`) | Todo el nodo | Se administra como configuración del nodo | Bottlerocket es inmutable; esta es la única ruta |
| **`securityContext.sysctls` del Pod** | **Solo el espacio de nombres de red del Pod** | Especificación del Pod | **Solo sysctls con espacio de nombres propio.** Muchos valores `net.*` cumplen este requisito |
| **DaemonSet de inicialización con privilegios** | Todo el nodo | Se vuelve a aplicar al reiniciar el Pod | De uso común, pero requiere privilegios (un punto que revisar en seguridad) |
| **ConfigMap `kube-proxy-config`** | Valores relacionados con conntrack | Lo administra kube-proxy | **En EKS, tiene prioridad sobre los argumentos CLI** |
| **`EC2NodeClass` de Karpenter** | Grupo de nodos | Al aprovisionar el nodo | Administra User Data de forma declarativa |

### Dos puntos que suelen pasarse por alto

**Primero, la diferencia entre sysctls con y sin espacio de nombres propio.** Muchos valores `net.*` se pueden establecer por espacio de nombres de red, de modo que `securityContext.sysctls` del Pod puede cambiarlos. En cambio, `vm.*`, `fs.*` y **algunos valores como `net.netfilter.nf_conntrack_max` son globales para el nodo** y no se pueden cambiar desde la especificación del Pod.

Además, kubelet rechaza de forma predeterminada los sysctls «inseguros». Si necesitas uno, permítelo explícitamente con `--allowed-unsafe-sysctls`, que es una configuración del nodo.

**Segundo, kube-proxy sobrescribe conntrack.** Ya se mencionó en [Funciones del kernel de los contenedores](./01-container-primitives.md), pero es el problema más habitual en la práctica, así que conviene repetirlo: EKS incluye de forma predeterminada un ConfigMap `kube-proxy-config` y **este tiene prioridad sobre los argumentos de la línea de comandos**. kube-proxy puede revertir un aumento de sysctl aplicado durante el arranque.

::: warning Requiere verificación
En Bottlerocket, aumentar el límite de conntrack mediante `settings.kernel.sysctl` no surte efecto ([bottlerocket-os/bottlerocket#4221](https://github.com/bottlerocket-os/bottlerocket/issues/4221), incidencia registrada en septiembre de 2024). La causa es que **el archivo de configuración de kube-proxy (`/var/lib/kube-proxy-config/config`) tiene prioridad sobre los argumentos de la línea de comandos**.

Si usas un archivo de configuración de kube-proxy y quieres delegar intencionadamente la administración del límite al sysctl del nodo, cambia los campos **`conntrack.maxPerCore`/`conntrack.min`**. Establecer ambos en 0 no justifica depender de argumentos CLI que `--config` ignora. Antes del despliegue, confirma la conciliación del complemento administrado y el margen de memoria.

**No se pudo confirmar si esto se corrigió en una versión específica de Bottlerocket.** Sea cual sea la ruta que uses, después de aplicarla verifica el valor real en el nodo.

```bash
# Check the actually applied values on the node
cat /proc/sys/net/netfilter/nf_conntrack_max
cat /proc/sys/net/netfilter/nf_conntrack_count
conntrack -S | head
```
:::

## Versión del kernel: transición de AL2023 de 6.1 a 6.18

Este es el cambio que conviene conocer ahora.

| Fecha | Cambio |
|---|---|
| Marzo de 2023 | AL2023 se publicó con kernel **6.1** |
| Abril de 2025 | Se añadió compatibilidad con kernel **6.12** |
| **17 de agosto de 2026** | **El kernel predeterminado de las AMI `al2023-ami-kernel-default` cambió de 6.1 a 6.18** |

**De aquí se desprenden dos consecuencias.**

Cambió la familia de AMI con el kernel predeterminado, pero al reemplazar un nodo se usa la AMI seleccionada por la plantilla de lanzamiento o la política de aprovisionamiento. Un ID de AMI fijado no cambia el kernel solo porque se inicie un nodo nuevo. Una consulta actualizada de la AMI más reciente o predeterminada sí puede seleccionar un kernel nuevo; las AMI optimizadas para EKS tienen su propio proceso de selección de versiones.

Si necesitas fijar un kernel, elige explícitamente **AMI específicas de versión** (`al2023-ami-kernel-6.1-*`, etc.).

**Qué comprobar cuando cambia el kernel:**

| Elemento | Motivo |
|---|---|
| Existencia y ubicación de los parámetros | Entre versiones, pueden cambiar de nombre o pasar de sysctl a debugfs |
| Componentes que dependen de módulos del kernel | Programas eBPF, funciones específicas de CNI, controladores de GPU y módulos personalizados |
| Comportamiento del planificador | EEVDF desde 6.6 (más adelante); podría notarse en cargas sensibles a la latencia |
| Regresiones de rendimiento | Vuelve a medir los benchmarks con cada versión del kernel |

**Recomendación**: trata una transición del kernel **con la misma importancia que una actualización de versión de Kubernetes**. Valídala en staging con el mismo kernel, vuelve a medir la referencia de rendimiento y luego pásala a producción.

## CPU: planificador y throttling

### EEVDF: qué cambió en 6.6

En Linux 6.6, **EEVDF** (Earliest Eligible Virtual Deadline First) sustituyó la lógica de selección de tareas de CFS.

Conviene entender con precisión **qué cambió y qué no**.

| Cambió | No cambió |
|---|---|
| **Cómo se elige la siguiente tarea** (según plazos virtuales) | Mecanismo de vruntime y cálculo del peso |
| Decisión de apropiación de una tarea que se despertó: **comparación de plazos** en vez de una heurística (`sched_wakeup_granularity_ns`) | Planificación por grupos (cgroup cpu.weight) y balanceo de carga |

Por eso, es correcto entenderlo como **una evolución que reemplazó la lógica de selección, no como una sustitución completa de CFS**. El cambio está dentro de `fair_sched_class`.

En la práctica, **pueden cambiar las características de latencia de activación en cargas sensibles a la latencia**. Por lo general, para mejor; sin embargo, si el percentil p99 se desplaza al pasar del kernel 6.1 a 6.18, esta es una posible causa.

### Dónde están realmente los parámetros

Confirmado en el código fuente del kernel (`kernel/sched/debug.c`):

| Elemento | Estado |
|---|---|
| `sched_latency_ns` | **Eliminado**: no quedan referencias en `kernel/sched/fair.c` |
| `sched_wakeup_granularity_ns` | **Eliminado** (igual que el anterior) |
| **`/sys/kernel/debug/sched/base_slice_ns`** | **Equivalente actual.** La variable interna es `sysctl_sched_base_slice`, expuesta en debugfs como `base_slice_ns` |

Así que los parámetros de latencia y de heurística de apropiación de la era CFS desaparecieron y se consolidaron en **un solo segmento de tiempo base (`base_slice_ns`)**. Ten en cuenta que el nombre no lleva el prefijo `sched_`; la ruta es `/sys/kernel/debug/sched/base_slice_ns`.

Por separado, EEVDF permite que una tarea **solicite su propio segmento de tiempo** mediante la llamada al sistema `sched_setattr()`. Para aplicaciones sensibles a la latencia, esa ruta es más adecuada que tocar un parámetro global.

**Los parámetros del planificador siguen sin ser un objetivo de ajuste recomendado.** debugfs es una interfaz de depuración del kernel y puede no estar montada en producción; en la mayoría de los casos, es mejor ajustar el número de subprocesos de la aplicación o los límites de cgroup.
### Límites de CPU: cuándo el throttling es el problema real

Como se explicó en [Funciones del kernel de los contenedores](./01-container-primitives.md), un límite de CPU restringe la capacidad de procesamiento y, por eso, genera latencia incluso con un uso bajo.

**Diagnóstico:**

```bash
# cgroup v2: from the container's cgroup path
cat cpu.stat
# nr_periods, nr_throttled, throttled_usec
```

Si `nr_throttled / nr_periods` representa una fracción considerable, el límite es la causa.

**Orden de prioridad de las respuestas** (consulta [Optimización de recursos](../ops/10-resource-optimization.md) para ver el diseño):

1. **Ajusta la cantidad de CPU que percibe la aplicación al límite.** Esta es la causa principal que se pasa por alto con más frecuencia: si el runtime dentro del contenedor ve todos los núcleos del nodo y crea esa cantidad de subprocesos, agota la cuota al instante. Ajusta JVM `-XX:ActiveProcessorCount`, Go `GOMAXPROCS`, Node.js `UV_THREADPOOL_SIZE`, etc., para que coincidan con el límite
2. **Aumenta el límite**, a costa de la estabilidad del nodo
3. **Si la aplicación es extremadamente sensible a la latencia, considera eliminar el límite**, pero gestiona el riesgo de interferencia entre cargas de trabajo con requests y separación de nodos
4. Comprueba el tiempo real de espera con PSI `cpu.pressure`

La **política estática de CPU Manager** (núcleos dedicados) es un mecanismo distinto y válido para cargas de trabajo sensibles a la latencia. Reduce el uso del nodo, así que hay que justificarla.

## Memoria: OOM y presión

### Qué ajustar y qué dejar como está

| Parámetro | Recomendación |
|---|---|
| `vm.swappiness` | Tradicionalmente, Kubernetes presupone que el intercambio (swap) está desactivado. La compatibilidad con swap ha madurado, pero **confirma el estado de compatibilidad antes de habilitarlo en EKS** |
| `vm.overcommit_memory` | **Conserva el valor predeterminado.** Cambiarlo dificulta prever los modos de fallo de asignación de memoria de los contenedores |
| `vm.min_free_kbytes` | Margen para recuperar memoria. Un valor demasiado bajo puede provocar OOM ante asignaciones repentinas. **Considéralo solo en nodos con mucha memoria y ráfagas intensas** |
| `vm.max_map_count` | **Un ajuste realmente necesario para Elasticsearch/OpenSearch** y software similar; el valor predeterminado es bajo y alcanza el límite de mmap |
| `kernel.pid_max` | Cuando se agotan los PID en nodos de alta densidad |

`vm.max_map_count` es un caso real que aparece con frecuencia: el software de la familia OpenSearch asigna muchos archivos a memoria (mmap) y no puede iniciarse con el valor predeterminado. Es un buen ejemplo de «ajuste justificado»: el síntoma es claro, el parámetro es la causa directa y el proveedor documenta un valor recomendado.

### Reservas de kubelet: antes que los parámetros del kernel

Para la estabilidad del nodo, las **reservas de recursos de kubelet** tienen más impacto que ajustar el kernel.

| Configuración | Propósito |
|---|---|
| `--system-reserved` | Se reserva para el sistema operativo y los daemons del sistema |
| `--kube-reserved` | Se reserva para kubelet y el runtime de contenedores |
| `--eviction-hard` | Desaloja Pods al alcanzarse este umbral |

Si la reserva es insuficiente, los Pods consumen toda la memoria del nodo y **se produce un OOM en el kernel o incluso en kubelet**. El nodo pasa a `NotReady` y afecta a todos sus Pods, un resultado mucho peor que el OOM de un Pod individual.

**El desalojo es mejor que el OOM.** Kubernetes mueve un Pod de forma controlada cuando lo desaloja; el OOM killer del kernel termina un proceso abruptamente. El objetivo es configurar `--eviction-hard` para que Kubernetes intervenga antes de que se produzca un OOM en el kernel.

### Observación de presión con PSI

El PSI de cgroup v2 proporciona una señal mejor que el uso.

```bash
# Whole node
cat /proc/pressure/memory
cat /proc/pressure/cpu
cat /proc/pressure/io

# A specific cgroup
: "${KERNEL_CGROUP_PATH:?Set the inspected cgroup directory}"
cat "$KERNEL_CGROUP_PATH/memory.pressure"
```

`some avg10` es la fracción de los últimos 10 segundos durante la cual **al menos una tarea estuvo bloqueada por ese recurso**. Si este valor aumenta mientras el gráfico de uso se mantiene tranquilo, significa que se está dedicando tiempo a recuperar memoria o a esperar por contención.

## Red: ajustes justificados

### conntrack

Como ya se explicó, **es el elemento que provoca incidentes reales con más frecuencia**.

| Elemento | Contenido |
|---|---|
| Síntoma | Las conexiones nuevas se descartan silenciosamente. La aplicación solo ve tiempos de espera o rechazos |
| Evidencia que conviene correlacionar | Aumento de **`insert_failed`** en `conntrack -S`; por sí solo, no demuestra que la tabla esté agotada |
| Señales secundarias | `nf_conntrack: table full` en `dmesg`, relación entre `nf_conntrack_count` y `nf_conntrack_max` |
| Ruta para ajustar | **`conntrack.maxPerCore` / `conntrack.min` en el ConfigMap `kube-proxy-config`** (tiene prioridad en EKS) |
| Costo | Memoria del nodo por entrada. No se puede aumentar sin límite |
| Solución de fondo | Reducir la rotación de conexiones e investigar la presión sobre el plano de datos y los mapas. El DNS headless por sí solo no desactiva el seguimiento |

Conviene saber **por qué se usa `maxPerCore`**. Como se define por núcleo y no como un valor absoluto, el mismo ajuste escala proporcionalmente con el tamaño del nodo. Fijar un valor absoluto (`nf_conntrack_max`) aprovisiona de más los nodos pequeños y de menos los grandes.

También se pueden ajustar los tiempos de espera: reducir `nf_conntrack_tcp_timeout_established` (cuyo valor predeterminado es muy largo) libera entradas antes. Ten cuidado de no interrumpir conexiones legítimas de larga duración.

### Búferes de sockets y colas

| Parámetro | Cuándo ajustarlo |
|---|---|
| `net.core.somaxconn` | **Cuando se desborda la cola de aceptación.** Ajuste común en servidores que reciben ráfagas de conexiones |
| `net.ipv4.tcp_max_syn_backlog` | Ante ráfagas de SYN |
| `net.core.netdev_max_backlog` | **Cuando softirq de recepción no da abasto** |
| `net.ipv4.tcp_rmem` / `tcp_wmem` | Límites/valores predeterminados del dimensionamiento TCP; cambiarlos no desactiva por sí solo el ajuste automático. Ajústalos solo con datos medidos de BDP/memoria |
| `net.ipv4.ip_local_port_range` | **Cuando se agotan los puertos de origen.** Ocurre en la práctica en nodos con mucho tráfico de salida |
| `net.ipv4.tcp_tw_reuse` | Cuando se acumulan estados TIME_WAIT. Aplícalo entendiendo su comportamiento |

**`somaxconn` e `ip_local_port_range` son ejemplos representativos de ajustes justificados.** El primero tiene un contador que aporta evidencia (`TcpExtListenOverflows` en `nstat`); el segundo aparece directamente como fallos de conexión.

Conserva límites razonables para `tcp_rmem`/`tcp_wmem` salvo que las mediciones justifiquen cambios. La documentación de Linux indica que definir explícitamente **SO_RCVBUF/SO_SNDBUF en un socket** desactiva el ajuste automático correspondiente a ese socket; no lo confundas con establecer los valores mínimo/predeterminado/máximo de sysctl.

### qdisc

Si confirmas descartes dentro del nodo (`dropped` en `tc -s qdisc`), este es el punto que debes ajustar.

- **`fq_codel`**: mitiga bufferbloat (cuando el problema es la latencia)
- **`fq`**: controla el pacing (al usar bbr)
- Aumentar el tamaño de la cola (`txqueuelen`) reduce los descartes, pero **eleva la latencia**. Decide teniendo en cuenta esa compensación

### Distribución de interrupciones

Si `/proc/interrupts` muestra que una CPU recibe una proporción desmedida y `mpstat -P ALL` muestra que `%soft` se dispara en ella, revisa RSS/RPS/RFS. Dicho esto, **los controladores ENA actuales y los tipos de instancia usan varias colas y RSS de forma predeterminada**, así que rara vez se convierte en un problema.

### Modo de kube-proxy

No es un parámetro del kernel del nodo, pero tiene la mayor influencia en el rendimiento del plano de datos.

| Situación | Recomendación |
|---|---|
| Muchos Services, modo iptables | **Considera el modo nftables**: GA desde 1.33, búsqueda O(1) y actualizaciones incrementales. Requiere kernel 5.13 o posterior (AL2023 lo cumple) |
| **Uso del modo IPVS** | **Hace falta un plan de migración**: está obsoleto desde 1.35; upstream prevé deshabilitarlo de forma predeterminada en 1.40 y eliminarlo en 1.43. Se recomienda sustituirlo por nftables |
| Mantener el valor predeterminado | Aunque nftables sea GA, **iptables sigue siendo la opción predeterminada**; cambiarlo es una decisión explícita |

## Almacenamiento

| Parámetro | Contenido |
|---|---|
| **Planificador de E/S** | En NVMe es habitual usar `none` (o `mq-deadline`). Los planificadores complejos aportan poco en NVMe |
| `vm.dirty_ratio` / `dirty_background_ratio` | Volumen del búfer de escritura. Influye en la latencia durante ráfagas de escritura |
| **Almacenamiento efímero** | Más que los parámetros del kernel, el problema real es el **costo de copy-up de overlayfs**; mueve las rutas con muchas escrituras a volúmenes ([Funciones del kernel de los contenedores](./01-container-primitives.md)) |
| **Rendimiento de EBS** | No depende del kernel, sino del tipo de volumen y de los valores de IOPS y rendimiento ([benchmark de EBS gp2 frente a gp3](../storage/01-ebs-gp2-gp3-benchmark.md)) |

## Por tipo de carga de trabajo

Una tabla que parte de los síntomas.

| Carga de trabajo | Ajustes que suelen necesitarse | Contadores que aportan evidencia |
|---|---|---|
| **Gateways/proxies con muchas conexiones** | Límite de conntrack, `somaxconn`, `ip_local_port_range` | `insert_failed`, `TcpExtListenOverflows`, agotamiento de puertos |
| **Sensible a la latencia (trading, tiempo real)** | Revisar límites de CPU, política estática de CPU Manager, `fq_codel` | Throttling en `cpu.stat`, `cpu.pressure` |
| **Alto rendimiento (lotes, datos)** | Límites de búfer (solo a larga distancia), `netdev_max_backlog` | `dropped` de qdisc, desequilibrio de softirq |
| **Búsqueda/indexación (OpenSearch, etc.)** | **`vm.max_map_count`**, límites de descriptores de archivo | Registros de errores al iniciar |
| **Nodos de alta densidad** | `kernel.pid_max`, reservas de kubelet, umbrales de desalojo | Agotamiento de PID, nodo `NotReady` |
| **Nodos de blockchain** | Descriptores de archivo, IOPS de disco, búferes de sockets | [Operaciones de nodos de blockchain](../blockchain/02-nodes-on-eks.md) |

## Cómo administrar los cambios

A largo plazo, **la forma de administrar los ajustes** importa más que el ajuste mismo.

| Principio | Motivo |
|---|---|
| **Administrar como código** (`EC2NodeClass` de Karpenter, plantillas de lanzamiento, configuración de Bottlerocket) | Evita que los valores difieran entre nodos |
| **Registrar la justificación en comentarios** | Si dentro de seis meses nadie recuerda «por qué este valor», nadie podrá revertirlo |
| **Separar grupos de nodos** | Las distintas características de las cargas de trabajo requieren ajustes distintos. No impongas el mismo perfil a todo |
| **Fijar el kernel o planificar la transición** | Las AMI `kernel-default` cambian de kernel sin aviso |
| **Verificar los valores reales tras aplicarlos** | Especialmente conntrack (otro componente podría sobrescribirlos) |
| **Medir antes y después en condiciones idénticas** | Ajustar sin medir se convierte en superstición |

## Resumen

- **Deja casi todo con los valores predeterminados.** El kernel se ajusta automáticamente bajo carga, y los cambios sin evidencia crean configuraciones imposibles de reproducir y fallos al actualizar el kernel.
- La condición previa para ajustar es medir. **Empieza con los contadores de descartes**: `insert_failed`, `dropped` de qdisc y descartes de la NIC.
- Verifica la AMI seleccionada y el kernel en ejecución. La familia de AMI predeterminada puede avanzar; los ID de AMI fijados no cambian automáticamente al reemplazar nodos.
- La causa principal del throttling de CPU suele ser **la discrepancia entre la cantidad de CPU que percibe la aplicación y su cuota**. Empieza por `GOMAXPROCS`/`ActiveProcessorCount`.
- Para la estabilidad del nodo, **las reservas de kubelet y los umbrales de desalojo** son más eficaces que ajustar el kernel. El desalojo es preferible a un OOM del kernel.
- Los ajustes justificados más representativos son **el límite de conntrack, `somaxconn`, `ip_local_port_range` y `vm.max_map_count`**; todos cuentan con indicadores directos.
- Los límites sysctl de TCP y la anulación del ajuste automático por socket son cosas distintas; ajusta solo con evidencia medida.
- **Si usas IPVS, necesitas un plan de migración** (obsoleto desde 1.35; se prevé deshabilitarlo de forma predeterminada en 1.40 y eliminarlo en 1.43). Antes del despliegue, confirma el calendario vigente de KEP-5495 en el enlace siguiente.

## Referencias

- [Amazon Linux 2023: actualización del kernel de Linux](https://docs.aws.amazon.com/linux/al2023/ug/kernel-update.html)
- [AMI de Amazon Linux 2023 optimizadas para Amazon EKS](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)
- [Aumentar el límite de nf_conntrack_max en nodos de EKS](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [Ejecución de kube-proxy en modo nftables: prácticas recomendadas de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [KEP-5495: obsolescencia del modo IPVS en kube-proxy](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [Planificador EEVDF: documentación del kernel de Linux](https://docs.kernel.org/scheduler/sched-eevdf.html)
- [kernel/sched/debug.c: definiciones de parámetros debugfs](https://github.com/torvalds/linux/blob/master/kernel/sched/debug.c)
- [bottlerocket-os/bottlerocket#4221: no se aplica el límite de conntrack](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [PSI - Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [Reserva de recursos de cómputo para daemons del sistema (Kubernetes)](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [Uso de sysctls en un clúster de Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/sysctl-cluster/)
- [Optimización de recursos](../ops/10-resource-optimization.md) / [Benchmark de red de Pods](../networking/06-pod-network-benchmark.md)
