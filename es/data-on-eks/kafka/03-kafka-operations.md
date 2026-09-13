# Parte 3: Operaciones de Kafka

> **Última actualización**: 12 de septiembre de 2026, Strimzi 1.2.0 / Kafka 4.3.1.
> **Validación**: Documentación y código de la versión actual, comprobaciones locales de CRD y parches de fusión, generación de propuestas y extracción de JSON, cálculos con Decimal y opciones de la CLI. No se ejecutaron reasignaciones ni actualizaciones de Kafka, ni cambios de volúmenes de AWS.

Este capítulo presupone el despliegue autenticado de Kafka y el grupo exclusivo de brokers de la [Parte 2](./02-strimzi-operator.md). Los comandos operativos pueden mover particiones reales y modificar recursos: revise la configuración, la ubicación y las propuestas antes de ejecutarlos. No aplique sin cambios los procedimientos de escalado de brokers a grupos con rol de controlador.

## 1. Rendimiento y durabilidad del almacenamiento

El retraso de los consumidores no convierte todas las lecturas en aleatorias. Incluso las lecturas históricas secuenciales pueden aumentar la E/S física y la latencia de cola cuando los consumidores intercalan rangos o exceden la caché de páginas. Mida IOPS, rendimiento, latencia de las colas, aciertos de caché y límites de EBS de la instancia.

| Característica | gp3 | io2 Block Express |
| --- | --- | --- |
| Rendimiento base incluido | 3,000 IOPS / 125 MiB/s | Depende de las IOPS aprovisionadas |
| IOPS máximas por volumen | 80,000 | 256,000 en Nitro |
| Rendimiento máximo por volumen | 2,000 MiB/s | 4,000 MiB/s |
| Tamaño máximo | 64 TiB | 64 TiB |
| Durabilidad de diseño publicada | 99.8–99.9% | 99.999% |
| Límite superior de AFR publicado | 0.2% | 0.001% |

Son cifras de diseño del volumen, no un SLA del servicio Kafka ni una garantía frente a fallos arbitrarios. El rendimiento máximo exige determinadas condiciones de tamaño, proporción de IOPS e instancia. gp3 en Outposts e io2 sin Nitro tienen límites diferentes.

La capacidad de almacenamiento forma parte de la factura. Evalúe también el rendimiento de gp3 por encima de la base incluida y las IOPS aprovisionadas de io2. Elija según los requisitos de latencia y durabilidad, las mediciones y los precios regionales vigentes. io2 no se factura únicamente por IOPS, y un gran retraso de consumidores no lo exige automáticamente.

## 2. Retención y espacio libre

Base las estimaciones en los **bytes de registros comprimidos retenidos** y la retención real. Tratar un pico breve como una tasa sostenida durante siete días puede sobreestimar el almacenamiento. Calcule por separado la retención y replicación de cada tema, e incluya compactación, índices, temas internos y copias temporales de reasignación.

Una tasa sintética sostenida de **50 MB/s (10⁶ bytes/s)** durante siete días con RF=3 produce 90.72 TB de registros replicados.

| Interpretación | Capacidad | Fracción libre real |
| --- | --- | --- |
| Añadir 30% al tamaño de los datos | 117.936 TB | Aproximadamente 23.08% |
| Mantener libre 30% de la capacidad total | 129.6 TB, aproximadamente 117.87 TiB | 30% |

El cálculo anterior de unos 118 TB es correcto para la primera interpretación. La segunda usa `data / (1 - 0.30)`. Repartir 129.6 TB entre tres brokers da 43.2 TB por broker, pero el desequilibrio real de las particiones sigue importando. Son ejemplos de cálculo, no recomendaciones de tamaño para los PVC del laboratorio de la Parte 2.

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

## 3. Ampliación y cambios de JBOD

Kafka 4.3.1 normalmente prefiere los directorios con menos registros de particiones al ubicar registros nuevos. No es una distribución simple por turnos ni equilibrada por bytes. Añadir un disco no redistribuye automáticamente los datos existentes.

Este parche de fusión amplía el volumen 0 de la Parte 2 de 100Gi a 500Gi y añade el volumen 1. **Reemplaza toda la matriz volumes**: conserve los demás volúmenes existentes en vez de aplicarlo sin cambios. La configuración de topología y recursos se mantiene.

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

La ampliación depende de StorageClass, CSI y el sistema de archivos. Reducir un PVC, cambiar su clase o los identificadores de volumen son operaciones diferentes. No asigne kraftMetadata: shared a dos volúmenes.

