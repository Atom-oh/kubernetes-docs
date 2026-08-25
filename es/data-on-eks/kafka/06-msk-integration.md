# Parte 6: Integración con MSK

> **Versiones compatibles**: Amazon MSK (Provisioned & Serverless), MSK Connect\
> **Última actualización**: July 9, 2026

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y el siguiente entorno:

### Herramientas necesarias

* AWS CLI v2 (para administrar el clúster de MSK y las políticas de IAM)
* kubectl v1.28 o posterior, y un clúster de EKS funcional
* La biblioteca cliente `aws-msk-iam-auth` (para clientes de Kafka que usan autenticación de IAM)
* Un clúster de EKS con External Secrets Operator o IRSA configurado (para la inyección de credenciales)

Las partes anteriores cubrieron cómo ejecutar Kafka por tu cuenta en EKS con Strimzi. Esta parte explica cómo conectar cargas de trabajo de EKS a Amazon MSK, el servicio Kafka totalmente administrado de AWS, y las diferencias frente al enfoque autogestionado de Strimzi. También aclara un punto de confusión frecuente: cómo se relaciona Kafka con Kinesis Data Streams, un servicio de streaming de AWS completamente independiente.

## Amazon MSK frente a Strimzi autogestionado

Ambos enfoques permiten que una carga de trabajo de EKS se comunique con Kafka, pero difieren en dónde se ejecutan realmente los brokers y quién los opera. MSK ejecuta brokers en infraestructura administrada por AWS fuera de tu clúster; Strimzi ejecuta brokers como Pods dentro de tu clúster de EKS.

| Aspecto | Amazon MSK (Provisioned) | Amazon MSK Serverless | Strimzi (autogestionado en EKS) |
| --- | --- | --- | --- |
| **Carga operativa** | AWS se encarga del parcheo de brokers, el reemplazo de hardware y la expansión de almacenamiento | AWS elimina por completo el dimensionamiento de brokers (escalado totalmente automático) | El Operator automatiza las actualizaciones graduales/la reconciliación, pero tú sigues siendo responsable del momento de las actualizaciones, la planificación de capacidad y la respuesta a incidentes |
| **Modelo de costos** | Por hora de broker + almacenamiento (GB-mes) + transferencia de datos | Basado en throughput (por partición, por GB de entrada/salida) | Costo directo de EC2/EBS; normalmente más económico a escala, pero asumes por separado el costo operativo de personal |
| **Autoscaling** | Se admite la expansión automática de almacenamiento; el escalado de brokers es manual/mediante API | Escalado por partición completamente automático; los brokers no se exponen como concepto | Semiautomatizado mediante herramientas como Cruise Control, pero por lo general tú lo activas |
| **Configuración personalizada** | Se puede personalizar la configuración del broker (`server.properties`) | Sin configuración personalizada de brokers; algunas API/funcionalidades están restringidas (por ejemplo, ciertos tipos de ACL y conectores) | Casi todo es ajustable: listeners, interceptors, configuración del controlador KRaft |
| **Compatibilidad de versiones** | AWS mantiene una lista de versiones de Kafka compatibles, que puede ir por detrás de upstream | Versión fija, sin posibilidad de elegir versión | Adopta cualquier versión de Kafka compatible con Strimzi cuando upstream la publique |
| **Multi-tenancy** | Aislamiento mediante políticas de clúster/recursos; la personalización detallada es limitada | El aislamiento de tenants se delega a la implementación interna de AWS | Tenancy detallado mediante namespaces, ACL de `KafkaUser` y listeners personalizados |
| **Adecuación a observabilidad/GitOps** | Se integra mediante exportadores de CloudWatch/Prometheus; la consola de AWS es la superficie principal de administración | Igual | Se adapta naturalmente al mismo pipeline de GitOps/observabilidad (Argo CD, Prometheus Operator) que el resto de la plataforma |

### Por qué elegir MSK

* Tu equipo no tiene experiencia profunda en operaciones de brokers de Kafka, o no quieres que las operaciones de Kafka sean una competencia central
* Ya has invertido considerablemente en herramientas de operaciones nativas de AWS (consola, IAM, CloudWatch)
* El tráfico es difícil de predecir y MSK Serverless te permite eliminar por completo la planificación de capacidad de brokers

### Por qué ejecutar Kafka por tu cuenta en EKS con Strimzi de todos modos (aunque exista MSK)

* Quieres administrar Kafka con las **mismas herramientas y el mismo pipeline de despliegue** que el resto de tu plataforma —otras cargas de trabajo, GitOps, Prometheus/Grafana— sin añadir una segunda superficie de consola/IAM de AWS que operar
* Necesitas **portabilidad** que no esté vinculada a una única nube (on-prem, posibilidad de migración multi-cloud)
* A muy gran escala, administrar EC2/EBS directamente es más rentable que el precio por hora de broker
* Necesitas las funcionalidades más recientes de Kafka (nuevos KIP, interceptors personalizados, opciones específicas de ajuste de KRaft) que MSK aún no ha incorporado

