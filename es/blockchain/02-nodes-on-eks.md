# Ejecución de nodos de blockchain en EKS

> **Versiones compatibles**: Kubernetes 1.33+ (Amazon EKS), Hyperledger Fabric 2.5 / 3.x
> **Última actualización**: 13 de septiembre de 2026

## Qué cubre este documento

- Cómo traducir las características operativas de [Fundamentos](./01-fundamentals.md) en una configuración real de Kubernetes: StatefulSets, almacenamiento y exposición P2P
- Cómo incluir el estado de sincronización en las comprobaciones de estado y por qué las comprobaciones de estado habituales no funcionan
- Las diferencias operativas entre los nodos de Ethereum y Hyperledger Fabric, y cómo gestionar los calendarios de hard forks

## Pregunta inicial: ¿debería ejecutar esto en EKS?

Antes de hablar de la configuración, considera esta pregunta. **Los nodos de blockchain no encajan bien con algunas de las fortalezas de Kubernetes.**

| Lo que Kubernetes hace bien | En el caso de un nodo de blockchain |
|---|---|
| Programación y reprogramación rápidas | El coste de reconstruir el estado hace que reprogramar sea caro |
| Escalado horizontal del rendimiento | Las réplicas pueden aumentar la capacidad agregada de RPC/lectura y la disponibilidad, pero no aumentan automáticamente la capacidad de escritura/consenso de la cadena base |
| Actualizaciones declarativas y progresivas | Los hard forks se activan simultáneamente |
| Mover Pods entre nodos | Está vinculado al disco local |

Aun así, hay motivos para usar EKS.

| Motivo | Contenido |
|---|---|
| **Estandarización operativa** | Si ya ejecutas todo en EKS, es mejor no añadir otra pila |
| **Varias cadenas/entornos** | Mainnet, redes de prueba y varios protocolos gestionados de la misma manera |
| **Integración con componentes relacionados** | Los indexadores, las puertas de enlace de API y la supervisión ya están en el clúster |
| **Orientación oficial para Fabric** | Hyperledger Fabric cuenta con un ecosistema maduro de operadores de Kubernetes |

**Por el contrario, EC2 sin Kubernetes es mejor cuando** solo tienes unos pocos nodos (1–3) y ninguna otra carga de trabajo en el clúster. En ese caso, la abstracción de EKS añade complejidad sin aportar beneficios. Ejecutar un único validador no requiere EKS.

**El criterio para decidir**: **¿hay otras cargas de trabajo alrededor del nodo de blockchain?** Si los indexadores, las API y la supervisión están en el clúster, tiene sentido mantener el nodo junto a ellos; si el nodo está aislado, EC2 es más sencillo.

## Configuración básica: StatefulSet y Service headless

### Por qué no usar un Deployment

| Requisito | Deployment | StatefulSet |
|---|---|---|
| Nombre estable (identidad P2P) | ✗ sufijo aleatorio | ✓ `node-0`, `node-1` |
| Volumen fijo por Pod | ✗ compartido o aleatorio | ✓ PVC por Pod mediante `volumeClaimTemplates` |
| DNS estable | ✗ | ✓ con un Service headless, `node-0.svc...` |
| Inicio y apagado ordenados | ✗ | ✓ |

Los requisitos de «identidad de peer estable» y «estado por Pod» de [Fundamentos](./01-fundamentals.md) son precisamente lo que proporcionan los StatefulSets.

### Esquema incompleto, solo para pruebas (no es un manifiesto desplegable)
Este fragmento omite el selector y las etiquetas de plantilla obligatorios del StatefulSet, la imagen y los argumentos, el Service headless, la StorageClass y la configuración posterior a Merge de EL/CL Engine API/JWT. No lo apliques tal cual. Completa y valida esos recursos en un entorno de pruebas aislado **sin fondos reales ni claves de firma de validadores**. Mantén JSON-RPC y Engine API en privado y autenticados; la accesibilidad P2P no debe exponer RPC ni puntos de conexión de firma.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: eth-node
spec:
  serviceName: eth-node          # headless Service name
  replicas: 2
  template:
    spec:
      terminationGracePeriodSeconds: 300   # graceful shutdown needs time
      containers:
        - name: execution
          # ... execution client
          ports:
            - { name: p2p-tcp, containerPort: 30303, protocol: TCP }
            - { name: p2p-udp, containerPort: 30303, protocol: UDP }
            - { name: rpc,     containerPort: 8545 }
          volumeMounts:
            - { name: data, mountPath: /data }
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: gp3-high-iops
        resources: { requests: { storage: 2Ti } }
