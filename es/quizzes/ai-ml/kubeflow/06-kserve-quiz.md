# Parte 6: KServe — Cuestionario sobre Model Serving en Kubernetes

Este cuestionario evalúa tu comprensión de la relación de KServe con Kubeflow, los componentes de `InferenceService`, la disyuntiva entre Serverless y Raw Deployment, los mecanismos de autoscaling, los despliegues canary y la inferencia con GPU en EKS.

## Preguntas de opción múltiple

1. ¿Cuál es la relación histórica entre KServe y Kubeflow?
   - A) KServe siempre fue un proyecto completamente independiente sin conexión con Kubeflow
   - B) KServe comenzó dentro de Kubeflow como KFServing y luego se independizó como su propio proyecto autónomo de primer nivel
   - C) Kubeflow es un subcomponente de KServe
   - D) KServe es un cambio de marca de Katib

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) KServe comenzó dentro de Kubeflow como KFServing y luego se independizó como su propio proyecto autónomo de primer nivel**

**Explicación:**
KServe comenzó como KFServing, un componente dentro de Kubeflow responsable de convertir modelos entrenados en endpoints de inferencia. Posteriormente se convirtió en un proyecto independiente y autónomo que puede instalarse en cualquier clúster de Kubernetes sin Kubeflow, mientras que Kubeflow sigue incluyéndolo como su capa predeterminada de model serving.
</details>

2. ¿Por qué no puedes asumir que la versión del controller/CRD de KServe coincide con la versión mostrada para la aplicación web de KServe en el dashboard de Kubeflow?
   - A) El dashboard de Kubeflow nunca muestra información de versión de KServe
   - B) KServe tiene su propia cadencia de lanzamientos independiente del ciclo de lanzamientos versionado por calendario de Kubeflow Community Distribution, por lo que un equipo de plataforma puede actualizar el controller independientemente de la aplicación web
   - C) KServe está obsoleto y ya no recibe actualizaciones de versión
   - D) La aplicación web de Kubeflow y el controller de KServe son siempre exactamente el mismo binario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) KServe tiene su propia cadencia de lanzamientos independiente del ciclo de lanzamientos versionado por calendario de Kubeflow Community Distribution, por lo que un equipo de plataforma puede actualizar el controller independientemente de la aplicación web**

**Explicación:**
Kubeflow Community Distribution 26.03 incluye la aplicación web de KServe en la versión v0.16.1, pero ese número describe la integración con el dashboard, no necesariamente la versión subyacente del controller/CRD de KServe que se ejecuta en el clúster, ya que el controller puede actualizarse según su propio calendario.
</details>

3. ¿Qué componente de `InferenceService` es obligatorio y los demás opcionales?
   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) Los tres son obligatorios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Predictor**

**Explicación:**
El predictor es el propio servidor de modelos y es el único componente obligatorio de un `InferenceService`. El transformer (pre/postprocesamiento) y el explainer (explicaciones del modelo) son complementos opcionales que se usan solo cuando el caso de uso los requiere.
</details>

4. ¿Cuál es la capacidad definitoria del modo de despliegue Serverless de KServe y cuál es su coste?
   - A) Usa un Deployment y HPA simples, sin ninguna desventaja
   - B) Escala los Pods a cero mediante Knative cuando están inactivos, a costa de latencia de inicio en frío al escalar
   - C) No requiere ningún clúster de Kubernetes
   - D) Elimina la necesidad de un predictor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Escala los Pods a cero mediante Knative cuando están inactivos, a costa de latencia de inicio en frío al escalar**

**Explicación:**
El modo Serverless delega el ciclo de vida de los Pods a Knative Serving, que puede escalar los Pods de predictor (y transformer/explainer) hasta cero cuando no hay tráfico, lo que ahorra el coste de GPU inactivas. La desventaja es la latencia de inicio en frío: programar un nuevo Pod, iniciar el contenedor y cargar el artefacto del modelo requieren tiempo antes de poder responder a la primera solicitud después de escalar desde cero.
</details>

