# Cuestionario sobre cargas de trabajo de AI/ML

Este cuestionario evalúa tu comprensión sobre la ejecución de cargas de trabajo de AI/ML en Kubernetes.

## Preguntas del cuestionario

### 1. ¿Cuál es el campo de solicitud de recursos requerido para programar un Pod que usa una GPU en Kubernetes?

A. resources.requests.gpu
B. resources.requests.nvidia.com/gpu
C. resources.requests.k8s.io/gpu
D. resources.requests.compute/gpu

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. resources.requests.nvidia.com/gpu**

**Explicación:**
El campo de solicitud de recursos requerido para programar un Pod que usa una GPU en Kubernetes es `resources.requests.nvidia.com/gpu`. Esta es la forma estándar de solicitar GPU NVIDIA, y otros proveedores de GPU pueden usar sus propios namespaces (por ejemplo, `amd.com/gpu`).

**Ejemplo de solicitud de recurso GPU:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: gpu-container
    image: nvidia/cuda:11.0-base
    resources:
      limits:
        nvidia.com/gpu: 1  # Request 1 GPU
      requests:
        nvidia.com/gpu: 1  # Requests and limits must be the same
```

**Características de los recursos GPU:**
1. **Asignación entera**: Las GPU solo pueden asignarse en unidades enteras (por ejemplo, 1, 2, 3). No se admiten valores decimales (por ejemplo, 0.5).
2. **Coincidencia entre requests y limits**: Para recursos GPU, `requests` y `limits` deben ser iguales.
3. **Uso exclusivo**: De forma predeterminada, las GPU no se comparten entre containers. Cada GPU se asigna a un solo container a la vez.
4. **Etiquetas de Node**: Los Nodes con GPU normalmente se etiquetan con `nvidia.com/gpu`.

**Requisitos previos para el uso de GPU:**
1. **Hardware GPU en el Node**: Debe haber una GPU física instalada en el Node.
2. **Drivers de GPU**: Deben instalarse los drivers de GPU adecuados en el Node.
3. **NVIDIA Device Plugin**: NVIDIA Device Plugin debe estar instalado en el cluster de Kubernetes.
4. **Compatibilidad del container runtime**: El container runtime debe admitir GPU.

**Instalación de NVIDIA Device Plugin:**
```bash
# Installation using Helm
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update
helm install nvidia-device-plugin nvdp/nvidia-device-plugin

# Or direct installation
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.13.0/nvidia-device-plugin.yml
```

**Comprobación de recursos GPU:**
```bash
# Check GPU resources on nodes
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu

# Check pods using GPUs
kubectl get pods -A -o custom-columns=NAME:.metadata.name,GPU:.spec.containers[*].resources.limits.nvidia\\.com/gpu
```

**Solicitud multi-GPU:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multi-gpu-pod
spec:
  containers:
  - name: multi-gpu-container
    image: nvidia/cuda:11.0-base
    resources:
      limits:
        nvidia.com/gpu: 4  # Request 4 GPUs
      requests:
        nvidia.com/gpu: 4
```

**Particionamiento de memoria GPU (NVIDIA MPS):**
NVIDIA Multi-Process Service (MPS) permite que varios procesos compartan la misma GPU. Esto no es compatible de forma nativa en Kubernetes y requiere configuración personalizada.

**Otros proveedores de GPU:**
Otros proveedores de GPU usan sus propios namespaces:
- AMD GPU: `amd.com/gpu`
- Intel GPU: `intel.com/gpu`

**Problemas con las otras opciones:**
- A. resources.requests.gpu: Este no es un campo de recurso válido de Kubernetes. Los recursos GPU deben usar namespaces específicos del proveedor.
- C. resources.requests.k8s.io/gpu: Este no es un campo de recurso válido de Kubernetes. El namespace `k8s.io` normalmente se usa para recursos principales de Kubernetes.
- D. resources.requests.compute/gpu: Este no es un campo de recurso válido de Kubernetes.
</details>

### 2. ¿Cuál es el tipo de recurso más adecuado para ejecutar trabajos de entrenamiento distribuido de TensorFlow en Kubernetes?

A. Deployment
B. StatefulSet
C. Job
D. TFJob (Kubeflow)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. TFJob (Kubeflow)**

**Explicación:**
El tipo de recurso más adecuado para ejecutar trabajos de entrenamiento distribuido de TensorFlow en Kubernetes es `TFJob`. TFJob forma parte del proyecto Kubeflow y es un recurso personalizado diseñado específicamente para ejecutar trabajos de entrenamiento de TensorFlow en Kubernetes.

**Características clave de TFJob:**
1. **Compatibilidad con entrenamiento distribuido**: Admite la arquitectura de entrenamiento distribuido de TensorFlow, incluidos workers, parameter servers y evaluators.
2. **Recuperación automática**: Reinicia automáticamente los workers fallidos.
3. **Gang scheduling**: Garantiza que todos los workers se programen simultáneamente.
4. **Características específicas de TensorFlow**: Configura automáticamente las variables de entorno y los ajustes necesarios para el entrenamiento distribuido de TensorFlow.
5. **Monitoreo y registros**: Proporciona características para monitorear el estado y los logs de los trabajos de TensorFlow.

**Ejemplo de TFJob:**
```yaml
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: mnist-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 3
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0
            command:
            - python
            - /opt/model/train.py
            - --batch_size=64
            - --learning_rate=0.001
            resources:
              limits:
                nvidia.com/gpu: 1
    PS:
      replicas: 1
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0
            command:
            - python
            - /opt/model/train.py
            - --batch_size=64
            - --learning_rate=0.001
    Chief:
      replicas: 1
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0
            command:
            - python
            - /opt/model/train.py
            - --batch_size=64
            - --learning_rate=0.001
            resources:
              limits:
                nvidia.com/gpu: 1
```

**Componentes de TFJob:**
1. **Chief**: El worker principal responsable de guardar checkpoints del modelo y escribir resúmenes.
2. **Worker**: Workers que realizan el entrenamiento del modelo.
3. **PS (Parameter Server)**: Almacena y actualiza los parámetros del modelo.
4. **Evaluator**: Realiza la evaluación del modelo.

**Instalación de TFJob:**
```bash
# Install Kubeflow
kubectl apply -f https://raw.githubusercontent.com/kubeflow/kubeflow/master/kfctl_k8s_istio.yaml

# Or install only the TFJob controller
kubectl apply -f https://raw.githubusercontent.com/kubeflow/tf-operator/master/deploy/v1/tf-operator.yaml
```

**Monitoreo de TFJob:**
```bash
# Check TFJob status
kubectl get tfjobs

# Check specific TFJob details
kubectl describe tfjob mnist-training

# Check TFJob pods
kubectl get pods -l tf-job-name=mnist-training
```

**Comparación con otros tipos de recursos:**

1. **Deployment**:
   - Adecuado para services de larga duración
   - Admite recuperación automática y rolling updates
   - Carece de características de coordinación para trabajos de entrenamiento distribuido
   - Sin características específicas de TensorFlow

2. **StatefulSet**:
   - Proporciona identificadores de red estables y almacenamiento persistente
   - Deployment y escalado ordenados
   - Carece de características de coordinación para trabajos de entrenamiento distribuido
   - Sin características específicas de TensorFlow

3. **Job**:
   - Adecuado para trabajos de una sola ejecución
   - Garantiza la finalización del trabajo
   - Carece de características de coordinación para trabajos de entrenamiento distribuido
   - Sin características específicas de TensorFlow

