# Cuestionario de KServe

Referencia: KServe 0.18.0 / Community Distribution 26.03.1.

## Preguntas de opción múltiple

1. ¿Cómo se relaciona KServe con Kubeflow?

   - A) Evolucionó de KFServing y puede ejecutarse de forma independiente con sus dependencias
   - B) Es un nuevo nombre para Katib
   - C) Siempre requiere la distribución completa de Kubeflow
   - D) Reemplaza a Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Evolucionó de KFServing y puede ejecutarse de forma independiente con sus dependencias**

Kubeflow completo y la Models Web Application no son requisitos previos para todas las instalaciones de KServe.
</details>

2. ¿Qué versiones revisa este capítulo?

   - A) Solo la aplicación web en 0.16.1
   - B) KServe y la aplicación web 0.18.0 en Community 26.03.1; el KServe más reciente comprobado el 2026-10-12 es 0.21.0
   - C) Todos los componentes deben tener versiones diferentes
   - D) La etiqueta de la aplicación web determina todos los CRDs instalados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) KServe y la aplicación web 0.18.0 en Community 26.03.1; el KServe más reciente comprobado el 2026-10-12 es 0.21.0**

El controlador, los CRDs y la aplicación web son artefactos independientes. Se deben registrar su compatibilidad y revisiones reales.
</details>

3. ¿Qué componente de InferenceService es obligatorio?

   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) Los tres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Predictor**

Transformer y explainer son opcionales; la compatibilidad del entorno de ejecución y del protocolo, así como las rutas de explicación reales, siguen siendo importantes.
</details>

4. ¿Al seleccionar Knative todos los predictores inactivos se escalan automáticamente a cero?

   - A) Sí, sin configuración
   - B) No; KServe establece minReplicas en 1 de forma predeterminada y el escalado a cero requiere parámetros compatibles del autoescalador o de la política, como minReplicas 0
   - C) Sí, y la facturación de EC2 se detiene inmediatamente
   - D) No se necesita una instalación de Knative

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; KServe establece minReplicas en 1 de forma predeterminada y el escalado a cero requiere parámetros compatibles del autoescalador o de la política, como minReplicas 0**

El escalado desde cero implica aprovisionar capacidad y cargar la imagen y el modelo. Tener cero Pods no garantiza que se retiren los nodos.
</details>

5. ¿Qué afirmación sobre el modo Standard es correcta?

   - A) Garantiza una réplica saludable y activa en todo momento
   - B) Usa Deployment/Service; el HPA predeterminado conserva al menos 1, mientras que una ruta KEDA configurada puede admitir cero
   - C) Siempre requiere Knative
   - D) No admite opciones de escalado automático

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa Deployment/Service; el HPA predeterminado conserva al menos 1, mientras que una ruta KEDA configurada puede admitir cero**

KEDA requiere instalación, métricas y activadores válidos, además de una ruta de activación. En ambos modos persiste la latencia de inicio causada por reinicios, actualizaciones graduales o escalado horizontal.
</details>

6. ¿Cuáles son los nombres de modo modernos en 0.18.0?

   - A) Serverless y RawDeployment son los únicos nombres válidos
   - B) Knative y Standard; los nombres antiguos son alias obsoletos
   - C) HPA y GPU
   - D) Predictor y Transformer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Knative y Standard; los nombres antiguos son alias obsoletos**

Inspeccione la anotación y la configuración reales. El valor alternativo del código es Standard; el chart de recursos OCI inspeccionado usa Knative de forma predeterminada.
</details>

7. ¿Qué implementa la ruta verificada de canaryTrafficPercent?

   - A) El controlador de KServe actúa como proxy de todas las solicitudes por sí mismo
   - B) KServe establece los destinos de tráfico de revisión de Knative; las redes de Knative enrutan las solicitudes
   - C) Todo Deployment Standard tiene automáticamente la misma división por revisión
   - D) Argo Rollouts es obligatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) KServe establece los destinos del tráfico entre revisiones de Knative; la capa de red de Knative enruta las solicitudes**

La actualización gradual de Standard no es el mismo mecanismo de porcentaje por revisión. La promoción/reversión y los artefactos conservados requieren validación independiente.
</details>

8. ¿Solicitar nvidia.com/gpu garantiza la inferencia mediante GPU?

   - A) Sí, para todos los modelos
   - B) No; los controladores, la imagen o el backend y la configuración del modelo y del dispositivo también deben coincidir
   - C) Instala automáticamente todos los controladores necesarios
   - D) Elimina la necesidad de capacidad de nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; los controladores, la imagen o el backend y la configuración del modelo y del dispositivo también deben coincidir**

La asignación de recursos y la ejecución real del modelo son aspectos distintos. Karpenter proporciona capacidad apta, sujeta a políticas, cuotas y disponibilidad.
</details>

## Preguntas de respuesta corta

9. ¿Por qué «siempre activo» frente a «escalado a cero» no es una distinción absoluta entre los dos modos?

<details>
<summary>Mostrar respuesta</summary>

Knative puede conservar réplicas activas mediante configuraciones mínimas, y Standard puede usar KEDA con una señal externa adecuada. Ningún modo garantiza disponibilidad ni latencia; pruebe la preparación para recibir tráfico, la carga del modelo, la capacidad y la recuperación.
</details>

10. ¿Por qué un URI de artefacto por sí solo es insuficiente y cómo se debe tratar TorchServe?

<details>
<summary>Mostrar respuesta</summary>

El entorno de ejecución, el formato y la estructura del modelo, la versión de la biblioteca, las credenciales, los puertos y el protocolo deben coincidir. TorchServe indica que ya no recibe mantenimiento activo ni se planean correcciones de seguridad, por lo que una entrada antigua del catálogo de entornos de ejecución no demuestra que la opción predeterminada siga recibiendo mantenimiento.
</details>

11. ¿Cómo interactúan el escalado automático de Pods y el escalado de EC2?

<details>
<summary>Mostrar respuesta</summary>

Knative/HPA/KEDA u otro escalador configurado determina la cantidad deseada de Pods. La planificación de Kubernetes y las políticas de capacidad de Karpenter afectan el aprovisionamiento y la retirada de nodos. Otras cargas de trabajo o reglas de interrupción pueden mantener facturados los nodos de EC2 después de que los Pods del modelo lleguen a cero.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/06-kserve.md)
