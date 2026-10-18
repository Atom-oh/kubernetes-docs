# Cuestionario de automatización y evaluación final

[Cuaderno de trabajo](../../../networking/expert/06-automation-capstone.md)

1. ¿Qué puede ocurrir si se cambian los valores esperados en la misma actualización solo para hacerlos coincidir con las observaciones?

   - A) TCP siempre se vuelve más rápido
   - B) Se pueden ocultar regresiones o infracciones de políticas
   - C) Ya no se necesita la evidencia original
   - D) La validación siempre se vuelve más estricta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Revise la intención por separado y registre su revisión y hash. Ajustar arbitrariamente a la vez la expectativa y la observación vuelve circular la validación.

</details>

2. ¿Qué demuestra el momento en que BGP vuelve al estado Established?

   - A) La convergencia del servicio se completó exactamente en ese momento
   - B) Todas las VRF están aisladas
   - C) El estado del plano de control; la recuperación del reenvío y del servicio requiere una medición aparte
   - D) Todos los paquetes se entregaron sin pérdidas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Los tiempos de anuncio, selección, FIB y recuperación de sondas pueden diferir. Alinee los puntos de observación y los ejes temporales.

</details>

3. Para un flujo prohibido, solo se observó que la solicitud agotó el tiempo de espera. ¿Cómo se debe normalizar?

   - A) Mantenerlo como desconocido sin evidencia de denegación por política
   - B) Marcarlo siempre como denegado
   - C) Marcarlo siempre como permitido
   - D) Eliminar el registro del flujo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** Un fallo de enrutamiento, de listener o de la ruta de retorno puede hacer que la sonda agote el tiempo de espera. Para demostrar la denegación, hay que correlacionar la evidencia de política con la sonda.

</details>

4. El ejemplo sintético muestra CONSISTENT_RECORD. ¿Qué se comprobó?

   - A) El éxito del reenvío en dispositivos reales
   - B) La aprobación de una implementación de producción
   - C) La autenticidad de los PCAP originales
   - D) La coincidencia entre la intención proporcionada y las condiciones del registro requerido

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** El comprobador valida la coherencia. Una etiqueta sintética o el nombre de un artefacto no demuestra el tráfico ni la recopilación reales.

</details>

5. Solo se aprueba anunciar 203.0.113.0/24, pero las observaciones también incluyen 0.0.0.0/0. ¿Qué debe ocurrir?

   - A) Aprobarlo porque más rutas son mejores
   - B) Rechazar el anuncio inesperado
   - C) Añadirlo automáticamente a la intención
   - D) Ignorar siempre las rutas predeterminadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Este contrato compara el conjunto exacto anunciado a un homólogo. No se deben ocultar los anuncios inesperados.

</details>

6. Existe una cadena de referencia a un artefacto. ¿Qué queda por verificar?

   - A) Nada
   - B) Se puede eliminar el original
   - C) La existencia, el hash, la hora, el recopilador, el punto de observación y el contenido real
   - D) Ampliar todos los permisos de cuenta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Una referencia y una evidencia confiable son cosas distintas. El ejemplo no inspecciona los originales de manera independiente.

</details>

7. ¿Se pueden comparar las rutas que FRR anuncia a su homólogo y toda la FIB de Linux como si fueran la misma lista de prefijos?

   - A) Sus alcances son distintos y requieren normalización e intención por separado
   - B) Siempre son idénticos
   - C) Basta con que tengan el mismo recuento
   - D) ECMP siempre tiene una sola ruta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** Los anuncios del plano de control y el estado de reenvío son conjuntos de datos distintos. Valide por separado los atributos o la información multipath que se pierde al convertirlos en conjuntos.

</details>

8. ¿Qué se debe comprobar después de la recuperación?

   - A) Solo que el proceso siga activo
   - B) Basta con un flujo permitido
   - C) Solo la puntuación agregada
   - D) Los flujos permitidos, el aislamiento y el acceso de administración conforme a los criterios originales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** La recuperación no se completa simplemente porque se haya copiado una configuración. Vuelva a comprobar tanto el comportamiento requerido como el prohibido usando las mismas observaciones.

</details>
