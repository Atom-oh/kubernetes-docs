# MSK Integration Quiz

Este cuestionario evalúa tu comprensión de las compensaciones entre Amazon MSK y Strimzi autogestionado, cómo conectar workloads de EKS a MSK, MSK Connect, y las diferencias entre Kafka y Kinesis Data Streams.

## Multiple Choice Questions

1. ¿Cuál es la diferencia más fundamental entre Amazon MSK y Strimzi autogestionado en EKS?
   - A) MSK no usa el protocolo Kafka
   - B) Dónde se ejecutan realmente los brokers y quién es responsable de operarlos
   - C) Strimzi no puede ejecutarse en Kubernetes
   - D) MSK no admite el concepto de particiones

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Dónde se ejecutan realmente los brokers y quién es responsable de operarlos**

**Explicación:**
MSK ejecuta brokers en infraestructura administrada por AWS, y AWS se encarga del parchado, el reemplazo de hardware y la expansión de almacenamiento en tu nombre. Strimzi ejecuta brokers como Pods dentro de tu cluster de EKS; aunque el Operator automatiza las actualizaciones progresivas y la reconciliación, sigues siendo responsable de decisiones como el momento de la actualización, la planificación de capacidad y la respuesta a incidentes. Ambos implementan el mismo protocolo Apache Kafka, por lo que no hay diferencia a nivel de protocolo.
</details>

2. ¿Qué afirmación describe correctamente MSK Serverless?
   - A) La configuración de broker (`server.properties`) se puede personalizar libremente
   - B) El dimensionamiento de los brokers no se expone al usuario, y la facturación se basa en throughput
   - C) Solo funciona con clusters basados en ZooKeeper
   - D) Siempre es más barato que MSK Provisioned

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El dimensionamiento de los brokers no se expone al usuario, y la facturación se basa en throughput**

**Explicación:**
MSK Serverless escala automáticamente por partición, y los usuarios nunca tienen que pensar en el número de brokers ni en los tipos de instancia. En cambio, se factura según el throughput: por partición, por GB de entrada/salida. No se admite configuración personalizada de brokers, y algunas APIs/funcionalidades (ciertos tipos de ACL, tipos de connector) están restringidas. Que sea más barato que Provisioned depende de tu patrón de tráfico, por lo que no se puede asumir que siempre será más barato.
</details>

3. ¿Qué combinación permite que un pod de EKS se autentique ante un broker de MSK sin distribuir credenciales IAM separadas?
   - A) SASL/SCRAM con Secrets Manager
   - B) IRSA con el mecanismo SASL `AWS_MSK_IAM`
   - C) mTLS con AWS Private CA
   - D) Un listener de texto plano solo con security groups

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) IRSA con el mecanismo SASL `AWS_MSK_IAM`**

**Explicación:**
IRSA (IAM Roles for Service Accounts) otorga un rol IAM a un pod, y configurar `sasl.mechanism=AWS_MSK_IAM` en el cliente Kafka hace que se autentique mediante solicitudes firmadas con SigV4. La ventaja clave es que no hay credenciales separadas —contraseñas, certificados— que distribuir o rotar. SASL/SCRAM y mTLS también son métodos de autenticación válidos, pero requieren sincronizar credenciales desde Secrets Manager o emitir/montar certificados, respectivamente.
</details>

4. ¿Qué configuración de red se requiere para que un workload de EKS alcance un cluster de MSK en una VPC diferente?
   - A) MSK siempre debe cambiarse a acceso público
   - B) VPC peering o un AWS Transit Gateway debe conectar las dos VPCs
   - C) El protocolo Kafka cruza automáticamente los límites de VPC
   - D) Un NAT gateway por sí solo es suficiente, no se necesita más configuración

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) VPC peering o un AWS Transit Gateway debe conectar las dos VPCs**

**Explicación:**
Si el cluster de EKS y el cluster de MSK residen en VPCs diferentes, necesitas VPC peering o un Transit Gateway para establecer el enrutamiento entre ellos. MSK sí admite acceso público, pero esa es una configuración opcional y separada, y los entornos de producción generalmente prefieren conectividad privada por motivos de seguridad. Incluso con una ruta de red establecida, la conectividad seguirá bloqueada si el security group del cluster de MSK no permite tráfico entrante desde el security group del nodo/pod de EKS.
</details>

