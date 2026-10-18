# Fundamentos de blockchain

> **Última actualización**: September 12, 2026

## Qué abarca este documento

- Por qué algunos libros contables replican la validación y en qué se diferencian los modelos de nodo completo, cliente ligero y con permisos
- El papel del consenso, los árboles de Merkle, P2P y la finalidad, y la restricción que cada uno impone a las operaciones de infraestructura
- Por qué un nodo de blockchain debe tratarse de forma distinta a un servicio con estado ordinario

## Planteamiento del problema: llegar a un acuerdo sin un árbitro de confianza

El punto de partida para entender blockchain no es la tecnología, sino **las restricciones.**

Pensemos en un sistema distribuido ordinario, por ejemplo, un clúster de etcd de Kubernetes. etcd también llega a un consenso entre nodos, pero bajo una premisa: **los nodos participantes están gestionados por la misma organización y fallan, pero no mienten.** Gestiona nodos que dejan de funcionar y particiones de red (fallos de tipo crash), pero no que un nodo afirme deliberadamente un valor distinto.

La premisa de blockchain es diferente.

| Elemento | etcd (Raft) | Blockchain |
|---|---|---|
| **Participantes** | Una misma organización, miembros conocidos | Partes que no se conocen entre sí, con membresía cambiante |
| **Fallos previstos** | Fallos de tipo crash (caída, partición) | **Fallos bizantinos** (mentiras, colusión, ataques) |
| **Elegibilidad** | Designada por el operador | **Cualquiera**, en las cadenas públicas |
| **¿Se puede revertir?** | Un operador puede intervenir | Solo lo que permita el protocolo |

En muchas cadenas públicas, los **nodos completos** verifican de forma independiente las transacciones y las reglas de consenso. Los clientes ligeros, los nodos podados o sincronizados a partir de instantáneas, y los diseños con permisos tienen distintos modelos de verificación y distribución de datos. La membresía con permisos no hace que un algoritmo de consenso sea tolerante a fallos bizantinos por sí sola.

De ahí se desprende la propiedad fundamental de blockchain.

> **Blockchain no es un sistema diseñado para el rendimiento.** Es un sistema que **acepta deliberadamente la redundancia** a cambio de verificabilidad y resistencia a la manipulación.

Entiéndelo y todas las características operativas que se describen a continuación se desprenden de forma natural.

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

La propiedad que esto proporciona es la **propagación de la manipulación.** Cambiar una transacción del bloque N → cambia el hash del bloque N → el `prev_hash` del bloque N+1 deja de coincidir → todo lo que viene después deja de ser válido.

En una cadena PoW, reescribir el historial requiere reconstruir suficiente trabajo aceptado; otras cadenas usan distintos supuestos de finalidad y gobernanza. Los enlaces de hash hacen que la manipulación sea detectable, pero por sí solos no establecen la finalidad ni hacen que toda blockchain sea inmutable desde el punto de vista económico.

### Árboles de Merkle: por qué hacen falta

La pregunta es cómo resumir las transacciones de un bloque. Se podrían concatenar y calcular el hash de todas, pero entonces **comprobar «si esta transacción está en este bloque» requiere el bloque completo.**

Un árbol de Merkle es un árbol binario que calcula los hashes de las transacciones por pares, de abajo hacia arriba.

```text
                merkle_root
               /            \
         H(AB)                H(CD)
        /     \              /     \
     H(A)    H(B)         H(C)    H(D)
      |        |            |        |
     tx A     tx B         tx C     tx D
```

De ahí se desprende la propiedad de la **prueba de Merkle.** Para demostrar que la transacción C está en este bloque solo necesitas **`H(D)` y `H(AB)`**, no el bloque completo. El receptor calcula `H(C)` → `H(CD)` → `merkle_root` y compara.

El tamaño de la prueba crece como **log N** respecto al número de transacciones N. Incluso en un bloque con un millón de transacciones, la prueba consta de unos 20 hashes.

