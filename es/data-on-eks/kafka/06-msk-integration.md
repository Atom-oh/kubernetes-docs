# Parte 6: Integración de MSK

> **Referencia de revisión**: MSK Provisioned Standard/Express, MSK Serverless, MSK Connect; biblioteca auxiliar de IAM para Java 2.3.9\
> **Última revisión**: 16 de octubre de 2026

## Responsabilidades y requisitos previos

Amazon MSK ejecuta brokers de Kafka fuera de tu clúster de EKS en infraestructura administrada por AWS.
Strimzi los ejecuta como cargas de trabajo de Kubernetes que opera tu equipo. Ambos requieren
decisiones sobre aplicaciones, temas, control de acceso, retención y recuperación. Un
broker administrado no elimina la necesidad de comprender el comportamiento de Kafka.

Usa AWS CLI v2 y kubectl compatibles con el clúster de EKS. Un cliente IAM necesita una
biblioteca auxiliar de autenticación compatible y una cadena de credenciales de carga de trabajo funcional.
EKS Pod Identity o IRSA pueden proporcionar credenciales temporales; External Secrets
Operator es opcional para otros flujos de administración de secretos, no es un requisito previo de IAM.

## Compara las variantes reales de MSK

| Opción | Capacidad y configuración | Costos que debes incluir |
| --- | --- | --- |
| MSK Provisioned Standard | Elige brokers y almacenamiento; configura el escalado automático del almacenamiento si es necesario; solo se pueden editar los ajustes de broker compatibles | Horas de broker, almacenamiento aprovisionado, rendimiento/almacenamiento por niveles opcionales y red |
| MSK Provisioned Express | Elige la capacidad de cómputo del broker; el almacenamiento escala automáticamente y se factura según el uso; límites de configuración/rendimiento obligatorios | Horas de broker, datos entrantes, almacenamiento utilizado y cargos de red aplicables |
| MSK Serverless | AWS administra la capacidad de los brokers; los usuarios siguen planificando temas, particiones, retención y cuotas del servicio | **Horas de clúster**, horas de partición, datos entrantes/salientes, almacenamiento utilizado y cargos de red aplicables |
| Strimzi en EKS | Opera nodos, discos, topología de brokers y controladores y configuración compatible del operador | EKS/EC2/EBS, redes, capacidad de reserva, observabilidad y esfuerzo operativo |

Express es un **tipo de broker Provisioned**, no Serverless. Su documentación actual
requiere tres AZ y enumera restricciones de API/funciones, incluida la compatibilidad incompleta con KStreams
y la falta de compatibilidad con KIP-932. Comprueba la combinación compatible de broker/versión
en lugar de suponer que todas las funciones de Kafka funcionan de la misma manera.

Serverless requiere autenticación/autorización de IAM; no admite ACL de Kafka. Solo permite
los ajustes de tema enumerados. Por ejemplo, la retención es configurable,
mientras que `cleanup.policy` solo se puede establecer al crear el tema. La retención predeterminada
también incluye un **límite de 250 GiB por partición**, no solo siete días. Un mayor volumen de datos puede alcanzar ese límite de tamaño antes del límite de tiempo. El escalado automático de capacidad no elimina los límites al número de particiones ni a las tasas de ráfagas.

Hay métricas de CloudWatch para estas ofertas, pero la supervisión de Serverless no es
la misma interfaz de Prometheus/monitorización abierta a nivel de broker que ofrece Provisioned.
Las políticas de temas/grupos de IAM siguen siendo tu responsabilidad para la multitenencia de Serverless.
En Strimzi, los namespaces de Kubernetes por sí solos no autorizan el acceso a los temas de Kafka.

MSK se puede administrar con API e infraestructura como código; GitOps no es exclusivo
de Strimzi. La portabilidad de una implementación de Strimzi sigue dependiendo del almacenamiento, las redes,
la identidad y las versiones compatibles del operador. Compara el costo total medido y los
requisitos de recuperación; ni «la autogestión siempre es más barata a escala» ni «Serverless
es la opción más barata para las ráfagas» son una suposición predeterminada acertada.

## Conectividad de red desde EKS

