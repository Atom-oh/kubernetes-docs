# Estructura de cuentas y límites de IAM

> **Última actualización**: 13 de septiembre de 2026

## 1. Partición de cuentas: ¿cuál debería ser el criterio?

Los criterios más habituales para dividir cuentas son el equipo, la marca, el dominio y el entorno (producción/no producción). Sin embargo, **una cuenta debe evaluarse según los requisitos de seguridad, las cuotas de servicio, el costo y la titularidad, y el ciclo de vida que comparten las cargas de trabajo relacionadas, no según el nombre del equipo.** Los equipos cambian con frecuencia durante las reorganizaciones, mientras que los dominios (capacidades empresariales) son candidatos relativamente estables para constituir cuentas.

| Opción | Configuración | Ventajas | Desventajas |
|---|---|---|---|
| Dominio × entorno | Una cuenta de producción/no producción independiente para cada dominio | Facilita asociar costos, cuotas, permisos y titularidad a un dominio | Incluso los dominios pequeños soportan costos fijos, y una reorganización del dominio se convierte directamente en una migración |
| Marca × entorno | Cuentas por marca y entorno, con varios dominios dentro de cada una | Permite administrar los costos, las cuotas, los permisos, la separación y las transferencias a nivel de marca mediante límites de cuenta | La titularidad de las funciones compartidas entre marcas se vuelve ambigua. Los cambios en el ciclo de vida de una marca activan directamente una reorganización de cuentas |
| Un número reducido de cuentas centrales de cargas de trabajo | Cargas de trabajo de varios dominios/equipos ubicadas en unas pocas cuentas compartidas | Operaciones iniciales sencillas y fácil incorporación de cargas pequeñas | Aumentan las cuotas, los permisos y el radio de impacto, y luego resulta difícil separarlas |
| **Cartera híbrida** | Las cargas pequeñas se alojan en cuentas compartidas; las cargas con límites estrictos de dominio, regulación o cuota obtienen cuentas dedicadas | Combina cuentas compartidas, por dominio y dedicadas según los requisitos | Si los criterios de evaluación son débiles, las excepciones aumentan rápidamente |

En la práctica, el patrón habitual es empezar con una cartera híbrida y decidir cada vez entre una cuenta compartida o dedicada mediante una matriz de decisión reproducible (consulte el [Marco de decisión](./06-decision-framework-and-poc.md) para saber cómo diseñarla).

Trate la marca como metadato si solo se necesita separar costos y promuévala a eje de cuenta únicamente cuando exista un límite sólido: regulación, cuota independiente, permisos o posibilidad de escisión. Una carga que agrega datos de varios dominios y los ofrece mediante una API puede ser candidata a su propia cuenta de cargas de trabajo si tiene un SLO, cuota, acceso a datos y ciclo de vida independientes. **Una cuenta independiente no implica necesariamente un clúster EKS independiente.**

> **Planificación de una escisión**: se admite compartir subredes dentro de una misma organización. Prepare una migración de red independiente antes de salir. Los recursos existentes pueden seguir funcionando después de dejar de compartir, pero la creación de nuevos recursos y el reemplazo o escalado de servicios administrados pueden verse afectados. Dejar de compartir no elimina ni detiene de inmediato todos los recursos.

## 2. Relación entre las cuentas y el entorno de ejecución de EKS

Una vez decidida la partición de cuentas, hay que decidir en qué cuenta se ejecutará el clúster EKS que aloja las cargas de trabajo de Kubernetes.

| Opción | Configuración | Ventajas | Desventajas |
|---|---|---|---|
| EKS dedicado por cuenta de cargas de trabajo | Cada cuenta de cargas de trabajo es propietaria de su propio clúster EKS | La responsabilidad sobre la cuenta y el entorno de ejecución queda alineada, al igual que el radio de impacto | Incluso las cargas pequeñas necesitan un clúster, lo que aumenta el número de clústeres que hay que administrar y la capacidad ociosa |
| **Cuenta de cargas de trabajo + cuenta de clúster compartido** | Los recursos como Lambda/SQS/DB residen en cada cuenta de cargas de trabajo, mientras que las cargas de Kubernetes se ejecutan en EKS compartido en una cuenta de clúster independiente | Los límites de cuenta y el número de clústeres EKS que se deben administrar se pueden decidir por separado | La identidad entre cuentas, la red y la titularidad del clúster se vuelven más complejas |

