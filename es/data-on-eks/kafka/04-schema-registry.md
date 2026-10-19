# Parte 4: Registro de esquemas

> **Base de revisión**: Karapace 6.2.4, Apicurio Registry 3.3.3, Strimzi 1.3.0 / Kafka 4.3.1\
> **Última revisión**: 16 de octubre de 2026

## ¿Por qué usar un registro de esquemas?

Kafka almacena las claves y los valores de los registros como bytes. Por lo tanto,
un productor y un consumidor pueden no estar de acuerdo sobre la estructura o el
significado de un valor. No toda incorporación de un campo rompe un consumidor:
el resultado depende de la codificación, del lector y de las reglas de compatibilidad.

Un registro crea versiones de los esquemas y comprueba las reglas de compatibilidad
configuradas cuando se registran esquemas. Las aplicaciones deben usar los
serializadores correspondientes y las rutas de validación. Un registro no inspecciona
automáticamente todos los registros de Kafka ni aplica reglas de negocio, como el
significado de una moneda o una marca de tiempo.

JSON también puede tener un contrato: JSON Schema, las comprobaciones de CI y las
especificaciones con control de versiones son posibles tanto con un registro como
sin él. Un registro central ayuda a distribuir y gobernar ese contrato; la
codificación binaria es una decisión independiente. Compare los registros medidos y comprimidos antes de afirmar que se ahorrará espacio en la carga útil o en el almacenamiento.

### ¿Qué se transmite en un registro?

Con el **encuadre de carga útil con ID de esquema** habitual de Confluent, un valor
comienza con un byte mágico y un ID de esquema de cuatro bytes: cinco bytes en total,
seguidos del valor codificado. La variante Protobuf también incluye índices de
mensajes. Los serializadores JSON Schema siguen codificando el valor como JSON.
Otros modos de serializador, los identificadores basados en encabezados y las
codificaciones nativas de Apicurio requieren su propia configuración.

El serializador registra o busca un esquema, y el deserializador recupera el esquema
del escritor mediante su identificador. Normalmente, los clientes almacenan los
esquemas en caché, así que no necesariamente se realiza una solicitud HTTP por cada
registro. Aun así, una caché vacía o un esquema nuevo pueden requerir el registro.
Conserve la correspondencia entre ID y esquema mientras los datos de Kafka
correspondientes, los archivos y las copias de recuperación ante desastres deban
seguir siendo legibles.

## Comparación de implementaciones

| Implementación | Formatos de esquema pertinentes | API y almacenamiento |
| --- | --- | --- |
| Karapace 6.2.4 | Avro, JSON Schema, **Protobuf** | API REST compatible con Confluent; almacenamiento de esquemas respaldado por Kafka; también proporciona un proxy REST |
| Apicurio Registry 3.3.3 | Avro, Protobuf, JSON Schema; tipos de artefactos adicionales | API nativa y `/apis/ccompat/v7` y `/apis/ccompat/v8`; opciones de almacenamiento KafkaSQL y SQL |
| Confluent Schema Registry | Avro, Protobuf, JSON Schema | API de Confluent; almacenamiento respaldado por Kafka en la implementación autogestionada |

Karapace y Apicurio publican licencias Apache-2.0. Esa licencia tiene condiciones,
incluida la conservación de los avisos requeridos; no significa «sin restricciones».
El repositorio de Confluent distingue los módulos de servidor con licencia Community
de los módulos de cliente/Avro con licencia Apache-2.0. Compruebe la licencia del
componente real y cualquier contrato de soporte, en lugar de inferir las condiciones
comerciales a partir del tamaño del clúster.

La compatibilidad de API es útil, pero **cambiar solo la URL no es un plan de migración**.
Pruebe los ID de esquema, las referencias, la nomenclatura de sujetos, la autenticación,
las versiones de cliente y la codificación en el cable con los registros conservados.
Por ejemplo, la API de compatibilidad de Apicurio no implementa todas las funciones
de exportación/cifrado de Confluent; aceptar un campo opcional de una solicitud no
significa necesariamente aplicar sus reglas.
Que Apicurio pueda almacenar un tipo de artefacto no significa que todos los
serializadores de Kafka lo admitan automáticamente. Karapace también necesita
configuración de broker, autenticación y tema de esquemas; que esté respaldado por
Kafka no significa que no requiera configuración.

