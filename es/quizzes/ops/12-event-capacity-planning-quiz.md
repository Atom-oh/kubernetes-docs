# Cuestionario del playbook de planificación de capacidad para eventos

1. Cuando se configuran varios triggers (Cron + Prometheus + SQS) en un KEDA ScaledObject, ¿cómo se determina el recuento final de réplicas?
   - A) Promedio de todos los valores de los triggers
   - B) Valor más bajo (MIN)
   - C) Valor más alto (MAX)
   - D) Valor del primer trigger

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Valor más alto (MAX)**

**Explicación:**
Cuando se configuran varios triggers, KEDA selecciona el recuento de réplicas deseado más alto entre todos los triggers. Esto habilita el patrón "cron establece el piso, las métricas determinan el techo". Por ejemplo, si cron solicita 100 y Prometheus solicita 150, el resultado es 150.

</details>

---

2. En el patrón de Pause Pod, ¿qué mecanismo hace que los Pause Pods sean desalojados cuando llegan cargas de trabajo reales?
   - A) Los Pods se reemplazan automáticamente debido a solicitudes de recursos pequeñas
   - B) Un valor bajo de PriorityClass activa Preemption
   - C) DaemonSet redistribuye automáticamente los Pods
   - D) La expiración del TTL causa la eliminación automática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un valor bajo de PriorityClass activa Preemption**

**Explicación:**
A los Pause Pods se les asigna una PriorityClass con value: -10. Cuando las cargas de trabajo reales (prioridad predeterminada 0 o superior) necesitan programarse y no hay capacidad suficiente, el Kubernetes Scheduler se antepone a los Pods de menor prioridad para liberar espacio. Esto permite que las cargas de trabajo reales se programen al instante en Nodes ya aprovisionados.

</details>

---

3. ¿Por qué el trigger cron de KEDA está configurado para activarse 30 minutos antes de que comience la venta flash?
   - A) El intervalo de sondeo de KEDA es de 30 minutos
   - B) Los triggers cron no se activan en horas exactas
   - C) El aprovisionamiento de Nodes y la programación de Pods requieren tiempo de anticipación
   - D) Para evitar la limitación de velocidad de la API de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El aprovisionamiento de Nodes y la programación de Pods requieren tiempo de anticipación**

**Explicación:**
Cuando KEDA escala Pods hacia arriba, Karpenter necesita entre 60 y 90 segundos para aprovisionar nuevos Nodes, además de tiempo adicional para la programación de Pods y el inicio de contenedores. Iniciar el escalado hacia arriba 30 minutos antes garantiza que todos los Pods estén en estado Ready antes de que llegue el primer pico de tráfico.

</details>

---

4. ¿Por qué la EC2 Capacity Reservation se configura con `instance_match_criteria = "targeted"`?
   - A) Para reducir costos
   - B) Para restringir el uso de la reservation solo a Karpenter NodePools específicos
   - C) Para permitir su uso con instancias Spot
   - D) Para despliegue multi-AZ

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para restringir el uso de la reservation solo a Karpenter NodePools específicos**

**Explicación:**
La configuración `targeted` garantiza que solo las instancias que hagan referencia explícita a la Capacity Reservation puedan usarla. Esto evita que las cargas de trabajo generales consuman la capacidad reservada destinada al Karpenter NodePool específico del evento (coincidente mediante capacityReservationSelectorTerms).

</details>

---

5. ¿Cuál es el efecto de un valor alto de `weight` en un Karpenter NodePool?
   - A) Los Nodes se aprovisionan más rápido
   - B) El NodePool se prefiere sobre otros NodePools
   - C) Se pueden aprovisionar más Nodes
   - D) Se seleccionan instancias de menor costo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El NodePool se prefiere sobre otros NodePools**

**Explicación:**
Cuando varios NodePools pueden satisfacer los requisitos de un Pending Pod, Karpenter selecciona el NodePool con el weight más alto. Establecer weight: 100 en el NodePool del evento garantiza que se use antes que el NodePool predeterminado (por ejemplo, weight: 10), aplicando la configuración específica del evento (tipos de instancia, tipos de capacidad, etc.).

</details>

---