4. **TFJob**:
   - Optimizado para el entrenamiento distribuido de TensorFlow
   - Define roles como workers y parameter servers
   - Configura automáticamente variables de entorno y ajustes específicos de TensorFlow
   - Lógica integrada de finalización de trabajos y manejo de fallos

**Operadores de Kubeflow para otros frameworks de ML:**
- **PyTorchJob**: Para trabajos de entrenamiento de PyTorch
- **MPIJob**: Para entrenamiento distribuido basado en MPI como Horovod
- **XGBoostJob**: Para trabajos de entrenamiento de XGBoost

**Problemas con las otras opciones:**
- A. Deployment: Adecuado para services de larga duración y no maneja los requisitos específicos de los trabajos de entrenamiento distribuido de TensorFlow.
- B. StatefulSet: Adecuado para aplicaciones que requieren persistencia de estado, pero carece de características de coordinación para trabajos de entrenamiento distribuido de TensorFlow.
- C. Job: Adecuado para trabajos de una sola ejecución, pero no maneja los requisitos específicos de los trabajos de entrenamiento distribuido de TensorFlow.
</details>
### 3. ¿Cuál es la consideración más importante al configurar almacenamiento persistente para cargas de trabajo de AI/ML en Kubernetes?

A. Capacidad de almacenamiento
B. Tipo de StorageClass
C. Patrones de acceso a datos y requisitos de throughput
D. Provisioner de almacenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Patrones de acceso a datos y requisitos de throughput**

**Explicación:**
La consideración más importante al configurar almacenamiento persistente para cargas de trabajo de AI/ML en Kubernetes son los patrones de acceso a datos y los requisitos de throughput. Las cargas de trabajo de AI/ML procesan grandes cantidades de datos y pueden tener varios patrones de acceso (lecturas secuenciales, lecturas aleatorias, acceso paralelo, etc.), que a menudo requieren un throughput alto. Elegir una solución de almacenamiento que cumpla estos requisitos tiene un impacto significativo en el rendimiento y la eficiencia.

**Patrones comunes de acceso a datos en cargas de trabajo de AI/ML:**
1. **Lecturas de datasets grandes**: Los datasets de entrenamiento pueden variar desde varios GB hasta varios TB, lo que requiere un rendimiento de lectura eficiente.
2. **Acceso paralelo**: Son comunes los escenarios de entrenamiento distribuido en los que varios workers acceden simultáneamente a los datos.
3. **Lecturas secuenciales**: Trabajos de procesamiento por lotes que leen datasets completos de forma secuencial.
4. **Acceso aleatorio**: Entrenamiento mini-batch o aprendizaje en línea que accede a partes aleatorias del dataset.
5. **Guardado de checkpoints**: Operaciones de escritura para guardar checkpoints del modelo durante el entrenamiento.

**Soluciones de almacenamiento adecuadas para cargas de trabajo de AI/ML:**

1. **Sistemas de archivos distribuidos**:
   - **Amazon FSx for Lustre**: Sistema de archivos de alto rendimiento optimizado para computación de alto rendimiento y cargas de trabajo de machine learning
   - **GlusterFS/Ceph**: Sistemas de archivos distribuidos open-source que admiten escalabilidad y acceso paralelo
   - **HDFS**: Hadoop Distributed File System adecuado para el procesamiento de datasets a gran escala

2. **Almacenamiento en bloque de alto rendimiento**:
   - **AWS EBS io2/io2 Block Express**: Almacenamiento en bloque basado en SSD que proporciona IOPS y throughput altos
   - **GCP Persistent Disk SSD**: Almacenamiento en bloque basado en SSD que proporciona IOPS y throughput altos
   - **Azure Ultra Disk**: Almacenamiento en bloque basado en SSD que proporciona IOPS y throughput muy altos

3. **Almacenamiento de objetos**:
   - **Amazon S3**: Almacenamiento de objetos altamente escalable, adecuado para almacenamiento de datasets a gran escala
   - **Google Cloud Storage**: Almacenamiento de objetos altamente escalable, adecuado para almacenamiento de datasets a gran escala
   - **Azure Blob Storage**: Almacenamiento de objetos altamente escalable, adecuado para almacenamiento de datasets a gran escala

**Ejemplo de configuración de almacenamiento (FSx for Lustre):**
```yaml
# StorageClass definition
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0eabfaa81fb22bcaf
  securityGroupIds: sg-068000ccf82dfba88
  deploymentType: SCRATCH_2
  automaticBackupRetentionDays: "0"
  dailyAutomaticBackupStartTime: "00:00"
  perUnitStorageThroughput: "200"
  dataCompressionType: "NONE"
mountOptions:
  - flock

---
# PersistentVolumeClaim definition
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-dataset
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi

---
# Using in training job
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: distributed-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0-gpu
            command:
            - python
            - /opt/model/train.py
            volumeMounts:
            - name: dataset
              mountPath: /data
            resources:
              limits:
                nvidia.com/gpu: 1
          volumes:
          - name: dataset
            persistentVolumeClaim:
              claimName: ml-dataset
```

**Métricas de rendimiento que se deben considerar al seleccionar almacenamiento:**
1. **Throughput**: Cantidad de datos que se pueden leer/escribir por segundo (MB/s o GB/s)
2. **IOPS (Input/Output Operations Per Second)**: Número de operaciones de I/O que se pueden realizar por segundo
3. **Latencia**: Tiempo de respuesta para solicitudes de I/O
4. **Compatibilidad con acceso paralelo**: Capacidad para que varios clientes accedan simultáneamente
5. **Escalabilidad**: Capacidad de mantener el rendimiento a medida que los datos crecen

**Almacenamiento recomendado por tipo de carga de trabajo de AI/ML:**
1. **Entrenamiento distribuido a gran escala**: FSx for Lustre, HDFS, Ceph
2. **Entrenamiento en un solo Node**: Almacenamiento en bloque SSD de alto rendimiento
3. **Preprocesamiento de datos**: Sistemas de archivos distribuidos o almacenamiento de objetos
4. **Model serving**: Almacenamiento en bloque SSD de alto rendimiento o almacenamiento en memoria

**Pruebas de rendimiento de almacenamiento:**
```bash
# Storage performance test using FIO
kubectl run fio-test --image=nixery.dev/shell/fio --restart=Never -- \
  fio --name=benchmark --directory=/data --direct=1 --rw=randread --bs=4k \
  --size=1G --numjobs=16 --runtime=60 --group_reporting
```

**Problemas con las otras opciones:**
- A. Capacidad de almacenamiento: Es importante, pero la capacidad por sí sola no puede cumplir los requisitos de rendimiento de las cargas de trabajo de AI/ML.
- B. Tipo de StorageClass: StorageClass define el método de aprovisionamiento, pero no determina por sí sola completamente las características de rendimiento.
- D. Provisioner de almacenamiento: El provisioner define cómo se crea el almacenamiento, pero no aborda directamente los requisitos de rendimiento de la carga de trabajo.
</details>

### 4. ¿Cuál es el método más efectivo para la asignación de recursos para cargas de trabajo de AI/ML en Kubernetes?

A. Asignar los mismos recursos a todos los Pods
B. Perfilado y optimización de recursos según las características de la carga de trabajo
C. Solicitar siempre los recursos máximos
D. Desplegar sin solicitudes de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Perfilado y optimización de recursos según las características de la carga de trabajo**

