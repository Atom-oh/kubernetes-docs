# Parte 6: KServe (serving de modelos en Kubernetes)

> **Referencia de revisión**: KServe 0.18.0 / Models Web Application 0.18.0 / Community Distribution 26.03.1
> **Última actualización**: October 12, 2026

## Configuración del entorno de laboratorio

Usa versiones compatibles de Kubernetes, el controlador/las CRD de KServe, ServingRuntime, acceso al almacenamiento y una ruta de red autenticada. No se requiere Kubeflow completo; la aplicación web es opcional. El modo Knative necesita Knative Serving/networking; la ruta KEDA de Standard necesita KEDA y proveedores de métricas. El uso de GPU depende de la carga de trabajo.

## KServe y Kubeflow

KServe evolucionó a partir de KFServing hasta convertirse en un proyecto de serving independiente. En este capítulo se revisan **KServe y Models Web Application 0.18.0**, incluidos en Community Distribution 26.03.1.

La versión pública más reciente de KServe consultada el 12 de octubre de 2026 es **0.21.0 (25 de septiembre de 2026)**. La versión 0.20.0 (6 de agosto de 2026) se publicó antes. Ninguna de las dos versiones corresponde a la referencia 0.18.0 de la distribución.

El controlador, las CRD y la aplicación web son artefactos independientes que requieren comprobaciones de compatibilidad. Sus números de versión no tienen por qué coincidir ni ser siempre distintos. Registra las imágenes reales, los esquemas de las CRD y las revisiones de la aplicación web.

`InferenceService` es la API de serving que se aborda aquí, no toda la arquitectura de KServe. ServingRuntime/ClusterServingRuntime, ModelMesh y la API LLMInferenceService independiente tienen diferentes dependencias y modelos operativos.

## InferenceService: Predictor, Transformer y Explainer

InferenceService requiere un predictor y admite, de forma opcional, un transformer y un explainer. Predictor configura el servidor del modelo, transformer proporciona el preprocesamiento y posprocesamiento, y explainer gestiona las solicitudes de explicación. Las explicaciones no se adjuntan automáticamente a cada predicción; la compatibilidad del runtime y el protocolo es importante.

Haz coincidir modelFormat, ServingRuntime, la estructura de archivos/la versión de la biblioteca, URI/credenciales, puertos/sondas y el protocolo de solicitud. Una URI por sí sola no permite servir cualquier modelo. Los contenedores personalizados también deben cumplir el contrato del cliente y los requisitos de enrutamiento y comprobación de estado de KServe.

El chart oficial de configuración de runtimes no genera recursos de forma predeterminada. Al renderizar con `kserve.servingruntime.enabled=true` se generan 12 ClusterServingRuntimes. La presencia en el catálogo no garantiza que las imágenes estén actualizadas, que cuenten con soporte de seguridad ni que sean compatibles con el modelo.

