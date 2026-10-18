# Guía de operaciones de EKS Auto Mode

> **Versiones compatibles**: EKS Auto Mode GA; línea base del ejemplo: EKS 1.36
> **Última actualización**: 12 de octubre de 2026

Amazon EKS Auto Mode automatiza la administración de los nodos de Kubernetes, incluido el aprovisionamiento y la optimización según los requisitos de las cargas de trabajo. Esta guía abarca los conceptos, la configuración y las operaciones de Auto Mode. AWS administra la infraestructura de Auto Mode; usted sigue siendo responsable de la disponibilidad de las aplicaciones, las solicitudes de recursos, la seguridad, la supervisión y la configuración del clúster y la VPC. Valide los ejemplos en su entorno antes de usarlos en producción.

### Actualización de octubre de 2026: valores predeterminados de EKS 1.37

EKS 1.37 estuvo disponible el 1 de octubre de 2026. Si se crea un NodePool personalizado sin especificar una política de consolidación, el valor predeterminado es `Balanced`; los NodePools integrados `general-purpose` y `system` también usan `Balanced`, y sus políticas no se pueden cambiar. En un NodePool personalizado, establezca explícitamente `WhenEmptyOrUnderutilized` cuando ese sea el comportamiento deseado. No todos los ejemplos de NodePool de esta guía especifican el campo, por lo que, al crearlos en EKS 1.37, esos ejemplos usan `Balanced`. Consulte la sección de Kubernetes 1.37 de las [notas de versiones de soporte estándar de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html).

### Actualización de julio de 2026: compatibilidad con EFA y grupos de ubicación

El 22 de julio de 2026, AWS anunció que los grupos de nodos de EKS Auto Mode y Karpenter de código abierto admiten la configuración de dispositivos de red Elastic Fabric Adapter (EFA) y los grupos de ubicación de EC2.

En instancias compatibles con EFA, las interfaces de red se pueden configurar como interfaces solo EFA o como ENI estándar. Las interfaces solo EFA no consumen direcciones IP de la VPC y, aun así, ofrecen todo el ancho de banda de interconexión. La configuración del grupo de nodos también puede especificar estrategias de ubicación `cluster`, `spread` o `partition`. Estas opciones están dirigidas a cargas de trabajo de entrenamiento e inferencia distribuidas que requieren un alto rendimiento o aislamiento ante fallos. Consulte el [anuncio](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-efa-placement-groups/) para obtener más información.

### Actualización de julio de 2026: compatibilidad con ARC Zonal Shift

Desde el 10 de julio de 2026, los clústeres de EKS Auto Mode admiten Zonal Shift y autoshift de Amazon Application Recovery Controller (ARC). Habilite ARC Zonal Shift en el clúster; Auto Mode no necesita ningún indicador adicional ni que usted administre versiones de Karpenter.

Durante un Zonal Shift, Auto Mode deja de aprovisionar capacidad en la AZ afectada y detiene las interrupciones voluntarias, como la consolidación y la corrección de drift, para los nodos de esa AZ. También bloquea las interrupciones voluntarias en las AZ en buen estado cuando la programación de reemplazos dependería de la AZ afectada. Configure ARC zonal autoshift por separado, después de registrar el clúster.

