# Cuestionario sobre el ajuste del kernel de nodos de EKS

Este cuestionario evalúa su comprensión de las rutas para aplicar parámetros, las transiciones de versión del kernel y los ajustes justificados.

## Preguntas de opción múltiple

1. ¿Qué tres problemas provoca ajustar el kernel sin una justificación?
   - A) Vulnerabilidades de seguridad, infracciones de licencias y pérdida de soporte
   - B) Configuración no reproducible, fallos al actualizar el kernel y anulación del ajuste automático del kernel
   - C) Menor ancho de banda de red, mayor uso del disco y fugas de memoria
   - D) Fallos de programación de Pods, de descarga de imágenes y de autenticación

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Configuración no reproducible, fallos al actualizar el kernel y anulación del ajuste automático del kernel**

**Explicación:**
Si los valores difieren de un nodo a otro, resulta difícil reproducir incidentes. Los nombres y las ubicaciones de los parámetros ajustables cambian entre versiones del kernel (sysctl → debugfs, entre otros), así que un ajuste válido en 6.1 puede fallar en 6.18. La configuración explícita de `SO_RCVBUF`/`SO_SNDBUF` por socket deshabilita el ajuste automático del socket correspondiente; cambiar los límites de `tcp_rmem`/`tcp_wmem` no deshabilita por sí solo el ajuste automático. Por tanto, el requisito previo para ajustar parámetros es medir: relacione el síntoma con los contadores pertinentes y modifique únicamente los ajustes respaldados por esas pruebas.
</details>

2. ¿Qué debe saber sobre la transición de versión del kernel de AL2023 a partir de 2026?
   - A) AL2023 solo ofrece el kernel 6.1
   - B) Una AMI predeterminada o más reciente renovada puede seleccionar un kernel nuevo, mientras que el ID de una AMI fijada permanece sin cambios
   - C) La versión del kernel se determina automáticamente según la versión del plano de control de EKS
   - D) AL2023 no admite actualizaciones del kernel

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una AMI predeterminada o más reciente renovada puede seleccionar un kernel nuevo, mientras que el ID de una AMI fijada permanece sin cambios**

**Explicación:**
Verifique la AMI seleccionada por la plantilla de lanzamiento o el aprovisionador, así como el kernel en ejecución. Las versiones de las AMI optimizadas para EKS tienen su propio método de selección; reemplazar un nodo por sí solo no demuestra que el kernel se haya actualizado.
</details>

3. ¿Cuál es la causa raíz más común de la limitación de CPU y cuál debería ser la primera medida?
   - A) CPU insuficiente en el nodo: cambiar a un tipo de instancia más grande
   - B) Diferencia entre la cantidad de CPU que percibe la aplicación y su cuota: hacer coincidir `GOMAXPROCS`, `-XX:ActiveProcessorCount`, etc., con el límite
   - C) Un error del planificador del kernel: actualizar el kernel
   - D) Un problema de migración a cgroup v2: volver a v1

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Diferencia entre la cantidad de CPU que percibe la aplicación y su cuota: hacer coincidir `GOMAXPROCS`, `-XX:ActiveProcessorCount`, etc., con el límite**

**Explicación:**
Si el entorno de ejecución dentro del contenedor ve todos los núcleos del nodo y crea esa cantidad de subprocesos, consume al instante la cuota del límite de CPU. Con 4 subprocesos en ejecución simultánea, se consume una cuota de 20 ms en 5 ms de tiempo real y los 95 ms restantes se pasan esperando. Por eso, la primera medida es hacer coincidir la cantidad de CPU percibida con el límite, luego aumentar el límite y, por último, considerar quitarlo en casos de sensibilidad extrema.
</details>

4. ¿Qué es más eficaz que ajustar el kernel para estabilizar el nodo, y por qué?
   - A) Limitar la cantidad de Pods: una menor densidad evita problemas
   - B) Reservas de recursos de kubelet y umbrales de desalojo: una reserva insuficiente puede hacer que el kernel o kubelet agoten la memoria (OOM), dejando todo el nodo en estado `NotReady`; es preferible desalojar un Pod antes de que ocurra un OOM del kernel
   - C) Programar reinicios del nodo: reiniciarlo periódicamente para liberar memoria
   - D) Usar imágenes más pequeñas: liberar margen en el disco

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Reservas de recursos de kubelet y umbrales de desalojo: una reserva insuficiente puede hacer que el kernel o kubelet agoten la memoria (OOM), dejando todo el nodo en estado `NotReady`; es preferible desalojar un Pod antes de que ocurra un OOM del kernel**