## Conexión a MSK desde EKS

Para que una carga de trabajo de EKS llegue a los brokers de MSK, necesitas tanto una ruta de red como un mecanismo de autenticación.

### Ruta de red

* **Misma VPC**: Si el clúster de EKS y el clúster de MSK se encuentran en la misma VPC, el enrutamiento de subred por sí solo proporciona conectividad; es la opción más sencilla y de menor latencia.
* **VPC diferentes**: Necesitarás VPC peering o un AWS Transit Gateway para conectar las dos VPC. MSK admite acceso público (endpoints de brokers públicos), pero las configuraciones de producción normalmente favorecen la conectividad privada.
* **Security groups**: El security group del clúster de MSK debe permitir explícitamente tráfico entrante desde el security group del nodo de EKS (o del Pod, si los Pods tienen sus propios security groups) en los puertos de broker pertinentes: plaintext 9092, TLS 9094, SASL/SCRAM 9096, IAM 9098. No se permite nada de forma predeterminada.

```bash
# Allow the IAM auth port on the MSK security group from the EKS node security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

### Comparación de mecanismos de autenticación

| Mecanismo | Cómo funciona | Punto de integración de EKS |
| --- | --- | --- |
| **Autenticación de IAM (`AWS_MSK_IAM`)** | El cliente se autentica con una solicitud firmada con SigV4 mediante `AWS_MSK_IAM`, un mecanismo SASL personalizado dedicado (no una extensión de OAUTHBEARER); las políticas de IAM controlan los permisos por topic | Concede al Pod un rol de IAM mediante IRSA; no hay credenciales que distribuir |
| **SASL/SCRAM** | Basado en nombre de usuario/contraseña; las credenciales se almacenan en AWS Secrets Manager | Sincroniza las credenciales SCRAM desde Secrets Manager a un Secret de Kubernetes mediante External Secrets Operator |
| **TLS mutuo (mTLS)** | Certificados de cliente emitidos por AWS Private CA; la identidad se verifica mediante certificado | Monta certificados/claves en los Pods mediante cert-manager o External Secrets Operator |

La autenticación de IAM es la opción más natural para EKS. Con IRSA (IAM Roles for Service Accounts), concedes a un Pod un rol de IAM con alcance limitado y expresas el control de acceso a nivel de topic exclusivamente mediante una política de IAM, sin contraseñas ni certificados que distribuir o rotar.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
        "kafka-cluster:AlterCluster",
        "kafka-cluster:DescribeCluster"
      ],
      "Resource": "arn:aws:kafka:us-east-1:111122223333:cluster/my-msk-cluster/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:*Topic*",
        "kafka-cluster:WriteData",
        "kafka-cluster:ReadData"
      ],
      "Resource": "arn:aws:kafka:us-east-1:111122223333:topic/my-msk-cluster/*/orders"
    }
  ]
}
```

En el lado del cliente, añade la biblioteca `aws-msk-iam-auth` a tu classpath (o el paquete equivalente para tu lenguaje) y, a continuación, configura el cliente de Kafka con:

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

## MSK Connect

MSK Connect es la oferta de Kafka Connect totalmente administrada de AWS. AWS se encarga del aprovisionamiento, el escalado y el parcheo de la infraestructura de workers de Connect; tú registras plugins de conectores (paquetes JAR) cargándolos en S3.

El detalle importante: MSK Connect **no está limitado a clústeres de MSK**. Siempre que tenga conectividad de red con los brokers de bootstrap, MSK Connect también puede ejecutar conectores contra un clúster de Kafka autogestionado que se ejecute en EKS mediante Strimzi.

```bash
# Upload a custom connector plugin to S3 and register it as an MSK Connect custom plugin
aws kafkaconnect create-custom-plugin \
  --name debezium-postgres-plugin \
  --content-type ZIP \
  --location s3Location='{bucketArn=arn:aws:s3:::my-connect-plugins,fileKey=debezium-postgres-2.7.zip}'
```

| Aspecto | MSK Connect | Strimzi `KafkaConnect` (operado por ti en EKS) |
| --- | --- | --- |
| **Carga operativa** | AWS administra la infraestructura de workers; tú solo administras la configuración del conector | Tú mismo administras el escalado de Pods de workers, la monitorización y el ajuste de recursos |
| **Flexibilidad** | Limitado al framework de conectores que AWS admite | Libertad total para conectores arbitrarios, SMT personalizados (Single Message Transforms), sidecars |
| **Portabilidad** | Servicio exclusivo de AWS, difícil de trasladar a otro lugar | Portable tal cual a cualquier otro clúster de Kubernetes |
| **Observabilidad** | Estado del conector mediante CloudWatch Logs/Metrics | Se integra en el mismo pipeline de Prometheus/Grafana que el resto de tus cargas de trabajo de EKS |

