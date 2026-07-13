# Parte 6: Integración con MSK

> **Versiones compatibles**: Amazon MSK (Provisioned & Serverless), MSK Connect\
> **Última actualización**: July 9, 2026

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Herramientas requeridas

* AWS CLI v2 (para gestionar el cluster de MSK y las políticas IAM)
* kubectl v1.28 o posterior, un cluster de EKS en funcionamiento
* La biblioteca cliente `aws-msk-iam-auth` (para clientes Kafka que usan autenticación IAM)
* Un cluster de EKS con External Secrets Operator o IRSA configurado (para inyección de credenciales)

Las partes anteriores cubrieron cómo ejecutar Kafka por tu cuenta en EKS con Strimzi. Esta parte cubre cómo conectar workloads de EKS a Amazon MSK — el servicio Kafka completamente gestionado de AWS — y las compensaciones frente al enfoque Strimzi autogestionado. También aclara un punto común de confusión: cómo se relaciona Kafka con Kinesis Data Streams, un servicio de streaming de AWS completamente independiente.

## Amazon MSK vs. Strimzi autogestionado

Ambos enfoques permiten que un workload de EKS se comunique con Kafka, pero difieren en dónde se ejecutan realmente los brokers y quién los opera. MSK ejecuta brokers en infraestructura gestionada por AWS fuera de tu cluster; Strimzi ejecuta brokers como Pods dentro de tu cluster de EKS.

| Aspecto | Amazon MSK (Provisioned) | Amazon MSK Serverless | Strimzi (autogestionado en EKS) |
| --- | --- | --- | --- |
| **Carga operativa** | AWS se encarga del parcheo de brokers, el reemplazo de hardware y la expansión de storage | AWS elimina por completo el dimensionamiento de brokers (auto-scaling completo) | El Operator automatiza rolling upgrades/reconciliation, pero sigues siendo responsable del momento de las actualizaciones, la planificación de capacidad y la respuesta a incidentes |
| **Modelo de costos** | Por hora de broker + storage (GB-mes) + transferencia de datos | Basado en throughput (por partition, por GB de entrada/salida) | Costo directo de EC2/EBS — normalmente más barato a escala, pero asumes por separado el costo del equipo operativo |
| **Autoscaling** | Se admite auto-expansión de storage; el escalado de brokers es manual/impulsado por API | Escalado por partition completamente automático; los brokers no se exponen como concepto | Semiautomatizado mediante herramientas como Cruise Control, pero generalmente tú lo activas |
| **Configuración personalizada** | La configuración del broker (`server.properties`) se puede personalizar | Sin configuración personalizada de broker; algunas APIs/funcionalidades están restringidas (p. ej., ciertos tipos de ACL, tipos de connectors) | Casi todo es ajustable — listeners, interceptors, configuración de controladores KRaft |
| **Soporte de versiones** | AWS selecciona una lista de versiones de Kafka compatibles, que puede ir por detrás de upstream | Versión fija, sin opción de elegir versión | Adopta cualquier versión de Kafka que Strimzi admita, tan pronto como upstream la publique |
| **Multi-tenancy** | Aislamiento mediante políticas de cluster/recurso; la personalización detallada es limitada | El aislamiento de tenants se delega a la implementación interna de AWS | Tenancy detallada mediante namespaces, ACLs de `KafkaUser` y listeners personalizados |
| **Observabilidad/encaje con GitOps** | Se integra mediante CloudWatch/Prometheus exporters; la consola de AWS es la superficie principal de gestión | Igual | Encaja de forma natural en el mismo pipeline de GitOps/observabilidad (Argo CD, Prometheus Operator) que el resto de la plataforma |

### Por qué elegir MSK

* Tu equipo no tiene experiencia profunda en operaciones de brokers Kafka, o no quieres que las operaciones de Kafka sean una competencia central
* Ya tienes una inversión fuerte en tooling de operaciones nativo de AWS (consola, IAM, CloudWatch)
* El tráfico es difícil de predecir, y MSK Serverless te permite eliminar por completo la planificación de capacidad de brokers

### Por qué ejecutar Kafka por tu cuenta en EKS con Strimzi de todos modos (aunque MSK exista)

* Quieres gestionar Kafka con las **mismas herramientas y el mismo pipeline de despliegue** que el resto de tu plataforma — otros workloads, GitOps, Prometheus/Grafana — sin añadir una segunda superficie de consola de AWS/IAM para operar
* Necesitas **portabilidad** que no esté atada a un único cloud (on-prem, potencial de migración multi-cloud)
* A muy gran escala, gestionar EC2/EBS directamente es más eficiente en costos que el pricing por hora de broker
* Necesitas las funcionalidades más recientes de Kafka (nuevos KIPs, interceptors personalizados, opciones específicas de ajuste de KRaft) que MSK aún no ha incorporado

