# Cuestionario sobre Inference Frameworks

15preguntas sobre las APIs actuales y los límites de ejecución.

## 1. ¿Qué proporciona NIM y qué se debe verificar?

<details>
<summary>Respuesta y explicación</summary>

Contenedores y perfiles orientados a modelos/dispositivos. NIM no siempre es TensorRT-LLM; verifique las revisiones de contenedor/modelo, los dispositivos compatibles, el acuerdo de soporte, la autenticación, la caché y las métricas.
</details>

## 2. ¿Qué es el serving desagregado de Dynamo?

<details>
<summary>Respuesta y explicación</summary>

Workers de prefill y decode separados conectados mediante una transferencia de KV compatible. El modelo, el formato KV, el backend, el dispositivo y la red deben coincidir; las mejoras de velocidad o costo dependen de la carga de trabajo.
</details>

## 3. ¿Cómo se declara un adaptador LoRA en AIBrix0.7.0?

<details>
<summary>Respuesta y explicación</summary>

Use ModelAdapter con baseModel, podSelector y artifactURL. Omitir replicas significa todos los Pods coincidentes;1 significa un Pod; otros valores no son compatibles. Los nombres de adaptadores no autentican a los tenants.
</details>

## 4. ¿Qué capas de controller y scaling operan Ray Serve en Kubernetes?

<details>
<summary>Respuesta y explicación</summary>

KubeRay reconcilia los recursos Ray; el autoscaling de Ray ajusta los workers y el autoscaling de Serve ajusta las réplicas de serving. No trate RayCluster como un objetivo HPA ordinario de Deployment.
</details>

## 5. ¿Cómo se deben evaluar el costo y el hardware de Inf2?

<details>
<summary>Respuesta y explicación</summary>

Mida el mismo modelo, SLO, throughput exitoso y precios con fecha. Cada chip tiene2cores/32GiB HBM. inf2.24xlarge tiene6chips/12cores/192GiB HBM;48xlarge tiene12/24/384GiB. La RAM del host es independiente.
</details>

## 6. ¿En qué se diferencian TTFT, ITL y la latencia end-to-end?

<details>
<summary>Respuesta y explicación</summary>

TTFT mide el tiempo hasta el primer token; ITL mide los intervalos entre tokens posteriores. La aproximación de intervalo uniforme es TTFT+(output tokens-1)×ITL más la sobrecarga independiente. Use SLO específicos para la carga de trabajo y unidades reales.
</details>

## 7. ¿Qué considera el routing con reconocimiento de KV de Dynamo?

<details>
<summary>Respuesta y explicación</summary>

La localidad de caché y la carga de los workers. Una fórmula fija de0.7/0.3 o la suposición de una caché solo para decode no son universales; inspeccione el backend y la política de routing reales.
</details>

## 8. ¿Qué se debe comprobar antes de instalar el device plugin de Neuron?

<details>
<summary>Respuesta y explicación</summary>

Renderice un chart oficial fijado e inspeccione los drivers, RBAC/hostPaths, los componentes habilitados y los DaemonSets reales. neuron asigna dispositivos completos; neuroncore asigna cores.
</details>

## 9. ¿Cuál es la forma de configuración del autoscaler de AIBrix?

<details>
<summary>Respuesta y explicación</summary>

PodAutoscaler usa scaleTargetRef, metricsSources y estrategias HPA/KPA/APA. Se requieren un controller y una fuente de métricas real; un ConfigMap o una solicitud de GPU por sí solos no escalan las cargas de trabajo.
</details>

## 10. ¿Cuáles son los roles de NGC/profile y los límites de credenciales?

<details>
<summary>Respuesta y explicación</summary>

Identifique los modelos, las imágenes y los perfiles compatibles. NIM_MODEL_PROFILE debe usar un ID/nombre de perfil real. Distinga las credenciales de image-pull de las de runtime-download; la entrega de secretos mediante variables de entorno no satisface una política que solo admite archivos.
</details>

## 11. ¿El soporte para múltiples backends implica una combinación arbitraria?

<details>
<summary>Respuesta y explicación</summary>

No. Valide el vLLM/SGLang/TensorRT-LLM, dispositivo, connector, modelo y formato KV elegidos. La coincidencia de nombres de modelos por sí sola no establece la interoperabilidad entre prefill/decode.
</details>

## 12. ¿Cómo se debe seleccionar la caché de modelos?

<details>
<summary>Respuesta y explicación</summary>

Compare local/EBS/EFS/FSx usando tamaño, revisión, concurrencia de reinicio/descarga, autorización y costo. No comparta un PVC RWO de EBS entre nodos; incorporar modelos en una imagen puede ser apropiado bajo restricciones específicas.
</details>

## 13. ¿Qué importa en los comandos y resultados de GenAI-Perf?

<details>
<summary>Respuesta y explicación</summary>

La versión0.0.16 usa profile y synthetic-input-tokens-mean/output-tokens-mean. analyze puede ejecutar una carga de sweep adicional. Conserve los resultados sin procesar, los fallos, el warmup y el tokenizer; la utilización de GPU requiere una recopilación configurada.
</details>

## 14. ¿StatefulSet por sí solo implementa vLLM distribuido?

<details>
<summary>Respuesta y explicación</summary>

No. Los nombres estables pueden ayudar, pero rank, rendezvous, TP/PP, el modelo y la comunicación necesitan configuración explícita. Compruebe los deadlocks de disponibilidad ordenada; otros controllers también pueden ser apropiados.
</details>

## 15. ¿Cómo se relaciona NEURON_RT_VISIBLE_CORES con la asignación de Kubernetes?

<details>
<summary>Respuesta y explicación</summary>

Selecciona cores de runtime y no crea dispositivos sin asignar. inf2.xlarge tiene un dispositivo, por lo que neuron:2 no se puede programar. Distinga NxD de SDK2.32 para Inf2 de la nueva ruta beta de Trn2/3.
</details>

[Volver a la guía](../../ai-ml/04-inference-frameworks.md)
