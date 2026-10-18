# Landing Zone, OU y control organizativo

> **Última actualización**: 13 de septiembre de 2026

## 1. Cadena de dependencias de la línea base de Control Tower Landing Zone 4.0

Al estandarizar un entorno de varias cuentas, AWS Control Tower suele ser la primera herramienta que se utiliza. Control Tower proporciona la creación administrada de cuentas y líneas base/controles organizativos, pero **Landing Zone 4.0 impone un orden de activación dependiente entre varias líneas base**. Si se finaliza el diseño de OU e IAM sin conocer esta cadena, habrá que rehacer el trabajo.

### Cadena de dependencias de activación

```
CentralConfigBaseline
  └─▶ CentralSecurityRolesBaseline
        ├─▶ IdentityCenterBaseline
        ├─▶ BackupAdminBaseline
        └─▶ BackupCentralVaultBaseline
```

Para usar `IdentityCenterBaseline` (integración con Identity Center), primero debe estar activa `CentralSecurityRolesBaseline`, que a su vez requiere `CentralConfigBaseline` (AWS Config). **La desactivación debe seguir el orden inverso**: hay que desactivar las tres de la derecha (IdentityCenter/BackupAdmin/BackupCentralVault) antes de desactivar SecurityRoles y, después, se puede desactivar Config.

> **Alcance**: esta cadena se aplica a `IdentityCenterBaseline` administrada por Control Tower 4.0. IAM Identity Center en sí no requiere AWS Config. Distinga Identity Center administrado de forma independiente de su integración con Control Tower.

La integración de Config de Landing Zone implementa recursos de Config en las cuentas de integración de servicios. Las cuentas miembro necesitan la línea base AWSControlTowerBaseline o ConfigBaseline a nivel de OU; estas dos opciones son mutuamente excluyentes en una OU. Esta ruta administrada requiere la integración de Config de Landing Zone. Para Config implementado de forma independiente, diseñe por separado la titularidad, la gestión de conflictos y la cobertura de controles de detección.

<span id="the-security-ou-is-no-longer-freely-designable"></span>

### Ubicación de la OU de seguridad y alcance de la línea base

Las versiones anteriores de Landing Zone incluían la creación de una OU de seguridad administrada por Control Tower. **La versión 4.0 ya no administra su creación; la OU principal común que contiene las cuentas de integración de servicios se designa como OU de seguridad.** Compruebe estas restricciones del alcance de la línea base.

1. No se pueden aplicar `AWSControlTowerBaseline` ni Config Baseline a esta OU (aparece como `Not Applicable`, lo cual es normal). Sí se puede aplicar `BackupBaseline`.
2. Si se coloca una cuenta que no sea de integración de servicios en esta OU, no recibirá recursos de línea base.
3. Control Tower crea automáticamente conjuntos de permisos de Identity Center solo para las cuentas Logging y SecurityRoles. **Debe crear usted mismo los conjuntos de permisos para las cuentas Config y Backup.**

Trasladar una cuenta general a la misma OU que las cuentas de integración de servicios puede hacer que los controles habilitados se desvíen, independientemente de la inscripción automática. Esta restricción afecta a esa OU. Considere una OU administrada aparte para las herramientas generales de seguridad y las cuentas pendientes de migración.

> **Propuesta de diseño**: separe las cuentas de integración de servicios de las cuentas generales de operaciones de seguridad para aclarar el alcance de la línea base. AWS no exige nombres concretos para las OU.

### Cambió el comportamiento de desactivación de CentralizedLogging

En Control Tower 3.3 y versiones anteriores, desactivar la integración CentralizedLogging solo deshabilitaba Organization CloudTrail y conservaba los recursos ya implementados. **En 4.0, al desactivarla se eliminan realmente el Config Recorder, el Delivery Channel y las instancias de pila relacionadas con CloudTrail en la cuenta Logging.** Después de eso, Control Tower deja de administrar esa cuenta.

Antes de desactivarla, inventaríe por separado las pilas afectadas, las brechas de registro y los registros de S3 conservados. La administración se puede restaurar reactivando la integración o trasladando la cuenta a una OU administrada, pero hay que validar la recuperación de las brechas de recopilación. Este comportamiento no demuestra que se eliminen todos los registros históricos.

### Dividir la responsabilidad entre Control Tower y la canalización interna

Según las integraciones de servicios y las líneas base de OU que se activen, primero hay que decidir entre dos enfoques.

| Enfoque | Configuración | Compensaciones |
|---|---|---|
| A. Administrado por Control Tower | Habilitar las integraciones requeridas en orden de dependencia; seleccionar líneas base por OU | Operación centralizada, con alcance y costo de registro administrados en conjunto |
| B. División explícita de titularidad | Definir ámbitos de Identity Center/Config y de Control Tower administrados de manera independiente | Validación interna del ciclo de vida, los conflictos y la cobertura |

## 2. Inscripción automática