5. ¿Cuál es la diferencia clave entre el modo Raw Deployment y el modo Serverless?
   - A) El modo Raw Deployment administra un Deployment/Service simple (y HPA opcional) sin dependencia de Knative y sin escalado a cero
   - B) El modo Raw Deployment requiere Knative Serving, pero agrega un transformer automáticamente
   - C) El modo Raw Deployment solo está disponible para modelos SKLearn
   - D) El modo Raw Deployment siempre ejecuta más réplicas que el modo Serverless

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El modo Raw Deployment administra un Deployment/Service simple (y HPA opcional) sin dependencia de Knative y sin escalado a cero**

**Explicación:**
El modo Raw Deployment es operativamente más sencillo (no hay Knative que instalar o actualizar) y evita por completo los inicios en frío, pero nunca escala por debajo del número mínimo de réplicas configurado para el Deployment, por lo que al menos esa cantidad de Pods de predictor (y sus GPU, si las hay) siempre se ejecutan independientemente del tráfico.
</details>

6. ¿Cómo difiere el autoscaling entre los dos modos de despliegue?
   - A) Ambos modos usan exactamente el mismo escalado de CPU basado en HPA
   - B) El modo Serverless escala según señales de concurrencia/RPS de Knative; el modo Raw Deployment escala mediante un HPA estándar usando CPU/memoria o métricas personalizadas
   - C) El modo Serverless nunca escala
   - D) El modo Raw Deployment escala según la concurrencia de Knative y el modo Serverless usa HPA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El modo Serverless escala según señales de concurrencia/RPS de Knative; el modo Raw Deployment escala mediante un HPA estándar usando CPU/memoria o métricas personalizadas**

**Explicación:**
El autoscaler de Knative en modo Serverless reacciona a señales a nivel de solicitud, como concurrencia o solicitudes por segundo, que tienden a reaccionar más rápido al tráfico de inferencia con ráfagas que una señal de utilización de recursos. En cambio, el modo Raw Deployment se basa en un Kubernetes HorizontalPodAutoscaler estándar, el mismo modelo de autoscaling usado por cualquier otro Deployment del clúster.
</details>

7. ¿Cómo se relaciona el mecanismo integrado de despliegue canary de KServe con los patrones de división de tráfico de Istio/Argo Rollouts tratados en otra parte de esta documentación?
   - A) Son exactamente el mismo mecanismo, solo con nombres diferentes
   - B) El despliegue canary de KServe es un mecanismo independiente y específico para model serving integrado en el plano de control de KServe, distinto de la división de tráfico de service mesh o controllers de entrega progresiva
   - C) KServe no tiene capacidad de despliegue canary y debe usar Argo Rollouts en su lugar
   - D) La división de tráfico de Istio reemplaza por completo la necesidad de un InferenceService

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El despliegue canary de KServe es un mecanismo independiente y específico para model serving integrado en el plano de control de KServe, distinto de la división de tráfico de service mesh o controllers de entrega progresiva**

**Explicación:**
KServe puede dividir por sí mismo el tráfico entre una revisión estable y una revisión canary de `InferenceService`, desplazando gradualmente el tráfico a medida que crece la confianza. Esto opera específicamente al nivel de las revisiones de `InferenceService` y es una herramienta distinta de los patrones de división de tráfico basados en Istio o Argo Rollouts usados para otras cargas de trabajo en la plataforma; no es un requisito de reemplazo, sino una vía diferenciada y específica para model serving.
</details>

