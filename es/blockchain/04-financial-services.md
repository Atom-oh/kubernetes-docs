# Perspectiva de los servicios financieros

> **Última actualización**: September 13, 2026

## Qué abarca este documento

- Por qué los servicios financieros optan por consorcios en lugar de cadenas públicas, y qué implica realmente esa elección
- Dónde entran en conflicto los requisitos de privacidad con la premisa de que «todos ven el mismo libro mayor», y qué soluciones hay disponibles
- Qué aspectos de la gestión de claves, la regulación y la integración con la infraestructura existente se convierten en cuestiones reales para el comité de revisión

## Primero: descartar los casos en los que blockchain no es la solución

El problema más frecuente en las evaluaciones de blockchain para servicios financieros es **seguir adelante cuando la tecnología no se ajusta al problema.** Este documento empieza con ese filtro.

Como se explica en [Fundamentos](./01-fundamentals.md), la esencia de blockchain es **«llegar a un acuerdo sin un árbitro de confianza».** El precio es el rendimiento y la complejidad. Por tanto:

| Situación | ¿Es adecuada blockchain? |
|---|---|
| Una sola organización posee y controla los datos | Por lo general, conviene empezar con alternativas como bases de datos o registros de auditoría; comparar los requisitos explícitos de verificación y gobernanza |
| Existe un árbitro y todo el mundo confía en él | **No**: basta con la base de datos del árbitro |
| Solo se necesita detectar alteraciones | **Por lo general, no**: bastan las cadenas hash, los registros firmados o el almacenamiento WORM |
| Varias instituciones que desconfían mutuamente actualizan un **estado compartido** | **Vale la pena evaluarlo** |
| Terceros deben poder **verificar de forma independiente** | **Vale la pena evaluarlo** |
| El coste de conciliación entre instituciones es realmente elevado | **Vale la pena evaluarlo** |

**«Solo se necesita detectar alteraciones» es una idea equivocada especialmente común.** Si el objetivo es tener un registro de auditoría o una prueba de integridad, se puede conseguir sin blockchain, mediante un registro firmado de solo anexión, una cadena hash o las funciones WORM (Write Once Read Many) del almacenamiento de objetos, con operaciones mucho más sencillas.

[El caso de Amazon QLDB](./03-managed-blockchain.md) es ilustrativo. QLDB ofrecía precisamente «un libro mayor verificable criptográficamente con una parte central de confianza», partiendo de la premisa de que **eso resuelve muchos problemas.** El servicio terminó, pero la definición del problema sigue siendo válida: muchos requisitos no necesitan un consenso totalmente descentralizado.

**Recomendación práctica**: si no puedes escribir en una sola frase «por qué este problema no debe tener árbitro», compara primero las alternativas que no usan blockchain.

## Por qué un consorcio

Algunas aplicaciones financieras eligen redes permisionadas para controlar la pertenencia, la gobernanza y la ubicación de los datos. Otras usan redes públicas con controles adicionales. **La elección de la red por sí sola no establece el cumplimiento de KYC/AML, la privacidad ni otros requisitos normativos**; evalúa la jurisdicción, la actividad, los participantes y los flujos de datos concretos.

| Restricción | El problema en una cadena pública | En un consorcio |
|---|---|---|
| **Identificación de los participantes (KYC/AML)** | Una dirección pública por sí sola no identifica a una contraparte legal; los controles de la aplicación dependen de la actividad | Los controles de pertenencia ayudan, pero no establecen por sí solos el cumplimiento normativo |
| **Soberanía y ubicación de los datos** | Datos replicados en nodos de todo el mundo | Solo en los nodos que controlan las instituciones participantes |
| **Rendimiento y latencia** | Rendimiento y finalidad probabilística/económica específicos del protocolo | Dependen del consenso y de la carga de trabajo; los permisos no garantizan el rendimiento |
| **Gobernanza** | No se pueden controlar los cambios del protocolo | Decide el consorcio |
| **Modelo de tarifas** | Tarifas de red más costes de operación e integración | Tarifas, gobernanza y costes de infraestructura específicos de la red; no se limita automáticamente a los costes de infraestructura |
| **Gestión de errores** | No se pueden revertir las transacciones incorrectas | Los procedimientos de gobernanza pueden dar respuesta |

