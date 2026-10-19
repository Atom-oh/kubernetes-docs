# Cuestionario sobre experimentos de producción con Spot en EKS

> **Guía relacionada**: [Experimentos de producción con Spot en EKS y evaluación de resultados](../../ops/17-spot-production-experiments.md)

## 1. Una prueba de drenaje se completa correctamente en un nodo Spot con un PDB. ¿Qué demuestra?

- A) Que la reclamación real de capacidad Spot siempre conserva la misma disponibilidad
- B) Que funciona la ruta de desalojo voluntario; la reclamación real requiere una prueba aparte
- C) Que EC2 espera al PDB antes de terminar la instancia
- D) Que la aplicación siempre dispone de dos minutos para salir

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Que funciona la ruta de desalojo voluntario; la reclamación real requiere una prueba aparte**

**Explicación:** Un PDB no puede evitar la pérdida de una instancia EC2. Prueba la entrega del aviso, el retraso del desalojo, la terminación forzada y el impacto en el servicio durante la interrupción real de la instancia y la pérdida de capacidad sin aviso.

</details>

## 2. Un Pod pendiente tiene un selector exclusivo para Spot. ¿Qué ocurre si agregas un nodo On-Demand?

- A) El Pod se mueve de inmediato, independientemente de su selector
- B) El PDB cambia el selector a On-Demand
- C) El Pod sigue sin ser apto para programarse en el nodo On-Demand
- D) La ponderación de NodePool anula el selector

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El Pod sigue sin ser apto para programarse en el nodo On-Demand**

**Explicación:** La alternativa requiere capacidad disponible y restricciones del Pod compatibles. Ampliar solo los tipos de capacidad de NodePool no elimina un selector del Pod exclusivo para Spot.

</details>

## 3. Un servicio se inicia después de cambiar un NodePool para que use solo On-Demand. ¿Qué verificó el ejercicio?

- A) La alternativa automática después de que EC2 devuelva capacidad Spot insuficiente
- B) La transición basada en la configuración, la programación y el inicio en On-Demand
- C) Suministro garantizado de Spot en todas las zonas de disponibilidad
- D) La reubicación inmediata de todos los Pods Spot existentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La transición basada en la configuración, la programación y el inicio en On-Demand**

**Explicación:** El ejercicio no inyectó un error de capacidad. Verifica por separado la gestión de errores y la alternativa en la ruta de aprovisionamiento real; si no puedes reproducirla, déjala como no verificada.

</details>

## 4. FIS informa `completed` y el nodo de reemplazo está `Ready`. ¿Qué demuestra que el servicio superó la prueba?

- A) Solo el estado de FIS
- B) Solo el estado `Ready` del nodo
- C) Que los errores del cliente, la latencia, el rendimiento y la corrección cumplen los criterios
- D) Que no hay respuestas LB 5xx, sin tener en cuenta los tiempos de espera del cliente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Que los errores del cliente, la latencia, el rendimiento y la corrección cumplen los criterios**

**Explicación:** La finalización de FIS describe la inyección del fallo. La recuperación del servicio también requiere que los Pods estén listos, que los destinos del balanceador tengan buen estado, que las solicitudes reales se completen correctamente y que el trabajo sea correcto.

</details>

## 5. ¿Qué comparación evalúa correctamente el ahorro de Spot?

- A) Informar el descuento de Spot como ahorro del servicio
- B) Comparar el costo efectivo por cada operación única exitosa que supera las comprobaciones de corrección, en condiciones equivalentes
- C) Excluir los costos de reintentos y reemplazos On-Demand
- D) Contabilizar la superposición de reemplazos tanto en la factura de EC2 como en una línea de costo adicional

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comparar el costo efectivo por cada operación única exitosa que supera las comprobaciones de corrección, en condiciones equivalentes**

**Explicación:** Incluye los gastos generales, los descuentos por compromiso, los reemplazos y los reintentos, sin contabilizar dos veces los cargos. Etiqueta como estimaciones las extrapolaciones mensuales a partir de ejecuciones breves.

</details>

## 6. ¿Cómo deben registrarse los resultados si no hay datos de experimentos?

- A) Introducir los tiempos de recuperación esperados como si fueran mediciones
- B) Registrar cero errores y aprobar
- C) Registrar NOT RUN y las mediciones faltantes; detener la expansión en producción
- D) Tratar la documentación oficial como un experimento completado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Registrar NOT RUN y las mediciones faltantes; detener la expansión en producción**

**Explicación:** El comportamiento documentado, las hipótesis y las mediciones son tipos de evidencia distintos. La ausencia de ID de ejecución y resultados sin procesar no demuestra que el sistema esté listo para producción.

</details>

## 7. La ruta mixta de E2 tuvo un 0.0556% de errores globales y un 0.8333% en su peor ventana completa de 60 segundos. Si el criterio para 60 segundos es 0.1%, ¿qué se concluye?