8. ¿Qué función desempeña Karpenter cuando un predictor de `InferenceService` solicita una GPU en EKS?
   - A) Karpenter configura el protocolo de inferencia del predictor de KServe
   - B) Karpenter aprovisiona una instancia EC2 compatible con GPU cuando la solicitud de GPU del Pod no puede satisfacerse con los nodos existentes, y puede consolidar o recuperar esa capacidad una vez que ya no se necesita
   - C) Karpenter reemplaza la necesidad de un plugin de dispositivo GPU
   - D) Karpenter solo funciona con el modo Raw Deployment, nunca con Serverless

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Karpenter aprovisiona una instancia EC2 compatible con GPU cuando la solicitud de GPU del Pod no puede satisfacerse con los nodos existentes, y puede consolidar o recuperar esa capacidad una vez que ya no se necesita**

**Explicación:**
La inferencia con GPU en EKS sigue el modelo estándar de solicitud de recursos de Kubernetes frente al recurso anunciado por el plugin de dispositivo GPU; los grupos de nodos GPU de Karpenter reaccionan a las solicitudes de GPU no programables aprovisionando capacidad compatible, y su comportamiento de consolidación puede recuperar esa capacidad cuando un predictor (especialmente uno que escala a cero en modo Serverless) ya no la necesita: un patrón de autoscaling de dos niveles usado también en otras partes de EKS.
</details>

## Preguntas de respuesta corta

9. En una o dos frases, explica por qué elegir el modo Serverless es adecuado para un modelo con tráfico de inferencia irregular e intermitente, pero inadecuado para uno que requiere una latencia constantemente baja en cada solicitud.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: El escalado a cero del modo Serverless ahorra el coste de GPU durante los períodos inactivos, lo que es adecuado para tráfico irregular/intermitente en el que el modelo permanece inactivo gran parte del tiempo. Sin embargo, volver a escalar desde cero genera latencia de inicio en frío (programación del Pod, inicio del contenedor y carga del modelo), lo que es inaceptable para cargas de trabajo que necesitan una latencia constantemente baja en todas las solicitudes.**

**Explicación:**
La disyuntiva es fundamentalmente entre coste (ahorro en GPU inactivas) y previsibilidad de la latencia (sin inicios en frío). El modo Raw Deployment invierte esta disyuntiva al mantener siempre activas las réplicas mínimas, a costa de pagar por esa capacidad incluso cuando está inactiva.
</details>

10. ¿Qué distingue la compatibilidad integrada con frameworks del predictor de un predictor de contenedor personalizado en KServe?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Los servidores de predictor integrados (por ejemplo, para SKLearn, XGBoost, PyTorch mediante TorchServe o NVIDIA Triton) permiten que una especificación de predictor simplemente apunte a una ubicación de artefacto de modelo y obtenga un servidor funcional sin escribir código de serving. Un predictor de contenedor personalizado se usa para cualquier caso fuera de esos frameworks integrados y debe implementar por sí mismo el protocolo de inferencia de KServe.**

**Explicación:**
Esta distinción determina cuánto trabajo de implementación en el lado del serving se necesita: los servidores integrados cubren frameworks comunes de forma inmediata, mientras que cualquier otro caso requiere un contenedor escrito a mano que hable el protocolo de KServe.
</details>

11. Describe la relación de autoscaling de dos niveles entre las decisiones de escalado de KServe y la respuesta de Karpenter a ellas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: KServe (mediante Knative en modo Serverless o HPA en modo Raw Deployment) decide cuántos Pods de predictor se necesitan según señales a nivel de solicitud o de utilización de recursos: una decisión a nivel de Pod sin conocimiento de los nodos. Karpenter reacciona por separado al estado resultante de programación de los Pods (solicitudes de GPU no programables o nodos GPU vacíos) para decidir cuánta capacidad EC2 con GPU aprovisionar o recuperar: una decisión a nivel de nodo sin conocimiento de por qué existen los Pods.**

**Explicación:**
Estos son dos bucles de control independientes, acoplados solo mediante el estado de cantidad/programación de Pods: el mismo patrón general de autoscaling de dos niveles (primero una decisión a nivel de trabajo/Pod y después una decisión a nivel de nodo que reacciona a ella) usado para otras cargas de trabajo con autoscaling en EKS en otra parte de esta documentación.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/06-kserve.md)
