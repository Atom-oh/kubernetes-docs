# Cuestionario sobre fundamentos de blockchain

Este cuestionario evalúa tu comprensión del consenso, los árboles de Merkle, la finalidad y las características operativas.

## Preguntas de opción múltiple

1. ¿Cómo se deben comparar los modelos de tolerancia a fallos?
   - A) La blockchain es distribuida, mientras que etcd es de un solo nodo
   - B) Compara el consenso elegido: etcd/Raft es CFT; algunas blockchains usan BFT, mientras que Fabric con permisos también puede usar Raft CFT
   - C) La blockchain ofrece consistencia fuerte, mientras que etcd ofrece coherencia eventual
   - D) etcd no usa criptografía

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Compara el consenso elegido: etcd/Raft es CFT; algunas blockchains usan BFT, mientras que Fabric con permisos también puede usar Raft CFT**

**Explicación:**
Fabric 3.x también ofrece SmartBFT. El hecho de que la membresía tenga permisos y que se use la palabra blockchain no implica por sí solo tolerancia a fallos bizantinos.
</details>

2. ¿Por qué añadir réplicas de nodos completos no aumenta automáticamente la capacidad de escritura de la cadena base?
   - A) Las operaciones criptográficas son lentas
   - B) La validación replicada de nodos completos no aumenta automáticamente la capacidad de escritura de la cadena base, aunque las lecturas RPC pueden escalar
   - C) El ancho de banda de la red P2P es limitado
   - D) El tamaño de bloque es limitado

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La validación replicada de nodos completos no aumenta automáticamente la capacidad de escritura de la cadena base, aunque las lecturas RPC pueden escalar**

**Explicación:**
Los nodos completos, los clientes ligeros y los modelos de distribución de datos con permisos son distintos. No afirmes que cada nodo siempre verifica cada transacción ni que la cantidad de réplicas nunca puede afectar el rendimiento.
</details>

3. ¿Cuál es el beneficio principal de un árbol de Merkle?
   - A) Comprime el tamaño de los bloques
   - B) Una prueba de inclusión de Merkle crece proporcionalmente a log N, donde N es el número de transacciones, lo que permite verificar sin tener toda la cadena y sirve de base para clientes ligeros
   - C) Garantiza el orden de las transacciones
   - D) Acelera el consenso

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una prueba de inclusión de Merkle crece proporcionalmente a log N, donde N es el número de transacciones, lo que permite verificar sin tener toda la cadena y sirve de base para clientes ligeros**

**Explicación:**
Como los hashes de las transacciones se combinan por pares hacia arriba en un árbol binario, para demostrar que una transacción está incluida solo hacen falta los hashes de sus nodos hermanos. Incluso en un bloque con un millón de transacciones, la prueba tiene unos 20 hashes. Esto permite usar clientes ligeros y sirve de base para decidir cómo integrar blockchain con sistemas existentes: ¿se debe ejecutar un nodo completo o basta con una verificación ligera?
</details>

4. ¿Cuál es la razón fundamental por la que el consenso requiere un costo (electricidad para PoW, participación para PoS)?
   - A) Para recompensar a los validadores
   - B) Defensa contra Sybil: sin costo, una parte puede crear identidades y candidatos a bloque ilimitados y paralizar la red
   - C) Para regular la tasa de producción de bloques
   - D) Para conservar el ancho de banda de la red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Defensa contra Sybil: sin costo, una parte puede crear identidades y candidatos a bloque ilimitados y paralizar la red**

**Explicación:**
En un entorno que permite participación anónima, la identidad por sí sola no impide que una parte cree muchas identidades (un ataque Sybil). PoW requiere un costo de cómputo; PoS requiere capital y el riesgo de slashing. La familia BFT **restringe desde el inicio quiénes participan**, evitando así el problema y permitiendo alcanzar el consenso mediante votación, sin la electricidad de PoW ni la participación de PoS. Esta es la base técnica para que los servicios financieros elijan cadenas de consorcio.
</details>

