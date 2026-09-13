# Cuestionario de fundamentos de Kafka

> **Última actualización**: 12 de septiembre de 2026, Kafka 4.3.1.

Este cuestionario evalúa brokers/temas/particiones, garantías de orden, reequilibrado de consumidores, KRaft y replicación/durabilidad.

## Preguntas de opción múltiple

1. ¿En qué ámbito garantiza Kafka el orden de mensajes?
   - A) En todo el clúster
   - B) En todo un tema, incluidas todas sus particiones
   - C) Solo dentro de la misma partición
   - D) Solo dentro del mismo grupo de consumidores

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Solo dentro de la misma partición**

**Explicación:**
La garantía es el orden del log de partición. Enrutar la misma clave requiere serialización, particionador y número de particiones coherentes; redimensionar o cambiar clientes puede alterar el mapeo. El tiempo del evento de negocio y el procesamiento paralelo necesitan contratos de orden separados.
</details>

2. ¿Qué significa ISR (In-Sync Replicas)?
   - A) Todos los brokers registrados
   - B) Réplicas suficientemente actualizadas respecto al líder
   - C) Réplicas no elegibles como líder
   - D) Consumidores de un grupo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Réplicas suficientemente actualizadas respecto al líder**

**Explicación:**
ISR incluye réplicas suficientemente sincronizadas, incluido el líder. acks=all espera al ISR completo actual; min.insync.replicas limita su mínimo. Confirmar no equivale a fsync de cada registro.
</details>

3. ¿Cuál es enable.auto.commit predeterminado en Java KafkaConsumer 4.3?
   - A) `false`
   - B) `true`
   - C) Depende del broker
   - D) Se eliminó desde Kafka 3.x

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `true`**

**Explicación:**
Java KafkaConsumer 4.3 usa true e intervalo 5000 ms. La posición cliente no es finalización del negocio externo. En procesamiento asíncrono/paralelo no confirme más allá de trabajo incompleto. El commit manual también necesita contabilizar correctamente la posición completada.
</details>

4. ¿Qué NO provoca reequilibrado del grupo?
   - A) Se incorpora un consumidor
   - B) Un consumidor Classic no envía heartbeat dentro de `session.timeout.ms`
   - C) Cambia el número de particiones
   - D) Un productor envía con `acks=all`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Un productor envía con `acks=all`**

**Explicación:**
Miembros, particiones suscritas y timeouts heartbeat/poll afectan asignación. Classic usa session.timeout.ms cliente; el protocolo consumer usa group.consumer.session.timeout.ms del broker. acks controla confirmaciones del productor.
</details>

5. ¿Desde qué versión KRaft quedó listo para producción (GA)?
   - A) Kafka 2.8
   - B) Kafka 3.3
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Kafka 3.3**

**Explicación:**
KRaft se introdujo por primera vez como versión preliminar de acceso anticipado en Kafka 2.8, pero no estuvo preparado para producción (disponibilidad general) hasta Kafka 3.3. Continuó estabilizándose en las versiones menores posteriores, y Kafka 4.0 eliminó por completo el modo ZooKeeper, convirtiendo KRaft en el único mecanismo compatible de gestión de metadatos.
</details>

6. ¿Qué versión eliminó completamente ZooKeeper, dejando solo KRaft?
   - A) Kafka 3.3
   - B) Kafka 3.5
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Kafka 4.0**

**Explicación:**
Kafka 4.0 (publicado en marzo de 2025) eliminó completamente el modo de gestión de metadatos basado en ZooKeeper. A partir de esta versión, los clústeres nuevos solo pueden inicializarse en modo KRaft, y los clústeres existentes basados en ZooKeeper deben completar una migración a KRaft en Kafka 3.x antes de actualizar a 4.0.
</details>

7. Con tres réplicas ISR sanas y otros requisitos como cuórum mantenidos, ¿cuántos fallos de broker tolera RF=3/min ISR=2/acks=all conservando escritura?
   - A) 0
   - B) 1
   - C) 2
   - D) 3

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) 1**

**Explicación:**
Se supone ISR inicial sano de tres y cuórum, red y almacenamiento operativos. Dos ISR restantes cumplen el mínimo tras un fallo, aunque pueden producirse errores/reintentos durante la transición. Dos fallos de réplica no conservan escritura. RF=3 solo no garantiza supervivencia ante dos fallos arbitrarios.
</details>

8. ¿Qué acks no espera confirmación del broker?
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) `acks=0`**

**Explicación:**
acks=0 no espera respuesta, no confirma almacenamiento y devuelve offset -1. No garantiza el mejor rendimiento/latencia en toda carga y entra en conflicto con idempotencia explícita. acks=all y -1 son equivalentes.
</details>

9. ¿Cómo se llama el único nodo KRaft que procesa cambios de metadatos, como elección de líder y creación de temas?
   - A) Votante controlador
   - B) Controlador activo
   - C) Líder de partición
   - D) Broker de metadatos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Controlador activo**

**Explicación:**
Se elige un votante como controlador activo. Elegir sustituto necesita mayoría y conectividad. Un controlador dedicado no necesita servir el rol de datos del broker.
</details>

