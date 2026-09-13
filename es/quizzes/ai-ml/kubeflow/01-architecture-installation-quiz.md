# Cuestionario sobre arquitectura e instalación de Kubeflow en EKS

Referencia: distribución de la comunidad 26.03.1 / Dashboard 2.0.0 / KFP 2.16.1.

## Preguntas de opción múltiple

1. ¿Qué establece la graduación de Kubeflow en CNCF del 17 de agosto de 2026?

   - A) Cumplimiento automático de cada Deployment de EKS
   - B) Madurez y gobernanza del proyecto, incluida una auditoría de seguridad independiente
   - C) Ya no se necesitan más actualizaciones de seguridad
   - D) Aislamiento garantizado de tenants sin configuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Madurez y gobernanza del proyecto, incluida una auditoría de seguridad independiente**

La graduación se refiere al proyecto. La seguridad de Deployment, el aislamiento y el cumplimiento normativo aún requieren su propia evaluación.
</details>

2. ¿Qué referencia de versión utiliza este capítulo?

   - A) AWS Kubeflow 1.7 y Community 26.03.1 son idénticos
   - B) Community 26.03.1, que incluye KFP 2.16.1 y Dashboard 2.0.0
   - C) Cada componente utiliza la versión 26.03.1
   - D) La rama master sin fijar una versión de lanzamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Community 26.03.1, que incluye KFP 2.16.1 y Dashboard 2.0.0**

Las versiones de la distribución y de los componentes difieren. El plan de lanzamientos por calendario de la comunidad contempla aproximadamente dos lanzamientos base al año y describe el soporte como de mejor esfuerzo, no como un SLA.
</details>

3. ¿Qué ocurre cuando se omite Profile resourceQuotaSpec.hard?

   - A) El controller establece una cuota predeterminada de GPU
   - B) Istio proporciona una cuota de CPU equivalente
   - C) El controller de Profile no crea su ResourceQuota
   - D) El namespace recibe permisos ilimitados de AWS IAM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El controller de Profile no crea su ResourceQuota**

La cuota es opcional. Vaciar hard elimina la cuota administrada por el controller. RBAC, la política de red, el almacenamiento y el acceso a AWS son límites independientes.
</details>

4. ¿Qué debe comprobarse antes de seguir la antigua guía de instalación de la distribución de AWS?

   - A) Solo la actividad reciente del repositorio
   - B) Si cambió el logo del dashboard
   - C) Si el lanzamiento es compatible y sus imágenes requeridas siguen disponibles
   - D) Si cada componente es un CRD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Si el lanzamiento es compatible y sus imágenes requeridas siguen disponibles**

El lanzamiento v1.7.0-aws-b1.0.3 inspeccionado advierte explícitamente que la disponibilidad eliminada de la imagen de OIDC impide nuevas instalaciones. No es una receta verificada para 26.03.1.
</details>

5. ¿Qué afirmación sobre la identidad S3 actual de KFP está respaldada?

   - A) KFPv2 requiere universalmente una clave estática de usuario de IAM
   - B) fromEnv acepta únicamente claves de acceso estáticas
   - C) La guía actual documenta IRSA; el SDK real, ServiceAccount y la confianza del rol aún necesitan validación
   - D) Un Profile crea automáticamente una asociación de Pod Identity

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La guía actual documenta IRSA; el SDK real, ServiceAccount y la confianza del rol aún necesitan validación**

KFP 2.16.1 delega fromEnv a Go Cloud, cuya opción predeterminada fijada utiliza la cadena de credenciales de AWS SDK v2. Esta inspección del código fuente no demuestra un Deployment de EKS Pod Identity.
</details>

6. ¿Qué función desempeña el dashboard?

   - A) Entrena y despliega automáticamente todos los modelos
   - B) Proporciona navegación hacia las interfaces de los componentes
   - C) Reemplaza toda la autorización de aplicaciones
   - D) Almacena cada artefacto de pipeline en un CRD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporciona navegación hacia las interfaces de los componentes**

Los controllers de carga de trabajo y las API de aplicaciones realizan sus propias operaciones. Las API de KFP también utilizan persistencia; sus conceptos de Run y Experiment no son CRD de manera universal.
</details>

## Preguntas de respuesta corta

7. ¿Por qué conservar los objetos Profile y su CRD durante la migración a Dashboard v2?

<details>
<summary>Mostrar respuesta</summary>

El controller de Profile establece la propiedad del namespace. Eliminar un Profile puede propagarse en cascada a su namespace y recursos. Siga la limpieza específica de la versión de los recursos del controller anterior sin eliminar los Profiles ni los namespaces de los tenants.
</details>

8. ¿Qué demuestra una renderización correcta del overlay de Profile y qué permanece sin verificar?

<details>
<summary>Mostrar respuesta</summary>

Demuestra que las entradas seleccionadas de Kustomize generan manifiestos; el overlay revisado produjo 14 recursos con imágenes de Dashboard 2.0.0. No demuestra la admisión de la API, la preparación del controller, el aislamiento de tenants ni el acceso S3 en EKS. Las sustituciones de servicios administrados también necesitan comprobaciones de identidad, compatibilidad, red, costos y migración.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/01-architecture-installation.md) | [Siguiente cuestionario: Pipelines](02-pipelines-quiz.md)
