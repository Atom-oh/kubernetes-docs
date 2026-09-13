# Cuestionario sobre Strimzi Operator

> **Última actualización**: 12 de septiembre de 2026, Strimzi 1.2.0 / Kafka 4.3.1.

Este cuestionario evalúa fundamentos de Strimzi Operator, métodos de instalación, CRD principales, roles KRaft y consideraciones de despliegue EKS.

## Preguntas de opción múltiple

1. ¿Qué tipo de proyecto CNCF es Strimzi?
   - A) Una malla de servicios
   - B) Un Operator para ejecutar Apache Kafka en Kubernetes
   - C) Un runtime de contenedores
   - D) Una herramienta de pipelines CI/CD

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un Operator para ejecutar Apache Kafka en Kubernetes**

**Explicación:**
Strimzi 1.2 es un proyecto CNCF en incubación que reconcilia el estado deseado de recursos personalizados. La gestión actual de Pods Kafka usa StrimziPodSet. Un Operator no completa automáticamente todas las políticas operativas ni las garantías de disponibilidad.
</details>

2. ¿Cuál describe MENOS acertadamente un reto de ejecutar Kafka directamente como StatefulSet sin Strimzi?
   - A) Gestionar actualizaciones continuas secuenciales
   - B) Emitir y rotar certificados TLS
   - C) Se vuelve imposible construir imágenes de contenedor
   - D) Gestionar movimiento de datos durante el rebalanceo de particiones

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Se vuelve imposible construir imágenes de contenedor**

**Explicación:**
La operación directa es posible, pero exige implementar procedimientos de actualización, certificados, almacenamiento y reasignación. Strimzi reconcilia trabajo repetitivo; recuperación de datos y disponibilidad siguen necesitando validación.
</details>

3. ¿Qué comando añade el repositorio Helm de Strimzi antes de instalar Cluster Operator?
   - A) `helm repo add strimzi https://strimzi.io/charts/`
   - B) `helm repo add kafka https://kafka.apache.org/charts/`
   - C) `helm repo add strimzi https://github.com/strimzi/charts/`
   - D) `helm install strimzi https://strimzi.io/`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) `helm repo add strimzi https://strimzi.io/charts/`**

**Explicación:**
Añada el repositorio oficial y fije 1.2.0 para una instalación nueva. Las API/CRD beta existentes requieren primero la migración oficial; un namespace nuevo no evita conflictos de CRD con ámbito de clúster.
</details>

4. ¿Qué namespaces observa por defecto Strimzi Cluster Operator?
   - A) Todos los namespaces del clúster
   - B) Todos los namespaces `kube-system`
   - C) Solo el namespace donde se despliega
   - D) Solo el namespace `default`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Solo el namespace donde se despliega**

**Explicación:**
El chart predeterminado observa el namespace de su release. Chart 1.2 lo incluye y deduplica junto con watchNamespaces adicionales y crea RoleBindings. Cambiar solo la variable de entorno puede dejar permisos RBAC ausentes.
</details>

5. ¿Qué bloque no se admite en despliegues KRaft actuales de Strimzi 1.2?
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `Kafka.spec.zookeeper`**

**Explicación:**
Strimzi 1.2 usa KRaft y no admite el bloque ZooKeeper. KafkaNodePool define roles controller y broker; no necesita anotaciones de activación antiguas.
</details>

6. ¿Qué valor NO es una entrada válida para `KafkaNodePool.spec.roles`?
   - A) `controller`
   - B) `broker`
   - C) Un rol doble que combine `controller` y `broker`
   - D) `zookeeper`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) `zookeeper`**

**Explicación:**
Los valores reales de enumeración son controller y broker. Ambos pueden listarse como [controller, broker]; dual-role no es una cadena independiente.
</details>

7. ¿Por qué elegir tres votantes de controlador?
   - A) Debe coincidir siempre con el número de brokers
   - B) Queda una mayoría de dos tras fallar un votante
   - C) Las bibliotecas cliente Kafka exigen al menos 3 controladores
   - D) Lo exigen los límites de volúmenes EBS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Queda una mayoría de dos tras fallar un votante**

**Explicación:**
Tres votantes conservan mayoría de dos tras un fallo. Los grupos pares también tienen mayoría; los impares son eficientes para la misma tolerancia. El número de controladores es independiente del de brokers y sigue dependiendo de conectividad y otras condiciones.
</details>

8. ¿Cuál es el provisioner StorageClass del controlador Amazon EBS CSI estándar?
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `ebs.csi.aws.com`**

**Explicación:**
EBS CSI estándar usa ebs.csi.aws.com. EKS Auto Mode usa ebs.csi.eks.amazonaws.com. Cambiar el provisioner no migra PVC existentes.
</details>

9. ¿Qué campo se añade a `KafkaNodePool.spec.template.pod` para distribuir Pods broker entre AZ de forma uniforme?
   - A) `nodeSelector`
   - B) `topologySpreadConstraints`
   - C) `tolerations`
   - D) `priorityClassName`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `topologySpreadConstraints`**

**Explicación:**
Los selectores deben coincidir con etiquetas Pod reales. Exigir tres AZ elegibles también necesita condiciones como minDomains: 3; maxSkew: 1 no crea tres AZ. Compruebe por separado planificación y ubicación de réplicas Kafka por rack.
</details>

10. ¿Qué tipos de listener pueden añadirse a `Kafka.spec.kafka.listeners` cuando clientes externos necesitan acceder a brokers desde fuera del clúster?
    - A) `internal` y `clusterip`
    - B) `loadbalancer` o `nodeport`
    - C) Solo `ingress`
    - D) No se admite exposición externa

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `loadbalancer` o `nodeport`**

