# Cuestionario de Plataforma de IA Agéntica en EKS

Veinte preguntas sobre las APIs actuales, los límites de ejecución y los límites de validación.

## 1. ¿Qué mejora principalmente PagedAttention?

<details>
<summary>Respuesta y explicación</summary>

La gestión de bloques de la KV-cache y el desperdicio de memoria. No comprime los pesos del modelo ni garantiza un rendimiento fijo de 2–4x.
</details>

## 2. ¿En qué se diferencia un inference gateway de un ejecutor de entrenamiento?

<details>
<summary>Respuesta y explicación</summary>

Un gateway/plugin compatible gestiona el enrutamiento, el acceso y los límites de inferencia. Trainer/Ray y otros sistemas ejecutan el entrenamiento. Instalar el gateway por sí solo no habilita todas las funciones de seguridad o A/B.
</details>

## 3. ¿Qué debe coincidir en un almacén de vectores de RAG?

<details>
<summary>Respuesta y explicación</summary>

La dimensión real del embedding, la revisión del modelo, la normalización, la métrica y el comportamiento de ingesta/consulta. Un campo de tenant por sí solo no es aislamiento; aplique un alcance de recuperación autenticado con filtros del lado del servidor.
</details>

## 4. ¿Qué modelo de control proporciona LangGraph?

<details>
<summary>Respuesta y explicación</summary>

Nodos con estado, aristas, enrutamiento condicional y ciclos. Un grafo por sí solo no implementa la ejecución de herramientas, el estado persistente ni los reintentos acotados.
</details>

## 5. ¿En qué se diferencian Langfuse y DCGM?

<details>
<summary>Respuesta y explicación</summary>

Langfuse rastrea llamadas instrumentadas, trazas, uso y evaluación; DCGM informa métricas de dispositivo. Las estimaciones de coste por tokens no son facturas y difieren de las mediciones de infraestructura, como la temperatura de la GPU.
</details>

## 6. ¿Qué forma de API usa Kagent 0.10.1?

<details>
<summary>Respuesta y explicación</summary>

kagent.dev/v1alpha2 con spec.type y declarative/BYO. Use declarative.modelConfig y las referencias de herramientas McpServer/Agent, no campos llm de nivel superior inventados, definiciones arbitrarias de herramientas python/eval ni campos de permissions.
</details>

## 7. ¿Qué aislamiento proporciona el time-slicing dentro de MIG?

<details>
<summary>Respuesta y explicación</summary>

Distinga el aislamiento entre instancias MIG del uso compartido dentro de una sola instancia. Los usuarios de time-slice dentro de una misma instancia no obtienen un nuevo aislamiento de memoria/fallos ni garantías de cómputo proporcional.
</details>

## 8. ¿Significa el continuous batching que las solicitudes nunca esperan?

<details>
<summary>Respuesta y explicación</summary>

No. La planificación puede admitir trabajo en cada paso, pero los presupuestos de tokens, la capacidad de KV, la concurrencia y los límites de cola pueden provocar espera. Mida el comportamiento real de la carga de trabajo.
</details>

## 9. ¿Cuándo significa un tamaño de chunk de 1000 exactamente 1000 tokens?

<details>
<summary>Respuesta y explicación</summary>

Cuando el splitter seleccionado mide tokens con el tokenizador adecuado. RecursiveCharacterTextSplitter usa por defecto conteos de caracteres. Evalúe conjuntamente los límites del modelo, las unidades semánticas y la calidad de recuperación.
</details>

## 10. ¿Qué debe comprobarse para el autoscaling de vLLM?

<details>
<summary>Respuesta y explicación</summary>

Los nombres reales de las métricas vllm:, las etiquetas de modelo/Pod, los adaptadores, las señales de cola/latencia y un único responsable del escalado. La asignación no es la utilización de GPU; evite que HPA/KEDA compitan por el control de las mismas réplicas.
</details>

## 11. ¿Qué almacena la KV cache?

<details>
<summary>Respuesta y explicación</summary>

Representaciones de clave/valor de los tokens anteriores para reducir el cómputo repetido. Se diferencia del almacenamiento en caché de respuestas; GQA/MQA, las ventanas deslizantes y otras arquitecturas cambian el cálculo de memoria.
</details>

## 12. ¿Cómo gestiona el SDK actual de Langfuse las trazas y los spans?