## Conectarse a MSK desde EKS

Para que un workload de EKS alcance brokers de MSK, necesitas tanto una ruta de red como un mecanismo de autenticación.

### Ruta de red

* **Misma VPC**: Si el cluster de EKS y el cluster de MSK viven en la misma VPC, solo el enrutamiento de subnets te da conectividad — lo más simple y con la menor latencia.
* **VPC diferente**: Necesitarás VPC peering o un AWS Transit Gateway para conectar las dos VPCs. MSK admite acceso público (endpoints públicos de brokers), pero las configuraciones de producción suelen preferir conectividad privada.
* **Security groups**: El security group del cluster de MSK debe permitir explícitamente tráfico entrante desde el security group del nodo de EKS (o del pod, si los pods tienen sus propios security groups) en los puertos relevantes de los brokers — plaintext 9092, TLS 9094, SASL/SCRAM 9096, IAM 9098. Nada está permitido de forma predeterminada.

```bash
# Allow the IAM auth port on the MSK security group from the EKS node security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

### Comparación de mecanismos de autenticación

| Mecanismo | Cómo funciona | Punto de integración con EKS |
| --- | --- | --- |
| **Autenticación IAM (`AWS_MSK_IAM`)** | El cliente se autentica con una solicitud firmada con SigV4 usando `AWS_MSK_IAM`, un mecanismo SASL personalizado dedicado (no una extensión OAUTHBEARER); las políticas IAM controlan permisos por topic | Otorga al pod un IAM role mediante IRSA — no hay credenciales que distribuir |
| **SASL/SCRAM** | Basado en usuario/contraseña; credenciales almacenadas en AWS Secrets Manager | Sincroniza credenciales SCRAM desde Secrets Manager hacia un Kubernetes Secret mediante External Secrets Operator |
| **Mutual TLS (mTLS)** | Certificados de cliente emitidos por AWS Private CA; la identidad se verifica mediante certificado | Monta certificados/keys en pods mediante cert-manager o External Secrets Operator |

La autenticación IAM es la opción más natural para EKS. Con IRSA (IAM Roles for Service Accounts), otorgas a un pod un IAM role acotado y expresas el control de acceso a nivel de topic puramente mediante políticas IAM — sin contraseñas ni certificados que distribuir o rotar.

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

En el lado del cliente, añade la biblioteca `aws-msk-iam-auth` a tu classpath (o el paquete equivalente para tu lenguaje), luego configura el cliente Kafka con:

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

## MSK Connect

MSK Connect es la oferta Kafka Connect completamente gestionada de AWS. AWS se encarga del aprovisionamiento, escalado y parcheo de la infraestructura de workers de Connect; tú registras plugins de connectors (paquetes JAR) subiéndolos a S3.

El detalle importante: MSK Connect **no se limita a clusters de MSK**. Siempre que tenga alcance de red a los bootstrap brokers, MSK Connect también puede ejecutar connectors contra un cluster Kafka autogestionado que se ejecuta en EKS mediante Strimzi.

```bash
# Upload a custom connector plugin to S3 and register it as an MSK Connect custom plugin
aws kafkaconnect create-custom-plugin \
  --name debezium-postgres-plugin \
  --content-type ZIP \
  --location s3Location='{bucketArn=arn:aws:s3:::my-connect-plugins,fileKey=debezium-postgres-2.7.zip}'
