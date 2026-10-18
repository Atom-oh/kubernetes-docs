# Datos en EKS

> **Última actualización**: 12 de septiembre de 2026

## Descripción general

Esta sección trata sobre la operación de Kafka, Spark, Airflow y Flink en Amazon EKS y su conexión con los servicios administrados de AWS. Los charts de Helm, los operadores de Kubernetes y los ejecutores ofrecen distintos modelos de implementación, observabilidad, escalado y responsabilidades.

Compara la operación autogestionada con opciones administradas como Amazon MSK, EMR y MWAA según la capacidad operativa, las funciones requeridas, la disponibilidad y el costo total. EMR on EKS gestiona la ejecución de los trabajos, pero deja la responsabilidad del clúster EKS subyacente en tus manos. SageMaker Unified Studio es un espacio de trabajo administrado de datos e IA con integración de gobernanza, no software que se implemente en EKS.

## Categorías de cargas de trabajo de datos

Distingue cuatro categorías de cargas de trabajo de ejecución y el área de gobernanza administrada que las conecta. Una herramienta puede cubrir varios roles.

| Categoría | Problema que resuelve | Herramienta representativa | Cobertura de Data on EKS |
|----------|--------------------|----------------------|------------------------|
| **Transmisión de eventos** | Publicar eventos y suscribirse a ellos en tiempo real, conectando de forma fiable la comunicación asíncrona entre sistemas | Apache Kafka | Disponible: [Kafka on EKS](kafka/README.md) |
| **Procesamiento por lotes y análisis** | Procesamiento distribuido de grandes conjuntos de datos para ETL, agregación y canalizaciones de ML | Apache Spark | Disponible: [Spark on EKS](spark/README.md) |
| **Orquestación** | Definir dependencias y programaciones entre trabajos de datos y gestionar su ejecución | Apache Airflow | Disponible: [Airflow on EKS](airflow/README.md) |
| **Procesamiento de flujos** | Realizar agregaciones, transformaciones y cálculos con estado en tiempo real sobre datos que llegan en flujo continuo | Apache Flink | Disponible: [Flink on EKS](flink/README.md) |
| **Espacio de trabajo de datos e IA con gobernanza** | Compartir activos de datos, perfiles de proyectos, herramientas y membresías dentro de un límite administrado | SageMaker Unified Studio | Disponible: [Gobernanza de Unified Studio](sagemaker-unified-studio/README.md) |

![Airflow coordina trabajos de Spark, mientras que Spark y Flink leen y procesan eventos de Kafka. Esto no representa a Airflow programando los brokers de Kafka.](../.gitbook/assets/en-data-on-eks-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-readme-0.html)

## Por qué ejecutarlos en EKS

Evalúa estas oportunidades y limitaciones al considerar la operación directa en EKS:

- **Operaciones y observabilidad unificadas**: Reutiliza las prácticas existentes de `kubectl`, GitOps y Prometheus/Grafana. La calidad de los datos, el linaje, el rendimiento de las consultas y el retraso de los consumidores siguen requiriendo observabilidad específica del dominio.
- **Escalado automático**: [Karpenter](../autoscaling/02-karpenter.md) ajusta la capacidad de los nodos; HPA/KEDA o los escaladores automáticos específicos del motor ajustan los workers/trabajos compatibles. Los cambios en los brokers de Kafka también requieren revisar la reasignación de particiones, el cuórum, el almacenamiento y la compatibilidad con el Operator.
- **Eficiencia de costos**: Aplica Spot y el empaquetado eficiente de cargas cuando los requisitos de reinicio, checkpoint y replicación lo permitan. Evalúa la [optimización de costos de EKS](../eks/07-eks-cost-optimization.md) junto con los costos de almacenamiento, redes y operación; no la apliques de manera uniforme a los brokers y los trabajos con estado.
- **Multitenencia**: Los espacios de nombres, ResourceQuotas y NetworkPolicies son componentes de aislamiento. Valida los permisos reales sobre los datos, los niveles de confianza, la autenticación, el almacenamiento y las redes; un espacio de nombres por sí solo no proporciona un aislamiento completo entre inquilinos.

Este enfoque también tiene contrapartidas: tu equipo asume directamente la gestión de los operadores, el diseño del almacenamiento y la estrategia de actualización. Los análisis detallados que siguen explican esas ventajas y costes para cada herramienta.

## Contenido disponible actualmente

- [Anatomía de una canalización de datos moderna](01-data-pipeline-anatomy.md): Un mapa introductorio de toda la canalización en cinco capas, desde las fuentes hasta el consumo, que muestra qué capa cubre cada análisis detallado.
- [Kafka on EKS](kafka/README.md): Un análisis detallado en 8 partes sobre la implementación y operación de Apache Kafka en EKS con el Strimzi Operator, además de una medición de referencia en la Parte 9 del límite de ingesta de un clúster RF3 de 3 brokers en gp3.
- [Spark on EKS](spark/README.md): Un análisis detallado en 5 partes sobre los fundamentos de Spark en Kubernetes, el panorama de Spark Operator, Amazon EMR on EKS y el ajuste del rendimiento y los costos.
- [Airflow on EKS](airflow/README.md): Un análisis detallado en 5 partes sobre la arquitectura de Airflow 3, la implementación basada en Helm y la selección del ejecutor, los patrones de DAG con KubernetesPodOperator y la integración con Amazon MWAA.
- [Flink on EKS](flink/README.md): Un análisis detallado en 4 partes sobre la arquitectura de Flink en Kubernetes, el Flink Kubernetes Operator, el estado y los checkpoints, y las operaciones y la alta disponibilidad.
- [Gobernanza de SageMaker Unified Studio](sagemaker-unified-studio/README.md): Dominios, perfiles de proyectos, proyectos, activos de catálogo, membresías y ciclo de vida de eliminación.

## Próximos pasos

1. [Kafka on EKS](kafka/README.md): Análisis detallado de Kafka basado en Strimzi
2. [Spark on EKS](spark/README.md): Análisis detallado de Spark Operator y EMR on EKS
3. [Airflow on EKS](airflow/README.md): Análisis detallado de la implementación de Airflow basada en Helm y los patrones de DAG
4. [Flink on EKS](flink/README.md): Análisis detallado de Flink Kubernetes Operator y los patrones de streaming
5. [Gobernanza de SageMaker Unified Studio](sagemaker-unified-studio/README.md): Guía de gobernanza que conecta un espacio de trabajo administrado de datos e IA con las canalizaciones de EKS
