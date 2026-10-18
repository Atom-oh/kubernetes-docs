# Hoja de ruta de la guía

> **Última actualización**: 16 de octubre de 2026

Esta guía cuenta una historia continua: desde el kernel de Linux, pasando por contenedores, Kubernetes, Amazon EKS, redes, service mesh, almacenamiento, bases de datos, canalizaciones de datos e IA/ML, además de las disciplinas transversales de seguridad, GitOps, ingeniería de plataformas, registros de contenedores, observabilidad y operaciones. Esta página ofrece el mapa y las rutas recomendadas para recorrerla.

![Mapa del flujo de aprendizaje de los quince dominios de la guía: desde los fundamentos (Linux/Container), pasando por la orquestación (Kubernetes/EKS), la conectividad (Networking/Service Mesh), la persistencia (Storage/Database) y los datos e IA (Data Pipeline/AI-ML), hasta las preocupaciones transversales (Security/GitOps/Platform/Container Registry/Observability/Operations).](.gitbook/assets/en-roadmap-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-roadmap-0.html)

## Mapa de dominios

| Capa | Dominio | Empieza aquí | En una frase |
|-------|--------|-----------|-----------|
| Fundamentos | Linux y Container | [Conceptos básicos de Linux](basics/01-linux-basics.md) | Kernel, espacios de nombres, cgroups: qué es realmente un contenedor |
| Orquestación | Conceptos fundamentales de Kubernetes | [Introducción a Kubernetes](basics/04-kubernetes-introduction.md) | Cargas de trabajo, planificación y escalado automático: Kubernetes en sí |
| Orquestación | Amazon EKS | [Introducción a EKS](eks/01-eks-introduction.md) | Desde la creación de clústeres hasta Hybrid Nodes y Auto Mode |
| Conectividad | Networking | [Fundamentos de redes](basics/06-network-fundamentals-part1.md) | 25 protocolos, hasta llegar a CNI (Cilium/Calico) |
| Conectividad | Service Mesh | [Istio](service-mesh/istio/README.md) | Istio/Linkerd/Cilium Mesh, con mediciones de latencia mTLS |
| Persistencia | Storage | [Resumen de almacenamiento](storage/README.md) | EBS gp2 frente a gp3, medido con fio |
| Persistencia | Database | [Resumen de bases de datos](database/README.md) | El panorama de operadores y una prueba comparativa de ClickHouse con 100 millones de filas |
| Datos e IA | Data Pipeline | [Resumen de Data on EKS](data-on-eks/README.md) | Análisis detallados de Kafka, Spark, Airflow y Flink, con un registro de una ejecución de la prueba comparativa de Kafka |
| Datos e IA | AI/ML | [Cargas de trabajo de AI/ML](ai-ml/01-ai-ml-workloads.md) | vLLM, Ray, Kubeflow y MLflow en EKS |
| Transversales | Seguridad y políticas | [Kyverno](security/01-kyverno-policy-management.md) | Autenticación/autorización, políticas, seguridad en tiempo de ejecución y cadena de suministro |
| Transversales | GitOps | [GitOps](gitops/README.md) | ArgoCD, Flux y entrega progresiva |
| Transversales | Ingeniería de plataformas | [Resumen](platform-engineering/00-platform-engineering-overview.md) | ACK, KRO, Crossplane y Backstage |
| Transversales | Container Registry | [Resumen](container-registry/README.md) | ECR, Harbor y cadena de suministro de imágenes |
| Transversales | Observability | [Resumen](observability/README.md) | Métricas, registros, trazas y pilas de alertas |
| Transversales | Guía de operaciones | [Guía de operaciones](ops/README.md) | Planificación de capacidad, FinOps, actualizaciones y un [manual de solución de problemas](ops/16-troubleshooting-playbook.md) basado en síntomas |

## Serie de pruebas con resultados medidos

Estos documentos presentan resultados de ejecuciones previas en recursos de AWS. Antes de usarlos para planificar la capacidad actual, comprueba el entorno, el número de repeticiones, el estado de la caché, si están disponibles los registros originales y las limitaciones; después, vuelve a medir:

- [Istio sidecar frente a ambient, mediciones](service-mesh/istio/comparison/03-sidecar-vs-ambient.md): latencia P50/P99 por plano de datos mTLS y tasas de 503 durante los rollouts
- [Prueba comparativa medida de EBS gp2 frente a gp3](storage/01-ebs-gp2-gp3-benchmark.md): una diferencia de 10 veces en IOPS con la misma capacidad de 100 GiB y el límite de créditos de ráfaga de gp2
- [Prueba comparativa medida de ClickHouse en EKS](database/01-clickhouse-on-eks.md): rendimiento de ingesta de 100 millones de filas, relaciones de compresión y latencia de consultas
- [Prueba comparativa medida de Kafka en EKS](data-on-eks/kafka/09-kafka-benchmark.md): registros de una sola ejecución de 134.74 MiB/s con RF3/acks=all y 337.81 MiB/s con RF1/acks=1 (no se confirmó como límite sostenido de RF3), p99 según la configuración de acks y una caída registrada del 44.49% en el rendimiento del productor mientras se consumían los mensajes reproducidos
- [Prueba comparativa de red de Pods](networking/06-pod-network-benchmark.md): la secuencia de RTT de 0.040 → 0.339 → 0.544 ms (mismo nodo → misma AZ → entre AZ), un límite de 4.96 Gbps para un solo flujo sin importar la zona de disponibilidad frente a 9.94 Gbps con 8 flujos, y la amplificación de 10 consultas/8 NXDOMAIN de `ndots:5`

