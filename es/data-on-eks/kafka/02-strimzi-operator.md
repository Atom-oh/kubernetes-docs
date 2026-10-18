# Parte 2: Operador Strimzi

> **Última actualización**: 16 de octubre de 2026. Strimzi 1.3.0, Kafka 4.3.1. Strimzi requiere Kubernetes 1.32 o posterior; la validación local del esquema se realizó con Kubernetes 1.36.2.
> **Validación**: Se procesaron dos configuraciones de Helm, 67 objetos de Kubernetes/CRD y cinco casos de archivos de credenciales con el analizador JAAS nativo de Kafka. No se realizó ninguna instalación en un clúster EKS activo, no se establecieron conexiones TLS, no se verificó la aplicación de ACL del broker ni se aprovisionaron recursos de EBS o NLB.

## 1. Alcance y requisitos previos

Este es un ejemplo de instalación nueva con tres controladores dedicados y tres brokers. Requiere capacidad disponible para programar cargas en tres AZ y una StorageClass adecuada. La actualización de un clúster existente es una operación aparte.

Strimzi es un proyecto de CNCF en fase de incubación que reconcilia recursos de Kafka mediante Kubernetes Operators. El Cluster Operator actual gestiona StrimziPodSets, Pods, Services y PVC. Cuando está habilitado, el Entity Operator ejecuta los Topic Operator y User Operator para reconciliar recursos KafkaTopic y KafkaUser. La instalación de un Operator no aplica automáticamente todas las políticas de reequilibrio, recuperación o disponibilidad.

Requisitos previos:

- Kubernetes 1.32 o posterior y una versión de kubectl compatible con ese clúster. «Cualquier versión de kubectl posterior a la 1.28» no es suficiente para todos los clústeres más recientes.
- Helm 3; aquí se usó Helm 3.21.3 para generar los manifiestos.
- El aprovisionador de volúmenes y la configuración de IAM adecuados para EBS CSI estándar o EKS Auto Mode.
- Nodos/capacidad programables en tres AZ y acceso a los registros de imágenes necesarios.

Strimzi 1.0 y posteriores solo admiten `kafka.strimzi.io/v1`. Primero, convierta los recursos beta antiguos y actualice los CRD siguiendo el procedimiento oficial. Los CRD tienen alcance de clúster: un espacio de nombres nuevo no evita los conflictos con definiciones existentes. El directorio `crds/` de Helm tiene un comportamiento distinto en la instalación inicial y en las actualizaciones de CRD existentes. El siguiente comando helm install no es un procedimiento de actualización para un clúster 0.45 existente.

## 2. Instalar el Cluster Operator

Estos comandos modifican un clúster real. Confirme el contexto y el espacio de nombres antes de utilizar estos comandos para una instalación nueva.

**`operator-values.yaml`**

```yaml
watchNamespaces: []
watchAnyNamespace: false
replicas: 1
```

```bash
kubectl config current-context
helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --version 1.3.0 --namespace kafka --create-namespace \
  -f operator-values.yaml --wait --timeout 10m
kubectl -n kafka rollout status deployment/strimzi-cluster-operator --timeout=300s
kubectl wait --for=condition=Established --timeout=120s \
  crd/kafkas.kafka.strimzi.io crd/kafkanodepools.kafka.strimzi.io \
  crd/kafkatopics.kafka.strimzi.io crd/kafkausers.kafka.strimzi.io
```

El chart predeterminado vigila su propio espacio de nombres. Para vigilar otros espacios de nombres, créelos primero y establezca valores como `watchNamespaces: [kafka-staging]`. El chart 1.3 añade el espacio de nombres de la release sin duplicarlo y genera los RoleBindings correspondientes. Cambiar únicamente la variable de entorno de observación con kubectl set env puede dejar permisos RBAC incompletos y provocar divergencias respecto de la configuración de Helm.

No combine la gestión de una misma instalación mediante Helm, OLM y administración manual. `watchAnyNamespace: true` es una decisión explícita que abarca todo el clúster y está desactivada en este ejemplo.

## 3. Almacenamiento y ubicación

### EBS CSI estándar

Esta StorageClass usa el aprovisionador EBS CSI estándar. Antes de aplicarla, compruebe si ya existen recursos con el mismo nombre. Cambiar el aprovisionador no migra automáticamente los volúmenes existentes a otro controlador.

**`storageclass.yaml`**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

El rendimiento de referencia de gp3 es de 3000 IOPS y 125 MiB/s. El ejemplo anterior con `throughput: "250"` aprovisionaba rendimiento adicional; no era el valor base. También son importantes los límites de EBS/red de la instancia, la replicación de las particiones y los patrones de lectura. JBOD no equilibra automáticamente los datos ni elimina los límites de la instancia.

