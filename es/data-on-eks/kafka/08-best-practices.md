# Parte 8: Buenas prácticas

> **Base de revisión**: Kafka 4.3.1, Strimzi 1.3.0\
> **Última revisión**: 16 de octubre de 2026

Este capítulo convierte los ejemplos anteriores en decisiones operativas que deben validarse.
A continuación se encuentra el [capítulo de pruebas de rendimiento](./09-kafka-benchmark.md); una lista de comprobación no sustituye las pruebas de carga y de fallos con mediciones.

## Diseño de particiones y mediciones

En un grupo de consumidores convencional, cada partición se asigna como máximo a un miembro del grupo a la vez. Por lo tanto, veinte miembros que consumen de forma independiente necesitan al menos veinte particiones para que todos estén ocupados. Mida también el rendimiento por partición, la distribución desigual de claves, el tamaño de los registros, la sobrecarga de replicación, el tiempo de recuperación y la capacidad de los brokers/controladores. Los grupos compartidos y el procesamiento paralelo interno de la aplicación tienen semánticas diferentes; no considere que esta regla describa de forma universal todas las API de consumidores.

Un mayor número de particiones aumenta el trabajo de metadatos, réplicas, búferes y recuperación. El coste no sigue una fórmula universal de memoria/descriptores de archivos por partición. Las reglas empíricas históricas de 4.000/200.000 no son límites universales vigentes. Elija las cantidades a partir del comportamiento medido en estado estable y ante fallos, incluidos los repartos de réplicas por broker, no solo las particiones lógicas del tema.

### Cuenta las particiones, no los encabezados de tema

`grep -c "PartitionCount"` cuenta **líneas de resumen de temas**, no particiones.
Guarde lo siguiente como `partition_summary.py`. Lea las filas de particiones de la CLI actual, incluida `Leader: none`, e informe por separado las particiones lógicas, las ubicaciones de réplicas y el liderazgo.

```python
import collections
import json
from pathlib import Path
import re
import sys

def summarize(text):
    pattern = re.compile(
        r"^\s*Topic:\s+(\S+)\s+Partition:\s+(\d+)\s+Leader:\s+(none|-?\d+)"
        r"\s+Replicas:[ \t]*([\d,]*)[ \t]+Isr:[ \t]*([\d,]*)"
    )
    partitions = {}
    topics = collections.Counter()
    leaders = collections.Counter()
    replicas = collections.Counter()
    offline = []
    for line in text.splitlines():
        if not re.search(r"\bPartition:", line):
            continue
        match = pattern.match(line)
        if not match:
            raise ValueError("Unrecognized partition row; check Kafka CLI version/output.")
        topic, partition, leader, replica_text, _ = match.groups()
        key = (topic, int(partition))
        if key in partitions:
            raise ValueError("Duplicate topic/partition row.")
        replica_ids = [int(x) for x in replica_text.split(",") if x]
        if not replica_ids or len(set(replica_ids)) != len(replica_ids):
            raise ValueError("Missing or duplicate replica IDs.")
        partitions[key] = True
        topics[topic] += 1
        replicas.update(replica_ids)
        if leader == "none" or int(leader) < 0:
            offline.append({"topic": topic, "partition": int(partition)})
        else:
            leaders[int(leader)] += 1
    if not partitions:
        raise ValueError("No partition rows; empty visibility is not proof of a healthy cluster.")
    return {
        "visible_topics": len(topics),
        "logical_partitions": len(partitions),
        "replica_assignments": sum(replicas.values()),
        "partitions_by_topic": dict(sorted(topics.items())),
        "leaders_by_broker": dict(sorted(leaders.items())),
        "replicas_by_broker": dict(sorted(replicas.items())),
        "offline_partitions": offline,
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 partition_summary.py topics.txt")
    print(json.dumps(summarize(Path(sys.argv[1]).read_text()), indent=2))
```

```bash
set -euo pipefail
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
# Run from a Kafka 4.3.1 client installation. admin.properties is local to this client.
bin/kafka-topics.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe > topics.txt
python3 partition_summary.py topics.txt
```

El resultado solo incluye los temas visibles para la identidad que realiza la llamada y los filtros del comando, incluidos los temas internos cuando se devuelven. Una consulta fallida o vacía no demuestra que un clúster tenga cero particiones ni que esté en buen estado. Use credenciales adecuadas para esta lectura administrativa; no suponga que los ID de los Pods de broker o el listener sin cifrar `localhost:9092` sean apropiados.

