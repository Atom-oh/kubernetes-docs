# Parte 3: Operaciones de Kafka

> **Última actualización**: 16 de octubre de 2026, Strimzi 1.3.0 / Kafka 4.3.1.
> **Validación**: documentación/código fuente de la versión actual, comprobaciones locales de CRD/merge-patch, generación de propuestas/extracción de JSON, cálculos con Decimal y opciones de CLI. No se ejecutaron reasignaciones de Kafka, actualizaciones ni cambios en volúmenes de AWS.

Este capítulo presupone el despliegue autenticado de Kafka y el pool dedicado a brokers de [Parte 2](./02-strimzi-operator.md). Los comandos operativos pueden mover particiones reales y cambiar recursos: inspeccione la configuración actual, la ubicación y las propuestas antes de ejecutarlos. No aplique sin modificaciones los procedimientos de escalado de brokers a pools con rol de controller.

## 1. Rendimiento y durabilidad del almacenamiento

El retraso de los consumidores no implica que todas las lecturas sean aleatorias. Incluso las lecturas históricas secuenciales pueden aumentar las E/S físicas y la latencia de cola cuando los consumidores intercalan rangos o superan la caché de páginas. Mida IOPS, rendimiento, latencia de cola, aciertos de caché y límites de EBS de la instancia.

| Característica | gp3 | io2 Block Express |
| --- | --- | --- |
| Línea base incluida | 3,000 IOPS / 125 MiB/s | El rendimiento depende de las IOPS aprovisionadas |
| IOPS máximas del volumen | 80,000 | 256,000 en Nitro |
| Rendimiento máximo del volumen | 2,000 MiB/s | 4,000 MiB/s |
| Tamaño máximo | 64 TiB | 64 TiB |
| Durabilidad de diseño publicada | 99.8–99.9% | 99.999% |
| Límite superior de AFR publicado | 0.2% | 0.001% |

Estas cifras corresponden al diseño del volumen; no son un SLA del servicio Kafka ni una garantía frente a fallos arbitrarios. El rendimiento máximo depende del tamaño del volumen, la relación de IOPS y los requisitos de la instancia. Los volúmenes gp3 de Outposts y los io2 que no son Nitro tienen límites diferentes.

La capacidad de almacenamiento forma parte del costo. Evalúe también el rendimiento de gp3 por encima de la línea base incluida y las IOPS aprovisionadas de io2. Elija según los requisitos de latencia/durabilidad, las mediciones y los precios regionales actuales. io2 no se factura solo por las IOPS, y un retraso elevado de los consumidores no requiere automáticamente io2.

## 2. Retención y espacio libre

Base las estimaciones en los **bytes de registros comprimidos retenidos** y en la retención real. Considerar un pico breve como si fuera una tasa sostenida durante siete días puede sobreestimar el almacenamiento. Calcule por separado la retención/replicación de los distintos topics y tenga en cuenta la compactación, los índices, los topics internos y las copias temporales de reasignación.

Un flujo sostenido sintético de **50 MB/s (10⁶ bytes/s)** durante siete días con RF=3 genera 90.72 TB de registros replicados.

| Interpretación | Capacidad | Fracción libre real |
| --- | --- | --- |
| Añadir un 30% al tamaño de los datos | 117.936 TB | Aproximadamente 23.08% |
| Mantener libre el 30% de la capacidad total del disco | 129.6 TB, aproximadamente 117.87 TiB | 30% |

El cálculo anterior de aproximadamente 118 TB es correcto para la primera interpretación. La segunda usa `data / (1 - 0.30)`. Repartir 129.6 TB equitativamente entre tres brokers da 43.2 TB cada uno, pero la distribución desigual real de las particiones sigue siendo importante. Son ejemplos de cálculo, no recomendaciones de dimensionamiento para los PVC de laboratorio de la Parte 2.

**`storage-sizing.py`**

