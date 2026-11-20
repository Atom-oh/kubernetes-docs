# Guía de operaciones de EKS Auto Mode

> **Versiones compatibles**: EKS Auto Mode GA; versión de referencia de los ejemplos: EKS 1.36  
> **Última actualización**: 16 de noviembre de 2026

Amazon EKS Auto Mode automatiza la administración de nodos de Kubernetes, incluido el aprovisionamiento y la optimización según los requisitos de las cargas de trabajo. Esta guía abarca los conceptos, la configuración y las operaciones de Auto Mode. AWS administra la infraestructura de Auto Mode; usted sigue siendo responsable de la disponibilidad de las aplicaciones, las solicitudes de recursos, la seguridad, la supervisión y la configuración del clúster y la VPC. Valide los ejemplos en su entorno antes de usarlos en producción.

### Actualización de noviembre de 2026: compatibilidad con grupos de seguridad para Pods

Desde el 11 de noviembre de 2026, EKS Auto Mode admite grupos de seguridad para Pods, lo que permite aplicar reglas específicas de grupos de seguridad de EC2 a Pods individuales. Las distintas cargas de trabajo del mismo nodo pueden tener grupos de seguridad diferentes, lo que proporciona segmentación de red a los Pods sin necesidad de crear grupos de nodos separados para cada aplicación. Consulte el [anuncio](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-auto-mode-security-groups-for-pods/) para obtener más información.

### Actualización de noviembre de 2026: compatibilidad con la asignación dinámica de recursos (DRA)

El 9 de noviembre de 2026, AWS anunció la compatibilidad con la asignación dinámica de recursos (DRA) de Kubernetes para GPU NVIDIA y dispositivos de red Elastic Fabric Adapter (EFA) con EKS Auto Mode y Karpenter. Las cargas de trabajo declaran los atributos de dispositivo que necesitan mediante DRA y pueden compartir dispositivos GPU entre Pods. Karpenter admite DRA en todas las versiones de Kubernetes; EKS Auto Mode lo admite en Kubernetes 1.36 y versiones posteriores, en todas las regiones de AWS excepto AWS GovCloud (EE. UU.) y las regiones de China. Consulte el [anuncio](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-auto-mode-karpenter-dra/) para obtener más información.

### Actualización de octubre de 2026: valores predeterminados de EKS 1.37

EKS 1.37 estuvo disponible el 1 de octubre de 2026. Un NodePool personalizado recién creado que no especifique una política de consolidación tendrá `Balanced` como valor predeterminado; los grupos integrados `general-purpose` y `system` también usan `Balanced`, y sus políticas no se pueden cambiar. Especifique `WhenEmptyOrUnderutilized` en un grupo personalizado cuando ese sea el comportamiento deseado. No todos los ejemplos de NodePool de esta guía especifican el campo, por lo que, en EKS 1.37, esos ejemplos usarán `Balanced` al crearse. Consulte la sección de Kubernetes 1.37 de las [notas de la versión de soporte estándar de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html).

### Actualización de julio de 2026: compatibilidad con EFA y grupos de ubicación

El 22 de julio de 2026, AWS anunció que los grupos de nodos de EKS Auto Mode y de Karpenter de código abierto admiten la configuración de dispositivos de red Elastic Fabric Adapter (EFA) y los grupos de ubicación de EC2.

En las instancias compatibles con EFA, las interfaces de red se pueden configurar como interfaces exclusivamente EFA o como ENI estándar. Las interfaces exclusivamente EFA no consumen direcciones IP de la VPC y, aun así, ofrecen todo el ancho de banda de interconexión. La configuración del grupo de nodos también puede especificar estrategias de ubicación de tipo clúster, dispersión o partición. Estas opciones están destinadas a cargas de trabajo de entrenamiento e inferencia distribuidos que necesitan un alto rendimiento o aislamiento de errores. Consulte el [anuncio](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-efa-placement-groups/) para obtener más información.

### Actualización de julio de 2026: compatibilidad con el desplazamiento zonal de ARC

Desde el 10 de julio de 2026, los clústeres de EKS Auto Mode admiten el desplazamiento zonal y el desplazamiento zonal automático de Amazon Application Recovery Controller (ARC). Habilite el desplazamiento zonal de ARC en el clúster; Auto Mode no requiere ninguna marca adicional ni administración de la versión de Karpenter.

