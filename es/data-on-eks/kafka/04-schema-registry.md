# Part 4: Schema Registry

> **Supported Versions**: Karapace 4.x, Apicurio Registry 3.x, Confluent Schema Registry (compatible API)\
> **Última actualización**: July 9, 2026

## Why You Need a Schema Registry

Kafka en sí trata cada mensaje como un arreglo de bytes opaco. No le importa qué formato escribe un producer en ese arreglo. El problema es que producers y consumers suelen ser aplicaciones separadas, propiedad de equipos distintos y desplegadas en calendarios diferentes. En el momento en que un producer añade un campo o cambia un tipo, cualquier consumer que no conozca el cambio falla al deserializar el mensaje o lee un valor corrupto.

### The Problem with Schema-less JSON

```json
{"orderId": "ORD-1001", "amount": 42.5, "currency": "USD"}
```

Los payloads JSON sin procesar como este son legibles por humanos, pero tienen costos reales:

* **No enforced contract**: nada impide que un producer convierta silenciosamente `amount` en una cadena.
* **Validation only at runtime**: los campos faltantes o las incompatibilidades de tipos solo aparecen cuando un consumer intenta analizar el payload.
* **Payload size**: los nombres de campos se repiten en cada mensaje, lo que es más grande que un formato binario y se convierte en un costo real de red/almacenamiento con alto throughput.
* **No version history**: no hay forma de responder "¿cómo se veía la versión 3 del schema de este topic?"

### What a Schema Registry Solves

Un schema registry es un servicio separado que almacena y versiona de forma centralizada schemas para formatos estructurados como Avro, Protobuf y JSON Schema, y aplica reglas de compatibilidad entre versiones. El flujo se ve aproximadamente así:

1. Antes de enviar un mensaje, el producer registra (o busca) su schema en el registry.
2. El registry devuelve un schema ID, y el producer serializa el payload solo con ese ID antepuesto (normalmente un encabezado de 5 bytes con magic byte + ID) en lugar del schema completo.
3. El consumer lee el schema ID incrustado en el mensaje, obtiene el schema correspondiente desde el registry y deserializa en consecuencia.
4. Cuando se registra una nueva versión del schema, el registry la compara con las reglas de compatibilidad y rechaza directamente el registro si las infringe.

Esto permite que producers y consumers evolucionen de forma independiente **sin conocer los calendarios de despliegue del otro**. También significa que el payload en la red solo lleva un schema ID, por lo que la codificación binaria de Avro/Protobuf es dramáticamente más pequeña que JSON.

## Comparing the Major Implementations

| | Karapace | Apicurio Registry | Confluent Schema Registry |
| --- | --- | --- | --- |
| **Vendor** | Aiven | Red Hat | Confluent |
| **License** | Apache License 2.0 | Apache License 2.0 | Confluent Community License (not fully open source since 2018) |
| **Supported formats** | Avro, JSON Schema | Avro, Protobuf, JSON Schema, OpenAPI, AsyncAPI, GraphQL, Kafka Connect schemas, etc. | Avro, Protobuf, JSON Schema |
| **API compatibility** | Compatible with the Confluent REST API | Confluent-compatible mode (`ccompat`) | The original API (de facto standard) |
| **Storage backend** | Kafka topic | Kafka topic or SQL (e.g. PostgreSQL) | Kafka topic |
| **Bundled REST Proxy** | Yes (Karapace REST Proxy) | No (registry only) | Separate commercial REST Proxy |
| **Commercial support terms** | Via Aiven's managed service, or community | Via Red Hat subscription | Requires Confluent Platform licensing at scale |
| **Fit for EKS/Strimzi** | Strong — pure open source, lightweight | Strong — multi-format, multi-backend | Needs a license review |

**Para un stack EKS + Strimzi autogestionado, recomendamos Karapace o Apicurio Registry.** Ambos se distribuyen bajo la licencia Apache-2.0, sin restricciones de redistribución o modificación. En cambio, la Confluent Community License de Confluent Schema Registry prohíbe explícitamente ofrecerlo como un servicio gestionado competidor; no ha sido completamente open source desde 2018. Las bibliotecas del lado cliente como `kafka-avro-serializer` todavía las publica Confluent, pero como la REST API es compatible, apuntar `schema.registry.url` a Karapace o Apicurio en su lugar suele funcionar sin cambios de código.

## Serialization Formats

### Avro

Avro define su schema como JSON y serializa los datos en un formato binario compacto. Es el formato más usado en el ecosistema Kafka, y su característica más destacada es **schema resolution**: el **writer schema** (usado cuando se escribieron los datos) y el **reader schema** (usado al leerlos de vuelta) no tienen que coincidir exactamente; Avro resuelve las diferencias según reglas bien definidas.

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example.orders",
  "fields": [
    { "name": "orderId", "type": "string" },
    { "name": "customerId", "type": "string" },
    { "name": "amount", "type": "double" },
    { "name": "currency", "type": "string", "default": "USD" },
    { "name": "createdAt", "type": "long", "logicalType": "timestamp-millis" }
  ]
}
```

### Protobuf

Los schemas de Protobuf se definen en archivos `.proto` y se compilan con `protoc` para generar código en cada lenguaje de destino. Igual que Avro, produce codificaciones binarias compactas, pero asigna números de campo explícitos y tiene un sistema de tipos más estricto, lo que tiende a producir código generado de mayor calidad entre lenguajes. La adopción de Protobuf en el ecosistema Kafka ha estado creciendo de forma constante.

```protobuf
syntax = "proto3";

package com.example.orders;