```python
"""Illustrative storage calculation, not measured traffic or a volume recommendation."""
from decimal import Decimal
import json

retained_log_bytes_per_second = Decimal("50000000")  # 50 decimal MB/s, sustained
retention_seconds = Decimal(7 * 24 * 60 * 60)
replication_factor = Decimal(3)
broker_count = Decimal(3)
margin = Decimal("0.30")
replicated_bytes = retained_log_bytes_per_second * retention_seconds * replication_factor
additive_capacity = replicated_bytes * (1 + margin)
free_space_capacity = replicated_bytes / (1 - margin)

print(json.dumps({
    "replicated_log_TB": str(replicated_bytes / Decimal(10**12)),
    "capacity_with_30_percent_added_TB": str(additive_capacity / Decimal(10**12)),
    "free_percent_with_added_margin": str((1 - replicated_bytes / additive_capacity) * 100),
    "capacity_with_30_percent_free_TB": str(free_space_capacity / Decimal(10**12)),
    "capacity_with_30_percent_free_TiB": str(free_space_capacity / Decimal(2**40)),
    "average_per_broker_TB": str(free_space_capacity / broker_count / Decimal(10**12)),
    "assumptions": [
        "Sustained retained-log bytes after compression; not a short traffic peak.",
        "No separate allowance here for indexes, internal topics, compaction or temporary reassignment copies.",
        "Per-broker division assumes equal data placement; measure actual skew."
    ]
}, indent=2))
```

## 3. Expansión de JBOD y cambios

Kafka 4.3.1 suele preferir los directorios con menos registros de particiones al ubicar registros nuevos. No se trata de una distribución simple por turnos ni equilibrada por bytes. Añadir un disco no redistribuye automáticamente los datos existentes.

Este merge patch amplía el volumen 0 de la Parte 2 de 100Gi a 500Gi y añade el volumen 1. **Reemplaza la matriz completa de volúmenes**: conserve cualquier otro volumen existente en lugar de aplicarlo sin cambios. La configuración existente de topología/recursos permanece intacta.

**`storage-expand.patch.yaml`**

```yaml
# For the Part 2 broker pool with one 100Gi volume (id 0).
# Merge patch replaces the entire volumes array; preserve every existing volume.
spec:
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 500Gi
        class: gp3-kafka
        deleteClaim: false
        kraftMetadata: shared
      - id: 1
        type: persistent-claim
        size: 500Gi
        class: gp3-kafka
        deleteClaim: false
```

```bash
kubectl -n kafka get kafkanodepool broker -o yaml > broker-before.yaml
kubectl -n kafka patch kafkanodepool broker --type=merge \
  --patch-file storage-expand.patch.yaml
kubectl -n kafka get pvc -l strimzi.io/cluster=my-cluster
```

La expansión depende de StorageClass/CSI y del sistema de archivos. La reducción de PVC, los cambios de clase y los cambios de ID de volumen no forman parte de esta operación. No asigne kraftMetadata: shared a dos volúmenes.

Antes de retirar un disco, inspeccione la ubicación de las réplicas y los metadatos, y traslade los datos fuera de él. Strimzi 1.3 admite el movimiento de JBOD a nivel de broker mediante el modo de rebalance remove-disks, con sus propios campos y requisitos previos. deleteClaim: false/Retain no constituye una copia de seguridad ni demuestra que se pueda recuperar. No ejecute manualmente kafka-storage.sh format en datos gestionados por el Operator.

## 4. Escalado de brokers: rutas manuales y automáticas

Estos procedimientos se dirigen a **pools dedicados a brokers**. Strimzi 1.3 configura un quórum estático de controllers; no escale de la misma manera los pools con rol de controller. La capacidad de quórum dinámico de Kafka upstream es distinta del soporte del Operator.

| Configuración | Cambio del número de réplicas en un pool existente |
| --- | --- |
| Sin un modo autoRebalance coincidente | La incorporación de brokers y el movimiento de réplicas existentes son operaciones distintas |
| `add-brokers` autoRebalance | Redistribuye automáticamente tras escalar horizontalmente |
| `remove-brokers` autoRebalance | Coordina automáticamente la evacuación de réplicas durante el escalado hacia abajo |