El cliente debe poder alcanzar **todos los endpoints de broker anunciados en los metadatos**, no solo
la dirección de bootstrap. Valida DNS, rutas, grupos de seguridad, NACL, identidad de origen del Pod/nodo
y salida. Compartir una VPC no es suficiente por sí solo.

Para conectar VPC distintas, las opciones incluyen peering/enrutamiento mediante Transit Gateway y
**conectividad privada multi-VPC** de MSK compatible con PrivateLink. La función administrada multi-VPC está disponible en la misma región y tiene requisitos de clúster, autenticación y subredes en las zonas de disponibilidad (AZ).
Los endpoints públicos son una opción explícita para clústeres compatibles, no un requisito previo
para el acceso entre VPC.

| Ejemplo de endpoint directo | Puerto |
| --- | --- |
| IPv4 privado TLS | 9094 |
| IPv4 privado SASL/SCRAM | 9096 |
| IPv4 privado IAM | 9098 |
| TLS / SCRAM / IAM público, cuando sea compatible y esté habilitado | 9194 / 9196 / 9198 |

Los endpoints IPv6 y los endpoints administrados multi-VPC pueden usar puertos distintos. Recupera la respuesta real
de bootstrap y selecciona el campo para la ruta de red/autenticación prevista; no reescribas todos los endpoints a 9098.

```bash
: "${DOCS_AWS_REGION:?Set the MSK region}"
: "${DOCS_MSK_CLUSTER_ARN:?Set the exact existing cluster ARN}"
aws kafka get-bootstrap-brokers \
  --region "$DOCS_AWS_REGION" \
  --cluster-arn "$DOCS_MSK_CLUSTER_ARN"
```

Para el acceso IAM directo mediante IPv4 privado en la misma VPC, un administrador de red puede
aplicar este ejemplo de alcance limitado tras comprobar las reglas existentes:

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

El comando **modifica** un grupo de seguridad. Usa el SG de origen real del nodo/Pod para la
ruta de red; las referencias a SG de distintas VPC tienen sus propias reglas de compatibilidad. Los SG existentes
pueden contener ya reglas, incluidas reglas autorreferenciales. La autenticación IAM
no puede tener éxito antes de establecer la conectividad TCP/TLS.

## Autenticación IAM e identidad de carga de trabajo

| Cliente | Mecanismo IAM compatible |
| --- | --- |
| Java | `AWS_MSK_IAM` o `OAUTHBEARER` con la biblioteca auxiliar de Java de AWS |
| Python, JavaScript, Go, .NET | `OAUTHBEARER` con el firmante o la biblioteca auxiliar oficial de AWS correspondiente |

`AWS_MSK_IAM` no es un mecanismo genérico que proporcione el cliente Kafka de todos los lenguajes.
Las bibliotecas auxiliares que no son de Java son proyectos oficiales de AWS, no simples equivalentes de la comunidad.
En clústeres Provisioned, también pueden estar disponibles SCRAM o TLS mutuo; configura
el flujo compatible de secretos/certificados y las ACL de Kafka. No son alternativas a
IAM en Serverless.

Configura la asociación/relación de confianza del rol de carga de trabajo y la actualización de credenciales temporales
antes de probar Kafka. No supongas que un rol de nodo heredado es la identidad prevista del Pod. Los entornos
privados también deben poder acceder a los servicios de identidad que requiera su proveedor de credenciales.
Prueba la reautenticación después de que se actualicen las credenciales.
La biblioteca auxiliar de Java documenta un problema de coherencia en el nombre de sesión con algunos proveedores,
incluido Pod Identity; aplica la solución alternativa documentada si se produce ese problema.

### Separa las políticas de productor y consumidor

El siguiente script deriva ARN de recursos exactos a partir del ARN del clúster existente.
Guárdalo como `policies.py`; escribe las políticas localmente y no las adjunta.
Omite las concesiones administrativas antiguas `AlterCluster` y `*Topic*`, incluye
acciones de grupos de consumidores y distingue el permiso de escritura idempotente de alcance de clúster
de las escrituras de alcance de tema.

