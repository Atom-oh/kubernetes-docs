# Amazon Managed Blockchain

> **Última actualización**: October 12, 2026

## Qué cubre este documento

- Qué cargas de [operar por cuenta propia](./02-nodes-on-eks.md) asume Amazon Managed Blockchain (AMB), y qué no puede hacer
- Criterios para elegir entre servicios gestionados y operación propia, y una variable que debes incluir en esa evaluación
- Qué implicaciones tiene para las decisiones de arquitectura el cambio en la cartera de servicios de ledger y blockchain de AWS

## De qué se compone AMB

AMB no es un solo servicio, sino un conjunto de componentes con características distintas.

| Oferta | Qué proporciona | Límites de costos/operaciones |
|---|---|---|
| **Hyperledger Fabric** | Recursos de red, miembros y peers con permisos | Precios por componente/nodo/almacenamiento y red; el cliente conserva las responsabilidades de aplicación, canales e identidad |
| **Nodos dedicados de Ethereum** | Acceso a nodos gestionados en redes compatibles | Cargos por nodo/almacenamiento/red, cuando corresponda |
| **AMB Access sin servidor** | Acceso RPC a cadenas públicas compatibles sin aprovisionar nodos dedicados | Precios por solicitud; verifica las cadenas, los métodos y las regiones actuales |
| **AMB Query** | API para datos de blockchain indexados | Precios por API/solicitud y cobertura de consultas compatible; no sustituye a un RPC arbitrario de nodo completo |

Estas ofertas tienen distintos modelos de aprovisionamiento, API, facturación y responsabilidades. Primero elige la red y el método que necesitas; no consideres AMB un único servicio universal con precios por nodo.

::: warning Requiere verificación
Los **frameworks y las cadenas compatibles con AMB, la disponibilidad regional y el estado de vista previa/GA varían con el tiempo en cada componente.** Entre los cambios confirmados figuran el fin del soporte para la red de pruebas Ethereum Goerli (1 de abril de 2024) y la red de pruebas Polygon Mumbai (15 de abril de 2024); en un momento dado, Polygon PoS mainnet se ofreció en **vista previa pública**.