**Explicación:**
Strimzi crea Services LoadBalancer o NodePorts. El balanceador de nube depende del controlador/clase. El artículo fija la clase AWS Load Balancer Controller y aplica ajustes internos/de destino IP al bootstrap y a cada Service broker.
</details>

## Preguntas de respuesta breve

11. Nombre los dos componentes internos que sincronizan recursos personalizados `KafkaTopic` y `KafkaUser` con Kafka real.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Topic Operator, User Operator**

**Explicación:**
Topic Operator y User Operator pueden ejecutarse en Entity Operator habilitado; también existen instalaciones independientes. Los CR de tema/usuario necesitan namespace y etiqueta de clúster adecuados.
</details>

12. ¿Qué variable configura Cluster Operator para observar varios namespaces?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `STRIMZI_NAMESPACE`**

**Explicación:**
La variable es STRIMZI_NAMESPACE. En instalaciones Helm, use watchNamespaces/watchAnyNamespace y RBAC correspondiente en vez de generar divergencia con kubectl set env.
</details>

13. ¿Qué tipo de almacenamiento de `KafkaNodePool.spec.storage` permite varios volúmenes EBS por broker para repartir E/S?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: JBOD (type: jbod)**

**Explicación:**
JBOD admite varios IDs de volumen. No garantiza equilibrio automático de datos ni elimina límites EBS/red de la instancia. Como máximo un volumen puede seleccionar kraftMetadata: shared.
</details>

14. ¿Qué condición indica la última reconciliación Kafka exitosa del Operator?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `Ready: True`**

**Explicación:**
Ready=True es la última observación de reconciliación. Compare observedGeneration con generation actual y compruebe readiness Pod, quórum y conectividad real del cliente autenticado.
</details>

15. ¿Qué CRD Strimzi define un clúster independiente de workers para conectores de origen/destino como Debezium?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `KafkaConnect`**

**Explicación:**
KafkaConnect define workers Connect y KafkaConnector representa conectores individuales. Configure por separado gestión de recursos de conectores y autenticación/autorización de workers.
</details>

## Preguntas prácticas

16. Usando operator-values.yaml del artículo, instale Strimzi 1.2.0 en un namespace kafka nuevo.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --version 1.2.0 --namespace kafka --create-namespace \
  -f operator-values.yaml --wait --timeout 10m
kubectl -n kafka rollout status deployment/strimzi-cluster-operator --timeout=300s
kubectl get crd kafkas.kafka.strimzi.io kafkanodepools.kafka.strimzi.io
```

**Explicación:**
Los comandos son para una instalación nueva. Fije el chart y verifique disponibilidad del Operator/CRD. Las instalaciones existentes requieren antes conversión v1 y revisión de propiedad/actualización de CRD.
</details>

17. Escriba un KafkaNodePool de tres brokers con namespace, almacenamiento y restricciones de tres AZ del artículo.

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
      size: 100Gi
      class: gp3-kafka
      deleteClaim: false
      kraftMetadata: shared
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
Usa StorageClass estándar gp3-kafka y el requisito de tres AZ. Haga coincidir etiquetas namespace/clúster y conserve PVC con deleteClaim: false. Auto Mode usa otra StorageClass; los pools no garantizan separación de nodos físicos.
</details>

18. Suponiendo que el Pod autenticado kafka-client esté listo, cree orders y pruébelo con comandos productor/consumidor TLS/SCRAM.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: orders
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 12
  replicas: 3
  config:
    retention.ms: 604800000
    min.insync.replicas: 2
```

```bash
kubectl apply -f orders-topic.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
printf 'strimzi-auth-smoke-test\n' |
  kubectl -n kafka exec -i kafka-client -- \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
    --producer.config /client/client.properties --topic orders
kubectl -n kafka exec kafka-client -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
  --consumer.config /client/client.properties --group order-processor \
  --topic orders --from-beginning --max-messages 1 --timeout-ms 10000
```

**Explicación:**
Deben existir KafkaUser, Secret CA y Pod kafka-client autenticado del artículo. Use propiedades TLS/SCRAM, no el endpoint de texto plano. Compruebe si el primer registro de un tema existente es realmente el recién enviado.
</details>

19. Defina un usuario SCRAM para producir/consumir orders, acceder al grupo order-processor y realizar operaciones de productor idempotente.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders
          patternType: literal
        operations: [Read, Write, Describe]
      - resource:
          type: group
          name: order-processor
          patternType: literal
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

**Explicación:**
Habilite también autenticación del listener y autorizador del clúster. Además de ACL de tema, concede Read al grupo order-processor y capacidad idempotente. Considere identidades distintas de productor/consumidor en servicios reales.
</details>

20. Escriba un fragmento de plantilla bajo spec del KafkaNodePool broker que coincida con etiquetas reales y exija tres AZ elegibles.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
# Merge under KafkaNodePool.spec
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
Combine el fragmento bajo spec del KafkaNodePool broker. Las etiquetas metadata coinciden con selectores; minDomains=3 puede dejar Pods Pending si no hay tres AZ elegibles. Las restricciones estrictas pueden bloquear reemplazos tras perder una AZ; la conciencia de rack Kafka es independiente.
</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/kafka/02-strimzi-operator.md) | [Siguiente cuestionario: Operaciones Kafka](./03-kafka-operations-quiz.md)
