# Cuestionario sobre arquitectura e instalación de Kubeflow en EKS

Este cuestionario evalúa tu comprensión de la arquitectura de componentes de Kubeflow, su graduación en CNCF, el modelo de lanzamientos de Kubeflow Community Distribution, los patrones de instalación específicos de EKS y el patrón de acceso de IAM para el almacenamiento de artefactos de Pipelines.

## Preguntas de opción múltiple

1. ¿Qué hito alcanzó Kubeflow con CNCF el 17 de agosto de 2026?
   - A) Fue aceptado como un proyecto sandbox de CNCF
   - B) Pasó de sandbox al estado de incubación
   - C) Se graduó — el nivel de madurez más alto de CNCF — después de una auditoría de seguridad y de formar un comité directivo
   - D) Fue archivado por CNCF debido a la inactividad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Se graduó — el nivel de madurez más alto de CNCF — después de una auditoría de seguridad y de formar un comité directivo**

**Explicación:**
Kubeflow ingresó a CNCF como un proyecto en incubación en 2023 y [se graduó el 17 de agosto de 2026](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/), después de superar una auditoría de seguridad independiente realizada por terceros y establecer un comité directivo formal para la gobernanza del proyecto. La graduación es el nivel de madurez más alto de CNCF.
</details>

2. ¿Qué esquema de versionado utiliza Kubeflow Community Distribution y con qué frecuencia aproximada publica una versión base?
   - A) Versionado semántico (major.minor.patch), publicado continuamente
   - B) Versionado de calendario (YY.MM.patch), aproximadamente dos veces al año
   - C) Una única etiqueta móvil "latest" sin lanzamientos discretos
   - D) Versionado LTS, una vez cada tres años

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Versionado de calendario (YY.MM.patch), aproximadamente dos veces al año**

**Explicación:**
Kubeflow Community Distribution utiliza versionado de calendario con el formato YY.MM.patch, con aproximadamente dos versiones base al año. La versión 26.03 es la versión base más reciente al momento de escribir esto (desde entonces se ha publicado un parche 26.03.1 con versiones más nuevas de los componentes).
</details>

3. En la arquitectura de Kubeflow, ¿qué es un "Kubeflow Profile"?
   - A) El tema y las preferencias de diseño del panel personal de un usuario
   - B) Un namespace de Kubernetes más enlaces de RBAC, cuotas de recursos y objetos Istio AuthorizationPolicy, reconciliados por el Profile Controller
   - C) Un archivo YAML que enumera los componentes instalados en un clúster
   - D) Una construcción de facturación utilizada solo por proveedores de Kubeflow administrado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un namespace de Kubernetes más enlaces de RBAC, cuotas de recursos y objetos Istio AuthorizationPolicy, reconciliados por el Profile Controller**

**Explicación:**
Un Kubeflow Profile es el límite de multi-tenancy: un namespace agrupado con enlaces de RBAC, cuotas y políticas de autorización de Istio, todo reconciliado desde un único recurso personalizado Profile por el Profile Controller. Otros componentes (Notebooks, Pipelines, Katib) crean sus recursos dentro del namespace de perfil de un usuario.
</details>

4. ¿Qué tres servicios nativos de AWS sustituye `awslabs/kubeflow-manifests` por Dex predeterminado de Kubeflow, MySQL en el clúster y MinIO?
   - A) IAM, DynamoDB y EFS
   - B) Cognito, RDS y S3
   - C) Secrets Manager, Aurora Serverless y EBS
   - D) SSO, Redshift y Glacier

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cognito, RDS y S3**

**Explicación:**
`awslabs/kubeflow-manifests` reemplaza Dex con Amazon Cognito para la autenticación, el MySQL incluido en el clúster con Amazon RDS para los metadatos de Pipelines/Katib y MinIO con Amazon S3 para el almacenamiento de artefactos de Pipelines. Tanto una implementación de manifiestos basada en kustomize como una implementación basada en Terraform documentan este patrón.
</details>

