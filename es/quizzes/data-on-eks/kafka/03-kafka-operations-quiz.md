# Cuestionario de operaciones de Kafka

> **Última actualización**: 16 de octubre de 2026, Strimzi 1.3.0 / Kafka 4.3.1.

Este cuestionario evalúa conocimientos sobre diseño de almacenamiento, escalado de brokers, reequilibrio de Cruise Control, actualizaciones graduales y gestión de fallos en un clúster Kafka administrado por Strimzi en EKS.

## Preguntas de opción múltiple

1. ¿Qué SSD diseña AWS para baja latencia, altas IOPS y durabilidad?
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) io2**

**Explicación:**
io2 Block Express persigue baja latencia, IOPS y durabilidad. Las 256,000 IOPS máximas requieren condiciones como Nitro. Distinga durabilidad de diseño 99.999% y AFR 0.001%. La capacidad y las IOPS influyen en los costos; elija según las mediciones, los requisitos y los precios.
</details>

2. ¿Qué tipo de `KafkaNodePool` permite varios volúmenes independientes por broker?
   - A) `type: persistent-claim`
   - B) `type: jbod`
   - C) `type: ephemeral`
   - D) `type: multi-volume`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `type: jbod`**

**Explicación:**
JBOD proporciona ID de volumen independientes. Al crear logs nuevos, Kafka 4.3.1 suele preferir los directorios que contienen menos logs de particiones; esto no garantiza una asignación por turnos ni un equilibrio en bytes. El movimiento de datos existentes es una operación aparte.
</details>

3. Con una tasa sostenida de 100 MB/s de registros retenidos, una retención de siete días y RF=3, ¿qué fórmula deja libre el 30 % de la capacidad total?
   - A) 100MB/s × 7 días (segundos) × 3
   - B) 100MB/s × 7 días (segundos) × 3 ÷ 0.70
   - C) 100MB/s × 7 días (segundos) ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) 100MB/s × 7 días (segundos) × 3 ÷ 0.70**

**Explicación:**
Sumar un 30 % al tamaño de los datos deja aproximadamente un 23.08 % de capacidad libre. Divida los datos replicados entre 0.70 para mantener libre el 30 %. Use el volumen de bytes de registros retenidos/comprimidos medido de forma sostenida, la retención real y añada por separado la sobrecarga operativa.
</details>

4. ¿Qué script debe ejecutar manualmente un operador para formatear volúmenes gestionados por Strimzi?
   - A) `kafka-storage.sh format` en todos los brokers
   - B) `kafka-configs.sh` para aplicar formato
   - C) Ninguno: Strimzi lo gestiona al iniciar el Pod del broker
   - D) `kafka-reassign-partitions.sh --format`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Ninguno: Strimzi lo gestiona al iniciar el Pod del broker**

**Explicación:**
Strimzi y sus scripts de inicio gestionan la inicialización necesaria de los metadatos de almacenamiento nuevo. Los datos existentes no se borran en cada arranque. No formatee manualmente volúmenes del Operator de forma arbitraria.
</details>

5. Sin un modo autoRebalance coincidente, ¿qué ocurre al aumentar las réplicas del pool de brokers?
   - A) Redistribuye inmediatamente particiones existentes
   - B) Los nuevos brokers se unen, pero las particiones existentes no se reasignan automáticamente
   - C) Los nuevos brokers pasan a liderar todas las particiones
   - D) Los nuevos brokers solo actúan como controladores

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nuevos brokers se unen, pero las particiones existentes no se reasignan automáticamente**

**Explicación:**
Esto describe la ausencia del modo correspondiente. Strimzi 1.3.0 puede reequilibrar automáticamente tras aumentar las réplicas de un pool existente cuando se configura la automatización add-brokers. Crear o eliminar un pool es un evento distinto.
</details>

