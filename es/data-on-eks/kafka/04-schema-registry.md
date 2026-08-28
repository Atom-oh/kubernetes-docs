# Parte 4: Schema Registry

> **Versiones compatibles**: Karapace 4.x, Apicurio Registry 3.x, Confluent Schema Registry (API compatible)\
> **Última actualización**: July 9, 2026

## Por qué necesita un Schema Registry

Kafka en sí trata cada mensaje como un arreglo de bytes opaco. No le importa qué formato escribe un producer en ese arreglo. El problema es que los producers y consumers suelen ser aplicaciones independientes, propiedad de equipos distintos e implementadas con calendarios diferentes. En el momento en que un producer agrega un campo o cambia un tipo, cualquier consumer que desconozca el cambio no logra deserializar el mensaje o lee un valor corrupto.

### El problema con JSON sin esquema

```json
{"orderId": "ORD-1001", "amount": 42.5, "currency": "USD"}
```

Las cargas útiles JSON sin procesar como esta son legibles para las personas, pero conllevan costos reales:

* **Sin contrato aplicado**: nada impide que un producer convierta silenciosamente `amount` en una cadena.
* **Validación solo en tiempo de ejecución**: los campos ausentes o las discrepancias de tipo solo aparecen cuando un consumer intenta analizar la carga útil.
* **Tamaño de la carga útil**: los nombres de los campos se repiten en cada mensaje, lo que es mayor que un formato binario y se convierte en un costo real de red/almacenamiento con un alto rendimiento.
* **Sin historial de versiones**: no hay forma de responder «¿cómo era la versión 3 del esquema de este topic?».

### Qué resuelve un Schema Registry

Un schema registry es un Service independiente que almacena centralmente y versiona esquemas para formatos estructurados como Avro, Protobuf y JSON Schema, y aplica reglas de compatibilidad entre versiones. El flujo es aproximadamente así:

1. Antes de enviar un mensaje, el producer registra (o busca) su esquema en el registry.
2. El registry devuelve un ID de esquema y el producer serializa la carga útil con solo ese ID antepuesto (normalmente un encabezado de 5 bytes de magic-byte + ID) en lugar del esquema completo.
3. El consumer lee el ID de esquema incrustado en el mensaje, obtiene el esquema correspondiente del registry y deserializa en consecuencia.
4. Cuando se registra una nueva versión del esquema, el registry la verifica con respecto a las reglas de compatibilidad y rechaza directamente el registro si las infringe.

Esto permite que producers y consumers evolucionen de forma independiente **sin conocer los calendarios de implementación de los demás**. También significa que la carga útil en tránsito solo lleva un ID de esquema, por lo que la codificación binaria Avro/Protobuf es considerablemente menor que JSON.

## Comparación de las principales implementaciones

| | Karapace | Apicurio Registry | Confluent Schema Registry |
| --- | --- | --- | --- |
| **Proveedor** | Aiven | Red Hat | Confluent |
| **Licencia** | Apache License 2.0 | Apache License 2.0 | Confluent Community License (no es completamente open source desde 2018) |
| **Formatos compatibles** | Avro, JSON Schema | Avro, Protobuf, JSON Schema, OpenAPI, AsyncAPI, GraphQL, esquemas de Kafka Connect, etc. | Avro, Protobuf, JSON Schema |
| **Compatibilidad de API** | Compatible con la Confluent REST API | Modo compatible con Confluent (`ccompat`) | La API original (estándar de facto) |
| **Backend de almacenamiento** | Kafka topic | Kafka topic o SQL (p. ej., PostgreSQL) | Kafka topic |
| **REST Proxy incluido** | Sí (Karapace REST Proxy) | No (solo registry) | REST Proxy comercial independiente |
| **Términos de soporte comercial** | Mediante el Service administrado de Aiven o la comunidad | Mediante suscripción de Red Hat | Requiere licencia de Confluent Platform a escala |
| **Adecuación para EKS/Strimzi** | Alta — totalmente open source, ligero | Alta — múltiples formatos y backends | Requiere revisar la licencia |

**Para una pila EKS + Strimzi autoadministrada, recomendamos Karapace o Apicurio Registry.** Ambos se distribuyen bajo la licencia Apache-2.0 sin restricciones para redistribución o modificación. Por el contrario, la Confluent Community License de Confluent Schema Registry prohíbe explícitamente ofrecerlo como un Service administrado competidor; no ha sido completamente open source desde 2018. Las bibliotecas del lado del cliente como `kafka-avro-serializer` todavía son publicadas por Confluent, pero debido a que la REST API es compatible, normalmente funciona sin cambios de código apuntar `schema.registry.url` a Karapace o Apicurio.

## Formatos de serialización

### Avro

Avro define su esquema como JSON y serializa los datos en un formato binario compacto. Es el formato más utilizado en el ecosistema Kafka, y su característica destacada es la **resolución de esquema**: el **esquema del escritor** (utilizado cuando se escribieron los datos) y el **esquema del lector** (utilizado al volver a leerlos) no tienen que coincidir exactamente; Avro resuelve las diferencias de acuerdo con reglas bien definidas.

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

Los esquemas Protobuf se definen en archivos `.proto` y se compilan con `protoc` para generar código en cada lenguaje objetivo. Al igual que Avro, produce codificaciones binarias compactas, pero asigna números de campo explícitos y tiene un sistema de tipos más estricto, lo que suele producir código generado de mayor calidad entre distintos lenguajes. La adopción de Protobuf en el ecosistema Kafka ha crecido de forma sostenida.

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