La identificación de las contrapartes y la gestión de los datos de clientes deben diseñarse para la actividad y la jurisdicción específicas. Las direcciones públicas no establecen automáticamente el anonimato legal, y pertenecer a un consorcio no satisface automáticamente las obligaciones de identidad o ubicación de los datos. Consulta estos aspectos con responsables cualificados de cumplimiento normativo y asuntos legales.

### Qué implica realmente elegir un consorcio

Aquí es donde hay que ser honestos. Optar por un consorcio **elimina gran parte de la propuesta de valor original de blockchain.**

| Valor de una cadena pública | En un consorcio |
|---|---|
| Resistencia a la censura | ✗ Una parte controla la pertenencia |
| Participación sin permisos | ✗ Se requiere aprobación |
| No se necesita árbitro | △ **El operador del consorcio es, en la práctica, un árbitro** |
| Resistencia a las alteraciones | △ Una mayoría de miembros que colabore puede hacerlo |
| Verificación independiente | ○ Válida entre los miembros |
| **Menores costes de conciliación entre instituciones** | **○ Se mantiene** |
| **Una única versión del estado compartido** | **○ Se mantiene** |

Así pues, el valor sustantivo de una cadena de consorcio se reduce a **«hacer que las instituciones vean los mismos datos para eliminar el trabajo de conciliación».** Ese valor es real, pero es una historia distinta de «descentralizado» o «sin necesidad de confianza».

**Esta distinción importa en las revisiones.** Si en una propuesta escribes «descentralizado y funciona sin confianza», la revisión preguntará «¿quién controla entonces la pertenencia?» y, si la respuesta es «la secretaría del consorcio», la lógica se desmorona. **Definir desde el principio el valor como «menores costes de conciliación entre instituciones» es defendible.**

## Privacidad: el problema más difícil

### La tensión fundamental

La premisa de blockchain es que **«todos ven el mismo libro mayor y lo verifican por sí mismos».** El requisito de una transacción financiera es que **«terceros que no sean contrapartes no deben ver mi transacción».**

**Ambas cosas entran directamente en conflicto.** Para verificar hay que ver; para preservar la privacidad, no se debe ver.

Hay formas de resolver la tensión, cada una con un coste distinto.

### Enfoques y contrapartidas

| Enfoque | Principio | Coste |
|---|---|---|
| **Separación por canales** (Fabric) | Un libro mayor independiente por grupo de transacciones. Solo los miembros del canal tienen los datos | Complejidad operativa por canal. **Las transacciones atómicas entre canales son difíciles** |
| **Recopilación de datos privados** (Fabric) | Solo se almacenan hashes en el libro mayor; los datos reales solo están en los peers autorizados | Carga asociada a la distribución de datos y su ciclo de vida |
| **Pruebas de conocimiento cero (ZKP)** | **Demostrar que una afirmación es verdadera** sin revelar su contenido | Coste computacional, dificultad de diseño de circuitos y revisión de la verificabilidad |
| **Almacenamiento fuera de la cadena** | Datos sensibles fuera de la cadena; solo hashes o punteros en la cadena | La disponibilidad e integridad del almacén externo se convierten en una nueva dependencia |
| **Almacenamiento cifrado** | Texto cifrado en la cadena | **La gestión de claves se convierte en control de acceso**; una filtración de claves expone todo el historial |

### Qué elegir

**La separación por canales es el punto de partida más común.** El concepto es sencillo, Fabric lo proporciona de forma nativa y «quién puede ver qué» queda explícito y es fácil de explicar en una revisión.

Su limitación son **las transacciones entre canales.** Con un canal A-B y otro B-C, es difícil procesar atómicamente una transacción que mueve valor de A→C. Si tu flujo de negocio tiene esa forma, hay que reconsiderar el diseño.

Los registros cifrados en un libro mayor público de solo anexión pueden permanecer en copias históricas; volver a cifrarlos más adelante no elimina esas copias. Una clave comprometida puede revelar los registros cifrados con ella. La eliminación de datos privados en redes permisionadas tiene semánticas distintas, así que valida el modelo real de retención y gestión de claves en lugar de afirmar que ninguna blockchain puede eliminar datos.