**Explicación:**
El método más efectivo para la asignación de recursos para cargas de trabajo de AI/ML en Kubernetes es el perfilado y la optimización de recursos según las características de la carga de trabajo. Las cargas de trabajo de AI/ML tienen diferentes requisitos de recursos en varias etapas, como entrenamiento, inferencia y preprocesamiento de datos, y comprender las características de cada carga de trabajo y asignar recursos en consecuencia es importante para optimizar el rendimiento y la eficiencia de costos.

**Métodos de perfilado de recursos de cargas de trabajo de AI/ML:**
1. **Benchmarking**: Ejecutar cargas de trabajo con varias configuraciones de recursos y medir el rendimiento.
2. **Monitoreo**: Monitorear el uso real de recursos para identificar patrones.
3. **Ajuste gradual**: Comenzar con estimaciones iniciales y ajustar gradualmente los recursos.
4. **Auto-scaling**: Ajustar automáticamente los recursos según las demandas de la carga de trabajo.

**Características de recursos por tipo de carga de trabajo de AI/ML:**

1. **Entrenamiento de modelos**:
   - CPU: Importante para el preprocesamiento de datos y la ingeniería de características
   - GPU: Esencial para el entrenamiento de modelos de deep learning
   - Memory: Necesaria para datasets grandes y almacenamiento de parámetros del modelo
   - Storage: Necesario para almacenamiento de datasets y checkpoints

2. **Inferencia de modelos**:
   - CPU: Adecuada para modelos simples o inferencia por lotes
   - GPU: Ventajosa para modelos complejos o inferencia en tiempo real
   - Memory: Necesaria para carga del modelo y procesamiento de entrada/salida
   - Latencia: Importante para inferencia en tiempo real

3. **Preprocesamiento de datos**:
   - CPU: La capacidad de procesamiento paralelo es importante
   - Memory: Necesaria para el procesamiento de datasets a gran escala
   - Storage I/O: El rendimiento de lectura/escritura de datos es importante

**Ejemplo de optimización de recursos:**
```yaml
# Training job - GPU and high memory requirements
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: training-job
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0-gpu
            resources:
              requests:
                cpu: 4
                memory: 16Gi
                nvidia.com/gpu: 1
              limits:
                cpu: 8
                memory: 32Gi
                nvidia.com/gpu: 1

---
# Inference service - low latency requirements
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      containers:
      - name: inference
        image: tensorflow/serving:2.6.0-gpu
        resources:
          requests:
            cpu: 2
            memory: 4Gi
            nvidia.com/gpu: 1
          limits:
            cpu: 4
            memory: 8Gi
            nvidia.com/gpu: 1
        env:
        - name: TF_FORCE_GPU_ALLOW_GROWTH
          value: "true"

---
# Data preprocessing job - CPU and memory intensive
apiVersion: batch/v1
kind: Job
metadata:
  name: data-preprocessing
spec:
  template:
    spec:
      containers:
      - name: preprocessing
        image: python:3.9
        resources:
          requests:
            cpu: 8
            memory: 16Gi
          limits:
            cpu: 16
            memory: 32Gi
```

**Herramientas de monitoreo y optimización de recursos:**
1. **Prometheus + Grafana**: Monitoreo y visualización del uso de recursos
2. **Kubernetes Metrics Server**: Recolección básica de métricas de recursos
3. **NVIDIA DCGM Exporter**: Recolección de métricas de GPU
4. **Vertical Pod Autoscaler**: Ajuste automático de solicitudes de recursos
5. **Horizontal Pod Autoscaler**: Ajuste automático del número de Pods

**Estrategias de optimización de recursos:**
1. **Uso compartido de GPU**: Compartir GPU entre varios trabajos mediante NVIDIA MPS o programación por intervalos de tiempo
2. **Optimización de memoria**: Cuantización de modelos, carga diferida, algoritmos eficientes en memoria
3. **Procesamiento por lotes**: Procesar solicitudes de inferencia por lotes para mejorar el throughput
4. **Auto-scaling**: Ajustar automáticamente los recursos según la carga
5. **Node affinity**: Colocar cargas de trabajo en Nodes con características de hardware específicas

**Ejemplo de optimización de memoria GPU:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-memory-optimized
spec:
  containers:
  - name: tensorflow
    image: tensorflow/tensorflow:2.6.0-gpu
    env:
    - name: TF_FORCE_GPU_ALLOW_GROWTH
      value: "true"  # Allocate only as much GPU memory as needed
    - name: TF_GPU_ALLOCATOR
      value: "cuda_malloc_async"  # Use asynchronous memory allocator
    resources:
      limits:
        nvidia.com/gpu: 1
```

**Ejemplo de optimización de CPU y memoria:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cpu-memory-optimized
spec:
  containers:
  - name: python
    image: python:3.9
    env:
    - name: OMP_NUM_THREADS
      value: "4"  # Limit OpenMP thread count
    - name: MKL_NUM_THREADS
      value: "4"  # Limit Intel MKL thread count
    resources:
      requests:
        cpu: 4
        memory: 8Gi
      limits:
        cpu: 8
        memory: 16Gi
```

**Problemas con las otras opciones:**
- A. Asignar los mismos recursos a todos los Pods: Puede causar desperdicio o escasez de recursos al no considerar diferentes características de la carga de trabajo.
- C. Solicitar siempre los recursos máximos: Baja eficiencia de costos y baja utilización de recursos del cluster.
- D. Desplegar sin solicitudes de recursos: Puede causar problemas de programación y contención de recursos, especialmente importantes para recursos limitados como las GPU.
</details>
### 5. ¿Cuál es el método más adecuado para model serving de AI/ML en Kubernetes?

A. Usar recursos Deployment regulares
B. Usar plataformas de serving especializadas como KServe (anteriormente KFServing) o Seldon Core
C. Usar recursos StatefulSet
D. Usar recursos CronJob

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar plataformas de serving especializadas como KServe (anteriormente KFServing) o Seldon Core**

**Explicación:**
El método más adecuado para model serving de AI/ML en Kubernetes es usar plataformas de serving especializadas como KServe (anteriormente KFServing) o Seldon Core. Estas plataformas proporcionan varias características necesarias para model serving (gestión de versiones de modelos, pruebas A/B, canary deployment, auto-scaling, monitoreo, etc.) y admiten varios frameworks de ML.

**Características clave de las plataformas especializadas de model serving:**
1. **Compatibilidad con varios frameworks de ML**: Admite modelos entrenados con varios frameworks como TensorFlow, PyTorch, ONNX, scikit-learn
2. **Gestión de versiones de modelos**: Gestiona varias versiones de modelos y permite rollback
3. **Traffic splitting**: Características de traffic splitting para pruebas A/B, canary deployment, etc.
4. **Auto-scaling**: Auto-scaling basado en la carga de solicitudes
5. **Monitoreo y registros**: Monitoreo del rendimiento, latencia, throughput, etc. del modelo
6. **Pre y post-procesamiento**: Pipelines de preprocesamiento de datos de entrada y post-procesamiento de datos de salida
7. **Inferencia por lotes**: Compatibilidad con inferencia por lotes sobre grandes cantidades de datos
8. **Explicabilidad del modelo**: Características para explicar las predicciones del modelo

**Ejemplo de KServe:**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: sklearn-iris
spec:
  predictor:
    sklearn:
      storageUri: "gs://kserve-examples/models/sklearn/iris"
      resources:
        requests:
          cpu: 100m
          memory: 256Mi
        limits:
          cpu: 1
          memory: 1Gi
```

**Ejemplo de Seldon Core:**
```yaml
apiVersion: machinelearning.seldon.io/v1
kind: SeldonDeployment
metadata:
  name: iris-model
