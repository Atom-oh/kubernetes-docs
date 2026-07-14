# Quiz de optimización de recursos

> **Documento relacionado**: [Optimización de recursos](../../ops/10-resource-optimization.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es la diferencia entre resource requests y limits en Kubernetes?

- A) Requests son solo para CPU, limits son solo para memoria
- B) Requests son recursos garantizados para la programación; limits son el máximo permitido
- C) Requests y limits son lo mismo
- D) Limits están garantizados, requests son opcionales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Requests son recursos garantizados para la programación; limits son el máximo permitido**

**Explicación:**
Requests son los recursos que Kubernetes garantiza a un container y usa para las decisiones de programación. Limits son los recursos máximos que un container puede usar. Superar los CPU limits provoca throttling; superar los memory limits puede provocar OOM kills.

</details>

### 2. ¿Qué clase de QoS obtiene la prioridad más alta durante la presión de recursos del node?

- A) BestEffort
- B) Burstable
- C) Guaranteed
- D) Todas las clases tienen la misma prioridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Guaranteed**

**Explicación:**
Los pods Guaranteed (requests=limits tanto para CPU como para memoria) tienen la prioridad más alta y son los últimos en ser desalojados durante la presión de recursos. Los pods BestEffort (sin requests/limits) son desalojados primero, seguidos por los pods Burstable.

</details>

### 3. ¿Qué causa CPU throttling en los containers de Kubernetes?

- A) Memoria insuficiente
- B) Que el container supere su CPU limit durante un período de CFS
- C) Congestión de red
- D) Cuello de botella de E/S de disco

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Que el container supere su CPU limit durante un período de CFS**

**Explicación:**
El Linux CFS (Completely Fair Scheduler) aplica CPU limits en períodos de 100 ms. Si un container usa su cuota al inicio del período, se le aplica throttling (se pausa) hasta que comienza el siguiente período. Esto se registra en `cpu.cfs_throttled_us`.

</details>

### 4. ¿Cuál es la configuración recomendada de JVM MaxRAMPercentage para containers?

- A) 100%
- B) 90%
- C) 75%
- D) 50%

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 75%**

**Explicación:**
Configurar MaxRAMPercentage en 75% deja el 25% de la memoria del container para uso fuera del heap: metaspace, stacks de threads, memoria nativa y sobrecarga del OS. Usar valores más altos implica riesgo de OOM kills cuando la memoria fuera del heap crece inesperadamente.

</details>

### 5. En VPA, ¿qué hace el modo de actualización "Initial"?

- A) Actualiza los pods continuamente
- B) Solo establece recursos cuando los pods se crean por primera vez
- C) Elimina todos los pods existentes
- D) Deshabilita VPA por completo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo establece recursos cuando los pods se crean por primera vez**

**Explicación:**
El modo "Initial" aplica las recomendaciones de VPA solo en el momento de creación del pod, no a los pods en ejecución. Esto es útil con HPA porque evita conflictos: VPA establece el tamaño inicial, HPA gestiona el escalado y los pods existentes no se interrumpen.

</details>

### 6. ¿Qué configuración del runtime de Go debe configurarse según los CPU limits del container?

- A) GOGC
- B) GOMAXPROCS
- C) GOPATH
- D) GOROOT

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) GOMAXPROCS**

**Explicación:**
GOMAXPROCS controla el número de threads del OS que ejecutan código Go. De forma predeterminada, Go usa todas las CPU del host, no los límites del container. Configurar GOMAXPROCS para que coincida con los CPU limits del container (usando la biblioteca automaxprocs) evita el cambio de contexto excesivo.

</details>

### 7. ¿Para qué se usa GOMEMLIMIT en aplicaciones Go?

- A) Establecer la asignación mínima de memoria
- B) Proporcionar una sugerencia de límite de memoria suave al garbage collector
- C) Limitar el número de goroutines
- D) Configurar la memoria swap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar una sugerencia de límite de memoria suave al garbage collector**

**Explicación:**
GOMEMLIMIT indica al garbage collector de Go el techo de memoria objetivo. El GC se activa antes a medida que la memoria se acerca a este límite, lo que reduce el riesgo de OOM kills y, aun así, utiliza la memoria disponible de manera eficiente.

</details>

### 8. Para workers de Python Gunicorn en containers, ¿cuál es la fórmula recomendada para el número de workers?

- A) 2 * CPU_CORES + 1
- B) Basada en el CPU limit del container, no en los cores del host
- C) Usar siempre 1 worker
- D) Usar 100 workers para el máximo throughput

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Basada en el CPU limit del container, no en los cores del host**

**Explicación:**
La fórmula clásica (2*cores+1) usa el número de CPU del host, lo que provoca sobreasignación en containers. El número de workers debe basarse en los CPU limits del container (por ejemplo, 2-4 workers por CPU limit) para evitar contención de recursos y problemas de OOM.

</details>

### 9. ¿Qué le sucede a un container que supera su memory limit?

- A) Se le aplica CPU throttling
- B) El kernel lo finaliza por OOM
- C) Escala horizontalmente de forma automática
- D) Toma memoria prestada de otros containers

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El kernel lo finaliza por OOM**

**Explicación:**
A diferencia de la CPU (a la que se le aplica throttling), los memory limits se aplican de forma estricta. Cuando un container supera su memory limit, el OOM killer de Linux termina procesos en el container. Luego Kubernetes reinicia el container según su restart policy.

</details>

### 10. ¿Cuál es el propósito del componente VPA Recommender?

- A) Reiniciar pods con nuevos recursos
- B) Analizar el uso de recursos y generar recomendaciones de recursos
- C) Gestionar el escalado de nodes
- D) Validar configuraciones de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Analizar el uso de recursos y generar recomendaciones de recursos**

**Explicación:**
El VPA Recommender observa el uso real de recursos de los containers a lo largo del tiempo y genera recomendaciones para requests y limits. Considera patrones de uso de CPU y memoria, picos y variación para sugerir valores adecuados.

</details>
