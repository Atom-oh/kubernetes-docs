# Cuestionario sobre Schema Registry

Repasa los contratos de esquemas, la codificación, la compatibilidad, la recuperación y el ejemplo de despliegue.

## 1. ¿Por qué el almacenamiento básico de registros de Kafka no impone un contrato de esquema?

<details>
<summary>Mostrar respuesta</summary>

Las claves y los valores se almacenan como bytes. La validación estructural y de negocio depende de los serializadores, las aplicaciones y las rutas de validación. Agregar un campo no siempre rompe un consumidor.

</details>

## 2. ¿Se pueden versionar y validar documentos JSON antes del tiempo de ejecución sin un registro?

<details>
<summary>Mostrar respuesta</summary>

Sí. JSON Schema, las comprobaciones de CI y las especificaciones versionadas pueden proporcionar un contrato. Un registro centraliza la gobernanza y la distribución; la codificación binaria es una elección aparte.

</details>

## 3. ¿Cuáles son los primeros cinco bytes del formato común de encuadre de Confluent con ID de esquema?

<details>
<summary>Mostrar respuesta</summary>

Un byte mágico y un ID de esquema de cuatro bytes, seguidos del valor. Protobuf también incluye índices de mensaje. Esta regla no es universal para todos los registros o formatos de codificación.

</details>

## 4. ¿Qué formatos de esquema principales admite Karapace 6.2.4?

<details>
<summary>Mostrar respuesta</summary>

Avro, JSON Schema y Protobuf. Comprueba por separado qué borradores y palabras clave de JSON Schema valida, y si admite análisis de compatibilidad.

</details>

## 5. ¿Qué hay que tener en cuenta al revisar las licencias Apache-2.0 y de los componentes de Confluent?

<details>
<summary>Mostrar respuesta</summary>

Apache-2.0 incluye condiciones como conservar los avisos requeridos. El servidor de Confluent y los módulos de cliente/Avro pueden tener licencias distintas. Comprueba el componente concreto y el contrato de soporte, en lugar de inferir las condiciones a partir de la escala.

</details>

## 6. ¿Qué permite la evolución de Avro y para qué sirve el valor predeterminado de un campo?

<details>
<summary>Mostrar respuesta</summary>

La resolución entre el esquema del escritor y el del lector. El lector usa un valor predeterminado cuando el esquema del escritor no incluye ese campo. Esto no permite que el escritor omita un campo obligatorio cualquiera.

</details>

## 7. ¿Se puede reutilizar con otro significado el número de un campo eliminado de Protobuf?

<details>
<summary>Mostrar respuesta</summary>

No lo reutilices. Los datos o clientes antiguos podrían interpretar ese número con su significado anterior. Reserva los números o nombres eliminados según corresponda, y comprueba los tipos wire y la semántica de la aplicación.

</details>

## 8. ¿Cuál suele ser el orden de despliegue de un cambio de esquema compatible hacia atrás?

<details>
<summary>Mostrar respuesta</summary>

Primero se actualizan los consumidores: el lector nuevo debe poder leer los datos escritos con el esquema anterior. Prueba también el comportamiento de negocio y recuerda que la compatibilidad se configura para un subject, no es inherente a un topic.

</details>

## 9. ¿En qué dirección comprueba la compatibilidad FORWARD?

<details>
<summary>Mostrar respuesta</summary>

El lector anterior debe poder leer los datos escritos con el esquema nuevo; normalmente esto permite actualizar primero a los productores. Esto por sí solo no valida que un lector nuevo pueda reproducir datos antiguos.

</details>

## 10. ¿Eliminar un campo de Avro siempre rompe la compatibilidad hacia adelante?

<details>
<summary>Mostrar respuesta</summary>

No. Si el lector antiguo tiene un valor predeterminado, puede proporcionarlo cuando faltan en los datos del escritor nuevo. Sin un valor predeterminado, la lectura falla. Distingue este caso de la dirección hacia atrás, en la que el lector nuevo deja de requerir el campo.

</details>

## 11. ¿Qué hay que comprobar para un consumidor con la caché fría y una migración de registro?