### Conserve el sentido de la clave

La asignación predeterminada de claves del productor Java usa los **bytes serializados de la clave** y `toPositive(murmur2(keyBytes)) % partitionCount`, a menos que una partición explícita, un particionador personalizado o una configuración que ignore la clave cambien el comportamiento. Los demás clientes deben usar un particionador/serializador compatible si es importante mantener la misma asignación.

Una cardinalidad alta por sí sola no garantiza un tráfico equilibrado: un cliente muy activo aún puede dominar. Añadir una sal aleatoria o basada en marcas de tiempo a las claves cambia el orden por clave, las uniones y la identidad de compactación. Hágalo solo cuando el contrato de datos permita esos cambios y defina una estrategia explícita para recombinar y ordenar los datos si es necesario.

Aumentar el número de particiones puede reasignar algunas claves; no redistribuye los registros antiguos. Puede romper el orden de las claves entre particiones y las suposiciones de las uniones con particiones alineadas. Los requisitos dependen de la unión y la topología; no todas las uniones de Kafka Streams requieren el mismo esquema de co-particionado. Para cargas de trabajo sensibles al orden o con estado, planifique y pruebe la redistribución/migración, a menudo mediante un tema nuevo.

## Ajuste del productor

Considere este perfil como un punto de partida sujeto a mediciones que se añade a la configuración autenticada existente del cliente, no un óptimo universal.

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

- `acks=all` espera al ISR actual. Con RF=3 y `min.insync.replicas=2` en el tema/broker, un ISR inferior a dos rechaza las escrituras en vez de esperar indefinidamente a una segunda réplica. Un único fallo solo es tolerable mientras las réplicas/cuórum restantes y las demás dependencias sigan cumpliendo los requisitos.
- `enable.idempotence=true` suprime los duplicados de los reintentos del productor compatibles. Requiere configuraciones compatibles de acks, reintentos y `max.in.flight.requests.per.connection`. Establecer explícitamente una propiedad compatible no lo desactiva.
- El valor predeterminado de linger de Kafka 4.3 es 5 ms; los 10 ms y 32 KiB de este ejemplo son opciones de ajuste. `batch.size` es una configuración de asignación/agrupación por partición, no un límite máximo estricto para el tamaño del registro o la solicitud. El encolado y los plazos de entrega también afectan la latencia.
- Compare lz4, zstd, gzip y la ausencia de compresión con datos, CPU y latencia representativos. No dé por sentado que un códec siempre tendrá el menor coste total.

`min.insync.replicas` pertenece al tema/broker, no a las propiedades del productor.
`delivery.timeout.ms` limita los intentos de entrega; un número alto de reintentos no implica un tiempo de entrega infinito. Observe siempre los errores de envío.

La idempotencia no elimina duplicados de reenvíos arbitrarios de la aplicación ni de un efecto secundario en una base de datos externa. El procesamiento exactamente una vez de Kafka en el flujo consumir-transformar-producir también requiere el ciclo de vida adecuado de las transacciones, la publicación de los mensajes de salida y la confirmación de los offsets de entrada en una misma transacción atómica, fencing y consumidores con read-committed. Una cadena `transactional.id` por sí sola no es suficiente.

## Procesamiento de consumidores y pertenencia al grupo

Este perfil usa explícitamente **`group.protocol=classic`**, de modo que se apliquen los ajustes de heartbeat/sesión del cliente. Con `group.protocol=consumer`, esos intervalos se controlan mediante la configuración del grupo de consumidores del broker.

```properties
group.id=order-processor
group.protocol=classic
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

Limite el tiempo real de procesamiento, no solo el número de registros. Un registro lento puede superar igualmente `max.poll.interval.ms`. Los miembros dinámicos y estáticos no tienen los mismos tiempos de reasignación: un miembro estático puede dejar de enviar heartbeats cuando vence el intervalo de poll, y la reasignación puede aplazarse hasta que expire su sesión.

### Confirme después de un procesamiento duradero

La confirmación automática no sabe cuándo termina un efecto externo asíncrono.
Un bucle síncrono con el orden correcto puede usar la confirmación automática, pero no dé por sentado que esta sigue el progreso de un pool de hilos. La siguiente función auxiliar muestra un procesamiento síncrono explícito antes de la confirmación, con la confirmación automática desactivada.

```java
import java.time.Duration;
import java.util.Properties;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;