## Compartir un diagrama: exportaciones para LinkedIn y presentaciones

Los diagramas interactivos de esta guía se abren en `https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`, y el botón **Export** de la barra de herramientas del visor (atajo `E`) genera al momento archivos listos para compartir. Los elementos disponibles dependen de la versión del visor, las capacidades del navegador y el estado de selección.

### Opciones del menú Export

| Grupo | Elemento del menú | Resultado | Uso |
|-------|-----------|--------|-----------|
| Compartir | **Share Card** / **Copy Share Card** | PNG de 1200×630 (descarga / portapapeles) | Vistas previas de enlaces de LinkedIn y X, archivos README y notas de versión |
| Compartir | **Route Share Card** | PNG de 1200×630 (solo descarga) | Aparece solo después de que Route Probe (`R`) haya encontrado una ruta entre dos nodos |
| Compartir | **Reach Share Card** | PNG de 1200×630 (solo descarga) | Aparece solo después de trazar la accesibilidad ascendente/descendente de un nodo desde su Semantic Passport |
| Compartir | **Copy diagram** | PNG del diagrama completo al portapapeles | Pegar directamente en diapositivas o documentos |
| Imagen | **PNG** / **JPEG** / **WebP** | Imagen rasterizada del diagrama completo | PNG cuando se requiere compresión sin pérdidas; JPEG/WebP cuando importa el tamaño |
| Vector y movimiento | **SVG** | Vector con tema dual (claro y oscuro) | Diapositivas que se mantienen nítidas con cualquier nivel de zoom |
| Vector y movimiento | **WebM** | Grabación de 6 segundos de la animación de trazas | Publicación de LinkedIn donde el flujo realmente se mueve en el feed |

Las exportaciones eliminan todo el estado del visor (el panel Guide, Lens, el buscador, el foco, la ruta, la historia, la posición de la cámara, el radar, el modo de presentación y las superposiciones temporales), de modo que solo queda el diagrama. Share Card conserva el tema y el ajuste visual actuales y siempre incluye el diagrama completo, sin recortarlo. La grabación WebM requiere un diagrama con animación de trazas y compatibilidad del navegador con MediaRecorder; los navegadores no compatibles lo indican en el menú.

### Receta de LinkedIn en 30 segundos

1. **Abre el diagrama**: haz clic en el enlace «Open full screen ↗» debajo de cualquier diagrama incrustado (en GitBook, «🔍 View interactive diagram»).
2. **Comprueba que la animación de la traza esté activa**: el control **Live/Still** de la barra de herramientas debe indicar Live. La grabación captura el movimiento a lo largo de las flechas. ¿Vas a ensayar una presentación? **Presentation stage** (`F`) ocupa toda el área visible del navegador con el diagrama.
3. Elige **Export → WebM** para una publicación animada o **Export → Share Card** para una vista previa estática de 1200×630. WebM muestra «Recording 6 seconds of motion…» y después se descarga el archivo.
4. **Publica**: comprueba los formatos que admite actualmente la plataforma de destino y convierte WebM si hace falta. Sube Share Card como imagen e incluye la URL del documento de origen. Para enlazar a un nodo, una ruta o un momento específico de una historia, usa **Copy link** en Semantic Passport o Route Probe, o **Copy moment** en Story Beat (solo aparece en diagramas con capítulos de historia definidos), y coloca el enlace profundo en un comentario o diapositiva.

### Límites de interpretación

- Las exportaciones son **materiales de comunicación**. No demuestran que se haya validado una arquitectura y no reemplazan el HTML publicado ni la validación del autor. Share Card nunca afirma que se haya realizado una validación.
- Route Share Card solo sigue **relaciones dirigidas definidas por el autor**. Nunca infiere una ruta a partir de la geometría y se niega a exportar una ruta obsoleta o inaccesible.
- Reach Share Card muestra *accesibilidad definida por el autor*. No la presentes como análisis de impacto, radio de impacto, interrupción o causalidad en tiempo de ejecución.

## Rutas recomendadas

### ① Incorporación a la infraestructura: «de los contenedores a EKS»

Conceptos básicos de Linux → Tecnología de contenedores → Introducción a Kubernetes → Conceptos fundamentales (Pods/servicios/almacenamiento/configuración) → Creación de clústeres de EKS → Fundamentos de redes. Comprueba lo aprendido con el cuestionario de cada documento y realiza en paralelo los [laboratorios](labs/README.md).

### ② Plataforma / SRE: «un clúster que puedes operar»

Operaciones de EKS (actualizaciones/solución de problemas/resiliencia) → Networking (VPC CNI, Cilium) → guía comparativa de Service Mesh → Seguridad y políticas → pila de observabilidad → GitOps → planificación de capacidad y FinOps en la Guía de operaciones. La serie de pruebas comparativas aporta la evidencia en la que se apoya esta ruta.

### ③ Plataforma de datos e IA: «el mundo de las cargas con estado»

Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow). Si necesitas GPU y control de la planificación, añade las secciones Custom Scheduler de Kubernetes Core Concepts.

## Lectura con LLM

La guía ofrece un índice y texto fuente con el formato propuesto llms.txt. La herramienta de IA sigue necesitando búsqueda web o una conexión MCP; proporcionar una URL no garantiza que lea o indexe automáticamente todo el libro. Consulta [Lectura con LLM](llm-guide.md) para ver los endpoints y ejemplos de uso.
