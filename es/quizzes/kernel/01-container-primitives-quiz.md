# Cuestionario sobre las funciones del kernel que sustentan los contenedores

Este cuestionario evalúa tu comprensión de los espacios de nombres, cgroup v2, netfilter y conntrack.

## Preguntas de opción múltiple

1. ¿Qué significa «no hay un contenedor en el kernel» y qué conclusión práctica se desprende?
   - A) Los contenedores son un tipo de máquina virtual y no guardan relación con el kernel
   - B) Un contenedor es una convención que combina espacios de nombres, cgroups, capacidades y otros elementos; por ello, el aislamiento es selectivo y el aislamiento que omita un entorno de ejecución se convierte en una brecha silenciosa
   - C) Los contenedores se implementan exclusivamente mediante bibliotecas de espacio de usuario
   - D) El kernel 6.x añadió una `struct container`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un contenedor es una convención que combina espacios de nombres, cgroups, capacidades y otros elementos; por ello, el aislamiento es selectivo y el aislamiento que omita un entorno de ejecución se convierte en una brecha silenciosa**

**Explicación:**
No existe una `struct container` ni una única llamada al sistema que cree uno. Un entorno de ejecución inicia un proceso mientras aplica conjuntamente espacios de nombres (aislamiento), cgroups (límites), capacidades/seccomp/LSM (privilegios), overlayfs (sistema de archivos) y netfilter (red). De que sea una combinación se desprenden dos conclusiones: el aislamiento no es total o inexistente, sino selectivo (un Pod que comparte el espacio de nombres de red y separa los montajes es un ejemplo); y, como el kernel no entiende la instrucción «crear un contenedor», si un entorno de ejecución no aplica un perfil de seccomp, el proceso se ejecuta sin él.
</details>

2. ¿Por qué dos contenedores de un Pod pueden comunicarse entre sí por `localhost`, pero no pueden enlazarse al mismo puerto?
   - A) Kubernetes crea automáticamente un proxy entre contenedores
   - B) Comparten un espacio de nombres de red por Pod, así que usan el mismo espacio de direcciones IP y puertos
   - C) CNI conecta un loopback por contenedor
   - D) kube-proxy enruta el tráfico dentro del Pod

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Comparten un espacio de nombres de red por Pod, así que usan el mismo espacio de direcciones IP y puertos**

**Explicación:**
Kubernetes crea un espacio de nombres de red por Pod (que mantiene el contenedor pause) y coloca en él todos los contenedores del Pod. Por eso comparten el mismo espacio de direcciones IP y puertos, funciona `localhost` y dos contenedores no pueden enlazarse ambos al puerto 8080. Esta es la base del patrón sidecar. Además, las reglas de netfilter son por espacio de nombres de red, así que el contenedor init de un mesh sidecar puede instalar reglas de iptables dentro del Pod sin afectar a todo el nodo.
</details>

3. ¿Por qué `memory.current` puede mantenerse cerca del límite en cgroup v2 y aun así ser completamente normal?
   - A) `memory.current` es una estimación y, por tanto, es inexacto
   - B) `memory.current` incluye la caché de páginas, que se puede reclamar: al alcanzar el límite, el kernel la descarta para liberar espacio
   - C) cgroup v2 no aplica límites
   - D) `memory.current` muestra la memoria de todo el nodo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `memory.current` incluye la caché de páginas, que se puede reclamar: al alcanzar el límite, el kernel la descarta para liberar espacio**

**Explicación:**
Aunque la memoria que realmente conserva la aplicación (anon/RSS) esté muy por debajo del límite, leer muchos archivos acumula caché de páginas y eleva `memory.current` hasta el límite. Sin embargo, la caché de páginas se puede reclamar, así que normalmente el kernel la descarta para liberar espacio y no se produce un OOM. El problema aparece **cuando la recuperación no puede seguir el ritmo de las asignaciones**; entonces entra en acción el OOM killer. Por eso el diagnóstico debe combinar `memory.stat` → `anon`, `memory.events` → `oom` y PSI (`memory.pressure`).
</details>

4. Si el uso de CPU es bajo (20 %), pero la latencia p99 se dispara, ¿cómo confirmas que la causa es el límite de CPU?
   - A) Volver a comprobar el uso con `top`
   - B) Comprobar la proporción entre `nr_throttled` y `nr_periods` en `cpu.stat`
   - C) Comprobar `memory.pressure`
   - D) Comprobar `/proc/loadavg` del nodo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Comprobar la proporción entre `nr_throttled` y `nr_periods` en `cpu.stat`**

**Explicación:**
Un límite de CPU limita el ancho de banda de CPU. `cpu.max` con el valor `20000 100000` significa «hasta 20 ms por periodo de 100 ms», así que una aplicación que ejecuta ráfagas breves en varios subprocesos consume la cuota enseguida y se detiene a la fuerza hasta que termina el periodo. El uso medio parece del 20 % mientras aumenta la latencia. Una proporción significativa de `nr_throttled / nr_periods` indica que la causa es el límite. La causa raíz suele ser una diferencia entre la cantidad de CPU que percibe la aplicación y su cuota, así que primero ajusta `GOMAXPROCS` o `-XX:ActiveProcessorCount`.
</details>