5. ¿Por qué la finalidad es el concepto más importante para las operaciones de infraestructura?
   - A) Determina la velocidad del consenso
   - B) Los datos más recientes que devuelve un nodo pueden no estar finalizados; una reorganización cambia la respuesta
   - C) Determina el tamaño de bloque
   - D) Determina la capacidad de almacenamiento del nodo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los datos más recientes que devuelve un nodo pueden no estar finalizados; una reorganización cambia la respuesta**

**Explicación:**
Un nodo responde según la cadena más reciente que conoce, y si ese bloque se reorganiza después, cambia la respuesta. Esto causa incidentes reales: confirmar un depósito según el bloque más reciente y actuar, solo para que una reorganización lo elimine; o distribuir solicitudes entre nodos cuyas alturas de cadena difieren y obtener respuestas distintas a la misma pregunta. Por lo tanto, la aplicación debe exigir un número de confirmaciones, y la infraestructura debe incluir el estado de sincronización en las comprobaciones de disponibilidad (readiness) y supervisar la divergencia de altura de la cadena.
</details>

6. ¿Por qué un nodo de blockchain necesita un volumen persistente?
   - A) No se pueden recuperar los datos de la cadena desde la red
   - B) El estado puede reconstruirse a partir del historial, pero el proceso tarda y durante ese tiempo el nodo no puede atender solicitudes
   - C) Kubernetes requiere volúmenes persistentes para StatefulSets
   - D) Las claves se almacenan en el directorio de datos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El estado puede reconstruirse a partir del historial, pero el proceso tarda y durante ese tiempo el nodo no puede atender solicitudes**

**Explicación:**
El estado de un nodo (saldos, almacenamiento de contratos) se puede derivar procesando de nuevo el historial de bloques, así que en teoría se puede reconstruir. Sin embargo, una sincronización completa que verifica y procesa de nuevo la cadena desde el bloque génesis tarda un tiempo proporcional a la antigüedad de la cadena; con cientos de GB a varios TB de datos, puede tardar días. Si se pierde el estado al reemplazar un pod, el nodo no puede atender solicitudes durante ese tiempo, por lo que el volumen persistente es obligatorio.
</details>

7. ¿Cómo se deben gestionar las actualizaciones de clientes para un hard fork?
   - A) Aumenta el tamaño de la imagen de contenedor
   - B) Prueba mediante un despliegue canary y distribuye clientes compatibles con la bifurcación antes de su activación; luego, evalúa por separado la reversión a una versión incompatible
   - C) Aumenta el tiempo de reinicio de los pods
   - D) Hay que volver a escribir las políticas de red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Prueba mediante un despliegue canary y distribuye clientes compatibles con la bifurcación antes de su activación; luego, evalúa por separado la reversión a una versión incompatible**

**Explicación:**
El protocolo se activa en un punto definido, pero instalar pronto un cliente compatible no significa necesariamente abandonar la cadena actual. Completa la preparación de toda la flota antes de la fecha límite externa.
</details>

8. ¿En qué se diferencia de forma decisiva la gestión de claves blockchain de la gestión de contraseñas en los sistemas existentes?
   - A) Las claves son más largas
   - B) Planifica la custodia y la recuperación antes de usarlas; la pérdida de una clave privada de firma puede ser irreversible, y las claves privadas de KMS no se pueden exportar
   - C) Las claves se deben rotar periódicamente
   - D) Las claves se transmiten en texto sin cifrar

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Planifica la custodia y la recuperación antes de usarlas; la pérdida de una clave privada de firma puede ser irreversible, y las claves privadas de KMS no se pueden exportar**

**Explicación:**
La recuperación depende del origen de la clave, de los controles de la cuenta/contrato y del diseño de copias de seguridad. Protege el historial de slashing de los validadores y no supongas que un HSM administrado permite exportar su clave privada para migrarla.
</details>