La automatización reacciona a los **cambios de réplicas en pools existentes**. La creación/eliminación de pools no activa lo mismo. Con Kafka 4.3+, el escalado automático hacia abajo también marca los brokers como no programables para impedir nuevas asignaciones de réplicas mientras se lleva a cabo la evacuación.

### Escalado manual hacia arriba

```bash
kubectl -n kafka get kafka my-cluster -o jsonpath='{.spec.cruiseControl.autoRebalance}'
# Continue with the manual path only when the relevant automatic mode is not enabled.
kubectl -n kafka get kafkanodepool broker -o json > broker-before.json
kubectl -n kafka patch kafkanodepool broker --type=merge -p '{"spec":{"replicas":6}}'
kubectl -n kafka get pods -l strimzi.io/pool-name=broker
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
```

Que los Pods estén en ejecución no basta: verifique la generación actual del Operator, el registro de brokers, el ISR y la capacidad. Los IDs de nodo abarcan todo el clúster; no dé por sentado que serán 0–5 ni que habrá un Pod my-cluster-broker-0.

### Escalado manual hacia abajo

Identifique los IDs que realmente se van a retirar y evacue **todas las réplicas, incluidos los topics internos**. Mover solo orders/payments no demuestra que un broker esté vacío. Verifique que la operación haya concluido, el RF/ISR restante, la distribución por racks y la capacidad antes de reducir el número de réplicas.

strimzi.io/remove-node-ids permite seleccionar IDs, pero un rango no válido puede recurrir a la selección predeterminada: compárela con nodeIds actuales. Mantenga habilitada la comprobación de Strimzi que impide escalar hacia abajo con brokers no vacíos. Eludirla para retirar brokers que contienen datos no es el procedimiento operativo estándar.

## 5. Propuestas de Cruise Control y aprobación

Este ejemplo utiliza la aprobación manual de forma predeterminada. Añada Cruise Control sin dejar de conservar la configuración de Kafka existente. No omita los objetivos estrictos predeterminados mediante una lista arbitraria de objetivos ni habilite skipHardGoalCheck como valor predeterminado genérico.

**`cruise-control.patch.yaml`**

```yaml
spec:
  cruiseControl: {}
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file cruise-control.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
```

**`rebalance-full.yaml`**

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaRebalance
metadata:
  name: reviewed-full-rebalance
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
  annotations:
    strimzi.io/rebalance-auto-approval: "false"
spec:
  mode: full
```

```bash
kubectl create -f rebalance-full.yaml
kubectl -n kafka wait kafkarebalance/reviewed-full-rebalance \
  --for=condition=ProposalReady --timeout=30m
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -o yaml
# Review optimizationResult, movement volume, goals, capacity and expected impact first.
kubectl -n kafka annotate kafkarebalance reviewed-full-rebalance \
  strimzi.io/rebalance=approve --overwrite
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -w
```

Un número insuficiente de muestras métricas u objetivos inviables pueden impedir que se alcance ProposalReady. Revise primero el volumen de movimiento, los objetivos, los racks y la capacidad antes de aprobar. Distinga las solicitudes creadas manualmente con auto-approval=false de las solicitudes generadas por el escalado automático. Use un nombre único para cada cambio nuevo si ya existe una solicitud anterior.

| Modo | Propósito |
| --- | --- |
| `full` | Redistribución basada en objetivos en todo el clúster |
| `add-brokers` | Trasladar réplicas a los brokers nuevos especificados |
| `remove-brokers` | Trasladar réplicas fuera de los brokers especificados |
| `remove-disks` | Trasladar réplicas fuera de volúmenes JBOD dentro de un broker |

Los modos add/remove requieren IDs de broker. Un alcance más limitado no garantiza que la ejecución sea más rápida ni que tenga menos impacto. Este auxiliar valida los IDs con una instantánea del pool de brokers y genera **solo JSON de CR de propuesta**. No evalúa la capacidad ni la seguridad del ISR/racks, ni llama a ninguna API.

**`rebalance_request.py`**

```python
"""Generate a manual KafkaRebalance proposal from a broker pool snapshot; no API calls."""
import argparse
import json
from pathlib import Path