spec:
  name: iris
  predictors:
  - name: default
    replicas: 1
    graph:
      name: classifier
      implementation: SKLEARN_SERVER
      modelUri: "gs://seldon-models/sklearn/iris"
      envSecretRefName: seldon-init-container-secret
    engineResources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 1
        memory: 1Gi
```

**Ejemplos de características avanzadas de serving:**

1. **Canary deployment (KServe):**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: sklearn-iris
spec:
  predictor:
    canaryTrafficPercent: 20
    sklearn:
      storageUri: "gs://kserve-examples/models/sklearn/iris-v2"
    containers:
    - name: sklearn-v1
      image: kserve/sklearnserver:latest
      args:
      - --model_dir=/mnt/models
      - --model_name=sklearn-iris
```

2. **Pipeline de pre y post-procesamiento (Seldon Core):**
```yaml
apiVersion: machinelearning.seldon.io/v1
kind: SeldonDeployment
metadata:
  name: iris-pipeline
spec:
  name: iris
  predictors:
  - name: default
    replicas: 1
    graph:
      name: preprocessor
      type: TRANSFORMER
      children:
      - name: model
        type: MODEL
        implementation: SKLEARN_SERVER
        modelUri: "gs://seldon-models/sklearn/iris"
        children:
        - name: postprocessor
          type: TRANSFORMER
          implementation: PYTHON
          modelUri: "gs://seldon-models/postprocessor"
```

3. **Serving multi-modelo (KServe):**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: multi-model-example
spec:
  predictor:
    triton:
      storageUri: "gs://kserve-examples/models/triton/multi-model"
```

**Instalación de plataformas de serving especializadas:**
```bash
# Install KServe
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.8.0/kserve.yaml

# Install Seldon Core (using Helm)
helm install seldon-core seldon-core-operator \
  --repo https://storage.googleapis.com/seldon-charts \
  --namespace seldon-system \
  --create-namespace
```

**Monitoreo de model serving:**
```bash
# Check KServe service status
kubectl get inferenceservices

# Check Seldon Core service status
kubectl get seldondeployments
```

**Comparación entre Deployment regular y plataformas de serving especializadas:**

| Característica | Deployment regular | Plataforma de serving especializada |
|---------|-------------------|------------------------------|
| Serving básico | Compatible | Compatible |
| Gestión de versiones de modelos | Requiere implementación manual | Compatibilidad integrada |
| Traffic splitting | Requiere implementación manual | Compatibilidad integrada |
| Auto-scaling | Compatibilidad limitada con HPA | Compatibilidad de escalado avanzada |
| Monitoreo | Requiere implementación manual | Compatibilidad integrada |
| Pre/post-procesamiento | Requiere implementación manual | Compatibilidad integrada |
| Inferencia por lotes | Requiere implementación manual | Compatibilidad integrada |
| Explicabilidad del modelo | Requiere implementación manual | Compatibilidad integrada |

**Problemas con las otras opciones:**
- A. Usar recursos Deployment regulares: El serving básico es posible, pero carece de características como gestión de versiones de modelos, traffic splitting y monitoreo avanzado.
- C. Usar recursos StatefulSet: Adecuado para aplicaciones que requieren persistencia de estado, pero carece de características especializadas para model serving.
- D. Usar recursos CronJob: Adecuado para trabajos por lotes periódicos y no adecuado para model serving en tiempo real.
</details>

### 6. ¿Cuál es la métrica más adecuada para configurar auto-scaling para cargas de trabajo de AI/ML en Kubernetes?

A. Utilización de CPU
B. Utilización de memoria
C. Utilización de GPU
D. Métricas personalizadas basadas en características de la carga de trabajo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Métricas personalizadas basadas en características de la carga de trabajo**

**Explicación:**
La métrica más adecuada para configurar auto-scaling para cargas de trabajo de AI/ML en Kubernetes son las métricas personalizadas basadas en características de la carga de trabajo. Las cargas de trabajo de AI/ML pueden necesitar escalado basado en varios factores más allá de la utilización de CPU, memoria y GPU, como latencia de solicitudes, longitud de cola y tamaño de lote. Es importante seleccionar métricas que reflejen mejor las características de la carga de trabajo.

**Tipos de métricas de auto-scaling para cargas de trabajo de AI/ML:**
1. **Métricas basadas en recursos**:
   - Utilización de CPU
   - Utilización de memoria
   - Utilización de GPU

2. **Métricas personalizadas**:
   - Latencia de solicitudes
   - Throughput de solicitudes
   - Longitud de cola
   - Tamaño de lote
   - Precisión del modelo
   - Tiempo de inferencia

3. **Métricas externas**:
   - Longitud de cola de mensajes (Kafka, RabbitMQ, etc.)
   - Latencia de consultas de base de datos
   - Conteo de solicitudes de API gateway

**Métricas recomendadas por tipo de carga de trabajo de AI/ML:**
1. **Service de inferencia de modelos**:
   - Latencia de solicitudes
   - Solicitudes por segundo (RPS)
   - Número de solicitudes en cola

2. **Trabajos de procesamiento por lotes**:
   - Longitud de la cola de trabajos
   - Cantidad de datos pendientes de procesamiento
   - Tiempo de finalización del trabajo

3. **Procesamiento de streaming**:
   - Latencia de procesamiento de stream
   - Tasa de procesamiento de eventos
   - Número de eventos sin procesar

**Ejemplos de Horizontal Pod Autoscaler (HPA):**
```yaml
# CPU utilization-based HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-cpu
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70

---
# Custom metric-based HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-custom
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: inference_latency_milliseconds
      target:
        type: AverageValue
        averageValue: 100

---
# External metric-based HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-external
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: kafka_topic_lag
        selector:
          matchLabels:
            topic: inference-requests
      target:
        type: AverageValue
        averageValue: 100
```

**Recolección y exposición de métricas personalizadas:**
1. **Prometheus Adapter**: Expone métricas recolectadas por Prometheus a la Kubernetes API
2. **Custom Metrics API**: Expone métricas personalizadas a la Kubernetes API
3. **External Metrics API**: Expone métricas de sistemas externos a la Kubernetes API

**Ejemplo de configuración de Prometheus Adapter:**
```yaml
# Prometheus Adapter configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: adapter-config
  namespace: monitoring
data:
  config.yaml: |
    rules:
    - seriesQuery: 'inference_latency_milliseconds{namespace!="",pod!=""}'
      resources:
        overrides:
          namespace: {resource: "namespace"}
          pod: {resource: "pod"}
      name:
        matches: "inference_latency_milliseconds"
      metricsQuery: 'avg(<<.Series>>{<<.LabelMatchers>>})'
```

**Ejemplo de KEDA (Kubernetes Event-driven Autoscaling):**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: inference-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc:9090
      metricName: inference_latency_milliseconds
      threshold: "100"
      query: avg(inference_latency_milliseconds{service="inference-service"})
```

**Escalado basado en utilización de GPU:**
El escalado basado en utilización de GPU puede implementarse usando herramientas como NVIDIA DCGM Exporter.

```yaml
# NVIDIA DCGM Exporter deployment
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
    spec:
      containers:
      - name: dcgm-exporter
        image: nvidia/dcgm-exporter:2.3.1-2.6.1-ubuntu20.04
        ports:
        - containerPort: 9400
          name: metrics
        securityContext:
          runAsNonRoot: false
          runAsUser: 0
        volumeMounts:
        - name: docker-socket
          mountPath: /var/run/docker.sock
      volumes:
      - name: docker-socket
        hostPath:
          path: /var/run/docker.sock

---
# GPU utilization-based HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-gpu
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: DCGM_FI_DEV_GPU_UTIL
      target:
        type: AverageValue
        averageValue: 70
```