5. ¿Qué afirmación sobre la configuración del security group del cluster de MSK es correcta?
   - A) Todo el tráfico dentro de la misma VPC se permite de forma predeterminada
   - B) El tráfico entrante hacia los puertos de los brokers debe permitirse explícitamente desde el security group del nodo (o pod) de EKS
   - C) No se necesitan security groups cuando se usa autenticación IAM
   - D) La configuración de security groups solo se aplica a MSK Serverless

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El tráfico entrante hacia los puertos de los brokers debe permitirse explícitamente desde el security group del nodo (o pod) de EKS**

**Explicación:**
El security group de un cluster de MSK no permite tráfico entrante de forma predeterminada. Debes agregar explícitamente una regla de entrada que permita como origen el security group del nodo worker de EKS (o del pod, si usas security groups por pod) para los puertos relevantes del broker: texto plano 9092, TLS 9094, SASL/SCRAM 9096, IAM 9098. Esta regla de security group de la capa de red es necesaria independientemente del mecanismo de autenticación (IAM, SCRAM, mTLS) que uses.
</details>

6. ¿Qué afirmación sobre MSK Connect es correcta?
   - A) Solo puede conectarse a clusters de MSK, no a otros clusters de Kafka
   - B) Siempre que tenga alcance de red hacia los bootstrap brokers, también puede ejecutar connectors contra un cluster de Strimzi en EKS
   - C) Los usuarios deben administrar por sí mismos el escalado y el parchado de los workers de Connect
   - D) Los plugins de connector solo pueden registrarse como imágenes de contenedor

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Siempre que tenga alcance de red hacia los bootstrap brokers, también puede ejecutar connectors contra un cluster de Strimzi en EKS**

**Explicación:**
MSK Connect no está restringido a clusters de MSK. Siempre que un connector pueda alcanzar los bootstrap brokers a través de la red, puede apuntarse a cualquier cluster de Kafka, incluido un cluster de Strimzi autogestionado en EKS. AWS administra el aprovisionamiento, el escalado y el parchado de la infraestructura de workers de Connect, por lo que los usuarios no administran eso por sí mismos. Los plugins personalizados de connector se registran subiendo un ZIP de JARs a S3.
</details>

7. ¿Qué afirmación describe correctamente la relación entre Kafka y Kinesis Data Streams?
   - A) Debido a que MSK es "compatible con Kafka", un cliente de Kinesis puede conectarse directamente a MSK
   - B) Kafka y Kinesis son servicios separados que usan protocolos diferentes y no son directamente compatibles
   - C) Kinesis implementa internamente el protocolo Kafka tal como es
   - D) Un cliente Kafka puede conectarse directamente a un stream de Kinesis solo cambiando la configuración

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Kafka y Kinesis son servicios separados que usan protocolos diferentes y no son directamente compatibles**

**Explicación:**
Kinesis Data Streams es un servicio completamente separado con su propia API/SDK propietaria de AWS; no entiende el protocolo de productor/consumidor de Kafka. Cuando MSK se describe como "compatible con Kafka", eso solo significa que implementa el protocolo Apache Kafka; no implica interoperabilidad con Kinesis. Conectar ambos requiere una capa separada, como connectors sink/source de Kinesis que se ejecuten bajo Kafka Connect (o MSK Connect).
</details>

8. ¿Cuál es la forma correcta de conectar realmente Kafka y Kinesis Data Streams?
   - A) Apuntar el `bootstrap.servers` del cliente Kafka al endpoint de Kinesis
   - B) Usar un connector sink/source de Kinesis bajo Kafka Connect o MSK Connect
   - C) Usar una bandera de configuración que cambie un cluster de MSK al "modo Kinesis"
   - D) Pueden referenciarse directamente entre sí, ya que comparten el mismo modelo de particiones

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar un connector sink/source de Kinesis bajo Kafka Connect o MSK Connect**

