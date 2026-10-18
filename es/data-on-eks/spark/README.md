# Análisis detallado de Spark en EKS

> **Base de revisión**: Apache Spark 4.2.0, Kubernetes 1.34 o posterior\
> **Última revisión**: 12 de septiembre de 2026

Apache Spark ejecuta cargas de trabajo distribuidas por lotes, SQL, streaming y
otros tipos. La compatibilidad nativa con Kubernetes se incorporó en Spark 2.3; la
compatibilidad con el modo cliente llegó en la versión 2.4. Spark 4.2.0 especifica
Kubernetes **1.34 o posterior** como requisito previo.
Usa una versión de kubectl compatible con la versión real de EKS, no un mínimo fijo obsoleto.

Spark puede usar la capacidad y el plano de control de Kubernetes que ya operas,
sin un master independiente de Spark Standalone ni un YARN ResourceManager.
Aun así, debes operar o aprovisionar la capacidad de los nodos, las imágenes, la
identidad, la red, el almacenamiento y la observabilidad. YARN ResourceManager y
NodeManager son componentes de YARN, no demonios específicos de Spark.

## Responsabilidades de ejecución

En el **modo de implementación en clúster**, el cliente que envía el trabajo solicita
a la API de Kubernetes que cree el pod del driver. La admisión y la planificación de
Kubernetes, junto con los kubelets de los nodos, gestionan la ubicación y el inicio
del pod. El driver de Spark solicita pods de executor y coordina las etapas y tareas
de Spark; no sustituye al scheduler de Kubernetes.

Los executors se registran y se comunican directamente con el driver para el trabajo
de Spark. Kubernetes sigue gestionando el ciclo de vida de sus pods. En el **modo
cliente**, el driver se ejecuta junto con la aplicación que envía el trabajo, dentro
de un pod o en otro host, y debe ser accesible para los executors. Ambos modos admiten
aplicaciones Spark.

![Envío de Spark en modo clúster a través de la API de Kubernetes; la ubicación e inicio de los pods se muestran por separado de la coordinación de tareas de Spark que realiza el driver.](../../.gitbook/assets/en-data-on-eks-spark-readme-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-spark-readme-0.html)

## Capítulos

1. [Fundamentos de Spark en Kubernetes](01-spark-fundamentals.md): envío en modo clúster o cliente, asignación de recursos, asignación dinámica y condiciones de desmantelamiento.
2. [Spark Operator](02-spark-operator.md): distingue los operadores de Apache y Kubeflow, sus API, el ciclo de vida de los trabajos, el envío y la supervisión.
3. [EMR en EKS](03-emr-on-eks.md): clústeres virtuales, envío de trabajos e identidades de ejecución; distingue las funciones del entorno de ejecución administrado de las operaciones de capacidad de EKS.
4. [Rendimiento y costos](04-performance-tuning.md): cuellos de botella de shuffle, almacenamiento, CPU y memoria; capacidades de nodo adecuadas, recuperación de Spot y escalado de executors frente al escalado de nodos.
5. [Prácticas recomendadas y seguridad](05-best-practices.md): identidad de Kubernetes y AWS, acceso a datos, registros e historial de eventos, métricas, política de red y recuperación.

La **asignación dinámica de recursos** de Spark ajusta los executors dentro de una
aplicación. Es distinta de la asignación dinámica de recursos de Kubernetes para
dispositivos y del escalado automático de nodos. El desmantelamiento puede reducir
el recálculo, pero no garantiza que todos los bloques sobrevivan a una terminación
forzada.

## Referencias

- [Spark 4.2.0 en Kubernetes](https://spark.apache.org/docs/4.2.0/running-on-kubernetes.html)
- [Configuración de Spark 4.2.0](https://spark.apache.org/docs/4.2.0/configuration.html)
- [Alternativas de asignación dinámica de Spark 4.2.0](https://spark.apache.org/docs/4.2.0/job-scheduling.html#dynamic-resource-allocation)
- [Asignación de recursos del driver](https://github.com/apache/spark/blob/v4.2.0/resource-managers/kubernetes/core/src/main/scala/org/apache/spark/deploy/k8s/features/BasicDriverFeatureStep.scala)
- [Recursos de los executors y hook de desmantelamiento](https://github.com/apache/spark/blob/v4.2.0/resource-managers/kubernetes/core/src/main/scala/org/apache/spark/deploy/k8s/features/BasicExecutorFeatureStep.scala)
- [Script oficial de desmantelamiento](https://github.com/apache/spark/blob/v4.2.0/resource-managers/kubernetes/docker/src/main/dockerfiles/spark/decom.sh)
- [Etiquetas oficiales de imágenes de Spark](https://github.com/docker-library/official-images/blob/master/library/spark)

- [Apache Spark Kubernetes Operator](https://github.com/apache/spark-kubernetes-operator)
- [Kubeflow Spark Operator](https://github.com/kubeflow/spark-operator)
- [Conceptos de EMR en EKS](https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-concepts.html)

## Cuestionario

[Cuestionario sobre los fundamentos de Spark](../../quizzes/data-on-eks/spark/01-spark-fundamentals-quiz.md)
