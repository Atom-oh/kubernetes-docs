# Cuestionario de comparación de recopiladores de logs

> **Última actualización**: September 13, 2026

1. ¿Cómo se deben comparar los requisitos de recursos de los recopiladores?

   - A) Suponer una clasificación fija de memoria según el lenguaje de implementación
   - B) Comparar los mismos registros, procesamiento, destinos y ajustes de fallos
   - C) Tratar todos los recopiladores de Go como idénticos
   - D) Usar un único número publicado de eventos/segundo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comparar los mismos registros, procesamiento, destinos y ajustes de fallos**

Los límites de búfer, las cachés de metadatos, el procesamiento por lotes, los reintentos y la concurrencia afectan al uso de recursos. Un lenguaje o formato de compresión por sí solo no establece una garantía de rendimiento.

</details>

---

2. ¿Qué filtro de Fluent Bit agrega metadatos de Pod y namespace?

   - A) modify
   - B) parser
   - C) kubernetes
   - D) solo record_modifier

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) kubernetes**

El filtro kubernetes necesita etiquetas correctas y acceso autorizado a los metadatos. Habilitar Use_Kubelet requiere su propia conectividad con kubelet y comprobaciones de permisos.

</details>

---

3. ¿Cuál es el enfoque actual correcto para Promtail?

   - A) Migrar: llegó al EOL el 2 de marzo de 2026
   - B) Elegirlo para cada nueva implementación de Loki
   - C) Suponer que las instalaciones existentes seguirán recibiendo futuras actualizaciones
   - D) La retirada también incluye automáticamente lambda-promtail

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Migrar: llegó al EOL el 2 de marzo de 2026**

El aviso oficial del ciclo de vida indica migrar a Alloy u otro cliente compatible y excluye explícitamente de ese aviso al cliente independiente lambda-promtail.

</details>

---

4. ¿Qué sintaxis utiliza Grafana Alloy?

   - A) Cualquier YAML de Kubernetes sin conversión
   - B) Sintaxis de configuración de Alloy, antes River
   - C) Terraform HCL con todos los proveedores de Terraform
   - D) Solo INI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sintaxis de configuración de Alloy, antes River**

La sintaxis se parece a HCL, pero un grafo de componentes de Alloy no es un archivo de Terraform intercambiable. Valídalo con el binario de Alloy seleccionado.

</details>

---

5. ¿Cuál es el orden habitual de un pipeline de Collector?

   - A) Exporters → Receivers → Processors
   - B) Processors → Exporters → Receivers
   - C) Receivers → Processors → Exporters
   - D) Todos los componentes se ejecutan en un orden arbitrario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Receivers → Processors → Exporters**

Los Connectors pueden enlazar pipelines. La ruta actual de Loki utiliza OTLP HTTP; el loki exporter eliminado no está presente en Contrib0.160.0.

</details>

---

6. ¿Qué garantiza la transformación Lua de ejemplo?

   - A) La eliminación de todos los secretos posibles de texto arbitrario
   - B) La eliminación de los archivos de logs originales del nodo
   - C) Entrega exactamente una vez
   - D) La redacción de claves estructuradas seleccionadas y la eliminación del duplicado sin procesar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) La redacción de claves estructuradas seleccionadas y la eliminación del duplicado sin procesar**

No es un detector general de PII ni un límite de cierre ante fallos. Los valores de mensajes de texto sin formato y texto libre pueden seguir conteniendo datos sensibles.

</details>

---

7. ¿Qué nombres distinguen correctamente las etapas de descarte de Promtail heredado y Alloy?

   - A) Ambos usan stage.drop como clave YAML de Promtail
   - B) Promtail YAML drop; Alloy stage.drop
   - C) Promtail filter.exclude; Alloy ignore
   - D) Ninguno admite descartar registros

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Promtail YAML drop; Alloy stage.drop**

Las etapas de parser, template, labels y output también tienen efectos en el orden y la retención de campos. No trates un catálogo de etapas como una única cadena de procesamiento universal.

</details>

---

8. ¿Cuáles son los nombres de plugins de salida nativos de Fluent Bit para los dos destinos de AWS?

   - A) cloudwatch_logs y opensearch
   - B) solo cloudwatch y elastic
   - C) stage.cloudwatch y stage.opensearch
   - D) Loki tenant_id crea ambos destinos de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) cloudwatch_logs y opensearch**

La disponibilidad de plugins no otorga permisos IAM. Haz coincidir la identidad real de ServiceAccount, Region, endpoint, TLS y la propiedad de los recursos creados previamente.

</details>

---

9. ¿Qué hace memory_limiter cuando hay presión de memoria?

   - A) Garantiza que el proceso nunca puede sufrir OOM
   - B) Crea memoria adicional en el nodo
   - C) Puede rechazar datos con errores reintentables y solicitar la recolección de basura
   - D) Conserva automáticamente cada registro de origen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Puede rechazar datos con errores reintentables y solicitar la recolección de basura**

El comportamiento de reintentos de Receiver, los límites y las colas importan. La ventana de reintento limitada de filelog puede expirar y descartar un lote fallido.

</details>

---

10. ¿Qué debe seguir a una conversión exitosa de Promtail a Alloy?

   - A) Declarar inmediatamente una entrega y métricas idénticas
   - B) Ignorar todas las advertencias de diagnóstico
   - C) Ejecutar ambos agentes en los mismos logs indefinidamente
   - D) Verificar el análisis, estado, propiedad, autenticación, métricas propias y registros reales del backend

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Verificar el análisis, estado, propiedad, autenticación, métricas propias y registros reales del backend**

El convertidor puede cambiar un límite de tasa global por límites por pipeline y no valida los montajes de host ni los permisos de Kubernetes. Elige la propiedad de archivo o de API para evitar la recopilación duplicada.

</details>

---

[Volver a la guía](../../../observability/logging/05-collectors.md)
