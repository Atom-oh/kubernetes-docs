# Límites de datos y seguridad

> **Última actualización**: 13 de septiembre de 2026

## 1. Opciones de titularidad de los datos

| Opción | Configuración |
|---|---|
| Cuenta centralizada de operaciones de bases de datos | El equipo de plataforma es propietario y opera todas las bases de datos en una sola cuenta |
| Datos propiedad de las cargas de trabajo | Cada equipo de cargas de trabajo es propietario y opera su propia base de datos |
| **Híbrida** | Las bases de datos operativas se eligen por carga de trabajo; los recursos compartidos, como un lago/almacén de datos o una infraestructura troncal de streaming, pertenecen a una plataforma de datos independiente |

El enfoque híbrido es un punto de partida realista para la mayoría de las organizaciones. Sin embargo, esta decisión importa menos que las **restricciones técnicas de copia de seguridad/restauración entre cuentas**, que se abordan en la siguiente sección.

<span id="_2-cross-account-data-recovery-constraints-—-the-conditions-that-actually-change-your-decision"></span>

## 2. Valide la recuperación entre cuentas según el recurso y el tipo de almacén

Elija conjuntamente la titularidad de los datos y la ubicación de recuperación. Una restricción en una API de instantáneas no hace imposibles todas las vías de recuperación.

<span id="rds-snapshots"></span>

### Compartir instantáneas de RDS

- Para las instancias de base de datos RDS, copie una instantánea automatizada a una instantánea manual antes de compartirla. El procedimiento para compartir RDS también trata las instantáneas generadas por AWS Backup; no define todos los flujos de trabajo de restauración de AWS Backup.
- El destinatario copia una instantánea compartida y cifrada de una instancia de base de datos antes de restaurarla. Las instantáneas cifradas con la clave KMS predeterminada administrada por AWS no se pueden compartir tal cual; evalúe una copia cifrada con una clave administrada por el cliente y aprobada.
- Se puede compartir una instantánea manual con hasta 20 cuentas. Las opciones permanentes/persistentes de Oracle/SQL Server añaden restricciones.
- **Las instantáneas de clústeres de bases de datos Multi-AZ no pueden usar esta vía de uso compartido de instantáneas de RDS.** Esto no descarta todas las rutas de copia de seguridad lógica ni las rutas de replicación/recuperación validadas, y tampoco exige que las bases de datos pertenezcan a las cargas de trabajo. Compruebe el motor, el tipo de instantánea, la compatibilidad de la región y el RTO/RPO de las alternativas de recuperación.

<span id="aws-backup-cross-account-copy"></span>

### Almacén estándar de AWS Backup: copiar y luego restaurar

- El origen y el destino deben pertenecer a la misma organización, y la cuenta de administración debe habilitar las copias de seguridad entre cuentas.
- El rol de origen necesita `backup:CopyFromBackupVault` y `backup:CopyIntoBackupVault`; el almacén de destino necesita una política de recursos que permita esta última acción. También se aplican los permisos específicos del servicio para copias de seguridad/copia y KMS.
- El cifrado depende del tipo de recurso. Los destinos de recursos de AWS Backup totalmente administrados admiten `aws/backup` o claves administradas por el cliente; los demás tipos de recursos requieren una clave administrada por el cliente. La página oficial de copia también advierte que no se usen los almacenes predeterminados. Por tanto, esta guía usa un **almacén de destino dedicado con configuración explícita de clave/política**; el nombre del almacén por sí solo no demuestra que el cifrado o la copia sean adecuados.
- La recuperación entre cuentas desde un almacén estándar primero copia y luego restaura en el destino. Prepare el rol vinculado al servicio del recurso, el rol de restauración, las subredes y los grupos de seguridad.
- No se admite la copia entre cuentas desde niveles de almacenamiento en frío. Compruebe las matrices de funciones para el recurso y la región.

### Almacén con aislamiento lógico: restaurar directamente desde una cuenta compartida

Un almacén con aislamiento lógico se puede compartir mediante AWS RAM con cuentas individuales, **incluidas las cuentas de otra organización**. El destinatario puede restaurar directamente los puntos de recuperación compatibles, sin copiarlos primero a un almacén propio. Por eso, afirmar que «AWS Backup nunca admite la restauración directa entre cuentas» es incorrecto.

Distinga los permisos de copia de almacenes estándar del uso compartido mediante RAM de almacenes con aislamiento lógico. Valide la compatibilidad del recurso/región, el IAM de restauración, el tipo de clave de cifrado, la autorización para compartir y la recuperación cuando la cuenta de origen no esté disponible. No dé por sentado que esto admite todos los tipos de bases de datos.

