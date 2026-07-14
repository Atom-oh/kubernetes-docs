# Cuestionario sobre la plataforma de visibilidad de costos FinOps

1. ¿Cuál es el orden correcto de las tres fases del ciclo operativo de FinOps?
   - A) Optimize → Inform → Operate
   - B) Inform → Optimize → Operate
   - C) Operate → Inform → Optimize
   - D) Inform → Operate → Optimize

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inform → Optimize → Operate**

**Explicación:**
El ciclo de FinOps itera a través de Inform (establecer visibilidad de costos) → Optimize (reducir costos) → Operate (gobernanza). Primero se entiende quién gasta qué y cuánto, luego se optimiza y después se gestiona con políticas.

</details>

---

2. ¿Cuál es la razón principal para integrar AWS CUR (Cost and Usage Report) con Kubecost?
   - A) Reducir los costos de licencia de Kubecost
   - B) Rastrear los costos de servicios de AWS fuera de Kubernetes
   - C) Mejorar la precisión de costos a nivel de Pod al compararlos con los datos reales de facturación de AWS
   - D) Habilitar la federación multi-cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Mejorar la precisión de costos a nivel de Pod al compararlos con los datos reales de facturación de AWS**

**Explicación:**
Kubecost estima los costos según los precios públicos de lista. La integración con CUR compara estas estimaciones con los datos reales de facturación que reflejan Savings Plans, Reserved Instances y tarifas negociadas, lo que mejora significativamente la precisión de costos.

</details>

---

3. Al aplicar etiquetas de costos con Kyverno, ¿qué significa `validationFailureAction: Enforce`?
   - A) Mostrar advertencias para workloads sin etiquetas
   - B) Bloquear el despliegue de workloads sin las etiquetas requeridas
   - C) Agregar etiquetas automáticamente
   - D) Modificar etiquetas en workloads existentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Bloquear el despliegue de workloads sin las etiquetas requeridas**

**Explicación:**
`validationFailureAction: Enforce` bloquea la creación/modificación de recursos que infringen la política. Los Deployments sin etiquetas team, service y cost-center serán rechazados. Se recomienda comenzar con el modo `Audit` para advertencias y luego cambiar a `Enforce` cuando los equipos estén listos.

</details>

---

4. ¿Por qué configurar VPA en `updateMode: "Off"`?
   - A) Para deshabilitar VPA por completo
   - B) Para proporcionar solo recomendaciones sin reiniciar automáticamente los Pods
   - C) Para ajustar solo CPU mientras se mantiene fija la memoria
   - D) Para evitar conflictos con HPA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para proporcionar solo recomendaciones sin reiniciar automáticamente los Pods**

**Explicación:**
`updateMode: "Off"` hace que VPA analice el uso de recursos y proporcione recomendaciones sin reiniciar automáticamente los Pods para aplicar cambios. Esto respalda un flujo de trabajo seguro en el que las recomendaciones se revisan y se aplican manualmente mediante PRs. El dashboard de Goldilocks también aprovecha este modo.

</details>

---

5. ¿Cuál es la diferencia entre Showback y Chargeback?
   - A) Showback muestra costos, Chargeback oculta costos
   - B) Showback proporciona visibilidad de costos, Chargeback cobra realmente a departamentos/equipos
   - C) Showback es en tiempo real, Chargeback es mensual
   - D) Showback es solo para cloud, Chargeback es solo on-premises

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Showback proporciona visibilidad de costos, Chargeback cobra realmente a departamentos/equipos**

**Explicación:**
Showback muestra a cada equipo/servicio cuánto gastan para aumentar la conciencia, mientras que Chargeback descuenta realmente los costos de los presupuestos departamentales. La mayoría de las organizaciones comienzan con Showback para establecer una cultura consciente de los costos antes de pasar a Chargeback.

</details>

---

6. ¿Qué etiqueta debe tener un namespace para que Goldilocks muestre recomendaciones de recursos?
   - A) goldilocks.fairwinds.com/vpa-enabled=true
   - B) goldilocks.fairwinds.com/enabled=true
   - C) vpa.kubernetes.io/enabled=true
   - D) monitoring.goldilocks.com/watch=true

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) goldilocks.fairwinds.com/enabled=true**

**Explicación:**
Goldilocks crea automáticamente VPAs para todos los Deployments en namespaces etiquetados con `goldilocks.fairwinds.com/enabled=true` y visualiza los valores de recursos recomendados en su dashboard web.

</details>

---

7. ¿Qué significa `aggregate=label:team` en la Kubecost Allocation API?
   - A) Filtrar solo Pods con una etiqueta team
   - B) Agrupar y sumar costos por valores de la etiqueta team
   - C) Crear llamadas de API separadas por equipo
   - D) Agregar etiquetas team automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupar y sumar costos por valores de la etiqueta team**

**Explicación:**
`aggregate=label:team` indica a Kubecost que agrupe todos los costos de Pods por los valores de la etiqueta `team` (por ejemplo, team-commerce, team-platform) y los sume, proporcionando costo total, costo de CPU y costo de memoria por equipo en una sola consulta.

</details>

---

8. ¿Por qué la alerta de anomalía de costos requiere 30 minutos de costo alto sostenido antes de activarse?
   - A) El intervalo de scraping de Prometheus es de 30 minutos
   - B) Para evitar falsos positivos por picos temporales (deployments, autoscaling)
   - C) Para evitar los límites de tasa de la API de Slack
   - D) El ciclo de actualización de datos de Kubecost es de 30 minutos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para evitar falsos positivos por picos temporales (deployments, autoscaling)**

**Explicación:**
Los deployments, eventos de autoscaling y trabajos batch pueden causar picos temporales de costos. La condición `for: 30m` garantiza que las alertas se activen solo cuando los costos permanezcan elevados durante más de 30 minutos, reduciendo el ruido de las actividades operativas normales.

</details>