Antes de retirar un disco, inspeccione la ubicación de réplicas y metadatos y evacúe los datos. Strimzi 1.2 admite movimientos JBOD dentro de un broker mediante remove-disks, con sus propios campos y requisitos. deleteClaim: false/Retain no es una copia de seguridad ni demuestra recuperación. No ejecute manualmente kafka-storage.sh format sobre datos gestionados por el Operator.

## 4. Escalado de brokers: vías manuales y automáticas

Estos procedimientos se dirigen a **grupos exclusivos de brokers**. Strimzi 1.2 configura un cuórum estático de controladores; no escale sus grupos del mismo modo. La capacidad de cuórum dinámico de Kafka y su soporte por el Operator son cuestiones distintas.

| Configuración | Cambio de réplicas en un grupo existente |
| --- | --- |
| Sin modo autoRebalance correspondiente | Añadir brokers y mover réplicas existentes son operaciones separadas |
| autoRebalance `add-brokers` | Redistribución automática tras ampliar |
| autoRebalance `remove-brokers` | Evacuación de réplicas coordinada automáticamente al reducir |

La automatización responde a **cambios de replicas en grupos existentes**. Crear o eliminar un grupo no es el mismo desencadenante. Con Kafka 4.3+, la reducción automática también bloquea nuevas asignaciones de réplicas a los brokers mientras se evacúan.

### Ampliación manual

```bash
kubectl -n kafka get kafka my-cluster -o jsonpath='{.spec.cruiseControl.autoRebalance}'
# Continue with the manual path only when the relevant automatic mode is not enabled.
kubectl -n kafka get kafkanodepool broker -o json > broker-before.json
kubectl -n kafka patch kafkanodepool broker --type=merge -p '{"spec":{"replicas":6}}'
kubectl -n kafka get pods -l strimzi.io/pool-name=broker
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
```

No basta con que los Pods estén Running: verifique la generación actual del Operator, el registro de brokers, ISR y capacidad. Los ID de nodo abarcan todo el clúster; no presuponga ID 0–5 ni un Pod my-cluster-broker-0.

### Reducción manual

Identifique los ID reales que se retirarán y evacúe **todas las réplicas, incluidos los temas internos**. Mover solo orders/payments no demuestra que un broker esté vacío. Antes de reducir replicas, compruebe la finalización, RF/ISR restantes, distribución por racks y capacidad.

strimzi.io/remove-node-ids permite seleccionar ID, pero un rango inválido puede recurrir a la selección predeterminada: compárelo con nodeIds actuales. Mantenga habilitada la comprobación de reducción de brokers no vacíos de Strimzi. Omitirla para eliminar brokers con datos no es el procedimiento operativo de referencia.

## 5. Propuestas de Cruise Control y aprobación

Este ejemplo usa aprobación manual por defecto. Añada Cruise Control conservando la configuración existente de Kafka. No omita objetivos obligatorios predeterminados con una lista arbitraria ni active skipHardGoalCheck como valor genérico.

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

Las muestras insuficientes o los objetivos inviables pueden impedir ProposalReady. Revise volumen de movimiento, objetivos, racks y capacidad antes de aprobar. Distinga las solicitudes manuales auto-approval=false de las generadas por el escalado automático. Si ya existe una solicitud previa, use un nombre único para el nuevo cambio.

| Modo | Propósito |
| --- | --- |
| `full` | Redistribuir todo el clúster según objetivos |
| `add-brokers` | Mover réplicas a los nuevos brokers especificados |
| `remove-brokers` | Evacuar réplicas de los brokers especificados |
| `remove-disks` | Retirar réplicas de volúmenes JBOD dentro de un broker |

Los modos de adición y retirada requieren ID de brokers. Un alcance menor no garantiza una ejecución más rápida ni un impacto menor. Este auxiliar valida los ID contra una instantánea del grupo y crea **solo el JSON del CR de propuesta**. No evalúa capacidad, seguridad de ISR/racks ni llama a una API.

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

### Opcional: reequilibrado automático de grupos existentes

Esta configuración puede **mover datos sin una aprobación manual adicional después de cambiar replicas**. Actívela solo bajo una política y objetivos operativos definidos. status.autoRebalance.state=Idle también puede aparecer después de un fallo; inspeccione conjuntamente el resultado de KafkaRebalance generado y el estado de Kafka.

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

## 6. Alternativa manual con la CLI de Kafka

Mantenga los archivos JSON y la configuración administrativa en el entorno que ejecuta la CLI. Un archivo local no está disponible automáticamente dentro de kubectl exec. El cliente necesita acceso a todos los endpoints anunciados y una identidad TLS/SASL autorizada para administrar. El usuario de la aplicación orders de la Parte 2 no es administrador.

Este ejemplo solo abarca orders. No es un inventario completo para retirar un broker.

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

