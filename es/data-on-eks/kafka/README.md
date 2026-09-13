# Kafka en EKS en profundidad

## Descripción general

Esta guía utiliza Strimzi Operator como una opción de Kafka autogestionada en EKS. El Operator reconcilia Pods, almacenamiento, listeners, certificados y actualizaciones; no elimina la responsabilidad sobre los datos, la disponibilidad ni la política de seguridad. La parte 6 compara alternativas gestionadas como Amazon MSK.

> **Última actualización**: September 12, 2026. Strimzi 1.2.0 / Kafka 4.3.1.
> **Requisito de actualización**: Strimzi 1.0 y versiones posteriores solo admiten la API `v1` de las CRD. Convierta los recursos existentes `v1beta2` / `v1beta1` / `v1alpha1` y prepare las CRD mediante el procedimiento oficial de migración antes de actualizar el Operator. Cambiar únicamente los números de versión no constituye un plan de actualización.

Strimzi 1.2.0 admite Kafka 4.2.0, 4.2.1, 4.3.0 y 4.3.1, con 4.3.1 como versión predeterminada. Esta guía fija una combinación compatible; compruebe también la distribución, la versión de Kubernetes y la ruta de actualización antes de la instalación.

## Conceptos fundamentales de arquitectura

Los brokers almacenan réplicas de las particiones de los temas. Los grupos de KafkaConsumer distribuyen las particiones, y un mismo miembro puede encargarse de varias de ellas. Un quórum de controladores independiente gestiona el registro Raft de metadatos.

KRaft llegó como acceso anticipado en la versión 2.8 y estuvo listo para producción en la 3.3; Kafka 4.0 eliminó el modo ZooKeeper. Los controladores y los brokers pueden desempeñar roles dedicados. Eliminar ZooKeeper no elimina las operaciones de controladores, almacenamiento ni recuperación.

Los usuarios declaran recursos personalizados como Kafka y KafkaNodePool; Strimzi reconcilia Pods, PVC, Services y Secrets. El siguiente diagrama es un esquema simplificado de relaciones, no una especificación de despliegue con cantidades de réplicas para alta disponibilidad.

![Reconciliación simplificada de Kafka/KafkaNodePool con Pods/PVC mediante Strimzi; las cantidades reales de réplicas de brokers y controladores requieren un diseño independiente](../../.gitbook/assets/en-data-on-eks-kafka-readme-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-kafka-readme-0.html)

## Índice de la guía en profundidad

**[1. Fundamentos de Kafka](01-kafka-fundamentals.md)**
- Brokers y estructura de temas y particiones
- Garantías de replicación y durabilidad
- Grupos de consumidores y gestión de offsets
- Arquitectura del quórum de controladores KRaft

**[2. Strimzi Operator](02-strimzi-operator.md)**
- Instalación y configuración de Strimzi
- Las CRD `Kafka` y `KafkaNodePool` en detalle
- Despliegue de un clúster Kafka en EKS

**[3. Operaciones de Kafka](03-kafka-operations.md)**
- Diseño del almacenamiento con EBS/gp3
- Estrategias de escalado de brokers
- Reequilibrado de particiones con Cruise Control
- Actualizaciones graduales con comprobaciones de compatibilidad y disponibilidad

**[4. Registro de esquemas](04-schema-registry.md)**
- Diseño de esquemas Avro/Protobuf
- Karapace frente a Apicurio Registry
- Estrategias de compatibilidad: BACKWARD/FORWARD/FULL

**[5. Kafka Connect y MirrorMaker](05-kafka-connect-mirrormaker.md)**
- Despliegue de Kafka Connect y configuración de conectores
- Operación de conectores de origen y destino
- Recuperación ante desastres y replicación entre regiones con MirrorMaker2

**[6. Integración con MSK](06-msk-integration.md)**
- Amazon MSK frente a Strimzi autogestionado
- Uso de MSK Connect
- Integración y comparación con Kinesis Data Streams

**[7. Monitorización](07-monitoring.md)**
- Recopilación de métricas de brokers con Prometheus/Grafana
- Monitorización del retraso de los consumidores
- Escalado automático de consumidores con KEDA

**[8. Buenas prácticas](08-best-practices.md)**
- Estrategias para el número de particiones y el diseño de claves
- Ajuste del rendimiento de productores y consumidores
- Seguridad con mTLS/SASL
- Optimización de costes de almacenamiento e instancias

**[9. Benchmark medido de Kafka](09-kafka-benchmark.md)**
- Límite de ingesta medido con RF3 frente a RF1 en un clúster KRaft de 3 brokers con volúmenes gp3
- Compromisos entre rendimiento y latencia p99 con acks=0/1/all
- Rendimiento y coste de CPU según el códec de compresión y el tamaño del registro
- Cómo afectan los consumidores en frío y las cargas mixtas al rendimiento de los productores

## Referencias

- [Versión Strimzi 1.2.0](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.2.0)

- [Documentación de Strimzi](https://strimzi.io/docs/operators/1.2.0/overview.html)
- [Documentación de Apache Kafka](https://kafka.apache.org/43/design/design/)
- [Guía de operaciones de KRaft](https://kafka.apache.org/43/operations/kraft/)
- [Proyecto AWS Data on EKS](https://awslabs.github.io/data-on-eks/)

## Cuestionario

Para evaluar lo aprendido en esta sección, realice el [Cuestionario de fundamentos de Kafka](../../quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md). Para comprobar si puede convertir las cifras del benchmark en decisiones de diseño, realice también el [Cuestionario del benchmark medido de Kafka](../../quizzes/data-on-eks/kafka/09-kafka-benchmark-quiz.md).
