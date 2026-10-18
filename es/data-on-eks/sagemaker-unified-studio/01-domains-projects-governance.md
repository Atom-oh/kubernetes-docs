# Parte 4: Gobernanza de dominios, proyectos y membresías

> Documentación revisada: 2026-09-12. Los resultados del aprovisionamiento de Qwen son históricos; no se volvió a comprobar el estado actual de la cuenta.

El tercer intento de aprovisionamiento de Qwen registrado informa de la creación de un proyecto, seguida de denegaciones de lectura/eliminación debido a la membresía de quien realizó la llamada. El entrenamiento no comenzó.
No generalices ese registro al estado actual de todos los dominios ni a todos los fallos de autorización.

## 1. Distinguir objetos e identidades

| Objeto/rol | Significado |
| --- | --- |
| Dominio unificado / unidad de dominio | Límite de gobernanza y jerarquía organizativa |
| Perfil de proyecto / blueprint | Aprovisionamiento de herramientas/entornos y cuentas/regiones permitidas |
| Proyecto | Colaboración, herramientas y recursos compartidos |
| Perfil de usuario/grupo | Representación del servicio para identidades de SSO o roles de IAM registrados |
| Designación de membresía | Roles a nivel de proyecto, como PROJECT_OWNER y PROJECT_CONTRIBUTOR |
| Rol de ejecución del proyecto | Identidad que accede a datos/cómputo de AWS para el proyecto |
| Activo del catálogo | Metadatos sujetos a gobernanza, como descripciones, esquemas y ubicaciones |

Primero identifica si la configuración y el inicio de sesión se basan en IAM o en Identity Center.
Los roles de miembro y de ejecución tienen finalidades distintas, aunque su ARN sea el mismo. Los miembros de un proyecto basado en IAM comparten el acceso a datos/cómputo mediante el rol de ejecución del proyecto; la designación de propietario no aísla automáticamente los permisos de datos de cada usuario. Si se usa, verifica por separado la autorización basada en identidad/Trusted Identity Propagation.

La documentación de administración de usuarios de AWS distingue entre el perfil de grupo de un rol de IAM registrado y el perfil de usuario de sesión que se crea para quien inicia sesión mediante ese rol.
La membresía puede usar el perfil de grupo del rol. CreateGroupProfile con rolePrincipalARN **registra un perfil; no crea el propio rol de IAM**.
El tratamiento automático del rol de ejecución de un proyecto no necesariamente equivale a la autorización de quien llama a la automatización.

## 2. El nombre de un perfil no demuestra que las herramientas estén listas

El perfil All capabilities identifica una plantilla de blueprints. Los perfiles pueden aprovisionar un blueprint al crear el proyecto o ponerlo a disposición más adelante bajo demanda. Comprueba los servicios, cuentas, regiones, redes y permisos necesarios para usar el perfil.

Selecciona el ID/configuración del perfil previsto en lugar de elegir a ciegas la primera coincidencia de nombre. Un conjunto más pequeño de capacidades puede servir para el experimento de Qwen, sujeto a aprobación organizativa y dependencias reales. Distingue este flujo de las rutas normales de entrenamiento de SageMaker/EKS sin proyectos de Unified Studio.

## 3. IAM, membresía y autorización de datos

Una acción de IAM permitida no otorga la propiedad del proyecto. La propiedad del proyecto tampoco elude las restricciones de IAM, SCP, políticas de recursos o permisos de datos.
Un miembro o colaborador normal no queda autorizado automáticamente a eliminar.
Verifica qué autoridad de propietario del proyecto o administrador requiere la ruta de eliminación.

La API actual de CreateProject acepta membershipAssignments.
Este es un **ejemplo de estructura de solicitud**: sustituye los identificadores de dominio/perfil/grupo por valores reales obtenidos con acceso autorizado.

```json
{
  "domainIdentifier": "dzd-1111111111111111",
  "name": "docs-governance-example",
  "projectProfileId": "c1111111111111",
  "membershipAssignments": [
    {
      "member": {
        "groupIdentifier": "11111111-1111-1111-1111-111111111111"
      },
      "designation": "PROJECT_OWNER"
    }
  ]
}
```


member es una unión etiquetada: establece **solo uno** de groupIdentifier o userIdentifier.
Incluir la membresía en la misma solicitud reduce la brecha que deja una solicitud de seguimiento por separado, pero no garantiza una reversión transaccional de todo el aprovisionamiento del proyecto/entorno. Vuelve a leer el proyecto y la membresía. Después de un timeout, concilia la solicitud original con el inventario en vez de crear repetidamente proyectos por nombre.

## 4. Secuencia para preparar el proyecto y las herramientas