--generate muestra JSON Current y Proposed. Conserve la salida original como registro de la ubicación anterior y extraiga únicamente Proposed a un archivo nuevo. El auxiliar rechaza sobrescribir una salida existente, por lo que cada plan nuevo necesita otro nombre.

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

El auxiliar valida la estructura JSON, no la existencia de brokers, la conservación de RF, el equilibrio de racks ni la integridad del inventario de particiones.

--verify comprueba la reasignación y los movimientos de directorios especificados. **Sin --preserve-throttles, una verificación completada puede borrar las restricciones de brokers/temas, por lo que no es estrictamente de solo lectura.** Coordine la limpieza con otros trabajos que compartan esos límites. Tampoco es una comprobación completa de particiones sin suficientes réplicas o desconectadas.

```bash
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-replicated-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-min-isr-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --unavailable-partitions
```

## 7. Actualizaciones de versión

Elija un Operator que soporte **tanto la versión actual como la objetivo de Kafka**. Si ya soporta ambas, no hace falta actualizarlo solo por el orden. Si el más reciente elimina el soporte de la versión actual, planifique versiones intermedias y conversión de API en lugar de instalarlo directamente.

### Software y metadataVersion

Al omitir metadataVersion, Strimzi puede actualizarlo automáticamente al valor predeterminado tras actualizar los binarios. Cambiar ambos campos en una sola actualización no corrompe por sí mismo el cuórum.

Conservar explícitamente metadataVersion permite una ventana de validación y decisión de recuperación antes de elevarlo. Este ejemplo actualiza **un clúster existente Kafka 4.2.1 / metadatos 4.2-IV1** a 4.3.1 con Strimzi 1.2. No indica reducir metadatos en el laboratorio de la Parte 2, que ya usa 4.3.1.

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

Compruebe conjuntamente status.kafkaVersion, status.kafkaMetadataVersion, status.operatorLastSuccessfulVersion, generation y las imágenes reales. También prepare versiones compatibles de imágenes personalizadas de Kafka, Connect o MirrorMaker.

Tras validar clientes y recuperación, eleve los metadatos si procede. Los nuevos formatos o funciones pueden impedir volver a una versión anterior; revertir Git no garantiza recuperación.

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

No todo cambio de spec reinicia Pods: la configuración dinámica o la ampliación compatible de volúmenes pueden seguir otras vías. Cuando se requieren reinicios, las comprobaciones del Operator no garantizan absolutamente cero interrupciones o pérdidas. Observe datos, ISR, cuórum, tiempos de espera y reintentos de clientes.

## 8. PDB y gestión de fallos

El PDB Kafka predeterminado de Strimzi 1.2 es **uno por clúster Kafka, que cubre sus Pods en todos los grupos de nodos**, no uno por grupo. Si cambian la generación o los PDB personalizados, inspeccione selectores y minAvailable/maxUnavailable reales.

Los PDB limitan desalojos voluntarios. No impiden fallos de nodo/AZ, eliminación directa de Pods ni todas las acciones del Operator. min.insync.replicas no evita por sí solo toda forma de pérdida de datos.

```bash
kubectl -n kafka get pdb -l strimzi.io/cluster=my-cluster -o yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get pods,pvc -l strimzi.io/cluster=my-cluster
```

acks=all mejora la durabilidad bajo sus supuestos de réplicas sincronizadas, pero no garantiza que cada solicitud tenga éxito. Prevea cambios de líder/coordinador, timeouts, reintentos y procesamiento repetido durante reinicios. Reiniciar brokers no detiene necesariamente cada grupo de consumidores completo.

Componentes adicionales como Strimzi Drain Cleaner tienen sus propios modos y comportamiento de PDB. No retire finalizers ni comprobaciones de reducción solo porque una operación haya fallado; primero investigue la causa y las réplicas de datos/metadatos restantes.

## Próximos pasos y referencias

- [Schema Registry](./04-schema-registry.md)
- [Descripción general de Kafka](./README.md)
- [Cuestionario](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
- [Operaciones de Strimzi 1.2](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Diseño de Kafka 4.3](https://kafka.apache.org/43/design/design/)
- [Selección de directorios de registros en Kafka 4.3.1](https://github.com/apache/kafka/blob/4.3.1/core/src/main/scala/kafka/log/LogManager.scala)
- [Implementación del comando de reasignación de Kafka](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/reassign/ReassignPartitionsCommand.java)
- [EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EBS io2 Block Express](https://docs.aws.amazon.com/ebs/latest/userguide/provisioned-iops.html)
- [Precios de EBS](https://aws.amazon.com/ebs/pricing/)
