# Fundamentos de blockchain

> **Última actualización**: 19 de octubre de 2026

## Qué abarca este documento

- Por qué algunos libros mayores replican la validación y en qué se diferencian los modelos de nodo completo, cliente ligero y con permisos
- El papel del consenso, los árboles de Merkle, P2P y la finalidad, y la restricción que cada uno impone a las operaciones de infraestructura
- Por qué un nodo de blockchain debe tratarse de forma distinta a un servicio con estado convencional

## Planteamiento del problema: llegar a un acuerdo sin un árbitro de confianza

El punto de partida para entender blockchain no es la tecnología, sino **las restricciones**.

Pensemos en un sistema distribuido convencional, como un clúster etcd de Kubernetes. etcd también llega a un consenso entre nodos, pero parte de una premisa: **los nodos participantes son gestionados por la misma organización y pueden fallar, pero no mentir**. Maneja la muerte de nodos y las particiones de red (fallos por caída), pero no el caso de que un nodo afirme deliberadamente un valor diferente.

La premisa de blockchain es otra.

| Elemento | etcd (Raft) | Blockchain |
|---|---|---|
| **Participantes** | Misma organización, miembros conocidos | Partes que no se conocen entre sí, con membresía cambiante |
| **Fallos asumidos** | Fallos por caída (muerte, partición) | **Fallos bizantinos** (mentiras, colusión, ataques) |
| **Elegibilidad** | Designada por el operador | **Cualquiera**, en las cadenas públicas |
| **¿Se puede revertir?** | Un operador puede intervenir | Solo lo que permita el protocolo |

Muchos **nodos completos** de cadenas públicas verifican de forma independiente las transacciones y las reglas de consenso. Los clientes ligeros, los nodos podados o sincronizados mediante instantáneas y los diseños con permisos tienen modelos de verificación y distribución de datos diferentes. La membresía con permisos no convierte por sí sola un algoritmo de consenso en tolerante a fallos bizantinos.

De esto se desprende la propiedad fundamental de blockchain.

> **Blockchain no es un sistema diseñado para ofrecer rendimiento.** Es un sistema que **acepta deliberadamente la redundancia** a cambio de verificabilidad y resistencia a la manipulación.

Si se entiende esto, todas las características operativas que se describen a continuación se desprenden naturalmente.

## Bloques y cadenas: por qué una «cadena»

Un grupo de transacciones forma un **bloque**, y cada bloque contiene **el hash del bloque inmediatamente anterior**.

```text
Block N-1               Block N                 Block N+1
┌──────────────┐       ┌──────────────┐        ┌──────────────┐
│ prev_hash:.. │       │ prev_hash: ──┼────────│ prev_hash: ──┤
│ merkle_root  │   ┌───│ merkle_root  │        │ merkle_root  │
│ transactions │───┘   │ transactions │        │ transactions │
└──────────────┘       └──────────────┘        └──────────────┘
      hash ────────────────┘
```

La propiedad que esto proporciona es la **propagación de la manipulación**. Cambiar una transacción del bloque N → cambia el hash del bloque N → el `prev_hash` del bloque N+1 deja de coincidir → todo lo que viene después deja de ser válido.

En una cadena PoW, reescribir la historia requiere reconstruir suficiente trabajo aceptado; otras cadenas usan supuestos diferentes de finalidad y gobernanza. Los enlaces entre hashes permiten detectar la manipulación, pero por sí solos no establecen la finalidad ni hacen que todas las cadenas de bloques sean inmutables desde el punto de vista económico.

### Árboles de Merkle: por qué hacen falta

La pregunta es cómo resumir las transacciones de un bloque. Podrías concatenarlas todas y calcular su hash, pero entonces **comprobar «si esta transacción está en este bloque» requeriría el bloque entero**.

Un árbol de Merkle es un árbol binario que calcula hashes de las transacciones por pares, de abajo hacia arriba.

```text
                merkle_root
               /            \
         H(AB)                H(CD)
        /     \              /     \
     H(A)    H(B)         H(C)    H(D)
      |        |            |        |
     tx A     tx B         tx C     tx D
```

La propiedad que se desprende de esto es la **prueba de Merkle**. Para demostrar que la transacción C está en este bloque, solo necesitas **`H(D)` y `H(AB)`**, no el bloque entero. El receptor calcula `H(C)` → `H(CD)` → `merkle_root` y los compara.