**Las ZKP son potentes, pero cuesta superar la revisión.** Explicar a un revisor «demostrar que algo es cierto sin revelar el contenido» y garantizar la corrección de la implementación son retos distintos. Si el esquema requiere una configuración de confianza, también habrá que abordar la fiabilidad de esa configuración.

### Conflicto con el derecho de supresión

Los requisitos de eliminación de la normativa de privacidad entran en conflicto con la inmutabilidad de blockchain.

**La respuesta habitual es «no pongas datos personales en la cadena»**: guarda en la cadena solo identificadores o hashes y mantén los datos personales fuera de ella, donde se puedan eliminar. Sin embargo, alguien que conozca el valor original todavía puede buscar un hash (mediante ataques de tablas arcoíris), por lo que se combina esta medida con la eliminación de la sal o de la clave, para que la recuperación resulte prácticamente imposible (destrucción criptográfica de claves).

::: warning Requiere verificación
**La interpretación legal de los requisitos de eliminación de la normativa de privacidad (la PIPA de Corea, el RGPD, etc.) frente a la inmutabilidad de blockchain varía según la jurisdicción y el caso, y este documento no constituye asesoramiento legal.**

Si los hashes o el texto cifrado constituyen datos personales, y si la destrucción criptográfica de claves satisface una obligación de eliminación, debe **confirmarse con los equipos legales y de cumplimiento normativo y contrastarse con las interpretaciones de los reguladores.** Esa confirmación debe preceder al diseño técnico.
:::

## Gestión de claves: el aspecto más exigente en los servicios financieros

En [Fundamentos](./01-fundamentals.md) se decía que «las claves son autoridad y perderlas es definitivo». Aquí se explica por qué esto resulta especialmente exigente en los servicios financieros.

### Requisitos contradictorios

| Requisito | El requisito en conflicto |
|---|---|
| La clave debe estar **en línea** para firmar transacciones | La clave debe estar **aislada** |
| Disponibilidad: un retraso en la firma implica una interrupción del servicio | Aprobación múltiple: ninguna parte puede firmar por sí sola |
| Las copias de seguridad son obligatorias: la pérdida es permanente | Las copias de seguridad son una vía de exposición |
| Auditabilidad: quién firmó qué | La clave en sí no debe quedar expuesta |

Esta contradicción es **el aspecto más difícil de resolver** en el diseño de blockchain para servicios financieros.

### Mecanismos disponibles

| Mecanismo | Qué ofrece | Límites |
|---|---|---|
| **HSM** (CloudHSM, HSM local) | Firma respaldada por hardware y protecciones de claves configurables | Comprueba la compatibilidad con los algoritmos, la posibilidad de extracción o envoltura y la política de copias de seguridad del módulo elegido |
| **AWS KMS** | Claves gestionadas, integración con IAM y auditoría de CloudTrail | Verifica si admite los algoritmos de firma que requiere la blockchain |
| **MPC** (computación multipartita) | Claves almacenadas de forma **distribuida**; las partes se combinan para firmar y no existe una clave completa en ningún lugar | Complejidad de implementación y dependencia del proveedor |
| **Multifirma** | Se requiere un número N de firmas M a nivel de protocolo | Requiere compatibilidad de la cadena/contrato. Mayor coste por transacción |
| **Separación entre almacenamiento en frío y en caliente** | Grandes cantidades fuera de línea; solo pequeñas cantidades en línea | Carga de los procedimientos operativos |

### Compatibilidad con las curvas: varía según la capa

**Esta es la suposición que más a menudo hace fracasar el diseño de gestión de claves.** Un plan basado en «usaremos KMS» puede fallar por la compatibilidad con los algoritmos; el punto clave es que **las dos capas de Ethereum usan curvas distintas.**

| Capa | Curva | Uso | AWS KMS / CloudHSM |
|---|---|---|---|
| **Capa de ejecución** (cuentas, transacciones) | **secp256k1** | Firma de transacciones, cuentas EOA | **✅ Compatible**: especificación de clave KMS `ECC_SECG_P256K1`, uso restringido a `SIGN_VERIFY` |
| **Capa de consenso** (validadores) | **BLS12-381** | Firma de propuestas de bloque y atestaciones | **❌ No compatible** |