### Alternativa EKS Auto Mode

Elija esta StorageClass independiente solo para Auto Mode y establezca `gp3-kafka-auto` como **clase de volumen de los NodePool nuevos**. Utilice la ruta del aprovisionador adecuada para el clúster. La migración de los PVC existentes requiere un procedimiento aparte.

**`storageclass-auto.yaml`**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka-auto
provisioner: ebs.csi.eks.amazonaws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
allowedTopologies:
  - matchLabelExpressions:
      - key: eks.amazonaws.com/compute-type
        values: [auto]
```

### Pools de controladores y brokers

Estos archivos hacen referencia a `gp3-kafka` estándar. Los roles reales son `controller` y `broker`; se pueden enumerar ambos juntos, pero `dual-role` no es un valor de enumeración independiente.

Ambos pools requieren tres AZ. Los selectores coinciden con la etiqueta personalizada real del Pod `docs.example.com/kafka-role` y con la etiqueta del clúster; las restricciones topológicas establecen `minDomains: 3`. Los Pods pueden permanecer en estado Pending si solo hay nodos aptos en dos AZ. La restricción estricta también puede impedir la creación de Pods de reemplazo en las AZ restantes durante una interrupción.

Los grupos separados aíslan los roles y la configuración de recursos de los Pods, pero no necesariamente los nodos de trabajo físicos. Utilice afinidad de nodos si necesita separación física. La distribución de réplicas por rack de Kafka y la programación de Pods operan en capas distintas.

**`controller-pool.yaml`**

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: controller
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
  - controller
  storage:
    type: jbod
    volumes:
    - id: 0
      type: persistent-claim
      size: 20Gi
      class: gp3-kafka
      deleteClaim: false
      kraftMetadata: shared
  resources:
    requests:
      cpu: '1'
      memory: 2Gi
    limits:
      memory: 2Gi
  template:
    pod:
      metadata:
        labels:
          docs.example.com/kafka-role: controller
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
            docs.example.com/kafka-role: controller
```

**`broker-pool.yaml`**

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

`kraftMetadata: shared` selecciona el volumen que se utilizará para los metadatos de KRaft; como máximo, un volumen del pool puede tenerlo. `deleteClaim: false` y el valor Retain de la StorageClass son opciones de retención, no copias de seguridad. Los PVC/PV/volúmenes de EBS pueden permanecer y seguir generando costos después de que se eliminen otros recursos.

Tres controladores conservan una mayoría de dos tras el fallo de un miembro votante. Tres brokers satisfacen un objetivo independiente de replicación de datos. Los números impares no son automáticamente seguros; la disponibilidad de la mayoría y la conectividad siguen siendo importantes.

## 4. Clúster de Kafka autenticado

Habilite a la vez un listener interno TLS/SCRAM y el autorizador de ACL. Crear un KafkaUser mientras se prueba mediante un listener de texto sin cifrar y sin autenticación no valida la autenticación de ese usuario.

**`kafka-cluster.yaml`**

```yaml
apiVersion: kafka.strimzi.io/v1
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    version: 4.3.1
    metadataVersion: 4.3-IV0
    rack:
      topologyKey: topology.kubernetes.io/zone
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
    authorization:
      type: simple
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      share.coordinator.state.topic.replication.factor: 3
      share.coordinator.state.topic.min.isr: 2
      default.replication.factor: 3
      min.insync.replicas: 2
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

Strimzi 1.3 usa KRaft y grupos de nodos; no agregue anotaciones de activación heredadas ni bloques de ZooKeeper. `rack.topologyKey` proporciona información de AZ para distribuir las réplicas; no reasigna automáticamente todas las particiones existentes.

Mantenga la compatibilidad entre la versión de Kafka y metadataVersion: este ejemplo usa 4.3.1 / 4.3-IV0. No cambie el campo de versión mientras conserve una sobrescritura de imagen antigua. Los ID de nodo se asignan en todo el clúster; no dé por sentado que todos los grupos tienen un Pod cuyo nombre termina en -0.

```bash
# Use the appropriate StorageClass file for the cluster.
kubectl apply -f storageclass.yaml
kubectl apply -f controller-pool.yaml -f broker-pool.yaml -f kafka-cluster.yaml
kubectl -n kafka wait kafka/my-cluster --for=condition=Ready --timeout=20m
kubectl -n kafka get kafka my-cluster \
  -o custom-columns=NAME:.metadata.name,GENERATION:.metadata.generation,OBSERVED:.status.observedGeneration