1. Verifica la cuenta/región previstas, el tipo de dominio y el ID del perfil.
2. Distingue el inicio de sesión/perfil de quien llama, la autoridad necesaria de propietario/administrador y los permisos del rol de ejecución.
3. Identifica los blueprints que se aprovisionan al crear el proyecto y los que se aprovisionan bajo demanda, y prepara dependencias aprobadas.
4. Guarda y vuelve a leer los resultados de CreateProject y de la membresía.
5. Comprueba por separado projectStatus y environmentDeploymentDetails.
6. Verifica que el entorno/herramienta requerido esté listo y que exista acceso real de lectura/escritura antes del siguiente paso de cómputo.

projectStatus=ACTIVE no significa que todos los entornos/herramientas estén listos.
overallDeploymentStatus incluye PENDING_DEPLOYMENT, IN_PROGRESS, SUCCESSFUL,
FAILED_VALIDATION y FAILED_DEPLOYMENT. No trates como fallos las herramientas bajo demanda que intencionadamente no se aprovisionaron; verifica **lo que realmente necesita esta carga de trabajo**.

## 5. Fallos de etiquetas y divulgación en el catálogo

La API actual admite resourceTags. El rechazo del experimento anterior fue una observación específica del dominio/solicitud, no una prueba de que Unified Studio no admita etiquetas. Inspecciona las políticas, los valores y los errores reales. Limita las acciones compensatorias a los recursos creados por esta ejecución y autorizados para la limpieza; un prefijo por sí solo no justifica eliminar buckets o roles compartidos.

La documentación pública puede incluir la cantidad necesaria de experimentos, el esquema/cantidad de registros de datos sintéticos, la versión/semilla/hash del generador y los principios de propiedad/retención.
No incluyas PII real, credenciales, URL prefirmadas ni correspondencias de reidentificación en artefactos públicos.

Un **catálogo interno** con acceso controlado puede necesitar ubicaciones de almacenamiento e identificadores de recursos para facilitar el descubrimiento/acceso. El enmascaramiento de la documentación pública no prohíbe de forma general los metadatos de ubicación internos. La publicación de metadatos, la aprobación de suscripciones y la autorización real para acceder a los datos son pasos distintos.

## 6. Verificación de eliminación y ausencia

1. Identifica los datos que se deben conservar, los recursos de esta ejecución y sus dependencias.
2. Usa un contexto autorizado de propietario/administrador para detener el trabajo del proyecto y definir el alcance de limpieza.
3. Elimina los recursos según el ciclo de vida del proyecto, el entorno y los recursos administrados.
4. Inspecciona los estados/errores DELETING/DELETE_FAILED y verifica que la eliminación se haya completado.
5. Concilia las Apps, S3, IAM y el cómputo externos restantes con el inventario de las cuentas/regiones pertinentes.

GetProject AccessDenied no demuestra que el proyecto esté ausente.
Una respuesta vacía de ListProjects tampoco es suficiente si la visibilidad, los filtros o la paginación la restringen. Verifica el dominio/la identidad y todas las páginas, y combina pruebas autorizadas de get/list con el inventario de recursos externos. La eliminación del proyecto no garantiza la eliminación de todos los recursos de servicios externos; verifica por separado su propiedad y retención.

## 7. Alcance histórico de la validación de Qwen

El JSON de validación almacenado tiene fecha **2026-09-01**.
Registra trainingStarted=false en los tres intentos, un proyecto restante después del tercero y la limpieza de recursos de App/S3/IAM del experimento. La documentación del 2 de septiembre informa que en ese momento se volvió a comprobar el estado ACTIVE. Esta revisión compara esos registros con la documentación pública actual de la API; no establece si el proyecto existe o se eliminó en la cuenta actual.

Antes de reanudar, verifica el inventario y la propiedad actuales.
Durante esta revisión no se creó ni eliminó ningún proyecto, membresía, recurso de IAM ni recurso de GPU.
El ejemplo de solicitud superó la **validación local de entrada con el esqueleto de salida de AWS CLI**; la variante que establecía ambos tipos de identidad de miembro fue rechazada por ParameterValidation.
Esto no demuestra autorización activa ni que el aprovisionamiento del entorno se haya realizado correctamente.

## Referencias

- [Dominios basados en IAM](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [Roles de miembro y de ejecución del proyecto](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [Perfiles de usuario y grupo](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [Solicitud CreateProject y estado de implementación](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [Perfiles All capabilities y aprovisionamiento bajo demanda](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [Eliminación de proyectos y recursos externos](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [Validación registrada del aprovisionamiento de Qwen](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

[Anterior: SageMaker AI / MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)

[Siguiente: Resultados de validación](../../ai-ml/sagemaker-ai/04-validation-results.md)

[Cuestionario](../../quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