```

Hay tres diferencias respecto a las cargas de trabajo habituales.

**① `terminationGracePeriodSeconds` debe ser largo.** Los clientes de blockchain deben volcar el estado en memoria al disco durante el apagado. Un cierre forzado puede **dañar la base de datos y obligar a resincronizar.** Los 30 segundos predeterminados no suelen ser suficientes.

**② Los puertos P2P usan TCP y UDP.** Muchos protocolos separan la detección de peers (UDP) de las conexiones propiamente dichas (TCP). Si abres solo uno, no podrás encontrar peers o no podrás conectarte.

**③ El volumen es grande.** Se aborda en la sección de almacenamiento a continuación.

## Almacenamiento: la decisión de diseño más importante

### Dónde está el cuello de botella

El patrón de acceso al disco de un nodo de blockchain se caracteriza por **muchas lecturas y escrituras aleatorias**, ya que recorrer y actualizar el árbol de estado (Merkle Patricia Trie y estructuras similares) implica acceder a claves dispersas.

Por eso, **las IOPS se convierten en el cuello de botella antes que la capacidad.** Si tienes capacidad de sobra, pero las IOPS son insuficientes, la sincronización se queda atrás, y un nodo que va atrasado no puede prestar servicio.

| Requisito | Motivo |
|---|---|
| **Muchas IOPS** | Patrón de acceso aleatorio |
| **Baja latencia** | Las consultas de estado forman parte de la ruta de procesamiento de bloques |
| **Rendimiento sostenido** | Carga continua, no en ráfagas |

### Cómo elegir un volumen de EBS

| Tipo de volumen | Idoneidad |
|---|---|
| **gp3** | Opción predeterminada. La ventaja clave es **configurar las IOPS y el rendimiento independientemente de la capacidad** |
| **io2 / io2 Block Express** | Cuando necesitas más IOPS y una latencia más constante |
| **gp2** | No recomendado: las IOPS están vinculadas a la capacidad y no se pueden ajustar |
| **Almacén de instancias (NVMe)** | El más rápido, pero **se pierde cuando se detiene la instancia**, así que úsalo solo si puedes aceptar una resincronización |

**Por qué importa que gp3 tenga ajustes independientes**: gp2 fija las IOPS por unidad de capacidad, así que aumentar las IOPS implicaba comprar capacidad que no necesitabas. gp3 configura por separado la capacidad y las IOPS, por lo que **puedes ajustarlas a tus necesidades reales.** Consulta [Prueba comparativa de EBS gp2 frente a gp3](../storage/01-ebs-gp2-gp3-benchmark.md) para ver las diferencias concretas.

**La contrapartida del almacén de instancias** está clara: ofrece el mejor rendimiento, pero el estado puede desaparecer. Elígelo si puedes aceptar el tiempo de resincronización (tienes un proceso para restaurar desde instantáneas) y ejecutas varios nodos, de modo que una resincronización no interrumpa el servicio.

### Planificación de la capacidad: el crecimiento es lo importante

Los datos de la cadena crecen **monótonamente.** Esto cambia la naturaleza de la planificación de la capacidad.

| Aspecto | Implicación |
|---|---|
| Crecimiento continuo | **Es obligatorio contar con un plan para ampliar el volumen**; tarde o temprano lo necesitarás |
| La tasa de crecimiento depende de la actividad del protocolo | Deja margen y configura alarmas |
| Opciones de poda | Los clientes ofrecen modos que descartan datos antiguos; úsalos si no necesitas un nodo de archivo |

**Los volúmenes de EBS admiten ampliación en línea** (seguida de una ampliación del sistema de archivos), por lo que la respuesta estándar es una StorageClass con `allowVolumeExpansion: true` y alarmas de uso del disco.

### Recomendaciones oficiales de hardware: EIP-7870

Usa [EIP-7870](https://eips.ethereum.org/EIPS/eip-7870) y la [Guía para ejecutar un nodo](https://ethereum.org/developers/docs/nodes-and-clients/run-a-node/) como **recomendaciones iniciales**, no como garantía de que una instancia de EKS o un volumen de EBS las cumplan. Verifica el cliente seleccionado, el fork, la poda y el crecimiento medido.

| Aspecto | Mínimo | **Recomendado (EIP-7870, nodo completo)** |
|---|---|---|
| **CPU** | 2+ núcleos | 4+ núcleos (**8+ si valida**) |
| **RAM** | 16 GB (se recomiendan 32 GB) | 32 GB (**64 GB si valida**) |
| **Disco** | **SSD NVMe de 2 TB** | **SSD NVMe de 4 TB** (se **desaconsejan** las unidades sin DRAM y QLC) |
| **Ancho de banda** | 25+ Mbit/s | 50 Mbit/s de bajada / 15+ Mbit/s de subida (**25+ de subida si valida**) |

Hay tres aspectos importantes para interpretar estos datos.

**① El cuello de botella es el disco.** ethereum.org lo dice explícitamente: «El cuello de botella de tu hardware suele ser el espacio en disco. Sincronizar la blockchain de Ethereum requiere mucha entrada/salida». Por eso, las IOPS se mencionaron primero.

**② EIP-7870 ofrece recomendaciones de hardware; no demuestra que una configuración específica de EBS las cumpla.** La latencia de EC2/EBS, el ancho de banda de la instancia y las IOPS y el rendimiento del volumen difieren de los de un NVMe local. Mide la sincronización y el procesamiento en régimen estable con el cliente y el perfil de almacenamiento seleccionados.

**③ El mínimo de 2 TB tiene fecha de caducidad.** ethereum.org señala que probablemente se «supere en 2027», lo que **explica por qué el crecimiento debe formar parte de tu plan de capacidad.**

::: warning Requiere verificación
Las cifras anteriores corresponden a un **nodo completo.** **Un nodo de archivo necesita mucho más almacenamiento, y el uso real varía según el cliente, la configuración de poda y el fork.**

En particular, PeerDAS de Fusaka cambió el manejo de blobs, así que consulta los requisitos actuales en las notas de la versión de tu cliente y **mide tú mismo la tasa de crecimiento en una prueba de concepto.**
:::

### Estrategia de instantáneas

Como se explica en [Fundamentos](./01-fundamentals.md), **los datos de la cadena se pueden volver a obtener de la red, pero hacerlo lleva tiempo.** Por tanto, el propósito de una copia de seguridad no es «conservar los datos», sino **«acortar el tiempo de recuperación».**

| Método | Características |
|---|---|
| **Instantáneas de EBS** | Volumen completo. Ten en cuenta la latencia de inicialización (carga diferida) al restaurar |
| **Exportación de instantáneas del cliente** | Exportación proporcionada por el cliente. Las garantías de consistencia están especificadas |
| **Resincronización** | Sin copia de seguridad, empezar de nuevo (con el coste de tiempo correspondiente) |

**Una advertencia**: crear una instantánea directamente del volumen de un nodo en ejecución puede capturar **la base de datos mientras se está escribiendo.** Para obtener una instantánea coherente, debes detener el cliente o usar un mecanismo de consistencia que proporcione el cliente.

## Comprobaciones de estado: por qué falla el enfoque habitual

Una comprobación de estado que ignora la sincronización puede enviar tráfico de la aplicación a un nodo desactualizado. Este es un riesgo de diseño que se debe probar, no una clasificación medida de errores operativos.

### El problema

Una comprobación de estado habitual pregunta: «¿responde el proceso?». En un nodo de blockchain, eso **no basta y es peligroso.**

Un nodo rezagado en la sincronización:

- Tiene abierto su puerto RPC y responde → la comprobación de actividad se supera
- Pero **responde según el estado desactualizado de la cadena** → devuelve datos incorrectos
- El Service le envía tráfico → la aplicación recibe balances y estados incorrectos

### La separación correcta

| Sonda | Qué debe comprobar |
|---|---|
| **startup** | La sincronización inicial está en curso; lleva mucho tiempo, así que debe tener un **`failureThreshold` generoso** |
| **liveness** | El proceso está activo y responde; **no compruebes aquí la sincronización** (matar un nodo rezagado puede impedir que se ponga al día) |
| **readiness** | Está **a N bloques de la cabeza de la cadena**, es decir, si puede prestar servicio |

**La separación entre liveness y readiness es decisiva.**

- Incluyes la sincronización en liveness → se reinicia un nodo rezagado → se queda aún más atrás → bucle infinito
- La excluyes de readiness → el nodo rezagado recibe tráfico y devuelve respuestas incorrectas

### Orientación para la implementación

El estado de sincronización se comprueba mediante el RPC del cliente. El método varía según el protocolo y el cliente, por lo que lo habitual es evaluarlo con un script de contenedor o un sidecar.

```yaml
# Conceptual form: the actual judgment logic differs per client
readinessProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-sync.sh"]   # block delta vs head
  periodSeconds: 15
  failureThreshold: 3