**Consideraciones al seleccionar una estrategia de auto-scaling:**
1. **Características de la carga de trabajo**: Procesamiento por lotes, inferencia en tiempo real, procesamiento de streaming, etc.
2. **Requisitos de rendimiento**: Latencia, throughput, precisión, etc.
3. **Eficiencia de recursos**: Optimización de costos, utilización de recursos, etc.
4. **Escalabilidad**: Capacidad de responder a variaciones de carga
5. **Estabilidad**: Prevención de interrupciones del service debido a escalado rápido

**Problemas con las otras opciones:**
- A. Utilización de CPU: Las cargas de trabajo de AI/ML suelen estar limitadas por GPU o memoria, por lo que la utilización de CPU por sí sola puede no llevar a decisiones de escalado adecuadas.
- B. Utilización de memoria: La utilización de memoria normalmente no aumenta de forma proporcional al incremento de carga, especialmente porque permanece relativamente constante después de cargar el modelo.
- C. Utilización de GPU: La utilización de GPU es una métrica importante, pero no todas las cargas de trabajo de AI/ML usan GPU, e incluso cuando lo hacen, la utilización de GPU por sí sola puede no reflejar completamente la calidad del service.
</details>
### 7. ¿Cuál es la consideración más importante al configurar redes para cargas de trabajo de AI/ML en Kubernetes?

A. Configuración de NetworkPolicy
B. Implementación de service mesh
C. Redes de alto rendimiento y conciencia de topología para entrenamiento distribuido
D. Configuración de accesibilidad externa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Redes de alto rendimiento y conciencia de topología para entrenamiento distribuido**

**Explicación:**
La consideración más importante al configurar redes para cargas de trabajo de AI/ML en Kubernetes es contar con redes de alto rendimiento y conciencia de topología para entrenamiento distribuido. Las cargas de trabajo distribuidas de AI/ML necesitan intercambiar grandes cantidades de datos y parámetros del modelo entre Nodes, por lo que el rendimiento de red tiene un impacto significativo en el rendimiento general de entrenamiento e inferencia. Reconocer la topología de red para garantizar comunicación entre Nodes cercanos es importante para minimizar la latencia.

**Requisitos de red para cargas de trabajo distribuidas de AI/ML:**
1. **Alto ancho de banda**: Alto ancho de banda de red para intercambiar grandes cantidades de datos y parámetros del modelo
2. **Baja latencia**: Baja latencia de red para comunicación rápida entre Nodes
3. **Compatibilidad con RDMA (Remote Direct Memory Access)**: Reduce la sobrecarga de CPU mediante transferencia directa de datos entre memorias
4. **Conciencia de topología**: Ubicación de Pods considerando la topología de red
5. **Comunicación directa de GPU**: Compatibilidad con tecnologías para comunicación directa GPU-a-GPU como NVIDIA GPUDirect RDMA

**Ejemplo de configuración de red de alto rendimiento:**
```yaml
# Node selector and affinity settings for high-performance networking
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: distributed-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4
      template:
        spec:
          nodeSelector:
            network-type: high-performance
          affinity:
            podAntiAffinity:
              preferredDuringSchedulingIgnoredDuringExecution:
              - weight: 100
                podAffinityTerm:
                  labelSelector:
                    matchExpressions:
                    - key: tf-job-name
                      operator: In
                      values:
                      - distributed-training
                  topologyKey: kubernetes.io/hostname
            nodeAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                nodeSelectorTerms:
                - matchExpressions:
                  - key: topology.kubernetes.io/zone
                    operator: In
                    values:
                    - us-west-2a
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0-gpu
            env:
            - name: TF_CONFIG
              valueFrom:
                configMapKeyRef:
                  name: tf-config
                  key: tf-config.json
            resources:
              limits:
                nvidia.com/gpu: 1
```

**Configuración de conciencia de topología de red:**
```yaml
# Topology spread constraints setting
apiVersion: v1
kind: Pod
metadata:
  name: ml-worker
  labels:
    app: distributed-training
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: distributed-training
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: distributed-training
  containers:
  - name: ml-container
    image: ml-training:latest
```

**Configuración de interfaz de red de alto rendimiento:**
```yaml
# High-performance network interface configuration using Multus CNI
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-net
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "sriov-net",
    "type": "sriov",
    "ipam": {
      "type": "host-local",
      "subnet": "192.168.1.0/24",
      "rangeStart": "192.168.1.10",
      "rangeEnd": "192.168.1.200"
    }
  }'

---
apiVersion: v1
kind: Pod
metadata:
  name: ml-worker
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-net
spec:
  containers:
  - name: ml-container
    image: ml-training:latest
    resources:
      limits:
        intel.com/sriov: 1
```

**Configuración de compatibilidad con RDMA:**
```yaml
# Configuration for RDMA support
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: rdma-net
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "rdma-net",
    "type": "rdma",
    "ipam": {
      "type": "host-local",
      "subnet": "192.168.2.0/24"
    },
    "deviceID": "0000:03:00.0"
  }'

---
apiVersion: v1
kind: Pod
metadata:
  name: rdma-pod
  annotations:
    k8s.v1.cni.cncf.io/networks: rdma-net
spec:
  containers:
  - name: rdma-container
    image: rdma-app:latest
    securityContext:
      capabilities:
        add: ["IPC_LOCK"]
    volumeMounts:
    - name: rdma-devices
      mountPath: /dev/infiniband
  volumes:
  - name: rdma-devices
    hostPath:
      path: /dev/infiniband
```

**Configuración de NVIDIA GPUDirect RDMA:**
```yaml
# Configuration for NVIDIA GPUDirect RDMA support
apiVersion: v1
kind: Pod
metadata:
  name: gpudirect-pod
spec:
  containers:
  - name: gpudirect-container
    image: nvidia/cuda:11.0-base
    command: ["sleep", "infinity"]
    resources:
      limits:
        nvidia.com/gpu: 1
    securityContext:
      capabilities:
        add: ["IPC_LOCK"]
    volumeMounts:
    - name: nvidia-dev
      mountPath: /dev/nvidia0
    - name: nvidia-uvm
      mountPath: /dev/nvidia-uvm
    - name: nvidia-uvm-tools
      mountPath: /dev/nvidia-uvm-tools
    - name: nvidia-modeset
      mountPath: /dev/nvidia-modeset
  volumes:
  - name: nvidia-dev
    hostPath:
      path: /dev/nvidia0
  - name: nvidia-uvm
    hostPath:
      path: /dev/nvidia-uvm
  - name: nvidia-uvm-tools
    hostPath:
      path: /dev/nvidia-uvm-tools
  - name: nvidia-modeset
    hostPath:
      path: /dev/nvidia-modeset
```

**Estrategias de optimización del rendimiento de red:**
1. **Optimización de ubicación de Nodes**: Colocar Pods relacionados en el mismo rack o en Nodes cercanos
2. **Optimización de interfaces de red**: Mejorar el rendimiento de red usando tecnologías como SR-IOV, DPDK
3. **Conciencia de topología de red**: Usar topology spread constraints para ubicar Pods considerando la topología de red
4. **Uso de red dedicada**: Configurar interfaces de red dedicadas para cargas de trabajo de AI/ML
5. **Optimización de MTU**: Optimización de MTU (Maximum Transmission Unit) para transmisión de paquetes grandes

