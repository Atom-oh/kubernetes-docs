# Parte 8: Cuestionario sobre mejores prácticas

Evalúa las particiones, los clientes, la seguridad, la capacidad y la recuperación según las condiciones reales.

## 1. ¿Qué se debe tener en cuenta al dimensionar las particiones para un grupo de consumidores convencional?

<details>
<summary>Mostrar respuesta</summary>

Mide el paralelismo de los miembros del grupo, el rendimiento por partición, el sesgo en la distribución de claves, el tamaño de los registros, la ubicación de las réplicas y la recuperación. Se asigna una partición a un miembro del grupo; los share groups y el paralelismo interno de la aplicación funcionan de otra manera.

</details>

## 2. ¿Se pueden tratar las reglas históricas sobre el número de particiones como límites universales actuales?

<details>
<summary>Mostrar respuesta</summary>

No. Los límites dependen de las versiones, los brokers y controladores, el número de réplicas y la carga de trabajo. Distingue las particiones lógicas de la ubicación de las réplicas en cada broker y prueba tanto el funcionamiento normal como los casos de fallo.

</details>

## 3. ¿Contar las líneas que contienen PartitionCount da el número total de particiones?

<details>
<summary>Mostrar respuesta</summary>

No. Cuenta las líneas de resumen de cada topic. Lee las filas `Partition:`, como hace `partition_summary.py`, para contar por separado las particiones lógicas y las ubicaciones de réplicas. Comprueba también los resultados vacíos, la visibilidad y los filtros.

</details>

## 4. ¿Deben moverse todas las claves al aumentar el número de particiones de un topic con claves?

<details>
<summary>Mostrar respuesta</summary>

No todas las claves tienen que moverse, pero algunas pueden reasignarse. Los registros antiguos permanecen donde estaban, lo que afecta al orden de las claves, al estado y a las suposiciones sobre joins co-particionados. Revisa los serializadores, los partitioners y la topología.

</details>

## 5. ¿Configurar explícitamente acks o retries siempre deshabilita la idempotencia predeterminada?

<details>
<summary>Mostrar respuesta</summary>

No. El problema surge cuando los valores son incompatibles. Si se establece explícitamente `enable.idempotence=true`, `acks`, `retries` y `max.in.flight` deben ser compatibles; los conflictos producen un error de configuración.

</details>

## 6. ¿La idempotencia o un transactional.id por sí solos proporcionan semántica exactly-once de extremo a extremo?

<details>
<summary>Mostrar respuesta</summary>

No. Los reintentos del producer no son lo mismo que los reenvíos de la aplicación ni que los efectos en sistemas externos. Las transacciones de Kafka requieren commits atómicos de las salidas y los offsets de entrada, fencing, `read_committed` y un ciclo de vida correcto; los sistemas externos necesitan su propia estrategia.

</details>

## 7. ¿Qué ocurre cuando el ISR baja a uno con RF=3, acks=all y min.insync.replicas=2?

<details>
<summary>Mostrar respuesta</summary>

Se rechazan las escrituras. `acks=all` espera al ISR actual, y el ISR mínimo es un ajuste del topic o del broker. No garantiza incondicionalmente que las escrituras continúen ni que no haya pérdida después de un fallo si la replicación ya está degradada.

</details>

## 8. ¿Qué distinciones importan para max.poll.interval.ms y los ajustes de heartbeat/session?

<details>
<summary>Mostrar respuesta</summary>

Comprueba el tiempo real de procesamiento entre llamadas a `poll()`. La reasignación de un miembro estático puede esperar hasta que venza la sesión. Distingue los ajustes clásicos de heartbeat/session del cliente de los ajustes controlados por el broker para el protocolo de consumidor.

</details>

## 9. ¿La pertenencia estática garantiza que un reinicio no provoque un rebalance?

<details>
<summary>Mostrar respuesta</summary>

No. Importan la identidad estable y única, el tiempo de reconexión, la topología, las suscripciones y la pertenencia al grupo. Los ID activos duplicados pueden provocar fencing; además, las sesiones más largas retrasan la recuperación ante fallos reales.

</details>

## 10. En Strimzi predeterminado, ¿qué CA firma los certificados de cliente mTLS de KafkaUser?