Durante un desplazamiento zonal, Auto Mode deja de aprovisionar capacidad en la AZ afectada y detiene las interrupciones voluntarias, como la consolidación y la detección de desviaciones, para los nodos de esa zona. También bloquea las interrupciones voluntarias en las AZ en buen estado cuando la programación de reemplazos dependería de la AZ afectada. Configure el desplazamiento zonal automático de ARC por separado, después de registrar el clúster.

El desplazamiento zonal no hace que los volúmenes zonales ni las cargas de trabajo estrictamente vinculadas a una AZ sean portátiles. ARC no aplica ningún cargo por el desplazamiento zonal; siguen aplicándose los cargos normales de infraestructura y por la capacidad de reemplazo. Consulte el [anuncio](https://aws.amazon.com/about-aws/whats-new/2026/07/eks-auto-mode-arc-zonal-shift) y la [documentación sobre el desplazamiento zonal de ARC](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift-enable.html) para obtener más información.

## Índice

1. [Primeros pasos con Auto Mode](./01-getting-started.md) - Creación del clúster y habilitación de Auto Mode
2. [Configuración y optimización de NodePool](./02-nodepool-configuration.md) - NodePool predeterminados y personalizados
3. [Comprender el comportamiento del escalado](./03-scaling-behavior.md) - Aprovisionamiento, consolidación y detección de desviaciones
4. [Estrategias para utilizar instancias Spot](./04-spot-strategies.md) - Capacidad mixta y gestión de interrupciones
5. [Operaciones y administración](./05-operations.md) - Presupuestos de interrupciones, reemplazo gradual y supervisión
6. [Administración y optimización de costos](./06-cost-management.md) - Análisis de costos, ahorro con Spot y ajuste del tamaño
7. [Administración del ciclo de vida de los nodos](./07-node-lifecycle.md) - Expiración, administración de AMI y políticas de actualización
8. [Optimización específica para cada carga de trabajo](./08-workload-optimization.md) - Cargas de trabajo web, por lotes, de GPU e IA/ML
9. [Migración desde grupos de nodos administrados](./09-migration-guide.md) - Pasos de migración y coexistencia

---

## Introducción a EKS Auto Mode

### ¿Qué es Auto Mode?

EKS Auto Mode es una solución de administración de nodos totalmente automatizada y administrada por AWS. Internamente, se basa en Karpenter; AWS opera los controladores de infraestructura administrada. En lugar de instalar un controlador de Karpenter independiente para Auto Mode, los usuarios configuran las restricciones de las cargas de trabajo, los NodePool/NodeClass personalizados y los presupuestos de interrupciones.

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

| Característica | Grupos de nodos administrados | Fargate | Auto Mode |
|---------|---------------------|---------|-----------|
| Administración de nodos | AWS administra los grupos de nodos; usted configura la capacidad y las actualizaciones | AWS administra la infraestructura de cada Pod | AWS administra los nodos lanzados y los controladores de infraestructura |
| Escalado | Cluster Autoscaler, si está instalado, o escalado explícito del grupo | Aprovisionamiento por Pod con perfiles de Fargate | Aprovisionamiento basado en Karpenter para Pods que no se pueden programar |
| Tiempo de aprovisionamiento | Depende de la capacidad, el arranque y la carga de trabajo | Depende de la capacidad, las imágenes y la carga de trabajo; no es instantáneo | Depende de la capacidad, el arranque, las imágenes y las restricciones; no hay una garantía de tiempo fijo |
| Selección de instancias | Tipos de instancia configurados | Tamaños de cómputo administrados | Selección según las restricciones de NodePool y de la carga de trabajo |
| Spot | Compatible con grupos de nodos administrados | No compatible | Compatible cuando NodePool lo permite |
| Cargas de trabajo de GPU | Compatibles en los nodos adecuados | No compatibles | Compatibles en instancias aceleradas compatibles; siguen aplicándose los requisitos de la carga de trabajo y del entorno de ejecución |
| DaemonSets | Compatibles | No compatibles | Compatibles, dentro de las restricciones de los nodos administrados |
| Control de costos | Solicitudes, selección de instancias y políticas del escalador automático | Tamaño de recursos y réplicas de los Pods | Solicitudes, capacidad permitida y políticas de consolidación; no se garantizan ahorros |
| Personalización del host | Opciones de AMI/plantillas de lanzamiento | Sin personalización del host | Variantes de Bottlerocket administradas por AWS; ajustes de NodeClass compatibles |

### Arquitectura interna y principios operativos

AWS opera el controlador basado en Karpenter, que se ejecuta fuera de los nodos de trabajo. Los diagramas son conceptuales: el programador identifica los Pods que no se pueden programar y, posteriormente, los vincula a los nodos; el servidor de API almacena los objetos. Que un Pod esté en estado Pending no demuestra por sí solo que agregar un nodo resolverá el problema.

![Diagrama de secuencia del aprovisionamiento de nodos de EKS Auto Mode: un Pod pendiente activa el controlador de Auto Mode, que busca un NodePool compatible y elige un tipo de instancia, lanza una instancia EC2, registra el nuevo nodo y programa el Pod hasta que se ejecuta.](../.gitbook/assets/en-eks-auto-mode-readme-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-auto-mode-readme-0.html)

### Regiones y limitaciones compatibles

#### Regiones y versiones compatibles

Las [preguntas frecuentes de EKS](https://aws.amazon.com/eks/faqs/) enumeran Auto Mode en las regiones de EKS, incluidas las de GovCloud (EE. UU.), excepto las regiones de China. Compruebe por separado la disponibilidad regional de instancias y funciones. La lista breve de regiones anterior no era exhaustiva.

El límite de versión original `1.29+` de las preguntas frecuentes no significa que todavía se puedan crear todas esas versiones ni que todas sigan en soporte estándar. Al 12 de octubre de 2026, EKS 1.34–1.37 están en soporte estándar; los ejemplos conservan la versión de referencia 1.36 que se revisó. Consulte el [calendario actual de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) para conocer las fechas del ciclo de vida y los cargos de soporte extendido.

#### Restricciones que se deben comprobar

| Elemento | Recomendación |
|------|----------|
| Capacidad y escalado | Compruebe las cuotas aplicadas de EKS/EC2, la capacidad de direcciones IP de las subredes y las restricciones de las cargas de trabajo; valide en su entorno la escala prevista |
| Límites de NodePool | Los límites de recursos definidos por el usuario son distintos de las cuotas de la cuenta y del servicio de AWS; valide la escala y el margen disponible para reemplazos |
| Sistema operativo | AWS selecciona su variante de Bottlerocket administrada; AL2023 o AMI personalizadas arbitrarias no son opciones de AMI para Auto Mode |
| Windows | Auto Mode no proporciona nodos de Windows; cuando sea necesario, utilice un grupo de nodos independiente compatible |
| DNS y almacenamiento | Los nodos de Auto Mode proporcionan CoreDNS local; los clústeres mixtos conservan CoreDNS para los demás nodos. El cifrado de discos de nodos administrados no demuestra que todos los PVC dinámicos estén cifrados; configure StorageClass explícitamente |

Use [Service Quotas](https://docs.aws.amazon.com/eks/latest/userguide/service-quotas.html) y la [referencia de NodeClass](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html) para verificar las restricciones pertinentes. Durante esta auditoría no se consultaron las cuotas reales de la cuenta ni la capacidad de las instancias.

---

## Próximos pasos

Después de configurar correctamente EKS Auto Mode, recomendamos aprender sobre los siguientes temas:

1. **[Optimización de costos de EKS](../eks/07-eks-cost-optimization.md)**: Spot, Savings Plans y optimización de recursos
2. **[Supervisión y registro de EKS](../eks/06-eks-monitoring-logging.md)**: CloudWatch, Prometheus y Grafana
3. **[Seguridad de EKS](../eks/05-eks-security.md)**: IAM, políticas de red y seguridad de los Pods
4. **[Análisis detallado de Karpenter](../autoscaling/02-karpenter.md)**: Instalación directa de Karpenter y funciones avanzadas

## Cuestionario relacionado

Para poner a prueba lo aprendido, pruebe el [cuestionario de EKS Auto Mode](../quizzes/eks-auto-mode/01-getting-started-quiz.md).

---

## Referencias

- [Documentación oficial de AWS EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Documentación oficial de Karpenter](https://karpenter.sh/)
- [Guía de prácticas recomendadas de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/)
- [Guía de optimización de costos de AWS](https://aws.amazon.com/pricing/cost-optimization/)
- [Nuevas funciones de EKS Auto Mode para mejorar la seguridad, el control de red y el rendimiento (AWS Containers Blog, 2025-10-16)](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)
- [Migrar de Karpenter autoadministrado a EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)

- [Arquitectura y responsabilidades de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Restricciones de EKS Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)

---

< [Volver a los temas de EKS](../README.md) | [Siguiente: Primeros pasos](./01-getting-started.md) >