**Pruebas de rendimiento de red:**
```bash
# Network performance test using iperf3
kubectl run iperf3-server --image=networkstatic/iperf3 --port=5201 -- -s
kubectl expose pod iperf3-server --port=5201 --target-port=5201

kubectl run iperf3-client --image=networkstatic/iperf3 --rm -it -- -c iperf3-server -p 5201 -t 30
```

**Problemas con las otras opciones:**
- A. Configuración de NetworkPolicy: Importante para la seguridad, pero no impacta directamente el rendimiento de las cargas de trabajo de AI/ML.
- B. Implementación de service mesh: Útil para arquitectura de microservices, pero no cumple los requisitos de redes de alto rendimiento para cargas de trabajo de AI/ML.
- D. Configuración de accesibilidad externa: Importante para model serving, pero no impacta directamente el rendimiento del entrenamiento distribuido.
</details>

### 8. ¿Cuál es la consideración más importante al configurar seguridad para cargas de trabajo de AI/ML en Kubernetes?

A. Configuración de NetworkPolicy
B. Control de acceso y cifrado para modelos y datos
C. Escaneo de imágenes de container
D. Configuración de Pod Security Policy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Control de acceso y cifrado para modelos y datos**

**Explicación:**
La consideración más importante al configurar seguridad para cargas de trabajo de AI/ML en Kubernetes es el control de acceso y cifrado para modelos y datos. Las cargas de trabajo de AI/ML a menudo manejan datos sensibles y modelos de propiedad intelectual, por lo que proteger estos activos es lo más importante. Las fugas de datos o el robo de modelos pueden tener impactos graves de negocio y regulatorios.

**Riesgos de seguridad clave para cargas de trabajo de AI/ML:**
1. **Fuga de datos**: Fuga de información sensible como datos de entrenamiento o datos de inferencia
2. **Robo de modelos**: Robo de archivos de modelos de propiedad intelectual
3. **Envenenamiento de modelos**: Degradación del rendimiento del modelo o inyección de sesgos mediante ataques adversarios
4. **Manipulación de inferencia**: Inducir predicciones incorrectas mediante la manipulación de datos de entrada
5. **Escalamiento de privilegios**: Acceso al sistema mediante privilegios excesivos

**Estrategias clave para la seguridad de modelos y datos:**
1. **Control de acceso**:
   - Gestión granular de permisos mediante RBAC (Role-Based Access Control)
   - Aplicar el principio de privilegio mínimo
   - Separación de service accounts

2. **Cifrado**:
   - Encryption at Rest
   - Encryption in Transit
   - Cifrado de archivos de modelo

3. **Gestión de secretos**:
   - Usar Kubernetes Secrets o sistemas externos de gestión de secretos
   - Gestión segura de API keys, tokens de autenticación, etc.

4. **Seguridad de containers**:
   - Ejecutar containers con privilegios mínimos
   - Usar sistema de archivos de solo lectura
   - Ejecutar como usuario no root

**Ejemplo de configuración de RBAC:**
```yaml
# Role definition for model access
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: model-reader
  namespace: ml-models
rules:
- apiGroups: [""]
  resources: ["secrets", "configmaps"]
  verbs: ["get", "list"]
  resourceNames: ["model-weights", "model-config"]

---
# Model access role binding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: model-reader-binding
  namespace: ml-models
subjects:
- kind: ServiceAccount
  name: inference-service
  namespace: ml-models
roleRef:
  kind: Role
  name: model-reader
  apiGroup: rbac.authorization.k8s.io
```

**Ejemplo de almacenamiento cifrado de modelos:**
```yaml
# Secret for encrypted model storage
apiVersion: v1
kind: Secret
metadata:
  name: model-weights
  namespace: ml-models
type: Opaque
data:
  model.h5: <base64-encoded-encrypted-model>

---
# Pod using encrypted model
apiVersion: v1
kind: Pod
metadata:
  name: inference-pod
  namespace: ml-models
spec:
  serviceAccountName: inference-service
  containers:
  - name: inference
    image: ml-inference:latest
    volumeMounts:
    - name: model-volume
      mountPath: /models
      readOnly: true
    env:
    - name: MODEL_ENCRYPTION_KEY
      valueFrom:
        secretKeyRef:
          name: model-encryption-keys
          key: key1
  volumes:
  - name: model-volume
    secret:
      secretName: model-weights
```

**Ejemplo de integración con sistema externo de gestión de secretos (HashiCorp Vault):**
```yaml
# Secret injection using Vault Agent Injector
apiVersion: v1
kind: Pod
metadata:
  name: ml-training
  namespace: ml-workloads
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/agent-inject-secret-db-creds: "database/creds/ml-training-role"
    vault.hashicorp.com/role: "ml-training-role"
spec:
  serviceAccountName: ml-training
  containers:
  - name: training
    image: ml-training:latest
```

**Ejemplo de configuración de cifrado de datos:**
```yaml
# PersistentVolume with EBS encryption
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: encrypted-data
  namespace: ml-workloads
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: encrypted-storage
  resources:
    requests:
      storage: 100Gi

---
# Encrypted storage class
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: encrypted-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
```

**Ejemplo de hardening de seguridad de container:**
```yaml
# Security-hardened pod configuration
apiVersion: v1
kind: Pod
metadata:
  name: secure-ml-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
  containers:
  - name: ml-container
    image: ml-image:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: model-output
      mountPath: /output
  volumes:
  - name: tmp
    emptyDir: {}
  - name: model-output
    persistentVolumeClaim:
      claimName: model-output-pvc
```

**Ejemplo de NetworkPolicy:**
```yaml
# Network policy for ML workloads
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ml-network-policy
  namespace: ml-workloads
spec:
  podSelector:
    matchLabels:
      app: ml-inference
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - namespaceSelector:
        matchLabels:
          name: logging
    ports:
    - protocol: TCP
      port: 8125
```

**Estrategias adicionales para seguridad de modelos y datos:**
1. **Firma y verificación de modelos**: Aplicar firmas digitales a los archivos de modelo y verificarlos antes de usarlos
2. **Gestión de versiones de modelos**: Rastrear versiones y cambios de modelos
3. **Audit logging**: Mantener logs de auditoría para acceso a modelos y datos
4. **Enmascaramiento de datos**: Enmascarar campos de datos sensibles
5. **Privacidad diferencial**: Aplicar técnicas de privacidad diferencial para proteger información personal

**Problemas con las otras opciones:**
- A. Configuración de NetworkPolicy: Importante, pero no garantiza directamente por sí misma la seguridad de modelos y datos.
- C. Escaneo de imágenes de container: Importante para la gestión de vulnerabilidades, pero no aborda directamente la seguridad de modelos y datos.
- D. Configuración de Pod Security Policy: Fortalece la seguridad del entorno de ejecución de containers, pero no garantiza directamente por sí misma la seguridad de modelos y datos.
</details>
### 9. ¿Cuál es la métrica más importante para la configuración de logging y monitoreo de cargas de trabajo de AI/ML en Kubernetes?

A. Estado de Pods y Nodes
B. Métricas de rendimiento del modelo (precisión, latencia, etc.) y uso de recursos
C. Conteo de llamadas de API
D. Tráfico de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Métricas de rendimiento del modelo (precisión, latencia, etc.) y uso de recursos**

**Explicación:**
Las métricas más importantes para la configuración de logging y monitoreo de cargas de trabajo de AI/ML en Kubernetes son las métricas de rendimiento del modelo (precisión, latencia, etc.) y el uso de recursos. Estas métricas reflejan directamente la calidad del modelo, el cumplimiento de SLO (Service Level Objective) y la eficiencia de recursos, y ayudan a detectar temprano la degradación del rendimiento del modelo o cuellos de botella de recursos.

