# Introducción al gobierno de la nube empresarial

> **Última actualización**: 13 de septiembre de 2026

## 1. Problema que aborda esta sección

Hasta ahora, los documentos de EKS, redes y seguridad suponían que había «un clúster
y una VPC» y explicaban funciones individuales sobre esa base. Pero las preguntas
cambian en una organización empresarial grande que opera decenas de equipos y
cientos de ingenieros en varias marcas, dominios y servicios.

- ¿Cuántas cuentas debemos crear?
- ¿Se deben compartir las VPC o mantenerlas separadas?
- ¿Cada equipo debe tener su propio clúster de EKS o se deben compartir los clústeres?
- ¿Estos tres límites (cuenta/VPC/EKS) y el límite de datos deben coincidir uno a uno?

Esta sección trata las decisiones de estandarización para entornos grandes con
varias cuentas y clústeres de EKS. Las restricciones de los servicios se comprueban
con la documentación de AWS enlazada; los diseños híbridos, los criterios de
separación y los umbrales de prueba de concepto son propuestas que la organización
debe validar. No establece las conclusiones de una revisión privada concreta ni el
éxito en producción de ninguna empresa.

## 2. Por qué se deben evaluar por separado los límites de cuenta de AWS, VPC, EKS y datos

El error más común es crear una cuenta por equipo o marca, y asociar
automáticamente una VPC y un clúster de EKS dedicados a cada cuenta: una **fórmula
fija uno a uno**. Es una regla sencilla, pero incluso una carga de trabajo pequeña
termina asumiendo el costo fijo de un clúster completo, y cada reorganización se
convierte en una migración de infraestructura.

La alternativa que propone esta sección es **evaluar cada límite de forma independiente**.

| Límite | Criterios de evaluación |
|---|---|
| Cuenta de AWS | Requisitos de seguridad, cuotas de servicio, costo/titularidad, ciclo de vida |
| VPC | Política de red, zona de confianza, requisitos de conectividad |
| EKS | Radio de impacto en tiempo de ejecución, requisitos de aislamiento de tenants y SLO |
| Datos | Propiedad de los datos, límite regulatorio, responsabilidad de copia de seguridad/recuperación |

Así se pueden tomar decisiones más precisas, como «esta carga de trabajo no necesita
su propia VPC, pero los requisitos normativos exigen una cuenta dedicada». También
hay un costo: ahora hay que mantener criterios de evaluación para cada límite, y
las excepciones pueden multiplicarse.

<span id="_3-four-conditions-where-aws-forces-boundaries-together"></span>

## 3. Restricciones de los servicios que se deben comprobar al conectar límites

Las decisiones independientes aún deben tener en cuenta las restricciones de
ubicación y autorización de los servicios. Estas restricciones no implican
automáticamente una única estructura organizativa obligatoria.

1. **Las subredes configuradas para un clúster de EKS deben pertenecer a una VPC.** Dos clústeres independientes pueden usar la misma VPC. Usar VPC distintas es una decisión adicional sobre el enrutamiento compartido, DNS y los dominios de fallo del espacio de direcciones.
2. **El rol de IAM principal de una asociación de Pod Identity debe estar en la cuenta del clúster.** La función de rol de destino usa el encadenamiento de rol de asociación → rol de destino. Otras opciones incluyen acceso directo mediante políticas de recursos para servicios como S3 y federación IRSA directa a un rol de la cuenta de destino. No se requieren dos roles para todas las solicitudes entre cuentas.
3. **En una VPC compartida, diseña los roles de IAM del clúster/nodos de EKS y los grupos de seguridad asociados teniendo en cuenta la cuenta participante que crea el clúster.** Puede ser distinta de la Workload Account propietaria de una base de datos o cola. Compartir una subred no transfiere la propiedad de los recursos.
4. **Los límites de datos varían según el servicio.** Las instancias de RDS usan subredes de una VPC; los buckets de S3 no se ubican en subredes. La lista de compatibilidad de VPC compartidas indica explícitamente que puede omitir servicios; por lo tanto, la ausencia en la lista no demuestra por sí sola que no haya compatibilidad ([Límites de datos y seguridad](./05-data-security-boundaries.md)).

