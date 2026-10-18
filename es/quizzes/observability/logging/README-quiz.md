# Cuestionario de visión general de Logging

> **Última actualización**: 13 de septiembre de 2026

1. ¿Qué afirmación sobre los logs JSON estructurados es correcta?

   - A) No requieren análisis sintáctico
   - B) Siempre usan menos bytes
   - C) Los campos explícitos facilitan el análisis, pero la decodificación, el encuadre y la asignación de campos siguen siendo importantes
   - D) Enmascaran automáticamente todos los datos confidenciales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Usa un esquema de eventos probado y, por lo general, un evento codificado por línea. JSON puede ocupar más espacio que el texto sin formato, y tanto las copias sin procesar como las analizadas requieren una política de manejo de datos.

</details>

2. ¿TRACE a FATAL están numerados universalmente del 0 al 5?

   - A) No; los frameworks difieren, y OpenTelemetry usa rangos de severidad de 1 a 24 con 0 sin especificar
   - B) Sí, en todos los lenguajes
   - C) Sí, solo en Kubernetes
   - D) FATAL siempre es 0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Asigna los niveles según su significado en lugar de copiar una escala numérica inventada. El nivel de un registro por sí solo no determina si el sistema puede recuperarse, y elevar todos los registros de producción a WARN puede hacer que se pierda evidencia.

</details>

3. ¿Cuál es la disposición predeterminada común de logs de contenedores en Linux?

   - A) Archivos reales en /var/log/containers; enlaces simbólicos en /var/log/pods
   - B) Archivos reales en /var/log/pods; enlaces simbólicos de compatibilidad en /var/log/containers
   - C) Cada entorno de ejecución escribe solo en /var/lib/docker
   - D) kubectl logs contiene un archivo histórico ilimitado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Las rutas originales estaban invertidas. podLogsDir/OS/runtime puede cambiar la disposición. La rotación y --previous no crean un archivo histórico central.

</details>

4. ¿Qué se necesita para comparar de manera justa los costos de los sistemas de almacenamiento?

   - A) Solo el precio en GB de S3
   - B) Elegir siempre Loki para la factura más baja
   - C) Asumir que las consultas autogestionadas son gratuitas
   - D) Comparar ingesta, datos conservados e indexados, cómputo, consultas, solicitudes, red, recuperación y operación con la misma carga de trabajo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Las cifras antiguas de 2025 y 100 GB mezclaban unidades y no incluían una configuración reproducible. No eran mediciones de un entorno de producción; actualizar solo la fecha no las corrige.

</details>

5. ¿Cómo se debe adjuntar el contexto de una traza a un registro?

   - A) Generar identificadores sin relación para cada registro
   - B) Usar el contexto activo real; los identificadores de traza y span del ejemplo tienen 32 y 16 caracteres hexadecimales, respectivamente, y no pueden ser todo ceros
   - C) Exigir identificadores de traza en cada registro de inicio
   - D) Usar tokens de sesión como identificadores de span

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los eventos sin traza son válidos. Los nombres de los campos JSON deben asignarse al modelo de destino; los identificadores por sí solos no crean trazas distribuidas ni demuestran que haya correlación.

</details>

6. ¿Qué opción de procesamiento es más segura para el pipeline ilustrado?

   - A) Descartar cada línea que contenga HealthCheck
   - B) Confiar en el JSON de la aplicación como identidad del tenant
   - C) Separar los campos de la aplicación de los metadatos confiables y validar la redacción y el filtrado, los desplazamientos, los búferes y los reintentos
   - D) Asumir que el almacenamiento en búfer evita todas las pérdidas y duplicados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El ejemplo de Fluent Bit es un fragmento de filtro con formato clásico. Keep_Log conserva otra copia que también debe someterse a redacción. Las comprobaciones de estado fallidas pueden aportar evidencia valiosa; las garantías de entrega dependen de toda la ruta.

</details>

7. ¿Cómo se debe elegir la retención regulatoria?

   - A) Según el tipo de registro aplicable, la jurisdicción, los contratos, las retenciones legales y la política aprobada
   - B) Siete años para todos los logs financieros
   - C) Seis años para todos los logs de atención médica
   - D) Un backend con nombre prueba el cumplimiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

La etiqueta de un sector no define por sí sola todos los requisitos legales. Incluye réplicas, versiones de objetos, copias de seguridad y exportaciones en los planes de conservación, eliminación y acceso; además, prueba la restauración.

</details>

8. ¿Qué es cierto sobre sidecars y DaemonSets?

   - A) Ambos garantizan el aislamiento de tenants
   - B) emptyDir sobrevive a la eliminación de un Pod
   - C) Un DaemonSet demuestra que se entregaron todos los registros de los nodos
   - D) Los sidecars pueden ayudar a las aplicaciones que solo escriben en archivos; aún hay que validar la programación, el almacenamiento compartido, el ciclo de vida y la seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

emptyDir sobrevive a los reinicios de contenedores dentro de un Pod, pero no a su eliminación. Los DaemonSets se ejecutan en los nodos elegibles y durante una actualización gradual puede haber instancias superpuestas; varias rutas pueden duplicar registros.

</details>

9. ¿Qué afirmación sobre el almacenamiento y los clientes es correcta?

   - A) OpenSearch solo usa S3 para las instantáneas en todas las implementaciones
   - B) Importa cómo se diseñan la implementación, los índices y las consultas; UltraWarm usa S3 y caché, y hay que migrar desde Promtail después de la fecha de fin de soporte anunciada
   - C) Todas las clases de registros de CloudWatch ofrecen las mismas funciones
   - D) Una clasificación de compresión es válida sin un conjunto de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Compara los modelos de implementación reales y las necesidades de consulta. El soporte de Promtail terminó el 2026-03-02; el aviso trata lambda-promtail por separado. Elegir un sistema de almacenamiento no garantiza un costo determinado ni el cumplimiento.

</details>

10. ¿Qué implica habilitar el registro de auditoría del plano de control de EKS?

   - A) Cada solicitud y cuerpo se registra sin pérdidas
   - B) Los DaemonSets de los nodos de trabajo leen el host administrado del servidor de API
   - C) Los registros de auditoría siguen una política y se entregan a CloudWatch mediante un mecanismo de mejor esfuerzo que debe verificarse
   - D) La recopilación de stdout de la aplicación se completa automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Comprueba el estado de la actualización asíncrona, los flujos de registros reales y su conservación y acceso. Fargate usa su enrutador administrado; los registros de rendimiento de Container Insights son distintos de stdout y stderr de la aplicación.

</details>

---

[Volver a la guía](../../../observability/logging/README.md)