<span id="summary"></span>

### Restringir la copia y el uso compartido no aprobados

Un destino que salga de la organización puede conservar las copias existentes. Evalúe conjuntamente las condiciones `backup:CopyTargets`/`backup:CopyTargetOrgPaths` del origen, las políticas del almacén de destino, KMS, los permisos para compartir mediante RAM y los procedimientos de salida de la organización. Habilitar las copias de seguridad entre cuentas no concede permiso de copia a todos los usuarios ni elude las denegaciones de IAM, del almacén o de KMS.

El RTO incluye las tareas de copia, restauración y validación de la aplicación que realmente se realizan después de un incidente. Las copias preexistentes hacen que la periodicidad de copia influya en el RPO. Registre las pruebas y los objetivos de recuperación específicos de cada recurso en el [Marco de decisión](./06-decision-framework-and-poc.md).

## 3. Aislar el nivel de datos PII

El almacenamiento que se coloca directamente dentro de una VPC (RDS, etc.) encaja bien en una VPC separada del nivel general de servicio. El propósito es separar el alcance del enrutamiento, la inspección, el acceso directo y la contención de incidentes. **Una VPC separada por sí sola no basta**; también se necesitan IAM, grupos de seguridad, política de claves KMS, registros y rutas de acceso aprobadas que funcionen conjuntamente.

> **Acceso de auditoría a una VPC compartida**: los participantes no pueden describir las puertas de enlace NAT del propietario, pero los inventarios de rutas/NAT proporcionados por el propietario, Config, Flow Logs y el acceso delegado de solo lectura pueden proporcionar evidencia. Las VPC dedicadas pueden simplificar la titularidad; una VPC compartida no es inherentemente inauditable.

S3 no es un recurso ubicado en una VPC. Contrólelo mediante la titularidad del bucket/cuenta, los endpoints de VPC y su política, la política del bucket/punto de acceso, la política de claves KMS y las rutas aprobadas por la organización.

### Bloquear el acceso de Dev/QA a los datos PII originales de Producción

Al concretar «bloquear el acceso directo» en vías específicas a nivel de API, se obtiene una matriz de cobertura como esta.

| Vía | Mecanismo de control |
|---|---|
| Copia de AWS Backup entre cuentas | Condiciones SCP `backup:CopyTargets`/`CopyTargetOrgPaths`, política de acceso del almacén de destino |
| Uso compartido de instantáneas de instancias de base de datos RDS | Restringir `rds:ModifyDBSnapshotAttribute` a la automatización aprobada; auditar destinatarios con `DescribeDBSnapshotAttributes` |
| Uso compartido de instantáneas de clústeres de bases de datos Aurora | Restringir `rds:ModifyDBClusterSnapshotAttribute` a la automatización aprobada; auditar destinatarios con `DescribeDBClusterSnapshotAttributes` |
| Uso compartido público de instantáneas de RDS/Aurora | Validar las listas de destinatarios permitidos y el rechazo de `restore=all` en ambas API para compartir; conservar los controles KMS, de detección y de corrección |
| Uso compartido saliente de instantáneas EBS | Restringir/auditar `ec2:ModifySnapshotAttribute` y createVolumePermission de los destinatarios |
| AMI permitidas por EC2 (consumo) | Los ajustes de cuenta/región o una política declarativa limitan el descubrimiento/uso de AMI públicas/compartidas; las AMI propiedad de la cuenta quedan excluidas |
| Replicación por lotes de S3 / replicación entre cuentas | Política del bucket, restricción de roles de replicación, RCP |
| Transferencia mediante DMS/Glue | Vía de red/IAM de ese servicio |
| Flujos CDC (MSK/Kinesis/DMS) | Política de recursos + restricción de consumidores entre cuentas |
| Consultas Athena/Redshift entre cuentas y Lake Formation | Auditar las concesiones de Lake Formation entre cuentas |

Elija el tipo de clave KMS y los permisos de recuperación para la ruta de copia/restauración seleccionada y los requisitos de la organización. AWS no exige universalmente claves administradas por el cliente para todo almacenamiento de PII. Pruebe las claves de destino, las copias preexistentes, las políticas/concesiones de clave permitidas y el uso compartido de almacenes con aislamiento lógico cuando la cuenta de origen no esté disponible.

## 4. Secrets Manager / KMS entre cuentas