message Order {
  string order_id = 1;
  string customer_id = 2;
  double amount = 3;
  string currency = 4;
  int64 created_at = 5;
}
```

### JSON Schema

JSON Schema define reglas de validación para los propios payloads JSON. Es legible por humanos y fácil de depurar, pero como los nombres de campos se repiten en cada mensaje, los payloads terminan siendo mucho más grandes que Avro o Protobuf. Encaja en workloads que necesitan validación de schema pero son menos sensibles al throughput o al costo de almacenamiento.

### Comparing the Three Formats

| | Avro | Protobuf | JSON Schema |
| --- | --- | --- | --- |
| Schema definition | JSON | `.proto` IDL | JSON Schema |
| Payload size | Small | Small | Large |
| Human-readable | Schema only | Schema only | Payload too |
| Cross-language codegen | Good | Excellent | Good |
| Kafka ecosystem adoption | Very high | High (growing) | Moderate |
| Schema evolution rules | Writer/reader resolution | Field-number based | JSON Schema validation rules |

## Compatibility Strategies

Cuando se registra una nueva versión de schema, el registry la compara con la versión anterior según el modo de compatibilidad configurado. Acertar con estos cuatro modos importa: este es el concepto que con más frecuencia se confunde en la gestión de schemas.

| Mode | Meaning | Deployment order |
| --- | --- | --- |
| **BACKWARD** | A reader using the **new** schema must be able to read data written with the **old** schema | Upgrade **consumers** first |
| **FORWARD** | A reader using the **old** schema must be able to read data written with the **new** schema | Upgrade **producers** first |
| **FULL** | Both BACKWARD and FORWARD hold | Either order is safe |
| **NONE** | No compatibility checking | Manual coordination required |

La parte que la gente suele invertir con más frecuencia:

* **BACKWARD** significa "el schema nuevo (como reader) puede leer datos antiguos". En la práctica, eso significa que puedes **desplegar primero el consumer con el schema nuevo** de forma segura; incluso mientras los producers siguen escribiendo con el schema antiguo, el consumer actualizado lo lee bien.
* **FORWARD** significa "el schema antiguo (como reader) puede leer datos nuevos". Eso significa que puedes **actualizar primero los producers al schema nuevo** de forma segura; los consumers que todavía ejecutan el schema antiguo siguen funcionando.

### Example of a Backward-Compatible Change

Añadir un campo opcional con un valor predeterminado al schema `Order` es compatible con BACKWARD:

```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

Un consumer que usa el schema nuevo leyendo datos antiguos (que carecen de este campo) simplemente obtiene el valor `default` (`null`), sin fallos.

### Examples of Breaking Changes

Estas son violaciones clásicas de compatibilidad BACKWARD:

* **Adding a required field without a default**: añadir un nuevo campo `discount_code` sin valor predeterminado significa que un reader con el schema nuevo espera el campo en datos antiguos que nunca lo tuvieron, y falla. (A la inversa, *eliminar* un campo es compatible con BACKWARD pero rompe FORWARD en su lugar: un reader con el schema antiguo seguiría esperando que el campo ahora eliminado sea obligatorio en los datos nuevos.)
* **Changing a field's type**: cambiar `amount` de `double` a `string` significa que los datos existentes codificados en binario ya no pueden decodificarse como el tipo nuevo.
* **Renaming a field** (without an alias): el reader busca el campo con su nombre nuevo, pero los datos antiguos solo lo tienen con el nombre antiguo.

## Deploying on Strimzi/EKS

### Deploying Apicurio Registry (Kafka-Topic Storage)

Suponiendo que ya se está ejecutando un cluster de Kafka gestionado por Strimzi, puedes desplegar Apicurio Registry como un Deployment en el mismo namespace, respaldado por un motor de almacenamiento de Kafka topic.

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
      containers:
        - name: apicurio-registry
          image: quay.io/apicurio/apicurio-registry:3.0.6
          ports:
            - containerPort: 8080
          env:
            - name: APICURIO_STORAGE_KIND
              value: "kafkasql"
            - name: APICURIO_KAFKASQL_BOOTSTRAP_SERVERS
              value: "my-kafka-cluster-kafka-bootstrap.kafka.svc:9092"
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
    - port: 8080
      targetPort: 8080
```

Apicurio también admite un backend SQL (`APICURIO_STORAGE_KIND=sql`) en lugar de `kafkasql`, así que si ya ejecutas una instancia de PostgreSQL/RDS, puedes apuntar el registry allí en su lugar. Karapace, por el contrario, siempre almacena schemas en un Kafka topic (`_schemas`) y no necesita configuración de backend separada.

### Registering a Schema

Una vez que el registry está en ejecución, los schemas se registran a través de su REST API (usando el endpoint compatible con Confluent):

```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

### Client Configuration

Las aplicaciones producer/consumer de Kafka apuntan su serializer a la URL del registry:

```properties
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6
```

La misma clase `KafkaAvroSerializer` también funciona contra Karapace: solo apunta `schema.registry.url` al endpoint REST de Karapace (puerto 8081 por defecto). El código de la aplicación no necesita cambiar cuando intercambias implementaciones de registry, que es exactamente el valor que proporciona la API compatible con Confluent.

## What's Next

Esta parte cubrió cómo un schema registry mantiene seguro el contrato de datos entre producers y consumers mientras ambos evolucionan de forma independiente. La Part 5 pasa a Kafka Connect y MirrorMaker: integrarse con sistemas externos y replicar datos entre clusters.

[Volver a la página principal](./)

## Quiz

Para probar lo que has aprendido en este capítulo, intenta el [cuestionario del tema](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md).