**Importancia práctica**: esto es lo que hace posibles los clientes ligeros. Puedes verificar la inclusión de una transacción concreta sin conservar la cadena completa. Esta es la base para decidir «¿ejecutar un nodo completo o basta con la verificación ligera?» al integrar blockchain con sistemas existentes.

## Consenso: quién escribe el siguiente bloque

Un algoritmo de consenso decide dos cosas: **quién propone un bloque** y **qué lado es canónico en caso de conflicto**.

### Principales enfoques

| Enfoque | Selección del proponente | Cuál es el costo real | Ejemplos |
|---|---|---|---|
| **PoW** (prueba de trabajo) | El nodo que primero resuelve un rompecabezas computacional | **Electricidad y hardware** | Bitcoin |
| **PoS** (prueba de participación) | Selección con una probabilidad proporcional a la participación | **Capital en staking + penalización por incumplimiento** | Ethereum |
| **Familia BFT** | Votos según un umbral definido de fallos bizantinos | Supuestos sobre membresía/validadores y cuórum | Tendermint; Fabric 3.x SmartBFT |
| **Ordenamiento CFT con permisos** | Réplicas conocidas usan consenso tolerante a fallos de tipo crash | No tolera comportamientos arbitrarios de ordenamiento bizantino | Fabric Raft |

### Por qué se necesita un costo

Esta pregunta es clave para entender el consenso. **Si proponer un bloque no cuesta nada, se pueden crear candidatos ilimitados y paralizar la red.** En un entorno que permite la participación anónima, la identidad por sí sola no puede impedirlo (un ataque Sybil: una parte crea muchas identidades).

PoW impone el costo de **computación**; PoS, el de **capital más el riesgo de penalización**. La familia BFT **restringe de entrada quiénes pueden participar**, eludiendo el problema, por lo que es adecuada para cadenas de consorcio.

### Aquí es donde se separan las redes públicas y privadas

| Tipo | Participación | Consenso | Rendimiento | Uso principal |
|---|---|---|---|---|
| **Pública** (sin permisos) | Cualquiera | PoW/PoS | Bajo | Activos públicos, interoperabilidad |
| **Privada/de consorcio** (con permisos) | Miembros aprobados | BFT/Raft | Relativamente alto | Libros contables entre empresas, entornos regulados |

Los diseños con permisos pueden usar una membresía conocida y una gobernanza explícita, y elegir CFT o BFT según el modelo de amenazas real. Las aplicaciones financieras pueden usar redes con permisos o públicas y distintos controles; ni la membresía ni la denominación del consenso demuestran el cumplimiento normativo.

## Finalidad: el concepto más importante desde el punto de vista operativo

**La finalidad describe la liquidación conforme a los supuestos de seguridad de un protocolo.** No es una garantía incondicional frente a cualquier ataque, intervención de gobernanza o transacción compensatoria a nivel de aplicación. Distingue entre confianza probabilística, finalidad económica y garantías deterministas de consenso.

### Finalidad probabilística frente a finalidad absoluta

| Tipo | Significado | Ejemplo |
|---|---|---|
| **Probabilística** | Cuantos más bloques se acumulan, más disminuye exponencialmente la probabilidad de reversión. **Nunca llega exactamente a cero** | PoW de Bitcoin |
| **Económica** | Los puntos de control finalizados están protegidos bajo supuestos de participación y penalización; revertirlos no es físicamente imposible | PoS de Ethereum |
| **Inmediata** | La liquidación ocurre al final de una ronda de consenso | Familia BFT |

### Por qué esto es un problema operativo

**Es posible que los datos que devuelve un nodo aún no sean definitivos.**

Si le preguntas a un nodo de blockchain «dime el resultado de esta transacción», responde **en función de la última cadena que conoce.** Si ese último bloque se reorganiza más adelante (una reorganización), la respuesta cambia.

Los patrones reales de incidentes que esto provoca:

| Patrón | Resultado |
|---|---|
| Confirmar un depósito tomando como referencia el último bloque y actuar en consecuencia | Una reorganización elimina el depósito después de que ya se haya enviado el retiro |
| Una comprobación de estado que solo confirma «el nodo está activo» | Un nodo rezagado en la sincronización **devuelve datos desactualizados** |
| Un balanceador de carga distribuye las solicitudes entre varios nodos | Las alturas de cadena difieren entre nodos → **respuestas distintas a la misma pregunta** |

**Por lo tanto, el diseño de la aplicación debe incluir una regla de «procesar después de N confirmaciones» (profundidad de confirmación), y ese valor depende de las características de finalidad de la cadena.** Esto no se puede resolver solo con infraestructura; es un acuerdo con la aplicación.

Lo que puede hacer la infraestructura:

- **Incluir el estado de sincronización en la comprobación de estado**: definir la disponibilidad como «a menos de N bloques de la cabeza de la cadena», no como «activo»
- **Supervisar las divergencias en la altura de la cadena entre nodos**: retirarlos del balanceo de carga cuando aumente la divergencia
- **Exponer las reorganizaciones como una métrica**, para que la aplicación pueda responder

## Redes P2P: por qué son distintas de los servicios ordinarios

Los nodos de blockchain se comunican **de igual a igual, en lugar de seguir un modelo cliente-servidor.** Esto genera fricciones con el modelo de redes de Kubernetes.

### Protocolos de difusión

Cuando aparece un nuevo bloque o una nueva transacción, **se propaga a los pares vecinos**, que a su vez la propagan a los suyos. Así es como todos llegan a conocerla.

Características:

- Sin intermediario central → sin un único punto de fallo
- **Los mismos datos llegan repetidamente por varias rutas** → se consume ancho de banda en duplicados
- La propagación lleva tiempo → la noción de «último» de cada nodo es distinta (lo que nos devuelve al problema de finalidad anterior)

### Fricciones en un entorno de Kubernetes

| Lo que necesita P2P de blockchain | Valor predeterminado de Kubernetes |
|---|---|
| **Identidad estable del par** (ID de nodo, dirección) | Las IP de los Pod cambian al reiniciarse |
| **Aceptar conexiones entrantes** (otros pares se conectan a mí) | Por defecto, los Pod no son directamente accesibles desde el exterior |
| **Persistencia de la lista de pares** | El estado se pierde al reemplazar un Pod |
| **Anunciar un puerto fijo** | Asignación de puertos del Service |

Por eso los nodos de blockchain suelen usar **StatefulSet + Service sin cabecera**, ya que necesitan nombres estables y orden. Aceptar conexiones P2P entrantes requiere un diseño de exposición adicional. [Ejecución de nodos de blockchain en EKS](./02-nodes-on-eks.md) cubre los detalles.

## Estado y almacenamiento: por qué reconstruir es difícil

Un nodo de blockchain conserva dos cosas.

| Datos | Naturaleza | Tamaño |
|---|---|---|
| **Historial de bloques** | Registro de solo anexado. El pasado es inmutable | Crece continuamente |
| **Estado actual** | Saldos, almacenamiento de contratos. Se puede derivar reproduciendo los bloques | Crece, pero es menor que el historial |

**La propiedad clave: el estado se puede reproducir a partir del historial, pero esa reproducción tarda mucho.**

Reproducir y verificar cada bloque desde el génesis (sincronización completa) lleva un tiempo proporcional a la antigüedad de la cadena. Por eso existen métodos de sincronización alternativos.

| Método | Qué hace | Compensación |
|---|---|---|
| **sincronización completa** | Verifica y reproduce todo desde el génesis | Máxima confianza, **la más lenta** |
| **sincronización snap/rápida** | Obtiene el estado con pruebas verificadas frente a una raíz de estado aceptada; las comprobaciones del historial dependen del cliente/modo | Más rápida, con supuestos explícitos de confianza en el consenso/punto de control y la implementación; no implica confiar ciegamente en un par arbitrario |
| **sincronización desde un punto de control** | Empieza desde un punto de control de confianza | La más rápida, confía en el origen del punto de control |
| **Restauración desde una instantánea** | Restaura un directorio de datos conservado por el operador | Rápida, requiere gestionar la vigencia y coherencia de la instantánea |