livenessProbe:
  httpGet: { path: /, port: rpc }     # responsiveness only
  periodSeconds: 30
  failureThreshold: 5

startupProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-alive.sh"]
  periodSeconds: 30
  failureThreshold: 240               # allow a long initial sync
```

**El umbral (N bloques) debe establecerse según los requisitos de la aplicación.** Decídelo junto con la profundidad de confirmación de [Fundamentos](./01-fundamentals.md).

## Exposición P2P: aceptar conexiones entrantes

### Por qué importan las conexiones entrantes

La sincronización funciona solo con conexiones salientes. Sin embargo, aceptar conexiones entrantes:

- Aumenta la cantidad de peers, lo que hace que la **propagación sea más rápida y estable**
- Contribuye a la red (es beneficioso para todas las partes en las cadenas públicas)

Es especialmente importante para los validadores: el retraso en la propagación de bloques afecta directamente al rendimiento (las recompensas).

### Métodos y contrapartidas

| Método | Características |
|---|---|
| **`hostNetwork: true`** | El método más sencillo. El Pod usa directamente la IP y los puertos del nodo. Restricción de **uno por nodo**; requiere una revisión de seguridad |
| **`hostPort`** | Asigna solo puertos específicos al nodo. Requiere gestionar los conflictos de puertos por nodo |
| **NodePort Service** | Opción estándar de Kubernetes. Restricciones del rango de puertos y problemas al anunciar la IP del nodo |
| **LoadBalancer por Pod (NLB)** | Dirección estable. **Coste de LB por Pod** |
| **Omitir conexiones entrantes** | Solo conexiones salientes. Configuración sencilla, pero menor calidad de peers |

### Un escollo habitual: la dirección anunciada

Los protocolos P2P **anuncian** su propia dirección a otros peers. Si la dirección visible dentro del contenedor (la IP del Pod) difiere de la dirección accesible desde el exterior (IP pública del nodo, dirección del LB), **los demás peers no pueden conectarse.**

La mayoría de los clientes ofrecen una opción para especificar la dirección anunciada (`--nat extip:<addr>` y otras similares). **Sin ella, abrir las conexiones entrantes no atraerá a ningún peer**. Esta es la causa clásica de «lo abrí y no pasó nada».

Como cada Pod debe anunciar una dirección distinta, necesitas una lógica de inicialización para que cada Pod descubra su propia dirección mediante el ordinal del StatefulSet o la downward API.

## Recursos: carga sostenida, no en ráfagas

Los nodos de blockchain **usan la CPU y las IOPS de forma constante.** Los bloques siguen llegando, la verificación continúa y el estado se actualiza continuamente.

| Aspecto | Recomendación |
|---|---|
| **Límite de CPU** | **Ten cuidado.** La limitación se convierte en retraso en el procesamiento de bloques, y el rendimiento de los validadores está vinculado a las recompensas. Consulta el diagnóstico de limitación en [Ajuste del kernel](../kernel/03-eks-node-tuning.md) |
| **Memoria** | Los clientes usan mucha memoria para las cachés de estado. **Establece límites generosos**, ya que un OOM puede dañar la base de datos |
| **request = limit** | La QoS garantizada reduce la prioridad de desalojo |
| **Nodos dedicados** | Sepáralos de otras cargas de trabajo mediante taints/tolerations para evitar vecinos ruidosos |
| **Descriptores de archivo** | Una conexión de socket por cada peer. Considera aumentar el límite ([Ajuste del kernel](../kernel/03-eks-node-tuning.md)) |

**La decisión sobre el límite de CPU es la más importante.** Como se explica en los [documentos sobre el kernel](../kernel/01-container-primitives.md), un límite de CPU limita el ancho de banda; por tanto, agotar la cuota dentro de un periodo obliga a detenerse. Si el procesamiento de bloques coincide con ese intervalo, aumenta la latencia y, en el caso de un validador, se pierde una oportunidad.

Los nodos dedicados reducen la contención entre inquilinos, pero kubelet, CNI/CSI, la observabilidad y los servicios del sistema operativo siguen compartiendo el nodo. Mantén las reservas y el margen disponible aunque omitas los límites de CPU de la aplicación; prueba la latencia, la sincronización y el estado del nodo bajo una carga sostenida.

## Nodos de Ethereum: estructura de dos clientes

Desde que Ethereum pasó a PoS, un nodo consta de **dos procesos.**

| Cliente | Función | Ejemplos |
|---|---|---|
| **Cliente de ejecución** (EL) | Ejecución de transacciones, gestión del estado y EVM | Geth, Nethermind, Besu, Erigon, Reth |
| **Cliente de consenso** (CL) | Consenso PoS, propuesta de bloques y certificación | Prysm, Lighthouse, Teku, Nimbus, Lodestar |

Se comunican mediante **Engine API** y comparten un secreto JWT.

### Decisión sobre la ubicación

| Enfoque | Ventajas y desventajas |
|---|---|
| **Dos contenedores en un Pod** | Comunicación sencilla mediante `localhost`; se programan y reinician juntos. Los recursos se solicitan conjuntamente |
| **StatefulSets separados** | Escalado y actualizaciones independientes. Requiere gestionar la conexión de Engine API |

**Un Pod es la opción predeterminada**: los dos clientes funcionan como un par 1:1 y la latencia de Engine API afecta al rendimiento, así que `localhost` dentro de un Pod es una opción natural.

También merece la pena hablar de la **diversidad de clientes**. Para que un error en un cliente no afecte a toda la red, la comunidad recomienda distribuir los clientes. Si ejecutas varios nodos, usar **combinaciones distintas de clientes** es una medida de defensa.

### Cambios recientes del protocolo con repercusiones operativas

Los siguientes son **eventos del protocolo con fecha**, no una garantía de una periodicidad futura. Consulta la [hoja de ruta](https://ethereum.org/roadmap/), los anuncios de activación y las notas de la versión de los clientes seleccionados antes de planificar una actualización.

| Fecha | Actualización | Importancia operativa |
|---|---|---|
| **7 de mayo de 2025** | **Pectra** en mainnet | EIP-7251 elevó a 2048 ETH el saldo efectivo máximo de los validadores que cumplen los requisitos; la consolidación modifica los registros de validadores, no necesariamente la cantidad de procesos o máquinas virtuales |
| **3 de diciembre de 2025** | **Fusaka** en mainnet (época 411392) | El aspecto destacado es **PeerDAS** (Peer Data Availability Sampling): verificar datos de blobs mediante muestreo, en lugar de hacerlo íntegramente. Aumenta el rendimiento de blobs |

La identidad o clave de un validador **no constituye un proceso ni una máquina virtual independientes**: un cliente de validador puede gestionar muchas claves en una pila de beacon node compartida. La consolidación de EIP-7251 puede reducir los registros de validadores y el trabajo de gestión de claves, pero no demuestra ahorros proporcionales en infraestructura ni en costes. Mide la topología real del cliente y conserva la protección contra slashing durante la migración de claves.

**PeerDAS afecta a la planificación del almacenamiento y del ancho de banda.** Un cambio en el manejo de blobs modifica la cantidad de datos que conserva y transfiere un nodo, así que conviene revisar las bases de dimensionamiento existentes.

## Hyperledger Fabric: operar una cadena permisionada

Fabric tiene características distintas. Al ser **una cadena de consorcio con participantes conocidos**, su consenso y sus características operativas son diferentes, como se explica en [Fundamentos](./01-fundamentals.md).

### Componentes

| Componente | Función | Ubicación en Kubernetes |
|---|---|---|
| **Peer** | Almacena el ledger, ejecuta chaincode y valida transacciones | StatefulSet + volumen persistente |
| **Orderer** | Ordena transacciones mediante el consenso configurado: CFT Raft o, en Fabric 3.x, SmartBFT | StatefulSet + almacenamiento persistente; la validación de los peers determina las actualizaciones válidas del estado |
| **CA** (Fabric CA) | Emite certificados de miembros | Deployment + volumen persistente |
| **Chaincode** | Contratos inteligentes | Generador externo o Pods separados |

### Aspectos operativos

**① El volumen persistente del orderer es imprescindible.** Perder el registro de Raft interrumpe el estado del consenso. Los Pods se reinician durante las actualizaciones, así que **operar sin un volumen persistente implica perder datos.**

**② La gestión de certificados es la tarea principal.** Fabric gestiona las organizaciones y las identidades mediante MSP (Membership Service Provider), y todas las comunicaciones usan TLS. Debes gestionar:

- Certificados y claves de firma de MSP
- Certificados TLS (para cada peer, orderer y CA)
- **Gestión de caducidad**: la caducidad de los certificados provoca interrupciones reales

La caducidad de los certificados es un riesgo importante de interrupción, pero aquí no se proporciona un conjunto de datos sobre su frecuencia. Supervisa y ensaya la renovación de las credenciales de MSP y TLS, y valida la compatibilidad de las versiones del operador y del cliente.

**③ Usa un operador.** Fabric cuenta con un ecosistema de operadores de Kubernetes.

| Operador | Características |
|---|---|
| [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) | Sigue el patrón de operadores de CNCF. CA, Peer, Orderer y Console se declaran como CR |
| [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric) | Del proyecto Hyperledger Bevel. Compatible con Fabric 2.3–3.x |

Un operador convierte la configuración repetitiva en la aplicación de recursos declarativos. **Se recomienda empezar con un operador en lugar de ensamblar YAML a mano**, porque la complejidad de la configuración de Fabric hace que la gestión manual sea propensa a errores.

### Ethereum frente a Fabric

| Aspecto | Nodo de Ethereum | Hyperledger Fabric |
|---|---|---|
| **Participación** | Sin permisos | Permisionada (MSP) |
| **Consenso** | PoS | Modo de orderer configurado: Raft (CFT) o SmartBFT (Fabric 3.x) |
| **Finalidad** | Basada en checkpoints, según los supuestos del protocolo | El ordenamiento es final según los supuestos del consenso; los peers siguen validando las transacciones, y una transacción ordenada puede no ser válida |
| **Principal carga operativa** | Sincronización, crecimiento del disco y hard forks | **Caducidad de certificados**, gestión de canales y políticas |
| **Exposición P2P** | Se recomiendan las conexiones entrantes | Conexiones entre organizaciones (puntos de conexión conocidos) |
| **Crecimiento del almacenamiento** | Elevado y monótono | Relativamente bajo (depende del volumen de transacciones) |
| **Actualizaciones** | Calendario externo (hard forks) | Decididas por consenso del consorcio |

**La mayor diferencia operativa**: Ethereum debe cumplir **un calendario establecido externamente** (hard forks), mientras que en Fabric **el consorcio fija el calendario.** A cambio, Fabric requiere un proceso de acuerdo entre los miembros.

## Gestión de los calendarios de hard forks

En [Fundamentos](./01-fundamentals.md), se describió un hard fork como «una migración con fecha límite». Este es un procedimiento práctico:

| Paso | Contenido |
|---|---|
| **1. Suscribirse** | Blog oficial del protocolo, notas de la versión de los clientes y comunidades de operadores |
| **2. Registrar la fecha** | Añade el bloque o la hora del fork al calendario del equipo. **Fija una fecha objetivo con margen** |
| **3. Validar en una red de prueba** | Los forks de las redes de prueba se producen antes que los de mainnet; valida allí |
| **4. Preparar las imágenes** | Compila y analiza las imágenes con una versión compatible con el fork |
| **5. Actualizar de forma secuencial** | **Termina antes** del punto de activación del fork. Si tienes varios nodos, actualiza uno a la vez |
| **6. Supervisar durante el fork** | Altura de la cadena, cantidad de peers y si se reconoció el fork |
| **7. Verificar después** | Que todos los nodos estén en la misma cadena |

Un nodo que ejecute un cliente incompatible puede dejar de seguir la cadena canónica o divergir tras la activación. Compara **la misma altura de bloque y el estado de finalidad** entre fuentes independientes de confianza, teniendo en cuenta los retrasos normales de propagación y sincronización; no compares cabezas más recientes que no estén relacionadas como si tuvieran que coincidir al instante.

## Supervisión

| Categoría | Métrica | Motivo |
|---|---|---|
| **Sincronización** | Diferencia de bloques respecto a la cabeza de la cadena | Indicador fundamental de si puede prestar servicio |
| **Sincronización** | Latencia de procesamiento de bloques | Señal temprana de que empieza a quedarse atrás |
| **P2P** | Cantidad de peers | Una caída brusca indica un problema de red o de configuración |
| **P2P** | Proporción de conexiones entrantes y salientes | Si no hay conexiones entrantes, la configuración de exposición ha fallado |
| **Almacenamiento** | Uso del disco y tasa de crecimiento | Permite predecir cuándo ampliar |
| **Almacenamiento** | IOPS, profundidad de cola y latencia | Permite confirmar el cuello de botella |
| **Consenso** | Reorganizaciones (reorgs) | Deben comunicarse a la aplicación |
| **Validador** | Tasa de participación y tareas omitidas | Vinculadas directamente a las recompensas |
| **Fabric** | **Tiempo restante hasta la caducidad del certificado** | Prevención de interrupciones |
| **Recursos** | Limitación de CPU (`nr_throttled`) | [Documentos sobre el kernel](../kernel/01-container-primitives.md) |

**La «diferencia de bloques respecto a la cabeza de la cadena» es la métrica más importante.** Cuando empieza a aumentar, debes encontrar la causa (IOPS, CPU, peers o red); al superar un umbral, el nodo debe dejar de estar listo.

## Resumen

- **Primero decide si ejecutar esto en EKS.** El criterio es si hay otras cargas de trabajo alrededor del nodo. Un nodo aislado es más sencillo en EC2.
- **StatefulSet + Service headless + volumen persistente** es la estructura básica, y `terminationGracePeriodSeconds` debe ser generoso (un cierre forzado puede dañar la base de datos).
- En el almacenamiento, **las IOPS se convierten en un cuello de botella antes que la capacidad.** La ventaja clave de gp3 es que permite ajustar por separado la capacidad y las IOPS, y es obligatorio contar con un plan para ampliar el volumen.
- Separa la actividad del proceso de la preparación para prestar servicio según la sincronización, y prueba ambas; este capítulo no proporciona una clasificación por frecuencia de interrupciones.
- Al abrir conexiones P2P entrantes, **si olvidas la dirección anunciada, no llegarán peers.**
- El uso de recursos es sostenido, no en ráfagas. **Dedica nodos y decide con cuidado los límites de CPU.**
- Ethereum usa clientes EL y CL; las identidades y claves de validadores son independientes de la cantidad de procesos y máquinas virtuales. La consolidación no demuestra por sí sola que se ahorren costes.
- La principal carga operativa de Fabric es **la caducidad de los certificados.** Empieza con un operador y automatiza la renovación.
- Después de un hard fork, **compara los hashes de bloque con los de otros nodos y exploradores** para confirmar que estás en la misma cadena.

Siguiente: [Amazon Managed Blockchain](./03-managed-blockchain.md) analiza cuánto de esta carga pueden asumir los servicios gestionados.

## Referencias

- [Ethereum: ejecutar un nodo](https://ethereum.org/developers/docs/nodes-and-clients/run-a-node/)
- [EIP-7870: recomendaciones de hardware y ancho de banda](https://eips.ethereum.org/EIPS/eip-7870): recomendaciones oficiales de hardware
- [Hoja de ruta de Ethereum](https://ethereum.org/roadmap/) / [Pectra](https://ethereum.org/roadmap/pectra/) / [Fusaka](https://ethereum.org/roadmap/fusaka/)
- [Anuncio de Pectra en mainnet (Ethereum Foundation)](https://blog.ethereum.org/2025/04/23/pectra-mainnet)
- [Anuncio de Fusaka en mainnet (Ethereum Foundation)](https://blog.ethereum.org/2025/11/06/fusaka-mainnet-announcement)
- [Hyperledger Fabric: implementar una red de producción](https://hyperledger-fabric.readthedocs.io/en/latest/deployment_guide_overview.html)
- [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) / [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric)
- [Prueba comparativa de EBS gp2 frente a gp3](../storage/01-ebs-gp2-gp3-benchmark.md) / [Ajuste del kernel de los nodos de EKS](../kernel/03-eks-node-tuning.md)