En el segundo patrón, distinga los roles IAM de la cuenta del clúster del acceso a los datos de otra cuenta. Con una VPC compartida, la cuenta que crea EKS es la **cuenta del clúster**, que puede ser distinta de la cuenta de cargas de trabajo que solo es propietaria de una base de datos o una cola. Elija según corresponda el encadenamiento de roles de destino con Pod Identity, las políticas de recursos del servicio o IRSA.

### Cuotas relacionadas con EKS: margen disponible y límites que realmente se alcanzan

| Cuota | Valor predeterminado | Ajustable |
|---|---|---|
| Clústeres / región | 100 | Sí |
| Grupos de nodos administrados / clúster | 30 | Sí |
| Nodos / grupo de nodos | 450 | Sí |
| Grupos de seguridad del plano de control / clúster | 4 | No |
| CIDR con permiso para acceder al endpoint público / clúster | 40 | No |
| **Entradas de acceso / clúster** | **3,000** | **No** |

La mayoría de las cuotas de EKS ofrece margen, pero el **límite no ajustable de 3,000 entradas de acceso por clúster** es un techo real al que se llega rápidamente si se crean roles individuales de CI/CD por carga de trabajo × entorno para decenas de equipos. Recomendamos consolidar las rutas de acceso en Permission Sets o roles a nivel de equipo, y agrupar las entradas de acceso por tipo de principal.

Treinta grupos de nodos administrados es un valor predeterminado ajustable, no un límite fijo de 30 inquilinos. Los NodePools de Karpenter y las taints/tolerations controlan la ubicación, pero por sí solos no constituyen límites de seguridad sólidos. Evalúe conjuntamente las cuotas aplicadas, los permisos, los kernels compartidos y los privilegios de los agentes de nodo.

## 3. Acceso humano a AWS (IAM para la fuerza laboral)

| Opción | Configuración | Ventajas | Desventajas |
|---|---|---|---|
| **Identity Center + RBAC** | Los usuarios inician sesión mediante Identity Center y acceden a las cuentas con Permission Sets basados en roles | Credenciales temporales, revocación y auditoría centralizadas | Los Permission Sets pueden multiplicarse entre las combinaciones de equipo × dominio × entorno |
| RBAC + ABAC limitado | Restringir aún más el alcance de los recursos mediante etiquetas dentro del límite de permisos por rol de RBAC | Combina un límite de permisos con escalabilidad | Requiere probar RBAC y ABAC, y controlar quién puede asignar etiquetas |
| Centrado en ABAC | Conceder permisos principalmente cuando coinciden las etiquetas del usuario y del recurso | Reduce la duplicación de políticas a medida que crecen las cuentas y las cargas de trabajo | Si la autoridad sobre las etiquetas es débil, aumentan la expansión de permisos y la dificultad de depuración |

Recomendamos excluir por completo a los usuarios de IAM por cuenta del conjunto general de opciones. Resérvelos únicamente como excepción para el acceso de emergencia cuando Identity Center no esté disponible, y documente de forma explícita el propósito, el propietario, las condiciones de uso, el almacenamiento de credenciales, las revisiones periódicas y las condiciones de terminación.

### Los límites reales de IAM Identity Center

| Cuota | Valor predeterminado | Ajustable |
|---|---|---|
| Total de permission sets | 3,500 | Sí |
| Permission sets aprovisionados por cuenta | 500 | Sí |
| Políticas administradas por permission set | 25; se debe aumentar según sea necesario el valor predeterminado independiente de 10 para roles de IAM | Límite de permission sets: no |
| Política integrada por permission set | 32,768 bytes; 10,240 bytes sin espacios en blanco | No |
| **Grupos asignados a un permission set en una cuenta** | **100** | **No** |
| Cuentas configurables | 7,000 | Sí |
| Límite de solicitudes de la API de Identity Center | Colectivo de 20 TPS; los aumentos de lectura se solicitan al soporte | Consulte los límites adicionales específicos de cada API |