6. En el comportamiento scaleDown de HPA, ¿qué significa `type: Percent, value: 10, periodSeconds: 120`?
   - A) Escalar hacia abajo al 10% del total en 120 segundos
   - B) Reducir en un 10% los Pods actuales cada 120 segundos
   - C) Eliminar 120 Pods cada 10 segundos
   - D) Mantener un mínimo de 10 Pods y luego eliminar todos después de 120 segundos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reducir en un 10% los Pods actuales cada 120 segundos**

**Explicación:**
Esta política permite reducir hasta el 10% del recuento actual de réplicas cada 120 segundos (2 minutos). Con 200 Pods, esto significa eliminar como máximo 20 Pods cada 2 minutos, lo que evita la inestabilidad del Service por un escalado hacia abajo repentino.

</details>

---

7. ¿Por qué la hoja de cálculo de planificación de capacidad añade un margen de seguridad del 30%?
   - A) Para tener en cuenta las fluctuaciones de precio de las instancias de AWS
   - B) Para cubrir errores de predicción, tiempo de inicio de Pods y distribución desigual de la carga
   - C) Para tener en cuenta el uso de recursos de Pods del sistema Kubernetes
   - D) Debido a limitaciones de ancho de banda de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para cubrir errores de predicción, tiempo de inicio de Pods y distribución desigual de la carga**

**Explicación:**
El margen de seguridad del 30% absorbe varias incertidumbres: (1) las predicciones de tráfico pueden ser inexactas, (2) no todos los Pods llegan a estar ready simultáneamente, (3) la carga no se distribuye perfectamente entre los Pods, (4) algunos Nodes/Pods pueden fallar. El margen puede ajustarse según los datos post-mortem de eventos anteriores.

</details>

---

8. ¿Por qué el DaemonSet de precaché de imágenes usa initContainers?
   - A) Para ejecutar y terminar imágenes y ahorrar recursos
   - B) Para descargar (pull) imágenes en la caché del Node y salir, dejando solo la caché
   - C) Para validar versiones de imágenes
   - D) Para autenticarse con el Container Registry

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para descargar (pull) imágenes en la caché del Node y salir, dejando solo la caché**

**Explicación:**
Los initContainers de DaemonSet se ejecutan en cada Node y hacen pull de las imágenes de contenedor. Solo ejecutan `echo cached` y salen, pero las imágenes permanecen en la caché local del Node. Cuando los Pods de carga de trabajo reales se programan más tarde, omiten la fase de pull de imágenes (que puede tomar de decenas de segundos a minutos), lo que reduce significativamente el tiempo de inicio de los Pods.

</details>

---

9. ¿Por qué la cronología D-30 indica realizar pruebas de carga al 120% del RPM objetivo?
   - A) Para obtener aprobación previa de AWS para tráfico alto
   - B) Para verificar la estabilidad del sistema más allá del tráfico objetivo y descubrir cuellos de botella temprano
   - C) Para calcular con precisión los umbrales de triggers de KEDA
   - D) Para mejorar la precisión de la estimación de costos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para verificar la estabilidad del sistema más allá del tráfico objetivo y descubrir cuellos de botella temprano**

**Explicación:**
El tráfico real del evento puede superar las predicciones, por lo que probar al 120% ayuda a: (1) confirmar la estabilidad del sistema por encima del objetivo, (2) descubrir cuellos de botella en conexiones de DB, ancho de banda de red, API gateways, etc., y (3) validar el comportamiento real de la cadena de escalado (KEDA → HPA → Karpenter) antes del evento real.

</details>

---

10. ¿Qué situación justifica más usar instancias On-Demand en lugar de Spot para un evento?
    - A) La duración del evento supera las 4 horas
    - B) Los ahorros de Spot superan el 60%
    - C) Service crítico para ingresos donde las interrupciones no son aceptables
    - D) La carga de trabajo tiene lógica de reintentos implementada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Service crítico para ingresos donde las interrupciones no son aceptables**

**Explicación:**
Las instancias Spot pueden ser reclamadas por AWS con un aviso de 2 minutos. Los Services críticos para ingresos, como el procesamiento de pedidos durante una venta flash, deben usar On-Demand para garantizar la disponibilidad. Los Services auxiliares, como notificaciones por correo electrónico o procesamiento de logs, pueden usar Spot si tienen lógica de reintentos, lo que ahorra costos mientras mantiene la resiliencia.

</details>
