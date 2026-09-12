# Cuestionario de cargas de trabajo de AI/ML

Repasa los límites de asignación, entrenamiento/serving, almacenamiento, redes, seguridad, observabilidad y costos.

## Preguntas del cuestionario

### 1. ¿Cómo debe un Pod solicitar GPUs expuestas por el plugin de dispositivos de NVIDIA?

- A. Establecer solo requests con nvidia.com/gpu:0.5
- B. Especificar limits enteros de nvidia.com/gpu, con un request igual si también se proporciona
- C. Agregar solo una anotación de nodo nvidia.com/gpu
- D. Nombrar una RuntimeClass nvidia-mps para habilitar el uso compartido automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Especificar limits enteros de nvidia.com/gpu, con un request igual si también se proporciona**

Los limits por sí solos implican un request igual. La capacidad de GPU asignable no es una etiqueta de nodo. Las etiquetas de GPU Feature Discovery, MIG, MPS y time-slicing requieren configuración independiente; un slot compartido no garantiza una fracción de la memoria de GPU.

[Asignación y uso compartido](../../ai-ml/01-ai-ml-workloads.md#nvidia-gpu-operator-and-device-allocation)
</details>

### 2. ¿Qué recurso heredado de Kubeflow instalado entiende los roles distribuidos de TensorFlow?

- A. Deployment crea automáticamente todos los valores de TF_CONFIG
- B. Job garantiza el éxito del entrenamiento y la colocación simultánea de workers
- C. TFJob proporciona roles/configuración específicos del framework
- D. TFJob está integrado en Kubernetes y no necesita instalación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. TFJob proporciona roles/configuración específicos del framework**

Instala su CRD/controller y configura la política de reinicio, la estrategia del framework, los checkpoints, el almacenamiento y las redes. La recuperación y la programación gang no son garantías universales. Un Job regular también puede entrenar cuando se proporciona código de ejecución real.

[APIs de Trainer y heredadas](../../ai-ml/kubeflow/05-training-operator.md)
</details>

### 3. ¿Cómo debe conectarse un sistema de archivos FSx for Lustre existente mediante CSI?

- A. Combinar un CR de Lustre y una StorageClass que contenga el ID existente
- B. Usar un PV estático con volumeHandle/dnsname/mountname y un PVC vinculado
- C. SCRATCH_2 admite todas las opciones de backup/throughput persistentes
- D. FIO en /data sin montar mide FSx

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar un PV estático con volumeHandle/dnsname/mountname y un PVC vinculado**

La conexión estática difiere de la creación dinámica de sistemas de archivos. Compara capacidad, IOPS/throughput, latencia, patrones de acceso, permisos, AZ/red y backups. Realiza pruebas comparativas en una ruta de prueba dedicada del volumen montado real.

[Almacenamiento estático y dinámico](../../ai-ml/01-ai-ml-workloads.md#storage-and-caching)
</details>

### 4. ¿Qué debe guiar la asignación de recursos de AI/ML?

- A. Todo trabajo de entrenamiento requiere una GPU
- B. Uso medido de CPU/memoria/GPU, tamaño del modelo, I/O, latencia y throughput
- C. Solicitar siempre los recursos máximos
- D. Omitir requests siempre es más eficiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Uso medido de CPU/memoria/GPU, tamaño del modelo, I/O, latencia y throughput**

CPU y otros aceleradores pueden ser apropiados. La configuración de hilos de OMP/MKL afecta a las bibliotecas auxiliares, no al uso compartido de GPU. La configuración del asignador CUDA difiere de la asignación/aislamiento de GPU de Kubernetes. Los efectos de VPA dependen del modo, el comportamiento de reinicio y la compatibilidad de la carga de trabajo.

[Ubicación de recursos](../../ai-ml/01-ai-ml-workloads.md#placement-and-topology)
</details>

### 5. ¿Qué se debe comprobar al seleccionar una plataforma de serving como KServe?

- A. Cualquier URI de modelo funciona de inmediato
- B. La imagen de runtime, el formato del modelo, el protocolo, el almacenamiento y el modo de despliegue cumplen los requisitos
- C. Un Deployment normal no puede servir inferencia
- D. Todos los modos ofrecen un comportamiento idéntico de canary y scale-to-zero

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La imagen de runtime, el formato del modelo, el protocolo, el almacenamiento y el modo de despliegue cumplen los requisitos**

Un Deployment puede ejecutar un servidor de inferencia. Las APIs de KServe Knative/Standard y las versiones de Seldon difieren. Explainability, procesamiento, weighted routing y batch inference no son valores predeterminados habilitados universalmente. TorchServe no es una opción predeterminada mantenida para usos nuevos.

[Modos y runtimes de KServe](../../ai-ml/kubeflow/06-kserve.md)
</details>

### 6. ¿Qué se requiere para el escalado de HPA según la utilización de GPU o la carga de requests?

- A. nvidia.com/gpu asignado se convierte automáticamente en una métrica Resource de utilización
- B. Exporters y adaptadores de métricas personalizadas/externas con las etiquetas, unidades y agregación correctas
- C. Aumentar las réplicas para corregir la baja precisión del modelo
- D. Adjuntar varios HPA al mismo Deployment para un escalado aditivo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Exporters y adaptadores de métricas personalizadas/externas con las etiquetas, unidades y agregación correctas**

La ruta Resource estándar de metrics-server expone CPU/memoria. Las métricas de GPU/requests necesitan recopilación/adaptadores independientes. Las métricas de Pod deben asignarse a las etiquetas de namespace/Pod; un promedio global puede perder esa asignación. Usa un único responsable del escalado y valida si la carga/cola es una señal proporcional mejor que los percentiles de latencia.

[Ejemplo de HPA](../../ai-ml/01-ai-ml-workloads.md#hpa-and-metrics)
</details>

### 7. ¿Qué afirmación sobre las redes de entrenamiento distribuido es correcta?

- A. Una anotación de zona por sí sola controla la ubicación
- B. Los montajes hostPath de GPU configuran EFA/GPUDirect
- C. Validar conjuntamente la ubicación por etiquetas de nodo, el hardware, los drivers/plugins, las bibliotecas de comunicación y las políticas de red
- D. NCCL siempre transporta datos mediante MPI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Validar conjuntamente la ubicación por etiquetas de nodo, el hardware, los drivers/plugins, las bibliotecas de comunicación y las políticas de red**

NCCL sobre EFA utiliza AWS OFI NCCL y libfabric; MPI puede iniciar procesos. La configuración de Multus/SR-IOV, MTU y RDMA es específica del entorno. Los ejemplos de NIC genéricos no son configuraciones listas para usar de EKS. NetworkPolicy puede afectar la disponibilidad/el rendimiento al bloquear el tráfico necesario.

[Límites del entrenamiento distribuido](../../ai-ml/01-ai-ml-workloads.md#kubeflow-and-distributed-training)
</details>

### 8. ¿Qué afirmación sobre la protección de modelos/datos es correcta?

- A. El base64 de Secret es cifrado
- B. Kubernetes RBAC concede permisos de S3/KMS
- C. Configurar por separado API RBAC, IAM de la carga de trabajo, cifrado/administración de claves, credenciales de archivos y redes
- D. Almacenar modelos grandes en Secrets y claves de descifrado en variables de entorno de forma predeterminada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Configurar por separado API RBAC, IAM de la carga de trabajo, cifrado/administración de claves, credenciales de archivos y redes**

Secrets tiene límites de tamaño y base64 es codificación. Usa almacenamiento de objetos con comprobaciones de autorización/integridad para modelos grandes. Una cuenta de servicio de Pod no siempre necesita permiso get de Secret para montar un volumen Secret: las lecturas de API y la entrega de volumen por kubelet difieren. PodSecurityPolicy se eliminó; usa controles de admisión/PSS actuales.

[Acceso a datos y modelos](../../ai-ml/01-ai-ml-workloads.md#data-and-model-access)
</details>

### 9. ¿Qué debe distinguir la observabilidad de servicios de ML?

- A. La utilización de GPU determina la precisión
- B. ServiceMonitor selecciona directamente las etiquetas de Pod
- C. Los errores/latencia/throughput del servicio, el uso de recursos y la calidad del modelo basada en datos reales son aspectos independientes
- D. Todos los logs de contenedores son JSON de Docker

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Los errores/latencia/throughput del servicio, el uso de recursos y la calidad del modelo basada en datos reales son aspectos independientes**

ServiceMonitor selecciona etiquetas de Service/puertos con nombre. Define si la latencia incluye fallos y evita contabilizar una request como éxito y error a la vez. La calidad necesita etiquetas/datos reales. Valida el formato de CRI frente al JSON de la aplicación, el esquema de datasource/panel de Grafana, la agregación de alertas etiquetadas y el comportamiento sin tráfico.

[Métricas y logs](../../ai-ml/01-ai-ml-workloads.md#prometheus-and-grafana)
</details>

### 10. ¿Cómo debe validarse la optimización de costos?

- A. Usar Spot para todas las cargas de trabajo
- B. Las instancias más nuevas siempre son las más económicas
- C. Medir el rendimiento requerido, el costo total, la recuperación/checkpointing ante interrupciones y la recuperación real de Pod/nodos
- D. La noche reduce automáticamente las tarifas On-Demand

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Medir el rendimiento requerido, el costo total, la recuperación/checkpointing ante interrupciones y la recuperación real de Pod/nodos**

Menos Pods no implica la terminación de EC2. Comprueba la disponibilidad, las cuotas, AMI/drivers y los límites de NodePool. Los taints de entrenamiento necesitan tolerations correspondientes; los grupos mixtos de CPU/GPU no son EKS Hybrid Nodes. Crear un ConfigMap de Autoscaler sin usar no cambia los flags del controller.

[Spot y aprovisionamiento de nodos](../../ai-ml/01-ai-ml-workloads.md#spot-and-node-provisioning)
</details>

---

[Volver a los materiales de aprendizaje](../../ai-ml/01-ai-ml-workloads.md)