El tamaño de la prueba crece como **log N**, donde N es la cantidad de transacciones. Incluso en un bloque con un millón de transacciones, la prueba tiene unos 20 hashes.

**Importancia práctica**: esto es lo que hace posibles los clientes ligeros. Puedes verificar la inclusión de una transacción concreta sin conservar toda la cadena. Es la base para decidir «¿ejecutar un nodo completo o basta con una verificación ligera?» al integrar blockchain con sistemas existentes.

## Consenso: quién escribe el siguiente bloque

Un algoritmo de consenso decide dos cosas: **quién propone un bloque** y **qué lado se considera canónico en caso de conflicto**.

### Enfoques principales

| Enfoque | Selección del proponente | Cuál es el costo real | Ejemplos |
|---|---|---|---|
| **PoW** (prueba de trabajo) | El nodo que resuelve primero un acertijo computacional | **Electricidad y hardware** | Bitcoin |
| **PoS** (prueba de participación) | Se selecciona con una probabilidad proporcional a la participación | **Capital en staking + penalización por infracción** | Ethereum |
| **Familia BFT** | Votación dentro de un umbral definido de tolerancia a fallos bizantinos | Supuestos sobre la membresía, los validadores y el quórum | Tendermint; Fabric 3.x SmartBFT |
| **Ordenamiento con CFT y permisos** | Réplicas conocidas usan un consenso tolerante a fallos por caída | No tolera comportamientos arbitrarios de ordenamiento bizantino | Fabric Raft |

### Por qué hace falta un costo

Esta pregunta es clave para entender el consenso. **Si proponer un bloque no costara nada, se podrían crear candidatos ilimitados y paralizar la red.** En un entorno que permite la participación anónima, la identidad por sí sola no puede impedirlo (un ataque Sybil: una parte crea muchas identidades).

PoW establece el costo en **cómputo**; PoS, en **capital más riesgo de penalización**. La familia BFT **restringe de entrada a los participantes**, evitando el problema; por eso es adecuada para las cadenas de consorcios.

### Aquí es donde se separan los modelos públicos y privados

| Tipo | Participación | Consenso | Rendimiento | Uso principal |
|---|---|---|---|---|
| **Pública** (sin permisos) | Cualquiera | PoW/PoS | Bajo | Activos públicos, interoperabilidad |
| **Privada/de consorcio** (con permisos) | Miembros aprobados | BFT/Raft | Relativamente alto | Libros mayores entre empresas, entornos regulados |

Los diseños con permisos pueden usar una membresía conocida y una gobernanza explícita, y elegir CFT o BFT según el modelo de amenazas real. Las aplicaciones financieras pueden usar redes con permisos o públicas y controles diferentes; ni la membresía ni la etiqueta de consenso garantizan el cumplimiento normativo.

## Finalidad: el concepto más importante desde el punto de vista operativo

**La finalidad describe la liquidación conforme a los supuestos de seguridad de un protocolo.** No es una garantía incondicional frente a todos los ataques, intervenciones de gobernanza o transacciones compensatorias a nivel de aplicación. Hay que distinguir entre la confianza probabilística, la finalidad económica y las garantías deterministas del consenso.

### Finalidad probabilística frente a finalidad absoluta

| Tipo | Significado | Ejemplo |
|---|---|---|
| **Probabilística** | Cuantos más bloques se acumulan, más disminuye exponencialmente la probabilidad de reversión. **Nunca llega exactamente a cero** | PoW de Bitcoin |
| **Económica** | Los puntos de control finalizados están protegidos bajo los supuestos de participación y penalización; su reversión no es físicamente imposible | PoS de Ethereum |
| **Inmediata** | La liquidación se produce al finalizar una ronda de consenso | Familia BFT |

### Por qué esto es un problema operativo

**Es posible que los datos que devuelve un nodo aún no estén finalizados.**

Si le preguntas a un nodo de blockchain «dime el resultado de esta transacción», responde **según la última cadena que conoce**. Si ese bloque más reciente se reorganiza después (una reorganización o *reorg*), la respuesta cambia.

Los patrones de incidentes que esto genera son:

| Patrón | Resultado |
|---|---|
| Confirmar un depósito con el último bloque y actuar en consecuencia | Una reorganización borra el depósito después de que ya se haya efectuado el retiro |
| Una comprobación de estado que solo confirma que «el nodo está activo» | Un nodo que va retrasado en la sincronización **devuelve datos obsoletos** |
| Un balanceador de carga distribuye las solicitudes entre varios nodos | Las alturas de la cadena difieren entre nodos → **respuestas distintas a la misma pregunta** |

**Por lo tanto, el diseño de la aplicación debe incluir una regla del tipo «procesar tras N confirmaciones» (profundidad de confirmación), y ese valor depende de las características de finalidad de la cadena.** Esto no se puede resolver únicamente con la infraestructura; es un acuerdo con la aplicación.

Lo que puede hacer la infraestructura:

- **Incluir el estado de sincronización en la comprobación de estado**: definir la preparación para atender solicitudes (readiness) como «estar a N bloques de la cabeza de la cadena», no como «estar activo»
- **Supervisar la divergencia en la altura de la cadena entre nodos**: retirarlos del balanceo de carga cuando la divergencia aumente
- **Exponer las reorganizaciones como una métrica**, para que la aplicación pueda responder

## Redes P2P: por qué difieren de los servicios convencionales

Los nodos de blockchain se comunican **entre pares, en lugar de mediante un modelo cliente-servidor**. Esto genera fricción con el modelo de redes de Kubernetes.

### Protocolos de difusión

Cuando aparece un bloque o una transacción nuevos, se **propagan a los pares vecinos**, que a su vez los propagan a sus propios pares. Así es como todos llegan a conocerlos.

Características:

- No hay un intermediario central → no existe un único punto de fallo
- **Los mismos datos llegan de forma redundante por varias rutas** → se desperdicia ancho de banda en duplicados
- La propagación lleva tiempo → la noción de «lo más reciente» varía entre nodos (lo que nos devuelve al problema de la finalidad descrito antes)

### Fricción en un entorno de Kubernetes

| Lo que necesita P2P de blockchain | Valor predeterminado de Kubernetes |
|---|---|
| **Identidad estable de los pares** (ID del nodo, dirección) | Las IP de los Pod cambian al reiniciarse |
| **Aceptar conexiones entrantes** (otros pares se conectan conmigo) | De forma predeterminada, no se puede acceder directamente a los Pod desde el exterior |
| **Persistencia de la lista de pares** | El estado se pierde al reemplazar un Pod |
| **Anunciar un puerto fijo** | Asignación de puertos del Service |

Por eso, los nodos de blockchain suelen usar **StatefulSet + Service sin cabecera**, ya que necesitan nombres y orden estables. Aceptar conexiones P2P entrantes requiere un diseño de exposición adicional. [Ejecución de nodos de blockchain en EKS](./02-nodes-on-eks.md) explica los detalles.

## Estado y almacenamiento: por qué cuesta reconstruirlos

Un nodo de blockchain conserva dos cosas.

| Datos | Naturaleza | Tamaño |
|---|---|---|
| **Historial de bloques** | Registro de solo anexado. El pasado es inmutable | Crece continuamente |
| **Estado actual** | Saldos, almacenamiento de contratos. Se puede derivar reproduciendo los bloques | Crece, pero ocupa menos que el historial |

**La propiedad clave: el estado se puede reproducir a partir del historial, pero esa reproducción lleva mucho tiempo.**

Reproducir y verificar cada bloque desde el génesis (sincronización completa) lleva un tiempo proporcional a la antigüedad de la cadena. Por eso existen métodos de sincronización alternativos.

| Método | Qué hace | Compensación |
|---|---|---|
| **sincronización completa** | Verifica y reproduce todo desde el génesis | Mayor confianza, **la más lenta** |
| **sincronización snap/rápida** | Obtiene el estado con pruebas verificadas respecto de una raíz de estado aceptada; las comprobaciones del historial dependen del cliente y del modo | Más rápida, con supuestos explícitos de confianza en el consenso, los puntos de control y la implementación; no implica confiar ciegamente en un par arbitrario |
| **sincronización desde un punto de control** | Parte de un punto de control de confianza | La más rápida, pero confía en la fuente del punto de control |
| **Restauración de una instantánea** | Restaura un directorio de datos conservado por el operador | Rápida, pero requiere gestionar la actualidad y coherencia de la instantánea |

**Conclusión operativa**: no se debe perder el estado al reemplazar un Pod. Perderlo implica una sincronización larga durante la cual ese nodo no puede atender solicitudes. Por eso, un volumen persistente **no es opcional, sino obligatorio** para un nodo de blockchain.