def request(pool, mode, broker_ids):
    if pool.get("kind") != "KafkaNodePool" or pool.get("spec", {}).get("roles") != ["broker"]:
        raise ValueError("Use a broker-only KafkaNodePool snapshot")
    metadata = pool.get("metadata", {})
    namespace = metadata.get("namespace")
    cluster = metadata.get("labels", {}).get("strimzi.io/cluster")
    if not namespace or not cluster:
        raise ValueError("The pool must include namespace and cluster label")
    known = pool.get("status", {}).get("nodeIds", [])
    if not known or any(type(value) is not int or value < 0 for value in known):
        raise ValueError("Read a fresh pool snapshot with valid status.nodeIds")
    if mode not in ("add-brokers", "remove-brokers"):
        raise ValueError("Select add-brokers or remove-brokers")
    if not broker_ids or len(broker_ids) != len(set(broker_ids)):
        raise ValueError("Supply distinct broker IDs")
    if any(type(value) is not int or value not in known for value in broker_ids):
        raise ValueError("Every selected broker must belong to the supplied pool")
    return {
        "apiVersion": "kafka.strimzi.io/v1", "kind": "KafkaRebalance",
        "metadata": {
            "name": f"reviewed-{mode}", "namespace": namespace,
            "labels": {"strimzi.io/cluster": cluster},
            "annotations": {"strimzi.io/rebalance-auto-approval": "false"},
        },
        "spec": {"mode": mode, "brokers": sorted(broker_ids)},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--mode", choices=["add-brokers", "remove-brokers"], required=True)
    parser.add_argument("--brokers", nargs="+", type=int, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(request(json.loads(args.pool.read_text()), args.mode, args.brokers), indent=2))
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"Cannot create proposal: {error}\n")
```

```bash
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
# Set actual broker IDs from the snapshot, not controller IDs.
DOCS_BROKER_ID="REPLACE_WITH_VERIFIED_BROKER_ID"
python3 rebalance_request.py --pool broker-pool.json \
  --mode remove-brokers --brokers "$DOCS_BROKER_ID" > remove-proposal.json
python3 -m json.tool remove-proposal.json
# Review the generated proposal before creating/approving it.
```

### Opcional: rebalanceo automático de pools existentes

Esta configuración puede **mover datos sin una aprobación manual independiente después de cambios en las réplicas**. Habilítela solo si existe una política/objetivos operativos definidos. status.autoRebalance.state=Idle también puede aparecer tras un fallo; inspeccione conjuntamente el resultado de KafkaRebalance generado y el estado de Kafka.

**`auto-rebalance.patch.yaml`**

```yaml
# Optional: enables automatic partition movement on existing pool replica changes.
spec:
  cruiseControl:
    autoRebalance:
      - mode: add-brokers
      - mode: remove-brokers
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file auto-rebalance.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get kafkarebalances -l strimzi.io/cluster=my-cluster
```

## 6. Alternativa con la CLI manual de Kafka

Mantenga los archivos JSON y la configuración de administración en el mismo entorno donde se ejecuta la CLI. Un archivo local no está disponible automáticamente dentro de kubectl exec. El cliente necesita acceso a todos los endpoints anunciados y una identidad TLS/SASL con autorización de administración. El usuario de la aplicación orders de la Parte 2 no es administrador.

Este ejemplo solo se aplica a orders. No es un inventario completo para retirar un broker.

```json
{
  "version": 1,
  "topics": [{"topic": "orders"}]
}
```

```bash
set -euo pipefail
: "${DOCS_BOOTSTRAP:?Set a reachable TLS bootstrap endpoint}"
: "${DOCS_ADMIN_CONFIG:?Set the local admin client.properties path}"
: "${DOCS_BROKER_IDS:?Set verified comma-separated target broker IDs}"
# Save the JSON above as topics-to-move.json in this environment.
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "$DOCS_BROKER_IDS" --generate > generate-output.txt
```

--generate imprime tanto el JSON Current como el Proposed. Conserve la salida original como registro de la ubicación anterior y, a continuación, extraiga solo Proposed a un archivo nuevo. El auxiliar se niega a sobrescribir una salida existente; use un nombre de archivo nuevo para cada plan nuevo.

**`extract_reassignment.py`**

```python
"""Extract Kafka 4.3 --generate's proposal; never execute reassignment."""
import argparse
import json
from pathlib import Path