5. ¿Qué afirmación sobre los modos de kube-proxy es correcta a partir de 2026?
   - A) nftables es el valor predeterminado e iptables se eliminó
   - B) nftables alcanzó la disponibilidad general (GA) en 1.33, IPVS quedó obsoleto en 1.35 (se prevé deshabilitarlo de forma predeterminada en 1.40 y eliminarlo en 1.43) y el valor predeterminado sigue siendo iptables
   - C) IPVS es el valor predeterminado y nftables está en fase alpha
   - D) Los tres modos tienen características de rendimiento idénticas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) nftables alcanzó la disponibilidad general (GA) en 1.33, IPVS quedó obsoleto en 1.35 (se prevé deshabilitarlo de forma predeterminada en 1.40 y eliminarlo en 1.43) y el valor predeterminado sigue siendo iptables**

**Explicación:**
El modo nftables maduró de alpha en 1.29 a beta en 1.31 y **GA en 1.33**; ofrece búsquedas O(1) y actualizaciones incrementales de reglas (requiere kernel 5.13+ en los nodos de trabajo; AL2023 lo cumple). El modo IPVS quedó **obsoleto en 1.35 (diciembre de 2025)**; upstream prevé deshabilitarlo de forma predeterminada en 1.40 y eliminarlo en 1.43. Son fechas futuras previstas: consulta el [calendario mantenido de KEP-5495](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md). Se recomienda nftables como reemplazo, pero **iptables sigue siendo el valor predeterminado**, por lo que cambiar de modo requiere una decisión explícita.
</details>

6. ¿Cómo debe verificarse la sospecha de agotamiento de conntrack?
   - A) Un kernel panic evidente y visible de inmediato en `dmesg`
   - B) Correlacionar la cantidad y el máximo de conntrack, los contadores de inserción/descarte y los registros del kernel; `insert_failed` por sí solo no demuestra de forma exclusiva que haya agotamiento
   - C) Se cortan de inmediato todas las conexiones existentes
   - D) El uso de CPU llega al 100%

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Correlacionar la cantidad y el máximo de conntrack, los contadores de inserción/descarte y los registros del kernel; `insert_failed` por sí solo no demuestra de forma exclusiva que haya agotamiento**

**Explicación:**
El seguimiento también puede aplicarse al tráfico que no usa NAT. El DNS de un Service headless evita el DNAT de VIP, pero no omite automáticamente el seguimiento de conexiones.
</details>

7. ¿Qué debes tener en cuenta al ajustar los valores de conntrack en EKS?
   - A) Basta con configurar sysctl en el inicio del nodo
   - B) El ConfigMap `kube-proxy-config` que EKS proporciona de forma predeterminada tiene prioridad sobre los argumentos de la línea de comandos, así que kube-proxy puede revertir el cambio si solo aumentas sysctl
   - C) conntrack es un valor fijo que no se puede ajustar
   - D) `securityContext.sysctls` de un Pod puede cambiar valores globales del nodo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El ConfigMap `kube-proxy-config` que EKS proporciona de forma predeterminada tiene prioridad sobre los argumentos de la línea de comandos, así que kube-proxy puede revertir el cambio si solo aumentas sysctl**

**Explicación:**
kube-proxy también administra los valores de conntrack y EKS proporciona de forma predeterminada un ConfigMap `kube-proxy-config` que tiene prioridad sobre los argumentos de la CLI. La ruta correcta consiste en ajustar `conntrack.maxPerCore`/`conntrack.min` en el ConfigMap y reiniciar el DaemonSet de kube-proxy. Se usa `maxPerCore` porque, al ser un valor por núcleo y no absoluto, se escala proporcionalmente en nodos de distintos tamaños. D es incorrecta: `nf_conntrack_max` es global al nodo y no se puede cambiar desde la especificación de un Pod.
</details>

8. ¿Qué problema operativo provoca la operación de copy-up de overlayfs?
   - A) Las capas de imagen se almacenan de forma redundante y aumenta el tamaño del registro
   - B) Al modificar un archivo de lowerdir, se copia el archivo completo a upperdir, así que incluso un cambio pequeño en un archivo grande paga el costo completo de la copia
   - C) El tiempo de inicio del contenedor aumenta con la cantidad de capas
   - D) El rendimiento de lectura se degrada en proporción a la cantidad de capas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Al modificar un archivo de lowerdir, se copia el archivo completo a upperdir, así que incluso un cambio pequeño en un archivo grande paga el costo completo de la copia**

**Explicación:**
overlayfs combina un lowerdir de solo lectura (las capas de imagen) con un upperdir modificable (los cambios). Para modificar un archivo de lowerdir, primero hay que copiarlo a upperdir, y esa es una **copia del archivo completo**: cambiar un byte de un archivo de 1 GB copia 1 GB. Por eso, muchas escrituras dentro de un contenedor consumen almacenamiento efímero del nodo, y **las rutas con muchas escrituras deben ir en volúmenes** como emptyDir o un PVC.
</details>