kubectl -n kafka get kafkanodepools
kubectl -n kafka get pods,pvc -l strimzi.io/cluster=my-cluster
```

Ready=True es el resultado de reconciliación observado por el Operator. Compare observedGeneration con la generación actual y compruebe que los Pods estén listos, además del quorum y la conectividad de los clientes. Una condición Ready antigua o una fase Running, por sí solas, no demuestran que todos los componentes estén en buen estado en este momento.

## 5. Topic y usuario

**`orders-topic.yaml`**

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

**`order-service-user.yaml`**

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

Para la prueba de humo, este usuario puede producir y consumir mensajes de orders, y leer el grupo order-processor. Las ACL de topic no otorgan ACL de grupo. IdempotentWrite a nivel de clúster admite operaciones de productor idempotentes; no sustituye el permiso Write en otros topics. Para servicios reales, considere utilizar identidades independientes para productores y consumidores.

El User Operator crea un Secret con el nombre del usuario que contiene las entradas password y sasl.jaas.config. También deben estar habilitados el autorizador del clúster y la autenticación del listener. KafkaConnect/KafkaConnector definen workers/conectores independientes; la Parte 5 cubre esas configuraciones.

```bash
kubectl apply -f orders-topic.yaml -f order-service-user.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
kubectl -n kafka wait kafkauser/order-service --for=condition=Ready --timeout=5m
```

## 6. Probar la conectividad TLS/SCRAM

Este archivo incluye un Pod de cliente temporal y código para generar la configuración. Las credenciales se leen desde un volumen Secret, se escapan para las propiedades de Java y se escriben en un archivo, sin poner contraseñas en argumentos de comandos, variables de entorno ni registros. El contenedor init de Python y el contenedor Kafka usan el mismo UID.

El cliente confía en la CA pública mediante un almacén de confianza PEM y mantiene la verificación del nombre de host. La imagen de Kafka está fijada por digest a la versión 4.3.1. No se necesita instalar paquetes durante la ejecución ni suponer que la imagen de Kafka contiene Python.

**`client.yaml`**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-client-config
  namespace: kafka
data:
  client_config.py: |
    """Build Kafka client properties from mounted files without printing credentials."""
    import argparse
    from pathlib import Path


    def property_value(value):
        encoded = []
        escapes = {"\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t", "\f": "\\f"}
        for index, character in enumerate(value):
            if character in escapes:
                encoded.append(escapes[character])
            elif character == " " and index == 0:
                encoded.append("\\ ")
            elif 0x20 <= ord(character) <= 0x7e:
                encoded.append(character)
            else:
                units = character.encode("utf-16-be")
                encoded.extend(f"\\u{int.from_bytes(units[i:i+2], 'big'):04x}" for i in range(0, len(units), 2))
        return "".join(encoded)


    def make_config(jaas, bootstrap, ca_file):
        if not jaas.strip():
            raise ValueError("The mounted JAAS configuration is empty")
        values = {
            "bootstrap.servers": bootstrap,
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "SCRAM-SHA-512",
            "sasl.jaas.config": jaas.strip(),
            "ssl.truststore.type": "PEM",
            "ssl.truststore.location": ca_file,
            "ssl.endpoint.identification.algorithm": "https",
        }
        return "".join(f"{key}={property_value(value)}\n" for key, value in values.items())


    if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("--jaas-file", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--ca-file", required=True)
        parser.add_argument("--bootstrap", required=True)
        args = parser.parse_args()
        args.output.write_text(make_config(args.jaas_file.read_text(), args.bootstrap, args.ca_file), encoding="ascii")
        args.output.chmod(0o600)
---
apiVersion: v1
kind: Pod
metadata:
  name: kafka-client
  namespace: kafka
  labels:
    app: kafka-client
spec:
  automountServiceAccountToken: false
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    runAsGroup: 1001
    fsGroup: 1001
    seccompProfile:
      type: RuntimeDefault
  initContainers:
  - name: client-config
    image: python:3.12.13-slim
    command:
    - python3
    - /bootstrap/client_config.py
    args:
    - --jaas-file
    - /user/sasl.jaas.config
    - --output
    - /client/client.properties
    - --ca-file
    - /ca/ca.crt
    - --bootstrap
    - my-cluster-kafka-bootstrap.kafka.svc:9093
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 50m
        memory: 32Mi
      limits:
        memory: 128Mi
    volumeMounts:
    - name: bootstrap
      mountPath: /bootstrap
      readOnly: true
    - name: user
      mountPath: /user
      readOnly: true
    - name: client
      mountPath: /client
  containers:
  - name: client
    image: quay.io/strimzi/kafka@sha256:e90a1a74af4226f3ca4d1ebef3ab13bdb09754ae17ca4c1444f7fcbb0ca8ea9a
    command:
    - /bin/sh
    - -c
    args:
    - sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    env:
    - name: LOG_DIR
      value: /tmp/kafka-client-logs
    - name: KAFKA_HEAP_OPTS
      value: -Xms128m -Xmx512m
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: client
      mountPath: /client
      readOnly: true
    - name: ca
      mountPath: /ca
      readOnly: true
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: bootstrap
    configMap:
      name: kafka-client-config
  - name: user
    secret:
      secretName: order-service
      items:
      - key: sasl.jaas.config
        path: sasl.jaas.config
  - name: ca
    secret:
      secretName: my-cluster-cluster-ca-cert
      items:
      - key: ca.crt
        path: ca.crt
  - name: client
    emptyDir: {}
  - name: tmp
    emptyDir: {}
```