```python
import json
import re
import sys
from pathlib import Path

def policies(cluster_arn, topic="orders", group="orders-consumer"):
    match = re.fullmatch(
        r"arn:(aws(?:-[a-z-]+)?):kafka:([a-z0-9-]+):(\d{12}):cluster/([A-Za-z0-9_-]+)/([A-Za-z0-9-]+)",
        cluster_arn,
    )
    if not match:
        raise ValueError("Supply an exact MSK cluster ARN, including its cluster UUID.")
    for name in [topic, group]:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,249}", name) or name in [".", ".."]:
            raise ValueError("Use an explicit topic/group name without wildcards.")
    partition, region, account, cluster_name, uuid = match.groups()
    prefix = f"arn:{partition}:kafka:{region}:{account}:"
    identity = f"{cluster_name}/{uuid}"
    topic_arn = prefix + f"topic/{identity}/{topic}"
    group_arn = prefix + f"group/{identity}/{group}"
    def statement(actions, resource):
        return {"Effect": "Allow", "Action": ["kafka-cluster:" + a for a in actions], "Resource": resource}
    return {
        "producer": {"Version": "2012-10-17", "Statement": [
            statement(["Connect", "WriteDataIdempotently"], cluster_arn),
            statement(["DescribeTopic", "WriteData"], topic_arn),
        ]},
        "consumer": {"Version": "2012-10-17", "Statement": [
            statement(["Connect"], cluster_arn),
            statement(["DescribeTopic", "ReadData"], topic_arn),
            statement(["DescribeGroup", "AlterGroup"], group_arn),
        ]},
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 policies.py EXACT_MSK_CLUSTER_ARN")
    for name, policy in policies(sys.argv[1]).items():
        Path(f"msk-{name}-policy.json").write_text(json.dumps(policy, indent=2) + "\n")
```

```bash
: "${DOCS_MSK_CLUSTER_ARN:?Set the exact existing MSK cluster ARN}"
python3 policies.py "$DOCS_MSK_CLUSTER_ARN"
# Review msk-producer-policy.json and msk-consumer-policy.json,
# then attach each to the appropriate workload role through your IAM workflow.
```

El tema existente es `orders`, y el consumidor debe usar el grupo
`orders-consumer`. La creación de temas corresponde a una identidad administrativa independiente.
La política del productor cubre escrituras **idempotentes no transaccionales** mediante el
conjunto documentado de acciones IAM. Un productor transaccional también necesita acciones de ID
transaccional con alcance definido y compatibilidad del broker; IAM admite
`WriteTxnMarkers` en MSK Kafka 3.8 y versiones posteriores. No concedas todos los ID transaccionales
ni desactives la idempotencia simplemente para ocultar un error de autorización.

El acceso efectivo también depende de otras políticas adjuntas, denegaciones explícitas, SCP, límites
de permisos y políticas de recursos entre cuentas. Estos documentos no constituyen
por sí solos un límite de autorización completo. Las acciones del plano de control de MSK,
como `kafka:GetBootstrapBrokers`, son independientes de las acciones del plano de datos `kafka-cluster:*`
y pueden corresponder a la identidad de implementación/operador.

### Configuración del cliente Java

Añade `software.amazon.msk:aws-msk-iam-auth:2.3.9` y sus dependencias, o usa el
JAR todo en uno de la versión verificada. Guarda esto como `iam.properties`:

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

Para el mecanismo OAuth de Java, usa esta alternativa en lugar de combinar ambos:

```properties
security.protocol=SASL_SSL
sasl.mechanism=OAUTHBEARER
sasl.jaas.config=org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required;
sasl.login.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
ssl.endpoint.identification.algorithm=https
```

Añade en la aplicación el `bootstrap.servers` seleccionado, serializadores o deserializadores de clave/valor
y `group.id` del consumidor. La JVM debe confiar en la cadena de certificados TLS del broker;
mantén habilitada la verificación del nombre de host. Estas propiedades configuran el mecanismo, pero no pueden
crear credenciales de carga de trabajo ni permisos IAM que falten.

## MSK Connect: compatibilidad antes de la implementación