Zonal Shift no permite trasladar volúmenes zonales ni cargas de trabajo estrictamente vinculadas a una AZ. ARC no añade cargos por Zonal Shift; la capacidad de reemplazo y los cargos normales de infraestructura siguen aplicándose. Consulte el [anuncio](https://aws.amazon.com/about-aws/whats-new/2026/07/eks-auto-mode-arc-zonal-shift) y la [documentación de ARC Zonal Shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift-enable.html) para obtener más información.

## Índice

1. [Introducción a Auto Mode](./01-getting-started.md) - Creación del clúster y habilitación de Auto Mode
2. [Configuración y optimización de NodePool](./02-nodepool-configuration.md) - NodePools predeterminados y personalizados
3. [Comprender el comportamiento de escalado](./03-scaling-behavior.md) - Aprovisionamiento, consolidación y detección de drift
4. [Estrategias de uso de instancias Spot](./04-spot-strategies.md) - Capacidad mixta y gestión de interrupciones
5. [Operaciones y administración](./05-operations.md) - Presupuestos de interrupción, reemplazo gradual y supervisión
6. [Administración y optimización de costos](./06-cost-management.md) - Análisis de costos, ahorros con Spot y dimensionamiento adecuado
7. [Administración del ciclo de vida de nodos](./07-node-lifecycle.md) - Expiración, administración de AMI y políticas de actualización
8. [Optimización específica para cargas de trabajo](./08-workload-optimization.md) - Cargas de trabajo web, por lotes, GPU e IA/ML
9. [Migración desde Managed Node Groups](./09-migration-guide.md) - Pasos de migración y coexistencia

---

## Introducción a EKS Auto Mode

### ¿Qué es Auto Mode?

EKS Auto Mode es una solución de administración de nodos totalmente automatizada y administrada por AWS. Internamente se basa en Karpenter; AWS opera los controladores de infraestructura administrados. Los usuarios configuran las restricciones de las cargas de trabajo, los NodePools/NodeClasses personalizados y los presupuestos de interrupción, en lugar de instalar un controlador de Karpenter independiente para Auto Mode.

```
+-----------------------------------------------------------------------------+
|                           EKS Auto Mode Architecture                         |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +---------------------------------------------------------------------+    |
|  |                    EKS Control Plane (AWS Managed)                   |    |
|  |  +------------+  +------------+  +------------+  +------------+    |    |
|  |  | API Server |  |   etcd     |  | Controller |  |  Karpenter |    |    |
|  |  |            |  |            |  |  Manager   |  | Controller |    |    |
|  |  +------------+  +------------+  +------------+  +------------+    |    |
|  +---------------------------------------------------------------------+    |
|                                    |                                         |
|                                    v                                         |
|  +---------------------------------------------------------------------+    |
|  |                        NodePool Resources                            |    |
|  |  +------------------+  +------------------+  +------------------+  |    |
|  |  |  general-purpose |  |      system      |  |   custom-pool    |  |    |
|  |  | (Default Provided)|  | (Default Provided)|  |  (User Defined)  |  |    |
|  |  +------------------+  +------------------+  +------------------+  |    |
|  +---------------------------------------------------------------------+    |
|                                    |                                         |
|                                    v                                         |
|  +---------------------------------------------------------------------+    |
|  |                     EC2 Instances (Auto Managed)                     |    |
|  |  +--------------+  +--------------+  +--------------+              |    |
|  |  |   m6i.2xl    |  |   c7g.xl     |  |   r6i.4xl    |   ...        |    |
|  |  |  (On-Demand) |  |   (Spot)     |  |  (On-Demand) |              |    |
|  |  +--------------+  +--------------+  +--------------+              |    |
|  +---------------------------------------------------------------------+    |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### Comparación con los métodos de administración existentes

| Característica | Managed Node Groups | Fargate | Auto Mode |
|---------|---------------------|---------|-----------|
| Administración de nodos | AWS administra los grupos de nodos; usted configura la capacidad y las actualizaciones | AWS administra la infraestructura de cada Pod | AWS administra los nodos lanzados y los controladores de infraestructura |
| Escalado | Cluster Autoscaler, si está instalado, o escalado explícito de los grupos | Aprovisionamiento por Pod con perfiles de Fargate | Aprovisionamiento basado en Karpenter para Pods que no se pueden programar |
| Tiempo de aprovisionamiento | Depende de la capacidad, el bootstrap y la carga de trabajo | Depende de la capacidad, las imágenes y la carga de trabajo; no es instantáneo | Depende de la capacidad, el bootstrap, las imágenes y las restricciones; no hay garantía de tiempo fijo |
| Selección de instancias | Tipos de instancia configurados | Tamaños de cómputo administrados | Selección conforme a las restricciones del NodePool y la carga de trabajo |
| Spot | Compatible con grupos de nodos administrados | No compatible con EKS Fargate | Compatible cuando un NodePool lo permite |
| Cargas de trabajo con GPU | Compatibles en nodos adecuados | No compatibles | Compatibles en instancias aceleradas adecuadas; deben cumplirse los requisitos de la carga de trabajo y el runtime |
| DaemonSets | Compatibles | No compatibles | Compatibles dentro de las restricciones de nodos administrados |
| Control de costos | Solicitudes, selección de instancias y políticas del autoscaler | Tamaño de recursos y réplicas de los Pods | Solicitudes, capacidad permitida y políticas de consolidación; no se garantizan ahorros |
| Personalización del host | Opciones de AMI/plantilla de lanzamiento | Sin personalización del host | Variantes de Bottlerocket administradas por AWS; ajustes compatibles de NodeClass |

### Arquitectura interna y principios operativos

AWS opera el controlador basado en Karpenter fuera de los nodos de trabajo. Los diagramas son conceptuales: el planificador identifica los Pods que no se pueden programar y luego los vincula a nodos; el servidor de API almacena los objetos. Que un Pod esté en estado Pending, por sí solo, no demuestra que añadir un nodo vaya a resolver el problema.

![Diagrama de secuencia del aprovisionamiento de nodos de EKS Auto Mode: un Pod pendiente activa el controlador de Auto Mode, que busca un NodePool y selecciona un tipo de instancia, lanza una instancia EC2, registra el nodo nuevo y programa el Pod hasta que queda en ejecución.](../.gitbook/assets/en-eks-auto-mode-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-auto-mode-readme-0.html)

### Regiones compatibles y limitaciones

#### Regiones y versiones compatibles

Las [preguntas frecuentes de EKS](https://aws.amazon.com/eks/faqs/) incluyen Auto Mode en las regiones de EKS, incluida GovCloud (EE. UU.), con excepción de las regiones de China. Compruebe por separado la disponibilidad regional de instancias y características. La lista breve de regiones publicada anteriormente no era exhaustiva.

La versión mínima `1.29+` indicada en las preguntas frecuentes para esta función no significa que todavía se puedan crear clústeres con todas esas versiones ni que todas sigan en soporte estándar. Al 12 de octubre de 2026, las versiones de EKS 1.34–1.37 están en soporte estándar; los ejemplos mantienen la línea base revisada de 1.36. Consulte el [calendario actual de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) para conocer las fechas del ciclo de vida y los cargos de soporte extendido.

#### Restricciones que debe comprobar

| Elemento | Orientación |
|------|----------|
| Capacidad y escala | Compruebe las cuotas aplicadas de EKS/EC2, la capacidad de direcciones IP de las subredes y las restricciones de las cargas de trabajo; valide la escala prevista en su entorno |
| Límites de NodePool | Los límites de recursos definidos por el usuario difieren de las cuotas de cuenta/servicio de AWS; valide la escala y el margen para reemplazos |
| Sistema operativo | AWS elige su variante administrada de Bottlerocket; AL2023 o AMI personalizadas arbitrarias no son opciones de AMI de Auto Mode |
| Windows | Auto Mode no proporciona nodos Windows; si los necesita, use un grupo de nodos independiente y compatible |
| DNS y almacenamiento | Los nodos de Auto Mode proporcionan CoreDNS local; los clústeres mixtos conservan CoreDNS para los demás nodos. El cifrado administrado del disco de los nodos no garantiza el cifrado de cada PVC dinámico; establezca explícitamente la StorageClass |

Use [Service Quotas](https://docs.aws.amazon.com/eks/latest/userguide/service-quotas.html) y la [referencia de NodeClass](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html) para verificar las restricciones pertinentes. Durante esta auditoría no se consultaron las cuotas reales de la cuenta ni la capacidad de las instancias.

---

## Próximos pasos

Después de configurar correctamente EKS Auto Mode, recomendamos aprender sobre los siguientes temas:

1. **[Optimización de costos de EKS](../eks/07-eks-cost-optimization.md)**: Spot, Savings Plans y optimización de recursos
2. **[Monitoreo y registro de EKS](../eks/06-eks-monitoring-logging.md)**: CloudWatch, Prometheus y Grafana
3. **[Seguridad de EKS](../eks/05-eks-security.md)**: IAM, políticas de red y seguridad de Pods
4. **[Profundización en Karpenter](../autoscaling/02-karpenter.md)**: Instalación directa de Karpenter y características avanzadas

## Cuestionario relacionado

Para poner a prueba lo aprendido, intente el [cuestionario de EKS Auto Mode](../quizzes/eks-auto-mode/01-getting-started-quiz.md).

---

## Referencias

- [Documentación oficial de EKS Auto Mode de AWS](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Documentación oficial de Karpenter](https://karpenter.sh/)
- [Guía de prácticas recomendadas de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/)
- [Guía de optimización de costos de AWS](https://aws.amazon.com/pricing/cost-optimization/)
- [Nuevas características de EKS Auto Mode para mejorar la seguridad, el control de red y el rendimiento (blog de AWS Containers, 2025-10-16)](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)
- [Migrar de Karpenter autoadministrado a EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)

- [Arquitectura y responsabilidades de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Restricciones de EKS Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)

---

< [Volver a los temas de EKS](../README.md) | [Siguiente: Primeros pasos](./01-getting-started.md) >
