# Cuestionario sobre la hoja de ruta de la guía

1. En el mapa de dominios, ¿a qué capa pertenecen los dominios Storage y Database?
   - A) Fundamentos
   - B) Conectividad
   - C) Estado
   - D) Transversales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Estado**

**Explicación:**
En la tabla del mapa de dominios, Storage (EBS gp2 frente a gp3, medido con fio) y Database (el panorama de operadores y una prueba comparativa de ClickHouse con 100 millones de filas) pertenecen a la capa «Estado». Fundamentos incluye Linux y Container; Conectividad incluye Networking y Service Mesh; Transversales incluye Security & Policy, GitOps, Platform Engineering, Container Registry, Observability y la guía de operaciones.

</details>

2. ¿Qué orden de capas coincide con el mapa del flujo de aprendizaje de la hoja de ruta?
   - A) Orquestación → Fundamentos → Conectividad → Estado → Datos e IA → Transversales
   - B) Fundamentos → Orquestación → Conectividad → Estado → Datos e IA → Transversales
   - C) Fundamentos → Conectividad → Orquestación → Datos e IA → Estado → Transversales
   - D) Transversales → Fundamentos → Orquestación → Conectividad → Estado → Datos e IA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Fundamentos → Orquestación → Conectividad → Estado → Datos e IA → Transversales**

**Explicación:**
El mapa de flujo de aprendizaje muestra los quince dominios de la guía «desde los fundamentos (Linux/Container), pasando por la orquestación (Kubernetes/EKS), la conectividad (Networking/Service Mesh), el estado (Storage/Database) y los datos e IA (Data Pipeline/AI-ML), hasta las preocupaciones transversales (Security/GitOps/Platform/Container Registry/Observability/Operations)». Es una historia continua que comienza en el kernel de Linux y abarca toda la pila cloud native.

</details>

3. ¿Cuál de estos dominios **no** forma parte de la serie de pruebas comparativas medidas de la hoja de ruta?
   - A) Service Mesh (Istio sidecar frente a ambient)
   - B) Storage (EBS gp2 frente a gp3)
   - C) Database (ClickHouse en EKS)
   - D) GitOps (ArgoCD, Flux)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) GitOps (ArgoCD, Flux)**

**Explicación:**
La serie de pruebas comparativas medidas consta de «documentos que informan de ejecuciones anteriores en recursos de AWS»: Istio sidecar frente a ambient (latencia P50/P99 por plano de datos mTLS y tasas de 503 durante los rollouts), la prueba de EBS gp2 frente a gp3 (una diferencia de 10x en IOPS con la misma capacidad y el límite de créditos de ráfaga de gp2), la prueba de ClickHouse en EKS (rendimiento de ingesta de 100 millones de filas, relaciones de compresión y latencia de consultas) y la prueba de Kafka en EKS (registros de rendimiento RF3/RF1 de una sola ejecución, entre otros), además de la prueba comparativa de red de Pods: cinco entradas en esta lista. GitOps es un dominio transversal, pero no tiene una página con mediciones en la serie.

</details>

4. ¿Cuál es el orden de lectura de la ruta recomendada ③, «Plataforma de datos e IA»?
   - A) AI/ML → Data Pipeline → Database → Storage
   - B) Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow)
   - C) Data Pipeline → Storage → AI/ML → Database
   - D) Database → Storage → AI/ML → Data Pipeline

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow)**

**Explicación:**
La ruta ③ sigue «Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow)» y añade que, si necesitas GPU y control de la planificación, debes incluir las partes de Custom Scheduler de Kubernetes Core Concepts. Avanza desde la capa Estado hasta la capa Datos e IA.

</details>

5. En la ruta recomendada ①, «Incorporación a la infraestructura», ¿cómo indica la hoja de ruta que compruebes lo aprendido?
   - A) Con el cuestionario de cada documento, y realizando los laboratorios en paralelo
   - B) Leyendo primero toda la serie de pruebas comparativas medidas
   - C) Exportando una tarjeta para compartir el diagrama
   - D) Entregando la URL llms.txt a un LLM y pidiéndole un resumen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Con el cuestionario de cada documento, y realizando los laboratorios en paralelo**