<details>
<summary>Mostrar respuesta</summary>

La CA de clientes. La CA del clúster se usa para los certificados de los brokers y de los componentes internos. Distingue las credenciales del cliente de la cadena de CA que se usa para confiar en el broker.

</details>

## 11. ¿La alta cardinalidad o los salts aleatorios resuelven por sí solos y de forma segura el sesgo de claves?

<details>
<summary>Mostrar respuesta</summary>

No. Una clave dominante y muy solicitada aún puede sesgar el tráfico. Añadir salts cambia el orden, los joins y la identidad usada en la compactación; primero verifica que el contrato lo permita y planifica cómo recombinar los resultados.

</details>

## 12. ¿Es seguro omitir el commit después de una excepción de procesamiento y simplemente seguir haciendo poll?

<details>
<summary>Mostrar respuesta</summary>

No. Es posible que la posición de lectura ya haya avanzado. Detén y recupera el procesamiento, o busca la posición correcta; confirma solo después del procesamiento duradero. Diseña para la repetición de mensajes y para que los efectos externos sean idempotentes.

</details>

## 13. ¿Se puede determinar la capacidad de Kafka solo a partir de la memoria o de un tamaño fijo de heap?

<details>
<summary>Mostrar respuesta</summary>

No. Mide la caché de páginas del sistema operativo (page cache), la CPU para TLS/compresión, la red, las IOPS/el rendimiento, la memoria de cgroup y la recuperación. Las ventajas de costo del codec y de la instancia dependen de los datos y de la carga de trabajo.

</details>

## 14. ¿Cómo se combinan namespaceSelector y podSelector dentro de una entrada networkPolicyPeers?

<details>
<summary>Mostrar respuesta</summary>

Se combinan con AND dentro de un peer; las entradas peer separadas se combinan con OR. Las NetworkPolicies son aditivas y requieren verificar la aplicación de políticas por el CNI y el egreso. Esta entrada no deniega el tráfico que permita otra política.

</details>

## 15. Explica el cifrado de StorageClass, Auto Mode y los volúmenes existentes.

<details>
<summary>Mostrar respuesta</summary>

Establece `encrypted:true` y los permisos reales de KMS para el provisionador seleccionado; luego verifica el volumen EBS. No deduzcas que todos los PVC dinámicos están cifrados por los discos de nodos o efímeros de Auto Mode. Los cambios en StorageClass o en el cifrado predeterminado de la cuenta no cifran retroactivamente los volúmenes existentes.

</details>

## 16. Escribe el perfil de ajuste del producer y explica batch.size y el ISR mínimo.

<details>
<summary>Mostrar respuesta</summary>

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

`batch.size` controla la agrupación de registros y la asignación por partición; no es un límite estricto para el tamaño de cada registro o solicitud. Configura `min.insync.replicas` en el topic o el broker. Mide las opciones de codec/linger y gestiona los fallos de envío y los tiempos de espera de entrega.

</details>

## 17. Escribe un KafkaUser mTLS independiente sin modificar el usuario SCRAM existente.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service-mtls
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
    - resource:
        type: topic
        name: orders
        patternType: literal
      operations:
      - Read
      - Write
      - Describe
    - resource:
        type: group
        name: order-processor-mtls
        patternType: literal
      operations:
      - Read
    - resource:
        type: cluster
      operations:
      - IdempotentWrite
```

También se necesita un listener con `tls:true` y `authentication.type:tls`; no existe ningún tipo de exposición llamado `tls`. Distribuye y rota las credenciales de la CA de clientes y la cadena de confianza del broker, y verifica las acciones permitidas y denegadas.

</details>

## 18. ¿Cómo se combina un ID de miembro estático basado en una variable de entorno con los commits manuales?

<details>
<summary>Mostrar respuesta</summary>

Java Properties no expande `${POD_NAME}`. Resuelve un ID único y estable y pásalo a `setStaticIdentity` antes de crear el consumer. Usa `enable.auto.commit=false` y `processOneBatch`; no ocultes los errores para luego seguir haciendo poll. La retención, la recuperación y la gestión de duplicados siguen siendo necesarias.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/kafka/08-best-practices.md) | [Siguiente cuestionario](./09-kafka-benchmark-quiz.md)