## Comparación y conexión con Kinesis Data Streams

Kinesis Data Streams y Kafka se mencionan a menudo juntos, pero **no son protocolos compatibles**. Kinesis es un servicio de streaming nativo de AWS con su propia API/SDK, y no entiende el protocolo de productores/consumidores de Kafka. El hecho de que MSK se describa como «compatible con Kafka» no significa que interopere con Kinesis: MSK es una implementación administrada del protocolo Apache Kafka, y Kinesis es un servicio completamente independiente.

| Aspecto | Apache Kafka (MSK/Strimzi) | Kinesis Data Streams |
| --- | --- | --- |
| **Protocolo** | Protocolo Kafka de código abierto, compatible con un amplio ecosistema de clientes/herramientas | API propietaria de AWS, no compatible con clientes de Kafka |
| **Unidad de escalado** | Particiones (definidas al crear el topic; se pueden reparticionar) | Shards (unidades de capacidad de lectura/escritura, ajustadas mediante división/fusión) |
| **Complejidad operativa** | Requiere operar brokers/controllers (MSK delega esto en AWS) | Totalmente administrado, sin concepto de servidor |
| **Integración con servicios de AWS** | Indirecta, mediante conectores (Kafka Connect, MSK Connect) | Integración nativa y directa con triggers de Lambda, Firehose, Kinesis Data Analytics |
| **Ecosistema** | Amplio ecosistema de código abierto: Kafka Streams, ksqlDB, Flink, Debezium | Ecosistema más pequeño, centrado en servicios de AWS, pero más sencillo de integrar |
| **Retención** | Efectivamente ilimitada (solo pagas por almacenamiento; 7 días de forma predeterminada) | 24 horas de forma predeterminada, ampliable hasta 365 días (con un costo creciente) |

### El patrón de conexión real

Si necesitas conectar realmente Kafka y Kinesis, para una migración o para crear un puente con consumidores de Kinesis heredados, el patrón práctico es un **conector de Kinesis que se ejecuta bajo Kafka Connect (o MSK Connect)**, no ninguna compatibilidad de protocolo integrada.

* **Conector Kinesis Sink**: lee mensajes de un topic de Kafka y los escribe en un stream de Kinesis; es útil para enviar la salida de un pipeline basado en Kafka al ecosistema de consumo de Kinesis (Lambda, Firehose)
* **Conector Kinesis Source**: lee registros de un stream de Kinesis y los escribe en un topic de Kafka; es útil para mantener los productores existentes de Kinesis mientras migras gradualmente los consumidores a Kafka

Estos conectores se pueden desplegar en MSK Connect o ejecutar directamente en EKS mediante los CR `KafkaConnect`/`KafkaConnector` de Strimzi; las mismas diferencias entre MSK Connect y Strimzi de la sección anterior también se aplican aquí.

## Guía de decisión

Usa esta lista de verificación para acotar la elección entre Strimzi autogestionado, MSK Provisioned, MSK Serverless y Kinesis.

* **¿Tu equipo tiene experiencia en operaciones de Kafka y necesita ajuste detallado/configuración personalizada?** → Sí: Strimzi (autogestionado en EKS) / No: considera MSK
* **¿La portabilidad multi-cloud/on-prem es un requisito estricto?** → Sí: Strimzi / No: vale la pena evaluar MSK
* **¿El tráfico es impredecible o variable, y quieres eliminar por completo la planificación de capacidad de brokers?** → Sí: MSK Serverless / No: MSK Provisioned o Strimzi
* **¿Ya has invertido profundamente en procesamiento de eventos nativo de AWS (Lambda, Firehose) y no necesitas el ecosistema de Kafka (Kafka Streams, ksqlDB, etc.)?** → Sí: evalúa Kinesis Data Streams / No: quédate con Kafka (MSK/Strimzi)
* **¿Quieres administrar Kafka mediante el mismo pipeline de GitOps que el resto de tu plataforma de EKS, sin añadir una superficie de consola/IAM de AWS?** → Sí: Strimzi / No: MSK

En la práctica, la respuesta suele ser «ambos»: iniciar un servicio nuevo en MSK Serverless por rapidez y migrar después a Strimzi cuando necesites ajustes personalizados es una trayectoria común.

## Próximos pasos

Tanto si ejecutas MSK como Strimzi, necesitas visibilidad continua de las métricas de brokers y del consumer lag para saber que el clúster está en buen estado. Ese es el tema de la [Parte 7: Monitorización](./07-monitoring.md).

[Volver a la página principal](./README.md)

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, prueba el [Cuestionario de topics](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md).