- A) Aprobado, porque la tasa global de errores es baja
- B) Ignora los fallos porque el p99 es bajo
- C) La ventana incumple el criterio; corrige la configuración y repite las pruebas
- D) No se puede usar Spot en ningún servicio de producción

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La ventana incumple el criterio; corrige la configuración y repite las pruebas**

**Explicación:** Un periodo saludable prolongado puede reducir la tasa global de errores. Ajusta la ventana de evaluación al SLO empresarial real y no generalices una ejecución sintética a todas las configuraciones.

</details>

## 8. Un Pod se creó con clase Guaranteed. La solicitud y el límite de CPU de su contenedor normal de destino se reducen de 200m a 50m. La solicitud y el límite de memoria siguen siendo 64Mi, y los demás contenedores conservan la configuración de recursos Guaranteed. ¿Qué se deduce?

- A) Reducir la CPU necesariamente cambia el Pod a Burstable
- B) El Pod conserva su clase Guaranteed original, con solicitudes y límites de CPU y memoria iguales después de la reducción
- C) El mismo cambio también puede convertir en Guaranteed un Pod que se creó como Burstable
- D) Los valores de CPU iguales conservan Guaranteed incluso si la solicitud y el límite de memoria difieren

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El Pod conserva su clase Guaranteed original, con solicitudes y límites de CPU y memoria iguales después de la reducción**

**Explicación:** La clase QoS se determina al crear el Pod y no puede cambiarse mediante redimensionamiento. Este diseño por contenedor mantiene iguales la solicitud y el límite de CPU y memoria correspondientes y positivos en cada contenedor aplicable, y reduce conjuntamente la solicitud y el límite de CPU de destino. Conservar Guaranteed no demuestra que se cumplan los SLO de la aplicación tras reducir recursos ni evita la reclamación de una instancia Spot.

</details>

## 9. ¿Qué pruebas confirman que se completó la inicialización, que se aplicó la reducción de CPU y que el servicio mantiene su calidad después de reducir recursos en E10?

- A) Un Pod en estado `Running` satisface las tres condiciones
- B) Una solicitud PATCH correcta a pods/resize demuestra la inicialización, la reducción completada y el cumplimiento de los SLO
- C) Verificar un `startupProbe` real y `started=true`, los recursos deseados frente a los reportados, las generaciones y el estado del redimensionamiento, además de los SLO de la aplicación después de reducir recursos
- D) Un `containerID` sin cambios y la clase Guaranteed hacen innecesarias las comprobaciones de errores de solicitud y latencia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Verificar un `startupProbe` real y `started=true`, los recursos deseados frente a los reportados, las generaciones y el estado del redimensionamiento, además de los SLO de la aplicación después de reducir recursos**

**Explicación:** El estado `Running` o el valor `started` por sí solos no demuestran que haya finalizado la inicialización; cada destino requiere un `startupProbe` que compruebe la inicialización real. La respuesta correcta a PATCH significa que se aceptó la solicitud, así que comprueba los recursos informados por kubelet, las generaciones observadas, `PodResizePending` y `PodResizeInProgress`. Después de aplicar el redimensionamiento, evalúa la calidad por separado mediante pruebas de readiness/estado del balanceador y de SLO de la aplicación, incluidos errores, p99, rendimiento y limitación de CPU.

</details>

## 10. ¿Qué demuestran las mediciones de Spot del 12 de septiembre de 2026 y la plantilla inicial publicada sobre el redimensionamiento de CPU según la fase?

- A) El p99 global bajo de E2 demuestra el beneficio de aumentar la CPU durante el inicio
- B) La plantilla inicial y las mediciones no incluyen la configuración por fases ni las pruebas requeridas, así que E10 sigue en estado NOT RUN
- C) La plantilla inicial por sí sola demuestra los recursos observados del Pod y la clase QoS después de la admisión
- D) El informe histórico de la hoja de ruta y las comprobaciones del prototipo local también completan el experimento combinado con Spot

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La plantilla inicial y las mediciones no incluyen la configuración por fases ni las pruebas requeridas, así que E10 sigue en estado NOT RUN**

**Explicación:** Los tres Deployments iniciales solicitan 50m/64Mi con límites de 500m/256Mi; esa configuración no cumple por sí misma los requisitos de Guaranteed. No incluyen la opción de redimensionamiento por fase, `resizePolicy` ni `startupProbe`, y no hay pruebas antes y después de los recursos reales, QoS o rendimiento comparativo del calentamiento. La plantilla inicial no es una observación de un Pod después de la admisión. Mantén separados el informe histórico de la hoja de ruta, las comprobaciones del prototipo local y las mediciones de Spot, y ejecuta E10 por separado.

</details>
