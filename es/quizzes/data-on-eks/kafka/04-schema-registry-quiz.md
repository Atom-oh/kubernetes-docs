# Cuestionario sobre Schema Registry

Este cuestionario evalúa tu comprensión de por qué existen los schema registries (registros de esquemas), las ventajas y desventajas de serialización de Avro/Protobuf, los cuatro modos de compatibilidad y las diferencias de licencia entre las principales implementaciones (Karapace, Apicurio, Confluent).

## Preguntas de opción múltiple

1. ¿Cuál es el problema más fundamental causado por el hecho de que los brokers de Kafka nunca validan el contenido de los mensajes?
   - A) El rendimiento del broker disminuye
   - B) Los productores y consumidores pueden evolucionar sus esquemas sin conocer los cambios de los demás, lo que provoca fallos de deserialización
   - C) No puedes crear más de un topic
   - D) El rebalanceo de particiones se vuelve imposible

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los productores y consumidores pueden evolucionar sus esquemas sin conocer los cambios de los demás, lo que provoca fallos de deserialización**

**Explicación:**
Kafka trata cada mensaje como un arreglo opaco de bytes y no impone ningún formato de datos. Como los productores y consumidores suelen ser aplicaciones separadas desplegadas con calendarios independientes, un cambio de esquema en un lado puede romper silenciosamente el otro, causando fallos de deserialización o valores corruptos. Un schema registry resuelve esto gestionando centralmente el contrato y aplicando la compatibilidad.
</details>

2. En comparación con JSON sin esquema, ¿cuál es la mayor ventaja de combinar un formato binario como Avro/Protobuf con un schema registry?
   - A) Se vuelve más fácil de leer para los humanos
   - B) Los payloads se vuelven más pequeños y los cambios de esquema se validan centralmente
   - C) Ajusta automáticamente el número de particiones
   - D) Los consumer groups se vuelven innecesarios

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los payloads se vuelven más pequeños y los cambios de esquema se validan centralmente**

**Explicación:**
Avro/Protobuf usan codificación binaria compacta que no repite los nombres de los campos, lo que hace que los payloads sean más pequeños que JSON. Además, los mensajes llevan solo un ID de esquema en lugar del esquema completo: el esquema real lo gestiona el registry, que valida la compatibilidad cada vez que se registra una nueva versión. JSON, en cambio, sigue siendo más fácil de leer directamente para una persona.
</details>

3. ¿Qué contiene un mensaje real en tránsito cuando se usa un schema registry?
   - A) La definición completa del esquema
   - B) Un encabezado corto que contiene el ID del esquema, seguido de datos codificados en binario
   - C) La URL del schema registry
   - D) El ID del consumer group

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un encabezado corto que contiene el ID del esquema, seguido de datos codificados en binario**

**Explicación:**
El productor registra (o busca) el esquema en el registry y antepone el ID de esquema devuelto, normalmente junto con un magic byte, al inicio del mensaje serializado. La definición completa del esquema nunca se incluye en el mensaje; solo el registry la almacena, que es lo que mantiene pequeño el payload. El consumidor lee este ID y obtiene del registry el esquema correspondiente para deserializar el resto.
</details>

4. ¿Cuál de las siguientes implementaciones de schema registry se distribuye bajo la Apache License 2.0?
   - A) Confluent Schema Registry
   - B) Tanto Karapace como Apicurio Registry
   - C) Solo Karapace
   - D) Solo Apicurio Registry

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Tanto Karapace como Apicurio Registry**

**Explicación:**
Karapace (Aiven) y Apicurio Registry (Red Hat) son proyectos completamente open-source distribuidos bajo la Apache License 2.0. Confluent Schema Registry se rige por la Confluent Community License desde 2018, que impone restricciones sobre ciertos usos comerciales y no es una licencia completamente open-source.
</details>

5. ¿Qué combinación se recomienda para un stack EKS + Strimzi autogestionado a fin de evitar fricciones de licencia?
   - A) Solo Confluent Schema Registry
   - B) Karapace o Apicurio Registry
   - C) Ningún schema registry; simplemente usa JSON
   - D) Solo AWS Glue Schema Registry es viable

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Karapace o Apicurio Registry**

**Explicación:**
Karapace y Apicurio Registry tienen licencia Apache-2.0 y se pueden alojar de forma autogestionada sin restricciones. La Confluent Community License de Confluent Schema Registry introduce términos que justifican una revisión de licencia antes de su uso autogestionado. Ambas alternativas open-source son compatibles con la API de Confluent, por lo que los clientes pueden cambiar sin modificaciones de código.
</details>