## Formatos de serialización

### Avro

Guarde el siguiente ejemplo canónico como `order.avsc`. Avro resuelve un esquema
escritor frente a un esquema lector mediante nombres, valores predeterminados,
alias y promociones de tipos definidas. El `logicalType` de la marca de tiempo
pertenece dentro de su **objeto de tipo**, no junto al `name` del campo. Un atributo
de campo mal ubicado puede analizarse correctamente y, aun así, no declarar una
marca de tiempo lógica.

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example.orders",
  "fields": [
    {
      "name": "orderId",
      "type": "string"
    },
    {
      "name": "customerId",
      "type": "string"
    },
    {
      "name": "amount",
      "type": "double"
    },
    {
      "name": "currency",
      "type": "string",
      "default": "USD"
    },
    {
      "name": "createdAt",
      "type": {
        "type": "long",
        "logicalType": "timestamp-millis"
      }
    }
  ]
}
```

Aquí, `amount` es solo un valor ilustrativo de tipo double. Un contrato real debe
definir las unidades, la precisión y el redondeo; cuando se requieran importes
decimales exactos, utilice una representación adecuada de entero o decimal.

### Protobuf y JSON Schema

Protobuf usa campos numerados y API de generación/ejecución específicas de cada
lenguaje. Defina explícitamente la unidad de tiempo; `int64` por sí solo no declara
una marca de tiempo lógica. No reutilice números de campos eliminados; reserve los
números y nombres eliminados según corresponda.

```protobuf
syntax = "proto3";
package com.example.orders;

