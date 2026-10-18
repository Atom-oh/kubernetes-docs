# Cuestionario sobre Amazon Managed Blockchain

Este cuestionario evalúa tu comprensión de los componentes de AMB, la frontera entre servicios administrados y autogestionados, y el riesgo de discontinuación del servicio.

## Preguntas de opción múltiple

1. ¿Cómo deben compararse las ofertas de AMB?
   - A) Las tres resuelven el mismo problema con distintos precios
   - B) Distinguir Fabric y los nodos dedicados de las API sin servidor de Access y Query, cada una con facturación y capacidades específicas
   - C) Se dividen en entornos de desarrollo, pruebas y producción
   - D) Se dividen en cadenas públicas, privadas e híbridas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Distinguir Fabric y los nodos dedicados de las API sin servidor de Access y Query, cada una con facturación y capacidades específicas**

**Explicación:**
AMB no siempre se factura por nodo. Los recursos dedicados, las solicitudes RPC sin servidor y las API Query indexadas tienen precios y cobertura distintos.
</details>

2. ¿Cuál es el aspecto más importante que los nodos administrados de AMB *no* resuelven?
   - A) La recopilación de métricas de CloudWatch
   - B) La operación de validadores: los nodos administrados se usan para consultar datos y enviar transacciones, mientras que el staking PoS requiere un conjunto distinto de medidas para la gestión de claves y la disponibilidad de firma, además de gestionar el riesgo de slashing
   - C) El control de acceso basado en IAM
   - D) La conectividad privada de VPC

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La operación de validadores: los nodos administrados se usan para consultar datos y enviar transacciones, mientras que el staking PoS requiere un conjunto distinto de medidas para la gestión de claves y la disponibilidad de firma, además de gestionar el riesgo de slashing**

**Explicación:**
Los nodos de cadenas públicas de AMB Access sirven para leer datos de la cadena y enviar transacciones. La validación PoS añade requisitos de disponibilidad de firma y protección contra el slashing. Los firmantes sin coordinación pueden producir mensajes conflictivos que expongan al validador al slashing; las firmas duplicadas idénticas no se penalizan automáticamente. La implementación habitual usa un único firmante activo, con conmutación por error protegida mediante fencing y el historial de slashing preservado; un firmante distribuido necesita coordinación probada. El acceso a nodos de AMB no proporciona ese diseño de validación, por lo que el staking requiere una operación independiente o un servicio especializado.
</details>

3. ¿Qué se presenta como el primer paso para decidir entre administrar el servicio y autogestionarlo?
   - A) ¿Cuánto cuesta?
   - B) ¿Realmente necesitas un nodo? Si solo consultas datos, AMB Query o un servicio RPC de terceros podrían ser suficientes
   - C) ¿Qué cadena usarás?
   - D) ¿Cuántos profesionales de operaciones tienes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) ¿Realmente necesitas un nodo? Si solo consultas datos, AMB Query o un servicio RPC de terceros podrían ser suficientes**

**Explicación:**
El orden de decisión es ① ¿realmente necesitas un nodo? → ② ¿necesitas control? → ③ costo → ④ ¿puedes combinar opciones? Ejecutar nodos es una opción costosa y exigente, así que primero hay que confirmar que sean necesarios, y **muchos casos se descartan en el paso 1.** En el paso 2, necesitar elegir el cliente, ajustar su configuración, usar un nodo de archivo o participar como validador implica autogestionarlo.
</details>

4. ¿Qué lección ofrece el caso de Amazon QLDB para las decisiones de arquitectura?
   - A) Los servicios administrados siempre cuestan menos que la autogestión
   - B) Los servicios administrados también pueden discontinuarse y la ruta de migración ofrecida quizá no sea funcionalmente equivalente: migrar a Aurora PostgreSQL implica perder la verificabilidad criptográfica
   - C) Las bases de datos de libro mayor solo se pueden implementar con blockchain
   - D) Los servicios de AWS tienen garantizados cinco años de soporte después de su disponibilidad general (GA)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los servicios administrados también pueden discontinuarse y la ruta de migración ofrecida quizá no sea funcionalmente equivalente: migrar a Aurora PostgreSQL implica perder la verificabilidad criptográfica**

