# Cuestionario de integración de MSK

Repasa las variantes de MSK, IAM y redes, MSK Connect y las diferencias con Kinesis.

## 1. ¿En qué se diferencian MSK y Strimzi en EKS, y qué responsabilidades siguen siendo necesarias?

<details>
<summary>Mostrar respuesta</summary>

MSK ejecuta los brokers en infraestructura administrada por AWS, fuera de EKS; Strimzi los ejecuta en tu entorno de Kubernetes. Aún es necesario diseñar la aplicación, los temas y su retención, el control de acceso y la recuperación.

</details>

## 2. Si solo se considera el caudal, ¿qué cargos de MSK Serverless pueden pasarse por alto?

<details>
<summary>Mostrar respuesta</summary>

Las horas de clúster y de partición, y el almacenamiento utilizado, además de los datos de entrada y salida y los cargos de red aplicables. El escalado automático sigue sujeto a cuotas del servicio y no siempre es la opción más barata.

</details>

## 3. ¿Qué necesita un Pod de EKS para autenticarse en MSK mediante IAM?

<details>
<summary>Mostrar respuesta</summary>

Una configuración de rol y confianza, como Pod Identity o IRSA; carga y renovación de credenciales temporales; un asistente de Kafka compatible; conectividad de red y TLS; y permisos del plano de datos. External Secrets Operator o un rol heredado del nodo no sustituyen estos requisitos.

</details>

## 4. ¿El peering y Transit Gateway son las únicas formas de acceder a MSK desde otra VPC?

<details>
<summary>Mostrar respuesta</summary>

No. La conectividad privada multi-VPC compatible de MSK usa PrivateLink. Comprueba los requisitos de misma región, autenticación y zonas de disponibilidad o subredes, así como los endpoints reales. El acceso público no es obligatorio.

</details>

## 5. ¿Compartir una VPC y tener una política de IAM garantiza la conectividad?

<details>
<summary>Mostrar respuesta</summary>

No. Comprueba DNS, rutas, grupos de seguridad, NACL, egreso, la identidad de origen real y cada dirección de broker anunciada. La autenticación de IAM no puede completarse antes de establecer la conectividad TCP/TLS; revisa también las reglas existentes de los grupos de seguridad.

</details>

## 6. ¿MSK Connect puede usar de inmediato cualquier listener de Strimzi accesible por red?

<details>
<summary>Mostrar respuesta</summary>

No. La API actual de autenticación del clúster ofrece NONE e IAM, y la confianza en los brokers, la autenticación y la configuración de los workers deben coincidir. No des por hecho que basta con proporcionar la dirección de un listener TLS/SCRAM para que funcione.

</details>

## 7. ¿Cambiar `bootstrap.servers` de Kafka por un endpoint de Kinesis hace que el cliente sea compatible?

<details>
<summary>Mostrar respuesta</summary>

No. Kinesis Data Streams usa sus propias API. Se necesita un connector o una capa de procesamiento de streams que conecte las claves, los registros, los reintentos y los checkpoints.

</details>

## 8. ¿Kafka se integra con Lambda y Firehose únicamente mediante Connect?

<details>
<summary>Mostrar respuesta</summary>

No. MSK también ofrece integraciones nativas con Lambda y Firehose. Conectar Kafka y Kinesis es una tarea aparte que requiere validar el entorno de ejecución, el formato, el orden y el tratamiento de duplicados.

</details>

## 9. ¿Es necesario elegir Strimzi en lugar de MSK para usar GitOps?

<details>
<summary>Mostrar respuesta</summary>

No. Las API y la infraestructura como código de MSK se pueden integrar en GitOps. Evalúa Strimzi según la configuración que necesitas, la portabilidad y la capacidad operativa, incluidas las dependencias de almacenamiento, red e identidad.

</details>

## 10. ¿En qué se diferencia MSK Express de Serverless?

<details>
<summary>Mostrar respuesta</summary>

Express es un tipo de broker aprovisionado, con recursos de cómputo seleccionados para el broker y almacenamiento de pago por uso que escala automáticamente. Comprueba sus requisitos de tres zonas de disponibilidad y de funciones. Compara los cargos aplicables por hora de broker, datos de entrada, almacenamiento y otros conceptos.

</details>

## 11. ¿Qué mecanismos SASL de IAM de MSK están disponibles para clientes Java y no Java?

<details>
<summary>Mostrar respuesta</summary>