## 4. Priorizar lo compartido o lo dedicado

Una vez que decides evaluar los límites de forma independiente, la siguiente
pregunta es: para las cargas de trabajo sin motivos para separarlas, ¿se debe
preferir el uso compartido o los recursos dedicados?

- **Priorizar lo compartido**: Primero se admiten las cargas de trabajo pequeñas en cuentas, VPC y clústeres compartidos. El aprovisionamiento es más rápido y se duplica menos infraestructura, pero existe el riesgo de interferencia entre inquilinos y de que se acumulen con el tiempo recursos compartidos sin responsable.
- **Priorizar lo dedicado**: Cuando no está claro si conviene separar, primero se evalúan límites dedicados. Se aclaran el costo, la responsabilidad y el radio de impacto, pero los costos fijos crecen rápidamente.

En la práctica, es razonable empezar con una estrategia **híbrida que priorice lo
compartido y pase a recursos dedicados cuando se confirmen requisitos normativos,
cuotas independientes o SLO estrictos**. Para no volver a debatir esta decisión en
cada caso, la sección posterior sobre [marco de decisión y diseño de prueba de concepto](./06-decision-framework-and-poc.md) explica cómo crear una matriz de decisión reproducible.

## 5. Un ID estable de carga de trabajo y metadatos mutables

Las reorganizaciones, consolidaciones de marcas y renombramientos de equipos
seguirán ocurriendo. Si los límites de cuenta o VPC dependen directamente de los
nombres de los equipos o las marcas, cada reorganización se convierte en una
migración de infraestructura.

La recomendación es mantener un único **Workload ID estable** y gestionar el
dominio, la marca, el equipo, el CUJ (recorrido crítico del usuario), el entorno, la
clase de datos y el SLO como **metadatos mutables** asociados a ese ID. Los equipos
cambian con las reorganizaciones, pero los dominios (capacidades empresariales)
son relativamente estables; por eso, un dominio es una base mejor para los límites
de cuenta que un equipo.

## 6. Contenido de esta sección

| Documento | Contenido |
|---|---|
| [Landing Zone, OUs y control organizativo](./01-landing-zone-and-ou.md) | Cadena de dependencias de referencia de Control Tower, diseño de OU y funciones de SCP/RCP/Tag Policy |
| [Estructura de cuentas y límites de IAM](./02-account-and-iam.md) | Partición de cuentas, IAM para usuarios/cargas de trabajo y acceso a la API de Kubernetes |
| [Arquitectura de EKS con varias cuentas y clústeres](./03-eks-multi-account-multi-cluster.md) | Clústeres compartidos/dedicados y condiciones reales para la redundancia del runtime A/B de EKS |
| [VPC compartida y conectividad](./04-shared-vpc-and-connectivity.md) | La cadena real de cuellos de botella de cuotas para VPC compartida, que combina TGW/PrivateLink/Lattice |
| [Límites de datos y seguridad](./05-data-security-boundaries.md) | Restricciones de copia de seguridad/restauración entre cuentas y aislamiento del nivel de datos PII |
| [Marco de decisión y diseño de prueba de concepto](./06-decision-framework-and-poc.md) | Construcción de una matriz de decisión, factores que se pasan por alto fácilmente y métricas de medición de pruebas de concepto |

Cada documento prioriza hechos verificados («los servicios de AWS se comportan
realmente así en estas condiciones») por encima de opiniones, y señala claramente
las partes que aún requieren criterio de la organización.

## Referencias

- [Requisitos de redes de EKS](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [Patrones de políticas de recursos entre cuentas de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