Con Landing Zone 3.1 o posterior, habilite la inscripción automática mediante los ajustes/API de Landing Zone antes de trasladar una cuenta a una OU registrada para aplicar automáticamente las líneas base y controles de esa OU. Aun así, hay cosas que no hace por usted.

- **No resuelve automáticamente conflictos de configuración preexistentes ni gestiona la recuperación de fallos.** Las comprobaciones previas (conflictos de Config, CloudTrail, SCP e IAM) deben hacerse por separado.
- La anulación de la inscripción puede eliminar recursos de línea base administrados. Verifique por separado la retención de registros y evidencia existentes. Mantener la gobernanza mientras se restringen los cambios es una opción operativa para retirar cuentas, no un requisito de AWS que obligue a mantener inscrita cada OU.
- La inscripción sigue un modelo de consistencia eventual, por lo que puede tardar desde minutos hasta horas según cuántas cuentas se trasladen.
- **La inscripción automática no crea, modifica ni termina productos aprovisionados de Service Catalog.** Si se anula la inscripción de una cuenta creada con Account Factory, su producto aprovisionado queda huérfano en la cuenta de administración.

Si su canalización interna automatiza «traslado de cuenta → inscripción automática → inicialización de cargas de trabajo», la condición de activación debería ser **«se confirmó que se completó la aplicación de la línea base»**, no el propio evento de traslado.

## 3. Cuotas por tipo de política organizativa

Los tipos de política compatibles con Organizations desempeñan funciones distintas y tienen cuotas predeterminadas diferentes.

| Tipo de política | Máximo de adjuntos por entidad | Tamaño máximo del documento | Máximo en toda la organización |
|---|---|---|---|
| SCP | 10 | 10,240 caracteres | 10,000 |
| RCP | 5 (incluido `RCPFullAWSAccess`; 4 disponibles) | 5,120 caracteres | 2,000 |
| Política declarativa | 10 | 10,000 caracteres | 1,000 |
| Política de etiquetas | 10 | 10,000 caracteres | 1,000 |
| Política de Backup | 10 | 10,000 caracteres | 1,000 |
| Política de Security Hub | 10 | 10,000 caracteres | 1,000 |

El dato clave es que **las políticas heredadas no consumen el límite de adjuntos por entidad**. Esto influye mucho en la estrategia de ubicación de SCP.

### Estrategias para ubicar adjuntos SCP

| Estrategia | Configuración | Evaluación desde el punto de vista de cuotas |
|---|---|---|
| Mucho en Root | Adjuntar en Root los SCP comunes a toda la organización; las OU heredan | Las cuentas nuevas heredan los controles de inmediato, pero es difícil crear excepciones por OU |
| Adjuntos directos completamente especificados por OU | Adjuntar directamente cada SCP que necesite cada OU, reduciendo al mínimo la dependencia de OU principales | No usa la herencia, así que una sola OU puede consumir el límite completo de 10 adjuntos; al llegar al límite, hay que combinar políticas |
| **Paquete por capas** | Root lleva solo un SCP mínimo y sin excepciones; el resto se administra en paquetes de políticas versionados por OU y excepciones con vencimiento | Aprovecha activamente la herencia para conservar el límite de adjuntos directos por OU; **es la opción más escalable desde el punto de vista de cuotas** |

Versione los documentos de políticas y los inventarios de adjuntos mediante revisiones de Git, manifiestos de implementación y cambios de CloudTrail. La versión en Sid es opcional. Las SCP/RCP heredadas, las políticas de recursos y los límites de permisos tienen alcances de evaluación distintos; una sola simulación no demuestra que la autorización efectiva esté completa.

Otras restricciones confirmadas:

- **Si una entidad tiene habilitada alguna SCP, no se puede eliminar la última SCP que le quede.** No es viable diseñar que «la OU de excepciones no tenga ningún control»; incluso las OU de excepciones necesitan una SCP mínima de línea base.
- El anidamiento de OU llega hasta **5 niveles** por debajo de Root, y la organización puede tener un máximo total de **2,000 OU**. Las estructuras planas o híbridas funcionales poco profundas no se ven afectadas por este límite.
- `RCPFullAWSAccess` consume uno de los cinco adjuntos RCP por entidad. Disponer de cuatro adjuntos directos no impide la herencia. Ubique los controles en los niveles Root, OU y cuenta mientras comprueba los servicios compatibles, las excepciones de principales de servicio y las denegaciones explícitas. Las RCP pueden proteger rutas a datos sensibles, pero no sustituyen a IAM, KMS ni a las políticas de recursos.
- Organizations también tiene un **tipo de política de Security Hub**, que permite implementar de forma centralizada la configuración de Security Hub como política organizativa y conviene revisar junto con SCP/RCP, las políticas declarativas y las políticas de etiquetas.

### Separación de funciones por tipo de política (hechos confirmados)

