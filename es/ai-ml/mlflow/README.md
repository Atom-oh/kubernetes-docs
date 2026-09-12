# Análisis detallado de MLflow en EKS

> **Línea base de revisión**: MLflow 3.16.0
> **Documentación revisada**: September 12, 2026

## Descripción general

MLflow proporciona seguimiento de experimentos, registro y registro en el Registry de modelos, gestión de versiones, evaluación de GenAI y tracing. Tracing llegó en la versión 2.14.0; la serie 3.x amplió LoggedModel, la evaluación y la integración con la UI. La versión 3.16.0 se lanzó el 2026-09-04.

Úselo localmente con el SDK y SQLite, u opere un servicio de tracking HTTP con almacenes independientes de metadatos SQL y artefactos. Un servicio lógico no tiene por qué ser un solo Pod o sistema de almacenamiento. Esta serie abarca Tracking, Registry y el despliegue en EKS; no valida todas las funcionalidades de MLflow ni el entrenamiento exitoso con GPU.

## Mapa de componentes

| Concepto | Problema que resuelve | Análisis detallado |
|---------|--------------------|-----------|
| **Tracking** | Registra y consulta parámetros de experimentos, métricas, artefactos, modelos y trazas de GenAI | [Parte 1](01-tracking.md) |
| **Model Registry** | Otorga a un modelo una identidad estable y versionada, independiente de cualquier ejecución de entrenamiento | [Parte 2](02-model-registry.md) |
| **Despliegue en EKS** | Ejecuta el servidor de tracking, el almacén de backend y el almacén de artefactos en EKS | [Parte 3](03-eks-deployment.md) |

![Un diagrama de pipeline de tres etapas que muestra MLflow Tracking (experimentos, ejecuciones, trazas) alimentando el Model Registry (modelos registrados, alias), que a su vez es resuelto por una etapa de Serving que está fuera del alcance de esta serie de documentación.](../../.gitbook/assets/en-ai-ml-mlflow-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-readme-0.html)

## Por qué ejecutar esto en EKS

La contrapartida es la misma que se aborda en otras secciones de datos/ML de este sitio de documentación: un equipo que ya ejecuta EKS puede reutilizar los mismos patrones de despliegue, IAM (IRSA/Pod Identity) y observabilidad para el servidor de tracking de MLflow que para todo lo demás en el clúster, a cambio de operar directamente el servidor de tracking, su base de datos de backend y su almacén de artefactos en lugar de utilizar una alternativa administrada.

La [guía de SageMaker AI](../sagemaker-ai/README.md) describe un diseño de comparación de Qwen. Ese ejemplo tiene versiones históricas fijadas por separado y actualmente bloquea la ejecución en GPU porque su DLC llegó al final de los parches. Las comprobaciones locales de MLflow 3.16.0 de esta serie no constituyen una validación de extremo a extremo de ese ejemplo.

El registro en Model Registry es un paso opcional del ciclo de vida. Los sistemas de Serving consumen URI o alias de modelos mediante configuración independiente; un registro o un cambio de alias no despliega automáticamente un modelo.

## Cobertura actual

1. [Parte 1: MLflow Tracking](01-tracking.md) — experimentos, ejecuciones, autologging, el cambio a `LoggedModel` en MLflow 3 y el tracing de GenAI
2. [Parte 2: MLflow Model Registry](02-model-registry.md) — Registered Models, Model Versions, alias y lineage
3. [Parte 3: Despliegue de MLflow en EKS](03-eks-deployment.md) — servidor de tracking, almacén de backend PostgreSQL, almacén de artefactos S3 y acceso IAM

## Fuentes principales

- [Lanzamiento de MLflow 3.16.0](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Tracing introducido en MLflow 2.14.0](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)
- [Almacén de backend](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