**Métricas clave de monitoreo:**

1. **Métricas de rendimiento del modelo**:
   - **Accuracy**: Precisión de las predicciones del modelo
   - **Precision**: Proporción de positivos reales entre los predichos como positivos
   - **Recall**: Proporción de predicciones positivas entre los positivos reales
   - **F1 Score**: Media armónica de precision y recall
   - **AUC-ROC**: Medición de rendimiento para modelos de clasificación binaria
   - **Mean Squared Error (MSE)**: Medición de error para modelos de regresión

2. **Métricas de nivel de service**:
   - **Latencia**: Tiempo desde la solicitud hasta la respuesta
   - **Throughput**: Número de solicitudes procesadas por unidad de tiempo
   - **Error Rate**: Proporción de solicitudes fallidas
   - **Availability**: Proporción de tiempo en que el service respondió normalmente

3. **Uso de recursos**:
   - **Utilización de CPU**: Utilización de CPU de containers y Nodes
   - **Utilización de memoria**: Utilización de memoria de containers y Nodes
   - **Utilización de GPU**: Utilización de cómputo y memoria de GPU
   - **Disk I/O**: Rendimiento de lectura/escritura de almacenamiento
   - **Network I/O**: Rendimiento de envío/recepción de red

**Ejemplo de configuración de stack de monitoreo:**
```yaml
# Prometheus configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
    - job_name: 'ml-metrics'
      kubernetes_sd_configs:
      - role: pod
        selectors:
        - role: pod
          label: "app=ml-inference"
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__

---
# Expose metrics from ML service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: inference
        image: ml-inference:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
```

**Ejemplo de exposición de métricas personalizadas (Python):**
```python
from prometheus_client import start_http_server, Summary, Counter, Gauge, Histogram
import time
import random

# Metric definitions
INFERENCE_LATENCY = Histogram('inference_latency_seconds', 'Inference latency in seconds',
                             ['model', 'version'])
INFERENCE_REQUESTS = Counter('inference_requests_total', 'Total number of inference requests',
                            ['model', 'version', 'status'])
MODEL_ACCURACY = Gauge('model_accuracy', 'Model accuracy',
                      ['model', 'version', 'dataset'])
GPU_MEMORY_USAGE = Gauge('gpu_memory_usage_bytes', 'GPU memory usage in bytes',
                        ['device'])

# Start metrics server
start_http_server(9090)

# Metric update example
def process_request(model_name, model_version, input_data):
    start_time = time.time()

    try:
        # Perform model inference
        result = model.predict(input_data)

        # Record latency
        latency = time.time() - start_time
        INFERENCE_LATENCY.labels(model=model_name, version=model_version).observe(latency)

        # Increment request count
        INFERENCE_REQUESTS.labels(model=model_name, version=model_version, status="success").inc()

        # Update GPU memory usage
        GPU_MEMORY_USAGE.labels(device="gpu0").set(get_gpu_memory_usage())

        return result
    except Exception as e:
        # Increment error request count
        INFERENCE_REQUESTS.labels(model=model_name, version=model_version, status="error").inc()
        raise e

# Periodically update model accuracy
def update_model_accuracy():
    while True:
        accuracy = evaluate_model_accuracy()
        MODEL_ACCURACY.labels(model="image_classifier", version="v1", dataset="validation").set(accuracy)
        time.sleep(3600)  # Update every hour
```

**Ejemplo de configuración de dashboard de Grafana:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ml-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  ml-dashboard.json: |
    {
      "title": "ML Model Monitoring",
      "panels": [
        {
          "title": "Inference Latency",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, sum(rate(inference_latency_seconds_bucket[5m])) by (le, model, version))",
              "legendFormat": "p95 - {{model}} - {{version}}"
            },
            {
              "expr": "histogram_quantile(0.50, sum(rate(inference_latency_seconds_bucket[5m])) by (le, model, version))",
              "legendFormat": "p50 - {{model}} - {{version}}"
            }
          ]
        },
        {
          "title": "Request Rate",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "sum(rate(inference_requests_total[5m])) by (model, version, status)",
              "legendFormat": "{{model}} - {{version}} - {{status}}"
            }
          ]
        },
        {
          "title": "Model Accuracy",
          "type": "gauge",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "model_accuracy",
              "legendFormat": "{{model}} - {{version}} - {{dataset}}"
            }
          ],
          "options": {
            "min": 0,
            "max": 1,
            "thresholds": [
              { "color": "red", "value": 0 },
              { "color": "yellow", "value": 0.7 },
              { "color": "green", "value": 0.9 }
            ]
          }
        },
        {
          "title": "GPU Memory Usage",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "gpu_memory_usage_bytes",
              "legendFormat": "{{device}}"
            }
          ]
        }
      ]
    }
