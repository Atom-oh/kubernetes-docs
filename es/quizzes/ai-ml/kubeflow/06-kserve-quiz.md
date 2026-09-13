# Cuestionario de KServe

Línea base: KServe 0.18.0 / Community Distribution 26.03.1.

## Preguntas de opción múltiple

1. ¿Cómo se relaciona KServe con Kubeflow?

   - A) Evolucionó de KFServing y puede ejecutarse de forma independiente con sus dependencias
   - B) Es un nuevo nombre para Katib
   - C) Siempre requiere toda la distribución de Kubeflow
   - D) Reemplaza a Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Evolucionó de KFServing y puede ejecutarse de forma independiente con sus dependencias**

Kubeflow completo y la Models Web Application no son requisitos previos para todas las instalaciones de KServe.
</details>

2. ¿Qué versiones revisa este capítulo?

   - A) Solo la aplicación web en 0.16.1
   - B) KServe y la aplicación web 0.18.0 en Community 26.03.1; el KServe más reciente inspeccionado es 0.20.0
   - C) Todos los componentes deben tener versiones diferentes
   - D) La etiqueta de la aplicación web determina todos los CRD instalados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) KServe y la aplicación web 0.18.0 en Community 26.03.1; el KServe más reciente inspeccionado es 0.20.0**

El Controller, los CRD y la aplicación web son artefactos independientes. Se debe registrar su compatibilidad y revisiones reales.
</details>

3. ¿Qué componente de InferenceService es obligatorio?

   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) Los tres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Predictor**

Transformer y explainer son opcionales; la compatibilidad de runtime/protocolo y las rutas de explicación reales siguen siendo importantes.
</details>

4. ¿Seleccionar Knative escala automáticamente a cero cada predictor inactivo?

   - A) Sí, sin configuración
   - B) No; KServe establece de forma predeterminada minReplicas en 1 y el escalado a cero requiere configuraciones compatibles de autoscaler/política, como minReplicas 0
   - C) Sí, y la facturación de EC2 se detiene inmediatamente
   - D) No se necesita ninguna instalación de Knative

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; KServe establece de forma predeterminada minReplicas en 1 y el escalado a cero requiere configuraciones compatibles de autoscaler/política, como minReplicas 0**

El escalado desde cero incluye la carga de capacidad, imagen y modelo. Que los Pods estén en cero no garantiza la terminación de los nodos.
</details>

5. ¿Qué afirmación sobre el modo Standard es correcta?

   - A) Garantiza una réplica saludable y en caliente en todo momento
   - B) Usa Deployment/Service; el HPA predeterminado retiene al menos 1, mientras que una ruta KEDA configurada puede admitir cero
   - C) Siempre requiere Knative
   - D) No admite opciones de autoscaling

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa Deployment/Service; el HPA predeterminado retiene al menos 1, mientras que una ruta KEDA configurada puede admitir cero**

KEDA necesita instalación, métricas/triggers válidos y una ruta de activación. La latencia de inicio por reinicio/rollout/scale-out se mantiene en ambos modos.
</details>

6. ¿Cuáles son los nombres de modo modernos en 0.18.0?

   - A) Serverless y RawDeployment son los únicos nombres válidos
   - B) Knative y Standard; los nombres antiguos son alias obsoletos
   - C) HPA y GPU
   - D) Predictor y Transformer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Knative y Standard; los nombres antiguos son alias obsoletos**

Inspeccione la anotación y la configuración reales. El respaldo de código es Standard; el chart de recursos OCI inspeccionado usa Knative de forma predeterminada.
</details>

7. ¿Qué implementa la ruta verificada canaryTrafficPercent?

   - A) El Controller de KServe actúa como proxy de todas las solicitudes por sí mismo
   - B) KServe establece destinos de tráfico de revisión de Knative; la red de Knative enruta las solicitudes
   - C) Cada Deployment Standard tiene automáticamente la misma división por revisión
   - D) Argo Rollouts es obligatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) KServe establece destinos de tráfico de revisión de Knative; la red de Knative enruta las solicitudes**

La actualización continua de Standard no es el mismo mecanismo de porcentaje por revisión. La promoción/reversión y los artefactos retenidos necesitan validación independiente.
</details>

8. ¿Solicitar nvidia.com/gpu garantiza la inferencia con GPU?

   - A) Sí, para todos los modelos
   - B) No; los drivers, la imagen/backend y la configuración del modelo/dispositivo también deben coincidir
   - C) Instala automáticamente todos los drivers necesarios
   - D) Elimina la necesidad de capacidad de nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; los drivers, la imagen/backend y la configuración del modelo/dispositivo también deben coincidir**

La asignación de recursos y la ejecución real del modelo son cosas distintas. Karpenter proporciona capacidad apta sujeta a políticas, cuotas y disponibilidad.
</details>

## Preguntas de respuesta corta

9. ¿Por qué siempre en caliente frente al escalado a cero no es una distinción absoluta entre los dos modos?

<details>
<summary>Mostrar respuesta</summary>

Knative puede retener réplicas en caliente mediante configuraciones mínimas, y Standard puede usar KEDA con una señal externa adecuada. Ningún modo garantiza disponibilidad o latencia; pruebe la preparación, carga, capacidad y recuperación.
</details>

10. ¿Por qué una URI de artefacto por sí sola es insuficiente y cómo debe tratarse TorchServe?

<details>
<summary>Mostrar respuesta</summary>

El runtime, el formato/disposición del modelo, la versión de la biblioteca, las credenciales, los puertos y el protocolo deben coincidir. TorchServe indica que ya no recibe mantenimiento activo y no tiene correcciones de seguridad planificadas, por lo que una entrada antigua del catálogo de runtime no demuestra que sea una opción predeterminada mantenida.
</details>

11. ¿Cómo interactúan el autoscaling de Pods y el escalado de EC2?

<details>
<summary>Mostrar respuesta</summary>

Knative/HPA/KEDA u otro scaler configurado determina los Pods deseados. La programación de Kubernetes y las políticas de capacidad de Karpenter afectan el aprovisionamiento/la recuperación de nodos. Otras cargas de trabajo o reglas de interrupción pueden mantener facturados los nodos de EC2 después de que los Pods del modelo lleguen a cero.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/06-kserve.md)