public final class ConsumerExamples {
    public static void setStaticIdentity(Properties props, String instanceId) {
        if (instanceId == null || instanceId.isBlank() || instanceId.contains("${")) {
            throw new IllegalArgumentException("Supply a resolved, stable, unique consumer instance ID.");
        }
        props.setProperty(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, instanceId);
    }

    public static int processOneBatch(
            Consumer<String, String> consumer,
            java.util.function.Consumer<ConsumerRecord<String, String>> processDurably) {
        var records = consumer.poll(Duration.ofMillis(500));
        for (var record : records) {
            processDurably.accept(record);
        }
        if (!records.isEmpty()) {
            consumer.commitSync();
        }
        return records.count();
    }
}
```

```java
// props already includes bootstrap, TLS/SCRAM, deserializers and the profile below.
try (var consumer = new KafkaConsumer<String, String>(props)) {
    consumer.subscribe(List.of("orders"));
    while (!Thread.currentThread().isInterrupted()) {
        ConsumerExamples.processOneBatch(consumer, application::processDurably);
    }
}
```

`application.processDurably` es código de la aplicación y solo debe devolver el control cuando se haya completado correctamente el efecto requerido. Si falla el procesamiento o la confirmación, deténgase y recupere el estado o reposicione explícitamente el consumidor en los offsets correctos; **no capture un error y siga sondeando** después de los registros fallidos. Un reinicio puede volver a reproducir registros ya procesados, por lo que los efectos externos necesitan una estrategia adecuada de idempotencia o transacciones. Configure el cierre usando el patrón compatible de wakeup/close de KafkaConsumer.

KafkaConsumer no es, por lo general, seguro para subprocesos. Delegar el trabajo requiere colas acotadas, orden por partición, pausa/reanudación en el hilo del consumidor, seguimiento contiguo de los desplazamientos completados y gestión de rebalanceos. Pasar el trabajo a un grupo de hilos por sí solo no es una solución de fiabilidad.

### Resuelva un ID estable para el miembro estático

Java `Properties` **no** expande `group.instance.id=${POD_NAME}`.
Resuelva el valor del entorno en el código de la aplicación o de configuración antes de crear el consumidor:

```java
// One consumer instance per stable logical member in this example.
ConsumerExamples.setStaticIdentity(props, System.getenv("KAFKA_GROUP_INSTANCE_ID"));
```

Para un consumidor por Pod de StatefulSet, un valor de Downward API procedente de `metadata.name` puede proporcionar una identidad lógica estable. Los nombres de los Pods de Deployment cambian en muchas actualizaciones; varios consumidores en un mismo Pod necesitan ID distintos. Cada instancia de consumidor activa necesita un ID único, que solo debe reutilizarse deliberadamente al sustituirla. Los ID activos duplicados pueden provocar el fencing de un miembro.

La pertenencia estática puede evitar rebalanceos innecesarios durante reinicios breves compatibles, pero no garantiza que la asignación permanezca igual cada vez que un Pod regresa antes de que venza un temporizador. También importan la topología, la pertenencia y las suscripciones, y un tiempo de espera de sesión más largo retrasa la recuperación de un miembro que realmente ha fallado.

## Autenticación, autorización y redes

### Separe las dos CA y las propiedades del listener

Con la configuración predeterminada de las CA gestionadas por Strimzi:

- La **CA del clúster** firma los certificados de brokers/componentes internos; los clientes confían en la cadena de certificados de servidor correspondiente.
- La **CA de clientes** firma los certificados de cliente `KafkaUser` para mTLS.
- `user.crt`/`user.key` son credenciales de cliente. El certificado de la CA de clientes de un Secret de usuario no sustituye a la cadena de confianza del broker.

La exposición de red de un listener usa `type: internal`, `loadbalancer`, etc.
El cifrado se indica con `tls: true` y la autenticación de cliente, con
`authentication.type: tls`. No existe un tipo de exposición de listener llamado `tls`.

Lo siguiente es **una entrada de listener adicional** para la matriz existente `spec.kafka.listeners`; no sustituye al listener TLS/SCRAM de la Parte 2. Revise todo el recurso Kafka deseado antes de añadirla:

```yaml
name: mtls
port: 9094
type: internal
tls: true
authentication:
  type: tls
