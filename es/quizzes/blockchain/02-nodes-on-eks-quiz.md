# Cuestionario sobre la ejecución de nodos blockchain en EKS

Este cuestionario evalúa tu comprensión de la configuración de StatefulSet, el almacenamiento, las comprobaciones de estado y la gestión de bifurcaciones duras (hard forks).

## Preguntas de opción múltiple

1. ¿Qué criterio se propone para decidir si ejecutar nodos de blockchain en EKS?
   - A) Si tienes 10 nodos o más
   - B) Si hay otras cargas de trabajo alrededor del nodo (indexadores, API, supervisión); un nodo aislado es más sencillo de ejecutar en EC2
   - C) Si la cadena es pública o privada
   - D) Si ejecutas un validador

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Si hay otras cargas de trabajo alrededor del nodo (indexadores, API, supervisión); un nodo aislado es más sencillo de ejecutar en EC2**

**Explicación:**
Los nodos blockchain no encajan bien con algunas de las ventajas de Kubernetes (reprogramación rápida, escalado horizontal y actualizaciones progresivas). Aun así, tiene sentido usar EKS para estandarizar las operaciones, gestionar varias cadenas y entornos e integrar los componentes relacionados. Si los indexadores, las API y la supervisión ya están en el clúster, conviene mantener también allí el nodo; para ejecutar un único validador, la abstracción de EKS añade complejidad sin aportar beneficios.
</details>

2. ¿Por qué `terminationGracePeriodSeconds` debe tener un valor generoso para un StatefulSet de nodos de blockchain?
   - A) Las descargas de imágenes tardan tiempo
   - B) Al cerrarse, el cliente debe volcar al disco el estado que mantiene en memoria; una terminación forzada puede dañar la base de datos y obligar a resincronizarla
   - C) Hay que notificar el cierre a los pares P2P
   - D) Desacoplar el volumen tarda tiempo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Al cerrarse, el cliente debe volcar al disco el estado que mantiene en memoria; una terminación forzada puede dañar la base de datos y obligar a resincronizarla**

**Explicación:**
Los 30 segundos predeterminados suelen ser insuficientes. Los clientes blockchain almacenan estado en memoria y deben volcarlo al disco al cerrarse. Una terminación forzada (SIGKILL) puede interrumpir una escritura y dañar la base de datos, lo que obliga a resincronizarla; esto puede tardar horas o días. Por la misma razón, los límites de memoria deben ser generosos: una terminación por falta de memoria (OOM) también es forzada.
</details>

3. ¿Por qué las IOPS se convierten en un cuello de botella antes que la capacidad del almacenamiento de nodos de blockchain?
   - A) Los datos de la cadena se almacenan comprimidos
   - B) Recorrer y actualizar el árbol de estado (Merkle Patricia Trie y similares) requiere acceder a claves dispersas, lo que genera un patrón de acceso aleatorio
   - C) Los bloques solo se escriben de forma secuencial
   - D) Se crean instantáneas con frecuencia

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Recorrer y actualizar el árbol de estado (Merkle Patricia Trie y similares) requiere acceder a claves dispersas, lo que genera un patrón de acceso aleatorio**

**Explicación:**
El uso de disco de un nodo de blockchain consiste en gran medida en lecturas y escrituras aleatorias. Si sobra capacidad, pero faltan IOPS, la sincronización se retrasa y un nodo atrasado no puede atender solicitudes. Por eso, la ventaja clave de gp3 es poder **configurar las IOPS y el rendimiento de forma independiente de la capacidad**. gp2 fija las IOPS en función de la capacidad, así que para aumentar las IOPS había que comprar capacidad que no se necesitaba.
</details>

4. ¿Por qué no debe incluirse el estado de sincronización en la sonda de actividad?
   - A) Las comprobaciones de sincronización añaden carga RPC
   - B) Se reinicia un nodo retrasado, el reinicio lo atrasa más y vuelve a reiniciarse: un ciclo infinito
   - C) Las sondas de actividad no admiten el método exec
   - D) El estado de sincronización solo se puede consultar en la sonda de disponibilidad

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Se reinicia un nodo retrasado, el reinicio lo atrasa más y vuelve a reiniciarse: un ciclo infinito**

**Explicación:**
La sonda de actividad solo debe comprobar «si el proceso está vivo y responde». Incluir allí la sincronización termina los nodos retrasados, y el reinicio demora aún más la sincronización, por lo que nunca pueden ponerse al día. En cambio, **la sonda de disponibilidad debe incluir la sincronización**; si no, un nodo atrasado recibe tráfico y devuelve datos incorrectos basados en una cadena obsoleta. Esta separación es fundamental para las comprobaciones de estado de nodos de blockchain.
</details>

