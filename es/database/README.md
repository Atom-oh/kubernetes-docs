# Introducción a las bases de datos en Kubernetes

> **Última actualización**: 11 de septiembre de 2026

La pregunta «¿deberías ejecutar bases de datos en Kubernetes?» ya no es una
pregunta de sí o no. La pregunta real es **qué base de datos, operada por qué
operador y sobre qué almacenamiento**. Esta sección presenta un marco para tomar
esa decisión y lo respalda con datos medidos, no solo con hojas de especificaciones.

## Contenido de esta sección

| Documento | Contenido |
|----------|----------------|
| [Prueba comparativa medida de ClickHouse en EKS](./01-clickhouse-on-eks.md) | Un nodo de ClickHouse en EKS cargado con 100 millones de filas de registros: rendimiento de ingesta medido, tasas de compresión, latencia de consultas y efecto de un índice de omisión |

## Servicio administrado frente a alojamiento propio en Kubernetes

| Criterio | Conviene el servicio administrado (RDS/Aurora/ElastiCache) | Conviene el alojamiento propio en K8s |
|-----------|---------------------------------------|----------------------|
| Personal de operaciones | No hace falta un equipo dedicado de DBA/plataforma | El equipo de plataforma es responsable del ciclo de vida |
| Disponibilidad del motor | PostgreSQL/MySQL/Redis con ofertas administradas consolidadas | Regiones, extensiones o versiones requeridas que los servicios administrados disponibles no ofrecen; compara también con ClickHouse Cloud |
| Estructura de costos | Precio del servicio más ahorro en operaciones | Infraestructura, alta disponibilidad, copias de seguridad, actualizaciones y personal en conjunto |
| Densidad de implementación | Pocos inquilinos | Decenas de bases de datos de distintos inquilinos desplegadas mediante GitOps |
| Requisitos de control | Comprueba las regiones, el cifrado y las capacidades de auditoría que se ofrecen | Asumes tanto el control adicional como la responsabilidad operativa |

La pregunta clave es **quién es responsable del ciclo de vida de la base de datos y
de las tareas de recuperación**. Un operador validado puede automatizar parte de
ese trabajo, pero instalarlo no garantiza la alta disponibilidad ni las copias de
seguridad. Comprueba las combinaciones admitidas de motores y Kubernetes, así como
las funciones de recuperación. Si un equipo usa StatefulSets sin operador, debe
implementar la automatización correspondiente y asumir por sí mismo las
responsabilidades operativas.

## Panorama de operadores (2026)

| Base de datos | Operadores principales | Notas sobre la madurez |
|----------|-------------------|----------------|
| PostgreSQL | CloudNativePG, Crunchy PGO, Zalando | Compara las versiones de PostgreSQL y Kubernetes admitidas, y el comportamiento de recuperación |
| MySQL | Percona Operator, Vitess (fragmentación), MySQL Operator (Oracle) | Vitess es una plataforma de fragmentación; compara la compatibilidad con motores y funciones de Percona y Oracle |
| Redis/Valkey | OT-CONTAINER-KIT redis-operator y alternativas; verifica la compatibilidad con el motor | Para el uso como caché, compara siempre primero con los precios de ElastiCache |
| ClickHouse | Altinity clickhouse-operator | Base de datos Apache-2.0 con un operador comunitario consolidado; ClickHouse Cloud es la alternativa administrada |
| MongoDB | MongoDB Controllers for Kubernetes, Percona | El antiguo Community Operator está obsoleto; usa el repositorio y la guía de migración actuales |
| Kafka | Strimzi | El streaming se trata en la [sección de canalizaciones de datos](../data-on-eks/kafka/README.md) |

## Cuatro pilares operativos de las bases de datos en K8s

1. **Almacenamiento**: el tipo de volumen determina tu presupuesto de rendimiento. Como muestra la [prueba comparativa de EBS gp2 frente a gp3](../storage/01-ebs-gp2-gp3-benchmark.md), capacidades idénticas pueden diferir 10 veces en IOPS. Para bases de datos, empieza con gp3 y considera las IOPS aprovisionadas.
2. **Topología**: distribuye las réplicas entre AZ con `topologySpreadConstraints` y ten en cuenta el costo de transferencia entre AZ y la latencia de replicación.
3. **Aislamiento de recursos**: si se desea QoS Guaranteed, cada contenedor debe tener iguales sus solicitudes y límites de CPU y memoria. Esto no elimina los OOM, la limitación de CPU ni los fallos de nodos. Dimensiona los límites de CPU, las cachés, el trabajo en segundo plano y el margen de memoria para las consultas según la carga medida.
4. **Copias de seguridad que realmente hayas restaurado**: habilitar la copia de seguridad del operador (por ejemplo, el complemento Barman Cloud admitido de CloudNativePG para S3) es lo mínimo; los ensayos de restauración programados son lo que demuestra que funciona.

## Lecturas relacionadas

- [ClickHouse como backend de registros](../observability/logging/04-clickhouse.md): ClickHouse desde la perspectiva de la canalización de observabilidad
- [Almacenamiento de Kubernetes](../core/04-storage.md) / [Sección de almacenamiento](../storage/README.md)
- [Almacenamiento de EKS, parte 1](../eks/04-eks-storage-part1.md)

## Referencias

- [Migración del operador de MongoDB](https://github.com/mongodb/mongodb-kubernetes/blob/master/docs/migration/community-operator-migration.md)
- [CloudNativePG](https://cloudnative-pg.io/docs/)
- [ClickHouse Cloud](https://clickhouse.com/cloud)
- [Altinity ClickHouse Operator](https://github.com/Altinity/clickhouse-operator)
