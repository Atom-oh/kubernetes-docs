# Análisis profundo de MLflow en EKS

> **Base de revisión**: MLflow 3.16.0
> **Último parche comprobado**: MLflow 3.16.1 (September 17, 2026)
> **Documentación revisada**: October 12, 2026

## Descripción general

MLflow proporciona seguimiento de experimentos, registro de modelos y su registro en el Registry, gestión de versiones, evaluación de GenAI y Tracing. Tracing se incorporó en 2.14.0; 3.x amplió `LoggedModel`, la evaluación y la integración de la UI. La versión 3.16.0 se lanzó el 2026-09-04.

El parche 3.16.1 se publicó después, el 2026-09-17, y eliminó la contraseña predeterminada del administrador de basic-auth distribuida. Los ejemplos siguientes se comprobaron con 3.16.0 y no se volvieron a ejecutar con 3.16.1. MLflow 3.17.0 (2026-10-07) es una versión secundaria posterior que requiere una actualización coordinada del esquema SQL para los servidores respaldados por SQL; esta serie no la cubre.

Úsalo localmente con el SDK y SQLite, u opera un servicio de Tracking HTTP con metadatos SQL y almacenes de artefactos independientes. Un servicio lógico no tiene por qué ser un único Pod ni un único sistema de almacenamiento. Esta serie cubre Tracking, Registry y el despliegue en EKS; no valida todas las funciones de MLflow ni un entrenamiento de GPU exitoso.

## Mapa de componentes

| Concepto | Problema que resuelve | Análisis detallado |
|---------|--------------------|-----------|
| **Tracking** | Registra y consulta parámetros, métricas, artefactos, modelos y trazas de GenAI de experimentos | [Parte 1](01-tracking.md) |
| **Model Registry** | Proporciona a un modelo una identidad estable y versionada independiente de cualquier ejecución de entrenamiento | [Parte 2](02-model-registry.md) |
| **EKS Deployment** | Ejecuta el servidor de Tracking, el backend store y el artifact store en EKS | [Parte 3](03-eks-deployment.md) |

![Un diagrama de pipeline de tres etapas que muestra MLflow Tracking (experimentos, ejecuciones, trazas) alimentando el Model Registry (modelos registrados, aliases), que a su vez se resuelve mediante una etapa de Serving que queda fuera del alcance de esta serie de documentación.](../../.gitbook/assets/en-ai-ml-mlflow-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-readme-0.html)

## Por qué ejecutar esto en EKS

La disyuntiva es la misma que se aborda en otras secciones de datos/ML de este sitio de documentación: un equipo que ya ejecuta EKS puede reutilizar los mismos patrones de despliegue, IAM (IRSA/Pod Identity) y observabilidad para el servidor de Tracking de MLflow que para todo lo demás en el clúster, a cambio de operar directamente el servidor de Tracking, su base de datos backend y su artifact store, en vez de utilizar una alternativa gestionada.

La [guía de SageMaker AI](../sagemaker-ai/README.md) describe un diseño de comparación de Qwen. Ese ejemplo tiene fijaciones de versiones históricas separadas y actualmente bloquea la ejecución de GPU porque su DLC llegó al final de los parches. Las comprobaciones locales de MLflow 3.16.0 de esta serie no constituyen una validación integral de ese ejemplo.

El registro en Model Registry es un paso opcional del ciclo de vida. Los sistemas de Serving consumen los URI de modelos o los aliases mediante una configuración independiente; el registro o un cambio de alias no despliega automáticamente un modelo.

## Contenido cubierto actualmente

1. [Parte 1: MLflow Tracking](01-tracking.md) — experimentos, ejecuciones, autologging, el cambio de `LoggedModel` de MLflow 3 y Tracing de GenAI
2. [Parte 2: MLflow Model Registry](02-model-registry.md) — Registered Models, Model Versions, aliases y lineage
3. [Parte 3: Desplegar MLflow en EKS](03-eks-deployment.md) — servidor de Tracking, backend store de PostgreSQL, artifact store de S3 y acceso de IAM

## Fuentes principales

- [Lanzamiento de MLflow 3.16.1](https://github.com/mlflow/mlflow/releases/tag/v3.16.1)
- [Base de revisión de MLflow 3.16.0](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Tracing introducido en MLflow 2.14.0](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)
- [Backend store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