<details>
<summary>Respuesta y explicación</summary>

Cree observaciones span/generation hijas bajo una sola traza con start_as_current_observation y registre usage_details. El SDK inspeccionado 4.15.2 no tiene los antiguos métodos trace()/generation(). Defina también los límites de registro de secretos y datos en bruto.
</details>

## 13. ¿Por qué la búsqueda híbrida es más que dos llamadas de búsqueda?

<details>
<summary>Respuesta y explicación</summary>

Necesita RRF o una fusión de puntuaciones calibrada, filtros de autorización equivalentes, deduplicación y evaluación de recall. Las puntuaciones de distintos recuperadores no son automáticamente comparables.
</details>

## 14. ¿Qué estaba mal en el ejemplo original de SqliteSaver?

<details>
<summary>Respuesta y explicación</summary>

Use from_conn_string como gestor de contexto. :memory: no es duradero y un DSN de PostgreSQL no es SQLite. Leer el historial por sí solo no reproduce ni reanuda la ejecución, y thread_id no es autenticación.
</details>

## 15. ¿Qué particionan TP y PP?

<details>
<summary>Respuesta y explicación</summary>

TP particiona las operaciones dentro de las capas; PP particiona las etapas de capas. Elija según las restricciones de arquitectura/backend/red/memoria, no según potencias de dos universales ni un número fijo de GPUs por tamaño de modelo.
</details>

## 16. Ejercicio: ¿qué debe validar un despliegue actual de vLLM?

<details>
<summary>Respuesta y explicación</summary>

Use la imagen/modelo fijados, el ejemplo de GPU/cache/startupProbe y ClusterIP de la [guía de vLLM](../../ai-ml/02-vllm-deployment.md). Prepare el namespace, los drivers y los dispositivos. Las comprobaciones de esquema sin inferencia no establecen rendimiento ni disponibilidad.
</details>

## 17. Ejercicio: ¿qué deben validar el despliegue de Langfuse y el tracing en Python?

<details>
<summary>Respuesta y explicación</summary>

Use el ejemplo del SDK actual del [capítulo](../../ai-ml/03-agentic-ai-platform.md), las credenciales en archivo, el enlazado de spans y flush/shutdown. El chart 2.1.0 incluye web/worker, Postgres, Valkey, almacenamiento de objetos, ClickHouse y requisitos previos de operador. La entrega por defecto de secretos mediante variables de entorno difiere de una política basada solo en archivos.
</details>

## 18. Ejercicio: ¿cómo debe terminar de forma segura un bucle de reintentos de RAG cuando no hay evidencia?

<details>
<summary>Respuesta y explicación</summary>

Mantenga la pregunta original separada de search_query, establezca límites de reintentos y de recursión, genere con evidencia, reescriba dentro del presupuesto y luego absténgase cuando no se encuentre ninguna. El capítulo verifica estas rutas y la reapertura de SQLite usando callbacks deterministas locales.
</details>

## 19. Avanzado: ¿qué límites importan en un agente de consultoría financiera?

<details>
<summary>Respuesta y explicación</summary>

Diseñe un alcance autenticado de tenant/cuenta, permisos de recuperación, egress hacia el proveedor, herramientas con privilegios mínimos/idempotentes/aprobadas, registro mínimo de datos sensibles, auditoría y traspaso a una persona. No sobrescriba un requires_human=true existente con false en una rama posterior. El nombre de una función compliance_check o una decisión del LLM no certifica el cumplimiento normativo.
</details>

## 20. Avanzado: ¿cómo deben validarse el enrutamiento multimodelo, las pruebas A/B y la optimización de costes?

<details>
<summary>Respuesta y explicación</summary>

Use adaptadores/credenciales de proveedor y rechace cuando ningún candidato cumpla las restricciones de proveedor permitido, presupuesto y calidad. Implemente una asignación A/B estable, consumidores de enrutamiento reales y guardrails medidos. Las claves de caché incluyen las revisiones de tenant/autorización/modelo/recuperación; las estimaciones de coste incluyen las llamadas de enrutamiento, los reintentos, las cachés y los costes fijos de GPU. Los porcentajes de ahorro inventados no son resultados.
</details>

[Volver al capítulo](../../ai-ml/03-agentic-ai-platform.md)