El límite de 100 grupos se aplica a una **combinación específica de permission set y cuenta**, no a todos los grupos de una cuenta. No sume los grupos de distintos permission sets y considere 100 como el límite de RBAC para toda la cuenta.

> **Propuesta de diseño**: mida las asignaciones por permission set y la duplicación de políticas antes de comparar la simplificación de RBAC, ABAC y la separación de cuentas. Un aviso al llegar a 50 es un umbral local opcional, no un requisito de AWS ni un activador obligatorio de ABAC.

## 4. Acceso de cargas de trabajo (aplicaciones/automatización) a AWS

Los elementos siguientes no son opciones mutuamente excluyentes; se combinan según el entorno de ejecución y la necesidad de acceso entre cuentas.

| Método | Configuración | Adecuado para |
|---|---|---|
| Rol del entorno de ejecución | Asociar un rol de IAM a un entorno de ejecución (EC2/Lambda/ECS, etc.) | Cargas de trabajo que no son de EKS |
| **EKS Pod Identity** | Asociar un Pod a un rol de IAM mediante una asociación de Pod Identity | Cargas de trabajo de EKS compatibles (dirección recomendada) |
| IRSA | Tokens de cuentas de servicio de Kubernetes + proveedor OIDC de IAM | Clústeres/cadenas de herramientas existentes que necesitan compatibilidad |
| **Rol de destino entre cuentas** | El rol de origen asume un rol de la cuenta de destino | Rutas que deben ejecutarse con permisos del rol de destino |

Permita claves de acceso estáticas solo como excepción para integraciones heredadas que no admitan roles ni federación, y documente de forma explícita el propósito, el propietario, la fecha de vencimiento y la rotación.

El rol principal de la asociación de Pod Identity está en la cuenta del clúster. Al establecer targetRoleArn, se encadenan dos roles, mientras que las políticas de recursos compatibles pueden autorizar directamente a ese rol de origen. IRSA también puede federarse directamente con un proveedor OIDC/rol de una cuenta de destino. La reutilización de roles y el diseño de etiquetas y políticas de sesión determinan el número de roles; «exactamente dos por carga de trabajo» no es una regla universal. Los roles de cargas de trabajo para las API de AWS se cuentan por separado de las entradas de acceso para el acceso a la API de Kubernetes.

## 5. Acceso a la API de Kubernetes

| Método | Configuración | Estado |
|---|---|---|
| **Entradas de acceso de EKS** | Administrar el acceso al clúster por principal de IAM mediante entradas de acceso, con una política de acceso o una asignación de grupo de Kubernetes para RBAC | Dirección recomendada |
| ConfigMap aws-auth | Administrar la asignación de principales de IAM a identidades de Kubernetes mediante el ConfigMap `aws-auth` del clúster | Mantener solo como excepción durante la migración de clústeres heredados |

**Unión de permisos**: las concesiones de las políticas de acceso y de RBAC de Kubernetes se combinan; ninguna restringe a la otra. Registre la ruta principal de cada principal y las concesiones adicionales intencionales, y revise las superposiciones. Las comprobaciones automatizadas son opciones útiles de implementación, no requisitos previos para usar la API.

## Siguiente paso

Una vez definidos los límites de cuentas e IAM, la siguiente decisión es cuántos clústeres EKS ejecutar y cómo lograr la disponibilidad → [Arquitectura EKS multicuenta y multiclúster](./03-eks-multi-account-multi-cluster.md)

## Referencias

- [Cuotas de IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/limits.html)
- [ABAC de IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/abac.html)
- [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Prácticas recomendadas de IAM para EKS](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Rol de destino de EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-assign-target-role.html)
- [Roles de IAM para cuentas de servicio (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Estrategia de varias cuentas para EKS](https://docs.aws.amazon.com/eks/latest/best-practices/multi-account-strategy.html)
- [Cuotas de EKS](https://docs.aws.amazon.com/general/latest/gr/eks.html#limits_eks)
- [Requisitos de subredes compartidas de EKS](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [Dejar de compartir subredes](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html)
- [Patrones de políticas de recursos de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