5. ¿Cuál es el historial documentado del soporte de IRSA para conceder a los Pods de Kubeflow Pipelines acceso a S3, específicamente para KFPv2?
   - A) IRSA siempre ha admitido completamente KFPv2 sin salvedades
   - B) IRSA nunca estuvo disponible en EKS para ninguna versión de Kubeflow Pipelines
   - C) Históricamente, el soporte de IRSA se retrasó para KFPv2, con una solución provisional basada en usuarios de IAM documentada mientras tanto, mientras que EKS Pod Identity es la dirección más amplia para los enlaces de IAM a Pods
   - D) KFPv2 requiere deshabilitar IAM por completo y utilizar acceso anónimo a S3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Históricamente, el soporte de IRSA se retrasó para KFPv2, con una solución provisional basada en usuarios de IAM documentada mientras tanto, mientras que EKS Pod Identity es la dirección más amplia para los enlaces de IAM a Pods**

**Explicación:**
Históricamente, la guía de `kubeflow-manifests` indicaba que IRSA era compatible con KFPv1, pero aún no con KFPv2, y recomendaba un usuario de IAM dedicado con credenciales estáticas como solución provisional. Por separado, EKS Pod Identity se ha convertido en el mecanismo predeterminado cada vez más recomendado para nuevos enlaces de IAM a Pods en EKS en general; sin embargo, el estado actual del soporte de Pod Identity específico para KFPv2 debe comprobarse en la documentación vigente en lugar de asumirse.
</details>

6. Según la disyuntiva sobre "por qué ejecutar esto en EKS en lugar de una alternativa administrada" analizada en este documento, ¿qué condición favorece más ejecutar Kubeflow en EKS en lugar de utilizar una plataforma completamente administrada como SageMaker?
   - A) El equipo desea evitar para siempre interactuar con controladores de Kubernetes o CRD
   - B) El equipo ya ejecuta cargas de trabajo mixtas en EKS y quiere que ML comparta los mismos grupos de nodos, escalado automático y pila de observabilidad
   - C) El equipo no tiene experiencia operativa previa con Kubernetes
   - D) El equipo desea la menor sobrecarga operativa posible independientemente de la portabilidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El equipo ya ejecuta cargas de trabajo mixtas en EKS y quiere que ML comparta los mismos grupos de nodos, escalado automático y pila de observabilidad**

**Explicación:**
Kubeflow en EKS se justifica más cuando un equipo ya opera otras cargas de trabajo en EKS y puede evitar mantener un segundo modelo operativo paralelo para ML, además de necesitar portabilidad/evitar la dependencia de un proveedor o un control detallado sobre los componentes internos de entrenamiento/servicio. Los equipos sin capacidad existente de Kubernetes, o aquellos que priorizan la mínima sobrecarga operativa, normalmente están mejor atendidos por una plataforma completamente administrada.
</details>

## Preguntas de respuesta corta

7. En una oración, explica qué señala sobre la madurez del proyecto de Kubeflow la graduación de CNCF (anunciada el 17 de agosto de 2026) y menciona un requisito concreto que el proyecto debió cumplir para alcanzarla.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
La graduación señala que un proyecto de CNCF ha demostrado madurez apta para producción, adopción amplia y una gobernanza sólida; para alcanzarla, Kubeflow se sometió a una auditoría de seguridad independiente realizada por terceros y formó un comité directivo formal para la gobernanza del proyecto. Consulta el [anuncio de CNCF](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/) para conocer todos los detalles.
</details>

8. ¿Por qué el patrón de implementación de `awslabs/kubeflow-manifests` reemplaza el almacén de artefactos MinIO en el clúster y la autenticación Dex incluida por S3 y Cognito respectivamente, al implementar Kubeflow en EKS?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Dado que EKS ya dispone de equivalentes administrados, duraderos e integrados con IAM para ambos — S3 para el almacenamiento de objetos y Cognito para la identidad — ejecutar las alternativas incluidas en el clúster implicaría operar servicios con estado adicionales que duplican capacidades que AWS ya proporciona, sin obtener nada que Kubeflow necesite específicamente de las versiones autohospedadas.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/01-architecture-installation.md) | [Siguiente cuestionario: Pipelines](./02-pipelines-quiz.md)
