# Cuestionario sobre marcos de inferencia

15 preguntas sobre las API actuales y los límites de ejecución.

## 1. ¿Qué proporciona NIM y qué se debe verificar?

<details>
<summary>Respuesta y explicación</summary>

Contenedores y perfiles optimizados para modelos y dispositivos. NIM no siempre es TensorRT-LLM; verifica las revisiones de contenedor y modelo, los dispositivos compatibles, el acuerdo de soporte, la autenticación, la caché y las métricas.
</details>

## 2. ¿Qué es el servicio de inferencia desagregado de Dynamo?

<details>
<summary>Respuesta y explicación</summary>

Los workers de prefill y decode se ejecutan por separado y se conectan mediante un mecanismo compatible de transferencia de KV. Deben ser compatibles el modelo, el formato de KV, el backend, el dispositivo y la red; las mejoras de velocidad o coste dependen de la carga de trabajo.
</details>

## 3. ¿Cómo se declara un adaptador LoRA en AIBrix 0.7.0?

<details>
<summary>Respuesta y explicación</summary>

Usa `ModelAdapter` con `baseModel`, `podSelector` y `artifactURL`. Si se omite `replicas`, se aplica a todos los Pods coincidentes; con el valor `1`, se aplica a un solo Pod. Los demás valores no son compatibles. El nombre de un adaptador no autentica a los tenants.
</details>

## 4. ¿Qué capas de controladores y escalado operan Ray Serve en Kubernetes?

<details>
<summary>Respuesta y explicación</summary>

KubeRay reconcilia los recursos de Ray; el autoscalado de Ray ajusta los workers y el de Serve ajusta las réplicas de servicio. No trates `RayCluster` como un destino ordinario de HPA para un `Deployment`.
</details>

## 5. ¿Cómo se deben evaluar el costo y el hardware de Inf2?

<details>
<summary>Respuesta y explicación</summary>

Mide el mismo modelo, SLO, caudal de solicitudes atendidas correctamente y precios con fecha. Cada chip tiene 2 núcleos y 32 GiB de HBM. `inf2.24xlarge` tiene 6 chips, 12 núcleos y 192 GiB de HBM; `48xlarge` tiene 12 chips, 24 núcleos y 384 GiB de HBM. La RAM del host es independiente.
</details>

## 6. ¿En qué se diferencian TTFT, ITL y la latencia de extremo a extremo?

<details>
<summary>Respuesta y explicación</summary>

TTFT mide el tiempo hasta el primer token; ITL mide los intervalos entre los tokens siguientes. Si el intervalo es uniforme, la latencia se aproxima a `TTFT + (tokens de salida - 1) × ITL`, más la sobrecarga adicional. Usa SLO específicos para la carga de trabajo y unidades reales.
</details>

## 7. ¿Qué factores considera el enrutamiento de Dynamo sensible a KV?

<details>
<summary>Respuesta y explicación</summary>

La localidad de la caché y la carga de los workers. Una fórmula fija de `0.7/0.3` o suponer que la caché solo se usa para decode no sirve para todos los casos; inspecciona el backend y la política de enrutamiento reales.
</details>

## 8. ¿Qué se debe comprobar antes de instalar el complemento de dispositivos de Neuron?

<details>
<summary>Respuesta y explicación</summary>

Renderiza un chart oficial con versión fijada e inspecciona los controladores, RBAC/`hostPaths`, los componentes habilitados y los DaemonSets reales. El recurso `neuron` asigna dispositivos completos; `neuroncore` asigna núcleos.
</details>

## 9. ¿Cuál es la forma de configuración del autoscaler de AIBrix?

<details>
<summary>Respuesta y explicación</summary>

`PodAutoscaler` usa `scaleTargetRef`, `metricsSources` y las estrategias HPA/KPA/APA. Se necesitan un controlador y una fuente de métricas real; un ConfigMap o una solicitud de GPU por sí solos no escalan las cargas de trabajo.
</details>

## 10. ¿Cuáles son los roles de NGC/profile y los límites de credenciales?

<details>
<summary>Respuesta y explicación</summary>

Identifica los modelos, las imágenes y los perfiles compatibles. `NIM_MODEL_PROFILE` debe contener el ID o el nombre de un perfil real. Distingue las credenciales para extraer imágenes de las credenciales para descargar el runtime; entregar secretos mediante variables de entorno no cumple una política que solo admite archivos.
</details>

## 11. ¿El soporte para múltiples backends implica una combinación arbitraria?

<details>
<summary>Respuesta y explicación</summary>

No. Valida cada backend elegido entre `vLLM`, `SGLang` y `TensorRT-LLM`, así como el dispositivo, el conector, el modelo y el formato de KV. Que coincidan los nombres de los modelos no demuestra por sí solo la interoperabilidad entre prefill y decode.
</details>

## 12. ¿Cómo se debe seleccionar la caché de modelos?

<details>
<summary>Respuesta y explicación</summary>

Compara el almacenamiento local, EBS, EFS y FSx según el tamaño, la revisión, la concurrencia de reinicios y descargas, la autorización y el coste. No compartas entre nodos un PVC de EBS con modo de acceso RWO. Incluir los modelos en una imagen puede ser adecuado si se cumplen ciertas restricciones.
</details>

## 13. ¿Qué importa en los comandos y resultados de GenAI-Perf?

<details>
<summary>Respuesta y explicación</summary>

La versión 0.0.16 usa `profile` y `synthetic-input-tokens-mean`/`output-tokens-mean`. `analyze` puede ejecutar pruebas de carga adicionales en modo de barrido. Conserva los resultados sin procesar, los fallos, el calentamiento inicial y el tokenizador; para medir la utilización de la GPU, hay que configurar su recopilación.
</details>

## 14. ¿StatefulSet por sí solo implementa vLLM distribuido?

<details>
<summary>Respuesta y explicación</summary>

No. Los nombres estables pueden ayudar, pero el `rank`, el encuentro de procesos (`rendezvous`), TP/PP, el modelo y la comunicación necesitan una configuración explícita. Comprueba si la disponibilidad ordenada causa bloqueos; otros controladores también pueden ser adecuados.
</details>

## 15. ¿Cómo se relaciona NEURON_RT_VISIBLE_CORES con la asignación de Kubernetes?

<details>
<summary>Respuesta y explicación</summary>

Selecciona núcleos para el runtime; no crea dispositivos que no se hayan asignado. `inf2.xlarge` tiene un dispositivo, por lo que `neuron:2` no se puede programar. Distingue NxD de SDK 2.32 para Inf2 de la nueva ruta beta para Trn2/3.
</details>

[Volver a la guía](../../ai-ml/04-inference-frameworks.md)