```

**Ejemplo de configuración de logging:**
```yaml
# Fluent Bit configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush        5
        Daemon       Off
        Log_Level    info

    [INPUT]
        Name             tail
        Tag              kube.*
        Path             /var/log/containers/*.log
        Parser           docker
        DB               /var/log/flb_kube.db
        Mem_Buf_Limit    5MB
        Skip_Long_Lines  On
        Refresh_Interval 10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Merge_Log_Key       log_processed
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [FILTER]
        Name         grep
        Match        kube.var.log.containers.ml-*
        Regex        log ERROR|WARN|INFO

    [OUTPUT]
        Name            es
        Match           kube.var.log.containers.ml-*
        Host            elasticsearch
        Port            9200
        Index           ml-logs
        Type            _doc
        Logstash_Format On
        Logstash_Prefix ml-logs
        Time_Key        @timestamp
        Replace_Dots    On
        Retry_Limit     False
```

**Herramientas adicionales para monitoreo del rendimiento de modelos:**
1. **MLflow**: Seguimiento de experimentos, gestión de versiones de modelos, registro de modelos
2. **TensorBoard**: Visualización del proceso de entrenamiento y rendimiento de modelos de TensorFlow
3. **Weights & Biases**: Seguimiento de experimentos, comparación de rendimiento de modelos, optimización de hiperparámetros
4. **Seldon Core Metrics**: Métricas de model serving proporcionadas por Seldon Core
5. **KServe Metrics**: Métricas de model serving proporcionadas por KServe

**Ejemplo de configuración de alertas de monitoreo:**
```yaml
# Prometheus alert rules
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ml-alerts
  namespace: monitoring
spec:
  groups:
  - name: ml.rules
    rules:
    - alert: HighInferenceLatency
      expr: histogram_quantile(0.95, sum(rate(inference_latency_seconds_bucket[5m])) by (le, model, version)) > 0.5
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High inference latency"
        description: "Model {{ $labels.model }} version {{ $labels.version }} has p95 latency above 500ms"

    - alert: LowModelAccuracy
      expr: model_accuracy < 0.8
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "Low model accuracy"
        description: "Model {{ $labels.model }} version {{ $labels.version }} has accuracy below 80%"

    - alert: HighErrorRate
      expr: sum(rate(inference_requests_total{status="error"}[5m])) / sum(rate(inference_requests_total[5m])) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate"
        description: "Error rate is above 5%"
```

**Problemas con las otras opciones:**
- A. Estado de Pods y Nodes: Importante para el monitoreo básico del estado del sistema, pero no refleja directamente el rendimiento y la calidad de las cargas de trabajo de AI/ML.
- C. Conteo de llamadas de API: Útil para medir el uso del sistema, pero no indica directamente el rendimiento del modelo ni la eficiencia de recursos.
- D. Tráfico de red: Importante para entrenamiento distribuido o transferencias de datos a gran escala, pero no refleja directamente el rendimiento ni la calidad del modelo.
</details>

### 10. ¿Cuál es la estrategia de optimización de costos más efectiva para cargas de trabajo de AI/ML en Kubernetes?

A. Usar siempre los tipos de instancia más recientes
B. Usar instancias Spot para todas las cargas de trabajo
C. Selección adecuada del tipo de instancia y auto-scaling según las características de la carga de trabajo
D. Minimizar requests y limits para todos los recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Selección adecuada del tipo de instancia y auto-scaling según las características de la carga de trabajo**

**Explicación:**
La estrategia de optimización de costos más efectiva para cargas de trabajo de AI/ML en Kubernetes es la selección adecuada del tipo de instancia y auto-scaling según las características de la carga de trabajo. Las cargas de trabajo de AI/ML tienen diferentes requisitos de recursos en varias etapas, como entrenamiento, inferencia y preprocesamiento de datos, y seleccionar tipos de instancia que coincidan con las características de cada carga de trabajo y aplicar auto-scaling según sea necesario es importante para optimizar la eficiencia de costos.

**Selección de tipos de instancia por características de la carga de trabajo:**

1. **Entrenamiento de modelos**:
   - **Instancias GPU**: Adecuadas para entrenamiento de modelos de deep learning
   - **Instancias optimizadas para memoria**: Adecuadas para procesamiento de datasets a gran escala
   - **Instancias optimizadas para cómputo**: Adecuadas para algoritmos intensivos en cómputo

2. **Inferencia de modelos**:
   - **Instancias GPU**: Adecuadas para modelos complejos o inferencia en tiempo real
   - **Instancias CPU**: Adecuadas para modelos simples o inferencia por lotes
   - **Instancias optimizadas para inferencia (AWS Inferentia, Google TPU, etc.)**: Instancias especializadas para inferencia

3. **Preprocesamiento de datos**:
   - **Instancias optimizadas para cómputo**: Adecuadas para procesamiento paralelo
   - **Instancias optimizadas para memoria**: Adecuadas para procesamiento de datasets a gran escala
   - **Instancias optimizadas para almacenamiento**: Adecuadas para trabajos intensivos en I/O

**Ejemplo de configuración de Node group:**
```yaml
# Training node group (GPU instances)
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ml-cluster
  region: us-west-2
nodeGroups:
  - name: training-ng
    instanceType: p3.2xlarge  # GPU instance
    minSize: 0
    maxSize: 10
    labels:
      workload-type: training
    taints:
      - key: workload-type
        value: training
        effect: NoSchedule
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"

  # Inference node group (CPU instances)
  - name: inference-ng
    instanceType: c5.2xlarge  # Compute-optimized instance
    minSize: 1
    maxSize: 20
    labels:
      workload-type: inference
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"

  # Data preprocessing node group (Memory-optimized instances)
  - name: preprocessing-ng
    instanceType: r5.2xlarge  # Memory-optimized instance
    minSize: 0
    maxSize: 10
    labels:
      workload-type: preprocessing
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"

  # Spot instance node group (Cost-effective batch jobs)
  - name: spot-ng
    instanceTypes: ["m5.xlarge", "m5a.xlarge", "m5n.xlarge"]
    minSize: 0
    maxSize: 20
    spot: true
    labels:
      workload-type: batch
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"
```

**Ejemplo de ubicación de cargas de trabajo:**
```yaml
# Training job (Place on GPU nodes)
apiVersion: batch/v1
kind: Job
metadata:
  name: training-job
spec:
  template:
    spec:
      nodeSelector:
        workload-type: training
      containers:
      - name: training
        image: training:latest
        resources:
          limits:
            nvidia.com/gpu: 1

# Inference service (Place on CPU nodes)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      nodeSelector:
        workload-type: inference
      containers:
      - name: inference
        image: inference:latest
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi

# Data preprocessing job (Place on memory-optimized nodes)
apiVersion: batch/v1
kind: Job
metadata:
  name: preprocessing-job
spec:
  template:
    spec:
      nodeSelector:
        workload-type: preprocessing
      containers:
      - name: preprocessing
        image: preprocessing:latest
        resources:
          requests:
            memory: 16Gi
          limits:
            memory: 32Gi

# Batch inference job (Place on Spot instances)
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-inference
spec:
  template:
    spec:
      nodeSelector:
        workload-type: batch
      tolerations:
      - key: spot
        operator: Exists
      containers:
      - name: batch-inference
        image: batch-inference:latest
```

**Ejemplo de configuración de auto-scaling:**
```yaml
# Cluster Autoscaler configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-config
  namespace: kube-system
data:
  config.yaml: |
    expendablePodsPriorityCutoff: -10
    scaleDownUtilizationThreshold: 0.5
    scaleDownUnneededTime: 5m
    scaleDownDelayAfterAdd: 5m
    scaleDownDelayAfterDelete: 0s
    scaleDownDelayAfterFailure: 3m
    maxNodeProvisionTime: 15m

# HPA configuration (Inference service)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: inference_latency_milliseconds
      target:
        type: AverageValue
        averageValue: 100
```

**Estrategias de optimización de costos:**

1. **Selección adecuada del tipo de instancia**:
   - Seleccionar tipos de instancia que coincidan con las características de la carga de trabajo
   - Seleccionar instancias óptimas mediante análisis de costo vs rendimiento
   - Utilizar instancias especializadas (GPU, TPU, etc.)

2. **Uso de instancias Spot**:
   - Usar instancias Spot para cargas de trabajo tolerantes a fallos
   - Mejorar la disponibilidad especificando varios tipos de instancia
   - Implementar estrategias de tolerancia a interrupciones

3. **Auto-scaling**:
   - Ajustar automáticamente el número de Nodes mediante Cluster Autoscaler
   - Ajustar automáticamente el número de Pods mediante HPA
   - Escalado basado en métricas personalizadas

4. **Optimización de requests y limits de recursos**:
   - Establecer solicitudes de recursos según el uso real
   - Ajustar automáticamente solicitudes de recursos mediante Vertical Pod Autoscaler
   - Monitoreo y optimización del uso de recursos

5. **Optimización de programación de trabajos**:
   - Ejecutar trabajos por lotes durante periodos de menor costo
   - Colocar trabajos de menor prioridad en recursos de bajo costo
   - Configuración de colas y prioridades de trabajos

**Herramientas de monitoreo y optimización de costos:**
1. **Kubecost**: Monitoreo y optimización de costos para clusters de Kubernetes
2. **AWS Cost Explorer**: Análisis de costos de recursos de AWS
3. **Google Cloud Cost Management**: Análisis de costos de recursos de GCP
4. **Azure Cost Management**: Análisis de costos de recursos de Azure
5. **Prometheus + Grafana**: Configuración de dashboard de costos personalizado

**Problemas con las otras opciones:**
- A. Usar siempre los tipos de instancia más recientes: Las instancias más recientes no siempre son las más rentables, y seleccionar instancias que coincidan con las características de la carga de trabajo es más importante.
- B. Usar instancias Spot para todas las cargas de trabajo: Las instancias Spot pueden interrumpirse, por lo que no son adecuadas para cargas de trabajo críticas sensibles a interrupciones.
- D. Minimizar requests y limits para todos los recursos: Minimizar excesivamente las solicitudes de recursos puede causar problemas de rendimiento, y es importante una asignación adecuada de recursos que coincida con las características de la carga de trabajo.
</details>