networkPolicyPeers:
- namespaceSelector:
    matchLabels:
      kubernetes.io/metadata.name: kafka-clients
  podSelector:
    matchLabels:
      app: order-service
```

Ambos selectores están en **un mismo peer**, por lo que el Pod debe tener `app=order-service` **y** estar en el espacio de nombres `kafka-clients`. Dos entradas de peer separadas usarían una condición OR: los Pods coincidentes en el espacio de nombres de la política o cualquier Pod en el espacio de nombres seleccionado. Las políticas de red se acumulan, requieren aplicación por parte del CNI y no anulan una segunda política que también permita el tráfico. Considere también el tráfico de salida y la ruta real del tráfico externo o de nodo.

Este usuario mTLS separado conserva la identidad del usuario SCRAM existente:

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

El User Operator debe conciliarlo y el autorizador simple del broker debe estar habilitado. Distribuya las credenciales del usuario y la cadena de confianza del broker en el espacio de nombres de la aplicación mediante un proceso de rotación controlado; Kubernetes no puede montar directamente un Secret de otro espacio de nombres. Confirme la generación actual, que TLS y la autenticación funcionen y qué acciones se permiten o deniegan. Un commit que solo incluya el YAML no concede acceso operativo.

La ruta SCRAM existente sigue necesitando TLS para el cifrado y la rotación de contraseñas. Ni una ACL de Kafka ni una NetworkPolicy sustituyen la otra capa.

### Cifra explícitamente el almacenamiento persistente aprovisionado recientemente

Para el controlador CSI estándar de EBS, utilice una StorageClass cifrada, la configuración predeterminada de cifrado de EBS de la cuenta o región, o ambas. Este ejemplo también conserva los volúmenes y espera a que se programe el Pod antes de seleccionar una AZ:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka-encrypted
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
parameters:
  type: gp3
  encrypted: 'true'
```

Para Auto Mode, utilice su aprovisionador independiente `ebs.csi.eks.amazonaws.com` y las restricciones de topología de la Parte 2, especificando también `encrypted: "true"`. No infiera el cifrado de los PVC aprovisionados dinámicamente a partir de la afirmación de Auto Mode sobre el cifrado de nodos o discos efímeros; la referencia de parámetros de su StorageClass indica que `encrypted` tiene false como valor predeterminado. Confirme el cifrado y la clave KMS del volumen EBS que se haya creado.

Una clave gestionada por el cliente requiere su ARN real y las concesiones adecuadas para el rol/clave, no `key/xxxxxxxx`. Cambiar una StorageClass o habilitar los valores predeterminados de la cuenta no cifra retroactivamente los volúmenes existentes. Planifique una migración compatible de datos o instantáneas y verifique el acceso para restaurarlas antes de sustituir el almacenamiento persistente.

## Capacidad, niveles y retención

Kafka se beneficia de la caché de páginas, pero la CPU (incluidos TLS/compresión), la red, el rendimiento/IOPS del almacenamiento y los límites de memoria de cgroups pueden ser factores determinantes. Incluya el heap, la memoria fuera del heap, la caché de páginas y otras cargas de trabajo en las mediciones. No existe una respuesta universal de «bastan 4–8 GB de heap» ni un ganador en coste entre las instancias optimizadas para memoria.

El almacenamiento por niveles de Kafka está listo para producción desde la versión 3.9 y es compatible con Strimzi 1.3. Aun así, necesita un **plugin RemoteStorageManager** compatible, sus dependencias en la imagen, credenciales/permisos de acceso remoto, retención, limpieza y configuración de recuperación. La integración personalizada de Strimzi usa `spec.kafka.tieredStorage` con la clase/ruta/configuración del plugin. Activar únicamente `remote.log.storage.system.enable` no conecta Kafka con S3.
Consulte las limitaciones de las funciones de esa versión y pruebe qué ocurre cuando el almacenamiento remoto no está disponible, además de probar la restauración.

### La retención es una decisión sobre los datos

El siguiente ejemplo modifica un tema existente para retener datos durante tres días o hasta **50 GiB por partición**, lo que ocurra primero. La eliminación funciona de forma asíncrona y a nivel de segmento; no constituye un límite exacto e instantáneo de bytes.