Se necesitan tanto la política de recursos del secreto como la política de identidad de quien lo solicita. Los secretos entre cuentas necesitan una clave KMS administrada por el cliente, y esa clave requiere tanto la política de claves del propietario como la política IAM de quien la solicita. En otras palabras, la administración centralizada de secretos/claves requiere algo más que políticas y rotación: exige **administrar conjuntamente los permisos y la responsabilidad de recuperación entre ambas cuentas.**

## 5. Telemetría de seguridad nativa de AWS frente a CNAPP existente

Si su organización ya tiene una CNAPP (plataforma de protección de aplicaciones nativas de la nube) y está adoptando capacidades nativas de AWS, el enfoque más seguro no es «reemplazar el producto», sino **comparar la cobertura actual con las capacidades nativas de AWS según el propósito de seguridad y cubrir solo las brechas confirmadas.** Los propósitos se pueden agrupar así:

- Controles preventivos de la organización
- Postura de configuración
- Postura de seguridad de los datos
- Protección del runtime de cargas de trabajo
- Detección de amenazas
- Flujo de trabajo de hallazgos
- Detección con contexto de las cargas de trabajo

Algunos hechos confirmados:

- Distinga los estándares, controles y hallazgos ASFF de Security Hub CSPM de otras capacidades de Security Hub. Los nombres por sí solos no demuestran que el alcance de las funciones ni las dependencias de Config sean idénticos.
- La mayoría de los controles de Security Hub CSPM requieren el registro de AWS Config. Revise esto junto con las dependencias de la línea base administrada de Control Tower 4.0, sin convertirlo en un requisito previo de Config para el propio servicio IAM Identity Center.
- **Security Hub CSPM no recopila retroactivamente los hallazgos generados antes de la activación y solo procesa los hallazgos en las regiones donde está habilitado.** Para cubrir por completo las comprobaciones de seguridad documentadas del CIS AWS Foundations Benchmark, debe habilitarse en cada región compatible. GuardDuty también se habilita por región.
- GuardDuty y Security Hub están disponibles en la región de Seúl, pero los tipos de hallazgos y la cobertura de controles difieren por región; las comparaciones deben basarse en la cobertura real de la región de Seúl.

## 6. Servicios cuya compatibilidad con la creación de recursos en una subred compartida está confirmada

La tabla resume la lista oficial de compatibilidad de VPC compartida. Esa lista permite explícitamente algunas omisiones: consulte la documentación específica de cada servicio para los servicios no listados y distinga entre la falta explícita de compatibilidad y la ausencia en una lista.

| Servicio compatible | Notas |
|---|---|
| Amazon RDS, Aurora | Destino principal |
| ElastiCache (Redis OSS) | |
| Redshift, EMR, Glue | Destino habitual de una plataforma de datos |
| OpenSearch Service, MSK | |
| EC2, ECS, EKS, Lambda, EFS | |
| ALB/NLB/GWLB | |
| PrivateLink (endpoint de interfaz) | |
| VPC Lattice, TGW, VPC Peering, Traffic Mirroring | |
| Route 53 (asociación entre cuentas de PHZ) | |
| DMS, Verified Access, SageMaker Unified Studio | |
| **Amazon MQ** | **Solo ActiveMQ. RabbitMQ no es compatible** |

Para los motores que la lista oficial excluye expresamente, como Amazon MQ RabbitMQ, evalúe una ubicación separada. Antes de excluir de VPC compartida un CUJ entero, considere conectar solo esa dependencia mediante otra VPC o una ruta de API.

## Siguiente paso

Para que las decisiones sobre límites, cuentas, IAM, red y datos sean reproducibles → [Marco de decisión y diseño de PoC](./06-decision-framework-and-poc.md)

## Referencias

- [Uso compartido de instantáneas de RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html)
- [Uso compartido de instantáneas cifradas de RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/share-encrypted-snapshot.html)
- [Copia de AWS Backup entre cuentas](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)
- [Secrets Manager entre cuentas](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples_cross.html)
- [Política de claves KMS para cuentas externas](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)
- [Introducción a Security Hub CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
- [Controles de Security Hub CSPM por región](https://docs.aws.amazon.com/securityhub/latest/userguide/regions-controls.html)
- [Diferencias de GuardDuty por región](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_regions.html)
- [Herramientas de seguridad de AWS SRA](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/security-tooling.html)
- [Servicios compatibles con subredes compartidas](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
- [Uso compartido y restauración de almacenes con aislamiento lógico](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)

- [API para compartir instantáneas de Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_ModifyDBClusterSnapshotAttribute.html)
- [Alcance de AMI permitidas de EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-allowed-amis.html)