message Order {
  string order_id = 1;
  string customer_id = 2;
  double amount = 3;
  string currency = 4;
  int64 created_at_millis = 5;
}
```

JSON Schema valida JSON. La compatibilidad con versiones del borrador y el análisis
de compatibilidad varían según el registro; admitir la validación no implica un
análisis completo de la evolución para todas las palabras clave. Son contratos
distintos, no codificaciones intercambiables.

| Formato | Representación en el cable | Consideraciones de evolución |
| --- | --- | --- |
| Avro | Binaria, con interpretación del esquema escritor | Resolución lector/escritor, valores predeterminados, nombres y promociones |
| Protobuf | Binaria, con campos numerados | Conserve los números de campo y los tipos de cable; compruebe la semántica de la aplicación |
| JSON Schema | JSON | Conjuntos de instancias aceptadas, campos obligatorios, propiedades adicionales y compatibilidad con borradores |

## Compatibilidad y orden de implementación

En la API compatible con Confluent, configure la compatibilidad en el nivel de
**sujeto** (o herede un valor predeterminado global). Con la estrategia
`TopicNameStrategy` predeterminada, los valores del tema `orders` usan el sujeto
`orders-value`; otras estrategias pueden compartir un sujeto entre temas o separar
tipos de registros dentro de un tema.

| Modo | Relación requerida | Despliegue habitual del esquema |
| --- | --- | --- |
| BACKWARD | El lector nuevo puede leer los datos del escritor anterior | Primero los consumidores |
| FORWARD | El lector anterior puede leer los datos del escritor nuevo | Primero los productores |
| FULL | Ambas direcciones | Cualquiera de los dos órdenes para la relación de esquemas comprobada |
| NONE | No se comprueba la compatibilidad | Coordine y pruebe explícitamente |

Los modos no transitivos comparan con la versión anterior más reciente. Sus variantes
`_TRANSITIVE` comparan con todas las versiones anteriores. Para reproducir registros
antiguos conservados, comprobar solo la versión más reciente puede ser insuficiente.
`FULL` no garantiza la semántica de negocio, el comportamiento de la aplicación ni
la compatibilidad con todas las versiones históricas; `FULL_TRANSITIVE` amplía la
comparación de esquemas, no esa garantía.

En Avro, añadir este campo permite que un lector nuevo proporcione `null` para los
registros antiguos:

```json
{"name":"discountCode","type":["null","string"],"default":null}
```

El valor predeterminado es una regla de **resolución del lector**, no un permiso para
que un escritor omita un campo obligatorio cualquiera.

| Cambio de Avro | Condición importante |
| --- | --- |
| Añadir un campo sin un valor predeterminado para el lector | El lector nuevo no puede leer los registros antiguos que carezcan de ese campo |
| Eliminar un campo | Compatible con versiones anteriores; la compatibilidad con versiones posteriores depende de si el lector antiguo tiene un valor predeterminado |
| Cambiar `double` a `string` | Incompatible; no es una promoción numérica de Avro |
| Cambiar `int` a `long` | El lector nuevo puede aceptar valores enteros antiguos; la dirección inversa es distinta |
| Cambiar el nombre de un campo | Un alias del lector o un valor predeterminado aplicable pueden cambiar el resultado; pruebe ambas direcciones |

Ejecute pruebas de lector/escritor con datos históricos representativos además de
usar el endpoint de compatibilidad del registro. Permiten detectar clases distintas
de fallos.

## Desplegar Apicurio con la base de Strimzi

Este es un **despliegue para un laboratorio privado**, no un registro público
autenticado.
Presupone el `my-cluster` de [la Parte 2](./02-strimzi-operator.md) en el espacio
de nombres `kafka`, tres brokers, los operadores Topic/User y el listener TLS/SCRAM
en el puerto 9093.
La API HTTP siguiente no tiene autenticación de aplicaciones. NetworkPolicy permite
el puerto 8080 solo desde Pods etiquetados en el mismo espacio de nombres cuando el
CNI aplica NetworkPolicy. Restrinja quién puede crear o etiquetar esos Pods. Para
un uso compartido en producción, configure por separado TLS, autenticación y
autorización para la API, sin depender de SASL de Kafka; un Service interno por sí
solo no proporciona esos controles.

### Temas de almacenamiento e identidad de Kafka

Guarde el archivo como `registry-storage.yaml`. La identidad de la aplicación lee
y escribe únicamente en sus tres temas designados y en el prefijo de su grupo de
consumidores. El Topic Operator crea los temas de antemano, por lo que la aplicación
no necesita permisos para crear temas.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: kafkasql-journal
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: kafkasql-snapshots
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: registry-events
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: apicurio-registry
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
          name: kafkasql-journal
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: kafkasql-snapshots
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: registry-events
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: group
          name: apicurio-registry-
          patternType: prefix
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

KafkaSQL 3.3.3 inicializa los temas de journal, snapshots y eventos. De forma
predeterminada, las comprobaciones de los temas de journal y snapshots requieren
`cleanup.policy=delete`, `retention.ms=-1` y `retention.bytes=-1`. No les aplique
una receta genérica de compactación de `_schemas` ni una retención normal de eventos
de siete días. Esto conserva los registros indefinidamente, así que supervise el
crecimiento del disco y planifique copias de seguridad y limpieza que se hayan probado.

KafkaSQL reconstruye el estado SQL local a partir del journal y de cualquier
snapshot disponible. El tema de snapshots contiene **rutas a archivos de snapshot**,
no los archivos de snapshot completos. Este laboratorio deshabilita los snapshots
programados y conserva el journal completo; si se pierde un Pod, habrá que reproducir
los datos y el inicio podría tardar mucho. El almacenamiento compartido y duradero
para snapshots, las copias de seguridad, la restauración y el truncamiento del
journal requieren un diseño de recuperación aparte.
El prefijo del grupo se puede configurar, pero un `group.id` fijo no sirve para
conservar el estado de KafkaSQL: esta versión genera grupos únicos para asegurar
que se reproduzcan los datos al iniciar.

### Deployment y Service

Guarde el archivo como `registry.yaml`. Los valores de CA y JAAS provienen de
Secrets de Strimzi.
La verificación del nombre de host está habilitada de forma explícita. El tamaño de los
recursos y el margen de inicio de diez minutos son valores iniciales para el
laboratorio; mida el uso de memoria y el tiempo de reproducción.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apicurio-registry
  namespace: kafka
spec:
  replicas: 1
  selector:
    matchLabels:
      app: apicurio-registry
  template:
    metadata:
      labels:
        app: apicurio-registry
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: registry
          image: quay.io/apicurio/apicurio-registry:3.3.3
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          ports:
            - name: http
              containerPort: 8080
            - name: management
              containerPort: 9000
          env:
            - name: APICURIO_STORAGE_KIND
              value: kafkasql
            - name: APICURIO_KAFKASQL_BOOTSTRAP_SERVERS
              value: my-cluster-kafka-bootstrap.kafka.svc:9093
            - name: APICURIO_KAFKASQL_TOPIC_AUTO_CREATE
              value: "false"
            - name: APICURIO_KAFKASQL_CONSUMER_GROUP_PREFIX
              value: apicurio-registry-
            - name: APICURIO_KAFKASQL_SNAPSHOT_SCHEDULED_ENABLED
              value: "false"
            - name: APICURIO_KAFKA_COMMON_SECURITY_PROTOCOL
              value: SASL_SSL
            - name: APICURIO_KAFKA_COMMON_SASL_MECHANISM
              value: SCRAM-SHA-512
            - name: APICURIO_KAFKA_COMMON_SASL_JAAS_CONFIG
              valueFrom:
                secretKeyRef:
                  name: apicurio-registry
                  key: sasl.jaas.config
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_TYPE
              value: PKCS12
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_LOCATION
              value: /etc/kafka-ca/ca.p12
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: my-cluster-cluster-ca-cert
                  key: ca.password
            - name: APICURIO_KAFKA_COMMON_SSL_ENDPOINT_IDENTIFICATION_ALGORITHM
              value: HTTPS
          volumeMounts:
            - name: kafka-ca
              mountPath: /etc/kafka-ca
              readOnly: true
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          startupProbe:
            httpGet:
              path: /health/ready
              port: management
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            httpGet:
              path: /health/ready
              port: management
          livenessProbe:
            httpGet:
              path: /health/live
              port: management
      volumes:
        - name: kafka-ca
          secret:
            secretName: my-cluster-cluster-ca-cert
            items:
              - key: ca.p12
                path: ca.p12
---
apiVersion: v1
kind: Service
metadata:
  name: apicurio-registry
  namespace: kafka
spec:
  selector:
    app: apicurio-registry
  ports:
    - name: http
      port: 8080
      targetPort: http
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: apicurio-registry-ingress
  namespace: kafka
spec:
  podSelector:
    matchLabels:
      app: apicurio-registry
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              docs.example.com/registry-client: "true"
      ports:
        - protocol: TCP
          port: 8080
```