**Explicación:**
Como Kafka y Kinesis son incompatibles a nivel de protocolo, conectarlos requiere un connector que haga la traducción. Un connector sink de Kinesis lee mensajes desde un topic de Kafka y los escribe en un stream de Kinesis; un connector source de Kinesis lee registros desde un stream de Kinesis y los escribe en un topic de Kafka. Estos connectors pueden desplegarse en MSK Connect o ejecutarse directamente en EKS mediante los CRs `KafkaConnect`/`KafkaConnector` de Strimzi.
</details>

9. ¿Cuál de las siguientes NO es una razón válida para seguir ejecutando Kafka por tu cuenta en EKS con Strimzi aunque exista MSK?
   - A) Quieres que Kafka encaje en el mismo pipeline de GitOps/observabilidad que el resto de la plataforma
   - B) Necesitas portabilidad a entornos on-prem o multi-cloud
   - C) Necesitas una funcionalidad reciente de Kafka que MSK aún no admite
   - D) No quieres tener ningún personal de operaciones de brokers en absoluto

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) No quieres tener ningún personal de operaciones de brokers en absoluto**

**Explicación:**
Strimzi autogestionado automatiza mucho mediante el Operator, pero decisiones como el momento de las actualizaciones, la planificación de capacidad y la respuesta a incidentes siguen siendo tu responsabilidad. Si quieres eliminar por completo la carga de operaciones de brokers, MSK —especialmente MSK Serverless— en realidad encaja mejor. La integración con GitOps, la portabilidad y el acceso a las funcionalidades más recientes de Kafka son razones legítimas para ejecutar Strimzi en EKS en su lugar.
</details>

10. ¿Qué afirmación describe con mayor precisión la diferencia del modelo de costos entre MSK Provisioned y Strimzi autogestionado?
    - A) MSK siempre es más barato que Strimzi
    - B) MSK factura por hora de broker más almacenamiento, mientras que Strimzi incurre en costos directos de EC2/EBS más un costo separado de personal operativo
    - C) Strimzi no tiene modelo de facturación y es completamente gratuito
    - D) Los dos modelos de costos son idénticos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) MSK factura por hora de broker más almacenamiento, mientras que Strimzi incurre en costos directos de EC2/EBS más un costo separado de personal operativo**

**Explicación:**
MSK Provisioned factura según precios por hora de broker, almacenamiento (GB-mes) y transferencia de datos. Con Strimzi pagas directamente por la infraestructura EC2/EBS —normalmente más barata a escala—, pero el costo del personal que la opera es una consideración separada y adicional. Qué opción gana en costo total de propiedad depende del volumen de tráfico, la capacidad operativa de tu organización y los costos laborales.
</details>

## Short Answer Questions

11. ¿Cuál es el nombre exacto del mecanismo SASL que usa un pod de EKS para autenticarse en MSK mediante un rol IAM?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `AWS_MSK_IAM`**

**Explicación:**
`AWS_MSK_IAM` es el mecanismo SASL que proporciona MSK y que permite a los clientes autenticarse mediante credenciales firmadas con SigV4 (un rol o usuario IAM). En la configuración del cliente, estableces `security.protocol=SASL_SSL` y `sasl.mechanism=AWS_MSK_IAM`, y registras el `IAMLoginModule` y el `IAMClientCallbackHandler` de la biblioteca `aws-msk-iam-auth` como el módulo de inicio de sesión JAAS y el callback handler.
</details>

12. ¿Cuál es el nombre de la biblioteca que un cliente de MSK debe agregar a su classpath (o el package manager equivalente para su lenguaje) para usar autenticación IAM?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `aws-msk-iam-auth`**

**Explicación:**
`aws-msk-iam-auth` es una biblioteca cliente proporcionada por AWS que implementa `AWS_MSK_IAM`, un mecanismo SASL personalizado dedicado (no una extensión OAUTHBEARER), que permite a los clientes Kafka generar solicitudes firmadas con SigV4 y autenticarse ante brokers de MSK con credenciales IAM. El cliente Java se distribuye como un artefacto Maven, y existen implementaciones comunitarias equivalentes para otros lenguajes (Python, Go, etc.).
</details>