El [aviso del proyecto](https://github.com/pytorch/serve) de TorchServe indica que no se prevén nuevas funciones, correcciones de errores ni parches de seguridad. Su presencia en un catálogo de runtimes antiguo no lo convierte en una opción predeterminada mantenida para nuevos usos en producción. Valida un runtime mantenido que sea adecuado para el formato del modelo y los requisitos de GPU.

## Modos de implementación: Knative y Standard

Los nombres de la versión 0.18.0 son **Knative** y **Standard**. Los valores de anotación Serverless y RawDeployment son alias obsoletos que se normalizan a esos nombres. Inspecciona serving.kserve.io/deploymentMode y el inferenceservice-config instalado. La alternativa predeterminada en el código es Standard, mientras que el chart de recursos OCI descargado tiene Knative como valor predeterminado. No deduzcas los valores predeterminados de la instalación basándote solo en la terminología.

| Elemento | Knative | Standard |
| --- | --- | --- |
| Recursos de carga de trabajo | Ruta de Knative Service/Revision | Deployment/Service y el autoscaler seleccionado |
| Reducción de escala | Es posible llegar a cero con compatibilidad con KPA/policies y minReplicas=0 | La ruta HPA predeterminada conserva al menos una réplica; KEDA puede permitir llegar a cero si se dispone de señales externas de activación adecuadas |
| minReplicas predeterminado | KServe establece el valor predeterminado en uno; elegir Knative por sí solo no habilita llegar a cero | HPA limita a un mínimo de uno el valor cero solicitado |
| Dependencias | Knative Serving/networking y el autoscaler seleccionado | Ingress/gateway elegido, métricas de HPA o KEDA, etc. |
| Latencia de inicio | La programación, la carga de imágenes y la carga del modelo cuando se parte de cero | Los reinicios, los despliegues progresivos y el escalado horizontal siguen teniendo latencia de inicio, incluso con réplicas en caliente |

Ninguno de los modos garantiza que haya réplicas disponibles ni ofrece un SLA de latencia. Valida la carga del modelo, la preparación, la capacidad, los tiempos de espera y la recuperación. El escalado desde cero con KEDA requiere una señal observable sin Pods en ejecución y una ruta de reactivación; las métricas de CPU/memoria por sí solas no implican una activación basada en solicitudes.

![La reconciliación de InferenceService es independiente de las solicitudes a los servidores de modelos en ejecución; las rutas Knative y Standard muestran un comportamiento de escalado automático condicional.](../../.gitbook/assets/en-ai-ml-kubeflow-06-kserve-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-06-kserve-0.html)

## Escalado automático y métricas

Knative KPA admite concurrencia/RPS, mientras que la clase HPA de Knative es otra alternativa. Standard selecciona hpa, keda o external/none mediante serving.kserve.io/autoscalerClass. No todas las implementaciones Standard crean un HPA.

Las métricas de CPU, externas o de Pod compatibles necesitan dependencias reales de metrics-server/adapter/proveedor. Las solicitudes de GPU no generan automáticamente métricas de GPU. La velocidad de respuesta depende de los intervalos de observación, la estabilización y el comportamiento del modelo; las métricas de concurrencia no son siempre más rápidas.

## Actualizaciones graduales y tráfico canary

Se verificó que canaryTrafficPercent de esta versión funciona con la **ruta de división del tráfico entre Revisiones de Knative**. KServe establece la revisión anterior implementada y la nueva como destinos del tráfico de Knative Service; Knative networking distribuye las solicitudes. El controlador de KServe no actúa como proxy para cada solicitud de inferencia.

No equipares una actualización progresiva de Deployment en Standard con ese enrutamiento basado en porcentajes por revisión. El enrutamiento ponderado en Standard requiere servicios/gateway/mesh o herramientas de despliegue gradual diseñados por separado, además de una titularidad bien definida. Al usar [la gestión del tráfico de Istio](../../service-mesh/istio/traffic-management/04-traffic-splitting.md) o [Argo Rollouts](../../service-mesh/istio/advanced/08-argo-rollouts.md), evita que haya titularidad en conflicto sobre los objetos gestionados por KServe.

Un porcentaje por sí solo no valida la calidad ni automatiza la promoción o la reversión. Comprueba las métricas de comparación, los errores y la latencia, las revisiones y los artefactos del modelo que se conservan, y la disponibilidad de las rutas.

## Inferencia con GPU en EKS

Una solicitud nvidia.com/gpu de un Pod permite la programación y la asignación del dispositivo. La inferencia real con GPU requiere CUDA/controladores compatibles, una imagen de servidor, un backend de modelo y una configuración del dispositivo compatibles. Revisa la configuración del modelo de Triton o la selección del dispositivo del framework; una solicitud de GPU no traslada automáticamente un modelo de CPU a la GPU.

Karpenter aprovisiona recursos para Pods Pending aptos, NodePools, cuotas y capacidad disponible. El escalado de Pods de KServe/Knative/HPA/KEDA y el aprovisionamiento/reclamación de instancias EC2 son ciclos independientes. Incluso cuando hay cero Pods de modelos, otras cargas de trabajo o las políticas de disrupción pueden mantener los nodos y los costes activos.

## Validación y fuentes

Se descargaron y renderizaron localmente los charts OCI oficiales de CRD, recursos y configuración de runtimes de la versión 0.18.0 para inspeccionar el esquema y la configuración. Se revisaron los alias de modo, los mínimos de HPA, ScaledObject de KEDA y el código de tráfico de Knative. No se ejecutó ninguna descarga ni serving de modelos, prueba de GPU, escalado automático del clúster ni solicitud canary en directo.

- [Nombres de modos y valores predeterminados de 0.18.0](https://github.com/kserve/kserve/blob/v0.18.0/pkg/constants/constants.go)
- [Gestión del número mínimo de réplicas de HPA](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/hpa/hpa_reconciler.go)
- [Gestión de ScaledObject de KEDA](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/keda/keda_reconciler.go)
- [Gestión del tráfico de Knative](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/knative/ksvc_reconciler.go)
- [Versión 0.20.0](https://github.com/kserve/kserve/releases/tag/v0.20.0)
- [Versión 0.21.0 (la más reciente consultada)](https://github.com/kserve/kserve/releases/tag/v0.21.0)

## Próximos pasos

Conecta esta ruta de serving con los capítulos sobre arquitectura, Pipelines, Notebooks, Katib y Trainer de la [serie de Kubeflow](README.md), tratando la implementación y validación de los artefactos del modelo como pasos independientes.

---

[Volver a la página principal](./README.md)

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, prueba el [cuestionario del tema](../../quizzes/ai-ml/kubeflow/06-kserve-quiz.md).