5. Has permitido el tráfico P2P entrante, pero no se conecta ningún par. ¿Cuál es la causa habitual?
   - A) Falta una regla de grupo de seguridad
   - B) No se configuró la dirección anunciada: la dirección IP del Pod que se ve dentro del contenedor es distinta de la dirección accesible externamente, por lo que los demás pares no pueden conectarse
   - C) Solo se abrió el puerto UDP, pero no el TCP
   - D) El límite de pares está configurado en 0

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) No se configuró la dirección anunciada: la dirección IP del Pod que se ve dentro del contenedor es distinta de la dirección accesible externamente, por lo que los demás pares no pueden conectarse**

**Explicación:**
Los protocolos P2P anuncian su propia dirección a los pares. Si la dirección visible dentro del contenedor (la IP del Pod) difiere de la dirección accesible desde el exterior (la IP pública del nodo o la del balanceador de carga), los pares no podrán conectarse a la dirección anunciada. La mayoría de los clientes ofrecen una opción como `--nat extip:<addr>` y, **si no la configuras, abrir el tráfico entrante no atraerá ningún par.** Como cada Pod debe anunciar una dirección distinta, se necesita lógica de inicialización que use el ordinal de StatefulSet o la Downward API.
</details>

6. ¿Por qué hay que tener cuidado con los límites de CPU de los nodos de blockchain, aunque se les dediquen nodos?
   - A) Los límites de CPU afectan el uso de memoria
   - B) Los nodos dedicados reducen la contención entre cargas de distintos equipos, pero los servicios del sistema siguen necesitando reservas y capacidad disponible
   - C) Los límites de CPU se ignoran en nodos dedicados
   - D) La QoS Guaranteed requiere nodos dedicados

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nodos dedicados reducen la contención entre cargas de distintos equipos, pero los servicios del sistema siguen necesitando reservas y capacidad disponible**

**Explicación:**
Kubelet, CNI/CSI, la supervisión y los servicios del sistema operativo siguen ejecutándose. Prueba la carga sostenida y el estado del nodo aunque omitas los límites de CPU de la aplicación.
</details>

7. ¿Qué impacto operativo tuvo el EIP-7251 de Pectra?
   - A) Los requisitos de disco del nodo se redujeron a la mitad
   - B) EIP-7251 permite consolidar validadores que cumplen los requisitos, pero las claves de validador no se corresponden una a una con procesos o máquinas virtuales
   - C) Los clientes de ejecución y de consenso se combinaron en uno
   - D) El calendario de bifurcaciones duras pasó a ser anual

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) EIP-7251 permite consolidar validadores que cumplen los requisitos, pero las claves de validador no se corresponden una a una con procesos o máquinas virtuales**

**Explicación:**
Un cliente validador puede administrar muchas claves. Reducir las entradas de validadores o el trabajo de gestión de claves no demuestra una reducción proporcional de la infraestructura ni de los costos.
</details>

8. ¿Qué tarea de mantenimiento aborda la caducidad de los certificados MSP/TLS de Fabric?
   - A) El fallo del consenso Raft del orderer
   - B) Supervisar la caducidad de los certificados MSP/TLS y ensayar su renovación junto con las operaciones de canal, políticas y consenso
   - C) Los errores de ejecución de chaincode
   - D) Los conflictos entre políticas de canal

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Supervisar la caducidad de los certificados MSP/TLS y ensayar su renovación junto con las operaciones de canal, políticas y consenso**

**Explicación:**
La caducidad de certificados es un riesgo concreto, no una clasificación medida de las interrupciones más frecuentes en este material. Valida también la compatibilidad del operador y la validación de transacciones por parte de los pares.
</details>

9. ¿Qué comprobación es esencial después de una bifurcación dura?
   - A) Reiniciar los Pods
   - B) Comparar los hashes de los bloques con otros nodos y con un explorador público para confirmar que estás en la misma cadena
   - C) Recalcular la capacidad de almacenamiento
   - D) Restablecer la lista de pares

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Comparar los hashes de los bloques con otros nodos y con un explorador público para confirmar que estás en la misma cadena**

**Explicación:**
Un cliente incompatible puede dejar de seguir la cadena canónica o divergir después de la activación; que el proceso siga activo no demuestra que funcione correctamente. Compara los hashes a la **misma altura de bloque y con el mismo estado de finalización** en varios nodos o exploradores independientes y de confianza, teniendo en cuenta la propagación normal y los retrasos de sincronización. Combina esas pruebas con comprobaciones de la versión del cliente, el reconocimiento de la bifurcación y la sincronización; no consideres definitivos ni las cabezas de cadena que no estén a la misma altura ni un único explorador.
</details>