6. ¿Qué mecanismo central permite la evolución de esquemas en la serialización Avro?
   - A) Mapeo basado en números de campo
   - B) Reglas de resolución entre el esquema del escritor y el esquema del lector
   - C) Referencias `$ref` de JSON Schema
   - D) Generación de código en tiempo de compilación

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Reglas de resolución entre el esquema del escritor y el esquema del lector**

**Explicación:**
Incluso cuando el esquema del escritor (usado cuando se escribieron los datos) y el esquema del lector (usado al leerlos de vuelta) difieren, Avro puede decodificar correctamente los datos aplicando reglas de resolución definidas: emparejar campos por nombre, aplicar valores predeterminados, etc. El mapeo basado en números de campo es una característica de Protobuf, no de Avro.
</details>

7. ¿Dónde tiene Protobuf una ventaja relativa sobre Avro?
   - A) Sus payloads siempre son más pequeños
   - B) Los números de campo explícitos y un sistema de tipos más estricto producen código generado entre lenguajes de mayor calidad
   - C) No requiere un schema registry
   - D) Es más legible para humanos que JSON

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los números de campo explícitos y un sistema de tipos más estricto producen código generado entre lenguajes de mayor calidad**

**Explicación:**
Protobuf asigna un número explícito a cada campo en su IDL `.proto` y aplica un sistema de tipos estricto, lo que tiende a producir código cliente generado más limpio entre lenguajes mediante `protoc`. El tamaño del payload suele ser comparable al de Avro, y Protobuf se combina comúnmente con un schema registry igual que Avro.
</details>

8. En un topic configurado con compatibilidad BACKWARD, ¿qué lado es seguro actualizar primero?
   - A) El productor
   - B) El consumidor
   - C) El broker
   - D) El controlador ZooKeeper o KRaft

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El consumidor**

**Explicación:**
La compatibilidad BACKWARD significa "un lector que usa el esquema nuevo debe poder leer datos escritos con el esquema antiguo". Esto significa que el consumidor puede actualizarse primero al esquema nuevo, incluso mientras los productores siguen escribiendo con el esquema antiguo; el consumidor actualizado leerá correctamente los datos antiguos. FORWARD, en cambio, es el modo en el que es seguro desplegar primero el productor.
</details>

9. ¿Qué afirmación describe correctamente la compatibilidad FORWARD?
   - A) Un lector que usa el esquema antiguo debe poder leer datos escritos con el esquema nuevo
   - B) Un lector que usa el esquema nuevo debe poder leer datos escritos con el esquema antiguo
   - C) No se realiza ninguna comprobación de compatibilidad
   - D) Los consumidores siempre deben actualizarse primero

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Un lector que usa el esquema antiguo debe poder leer datos escritos con el esquema nuevo**

**Explicación:**
FORWARD significa "el esquema antiguo (como lector) puede leer datos escritos con el esquema nuevo". Bajo este modo, los productores pueden actualizarse primero al esquema nuevo y los consumidores que aún ejecutan el esquema antiguo seguirán leyendo correctamente. B describe BACKWARD, C describe NONE y D es el orden seguro bajo BACKWARD, no FORWARD.
</details>

10. ¿Cuál de los siguientes cambios de esquema infringe la compatibilidad BACKWARD?
    - A) Agregar un campo opcional con un valor predeterminado
    - B) Agregar un campo requerido sin un valor predeterminado
    - C) Agregar un comentario de documentación a un campo
    - D) Reordenar campos sin cambiar sus nombres ni tipos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Agregar un campo requerido sin un valor predeterminado**

**Explicación:**
Agregar un campo requerido sin valor predeterminado significa que un lector que usa el esquema nuevo, al leer datos antiguos (que nunca tuvieron este campo), espera un valor pero no encuentra ninguno, lo que provoca un fallo de lectura. Eliminar un campo, en cambio, SÍ es compatible hacia atrás, ya que el lector con el esquema nuevo simplemente nunca lo busca (aunque esto rompe la compatibilidad FORWARD). Agregar un campo opcional con un valor predeterminado es el ejemplo clásico de un cambio compatible con BACKWARD, mientras que agregar comentarios de documentación o reordenar campos (Avro empareja por nombre) no tiene efecto sobre la estructura real de los datos.
</details>

## Preguntas de respuesta corta

11. ¿Qué información lee un consumidor de un mensaje para encontrar el esquema correcto con el que deserializarlo?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: El ID del esquema**

