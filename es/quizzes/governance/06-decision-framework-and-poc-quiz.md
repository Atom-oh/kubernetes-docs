# Cuestionario sobre el marco de decisión y el diseño de PoC

> Este cuestionario evalúa su comprensión del [marco de decisión y el diseño de PoC](../../governance/06-decision-framework-and-poc.md).

---

1. ¿Qué identifica este documento como «la mayor brecha» entre los factores de decisión?
   - A) Las convenciones para nombrar etiquetas
   - B) Los objetivos de RTO/RPO por CUJ
   - C) El número de versión de EKS
   - D) El tamaño del CIDR de VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los objetivos de RTO/RPO por CUJ**

**Explicación:**
Sin definir objetivos de RTO/RPO por CUJ, no se puede determinar si la conmutación por error del runtime de EKS A/B es lo bastante rápida, qué modelo de propiedad de datos permite recuperarlos realmente ni si importan las diferencias de configuración entre AZ. Este objetivo debe definirse antes que cualquier otra cosa.

</details>

---

2. ¿Qué relación existe entre el reenvío ponderado de ALB y el modo fail-open?
   - A) Un grupo en mal estado siempre conmuta a otro
   - B) La conmutación automática entre grupos y el enrutamiento a targets en mal estado dentro de un grupo son mecanismos distintos
   - C) Los pesos garantizan el RTO
   - D) Los targets se replican entre Regions

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La conmutación automática entre grupos y el enrutamiento a targets en mal estado dentro de un grupo son mecanismos distintos**

**Explicación:**
El reenvío ponderado no transfiere automáticamente a otro grupo el peso de un grupo vacío o en mal estado. Evalúe por separado los umbrales de estado de DNS y enrutamiento del grupo seleccionado.

</details>

---

3. ¿Por qué se ejecuta la «prueba en seco de la matriz de decisión» como PoC-0, antes que las demás PoC?
   - A) Porque es la opción más barata
   - B) Porque todas las demás opciones (evaluar de forma independiente los límites, configuraciones híbridas, etc.) establecen como condición de validez que se puedan reproducir mediante una matriz de decisión; por eso ningún resultado de PoC se convierte en estándar sin ella
   - C) Porque requiere la aprobación de AWS SA
   - D) Porque no guarda relación con las demás PoC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Porque todas las demás opciones (evaluar de forma independiente los límites, configuraciones híbridas, etc.) establecen como condición de validez que se puedan reproducir mediante una matriz de decisión; por eso ningún resultado de PoC se convierte en estándar sin ella**

**Explicación:**
En la prueba en seco de la matriz de decisión, dos personas aplican la matriz de forma independiente a entre 10 y 15 cargas de trabajo representativas, con objetivos de ejemplo locales de menos del 20 % de desacuerdo y menos del 15 % de excepciones. El recuento estimado resultante de Accounts, VPC y clústeres determina los objetivos de medición para las PoC restantes.

</details>

---

4. ¿Qué afirmación describe correctamente los controles de Regions sin uso?
   - A) Se pueden desactivar todas las Regions predeterminadas
   - B) Combinar SCP, detección, desactivación compatible de Regions opt-in y comprobaciones de costos de recursos existentes
   - C) GuardDuty por sí solo bloquea las API
   - D) Desactivar una Region elimina todos los recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Combinar SCP, detección, desactivación compatible de Regions opt-in y comprobaciones de costos de recursos existentes**

**Explicación:**
No se pueden desactivar las Regions habilitadas de forma predeterminada. Desactivar una Region opt-in no elimina los recursos existentes ni garantiza que cesen los cargos; por eso, planifique conjuntamente la limpieza y los controles de acceso.

</details>
