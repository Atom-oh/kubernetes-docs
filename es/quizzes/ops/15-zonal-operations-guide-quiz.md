# Cuestionario sobre operaciones de clústeres zonales

> **Documento relacionado**: [Operaciones de clústeres zonales](../../ops/15-zonal-operations-guide.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es la ventana de elegibilidad para el rollback nativo de la versión de Kubernetes de Amazon EKS (GA en julio de 2026)?

- A) 24 horas
- B) 7 días
- C) 30 días
- D) Ilimitado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 7 días**

**Explicación:**
El rollback nativo de EKS puede revertir una versión menor a la vez, dentro de los 7 días posteriores a la actualización. Los clústeres creados con la versión de destino, aquellos para los que han transcurrido más de 7 días o los clústeres que ya se actualizaron nuevamente no son elegibles.

</details>

### 2. ¿Qué mecanismo se utiliza para desviar el tráfico de una zona durante una actualización Zonal In-Place?

- A) `kubectl drain`
- B) Ajustar el peso del Target Group
- C) Esperar a que expire el DNS TTL
- D) Recrear el clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ajustar el peso del Target Group**

**Explicación:**
En lugar de modificar algo dentro del clúster, ajustas el peso del Target Group vinculado mediante TargetGroupBinding para reducir o detener el tráfico hacia una zona determinada. En situaciones no planificadas, como una interrupción de AZ, ARC Zonal Shift realiza esta función automáticamente.

</details>

### 3. ¿Qué se debe configurar en los brokers de Kafka para habilitar KIP-392 (Follower Fetching)?

- A) `auto.leader.rebalance.enable=true`
- B) `replica.selector.class=RackAwareReplicaSelector`
- C) `unclean.leader.election.enable=true`
- D) `min.insync.replicas=2`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `replica.selector.class=RackAwareReplicaSelector`**

**Explicación:**
Los brokers necesitan tener `replica.selector.class` configurado como `RackAwareReplicaSelector` y tener asignado un `broker.rack` (ID de AZ). Del lado del consumidor, la propiedad `client.rack` debe configurarse con el propio ID de AZ del consumidor para que las recuperaciones se redirijan a un follower del mismo rack.

</details>

### 4. ¿Qué estrategia `ReadFrom` de Valkey GLIDE se recomienda para cargas de trabajo con más del 99 % de lecturas?

- A) `PRIMARY`
- B) `PREFER_REPLICA`
- C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`
- D) Distribución aleatoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`**

**Explicación:**
Primero prefiere una réplica en la misma AZ, recurre al primary en la misma AZ y solo accede a otras AZ como último recurso. Para cargas de trabajo dominadas por lecturas, este es el equilibrio recomendado entre ahorro de costos y disponibilidad: HotelTrader redujo los costos de transferencia entre AZ en un 95 % después de adoptarla.

</details>

### 5. ¿Qué afirmación sobre el endpoint de reader predeterminado de Amazon Aurora es correcta?

- A) Prioriza automáticamente las réplicas en la misma AZ
- B) Es DNS round-robin sin reconocimiento de AZ
- C) Siempre enruta al primary
- D) No se puede usar sin AWS Advanced JDBC Wrapper

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es DNS round-robin sin reconocimiento de AZ**

**Explicación:**
El endpoint de reader predeterminado de Aurora no tiene afinidad de AZ. Puedes evitar esta limitación con endpoints personalizados por AZ o con la estrategia `fastestResponse` de AWS Advanced JDBC Wrapper, pero la afinidad de AZ real sigue siendo una solicitud de funcionalidad abierta en el repositorio `aws-advanced-jdbc-wrapper`.

</details>

### 6. ¿Qué afirmación sobre cómo un pod puede determinar su propia AZ es INCORRECTA?

- A) Puede consultarla directamente a través de EC2 IMDS
- B) Una política de mutación de Kyverno puede copiar una etiqueta de nodo en una anotación de pod
- C) La Kubernetes Downward API inyecta de forma predeterminada la etiqueta de zona del nodo en el pod
- D) Un operator como Strimzi puede proporcionar reconocimiento de rack como una funcionalidad integrada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La Kubernetes Downward API inyecta de forma predeterminada la etiqueta de zona del nodo en el pod**

**Explicación:**
La Downward API no inyecta automáticamente la etiqueta `topology.kubernetes.io/zone` de un nodo en un pod. Por eso se necesita uno de los otros enfoques: consulta directa de IMDS, copia de etiquetas durante la admisión basada en Kyverno o soporte integrado de un operator como Strimzi.

</details>