### Actualización de octubre de 2026: instantáneas de blockchain en AWS

Según el [anuncio del 14 de octubre de 2026](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/), AWS lanzó **Blockchain Snapshots on AWS**, que publica datos de cadenas de bloques públicas presincronizados para nodos. Las instantáneas abarcan Ethereum y Solana, están disponibles sin costo y se actualizan con la misma frecuencia que el proveedor de origen. Es una opción para reducir el tiempo de inicialización: añadir capacidad a una flota de RPC, recuperar un nodo fallido o volver a sincronizar una base de datos dañada. Para ello, vuelve a publicar la instantánea de cada red en un formato optimizado para la extracción paralela. Está disponible en EE. UU. Este (Norte de Virginia), Europa (Irlanda) y Asia-Pacífico (Tokio), y el acceso requiere una instancia EC2 en la misma región con un punto de conexión de VPC de puerta de enlace de S3. Esto corresponde a «Restauración de una instantánea» en la tabla anterior, por lo que se aplican los mismos supuestos de confianza sobre la procedencia y la actualidad de la instantánea.

### Nodos de archivo: una consideración aparte

Un nodo que puede consultar «el estado en cualquier momento pasado» es un nodo de archivo. Conserva todos los estados intermedios, por lo que necesita **mucho más almacenamiento** que un nodo normal.

**Aquí hace falta tomar una decisión de diseño**: primero, confirma que realmente necesitas la capacidad de archivo. La mayoría de las aplicaciones solo necesitan el estado reciente y, si se requieren consultas históricas, es más rentable gestionarlas mediante un servicio de indexación o un almacén de datos.

## Gestión de claves: perderla significa el fin

En blockchain, **la identidad y la autoridad son la clave privada**. Esto crea una diferencia decisiva con respecto a los sistemas existentes.

| Sistemas existentes | Blockchain |
|---|---|
| Si olvidas una contraseña, la restableces | **Si pierdes la clave, los activos o la autoridad desaparecen para siempre** |
| Un administrador puede congelar una cuenta comprometida | No existe ninguna parte que pueda revertirlo (salvo que el protocolo lo permita) |
| Los registros de auditoría permiten rastrear los hechos a posteriori | Una transacción firmada, una vez finalizada, no se puede revertir |

**Por eso, la estrategia de copia de seguridad es distinta por naturaleza.** Los datos de la cadena se pueden volver a descargar de la red, así que hacer copias de seguridad de ellos aporta poco valor. En cambio, las claves **deben tener copias de seguridad**, y **la propia copia de seguridad supone un riesgo de exposición**.

Por eso son importantes los HSM y AWS KMS/CloudHSM en la infraestructura de blockchain. En particular, los validadores tienen el requisito contradictorio de que **la clave debe estar en línea para firmar, pero no debe filtrarse**. [Perspectiva de los servicios financieros](./04-financial-services.md) aborda este problema.

## Características operativas: qué se desprende de todo esto

Estas son las características operativas que generan los conceptos anteriores:

| Diseño de blockchain | Característica operativa resultante | Implicación en Kubernetes |
|---|---|---|
| Validación replicada de nodos completos | Añadir réplicas no aumenta por sí solo la capacidad de escritura de la cadena base | Puede aumentar la capacidad agregada de RPC/lectura y la disponibilidad |
| El estado se acumula localmente | **Reemplazar un Pod es muy costoso** | StatefulSet + volumen persistente obligatorios; conviene considerar la afinidad de nodos |
| La sincronización de la cadena se retrasa | **«Activo» y «capaz de atender solicitudes» no son lo mismo** | Incluir el estado de sincronización en la comprobación de preparación para atender solicitudes (readiness) |
| La finalidad no es inmediata | **Los datos más recientes no son datos finalizados** | La profundidad de confirmación debe formar parte del acuerdo con la aplicación |
| Difusión P2P | **Necesita conexiones entrantes e identidad estable** | Service sin cabecera y diseño de exposición adicional |
| Las bifurcaciones duras activan reglas en un momento definido | Actualizar los binarios compatibles antes de la activación | Los despliegues canarios y progresivos pueden preparar la flota con antelación |
| Las claves representan la autoridad | **Perder la clave = pérdida permanente** | KMS/HSM y estrategias de copia de seguridad separadas para claves y datos |
| La verificación redundante es el objetivo | **Consumo constante de CPU e IOPS** | No se adapta bien a la configuración de recursos orientada a picos |