```bash
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe \
  --entity-type topics --entity-name application-logs
# After reviewing retention/recovery requirements: shortening retention can delete data.
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --alter \
  --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

Reducir la retención puede eliminar irreversiblemente registros necesarios para la reproducción o la recuperación. Con `cleanup.policy=compact`, la limpieza es asíncrona y conserva el último valor por clave, sujeto al comportamiento de tombstones/cleaner; una cardinalidad alta de claves y los segmentos activos/no limpiados aún pueden hacer que el almacenamiento crezca. La compactación no impone un límite estricto de almacenamiento.
`compact,delete` también aplica la retención de eliminación, que puede quitar el último valor de una clave antigua. Diseñe explícitamente los requisitos de reconstrucción del estado y de retención de tombstones.

### Spot e interrupciones

Mantenga el cuórum de controladores en capacidad adecuada y fiable para esta configuración de referencia de producción. Puede considerar capacidad Spot para los brokers en cargas de trabajo que toleren sus riesgos, pero distribuir los Pods por sí solo no evita las reclamaciones correlacionadas. Combine la ubicación de réplicas de broker con conocimiento de los racks, la distribución entre nodos/AZ, la capacidad de reemplazo en la AZ del volumen EBS y la recuperación y el margen de capacidad probados.

El PDB de Strimzi 1.3 cubre los pods del clúster Kafka y limita la expulsión voluntaria. No garantiza el cuórum durante una eliminación forzada, un fallo de nodo, la recuperación de Spot ni todas las operaciones de actualización gradual del Operator. RF=3/minISR=2, un PDB y controladores On-Demand son elementos de diseño, no una prueba de que no habrá pérdidas ni tiempo de inactividad.

## Evidencias que deben conservarse antes de usarlo en producción

- Compatibilidad de versiones/API y ensayos de actualización/reversión y rotación de certificados.
- Límites medidos de particiones, réplicas, CPU/memoria/red/almacenamiento en condiciones de fallo.
- Límites de autorización probados, identidad del cliente y rotación de secretos/confianza.
- Compatibilidad de esquemas/historial, comportamiento de procesamiento/confirmación y gestión de duplicados.
- Evidencias de restauración/conmutación por error con RPO/RTO medidos y los esquemas/las claves requeridos.
- Cobertura de extracción de métricas/alertas/notificaciones, capacidad de consumidores y SLO de la aplicación.
- Retención, cifrado del almacenamiento, supuestos de costes y un responsable de operaciones identificado.

Aplique los controles pertinentes para la carga de trabajo y registre las limitaciones pendientes.
Completar una lista de comprobación genérica no certifica que el sistema esté listo para producción.

## Referencias y validación

Los ejemplos se comprobaron con las clases de configuración de Kafka 4.3.1, su particionador real basado en claves y pruebas de procesamiento/confirmación con MockConsumer, además de esquemas de recursos publicados y fixtures de salida de temas. No sustituyen las pruebas reales de aplicación de TLS/CNI, inspección de volúmenes cifrados, recuperación ante fallos ni corrección de la aplicación.

- [Configuración del productor de Kafka 4.3](https://kafka.apache.org/43/configuration/producer-configs/)
- [Configuración del consumidor de Kafka 4.3](https://kafka.apache.org/43/configuration/consumer-configs/)
- [Almacenamiento por niveles de Kafka 4.3](https://kafka.apache.org/43/operations/tiered-storage/)
- [Particionador basado en claves de Kafka 4.3.1](https://github.com/apache/kafka/blob/4.3.1/clients/src/main/java/org/apache/kafka/clients/producer/internals/BuiltInPartitioner.java)
- [Salida de descripción de temas de Kafka 4.3.1](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/TopicCommand.java)
- [Guía de implementación, TLS y almacenamiento por niveles de Strimzi 1.3.0](https://strimzi.io/docs/operators/1.3.0/deploying.html)
- [Semántica de selectores de NetworkPolicy de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cifrado de EBS de forma predeterminada](https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html)
- [Parámetros de StorageClass de EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html)

## Próximos pasos

[Parte 9: Pruebas de rendimiento de Kafka](./09-kafka-benchmark.md)

[Volver a la página principal](./README.md)

## Cuestionario

[Cuestionario del tema](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
