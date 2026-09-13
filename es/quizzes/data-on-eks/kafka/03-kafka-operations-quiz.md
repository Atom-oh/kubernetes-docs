# Cuestionario de operaciones de Kafka

> **Última actualización**: 12 de septiembre de 2026, Strimzi 1.2.0 / Kafka 4.3.1.

Evalúa almacenamiento, escalado de brokers, Cruise Control, actualizaciones graduales y fallos de Kafka administrado por Strimzi en EKS.

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
io2 Block Express persigue baja latencia, IOPS y durabilidad. Las 256,000 IOPS máximas requieren condiciones como Nitro. Distinga durabilidad de diseño 99.999% y AFR 0.001%. Capacidad e IOPS influyen en coste; elija por mediciones, requisitos y precios.
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
JBOD ofrece ID de volúmenes independientes. Kafka 4.3.1 suele preferir directorios con menos logs de particiones para los nuevos, sin garantizar turnos ni equilibrio por bytes. Mover datos existentes es aparte.
</details>

3. Con 100MB/s sostenidos retenidos, siete días y RF=3, ¿qué fórmula mantiene libre 30% de la capacidad total?
   - A) 100MB/s × 7 días (segundos) × 3
   - B) 100MB/s × 7 días (segundos) × 3 ÷ 0.70
   - C) 100MB/s × 7 días (segundos) ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) 100MB/s × 7 días (segundos) × 3 ÷ 0.70**

**Explicación:**
Añadir 30% al dato deja aproximadamente 23.08% libre del total. Divida datos replicados por 0.70 para conservar 30%. Use bytes sostenidos retenidos/comprimidos, retención real y sobrecarga operativa aparte.
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
Strimzi/scripts inicializan los metadatos de almacenamiento nuevo cuando corresponde. Los datos existentes no se borran en cada arranque. No formatee manualmente volúmenes del Operator de forma arbitraria.
</details>

5. Sin un modo autoRebalance correspondiente, ¿qué hace aumentar replicas del grupo de brokers?
   - A) Redistribuye inmediatamente particiones existentes
   - B) Los nuevos brokers se unen, pero las particiones existentes no se reasignan automáticamente
   - C) Los nuevos brokers pasan a liderar todas las particiones
   - D) Los nuevos brokers solo actúan como controladores

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nuevos brokers se unen, pero las particiones existentes no se reasignan automáticamente**

**Explicación:**
Esto describe la ausencia del modo correspondiente. Strimzi 1.2 puede reequilibrar tras aumentar replicas en un grupo existente si se configura add-brokers. Crear/eliminar el grupo es otro evento.
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
Deben evacuarse todas las réplicas de forma segura. El procedimiento manual incluye temas internos; remove-brokers autoRebalance configurado puede coordinarlo. Conserve la comprobación de broker no vacío y valide ID de retirada.
</details>

7. ¿Cuál es el papel principal de Cruise Control?
   - A) Automatizar creación/eliminación de temas
   - B) Recoger carga de brokers y generar/ejecutar planes de reasignación según objetivos
   - C) Gestionar commits de offsets de grupos
   - D) Renovar certificados TLS automáticamente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Recoger carga de brokers y generar/ejecutar planes de reasignación según objetivos**

**Explicación:**
Calcula propuestas desde carga/objetivos y ejecuta según aprobación/automatización. Proponer y mover son operaciones distintas; no omita a la ligera métricas insuficientes o fallos de objetivos obligatorios.
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
Usa los nuevos brokers especificados y necesita sus ID reales. Objetivos, volumen y racks determinan duración/impacto; no siempre es más rápido que full. remove-brokers evacúa antes de retirar.
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
Retiene explícitamente metadataVersion para validar. Si se omite, Strimzi puede actualizar metadatos tras los binarios. El Operator debe soportar ambas versiones y el formato posterior puede impedir downgrade.
</details>

10. ¿Qué recurso limita desalojos voluntarios de Kafka Strimzi?
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) PodDisruptionBudget**

**Explicación:**
Strimzi 1.2 normalmente crea uno por clúster, cubriendo Pods Kafka de todos sus grupos. Limita desalojos voluntarios, no fallos nodo/AZ o borrado forzado.
</details>

## Preguntas breves

11. ¿Qué configuración de ISR mínimo interviene en la disponibilidad durante rollouts?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `min.insync.replicas`**

**Explicación:**
Es una entrada importante, no garantía incondicional durante cualquier rollout. Verifique ISR real, cuórum, almacenamiento/red y timeouts/reintentos cliente.
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

14. Distinga la durabilidad de acks=all de una garantía de éxito durante un rollout.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: La durabilidad mejora mientras hay copias sincronizadas y líder/cuórum viables, pero las solicitudes pueden agotar su tiempo o necesitar reintentos.**

**Explicación:**
acks=all espera al ISR actual completo y exige su mínimo. Deben conservarse copias sincronizadas y condiciones viables de líder/cuórum/storage. Gestione timeouts, reintentos y procesamiento repetido aparte.
</details>

## Ejercicios prácticos

15. Defina un grupo de brokers para entorno nuevo con tres volúmenes gp3 de 300Gi.

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
Es una definición nueva, no una orden de reducir un volumen ampliado a 500Gi. Usa gp3-kafka de la Parte 2 y selecciona un volumen de metadatos. Retain/deleteClaim no son backups.
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
Cruise Control debe estar habilitado con métricas/objetivos válidos. Autoaprobación es false: inspeccione ProposalReady. Distinga solicitudes manuales y de escalado automático.
</details>

17. Tras ampliar brokers, use ID reales y administración TLS para generar, extraer, ejecutar y comprobar reasignación de orders.

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
Mantenga archivos donde corre la CLI. Use ID y configuración TLS reales y extraiga Proposed, no Current. Consulte movimiento con --verify --preserve-throttles y después URP/min-ISR/offline aparte. Mover un tema no demuestra evacuación completa del broker.
</details>

---

[Volver al material](../../../data-on-eks/kafka/03-kafka-operations.md) | [Siguiente cuestionario: Schema Registry](./04-schema-registry-quiz.md)