**Explicación:**
Al serializar, el productor incluye solo el ID de esquema emitido por el registry (normalmente codificado cerca del inicio del mensaje junto con un magic byte) en lugar del esquema completo. El consumidor lee este ID, consulta al registry por el esquema correspondiente y lo usa para deserializar el resto del payload binario.
</details>

12. ¿Cuál es el nombre del modo de compatibilidad que requiere que tanto BACKWARD como FORWARD se cumplan al mismo tiempo?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: FULL**

**Explicación:**
La compatibilidad FULL requiere que tanto BACKWARD (un lector con el esquema nuevo puede leer datos antiguos) como FORWARD (un lector con el esquema antiguo puede leer datos nuevos) se cumplan simultáneamente. Esto hace que el orden de actualización de productor/consumidor sea irrelevante, pero también es el más estricto de los cuatro modos en cuanto a los cambios de esquema que permite.
</details>

13. ¿Cuáles son los dos tipos de backend de almacenamiento compatibles con Apicurio Registry?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Un backend basado en un topic de Kafka (kafkasql) y un backend basado en SQL (sql, por ejemplo PostgreSQL)**

**Explicación:**
Apicurio Registry te permite elegir el backend mediante la variable de entorno `APICURIO_STORAGE_KIND`: `kafkasql` almacena los metadatos de esquema en un topic de Kafka, mientras que `sql` los almacena en una base de datos relacional como PostgreSQL. Karapace, en cambio, siempre usa un topic de Kafka (`_schemas`) como su única opción de almacenamiento.
</details>

14. ¿A qué licencia cambió Confluent componentes clave (incluido Schema Registry) alrededor de 2018, haciendo que ya no fueran completamente open source?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: La Confluent Community License**

**Explicación:**
Alrededor de 2018, Confluent migró varios componentes centrales, incluido Schema Registry, a la Confluent Community License. Esta licencia mantiene visible el código fuente, pero prohíbe ciertos usos, como ofrecerlo como un servicio gestionado competidor, que las licencias open-source aprobadas por la OSI permitirían.
</details>

15. ¿Qué propiedad configuran los clientes de Kafka para que un serializer/deserializer de Avro sepa dónde encontrar el schema registry?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: schema.registry.url**

**Explicación:**
La propiedad `schema.registry.url` indica a `KafkaAvroSerializer`/`KafkaAvroDeserializer` (y sus equivalentes) qué endpoint REST usar para registrar y buscar esquemas. Cambiar solo esta propiedad te permite alternar entre Karapace, Apicurio y Confluent sin cambios en el código de la aplicación.
</details>

## Preguntas prácticas

16. Escribe una definición de campo Avro que agregue un campo opcional `discountCode` a un esquema `Order` existente de forma compatible con BACKWARD.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

**Explicación:**
Combinar el tipo union `["null", "string"]` con `default: null` significa que un lector que usa el esquema nuevo, al leer datos antiguos que no tienen este campo, recibe automáticamente `null`. Agregar un campo requerido sin valor predeterminado rompería la compatibilidad BACKWARD, por lo que preservar la compatibilidad con los datos existentes siempre requiere especificar un valor predeterminado.
</details>

17. Escribe una llamada curl a la API REST compatible con Confluent para registrar un nuevo esquema Avro bajo el subject `orders-value`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

**Explicación:**
Enviar una solicitud `POST` a `/subjects/<subject>/versions` registra el esquema. `<topic>-value` es la convención estándar de nomenclatura de subjects de Confluent para el payload de valor de un topic determinado. El campo `schema` en el cuerpo de la solicitud lleva el esquema Avro real como una cadena JSON escapada. Al registrarse, el registry valida el esquema nuevo contra las versiones anteriores según el modo de compatibilidad configurado.
</details>

18. Escribe la especificación central del container (imagen, variables de entorno) para un Deployment de Apicurio Registry que usa un topic de Kafka como backend de almacenamiento y se ejecuta en el mismo namespace que un cluster Kafka de Strimzi.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
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
```

**Explicación:**
`APICURIO_STORAGE_KIND=kafkasql` indica a Apicurio que persista los metadatos de esquema en un topic de Kafka en lugar de requerir una base de datos separada. `APICURIO_KAFKASQL_BOOTSTRAP_SERVERS` debe apuntar al bootstrap service que crea Strimzi (`<cluster-name>-kafka-bootstrap`). Para usar el backend SQL en su lugar, establece `APICURIO_STORAGE_KIND=sql` junto con la configuración de conexión del datasource correspondiente.
</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/kafka/04-schema-registry.md) | [Siguiente cuestionario: Kafka Connect y MirrorMaker](./05-kafka-connect-mirrormaker-quiz.md)