| Tipo de política | Función |
|---|---|
| SCP | Limita los permisos máximos de un principal (no concede permisos) |
| RCP | Limita los permisos máximos disponibles para recursos compatibles en las cuentas miembro (no concede permisos) |
| Política declarativa | Mantiene ajustes comunes de línea base de la organización para los servicios compatibles |
| Política de etiquetas | Comprueba y aplica el cumplimiento de los estándares de etiquetas |
| Control de Control Tower | Control preventivo/proactivo/de detección a nivel de OU |

Conviene recordar un principio de evaluación SCP: el enfoque de lista de permitidos requiere un Allow explícito **en todos los niveles** desde Root hasta la cuenta de destino, y un Deny explícito en cualquier nivel no puede anularse con un Allow situado más abajo.

## 4. Lista de permitidos frente a lista de denegación

| Enfoque | Adecuado para | Sobrecarga operativa |
|---|---|---|
| Centrado en lista de permitidos | Sandbox y zonas reguladas donde se puede restringir de antemano el conjunto de servicios utilizables | Hay que permitir explícitamente cada nuevo servicio/API antes de usarlo |
| **Centrado en lista de denegación** | OU general de cargas de trabajo (predeterminado) | Requiere detectar continuamente riesgos en nuevos servicios/API y mantener un catálogo Deny |

Compare los resultados regionales de `describe-vpc-endpoint-services` con la documentación de los servicios. El inventario de API por sí solo no demuestra que la compatibilidad con políticas de endpoints, funciones o DNS privado sea completa.

## 5. Opciones de diseño de OU

| Opción | Configuración | Ventajas | Desventajas |
|---|---|---|---|
| Jerarquía profunda | Varios niveles anidados debajo de Root; los controles de la OU principal se heredan en las secundarias | Representa fácilmente la clasificación y los controles compartidos en la jerarquía | Un Deny de nivel superior tiene un radio de impacto amplio. El límite real es de 5 niveles |
| Plana bajo Root | La mayoría de las OU están directamente bajo Root y los controles se adjuntan directamente | Facilita razonar sobre el radio de impacto de cada OU | Riesgo de duplicar u omitir políticas compartidas; sin herencia, se consume el límite de 10 adjuntos |
| **Híbrida funcional poco profunda** | Combina OU funcionales que cambian poco (`Security`, `Infrastructure`) con OU de ciclo de vida/procedimiento (`Workloads/Production`, `Workloads/Non-production`, `Sandbox`, `PolicyStaging`, `Transitional`, `Suspended`) con pocos niveles | Reduce el radio de impacto de los cambios de organigrama y expresa el estado operativo | Hay que validar conjuntamente la clasificación funcional, el ciclo de vida, la herencia y los paquetes de políticas. Debido a la restricción de la OU de seguridad 4.0 anterior, considere ubicar por separado las cuentas de integración de servicios y las de operaciones generales |

`Transitional` puede alojar temporalmente cuentas durante las comprobaciones de migración; `Suspended` puede restringir cambios antes del retiro. Decida la inscripción, la retención de evidencia y el acceso de recuperación para cada ciclo de vida. Use una `Quarantine` separada si los procedimientos de investigación de incidentes son distintos.

Conviene distinguir una OU persistente `Production-Exception` de las políticas de excepción con plazo limitado. Si una API o política concreta solo necesita estar permitida durante un periodo breve, gestione la excepción dentro de la OU Production estándar, con aprobación y vencimiento; cree una OU separada solo cuando una cuenta necesite un conjunto de controles fundamentalmente distinto a largo plazo que sea técnicamente incompatible con la línea base estándar.

## Siguiente paso

Una vez definidas Landing Zone y la estructura de OU, la siguiente decisión es cómo dividir las cuentas y qué rutas de IAM ofrecer a los usuarios y a las cargas de trabajo → [Estructura de cuentas y límites de IAM](./02-account-and-iam.md)

## Referencias

- [Cuotas de Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_reference_limits.html)
- [Cambios clave de Control Tower Landing Zone 4.0](https://docs.aws.amazon.com/controltower/latest/userguide/key-changes-lz-v4.html)
- [Actualizaciones de AWS Config en Control Tower (4.0)](https://docs.aws.amazon.com/controltower/latest/userguide/config-updates-v4.html)
- [Inscripción automática de cuentas en Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/account-auto-enrollment.html)
- [Tipos de línea base](https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html)
- [Inscribir una cuenta existente](https://docs.aws.amazon.com/controltower/latest/userguide/enroll-account.html)
- [Evaluación de SCP](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_evaluation.html)
- [RCP](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_rcps.html)
- [Políticas declarativas](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_declarative_policies.html)
- [Políticas de etiquetas](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html)
- [Referencia de controles de Control Tower](https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html)
- [Principios de diseño multicuenta de AWS](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/design-principles-for-your-multi-account-strategy.html)
- [OU y cuentas recomendadas por AWS](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/recommended-ous-and-accounts.html)
