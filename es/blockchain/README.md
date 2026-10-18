# Descripción general de blockchain

> **Última actualización**: 12 de septiembre de 2026

## Qué abarca esta sección

- Qué tipo de carga de trabajo es una blockchain **desde la perspectiva de un ingeniero de infraestructura** y por qué sus características operativas difieren de las de los servicios con estado habituales
- Qué problemas reales encuentras al ejecutar nodos de blockchain en Kubernetes (EKS): almacenamiento, redes P2P, sincronización y actualizaciones
- El límite entre los servicios administrados (Amazon Managed Blockchain) y los autogestionados, y cómo cambia esa elección en los servicios financieros

## Por qué esta sección está en este repositorio

Este repositorio contiene material de formación sobre Kubernetes y EKS. Blockchain está aquí porque **un nodo de blockchain es una carga de trabajo inusual para un operador de Kubernetes.**

La mayoría de las cargas de trabajo de Kubernetes son de uno de estos dos tipos: sin estado, por lo que puedes detenerlas y reiniciarlas libremente, o con estado, pero susceptibles de trasladarse a un servicio administrado (RDS, ElastiCache). Un nodo de blockchain **no es ninguna de las dos cosas.**

| Suposición habitual | En el caso de un nodo de blockchain |
|---|---|
| «Los Pods se pueden reemplazar en cualquier momento» | Reconstruir cientos de GB o varios TB de estado local puede llevar **días** |
| «Escalar horizontalmente aumenta el rendimiento» | Las réplicas pueden escalar las lecturas de RPC y la disponibilidad, pero no aumentan automáticamente la capacidad de escritura o consenso de la cadena base |
| «Si supera la comprobación de estado, puede atender solicitudes» | Un nodo que va atrasado en la sincronización supera la comprobación de estado y, aun así, **devuelve datos incorrectos** |
| «Las actualizaciones graduales permiten despliegues sin tiempo de inactividad» | Las versiones compatibles con la bifurcación pueden desplegarse primero en un canario y luego gradualmente antes de la activación; la fecha límite del protocolo y la compatibilidad de la reversión posterior a la bifurcación son restricciones independientes |
| «Restaura los datos desde las copias de seguridad» | El estado se puede reproducir a partir de la cadena, pero **si pierdes las claves, todo se acaba** |

Estas diferencias determinan decisiones operativas reales. Esta sección tiene como propósito explicarlas.

## Público y supuestos

- Ingenieros y arquitectos de infraestructura con experiencia operativa en EKS/Kubernetes
- **Suponemos que blockchain es un concepto nuevo para ti**; el documento 1 explica los conceptos desde cero
- El desarrollo de contratos inteligentes, la economía de los tokens y los criterios de inversión quedan fuera de alcance. Esta es **una perspectiva de operaciones de infraestructura**

## Estructura del documento

| # | Documento | Pregunta a la que responde |
|---|----------|---------------------|
| 1 | [Fundamentos de blockchain](./01-fundamentals.md) | ¿Qué son el consenso, los árboles de Merkle, P2P y la finalidad, y por qué se derivan de ese diseño estas características operativas? |
| 2 | [Ejecución de nodos de blockchain en EKS](./02-nodes-on-eks.md) | ¿Cómo se gestionan realmente los StatefulSets, el almacenamiento, P2P, la sincronización y las actualizaciones? |
| 3 | [Amazon Managed Blockchain](./03-managed-blockchain.md) | ¿De qué tareas te libera el servicio administrado y qué no puede hacer? ¿Qué implicaciones tiene el cambio en los servicios de registro contable de AWS? |
| 4 | [Perspectiva de los servicios financieros](./04-financial-services.md) | ¿Cuáles son los problemas reales de la gobernanza de consorcios, la privacidad, la regulación y la integración con la infraestructura existente? |

El documento 1 es un requisito previo para los documentos 2–4. Si ya conoces blockchain, puedes empezar por el 2, pero **la sección «de dónde proceden las características operativas» del documento 1** es necesaria para seguir el documento 2.

## Nota sobre la precisión

Esta sección aborda de forma distinta dos tipos de incertidumbre.

**① Especificaciones de protocolos que evolucionan con rapidez**: utiliza las fechas de activación anunciadas en lugar de presuponer una cadencia de actualizaciones fija. El hardware, el staking y la gestión de blobs pueden cambiar; las cifras que aparecen a continuación son orientativas y están fechadas, no constituyen requisitos garantizados y vigentes.

**② Cifras que no proceden de fuentes primarias**: valores como los requisitos de hardware de los nodos suelen ser estimaciones de la comunidad o de proveedores, no especificaciones oficiales. Estos valores se indican junto con la naturaleza de la fuente y se presentan como intervalos.

Todo lo que no se haya confirmado con documentación oficial se incluye en un bloque `Needs verification`. **Antes de diseñar para producción, comprueba los valores actuales directamente en la documentación oficial del protocolo y en las notas de versión de los clientes.**

## Documentos relacionados

- [Arquitectura del clúster](../core/01-cluster-architecture.md): etcd y consenso (Raft), punto de referencia para comparar con el consenso de blockchain
- [Pods y cargas de trabajo](../core/02-pods-and-workloads.md): StatefulSets
- [Almacenamiento](../core/04-storage.md) / [Almacenamiento de EKS](../eks/04-eks-storage-part1.md): PV/PVC y EBS
- [Comparativa de rendimiento de EBS gp2 y gp3](../storage/01-ebs-gp2-gp3-benchmark.md): qué significan realmente los IOPS
- [Ajuste del kernel de los nodos de EKS](../kernel/03-eks-node-tuning.md): descriptores de archivos, búferes de sockets
- [Descripción general de Data on EKS](../data-on-eks/README.md): cargas de trabajo de datos con estado en general
- [Resiliencia de EKS](../eks/10-eks-resiliency.md): diseño de dominios de error
