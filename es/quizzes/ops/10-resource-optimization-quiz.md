# Cuestionario de optimización de recursos

> **Documento relacionado**: [Optimización de recursos](../../ops/10-resource-optimization.md)

## 1. ¿Qué afirmación describe correctamente la expulsión por presión de memoria?

- A) La clase QoS determina por sí sola el orden
- B) Importan el uso por encima de las solicitudes, la prioridad del Pod y el uso relativo
- C) Los Pods Guaranteed nunca pueden ser expulsados
- D) Los PDB impiden cualquier expulsión por presión del nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

QoS es útil, pero no establece un orden absoluto de expulsión. Distinga entre OOM por límite de contenedor, expulsión por presión de memoria y DiskPressure.

</details>

## 2. ¿Qué mide la proporción de períodos con throttling de CPU?

- A) La fracción exacta de tiempo de CPU perdido
- B) La fracción de períodos de cuota en los que hubo throttling
- C) El uso de la solicitud de CPU
- D) El uso medio de memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los threads comparten la cuota. La proporción de períodos por sí sola no determina el tiempo perdido ni demuestra que aumentar el límite sea la solución correcta.

</details>

## 3. ¿Qué afirmación sobre el heap de JVM y la memoria del contenedor es correcta?

- A) El 75 % siempre es óptimo
- B) Al elegir una proporción, mida la memoria no heap y RSS
- C) MaxRAMPercentage siempre sigue de inmediato los cambios en el límite activo del Pod
- D) SIGKILL del kernel siempre produce un volcado de heap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Metaspace, stacks, búferes directos y JNI necesitan memoria. Distinga la ergonomía de JVM de los límites de cgroup, y una excepción Java OOME de SIGKILL.

</details>

## 4. ¿Por qué puede no surtir efecto establecer JAVA_OPTS?

- A) Es una opción de seguridad que la JVM debe rechazar
- B) La JVM no la lee automáticamente a menos que el punto de entrada se la pase
- C) Kubernetes no admite variables de entorno
- D) Java 21 no puede ejecutarse en contenedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Use `JAVA_TOOL_OPTIONS` o argumentos explícitos de `java` y verifique la salida real de `VM.flags`.

</details>

## 5. ¿Qué afirmación sobre `upperBound` de VPA es correcta?

- A) Cópielo siempre al límite de memoria del contenedor
- B) Forma parte del rango de recomendaciones de solicitudes, no es el límite del contenedor
- C) Es el número máximo de réplicas de HPA
- D) Es la cantidad de memoria que garantiza que no haya OOM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Distinga `target`, `lowerBound`, `upperBound` y `uncappedTarget`. El modo inicial aún puede afectar el denominador de HPA mediante las nuevas solicitudes.

</details>

## 6. ¿Qué afirmación sobre el valor predeterminado de GOMAXPROCS en Go 1.25 o posterior es correcta?

- A) Siempre usa las CPU del host y requiere una biblioteca externa
- B) Sujeto a los valores predeterminados de versión del lenguaje/compatibilidad, tiene en cuenta la cuota y la afinidad; los ajustes explícitos deshabilitan las actualizaciones automáticas
- C) Solo usa las solicitudes de CPU
- D) 500m siempre produce 1 en todos los entornos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El ejemplo se probó con Go 1.27.2 y go.mod 1.25 o posterior. Importan el redondeo de la cuota y las condiciones del valor mínimo.

</details>

## 7. ¿Qué limitación comparten GOMEMLIMIT y el límite antiguo de espacio de objetos de Node?

- A) No acotan por completo el RSS del proceso
- B) Liberan por la fuerza toda la memoria nativa
- C) Garantizan que el contenedor no sufra OOM
- D) Cambian automáticamente las solicitudes del Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

El valor de Go es un límite flexible administrado por el runtime; la opción de Node controla el espacio antiguo de V8. Tenga en cuenta por separado las asignaciones nativas y los procesos worker múltiples.

</details>

## 8. ¿Cómo se deben elegir los números de workers de Gunicorn/Tokio?

- A) Basta con usar un múltiplo fijo del número de CPU del host
- B) Verifique los ajustes reales y pruebe el comportamiento de la cuota, la memoria y la carga de trabajo
- C) Rust no necesita límites de concurrencia porque no tiene GC
- D) La cantidad de threads/procesos no afecta la memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La configuración debe leer realmente `WEB_CONCURRENCY`. `worker_threads` explícito de Tokio prevalece sobre la variable de entorno; el grupo de tareas bloqueantes es independiente.

</details>

## 9. ¿Cómo se deben interpretar las métricas de motivo OOM y de fase Pending?

- A) Sume la métrica de motivo para obtener un conteo exacto de OOM
- B) Cuente todas las series Pending para obtener el total Pending actual
- C) Evalúe los valores 0/1 y conserve en la interpretación la limitación de último estado de las métricas de motivo
- D) Pending siempre significa que falta CPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Existen series Pending con valor cero. Combinar reinicios recientes con el último motivo OOM no reconstruye todos los OOM del intervalo.

</details>

## 10. ¿Qué afirmación sobre el empaquetado compacto y los Pods marcadores de EKS Auto Mode es correcta?

- A) Una instancia de 4 vCPU siempre admite cuatro CPU de solicitudes de aplicaciones
- B) Un Pod marcador es una reserva de capacidad de EC2
- C) Tenga en cuenta los recursos asignables, la sobrecarga y las restricciones de programación; los Pods marcadores no garantizan capacidad
- D) `preemptionPolicy: Never` impide que se pueda desalojar el Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

`Never` impide que este Pod desaloje otros. NodePool usa `karpenter.sh/v1`; el grupo de NodeClass de Auto Mode es `eks.amazonaws.com`.

</details>