13. ¿Cuál es el nombre del servicio Kafka Connect completamente administrado de AWS, donde AWS se encarga del aprovisionamiento y escalado de los workers de connectors?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: MSK Connect**

**Explicación:**
MSK Connect es el servicio donde AWS administra el aprovisionamiento, el escalado y el parchado del cluster de workers de Kafka Connect. Los usuarios simplemente suben plugins de connector (un ZIP de JARs) a S3 y registran la configuración del connector. Puede conectarse no solo a clusters de MSK, sino a cualquier cluster de Kafka alcanzable por red, incluido un cluster de Strimzi en EKS.
</details>

14. ¿Cuál es la unidad de escalado de Kinesis Data Streams que corresponde a la "partition" de Kafka?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Shard**

**Explicación:**
Kafka divide un topic en varias particiones para paralelismo y escalabilidad; el número de particiones se define al crear el topic y luego puede ajustarse mediante reparticionamiento. Kinesis, en cambio, divide la capacidad de lectura/escritura en shards, y la capacidad se ajusta mediante operaciones de división y fusión de shards. Los dos conceptos cumplen un propósito similar, pero difieren en la API y la mecánica operativa.
</details>

15. ¿Qué tipo de connector de Kafka Connect lee mensajes desde un topic de Kafka y los escribe en un stream de Kinesis?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: connector Kinesis Sink**

**Explicación:**
Un connector Kinesis Sink trata un topic de Kafka como su origen, lee mensajes y los escribe en un stream de Kinesis. Por el contrario, un connector Kinesis Source lee registros desde un stream de Kinesis y los escribe en un topic de Kafka. Ambos connectors existen específicamente porque Kafka y Kinesis no tienen compatibilidad de protocolo: son la capa que realmente conecta datos entre ambos.
</details>

## Hands-on Questions

16. Escribe el comando de AWS CLI que permite tráfico entrante desde el security group del nodo worker de EKS (`sg-0efgh5678eksnode`) hacia el puerto de autenticación IAM en el security group del cluster de MSK (`sg-0abcd1234msk`).

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

**Explicación:**
El puerto de autenticación IAM de MSK es 9098. En `authorize-security-group-ingress`, `--group-id` especifica el security group de destino al que se agregará la regla (el security group de MSK), y `--source-group` especifica el origen de tráfico permitido (el security group del nodo de EKS). Sin esta regla, incluso un intento exitoso de autenticación IAM quedaría bloqueado en la etapa de conexión TCP. Si usas un mecanismo de autenticación diferente, ajusta el puerto según corresponda (TLS: 9094, SASL/SCRAM: 9096).
</details>

17. Escribe un JSON de política IAM que otorgue a un cliente Kafka que usa autenticación IAM acceso de lectura/escritura solo al topic `orders` en un cluster de MSK específico.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
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

**Explicación:**
La primera declaración otorga los permisos mínimos para conectarse al cluster y describir su estado (`Connect`, `DescribeCluster`). La segunda declaración limita el ARN del recurso a `topic/my-msk-cluster/*/orders`, otorgando acciones relacionadas con topics, permisos de escritura (`WriteData`) y lectura (`ReadData`) solo para el topic `orders`. Limitar el ARN del recurso de forma tan estricta significa que el cliente no puede acceder a ningún otro topic en el mismo cluster.
</details>

18. Escribe un archivo de configuración de cliente Kafka (properties) que configure el cliente para usar el mecanismo `AWS_MSK_IAM`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

**Explicación:**
`security.protocol=SASL_SSL` especifica el uso de autenticación SASL junto con cifrado TLS. `sasl.mechanism=AWS_MSK_IAM` selecciona el mecanismo SASL basado en IAM. `sasl.jaas.config` registra el `IAMLoginModule` de la biblioteca `aws-msk-iam-auth` como el módulo de inicio de sesión JAAS, y `sasl.client.callback.handler.class` especifica el callback handler que genera la solicitud firmada con SigV4. Con solo esta configuración, el cliente se autentica automáticamente usando su cadena local de credenciales, incluido un rol IAM inyectado mediante IRSA.
</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/kafka/06-msk-integration.md) | [Siguiente cuestionario: Monitoring](./07-monitoring-quiz.md)