**Explicación:**
QLDB se anunció en 2018, alcanzó la disponibilidad general en 2019, anunció el fin del soporte en julio de 2024 y **el servicio finalizó el 31 de julio de 2025.** La ruta propuesta por AWS fue Aurora PostgreSQL; se puede crear una funcionalidad similar a un libro mayor mediante extensiones, pero no sustituye el valor principal de QLDB: «demostrar matemáticamente que nada se manipuló». Las lecciones son: ① los servicios administrados conllevan riesgo de discontinuación ② «hay un reemplazo» no significa «ofrece lo mismo» ③ el plazo de aviso puede ser corto ④ es más fácil dejar de usar tecnología estándar.
</details>

5. ¿Cuál es la mitigación más eficaz frente al riesgo de discontinuación del servicio?
   - A) Implementar simultáneamente en varios proveedores de nube
   - B) Usar protocolos estándar y una capa de abstracción: si la aplicación se comunica mediante una interfaz RPC estándar, se puede cambiar el backend entre AMB, uno autogestionado y uno de terceros
   - C) No usar servicios administrados
   - D) Firmar un contrato de largo plazo con AWS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar protocolos estándar y una capa de abstracción: si la aplicación se comunica mediante una interfaz RPC estándar, se puede cambiar el backend entre AMB, uno autogestionado y uno de terceros**

**Explicación:**
Una interfaz estándar como Ethereum JSON-RPC puede facilitar el reemplazo de backends compatibles, mientras que las API específicas de AMB generan acoplamiento. Conserva los datos necesarios de forma independiente y mide cuánto tardarían la resincronización o la migración. Planifica la recuperación y la salida de las claves antes de empezar: **las claves privadas de firma en KMS no se pueden exportar**. Distingue entre descargar una clave pública, hacer copias de seguridad del material de claves importado, las reglas de extracción y encapsulado de CloudHSM, y las opciones de rotación de cuentas o contratos; elegir una clave administrada no proporciona por sí solo una copia de seguridad portátil de la clave privada.
</details>

6. ¿Por qué es una ventaja sustancial la integración de AMB con IAM?
   - A) IAM firma las transacciones de blockchain por ti
   - B) El endpoint RPC de un nodo autogestionado necesita su propio esquema de autenticación o controles exclusivos en la capa de red, mientras que AMB se puede controlar mediante IAM de forma coherente con el modelo interno de permisos
   - C) IAM hace copias de seguridad de las claves automáticamente
   - D) Las políticas de IAM pueden modificar los datos de la cadena

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El endpoint RPC de un nodo autogestionado necesita su propio esquema de autenticación o controles exclusivos en la capa de red, mientras que AMB se puede controlar mediante IAM de forma coherente con el modelo interno de permisos**

**Explicación:**
El control de acceso al endpoint RPC de un nodo autogestionado requiere crear un esquema de autenticación o depender únicamente de controles en la capa de red, como Security Groups o NetworkPolicy. AMB se puede controlar con políticas de IAM y administrar de manera coherente con el modelo interno de permisos. También integra métricas y registros de CloudWatch, auditoría de las API de administración de CloudTrail, conectividad privada mediante endpoints de VPC/PrivateLink y gestión de claves de KMS.
</details>

7. ¿Qué elemento aparece marcado como `Needs verification` en el documento de AMB?
   - A) Que AMB Query proporciona datos mediante una API
   - B) La lista de cadenas compatibles con AMB, la disponibilidad regional y el estado de vista previa/GA
   - C) Que QLDB finalizó el 31 de julio de 2025
   - D) Que AMB admite Hyperledger Fabric

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La lista de cadenas compatibles con AMB, la disponibilidad regional y el estado de vista previa/GA**

**Explicación:**
Las cadenas compatibles y su estado varían con el tiempo. Entre los cambios confirmados están el fin de la red de pruebas Ethereum Goerli (1 de abril de 2024) y el de la red de pruebas Polygon Mumbai (15 de abril de 2024); en un momento dado, Polygon PoS mainnet también estuvo en Public Preview.

El fin del soporte de AMB ya no es un asunto pendiente: AWS deja de aceptar nuevos clientes de AMB el 29 de octubre de 2026 y el acceso finaliza el 29 de septiembre de 2027 (guía de migración de AMB, https://docs.aws.amazon.com/managed-blockchain/latest/ethereum-dev/migrating-node-rpc-workloads.html).
</details>