JSON Schema define reglas de validación para las propias cargas útiles JSON. Es legible para las personas y fácil de depurar, pero debido a que los nombres de campos se repiten en cada mensaje, las cargas útiles terminan siendo mucho mayores que Avro o Protobuf. Es adecuado para cargas de trabajo que necesitan validación de esquemas, pero son menos sensibles al rendimiento o al costo de almacenamiento.

### Comparación de los tres formatos

| | Avro | Protobuf | JSON Schema |
| --- | --- | --- | --- |
| Definición del esquema | JSON | `.proto` IDL | JSON Schema |
| Tamaño de la carga útil | Pequeño | Pequeño | Grande |
| Legible para humanos | Solo el esquema | Solo el esquema | También la carga útil |
| Generación de código entre lenguajes | Buena | Excelente | Buena |
| Adopción en el ecosistema Kafka | Muy alta | Alta (en crecimiento) | Moderada |
| Reglas de evolución del esquema | Resolución escritor/lector | Basadas en números de campo | Reglas de validación JSON Schema |

## Estrategias de compatibilidad

Cuando se registra una nueva versión del esquema, el registry la verifica con la versión anterior de acuerdo con el modo de compatibilidad configurado. Comprender correctamente estos cuatro modos es importante: este es el concepto que más se confunde en la gestión de esquemas.

| Modo | Significado | Orden de implementación |
| --- | --- | --- |
| **BACKWARD** | Un lector que usa el esquema **nuevo** debe poder leer datos escritos con el esquema **antiguo** | Actualice primero los **consumers** |
| **FORWARD** | Un lector que usa el esquema **antiguo** debe poder leer datos escritos con el esquema **nuevo** | Actualice primero los **producers** |
| **FULL** | Se cumplen tanto BACKWARD como FORWARD | Cualquier orden es segura |
| **NONE** | Sin verificación de compatibilidad | Se requiere coordinación manual |

La parte que las personas con mayor frecuencia interpretan al revés:

* **BACKWARD** significa «el esquema nuevo (como lector) puede leer datos antiguos». En la práctica, esto significa que puede **implementar primero el consumer con el esquema nuevo** de forma segura; incluso mientras los producers siguen escribiendo con el esquema antiguo, el consumer actualizado los lee correctamente.
* **FORWARD** significa «el esquema antiguo (como lector) puede leer datos nuevos». Eso significa que puede **actualizar primero los producers al esquema nuevo** de forma segura; los consumers que aún ejecutan el esquema antiguo siguen funcionando.

### Ejemplo de un cambio compatible con versiones anteriores

Agregar un campo opcional con un valor predeterminado al esquema `Order` es compatible con BACKWARD:

```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

Un consumer que usa el esquema nuevo y lee datos antiguos (que carecen de este campo) simplemente obtiene el valor `default` (`null`), sin fallar.

### Ejemplos de cambios que rompen la compatibilidad

Estas son infracciones clásicas de la compatibilidad BACKWARD:

* **Agregar un campo obligatorio sin un valor predeterminado**: agregar un nuevo campo `discount_code` sin un valor predeterminado significa que un lector con el esquema nuevo espera el campo en datos antiguos que nunca lo tuvieron, y falla. (Por el contrario, *eliminar* un campo es compatible con BACKWARD, pero rompe FORWARD: un lector con el esquema antiguo aún esperaría que el campo ahora eliminado fuera obligatorio en los datos nuevos.)
* **Cambiar el tipo de un campo**: cambiar `amount` de `double` a `string` significa que los datos existentes codificados en binario ya no se pueden decodificar como el tipo nuevo.
* **Renombrar un campo** (sin un alias): el lector busca el campo con su nombre nuevo, pero los datos antiguos solo lo tienen con el nombre antiguo.

## Implementación en Strimzi/EKS

### Implementación de Apicurio Registry (almacenamiento en Kafka topic)

Suponiendo que ya se está ejecutando un clúster Kafka administrado por Strimzi, puede implementar Apicurio Registry como un Deployment en el mismo namespace, respaldado por un motor de almacenamiento en Kafka topic.

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

Apicurio también admite un backend SQL (`APICURIO_STORAGE_KIND=sql`) en lugar de `kafkasql`, por lo que, si ya ejecuta una instancia PostgreSQL/RDS, puede apuntar el registry allí. En cambio, Karapace siempre almacena los esquemas en un Kafka topic (`_schemas`) y no necesita una configuración de backend independiente.

### Registro de un esquema

Una vez que el registry está en ejecución, los esquemas se registran mediante su REST API (utilizando el endpoint compatible con Confluent):

```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

### Configuración del cliente

Las aplicaciones producer/consumer de Kafka apuntan su serializer a la URL del registry:

```properties
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6
```

La misma clase `KafkaAvroSerializer` también funciona con Karapace; simplemente apunte `schema.registry.url` al endpoint REST de Karapace (puerto 8081 de forma predeterminada). El código de la aplicación no necesita cambiar cuando intercambia implementaciones de registry, que es precisamente el valor que proporciona la API compatible con Confluent.

## Qué sigue

Esta parte cubrió cómo un schema registry mantiene seguro el contrato de datos entre producers y consumers mientras ambos evolucionan de forma independiente. La parte 5 continúa con Kafka Connect y MirrorMaker: integración con sistemas externos y replicación de datos entre clústeres.

[Volver a la página principal](./README.md)

## Cuestionario

Para comprobar lo que ha aprendido en este capítulo, pruebe el [Cuestionario del topic](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md).