```bash
kubectl apply -f registry-storage.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s \
  kafkatopic/kafkasql-journal kafkatopic/kafkasql-snapshots kafkatopic/registry-events \
  kafkauser/apicurio-registry
kubectl apply -f registry.yaml
kubectl -n kafka rollout status deployment/apicurio-registry --timeout=600s
kubectl -n kafka port-forward --address=127.0.0.1 service/apicurio-registry 8080:8080
```

El reenvío de puertos requiere acceso a Kubernetes y permanece en primer plano.
Reinicie la carga de trabajo después de cambiar las variables de entorno respaldadas
por Secrets. Para el almacenamiento SQL, `APICURIO_STORAGE_KIND=sql` por sí solo
no configura PostgreSQL: seleccione el tipo SQL y proporcione una base de datos
dedicada, TLS, credenciales y procedimientos de recuperación. La base de datos H2
en memoria predeterminada no es un almacenamiento de producción duradero.

## Registre el mismo esquema que usa la aplicación

Desde otra terminal, registre `order.avsc` con el sujeto `orders-value`. Así se
evita la antigua discrepancia entre un ejemplo con espacio de nombres y varios
campos y un esquema distinto de un solo campo oculto en una cadena de curl. La
primera solicitud configura explícitamente la compatibilidad del sujeto; los
errores HTTP hacen que curl devuelva un código de salida distinto de cero.