10. ¿Para qué sirve CooperativeStickyAssignor en Classic?
    - A) Cambiar el hash de claves del productor
    - B) Minimizar movimiento de particiones durante reequilibrado y reducir su coste
    - C) Ajustar dinámicamente votantes del cuórum
    - D) Aumentar réplicas ISR

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Minimizar movimiento de particiones durante reequilibrado y reducir su coste**

**Explicación:**
Es un asignador cliente de Classic. La reasignación incremental reduce interrupciones innecesarias. El nuevo protocolo consumer usa asignadores del servidor, por lo que esa configuración de clase cliente no se aplica.
</details>

## Preguntas breves

11. ¿Cómo se llama el log Raft interno de metadatos KRaft?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `__cluster_metadata`**

**Explicación:**
__cluster_metadata es el log interno Raft, visible normalmente como directorio __cluster_metadata-0. No es un tema de aplicación administrado con KafkaProducer/KafkaConsumer; controladores y brokers usan rutas de replicación/consulta de metadatos.
</details>

12. ¿Qué ajuste evita escrituras duplicadas por reintentos de red?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `enable.idempotence` (productor idempotente, `enable.idempotence=true`)**

**Explicación:**
ID, épocas y secuencias del productor suprimen duplicados de la misma transmisión reintentada. No deduplican generalmente un evento enviado por la aplicación como envío nuevo. Las transacciones requieren identidad/fencing del escritor lógico, commits atómicos de salida/offsets y consumo read_committed.
</details>

13. ¿Cómo se llama la concentración de tráfico en pocas particiones por baja cardinalidad de la clave?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Partición caliente**

**Explicación:**
Una partición caliente se produce cuando los valores elegidos como clave de partición no tienen suficiente cardinalidad (valores distintos), o cuando un valor concreto aparece con frecuencia desproporcionada. Por ejemplo, si la mayor parte del tráfico se concentra en unos pocos ID de grandes clientes, solo las particiones a las que se asignan esas claves mediante hash reciben una carga excesiva, mientras las demás permanecen inactivas. Esto anula la ventaja del procesamiento paralelo de consumidores, por lo que debe revisarse cuidadosamente la distribución del tráfico al diseñar la clave.
</details>

14. ¿Qué ajuste limita el intervalo entre poll() consecutivos de KafkaConsumer?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `max.poll.interval.ms`**

**Explicación:**
El valor predeterminado es 300000 ms. Con membresía estática (group.instance.id), superarlo no reasigna inmediatamente: también importa el timeout tras cesar heartbeats. Revise reglas Classic/consumer y ajuste procesamiento, tamaño poll y modelo de ejecución juntos.
</details>

## Ejercicios prácticos

15. Escriba `kafka-topics.sh` para crear `events` con 8 particiones, replicación 3 y `min.insync.replicas=2`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
kafka-topics.sh --create \
  --bootstrap-server "$DOCS_BOOTSTRAP" \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**Explicación:**
Se necesita un clúster accesible con al menos tres brokers y autenticación adecuada. Ocho particiones permiten hasta ocho propietarios activos en un grupo por particiones asignado automáticamente; uno puede poseer varias. La tolerancia depende de sincronización real, cuórum y otras condiciones.
</details>

16. Escriba un fragmento Kafka 4.3.1 de cuórum dinámico para controlador dedicado node.id=90 con tres endpoints de descubrimiento y explique por qué las semillas no son los votantes.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```properties
# Configuration excerpt for node 90; these DNS names must resolve in the deployment.
process.roles=controller
node.id=90
controller.quorum.bootstrap.servers=controller-0.example.internal:9093,controller-1.example.internal:9093,controller-2.example.internal:9093
listeners=CONTROLLER://controller-0.example.internal:9093
advertised.listeners=CONTROLLER://controller-0.example.internal:9093
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
controller.listener.names=CONTROLLER
log.dirs=./controller-90-data
```

**Explicación:**
controller.quorum.bootstrap.servers enumera semillas, no votantes. El formato/arranque inicial coordina cluster ID, directory ID y votantes iniciales. No defina controller.quorum.voters en cuórum dinámico. Ajuste DNS, listeners y TLS/autenticación; es un fragmento, no un clúster completo desplegable.
</details>

17. Configure idempotencia e ID transaccional y explique los pasos adicionales para exactly-once de Kafka a Kafka.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```properties
bootstrap.servers=127.0.0.1:19092
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=org.apache.kafka.common.serialization.StringSerializer
acks=all
enable.idempotence=true
transactional.id=orders-writer-1
max.in.flight.requests.per.connection=5
delivery.timeout.ms=120000
```

**Explicación:**
La configuración solo prepara al productor. Implemente initTransactions, beginTransaction, envíos de salida, sendOffsetsToTransaction con siguientes offsets de entrada, commitTransaction y abort/recuperación. Los consumidores desactivan auto commit y usan read_committed. Escritores concurrentes necesitan ID transaccionales distintos; siguen vigentes plazos como delivery.timeout.ms.
</details>

---

[Volver al material](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [Siguiente cuestionario: Strimzi Operator](./02-strimzi-operator-quiz.md)