**Conclusión operativa**: no debes perder el estado al reemplazar un Pod. Perderlo implica una sincronización larga durante la cual ese nodo no puede prestar servicio. Por eso, un volumen persistente **no es opcional, sino obligatorio** para un nodo de blockchain.

### Nodos de archivo: una consideración aparte

Un nodo que puede consultar el «estado en cualquier momento pasado» es un nodo de archivo. Conserva todos los estados intermedios, por lo que necesita **mucho más almacenamiento** que un nodo normal.

**Aquí se necesita tomar una decisión de diseño**: primero confirma que realmente necesitas capacidades de archivo. La mayoría de las aplicaciones solo necesitan el estado reciente y, si hacen falta consultas históricas, gestionarlas con un servicio de indexación o un almacén de datos es más rentable.

## Gestión de claves: perderla significa que todo se acaba

En blockchain, **la identidad y la autoridad son la clave privada.** Esto crea una diferencia decisiva respecto a los sistemas existentes.

| Sistemas existentes | Blockchain |
|---|---|
| Si olvidas una contraseña, la restableces | **Si pierdes la clave, los activos/la autoridad desaparecen para siempre** |
| Un administrador puede congelar una cuenta vulnerada | No existe ninguna parte que pueda revertirlo (salvo que el protocolo lo permita) |
| Los registros de auditoría permiten rastrear los hechos a posteriori | Una transacción firmada, una vez finalizada, no se puede revertir |

**Por eso la naturaleza de la estrategia de copias de seguridad es distinta.** Los datos de la cadena se pueden volver a obtener de la red, así que hacer copias de seguridad tiene poco valor. En cambio, **es necesario hacer copias de seguridad de las claves**, y **la propia copia de seguridad supone un riesgo de exposición.**

Por eso los HSM y AWS KMS/CloudHSM son importantes en la infraestructura de blockchain. Los validadores, en particular, tienen un requisito contradictorio: **la clave debe estar en línea para firmar, pero no debe filtrarse.** [Perspectiva de los servicios financieros](./04-financial-services.md) aborda este problema.

## Características operativas: qué se desprende de todo esto

Resumen de las características operativas que generan estos conceptos:

| Diseño de blockchain | Característica operativa resultante | Implicación en Kubernetes |
|---|---|---|
| Validación replicada por nodos completos | Añadir réplicas no aumenta por sí solo la capacidad de escritura de la cadena base | Puede aumentar la capacidad agregada de RPC/lectura y la disponibilidad |
| El estado se acumula localmente | **Reemplazar un Pod es muy costoso** | StatefulSet + volumen persistente obligatorios; considerar la afinidad de nodos |
| La sincronización de la cadena puede ir con retraso | **«Activo» y «capaz de prestar servicio» son cosas distintas** | Incluir el estado de sincronización en la disponibilidad |
| La finalidad no es inmediata | **Los datos más recientes no son datos definitivos** | La profundidad de confirmación es un acuerdo con la aplicación |
| Difusión P2P | **Necesita conexiones entrantes e identidad estable** | Service sin cabecera, diseño de exposición adicional |
| Las bifurcaciones duras activan reglas en un momento definido | Actualizar los binarios compatibles antes de la activación | Las actualizaciones canary y graduales pueden preparar la flota de antemano |
| Las claves son autoridad | **Perder la clave = pérdida permanente** | KMS/HSM, estrategias de copia de seguridad distintas para las claves y los datos |
| La verificación redundante es el objetivo | **Consumo constante de CPU e IOPS** | Poco adecuado para configuraciones de recursos orientadas a ráfagas |

