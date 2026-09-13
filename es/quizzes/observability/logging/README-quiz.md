# Cuestionario de visión general de Logging

> **Última actualización**: September 13, 2026

1. ¿Qué afirmación sobre los logs JSON estructurados es correcta?

   - A) No necesitan análisis
   - B) Siempre usan menos bytes
   - C) Los campos explícitos ayudan al análisis, pero la decodificación, el enmarcado y el mapeo de campos siguen siendo importantes
   - D) Enmascaran automáticamente todos los datos confidenciales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Usa un esquema de eventos probado y normalmente un evento codificado por línea. JSON puede ser más grande que el texto sin formato, y tanto las copias sin procesar como las analizadas necesitan una política de gestión de datos.

</details>

2. ¿TRACE a FATAL están numerados universalmente del 0 al 5?

   - A) No; los frameworks difieren, y OpenTelemetry usa rangos de severidad de 1 a 24 con 0 sin especificar
   - B) Sí, en todos los lenguajes
   - C) Sí, solo en Kubernetes
   - D) FATAL siempre es 0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Mapea el significado de la severidad en lugar de copiar una escala numérica inventada. Un nivel de log por sí solo no determina la capacidad de recuperación, y elevar todos los logs de producción a WARN puede perder evidencia.

</details>

3. ¿Cuál es la disposición predeterminada común de logs de contenedores en Linux?

   - A) Archivos reales en /var/log/containers; enlaces simbólicos en /var/log/pods
   - B) Archivos reales en /var/log/pods; enlaces simbólicos de compatibilidad en /var/log/containers
   - C) Cada runtime escribe solo en /var/lib/docker
   - D) kubectl logs contiene un archivo ilimitado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Las rutas originales estaban invertidas. podLogsDir/OS/runtime puede cambiar la disposición. La rotación y --previous no crean un archivo histórico central.

</details>

4. ¿Qué se requiere para una comparación justa de costos de backend?

   - A) Solo el precio en GB de S3
   - B) Elegir siempre Loki para la factura más baja
   - C) Asumir que las consultas autogestionadas son gratuitas
   - D) Comparar ingesta, datos retenidos/indexados, cómputo, consultas, solicitudes, red, recuperación y operaciones con la misma carga de trabajo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Las cifras antiguas de 2025 y 100 GB mezclaban unidades y carecían de una configuración reproducible. No eran resultados de producción medidos; actualizar solo la fecha no los corrige.

</details>

5. ¿Cómo se debe adjuntar el contexto de trace a un log?

   - A) Generar ID no relacionados para cada registro
   - B) Usar el contexto activo real; los ID de trace/span mostrados tienen 32/16 caracteres hexadecimales y no pueden ser todos cero
   - C) Exigir ID de trace en cada registro de inicio
   - D) Usar tokens de sesión como ID de span

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los eventos sin trace son válidos. Los nombres de campos JSON requieren mapeo al modelo de destino; los ID por sí solos no crean traces distribuidos ni prueban correlación.

</details>

6. ¿Qué opción de procesamiento es más segura para el pipeline ilustrado?

   - A) Descartar cada línea que contenga HealthCheck
   - B) Confiar en JSON de la aplicación como identidad del tenant
   - C) Separar los campos de la aplicación de los metadatos de confianza y validar el enmascaramiento/el filtrado, los offsets, los búferes y los reintentos
   - D) Asumir que el almacenamiento en búfer evita todas las pérdidas y duplicados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El ejemplo de Fluent Bit es un fragmento de filtro de formato clásico. Keep_Log conserva otra copia para enmascarar. Las comprobaciones de estado fallidas pueden ser evidencia valiosa, y las garantías de entrega dependen de toda la ruta.

</details>

7. ¿Cómo se debe elegir la retención regulatoria?

   - A) Según el tipo de registro aplicable, la jurisdicción, los contratos, las retenciones legales y la política aprobada
   - B) Siete años para todos los logs financieros
   - C) Seis años para todos los logs de atención médica
   - D) Un backend con nombre prueba el cumplimiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Una etiqueta de industria no es una regla legal completa. Incluye réplicas, versiones de objetos, copias de seguridad y exportaciones en los planes de retención/eliminación/acceso, y prueba la restauración.

</details>

8. ¿Qué es cierto sobre sidecars y DaemonSets?

   - A) Ambos garantizan el aislamiento de tenants
   - B) emptyDir sobrevive a la eliminación de un pod
   - C) Un DaemonSet prueba que se entregaron todos los logs de los nodos
   - D) Los sidecars pueden ayudar a las aplicaciones solo de archivos; la programación, el almacenamiento compartido, el ciclo de vida y la seguridad aún necesitan validación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

emptyDir sobrevive a los reinicios de contenedores dentro de un pod, no a la eliminación de un pod. Los DaemonSets se dirigen a nodos elegibles y pueden tener superposición de despliegue; múltiples rutas pueden duplicar registros.

</details>

9. ¿Qué afirmación sobre almacenamiento/cliente es correcta?

   - A) OpenSearch solo usa S3 para snapshots en todos los despliegues
   - B) El diseño de Deployment/índice/consulta importa; UltraWarm usa S3/caché y Promtail necesita migración después de su EOL indicado
   - C) Todas las clases de logs de CloudWatch tienen funcionalidades idénticas
   - D) Una clasificación de compresión es válida sin un conjunto de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Compara los modelos de despliegue reales y las necesidades de consulta. El EOL de Promtail es 2026-03-02; el aviso trata lambda-promtail por separado. Elegir un backend no garantiza el costo ni el cumplimiento.

</details>

10. ¿Qué establece habilitar el logging de auditoría del plano de control de EKS?

   - A) Cada solicitud y cuerpo se registra sin pérdidas
   - B) Los DaemonSets de worker leen el host administrado del servidor API
   - C) Los registros de auditoría siguen una política y una ruta de entrega de CloudWatch de mejor esfuerzo que debe verificarse
   - D) La recopilación de stdout de la aplicación se completa automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Comprueba el estado de actualización asíncrona, los streams reales y la retención/el acceso. Fargate usa su router administrado; los logs de rendimiento de Container Insights son distintos del stdout/stderr de la aplicación.

</details>

---

[Volver a la guía](../../../observability/logging/README.md)
