# Parte 5: Kafka Connect y MirrorMaker

> **Línea base de revisión**: Strimzi 1.3.0, Kafka 4.3.1, Debezium PostgreSQL 3.6.3.Final, Aiven S3 sink 3.4.3\
> **Última revisión**: 16 de octubre de 2026

## Workers y conectores de Connect

Kafka Connect ejecuta plugins que mueven datos entre Kafka y sistemas externos.
La configuración es suficiente solo cuando ya existe un plugin adecuado y se
cumplen los requisitos previos de permisos de base de datos/almacenamiento, formato
y red.

| Dirección | Ejemplo | Distinción importante |
| --- | --- | --- |
| Origen: sistema externo → Kafka | Debezium PostgreSQL CDC | La instantánea inicial y la transmisión lógica de WAL son diferentes del sondeo de JDBC |
| Sink: Kafka → sistema externo | Aiven S3 sink | Los formatos admitidos y el comportamiento de entrega dependen del plugin específico |

En modo distribuido, un **broker de Kafka** coordina el grupo de workers; un
worker elegido como líder calcula las asignaciones. Si falla un worker, se activa
una reasignación, que puede tardar y provocar una repetición de datos. El fallo de
una tarea de conector no es automáticamente lo mismo que el fallo de un worker;
investiga los fallos y configura el comportamiento de reinicio.

Connect en modo independiente puede ejecutarse en un contenedor o en Kubernetes,
pero no tiene conmutación por error de workers distribuidos. `KafkaConnect` de
Strimzi administra el modo distribuido. Tres workers no hacen que un conector de
PostgreSQL con una sola tarea ejecute tres tareas.

Connect distribuido usa topics compactados de configuración, offsets de origen y
estado. El topic de configuración necesita **una partición**. Asigna a cada
despliegue de Connect su propio ID de grupo y nombres de topics. RF=3 es la línea
base en este caso porque hay tres brokers; no es un mínimo universal que funcione
con menos brokers. La replicación no es una copia de seguridad. Los offsets de
consumidor de un sink suelen residir en grupos de consumidores de Kafka, no en el
topic de almacenamiento de offsets de origen.

## Strimzi v1 es más que un cambio de apiVersion

Strimzi 1.3.0 sirve la API `kafka.strimzi.io/v1`. Convierte los recursos antiguos
con el procedimiento de migración de la versión antes de actualizar; no te limites
a cambiar el nombre de `v1beta2`.

| Recurso | Campo actual de v1 |
| --- | --- |
| Grupo de workers de KafkaConnect | `spec.groupId` |
| Nombres de topics internos de KafkaConnect | `spec.configStorageTopic`, `spec.offsetStorageTopic`, `spec.statusStorageTopic` |
| Destino y almacenamiento de workers de KafkaMirrorMaker2 | `spec.target`, con su propio `groupId` y los tres campos de nombres de topics |
| Conexión de origen de KafkaMirrorMaker2 | `spec.mirrors[].source` |

Los campos antiguos de MM2 `connectCluster`, `clusters`, `sourceCluster`, `targetCluster` y
`heartbeatConnector` no están en este esquema v1. Apache MM2 incluye una
implementación de conector de heartbeat, pero eso no significa que sea un campo
configurable de `KafkaMirrorMaker2` v1.

## Preparar el ejemplo de Connect

Usa el clúster `my-cluster` de tres brokers de la
[Parte 2](./02-strimzi-operator.md), con TLS/SCRAM y los operadores Topic/User.
Reemplaza la cuenta/repositorio ECR y los nombres de DB/S3 del ejemplo antes del
despliegue. Prepara estas dependencias adicionales:

- `debezium-db-credentials`: un Secret de Kubernetes con una clave `password`.
- `rds-ca`: un Secret con `ca.crt`, que contenga la cadena de CA de PostgreSQL/RDS de confianza.
- Un repositorio ECR existente, un Secret de inserción
  `kubernetes.io/dockerconfigjson` vigente llamado `ecr-registry-credentials` y
  permiso para que los nodos extraigan la imagen.
- Una identidad de AWS para la carga de trabajo de los **Pods de Connect**, limitada al bucket/prefijo de S3 previsto. Configura Pod Identity o IRSA y valida la cadena de credenciales real del plugin. La identidad para compilar e insertar imágenes y la identidad de S3 en tiempo de ejecución son independientes.

Los tokens de autorización de ECR caducan después de 12 horas. Mantén/actualiza
el Secret de inserción antes de compilar. Asignar un rol de IRSA por sí solo no
garantiza que el generador de imágenes seleccionado pueda iniciar sesión en ECR.
Strimzi 1.3 compila imágenes de Connect únicamente con Buildah; comprueba los
requisitos del Pod de compilación en los nodos reales.