MARKER = "Proposed partition reassignment configuration"


def extract(text):
    if text.count(MARKER) != 1:
        raise ValueError("Expected exactly one proposal marker; inspect the command output")
    proposal, _ = json.JSONDecoder().raw_decode(text.split(MARKER, 1)[1].lstrip())
    if (not isinstance(proposal, dict) or type(proposal.get("version")) is not int
            or proposal["version"] != 1 or not isinstance(proposal.get("partitions"), list)
            or not proposal["partitions"]):
        raise ValueError("Expected a nonempty version-1 reassignment proposal")
    seen = set()
    for entry in proposal["partitions"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid partition entry")
        topic, partition, replicas = entry.get("topic"), entry.get("partition"), entry.get("replicas")
        if not isinstance(topic, str) or not topic or type(partition) is not int or partition < 0:
            raise ValueError("Invalid topic/partition")
        if (topic, partition) in seen:
            raise ValueError("Duplicate topic/partition")
        seen.add((topic, partition))
        if (not isinstance(replicas, list) or not replicas
                or any(type(broker) is not int or broker < 0 for broker in replicas)
                or len(replicas) != len(set(replicas))):
            raise ValueError("Invalid replica list")
        if "log_dirs" in entry:
            if (not isinstance(entry["log_dirs"], list) or len(entry["log_dirs"]) != len(replicas)
                    or not all(isinstance(directory, str) for directory in entry["log_dirs"])):
                raise ValueError("Log directory and replica lists must have equal lengths")
    return proposal


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        proposal = extract(args.input.read_text())
        with args.output.open("x") as stream:
            json.dump(proposal, stream, indent=2)
            stream.write("\n")
    except (ValueError, OSError, TypeError, AttributeError) as error:
        parser.exit(1, f"Proposal extraction failed: {error}\n")
```

```bash
python3 extract_reassignment.py generate-output.txt reassignment.json
python3 -m json.tool reassignment.json
# Review topic coverage, replica order/count, broker IDs, racks and capacity.
: "${DOCS_MOVE_BYTES_PER_SEC:?Choose the reviewed movement throttle in bytes/second}"
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --execute \
  --throttle "$DOCS_MOVE_BYTES_PER_SEC"

# Status check without removing configured throttles:
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --verify --preserve-throttles
```

El auxiliar valida la estructura del JSON, no la existencia de los brokers, el RF retenido, el equilibrio entre racks ni el inventario completo de particiones.

--verify comprueba las reasignaciones/movimientos de directorios de registros especificados. **Sin --preserve-throttles, la verificación completada puede borrar la configuración de throttles de brokers/topics, por lo que no es una operación puramente de lectura.** Coordine la limpieza con otros trabajos que compartan esos límites. La verificación tampoco es una comprobación completa del estado de las particiones subreplicadas/fuera de línea.

```bash
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-replicated-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-min-isr-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --unavailable-partitions
```

## 7. Actualizaciones de versión

Elija una combinación de Operator que admita **tanto la versión actual de Kafka como la de destino**. No hace falta actualizar el Operator solo para respetar el orden si ya admite ambas versiones. Si el Operator más reciente deja de admitir la versión actual de Kafka, planifique versiones intermedias compatibles y la conversión de API en lugar de instalarlo directamente.

### Software y metadataVersion

Si se omite metadataVersion, Strimzi puede actualizarla automáticamente al valor predeterminado después de actualizar los binarios de Kafka. Cambiar ambos campos en una sola actualización no corrompe inherentemente el quórum.

Retener explícitamente la metadataVersion anterior puede proporcionar un período de validación/recuperación antes de aumentarla. Este ejemplo actualiza un clúster **existente de Kafka 4.2.1 / metadata 4.2-IV1** a 4.3.1 con Strimzi 1.3. No es una instrucción para reducir los metadatos del laboratorio de la Parte 2, que ya está en 4.3.1.

**`upgrade-binaries.patch.yaml`**

```yaml
# Only for an existing Kafka 4.2.1 cluster currently using metadata 4.2-IV1.
spec:
  kafka:
    version: 4.3.1
    metadataVersion: 4.2-IV1
```

```bash
kubectl -n kafka get kafka my-cluster -o yaml > kafka-before-upgrade.yaml
# Check current version, metadataVersion and any custom image override first.
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file upgrade-binaries.patch.yaml
kubectl -n kafka get pods -l 'strimzi.io/cluster=my-cluster,strimzi.io/pool-name' \
  -o 'custom-columns=NAME:.metadata.name,IMAGES:.spec.containers[*].image'
kubectl -n kafka get kafka my-cluster -o yaml
```

Compruebe conjuntamente status.kafkaVersion, status.kafkaMetadataVersion, status.operatorLastSuccessfulVersion, la generación y las imágenes reales de los Pod. También deben prepararse las imágenes personalizadas de Kafka, Connect o MirrorMaker para versiones compatibles.

Después de validar los clientes y el plan de recuperación, aumente los metadatos si corresponde. Los metadatos/funciones nuevos pueden impedir la reversión; revertir en Git no garantiza la recuperación.

**`upgrade-metadata.patch.yaml`**

```yaml
# Apply only after validating the completed binary upgrade and recovery plan.
spec:
  kafka:
    metadataVersion: 4.3-IV0
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file upgrade-metadata.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
```

No todos los cambios de spec reinician Pods: la configuración dinámica de Kafka o la expansión de volúmenes admitida pueden seguir otras rutas. Cuando se requieren reinicios, las comprobaciones de disponibilidad del Operator no garantizan que no haya interrupciones ni pérdida de datos. Vigile el estado de los datos, el ISR, el quórum de controllers, los tiempos de espera de los clientes y los reintentos.

## 8. PDB y gestión de fallos

El PDB predeterminado de Kafka de Strimzi 1.3 es **uno por clúster de Kafka, que abarca los Pods de Kafka de todos sus pools de nodos**, no uno por pool. Si la configuración de generación o los PDB personalizados difieren, inspeccione los selectores reales y minAvailable/maxUnavailable.

Los PDB limitan las expulsiones voluntarias. No impiden fallos de nodo/AZ, la eliminación directa de Pods ni todas las acciones del Operator. min.insync.replicas no es un interruptor único que impida todas las formas de pérdida de datos.

```bash
kubectl -n kafka get pdb -l strimzi.io/cluster=my-cluster -o yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get pods,pvc -l strimzi.io/cluster=my-cluster
```

acks=all ofrece mayor durabilidad bajo sus supuestos sobre las réplicas sincronizadas, pero no garantiza que todas las solicitudes de la aplicación tengan éxito. Planifique los cambios de líder/coordinador, los tiempos de espera, los reintentos y el procesamiento repetido durante los reinicios. Los reinicios de brokers no necesariamente detienen por completo todos los grupos de consumidores.

Los componentes adicionales, como Strimzi Drain Cleaner, tienen sus propios modos admitidos y comportamiento de PDB. No elimine finalizers ni comprobaciones de escalado hacia abajo solo porque haya fallado una operación; primero investigue la causa y las réplicas de datos/metadatos restantes.

## Siguientes pasos y referencias

- [Schema Registry](./04-schema-registry.md)
- [Descripción general de Kafka](./README.md)
- [Cuestionario](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
- [Operaciones de Strimzi 1.3](https://strimzi.io/docs/operators/1.3.0/deploying.html)
- [Diseño de Kafka 4.3](https://kafka.apache.org/43/design/design/)
- [Selección de directorios de registros en Kafka 4.3.1](https://github.com/apache/kafka/blob/4.3.1/core/src/main/scala/kafka/log/LogManager.scala)
- [Implementación del comando de reasignación de Kafka](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/reassign/ReassignPartitionsCommand.java)
- [EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EBS io2 Block Express](https://docs.aws.amazon.com/ebs/latest/userguide/provisioned-iops.html)
- [Precios de EBS](https://aws.amazon.com/ebs/pricing/)