MSK Connect ejecuta workers administrados de Kafka Connect y puede apuntar a un clúster de Kafka alojado de forma independiente. **La accesibilidad de red por sí sola no basta.** La API actual
`KafkaClusterClientAuthentication` acepta `NONE` o `IAM`; la confianza en el broker,
la autenticación y los ajustes compatibles del worker deben coincidir. El listener TLS/SCRAM de Strimzi de la Parte 2 no es un destino directo solo porque resuelva su nombre de host.
No elimines su autenticación para forzar una integración.

Los runtimes de Connect documentados por el servicio son **2.7.1 / Java 11** y
**3.7.x / Java 17**. Son distintos de la versión del broker Kafka y del runtime de Connect Kafka 4.3.1 usado en la Parte 5. Comprueba el bytecode del plugin, las dependencias, las API de Connect y la matriz de compatibilidad del proveedor. Un JAR que se carga en Java 17 sigue necesitando
pruebas de integración en el runtime administrado seleccionado.

Los artefactos de la Parte 5 no contienen ninguna clase base superior a Java 17, pero eso **no**
certifica la compatibilidad con MSK Connect. Lo siguiente registra el ZIP de Aiven 3.4.3
tras esa revisión de compatibilidad. Presupone un bucket privado de S3 existente en la región de destino y permiso para subir/registrar el plugin.

```bash
: "${DOCS_AWS_REGION:?Set the target region}"
: "${DOCS_PLUGIN_BUCKET:?Set an existing private S3 bucket in that region}"
DOCS_PLUGIN_ZIP="s3-sink-connector-for-apache-kafka-3.4.3.zip"
DOCS_PLUGIN_KEY="plugins/aiven-s3/3.4.3/${DOCS_PLUGIN_ZIP}"
# Download the reviewed release artifact and verify its published digest first.
aws s3 cp "$DOCS_PLUGIN_ZIP" "s3://${DOCS_PLUGIN_BUCKET}/${DOCS_PLUGIN_KEY}" \
  --region "$DOCS_AWS_REGION"
export DOCS_PLUGIN_BUCKET DOCS_PLUGIN_KEY
python3 - <<'PY'
import json
import os
from pathlib import Path
Path("custom-plugin.json").write_text(json.dumps({
    "name": "aiven-s3-3-4-3-reviewed",
    "contentType": "ZIP",
    "location": {"s3Location": {
        "bucketArn": "arn:aws:s3:::" + os.environ["DOCS_PLUGIN_BUCKET"],
        "fileKey": os.environ["DOCS_PLUGIN_KEY"]
    }}
}, indent=2) + "\n")
PY
aws kafkaconnect create-custom-plugin \
  --region "$DOCS_AWS_REGION" \
  --cli-input-json file://custom-plugin.json
```

Esto sube y registra un **plugin**, no un conector en ejecución. Para crear el
conector también se necesita un rol de ejecución del servicio, configuración de Kafka/red,
permisos de origen/destino, capacidad y configuración de conversores. Los conversores
predeterminados de clave/valor de MSK Connect son StringConverter; los ajustes del ejemplo CDC para el sobre de esquema JSON deben configurarse de forma deliberada.

MSK Connect copia el objeto de S3 al crear el plugin. Sobrescribir el objeto
no actualiza el plugin, y los plugins personalizados no se pueden editar en el sitio. Usa un nuevo
recurso de plugin con versión y un plan probado de transición del conector; conserva y
verifica los offsets antes de reemplazar una canalización de datos activa. El escalado automático también tiene
límites configurados y no paraleliza una fuente de una sola tarea.

## Kafka y Kinesis Data Streams

Kinesis Data Streams tiene sus propias API; reemplazar `bootstrap.servers` por un endpoint de Kinesis
no convierte un cliente Kafka. Un conector o un puente explícito de procesamiento de flujos
debe traducir registros, claves, comportamiento de reintento y puntos de control.