**Explicación:**
La ruta ① indica «Linux Basics → Container Technology → Introduction to Kubernetes → Core Concepts (pods/services/storage/configuration) → EKS Cluster Creation → Network Fundamentals» y recomienda «comprobar lo aprendido con el cuestionario de cada documento y realizar los laboratorios en paralelo»; los laboratorios empiezan en `labs/README.md`. La serie de pruebas comparativas medidas se presenta como evidencia para la ruta ②, Plataforma/SRE.

</details>

6. Quieres publicar un diagrama en LinkedIn donde el flujo realmente se mueva en el feed. ¿Qué procedimiento coincide con la receta de 30 segundos de la hoja de ruta?
   - A) Grabar la vista con una grabadora de pantalla y convertirla a GIF
   - B) Comprobar que el control Live/Still de la barra de herramientas indique Live y, después, elegir Export (`E`) → WebM para descargar la animación de trazas de 6 segundos
   - C) Elegir Export → SVG y subirlo a LinkedIn como vídeo
   - D) Resolver una ruta con Route Probe (`R`) y usar Copy diagram para copiarla al portapapeles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comprobar que el control Live/Still de la barra de herramientas indique Live y, después, elegir Export (`E`) → WebM para descargar la animación de trazas de 6 segundos**

**Explicación:**
Cada diagrama interactivo se abre en `https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`, y el botón **Export** de la barra de herramientas del visor (atajo `E`) crea archivos listos para compartir en el momento; la disponibilidad depende de la versión del visor, la compatibilidad del navegador y la selección actual. La receta es: (1) abrir el diagrama; (2) comprobar que el control **Live/Still** indique Live, ya que la grabación captura el movimiento a lo largo de las flechas; (3) elegir **Export → WebM** para una publicación animada o **Export → Share Card** para una vista previa estática de 1200×630; (4) publicarla junto con la URL del documento de origen. WebM muestra «Recording 6 seconds of motion…» antes de descargar el archivo y requiere un diagrama con animación de trazas y compatibilidad del navegador con MediaRecorder. SVG es el formato vectorial de tema dual pensado para diapositivas.

</details>

7. ¿Qué afirmación sobre **Route Share Card** del menú Export es correcta?
   - A) Siempre aparece en todos los diagramas e infiere rutas automáticamente entre formas cercanas
   - B) Solo aparece después de que Route Probe (`R`) haya encontrado una ruta entre dos nodos, y sigue únicamente relaciones dirigidas definidas por el autor
   - C) Muestra la accesibilidad ascendente y descendente de un nodo como análisis del radio de impacto
   - D) Solo permite copiar al portapapeles, no descargar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo aparece después de que Route Probe (`R`) haya encontrado una ruta entre dos nodos, y sigue únicamente relaciones dirigidas definidas por el autor**

**Explicación:**
En la tabla del menú Export, Route Share Card es un PNG de 1200×630 (solo descarga) que «aparece únicamente después de que Route Probe (`R`) haya encontrado una ruta entre dos nodos». La sección de límites de certeza añade que «Route Share Card solo sigue las relaciones dirigidas definidas por el autor. Nunca infiere una ruta a partir de la geometría y se niega a exportar una ruta obsoleta o inaccesible». La accesibilidad ascendente/descendente pertenece a Reach Share Card, una tarjeta distinta que tampoco debe presentarse como análisis de impacto, radio de impacto, interrupción o causalidad durante la ejecución.

</details>

8. ¿Qué postura adopta el «límite de certeza» de la hoja de ruta respecto a archivos exportados, como Share Card?
   - A) Las exportaciones son materiales de comunicación (no pruebas de que se haya validado una arquitectura), y Share Card nunca afirma que haya habido validación
   - B) Share Card incluye automáticamente una insignia «validado» y puede servir como prueba de validación
   - C) Las exportaciones son el entregable oficial y sustituyen el HTML publicado
   - D) Reach Share Card mide la propagación de fallos durante la ejecución y se puede incluir directamente en un informe de incidentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Las exportaciones son materiales de comunicación (no pruebas de que se haya validado una arquitectura), y Share Card nunca afirma que haya habido validación**

**Explicación:**
La primera viñeta de la sección dice: «Las exportaciones son materiales de comunicación. No demuestran que se haya validado una arquitectura y no reemplazan el HTML publicado ni la validación del propio autor. Share Card nunca afirma que haya habido validación». Del mismo modo, Reach Share Card solo muestra *accesibilidad definida por el autor*; no debe presentarse como análisis de impacto, radio de impacto, interrupción ni causalidad durante la ejecución.

</details>