6. ¿Qué condición de datos debe cumplirse antes de retirar un broker?
   - A) Ninguna: Strimzi lo evacúa automáticamente
   - B) Reasignar primero sus particiones a los brokers restantes
   - C) Reiniciar el clúster
   - D) Eliminar todos los temas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Reasignar primero sus particiones a los brokers restantes**

**Explicación:**
Deben evacuarse todas las réplicas de forma segura. El procedimiento manual incluye temas internos; remove-brokers autoRebalance configurado puede coordinarlo. Mantenga la comprobación de que el broker no esté vacío y verifique los ID de los brokers que se retirarán.
</details>

7. ¿Cuál es el papel principal de Cruise Control?
   - A) Automatizar creación/eliminación de temas
   - B) Recopilar métricas de carga de los brokers y generar/ejecutar automáticamente planes de reasignación según objetivos
   - C) Gestionar commits de offsets de grupos
   - D) Renovar certificados TLS automáticamente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Recopilar métricas de carga de los brokers y generar/ejecutar automáticamente planes de reasignación según objetivos**

**Explicación:**
Calcula propuestas a partir de las métricas de carga y los objetivos, y las ejecuta según la política de aprobación/automatización. Generar una propuesta y mover particiones son operaciones distintas; no ignore a la ligera la falta de métricas ni el incumplimiento de objetivos obligatorios.
</details>

8. ¿Qué `mode` de `KafkaRebalance` mueve particiones a nuevos brokers para darles carga?
   - A) `full`
   - B) `add-brokers`
   - C) `remove-brokers`
   - D) `partial`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `add-brokers`**

**Explicación:**
El modo add-brokers actúa sobre los brokers nuevos especificados y requiere sus ID reales. Los objetivos, el volumen de datos y las restricciones de racks determinan la duración y el impacto; no siempre es más rápido que full. remove-brokers evacúa los brokers antes de retirarlos.
</details>

9. ¿Qué patrón actualiza 4.2.1 a 4.3.1 conservando el formato anterior durante la validación?
   - A) Elevar inmediatamente version y metadataVersion
   - B) Elevar version a 4.3.1, conservar metadataVersion 4.2-IV1 y validar antes de pasar a 4.3-IV0
   - C) Elevar metadataVersion antes de comprobar binarios
   - D) Borrar todos los datos y reiniciar

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Elevar version a 4.3.1, conservar metadataVersion 4.2-IV1 y validar antes de pasar a 4.3-IV0**

**Explicación:**
Conserva explícitamente metadataVersion para validar. Si se omite, Strimzi puede actualizar los metadatos tras la actualización de la versión binaria. El Operator debe ser compatible con las versiones actual y objetivo de Kafka; un cambio posterior de formato puede impedir volver a una versión anterior.
</details>

10. ¿Qué recurso limita los desalojos voluntarios de Pods en un clúster Kafka gestionado por Strimzi?
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) PodDisruptionBudget**

**Explicación:**
Strimzi 1.3.0 normalmente crea un PDB de Kafka por clúster que cubre los Pods de Kafka de todos sus pools. Limita los desalojos voluntarios, no los fallos de nodo/AZ ni el borrado forzado.
</details>

## Preguntas breves

11. ¿Qué configuración de ISR mínimo se tiene en cuenta al comprobar la disponibilidad durante una actualización gradual?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `min.insync.replicas`**

**Explicación:**
Es un factor importante para la disponibilidad, no una garantía incondicional durante cualquier actualización gradual. Verifique el ISR real, el cuórum del controlador, el almacenamiento y la red, además de los tiempos de espera y reintentos del cliente.
</details>

12. ¿Qué componente debe soportar Kafka actual y objetivo antes de actualizar?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Strimzi Operator**

**Explicación:**
Verifique una versión compatible con ambas. No hace falta actualizar el Operator si ya lo es. Si el último elimina soporte actual, planifique versiones intermedias y migración API/CRD.
</details>

13. ¿Qué opción de `kafka-reassign-partitions.sh` genera un plan para una lista de brokers antes de ejecutarlo?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `--generate`**

