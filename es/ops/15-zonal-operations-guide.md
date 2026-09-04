# Operaciones de clúster zonal: desplazamiento de tráfico, reversión de actualizaciones y afinidad de AZ en la capa de datos

> **Versiones compatibles**: Amazon EKS 1.33+, AWS Load Balancer Controller 2.9+, Kafka 2.4+ (KIP-392), Valkey GLIDE 1.x
> **Última actualización**: July 21, 2026

< [Anterior: Pipelines de Tekton](14-tekton-pipelines.md) | [Tabla de contenidos](./README.md) | [Siguiente: Manual de solución de problemas](16-troubleshooting-playbook.md) >

***

El tema más común en las preguntas de los clientes es «operaciones». Una combinación sigue apareciendo: **dividir los clústeres por zona para aislar fallos, desplazar el tráfico con pesos de grupos de destino del balanceador de carga y, cuando algo falla, revertir localmente en lugar de levantar un clúster nuevo.** Esta guía reúne esa combinación como una única estrategia operativa y añade la pieza que normalmente falta: **fijar la ruta de lectura de la capa de DB/cache/mensajería a una zona.**

Los procedimientos detallados para cada parte ya se encuentran en otros lugares de este repositorio. Este documento explica por qué se utilizan conjuntamente y completa la brecha de la capa de datos que no existía antes.

## Tabla de contenidos

