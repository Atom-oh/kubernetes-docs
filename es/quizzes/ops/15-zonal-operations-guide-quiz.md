# Cuestionario sobre operaciones de clústeres zonales

> **Documento relacionado**: [Operaciones de clústeres zonales](../../ops/15-zonal-operations-guide.md)

## Preguntas de opción múltiple

### 1. ¿Qué significa la ventana de siete días para revertir de forma nativa una actualización de EKS?

- A) El tiempo que debe tardar la reversión
- B) El plazo para poder iniciar la reversión una vez completada la actualización
- C) La vida útil máxima de un nodo
- D) El periodo para restaurar automáticamente los complementos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El plazo para poder iniciar la reversión una vez completada la actualización**

Es el plazo para iniciar la reversión a la versión menor inmediatamente anterior. También importan la versión con la que se creó el clúster, su estado de soporte, las actualizaciones posteriores y la compatibilidad. En Auto Mode, primero se revierten los nodos; los complementos, las aplicaciones y los cambios en los datos no se restauran automáticamente.

</details>

### 2. ¿Qué se debe comprobar después de establecer en cero el peso de un grupo de destino de NLB?

- A) Que todas las conexiones existentes terminen de inmediato
- B) Que TargetGroupBinding se mueva a otro clúster
- C) Por separado, la reducción de flujos nuevos y el drenaje de los existentes
- D) Que ARC reescriba automáticamente los pesos de todos los demás clústeres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Por separado, la reducción de flujos nuevos y el drenaje de los existentes**

Los cambios normales de peso afectan a los flujos nuevos, pero la guía actual de NLB indica que el peso cero también cierra las conexiones existentes después de un breve intervalo. No des por hecho que basta con el drenaje natural: prueba el comportamiento de reconexión y reintento. Antes de cambiar los nodos, comprueba NewFlowCount, ActiveFlowCount y los errores. TGB no tiene un campo de peso, y el cambio zonal de EKS no modifica automáticamente los pesos entre clústeres.

</details>

### 3. ¿Qué combinación configura correctamente Kafka KIP-392?

- A) broker.rack, que configura automáticamente a todos los consumidores
- B) RackAwareReplicaSelector, broker.rack y un client.rack coincidente en el consumidor
- C) Solo unclean.leader.election.enable=true
- D) Las cadenas del nombre de AZ y del ID de AZ son intercambiables

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) RackAwareReplicaSelector, broker.rack y un client.rack coincidente en el consumidor**

El valor completo de replica.selector.class es org.apache.kafka.common.replica.RackAwareReplicaSelector. El recurso Kafka de Strimzi configura los brokers; los consumidores de aplicaciones normales necesitan una configuración aparte. Si no hay una réplica local adecuada, la selección vuelve al líder.

</details>

### 4. ¿Cuál es el orden de preferencia de GLIDE para AZ_AFFINITY_REPLICAS_AND_PRIMARY?

- A) Solo el nodo principal
- B) Réplicas locales → nodo principal local → réplicas o nodo principal de otras AZ
- C) Solo réplicas remotas
- D) Siempre se produce un error si no hay un nodo local

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Réplicas locales → nodo principal local → réplicas o nodo principal de otras AZ**

Los metadatos de AZ del servidor deben coincidir con client_az. Evalúa si puedes tolerar lecturas obsoletas de las réplicas; el porcentaje de lecturas, por sí solo, no basta. Entre las mejoras comunicadas por HotelTrader se incluyen tanto el procesamiento por lotes de solicitudes como el enrutamiento con reconocimiento de AZ.

</details>

### 5. ¿Qué afirmación sobre el endpoint de lectura predeterminado de Aurora es correcta?

- A) Envía cada consulta SQL a una réplica diferente
- B) Garantiza una réplica de lectura en la misma AZ
- C) Distribuye las conexiones y puede usar el nodo de escritura si no hay réplicas
- D) Requiere JDBC Wrapper para conectarse

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Distribuye las conexiones y puede usar el nodo de escritura si no hay réplicas**

No garantiza preferencia por AZ. Los endpoints READER personalizados por AZ requieren gestionar la pertenencia y la alternativa de respaldo. fastestResponse de JDBC usa el tiempo de respuesta, no impone una restricción estricta de AZ. La solicitud de función n.º 1139 se cerró en 2025.

</details>

### 6. ¿Qué afirmación sobre cómo averiguar la AZ de un pod es incorrecta?

- A) La admisión normal al crear un Pod siempre conoce el nodo que eligió el planificador
- B) El ejemplo de Kyverno para AWS MSK gestiona solicitudes de Pod y de enlace
- C) spec.nodeName se puede pasar a un componente de inicialización mediante Downward API
- D) El acceso a IMDS depende del entorno y de la configuración de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) La admisión normal al crear un Pod siempre conoce el nodo que eligió el planificador**

Normalmente, aún no se ha elegido un nodo al crear el Pod. Usa la inyección durante el enlace o consulta la información después de la programación. Downward API no consulta directamente las etiquetas del nodo, y Strimzi no configura automáticamente los consumidores de aplicaciones ajenos a él.

</details>