```bash
kubectl apply -f client.yaml
kubectl -n kafka wait pod/kafka-client --for=condition=Ready --timeout=5m
printf 'strimzi-auth-smoke-test\n' |
  kubectl -n kafka exec -i kafka-client -- \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
    --producer.config /client/client.properties \
    --producer-property acks=all --producer-property enable.idempotence=true \
    --topic orders
kubectl -n kafka exec kafka-client -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
  --consumer.config /client/client.properties --group order-processor \
  --topic orders --from-beginning --max-messages 1 --timeout-ms 10000
kubectl -n kafka delete pod kafka-client
```

Esta es una prueba de humo de conectividad para un topic nuevo del laboratorio. Un topic existente puede contener registros anteriores, así que revise la salida en lugar de suponer que el primer registro es el que acaba de enviar. Una validación real también debe comprobar el rechazo de topics y grupos no autorizados, los fallos de autenticación, la rotación de CA, el acceso a los endpoints de los brokers y la recuperación. Durante la validación local de este capítulo no se enviaron mensajes a Kafka.

## 7. Opcional: clientes en la VPC fuera de Kubernetes

Este parche de combinación crea NLB internos mediante **AWS Load Balancer Controller**. Incluye el listener TLS existente porque un parche JSON de tipo merge reemplaza la matriz completa de listeners. Antes de utilizarlo, sustituya 10.0.0.0/16 por los CIDR de cliente aprobados que correspondan.

La propiedad configuration.class se convierte en el campo loadBalancerClass del Service generado. Las anotaciones para el esquema interno y los destinos IP se aplican tanto al Service de bootstrap como a cada Service de broker, sin suponer que los ID de broker sean 0/1/2. El balanceo de carga de Auto Mode requiere confirmar por separado la clase del controlador y las opciones compatibles.

**`external-listener.patch.yaml`**

```yaml
spec:
  kafka:
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
      - name: external
        port: 9094
        type: loadbalancer
        tls: true
        authentication:
          type: scram-sha-512
        configuration:
          class: service.k8s.aws/nlb
          allocateLoadBalancerNodePorts: false
          loadBalancerSourceRanges: ["10.0.0.0/16"]
          bootstrap:
            annotations:
              service.beta.kubernetes.io/aws-load-balancer-scheme: internal
              service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
          perBrokerAnnotationsTemplate:
            service.beta.kubernetes.io/aws-load-balancer-scheme: internal
            service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file external-listener.patch.yaml
kubectl -n kafka get services -l strimzi.io/cluster=my-cluster
kubectl -n kafka get kafka my-cluster -o jsonpath='{.status.listeners}'
```

Esta opción crea Services de tipo LoadBalancer para bootstrap y para cada broker, con los costos correspondientes. Los clientes deben poder acceder a todos los endpoints de broker que devuelven los metadatos, no solo al de bootstrap. Añadir registros DNS o cambiar a NodePort no resuelve automáticamente los requisitos de enrutamiento, TLS ni ciclo de vida de los nodos.

## Próximos pasos y referencias

- [Operaciones de Kafka](./03-kafka-operations.md)
- [Descripción general de Kafka](./README.md)
- [Cuestionario](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
- [Implementación de Strimzi 1.3.0](https://strimzi.io/docs/operators/1.3.0/deploying.html)
- [Conversión de la API v1 de Strimzi](https://strimzi.io/docs/operators/1.0.0/deploying.html#assembly-api-conversion-str)
- [Versión 1.3.0 de Strimzi](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.3.0)
- [Rendimiento de EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