1. [Por qué realizar operaciones zonales](#why-zonal-operations)
2. [Capa de tráfico: Target Group + TargetGroupBinding + desplazamiento de peso](#traffic-layer-target-group--targetgroupbinding--weight-shifting)
3. [Actualizaciones: por qué la actualización local + reversión nativa se convirtió en la opción predeterminada](#upgrades-why-in-place--native-rollback-became-the-default)
4. [Capa de datos: fijar la ruta de lectura a una zona](#data-layer-pinning-the-read-path-to-a-zone)
5. [Resumen de la combinación recomendada](#recommended-combination-summary)

***

## Por qué realizar operaciones zonales

Un único clúster Multi-AZ y una flota de un clúster por AZ (zonal/de una sola zona) implican distintas ventajas y desventajas.

| Aspecto | Un único clúster Multi-AZ | Clústeres zonales (de una sola zona) |
|--------|--------------------------|-------------------------------|
| Aislamiento de fallos | Un fallo de AZ afecta a parte del clúster | Un fallo de AZ afecta solo a ese clúster zonal; el resto no se ve afectado |
| Coste entre AZ | El tráfico de Pod a Pod cruza límites de AZ ($0.01/GB) | Solo tráfico dentro de la misma AZ, sin coste de transferencia entre AZ |
| Actualizaciones | Actualización progresiva; todo el clúster cambia de versión a la vez | Actualización secuencial zona por zona; las demás zonas permanecen en la versión anterior |
| Complejidad operativa | Un clúster que gestionar | N clústeres más una capa de enrutamiento de tráfico que mantener sincronizada |

AWS ofrece este patrón exacto como la [guía de arquitectura basada en celdas para Amazon EKS](https://aws.amazon.com/solutions/guidance/cell-based-architecture-for-amazon-eks/). Aquí, un clúster zonal es una «celda», y un grupo de celdas dentro de una Region es una «supercelda». Una capa de enrutamiento delante de las celdas (enrutamiento ponderado de Route 53 más Application Recovery Controller) gestiona la conmutación por error, y un ALB dentro de cada celda distribuye el tráfico en ella. La propiedad clave: el tráfico nunca cruza un límite de celda, por lo que no existe desde el principio ningún coste de transferencia de datos entre AZ.

La arquitectura zonal/blue-green ya se trata en [`ops/02-infrastructure-advanced.md`](02-infrastructure-advanced.md#1-bluegreen-architecture-overview), y la perspectiva del modelo de madurez de la arquitectura Multi-AZ/basada en celdas está en [`eks/10-eks-resiliency.md`](../eks/10-eks-resiliency.md). Esta guía conecta el desplazamiento de tráfico, las actualizaciones y las lecturas de datos en un único ciclo operativo sobre esa base.

***

## Capa de tráfico: Target Group + TargetGroupBinding + desplazamiento de peso

![Arquitectura de celda zonal con desplazamiento de tráfico ponderado](../../assets/ops-zonal-traffic-architecture.png)

El patrón estándar para mover tráfico entre varios clústeres zonales:

1. Cree el NLB/ALB y los Target Groups **fuera** del clúster con IaC como Terraform (para que el balanceador de carga sobreviva incluso si se reemplaza un clúster).
2. Vincule el Service de cada clúster zonal a su Target Group con el CRD `TargetGroupBinding`.
3. Mueva tráfico entre clústeres ajustando el **peso del Target Group** en el balanceador de carga, sin tocar nada dentro de los clústeres.

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: zone-a-tgb
  namespace: production
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:ap-northeast-2:ACCOUNT:targetgroup/zone-a-tg/xxxxxxxxxxxx
  serviceRef:
    name: app-service
    port: 80
  targetType: ip
```

```bash
# Adjust weight between target groups in the ALB listener's forward action
aws elbv2 modify-listener \
  --listener-arn "$LISTENER_ARN" \
  --default-actions '[{
    "Type": "forward",
    "ForwardConfig": {
      "TargetGroups": [
        {"TargetGroupArn": "'"$ZONE_A_TG_ARN"'", "Weight": 20},
        {"TargetGroupArn": "'"$ZONE_C_TG_ARN"'", "Weight": 80}
      ]
    }
  }]'
```

La configuración básica/avanzada/multiport de TargetGroupBinding se trata en [`networking/03-aws-lb-controller.md`](../networking/03-aws-lb-controller.md#targetgroupbinding), y la configuración completa de Terraform para Target Groups ponderados de NLB más enrutamiento ponderado de Route 53 está en [`ops/02-infrastructure-advanced.md`](02-infrastructure-advanced.md#2-nlb-weighted-target-groups).

**Desplazamientos planificados frente a desplazamientos provocados por fallos**: el ajuste de peso sirve para transiciones **planificadas**, como actualizaciones y despliegues. Las situaciones no planificadas, como una interrupción de AZ, se gestionan mediante [ARC (Application Recovery Controller) Zonal Shift](../eks/10-eks-resiliency.md#arc-zonal-shift), que detecta y desplaza automáticamente; los dos mecanismos no compiten, sino que dividen las responsabilidades entre lo planificado y lo reactivo.

> **Actualización de julio de 2026**: el desplazamiento zonal/autodesplazamiento de ARC [ahora también es compatible con clústeres de EKS Auto Mode](https://aws.amazon.com/about-aws/whats-new/2026/07/eks-auto-mode-arc-zonal-shift). En Auto Mode no hay flags que establecer ni versiones de Karpenter que gestionar: basta con habilitar el desplazamiento zonal de ARC en el clúster y, cuando se activa un desplazamiento, el aprovisionamiento de nuevos nodos en la AZ afectada y las interrupciones voluntarias (consolidación/desviación) se detienen automáticamente.

***

## Actualizaciones: por qué la actualización local + reversión nativa se convirtió en la opción predeterminada

En julio de 2026, Amazon EKS [lanzó GA de la reversión nativa de versión de Kubernetes](https://aws.amazon.com/blogs/containers/announcing-amazon-eks-rollback-for-safe-and-reliable-management-of-cluster-upgrades/). Si surge un problema después de una actualización, puede revertir **una versión secundaria a la vez, dentro de 7 días**, y Rollback Readiness Insights verifica automáticamente de antemano la compatibilidad de API, el desfase de versión de kubelet y las versiones de complementos antes de revertir. En los clústeres Auto Mode, la reversión cubre el plano de datos (nodos de trabajo) además del plano de control; pero si actualiza un clúster zonal localmente con grupos de nodos autogestionados (como en la siguiente sección), esa reversión automática del plano de datos no se aplica; solo revierte el plano de control, por lo que los cambios de nodo/AMI/complemento se deben revertir por separado. Ninguno de los dos casos conlleva un cargo adicional.

Antes de que existiera esta característica, la única respuesta a «qué sucede si la nueva versión es defectuosa» era tener una flota de clústeres blue/green preparada que se pudiera validar antes de realizar el cambio. Ahora, los equipos que ya operan una configuración zonal (una sola zona por clúster) tienen una opción más ligera: actualizar cada clúster zonal localmente, una zona a la vez, y utilizar la reversión nativa como red de seguridad.

| Enfoque | Cuándo es la opción adecuada |
|----------|---------------------------|
| **Flota de clústeres blue/green preparada** | Necesita validar la nueva versión con tráfico de producción real en un clúster completamente independiente antes de realizar el cambio, o necesita revertir en bloque cambios de nodo/AMI/complemento (la reversión nativa solo revierte el plano de control) |
| **Actualización zonal local + reversión nativa** | Ya opera clústeres zonales por motivos de disponibilidad (no solo para actualizaciones), desea evitar el coste de ejecutar dos flotas completas de clústeres en todo momento y puede tolerar la ventana de elegibilidad para reversión de ~7 días en lugar de una conmutación por recuperación inmediata a nivel de clúster |
| **Cambio de DNS ponderado de Route 53** | Los clústeres se encuentran en Regions/cuentas completamente diferentes, o necesita reemplazar la propia capa de NLB |

El manual de ejecución (desplazar el peso de NLB -> actualización local -> validar -> restaurar el peso, además de los casos en que la flota blue/green completa sigue siendo la opción adecuada) ya está documentado en la sección [`ops/11-upgrade-operations.md` «Alternative: Zonal In-Place Upgrade with Native Rollback»](11-upgrade-operations.md#alternative-zonal-in-place-upgrade-with-native-rollback), por lo que no se repite aquí. Para conocer las condiciones exactas en las que una reversión es elegible (un clúster creado en la versión de destino no puede revertir, un clúster que ya se actualizó de nuevo no puede hacerlo, etc.), consulte el [procedimiento de reversión de `eks/08-eks-upgrades.md`](../eks/08-eks-upgrades.md#rollback-procedure).

***

## Capa de datos: fijar la ruta de lectura a una zona

El desplazamiento de tráfico y las actualizaciones normalmente ya están implementados para un equipo con una arquitectura zonal. La **ruta de lectura de DB/cache/mensajería** es la parte que se pasa por alto discretamente: un Pod de aplicación puede estar completamente dentro de una AZ, pero el lector de DB, la réplica de caché o el broker de Kafka con el que se comunica se asigna en round-robin entre AZ, lo que genera costes y latencia entre AZ que nadie advierte hasta que llega la factura.

El principio subyacente es el mismo en todas partes: **las escrituras deben ir al líder/primario, por lo que pueden cruzar AZ independientemente de ello; pero las lecturas pueden enrutarse a una réplica en la misma AZ.** Para las cargas de trabajo que son principalmente de lectura (cachés, consultas de búsqueda, consumidores), solo eso elimina una gran parte del coste entre AZ.

![Ruta de lectura de la capa de datos con afinidad de AZ](../../assets/ops-zonal-data-az-affinity.png)

Para hacerlo, el Pod debe saber en qué AZ se encuentra. La Kubernetes Downward API no inserta directamente en un Pod la etiqueta de zona del nodo (`topology.kubernetes.io/zone`), por lo que se necesita una de las siguientes opciones:

- **Consulta de EC2 IMDS**: el Pod o un sidecar llama directamente a `http://169.254.169.254/latest/meta-data/placement/availability-zone`
- **Inyección de etiquetas en tiempo de admisión**: una política mutante como Kyverno copia la etiqueta `topology.k8s.aws/zone-id` del nodo a una anotación del Pod; es el patrón que AWS recomienda en su [guía de reconocimiento de rack de MSK en EKS](https://aws.amazon.com/blogs/big-data/optimize-traffic-costs-of-amazon-msk-consumers-on-amazon-eks-with-rack-awareness/); consulte [`security/01-kyverno-policy-management.md`](../security/01-kyverno-policy-management.md) en este repositorio para saber cómo escribir la política de Kyverno
- **Compatibilidad integrada del operador**: operadores como Strimzi tratan el reconocimiento de rack como una característica de primer nivel, por lo que un init-container lo gestiona sin implementación personalizada

### Kafka: obtención de seguidores con KIP-392

[KIP-392](https://cwiki.apache.org/confluence/display/KAFKA/KIP-392:+Allow+consumers+to+fetch+from+closest+replica) (Kafka 2.4+) permite que un consumidor obtenga datos directamente de una **réplica seguidora en su propio rack (AZ)** en lugar de ir siempre al líder de la partición.

![Diagrama de secuencia que muestra a un consumidor de Kafka en AZ-a obteniendo datos del broker líder en AZ-b, siendo redirigido a una réplica seguidora en la misma AZ mediante una indicación consciente del rack y, a continuación, obteniendo datos localmente para recibirlos sin pagar costes de transferencia entre AZ.](../../assets/diagrams/rendered/en-ops-15-zonal-operations-guide-0.svg)

- **Brokers**: establezca `replica.selector.class=org.apache.kafka.common.replica.RackAwareReplicaSelector` y proporcione a cada broker un `broker.rack` (ID de AZ)
- **Consumidores**: establezca la propiedad de consumidor `client.rack` en el ID de AZ propio del consumidor, obtenido mediante uno de los métodos de reconocimiento de zona anteriores
- **Con Strimzi**, el operador admite esto de forma nativa:

  ```yaml
  apiVersion: kafka.strimzi.io/v1beta2
  kind: Kafka
  spec:
    kafka:
      rack:
        topologyKey: topology.kubernetes.io/zone
      config:
        replica.selector.class: org.apache.kafka.common.replica.RackAwareReplicaSelector
  ```

  Configurar `rack.topologyKey` hace que Strimzi configure automáticamente `broker.rack` e inyecte el rack del cliente mediante un init-container.
- También es importante saberlo: [KIP-881](https://cwiki.apache.org/confluence/display/KAFKA/KIP-881%3A+Rack-aware+Partition+Assignment+for+Kafka+Consumers) va un paso más allá y hace que la propia asignación de particiones de un grupo de consumidores sea consciente del rack.

Para ejecutar Kafka en EKS de manera más amplia, consulte [`data-on-eks/kafka/`](../data-on-eks/kafka/README.md).

### Redis/Valkey (ElastiCache): estrategias de lectura con afinidad de AZ

El cliente [Valkey GLIDE](https://valkey.io/blog/az-affinity-strategy/) admite cuatro estrategias de lectura mediante su configuración `ReadFrom`.

| Estrategia | Comportamiento |
|----------|----------|
| `PRIMARY` | Siempre lee desde el primario (predeterminado, sin reconocimiento de AZ) |
| `PREFER_REPLICA` | Realiza round-robin entre réplicas; recurre a otra opción en caso de fallo |
| `AZ_AFFINITY` | Prefiere una réplica en la misma AZ; recurre a otra opción en caso contrario |
| `AZ_AFFINITY_REPLICAS_AND_PRIMARY` | Primero una réplica en la misma AZ, luego el primario en la misma AZ y, como último recurso, otras AZ |

Para cargas de trabajo con muchas lecturas (>99 % de lecturas), `AZ_AFFINITY_REPLICAS_AND_PRIMARY` es el equilibrio recomendado entre ahorro de costes y disponibilidad.

```python
from glide import GlideClient, GlideClientConfiguration, ReadFrom

config = GlideClientConfiguration(
    addresses=[...],
    read_from=ReadFrom.AZ_AFFINITY_REPLICAS_AND_PRIMARY,
    client_az="ap-northeast-2a",  # the pod's AZ, obtained via one of the methods above
)
client = await GlideClient.create(config)
```

Como ejemplo real, HotelTrader redujo el coste de transferencia de datos entre AZ en un 95 % y mejoró la latencia media en un 49 % después de adoptar el enrutamiento con afinidad de AZ de Valkey GLIDE (sin reconocimiento de AZ, las solicitudes de caché se distribuían aleatoriamente entre AZ, generando costes de transferencia innecesarios). Consulte los detalles en la [publicación del blog de AWS Database](https://aws.amazon.com/blogs/database/how-hoteltrader-cut-inter-az-cost-95-and-latency-by-49-with-valkey-glide-on-amazon-elasticache/).

### Aurora/RDS: los límites del endpoint de lector y soluciones alternativas

El endpoint de lector predeterminado de Aurora es **DNS round-robin sin reconocimiento de AZ**: una réplica en la misma AZ no recibe prioridad. No es tanto una característica ausente como una restricción actual y real; la incidencia abierta [aws-advanced-jdbc-wrapper#1139](https://github.com/aws/aws-advanced-jdbc-wrapper/issues/1139) solicita la propia afinidad de AZ.

Existen dos soluciones alternativas:

1. **Endpoints personalizados por AZ**: agrupe las instancias de réplica en una AZ determinada en un endpoint personalizado y dirija hacia él el tráfico de aplicación de esa AZ.

   ```bash
   aws rds create-db-cluster-endpoint \
     --db-cluster-identifier my-aurora-cluster \
     --db-cluster-endpoint-identifier reader-az-a \
     --endpoint-type READER \
     --static-members db-instance-az-a-1 db-instance-az-a-2
   ```

2. **AWS Advanced JDBC Wrapper**: proporciona división de lectura/escritura y una estrategia de selección de lector `fastestResponse`. No es una afinidad de AZ real, pero favorece el lector que responde más rápido, que normalmente es el de la misma AZ.

Si necesita una afinidad de AZ auténtica, la opción 1 (endpoints personalizados) es la única ruta fiable hasta que se resuelva la incidencia abierta anterior.

### Opciones complementarias de Kubernetes en la capa de Service

Para fijar el propio tráfico de Service a una AZ en la capa de aplicación, consulte [Topology Aware Routing (GA)](../eks/12-kubernetes-version-roadmap.md); si ejecuta un service mesh, consulte [Istio Zone-Aware Routing](../service-mesh/istio/resilience/03-zone-aware-routing.md). Combinada con las estrategias de la capa de datos anteriores, toda la ruta de lectura, desde la aplicación hasta la caché/DB/mensajería, permanece dentro de la AZ.

***

## Resumen de la combinación recomendada

| Capa | Recomendado a partir de 2026 | Alternativa/plan de respaldo |
|-------|--------------------------|------------------------|
| Arquitectura | Clústeres zonales (de una sola zona) + arquitectura basada en celdas | Un único clúster Multi-AZ (equipos de operaciones más pequeños) |
| Desplazamiento de tráfico | Target Group + TargetGroupBinding + ajuste de peso | DNS ponderado de Route 53 (Region/cuenta diferente) |
| Respuesta ante fallos | ARC Zonal Shift (automático) | Ajuste manual de peso |
| Actualizaciones | Actualización zonal local + reversión nativa de EKS (7 días) | Flota de clústeres blue/green preparada (cuando se requiere validación previa completa) |
| Lecturas de Kafka | KIP-392 (`client.rack` + `RackAwareReplicaSelector`) o `rack.topologyKey` de Strimzi | Permitir respaldo en toda la Region (automático si no hay un seguidor local) |
| Lecturas de caché | Valkey GLIDE `AZ_AFFINITY_REPLICAS_AND_PRIMARY` | `PREFER_REPLICA` (cuando no se necesita reconocimiento de AZ) |
| Lecturas de DB | Endpoints personalizados de Aurora por AZ | AWS Advanced JDBC Wrapper `fastestResponse` |

El orden de implementación recomendado es **capa de desplazamiento de tráfico -> actualización/reversión -> capa de lectura de datos**, ya que es difícil medir el beneficio (especialmente el ahorro de costes) de las capas posteriores sin que las anteriores estén implementadas.

***

< [Anterior: Pipelines de Tekton](14-tekton-pipelines.md) | [Tabla de contenidos](./README.md) | [Siguiente: Manual de solución de problemas](16-troubleshooting-playbook.md) >