Guarda lo siguiente como `create-topics.py`, ejecútalo y aplica
`connect-topics.json`. La retención de datos de siete días es una elección para el
laboratorio; dimensiona la retención según los requisitos de interrupción y
recuperación antes de depender de este pipeline.

```python
import json
from pathlib import Path

topics = [
    ("connect-cluster-configs", 1, "compact"),
    ("connect-cluster-offsets", 3, "compact"),
    ("connect-cluster-status", 3, "compact"),
    ("orders-db.public.orders", 3, "delete"),
    ("orders-db.public.order_items", 3, "delete"),
]
items = []
for name, partitions, cleanup in topics:
    config = {"cleanup.policy": cleanup, "min.insync.replicas": 2}
    if cleanup == "delete":
        config["retention.ms"] = 604800000
    items.append({
        "apiVersion": "kafka.strimzi.io/v1", "kind": "KafkaTopic",
        "metadata": {"name": name, "namespace": "kafka",
                     "labels": {"strimzi.io/cluster": "my-cluster"}},
        "spec": {"partitions": partitions, "replicas": 3, "config": config},
    })
Path("connect-topics.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": items}, indent=2) + "\n")
```

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: connect-cluster
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: connect-cluster-
          patternType: prefix
        operations: [Read, Write, Create, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: orders-db.
          patternType: prefix
        operations: [Read, Write, Describe]
      - resource:
          type: group
          name: connect-cluster
          patternType: literal
        operations: [Read]
      - resource:
          type: group
          name: connect-orders-s3-sink
          patternType: literal
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

Guarda el recurso de usuario como `connect-user.yaml`. El permiso de creación
está limitado al prefijo de topics internos de Connect; los cinco topics se
crean previamente con ajustes explícitos mediante el operador Topic. La creación
automática de topics de datos de origen está deshabilitada. Las tablas/topics
adicionales requieren una actualización explícita correspondiente.

## Compilar y desplegar Connect

Guárdalo como `connect.yaml`. Ambos artefactos de plugin descargados tienen
sumas de comprobación SHA-512. `spec.build` es una opción admitida; una imagen
precompilada y probada o volúmenes de imágenes de plugins admitidos son otras
opciones. Una compilación correcta no demuestra que haya acceso a DB/S3.

El proveedor de configuración de directorio lee un Secret montado desde una ruta
permitida; no necesita permisos RBAC de lectura de Secrets de la API de Kubernetes.
Esto reemplaza el ejemplo incompleto `${secrets:...}`, que no tenía ni el proveedor
ni los permisos de acceso.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnect
metadata:
  name: connect-cluster
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 4.3.1
  replicas: 3
  bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9093
  groupId: connect-cluster
  configStorageTopic: connect-cluster-configs
  offsetStorageTopic: connect-cluster-offsets
  statusStorageTopic: connect-cluster-status
  tls:
    trustedCertificates:
      - secretName: my-cluster-cluster-ca-cert
        certificate: ca.crt
  authentication:
    type: scram-sha-512
    username: connect-cluster
    passwordSecret:
      secretName: connect-cluster
      password: password
  config:
    config.storage.replication.factor: 3
    offset.storage.replication.factor: 3
    status.storage.replication.factor: 3
    offset.flush.interval.ms: 60000
    topic.creation.enable: false
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    config.providers: dir
    config.providers.dir.class: org.apache.kafka.common.config.provider.DirectoryConfigProvider
    config.providers.dir.param.allowed.paths: /mnt/debezium
  template:
    pod:
      volumes:
        - name: debezium-credentials
          secret:
            secretName: debezium-db-credentials
        - name: rds-ca
          secret:
            secretName: rds-ca
    connectContainer:
      volumeMounts:
        - name: debezium-credentials
          mountPath: /mnt/debezium
          readOnly: true
        - name: rds-ca
          mountPath: /mnt/rds-ca
          readOnly: true
  build:
    output:
      type: docker
      image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/connect-cluster:kafka4.3.1-deb3.6.3-s3-3.4.3
      pushSecret: ecr-registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo.maven.apache.org/maven2/io/debezium/debezium-connector-postgres/3.6.3.Final/debezium-connector-postgres-3.6.3.Final-plugin.tar.gz
            sha512sum: 400495c485a1da532c5d7e2dcc3bbb1b7f7dcdbcdc74c82529309cb89a2c37298319ea45ea00414b3ce750a51ad01084e104725e810c55c1a7c1981baff201a0
      - name: aiven-s3
        artifacts:
          - type: zip
            url: https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/releases/download/v3.4.3/s3-sink-connector-for-apache-kafka-3.4.3.zip
            sha512sum: d355c7d41713dab83384a51e28b6670f63775a0aa394eb0d9e99172d862f53d9e42c54534369cdcfefadfeb4f50e7ffac2029c65dd878f0def3db33058627758
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
```

```bash
python3 create-topics.py
kubectl apply -f connect-topics.json -f connect-user.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/connect-cluster
kubectl -n kafka wait --for=condition=Ready --timeout=180s \
  kafkatopic/connect-cluster-configs kafkatopic/connect-cluster-offsets \
  kafkatopic/connect-cluster-status kafkatopic/orders-db.public.orders \
  kafkatopic/orders-db.public.order_items
kubectl apply -f connect.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=900s kafkaconnect/connect-cluster
```

Con `strimzi.io/use-connector-resources: "true"`, administra los cambios de los
conectores mediante los CR; los cambios directos a través de REST pueden ser
revertidos por la reconciliación. Restringe la API REST de Connect y los permisos
de actualización de Kubernetes. Todos los plugins de este despliegue de workers
comparten los Secrets montados y la identidad de carga de trabajo; aísla los
distintos dominios de confianza en despliegues de Connect diferentes.

## Origen CDC de PostgreSQL

Antes de aplicar `source.yaml`, habilita la replicación lógica de PostgreSQL y
configura los slots de replicación/emisores de WAL necesarios, el usuario de
replicación y los privilegios de tabla. En RDS PostgreSQL, habilitar el parámetro
de replicación lógica puede requerir un reinicio. Sigue el procedimiento de la
versión real del motor. Supervisa el WAL retenido: un slot detenido puede llenar
el almacenamiento. No elimines un slot como paso rutinario de reinicio.

El propietario autorizado de la tabla crea la publicación en la base de datos
`orders`:

```sql
CREATE PUBLICATION debezium_orders_pub
FOR TABLE public.orders, public.order_items;
```

Asegúrate de que las claves primarias/identidades de réplica sean adecuadas para
los eventos de actualización/eliminación que necesitas. El conector toma una
instantánea inicial y luego transmite WAL. El conector de PostgreSQL usa una sola
tarea; `tasksMax` es un máximo, no una garantía de paralelismo.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnector
metadata:
  name: orders-db-source
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.debezium.connector.postgresql.PostgresConnector
  tasksMax: 1
  config:
    database.hostname: orders-db.REPLACE.ap-northeast-2.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${dir:/mnt/debezium:password}"
    database.dbname: orders
    database.sslmode: verify-full
    database.sslrootcert: /mnt/rds-ca/ca.crt
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    publication.name: debezium_orders_pub
    publication.autocreate.mode: disabled
    table.include.list: 'public[.]orders,public[.]order_items'
    snapshot.mode: initial
```

La contraseña montada no se muestra en el manifiesto. Prueba la rotación de
credenciales y el comportamiento de reinicio/reconfiguración en lugar de suponer
que las conexiones existentes a la DB adoptan de inmediato un Secret modificado.

## Aiven S3 sink

Guárdalo como `sink.yaml`. La clase real del conector 3.4.3 es
`io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector`.
La clase del ejemplo antiguo `io.aiven.kafka.connect.s3.S3SinkConnector` no está
en ese artefacto. `flush.size` y `rotate.schedule.interval.ms` tampoco son claves
de configuración suyas; no deben copiarse de un conector S3 de otro proveedor.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnector
metadata:
  name: orders-s3-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector
  tasksMax: 3
  config:
    topics: orders-db.public.orders
    aws.s3.bucket.name: REPLACE-WITH-YOUR-BUCKET
    aws.s3.region: ap-northeast-2
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    format.output.type: jsonl
    format.output.fields: key,value,offset,timestamp
    file.compression.type: gzip
    file.max.records: 10000
```

Esto almacena **envolturas de eventos CDC**, incluidos la operación y los datos
anteriores/posteriores, no una tabla de estado actual materializada
automáticamente. El origen y el sink usan convertidores JSON con las envolturas de
esquema habilitadas. Mantén los ajustes de los convertidores coherentes con los
registros reales de Kafka. `file.max.records` controla la agrupación de registros,
y `offset.flush.interval.ms` del worker afecta el vaciado periódico; no promete
que cada objeto llegue dentro de un plazo fijo.

Se usa la cadena predeterminada de credenciales de AWS cuando no hay opciones de
credenciales explícitas. Concede las operaciones de objetos/multiparte que
requiere el plugin solo para el destino previsto y cualquier clave KMS necesaria.
Prueba eventos normales, eliminaciones, tombstones, reintentos y repetición tras
reinicio antes de tratar el archivo como origen de recuperación. Los objetos de
S3 no proporcionan automáticamente un comportamiento de exactamente una vez de
extremo a extremo.

```bash
kubectl apply -f source.yaml -f sink.yaml
kubectl -n kafka get kafkaconnector orders-db-source orders-s3-sink -o yaml
```

Inspecciona la generación actual, las condiciones, `status.connectorStatus.connector.state`
y el estado/trace de cada tarea. Comprueba también el progreso real del origen y
el destino. `Ready=True` es una observación del estado del operador, no una prueba
de que los datos estén actualizados.

## MirrorMaker 2 y recuperación ante desastres

MM2 conserva los bytes de los registros y los números de partición al escribir
nuevos offsets de destino. No conserva los números de offset de origen ni migra
automáticamente los ID del registro de esquemas, las transacciones de
aplicaciones, el estado de sinks externos o todas las políticas de seguridad.

| Componente | Responsabilidad y límite |
| --- | --- |
| MirrorSourceConnector | Copia registros y emite asignaciones de sincronización de offsets; la sincronización de topics/configuración/ACL depende de los ajustes |
| MirrorCheckpointConnector | Traduce offsets de grupos de origen y emite checkpoints; puede actualizar grupos de destino inactivos aptos |
| Apache MirrorHeartbeatConnector | Emite registros de heartbeat; su tarea puede hacerlo sin leer datos de origen, por lo que la presencia de heartbeats por sí sola no demuestra ni el estado del origen ni la replicación completa |

El modo activo-pasivo usa replicación unidireccional y un procedimiento explícito
de cambio. Si no se puede recuperar el origen, pueden perderse los registros que
no se hayan replicado antes del fallo. Los registros reproducidos pueden
duplicarse; la ventana de repetición no tiene por qué ser pequeña. Mide la
actualización de la replicación y de los checkpoints, bloquea a los antiguos
emisores, verifica los permisos y la disponibilidad del esquema en el destino,
cambia los endpoints de la aplicación/suscripciones a topics y prueba las
posiciones reanudadas. MM2 no realiza estos pasos de aplicación.

En el modo activo-activo, `DefaultReplicationPolicy` añade prefijos a los topics
remotos y detecta ciclos **de vuelta a un alias que ya está en su cadena de
origen**. No excluye todos los topics con prefijo: la replicación de varios saltos
a un tercer clúster puede ser legítima. `IdentityReplicationPolicy` pierde esa
información de nombres y no ofrece una protección equivalente contra bucles. Usa
filtros direccionales deliberados y define la propiedad; no es un sistema genérico
de resolución de conflictos para dos emisores.

## Ejemplo actual de KafkaMirrorMaker2 v1

Esta plantilla unidireccional requiere acceso de red/DNS entre clústeres en
funcionamiento, tres brokers de destino, los Secrets de origen/destino indicados
en el namespace `kafka` y ACL de Kafka preparados por separado. Las cadenas de
endpoints son marcadores de posición. Ejecuta los workers donde ambos clústeres
sean accesibles; `spec.target` selecciona el almacenamiento de Kafka, no una
región de Kubernetes.

| Identidad | Alcance necesario que se debe planificar |
| --- | --- |
| Origen | Leer/describir los topics seleccionados y describir los offsets de los grupos seleccionados |
| Destino | Conectarse a los topics internos y al grupo de workers; escribir/crear los topics remotos previstos y los topics internos de MM2; leer las asignaciones de offsets/checkpoints; actualizar los offsets de grupos seleccionados inactivos |

Crea previamente los topics internos con la compactación/particionado adecuados o
concede los derechos específicos de creación que requiera la configuración
seleccionada. Las credenciales de origen y destino pueden ser diferentes. Este
ejemplo almacena las sincronizaciones de offsets en el destino y deshabilita la
copia de ACL/configuración para que las políticas de destino se administren
explícitamente.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaMirrorMaker2
metadata:
  name: primary-to-dr
  namespace: kafka
spec:
  version: 4.3.1
  replicas: 3
  target:
    alias: dr-region
    bootstrapServers: dr-kafka-bootstrap.REPLACE.example.com:9093
    groupId: primary-to-dr
    configStorageTopic: primary-to-dr-configs
    offsetStorageTopic: primary-to-dr-offsets
    statusStorageTopic: primary-to-dr-status
    tls:
      trustedCertificates:
        - secretName: dr-cluster-ca-cert
          certificate: ca.crt
    authentication:
      type: scram-sha-512
      username: mm2-target
      passwordSecret:
        secretName: mm2-target
        password: password
    config:
      config.storage.replication.factor: 3
      offset.storage.replication.factor: 3
      status.storage.replication.factor: 3
  mirrors:
    - source:
        alias: us-east-1
        bootstrapServers: primary-kafka-bootstrap.REPLACE.example.com:9093
        tls:
          trustedCertificates:
            - secretName: primary-cluster-ca-cert
              certificate: ca.crt
        authentication:
          type: scram-sha-512
          username: mm2-source
          passwordSecret:
            secretName: mm2-source
            password: password
      sourceConnector:
        tasksMax: 5
        config:
          replication.factor: 3
          offset-syncs.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.topic.acls.enabled: false
          sync.topic.configs.enabled: false
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      checkpointConnector:
        config:
          checkpoints.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.group.offsets.enabled: true
          sync.group.offsets.interval.seconds: 60
          emit.checkpoints.interval.seconds: 60
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      topicsPattern: 'orders[.].*|payments[.].*'
      groupsPattern: 'orders-consumer-.*'
```

El patrón coincide con los prefijos `orders.` y `payments.`; no incluye
`orders`, `payments` ni `orders-db.public.orders` sin más. Adáptalo al inventario
real de topics. Los conectores de origen y de checkpoints deben coincidir en la
política de replicación, el separador y la ubicación de sincronización de offsets.

`sync.group.offsets.enabled=true` solo actualiza grupos de destino aptos
**inactivos/ausentes** con offsets traducibles; no sobrescribe un grupo que esté
consumiendo activamente. La pertenencia de consumidores, los permisos, la
disponibilidad de asignaciones/checkpoints y las posiciones de destino ya
confirmadas afectan al resultado. Nunca deduzcas que una conmutación por error ha
sido exitosa basándote únicamente en este ajuste o en una condición Ready del
operador.

## Red y supervisión

Para los workers de la región de destino, el tráfico de extracción desde el
origen hasta los workers cruza regiones. Comprimir el **productor de destino**
del worker no comprime retroactivamente ese tráfico de extracción; la compresión
del productor/topic de origen y la ubicación son importantes. Mide ambos tramos
de red, la CPU y la latencia en lugar de prometer un ahorro a partir de un solo
parámetro.

`replication-latency-ms` se mide cuando el destino confirma un registro, en
relación con la marca temporal del registro. El modo de marca temporal, la
reproducción histórica y la desviación del reloj influyen en esta métrica.
`record-age-ms` se observa en la ruta de lectura. Supervisa también el progreso
por partición, los errores, la frescura de los datos y la frescura de los
checkpoints; un flujo detenido o vacío puede producir muestras obsoletas o
ausentes. Los nombres de métricas de Prometheus dependen de las asignaciones del
exportador, por lo que un nombre de métrica de Kafka no es automáticamente un
nombre de PromQL.

## Referencias y validación

Los ejemplos se comprobaron con las CRD v1 publicadas y las definiciones nativas
de configuración de los conectores. Las comprobaciones locales del comportamiento
de MM2 no establecen que funcionen la conectividad real entre regiones, los
privilegios de la base de datos, las compilaciones de ECR, la entrega a S3 ni un
cambio satisfactorio para la recuperación ante desastres.

- [CRD de Strimzi 1.3.0: campos de recursos autoritativos](https://github.com/strimzi/strimzi-kafka-operator/tree/1.3.0/install/cluster-operator)
- [Guía de despliegue de Strimzi 1.3.0](https://strimzi.io/docs/operators/1.3.0/deploying.html)
- [Conector PostgreSQL de Debezium 3.6](https://debezium.io/documentation/reference/3.6/connectors/postgresql.html)
- [Conector S3 de Aiven 3.4.3](https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/blob/v3.4.3/s3-sink-connector/README.md)
- [Duración del token de autorización de ECR](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_GetAuthorizationToken.html)
- [MirrorSourceConnector de Kafka 4.3.1](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceConnector.java)
- [MirrorCheckpointTask de Kafka 4.3.1](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorCheckpointTask.java)
- [MirrorHeartbeatTask de Kafka 4.3.1](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorHeartbeatTask.java)
- [MirrorSourceTask de Kafka 4.3.1](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceTask.java)

## Próximos pasos

[Parte 6: integración con MSK](./06-msk-integration.md) compara las opciones administradas.

[Volver a la página principal](./README.md)

## Cuestionario

[Cuestionario sobre topics](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