<details>
<summary>Mostrar respuesta</summary>

El identificador de un registro conservado debe resolverse al mismo esquema de escritor. Verifica la correspondencia de ID, las referencias, la estrategia de subject, la codificación, la autenticación y las versiones de cliente. Un cambio de URL por sí solo no es prueba suficiente.

</details>

## 12. ¿Qué modo requiere compatibilidad BACKWARD y FORWARD, y qué añade su variante TRANSITIVE?

<details>
<summary>Mostrar respuesta</summary>

FULL. FULL_TRANSITIVE comprueba ambas direcciones del esquema frente a todas las versiones anteriores. FULL normal compara con la versión anterior más reciente. Ninguno garantiza la semántica de negocio ni el comportamiento de la aplicación.

</details>

## 13. ¿Apicurio KafkaSQL almacena archivos completos de instantánea en su topic de snapshots?

<details>
<summary>Mostrar respuesta</summary>

No. Registra las rutas de los archivos. La durabilidad, el uso compartido y la recuperación de los archivos requieren un diseño propio. El laboratorio deshabilita las instantáneas programadas y conserva el diario completo para reproducirlo tras reiniciar.

</details>

## 14. ¿Qué valores satisfacen las comprobaciones predeterminadas de los topics de diario e instantáneas de KafkaSQL 3.3.3?

<details>
<summary>Mostrar respuesta</summary>

`cleanup.policy=delete`, `retention.ms=-1` y `retention.bytes=-1`. Supervisa el crecimiento cuando la retención es indefinida. No copies una configuración genérica de compactación para `_schemas` ni una retención breve de eventos.

</details>

## 15. ¿Qué propiedades de Avro son distintas entre un productor y un consumidor?

<details>
<summary>Mostrar respuesta</summary>

El productor usa `value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer`; el consumidor usa `value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer`. Ambos necesitan una URL del registro, la configuración TLS/SASL del broker y las dependencias de biblioteca correspondientes.

</details>

## 16. Escribe definiciones Avro para un campo timestamp-millis y un campo discountCode con valor predeterminado.

<details>
<summary>Mostrar respuesta</summary>

```json
[
  {"name":"createdAt","type":{"type":"long","logicalType":"timestamp-millis"}},
  {"name":"discountCode","type":["null","string"],"default":null}
]
```

Estas son definiciones para el arreglo `fields` de un registro. El tipo lógico va dentro del objeto type; el valor null predeterminado del campo agregado se usa cuando un lector nuevo lee datos antiguos.

</details>

## 17. ¿Cómo se registra el archivo order.avsc del capítulo bajo el subject orders-value?

<details>
<summary>Mostrar respuesta</summary>

Sigue el ejemplo `register.sh` del capítulo: analiza el JSON y crea un archivo de solicitud que contenga la cadena del esquema y `schemaType: AVRO`. Envíalo mediante POST a `/apis/ccompat/v7/subjects/orders-value/versions` y comprueba los errores HTTP. Configura primero la compatibilidad y después recupera la versión más reciente. La estrategia predeterminada TopicNameStrategy supone que el topic se llama `orders`.

</details>

## 18. Describe qué conecta el despliegue de Apicurio del capítulo con el entorno Strimzi anterior.

<details>
<summary>Mostrar respuesta</summary>

Usa la imagen 3.3.3, `APICURIO_STORAGE_KIND=kafkasql`, `my-cluster-kafka-bootstrap.kafka.svc:9093`, SASL_SSL/SCRAM-SHA-512, el truststore de CA, la configuración JAAS respaldada por un Secret y la verificación explícita del nombre de host. Crea de antemano tres topics de almacenamiento y las ACL del usuario, y deshabilita la creación automática de topics. Distingue las comprobaciones de estado en el puerto de administración 9000 del puerto de la API HTTP 8080. La autenticación de la API HTTP es independiente de la autenticación de Kafka; el laboratorio no es un servicio público.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/kafka/04-schema-registry.md) | [Siguiente cuestionario](./05-kafka-connect-mirrormaker-quiz.md)