**Antes de finalizar un diseño, consulta directamente la [documentación oficial de AMB](https://docs.aws.amazon.com/managed-blockchain/) y la disponibilidad regional.** Este documento no afirma cuál es el estado actual de compatibilidad de ninguna cadena específica.
:::

## Qué asume

La comparación con las cargas cubiertas en el [documento sobre operación propia](./02-nodes-on-eks.md) deja claro el límite.

| Carga al operar por cuenta propia | Con AMB |
|---|---|
| Diseño de StatefulSet, volúmenes y clases de almacenamiento | **Gestionado** |
| Supervisión del crecimiento del disco y ampliación de volúmenes | **Gestionado** |
| Sincronización inicial y gestión de snapshots | **Gestionado** |
| Exposición P2P y configuración de la dirección anunciada | **Gestionado** |
| Actualizaciones de versiones del cliente | **Gestionado** |
| Respuesta ante hard forks | **Gestionada** (nodos gestionados) |
| Infraestructura de emisión de certificados de Fabric | **En gran medida gestionada** (CA gestionada) |
| Disponibilidad de los nodos y base de supervisión | **Gestionadas** |

Los proveedores gestionados se encargan del mantenimiento de nodos/servicios que promete la oferta elegida. Verifica las redes compatibles, los avisos de actualización, el comportamiento de la API y las responsabilidades de aplicación que conservas; el ritmo del protocolo no define por sí solo una garantía del servicio de AWS.

## Qué no puede hacer

Este es el punto clave de la decisión.

| Elemento | Limitación |
|---|---|
| **Elección del cliente** | Limitada a los clientes y versiones que ofrece AMB. No puedes controlar directamente una estrategia de [diversidad de clientes](./02-nodes-on-eks.md) |
| **Ajustes detallados** | No se pueden ajustar los tamaños de caché, los modos de pruning ni los parámetros del kernel |
| **Cadenas compatibles** | Solo las que admite AMB. En general, las cadenas nuevas o pequeñas no son compatibles |
| **Modo de archivo** | La cobertura puede ser limitada |
| **Operación de validadores** | Por lo general, los nodos gestionados sirven para **consultas y envío de transacciones**. Ejecutar un validador de staking es otra cuestión |
| **Región y configuración de red** | Limitadas a las regiones y opciones de conectividad compatibles con AMB |
| **Estructura de costos** | Depende de la oferta: costos de nodos/componentes aprovisionados o cargos por solicitudes/API sin servidor; mide una cobertura y un uso equivalentes |

**La operación de validadores es una distinción especialmente importante.** Los nodos de cadenas públicas de AMB Access sirven para leer datos de la cadena y enviar transacciones; **participar como validador PoS para obtener recompensas de staking tiene otros requisitos** (gestión de claves, disponibilidad de firma y riesgo de slashing). Si el objetivo es hacer staking, AMB no lo resuelve.

## Criterios de selección

| Situación | Recomendación |
|---|---|
| Solo **leer** datos de la cadena | **AMB Query** (no se necesita ningún nodo) |
| Consultas y envío, con poco personal de operaciones | **Nodos gestionados de AMB Access** |
| Se necesita un cliente específico o ajustes | **Operar por cuenta propia** |
| **Validación/staking** | **Operar por cuenta propia** (o usar un servicio especializado de staking) |
| Cadena no compatible con AMB | **Operar por cuenta propia** |
| Fabric de consorcio, inicio rápido | **AMB Access Fabric** |
| Control detallado de Fabric | **Operar por cuenta propia con un operador** |
| Tráfico elevado, objetivo de optimización de costos | **Operar por cuenta propia** (se necesita una comparación) |

### Orden de decisión

**Paso 1: ¿realmente necesitas un nodo?** Si solo consultas datos, AMB Query o un proveedor RPC externo podrían bastar. Ejecutar nodos es una opción costosa y laboriosa, así que **confirma primero que los necesitas.**

**Paso 2: ¿necesitas control?** Si necesitas elegir el cliente, ajustar parámetros, usar modo de archivo o participar como validador, opera por cuenta propia.

**Paso 3: ¿costo?** Calcula el precio de la oferta seleccionada: recursos dedicados, solicitudes sin servidor o API de Query, según corresponda. Compara EC2/EKS, almacenamiento, transferencia, redundancia y costos de personal con una cobertura y disponibilidad equivalentes. No hay un punto de equilibrio universal medido que dependa solo del número de nodos.

**Paso 4: ¿puedes combinar opciones?** Por lo general, sí, y en la práctica suele ser razonable; por ejemplo, usar el servicio gestionado para consultas generales y operar por cuenta propia para fines especiales.

## El cambio en la cartera de servicios de ledger y blockchain de AWS: una variable que debes considerar

Esta es la parte más importante de este documento. **Decidir basándose únicamente en una comparación técnica pasa por alto un riesgo.**

### El fin de Amazon QLDB

Amazon QLDB (Quantum Ledger Database) era una base de datos de ledger gestionada que ofrecía **un registro de transacciones inmutable y verificable criptográficamente.** Se anunció en re:Invent 2018 y pasó a GA en 2019.

| Fecha | Evento |
|---|---|
| 2018 | Anunciado en re:Invent |
| 2019 | GA |
| Julio de 2024 | Se anunció el fin del soporte |
| **31 de julio de 2025** | **Fin del servicio** |

La ruta de migración que ofreció AWS fue **Amazon Aurora PostgreSQL.** Pero hay un aspecto importante: **migrar a Aurora PostgreSQL hace perder la verificabilidad criptográfica, que era el valor central de QLDB.** Se puede implementar una funcionalidad similar a un ledger con extensiones, pero no se sustituye la parte que «demuestra matemáticamente que no se ha manipulado nada».

### Implicaciones

QLDB y AMB son servicios distintos, y **el fin del soporte de QLDB no implicaba por sí mismo el de AMB**; el fin del soporte de AMB se anunció por separado (ver más abajo). Aun así, las lecciones para las decisiones de arquitectura siguen siendo aplicables.

| Lección | Aplicación práctica |
|---|---|
| **También se pueden discontinuar los servicios gestionados** | En especial, los servicios de uso reducido y propósito específico |
| **Una ruta de migración puede no ser funcionalmente equivalente** | «Existe un reemplazo» no significa «ofrece lo mismo» |
| **El plazo de aviso puede ser breve** | Calcula de antemano cuánto tiempo necesitaría tu migración |
| **Es más fácil dejar atrás la tecnología estándar** | Si se basa en un protocolo de código abierto, puedes pasar a operarlo por cuenta propia |

::: warning Fin del soporte anunciado
**AWS ha anunciado el fin del soporte de Amazon Managed Blockchain (AMB).** Dejará de aceptar nuevos clientes el **29 de octubre de 2026**. Los clientes actuales podrán usarlo hasta el **29 de septiembre de 2027**; el acceso finalizará después de esa fecha.

Para AMB Access Ethereum/Bitcoin/Polygon, la [guía de migración de AMB](https://docs.aws.amazon.com/managed-blockchain/latest/ethereum-dev/migrating-node-rpc-workloads.html) recomienda nodos autogestionados en AWS (AWS Blockchain Node Runners cuando exista un blueprint) o un proveedor RPC externo. La [página sobre el fin del soporte de AMB](https://docs.aws.amazon.com/managed-blockchain/latest/hyperledger-fabric-dev/managed-blockchain-end-of-support.html) enumera, para AMB Access Hyperledger Fabric, otra red de Fabric gestionada, Fabric autogestionado en Amazon EC2 o Amazon EKS, o una base de datos de AWS; para AMB Query, un proveedor gestionado de datos de blockchain (consultado el 12 de octubre de 2026).

**Todo diseño que dependa de AMB necesita ahora un plan de migración con una fecha límite fija.** En entornos con ciclos de vida de sistema prolongados, como los servicios financieros, esto afecta directamente a la comparación técnica.
:::

### Diseñar para reducir el riesgo de discontinuación

Este riesgo no se puede eliminar, solo **mitigar.**

| Mitigación | Contenido |
|---|---|
| **Usar protocolos estándar** | Con protocolos abiertos como Ethereum o Fabric, puedes pasar a operarlo por cuenta propia o a otro proveedor si desaparece la oferta gestionada |
| **Una capa de abstracción** | Evita que la aplicación dependa directamente de las API de AMB. Abstraer la interfaz RPC facilita cambiar los backends |
| **Independencia de los datos** | Conserva también los datos de la cadena en tu propio índice o almacén de datos. Los datos históricos sobreviven al cambio de proveedor |
| **Recuperación de claves y salida** | Las claves privadas de firma de KMS no se pueden exportar. Planifica la recuperación y la salida antes de financiar o registrar una identidad; distingue entre la descarga de claves públicas, las copias de seguridad de claves importadas, las reglas de copia de seguridad/envoltura de CloudHSM y las opciones de rotación de cuentas/contratos |
| **Estimar el tiempo de migración** | Medir cuánto tardan la resincronización de nodos y la migración de datos permite determinar si podrías responder dentro del plazo de aviso |

**La «capa de abstracción» es la respuesta más eficaz.** Si la aplicación usa una interfaz RPC estándar (Ethereum JSON-RPC y similares), el backend puede ser AMB, una solución operada por cuenta propia o un tercero. Acoplarse directamente a las API específicas de AMB hace perder esa flexibilidad.

## Integración con servicios de AWS

Una de las ventajas sustanciales de AMB es su integración con el ecosistema de AWS.

| Integración | Uso |
|---|---|
| **IAM** | Control de acceso: políticas de IAM aplicadas al acceso a nodos de cadenas |
| **CloudWatch** | Métricas y registros |
| **CloudTrail** | Auditoría de llamadas a las API de administración |
| **VPC endpoints / PrivateLink** | Conectividad privada |
| **KMS** | Gestión de claves |

**La integración con IAM resulta especialmente útil.** El endpoint RPC de un nodo operado por cuenta propia necesita su propio esquema de autenticación (o solo controles en la capa de red), mientras que AMB se puede controlar mediante IAM y, por tanto, se gestiona de manera coherente con el modelo interno de permisos.

Para la conectividad privada, pueden aplicarse conceptos de la [sección sobre VPC Lattice](../service-mesh/vpc-lattice/README.md), aunque **hay que confirmar por separado si AMB y Lattice se integran directamente** (igual que los elementos no confirmados en [Limitaciones de VPC Lattice](../service-mesh/vpc-lattice/06-constraints.md)).

## Comparación con la operación propia

| Elemento | AMB | Operación propia (EKS/EC2) |
|---|---|---|
| **Tiempo de implementación inicial** | Corto | Largo (incluida la sincronización) |
| **Personal de operaciones** | Poco | Mucho |
| **Respuesta ante hard forks** | AWS | **Tú** |
| **Gestión del crecimiento del disco** | AWS | **Tú** |
| **Elección del cliente** | Limitada | **Libre** |
| **Alcance de los ajustes** | Limitado | **Todo** |
| **Operación de validadores** | Difícil | **Posible** |
| **Cadenas compatibles** | La lista de AMB | **Sin restricciones** |
| **Estructura de costos** | Depende de la oferta: costos de nodos/componentes aprovisionados o cargos por solicitudes/API sin servidor; mide una cobertura y un uso equivalentes |
| **Integración con IAM** | **Incorporada** | Debes implementarla |
| **Riesgo del ciclo de vida del servicio** | La disponibilidad y el soporte de la oferta gestionada pueden cambiar | También persisten las dependencias del mantenimiento de código abierto/clientes, los protocolos y la infraestructura |
| **Portabilidad** | Posible con protocolos estándar | - |

## Resumen

- AMB agrupa **AMB Access Fabric** (redes de consorcio), **nodos públicos de AMB Access** (externalización de la operación de nodos) y **AMB Query** (datos sin nodos), cada uno para resolver un problema distinto.
- El mantenimiento gestionado puede reducir el trabajo de operar nodos, pero siguen siendo relevantes las responsabilidades específicas de cada oferta, los avisos de actualización y la validación de aplicaciones.
- De lo que no puede hacer, la distinción más importante es la **operación de validadores.** Los nodos gestionados sirven para consultas y envíos; el staking tiene otro conjunto de requisitos.
- Orden de decisión: **① ¿realmente necesitas un nodo? → ② ¿necesitas control? → ③ ¿costo? → ④ ¿puedes combinar opciones?** Muchos casos quedan descartados en el paso 1.
- **QLDB finalizó el 31 de julio de 2025**, y su ruta de migración (Aurora PostgreSQL) **no ofrece verificabilidad criptográfica.** Es un ejemplo de servicios gestionados que se discontinuaron y reemplazos que no son funcionalmente equivalentes.
- La mitigación más eficaz consiste en **usar protocolos estándar y una capa de abstracción.** Evita acoplarte directamente a las API específicas de AMB para poder cambiar de backend.
- **AWS ha anunciado el fin del soporte de AMB:** no se aceptarán nuevos clientes a partir del 29 de octubre de 2026 y el acceso finalizará el 29 de septiembre de 2027. Todo diseño que dependa de AMB necesita un plan de migración con fecha.

Siguiente: [Perspectiva de los servicios financieros](./04-financial-services.md) aborda cuestiones regulatorias, de privacidad y de comités de revisión.

## Referencias

- [Documentación de Amazon Managed Blockchain](https://docs.aws.amazon.com/managed-blockchain/)
- [Guía para desarrolladores de AMB Hyperledger Fabric](https://docs.aws.amazon.com/managed-blockchain/latest/hyperledger-fabric-dev/what-is-managed-blockchain.html)
- [Preguntas frecuentes sobre Amazon Managed Blockchain](https://aws.amazon.com/managed-blockchain/faqs/)
- [Historial del documento de AMB Query](https://docs.aws.amazon.com/managed-blockchain/latest/ambq-dg/doc-history.html)
- [Historial del documento de AMB Access Polygon](https://docs.aws.amazon.com/managed-blockchain/latest/ambp-dg/doc-history.html)
- [Ejecución de nodos de blockchain en EKS](./02-nodes-on-eks.md): las cargas de operar por cuenta propia

- [Precios de AMB por oferta](https://aws.amazon.com/managed-blockchain/pricing/)
- [Especificaciones de claves asimétricas de AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/asymmetric-key-specs.html): el acceso a la clave pública no exporta la clave privada