| Aspecto | Kafka / MSK / Strimzi | Kinesis Data Streams |
| --- | --- | --- |
| Paralelismo | Particiones de tema; aumentar el número no redistribuye los registros antiguos ni permite reducirlo in situ | Shards; dimensionamiento manual en Provisioned o capacidad administrada por el servicio en los modos bajo demanda |
| Opciones de capacidad | Dependen de Standard, Express, Serverless o de una implementación autogestionada | Provisioned, On-demand Standard y On-demand Advantage |
| Retención | Ajustes del tema/servicio, almacenamiento y política de limpieza; importan tanto los límites de tiempo como los de tamaño | 24 horas de forma predeterminada; configurable hasta 365 días |
| Integraciones de AWS | Incluye integración nativa de Lambda y Firehose con MSK, además de conectores | Integraciones nativas de Lambda, Firehose y Managed Service for Apache Flink |

«Kafka solo se integra con AWS mediante Connect» es incorrecto. Usa también el nombre actual
**Amazon Managed Service for Apache Flink** en lugar de Kinesis Data Analytics.
Para el puente, un conector de salida (sink) de Kinesis escribe registros de Kafka en Kinesis y un conector de entrada (source) hace lo contrario. Selecciona un plugin mantenido compatible con el runtime elegido y prueba
el orden, el comportamiento de la clave de partición, los límites de tamaño de registro y la gestión de duplicados.
Las diferencias de protocolo no prescriben un producto de puente universal.

## Cómo elegir una opción

Empieza por las API de Kafka requeridas, las tasas y asimetrías de datos, los límites de particiones/retención,
la latencia, los objetivos de recuperación, el cumplimiento normativo, las operaciones del equipo y el costo total.
Verifica la compatibilidad regional y de la versión del broker actual. IaC/GitOps se pueden usar tanto con
MSK como con Strimzi. Cambiar de servicio más adelante requiere una migración explícita de datos, esquemas,
identidad y offsets de consumidores; no es automáticamente un paso siguiente sencillo o habitual.

## Referencias y validación

La generación de políticas, la configuración de clases/JAAS de Java, el bytecode del plugin y las formas de solicitud de CLI
se pueden comprobar localmente. Esas comprobaciones no demuestran la autorización IAM efectiva,
la actualización de credenciales de la carga de trabajo, el acceso al broker, una implementación de conector administrado ni la entrega.

- [Brokers Express de MSK](https://docs.aws.amazon.com/msk/latest/developerguide/msk-broker-types-express.html)
- [MSK Serverless](https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html)
- [Configuración de Serverless](https://docs.aws.amazon.com/msk/latest/developerguide/serverless-config.html)
- [Dimensiones de precios de MSK](https://aws.amazon.com/msk/pricing/)
- [Conectividad privada multi-VPC de MSK](https://docs.aws.amazon.com/msk/latest/developerguide/aws-access-mult-vpc.html)
- [Información sobre puertos de MSK](https://docs.aws.amazon.com/msk/latest/developerguide/port-info.html)
- [Mecanismos de cliente IAM y bibliotecas auxiliares oficiales para lenguajes](https://docs.aws.amazon.com/msk/latest/developerguide/configure-clients-for-iam-access-control.html)
- [Dependencias de acciones/recursos de IAM para MSK](https://docs.aws.amazon.com/msk/latest/developerguide/kafka-actions.html)
- [Casos de uso de IAM](https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control-use-cases.html)
- [aws-msk-iam-auth 2.3.9](https://github.com/aws/aws-msk-iam-auth/tree/v2.3.9)
- [MSK Connect](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect.html)
- [Empaquetado de plugins y versiones de Java de MSK Connect](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect-plugins.html)
- [API de autenticación de clientes de MSK Connect](https://docs.aws.amazon.com/MSKC/latest/mskc/API_KafkaClusterClientAuthentication.html)
- [Lambda con MSK](https://docs.aws.amazon.com/lambda/latest/dg/with-msk.html)
- [Firehose con MSK](https://docs.aws.amazon.com/msk/latest/developerguide/integrations-kinesis-data-firehose.html)
- [Modos de capacidad de Kinesis](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html)
- [Retención de Kinesis](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)

## Próximos pasos

[Parte 7: Supervisión](./07-monitoring.md)

[Volver a la página principal](./README.md)

## Cuestionario

[Cuestionario del tema](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