**Explicación:**
Si `--system-reserved` y `--kube-reserved` son insuficientes, los Pods consumen toda la memoria del nodo y el kernel o kubelet sufren OOM. El nodo pasa a `NotReady` y esto afecta a todos los Pods que ejecuta, lo cual es mucho peor que un OOM individual de un Pod. El desalojo permite que Kubernetes mueva un Pod de manera controlada, mientras que el mecanismo OOM killer termina un proceso de forma abrupta; el objetivo es establecer `--eviction-hard` para que Kubernetes intervenga antes de un OOM del kernel.
</details>

5. ¿Por qué PSI (Pressure Stall Information) proporciona una señal mejor que las métricas de uso?
   - A) Mide el uso con mayor precisión
   - B) Indica qué fracción del tiempo las tareas quedan bloqueadas por ese recurso, no solo cuánto se usa; así revela el tiempo dedicado a la reclamación de memoria o a la contención aunque el gráfico de uso parezca tranquilo
   - C) Se recopila en el hardware y no en el kernel
   - D) Conserva automáticamente los datos históricos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Indica qué fracción del tiempo las tareas quedan bloqueadas por ese recurso, no solo cuánto se usa; así revela el tiempo dedicado a la reclamación de memoria o a la contención aunque el gráfico de uso parezca tranquilo**

**Explicación:**
`some avg10` en `memory.pressure` es la fracción de los últimos 10 segundos durante la que al menos una tarea estuvo bloqueada esperando ese recurso. Si el uso de memoria se mantiene estable por debajo del límite y el valor va subiendo, significa que se está dedicando tiempo a reclamar memoria de la caché de páginas, algo que un gráfico de uso por sí solo no muestra. Lo proporciona cgroup v2; está disponible para todo el nodo en `/proc/pressure/*` y para cada cgroup en `<cgroup>/memory.pressure`.
</details>

6. ¿Cuál de los siguientes casos NO es un ejemplo representativo de «ajuste justificado»?
   - A) `vm.max_map_count`: el software de la familia OpenSearch no se inicia con el valor predeterminado
   - B) `net.core.somaxconn`: hay pruebas disponibles en el contador de desbordamiento de la cola de aceptación
   - C) Cambiar los tamaños de búfer TCP sin haber medido un problema de BDP o memoria, ni entender la sobrescritura por socket
   - D) `net.ipv4.ip_local_port_range`: el agotamiento de puertos de origen aparece directamente como fallos de conexión

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Cambiar los tamaños de búfer TCP sin haber medido un problema de BDP o memoria, ni entender la sobrescritura por socket**

**Explicación:**
`tcp_rmem`/`tcp_wmem` definen límites y valores predeterminados de tamaño; cambiarlos no deshabilita por sí solo el ajuste automático. La configuración explícita de `SO_RCVBUF`/`SO_SNDBUF` deshabilita el ajuste automático del socket correspondiente.
</details>

7. ¿Qué valor no se puede cambiar mediante `securityContext.sysctls` de un Pod?
   - A) Muchos valores `net.*` que se pueden establecer por espacio de nombres de red
   - B) `net.netfilter.nf_conntrack_max`, un valor global del nodo
   - C) Valores relacionados con TCP que pertenecen al espacio de nombres de red del Pod
   - D) Todos los anteriores se pueden cambiar

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `net.netfilter.nf_conntrack_max`, un valor global del nodo**

**Explicación:**
Muchos valores `net.*` se pueden establecer por espacio de nombres de red y cambiar mediante `securityContext.sysctls` del Pod. En cambio, `vm.*`, `fs.*` y algunos valores como `net.netfilter.nf_conntrack_max` son globales al nodo y requieren la ruta de configuración de inicio del nodo o de Bottlerocket. Además, kubelet rechaza de forma predeterminada los sysctl «inseguros»; para permitir uno hay que usar `--allowed-unsafe-sysctls`, que a su vez es un ajuste del nodo.
</details>

8. ¿Qué es lo más importante a largo plazo para gestionar los cambios de parámetros del kernel?
   - A) Actualizar siempre al kernel más reciente
   - B) Gestionarlos como código, registrar la justificación en comentarios y separar los grupos de nodos según las características de las cargas de trabajo
   - C) Forzar un único perfil de ajuste idéntico en todos los nodos
   - D) Aplicar los cambios en producción de inmediato

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionarlos como código, registrar la justificación en comentarios y separar los grupos de nodos según las características de las cargas de trabajo**

**Explicación:**
Declarar los ajustes en código con `EC2NodeClass` de Karpenter, plantillas de lanzamiento o la configuración de Bottlerocket evita que los valores difieran de un nodo a otro. Sin un comentario que explique «por qué este valor», nadie podrá revertirlo seis meses después. Las distintas características de las cargas de trabajo requieren ajustes diferentes, así que use grupos de nodos separados en lugar de imponer un solo perfil. También hay que fijar o planificar la transición del kernel, verificar los valores reales después de aplicar cambios (especialmente conntrack) y medir antes y después en condiciones idénticas.
</details>