```

| Aspecto | MSK Connect | Strimzi `KafkaConnect` (autooperado en EKS) |
| --- | --- | --- |
| **Carga operativa** | AWS gestiona la infraestructura de workers; tú solo gestionas la configuración de connectors | Tú gestionas el escalado de worker pods, el monitoreo y el ajuste de recursos |
| **Flexibilidad** | Limitada al framework de connectors que AWS admite | Libertad total para connectors arbitrarios, SMTs (Single Message Transforms) personalizados, sidecars |
| **Portabilidad** | Servicio solo de AWS, difícil de mover a otro lugar | Portable tal cual a cualquier otro cluster de Kubernetes |
| **Observabilidad** | Estado de connectors mediante CloudWatch Logs/Metrics | Se integra en el mismo pipeline de Prometheus/Grafana que el resto de tus workloads de EKS |

## Comparación y puente con Kinesis Data Streams

Kinesis Data Streams y Kafka a menudo se mencionan en el mismo contexto, pero **no son protocolos compatibles**. Kinesis es un servicio de streaming nativo de AWS con su propia API/SDK, y no entiende el protocolo producer/consumer de Kafka. El hecho de que MSK se describa como "compatible con Kafka" no significa que interopere con Kinesis — MSK es una implementación gestionada del protocolo Apache Kafka, y Kinesis es un servicio completamente independiente.

| Aspecto | Apache Kafka (MSK/Strimzi) | Kinesis Data Streams |
| --- | --- | --- |
| **Protocolo** | Protocolo Kafka open-source, compatible con un amplio ecosistema de clientes/tooling | API propietaria de AWS, no compatible con clientes Kafka |
| **Unidad de escalado** | Partitions (definidas al crear el topic, pueden reparticionarse) | Shards (unidades de capacidad de lectura/escritura, ajustadas mediante split/merge) |
| **Complejidad operativa** | Requiere operar brokers/controllers (MSK descarga esto en AWS) | Completamente gestionado, sin concepto de server en absoluto |
| **Integración con servicios de AWS** | Indirecta, mediante connectors (Kafka Connect, MSK Connect) | Nativa, integración directa con triggers de Lambda, Firehose, Kinesis Data Analytics |
| **Ecosistema** | Amplio ecosistema open-source: Kafka Streams, ksqlDB, Flink, Debezium | Más pequeño, centrado en servicios de AWS, pero más simple de integrar |
| **Retención** | Efectivamente ilimitada (pagas solo por storage; valor predeterminado de 7 días) | 24 horas por defecto, ampliable hasta 365 días (con costo creciente) |

### El patrón real de puente

Si necesitas conectar realmente Kafka y Kinesis — para migración, o para hacer puente con consumidores Kinesis legacy — el patrón práctico es un **connector de Kinesis ejecutándose bajo Kafka Connect (o MSK Connect)**, no ninguna compatibilidad de protocolo incorporada.

* **Kinesis Sink connector**: lee mensajes de un topic de Kafka y los escribe en un stream de Kinesis — útil para alimentar la salida de un pipeline basado en Kafka hacia el ecosistema de consumo de Kinesis (Lambda, Firehose)
* **Kinesis Source connector**: lee records de un stream de Kinesis y los escribe en un topic de Kafka — útil para mantener productores Kinesis existentes en su lugar mientras migras consumidores gradualmente a Kafka

Estos connectors pueden desplegarse en MSK Connect o ejecutarse directamente en EKS mediante los CRs `KafkaConnect`/`KafkaConnector` de Strimzi — aquí también aplican las mismas compensaciones entre MSK Connect y Strimzi de la sección anterior.

## Guía de decisión

Usa esta checklist para acotar la elección entre Strimzi autogestionado, MSK Provisioned, MSK Serverless y Kinesis.

* **¿Tu equipo tiene experiencia en operaciones Kafka y necesita ajuste fino/configuración personalizada?** → Sí: Strimzi (autogestionado en EKS) / No: considera MSK
* **¿La portabilidad multi-cloud/on-prem es un requisito estricto?** → Sí: Strimzi / No: vale la pena evaluar MSK
* **¿El tráfico es impredecible o con picos, y quieres eliminar por completo la planificación de capacidad de brokers?** → Sí: MSK Serverless / No: MSK Provisioned o Strimzi
* **¿Ya tienes una inversión profunda en procesamiento de eventos nativo de AWS (Lambda, Firehose) y no necesitas el ecosistema Kafka (Kafka Streams, ksqlDB, etc.)?** → Sí: evalúa Kinesis Data Streams / No: mantente con Kafka (MSK/Strimzi)
* **¿Quieres gestionar Kafka mediante el mismo pipeline GitOps que el resto de tu plataforma EKS, sin añadir una superficie de consola de AWS/IAM?** → Sí: Strimzi / No: MSK

En la práctica, la respuesta a menudo es "ambos" — iniciar un servicio nuevo en MSK Serverless por rapidez y luego migrar a Strimzi cuando necesitas ajustes personalizados es una trayectoria común.

## Próximos pasos

Ya sea que ejecutes MSK o Strimzi, necesitas visibilidad continua de las métricas de brokers y del consumer lag para saber que el cluster está saludable. Ese es el tema de [Parte 7: Monitoreo](./07-monitoring.md).

[Volver a la página principal](./)

## Cuestionario

Para probar lo que aprendiste en este capítulo, intenta el [Cuestionario del tema](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md).