```bash
# Run from a directory containing the order.avsc above.
# Keep kubectl port-forward running in a separate terminal.
REGISTRY_URL="http://127.0.0.1:8080/apis/ccompat/v7"
python3 - <<'PY'
import json
from pathlib import Path
schema = json.loads(Path("order.avsc").read_text())
Path("register-order.json").write_text(json.dumps({
    "schemaType": "AVRO",
    "schema": json.dumps(schema)
}) + "\n")
PY
curl --fail-with-body --silent --show-error \
  -X PUT "$REGISTRY_URL/config/orders-value" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data-binary '{"compatibility":"BACKWARD_TRANSITIVE"}'
curl --fail-with-body --silent --show-error \
  -X POST "$REGISTRY_URL/subjects/orders-value/versions" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data-binary @register-order.json
curl --fail-with-body --silent --show-error \
  "$REGISTRY_URL/subjects/orders-value/versions/latest"
```

## Configuración del productor y el consumidor

Estas son propiedades **adicionales** para aplicaciones ya configuradas con la
dirección del broker de la Parte 2, la confianza TLS y sus propias identidades de
Kafka. Las credenciales HTTP del registro y las credenciales SASL de Kafka son
independientes. Incluya en la aplicación una dependencia del serializador Avro de
Confluent compatible y con la versión fijada; no se proporciona simplemente por
instalar Kafka o Strimzi.

Productor:

```properties
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v7
auto.register.schemas=false
```

Consumidor:

```properties
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v7
specific.avro.reader=false
```

El ejemplo de productor requiere que el esquema correspondiente esté registrado
primero.
Con `specific.avro.reader=false`, los consumidores usan registros Avro genéricos;
las clases SpecificRecord generadas requieren el código correspondiente y la
configuración del lector. La estrategia de sujetos predeterminada presupone que el
tema de Kafka de la aplicación es `orders`.

Antes de cambiar de registro, pruebe un consumidor con la caché vacía frente a los
registros conservados, el registro de una nueva versión, el rechazo por
incompatibilidad, las referencias de esquemas y el reinicio/la recuperación.
Conserve la correspondencia original entre ID de esquema y esquema o realice una
migración explícita y compatible de datos/identificadores. Una comprobación HTTP de
estado satisfactoria no es una prueba de serialización.

## Referencias y validación

Los ejemplos de este capítulo se comprobaron con la configuración de las versiones
fijadas y los esquemas de Strimzi/Kubernetes, además de con pruebas locales de
lector/escritor de Avro. Esas comprobaciones no sustituyen el despliegue de la
imagen, la conexión con el broker TLS real ni la prueba de la versión exacta del
serializador de la aplicación.

- [Especificación de Apache Avro](https://avro.apache.org/docs/1.12.0/specification/)
- [Protocol Buffers: actualizar un tipo de mensaje](https://protobuf.dev/programming-guides/proto3/#updating)
- [Reglas de compatibilidad de Confluent](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- [Serializadores y formato en el cable de Confluent](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html)
- [Karapace 6.2.4](https://github.com/Aiven-Open/karapace/tree/6.2.4)
- [Apicurio Registry 3.3.3](https://github.com/Apicurio/apicurio-registry/tree/3.3.3)
- [Matriz de compatibilidad con la API de Apicurio](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/ccompat/rest/README.md)
- [Configuración de KafkaSQL de Apicurio](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/kafkasql/KafkaSqlConfiguration.java)
- [Verificación de la configuración de temas de Apicurio](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/util/KafkaAdminUtil.java)
- [Licencias de los componentes de Confluent](https://github.com/confluentinc/schema-registry/blob/master/LICENSE)

## Qué sigue

[La Parte 5](./05-kafka-connect-mirrormaker.md) trata las integraciones externas y
la replicación entre clústeres. El almacenamiento de esquemas y la migración de ID
deben considerarse junto con la replicación de registros.

[Volver a la página principal](./README.md)

## Cuestionario

[Cuestionario del tema](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