**Explicación:**
--generate muestra asignaciones actuales/propuestas sin mover. Extraiga Proposed y revise RF, ID, racks y capacidad. --verify completado puede borrar throttles si no se usa preserve-throttles.
</details>

14. Distinga la durabilidad de acks=all de una garantía de éxito durante una actualización gradual.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: La durabilidad es mayor mientras haya copias sincronizadas y un líder/cuórum viable, pero aun así las solicitudes pueden agotar el tiempo de espera o requerir reintentos.**

**Explicación:**
acks=all espera al ISR completo actual mientras se cumple el mínimo de réplicas en sincronía. Deben mantenerse copias sincronizadas y condiciones viables de líder/cuórum/almacenamiento. Gestione timeouts, reintentos y procesamiento repetido aparte.
</details>

## Ejercicios prácticos

15. Defina un ejemplo de pool de brokers para un entorno nuevo con tres volúmenes gp3 de 300 Gi.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: broker
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
  - broker
  storage:
    type: jbod
    volumes:
    - id: 0
      type: persistent-claim
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
      kraftMetadata: shared
    - id: 1
      type: persistent-claim
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
    - id: 2
      type: persistent-claim
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
  resources:
    requests:
      cpu: '2'
      memory: 4Gi
    limits:
      memory: 4Gi
  template:
    pod:
      metadata:
        labels:
          docs.example.com/kafka-role: broker
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 3
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            strimzi.io/cluster: my-cluster
            docs.example.com/kafka-role: broker
```

**Explicación:**
Es una definición nueva, no una orden de reducir un volumen ampliado a 500Gi. Usa gp3-kafka de la Parte 2 y selecciona un volumen de metadatos. Los ajustes Retain y deleteClaim no sustituyen las copias de seguridad.
</details>

16. Cree `KafkaRebalance` en modo `full` para `my-cluster` y escriba la aprobación de la propuesta.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
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
# Review the proposal before executing:
kubectl -n kafka annotate kafkarebalance reviewed-full-rebalance \
  strimzi.io/rebalance=approve --overwrite
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -w
```

**Explicación:**
Cruise Control debe estar habilitado con métricas/objetivos válidos. La autoaprobación está desactivada (false): inspeccione ProposalReady. Distinga las solicitudes manuales de las solicitudes de escalado automático.
</details>

17. Tras ampliar el número de brokers, use sus ID reales y la configuración TLS de administración para generar, extraer, ejecutar y comprobar la reasignación del tema orders.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
set -euo pipefail
: "${DOCS_BOOTSTRAP:?Set reachable TLS bootstrap}"
: "${DOCS_ADMIN_CONFIG:?Set local admin properties file}"
: "${DOCS_BROKER_IDS:?Set verified comma-separated broker IDs}"
: "${DOCS_MOVE_BYTES_PER_SEC:?Choose reviewed throttle bytes/second}"
cat > topics-to-move.json <<'JSON'
{"version":1,"topics":[{"topic":"orders"}]}
JSON
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --topics-to-move-json-file topics-to-move.json --broker-list "$DOCS_BROKER_IDS" \
  --generate > generate-output.txt
python3 extract_reassignment.py generate-output.txt reassignment.json
python3 -m json.tool reassignment.json
# Review the exact proposal before movement:
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --execute --throttle "$DOCS_MOVE_BYTES_PER_SEC"
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --verify --preserve-throttles
```

**Explicación:**
Mantenga los archivos en el entorno donde se ejecuta la CLI. Use ID de brokers y configuración TLS de administración reales; extraiga Proposed, no Current. Consulte el estado del movimiento con --verify --preserve-throttles y después compruebe por separado URP, min-ISR y particiones fuera de línea. Mover un tema no demuestra que el broker se haya evacuado por completo.
</details>

---

[Volver al material](../../../data-on-eks/kafka/03-kafka-operations.md) | [Siguiente cuestionario: Schema Registry](./04-schema-registry-quiz.md)