`ECC_SECG_P256K1` de KMS con `SIGN_VERIFY` puede admitir un **flujo de firma ECDSA de Ethereum adaptado**. La compatibilidad con la curva por sí sola no basta: valida el tratamiento del resumen criptográfico, la conversión de firmas DER a las de la cadena, los requisitos de low-S y recuperación, y el formato exacto de la transacción. Los esquemas de firma de Bitcoin son distintos; la compatibilidad con secp256k1 no implica compatibilidad con todos los flujos de Schnorr/Taproot. Haz pruebas sin fondos reales.

**El problema está en la capa de consenso.** BLS12-381 no figura entre las especificaciones de claves de KMS y CloudHSM tampoco la admite. **Por tanto, un diseño que almacene las claves de firma de los validadores en KMS/HSM sencillamente no funciona.**

La alternativa propuesta por AWS es **Nitro Enclaves**: ejecutar un firmante como Web3Signer dentro de un entorno de ejecución aislado para que la clave nunca salga del enclave. La generación de claves (keystores BLS12-381 en formato EIP-2335) también requiere un enfoque aparte.

**Implicación para el diseño**: además de la contradicción relativa a las claves de validadores descrita anteriormente (siempre en línea + aisladas + sin doble firma), hay otra limitación: **la respuesta habitual de «proteger la clave en un HSM» no es aplicable.** Si estás evaluando operaciones de validadores, este es el primer punto de decisión que obliga a apartarse de un diseño basado en KMS.

::: warning Requiere verificación
El estado de compatibilidad anterior corresponde al momento de la investigación y **la compatibilidad de los HSM con BLS12-381 es un tema que lleva mucho tiempo debatiéndose en el sector, así que podría cambiar.** La compatibilidad con curvas de protocolos distintos de Ethereum (por ejemplo, cadenas que usan Ed25519) también debe confirmarse por separado.