Java puede usar AWS_MSK_IAM u OAUTHBEARER. Python, JavaScript, Go y .NET usan OAUTHBEARER con firmantes o asistentes oficiales de AWS. No configures AWS_MSK_IAM indiscriminadamente para todos los lenguajes.

</details>

## 12. ¿Añadir únicamente aws-msk-iam-auth completa la autenticación de IAM?

<details>
<summary>Mostrar respuesta</summary>

No. El asistente de Java implementa el mecanismo configurado. También se necesitan credenciales de rol válidas y su renovación, confianza, permisos de datos, conectividad de red y TLS. Los clientes no Java usan el asistente oficial correspondiente a su lenguaje.

</details>

## 13. ¿Qué debes tener en cuenta sobre las versiones de ejecución de MSK Connect y las actualizaciones de plugins?

<details>
<summary>Mostrar respuesta</summary>

Las combinaciones documentadas son Connect 2.7.1/Java 11 y 3.7.x/Java 17. Son independientes de las versiones de los brokers; valida tanto las dependencias y las API como el bytecode. Los plugins copian el contenido de S3 al crearse, así que sobrescribir el objeto no los actualiza.

</details>

## 14. Compara el aumento del número de particiones de Kafka con los modos de capacidad de Kinesis.

<details>
<summary>Mostrar respuesta</summary>

Aumentar las particiones de Kafka no redistribuye los registros existentes ni permite reducirlas in situ. Kinesis usa shards y distingue entre los modos Provisioned, On-demand Standard y On-demand Advantage.

</details>

## 15. ¿Por qué no basta con decir que la retención predeterminada de Serverless es de siete días?

<details>
<summary>Mostrar respuesta</summary>

El valor predeterminado de `retention.bytes` es 250 GiB por partición, por lo que el límite de tamaño puede alcanzarse primero. Comprueba conjuntamente el tiempo, el tamaño, la política de limpieza y las restricciones del servicio. Kinesis Data Streams tiene una retención predeterminada de 24 horas y admite hasta 365 días.

</details>

## 16. Escribe el comando de grupos de seguridad para el acceso IAM privado por IPv4 dentro de la misma VPC y explica su alcance.

<details>
<summary>Mostrar respuesta</summary>

```bash
: "${DOCS_AWS_REGION:?Set the MSK region}"
: "${DOCS_MSK_SG_ID:?Set the existing MSK security group ID}"
: "${DOCS_EKS_SOURCE_SG_ID:?Set the actual EKS source security group ID}"
# Example: same-VPC, direct private IPv4 IAM endpoint on port 9098.
aws ec2 authorize-security-group-ingress \
  --region "$DOCS_AWS_REGION" \
  --group-id "$DOCS_MSK_SG_ID" \
  --protocol tcp --port 9098 \
  --source-group "$DOCS_EKS_SOURCE_SG_ID"
```

Usa el grupo de seguridad real de origen de los nodos o Pods y revisa las reglas existentes. Los endpoints IPv6, públicos y multi-VPC pueden usar otros puertos; inspecciona la respuesta de bootstrap. Este comando modifica el grupo de seguridad.

</details>

## 17. ¿Qué permisos corresponden a las políticas de IAM del productor y del consumidor del tema orders?

<details>
<summary>Mostrar respuesta</summary>

Usa `policies.py` para derivar las políticas a partir del ARN/UUID exacto del clúster. El productor necesita `Connect` y `WriteDataIdempotently` en el clúster, y `DescribeTopic` y `WriteData` en orders. El consumidor necesita `Connect` en el clúster, `DescribeTopic` y `ReadData` en orders, y `DescribeGroup` y `AlterGroup` para su grupo. `AlterCluster` y las acciones que coincidan con `*Topic*` son innecesarias. Diseña por separado permisos de `transactional-ID` con alcance limitado para las transacciones.

</details>

## 18. Escribe las propiedades Java de AWS_MSK_IAM y explica qué más se necesita.

<details>
<summary>Mostrar respuesta</summary>

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

Indica el `bootstrap.servers` seleccionado, los serializadores y deserializadores, y el `group.id` del consumidor. También se necesitan la confianza de CA de la JVM, las credenciales del workload, permisos de IAM y conectividad de red. Mantén habilitada la verificación del hostname.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/kafka/06-msk-integration.md) | [Cuestionario siguiente](./07-monitoring-quiz.md)