**Esta tabla es el núcleo de esta sección.** Todas las recomendaciones concretas del documento 2 se derivan de ella.

## Bifurcaciones duras: el mayor choque con el modelo operativo de Kubernetes

Un cambio de protocolo que no es compatible con versiones anteriores es una **bifurcación dura.** Toda la red cambia a las nuevas reglas en una altura de bloque o momento determinado, y **los nodos que no cambian permanecen en una cadena distinta.**

Dónde choca con la sabiduría convencional de Kubernetes:

| Convención de Kubernetes | Durante una bifurcación dura |
|---|---|
| Transición gradual mediante una actualización progresiva | Es válida antes de la activación, siempre que todos los nodos necesarios admitan las nuevas reglas antes de la fecha límite |
| Probar primero una parte en canary | Probar los binarios compatibles con la bifurcación antes de la activación; comparar el comportamiento en la fase adecuada de testnet/mainnet |
| Revertir si hay problemas | Revertir deja ese nodo en la cadena antigua |
| El equipo de operaciones fija el calendario de las actualizaciones | **El calendario se establece externamente** |

**Recomendación práctica**: trata una bifurcación dura no como un despliegue, sino como **una migración con fecha límite.** Suscríbete a las notas de publicación de los clientes, actualiza mucho antes de la fecha de la bifurcación y valida primero en una testnet.

Ethereum implementó Pectra y Fusaka en 2025 y ha avanzado hacia actualizaciones más frecuentes. **Planifica el mantenimiento usando las fechas de activación publicadas y las notas de publicación de los clientes, no un calendario garantizado de dos veces al año.**

## Resumen

- Compara el modelo de consenso y confianza elegido: **etcd/Raft tolera fallos de tipo crash**, algunas blockchains usan BFT y Fabric con permisos puede usar CFT Raft o SmartBFT. La etiqueta blockchain por sí sola no implica tolerancia a fallos bizantinos.
- Muchos diseños de nodo completo replican la verificación; los modelos de cliente ligero y con permisos son distintos, y la capacidad de RPC/lectura puede escalar por separado de las escrituras en la cadena base.
- La cadena `prev_hash` propaga la manipulación y **los árboles de Merkle** permiten pruebas de inclusión de tamaño log-N (la base de los clientes ligeros).
- El consenso necesita un costo por la **defensa contra Sybil.** Restringir la participación (consorcio) elimina esa necesidad y permite BFT con mayor rendimiento y finalidad, a costa de la descentralización.
- **La finalidad es el concepto más importante desde el punto de vista operativo.** Los datos más recientes no son datos definitivos; por eso, incluye el estado de sincronización en la disponibilidad y establece la profundidad de confirmación como un acuerdo con la aplicación.
- El estado se puede reproducir, pero **la reproducción tarda mucho**, por lo que los volúmenes persistentes son obligatorios.
- Una bifurcación dura tiene un punto de activación coordinado externamente; prepara con antelación clientes compatibles y evalúa por separado la reversión posterior a la activación.

Siguiente: [Ejecución de nodos de blockchain en EKS](./02-nodes-on-eks.md) traduce estas características en una configuración concreta.

## Referencias

- [Documentación para desarrolladores de Ethereum](https://ethereum.org/developers/docs/): consenso, nodos, clientes
- [Ethereum: prueba de participación](https://ethereum.org/developers/docs/consensus-mechanisms/pos/)
- [Documentación de Hyperledger Fabric](https://hyperledger-fabric.readthedocs.io/): estructura de una cadena con permisos
- [Guía para desarrolladores de Bitcoin](https://developer.bitcoin.org/devguide/): PoW y árboles de Merkle
- [Arquitectura del clúster: etcd y Raft](../core/01-cluster-architecture.md): comparación con el consenso tolerante a fallos de tipo crash


- [Servicio de ordenamiento de Fabric](https://hyperledger-fabric.readthedocs.io/en/latest/orderer/ordering_service.html): CFT Raft frente a SmartBFT