**Esta tabla es el núcleo de esta sección.** Todas las recomendaciones concretas del documento 2 se derivan de ella.

## Bifurcaciones duras: el mayor choque con el modelo operativo de Kubernetes

Un cambio de protocolo que no es compatible con versiones anteriores es una **bifurcación dura**. Toda la red cambia a las nuevas reglas al llegar a una altura de bloque o un momento determinados, y **los nodos que no cambien permanecerán en una cadena diferente**.

Dónde choca con las prácticas habituales de Kubernetes:

| Convención de Kubernetes | En una bifurcación dura |
|---|---|
| Transición gradual mediante una actualización progresiva | Es válida antes de la activación, siempre que todos los nodos necesarios admitan las nuevas reglas antes de la fecha límite |
| Probar primero un subconjunto como canario | Probar los binarios compatibles con la bifurcación antes de la activación; comparar el comportamiento en la fase apropiada de la testnet/mainnet |
| Revertir si hay problemas | Revertir deja ese nodo en la cadena antigua |
| El equipo de operaciones fija el calendario de las actualizaciones | **El calendario se fija externamente** |

**Recomendación práctica**: trata una bifurcación dura no como un despliegue, sino como **una migración con fecha límite**. Suscríbete a las notas de las versiones de los clientes, actualiza con suficiente antelación a la fecha de la bifurcación y valida primero en una testnet.

Ethereum implementó Pectra y Fusaka en 2025 y ha avanzado hacia actualizaciones más frecuentes. **Usa las fechas de activación publicadas y las notas de las versiones de los clientes, no un calendario garantizado de dos actualizaciones al año**, para planificar el mantenimiento.

## Resumen

- Compara el consenso elegido y el modelo de confianza: **etcd/Raft tolera fallos por caída**, algunas cadenas de bloques usan BFT y Fabric con permisos puede usar CFT Raft o SmartBFT. La etiqueta «blockchain» por sí sola no implica tolerancia a fallos bizantinos.
- Muchos diseños de nodo completo replican la verificación; los modelos de cliente ligero y con permisos son diferentes, y la capacidad de RPC/lectura puede escalar por separado de las escrituras en la cadena base.
- La cadena de `prev_hash` propaga la manipulación, y los **árboles de Merkle** permiten pruebas de inclusión cuyo tamaño es logarítmico respecto del número de transacciones (la base de los clientes ligeros).
- El consenso necesita un costo para **defenderse de los ataques Sybil**. Restringir a los participantes (consorcio) elimina esa necesidad, lo que permite usar BFT con mayor rendimiento y finalidad a costa de la descentralización.
- **La finalidad es el concepto más importante desde el punto de vista operativo.** Los datos más recientes no son datos finalizados, así que incluye el estado de sincronización en la comprobación de preparación para atender solicitudes (readiness) y establece la profundidad de confirmación como parte del acuerdo con la aplicación.
- El estado se puede reproducir, pero **la reproducción lleva mucho tiempo**, por lo que los volúmenes persistentes son obligatorios.
- Una bifurcación dura tiene un punto de activación coordinado externamente; prepara por adelantado clientes compatibles y evalúa por separado la reversión posterior a la activación.

Siguiente: [Ejecución de nodos de blockchain en EKS](./02-nodes-on-eks.md) convierte estas características en una configuración real.

## Referencias

- [Documentación para desarrolladores de Ethereum](https://ethereum.org/developers/docs/): consenso, nodos y clientes
- [Ethereum: prueba de participación](https://ethereum.org/developers/docs/consensus-mechanisms/pos/)
- [Documentación de Hyperledger Fabric](https://hyperledger-fabric.readthedocs.io/): estructura de una cadena con permisos
- [Guía para desarrolladores de Bitcoin](https://developer.bitcoin.org/devguide/): PoW y árboles de Merkle
- [Arquitectura del clúster: etcd y Raft](../core/01-cluster-architecture.md): comparación con el consenso tolerante a fallos por caída


- [Servicio de ordenamiento de Fabric](https://hyperledger-fabric.readthedocs.io/en/latest/orderer/ordering_service.html): CFT Raft frente a SmartBFT
