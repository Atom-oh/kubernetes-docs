# Análisis profundo de MLflow en EKS

> **Versión de referencia revisada**: MLflow 3.16.0
> **Última versión comprobada**: MLflow 3.17.1 (13 de octubre de 2026); último parche de 3.16, 3.16.1 (17 de septiembre de 2026)
> **Documentación revisada**: 16 de octubre de 2026

## Descripción general

MLflow ofrece seguimiento de experimentos, registro de artefactos de modelos, inscripción de modelos en el registro, administración de versiones, evaluación de GenAI y trazas. Las trazas se incorporaron en la versión 2.14.0; la versión 3.x amplió LoggedModel, la evaluación y la integración con la interfaz de usuario. La versión 3.16.0 se publicó el 4 de septiembre de 2026.

El parche 3.16.1 llegó el 17 de septiembre de 2026 y eliminó la contraseña predeterminada de administrador de autenticación básica que se incluía en el paquete. Los ejemplos siguientes se comprobaron con la versión 3.16.0 y no se volvieron a ejecutar con la 3.16.1. MLflow 3.17.0 (7 de octubre de 2026) es una versión menor posterior que requiere una actualización coordinada del esquema SQL para los servidores respaldados por SQL; la versión 3.17.1 (13 de octubre de 2026) es su lanzamiento de parche. Esta serie no abarca las versiones 3.17.x.

Úsalo localmente con el SDK y SQLite, u opera un servicio de seguimiento HTTP con almacenes de metadatos SQL y de artefactos independientes. Un servicio lógico no tiene por qué consistir en un solo Pod o sistema de almacenamiento. Esta serie abarca el seguimiento, el registro de modelos y la implementación en EKS; no valida todas las funciones de MLflow ni el entrenamiento correcto con GPU.

## Mapa de componentes

| Concepto | Problema que resuelve | Análisis profundo |
|---------|--------------------|-----------|
| **Seguimiento** | Registrar y consultar parámetros, métricas, artefactos, modelos y trazas de GenAI de los experimentos | [Parte 1](01-tracking.md) |
| **Registro de modelos** | Asignar a un modelo una identidad estable y con versiones, independiente de cualquier ejecución de entrenamiento | [Parte 2](02-model-registry.md) |
| **Implementación en EKS** | Ejecutar el servidor de seguimiento, el almacén de backend y el almacén de artefactos en EKS | [Parte 3](03-eks-deployment.md) |

![Diagrama de una canalización de tres etapas que muestra MLflow Tracking (experimentos, ejecuciones y trazas), que alimenta el Registro de modelos (modelos registrados y alias), que a su vez se resuelve mediante una etapa de servicio que queda fuera del alcance de esta serie de documentación.](../../.gitbook/assets/en-ai-ml-mlflow-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-readme-0.html)

## Por qué ejecutarlo en EKS

La disyuntiva es la misma que se aborda en otras secciones de datos y ML de este sitio de documentación: un equipo que ya ejecuta EKS puede reutilizar los mismos patrones de implementación, IAM (IRSA/Pod Identity) y observabilidad para el servidor de seguimiento de MLflow que para el resto del clúster, a cambio de operar directamente el servidor de seguimiento, su base de datos de backend y su almacén de artefactos, en lugar de usar una alternativa administrada.

La [guía de SageMaker AI](../sagemaker-ai/README.md) describe un diseño de comparación de Qwen. Ese ejemplo tiene sus propias versiones históricas fijadas y actualmente bloquea la ejecución con GPU porque su DLC llegó al final de su ciclo de parches. Las comprobaciones locales de MLflow 3.16.0 de esta serie no constituyen una validación integral de ese ejemplo.

El registro en el Registro de modelos es un paso opcional del ciclo de vida. Los sistemas de inferencia consumen las URI de modelos o sus alias mediante una configuración independiente; registrar un modelo o cambiar un alias no implementa un modelo automáticamente.

## Cobertura actual

1. [Parte 1: Seguimiento de MLflow](01-tracking.md): experimentos, ejecuciones, registro automático, el cambio de `LoggedModel` en MLflow 3 y el seguimiento de GenAI
2. [Parte 2: Registro de modelos de MLflow](02-model-registry.md): modelos registrados, versiones de modelo, alias y linaje
3. [Parte 3: Implementación de MLflow en EKS](03-eks-deployment.md): servidor de seguimiento, almacén de backend PostgreSQL, almacén de artefactos S3 y acceso de IAM

## Fuentes principales

- [Lanzamiento de MLflow 3.17.1](https://github.com/mlflow/mlflow/releases/tag/v3.17.1)
- [Lanzamiento de MLflow 3.17.0 (notas de actualización de la base de datos)](https://github.com/mlflow/mlflow/releases/tag/v3.17.0)
- [Lanzamiento de MLflow 3.16.1](https://github.com/mlflow/mlflow/releases/tag/v3.16.1)
- [Versión de referencia revisada: MLflow 3.16.0](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Trazas incorporadas en MLflow 2.14.0](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)
- [Almacén de backend](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