**Antes de diseñar, consulta la lista actual en la [referencia de especificaciones de claves de KMS](https://docs.aws.amazon.com/kms/latest/developerguide/symm-asymm-choose-key-spec.html) y verifica siempre con una PoC que la firma real sea válida en la cadena de destino.**
:::

### El caso especial de las claves de validadores

Ejecutar un validador PoS añade un problema.

- **La clave de firma debe estar en línea continuamente**, ya que las oportunidades de firma llegan en cada slot
- **Las firmas en conflicto de un mismo validador pueden dar lugar a penalizaciones (slashing).** Varios firmantes o copias de claves sin coordinación crean ese riesgo; no toda firma idéntica duplicada implica automáticamente una penalización.
- Por tanto, **«tener redundancia para lograr una alta disponibilidad» genera por sí mismo el riesgo**

En despliegues ordinarios, usa un único firmante activo con conmutación por error protegida contra la activación simultánea y con el historial de protección contra slashing preservado. Cualquier firmante activo-activo o distribuido requiere un diseño probado de protección contra slashing compartida. No inicies un segundo firmante con copias de las claves de validador en uso solo para mejorar la disponibilidad.

## Cuestiones normativas y de revisión

Las preguntas que realmente surgen en las revisiones de servicios financieros:

| Cuestión | La pregunta | La respuesta que hay que preparar |
|---|---|---|
| **Necesidad** | ¿Por qué no usar una base de datos convencional? | Una frase que explique «por qué esto no debe tener árbitro» |
| **Control de los participantes** | ¿Quién controla la pertenencia y cómo? | Estructura de gobernanza y procedimientos de incorporación y salida |
| **Ubicación de los datos** | ¿Dónde se replican los datos? | Ubicación de los nodos y medidas de control regional |
| **Control de acceso** | ¿Quién puede ver qué? | Diseño de canales/PDC y política de cifrado |
| **Solicitudes de eliminación** | ¿Cómo se responde a las solicitudes de eliminación de datos personales? | Un diseño que mantenga los datos personales fuera de la cadena |
| **Gestión de claves** | ¿Dónde están las claves y quién puede acceder a ellas? | Estructura de HSM/KMS/MPC y segregación de funciones |
| **Corrección de errores** | ¿Cómo se revierte una transacción incorrecta? | Procedimiento de gobernanza. **La respuesta debe ser un proceso, no tecnología** |
| **Disponibilidad** | ¿Qué ocurre si falla un nodo o el consorcio? | Dominios de fallo y operación independiente por miembro |
| **Auditoría** | ¿Qué comprueba un auditor y cómo? | Método de acceso para auditorías y registros |
| **Actualizaciones** | ¿Quién decide los cambios del protocolo? | Gobernanza del consorcio |
| **Plan de terminación** | Si se cierra el servicio, ¿qué ocurre con los datos? | **Una estrategia de salida** |
| **Dependencia de proveedores/servicios** | ¿Qué pasa si se interrumpe el servicio gestionado? | Protocolos estándar y capa de abstracción ([documento de AMB](./03-managed-blockchain.md)) |

### Los dos aspectos que con más frecuencia se preparan insuficientemente

**① Corrección de errores: «no se puede revertir» se convierte en una debilidad durante la revisión.**

La inmutabilidad que se promociona como una fortaleza de blockchain es **un problema** en las operaciones financieras. Sí ocurren transacciones incorrectas, transferencias equivocadas y errores del sistema, y las instituciones financieras tienen obligaciones y procedimientos para corregirlos.

**La respuesta es un proceso, no tecnología.** El enfoque habitual no es «revertir la cadena», sino **«emitir una transacción compensatoria»**: el registro original se mantiene y se añade una transacción compensatoria para corregir el resultado. Es el mismo concepto que un asiento de reversión en contabilidad. Documenta ese procedimiento y quién tiene autoridad para aprobarlo, de cara a la revisión.

**② Estrategia de salida: casi nunca se prepara.**

¿Qué pasa con los datos y las obligaciones cuando se disuelve un consorcio, se retira un miembro o se cierra el sistema? Los datos financieros conllevan obligaciones de conservación, por lo que **«apagamos la cadena» no es el final.**

Qué hay que preparar: el formato de exportación del libro mayor, quién lo conserva, cómo se gestionan los datos de los miembros que se retiran y cómo se accede a los registros. **Esto debe constar en el acuerdo del consorcio** y el diseño técnico debe permitirlo.

## Integración con la infraestructura financiera existente

La realidad es que blockchain se sitúa **junto a** los sistemas existentes, en lugar de sustituirlos. Los problemas prácticos surgen en los puntos de integración.

| Problema de integración | Contenido |
|---|---|
| **Desajuste de finalidad** | Los sistemas existentes consideran definitivo un commit de la base de datos. Una cadena necesita cierta profundidad de confirmación → **gestión del estado en el límite** |
| **Falta de atomicidad** | Una transacción en una base de datos existente y una transacción en la cadena **no se pueden vincular en una sola unidad atómica** |
| **Diferencia de rendimiento** | Los sistemas existentes son mucho más rápidos → la cadena se convierte en el cuello de botella. Se necesitan colas y procesamiento por lotes |
| **Diferencia de reversibilidad** | Los sistemas existentes permiten deshacer cambios; las cadenas no → el diseño de escenarios de fallo es asimétrico |
| **Sincronización horaria** | Conciliación entre la hora de los bloques y la hora del sistema existente |

**La «falta de atomicidad» es el problema más sustantivo.** Si se produce un fallo entre la escritura en la base de datos y el envío de la transacción a la cadena, se genera una incoherencia. Como no se pueden vincular en una transacción distribuida, se necesitan enfoques de consistencia eventual, como **el patrón Saga o el patrón outbox**, conectados con el **procedimiento de transacción compensatoria** descrito anteriormente.

Esta es una decisión de arquitectura, así que **hay que abordarla al principio del diseño.** Si se añade más tarde, los problemas de coherencia de datos salen a la luz en producción.

## Una ruta de adopción realista

| Etapa | Contenido |
|---|---|
| **1. Validar el problema** | Confirmar que se necesita blockchain. Comparar alternativas (base de datos convencional, registros firmados, WORM) |
| **2. Asegurar la participación de las instituciones** | Acordar los participantes previstos y sus funciones; justificar las ventajas del libro mayor compartido, la verificación y la gobernanza frente a alternativas más sencillas, en lugar de dar por hecho un número mínimo universal de instituciones |
| **3. Acordar la gobernanza** | Antes que la tecnología. Pertenencia, toma de decisiones, disputas y salida |
| **4. Diseñar la privacidad** | Estructura de canales/PDC. En conjunto con los responsables de revisión |
| **5. Confirmación legal y de cumplimiento normativo** | Solicitudes de eliminación, ubicación de los datos y requisitos de auditoría |
| **6. PoC** | Validación técnica y **medición del rendimiento y la carga operativa** |
| **7. Piloto** | Transacciones reales con un alcance limitado |
| **8. Operaciones** | [Operaciones de nodos](./02-nodes-on-eks.md), supervisión, renovación de certificados y bifurcaciones duras/actualizaciones |

El objetivo de esta tabla es señalar que **las etapas 2 y 3 preceden a la tecnología.** Incluso una validación técnica satisfactoria no llega a ninguna parte sin instituciones participantes ni una gobernanza acordada. En la práctica, muchos proyectos de blockchain para servicios financieros se detuvieron en esta etapa.

## Resumen

- **Descarta primero los casos en los que blockchain no es la solución.** Si no puedes escribir en una frase «por qué esto no debe tener árbitro», compara las alternativas. Si solo se necesita detectar alteraciones, bastan los registros firmados o WORM.
- Las razones decisivas por las que los servicios financieros optan por consorcios son **las obligaciones de KYC/AML y la soberanía de los datos.** El rendimiento y la gobernanza son beneficios secundarios.
- Elegir un consorcio **elimina gran parte del valor original de blockchain.** Lo que queda, en esencia, es **«reducir los costes de conciliación entre instituciones»**, y definir el valor así es defendible en una revisión.
- Elige mecanismos de privacidad que se ajusten al modelo de datos real. Las copias históricas de texto cifrado pueden perdurar después de rotar las claves; valida explícitamente la retención, la eliminación de datos privados y las obligaciones legales.
- La gestión de claves debe equilibrar el aislamiento y la disponibilidad para firmar. En validadores PoS, los firmantes sin coordinación pueden producir **mensajes en conflicto susceptibles de penalización (slashing)**; una firma duplicada idéntica no implica automáticamente una penalización. Usa conmutación por error protegida contra la activación simultánea y conserva el historial de slashing, o emplea un diseño probado de firma distribuida coordinada.
- Los dos aspectos que más suelen prepararse insuficientemente para la revisión son **la corrección de errores** (la respuesta es un procedimiento de transacción compensatoria, no tecnología) y **una estrategia de salida** (las obligaciones de conservación implican que «lo apagamos» no es el final).
- La dificultad central para integrarse con la infraestructura existente es **la falta de atomicidad.** Incorpora pronto al diseño enfoques de consistencia eventual, como Saga/outbox.
- En la ruta de adopción, **asegurar la participación de las instituciones y acordar la gobernanza son pasos previos a la tecnología.**

## Referencias

- [Hyperledger Fabric: datos privados](https://hyperledger-fabric.readthedocs.io/en/latest/private-data/private-data.html)
- [Hyperledger Fabric: canales](https://hyperledger-fabric.readthedocs.io/en/latest/channels.html)
- [Documentación de AWS CloudHSM](https://docs.aws.amazon.com/cloudhsm/) / [Documentación de AWS KMS](https://docs.aws.amazon.com/kms/)
- [Referencia de especificaciones de claves de AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/symm-asymm-choose-key-spec.html): incluye `ECC_SECG_P256K1`
- [Usar AWS KMS para gestionar cuentas de Ethereum de forma segura (AWS Web3 Blog)](https://aws.amazon.com/blogs/web3/use-key-management-service-aws-kms-to-securely-manage-ethereum-accounts-part-1/)
- [AWS Nitro Enclaves para ejecutar validadores de Ethereum (AWS Web3 Blog)](https://aws.amazon.com/blogs/web3/aws-nitro-enclaves-for-running-ethereum-validators-part-1/): la alternativa dado que BLS12-381 no es compatible
- [Amazon Managed Blockchain](./03-managed-blockchain.md): riesgo de interrupción y mitigación
- [Fundamentos de blockchain](./01-fundamentals.md): consenso y finalidad
- [Ejecución de nodos de blockchain en EKS](./02-nodes-on-eks.md): operaciones
- [Seguridad de EKS](../eks/05-eks-security.md) / [Seguridad](../core/06-security.md): controles generales de seguridad
