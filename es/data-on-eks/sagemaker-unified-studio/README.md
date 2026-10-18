# Gobernanza de SageMaker Unified Studio

> Documentación revisada: 2026-09-12. Los resultados del experimento hacen referencia al registro del 2026-09-01 y a la documentación histórica del 2 de septiembre.

Amazon SageMaker Unified Studio administra la colaboración, las herramientas y los
activos del catálogo para equipos de datos e IA. Esta sección explica los límites de
dominio y proyecto para los activos de canalizaciones de EKS, los usuarios y los
permisos de ejecución.
El **proyecto de Unified Studio/DataZone** aquí no es el mismo objeto de API que un
proyecto de MLOps de SageMaker AI ni que un dominio de SageMaker AI Studio.

## Límites incluidos

| Tema | Qué verificar |
| --- | --- |
| Tipo de dominio | Inicio de sesión/administración basados en IAM frente a los basados en IAM Identity Center |
| Perfil de proyecto / blueprint | Herramientas aprovisionadas al crear el proyecto frente a las habilitadas bajo demanda |
| Rol de miembro / ejecución | Identidad para acceder al portal/proyecto frente a identidad para ejecutar recursos de AWS |
| Membresía / acceso a datos | Designaciones administrativas frente a permisos de datos de IAM, Lake Formation y el catálogo |
| Ciclo de vida | Existencia del proyecto, disponibilidad del entorno, acceso real a las herramientas y limpieza de recursos propiedad del proyecto |

[La parte 4: dominio, proyecto y membresía](01-domains-projects-governance.md) explica
los fallos registrados del experimento Qwen mediante estos límites. Un proyecto de
Unified Studio es la opción de gobernanza de esta guía, no una dependencia técnica
obligatoria para todos los Training Jobs de SageMaker ni para todas las cargas de
trabajo de entrenamiento de EKS.

## Distinguir la evidencia histórica del estado actual

El JSON de validación guardado del 2026-09-01 registra una detención antes del
entrenamiento, la limpieza de los recursos App/S3/IAM del experimento y un proyecto
de Unified Studio restante. La documentación del 2 de septiembre registra que en ese
momento se comprobó que seguía en estado ACTIVE.
**Esta revisión de la documentación no volvió a consultar la cuenta de AWS y no
afirma que hoy siga quedando un proyecto.**

Antes de reanudar ese experimento, un operador autorizado debe verificar el inventario,
la membresía y el estado de limpieza actuales. No generalice el fallo anterior para
conceder privilegios nuevos automáticamente ni para eliminar recursos compartidos.

Guías relacionadas:

- [Guía de PII de SageMaker Qwen](../../ai-ml/sagemaker-ai/README.md)
- [Parte 3: SageMaker AI y MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
- [Parte 5: resultados de validación factual](../../ai-ml/sagemaker-ai/04-validation-results.md)

## Referencias

- [Dominios basados en IAM](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [Roles de miembro y ejecución del proyecto](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [Perfiles de usuario y grupo](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [Solicitud CreateProject y estado de implementación](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [Todos los perfiles de capacidades y aprovisionamiento bajo demanda](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [Eliminación de proyectos y recursos externos](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [Validación registrada del aprovisionamiento de Qwen](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
